#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml==0.19.1",
# ]
# ///
"""lean-business capability — change-plan: change a planned cycle's plan, before its window
starts (lean-business DEC-002 point 11; DEC-003 points 4 and 5).

The change is the person's act, so it takes their word, and records who changed the plan
last and when, keeping who first planned it, with the plan's fingerprint taken again
(DEC-003 point 5). It is no move: the cycle stays planned. Each part of the plan a flag
gives replaces that part whole, so `--variant` and `--key-result` give every variant and
key result the plan then holds. The cycle is named as every command names one, read within
the location (`naming.named`).

Refused: a cycle that is not planned, as the process engine places it; through the
predicate the check shares (`gates.changing`), a change that moves the window's start to
today or before, since a plan is frozen from its window's first day; and a variant given
that is not shortlisted. The check, which every write is held to, refuses the rest, such
as a variant dropped that an experiment of the cycle tests, a variant left with no key
result, or a window that comes to overlap another cycle's.

Usage:
  pkit lean change-plan <cycle> [--variant <variant>]... [--start <day>] [--days <n>]
                        [--objective <text>] [--key-result <variant>:<step>:<target>]...
                        [--constraint-step <step>] [--constraint-evidence <text>]
                        [--person-decided]

Exit codes:
  0  written
  1  refused, or answered no: nothing was written
  2  usage
  3  nobody could be asked: the question is printed, and nothing was written
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))

from _lib import acting, cycles, engine, gates, model, naming, positions, writes
from _lib.acting import Context
from _lib.writes import Refused


def parser() -> argparse.ArgumentParser:
    made = argparse.ArgumentParser(
        prog="pkit lean change-plan",
        description="Change a planned cycle's plan, before its window starts.",
    )
    made.add_argument("cycle", help="The cycle, by its id, `<idea>--<cycle>`, or its own part.")
    cycles.plan_flags(made, first=False)
    acting.person_decided(made)
    return made


def run(args: argparse.Namespace, ctx: Context) -> None:
    if not cycles.given(args):
        raise Refused(
            "give what the plan changes: --variant, --start, --days, --objective, --key-result, "
            "--constraint-step or --constraint-evidence"
        )
    files = writes.Files(ctx.root, writes.for_writing(ctx.root))
    cycle_id = naming.named(files, naming.CYCLE, str(args.cycle))
    cycle = cycles.open_cycle(files, cycle_id)
    state = acting.position(ctx, engine.CYCLE, cycle_id).state
    if state != positions.PLANNED:
        raise Refused(
            f"`{cycle_id}` stands {state}, not planned: a plan changes only before its window "
            f"starts, and is frozen from its first day"
        )
    before = cycles.words(cycle.plain())
    cycles.lay_plan(ctx, files, cycle, args)
    # A change on the day of the first planning is part of planning, as the check reads it.
    if model.first_planned(cycle.plain()) != ctx.on:
        refusals = gates.changing(cycle.plain(), ctx.on)
        if refusals:
            raise Refused("; ".join(refusal.message for refusal in refusals))
    cycles.stamp(ctx, cycle)
    files.put(cycle.rel, cycle.doc)
    after = cycles.words(cycle.plain())
    acting.act(
        ctx,
        files,
        f"Changed the plan of `{cycle_id}`: {after}.",
        question=(
            f"Change the plan of `{cycle_id}`, from {before}, to {after}? Its plan may change "
            f"until its window starts, and is frozen from then."
        ),
        decided=args.person_decided,
    )


def main() -> int:
    return acting.main(parser(), run, date.today())


if __name__ == "__main__":
    sys.exit(main())
