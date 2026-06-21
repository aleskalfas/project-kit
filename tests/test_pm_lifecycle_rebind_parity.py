"""Behaviour-parity tests for the issue-lifecycle rebind onto the process
substrate (DEC-032). Parity is the acceptance bar: the issue lifecycle must
behave identically after the rebind.

Coverage (DEC-032 Implications):
  (a) position truth-table — every (issue-state x milestone x labels) input
      resolves to the SAME state through the pre-rebind logic
      (move-issue `_infer_current_state`) and the rebound detectors, AND the
      detectors are mutually exclusive (exactly one matches), which is what
      makes the engine's first-matching-detection rule reproduce the old
      precedence regardless of state order;
  (b) transition legality + gate outcomes — the checkbox close-gate refuses an
      unticked body and passes a ticked one; the PR-merge gate is an
      authorisation artifact whose cross-authority the ENGINE computes
      (self-authored merge refuses; cross-authority merge passes);
  (d) parent in-progress inference is a pm-local descendant walk, not engine
      position.

The gh layer is stubbed; these tests exercise the pure inference + the
predicate contract, not the network.
"""

from __future__ import annotations

import importlib.util
import itertools
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
CAP_SCRIPTS = REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"
sys.path.insert(0, str(CAP_SCRIPTS))

from _lib import lifecycle_inference as infer  # noqa: E402
from _lib import lifecycle_predicates as predicates  # noqa: E402

ALL_STATES = ["todo", "backlog", "in-progress", "review", "done"]


# --- (a) position truth-table ---------------------------------------------


def _truth_table_inputs():
    """Every combination of (gh issue state, milestone presence, state:* label)
    that move-issue's `_infer_current_state` distinguishes."""
    gh_states = ["open", "closed"]
    milestones = [None, {}, {"title": "M1"}]
    label_sets = [
        [],
        ["type:feature"],
        ["state:todo"],
        ["state:backlog"],
        ["state:in-progress"],
        ["state:review"],
        ["state:done"],
        ["state:in-progress", "type:feature"],
        ["priority:High", "state:review"],
    ]
    return itertools.product(gh_states, milestones, label_sets)


def _pre_rebind_infer(state: str, milestone, labels: list[str]) -> str:
    """The pre-rebind precedence, transcribed from move-issue's original
    `_infer_current_state` (the parity baseline)."""
    if state == "closed":
        return "done"
    for lbl in labels:
        if lbl.startswith("state:"):
            return lbl.removeprefix("state:")
    if milestone:
        return "backlog"
    return "todo"


def test_position_truth_table_matches_pre_rebind() -> None:
    """The shared inference (which backs the detectors) equals the pre-rebind
    precedence for every input combination."""
    for gh_state, milestone, labels in _truth_table_inputs():
        expected = _pre_rebind_infer(gh_state, milestone, labels)
        actual = infer.infer_current_state(
            state=gh_state, milestone=milestone, labels=labels
        )
        assert actual == expected, (
            f"parity break: state={gh_state} milestone={milestone} labels={labels} "
            f"-> pre={expected} post={actual}"
        )


def test_detectors_are_mutually_exclusive(monkeypatch: pytest.MonkeyPatch) -> None:
    """For every truth-table input, EXACTLY ONE state detector returns
    result=True — so the engine's first-matching-detection is order-independent
    and reproduces the precedence."""
    for gh_state, milestone, labels in _truth_table_inputs():
        issue = {"state": gh_state, "milestone": milestone or {}, "labels": labels}
        _stub_fetch_issue(monkeypatch, issue)
        matches = [
            s for s in ALL_STATES if predicates.detect_state(1, s)["result"]
        ]
        expected = _pre_rebind_infer(gh_state, milestone, labels)
        assert matches == [expected], (
            f"detectors not exclusive for state={gh_state} milestone={milestone} "
            f"labels={labels}: matched {matches}, expected exactly [{expected!r}]"
        )


