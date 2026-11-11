#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml==0.19.1",
#   "uharfbuzz==0.57.0",
#   "fonttools==4.68.0",
#   "uniseg==0.10.1",
# ]
# ///
"""visual-communication capability — prune: remove each library version that lies behind,
after showing the list and asking once (DEC-019 points 9 and 10, and point 11's second bullet).

A version lies behind where no lock names it, the lock of the version that wrote a current copy
included; no lock that moves can still reach it; a newer version of its major serves in its
place; and it holds no unreleased work (`_lib/pruning.py`). The run takes no version by name,
and reads only the working tree.

It lists each version it would remove, each it spares with why, and each kept export made
under a version it removes. `--dry-run` shows that list and removes nothing. Otherwise it asks a
terminal once, and `--yes` is a person's consent up front. With nobody to ask and no consent
given, it refuses and removes nothing. It removes from the working tree alone, and stages
nothing, so a reviewer reads the removal as a diff.

A lock it cannot read stops it, and so do a record of exports it cannot read and a fingerprint
it cannot read of the version that wrote a current copy, each naming the file.

It writes in the location, so where the configuration records none it takes `visual/` and
records it before its first write, or the path `--location` names. Every check that can refuse
runs before that first write, so a refused run writes nothing, the location included. It writes
as one change: a removal that fails leaves every file as it was before the run, or names each it
could not put back.

Usage:
  pkit visual prune [--dry-run] [--yes] [--location <path>]

Exit codes:
  0  removed what lies behind, found nothing to remove, ended a dry run, or was answered no
  1  refused or stopped: nothing is removed. Or a removal failed: it names the file, and every
     file is as it was before the run, or each it could not put back is named
  2  a usage error
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))

from _lib import files, location, pruning
from _lib import pipeline as pl
from _lib.root import project_root

#: What a run says where no version lies behind.
NOTHING = "nothing to remove: no library version lies behind"

#: What a dry run says after its list.
DRY_RUN = "dry run: nothing is removed"

#: What a run says where the person answers anything but yes.
DECLINED = "nothing is removed"

#: What stops a run with nobody to ask and no consent given.
NOBODY = (
    "the run asks before it removes, and no terminal is here to ask: run it at a terminal, or "
    "pass --yes to consent to the list above. Nothing is removed"
)

#: What a run says once it has removed what lies behind.
LEFT = (
    "removed from the working tree alone, with nothing staged: land the removal as a change of "
    "its own, after any proposal lands"
)

#: How a version removed comes back.
WAY_BACK = (
    "to bring one back, restore it from version control, or bring a shipped one in again with "
    "`pkit visual add <library>@<version>`"
)


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="pkit visual prune",
        description="Remove each library version that lies behind, after showing the list.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="show what the run would remove and spare, and remove nothing",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="consent up front to the list the run shows, so it asks nothing",
    )
    parser.add_argument("--location", help="the location to take and record, where none is")
    args = parser.parse_args()
    root = project_root()
    try:
        return _prune(root, args)
    except (
        pl.Refused,
        location.LocationRefused,
        location.GitFailed,
        files.WriteFailed,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


def _prune(root: Path, args: argparse.Namespace) -> int:
    where = location.for_writing(root, args.location)
    planned = pruning.plan(root, where.path)
    for line in pruning.report(planned):
        print(line)
    if not planned.removed:
        print(NOTHING)
        return 0
    if args.dry_run:
        print(DRY_RUN)
        return 0
    if not args.yes:
        if not _terminal():
            print(f"error: {NOBODY}", file=sys.stderr)
            return 1
        count = len(planned.removed)
        if not _consents(f"remove the {count} version{'s' if count > 1 else ''} listed? [y/N] "):
            print(DECLINED)
            return 0
    change = files.Change(root)
    said = location.record(change, where)
    pruning.write(planned, change)
    if said is not None:
        print(said)
    for line in (*pruning.removed_lines(planned), LEFT, WAY_BACK):
        print(line)
    return 0


def _terminal() -> bool:
    """Whether a person at a terminal can answer the run's question."""
    try:
        return bool(sys.stdin is not None and sys.stdin.isatty())
    except (AttributeError, ValueError, OSError):
        return False


def _consents(question: str) -> bool:
    """Whether the person answers `question` yes."""
    try:
        reply = input(question)
    except EOFError:
        return False
    return reply.strip().lower() in ("y", "yes")


if __name__ == "__main__":
    sys.exit(main())
