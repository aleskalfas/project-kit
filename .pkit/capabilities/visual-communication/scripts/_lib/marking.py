"""Marking a piece final: the version handed out named, its lock put back, and its files kept
with the piece (visual-communication DEC-017 points 1, 2 and 8).

- **It takes the version named, whatever changed since.** A file that went out is a fact, so
  no change of the piece stops the run, and the piece is read from its own file alone
  (`pipeline.read_piece_file`). What refuses is what keeps the version from being read: a
  fingerprint that gives no lock, or a file of the version that is missing or differs.
- **It puts back the lock,** read from the version's fingerprint (`current_copy.version_lock`),
  whatever lock the piece holds, a published piece's included, and only the lock.
- **It says what else changed** (`Planned.changed`), reading "changed" as an export's reading
  does (DEC-016 point 1), with the lock put back and the state as it stood, so neither of the
  run's own writes counts. A version made before that reading read a file whole, and the run
  says which (`Planned.read_whole`). It names each number or date the version let through,
  and stops on none (`Planned.let_through`): nothing mends a file that went out.
- **A lock that no longer holds refuses nothing.** The run says what the check will find of
  it (`Planned.lock_faults`), read as the check reads a final piece's, and goes on.
- **One version, whole.** Every file of the version moves from the clone's local folder into
  the piece's `handed-out/`, under the name it carries. One field of the record of exports
  names the version, at the record's end, so two branches that mark two versions conflict on
  merge. A piece with a version handed out refuses a second.
- **A current copy stays.** The run says so where the version named did not write it.
- **Refused before any write.** Everything that can refuse is checked by `plan`.
- **Written as one change** (`write`): the files, then `piece.yaml`, then the record. Where a
  write fails, every file is put back as it was before the run, or each it could not put
  back is named. In the piece's own file only `state` and `lock` change, and in the record
  only its last line is new.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from _lib import checks, copies, current_copy, exports, fingerprint, records
from _lib import pipeline as pl
from _lib.files import Change
from _lib.fingerprint import HANDED_OUT
from _lib.libraries import Held
from _lib.reading import sha256


@dataclass(frozen=True)
class Planned:
    """A mark checked and not yet written: the version's number and its lock; the name of each
    of its files; the bytes of `piece.yaml`, None where it stays as it is, and of the record of
    exports; each input that still does not verify; each file the version read whole, of those
    an export now reads in part; what no longer holds of the lock, a line each; the version
    that wrote the piece's current copy, where another did; and each number or date the
    version let through, in words."""

    piece: pl.Piece
    number: int
    lock: dict[str, str]
    files: tuple[str, ...]
    piece_file: bytes | None
    record: bytes
    changed: tuple[str, ...]
    read_whole: tuple[str, ...]
    lock_faults: tuple[str, ...]
    copy_writer: int | None
    let_through: tuple[str, ...]


def plan(piece: pl.Piece, held: Held, number: int) -> Planned:
    """The mark of the version `number` of `piece`, read from its own file alone, every file it
    writes checked. Raises Refused, naming what stops it, so `write` refuses nothing."""
    record = _record(piece)
    versions = exports.recorded_versions(piece, record)
    version = _version(piece, versions, number)
    lock = _lock(piece, version)
    files = _files(piece, version)
    folder = piece.folder / HANDED_OUT
    if folder.exists() or folder.is_symlink():
        raise pl.Refused(
            f"{piece.file(HANDED_OUT)} lies in the piece's folder, though no version is handed "
            f"out, and the version's files go there: move it"
        )
    before = (piece.folder / pl.PIECE_FILE).read_bytes()
    locked = pl.locked(piece, lock) or before
    marked = _marked(piece, locked)
    planned = Planned(
        piece,
        number,
        lock,
        files,
        None if marked == before else marked,
        _record_with(piece, number),
        tuple(_changed(piece, held, lock, version["fingerprint"], locked)),
        tuple(fingerprint.read_whole(version["fingerprint"])),
        tuple(_lock_faults(piece, held, lock)),
        _copy_writer(piece, record, number),
        tuple(current_copy.let_through_said(each) for each in current_copy.let_through(version)),
    )
    _writable(planned)
    return planned


def _local(piece: pl.Piece) -> Path:
    """The clone's local folder a version's files lie in."""
    return piece.root / exports.FOLDER / piece.name


def write(planned: Planned, change: Change) -> None:
    """Write a planned mark as the next steps of `change`, and take it: the version's files
    into their folder, then each removed from the clone's local folder, then `piece.yaml`, then
    the record. Raises WriteFailed where a write fails, every file then as it was before the
    run, or named."""
    piece = planned.piece
    local = {name: _local(piece) / name for name in planned.files}
    change.add_folder(piece.folder / HANDED_OUT, local)
    for path in local.values():
        change.remove(path)
    if planned.piece_file is not None:
        change.write(piece.folder / pl.PIECE_FILE, planned.piece_file)
    change.write(piece.folder / pl.EXPORTS_FILE, planned.record)
    change.commit()


def report(planned: Planned) -> list[str]:
    """What a mark says, a line each: each file kept, the lock put back, what else changed,
    each text let through, what no longer holds of the lock, the current copy, and the version
    recorded."""
    piece, number = planned.piece, planned.number
    locked = ", ".join(f"{library} {planned.lock[library]}" for library in sorted(planned.lock))
    said = [f"handed out: {piece.file(f'{HANDED_OUT}/{name}')}" for name in planned.files]
    said.append(f"lock of version {number} put back: {locked}")
    said.extend(f"changed since version {number}: {change}" for change in planned.changed)
    said.extend(
        f"read whole: version {number} read `{file}` whole, made before an export left fields "
        f"out of it, so a pin or a change of state reads as a change"
        for file in planned.read_whole
    )
    said.extend(
        f"let through: version {number} shows {text}, which does not fit, and no check judges "
        f"it once the piece is final"
        for text in planned.let_through
    )
    said.extend(planned.lock_faults)
    if planned.copy_writer is not None:
        said.append(
            f"current copy: version {planned.copy_writer} wrote it, not version {number}. It "
            f"stays, a page goes on showing it, and no export mends it"
        )
    said.append(
        f"final: `{piece.name}`, version {number} named as handed out in "
        f"{piece.file(pl.EXPORTS_FILE)}: commit the piece's folder, which holds its files"
    )
    return said


def _record(piece: pl.Piece) -> dict[str, Any]:
    """What the piece's `exports.yaml` holds, nothing where it is absent. Raises Refused where
    it cannot be read, or names a version handed out already: a piece holds one lock."""
    try:
        kept = copies.handed_out(piece.folder)
    except records.RecordError as exc:
        raise pl.Refused(f"{exc}: mend it, then name the version") from exc
    if kept is not None:
        raise pl.Refused(
            f"{piece.file(pl.EXPORTS_FILE)} names version {kept} as handed out, and a piece holds "
            f"one: for new work, run {copies.take_up_command(piece.name)}, which takes it up "
            f"again as a new draft. A mark made in error is undone by reverting its change"
        )
    return exports.recorded(piece)


def _version(
    piece: pl.Piece, versions: Sequence[Mapping[str, Any]], number: int
) -> Mapping[str, Any]:
    """What the record keeps of the version `number`. Raises Refused where it keeps none."""
    version = next((each for each in versions if each["version"] == number), None)
    if version is None:
        held = ", ".join(str(each["version"]) for each in versions) or "none"
        raise pl.Refused(
            f"{piece.file(pl.EXPORTS_FILE)} records no version {number}: it holds {held}"
        )
    return version


def _lock(piece: pl.Piece, version: Mapping[str, Any]) -> dict[str, str]:
    """The lock `version` was made under. Raises Refused where its fingerprint is missing, or
    no longer matches its own inputs, naming the record."""
    try:
        return current_copy.version_lock(version)
    except fingerprint.UnreadableFingerprint as exc:
        raise pl.Refused(
            f"{piece.file(pl.EXPORTS_FILE)} gives no lock of version {version['version']}: {exc}. "
            f"Mend it, or name another version"
        ) from exc


def _files(piece: pl.Piece, version: Mapping[str, Any]) -> tuple[str, ...]:
    """The name of each file of `version`. Raises Refused, naming each, where a file is missing
    from the clone's local folder, or its hash differs from the record's: a version is marked
    where its files lie as they were made."""
    held = version.get("files")
    if not isinstance(held, Mapping) or not held:
        raise pl.Refused(
            f"{piece.file(pl.EXPORTS_FILE)} names no file of version {version['version']}"
        )
    folder = _local(piece)
    faults = []
    for name, hashed in held.items():
        shown = f"{exports.FOLDER}/{piece.name}/{name}"
        if "/" in name or name in (".", ".."):
            faults.append(f"`{name}` names no file of that folder")
        elif not (folder / name).is_file():
            faults.append(f"{shown} is missing")
        elif sha256((folder / name).read_bytes()) != hashed:
            faults.append(f"{shown} differs from the hash the record keeps")
    if faults:
        raise pl.Refused(
            f"version {version['version']} of `{piece.name}` cannot be marked, since each of its "
            f"files must lie in this clone as it was made: {'; '.join(faults)}"
        )
    return tuple(held)


def _marked(piece: pl.Piece, locked: bytes) -> bytes:
    """The bytes of `piece.yaml`, `locked` once its lock is put back, with its state final.
    Raises Refused where its text cannot take that state."""
    if piece.state == copies.FINAL:
        return locked
    try:
        text = records.with_value(locked.decode("utf-8"), [], "state", copies.FINAL, each="field")
    except records.RecordError as exc:
        raise pl.Refused(
            f"{piece.file(pl.PIECE_FILE)} cannot take the state `{copies.FINAL}` as text: {exc}"
        ) from exc
    return text.encode("utf-8")


def _record_with(piece: pl.Piece, number: int) -> bytes:
    """The bytes of `exports.yaml` once its last line names the version handed out. Raises
    Refused where its text cannot take it."""
    text = (piece.folder / pl.EXPORTS_FILE).read_bytes().decode("utf-8")
    try:
        marked = records.with_entry(text, [], copies.HANDED_OUT_FIELD, number, each="field")
    except records.RecordError as exc:
        raise pl.Refused(
            f"{piece.file(pl.EXPORTS_FILE)} cannot name the version handed out as text: {exc}"
        ) from exc
    return marked.encode("utf-8")


def _changed(
    piece: pl.Piece, held: Held, lock: Mapping[str, str], kept: Mapping[str, Any], locked: bytes
) -> list[str]:
    """Each input of the fingerprint `kept` that does not verify with the lock put back and
    `piece.yaml` as `locked` holds it, its state as it stood: a version that read the whole
    file read that too."""
    fonts = pl.recorded_fonts(piece.root, piece.location, kept)
    sources = pl.findings_key_sources(piece.root, held, piece, lock, fonts)
    written = {piece.folder / pl.PIECE_FILE: locked}
    return fingerprint.verify(kept, "export", **sources, written=written)


def _lock_faults(piece: pl.Piece, held: Held, lock: Mapping[str, str]) -> list[str]:
    """What the check will find of the lock put back on the piece once it is final, a line
    each (DEC-017 point 2)."""
    data = {**piece.data, "lock": dict(lock), "state": copies.FINAL}
    marked = pl.Piece(piece.root, piece.location, piece.name, data, {})
    found = [*checks.lock_findings(held, marked), *checks.changed_versions(held, lock)]
    return [f"{each.level}: {checks.place(each)}: {checks.said(each)}" for each in found]


def _copy_writer(piece: pl.Piece, record: Mapping[str, Any], number: int) -> int | None:
    """The version that wrote the piece's own current copy, where another than `number` did."""
    copy = current_copy.own(piece, record)
    return None if copy is None or copy["version"] == number else copy["version"]


def _writable(planned: Planned) -> None:
    """Raise Refused where a planned mark could not be written: a file it writes or removes is
    reached through a link."""
    piece = planned.piece
    for path in (
        *(piece.folder / HANDED_OUT / name for name in planned.files),
        *(_local(piece) / name for name in planned.files),
        piece.folder / pl.PIECE_FILE,
        piece.folder / pl.EXPORTS_FILE,
    ):
        pl.writable(piece.root, path)
