#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml==0.19.1",
# ]
# ///
"""lean-business:desk-stage — the gate on `desirable` -> `shelved`, on `shelve`: may the
person shelve the variant? (lean-business DEC-003 point 2).

A shelving records its reason (`_lib.positions.shelving`). The engine asks the gate by
`can-move` before the command writes the shelving, when nothing recorded refuses it, and by
`move` after, when the canvas records the variant shelved with a reason that is not blank
(the process area's README, "Seam-ordering contract"). Every shelve move of the desk stage
reads this one predicate.

The desk stage reads no day. `judge` takes one all the same, as every predicate of the
capability does, so that each is asked alike: today, read in `main` and nowhere else
(DEC-003 point 1), or the fixed day the test suite gives by calling `judge` in its own
process. The gate leaves it unread.

READ-ONLY. The engine runs it from the repository's root as

  desk_stage_gate_desirable_shelved_shelve.py <idea>--<variant> --json

and reads one JSON object on standard output, `{"result": <bool>, "reason": "..."}`.

Exit codes:
  0  answered
  2  no answer: the subject is no variant's id; its location, its files or its canvas
     cannot be read; or its outcome is none of shortlisted, shelved and split. Why goes to
     standard error, and the engine refuses the move as indeterminate.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).parent))

from _lib import positions

PROG = "desk-stage-gate-desirable-shelved-shelve"
WHAT = "May the person shelve the variant, moving it from desirable to shelved?"


def judge(root: Path, subject: str, on: date) -> positions.Answer:
    """The gate on the variant `subject`, read from the project at `root`. The desk stage
    reads no day, so `on` goes unread."""
    return positions.desk_gate(positions.shelving)(root, subject)


def main() -> int:
    return positions.answer_gate(sys.argv[1:], PROG, WHAT, positions.as_of(judge, date.today()))


if __name__ == "__main__":
    sys.exit(main())
