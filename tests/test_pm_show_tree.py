"""Tests for project-management's show-tree script's pure logic.

Covers parent-ref extraction, parent linkage, issue parsing, PR
parsing, orphan detection.
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
    / "show-tree.py"
)


@pytest.fixture(scope="module")
def st():
    module_name = "pm_show_tree_under_test"
    spec = importlib.util.spec_from_file_location(module_name, SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _link_parents_textual_only(st, issues, monkeypatch) -> None:
    """Run `_link_parents` with the native `…/sub_issues` read stubbed to
    unsupported (None) → textual-only resolution through the containment seam.

    show-tree no longer parses body parent-refs directly; it routes child
    building through `_lib.containment.resolve_children` (ADR-026). These linkage
    tests assert the TEXTUAL projection, so the native side is stubbed off; the
    native-wins / mixed-mode behaviour is proven in the read-seam test.
    """
    monkeypatch.setattr(
        st.containment,
        "read_native_child_numbers",
        lambda _config, *, parent_number: None,
    )
    st._link_parents(issues, {})


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


# --- candidate-parent pre-scan ref recognition -----------------------
# show-tree's direct body-ref parser is gone; the seam owns authoritative
# resolution. `_first_parent_ref` survives only to BOUND which parents get a
# native read (it never decides the rendered child set) — same recognition.


def test_first_parent_ref_simple(st) -> None:
    body = "Feature: #42\n\n## What\nfoo"
    assert st._first_parent_ref(body) == 42


def test_first_parent_ref_epic_form(st) -> None:
    body = "EPIC: #99\n\nbody"
    assert st._first_parent_ref(body) == 99


def test_first_parent_ref_returns_none_when_no_ref(st) -> None:
    body = "## What\nplain body."
    assert st._first_parent_ref(body) is None


def test_first_parent_ref_empty_body(st) -> None:
    assert st._first_parent_ref("") is None


def test_first_parent_ref_skips_leading_whitespace(st) -> None:
    body = "\n\n   EPIC: #5\nbody"
    assert st._first_parent_ref(body) == 5


# --- structural type inference ---------------------------------------


def test_infer_recognises_each_prefix(st, issue_types) -> None:
    assert st._infer_structural_type("[EPIC] x", issue_types) == "epic"
    assert st._infer_structural_type("[Feature] y", issue_types) == "feature"
    assert st._infer_structural_type("[Umbrella] z", issue_types) == "umbrella"
    assert st._infer_structural_type("[Task] w", issue_types) == "task"


def test_infer_none_for_unknown_prefix(st, issue_types) -> None:
    assert st._infer_structural_type("plain", issue_types) is None


# --- issue parsing ---------------------------------------------------


def test_parse_issues_extracts_basic_fields(st, issue_types) -> None:
    raw = [
        {
            "number": 42,
            "title": "[Task] do thing",
            "body": "Feature: #1\n\n## What\nfoo",
            "state": "OPEN",
            "labels": [{"name": "type:feature"}, {"name": "priority:Medium"}],
            "milestone": {"title": "M1"},
        }
    ]
    issues = st._parse_issues(raw, issue_types)
    assert 42 in issues
    issue = issues[42]
    assert issue.title == "[Task] do thing"
    assert issue.state == "open"
    assert issue.structural_type == "task"
    assert "type:feature" in issue.labels
    assert issue.milestone == "M1"


def test_parse_issues_handles_missing_milestone(st, issue_types) -> None:
    raw = [{"number": 1, "title": "[Task] x", "body": "", "state": "OPEN", "labels": []}]
    issues = st._parse_issues(raw, issue_types)
    assert issues[1].milestone is None


def test_parse_issues_skips_malformed(st, issue_types) -> None:
    raw = ["string", 42, {"title": "no number"}, {"number": 1, "title": "ok", "state": "OPEN"}]
    issues = st._parse_issues(raw, issue_types)
    assert 1 in issues
    assert len(issues) == 1


# --- PR parsing ------------------------------------------------------


def test_parse_prs_extracts_closes(st) -> None:
    raw = [{"number": 99, "title": "feat: x", "state": "OPEN", "body": "Closes #42"}]
    prs = st._parse_prs(raw)
    assert prs[99].closes == [42]


def test_parse_prs_extracts_multiple_closes(st) -> None:
    raw = [
        {
            "number": 99,
            "title": "feat: x",
            "state": "OPEN",
            "body": "Closes #1, fixes #2\nResolves #3",
        }
    ]
    prs = st._parse_prs(raw)
    assert prs[99].closes == [1, 2, 3]


def test_parse_prs_empty_closes_when_no_keyword(st) -> None:
    raw = [{"number": 99, "title": "x", "state": "OPEN", "body": "no keyword"}]
    prs = st._parse_prs(raw)
    assert prs[99].closes == []


# --- parent linking --------------------------------------------------


def test_link_parents_sets_relationships(st, issue_types, monkeypatch) -> None:
    raw = [
        {
            "number": 1,
            "title": "[EPIC] thing",
            "body": "Milestone: #M1",
            "state": "OPEN",
            "labels": [],
        },
        {
            "number": 2,
            "title": "[Feature] sub-feature",
            "body": "EPIC: #1\n",
            "state": "OPEN",
            "labels": [],
        },
        {
            "number": 3,
            "title": "[Task] do thing",
            "body": "Feature: #2\n",
            "state": "OPEN",
            "labels": [],
        },
    ]
    issues = st._parse_issues(raw, issue_types)
    _link_parents_textual_only(st, issues, monkeypatch)
    assert issues[3].parent_number == 2
    assert issues[2].parent_number == 1
    # EPIC ref to Milestone: parent is M1 (not a real issue number); we
    # try to parse but EPIC's parent_ref says "Milestone: #M1" which
    # won't match the digits regex, so parent stays None.
    assert issues[1].parent_number is None
    assert 3 in issues[2].children
    assert 2 in issues[1].children


def test_link_parents_handles_missing_parent_target(st, issue_types, monkeypatch) -> None:
    """Parent ref that doesn't resolve in the loaded set stays unlinked."""
    raw = [
        {
            "number": 5,
            "title": "[Task] x",
            "body": "Feature: #999\n",
            "state": "OPEN",
            "labels": [],
        }
    ]
    issues = st._parse_issues(raw, issue_types)
    _link_parents_textual_only(st, issues, monkeypatch)
    assert issues[5].parent_number is None


