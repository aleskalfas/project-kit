#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml==0.19.1",
# ]
# ///
"""lean-business capability — record-estimate: record the person's own guess at the number an
experiment's result is held against, made alone before it is declared (lean-business
DEC-002 point 9; DEC-003 points 3 and 5).

An act, not content: an estimate an agent drafts in the person's name is not made alone,
so it takes the person's word (DEC-003 point 5). It is recorded under git's user.name, and
a second estimate by the same person replaces their first. Refused once the experiment is
declared, and while its cycle is suspended, naming `resume`.

Usage:
  pkit lean record-estimate <experiment> <value> [--person-decided]

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

from ruamel.yaml.comments import CommentedSeq

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))

from _lib import acting, editing, experiments, writes
from _lib.acting import Context
from _lib.experiments import ORDER


def parser() -> argparse.ArgumentParser:
    made = argparse.ArgumentParser(
        prog="pkit lean record-estimate",
        description="Record your own guess at the number an experiment's result is held "
        "against, made alone before it is declared.",
    )
    made.add_argument("experiment", help="The experiment's id, `<idea>--<experiment>`.")
    made.add_argument("value", type=float, help="Your guess, a number.")
    acting.person_decided(made)
    return made


def run(args: argparse.Namespace, ctx: Context) -> None:
    files = writes.Files(ctx.root, writes.for_writing(ctx.root))
    experiment = experiments.open_experiment(files, str(args.experiment))
    experiments.unfrozen(experiment, "its estimates are those made before it")
    experiments.refuse_if_suspended(ctx, experiment.plain(), "an estimate")
    who, value = ctx.who, editing.number(args.value)
    held = experiment.data.get("estimates")
    estimates = held if isinstance(held, CommentedSeq) else editing.seq()
    earlier = next(
        (
            index
            for index, estimate in enumerate(estimates)
            if isinstance(estimate, Mapping) and estimate.get("by") == who
        ),
        None,
    )
    estimate = editing.mapping([("by", who), ("value", value)])
    if earlier is None:
        estimates.append(estimate)
    else:
        estimates[earlier] = estimate
    editing.place(experiment.data, "estimates", estimates, ORDER)
    files.put(experiment.rel, experiment.doc)
    replaces = " It replaces your earlier one." if earlier is not None else ""
    acting.act(
        ctx,
        files,
        f"Recorded {who}'s estimate for `{experiment.id}`: {value}.{replaces}",
        question=(
            f"Record {value} as your own estimate for `{experiment.id}`, made alone, before "
            f"seeing anyone else's?{replaces}"
        ),
        decided=args.person_decided,
    )


def main() -> int:
    return acting.main(parser(), run, date.today())


if __name__ == "__main__":
    sys.exit(main())
