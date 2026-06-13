"""Tests for project-management's bootstrap script's pure logic.

Covers plan computation — what would be created vs already exists,
with a focus on the state-label additions in label-fallback mode.
The gh subprocess layer is not tested here; those wrappers are thin
pass-throughs covered by integration-level validation.
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
    / "bootstrap.py"
)


@pytest.fixture(scope="module")
def bs():
    module_name = "pm_bootstrap_under_test"
    spec = importlib.util.spec_from_file_location(module_name, SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def classification() -> dict:
    """Minimal classification.yaml-shaped dict."""
    return {
        "axes": {
            "type": {
                "values": ["feature", "bug", "docs"],
            },
            "priority": {
                "values": ["High", "Medium", "Low"],
            },
        },
    }


@pytest.fixture
def workflow_data() -> dict:
    """Minimal workflow.yaml-shaped dict with five states."""
    return {
        "states": [
            {"id": "todo"},
            {"id": "backlog"},
            {"id": "in-progress"},
            {"id": "review"},
            {"id": "done"},
        ],
    }


# --- _resolve_state_ids -----------------------------------------------


def test_resolve_state_ids_reads_from_workflow(bs, tmp_path) -> None:
    """_resolve_state_ids returns state IDs from workflow.yaml in order."""
    schemas_dir = tmp_path / "schemas"
    schemas_dir.mkdir()
    workflow_path = schemas_dir / "workflow.yaml"
    workflow_path.write_text(
        "states:\n  - id: todo\n  - id: backlog\n  - id: in-progress\n  - id: review\n  - id: done\n",
        encoding="utf-8",
    )
    cap_root = tmp_path
    ids = bs._resolve_state_ids(cap_root)
    assert ids == ["todo", "backlog", "in-progress", "review", "done"]


def test_resolve_state_ids_returns_empty_when_missing(bs, tmp_path) -> None:
    """Missing workflow.yaml returns empty list — no crash."""
    ids = bs._resolve_state_ids(tmp_path)
    assert ids == []


def test_resolve_state_ids_skips_non_string_ids(bs, tmp_path) -> None:
    schemas_dir = tmp_path / "schemas"
    schemas_dir.mkdir()
    workflow_path = schemas_dir / "workflow.yaml"
    workflow_path.write_text(
        "states:\n  - id: todo\n  - id: 42\n  - id: done\n",
        encoding="utf-8",
    )
    ids = bs._resolve_state_ids(tmp_path)
    # 42 is an integer in YAML, not a string — should be filtered out
    assert "todo" in ids
    assert "done" in ids


# --- _compute_plan state-label behaviour ------------------------------


def test_compute_plan_includes_state_labels_in_label_fallback(
    bs, tmp_path, classification, workflow_data
) -> None:
    """In label-fallback mode, plan includes state:* label creates."""
    schemas_dir = tmp_path / "schemas"
    schemas_dir.mkdir()
    (schemas_dir / "workflow.yaml").write_text(
        "states:\n  - id: todo\n  - id: backlog\n  - id: in-progress\n  - id: review\n  - id: done\n",
        encoding="utf-8",
    )
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    # Patch _fetch_existing_labels to return an empty set (fresh repo).
    original = bs._fetch_existing_labels
    bs._fetch_existing_labels = lambda: set()
    try:
        plan = bs._compute_plan(
            config={},
            classification=classification,
            has_board=False,
            with_starter_epic=False,
            capability_root=tmp_path,
        )
    finally:
        bs._fetch_existing_labels = original

    label_names = [name for _, name in plan.label_creates]
    state_label_names = [n for n in label_names if n.startswith("state:")]
    assert "state:todo" in state_label_names
    assert "state:backlog" in state_label_names
    assert "state:in-progress" in state_label_names
    assert "state:review" in state_label_names
    assert "state:done" in state_label_names


def test_compute_plan_skips_existing_state_labels(
    bs, tmp_path, classification, workflow_data
) -> None:
    """State labels already in the repo are recorded as 'exists', not 'creates'."""
    schemas_dir = tmp_path / "schemas"
    schemas_dir.mkdir()
    (schemas_dir / "workflow.yaml").write_text(
        "states:\n  - id: todo\n  - id: backlog\n  - id: in-progress\n  - id: review\n  - id: done\n",
        encoding="utf-8",
    )

    existing = {"state:todo", "state:backlog", "state:in-progress", "state:review", "state:done"}
    original = bs._fetch_existing_labels
    bs._fetch_existing_labels = lambda: existing
    try:
        plan = bs._compute_plan(
            config={},
            classification=classification,
            has_board=False,
            with_starter_epic=False,
            capability_root=tmp_path,
        )
    finally:
        bs._fetch_existing_labels = original

    state_creates = [n for _, n in plan.label_creates if n.startswith("state:")]
    assert state_creates == [], "All state labels exist; none should be in creates"
    state_exists = [n for n in plan.label_exists if n.startswith("state:")]
    assert len(state_exists) == 5


def test_compute_plan_omits_state_labels_in_board_mode(
    bs, tmp_path, classification, workflow_data
) -> None:
    """In board mode, state:* labels are NOT created (skip message instead)."""
    schemas_dir = tmp_path / "schemas"
    schemas_dir.mkdir()
    (schemas_dir / "workflow.yaml").write_text(
        "states:\n  - id: todo\n  - id: backlog\n  - id: in-progress\n  - id: review\n  - id: done\n",
        encoding="utf-8",
    )

    original = bs._fetch_existing_labels
    bs._fetch_existing_labels = lambda: set()
    try:
        plan = bs._compute_plan(
            config={},
            classification=classification,
            has_board=True,
            with_starter_epic=False,
            capability_root=tmp_path,
        )
    finally:
        bs._fetch_existing_labels = original

    state_creates = [n for _, n in plan.label_creates if n.startswith("state:")]
    assert state_creates == [], "Board mode: state labels should not be in creates"
    state_skipped = any("state:*" in msg for msg in plan.skipped_messages)
    assert state_skipped, "Board mode: should have a skip message for state:* labels"
