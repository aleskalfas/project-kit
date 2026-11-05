#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml==0.19.1",
# ]
# ///
"""visual-communication capability — add: copy a library the capability ships into the
location's library folder, list it, and bring every copy of it up to date (DEC-002 point 3,
DEC-003 points 4 and 5, DEC-013 point 5).

Copies the newest released version of the library the capability ships, whole, to
`libraries/<library>/<version>/` in the location, and lists it in `libraries/libraries.yaml`
with the source `shipped`, `released: true` and the hash the library's record keeps, as it
is. `<library>@<version>` names another released version; `--being-built` takes the
version being built, or the released version of its number where it carries a released
one. Where the library has no released version, it takes the version being built, and
lists it `released: false`, with no hash.

The same run brings up to date every copy of the library the location holds or its list
names: a copy not yet released, of a number the capability ships, is replaced whole by what
the capability ships under it, and listed released, with its hash, where that number is
released; a released copy whose files no longer match its hash is restored; a released copy
that matches is not written. A new number is copied beside the others. A copy of a number
the installed capability does not ship stays as it is. A version the list names whose
folder is missing is brought in as a copy of its kind is. A copy not yet released is
replaced only where every lock that names it is an unpinned draft's. Under a pinned draft's
lock, or written code's, or one the command cannot read, it stays as it is, the command
names each such piece or declaration, and the rest of the run goes on. Every other byte of
the list is kept. Running the command is the consent for each copy it writes: no version
transition copies a library into the location (DEC-003 point 5).

It refuses a library the capability does not ship, naming the ones it ships; a released
version it does not ship; files it ships that no longer match the hash the library's
record keeps, or whose files of the capability's format lack their binding; a hash the list
keeps for a released version that differs from the one the capability records, naming
both; a version folder the list does not name, where the version is to be copied; and a
library the list names from another source, since a name ties one library to its source.

It writes in the location, so where the configuration records none it takes `visual/` and
records it before its first write, or the path `--location` names. Every check that can
refuse runs before that first write, so a refused run writes nothing, the location
included. It moves each copied folder into its place, a folder it replaces moved aside,
then writes the list, as one change: a write that fails puts every folder back, and leaves
the list and the configuration as they were before the run.

It prints each copy it writes, as copied, replaced or restored, with each piece and
declaration whose lock names it; each copy it leaves, with why; and each version it lists.

Usage:
  pkit visual add <library>[@<version>] [--being-built] [--location <path>]

Exit codes:
  0  every copy written, or left with why
  1  refused: nothing is written. Or a write failed: it names the file, and every file is
     as it was before the run, or each it could not put back is named
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))

from _lib import copies, files, location
from _lib.libraries import Version
from _lib.root import project_root


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="pkit visual add",
        description=(
            "Copy a library the capability ships into the location's library folder, and "
            "bring every copy of it up to date."
        ),
    )
    parser.add_argument(
        "library",
        help="the library's name, as the capability ships it, or `<library>@<version>` for "
        "one of its released versions",
    )
    parser.add_argument(
        "--being-built",
        action="store_true",
        help="take the version being built, or the released version of its number",
    )
    parser.add_argument("--location", help="the location to take and record, where none is")
    args = parser.parse_args()
    root = project_root()
    try:
        return _add(root, args.library, args.being_built, args.location)
    except (
        copies.CopyRefused,
        location.LocationRefused,
        location.GitFailed,
        files.WriteFailed,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


def _add(root: Path, named: str, being_built: bool, given: str | None) -> int:
    name, at, number = named.partition("@")
    version = None
    if at:
        try:
            version = Version.parse(number)
        except ValueError as exc:
            raise copies.CopyRefused(f"`{named}`: {exc}") from exc
        if being_built:
            raise copies.CopyRefused(
                f"`{named}` names a released version, and `--being-built` asks for the "
                f"version being built: ask for one of them"
            )
    where = location.for_writing(root, given)
    planned = copies.plan(root, where.path, name, version, being_built=being_built)
    change = files.Change(root)
    said = location.record(change, where)
    copies.write(planned, change)
    if said is not None:
        print(said)
    for line in copies.report(planned, root):
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
