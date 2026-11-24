# /// script
# requires-python = ">=3.10"
# dependencies = ["ruamel.yaml==0.19.1"]
# ///
"""Build the report page of the first held-out calibration of the graphic-design review
(project-kit#3230).

Usage, from the repository's root:

    uv run --script .agent-workspace/calibration/report/build_report.py

It writes `.agent-workspace/calibration/report/index.html`. Run `readings.py` first: the page's
conditions and per-rule readings are quoted from the two readings it writes.

What this script computes itself, since the plan asks for it and analyse.py does not:

- each page design's verdict and grades in each run, read with analyse.py's own `Review` class
  from the deck the judges' key names first for the design, as analyse.py scores it;
- the same image's verdict and covered grades in every other deck it stands in, within each run;
- the review's place on each page, by analyse.py's own score (counting weak grades), over the
  page's ten designs, ties sharing a place;
- the marks of plan.md section 3 (a difference that counts, a smaller difference);
- the judges' grades, read from their files; the models and the reads each review names; the
  digests of the ladder's files and of the review folders' images, checked against their lists.
"""

import datetime
import hashlib
import html
import importlib.util
import json
import re
import subprocess
from ast import literal_eval
from collections import Counter
from pathlib import Path

from ruamel.yaml.error import MarkedYAMLError

ROOT = Path.cwd()
PLAN = ROOT / ".claude/worktrees/w3230/tech-docs/calibrations/graphic-design-review/2026-11-17"
WS = ROOT / ".agent-workspace"
JUDGE = WS / "ladder-judge"
CAL = WS / "calibration"
OUT = CAL / "report"
RUNS = (1, 2, 3)
RULES = [f"RS-COMM-00{i}" for i in range(1, 6)] + [f"RS-GRAPHIC-00{i}" for i in range(1, 9)]
GRADES = ("below competent", "competent", "professional", "excellent")
SHORT = {1: "below", 2: "comp", 3: "prof", 4: "exc"}
LETTER = {1: "B", 2: "C", 3: "P", 4: "E"}
PRO = 3


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


analyse = load("analyse", PLAN / "run/analyse.py")
readings = load("readings", OUT / "readings.py")
VAL = analyse.VAL

ref = json.loads((PLAN / "run/reference.json").read_text())
jkey = json.loads((JUDGE / "key.json").read_text())
covered = set(ref["bar"]["covers"])
COVERED_PAGE = [r for r in RULES if r in covered and r != "RS-COMM-003"]


def e(x) -> str:
    return html.escape(str(x), quote=True)


def deck_label(d: str | None) -> str:
    if d is None:
        return "?"
    if d.startswith("rounds/round-"):
        return "r" + d.rsplit("-", 1)[1]
    return {
        "sets/capability-main": "main",
        "sets/grey-boxes": "grey",
        "sets/form-contradicts": "form",
    }.get(d, d.replace("variants/RS-", "var "))


# --- the reviews -------------------------------------------------------------------------

runs: dict[int, dict[str, dict]] = {}
for n in RUNS:
    key = json.loads((CAL / f"keys/run-{n}.json").read_text())
    runs[n] = {}
    for code, entry in key["folders"].items():
        path = CAL / f"reports/run-{n}/{code}.md"
        lines: list = []
        try:
            doc = analyse.load_doc(path)
            recovered = False
        except MarkedYAMLError:
            doc = readings.recover(path, lines)
            recovered = True
        runs[n][entry["version"]] = {
            "code": code,
            "doc": doc,
            "recovered": recovered,
            "lines": lines,
            "entry": entry,
            "review": analyse.Review(doc, entry, covered),
            "folder": WS / f"review-runs/run-{n}/{code}",
        }
VERSIONS = sorted(runs[1])

home: dict[tuple[int, str], str] = {}
decks_of: dict[tuple[int, str], list[str]] = {}
for p, codes in jkey["pages"].items():
    for code, sources in codes.items():
        ds = [s for s in sources if not s.startswith("anchor")]
        if ds:
            home[(int(p), code)] = ds[0]
            decks_of[(int(p), code)] = ds

ORDER_VARIANT = "variants/RS-COMM-003"
VARIANT_PAGE_OF = {1: 1, 4: 2, 2: 3, 3: 4}  # round 5's page n stands as the order variant's page m


def rv(n: int, deck: str):
    return runs[n][deck]["review"]


def page_grade(n: int, deck: str, p: int, rule: str):
    g = rv(n, deck).pages[p].get(rule)
    return g


def marks_of(n: int, deck: str, p: int | None) -> list[dict]:
    doc = runs[n][deck]["doc"]
    pid = runs[n][deck]["entry"]["pages"][str(p)]["id"] if p else None
    return [
        g
        for g in doc.get("grades", []) or []
        if "mark" in g
        and ((p is None and g["on"].get("piece")) or (p is not None and g["on"].get("page") == pid))
    ]


MARK_COUNT = sum(
    1
    for n in RUNS
    for d in VERSIONS
    for g in runs[n][d]["doc"].get("grades", []) or []
    if "mark" in g
)


def not_graded(n: int, deck: str, p: int | None, rule: str) -> str | None:
    doc = runs[n][deck]["doc"]
    pid = runs[n][deck]["entry"]["pages"][str(p)]["id"] if p else None
    for g in doc.get("not-graded", []) or []:
        on = g.get("on", {})
        if g.get("rule") == rule and (
            (p is None and on.get("piece")) or (p is not None and on.get("page") == pid)
        ):
            return " ".join(str(g.get("why", "")).split())
    return None


# --- the judges ---------------------------------------------------------------------------

GRADE_RE = "(below competent|competent|professional|excellent)"


def parse_rule_list(rest: str, known: dict) -> dict[str, int]:
    rest = rest.strip()
    m = re.match(r"as (\w+) but (.*)$", rest)
    if m:
        out = dict(known[m.group(1)])
        out.update(parse_rule_list(m.group(2), known))
        return out
    m = re.match(rf"(.*?) {GRADE_RE}$", rest)
    if m and ";" not in rest:
        out = {}
        for part in re.split(r" and ", m.group(1)):
            fam = re.match(r"(RS-[A-Z]+)-(\d{3})((?:, \d{3})*)", part.strip())
            if fam:
                nums = [fam.group(2), *re.findall(r"\d{3}", fam.group(3))]
                for num in nums:
                    out[f"{fam.group(1)}-{num}"] = VAL[m.group(2)]
        if out:
            return out
    out = {}
    for item in rest.split(";"):
        mm = re.match(rf"\s*(RS-[A-Z]+-\d{{3}}) {GRADE_RE}\s*$", item)
        if not mm:
            raise SystemExit(f"error: cannot read the judge's grade {item!r}")
        out[mm.group(1)] = VAL[mm.group(2)]
    return out


def parse_judge(path: Path, rules_heading: str) -> dict:
    text = path.read_text()
    out: dict = {"pages": {str(p): {} for p in range(1, 5)}, "deck": {}}
    page = None
    in_rules = False
    known: dict[str, dict] = {}
    for line in text.splitlines():
        m = re.match(r"^## Page (\d)", line)
        if m:
            page, in_rules = m.group(1), False
            continue
        if line.startswith("## Rule grades"):
            in_rules = True
            page = None
            continue
        m = re.match(r"^### Page (\d)", line)
        if m and in_rules:
            page = m.group(1)
            known = {}
            continue
        if line.startswith("### Rule grades"):
            in_rules = True
            known = {}
            continue
        if line.startswith("### Pass line") or line.startswith("## Deck order"):
            in_rules = False
            if line.startswith("## Deck order"):
                page = None
            continue
        m = re.match(r"^\| (\d+=?) \| ([A-Z]{3}) \| " + GRADE_RE + r" \|", line)
        if m and page and not in_rules:
            out["pages"][page].setdefault(m.group(2), {})["rank"] = m.group(1)
            out["pages"][page][m.group(2)]["overall"] = m.group(3)
            continue
        m = re.match(r"^- ([A-Z]{3}): (.*)$", line)
        if m and page and in_rules:
            grades = parse_rule_list(m.group(2), known)
            known[m.group(1)] = grades
            out["pages"][page].setdefault(m.group(1), {})["rules"] = grades
            continue
        m = re.match(rf"^- order[- ]([AB]): RS-COMM-003 {GRADE_RE}", line, re.I)
        if m:
            out["deck"][m.group(1).upper()] = VAL[m.group(2)]
    return out


judges = {
    1: parse_judge(JUDGE / "judge-1-fable.md", "## Rule grades"),
    2: parse_judge(JUDGE / "judge-2-opus.md", "### Rule grades"),
}


def jgrade(j: int, p: int, code: str, rule: str) -> int | None:
    return judges[j]["pages"][str(p)].get(code, {}).get("rules", {}).get(rule)


# --- the readings ---------------------------------------------------------------------------


