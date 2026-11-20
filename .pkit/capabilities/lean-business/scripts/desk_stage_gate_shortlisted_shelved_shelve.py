#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml==0.19.1",
# ]
# ///
"""lean-business:desk-stage — the gate on `shortlisted` -> `shelved`, on `shelve`: may the
person shelve the variant? (lean-business DEC-003 point 2).

A shortlisted variant may be shelved, and a shelving records its reason
(`_lib.positions.shelving`). The engine asks the gate by `can-move` before the command
writes the shelving, when the canvas still records the shortlisting, and by `move` after,
when it records the variant shelved with a reason that is not blank (the process area's
README, "Seam-ordering contract"). Every shelve move of the desk stage reads this one
predicate.

READ-ONLY. The engine runs it from the repository's root as

  desk_stage_gate_shortlisted_shelved_shelve.py <idea>--<variant> --json

and reads one JSON object on standard output, `{"result": <bool>, "reason": "..."}`.

Exit codes:
  0  answered
  2  no answer: the subject is no variant's id; its location, its files or its canvas
     cannot be read; or its outcome is none of shortlisted, shelved and split. Why goes to
     standard error, and the engine refuses the move as indeterminate.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).parent))

from _lib import positions

PROG = "desk-stage-gate-shortlisted-shelved-shelve"
WHAT = "May the person shelve the variant, moving it from shortlisted to shelved?"

if __name__ == "__main__":
    sys.exit(
        positions.answer_gate(sys.argv[1:], PROG, WHAT, positions.desk_gate(positions.shelving))
    )
