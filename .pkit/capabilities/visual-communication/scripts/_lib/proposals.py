"""A proposed move of a published piece's lock: what one run of `pkit visual upgrade` leaves in
the working tree (visual-communication DEC-019 points 1 to 4, 6, 7 and 11).

- **A published piece alone** (`read`). Any other refuses, naming what moves that lock. The
  lock is read from the piece's own file, whoever wrote it, so a piece the gate stopped is
  served.
- **The look ahead** (`ahead`) gives what a run would propose, through the look of
  `pkit visual before-after` (`looks.ahead`), and reads the version that wrote the copy. A
  fingerprint it cannot read refuses, as the gate does.
- **Nothing to move** (`Move.settled`). The move would give the lock the piece holds, and that
  version was made under it.
- **An edit since the copy** stops the run (`_named_edits`). The piece is compared with that
  version, the lock put back and the files of its library versions left out, so a move counts
  for nothing, and a version gone from the project stops nothing. A person names each input
  to pass it. An input nobody named still stops, and the refusal prints the line that names
  them all. Where no version wrote a copy, nothing compares.
- **A stale picture** stops the run too, read under the moved lock, as it stops an export. It
  runs no program, since a program reads under the lock the piece holds, so the way past is
  its own (`_way_past_stale`): a person names each output to use it as it is. No run writes
  the lock and stops.
- **What it carries** (`plan`, `write`). The lock, the findings record of a render under it,
  and an export run under it, which follows every rule of an export but the gate: the gate
  lies in `export.py`, so nothing here passes through it. The drawing a look ahead gives is
  kept in the clone's local folder. So the version that wrote the copy was made under the lock
  the piece holds, the next export runs, and the move itself fails no check.
- **Refused before any write.** Every stop lies in `read`, `ahead` and `plan`. They write
  nothing, so a dry run takes them too, and leaves off where a run would draw and write.
- **Written as one change** (`write`). Where a write fails, every file is put back as it was
  before the run, or each it could not put back is named.
- **What the change shows** (`Planned.after_alone`). A file of the copy that no file stood at
  shows only its after, and the run says so (DEC-019 point 6).
- **What it says** (`report`, `failing`). What the move wrote, what it left behind, each
  input and output named, and each finding that fails now the lock has moved. Such a finding
  stops nothing: it holds the landing, and a person mends the content in the same change.
"""

from __future__ import annotations

from collections.abc import Callable, Collection, Iterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from _lib import (
    before_after,
    checks,
    copies,
    current_copy,
    exports,
    fingerprint,
    looks,
    rendering,
)
from _lib import pipeline as pl
from _lib.before_after import Side
from _lib.files import Change
from _lib.findings import FAILS
from _lib.libraries import Held


@dataclass(frozen=True)
class Writer:
    """The version that wrote the piece's current copy: its number, its lock and its
    fingerprint."""

    number: int
    lock: Mapping[str, str]
    fingerprint: Mapping[str, Any]


@dataclass(frozen=True)
class Move:
    """What a run would propose: the look ahead at it, and the version that wrote the piece's
    current copy, where one of its own did."""

    look: looks.Look
    writer: Writer | None

    @property
    def settled(self) -> bool:
        """Whether nothing moves: the move gives the lock the piece holds, and the version that
        wrote the copy was made under it."""
        lock = self.look.piece.lock
        return dict(self.look.after) == lock and (
            self.writer is not None and dict(self.writer.lock) == lock
        )


@dataclass(frozen=True)
class Named:
    """What a person named to a run: each library version to move to, each input that changed
    since the copy, and each stale output to use as it is."""

    versions: Sequence[str] = ()
    edited: Sequence[str] = ()
    use_stale: Sequence[str] = ()

    def line(self, piece: str, edited: Sequence[str], use_stale: Sequence[str]) -> str:
        """The command that runs again with these versions, `edited` and `use_stale`."""
        words = [
            "pkit visual upgrade",
            piece,
            *self.versions,
            *(f"--edited {name}" for name in edited),
            *(f"--use-stale {output}" for output in use_stale),
        ]
        return " ".join(words)


@dataclass(frozen=True)
class Planned:
    """A proposal checked and not yet written: the move, the bytes of `piece.yaml`, None where
    it stays as it is, the findings record, the export under the moved lock, each edit a person
    named, each input named that did not change, and each file of the copy that shows only its
    after, by its path from the repository's root, with whether no file of it stood at all."""

    move: Move
    piece_file: bytes | None
    findings: bytes
    export: exports.Planned
    edits: tuple[fingerprint.Edit, ...]
    not_edited: tuple[str, ...]
    after_alone: tuple[str, ...]
    none_stood: bool


