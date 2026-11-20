#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml==0.19.1",
# ]
# ///
"""lean-business:cycle-lifecycle — the gate on `in-review` -> `decided`, on `decide`: may the
person's decision close the cycle? (lean-business DEC-003 point 4).

Deciding is the person's move, from review. The engine asks the gate by `can-move` before
the command writes the review, and by `move` after, so it holds on both sides of the write
(`_lib.positions.deciding_cycle`):

- before, the cycle is in review: its window, as its suspensions work it out, ended before
  today, no suspension is ongoing, and nothing is decided;
- after, the review records one decision of persevere, pivot and pause, its reasons, its
  winning variant, and who decided and when, and passes the review's gate as the check
  asks it, on the day it was recorded with the suspensions as they stood then
  (`gates.deciding_cycle`, through `acts.as_stood`; DEC-002 point 14): each key result's
  reach recorded, a winning variant the cycle explored, neither shelved nor split for
  persevere or pivot, at least one decided experiment as a pivot's evidence, and the window
  ended before the decision.

Persevering where the winning variant missed the objective passes, and draws the command's
and the check's warning. The review waits on no experiment.

Today is the local date where it runs, read here and nowhere else (DEC-003 point 1). The
test suite gives a fixed day by calling `judge` in its own process.

READ-ONLY. The engine runs it from the repository's root as

  cycle_lifecycle_gate_in_review_decided_decide.py <idea>--<cycle> --json

and reads one JSON object on standard output, `{"result": <bool>, "reason": "..."}`.

Exit codes:
  0  answered
  2  no answer: the subject is no cycle's id; its location, its idea's files, its file,
     its review, its suspensions or its window cannot be read; or, where nothing is
     refused, the winning variant's canvas, or an experiment a pivot names, lies in its
     place but does not read. Why goes to standard error, and the engine refuses the move
     as indeterminate.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).parent))

from _lib import positions

PROG = "cycle-lifecycle-gate-in-review-decided-decide"
WHAT = "May the person's decision move the cycle from review to decided?"


def judge(root: Path, subject: str, on: date) -> positions.Answer:
    """The gate on the cycle `subject` on the day `on`, read from the project at `root`."""
    return positions.cycle_gate(positions.deciding_cycle)(root, subject, on)


def main() -> int:
    return positions.answer_gate(sys.argv[1:], PROG, WHAT, positions.as_of(judge, date.today()))


if __name__ == "__main__":
    sys.exit(main())
