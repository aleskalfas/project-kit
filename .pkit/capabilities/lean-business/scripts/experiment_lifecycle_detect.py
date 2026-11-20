#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml==0.19.1",
# ]
# ///
"""lean-business:experiment-lifecycle — the classifier: which state of its process is an
experiment in? (lean-business DEC-003 points 1 and 3).

Every state of the definition names it under `mode: classified`, so the engine runs it once
each time it reads an experiment's position (the process area's shape page, "Detection
modes"). It reads the experiment's file, at the place the layout gives it, the suspensions
of the cycle it names, and today's date, and answers from them in the order the data says
first (`_lib.positions.experiment_lifecycle`):

- a decision that records the person's next action places the experiment in `decided`,
  whatever its dates say;
- else an experiment whose declaration is not recorded is `drafted`;
- else a generative experiment whose stopping rule is recorded as reached is `due`,
  whatever its dates say;
- else its time box, as its cycle's suspensions move it (DEC-002 point 12), places it in
  `declared` before its first day, or while an ongoing suspension leaves it no start,
  `running` from its first day through its last, and `due` after it.

The time box is worked out by the predicate that also works out where the cycle's window
falls, so an experiment and its cycle never disagree on a day. Today is the local date
where it runs, read here and nowhere else, and never taken from the arguments or the
environment (DEC-003 point 1). The test suite gives a fixed day by calling `classify` in its
own process.

READ-ONLY. The engine runs it from the repository's root as

  experiment_lifecycle_detect.py <idea>--<experiment> --json

and reads one JSON object on standard output:

  {"state": "<state>", "reason": "..."}   the experiment stands there
  {"state": null, "reason": "..."}        it has no file, so it stands in no state

Exit codes:
  0  answered
  2  no answer: the subject is no experiment's id; its location, its idea's files, its
     file, its decision, its declaration, its stopping rule or its time box cannot be read;
     or it names something other than a cycle of its idea, or a cycle whose file or
     suspensions cannot be read. Why goes to standard error, and the engine reads every
     state as indeterminate.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).parent))

from _lib import positions

PROG = "experiment-lifecycle-detect"
WHAT = "Classify which state of its process an experiment is in, for the process engine."


def classify(root: Path, subject: str, on: date) -> positions.Position:
    """Where the experiment `subject` stands on the day `on`, read from the project at
    `root`."""
    return positions.experiment_lifecycle_of(root, subject, on)


def main() -> int:
    return positions.answer_detection(
        sys.argv[1:], PROG, WHAT, positions.as_of(classify, date.today())
    )


if __name__ == "__main__":
    sys.exit(main())
