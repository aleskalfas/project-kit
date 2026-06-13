"""Tests for the DEC-019 mandatory-issue-state surface.

Covers validate-issue's new schema-driven severity handling for the
assignment + board-membership checks.
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
    / "validate-issue.py"
)


@pytest.fixture(scope="module")
def vi():
    module_name = "pm_validate_issue_under_test_mandatory"
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
            "task": {
                "title_prefix": "Task",
                "title_case": "title",
                "parent_issue_types": ["feature", "umbrella", "epic"],
                "parent_ref_optional": False,
                "parent_ref_form": "Feature: #<N>",
            },
        },
    }


@pytest.fixture
def titles() -> dict:
    return {"formats": {"issue-task": {"pattern": r"^\[Task\] .+$"}}}


@pytest.fixture
def body_format() -> dict:
    return {
        "bodies": {
            "task": {
                "required_sections": [
                    {"heading": "## What", "severity": "[validation-severity:hard-reject]"},
                    {"heading": "## Acceptance criteria", "severity": "[validation-severity:hard-reject]"},
                    {"heading": "## Doc impact", "severity": "[validation-severity:hard-reject]"},
                ],
            },
        },
    }


@pytest.fixture
def label_fallback_config() -> dict:
    return {"has_projects_v2_board": False, "workstreams": ["cli"]}


@pytest.fixture
def board_config() -> dict:
    return {"has_projects_v2_board": True, "projects_v2_board_id": 42}


@pytest.fixture
def mandatory_state() -> dict:
    return {
        "schema_version": 1,
        "required_fields": {
            "assignee": {
                "missing_severity": "[validation-severity:hard-reject]",
                "drift_severity": "[validation-severity:warning]",
            },
            "board_membership": {
                "applies_when": "config.has_projects_v2_board == true",
                "missing_severity": "[validation-severity:hard-reject]",
                "drift_severity": "[validation-severity:warning]",
            },
        },
    }


def _make_issue(*, body: str, labels=None, assignees=None, project_items=None) -> dict:
    return {
        "title": "[Task] Install the Claude Code CLI inside the sandbox",
        "body": body,
        "labels": [{"name": l} for l in (labels or ["type:feature", "priority:Medium", "workstream:cli"])],
        "assignees": assignees if assignees is not None else [{"login": "alice"}],
        **({"projectItems": project_items} if project_items is not None else {}),
    }


def _labels_of(findings):
    return [f.label for f in findings]


# --- mandatory_state plumbing -----------------------------------------


def test_validate_issue_accepts_mandatory_state_param(
    vi, issue_types, titles, body_format, label_fallback_config, mandatory_state
) -> None:
    """Signature change: mandatory_state is now a recognised kwarg."""
    issue = _make_issue(
        body=(
            "Feature: #1\n\n## What\nx\n## Acceptance criteria\n- [ ] x\n## Doc impact\nnone."
        )
    )
    findings = vi._validate_issue(
        issue=issue,
        issue_types=issue_types,
        titles=titles,
        body_format=body_format,
        config=label_fallback_config,
        mandatory_state=mandatory_state,
    )
    # Properly-formed issue with assignee → no mandatory-state findings.
    assert "assignment.missing" not in _labels_of(findings)
    assert "board_membership.missing" not in _labels_of(findings)


def test_validate_uses_schema_severity_for_missing_assignee(
    vi, issue_types, titles, body_format, label_fallback_config, mandatory_state
) -> None:
    """drift_severity (warning) applies on an existing-issue check."""
    issue = _make_issue(
        body=(
            "Feature: #1\n\n## What\nx\n## Acceptance criteria\n- [ ] x\n## Doc impact\nnone."
        ),
        assignees=[],
    )
    findings = vi._validate_issue(
        issue=issue,
        issue_types=issue_types,
        titles=titles,
        body_format=body_format,
        config=label_fallback_config,
        mandatory_state=mandatory_state,
    )
    assignment_findings = [f for f in findings if f.label == "assignment.missing"]
    assert len(assignment_findings) == 1
    assert assignment_findings[0].severity == "warning"


# --- board-membership drift -------------------------------------------


def test_board_membership_drift_warning_for_board_adopter(
    vi, issue_types, titles, body_format, board_config, mandatory_state
) -> None:
    """Open board-mode issue with empty projectItems → warning drift."""
    issue = _make_issue(
        body=(
            "Feature: #1\n\n## What\nx\n## Acceptance criteria\n- [ ] x\n## Doc impact\nnone."
        ),
        labels=["type:feature"],
        project_items=[],
    )
    findings = vi._validate_issue(
        issue=issue,
        issue_types=issue_types,
        titles=titles,
        body_format=body_format,
        config=board_config,
        mandatory_state=mandatory_state,
    )
    board_findings = [f for f in findings if f.label == "board_membership.missing"]
    assert len(board_findings) == 1
    assert board_findings[0].severity == "warning"


def test_board_membership_skipped_for_label_substrate(
    vi, issue_types, titles, body_format, label_fallback_config, mandatory_state
) -> None:
    """Label-fallback adopters never trigger board-membership findings."""
    issue = _make_issue(
        body=(
            "Feature: #1\n\n## What\nx\n## Acceptance criteria\n- [ ] x\n## Doc impact\nnone."
        ),
        project_items=[],
    )
    findings = vi._validate_issue(
        issue=issue,
        issue_types=issue_types,
        titles=titles,
        body_format=body_format,
        config=label_fallback_config,
        mandatory_state=mandatory_state,
    )
    assert "board_membership.missing" not in _labels_of(findings)


def test_board_membership_skipped_when_projectitems_absent(
    vi, issue_types, titles, body_format, board_config, mandatory_state
) -> None:
    """Without projectItems in the gh response, we don't fabricate a finding."""
    issue = _make_issue(
        body=(
            "Feature: #1\n\n## What\nx\n## Acceptance criteria\n- [ ] x\n## Doc impact\nnone."
        ),
        labels=["type:feature"],
        project_items=None,  # omitted entirely
    )
    findings = vi._validate_issue(
        issue=issue,
        issue_types=issue_types,
        titles=titles,
        body_format=body_format,
        config=board_config,
        mandatory_state=mandatory_state,
    )
    assert "board_membership.missing" not in _labels_of(findings)


