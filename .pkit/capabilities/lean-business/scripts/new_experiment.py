#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml==0.19.1",
# ]
# ///
"""lean-business capability — new-experiment: start a draft of an experiment, one test of one
assumption (lean-business DEC-002 point 9).

Content, so it asks nothing and records no who or when. The draft may come before its
cycle is planned, so the assumption it tests and the cycle it runs in may each wait for
`draft-experiment`. Each is named as every command names one, read within the
experiment's idea (`naming.named`), and is refused where nothing holds it. Its authors are
those `--author` gives, or git's user.name, and it is refused where neither names anyone. A
draft in a suspended cycle is warned of, since nothing is declared or recorded on it until
the cycle resumes.

Usage:
  pkit lean new-experiment <idea>--<experiment> --kind generative|evaluative
                           [--assumption <assumption>] [--cycle <cycle>] [--author <name>]...

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

from _lib import acting, editing, experiments, ids, layout, naming, positions, writes
from _lib.acting import Context
from _lib.writes import Refused


def parser() -> argparse.ArgumentParser:
    made = argparse.ArgumentParser(
        prog="pkit lean new-experiment",
        description="Start a draft of an experiment, one test of one assumption.",
    )
    made.add_argument("experiment", help="The experiment's id, `<idea>--<experiment>`.")
    made.add_argument(
        "--kind",
        required=True,
        choices=positions.KINDS,
        help="`generative`, run to discover, or `evaluative`, run to measure traction.",
    )
    made.add_argument(
        "--assumption",
        help="The assumption it tests, by its id, the part after the idea, "
        "`<variant>--<assumption>`, or its own part.",
    )
    made.add_argument("--cycle", help="The cycle it runs in, by its id or its own part.")
    made.add_argument(
        "--author",
        action="append",
        dest="authors",
        help="Who writes it; repeat it for each. Git's user.name where none is given.",
    )
    return made


def run(args: argparse.Namespace, ctx: Context) -> None:
    experiment = experiments.experiment_id(str(args.experiment))
    idea = ids.idea_of(experiment)
    files = writes.Files(ctx.root, writes.for_writing(ctx.root))
    rel = files.path("experiment", experiment)
    if files.exists(rel):
        raise Refused(f"the experiment `{experiment}` exists already, at `{rel}`")
    naming.given(
        idea,
        typed=ids.own(experiment),
        text="",
        fallback="experiment",
        taken=naming.in_use(files, idea),
    )
    assumption = None
    if args.assumption is not None:
        assumption = experiments.assumption_ref(files, idea, str(args.assumption))
        experiments.assumption_held(files, assumption)
    cycle = None
    if args.cycle is not None:
        cycle = experiments.cycle_ref(files, idea, str(args.cycle))
        experiments.cycle_held(files, cycle)
    authors = ctx.authors(args.authors, "an experiment")
    body = editing.mapping(
        [
            ("id", experiment),
            ("assumption", assumption),
            ("cycle", cycle),
            ("kind", args.kind),
            ("authors", editing.seq(authors)),
        ]
    )
    files.put(rel, editing.new(layout.SCHEMA["experiment"], body))
    acting.content(
        ctx,
        files,
        f"Created the draft `{experiment}`: `{rel}`. `pkit lean draft-experiment {experiment}` "
        f"writes what it declares.",
    )
    warning = experiments.suspended_warning(ctx, body)
    if warning is not None:
        ctx.say(warning)


def main() -> int:
    return acting.main(parser(), run, date.today())


if __name__ == "__main__":
    sys.exit(main())
