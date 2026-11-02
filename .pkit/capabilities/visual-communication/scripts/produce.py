#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml==0.19.1",
# ]
# ///
"""visual-communication capability — produce: run the producer a piece declares for one of
its produced outputs, and keep its picture (DEC-006 points 1 to 5).

The piece's `piece.yaml` declares the output under `produced.<output>`: the producer, the
role each of its inputs reads, and the pixel size of each variant. The command resolves
those roles in every combination the piece names, under the piece's lock, makes one
variant for each distinct set of values, hands them to the producer, and runs it. It keeps
the picture only when no input changed during the run and every variant is a PNG of the
declared size, exposing the same points at the same places: then it writes
`produced/<output>/<key>.png` for each variant and `produced/<output>/record.yaml`, and
removes a variant file left from before. The hand-over and the producer's own output lie
under the capability's local folder, never committed.

A piece with no lock yet is refused: run `pkit visual render <piece>` first. The command
writes in the location, so where none is recorded it records the location at its first
write (DEC-002 point 1); `--location <path>` names it.

Usage:
  pkit visual produce <piece> <output> [--location <path>]

Exit codes:
  0  produced: the variants and their record written
  1  refused: nothing written in the location
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))

from _lib import framing
from _lib import location as loc
from _lib.root import project_root


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="pkit visual produce",
        description="Run the producer a piece declares for one of its produced outputs.",
    )
    parser.add_argument("piece", help="the piece, by the name of its folder")
    parser.add_argument("output", help="the produced output, as `piece.yaml` names it")
    parser.add_argument(
        "--location",
        help="the location to record, where the configuration records none yet",
    )
    args = parser.parse_args()
    root = project_root()
    try:
        where = loc.for_writing(root, args.location)
        done = framing.produce(root, where, args.piece, args.output)
    except (framing.Refused, loc.LocationRefused, loc.GitFailed) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if done.location is not None:
        print(done.location)
    plan = done.plan
    variants, combinations = len(plan.variants), len(plan.combinations)
    print(
        f"produced `{plan.output}` of `{plan.piece}` with {plan.plugin['name']} "
        f"{plan.plugin['version']}: {variants} variant{'s' if variants != 1 else ''} for "
        f"{combinations} combination{'s' if combinations != 1 else ''}"
    )
    for key, served in plan.variants.items():
        print(f"  {key}.png serves {', '.join(served)}")
    for name in done.removed:
        print(f"  removed {name}, which no variant names now")
    print(f"wrote {done.record.relative_to(root).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
