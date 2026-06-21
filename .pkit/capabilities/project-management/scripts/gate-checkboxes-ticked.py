#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml>=0.18",
# ]
# ///
"""Project-management capability — gate-checkboxes-ticked (process predicate, DEC-033).

Deterministic close-gate (DEC-007): result=True iff the issue body has no unticked '- [ ]' checkbox. The checkbox close-gate for won't-do closure and PR-merge closing issues.

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
    parser = argparse.ArgumentParser(description='Check that every checkbox in an issue body is ticked (close-gate).')
    parser.add_argument("issue_number", help="The keyed subject: a GitHub issue number.")
    parser.add_argument("--json", action="store_true", help="Emit the structured JSON contract.")
    parser.add_argument("--actor", default=None, help="The actor being gated (gates only).")
    args = parser.parse_args()

    try:
        issue_number = int(args.issue_number)
    except (TypeError, ValueError):
        print(f"error: issue number must be an integer, got {args.issue_number!r}", file=sys.stderr)
        return 2

    payload = predicates.gate_checkboxes_ticked(issue_number)
    # A predicate that genuinely couldn't evaluate exits non-zero so the
    # engine treats it as INDETERMINATE (fail-closed, COR-033), not a clean
    # negative. Strip the internal marker from the emitted JSON.
    indeterminate = bool(payload.pop(predicates.INDETERMINATE_KEY, False))
    print(json.dumps(payload))
    return 2 if indeterminate else 0


if __name__ == "__main__":
    sys.exit(main())
