#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml==0.19.1",
# ]
# ///
"""lean-business:cycle-lifecycle — the gate on `in-review` -> `running`, on `shift-window`:
did an absence already over, recorded late, give the cycle back days its window had left?
(lean-business DEC-003 point 4).

A suspension recorded late with its first day and the day the cycle resumed at once moves
the window's end later by the days it covers, and may so take a cycle from its review back
to running. The move is the script's, and the command that records the suspension takes it
after the write, naming the origin it read before (the process area's README, "Seam-ordering
contract"). The gate reads the facts the detection reads, and the rules through the
predicate the check shares (`_lib.positions.shifting_window`): the window, as the
suspensions now work it out, holds today, no suspension is ongoing, no decision is
recorded, and no break of DEC-002 point 12's rules names the suspension recorded last. So
it takes the cycle back only where nothing recorded since needed the window ended, such as
the goal set at the review.

The gate is closed before the command writes, and `can-move` refuses then: open there, it
would be a way forward without the person, and a cycle in review would no longer wait on
them (the process area's shape page, "How each wait clears").

Today is the local date where it runs, read here and nowhere else (DEC-003 point 1). The
test suite gives a fixed day by calling `judge` in its own process.

READ-ONLY. The engine runs it from the repository's root as

  cycle_lifecycle_gate_in_review_running_shift_window.py <idea>--<cycle> --json

and reads one JSON object on standard output, `{"result": <bool>, "reason": "..."}`.

Exit codes:
  0  answered
  2  no answer: the subject is no cycle's id; its location, its idea's files, its file,
     its review's decision, its suspensions or its window cannot be read; or, where
     nothing is refused, a file or a day the rules weigh cannot be read. Why goes to
     standard error, and the engine refuses the move as indeterminate.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).parent))

from _lib import positions

PROG = "cycle-lifecycle-gate-in-review-running-shift-window"
WHAT = "Did an absence already over, recorded late, take the cycle from review back to running?"


def judge(root: Path, subject: str, on: date) -> positions.Answer:
    """The gate on the cycle `subject` on the day `on`, read from the project at `root`."""
    return positions.cycle_gate(positions.shifting_window)(root, subject, on)


def main() -> int:
    return positions.answer_gate(sys.argv[1:], PROG, WHAT, positions.as_of(judge, date.today()))


if __name__ == "__main__":
    sys.exit(main())
