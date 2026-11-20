#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml==0.19.1",
# ]
# ///
"""lean-business:cycle-lifecycle — the gate on `suspended` -> `running`, on `resume`: may the
person's resumption move the cycle on? (lean-business DEC-003 point 4).

Resuming is the person's move. The person gives the day the cycle resumed, today unless
they name an earlier one, and the move's gate checks that the suspension now has a day of
resuming that DEC-002 point 12's rules allow. The window then falls later by the days the
suspension covered, and the resumption goes to running where it still holds the day the
resumption is recorded, and into review where it ended before, by the other move of
`resume`. The two moves are one predicate (`_lib.positions.resuming_cycle`), asked by
`can-move` before the command writes the resumption, and by `move` after, so it holds on
both sides of the write:

- before, the cycle is suspended, with no decision recorded and one suspension ongoing,
  and resumed today, the latest day its rules allow, the window, so moved, would still hold
  today. Where resuming on an earlier day would leave it ended, the reason names the first
  day of resuming that runs the cycle again;
- after, no suspension is ongoing, no break of the rules, through the predicate the check
  shares, names the suspension the cycle resumed from, the window, falling later by the
  days that suspension covered, still holds today, and it held the day the resumption was
  recorded, as the suspensions stood then.

Today is the local date where it runs, read here and nowhere else (DEC-003 point 1). The
test suite gives a fixed day by calling `judge` in its own process.

READ-ONLY. The engine runs it from the repository's root as

  cycle_lifecycle_gate_suspended_running_resume.py <idea>--<cycle> --json

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

PROG = "cycle-lifecycle-gate-suspended-running-resume"
WHAT = "May the person's resumption move the cycle from suspended to running?"


def _resuming(subject: positions.Cycle, on: date) -> positions.Answer:
    return positions.resuming_cycle(subject, on, positions.RUNNING)


def judge(root: Path, subject: str, on: date) -> positions.Answer:
    """The gate on the cycle `subject` on the day `on`, read from the project at `root`."""
    return positions.cycle_gate(_resuming)(root, subject, on)


def main() -> int:
    return positions.answer_gate(sys.argv[1:], PROG, WHAT, positions.as_of(judge, date.today()))


if __name__ == "__main__":
    sys.exit(main())
