# /// script
# requires-python = ">=3.10"
# dependencies = ["ruamel.yaml==0.19.1"]
# ///
"""Read the calibration's review reports and compute each condition and each rule's reading.

Usage:

    uv run --script analyse.py <reference.json> <judge-key.json> <keys-dir> <reports-dir> [<out.md>]

<reference.json>  the reference fixed before the run (`reference.json` beside this script)
<judge-key.json>  the judges' key, `ladder-judge/key.json`: which deck each blind image stands in
<keys-dir>        the run keys `layout.py` wrote, `run-<n>.json`
<reports-dir>     `run-<n>/<CODE>.yaml` (the review's document alone) or `run-<n>/<CODE>.md`
                  (the whole report, whose first fenced YAML block is the document)

What it computes, as plan.md section 2 fixes it:

- **The verdict,** as `pkit visual verdict` gives it (outputs.md, "The verdict"): a page meets the
  bar where each unmarked grade on a covered rule is professional or above, the piece where every
  page does and each unmarked grade it takes as a whole does. A covered rule the report neither
  grades nor lists as not graded gives no verdict.
- **The order,** by counting weak grades (answer 8): fewer unmarked below-competent grades on the
  covered rules rank higher, then fewer competent, then more excellent. An ungraded rule counts in
  none. A page design is scored in the deck the judges' key names first for it (its round, for a
  round's page). A deck is scored over its pages' and its piece's grades.
- **Conditions 1 to 3** on each page and on the deck, met only where met on all five in every run
  (answer 7); **condition 4** on each page of the weak deck and on its deck, in every run \
(answer 11).
- **Each covered rule's readings** (answer 12): its pair, its grades on the designs the reference
  passes, its side of professional across the runs, and its grades on the weak deck.

The review grades each page once, for both its images, so a reading "on both modes" reads that one
grade. A pair's test reads a grade whether or not it is marked (plan.md section 1). The readings of
the pass line leave a marked grade out, as the verdict does.
"""

import json
import re
import sys
from itertools import combinations
from pathlib import Path

from ruamel.yaml import YAML

VAL = {"below competent": 1, "competent": 2, "professional": 3, "excellent": 4}
WORD = {v: k for k, v in VAL.items()}
PRO = 3


def load_doc(path: Path) -> dict:
    text = path.read_text()
    if path.suffix == ".md":
        m = re.search(r"```ya?ml\n(.*?)```", text, re.S)
        if not m:
            sys.exit(f"error: {path} holds no fenced YAML document")
        text = m.group(1)
    return YAML(typ="safe").load(text)


class Review:
    """One review of one deck version in one run."""

    def __init__(self, doc: dict, entry: dict, covered: set[str]):
        self.version = entry["version"]
        by_id = {p["id"]: int(n) for n, p in entry["pages"].items()}
        self.image = {int(n): p["image"] for n, p in entry["pages"].items()}
        self.pages: dict[int, dict[str, tuple[int, bool]]] = {n: {} for n in range(1, 5)}
        self.piece: dict[str, tuple[int, bool]] = {}
        self.ruled: set[str] = set()
        self.model = doc.get("model", {})
        self.read = [r.get("kind", "?") for r in doc.get("read-before-grading", [])]
        for g in doc.get("grades", []):
            self.ruled.add(g["rule"])
            value = (VAL[g["grade"]], "mark" in g)
            if g["on"].get("piece"):
                self.piece[g["rule"]] = value
            else:
                self.pages[by_id[g["on"]["page"]]][g["rule"]] = value
        for g in doc.get("not-graded", []):
            self.ruled.add(g["rule"])
        self.covered = covered
        self.missing = sorted(covered - self.ruled)

    def page_verdict(self, n: int) -> str | None:
        if self.missing:
            return None
        bad = [
            r
            for r, (v, marked) in self.pages[n].items()
            if r in self.covered and not marked and v < PRO
        ]
        return "fail" if bad else "pass"

    def piece_verdict(self) -> str | None:
        if self.missing:
            return None
        pages = [self.page_verdict(n) for n in range(1, 5)]
        bad = [
            r
            for r, (v, marked) in self.piece.items()
            if r in self.covered and not marked and v < PRO
        ]
        return "fail" if bad or "fail" in pages else "pass"

    def score(self, scope: list[dict[str, tuple[int, bool]]]) -> tuple[int, int, int]:
        vs = [
            v
            for grades in scope
            for r, (v, marked) in grades.items()
            if r in self.covered and not marked
        ]
        return (-vs.count(1), -vs.count(2), vs.count(4))

    def page_score(self, n: int):
        return self.score([self.pages[n]])

    def deck_score(self):
        return self.score([self.pages[n] for n in range(1, 5)] + [self.piece])

    def grade(self, rule: str, n: int | None) -> tuple[int, bool] | None:
        return self.piece.get(rule) if n is None else self.pages[n].get(rule)


