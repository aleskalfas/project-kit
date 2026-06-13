"""Tests for project-management's edit-issue script's pure logic.

Covers body computation (replace / append / file / stdin), validation
findings, structural-type inference, title-pattern matching.
"""

from __future__ import annotations

import argparse
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
    / "edit-issue.py"
)


@pytest.fixture(scope="module")
def ei():
    module_name = "pm_edit_issue_under_test"
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
            "epic": {
                "title_prefix": "EPIC",
                "title_case": "upper",
                "parent_issue_types": [],
                "parent_ref_optional": True,
                "parent_ref_form": "Milestone: #<N>",
            },
            "feature": {
                "title_prefix": "Feature",
                "title_case": "title",
                "parent_issue_types": ["epic"],
                "parent_ref_optional": False,
                "parent_ref_form": "EPIC: #<N>",
            },
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
    return {
        "formats": {
            "issue-epic": {"pattern": r"^\[EPIC\] .+$"},
            "issue-feature": {"pattern": r"^\[Feature\] .+$"},
            "issue-task": {"pattern": r"^\[Task\] .+$"},
        },
    }


@pytest.fixture
def body_format() -> dict:
    return {
        "bodies": {
            "task": {
                "required_sections": [
                    {
                        "heading": "## What",
                        "severity": "[validation-severity:hard-reject]",
                    },
                    {
                        "heading": "## Acceptance criteria",
                        "severity": "[validation-severity:hard-reject]",
                    },
                    {
                        "heading": "## Doc impact",
                        "severity": "[validation-severity:hard-reject]",
                    },
                ],
            },
        },
    }


# --- body computation ------------------------------------------------


def test_compute_new_body_with_body_arg(ei) -> None:
    args = argparse.Namespace(body="replacement", body_file=None, append=None)
    assert ei._compute_new_body("old", args) == "replacement"


def test_compute_new_body_with_body_file(ei, tmp_path) -> None:
    f = tmp_path / "body.md"
    f.write_text("from file", encoding="utf-8")
    args = argparse.Namespace(body=None, body_file=f, append=None)
    assert ei._compute_new_body("old", args) == "from file"


def test_compute_new_body_append_adds_blank_line_separator(ei) -> None:
    args = argparse.Namespace(body=None, body_file=None, append="more")
    result = ei._compute_new_body("first paragraph.", args)
    assert result == "first paragraph.\n\nmore"


def test_compute_new_body_append_to_already_double_blank(ei) -> None:
    args = argparse.Namespace(body=None, body_file=None, append="more")
    result = ei._compute_new_body("first paragraph.\n\n", args)
    assert result == "first paragraph.\n\nmore"


def test_compute_new_body_append_to_empty(ei) -> None:
    args = argparse.Namespace(body=None, body_file=None, append="more")
    result = ei._compute_new_body("", args)
    assert result == "more"


def test_compute_new_body_no_args_returns_current(ei) -> None:
    args = argparse.Namespace(body=None, body_file=None, append=None)
    assert ei._compute_new_body("old", args) == "old"


def test_compute_new_body_missing_file_returns_none(ei, tmp_path) -> None:
    args = argparse.Namespace(
        body=None,
        body_file=tmp_path / "nonexistent.md",
        append=None,
    )
    assert ei._compute_new_body("old", args) is None


# --- validation ------------------------------------------------------


def test_validate_passes_for_well_formed_task(
    ei, issue_types, titles, body_format
) -> None:
    findings = ei._validate(
        title="[Task] Install the Claude Code CLI inside the sandbox",
        body=(
            "Feature: #1\n\n"
            "## What\nx\n"
            "## Acceptance criteria\n- [ ] x\n"
            "## Doc impact\nnone."
        ),
        issue_types=issue_types,
        titles=titles,
        body_format=body_format,
    )
    assert findings == []


def test_validate_flags_unknown_title_prefix(
    ei, issue_types, titles, body_format
) -> None:
    findings = ei._validate(
        title="Random title",
        body="some body",
        issue_types=issue_types,
        titles=titles,
        body_format=body_format,
    )
    labels = [f.label for f in findings]
    assert "title.format" in labels


def test_validate_flags_missing_required_section(
    ei, issue_types, titles, body_format
) -> None:
    findings = ei._validate(
        title="[Task] Install the Claude Code CLI inside the sandbox",
        body="Feature: #1\n\n## What\nx\n## Acceptance criteria\n- [ ] x",
        issue_types=issue_types,
        titles=titles,
        body_format=body_format,
    )
    labels = [f.label for f in findings]
    assert "body.required-section" in labels


