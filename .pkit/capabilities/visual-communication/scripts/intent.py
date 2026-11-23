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
"""visual-communication capability — intent: what a piece's brief hands the review first
(DEC-070 point 5).

It prints the goals, relations and takeaways of the piece and of each page its brief speaks
of, and none of the reasons. DEC-070 point 5 has the review judge each page against them, and
read the brief's file only once its findings are written. A part that states none is named as
stating none.

It reads the piece's `piece.yaml` and its brief, and needs no lock, no drawing and no network.

Usage:
  pkit visual intent <piece>          the intent, in words
  pkit visual intent --json <piece>   the same as one JSON document

Exit codes:
  0  printed, or the piece keeps no brief, which it says
  1  refused: the project holds no visual work, the piece cannot be read, or the
     configuration cannot be read
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))

from _lib import intent, location
from _lib import pipeline as pl
from _lib.root import project_root


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="pkit visual intent",
        description="Print the goals, relations and takeaways of a piece's brief, "
        "without their reasons.",
    )
    parser.add_argument("piece", help="the piece's name: its folder under the location's pieces/")
    parser.add_argument("--json", action="store_true", help="print one JSON document")
    args = parser.parse_args()
    try:
        handed = _handed(project_root(), args.piece)
    except (pl.Refused, location.LocationRefused, location.GitFailed) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps({"piece": args.piece, "intent": handed}, ensure_ascii=False, indent=2))
    elif handed is None:
        print(f"{args.piece} keeps no brief, or its brief cannot be read")
    else:
        print("\n".join(intent.lines(handed)))
    return 0


def _handed(root: Path, name: str) -> dict[str, Any] | None:
    found = location.for_reading(root)
    if found is None:
        raise pl.Refused(f"the project holds no visual work, so no piece `{name}`")
    return intent.of(pl.read_piece_file(root, found.path, name))


if __name__ == "__main__":
    sys.exit(main())
