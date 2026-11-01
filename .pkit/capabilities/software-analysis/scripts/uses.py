#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "jsonschema>=4.18",
#   "ruamel.yaml>=0.18",
# ]
# ///
"""software-analysis capability — uses: what to search for when a term changes (DEC-001
point 12).

Prints, from front matter alone, the names a reader searches the analysis for when a term
is renamed, merged into another or withdrawn: its names, the names it replaces, each name
another term holds, listed apart, and each analysis whose glossary's head lists it. It
reads no body (DEC-001 point 1; DEC-006 point 3), so the search, and mending each use, is
the reader's. `_lib/uses.py` states the rules.

It reads the analysis in the working tree through the backbone's discovery, `pkit
friction artefacts --json`. It writes nothing and needs no network: a query.

Usage:
  pkit analysis uses <TERM-id>           the names to search for
  pkit analysis uses <TERM-id> --json    the document {schema_version, term, names,
                                         replaces, not_searched, listed_in}

Where the project lists several analyses (DEC-001 point 2), `--analysis <component>`
names the one read; it may be left out where the list holds one.

Exit codes:
  0  answered, a withdrawn term included
  1  no answer: `--analysis` names no analysis the project lists, or none where it lists
     several; the analysis could not be read, a glossary of the analyses the project
     keeps cannot be read, or the analysis neither holds the term nor lists it in its
     glossary's head
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
from _lib import analyses, backbone, links, uses
from _lib.model import Unreadable


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="pkit analysis uses",
        description=(
            "Print what to search the analysis for when a term is renamed, merged or "
            "withdrawn: its names, the names it replaces, each name another term holds, and "
            "each analysis whose glossary's head lists it, read from front matter alone. "
            "Search the artefacts in force for each, and mend each use (software-analysis "
            "DEC-001 point 12). Read-only and offline."
        ),
    )
    parser.add_argument(
        "term",
        metavar="TERM-ID",
        help="The term whose names are printed, by its id, such as TERM-order.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the document {schema_version, term, names, replaces, not_searched, listed_in}.",
    )
    parser.add_argument(
        "--analysis",
        metavar="COMPONENT",
        default=None,
        help="The analysis to read, by its component, where the project lists several in "
        "its configuration (software-analysis DEC-001 point 2). Needed where it lists more "
        "than one.",
    )
    args = parser.parse_args()

    try:
        root = backbone.project_root()
        listing = analyses.read(root)
        folder = analyses.folder_named(listing, args.analysis, "to read")
        found = uses.searched(backbone.read_analysis(root), listing, folder, args.term)
    except (Unreadable, uses.NoAnswer, analyses.Unnamed) as exc:
        print(f"error: {exc}; nothing is answered.", file=sys.stderr)
        return 1
    if args.json:
        document = uses.document(found, links.component(listing, folder))
        print(json.dumps(document, indent=2, ensure_ascii=False))
        return 0
    for line in uses.lines(found, listing.named(folder)):
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
