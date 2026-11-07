"""The capability's own checks of the libraries it ships (visual-communication DEC-013
points 4 and 6). The default branch's required checks run them on each change as it would
merge. They lie outside a project's validation, which never runs them.

The shipped folder (`shipped`) holds, for each library, the version being built,
`libraries/<library>/`, and apart from it each released version,
`releases/<library>/<version>/`, with the library's record, `releases/<library>/releases.yaml`.
Six checks hold every version it ships, each run on the capability's folder as the tree
holds it and on the history as the clone holds it:

1. **Each released version** matches the hash its record keeps, and the engine reads its
   files: each file of the capability's format holds its schema, its roles, its
   components, its brand or its notation are read with the versions it is checked with,
   and each picture file it holds is read as the engine reads it.
2. **Every released version was untouched since the release it names:** no change touched
   the place of the version being built between the release step's change that wrote
   the version of the capability it names and the change on HEAD's first-parent line that
   brings it in, that change included (DEC-013 point 1).
3. **The newest released versions read together,** each on the newest released version of
   each major it builds on, as the capability's check reads a version alone.
4. **Each version being built** is read and checked on the versions being built of its
   bases, listed as a project's own library not yet released, so a finding in it fails.
5. **A version being built that carries a released number** differs from that released
   version only in the release it needs, and none carries a number below the newest
   released one.
6. **A version being built breaks nothing its major promises:** the release's comparison
   (`comparison.compare`) of each version being built with the newest released version of
   the major it carries, each read in full on the versions it is checked with, finds no
   break. An addition fails nothing, since whether a change is a patch or a minor is the
   owner's judgement (DEC-013 point 3).

Each version is read in full through the one routine the release and the fetch read it
through too (`full_read.read`, DEC-014 point 1).

**Findings are read by their labels,** not their levels: the check makes a failing finding
in a released version ask for attention instead. A label of `FAILS_AT_ANY_LEVEL` fails
wherever it lies. Any other finding in a released version is printed in the test's
output, and fails nothing: only a new version corrects it (DEC-002 point 7). In a version
being built, a finding fails at the level the check gives it.

Each check is shown to fail where it should, on a folder and a history the tests build.
"""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from tests.in_process import load
from tests.visual_communication_project import (
    CAPABILITY,
    FOUNDATIONS,
    REPO,
    TEST_PICTURES,
    bound,
    project,
    write,
    yaml_text,
)

(
    checks,
    comparison,
    findings_,
    fingerprint,
    full_read,
    libraries,
    location,
    pl,
    reading,
    shipped,
) = load(
    "visual-communication",
    "checks",
    "comparison",
    "findings",
    "fingerprint",
    "full_read",
    "libraries",
    "location",
    "pipeline",
    "reading",
    "shipped",
)

#: The label of a file of the capability's format that its schema refuses. These checks
#: report it, since the core's data validation reads no file under `.pkit/`.
SCHEMA_REFUSED = full_read.SCHEMA_REFUSED

#: The labels that fail at any level: those that mean a version cannot be read, or cannot
#: be read with its bases, or no longer matches its hash. A released version that shows
#: one breaks the format's promise (DEC-003 point 3) or its release (DEC-013 point 3).
FAILS_AT_ANY_LEVEL = frozenset(
    {
        # A file of the capability's format that cannot be read, or that its schema or
        # its binding refuses.
        "file-unreadable",
        "binding",
        SCHEMA_REFUSED,
        # A version the engine cannot read, or that no longer matches its hash.
        "library-unreadable",
        "library-folder",
        "library-changed",
        # A version that cannot be read with its bases.
        "alone-majors",
        "alone-missing",
        # A component the engine refuses: its file, its shape, or a formula it cannot read.
        "component-unreadable",
        "component-shape",
        "formula-unreadable",
        # Declarations of roles the engine leaves unread.
        "roles-unreadable",
        "roles-shape",
        "roles-declaration",
        "role-picture",
        "role-name",
        "role-type",
        "axes-shape",
        "axis-shape",
        "families-shape",
        "family-shape",
        "pairs-shape",
        "pair-shape",
        # A brand the engine stops, alone or over its base.
        "brand-unreadable",
        "brand-kind",
        "brand-dtcg",
        "brand-file",
        "brand-axis",
        "base-loop",
        "base-kind",
        "base-shape",
        "base-lock",
        "base-axis",
        "resolver-unreadable",
        "resolver-shape",
        "tokens-unreadable",
        "tokens-shape",
        "token-name",
        "token-type",
        "token-value",
        "token-shared-group",
        "picture-shape",
        "picture-name",
        "role-missing",
        "alias-loop",
        "alias-dangling",
        "alias-type",
        "alias-private",
        "value-axis-changes-size",
        # A notation the engine cannot read.
        "notation-kind",
        "notation-unreadable",
        # A picture file the engine cannot read, or does not read (DEC-025 point 9).
        "picture-unreadable",
        "picture-stored",
        "picture-encoding",
        "picture-extension",
        # A check that stopped on an error it does not expect.
        "unexpected-error",
        # The list of the location these checks build.
        "list-missing",
        "list-unreadable",
        "version-unlisted",
        "version-missing",
    }
)

#: The location these checks build, within the project root.
LOCATION = "visual"

#: Each label of the check that `FAILS_AT_ANY_LEVEL` leaves to its level, a sample the
#: list is checked against.
LEFT_TO_LEVEL = ("arrangement-clash", "formula-dimension", "role-default", "pair-contrast")


