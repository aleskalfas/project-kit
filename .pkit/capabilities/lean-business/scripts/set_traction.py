#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml==0.19.1",
# ]
# ///
"""lean-business capability — set-traction: give a variant its traction target: the yearly
growth multiplier and the first stage's target (lean-business DEC-002 point 4).

Content, so it asks nothing and records no who or when. `--multiplier` is how many times
the traction grows each year toward the goal, ten where none is given. The first stage's
target is a step of the customer factory and the number it reaches there, given together.
`--clear` removes the traction target whole.

A change to what a standing verdict judged is warned of, never refused, naming each
judgement it leaves stale.

Usage:
  pkit lean set-traction <variant> [--multiplier <n>]
                         [--first-stage-metric <factory step> --first-stage-target <n>]
  pkit lean set-traction <variant> --clear

Exit codes:
  0  written
  1  refused: nothing was written
  2  usage
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))

from _lib import acting, canvases, editing, writes
from _lib.acting import Context
from _lib.writes import Refused


def parser() -> argparse.ArgumentParser:
    made = argparse.ArgumentParser(
        prog="pkit lean set-traction",
        description="Give a variant its traction target: the yearly growth multiplier and the "
        "first stage's target.",
    )
    made.add_argument("variant", help="The variant's id, `<idea>--<variant>`.")
    made.add_argument("--multiplier", type=float, help="Above 1; ten where none is given.")
    made.add_argument("--first-stage-metric", choices=canvases.FACTORY_STEPS)
    made.add_argument("--first-stage-target", type=float, help="Above 0.")
    made.add_argument("--clear", action="store_true", help="Remove the traction target whole.")
    return made


def run(args: argparse.Namespace, ctx: Context) -> None:
    setting = [args.multiplier, args.first_stage_metric, args.first_stage_target]
    if args.clear and any(value is not None for value in setting):
        raise Refused("--clear removes the traction target whole, and takes no other flag")
    if not args.clear and all(value is None for value in setting):
        raise Refused("give --multiplier, the first stage's metric and target, or --clear")
    if (args.first_stage_metric is None) != (args.first_stage_target is None):
        raise Refused("the first stage's target is a metric and a number, given together")
    multiplier = editing.number(args.multiplier) if args.multiplier is not None else None
    target = (
        editing.number(args.first_stage_target) if args.first_stage_target is not None else None
    )
    if multiplier is not None and multiplier <= 1:
        raise Refused("--multiplier is above 1: the traction grows each year")
    if target is not None and target <= 0:
        raise Refused("--first-stage-target is above 0")
    files = writes.Files(ctx.root, writes.for_writing(ctx.root))
    canvas = canvases.open_variant(files, str(args.variant))
    if args.clear:
        if "traction" not in canvas.data:
            raise Refused(f"`{canvas.id}` has no traction target to clear")
        del canvas.data["traction"]
    else:
        traction = canvas.data.get("traction")
        if not isinstance(traction, dict):
            traction = editing.mapping()
            editing.place(canvas.data, "traction", traction, canvases.ORDER)
        order = ("multiplier", "first-stage")
        if multiplier is not None:
            editing.place(traction, "multiplier", multiplier, order)
        if args.first_stage_metric is not None:
            stage = editing.mapping(
                [
                    ("metric", args.first_stage_metric),
                    ("target", target),
                ]
            )
            editing.place(traction, "first-stage", stage, order)
    files.put(canvas.rel, canvas.doc)
    acting.content(
        ctx, files, f"{'Cleared' if args.clear else 'Set'} the traction target of `{canvas.id}`."
    )


def main() -> int:
    return acting.main(parser(), run, date.today())


if __name__ == "__main__":
    sys.exit(main())
