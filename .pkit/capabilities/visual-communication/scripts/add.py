#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml==0.19.1",
# ]
# ///
"""visual-communication capability — add: copy a library the capability ships into the
location's library folder, and list it (DEC-002 point 3, DEC-003 points 4 and 5).

Copies the version of the library the capability ships, whole, to
`libraries/<library>/<version>/` in the location, and lists it in
`libraries/libraries.yaml` with the source `shipped`, every other byte of the list kept.
The shipped libraries are not released yet, so the list marks the version
`released: false`. Running the command is the consent for the copy: no version transition
copies a library into the location (DEC-003 point 5).

It refuses a library the capability does not ship, naming the ones it ships; a version
whose files of the capability's format lack their binding; a version the library folder
holds, which it never overwrites, or that the list names already; and a library the list
names from another source, since a name ties one library to its source.

It writes in the location, so where the configuration records none it takes `visual/` and
records it before its first write, or the path `--location` names. Every check that can
refuse runs before that first write, so a refused copy writes nothing, the location
included.

Usage:
  pkit visual add <library> [--location <path>]

Exit codes:
  0  copied and listed
  1  refused: nothing is written
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))

from _lib import libraries, location
from _lib.root import project_root


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="pkit visual add",
        description="Copy a library the capability ships into the location's library folder.",
    )
    parser.add_argument("library", help="the library's name, as the capability ships it")
    parser.add_argument("--location", help="the location to take and record, where none is")
    args = parser.parse_args()
    root = project_root()
    try:
        return _add(root, args.library, args.location)
    except (libraries.CopyRefused, location.LocationRefused, location.GitFailed) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


def _add(root: Path, name: str, given: str | None) -> int:
    where = location.for_writing(root, given)
    planned = libraries.plan_copy(root, where.path, name)
    if where.record:
        print(location.record(root, where.path))
    libraries.copy_shipped(planned)
    library = planned.library
    count = len(planned.files)
    print(
        f"copied {library.label}, {count} file{'s' if count != 1 else ''}, to "
        f"{planned.folder.relative_to(root).as_posix()}/"
    )
    print(
        f"listed {library.label} in {planned.list_file.relative_to(root).as_posix()}, "
        f"from the source `shipped`, not released"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
