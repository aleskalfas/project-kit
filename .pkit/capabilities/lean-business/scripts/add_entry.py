#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml==0.19.1",
# ]
# ///
"""lean-business capability — add-entry: add an entry to a box of a variant's canvas
(lean-business DEC-002 points 4, 6 and 7).

Content, so it asks nothing and records no who or when. The entry goes last in its box; a
problem's place is its rank. Its id is the one `--id` gives, or one taken from its text,
qualified by its variant, and printed. The box's links come as flags, each on the boxes
that take it; a link names another entry of the canvas by its id, or by its own part.

A change to what a standing verdict judged is warned of, never refused, naming each
judgement it leaves stale.

Usage:
  pkit lean add-entry <variant> <box> <text> [--id <id>] [--side <side>]
                      [--alternative <entry>]... [--problem <entry>] [--sub-headline <text>]
                      [--trigger <text>]... [--kind early|scalable] [--step <factory step>]

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

from _lib import acting, canvases, editing, naming, writes
from _lib.acting import Context
from _lib.fingerprint import BOXES
from _lib.writes import Refused


def parser() -> argparse.ArgumentParser:
    made = argparse.ArgumentParser(
        prog="pkit lean add-entry",
        description="Add an entry to a box of a variant's canvas.",
    )
    made.add_argument("variant", help="The variant's id, `<idea>--<variant>`.")
    made.add_argument("box", choices=BOXES, metavar="box", help=f"One of {', '.join(BOXES)}.")
    made.add_argument("text", help="The entry's words.")
    made.add_argument("--id", help="The entry's own id; taken from its text where not given.")
    made.add_argument("--side", help="The side it belongs to, in a model with several.")
    canvases.link_flags(made)
    return made


def run(args: argparse.Namespace, ctx: Context) -> None:
    text = str(args.text).strip()
    if not text:
        raise Refused("an entry has words")
    files = writes.Files(ctx.root, writes.for_writing(ctx.root))
    canvas = canvases.open_variant(files, str(args.variant))
    canvases.check_side(canvas, args.side)
    entry = editing.mapping()
    entry["id"] = naming.given(
        canvas.id,
        typed=args.id,
        text=text,
        fallback=args.box,
        taken=naming.in_use(files, canvas.idea),
    )
    entry["text"] = text
    if args.side is not None:
        canvases.set_entry_field(entry, "side", args.side)
    canvases.add_links(canvas, args.box, entry, canvases.given_links(args))
    canvas.box(args.box).append(entry)
    files.put(canvas.rel, canvas.doc)
    acting.content(ctx, files, f"Added `{entry['id']}` to {args.box}.")


def main() -> int:
    return acting.main(parser(), run, date.today())


if __name__ == "__main__":
    sys.exit(main())
