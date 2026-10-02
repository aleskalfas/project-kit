#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml>=0.18",
# ]
# ///
"""Project-management capability — detect-state (process classifier, DEC-033).

The issue lifecycle's classifier: which lifecycle state is the issue in? Every
state of the shipped lifecycle names it under `mode: classified` (COR-033 point
5), so the engine runs it once per reading of an issue's position. It reads the
issue once and resolves its live position by move-issue's exact inference
precedence (closed->done; first state:* label; milestone->backlog; else todo).
An issue in another repository — a native sub-issue that lives there, the
closure fold's member `owner/repo#<n>` — is read there by its open/closed alone:
closed is done, open is none of the lifecycle's states.

READ-ONLY. The process engine (COR-033) invokes this as
  <script> <issue-number | owner/repo#<n>> --json
and reads one JSON object on stdout:
  {"state": "<state-id>", "reason": "..."}   the issue is in that state
  {"state": null, "reason": "..."}           the inference yields a value the
                                             lifecycle does not declare (a
                                             derive binding's `open`/`blocked`,
                                             a stray state label), named in the
                                             reason
Self-contained via PEP 723.

Exit codes:
  0  answered (the JSON above on stdout)
  2  usage error, an un-bootstrapped project, or the issue could not be read:
     nothing on stdout, and why on stderr — the engine reads every lifecycle
     state as indeterminate and shows what this said
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
from _lib import bootstrap_gate
from _lib import lifecycle_predicates as predicates


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Classify which issue-lifecycle state an issue is in."
    )
    parser.add_argument(
        "issue_number",
        help="The keyed subject: a GitHub issue number, or owner/repo#<n> for an issue in "
        "another repository.",
    )
    parser.add_argument("--json", action="store_true", help="Emit the structured JSON contract.")
    args = parser.parse_args()

    # Prerequisite gate (#747): refuse on an un-bootstrapped project rather
    # than operating on assumed defaults. See _lib/bootstrap_gate.py.
    if not bootstrap_gate.enforce("detect-state"):
        return 2

    subject = predicates.read_subject(args.issue_number)
    if subject is None:
        print(
            "error: the subject must be an issue number, or owner/repo#<n> for an issue in "
            f"another repository, got {args.issue_number!r}",
            file=sys.stderr,
        )
        return 2

    payload = predicates.classify_state(subject)
    if payload.pop(predicates.INDETERMINATE_KEY, False):
        # No answer: the engine reads a non-zero exit as indeterminate for every
        # state, and shows what was said here beside it.
        print(
            f"detect-state: {payload.get('reason', 'could not classify the issue')}",
            file=sys.stderr,
        )
        return 2
    print(json.dumps(payload))
    return 0


if __name__ == "__main__":
    sys.exit(main())
