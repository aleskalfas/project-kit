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
local folder, for a person or an agent to read (DEC-015, DEC-020 point 5, DEC-027).

It reads the piece's own file with its lock, computes the scenes under that lock and never
moves it. It runs no helper and no producer, draws a produced picture as it stands, keeps
no finding, takes no number and records no location. Its images show what a preview fills,
and it says where one shows a stand-in, with why (`exports.preview_filling`). It reads a
piece through the HTML renderer where the piece declares `html`, and through the SVG
renderer otherwise; `--renderer` names either. Each renderer has a folder of its own in
`.pkit/capabilities/visual-communication/project/local/look/`: `<piece>/` for the SVG
renderer's pages, `<piece>.html/` for the HTML renderer's. Each image lies there beside its
frames and one report, and a run replaces only what an earlier run left in that folder. A
page too tall for one image is drawn in bands, each an image as wide as the page, and the
run names them in order. The report says what the images cannot show as the renderer set
it, a page too wide for its smallest text to read among it. See `_lib/viewing.py`.

- **The SVG renderer's pages** are drawn by resvg, through the wheel this script pins, with
  no network.
- **The HTML renderer's pages** are drawn by a browser of the Chromium family: the one the
  capability's configuration names under `browser`, or else the first found where Chrome
  and Chromium install themselves. No flag and no environment variable names one. A page
  file holds the modes a reader's signal names, and each key picked is drawn out of the file
  that holds it, its signals set through the browser. Each page file lies beside the images,
  for a person to open in their own browser.
- **Under forced colours,** with `--forced-colours`, the browser also draws each page file
  in its two forced palettes, light and dark, in a second start under its own flag that
  forces its colours. Each palette shows the key the file holds for the signals the browser
  sets with it. Its images lie in a folder of their own, `forced-light/` or `forced-dark/`,
  under the names any image takes, and the report names the palette of each image and of
  each entry that lies on one. resvg knows no forced colours, so the SVG renderer's pages
  are never drawn so.

Its shebang reads no network. Where the script has no environment yet, `uv run --script`
asks the index once its cached answer is stale, and fails offline, though the cache holds
every package. So a machine draws from what `pkit sync` put in the cache, which it provisions
through `pkit visual pages`: a query command, so `pkit sync` resolves its script, which pins
every package this one does.

Usage:
  pkit visual look <piece> [--page <page>]... [--language <language>]... [--key <key>]...
                           [--every-language] [--every-key] [--renderer svg|html]
                           [--forced-colours]

Exit codes:
  0  drawn; what the images cannot show, if anything, is printed and in the report
  1  refused, forced colours asked of the SVG renderer among it: the renderer's folder is as
     it was. Or a write failed: it names the file, and every file is as it was before the
     run, or each it could not put back is named
  2  usage error
  3  stopped: no browser ran, or one stopped part way, or the first read of either start
     failed. The HTML renderer's folder holds the page files and a report that says what
     stopped it, and no image. It names the ways on: a build pipeline's drawings, the same look
     run by a person outside any sandbox, and the SVG renderer's pages (DEC-024 point 4), and
     where the start that forces the browser's colours stopped, a run without them
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))

from _lib import exports, files, location, viewing
from _lib import pipeline as pl
from _lib.root import project_root

#: The exit of a run a browser drew nothing for: neither a refusal nor a usage error.
STOPPED = 3


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
    parser.add_argument(
        "--renderer",
        metavar="RENDERER",
        help="the renderer whose pages to draw, `svg` or `html`; default `html` for a piece "
        "that declares it, `svg` otherwise",
    )
    parser.add_argument(
        viewing.ASK_FORCED,
        dest="forced",
        action="store_true",
        help="draw each page file of the HTML renderer in the browser's two forced palettes "
        "too, light and dark, each in a folder of its own",
    )
    args = parser.parse_args()
    root = project_root()
    try:
        return _look(root, args)
    except (
        pl.Refused,
        location.LocationRefused,
        location.GitFailed,
        files.WriteFailed,
        OSError,
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
        renderer=args.renderer,
        forced=args.forced,
    )
    folder = viewing.folder_of(args.piece, wanted.renderer)
    pl.writable(root, root / folder / viewing.REPORT)
    filling = exports.preview_filling(project.piece)
    results = viewing.scenes(project, wanted.languages, wanted.keys, facts=filling.facts)
    viewed = viewing.view(project, results, wanted)
    written = viewing.write(root, folder, viewed)
    if viewed.stopped:
        _print_stop(written, viewed.report)
        return STOPPED
    _print(written, viewed.report, filling.said(exports.shown_stand_ins(results)))
    return 0