def parse_readings(path: Path) -> dict:
    text = path.read_text()
    R: dict = {
        "c1": {},
        "c1ev": {},
        "c2": {},
        "fpff": {},
        "c3": {},
        "c4": {},
        "bar": {},
        "rules": {},
        "matrix": {},
        "head": [],
        "text": text,
    }
    section = None
    place = None
    rule = None
    cur_run = None
    for line in text.splitlines():
        if line.startswith("## "):
            section = line[3:]
            rule = None
            continue
        if section is None and line.startswith("- "):
            R["head"].append(line[2:])
        m = re.match(r"^\*\*Condition (\d) for the bar: (met|NOT MET)\*\*", line)
        if m:
            R["bar"][int(m.group(1))] = m.group(2) == "met"
            continue
        if section == "Condition 1, order":
            m = re.match(r"^### (?:Page (\d)|The deck):", line)
            if m:
                place = m.group(1) or "deck"
                R["c1"][place] = {}
                R["c1ev"][place] = {}
                continue
            m = re.match(r"^- run (\d): (met|NOT MET); scores \(.*?\): (.*)$", line)
            if m:
                cur_run = int(m.group(1))
                scores = {
                    k: (int(a), int(b), int(c))
                    for k, a, b, c in re.findall(
                        r"([a-z-]+) \((-?\d+), (-?\d+), (-?\d+)\)", m.group(3)
                    )
                }
                R["c1"][place][cur_run] = {
                    "met": m.group(2) == "met",
                    "scores": scores,
                    "clauses": {},
                }
                continue
            m = re.match(r"^  - (.+): (holds|DOES NOT HOLD)$", line)
            if m:
                R["c1"][place][cur_run]["clauses"][m.group(1)] = m.group(2) == "holds"
                continue
            m = re.match(
                r"^- run (\d), evidence over (\d+) designs: tau-b ([+-]\d\.\d\d); his ordered "
                r"pairs kept in order (\d+)%",
                line,
            )
            if m:
                R["c1ev"][place][int(m.group(1))] = (m.group(2), m.group(3), m.group(4))
        elif section == "Condition 2, the pass line":
            m = re.match(
                r"^- (page (\d)|the deck), run (\d): last failed (\S+) (\w+), first passed (\S+) "
                r"(\w+): (met|NOT MET)",
                line,
            )
            if m:
                pl = m.group(2) or "deck"
                R["c2"].setdefault(pl, {})[int(m.group(3))] = {
                    "lf": m.group(4),
                    "lfv": m.group(5),
                    "fp": m.group(6),
                    "fpv": m.group(7),
                    "met": m.group(8) == "met",
                }
                continue
            m = re.match(r"^- run (\d): false passes (\d+) (\[.*\])$", line)
            if m:
                cur_run = int(m.group(1))
                R["fpff"][cur_run] = {"fp": literal_eval(m.group(3))}
                continue
            m = re.match(r"^  false fails (\d+) (\[.*\])$", line)
            if m:
                R["fpff"][cur_run]["ff"] = literal_eval(m.group(2))
        elif section == "Condition 3, stability":
            m = re.match(
                r"^- page (\d): (\d+) of (\d+) images take one verdict in every run and every "
                r"deck(?:: (.*))?$",
                line,
            )
            if m:
                R["c3"][m.group(1)] = (m.group(2), m.group(3), m.group(4))
                continue
            m = re.match(
                r"^- the deck: (\d+) of (\d+) deck versions take one piece verdict in every "
                r"run(?:: (.*))?$",
                line,
            )
            if m:
                R["c3"]["deck"] = (m.group(1), m.group(2), m.group(3))
        elif section == "Condition 4, the weak deck fails":
            m = re.match(r"^- run (\d): (.*); its deck (\w+): (met|NOT MET)$", line)
            if m:
                pages = dict(re.findall(r"([A-Z]{3}) (\w+)", m.group(2)))
                R["c4"][int(m.group(1))] = {
                    "pages": pages,
                    "deck": m.group(3),
                    "met": m.group(4) == "met",
                }
        elif section == "Each covered rule":
            m = re.match(r"^### (RS-\S+)", line)
            if m:
                rule = m.group(1)
                R["rules"][rule] = []
                continue
            if rule and line.startswith("- "):
                R["rules"][rule].append(line[2:])
        elif section == "The covered rules against the four conditions":
            m = re.match(r"^\| (\*\*For the bar\*\*|RS-\S+) \| (.*) \|$", line)
            if m:
                R["matrix"][m.group(1).strip("*")] = [c.strip() for c in m.group(2).split("|")]
    return R


REC = parse_readings(OUT / "readings-recovered.md")
STR = parse_readings(OUT / "readings-strict.md")
recovery = json.loads((OUT / "recovery.json").read_text())


# --- figures this script computes -------------------------------------------------------------


def place_on_page(n: int, p: int) -> dict[str, str]:
    order = ref["pages"][str(p)]["order"]
    scores = {c: rv(n, home[(p, c)]).page_score(p) for c in order}
    out = {}
    for c in order:
        better = sum(1 for o in order if scores[o] > scores[c])
        tie = any(scores[o] == scores[c] for o in order if o != c)
        out[c] = f"{better + 1}{'=' if tie else ''}"
    return out


PLACES = {(n, p): place_on_page(n, p) for n in RUNS for p in range(1, 5)}


def ordinal(k: int) -> str:
    return f"{k}{'th' if 10 <= k % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(k % 10, 'th')}"


def his_verdict(p: int, code: str) -> str:
    pl = ref["pages"][str(p)]
    if code in pl["pass"]:
        return "pass"
    if code in pl["fail"]:
        return "fail"
    return "none"


def deck_ref(d: str) -> str:
    if d in ref["decks"]["pass"]:
        return "pass"
    if d in ref["decks"]["fail"]:
        return "fail"
    return "none"


def side(v: int | None):
    return None if v is None else v >= PRO


def within_run_splits() -> list[str]:
    out = []
    for p in range(1, 5):
        for code in ref["pages"][str(p)]["order"]:
            ds = decks_of[(p, code)]
            if len(ds) < 2:
                continue
            for n in RUNS:
                vs = {d: rv(n, d).page_verdict(p) for d in ds}
                if len(set(vs.values())) > 1:
                    groups: dict = {}
                    for d, v in vs.items():
                        groups.setdefault(v, []).append(deck_label(d))
                    out.append(
                        f"page {p} {code}, run {n}: "
                        + "; ".join(
                            f"{v or 'none'} in {', '.join(ds_)}" for v, ds_ in groups.items()
                        )
                    )
    return out


WITHIN = within_run_splits()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ladder_check() -> dict:
    lines = (PLAN / "ladder-digests.txt").read_text().splitlines()
    ok = bad = missing = 0
    bad_list = []
    for line in lines:
        digest, rel = line.split(None, 1)
        f = WS / "ladder" / rel.strip()
        if not f.exists():
            missing += 1
            bad_list.append(f"missing {rel}")
        elif sha256(f) == digest:
            ok += 1
        else:
            bad += 1
            bad_list.append(f"differs {rel}")
    pngs = [ln for ln in lines if ln.endswith(".png")]
    blind = sorted(p for p in (JUDGE / "blind").rglob("*.png"))
    blind_list = "".join(f"{sha256(b)}  {b.relative_to(JUDGE / 'blind')}\n" for b in blind)
    folder_ok = folder_bad = 0
    for n in RUNS:
        key = json.loads((CAL / f"keys/run-{n}.json").read_text())
        for code, entry in key["folders"].items():
            for name, digest in entry["digests"].items():
                f = WS / f"review-runs/run-{n}/{code}/{name}"
                if f.exists() and sha256(f) == digest:
                    folder_ok += 1
                else:
                    folder_bad += 1
    return {
        "files": len(lines),
        "pngs": len(pngs),
        "ok": ok,
        "bad": bad,
        "missing": missing,
        "bad_list": bad_list,
        "list_digest": sha256(PLAN / "ladder-digests.txt"),
        "blind_count": len(blind),
        "blind_digest": hashlib.sha256(blind_list.encode()).hexdigest(),
        "folder_ok": folder_ok,
        "folder_bad": folder_bad,
    }


LADDER = ladder_check()


def git(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(PLAN), *args], capture_output=True, text=True
    ).stdout.strip()


PLAN_COMMIT = git("log", "-1", "--format=%H %cI", "45ec28e3aba1816491c6e826bb525e626c83d243")
PROMPT_COMMIT = git("log", "-1", "--format=%H %cI", "--", "run/review-prompt.md")
PLAN_LAST = git("log", "-1", "--format=%H %cI", "--", "plan.md")
PLAN_DIRTY = git("status", "--porcelain", "--", ".")


def mtime(path: Path) -> str:
    return (
        datetime.datetime.fromtimestamp(path.stat().st_mtime)
        .astimezone()
        .isoformat(timespec="seconds")
    )


RUN_TIMES = {}
for n in RUNS:
    reps = [CAL / f"reports/run-{n}/{runs[n][d]['code']}.md" for d in VERSIONS]
    ts = sorted(r.stat().st_mtime for r in reps)
    RUN_TIMES[n] = {
        "key": mtime(CAL / f"keys/run-{n}.json"),
        "first": datetime.datetime.fromtimestamp(ts[0]).astimezone().isoformat(timespec="seconds"),
        "last": datetime.datetime.fromtimestamp(ts[-1]).astimezone().isoformat(timespec="seconds"),
    }


def analyse_fence_end(text: str) -> int:
    m = readings.FENCE.search(text)
    return m.end() if m else 0


# the reads each review names
READS = []
for n in RUNS:
    for d in VERSIONS:
        r = runs[n][d]
        entries = r["doc"].get("read-before-grading", []) or []
        texts = " ".join(str(x.get("what", "")) for x in entries)
        full = (CAL / f"reports/run-{n}/{r['code']}.md").read_text()
        prose = full[analyse_fence_end(full) :]
        READS.append(
            {
                "run": n,
                "code": r["code"],
                "deck": d,
                "entries": entries,
                "schemas": bool(re.search(r"schema", texts)),
                "schemas-prose": bool(re.search(r"review\.schema\.json|review\.ya?ml", prose)),
                "techdocs": "tech-docs" in texts,
                "model": r["doc"].get("model", {}) or {},
            }
        )

MODELS = Counter((x["model"].get("name"), x["model"].get("effort")) for x in READS)


# --- rendering helpers -------------------------------------------------------------------------


