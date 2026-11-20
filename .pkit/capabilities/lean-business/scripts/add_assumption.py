#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml==0.19.1",
# ]
# ///
"""lean-business capability — add-assumption: add an assumption to a variant's list, what
its model takes for granted that no evidence supports yet (lean-business DEC-002 points 7
and 8).

Content, so it asks nothing and records no who or when. It comes from an entry of the
canvas, `--entry`, or from an input of the estimate, `--input`, for `--side` where the
model names several. An entry the canvas does not hold is refused, since it can only be a
typo. The assumption goes one past the highest rank, a placement that judges nothing: the
person ranks the list by risk with `rank` before an experiment is declared on it. Its id is
the one `--id` gives, or one taken from its statement, qualified by its variant, and
printed. The variant's list is created where it has none.

Usage:
  pkit lean add-assumption <variant> <statement>
                           --kind desirability|viability|feasibility
                           (--entry <entry> | --input <input> [--side <side>]) [--id <id>]

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

from _lib import acting, assumptions, canvases, editing, naming, writes
from _lib.acting import Context
from _lib.writes import Refused


def parser() -> argparse.ArgumentParser:
    made = argparse.ArgumentParser(
        prog="pkit lean add-assumption",
        description="Add an assumption to a variant's list: what its model takes for granted "
        "that no evidence supports yet.",
    )
    made.add_argument("variant", help="The variant's id, `<idea>--<variant>`.")
    made.add_argument("statement", help="What the model takes for granted, as a leap of faith.")
    made.add_argument(
        "--kind",
        required=True,
        choices=assumptions.KINDS,
        help="The desk step whose risk it carries.",
    )
    source = made.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--entry",
        metavar="ENTRY",
        help="The entry of the canvas it comes from, by its id or its own part.",
    )
    source.add_argument(
        "--input",
        dest="input_name",
        choices=assumptions.INPUTS,
        help="The input of the estimate it comes from.",
    )
    made.add_argument("--side", help="With --input: the side the input is given for.")
    made.add_argument(
        "--id", help="The assumption's own id; taken from its statement where not given."
    )
    return made


def run(args: argparse.Namespace, ctx: Context) -> None:
    statement = str(args.statement).strip()
    if not statement:
        raise Refused("an assumption has words")
    files = writes.Files(ctx.root, writes.for_writing(ctx.root))
    canvas = canvases.open_variant(files, str(args.variant))
    listed = assumptions.open_list(files, canvas.id, create=True)
    assumption = editing.mapping()
    assumption["id"] = naming.given(
        canvas.id,
        typed=args.id,
        text=statement,
        fallback="assumption",
        taken=naming.in_use(files, canvas.idea),
    )
    assumption["statement"] = statement
    assumption["source"] = assumptions.source(
        canvas, entry=args.entry, input_name=args.input_name, side=args.side
    )
    assumption["kind"] = args.kind
    rank = listed.next_rank()
    assumption["rank"] = rank
    listed.items().append(assumption)
    files.put(listed.rel, listed.doc)
    acting.content(
        ctx,
        files,
        f"Added `{assumption['id']}` to the assumptions of `{canvas.id}`, ranked {rank}, below "
        f"the others until you rank them: `pkit lean rank {canvas.id} <assumption>...`.",
    )


def main() -> int:
    return acting.main(parser(), run, date.today())


if __name__ == "__main__":
    sys.exit(main())
