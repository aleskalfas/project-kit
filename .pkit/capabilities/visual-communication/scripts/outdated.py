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
"""visual-communication capability — outdated: what each lock a person moves could still take,
across majors (DEC-019 points 8 and 11).

It takes each lock a person moves, as the command that brings a library in reads the locks
(`copies.locks`): a published piece's, a pinned draft's and written code's. An unpinned draft's
render moves its own lock, and a final piece's never moves, so both are left out.

For each library a lock names, it names the newest version that fits within the lock's major,
as the search of a proposed move works it out (`libraries.propose_lock`). A published piece's
search takes released versions alone, since its lock holds no other. The search of a lock a hand
moves takes every version, since a pinned draft's lock, and written code's, may hold one not yet
released. A piece is placed under each combination the search judges, as a draft's render
places it (`pipeline.fit`). Written code places nothing, so only its lock is judged.

It names each other newer version too, with why that search would not take it: a later major,
a clash, a lost end, a version the installed capability cannot read, or what else the search
says held it back. A lock is behind where such a version stands, or a newer one fits. A
published piece's lock is never behind a version not yet released.

It says so where none is behind, and names each lock it could not judge, with why. It reads
only, needs no network and writes nothing.

Usage:
  pkit visual outdated

Exit codes:
  0  listed, whatever is behind or could not be judged
  1  the location cannot be read: the configuration cannot be read, or records a location
     that is refused or whose folder is missing
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))

from _lib import copies, current_copy, libraries
from _lib import location as loc
from _lib import pipeline as pl
from _lib.libraries import Held, HeldBack, Version
from _lib.root import CONFIG, project_root


@dataclass(frozen=True)
class Behind:
    """A library a lock names that is behind: the version the lock names, the newest that fits
    within its major, and each newer version the search did not take, with why."""

    name: str
    locked: Version
    fits: Version
    others: tuple[HeldBack, ...]


@dataclass(frozen=True)
class Judged:
    """A lock a person moves, judged: each library of it that is behind, what the search states
    of the lock as a whole, and whether it takes released versions alone. Where it could not be
    judged, `why` says why."""

    lock: copies.Lock
    behind: tuple[Behind, ...] = ()
    stated: tuple[str, ...] = ()
    released_only: bool = False
    why: str = ""


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="pkit visual outdated",
        description="List what each lock a person moves could still take, across majors.",
    )
    parser.parse_args()
    root = project_root()
    try:
        found = loc.for_reading(root)
        if found is None:
            print(f"No visual work: {CONFIG} records no location, and `{loc.DEFAULT}/` holds none.")
            return 0
        held = Held(root, found.path)
        judged = [
            judge(root, found.path, held, lock)
            for lock in copies.locks(root, found.path)
            if not lock.follows
        ]
    except (loc.LocationRefused, loc.GitFailed) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    for line in report(judged):
        print(line)
    return 0


def judge(root: Path, location: str, held: Held, lock: copies.Lock) -> Judged:
    """`lock` judged: each library of it that is behind, or why it could not be judged."""
    if lock.versions is None:
        return Judged(lock, why=lock.why)
    if not lock.versions:
        return Judged(lock, why="it holds no lock yet")
    try:
        moved, released_only = _searched(root, location, held, lock)
    except (pl.Refused, libraries.LockRefused) as exc:
        return Judged(lock, why=str(exc))
    behind = _behind(held, lock.versions, moved, released_only)
    stated = (*moved.below, *((moved.kept,) if moved.kept else ()))
    return Judged(lock, behind, stated if behind or moved.kept else (), released_only)


def _searched(
    root: Path, location: str, held: Held, lock: copies.Lock
) -> tuple[libraries.Moved, bool]:
    """The move the search of a proposed move works out for `lock`, with no version named, and
    whether it takes released versions alone: a published piece's does. Raises Refused where
    the piece cannot be read, and LockRefused where the search refuses."""
    assert lock.versions is not None
    if lock.kind == copies.DECLARATION:
        names = sorted(lock.versions)
        return libraries.propose_lock(held, names, lock.versions, unreleased=True), False
    piece = pl.read_piece(root, location, lock.name)
    published = current_copy.keeps(piece)
    moved = libraries.propose_lock(
        held,
        pl.needed(piece),
        piece.lock,
        unreleased=not published,
        judge=pl.fit(piece, held),
    )
    return moved, published


def _behind(
    held: Held, lock: Mapping[str, str], moved: libraries.Moved, released_only: bool
) -> tuple[Behind, ...]:
    """Each library `lock` names that is behind, in name order: a newer version than the lock
    names fits within its major, or the search held one back. A published piece's search
    holds back each version not yet released, and its lock is behind none of them."""
    found = []
    for name in sorted(moved.lock):
        try:
            locked = Version.parse(lock.get(name))
        except ValueError:
            continue  # the piece uses a library its lock does not name: the check's to report
        fits = Version.parse(moved.lock[name])
        others = tuple(
            each
            for each in moved.held_back
            if each.name == name
            and each.version > locked
            and (not released_only or held.released(name, each.version))
        )
        if fits > locked or others:
            found.append(Behind(name, locked, fits, others))
    return tuple(found)


def report(judged: Sequence[Judged]) -> Iterator[str]:
    """What the command prints, a line each: how many locks are behind, then each with what it
    could take and the way to move it, then each lock it could not judge, with why."""
    read = [each for each in judged if not each.why]
    behind = [each for each in read if each.behind or each.stated]
    counted = f"{len(read)} lock{'' if len(read) == 1 else 's'} a person moves"
    yield f"behind: {len(behind)} of {counted}" if behind else f"behind: none, of {counted}"
    for each in behind:
        yield f"{each.lock.described}, in {each.lock.file}: {_way(each)}"
        newest = "newest released version" if each.released_only else "newest version"
        for library in each.behind:
            major = library.locked.major
            if library.fits == library.locked:
                said = f"no newer version fits within major {major}"
            else:
                said = f"{library.fits} is the {newest} that fits within major {major}"
            yield f"  {library.name} {library.locked}: {said}"
            for other in library.others:
                yield f"    {other.label}: {'; '.join(reason.said for reason in other.reasons)}"
        for line in each.stated:
            yield f"  {line}"
    for each in judged:
        if each.why:
            shown = each.lock.described if each.lock.versions is None else _shown(each)
            yield f"not judged: {shown}"


def _way(judged: Judged) -> str:
    """What moves the lock, in words."""
    lock = judged.lock
    if lock.kind == copies.DECLARATION:
        return f"a hand moves its lock, then `pkit visual write-code {lock.name}` writes the code"
    if judged.released_only:
        return (
            f"`pkit visual upgrade {lock.name}` proposes a move within its majors, and a later "
            f"major where you name it"
        )
    return "a hand moves its lock, or a render once it is unpinned"


def _shown(judged: Judged) -> str:
    """A lock that could not be judged, with why."""
    return f"{judged.lock.described}, in {judged.lock.file}: {judged.why}"


if __name__ == "__main__":
    sys.exit(main())