def test_validate_flags_missing_parent_ref(
    ei, issue_types, titles, body_format
) -> None:
    findings = ei._validate(
        title="[Task] Install the Claude Code CLI inside the sandbox",
        body="## What\nx\n## Acceptance criteria\n- [ ] x\n## Doc impact\nnone.",
        issue_types=issue_types,
        titles=titles,
        body_format=body_format,
    )
    labels = [f.label for f in findings]
    assert "body.parent-ref" in labels


def test_validate_flags_h1_in_body(
    ei, issue_types, titles, body_format
) -> None:
    findings = ei._validate(
        title="[Task] Install the Claude Code CLI inside the sandbox",
        body=(
            "Feature: #1\n\n# forbidden h1\n"
            "## What\nx\n## Acceptance criteria\n- [ ] x\n## Doc impact\nnone."
        ),
        issue_types=issue_types,
        titles=titles,
        body_format=body_format,
    )
    labels = [f.label for f in findings]
    assert "body.h1" in labels


def test_validate_warns_on_file_line_refs(
    ei, issue_types, titles, body_format
) -> None:
    findings = ei._validate(
        title="[Task] Install the Claude Code CLI inside the sandbox",
        body=(
            "Feature: #1\n\n"
            "## What\nsee foo/bar.py:42 for context.\n"
            "## Acceptance criteria\n- [ ] x\n"
            "## Doc impact\nnone."
        ),
        issue_types=issue_types,
        titles=titles,
        body_format=body_format,
    )
    warns = [f for f in findings if f.severity == "warning"]
    assert any(f.label == "body.file-line-refs" for f in warns)


def test_validate_epic_passes_without_parent_ref(
    ei, issue_types, titles, body_format
) -> None:
    findings = ei._validate(
        title="[EPIC] Migrate the legacy work-tracker into Projects v2",
        body="some body",
        issue_types=issue_types,
        titles=titles,
        body_format=body_format,
    )
    parent_findings = [f for f in findings if f.label == "body.parent-ref"]
    assert parent_findings == []


def test_validate_accepts_markdown_milestone_link_form(
    ei, issue_types, titles, body_format
) -> None:
    """Per #210: `Milestone: [#N](../milestone/N)` is the new canonical form.

    edit-issue's regex previously rejected this form despite it being
    what create-issue produces (since #202). Brought into parity with
    validate-issue.py's three-regex pattern.
    """
    findings = ei._validate(
        title="[Task] Install the Claude Code CLI inside the sandbox",
        body=(
            "Milestone: [#6](../milestone/6)\n\n"
            "## What\nx\n## Acceptance criteria\n- [ ] x\n## Doc impact\nnone."
        ),
        issue_types=issue_types,
        titles=titles,
        body_format=body_format,
    )
    parent_findings = [f for f in findings if f.label.startswith("body.parent-ref")]
    assert parent_findings == [], (
        f"markdown milestone link rejected — got findings: {parent_findings}"
    )


def test_validate_warns_on_old_milestone_form(
    ei, issue_types, titles, body_format
) -> None:
    """Old plain `Milestone: #N` form is accepted with a deprecation warning."""
    findings = ei._validate(
        title="[Task] Install the Claude Code CLI inside the sandbox",
        body=(
            "Milestone: #6\n\n"
            "## What\nx\n## Acceptance criteria\n- [ ] x\n## Doc impact\nnone."
        ),
        issue_types=issue_types,
        titles=titles,
        body_format=body_format,
    )
    labels = [f.label for f in findings]
    severities = {f.label: f.severity for f in findings}
    # The old form is a warning, not a hard-reject.
    assert "body.parent-ref.milestone-old-form" in labels
    assert severities["body.parent-ref.milestone-old-form"] == "warning"
    # And no hard-reject parent-ref finding.
    assert not any(
        f.severity == "hard-reject" and f.label == "body.parent-ref"
        for f in findings
    )


def test_validate_still_rejects_unrelated_first_line(
    ei, issue_types, titles, body_format
) -> None:
    """Junk first lines (not any of the three accepted forms) still hard-reject."""
    findings = ei._validate(
        title="[Task] Install the Claude Code CLI inside the sandbox",
        body=(
            "Some random first line\n\n"
            "## What\nx\n## Acceptance criteria\n- [ ] x\n## Doc impact\nnone."
        ),
        issue_types=issue_types,
        titles=titles,
        body_format=body_format,
    )
    hard_rejects = [
        f for f in findings
        if f.severity == "hard-reject" and f.label == "body.parent-ref"
    ]
    assert hard_rejects, "junk first line should have raised a hard-reject parent-ref finding"


