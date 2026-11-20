#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml==0.19.1",
# ]
# ///
"""lean-business:cycle-lifecycle — the gate on `in-review` -> `suspended`, on `suspend`: is a
suspension the person recorded late ongoing? (lean-business DEC-003 point 4).

A suspension may be recorded once the window has run out, where its first day lies within
the window as worked out, so the person whose absence outlasted the window has again the
days the cycle had left. The command that records it refuses one that breaks DEC-002 point
12's rules, such as one that contradicts an act already recorded, writes it, and then asks
the engine to move, naming the origin it read before the write (the process area's README,
"Seam-ordering contract"). The gate reads the facts the detection reads, and the rules
through the predicate the check shares (`_lib.positions.suspending_cycle`): a suspension is
ongoing, no decision is recorded, and no break of the rules names the ongoing suspension.

The gate is closed before the command writes, and `can-move` refuses then: open there, it
would be a way forward without the person, and a cycle in review would no longer wait on
them (the process area's shape page, "How each wait clears"). The command judges the
suspension by the rules' predicate instead.

Today is the local date where it runs, read here and nowhere else (DEC-003 point 1). The
test suite gives a fixed day by calling `judge` in its own process.

READ-ONLY. The engine runs it from the repository's root as

  cycle_lifecycle_gate_in_review_suspended_suspend.py <idea>--<cycle> --json

and reads one JSON object on standard output, `{"result": <bool>, "reason": "..."}`.

Exit codes:
  0  answered
  2  no answer: the subject is no cycle's id; its location, its idea's files, its file,
     its review's decision or its suspensions cannot be read; or, where nothing is
     refused, a file or a day the rules weigh cannot be read. Why goes to standard error,
     and the engine refuses the move as indeterminate.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).parent))

from _lib import positions

PROG = "cycle-lifecycle-gate-in-review-suspended-suspend"
WHAT = "Is a suspension recorded late ongoing, so that the cycle in review is suspended?"


def judge(root: Path, subject: str, on: date) -> positions.Answer:
    """The gate on the cycle `subject` on the day `on`, read from the project at `root`."""
    return positions.cycle_gate(positions.suspending_cycle)(root, subject, on)


def main() -> int:
    return positions.answer_gate(sys.argv[1:], PROG, WHAT, positions.as_of(judge, date.today()))


if __name__ == "__main__":
    sys.exit(main())
