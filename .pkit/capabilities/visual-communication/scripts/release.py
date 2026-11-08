#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "jsonschema==4.26.0",
#   "referencing==0.37.0",
#   "ruamel.yaml==0.19.1",
#   "uharfbuzz==0.57.0",
#   "fonttools==4.68.0",
#   "uniseg==0.10.1",
# ]
# ///
"""visual-communication capability — release: release a version of a library, read in full
and compared with the library's previous release first (DEC-003 points 6 and 7, DEC-013,
DEC-014 point 1).

Two kinds of library, released on the same steps where they share them:

- **A project's own library,** `pkit visual release <library>`: the newest version the
  location holds of a library its list names from the source `project`. It writes only
  the location: the release it needs in the version's `library.yaml`, and the version
  marked released in the list, with its hash, every other byte of the list kept.
- **A library the capability ships,** `pkit visual release <library> --shipped`: its
  version being built as HEAD holds it, where the capability is authored. It adds the
  released place and the entry in the library's record, and writes the change's patch
  changeset for the capability. It changes no other file of the capability's folder.

**The steps both take,** every refusal before any write:

1. **Read in full** (`full_read.read`): each file against its schema, every component and
   the brand's tokens as the engine reads them, each font it holds, and each pattern
   against its lists' default components, as the check of a version alone judges them. No
   scene is computed. A finding that fails refuses the release, each one named.
2. **Compared** with the library's previous release (`comparison.compare`): the segment the
   number needs is shown, and a break in a version that keeps the previous release's
   major refuses the release. A library's first release is compared with none, and the
   command says so.
3. **The release it needs** is the capability's current version, written into the
   version's `library.yaml` before the hash is worked out, so the hash covers it.

**A shipped library's release first** (DEC-013 point 1, in the order of its Implications):

1. refuses where the methodology holds the capability's folder as a synced copy, by the
   methodology's own answer (`shipped.synced_copy`);
2. finds the release step's change that wrote the capability's current version, by the
   changelog's entry it added, and refuses where that history is not at hand, records no
   such release, or that change's tree holds no checks of the shipped versions;
3. refuses where a change touched the version being built since, `git log
   --full-history <that change>..HEAD`, or where the working tree changes it;
4. refuses a number already released, below the newest released one, or below one the
   version being built carried at an earlier release;
5. checks the version, in a location built for the run in the clone's local folder, on
   the newest released version of each major of each library it builds on, a base
   released earlier in the same change included; it refuses where a base has no released
   version of a major the library names, and on a finding that fails;
6. reads it in full there and compares it, as above.

Usage:
  pkit visual release <library>
  pkit visual release <library> --shipped

Exit codes:
  0  released
  1  refused: nothing is written. Or a write failed: it names the file, and every file is
     as it was before the run, or each it could not put back is named
"""

from __future__ import annotations

import argparse
import contextlib
import dataclasses
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Iterator, Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))

from _lib import (
    checks,
    comparison,
    files,
    fingerprint,
    full_read,
    libraries,
    location,
    records,
    shipped,
)
from _lib import pipeline as pl
from _lib.findings import FAILS, Finding
from _lib.root import CAPABILITY, CAPABILITY_DIR, CONFIG, LOCAL, project_root

#: Where a changeset lies, relative to the repository's top (the release mechanics,
#: "Changeset files").
CHANGESETS = ".changes/unreleased"

#: The location a shipped library's release builds to check a version, within the folder
#: it builds for the run.
WORK = "visual"


