"""Tests for the add-workstream script's pure logic.

Covers slug validation and the file-write helper (which exercises
both bootstrap of a fresh file and append to an existing one).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = (
    REPO_ROOT
    / ".pkit"
    / "capabilities"
    / "project-management"
    / "scripts"
    / "add-workstream.py"
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
    err = aw.validate_slug(None)  # type: ignore[arg-type]
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
    ok = aw._add_to_file(
        cap_root, "agent-platform", {"name": "Agent Platform", "status": "active"}
    )
    assert ok is True
    content = target.read_text(encoding="utf-8")
    # cli/schemas should be retained.
    assert "cli" in content
    assert "schemas" in content
    assert "agent-platform" in content
    # Mapping form has nested attributes.
    assert "name:" in content
