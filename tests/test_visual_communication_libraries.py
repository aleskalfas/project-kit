"""The library folder, its list, versions, and a piece's lock (DEC-001 point 5, DEC-003
points 1, 4, 8 and 9, DEC-004 point 6). Each project is laid in the test's own folder,
outside git, so its files are listed by walking."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest

from tests.in_process import load
from tests.visual_communication_project import (
    CAPABILITY,
    FOUNDATIONS,
    TEST_BRAND,
    TEST_EDITION,
    add_library,
    bound,
    copy_library,
    project,
    version_folder,
    write,
    write_list,
    write_piece,
    yaml_text,
)

libraries, fingerprint, files, reading, checks, pl = load(
    "visual-communication", "libraries", "fingerprint", "files", "reading", "checks", "pipeline"
)

V = libraries.Version.parse
RELEASE = (0, 1, 0)
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
        V("1.0.0"),
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
    assert found[1].library == "arrows@1.0.0"
    assert found[3].where == "libraries.charts.versions.2.0.0"


def test_a_released_version_that_changed_is_a_finding(tmp_path: Path) -> None:
    root = project(tmp_path)
    folder = copy_library(root, FOUNDATIONS, "foundations", "1.0.0")
    write_list(
        root,
        {
            "foundations": {
                "source": {"kind": "shipped"},
                "versions": {"1.0.0": released_entry(root, "foundations", "1.0.0")},
            }
        },
    )
    assert held(root).findings() == []
    roles = folder / "roles.yaml"
    roles.write_text(roles.read_text(encoding="utf-8") + "# a comment changes no value\n")
    assert held(root).findings() == []
    roles.write_text(roles.read_text(encoding="utf-8").replace("space.4", "space.5"))
    (finding,) = held(root).findings()
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
    copy_library(root, FOUNDATIONS, "foundations", "1.0.0")
    copy_library(root, TEST_BRAND, "test-brand", "1.0.0")
    lock = libraries.move_lock(libraries.Held(root, "visual"), ["foundations", "test-brand"])
    assert lock == {"foundations": "1.0.0", "test-brand": "1.0.0"}


def edition_project(tmp_path: Path) -> Path:
    """The shipped foundations, the test brand, and the test edition built on it."""
    root = project(tmp_path)
    copy_library(root, FOUNDATIONS, "foundations", "1.0.0")
    copy_library(root, TEST_BRAND, "test-brand", "1.0.0")
    copy_library(root, TEST_EDITION, "test-edition", "1.0.0")
    return root


def test_a_brands_lock_names_its_base(tmp_path: Path) -> None:
    root = edition_project(tmp_path)
    roots = ["foundations", "test-edition"]
    lock = libraries.move_lock(held(root), roots)
    assert lock == {"foundations": "1.0.0", "test-brand": "1.0.0", "test-edition": "1.0.0"}
    without_base = {"foundations": "1.0.0", "test-edition": "1.0.0"}
    with pytest.raises(libraries.LockRefused, match="needs `test-brand`, which its pinned lock"):
        libraries.move_lock(held(root), roots, without_base, pinned=True)


def test_the_check_finds_a_lock_that_leaves_out_a_brands_base(tmp_path: Path) -> None:
    root = edition_project(tmp_path)
    lock = {"foundations": "1.0.0", "test-edition": "1.0.0"}
    write_piece(root, "card", brand="test-edition", lock=lock)
    write(root / "visual/pieces/card/content.en.yaml", yaml_text(bound("content", caption="x")))
    (finding,) = checks.lock_findings(held(root), pl.read_piece(root, "visual", "card"))
    assert finding.code == "lock-incomplete"
    assert "test-edition@1.0.0 builds on `test-brand`" in finding.message


def test_a_first_lock_takes_the_newest_of_each_with_what_it_builds_on(tmp_path: Path) -> None:
    root = project(tmp_path)
    add_library(root, "base", "1.0.0")
    add_library(root, "base", "1.2.0")
    add_library(root, "charts", "1.0.0", builds_on={"base": 1})
    add_library(root, "charts", "2.1.0", builds_on={"base": 1})
    assert libraries.move_lock(held(root), ["charts"]) == {"base": "1.2.0", "charts": "2.1.0"}


def test_a_lock_moves_within_the_lines_it_names(tmp_path: Path) -> None:
    root = project(tmp_path)
    add_library(root, "base", "1.0.0")
    add_library(root, "base", "1.3.0")
    add_library(root, "base", "2.0.0")
    add_library(root, "extra", "3.0.0")
    lock = libraries.move_lock(held(root), ["base", "extra"], {"base": "1.0.0"})
    assert lock == {"base": "1.3.0", "extra": "3.0.0"}


def test_a_lock_skips_a_newer_version_the_capability_cannot_read(tmp_path: Path) -> None:
    root = project(tmp_path)
    add_library(root, "base", "1.0.0")
    add_library(root, "base", "1.1.0", needs_release="9.0.0")
    assert libraries.move_lock(held(root), ["base"]) == {"base": "1.0.0"}


def test_a_lock_backs_off_library_by_library_where_two_build_on_two_majors(
    tmp_path: Path,
) -> None:
    root = project(tmp_path)
    add_library(root, "base", "1.0.0")
    add_library(root, "base", "2.0.0")
    add_library(root, "a", "1.0.0", builds_on={"base": 1})
    add_library(root, "a", "2.0.0", builds_on={"base": 2})
    add_library(root, "b", "1.0.0", builds_on={"base": 1})
    lock = libraries.move_lock(held(root), ["a", "b"])
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
    assert libraries.move_lock(held(root), ["charts"], lock, pinned=True) == lock


@pytest.mark.parametrize(
    ("lock", "said"),
    [
        (None, "has no lock yet"),
        ({"charts": "1.0.0"}, "needs `base`, which its pinned lock does not name"),
        ({"base": "1.0.0", "charts": "1.1.0"}, "charts@1.1.0, which the project does not hold"),
        ({"base": "2.0.0", "charts": "1.0.0"}, "base@2.0.0, which the project does not hold"),
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
    with pytest.raises(libraries.LockRefused, match="builds on `base` 1"):
        libraries.move_lock(held(root), ["charts"], lock, pinned=True)


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
