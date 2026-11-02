#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "jsonschema==4.26.0",
#   "ruamel.yaml==0.19.1",
# ]
# ///
"""visual-communication capability — write-code: write a brand out as code, as a
declaration in the location asks (DEC-005 point 7, DEC-006 points 4 and 5).

Reads the declaration `code/<name>.yaml` in the location: the code writer, the form of its
spelling, the brand, the lock of the brand and what it builds on, and where the code goes
(`out`). Resolves every token the brand exports in every combination of its axes, at the
versions the lock names, and writes the code to `out` and its record beside it,
`<out>.record.yaml`: the fingerprint of the declaration, the values written and the
writer's version, which `pkit visual check` verifies. Where the record verifies and the
code is what the writer writes now, it writes nothing.

It never moves the declaration's lock: a person moves it on purpose. It prints each token
the writer has no form for, as a loss, unless the declaration accepts it in
`accept-losses`.

Writes `out` and its record, which may lie anywhere in the project's tree but under
`.pkit/`, under a hidden folder, in the location's library folder or in its `code/` folder
of declarations; nor may `out` be reached through a link, or be a folder. Needs no network.

Usage:
  pkit visual write-code <name>

Exit codes:
  0  written, or up to date
  1  refused: no such declaration, a declaration that cannot be read, an `out` the rules
     refuse, a lock that does not hold, or a brand that cannot be resolved
  2  usage error
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))

from _lib import code
from _lib import location as loc
from _lib.root import project_root


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="pkit visual write-code",
        description="Write a brand out as code, as the declaration code/<name>.yaml asks.",
    )
    parser.add_argument("name", help="the declaration's name: code/<name>.yaml in the location")
    args = parser.parse_args()
    root = project_root()
    try:
        found = loc.for_reading(root)
        if found is None:
            raise code.CodeRefused(
                f"there is no visual work here, so no declaration `{args.name}`: the location "
                f"holds the declarations, `{loc.DEFAULT}/{code.FOLDER}/<name>.yaml` by default"
            )
        written = code.write(root, found.path, args.name)
    except (code.CodeRefused, loc.LocationRefused, loc.GitFailed) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if written.changed:
        print(f"wrote {written.code} and its record {written.record}")
    else:
        print(f"{written.code} is up to date: its record verifies, so nothing was written")
    for loss in written.losses:
        print(f"loss: {loss.plugin} {loss.did.replace('-', ' ')} `{loss.what}`: {loss.why}")
    if written.losses:
        print(
            f"accept a loss under `accept-losses` in {code.file_of(found.path, args.name)} to "
            f"stop it being reported"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
