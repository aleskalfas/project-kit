"""project-management 0.55.0: the board flag carries no axis, and the config moves to 2.

[project-management:DEC-062-axes-chosen-in-the-map] point 6: the migration acts
only where `project/config.yaml` is at version 1, and writes version 2 there.
Where the flag is set, priority and workstream stay on the board through the map
— `board: true` for each the map omits or marks `unsupported`, its `default:`
kept — and state gets no binding, in a present map or in one the migration
writes. A present map keeps its comments and every other key. The report names
each binding written, and each comment that speaks of the board. Pinned here,
with idempotence: a second run changes nothing.
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
CAPABILITY = REPO_ROOT / ".pkit" / "capabilities" / "project-management"
MIGRATION = CAPABILITY / "migrations" / "0.55.0" / "005-board-flag-carries-no-axis.sh"
PROJECT = Path(".pkit/capabilities/project-management/project")

BOARD_CONFIG = """\
schema_version: 1   # the configuration's version
# the board: priority, workstream and state on its fields
has_projects_v2_board: true
projects_v2_board_id: 7
workstreams: []
"""

NO_BOARD_CONFIG = """\
schema_version: 1
has_projects_v2_board: false
workstreams: []
"""

PARTIAL_MAP = """\
schema_version: 1
hierarchy: advisory
axes:
  # Priority: the board carries it — the map cannot say so (the old workaround).
  priority:
    unsupported: true
    default: Medium
  type:
    title-prefix:
      remap:
        task: "[Task]"
  # State: left out, so the board carries it.
"""

_YAML: Any = YAML(typ="safe")


def _run(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(MIGRATION)],
        env={"ROOT": str(root), "PATH": "/usr/bin:/bin:/usr/local/bin"},
        capture_output=True,
        text=True,
        check=False,
    )


def _project(tmp_path: Path, config: str | None, substrate_map: str | None = None) -> Path:
    (tmp_path / PROJECT).mkdir(parents=True)
    if config is not None:
        (tmp_path / PROJECT / "config.yaml").write_text(config, encoding="utf-8")
    if substrate_map is not None:
        (tmp_path / PROJECT / "substrate-map.yaml").write_text(substrate_map, encoding="utf-8")
    return tmp_path


def _config(root: Path) -> str:
    return (root / PROJECT / "config.yaml").read_text(encoding="utf-8")


def _map(root: Path) -> str:
    return (root / PROJECT / "substrate-map.yaml").read_text(encoding="utf-8")


def _validates(text: str, schema: str) -> None:
    validator = Draft202012Validator(
        json.loads((CAPABILITY / "schemas" / schema).read_text(encoding="utf-8"))
    )
    assert [e.message for e in validator.iter_errors(_YAML.load(text))] == []


# --- with no map, it writes one ---------------------------------------------


def test_with_no_map_it_writes_one_keeping_the_board_axes(tmp_path: Path) -> None:
    root = _project(tmp_path, BOARD_CONFIG)

    result = _run(root)

    assert result.returncode == 0, result.stderr
    axes = _YAML.load(_map(root))["axes"]
    assert axes == {
        "type": {"kit-label": True},
        "priority": {"board": True},
        "workstream": {"board": True},
    }
    _validates(_map(root), "substrate-map.schema.json")
    assert "state left out" in result.stdout
    assert "schema_version 1 → 2" in result.stdout


def test_the_configuration_moves_to_version_2_and_keeps_the_rest(tmp_path: Path) -> None:
    root = _project(tmp_path, BOARD_CONFIG)

    _run(root)

    assert _config(root) == BOARD_CONFIG.replace("schema_version: 1", "schema_version: 2")


# --- in a present map, it changes priority and workstream only ----------------


def test_in_a_present_map_it_binds_priority_and_workstream_and_keeps_the_rest(
    tmp_path: Path,
) -> None:
    root = _project(tmp_path, BOARD_CONFIG, PARTIAL_MAP)

    result = _run(root)

    assert result.returncode == 0, result.stderr
    text = _map(root)
    data = _YAML.load(text)
    assert data["axes"]["priority"] == {"board": True, "default": "Medium"}
    assert data["axes"]["workstream"] == {"board": True}
    assert data["axes"]["type"] == {"title-prefix": {"remap": {"task": "[Task]"}}}
    assert "state" not in data["axes"]
    assert data["hierarchy"] == "advisory"
    # Every comment kept, and only the changed lines differ.
    assert text == PARTIAL_MAP.replace("    unsupported: true", "    board: true").replace(
        "  # State:", "  workstream:\n    board: true\n  # State:"
    )
    _validates(text, "substrate-map.schema.json")


def test_the_report_names_each_binding_and_each_comment_on_the_board(tmp_path: Path) -> None:
    root = _project(tmp_path, BOARD_CONFIG, PARTIAL_MAP)

    out = _run(root).stdout

    assert "wrote `board: true` for `priority`" in out
    assert "its `default:` is kept" in out
    assert "wrote `workstream: {board: true}`" in out
    assert "line 4: # Priority: the board carries it" in out
    assert "line 13: # State: left out, so the board carries it." in out


def test_an_axis_bound_another_way_is_left_as_it_is(tmp_path: Path) -> None:
    substrate_map = (
        "schema_version: 1\n"
        "axes:\n"
        "  priority:\n"
        "    label:\n"
        "      remap: {High: P0}\n"
        "  workstream:\n"
        "    kit-label: true\n"
        "  state:\n"
        "    derive:\n"
        "      states: {done: closed}\n"
    )
    root = _project(tmp_path, BOARD_CONFIG, substrate_map)

    result = _run(root)

    assert result.returncode == 0, result.stderr
    assert _map(root) == substrate_map
    assert "no binding written" in result.stdout


def test_state_is_never_bound_even_when_marked_unsupported(tmp_path: Path) -> None:
    substrate_map = "schema_version: 1\naxes:\n  state:\n    unsupported: true\n"
    root = _project(tmp_path, BOARD_CONFIG, substrate_map)

    _run(root)

    axes = _YAML.load(_map(root))["axes"]
    assert axes["state"] == {"unsupported": True}
    assert axes["priority"] == axes["workstream"] == {"board": True}


def test_a_flow_style_axis_to_change_stops_the_upgrade_and_writes_nothing(
    tmp_path: Path,
) -> None:
    substrate_map = "schema_version: 1\naxes:\n  priority: {unsupported: true}\n"
    root = _project(tmp_path, BOARD_CONFIG, substrate_map)

    result = _run(root)

    assert result.returncode == 1
    assert _map(root) == substrate_map and _config(root) == BOARD_CONFIG
    assert "one-line flow mapping" in result.stderr


# --- where the flag is not set, only the version moves -------------------------


@pytest.mark.parametrize("substrate_map", [None, PARTIAL_MAP])
def test_with_no_board_flag_only_the_version_moves(
    tmp_path: Path, substrate_map: str | None
) -> None:
    root = _project(tmp_path, NO_BOARD_CONFIG, substrate_map)

    result = _run(root)

    assert result.returncode == 0, result.stderr
    assert _config(root) == NO_BOARD_CONFIG.replace("schema_version: 1", "schema_version: 2")
    if substrate_map is None:
        assert not (root / PROJECT / "substrate-map.yaml").exists()
    else:
        assert _map(root) == substrate_map
    assert "no axis moved" in result.stdout
    _validates(_config(root), "config.schema.json")


# --- it acts only at version 1, and runs once ---------------------------------


def test_a_second_run_changes_nothing(tmp_path: Path) -> None:
    root = _project(tmp_path, BOARD_CONFIG, PARTIAL_MAP)
    _run(root)
    config, substrate_map = _config(root), _map(root)

    result = _run(root)

    assert result.returncode == 0
    assert (_config(root), _map(root)) == (config, substrate_map)
    assert "is at version 2" in result.stdout


def test_a_map_left_unsupported_after_the_upgrade_is_never_overwritten(tmp_path: Path) -> None:
    """The project's choice after the migration stands (DEC-062 point 6)."""
    root = _project(tmp_path, BOARD_CONFIG.replace("schema_version: 1", "schema_version: 2"))
    substrate_map = "schema_version: 1\naxes:\n  priority:\n    unsupported: true\n"
    (root / PROJECT / "substrate-map.yaml").write_text(substrate_map, encoding="utf-8")

    _run(root)

    assert _map(root) == substrate_map


