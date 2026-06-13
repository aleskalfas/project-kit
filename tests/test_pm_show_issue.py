"""Tests for project-management's show-issue script's pure logic.

Covers the summary builder, structural-type inference, first-body-line
extraction, required-section status check.
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
