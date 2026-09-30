#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "jsonschema>=4.18",
#   "ruamel.yaml>=0.18",
# ]
# ///
"""software-analysis capability — check-numbers: a number the default branch took first.

A use case or journey numbered in the working tree whose number the default
branch took too since this branch left it — its tip holds it, or its history
since gave it a file gone since — for another line of work's artefact: the
first to reach the default branch keeps the number, and a number is never used
again, so this one renumbers before merging (DEC-001 point 3). An artefact is
known by its id, not its path; a file of the name this branch gives the
number is a warning — possibly its own work landed; `_lib/numbers.py` states
the rule.

It reads a base, so it answers about a change rather than the tree: it is its
own line of a project's check gate, beside `pkit friction check`, and not a
member of `pkit validate` (ADR-058 point 7). A query — bounded, deterministic,
read-only, needing no network — reading the analysis through the backbone's
discovery, `pkit friction artefacts`, at the working tree and at the base's
commits, and git for which commits those are, what the base's history added
since the fork and, for a number both sides took, whether the base's file is
a version this branch's history wrote, or of a name it gave the number.

Usage:
  pkit analysis check-numbers [--base <ref>]          the summary and the findings
  pkit analysis check-numbers [--base <ref>] --json   {schema_version, base, summary, findings}

The base is `--base`, else `$PKIT_CHECK_BASE`, else `origin/main`.

Exit codes:
  0  compared, and no number collides — a warning never fails — or the
     working tree numbers nothing
  1  a number collides; or the numbers cannot be compared — the base names no
     commit, or shares no history with HEAD — said on standard error, with
     nothing on standard output
  2  a usage error
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
from _lib import backbone, numbers  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="pkit analysis check-numbers",
        description=(
            "Report a use case or journey whose number the default branch took too since "
            "this branch left it, for another line of work's artefact (software-analysis "
            "DEC-001 point 3). Read-only and offline."
        ),
    )
    parser.add_argument(
        "--base",
        metavar="REF",
        default=None,
        help=(
            "The default branch to compare with "
            f"(default: ${backbone.BASE_ENV}, else {backbone.DEFAULT_BASE})."
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the document {schema_version, base, summary, findings}.",
    )
    args = parser.parse_args()

    try:
        comparison = numbers.compare(backbone.project_root(), args.base or backbone.default_base())
    except numbers.CannotCompare as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(comparison.document(), indent=2, ensure_ascii=False))
    else:
        print("\n".join(comparison.outcome.lines()))
    return 1 if comparison.outcome.errors else 0


if __name__ == "__main__":
    sys.exit(main())
