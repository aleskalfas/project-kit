"""The library folder, the list of the project's libraries, versions, the libraries the
capability ships, and a piece's lock (DEC-001 point 5, DEC-002 point 3, DEC-003 points 1,
4, 5, 8 and 9, DEC-004 point 6).

- **The library folder** is `libraries/` in the location. Each version a lock may name is
  a folder of its own, `libraries/<name>/<version>/`, holding the version whole with its
  `library.yaml`. A version is *held* when its folder's `library.yaml` is listed as git
  sees the files.
- **The list**, `libraries/libraries.yaml` (format `libraries`), names each library's
  source and the versions present, which of them are released, and the fingerprint of
  each released one (form 1, over every file of its folder). A released version whose
  folder no longer verifies has changed since its release.
- **A shipped library** is one the capability ships: one version of each, in a folder of
  its own under `SHIPPED_LIBRARIES`. A person brings it in by a command, which copies the
  version whole into the library folder and lists it with the source `shipped`, every
  other byte of the list kept (`plan_copy`, then `copy_shipped`). A shipped version is not
  released yet, so the list marks it `released: false`. The copy never overwrites a
  version the folder holds, and is refused where a file of the capability's format in the
  version lacks its binding.
- **Versions** are `X.Y.Z` with X at least 1 in format 1, and a library's *line* is its
  major. `builds-on` names each library a library builds on by its major, an integer. A
  brand marks at most one of them as its base, `base: true` (DEC-004 point 6); a
  component library marks none. Whether the base is a brand is read with the brand
  (`tokens.read_brand`). The base is one of the libraries the brand builds on, so the
  lock names it as it names the others.
- **The release a library needs**, `needs-release`, is a release of the capability; the
  installed capability reads no library that needs a newer one.
- **A draft's lock** moves, at each render, to the newest combination of held versions the
  installed capability reads that fit together, within the lines the lock names. It tries
  the newest of each library first, and where two libraries build on two majors of one
  library, it backs off library by library; it refuses, naming the conflict, when none
  fits. A library the lock does not name yet takes its newest version of any major. A
  pinned draft's lock never moves: it is checked, never changed.
"""

from __future__ import annotations

import os
import re
import shutil
import tempfile
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import Any

from _lib import fingerprint, records
from _lib.files import (
    FORMAT,
    FileError,
    binding_problem,
    read_bound,
    refuse_links,
    schema_of,
    write_whole,
)
from _lib.findings import FAILS, Finding
from _lib.location import files as listed_files
from _lib.names import is_name
from _lib.reading import ReadError, read_yaml
from _lib.root import SHIPPED

#: The library folder, within the location.
FOLDER = "libraries"

#: The library that owns the shared roles, axes, families and pairs (DEC-004 point 7).
FOUNDATIONS = "foundations"

#: The list of the project's libraries, within the location.
LIST = f"{FOLDER}/libraries.yaml"

#: The libraries the capability ships, one version of each, in its own folder.
SHIPPED_LIBRARIES = SHIPPED / "libraries"

#: The comment that opens a list a command writes whole, a line each.
LIST_HEADER = (
    "The list of the project's libraries (visual-communication DEC-003 point 4): each",
    "library's source, the versions the library folder holds, which of them are released,",
    "and the fingerprint of each released one. `pkit visual add` lists a version it copies.",
)

#: The kinds of library format 1 reads.
KINDS = ("components", "brand")

_SEMVER = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")


class LibraryError(Exception):
    """A library version that cannot be read, or a list that cannot."""


class LockRefused(Exception):
    """No lock fits: the message names the conflict, or what the project lacks."""


@dataclass(frozen=True, order=True)
class Version:
    """A library's version, `X.Y.Z` with X at least 1 (format 1)."""

    major: int
    minor: int
    patch: int

    @classmethod
    def parse(cls, text: object) -> Version:
        """The version `text` spells. Raises ValueError for another shape, or a major of 0."""
        match = _SEMVER.match(text) if isinstance(text, str) else None
        if match is None or int(match.group(1)) < 1:
            raise ValueError(f"`{text}` is not a version `X.Y.Z` with X at least 1")
        return cls(*(int(part) for part in match.groups()))

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"


def release_of(text: object) -> tuple[int, int, int]:
    """A release of the capability, `X.Y.Z`. Raises ValueError for another shape."""
    match = _SEMVER.match(text) if isinstance(text, str) else None
    if match is None:
        raise ValueError(f"`{text}` is not a release `X.Y.Z`")
    major, minor, patch = (int(part) for part in match.groups())
    return major, minor, patch


