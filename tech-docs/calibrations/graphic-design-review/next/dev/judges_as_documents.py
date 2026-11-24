# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Write the first ladder's two outside judges' grades as judge documents, so `analyse.py` can
run its control on the development set (project-kit#3397).

Usage, from the repository's root:

    uv run --script judges_as_documents.py <ladder-judge> <reference.json> <out>

It writes `<out>/keys/judge-<n>.json` and `<out>/reports/judge-<n>/<CODE>.yaml`, in the form
`layout.py` and `judge.schema.json` give them: judge 1 from `judge-1-fable.md`, judge 2 from
`judge-2-opus.md`. It is the development set's adapter alone, and changes no grade.

What the first ladder's judges gave, and so what these documents hold:

- **Each image graded once, side by side,** and not each version alone. An image takes the
  judge's grades in every deck it stands in.
- **No words.** The judges named no passage of a rule behind any grade, so no grade carries
  `words`, and no per-rule reference below professional can stand on them.
- **RS-COMM-003 on two decks alone:** order A, round 5's deck, and order B, the order variant.
  No other deck's piece is graded, so each other deck's piece has no reading.
- **A covered rule a judge left ungraded on a page** is listed as not graded there: their brief
  had them leave out a rule the page gave no evidence on.
- **No folder and no digest.** The judges were handed the blind copies and their brief, never
  a version's folder, so the keys record nothing handed.
"""

import json
import re
import sys
from pathlib import Path

JUDGES = [("judge-1", "judge-1-fable.md", "fable"), ("judge-2", "judge-2-opus.md", "opus")]
WORDS = ("below competent", "competent", "professional", "excellent")
GRADE = r"(below competent|competent|professional|excellent)"
ORDER_VARIANT = "variants/RS-COMM-003"
ORDER_A = "rounds/round-5"


def rule_grades(path: Path) -> dict[str, dict[str, str]]:
    """Each blind code's grades, rule by rule, from a judge's "Rule grades" lists."""
    out: dict[str, dict[str, str]] = {}
    raw: dict[str, str] = {}
    for line in path.read_text().splitlines():
        found = re.match(r"^- ([A-Z]{3}): (.*)$", line.strip())
        if not found:
            continue
        code, rest = found.groups()
        raw[code] = rest
        grades = {}
        for part in rest.split(";"):
            each = re.match(rf"\s*(RS-[A-Z]+-\d{{3}}) {GRADE}", part)
            if each:
                grades[each.group(1)] = each.group(2)
        if not grades:  # "RS-COMM-001, 002, 004, 005 and RS-GRAPHIC-001, 002, ... professional"
            last = re.search(rf"{GRADE}\s*$", rest)
            if last and "RS-GRAPHIC" in rest:
                comm, graphic = rest.split("RS-GRAPHIC-", 1)
                for n in re.findall(r"\b(\d{3})\b", comm):
                    grades[f"RS-COMM-{n}"] = last.group(1)
                for n in re.findall(r"\b(\d{3})\b", graphic):
                    grades[f"RS-GRAPHIC-{n}"] = last.group(1)
        out[code] = grades
    for code, rest in raw.items():  # "as TLG but RS-GRAPHIC-005 competent"
        found = re.match(r"as ([A-Z]{3}) but (.*)$", rest)
        if found:
            grades = dict(out[found.group(1)])
            for part in found.group(2).split(";"):
                each = re.match(rf"\s*(RS-[A-Z]+-\d{{3}}) {GRADE}", part)
                if each:
                    grades[each.group(1)] = each.group(2)
            out[code] = grades
    return out


def order_grades(path: Path) -> dict[str, str]:
    out = {}
    for line in path.read_text().splitlines():
        found = re.match(rf"^- (?:Order |order-)([AB]): RS-COMM-003 {GRADE}", line.strip())
        if found:
            out[found.group(1)] = found.group(2)
    if sorted(out) != ["A", "B"]:
        sys.exit(f"error: {path} grades RS-COMM-003 on no two orders")
    return out


def main() -> None:
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    judge_dir, reference, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    ref = json.loads(reference.read_text())
    ids = ref["page-ids"]
    page_rules = [rule for rule in ref["bar"]["covers"] if "page" in ref["places"][rule]]
    key = json.loads((judge_dir / "key.json").read_text())

    decks: dict[str, dict[int, str]] = {}
    for page, codes in key["pages"].items():
        for code, versions in codes.items():
            for version in versions:
                if not version.startswith("anchor"):
                    decks.setdefault(version, {})[int(page)] = code
    for version, order in ref["orders"].items():
        decks[version] = {n: decks[ORDER_A][shown] for n, shown in enumerate(order, 1)}

    for judge, file_name, model in JUDGES:
        grades = rule_grades(judge_dir / file_name)
        orders = order_grades(judge_dir / file_name)
        folder = out / "reports" / judge
        folder.mkdir(parents=True, exist_ok=True)
        run_key: dict = {"run": judge, "folders": {}}
        for i, version in enumerate(sorted(decks), 1):
            code = f"J{judge[-1]}{i:02d}"
            order = ref["orders"].get(version, list(range(1, len(ids) + 1)))
            page_ids = [ids[shown - 1] for shown in order]
            pages = {}
            for n in range(1, len(ids) + 1):
                image = None if version in ref["orders"] else decks[version][n]
                pages[str(n)] = {"id": page_ids[n - 1], "image": image}
            run_key["folders"][code] = {"version": version, "pages": pages}
            doc_grades, not_graded = [], []
            for n in range(1, len(ids) + 1):
                shown = decks[version][n]
                for rule, word in sorted(grades[shown].items()):
                    doc_grades.append(
                        {
                            "rule": rule,
                            "on": {"page": page_ids[n - 1]},
                            "grade": word,
                            "evidence": f"The judge's grade of {shown}, graded side by side.",
                        }
                    )
                for rule in page_rules:
                    if rule not in grades[shown]:
                        not_graded.append(
                            {
                                "rule": rule,
                                "on": {"page": page_ids[n - 1]},
                                "why": "The judge gave none: the page gave it no evidence.",
                            }
                        )
            which = {ORDER_A: "A", ORDER_VARIANT: "B"}.get(version)
            if which:
                doc_grades.append(
                    {
                        "rule": "RS-COMM-003",
                        "on": {"piece": True},
                        "grade": orders[which],
                        "evidence": f"The judge's grade of order {which}.",
                    }
                )
            doc = {
                "judge": judge,
                "folder": code,
                "model": {"name": model},
                "read": [
                    {"kind": "images", "what": "The blind copies, as the first judges' brief lets"},
                    {"kind": "rule-sets", "what": "comm.md and graphic.md, as that brief lets"},
                ],
                "grades": doc_grades,
                "not-graded": not_graded,
            }
            (folder / f"{code}.yaml").write_text(json.dumps(doc, indent=1) + "\n")
        keys = out / "keys"
        keys.mkdir(parents=True, exist_ok=True)
        (keys / f"{judge}.json").write_text(json.dumps(run_key, indent=2) + "\n")
        print(f"{judge}: {len(decks)} documents from {file_name}")


if __name__ == "__main__":
    main()
