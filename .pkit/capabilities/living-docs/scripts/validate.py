#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "jsonschema>=4.18",
#   "ruamel.yaml>=0.18",
# ]
# ///
"""living-docs capability — validate: the project's documentation spaces (DEC-001).

Checks the places the spaces' pages are found in and their assignment to a
space, what is never a page, the pages' own fields and whether each page's
reader resolves, each space's entry point and definition, and whether the two
spaces are separate. `_lib/spaces.py` states every check and the record point
it applies.

The backbone runs it as this capability's validator, the `living-docs:spaces`
member of `pkit validate` (ADR-058): from the project root, with `--json`
alone and the offline marker set, reading one findings document from standard
output. It is a query — bounded, deterministic, read-only, needing no network —
and `pkit init` and `pkit sync` provision its dependencies in uv's cache. It
reads through the backbone's read commands: the roots, the places and the
documents in them through `pkit friction artefacts`, and the readers point
through `pkit connections resolve`, only when some page names a reader.

Usage:
  pkit living-docs validate           the summary, the findings, the unclassified documents
                                      and the pages left unanchored
  pkit living-docs validate --json    the findings document {summary, findings}

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
from _lib import spaces  # noqa: E402
from _lib.declarations import project_root  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate the project's documentation spaces (living-docs DEC-001): places and "
            "their assignment, pages' fields, entry points and definitions. Read-only and offline."
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the findings document {summary, findings}, as `pkit validate` reads it.",
    )
    args = parser.parse_args()

    outcome = spaces.check(project_root())
    if args.json:
        print(json.dumps(outcome.document(), indent=2, ensure_ascii=False))
        return 0
    for line in outcome.summary:
        print(line)
    for finding in outcome.findings:
        print(f"  {finding.severity:<7}{finding.location}")
        print(f"    → {finding.message}")
    if outcome.unclassified:
        print(
            f"unclassified document(s), for onboarding to classify ({len(outcome.unclassified)}):"
        )
        for rel in outcome.unclassified:
            print(f"  {rel}")
    if outcome.unanchored:
        print(
            f"page(s) unanchored without an accepted reason, for onboarding to anchor or accept "
            f"({len(outcome.unanchored)}):"
        )
        for rel in outcome.unanchored:
            print(f"  {rel}")
    accepted = outcome.accepted_unanchored
    if accepted:
        print(f"page(s) accepted unanchored, each with its reason ({len(accepted)}):")
        for rel, reason in accepted:
            print(f"  {rel} — {reason}")
    return 1 if outcome.errors else 0


if __name__ == "__main__":
    sys.exit(main())
