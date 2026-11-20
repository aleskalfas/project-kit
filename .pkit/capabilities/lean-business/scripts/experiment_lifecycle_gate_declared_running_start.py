#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml==0.19.1",
# ]
# ///
"""lean-business:experiment-lifecycle — the gate on `declared` -> `running`, on `start`: has
the experiment's time box started? (lean-business DEC-003 point 3).

The move is the script's, and the dates make it: no command takes it, and the journal shows
no entry for it (DEC-003 point 6). The gate reads the facts the detection reads
(`_lib.positions.starting_experiment`): the experiment's time box, as its cycle's
suspensions move it, has started and not ended by today, no stopping rule makes it due,
and no decision is recorded. So it is closed while the experiment is declared, and a
declared experiment shows no legal move: it waits only on a date, or on its cycle's
resumption where an ongoing suspension left its time box no start yet.

Today is the local date where it runs, read here and nowhere else (DEC-003 point 1). The
test suite gives a fixed day by calling `judge` in its own process.

READ-ONLY. The engine runs it from the repository's root as

  experiment_lifecycle_gate_declared_running_start.py <idea>--<experiment> --json

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

PROG = "experiment-lifecycle-gate-declared-running-start"
WHAT = "Has the experiment's time box started, so that the dates move it from declared to running?"


def judge(root: Path, subject: str, on: date) -> positions.Answer:
    """The gate on the experiment `subject` on the day `on`, read from the project at
    `root`."""
    return positions.experiment_gate(positions.starting_experiment)(root, subject, on)


def main() -> int:
    return positions.answer_gate(sys.argv[1:], PROG, WHAT, positions.as_of(judge, date.today()))


if __name__ == "__main__":
    sys.exit(main())
