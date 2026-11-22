#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml==0.19.1",
# ]
# ///
"""lean-business capability — move-entry: move an entry to another position in its box
(lean-business DEC-002 point 4).

Content, so it asks nothing and records no who or when. A position counts from 1, the
first. The problems' order is their rank, so a problem's position is its rank. The entry
keeps its id, its words and its links, and the others keep their order.

A box's order is part of what a verdict judged, so a move is warned of, never refused,
naming each judgement it leaves stale.

Usage:
  pkit lean move-entry <entry> --to <position>

Exit codes:
  0  written, or the entry stands at that position already
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

from _lib import acting, canvases, editing, writes
from _lib.acting import Context
from _lib.writes import Refused


def parser() -> argparse.ArgumentParser:
    made = argparse.ArgumentParser(
        prog="pkit lean move-entry",
        description="Move an entry to another position in its box.",
    )
    made.add_argument("entry", help="The entry's id, `<idea>--<variant>--<entry>`.")
    made.add_argument(
        "--to",
        type=int,
        required=True,
        metavar="POSITION",
        help="Its position in its box, 1 the first; a problem's position is its rank.",
    )
    return made


def run(args: argparse.Namespace, ctx: Context) -> None:
    entry_id = str(args.entry)
    variant = canvases.entry_variant(entry_id)
    files = writes.Files(ctx.root, writes.for_writing(ctx.root))
    canvas = canvases.open_variant(files, variant)
    box, held, index = canvases.find_entry(canvas, entry_id)
    to = int(args.to)
    if not 1 <= to <= len(held):
        raise Refused(
            f"{box} holds {len(held)} {'entry' if len(held) == 1 else 'entries'}, so a "
            f"position there is 1 to {len(held)}, and {to} is none"
        )
    ranked = ", its rank among the problems" if box == "problem" else ""
    if to == index + 1:
        ctx.say(f"`{entry_id}` is at position {to} of {box}{ranked} already; nothing changed.")
        return
    editing.move(canvas.boxes(), box, index, to - 1)
    files.put(canvas.rel, canvas.doc)
    acting.content(ctx, files, f"Moved `{entry_id}` to position {to} of {box}{ranked}.")


def main() -> int:
    return acting.main(parser(), run, date.today())


if __name__ == "__main__":
    sys.exit(main())
