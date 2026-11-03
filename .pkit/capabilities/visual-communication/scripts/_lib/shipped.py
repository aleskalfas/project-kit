"""The libraries the capability ships: the version being built of each, its released
versions and its record, and the history that says when a release could be made
(visual-communication DEC-013 points 1 to 4).

**The layout** of the capability's folder, for each library it ships:

- **The version being built,** `libraries/<library>/`, under a name that names no
  version: the one version every change to the library goes into (DEC-013 point 2). The
  libraries the capability ships are read from these alone (`libraries.shipped_names`).
- **Each released version,** whole, as it was released, in a place of its own,
  `releases/<library>/<version>/`. Its release adds the place, and nothing later
  renames, removes or changes a file of it.
- **The library's record,** `releases/<library>/releases.yaml`, a file of the format
  `libraries` that holds the one library: `source: {kind: shipped}`, and each released
  version as the location's list keeps one, `{released: true, hash: <fingerprint>}`
  (DEC-003 point 4). So the command that brings the library in copies the entry as it
  is. The hash is the fingerprint, form 1, over every file of the released place, the
  `library.yaml` that names the release it needs included (`entry_of`). A library with
  no released version has no record.

The released places and the record lie outside the place of the version being built, and
each library's apart from every other's, under its own name. So a release touches no file
of the version being built, the look at its history sees only changes to it, and the
releases of two libraries meet nowhere.

**The reader**, `read`, gives each library the capability ships (`Shipped`): its version
being built, each released version with its place and its hash (`Released`), and the
newest released version of each major. It reads the record as it finds it, and names
what does not match it (`Shipped.problems`, `strays`).

**The history** of the repository the capability is authored in, read with git:

- `release_change`: the release step's change that wrote a version of the capability,
  the change on HEAD's first-parent line that added the changelog's entry for that
  version, which the release step tags inline as `**visual-communication X.Y.Z**`. Never
  a tag, since a release that moves only components is not tagged, and never a change
  that stamped the number by hand, since only the release step writes the changelog.
- `changes_to`: each change to a place between two changes, read with
  `--full-history`, so a change and its take-back on one side of a merge are not pruned.
- `brought_in`: the change that brings a released version in, the last change on HEAD's
  first-parent line that added its place. A place taken back and released again is read
  from its last release.

Each raises HistoryMissing where the history is not at hand: git cannot be run, the
folder holds no repository, or the clone is shallow, so a change it needs may lie beyond
it; or a change it is given is not in the history. HistoryRefused, which HistoryMissing
is a kind of, says the history at hand cannot answer otherwise.
"""

from __future__ import annotations

import subprocess
from collections.abc import Mapping
from functools import cached_property
from pathlib import Path
from typing import Any

from _lib import fingerprint, location, records
from _lib.libraries import SHIPPED_LIBRARIES, Library, Version, read_library, shipped_names
from _lib.root import CAPABILITY, SHIPPED

#: The folder of the capability that holds the version being built of each library.
BEING_BUILT = SHIPPED_LIBRARIES.name

#: The folder of the capability that holds the released versions and the records.
RELEASES = "releases"

#: A library's record, within `releases/<library>/`.
RECORD = "releases.yaml"

#: The changelog the release step writes, relative to the repository's top.
CHANGELOG = "CHANGELOG.md"


class ShippedError(Exception):
    """A library's record that cannot be read as the record of its released versions."""


class HistoryRefused(Exception):
    """The history at hand cannot answer: the message says why."""


class HistoryMissing(HistoryRefused):
    """The history is not at hand: the message says what is missing, and the way out."""


class Released:
    """A released version of a library the capability ships: its version, its place, and its
    entry in the library's record, `{released: true, hash: <fingerprint>}`."""

    def __init__(self, folder: Path, name: str, version: Version, entry: Mapping[str, Any]) -> None:
        self.folder = folder
        self.name = name
        self.version = version
        self.entry = entry

    @property
    def label(self) -> str:
        return f"{self.name}@{self.version}"

    @property
    def place(self) -> Path:
        """The released version's folder, `releases/<library>/<version>/`."""
        return place_of(self.folder, self.name, self.version)

    @property
    def hash(self) -> Mapping[str, Any]:
        """The fingerprint the record keeps of it."""
        return self.entry["hash"]

    def files(self) -> list[Path]:
        """Every file of its place (`files_of`)."""
        return files_of(self.folder, self.name, self.version)

    def hash_changes(self) -> list[str]:
        """What no longer matches the hash the record keeps; empty when it verifies."""
        if not self.place.is_dir():
            return ["the capability no longer holds its place"]
        return fingerprint.verify(
            self.hash,
            "library-version",
            library=self.name,
            version=str(self.version),
            folder=self.place,
            files=self.files(),
        )