def installed_release() -> tuple[int, int, int]:
    """The release of the installed capability, as its `package.yaml` gives it."""
    package = read_yaml(SHIPPED / "package.yaml")
    return release_of(package["component"]["version"])


@dataclass(frozen=True)
class BuildsOn:
    """A library a library builds on, by its major; `base` when a brand marks it its base."""

    name: str
    major: int
    base: bool = False


@dataclass(frozen=True)
class Library:
    """A library version as its `library.yaml` gives it."""

    name: str
    version: Version
    kind: str
    needs_release: tuple[int, int, int]
    builds_on: tuple[BuildsOn, ...]
    folder: Path

    @property
    def label(self) -> str:
        return f"{self.name}@{self.version}"

    @property
    def base(self) -> BuildsOn | None:
        """The library of `builds-on` it marks as its base, or None."""
        return next((need for need in self.builds_on if need.base), None)


def read_library(folder: Path) -> Library:
    """The library version in `folder`, from its `library.yaml`. Raises LibraryError."""
    path = folder / "library.yaml"
    try:
        data = read_bound(path, "library")
    except (ReadError, FileError) as exc:
        raise LibraryError(str(exc)) from exc
    name, kind = data.get("name"), data.get("kind")
    if not is_name(name):
        raise LibraryError(f"{path}: `name` is not a name of lower-case words")
    if kind not in KINDS:
        raise LibraryError(f"{path}: `kind` is not one of {', '.join(KINDS)}")
    try:
        version = Version.parse(data.get("version"))
        needs = release_of(data.get("needs-release"))
    except ValueError as exc:
        raise LibraryError(f"{path}: {exc}") from exc
    raw = data.get("builds-on")
    if not isinstance(raw, list):
        raise LibraryError(f"{path}: `builds-on` is not a list")
    builds_on = []
    for entry in raw:
        if (
            not isinstance(entry, Mapping)
            or not {"name", "major"} <= set(entry) <= {"name", "major", "base"}
            or not is_name(entry["name"])
            or not isinstance(entry["major"], int)
            or isinstance(entry["major"], bool)
            or entry["major"] < 1
            or entry.get("base", True) is not True
        ):
            raise LibraryError(
                f"{path}: each of `builds-on` is `{{name, major}}`, a major from 1, and "
                f"`base: true` on a brand's base"
            )
        builds_on.append(BuildsOn(entry["name"], entry["major"], base="base" in entry))
    bases = [need.name for need in builds_on if need.base]
    if len(bases) > 1:
        raise LibraryError(
            f"{path}: `builds-on` marks {', '.join(f'`{name}`' for name in bases)} as bases; a "
            f"brand has at most one base"
        )
    if bases and kind != "brand":
        raise LibraryError(
            f"{path}: `builds-on` marks `{bases[0]}` as a base, but only a brand has a base"
        )
    return Library(
        name=name,
        version=version,
        kind=kind,
        needs_release=needs,
        builds_on=tuple(builds_on),
        folder=folder,
    )


def kind_within(within: Sequence[str]) -> str | None:
    """The kind of file of the capability's format a path within a version folder names,
    by its name and place, `within` being its parts; None for a file no name makes one."""
    parts = tuple(within)
    if parts == ("library.yaml",):
        return "library"
    if parts == ("roles.yaml",):
        return "roles"
    if len(parts) == 2 and parts[0] == "components" and parts[1].endswith(".yaml"):
        return "component"
    return None