def tau_b(xs, ys):
    c = d = tx = ty = 0
    for i, j in combinations(range(len(xs)), 2):
        a = (xs[i] > xs[j]) - (xs[i] < xs[j])
        b = (ys[i] > ys[j]) - (ys[i] < ys[j])
        if a == 0 and b == 0:
            continue
        if a == 0:
            tx += 1
        elif b == 0:
            ty += 1
        elif a == b:
            c += 1
        else:
            d += 1
    den = ((c + d + tx) * (c + d + ty)) ** 0.5
    return (c - d) / den if den else 0.0


def kept(review_scores, n_items):
    """The share of the reference's ordered pairs (best first) the review keeps strictly in
    order."""
    pairs = list(combinations(range(n_items), 2))
    return sum(1 for i, j in pairs if review_scores[i] > review_scores[j]) / len(pairs)


def mark(ok) -> str:
    return "no counterpart" if ok is None else ("met" if ok else "NOT MET")


def v(x) -> str:
    return "none" if x is None else x


def main() -> None:
    if len(sys.argv) not in (5, 6):
        sys.exit(__doc__)
    save = Path(sys.argv[5]) if len(sys.argv) == 6 else None
    ref = json.loads(Path(sys.argv[1]).read_text())
    jkey = json.loads(Path(sys.argv[2]).read_text())
    keys_dir, reports_dir = Path(sys.argv[3]), Path(sys.argv[4])
    covered = set(ref["bar"]["covers"])

    home = {}  # (page, code) -> the deck the image is scored in
    for p, codes in jkey["pages"].items():
        for code, sources in codes.items():
            decks = [s for s in sources if not s.startswith("anchor")]
            if decks:
                home[(int(p), code)] = decks[0]

    runs: dict[int, dict[str, Review]] = {}
    for kp in sorted(keys_dir.glob("run-*.json"), key=lambda q: int(q.stem.split("-")[1])):
        n = int(kp.stem.split("-")[1])
        key = json.loads(kp.read_text())
        runs[n] = {}
        for code, entry in key["folders"].items():
            found = [reports_dir / f"run-{n}" / f"{code}{ext}" for ext in (".yaml", ".md")]
            found = [f for f in found if f.exists()]
            if not found:
                sys.exit(f"error: no report for {code} ({entry['version']}) in run {n}")
            runs[n][entry["version"]] = Review(load_doc(found[0]), entry, covered)
    R = sorted(runs)
    out: list[str] = []
    say = out.append

    # --- the head ---------------------------------------------------------
    say("# The calibration's readings")
    say("")
    say(f"- bar: {sorted(covered)} at least {ref['bar']['at-least']}")
    say(
        f"- runs read: {len(R)} (the plan fixes {ref['runs']})"
        + ("" if len(R) == ref["runs"] else "  <-- not the plan's number")
    )
    models = {
        (r.model.get("name"), r.model.get("effort")) for run in runs.values() for r in run.values()
    }
    say(
        f"- models named: {sorted(models, key=str)}"
        + ("" if len(models) == 1 else "  <-- more than one")
    )
    breaches = sorted(
        {
            (n, r.version)
            for n in R
            for r in runs[n].values()
            if {"brief-file", "earlier-reports"} & set(r.read)
        }
    )
    say(
        "- reviews that list the brief's file or an earlier report before grading: "
        f"{breaches or 'none'}"
    )
    gaps = sorted(
        {(n, r.version, tuple(r.missing)) for n in R for r in runs[n].values() if r.missing}
    )
    say(f"- reviews that give no verdict, a covered rule left out: {gaps or 'none'}")
    say("")

    # --- condition 1, order ------------------------------------------------
    say("## Condition 1, order")
    say("")
    c1_all = True
    for place in ["1", "2", "3", "4", "deck"]:
        cp = ref["counterparts"][place]
        say(
            f"### {'The deck' if place == 'deck' else 'Page ' + place}: "
            + ", ".join(f"{k} {cp[k]}" for k in cp)
        )
        for n in R:
            if place == "deck":
                sc = {k: runs[n][cp[k]].deck_score() for k in cp}
                verdict = {k: runs[n][cp[k]].piece_verdict() for k in cp}
            else:
                p = int(place)
                sc = {k: runs[n][home[(p, cp[k])]].page_score(p) for k in cp}
                verdict = {k: runs[n][home[(p, cp[k])]].page_verdict(p) for k in cp}
            clauses = {}
            if cp["first-draft"] != cp["last-failed"]:
                clauses["first draft below last failed"] = sc["first-draft"] < sc["last-failed"]
            clauses["last failed below first passed"] = sc["last-failed"] < sc["first-passed"]
            if cp["first-passed"] != cp["last-polished"]:
                clauses["first passed about equal to last polished"] = (
                    verdict["first-passed"] == "pass" and verdict["last-polished"] == "pass"
                )
            ok = all(clauses.values())
            c1_all &= ok
            scores = "  ".join(f"{k} {sc[k]}" for k in cp)
            say(
                f"- run {n}: {mark(ok)}; "
                f"scores (-#below competent, -#competent, #excellent): {scores}"
            )
            for clause, held in clauses.items():
                say(f"  - {clause}: {'holds' if held else 'DOES NOT HOLD'}")
        if place != "deck":
            p = int(place)
            order = [c for c in ref["pages"][place]["order"] if c not in ref["pages"][place]["out"]]
            his = [-i for i in range(len(order))]
            for n in R:
                rs = [runs[n][home[(p, c)]].page_score(p) for c in order]
                say(
                    f"- run {n}, evidence over {len(order)} designs: tau-b {tau_b(rs, his):+.2f}; "
                    f"his ordered pairs kept in order {kept(rs, len(order)):.0%}"
                )
        say("")
    say(f"**Condition 1 for the bar: {mark(c1_all)}**")
    say("")

    # --- condition 2, the pass line -----------------------------------------
    say("## Condition 2, the pass line")
    say("")
    c2_all = True
    for place in ["1", "2", "3", "4", "deck"]:
        cp = ref["counterparts"][place]
        for n in R:
            if place == "deck":
                lf, fp = (
                    runs[n][cp["last-failed"]].piece_verdict(),
                    runs[n][cp["first-passed"]].piece_verdict(),
                )
            else:
                p = int(place)
                lf = runs[n][home[(p, cp["last-failed"])]].page_verdict(p)
                fp = runs[n][home[(p, cp["first-passed"])]].page_verdict(p)
            ok = lf == "fail" and fp == "pass"
            c2_all &= ok
            say(
                f"- {'the deck' if place == 'deck' else 'page ' + place}, run {n}: "
                f"last failed {cp['last-failed']} {v(lf)}, "
                f"first passed {cp['first-passed']} {v(fp)}: {mark(ok)}"
            )
    say("")
    say(f"**Condition 2 for the bar: {mark(c2_all)}**")
    say("")
    say(
        "Reported, counting toward no acceptance (answer 13): the verdict against the pass line "
        "on every version with a reading."
    )
    for n in R:
        fpass, ffail = [], []
        for version, r in sorted(runs[n].items()):
            for p in range(1, 5):
                code = r.image[p]
                if code is None:
                    continue
                pl = ref["pages"][str(p)]
                want = "pass" if code in pl["pass"] else "fail" if code in pl["fail"] else None
                got = r.page_verdict(p)
                if want and got and got != want:
                    (fpass if got == "pass" else ffail).append(f"p{p} {code} in {version}")
            want = (
                "pass"
                if version in ref["decks"]["pass"]
                else "fail"
                if version in ref["decks"]["fail"]
                else None
            )
            got = r.piece_verdict()
            if want and got and got != want:
                (fpass if got == "pass" else ffail).append(f"deck {version}")
        say(f"- run {n}: false passes {len(fpass)} {fpass}")
        say(f"  false fails {len(ffail)} {ffail}")
    say("")

    # --- condition 3, stability ----------------------------------------------
    say("## Condition 3, stability")
    say("")
    c3_all = True
    for place in ["1", "2", "3", "4"]:
        p = int(place)
        seen: dict[str, list[tuple[int, str, str | None]]] = {}
        for n in R:
            for version, r in runs[n].items():
                if r.image[p] is not None:
                    seen.setdefault(r.image[p], []).append((n, version, r.page_verdict(p)))
        unstable = {c: vs for c, vs in seen.items() if len({x[2] for x in vs}) > 1}
        c3_all &= not unstable
        unstable_text = (
            ""
            if not unstable
            else ": "
            + "; ".join(
                c + " " + str(sorted({(x[0], v(x[2])) for x in vs}))
                for c, vs in sorted(unstable.items())
            )
        )
        say(
            f"- page {place}: {len(seen) - len(unstable)} of {len(seen)} images "
            f"take one verdict in every run and every deck{unstable_text}"
        )
    decks = sorted(runs[R[0]])
    unstable_decks = [d for d in decks if len({runs[n][d].piece_verdict() for n in R}) > 1]
    c3_all &= not unstable_decks
    say(
        f"- the deck: {len(decks) - len(unstable_decks)} of {len(decks)} deck versions "
        "take one piece verdict in every run"
        f"{'' if not unstable_decks else ': ' + ', '.join(unstable_decks)}"
    )
    say("")
    say(f"**Condition 3 for the bar: {mark(c3_all)}**")
    say("")

    # --- condition 4, the weak deck -------------------------------------------
    say("## Condition 4, the weak deck fails")
    say("")
    weak = ref["weak-deck"]
    c4_all = True
    for n in R:
        r = runs[n][weak["deck"]]
        pages = {p: r.page_verdict(int(p)) for p in weak["pages"]}
        ok = all(x == "fail" for x in pages.values()) and r.piece_verdict() == "fail"
        c4_all &= ok
        say(
            f"- run {n}: "
            + ", ".join(f"{weak['pages'][p]} {v(x)}" for p, x in pages.items())
            + f"; its deck {v(r.piece_verdict())}: {mark(ok)}"
        )
    say("")
    say(f"**Condition 4 for the bar: {mark(c4_all)}**")
    say("")

    # --- each covered rule ------------------------------------------------------
    say("## Each covered rule")
    say("")
    matrix = {}
    for rule in sorted(covered):
        pair = ref["pairs"][rule]
        on_piece = pair["on"] == "piece"
        say(f"### {rule}")
        # (a) the pair
        pair_ok, order_ok = True, True
        for n in R:
            if on_piece:
                b, va = (
                    runs[n][pair["base"]].grade(rule, None),
                    runs[n][pair["variant"]].grade(rule, None),
                )
            else:
                p = int(pair["on"])
                b = runs[n][home[(p, pair["base"])]].grade(rule, p)
                va = runs[n][pair["variant-deck"]].grade(rule, p)
            a_ok = b is not None and b[0] >= PRO
            b_ok = va is not None and va[0] < PRO
            c_ok = b is not None and va is not None and va[0] < b[0]
            pair_ok &= a_ok and b_ok and c_ok
            order_ok &= c_ok
            say(
                f"- pair, run {n}: base {pair['base']} {WORD.get(b[0]) if b else 'no grade'}"
                f"{' (marked)' if b and b[1] else ''}, "
                f"variant {pair['variant']} {WORD.get(va[0]) if va else 'no grade'}"
                f"{' (marked)' if va and va[1] else ''}: "
                f"(a) {'holds' if a_ok else 'FAILS'}, (b) {'holds' if b_ok else 'FAILS'}, "
                f"(c) {'holds' if c_ok else 'FAILS'}"
            )
        # (b) the designs the reference passes
        below = []
        for n in R:
            for version, r in runs[n].items():
                if on_piece:
                    if version in ref["decks"]["pass"]:
                        g = r.grade(rule, None)
                        if g and not g[1] and g[0] < PRO:
                            below.append(f"run {n} deck {version} {WORD[g[0]]}")
                else:
                    for p in range(1, 5):
                        code = r.image[p]
                        if code in ref["pages"][str(p)]["pass"]:
                            g = r.grade(rule, p)
                            if g and not g[1] and g[0] < PRO:
                                below.append(f"run {n} p{p} {code} in {version} {WORD[g[0]]}")
        say(
            f"- on what the reference passes, unmarked grades below professional: {len(below)}"
            + ("" if not below else " " + "; ".join(below[:12]) + (" …" if len(below) > 12 else ""))
        )
        # (c) one side of professional across the runs
        sides: dict[str, list[int]] = {}
        for n in R:
            for version, r in runs[n].items():
                if on_piece:
                    g = r.grade(rule, None)
                    if g:
                        sides.setdefault(version, []).append(g[0])
                else:
                    for p in range(1, 5):
                        g = r.grade(rule, p)
                        if g and r.image[p] is not None:
                            sides.setdefault(f"p{p} {r.image[p]}", []).append(g[0])
        crossing = sorted(k for k, gs in sides.items() if len({x >= PRO for x in gs}) > 1)
        exact = sum(1 for gs in sides.values() if len(set(gs)) == 1)
        spread = max((max(gs) - min(gs) for gs in sides.values()), default=0)
        say(
            f"- across runs and decks: one grade on {exact} of {len(sides)} "
            f"{'decks' if on_piece else 'images'}; "
            f"widest spread {spread} step(s); crossing professional: {crossing or 'none'}"
        )
        # (d) the weak deck
        listed = ref["weak-deck-by-rule"][rule]
        if listed:
            misses = []
            for n in R:
                r = runs[n][weak["deck"]]
                for p, code in weak["pages"].items():
                    if code in listed:
                        g = r.grade(rule, int(p))
                        if not (g and g[0] < PRO):
                            misses.append(f"run {n} {code} {WORD[g[0]] if g else 'no grade'}")
            weak_ok = not misses
            say(
                f"- on the weak deck, below professional on {listed}: {mark(weak_ok)}"
                + ("" if weak_ok else f" ({'; '.join(misses)})")
            )
        else:
            weak_ok = None
            say("- on the weak deck: no counterpart")
        matrix[rule] = {
            "1 order": order_ok,
            "2 pass line": pair_ok and not below,
            "3 stability": not crossing,
            "4 weak deck": weak_ok,
        }
        say("")

    say("## The covered rules against the four conditions")
    say("")
    say("| Rule | 1 order | 2 pass line | 3 stability | 4 weak deck |")
    say("|---|---|---|---|---|")
    for rule, cells in matrix.items():
        say(f"| {rule} | " + " | ".join(mark(x) for x in cells.values()) + " |")
    say(
        "| **For the bar** | "
        + " | ".join(mark(x) for x in (c1_all, c2_all, c3_all, c4_all))
        + " |"
    )
    text = "\n".join(out) + "\n"
    print(text, end="")
    if save:
        save.write_text(text)


if __name__ == "__main__":
    main()
