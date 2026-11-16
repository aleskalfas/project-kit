#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "jsonschema==4.26.0",
#   "referencing==0.37.0",
#   "ruamel.yaml==0.19.1",
# ]
# ///
"""visual-communication capability — verdict: the verdict against the project's bar, from a
round's review report, and whether it ends the designer's loop (DEC-042 points 1, 9 and 10).

It reads the document the round's review opens its report with, as its dispatcher kept it
alone in the clone's local folder, and the bar, from the capability's configuration. It
says whether each page meets the bar, and whether the piece does, and names each unmarked
grade that fails it, each marked grade it leaves out, and the rules the bar covers
(`verdicts`). Anyone gives the same verdict again from the same report.

It then says whether the verdict ends the designer's loop: only where a calibration's
report is accepted, the bar covers only rules with evidence of their own in it, and nothing
the accepted data names has lapsed (`calibration`). Where it ends no loop, or no verdict is
given, it says why, and the loop ends as DEC-030 point 2 says. It starts nothing: a lapse
only withdraws the hold, and a new calibration is a person's to start.

Usage:
  pkit visual verdict <piece>                 the verdict on the highest round kept
  pkit visual verdict <piece> --round <n>     the verdict on round <n>
  pkit visual verdict --json <piece>          the same as one JSON document, with the
                                              reading the hold was compared on

Exit codes:
  0  answered: a verdict, or why none is given, whether or not it ends the loop
  1  refused: no report is kept, it or the configuration cannot be read, the report is of
     another piece or round, or the configuration holds a bar its schema refuses or the
     capability's check fails
  2  usage error
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))

from _lib import verdicts
from _lib.root import project_root


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="pkit visual verdict",
        description="Give the verdict against the project's bar from a round's review report.",
    )
    parser.add_argument("piece", help="the piece's name, as its reports are kept under")
    parser.add_argument(
        "--round", type=_round, help="the round whose report to read; the highest kept by default"
    )
    parser.add_argument("--json", action="store_true", help="print one JSON document")
    args = parser.parse_args()
    try:
        answered = verdicts.answer(project_root(), args.piece, args.round)
    except verdicts.Refused as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(answered.as_data(), ensure_ascii=False, indent=2))
    else:
        for line in report(answered):
            print(line)
    return 0


def report(answered: verdicts.Answer) -> list[str]:
    """What the command prints, a line each."""
    lines = [f"report: round {answered.round} of `{answered.piece}`, in {answered.report}"]
    if answered.bar is None:
        lines.append("bar: none")
    else:
        covers = ", ".join(answered.bar["covers"])
        lines.append(f"bar: at least {answered.bar['at-least']} on {covers}")
        lines.append(f"rules covered: {', '.join(answered.rules)}")
    verdict = answered.verdict
    if verdict is None:
        lines.append("verdict: none")
    else:
        lines.append(f"verdict: the piece {_meets(verdict.meets)} the bar")
        for page in verdict.pages:
            lines.append(f"  page `{page.page}`: {_meets(page.meets)} the bar")
            lines.extend(f"    {_failing(each)}" for each in page.failing)
        lines.append(f"  the piece as a whole: {_meets(not verdict.whole)} the bar")
        lines.extend(f"    {_failing(each)}" for each in verdict.whole)
        lines.extend(
            f"  left out, marked `{each.mark}`: {each.rule}, {each.grade}, on {each.place}"
            for each in verdict.marked
        )
    if answered.ends_the_loop:
        lines.append(
            "ends the loop: yes, the designer's loop runs to this bar, within the accepted "
            "calibration (DEC-042 points 9 and 10)"
        )
    else:
        informs = ", the verdict informs" if verdict is not None else ""
        lines.append(f"ends the loop: no{informs}")
        lines.extend(f"  {why}" for why in answered.why)
    return lines


def _meets(meets: bool) -> str:
    return "meets" if meets else "fails"


def _failing(grade: verdicts.Grade) -> str:
    return f"{grade.rule}, {grade.grade}: {grade.evidence}"


def _round(text: str) -> int:
    try:
        number = int(text)
    except ValueError:
        number = 0
    if number < 1:
        raise argparse.ArgumentTypeError(f"`{text}` is no round: a round is a whole number from 1")
    return number


if __name__ == "__main__":
    sys.exit(main())
