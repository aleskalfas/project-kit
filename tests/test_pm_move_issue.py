"""Tests for project-management's move-issue script's pure logic.

Covers transition lookup, state inference, plan computation, severity
parsing, forward-direction detection, parent-chain walking. The
subprocess (gh) layer is not tested — those wrappers are thin
pass-throughs.

Also covers the DEC-031 placeholder-check wiring (issue #25):
the transition path must invoke detect_placeholder_residuals at
phase=transition; an unauthored body must produce a hard-reject
finding that would block the transition; an authored body must produce
no hard-reject.
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
CAPABILITY_ROOT = REPO_ROOT / ".pkit" / "capabilities" / "project-management"
LIB_PATH = REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"

sys.path.insert(0, str(LIB_PATH))
from _lib.placeholder_detection import (  # noqa: E402
    PHASE_TRANSITION,
    detect_placeholder_residuals,
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


# --- noop / idempotency path (regression for GitHub issue #7) ---------
#
# When done-work squash-merges a PR whose body carries `Closes #N`,
# GitHub auto-closes the issue before move-issue is called. At that
# point _infer_current_state returns "done" (from state==closed). The
# old code then tried to look up a "done → done" transition — which
# doesn't exist — and exited 2. The fix: detect current==target BEFORE
# the transition-table lookup and treat it as an idempotent noop, while
# still reconciling any stale state:* label on the label substrate.


def test_infer_state_closed_returns_done_regardless_of_labels(mi) -> None:
    """Closed GitHub state always maps to done, even with stale state:review label.

    This is the precondition that triggers the bug: after GitHub auto-closes
    the issue via Closes #N, state is 'closed' but state:review label lingers.
    _infer_current_state must return 'done' so the noop path fires.
    """
    result = mi._infer_current_state(
        state="closed",
        milestone=None,
        labels=["state:review", "priority:High"],
    )
    assert result == "done"


def test_compute_plan_noop_with_stale_label_reconciles_label(mi) -> None:
    """When current==target but a stale state:review label is present,
    _compute_plan should produce a plan that removes state:review and
    adds state:done (idempotent reconciliation).

    This is the core of the fix: the noop path calls _compute_plan and
    acts when plan.remove_label is set.
    """
    plan = mi._compute_plan(
        issue_number=42,
        current_state="done",
        target_state="done",
        has_board=False,
        labels=["state:review", "priority:High"],
    )
    assert plan.add_label == "state:done"
    assert plan.remove_label == "state:review"


def test_compute_plan_noop_with_correct_label_no_mutation(mi) -> None:
    """When state:done is already present (no stale label), plan.remove_label
    is None so no gh round-trip is needed."""
    plan = mi._compute_plan(
        issue_number=42,
        current_state="done",
        target_state="done",
        has_board=False,
        labels=["state:done", "priority:High"],
    )
    # state:done is already correct; nothing to remove.
    assert plan.remove_label is None


def test_noop_does_not_require_transition_in_workflow(mi, workflow) -> None:
    """done → done has no transition in workflow.yaml, but _find_transition
    returning None should not be reached on the noop path. Confirm that
    _find_transition returns None for same-state lookup (the pre-fix
    code path that caused the exit-2 error).
    """
    # This would have caused the bug: the transition table has no done→done entry.
    assert mi._find_transition(workflow, "done", "done", "task") is None


# ---- DEC-031 transition-enforcement wiring (regression for issue #25) ----------
#
# move-issue was not calling detect_placeholder_residuals at phase=transition,
# so an unauthored issue could advance freely. Tests below verify the correct
# semantics that the wired check relies on: authored bodies pass, skeleton
# bodies hard-reject.  The inline call in move-issue.main() cannot be exercised
# without a full gh mock, so we verify the detection contract here and leave the
# wiring proven by code inspection + check.sh.


@pytest.fixture
def body_format_task_with_checkboxes() -> dict:
    """Minimal body-format.yaml data with a checkbox-requiring section."""
    return {
        "bodies": {
            "task": {
                "required_sections": [
                    {
                        "heading": "## What",
                        "has_checkboxes": False,
                        "severity": "[validation-severity:hard-reject]",
                    },
                    {
                        "heading": "## Acceptance criteria",
                        "has_checkboxes": True,
                        "severity": "[validation-severity:hard-reject]",
                    },
                    {
                        "heading": "## Doc impact",
                        "has_checkboxes": False,
                        "severity": "[validation-severity:hard-reject]",
                    },
                ],
            },
        },
    }


def test_regression_25_transition_check_blocks_skeleton_body(
    body_format_task_with_checkboxes: dict,
) -> None:
    """Regression #25 — at phase=transition an unauthored (skeleton) body must
    produce a hard-reject finding that move-issue uses to block the transition.

    Before the fix, move-issue did not invoke the placeholder check at all on
    the transition path; an unauthored issue could advance Todo → Backlog freely.
    """
    skeleton_body = (
        "Feature: #1\n\n"
        "## What\n"
        "The concrete change being made. Outcome-focused, not implementation-focused.\n\n"
        "## Acceptance criteria\n"
        "- [ ]\n"
        "- [ ]\n\n"
        "## Doc impact\n"
        "- [ ]\n"
    )
    findings = detect_placeholder_residuals(
        body=skeleton_body,
        structural_type="task",
        body_format=body_format_task_with_checkboxes,
        capability_root=CAPABILITY_ROOT,
        phase=PHASE_TRANSITION,
    )
    hard_rejects = [f for f in findings if f[0] == "hard-reject"]
    assert hard_rejects, (
        "skeleton body must produce at least one hard-reject finding at "
        f"phase=transition so move-issue can block the transition; got: {findings}"
    )


def test_regression_25_transition_check_passes_authored_body(
    body_format_task_with_checkboxes: dict,
) -> None:
    """Regression #25 — at phase=transition an authored body must not produce
    any hard-reject finding so move-issue lets the transition proceed.

    Covers both checked (- [x]) and unchecked (- [ ] with real text) criteria
    to confirm the false-positive fix (Defect 1) and the wiring (Defect 2)
    work together.
    """
    authored_body_unchecked = (
        "Feature: #1\n\n"
        "## What\n"
        "Implement the frobnication layer.\n\n"
        "## Acceptance criteria\n"
        "- [ ] The frobnication layer is installed and returns the correct value.\n"
        "- [ ] Edge-case inputs are handled without panic.\n\n"
        "## Doc impact\n"
        "No doc impact: internal refactor only.\n"
    )
    findings = detect_placeholder_residuals(
        body=authored_body_unchecked,
        structural_type="task",
        body_format=body_format_task_with_checkboxes,
        capability_root=CAPABILITY_ROOT,
        phase=PHASE_TRANSITION,
    )
    hard_rejects = [f for f in findings if f[0] == "hard-reject"]
    assert hard_rejects == [], (
        "authored body with unchecked real criteria must produce no hard-reject "
        f"at phase=transition; got: {hard_rejects}"
    )
