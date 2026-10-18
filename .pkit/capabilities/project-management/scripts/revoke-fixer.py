#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml>=0.18",
# ]
# ///
"""Project-management capability — revoke-fixer (DEC-056 point 2).

Revokes a fixer: records in the grant list (`fixers` in `project/config.yaml`)
a refusal for the agent's types — every type the `pkit::work-tracking:fixers`
point gives it and every type it is granted, or only those named with `--type`.
A revoke is a refusal, so nothing asks about those types again. It works while
the point does not resolve, on the grant list alone, so the grant validation
reports as naming nothing stays revocable. The change shows in the project's
diff, and counts once it merges into the default branch.

Usage:
  pkit pm revoke-fixer <agent> [--type <type>]... [--dry-run]

Exit codes:
  0  recorded, or already refused
  1  refused: nothing to revoke, or the grant list cannot be read or written;
     nothing written
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
    return run_answer_verb(verb=fixers.REVOKE_VERB, answer=fixers.REFUSED)


if __name__ == "__main__":
    sys.exit(main())
