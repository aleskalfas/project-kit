#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml==0.19.1",
# ]
# ///
"""lean-business:desk-stage — the classifier: which state of its desk stage is a variant in?
(lean-business DEC-003 points 1 and 2).

Every state of the definition names it under `mode: classified`, so the engine runs it once
each time it reads a variant's position (the process area's shape page, "Detection
modes"). It reads the variant's canvas, at the place the layout gives it, and answers from
its outcome and its verdicts alone (`_lib.positions.desk_stage`):

- an outcome places the variant in `shortlisted`, `shelved` or `split`, whatever its
  verdicts say;
- else the longest run of the person's yes verdicts from desirability places it in
  `sketched`, `desirable`, `viable` or `feasible`. A stale verdict holds the position.

READ-ONLY. The engine runs it from the repository's root as

  desk_stage_detect.py <idea>--<variant> --json

and reads one JSON object on standard output:

  {"state": "<state>", "reason": "..."}   the variant stands there
  {"state": null, "reason": "..."}        it has no canvas, so it stands in no state

Exit codes:
  0  answered
  2  no answer: the subject is no variant's id, or its location, its files, its outcome or
     a verdict its position rests on cannot be read. Why goes to standard error, and the
     engine reads every state as indeterminate.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).parent))

from _lib import positions

PROG = "desk-stage-detect"
WHAT = "Classify which state of its desk stage a variant is in, for the process engine."

if __name__ == "__main__":
    sys.exit(positions.answer_detection(sys.argv[1:], PROG, WHAT, positions.desk_stage_of))
