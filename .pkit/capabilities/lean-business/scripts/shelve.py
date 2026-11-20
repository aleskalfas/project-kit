#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml==0.19.1",
# ]
# ///
"""lean-business capability — shelve: set a variant aside for good, with the reason
(lean-business DEC-003 points 2, 5 and 8; DEC-002 point 5).

The shelving is the person's, so it takes their word and records who shelved the variant
and when, with the reason. It moves the variant from any state but shelved and split into
shelved, which is final: a shortlisted one too, its shortlisting replaced. Its verdicts
stay as they were, and its content stays editable. A cycle that explores it keeps its plan,
and no new experiment is declared on it (DEC-003 point 7).

Where the variant was the last of its idea not shelved or split, the idea is dropped,
which the command says: dropping is no move, but what shelving the last variant leaves.
Taking a shelved story up again is a new variant that names it, `new-variant
--comes-from`.

Usage:
  pkit lean shelve <variant> --reason <text> [--person-decided]

Exit codes:
  0  written
  1  refused, or answered no: nothing was written
  2  usage
  3  nobody could be asked: the question is printed, and nothing was written
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))

from _lib import (
    acting,
    canvases,
    editing,
    engine,
    ids,
    layout,
    listing,
    positions,
    readings,
    writes,
)
from _lib.acting import Context
from _lib.writes import Refused

#: The trigger of the desk stage's moves into shelved.
TRIGGER = "shelve"


def parser() -> argparse.ArgumentParser:
    made = argparse.ArgumentParser(
        prog="pkit lean shelve",
        description="Set a variant aside for good, with the reason.",
    )
    made.add_argument("variant", help="The variant's id, `<idea>--<variant>`.")
    made.add_argument("--reason", required=True, help="Why, in a sentence.")
    acting.person_decided(made)
    return made


def run(args: argparse.Namespace, ctx: Context) -> None:
    variant = canvases.variant_id(str(args.variant))
    reason = str(args.reason).strip()
    if not reason:
        raise Refused("a shelving says why: give --reason its words")
    before = acting.position(ctx, engine.DESK, variant)
    if before.state in (positions.SHELVED, positions.SPLIT):
        raise Refused(f"`{variant}` is {before.state}, which is final")

    def build() -> tuple[writes.Files, str]:
        files = writes.Files(ctx.root, writes.for_writing(ctx.root))
        canvas = canvases.open_variant(files, variant)
        outcome = editing.mapping(
            [
                ("kind", "shelved"),
                ("reason", reason),
                ("by", ctx.who),
                ("when", ctx.on),
            ]
        )
        editing.place(canvas.data, "outcome", outcome, canvases.ORDER)
        files.put(canvas.rel, canvas.doc)
        return files, f"Shelved `{variant}`: {reason}"

    acting.person_move(
        ctx, engine.DESK, variant, TRIGGER, before, build, decided=args.person_decided
    )
    idea = ids.idea_of(variant)
    if _dropped(ctx, idea):
        ctx.say(
            f"Every variant of `{idea}` not split is shelved now, so the idea is dropped. A "
            f"new variant may take a shelved story up again, `pkit lean new-variant "
            f"{idea}--<variant> --archetype <archetype> --comes-from <shelved variant>`."
        )


def _dropped(ctx: Context, idea: str) -> bool:
    """Whether the idea is dropped, as its files stand after the shelving. Where they, or a
    canvas of theirs, cannot be read, it cannot be told, and nothing is said of it."""
    try:
        location = canvases.reading_location(ctx.root)
        held = layout.read(ctx.root, location, idea).ideas.get(idea)
    except (Refused, listing.ListingFailed, layout.IdRefused):
        return False
    if held is None:
        return False
    read = [v.canvas.data if v.canvas is not None else None for v in held.variants.values()]
    if any(data is None for data in read):
        return False
    return readings.dropped([data for data in read if data is not None])


def main() -> int:
    return acting.main(parser(), run, date.today())


if __name__ == "__main__":
    sys.exit(main())
