"""A project's copies of a library the capability ships, what the command that brings the
library in writes of them, and what the check finds of them (visual-communication DEC-003
point 5, DEC-013 points 5 and 6).

- **What the capability ships under a number** (`under`): its released version of that
  number, from its released place, with the entry the library's record keeps of it; else
  the version being built, where it carries that number, `released: false`. So the version
  being built, while it carries a released number, is that released version (DEC-013
  point 2). The libraries, their released versions and their records are read through the
  capability's reader (`shipped`). A version's files are listed as git lists them, as the
  hash of a released version lists its place's (`shipped.files_of`).
- **The version a run takes** (`plan`): the newest released version, or the released
  version a person names by its number, or the version being built, where the person asks
  for it or none is released.
- **Each copy of the library** that the library folder holds or the list names is brought
  up to date in the same run:
  - **A copy the list marks not released,** of a number the capability ships, is replaced
    whole by what the capability ships under it, and listed released, with its hash, where
    that number is released. It is left as it is where it holds that already, or where a
    lock that moves only on purpose names it, or may (`holding`), unless the person names
    each such piece and declaration in the command. Naming it is the move on purpose: the
    lock keeps its number, and only its copy changes. A person names only a lock that
    locks a copy the run would replace, and one the command can read (`_check_named`).
  - **A released copy** whose files no longer match its hash is restored as released, from
    the capability's released place; one that matches is not written. Where the hash the
    capability records for its version differs from the list's, the run refuses.
  - **The version the run takes,** of a number the location does not hold, is copied beside
    the others.
  - **A copy of a number the installed capability does not ship,** and a version folder the
    list does not name, stay as they are.

  A version the list names whose folder is missing is a copy that no longer holds its
  files: it is brought in as a copy of its kind is, a released one restored, one not
  released replaced, under the same locks.
- **The locks** (`locks`): each piece's, read from its `piece.yaml` alone, its `lock`,
  `pinned` and `state`, so a fault in its content stops nothing; and each declaration's of
  written code. A draft's lock that is not pinned follows its libraries, moving at each
  render, and a final piece's no longer draws, so neither holds a copy (DEC-013 point 5). A
  pinned draft's, a published piece's and written code's move only on purpose (DEC-003
  point 8, DEC-005 point 7). `pinned` is read of a draft alone. A lock the command cannot
  read counts as one that moves only on purpose, and may name any copy of the library.

Every check that can refuse runs in `plan`, before the first write. `write` writes the plan
as one change (`files.Change`): each folder copied, or replaced whole, then the list, every
other byte of it kept.

**What the check finds** of each copy (`compare`) follows what a run would write of it: a
copy not released that is not what the capability ships under its number, and a released
copy whose hash differs from the one the capability records, each ask the project for
attention (DEC-013 point 6).
"""

from __future__ import annotations

from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from _lib import records, shipped
from _lib.files import (
    FORMAT,
    Change,
    FileError,
    binding_problem,
    refuse_links,
    schema_of,
)
from _lib.findings import ATTENTION, PROJECT, Finding
from _lib.libraries import (
    FOLDER,
    LIST,
    LIST_HEADER,
    SHIPPED_SOURCE,
    Held,
    LibraryError,
    Version,
    kind_within,
)
from _lib.location import files as listed_files
from _lib.reading import ReadError, read_yaml
from _lib.root import SHIPPED

#: The folder of the location that holds the pieces, one folder each (`pipeline.PIECES`,
#: not imported: the pipeline measures text, and this module reads only the locks).
PIECES = "pieces"

#: A piece's file that holds its lock.
PIECE_FILE = "piece.yaml"

#: The folder of the location that holds the declarations of written code (`code.FOLDER`).
DECLARATIONS = "code"

#: The states of a piece (DEC-003 point 8).
DRAFT = "draft"
FINAL = "final"
PUBLISHED = "published"
STATES = (DRAFT, FINAL, PUBLISHED)

#: What a published piece needs where it has no lock, since no render moves it.
FIRST_RENDER = "set it back to a draft for its first render"

#: What mends a final piece's lock that holds no version to move from: the lock its version
#: was made under, which is no move of it (DEC-002 point 7, DEC-017 point 1).
WRITE_BACK = "write back the lock of the version handed out, which is no move of it"

