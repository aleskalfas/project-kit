#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml==0.19.1",
# ]
# ///
"""lean-business capability — add-side: name a group of customers a multisided or
marketplace variant serves (lean-business DEC-002 point 6).

Content, so it asks nothing and records no who or when. Each entry and each set of inputs
of such a variant then names its side. A direct model names none, which the check holds.

Usage:
  pkit lean add-side <variant> <name>

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

from _lib import acting, canvases, editing, ids, writes
from _lib.acting import Context
from _lib.writes import Refused


def parser() -> argparse.ArgumentParser:
    made = argparse.ArgumentParser(
        prog="pkit lean add-side",
        description="Name a group of customers a multisided or marketplace variant serves.",
    )
    made.add_argument("variant", help="The variant's id, `<idea>--<variant>`.")
    made.add_argument("name", help="The side's name, such as `cooks`.")
    return made


def run(args: argparse.Namespace, ctx: Context) -> None:
    files = writes.Files(ctx.root, writes.for_writing(ctx.root))
    canvas = canvases.open_variant(files, str(args.variant))
    name = str(args.name)
    if not ids.is_segment(name):
        raise Refused(
            f"`{name}` is no side's name: words of lower-case letters and digits, the first "
            f"beginning with a letter, joined by single hyphens"
        )
    if name in canvas.sides():
        raise Refused(f"`{canvas.id}` names the side `{name}` already")
    held = canvas.data.get("sides")
    if isinstance(held, list):
        held.append(name)
    else:
        editing.place(canvas.data, "sides", editing.seq([name]), canvases.ORDER)
    files.put(canvas.rel, canvas.doc)
    acting.content(ctx, files, f"`{canvas.id}` serves the side `{name}`.")


def main() -> int:
    return acting.main(parser(), run, date.today())


if __name__ == "__main__":
    sys.exit(main())
