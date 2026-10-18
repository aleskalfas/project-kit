#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "jsonschema>=4.18",
#   "ruamel.yaml>=0.18",
# ]
# ///
"""software-analysis capability — met-by: what meets each requirement (DEC-002 point 7).

Lists, for each requirement the analysis holds, the use cases and journeys in
force that list it in their `requirements`, worked out from those lists each
time. The requirement stores none of it, so nothing is written, and a page that
shows a requirement reads it here. `_lib/met_by.py` states the rules.

It reads the analysis in the working tree, through the backbone's discovery,
`pkit friction artefacts --json`, writes nothing and needs no network: a query.

Usage:
  pkit analysis met-by [<REQ-id>]           each requirement, or the one named, and what meets it
  pkit analysis met-by [<REQ-id>] --json    the document {schema_version, requirements}

Exit codes:
  0  answered, an analysis with no requirement included
  1  no answer: the analysis could not be read, a file of the use cases, the
     journeys or the requirements cannot be read as its kind, or the
     requirement named is not in the analysis
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
from _lib import backbone, met_by, structure
from _lib.model import REQUIREMENTS, Unreadable


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="pkit analysis met-by",
        description=(
            "List what meets each requirement: the use cases and journeys in force that list it "
            "in their `requirements` (software-analysis DEC-002 point 7). Computed from the "
            "working tree each time, and never stored. Read-only and offline."
        ),
    )
    parser.add_argument(
        "requirement",
        nargs="?",
        metavar="REQ-ID",
        help="One requirement to answer for (default: each requirement the analysis holds).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the document {schema_version, requirements}, each requirement with its "
        "`met_by`.",
    )
    args = parser.parse_args()

    try:
        kinds = structure.read_kinds()
        found = met_by.met_by(backbone.read_analysis(backbone.project_root()), args.requirement)
    except structure.Unreadable as exc:
        print(f"error: the kinds' structures cannot be read: {exc}", file=sys.stderr)
        return 1
    except (Unreadable, met_by.NoAnswer) as exc:
        print(f"error: {exc}; nothing is answered.", file=sys.stderr)
        return 1
    shown_as = {kind: kinds[kind].shown_as or kind for kind in REQUIREMENTS if kind in kinds}
    if args.json:
        print(json.dumps(met_by.document(found, shown_as), indent=2, ensure_ascii=False))
        return 0
    if not found:
        print("The analysis holds no requirement.")
        return 0
    for line in met_by.lines(found, shown_as):
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
