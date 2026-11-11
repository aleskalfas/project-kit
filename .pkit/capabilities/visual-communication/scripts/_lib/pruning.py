"""Pruning the library folder: each library version that lies behind is removed, with its
entry in the list of libraries, once a person has seen the list (visual-communication DEC-003
point 4, DEC-019 points 9 to 11).

- **The locks it reads** (`plan`): each piece's, in any state, and each declaration's of
  written code, through `copies.locks`; and, of each piece, the lock of the version that
  wrote its own current copy, read from that version's fingerprint
  (`current_copy.written_lock`), since the gate reads it and writing it back is a way past
  (DEC-017 point 5). The versions each names stay.
- **A lock that moves** is a draft's, pinned or not, a published piece's and written code's.
  A final piece's never moves (DEC-017 point 3), and a kept export's is only read, so each
  keeps what it names and no more.
- **A version lies behind** (`why_kept`) where nothing keeps it:
  - a lock names it;
  - it is the project's own, not yet released, and holds work that lies nowhere else;
  - a lock that moves names its library below it in its major, and may still move to it;
  - nothing newer of its library stands, so it is the library's last version;
  - no newer version of its major stands that the installed capability reads, which a
    first lock and a `builds-on` of that major take (DEC-003 point 8, DEC-010 point 9);
  - it is released, and no newer release of its major stands, which a release of the
    library is compared with (DEC-003 point 7).

  A version the list does not name stays too, since the run cannot tell what it holds.
- **What it reads no further.** A version only a kept export's fingerprint names goes, and
  the run names each such export, since marking it final leaves a finding until the version
  is back (DEC-017 point 2). A kept export whose fingerprint gives no lock is named too. It
  reads no piece with no lock yet: its first lock takes the newest of each major, which stay.
- **What stops it** (`plan`), before anything is written: a list it cannot read, or whose
  text cannot lose an entry; a lock it cannot read, which may name any version; a record of
  exports it cannot read, since it then cannot tell whether a lock moves; a fingerprint it
  cannot read of the version that wrote a current copy, since that lock counts too; and a
  folder or the list reached through a link.
- **The working tree alone.** It reads the files as git lists them, and removes from the
  working tree, staging nothing. It takes no version by name.
- **Written as one change** (`write`): each version's folder removed, then the list written,
  every other byte of it kept. A removal that fails leaves each file as it was, or names each
  it could not put back.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from _lib import copies, current_copy, fingerprint, records
from _lib import pipeline as pl
from _lib.files import Change, FileError, read_bound, without_binding
from _lib.libraries import Held, LibraryError, Version
from _lib.reading import ReadError

#: The kind of source the list gives a library of the project's own (DEC-003 point 4).
PROJECT_SOURCE = "project"


@dataclass(frozen=True)
class Holder:
    """A lock the run reads: who holds it, in words, what it does with a version it names,
    the versions it names by library, and whether it moves."""

    said: str
    verb: str
    lock: Mapping[str, str]
    moves: bool


@dataclass(frozen=True)
class Kept:
    """An export a record keeps, other than the version that wrote a current copy: its piece,
    its number, and the lock read from its fingerprint, or None and why none can be read."""

    piece: str
    number: int
    lock: Mapping[str, str] | None
    why: str = ""


@dataclass(frozen=True)
class Removed:
    """A version that lies behind: its library, its number, its folder, and the newer version
    of its major that serves in its place."""

    name: str
    version: Version
    folder: Path
    serving: Version

    @property
    def label(self) -> str:
        return f"{self.name}@{self.version}"


@dataclass(frozen=True)
class Spared:
    """A version the run keeps, and why, in words."""

    label: str
    why: str


@dataclass(frozen=True)
class Planned:
    """A run, read and checked, not yet written: each version to remove and each spared, by
    library and the newest first; each kept export; and the list's path, with its text once
    it loses each entry, None where it loses none."""

    root: Path
    removed: tuple[Removed, ...]
    spared: tuple[Spared, ...]
    kept: tuple[Kept, ...]
    list_file: Path
    list_text: str | None


def plan(root: Path, location: str, held: Held | None = None) -> Planned:
    """The run over the location's library folder, `held` unless given: every lock read, each
    version judged, and the list's text worked out. Raises Refused, naming the file, where
    anything stops it, so `write` refuses nothing."""
    held = Held(root, location) if held is None else held
    try:
        _ = held.listed
    except LibraryError as exc:
        raise pl.Refused(
            f"the list of libraries cannot be read: {exc}. The run cannot tell which versions "
            f"are released, so it removes nothing: mend the list"
        ) from exc
    holders, kept = _read(root, location, held)
    removed: list[Removed] = []
    spared: list[Spared] = []
    for name in held.names():
        for version in held.versions(name):
            label = f"{name}@{version}"
            why = why_kept(held, name, version, holders)
            if why:
                spared.append(Spared(label, why))
                continue
            folder = held.folders[name][version]
            pl.writable(root, folder)
            removed.append(Removed(name, version, folder, _serving(held, name, version)))
    list_file = root / held.list_path
    text = _list_text(root, list_file, removed) if removed else None
    return Planned(root, tuple(removed), tuple(spared), tuple(kept), list_file, text)


def write(planned: Planned, change: Change) -> None:
    """Write a planned run as the next steps of `change`, and take it: each version's folder
    removed, then the list. Raises WriteFailed where a removal or the write fails, every file
    then as it was before the run, or named."""
    for each in planned.removed:
        change.remove_folder(each.folder)
    if planned.list_text is not None:
        change.write(planned.list_file, planned.list_text.encode("utf-8"))
    change.commit()


def report(planned: Planned) -> list[str]:
    """The run's list, a line each: each version it removes, each it spares with why, each
    kept export made under a version it removes, and each kept export whose lock it cannot
    read."""
    lines: list[str] = []
    if planned.removed:
        lines.append("lies behind, to remove with its entry in the list:")
        lines += [
            f"  {each.label}: {_rel(planned.root, each.folder)}; {each.name}@{each.serving} "
            f"serves in its place"
            for each in planned.removed
        ]
    if planned.spared:
        lines.append("spared:")
        lines += [f"  {each.label}: {each.why}" for each in planned.spared]
    under = list(_under(planned))
    if under:
        lines.append(
            "kept exports made under a version to remove, which marking one final leaves a "
            "finding on until that version is back:"
        )
        lines += [
            f"  version {kept.number} of `{kept.piece}`, made under {', '.join(labels)}"
            for kept, labels in under
        ]
    unread = [kept for kept in planned.kept if kept.lock is None]
    if unread:
        lines.append(
            "kept exports whose fingerprint gives no lock, so the run cannot say what they were "
            "made under:"
        )
        lines += [f"  version {kept.number} of `{kept.piece}`: {kept.why}" for kept in unread]
    return lines


def removed_lines(planned: Planned) -> list[str]:
    """What a run says once it has removed each version, a line each."""
    shown = _rel(planned.root, planned.list_file)
    return [
        f"removed {each.label}: {_rel(planned.root, each.folder)}, and its entry in {shown}"
        for each in planned.removed
    ]


def why_kept(held: Held, name: str, version: Version, holders: Sequence[Holder]) -> str:
    """Why the run keeps a version the location holds, in words; empty where it lies behind
    (DEC-019 point 9). `holders` are the locks the run read."""
    if not _listed(held, name, version):
        return "the list does not name it, so the run cannot tell what it holds"
    named = [
        f"{each.said} {each.verb} it" for each in holders if each.lock.get(name) == str(version)
    ]
    if named:
        return "; ".join(named)
    released = held.released(name, version)
    if held.source(name) == PROJECT_SOURCE and not released:
        return "it is the project's own, not yet released, and holds work that lies nowhere else"
    below = [
        f"{each.said} locks {name}@{locked}, below it in its major, and may still move to it"
        for each in holders
        if each.moves
        and (locked := _parsed(each.lock.get(name))) is not None
        and locked.major == version.major
        and locked < version
    ]
    if below:
        return "; ".join(below)
    newer = [each for each in held.versions(name) if each > version]
    if not newer:
        return f"it is the last version of `{name}`: nothing newer stands"
    serving = _readable_newer(held, name, version)
    if not serving:
        builders = _building_on(held, name, version.major)
        built = f", and `builds-on` names that major in {', '.join(builders)}" if builders else ""
        return (
            f"it is the newest version of `{name}` {version.major} that the installed capability "
            f"reads, which a first lock takes{built}"
        )
    if released and not any(held.released(name, each) for each in serving):
        return (
            f"it is the newest release of `{name}` {version.major}, which the library's next "
            f"release is compared with"
        )
    return ""


# --- reading the locks --------------------------------------------------------------------------


def _read(root: Path, location: str, held: Held) -> tuple[list[Holder], list[Kept]]:
    """Each lock the run reads, and each kept export. Raises Refused where a lock, a record of
    exports or the fingerprint of the version that wrote a current copy cannot be read."""
    found: list[copies.Lock] = []
    # Each call holds the entry of one library to a version, so every library held is read.
    for name in held.names():
        found = copies.locks(root, location, name)
        unread = next((lock for lock in found if lock.versions is None), None)
        if unread is not None:
            raise pl.Refused(
                f"the lock of {unread.file} cannot be read: {unread.why}. It may name any "
                f"version, so the run removes nothing: mend it"
            )
    holders: list[Holder] = []
    kept: list[Kept] = []
    for lock in found:
        assert lock.versions is not None
        if lock.kind == copies.DECLARATION:
            holders.append(Holder(lock.described, "locks", lock.versions, moves=True))
            continue
        piece = _piece(root, location, lock)
        record = _record(piece)
        versions = _versions(piece, record)
        holders.append(Holder(lock.described, "locks", lock.versions, moves=not piece.final))
        number = None
        writer = _writer(piece, record, versions)
        if writer is not None:
            number, written = writer
            said = f"version {number} of `{piece.name}`, which wrote its current copy,"
            holders.append(Holder(said, "was made under", written, moves=False))
        kept += [_kept(piece.name, each) for each in versions if each["version"] != number]
    return holders, kept


def _piece(root: Path, location: str, lock: copies.Lock) -> pl.Piece:
    """The piece whose lock `lock` is, as its own file gives it, with no contents read."""
    try:
        data = without_binding(read_bound(root / lock.file, "piece"))
    except (ReadError, FileError) as exc:
        raise pl.Refused(f"the lock of {lock.file} cannot be read: {exc}") from exc
    return pl.Piece(root, location, lock.name, data, {})


def _record(piece: pl.Piece) -> Mapping[str, Any]:
    """What the piece's record of exports holds, nothing where it has none. Raises Refused,
    naming it, where it cannot be read, or names no version handed out as its field asks."""
    path = piece.folder / pl.EXPORTS_FILE
    try:
        copies.handed_out(piece.folder)
        return records.read(path, "exports") if path.exists() or path.is_symlink() else {}
    except records.RecordError as exc:
        raise _unread(piece, str(exc).removeprefix(f"{path}: ")) from exc


def _versions(piece: pl.Piece, record: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """The versions the record keeps. Raises Refused where it keeps no list of them."""
    versions = record.get("versions", [])
    if not isinstance(versions, list) or not all(
        isinstance(each, Mapping) and isinstance(each.get("version"), int) for each in versions
    ):
        raise _unread(piece, "it keeps no list of numbered versions")
    return versions


def _writer(
    piece: pl.Piece, record: Mapping[str, Any], versions: Sequence[Mapping[str, Any]]
) -> tuple[int, dict[str, str]] | None:
    """The number of the version that wrote the piece's own current copy, and its lock; None
    where the record names no such copy. Raises Refused, naming the record, where the entry
    or that version's fingerprint cannot be read."""
    try:
        entry = current_copy.own(piece, record)
    except pl.Refused as exc:
        why = f"its `{current_copy.FIELD}` names no piece, version and files as its schema asks"
        raise _unread(piece, why) from exc
    if entry is None:
        return None
    number = entry["version"]
    try:
        return number, current_copy.written_lock(entry, versions)
    except fingerprint.UnreadableFingerprint as exc:
        raise pl.Refused(
            f"{piece.file(pl.EXPORTS_FILE)} gives no lock of version {number}, which wrote the "
            f"current copy of `{piece.name}`: {exc}. That lock keeps what it names, so the run "
            f"removes nothing: restore the record as version control last held it"
        ) from exc