def chip(v: int | None, extra: str = "", title: str = "") -> str:
    if v is None:
        return (
            f'<span class="g g0"{f" title={chr(34)}{e(title)}{chr(34)}" if title else ""}>'
            f"—</span>{extra}"
        )
    return f'<span class="g g{v}" title="{e(GRADES[v - 1])}">{SHORT[v]}</span>{extra}'


def vchip(v: str | None, mark: str = "") -> str:
    if v is None or v == "none":
        return f'<span class="v vn">no verdict</span>{mark}'
    return (
        f'<span class="v v{"p" if v == "pass" else "f"}">'
        f"{'pass' if v == 'pass' else 'FAIL'}</span>{mark}"
    )


def refchip(v: str) -> str:
    return {
        "pass": '<span class="v vp">passes</span>',
        "fail": '<span class="v vf">fails</span>',
        "none": '<span class="v vn">no reading</span>',
    }[v]


def big(s: str) -> str:
    return f'<span class="dm" title="a difference that counts">◆{s}</span>'


def small() -> str:
    return '<span class="sm" title="a smaller difference">◇</span>'


def met(x) -> str:
    if x is None:
        return '<span class="nc">no counterpart</span>'
    if isinstance(x, str):
        x = {"met": True, "NOT MET": False, "no counterpart": None}[x]
        if x is None:
            return '<span class="nc">no counterpart</span>'
    return '<span class="met">met</span>' if x else '<span class="nmet">not met</span>'


def img(p: int, code: str, mode: str) -> str:
    src = f"../../ladder-judge/blind/page-{p}/{mode}/{code}.png"
    return (
        f'<figure><a href="{e(src)}"><img loading="lazy" src="{e(src)}" width="1600" height="900" '
        f'alt="Page {p}, {code}, {mode} mode"></a><figcaption>{mode}</figcaption></figure>'
    )


def rec_mark(n: int, deck: str) -> str:
    return (
        '<sup class="rec" title="this review\'s document does not parse; read with its evidence '
        'line quoted">‡</sup>'
        if runs[n][deck]["recovered"]
        else ""
    )


def score_text(t) -> str:
    a, b, c = t
    return f"{-a}·{-b}·{c}"


# --- the head ----------------------------------------------------------------------------------


def head_section() -> str:
    covers = ", ".join(f"{r}@{1 if r.startswith('RS-COMM') else 2}" for r in ref["bar"]["covers"])
    unparsed = [
        (n, runs[n][d]["code"], d) for n in RUNS for d in VERSIONS if runs[n][d]["recovered"]
    ]
    rec_rows = "".join(
        f"<tr><td>{e(Path(x['report']).parent.name)}</td><td>{e(Path(x['report']).stem)}</td><td>"
        f"{x['line']}</td>"
        f"<td>{e(x['error'])}</td><td><code>{e(x['was'].strip())}</code></td></tr>"
        for x in recovery["lines-read-as-quoted"]
    )
    digests = (PLAN / "digests.txt").read_text()
    dj = json.loads(digests[digests.index("{") :])
    dig_rows = "".join(
        f"<tr><td>{e(r)}@{v['major']}</td><td><code>{e(v['text'])}</code></td></tr>"
        for r, v in dj["rules"].items()
    )
    for k in ("reviewer", "design-knowledge", "code", "checks"):
        dig_rows += f"<tr><td>{e(k)}</td><td><code>{e(dj[k])}</code></td></tr>"

    def model_reads(name, eff) -> str:
        return ", ".join(
            f"run {x['run']} {x['code']}"
            for x in READS
            if (x["model"].get("name"), x["model"].get("effort")) == (name, eff)
        )

    model_rows = "".join(
        f"<tr><td>{e(name)}</td><td>"
        f"{e(eff) if eff is not None else '<em>no effort field</em>'}</td><td>{c}</td>"
        f"<td>{e(model_reads(name, eff)) if c <= 3 else ''}</td></tr>"
        for (name, eff), c in sorted(MODELS.items(), key=lambda kv: (-kv[1], str(kv[0])))
    )
    names = Counter(x["model"].get("name") for x in READS)
    schemas = [x for x in READS if x["schemas"]]
    noschemas = [x for x in READS if not x["schemas"]]
    techdocs = [x for x in READS if x["techdocs"]]
    read_rows = ""
    for x in READS:
        items = "".join(
            f"<li><b>{e(it.get('kind'))}</b>: {e(' '.join(str(it.get('what', '')).split()))}</li>"
            for it in x["entries"]
        )
        flags = []
        if x["schemas"]:
            flags.append("review schemas")
        if x["techdocs"]:
            flags.append("<b>tech-docs/rule-sets/</b>")
        read_rows += (
            f"<tr><td>{x['run']}</td><td>{e(x['code'])}</td><td>{e(deck_label(x['deck']))}</td>"
            f"<td>{', '.join(flags) or '—'}</td><td><ul class='reads'>{items}</ul></td></tr>"
        )
    strict_matrix = matrix_table(STR, strict=True)
    run_times = "".join(
        f"<li>Run {n}: folders and key laid out {e(RUN_TIMES[n]['key'])}; reports written "
        f"{e(RUN_TIMES[n]['first'])} to {e(RUN_TIMES[n]['last'])} (file times).</li>"
        for n in RUNS
    )
    logs = ""
    for n in RUNS:
        lp = CAL / f"reports/run-{n}/log.md"
        if lp.exists():
            logs += (
                f"<li>Run {n}'s <code>log.md</code>: <blockquote>"
                f"{e(lp.read_text().strip())}</blockquote></li>"
            )
        else:
            logs += f"<li>Run {n}'s report folder holds no <code>log.md</code>.</li>"
    unparsed_rows = "".join(
        f"<li>run {n}, {e(c)}, {e(deck_label(d))} (<code>{e(d)}</code>)</li>"
        for n, c, d in unparsed
    )
    ladder_bad = (
        ""
        if not LADDER["bad_list"]
        else "<ul>" + "".join(f"<li><code>{e(b)}</code></li>" for b in LADDER["bad_list"]) + "</ul>"
    )
    return f"""
<section id="head">
<h2>The head</h2>

<div class="alert">
<h3>Step 1 failed: the plan's script stopped on a report</h3>
<p><code>analyse.py</code>, run as the plan fixes it, stopped on the first report whose YAML document does not parse
(<code>run-1/SXXN.md</code>: <em>mapping values are not allowed here</em>), and wrote no <code>readings.md</code>.
No report was edited. Read with <code>analyse.py</code>'s own loader, <b>{len(unparsed)} of 60</b> review documents do not parse,
at {len(recovery["lines-read-as-quoted"])} lines, each an <code>evidence:</code> value written as a plain scalar that holds
<code>": "</code> or opens with a quoted phrase followed by more words. As the reports stand, these {len(unparsed)} reviews give no verdict.</p>
<ul>{unparsed_rows}</ul>
<p>So the readings are taken twice, by <code>readings.py</code> (below), which runs <code>analyse.py</code>'s own code unchanged and replaces only how a document is read:</p>
<ul>
<li><b>Strict</b> (<a href="readings-strict.md"><code>readings-strict.md</code></a>): a document that does not parse is read as empty, so that review grades nothing and, by <code>analyse.py</code>'s rule, gives no verdict. This is the run as its reports stand. An empty review counts no weak grade, so condition 1's order places it as a version with none.</li>
<li><b>Recovered</b> (<a href="readings-recovered.md"><code>readings-recovered.md</code></a>): each <code>evidence:</code> line the parser stops on is read with its text as one single-quoted scalar, and nothing else is touched (<a href="recovery.json"><code>recovery.json</code></a> lists every such line). No grade, rule or page id is on any of these lines.</li>
</ul>
<p>Sections A to E show the <b>recovered</b> reading. Every figure from a recovered document carries <sup class="rec">‡</sup>, and each table of A gives the strict result beside it. Under the strict reading every condition is <b>not met</b> for the bar:</p>
{strict_matrix}
<details><summary>The {len(recovery["lines-read-as-quoted"])} lines read as quoted</summary>
<div class="tw"><table><thead><tr><th>Run</th><th>Report</th><th>Line of the YAML document</th><th>Parser's error</th><th>The line as written</th></tr></thead><tbody>{rec_rows}</tbody></table></div>
</details>
</div>

<h3>What ran</h3>
<ul>
<li><b>The bar as run:</b> <code>{{covers: [{e(covers)}], at-least: {e(ref["bar"]["at-least"])}}}</code>, from <code>run/reference.json</code>.</li>
<li><b>The plan's commit:</b> <code>{e(PLAN_COMMIT)}</code> on branch <code>feat/3230-the-review-is-calibrated-on</code> (worktree <code>w3230</code>), "fix the first held-out calibration's plan before its first run". The last commit touching <code>plan.md</code> is <code>{e(PLAN_LAST)}</code>. The review prompt was committed after it, at <code>{e(PROMPT_COMMIT)}</code>. The plan's folder has {"no uncommitted change" if not PLAN_DIRTY else "uncommitted changes: <code>" + e(PLAN_DIRTY) + "</code>"}.</li>
<li><b>The runs' times</b>, from the files' modification times:<ul>{run_times}</ul>Every run was laid out after both commits.</li>
<li><b>The number of runs:</b> 3, each with 20 reviews, one per deck version (the five anchors left out, answer 18).</li>
<li><b>The model and its effort,</b> as each review's document names them. Name: {", ".join(f"<code>{e(k)}</code> in {v}" for k, v in names.items())} of 60. The plan pins "Fable, at its default effort" (<code>digests.txt</code>).
<details><summary>Each (name, effort) the documents give, with its count</summary><div class="tw"><table><thead><tr><th>Name</th><th>Effort, as written</th><th>Reviews</th><th>Which, where three or fewer</th></tr></thead><tbody>{model_rows}</tbody></table></div></details></li>
<li><b>The digests</b> the hold is compared on, from <code>digests.txt</code> (read at <code>origin/main</code> b8a4e111d before the first run):
<div class="tw"><table class="dig"><thead><tr><th>What</th><th>Digest</th></tr></thead><tbody>{dig_rows}</tbody></table></div></li>
<li><b>The ladder:</b> its source lies in <code>.agent-workspace/ladder/</code> with its <code>manifest.md</code>; <code>ladder-digests.txt</code> beside the plan (sha256 <code>{LADDER["list_digest"]}</code>) lists {LADDER["files"]} files, {LADDER["pngs"]} of them images. Checked now: {LADDER["ok"]} match, {LADDER["bad"]} differ, {LADDER["missing"]} missing.{ladder_bad}
The judges' blind copies lie in <code>.agent-workspace/ladder-judge/blind/</code>: {LADDER["blind_count"]} images, whose list of digests hashes to <code>{LADDER["blind_digest"]}</code>. The review folders' {LADDER["folder_ok"] + LADDER["folder_bad"]} images, checked against each run key's digests: {LADDER["folder_ok"]} match, {LADDER["folder_bad"]} do not.</li>
<li><b>No viewing step's report.</b> Each review read the 1600 × 900 copies the judges ranked, with no frames and no viewing step's report, so no check measured any image, and <b>no text's size was compared with its medium's minimum on any image</b> (DEC-046 point 8). That holds for every image on this page.</li>
</ul>

<h3>What the runs' coordinators recorded</h3>
<ul>
<li>Four reviews in runs 1 and 2 were refused at the harness's limit on agents and sent again. A refusal at that limit starts no review, so it counts as no retry.</li>
<li>Run 1's coordinator recorded one of them, XGRM, as a retry in its <code>log.md</code>.</li>
<li>The coordinators recorded no review as failed in any run.</li>
{logs}
</ul>

<h3>What each review read before grading</h3>
<ul>
<li><b>Outside its own folder, the capability's rule sets and its design knowledge,</b> the reviews list the capability's review schemas (<code>schemas/review.yaml</code>, <code>schemas/review.schema.json</code>), read for the report's form: {len(schemas)} of 60 list them in <code>read-before-grading</code>. Of the {len(noschemas)} that do not, {sum(1 for x in noschemas if x["schemas-prose"])} name the schemas only in the report's prose after the document ({e(", ".join(f"run {x['run']} {x['code']}" for x in noschemas if x["schemas-prose"])) or "none"}), and {sum(1 for x in noschemas if not x["schemas-prose"])} name them nowhere ({e(", ".join(f"run {x['run']} {x['code']}" for x in noschemas if not x["schemas-prose"])) or "none"}). No other file outside the review's own folder, the two rule sets and the design knowledge is listed, but the one below.</li>
<li>One report lists project-kit's <code>tech-docs/rule-sets/</code>, searched for an inherit line: {e(", ".join(f"run {x['run']} {x['code']} ({deck_label(x['deck'])})" for x in techdocs)) or "none"}.</li>
<li><code>analyse.py</code>'s own check, reviews that list the brief's file or an earlier report before grading: {e(next((h.split(": ", 1)[1] for h in REC["head"] if h.startswith("reviews that list the brief")), "?"))}.</li>
</ul>
<details><summary>Each review's own list, as its document gives it</summary>
<div class="tw"><table class="readlist"><thead><tr><th>Run</th><th>Code</th><th>Deck</th><th>Beyond its folder</th><th>read-before-grading</th></tr></thead><tbody>{read_rows}</tbody></table></div>
</details>

<h3>How this page was made</h3>
<ul>
<li><code>run/analyse.py</code> (the plan's) computes every condition and per-rule reading, through <a href="readings.py"><code>.agent-workspace/calibration/report/readings.py</code></a>, which writes the two readings.</li>
<li><a href="build_report.py"><code>.agent-workspace/calibration/report/build_report.py</code></a> builds this page, and computes what the plan asks for that <code>analyse.py</code> does not: each design's verdict and grades in each run, from the deck <code>analyse.py</code> scores it in; the same image's verdict in each other deck within a run; the review's place on each page, by <code>analyse.py</code>'s own score over the page's ten designs, ties sharing a place; the marks; the judges' grades read from their files; the models and reads; the digests checked above.</li>
<li>The review grades each page once, for both its images, so each grade below stands for the light and the dark image alike, and no mark compares light with dark.</li>
<li>{"No review marked any grade, <i>need</i> or <i>the asker" + chr(39) + "s</i>, in any run, so the verdict left no grade out." if MARK_COUNT == 0 else f"The reviews marked {MARK_COUNT} grades in all; each card names its own, and the verdict leaves each out."}</li>
</ul>
</section>"""  # noqa: E501 — each paragraph of the page's HTML is one line


