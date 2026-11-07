#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "jsonschema==4.26.0",
#   "ruamel.yaml==0.19.1",
#   "uharfbuzz==0.57.0",
#   "fonttools==4.68.0",
#   "uniseg==0.10.1",
# ]
# ///
"""visual-communication capability — add: copy a library the capability ships into the
location's library folder, list it, and bring every copy of it up to date (DEC-002 point 3,
DEC-003 points 4, 5 and 8, DEC-005 point 7, DEC-013 point 5).

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
folder is missing is brought in as a copy of its kind is. Every other byte of the list is
kept. Running the command is the consent for each copy it writes: no version transition
copies a library into the location (DEC-003 point 5).

A copy not yet released is replaced only where every lock that names it is an unpinned
draft's or a final piece's, or the person names the piece or the declaration it locks:
`--piece <name>` and `--declaration <name>` name each pinned draft, each published piece and
each declaration of written code. Naming it is the move on purpose: the lock keeps its
number, no `piece.yaml` and no declaration is written, and what it draws, or the code it
writes, changes only then. Where any such lock is left unnamed, or cannot be read, the copy
stays as it is, the command names each left, and the rest of the run goes on.

For each lock left that it can read, the run shows what replacing the copy would change: a
pinned draft's or a published piece's scenes drawn with the copy as it is and with what the
capability ships, in
`.pkit/capabilities/visual-communication/project/local/before-after/<piece>/`, local to the
clone; and a declaration's difference in the code its writer writes with each. Where it
cannot draw or write a side, it says why, and goes on.

It refuses a library the capability does not ship, naming the ones it ships; a released
version it does not ship; files it ships that no longer match the hash the library's
record keeps, or whose files of the capability's format lack their binding; a hash the list
keeps for a released version that differs from the one the capability records, naming
both; a version folder the list does not name, where the version is to be copied; a library
the list names from another source, since a name ties one library to its source; and a
piece or a declaration named that locks no copy the run would replace, naming what it locks.

It writes in the location, so where the configuration records none it takes `visual/` and
records it before its first write, or the path `--location` names. Every check that can
refuse runs before that first write, so a refused run writes nothing, the location
included. It moves each copied folder into its place, a folder it replaces moved aside,
then writes the list, as one change with the before-and-after it keeps: a write that fails
puts every folder back, and leaves the list and the configuration as they were before the
run.

It prints each copy it writes, as copied, replaced or restored, with each piece and
declaration whose lock names it; each copy it leaves, with why, each lock left with its
before-and-after, and, where it can read each, the command that names them; and each
version it lists.

Usage:
  pkit visual add <library>[@<version>] [--being-built] [--location <path>]
                  [--piece <name>]... [--declaration <name>]...

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

from _lib import before_after, copies, files, location
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
    parser.add_argument(
        "--piece",
        action="append",
        default=[],
        metavar="<name>",
        help="a pinned draft or a published piece whose copy the run may replace; repeat for each",
    )
    parser.add_argument(
        "--declaration",
        action="append",
        default=[],
        metavar="<name>",
        help="a declaration of written code whose copy the run may replace; repeat for each",
    )
    args = parser.parse_args()
    root = project_root()
    named = {
        *((copies.PIECE, name) for name in args.piece),
        *((copies.DECLARATION, name) for name in args.declaration),
    }
    try:
        return _add(root, args.library, args.being_built, args.location, named)
    except (
        copies.CopyRefused,
        location.LocationRefused,
        location.GitFailed,
        files.WriteFailed,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


def _add(
    root: Path, library: str, being_built: bool, given: str | None, named: set[tuple[str, str]]
) -> int:
    name, at, number = library.partition("@")
    version = None
    if at:
        try:
            version = Version.parse(number)
        except ValueError as exc:
            raise copies.CopyRefused(f"`{library}`: {exc}") from exc
        if being_built:
            raise copies.CopyRefused(
                f"`{library}` names a released version, and `--being-built` asks for the "
                f"version being built: ask for one of them"
            )
    where = location.for_writing(root, given)
    planned = copies.plan(root, where.path, name, version, being_built=being_built, named=named)
    change = files.Change(root)
    said = location.record(change, where)
    shown = before_after.shown(root, where.path, planned, change)
    copies.write(planned, change)
    if said is not None:
        print(said)
    for line in copies.report(planned, root, shown):
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
