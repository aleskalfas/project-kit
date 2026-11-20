#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml==0.19.1",
# ]
# ///
"""lean-business capability — remove-assumption: take an assumption out of its variant's list
(lean-business DEC-002 points 7 and 8).

Content, so it asks nothing and records no who or when. Refused while an experiment tests
it, declared or a draft: a declared experiment names what it tested for good, and a draft
is removed, or drafted on another assumption, first. The others keep their ranks. The
assumption is named as every command names one, read within the location (`naming.named`).

Usage:
  pkit lean remove-assumption <assumption>

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

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))

from _lib import acting, assumptions, experiments, ids, model, naming, writes
from _lib.acting import Context
from _lib.writes import Refused


def parser() -> argparse.ArgumentParser:
    made = argparse.ArgumentParser(
        prog="pkit lean remove-assumption",
        description="Take an assumption out of its variant's list.",
    )
    made.add_argument(
        "assumption",
        help="The assumption, by its id, `<idea>--<variant>--<assumption>`, the part after the "
        "idea, or its own part.",
    )
    return made


def run(args: argparse.Namespace, ctx: Context) -> None:
    files = writes.Files(ctx.root, writes.for_writing(ctx.root))
    assumption_id = naming.named(files, naming.ASSUMPTION, str(args.assumption))
    variant = ids.qualifier(assumption_id)
    listed = assumptions.open_list(files, variant)
    index, _ = listed.find(assumption_id)
    held = experiments.read_idea(files, ids.idea_of(variant))
    testing = held.experiments_on(assumption_id) if held is not None else []
    if testing and held is not None:
        named = "; ".join(
            f"`{held.qualified(e.own)}`, {'declared' if model.declared(e.data) else 'a draft'}"
            for e in testing
        )
        raise Refused(
            f"{named} {'tests' if len(testing) == 1 else 'test'} `{assumption_id}`: a declared "
            f"experiment names what it tested for good, and a draft is removed first, `pkit "
            f"lean remove-experiment`, or drafted on another assumption"
        )
    del listed.items()[index]
    files.put(listed.rel, listed.doc)
    acting.content(ctx, files, f"Removed `{assumption_id}` from the assumptions of `{variant}`.")


def main() -> int:
    return acting.main(parser(), run, date.today())


if __name__ == "__main__":
    sys.exit(main())
