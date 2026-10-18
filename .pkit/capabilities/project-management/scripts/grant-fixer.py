#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml>=0.18",
# ]
# ///
"""Project-management capability — grant-fixer (DEC-056 point 2).

Grants a fixer: records in the grant list (`fixers` in `project/config.yaml`)
that the agent may start on its own on the stale artefacts of its types — every
type the `pkit::work-tracking:fixers` point gives it, or only those named with
`--type`. Running it is the person's own answer yes, as answering the question
of `ask-fixers` is. The change shows in the project's diff, and the grant counts
once it merges into the default branch.

Usage:
  pkit pm grant-fixer <agent> [--type <type>]... [--dry-run]

Exit codes:
  0  recorded, or already granted
  1  refused: the point does not resolve, no entry names the agent or a type,
     or the grant list cannot be read or written; nothing written
  2  usage error, or the capability is not found
"""

from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
from _lib import fixers
from _lib.fixer_cli import run_answer_verb


def main() -> int:
    return run_answer_verb(verb=fixers.GRANT_VERB, answer=fixers.GRANTED)


if __name__ == "__main__":
    sys.exit(main())