#: The kinds of lock, each what a person names one by in the command (`Lock.key`).
PIECE = "piece"
DECLARATION = "declaration"


class CopyRefused(Exception):
    """A run refused before it writes anything: the message says why, and the way out."""


@dataclass(frozen=True)
class Source:
    """What the capability ships under a number: its folder, each of its files relative to
    it, and the entry the list takes for it, `{released: false}`, or the entry the library's
    record keeps, its hash included."""

    name: str
    version: Version
    folder: Path
    files: tuple[str, ...]
    entry: Mapping[str, Any]
    released: shipped.Released | None

    @property
    def label(self) -> str:
        return f"{self.name}@{self.version}"

    @property
    def said(self) -> str:
        """Which version it is, in words."""
        return "the released version" if self.released is not None else "the version being built"


@dataclass(frozen=True)
class Lock:
    """A lock of the location, by the file that holds it: a piece's or a declaration's of
    written code. `versions` is the lock as read, or None where it cannot be read, `why`
    then saying why; `follows` says whether a copy it names is replaced with no person
    naming it, since it moves at each render or, a final piece's, no longer draws; `called`
    is what a piece's state calls it, in words."""

    kind: str
    name: str
    file: str
    follows: bool
    versions: Mapping[str, str] | None
    why: str = ""
    called: str = ""

    @property
    def key(self) -> tuple[str, str]:
        """What a person names it by in the command: its kind and its name."""
        return self.kind, self.name

    def names(self, library: str, version: Version) -> bool:
        """Whether it names the copy of `library` at `version`, or may: a lock that cannot
        be read may name any."""
        return self.versions is None or self.versions.get(library) == str(version)

    @property
    def described(self) -> str:
        """The piece or the declaration, in words."""
        if self.versions is None:
            return f"{self.file}, whose lock cannot be read: {self.why}"
        if self.kind == DECLARATION:
            return f"the declaration `{self.name}` of written code"
        return f"the {self.called} `{self.name}`"


@dataclass(frozen=True)
class Written:
    """A copy the run writes: `copied`, `replaced` or `restored`; what the capability ships
    that it writes; the version folder; what is said of it; and each lock that names it."""

    how: str
    source: Source
    folder: Path
    said: str
    locks: tuple[Lock, ...]


@dataclass(frozen=True)
class Left:
    """A copy the run leaves as it is, why, and each lock that holds it, the person not having
    named it. Where only such locks hold it: what the capability ships, which the run would
    replace it with, and each lock a run names to replace it, those already named included."""

    label: str
    why: str
    locks: tuple[Lock, ...] = ()
    source: Source | None = None
    to_name: tuple[Lock, ...] = ()


@dataclass(frozen=True)
class Plan:
    """A run, checked and not yet written: each copy of the library, newest first, written
    or left; each line the list takes, in words; and the list's path with its text once it
    takes them, None where it takes none."""

    copies: tuple[Written | Left, ...]
    listed: tuple[str, ...]
    list_file: Path
    list_text: str | None