class Held:
    """The library versions a location holds, and its list.

    `root` is the project root and `location` the location's path within it. `release` is
    the installed capability's release, read from its `package.yaml` unless given."""

    def __init__(
        self, root: Path, location: str, release: tuple[int, int, int] | None = None
    ) -> None:
        self.root = root
        self.location = location
        self.release = release if release is not None else installed_release()
        self._libraries: dict[tuple[str, Version], Library | LibraryError] = {}
        self.folders: dict[str, dict[Version, Path]] = {}
        self.strays: list[str] = []
        prefix = f"{location}/{FOLDER}/"
        self._files = listed_files(root, f"{location}/{FOLDER}")
        for rel in self._files:
            parts = rel[len(prefix) :].split("/")
            if len(parts) != 3 or parts[2] != "library.yaml":
                continue
            try:
                version = Version.parse(parts[1])
            except ValueError:
                self.strays.append(f"{prefix}{parts[0]}/{parts[1]}")
                continue
            self.folders.setdefault(parts[0], {})[version] = root / prefix / parts[0] / parts[1]

    @property
    def list_path(self) -> str:
        """The list's path, relative to the project root."""
        return f"{self.location}/{LIST}"

    def names(self) -> list[str]:
        """The libraries held, in name order."""
        return sorted(self.folders)

    def versions(self, name: str) -> list[Version]:
        """The versions of `name` held, the newest first."""
        return sorted(self.folders.get(name, {}), reverse=True)

    def files(self, name: str, version: Version) -> list[Path]:
        """Every file of a version's folder, as git sees them, in path order."""
        prefix = f"{self.location}/{FOLDER}/{name}/{version}/"
        return [self.root / rel for rel in self._files if rel.startswith(prefix)]

    def library(self, name: str, version: Version) -> Library:
        """The library version held, read. Raises LibraryError."""
        key = (name, version)
        if key not in self._libraries:
            folder = self.folders.get(name, {}).get(version)
            if folder is None:
                self._libraries[key] = LibraryError(
                    f"the project holds no version {version} of `{name}`"
                )
            else:
                try:
                    self._libraries[key] = read_library(folder)
                except LibraryError as exc:
                    self._libraries[key] = exc
        found = self._libraries[key]
        if isinstance(found, LibraryError):
            raise found
        return found

    def unreadable(self, name: str, version: Version) -> str | None:
        """Why the installed capability cannot read a version held, or None."""
        try:
            library = self.library(name, version)
        except LibraryError as exc:
            return str(exc)
        if (library.name, library.version) != (name, version):
            return (
                f"its `library.yaml` says {library.label}, but it lies in the folder of "
                f"{name}@{version}"
            )
        if library.needs_release > self.release:
            needs = ".".join(map(str, library.needs_release))
            have = ".".join(map(str, self.release))
            return (
                f"it needs release {needs} of the capability, and {have} is installed: "
                f"upgrade the capability"
            )
        return None

    @cached_property
    def listed(self) -> Mapping[str, Any] | None:
        """The list's libraries, or None when the location holds no list. Raises
        LibraryError when it cannot be read."""
        path = self.root / self.list_path
        if self.list_path not in self._files:
            return None
        try:
            data = records.read(path, "libraries")
        except records.RecordError as exc:
            raise LibraryError(str(exc)) from exc
        libraries = data.get("libraries")
        if not isinstance(libraries, Mapping):
            raise LibraryError(f"{path}: `libraries` is not a mapping of libraries")
        return libraries

    def released(self, name: str, version: Version) -> bool:
        """Whether the list marks a version released."""
        try:
            entry = self._listed_version(name, version)
        except LibraryError:
            return False
        return bool(entry and entry.get("released") is True)

    def _listed_version(self, name: str, version: Version) -> Mapping[str, Any] | None:
        listed = self.listed or {}
        library = listed.get(name)
        versions = library.get("versions") if isinstance(library, Mapping) else None
        entry = versions.get(str(version)) if isinstance(versions, Mapping) else None
        return entry if isinstance(entry, Mapping) else None

    def hash_changes(self, name: str, version: Version) -> list[str]:
        """What no longer matches a released version's fingerprint in the list; empty when
        it verifies, or the version is not released."""
        entry = self._listed_version(name, version)
        if not entry or entry.get("released") is not True:
            return []
        recorded = entry.get("hash")
        if not isinstance(recorded, Mapping):
            return ["the list keeps no fingerprint of it"]
        folder = self.folders.get(name, {}).get(version)
        if folder is None:
            return ["the project no longer holds its folder"]
        return fingerprint.verify(
            recorded,
            "library-version",
            library=name,
            version=str(version),
            folder=folder,
            files=self.files(name, version),
        )

    def findings(self) -> list[Finding]:
        """What is wrong with the library folder and its list (DEC-003 point 9): a version
        the list does not name or the folder does not hold, a version the capability
        cannot read, and a released version that changed."""
        found: list[Finding] = []
        file = self.list_path
        for stray in self.strays:
            found.append(
                Finding(
                    "library-folder",
                    FAILS,
                    f"`{stray}` is not a version folder `X.Y.Z`",
                    file=stray,
                    fix="name the folder after the version its `library.yaml` gives",
                )
            )
        try:
            listed = self.listed
        except LibraryError as exc:
            return [*found, Finding("list-unreadable", FAILS, str(exc), file=file)]
        if listed is None:
            if self.folders:
                found.append(
                    Finding(
                        "list-missing",
                        FAILS,
                        "the library folder holds versions but no list of them",
                        file=file,
                        fix=f"write {file}, naming each library's source and versions",
                    )
                )
            return found
        for name in self.names():
            for version in self.versions(name):
                where = f"{name}/{version}"
                label = f"{name}@{version}"
                if self._listed_version(name, version) is None:
                    found.append(
                        Finding(
                            "version-unlisted",
                            FAILS,
                            f"the list does not name {label}, which the library folder holds",
                            file=file,
                            where=f"libraries.{name}.versions",
                            fix=f"add {version} under `libraries.{name}.versions`",
                        )
                    )
                why = self.unreadable(name, version)
                if why is not None:
                    found.append(
                        Finding(
                            "library-unreadable",
                            FAILS,
                            f"the installed capability cannot read {label}: {why}",
                            file=f"{self.location}/{FOLDER}/{where}/library.yaml",
                            library=label,
                        )
                    )
                changes = self.hash_changes(name, version)
                if changes:
                    found.append(
                        Finding(
                            "library-changed",
                            FAILS,
                            f"{label} no longer matches what was released: " + "; ".join(changes),
                            file=f"{self.location}/{FOLDER}/{where}",
                            library=label,
                            fix="restore the version folder as it was released",
                        )
                    )
        for name, library in listed.items():
            versions = library.get("versions") if isinstance(library, Mapping) else None
            for text in versions or {}:
                try:
                    version = Version.parse(text)
                except ValueError:
                    continue
                if version not in self.folders.get(name, {}):
                    found.append(
                        Finding(
                            "version-missing",
                            FAILS,
                            f"the list names {name}@{text}, which the library folder does not hold",
                            file=file,
                            where=f"libraries.{name}.versions.{text}",
                            fix="restore the version's folder, or take it off the list",
                        )
                    )
        return found


