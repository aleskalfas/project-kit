#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml==0.19.1",
# ]
# ///
"""lean-business capability — set-inputs: give a variant's viability estimate its inputs
(lean-business DEC-002 point 4).

Content, so it asks nothing and records no who or when. A direct model has one set of
inputs; a model with several sides has one for each, named by `--side`. The flags given are
merged into the set, which is created where none is, and `--clear` takes an input out.

- `--price <amount> <month|year>`: what the business keeps from one active customer, on
  average, each month or year, in the idea's currency: a one-off sale spread over the
  customer's lifetime, a marketplace's side by what the business keeps of it, a side that
  pays nothing at 0.
- `--lifetime <length> <month|year>`: how long a customer stays.
- `--conversion <share>`: the share of leads who become customers, above 0 and at most 1.
- `--referral-share <share>`: the share of new customers who come by referral, at least 0
  and below 1.

A change to what a standing verdict judged is warned of, never refused, naming each
judgement it leaves stale.

Usage:
  pkit lean set-inputs <variant> [--side <side>] [--price <amount> <month|year>]
                       [--lifetime <length> <month|year>] [--conversion <share>]
                       [--referral-share <share>] [--clear <input>]...

Exit codes:
  0  written
  1  refused: nothing was written
  2  usage
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path
from typing import Any

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))

from _lib import acting, canvases, editing, writes
from _lib.acting import Context
from _lib.writes import Refused

#: An input set's keys, in order.
ORDER = ("side", "price", "lifetime", "conversion", "referral-share")

#: The inputs `--clear` takes out.
INPUTS = ORDER[1:]

PERIODS = ("month", "year")


def parser() -> argparse.ArgumentParser:
    made = argparse.ArgumentParser(
        prog="pkit lean set-inputs",
        description="Give a variant's viability estimate its inputs, merged into the set for "
        "its side.",
    )
    made.add_argument("variant", help="The variant's id, `<idea>--<variant>`.")
    made.add_argument("--side", help="The side the inputs are for, in a model with several.")
    made.add_argument("--price", nargs=2, metavar=("AMOUNT", "PER"), help="month or year.")
    made.add_argument("--lifetime", nargs=2, metavar=("LENGTH", "UNIT"), help="month or year.")
    made.add_argument("--conversion", type=float, help="Above 0 and at most 1.")
    made.add_argument("--referral-share", type=float, help="At least 0 and below 1.")
    made.add_argument("--clear", action="append", choices=INPUTS, default=[])
    return made


def _number(text: str, flag: str) -> int | float:
    try:
        value = float(text)
    except ValueError:
        raise Refused(f"{flag} takes a number, and `{text}` is none") from None
    return int(value) if value == int(value) else value


def _period(text: str, flag: str) -> str:
    if text not in PERIODS:
        raise Refused(f"{flag} counts in a month or a year, and `{text}` is neither")
    return text


def run(args: argparse.Namespace, ctx: Context) -> None:
    given: dict[str, Any] = {}
    if args.price is not None:
        amount = _number(args.price[0], "--price")
        if amount < 0:
            raise Refused("--price is never below 0: a side that pays nothing counts at 0")
        given["price"] = editing.mapping(
            [("amount", amount), ("per", _period(args.price[1], "--price"))]
        )
    if args.lifetime is not None:
        length = _number(args.lifetime[0], "--lifetime")
        if length <= 0:
            raise Refused("--lifetime is longer than nothing")
        given["lifetime"] = editing.mapping(
            [("length", length), ("unit", _period(args.lifetime[1], "--lifetime"))]
        )
    if args.conversion is not None:
        if not 0 < args.conversion <= 1:
            raise Refused("--conversion is a share above 0 and at most 1, such as 0.05")
        given["conversion"] = args.conversion
    if args.referral_share is not None:
        if not 0 <= args.referral_share < 1:
            raise Refused("--referral-share is a share at least 0 and below 1, such as 0.2")
        given["referral-share"] = args.referral_share
    both = sorted(set(args.clear) & set(given))
    if both:
        raise Refused(f"{', '.join(both)} is given and cleared at once: give one or the other")
    if not given and not args.clear:
        raise Refused("give an input to set, or one to --clear")
    files = writes.Files(ctx.root, writes.for_writing(ctx.root))
    canvas = canvases.open_variant(files, str(args.variant))
    canvases.check_side(canvas, args.side)
    held = canvas.data.get("viability")
    if not isinstance(held, list):
        held = editing.seq()
        editing.place(canvas.data, "viability", held, canvases.ORDER)
    inputs = next(
        (s for s in held if isinstance(s, dict) and s.get("side") == args.side),
        None,
    )
    if inputs is None:
        if args.clear and not given:
            raise Refused(f"`{canvas.id}` holds no inputs{_for(args.side)} to clear")
        inputs = editing.mapping([("side", args.side)])
        held.append(inputs)
    for key, value in given.items():
        editing.place(inputs, key, value, ORDER)
    for key in args.clear:
        inputs.pop(key, None)
    if not any(key != "side" for key in inputs):
        held.remove(inputs)
    if not held:
        canvas.data.pop("viability", None)
    files.put(canvas.rel, canvas.doc)
    acting.content(ctx, files, f"Set the inputs of `{canvas.id}`{_for(args.side)}.")


def _for(side: str | None) -> str:
    return f" for the side `{side}`" if side is not None else ""


def main() -> int:
    return acting.main(parser(), run, date.today())


if __name__ == "__main__":
    sys.exit(main())
