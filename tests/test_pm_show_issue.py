"""Tests for project-management's show-issue script's pure logic.

Covers the summary builder, structural-type inference, first-body-line
extraction, required-section status check.
"""

from __future__ import annotations

import importlib.util
import subprocess
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
    / "show-issue.py"
)


@pytest.fixture(scope="module")
def si():
    """Load show-issue.py as a module via importlib."""
    module_name = "pm_show_issue_under_test"
    spec = importlib.util.spec_from_file_location(module_name, SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


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
def body_format() -> dict:
    return {
        "bodies": {
            "task": {
                "required_sections": [
                    {"heading": "## What"},
                    {"heading": "## Acceptance criteria"},
                    {"heading": "## Doc impact"},
                ],
            },
        },
    }


# --- structural type inference ---------------------------------------


def test_infer_returns_epic_for_uppercase_prefix(si, issue_types) -> None:
    assert si._infer_structural_type("[EPIC] x", issue_types) == "epic"


def test_infer_returns_task_for_title_prefix(si, issue_types) -> None:
    assert si._infer_structural_type("[Task] x", issue_types) == "task"


def test_infer_returns_none_for_unrecognised_prefix(si, issue_types) -> None:
    assert si._infer_structural_type("Plain title", issue_types) is None


# --- first body line --------------------------------------------------


def test_first_body_line_extracts_parent_ref(si) -> None:
    body = "Feature: #42\n\n## What\nfoo"
    assert si._first_body_line(body) == "Feature: #42"


def test_first_body_line_empty_for_empty_body(si) -> None:
    assert si._first_body_line("") == ""
    assert si._first_body_line("   \n\n  ") == ""


def test_first_body_line_skips_leading_whitespace(si) -> None:
    body = "\n\n   Feature: #5\nrest"
    assert si._first_body_line(body) == "Feature: #5"


# --- required-section status -----------------------------------------


def test_required_sections_all_present(si, body_format) -> None:
    body = "## What\nfoo\n## Acceptance criteria\n- [ ] x\n## Doc impact\nnone"
    statuses = si._required_section_status("task", body, body_format)
    assert all(s["present"] for s in statuses)
    assert len(statuses) == 3


def test_required_sections_one_missing(si, body_format) -> None:
    body = "## What\nfoo\n## Acceptance criteria\n- [ ] x\n"  # no Doc impact
    statuses = si._required_section_status("task", body, body_format)
    present_map = {s["heading"]: s["present"] for s in statuses}
    assert present_map["## What"] is True
    assert present_map["## Acceptance criteria"] is True
    assert present_map["## Doc impact"] is False


def test_required_sections_returns_empty_for_unknown_type(si, body_format) -> None:
    statuses = si._required_section_status("unknown", "any body", body_format)
    assert statuses == []


def test_required_sections_returns_empty_when_type_is_none(si, body_format) -> None:
    statuses = si._required_section_status(None, "any body", body_format)
    assert statuses == []


# --- summary ----------------------------------------------------------


def test_summarise_picks_up_classification_labels(si, issue_types, body_format) -> None:
    issue = {
        "title": "[Task] Install the Claude Code CLI inside the sandbox",
        "body": "Feature: #1\n\n## What\nx\n## Acceptance criteria\n- [ ] x\n## Doc impact\nnone.",
        "labels": [
            {"name": "type:feature"},
            {"name": "priority:Medium"},
            {"name": "workstream:cli"},
            {"name": "good first issue"},  # other label
        ],
        "assignees": [{"login": "alice"}],
        "state": "OPEN",
        "milestone": {"title": "M1 — CLI walkthrough"},
        "url": "https://github.com/owner/repo/issues/42",
    }
    summary = si._summarise(issue, issue_types, body_format)
    assert summary["structural_type"] == "task"
    assert summary["state"] == "open"
    assert summary["assignees"] == ["alice"]
    assert summary["milestone"] == "M1 — CLI walkthrough"
    assert summary["parent_ref"] == "Feature: #1"
    assert summary["classification"]["type"] == ["type:feature"]
    assert summary["classification"]["priority"] == ["priority:Medium"]
    assert summary["classification"]["workstream"] == ["workstream:cli"]
    assert summary["other_labels"] == ["good first issue"]
    assert summary["url"] == "https://github.com/owner/repo/issues/42"
    # Required-sections summary present for inferred task.
    assert len(summary["required_sections"]) == 3
    assert all(s["present"] for s in summary["required_sections"])


def test_summarise_handles_no_assignees(si, issue_types, body_format) -> None:
    issue = {
        "title": "[Task] short title",
        "body": "Feature: #1",
        "labels": [],
        "assignees": [],
        "state": "OPEN",
    }
    summary = si._summarise(issue, issue_types, body_format)
    assert summary["assignees"] == []
    assert summary["classification"]["type"] == []


# --- acceptance-criteria extraction ----------------------------------


def test_extract_criteria_pulls_checkbox_items(si) -> None:
    body = (
        "Feature: #1\n\n## What\nbuild it\n\n"
        "## Acceptance criteria\n"
        "- [ ] first criterion\n"
        "- [x] second criterion\n\n"
        "## Doc impact\n- update README\n"
    )
    # Collection starts at the heading and stops at the next level-2 heading,
    # so the Doc-impact bullet is not pulled in.
    assert si._extract_criteria(body) == ["first criterion", "second criterion"]


def test_extract_criteria_skips_bare_skeleton_item(si) -> None:
    body = "## Acceptance criteria\n- [ ]\n- [ ] real one\n"
    assert si._extract_criteria(body) == ["real one"]


def test_extract_criteria_empty_when_section_absent(si) -> None:
    assert si._extract_criteria("## What\n- not criteria\n") == []


# --- --field projection ----------------------------------------------


@pytest.fixture
def sample_summary(si, issue_types, body_format) -> dict:
    issue = {
        "title": "[Task] Install the Claude Code CLI inside the sandbox",
        "body": (
            "Feature: #1\n\n## What\nx\n"
            "## Acceptance criteria\n- [ ] alpha\n- [ ] beta\n"
            "## Doc impact\nnone."
        ),
        "labels": [
            {"name": "type:feature"},
            {"name": "priority:Medium"},
            {"name": "workstream:cli"},
            {"name": "good first issue"},
        ],
        "assignees": [{"login": "alice"}],
        "state": "OPEN",
        "url": "https://github.com/owner/repo/issues/42",
    }
    return si._summarise(issue, issue_types, body_format)


def test_field_names_match_resolver_keys(si, sample_summary) -> None:
    # The documented vocabulary must stay in lock-step with what the resolver
    # actually projects, in order.
    assert tuple(si._field_lines_for(sample_summary)) == si.ISSUE_FIELD_NAMES


def test_field_scalar_is_bare_value(si, sample_summary) -> None:
    fields = si._field_lines_for(sample_summary)
    # A scalar field renders as exactly one bare line: no banner, no label.
    assert fields["state"] == ["open"]
    assert fields["title"] == [
        "[Task] Install the Claude Code CLI inside the sandbox"
    ]
    # No chrome: the value line carries no "issue #" banner or "  state:" label.
    for line in fields["state"]:
        assert "issue #" not in line
        assert "state:" not in line


def test_field_list_is_one_item_per_line(si, sample_summary) -> None:
    assert si._field_lines_for(sample_summary)["criteria"] == ["alpha", "beta"]


def test_field_priority_projects_axis_label(si, sample_summary) -> None:
    assert si._field_lines_for(sample_summary)["priority"] == ["priority:Medium"]


def test_field_absent_scalar_renders_no_lines(si, issue_types, body_format) -> None:
    summary = si._summarise(
        {"title": "[Task] x", "body": "Feature: #1", "state": "OPEN"},
        issue_types,
        body_format,
    )
    # No milestone in the issue -> the field yields no output (not a blank line).
    assert summary["milestone"] is None
    assert si._field_lines_for(summary)["milestone"] == []


def test_unknown_field_exits_nonzero_and_lists_valid_fields() -> None:
    # Field validation happens right after parse_args, before any gh/network,
    # so this runs offline.
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "1", "--field", "not-a-field"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode != 0
    assert "unknown field" in result.stderr.lower()
    # The error must list the valid vocabulary so the caller can self-correct.
    assert "criteria" in result.stderr
    assert "state" in result.stderr


def test_field_and_json_are_mutually_exclusive() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "1", "--field", "state", "--json"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode != 0
    assert "not allowed with" in result.stderr.lower()