@dataclass
class Outcome:
    """What a check found: each failure, and each finding it reports and fails nothing for,
    each said once."""

    failures: list[str] = field(default_factory=list)
    reported: list[str] = field(default_factory=list)

    def fail(self, said: str) -> None:
        if said not in self.failures:
            self.failures.append(said)

    def report(self, said: str) -> None:
        if said not in self.reported:
            self.reported.append(said)

    def show(self, check: str) -> None:
        """Print each finding reported, under the check's name."""
        for said in self.reported:
            print(f"{check}: reported, fails nothing: {said}")


def said(finding: Any, level: str) -> str:
    """A finding in words: its label and level, where it lies, and what it says."""
    where = finding.file or finding.extra.get("component", "")
    if finding.where:
        where = f"{where}#{finding.where}"
    lies = " in ".join(part for part in (where, finding.library) if part)
    return f"`{finding.code}` ({level}){f' at {lies}' if lies else ''}: {finding.message}"


def judge(outcome: Outcome, found: Sequence[Any], *, released: bool) -> None:
    """Each finding by its label: one of `FAILS_AT_ANY_LEVEL` fails; any other fails in a
    version being built at the level the check gives it, and is reported in a released
    version."""
    for finding in found:
        _, level = findings_.as_read(finding, released)
        if finding.code in FAILS_AT_ANY_LEVEL or (not released and level == findings_.FAILS):
            outcome.fail(said(finding, level))
        else:
            outcome.report(said(finding, level))


def judge_report(outcome: Outcome, report: Any) -> None:
    """The check's findings by their labels, each at the level the check gave it where it
    lies. A finding that fails there lies outside a released version, or in one that no
    longer matches its hash, so it fails here too."""
    for finding, level in report.judged:
        if finding.code in FAILS_AT_ANY_LEVEL or level == findings_.FAILS:
            outcome.fail(said(finding, level))
        else:
            outcome.report(said(finding, level))


# --- reading a version --------------------------------------------------------------------------


def listed(folder: Path, place: Path) -> list[Path]:
    """Every file of `place`, within the capability's folder `folder`, as a location's version
    is listed: as git sees them, tracked and untracked but not ignored."""
    rel = place.relative_to(folder).as_posix()
    return [folder / each for each in location.files(folder, rel)]


@dataclass(frozen=True)
class Copied:
    """A version the location these checks build holds: its library, its version, the
    folder it is copied from with its files, and its entry in the list."""

    name: str
    version: Any
    source: Path
    files: tuple[Path, ...]
    entry: Mapping[str, Any]


def location_of(tmp: Path, versions: Sequence[Copied], kind: str) -> Any:
    """The library versions of a project's location that holds `versions`, each copied
    whole, and lists them with the source `kind`."""
    root = project(tmp)
    folder = root / LOCATION / libraries.FOLDER
    entries: dict[str, Any] = {}
    for each in versions:
        target = folder / each.name / str(each.version)
        for path in each.files:
            copy = target / path.relative_to(each.source)
            copy.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, copy)
        library = entries.setdefault(each.name, {"source": {"kind": kind}, "versions": {}})
        library["versions"][str(each.version)] = dict(each.entry)
    write(folder / "libraries.yaml", yaml_text(bound("libraries", libraries=entries)))
    return libraries.Held(root, LOCATION)


def version_findings(held: Any, name: str, version: Any) -> list[Any]:
    """What reading a version the location `held` holds in full finds (`full_read.read`):
    each of its files against its schema, then the engine's read of it with the versions it
    is checked with, the newest version held of each major it builds on."""
    return list(full_read.read(held, name, version).findings)


# --- the checks ---------------------------------------------------------------------------------


def released_versions(folder: Path, outcome: Outcome) -> list[Any]:
    """Each released version the capability whose folder is `folder` ships, newest first
    within each library; what does not match the layout fails."""
    for stray in shipped.strays(folder):
        outcome.fail(stray)
    found = []
    for library in shipped.read(folder):
        for problem in library.problems():
            outcome.fail(problem)
        try:
            versions = library.released
        except shipped.ShippedError:
            continue  # among its problems
        found.extend(each for each in versions if each.place.is_dir())  # else a problem
    return found


def released_location(tmp: Path, versions: Sequence[Any]) -> Any:
    """A location that holds `versions`, released versions, each listed as its record
    keeps it."""
    copied = [
        Copied(each.name, each.version, each.place, tuple(each.files()), each.entry)
        for each in versions
    ]
    return location_of(tmp, copied, "shipped")


def released_outcome(tmp: Path, folder: Path) -> Outcome:
    """Check 1: each released version matches the hash its record keeps; each record and
    each file of the capability's format in it holds its schema; and the engine reads it,
    with the newest released version of each major it builds on."""
    outcome = Outcome()
    versions = released_versions(folder, outcome)
    for library in shipped.read(folder):
        if library.record.is_file():
            for finding in full_read.shape_findings(library.record, "libraries", "", folder):
                outcome.fail(said(finding, finding.level))
    for each in versions:
        changes = each.hash_changes()
        if changes:
            outcome.fail(
                f"`library-changed`: {each.label} no longer matches the hash "
                f"{shipped.RELEASES}/{each.name}/{shipped.RECORD} keeps: " + "; ".join(changes)
            )
    if versions:
        held = released_location(tmp, versions)
        for each in versions:
            judge(outcome, version_findings(held, each.name, each.version), released=True)
    return outcome


