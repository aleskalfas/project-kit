#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml==0.19.1",
# ]
# ///
"""lean-business:cycle-lifecycle — the gate on `planned` -> `running`, on `start`: has the
cycle's window started? (lean-business DEC-003 point 4).

The move is the script's, and the dates make it: no command takes it, and the journal shows
no entry for it (DEC-003 point 6). The gate reads the facts the detection reads
(`_lib.positions.starting_cycle`): the cycle's window, as its suspensions work it out, has
started and not ended by today, no suspension is ongoing, and no decision is recorded. So
it is closed while the cycle is planned, and a planned cycle shows no legal move: it waits
only on a date.

Today is the local date where it runs, read here and nowhere else (DEC-003 point 1). The
test suite gives a fixed day by calling `judge` in its own process.

READ-ONLY. The engine runs it from the repository's root as

  cycle_lifecycle_gate_planned_running_start.py <idea>--<cycle> --json

and reads one JSON object on standard output, `{"result": <bool>, "reason": "..."}`.

Exit codes:
  0  answered
  2  no answer: the subject is no cycle's id, or its location, its idea's files, its file,
     its review's decision, its suspensions or its window cannot be read. Why goes to
     standard error, and the engine refuses the move as indeterminate.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).parent))

from _lib import positions

PROG = "cycle-lifecycle-gate-planned-running-start"
WHAT = "Has the cycle's window started, so that the dates move it from planned to running?"


def judge(root: Path, subject: str, on: date) -> positions.Answer:
    """The gate on the cycle `subject` on the day `on`, read from the project at `root`."""
    return positions.cycle_gate(positions.starting_cycle)(root, subject, on)


def main() -> int:
    return positions.answer_gate(sys.argv[1:], PROG, WHAT, positions.as_of(judge, date.today()))


if __name__ == "__main__":
    sys.exit(main())
