"""The two looks of `pkit visual before-after`: a piece's pages drawn under two locks (DEC-019
point 5).

- **A look ahead** (`ahead`), before a move. Its before is the lock of the version that
  wrote a published piece's current copy, and otherwise the lock the piece holds. Its after
  is what a run would propose (`libraries.propose_lock`), or the versions a person names in
  the form `pkit visual add` takes. It states what the search states: each newer version
  held back with why, each library moved below the lock, and each clash or lost end a name
  goes past.
- **Who takes one.** No run proposes a draft's lock, pinned or not, so a draft takes a look
  ahead only with versions named, and those may include one not yet released (DEC-003
  point 8). A published piece's may not. No run moves a final piece's lock, so its after is
  the lock it holds, and a version named refuses.
- **A look back** (`back`), at a change. Its base is the backbone's answer for a comparison:
  where the branch left the default branch, or a base a person names (COR-054 points 3 and
  5). A base that resolves to nothing refuses (point 4). Its before is the lock of the
  version that wrote the copy at that commit, or the lock held there where no version did.
  Its after is the lock the piece holds now. Only the piece's own file and its record are
  read at the base, each as a file on disk is (`files.load_bound`), since both drawings
  take the same content.
- **What each drawing takes** (`sides`). Today's engine, the piece's files as they lie and
  the pictures they hold, and one filling of an export's facts, so what differs is the
  locks'. No program runs. A lock checked and found not to hold, a before no lock can be
  read for, or a drawing that fails gives a side that says why, and stops nothing: the
  other side is still drawn.
- **What it says** (`report`). Each lock, what the search states, a release that differs
  from the one the copy's version recorded, each stale picture, and each page that differs.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Collection, Iterator, Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from _lib import backbone, before_after, copies, current_copy, exports, fingerprint, libraries
from _lib import location as loc
from _lib import pipeline as pl
from _lib.before_after import Side
from _lib.files import FileError, load_bound
from _lib.libraries import Held
from _lib.reading import ReadError

#: The backbone's reading of a comparison's base (COR-054 point 5), and its version this
#: capability reads.
BASE_ARGV = ("pkit", "repository", "base", "--json")
READING_VERSION = 1

#: As much of a commit as a person needs to find it.
SHORT = 12

#: Whose each lock is, where it is the one the piece's own file holds.
HELD = "the lock the piece holds"
HELD_NOW = "the lock the piece holds now"

#: Whose an after is, where the search gives it.
PROPOSED = "what a run would propose"
NAMED = "the versions named"

#: What versions a person named go past, by the rule of the misfit (`libraries.Misfit`).
PAST = {"clash": "a clash", "end": "a lost end"}


@dataclass(frozen=True)
class Before:
    """A look's before: the lock it draws and, in words, whose that is. Where it has no lock,
    `lock` is None and `said` says why. Where a version wrote the copy, `version` names it
    and `release` is the capability's release it recorded."""

    lock: Mapping[str, str] | None
    said: str
    version: int | None = None
    release: str = ""


@dataclass(frozen=True)
class Look:
    """Two locks of a piece, whose each is, and what the search for the after states, a line
    each."""

    piece: pl.Piece
    held: Held
    before: Before
    after: Mapping[str, str]
    after_said: str
    stated: tuple[str, ...] = ()


def ahead(piece: pl.Piece, held: Held, names: Sequence[str]) -> Look:
    """A look ahead at `piece`, its after the versions `names` names, each
    `<library>@<version>`, or with none what a run would propose. Raises Refused where the
    piece takes none, or the search refuses."""
    _refuse_no_lock(piece)
    if piece.final:
        if names:
            raise pl.Refused(
                f"the piece `{piece.name}` is final, so no version moves its lock: take the look "
                f"ahead with none named"
            )
        return Look(piece, held, Before(piece.lock, HELD), piece.lock, HELD)
    published = current_copy.keeps(piece)
    if not published and not names:
        raise pl.Refused(
            f"no run proposes a draft's lock, so a look ahead at `{piece.name}` takes the "
            f"versions you name: `<library>@<version>`, as `pkit visual add` takes one"
        )
    try:
        moved = libraries.propose_lock(
            held,
            pl.needed(piece),
            piece.lock,
            names=names,
            unreleased=not published,
            judge=pl.fit(piece, held),
        )
    except libraries.LockRefused as exc:
        raise pl.Refused(f"{piece.file(pl.PIECE_FILE)}: {exc}") from exc
    before = _copys_before(piece) if published else Before(piece.lock, HELD)
    return Look(piece, held, before, moved.lock, NAMED if names else PROPOSED, _stated(moved))


