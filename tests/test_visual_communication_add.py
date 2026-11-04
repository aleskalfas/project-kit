"""`pkit visual add <library>` (visual-communication DEC-002 point 3, DEC-003 points 4 and
5): the version the capability ships copied whole into the location's library folder and
listed, every other byte of the list kept; never over a version the folder holds; refused
where its files lack their binding, or the capability does not ship the library. Run in
this process (`tests/in_process.py`); it starts no `pkit`.

The last tests install the capability in an adopter's repository and show that `pkit
sync` and an upgrade write nothing into the location: only the command copies a library
there."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

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
)
from tests.visual_communication_writes import FULL, failing

script, libraries, reading = load("visual-communication", "add.py", "libraries", "reading")

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


def shipped(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A folder of shipped libraries the test controls, holding a copy of the foundations,
    in place of the capability's own for the length of the test."""
    folder = tmp_path / "shipped"
    shutil.copytree(FOUNDATIONS, folder / "foundations")
    monkeypatch.setattr(libraries, "SHIPPED_LIBRARIES", folder)
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
def test_a_version_the_folder_holds_is_never_overwritten(tmp_path: Path, held: str) -> None:
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
        f"error: the library folder holds {COPY} already, and a version it holds is never "
        f"overwritten\n"
    )
    assert tree(root) == before


def test_a_version_the_list_names_without_its_folder_is_refused(tmp_path: Path) -> None:
    root = project(tmp_path)
    write_list(root, {"foundations": LISTED})
    before = tree(root)
    added = run(root, "foundations")
    assert added.returncode == 1
    assert added.stderr == (
        f"error: {LIST} names foundations@1.0.0 already, though the library folder does not "
        f"hold it: restore its folder, or take it off the list\n"
    )
    assert tree(root) == before


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
    folder = shipped(tmp_path, monkeypatch) / "foundations"
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
        "error: the capability ships no library `charts`; it ships `foundations`, `starter`\n"
    )
    folder = shipped(tmp_path, monkeypatch)
    shutil.copytree(FOUNDATIONS, folder / "neutral")
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
