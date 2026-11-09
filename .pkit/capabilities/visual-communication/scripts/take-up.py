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
"""visual-communication capability — take-up: take a final piece up again, as a new piece
copied from it, a draft with its lock pinned (DEC-003 point 8, DEC-017 points 1, 3 and 8).

It takes a piece with a version handed out, and writes a new piece under the name a person
gives, that no piece holds. It copies the piece's folder whole, but for what only its past
holds: its record of exports, its findings record, and the folders of the files handed out
and of a current copy. In the new piece's `piece.yaml` it sets `state: draft`, pins the lock
of the version handed out, and drops `copy-place`, every other byte kept. So the new piece
draws as the piece it copies until a person moves its lock. Only the lock comes back: where
the sources changed since that version, the copy holds the later words, and the run names
each change (`_lib/taking_up.py`). The final piece stays as it was.

It writes in the location, so where the configuration records none it takes `visual/` and
records it before its first write, or the path `--location` names. Every check that can
refuse runs before that first write, so a refused run writes nothing, the location included.
It writes as one change: a write that fails leaves no part of the new piece, and every file
as it was before the run, or names each it could not put back.

Usage:
  pkit visual take-up <piece> <name> [--location <path>]

Exit codes:
  0  copied, whatever it says changed since the version handed out
  1  refused: nothing is written. Or a write failed: it names the file, and every file is as
     it was before the run, or each it could not put back is named
  2  a usage error
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))

from _lib import files, location, taking_up
from _lib import pipeline as pl
from _lib.root import project_root


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="pkit visual take-up",
        description="Take a final piece up again, as a new draft with its lock pinned.",
    )
    parser.add_argument("piece", help="the final piece: its folder under the location's pieces/")
    parser.add_argument("name", help="the new piece's name, which no piece of the location holds")
    parser.add_argument("--location", help="the location to take and record, where none is")
    args = parser.parse_args()
    root = project_root()
    try:
        return _take_up(root, args.piece, args.name, args.location)
    except (
        pl.Refused,
        location.LocationRefused,
        location.GitFailed,
        files.WriteFailed,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


def _take_up(root: Path, name: str, new: str, given: str | None) -> int:
    where = location.for_writing(root, given)
    piece = pl.read_piece_file(root, where.path, name)
    planned = taking_up.plan(piece, new)
    change = files.Change(root)
    said = location.record(change, where)
    taking_up.write(planned, change)
    if said is not None:
        print(said)
    for line in taking_up.report(planned):
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
