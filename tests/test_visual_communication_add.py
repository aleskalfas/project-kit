"""`pkit visual add <library>` (visual-communication DEC-002 point 3, DEC-003 points 4 and
5, DEC-013 point 5): the version the capability ships copied whole into the location's
library folder and listed, every other byte of the list kept; never over a folder the list
does not name; refused where its files lack their binding, or the capability does not ship
the library. Run in this process (`tests/in_process.py`); it starts no `pkit`.

The tests of the released versions build a capability's folder of their own, with a
released version of the foundations and a version being built: the newest released version
taken with its hash, or another the person names, or the version being built; and every
copy of the library brought up to date in the same run, under the locks that name it.

The tests of sync install the capability in an adopter's repository and show that `pkit
sync` and an upgrade write nothing into the location: only the command copies a library
there."""

from __future__ import annotations

import errno
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from project_kit import install, sync, upgrade
from project_kit.cli import main
from tests.adopter_repo import MakeAdopterRepo
from tests.in_process import load, run_main
from tests.visual_communication_project import (
    CONFIG,
    FOUNDATIONS,
    bound,
    copy_library,
    project,
    write,
    write_list,
    write_piece,
    yaml_text,
)
from tests.visual_communication_writes import FULL, failing

script, libraries, reading, copies, shipped = load(
    "visual-communication", "add.py", "libraries", "reading", "copies", "shipped"
)

LIST = "visual/libraries/libraries.yaml"
COPY = "visual/libraries/foundations/1.0.0"
LOCATION = (
    f"recorded the location `visual` (the default, at the repository's top) in {CONFIG}; "
    f"to move the work, move the folder and change the `location:` line there"
)
#: The foundations, as the list names them once the command copied them.
LISTED = {"source": {"kind": "shipped"}, "versions": {"1.0.0": {"released": False}}}