class ReleaseRefused(Exception):
    """A release that is not made: the message says why, and the way out."""


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="pkit visual release",
        description=(
            "Release a version of a library, read in full and compared with the library's "
            "previous release first."
        ),
    )
    parser.add_argument("library", help="the library's name")
    parser.add_argument(
        "--shipped",
        action="store_true",
        help="release the version being built of a library the capability ships, where the "
        "capability is authored",
    )
    args = parser.parse_args()
    root = project_root()
    try:
        if args.shipped:
            return _release_shipped(root, args.library)
        return _release_own(root, args.library)
    except (
        ReleaseRefused,
        location.LocationRefused,
        location.GitFailed,
        files.WriteFailed,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


# --- the steps both kinds take ------------------------------------------------------------------


def _read_in_full(
    held: libraries.Held,
    name: str,
    version: libraries.Version,
    shown: Mapping[str, tuple[str, str]],
) -> full_read.FullRead:
    """The version read in full (DEC-014 point 1), and each of its patterns judged against
    its lists' default components, as the check of a version alone judges them
    (`checks.default_clashes`). Refused on a finding that fails, each one named; each
    other finding is printed."""
    read = full_read.read(held, name, version)
    found = list(read.findings)
    if read.library is not None and read.scope is not None and read.library.kind == "components":
        env = pl.LibraryEnv(read.versions, read.scope)
        found.extend(checks.default_clashes(held, read.library, env))
    _judge(read.label, [(finding, finding.level) for finding in found], "read in full", shown)
    return read


def _judge(
    label: str,
    judged: Sequence[tuple[Finding, str]],
    step: str,
    shown: Mapping[str, tuple[str, str]],
) -> None:
    """Refuse the release of `label` where a finding fails, naming each; print each other
    finding that lies in the version, or in none, each named where the tree holds it
    (`_in_tree`)."""
    failing, noted, said = [], [], set()
    for finding, level in judged:
        finding = _in_tree(finding, shown)
        line = f"  {checks.place(finding)} [{finding.code}] ({level}): {checks.said(finding)}"
        if line in said:
            continue
        said.add(line)
        if level == FAILS:
            failing.append(line)
        elif finding.library in (label, ""):
            noted.append(line)
    for line in noted:
        print(line.strip())
    if failing:
        count = f"{len(failing)} finding{'s' if len(failing) != 1 else ''}"
        raise ReleaseRefused(
            f"{label} is not released: {count} that fail{'s' if len(failing) == 1 else ''} "
            f"where it is {step}, each to mend in the version first:\n" + "\n".join(failing)
        )


def _in_tree(finding: Finding, shown: Mapping[str, tuple[str, str]]) -> Finding:
    """`finding`, its file named where the tree holds it. `shown` maps a version's label to
    where the read held it, relative to the read's root, and where the tree holds it: a file
    of the version is named at its place in the tree, and a component the engine read,
    which the finding names with no file, at the component's file."""
    for prefix, place in shown.values():
        if finding.file == prefix or finding.file.startswith(f"{prefix}/"):
            return dataclasses.replace(finding, file=place + finding.file[len(prefix) :])
    library, _, component = str(finding.extra.get("component") or "").partition("/")
    lies = shown.get(finding.library)
    if not finding.file and lies and component and finding.library.startswith(f"{library}@"):
        return dataclasses.replace(finding, file=f"{lies[1]}/{pl.COMPONENTS}/{component}.yaml")
    return finding


def _compared(previous: full_read.FullRead | None, read: full_read.FullRead) -> None:
    """The comparison of `read` with the library's previous release, shown; refused where
    it finds a break and the number keeps the previous release's major (DEC-003 point 7,
    DEC-004 point 5). A first release is compared with none, and says so."""
    if previous is None:
        print(f"{read.label} is the library's first release, so it is compared with none")
        return
    try:
        found = comparison.compare(previous, read)
    except comparison.ComparisonError as exc:
        raise ReleaseRefused(
            f"{read.label} cannot be compared with its previous release, {previous.label}: {exc}"
        ) from exc
    if not found.allowed:
        major = previous.version.major
        raise ReleaseRefused(
            f"{read.label} keeps the major of its previous release, {previous.label}, and "
            f"breaks what it promises: raise its number to {major + 1}.0.0, or take each "
            f"break back:\n" + "\n".join(found.lines())
        )
    for line in found.lines():
        print(line)


def _checked_on(read: full_read.FullRead) -> str:
    """The versions `read` was read with, but itself, in words."""
    others = [library.label for name, library in read.versions.items() if name != read.name]
    return f" on {', '.join(others)}" if others else ""


# --- a project's own library --------------------------------------------------------------------


def _release_own(root: Path, name: str) -> int:
    """Release the newest version the location holds of the project's own library `name`
    (DEC-014 point 1, DEC-003 points 4 and 6)."""
    where = location.for_reading(root)
    if where is None:
        raise ReleaseRefused(
            f"the project has no visual work: {CONFIG} records no location, and "
            f"`{location.DEFAULT}/` holds none"
        )
    held = libraries.Held(root, where.path)
    try:
        listed = held.listed
    except libraries.LibraryError as exc:
        raise ReleaseRefused(f"the list of libraries cannot be read: {exc}") from exc
    if listed is None:
        raise ReleaseRefused(
            f"the location holds no list of libraries, {held.list_path}: write it, naming "
            f"`{name}` from the source `project`"
        )
    entry = listed.get(name)
    if not isinstance(entry, Mapping):
        raise ReleaseRefused(f"{held.list_path} names no library `{name}`")
    source = entry.get("source")
    kind = source.get("kind") if isinstance(source, Mapping) else None
    if kind == "shipped":
        raise ReleaseRefused(
            f"`{name}` is a library the capability ships, which the project does not own: "
            f"whoever maintains the capability releases it where the capability is "
            f"authored, with `--shipped`"
        )
    if kind != "project":
        raise ReleaseRefused(
            f"{held.list_path} names `{name}` from the source `{kind}`, a library another "
            f"repository shares and releases: the project releases only a library of its "
            f"own, from the source `project`"
        )
    versions = held.versions(name)
    if not versions:
        raise ReleaseRefused(f"the library folder holds no version of `{name}`")
    version = versions[0]
    label = f"{name}@{version}"
    listed_versions = entry.get("versions")
    if not isinstance(listed_versions, Mapping) or str(version) not in listed_versions:
        raise ReleaseRefused(
            f"{held.list_path} does not list {label}, the newest version the library folder "
            f"holds: list it `released: false` first"
        )
    if held.released(name, version):
        raise ReleaseRefused(
            f"{label}, the newest version the library folder holds, is released already, and "
            f"a released version never changes: put the next version in a folder of its "
            f"own, `{held.location}/{libraries.FOLDER}/{name}/<version>/`, and list it "
            f"`released: false`"
        )
    lies = held.folders[name][version].relative_to(root).as_posix()
    read = _read_in_full(held, name, version, {label: (lies, lies)})
    print(f"checked {label}{_checked_on(read)}: no finding fails")
    previous = next((each for each in versions[1:] if held.released(name, each)), None)
    if previous is not None:
        changes = held.hash_changes(name, previous)
        if changes:
            raise ReleaseRefused(
                f"{name}@{previous}, the previous release, no longer matches what was "
                f"released, so {label} cannot be compared with it: restore its folder as it "
                f"was released first: " + "; ".join(changes)
            )
        _compared(full_read.read(held, name, previous), read)
    else:
        _compared(None, read)
    needs = ".".join(map(str, held.release))
    folder = held.folders[name][version]
    file = folder / "library.yaml"
    list_file = root / held.list_path
    for target in (file, list_file):
        try:
            files.refuse_links(root, target)
        except files.FileError as exc:
            raise ReleaseRefused(str(exc)) from exc
    try:
        written = shipped.needs_written(file, needs)
    except shipped.ShippedError as exc:
        raise ReleaseRefused(str(exc)) from exc
    inputs = fingerprint.library_version_inputs(
        library=name,
        version=str(version),
        folder=folder,
        files=held.files(name, version),
        data={"library.yaml": written},
    )
    released = {"released": True, "hash": fingerprint.fingerprint(inputs)}
    try:
        text = records.with_value(
            list_file.read_bytes().decode("utf-8"),
            ["libraries", name, "versions"],
            str(version),
            released,
            each="version",
        )
    except (OSError, UnicodeDecodeError, records.RecordError) as exc:
        raise ReleaseRefused(
            f"{held.list_path} cannot mark {label} released as text: {exc}"
        ) from exc
    change = files.Change(root)
    change.write(file, written)
    change.write(list_file, text.encode("utf-8"))
    change.commit()
    print(f"wrote the release it needs, {needs}, in {file.relative_to(root).as_posix()}")
    print(f"listed {label} released in {held.list_path}, with its hash")
    return 0


# --- a library the capability ships -------------------------------------------------------------


def _release_shipped(root: Path, name: str) -> int:
    """Release the version being built of `name`, a library the capability whose folder
    the tree at `root` holds ships (DEC-013 points 1 to 4)."""
    folder = root / CAPABILITY_DIR
    try:
        copy = shipped.synced_copy(root, CAPABILITY_DIR)
    except shipped.ShippedError as exc:
        raise ReleaseRefused(str(exc)) from exc
    if copy:
        raise ReleaseRefused(
            f"{CAPABILITY_DIR} arrives in this repository as a synced copy, so no library it "
            f"ships is released here: whoever maintains the capability releases it where the "
            f"capability is authored"
        )
    every = shipped.read(folder)
    library = next((each for each in every if each.name == name), None)
    if library is None:
        ships = ", ".join(f"`{each.name}`" for each in every) or "none"
        raise ReleaseRefused(f"the capability ships no library `{name}`; it ships {ships}")
    try:
        built = library.being_built()
        released = library.released
        current = shipped.current_version(folder)
    except (libraries.LibraryError, shipped.ShippedError) as exc:
        raise ReleaseRefused(f"`{name}` cannot be released: {exc}") from exc
    label = built.label
    place = library.built.relative_to(root).as_posix()
    since = _release_change(root, current, label)
    _untouched(root, place, since, current)
    _numbers(root, library, built, released, place)
    bases = _bases(every, built)
    try:
        planned = shipped.plan_release(library, built, current)
    except shipped.ShippedError as exc:
        raise ReleaseRefused(str(exc)) from exc
    with _scratch(root) as work:
        held, shown = _work_location(root, work, every, planned)
        report = checks.check(work)
        _judge(label, report.judged, "checked on released bases", shown)
        read = _read_in_full(held, name, built.version, shown)
        on = f" on {', '.join(bases)}" if bases else ""
        print(f"checked {label}{on}: no finding fails")
        previous = library.newest()
        _compared(full_read.read(held, name, previous.version) if previous else None, read)
    changeset, text = _changeset(root, name, built.version)
    change = files.Change(root)
    shipped.write_release(planned, change)
    change.write(changeset, text.encode("utf-8"))
    change.commit()
    count = len(planned.files)
    print(
        f"released {label}, {count} file{'s' if count != 1 else ''}, to "
        f"{planned.place.relative_to(root).as_posix()}/, needing release {current}"
    )
    print(f"recorded its hash in {library.record.relative_to(root).as_posix()}")
    print(
        f"wrote {changeset.relative_to(root).as_posix()}, a patch of {CAPABILITY}: raise its "
        f"kind where the release needs more"
    )
    return 0


def _release_change(root: Path, current: str, label: str) -> str:
    """Step 2: the release step's change that wrote the capability's current version, whose
    tree holds the capability's own checks of the versions it ships."""
    try:
        since = shipped.release_change(root, current)
    except shipped.HistoryMissing as exc:
        raise ReleaseRefused(f"{label} is not released: {exc}") from exc
    except shipped.HistoryRefused as exc:
        raise ReleaseRefused(
            f"{label} is not released: {exc}. No release has carried it under the "
            f"capability's current version: release it once a release writes the version "
            f"the capability's package.yaml carries"
        ) from exc
    if not shipped.held_at(root, since, shipped.CHECKS):
        raise ReleaseRefused(
            f"{label} is not released: the tree at the release step's change that wrote "
            f"{CAPABILITY} {current}, {since[:12]}, holds no {shipped.CHECKS}, so no check "
            f"read the version as that release carried it: release it after the next "
            f"release that moves the capability's version"
        )
    return since


def _untouched(root: Path, place: str, since: str, current: str) -> None:
    """Step 3: no change touched the version being built since the release step's change
    `since`, and the working tree changes nothing of it."""
    try:
        changes = shipped.changes_to(root, place, since)
        pending = shipped.uncommitted(root, place)
    except shipped.HistoryRefused as exc:
        raise ReleaseRefused(f"the history of {place} cannot be read: {exc}") from exc
    later = "wait for the next release that moves the capability's version, and release it then"
    if changes:
        count = f"{len(changes)} change{'s' if len(changes) != 1 else ''}"
        listed = ", ".join(change[:12] for change in changes)
        raise ReleaseRefused(
            f"{count} touched {place} after the release step's change that wrote "
            f"{CAPABILITY} {current}, {since[:12]}, so no release carried the version as it "
            f"stands ({listed}): {later}"
        )
    if pending:
        raise ReleaseRefused(
            f"the working tree changes {place} since HEAD ({', '.join(pending)}), and the "
            f"release takes the version as HEAD holds it: take the change out, or commit it "
            f"and {later}"
        )


def _numbers(
    root: Path,
    library: shipped.Shipped,
    built: libraries.Library,
    released: Sequence[shipped.Released],
    place: str,
) -> None:
    """Step 4: the version being built carries no released number, none below the newest
    released one, and none below a number it carried at an earlier release."""
    raise_first = "raise the number in its library.yaml first"
    if any(each.version == built.version for each in released):
        raise ReleaseRefused(
            f"{built.label} is released already, and a released number never names other "
            f"files: {raise_first}"
        )
    newest = library.newest()
    if newest is not None and built.version < newest.version:
        raise ReleaseRefused(
            f"{built.label} is below the newest released version of `{library.name}`, "
            f"{newest.version}: {raise_first}"
        )
    try:
        carried = shipped.numbers_carried(root, place)
    except shipped.HistoryRefused as exc:
        raise ReleaseRefused(f"the history of {place} cannot be read: {exc}") from exc
    above = [(change, version) for change, version in carried if version > built.version]
    if above:
        change, version = max(above, key=lambda each: each[1])
        raise ReleaseRefused(
            f"{built.label} is below {version}, which the version being built carried at "
            f"the release {change[:12]}, and a project's copy may carry: raise its number to "
            f"{version} or above first"
        )


def _bases(every: Sequence[shipped.Shipped], built: libraries.Library) -> list[str]:
    """The newest released version of each major `built` builds on, in words; refused
    where a base is no library the capability ships, or has no released version of the
    major the library names."""
    by_name = {each.name: each for each in every}
    found = []
    for need in built.builds_on:
        base = by_name.get(need.name)
        if base is None:
            raise ReleaseRefused(
                f"{built.label} builds on `{need.name}`, which the capability does not ship"
            )
        try:
            newest = base.newest_of_majors().get(need.major)
        except shipped.ShippedError as exc:
            raise ReleaseRefused(f"`{need.name}`, which {built.label} builds on: {exc}") from exc
        if newest is None:
            raise ReleaseRefused(
                f"{built.label} builds on `{need.name}` {need.major}, of which no version is "
                f"released: release `{need.name}` first"
            )
        found.append(newest.label)
    return found


@contextlib.contextmanager
def _scratch(root: Path) -> Iterator[Path]:
    """A folder in the clone's local folder, a project of its own for the length of the
    run, and removed after it. The clone ignores the local folder, so where it lies in a
    repository the folder is made one of its own, whose files git lists."""
    base = root / LOCAL
    base.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(dir=base, prefix="release-"))
    try:
        if any((each / ".git").exists() for each in work.parents):
            try:
                made = subprocess.run(
                    ["git", "init", "-q"], cwd=work, capture_output=True, text=True, check=False
                )
            except OSError as exc:
                raise ReleaseRefused(f"git could not be run ({exc})") from exc
            if made.returncode:
                raise ReleaseRefused(
                    f"no location could be built to check the version in: {made.stderr.strip()}"
                )
        yield work
    finally:
        shutil.rmtree(work, ignore_errors=True)


