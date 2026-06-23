#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml>=0.18",
# ]
# ///
"""Project-management capability — cascade-members (process predicate, DEC-034).

COR-037 cascade `members` predicate for the issue-lifecycle CLOSURE fold: the
parent-scoped candidate-member SOURCE. Given the parent issue number (the keyed
subject the engine threads), returns `{members: ["<n>", ...]}` — the issue
numbers of EVERY child of the parent (open and closed), discovered via the body
parent-ref (the SAME hierarchy walk close-issue's `_find_open_children` uses).
The engine resolves each member's lifecycle outcome and folds them; an open
child resolves to a non-terminal state and HOLDS the fold, reproducing pm's
"an open child blocks eligibility" without filtering by state here.

READ-ONLY. The process engine (COR-033) invokes this as
  <script> <parent-issue-number> --json
and reads the structured-JSON contract on stdout. Self-contained via PEP 723.

Exit codes:
  0  evaluated (members emitted as JSON); 2  usage error.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
from _lib import lifecycle_predicates as predicates  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="List the candidate child members of a parent issue (cascade members source)."
    )
    parser.add_argument("issue_number", help="The keyed subject: the PARENT issue number.")
    parser.add_argument("--json", action="store_true", help="Emit the structured JSON contract.")
    parser.add_argument("--actor", default=None, help="The actor being gated (gates only).")
    args = parser.parse_args()

    try:
        issue_number = int(args.issue_number)
    except (TypeError, ValueError):
        print(f"error: issue number must be an integer, got {args.issue_number!r}", file=sys.stderr)
        return 2

    payload = predicates.cascade_members(issue_number)
    # A predicate that genuinely couldn't evaluate exits non-zero so the engine
    # treats it as INDETERMINATE (fail-closed, COR-037: a broken members read
    # holds the whole fold, never a confident "no members"). Strip the marker.
    indeterminate = bool(payload.pop(predicates.INDETERMINATE_KEY, False))
    print(json.dumps(payload))
    return 2 if indeterminate else 0


if __name__ == "__main__":
    sys.exit(main())