def plan(
    root: Path,
    location: str,
    name: str,
    version: Version | None = None,
    *,
    being_built: bool = False,
    named: Collection[tuple[str, str]] = (),
) -> Plan:
    """The run of the command for the library `name` in `location`: the version it takes,
    the released `version` where one is named, or the version being built where
    `being_built` asks for it; and each copy of the library brought up to date, `named`
    giving each lock the person names, by its `Lock.key`. Raises CopyRefused, before anything
    is written, for a library the capability does not ship, a version it does not ship,
    files it ships that no longer match the hash its record keeps or lack their binding, a
    list that cannot be read or names the library from another source, a hash the list keeps
    that differs from the record's, a folder the list does not name where the version is to
    be copied, a lock named that locks no copy the run would replace, a path reached through
    a link, and a list that cannot take what changes as text."""
    library = _library(name)
    taken = _taken(library, version, being_built)
    held = Held(root, location)
    listed = _listed(held, name)
    found = locks(root, location, name)
    shown = f"{location}/{LIST}"
    copies: list[Written | Left] = []
    entries: list[tuple[Version, Mapping[str, Any], bool]] = []
    for number in sorted({*held.versions(name), *listed, taken.version}, reverse=True):
        label = f"{name}@{number}"
        folder = root / location / FOLDER / name / str(number)
        entry = listed.get(number)
        naming = tuple(
            lock for lock in found if lock.versions is not None and lock.names(name, number)
        )
        if entry is None:
            if number != taken.version:
                copies.append(Left(label, f"{shown} does not name it"))
                continue
            if folder.exists() or folder.is_symlink():
                raise CopyRefused(
                    f"{_rel(root, folder)} lies in the library folder already, though {shown} "
                    f"does not name it: list it, or take the folder out"
                )
            copies.append(Written("copied", taken, folder, "", naming))
            entries.append((number, taken.entry, True))
        elif entry.get("released") is True:
            copies.append(_released_copy(held, library, number, entry, folder, naming, shown))
        else:
            copied = _copy_not_released(held, library, number, entry, folder, naming, found, named)
            copies.append(copied)
            if isinstance(copied, Written) and dict(copied.source.entry) != dict(entry):
                entries.append((number, copied.source.entry, False))
    _check_named(named, found, name, copies)
    written = [each for each in copies if isinstance(each, Written)]
    sources = {(each.version, each.folder): each for each in (taken, *(w.source for w in written))}
    for source in sources.values():
        _check(source)
    for path in (*(each.folder for each in written), root / shown):
        try:
            refuse_links(root, path)
        except FileError as exc:
            raise CopyRefused(str(exc)) from exc
    for each in written:
        if each.folder.exists() and not each.folder.is_dir():
            raise CopyRefused(
                f"{_rel(root, each.folder)} is a file where a version's folder belongs: take it out"
            )
    list_file = root / shown
    return Plan(
        tuple(copies),
        tuple(_listed_line(name, each, entry, new, shown) for each, entry, new in entries),
        list_file,
        _list_text(root, list_file, name, entries),
    )


def write(planned: Plan, change: Change) -> None:
    """Write a planned run, as the next steps of `change`, and take it: each copy written
    into a folder beside its own and moved into its place, the folder it replaces moved
    aside, then the list. Raises WriteFailed where a write fails, every file then as it was
    before the run, or named."""
    for each in planned.copies:
        if not isinstance(each, Written):
            continue
        sources = {rel: each.source.folder / rel for rel in each.source.files}
        if each.folder.exists():
            change.replace_folder(each.folder, sources)
        else:
            change.add_folder(each.folder, sources)
    if planned.list_text is not None:
        change.write(planned.list_file, planned.list_text.encode("utf-8"))
    change.commit()


def report(planned: Plan, root: Path, shown: Mapping[tuple[str, str], Sequence[str]]) -> list[str]:
    """What a run says: each copy it wrote, with each lock that names it, and each it left,
    with why, each lock that holds it with what `shown` gives of it by its `Lock.key`, and
    how to replace it; then each line the list took."""
    said = []
    for each in planned.copies:
        if isinstance(each, Left):
            said.append(f"left {each.label} as it is: {each.why}")
            for lock in each.locks:
                said.append(f"  {lock.described}")
                said.extend(f"    {line}" for line in shown.get(lock.key, ()))
            said.extend(_way_to_replace(each))
            continue
        count = len(each.source.files)
        where = "to" if each.how == "copied" else "in"
        said.append(
            f"{each.how} {each.source.label}, {count} file{'s' if count != 1 else ''}, {where} "
            f"{_rel(root, each.folder)}/{each.said}"
        )
        said.extend(f"  locked by {lock.described}" for lock in each.locks)
    return [*said, *planned.listed]


def _way_to_replace(left: Left) -> list[str]:
    """The command that replaces a copy only locks hold, naming each of them; none while a
    lock cannot be read, which no person can name."""
    if left.source is None or any(lock.versions is None for lock in left.to_name):
        return []
    named = " ".join(f"--{lock.kind} {lock.name}" for lock in left.to_name)
    return [f"  to replace it, run `pkit visual add {left.source.name} {named}`"]


# --- what the capability ships ------------------------------------------------------------------


