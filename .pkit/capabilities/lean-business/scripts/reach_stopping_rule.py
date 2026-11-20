#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml==0.19.1",
# ]
# ///
"""lean-business capability — reach-stopping-rule: record that a generative experiment's
stopping rule was reached, which ends it before its time box does (lean-business DEC-002
point 10; DEC-003 points 3 and 5).

The person's act, so it takes their word, and records who and the day. It takes no move:
the experiment is then due, whatever its dates say, and the move there is the script's,
`come-due`, which follows the files as a date's does and which no command takes (DEC-003
point 3). Deciding it comes next.

Refused: an evaluative experiment, which runs its whole time box; one not declared, or
decided, or whose stopping rule is recorded already; one whose cycle is suspended, naming
`resume`; and, through the predicate the check shares (`gates.stopping`), a day outside
its time box, as its cycle's suspensions move it.

Usage:
  pkit lean reach-stopping-rule <experiment> [--person-decided]

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

from _lib import acting, editing, experiments, gates, model, writes
from _lib.acting import Context
from _lib.experiments import ORDER
from _lib.writes import Refused


def parser() -> argparse.ArgumentParser:
    made = argparse.ArgumentParser(
        prog="pkit lean reach-stopping-rule",
        description="Record that a generative experiment's stopping rule was reached, which "
        "ends it before its time box does.",
    )
    made.add_argument("experiment", help="The experiment's id, `<idea>--<experiment>`.")
    acting.person_decided(made)
    return made


def run(args: argparse.Namespace, ctx: Context) -> None:
    files = writes.Files(ctx.root, writes.for_writing(ctx.root))
    experiment = experiments.open_experiment(files, str(args.experiment))
    subject, plain = experiment.id, experiment.plain()
    if plain.get("kind") != "generative":
        raise Refused(
            f"`{subject}` is {plain.get('kind')}, and only a generative experiment has a "
            f"stopping rule: an evaluative one runs its whole time box"
        )
    if not model.declared(plain):
        raise Refused(f"`{subject}` is a draft: a stopping rule is reached once it is declared")
    if isinstance(plain.get("decision"), Mapping):
        raise Refused(f"`{subject}` is decided already")
    stopped = plain.get("stopped")
    if isinstance(stopped, Mapping):
        raise Refused(
            f"`{subject}` records its stopping rule reached already, on {stopped.get('when')}"
        )
    experiments.refuse_if_suspended(ctx, plain, "its stopping rule")
    cycle = experiments.cycle_plain(files, plain)
    refusals = gates.stopping(plain, ctx.on, cycle)
    if refusals:
        raise Refused("; ".join(refusal.message for refusal in refusals))
    record = editing.mapping([("by", ctx.who), ("when", ctx.on)])
    editing.place(experiment.data, "stopped", record, ORDER)
    files.put(experiment.rel, experiment.doc)
    acting.act(
        ctx,
        files,
        f"Recorded the stopping rule of `{subject}` reached today, {ctx.on}: it is due for its "
        f"result and your decision.",
        question=(
            f'Record the stopping rule of `{subject}`, "{plain.get("stopping-rule")}", reached '
            f"today? The experiment then ends, due for its result and your decision."
        ),
        decided=args.person_decided,
    )


def main() -> int:
    return acting.main(parser(), run, date.today())


if __name__ == "__main__":
    sys.exit(main())