# --- orphan detection ------------------------------------------------


def test_orphan_task_with_no_parent_ref(st, issue_types, monkeypatch) -> None:
    raw = [
        {
            "number": 1,
            "title": "[Task] orphan",
            "body": "## What\nno parent ref",
            "state": "OPEN",
            "labels": [],
        }
    ]
    issues = st._parse_issues(raw, issue_types)
    _link_parents_textual_only(st, issues, monkeypatch)
    orphans = st._detect_orphans(issues, {})
    assert 1 in orphans["open_issues_with_no_parent_ref"]


def test_epic_with_no_parent_is_not_orphan(st, issue_types, monkeypatch) -> None:
    """EPICs legitimately have no parent (parent_ref_optional)."""
    raw = [
        {
            "number": 1,
            "title": "[EPIC] thing",
            "body": "## Outcome\nfoo",
            "state": "OPEN",
            "labels": [],
        }
    ]
    issues = st._parse_issues(raw, issue_types)
    _link_parents_textual_only(st, issues, monkeypatch)
    orphans = st._detect_orphans(issues, {})
    assert 1 not in orphans["open_issues_with_no_parent_ref"]


def test_orphan_pr_without_matching_closing_issue(st, issue_types) -> None:
    issues = st._parse_issues([], issue_types)
    prs = st._parse_prs(
        [{"number": 99, "title": "x", "state": "OPEN", "body": "Closes #42"}]
    )
    orphans = st._detect_orphans(issues, prs)
    assert 99 in orphans["prs_without_closing_issue_in_repo"]


def test_pr_with_matching_closing_issue_not_orphan(st, issue_types) -> None:
    raw_issues = [
        {
            "number": 42,
            "title": "[Task] x",
            "body": "Feature: #1\n",
            "state": "OPEN",
            "labels": [],
        }
    ]
    issues = st._parse_issues(raw_issues, issue_types)
    prs = st._parse_prs(
        [{"number": 99, "title": "y", "state": "OPEN", "body": "Closes #42"}]
    )
    orphans = st._detect_orphans(issues, prs)
    assert 99 not in orphans["prs_without_closing_issue_in_repo"]


def test_closed_issues_not_counted_as_orphans(st, issue_types, monkeypatch) -> None:
    raw = [
        {
            "number": 1,
            "title": "[Task] x",
            "body": "## What\nno parent ref",
            "state": "CLOSED",
            "labels": [],
        }
    ]
    issues = st._parse_issues(raw, issue_types)
    _link_parents_textual_only(st, issues, monkeypatch)
    orphans = st._detect_orphans(issues, {})
    assert 1 not in orphans["open_issues_with_no_parent_ref"]