def _library(name: str) -> shipped.Shipped:
    """The library `name` the capability ships. Raises CopyRefused."""
    ships = shipped.read(SHIPPED)
    found = next((each for each in ships if each.name == name), None)
    if found is None:
        named = ", ".join(f"`{each.name}`" for each in ships) or "none"
        raise CopyRefused(f"the capability ships no library `{name}`; it ships {named}")
    return found


def _released(library: shipped.Shipped) -> tuple[shipped.Released, ...]:
    """The library's released versions, the newest first. Raises CopyRefused."""
    try:
        return library.released
    except shipped.ShippedError as exc:
        raise CopyRefused(
            f"the record of the shipped `{library.name}` cannot be read: {exc}"
        ) from exc


def _being_built(library: shipped.Shipped) -> Version:
    """The number the version being built carries. Raises CopyRefused."""
    try:
        built = library.being_built()
    except LibraryError as exc:
        unbound = _unbound(library.built, ["library.yaml"])
        if unbound:
            raise CopyRefused(
                f"the shipped `{library.name}` cannot be copied: {'; '.join(unbound)}"
            ) from exc
        raise CopyRefused(f"the shipped `{library.name}` cannot be read: {exc}") from exc
    if built.name != library.name:
        raise CopyRefused(
            f"the shipped `{library.name}` names itself `{built.name}` in its library.yaml"
        )
    return built.version


def under(library: shipped.Shipped, version: Version) -> Source | None:
    """What the capability ships of `library` under `version`: the released version of that
    number, else the version being built where it carries it; None where it ships neither.
    Raises CopyRefused where the library's record or its version being built cannot be
    read."""
    released = next((each for each in _released(library) if each.version == version), None)
    if released is not None:
        place = released.place
        files = tuple(path.relative_to(place).as_posix() for path in released.files())
        return Source(library.name, version, place, files, dict(released.entry), released)
    if _being_built(library) != version:
        return None
    top = library.built.relative_to(library.folder).as_posix()
    files = tuple(rel[len(top) + 1 :] for rel in listed_files(library.folder, top))
    return Source(library.name, version, library.built, files, {"released": False}, None)


def _taken(library: shipped.Shipped, version: Version | None, being_built: bool) -> Source:
    """The version the run takes: the released `version` named, the version being built
    where `being_built` asks, or by default the newest released version, else the version
    being built. Raises CopyRefused for a number the capability releases no version of."""
    released = _released(library)
    if version is not None:
        if not any(each.version == version for each in released):
            ships = ", ".join(str(each.version) for each in released) or "none"
            raise CopyRefused(
                f"the capability releases no {library.name}@{version}; it releases {ships}. "
                f"`--being-built` takes the version being built, "
                f"{library.name}@{_being_built(library)}"
            )
        number = version
    elif being_built or not released:
        number = _being_built(library)
    else:
        number = released[0].version
    found = under(library, number)
    assert found is not None  # a released number, or the version being built's
    return found


def _check(source: Source) -> None:
    """Refuse what the capability ships that no copy may be taken from: a released version
    whose files no longer match the hash its record keeps, files of the capability's format
    that lack their binding, and a version with no `library.yaml`."""
    if source.released is not None:
        changes = source.released.hash_changes()
        if changes:
            raise CopyRefused(
                f"the capability's {source.label} no longer matches the hash its record keeps: "
                f"{'; '.join(changes)}"
            )
    if "library.yaml" not in source.files:
        raise CopyRefused(f"the shipped {source.label} holds no library.yaml")
    unbound = _unbound(source.folder, source.files)
    if unbound:
        raise CopyRefused(f"the shipped `{source.name}` cannot be copied: {'; '.join(unbound)}")


def _unbound(folder: Path, files: Sequence[str]) -> list[str]:
    """Why each file of the capability's format among `files` is not bound to its kind."""
    found = []
    for rel in files:
        kind = kind_within(rel.split("/"))
        if kind is None:
            continue
        try:
            problem = binding_problem(read_yaml(folder / rel), kind)
        except ReadError as exc:
            found.append(str(exc))
            continue
        if problem is not None:
            found.append(f"{rel} {problem}")
    return found