# --- A, the conditions ----------------------------------------------------------------------------


def matrix_table(R: dict, strict: bool = False) -> str:
    strength = {
        "RS-COMM-003": "tested, thin: one pair, one grade a run",
        "RS-GRAPHIC-001": "clean",
        "RS-GRAPHIC-002": "clean, base contested by judge 1",
        "RS-GRAPHIC-003": "clean",
        "RS-GRAPHIC-006": "clean",
        "RS-GRAPHIC-007": "clean for an added difference",
    }
    rows = ""
    for rule, cells in R["matrix"].items():
        label = (
            "<b>For the bar</b>"
            if rule == "For the bar"
            else f"<a href='#rule-{e(rule)}'>{e(rule)}</a>"
        )
        st = "" if rule == "For the bar" else e(strength.get(rule, ""))
        rows += (
            f"<tr><td>{label}</td><td class='muted'>{st}</td>"
            + "".join(f"<td>{met(c)}</td>" for c in cells)
            + "</tr>"
        )
    cap = "Strict reading: as the reports stand" if strict else "Recovered reading"
    return (
        f"<div class='tw'><table class='matrix'><caption>{cap}</caption><thead><tr><th>Rule</th>"
        f"<th>Strength (plan section 1)</th>"
        "<th>1 order</th><th>2 pass line</th><th>3 stability</th><th>4 weak deck</th></tr></thead>"
        f"<tbody>{rows}</tbody></table></div>"
    )


def his_place(p: int, code: str) -> str:
    return ordinal(ref["pages"][str(p)]["order"].index(code) + 1)


