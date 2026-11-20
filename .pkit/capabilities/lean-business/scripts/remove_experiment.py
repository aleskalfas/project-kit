#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml==0.19.1",
# ]
# ///
"""lean-business capability — remove-experiment: remove a draft of an experiment never
declared (lean-business DEC-003 point 3; DEC-002 point 9).

Content, so it asks nothing and records no who or when. Refused once the experiment is
declared, since a declared experiment stays, whatever it comes to.

Usage:
  pkit lean remove-experiment <experiment>

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

from _lib import acting, experiments, writes
from _lib.acting import Context


def parser() -> argparse.ArgumentParser:
    made = argparse.ArgumentParser(
        prog="pkit lean remove-experiment",
        description="Remove a draft of an experiment never declared.",
    )
    made.add_argument("experiment", help="The experiment's id, `<idea>--<experiment>`.")
    return made


def run(args: argparse.Namespace, ctx: Context) -> None:
    files = writes.Files(ctx.root, writes.for_writing(ctx.root))
    experiment = experiments.open_experiment(files, str(args.experiment))
    experiments.unfrozen(experiment, "it stays")
    files.remove(experiment.rel)
    acting.content(ctx, files, f"Removed the draft `{experiment.id}`: `{experiment.rel}`.")


def main() -> int:
    return acting.main(parser(), run, date.today())


if __name__ == "__main__":
    sys.exit(main())
