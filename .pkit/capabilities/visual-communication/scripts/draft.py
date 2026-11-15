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
"""visual-communication capability — draft: the digest of a draft's text, and whether a text
still matches the digest the brief records (DEC-042 point 7, DEC-029 points 3 and 4).

It reads the text from the piece, so no one hashes text by hand: a takeaway from the
brief's part, a lead or a title from the content in the language, at the key path `--at`
names from the page (from the content's top without `--page`, for a piece of one page).
The digest is over the text normalised as `_lib/drafts.py` says: Unicode form C, each run
of white space one space, the ends trimmed.

Without `--check` it prints the entry for the part's `drafts`, for whoever designs the
piece to write, and writes nothing, since no command changes what a brief says. With
`--check` it says whether the text matches the recorded entry for its page, kind and
language, differs from it, or has none, and so whose the text is: the designer's only on a
match, and the asker's otherwise.

Usage:
  pkit visual draft <piece> --kind lead|title|takeaway --language <language>
      [--page <id>] [--at <key path>]
  pkit visual draft <piece> ... --check

Exit codes:
  0  the entry printed, or `--check` found the text a match, the designer's
  1  refused: the piece, its brief or the text asked for cannot be read
  3  `--check` found the text the asker's: it differs from its entry, or has none
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))

from _lib import briefs, checks, drafts, location
from _lib import pipeline as pl
from _lib.files import FileError
from _lib.reading import ReadError
from _lib.root import project_root

ASKERS = 3


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="pkit visual draft",
        description="The digest of a draft's text, and whether a text matches the recorded one.",
    )
    parser.add_argument("piece", help="the piece's name: its folder under the location's pieces/")
    parser.add_argument("--kind", required=True, choices=drafts.KINDS)
    parser.add_argument("--language", required=True, help="the language of the text")
    parser.add_argument("--page", help="the page's id; none for a piece of one page")
    parser.add_argument("--at", help="the key path of a lead's or title's field, from the page")
    parser.add_argument("--check", action="store_true", help="compare with the recorded entry")
    args = parser.parse_args()
    try:
        root = project_root()
        found = location.for_reading(root)
        if found is None:
            raise pl.Refused(f"the project holds no visual work, so no piece `{args.piece}`")
        piece = pl.read_piece(root, found.path, args.piece)
        brief = briefs.read(piece)
        text = drafts.text_of(
            piece, brief, checks.top_of(piece), args.page, args.kind, args.language, args.at
        )
    except (
        pl.Refused,
        drafts.DraftRefused,
        location.LocationRefused,
        location.GitFailed,
        ReadError,
        FileError,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    where = "piece" if args.page is None else f"pages.{args.page}"
    if not args.check:
        made = drafts.entry(args.kind, args.language, text)
        print(f"add to `{where}.drafts` in the brief:")
        print(f"- kind: {made['kind']}")
        print(f"  language: {made['language']}")
        print(f"  digest: {made['digest']}")
        return 0
    state = drafts.state(drafts.part_of(brief, args.page), args.kind, args.language, text)
    asker = drafts.asker_owns(state)
    print(
        f"{state}: the {args.kind} in `{args.language}` of `{where}` is the "
        + ("asker's" if asker else "designer's")
    )
    return ASKERS if asker else 0


if __name__ == "__main__":
    sys.exit(main())
