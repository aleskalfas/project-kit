"""Tests for set-field's pure planning logic (no network).

Covers label resolution + idempotent diff for priority/workstream, the
parent-ref body rewrite (replace / prepend / no-op), value-vocabulary reads,
and the board-degrade posture.
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
    / "set-field.py"
)
SCRIPTS = SCRIPT_PATH.parent


@pytest.fixture(scope="module")
def sf():
    sys.path.insert(0, str(SCRIPTS))
    module_name = "pm_set_field_under_test"
    spec = importlib.util.spec_from_file_location(module_name, SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def issue_types() -> dict:
    return {
        "types": {
            "epic": {"title_prefix": "EPIC", "title_case": "upper"},
            "feature": {
                "title_prefix": "Feature",
                "title_case": "title",
                "parent_ref_form": "EPIC: #<N>",
            },
            "task": {
                "title_prefix": "Task",
                "title_case": "title",
                "parent_ref_form": "Feature: #<N>",
            },
        },
    }


@pytest.fixture
def classification() -> dict:
    return {
        "axes": {
            "priority": {"values": ["High", "Medium", "Low"]},
            "type": {"title_prefix_by_value": {"bug": "Bug"}},
        },
    }


# --- value vocabulary reads -------------------------------------------------


def test_axis_values_reads_priority_list(sf, classification) -> None:
    assert sf._axis_values(classification, "priority") == {"High", "Medium", "Low"}


def test_axis_values_empty_for_unknown_axis(sf, classification) -> None:
    assert sf._axis_values(classification, "nope") == set()


def test_adopter_workstreams_list_form(sf) -> None:
    assert sf._adopter_workstreams({"workstreams": ["cli", "docs"]}) == {"cli", "docs"}


def test_adopter_workstreams_mapping_form(sf) -> None:
    assert sf._adopter_workstreams(
        {"workstreams": {"cli": {}, "docs": {}}}
    ) == {"cli", "docs"}


# --- label planning (greenfield: substrate_map None) -----------------------


def test_plan_labels_sets_new_priority(sf) -> None:
    results, add, remove = sf._plan_labels(
        priority="High",
        workstream=None,
        current_labels=["type:feature"],
        substrate_map=None,
        has_board=False,
    )
    assert add == ["priority:High"]
    assert remove == []
    assert any(r.changed for r in results)


def test_plan_labels_replaces_stale_priority(sf) -> None:
    results, add, remove = sf._plan_labels(
        priority="High",
        workstream=None,
        current_labels=["priority:Low", "type:feature"],
        substrate_map=None,
        has_board=False,
    )
    assert add == ["priority:High"]
    assert remove == ["priority:Low"]


def test_plan_labels_idempotent_noop(sf) -> None:
    results, add, remove = sf._plan_labels(
        priority="High",
        workstream=None,
        current_labels=["priority:High"],
        substrate_map=None,
        has_board=False,
    )
    assert add == [] and remove == []
    assert any("no-op" in r.message for r in results)


def test_plan_labels_batch_priority_and_workstream(sf) -> None:
    results, add, remove = sf._plan_labels(
        priority="Medium",
        workstream="cli",
        current_labels=[],
        substrate_map=None,
        has_board=False,
    )
    assert set(add) == {"priority:Medium", "workstream:cli"}


def test_plan_labels_board_degrades(sf) -> None:
    results, add, remove = sf._plan_labels(
        priority="High",
        workstream=None,
        current_labels=[],
        substrate_map=None,
        has_board=True,
    )
    assert add == [] and remove == []
    assert any("board substrate" in r.message for r in results)


# --- parent-ref planning ----------------------------------------------------


def test_plan_parent_replaces_existing_ref(sf) -> None:
    body = "Feature: #1\n\n## What\nx\n"
    new_body, result = sf._plan_parent(body, "Feature: #9")
    assert new_body.startswith("Feature: #9\n")
    assert result.changed is True


def test_plan_parent_idempotent_noop(sf) -> None:
    body = "Feature: #9\n\n## What\nx\n"
    new_body, result = sf._plan_parent(body, "Feature: #9")
    assert new_body == body
    assert result.changed is False
    assert "no-op" in result.message


def test_plan_parent_prepends_when_absent(sf) -> None:
    body = "## What\nx\n"
    new_body, result = sf._plan_parent(body, "Feature: #9")
    assert new_body.startswith("Feature: #9\n\n## What")
    assert result.changed is True


def test_plan_parent_preserves_milestone_link_form_recognised(sf) -> None:
    body = "Milestone: [#6](../milestone/6)\n\n## What\nx\n"
    new_body, result = sf._plan_parent(body, "EPIC: #3")
    # The existing first line is a recognised parent-ref, so it is REPLACED
    # (not prepended-before).
    assert new_body.startswith("EPIC: #3\n")
    assert "Milestone:" not in new_body.splitlines()[0]


# --- structural type + parent-ref form -------------------------------------


def test_infer_structural_type_task(sf, issue_types) -> None:
    assert sf._infer_structural_type("[Task] x", issue_types) == "task"


def test_infer_structural_type_bug_via_classification(sf, issue_types, classification) -> None:
    assert sf._infer_structural_type("[Bug] x", issue_types, classification) == "task"


def test_parent_ref_line_uses_type_form(sf, issue_types) -> None:
    task = issue_types["types"]["task"]
    assert sf._parent_ref_line(task, 42) == "Feature: #42"


def test_parent_ref_line_empty_without_form(sf) -> None:
    assert sf._parent_ref_line({}, 42) == ""


def test_is_parent_ref_recognises_forms(sf) -> None:
    assert sf._is_parent_ref("Feature: #1")
    assert sf._is_parent_ref("Milestone: [#6](../milestone/6)")
    assert sf._is_parent_ref("Milestone: #6")
    assert not sf._is_parent_ref("## What")
    assert not sf._is_parent_ref("just prose")
