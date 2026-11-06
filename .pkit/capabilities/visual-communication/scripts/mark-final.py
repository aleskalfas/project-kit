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
"""visual-communication capability — mark-final: mark a piece final, naming the version handed
out (DEC-017 points 1, 2 and 8).

It takes the version named, whatever changed since: it puts back the lock that version was
made under, and only the lock, and says what else changed, stopping on none of it. It moves
every file of the version from the clone's local folder into the piece's `handed-out/`, and
names the version in `exports.yaml` (`_lib/marking.py`). The project commits them: they are
the piece's freeze. It takes a piece set final by hand.

It writes in the location, so where the configuration records none it takes `visual/` and
records it before its first write, or the path `--location` names. Every check that can
refuse runs before that first write, so a refused run writes nothing, the location included.
It writes as one change: a write that fails leaves every file as it was before the run, or
names each it could not put back.

Usage:
  pkit visual mark-final <piece> <version> [--location <path>]

Exit codes:
  0  marked, whatever it says changed, or no longer holds of the lock
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

from _lib import files, libraries, location, marking
from _lib import pipeline as pl
from _lib.root import project_root


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="pkit visual mark-final",
        description="Mark a piece final, naming the version handed out.",
    )
    parser.add_argument("piece", help="the piece's name: its folder under the location's pieces/")
    parser.add_argument("version", type=int, help="the number of the version handed out")
    parser.add_argument("--location", help="the location to take and record, where none is")
    args = parser.parse_args()
    root = project_root()
    try:
        return _mark(root, args.piece, args.version, args.location)
    except (
        pl.Refused,
        location.LocationRefused,
        location.GitFailed,
        files.WriteFailed,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


def _mark(root: Path, name: str, number: int, given: str | None) -> int:
    where = location.for_writing(root, given)
    piece = pl.read_piece_file(root, where.path, name)
    planned = marking.plan(piece, libraries.Held(root, where.path), number)
    change = files.Change(root)
    said = location.record(change, where)
    marking.write(planned, change)
    if said is not None:
        print(said)
    for line in marking.report(planned):
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