def _work_location(
    root: Path, work: Path, every: Sequence[shipped.Shipped], planned: shipped.Release
) -> tuple[libraries.Held, dict[str, tuple[str, str]]]:
    """The location, in `work`, that holds every released version of every library the
    capability ships, each listed as its record keeps it, and the version to release, its
    files as the release writes them, listed not released. Each is listed from the source
    `project`, so a finding in the version to release fails, as in a project's own library
    not yet released. Also: where each lies in `work` and in the tree, by its label."""
    folder = work / WORK / libraries.FOLDER
    listed: dict[str, dict[str, object]] = {}
    shown: dict[str, tuple[str, str]] = {}

    def hold(name: str, version: libraries.Version, sources: Mapping[str, Path | bytes]) -> None:
        target = folder / name / str(version)
        for rel, source in sources.items():
            copy = target / rel
            copy.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(source, bytes):
                copy.write_bytes(source)
            else:
                shutil.copyfile(source, copy)
        listed.setdefault(name, {"source": {"kind": "project"}, "versions": {}})

    for library in every:
        try:
            released = library.released
        except shipped.ShippedError as exc:
            raise ReleaseRefused(f"the released versions of `{library.name}`: {exc}") from exc
        for each in released:
            sources = {path.relative_to(each.place).as_posix(): path for path in each.files()}
            hold(each.name, each.version, sources)
            versions = listed[each.name]["versions"]
            assert isinstance(versions, dict)
            versions[str(each.version)] = dict(each.entry)
            shown[each.label] = (
                f"{WORK}/{libraries.FOLDER}/{each.name}/{each.version}",
                each.place.relative_to(root).as_posix(),
            )
    hold(planned.library.name, planned.version, planned.files)
    versions = listed[planned.library.name]["versions"]
    assert isinstance(versions, dict)
    versions[str(planned.version)] = {"released": False}
    shown[f"{planned.library.name}@{planned.version}"] = (
        f"{WORK}/{libraries.FOLDER}/{planned.library.name}/{planned.version}",
        planned.library.built.relative_to(root).as_posix(),
    )
    record = {
        "pkit_schema": files.schema_of("libraries"),
        "schema_version": files.FORMAT,
        "libraries": listed,
    }
    (folder / "libraries.yaml").write_text(records.text(record, ()), encoding="utf-8")
    return libraries.Held(work, WORK), shown


def _changeset(root: Path, name: str, version: libraries.Version) -> tuple[Path, str]:
    """The change's patch changeset for the capability, naming the library and the version
    released (DEC-013 point 4): its path, named as the release mechanics name one, and its
    text."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    slug = f"release-{name}-{str(version).replace('.', '-')}"
    path = root / CHANGESETS / f"{CAPABILITY}-patch-{stamp}-{slug}.yaml"
    if path.exists():
        raise ReleaseRefused(f"{path.relative_to(root).as_posix()} exists already: run it again")
    body = (
        f"`{name}` {version}, a library the capability ships, is released: its files are "
        f"fixed from now on, and the capability records their hash."
    )
    text = f"component: {CAPABILITY}\nkind: patch\ncustom:\n  category: Added\nbody: >\n  {body}\n"
    return path, text


if __name__ == "__main__":
    sys.exit(main())
