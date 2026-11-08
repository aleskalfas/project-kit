"""`pkit visual add <library>` (visual-communication DEC-002 point 3, DEC-003 points 4 and
5, DEC-013 point 5): the version the capability ships copied whole into the location's
library folder and listed, every other byte of the list kept; never over a folder the list
does not name; refused where its files lack their binding, or the capability does not ship
the library. Run in this process (`tests/in_process.py`); it starts no `pkit`.

The tests of the copy and the list read what the capability ships from the tree: the
newest released version, or the version being built where none is released. Those that
read a version listed not released, and the text the list takes of it, build a
capability's folder of their own that releases none.

The tests of the released versions build a capability's folder of their own, with a
released version of the foundations and a version being built: the newest released version
taken with its hash, or another the person names, or the version being built; and every
copy of the library brought up to date in the same run, under the locks that name it.

The last tests name a lock that moves only on purpose in the command, and read the
before-and-after a run shows of a lock it leaves: a piece's scenes drawn both ways,
and the difference in the code a declaration's writer writes (DEC-013 point 5).

The tests of sync install the capability in an adopter's repository and show that `pkit
sync` and an upgrade write nothing into the location: only the command copies a library
there."""

from __future__ import annotations

import errno
import os
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from project_kit import install, sync, upgrade
from project_kit.cli import main
from tests.adopter_repo import MakeAdopterRepo
from tests.in_process import load, run_main
from tests.test_visual_communication_pipeline import lay_out_drawing
from tests.visual_communication_project import (
    CAPABILITY,
    CONFIG,
    FOUNDATIONS,
    RELEASED_FOUNDATIONS,
    TEST_BRAND,
    TEST_PARTS,
    bound,
    built_as_released,
    copy_library,
    importable,
    project,
    taken,
    write,
    write_list,
    write_piece,
    yaml_text,
)
from tests.visual_communication_writes import FULL, failing

script, libraries, reading, copies, shipped, before_after, exports, pl, svg, css = load(
    "visual-communication",
    "add.py",
    "libraries",
    "reading",
    "copies",
    "shipped",
    "before_after",
    "exports",
    "pipeline",
    "plugins.svg",
    "plugins.css",
)

LIST = "visual/libraries/libraries.yaml"
COPY = "visual/libraries/foundations/1.0.0"
LOCATION = (
    f"recorded the location `visual` (the default, at the repository's top) in {CONFIG}; "
    f"to move the work, move the folder and change the `location:` line there"
)
#: The foundations, as the list names them once the command copied them from a capability
#: that releases none.
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
    """A capability's folder the test controls, building the foundations as they stood when
    1.0.0 was released and releasing none, in place of the capability's own for the length
    of the test."""
    folder = tmp_path / "capability"
    built_as_released(folder / "libraries" / "foundations")
    monkeypatch.setattr(copies, "SHIPPED", folder)
    return folder


# --- the copy and the list --------------------------------------------------------------------


