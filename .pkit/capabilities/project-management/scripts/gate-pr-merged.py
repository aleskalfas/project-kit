#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml>=0.18",
# ]
# ///
"""Project-management capability — gate-pr-merged (process predicate, DEC-033).

Authorisation-artifact gate (PR-merge, cross-authority): reports {exists, produced_by} for a merged PR closing this issue. The ENGINE computes result = exists && produced_by != actor (COR-033 P4); this predicate returns only the facts (who merged the PR).

READ-ONLY. The process engine (COR-033) invokes this as
  <script> <issue-number> --json
and reads the structured-JSON contract on stdout. Self-contained via PEP 723.

Exit codes:
  0  evaluated (result emitted as JSON); 2  usage error.
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
    parser = argparse.ArgumentParser(description='Report the merged-PR authorisation artifact for an issue (gate).')
    parser.add_argument("issue_number", help="The keyed subject: a GitHub issue number.")
    parser.add_argument("--json", action="store_true", help="Emit the structured JSON contract.")
    parser.add_argument("--actor", default=None, help="The actor being gated (gates only).")
    args = parser.parse_args()

    try:
        issue_number = int(args.issue_number)
    except (TypeError, ValueError):
        print(f"error: issue number must be an integer, got {args.issue_number!r}", file=sys.stderr)
        return 2

    payload = predicates.gate_pr_merged(issue_number, actor=args.actor)
    # A predicate that genuinely couldn't evaluate exits non-zero so the
    # engine treats it as INDETERMINATE (fail-closed, COR-033), not a clean
    # negative. Strip the internal marker from the emitted JSON.
    indeterminate = bool(payload.pop(predicates.INDETERMINATE_KEY, False))
    print(json.dumps(payload))
    return 2 if indeterminate else 0


if __name__ == "__main__":
    sys.exit(main())
