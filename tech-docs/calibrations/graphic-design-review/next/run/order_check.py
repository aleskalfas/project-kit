# /// script
# requires-python = ">=3.11"
# dependencies = ["jsonschema==4.26.0", "referencing==0.37.0", "ruamel.yaml==0.19.1"]
# ///
"""Check each method of ordering designs on a spread of grades like the review's, before the
plan fixes one (project-kit#3397).

Usage, from the repository's root:

    uv run --script order_check.py --reference R --blind-key K --judges KEYS REPORTS
        --runs KEYS REPORTS [--draws N] [--seed S] --out order-check.md --json order-check.json

`--judges` are the outside judges' documents and `--runs` the review's, both of the development
set, read as `analyse.py` reads them. The check takes the judges' grades as what each design is,
and asks which method keeps its order once the grades look like the review's.

- **The pairs.** On each page, a pair of designs one of which dominates the other in a judge's
  grades: at least as high on every covered rule both are graded on, and higher on one. Any
  method of ordering should rank the dominant design higher, so the pairs favour none of them,
  and the maintainer's order enters nowhere.
- **The spread.** The share of each grade among the review's unmarked covered grades on the
  pages, over every document with a reading.
- **The noise.** How often two runs of the review grade one image on one rule differently, in
  the image's home deck. Each draw moves each grade one step up or down at the rate that makes
  two draws differ that often.
- **Two scenarios,** each over `--draws` seeded draws: *review-like*, each judge's grades mapped
  onto the review's spread by their rank, ties broken at random, then the noise; and
  *as the judges*, each judge's own grades with the noise alone.
- **What each method gives** on each pair and draw: *kept*, the dominant design scores higher;
  *tied*; or *inverted*, the other scores higher.

The check's rule picks the method with the fewest inverted pairs in the review-like
scenario, then the most kept, and `counting`, the first plan's, where two are equal on both.
The plan fixes the method the calibration uses, with the check's result before it
(plan.md section 3).
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter
from itertools import combinations
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import analyse  # noqa: E402  (beside this file, and read after the path is set)

FIRST_PLAN = "counting"


def page_grades(ladder: analyse.Ladder, src: analyse.Source, ref: analyse.Reference) -> dict:
    """Each page's designs, with their unmarked grades on the covered page rules, read in each
    design's home deck. A design with no reading there is left out."""
    out: dict[str, dict[str, dict[str, int]]] = {}
    for page, design in sorted(ladder.home):
        reading, n = ladder.reading(src, page, design)
        if reading.gap(n):
            continue
        grades = {
            rule: grade.value
            for rule, grade in reading.pages[n].items()
            if rule in ref.page_rules and not grade.marked
        }
        if grades:
            out.setdefault(page, {})[design] = grades
    return out


def dominant_pairs(designs: dict[str, dict[str, int]]) -> list[tuple[str, str]]:
    """Each pair (higher, lower) where `higher` dominates `lower`."""
    pairs = []
    for a, b in combinations(sorted(designs), 2):
        both = designs[a].keys() & designs[b].keys()
        if not both:
            continue
        up = [designs[a][rule] - designs[b][rule] for rule in sorted(both)]
        if all(d >= 0 for d in up) and any(d > 0 for d in up):
            pairs.append((a, b))
        elif all(d <= 0 for d in up) and any(d < 0 for d in up):
            pairs.append((b, a))
    return pairs


def review_spread(runs: dict[str, analyse.Source], ref: analyse.Reference) -> Counter:
    spread: Counter = Counter()
    for src in runs.values():
        for reading in src.readings.values():
            for n in reading.ids:
                if reading.gap(n):
                    continue
                for rule, grade in reading.pages[n].items():
                    if rule in ref.page_rules and not grade.marked:
                        spread[grade.value] += 1
    return spread


def disagreement(
    ladder: analyse.Ladder, runs: dict[str, analyse.Source], ref: analyse.Reference
) -> tuple[int, int]:
    """How many pairs of runs grade one image on one rule differently, of all such pairs."""
    differ = total = 0
    for page, design in sorted(ladder.home):
        for rule in sorted(ref.page_rules):
            values = []
            for src in runs.values():
                grade = ladder.grade(src, page, design, rule)
                if grade is not None and not grade.marked:
                    values.append(grade.value)
            for a, b in combinations(values, 2):
                total += 1
                differ += a != b
    return differ, total


def mapped(grades: dict, spread: Counter, rng: random.Random) -> dict:
    """`grades` mapped onto `spread` by their rank: the lowest share of the judge's grades takes
    the review's lowest grade, and so on, ties broken at random."""
    flat = [
        (page, design, rule)
        for page in grades
        for design in grades[page]
        for rule in grades[page][design]
    ]
    flat.sort(key=lambda at: (grades[at[0]][at[1]][at[2]], rng.random()))
    total = sum(spread.values())
    edges, running = [], 0
    for value in sorted(spread):
        running += spread[value]
        edges.append((running / total, value))
    out: dict = {page: {design: {} for design in grades[page]} for page in grades}
    for i, (page, design, rule) in enumerate(flat):
        where = (i + 0.5) / len(flat)
        out[page][design][rule] = next(value for edge, value in edges if where <= edge)
    return out


