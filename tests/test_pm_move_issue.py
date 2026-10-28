"""Tests for project-management's move-issue script's pure logic.

Covers transition lookup, state inference, plan computation, severity
parsing, forward-direction detection. The parent an issue's first line
names is read by `_lib/body_parent_ref.parent_issue`, tested in
`test_pm_body_parent_ref.py`. The subprocess (gh) layer is not tested —
those wrappers are thin pass-throughs.

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

from tests.pm_composed_move_support import FakeEngine, MoveIssueInProcess, status_at
from tests.pm_ownership_support import (
    FakeGitHub,
    clone_with,
    seat_issue,
    seat_snapshot,
    snapshot_with,
    use,
)
from tests.pm_state_issue_fakes import FakeRepo

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = (
    REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts" / "move-issue.py"
)
CAPABILITY_ROOT = REPO_ROOT / ".pkit" / "capabilities" / "project-management"
LIB_PATH = REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"

sys.path.insert(0, str(LIB_PATH))
from _lib import instance_claims  # noqa: E402
from _lib.placeholder_detection import (  # noqa: E402
    PHASE_TRANSITION,
    detect_placeholder_residuals,
)
from _lib.structural_type import structural_type_from_kind_label  # noqa: E402


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
    """Compact fixture mirroring workflow.yaml's transitions block.

    Review is task-only (DEC-006, "State machine" and "Cascade rule"). No
    parent-typed review→done row exists: containers never enter Review, so
    no closure path from Review is needed for them.
    """
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
            {
                "from": "in-progress",
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


@pytest.fixture
def classification() -> dict:
    """Compact fixture mirroring classification.yaml's type axis.

    Carries `title_prefix_by_value` (the kind-driven prefixes) and the
    `structural_restriction.allowed_structural_types_per_kind` mapping the
    fallback reads to recover a structural type from a `type:*` label.
    """
    return {
        "axes": {
            "type": {
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


def test_find_transition_review_to_done_not_available_for_parent_types(mi, workflow) -> None:
    """review → done is NOT available to epic/feature/umbrella (DEC-006, "Cascade rule").

    Containers never enter Review via forward cascade (the cap is in-progress),
    so no closure path from Review is needed for them, and workflow.yaml holds
    no such row.
    """
    for parent_type in ("epic", "feature", "umbrella"):
        t = mi._find_transition(workflow, "review", "done", parent_type)
        assert t is None, (
            f"parent type {parent_type!r} must not have a review→done "
            "transition — containers never enter Review"
        )


# --- legal targets --------------------------------------------------


def test_legal_targets_lists_outgoing_for_state(mi, workflow) -> None:
    targets = mi._legal_targets(workflow, "backlog", "task")
    assert "in-progress" in targets
    assert "todo" not in targets


def test_legal_targets_filters_by_type(mi, workflow) -> None:
    # in-progress can go to review for task only.
    assert "review" in mi._legal_targets(workflow, "in-progress", "task")
    assert "review" not in mi._legal_targets(workflow, "in-progress", "feature")


def test_legal_targets_review_to_done_not_available_for_parent_types(mi, workflow) -> None:
    """Parents have no review → done transition (DEC-006, "Cascade rule").

    Containers never enter Review via the forward cascade; their closure path
    is in-progress → done (cascade-eligibility-close).
    """
    for parent_type in ("epic", "feature", "umbrella"):
        assert "done" not in mi._legal_targets(workflow, "review", parent_type), (
            f"parent type {parent_type!r} must not have 'done' reachable from 'review'"
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


# --- --bypass reason enforcement (issue #580) -----------------------
#
# `--bypass` overrides a bypassable-with-audit gate, which records the
# reason in the audit comment (DEC-014); the override-flag convention
# (DEC-046) requires that reason to be non-empty. A bare `--bypass` with
# no `--bypass-reason` must refuse, not substitute a placeholder. The
# refusal predicate is pure and unit-tested here; the argparse/gh main()
# wiring calls it before any mutation or audit comment.


def test_bypass_reason_missing_true_when_bypass_without_reason(mi) -> None:
    """Acceptance 1 — bare --bypass (no reason) is flagged for refusal."""
    assert mi._bypass_reason_missing(True, None) is True
    assert mi._bypass_reason_missing(True, "") is True
    assert mi._bypass_reason_missing(True, "   ") is True
    assert mi._bypass_reason_missing(True, "\t\n") is True


def test_bypass_reason_missing_false_when_reason_present(mi) -> None:
    """Acceptance 2 — --bypass with a non-empty reason passes."""
    assert mi._bypass_reason_missing(True, "landing hotfix out of band") is False
    assert mi._bypass_reason_missing(True, "x") is False
    # Leading/trailing whitespace around real content is still a real reason.
    assert mi._bypass_reason_missing(True, "  real reason  ") is False


def test_bypass_reason_missing_false_when_bypass_not_set(mi) -> None:
    """The flag is inert without --bypass, so there is nothing to enforce
    (the TTY-confirm path does not post an audit comment)."""
    assert mi._bypass_reason_missing(False, None) is False
    assert mi._bypass_reason_missing(False, "") is False
    assert mi._bypass_reason_missing(False, "unused reason") is False


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
        mi._infer_current_state(state="open", milestone={"title": "M1"}, labels=["type:feature"])
        == "backlog"
    )


def test_infer_state_no_milestone_no_label_means_todo(mi) -> None:
    assert mi._infer_current_state(state="open", milestone={}, labels=[]) == "todo"


# --- plan computation -----------------------------------------------


def test_plan_label_substrate_adds_new_and_removes_old(mi) -> None:
    plan = mi._compute_plan(
        issue_number=42,
        current_state="todo",
        target_state="backlog",
        state_on_board=False,
        labels=["state:todo", "type:feature"],
    )
    assert plan.add_label == "state:backlog"
    assert plan.remove_label == "state:todo"


def test_plan_label_substrate_handles_no_prior_state_label(mi) -> None:
    plan = mi._compute_plan(
        issue_number=42,
        current_state="todo",
        target_state="backlog",
        state_on_board=False,
        labels=["type:feature"],
    )
    assert plan.add_label == "state:backlog"
    assert plan.remove_label is None


def test_plan_board_substrate_no_label_mutation(mi) -> None:
    plan = mi._compute_plan(
        issue_number=42,
        current_state="todo",
        target_state="backlog",
        state_on_board=True,
        labels=[],
    )
    assert plan.add_label is None
    assert plan.remove_label is None


# --- structural type inference --------------------------------------


def test_infer_structural_type_recognises_each_prefix(mi, issue_types) -> None:
    assert mi.infer_structural_type("[EPIC] x", issue_types) == "epic"
    assert mi.infer_structural_type("[Task] x", issue_types) == "task"


def test_infer_structural_type_none_on_unknown(mi, issue_types) -> None:
    assert mi.infer_structural_type("Plain", issue_types) is None


# --- structural type: type:* label fallback (issue #370) -------------
#
# When the title prefix is edited away, inference falls back to the issue's
# `type:*` kind label to recover the structural type. PRECEDENCE: the title
# prefix wins; the label is consulted only when no prefix matches. A `type:*`
# label can only ever recover `task` (every non-feature kind maps to the single
# structural type `task`); a container has no distinguishing `type:*` label, so
# an edited-away container prefix stays unrecoverable (malformed).


def test_infer_structural_type_prefix_wins_over_label(mi, issue_types, classification) -> None:
    """Acceptance 4 — title prefix takes precedence over the `type:*` label.

    A [Feature] container that (oddly) also carries a `type:bug` label still
    resolves to `feature` from the prefix; the label fallback is never consulted.
    """
    assert (
        mi.infer_structural_type(
            "[Feature] x", issue_types, classification=classification, labels=["type:bug"]
        )
        == "feature"
    )


def test_infer_structural_type_recovers_task_from_label_when_prefix_absent(
    mi, issue_types, classification
) -> None:
    """Acceptance 1 & 2 — prefix edited away + `type:*` label ⇒ recover `task`."""
    assert (
        mi.infer_structural_type(
            "edited-away title", issue_types, classification=classification, labels=["type:bug"]
        )
        == "task"
    )
    # Holds for every task-only kind, not just bug.
    for kind in ("docs", "test", "refactor", "maintenance"):
        assert (
            mi.infer_structural_type(
                "edited-away title",
                issue_types,
                classification=classification,
                labels=[f"type:{kind}"],
            )
            == "task"
        ), f"kind {kind!r} must recover structural type 'task'"


def test_infer_structural_type_container_without_label_is_malformed(
    mi, issue_types, classification
) -> None:
    """Acceptance 3 — container prefix edited away, no `type:*` label ⇒ None.

    A container (EPIC/Feature/Umbrella) carries no distinguishing `type:*`
    label, so it cannot be recovered and must surface as malformed (None) rather
    than be silently guessed.
    """
    assert (
        mi.infer_structural_type(
            "edited-away epic title",
            issue_types,
            classification=classification,
            labels=["priority:High", "workstream:core"],
        )
        is None
    )


def test_infer_structural_type_feature_kind_label_is_ambiguous(
    mi, issue_types, classification
) -> None:
    """A `type:feature` label maps to multiple structural types, so it cannot
    recover a unique structural type — the fallback returns None rather than
    guessing (only task-only kinds are unambiguous)."""
    assert (
        mi.infer_structural_type(
            "edited-away title", issue_types, classification=classification, labels=["type:feature"]
        )
        is None
    )


def test_structural_type_from_kind_label_reads_mapping(mi, classification) -> None:
    """The helper reads the kind→structural mapping straight from the schema's
    `allowed_structural_types_per_kind` (single-valued ⇒ recoverable)."""
    assert structural_type_from_kind_label(["type:bug"], classification) == "task"
    assert structural_type_from_kind_label(["type:feature"], classification) is None
    assert structural_type_from_kind_label(["priority:High"], classification) is None


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
        state_on_board=False,
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
        state_on_board=False,
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


# ---- DEC-006 "Cascade rule" — container forward-cascade cap at in-progress ------
#
# A child entering review (or done) must NOT promote its container to review.
# The forward cascade is scoped to todo → backlog → in-progress; containers
# reach done only via the closure cascade (in-progress → done,
# cascade-eligibility-close). _cascade_forward_target caps the ancestor's
# bump target at in-progress regardless of the child state.


def test_cascade_forward_target_caps_review_at_in_progress(mi) -> None:
    """Child entering review → ancestor cascade target is in-progress, not review."""
    assert mi._cascade_forward_target("review") == "in-progress"


def test_cascade_forward_target_caps_done_at_in_progress(mi) -> None:
    """Child entering done → ancestor cascade target is in-progress, not done.

    Closure cascade (in-progress → done) is the correct path to done for containers.
    """
    assert mi._cascade_forward_target("done") == "in-progress"


def test_cascade_forward_target_passes_through_in_progress(mi) -> None:
    """Child entering in-progress → ancestor cascade target is in-progress (unchanged)."""
    assert mi._cascade_forward_target("in-progress") == "in-progress"


def test_cascade_forward_target_passes_through_backlog(mi) -> None:
    """Child entering backlog → ancestor cascade target is backlog (unchanged)."""
    assert mi._cascade_forward_target("backlog") == "backlog"


def test_cascade_forward_target_passes_through_todo(mi) -> None:
    """Child entering todo → ancestor cascade target is todo (unchanged)."""
    assert mi._cascade_forward_target("todo") == "todo"


def test_container_closure_path_is_in_progress_to_done(mi, workflow) -> None:
    """Closure-cascade path for containers is in-progress → done (DEC-006).

    This is the only Done path for containers; the forward cascade never
    takes them to review.
    """
    for parent_type in ("epic", "feature", "umbrella"):
        t = mi._find_transition(workflow, "in-progress", "done", parent_type)
        assert t is not None, (
            f"container type {parent_type!r} must have in-progress→done "
            "transition for the closure-cascade path"
        )
        assert t.authorisation == "user"
        assert t.severity == "hard-reject"


def test_state_is_behind_in_progress_not_behind_in_progress(mi) -> None:
    """Container already at in-progress is not 'behind' the capped cascade target.

    This confirms the no-op path: a container at in-progress while the child
    enters review/done must not be re-bumped (it's already at the cap).
    """
    capped = mi._cascade_forward_target("review")  # == "in-progress"
    assert not mi._state_is_behind("in-progress", capped)


def test_cascade_review_child_bumps_behind_container_to_in_progress(mi) -> None:
    """A container that is behind (todo/backlog) gets bumped to in-progress,
    not to review, when a child enters review (DEC-006, "Cascade rule").
    """
    capped = mi._cascade_forward_target("review")  # == "in-progress"
    assert mi._state_is_behind("todo", capped)
    assert mi._state_is_behind("backlog", capped)
    plan = mi._compute_plan(
        issue_number=1,
        current_state="backlog",
        target_state=capped,
        state_on_board=False,
        labels=["state:backlog"],
    )
    assert plan.add_label == "state:in-progress"
    assert plan.remove_label == "state:backlog"


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


# ---- canonical audit comment (DEC-049) ------------------------------

from types import SimpleNamespace  # noqa: E402

_CAP_ROOT = Path(".pkit/capabilities/project-management")


def test_load_audit_template_reads_schema_marker(mi) -> None:
    tmpl = mi._load_audit_template(_CAP_ROOT)
    assert "<!-- pkit-audit -->" in tmpl
    assert "Bypassed by <name> <<email>>: <reason>" in tmpl


def test_load_audit_template_falls_back_on_bad_root(mi) -> None:
    assert mi._load_audit_template(Path("/nonexistent")) == mi._AUDIT_TEMPLATE_FALLBACK


def test_render_audit_comment_canonical(mi) -> None:
    invoker = SimpleNamespace(github_login="alice", email="alice@x.io")
    out = mi._render_audit_comment(_CAP_ROOT, invoker, "verbal PM approval")
    assert out.startswith("<!-- pkit-audit -->")
    assert "Bypassed by alice <alice@x.io>: verbal PM approval" in out


def test_render_audit_comment_no_email_is_clean(mi) -> None:
    invoker = SimpleNamespace(github_login="alice", email=None)
    out = mi._render_audit_comment(_CAP_ROOT, invoker, "reason")
    assert out.startswith("<!-- pkit-audit -->")
    assert "Bypassed by alice: reason" in out
    assert "<<" not in out and "<>" not in out  # no empty angle brackets


# ---- audit projection intensity (DEC-049) ---------------------------


def test_audit_projection_levels(mi) -> None:
    assert mi._audit_projection({"audit": {"projection": "full"}}) == "full"
    assert mi._audit_projection({"audit": {"projection": "off"}}) == "off"
    assert mi._audit_projection({"audit": {"projection": "audit"}}) == "audit"
    assert mi._audit_projection({}) == "audit"  # default
    assert mi._audit_projection({"audit": {"projection": "bogus"}}) == "audit"  # invalid → default
    assert mi._audit_projection(None) == "audit"


def test_render_provenance_comment(mi, monkeypatch) -> None:
    monkeypatch.setattr(mi, "_pkit_version", lambda: "1.148.1")
    invoker = SimpleNamespace(github_login="alice", email=None)
    out = mi._render_provenance_comment(invoker, "backlog", "in-progress")
    assert out.startswith("<!-- pkit-audit -->")
    assert "alice moved backlog → in-progress" in out
    assert "pkit 1.148.1" in out


def test_render_provenance_comment_no_version(mi, monkeypatch) -> None:
    monkeypatch.setattr(mi, "_pkit_version", lambda: "")
    out = mi._render_provenance_comment(SimpleNamespace(github_login="a", email=None), None, "done")
    assert "a moved done (governed by pkit)" in out
    assert "pkit " not in out  # no dangling version stamp


# ---- transition audit retry is idempotent (#901) --------------------
#
# A bypassed transition posts its audit comment BEFORE the label write, so the
# justification survives a failed mutation (DEC-049). A retry of that failed
# attempt must not post a second one (one audit comment per audited mutation),
# while a different reason, or the same transition after the move has landed
# and been journaled, still posts.

import json as _json  # noqa: E402


class _FakeIssueComments:
    """A stand-in for `gh_run` that keeps the issue's comments in memory."""

    def __init__(self) -> None:
        self.bodies: list[str] = []
        self.posts = 0

    def __call__(self, cmd, config, check=False):
        if cmd[:3] == ["gh", "issue", "view"]:
            # What GitHub reports for comments the gh-authenticated identity
            # posted and never edited — pkit's own posts.
            payload = {
                "comments": [
                    {"body": b, "viewerDidAuthor": True, "includesCreatedEdit": False}
                    for b in self.bodies
                ]
            }
            return SimpleNamespace(returncode=0, stdout=_json.dumps(payload), stderr="")
        if cmd[:3] == ["gh", "issue", "comment"]:
            self.bodies.append(cmd[cmd.index("--body") + 1])
            self.posts += 1
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        raise AssertionError(f"unexpected gh call: {cmd}")


def _post(mi, from_state, to_state, reason, landed_moves):
    # `main` strips the reason before rendering and keying; mirror it.
    reason = reason.strip()
    invoker = SimpleNamespace(github_login="alice", email="alice@x.io")
    key = mi._transition_audit_key(from_state, to_state, reason, landed_moves)
    body = mi._render_audit_comment(_CAP_ROOT, invoker, reason) + "\n\n" + key
    return mi._post_transition_audit_once(42, body, key, {})


def test_retried_bypass_posts_no_second_audit_comment(mi, monkeypatch) -> None:
    gh = _FakeIssueComments()
    monkeypatch.setattr(mi, "gh_run", gh)
    assert _post(mi, "todo", "backlog", "verbal PM approval", "3")
    # The label write failed, so the journal did not grow; the retry reproduces
    # the transition, the reason and the journal length exactly.
    assert _post(mi, "todo", "backlog", "  verbal PM approval ", "3")
    assert gh.posts == 1


def test_bypass_with_a_different_reason_still_posts(mi, monkeypatch) -> None:
    gh = _FakeIssueComments()
    monkeypatch.setattr(mi, "gh_run", gh)
    assert _post(mi, "todo", "backlog", "verbal PM approval", "3")
    assert _post(mi, "todo", "backlog", "sprint planning decision", "3")
    assert gh.posts == 2


def test_same_bypass_after_the_move_landed_posts_again(mi, monkeypatch) -> None:
    """A later, genuinely new mutation — the issue went back and is re-promoted
    for the same reason — has a longer journal, so it gets its own comment."""
    gh = _FakeIssueComments()
    monkeypatch.setattr(mi, "gh_run", gh)
    assert _post(mi, "todo", "backlog", "verbal PM approval", "3")
    assert _post(mi, "todo", "backlog", "verbal PM approval", "5")
    assert gh.posts == 2


def test_unreadable_comments_post_rather_than_skip(mi, monkeypatch) -> None:
    posted: list[list[str]] = []

    def gh(cmd, config, check=False):
        if cmd[:3] == ["gh", "issue", "view"]:
            return SimpleNamespace(returncode=1, stdout="", stderr="boom")
        posted.append(cmd)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(mi, "gh_run", gh)
    assert _post(mi, "todo", "backlog", "reason", "0")
    assert len(posted) == 1


def test_failed_post_is_reported_so_the_move_aborts(mi, monkeypatch) -> None:
    def gh(cmd, config, check=False):
        if cmd[:3] == ["gh", "issue", "view"]:
            return SimpleNamespace(returncode=0, stdout='{"comments": []}', stderr="")
        return SimpleNamespace(returncode=1, stdout="", stderr="denied")

    monkeypatch.setattr(mi, "gh_run", gh)
    assert _post(mi, "todo", "backlog", "reason", "0") is False


def test_transition_audit_key_components(mi) -> None:
    key = mi._transition_audit_key("todo", "backlog", "why", "2")
    assert key.startswith(mi.TRANSITION_AUDIT_KEY_PREFIX) and key.endswith(" -->")
    assert key == mi._transition_audit_key("todo", "backlog", " why ", "2")
    assert key != mi._transition_audit_key("todo", "in-progress", "why", "2")
    assert key != mi._transition_audit_key("backlog", "backlog", "why", "2")
    assert key != mi._transition_audit_key("todo", "backlog", "why", "3")
    assert key != mi._transition_audit_key("todo", "backlog", "why", "")
    assert key != mi._transition_audit_key("todo", "backlog", "why", "state-label-events:2")
    # A reason that tries to close the HTML comment cannot: it is hashed.
    assert "-->" not in mi._transition_audit_key("todo", "backlog", "x --> y", "2")[:-4]


def test_logging_on_key_is_unchanged_by_the_logging_off_fix(mi) -> None:
    """With a journal kept, the landed-move component is the bare journal length
    — the same key a pre-#954 move-issue minted, so a retry across the upgrade
    is still recognised."""
    expected = mi._audit.audit_key("move-issue", "todo", "backlog", "why", "2")
    assert mi._transition_audit_key("todo", "backlog", "why", "2") == expected


def test_journal_length_and_position_read_one_status(mi) -> None:
    status = {"position": {"state": "todo"}, "journal": [{}, {}]}
    assert mi._position_from_status(status) == "todo"
    assert mi._journal_length_from_status(status) == 2
    assert mi._journal_length_from_status({"position": {"state": "todo"}}) is None
    assert mi._journal_length_from_status(None) is None
    assert mi._position_from_status(None) is None
    assert mi._position_from_status({"position": {"indeterminate": True}}) is None


# ---- the landed-move component, in both journal modes (#954) ----------

_LOGGING_OFF = {
    "position": {"state": "todo"},
    "journal": [],
    "journal_logging": {"enabled": False, "committed": False},
}


class _TimelineGh:
    """A `gh_run` stand-in answering only the issue's timeline read."""

    def __init__(self, events: list[dict], returncode: int = 0) -> None:
        self.events = events
        self.returncode = returncode
        self.calls = 0

    def __call__(self, cmd, config, check=False):
        assert cmd[:3] == ["gh", "api", "--paginate"], cmd
        assert cmd[3].endswith("/issues/42/timeline")
        self.calls += 1
        return SimpleNamespace(
            returncode=self.returncode,
            stdout=_json.dumps(self.events),
            stderr="",
        )


def _no_gh(*_a, **_k):  # pragma: no cover - must not run
    raise AssertionError("the landed-move count must not read the timeline here")


def test_journal_logging_off_needs_the_engine_to_say_so(mi) -> None:
    assert mi._journal_logging_off(_LOGGING_OFF)
    assert not mi._journal_logging_off({"journal_logging": {"enabled": True}, "journal": []})
    # An engine that predates the setting always kept a journal.
    assert not mi._journal_logging_off({"journal": []})
    # No payload says nothing either way.
    assert not mi._journal_logging_off(None)


def test_landed_moves_is_the_journal_length_where_a_journal_is_kept(mi, monkeypatch) -> None:
    monkeypatch.setattr(mi, "gh_run", _no_gh)
    kept = {"journal_logging": {"enabled": True, "committed": False}, "journal": [{}, {}]}
    assert mi._landed_moves(42, kept, {}, None) == "2"
    assert mi._landed_moves(42, {"journal": [{}, {}]}, {}, None) == "2"
    # An unreachable engine: unknown, as before logging became optional.
    assert mi._landed_moves(42, None, {}, None) == ""


def test_landed_moves_counts_state_label_events_when_logging_is_off(mi, monkeypatch) -> None:
    """Labels put on and taken off both count; other labels and events do not."""
    events = [
        {"event": "labeled", "label": {"name": "state:todo"}},
        {"event": "labeled", "label": {"name": "type:task"}},
        {"event": "commented"},
        {"event": "unlabeled", "label": {"name": "state:todo"}},
        {"event": "labeled", "label": {"name": "state:backlog"}},
    ]
    gh = _TimelineGh(events)
    monkeypatch.setattr(mi, "gh_run", gh)
    assert mi._landed_moves(42, _LOGGING_OFF, {}, None) == "state-label-events:3"
    assert gh.calls == 1


def test_landed_moves_is_empty_when_the_timeline_cannot_be_read(mi, monkeypatch) -> None:
    monkeypatch.setattr(mi, "gh_run", _TimelineGh([], returncode=1))
    assert mi._landed_moves(42, _LOGGING_OFF, {}, None) == ""


def test_landed_moves_reads_no_timeline_when_no_label_carries_state(mi, monkeypatch) -> None:
    """The map binds state to the board, so `move-issue` writes no label and the
    timeline's label events say nothing about moves."""
    monkeypatch.setattr(mi, "gh_run", _no_gh)
    on_board = mi.axis_labels.SubstrateMap(axes={"state": {"board": True}})
    assert mi._landed_moves(42, _LOGGING_OFF, {"has_projects_v2_board": True}, on_board) == ""


def test_audit_comment_is_posted_before_the_label_write() -> None:
    """The pre-mutation order DEC-049 requires: the audit post precedes the
    label edit in `main`, so a failed edit leaves the justification behind."""
    src = SCRIPT_PATH.read_text(encoding="utf-8")
    main_src = src[src.index("def main(") : src.index("def _bypass_reason_missing(")]
    assert main_src.index("_post_transition_audit_once(") < main_src.index(
        "_gh_apply_state_label(args.issue_number, plan, config)\n        if not ok"
    )


# ---- the clash guard (DEC-035 point 6) ------------------------------------------
#
# move-issue runs in process, as a composing verb's child would; its ownership
# reads and writes reach an in-memory GitHub, and it makes no other write.


def _owned_by_instance_3() -> FakeGitHub:
    from _lib import instance_ownership

    github = FakeGitHub()
    github.add(42, assignees=("me",))
    claim = instance_ownership.format_event_comment(event="claim", instance=3)
    github.post(42, claim)
    return github


def _move_42(monkeypatch, github: FakeGitHub, *extra: str, seats: FakeRepo | None = None) -> int:
    """Move #42 as instance 2, or, with `seats`, as the clone that took the seat
    `worker-2`, whose state issue `seats` holds."""
    issue = {
        "title": "[Task] do the thing",
        "labels": ["type:bug", "state:in-progress"],
        "assignees": [{"login": "me"}],
        "state": "OPEN",
        "body": "## What\nx",
        "milestone": None,
    }
    move = MoveIssueInProcess(monkeypatch, issue)
    claims = move.module.instance_claims
    use(claims, monkeypatch, github)
    clone_with(claims, monkeypatch, 2 if seats is None else None)
    if seats is not None:
        doc = {"schema_version": 1, "seats": [{"name": "worker-2", "role": "worker"}]}
        doc["seats"][0]["state_issue"] = 13
        snapshot_with(claims, monkeypatch, seat_snapshot(claims, doc, seats), hint="worker-2")
    FakeEngine(status_at("in-progress")).install(monkeypatch)
    argv = [sys.executable, "move-issue.py", "42", "--to", "in-progress", "--yes", *extra]
    return move.run(argv).returncode


def test_the_clash_guard_refuses_a_move_of_another_instances_issue(monkeypatch, capsys) -> None:
    github = _owned_by_instance_3()
    assert _move_42(monkeypatch, github) == 1
    assert github.writes() == []
    err = capsys.readouterr().err
    assert (
        "[refused] move-issue #42: #42 is owned by instance 3, and this clone is instance 2" in err
    )
    assert 'pass --bypass-owner "<reason>"' in err


def test_bypass_owner_posts_the_reason_and_moves(monkeypatch, capsys) -> None:
    github = _owned_by_instance_3()
    assert _move_42(monkeypatch, github, "--bypass-owner", "its session is gone") == 0
    assert [argv[2] for argv in github.writes()] == ["comment"]
    assert "its session is gone" in github.issues[42].comments[-1]["body"]
    assert "[noop] already at target state" in capsys.readouterr().out


def test_a_move_from_a_seat_this_clone_no_longer_holds_refuses_and_writes_nothing(
    monkeypatch, capsys
) -> None:
    """DEC-059 point 6: the clone's seat is confirmed on its state issue before
    the guard runs. Another clone took it, so the move refuses, and even a bypass
    of the guard writes nothing."""
    github = FakeGitHub()
    github.add(42, assignees=("me",))
    seats = FakeRepo()
    seat_issue(instance_claims, seats, 13, "worker-2", ("me", "k9"))
    assert _move_42(monkeypatch, github, "--bypass-owner", "mine", seats=seats) == 1
    assert github.calls == [] and seats.writes() == []
    err = capsys.readouterr().err
    assert "[refused] move-issue #42: this clone no longer holds the seat worker-2" in err
    assert "Nothing was written." in err


def test_a_move_from_the_seat_this_clone_holds_goes_on(monkeypatch, capsys) -> None:
    github = FakeGitHub()
    github.add(42, assignees=("me",))
    seats = FakeRepo()
    seat_issue(instance_claims, seats, 13, "worker-2", ("me", "k2"))
    assert _move_42(monkeypatch, github, seats=seats) == 0
    assert seats.writes() == []
    assert "[noop] already at target state" in capsys.readouterr().out


# ---- the move back from In Progress (DEC-006, "Moving back from In Progress") ----


def _shipped_workflow() -> dict:
    from ruamel.yaml import YAML

    return YAML(typ="safe").load((CAPABILITY_ROOT / "schemas" / "workflow.yaml").read_text())


def test_the_shipped_workflow_declares_the_move_back_for_every_type_in_progress() -> None:
    """Every type that has In Progress may move back to Backlog and to Todo, a
    move the user holds at hard-reject, made by `move-issue`."""
    process = _shipped_workflow()["process"]
    (in_progress,) = [s for s in process["states"] if s["id"] == "in-progress"]
    types = in_progress["applies_to"]
    assert types
    for target in ("backlog", "todo"):
        (move,) = [
            t for t in process["transitions"] if (t["from"], t["to"]) == ("in-progress", target)
        ]
        assert move["applies_to"] == types
        assert move["authorisation"] == "user"
        assert move["severity"] == "[validation-severity:hard-reject]"
        assert move["command"] == move["trigger"] == "move-issue"


def test_the_move_back_is_found_and_held_by_the_user(mi) -> None:
    workflow = _shipped_workflow()
    for kind in ("task", "feature", "epic", "umbrella"):
        for target in ("backlog", "todo"):
            move = mi._find_transition(workflow, "in-progress", target, kind)
            assert move is not None
            assert (move.authorisation, move.severity) == ("user", "hard-reject")
        assert {"backlog", "todo"} <= set(mi._legal_targets(workflow, "in-progress", kind))
    # Only In Progress moves back: Backlog still has no way to Todo.
    assert mi._find_transition(workflow, "backlog", "todo", "task") is None


def test_only_a_move_to_an_earlier_state_is_a_move_back(mi) -> None:
    assert mi._is_move_back("in-progress", "backlog") is True
    assert mi._is_move_back("in-progress", "todo") is True
    assert mi._is_move_back("backlog", "in-progress") is False
    assert mi._is_move_back("in-progress", "in-progress") is False
    assert mi._is_move_back("open", "todo") is False


# The move back run in process: move-issue's own `main()` against one issue, its
# writes recorded in the order it makes them, and the ownership reads and writes
# reaching an in-memory GitHub where #42 is claimed by this clone, instance 2.

_TASK_BODY = (
    "## What\nShip the frobnicator.\n\n"
    "## Acceptance criteria\n- [ ] The frobnicator ships.\n\n"
    "## Doc impact\nNo doc impact: internal only.\n"
)
_FEATURE_BODY = (
    "## What\nA frobnication layer.\n\n## Acceptance criteria\n- [ ] Every Task under it ships.\n"
)
_MILESTONE = {"number": 3, "title": "Alpha"}


def _child(mi, number: int, state: str):
    return (mi.containment.ResolvedChild(number, mi.containment.ChildSubstrate.NATIVE), state)


def _move_back(
    monkeypatch,
    *argv: str,
    milestone: dict | None = _MILESTONE,
    container: bool = False,
    children=None,
    projection: str = "audit",
    failing: tuple[str, ...] = (),
    instance: int | None = 2,
    assignee: str = "me",
    claims: tuple[tuple[int, str], ...] = ((2, "me"),),
    labels: tuple[str, ...] = (),
    board_carried: bool = False,
):
    """Run `move-issue 42 <argv>` on #42 In Progress, as the clone `instance`
    (None: no instance id); the exit code, the writes in order, and the
    in-memory GitHub, whose `failing` calls fail once. #42 is assigned to
    `assignee`, and carries a claim on its comment log for each `claims` entry,
    an instance and the account that made it, and the ownership `labels`."""
    issue = {
        "title": "[Feature] the frobnication layer" if container else "[Task] ship the frobnicator",
        "labels": ["state:in-progress"] if container else ["type:bug", "state:in-progress"],
        "assignees": [{"login": assignee}],
        "state": "OPEN",
        "body": _FEATURE_BODY if container else _TASK_BODY,
        "milestone": milestone,
    }
    move = MoveIssueInProcess(monkeypatch, issue)
    mi = move.module
    writes: list[tuple] = []

    def comment(n, body, key, _config):
        writes.append(("comment", n, body))
        return True

    def label(n, plan, _config):
        writes.append(("label", n, plan.add_label, plan.remove_label))
        return True

    def journal(n, origin, target, _actor, reason=None):
        writes.append(("journal", n, origin, target, reason))
        return True

    monkeypatch.setattr(mi, "_post_transition_audit_once", comment)
    monkeypatch.setattr(mi, "_gh_apply_state_label", label)
    monkeypatch.setattr(mi, "_journal_move", journal)
    monkeypatch.setattr(mi, "_landed_moves", lambda *_a: "3")
    monkeypatch.setattr(mi, "_audit_projection", lambda _config: projection)
    monkeypatch.setattr(
        mi, "_read_children", lambda *_a: children if children is not None else mi._Children()
    )
    github = FakeGitHub()
    github.add(42, assignees=(assignee,), labels=labels)
    for number, author in claims:
        claim = mi.instance_claims.ownership.format_event_comment(event="claim", instance=number)
        github.post(42, claim, author=author)
    github.failing.update(failing)
    use(mi.instance_claims, monkeypatch, github)
    clone_with(mi.instance_claims, monkeypatch, instance)
    if board_carried:
        monkeypatch.setattr(mi.axis_carriage, "is_board_carried", lambda *_a, **_kw: True)
    FakeEngine(status_at("in-progress")).install(monkeypatch)
    rc = move.run([sys.executable, "move-issue.py", "42", *argv]).returncode
    return rc, writes, github


def _ownership_events(github: FakeGitHub) -> list[str]:
    """The ownership events on #42, as `<event> <instance>`."""
    out = []
    for comment in github.issues[42].comments:
        body = comment["body"]
        if "event=" in body:
            event = body.split("event=")[1].split()[0]
            instance = body.split("instance=")[1].split()[0]
            out.append(f"{event} {instance}")
    return out


def test_a_move_back_posts_its_reason_moves_journals_and_releases_the_owner(
    monkeypatch, capsys
) -> None:
    rc, writes, github = _move_back(
        monkeypatch, "--to", "backlog", "--reason", "stalled since September", "--yes"
    )
    assert rc == 0
    assert [w[0] for w in writes] == ["comment", "label", "journal"]
    body = writes[0][2]
    assert body.startswith("<!-- pkit-audit -->")
    assert "stalled since September" in body
    assert "Moved back from in-progress to backlog" in body
    assert writes[1] == ("label", 42, "state:backlog", "state:in-progress")
    assert writes[2] == (
        "journal",
        42,
        "in-progress",
        "backlog",
        "move back: stalled since September",
    )
    assert _ownership_events(github) == ["claim 2", "release 2"]
    out = capsys.readouterr().out
    assert "[ok] ownership: #42 released (instance 2)." in out
    assert "[ok] transitioned #42: in-progress → backlog" in out


def test_a_release_that_fails_leaves_the_move_back_standing(monkeypatch, capsys) -> None:
    rc, writes, _github = _move_back(
        monkeypatch, "--to", "backlog", "--reason", "stalled", "--yes", failing=("comment",)
    )
    assert rc == 0
    assert [w[0] for w in writes] == ["comment", "label", "journal"]
    err = capsys.readouterr().err
    assert "#42 moved back to backlog, but its owner could not all be released" in err


# An owner this clone cannot release refuses the move back before anything is
# written, so an issue never waits in Backlog or Todo still claimed (DEC-006,
# DEC-035 point 4).


def test_a_clone_with_no_instance_moves_back_an_issue_no_instance_owns(monkeypatch, capsys) -> None:
    """DEC-035 point 1: a clone with no instance id touches no marker, and an
    issue with no owner leaves it none to touch."""
    rc, writes, github = _move_back(
        monkeypatch, "--to", "backlog", "--reason", "stalled", "--yes", instance=None, claims=()
    )
    assert rc == 0
    assert [w[0] for w in writes] == ["comment", "label", "journal"]
    assert github.writes() == []
    assert "ownership:" not in capsys.readouterr().out


@pytest.mark.parametrize(
    ("claims", "labels", "owner"),
    [
        pytest.param(((2, "me"),), (), "instance 2", id="a-claim-on-the-comment-log"),
        pytest.param((), ("instance:3",), "instance 3", id="an-instance-label"),
    ],
)
def test_a_clone_with_no_instance_refuses_an_owned_issue_naming_the_owner(
    monkeypatch, capsys, claims, labels, owner
) -> None:
    rc, writes, github = _move_back(
        monkeypatch,
        "--to",
        "backlog",
        "--reason",
        "stalled",
        "--yes",
        instance=None,
        claims=claims,
        labels=labels,
    )
    assert rc == 1
    assert writes == [] and github.writes() == []
    err = capsys.readouterr().err
    assert (
        f"[refused] #42 does not move back: #42 is owned by {owner} of @me, and this clone "
        "takes no part in instance ownership, so it releases no claim (DEC-035 point 1)."
    ) in err
    assert "the issue never waits in backlog still claimed" in err
    assert "→ run this from the owner's clone, or once the owner released it." in err


def test_a_claim_another_account_made_refuses_before_the_guard_posts_anything(
    monkeypatch, capsys
) -> None:
    """A claim on the comment log counts only from its account (DEC-043 point
    3), so no clone of another account can release it: the move back refuses
    before the clash guard, and a bypass of the guard posts nothing."""
    rc, writes, github = _move_back(
        monkeypatch,
        "--to",
        "backlog",
        "--reason",
        "stalled",
        "--yes",
        "--bypass-owner",
        "her session is gone",
        assignee="alice",
        claims=((3, "alice"),),
    )
    assert rc == 1
    assert writes == [] and github.writes() == []
    err = capsys.readouterr().err
    assert (
        "#42 is owned by instance 3 of @alice, a claim on the comment log that only a clone "
        "of @alice can release (DEC-043 point 3)"
    ) in err
    assert "→ run this from a clone of @alice, or once that account's clone released it." in err
    assert "clash guard" not in err


def test_another_instance_of_this_account_is_released_once_the_guard_is_bypassed(
    monkeypatch, capsys
) -> None:
    """This clone can release a claim its own account made, so the clash guard
    decides: refused, and with a bypass the move back releases that owner."""
    common = ("--to", "backlog", "--reason", "stalled", "--yes")
    rc, writes, github = _move_back(monkeypatch, *common, claims=((3, "me"),))
    assert rc == 1
    assert writes == [] and github.writes() == []
    assert "#42 is owned by instance 3, and this clone is instance 2" in capsys.readouterr().err

    rc, writes, github = _move_back(
        monkeypatch, *common, "--bypass-owner", "its session is gone", claims=((3, "me"),)
    )
    assert rc == 0
    assert [w[0] for w in writes] == ["comment", "label", "journal"]
    assert _ownership_events(github) == ["claim 3", "release 3"]


def test_a_move_back_of_an_issue_that_cannot_be_read_is_refused(monkeypatch, capsys) -> None:
    rc, writes, _github = _move_back(
        monkeypatch, "--to", "backlog", "--reason", "stalled", "--yes", failing=("view",)
    )
    assert rc == 1
    assert writes == []
    err = capsys.readouterr().err
    assert "#42 could not be read, so whose it is cannot be told" in err
    assert "→ run this again once the issue can be read." in err


def test_where_the_board_carries_the_state_the_move_back_is_refused(monkeypatch, capsys) -> None:
    """The board's Status write for a board-carried state comes with #2271:
    until then the move back writes nothing, releases no claim and journals no
    move (DEC-006)."""
    rc, writes, github = _move_back(
        monkeypatch, "--to", "backlog", "--reason", "stalled", "--yes", board_carried=True
    )
    assert rc == 1
    assert writes == [] and github.calls == []
    err = capsys.readouterr().err
    assert "[refused] #42 does not move back here: the board carries its state" in err
    assert "comes with #2271 (pull request #2275)" in err
    assert "no claim was released and no move journaled" in err


def test_a_move_back_without_a_reason_is_refused_and_writes_nothing(monkeypatch, capsys) -> None:
    for argv in (("--yes",), ("--reason", "  ", "--yes")):
        rc, writes, github = _move_back(monkeypatch, "--to", "backlog", *argv)
        assert rc == 1
        assert writes == [] and github.writes() == []
        assert '--reason "<why the work stopped>"' in capsys.readouterr().err


def test_a_move_back_needs_the_persons_authorisation(monkeypatch, capsys) -> None:
    """Held by the user at hard-reject (DEC-006): with no terminal and no
    `--yes`, it is refused and nothing is written."""
    import io

    monkeypatch.setattr(sys, "stdin", io.StringIO())
    rc, writes, github = _move_back(monkeypatch, "--to", "backlog", "--reason", "stalled")
    assert rc == 1
    assert writes == [] and github.writes() == []
    assert "user-authorised" in capsys.readouterr().err


def test_a_move_back_lands_in_todo_where_the_issue_is_in_no_milestone(monkeypatch, capsys) -> None:
    rc, writes, _github = _move_back(
        monkeypatch, "--to", "backlog", "--reason", "stalled", "--yes", milestone=None
    )
    assert rc == 2
    assert writes == []
    err = capsys.readouterr().err
    assert "#42 moves back to todo, not backlog: it is in no Milestone" in err
    assert "--to todo" in err

    rc, writes, _github = _move_back(
        monkeypatch, "--to", "todo", "--reason", "stalled", "--yes", milestone=None
    )
    assert rc == 0
    assert writes[1] == ("label", 42, "state:todo", "state:in-progress")


def test_a_move_back_to_todo_of_an_issue_in_a_milestone_is_refused(monkeypatch, capsys) -> None:
    rc, writes, _github = _move_back(monkeypatch, "--to", "todo", "--reason", "stalled", "--yes")
    assert rc == 2
    assert writes == []
    err = capsys.readouterr().err
    assert "#42 moves back to backlog, not todo: it is in the Milestone 'Alpha'" in err


def test_a_container_with_a_child_in_progress_or_in_review_is_refused_naming_it(
    monkeypatch, capsys
) -> None:
    from tests.pm_composed_move_support import load_move_issue

    mi = load_move_issue()
    children = mi._Children(
        read=(_child(mi, 43, "in-progress"), _child(mi, 44, "review"), _child(mi, 45, "backlog"))
    )
    rc, writes, github = _move_back(
        monkeypatch,
        "--to",
        "backlog",
        "--reason",
        "stalled",
        "--yes",
        container=True,
        children=children,
    )
    assert rc == 1
    assert writes == [] and github.writes() == []
    err = capsys.readouterr().err
    assert "#43 is in-progress" in err and "#44 is review" in err
    assert "#45" not in err


def test_a_container_whose_children_cannot_be_told_is_refused(monkeypatch, capsys) -> None:
    from tests.pm_composed_move_support import load_move_issue

    mi = load_move_issue()
    abroad = mi.containment.ResolvedChild(
        7, mi.containment.ChildSubstrate.NATIVE, repository="o/other"
    )
    for children, said, again in (
        (
            mi._Children(incomplete="the issue list could not be read (gh failure)"),
            "its children could not be listed in full: the issue list could not be read",
            True,
        ),
        (
            mi._Children(untold=((_child(mi, 46, "")[0], "it could not be read"),)),
            "#46: it could not be read",
            True,
        ),
        (
            mi._Children(open_elsewhere=(abroad,)),
            "o/other#7 is open in o/other, where only open or closed is read, so it holds "
            "#42 until it closes.",
            False,
        ),
    ):
        rc, writes, _github = _move_back(
            monkeypatch,
            "--to",
            "backlog",
            "--reason",
            "stalled",
            "--yes",
            container=True,
            children=children,
        )
        assert rc == 1
        assert writes == []
        err = capsys.readouterr().err
        assert said in err
        # Reading again tells no more of an open child in another repository.
        assert ("run this again once every child can be read" in err) is again


def test_a_container_in_no_milestone_lands_in_backlog_over_a_child_in_backlog(
    monkeypatch, capsys
) -> None:
    """A container is never behind the work under it (DEC-006)."""
    from tests.pm_composed_move_support import load_move_issue

    mi = load_move_issue()
    children = mi._Children(read=(_child(mi, 45, "backlog"), _child(mi, 47, "done")))
    common = ("--reason", "stalled", "--yes")
    rc, writes, _github = _move_back(
        monkeypatch, "--to", "todo", *common, milestone=None, container=True, children=children
    )
    assert rc == 2
    assert writes == []
    assert "#42 moves back to backlog, not todo: its child #45 is in backlog" in (
        capsys.readouterr().err
    )
    rc, writes, _github = _move_back(
        monkeypatch, "--to", "backlog", *common, milestone=None, container=True, children=children
    )
    assert rc == 0
    assert writes[1] == ("label", 42, "state:backlog", "state:in-progress")


def test_reason_on_any_other_move_is_a_usage_error(monkeypatch, capsys) -> None:
    rc, writes, _github = _move_back(monkeypatch, "--to", "review", "--reason", "x", "--yes")
    assert rc == 2
    assert writes == []
    assert "--reason applies to a move back from in-progress only" in capsys.readouterr().err


def test_a_dry_run_of_a_move_back_writes_nothing_and_names_what_it_would(
    monkeypatch, capsys
) -> None:
    rc, writes, github = _move_back(
        monkeypatch, "--to", "backlog", "--reason", "stalled", "--dry-run", "--yes"
    )
    assert rc == 0
    assert writes == [] and github.writes() == []
    out = capsys.readouterr().out
    assert "reason:" in out and "stalled" in out
    assert "released on the move back (this clone is instance 2" in out


def test_at_projection_off_the_move_back_posts_no_comment_and_journals_its_reason(
    monkeypatch,
) -> None:
    rc, writes, _github = _move_back(
        monkeypatch, "--to", "backlog", "--reason", "stalled", "--yes", projection="off"
    )
    assert rc == 0
    assert [w[0] for w in writes] == ["label", "journal"]
    assert writes[1][4] == "move back: stalled"


# The children a container's move back reads, through the containment seam.


def _seam(mi, monkeypatch, *, rows, children, complete=True, records=None):
    containment = mi.containment
    corpus = containment.IssueCorpus(rows=tuple(rows), complete=True)
    monkeypatch.setattr(containment, "fetch_issue_corpus", lambda _config: corpus)
    resolution = containment.ChildResolution(
        children=tuple(children),
        native_supported=True,
        complete=complete,
        incomplete_reason=None if complete else "a native read failed",
    )
    monkeypatch.setattr(containment, "resolve_children", lambda _config, **_kw: resolution)
    monkeypatch.setattr(
        containment,
        "read_issue_record",
        lambda _config, *, issue_number, repository=None: (records or {})[issue_number],
    )


def test_read_children_reads_each_childs_state(mi, monkeypatch) -> None:
    containment = mi.containment
    here = containment.ChildSubstrate.NATIVE
    rows = [
        {
            "number": 43,
            "state": "OPEN",
            "labels": [{"name": "state:in-progress"}],
            "milestone": None,
        },
        {"number": 44, "state": "OPEN", "labels": [], "milestone": {"title": "Alpha"}},
        {"number": 45, "state": "CLOSED", "labels": [], "milestone": None},
        {"number": 46, "state": "OPEN", "labels": [{"name": "state:frozen"}], "milestone": None},
    ]
    abroad_open = containment.ResolvedChild(7, here, repository="o/other")
    abroad_closed = containment.ResolvedChild(8, here, repository="o/other")
    abroad_unread = containment.ResolvedChild(9, here, repository="o/other")
    records = {
        7: containment.IssueRecord(issue={"state": "OPEN"}, parent=None),
        8: containment.IssueRecord(issue={"state": "CLOSED"}, parent=None),
        9: containment.UnreadIssue("no access"),
    }
    children = [containment.ResolvedChild(n, here) for n in (43, 44, 45, 46, 48)]
    _seam(
        mi,
        monkeypatch,
        rows=rows,
        children=[*children, abroad_open, abroad_closed, abroad_unread],
        records=records,
    )
    read = mi._read_children(10, {}, None)
    assert [(c.number, s) for c, s in read.read] == [
        (43, "in-progress"),
        (44, "backlog"),
        (45, "done"),
    ]
    untold = {c.ref: why for c, why in read.untold}
    assert set(untold) == {"#46", "#48", "o/other#9"}
    assert "not among the issues the issue list returned" in untold["#48"]
    assert "no access" in untold["o/other#9"]
    # Open in another repository: read only as open or closed, so it is no
    # child that could not be read, and it holds the container until it closes.
    assert [c.ref for c in read.open_elsewhere] == ["o/other#7"]
    assert read.incomplete is None
    assert not read.told


def test_read_children_says_a_child_set_it_cannot_list_in_full(mi, monkeypatch) -> None:
    _seam(mi, monkeypatch, rows=[], children=[], complete=False)
    assert mi._read_children(10, {}, None).incomplete == "a native read failed"
    monkeypatch.setattr(mi.containment, "fetch_issue_corpus", lambda _config: None)
    assert "could not be read" in (mi._read_children(10, {}, None).incomplete or "")
