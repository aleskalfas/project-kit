"""The library folder, its list, versions, and a piece's lock (DEC-001 point 5, DEC-003
points 1, 4, 8 and 9, DEC-004 point 6); a lock's proposed move (DEC-019 point 7); the level
of a version the installed capability cannot read, released or not (DEC-002 point 7, DEC-014
point 5); what the command that brings a shipped library in reads of the locks and of the
capability's folder (DEC-013 point 5); and what the check finds of a copy of a library the
capability ships, against a capability's folder the test controls (DEC-013 point 6). Each
project is laid in the test's own folder, outside git, so its files are listed by walking."""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Any

import pytest

from tests.in_process import load
from tests.visual_communication_project import (
    CAPABILITY,
    FOUNDATIONS,
    RELEASED_FOUNDATIONS,
    TEST_BRAND,
    TEST_EDITION,
    add_library,
    bound,
    built_as_released,
    copy_library,
    project,
    version_folder,
    write,
    write_list,
    write_piece,
    yaml_text,
)

libraries, fingerprint, files, reading, checks, pl, copies, shipped = load(
    "visual-communication",
    "libraries",
    "fingerprint",
    "files",
    "reading",
    "checks",
    "pipeline",
    "copies",
    "shipped",
)

V = libraries.Version.parse
RELEASE = (0, 1, 0)
#: The installed capability's release, which the foundations' released version reads at.
INSTALLED = libraries.installed_release()
PROJECT = {"kind": "project"}
UNRELEASED = {"released": False}


def held(root: Path, release: tuple[int, int, int] = RELEASE) -> Any:
    return libraries.Held(root, "visual", release)


def codes(found: Any) -> list[str]:
    return [finding.code for finding in found]


def released_entry(root: Path, name: str, version: str) -> dict[str, Any]:
    """The list's entry of a released version, its fingerprint over its folder as it is."""
    folder = version_folder(root, name, version)
    files = sorted(path for path in folder.rglob("*") if path.is_file())
    inputs = fingerprint.library_version_inputs(
        library=name, version=version, folder=folder, files=files
    )
    return {"released": True, "hash": fingerprint.fingerprint(inputs)}


# --- versions -----------------------------------------------------------------------------------


def test_a_version_is_x_y_z_with_x_at_least_1_and_orders_by_number() -> None:
    assert V("1.10.0") > V("1.9.3") > V("1.0.0")
    assert str(V("2.0.1")) == "2.0.1"
    assert V("2.0.1").major == 2


@pytest.mark.parametrize("text", ["0.1.0", "1.0", "01.0.0", "1.0.0-rc.1", "v1.0.0", 1, None])
def test_what_is_not_a_library_version(text: object) -> None:
    with pytest.raises(ValueError):
        V(text)


def test_a_release_of_the_capability_may_have_major_0() -> None:
    assert libraries.release_of("0.1.0") == (0, 1, 0)
    with pytest.raises(ValueError):
        libraries.release_of("0.1")


def test_the_installed_release_is_the_packages_version() -> None:
    text = (CAPABILITY / "package.yaml").read_text(encoding="utf-8")
    match = re.search(r"^  version: (\S+)$", text, re.MULTILINE)
    assert match is not None
    assert libraries.installed_release() == libraries.release_of(match.group(1))


# --- a library version --------------------------------------------------------------------------


def test_the_shipped_foundations_and_the_test_brand_read() -> None:
    foundations = libraries.read_library(FOUNDATIONS)
    assert (foundations.name, foundations.version, foundations.kind) == (
        "foundations",
        V("1.1.0"),
        "components",
    )
    assert foundations.needs_release == (0, 1, 0)
    assert foundations.builds_on == ()
    brand = libraries.read_library(TEST_BRAND)
    assert brand.kind == "brand"
    assert brand.builds_on == (libraries.BuildsOn("foundations", 1),)
    assert brand.label == "test-brand@1.0.0"
    assert brand.base is None


def test_a_brand_marks_the_brand_it_builds_on_as_its_base() -> None:
    edition = libraries.read_library(TEST_EDITION)
    assert edition.builds_on == (
        libraries.BuildsOn("foundations", 1),
        libraries.BuildsOn("test-brand", 1, base=True),
    )
    assert edition.base == libraries.BuildsOn("test-brand", 1, base=True)


LIBRARY_TEXT = (
    "pkit_schema: visual-communication:library\nschema_version: 1\nname: x\n"
    "version: 1.0.0\nkind: components\nneeds-release: 0.1.0\nbuilds-on: []\n"
)
TWO_BASES = "builds-on: [{name: alpha, major: 1, base: true}, {name: beta, major: 1, base: true}]"


@pytest.mark.parametrize(
    ("old", "new", "said"),
    [
        ("name: x", "name: X", "`name`"),
        ("kind: components", "kind: palette", "`kind`"),
        ("version: 1.0.0", "version: 0.1.0", "X at least 1"),
        ("needs-release: 0.1.0", "needs-release: next", "is not a release"),
        ("builds-on: []", "builds-on: {}", "not a list"),
        ("builds-on: []", "builds-on: [{name: alpha, major: 0}]", "a major from 1"),
        ("builds-on: []", "builds-on: [{name: alpha, major: true}]", "a major from 1"),
        ("builds-on: []", "builds-on: [{name: alpha, major: 1, base: no}]", "`base: true`"),
        ("builds-on: []", "builds-on: [{name: alpha, major: 1, base: true}]", "only a brand"),
        ("schema_version: 1", "schema_version: 2", "format 2"),
    ],
)
def test_a_library_file_the_capability_cannot_read_is_refused(
    tmp_path: Path, old: str, new: str, said: str
) -> None:
    assert old in LIBRARY_TEXT
    write(tmp_path / "library.yaml", LIBRARY_TEXT.replace(old, new))
    with pytest.raises(libraries.LibraryError, match=said):
        libraries.read_library(tmp_path)


def test_a_brand_has_at_most_one_base(tmp_path: Path) -> None:
    brand = LIBRARY_TEXT.replace("kind: components", "kind: brand")
    write(tmp_path / "library.yaml", brand.replace("builds-on: []", TWO_BASES))
    with pytest.raises(libraries.LibraryError, match="`alpha`, `beta` as bases"):
        libraries.read_library(tmp_path)


# --- what the location holds --------------------------------------------------------------------


def test_the_versions_held_are_listed_newest_first(tmp_path: Path) -> None:
    root = project(tmp_path)
    for version in ("1.0.0", "1.10.0", "1.9.0"):
        add_library(root, "charts", version)
    add_library(root, "arrows", "2.0.0")
    write(version_folder(root, "charts", "1.9.0") / "components" / "bar.yaml", "")
    found = held(root)
    assert found.names() == ["arrows", "charts"]
    assert found.versions("charts") == [V("1.10.0"), V("1.9.0"), V("1.0.0")]
    assert found.versions("none") == []
    assert [p.name for p in found.files("charts", V("1.9.0"))] == ["bar.yaml", "library.yaml"]
    assert found.list_path == "visual/libraries/libraries.yaml"


def test_a_version_the_capability_cannot_read_says_why(tmp_path: Path) -> None:
    root = project(tmp_path)
    add_library(root, "charts", "1.0.0", needs_release="0.2.0")
    folder = add_library(root, "arrows", "1.0.0")
    (folder / "library.yaml").write_text(
        (folder / "library.yaml").read_text(encoding="utf-8").replace("1.0.0", "1.1.0"),
        encoding="utf-8",
    )
    found = held(root)
    assert "needs release 0.2.0" in (found.unreadable("charts", V("1.0.0")) or "")
    assert held(root, (0, 2, 0)).unreadable("charts", V("1.0.0")) is None
    assert "lies in the folder of arrows@1.0.0" in (found.unreadable("arrows", V("1.0.0")) or "")
    assert "holds no version 2.0.0" in (found.unreadable("charts", V("2.0.0")) or "")


# --- the list's findings ------------------------------------------------------------------------


