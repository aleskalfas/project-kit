#!/usr/bin/env -S uv run --offline --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml==0.19.1",
#   "uharfbuzz==0.57.0",
#   "fonttools==4.68.0",
#   "uniseg==0.10.1",
#   "resvg-py==0.5.0",
# ]
# ///
"""visual-communication capability — look: draw a piece's pages as images, in the clone's
local folder, for a person or an agent to read (DEC-015).

It reads the piece's own file with its lock, computes the scenes under that lock and never
moves it. It runs no helper and no producer, draws a produced picture as it stands, keeps
no finding, takes no number and records no location. Each image lies beside its frames and
one report, in `.pkit/capabilities/visual-communication/project/local/look/<piece>/`, and a
run replaces what an earlier run left there. The report says what the images cannot show as
the renderer set it: each loss, each text or run the tool dropped, and each run it may draw
otherwise. See `_lib/viewing.py`.

Its shebang reads no network. Where the script has no environment yet, `uv run --script`
asks the index once its cached answer is stale, and fails offline, though the cache holds
every package. So a machine draws from what `pkit sync` put in the cache, which it provisions
through `pkit visual pages`: a query command, so `pkit sync` resolves its script, which pins
every package this one does.

Usage:
  pkit visual look <piece> [--page <page>]... [--language <language>]... [--key <key>]...
                           [--every-language] [--every-key]

Exit codes:
  0  drawn; what the images cannot show, if anything, is printed and in the report
  1  refused: look/<piece>/ is as it was. Or a write failed: it names the file, and every file is
     as it was before the run, or each it could not put back is named
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))

from _lib import files, location, viewing
from _lib import pipeline as pl
from _lib.root import project_root


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="pkit visual look",
        description="Draw a piece's pages as images in the clone's local folder.",
    )
    parser.add_argument("piece", help="the piece's name: its folder under the location's pieces/")
    parser.add_argument(
        "--page",
        action="append",
        default=[],
        metavar="PAGE",
        help="a page to draw, by its number from 1 or its trace id; may repeat; default every",
    )
    parser.add_argument(
        "--language",
        action="append",
        default=[],
        metavar="LANGUAGE",
        help="a language to draw; may repeat; default the piece's source language",
    )
    parser.add_argument(
        "--key",
        action="append",
        default=[],
        metavar="KEY",
        help="a combination of modes to draw, by its key; may repeat; default the first",
    )
    parser.add_argument("--every-language", action="store_true", help="draw every language")
    parser.add_argument("--every-key", action="store_true", help="draw every key the piece names")
    args = parser.parse_args()
    root = project_root()
    try:
        return _look(root, args)
    except (
        pl.Refused,
        location.LocationRefused,
        location.GitFailed,
        files.WriteFailed,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


def _look(root: Path, args: argparse.Namespace) -> int:
    project = viewing.opened(root, args.piece)
    wanted = viewing.asked(
        project,
        languages=args.language,
        every_language=args.every_language,
        named_keys=args.key,
        every_key=args.every_key,
        pages=args.page,
    )
    pl.writable(root, root / viewing.FOLDER / args.piece / viewing.REPORT)
    viewed = viewing.view(project, viewing.scenes(project, wanted.languages), wanted)
    folder = viewing.write(root, args.piece, viewed)
    _print(folder, viewed.report)
    return 0


def _print(folder: str, report: Mapping[str, Any]) -> None:
    lock = report["lock"]
    print(f"look: {len(report['images'])} image(s) in {folder}")
    print(f"lock: {', '.join(f'{library} {lock[library]}' for library in sorted(lock))}")
    for image in report["images"]:
        if image["on-white"]:
            print(f"on white: {_at(image)} draws no ground of its own")
    for each in report["dropped"]:
        what = "text" if each["whole"] else "part of the text"
        print(
            f"dropped: {_at(each)}: the tool drew nothing of the {what} `{each['element']}`: "
            f"{each['text']!r}"
        )
    for each in report["losses"]:
        accepted = " (accepted)" if each["accepted"] else ""
        print(f"loss{accepted}: {_at(each)}: `{each['what']}` {each['did']}: {each['why']}")
    for each in report["drawn-otherwise"]:
        families = ", ".join(each["families"])
        print(
            f"drawn otherwise: {_at(each)}: `{each['element']}` is measured in {families}, and "
            f"the tool may set the whole line in one of them"
        )
    print(f"report: {folder}{viewing.REPORT}")


def _at(place: Mapping[str, Any]) -> str:
    """Which image something lies on."""
    return f"{place['page']} ({place['language']}, {place['key']})"


if __name__ == "__main__":
    sys.exit(main())
