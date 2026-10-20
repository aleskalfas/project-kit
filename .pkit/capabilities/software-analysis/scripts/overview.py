#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "jsonschema>=4.18",
#   "ruamel.yaml>=0.18",
# ]
# ///
"""software-analysis capability — overview: write each analysis's overview (DEC-003 point 8).

Writes the overview of each analysis the project keeps that holds an artefact,
`overview/README.md` in the analysis's folder: the reader's entry point. It shows
what the analysis holds, in the order it is built, each area with its goal, and
the analysis's diagrams, each with its text alternative. It carries a
fingerprint of what it draws, which `pkit analysis validate` compares with the
analysis. `_lib/overview.py` states the rules.

Run it after a hand edit of what an overview draws, and to resolve two branches'
conflict on one: the stamp rewrites the overview of the analysis it writes in.
It writes a file only where its bytes change, whole or not at all, and records
the analysis location where it is not recorded yet (COR-049 point 5).

Usage:
  pkit analysis overview

Exit codes:
  0  every overview written, or fresh already
  1  refused: the project keeps no overview (`overview: false`), the analysis
     could not be read, or an overview could not be drawn in full or written;
     each other overview is written all the same
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
from _lib import analyses, backbone, diagrams, overview, stamp, structure
from _lib.model import Unreadable
from _lib.numbering import CONFIG


def main() -> int:
    argparse.ArgumentParser(
        prog="pkit analysis overview",
        description=(
            "Write the overview of each analysis the project keeps that holds an artefact, "
            "`overview/README.md` in its folder (software-analysis DEC-003 point 8): what "
            "the analysis holds, in the order it is built, each area with its goal, and its "
            "diagrams. Writes only where an overview's bytes change; `pkit analysis "
            "validate` holds each fresh by its fingerprint."
        ),
    ).parse_args()

    root = backbone.project_root()
    listing = analyses.read(root)
    if not listing.keeps_overview:
        print(
            f"refused: the setting `{analyses.OVERVIEW}: false` in {CONFIG} keeps no overview "
            f"(DEC-003 point 8) — remove it to keep one; nothing is written.",
            file=sys.stderr,
        )
        return 1
    try:
        analysis = backbone.read_analysis(root)
        shown_as = overview.shown_as()
    except (Unreadable, structure.Unreadable) as exc:
        print(f"error: the analysis could not be read: {exc}; nothing is written.", file=sys.stderr)
        return 1
    if analysis.location is None:
        print("No place of the analysis is in the backbone's reading; nothing is written.")
        return 0
    failed = 0
    for folder in listing.kept():
        named = listing.named(folder)
        if not any(a.folder == folder for a in analysis.artefacts):
            print(f"{named} holds no artefact yet, so it keeps no overview.")
            continue
        try:
            written = overview.write(
                root, analysis, listing, folder, shown_as, record=backbone.record_location
            )
        except (diagrams.NoAnswer, stamp.Refused) as exc:
            print(f"error: the overview of {named} is not written: {exc}", file=sys.stderr)
            failed += 1
            continue
        print(f"{'wrote' if written.changed else 'fresh already:'} {written.path}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