def test_a_folder_listed_whole_has_no_findings(tmp_path: Path) -> None:
    root = project(tmp_path)
    add_library(root, "charts", "1.0.0")
    add_library(root, "charts", "1.1.0")
    write_list(
        root,
        {
            "charts": {
                "source": {"kind": "repository", "url": "https://example.org/c.git", "ref": "v1"},
                "versions": {"1.0.0": released_entry(root, "charts", "1.0.0"), "1.1.0": UNRELEASED},
            }
        },
    )
    listed = reading.read_yaml(root / "visual" / "libraries" / "libraries.yaml")
    assert files.shape_problems(listed, "libraries") == []
    found = held(root)
    assert found.findings() == []
    assert found.released("charts", V("1.0.0"))
    assert not found.released("charts", V("1.1.0"))


def test_an_empty_location_has_no_findings(tmp_path: Path) -> None:
    assert held(project(tmp_path)).findings() == []


def test_versions_but_no_list_is_a_finding(tmp_path: Path) -> None:
    root = project(tmp_path)
    add_library(root, "charts", "1.0.0")
    assert codes(held(root).findings()) == ["list-missing"]


def test_a_list_that_cannot_be_read_is_a_finding(tmp_path: Path) -> None:
    root = project(tmp_path)
    write(root / "visual" / "libraries" / "libraries.yaml", "libraries: [\n")
    assert codes(held(root).findings()) == ["list-unreadable"]


def test_the_list_and_the_folder_must_agree(tmp_path: Path) -> None:
    root = project(tmp_path)
    add_library(root, "charts", "1.0.0")
    add_library(root, "arrows", "1.0.0", needs_release="9.0.0")
    write(root / "visual" / "libraries" / "charts" / "latest" / "library.yaml", "")
    write_list(
        root,
        {
            "arrows": {"source": PROJECT, "versions": {"1.0.0": UNRELEASED}},
            "charts": {"source": PROJECT, "versions": {"2.0.0": UNRELEASED}},
        },
    )
    found = held(root).findings()
    assert codes(found) == [
        "library-folder",
        "library-unreadable",
        "version-unlisted",
        "version-missing",
    ]
    assert found[0].file == "visual/libraries/charts/latest"
    assert (found[1].library, found[1].who) == ("", "the project")
    assert found[3].where == "libraries.charts.versions.2.0.0"


def unreadable_version(root: Path, cause: str) -> None:
    """`charts@1.0.0`, held, with the cause of `library-unreadable` that `cause` names:
    `file` a `library.yaml` that cannot be read, `other` one that names another library
    than its folder, `newer` one that needs a newer release than the installed capability."""
    folder = add_library(
        root, "charts", "1.0.0", needs_release="9.0.0" if cause == "newer" else "0.1.0"
    )
    file = folder / "library.yaml"
    if cause == "file":
        write(file, "name: [\n")
    elif cause == "other":
        text = file.read_text(encoding="utf-8")
        assert "name: charts\n" in text
        write(file, text.replace("name: charts\n", "name: arrows\n"))


def unreadable_as_checked(tmp_path: Path, cause: str, released: bool) -> tuple[Any, str]:
    """The `library-unreadable` finding the check gives `charts@1.0.0` with `cause`, held
    released where `released` says so and still as it was released, with its level."""
    root = project(tmp_path)
    unreadable_version(root, cause)
    entry = released_entry(root, "charts", "1.0.0") if released else UNRELEASED
    write_list(root, {"charts": {"source": PROJECT, "versions": {"1.0.0": entry}}})
    report = checks.check(root)
    assert "library-changed" not in [finding.code for finding, _ in report.judged]
    (judged,) = [(f, level) for f, level in report.judged if f.code == "library-unreadable"]
    return judged


@pytest.mark.parametrize("released", [False, True], ids=["not-released", "released"])
@pytest.mark.parametrize("cause", ["file", "other"])
def test_a_library_yaml_not_read_as_its_folder_names_it_asks_its_owner_once_released(
    tmp_path: Path, cause: str, released: bool
) -> None:
    finding, level = unreadable_as_checked(tmp_path, cause, released)
    assert finding.library == "charts@1.0.0"
    if released:
        owner = "the owner of `charts`, who corrects it in a new release"
        assert (level, finding.who) == ("attention", owner)
    else:
        assert (level, finding.who) == ("fails", "")


@pytest.mark.parametrize("released", [False, True], ids=["not-released", "released"])
def test_a_version_that_needs_a_newer_release_fails_released_or_not_and_names_the_project(
    tmp_path: Path, released: bool
) -> None:
    finding, level = unreadable_as_checked(tmp_path, "newer", released)
    assert (level, finding.library, finding.who) == ("fails", "", "the project")
    assert finding.file == "visual/libraries/charts/1.0.0/library.yaml"
    said = checks.said(finding)
    assert said.startswith(
        "the installed capability cannot read charts@1.0.0: it needs release 9.0.0 of the "
        "capability, and "
    )
    assert said.endswith(
        " is installed — for the project — upgrade the capability, or take charts@1.0.0 out "
        "of the library folder and off the list once no lock names it"
    )


def test_a_released_version_that_changed_is_a_finding(tmp_path: Path) -> None:
    root = project(tmp_path)
    folder = copy_library(root, RELEASED_FOUNDATIONS, "foundations", "1.0.0")
    write_list(
        root,
        {
            "foundations": {
                "source": {"kind": "shipped"},
                "versions": {"1.0.0": released_entry(root, "foundations", "1.0.0")},
            }
        },
    )
    assert held(root, INSTALLED).findings() == []
    roles = folder / "roles.yaml"
    roles.write_text(roles.read_text(encoding="utf-8") + "# a comment changes no value\n")
    assert held(root, INSTALLED).findings() == []
    roles.write_text(roles.read_text(encoding="utf-8").replace("space.4", "space.5"))
    (finding,) = held(root, INSTALLED).findings()
    assert finding.code == "library-changed"
    assert "`roles.yaml` of foundations@1.0.0 changed" in finding.message


def test_a_released_version_with_no_fingerprint_is_a_finding(tmp_path: Path) -> None:
    root = project(tmp_path)
    add_library(root, "charts", "1.0.0")
    write_list(root, {"charts": {"source": PROJECT, "versions": {"1.0.0": {"released": True}}}})
    (finding,) = held(root).findings()
    assert "keeps no fingerprint" in finding.message


# --- the lock -----------------------------------------------------------------------------------


def test_the_shipped_foundations_and_the_test_brand_lock_together(tmp_path: Path) -> None:
    root = project(tmp_path)
    copy_library(root, RELEASED_FOUNDATIONS, "foundations", "1.0.0")
    copy_library(root, TEST_BRAND, "test-brand", "1.0.0")
    lock = libraries.move_lock(libraries.Held(root, "visual"), ["foundations", "test-brand"]).lock
    assert lock == {"foundations": "1.0.0", "test-brand": "1.0.0"}


def edition_project(tmp_path: Path) -> Path:
    """The shipped foundations, the test brand, and the test edition built on it."""
    root = project(tmp_path)
    copy_library(root, RELEASED_FOUNDATIONS, "foundations", "1.0.0")
    copy_library(root, TEST_BRAND, "test-brand", "1.0.0")
    copy_library(root, TEST_EDITION, "test-edition", "1.0.0")
    return root


def test_a_brands_lock_names_its_base(tmp_path: Path) -> None:
    root = edition_project(tmp_path)
    roots = ["foundations", "test-edition"]
    lock = libraries.move_lock(held(root, INSTALLED), roots).lock
    assert lock == {"foundations": "1.0.0", "test-brand": "1.0.0", "test-edition": "1.0.0"}
    without_base = {"foundations": "1.0.0", "test-edition": "1.0.0"}
    with pytest.raises(libraries.LockRefused, match="needs `test-brand`, which the lock"):
        libraries.move_lock(held(root, INSTALLED), roots, without_base, pinned=True)


def test_the_check_finds_a_lock_that_leaves_out_a_brands_base(tmp_path: Path) -> None:
    root = edition_project(tmp_path)
    lock = {"foundations": "1.0.0", "test-edition": "1.0.0"}
    write_piece(root, "card", brand="test-edition", lock=lock)
    write(root / "visual/pieces/card/content.en.yaml", yaml_text(bound("content", caption="x")))
    (finding,) = checks.lock_findings(held(root, INSTALLED), pl.read_piece(root, "visual", "card"))
    assert finding.code == "lock-incomplete"
    assert "test-edition@1.0.0 builds on `test-brand`" in finding.message


