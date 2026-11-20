#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml==0.19.1",
# ]
# ///
"""lean-business:desk-stage — the gate on `desirable` -> `viable`, on `pass-viability`: may
the person's yes on viability move the variant on? (lean-business DEC-003 point 2).

Viability judges the model against the idea's goal, so a yes on it needs, through the
predicates the check shares (`_lib.positions.passing`):

- the idea's goal set (`gates.judging`; DEC-002 point 3);
- the revenue streams holding an entry, through the one predicate the check's warning on
  an unpriced canvas reads (`readings.priced`), and the estimate's inputs given
  (`gates.yes_content`; DEC-002 point 14);
- a yes on desirability that is not stale (`gates.stale_before`; DEC-002 point 13).

The engine asks it by `can-move` before the command writes the yes, and by `move` after.
The write adds the verdict and nothing the gate reads, so both read one answer (the process
area's README, "Seam-ordering contract").

The desk stage reads no day. `judge` takes one all the same, as every predicate of the
capability does, so that each is asked alike: today, read in `main` and nowhere else
(DEC-003 point 1), or the fixed day the test suite gives by calling `judge` in its own
process. The gate leaves it unread.

READ-ONLY. The engine runs it from the repository's root as

  desk_stage_gate_desirable_viable_pass_viability.py <idea>--<variant> --json

and reads one JSON object on standard output, `{"result": <bool>, "reason": "..."}`.

Exit codes:
  0  answered
  2  no answer: the subject is no variant's id; its location, its files or its canvas
     cannot be read; or nothing else refuses the move, and the goal's file, or the
     fingerprint of the yes on desirability, cannot be read. Why goes to standard error,
     and the engine refuses the move as indeterminate.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).parent))

from _lib import positions

PROG = "desk-stage-gate-desirable-viable-pass-viability"
WHAT = "May the person's yes on viability move the variant from desirable to viable?"


def _passing(subject: positions.Variant) -> positions.Answer:
    return positions.passing(subject, "viability")


def judge(root: Path, subject: str, on: date) -> positions.Answer:
    """The gate on the variant `subject`, read from the project at `root`. The desk stage
    reads no day, so `on` goes unread."""
    return positions.desk_gate(_passing)(root, subject)


def main() -> int:
    return positions.answer_gate(sys.argv[1:], PROG, WHAT, positions.as_of(judge, date.today()))


if __name__ == "__main__":
    sys.exit(main())