def _copys_before(piece: pl.Piece) -> Before:
    """A published piece's before: the lock of the version that wrote its current copy, the
    lock it holds where none did, and where the record cannot be read, why."""
    try:
        return _written(piece, exports.recorded(piece)) or Before(piece.lock, HELD)
    except pl.Refused as exc:
        return Before(None, str(exc))


def back(piece: pl.Piece, held: Held, base: str | None) -> Look:
    """A look back at `piece`, from where this branch left `base`, or the base the backbone
    answers for a comparison. Raises Refused where the piece has no lock, or the base
    resolves to nothing."""
    _refuse_no_lock(piece)
    return Look(piece, held, _before_at(piece, base_commit(piece.root, base)), piece.lock, HELD_NOW)


def base_commit(root: Path, base: str | None) -> str:
    """Where this branch left `base`, or the base the backbone answers for a comparison
    (COR-054 points 3 and 5). What the backbone says on standard error, such as a base read
    from a local branch, is passed on. Raises Refused where the reading gives no answer, or
    the base resolves to nothing (COR-054 point 4)."""
    argv = [*BASE_ARGV, *(() if base is None else (f"--base={base}",))]
    shown = " ".join(BASE_ARGV)
    try:
        proc = backbone.run(argv, cwd=root, capture_output=True, text=True, check=False)
    except OSError as exc:
        raise pl.Refused(f"`pkit` could not be run ({exc})") from exc
    if proc.stderr:
        sys.stderr.write(proc.stderr)
    try:
        document = json.loads(proc.stdout or "")
    except ValueError:
        document = None
    if proc.returncode != 0 or not isinstance(document, Mapping):
        raise pl.Refused(f"`{shown}` exited {proc.returncode} without its document")
    version = document.get("schema_version")
    if version != READING_VERSION:
        raise pl.Refused(
            f"`{shown}` answered schema_version {version!r}; this capability reads "
            f"{READING_VERSION}"
        )
    found = document.get("base")
    found = found if isinstance(found, Mapping) else {}
    fork = found.get("fork")
    if not isinstance(fork, str) or not fork:
        raise pl.Refused(str(found.get("problem") or "the base resolves to no commit"))
    return fork


def _before_at(piece: pl.Piece, commit: str) -> Before:
    """A look back's before, from the piece's own file and its record at `commit`: the lock
    of the version that wrote the copy there, or the lock held there. Where the commit does
    not hold the piece, or its files cannot be read, it has no lock, and says why. Raises
    GitFailed where git cannot read the commit."""
    at = f"the base {commit[:SHORT]}"
    listed = loc.files_at(piece.root, commit, f"{piece.location}/{pl.PIECES}")
    if piece.file(pl.PIECE_FILE) not in listed:
        return Before(None, f"{at} does not hold the piece `{piece.name}`")
    try:
        lock = _read_at(piece, commit, pl.PIECE_FILE, "piece").get("lock")
        written = None
        if piece.file(pl.EXPORTS_FILE) in listed:
            record = _read_at(piece, commit, pl.EXPORTS_FILE, "exports")
            written = _written(piece, record, pl.pieces_in(piece.location, listed))
    except pl.Refused as exc:
        return Before(None, f"at {at}: {exc}")
    if written is not None:
        return replace(written, said=f"{written.said}, at {at}")
    if not isinstance(lock, Mapping) or not lock:
        return Before(None, f"{at} holds the piece `{piece.name}` with no lock")
    return Before(dict(lock), f"the lock held at {at}")


def _read_at(piece: pl.Piece, commit: str, name: str, kind: str) -> dict[str, Any]:
    """The value of the piece's file `name` at `commit`, a file of `kind`, read as a file on
    disk is, an older format through its converters (DEC-003 point 2). Raises Refused where
    it cannot be, and GitFailed."""
    rel = piece.file(name)
    data = loc.file_at(piece.root, commit, rel)
    try:
        return load_bound(data, rel, kind)
    except (ReadError, FileError) as exc:
        raise pl.Refused(str(exc)) from exc


def _written(
    piece: pl.Piece, record: Mapping[str, Any], pieces: Collection[str] | None = None
) -> Before | None:
    """The lock of the version that wrote the piece's current copy, as the record of exports
    `record` gives it, or None where it names none of the piece's own. `pieces` is as
    `current_copy.own` takes it. Raises Refused where that lock cannot be read, as the gate
    of an export does (DEC-017 point 5)."""
    entry = current_copy.own(piece, record, pieces)
    if entry is None:
        return None
    number = entry["version"]
    said = f"version {number}, which wrote the current copy"
    versions = exports.recorded_versions(piece, record)
    try:
        lock = current_copy.written_lock(entry, versions)
    except fingerprint.UnreadableFingerprint as exc:
        raise pl.Refused(f"{piece.file(pl.EXPORTS_FILE)} gives no lock of {said}: {exc}") from exc
    release = current_copy.written_release(entry, versions)
    return Before(lock, f"the lock of {said}", number, release)


