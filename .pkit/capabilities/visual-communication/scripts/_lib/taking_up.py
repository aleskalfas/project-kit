"""Taking a final piece up again: a new piece copied from it, a draft with its lock pinned, so
it draws as the piece it copies until a person moves that lock (visual-communication DEC-003
point 8, DEC-017 points 1, 3, 5 and 8).

- **From a piece with a version handed out.** No state leads out of final, and a copy is the
  way back (DEC-017 point 5). A piece set final by hand names no version handed out, so it is
  refused: marking it final names one (`marking`).
- **Under a name no piece holds,** of the name shape, where nothing lies in the location's
  `pieces/` under it yet.
- **Copied whole, but for its past** (`PAST`): its record of exports, its findings record, and
  the folders of the files handed out and of a current copy. A renderer that draws into a
  lasting medium keeps a record of what it last drew (DEC-005 point 11). No such renderer
  ships, so no piece holds one yet, and the change that builds one adds it here. Every other
  file of the folder, as git sees it, is copied as it lies: the content, the brief, which no
  command changes (DEC-029 point 4), the local components, and each produced picture with its
  record. A fingerprint names a piece's file by its path
  within the piece's folder, so the copy makes nothing stale.
- **The new piece's own file** (`_piece_file`): the final piece's, with `state: draft`,
  `pinned: true` and the lock of the version handed out, read from its fingerprint as marking
  final reads it (`current_copy.version_lock`), and without `copy-place`. A draft writes no
  current copy, and kept, the place would have two pieces claim one path. Every other byte is
  kept, such as who the piece is for.
- **Later words.** Only the lock comes back (DEC-017 point 1). Where the sources changed since
  the version handed out, the copy holds the later words, and the run names each change, read
  as an edit since a version is (`fingerprint.edits`) with the copy's own file. An input it
  cannot read stops nothing: the run says so.
- **It only reads the final piece** (DEC-017 point 3), whose folder stays as it was.
- **Refused before any write** (`plan`): a piece with no version handed out, a name taken or
  not a piece's name, a version whose lock cannot be read, and a file reached through a link,
  whether one it copies or one it writes.
- **Written as one change** (`write`): the new folder is staged whole beside its place, then
  moved in at once, so a write that fails leaves no part of it.
"""

from __future__ import annotations

import os
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from _lib import copies, current_copy, exports, fingerprint, location, records
from _lib import pipeline as pl
from _lib.files import Change, FileError, refuse_links
from _lib.fingerprint import COPY_PLACE, CURRENT_COPY, HANDED_OUT

#: What only the final piece's past holds, at the top of its folder, which a copy leaves out
#: (DEC-017 point 8): its record of exports, its findings record, and the folders of the
#: files handed out and of a current copy.
PAST = (pl.EXPORTS_FILE, pl.FINDINGS_FILE, HANDED_OUT, CURRENT_COPY)


@dataclass(frozen=True)
class Planned:
    """A copy checked and not yet written: the final piece, the new piece's name, the number
    of the version handed out and its lock; each file of the new folder by its path within
    it, a copy of the final piece's file or the bytes of its own `piece.yaml`; and what
    changed since that version, a line each."""

    piece: pl.Piece
    name: str
    number: int
    lock: dict[str, str]
    files: dict[str, Path | bytes]
    changed: tuple[str, ...]

    @property
    def rel(self) -> str:
        """The new piece's folder, relative to the project root."""
        return f"{self.piece.location}/{pl.PIECES}/{self.name}"

    @property
    def folder(self) -> Path:
        return self.piece.root / self.rel


def plan(piece: pl.Piece, name: str) -> Planned:
    """The copy of `piece`, read from its own file alone, as the new piece `name`, every file
    it reads and writes checked. Raises Refused, naming what stops it, so `write` refuses
    nothing."""
    target = pl.new_piece_folder(piece.root, piece.location, name)
    number = _handed_out(piece)
    version = _version(piece, number)
    lock = _lock(piece, version)
    copied = _copied(piece)
    piece_file = _piece_file(piece, lock)
    pl.writable(piece.root, target / pl.PIECE_FILE)
    written: dict[str, Path | bytes] = dict(copied)
    written[pl.PIECE_FILE] = piece_file
    changed = _changed(piece, version, copied.values(), piece_file)
    return Planned(piece, name, number, lock, written, tuple(changed))


def write(planned: Planned, change: Change) -> None:
    """Write a planned copy as the next step of `change`, and take it: the new folder, whole.
    Raises WriteFailed where a write fails, every file then as it was before the run, or
    named."""
    change.add_folder(planned.folder, planned.files)
    change.commit()


def report(planned: Planned) -> list[str]:
    """What a copy says, a line each: the lock it pinned, what changed since the version
    handed out, and the new piece."""
    piece, number = planned.piece, planned.number
    locked = ", ".join(f"{library} {planned.lock[library]}" for library in sorted(planned.lock))
    return [
        f"lock of version {number} pinned: {locked}",
        *planned.changed,
        f"taken up: `{planned.name}`, a draft copied from `{piece.name}` with the lock of version "
        f"{number} pinned, in {planned.rel}: commit its folder. `{piece.name}` stays as it was",
    ]