def test_a_first_lock_takes_the_newest_of_each_with_what_it_builds_on(tmp_path: Path) -> None:
    root = project(tmp_path)
    add_library(root, "base", "1.0.0")
    add_library(root, "base", "1.2.0")
    add_library(root, "charts", "1.0.0", builds_on={"base": 1})
    add_library(root, "charts", "2.1.0", builds_on={"base": 1})
    assert libraries.move_lock(held(root), ["charts"]).lock == {"base": "1.2.0", "charts": "2.1.0"}


def test_a_lock_moves_within_the_lines_it_names(tmp_path: Path) -> None:
    root = project(tmp_path)
    add_library(root, "base", "1.0.0")
    add_library(root, "base", "1.3.0")
    add_library(root, "base", "2.0.0")
    add_library(root, "extra", "3.0.0")
    lock = libraries.move_lock(held(root), ["base", "extra"], {"base": "1.0.0"}).lock
    assert lock == {"base": "1.3.0", "extra": "3.0.0"}


def test_a_lock_skips_a_newer_version_the_capability_cannot_read(tmp_path: Path) -> None:
    root = project(tmp_path)
    add_library(root, "base", "1.0.0")
    add_library(root, "base", "1.1.0", needs_release="9.0.0")
    assert libraries.move_lock(held(root), ["base"]).lock == {"base": "1.0.0"}


def test_a_lock_backs_off_library_by_library_where_two_build_on_two_majors(
    tmp_path: Path,
) -> None:
    root = project(tmp_path)
    add_library(root, "base", "1.0.0")
    add_library(root, "base", "2.0.0")
    add_library(root, "a", "1.0.0", builds_on={"base": 1})
    add_library(root, "a", "2.0.0", builds_on={"base": 2})
    add_library(root, "b", "1.0.0", builds_on={"base": 1})
    lock = libraries.move_lock(held(root), ["a", "b"]).lock
    assert lock == {"a": "1.0.0", "b": "1.0.0", "base": "1.0.0"}


def test_no_lock_fits_where_two_libraries_need_two_majors_of_a_third(tmp_path: Path) -> None:
    root = project(tmp_path)
    add_library(root, "base", "1.0.0")
    add_library(root, "base", "2.0.0")
    add_library(root, "a", "2.0.0", builds_on={"base": 2})
    add_library(root, "b", "1.0.0", builds_on={"base": 1})
    with pytest.raises(libraries.LockRefused) as refused:
        libraries.move_lock(held(root), ["a", "b"])
    said = str(refused.value)
    assert "a@2.0.0 builds on `base` 2" in said
    assert "b@1.0.0 builds on `base` 1" in said


@pytest.mark.parametrize(
    ("lock", "said"),
    [
        (None, "holds no version of `missing`: bring it in"),
        ({"base": "latest"}, "which is no version"),
    ],
)
def test_a_lock_the_project_cannot_give_is_refused_naming_why(
    tmp_path: Path, lock: dict[str, str] | None, said: str
) -> None:
    root = project(tmp_path)
    add_library(root, "base", "1.0.0")
    roots = ["missing"] if lock is None else ["base"]
    with pytest.raises(libraries.LockRefused, match=re.escape(said)):
        libraries.move_lock(held(root), roots, lock)


def test_a_refusal_names_why_no_version_can_be_read(tmp_path: Path) -> None:
    root = project(tmp_path)
    add_library(root, "base", "1.0.0", needs_release="9.0.0")
    with pytest.raises(libraries.LockRefused, match=r"needs release 9\.0\.0"):
        libraries.move_lock(held(root), ["base"])


def test_a_lock_within_a_line_the_project_no_longer_holds_is_refused(tmp_path: Path) -> None:
    root = project(tmp_path)
    add_library(root, "base", "2.0.0")
    with pytest.raises(libraries.LockRefused, match="of major 1, the line the lock names"):
        libraries.move_lock(held(root), ["base"], {"base": "1.4.0"})


def backtracking_project(tmp_path: Path, versions: int) -> Path:
    """`a` and `b` at `versions` versions each, every one built on `base` 1, and `c` built
    on `base` 2: a search for `a`, `b` and `c` tries every pair of `a` and `b` before it
    finds that none fits."""
    root = project(tmp_path)
    add_library(root, "base", "1.0.0")
    add_library(root, "base", "2.0.0")
    for minor in range(versions):
        add_library(root, "a", f"1.{minor}.0", builds_on={"base": 1})
        add_library(root, "b", f"1.{minor}.0", builds_on={"base": 1})
    add_library(root, "c", "1.0.0", builds_on={"base": 2})
    return root


def test_a_search_past_its_bound_stops_naming_the_libraries_it_was_choosing(
    tmp_path: Path,
) -> None:
    """80 versions each: some 12 800 tried before the search could find that none fits."""
    root = backtracking_project(tmp_path, 80)
    with pytest.raises(libraries.LockRefused) as refused:
        libraries.move_lock(held(root), ["a", "b", "c"])
    assert str(refused.value) == (
        f"the search for versions that fit together stopped at its bound, "
        f"{libraries.SEARCH_STEPS} versions tried, choosing among those of `a`, `b`, `base`, "
        f"`c`: name the line of each in the lock, or take the versions no piece needs out of "
        f"the library folder"
    )


def test_the_bound_leaves_room_for_a_search_of_many_versions(tmp_path: Path) -> None:
    """60 versions each: some 7 300 tried, within the bound, to find that none fits."""
    root = backtracking_project(tmp_path, 60)
    with pytest.raises(libraries.LockRefused, match=re.escape("c@1.0.0 builds on `base` 2")):
        libraries.move_lock(held(root), ["a", "b", "c"])


# --- a pinned lock ------------------------------------------------------------------------------


def pinned_project(tmp_path: Path) -> Path:
    root = project(tmp_path)
    add_library(root, "base", "1.0.0")
    add_library(root, "base", "1.5.0")
    add_library(root, "charts", "1.0.0", builds_on={"base": 1})
    return root


def test_a_pinned_lock_that_fits_never_moves(tmp_path: Path) -> None:
    root = pinned_project(tmp_path)
    lock = {"base": "1.0.0", "charts": "1.0.0"}
    assert libraries.move_lock(held(root), ["charts"], lock, pinned=True).lock == lock


@pytest.mark.parametrize(
    ("lock", "said"),
    [
        (None, "has no lock yet"),
        ({"charts": "1.0.0"}, "needs `base`, which the lock does not name"),
        (
            {"base": "1.0.0", "charts": "1.1.0"},
            "the lock names charts@1.1.0, which the project does not hold",
        ),
        (
            {"base": "2.0.0", "charts": "1.0.0"},
            "the lock names base@2.0.0, which the project does not hold",
        ),
        ({"base": "x", "charts": "1.0.0"}, "`base: x`, which is no version"),
    ],
)
def test_a_pinned_lock_that_does_not_fit_is_refused(
    tmp_path: Path, lock: dict[str, str] | None, said: str
) -> None:
    root = pinned_project(tmp_path)
    with pytest.raises(libraries.LockRefused, match=re.escape(said)):
        libraries.move_lock(held(root), ["charts"], lock, pinned=True)


def test_a_pinned_lock_whose_libraries_do_not_build_on_each_other_is_refused(
    tmp_path: Path,
) -> None:
    root = pinned_project(tmp_path)
    add_library(root, "base", "2.0.0")
    lock = {"base": "2.0.0", "charts": "1.0.0"}
    with pytest.raises(libraries.LockRefused) as refused:
        libraries.move_lock(held(root), ["charts"], lock, pinned=True)
    assert str(refused.value) == (
        "the lock does not fit: charts@1.0.0 builds on `base` 1, but the lock names base@2.0.0"
    )


def test_a_lock_on_a_version_it_cannot_read_is_refused_as_the_lock(tmp_path: Path) -> None:
    root = pinned_project(tmp_path)
    add_library(root, "base", "1.6.0", needs_release="9.0.0")
    lock = {"base": "1.6.0", "charts": "1.0.0"}
    with pytest.raises(libraries.LockRefused) as refused:
        libraries.move_lock(held(root), ["charts"], lock, pinned=True)
    assert str(refused.value) == (
        "the lock names base@1.6.0, which cannot be read: it needs release 9.0.0 of the "
        "capability, and 0.1.0 is installed: upgrade the capability"
    )


# --- a version checked alone (DEC-005 point 7, DEC-008 point 1) ----------------------------------


