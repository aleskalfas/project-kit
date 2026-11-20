#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml==0.19.1",
# ]
# ///
"""lean-business capability — set-authors: name who writes a variant's canvas, or a draft
experiment, one person or a team (lean-business DEC-002 points 4 and 9).

Content, so it asks nothing and records no who or when. The names given replace the authors
whole, in the order given. A variant and an experiment are both named `<idea>--<own>`, so
the command finds which the id names, and refuses one that names both, or neither.

An experiment's authors are part of its declaration, so they are refused once it is
declared, since a declaration is frozen and a correction comes as a new experiment. A draft
in a suspended cycle is warned of, since nothing is declared or recorded on it until the
cycle resumes. No verdict covers a canvas's authors, so a change of them leaves none stale.

Usage:
  pkit lean set-authors <variant|experiment> <name>...

Exit codes:
  0  written, or the authors are those already
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

from _lib import acting, canvases, editing, experiments, ids, writes
from _lib.acting import Context
from _lib.writes import Refused


def parser() -> argparse.ArgumentParser:
    made = argparse.ArgumentParser(
        prog="pkit lean set-authors",
        description="Name who writes a variant's canvas, or a draft experiment.",
    )
    made.add_argument(
        "subject",
        metavar="variant|experiment",
        help="The variant's or the experiment's id, `<idea>--<own>`.",
    )
    made.add_argument(
        "names",
        nargs="+",
        metavar="name",
        help="Each author, in order; together they replace the authors whole.",
    )
    return made


def run(args: argparse.Namespace, ctx: Context) -> None:
    subject = str(args.subject)
    if not ids.is_idea_qualified(subject):
        raise Refused(
            f"`{subject}` is no variant's or experiment's id: each is named `<idea>--<own>`, "
            f"such as `meal-plan--direct`"
        )
    names = [str(name).strip() for name in args.names]
    if not all(names):
        raise Refused("an author has a name")
    twice = sorted({name for name in names if names.count(name) > 1})
    if twice:
        raise Refused(f"{', '.join(f'`{n}`' for n in twice)} is named twice")
    files = writes.Files(ctx.root, writes.for_writing(ctx.root))
    is_variant = files.exists(files.path("canvas", subject))
    is_experiment = files.exists(files.path("experiment", subject))
    if is_variant and is_experiment:
        raise Refused(
            f"`{subject}` names both a variant and an experiment, so which to change cannot be told"
        )
    warning = None
    if is_variant:
        canvas = canvases.open_variant(files, subject)
        data, rel, doc, order = canvas.data, canvas.rel, canvas.doc, canvases.ORDER
    elif is_experiment:
        experiment = experiments.open_experiment(files, subject)
        experiments.unfrozen(experiment, "its authors stay as they were declared")
        data, rel, doc, order = experiment.data, experiment.rel, experiment.doc, experiments.ORDER
        warning = experiments.suspended_warning(ctx, experiment.plain())
    else:
        raise Refused(
            f"there is no variant or experiment `{subject}`: `pkit lean status "
            f"{ids.idea_of(subject)}` lists the idea's"
        )
    if list(data.get("authors") or []) == names:
        ctx.say(f"The authors of `{subject}` are those already; nothing changed.")
        return
    editing.place(data, "authors", editing.seq(names), order)
    files.put(rel, doc)
    named = ", ".join(f"`{name}`" for name in names)
    acting.content(ctx, files, f"The authors of `{subject}` are now {named}.")
    if warning is not None:
        ctx.say(warning)


def main() -> int:
    return acting.main(parser(), run, date.today())


if __name__ == "__main__":
    sys.exit(main())