# --- a shipped library --------------------------------------------------------------------------


class CopyRefused(Exception):
    """A shipped version that is not copied into the library folder: the message says why,
    and the way out."""


@dataclass(frozen=True)
class ShippedCopy:
    """A copy of a shipped version into the library folder, checked and not yet written: the
    version, its shipped folder with each of its files relative to it, the version folder it
    is copied to, and the list's path with its text once it lists the version."""

    library: Library
    source: Path
    files: tuple[str, ...]
    folder: Path
    list_file: Path
    list_text: str


def shipped_names() -> list[str]:
    """The libraries the capability ships, in name order: each folder of
    `SHIPPED_LIBRARIES` that holds a `library.yaml`."""
    if not SHIPPED_LIBRARIES.is_dir():
        return []
    return sorted(
        path.name for path in SHIPPED_LIBRARIES.iterdir() if (path / "library.yaml").is_file()
    )


def plan_copy(root: Path, location: str, name: str) -> ShippedCopy:
    """The copy of the version of `name` the capability ships into the library folder of
    `location` (DEC-003 point 5), checked, so a refused copy writes nothing. Raises
    CopyRefused for a library the capability does not ship, a file of the capability's
    format in the version that lacks its binding (DEC-002 point 3), a version the library
    folder holds or the list names already, a library the list names from another source
    (DEC-003 point 4), a list that cannot be read or cannot take the version as text, and a
    path reached through a link."""
    shipped = shipped_names()
    if name not in shipped:
        ships = ", ".join(f"`{each}`" for each in shipped) or "none"
        raise CopyRefused(f"the capability ships no library `{name}`; it ships {ships}")
    source = SHIPPED_LIBRARIES / name
    files = _files_of(source)
    unbound = _unbound(source, files)
    if unbound:
        raise CopyRefused(f"the shipped `{name}` cannot be copied: {'; '.join(unbound)}")
    try:
        library = read_library(source)
    except LibraryError as exc:
        raise CopyRefused(f"the shipped `{name}` cannot be read: {exc}") from exc
    if library.name != name:
        raise CopyRefused(f"the shipped `{name}` names itself `{library.name}` in its library.yaml")
    folder = root / location / FOLDER / name / str(library.version)
    if folder.exists() or folder.is_symlink():
        raise CopyRefused(
            f"the library folder holds {folder.relative_to(root).as_posix()} already, and a "
            f"version it holds is never overwritten"
        )
    list_file = root / location / LIST
    for path in (folder, list_file):
        try:
            refuse_links(root, path)
        except FileError as exc:
            raise CopyRefused(str(exc)) from exc
    return ShippedCopy(
        library, source, files, folder, list_file, _listing(root, list_file, library)
    )


