#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml==0.19.1",
# ]
# ///
"""lean-business capability — rank: rank a variant's assumptions by risk, the riskiest first
(lean-business DEC-002 point 8; DEC-003 point 5).

The rank is the person's act, so it takes their word (DEC-003 point 5). It records no who
or when, since nothing rests on a rank (DEC-002 point 8). The assumptions named take the
first ranks, in the order given; the others follow them in the order their ranks held. An
assumption is named by its id or its own part. Each keeps its place in the file.

Usage:
  pkit lean rank <variant> <assumption>... [--person-decided]

Exit codes:
  0  written, or ranked so already
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

from _lib import acting, assumptions, canvases, writes
from _lib.acting import Context
from _lib.writes import Refused


def parser() -> argparse.ArgumentParser:
    made = argparse.ArgumentParser(
        prog="pkit lean rank",
        description="Rank a variant's assumptions by risk, the riskiest first.",
    )
    made.add_argument("variant", help="The variant's id, `<idea>--<variant>`.")
    made.add_argument(
        "assumptions",
        nargs="+",
        metavar="assumption",
        help="The assumptions, the riskiest first, each by its id or its own part; those left "
        "out follow them as they were ranked.",
    )
    acting.person_decided(made)
    return made


def run(args: argparse.Namespace, ctx: Context) -> None:
    variant = canvases.variant_id(str(args.variant))
    named = [assumptions.own_or_whole(variant, str(given)) for given in args.assumptions]
    twice = sorted({a for a in named if named.count(a) > 1})
    if twice:
        raise Refused(f"{', '.join(f'`{a}`' for a in twice)} is named twice")
    files = writes.Files(ctx.root, writes.for_writing(ctx.root))
    listed = assumptions.open_list(files, variant)
    for assumption in named:
        listed.find(assumption)
    order = [*named, *(a for a in _by_rank(listed) if a not in named)]
    if [_rank(listed, a) for a in order] == list(range(1, len(order) + 1)):
        ctx.say(f"The assumptions of `{variant}` are ranked so already: {_words(order)}.")
        return
    for rank, assumption in enumerate(order, start=1):
        listed.find(assumption)[1]["rank"] = rank
    files.put(listed.rel, listed.doc)
    acting.act(
        ctx,
        files,
        f"Ranked the assumptions of `{variant}`: {_words(order)}.",
        question=(
            f"Rank the assumptions of `{variant}` by risk, the riskiest first: {_words(order)}? "
            f"The riskiest is tested first."
        ),
        decided=args.person_decided,
    )


def _by_rank(listed: assumptions.Assumptions) -> list[str]:
    """The list's assumptions by the rank each holds, those of one rank, or of none, in the
    order of the file."""
    held = [
        item
        for item in listed.items()
        if isinstance(item, Mapping) and isinstance(item.get("id"), str)
    ]
    ordered = sorted(enumerate(held), key=lambda pair: (_held_rank(pair[1]), pair[0]))
    return [str(item["id"]) for _, item in ordered]


def _held_rank(item: Mapping[str, object]) -> float:
    rank = item.get("rank")
    if isinstance(rank, bool) or not isinstance(rank, int):
        return float("inf")
    return float(rank)


def _rank(listed: assumptions.Assumptions, assumption: str) -> object:
    return listed.find(assumption)[1].get("rank")


def _words(order: list[str]) -> str:
    return ", ".join(f"{rank}. `{assumption}`" for rank, assumption in enumerate(order, start=1))


def main() -> int:
    return acting.main(parser(), run, date.today())


if __name__ == "__main__":
    sys.exit(main())
