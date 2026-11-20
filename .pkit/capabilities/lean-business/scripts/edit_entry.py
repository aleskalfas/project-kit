#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml==0.19.1",
# ]
# ///
"""lean-business capability — edit-entry: change an entry of a variant's canvas: its words,
its side or its links (lean-business DEC-002 points 4, 6 and 7).

Content, so it asks nothing and records no who or when. The entry keeps its id whatever its
words become. A list link, a problem's alternatives or an early adopter's triggers, takes
each item given, `--drop-alternative` and `--drop-trigger` take one out, and `--clear`
removes a field whole.

A change to what a standing verdict judged is warned of, never refused, naming each
judgement it leaves stale.

Usage:
  pkit lean edit-entry <entry> [--text <text>] [--side <side>]
                       [--alternative <entry>]... [--problem <entry>] [--sub-headline <text>]
                       [--trigger <text>]... [--kind early|scalable] [--step <factory step>]
                       [--clear <field>]... [--drop-alternative <entry>]...
                       [--drop-trigger <text>]...

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

from _lib import acting, canvases, writes
from _lib.acting import Context
from _lib.writes import Refused


def parser() -> argparse.ArgumentParser:
    made = argparse.ArgumentParser(
        prog="pkit lean edit-entry",
        description="Change an entry of a variant's canvas: its words, its side or its links.",
    )
    made.add_argument("entry", help="The entry's id, `<idea>--<variant>--<entry>`.")
    made.add_argument("--text", help="The entry's new words. Its id stays as it is.")
    made.add_argument("--side", help="The side it belongs to, in a model with several.")
    canvases.link_flags(made)
    made.add_argument(
        "--clear",
        action="append",
        choices=canvases.CLEARABLE,
        default=[],
        help="Remove a field of the entry whole; repeat it for each.",
    )
    made.add_argument(
        "--drop-alternative",
        action="append",
        default=[],
        metavar="ENTRY",
        help="Take one existing alternative out of a problem's.",
    )
    made.add_argument(
        "--drop-trigger",
        action="append",
        default=[],
        metavar="TEXT",
        help="Take one trigger out of an early adopter's.",
    )
    return made


def run(args: argparse.Namespace, ctx: Context) -> None:
    entry_id = str(args.entry)
    variant = canvases.entry_variant(entry_id)
    files = writes.Files(ctx.root, writes.for_writing(ctx.root))
    canvas = canvases.open_variant(files, variant)
    box, held, index = canvases.find_entry(canvas, entry_id)
    entry = held[index]
    links = canvases.given_links(args)
    cleared = set(args.clear)
    given = set(links) | ({"side"} if args.side is not None else set())
    if not (
        given or cleared or args.text is not None or args.drop_alternative or args.drop_trigger
    ):
        raise Refused(
            "give what the entry changes: its words, its side, a link or a field to clear"
        )
    both = sorted(cleared & given)
    if both:
        raise Refused(f"{', '.join(both)} is given and cleared at once: give one or the other")
    if args.text is not None:
        text = str(args.text).strip()
        if not text:
            raise Refused("an entry has words")
        entry["text"] = text
    if args.side is not None:
        canvases.check_side(canvas, args.side)
        canvases.set_entry_field(entry, "side", args.side)
    for field in args.clear:
        if field != "side":
            canvases.check_link(box, field, f"--clear {field}")
        entry.pop(field, None)
    if args.drop_alternative:
        canvases.check_link(box, "alternatives", "--drop-alternative")
        _drop(
            entry, "alternatives", [canvases.entry_ref(variant, v) for v in args.drop_alternative]
        )
    if args.drop_trigger:
        canvases.check_link(box, "triggers", "--drop-trigger")
        _drop(entry, "triggers", list(args.drop_trigger))
    canvases.add_links(canvas, box, entry, links)
    files.put(canvas.rel, canvas.doc)
    acting.content(ctx, files, f"Changed `{entry_id}`.")


def _drop(entry: dict[str, object], field: str, values: list[str]) -> None:
    held = entry.get(field)
    for value in values:
        if not isinstance(held, list) or value not in held:
            raise Refused(f"the entry's {field} hold no `{value}`")
        held.remove(value)
    if isinstance(held, list) and values and not held:
        entry.pop(field, None)


def main() -> int:
    return acting.main(parser(), run, date.today())


if __name__ == "__main__":
    sys.exit(main())