# --- the project's copies -----------------------------------------------------------------------


def _listed(held: Held, name: str) -> dict[Version, Mapping[str, Any]]:
    """Each version of `name` the list names, with its entry. Raises CopyRefused where the
    list cannot be read, or names the library from another source."""
    try:
        listed = held.listed or {}
    except LibraryError as exc:
        raise CopyRefused(f"the list of libraries cannot be read: {exc}") from exc
    library = listed.get(name)
    if library is None:
        return {}
    source = library.get("source") if isinstance(library, Mapping) else None
    if not isinstance(source, Mapping) or source.get("kind") != "shipped":
        raise CopyRefused(
            f"{held.list_path} names `{name}` from another source than the capability's, and a "
            f"name ties one library to its source: rename that library, or take it off the "
            f"list"
        )
    versions = library.get("versions")
    found = {}
    for text, entry in (versions if isinstance(versions, Mapping) else {}).items():
        try:
            found[Version.parse(text)] = entry if isinstance(entry, Mapping) else {}
        except ValueError:
            continue
    return found


def _released_copy(
    held: Held,
    library: shipped.Shipped,
    version: Version,
    entry: Mapping[str, Any],
    folder: Path,
    naming: tuple[Lock, ...],
    shown: str,
) -> Written | Left:
    """A copy the list marks released: restored where its files no longer match its hash,
    else left. Raises CopyRefused where the hash the capability records differs from the
    list's."""
    label = f"{library.name}@{version}"
    changes = held.hash_changes(library.name, version)
    source = under(library, version)
    if source is None or source.released is None:
        why = f"the list marks it released, and the installed capability releases no {label}"
        return Left(label, f"{why}; its files no longer match its hash" if changes else why)
    if entry.get("hash") != source.entry.get("hash"):
        raise CopyRefused(
            f"{shown} keeps the hash {_value(entry)} for {label}, released, and the capability "
            f"records {_value(source.entry)}: two contents carry one released number"
        )
    if not changes:
        return Left(label, "released, and its files match its hash")
    return Written("restored", source, folder, f", as released: {'; '.join(changes)}", naming)


def _copy_not_released(
    held: Held,
    library: shipped.Shipped,
    version: Version,
    entry: Mapping[str, Any],
    folder: Path,
    naming: tuple[Lock, ...],
    found: Sequence[Lock],
    named: Collection[tuple[str, str]],
) -> Written | Left:
    """A copy the list marks not released: replaced by what the capability ships under its
    number, else left, with why. A lock that moves only on purpose holds it unless `named`
    names that lock."""
    label = f"{library.name}@{version}"
    source = under(library, version)
    if source is None:
        return Left(label, f"the installed capability ships no {label}")
    if dict(source.entry) == dict(entry) and holds(held, source):
        return Left(label, f"it holds {source.said} of its number already")
    to_name = holding(found, library.name, version)
    held_by = tuple(lock for lock in to_name if lock.key not in named)
    if held_by:
        why = "a lock that moves only on purpose names it"
        return Left(label, why, held_by, source, to_name)
    if folder.is_dir() and not folder.is_symlink():
        said = f", with {source.said}"
    else:
        said = f", with {source.said}, its folder missing before"
    return Written("replaced", source, folder, said, naming)


def holding(found: Sequence[Lock], library: str, version: Version) -> tuple[Lock, ...]:
    """The locks that keep a copy not yet released as it is: each that names it, or may, and
    moves only on purpose. A person naming each such piece and declaration in the command is
    the move on purpose that lets the copy be replaced."""
    return tuple(lock for lock in found if lock.names(library, version) and not lock.follows)