def chosen(found: dict[str, Any]) -> dict[str, str]:
    return {name: str(library.version) for name, library in found.items()}


def test_a_version_alone_takes_the_newest_of_each_major_it_names(tmp_path: Path) -> None:
    root = project(tmp_path)
    add_library(root, "base", "1.0.0")
    add_library(root, "base", "1.4.0")
    add_library(root, "base", "2.0.0")
    add_library(root, "parts", "1.0.0", builds_on={"base": 1})
    add_library(root, "parts", "1.2.0", builds_on={"base": 1})
    add_library(root, "brand", "1.0.0", builds_on={"base": 1, "parts": 1}, kind="brand")
    found = libraries.newest_of_majors(held(root), held(root).library("brand", V("1.0.0")))
    assert chosen(found) == {"base": "1.4.0", "brand": "1.0.0", "parts": "1.2.0"}


def test_the_newest_of_a_major_skips_a_version_the_capability_cannot_read(
    tmp_path: Path,
) -> None:
    root = project(tmp_path)
    add_library(root, "base", "1.0.0")
    add_library(root, "base", "1.1.0", needs_release="9.0.0")
    add_library(root, "parts", "1.0.0", builds_on={"base": 1})
    found = libraries.newest_of_majors(held(root), held(root).library("parts", V("1.0.0")))
    assert chosen(found) == {"base": "1.0.0", "parts": "1.0.0"}


def test_two_majors_of_one_library_conflict_naming_both(tmp_path: Path) -> None:
    root = project(tmp_path)
    add_library(root, "base", "1.0.0")
    add_library(root, "base", "2.0.0")
    add_library(root, "parts", "1.0.0", builds_on={"base": 2})
    add_library(root, "brand", "1.0.0", builds_on={"base": 1, "parts": 1}, kind="brand")
    with pytest.raises(libraries.MajorsConflict) as refused:
        libraries.newest_of_majors(held(root), held(root).library("brand", V("1.0.0")))
    said = str(refused.value)
    assert "brand@1.0.0 builds on `base` 1" in said
    assert "parts@1.0.0 builds on `base` 2" in said
    assert isinstance(refused.value, libraries.LockRefused)


def test_a_major_the_project_holds_no_version_of_is_refused_naming_why(tmp_path: Path) -> None:
    root = project(tmp_path)
    add_library(root, "base", "1.0.0", needs_release="9.0.0")
    add_library(root, "parts", "1.0.0", builds_on={"base": 1, "other": 3})
    with pytest.raises(libraries.LockRefused, match=r"needs release 9\.0\.0") as refused:
        libraries.newest_of_majors(held(root), held(root).library("parts", V("1.0.0")))
    assert not isinstance(refused.value, libraries.MajorsConflict)


# --- a shipped library's copies, and the locks that name them (DEC-013 point 5) ------------------


def test_each_lock_is_read_from_its_piece_yaml_alone_and_says_whether_it_follows(
    tmp_path: Path,
) -> None:
    root = project(tmp_path)
    write_piece(root, "draft", lock={"foundations": "1.0.0"})
    write(root / "visual" / "pieces" / "draft" / "content.en.yaml", "not: [content\n")
    write_piece(root, "pinned", lock={"foundations": "1.0.0"}, pinned=True)
    write_piece(root, "new")
    write(root / "visual" / "pieces" / "loose" / "notes.md", "No piece.yaml.\n")
    write_piece(root, "odd", lock={"foundations": "latest"})
    write_piece(root, "unpinned", pinned="no")
    write(
        root / "visual" / "code" / "css.yaml",
        yaml_text(bound("code", lock={"foundations": "1.0.0"})),
    )
    write(root / "visual" / "code" / "broken.yaml", "lock: {foundations: 1.0.0}\n")
    found = {
        Path(lock.file).parent.name if lock.kind == "piece" else Path(lock.file).name: lock
        for lock in copies.locks(root, "visual", "foundations")
    }
    assert [(name, lock.follows, lock.versions is None) for name, lock in found.items()] == [
        ("draft", True, False),
        ("loose", False, True),
        ("new", True, False),
        ("odd", False, True),
        ("pinned", False, False),
        ("unpinned", False, True),
        ("broken.yaml", False, True),
        ("css.yaml", False, False),
    ]
    one = V("1.0.0")
    assert [name for name, lock in found.items() if lock.names("foundations", one)] == [
        "draft",
        "loose",
        "odd",
        "pinned",
        "unpinned",
        "broken.yaml",
        "css.yaml",
    ]
    assert [lock.described for lock in copies.holding(found.values(), "foundations", one)] == [
        "visual/pieces/loose/piece.yaml, whose lock cannot be read: the file does not exist",
        "visual/pieces/odd/piece.yaml, whose lock cannot be read: its lock names `foundations: "
        "latest`, which is no version",
        "the pinned draft `pinned`",
        "visual/pieces/unpinned/piece.yaml, whose lock cannot be read: its `pinned` is not true "
        "or false",
        "visual/code/broken.yaml, whose lock cannot be read: the file names no schema: add "
        "`pkit_schema: visual-communication:code` and `schema_version: 1` at its top",
        "the declaration `css` of written code",
    ]


@pytest.mark.parametrize(
    ("fields", "follows", "called"),
    [
        pytest.param({}, True, "draft", id="draft"),
        pytest.param({"pinned": True}, False, "pinned draft", id="pinned-draft"),
        pytest.param({"state": "final"}, True, "final piece", id="final"),
        pytest.param({"state": "final", "pinned": True}, True, "final piece", id="final-pinned"),
        pytest.param({"state": "final", "pinned": "no"}, True, "final piece", id="final-odd-pin"),
        pytest.param({"state": "published"}, False, "published piece", id="published"),
        pytest.param(
            {"state": "published", "pinned": False},
            False,
            "published piece",
            id="published-not-pinned",
        ),
    ],
)
def test_a_lock_follows_by_its_state_and_a_pin_is_read_of_a_draft_alone(
    tmp_path: Path, fields: dict[str, Any], follows: bool, called: str
) -> None:
    root = project(tmp_path)
    write_piece(root, "flow", lock={"foundations": "1.0.0"}, **fields)
    (lock,) = copies.locks(root, "visual", "foundations")
    assert lock.follows is follows
    assert lock.described == f"the {called} `flow`"


def test_what_the_capability_ships_under_a_number_is_its_release_before_its_version_being_built(
    tmp_path: Path,
) -> None:
    folder = tmp_path / "capability"
    built = built_as_released(folder / "libraries" / "foundations")
    [library] = shipped.read(folder)
    being_built = copies.under(library, V("1.0.0"))
    assert (being_built.folder, being_built.entry, being_built.released) == (
        built,
        UNRELEASED,
        None,
    )
    assert sorted(being_built.files) == sorted(
        path.relative_to(built).as_posix() for path in built.rglob("*.yaml")
    )
    assert copies.under(library, V("1.1.0")) is None
    place = shipped.place_of(folder, "foundations", V("1.0.0"))
    shutil.copytree(built, place)
    entry = shipped.entry_of(folder, "foundations", V("1.0.0"))
    listed = {"source": {"kind": "shipped"}, "versions": {"1.0.0": entry}}
    write(
        folder / "releases" / "foundations" / "releases.yaml",
        yaml_text(bound("libraries", libraries={"foundations": listed})),
    )
    [library] = shipped.read(folder)
    taken = copies.under(library, V("1.0.0"))
    assert (taken.folder, taken.entry, taken.released.version) == (place, entry, V("1.0.0"))


# --- a search that judges each whole combination (DEC-003 point 8, DEC-010 point 2, DEC-011
# --- point 4) -----------------------------------------------------------------------------------


def two_libraries(tmp_path: Path, *versions: str) -> Path:
    """`a` and `b`, at each of `versions`."""
    root = project(tmp_path)
    for version in versions:
        add_library(root, "a", version)
        add_library(root, "b", version)
    return root


class Judging:
    """A judgement that finds a misfit in each combination `rule` names, implicating the
    libraries it returns, and keeps each combination it judged, by its versions."""

    def __init__(self, rule: Any) -> None:
        self.rule = rule
        self.judged: list[dict[str, str]] = []

    def __call__(self, versions: Any) -> list[Any]:
        chosen = {name: str(library.version) for name, library in versions.items()}
        self.judged.append(chosen)
        implicated = self.rule(chosen)
        if not implicated:
            return []
        return [libraries.Misfit("end", f"a loss under {chosen}", frozenset(implicated))]


