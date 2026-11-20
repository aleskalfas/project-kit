#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml==0.19.1",
# ]
# ///
"""lean-business capability — resume: record the day a suspended cycle resumed, which counts
again (lean-business DEC-002 point 12; DEC-003 points 4 and 5).

Resuming is the person's move, on `resume`, out of suspended, so it takes their word and
records who recorded it and the day. The day the cycle resumed is today, unless the person
names an earlier one with `--on`. The window, and each time box the suspension reached
before it started, then fall later by the days it covered, so the cycle, and each
experiment not yet started, has the days it had left when it stopped.

The move has two targets, and the command chooses neither before its write. It checks the
day against the predicate the check shares (`suspensions.of_cycle`) and asks the process
engine whether either move of `resume` may be taken. After the write it moves the cycle to
where the engine places it: to running, or into review where the window, so moved, ended
before today, since time that ran out while the person was working is never given back.
Where the engine refuses the move after the write, the write is undone.

Refused: a cycle that is not suspended, and a day of resuming that breaks the suspension's
rules, such as one before its first day or later than today.

Usage:
  pkit lean resume <cycle> [--on <day>] [--person-decided]

Exit codes:
  0  resumed
  1  refused, or answered no: nothing was written
  2  usage
  3  nobody could be asked: the question is printed, and nothing was written
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Mapping
from datetime import date
from pathlib import Path

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))

from _lib import acting, cycles, editing, engine, positions, writes
from _lib.acting import Context
from _lib.experiments import a_day
from _lib.writes import Refused

TRIGGER = "resume"


def parser() -> argparse.ArgumentParser:
    made = argparse.ArgumentParser(
        prog="pkit lean resume",
        description="Record the day a suspended cycle resumed, which counts again.",
    )
    made.add_argument("cycle", help="The cycle's id, `<idea>--<cycle>`.")
    made.add_argument(
        "--on",
        help="The day you came back, YYYY-MM-DD, which counts again; today where none is given.",
    )
    acting.person_decided(made)
    return made


def run(args: argparse.Namespace, ctx: Context) -> None:
    files = writes.Files(ctx.root, writes.for_writing(ctx.root))
    cycle = cycles.open_cycle(files, str(args.cycle))
    subject = cycle.id
    before = acting.position(ctx, engine.CYCLE, subject)
    if before.state != positions.SUSPENDED:
        raise Refused(
            f"`{subject}` stands {before.state}, not suspended: only a suspended cycle resumes"
        )
    on = a_day(str(args.on), "--on") if args.on is not None else ctx.on
    listed = cycle.data.get("suspensions")
    ongoing = [
        index
        for index, entry in enumerate(listed if isinstance(listed, list) else [])
        if isinstance(entry, Mapping) and not isinstance(entry.get("resumed"), Mapping)
    ]
    if len(ongoing) != 1:
        raise Refused(
            f"`{subject}` has {len(ongoing)} suspensions ongoing, and resuming from one leaves "
            f"it suspended: `pkit lean check` names the break"
        )
    index = ongoing[0]
    was = cycle.plain()
    resumption = editing.mapping([("day", on), ("by", ctx.who), ("when", ctx.on)])
    editing.place(listed[index], "resumed", resumption, cycles.SUSPENSION_ORDER)
    broken = cycles.suspension_breaks(files, cycle, index)
    if broken:
        raise Refused(f"resuming on {on} breaks the suspension's rules: {'; '.join(broken)}")
    resumed = cycle.plain()["suspensions"][index]

    def build() -> tuple[writes.Files, str]:
        # Said once the engine opened a move of `resume`, before the question.
        ctx.say(f"Resuming `{subject}` on {on}: the suspension {cycles.away(resumed)}.")
        for line in cycles.moved(files, cycle, was):
            ctx.say(line)
        files.put(cycle.rel, cycle.doc)
        return files, f"Resumed `{subject}` on {on}."

    acting.person_move(
        ctx, engine.CYCLE, subject, TRIGGER, before, build, decided=args.person_decided
    )


def main() -> int:
    return acting.main(parser(), run, date.today())


if __name__ == "__main__":
    sys.exit(main())
