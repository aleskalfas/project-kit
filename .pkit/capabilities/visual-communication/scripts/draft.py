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
names from the page. With `--from-top`, the key path starts at the content's top instead,
for a page's lead or title that the piece's top holds, such as the heading of a hero in a
one-page site's shared header, which is that page's title (DEC-068 point 4): its entry lies
in that page's part, and a key path that leads into the pages, which names a page's own
content, is refused. Without `--page`, a draft is the whole piece's, which only a piece
whose top is a page alone, such as a figure, has: its entry lies in the brief's part for
the whole piece, a takeaway is read from that part, and a lead's or a title's key path
from the content's top. On a piece whose top holds pages, such as a deck or a site, even
of one page, each draft lies in its page's part. So a draft given without `--page` is
refused on such a piece, and on a piece whose top cannot be read to tell whether it holds
pages. It finds the page, and whether the top holds pages, under the piece's lock, or,
before the piece's first render, under the versions that render would lock, so a draft is
digested as it is written. The digest is over the text normalised as
`_lib/drafts.py` says: Unicode form C, each run of white space one space, the ends
trimmed. A brief that cannot be read, or whose binding is broken, is refused, never read
as no brief.

Without `--check` it prints the entry for the part's `drafts`, for whoever designs the
piece to write, and writes nothing, since no command changes what a brief says. With
`--check` it says whether the text matches the recorded entry for its page, kind and
language, differs from it, or has none, and so whose the text is: the designer's only on a
match, and the asker's otherwise.

Usage:
  pkit visual draft <piece> --kind lead|title|takeaway --language <language>
      [--page <id>] [--at <key path> [--from-top]]
  pkit visual draft <piece> ... --check

Exit codes:
  0  the entry printed, or `--check` found the text a match, the designer's
  1  refused: the piece, its brief or the text asked for cannot be read, a draft of a piece
     whose top holds pages, or cannot be read, is given no page, a key path from the
     content's top leads into the pages, or, before the first render, the versions that
     render would lock cannot be found
  2  a usage error
  3  `--check` found the text the asker's: it differs from its entry, or has none
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))

from _lib import briefs, drafts, location
from _lib import pipeline as pl
from _lib.files import FileError, read_bound, without_binding
from _lib.fingerprint import BRIEF
from _lib.reading import ReadError
from _lib.root import project_root

ASKERS = 3


def brief_of(piece: pl.Piece) -> dict[str, Any] | None:
    """The piece's brief, its binding removed; None where the piece keeps no brief file.
    Raises ReadError or FileError where the brief cannot be read or its binding is broken,
    so the command refuses it, where `briefs.read` leaves it to the check of bindings."""
    path = piece.folder / BRIEF
    if not path.is_file():
        return None
    return without_binding(read_bound(path, briefs.KIND))


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="pkit visual draft",
        description="The digest of a draft's text, and whether a text matches the recorded one.",
    )
    parser.add_argument("piece", help="the piece's name: its folder under the location's pieces/")
    parser.add_argument("--kind", required=True, choices=drafts.KINDS)
    parser.add_argument("--language", required=True, help="the language of the text")
    parser.add_argument(
        "--page",
        help="the page's id, for a piece whose top holds pages, such as a deck or a site, even "
        "of one page; none only for a piece whose top is a page alone, such as a figure",
    )
    parser.add_argument("--at", help="the key path of a lead's or title's field, from the page")
    parser.add_argument(
        "--from-top",
        action="store_true",
        help="read the key path `--at` from the content's top, for a page's lead or title "
        "that the piece's top holds, such as a hero's heading in a site's shared header",
    )
    parser.add_argument("--check", action="store_true", help="compare with the recorded entry")
    args = parser.parse_args()
    try:
        root = project_root()
        found = location.for_reading(root)
        if found is None:
            raise pl.Refused(f"the project holds no visual work, so no piece `{args.piece}`")
        piece = pl.read_piece(root, found.path, args.piece)
        brief = brief_of(piece)
        text = drafts.text_of(
            piece, brief, args.page, args.kind, args.language, args.at, from_top=args.from_top
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