class Shipped:
    """A library the capability ships, in the capability's folder `folder`."""

    def __init__(self, folder: Path, name: str) -> None:
        self.folder = folder
        self.name = name

    @property
    def built(self) -> Path:
        """The place of the version being built, `libraries/<library>/`."""
        return self.folder / BEING_BUILT / self.name

    @property
    def releases(self) -> Path:
        """The folder of its released places and its record, `releases/<library>/`."""
        return self.folder / RELEASES / self.name

    @property
    def record(self) -> Path:
        """Its record, `releases/<library>/releases.yaml`, which it holds only once a
        version is released."""
        return self.releases / RECORD

    def being_built(self) -> Library:
        """The version being built, read. Raises LibraryError."""
        return read_library(self.built)

    @cached_property
    def released(self) -> tuple[Released, ...]:
        """Each released version the record lists, the newest first; none where it has no
        record. Raises ShippedError where the record cannot be read as the record of this
        library's released versions."""
        if not self.record.is_file():
            return ()
        shown = self.record.relative_to(self.folder).as_posix()
        try:
            data = records.read(self.record, "libraries")
        except records.RecordError as exc:
            raise ShippedError(str(exc)) from exc
        libraries = data.get("libraries")
        if not isinstance(libraries, Mapping) or list(libraries) != [self.name]:
            raise ShippedError(f"{shown} does not hold `{self.name}` alone under `libraries`")
        library = libraries[self.name]
        source = library.get("source") if isinstance(library, Mapping) else None
        if source != {"kind": "shipped"}:
            raise ShippedError(f"{shown} does not name `{self.name}`'s source `shipped`")
        versions = library.get("versions")
        if not isinstance(versions, Mapping) or not versions:
            raise ShippedError(
                f"{shown} lists no released version of `{self.name}`, and a library with "
                f"none has no record"
            )
        found = []
        for text, entry in versions.items():
            try:
                version = Version.parse(text)
            except ValueError as exc:
                raise ShippedError(f"{shown}: {exc}") from exc
            if (
                not isinstance(entry, Mapping)
                or entry.get("released") is not True
                or not isinstance(entry.get("hash"), Mapping)
            ):
                raise ShippedError(
                    f"{shown} lists {self.name}@{version} otherwise than as released, with its hash"
                )
            found.append(Released(self.folder, self.name, version, entry))
        return tuple(sorted(found, key=lambda each: each.version, reverse=True))

    def newest(self) -> Released | None:
        """The newest released version, or None where none is released."""
        return self.released[0] if self.released else None

    def newest_of_majors(self) -> dict[int, Released]:
        """The newest released version of each major, by major."""
        found: dict[int, Released] = {}
        for each in self.released:
            found.setdefault(each.version.major, each)
        return found

    def places(self) -> list[str]:
        """The name of each folder under `releases/<library>/`, each a released place where
        the record lists it, as git lists the files."""
        return sorted({rel.split("/")[0] for rel in self._listed() if "/" in rel})

    def _listed(self) -> list[str]:
        """Every file under `releases/<library>/`, relative to it, as git lists them."""
        rel = self.releases.relative_to(self.folder).as_posix()
        return [each[len(rel) + 1 :] for each in location.files(self.folder, rel)]

    def problems(self) -> list[str]:
        """What does not match the layout: a record that cannot be read, a version it lists
        whose place is missing, a place it does not list, and a file beside them that is
        neither."""
        try:
            listed = {str(each.version) for each in self.released}
        except ShippedError as exc:
            return [str(exc)]
        found = []
        shown = self.releases.relative_to(self.folder).as_posix()
        for version in sorted(listed - set(self.places())):
            found.append(
                f"{shown}/{RECORD} lists {self.name}@{version}, whose place {shown}/{version}/ "
                f"is missing"
            )
        for version in sorted(set(self.places()) - listed):
            found.append(
                f"{shown}/{version}/ is no released version {shown}/{RECORD} lists: list it, "
                f"or take the folder out"
            )
        for rel in self._listed():
            if "/" not in rel and rel != RECORD:
                found.append(f"{shown}/{rel} is neither a released place nor the record")
        return found


def read(folder: Path = SHIPPED) -> list[Shipped]:
    """Each library the capability whose folder is `folder` ships, in name order: each with
    a version being built (`libraries.shipped_names`)."""
    return [Shipped(folder, name) for name in shipped_names(folder / BEING_BUILT)]


def strays(folder: Path = SHIPPED) -> list[str]:
    """What `releases/` holds for no library the capability ships: each entry whose name is
    no library with a version being built."""
    shipped = set(shipped_names(folder / BEING_BUILT))
    named = {rel.split("/")[1] for rel in location.files(folder, RELEASES)}
    return [
        f"{RELEASES}/{name} names no library the capability builds: a released version lies "
        f"beside its library's version being built"
        for name in sorted(named - shipped)
    ]


def place_of(folder: Path, name: str, version: Version) -> Path:
    """The place of a released version, `releases/<library>/<version>/`."""
    return folder / RELEASES / name / str(version)