def test_a_judged_search_backs_off_the_library_a_misfit_implicates_first(tmp_path: Path) -> None:
    root = two_libraries(tmp_path, "1.0.0", "1.1.0")
    judge = Judging(lambda chosen: {"a"} if chosen["a"] == "1.1.0" else set())

    moved = libraries.move_lock(held(root), ["a", "b"], {"a": "1.0.0", "b": "1.0.0"}, judge=judge)

    assert moved.lock == {"a": "1.0.0", "b": "1.1.0"}
    # `b`, chosen last, is not backed off: the misfit does not implicate it.
    assert judge.judged == [{"a": "1.1.0", "b": "1.1.0"}, {"a": "1.0.0", "b": "1.1.0"}]
    [held_back] = moved.held_back
    assert held_back.label == "a@1.1.0"
    assert [reason.said for reason in held_back.reasons] == [
        "a loss under {'a': '1.1.0', 'b': '1.1.0'}"
    ]
    assert (moved.below, moved.kept) == ((), "")


def test_a_loss_only_both_newest_versions_show_backs_off_the_later_library(
    tmp_path: Path,
) -> None:
    root = two_libraries(tmp_path, "1.0.0", "1.1.0")
    both = {"a": "1.1.0", "b": "1.1.0"}
    judge = Judging(lambda chosen: {"a", "b"} if chosen == both else set())

    moved = libraries.move_lock(held(root), ["a", "b"], {"a": "1.0.0", "b": "1.0.0"}, judge=judge)

    assert moved.lock == {"a": "1.1.0", "b": "1.0.0"}
    assert [each.label for each in moved.held_back] == ["b@1.1.0"]


def test_a_library_moves_no_lower_than_its_lock_while_versions_at_or_above_fit(
    tmp_path: Path,
) -> None:
    """`b` below its lock would let `a` move up; the search keeps both at or above."""
    root = two_libraries(tmp_path, "1.0.0", "1.1.0")
    both = {"a": "1.1.0", "b": "1.1.0"}
    judge = Judging(lambda chosen: {"a", "b"} if chosen == both else set())

    moved = libraries.move_lock(held(root), ["a", "b"], {"a": "1.0.0", "b": "1.1.0"}, judge=judge)

    assert moved.lock == {"a": "1.0.0", "b": "1.1.0"}
    assert [each.label for each in moved.held_back] == ["a@1.1.0"]
    assert moved.below == ()


def test_a_library_moves_below_its_lock_only_where_nothing_at_or_above_fits_and_says_so(
    tmp_path: Path,
) -> None:
    root = two_libraries(tmp_path, "1.0.0", "1.1.0", "1.2.0")
    judge = Judging(lambda chosen: {"a"} if chosen["a"] >= "1.1.0" else set())

    moved = libraries.move_lock(held(root), ["a", "b"], {"a": "1.1.0", "b": "1.0.0"}, judge=judge)

    assert moved.lock == {"a": "1.0.0", "b": "1.2.0"}
    assert moved.below == (
        "`a` moves below 1.1.0, the version the lock named, to 1.0.0: no versions at or "
        "above those the lock names fit together",
    )
    assert [each.label for each in moved.held_back] == ["a@1.2.0", "a@1.1.0"]

    missing = libraries.move_lock(held(root), ["a"], {"a": "1.4.0"})
    assert missing.lock == {"a": "1.2.0"}
    assert missing.below == (
        "`a` moves below 1.4.0, the version the lock named, to 1.2.0: the project holds no "
        "version 1.4.0 that the installed capability reads",
    )


#: Three versions of each of `a` and `b`, and a lock between the oldest and the newest.
LADDER = ("1.0.0", "1.1.0", "1.2.0")
BETWEEN = {"a": "1.1.0", "b": "1.1.0"}


@pytest.mark.parametrize("move", [False, True], ids=["render", "proposed-move"])
def test_a_search_goes_below_its_lock_only_where_nothing_at_or_above_it_fits(
    tmp_path: Path, move: bool
) -> None:
    """What removing a version that lies behind rests on (DEC-019 point 9): for every set of
    combinations that do not fit, a draft's search and a proposed move each find a lock at or
    above the one held wherever a combination at or above it fits, and one that fits."""
    root = two_libraries(tmp_path, *LADDER)
    listing(root)
    found_in = held(root)
    pairs = [(a, b) for a in LADDER for b in LADDER]
    above = {(a, b) for a, b in pairs if min(V(a), V(b)) >= V("1.1.0")}
    for mask in range(1 << len(pairs)):
        unfit = {pair for index, pair in enumerate(pairs) if mask >> index & 1}
        judge = Judging(
            lambda chosen, unfit=unfit: {"a", "b"} if (chosen["a"], chosen["b"]) in unfit else set()
        )
        search = libraries.propose_lock if move else libraries.move_lock
        fits = set(pairs) - unfit
        try:
            moved = search(found_in, ["a", "b"], BETWEEN, judge=judge)
        except libraries.LockRefused:
            assert not fits, unfit
            continue
        lock = (moved.lock["a"], moved.lock["b"])
        assert lock in fits, unfit
        if fits & above:
            assert lock in above, unfit


def test_a_searchs_advice_past_its_bounds_names_no_command_that_removes_versions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The advice stays as it is (DEC-019, Implications): the command that removes versions
    spares many that a search tries."""
    root = two_libraries(tmp_path, *LADDER)
    monkeypatch.setattr(libraries, "SEARCH_JUDGED", 1)
    kept = libraries.move_lock(held(root), ["a", "b"], BETWEEN, judge=Judging(lambda _: {"a"}))
    monkeypatch.setattr(libraries, "SEARCH_STEPS", 1)
    with pytest.raises(libraries.LockRefused) as refused:
        libraries.move_lock(held(root), ["a", "b"], BETWEEN)
    for advice in (kept.kept, str(refused.value)):
        assert "take the versions no piece needs out of the library folder" in advice
        assert "prune" not in advice


def test_past_its_bound_of_combinations_judged_the_search_keeps_the_lock_and_says_so(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Every combination is a misfit: after two judged, the search keeps `a` at its lock,
    and takes the newest of `extra`, which the lock does not name yet."""
    root = two_libraries(tmp_path, "1.0.0", "1.1.0", "1.2.0", "1.3.0")
    add_library(root, "extra", "1.0.0")
    add_library(root, "extra", "2.0.0")
    monkeypatch.setattr(libraries, "SEARCH_JUDGED", 2)
    judge = Judging(lambda chosen: {"a"})

    moved = libraries.move_lock(held(root), ["a", "extra"], {"a": "1.0.0"}, judge=judge)

    assert moved.lock == {"a": "1.0.0", "extra": "2.0.0"}
    assert len(judge.judged) == 2
    assert moved.kept == (
        "the search for versions that fit together stopped at its bound, 2 combinations "
        "judged, choosing among those of `a`, `extra`: the lock is kept, with the newest version "
        "that fits of each library it does not name yet; move the lock by hand, or take the "
        "versions no piece needs out of the library folder"
    )
    assert moved.held_back == ()


def test_a_pinned_lock_is_never_judged(tmp_path: Path) -> None:
    root = pinned_project(tmp_path)
    lock = {"base": "1.0.0", "charts": "1.0.0"}
    judge = Judging(lambda chosen: pytest.fail(f"{chosen} judged"))
    assert libraries.move_lock(held(root), ["charts"], lock, pinned=True, judge=judge).lock == lock


# --- a lock's proposed move (DEC-019 point 7) -----------------------------------------------------


def listing(root: Path, *unreleased: str) -> None:
    """The list of every version the library folder holds, each released but those
    `unreleased` names, by label."""
    listed: dict[str, Any] = {}
    for folder in sorted((root / "visual" / "libraries").glob("*/*")):
        if folder.is_dir():
            name, version = folder.parent.name, folder.name
            entry = UNRELEASED if f"{name}@{version}" in unreleased else {"released": True}
            listed.setdefault(name, {"source": PROJECT, "versions": {}})["versions"][version] = (
                entry
            )
    write_list(root, listed)