def test_board_membership_no_finding_when_present(
    vi, issue_types, titles, body_format, board_config, mandatory_state
) -> None:
    """projectItems with at least one entry → no drift."""
    issue = _make_issue(
        body=(
            "Feature: #1\n\n## What\nx\n## Acceptance criteria\n- [ ] x\n## Doc impact\nnone."
        ),
        labels=["type:feature"],
        project_items=[{"id": "PVTI_xyz"}],
    )
    findings = vi._validate_issue(
        issue=issue,
        issue_types=issue_types,
        titles=titles,
        body_format=body_format,
        config=board_config,
        mandatory_state=mandatory_state,
    )
    assert "board_membership.missing" not in _labels_of(findings)


# --- absent mandatory_state falls back to warning ---------------------


def test_missing_mandatory_state_param_still_warns_on_missing_assignee(
    vi, issue_types, titles, body_format, label_fallback_config
) -> None:
    """Backward-compat: when mandatory_state isn't passed, defaults apply."""
    issue = _make_issue(
        body=(
            "Feature: #1\n\n## What\nx\n## Acceptance criteria\n- [ ] x\n## Doc impact\nnone."
        ),
        assignees=[],
    )
    findings = vi._validate_issue(
        issue=issue,
        issue_types=issue_types,
        titles=titles,
        body_format=body_format,
        config=label_fallback_config,
    )
    assignment_findings = [f for f in findings if f.label == "assignment.missing"]
    assert len(assignment_findings) == 1
    assert assignment_findings[0].severity == "warning"