def run(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return run_main(script, *args, cwd=root)


def tree(folder: Path) -> dict[str, bytes]:
    """Every file under `folder`, relative to it, with its bytes."""
    return {
        path.relative_to(folder).as_posix(): path.read_bytes()
        for path in sorted(folder.rglob("*"))
        if path.is_file()
    }


def capability(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A capability's folder the test controls, building a copy of the foundations and
    releasing none, in place of the capability's own for the length of the test."""
    folder = tmp_path / "capability"
    shutil.copytree(FOUNDATIONS, folder / "libraries" / "foundations")
    monkeypatch.setattr(copies, "SHIPPED", folder)
    return folder


# --- the copy and the list --------------------------------------------------------------------


def test_the_shipped_version_is_copied_whole_and_listed(tmp_path: Path) -> None:
    root = project(tmp_path)
    added = run(root, "foundations")
    assert added.returncode == 0, added.stderr
    assert tree(root / COPY) == tree(FOUNDATIONS)
    assert reading.read_yaml(root / LIST) == bound("libraries", libraries={"foundations": LISTED})
    assert added.stdout.splitlines() == [
        LOCATION,
        f"copied foundations@1.0.0, {len(tree(FOUNDATIONS))} files, to {COPY}/",
        f"listed foundations@1.0.0 in {LIST}, from the source `shipped`, not released",
    ]
    assert libraries.Held(root, "visual").findings() == []


def test_a_list_written_whole_opens_with_its_comment(tmp_path: Path) -> None:
    root = project(tmp_path)
    assert run(root, "foundations").returncode == 0
    text = (root / LIST).read_text(encoding="utf-8")
    assert text.startswith(
        "# The list of the project's libraries (visual-communication DEC-003 point 4): each\n"
    )
    assert "\n\npkit_schema: visual-communication:libraries\nschema_version: 1\n" in text


def test_the_list_takes_the_library_and_keeps_every_other_byte(tmp_path: Path) -> None:
    root = project(tmp_path)
    original = (
        "﻿# Our libraries.\r\n"
        "pkit_schema: visual-communication:libraries\r\n"
        "schema_version: 1\r\n"
        "libraries:\r\n"
        "    brand:  # ours\r\n"
        "        source: {kind: project}\r\n"
        "        versions: {1.0.0: {released: false}}\r\n"
        "\r\n"
        "# The end.\r\n"
    )
    (root / "visual" / "libraries").mkdir(parents=True)
    (root / LIST).write_bytes(original.encode("utf-8"))
    assert run(root, "foundations").returncode == 0
    assert (root / LIST).read_bytes().decode("utf-8") == original.replace(
        "{1.0.0: {released: false}}\r\n",
        "{1.0.0: {released: false}}\r\n"
        "    foundations:\r\n"
        "      source:\r\n"
        "        kind: shipped\r\n"
        "      versions:\r\n"
        "        1.0.0:\r\n"
        "          released: false\r\n",
    )


def test_a_version_is_added_to_the_shipped_library_the_list_names(tmp_path: Path) -> None:
    root = project(tmp_path)
    original = (
        "pkit_schema: visual-communication:libraries\n"
        "schema_version: 1\n"
        "libraries:\n"
        "  foundations:\n"
        "    source: {kind: shipped}\n"
        "    versions: {2.0.0: {released: false}}  # the newer line\n"
    )
    write(root / LIST, original)
    assert run(root, "foundations").returncode == 0
    assert (root / LIST).read_text(encoding="utf-8") == original.replace(
        "{2.0.0: {released: false}}", "{2.0.0: {released: false}, 1.0.0: {released: false}}"
    )
    assert tree(root / COPY) == tree(FOUNDATIONS)


def test_an_empty_list_takes_the_library_in_its_flow(tmp_path: Path) -> None:
    root = project(tmp_path)
    write_list(root, {})
    assert run(root, "foundations").returncode == 0
    assert (
        (root / LIST)
        .read_text(encoding="utf-8")
        .endswith(
            "libraries: {foundations: {source: {kind: shipped}, versions: {1.0.0: {released: "
            "false}}}}\n"
        )
    )
    assert reading.read_yaml(root / LIST)["libraries"] == {"foundations": LISTED}


# --- what it never overwrites -----------------------------------------------------------------


@pytest.mark.parametrize("held", ["changed", "empty"])
def test_a_folder_the_list_does_not_name_is_never_overwritten(tmp_path: Path, held: str) -> None:
    root = project(tmp_path)
    if held == "changed":
        folder = copy_library(root, FOUNDATIONS, "foundations", "1.0.0")
        write(folder / "roles.yaml", "# Changed by the project.\n")
    else:
        (root / COPY).mkdir(parents=True)
    before = tree(root)
    added = run(root, "foundations")
    assert added.returncode == 1
    assert added.stdout == ""
    assert added.stderr == (
        f"error: {COPY} lies in the library folder already, though {LIST} does not name it: "
        f"list it, or take the folder out\n"
    )
    assert tree(root) == before


def test_a_version_the_list_names_without_its_folder_is_brought_in(tmp_path: Path) -> None:
    root = project(tmp_path)
    write_list(root, {"foundations": LISTED})
    listed = (root / LIST).read_bytes()
    added = run(root, "foundations")
    assert added.returncode == 0, added.stderr
    assert tree(root / COPY) == tree(FOUNDATIONS)
    assert (root / LIST).read_bytes() == listed
    assert added.stdout.splitlines()[1:] == [
        f"replaced foundations@1.0.0, {len(tree(FOUNDATIONS))} files, in {COPY}/, with the "
        f"version being built, its folder missing before"
    ]


def test_a_library_the_list_names_from_another_source_is_refused(tmp_path: Path) -> None:
    root = project(tmp_path)
    write_list(root, {"foundations": {"source": {"kind": "project"}, "versions": {}}})
    before = tree(root)
    added = run(root, "foundations")
    assert added.returncode == 1
    assert added.stderr.startswith(
        f"error: {LIST} names `foundations` from another source than the capability's, and a "
        f"name ties one library to its source"
    )
    assert tree(root) == before


def test_a_list_that_cannot_take_the_version_as_text_is_refused(tmp_path: Path) -> None:
    root = project(tmp_path)
    write(
        root / LIST,
        "pkit_schema: visual-communication:libraries\nschema_version: 1\nlibraries: {\n"
        "  brand: {source: {kind: project}, versions: {}}}\n",
    )
    before = tree(root)
    added = run(root, "foundations")
    assert added.returncode == 1
    assert added.stderr == (
        f"error: {LIST} cannot take foundations@1.0.0 as text: write `libraries` as a block "
        f"mapping, one library an entry\n"
    )
    assert tree(root) == before


def test_a_list_that_cannot_be_read_is_refused(tmp_path: Path) -> None:
    root = project(tmp_path)
    write(root / LIST, "libraries: {}\n")
    added = run(root, "foundations")
    assert added.returncode == 1
    assert added.stderr.startswith("error: the list of libraries cannot be read: ")
    assert "names no schema" in added.stderr
    assert not (root / COPY).exists()


# --- what it refuses to copy ------------------------------------------------------------------


@pytest.mark.parametrize("file", ["components/figure.yaml", "library.yaml"])
def test_a_copy_whose_files_lack_their_binding_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, file: str
) -> None:
    folder = capability(tmp_path, monkeypatch) / "libraries" / "foundations"
    path = folder / file
    path.write_text(
        "".join(
            line
            for line in path.read_text(encoding="utf-8").splitlines(keepends=True)
            if not line.startswith("pkit_schema:")
        ),
        encoding="utf-8",
    )
    root = project(tmp_path)
    added = run(root, "foundations")
    assert added.returncode == 1
    assert added.stderr.startswith(
        f"error: the shipped `foundations` cannot be copied: {file} names no schema: add "
        f"`pkit_schema: visual-communication:"
    )
    assert not (root / "visual").exists()
    assert not (root / CONFIG).exists()


def test_a_library_the_capability_does_not_ship_is_refused_naming_the_ones_it_ships(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = project(tmp_path)
    added = run(root, "charts")
    assert added.returncode == 1
    assert added.stderr == (
        "error: the capability ships no library `charts`; it ships `foundations`, `neutral`, "
        "`starter`\n"
    )
    folder = capability(tmp_path, monkeypatch)
    shutil.copytree(FOUNDATIONS, folder / "libraries" / "neutral")
    assert run(root, "../foundations").stderr == (
        "error: the capability ships no library `../foundations`; it ships `foundations`, "
        "`neutral`\n"
    )
    assert not (root / "visual").exists()


@pytest.mark.parametrize(("file", "failed"), [("libraries.yaml", LIST), ("1.0.0", COPY)])
def test_a_write_that_fails_leaves_no_copy_no_list_and_no_location(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, file: str, failed: str
) -> None:
    root = project(tmp_path)
    with monkeypatch.context() as patch:
        failing(patch, write={file})
        added = run(root, "foundations")
    assert added.returncode == 1
    assert added.stdout == ""
    assert added.stderr == f"error: {failed} could not be written: {FULL}\n"
    assert not (root / "visual").exists()
    assert not (root / CONFIG).exists()


def test_a_write_that_fails_leaves_the_list_as_it_was(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = project(tmp_path)
    write_list(root, {})
    listed = (root / LIST).read_bytes()
    with monkeypatch.context() as patch:
        failing(patch, write={"libraries.yaml"})
        assert run(root, "foundations").returncode == 1
    assert tree(root / "visual") == {"libraries/libraries.yaml": listed}
    assert not (root / CONFIG).exists()


# --- the location -----------------------------------------------------------------------------


def test_the_location_a_person_names_is_recorded_and_takes_the_copy(tmp_path: Path) -> None:
    root = project(tmp_path)
    added = run(root, "foundations", "--location", "docs/art")
    assert added.returncode == 0, added.stderr
    assert "location: docs/art\n" in (root / CONFIG).read_text(encoding="utf-8")
    assert tree(root / "docs/art/libraries/foundations/1.0.0") == tree(FOUNDATIONS)
    assert not (root / "visual").exists()


def test_a_default_that_holds_other_files_is_refused_with_nothing_written(
    tmp_path: Path,
) -> None:
    root = project(tmp_path)
    write(root / "visual" / "notes.md", "Not visual work.\n")
    added = run(root, "foundations")
    assert added.returncode == 1
    assert "name the location with `--location <path>`" in added.stderr
    assert tree(root / "visual") == {"notes.md": b"Not visual work.\n"}
    assert not (root / CONFIG).exists()


def test_a_copy_into_a_location_already_recorded_records_nothing(tmp_path: Path) -> None:
    root = project(tmp_path)
    assert run(root, "foundations").returncode == 0
    shutil.rmtree(root / "visual" / "libraries")
    (root / "visual").mkdir(exist_ok=True)
    config = (root / CONFIG).read_bytes()
    added = run(root, "foundations")
    assert added.returncode == 0, added.stderr
    assert not added.stdout.startswith("recorded")
    assert (root / CONFIG).read_bytes() == config


# --- sync and an upgrade write nothing into the location ---------------------------------------


@pytest.fixture
def adopter(make_adopter_repo: MakeAdopterRepo, monkeypatch: pytest.MonkeyPatch) -> Path:
    """An adopter's repository with the capability installed, its query commands taken as
    provisioned, so nothing asks `uv`."""
    root = make_adopter_repo(capabilities=("visual-communication",)).root
    monkeypatch.setattr(install, "provision_query_commands", lambda *_a, **_k: None)
    return root


def _sync_and_upgrade(
    root: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """`pkit sync`; the capability's own upgrade; then `pkit upgrade`, over the capability
    recorded at an older version, so that its transition moves the capability, copy and
    migrations included."""
    sync.run_sync(root)
    upgraded = CliRunner().invoke(main, ["capabilities", "upgrade", "visual-communication"])
    assert upgraded.exit_code == 0, upgraded.output
    record = root / ".pkit/capabilities/visual-communication/project/manifest.yaml"
    text = record.read_text(encoding="utf-8")
    older = text.replace(f"version: {_shipped_version()}\n", "version: 0.0.1\n")
    assert older != text
    record.write_text(older, encoding="utf-8")
    monkeypatch.setattr(upgrade, "_latest_released_version", lambda: None)
    capsys.readouterr()
    upgrade.run_upgrade(root, pin=False, self_update=False)
    assert f"capability 'visual-communication': 0.0.1 -> {_shipped_version()}" in (
        capsys.readouterr().out
    )


def _shipped_version() -> str:
    package = reading.read_yaml(FOUNDATIONS.parents[1] / "package.yaml")
    return str(package["component"]["version"])


def test_sync_and_an_upgrade_bring_no_library_into_a_project(
    adopter: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    assert (adopter / ".pkit/capabilities/visual-communication/libraries/foundations").is_dir()
    _sync_and_upgrade(adopter, monkeypatch, capsys)
    assert not (adopter / "visual").exists()
    assert not (adopter / CONFIG).exists()


@pytest.mark.parametrize("where", ["visual", "art"], ids=["default", "recorded"])
def test_sync_and_an_upgrade_write_nothing_into_the_location(
    adopter: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], where: str
) -> None:
    if where != "visual":
        write(
            adopter / CONFIG,
            f"pkit_schema: visual-communication:config\nschema_version: 1\nlocation: {where}\n",
        )
    write_list(adopter, {}, location=where)
    write(adopter / where / "pieces" / "flow" / "piece.yaml", "# A piece.\n")
    before = tree(adopter / where)
    config = _bytes(adopter / CONFIG)
    _sync_and_upgrade(adopter, monkeypatch, capsys)
    assert tree(adopter / where) == before
    assert _bytes(adopter / CONFIG) == config
    assert (adopter / "visual").exists() == (where == "visual")


def _bytes(path: Path) -> bytes | None:
    return path.read_bytes() if path.exists() else None


# --- released versions, and every copy of the library (DEC-013 point 5) -------------------------

#: The project's copy of the version being built, and of the version being built next.
NEXT = "visual/libraries/foundations/1.1.0"


def set_fields(path: Path, **fields: Any) -> None:
    """A YAML file with `fields` set, its other keys kept."""
    data = dict(reading.read_yaml(path))
    data.update(fields)
    write(path, yaml_text(data))


def release(folder: Path) -> dict[str, Any]:
    """Release the foundations' version being built as it stands, in the capability's
    folder `folder`: its files copied to its place, and its entry added to its record,
    which it returns."""
    built = folder / "libraries" / "foundations"
    version = libraries.read_library(built).version
    shutil.copytree(built, shipped.place_of(folder, "foundations", version))
    record = folder / "releases" / "foundations" / "releases.yaml"
    if record.is_file():
        data = reading.read_yaml(record)
    else:
        library = {"source": {"kind": "shipped"}, "versions": {}}
        data = bound("libraries", libraries={"foundations": library})
    entry = shipped.entry_of(folder, "foundations", version)
    data["libraries"]["foundations"]["versions"][str(version)] = entry
    write(record, yaml_text(data))
    return entry


def build(folder: Path, version: str, about: str) -> None:
    """The version being built moved on to `version`, its figure's `about` changed."""
    built = folder / "libraries" / "foundations"
    set_fields(built / "library.yaml", version=version)
    set_fields(built / "components" / "figure.yaml", about=about)


@pytest.fixture
def released(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, dict[str, Any]]:
    """A capability's folder that has released foundations 1.0.0 and builds 1.1.0, in place
    of the capability's own, and the record's entry of 1.0.0."""
    folder = capability(tmp_path, monkeypatch)
    entry = release(folder)
    build(folder, "1.1.0", "A figure being built.")
    return folder, entry


def place(folder: Path, version: str = "1.0.0") -> Path:
    return shipped.place_of(folder, "foundations", libraries.Version.parse(version))


def listed(root: Path) -> dict[str, Any]:
    """The versions of the foundations the list names."""
    return reading.read_yaml(root / LIST)["libraries"]["foundations"]["versions"]


def unreleased_copy(root: Path, about: str = "An older figure.") -> Path:
    """A copy of foundations 1.0.0 not yet released, taken before the release, so its figure
    differs from the released one, and listed `released: false`."""
    folder = copy_library(root, FOUNDATIONS, "foundations", "1.0.0")
    set_fields(folder / "components" / "figure.yaml", about=about)
    write_list(root, {"foundations": LISTED})
    return folder


def released_copy(root: Path, folder: Path, entry: dict[str, Any]) -> Path:
    """The released foundations 1.0.0, copied into the location as released, with `entry`."""
    copied = copy_library(root, place(folder), "foundations", "1.0.0")
    write_list(root, {"foundations": {"source": {"kind": "shipped"}, "versions": {"1.0.0": entry}}})
    return copied


def declaration(root: Path, name: str, lock: dict[str, str]) -> Path:
    """A declaration of written code whose lock is `lock`."""
    data = bound(
        "code", writer="css", form=1, brand="test-brand", lock=lock, out=f"styles/{name}.css"
    )
    return write(root / "visual" / "code" / f"{name}.yaml", yaml_text(data))


def test_the_newest_released_version_is_copied_and_listed_with_its_hash(
    tmp_path: Path, released: tuple[Path, dict[str, Any]]
) -> None:
    folder, entry = released
    root = project(tmp_path)
    added = run(root, "foundations")
    assert added.returncode == 0, added.stderr
    assert tree(root / COPY) == tree(place(folder))
    assert listed(root) == {"1.0.0": entry}
    assert added.stdout.splitlines()[1:] == [
        f"copied foundations@1.0.0, {len(tree(place(folder)))} files, to {COPY}/",
        f"listed foundations@1.0.0 in {LIST}, from the source `shipped`, released, with the "
        f"hash the capability records",
    ]
    assert libraries.Held(root, "visual").findings() == []


def test_the_version_being_built_is_copied_when_asked_not_released(
    tmp_path: Path, released: tuple[Path, dict[str, Any]]
) -> None:
    folder, _ = released
    root = project(tmp_path)
    added = run(root, "foundations", "--being-built")
    assert added.returncode == 0, added.stderr
    assert tree(root / NEXT) == tree(folder / "libraries" / "foundations")
    assert listed(root) == {"1.1.0": {"released": False}}
    assert added.stdout.splitlines()[-1] == (
        f"listed foundations@1.1.0 in {LIST}, from the source `shipped`, not released"
    )


def test_a_released_version_is_taken_by_its_number(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    folder = capability(tmp_path, monkeypatch)
    entry = release(folder)
    build(folder, "1.1.0", "The next figure.")
    newer = release(folder)
    build(folder, "1.2.0", "A figure being built.")
    root = project(tmp_path)
    assert run(root, "foundations@1.0.0").returncode == 0
    assert tree(root / COPY) == tree(place(folder))
    assert listed(root) == {"1.0.0": entry}
    assert run(root, "foundations").returncode == 0
    assert listed(root) == {"1.0.0": entry, "1.1.0": newer}


def test_a_number_the_capability_releases_no_version_of_is_refused(
    tmp_path: Path, released: tuple[Path, dict[str, Any]]
) -> None:
    root = project(tmp_path)
    added = run(root, "foundations@1.1.0")
    assert added.returncode == 1
    assert added.stderr == (
        "error: the capability releases no foundations@1.1.0; it releases 1.0.0. "
        "`--being-built` takes the version being built, foundations@1.1.0\n"
    )
    assert run(root, "foundations@1.0.0", "--being-built").stderr.startswith(
        "error: `foundations@1.0.0` names a released version, and `--being-built` asks for"
    )
    assert run(root, "foundations@1.0").stderr == (
        "error: `foundations@1.0`: `1.0` is not a version `X.Y.Z` with X at least 1\n"
    )
    assert not (root / "visual").exists()


def test_the_version_being_built_that_carries_a_released_number_is_the_released_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    folder = capability(tmp_path, monkeypatch)
    release(folder)
    set_fields(place(folder) / "library.yaml", **{"needs-release": "0.2.0"})
    data = reading.read_yaml(folder / "releases" / "foundations" / "releases.yaml")
    entry = shipped.entry_of(folder, "foundations", libraries.Version.parse("1.0.0"))
    data["libraries"]["foundations"]["versions"]["1.0.0"] = entry
    write(folder / "releases" / "foundations" / "releases.yaml", yaml_text(data))
    root = project(tmp_path)
    added = run(root, "foundations", "--being-built")
    assert added.returncode == 0, added.stderr
    assert tree(root / COPY) == tree(place(folder))
    assert listed(root) == {"1.0.0": entry}


def test_released_files_that_no_longer_match_their_hash_are_refused(
    tmp_path: Path, released: tuple[Path, dict[str, Any]]
) -> None:
    folder, _ = released
    set_fields(place(folder) / "components" / "figure.yaml", about="Changed after its release.")
    root = project(tmp_path)
    added = run(root, "foundations")
    assert added.returncode == 1
    assert added.stderr.startswith(
        "error: the capability's foundations@1.0.0 no longer matches the hash its record keeps: "
    )
    assert not (root / "visual").exists()
    assert not (root / CONFIG).exists()


def test_a_copy_not_released_under_an_unpinned_draft_is_replaced_and_listed_released(
    tmp_path: Path, released: tuple[Path, dict[str, Any]]
) -> None:
    folder, entry = released
    root = project(tmp_path)
    unreleased_copy(root)
    write_piece(root, "flow", lock={"foundations": "1.0.0", "test-brand": "1.0.0"})
    write(root / "visual" / "pieces" / "flow" / "content.en.yaml", "not: [content\n")
    write_piece(root, "other", lock={"foundations": "1.1.0"}, pinned=True)
    added = run(root, "foundations")
    assert added.returncode == 0, added.stderr
    assert tree(root / COPY) == tree(place(folder))
    assert listed(root) == {"1.0.0": entry}
    assert added.stdout.splitlines()[1:] == [
        f"replaced foundations@1.0.0, {len(tree(place(folder)))} files, in {COPY}/, with the "
        f"released version",
        "  locked by the draft `flow`",
        f"listed foundations@1.0.0 in {LIST} as released, with the hash the capability records",
    ]
    assert libraries.Held(root, "visual").findings() == []


@pytest.mark.parametrize("held_by", ["pinned", "code", "unreadable", "final"])
def test_a_copy_not_released_under_a_lock_that_moves_on_purpose_stays_and_the_run_goes_on(
    tmp_path: Path, released: tuple[Path, dict[str, Any]], held_by: str
) -> None:
    folder, _ = released
    root = project(tmp_path)
    copy = unreleased_copy(root)
    write_piece(root, "flow", lock={"foundations": "1.0.0"})
    if held_by == "pinned":
        write_piece(root, "poster", lock={"foundations": "1.0.0"}, pinned=True)
        named = "  the pinned draft `poster`"
    elif held_by == "code":
        declaration(root, "css", {"foundations": "1.0.0", "test-brand": "1.0.0"})
        named = "  the declaration `css` of written code"
    elif held_by == "unreadable":
        write(root / "visual" / "pieces" / "poster" / "piece.yaml", "lock: [\n")
        named = (
            "  visual/pieces/poster/piece.yaml, whose lock cannot be read: does not parse as YAML"
        )
    else:
        write_piece(root, "poster", lock={"foundations": "2.0.0"}, state="final")
        named = (
            "  visual/pieces/poster/piece.yaml, whose lock cannot be read: its state `final` is "
            "not one format 1 takes"
        )
    before = tree(copy)
    added = run(root, "foundations", "--being-built")
    assert added.returncode == 0, added.stderr
    assert tree(copy) == before
    assert tree(root / NEXT) == tree(folder / "libraries" / "foundations")
    assert listed(root) == {"1.0.0": {"released": False}, "1.1.0": {"released": False}}
    lines = added.stdout.splitlines()
    assert lines[1] == f"copied foundations@1.1.0, {len(tree(root / NEXT))} files, to {NEXT}/"
    assert lines[2] == (
        "left foundations@1.0.0 as it is: a lock that moves only on purpose names it"
    )
    assert lines[3].startswith(named)
    assert len(lines) == 5


def test_a_released_copy_changed_is_restored_and_one_intact_is_not_written(
    tmp_path: Path, released: tuple[Path, dict[str, Any]]
) -> None:
    folder, entry = released
    root = project(tmp_path)
    copy = released_copy(root, folder, entry)
    write_piece(root, "poster", lock={"foundations": "1.0.0"}, pinned=True)
    set_fields(copy / "components" / "figure.yaml", about="Changed by the project.")
    write(copy / "components" / "extra.yaml", "# Added by the project.\n")
    list_before = (root / LIST).read_bytes()
    added = run(root, "foundations")
    assert added.returncode == 0, added.stderr
    assert tree(copy) == tree(place(folder))
    assert (root / LIST).read_bytes() == list_before
    lines = added.stdout.splitlines()
    assert lines[1].startswith(
        f"restored foundations@1.0.0, {len(tree(place(folder)))} files, in {COPY}/, as released: "
    )
    assert lines[2:] == ["  locked by the pinned draft `poster`"]
    assert not [path for path in copy.parent.iterdir() if path.name != "1.0.0"]
    again = run(root, "foundations")
    assert again.returncode == 0, again.stderr
    assert again.stdout.splitlines() == [
        "left foundations@1.0.0 as it is: released, and its files match its hash"
    ]
    assert tree(copy) == tree(place(folder))


def test_a_released_copy_whose_folder_is_missing_is_restored(
    tmp_path: Path, released: tuple[Path, dict[str, Any]]
) -> None:
    folder, entry = released
    root = project(tmp_path)
    shutil.rmtree(released_copy(root, folder, entry))
    added = run(root, "foundations")
    assert added.returncode == 0, added.stderr
    assert tree(root / COPY) == tree(place(folder))
    assert "as released: the project no longer holds its folder" in added.stdout


def test_a_hash_the_list_keeps_that_differs_from_the_records_is_refused_naming_both(
    tmp_path: Path, released: tuple[Path, dict[str, Any]]
) -> None:
    folder, entry = released
    root = project(tmp_path)
    other = {**entry, "hash": {**entry["hash"], "value": "0" * 64}}
    copy = released_copy(root, folder, other)
    before = tree(root)
    added = run(root, "foundations", "--being-built")
    assert added.returncode == 1
    assert added.stderr == (
        f"error: {LIST} keeps the hash `{'0' * 64}` for foundations@1.0.0, released, and the "
        f"capability records `{entry['hash']['value']}`: two contents carry one released "
        f"number\n"
    )
    assert tree(root) == before
    assert copy.is_dir()


def test_a_new_number_is_copied_beside_the_others_and_replaces_none(
    tmp_path: Path, released: tuple[Path, dict[str, Any]]
) -> None:
    folder, entry = released
    root = project(tmp_path)
    copy = released_copy(root, folder, entry)
    before = tree(copy)
    added = run(root, "foundations", "--being-built")
    assert added.returncode == 0, added.stderr
    assert tree(copy) == before
    assert tree(root / NEXT) == tree(folder / "libraries" / "foundations")
    assert listed(root) == {"1.0.0": entry, "1.1.0": {"released": False}}
    assert added.stdout.splitlines()[1:] == [
        f"copied foundations@1.1.0, {len(tree(root / NEXT))} files, to {NEXT}/",
        "left foundations@1.0.0 as it is: released, and its files match its hash",
        f"listed foundations@1.1.0 in {LIST}, from the source `shipped`, not released",
    ]


def test_a_copy_of_a_number_the_capability_does_not_ship_stays_as_it_is(
    tmp_path: Path, released: tuple[Path, dict[str, Any]]
) -> None:
    folder, entry = released
    root = project(tmp_path)
    old = copy_library(root, FOUNDATIONS, "foundations", "2.0.0")
    unlisted = copy_library(root, FOUNDATIONS, "foundations", "1.5.0")
    versions = {"2.0.0": {"released": False}, "1.0.0": entry}
    copy_library(root, place(folder), "foundations", "1.0.0")
    write_list(root, {"foundations": {"source": {"kind": "shipped"}, "versions": versions}})
    write_piece(root, "flow", lock={"foundations": "2.0.0"})
    before = {"old": tree(old), "unlisted": tree(unlisted)}
    added = run(root, "foundations")
    assert added.returncode == 0, added.stderr
    assert {"old": tree(old), "unlisted": tree(unlisted)} == before
    assert added.stdout.splitlines()[1:] == [
        "left foundations@2.0.0 as it is: the installed capability ships no foundations@2.0.0",
        f"left foundations@1.5.0 as it is: {LIST} does not name it",
        "left foundations@1.0.0 as it is: released, and its files match its hash",
    ]


def test_a_copy_not_released_that_holds_what_the_capability_ships_is_not_written(
    tmp_path: Path, released: tuple[Path, dict[str, Any]]
) -> None:
    folder, _ = released
    root = project(tmp_path)
    copy_library(root, folder / "libraries" / "foundations", "foundations", "1.1.0")
    write_list(
        root,
        {
            "foundations": {
                "source": {"kind": "shipped"},
                "versions": {"1.1.0": {"released": False}},
            }
        },
    )
    list_before = (root / LIST).read_bytes()
    added = run(root, "foundations", "--being-built")
    assert added.returncode == 0, added.stderr
    assert (root / LIST).read_bytes() == list_before
    assert added.stdout.splitlines()[1:] == [
        "left foundations@1.1.0 as it is: it holds the version being built of its number already"
    ]


@pytest.mark.parametrize("failed", [LIST, COPY])
def test_a_write_that_fails_puts_back_the_copy_it_replaced_and_the_list(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    released: tuple[Path, dict[str, Any]],
    failed: str,
) -> None:
    root = project(tmp_path)
    copy = unreleased_copy(root)
    before = tree(root)
    with monkeypatch.context() as patch:
        if failed == LIST:
            failing(patch, write={"libraries.yaml"})
        else:
            rename = os.rename

            def full(source: Any, target: Any) -> None:
                # The copy cannot be moved into its place; the folder moved aside can.
                if Path(target).name == "1.0.0" and Path(source).name.endswith(".tmp"):
                    raise OSError(errno.ENOSPC, FULL, str(target))
                rename(source, target)

            patch.setattr(os, "rename", full)
        added = run(root, "foundations")
    assert added.returncode == 1
    assert added.stdout == ""
    assert (
        added.stderr
        == f"error: {failed} could not be {'written' if failed == LIST else 'replaced'}: {FULL}\n"
    )
    assert tree(root) == before
    assert sorted(path.name for path in copy.parent.iterdir()) == ["1.0.0"]
    assert not (root / CONFIG).exists()