def reasons(moved: Any) -> dict[str, list[str]]:
    """The rule of each reason the search gives for each version it held back."""
    return {each.label: [reason.rule for reason in each.reasons] for each in moved.held_back}


def said(moved: Any, label: str) -> list[str]:
    """The words of each reason the search gives for a version it held back."""
    [held_back] = [each for each in moved.held_back if each.label == label]
    return [reason.said for reason in held_back.reasons]


def test_a_move_offers_only_released_versions_it_can_read_within_the_locks_major(
    tmp_path: Path,
) -> None:
    root = project(tmp_path)
    for version in ("1.0.0", "1.1.0", "1.2.0", "2.0.0"):
        add_library(root, "base", version)
    add_library(root, "base", "1.3.0", needs_release="9.0.0")
    listing(root, "base@1.2.0")

    moved = libraries.propose_lock(held(root), ["base"], {"base": "1.0.0"})

    assert moved.lock == {"base": "1.1.0"}
    assert reasons(moved) == {
        "base@2.0.0": ["later-major"],
        "base@1.3.0": ["unreadable"],
        "base@1.2.0": ["not-released"],
    }
    assert said(moved, "base@2.0.0") == ["it is of major 2, and the move stays within major 1"]
    assert said(moved, "base@1.3.0") == [
        "it needs release 9.0.0 of the capability, and 0.1.0 is installed: upgrade the capability"
    ]
    assert said(moved, "base@1.2.0") == ["it is not released"]
    assert [each.label for each in moved.held_back] == ["base@2.0.0", "base@1.3.0", "base@1.2.0"]
    assert (moved.below, moved.kept, moved.past) == ((), "", ())


def test_a_version_held_back_gives_each_reason_that_holds(tmp_path: Path) -> None:
    root = project(tmp_path)
    add_library(root, "base", "1.0.0")
    add_library(root, "base", "2.0.0", needs_release="9.0.0")
    listing(root, "base@2.0.0")

    moved = libraries.propose_lock(held(root), ["base"], {"base": "1.0.0"})

    assert reasons(moved) == {"base@2.0.0": ["unreadable", "not-released", "later-major"]}


def test_a_version_whose_library_yaml_cannot_be_read_is_held_back_by_its_name(
    tmp_path: Path,
) -> None:
    root = project(tmp_path)
    add_library(root, "base", "1.0.0")
    write(version_folder(root, "base", "1.1.0") / "library.yaml", "name: [")
    listing(root)

    moved = libraries.propose_lock(held(root), ["base"], {"base": "1.0.0"})

    assert moved.lock == {"base": "1.0.0"}
    assert reasons(moved) == {"base@1.1.0": ["unreadable"]}


def test_a_move_keeps_to_versions_that_fit_and_names_each_it_held_back(tmp_path: Path) -> None:
    root = two_libraries(tmp_path, "1.0.0", "1.1.0")
    listing(root)
    judge = Judging(lambda chosen: {"a"} if chosen["a"] == "1.1.0" else set())

    moved = libraries.propose_lock(
        held(root), ["a", "b"], {"a": "1.0.0", "b": "1.0.0"}, judge=judge
    )

    assert moved.lock == {"a": "1.0.0", "b": "1.1.0"}
    assert reasons(moved) == {"a@1.1.0": ["end"]}
    assert said(moved, "a@1.1.0") == ["a loss under {'a': '1.1.0', 'b': '1.1.0'}"]


def test_a_version_of_the_locks_major_that_needs_a_later_major_of_another_is_held_back(
    tmp_path: Path,
) -> None:
    root = project(tmp_path)
    add_library(root, "base", "1.0.0")
    add_library(root, "base", "2.0.0")
    add_library(root, "charts", "1.0.0", builds_on={"base": 1})
    add_library(root, "charts", "1.1.0", builds_on={"base": 2})
    listing(root)
    lock = {"base": "1.0.0", "charts": "1.0.0"}

    for roots in (["charts"], ["base", "charts"]):
        moved = libraries.propose_lock(held(root), roots, lock)

        assert moved.lock == lock
        assert reasons(moved) == {"base@2.0.0": ["later-major"], "charts@1.1.0": ["later-major"]}
        assert said(moved, "charts@1.1.0") == [
            "charts@1.1.0 builds on `base` 2, and the lock names base@1.0.0: only a name moves a "
            "lock to another major"
        ]


def test_a_version_whose_base_the_project_lacks_is_held_back_in_the_searchs_words(
    tmp_path: Path,
) -> None:
    root = project(tmp_path)
    add_library(root, "charts", "1.0.0")
    add_library(root, "charts", "1.1.0", builds_on={"missing": 1})
    listing(root)

    moved = libraries.propose_lock(held(root), ["charts"], {"charts": "1.0.0"})

    assert moved.lock == {"charts": "1.0.0"}
    assert reasons(moved) == {"charts@1.1.0": ["no-fit"]}
    assert said(moved, "charts@1.1.0") == ["the project holds no version of `missing`: bring it in"]


def test_a_lock_on_a_version_not_released_moves_to_a_released_one_and_says_why(
    tmp_path: Path,
) -> None:
    root = project(tmp_path)
    add_library(root, "base", "1.0.0")
    add_library(root, "base", "1.1.0")
    listing(root, "base@1.1.0")

    moved = libraries.propose_lock(held(root), ["base"], {"base": "1.1.0"})

    assert moved.lock == {"base": "1.0.0"}
    assert moved.below == (
        "`base` moves below 1.1.0, the version the lock named, to 1.0.0: 1.1.0 is not released",
    )


def test_a_move_refuses_a_line_with_no_released_version(tmp_path: Path) -> None:
    root = project(tmp_path)
    add_library(root, "base", "1.0.0")
    listing(root, "base@1.0.0")
    with pytest.raises(libraries.LockRefused) as refused:
        libraries.propose_lock(held(root), ["base"], {"base": "1.0.0"})
    assert str(refused.value) == (
        "the project holds no released version of `base` of major 1, the line the lock names "
        "that the installed capability reads"
    )


def test_a_move_refuses_libraries_that_build_on_two_majors_of_one_library(tmp_path: Path) -> None:
    root = project(tmp_path)
    add_library(root, "base", "1.0.0")
    add_library(root, "base", "2.0.0")
    add_library(root, "a", "1.0.0", builds_on={"base": 2})
    add_library(root, "b", "1.0.0", builds_on={"base": 1})
    listing(root)
    lock = {"a": "1.0.0", "b": "1.0.0", "base": "1.0.0"}
    with pytest.raises(libraries.LockRefused) as refused:
        libraries.propose_lock(held(root), ["a", "b"], lock)
    said = str(refused.value)
    assert "a@1.0.0 builds on `base` 2" in said
    assert "b@1.0.0 builds on `base` 1" in said


def test_a_move_refuses_a_list_it_cannot_read(tmp_path: Path) -> None:
    root = project(tmp_path)
    add_library(root, "base", "1.0.0")
    write(root / "visual" / "libraries" / "libraries.yaml", "libraries: [")
    with pytest.raises(libraries.LockRefused, match=r"libraries\.yaml"):
        libraries.propose_lock(held(root), ["base"], {"base": "1.0.0"})