def history_outcome(root: Path, folder: Path) -> Outcome:
    """Check 2: no change touched the place of a released version's version being built
    between the release step's change that wrote the version of the capability it names
    and the change that brings it in, that change included; where no change on HEAD's
    first-parent line has brought it in yet, up to HEAD. `root` is the top of the
    repository the capability's folder `folder` lies in."""
    outcome = Outcome()
    for library in shipped.read(folder):
        try:
            versions = library.released
        except shipped.ShippedError as exc:
            outcome.fail(str(exc))
            continue
        built = library.built.relative_to(root).as_posix()
        for each in versions:
            try:
                needs = libraries.read_library(each.place).needs_release
            except libraries.LibraryError as exc:
                outcome.fail(f"{each.label}: {exc}")
                continue
            release = ".".join(map(str, needs))
            place = each.place.relative_to(root).as_posix()
            try:
                since = shipped.release_change(root, release)
                until = shipped.brought_in(root, place) or "HEAD"
                changes = shipped.changes_to(root, built, since, until)
            except shipped.HistoryRefused as exc:
                outcome.fail(f"{each.label}: {exc}")
                continue
            if changes:
                outcome.fail(
                    f"{each.label} names release {release}, but {len(changes)} change(s) "
                    f"touched {built} after the release step's change that wrote it, "
                    f"{since[:12]}, up to {until[:12]}, which brings it in: "
                    + ", ".join(change[:12] for change in changes)
                )
    return outcome


def together_outcome(tmp: Path, folder: Path) -> Outcome:
    """Check 3: the newest released versions read together, each on the newest released
    version of each major it builds on, as the capability's check reads the newest version
    of each major alone, in a location that holds every released version."""
    outcome = Outcome()
    versions = released_versions(folder, outcome)
    if versions:
        judge_report(outcome, checks.check(released_location(tmp, versions).root))
    return outcome


def built_versions(folder: Path, outcome: Outcome) -> list[Copied]:
    """The version being built of each library the capability whose folder is `folder`
    ships, each to be listed as a project's own library not yet released; one that cannot
    be read fails."""
    versions = []
    for library in shipped.read(folder):
        try:
            built = library.being_built()
        except libraries.LibraryError as exc:
            outcome.fail(f"`library-unreadable`: `{library.name}` being built: {exc}")
            continue
        found = tuple(listed(folder, library.built))
        unreleased = {"released": False}
        versions.append(Copied(library.name, built.version, library.built, found, unreleased))
    return versions


def built_outcome(tmp: Path, folder: Path) -> Outcome:
    """Check 4: each version being built, read and checked on the versions being built of
    its bases, in a location that lists each as a project's own library not yet released:
    each file against its schema, each read by the engine, and the capability's check."""
    outcome = Outcome()
    versions = built_versions(folder, outcome)
    if not versions:
        return outcome
    held = location_of(tmp, versions, "project")
    for each in versions:
        judge(outcome, version_findings(held, each.name, each.version), released=False)
    judge_report(outcome, checks.check(held.root))
    return outcome


def differences(folder: Path, built: Path, place: Path) -> list[str]:
    """How the version being built at `built` differs from the released version at `place`,
    each file read as its hash reads it, but for the release it needs."""
    ours = {path.relative_to(built).as_posix(): path for path in listed(folder, built)}
    theirs = {path.relative_to(place).as_posix(): path for path in listed(folder, place)}
    found = []
    for rel in sorted(set(ours) | set(theirs)):
        if rel not in theirs:
            found.append(f"`{rel}` is not in the released version")
        elif rel not in ours:
            found.append(f"`{rel}` of the released version is missing")
        elif rel == "library.yaml":
            if _but_release(ours[rel]) != _but_release(theirs[rel]):
                found.append(f"`{rel}` differs in more than the release it needs")
        elif fingerprint.reading(ours[rel]) != fingerprint.reading(theirs[rel]):
            found.append(f"`{rel}` differs")
    return found


def _but_release(path: Path) -> Any:
    data = reading.read_yaml(path)
    return {key: value for key, value in data.items() if key != "needs-release"}


def numbers_outcome(folder: Path) -> Outcome:
    """Check 5: a version being built that carries a released number differs from that
    released version only in the release it needs, and none carries a number below the
    newest released one."""
    outcome = Outcome()
    for library in shipped.read(folder):
        try:
            built = library.being_built()
            released = library.released
        except (libraries.LibraryError, shipped.ShippedError) as exc:
            outcome.fail(f"`{library.name}`: {exc}")
            continue
        newest = library.newest()
        if newest is not None and built.version < newest.version:
            outcome.fail(
                f"the version being built of `{library.name}` carries {built.version}, below "
                f"its newest released version, {newest.version}"
            )
        same = next((each for each in released if each.version == built.version), None)
        if same is not None:
            found = differences(folder, library.built, same.place)
            if found:
                outcome.fail(
                    f"the version being built of `{library.name}` carries the released number "
                    f"{built.version}, and differs from it: " + "; ".join(found) + ". Raise "
                    "its number first"
                )
    return outcome