def test_detector_state_order_in_workflow_encodes_precedence() -> None:
    """The shipped workflow.yaml lists states done->...->todo so the engine's
    first-matching rule also encodes the closed->label->milestone->todo
    precedence (belt-and-suspenders alongside mutual exclusivity)."""
    from ruamel.yaml import YAML

    wf = YAML(typ="safe").load(
        (
            REPO_ROOT
            / ".pkit"
            / "capabilities"
            / "project-management"
            / "schemas"
            / "workflow.yaml"
        ).read_text(encoding="utf-8")
    )
    order = [s["id"] for s in wf["process"]["states"]]
    assert order == ["done", "review", "in-progress", "backlog", "todo"]


# --- (b) gate outcomes ----------------------------------------------------


def test_checkbox_gate_refuses_unticked(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_fetch_issue(
        monkeypatch, {"body": "## Acceptance\n- [ ] not done yet\n- [x] done"}
    )
    out = predicates.gate_checkboxes_ticked(1)
    assert out["result"] is False
    assert out["detail"]["unticked"]


def test_checkbox_gate_passes_ticked(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_fetch_issue(
        monkeypatch, {"body": "## Acceptance\n- [x] done\n- [x] also done"}
    )
    out = predicates.gate_checkboxes_ticked(1)
    assert out["result"] is True
    assert out["detail"]["unticked"] == []


def test_checkbox_gate_passes_when_no_checkboxes(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_fetch_issue(monkeypatch, {"body": "Plain prose, no checkboxes."})
    assert predicates.gate_checkboxes_ticked(1)["result"] is True


def test_pr_merge_gate_reports_facts_only(monkeypatch: pytest.MonkeyPatch) -> None:
    """The PR-merge gate returns {exists, produced_by} — it must NOT pre-decide
    `result` (the engine computes cross-authority, COR-031 P4)."""
    _stub_merged_pr(monkeypatch, {"number": 7, "merged_by": "reviewer-bob"})
    out = predicates.gate_pr_merged(1, actor="author-alice")
    assert out["exists"] is True
    assert out["produced_by"] == "reviewer-bob"
    assert "result" not in out  # the predicate does not decide; the engine does


def test_pr_merge_gate_absent_when_no_merged_pr(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_merged_pr(monkeypatch, None)
    out = predicates.gate_pr_merged(1, actor="anyone")
    assert out["exists"] is False
    assert out["produced_by"] is None


def test_pr_merge_cross_authority_via_engine() -> None:
    """The ENGINE's gate interpretation: a self-authored merge refuses; a
    different-authority merge passes — given the {exists, produced_by} the
    predicate reports."""
    from project_kit.process import PredicateRunner

    runner = PredicateRunner(
        capability="x", capability_dir=Path("/tmp"), repo_root=Path("/tmp"), subject="1"
    )

    # produced_by == actor -> refuse.
    runner._raw_cache[("gate-pr-merged", ())] = {
        "exists": True,
        "produced_by": "alice",
    }
    refused = runner.evaluate_gate(
        {"kind": "authorisation-artifact", "predicate": {"run": "gate-pr-merged"}},
        actor="alice",
    )
    assert refused.result is False

    # produced_by != actor -> pass.
    runner._raw_cache[("gate-pr-merged", ())] = {
        "exists": True,
        "produced_by": "bob",
    }
    passed = runner.evaluate_gate(
        {"kind": "authorisation-artifact", "predicate": {"run": "gate-pr-merged"}},
        actor="alice",
    )
    assert passed.result is True


# --- (d) parent in-progress is a pm-local descendant walk -----------------


def test_parent_active_descendant_walks_children(monkeypatch: pytest.MonkeyPatch) -> None:
    """A parent has an active descendant when a child naming it is in-progress
    or further. This is pm-LOCAL (never the engine's position)."""
    children = [
        # names #10 as parent, in-progress -> active.
        {
            "number": 11,
            "body": "Feature: #10\n\n## What\nx",
            "state": "open",
            "milestone": {},
            "labels": ["state:in-progress"],
        },
        # names #10, only backlog -> not active.
        {
            "number": 12,
            "body": "Feature: #10\n",
            "state": "open",
            "milestone": {"title": "M1"},
            "labels": [],
        },
        # names a different parent -> ignored.
        {
            "number": 13,
            "body": "Feature: #99\n",
            "state": "open",
            "milestone": {},
            "labels": ["state:done"],
        },
    ]
    _stub_list_issues(monkeypatch, children)
    out = predicates.parent_has_active_descendant(10)
    assert out["result"] is True
    assert out["detail"]["active_descendants"] == [11]


def test_parent_no_active_descendant(monkeypatch: pytest.MonkeyPatch) -> None:
    children = [
        {
            "number": 11,
            "body": "Feature: #10\n",
            "state": "open",
            "milestone": {"title": "M1"},
            "labels": ["state:backlog"],
        },
    ]
    _stub_list_issues(monkeypatch, children)
    assert predicates.parent_has_active_descendant(10)["result"] is False


def test_parent_walk_does_not_affect_position(monkeypatch: pytest.MonkeyPatch) -> None:
    """The descendant walk must NOT change a parent's resolved position: a
    parent with no state:* label and an in-progress child still infers per the
    label/milestone precedence (todo/backlog), not in-progress."""
    # Position inference ignores descendants entirely (it is label/milestone-only).
    assert (
        infer.infer_current_state(state="open", milestone={}, labels=[]) == "todo"
    )
    assert (
        infer.infer_current_state(
            state="open", milestone={"title": "M1"}, labels=[]
        )
        == "backlog"
    )


# --- fail-closed: an unevaluable predicate is indeterminate ---------------


def test_detector_gh_failure_is_indeterminate(monkeypatch: pytest.MonkeyPatch) -> None:
    """A gh failure must mark the detector INDETERMINATE (fail-closed), not a
    clean result=False — a 'couldn't tell' must never look like a 'no'."""
    monkeypatch.setattr(predicates, "_capability_root", lambda: REPO_ROOT)
    monkeypatch.setattr(predicates, "_config", lambda _root: {})
    monkeypatch.setattr(predicates, "_fetch_issue", lambda _n, _c, _f: None)
    out = predicates.detect_state(1, "todo")
    assert out[predicates.INDETERMINATE_KEY] is True
    assert out["result"] is False


def test_checkbox_gate_gh_failure_is_indeterminate(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(predicates, "_capability_root", lambda: REPO_ROOT)
    monkeypatch.setattr(predicates, "_config", lambda _root: {})
    monkeypatch.setattr(predicates, "_fetch_issue", lambda _n, _c, _f: None)
    out = predicates.gate_checkboxes_ticked(1)
    assert out[predicates.INDETERMINATE_KEY] is True


def test_pr_merge_gate_gh_failure_is_indeterminate(monkeypatch: pytest.MonkeyPatch) -> None:
    """A failed PR query is indeterminate; only a confident 'no merged PR' is a
    clean exists=False."""
    monkeypatch.setattr(predicates, "_capability_root", lambda: REPO_ROOT)
    monkeypatch.setattr(predicates, "_config", lambda _root: {})
    monkeypatch.setattr(
        predicates, "_find_merged_pr_for_issue", lambda _n, _c: predicates._GH_ERROR
    )
    out = predicates.gate_pr_merged(1, actor="x")
    assert out[predicates.INDETERMINATE_KEY] is True


# --- pagination ceiling -> indeterminate (fail-closed) --------------------


def _completed(stdout: str):
    import subprocess

    return subprocess.CompletedProcess(["gh"], 0, stdout=stdout, stderr="")


def test_parent_walk_indeterminate_when_issue_list_hits_ceiling(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A full page of issues means there may be unseen rows -> the descendant
    walk is indeterminate (fail-closed), not a confident 'no active descendant'.
    """
    import json

    monkeypatch.setattr(predicates, "_capability_root", lambda: REPO_ROOT)
    monkeypatch.setattr(predicates, "_config", lambda _root: {})
    full_page = [
        {"number": n, "body": "", "state": "open", "labels": [], "milestone": {}}
        for n in range(predicates._OPEN_ISSUES_LIMIT)
    ]
    monkeypatch.setattr(
        predicates, "gh_run", lambda *a, **k: _completed(json.dumps(full_page))
    )
    out = predicates.parent_has_active_descendant(10)
    assert out[predicates.INDETERMINATE_KEY] is True
    assert "ceiling" in out["reason"]


def test_pr_merge_gate_indeterminate_when_pr_list_hits_ceiling(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A full page of merged PRs with no match means an unseen merged PR may
    exist -> indeterminate (fail-closed), not a confident exists=False."""
    import json

    monkeypatch.setattr(predicates, "_capability_root", lambda: REPO_ROOT)
    monkeypatch.setattr(predicates, "_config", lambda _root: {})
    # A full page, none of which closes issue #1.
    full_page = [
        {"number": n, "body": "unrelated", "mergedBy": {"login": "someone"}}
        for n in range(predicates._MERGED_PRS_LIMIT)
    ]
    monkeypatch.setattr(
        predicates, "gh_run", lambda *a, **k: _completed(json.dumps(full_page))
    )
    out = predicates.gate_pr_merged(1, actor="x")
    assert out[predicates.INDETERMINATE_KEY] is True


def test_pr_merge_gate_finds_match_even_at_ceiling(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A match within a full page is still a confident hit — the ceiling only
    matters when NO match was found in the fetched page."""
    import json

    monkeypatch.setattr(predicates, "_capability_root", lambda: REPO_ROOT)
    monkeypatch.setattr(predicates, "_config", lambda _root: {})
    page = [
        {"number": n, "body": "unrelated", "mergedBy": {"login": "someone"}}
        for n in range(predicates._MERGED_PRS_LIMIT - 1)
    ]
    page.append(
        {"number": 999, "body": "Closes #1", "mergedBy": {"login": "reviewer-bob"}}
    )
    monkeypatch.setattr(
        predicates, "gh_run", lambda *a, **k: _completed(json.dumps(page))
    )
    out = predicates.gate_pr_merged(1, actor="author-alice")
    assert predicates.INDETERMINATE_KEY not in out
    assert out["exists"] is True
    assert out["produced_by"] == "reviewer-bob"


# --- stubs ----------------------------------------------------------------


def _stub_fetch_issue(monkeypatch: pytest.MonkeyPatch, issue: dict) -> None:
    monkeypatch.setattr(predicates, "_capability_root", lambda: REPO_ROOT)
    monkeypatch.setattr(predicates, "_config", lambda _root: {})
    monkeypatch.setattr(predicates, "_fetch_issue", lambda _n, _c, _f: issue)


def _stub_list_issues(monkeypatch: pytest.MonkeyPatch, issues: list[dict]) -> None:
    monkeypatch.setattr(predicates, "_capability_root", lambda: REPO_ROOT)
    monkeypatch.setattr(predicates, "_config", lambda _root: {})
    monkeypatch.setattr(predicates, "_list_open_issues", lambda _c: issues)


def _stub_merged_pr(monkeypatch: pytest.MonkeyPatch, pr: dict | None) -> None:
    monkeypatch.setattr(predicates, "_capability_root", lambda: REPO_ROOT)
    monkeypatch.setattr(predicates, "_config", lambda _root: {})
    monkeypatch.setattr(predicates, "_find_merged_pr_for_issue", lambda _n, _c: pr)
