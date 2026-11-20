#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml==0.19.1",
# ]
# ///
"""lean-business capability — suspend: record that the person's life stopped a cycle, from a
day they give, with the reason (lean-business DEC-002 point 12; DEC-003 points 4 and 5).

A suspension is the person's act, so it takes their word and records who recorded it and
the day. Its first day, and the day the cycle resumed where the absence is already over,
are the person's word, today or earlier, so an absence may be recorded late, on coming
back. The suspension lies beside the frozen plan, never in it: its days count toward no
window, and toward no time box of an experiment that had not started by its first day. An
experiment already running keeps its dates.

The command validates the suspension through the predicate the check shares
(`suspensions.of_cycle`) and writes it. Its effect is then the script's move, which the
command takes from where the cycle stood before the write, never asking first whether it
may: into suspended where the suspension is ongoing, and from review back to running where
an absence already over gives the window days that hold today. Where the cycle stands
where it stood, nothing moves. Where the process engine places the cycle in none of its
states after the write, the act stands, and the command says the move waits.

Refused: a cycle planned, whose window has not started, since an absence known now is
sized into the window; one suspended already, on which nothing is recorded but resuming;
one decided; and a suspension that breaks its rules, such as a first day outside the
window or later than today, a covered day that holds recorded work, or one that would make
an act already recorded read as one its gate refuses.

Usage:
  pkit lean suspend <cycle> --reason <text> --since <day> [--resumed <day>]
                    [--person-decided]

Exit codes:
  0  written
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
from typing import Any

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))

from _lib import acting, cycles, editing, engine, naming, positions, timeline, writes
from _lib.acting import Context
from _lib.experiments import a_day
from _lib.writes import Refused


def parser() -> argparse.ArgumentParser:
    made = argparse.ArgumentParser(
        prog="pkit lean suspend",
        description="Record that your life stopped a cycle, from the day you were first away.",
    )
    made.add_argument("cycle", help="The cycle, by its id, `<idea>--<cycle>`, or its own part.")
    made.add_argument("--reason", required=True, help="What stopped the work, in a sentence.")
    made.add_argument(
        "--since",
        required=True,
        help="The first day you were away, YYYY-MM-DD: today or earlier.",
    )
    made.add_argument(
        "--resumed",
        help="The day you came back, YYYY-MM-DD, which counts again, where the absence is "
        "over: today or earlier.",
    )
    acting.person_decided(made)
    return made


def run(args: argparse.Namespace, ctx: Context) -> None:
    reason = str(args.reason).strip()
    if not reason:
        raise Refused("a suspension says why: give --reason its words")
    since = a_day(str(args.since), "--since")
    resumed = a_day(str(args.resumed), "--resumed") if args.resumed is not None else None
    files = writes.Files(ctx.root, writes.for_writing(ctx.root))
    cycle = cycles.open_cycle(files, naming.named(files, naming.CYCLE, str(args.cycle)))
    subject = cycle.id
    before = acting.position(ctx, engine.CYCLE, subject)
    _open_to_it(subject, before.state, cycle.plain())
    was = cycle.plain()
    entry = editing.mapping(
        [
            ("reason", reason),
            ("first-day", since),
            ("by", ctx.who),
            ("when", ctx.on),
            (
                "resumed",
                editing.mapping([("day", resumed), ("by", ctx.who), ("when", ctx.on)])
                if resumed is not None
                else None,
            ),
        ]
    )
    listed = cycle.data.get("suspensions")
    if not isinstance(listed, list):
        listed = editing.seq()
        editing.place(cycle.data, "suspensions", listed, cycles.ORDER)
    listed.append(entry)
    broken = cycles.suspension_breaks(files, cycle, len(listed) - 1)
    if broken:
        raise Refused(f"the suspension breaks its rules: {'; '.join(broken)}")
    files.put(cycle.rel, cycle.doc)
    until = f" until {resumed}" if resumed is not None else ""
    effects = cycles.moved(files, cycle, was, since=since)
    acting.act_then_moved(
        ctx,
        engine.CYCLE,
        subject,
        before,
        files,
        "\n".join([f"Suspended `{subject}` from {since}{until}: {reason}", *effects]),
        question=" ".join(
            [
                f"Record that your life stopped `{subject}` from {since}{until}, for this "
                f"reason: {reason}? Its days count toward no window, and the review shows "
                f"the suspension and the day it was recorded.",
                *effects,
            ]
        ),
        decided=args.person_decided,
    )
    if resumed is None:
        ctx.say(f"Once you are back, `pkit lean resume {subject}` resumes it.")


def _open_to_it(subject: str, state: str | None, plain: Mapping[str, Any]) -> None:
    """Refuse a cycle where it stands somewhere a suspension cannot be recorded: planned,
    suspended already, or decided (DEC-003 point 4)."""
    if state == positions.PLANNED:
        window = timeline.cycle_window(plain)
        starts = f", on {window.start}" if window is not None and window.start else ""
        raise Refused(
            f"`{subject}` is planned, and its window has not started{starts}: an absence "
            f"known before it starts is sized into the window, `pkit lean change-plan "
            f"{subject} --days <n>`"
        )
    if state == positions.SUSPENDED:
        raise Refused(
            f"`{subject}` is suspended already: nothing is recorded on a suspended cycle but "
            f"resuming it, `pkit lean resume {subject}`"
        )
    if state == positions.DECIDED:
        raise Refused(f"`{subject}` is decided, and a decided cycle takes no act")


def main() -> int:
    return acting.main(parser(), run, date.today())


if __name__ == "__main__":
    sys.exit(main())
