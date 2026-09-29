#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "jsonschema>=4.18",
#   "ruamel.yaml>=0.18",
# ]
# ///
"""software-analysis capability — validate: the analysis artefacts (DEC-001).

Checks each artefact's shape and own fields against its companion schema, ids
two artefacts share, a use case not anchored to its actor, a journey whose
use-case anchors do not match its steps, and the revalidation records' front
matter. `_lib/check.py` states every check and the record point it applies.

The backbone runs it as this capability's validator, the
`software-analysis:artefacts` member of `pkit validate` (ADR-058): from the
project root, with `--json` alone and the offline marker set, reading one
findings document from standard output. It is a query — bounded,
deterministic, read-only, needing no network — and `pkit init` and `pkit sync`
provision its dependencies in uv's cache. It reads the analysis in the working
tree alone, through the backbone's discovery, `pkit friction artefacts`; a
number another branch took first reads a base, and is `pkit analysis
check-numbers`' to report.

Usage:
  pkit analysis validate          the summary and the findings
  pkit analysis validate --json   the findings document {summary, findings}

Exit codes:
  0  answered; without --json, also: no error found
  1  without --json: an error found
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
from _lib import backbone, check  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="pkit analysis validate",
        description=(
            "Check the analysis artefacts (software-analysis DEC-001): shape and required "
            "parts, duplicate ids, actor and journey anchors, revalidation records. "
            "Read-only and offline; the working tree alone."
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the findings document {summary, findings}, as `pkit validate` reads it.",
    )
    args = parser.parse_args()

    outcome = check.check(backbone.project_root())
    if args.json:
        print(json.dumps(outcome.document(), indent=2, ensure_ascii=False))
        return 0
    print("\n".join(outcome.lines()))
    return 1 if outcome.errors else 0


if __name__ == "__main__":
    sys.exit(main())