def _check_named(
    named: Collection[tuple[str, str]],
    found: Sequence[Lock],
    library: str,
    copies: Sequence[Written | Left],
) -> None:
    """Refuse each lock a person names that locks no copy the run would replace, whichever
    other locks still hold that copy, naming what it locks; a piece or a declaration the
    location does not hold; and a lock the command cannot read. Raises CopyRefused."""
    replaced = {
        each.source.version
        for each in copies
        if each.source is not None and (isinstance(each, Left) or each.how == "replaced")
    }
    for kind, name in sorted(named):
        lock = next((each for each in found if each.key == (kind, name)), None)
        if lock is None:
            raise CopyRefused(f"the location holds no {kind} `{name}`")
        if lock.versions is None:
            raise CopyRefused(f"{lock.described}: mend it, then name it")
        if not any(lock.names(library, number) for number in replaced):
            locked = ", ".join(f"{each}@{lock.versions[each]}" for each in sorted(lock.versions))
            raise CopyRefused(
                f"{lock.described} locks no copy of `{library}` this run would replace: it "
                f"locks {locked or 'nothing'}"
            )


def holds(held: Held, source: Source) -> bool:
    """Whether the location's copy of the version holds exactly the files `source` ships."""
    held_it = source.version in held.folders.get(source.name, {})
    return held_it and not differences(held, source)


def differences(held: Held, source: Source) -> list[str]:
    """How the location's copy of the version differs from what `source` ships, file by file
    in path order: a file only one of them holds, or one whose bytes differ. Empty where the
    copy holds exactly the files `source` ships."""
    prefix = f"{held.location}/{FOLDER}/{source.name}/{source.version}/"
    mine = {
        path.relative_to(held.root).as_posix()[len(prefix) :]: path
        for path in held.files(source.name, source.version)
    }
    theirs = set(source.files)
    found = []
    for rel in sorted(set(mine) | theirs):
        if rel not in theirs:
            found.append(f"`{rel}` is not in what the capability ships")
        elif rel not in mine:
            found.append(f"`{rel}` is missing")
        elif mine[rel].read_bytes() != (source.folder / rel).read_bytes():
            found.append(f"`{rel}` differs")
    return found


def _value(entry: Mapping[str, Any]) -> str:
    """The value of an entry's hash, or `none`."""
    found = entry.get("hash")
    value = found.get("value") if isinstance(found, Mapping) else None
    return f"`{value}`" if isinstance(value, str) else "none"


# --- what the check finds of each copy ----------------------------------------------------------


@dataclass(frozen=True)
class Compared:
    """Each copy of a library the capability ships, compared with what the installed
    capability ships (`compare`): what the check finds of them, and each released copy, by
    its label, that the command restores where its files no longer match its hash."""

    findings: tuple[Finding, ...]
    restored: frozenset[str]


def compare(held: Held) -> Compared:
    """Each copy the list names of a library the capability ships, compared with what the
    installed capability ships under its number (DEC-013 point 6). Each finding asks the
    project for attention, and names no version, so its level stands:

    - `copy-not-shipped`: a copy the list marks not released, that the library folder holds,
      and that is not what the capability ships under its number: other files, a released
      version, or a number it does not ship. It names the command, or, for a number not
      shipped, the way out of DEC-013 point 5.
    - `copy-hash-differs`: a copy the list marks released whose hash differs from the one the
      capability records for that version, naming both: two contents carry one released
      number.

    A released copy whose hash is the one the capability records is one the command
    restores (`Compared.restored`). A library the list gives another source, or that the
    capability does not ship, is not compared. Nor is one whose record or version being
    built the capability cannot read: the capability's own checks hold those."""
    try:
        listed = held.listed or {}
    except LibraryError:
        return Compared((), frozenset())  # `list-unreadable`, in `Held.findings`
    ships = {each.name: each for each in shipped.read(SHIPPED)}
    found: list[Finding] = []
    restored: set[str] = set()
    for name in sorted(listed):
        library = ships.get(name)
        if library is None or held.source(name) != SHIPPED_SOURCE:
            continue
        try:
            mine, theirs = _compared(held, library, _listed(held, name))
        except CopyRefused:
            continue
        found.extend(mine)
        restored |= theirs
    return Compared(tuple(found), frozenset(restored))


