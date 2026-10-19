#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "jsonschema>=4.18",
#   "ruamel.yaml>=0.18",
# ]
# ///
"""software-analysis capability — diagram: the analysis's diagrams, from its front matter (DEC-003).

Prints the use-case diagram, each journey's flow, the requirement map and the
chain of use cases as Mermaid, each with its `accTitle` and `accDescr` and no
styling, drawn from the analysis's front matter each time (DEC-003 points 3 to
5 and 7). Nothing is
stored, so a diagram never goes stale. `_lib/diagrams.py` states the rules.

It reads the analysis in the working tree, through the backbone's discovery,
`pkit friction artefacts --json`, writes nothing and needs no network: a query.

Usage:
  pkit analysis diagram [<subject>]           each diagram in a `mermaid` fence
  pkit analysis diagram [<subject>] --json    the document {schema_version, diagrams}

The subject is `use-cases`, `journeys`, `requirements`, `chain`, a journey's id
or a requirement's id; with none, every diagram the analysis has something for.
The chain draws each use case's `after`, grouped by area (DEC-003 point 5).
Where the project lists several analyses (DEC-001 point 2), `--analysis
<component>` names the one drawn (DEC-003 point 6); it may be left out where
the list holds one.

Exit codes:
  0  answered, an analysis with nothing to draw included
  1  no answer: `--analysis` names no analysis the project lists, or none
     where it lists several; the analysis could not be read, a file of a place a diagram
     reads cannot be read as its kind, gives no id of its kind's shape or a
     list a diagram reads that is no list of ids, a use case's `after` the chain
     reads is no list of lists of ids, or the subject names no
     diagram, or a journey or a requirement the analysis does not hold in force
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
from _lib import analyses, backbone, diagrams, structure
from _lib.model import REQUIREMENTS, Unreadable

#: What is said when the subject's diagrams have nothing to draw.
_NOTHING = {
    None: "The analysis holds nothing to draw.",
    diagrams.USE_CASES: "The analysis holds no use case in force.",
    diagrams.JOURNEYS: "The analysis holds no journey in force.",
    diagrams.REQUIREMENT_MAP: "The analysis holds no requirement in force.",
    diagrams.CHAIN: "The analysis holds no use case in force that writes `after`.",
}


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="pkit analysis diagram",
        description=(
            "Print the analysis's diagrams as Mermaid, drawn from its front matter: the "
            "use-case diagram, each journey's flow, the requirement map and the chain of use "
            "cases (software-analysis DEC-003). Each carries its accTitle and accDescr, and no "
            "styling. Computed from "
            "the working tree each time, and never stored. Read-only and offline."
        ),
    )
    parser.add_argument(
        "subject",
        nargs="?",
        metavar="SUBJECT",
        help="`use-cases`, `journeys`, `requirements`, `chain`, a journey's id or a "
        "requirement's id (default: every diagram the analysis has something for).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the document {schema_version, diagrams}, each diagram with its id, title, "
        "description and mermaid text.",
    )
    parser.add_argument(
        "--analysis",
        metavar="COMPONENT",
        default=None,
        help="The analysis to draw, by its component, where the project lists several in its "
        "configuration (software-analysis DEC-001 point 2, DEC-003 point 6). Needed where it "
        "lists more than one.",
    )
    args = parser.parse_args()

    try:
        root = backbone.project_root()
        folder = analyses.folder_named(analyses.read(root), args.analysis, "to draw")
        kinds = structure.read_kinds()
        analysis = backbone.read_analysis(root)
        shown_as = {kind: kinds[kind].shown_as or kind for kind in REQUIREMENTS if kind in kinds}
        found = diagrams.diagrams(analysis, args.subject, shown_as, folder)
    except structure.Unreadable as exc:
        print(f"error: the kinds' structures cannot be read: {exc}", file=sys.stderr)
        return 1
    except (Unreadable, diagrams.NoAnswer, analyses.Unnamed) as exc:
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
