#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml==0.19.1",
# ]
# ///
"""lean-business capability — canvas: draw a variant's canvas as a grid, arranged as in the
book, with its credit and licence line beneath (lean-business DEC-001 point 6).

Read-only. `--ids` shows each entry's own part of its id under it, in brackets; its id is
the variant's id, `--` and that part, as `edit-entry` and `remove-entry` name it. The
capability's README gives which box lies where.

Usage:
  pkit lean canvas <variant> [--ids]

Exit codes:
  0  shown
  1  refused: the canvas cannot be read
  2  usage
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))

from _lib import acting, canvases, grid
from _lib.acting import Context


def parser() -> argparse.ArgumentParser:
    made = argparse.ArgumentParser(
        prog="pkit lean canvas",
        description="Draw a variant's canvas as a grid. Read-only.",
    )
    made.add_argument("variant", help="The variant's id, `<idea>--<variant>`.")
    made.add_argument(
        "--ids", action="store_true", help="Show each entry's own part of its id under it."
    )
    return made


def run(args: argparse.Namespace, ctx: Context) -> None:
    canvas, _ = canvases.read_variant(ctx.root, str(args.variant))
    ctx.say(grid.heading(canvas))
    if args.ids:
        ctx.say(
            f"Each entry's id is `{canvas.get('id')}--` and the part under it in brackets, "
            f"as `edit-entry` and `remove-entry` name it."
        )
    for line in grid.draw(canvas, with_ids=args.ids):
        ctx.say(line)


def main() -> int:
    return acting.main(parser(), run, date.today())


if __name__ == "__main__":
    sys.exit(main())