def _compared(
    held: Held, library: shipped.Shipped, versions: Mapping[Version, Mapping[str, Any]]
) -> tuple[list[Finding], set[str]]:
    """The findings of one library's copies, the newest first, and the label of each released
    copy the command restores. Raises CopyRefused where the library's record, or its version
    being built, cannot be read."""
    found: list[Finding] = []
    restored: set[str] = set()
    name = library.name
    for version in sorted(versions, reverse=True):
        entry = versions[version]
        label = f"{name}@{version}"
        source = under(library, version)
        if entry.get("released") is True:
            if source is None or source.released is None:
                continue  # the capability releases no version of that number
            if entry.get("hash") == source.entry.get("hash"):
                restored.add(label)
                continue
            found.append(
                Finding(
                    "copy-hash-differs",
                    ATTENTION,
                    f"{held.list_path} keeps the hash {_value(entry)} for {label}, released, "
                    f"and the installed capability records {_value(source.entry)}: two "
                    f"contents carry one released number",
                    file=held.list_path,
                    where=f"libraries.{name}.versions.{version}.hash",
                    fix=f"choose which content {label} holds: `pkit visual add {name}` refuses "
                    f"while the two hashes differ",
                    who=PROJECT,
                )
            )
            continue
        if version not in held.folders.get(name, {}):
            continue  # `version-missing`, in `Held.findings`
        fix = (
            f"run `pkit visual add {name}`, which replaces the copy with what the capability "
            f"ships under its number"
        )
        if source is None:
            said = f"{label} is listed not released, and the installed capability ships no {label}"
            fix = (
                "move each draft that locks it, on purpose, to a version the capability ships, "
                "by pinning it to that version or by taking a new major; once no lock names "
                "the copy, take it out of the library folder and off the list"
            )
        elif source.released is not None:
            said = f"{label} is listed not released, and the installed capability released it"
        else:
            changes = differences(held, source)
            if not changes:
                continue
            said = (
                f"{label}, listed not released, holds other files than the installed "
                f"capability ships under its number, {source.said}: " + "; ".join(changes)
            )
        found.append(
            Finding(
                "copy-not-shipped",
                ATTENTION,
                said,
                file=f"{held.location}/{FOLDER}/{name}/{version}",
                fix=fix,
                who=PROJECT,
            )
        )
    return found, restored


# --- the locks ----------------------------------------------------------------------------------


def locks(root: Path, location: str, library: str) -> list[Lock]:
    """Each lock of the location, as it bears on `library`: each piece's, a folder of
    `pieces/` that holds a file, in name order; then each declaration's of written code, a
    YAML file directly in `code/`, in name order."""
    found = []
    prefix = f"{location}/{PIECES}/"
    pieces = {rel[len(prefix) :].split("/")[0] for rel in listed_files(root, prefix[:-1])}
    for name in sorted(pieces):
        found.append(_piece_lock(root, f"{prefix}{name}/{PIECE_FILE}", name, library))
    prefix = f"{location}/{DECLARATIONS}/"
    for rel in listed_files(root, prefix[:-1]):
        rest = rel[len(prefix) :]
        if "/" not in rest and rest.endswith(".yaml"):
            found.append(_declaration_lock(root, rel, rest[: -len(".yaml")], library))
    return found


def final(piece: Mapping[str, Any]) -> bool:
    """Whether a piece, by what its `piece.yaml` holds, is final to every command: no render
    moves its lock, and an export and a producer's run refuse it (DEC-017 point 3). This is
    the one place that says so."""
    return piece.get("state") == FINAL


def lock_stays(piece: Mapping[str, Any]) -> bool:
    """Whether no render moves a piece's lock, whatever its `pinned` says: it is final or
    published (DEC-003 point 8)."""
    return final(piece) or piece.get("state") == PUBLISHED


def no_lock(piece: Mapping[str, Any]) -> str:
    """What a piece whose lock no render moves (`lock_stays`) needs where it has no lock: a
    published piece goes back to a draft, and no state leads out of final (DEC-017 point 5)."""
    return WRITE_BACK if final(piece) else FIRST_RENDER


def _piece_lock(root: Path, file: str, name: str, library: str) -> Lock:
    """A piece's lock, from its `piece.yaml` alone: its `lock`, `state` and, of a draft,
    `pinned`."""
    data, why = _bound(root / file, "piece")
    if data is not None:
        state, pinned = data.get("state"), data.get("pinned", False)
        if state not in STATES:
            why = f"its state `{state}` is not one format 1 takes"
        elif state == DRAFT and not isinstance(pinned, bool):
            why = "its `pinned` is not true or false"
        else:
            versions, why = _versions(data, library)
            if versions is not None:
                draft = state == DRAFT
                follows = final(data) or (draft and not pinned)
                called = f"{'pinned ' if pinned else ''}draft" if draft else f"{state} piece"
                return Lock(PIECE, name, file, follows, versions, called=called)
    return Lock(PIECE, name, file, False, None, why)