def comparison_outcome(tmp: Path, folder: Path) -> Outcome:
    """Check 6: the release's comparison of each version being built with the newest
    released version of the major it carries, where that major has one (DEC-013 point 6).
    The released version is read on the newest released version of each major it builds
    on, and the version being built on the versions being built of its bases. The version
    being built keeps that major, so each break the comparison finds fails. Each addition
    is reported, and fails nothing."""
    outcome = Outcome()
    compared = []
    for library in shipped.read(folder):
        try:
            built = library.being_built()
            newest = library.newest_of_majors().get(built.version.major)
        except (libraries.LibraryError, shipped.ShippedError):
            continue  # checks 1 and 4 fail it
        if newest is not None:
            compared.append((library.name, newest.version, built.version))
    if not compared:
        return outcome
    released = released_location(tmp / "released", released_versions(folder, Outcome()))
    being_built = location_of(tmp / "built", built_versions(folder, Outcome()), "project")
    for name, was, now in compared:
        try:
            found = comparison.compare(
                full_read.read(released, name, was), full_read.read(being_built, name, now)
            )
        except comparison.ComparisonError as exc:
            outcome.fail(f"the comparison of `{name}` {was} with {now} cannot be made: {exc}")
            continue
        for change in found.breaks:
            outcome.fail(
                f"`{name}` {now} keeps the major of its released version {was}, and breaks it: "
                f"{change}"
            )
        for change in found.additions:
            outcome.report(f"`{name}` {now} adds to its released version {was}: {change}")
    return outcome


# --- the checks, on the tree and the history as the clone holds them ----------------------------


def test_each_released_version_matches_its_hash_and_the_engine_reads_it(tmp_path: Path) -> None:
    outcome = released_outcome(tmp_path, CAPABILITY)
    outcome.show("released versions")
    assert outcome.failures == []


def test_every_released_version_was_untouched_since_the_release_it_names() -> None:
    outcome = history_outcome(REPO, CAPABILITY)
    assert outcome.failures == []


def test_the_newest_released_versions_read_together_on_released_bases(tmp_path: Path) -> None:
    outcome = together_outcome(tmp_path, CAPABILITY)
    outcome.show("released versions together")
    assert outcome.failures == []


def test_each_version_being_built_reads_and_checks_clean_on_its_bases(tmp_path: Path) -> None:
    outcome = built_outcome(tmp_path, CAPABILITY)
    outcome.show("versions being built")
    assert outcome.failures == []


def test_a_version_being_built_keeps_to_its_released_numbers() -> None:
    outcome = numbers_outcome(CAPABILITY)
    assert outcome.failures == []


def test_a_version_being_built_breaks_nothing_its_released_major_promises(tmp_path: Path) -> None:
    outcome = comparison_outcome(tmp_path, CAPABILITY)
    outcome.show("versions being built against their released majors")
    assert outcome.failures == []


def test_the_labels_that_fail_at_any_level_are_labels_the_check_reports() -> None:
    """Each label of the list is one the capability's code raises, and a label left to its
    level is not among them."""
    code = "\n".join(
        path.read_text(encoding="utf-8") for path in (CAPABILITY / "scripts" / "_lib").glob("*.py")
    )
    unknown = {label for label in FAILS_AT_ANY_LEVEL if f'"{label}"' not in code}
    assert unknown == set()
    assert not FAILS_AT_ANY_LEVEL & set(LEFT_TO_LEVEL)


# --- a folder the tests build -------------------------------------------------------------------

#: A component the engine reads, whose height has the wrong dimension: a finding the check
#: fails in a version being built, and reports in a released one.
SQUARED = bound(
    "component",
    status="experimental",
    about="A box whose height squares a length.",
    parts={
        "box": {"box": {"fill": "background"}, "width": "=:width", "height": "=@space.3 * @space.3"}
    },
)

#: A component whose width the engine cannot read, though its schema holds.
UNFINISHED = bound(
    "component",
    status="experimental",
    about="A box whose width is not finished.",
    parts={"box": {"box": {"fill": "background"}, "width": "=:width +", "height": "=:height"}},
)


def capability(tmp: Path) -> Path:
    """A capability's folder that builds the foundations, as the tree holds them."""
    folder = tmp / "capability"
    shutil.copytree(FOUNDATIONS, folder / libraries.FOLDER / libraries.FOUNDATIONS)
    return folder


def built(folder: Path, name: str = libraries.FOUNDATIONS) -> Path:
    return folder / libraries.FOLDER / name


def add_component(folder: Path, component: Mapping[str, Any], name: str, library: str) -> None:
    write(built(folder, library) / pl.COMPONENTS / f"{name}.yaml", yaml_text(component))


def set_fields(path: Path, **fields: Any) -> None:
    """A YAML file with `fields` set, its other keys kept."""
    data = dict(reading.read_yaml(path))
    data.update(fields)
    write(path, yaml_text(data))


def add_library(folder: Path, name: str, builds_on: Mapping[str, int], version: str) -> None:
    """A component library being built, from its fields alone."""
    library = bound(
        "library",
        name=name,
        version=version,
        kind="components",
        **{
            "needs-release": "0.1.0",
            "builds-on": [{"name": n, "major": m} for n, m in builds_on.items()],
        },
    )
    write(built(folder, name) / "library.yaml", yaml_text(library))


def release(folder: Path, name: str = libraries.FOUNDATIONS) -> Any:
    """Release the version being built of `name` as it stands: its files copied to its place,
    and its entry added to its record."""
    version = libraries.read_library(built(folder, name)).version
    place = shipped.place_of(folder, name, version)
    shutil.copytree(built(folder, name), place)
    rewrite_entry(folder, name, version)
    return version


