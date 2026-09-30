"""project-management 0.55.0: its `default_branch` retires into the backbone's key (COR-054).

The default branch is declared once, in the backbone configuration
(`repository.default-branch`, `main` when absent). The upgrade migration is the
writer COR-054 point 1 names: it carries a value other than `main` over while
the backbone declares none, and removes project-management's key in each of
those cases. Where carrying over would need a guess — the backbone's file
cannot take an appended block, or the value is no branch name — it writes
nothing and keeps the key, which project-management still reads. Pinned here,
with idempotence: a second run finds nothing to do.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from ruamel.yaml import YAML

REPO_ROOT = Path(__file__).resolve().parents[1]
MIGRATION = (
    REPO_ROOT
    / ".pkit"
    / "capabilities"
    / "project-management"
    / "migrations"
    / "0.55.0"
    / "004-default-branch-to-backbone.sh"
)
SCHEMA = REPO_ROOT / ".pkit" / "schemas" / "backbone" / "config.schema.json"
PM_CONFIG = Path(".pkit/capabilities/project-management/project/config.yaml")
CONFIG = Path(".pkit/project/config.yaml")

PM_WITH = """\
schema_version: 1
# the repo's default branch
default_branch: {value}                  # a trailing comment
has_projects_v2_board: false
workstreams: []
"""

PM_WITHOUT = """\
schema_version: 1
# the repo's default branch
has_projects_v2_board: false
workstreams: []
"""


def _run(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(MIGRATION)],
        env={"ROOT": str(root), "PATH": "/usr/bin:/bin"},
        capture_output=True,
        text=True,
        check=False,
    )


def _project(tmp_path: Path, value: str | None, backbone: str | None = None) -> Path:
    if value is not None:
        (tmp_path / PM_CONFIG).parent.mkdir(parents=True)
        (tmp_path / PM_CONFIG).write_text(PM_WITH.format(value=value), encoding="utf-8")
    if backbone is not None:
        (tmp_path / CONFIG).parent.mkdir(parents=True)
        (tmp_path / CONFIG).write_text(backbone, encoding="utf-8")
    return tmp_path


_YAML: Any = YAML(typ="safe")


def _load(path: Path) -> Any:
    return _YAML.load(path.read_text(encoding="utf-8"))


def _twice(root: Path) -> str:
    """Run the migration, then again: the second run finds nothing to do."""
    first = _run(root)
    assert first.returncode == 0, first.stderr
    again = _run(root)
    assert again.returncode == 0, again.stderr
    return first.stdout


@pytest.mark.parametrize("value", ["develop", "'release/2'", '"trunk"'])
def test_a_value_other_than_main_is_carried_over_and_the_key_removed(
    tmp_path: Path, value: str
) -> None:
    root = _project(tmp_path, value, backbone="name: example\n")
    said = _twice(root)
    name = value.strip("'\"")
    assert f"recorded repository.default-branch: {name}" in said
    config = _load(root / CONFIG)
    assert config == {"name": "example", "repository": {"default-branch": name}}
    validator: Any = Draft202012Validator(_load_schema())
    assert list(validator.iter_errors(config)) == []
    assert (root / PM_CONFIG).read_text(encoding="utf-8") == PM_WITHOUT


def test_a_missing_backbone_file_is_created_with_the_editor_directive(tmp_path: Path) -> None:
    root = _project(tmp_path, "trunk")
    _twice(root)
    text = (root / CONFIG).read_text(encoding="utf-8")
    assert text.startswith(
        "# yaml-language-server: $schema=../schemas/backbone/config.schema.json\n"
    )
    assert _load(root / CONFIG) == {"repository": {"default-branch": "trunk"}}


def test_main_is_the_default_so_only_the_key_goes(tmp_path: Path) -> None:
    root = _project(tmp_path, "main", backbone="name: example\n")
    said = _twice(root)
    assert "removed project-management's default_branch (main)" in said
    assert (root / CONFIG).read_text(encoding="utf-8") == "name: example\n"
    assert (root / PM_CONFIG).read_text(encoding="utf-8") == PM_WITHOUT


def test_a_declared_default_branch_wins(tmp_path: Path) -> None:
    backbone = "repository:\n  default-branch: trunk\n"
    root = _project(tmp_path, "develop", backbone=backbone)
    said = _twice(root)
    assert "declares repository.default-branch" in said
    assert (root / CONFIG).read_text(encoding="utf-8") == backbone
    assert (root / PM_CONFIG).read_text(encoding="utf-8") == PM_WITHOUT


@pytest.mark.parametrize(
    ("backbone", "value", "why"),
    [
        ("{name: example}\n", "develop", "one flow-style mapping"),
        ("repository: {}\n", "develop", "declares repository without default-branch"),
        ("name: example\n", "origin/develop", "not a branch name the backbone takes"),
    ],
    ids=["flow-root", "repository-without-key", "not-a-branch-name"],
)
def test_where_carrying_over_would_guess_nothing_is_written_and_the_key_kept(
    tmp_path: Path, backbone: str, value: str, why: str
) -> None:
    root = _project(tmp_path, value, backbone=backbone)
    said = _twice(root)
    assert why in said
    assert f"pkit config set repository.default-branch {value} --yes" in said
    assert (root / CONFIG).read_text(encoding="utf-8") == backbone
    assert (root / PM_CONFIG).read_text(encoding="utf-8") == PM_WITH.format(value=value)


def test_nothing_to_retire(tmp_path: Path) -> None:
    assert "no project-management project config" in _run(tmp_path).stdout
    (tmp_path / PM_CONFIG).parent.mkdir(parents=True)
    (tmp_path / PM_CONFIG).write_text(PM_WITHOUT, encoding="utf-8")
    assert "retired already" in _run(tmp_path).stdout
    assert (tmp_path / PM_CONFIG).read_text(encoding="utf-8") == PM_WITHOUT


def _load_schema() -> Any:
    return json.loads(SCHEMA.read_text(encoding="utf-8"))