def _declaration_lock(root: Path, file: str, name: str, library: str) -> Lock:
    """A declaration's lock of written code, which moves only on purpose."""
    data, why = _bound(root / file, "code")
    if data is not None:
        versions, why = _versions(data, library)
        if versions is not None:
            return Lock(DECLARATION, name, file, False, versions)
    return Lock(DECLARATION, name, file, False, None, why)


def _bound(path: Path, kind: str) -> tuple[Mapping[str, Any] | None, str]:
    """The file at `path` bound to `kind` at format 1, or None and why it cannot be read."""
    if not path.is_file():
        return None, "the file does not exist"
    try:
        data = read_yaml(path)
    except ReadError as exc:
        said = str(exc)
        return None, said.removeprefix(f"{path}: ")
    problem = binding_problem(data, kind)
    if problem is not None:
        return None, f"the file {problem}"
    return data, ""


def _versions(data: Mapping[str, Any], library: str) -> tuple[Mapping[str, str] | None, str]:
    """The lock `data` holds, or None and why: a mapping of libraries to versions, its entry
    for `library`, where it has one, a version."""
    lock = data.get("lock", {})
    if not isinstance(lock, Mapping) or not all(
        isinstance(key, str) and isinstance(value, str) for key, value in lock.items()
    ):
        return None, "its `lock` is not a mapping of libraries to versions"
    if library in lock:
        try:
            Version.parse(lock[library])
        except ValueError:
            return None, f"its lock names `{library}: {lock[library]}`, which is no version"
    return lock, ""


# --- the list -----------------------------------------------------------------------------------


def _list_text(
    root: Path,
    list_file: Path,
    name: str,
    entries: Sequence[tuple[Version, Mapping[str, Any], bool]],
) -> str | None:
    """The list's text once it takes each entry, a new version added and a version listed
    otherwise written again, every other byte kept; a list written whole where the location
    holds none; None where it takes none. Raises CopyRefused."""
    if not entries:
        return None
    shipped_source = {"kind": "shipped"}
    if not list_file.exists():
        versions = {str(version): dict(entry) for version, entry, _ in entries}
        record = {"pkit_schema": schema_of("libraries"), "schema_version": FORMAT}
        library = {"source": shipped_source, "versions": versions}
        return records.text({**record, "libraries": {name: library}}, LIST_HEADER)
    shown = _rel(root, list_file)
    try:
        text = list_file.read_bytes().decode("utf-8")
        named = name in (records.read(list_file, "libraries").get("libraries") or {})
    except (OSError, UnicodeDecodeError, records.RecordError) as exc:
        raise CopyRefused(f"the list of libraries cannot be read: {exc}") from exc
    for version, entry, new in entries:
        label = f"{name}@{version}"
        try:
            if not named:
                library = {"source": shipped_source, "versions": {str(version): dict(entry)}}
                text = records.with_entry(text, ["libraries"], name, library, each="library")
                named = True
            elif new:
                path = ["libraries", name, "versions"]
                text = records.with_entry(text, path, str(version), dict(entry), each="version")
            else:
                path = ["libraries", name, "versions"]
                text = records.with_value(text, path, str(version), dict(entry), each="version")
        except records.RecordError as exc:
            raise CopyRefused(f"{shown} cannot take {label} as text: {exc}") from exc
    return text


def _listed_line(
    name: str, version: Version, entry: Mapping[str, Any], new: bool, shown: str
) -> str:
    """What the list takes for a version, in words."""
    released = entry.get("released") is True
    state = "released, with the hash the capability records" if released else "not released"
    if new:
        return f"listed {name}@{version} in {shown}, from the source `shipped`, {state}"
    return f"listed {name}@{version} in {shown} as {state}"


def _rel(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()
