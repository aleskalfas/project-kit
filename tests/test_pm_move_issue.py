"""Tests for project-management's move-issue script's pure logic.

Covers transition lookup, state inference, plan computation, severity
parsing, forward-direction detection, parent-chain walking. The
subprocess (gh) layer is not tested — those wrappers are thin
pass-throughs.
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
    / "move-issue.py"
)


@pytest.fixture(scope="module")
def mi():
    module_name = "pm_move_issue_under_test"
    spec = importlib.util.spec_from_file_location(module_name, SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def workflow() -> dict:
    """Compact fixture mirroring workflow.yaml's transitions block."""
    return {
        "states": [
            {"id": "todo"},
            {"id": "backlog"},
            {"id": "in-progress"},
            {"id": "review"},
            {"id": "done"},
        ],
        "transitions": [
            {
                "from": "todo",
                "to": "backlog",
                "authorisation": "user",
                "severity": "[validation-severity:bypassable-with-audit]",
                "applies_to": [
                    "[issue-types:epic]",
                    "[issue-types:feature]",
                    "[issue-types:umbrella]",
                    "[issue-types:task]",
                ],
            },
            {
                "from": "backlog",
                "to": "in-progress",
                "authorisation": "agent-autonomous",
                "severity": "[validation-severity:warning]",
                "applies_to": [
                    "[issue-types:epic]",
                    "[issue-types:feature]",
                    "[issue-types:umbrella]",
                    "[issue-types:task]",
                ],
            },
            {
                "from": "in-progress",
                "to": "review",
                "authorisation": "agent-autonomous",
                "severity": "[validation-severity:warning]",
                "applies_to": ["[issue-types:task]"],
            },
            {
                "from": "review",
                "to": "done",
                "authorisation": "user",
                "severity": "[validation-severity:hard-reject]",
                "applies_to": ["[issue-types:task]"],
            },
            # Parent-typed review→done — added per #208 so the forward
            # cascade has a closure path when parents have been walked
            # into Review by children.
            {
                "from": "review",
                "to": "done",
                "authorisation": "user",
                "severity": "[validation-severity:hard-reject]",
                "applies_to": [
                    "[issue-types:epic]",
                    "[issue-types:feature]",
                    "[issue-types:umbrella]",
                ],
            },
        ],
    }


@pytest.fixture
def issue_types() -> dict:
    return {
        "types": {
            "epic": {"title_prefix": "EPIC", "title_case": "upper"},
            "feature": {"title_prefix": "Feature", "title_case": "title"},
            "umbrella": {"title_prefix": "Umbrella", "title_case": "title"},
            "task": {"title_prefix": "Task", "title_case": "title"},
        },
    }


# --- known states ---------------------------------------------------


def test_known_states_lists_all_five(mi, workflow) -> None:
    assert mi._known_states(workflow) == {
        "todo",
        "backlog",
        "in-progress",
        "review",
        "done",
    }


def test_known_states_returns_empty_on_garbage(mi) -> None:
    assert mi._known_states({}) == set()


# --- transition lookup ----------------------------------------------


def test_find_transition_returns_entry_for_known_pair(mi, workflow) -> None:
    t = mi._find_transition(workflow, "backlog", "in-progress", "task")
    assert t is not None
    assert t.from_state == "backlog"
    assert t.to_state == "in-progress"
    assert t.authorisation == "agent-autonomous"
    assert t.severity == "warning"


def test_find_transition_returns_none_for_unknown(mi, workflow) -> None:
    assert mi._find_transition(workflow, "todo", "in-progress", "task") is None
    assert mi._find_transition(workflow, "review", "todo", "task") is None


def test_find_transition_respects_applies_to(mi, workflow) -> None:
    # in-progress → review is task-only.
    assert mi._find_transition(workflow, "in-progress", "review", "feature") is None
    assert mi._find_transition(workflow, "in-progress", "review", "task") is not None


def test_find_transition_user_authorised_severity_parsed(mi, workflow) -> None:
    t = mi._find_transition(workflow, "review", "done", "task")
    assert t is not None
    assert t.authorisation == "user"
    assert t.severity == "hard-reject"


def test_find_transition_review_to_done_for_parent_types(mi, workflow) -> None:
    """review → done is also available to epic/feature/umbrella via close-issue (#208).

    The forward cascade walks parents into Review when children advance;
    without a parent-typed review→done transition, parents dead-end in
    Review (worked-around manually before this fix).
    """
    for parent_type in ("epic", "feature", "umbrella"):
        t = mi._find_transition(workflow, "review", "done", parent_type)
        assert t is not None, f"no review→done transition for {parent_type!r}"
        assert t.from_state == "review"
        assert t.to_state == "done"
        assert t.authorisation == "user"
        assert t.severity == "hard-reject"


# --- legal targets --------------------------------------------------


def test_legal_targets_lists_outgoing_for_state(mi, workflow) -> None:
    targets = mi._legal_targets(workflow, "backlog", "task")
    assert "in-progress" in targets
    assert "todo" not in targets


