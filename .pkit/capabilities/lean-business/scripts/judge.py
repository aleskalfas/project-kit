#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml==0.19.1",
# ]
# ///
"""lean-business capability — judge: record the person's yes or no on a desk step of a
variant: desirability, viability or feasibility (lean-business DEC-003 points 2 and 5;
DEC-002 points 5 and 13).

The verdict is the person's, so it takes their word and records who judged and when, with
the fingerprint of what it judged. Where the variant stands is read from the process
engine, and the verdict does what the desk stage lets it:

- a yes on the next step moves the variant on (`pass-<step>`), its gate first: the goal
  set, where the step judges against it; each box the step judges holding an entry; and a
  yes that is not stale on each step before;
- a yes on a step passed already judges it again, on the canvas as it stands, and moves
  nothing;
- a no on the next step records it, and moves nothing;
- a no on a step passed already takes the variant back (`fail-<step>`), clears the
  verdicts after it and withdraws a shortlisting.

A step after the next is refused, as is any verdict on a shelved or split variant, which
is final.

Usage:
  pkit lean judge <variant> desirability|viability|feasibility yes|no [--note <text>]
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
from collections.abc import Mapping
from datetime import date
from pathlib import Path
from typing import Any

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))

from _lib import acting, canvases, editing, engine, fingerprint, gates, positions, writes
from _lib.acting import Context
from _lib.fingerprint import STEPS
from _lib.writes import Refused

#: How many steps the person's yes stands on in each state of the desk stage.
PASSED = {
    positions.SKETCHED: 0,
    positions.DESIRABLE: 1,
    positions.VIABLE: 2,
    positions.FEASIBLE: 3,
    positions.SHORTLISTED: 3,
}


def parser() -> argparse.ArgumentParser:
    made = argparse.ArgumentParser(
        prog="pkit lean judge",
        description="Record the person's yes or no on a desk step of a variant.",
    )
    made.add_argument("variant", help="The variant's id, `<idea>--<variant>`.")
    made.add_argument("step", choices=STEPS)
    made.add_argument("answer", choices=("yes", "no"))
    made.add_argument("--note", help="Why, in a sentence.")
    acting.person_decided(made)
    return made


def run(args: argparse.Namespace, ctx: Context) -> None:
    variant = canvases.variant_id(str(args.variant))
    step, answer = str(args.step), str(args.answer)
    note = str(args.note).strip() if args.note is not None else None
    if note == "":
        raise Refused("a note has words")
    before = acting.position(ctx, engine.DESK, variant)
    state = before.state
    if state in (positions.SHELVED, positions.SPLIT):
        raise Refused(f"`{variant}` is {state}, which is final: no step of it is judged again")
    if state not in PASSED:
        raise Refused(f"`{variant}` stands in none of the desk stage's states")
    passed, index = PASSED[state], STEPS.index(step)
    if index > passed:
        raise Refused(
            f"`{variant}` is {state}: {STEPS[passed]} is judged next, and {step} only once "
            f"each step before it has a yes"
        )

    def build() -> tuple[writes.Files, str]:
        files = writes.Files(ctx.root, writes.for_writing(ctx.root))
        canvas = canvases.open_variant(files, variant)
        goal = canvases.goal_of(files, canvas.idea)
        plain = canvas.plain()
        refusals = [*gates.judging(step, goal)]
        if answer == "yes":
            refusals += [
                *gates.yes_content(step, plain),
                *gates.stale_before(step, plain, goal),
            ]
        if refusals:
            raise Refused("; ".join(refusal.message for refusal in refusals))
        _record(ctx, canvas, step, answer, note, goal)
        files.put(canvas.rel, canvas.doc)
        return files, f"Recorded a {answer} on {step} for `{variant}`."

    decided = bool(args.person_decided)
    if answer == "yes" and index == passed:
        trigger = f"pass-{step}"
        acting.person_move(ctx, engine.DESK, variant, trigger, before, build, decided=decided)
    elif answer == "no" and index < passed:
        trigger = f"fail-{step}"
        acting.person_move(ctx, engine.DESK, variant, trigger, before, build, decided=decided)
    else:
        files, done = build()
        question = (
            f"Record a no on {step} for `{variant}`? It stays {state} until a yes."
            if answer == "no"
            else f"Judge {step} of `{variant}` yes again, on the canvas as it stands?"
        )
        acting.act(ctx, files, done, question=question, decided=decided)


def _record(
    ctx: Context,
    canvas: canvases.Canvas,
    step: str,
    answer: str,
    note: str | None,
    goal: Mapping[str, Any] | None,
) -> None:
    """Write the verdict on `step` into the canvas; a no clears the verdicts after it and
    withdraws a shortlisting."""
    verdicts = canvas.data.get("verdicts")
    if not isinstance(verdicts, dict):
        verdicts = editing.mapping()
        editing.place(canvas.data, "verdicts", verdicts, canvases.ORDER)
    if answer == "no":
        for later in STEPS[STEPS.index(step) + 1 :]:
            verdicts.pop(later, None)
        outcome = canvas.data.get("outcome")
        if isinstance(outcome, Mapping) and outcome.get("kind") == "shortlisted":
            del canvas.data["outcome"]
    plain = canvas.plain()
    taken = canvases.fingerprint_data(lambda: fingerprint.of_verdict(step, plain, goal))
    verdict = editing.mapping(
        [
            ("answer", editing.quoted(answer)),
            ("note", note),
            ("fingerprint", taken),
            ("by", ctx.who),
            ("when", ctx.on),
        ]
    )
    editing.place(verdicts, step, verdict, STEPS)


def main() -> int:
    return acting.main(parser(), run, date.today())


if __name__ == "__main__":
    sys.exit(main())
