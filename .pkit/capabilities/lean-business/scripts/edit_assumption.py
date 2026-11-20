#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml==0.19.1",
# ]
# ///
"""lean-business capability — edit-assumption: change an assumption's statement, its kind or
where it comes from (lean-business DEC-002 points 7 and 8).

Content, so it asks nothing and records no who or when. `--entry` or `--input` replaces
where it comes from whole, `--side` alone changes the side of an input it comes from. Its
id never changes, and its rank is `rank`'s. The assumption is named as every command names
one, read within the location (`naming.named`). An assumption a declared experiment tests
is warned of, never refused: the declaration stays as it was declared, so the change reads
only for later experiments.

Usage:
  pkit lean edit-assumption <assumption> [--statement <text>]
                            [--kind desirability|viability|feasibility]
                            [--entry <entry> | --input <input>] [--side <side>]

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

from ruamel.yaml.comments import CommentedMap

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))

from _lib import acting, assumptions, canvases, editing, experiments, ids, model, naming, writes
from _lib.acting import Context
from _lib.writes import Refused


def parser() -> argparse.ArgumentParser:
    made = argparse.ArgumentParser(
        prog="pkit lean edit-assumption",
        description="Change an assumption's statement, its kind or where it comes from.",
    )
    made.add_argument(
        "assumption",
        help="The assumption, by its id, `<idea>--<variant>--<assumption>`, the part after the "
        "idea, or its own part.",
    )
    made.add_argument("--statement", help="Its new words. Its id stays as it is.")
    made.add_argument("--kind", choices=assumptions.KINDS)
    source = made.add_mutually_exclusive_group()
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
    made.add_argument(
        "--side",
        help="The side the input it comes from is given for; with --input, or alone where it "
        "comes from an input already.",
    )
    return made


def run(args: argparse.Namespace, ctx: Context) -> None:
    if all(
        value is None
        for value in (args.statement, args.kind, args.entry, args.input_name, args.side)
    ):
        raise Refused(
            "give what the assumption changes: --statement, --kind, --entry, --input or --side"
        )
    files = writes.Files(ctx.root, writes.for_writing(ctx.root))
    assumption_id = naming.named(files, naming.ASSUMPTION, str(args.assumption))
    variant = ids.qualifier(assumption_id)
    canvas = canvases.open_variant(files, variant)
    listed = assumptions.open_list(files, variant)
    _, assumption = listed.find(assumption_id)
    if args.statement is not None:
        statement = str(args.statement).strip()
        if not statement:
            raise Refused("an assumption has words")
        assumption["statement"] = statement
    if args.kind is not None:
        assumption["kind"] = args.kind
    if args.entry is not None or args.input_name is not None:
        assumption["source"] = assumptions.source(
            canvas, entry=args.entry, input_name=args.input_name, side=args.side
        )
    elif args.side is not None:
        held = assumption.get("source")
        if not isinstance(held, CommentedMap) or held.get("input") is None:
            raise Refused(
                f"`{assumption_id}` comes from no input, so it names no side: give --input "
                f"with --side"
            )
        canvases.check_side(canvas, args.side)
        editing.place(held, "side", args.side, assumptions.SOURCE_ORDER)
    files.put(listed.rel, listed.doc)
    tested = _declared_on(files, canvas.idea, assumption_id)
    acting.content(ctx, files, f"Changed `{assumption_id}`.")
    if tested:
        named = ", ".join(f"`{e}`" for e in tested)
        ctx.say(
            f"warning: {named}, declared, {'tests' if len(tested) == 1 else 'test'} "
            f"`{assumption_id}`: a declaration stays as it was declared, so the change reads "
            f"only for later experiments"
        )


def _declared_on(files: writes.Files, idea: str, assumption: str) -> list[str]:
    """The ids of the declared experiments that test the assumption."""
    held = experiments.read_idea(files, idea)
    if held is None:
        return []
    return [
        held.qualified(e.own) for e in held.experiments_on(assumption) if model.declared(e.data)
    ]


def main() -> int:
    return acting.main(parser(), run, date.today())


if __name__ == "__main__":
    sys.exit(main())
