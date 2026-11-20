#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml==0.19.1",
# ]
# ///
"""lean-business:experiment-lifecycle — the gate on `due` -> `decided`, on `decide`: may the
person's decision close the experiment? (lean-business DEC-003 point 3; DEC-002 point 10).

Deciding is the person's move, from due. The engine asks the gate by `can-move` before the
command writes the decision, and by `move` after, so it holds on both sides of the write
(`_lib.positions.deciding_experiment`):

- on both sides, the cycle it names is not suspended, as the cycle's detection places it:
  nothing is recorded on a suspended cycle's experiments until the person resumes the
  cycle, and the refusal names that move;
- before, the experiment is due: its time box, as its cycle's suspensions move it, ended
  before today, or it is generative and its stopping rule is recorded as reached, and
  nothing is decided;
- after, the decision records its next action, correct-course, double-down or stop, who
  decided and when; the result is recorded, with who recorded it and when; and each passes
  its gate as the check asks it, on the day it was recorded with the suspensions as they
  stood then (`gates.result`, `gates.deciding`, through `acts.as_stood`; DEC-002 point
  14): the experiment was declared, its result recorded no later than the decision, a
  measurement spoiled only by a suspension its time box ran through, and its time box
  ended before the decision, or a generative experiment's stopping rule reached within it.

Pass or fail is worked out from the result and what was declared, never chosen, and the
gate's reason says what it works out to (`readings.experiment_outcome`).

Today is the local date where it runs, read here and nowhere else (DEC-003 point 1). The
test suite gives a fixed day by calling `judge` in its own process.

READ-ONLY. The engine runs it from the repository's root as

  experiment_lifecycle_gate_due_decided_decide.py <idea>--<experiment> --json

and reads one JSON object on standard output, `{"result": <bool>, "reason": "..."}`.

Exit codes:
  0  answered
  2  no answer: the subject is no experiment's id; its location, its idea's files, its
     file, its decision, its declaration, its stopping rule or its time box cannot be read;
     or the cycle's file, its review's decision, its suspensions or its window cannot be
     read. Why goes to standard error, and the engine refuses the move as indeterminate.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).parent))

from _lib import positions

PROG = "experiment-lifecycle-gate-due-decided-decide"
WHAT = "May the person's decision move the experiment from due to decided?"


def judge(root: Path, subject: str, on: date) -> positions.Answer:
    """The gate on the experiment `subject` on the day `on`, read from the project at
    `root`."""
    return positions.experiment_gate(positions.deciding_experiment)(root, subject, on)


def main() -> int:
    return positions.answer_gate(sys.argv[1:], PROG, WHAT, positions.as_of(judge, date.today()))


if __name__ == "__main__":
    sys.exit(main())