def _print(folder: str, report: Mapping[str, Any], stand_ins: str) -> None:
    """What a run prints: the report, and `stand_ins`, what it says of a stand-in an image
    shows, where one does."""
    print(f"look: {len(report['images'])} image(s) in {folder}")
    _print_lock_and_renderer(report)
    tool = report["tool"]
    if report.get("stands-for"):
        print(f"drawn by: {tool['name']} {tool['version']}, {tool['program']}")
        print(f"stands for: {report['stands-for']}")
    forced = report.get(viewing.FORCED)
    if forced:
        folders = ", ".join(f"{folder}{each}" for each in forced["folders"].values())
        print(
            f"forced colours: {', '.join(forced['palettes'])}, forced by {tool['name']}'s flag "
            f"`{forced['flag']}`; their images lie in {folders}"
        )
        print(f"forced colours do not show: {forced['does-not-show']}")
    for each in report.get("page-files", []):
        print(f"page file: {folder}{each['file']}, to open in your own browser")
    through_svg = report["renderer"]["name"] == viewing.SVG
    for image in report["images"]:
        band = image.get("band")
        if band and band["number"] > 1:
            continue
        if band:
            print(f"bands: {_at(image)}: {band['of']}, top to bottom: {_bands(report, image)}")
        if image.get(viewing.TOO_WIDE):
            print(
                f"too wide: {_at(image)} is drawn {image['pixels']['width']} pixels wide, so its "
                f"smallest text may not read"
            )
        if through_svg and image["on-white"]:
            print(f"on white: {_at(image)} draws no ground of its own")
        if not through_svg and image["on-browser-ground"] and image.get(viewing.FORCED):
            print(
                f"on the forced palette's ground: {_at(image)} draws no ground of its own, so "
                f"it lies on the ground of {tool['name']}'s `{image[viewing.FORCED]}` forced "
                f"palette"
            )
        elif not through_svg and image["on-browser-ground"]:
            print(
                f"on the browser's ground: {_at(image)} draws no ground of its own, so it lies "
                f"on {tool['name']}'s own ground in `{image['key']}`, not on white"
            )
    for each in report.get("words", []):
        print(
            f"words: {_at(each)}: the text `{each['element']}` holds {each['document']!r} in "
            f"the page file, and {each['scene']!r} in the scene"
        )
    for each in report["dropped"]:
        print(f"dropped: {_at(each)}: {_dropped(each)}")
    for each in report["losses"]:
        accepted = " (accepted)" if each["accepted"] else ""
        print(f"loss{accepted}: {_at(each)}: `{each['what']}` {each['did']}: {each['why']}")
    for each in report["drawn-otherwise"]:
        print(f"drawn otherwise: {_at(each)}: {_otherwise(each)}")
    for each in report.get("profiles", []):
        print(f"profile: {_at(each)}: `{each['element']}` shows `{each['picture']}`: {each['why']}")
    for each in report.get("refused", []):
        under = f", forced {each[viewing.FORCED]}" if each.get(viewing.FORCED) else ""
        print(f"refused: {each['language']}, {each['key']}{under}: a request for {each['url']}")
    if stand_ins:
        print(f"look: {stand_ins}")
    print(f"report: {folder}{viewing.REPORT}")


def _print_stop(folder: str, report: Mapping[str, Any]) -> None:
    """A stop, on standard error: what stopped the browser, what the folder holds, the ways on
    in their order, and what an agent does (DEC-020 point 8, DEC-024 points 4 and 6)."""
    stop = report["stopped"]
    said = [stop["what"]]
    if stop["looked"]:
        said.append(f"looked at: {', '.join(stop['looked'])}")
    if stop["program"]:
        said.append(f"started: {stop['program']}")
    if stop["said"]:
        said.append(f"it said: {stop['said']}")
    print(f"stopped: {'; '.join(said)}", file=sys.stderr)
    if stop["as-root"]:
        print(
            "stopped: the browser runs as root, where it refuses to start with its own sandbox "
            "on, and the step never turns that sandbox off",
            file=sys.stderr,
        )
    elif stop["sandbox"]:
        print("stopped: a sandbox stopped the browser", file=sys.stderr)
    print(
        f"stopped: no image; the page files and {viewing.REPORT} lie in {folder}",
        file=sys.stderr,
    )
    _print_lock_and_renderer(report, sys.stderr)
    for way in stop["go-on"]:
        print(f"go on: {way}", file=sys.stderr)
    print(f"for an agent: {stop['for-an-agent']}", file=sys.stderr)


def _print_lock_and_renderer(report: Mapping[str, Any], to: Any = None) -> None:
    lock, renderer = report["lock"], report["renderer"]
    out = to or sys.stdout
    print(f"lock: {', '.join(f'{library} {lock[library]}' for library in sorted(lock))}", file=out)
    print(f"renderer: {renderer['name']} {renderer['version']}", file=out)


def _dropped(each: Mapping[str, Any]) -> str:
    """What the report says of a text or a span left with nothing on its page."""
    if "whole" in each:
        what = "text" if each["whole"] else "part of the text"
        return f"the tool drew nothing of the {what} `{each['element']}`: {each['text']!r}"
    return f"a span of the text `{each['element']}` left {each['why']}: {each['text']!r}"


def _otherwise(each: Mapping[str, Any]) -> str:
    """What the report says of a run or a span drawn otherwise than the engine measured it."""
    element = each["element"]
    if "families" in each:
        families = ", ".join(each["families"])
        return (
            f"`{element}` is measured in {families}, and the tool may set the whole run on a "
            f"line in one of them"
        )
    if "fonts" in each:
        fonts = ", ".join(each["fonts"])
        return f"a span of `{element}` is drawn in {fonts}, a font of the machine: {each['text']!r}"
    return (
        f"a span of `{element}` has no face of {each['family']} at weight {each['weight']}: "
        f"{each['text']!r}"
    )


def _bands(report: Mapping[str, Any], first: Mapping[str, Any]) -> str:
    """The images of the bands of the page whose first band `first` shows, in order."""
    at = ("language", "key", "page", viewing.FORCED)
    return ", ".join(
        image["image"]
        for image in report["images"]
        if "band" in image and all(image.get(each) == first.get(each) for each in at)
    )


def _at(place: Mapping[str, Any]) -> str:
    """Which image something lies on, naming its forced palette where it has one."""
    forced = place.get(viewing.FORCED)
    under = f", forced {forced}" if forced else ""
    return f"{place['page']} ({place['language']}, {place['key']}{under})"


if __name__ == "__main__":
    sys.exit(main())
