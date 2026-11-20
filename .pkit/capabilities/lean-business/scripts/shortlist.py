#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml==0.19.1",
# ]
# ///
"""lean-business capability — shortlist: choose a variant to test in a cycle (lean-business
DEC-003 points 2 and 5; DEC-002 points 5 and 13).

The shortlisting is the person's, so it takes their word and records who chose it and
when, with the fingerprint of the canvas and the goal it was chosen on. It moves the
variant from feasible to shortlisted. On a shortlisted variant it takes the shortlisting
again, on the canvas and the goal as they stand, as after a change left the old one stale.

Its gate, which the check shares: a yes on all three steps, none stale.

Usage:
  pkit lean shortlist <variant> [--person-decided]

Exit codes:
  0  written
  1  refused, or answered no: nothing was written
  2  usage
  3  nobody could be asked: the question is printed, and nothing was written
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))

from _lib import acting, canvases, editing, engine, fingerprint, gates, writes
from _lib.acting import Context
from _lib.writes import Refused

#: The trigger of the desk stage's move into shortlisted.
TRIGGER = "shortlist"


def parser() -> argparse.ArgumentParser:
    made = argparse.ArgumentParser(
        prog="pkit lean shortlist",
        description="Choose a variant to test in a cycle, on its canvas and the goal as they "
        "stand.",
    )
    made.add_argument("variant", help="The variant's id, `<idea>--<variant>`.")
    acting.person_decided(made)
    return made


def run(args: argparse.Namespace, ctx: Context) -> None:
    variant = canvases.variant_id(str(args.variant))
    before = acting.position(ctx, engine.DESK, variant)

    def build() -> tuple[writes.Files, str]:
        files = writes.Files(ctx.root, writes.for_writing(ctx.root))
        canvas = canvases.open_variant(files, variant)
        goal = canvases.goal_of(files, canvas.idea)
        plain = canvas.plain()
        refusals = [*gates.shortlisting(plain), *gates.stale_verdicts(plain, goal)]
        if refusals:
            raise Refused("; ".join(refusal.message for refusal in refusals))
        taken = canvases.fingerprint_data(lambda: fingerprint.of_shortlisting(plain, goal))
        outcome = editing.mapping(
            [
                ("kind", "shortlisted"),
                ("fingerprint", taken),
                ("by", ctx.who),
                ("when", ctx.on),
            ]
        )
        editing.place(canvas.data, "outcome", outcome, canvases.ORDER)
        files.put(canvas.rel, canvas.doc)
        return files, f"Shortlisted `{variant}`, on its canvas and the goal as they stand."

    acting.person_move(
        ctx, engine.DESK, variant, TRIGGER, before, build, decided=args.person_decided
    )


def main() -> int:
    return acting.main(parser(), run, date.today())


if __name__ == "__main__":
    sys.exit(main())
