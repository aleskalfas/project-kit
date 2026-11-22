#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml==0.19.1",
# ]
# ///
"""lean-business capability — record-result: record what a declared experiment found
(lean-business DEC-002 point 10; DEC-003 points 3 and 5).

The person's act, so it takes their word, and records who and the day. It records what was
measured, held against the declared expectation or fit, whether a suspension its time box
ran through spoiled the measurement, where its evidence lies and what was learned. Pass or
fail is worked out from it and the declaration, never chosen, and said once it is recorded.
A result recorded again replaces the earlier one, until the experiment is decided.

Refused: an experiment not declared, or decided; one whose cycle is suspended, naming
`resume`; and, through the predicate the check shares (`gates.result`), a measurement
recorded as spoiled where no suspension of its cycle ran through its time box.

Usage:
  pkit lean record-result <experiment> [--measured <number>] [--spoiled]
                          --evidence <text> --learned <text> [--person-decided]

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

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))

from _lib import acting, editing, experiments, gates, model, positions, readings, writes
from _lib.acting import Context
from _lib.experiments import ORDER
from _lib.writes import Refused


def parser() -> argparse.ArgumentParser:
    made = argparse.ArgumentParser(
        prog="pkit lean record-result",
        description="Record what a declared experiment found.",
    )
    made.add_argument("experiment", help="The experiment's id, `<idea>--<experiment>`.")
    made.add_argument(
        "--measured",
        type=float,
        help="What was measured, held against the declared expectation or fit; left out where "
        "nothing could be.",
    )
    made.add_argument(
        "--spoiled",
        action="store_true",
        help="A suspension its time box ran through spoiled the measurement.",
    )
    made.add_argument("--evidence", required=True, help="Where its evidence lies.")
    made.add_argument("--learned", required=True, help="What was learned.")
    acting.person_decided(made)
    return made


def run(args: argparse.Namespace, ctx: Context) -> None:
    evidence, learned = str(args.evidence).strip(), str(args.learned).strip()
    if not evidence or not learned:
        raise Refused("--evidence and --learned each have words")
    files = writes.Files(ctx.root, writes.for_writing(ctx.root))
    experiment = experiments.open_experiment(files, str(args.experiment))
    subject, plain = experiment.id, experiment.plain()
    if not model.declared(plain):
        raise Refused(f"`{subject}` is a draft: a result is recorded once it is declared")
    if isinstance(plain.get("decision"), Mapping):
        raise Refused(f"`{subject}` is decided, and its result is the one it was decided on")
    experiments.refuse_if_suspended(ctx, plain, "its result")
    earlier = isinstance(plain.get("result"), Mapping)
    result = editing.mapping(
        [
            ("measured", editing.number(args.measured) if args.measured is not None else None),
            ("spoiled", True if args.spoiled else None),
            ("evidence", evidence),
            ("learned", learned),
            ("by", ctx.who),
            ("when", ctx.on),
        ]
    )
    editing.place(experiment.data, "result", result, ORDER)
    recorded = experiment.plain()
    refusals = gates.result(recorded, ctx.on, experiments.cycle_plain(files, recorded))
    if refusals:
        raise Refused("; ".join(refusal.message for refusal in refusals))
    files.put(experiment.rel, experiment.doc)
    outcome = readings.experiment_outcome(recorded) or readings.NEITHER
    works_out = positions.OUTCOME_WORDS[outcome]
    replaces = " It replaces the result recorded before." if earlier else ""
    acting.act(
        ctx,
        files,
        f"Recorded the result of `{subject}`, which works out to {works_out}.{replaces}",
        question=(
            f"Record the result of `{subject}`: {_measured(args)}, which works out to "
            f"{works_out}?{replaces}"
        ),
        decided=args.person_decided,
    )


def _measured(args: argparse.Namespace) -> str:
    """What the result measured, and whether a suspension spoiled it, as the question says."""
    if args.measured is None:
        measured = "nothing measured"
    else:
        measured = f"{editing.number(args.measured)} measured"
    return f"{measured}, spoiled" if args.spoiled else measured


def main() -> int:
    return acting.main(parser(), run, date.today())


if __name__ == "__main__":
    sys.exit(main())