def test_legal_targets_filters_by_type(mi, workflow) -> None:
    # in-progress can go to review for task only.
    assert "review" in mi._legal_targets(workflow, "in-progress", "task")
    assert "review" not in mi._legal_targets(workflow, "in-progress", "feature")


def test_legal_targets_review_to_done_for_parent_types(mi, workflow) -> None:
    """Parents can transition review → done via close-issue (#208 fix)."""
    for parent_type in ("epic", "feature", "umbrella"):
        assert "done" in mi._legal_targets(workflow, "review", parent_type), (
            f"parent type {parent_type!r} should have 'done' reachable from 'review'"
        )


# --- forward direction ----------------------------------------------


def test_is_forward_true_for_increasing_states(mi, workflow) -> None:
    assert mi._is_forward(workflow, "todo", "backlog") is True
    assert mi._is_forward(workflow, "backlog", "in-progress") is True
    assert mi._is_forward(workflow, "in-progress", "review") is True
    assert mi._is_forward(workflow, "review", "done") is True


def test_is_forward_false_for_backward(mi, workflow) -> None:
    assert mi._is_forward(workflow, "in-progress", "backlog") is False
    assert mi._is_forward(workflow, "done", "todo") is False


def test_is_forward_false_for_unknown_states(mi, workflow) -> None:
    assert mi._is_forward(workflow, "bogus", "backlog") is False


# --- severity parsing -----------------------------------------------


def test_severity_from_token_parses_hard_reject(mi) -> None:
    assert mi._severity_from_token("[validation-severity:hard-reject]") == "hard-reject"


def test_severity_from_token_falls_back_to_warning(mi) -> None:
    assert mi._severity_from_token("garbage") == "warning"
    assert mi._severity_from_token("") == "warning"


# --- state inference ------------------------------------------------


def test_infer_state_closed_issue_is_done(mi) -> None:
    assert mi._infer_current_state(state="closed", milestone={}, labels=[]) == "done"


def test_infer_state_state_label_wins(mi) -> None:
    assert (
        mi._infer_current_state(
            state="open", milestone={"title": "M1"}, labels=["state:in-progress"]
        )
        == "in-progress"
    )


def test_infer_state_milestone_alone_means_backlog(mi) -> None:
    assert (
        mi._infer_current_state(
            state="open", milestone={"title": "M1"}, labels=["type:feature"]
        )
        == "backlog"
    )


def test_infer_state_no_milestone_no_label_means_todo(mi) -> None:
    assert (
        mi._infer_current_state(state="open", milestone={}, labels=[]) == "todo"
    )


# --- plan computation -----------------------------------------------


def test_plan_label_substrate_adds_new_and_removes_old(mi) -> None:
    plan = mi._compute_plan(
        issue_number=42,
        current_state="todo",
        target_state="backlog",
        has_board=False,
        labels=["state:todo", "type:feature"],
    )
    assert plan.add_label == "state:backlog"
    assert plan.remove_label == "state:todo"


def test_plan_label_substrate_handles_no_prior_state_label(mi) -> None:
    plan = mi._compute_plan(
        issue_number=42,
        current_state="todo",
        target_state="backlog",
        has_board=False,
        labels=["type:feature"],
    )
    assert plan.add_label == "state:backlog"
    assert plan.remove_label is None


def test_plan_board_substrate_no_label_mutation(mi) -> None:
    plan = mi._compute_plan(
        issue_number=42,
        current_state="todo",
        target_state="backlog",
        has_board=True,
        labels=[],
    )
    assert plan.add_label is None
    assert plan.remove_label is None


# --- structural type inference --------------------------------------


def test_infer_structural_type_recognises_each_prefix(mi, issue_types) -> None:
    assert mi._infer_structural_type("[EPIC] x", issue_types) == "epic"
    assert mi._infer_structural_type("[Task] x", issue_types) == "task"


def test_infer_structural_type_none_on_unknown(mi, issue_types) -> None:
    assert mi._infer_structural_type("Plain", issue_types) is None


# --- parent-chain walking --------------------------------------------


def test_walk_parent_chain_extracts_first_parent_ref(mi) -> None:
    body = "Feature: #42\n\n## What\nfoo"
    assert mi._walk_parent_chain(body) == [42]


def test_walk_parent_chain_extracts_epic_form(mi) -> None:
    body = "EPIC: #99\n\nbody"
    assert mi._walk_parent_chain(body) == [99]


def test_walk_parent_chain_skips_leading_blank_lines(mi) -> None:
    body = "\n\nUmbrella: #5\n"
    assert mi._walk_parent_chain(body) == [5]


def test_walk_parent_chain_returns_empty_when_no_parent_ref(mi) -> None:
    body = "## What\nno parent ref"
    assert mi._walk_parent_chain(body) == []


def test_walk_parent_chain_returns_empty_for_empty_body(mi) -> None:
    assert mi._walk_parent_chain("") == []


# --- state ordering ---------------------------------------------------


def test_state_is_behind(mi) -> None:
    assert mi._state_is_behind("todo", "backlog") is True
    assert mi._state_is_behind("backlog", "todo") is False
    assert mi._state_is_behind("in-progress", "in-progress") is False
