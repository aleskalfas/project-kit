#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "jsonschema>=4.18",
#   "ruamel.yaml>=0.18",
# ]
# ///
"""software-analysis capability — uses: where an analysis uses a term (`RS-SAN-008`).

Lists each mention of a term's names, and of the names it replaces, in the artefacts in
force of one analysis, by artefact and line: what renaming, merging or withdrawing the
term leaves to mend. A mention is what `pkit analysis link` reads as one, read by the
links' own code, and each one is listed, not only the first. `_lib/uses.py` states the
rules.

It reads the analysis in the working tree through the backbone's discovery, `pkit
friction artefacts --json`, and asks where its citations lead, `pkit refs lookup --json`,
as the links do, since no mention is read inside a citation. It writes nothing and needs
no network: a query.

Usage:
  pkit analysis uses <TERM-id>           each use, by artefact and line
  pkit analysis uses <TERM-id> --json    the document {schema_version, term, uses}

Where the project lists several analyses (DEC-001 point 2), `--analysis <component>`
names the one read; it may be left out where the list holds one.

Exit codes:
  0  answered, a term with no use included
  1  no answer: `--analysis` names no analysis the project lists, or none where it lists
     several; the analysis or the kinds' declared structure could not be read, the
     citations could not be looked up, a file of the analysis cannot be read as an
     artefact of its place or read at all, or the analysis neither holds the term nor
     lists it in its glossary's head
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
from _lib import analyses, backbone, links, structure, uses
from _lib.model import Unreadable


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="pkit analysis uses",
        description=(
            "List where an analysis uses a term: each mention of its names, and of the names "
            "it replaces, in the artefacts in force, by artefact and line. A mention is what "
            "`pkit analysis link` reads as one, each listed, not only the first. Run it after "
            "a term is renamed, merged or withdrawn, to find each use to mend (software-"
            "analysis RS-SAN-008). Read-only and offline."
        ),
    )
    parser.add_argument(
        "term",
        metavar="TERM-ID",
        help="The term whose uses are listed, by its id, such as TERM-order.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the document {schema_version, term, uses}: the term with the names "
        "searched, and each use with its artefact, line, text and the name it matched.",
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
        kinds = links.parted(root)
        analysis = backbone.read_analysis(root)
        found, words = uses.searched(analysis, listing, folder, args.term)
        read = uses.texts(root, uses.files(analysis, folder))
        asked = uses.asked(analysis, listing, folder, read, kinds, words)
        lookups = backbone.lookup(root, asked)
        listed = uses.uses(analysis, listing, folder, read, kinds, found, words, lookups)
    except structure.Unreadable as exc:
        print(f"error: the kinds' structures cannot be read: {exc}", file=sys.stderr)
        return 1
    except (Unreadable, uses.NoAnswer, analyses.Unnamed) as exc:
        print(f"error: {exc}; nothing is answered.", file=sys.stderr)
        return 1
    if args.json:
        document = uses.document(found, listed, links.component(listing, folder))
        print(json.dumps(document, indent=2, ensure_ascii=False))
        return 0
    for line in uses.lines(found, listed, listing.named(folder)):
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
