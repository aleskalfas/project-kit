#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml==0.19.1",
# ]
# ///
"""lean-business:experiment-lifecycle — the gate on `drafted` -> `running`, on `declare`:
may the person's declaration freeze the experiment, its time box starting today?
(lean-business DEC-003 points 3 and 7; DEC-002 point 9).

Declaring is the person's move, and a time box that starts on the day it is declared is
running as soon as the declaration is recorded, so the definition gives the declaring move
this target too (DEC-003, "Why a declaration may move straight to running"). The gate is
the one predicate both moves of `declare` carry (`_lib.positions.declaring_experiment`),
asked by `can-move` before the command writes and by `move` after:

- on both sides, the experiment tests an assumption of a variant whose shortlisting stands,
  as the desk stage's detection places it, and is not stale; and the cycle it names is
  open, planned or running, as the cycle's detection places it, and explores that variant;
- before, the experiment is drafted, its time box starts today, and the declaring gate the
  check shares lets it through today (`gates.declaring`): every field its kind needs, at
  least one estimate, a time box of fourteen days at most, resting on the shortlisting the
  canvas keeps;
- after, the detection places the experiment in `running`, and the declaration records who
  declared it, the day, the shortlisting it rested on and its fingerprint, which matches
  what it declared, and passes the declaring gate as the check asks it, on the day it was
  recorded.

A time box that starts after today takes the move into declared instead.

Today is the local date where it runs, read here and nowhere else (DEC-003 point 1). The
test suite gives a fixed day by calling `judge` in its own process.

READ-ONLY. The engine runs it from the repository's root as

  experiment_lifecycle_gate_drafted_running_declare.py <idea>--<experiment> --json

and reads one JSON object on standard output, `{"result": <bool>, "reason": "..."}`.

Exit codes:
  0  answered
  2  no answer: the subject is no experiment's id; its location, its idea's files, its
     file, its declaration, the variant's canvas or its outcome, or the cycle's file, its
     suspensions or its window cannot be read; or, where nothing is refused, the variant's
     assumptions, the idea's goal or a fingerprint the gate compares cannot be read. Why
     goes to standard error, and the engine refuses the move as indeterminate.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).parent))

from _lib import positions

PROG = "experiment-lifecycle-gate-drafted-running-declare"
WHAT = "May the person's declaration move the experiment from drafted straight to running?"


def _declaring(subject: positions.Experiment, on: date) -> positions.Answer:
    return positions.declaring_experiment(subject, on, positions.RUNNING)


def judge(root: Path, subject: str, on: date) -> positions.Answer:
    """The gate on the experiment `subject` on the day `on`, read from the project at
    `root`."""
    return positions.experiment_gate(_declaring)(root, subject, on)


def main() -> int:
    return positions.answer_gate(sys.argv[1:], PROG, WHAT, positions.as_of(judge, date.today()))


if __name__ == "__main__":
    sys.exit(main())