def a_section() -> str:
    roles = ["first-draft", "last-failed", "first-passed", "last-polished"]
    # condition 1
    rows = ""
    for place in ["1", "2", "3", "4", "deck"]:
        cp = ref["counterparts"][place]
        codes = " · ".join(
            f"{r.replace('-', ' ')}: <b>{e(cp[r] if place != 'deck' else deck_label(cp[r]))}</b>"
            for r in roles
        )
        if place == "deck":
            refplaces = "r1 fails · r4 fails · r5 passes · r5 passes"
        else:
            refplaces = " · ".join(f"{e(cp[r])} {his_place(int(place), cp[r])}" for r in roles)
        for i, n in enumerate(RUNS):
            c = REC["c1"][place][n]
            s = STR["c1"][place][n]
            rec = rec_any(place, cp, n)
            clauses = "<br>".join(
                f"{e(k)}: {'holds' if v else '<b>does not hold</b>'}"
                for k, v in c["clauses"].items()
            )
            ev = REC["c1ev"][place].get(n)
            evs = f"tau-b {ev[1]}; pairs kept {ev[2]}% (over {ev[0]} designs)" if ev else "—"
            pl = PLACES[(n, int(place))] if place != "deck" else {}
            review_places = "<br>".join(
                f"{e(cp[r] if place != 'deck' else deck_label(cp[r]))}"
                f"{' ' + pl[cp[r]] if pl else ''} "
                f"<span class='muted'>({score_text(c['scores'][r])})</span>"
                for r in roles
            )
            rows += "<tr>"
            if i == 0:
                rows += (
                    f"<td rowspan='3'><b>"
                    f"{'Page ' + place if place != 'deck' else 'The deck'}</b><br><span "
                    f"class='small'>{codes}</span></td><td rowspan='3' class='small'>"
                    f"{refplaces}</td>"
                )
            rows += (
                f"<td>run {n}{rec}</td><td class='small'>{review_places}</td><td class='small'>"
                f"{clauses}</td>"
                f"<td class='small'>{evs}</td><td>{met(c['met'])}</td><td>{met(s['met'])}</td></tr>"
            )
    c1 = (
        "<div class='tw'><table class='cond'><thead><tr><th>Page or deck, its counterparts</th><th>"
        "Reference's place</th><th>Run</th>"
        "<th>Each counterpart: the review's place by weak grades (unmarked covered grades below "
        "competent · competent · excellent)</th><th>Clauses</th><th>Evidence: tau-b, his pairs "
        "kept</th>"
        "<th>Recovered</th><th>Strict</th></tr></thead><tbody>" + rows + "</tbody></table></div>"
        f"<p>Condition 1 for the bar: recovered {met(REC['bar'][1])}; strict {met(STR['bar'][1])}. "
        f"The review's place is over the page's ten designs (TXF included), ties sharing a place; "
        f"the deck's counterparts are compared by <code>analyse.py</code>'s deck score, whose "
        f"counts the cell gives.</p>"
    )
    # condition 2
    rows = ""
    for place in ["1", "2", "3", "4", "deck"]:
        cp = ref["counterparts"][place]
        for i, n in enumerate(RUNS):
            c = REC["c2"][place][n]
            s = STR["c2"][place][n]
            rec = rec_any(place, cp, n)
            rows += "<tr>"
            if i == 0:
                lf = cp["last-failed"] if place != "deck" else deck_label(cp["last-failed"])
                fp = cp["first-passed"] if place != "deck" else deck_label(cp["first-passed"])
                rows += (
                    f"<td rowspan='3'><b>{'Page ' + place if place != 'deck' else 'The deck'}</b>"
                    f"</td>"
                    f"<td rowspan='3'>last failed <b>{e(lf)}</b> {refchip('fail')}<br>first passed "
                    f"<b>{e(fp)}</b> {refchip('pass')}</td>"
                )
            lfm = big("") if c["lfv"] != "fail" else ""
            fpm = big("") if c["fpv"] != "pass" else ""
            rows += (
                f"<td>run {n}{rec}</td><td>{vchip(c['lfv'], lfm)}</td><td>"
                f"{vchip(c['fpv'], fpm)}</td>"
                f"<td>{met(c['met'])}</td><td>{vchip(s['lfv'])} / {vchip(s['fpv'])} "
                f"{met(s['met'])}</td></tr>"
            )
    c2 = (
        "<div class='tw'><table class='cond'><thead><tr><th>Page or deck</th><th>Reference</th><th>"
        "Run</th><th>Last failed</th>"
        "<th>First passed</th><th>Recovered</th><th>Strict</th></tr></thead><tbody>"
        + rows
        + "</tbody></table></div>"
        f"<p>Condition 2 for the bar: recovered {met(REC['bar'][2])}; strict "
        f"{met(STR['bar'][2])}.</p>"
    )
    # false passes and fails
    rows = ""
    for n in RUNS:
        for kind in ("fp", "ff"):
            items = REC["fpff"][n][kind]
            by: dict = {}
            for it in items:
                k = it.split(" ", 1)[0]
                by.setdefault(k, []).append(it)
            cells = "".join(
                f"<td>{len(by.get(k, []))}<br><span class='small'>"
                f"{e('; '.join(by.get(k, [])))}</span></td>"
                for k in ("p1", "p2", "p3", "p4", "deck")
            )
            rows += (
                f"<tr><td>run {n}</td><td>"
                f"{'false passes' if kind == 'fp' else 'false fails'}</td><td><b>{len(items)}</b>"
                f"</td>{cells}</tr>"
            )
    fpff = (
        "<h4>The verdict against his pass line on every version with a reading (answer 13, "
        "counting toward no acceptance)</h4>"
        "<div class='tw'><table class='cond'><thead><tr><th>Run</th><th></th><th>All</th><th>Page "
        "1</th><th>Page 2</th><th>Page 3</th><th>Page 4</th><th>Deck</th></tr></thead><tbody>"
        + rows
        + "</tbody></table></div>"
        "<p class='small'>Recovered reading. A page design counts once for each deck it stands in. "
        "In the strict reading the reviews that give no verdict count in neither list: see <a "
        "href='readings-strict.md'>readings-strict.md</a>.</p>"
    )
    # condition 3
    rows = ""
    for place in ["1", "2", "3", "4", "deck"]:
        a, b, unstable = REC["c3"][place]
        sa, sb, sun = STR["c3"][place]
        what = "images" if place != "deck" else "deck versions"
        rows += (
            f"<tr><td><b>{'Page ' + place if place != 'deck' else 'The deck'}</b></td><td>{a} of "
            f"{b} {what}</td>"
            f"<td class='small'>{e(unstable or '—')}</td><td>{met(not unstable)}</td>"
            f"<td>{sa} of {sb} {met(not sun)}</td></tr>"
        )
    within = "".join(f"<li>{e(w)}</li>" for w in WITHIN) or "<li>none</li>"
    c3 = (
        "<div class='tw'><table class='cond'><thead><tr><th>Page or deck</th><th>One verdict in "
        "every run and every deck</th>"
        "<th>Where not: (run, verdict)</th><th>Recovered</th><th>Strict</th></tr></thead><tbody>"
        + rows
        + "</tbody></table></div>"
        f"<p>Within one run, the same image's verdict in each deck it stands in differs here "
        f"(computed by <code>build_report.py</code>, recovered reading):</p><ul class='small'>"
        f"{within}</ul>"
        f"<p>Condition 3 for the bar: recovered {met(REC['bar'][3])}; strict {met(STR['bar'][3])}. "
        f"Each rule's own stability is in its row of the matrix below and in C.</p>"
    )
    # condition 4
    weak = ref["weak-deck"]
    rows = ""
    for n in RUNS:
        c = REC["c4"][n]
        s = STR["c4"][n]
        rec = rec_mark(n, weak["deck"])
        cells = "".join(
            "<td>"
            f"{vchip(c['pages'].get(code), big('') if c['pages'].get(code) != 'fail' else '')}"
            "</td>"
            for code in weak["pages"].values()
        )
        rows += (
            f"<tr><td>run {n}{rec}</td>{cells}<td>"
            f"{vchip(c['deck'], big('') if c['deck'] != 'fail' else '')}</td><td>"
            f"{met(c['met'])}</td><td>{met(s['met'])}</td></tr>"
        )
    heads = "".join(
        f"<th>Page {p}: {e(code)} ({his_place(int(p), code)}, fails)</th>"
        for p, code in weak["pages"].items()
    )
    c4 = (
        f"<div class='tw'><table class='cond'><thead><tr><th>Run</th>{heads}<th>Its deck "
        f"(fails)</th><th>Recovered</th><th>Strict</th></tr></thead><tbody>"
        + rows
        + "</tbody></table></div>"
        f"<p>Condition 4 for the bar: recovered {met(REC['bar'][4])}; strict "
        f"{met(STR['bar'][4])}.</p>"
    )
    return f"""
<section id="a">
<h2>A. The conditions</h2>
<p>Each condition is read for the bar on each page and on the deck, and holds only where it holds on all five in every run (answer 7). <b>Recovered</b> is the reading this page shows; <b>strict</b> is the run as its reports stand. <sup class="rec">‡</sup> marks a run where a review this row reads has a document that does not parse.</p>
<h3 id="c1">Condition 1, order</h3>{c1}
<h3 id="c2">Condition 2, the pass line</h3>{c2}{fpff}
<h3 id="c3">Condition 3, stability</h3>{c3}
<h3 id="c4">Condition 4, the weak deck fails</h3>{c4}
<h3 id="matrix">The covered rules against the four conditions</h3>
{matrix_table(REC)}
{matrix_table(STR, strict=True)}
<p class="small">Each rule's row reads: 1, the variant below the base on the rule in every run (test c); 2, tests a and b in every run, and no unmarked grade below professional on a design the reference passes; 3, the rule on one side of professional on each image across the runs and decks; 4, the rule below professional on <code>main</code> where both judges grade it so.</p>
</section>"""  # noqa: E501 — each paragraph of the page's HTML is one line


def rec_any(place: str, cp: dict, n: int) -> str:
    decks = {r if place == "deck" else home[(int(place), r)] for r in cp.values()}
    if any(runs[n][d]["recovered"] for d in decks):
        return (
            '<sup class="rec" title="a review this row reads has a document that does not '
            'parse">‡</sup>'
        )
    return ""


# --- B, each version page by page -----------------------------------------------------------------

PAGE_TITLES = {1: "an order of levels", 2: "a mapping", 3: "a flow", 4: "a session and code"}


