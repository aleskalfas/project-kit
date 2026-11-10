#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "jsonschema==4.26.0",
#   "referencing==0.37.0",
#   "ruamel.yaml==0.19.1",
#   "uharfbuzz==0.57.0",
#   "fonttools==4.68.0",
#   "uniseg==0.10.1",
# ]
# ///
"""visual-communication capability — new: stamp a new piece's first files, from what a
person chooses (DEC-002 points 3 and 5, DEC-029 point 4).

It writes `pieces/<piece>/` in the location: `piece.yaml`, with the top, the brand, the
notations, the languages, the modes, the exports, `audience`, `shown` and `explains` it is
given, and `state: draft`; a content file for each language, holding each field of the
top it can leave empty, empty, a field of another type, such as a number, left out; and a
brief that holds its binding and says nothing yet (`_lib/stamping.py`).
It writes no lock: the first render writes it, as for a piece written by hand.

It writes in the location, so where the configuration records none it takes `visual/` and
records it before its first write, or the path `--location` names. It refuses a name taken
or not a piece's name, a choice the piece's schema refuses, and a library the location
lacks, naming `pkit visual add` for one the capability ships. Every check that can refuse
runs before the first write, so a refused run writes nothing, the location included. It
writes the new folder as one change, and never writes over a file.

Usage:
  pkit visual new <piece> --top <library>/<component> --brand <library>
                  --language <language>... --audience <text> --shown <text>
                  [--explains] [--export <format>]... [--notation <library>]...
                  [--mode <axis>=<mode>[,<mode>...]]... [--location <path>]

Exit codes:
  0  stamped
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

from _lib import files, location, stamping
from _lib import pipeline as pl
from _lib.root import project_root


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="pkit visual new",
        description="Stamp a new piece's first files: its piece.yaml, its content and its brief.",
    )
    parser.add_argument("piece", help="the new piece's name, which no piece of the location holds")
    parser.add_argument(
        "--top", required=True, metavar="<library>/<component>", help="the piece's top component"
    )
    parser.add_argument("--brand", required=True, metavar="<library>", help="the piece's brand")
    parser.add_argument(
        "--language",
        action="append",
        required=True,
        metavar="<language>",
        help="a language of its content, the first its source language; repeat for each",
    )
    parser.add_argument("--audience", required=True, help="who the piece is for, in words")
    parser.add_argument("--shown", required=True, help="where the piece is shown, in words")
    parser.add_argument(
        "--explains", action="store_true", help="the piece explains, rather than only shows"
    )
    parser.add_argument(
        "--export",
        action="append",
        default=[],
        metavar="<format>",
        help="a format an export makes; repeat for each, or give none to make none yet",
    )
    parser.add_argument(
        "--notation",
        action="append",
        default=[],
        metavar="<library>",
        help="a notation the content names concepts from; repeat for each",
    )
    parser.add_argument(
        "--mode",
        action="append",
        default=[],
        metavar="<axis>=<mode>[,<mode>...]",
        help="the modes the piece is drawn in on an axis; repeat for each axis",
    )
    parser.add_argument("--location", help="the location to take and record, where none is")
    args = parser.parse_args()
    modes: dict[str, list[str]] = {}
    for given in args.mode:
        axis, said, named = given.partition("=")
        if not said or not axis or not named:
            parser.error(f"--mode `{given}`: give it as <axis>=<mode>[,<mode>...]")
        modes.setdefault(axis, []).extend(named.split(","))
    chosen = stamping.Chosen(
        top=args.top,
        brand=args.brand,
        languages=tuple(args.language),
        audience=args.audience,
        shown=args.shown,
        explains=args.explains,
        exports=tuple(args.export),
        notations=tuple(args.notation),
        modes=modes,
    )
    root = project_root()
    try:
        return _new(root, args.piece, chosen, args.location)
    except (
        pl.Refused,
        location.LocationRefused,
        location.GitFailed,
        files.WriteFailed,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


def _new(root: Path, name: str, chosen: stamping.Chosen, given: str | None) -> int:
    where = location.for_writing(root, given)
    planned = stamping.plan(root, where.path, name, chosen)
    change = files.Change(root)
    said = location.record(change, where)
    stamping.write(planned, change)
    if said is not None:
        print(said)
    for line in stamping.report(planned):
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
