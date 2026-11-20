#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml==0.19.1",
# ]
# ///
"""lean-business:desk-stage — the gate on `sketched` -> `split`, on `split`: may the person
split the variant into the variants named? (lean-business DEC-003 point 2).

A split names the variants it was split into, each of which exists and names this one as
the variant it comes from (`_lib.positions.splitting`, through `gates.split`, the predicate
the check shares; DEC-002 point 14). The engine asks the gate by `can-move` before the
command writes the split, and by `move` after (the process area's README, "Seam-ordering
contract"). Before the write the variant has no outcome, and the variants the split will
name are the command's alone, so nothing recorded refuses it; `gates.split` takes the
variants it judges from its caller, so the command can judge them before it writes. After,
the canvas records the variant split into at least one variant, each a reference to a
canvas of its idea, and each another variant that names this one as the one it comes from.
Every split move of the desk stage reads this one predicate.

The desk stage reads no day. `judge` takes one all the same, as every predicate of the
capability does, so that each is asked alike: today, read in `main` and nowhere else
(DEC-003 point 1), or the fixed day the test suite gives by calling `judge` in its own
process. The gate leaves it unread.

READ-ONLY. The engine runs it from the repository's root as

  desk_stage_gate_sketched_split_split.py <idea>--<variant> --json

and reads one JSON object on standard output, `{"result": <bool>, "reason": "..."}`.

Exit codes:
  0  answered
  2  no answer: the subject is no variant's id; its location, its files or its canvas
     cannot be read; its outcome is none of shortlisted, shelved and split; or nothing
     else refuses the split, and the canvas of a variant it names lies in its place but
     cannot be read. Why goes to standard error, and the engine refuses the move as
     indeterminate.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).parent))

from _lib import positions

PROG = "desk-stage-gate-sketched-split-split"
WHAT = "May the person split the variant into those named, moving it from sketched to split?"


def judge(root: Path, subject: str, on: date) -> positions.Answer:
    """The gate on the variant `subject`, read from the project at `root`. The desk stage
    reads no day, so `on` goes unread."""
    return positions.desk_gate(positions.splitting)(root, subject)


def main() -> int:
    return positions.answer_gate(sys.argv[1:], PROG, WHAT, positions.as_of(judge, date.today()))


if __name__ == "__main__":
    sys.exit(main())