def noisy(grades: dict, rate: float, rng: random.Random) -> dict:
    return {
        page: {
            design: {
                rule: min(4, max(1, value + rng.choice((-1, 1)))) if rng.random() < rate else value
                for rule, value in rules.items()
            }
            for design, rules in designs.items()
        }
        for page, designs in grades.items()
    }


def tally(grades: dict, pairs: dict, method: str) -> Counter:
    counts: Counter = Counter()
    for page, page_pairs in pairs.items():
        for higher, lower in page_pairs:
            a = analyse.METHODS[method](list(grades[page][higher].values()))
            b = analyse.METHODS[method](list(grades[page][lower].values()))
            counts["kept" if a > b else "tied" if a == b else "inverted"] += 1
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--blind-key", type=Path, required=True)
    parser.add_argument("--judges", type=Path, nargs=2, required=True, metavar=("KEYS", "REPORTS"))
    parser.add_argument("--runs", type=Path, nargs=2, required=True, metavar=("KEYS", "REPORTS"))
    parser.add_argument("--draws", type=int, default=500)
    parser.add_argument("--seed", type=int, default=3397)
    parser.add_argument("--root", type=Path, default=analyse.ROOT)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--json", type=Path, required=True)
    args = parser.parse_args()

    from jsonschema import Draft202012Validator

    schema = Draft202012Validator(json.loads((HERE / "judge.schema.json").read_text()))
    cap = analyse.Capability(args.root)
    ref = analyse.Reference(json.loads(args.reference.read_text()))
    ladder = analyse.Ladder(json.loads(args.blind_key.read_text()))
    judges = analyse.load_sources(*args.judges, "judge", "judge", ref, cap, schema)
    runs = analyse.load_sources(*args.runs, "run", "review", ref, cap, schema)

    spread = review_spread(runs, ref)
    differ, total = disagreement(ladder, runs, ref)
    between = differ / total if total else 0.0
    rate = 1 - (1 - between) ** 0.5
    found: dict = {
        "draws": args.draws,
        "seed": args.seed,
        "review spread": {analyse.WORD[v]: spread[v] for v in sorted(spread)},
        "between runs": {"differing": differ, "pairs": total, "rate per grade": rate},
        "judges": {},
        "methods": {},
    }
    truth = {name: page_grades(ladder, src, ref) for name, src in judges.items()}
    pairs = {
        name: {page: dominant_pairs(designs) for page, designs in grades.items()}
        for name, grades in truth.items()
    }
    for name, grades in truth.items():
        own: Counter = Counter(v for d in grades.values() for r in d.values() for v in r.values())
        found["judges"][name] = {
            "spread": {analyse.WORD[v]: own[v] for v in sorted(own)},
            "pairs": sum(len(p) for p in pairs[name].values()),
            "pairs by page": {page: len(p) for page, p in sorted(pairs[name].items())},
        }
    for method in analyse.METHODS:
        found["methods"][method] = {}
        for scenario in ("review-like", "as the judges"):
            rng = random.Random(f"{args.seed}/{method}/{scenario}")
            counts: Counter = Counter()
            for _ in range(args.draws):
                for name, grades in truth.items():
                    base = mapped(grades, spread, rng) if scenario == "review-like" else grades
                    counts += tally(noisy(base, rate, rng), pairs[name], method)
            whole = sum(counts.values()) or 1
            found["methods"][method][scenario] = {
                kind: counts[kind] / whole for kind in ("kept", "tied", "inverted")
            }

    def rank(method: str) -> tuple:
        shares = found["methods"][method]["review-like"]
        return (round(shares["inverted"], 4), -round(shares["kept"], 4), method != FIRST_PLAN)

    chosen = min(found["methods"], key=rank)
    found["chosen"] = chosen

    say = [
        "# The order's methods, checked on a spread like the review's",
        "",
        f"- {args.draws} draws a scenario, seed {args.seed}; the judges' pairs from "
        f"{len(judges)} judges' documents, the review's spread and noise from {len(runs)} runs' "
        f"({sum(len(src.readings) for src in runs.values())} documents).",
        f"- **The review's spread** on the covered page rules: {found['review spread']}.",
        f"- **Between runs,** {differ} of {total} pairs of runs grade an image on a rule "
        f"differently ({between:.1%}); each draw moves a grade at {rate:.1%}.",
    ]
    for name, d in found["judges"].items():
        say.append(
            f"- **{name}:** spread {d['spread']}; {d['pairs']} dominant pairs, by page "
            f"{d['pairs by page']}."
        )
    say += [
        "",
        "| Method | review-like: kept | tied | inverted | as the judges: kept | tied | inverted |",
        "|---|---|---|---|---|---|---|",
    ]
    for method, scenarios in found["methods"].items():
        cells = [
            f"{scenarios[s][kind]:.1%}"
            for s in ("review-like", "as the judges")
            for kind in ("kept", "tied", "inverted")
        ]
        say.append(f"| {method} | " + " | ".join(cells) + " |")
    say += [
        "",
        f"**The method the rule chooses:** `{chosen}`: the fewest inverted pairs in the "
        "review-like scenario, then the most kept, then the first plan's.",
        "",
    ]
    args.out.write_text("\n".join(say) + "\n")
    args.json.write_text(json.dumps(found, indent=1) + "\n")
    print(f"wrote {args.out} and {args.json}; chosen: {chosen}")


if __name__ == "__main__":
    main()
