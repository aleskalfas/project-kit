#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml==0.19.1",
# ]
# ///
"""lean-business:experiment-lifecycle — the gate on `due` -> `running`, on `shift-time-box`:
did a suspension recorded late move the experiment's time box so that it runs again?
(lean-business DEC-003 point 3; DEC-002 point 12).

A suspension of the experiment's cycle, recorded late with its first day and the day the
cycle resumed, moves a time box that had not started by its first day later by the days it
covers, and may so make a due experiment run again. The move is the script's, as the moves
the dates make are. The gate reads the facts the detection reads, and the rules through
the predicate the check shares (`_lib.positions.shifting_time_box`):

- the detection places the experiment in `running`: its time box, as its cycle's
  suspensions now move it, holds today, no stopping rule makes it due, and no decision is
  recorded;
- the suspension of its cycle recorded last moves its time box, so that without it the
  time box would fall where it did; one that began after the time box started leaves its
  dates as they were, and brings no move back;
- no break of DEC-002 point 12's rules names that suspension (`suspensions.of_cycle`).

So the gate is closed at the move's origin: a due experiment, which waits on the person,
shows no move of the script's open.

Today is the local date where it runs, read here and nowhere else (DEC-003 point 1). The
test suite gives a fixed day by calling `judge` in its own process.

READ-ONLY. The engine runs it from the repository's root as

  experiment_lifecycle_gate_due_running_shift_time_box.py <idea>--<experiment> --json

and reads one JSON object on standard output, `{"result": <bool>, "reason": "..."}`.

Exit codes:
  0  answered
  2  no answer: the subject is no experiment's id; its location, its idea's files, its
     file, its decision, its declaration, its stopping rule or its time box cannot be read;
     it names something other than a cycle of its idea, or a cycle whose file or
     suspensions cannot be read; or, where nothing is refused, a file or a day the rules
     weigh cannot be read. Why goes to standard error, and the engine refuses the move as
     indeterminate.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).parent))

from _lib import positions

PROG = "experiment-lifecycle-gate-due-running-shift-time-box"
WHAT = "Did a suspension recorded late move the experiment's time box, so that it runs again?"


def _shifting(subject: positions.Experiment, on: date) -> positions.Answer:
    return positions.shifting_time_box(subject, on, positions.RUNNING)


def judge(root: Path, subject: str, on: date) -> positions.Answer:
    """The gate on the experiment `subject` on the day `on`, read from the project at
    `root`."""
    return positions.experiment_gate(_shifting)(root, subject, on)


def main() -> int:
    return positions.answer_gate(sys.argv[1:], PROG, WHAT, positions.as_of(judge, date.today()))


if __name__ == "__main__":
    sys.exit(main())
