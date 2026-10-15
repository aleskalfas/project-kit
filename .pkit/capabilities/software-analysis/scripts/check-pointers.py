#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "jsonschema>=4.18",
#   "ruamel.yaml>=0.18",
# ]
# ///
"""software-analysis capability — check-pointers: a planned record's commit off the default branch.

A planned revalidation record names where the design it reviewed stood, in
`reviewed-against` (DEC-001 point 6). Each source in this repository names a
commit, or `this change`. A commit the default branch holds stays reachable
after a squash merge; a branch's commit does not. This places each commit on
the default branch, and fails on one it does not hold in a record the change
adds — the one place its pointer can still be fixed. The same in a record the
merge-base holds is reported, never failed; a commit it cannot place, in a
shallow clone, is reported as unknown, never failed. `_lib/pointers.py` states
the rule.

It reads history beyond the working tree, and the pointers are provenance, so
it is its own line of a project's check gate, beside `pkit analysis
check-numbers`, and not a member of `pkit validate` (COR-055 points 1 and 2). A
query — bounded, deterministic, read-only, needing no network — reading the
records through the backbone's discovery, `pkit friction artefacts`, the
default branch and the base through `pkit repository base`, and git for where
each commit sits and which records the merge-base holds.

Usage:
  pkit analysis check-pointers [--base <ref>]          the summary and the findings
  pkit analysis check-pointers [--base <ref>] --json   {schema_version, default_branch, base,
                                                         summary, findings, pointers}

The commits are placed on the default branch alone, as the backbone resolves it
(COR-054 point 5). The base says only which records the change adds: `--base`,
else `$PKIT_CHECK_BASE`, else the default branch (COR-054 point 3).

Exit codes:
  0  placed, and no record the change adds names a commit the default branch does
     not hold — a report never fails — or there was nothing to place
  1  a record the change adds names a commit the default branch does not hold; or
     the commits cannot be placed — no default branch resolved, a base that names
     no commit or shares no history with HEAD — said on standard error, with
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
from _lib import backbone, pointers


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="pkit analysis check-pointers",
        description=(
            "Place on the default branch each commit a planned revalidation record names, and "
            "fail on one it does not hold in a record the change adds (software-analysis "
            "DEC-001 point 6). Read-only and offline."
        ),
    )
    parser.add_argument(
        "--base",
        metavar="REF",
        default=None,
        help=(
            "The base that says which records the change adds (default: $PKIT_CHECK_BASE, "
            "else the default branch, as the backbone resolves it). Commits are always placed "
            "on the default branch."
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help=(
            "Print the document {schema_version, default_branch, base, summary, findings, "
            "pointers}."
        ),
    )
    args = parser.parse_args()

    try:
        checked = pointers.check(backbone.project_root(), args.base)
    except pointers.CannotCheck as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(checked.document(), indent=2, ensure_ascii=False))
    else:
        print("\n".join(checked.outcome.lines()))
    return 1 if checked.outcome.errors else 0


if __name__ == "__main__":
    sys.exit(main())