def files_of(folder: Path, name: str, version: Version) -> list[Path]:
    """Every file of a released version's place, listed as a location's version is: as git
    sees them, tracked and untracked but not ignored; walked outside a repository."""
    rel = place_of(folder, name, version).relative_to(folder).as_posix()
    return [folder / each for each in location.files(folder, rel)]


def entry_of(folder: Path, name: str, version: Version) -> dict[str, Any]:
    """A released version's entry, as the location's list and the library's record keep
    it: `released: true`, and its hash, the fingerprint, form 1, over every file of its
    place, the release it needs included."""
    place = place_of(folder, name, version)
    inputs = fingerprint.library_version_inputs(
        library=name, version=str(version), folder=place, files=files_of(folder, name, version)
    )
    return {"released": True, "hash": fingerprint.fingerprint(inputs)}


# --- the history --------------------------------------------------------------------------------


def release_change(
    root: Path, version: str, *, changelog: str = CHANGELOG, head: str = "HEAD"
) -> str:
    """The release step's change that wrote `version` of the capability, in the repository
    at `root`: the last change on `head`'s first-parent line that added the changelog's
    entry tagged `**visual-communication <version>**`, a merge read against its first
    parent. Raises HistoryMissing where the history is not at hand, and HistoryRefused
    where it records no release of that version."""
    _whole(root)
    tag = f"**{CAPABILITY} {version}**"
    changed = _lines(
        root,
        "log",
        "--first-parent",
        "--diff-merges=first-parent",
        "--no-patch",
        "--format=%H",
        "-S",
        tag,
        head,
        "--",
        changelog,
    )
    found, held = None, False
    for change in reversed(changed):
        holds = tag in _show(root, change, changelog)
        if holds and not held:
            found = change
        held = holds
    if found is None:
        raise HistoryRefused(
            f"the history records no release of {CAPABILITY} {version}: no change on {head}'s "
            f"first-parent line adds the entry `{tag}` to {changelog}"
        )
    return found


def changes_to(root: Path, place: str, since: str, until: str = "HEAD") -> list[str]:
    """Each change to `place`, a path relative to `root`, after the change `since` up to the
    change `until`, that change included, newest first: `git log --full-history
    <since>..<until> -- <place>`. Raises HistoryMissing where the history is not at hand,
    and HistoryRefused where `since` does not lead to `until`."""
    _whole(root)
    for change in (since, until):
        if _git(root, "rev-parse", "--verify", "--quiet", f"{change}^{{commit}}").returncode:
            raise HistoryMissing(f"the change {change} is not in the history at hand")
    if _git(root, "merge-base", "--is-ancestor", since, until).returncode:
        raise HistoryRefused(f"the change {since} does not lead to the change {until}")
    return _lines(root, "log", "--full-history", "--format=%H", f"{since}..{until}", "--", place)


def brought_in(root: Path, place: str, head: str = "HEAD") -> str | None:
    """The change that brings the released place `place`, a path relative to `root`, in:
    the last change on `head`'s first-parent line that added its `library.yaml`, a merge
    read against its first parent; None where no change on that line added it. Raises
    HistoryMissing where the history is not at hand."""
    _whole(root)
    added = _lines(
        root,
        "log",
        "--first-parent",
        "--diff-merges=first-parent",
        "--no-patch",
        "--no-renames",
        "--diff-filter=A",
        "--format=%H",
        head,
        "--",
        f"{place}/library.yaml",
    )
    return added[0] if added else None


def _whole(root: Path) -> None:
    """Raise HistoryMissing unless `root` lies in a repository whose whole history is at
    hand."""
    proc = _git(root, "rev-parse", "--is-shallow-repository")
    if proc.returncode:
        detail = [line for line in proc.stderr.splitlines() if line]
        said = detail[-1] if detail else f"git exited {proc.returncode}"
        raise HistoryMissing(f"{root} holds no history git can read: {said}")
    if proc.stdout.strip() == "true":
        raise HistoryMissing(
            "the clone is shallow, so the history is not at hand: fetch it whole, as a "
            "checkout with `fetch-depth: 0` does"
        )


def _show(root: Path, change: str, path: str) -> str:
    """The file at `path` as the change `change` holds it; empty where it holds none."""
    proc = _git(root, "show", f"{change}:{path}")
    return proc.stdout if proc.returncode == 0 else ""


def _lines(root: Path, *args: str) -> list[str]:
    proc = _git(root, *args)
    if proc.returncode:
        detail = [line for line in proc.stderr.splitlines() if line]
        said = detail[-1] if detail else f"git exited {proc.returncode}"
        raise HistoryMissing(f"git {args[0]} could not read the history: {said}")
    return [line for line in proc.stdout.splitlines() if line]


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            ["git", *args],
            cwd=root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except OSError as exc:
        raise HistoryMissing(f"git could not be run ({exc})") from exc
