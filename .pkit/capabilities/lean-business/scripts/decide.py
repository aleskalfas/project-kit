#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml==0.19.1",
# ]
# ///
"""lean-business capability — decide: record the person's next action on a due experiment,
with its result recorded (lean-business DEC-002 point 10; DEC-003 points 3 and 5).

The person's move, on `decide`, from due to decided: it records the next action, who
decided it and the day. `correct-course` means a new experiment, `double-down` doing more
of what passed, and `stop` stopping it.

Refused: an experiment that is not due, as the process engine places it: its time box has
not ended, and no generative stopping rule is recorded as reached; one whose result is not
recorded, naming `record-result`; one whose cycle is suspended, naming `resume`; and,
through the predicate the check shares (`gates.deciding`), a decision its rules refuse.

Usage:
  pkit lean decide <experiment> correct-course|double-down|stop [--person-decided]

Exit codes:
  0  decided
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

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))

from _lib import acting, editing, engine, experiments, gates, positions, readings, writes
from _lib.acting import Context
from _lib.experiments import ORDER
from _lib.writes import Refused

TRIGGER = "decide"


def parser() -> argparse.ArgumentParser:
    made = argparse.ArgumentParser(
        prog="pkit lean decide",
        description="Record your next action on a due experiment, with its result recorded.",
    )
    made.add_argument("experiment", help="The experiment's id, `<idea>--<experiment>`.")
    made.add_argument(
        "next",
        choices=tuple(positions.NEXT_ACTIONS),
        help="`correct-course`, a new experiment; `double-down`; or `stop`.",
    )
    acting.person_decided(made)
    return made


def run(args: argparse.Namespace, ctx: Context) -> None:
    files = writes.Files(ctx.root, writes.for_writing(ctx.root))
    experiment = experiments.open_experiment(files, str(args.experiment))
    subject, plain = experiment.id, experiment.plain()
    following = str(args.next)
    if isinstance(plain.get("decision"), Mapping):
        raise Refused(f"`{subject}` is decided already, on {plain['decision'].get('when')}")
    experiments.refuse_if_suspended(ctx, plain, "its decision")
    before = acting.position(ctx, engine.EXPERIMENT, subject)
    if before.state != positions.DUE:
        raise Refused(
            f"`{subject}` stands {before.state}, not due: it is decided once its time box has "
            f"ended, or a generative experiment's stopping rule is recorded as reached"
        )
    if not isinstance(plain.get("result"), Mapping):
        raise Refused(
            f"`{subject}` has no result recorded, and deciding needs it: `pkit lean "
            f"record-result {subject} --evidence <text> --learned <text>` records it"
        )
    refusals = gates.deciding(plain, ctx.on, experiments.cycle_plain(files, plain))
    if refusals:
        raise Refused("; ".join(refusal.message for refusal in refusals))
    outcome = positions.OUTCOME_WORDS[readings.experiment_outcome(plain) or readings.NEITHER]

    def build() -> tuple[writes.Files, str]:
        decision = editing.mapping([("next", following), ("by", ctx.who), ("when", ctx.on)])
        editing.place(experiment.data, "decision", decision, ORDER)
        files.put(experiment.rel, experiment.doc)
        return files, (
            f"Decided `{subject}`, whose result works out to {outcome}: "
            f"{positions.NEXT_ACTIONS[following]}."
        )

    ctx.say(
        f"Deciding `{subject}`: its result works out to {outcome}, and the next action is to "
        f"{positions.NEXT_ACTIONS[following]}."
    )
    acting.person_move(
        ctx, engine.EXPERIMENT, subject, TRIGGER, before, build, decided=args.person_decided
    )


def main() -> int:
    return acting.main(parser(), run, date.today())


if __name__ == "__main__":
    sys.exit(main())