def _handed_out(piece: pl.Piece) -> int:
    """The number of the version handed out. Raises Refused where the record of exports cannot
    be read, or names none."""
    try:
        number = copies.handed_out(piece.folder)
    except records.RecordError as exc:
        raise pl.Refused(f"{exc}: mend it, then take the piece up") from exc
    if number is not None:
        return number
    if piece.state == copies.FINAL:
        raise pl.Refused(
            f"the piece `{piece.name}` is final, and {piece.file(pl.EXPORTS_FILE)} names no "
            f"version handed out: run `pkit visual mark-final {piece.name} <version>` first, "
            f"which names it"
        )
    raise pl.Refused(
        f"the piece `{piece.name}` has no version handed out, and only a final piece is taken up "
        f"again"
    )


def _version(piece: pl.Piece, number: int) -> Mapping[str, Any]:
    """What the record of exports keeps of the version handed out. Raises Refused where it
    keeps none."""
    versions = exports.recorded_versions(piece, exports.recorded(piece))
    kept = next((each for each in versions if each["version"] == number), None)
    if kept is None:
        raise pl.Refused(
            f"{piece.file(pl.EXPORTS_FILE)} hands out version {number}, and keeps no such one: "
            f"restore what it kept of it from the repository's history"
        )
    return kept


def _lock(piece: pl.Piece, version: Mapping[str, Any]) -> dict[str, str]:
    """The lock the version handed out was made under. Raises Refused where its fingerprint
    gives none, naming the record."""
    try:
        return current_copy.version_lock(version)
    except fingerprint.UnreadableFingerprint as exc:
        raise pl.Refused(
            f"{piece.file(pl.EXPORTS_FILE)} gives no lock of version {version['version']}, handed "
            f"out: {exc}. Restore what it kept of it from the repository's history"
        ) from exc


def _past(rel: str) -> bool:
    """Whether the path `rel`, within a piece's folder, lies in what only its past holds."""
    return rel.split("/", 1)[0] in PAST


def _copied(piece: pl.Piece) -> dict[str, Path]:
    """Each file of the final piece's folder the new piece takes, by its path within the
    folder: every file git sees there, but for its past. Raises Refused where one of them is
    reached through a link."""
    _refuse_links(piece)
    prefix = f"{piece.rel}/"
    copied = {}
    for rel in location.files(piece.root, piece.rel):
        inner = rel.removeprefix(prefix)
        if not _past(inner):
            copied[inner] = piece.root / rel
    return copied


def _refuse_links(piece: pl.Piece) -> None:
    """Raise Refused where a file the copy takes is reached through a link: the piece's folder,
    or a folder above it, is one, or a link lies in the folder, outside its past. A link git
    ignores is no part of the piece, so it refuses nothing."""
    try:
        refuse_links(piece.root, piece.folder)
    except FileError as exc:
        raise pl.Refused(str(exc)) from exc
    found = []
    for current, folders, names in os.walk(piece.folder):
        for each in (*folders, *names):
            path = Path(current) / each
            if path.is_symlink() and not _past(path.relative_to(piece.folder).as_posix()):
                found.append(path.relative_to(piece.root).as_posix())
    ignored = set(location.ignored(piece.root, found)) if found else set()
    links = [rel for rel in found if rel not in ignored]
    if links:
        raise pl.Refused(
            f"the copy would reach a file through the link "
            f"{', '.join(sorted(links))}: put the file or folder itself in the link's place"
        )


def _piece_file(piece: pl.Piece, lock: Mapping[str, str]) -> bytes:
    """The bytes of the new piece's `piece.yaml`: the final piece's, a draft with its lock
    pinned to `lock`, and no place for a current copy, every other byte kept. Raises Refused
    where its text cannot take them."""
    text = (piece.folder / pl.PIECE_FILE).read_bytes().decode("utf-8")
    try:
        text = _set(text, piece.data, "state", copies.DRAFT)
        text = _set(text, piece.data, "pinned", True)
        if COPY_PLACE in piece.data:
            text = records.without_entry(text, COPY_PLACE)
    except records.RecordError as exc:
        raise pl.Refused(
            f"{piece.file(pl.PIECE_FILE)} cannot be copied as a pinned draft as text: {exc}"
        ) from exc
    return pl.lock_text(text, lock).encode("utf-8")


def _set(text: str, data: Mapping[str, Any], key: str, value: Any) -> str:
    """`text` with the top-level `key` written as `value`: in its place where `data`, what the
    text holds, has it, else at the end."""
    if key in data:
        return records.with_value(text, [], key, value, each="field")
    return records.with_entry(text, [], key, value, each="field")


def _changed(
    piece: pl.Piece, version: Mapping[str, Any], copied: Iterable[Path], piece_file: bytes
) -> list[str]:
    """Each input of the piece's own that differs between the version handed out and the
    copy, a line each, read with the copy's own `piece.yaml`. An input that cannot be read is
    said, and stops nothing."""
    kept = version["fingerprint"]
    number = version["version"]
    try:
        found = fingerprint.edits(
            kept,
            piece=piece.folder,
            files=list(copied),
            fonts=pl.recorded_fonts(piece.root, piece.location, kept),
            written={piece.folder / pl.PIECE_FILE: piece_file},
        )
    except fingerprint.FingerprintError as exc:
        return [f"not compared with version {number}: {exc}"]
    return [f"changed since version {number}: {edit.said}" for edit in found]