def test_a_run_stopped_after_the_map_finishes_with_the_version(tmp_path: Path) -> None:
    """The map holds its bindings, the version is still 1: a run writes none again."""
    root = _project(tmp_path, BOARD_CONFIG)
    _run(root)
    written = _map(root)
    (root / PROJECT / "config.yaml").write_text(BOARD_CONFIG, encoding="utf-8")

    result = _run(root)

    assert result.returncode == 0, result.stderr
    assert _map(root) == written
    assert "schema_version: 2" in _config(root)


@pytest.mark.parametrize(
    ("config", "says"),
    [
        ("has_projects_v2_board: true\nworkstreams: []\n", "declares no schema_version"),
        ("schema_version: 3\nworkstreams: []\n", "is at version 3, not 1"),
    ],
)
def test_a_configuration_not_at_version_1_is_left_as_it_is(
    tmp_path: Path, config: str, says: str
) -> None:
    root = _project(tmp_path, config)

    result = _run(root)

    assert result.returncode == 0
    assert _config(root) == config
    assert says in result.stdout
    assert not (root / PROJECT / "substrate-map.yaml").exists()


def test_no_capability_or_no_configuration_skips(tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    assert "[skip]" in _run(empty).stdout
    assert "[skip]" in _run(_project(tmp_path / "bare", None)).stdout


def test_script_is_executable_and_sets_strict_mode() -> None:
    assert MIGRATION.stat().st_mode & 0o111, "migration must be executable"
    assert "set -euo pipefail" in MIGRATION.read_text(encoding="utf-8")