def card(p: int, code: str) -> str:
    hd = home[(p, code)]
    ds = decks_of[(p, code)]
    in_decks = deck_label(hd) if len(ds) == 1 else f"{deck_label(hd)} (in {len(ds)} decks)"
    if code in ("VNH", "BRS", "MCM"):
        in_decks = "r2 = r3"
    hv = his_verdict(p, code)
    hp = his_place(p, code)
    note = ""
    if code in ref["pages"][str(p)]["out"]:
        note = " — no reading: it fails only on the layering rule, which no bar covers (question 2)"
    elif hv == "none":
        note = " — no reading: he failed it by its own rule, off the bar"
    j = {}
    for k in (1, 2):
        jj = judges[k]["pages"][str(p)].get(code, {})
        j[k] = f"{e(jj.get('rank', '?'))} · {e(jj.get('overall', '?'))}"
    # verdict row
    verdicts = {n: rv(n, hd).page_verdict(p) for n in RUNS}
    vcells = ""
    for n in RUNS:
        m = big("") if hv in ("pass", "fail") and verdicts[n] != hv else ""
        vcells += f"<td>{vchip(verdicts[n], m)}</td>"
    vrow_mark = big("R") if len(set(verdicts.values())) > 1 else ""
    places = "".join(f"<td>{PLACES[(n, p)][code]}</td>" for n in RUNS)
    # grade rows
    grows = ""
    for group, rules in (
        ("covered", COVERED_PAGE),
        ("off", [r for r in RULES if r not in covered]),
    ):
        if group == "off":
            grows += "<tr class='grp'><th colspan='7'>Off the bar</th></tr>"
        for rule in rules:
            j1, j2 = jgrade(1, p, code, rule), jgrade(2, p, code, rule)
            gs = {n: page_grade(n, hd, p, rule) for n in RUNS}
            cells = ""
            for n in RUNS:
                g = gs[n]
                v = g[0] if g else None
                mk = ""
                if group == "covered" and v is not None:
                    which = [
                        str(k)
                        for k, jv in ((1, j1), (2, j2))
                        if jv is not None and side(jv) != side(v)
                    ]
                    if which:
                        mk = big("J" + ",".join(which))
                    elif any(jv is not None and jv != v for jv in (j1, j2)):
                        mk = small()
                ng = not_graded(n, hd, p, rule) if v is None else None
                cells += (
                    f"<td>{chip(v, mk, title=('not graded: ' + ng) if ng else 'not graded')}</td>"
                )
            vals = [gs[n][0] for n in RUNS if gs[n]]
            rm = ""
            if group == "covered" and vals:
                if len({side(x) for x in vals}) > 1:
                    rm = big("R")
                elif len(set(vals)) > 1:
                    rm = small()
            cls = "cov" if group == "covered" else "off"
            grows += (
                f"<tr class='{cls}'><th>{e(rule)}</th><td>{chip(j1)}</td><td>{chip(j2)}</td>"
                f"{cells}<td>{rm}</td></tr>"
            )
    run_heads = "".join(f"<th>Run {n}{rec_mark(n, hd)}</th>" for n in RUNS)
    # same image elsewhere
    others = [d for d in ds if d != hd]
    extra = ""
    if others or (hd == "rounds/round-5"):
        rows = ""
        listing = ds + ([ORDER_VARIANT] if hd == "rounds/round-5" else [])
        for d in listing:
            pp = VARIANT_PAGE_OF[p] if d == ORDER_VARIANT else p
            label = deck_label(d) + (" (home)" if d == hd else "")
            if d == ORDER_VARIANT:
                label += (
                    f", as its page {pp}: not this image, round 5's page with its footer's "
                    f"number changed; analyse.py does not count it"
                )
            cells = ""
            for n in RUNS:
                v = rv(n, d).page_verdict(pp)
                m = big("") if d != hd and d != ORDER_VARIANT and v != verdicts[n] else ""
                letters = ""
                for rule in COVERED_PAGE:
                    g = rv(n, d).pages[pp].get(rule)
                    gh = rv(n, hd).pages[p].get(rule)
                    t = LETTER[g[0]] if g else "–"
                    if d != hd and g and gh and side(g[0]) != side(gh[0]):
                        t = f"<b class='dm'>{t}◆</b>"
                    elif d != hd and g and gh and g[0] != gh[0]:
                        t = f"<b>{t}</b>{small()}"
                    letters += t + " "
                cells += (
                    f"<td>{vchip(v, m)}{rec_mark(n, d)}<br><span class='mono'>{letters}</span></td>"
                )
            rows += f"<tr><td>{e(label)}</td>{cells}</tr>"
        extra = (
            f"<details><summary>The same image in the other decks it stands in, run by "
            f"run</summary>"
            f"<div class='tw'><table class='same'><thead><tr><th>Deck</th><th>Run 1</th><th>Run "
            f"2</th><th>Run 3</th></tr></thead><tbody>{rows}</tbody></table></div>"
            f"<p class='small'>Letters: the covered page rules in order "
            f"{', '.join(r.replace('RS-GRAPHIC-', '') for r in COVERED_PAGE)}; B below competent, "
            f"C competent, P professional, E excellent. ◆ marks a verdict, or a grade's side, that "
            f"differs from the home deck's in the same run.</p></details>"
        )
    found = [(n, m) for n in RUNS for m in marks_of(n, hd, p)]
    if found:
        marks = (
            "Marked grades, each left out of the verdict: "
            + "; ".join(
                f"run {n} {e(m.get('rule'))} {e(m['mark'].get('kind'))} "
                f"({e(m['mark'].get('names'))})"
                for n, m in found
            )
            + "."
        )
    else:
        marks = "Marked grades: none in any run, so the verdict left nothing out."
    recs = [n for n in RUNS if runs[n][hd]["recovered"]]
    recnote = ""
    if recs:
        recnote = (
            f"<p class='small'><sup class='rec'>‡</sup> In run{'s' if len(recs) > 1 else ''} "
            f"{', '.join(map(str, recs))} this deck's review "
            f"({', '.join(runs[n][hd]['code'] for n in recs)}) has a document that does not parse; "
            f"its grades are read with its evidence line quoted. As the report stands, it gives no "
            f"verdict.</p>"
        )
    return f"""
<article class="card" id="p{p}-{code}">
<header><h4>Page {p} · {e(code)} · {e(in_decks)}</h4><span class="where">{e(", ".join(deck_label(d) for d in ds))}</span></header>
<div class="imgs">{img(p, code, "light")}{img(p, code, "dark")}</div>
<div class="who">
<div><span class="lbl">Maintainer</span> {hp} · {refchip(hv)}{e(note)}</div>
<div><span class="lbl">Judge 1</span> {j[1]}</div>
<div><span class="lbl">Judge 2</span> {j[2]}</div>
</div>
<div class="tw"><table class="grades">
<thead><tr><th></th><th>J1</th><th>J2</th>{run_heads}<th>Runs</th></tr></thead>
<tbody>
<tr class="vrow"><th>Verdict</th><td colspan="2">his: {refchip(hv)}</td>{vcells}<td>{vrow_mark}</td></tr>
<tr class="prow"><th>Place, by weak grades</th><td colspan="2">his: {hp}</td>{places}<td></td></tr>
{grows}
</tbody></table></div>
<p class="small">{marks} One grade a page stands for both its images.</p>
{recnote}
{extra}
</article>"""  # noqa: E501 — each paragraph of the page's HTML is one line


def b_section() -> str:
    out = [
        "<section id='b'><h2>B. Each version, page by page</h2>",
        "<p>The cards run in the maintainer's order, best first, with his pass line read on the "
        "bar's rules (plan section 0) drawn between them. Each card's verdict and grades are the "
        "review of the deck <code>analyse.py</code> scores the design in (its round, for a round's "
        "page); the other decks it stands in are under the card.</p>",
        "<p class='legend'><b>Marks.</b> ◆ a difference that counts: on a verdict, it differs from "
        "his pass line; on a grade, it falls on the other side of professional from the judge "
        "named (J1, J2); in the Runs column, the runs disagree on the verdict or a grade's side "
        "(R). ◇ a smaller difference: another grade on the same side as a judge's, or as another "
        "run's. Marks are set on the covered rules only. — not graded (hover for the review's "
        "reason). <sup class='rec'>‡</sup> the review's document does not parse.</p>",
    ]
    for p in range(1, 5):
        pl = ref["pages"][str(p)]
        out.append(f"<h3 id='page-{p}'>Page {p}, {PAGE_TITLES[p]}</h3>")
        if p == 1:
            out.append(
                "<p class='small'>His pass line as a whole fell after VNH (<code>"
                "maintainer-ranking.md</code>). Read on the bar's rules, VNH fails RS-GRAPHIC-001 "
                "(question 1, row 5), so the line below falls after GPM.</p>"
            )
        last_pass = max(pl["order"].index(c) for c in pl["pass"])
        for i, code in enumerate(pl["order"]):
            out.append(card(p, code))
            if i == last_pass:
                out.append(
                    "<div class='passline'><span>his pass line, on the bar's rules: above passes, "
                    "below fails</span></div>"
                )
        out.append(
            "<p class='small'>Left out: the anchors, real slides of other content (answer 18).</p>"
        )
    out.append("</section>")
    return "\n".join(out)


# --- C, each rule's own evidence ------------------------------------------------------------------

CORROBORATE = {
    "RS-COMM-003": (
        "Judged on the piece only. Thin: one pair, and one grade a run. It is confounded with "
        "RS-COMM-002's piece part, which is off the bar.",
        "The ladder cannot break it on one page: the variant moves round 5's page 4 to second "
        "place and changes only the footers' numbers. The move also puts the session's detail "
        "before two pages of the big picture, which RS-COMM-002 judges too (manifest).",
    ),
    "RS-GRAPHIC-001": (
        "Side effect: losing the mark also drops emphasis, which RS-GRAPHIC-007 reads. Elsewhere: "
        "the maintainer agrees with judge 1 that VNH, page 1's round 2, is below professional here "
        "(question 1, row 5).",
        "Varied on one page, by one pair (answer 6).",
    ),
    "RS-GRAPHIC-002": (
        'Base contested: judge 1 grades ZKD competent here, since the "Kind" head sits off the '
        "icons' edge; the maintainer holds it professional (question 1, row 3). Corroborating, not "
        "clean: VVL (page 4, form, the steps reversed), for the part on steps joined in reading "
        "order, which no variant varies alone.",
        "Varied on one page, by one pair (answer 6).",
    ),
    "RS-GRAPHIC-003": (
        'The maintainer reads the "your scene" tag on LTV and GPM as RS-COMM-004 (rows 8 and 9), '
        "so the base passes on this rule. Side effect: the decoration also covers words, so "
        "RS-GRAPHIC-001 and -007 drop in the judges' grades.",
        "Varied on one page, by one pair (answer 6).",
    ),
    "RS-GRAPHIC-006": (
        "Side effect: losing the names also moves RS-GRAPHIC-007 and -002.",
        "The variant removes the kinds' names from the rows, since the name is the other signal; "
        "the key under the table keeps the names readable, by colour alone (manifest).",
    ),
    "RS-GRAPHIC-007": (
        "The other half, a difference the content has but the form drops, is tested only by the "
        "form set against round 2, on all four pages. That set also moves RS-COMM-001 and "
        "RS-GRAPHIC-002, so it corroborates and is not clean.",
        "The variant adds a difference the content lacks (hues on an order); it does not drop one "
        "the content has (manifest).",
    ),
}
CORR_ROWS = {
    "RS-GRAPHIC-001": [(1, "VNH")],
    "RS-GRAPHIC-002": [(4, "VVL")],
    "RS-GRAPHIC-007": [
        (1, "RWC"),
        (1, "VNH"),
        (2, "TNZ"),
        (2, "BRS"),
        (3, "XPD"),
        (3, "CKM"),
        (4, "VVL"),
        (4, "MCM"),
    ],
}


