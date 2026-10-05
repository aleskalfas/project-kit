#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "jsonschema>=4.18",
#   "ruamel.yaml>=0.18",
# ]
# ///
"""software-analysis capability — fill-use-cases: its contribution to the use-case point.

This capability's filler of the `pkit::work-tracking:use-cases` data point
(DEC-001 point 8): the use cases settled on the default branch, one entry per
use case — its id as the analysis writes it, its title, `active` or
`withdrawn`, and the path of its document. `_lib/settled_use_cases.py` states
the mapping.

The backbone runs it wherever the point resolves — `pkit validate`, `pkit
status`, `pkit connections resolve` — as a query (COR-052 point 6): from the
project root, with `--json` alone and the offline marker set. It takes no
parameter and declares `reads: [settled]`: it reads the default branch at the
commit the backbone resolves it to (`pkit repository base --json`, its
`default_branch`, never its `base`) and what that commit holds (`pkit friction
artefacts --at <commit> --json`). It never reads the working tree, asks git
nothing itself, writes nothing and needs no network. The contribution is inert
while no capability provides the work-tracking role; nothing here asks.

Usage:
  pkit analysis fill-use-cases           one line per use case, for a person
  pkit analysis fill-use-cases --json    the filler envelope {schema_version, value}

Exit codes:
  0  answered — the empty list where the default branch has no commit yet, or
     its commit holds no use case
  1  no answer, and nothing on standard output: a reading of the backbone's
     failed, or a use case at that commit cannot be read in full — never a
     shorter list in its place, whatever the point's policy (COR-052 point 6)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
from _lib import settled_use_cases


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="pkit analysis fill-use-cases",
        description=(
            f"Print the use cases settled on the default branch as the value of the "
            f"{settled_use_cases.POINT} data point (software-analysis DEC-001 point 8). "
            f"Read-only and offline."
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the filler envelope {schema_version, value}, as the backbone reads it.",
    )
    args = parser.parse_args()

    # The backbone starts a filler from the project root, and so does the dispatcher.
    try:
        value = settled_use_cases.read(Path.cwd())
    except settled_use_cases.NoAnswer as exc:
        print(f"error: {exc}; no use cases can be given.", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(settled_use_cases.envelope(value), indent=2, ensure_ascii=False))
        return 0
    print(f"{settled_use_cases.POINT}: {len(value)} use case(s) settled on the default branch")
    for use_case in value:
        print(
            f"  {use_case['id']} — {use_case['title']} ({use_case['status']}; {use_case['path']})"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