def rewrite_entry(folder: Path, name: str, version: Any) -> None:
    """The record's entry of a released version, worked out again from its place."""
    record = folder / shipped.RELEASES / name / shipped.RECORD
    if record.is_file():
        data = reading.read_yaml(record)
    else:
        library = {"source": {"kind": "shipped"}, "versions": {}}
        data = bound("libraries", libraries={name: library})
    data["libraries"][name]["versions"][str(version)] = shipped.entry_of(folder, name, version)
    write(record, yaml_text(data))


def place(folder: Path, name: str = libraries.FOUNDATIONS, version: str = "1.0.0") -> Path:
    return shipped.place_of(folder, name, libraries.Version.parse(version))


def test_a_folder_that_releases_nothing_passes_every_check(tmp_path: Path) -> None:
    folder = capability(tmp_path)

    assert released_outcome(tmp_path / "1", folder) == Outcome()
    assert together_outcome(tmp_path / "2", folder) == Outcome()
    assert built_outcome(tmp_path / "3", folder) == Outcome()
    assert numbers_outcome(folder) == Outcome()


def test_a_released_version_as_its_record_keeps_it_passes(tmp_path: Path) -> None:
    folder = capability(tmp_path)
    release(folder)

    [library] = shipped.read(folder)
    [released] = library.released
    assert (str(released.version), released.place) == ("1.0.0", place(folder))
    assert library.newest_of_majors() == {1: released}
    assert reading.read_yaml(library.record)["libraries"] == {
        "foundations": {"source": {"kind": "shipped"}, "versions": {"1.0.0": released.entry}}
    }
    assert released_outcome(tmp_path / "1", folder) == Outcome()
    assert together_outcome(tmp_path / "2", folder) == Outcome()
    assert numbers_outcome(folder) == Outcome()


def test_a_released_file_changed_fails(tmp_path: Path) -> None:
    folder = capability(tmp_path)
    release(folder)
    set_fields(place(folder) / "components" / "figure.yaml", about="Changed after its release.")

    [failure] = released_outcome(tmp_path, folder).failures

    assert failure.startswith("`library-changed`: foundations@1.0.0 no longer matches the hash")
    assert "`components/figure.yaml` of foundations@1.0.0 changed" in failure


def test_a_released_file_its_schema_refuses_fails(tmp_path: Path) -> None:
    folder = capability(tmp_path)
    release(folder)
    set_fields(place(folder) / "library.yaml", origin="the tests")
    rewrite_entry(folder, "foundations", libraries.Version(1, 0, 0))

    [failure] = released_outcome(tmp_path, folder).failures

    assert failure.startswith(
        "`schema-refused` (attention) at visual/libraries/foundations/1.0.0/library.yaml in "
        "foundations@1.0.0: the schema `library` refuses it at /: Additional properties"
    )


def test_a_released_record_its_schema_refuses_fails(tmp_path: Path) -> None:
    folder = capability(tmp_path)
    release(folder)
    record = folder / "releases" / "foundations" / "releases.yaml"
    data = reading.read_yaml(record)
    data["libraries"]["foundations"]["origin"] = "the tests"
    write(record, yaml_text(data))

    [failure] = released_outcome(tmp_path, folder).failures

    assert failure.startswith(
        "`schema-refused` (fails) at releases/foundations/releases.yaml: the schema "
        "`libraries` refuses it at /libraries/foundations: Additional properties"
    )


def test_a_released_component_the_engine_cannot_read_fails_and_another_finding_is_reported(
    tmp_path: Path,
) -> None:
    folder = capability(tmp_path)
    add_component(folder, UNFINISHED, "unfinished", "foundations")
    add_component(folder, SQUARED, "squared", "foundations")
    release(folder)

    outcome = released_outcome(tmp_path, folder)

    assert outcome.failures == [
        "`formula-unreadable` (attention) at foundations/unfinished#parts.box.width in "
        "foundations@1.0.0: foundations/unfinished: the formula `=:width +` ends too early"
    ]
    assert outcome.reported == [
        "`formula-dimension` (attention) at foundations/squared#parts.box.height in "
        "foundations@1.0.0: foundations/squared: the formula `=@space.3 * @space.3` gives "
        "a length to the power 2 where a length belongs"
    ]


def test_a_picture_file_the_engine_does_not_read_fails_released_or_being_built(
    tmp_path: Path,
) -> None:
    """The full read reads each picture file a version holds (DEC-014 point 1), and one it
    refuses breaks a released version's promise as a component it cannot read does."""
    folder = capability(tmp_path)
    picture = built(folder) / "pictures" / "deep.png"
    picture.parent.mkdir()
    shutil.copyfile(TEST_PICTURES / "deep.png", picture)
    said = (
        "at visual/libraries/foundations/1.0.0/pictures/deep.png in foundations@1.0.0: "
        "`deep.png` is a PNG of 16 bits for each sample, which the capability does not read"
    )

    assert built_outcome(tmp_path / "1", folder).failures == [f"`picture-encoding` (fails) {said}"]
    release(folder)
    assert released_outcome(tmp_path / "2", folder).failures == [
        f"`picture-encoding` (attention) {said}"
    ]