def test_past_its_bound_a_move_keeps_the_lock_and_gives_only_what_it_knows(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = two_libraries(tmp_path, "1.0.0", "1.1.0", "1.2.0")
    add_library(root, "a", "2.0.0")
    listing(root, "a@1.2.0")
    monkeypatch.setattr(libraries, "SEARCH_JUDGED", 1)
    judge = Judging(lambda chosen: {"a"})

    moved = libraries.propose_lock(held(root), ["a"], {"a": "1.0.0"}, judge=judge)

    assert moved.lock == {"a": "1.0.0"}
    assert moved.kept.startswith("the search for versions that fit together stopped at its bound")
    assert reasons(moved) == {"a@2.0.0": ["later-major"], "a@1.2.0": ["not-released"]}


def test_a_name_moves_what_it_names_and_leaves_the_rest(tmp_path: Path) -> None:
    root = two_libraries(tmp_path, "1.0.0", "1.1.0", "1.2.0")
    listing(root)
    lock = {"a": "1.0.0", "b": "1.0.0"}

    moved = libraries.propose_lock(held(root), ["a", "b"], lock, names=["a@1.1.0"])

    assert moved.lock == {"a": "1.1.0", "b": "1.0.0"}
    assert moved.held_back == ()


def test_several_names_each_move_their_library(tmp_path: Path) -> None:
    root = two_libraries(tmp_path, "1.0.0", "1.1.0", "1.2.0")
    listing(root)
    lock = {"a": "1.0.0", "b": "1.0.0"}
    names = ["a@1.1.0", "b@1.2.0", "b@1.2.0"]
    moved = libraries.propose_lock(held(root), ["a", "b"], lock, names=names)
    assert moved.lock == {"a": "1.1.0", "b": "1.2.0"}


def test_a_name_may_lie_below_the_lock_and_is_no_move_the_search_explains(tmp_path: Path) -> None:
    root = two_libraries(tmp_path, "1.0.0", "1.1.0")
    listing(root)
    lock = {"a": "1.1.0", "b": "1.1.0"}

    moved = libraries.propose_lock(held(root), ["a", "b"], lock, names=["a@1.0.0"])

    assert moved.lock == {"a": "1.0.0", "b": "1.1.0"}
    assert moved.below == ()


def test_a_name_takes_a_new_major_and_what_it_newly_needs(tmp_path: Path) -> None:
    root = project(tmp_path)
    add_library(root, "charts", "1.0.0")
    add_library(root, "charts", "2.0.0", builds_on={"extra": 1})
    add_library(root, "extra", "1.0.0")
    add_library(root, "extra", "1.1.0")
    add_library(root, "extra", "1.2.0")
    listing(root, "extra@1.2.0")

    moved = libraries.propose_lock(
        held(root), ["charts"], {"charts": "1.0.0"}, names=["charts@2.0.0"]
    )

    assert moved.lock == {"charts": "2.0.0", "extra": "1.1.0"}


def majors_project(tmp_path: Path) -> Path:
    """`base` at two majors, `charts` on each, and a `tail` the libraries do not build on."""
    root = project(tmp_path)
    add_library(root, "base", "1.0.0")
    add_library(root, "base", "2.0.0")
    add_library(root, "charts", "1.0.0", builds_on={"base": 1})
    add_library(root, "charts", "2.0.0", builds_on={"base": 2})
    add_library(root, "tail", "1.0.0")
    add_library(root, "tail", "1.1.0")
    listing(root)
    return root


MAJORS_LOCK = {"base": "1.0.0", "charts": "1.0.0", "tail": "1.0.0"}


@pytest.mark.parametrize("roots", [["charts", "tail"], ["base", "charts", "tail"]])
def test_a_name_that_needs_a_new_major_of_another_library_refuses_naming_it(
    tmp_path: Path, roots: list[str]
) -> None:
    root = majors_project(tmp_path)
    with pytest.raises(libraries.LockRefused) as refused:
        libraries.propose_lock(held(root), roots, MAJORS_LOCK, names=["charts@2.0.0"])
    assert str(refused.value) == (
        "charts@2.0.0 builds on `base` 2, and the lock names base@1.0.0: only a name moves a "
        "lock to another major"
    )


def test_naming_that_major_too_moves_both_and_leaves_the_rest(tmp_path: Path) -> None:
    root = majors_project(tmp_path)
    names = ["charts@2.0.0", "base@2.0.0"]
    moved = libraries.propose_lock(held(root), ["charts", "tail"], MAJORS_LOCK, names=names)
    assert moved.lock == {"base": "2.0.0", "charts": "2.0.0", "tail": "1.0.0"}


@pytest.mark.parametrize("roots", [["charts", "tail"], ["base", "charts", "tail"]])
def test_a_name_that_leaves_two_majors_of_a_library_refuses_naming_both(
    tmp_path: Path, roots: list[str]
) -> None:
    root = majors_project(tmp_path)
    with pytest.raises(libraries.LockRefused) as refused:
        libraries.propose_lock(held(root), roots, MAJORS_LOCK, names=["base@2.0.0"])
    assert str(refused.value) == "charts@1.0.0 builds on `base` 1, and base@2.0.0 is named"


def test_a_library_a_name_leaves_on_another_major_moves_within_its_own(tmp_path: Path) -> None:
    root = project(tmp_path)
    add_library(root, "base", "1.0.0")
    add_library(root, "base", "2.0.0")
    add_library(root, "charts", "1.0.0", builds_on={"base": 2})
    add_library(root, "charts", "1.1.0", builds_on={"base": 1})
    add_library(root, "charts", "1.2.0", builds_on={"base": 2})
    add_library(root, "charts", "1.3.0", builds_on={"base": 1})
    listing(root)
    lock = {"base": "1.0.0", "charts": "1.1.0"}

    moved = libraries.propose_lock(held(root), ["charts"], lock, names=["base@2.0.0"])

    assert moved.lock == {"base": "2.0.0", "charts": "1.2.0"}
    assert moved.below == ()

    down = {"base": "1.0.0", "charts": "1.3.0"}
    moved = libraries.propose_lock(held(root), ["charts"], down, names=["base@2.0.0"])
    assert moved.lock == {"base": "2.0.0", "charts": "1.2.0"}
    assert moved.below == (
        "`charts` moves below 1.3.0, the version the lock named, to 1.2.0: no versions at or "
        "above those the lock names fit together",
    )


def test_a_library_stays_at_its_lock_below_a_later_library_that_had_to_move(
    tmp_path: Path,
) -> None:
    """`a` could move up, and `b` must go below its lock: `a` stays all the same."""
    root = project(tmp_path)
    add_library(root, "base", "1.0.0")
    add_library(root, "base", "2.0.0")
    add_library(root, "a", "1.0.0", builds_on={"base": 2})
    add_library(root, "a", "1.1.0", builds_on={"base": 2})
    add_library(root, "b", "1.0.0", builds_on={"base": 2})
    add_library(root, "b", "1.1.0", builds_on={"base": 1})
    listing(root)
    lock = {"a": "1.0.0", "b": "1.1.0", "base": "1.0.0"}

    moved = libraries.propose_lock(held(root), ["a", "b"], lock, names=["base@2.0.0"])

    assert moved.lock == {"a": "1.0.0", "b": "1.0.0", "base": "2.0.0"}


@pytest.mark.parametrize("rule", ["clash", "end"])
def test_a_name_goes_past_a_clash_or_a_lost_end_and_the_result_names_it(
    tmp_path: Path, rule: str
) -> None:
    root = two_libraries(tmp_path, "1.0.0", "1.1.0")
    listing(root)
    misfit = libraries.Misfit(rule, "what the render says", frozenset({"a"}))
    judged: list[dict[str, str]] = []

    def judge(versions: Any) -> list[Any]:
        judged.append({name: str(library.version) for name, library in versions.items()})
        return [misfit]

    lock = {"a": "1.0.0", "b": "1.0.0"}
    moved = libraries.propose_lock(held(root), ["a", "b"], lock, names=["a@1.1.0"], judge=judge)

    assert moved.lock == {"a": "1.1.0", "b": "1.0.0"}
    assert moved.past == (misfit,)
    assert moved.held_back == ()
    assert judged == [{"a": "1.1.0", "b": "1.0.0"}]


@pytest.mark.parametrize(
    ("names", "refusal"),
    [
        (["a"], "`a` is no `<library>@<version>`"),
        (["a@latest"], "`a@latest` is no `<library>@<version>`"),
        (["a@1.1.0", "a@1.0.0"], "`a` is named at 1.1.0 and at 1.0.0"),
        (["a@1.9.0"], "the project does not hold a@1.9.0: bring it in"),
        (["missing@1.0.0"], "the project does not hold missing@1.0.0: bring it in"),
        (
            ["a@1.2.0"],
            "a@1.2.0 cannot be read: it needs release 9.0.0 of the capability, and 0.1.0 is "
            "installed: upgrade the capability",
        ),
        (["a@1.3.0"], "a@1.3.0 is not released, and this move takes released versions"),
        (["other@1.0.0"], "the piece does not use `other`, so no lock of it names one"),
    ],
)
def test_a_name_goes_past_nothing_else(tmp_path: Path, names: list[str], refusal: str) -> None:
    root = project(tmp_path)
    add_library(root, "a", "1.0.0")
    add_library(root, "a", "1.1.0")
    add_library(root, "a", "1.2.0", needs_release="9.0.0")
    add_library(root, "a", "1.3.0")
    add_library(root, "other", "1.0.0")
    listing(root, "a@1.3.0")
    with pytest.raises(libraries.LockRefused, match=re.escape(refusal)):
        libraries.propose_lock(held(root), ["a"], {"a": "1.0.0"}, names=names)


def test_a_caller_may_allow_a_name_not_yet_released(tmp_path: Path) -> None:
    root = two_libraries(tmp_path, "1.0.0", "1.1.0")
    listing(root, "a@1.1.0", "b@1.0.0")
    lock = {"a": "1.0.0", "b": "1.0.0"}

    moved = libraries.propose_lock(held(root), ["a", "b"], lock, names=["a@1.1.0"], unreleased=True)

    assert moved.lock == {"a": "1.1.0", "b": "1.0.0"}


def test_a_name_leaves_no_version_not_yet_released_where_no_caller_allows_one(
    tmp_path: Path,
) -> None:
    root = two_libraries(tmp_path, "1.0.0", "1.1.0")
    listing(root, "b@1.0.0")
    lock = {"a": "1.0.0", "b": "1.0.0"}

    moved = libraries.propose_lock(held(root), ["a", "b"], lock, names=["a@1.1.0"])

    assert moved.lock == {"a": "1.1.0", "b": "1.1.0"}


def test_a_drafts_search_is_as_it_was(tmp_path: Path) -> None:
    root = project(tmp_path)
    for version in ("1.0.0", "1.1.0", "1.2.0", "2.0.0"):
        add_library(root, "base", version)
    add_library(root, "base", "1.3.0", needs_release="9.0.0")
    listing(root, "base@1.2.0")

    moved = libraries.move_lock(held(root), ["base"], {"base": "1.0.0"})

    assert moved == libraries.Moved({"base": "1.2.0"})


# --- a copy of a library the capability ships, against what it ships (DEC-013 point 6) ---------

SHIPPED = {"kind": "shipped"}
COPY = "visual/libraries/foundations/1.0.0"


def capability(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, release: bool, building: str = "1.0.0"
) -> Path:
    """A capability's folder the test controls, in place of the capability's own for the
    length of the test: it builds the foundations at `building`, their files those of their
    release 1.0.0, and releases foundations@1.0.0, as it was built, where `release` says
    so."""
    folder = tmp_path / "capability"
    built = folder / "libraries" / "foundations"
    shutil.copytree(RELEASED_FOUNDATIONS, built)
    if release:
        shutil.copytree(built, shipped.place_of(folder, "foundations", V("1.0.0")))
        entry = shipped.entry_of(folder, "foundations", V("1.0.0"))
        listed = {"source": SHIPPED, "versions": {"1.0.0": entry}}
        write(
            folder / "releases" / "foundations" / "releases.yaml",
            yaml_text(bound("libraries", libraries={"foundations": listed})),
        )
    file = built / "library.yaml"
    file.write_text(
        file.read_text(encoding="utf-8").replace("version: 1.0.0", f"version: {building}")
    )
    monkeypatch.setattr(copies, "SHIPPED", folder)
    return folder


def judged(root: Path, code: str) -> list[tuple[Any, str]]:
    """Each finding of the check with the label `code`, with its level where it lies."""
    return [
        (finding, level) for finding, level in checks.check(root).judged if finding.code == code
    ]


@pytest.mark.parametrize("release", [True, False], ids=["shipped", "not-shipped"])
def test_library_changed_names_the_command_only_on_a_copy_of_a_version_the_capability_ships(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, release: bool
) -> None:
    capability(tmp_path, monkeypatch, release=release)
    root = project(tmp_path)
    copy_library(root, RELEASED_FOUNDATIONS, "foundations", "1.0.0")
    add_library(root, "charts", "1.0.0")
    entries = {name: released_entry(root, name, "1.0.0") for name in ("charts", "foundations")}
    write_list(
        root,
        {
            "charts": {"source": PROJECT, "versions": {"1.0.0": entries["charts"]}},
            "foundations": {"source": SHIPPED, "versions": {"1.0.0": entries["foundations"]}},
        },
    )
    assert judged(root, "library-changed") == judged(root, "copy-hash-differs") == []
    for name in ("charts", "foundations"):
        write(version_folder(root, name, "1.0.0") / "notes.txt", "Added after the release.\n")
    found = {
        finding.library: (finding.fix, level) for finding, level in judged(root, "library-changed")
    }
    restore = ("restore the version folder as it was released", "fails")
    add = ("run `pkit visual add foundations`, which restores it as released", "fails")
    assert found == {"charts@1.0.0": restore, "foundations@1.0.0": add if release else restore}


#: What the check says of a copy not released of a number the capability does not ship.
UNSHIPPED = (
    "move each draft that locks it, on purpose, to a version the capability ships, by pinning "
    "it to that version or by taking a new major; once no lock names the copy, take it out of "
    "the library folder and off the list"
)
#: What the check says of any other copy not released that is not what the capability ships.
ADD = (
    "run `pkit visual add foundations`, which replaces the copy with what the capability ships "
    "under its number"
)


@pytest.mark.parametrize(
    ("case", "message", "fix"),
    [
        pytest.param(
            "files",
            "foundations@1.0.0, listed not released, holds other files than the installed "
            "capability ships under its number, the version being built: `notes.txt` is not in "
            "what the capability ships; `roles.yaml` differs",
            ADD,
            id="other-files",
        ),
        pytest.param(
            "released",
            "foundations@1.0.0 is listed not released, and the installed capability released it",
            ADD,
            id="released",
        ),
        pytest.param(
            "unshipped",
            "foundations@1.0.0 is listed not released, and the installed capability ships no "
            "foundations@1.0.0",
            UNSHIPPED,
            id="number-not-shipped",
        ),
    ],
)
def test_a_copy_not_released_that_is_not_what_the_capability_ships_asks_for_attention(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: str, message: str, fix: str
) -> None:
    building = "1.1.0" if case == "unshipped" else "1.0.0"
    capability(tmp_path, monkeypatch, release=case == "released", building=building)
    root = project(tmp_path)
    folder = copy_library(root, RELEASED_FOUNDATIONS, "foundations", "1.0.0")
    write_list(root, {"foundations": {"source": SHIPPED, "versions": {"1.0.0": UNRELEASED}}})
    if case == "files":
        assert judged(root, "copy-not-shipped") == []
        write(folder / "notes.txt", "Added in the copy.\n")
        roles = folder / "roles.yaml"
        roles.write_text(roles.read_text(encoding="utf-8") + "# changed in the copy\n")
    [(finding, level)] = judged(root, "copy-not-shipped")
    assert (level, finding.who, finding.library) == ("attention", "the project", "")
    assert checks.place(finding) == COPY
    assert (finding.message, finding.fix) == (message, fix)


def test_a_released_copy_whose_hash_differs_from_the_capabilitys_names_both(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    folder = capability(tmp_path, monkeypatch, release=True)
    recorded = shipped.entry_of(folder, "foundations", V("1.0.0"))["hash"]["value"]
    root = project(tmp_path)
    copy = copy_library(root, RELEASED_FOUNDATIONS, "foundations", "1.0.0")
    roles = copy / "roles.yaml"
    role = "  space.4: {type: dimension}\n"
    added = role + "  space.5: {type: dimension}\n"
    roles.write_text(roles.read_text(encoding="utf-8").replace(role, added))
    entry = released_entry(root, "foundations", "1.0.0")
    write_list(root, {"foundations": {"source": SHIPPED, "versions": {"1.0.0": entry}}})
    [(finding, level)] = judged(root, "copy-hash-differs")
    assert (level, finding.who) == ("attention", "the project")
    list_file = "visual/libraries/libraries.yaml"
    assert checks.place(finding) == f"{list_file}#libraries.foundations.versions.1.0.0.hash"
    assert finding.message == (
        f"{list_file} keeps the hash `{entry['hash']['value']}` for foundations@1.0.0, released, "
        f"and the installed capability records `{recorded}`: two contents carry one released "
        f"number"
    )
    assert entry["hash"]["value"] != recorded
    assert finding.fix == (
        "choose which content foundations@1.0.0 holds: `pkit visual add foundations` refuses "
        "while the two hashes differ"
    )
    write(copy / "notes.txt", "Added after the release.\n")
    [(changed, _)] = judged(root, "library-changed")
    assert changed.fix == "restore the version folder as it was released"
