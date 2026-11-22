#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml==0.19.1",
# ]
# ///
"""lean-business capability — plan-cycle: plan an idea's next cycle, the shortlisted
variants it explores, its window, its objective and its constraint (lean-business DEC-002
point 11; DEC-003 points 4 and 5).

The plan is the person's act, so it takes their word and records who planned it and when,
with the plan's fingerprint (DEC-003 point 5). Planning is no move: a cycle whose plan is
recorded stands planned. Its window holds 90 days where `--days` gives none, sized to the
time the person can give it, and 3650 days, ten years, at most. A key result names the
variant it is taken from, its step of the customer factory and the number to reach there.

Refused: a variant that is not shortlisted, as the process engine places it; and, through
the predicate the check shares (`gates.planning`), an idea with no goal and a cycle of the
idea still undecided. The check, which every write is held to, refuses the rest: a window
that overlaps another cycle's as worked out, a variant explored with no key result, and a
key result naming a variant the cycle does not explore. A window that has started by today
is warned of, since its plan is frozen from its first day.

Usage:
  pkit lean plan-cycle <idea>--<cycle> --variant <variant>... --start <day> [--days <n>]
                       --objective <text> --key-result <variant>:<step>:<target>...
                       --constraint-step <step> --constraint-evidence <text>
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

from _lib import acting, canvases, cycles, editing, experiments, gates, ids, layout, naming, writes
from _lib.acting import Context
from _lib.writes import Refused


def parser() -> argparse.ArgumentParser:
    made = argparse.ArgumentParser(
        prog="pkit lean plan-cycle",
        description="Plan an idea's next cycle: the shortlisted variants it explores, its "
        "window, its objective and its constraint.",
    )
    made.add_argument("cycle", help="The cycle's id, `<idea>--<cycle>`.")
    cycles.plan_flags(made, first=True)
    acting.person_decided(made)
    return made


def run(args: argparse.Namespace, ctx: Context) -> None:
    cycle_id = cycles.cycle_id(str(args.cycle))
    idea = ids.idea_of(cycle_id)
    files = writes.Files(ctx.root, writes.for_writing(ctx.root))
    rel = files.path("cycle", cycle_id)
    if files.exists(rel):
        raise Refused(
            f"the cycle `{cycle_id}` exists already, at `{rel}`: `pkit lean change-plan` "
            f"changes its plan while it is planned"
        )
    naming.given(
        idea,
        typed=ids.own(cycle_id),
        text="",
        fallback="cycle",
        taken=naming.in_use(files, idea),
    )
    doc = editing.new(layout.SCHEMA["cycle"], {"id": cycle_id})
    cycle = cycles.Cycle(rel, doc, cycle_id)
    cycles.lay_plan(ctx, files, cycle, args)
    cycles.stamp(ctx, cycle)
    held = experiments.read_idea(files, idea)
    refusals = gates.planning(
        cycle.plain(),
        ctx.on,
        goal=canvases.goal_of(files, idea),
        others=[other.data for other in held.cycles] if held is not None else [],
    )
    if refusals:
        raise Refused("; ".join(refusal.message for refusal in refusals))
    files.put(rel, doc)
    plan = cycles.words(cycle.plain())
    acting.act(
        ctx,
        files,
        f"Planned the cycle `{cycle_id}`: {plan}.",
        question=(
            f"Plan the cycle `{cycle_id}`: {plan}? Its plan may change until its window "
            f"starts, and is frozen from then."
        ),
        decided=args.person_decided,
    )
    started = cycles.started(cycle.plain(), ctx.on)
    if started is not None:
        ctx.say(started)


def main() -> int:
    return acting.main(parser(), run, date.today())


if __name__ == "__main__":
    sys.exit(main())