def test_released_versions_that_do_not_read_together_fail(tmp_path: Path) -> None:
    """The library builds on a major of the foundations that no released version is of."""
    folder = capability(tmp_path)
    release(folder)
    add_library(folder, "parts", {"foundations": 2}, "1.0.0")
    release(folder, "parts")

    failures = together_outcome(tmp_path, folder).failures

    assert [failure.split(" (")[0] for failure in failures] == ["`alone-missing`"]
    assert "parts@1.0.0 builds on `foundations` 2" in failures[0]


def test_a_finding_in_a_version_being_built_fails(tmp_path: Path) -> None:
    folder = capability(tmp_path)
    add_component(folder, SQUARED, "squared", "foundations")

    outcome = built_outcome(tmp_path, folder)

    assert outcome.failures == [
        "`formula-dimension` (fails) at foundations/squared#parts.box.height in "
        "foundations@1.0.0: foundations/squared: the formula `=@space.3 * @space.3` gives "
        "a length to the power 2 where a length belongs"
    ]


def test_a_version_being_built_is_read_on_the_versions_being_built_of_its_bases(
    tmp_path: Path,
) -> None:
    """A library built on the foundations' next major, which only their version being
    built carries, while their released version is of major 1."""
    folder = capability(tmp_path)
    release(folder)
    set_fields(built(folder) / "library.yaml", version="2.0.0")
    add_library(folder, "parts", {"foundations": 2}, "1.0.0")

    assert built_outcome(tmp_path, folder) == Outcome()


def test_a_version_being_built_that_carries_a_released_number_with_other_files_fails(
    tmp_path: Path,
) -> None:
    folder = capability(tmp_path)
    release(folder)
    set_fields(built(folder) / "components" / "figure.yaml", about="Changed since its release.")
    add_component(folder, SQUARED, "squared", "foundations")

    [failure] = numbers_outcome(folder).failures

    assert failure == (
        "the version being built of `foundations` carries the released number 1.0.0, and "
        "differs from it: `components/figure.yaml` differs; `components/squared.yaml` is not "
        "in the released version. Raise its number first"
    )


def test_a_version_being_built_may_differ_from_its_released_number_in_the_release_it_needs(
    tmp_path: Path,
) -> None:
    folder = capability(tmp_path)
    release(folder)
    library = built(folder) / "library.yaml"
    library.write_text(
        library.read_text(encoding="utf-8").replace("needs-release: 0.1.0", "needs-release: 0.0.9"),
        encoding="utf-8",
    )

    assert numbers_outcome(folder) == Outcome()


def test_a_version_being_built_below_the_newest_released_number_fails(tmp_path: Path) -> None:
    folder = capability(tmp_path)
    set_fields(built(folder) / "library.yaml", version="1.1.0")
    release(folder)
    set_fields(built(folder) / "library.yaml", version="1.0.1")

    assert numbers_outcome(folder).failures == [
        "the version being built of `foundations` carries 1.0.1, below its newest released "
        "version, 1.1.0"
    ]


def test_a_released_place_or_a_record_entry_alone_fails(tmp_path: Path) -> None:
    folder = capability(tmp_path)
    release(folder)
    shutil.copytree(place(folder), place(folder, version="1.0.1"))
    shutil.rmtree(place(folder))
    write(folder / "releases" / "starter" / "1.0.0" / "library.yaml", "")

    failures = released_outcome(tmp_path, folder).failures

    assert failures[:3] == [
        "releases/starter names no library the capability builds: a released version lies "
        "beside its library's version being built",
        "releases/foundations/releases.yaml lists foundations@1.0.0, whose place "
        "releases/foundations/1.0.0/ is missing",
        "releases/foundations/1.0.1/ is no released version releases/foundations/releases.yaml "
        "lists: list it, or take the folder out",
    ]


#: A stable component the engine reads: a line of text, and a note below it.
LABEL = bound(
    "component",
    status="stable",
    about="A line of text, and a note below it.",
    fields={
        "type": "object",
        "properties": {"text": {"type": "string"}, "note": {"type": "string"}},
    },
    parts={
        "text": {
            "text": {"content": "text", "style": "type.body", "fill": "text-primary"},
            "width": "=:width",
        },
        "note": {
            "when": "note",
            "text": {"content": "note", "style": "type.body", "fill": "text-secondary"},
            "y": "=text.bottom",
            "width": "=:width",
        },
    },
)

#: An experimental component the engine reads.
BADGE = bound(
    "component",
    status="experimental",
    about="A badge.",
    parts={"box": {"box": {"fill": "accent"}, "width": "=:width", "height": "=:height"}},
)


def without_note(folder: Path) -> None:
    """The label being built, its field `note` removed, and the part that shows it."""
    path = built(folder) / pl.COMPONENTS / "label.yaml"
    data = reading.read_yaml(path)
    del data["fields"]["properties"]["note"]
    del data["parts"]["note"]
    write(path, yaml_text(data))


def test_a_version_being_built_that_breaks_its_released_major_fails(tmp_path: Path) -> None:
    """A stable component's field removed in a minor fails; in a major, its major has no
    released version to compare with."""
    folder = capability(tmp_path)
    add_component(folder, LABEL, "label", "foundations")
    release(folder)
    without_note(folder)
    set_fields(built(folder) / "library.yaml", version="1.1.0")

    minor = comparison_outcome(tmp_path / "minor", folder)
    set_fields(built(folder) / "library.yaml", version="2.0.0")
    major = comparison_outcome(tmp_path / "major", folder)

    assert minor.failures == [
        "`foundations` 1.1.0 keeps the major of its released version 1.0.0, and breaks it: "
        "`foundations/label`, field `note`: is removed (DEC-003 point 6)"
    ]
    assert major == Outcome()