def read(root: Path, location: str, name: str) -> pl.Piece:
    """The published piece `name`, read. Its own file comes first, so a fault in its content
    hides no state. Raises Refused for a piece in another state, naming what moves that lock,
    and for one with no lock."""
    piece = pl.read_piece_file(root, location, name)
    if piece.final:
        raise pl.Refused(
            f"the piece `{name}` is final ({piece.why_final}), and nothing moves a final piece's "
            f"lock"
        )
    if not current_copy.keeps(piece):
        way = (
            f"A hand moves a pinned draft's lock: change it in {piece.file(pl.PIECE_FILE)}"
            if piece.pinned
            else f"A draft's render moves its lock: run {pl.render_command(name)}"
        )
        raise pl.Refused(
            f"the piece `{name}` is a draft, and this run moves only a published piece's lock. "
            f"{way}"
        )
    if not piece.lock:
        raise pl.Refused(f"the piece `{name}` has no lock to move: {copies.no_lock(False)}")
    return pl.read_piece(root, location, name)


def ahead(piece: pl.Piece, held: Held, versions: Sequence[str]) -> Move:
    """What a run would propose for `piece`, the versions `versions` names or the newest that
    fit. Raises Refused where the search refuses, or the version that wrote the copy gives no
    lock."""
    return Move(looks.ahead(piece, held, versions), _writer(piece))


def _writer(piece: pl.Piece) -> Writer | None:
    """The version that wrote the piece's own current copy, or None where none did. Raises
    Refused, naming the record, where its fingerprint cannot be read."""
    record = exports.recorded(piece)
    entry = current_copy.own(piece, record)
    if entry is None:
        return None
    versions = exports.recorded_versions(piece, record)
    number = entry["version"]
    try:
        lock = current_copy.written_lock(entry, versions)
    except fingerprint.UnreadableFingerprint as exc:
        raise _unread(piece, number, exc) from exc
    return Writer(number, lock, current_copy.written_fingerprint(entry, versions))


def _unread(piece: pl.Piece, number: int, exc: Exception) -> pl.Refused:
    """The refusal of a fingerprint that cannot be read, which names the record, and the way
    out: that record as version control last held it (DEC-019 point 3)."""
    return pl.Refused(
        f"{piece.file(pl.EXPORTS_FILE)} gives no lock of version {number}, which wrote the "
        f"current copy: {exc}. Restore that record as version control last held it"
    )


def settled(move: Move) -> Iterator[str]:
    """What a run says where nothing moves, a line each: what the search states, then why."""
    look = move.look
    assert move.writer is not None
    yield from look.stated
    yield (
        f"nothing to move: `{look.piece.name}` holds {looks.versions_said(look.after)}, and "
        f"version {move.writer.number}, which wrote its current copy, was made under that lock"
    )


def plan(move: Move, named: Named) -> Planned:
    """The proposal of `move`: every stop passed, and every file it writes worked out and
    checked. Raises Refused, naming what stops it and the line that goes on where a name
    does, so `write` refuses nothing."""
    look = move.look
    piece, held = look.piece, look.held
    edits = [] if move.writer is None else _named_edits(piece, held, move.writer, named)
    locked = pl.locked(piece, look.after)
    data = {**piece.data, "lock": dict(look.after)}
    moved = pl.Piece(piece.root, piece.location, piece.name, data, piece.contents)
    project = rendering.exportable(moved, held)
    written = {} if locked is None else {piece.folder / pl.PIECE_FILE: locked}
    export = exports.plan(
        project,
        use_stale=named.use_stale,
        written=written,
        way_past_stale=_way_past_stale(piece.name, sorted({edit.name for edit in edits}), named),
    )
    pl.writable(piece.root, piece.folder / pl.FINDINGS_FILE)
    found = checks.scene_findings(project, export.results)
    record = rendering.record_text(rendering.record(project, found, locked))
    alone = _after_alone(export)
    return Planned(
        move,
        locked,
        record,
        export,
        tuple(edits),
        tuple(sorted(set(named.edited) - {edit.name for edit in edits})),
        tuple(alone),
        _none_stood(export, alone),
    )


def _named_edits(
    piece: pl.Piece, held: Held, writer: Writer, named: Named
) -> list[fingerprint.Edit]:
    """Each input of the piece's own that differs from the version that wrote its copy, where
    a person named every one. Raises Refused where an input changed that nobody named, naming
    each and the line that names them all (DEC-019 point 3)."""
    edits = _edits(piece, held, writer)
    unnamed = [edit for edit in edits if edit.name not in named.edited]
    if unnamed:
        said = "; ".join(edit.said for edit in unnamed)
        line = named.line(piece.name, sorted({edit.name for edit in edits}), named.use_stale)
        raise pl.Refused(
            f"`{piece.name}` changed since version {writer.number}, which wrote its current "
            f"copy: {said}. Run `pkit visual export {piece.name}` to land the edit under the "
            f"lock the copy holds, then this run again. Where the edit needs the move, name "
            f"each input: `{line}`"
        )
    return edits


