#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml==0.19.1",
# ]
# ///
"""lean-business capability — set-archetype: change the story a variant tells of how its
business works: direct, multisided or marketplace (lean-business DEC-001 point 7; DEC-002
points 4 and 6).

Content, so it asks nothing and records no who or when. A direct model names no sides, so
the way to direct is refused while the canvas names one: each is removed first, with
`remove-side`. The way from direct leaves the model to name its sides, with `add-side`, and
the check warns until it names two.

The archetype is part of the model every verdict and each shortlisting cover, so the change
is warned of, never refused, naming each judgement it leaves stale.

Usage:
  pkit lean set-archetype <variant> direct|multisided|marketplace

Exit codes:
  0  written, or the variant has that archetype already
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
        prog="pkit lean set-archetype",
        description="Change the story a variant tells of how its business works.",
    )
    made.add_argument("variant", help="The variant's id, `<idea>--<variant>`.")
    made.add_argument("archetype", choices=canvases.ARCHETYPES)
    return made


def run(args: argparse.Namespace, ctx: Context) -> None:
    files = writes.Files(ctx.root, writes.for_writing(ctx.root))
    canvas = canvases.open_variant(files, str(args.variant))
    archetype = str(args.archetype)
    if canvas.data.get("archetype") == archetype:
        ctx.say(f"`{canvas.id}` is a {archetype} model already; nothing changed.")
        return
    sides = canvas.sides()
    if archetype == "direct" and sides:
        named = ", ".join(f"`{s}`" for s in sides)
        raise Refused(
            f"a direct model names no sides, and `{canvas.id}` names {named}: remove each "
            f"first, `pkit lean remove-side {canvas.id} <side>`"
        )
    editing.place(canvas.data, "archetype", archetype, canvases.ORDER)
    files.put(canvas.rel, canvas.doc)
    acting.content(ctx, files, f"`{canvas.id}` is a {archetype} model now.")


def main() -> int:
    return acting.main(parser(), run, date.today())


if __name__ == "__main__":
    sys.exit(main())
