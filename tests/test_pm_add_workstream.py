"""Tests for the add-workstream script's pure logic.

Covers slug validation and the file-write helper (which exercises
both bootstrap of a fresh file and append to an existing one).
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

from tests.pm_workstream_fakes import FakeBoard, FakeRepo, stage_project

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = (
    REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts" / "add-workstream.py"
)


@pytest.fixture(scope="module")
def aw():
    module_name = "pm_add_workstream_under_test"
    spec = importlib.util.spec_from_file_location(module_name, SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


# --- slug validation ------------------------------------------------


def test_validate_slug_accepts_kebab(aw) -> None:
    assert aw.validate_slug("cli") is None
    assert aw.validate_slug("agent-platform") is None
    assert aw.validate_slug("ab") is None


def test_validate_slug_rejects_uppercase(aw) -> None:
    err = aw.validate_slug("CLI")
    assert err is not None
    assert "does not match" in err


def test_validate_slug_rejects_underscores(aw) -> None:
    err = aw.validate_slug("agent_platform")
    assert err is not None


def test_validate_slug_rejects_trailing_hyphen(aw) -> None:
    err = aw.validate_slug("cli-")
    assert err is not None


def test_validate_slug_rejects_consecutive_hyphens(aw) -> None:
    err = aw.validate_slug("agent--platform")
    assert err is not None
    assert "consecutive hyphens" in err


def test_validate_slug_rejects_too_short(aw) -> None:
    err = aw.validate_slug("a")
    assert err is not None


def test_validate_slug_rejects_too_long(aw) -> None:
    err = aw.validate_slug("a" * 41)
    assert err is not None


def test_validate_slug_rejects_empty(aw) -> None:
    err = aw.validate_slug("")
    assert err is not None


def test_validate_slug_rejects_non_string(aw) -> None:
    err = aw.validate_slug(None)
    assert err is not None


# --- file write -----------------------------------------------------


def test_add_to_file_bootstraps_fresh_file(aw, tmp_path) -> None:
    cap_root = tmp_path / "cap"
    (cap_root / "project").mkdir(parents=True)
    ok = aw._add_to_file(cap_root, "cli", {"name": "cli", "status": "active"})
    assert ok is True
    target = cap_root / "project" / "workstreams.yaml"
    assert target.is_file()
    content = target.read_text(encoding="utf-8")
    assert "schema_version" in content
    assert "cli" in content


def test_add_to_file_appends_to_existing_mapping(aw, tmp_path) -> None:
    cap_root = tmp_path / "cap"
    (cap_root / "project").mkdir(parents=True)
    target = cap_root / "project" / "workstreams.yaml"
    target.write_text(
        "schema_version: 1\nworkstreams:\n  cli:\n    name: cli\n    status: active\n",
        encoding="utf-8",
    )
    ok = aw._add_to_file(cap_root, "schemas", {"name": "schemas", "status": "active"})
    assert ok is True
    content = target.read_text(encoding="utf-8")
    assert "cli" in content
    assert "schemas" in content


def test_add_to_file_upgrades_list_to_mapping(aw, tmp_path) -> None:
    """If the existing file is in list-shorthand form, an attributed
    entry forces an upgrade to mapping form."""
    cap_root = tmp_path / "cap"
    (cap_root / "project").mkdir(parents=True)
    target = cap_root / "project" / "workstreams.yaml"
    target.write_text(
        "schema_version: 1\nworkstreams:\n  - cli\n  - schemas\n",
        encoding="utf-8",
    )
    ok = aw._add_to_file(cap_root, "agent-platform", {"name": "Agent Platform", "status": "active"})
    assert ok is True
    content = target.read_text(encoding="utf-8")
    # cli/schemas should be retained.
    assert "cli" in content
    assert "schemas" in content
    assert "agent-platform" in content
    # Mapping form has nested attributes.
    assert "name:" in content


# --- main(): every attribute checked, and the board kept in step (#1940) -----

WORKSTREAMS = "schema_version: 1\nworkstreams:\n  cli:\n    name: cli\n    status: active\n"


def _run(aw, monkeypatch, cap_root: Path, *argv: str) -> int:
    # The invoker's login, without asking GitHub for it.
    monkeypatch.setenv("PM_INVOKER_LOGIN", "me")
    monkeypatch.setattr(
        sys,
        "argv",
        ["add-workstream.py", *argv, "--capability-root", str(cap_root), "--yes"],
    )
    return aw.main()


def _lib():
    if str(SCRIPT_PATH.parent) not in sys.path:
        sys.path.insert(0, str(SCRIPT_PATH.parent))
    from _lib import board_fields, substrate_writes

    return board_fields, substrate_writes


def test_main_refuses_a_description_over_200_chars_and_writes_nothing(
    aw, tmp_path, monkeypatch
) -> None:
    """The reported gap: a 250-char description was written, and the file's
    reader then dropped the whole entry."""
    stage_project(tmp_path, WORKSTREAMS)
    repo = FakeRepo()
    monkeypatch.setattr(aw, "gh_run", repo)
    rc = _run(aw, monkeypatch, tmp_path, "docs", "--description", "d" * 250)
    assert rc == 1
    assert "docs" not in (tmp_path / "project" / "workstreams.yaml").read_text(encoding="utf-8")
    assert repo.mutations() == []


@pytest.mark.parametrize(
    "extra",
    [
        ["--name", "n" * 65],
        ["--name", "two\nlines"],
        ["--status", "deprecated", "--deprecated-reason", "r" * 201],
    ],
)
def test_main_refuses_each_attribute_outside_the_rules(aw, tmp_path, monkeypatch, extra) -> None:
    stage_project(tmp_path, WORKSTREAMS)
    monkeypatch.setattr(aw, "gh_run", FakeRepo())
    assert _run(aw, monkeypatch, tmp_path, "docs", *extra) == 1


def test_main_adds_the_option_to_the_boards_field(aw, tmp_path, monkeypatch) -> None:
    stage_project(tmp_path, WORKSTREAMS, board=True)
    board = FakeBoard(["cli"])
    board.install(monkeypatch, *_lib())
    monkeypatch.setattr(aw, "gh_run", FakeRepo())
    assert _run(aw, monkeypatch, tmp_path, "docs", "--description", "The docs.") == 0
    assert board.option_names() == ["cli", "docs"]
    assert board.options[-1]["description"] == "The docs."
    # The existing option keeps its id, so its cards keep their value.
    assert board.options[0]["id"] == "opt_cli"
    assert "docs" in (tmp_path / "project" / "workstreams.yaml").read_text(encoding="utf-8")


def test_main_writes_no_option_the_board_already_offers(aw, tmp_path, monkeypatch) -> None:
    stage_project(tmp_path, WORKSTREAMS, board=True)
    board = FakeBoard(["cli", "docs"])
    board.install(monkeypatch, *_lib())
    monkeypatch.setattr(aw, "gh_run", FakeRepo())
    assert _run(aw, monkeypatch, tmp_path, "docs") == 0
    assert board.writes == []


def test_main_refuses_a_board_with_no_workstream_field(aw, tmp_path, monkeypatch) -> None:
    stage_project(tmp_path, WORKSTREAMS, board=True)
    FakeBoard(has_field=False).install(monkeypatch, *_lib())
    monkeypatch.setattr(aw, "gh_run", FakeRepo())
    assert _run(aw, monkeypatch, tmp_path, "docs") == 1
    assert "docs" not in (tmp_path / "project" / "workstreams.yaml").read_text(encoding="utf-8")


def test_main_writes_no_file_when_the_board_write_fails(aw, tmp_path, monkeypatch) -> None:
    stage_project(tmp_path, WORKSTREAMS, board=True)
    board = FakeBoard(["cli"])
    board_fields, substrate_writes = _lib()
    board.install(monkeypatch, board_fields, substrate_writes)

    def refuse(cmd, config):
        return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="no project scope")

    monkeypatch.setattr(substrate_writes, "_gh_call", refuse)
    monkeypatch.setattr(aw, "gh_run", FakeRepo())
    assert _run(aw, monkeypatch, tmp_path, "docs") == 3
    assert "docs" not in (tmp_path / "project" / "workstreams.yaml").read_text(encoding="utf-8")
