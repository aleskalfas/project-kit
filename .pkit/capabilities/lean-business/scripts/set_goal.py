#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml==0.19.1",
# ]
# ///
"""lean-business capability — set-goal: set the idea's goal, the revenue it is to reach and
the years it is to reach it in (lean-business DEC-002 point 3).

The goal is the person's act, so it takes their word and records who set it and when
(DEC-003 point 5). The first goal of an idea needs every flag; a change gives the flags it
changes. It creates the idea's folder where none is.

Refused, through the predicate the check shares (`gates.setting_goal`): any change while a
cycle of the idea is planned, running or suspended; and a change of currency while an
experiment declared in the old one is undecided.

Usage:
  pkit lean set-goal <idea> --revenue <amount> --per month|year --currency <code> --years <n>
                     [--person-decided]

Exit codes:
  0  written
  1  refused, or answered no: nothing was written
  2  usage
  3  nobody could be asked: the question is printed, and nothing was written
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))

from _lib import acting, editing, gates, ids, layout, listing, writes
from _lib.acting import Context
from _lib.writes import Refused

#: A goal's keys, in the order the schema's reference instance writes them.
ORDER = ("pkit_schema", "schema_version", "revenue", "currency", "years", "by", "when")

CURRENCY = re.compile(r"^[A-Z]{3}$")


def parser() -> argparse.ArgumentParser:
    made = argparse.ArgumentParser(
        prog="pkit lean set-goal",
        description="Set the idea's goal: the recurring revenue it is to reach, in its "
        "currency, and the years it is to reach it in.",
    )
    made.add_argument("idea", help="The idea's id, such as `meal-plan`.")
    made.add_argument("--revenue", type=float, help="The revenue to reach, each month or year.")
    made.add_argument("--per", choices=("month", "year"), help="The period the revenue counts.")
    made.add_argument("--currency", help="The idea's currency, a three-letter code such as EUR.")
    made.add_argument("--years", type=float, help="The years to reach it in.")
    acting.person_decided(made)
    return made


def run(args: argparse.Namespace, ctx: Context) -> None:
    idea = str(args.idea)
    if not ids.is_segment(idea):
        raise Refused(
            f"`{idea}` is no idea's id: words of lower-case letters and digits, the first "
            f"beginning with a letter, joined by single hyphens"
        )
    if args.currency is not None and not CURRENCY.match(args.currency):
        raise Refused(f"`{args.currency}` is no currency's code: three capital letters, as EUR")
    amount = editing.number(args.revenue) if args.revenue is not None else None
    years = editing.number(args.years) if args.years is not None else None
    if amount is not None and amount < 0:
        raise Refused("the revenue to reach is never below nothing")
    if years is not None and years <= 0:
        raise Refused("the years to reach the goal are more than none")
    files = writes.Files(ctx.root, writes.for_writing(ctx.root))
    rel = files.path("goal", idea)
    doc = files.read(rel)
    previous = doc.plain() if doc is not None else None
    if doc is None:
        missing = [
            f"--{name}"
            for name in ("revenue", "per", "currency", "years")
            if getattr(args, name) is None
        ]
        if missing:
            raise Refused(f"the idea has no goal yet, and its first needs {', '.join(missing)}")
        doc = editing.new(layout.SCHEMA["goal"], {})
    elif all(getattr(args, n) is None for n in ("revenue", "per", "currency", "years")):
        raise Refused("give what the goal changes: --revenue, --per, --currency or --years")
    data = doc.data
    revenue = data.get("revenue")
    if not isinstance(revenue, dict):
        revenue = editing.mapping()
        editing.place(data, "revenue", revenue, ORDER)
    if amount is not None:
        editing.place(revenue, "amount", amount, ("amount", "per"))
    if args.per is not None:
        editing.place(revenue, "per", args.per, ("amount", "per"))
    if args.currency is not None:
        editing.place(data, "currency", args.currency, ORDER)
    if years is not None:
        editing.place(data, "years", years, ORDER)
    editing.place(data, "by", ctx.who, ORDER)
    editing.place(data, "when", ctx.on, ORDER)
    goal = doc.plain()
    refusals = gates.setting_goal(
        goal,
        ctx.on,
        cycles=_read(ctx, files, idea, layout.CYCLES),
        previous=previous if isinstance(previous, dict) else None,
        experiments=_read(ctx, files, idea, layout.EXPERIMENTS),
    )
    if refusals:
        raise Refused("; ".join(refusal.message for refusal in refusals))
    files.put(rel, doc)
    acting.act(
        ctx,
        files,
        f"The goal of `{idea}` is set: {_words(goal)}.",
        question=_question(goal),
        decided=args.person_decided,
    )


def _read(ctx: Context, files: writes.Files, idea: str, folder: str) -> list[dict[str, Any]]:
    """Each file of the idea's `folder` that reads as a mapping."""
    try:
        contents = layout.read(ctx.root, files.location, idea)
    except (listing.ListingFailed, layout.IdRefused) as exc:
        raise Refused(f"the idea's files cannot be read: {exc}") from exc
    held = contents.ideas.get(idea)
    if held is None:
        return []
    found = held.cycles if folder == layout.CYCLES else held.experiments
    return [dict(file.data) for file in found.values() if file.data is not None]


def _words(goal: Any) -> str:
    revenue = goal.get("revenue") or {}
    return (
        f"{revenue.get('amount')} {goal.get('currency')} a {revenue.get('per')}, within "
        f"{goal.get('years')} years"
    )


def _question(goal: Any) -> str:
    return (
        f"Set the idea's goal to {_words(goal)}? Viability and feasibility are judged against it."
    )


def main() -> int:
    return acting.main(parser(), run, date.today())


if __name__ == "__main__":
    sys.exit(main())
