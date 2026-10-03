#!/usr/bin/env -S uv run --script
"""living-docs capability — resolve-source: the `source` anchor kind's resolver (DEC-001 point 4).

A page anchors a source outside the repository by its name (`source:
[keep-a-changelog]`), and the source is captured in one file of this
capability's project tier, found from the name alone:
`.pkit/capabilities/living-docs/project/sources/<name>.yaml`. The resolver
answers that file — any change to it is the source's change — or no file,
when the name is outside the grammar or nothing captures it: the anchor is
then dead. `_lib/source_layout.py` is where the layout and the grammar live.

The backbone runs it for each anchor value as a query (the lifecycle README,
"How a registered anchor kind is resolved"): from the project root, with
`--json`, `--` and then the value, the offline marker set. It is bounded,
deterministic, read-only and offline; it imports nothing beyond the standard
library, so there is nothing to provision.

Usage:
  pkit living-docs resolve-source <name>             the file the name resolves to
  pkit living-docs resolve-source --json -- <name>   {"paths": [...]}, as the backbone reads it

Exit codes:
  0  answered — a file, or none
  1  where sources are kept could not be read (a permission or I/O error): no answer
  2  usage error
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
from _lib import source_layout
from _lib.root import project_root


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Resolve the `source` anchor kind (living-docs DEC-001 point 4): the file "
            "capturing a source, found from its name. Read-only and offline."
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help='Print {"paths": [...]}, as the friction checks read it.',
    )
    parser.add_argument("value", help="The source's name, as an anchor writes it.")
    args = parser.parse_args()

    try:
        paths = source_layout.answer(project_root(), args.value)
    except source_layout.Unreadable as exc:
        print(f"error: where sources are kept cannot be read — {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps({"paths": paths}))
    elif paths:
        print(paths[0])
    else:
        print(f"no source named {args.value!r} is captured ({source_layout.file_path(args.value)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
