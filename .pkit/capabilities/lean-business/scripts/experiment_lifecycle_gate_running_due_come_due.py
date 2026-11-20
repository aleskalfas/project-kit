#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml==0.19.1",
# ]
# ///
"""lean-business:experiment-lifecycle — the gate on `running` -> `due`, on `come-due`: has
the experiment's time box ended, or a generative experiment's stopping rule been reached?
(lean-business DEC-003 point 3).

The move is the script's. The dates make it, or the stopping rule the person records as
reached, which makes a generative experiment due early; an evaluative one runs its whole
time box. The gate reads the facts the detection reads, the early stopping rule included
(`_lib.positions.coming_due`):

- the detection places the experiment in `due`: its time box, as its cycle's suspensions
  move it, ended before today, or its stopping rule is recorded as reached, and no
  decision is recorded;
- where the stopping rule alone makes it due, the rule keeps its rules: its gate lets it
  through as the check asks it (`gates.stopping`, through `acts.as_stood`), reached within
  the time box, and no suspension of its cycle covers the day it was recorded, since
  nothing is recorded on a suspended cycle's experiments (DEC-002 point 12).

So the gate is closed while the experiment runs, and a running experiment shows no legal
move: it waits only on a date. Where a command records the stopping rule and then asks the
engine to move, naming the origin it read before the write, the gate is asked after the
write (the process area's README, "Seam-ordering contract").

Today is the local date where it runs, read here and nowhere else (DEC-003 point 1). The
test suite gives a fixed day by calling `judge` in its own process.

READ-ONLY. The engine runs it from the repository's root as

  experiment_lifecycle_gate_running_due_come_due.py <idea>--<experiment> --json

and reads one JSON object on standard output, `{"result": <bool>, "reason": "..."}`.

Exit codes:
  0  answered
  2  no answer: the subject is no experiment's id; its location, its idea's files, its
     file, its decision, its declaration, its stopping rule or its time box cannot be read;
     or it names something other than a cycle of its idea, or a cycle whose file or
     suspensions cannot be read. Why goes to standard error, and the engine refuses the
     move as indeterminate.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).parent))

from _lib import positions

PROG = "experiment-lifecycle-gate-running-due-come-due"
WHAT = "Has the experiment come due, by its dates or its stopping rule, so it moves from running?"


def judge(root: Path, subject: str, on: date) -> positions.Answer:
    """The gate on the experiment `subject` on the day `on`, read from the project at
    `root`."""
    return positions.experiment_gate(positions.coming_due)(root, subject, on)


def main() -> int:
    return positions.answer_gate(sys.argv[1:], PROG, WHAT, positions.as_of(judge, date.today()))


if __name__ == "__main__":
    sys.exit(main())
