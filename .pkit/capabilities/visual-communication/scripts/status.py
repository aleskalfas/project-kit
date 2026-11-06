#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml==0.19.1",
# ]
# ///
"""visual-communication capability — status: where the visual work lies, and each piece
with its state and its lock (DEC-002 point 1, DEC-003 point 8).

Shows the location, and whether a command recorded it in the capability's configuration
or it is the default, `visual/`, not recorded yet; then each piece of the location, with
its state and its lock. A piece is a folder of the location's `pieces/` that holds files,
and its `piece.yaml` says its state and its lock. The files are listed as git sees them.

It only reads, and needs no network.

Usage:
  pkit visual status

Exit codes:
  0  shown, no visual work included
  1  the location cannot be read: the configuration cannot be read, or records a location
     that is refused or whose folder is missing
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))

from _lib import location as loc
from _lib.copies import DRAFT, lock_stays, no_lock
from _lib.files import binding_problem
from _lib.reading import ReadError, read_yaml
from _lib.root import CONFIG, project_root

#: The folder of the location that holds the pieces, one folder each.
PIECES = "pieces"


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="pkit visual status",
        description="Show the location and each piece with its state and its lock.",
    )
    parser.parse_args()
    root = project_root()
    try:
        found = loc.for_reading(root)
        pieces = _pieces(root, found.path) if found is not None else []
    except (loc.LocationRefused, loc.GitFailed) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if found is None:
        print(
            f"location: none — {CONFIG} records none, and `{loc.DEFAULT}/` holds no visual "
            f"work; the first command that writes takes `{loc.DEFAULT}` and records it"
        )
        return 0
    if found.recorded:
        print(f"location: {found.path} (recorded in {CONFIG})")
    else:
        print(
            f"location: {found.path} (the default, not recorded yet; the first command that "
            f"writes there records it in {CONFIG})"
        )
    if not pieces:
        print("pieces: none")
        return 0
    print("pieces:")
    for name, shown in pieces:
        print(f"  {name}: {shown}")
    return 0


def _pieces(root: Path, location: str) -> list[tuple[str, str]]:
    """Each piece of the location, by name, with its state and its lock in words."""
    prefix = f"{location}/{PIECES}/"
    names = sorted(
        {rel[len(prefix) :].split("/")[0] for rel in loc.files(root, f"{location}/{PIECES}")}
    )
    return [(name, _piece(root / prefix / name / "piece.yaml")) for name in names]


def _piece(path: Path) -> str:
    """A piece's state and its lock, from its `piece.yaml`, in words."""
    if not path.is_file():
        return "no piece.yaml"
    try:
        data = read_yaml(path)
    except ReadError as exc:
        return f"piece.yaml cannot be read: {exc}"
    problem = binding_problem(data, "piece")
    if problem is not None:
        return f"piece.yaml {problem}"
    state = str(data.get("state", "no state"))
    if state == DRAFT and data.get("pinned") is True:
        state += ", pinned"
    lock = data.get("lock")
    if isinstance(lock, dict) and lock:
        locked = "lock " + ", ".join(f"{name} {lock[name]}" for name in sorted(lock))
    elif lock_stays(data):
        locked = f"no lock ({no_lock(data)})"
    else:
        locked = "no lock yet (its first render writes one)"
    return f"{state}; {locked}"


if __name__ == "__main__":
    sys.exit(main())