def copy_shipped(planned: ShippedCopy) -> None:
    """Write a planned copy: the version's files into a folder beside its own, moved into
    its place whole, then the list. Where a write fails, what was copied is removed and the
    error raised."""
    planned.folder.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(
            dir=planned.folder.parent, prefix=f".{planned.folder.name}.", suffix=".tmp"
        )
    )
    try:
        for rel in planned.files:
            target = staging / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(planned.source / rel, target)
        os.rename(staging, planned.folder)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    try:
        write_whole(planned.list_file, planned.list_text.encode("utf-8"))
    except BaseException:
        shutil.rmtree(planned.folder, ignore_errors=True)
        raise


def _files_of(folder: Path) -> tuple[str, ...]:
    """Every file of `folder`, relative to it, in path order; a link is never followed."""
    found = []
    for current, dirs, names in os.walk(folder, followlinks=False):
        dirs[:] = [d for d in dirs if not (Path(current) / d).is_symlink()]
        for each in names:
            path = Path(current) / each
            if path.is_file() and not path.is_symlink():
                found.append(path.relative_to(folder).as_posix())
    return tuple(sorted(found))


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


def _listing(root: Path, list_file: Path, library: Library) -> str:
    """The list's text once it lists the shipped `library`, not released: a list written
    whole where the location holds none, or the list with the version added, every other
    byte kept. Raises CopyRefused."""
    name, version = library.name, str(library.version)
    unreleased = {"released": False}
    entry = {"source": {"kind": "shipped"}, "versions": {version: unreleased}}
    if not list_file.exists():
        record = {"pkit_schema": schema_of("libraries"), "schema_version": FORMAT}
        return records.text({**record, "libraries": {name: entry}}, LIST_HEADER)
    shown = list_file.relative_to(root).as_posix()
    try:
        data = records.read(list_file, "libraries")
    except records.RecordError as exc:
        raise CopyRefused(f"the list of libraries cannot be read: {exc}") from exc
    listed = data.get("libraries")
    if not isinstance(listed, Mapping):
        raise CopyRefused(f"{shown}: `libraries` is not a mapping of libraries")
    found = listed.get(name)
    if found is None:
        path, key, value = ["libraries"], name, entry
    else:
        source = found.get("source") if isinstance(found, Mapping) else None
        if not isinstance(source, Mapping) or source.get("kind") != "shipped":
            raise CopyRefused(
                f"{shown} names `{name}` from another source than the capability's, and a "
                f"name ties one library to its source: rename that library, or take it off "
                f"the list"
            )
        versions = found.get("versions")
        if isinstance(versions, Mapping) and version in versions:
            raise CopyRefused(
                f"{shown} names {library.label} already, though the library folder does not "
                f"hold it: restore its folder, or take it off the list"
            )
        path, key, value = ["libraries", name, "versions"], version, unreleased
    each = "library" if found is None else "version"
    try:
        return records.with_entry(
            list_file.read_bytes().decode("utf-8"), path, key, value, each=each
        )
    except records.RecordError as exc:
        raise CopyRefused(f"{shown} cannot take {library.label} as text: {exc}") from exc


# --- the lock -----------------------------------------------------------------------------------


def move_lock(
    held: Held,
    roots: Iterable[str],
    lock: Mapping[str, str] | None = None,
    *,
    pinned: bool = False,
) -> dict[str, str]:
    """The lock a render writes for a piece that names the libraries `roots` (its top's
    library, its brand, every library its content uses), with what they build on.

    A draft's lock moves to the newest combination that fits within the lines `lock`
    names; a first lock, or a library the lock does not name yet, takes the newest version
    of any major. A pinned draft's lock is returned as it is once it is checked. Raises
    LockRefused, naming the conflict or what the project lacks."""
    roots = sorted(set(roots))
    if pinned:
        return _checked_pinned(held, roots, lock)
    search = _Search(held, lock or {})
    found = search.run(roots)
    if found is None:
        raise LockRefused(search.conflict or "no versions the project holds fit together")
    return {name: str(found[name].version) for name in sorted(found)}