def test_validate_issue_parent_form_still_accepted(
    ei, issue_types, titles, body_format
) -> None:
    """Regression guard: the plain `<Label>: #N` issue-parent form still passes."""
    findings = ei._validate(
        title="[Task] Install the Claude Code CLI inside the sandbox",
        body=(
            "Feature: #1\n\n"
            "## What\nx\n## Acceptance criteria\n- [ ] x\n## Doc impact\nnone."
        ),
        issue_types=issue_types,
        titles=titles,
        body_format=body_format,
    )
    parent_findings = [f for f in findings if f.label.startswith("body.parent-ref")]
    assert parent_findings == [], (
        f"issue-parent form rejected — got findings: {parent_findings}"
    )


# --- structural type inference --------------------------------------


def test_infer_structural_type_recognises_task(ei, issue_types) -> None:
    assert ei._infer_structural_type("[Task] foo", issue_types) == "task"


def test_infer_structural_type_returns_none_for_unknown(ei, issue_types) -> None:
    assert ei._infer_structural_type("Plain", issue_types) is None


@pytest.fixture
def classification() -> dict:
    """Compact fixture mirroring classification.yaml's title_prefix_by_value."""
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
            },
        },
    }


def test_infer_structural_type_honours_bug_prefix(ei, issue_types, classification) -> None:
    """[Bug] prefix maps to structural type 'task' via classification.yaml."""
    result = ei._infer_structural_type("[Bug] Fix the auth flow", issue_types, classification)
    assert result == "task"


def test_infer_structural_type_honours_docs_prefix(ei, issue_types, classification) -> None:
    result = ei._infer_structural_type("[Docs] Update README", issue_types, classification)
    assert result == "task"


def test_infer_structural_type_honours_chore_prefix(ei, issue_types, classification) -> None:
    result = ei._infer_structural_type("[Chore] Bump dependency", issue_types, classification)
    assert result == "task"


def test_infer_structural_type_honours_refactor_prefix(ei, issue_types, classification) -> None:
    result = ei._infer_structural_type("[Refactor] Extract helper", issue_types, classification)
    assert result == "task"


def test_infer_structural_type_honours_test_prefix(ei, issue_types, classification) -> None:
    result = ei._infer_structural_type("[Test] Add coverage", issue_types, classification)
    assert result == "task"


def test_infer_structural_type_returns_none_without_classification(ei, issue_types) -> None:
    """Without classification data, [Bug] should return None — not a false match."""
    result = ei._infer_structural_type("[Bug] Fix the auth flow", issue_types)
    assert result is None


def test_validate_accepts_bug_prefix_with_classification(
    ei, issue_types, titles, body_format, classification
) -> None:
    """[Bug] title is accepted when classification is provided."""
    # The titles.yaml pattern for issue-task must match [Bug] too.
    # We simulate a permissive titles fixture that accepts all kind prefixes.
    titles_extended = {
        "formats": {
            "issue-task": {"pattern": r"^\[(Task|Bug|Docs|Test|Refactor|Chore)\] .+$"},
        },
    }
    findings = ei._validate(
        title="[Bug] Fix the auth flow completely",
        body=(
            "Feature: #1\n\n"
            "## What\nx\n"
            "## Acceptance criteria\n- [ ] x\n"
            "## Doc impact\nnone."
        ),
        issue_types=issue_types,
        titles=titles_extended,
        body_format=body_format,
        classification=classification,
    )
    format_findings = [f for f in findings if f.label == "title.format"]
    assert format_findings == [], (
        "Expected no title.format finding for [Bug] prefix with classification; "
        f"got: {findings}"
    )


def test_validate_rejects_bug_prefix_without_classification(
    ei, issue_types, titles, body_format
) -> None:
    """Without classification, [Bug] title should produce title.format finding."""
    findings = ei._validate(
        title="[Bug] Fix the auth flow completely",
        body="some body",
        issue_types=issue_types,
        titles=titles,
        body_format=body_format,
    )
    format_findings = [f for f in findings if f.label == "title.format"]
    assert format_findings, (
        "Expected title.format finding for [Bug] without classification"
    )


# --- title pattern ---------------------------------------------------


def test_title_pattern_for_returns_expected(ei, titles) -> None:
    assert ei._title_pattern_for(titles, "task") == r"^\[Task\] .+$"


def test_title_pattern_for_returns_none_for_unknown(ei, titles) -> None:
    assert ei._title_pattern_for(titles, "bogus") is None
