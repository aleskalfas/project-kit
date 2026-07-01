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


@pytest.fixture(scope="module")
def cr():
    # The shared kind ↔ structural predicate now lives in _lib (extracted from
    # set-field per COR-007 / issue #410); the pure permit/refuse + kind-drives
    # tests assert it directly at its new home.
    sys.path.insert(0, str(SCRIPTS))
    from _lib import classification_rules

    return classification_rules


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
            "type": {
                "values": [
                    "feature",
                    "bug",
                    "docs",
                    "test",
                    "refactor",
                    "maintenance",
                ],
                "title_prefix_by_value": {
                    "feature": "Task",
                    "bug": "Bug",
                    "docs": "Docs",
                    "test": "Test",
                    "refactor": "Refactor",
                    "maintenance": "Chore",
                },
                "structural_restriction": {
                    "allowed_structural_types_per_kind": {
                        "feature": ["task", "feature", "umbrella", "epic"],
                        "bug": ["task"],
                        "docs": ["task"],
                        "test": ["task"],
                        "refactor": ["task"],
                        "maintenance": ["task"],
                    },
                },
            },
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


# --- kind planning (label swap + title-prefix realignment) ------------------


def test_axis_values_reads_type_list(sf, classification) -> None:
    assert sf._axis_values(classification, "type") == {
        "feature",
        "bug",
        "docs",
        "test",
        "refactor",
        "maintenance",
    }


def test_plan_kind_swaps_label_and_realigns_prefix(
    sf, issue_types, classification
) -> None:
    results, add, remove, new_title = sf._plan_kind(
        kind="bug",
        title="[Chore] fix the broken verb",
        current_labels=["type:maintenance", "priority:Medium"],
        issue_types=issue_types,
        classification=classification,
        substrate_map=None,
    )
    assert add == ["type:bug"]
    assert remove == ["type:maintenance"]
    assert new_title == "[Bug] fix the broken verb"
    assert any(r.field == "kind" and r.changed for r in results)
    assert any(r.field == "title" and r.changed for r in results)


def test_plan_kind_prefix_already_correct_is_noop(
    sf, issue_types, classification
) -> None:
    # Label changes but the title prefix already matches the target kind.
    results, add, remove, new_title = sf._plan_kind(
        kind="bug",
        title="[Bug] already titled right",
        current_labels=["type:maintenance"],
        issue_types=issue_types,
        classification=classification,
        substrate_map=None,
    )
    assert add == ["type:bug"]
    assert remove == ["type:maintenance"]
    assert new_title is None
    assert not any(r.field == "title" for r in results)


def test_plan_kind_idempotent_when_label_and_prefix_match(
    sf, issue_types, classification
) -> None:
    results, add, remove, new_title = sf._plan_kind(
        kind="bug",
        title="[Bug] nothing to do",
        current_labels=["type:bug"],
        issue_types=issue_types,
        classification=classification,
        substrate_map=None,
    )
    assert add == [] and remove == []
    assert new_title is None
    assert any("no-op" in r.message for r in results)


def test_kind_mismatch_on_epic_feature_umbrella_is_refused(cr, classification) -> None:
    # The up-front gate (DEC-011 / structural_restriction) refuses a non-feature
    # kind on epic/feature/umbrella — it would manufacture the kind/structural
    # mismatch that breaks PR-conv-type derivation. The gate is the SAME table
    # `kind_drives_title` reads; assert the shared predicate that drives it.
    assert cr.kind_allowed_for_structural_type("bug", "epic", classification) is False
    assert cr.kind_allowed_for_structural_type("bug", "feature", classification) is False
    assert cr.kind_allowed_for_structural_type("docs", "umbrella", classification) is False


def test_kind_feature_on_epic_feature_umbrella_is_permitted(cr, classification) -> None:
    # `feature` IS the kind epic/feature/umbrella carry by definition, so the gate
    # permits it (it lands downstream as a no-op: label already type:feature, no
    # prefix change). Permitted-not-refused is the consistent choice with the
    # up-front check keyed on `allowed_structural_types_per_kind`.
    assert cr.kind_allowed_for_structural_type("feature", "epic", classification) is True
    assert cr.kind_allowed_for_structural_type("feature", "feature", classification) is True
    assert cr.kind_allowed_for_structural_type("feature", "umbrella", classification) is True
    # And on a task, every kind is permitted.
    assert cr.kind_allowed_for_structural_type("bug", "task", classification) is True


def test_kind_allowed_permissive_on_empty_classification(cr) -> None:
    # No restriction table to ground a refusal ⇒ permit (the up-front gate refuses
    # nothing it can't ground in the schema).
    assert cr.kind_allowed_for_structural_type("bug", "epic", {}) is True


def test_plan_kind_feature_on_feature_issue_is_full_noop(
    sf, issue_types, classification
) -> None:
    # The one --kind path that reaches _plan_kind for a feature-structural issue:
    # kind `feature` on an already-`type:feature` [Feature] issue. Label already
    # correct, structural prefix already correct — nothing mutates.
    results, add, remove, new_title = sf._plan_kind(
        kind="feature",
        title="[Feature] a feature surface",
        current_labels=["type:feature"],
        issue_types=issue_types,
        classification=classification,
        substrate_map=None,
    )
    assert add == [] and remove == []
    assert new_title is None
    assert any("no-op" in r.message for r in results)


def test_retitle_prefix_swaps_leading_bracket(sf) -> None:
    assert sf._retitle_prefix("[Chore] do a thing", "Bug") == "[Bug] do a thing"


def test_retitle_prefix_none_without_prefix(sf) -> None:
    assert sf._retitle_prefix("no prefix here", "Bug") is None


def test_kind_drives_title_true_for_task(cr, classification) -> None:
    assert cr.kind_drives_title("task", classification) is True


def test_kind_drives_title_false_for_feature(cr, classification) -> None:
    assert cr.kind_drives_title("feature", classification) is False


def test_kind_drives_title_false_on_empty_classification(cr) -> None:
    assert cr.kind_drives_title("task", {}) is False


def test_unknown_kind_not_in_declared_values(sf, classification) -> None:
    # The up-front validation gate reads the declared type vocabulary; an unknown
    # kind is absent from it, so the gate (in main) refuses before any mutation.
    valid = sf._axis_values(classification, "type")
    assert "nonsense" not in valid
    assert "bug" in valid


def test_kind_composes_with_priority_workstream_batch(
    sf, issue_types, classification
) -> None:
    # The aggregate add/remove main builds: kind swap + priority + workstream in
    # one batch, all label writes against a single edit call.
    current = ["type:maintenance", "priority:Low"]
    k_results, k_add, k_remove, new_title = sf._plan_kind(
        kind="bug",
        title="[Chore] mislabelled defect",
        current_labels=current,
        issue_types=issue_types,
        classification=classification,
        substrate_map=None,
    )
    a_results, a_add, a_remove = sf._plan_labels(
        priority="High",
        workstream="cli",
        current_labels=current,
        substrate_map=None,
        has_board=False,
    )
    add = k_add + a_add
    remove = k_remove + a_remove
    assert set(add) == {"type:bug", "priority:High", "workstream:cli"}
    assert set(remove) == {"type:maintenance", "priority:Low"}
    assert new_title == "[Bug] mislabelled defect"


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