def rule_row(rule: str, p: int, code: str, role: str, deck: str | None = None) -> str:
    d = deck or home[(p, code)]
    j1, j2 = jgrade(1, p, code, rule), jgrade(2, p, code, rule)
    cells = ""
    for n in RUNS:
        g = rv(n, d).pages[p].get(rule)
        cells += f"<td>{chip(g[0] if g else None)}{rec_mark(n, d)}</td>"
    hv = his_verdict(p, code)
    return (
        f"<tr><td>{e(role)}</td><td><a href='#p{p}-{e(code)}'>{e(code)}</a> (page {p}, "
        f"{e(deck_label(d))})</td>"
        f"<td>{his_place(p, code)} · {refchip(hv)}</td><td>{chip(j1)}</td><td>{chip(j2)}</td>"
        f"{cells}</tr>"
    )


def c_section() -> str:
    out = [
        "<section id='c'><h2>C. Each covered rule's own evidence</h2>",
        "<p>Each covered rule has one pair, round 5's page (the base) against the variant that "
        "changes it in what the rule judges. The review grades each page once for both its images, "
        "so the one grade stands for both modes. The readings are quoted from <code>"
        "analyse.py</code>'s output, recovered and strict.</p>",
    ]
    for rule in ref["bar"]["covers"]:
        pair = ref["pairs"][rule]
        corr, fixed = CORROBORATE[rule]
        if pair["on"] == "piece":
            imgs = (
                "<div class='strips'><figure><img loading='lazy' "
                "src='../../ladder-judge/blind/deck-order/order-A.png' alt='Strip A, round 5 in "
                "its order'><figcaption>Strip A: round 5, pages 1, 2, 3, 4 (the base)</figcaption>"
                "</figure>"
                "<figure><img loading='lazy' src='../../ladder-judge/blind/deck-order/order-B.png' "
                "alt='Strip B, the order variant'><figcaption>Strip B: the variant, round 5's "
                "pages 1, 4, 2, 3</figcaption></figure></div>"
            )
            rows = ""
            for role, d, s in (("base", pair["base"], "A"), ("variant", pair["variant"], "B")):
                cells = "".join(
                    f"<td>{chip((rv(n, d).piece.get(rule) or (None,))[0])}{rec_mark(n, d)}</td>"
                    for n in RUNS
                )
                rows += (
                    f"<tr><td>{role}</td><td>strip {s}: {e(deck_label(d))}</td><td>"
                    f"{'in order' if s == 'A' else 'not in order'} (question 3)</td>"
                    f"<td>{chip(judges[1]['deck'].get(s))}</td><td>"
                    f"{chip(judges[2]['deck'].get(s))}</td>{cells}</tr>"
                )
        else:
            p = int(pair["on"])
            imgs = (
                f"<div class='pair'><div><p class='lbl'>Base: {e(pair['base'])} (round 5)</p><div "
                f"class='stack'>{img(p, pair['base'], 'light')}{img(p, pair['base'], 'dark')}</div>"
                f"</div>"
                f"<div><p class='lbl'>Variant: {e(pair['variant'])} "
                f"({e(deck_label(pair['variant-deck']))})</p><div class='stack'>"
                f"{img(p, pair['variant'], 'light')}{img(p, pair['variant'], 'dark')}</div></div>"
                f"</div>"
            )
            rows = rule_row(rule, p, pair["base"], "base") + rule_row(
                rule, p, pair["variant"], "variant", pair["variant-deck"]
            )
        corr_rows = "".join(
            rule_row(
                rule,
                p_,
                c_,
                "corroborating"
                if rule != "RS-GRAPHIC-007"
                else ("form set" if c_ in ("RWC", "TNZ", "XPD", "VVL") else "round 2"),
            )
            for p_, c_ in CORR_ROWS.get(rule, [])
        )
        weak_rows = ""
        if ref["weak-deck-by-rule"][rule]:
            for p_, c_ in ref["weak-deck"]["pages"].items():
                if c_ in ref["weak-deck-by-rule"][rule]:
                    weak_rows += rule_row(rule, int(p_), c_, "main, both judges below professional")
        rec_lines = "".join(f"<li>{e(x)}</li>" for x in REC["rules"][rule])
        str_lines = "".join(f"<li>{e(x)}</li>" for x in STR["rules"][rule])
        mrow = REC["matrix"][rule]
        srow = STR["matrix"][rule]
        cond = "".join(
            f"<td>{met(a)}</td><td class='muted'>{met(b)}</td>"
            for a, b in zip(mrow, srow, strict=False)
        )
        out.append(f"""
<article class="card rule" id="rule-{e(rule)}">
<header><h3>{e(rule)}</h3><span class="where">{"the piece" if pair["on"] == "piece" else "page " + pair["on"]}</span></header>
{imgs}
<div class="tw"><table class="grades"><thead><tr><th>Role</th><th>Design</th><th>Reference</th><th>J1</th><th>J2</th><th>Run 1</th><th>Run 2</th><th>Run 3</th></tr></thead>
<tbody>{rows}{corr_rows}{weak_rows}</tbody></table></div>
<div class="tw"><table class="matrix"><thead><tr><th colspan="2">1 order</th><th colspan="2">2 pass line</th><th colspan="2">3 stability</th><th colspan="2">4 weak deck</th></tr>
<tr><th>recovered</th><th>strict</th><th>recovered</th><th>strict</th><th>recovered</th><th>strict</th><th>recovered</th><th>strict</th></tr></thead><tbody><tr>{cond}</tr></tbody></table></div>
<h4>The readings, recovered</h4><ul class="small">{rec_lines}</ul>
<details><summary>The readings, strict</summary><ul class="small">{str_lines}</ul></details>
<p><b>Corroborating, and side effects:</b> {e(corr)}</p>
<p><b>What the ladder holds fixed of the rule:</b> {e(fixed)}</p>
</article>""")  # noqa: E501 — each paragraph of the page's HTML is one line
    out.append("</section>")
    return "\n".join(out)


# --- D, the decks ---------------------------------------------------------------------------------


def deck_rows(decks: list[str]) -> str:
    rows = ""
    for d in decks:
        refv = deck_ref(d)
        pverd = {n: rv(n, d).piece_verdict() for n in RUNS}
        unstable = len(set(pverd.values())) > 1
        for i, n in enumerate(RUNS):
            r = rv(n, d)
            cells = ""
            for p in range(1, 5):
                code = runs[n][d]["entry"]["pages"][str(p)]["image"]
                v = r.page_verdict(p)
                hv = his_verdict(p, code) if code else "none"
                m = big("") if hv in ("pass", "fail") and v != hv else ""
                cells += (
                    f"<td>{vchip(v, m)}<br><span class='small'>"
                    f"{e(code or 'as ' + runs[n][d]['entry']['pages'][str(p)]['as'])}</span></td>"
                )
            pg = ""
            strip = {"rounds/round-5": "A", ORDER_VARIANT: "B"}.get(d)
            c3 = [(rv(k, d).piece.get("RS-COMM-003") or (None,))[0] for k in RUNS]
            for rule in ("RS-COMM-003", "RS-COMM-002", "RS-GRAPHIC-004"):
                g = r.piece.get(rule)
                mk = ""
                if rule == "RS-COMM-003" and g:
                    if strip:
                        js = [(k, judges[k]["deck"].get(strip)) for k in (1, 2)]
                        which = [
                            str(k) for k, jv in js if jv is not None and side(jv) != side(g[0])
                        ]
                        if which:
                            mk = big("J" + ",".join(which))
                        elif any(jv is not None and jv != g[0] for _, jv in js):
                            mk = small()
                    if len({side(x) for x in c3 if x is not None}) > 1:
                        mk += big("R")
                    elif len({x for x in c3 if x is not None}) > 1:
                        mk += small()
                pg += f"<td>{chip(g[0] if g else None, mk)}</td>"
            m = big("") if refv in ("pass", "fail") and pverd[n] != refv else ""
            rows += "<tr>"
            if i == 0:
                rows += (
                    f"<td rowspan='3'><b>{e(deck_label(d))}</b><br><span class='small'>"
                    f"{e(d)}</span></td><td rowspan='3'>{refchip(refv)}</td>"
                )
            rows += (
                f"<td>run {n}{rec_mark(n, d)} <span class='small'>"
                f"{e(runs[n][d]['code'])}</span></td>{cells}{pg}<td>{vchip(pverd[n], m)}</td><td>"
                f"{big('R') if unstable and i == 0 else ''}</td></tr>"
            )
    return rows


DECK_ORDER = [
    "rounds/round-1",
    "rounds/round-2",
    "rounds/round-3",
    "rounds/round-4",
    "rounds/round-5",
    "sets/capability-main",
    *sorted(d for d in VERSIONS if d.startswith("variants/")),
]


def d_section() -> str:
    head = (
        "<thead><tr><th>Deck</th><th>Reference</th><th>Run</th><th>Page 1</th><th>Page 2</th><th>"
        "Page 3</th><th>Page 4</th>"
        "<th>RS-COMM-003 (covered)</th><th>RS-COMM-002 (off)</th><th>RS-GRAPHIC-004 (off)</th><th>"
        "Piece verdict</th><th>Runs</th></tr></thead>"
    )
    return f"""
<section id="d"><h2>D. The decks</h2>
<p>Each deck version's four page verdicts and its piece-wide grades in each run. The review grades three rules on the piece; RS-COMM-003 is the only one the bar covers. The piece's verdict is set against the reference's: only round 5 and the RS-GRAPHIC-004 deck pass. ◆ marks a verdict that differs from the reference (a page's from his pass line on that page), and R runs that disagree on the piece's verdict. On RS-COMM-003, ◆J1 or ◆J2 marks a grade on the other side of professional from that judge's grade of strip A (round 5) or strip B (the order variant), ◆R runs that put the deck on different sides, and ◇ a smaller difference. The grey and form sets are in E.</p>
<div class="tw"><table class="decks">{head}<tbody>{deck_rows(DECK_ORDER)}</tbody></table></div>
</section>"""  # noqa: E501 — each paragraph of the page's HTML is one line