def _kept(piece: str, version: Mapping[str, Any]) -> Kept:
    """A kept export, with the lock its fingerprint gives, or why it gives none."""
    try:
        return Kept(piece, version["version"], current_copy.version_lock(version))
    except fingerprint.UnreadableFingerprint as exc:
        return Kept(piece, version["version"], None, str(exc))


def _unread(piece: pl.Piece, why: str) -> pl.Refused:
    """The stop on a record of exports the run cannot read, naming it and why."""
    return pl.Refused(
        f"{piece.file(pl.EXPORTS_FILE)} cannot be read: {why}. The run cannot tell whether the "
        f"lock of `{piece.name}` moves, so it removes nothing: mend the record, or restore it "
        f"as version control last held it"
    )


# --- judging a version --------------------------------------------------------------------------


def _listed(held: Held, name: str, version: Version) -> bool:
    """Whether the list names a version."""
    library = (held.listed or {}).get(name)
    versions = library.get("versions") if isinstance(library, Mapping) else None
    return isinstance(versions, Mapping) and str(version) in versions


def _parsed(text: object) -> Version | None:
    """The version `text` spells, or None."""
    try:
        return Version.parse(text)
    except ValueError:
        return None


def _readable_newer(held: Held, name: str, version: Version) -> list[Version]:
    """Each version newer than `version` of its major that the installed capability reads,
    the newest first."""
    return [
        each
        for each in held.versions(name)
        if each.major == version.major and each > version and held.unreadable(name, each) is None
    ]


