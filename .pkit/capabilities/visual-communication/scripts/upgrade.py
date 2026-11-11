#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml==0.19.1",
#   "uharfbuzz==0.57.0",
#   "fonttools==4.68.0",
#   "uniseg==0.10.1",
# ]
# ///
"""visual-communication capability — upgrade: propose a move of a published piece's lock
(DEC-019 points 1 to 4, 6 and 7, and point 11's first and last bullets).

A proposal is what one run leaves in the working tree: the moved lock, a new version in the
record of exports, the current copy it wrote, and the findings record (`_lib/proposals.py`).
The run commits nothing, makes no branch and opens nothing on a work tracker. A person lands
it, and that is the review's yes. Discarding it leaves only a numbered version's files in the
clone's local folder.

It takes a published piece alone, and refuses any other, naming what moves that lock. It reads
the lock in the piece's own file, whoever wrote it. It moves that lock as a draft's render
does, among released versions alone, within its majors, to versions that fit, and states each
newer version it held back, with why. Each `<library>@<version>`, in the form `pkit visual add`
takes, moves what it names and only what that needs, past a clash or a lost end, and past the
lock's majors. No library version travels in the run: it moves only to versions the library
folder holds. Where the lock it proposes names another brand than the lock the piece holds, or
than the lock that wrote the copy, it names what does not follow that brand, as the look ahead
does (DEC-025 point 8).

Where it would propose the lock the piece holds, and the version that wrote the copy was made
under that lock, it says so and writes nothing. Otherwise the run is a lock move, a render with
no preview, then an export run, under every rule of an export but the gate, as one change.
`pkit visual before-after --ahead` looks ahead for it, and the drawing lies in the clone's
local folder. Its findings take the stand-ins for a version's number and its date. Its export
fills them with its own number and date, and its drawing shows what the export fills
(`exports.plan`, DEC-016 point 5).

It stops on an edit of the piece since the copy, naming each input that changed, unless
`--edited <input>` names it: a file by its path in the piece's folder, a font as the refusal
writes it. It stops on a produced picture stale under the moved lock, naming what changed,
unless `--use-stale <output>` names it. It runs no program. It stops on a number or a date
that overflows where its export fills it, unless `--use-overflowing <fact>` names the fact
(DEC-016 point 6). It stops on an element of a switching file that paints a combination
otherwise than the SVG file of it, unless `--use-differing <element>` names the element
(DEC-018 point 1). Each refusal prints the line that names them all. A fingerprint it cannot
read refuses, and names the record. With no copy standing, or none of its own, it goes on,
writes the copy whole, and says no file stood.

It names each finding that fails once the lock has moved, which holds the landing and stops
nothing here. `--dry-run` stops where the run would, says what it would write and prints each
page that differs. It keeps no drawing.

It writes in the location, so where the configuration records none it takes `visual/` and
records it before its first write, or the path `--location` names. Every check that can refuse
runs before that first write, so a refused run writes nothing, the location included. It writes
as one change: a write that fails leaves every file as it was before the run, or names each it
could not put back.

Usage:
  pkit visual upgrade <piece> [<library>@<version>]... [--edited <input>]...
                      [--use-stale <output>]... [--use-overflowing <fact>]...
                      [--use-differing <element>]... [--dry-run] [--location <path>]

Exit codes:
  0  proposed, nothing to move, or a dry run that would propose, whatever findings it names
  1  refused: nothing is written. Or a write failed: it names the file, and every file is as it
     was before the run, or each it could not put back is named
  2  a usage error
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))

from _lib import files, libraries, location, looks, proposals
from _lib import pipeline as pl
from _lib.root import project_root

#: What a dry run says before what a run would leave.
WOULD = "dry run: nothing is written, and a run would leave:"

#: What a run says once its proposal lies in the working tree.
LEFT = (
    "proposal: left in the working tree, with nothing committed. Land it as a change, or discard it"
)


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="pkit visual upgrade",
        description="Propose a move of a published piece's lock, as a diff in the working tree.",
    )
    parser.add_argument("piece", help="the piece's name: its folder under the location's pieces/")
    parser.add_argument(
        "versions",
        nargs="*",
        metavar="<library>@<version>",
        help="a version to move to, in place of what a run would propose; may repeat",
    )
    parser.add_argument(
        "--edited",
        action="append",
        default=[],
        metavar="INPUT",
        help="an input that changed since the current copy, to carry in the move; may repeat",
    )
    parser.add_argument(
        "--use-stale",
        action="append",
        default=[],
        metavar="OUTPUT",
        help="carry this produced picture as it is, though it is stale; may repeat",
    )
    parser.add_argument(
        "--use-overflowing",
        action="append",
        default=[],
        metavar="FACT",
        help="carry this fact's text as it is, `version` or `date`, though it overflows; "
        "may repeat",
    )
    parser.add_argument(
        "--use-differing",
        action="append",
        default=[],
        metavar="ELEMENT",
        help="carry a switching file as it is, though this element, by its trace id, paints a "
        "combination otherwise than the SVG file of it; may repeat",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="stop where the run would, and say what it would write, writing nothing",
    )
    parser.add_argument("--location", help="the location to take and record, where none is")
    # Versions may follow a flag, and a plain parse leaves them out on an older Python.
    args = parser.parse_intermixed_args()
    root = project_root()
    try:
        return _upgrade(root, args)
    except (
        pl.Refused,
        location.LocationRefused,
        location.GitFailed,
        files.WriteFailed,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


def _upgrade(root: Path, args: argparse.Namespace) -> int:
    where = location.for_writing(root, args.location)
    piece = proposals.read(root, where.path, args.piece)
    move = proposals.ahead(piece, libraries.Held(root, where.path), args.versions)
    if move.settled:
        for line in proposals.settled(move):
            print(line)
        return 0
    named = proposals.Named(
        args.versions, args.edited, args.use_stale, args.use_overflowing, args.use_differing
    )
    planned = proposals.plan(move, named)
    # The drawing shows what the run's export fills: its number and its date (DEC-016 point 5).
    before, after = looks.sides(move.look, planned.export.facts)
    if args.dry_run:
        for line in (
            *looks.report(move.look, before, after, kept=False, moved=piece.lock),
            WOULD,
            *proposals.report(planned),
        ):
            print(line)
        return 0
    change = files.Change(root)
    said = location.record(change, where)
    why = proposals.write(planned, before, after, change)
    if said is not None:
        print(said)
    for line in looks.report(move.look, before, after, kept=not why, moved=piece.lock):
        print(line)
    if why:
        print(f"no before-and-after kept: {why}")
    for line in (*proposals.report(planned), *proposals.failing(root, args.piece), LEFT):
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
