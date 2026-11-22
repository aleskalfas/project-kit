#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml==0.19.1",
# ]
# ///
"""lean-business capability — status: where the ideas stand, and what waits on the person
(lean-business DEC-001 point 10; DEC-002 point 15).

Read-only, worked out from the files each time and kept nowhere. Each subject's position is
the process engine's. Without an idea it gives one line for each idea; with one, the
briefing that orients a person coming back to it (`briefing`): its first line, which says
where the idea is dropped, or where whether it is cannot be told; after a long silence on
a cycle, an offer to record the gap as a suspension; the person's last act; the goal; each
cycle and variant with where it stands, the cycle not yet decided in full, and each
assumption with its outcome; the canvas of each variant neither shelved nor split, drawn
as `canvas` draws it; each experiment with where it stands; and what waits on the person,
each with the command that takes it. The day the silence and the window's days are
counted to is today, read at the command's entry. `--json` prints the structured form,
whose keys the capability's README lists, with its `schema_version`.

Usage:
  pkit lean status [<idea>] [--json]

Exit codes:
  0  shown
  1  refused: the location cannot be read, or the idea named is not there
  2  usage
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))

from _lib import acting, briefing, canvases, ids, layout, listing
from _lib.acting import Context
from _lib.model import IdeaModel, Pools
from _lib.writes import Refused


def parser() -> argparse.ArgumentParser:
    made = argparse.ArgumentParser(
        prog="pkit lean status",
        description="Where the ideas stand, and what waits on you. Read-only.",
    )
    made.add_argument("idea", nargs="?", help="The idea's id; every idea where none is given.")
    made.add_argument(
        "--json",
        action="store_true",
        help="Print the structured form, its keys as the capability's README lists them.",
    )
    return made


def run(args: argparse.Namespace, ctx: Context) -> None:
    location = canvases.reading_location(ctx.root)
    if args.idea is not None and not ids.is_segment(args.idea):
        raise Refused(f"`{args.idea}` is no idea's id")
    try:
        contents = layout.read(ctx.root, location, args.idea)
    except (listing.ListingFailed, layout.IdRefused) as exc:
        raise Refused(f"the ideas cannot be read: {exc}") from exc
    if args.idea is not None and args.idea not in contents.ideas:
        raise Refused(f"there is no idea `{args.idea}` in `{location}/`")
    pools = Pools.of(contents)
    ideas = [
        briefing.of_idea(ctx.engine, IdeaModel(contents.ideas[name], pools), ctx.on)
        for name in sorted(contents.ideas)
    ]
    if args.json:
        ctx.say(json.dumps(briefing.document(location, ideas), indent=2, ensure_ascii=False))
        return
    if not ideas:
        ctx.say(
            f"No idea in `{location}/` yet: `pkit lean new-variant <idea>--<variant>` starts one."
        )
        return
    if args.idea is not None:
        for line in briefing.lines(ideas[0]):
            ctx.say(line)
        return
    for idea in ideas:
        ctx.say(briefing.line(idea))


def main() -> int:
    return acting.main(parser(), run, date.today())


if __name__ == "__main__":
    sys.exit(main())