def _serving(held: Held, name: str, version: Version) -> Version:
    """The newest version that serves in the place of one that lies behind: of its major, read
    by the installed capability, and released where it is."""
    serving = _readable_newer(held, name, version)
    if held.released(name, version):
        serving = [each for each in serving if held.released(name, each)]
    return serving[0]


def _building_on(held: Held, name: str, major: int) -> list[str]:
    """Each version the location holds whose `builds-on` names `name` at `major`, by label."""
    return [
        f"{other}@{version}"
        for other in held.names()
        for version in held.versions(other)
        if held.file_fault(other, version) is None
        and any(
            need.name == name and need.major == major
            for need in held.library(other, version).builds_on
        )
    ]


def _under(planned: Planned) -> list[tuple[Kept, list[str]]]:
    """Each kept export made under a version the run removes, with each such version."""
    gone = {(each.name, str(each.version)) for each in planned.removed}
    found = []
    for kept in planned.kept:
        if kept.lock is None:
            continue
        labels = [f"{name}@{v}" for name, v in sorted(kept.lock.items()) if (name, v) in gone]
        if labels:
            found.append((kept, labels))
    return found


# --- the list -----------------------------------------------------------------------------------


def _list_text(root: Path, list_file: Path, removed: Sequence[Removed]) -> str:
    """The list's text once each version removed has lost its entry, every other byte kept.
    Raises Refused where it cannot be read, or cannot lose an entry as text."""
    shown = _rel(root, list_file)
    pl.writable(root, list_file)
    try:
        text = list_file.read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise pl.Refused(f"{shown} cannot be read: {exc}") from exc
    for each in removed:
        path = ["libraries", each.name, "versions"]
        try:
            text = records.without_entry(text, str(each.version), path, each="version")
        except records.RecordError as exc:
            raise pl.Refused(
                f"{shown} cannot lose the entry of {each.label} as text: {exc}. The run removes "
                f"nothing"
            ) from exc
    return text


def _rel(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()
