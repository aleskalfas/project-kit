#!/usr/bin/env -S uv run --script
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
"""visual-communication capability — pages: what `pkit visual look` can draw of a piece, and
the tools that would draw it (DEC-015 points 2 and 5, DEC-020 points 5 and 7).

It lists the piece's languages, its keys and its pages in each language, by number and
trace id, computed under the lock its `piece.yaml` holds. It says which renderer a run reads
by default, and each renderer's tool. It reads resvg's version from the module that holds
the tool, so it needs the wheel as `look` does. It finds the browser as a run would, and
starts none, so it names the program and no version. It only reads: being a query, `pkit
sync` resolves this script's packages into uv's cache, and so `look` finds them there with
no network.

Usage:
  pkit visual pages <piece>          the piece's languages, keys and pages
  pkit visual pages --json <piece>   the same as one JSON document

Exit codes:
  0  listed
  1  refused: the piece, its lock, its brand or its fonts cannot be drawn, or the
     configuration cannot be read
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))

from _lib import exports, location, viewing, viewing_tool
from _lib import pipeline as pl
from _lib.root import project_root


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="pkit visual pages",
        description="List what `pkit visual look` can draw of a piece.",
    )
    parser.add_argument("piece", help="the piece's name: its folder under the location's pieces/")
    parser.add_argument("--json", action="store_true", help="print one JSON document")
    args = parser.parse_args()
    try:
        listed = _listed(project_root(), args.piece)
    except (pl.Refused, location.LocationRefused, location.GitFailed) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(listed, ensure_ascii=False, indent=2))
    else:
        _print(listed)
    return 0


def _listed(root: Path, name: str) -> dict[str, Any]:
    project = viewing.opened(root, name)
    languages = project.piece.languages
    first = viewing.first_key(project)
    facts = exports.preview_filling(project.piece).facts
    # Every scene is computed, so what refuses `look` at any key refuses the list. The pages
    # of each language are those of the scene of the key drawn by default.
    return {
        "piece": name,
        "languages": languages,
        "keys": project.keys,
        "drawn-by-default": {"language": languages[0], "key": first},
        "pages": {
            language: list(result.scene.to_dict().get("pages", []))
            for language, result in viewing.scenes(project, languages, facts=facts)
            if result.scene.size_key == project.size_key(first)
        },
        "renderer": viewing.renderer_of(project.piece),
        "tools": {
            viewing.SVG: viewing_tool.TOOL,
            viewing.HTML: viewing.browser_found(root),
        },
    }


def _print(listed: Mapping[str, Any]) -> None:
    default = listed["drawn-by-default"]
    print(f"languages: {', '.join(listed['languages'])} (by default {default['language']})")
    print(f"keys: {', '.join(listed['keys'])} (by default {default['key']})")
    for language, pages in listed["pages"].items():
        print(f"pages in {language}:")
        for number, page in enumerate(pages, start=1):
            print(f"  {number}: {page}")
    print(f"renderer: {listed['renderer']} by default")
    resvg, browser = listed["tools"][viewing.SVG], listed["tools"][viewing.HTML]
    print(f"tool of svg: {resvg['name']} {resvg['version']}, through resvg-py {resvg['wheel']}")
    print(f"tool of html: {_browser(browser)}")


def _browser(found: Mapping[str, Any]) -> str:
    """The browser a run would start, in words."""
    if found["program"] is None:
        named = (
            "the browser the configuration names is no program that runs"
            if found["named"]
            else "no browser of the Chromium family was found"
        )
        return f"none, so a run stops: {named}; looked at: {', '.join(found['looked'])}"
    where = "named in the configuration" if found["named"] else "the first found"
    return f"a browser, {where}: {found['program']}"


if __name__ == "__main__":
    sys.exit(main())