class _Search:
    """The newest combination that fits, backing off library by library."""

    def __init__(self, held: Held, lock: Mapping[str, str]) -> None:
        self.held = held
        self.lock = lock
        self.conflict: str | None = None

    def _note(self, conflict: str) -> None:
        if self.conflict is None:
            self.conflict = conflict

    def candidates(self, name: str) -> list[Library]:
        held = self.held
        versions = held.versions(name)
        if not versions:
            self._note(f"the project holds no version of `{name}`: bring it in")
            return []
        line: int | None = None
        if name in self.lock:
            try:
                line = Version.parse(self.lock[name]).major
            except ValueError:
                self._note(f"the lock names `{name}: {self.lock[name]}`, which is no version")
                return []
        readable, unread = [], []
        for version in versions:
            if line is not None and version.major != line:
                continue
            why = held.unreadable(name, version)
            if why is None:
                readable.append(held.library(name, version))
            else:
                unread.append(f"{name}@{version}: {why}")
        if not readable:
            within = f" of major {line}, the line the lock names" if line is not None else ""
            reasons = f" ({'; '.join(unread)})" if unread else ""
            self._note(
                f"the project holds no version of `{name}`{within} that the installed "
                f"capability reads{reasons}"
            )
        return readable

    def run(self, roots: list[str]) -> dict[str, Library] | None:
        return self._step({}, list(roots))

    def _step(self, chosen: dict[str, Library], pending: list[str]) -> dict[str, Library] | None:
        if not pending:
            return chosen
        name, rest = pending[0], pending[1:]
        wanted = {
            (library.label, need.major)
            for library in chosen.values()
            for need in library.builds_on
            if need.name == name
        }
        majors = {major for _, major in wanted}
        if len(majors) > 1:
            listed = ", ".join(
                f"{label} builds on `{name}` {major}" for label, major in sorted(wanted)
            )
            self._note(f"no lock fits: {listed}, and a piece locks one version of each library")
            return None
        candidates = self.candidates(name)
        fitting = [
            library for library in candidates if not majors or library.version.major in majors
        ]
        if candidates and not fitting:
            (label, major), *_ = sorted(wanted)
            self._note(
                f"{label} builds on `{name}` {major}, of which the project holds no version "
                f"that fits"
            )
        for library in fitting:
            clash = next(
                (
                    need
                    for need in library.builds_on
                    if need.name in chosen and chosen[need.name].version.major != need.major
                ),
                None,
            )
            if clash is not None:
                self._note(
                    f"no lock fits: {library.label} builds on `{clash.name}` {clash.major}, but "
                    f"{chosen[clash.name].label} is in the lock"
                )
                continue
            added = sorted(
                {
                    need.name
                    for need in library.builds_on
                    if need.name not in chosen and need.name not in rest and need.name != name
                }
            )
            found = self._step({**chosen, name: library}, rest + added)
            if found is not None:
                return found
        return None


def _checked_pinned(held: Held, roots: list[str], lock: Mapping[str, str] | None) -> dict[str, str]:
    """A pinned lock, checked: it names every library the piece needs, each a version the
    project holds and the capability reads, fitting together. Each library's own entry is
    checked before whether the entries fit, so a refusal names the plainer fault."""
    if not lock:
        raise LockRefused("the piece is pinned but has no lock yet: unpin it for its first render")
    pending, seen = list(roots), set()
    needs: list[tuple[str, Version, BuildsOn]] = []
    while pending:
        name = pending.pop(0)
        if name in seen:
            continue
        seen.add(name)
        if name not in lock:
            raise LockRefused(
                f"the piece needs `{name}`, which its pinned lock does not name: move the lock "
                f"on purpose"
            )
        try:
            version = Version.parse(lock[name])
        except ValueError as exc:
            raise LockRefused(
                f"the lock names `{name}: {lock[name]}`, which is no version"
            ) from exc
        if version not in held.folders.get(name, {}):
            raise LockRefused(
                f"the pinned lock names {name}@{version}, which the project does not hold: "
                f"restore it"
            )
        why = held.unreadable(name, version)
        if why is not None:
            raise LockRefused(
                f"the pinned lock names {name}@{version}, which cannot be read: {why}"
            )
        for need in held.library(name, version).builds_on:
            needs.append((name, version, need))
            pending.append(need.name)
    for name, version, need in needs:
        locked = Version.parse(lock[need.name])
        if locked.major != need.major:
            raise LockRefused(
                f"the pinned lock does not fit: {name}@{version} builds on `{need.name}` "
                f"{need.major}, but the lock names {need.name}@{locked}"
            )
    return dict(lock)
