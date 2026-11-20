#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml==0.19.1",
# ]
# ///
"""lean-business:cycle-lifecycle — the classifier: which state of its process is a cycle in?
(lean-business DEC-003 points 1 and 4).

Every state of the definition names it under `mode: classified`, so the engine runs it once
each time it reads a cycle's position (the process area's shape page, "Detection modes").
It reads the cycle's file, at the place the layout gives it, and today's date, and answers
from them in the order the data says first (`_lib.positions.cycle_lifecycle`):

- a review that records the person's decision places the cycle in `decided`, whatever its
  suspensions and its dates say;
- else an ongoing suspension, one with no day of resuming, places it in `suspended`,
  whatever its dates say;
- else its window, as its suspensions work it out (DEC-002 point 12), places it in
  `planned` before the window's first day, `running` from its first day through its last,
  and `in-review` after it.

Today is the local date where it runs, read here and nowhere else, and never taken from
the arguments or the environment (DEC-003 point 1). The test suite gives a fixed day by
calling `classify` in its own process.

READ-ONLY. The engine runs it from the repository's root as

  cycle_lifecycle_detect.py <idea>--<cycle> --json

and reads one JSON object on standard output:

  {"state": "<state>", "reason": "..."}   the cycle stands there
  {"state": null, "reason": "..."}        it has no file, so it stands in no state

Exit codes:
  0  answered
  2  no answer: the subject is no cycle's id, or its location, its idea's files, its file,
     its review's decision, its suspensions or its window cannot be read. Why goes to
     standard error, and the engine reads every state as indeterminate.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).parent))

from _lib import positions

PROG = "cycle-lifecycle-detect"
WHAT = "Classify which state of its process a cycle is in, for the process engine."


def classify(root: Path, subject: str, on: date) -> positions.Position:
    """Where the cycle `subject` stands on the day `on`, read from the project at `root`."""
    return positions.cycle_lifecycle_of(root, subject, on)


def main() -> int:
    return positions.answer_detection(
        sys.argv[1:], PROG, WHAT, positions.as_of(classify, date.today())
    )


if __name__ == "__main__":
    sys.exit(main())
