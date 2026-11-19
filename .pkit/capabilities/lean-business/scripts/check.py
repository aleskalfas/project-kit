#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml==0.19.1",
# ]
# ///
"""lean-business capability — check: what the files of the location break, as one validator
of the project's validation (lean-business DEC-002 point 14; COR-055).

It reads the location the configuration records, or the default until one is, and judges
the files as they stand: each file's place and binding, the ids and the references between
the files, and every invariant the files can show broken, as an error; a guideline of the
book, or a judgement gone stale, as a warning. It never reads today's date. Each file's
shape is the backbone's data validation's, the `data` member of `pkit validate`, and the
check judges only what the shapes leave open. The capability's README, "The check", lists
each finding by its label.

The backbone runs it as this capability's validator, the `lean-business:check` member of
`pkit validate` (COR-055 point 3): from the project root, with `--json` alone, offline. It
only reads.

Usage:
  pkit lean check          the summary and the findings
  pkit lean check --json   the findings document {summary, findings}

Exit codes:
  0  answered; without --json, also: no finding is an error
  1  without --json: a finding is an error
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))

from _lib import checks
from _lib.findings import ERROR, document, ordered
from _lib.root import project_root


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="pkit lean check",
        description=(
            "Check the files of the lean-business location, as the lean-business:check member "
            "of pkit validate. Read-only and offline."
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the findings document {summary, findings}, as `pkit validate` reads it.",
    )
    args = parser.parse_args()
    report = checks.check(project_root())
    if args.json:
        print(json.dumps(document(report.summary, report.findings), indent=2, ensure_ascii=False))
        return 0
    for line in report.summary:
        print(line)
    found = ordered(report.findings)
    for finding in found:
        print(f"  {finding.severity:<8}{finding.location}  [{finding.label}]")
        print(f"    {finding.message}")
    return 1 if any(f.severity == ERROR for f in found) else 0


if __name__ == "__main__":
    sys.exit(main())