def test_a_version_being_built_that_adds_an_experimental_component_in_a_patch_passes(
    tmp_path: Path,
) -> None:
    """Whether the change is a patch or a minor is the owner's judgement, so the addition is
    reported and fails nothing."""
    folder = capability(tmp_path)
    add_component(folder, LABEL, "label", "foundations")
    release(folder)
    add_component(folder, BADGE, "badge", "foundations")
    set_fields(built(folder) / "library.yaml", version="1.0.1")

    outcome = comparison_outcome(tmp_path, folder)

    assert outcome == Outcome(
        reported=[
            "`foundations` 1.0.1 adds to its released version 1.0.0: `foundations/badge`: is "
            "new (DEC-003 point 1)"
        ]
    )


def test_a_version_being_built_that_cannot_be_compared_fails(tmp_path: Path) -> None:
    """The version being built of a library builds on a major of the foundations that
    nothing builds, so it cannot be read with its bases."""
    folder = capability(tmp_path)
    release(folder)
    add_library(folder, "parts", {"foundations": 1}, "1.0.0")
    release(folder, "parts")
    add_library(folder, "parts", {"foundations": 2}, "1.1.0")

    [failure] = comparison_outcome(tmp_path, folder).failures

    assert failure.startswith(
        "the comparison of `parts` 1.0.0 with 1.1.0 cannot be made: parts@1.1.0 cannot be "
        "compared: parts@1.1.0 cannot be read with its bases"
    )


# --- a history the tests build ------------------------------------------------------------------


class History:
    """A repository the tests build, whose capability's folder builds the foundations: a
    commit at a time, never signed."""

    def __init__(self, tmp: Path) -> None:
        self.root = tmp / "repository"
        self.root.mkdir()
        self.folder = capability(self.root)
        self.git("init", "-q", "-b", "main")
        write(self.root / shipped.CHANGELOG, "# Changelog\n")
        self.commit("the capability")

    @property
    def built(self) -> str:
        return built(self.folder).relative_to(self.root).as_posix()

    def git(self, *args: str) -> str:
        done = subprocess.run(
            [
                "git",
                "-c",
                "commit.gpgsign=false",
                "-c",
                "user.name=Tests",
                "-c",
                "user.email=tests@example.com",
                *args,
            ],
            cwd=self.root,
            check=True,
            capture_output=True,
            text=True,
        )
        return done.stdout.strip()

    def commit(self, message: str) -> str:
        self.git("add", "-A")
        self.git("commit", "-q", "--no-verify", "--allow-empty", "-m", message)
        return self.git("rev-parse", "HEAD")

    def release_step(self, version: str = "0.1.0") -> str:
        """The release step's change that writes `version` of the capability."""
        changelog = self.root / shipped.CHANGELOG
        entry = f"- **visual-communication {version}** — A release.\n"
        changelog.write_text(changelog.read_text(encoding="utf-8") + entry, encoding="utf-8")
        return self.commit(f"chore(release): visual-communication {version}")

    def change(self, about: str = "A change.") -> str:
        """A change to the foundations' version being built."""
        set_fields(built(self.folder) / "components" / "figure.yaml", about=about)
        return self.commit(f"a change: {about}")

    def take_back(self) -> str:
        self.git("revert", "--no-edit", "HEAD")
        return self.git("rev-parse", "HEAD")

    def elsewhere(self, name: str) -> str:
        """A change outside the version being built."""
        write(self.root / f"{name}.txt", name)
        return self.commit(f"elsewhere: {name}")

    def release(self) -> str:
        release(self.folder)
        return self.commit("release foundations 1.0.0")

    def outcome(self) -> Outcome:
        return history_outcome(self.root, self.folder)


def test_a_version_untouched_since_the_release_it_names_passes(tmp_path: Path) -> None:
    history = History(tmp_path)
    history.change("Before the release step.")
    step = history.release_step()
    history.elsewhere("other")
    brought = history.release()
    history.change("After the release.")

    assert history.outcome() == Outcome()
    assert shipped.release_change(history.root, "0.1.0") == step
    assert shipped.brought_in(history.root, "capability/releases/foundations/1.0.0") == brought


def test_a_change_to_the_version_being_built_since_the_release_it_names_fails(
    tmp_path: Path,
) -> None:
    history = History(tmp_path)
    step = history.release_step()
    change = history.change()
    brought = history.release()

    [failure] = history.outcome().failures

    assert failure == (
        f"foundations@1.0.0 names release 0.1.0, but 1 change(s) touched "
        f"capability/libraries/foundations after the release step's change that wrote it, "
        f"{step[:12]}, up to {brought[:12]}, which brings it in: {change[:12]}"
    )


def test_a_change_the_release_itself_makes_to_the_version_being_built_fails(
    tmp_path: Path,
) -> None:
    history = History(tmp_path)
    history.release_step()
    release(history.folder)
    set_fields(built(history.folder) / "components" / "figure.yaml", about="With the release.")
    brought = history.commit("release foundations 1.0.0, and change it")

    [failure] = history.outcome().failures

    assert failure.endswith(f"which brings it in: {brought[:12]}")


