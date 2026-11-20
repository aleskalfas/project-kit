#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml==0.19.1",
# ]
# ///
"""lean-business:cycle-lifecycle — the gate on `running` -> `suspended`, on `suspend`: is a
suspension the person recorded ongoing? (lean-business DEC-003 point 4).

Suspending is the person's act, and the move it brings is the script's. The command that
records the suspension refuses one that breaks DEC-002 point 12's rules, writes it, and then
asks the engine to move, naming the origin it read before the write (the process area's
README, "Seam-ordering contract"). The gate reads the facts the detection reads, and the
rules through the predicate the check shares (`_lib.positions.suspending_cycle`): a
suspension is ongoing, no decision is recorded, and no break of the rules names the ongoing
suspension. So the gate is closed before the command writes, and `can-move` refuses then:
the command judges the suspension by the rules' predicate instead.

The gate on `in-review` -> `suspended` is the same predicate.

Today is the local date where it runs, read here and nowhere else (DEC-003 point 1). The
test suite gives a fixed day by calling `judge` in its own process.

READ-ONLY. The engine runs it from the repository's root as

  cycle_lifecycle_gate_running_suspended_suspend.py <idea>--<cycle> --json

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

PROG = "cycle-lifecycle-gate-running-suspended-suspend"
WHAT = "Is a suspension the person recorded ongoing, so that the running cycle is suspended?"


def judge(root: Path, subject: str, on: date) -> positions.Answer:
    """The gate on the cycle `subject` on the day `on`, read from the project at `root`."""
    return positions.cycle_gate(positions.suspending_cycle)(root, subject, on)


def main() -> int:
    return positions.answer_gate(sys.argv[1:], PROG, WHAT, positions.as_of(judge, date.today()))


if __name__ == "__main__":
    sys.exit(main())