def _refuse_no_lock(piece: pl.Piece) -> None:
    """Raise Refused where the piece has no lock yet, naming what writes one."""
    if piece.lock:
        return
    stays = piece.lock_stays
    way = copies.no_lock(piece.final) if stays else f"run {pl.render_command(piece.name)} first"
    raise pl.Refused(f"the piece `{piece.name}` has no lock yet, so no look draws it: {way}")


def _stated(moved: libraries.Moved) -> tuple[str, ...]:
    """What the search for an after states, a line each: each newer version it held back,
    with why; each library it moved below the lock; a search that kept the lock; and each
    clash or lost end versions named go past (DEC-019 point 7)."""
    return (
        *(
            f"held back: {held.label}: {'; '.join(reason.said for reason in held.reasons)}"
            for held in moved.held_back
        ),
        *moved.below,
        *((moved.kept,) if moved.kept else ()),
        *(f"goes past {PAST[misfit.rule]}: {misfit.said}" for misfit in moved.past),
    )


def sides(look: Look) -> tuple[Side, Side]:
    """The look's two drawings. Where its locks are one, it draws once. Where it has no
    lock of its before, that side says why."""
    after = _side(look, look.after)
    lock = look.before.lock
    if lock is None:
        return Side(why=look.before.said), after
    return (after if lock == look.after else _side(look, lock)), after


def _side(look: Look, lock: Mapping[str, str]) -> Side:
    """The piece's pages under `lock`, or why not. It checks the lock first, since a library
    version gone would otherwise leave only a hole in the drawing."""
    piece = look.piece
    try:
        libraries.move_lock(look.held, pl.needed(piece), lock, pinned=True)
    except libraries.LockRefused as exc:
        return Side(why=str(exc))
    return before_after.drawing(piece.root, piece.location, piece.name, lock)


def report(look: Look, before: Side, after: Side) -> Iterator[str]:
    """What the command prints of a look and its two drawings, a line each."""
    name, lock = look.piece.name, look.before.lock
    if lock is not None:
        yield f"before: {look.before.said}: {_versions(lock)}"
    yield f"after: {look.after_said}: {_versions(look.after)}"
    if lock == look.after:
        yield "the two locks are one"
    yield from _release(look)
    yield from look.stated
    yield from _stale(before, after)
    if before.why == after.why != "":
        yield f"no drawing: {after.why}"
    elif before.why or after.why:
        yield from (f"no {side}: {why}" for side, why in _whys(before, after))
        drawn, folder = (after, before_after.AFTER) if before.why else (before, before_after.BEFORE)
        if drawn.files:
            where = f"{before_after.FOLDER}/{name}/{folder}/"
            yield f"drawn in {where}: {len(drawn.files)} files, and nothing to compare them with"
    else:
        yield before_after.both_ways(name, before, after)
        yield from (f"differs: {file}" for file in before_after.differing(before, after))


def _whys(before: Side, after: Side) -> Iterator[tuple[str, str]]:
    """Each side that gives no drawing, with why."""
    for side, drawn in ((before_after.BEFORE, before), (before_after.AFTER, after)):
        if drawn.why:
            yield side, drawn.why


def _release(look: Look) -> Iterator[str]:
    """That today's engine is another release than the one the copy's version recorded, so
    the copy's two sides hold more than the move, where it is."""
    now = ".".join(map(str, look.held.release))
    then = look.before.release
    if then and then != now:
        yield (
            f"the engine is release {now}, and version {look.before.version}, which wrote the "
            f"copy, recorded {then}: the copy's two sides hold more than the move"
        )


def _stale(before: Side, after: Side) -> Iterator[str]:
    """Each picture a side drew stale or could not find, once where the sides agree."""
    said: dict[tuple[str, tuple[str, ...]], list[str]] = {}
    for side, drawn in ((before_after.BEFORE, before), (before_after.AFTER, after)):
        for output, changes in drawn.stale.items():
            said.setdefault((output, tuple(changes)), []).append(side)
    for (output, changes), named in sorted(said.items()):
        yield f"stale, {' and '.join(named)}: `{output}`: {'; '.join(changes)}"


def _versions(lock: Mapping[str, str]) -> str:
    """A lock in words."""
    return ", ".join(f"{library} {lock[library]}" for library in sorted(lock))
