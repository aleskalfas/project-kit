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
use-case anchors do not match its steps, a number the default branch took for
another file since this branch left it, and the revalidation records' front
matter. `_lib/check.py` states every check and the record point it applies.

The backbone runs it as this capability's validator, the
`software-analysis:artefacts` member of `pkit validate` (ADR-058): from the
project root, with `--json` alone and the offline marker set, reading one
findings document from standard output. It is a query — bounded,
deterministic, read-only, needing no network — and `pkit init` and `pkit sync`
provision its dependencies in uv's cache. It reads the analysis through the
backbone's discovery, `pkit friction artefacts`, at the working tree and at
the default branch's commits, and git only for which commits those are.

Usage:
  pkit analysis validate [--base <ref>]          the summary and the findings
  pkit analysis validate [--base <ref>] --json   the findings document {summary, findings}

The default branch is `--base`, else `$PKIT_CHECK_BASE`, else `origin/main`.

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
        description=(
            "Check the analysis artefacts (software-analysis DEC-001): shape and required "
            "parts, duplicate ids, actor and journey anchors, numbers another branch took, "
            "revalidation records. Read-only and offline."
        ),
    )
    parser.add_argument(
        "--base",
        metavar="REF",
        default=None,
        help=(
            "The default branch numbers are compared with "
            f"(default: ${backbone.BASE_ENV}, else {backbone.DEFAULT_BASE})."
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the findings document {summary, findings}, as `pkit validate` reads it.",
    )
    args = parser.parse_args()

    outcome = check.check(backbone.project_root(), args.base or backbone.default_base())
    if args.json:
        print(json.dumps(outcome.document(), indent=2, ensure_ascii=False))
        return 0
    for line in outcome.summary:
        print(line)
    for finding in outcome.findings:
        print(f"  {finding.severity:<7}{finding.location}")
        print(f"    → {finding.message}")
    return 1 if outcome.errors else 0


if __name__ == "__main__":
    sys.exit(main())