def test_the_shipped_version_is_copied_whole_and_listed(tmp_path: Path) -> None:
    """What the capability ships by default, as the tree holds it: the newest released
    version, with its record's entry, or the version being built where none is released."""
    ships = taken("foundations")
    label = f"foundations@{ships.version}"
    copy = f"visual/libraries/foundations/{ships.version}"
    state = "released, with the hash the capability records"
    if not ships.entry["released"]:
        state = "not released"
    root = project(tmp_path)
    added = run(root, "foundations")
    assert added.returncode == 0, added.stderr
    assert tree(root / copy) == tree(ships.folder)
    versions = {ships.version: ships.entry}
    assert reading.read_yaml(root / LIST) == bound(
        "libraries",
        libraries={"foundations": {"source": {"kind": "shipped"}, "versions": versions}},
    )
    assert added.stdout.splitlines() == [
        LOCATION,
        f"copied {label}, {len(tree(ships.folder))} files, to {copy}/",
        f"listed {label} in {LIST}, from the source `shipped`, {state}",
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


def test_the_list_takes_the_library_and_keeps_every_other_byte(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    capability(tmp_path, monkeypatch)
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


def test_a_version_is_added_to_the_shipped_library_the_list_names(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    folder = capability(tmp_path, monkeypatch)
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
    assert tree(root / COPY) == tree(folder / "libraries" / "foundations")


def test_an_empty_list_takes_the_library_in_its_flow(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    capability(tmp_path, monkeypatch)
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
        folder = copy_library(root, RELEASED_FOUNDATIONS, "foundations", "1.0.0")
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


def test_a_version_the_list_names_without_its_folder_is_brought_in(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    folder = capability(tmp_path, monkeypatch)
    root = project(tmp_path)
    write_list(root, {"foundations": LISTED})
    listed = (root / LIST).read_bytes()
    added = run(root, "foundations")
    assert added.returncode == 0, added.stderr
    assert tree(root / COPY) == tree(folder / "libraries" / "foundations")
    assert (root / LIST).read_bytes() == listed
    assert added.stdout.splitlines()[1:] == [
        f"replaced foundations@1.0.0, {len(tree(RELEASED_FOUNDATIONS))} files, in {COPY}/, "
        f"with the version being built, its folder missing before"
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
    ships = taken("foundations")
    root = project(tmp_path)
    added = run(root, "foundations", "--location", "docs/art")
    assert added.returncode == 0, added.stderr
    assert "location: docs/art\n" in (root / CONFIG).read_text(encoding="utf-8")
    assert tree(root / "docs/art/libraries/foundations" / ships.version) == tree(ships.folder)
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
    folder = copy_library(root, RELEASED_FOUNDATIONS, "foundations", "1.0.0")
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


@pytest.mark.parametrize("fields", [{}, {"pinned": True}], ids=["not-pinned", "pinned"])
def test_a_copy_not_released_under_a_final_pieces_lock_is_replaced_with_no_piece_named(
    tmp_path: Path, released: tuple[Path, dict[str, Any]], fields: dict[str, Any]
) -> None:
    folder, entry = released
    root = project(tmp_path)
    unreleased_copy(root)
    final = write_piece(root, "poster", lock={"foundations": "1.0.0"}, state="final", **fields)
    piece = final.read_bytes()
    added = run(root, "foundations")
    assert added.returncode == 0, added.stderr
    assert final.read_bytes() == piece
    assert tree(root / COPY) == tree(place(folder))
    assert listed(root) == {"1.0.0": entry}
    assert added.stdout.splitlines()[1:] == [
        f"replaced foundations@1.0.0, {len(tree(place(folder)))} files, in {COPY}/, with the "
        f"released version",
        "  locked by the final piece `poster`",
        f"listed foundations@1.0.0 in {LIST} as released, with the hash the capability records",
    ]


@pytest.mark.parametrize("held_by", ["pinned", "published", "code", "unreadable", "no-such-state"])
def test_a_copy_not_released_under_a_lock_that_moves_on_purpose_stays_and_the_run_goes_on(
    tmp_path: Path, released: tuple[Path, dict[str, Any]], held_by: str
) -> None:
    folder, _ = released
    root = project(tmp_path)
    copy = unreleased_copy(root)
    write_piece(root, "flow", lock={"foundations": "1.0.0"})
    way = []
    if held_by == "pinned":
        write_piece(root, "poster", lock={"foundations": "1.0.0"}, pinned=True)
        named = "  the pinned draft `poster`"
        way = ["  to replace it, run `pkit visual add foundations --piece poster`"]
    elif held_by == "published":
        write_piece(root, "poster", lock={"foundations": "1.0.0"}, state="published")
        named = "  the published piece `poster`"
        way = ["  to replace it, run `pkit visual add foundations --piece poster`"]
    elif held_by == "code":
        declaration(root, "css", {"foundations": "1.0.0", "test-brand": "1.0.0"})
        named = "  the declaration `css` of written code"
        way = ["  to replace it, run `pkit visual add foundations --declaration css`"]
    elif held_by == "unreadable":
        write(root / "visual" / "pieces" / "poster" / "piece.yaml", "lock: [\n")
        named = (
            "  visual/pieces/poster/piece.yaml, whose lock cannot be read: does not parse as YAML"
        )
    else:
        write_piece(root, "poster", lock={"foundations": "2.0.0"}, state="retired")
        named = (
            "  visual/pieces/poster/piece.yaml, whose lock cannot be read: its state `retired` is "
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
    assert lines[4:-1] == (
        [next(line for line in lines if "no before-and-after: " in line), *way] if way else []
    )
    assert lines[-1].startswith("listed foundations@1.1.0 in ")


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


# --- a lock that moves only on purpose, named in the command (DEC-013 point 5) ------------------

#: The foundations' caption, as they ship, and as the capability the tests read changes it.
CAPTION = "text: {content: caption, style: type.body, fill: text-secondary}"
CHANGED_CAPTION = "text: {content: caption, style: type.heading, fill: text-secondary}"

#: The second spacing a test library's gap reads, and the third it reads once changed.
GAP = "{space.2}"
CHANGED_GAP = "{space.3}"

#: Where a piece's before-and-after lies, for the draft of `lay_out_drawing`.
FLOW = f"{before_after.FOLDER}/flow"
#: The font the draft's brand measures with, in the project's copy of that brand.
FLOW_FONT = "visual/libraries/test-brand/1.0.0/fonts/SourceSansPro-Regular.otf"
FLOW_LOCK = {"foundations": "1.0.0", "test-brand": "1.0.0", "tests": "1.0.0"}
PIECE_FILE = "visual/pieces/flow/piece.yaml"


def changed(path: Path, old: str, new: str) -> None:
    """The file at `path` with the text `old` changed to `new`."""
    text = path.read_text(encoding="utf-8")
    assert old in text
    path.write_text(text.replace(old, new), encoding="utf-8")


@pytest.fixture
def pinned(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """The pinned draft `flow`, which locks a copy of the foundations not yet released, in a
    project of its own; and a capability whose foundations being built, of that number, draw
    its caption in another style. Returns the project."""
    folder = capability(tmp_path, monkeypatch)
    changed(folder / "libraries/foundations/components/figure.yaml", CAPTION, CHANGED_CAPTION)
    importable(monkeypatch, svg)
    return lay_out_drawing(project(tmp_path), picture=False, pinned=True)


@pytest.fixture
def published(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """The published piece `flow`, which locks a copy of the foundations not yet released, as
    the draft of `pinned` does, under the same capability. Returns the project."""
    folder = capability(tmp_path, monkeypatch)
    changed(folder / "libraries/foundations/components/figure.yaml", CAPTION, CHANGED_CAPTION)
    importable(monkeypatch, svg)
    return lay_out_drawing(project(tmp_path), picture=False, state="published", released=False)


@pytest.fixture
def written(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """The declaration `brand-css`, which locks a copy of `test-parts` not yet released, in a
    project of its own; and a capability that ships that number, its gap on another spacing.
    Returns the project."""
    folder = capability(tmp_path, monkeypatch)
    shutil.copytree(TEST_PARTS, folder / "libraries" / "test-parts")
    changed(folder / "libraries/test-parts/roles.yaml", GAP, CHANGED_GAP)
    importable(monkeypatch, css)
    root = project(tmp_path)
    copy_library(root, RELEASED_FOUNDATIONS, "foundations", "1.0.0")
    copy_library(root, TEST_BRAND, "test-brand", "1.0.0")
    copy_library(root, TEST_PARTS, "test-parts", "1.0.0")
    versions = {"1.0.0": {"released": False}}
    write_list(
        root,
        {
            "foundations": {"source": {"kind": "shipped"}, "versions": versions},
            "test-brand": {"source": {"kind": "project"}, "versions": versions},
            "test-parts": {"source": {"kind": "shipped"}, "versions": versions},
        },
    )
    lock = {"foundations": "1.0.0", "test-brand": "1.0.0", "test-parts": "1.0.0"}
    declaration(root, "brand-css", lock)
    return root


@pytest.mark.parametrize("named", [True, False], ids=["named", "not named"])
def test_a_pinned_draft_named_beside_an_unpinned_one_lets_the_copy_be_replaced(
    tmp_path: Path, released: tuple[Path, dict[str, Any]], named: bool
) -> None:
    folder, entry = released
    root = project(tmp_path)
    copy = unreleased_copy(root)
    flow = write_piece(root, "flow", lock={"foundations": "1.0.0"})
    poster = write_piece(root, "poster", lock={"foundations": "1.0.0"}, pinned=True)
    pieces = (flow.read_bytes(), poster.read_bytes())
    before = tree(copy)
    added = run(root, "foundations", *(("--piece", "poster") if named else ()))
    assert added.returncode == 0, added.stderr
    assert (flow.read_bytes(), poster.read_bytes()) == pieces
    lines = added.stdout.splitlines()[1:]
    if named:
        assert tree(copy) == tree(place(folder))
        assert listed(root) == {"1.0.0": entry}
        assert lines == [
            f"replaced foundations@1.0.0, {len(tree(copy))} files, in {COPY}/, with the released "
            f"version",
            "  locked by the draft `flow`",
            "  locked by the pinned draft `poster`",
            f"listed foundations@1.0.0 in {LIST} as released, with the hash the capability records",
        ]
    else:
        assert tree(copy) == before
        assert listed(root) == {"1.0.0": {"released": False}}
        assert lines[:2] == [
            "left foundations@1.0.0 as it is: a lock that moves only on purpose names it",
            "  the pinned draft `poster`",
        ]
        assert lines[-1] == "  to replace it, run `pkit visual add foundations --piece poster`"


def test_a_copy_locked_by_written_code_is_replaced_once_its_declaration_is_named(
    written: Path,
) -> None:
    file = written / "visual/code/brand-css.yaml"
    declared = file.read_bytes()
    added = run(written, "test-parts", "--declaration", "brand-css")
    assert added.returncode == 0, added.stderr
    assert file.read_bytes() == declared
    copy = written / "visual/libraries/test-parts/1.0.0"
    assert CHANGED_GAP in (copy / "roles.yaml").read_text(encoding="utf-8")
    assert added.stdout.splitlines()[-1:] == [
        "  locked by the declaration `brand-css` of written code"
    ]


def test_a_copy_stays_until_each_lock_that_holds_it_is_named_and_the_run_names_those_left(
    tmp_path: Path, released: tuple[Path, dict[str, Any]]
) -> None:
    folder, _ = released
    root = project(tmp_path)
    copy = unreleased_copy(root)
    write_piece(root, "poster", lock={"foundations": "1.0.0"}, pinned=True)
    declaration(root, "css", {"foundations": "1.0.0"})
    before = tree(copy)
    added = run(root, "foundations", "--being-built", "--piece", "poster")
    assert added.returncode == 0, added.stderr
    assert tree(copy) == before
    assert tree(root / NEXT) == tree(folder / "libraries" / "foundations")
    lines = added.stdout.splitlines()
    assert "  the pinned draft `poster`" not in lines
    assert "  the declaration `css` of written code" in lines
    assert (
        "  to replace it, run `pkit visual add foundations --piece poster --declaration css`"
    ) in lines
    both = run(root, "foundations", "--piece", "poster", "--declaration", "css")
    assert both.returncode == 0, both.stderr
    assert tree(copy) == tree(place(folder))


def test_a_lock_that_cannot_be_read_holds_the_copy_and_offers_no_command_to_name_it(
    tmp_path: Path, released: tuple[Path, dict[str, Any]]
) -> None:
    root = project(tmp_path)
    unreleased_copy(root)
    write(root / "visual" / "pieces" / "poster" / "piece.yaml", "lock: [\n")
    added = run(root, "foundations")
    assert added.returncode == 0, added.stderr
    assert not [line for line in added.stdout.splitlines() if "to replace it" in line]


@pytest.mark.parametrize(
    ("args", "refused"),
    [
        pytest.param(
            ("--piece", "other"),
            "the pinned draft `other` locks no copy of `foundations` this run would replace: it "
            "locks starter@1.0.0, test-brand@1.0.0",
            id="another library",
        ),
        pytest.param(
            ("--piece", "older"),
            "the pinned draft `older` locks no copy of `foundations` this run would replace: it "
            "locks foundations@2.0.0",
            id="another number",
        ),
        pytest.param(
            ("--piece", "empty"),
            "the pinned draft `empty` locks no copy of `foundations` this run would replace: it "
            "locks nothing",
            id="no lock",
        ),
        pytest.param(
            ("--declaration", "other"),
            "the declaration `other` of written code locks no copy of `foundations` this run "
            "would replace: it locks test-brand@1.0.0",
            id="a declaration",
        ),
        pytest.param(
            ("--piece", "unknown"), "the location holds no piece `unknown`", id="no such piece"
        ),
        pytest.param(
            ("--declaration", "poster"),
            "the location holds no declaration `poster`",
            id="no such declaration",
        ),
        pytest.param(
            ("--piece", "broken"),
            "visual/pieces/broken/piece.yaml, whose lock cannot be read: does not parse as YAML",
            id="an unreadable lock",
        ),
    ],
)
def test_a_lock_named_that_locks_no_copy_the_run_would_replace_is_refused_with_nothing_written(
    tmp_path: Path,
    released: tuple[Path, dict[str, Any]],
    args: tuple[str, ...],
    refused: str,
) -> None:
    root = project(tmp_path)
    unreleased_copy(root)
    write_piece(root, "poster", lock={"foundations": "1.0.0"}, pinned=True)
    write_piece(root, "other", lock={"starter": "1.0.0", "test-brand": "1.0.0"}, pinned=True)
    write_piece(root, "older", lock={"foundations": "2.0.0"}, pinned=True)
    write_piece(root, "empty", pinned=True)
    write(root / "visual" / "pieces" / "broken" / "piece.yaml", "lock: [\n")
    declaration(root, "other", {"test-brand": "1.0.0"})
    before = tree(root)
    added = run(root, "foundations", "--piece", "poster", *args)
    assert added.returncode == 1
    assert added.stdout == ""
    assert added.stderr.startswith(f"error: {refused}")
    assert tree(root) == before


def test_a_piece_that_locks_a_released_copy_is_refused_since_restoring_it_names_no_piece(
    tmp_path: Path, released: tuple[Path, dict[str, Any]]
) -> None:
    folder, entry = released
    root = project(tmp_path)
    copy = released_copy(root, folder, entry)
    write_piece(root, "poster", lock={"foundations": "1.0.0"}, pinned=True)
    set_fields(copy / "components" / "figure.yaml", about="Changed by the project.")
    added = run(root, "foundations", "--piece", "poster")
    assert added.returncode == 1
    assert added.stderr == (
        "error: the pinned draft `poster` locks no copy of `foundations` this run would replace: "
        "it locks foundations@1.0.0\n"
    )


def test_an_unpinned_draft_named_stands_beside_the_one_the_copy_needs(
    tmp_path: Path, released: tuple[Path, dict[str, Any]]
) -> None:
    folder, _ = released
    root = project(tmp_path)
    copy = unreleased_copy(root)
    write_piece(root, "flow", lock={"foundations": "1.0.0"})
    added = run(root, "foundations", "--piece", "flow")
    assert added.returncode == 0, added.stderr
    assert tree(copy) == tree(place(folder))


def test_a_pinned_drafts_before_and_after_is_drawn_both_ways_and_writes_nothing_of_the_project(
    pinned: Path,
) -> None:
    before = tree(pinned / "visual")
    added = run(pinned, "foundations")
    assert added.returncode == 0, added.stderr
    assert tree(pinned / "visual") == before
    assert added.stdout.splitlines()[1:] == [
        "left foundations@1.0.0 as it is: a lock that moves only on purpose names it",
        "  the pinned draft `flow`",
        f"    drawn both ways in {FLOW}/: 2 of 2 files differ",
        "  to replace it, run `pkit visual add foundations --piece flow`",
    ]
    files = ["flow.en.colour-scheme.dark.svg", "flow.en.default.svg"]
    kept = tree(pinned / FLOW)
    assert sorted(kept) == [
        *(f"after/{file}" for file in files),
        *(f"before/{file}" for file in files),
    ]
    assert sorted(path.name for path in (pinned / before_after.FOLDER).iterdir()) == ["flow"]
    for file in files:
        assert kept[f"before/{file}"] != kept[f"after/{file}"]
        assert b"The flow." in kept[f"before/{file}"]
        assert b"The flow." in kept[f"after/{file}"]


def test_a_published_pieces_copy_stays_with_its_before_and_after_until_it_is_named(
    published: Path,
) -> None:
    piece = (published / PIECE_FILE).read_bytes()
    copy = tree(published / COPY)
    left = run(published, "foundations")
    assert left.returncode == 0, left.stderr
    assert tree(published / COPY) == copy
    assert left.stdout.splitlines()[1:] == [
        "left foundations@1.0.0 as it is: a lock that moves only on purpose names it",
        "  the published piece `flow`",
        f"    drawn both ways in {FLOW}/: 2 of 2 files differ",
        "  to replace it, run `pkit visual add foundations --piece flow`",
    ]
    named = run(published, "foundations", "--piece", "flow")
    assert named.returncode == 0, named.stderr
    assert "  locked by the published piece `flow`" in named.stdout.splitlines()
    assert CHANGED_CAPTION in (published / COPY / "components/figure.yaml").read_text(
        encoding="utf-8"
    )
    assert (published / PIECE_FILE).read_bytes() == piece


def preview_facts(root: Path) -> Any:
    """What a preview of `flow` fills its facts with, as the run's before-and-after does."""
    return exports.preview_filling(pl.read_piece_file(root, "visual", "flow")).facts


def test_the_after_side_is_what_the_piece_draws_once_it_is_named(pinned: Path) -> None:
    drawn_before = before_after.drawing(
        pinned, "visual", "flow", FLOW_LOCK, facts=preview_facts(pinned)
    )
    assert run(pinned, "foundations").returncode == 0
    kept = tree(pinned / FLOW)
    piece = (pinned / PIECE_FILE).read_bytes()
    named = run(pinned, "foundations", "--piece", "flow")
    assert named.returncode == 0, named.stderr
    assert (pinned / PIECE_FILE).read_bytes() == piece
    assert CHANGED_CAPTION in (pinned / COPY / "components/figure.yaml").read_text(encoding="utf-8")
    drawn_after = before_after.drawing(
        pinned, "visual", "flow", FLOW_LOCK, facts=preview_facts(pinned)
    )
    assert drawn_before.why == drawn_after.why == ""
    for file, text in drawn_before.files.items():
        assert kept[f"before/{file}"] == text.encode("utf-8")
    for file, text in drawn_after.files.items():
        assert kept[f"after/{file}"] == text.encode("utf-8")


def test_a_later_run_draws_again_and_leaves_no_file_from_before(pinned: Path) -> None:
    write(pinned / FLOW / "before" / "flow.fr.default.svg", "<svg/>")
    assert run(pinned, "foundations").returncode == 0
    assert "before/flow.fr.default.svg" not in tree(pinned / FLOW)


def test_a_side_that_cannot_be_drawn_is_said_and_the_run_goes_on(
    pinned: Path, tmp_path: Path
) -> None:
    roles = tmp_path / "capability/libraries/foundations/roles.yaml"
    write(roles, yaml_text(bound("roles", roles="none")))
    added = run(pinned, "foundations")
    assert added.returncode == 0, added.stderr
    said = next(line for line in added.stdout.splitlines() if "no before-and-after" in line)
    assert said.startswith("    no before-and-after: with what the capability ships, ")
    assert ".location." not in said
    assert not (pinned / FLOW).exists()
    assert added.stdout.splitlines()[-1] == (
        "  to replace it, run `pkit visual add foundations --piece flow`"
    )


def test_a_top_the_shipped_copy_no_longer_holds_is_said_and_the_run_goes_on(
    pinned: Path, tmp_path: Path
) -> None:
    (tmp_path / "capability/libraries/foundations/components/figure.yaml").unlink()
    added = run(pinned, "foundations")
    assert added.returncode == 0, added.stderr
    assert added.stdout.splitlines()[1:] == [
        "left foundations@1.0.0 as it is: a lock that moves only on purpose names it",
        "  the pinned draft `flow`",
        "    no before-and-after: with what the capability ships, the piece draws no page in "
        "`en`: the piece's top names no component `foundations/figure`",
        "  to replace it, run `pkit visual add foundations --piece flow`",
    ]
    assert not (pinned / FLOW).exists()


def test_a_top_that_names_no_component_on_either_side_is_said_once(pinned: Path) -> None:
    changed(pinned / PIECE_FILE, "top: foundations/figure", "top: foundations/nothing")
    added = run(pinned, "foundations")
    assert added.returncode == 0, added.stderr
    assert (
        "    no before-and-after: the piece draws no page in `en`: the piece's top names no "
        "component `foundations/nothing`"
    ) in added.stdout.splitlines()
    assert "files differ" not in added.stdout
    assert not (pinned / FLOW).exists()


def test_a_fault_in_the_piece_is_said_once_and_stops_nothing(pinned: Path) -> None:
    write(pinned / "visual/pieces/flow/content.en.yaml", "not: [content\n")
    added = run(pinned, "foundations")
    assert added.returncode == 0, added.stderr
    assert added.stdout.count("no before-and-after") == 1
    assert "with the copy as it is" not in added.stdout


@pytest.mark.parametrize(
    "broken",
    [
        lambda _font: b"not a font",
        lambda _font: b"version https://git-lfs.github.com/spec/v1\noid sha256:0\nsize 1\n",
        lambda font: font[:2000],
        lambda font: font[: len(font) * 3 // 4],
    ],
    ids=["no font", "a git-lfs pointer", "cut before what is measured", "cut after it"],
)
def test_a_font_that_cannot_be_read_is_said_once_and_stops_nothing(
    pinned: Path, broken: Callable[[bytes], bytes]
) -> None:
    font = pinned / FLOW_FONT
    font.write_bytes(broken(font.read_bytes()))
    added = run(pinned, "foundations")
    assert added.returncode == 0, added.stderr
    [said] = [line for line in added.stdout.splitlines() if "no before-and-after" in line]
    assert said.startswith(f"    no before-and-after: the font file {FLOW_FONT} cannot be read: ")
    assert added.stdout.splitlines()[-1] == (
        "  to replace it, run `pkit visual add foundations --piece flow`"
    )
    assert not (pinned / FLOW).exists()


def test_a_before_and_after_that_cannot_be_written_stops_the_run_as_any_write_does(
    pinned: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    before = tree(pinned)
    with monkeypatch.context() as patch:
        failing(patch, write={"flow.en.colour-scheme.dark.svg"})
        added = run(pinned, "foundations")
    assert added.returncode == 1
    assert added.stdout == ""
    assert added.stderr == (
        f"error: {FLOW}/before/flow.en.colour-scheme.dark.svg could not be written: {FULL}\n"
    )
    assert tree(pinned) == before


def test_a_before_and_after_reached_through_a_link_is_refused_and_the_run_goes_on(
    pinned: Path, tmp_path: Path
) -> None:
    local = pinned / before_after.FOLDER
    local.parent.mkdir(parents=True)
    (tmp_path / "elsewhere").mkdir()
    local.symlink_to(tmp_path / "elsewhere", target_is_directory=True)
    added = run(pinned, "foundations")
    assert added.returncode == 0, added.stderr
    assert "no before-and-after: " in added.stdout
    assert "is reached through the link" in added.stdout
    assert list((tmp_path / "elsewhere").iterdir()) == []


def test_written_codes_before_and_after_shows_the_difference_in_the_code(written: Path) -> None:
    before = tree(written / "visual")
    added = run(written, "test-parts")
    assert added.returncode == 0, added.stderr
    assert tree(written / "visual") == before
    assert not (written / "styles").exists()
    lines = added.stdout.splitlines()[1:]
    assert lines[:5] == [
        "left test-parts@1.0.0 as it is: a lock that moves only on purpose names it",
        "  the declaration `brand-css` of written code",
        "    its writer writes other code with what the capability ships:",
        "    --- styles/brand-css.css, with the copy as it is",
        "    +++ styles/brand-css.css, with what the capability ships",
    ]
    assert "    -  --test-parts--gap: 8px;" in lines
    assert "    +  --test-parts--gap: 16px;" in lines
    assert lines[-1] == (
        "  to replace it, run `pkit visual add test-parts --declaration brand-css`"
    )


def test_written_code_that_would_not_change_says_so(written: Path, tmp_path: Path) -> None:
    roles = tmp_path / "capability/libraries/test-parts/roles.yaml"
    changed(roles, CHANGED_GAP, GAP)
    changed(roles, "its gap the second spacing", "its gap, the second spacing")
    added = run(written, "test-parts")
    assert added.returncode == 0, added.stderr
    assert "    its writer writes the same code with what the capability ships" in (
        added.stdout.splitlines()
    )


def test_each_before_and_after_reads_a_location_git_ignores(
    pinned: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    importable(monkeypatch, css)
    declaration(pinned, "brand-css", {"foundations": "1.0.0", "test-brand": "1.0.0"})
    write(pinned / ".gitignore", ".pkit/capabilities/visual-communication/project/local/\n")
    subprocess.run(["git", "init", "-q"], cwd=pinned, check=True, capture_output=True)
    added = run(pinned, "foundations")
    assert added.returncode == 0, added.stderr
    assert f"    drawn both ways in {FLOW}/: 2 of 2 files differ" in added.stdout.splitlines()
    assert "    its writer writes the same code with what the capability ships" in (
        added.stdout.splitlines()
    )


@pytest.mark.process(
    "the command's end-to-end test: the script as a process of its own, importing its renderer "
    "and its writer when it runs, over the capability's own files"
)
def test_the_command_shows_a_before_and_after_as_a_process_of_its_own(tmp_path: Path) -> None:
    root = lay_out_drawing(project(tmp_path), picture=False, pinned=True)
    changed(root / COPY / "components/figure.yaml", CAPTION, CHANGED_CAPTION)
    declaration(root, "brand-css", {"foundations": "1.0.0", "test-brand": "1.0.0"})
    done = subprocess.run(
        [sys.executable, str(CAPABILITY / "scripts" / "add.py"), "foundations"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.returncode == 0, done.stderr
    assert f"    drawn both ways in {FLOW}/: 2 of 2 files differ" in done.stdout.splitlines()
    assert "    its writer writes the same code with what the capability ships" in (
        done.stdout.splitlines()
    )
    assert (
        "  to replace it, run `pkit visual add foundations --piece flow --declaration brand-css`"
    ) in done.stdout.splitlines()
