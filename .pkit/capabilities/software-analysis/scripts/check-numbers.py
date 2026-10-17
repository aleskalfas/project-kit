#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "jsonschema>=4.18",
#   "ruamel.yaml>=0.18",
# ]
# ///
"""software-analysis capability — check-numbers: a number given never changes meaning.

Two checks guard that promise (DEC-001 point 3). The first is of a number the
default branch took first: a use case or journey numbered in the working tree
whose number the default branch took too since this branch left it — its tip
holds it, or its history since gave it a file gone since — for another line of
work's artefact. The first to reach the default branch keeps the number, and a
number is never used again, so this one renumbers before merging. An artefact is
known by its id, not its path; a file of the name this branch gives the
number is a warning — possibly its own work landed; `_lib/numbers.py` states
the rule. An id the project's numbering setting frees is free again, as the
stamp counts it, and each entry's are listed; an entry naming what is no
commit of the default branch's history, or listing an id its commit does not
free, is an error, numbered here or not (`_lib/numbering.py`).

The second is of a use case's steps and variants, which journeys and evidence
cite by number and letter, so they stay append-only. Each use case in the
working tree is compared with the same use case, by id, where this branch left
the base, and a step or a variant renumbered or removed is reported. One added,
and a use case new in the change, pass. It binds where the append-only rule,
RS-SAN-002, binds and at its status, as the structure check binds under the
format rule: accepted, an error; with `--preview`, a proposed rule's findings
are reports opening `preview:`, which never fail. `_lib/append_only.py` states
the check.

It reads a base, so it answers about a change rather than the tree: it is its
own line of a project's check gate, beside `pkit friction check`, and not a
member of `pkit validate` (ADR-058 point 7). A query — bounded, deterministic,
read-only, needing no network — reading the analysis through the backbone's
discovery, `pkit friction artefacts`, at the working tree and at the base's
commits — which commits those are the same document names — where the format
rule binds through `pkit rule-sets reach`, and git for what the base's history
added since the fork and, for a number both sides took, whether the base's file
is a version this branch's history wrote, or of a name it gave the number, and
for a use case's steps, the text its file held at the fork.

Usage:
  pkit analysis check-numbers [--base <ref>]            the summary and the findings
  pkit analysis check-numbers [--base <ref>] --json     {schema_version, base, freed, summary,
                                                         findings}
  pkit analysis check-numbers [--base <ref>] --preview  a proposed format rule's findings too,
                                                         as reports

The base is `--base`, else `$PKIT_CHECK_BASE`, else the project's default
branch, as the backbone resolves it for every reader (COR-054).

Exit codes:
  0  compared, and no number collides and no step or variant is renumbered or
     removed where the append-only rule is accepted — a warning or a report
     never fails — or the working tree numbers nothing; and the numbering
     setting, if any, holds
  1  a number collides, a step or a variant is renumbered or removed where the
     append-only rule is accepted and binds, or an entry of the numbering setting
     names what is no commit of the default branch's history, or lists an id
     its commit does not free; or the numbers cannot be compared — the base
     names no commit, or shares no history with HEAD, or a use case's file
     where this branch left it cannot be read from this clone — said on
     standard error, with nothing on standard output
  2  a usage error
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
from _lib import backbone, numbers


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="pkit analysis check-numbers",
        description=(
            "Report a use case or journey whose number the default branch took too since "
            "this branch left it, for another line of work's artefact, and a use case's step "
            "or variant renumbered or removed since (software-analysis DEC-001 point 3). "
            "Read-only and offline."
        ),
    )
    parser.add_argument(
        "--base",
        metavar="REF",
        default=None,
        help=(
            "The base to compare with (default: $PKIT_CHECK_BASE, else the default branch, "
            "as the backbone resolves it)."
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the document {schema_version, base, freed, summary, findings}.",
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help=(
            "Preview the append-only rule, RS-SAN-002, as if it were accepted, where `pkit "
            "rule-sets reach --preview` says it would bind: each step or variant renumbered or "
            "removed, as a report opening `preview:`, which never changes the exit status."
        ),
    )
    args = parser.parse_args()

    try:
        comparison = numbers.compare(backbone.project_root(), args.base, preview=args.preview)
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