# --- E, outside the conditions --------------------------------------------------------------------


def e_section() -> str:
    head = (
        "<thead><tr><th>Deck</th><th>Reference</th><th>Run</th><th>Page 1</th><th>Page 2</th><th>"
        "Page 3</th><th>Page 4</th>"
        "<th>RS-COMM-003 (covered)</th><th>RS-COMM-002 (off)</th><th>RS-GRAPHIC-004 (off)</th><th>"
        "Piece verdict</th><th>Runs</th></tr></thead>"
    )
    links = []
    for d in ("sets/grey-boxes", "sets/form-contradicts"):
        codes = [runs[1][d]["entry"]["pages"][str(p)]["image"] for p in range(1, 5)]
        links.append(
            f"{deck_label(d)}: "
            + ", ".join(
                f"<a href='#p{p}-{c}'>page {p} {c}</a>"
                for p, c in zip(range(1, 5), codes, strict=False)
            )
        )
    noread = []
    for p in range(1, 5):
        pl = ref["pages"][str(p)]
        for c in pl["no-reading"] + pl["out"]:
            noread.append(f"<a href='#p{p}-{c}'>{c}</a> (page {p}, {e(deck_label(home[(p, c)]))})")
    return f"""
<section id="e"><h2>E. Outside the conditions</h2>
<p>The <code>grey</code> and <code>form</code> sets lie outside the series and enter no condition (plan section 2); they are reported apart. Each page of each is a card in B, in his order: {"; ".join(links)}.</p>
<div class="tw"><table class="decks">{head}<tbody>{deck_rows(["sets/grey-boxes", "sets/form-contradicts"])}</tbody></table></div>
<p>The <code>form</code> set also corroborates RS-GRAPHIC-007's other half and RS-GRAPHIC-002's steps in reading order (VVL); C shows those rows.</p>
<p>Versions with no reading, reported and in no condition: {", ".join(noread)}; and the decks <code>variants/RS-COMM-001</code>, <code>-002</code>, <code>-004</code>, <code>-005</code> and <code>variants/RS-GRAPHIC-005</code>, whose rows are in D.</p>
<p>The anchors, five real slides of other content, are left out of every run (answer 18).</p>
</section>"""  # noqa: E501 — each paragraph of the page's HTML is one line


CSS = """
:root{--bg:#f7f6f2;--fg:#1c1c1a;--muted:#5d5c57;--line:#d9d6cc;--card:#ffffff;--soft:#efede6;--accent:#24527a;
--dm:#b0281b;--sm:#7a5a00;--g1bg:#f6d4cf;--g1fg:#7d1a10;--g2bg:#f6e6bf;--g2fg:#5f4300;--g3bg:#d3ead5;--g3fg:#1e5a26;--g4bg:#cfe0f2;--g4fg:#173f66;
--pass:#1e5a26;--passbg:#d3ead5;--fail:#7d1a10;--failbg:#f6d4cf;--alertbg:#fff4e5;--alertline:#d08a1a;}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--bg:#151514;--fg:#e9e7e1;--muted:#a3a198;--line:#3a3934;--card:#1e1e1c;--soft:#262623;--accent:#8db8e0;
--dm:#ff8a7a;--sm:#e2c46a;--g1bg:#5a1f19;--g1fg:#ffd2cb;--g2bg:#4f3f12;--g2fg:#f6e2a8;--g3bg:#1f4526;--g3fg:#c9ebcd;--g4bg:#1b3a5a;--g4fg:#cfe3f7;
--pass:#c9ebcd;--passbg:#1f4526;--fail:#ffd2cb;--failbg:#5a1f19;--alertbg:#33270f;--alertline:#c98a2a;}}
:root[data-theme="dark"]{--bg:#151514;--fg:#e9e7e1;--muted:#a3a198;--line:#3a3934;--card:#1e1e1c;--soft:#262623;--accent:#8db8e0;
--dm:#ff8a7a;--sm:#e2c46a;--g1bg:#5a1f19;--g1fg:#ffd2cb;--g2bg:#4f3f12;--g2fg:#f6e2a8;--g3bg:#1f4526;--g3fg:#c9ebcd;--g4bg:#1b3a5a;--g4fg:#cfe3f7;
--pass:#c9ebcd;--passbg:#1f4526;--fail:#ffd2cb;--failbg:#5a1f19;--alertbg:#33270f;--alertline:#c98a2a;}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:1240px;margin:0 auto;padding:16px}
h1{font-size:1.6rem;margin:.4em 0 .2em}h2{font-size:1.3rem;margin:2em 0 .6em;padding-top:.6em;border-top:2px solid var(--line)}
h3{font-size:1.1rem;margin:1.6em 0 .5em}h4{font-size:1rem;margin:0}
a{color:var(--accent)}code,.mono{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.88em}
nav{position:sticky;top:0;z-index:5;background:var(--bg);border-bottom:1px solid var(--line);padding:8px 0;display:flex;flex-wrap:wrap;gap:4px 14px;font-size:.9rem}
.sub{color:var(--muted);margin-top:0}
.small{font-size:.85rem}.muted{color:var(--muted)}
.tw{overflow-x:auto;margin:.6em 0}
table{border-collapse:collapse;font-size:.88rem;background:var(--card)}
th,td{border:1px solid var(--line);padding:4px 7px;text-align:left;vertical-align:top}
thead th{background:var(--soft);font-weight:600}
caption{text-align:left;font-weight:600;padding:4px 0}
.g{display:inline-block;min-width:3.6em;text-align:center;border-radius:3px;padding:0 4px;font-size:.82rem}
.g0{color:var(--muted)}.g1{background:var(--g1bg);color:var(--g1fg);font-weight:600}.g2{background:var(--g2bg);color:var(--g2fg)}
.g3{background:var(--g3bg);color:var(--g3fg)}.g4{background:var(--g4bg);color:var(--g4fg)}
.v{display:inline-block;border-radius:3px;padding:0 5px;font-size:.82rem}
.vp{background:var(--passbg);color:var(--pass)}.vf{background:var(--failbg);color:var(--fail);font-weight:700}.vn{border:1px dashed var(--line);color:var(--muted)}
.dm{color:var(--dm);font-weight:700;margin-left:2px}.sm{color:var(--sm);margin-left:2px}
.met{color:var(--pass);font-weight:600}.nmet{color:var(--dm);font-weight:700}.nc{color:var(--muted)}
sup.rec{color:var(--sm);font-weight:700}
.alert{background:var(--alertbg);border-left:4px solid var(--alertline);padding:8px 16px;margin:1em 0}
.card{background:var(--card);border:1px solid var(--line);border-radius:6px;padding:12px 14px;margin:14px 0}
.card header{display:flex;flex-wrap:wrap;justify-content:space-between;gap:4px 12px;align-items:baseline;margin-bottom:8px}
.where{color:var(--muted);font-size:.82rem}
.imgs{display:grid;grid-template-columns:1fr 1fr;gap:8px}
figure{margin:0}figure img{width:100%;height:auto;display:block;border:1px solid var(--line)}
figcaption{font-size:.78rem;color:var(--muted)}
.pair{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.stack{display:grid;gap:8px}
table.decks td{white-space:nowrap}
.strips{display:grid;gap:10px}
.who{display:flex;flex-wrap:wrap;gap:4px 20px;margin:8px 0;font-size:.9rem}
.lbl{font-weight:600;color:var(--muted);margin-right:4px}
table.grades th{white-space:nowrap}
tr.grp th{background:var(--soft);font-weight:500;color:var(--muted);font-size:.8rem}
tr.off th,tr.off td{opacity:.75}
tr.vrow th,tr.prow th{font-weight:600}
.passline{position:relative;margin:22px 0;border-top:3px dashed var(--dm);text-align:center}
.passline span{position:relative;top:-.8em;background:var(--bg);padding:0 10px;color:var(--dm);font-weight:700;font-size:.85rem}
.legend{font-size:.85rem;background:var(--soft);padding:8px 10px;border-radius:4px}
ul.reads{margin:0;padding-left:1.1em}
blockquote{margin:.3em 0 .3em 1em;padding-left:8px;border-left:3px solid var(--line);white-space:pre-wrap;font-size:.85rem}
details{margin:.5em 0}summary{cursor:pointer;color:var(--accent)}
@media (max-width:640px){.imgs,.pair{grid-template-columns:1fr}main{padding:16px}}
"""  # noqa: E501 — the page's CSS, written out as the page carries it


def page() -> str:
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Graphic-design review calibration</title>
<style>{CSS}</style></head>
<body><main>
<h1>The first held-out calibration of the graphic-design review</h1>
<p class="sub">project-kit#3230 · three runs over the held-out ladder, read against the maintainer's ranking, by the plan committed before the first run. For the maintainer to judge.</p>
<nav><a href="#head">Head</a><a href="#a">A. Conditions</a><a href="#matrix">Rule matrix</a><a href="#b">B. Versions</a><a href="#page-1">p1</a><a href="#page-2">p2</a><a href="#page-3">p3</a><a href="#page-4">p4</a><a href="#c">C. Rules</a><a href="#d">D. Decks</a><a href="#e">E. Outside</a></nav>
{head_section()}
{a_section()}
{b_section()}
{c_section()}
{d_section()}
{e_section()}
</main></body></html>
"""  # noqa: E501 — each paragraph of the page's HTML is one line


if __name__ == "__main__":
    (OUT / "index.html").write_text(page())
    print(f"wrote {OUT / 'index.html'}")