@pytest.mark.parametrize("taken_back", [False, True], ids=["kept", "taken-back"])
@pytest.mark.parametrize("side", ["first", "second"])
def test_a_change_on_either_side_of_a_merge_inside_the_window_fails(
    tmp_path: Path, side: str, taken_back: bool
) -> None:
    """The change, and its take-back, lie on one side of a merge; the other side changes
    something else. A merge that brings the change to the other side is listed too."""
    history = History(tmp_path)
    history.release_step()
    history.git("checkout", "-q", "-b", "side")
    if side == "second":
        changed = [history.change()]
        if taken_back:
            changed.append(history.take_back())
        history.git("checkout", "-q", "main")
        history.elsewhere("main")
    else:
        history.elsewhere("side")
        history.git("checkout", "-q", "main")
        changed = [history.change()]
        if taken_back:
            changed.append(history.take_back())
    history.git("merge", "-q", "--no-ff", "--no-edit", "side")
    history.release()

    [failure] = history.outcome().failures

    assert {change[:12] for change in changed} <= set(failure.rpartition(": ")[2].split(", "))


def test_a_change_taken_back_on_the_merged_side_is_found_only_with_the_full_history(
    tmp_path: Path,
) -> None:
    """Without `--full-history`, git prunes the merged side, whose result its merge does not
    keep."""
    history = History(tmp_path)
    step = history.release_step()
    history.git("checkout", "-q", "-b", "side")
    changed = {history.change(), history.take_back()}
    history.git("checkout", "-q", "main")
    history.elsewhere("main")
    history.git("merge", "-q", "--no-ff", "--no-edit", "side")
    head = history.git("rev-parse", "HEAD")

    pruned = history.git("log", "--format=%H", f"{step}..{head}", "--", history.built)

    assert pruned == ""
    assert set(shipped.changes_to(history.root, history.built, step, head)) == changed


def test_a_released_place_taken_back_and_released_again_is_read_from_its_last_release(
    tmp_path: Path,
) -> None:
    history = History(tmp_path)
    history.release_step()
    history.release()
    change = history.change()
    shutil.rmtree(history.folder / "releases")
    history.commit("take the release back")
    brought = history.release()

    [failure] = history.outcome().failures

    assert shipped.brought_in(history.root, "capability/releases/foundations/1.0.0") == brought
    assert failure.endswith(f"up to {brought[:12]}, which brings it in: {change[:12]}")


def test_a_release_brought_in_by_a_merge_is_read_up_to_the_merge(tmp_path: Path) -> None:
    history = History(tmp_path)
    history.release_step()
    history.git("checkout", "-q", "-b", "release")
    history.release()
    history.git("checkout", "-q", "main")
    history.elsewhere("main")
    history.git("merge", "-q", "--no-ff", "--no-edit", "release")
    merge = history.git("rev-parse", "HEAD")

    assert shipped.brought_in(history.root, "capability/releases/foundations/1.0.0") == merge
    assert history.outcome() == Outcome()


def test_a_release_brought_in_before_the_release_it_names_fails(tmp_path: Path) -> None:
    history = History(tmp_path)
    brought = history.release()
    step = history.release_step()

    assert history.outcome().failures == [
        f"foundations@1.0.0: the change {step} does not lead to the change {brought}"
    ]


def test_a_release_the_history_does_not_record_fails(tmp_path: Path) -> None:
    """The capability's version was stamped by hand: no changelog's entry names it."""
    history = History(tmp_path)
    write(history.root / "package.yaml", "version: 0.1.0\n")
    history.commit("stamp 0.1.0 by hand")
    history.release()

    assert history.outcome().failures == [
        "foundations@1.0.0: the history records no release of visual-communication 0.1.0: no "
        "change on HEAD's first-parent line adds the entry `**visual-communication 0.1.0**` "
        "to CHANGELOG.md"
    ]


def test_the_release_change_is_the_one_that_added_the_entry_on_the_first_parent_line(
    tmp_path: Path,
) -> None:
    """The entry is added on a merged side, and a later change adds a second entry tagged
    with the same version."""
    history = History(tmp_path)
    history.git("checkout", "-q", "-b", "release")
    history.release_step()
    history.git("checkout", "-q", "main")
    history.elsewhere("main")
    history.git("merge", "-q", "--no-ff", "--no-edit", "release")
    merge = history.git("rev-parse", "HEAD")
    history.release_step()

    assert shipped.release_change(history.root, "0.1.0") == merge


def test_a_history_that_is_not_at_hand_fails(tmp_path: Path) -> None:
    history = History(tmp_path)
    history.release_step()
    history.release()
    clone = tmp_path / "shallow"
    source = history.root.as_uri()
    subprocess.run(
        ["git", "clone", "-q", "--depth", "1", source, str(clone)], check=True, capture_output=True
    )

    failures = history_outcome(clone, clone / "capability").failures

    assert failures == [
        "foundations@1.0.0: the clone is shallow, so the history is not at hand: fetch it "
        "whole, as a checkout with `fetch-depth: 0` does"
    ]
    with pytest.raises(shipped.HistoryMissing, match="holds no history git can read"):
        shipped.release_change(tmp_path, "0.1.0")
    with pytest.raises(shipped.HistoryMissing, match="is not in the history at hand"):
        shipped.changes_to(history.root, history.built, "0" * 40)
