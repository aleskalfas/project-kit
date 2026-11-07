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
"""visual-communication capability — before-after: draw each of a piece's pages under two
locks, in the clone's local folder, and print each page that differs (DEC-019 point 5).

A person asks for one of two looks (`_lib/looks.py`):

- **`--ahead`, before a move.** Its before is the lock of the version that wrote a published
  piece's current copy, and otherwise the lock the piece holds. Its after is what a run
  would propose, or the versions named, each `<library>@<version>`, as `pkit visual add`
  takes one. It prints each newer version held back, with why, and each clash or lost end a
  version named goes past. A draft takes it only with versions named, and those may include
  one not yet released, which a published piece's may not. A final piece takes it with none
  named, and its two locks are one.
- **`--back`, at a change.** Its base is where the branch left the base the backbone
  answers for a comparison, or `--base <ref>`. Its before is the lock of the version that
  wrote the copy at that commit, or the lock held there. Its after is the lock the piece
  holds now. A piece the base does not hold has no before, and the command says so.

Both drawings take today's engine, the piece's files and pictures as they lie, and one
filling of an export's facts, what a preview fills (`exports.preview_filling`), so what
differs is the locks'. Where that is a stand-in, it says so, and why. It runs no program,
moves no lock, keeps no finding, takes no number and records no location. It says where the
two locks are one, where the engine's release differs from the one the copy's version
recorded, and which pictures are stale. A drawing it cannot make stops nothing: it says why,
and the other is still drawn. It writes each page in
`.pkit/capabilities/visual-communication/project/local/before-after/<piece>/`, under
`before/` and `after/`, replacing what an earlier run left there. No validator runs it.

Usage:
  pkit visual before-after <piece> --ahead [<library>@<version>]...
  pkit visual before-after <piece> --back [--base <ref>]

Exit codes:
  0  drawn, or a drawing it could not make named with why
  1  refused: the piece has no lock or takes no such look, the search refuses what is named,
     or the base resolves to nothing; nothing is written. Or a write failed: it names the
     file, and every file is as it was before the run, or each it could not put back is named
  2  a usage error
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))

from _lib import before_after, exports, files, libraries, location, looks
from _lib import pipeline as pl
from _lib.root import project_root


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="pkit visual before-after",
        description="Draw each of a piece's pages under two locks, and print each that differs.",
    )
    parser.add_argument("piece", help="the piece's name: its folder under the location's pieces/")
    parser.add_argument(
        "versions",
        nargs="*",
        metavar="<library>@<version>",
        help="with --ahead, the versions to draw in place of what a run would propose",
    )
    look = parser.add_mutually_exclusive_group(required=True)
    look.add_argument("--ahead", action="store_true", help="look ahead, before a move")
    look.add_argument("--back", action="store_true", help="look back, at a change")
    parser.add_argument(
        "--base",
        metavar="<ref>",
        help="with --back, the base to read, in place of the one the backbone answers",
    )
    # Versions follow `--ahead`, and a plain parse leaves them out on an older Python.
    args = parser.parse_intermixed_args()
    if args.ahead and args.base is not None:
        parser.error("--base names the base of a look back: use it with --back")
    if args.back and args.versions:
        parser.error("versions are named to a look ahead: use them with --ahead")
    root = project_root()
    try:
        return _before_after(root, args)
    except (
        pl.Refused,
        location.LocationRefused,
        location.GitFailed,
        files.WriteFailed,
        OSError,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


def _before_after(root: Path, args: argparse.Namespace) -> int:
    found = location.for_reading(root)
    if found is None:
        raise pl.Refused(f"the project holds no visual work, so no piece `{args.piece}`")
    piece = pl.read_piece(root, found.path, args.piece)
    held = libraries.Held(root, found.path)
    if args.back:
        look = looks.back(piece, held, args.base)
    else:
        look = looks.ahead(piece, held, args.versions)
    filling = exports.preview_filling(piece)
    before, after = looks.sides(look, filling.facts)
    change = files.Change(root)
    before_after.keep(change, piece.name, before, after)
    change.commit()
    for line in looks.report(look, before, after):
        print(line)
    said = before_after.stand_ins_said(filling, before, after)
    if said:
        print(said)
    return 0


if __name__ == "__main__":
    sys.exit(main())
