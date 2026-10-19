#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "jsonschema>=4.18",
#   "ruamel.yaml>=0.18",
# ]
# ///
"""software-analysis capability — diagram: the analysis's diagrams, from its front matter (DEC-003).

Prints the use-case diagram, each journey's flow and the requirement map as
Mermaid, each with its `accTitle` and `accDescr` and no styling, drawn from the
analysis's front matter each time (DEC-003 points 3, 4 and 7). Nothing is
stored, so a diagram never goes stale. `_lib/diagrams.py` states the rules.

It reads the analysis in the working tree, through the backbone's discovery,
`pkit friction artefacts --json`, writes nothing and needs no network: a query.

Usage:
  pkit analysis diagram [<subject>]           each diagram in a `mermaid` fence
  pkit analysis diagram [<subject>] --json    the document {schema_version, diagrams}

The subject is `use-cases`, `journeys`, `requirements`, a journey's id or a
requirement's id; with none, every diagram the analysis has something for.

Exit codes:
  0  answered, an analysis with nothing to draw included
  1  no answer: the analysis could not be read, a file of a place a diagram
     reads cannot be read as its kind, gives no id of its kind's shape or a
     list a diagram reads that is no list of ids, or the subject names no
     diagram, or a journey or a requirement the analysis does not hold in force
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
from _lib import backbone, diagrams, structure
from _lib.model import REQUIREMENTS, Unreadable

#: What is said when the subject's diagrams have nothing to draw.
_NOTHING = {
    None: "The analysis holds nothing to draw.",
    diagrams.USE_CASES: "The analysis holds no use case in force.",
    diagrams.JOURNEYS: "The analysis holds no journey in force.",
    diagrams.REQUIREMENT_MAP: "The analysis holds no requirement in force.",
}


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="pkit analysis diagram",
        description=(
            "Print the analysis's diagrams as Mermaid, drawn from its front matter: the "
            "use-case diagram, each journey's flow and the requirement map (software-analysis "
            "DEC-003). Each carries its accTitle and accDescr, and no styling. Computed from "
            "the working tree each time, and never stored. Read-only and offline."
        ),
    )
    parser.add_argument(
        "subject",
        nargs="?",
        metavar="SUBJECT",
        help="`use-cases`, `journeys`, `requirements`, a journey's id or a requirement's id "
        "(default: every diagram the analysis has something for).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the document {schema_version, diagrams}, each diagram with its id, title, "
        "description and mermaid text.",
    )
    args = parser.parse_args()

    try:
        kinds = structure.read_kinds()
        analysis = backbone.read_analysis(backbone.project_root())
        shown_as = {kind: kinds[kind].shown_as or kind for kind in REQUIREMENTS if kind in kinds}
        found = diagrams.diagrams(analysis, args.subject, shown_as)
    except structure.Unreadable as exc:
        print(f"error: the kinds' structures cannot be read: {exc}", file=sys.stderr)
        return 1
    except (Unreadable, diagrams.NoAnswer) as exc:
        print(f"error: {exc}; nothing is drawn.", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(diagrams.document(found), indent=2, ensure_ascii=False))
        return 0
    if not found:
        print(_NOTHING.get(args.subject, _NOTHING[None]))
        return 0
    print(diagrams.fenced(found), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