def _edits(piece: pl.Piece, held: Held, writer: Writer) -> list[fingerprint.Edit]:
    """Each input of the piece's own that differs from the version that wrote its copy, read
    with that lock put back. Raises Refused where the fingerprint or an input cannot be
    read."""
    locked = pl.locked(piece, writer.lock)
    written = {} if locked is None else {piece.folder / pl.PIECE_FILE: locked}
    sources = pl.findings_key_sources(piece.root, held, piece, {}, [])
    fonts = pl.recorded_fonts(piece.root, piece.location, writer.fingerprint)
    try:
        return fingerprint.edits(
            writer.fingerprint,
            piece=sources["piece"],
            files=sources["files"],
            fonts=fonts,
            written=written,
        )
    except fingerprint.UnreadableFingerprint as exc:
        raise _unread(piece, writer.number, exc) from exc
    except fingerprint.FingerprintError as exc:
        raise pl.Refused(
            f"the piece `{piece.name}` cannot be compared with version {writer.number}, which "
            f"wrote its current copy: {exc}"
        ) from exc


def _way_past_stale(
    piece: str, edited: Sequence[str], named: Named
) -> Callable[[Collection[str]], str]:
    """What says the way past a picture stale under the moved lock, from every output stale:
    the line that names them all (DEC-019 point 4)."""

    def way(stale: Collection[str]) -> str:
        line = named.line(piece, edited, sorted({*stale, *named.use_stale}))
        return (
            f"This run runs no program, and a program reads under the lock the piece holds. Name "
            f"each to use it as it is, and make it again once the lock has moved: `{line}`"
        )

    return way


def _after_alone(export: exports.Planned) -> list[str]:
    """Each file of the copy `export` writes, by its path from the repository's root, where no
    file stands now."""
    piece, copy = export.piece, export.copy
    assert copy is not None
    paths = (current_copy.rooted(piece, path) for path in copy.entry["files"])
    return [path for path in paths if not (piece.root / path).is_file()]


def _none_stood(export: exports.Planned, alone: Sequence[str]) -> bool:
    """Whether no file of a copy stood before the run: not at a path it writes, and not where
    the last copy left one behind."""
    copy = export.copy
    assert copy is not None
    return len(alone) == len(copy.entry["files"]) and not export.left_behind


def write(planned: Planned, before: Side, after: Side, change: Change) -> str:
    """Add a proposal to `change` and take it: the drawings, then `piece.yaml`, the findings
    record and the export. A drawing that cannot be kept stops nothing, and its fault is what
    this returns, empty where it was kept. Raises WriteFailed where a write fails, every file
    then as it was before the run, or named."""
    piece = planned.export.piece
    why = ""
    try:
        before_after.keep(change, piece.name, before, after)
    except pl.Refused as exc:
        why = str(exc)
    if planned.piece_file is not None:
        change.write(piece.folder / pl.PIECE_FILE, planned.piece_file)
    change.write(piece.folder / pl.FINDINGS_FILE, planned.findings)
    exports.add(planned.export, change)
    change.commit()
    return why


def report(planned: Planned) -> Iterator[str]:
    """What a proposal holds, a line each: the lock, each input named, what the export writes,
    the findings record, and each file that shows only its after."""
    export = planned.export
    piece = export.piece
    moved = "lock" if planned.piece_file is not None else "lock as it stands"
    yield f"{moved}: {looks.versions_said(planned.move.look.after)}"
    for edit in planned.edits:
        yield f"edit named: {edit.said}"
    for name in planned.not_edited:
        yield f"named, and not changed since the copy: `{name}`"
    yield from exports.report(export)
    yield f"findings: kept in {piece.file(pl.FINDINGS_FILE)}"
    if planned.none_stood:
        yield "no file of the current copy stood, so the change shows only an after"
    else:
        yield from (
            f"no file stood at {path}, so the change shows only its after"
            for path in planned.after_alone
        )


def failing(root: Path, name: str) -> Iterator[str]:
    """Each finding that fails in the check of the piece `name` as the run left it, a line
    each. It reads the lock as moved, so it names what holds the landing (DEC-019 point 7)."""
    for finding, level in checks.check(root, only=name).judged:
        if level == FAILS:
            yield f"{FAILS}: {checks.place(finding)}: {checks.said(finding)}"
