#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "jsonschema>=4.18",
#   "ruamel.yaml>=0.18",
# ]
# ///
"""software-analysis capability — fill-readers: its contribution to the readers point.

This capability's filler of the `pkit::documentation:readers` data point
(DEC-001 point 8): one reader per actor in force, its id the actor's id in
lower case (`ACT-tester` → `act-tester`) and its description the actor's name
and needs. `_lib/readers.py` states the mapping.

The backbone runs it wherever the point resolves — `pkit validate`, `pkit
status`, `pkit connections resolve` — as a query (COR-052 point 6): from the
project root, with `--json` alone and the offline marker set. It takes no
parameter: it reads the analysis in the working tree through the backbone's
discovery, `pkit friction artefacts --json`, writes nothing and needs no
network. The contribution is inert while no capability provides the
documentation role; nothing here asks.

Usage:
  pkit analysis fill-readers           one line per reader, for a person
  pkit analysis fill-readers --json    the filler envelope {schema_version, value}

Exit codes:
  0  answered
  1  no answer: the analysis could not be read, or the actors' file cannot be
     read as a collection of actors — never an empty answer in its place,
     whatever the point's policy (COR-052 point 6). An entry that is no actor
     is skipped, not a reason to give no answer.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
from _lib import backbone, readers
from _lib.model import Unreadable


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="pkit analysis fill-readers",
        description=(
            f"Print the analysis' actors as readers of the {readers.POINT} data point "
            f"(software-analysis DEC-001 point 8). Read-only and offline."
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the filler envelope {schema_version, value}, as the backbone reads it.",
    )
    args = parser.parse_args()

    try:
        value = readers.readers(backbone.read_analysis(backbone.project_root()))
    except (Unreadable, readers.NoAnswer) as exc:
        print(f"error: {exc}; no readers can be given.", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(readers.envelope(value), indent=2, ensure_ascii=False))
        return 0
    print(f"{readers.POINT}: {len(value)} reader(s) from the analysis' actors")
    for reader in value:
        print(f"  {reader['id']} — {reader['description']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
