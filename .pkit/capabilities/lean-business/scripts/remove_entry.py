#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml==0.19.1",
# ]
# ///
"""lean-business capability — remove-entry: take an entry out of a variant's canvas
(lean-business DEC-002 points 4 and 7).

Content, so it asks nothing and records no who or when. Where another entry's link or an
assumption's source still names the entry, the removal is warned of and never refused: the
method removes an entry its experiment refuted, and the assumption keeps naming what it
tested ("One link that may dangle"). Its id is never given again while anything names it.

A change to what a standing verdict judged is warned of, never refused, naming each
judgement it leaves stale.

Usage:
  pkit lean remove-entry <entry>

Exit codes:
  0  written
  1  refused: nothing was written
  2  usage
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Mapping
from datetime import date
from pathlib import Path

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))

from _lib import acting, canvases, layout, listing, readings, writes
from _lib.acting import Context
from _lib.fingerprint import BOXES
from _lib.writes import Refused


def parser() -> argparse.ArgumentParser:
    made = argparse.ArgumentParser(
        prog="pkit lean remove-entry",
        description="Take an entry out of a variant's canvas.",
    )
    made.add_argument("entry", help="The entry's id, `<idea>--<variant>--<entry>`.")
    return made


def run(args: argparse.Namespace, ctx: Context) -> None:
    entry_id = str(args.entry)
    variant = canvases.entry_variant(entry_id)
    files = writes.Files(ctx.root, writes.for_writing(ctx.root))
    canvas = canvases.open_variant(files, variant)
    box, held, index = canvases.find_entry(canvas, entry_id)
    del held[index]
    if not held:
        canvas.boxes().pop(box, None)
    files.put(canvas.rel, canvas.doc)
    still = [
        *_entries_naming(canvas.plain(), entry_id),
        *_assumptions_naming(ctx, files, canvas.idea, entry_id),
    ]
    acting.content(ctx, files, f"Removed `{entry_id}` from {box}.")
    if still:
        ctx.say(
            f"warning: {', '.join(still)} still {'names' if len(still) == 1 else 'name'} "
            f"`{entry_id}`, and {'is' if len(still) == 1 else 'are'} kept as "
            f"{'it is' if len(still) == 1 else 'they are'}"
        )


def _entries_naming(canvas: Mapping[str, object], entry: str) -> list[str]:
    """Each entry of the canvas whose link names `entry`."""
    found: list[str] = []
    for box in BOXES:
        for other in readings.entries(canvas, box):
            alternatives = other.get("alternatives")
            named = isinstance(alternatives, list) and entry in alternatives
            if named or other.get("problem") == entry:
                found.append(f"the entry `{other.get('id')}`")
    return found


def _assumptions_naming(ctx: Context, files: writes.Files, idea: str, entry: str) -> list[str]:
    """Each assumption of the idea whose source names `entry`."""
    try:
        contents = layout.read(ctx.root, files.location, idea)
    except (listing.ListingFailed, layout.IdRefused) as exc:
        raise Refused(f"the idea's files cannot be read: {exc}") from exc
    held = contents.ideas.get(idea)
    found: list[str] = []
    for variant in held.variants.values() if held is not None else []:
        data = variant.assumptions.data if variant.assumptions is not None else None
        listed = data.get("assumptions") if data is not None else None
        for assumption in listed if isinstance(listed, list) else []:
            source = assumption.get("source") if isinstance(assumption, Mapping) else None
            if isinstance(source, Mapping) and source.get("entry") == entry:
                found.append(f"the assumption `{assumption.get('id')}`")
    return found


def main() -> int:
    return acting.main(parser(), run, date.today())


if __name__ == "__main__":
    sys.exit(main())
