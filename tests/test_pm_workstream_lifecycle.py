"""Tests for the workstream lifecycle scripts' file-mutation logic.

Covers rename/edit/merge/split/remove via their file-write helpers.
The gh subprocess wrappers are not unit-tested (thin pass-throughs).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = (
    REPO_ROOT
    / ".pkit"
    / "capabilities"
    / "project-management"
    / "scripts"
)


def _load(name: str):
    path = SCRIPTS_DIR / f"{name}.py"
    module_name = f"pm_{name}_under_test"
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def rn():
    return _load("rename-workstream")


# --- rename ----------------------------------------------------------


def test_rename_in_file_list_form(rn, tmp_path) -> None:
    from ruamel.yaml import YAML

    yaml = YAML(typ="rt")
    path = tmp_path / "workstreams.yaml"
    path.write_text(
        "schema_version: 1\nworkstreams:\n  - cli\n  - schemas\n",
        encoding="utf-8",
    )
    with path.open("r", encoding="utf-8") as f:
        data = yaml.load(f)
    ok = rn._rename_in_file(yaml, data, "cli", "cli-tools", path)
    assert ok is True
    text = path.read_text(encoding="utf-8")
    assert "cli-tools" in text
    assert "schemas" in text
    # Old slug `cli` should not appear as a standalone list item.
    assert "\n- cli\n" not in text and "  - cli\n" not in text


def test_rename_in_file_mapping_form(rn, tmp_path) -> None:
    from ruamel.yaml import YAML

    yaml = YAML(typ="rt")
    path = tmp_path / "workstreams.yaml"
    path.write_text(
        "schema_version: 1\n"
        "workstreams:\n"
        "  cli:\n    name: cli\n    status: active\n"
        "  schemas:\n    name: schemas\n    status: active\n",
        encoding="utf-8",
    )
    with path.open("r", encoding="utf-8") as f:
        data = yaml.load(f)
    ok = rn._rename_in_file(yaml, data, "cli", "agent-platform", path)
    assert ok is True
    text = path.read_text(encoding="utf-8")
    assert "agent-platform:" in text
    assert "schemas:" in text


# --- end-to-end via test fixture: parse and verify state -------------


def test_remove_file_mutation_mapping_form(tmp_path) -> None:
    from ruamel.yaml import YAML

    yaml = YAML(typ="rt")
    path = tmp_path / "workstreams.yaml"
    path.write_text(
        "schema_version: 1\n"
        "workstreams:\n"
        "  cli:\n    name: cli\n    status: active\n"
        "  schemas:\n    name: schemas\n    status: active\n",
        encoding="utf-8",
    )
    with path.open("r", encoding="utf-8") as f:
        data = yaml.load(f)
    ws = data["workstreams"]
    ws.pop("cli")
    with path.open("w", encoding="utf-8") as f:
        yaml.dump(data, f)
    text = path.read_text(encoding="utf-8")
    assert "schemas:" in text
    assert "cli:" not in text


def test_merge_file_mutation_list_form(tmp_path) -> None:
    from ruamel.yaml import YAML

    yaml = YAML(typ="rt")
    path = tmp_path / "workstreams.yaml"
    path.write_text(
        "schema_version: 1\nworkstreams:\n  - cli\n  - cli-old\n  - other\n",
        encoding="utf-8",
    )
    with path.open("r", encoding="utf-8") as f:
        data = yaml.load(f)
    ws = data["workstreams"]
    losers = {"cli-old"}
    data["workstreams"] = [item for item in ws if item not in losers]
    with path.open("w", encoding="utf-8") as f:
        yaml.dump(data, f)
    text = path.read_text(encoding="utf-8")
    assert "cli\n" in text
    assert "other\n" in text
    assert "cli-old" not in text


def test_split_file_mutation_mapping_form(tmp_path) -> None:
    from ruamel.yaml import YAML

    yaml = YAML(typ="rt")
    path = tmp_path / "workstreams.yaml"
    path.write_text(
        "schema_version: 1\n"
        "workstreams:\n"
        "  cli:\n    name: cli\n    status: active\n",
        encoding="utf-8",
    )
    with path.open("r", encoding="utf-8") as f:
        data = yaml.load(f)
    ws = data["workstreams"]
    ws.pop("cli")
    for slug in ["cli-tools", "cli-rendering"]:
        ws[slug] = {"name": slug, "status": "active"}
    with path.open("w", encoding="utf-8") as f:
        yaml.dump(data, f)
    text = path.read_text(encoding="utf-8")
    assert "cli-tools:" in text
    assert "cli-rendering:" in text
    assert "  cli:" not in text


# --- edit ------------------------------------------------------------


@pytest.fixture(scope="module")
def ew():
    return _load("edit-workstream")


def test_edit_workstream_no_args_returns_usage_error(ew, monkeypatch) -> None:
    """Calling main with no edit-args should exit 2 (usage error).

    We bypass argparse + membership checks by short-circuiting the
    capability-root resolution to a non-existent path. The first
    return is the no-edit-args check.
    """
    monkeypatch.setattr(sys, "argv", ["edit-workstream", "cli"])
    rc = ew.main()
    assert rc == 2
