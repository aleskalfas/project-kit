#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml==0.19.1",
# ]
# ///
"""lean-business capability — estimate: what the idea's goal asks of a variant, worked out
through the customer factory from the canvas's inputs (lean-business DEC-002 point 4).

Read-only. The numbers are worked out each time and never stored: the active customers
needed, the customers lost and won each year, the leads needed, and the active customers
each year on the way, for each side that pays. The capability's README gives the formulas.
Whether a number is within reach is the person's judgement, at the viability step.

Usage:
  pkit lean estimate <variant>

Exit codes:
  0  shown
  1  refused: the canvas or the goal cannot be read, or the idea has no goal
  2  usage
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))

from _lib import acting, canvases, estimates
from _lib.acting import Context
from _lib.writes import Refused


def parser() -> argparse.ArgumentParser:
    made = argparse.ArgumentParser(
        prog="pkit lean estimate",
        description="Work out what the idea's goal asks of a variant. Read-only; nothing is "
        "stored.",
    )
    made.add_argument("variant", help="The variant's id, `<idea>--<variant>`.")
    return made


def run(args: argparse.Namespace, ctx: Context) -> None:
    canvas, goal = canvases.read_variant(ctx.root, str(args.variant))
    if goal is None:
        raise Refused(
            "the estimate works from the idea's goal, and the idea has none: `pkit lean "
            "set-goal` sets it"
        )
    found = estimates.estimate(canvas, goal)
    if found is None:
        raise Refused("the idea's goal gives no yearly revenue or no years to reach it in")
    ctx.say(f"The estimate for `{canvas.get('id')}`, worked out now and stored nowhere.")
    for line in estimates.lines(found):
        ctx.say(line)


def main() -> int:
    return acting.main(parser(), run, date.today())


if __name__ == "__main__":
    sys.exit(main())
