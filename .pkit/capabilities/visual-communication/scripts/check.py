#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml==0.19.1",
#   "uharfbuzz==0.57.0",
#   "fonttools==4.68.0",
#   "uniseg==0.10.1",
# ]
# ///
"""visual-communication capability — check: what the project's visual work breaks, as one
validator of the project's validation (DEC-002 points 6 and 7, DEC-005 point 13).

Every run judges the files themselves: the binding of each file of the capability's format
in the location, the library folder and its list, each piece's lock, the brand it locks,
the ids of its content and its content against the components it fills. A piece's scenes
are judged from its findings record, `findings.yaml`, while the record's key verifies
against the files; otherwise they are computed now, while the validation's bound allows.
A final piece is read by its files and its lock alone (DEC-017 point 4). A published piece
is held to the version that wrote its current copy, and a draft is told of a file of that
copy still standing (DEC-017 points 5 to 7). A finding fails, asks for attention, or states
a fact; a finding that would fail in a released library version asks for attention instead.

The backbone runs it as this capability's validator, the `visual-communication:check`
member of `pkit validate` (COR-055 point 3): from the project root, with `--json` alone,
offline and bounded. It only reads, and runs no program of the project's.

Usage:
  pkit visual check [<piece>]          the summary and the findings
  pkit visual check --json [<piece>]   the findings document {summary, findings}

Exit codes:
  0  answered; without --json, also: nothing fails
  1  without --json: a finding fails
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))

from _lib import checks
from _lib.findings import SEVERITY
from _lib.root import project_root


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="pkit visual check",
        description=(
            "Check the project's visual work, as the visual-communication:check member of "
            "pkit validate. Read-only and offline."
        ),
    )
    parser.add_argument("piece", nargs="?", help="check this piece alone")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the findings document {summary, findings}, as `pkit validate` reads it.",
    )
    args = parser.parse_args()
    report = checks.check(
        project_root(), only=args.piece, deadline=checks.deadline_from(os.environ)
    )
    if args.json:
        print(json.dumps(checks.document(report), indent=2, ensure_ascii=False))
        return 0
    for line in report.summary:
        print(line)
    for finding, level in report.judged:
        print(f"  {SEVERITY[level]:<8}{checks.place(finding)}  [{finding.code}]")
        print(f"    → {checks.said(finding)}")
    return 1 if report.failed() else 0


if __name__ == "__main__":
    sys.exit(main())
