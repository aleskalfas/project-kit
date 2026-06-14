"""Tests for project-management's validate-issue script's pure logic.

The script's `_validate_issue` function takes already-parsed schemas
and issue data, so it's testable without subprocess mocking. Tests
exercise the validation paths against representative schema fixtures
+ synthetic issue bodies.
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
    """Load validate-issue.py as a module via importlib."""
    module_name = "pm_validate_issue_under_test"
    spec = importlib.util.spec_from_file_location(module_name, SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def issue_types() -> dict:
    """Minimal issue-types.yaml fixture covering the four structural types."""
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
            "umbrella": {
                "title_prefix": "Umbrella",
                "title_case": "title",
                "parent_issue_types": ["epic", "umbrella"],
                "parent_ref_optional": False,
                "parent_ref_form": "EPIC: #<N> or Umbrella: #<N>",
            },
            "task": {
                "title_prefix": "Task",
                "title_case": "title",
                "parent_issue_types": ["feature", "umbrella", "epic"],
                "parent_ref_optional": False,
                "parent_ref_form": "Feature: #<N> or Umbrella: #<N> or EPIC: #<N>",
            },
        },
    }


@pytest.fixture
def titles() -> dict:
    """Minimal titles.yaml fixture with per-type regex patterns."""
    return {
        "formats": {
            "issue-epic": {"pattern": r"^\[EPIC\] .+$"},
            "issue-feature": {"pattern": r"^\[Feature\] .+$"},
            "issue-umbrella": {"pattern": r"^\[Umbrella\] .+$"},
            "issue-task": {"pattern": r"^\[Task\] .+$"},
        },
    }


@pytest.fixture
def body_format() -> dict:
    """Minimal body-format.yaml fixture covering Task's required sections."""
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
            "epic": {
                "required_sections": [
                    {
                        "heading": "## Outcome",
                        "severity": "[validation-severity:hard-reject]",
                    },
                    {
                        "heading": "## Success criteria",
                        "severity": "[validation-severity:hard-reject]",
                    },
                ],
            },
        },
    }


@pytest.fixture
def label_fallback_config() -> dict:
    """Adopter config: label-fallback mode (no board)."""
    return {"has_projects_v2_board": False, "workstreams": ["cli", "schemas"]}


@pytest.fixture
def board_config() -> dict:
    """Adopter config: Projects v2 board mode."""
    return {"has_projects_v2_board": True, "projects_v2_board_id": 42}


# --- helpers ----------------------------------------------------------


def _make_issue(
    *,
    title: str,
    body: str,
    labels: list[str],
    assignees: list[dict] | None = None,
) -> dict:
    return {
        "title": title,
        "body": body,
        "labels": [{"name": lbl} for lbl in labels],
        "assignees": assignees if assignees is not None else [{"login": "alice"}],
    }


def _severities(findings) -> list[str]:
    return [f.severity for f in findings]


def _labels(findings) -> list[str]:
    return [f.label for f in findings]


# --- title format ----------------------------------------------------


def test_unknown_title_prefix_is_hard_reject(
    vi, issue_types, titles, body_format, label_fallback_config
) -> None:
    issue = _make_issue(
        title="Random title with no prefix",
        body="Feature: #1\n\n## What\nthing.\n## Acceptance criteria\n- [ ] x\n## Doc impact\nnone.",
        labels=["type:feature", "priority:Medium", "workstream:cli"],
    )
    findings = vi._validate_issue(
        issue=issue,
        issue_types=issue_types,
        titles=titles,
        body_format=body_format,
        config=label_fallback_config,
    )
    assert "title.format" in _labels(findings)


def test_valid_task_passes_title_check(
    vi, issue_types, titles, body_format, label_fallback_config
) -> None:
    issue = _make_issue(
        title="[Task] Install the Claude Code CLI inside the sandbox",
        body=(
            "Feature: #1\n\n"
            "## What\nThing.\n"
            "## Acceptance criteria\n- [ ] x\n"
            "## Doc impact\nnone."
        ),
        labels=["type:feature", "priority:Medium", "workstream:cli"],
    )
    findings = vi._validate_issue(
        issue=issue,
        issue_types=issue_types,
        titles=titles,
        body_format=body_format,
        config=label_fallback_config,
    )
    title_findings = [f for f in findings if f.label.startswith("title.")]
    assert title_findings == []


# --- classification --------------------------------------------------


def test_missing_type_label_is_hard_reject(
    vi, issue_types, titles, body_format, label_fallback_config
) -> None:
    issue = _make_issue(
        title="[Task] Install the Claude Code CLI inside the sandbox",
        body=(
            "Feature: #1\n\n## What\nx\n## Acceptance criteria\n- [ ] x\n## Doc impact\nnone."
        ),
        labels=["priority:Medium", "workstream:cli"],  # no type:*
    )
    findings = vi._validate_issue(
        issue=issue,
        issue_types=issue_types,
        titles=titles,
        body_format=body_format,
        config=label_fallback_config,
    )
    assert "classification.type.missing" in _labels(findings)


def test_multiple_type_labels_is_hard_reject(
    vi, issue_types, titles, body_format, label_fallback_config
) -> None:
    issue = _make_issue(
        title="[Task] Install the Claude Code CLI inside the sandbox",
        body=(
            "Feature: #1\n\n## What\nx\n## Acceptance criteria\n- [ ] x\n## Doc impact\nnone."
        ),
        labels=["type:feature", "type:bug", "priority:Medium", "workstream:cli"],
    )
    findings = vi._validate_issue(
        issue=issue,
        issue_types=issue_types,
        titles=titles,
        body_format=body_format,
        config=label_fallback_config,
    )
    assert "classification.type.multiple" in _labels(findings)


def test_board_mode_does_not_require_priority_or_workstream_labels(
    vi, issue_types, titles, body_format, board_config
) -> None:
    """In board mode, priority and workstream live on board fields, not labels."""
    issue = _make_issue(
        title="[Task] Install the Claude Code CLI inside the sandbox",
        body=(
            "Feature: #1\n\n## What\nx\n## Acceptance criteria\n- [ ] x\n## Doc impact\nnone."
        ),
        labels=["type:feature"],
    )
    findings = vi._validate_issue(
        issue=issue,
        issue_types=issue_types,
        titles=titles,
        body_format=body_format,
        config=board_config,
    )
    assert "classification.priority.missing" not in _labels(findings)
    assert "classification.workstream.missing" not in _labels(findings)


# --- assignment ------------------------------------------------------


def test_missing_assignee_is_warning(
    vi, issue_types, titles, body_format, label_fallback_config
) -> None:
    issue = _make_issue(
        title="[Task] Install the Claude Code CLI inside the sandbox",
        body=(
            "Feature: #1\n\n## What\nx\n## Acceptance criteria\n- [ ] x\n## Doc impact\nnone."
        ),
        labels=["type:feature", "priority:Medium", "workstream:cli"],
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


# --- body required sections ------------------------------------------


def test_missing_required_section_is_hard_reject(
    vi, issue_types, titles, body_format, label_fallback_config
) -> None:
    issue = _make_issue(
        title="[Task] Install the Claude Code CLI inside the sandbox",
        body=(
            "Feature: #1\n\n## What\nx\n## Acceptance criteria\n- [ ] x\n"
            # Missing ## Doc impact
        ),
        labels=["type:feature", "priority:Medium", "workstream:cli"],
    )
    findings = vi._validate_issue(
        issue=issue,
        issue_types=issue_types,
        titles=titles,
        body_format=body_format,
        config=label_fallback_config,
    )
    body_findings = [f for f in findings if f.label == "body.required-section"]
    assert len(body_findings) == 1
    assert "Doc impact" in body_findings[0].detail
    assert body_findings[0].severity == "hard-reject"


def test_all_required_sections_present_clears_body_check(
    vi, issue_types, titles, body_format, label_fallback_config
) -> None:
    issue = _make_issue(
        title="[Task] Install the Claude Code CLI inside the sandbox",
        body=(
            "Feature: #1\n\n## What\nx\n## Acceptance criteria\n- [ ] x\n## Doc impact\nnone."
        ),
        labels=["type:feature", "priority:Medium", "workstream:cli"],
    )
    findings = vi._validate_issue(
        issue=issue,
        issue_types=issue_types,
        titles=titles,
        body_format=body_format,
        config=label_fallback_config,
    )
    body_findings = [f for f in findings if f.label == "body.required-section"]
    assert body_findings == []


# --- parent-ref ------------------------------------------------------


def test_missing_parent_ref_first_line_is_hard_reject(
    vi, issue_types, titles, body_format, label_fallback_config
) -> None:
    issue = _make_issue(
        title="[Task] Install the Claude Code CLI inside the sandbox",
        body=(
            # Body opens directly with content; no parent-ref line.
            "## What\nx\n## Acceptance criteria\n- [ ] x\n## Doc impact\nnone."
        ),
        labels=["type:feature", "priority:Medium", "workstream:cli"],
    )
    findings = vi._validate_issue(
        issue=issue,
        issue_types=issue_types,
        titles=titles,
        body_format=body_format,
        config=label_fallback_config,
    )
    assert "body.parent-ref" in _labels(findings)


def test_epic_without_parent_ref_is_ok_because_parent_is_optional(
    vi, issue_types, titles, body_format, label_fallback_config
) -> None:
    issue = _make_issue(
        title="[EPIC] Migrate the legacy work-tracker into Projects v2",
        body="## Outcome\nThe thing happens.\n## Success criteria\n- [ ] x",
        labels=["type:feature", "priority:Medium", "workstream:cli"],
    )
    findings = vi._validate_issue(
        issue=issue,
        issue_types=issue_types,
        titles=titles,
        body_format=body_format,
        config=label_fallback_config,
    )
    assert "body.parent-ref" not in _labels(findings)


# --- universal body rules --------------------------------------------


def test_h1_heading_in_body_is_hard_reject(
    vi, issue_types, titles, body_format, label_fallback_config
) -> None:
    issue = _make_issue(
        title="[Task] Install the Claude Code CLI inside the sandbox",
        body=(
            "Feature: #1\n\n"
            "# Forbidden h1\n"
            "## What\nx\n## Acceptance criteria\n- [ ] x\n## Doc impact\nnone."
        ),
        labels=["type:feature", "priority:Medium", "workstream:cli"],
    )
    findings = vi._validate_issue(
        issue=issue,
        issue_types=issue_types,
        titles=titles,
        body_format=body_format,
        config=label_fallback_config,
    )
    assert "body.h1" in _labels(findings)


# --- severity token parsing ------------------------------------------


def test_severity_from_token_extracts_hard_reject(vi) -> None:
    assert vi._severity_from_token("[validation-severity:hard-reject]") == "hard-reject"


def test_severity_from_token_extracts_warning(vi) -> None:
    assert vi._severity_from_token("[validation-severity:warning]") == "warning"


def test_severity_from_token_falls_back_to_warning_on_bad_input(vi) -> None:
    assert vi._severity_from_token(None) == "warning"
    assert vi._severity_from_token("garbage") == "warning"


# --- structural-type inference ---------------------------------------


def test_infer_structural_type_recognises_each_prefix(vi, issue_types) -> None:
    assert vi._infer_structural_type("[EPIC] x", issue_types) == "epic"
    assert vi._infer_structural_type("[Feature] x", issue_types) == "feature"
    assert vi._infer_structural_type("[Umbrella] x", issue_types) == "umbrella"
    assert vi._infer_structural_type("[Task] x", issue_types) == "task"


def test_infer_structural_type_returns_none_for_unknown_prefix(vi, issue_types) -> None:
    assert vi._infer_structural_type("Plain title", issue_types) is None
    assert vi._infer_structural_type("[Bug] something", issue_types) is None


# --- milestone parent-ref forms (new canonical vs. old deprecated) ---


@pytest.fixture
def issue_types_with_milestone_parent() -> dict:
    """Issue-types fixture where task permits milestone as a parent."""
    return {
        "types": {
            "task": {
                "title_prefix": "Task",
                "title_case": "title",
                "parent_issue_types": ["feature", "umbrella", "epic", "milestone"],
                "parent_ref_optional": False,
                "parent_ref_form": (
                    "Feature: #<N> or Umbrella: #<N> or EPIC: #<N>"
                    " or Milestone: [#<N>](../milestone/<N>)"
                ),
            },
        },
    }


@pytest.fixture
def titles_task_only() -> dict:
    return {"formats": {"issue-task": {"pattern": r"^\[Task\] .+$"}}}


@pytest.fixture
def body_format_task_only() -> dict:
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


def _task_issue_with_first_line(first_line: str) -> dict:
    return {
        "title": "[Task] Some task",
        "body": (
            f"{first_line}\n\n"
            "## What\nThing.\n"
            "## Acceptance criteria\n- [ ] x\n"
            "## Doc impact\nnone."
        ),
        "labels": [{"name": "type:feature"}],
        "assignees": [{"login": "alice"}],
    }


def test_new_milestone_parent_ref_is_accepted_clean(
    vi,
    issue_types_with_milestone_parent,
    titles_task_only,
    body_format_task_only,
    board_config,
) -> None:
    """New form `Milestone: [#6](../milestone/6)` must produce no parent-ref finding."""
    issue = _task_issue_with_first_line("Milestone: [#6](../milestone/6)")
    findings = vi._validate_issue(
        issue=issue,
        issue_types=issue_types_with_milestone_parent,
        titles=titles_task_only,
        body_format=body_format_task_only,
        config=board_config,
    )
    parent_findings = [f for f in findings if "parent-ref" in f.label]
    assert parent_findings == [], f"unexpected findings: {parent_findings}"


def test_old_milestone_parent_ref_yields_warning(
    vi,
    issue_types_with_milestone_parent,
    titles_task_only,
    body_format_task_only,
    board_config,
) -> None:
    """Old form `Milestone: #6` must be accepted but produce a deprecation warning."""
    issue = _task_issue_with_first_line("Milestone: #6")
    findings = vi._validate_issue(
        issue=issue,
        issue_types=issue_types_with_milestone_parent,
        titles=titles_task_only,
        body_format=body_format_task_only,
        config=board_config,
    )
    parent_findings = [f for f in findings if "parent-ref" in f.label]
    assert len(parent_findings) == 1, f"expected 1 finding, got: {parent_findings}"
    assert parent_findings[0].severity == "warning"
    assert parent_findings[0].label == "body.parent-ref.milestone-old-form"


def test_malformed_milestone_parent_ref_is_hard_reject(
    vi,
    issue_types_with_milestone_parent,
    titles_task_only,
    body_format_task_only,
    board_config,
) -> None:
    """A truly malformed milestone ref (neither old nor new form) must hard-reject."""
    issue = _task_issue_with_first_line("Milestone: milestone/6")
    findings = vi._validate_issue(
        issue=issue,
        issue_types=issue_types_with_milestone_parent,
        titles=titles_task_only,
        body_format=body_format_task_only,
        config=board_config,
    )
    parent_findings = [f for f in findings if f.label == "body.parent-ref"]
    assert len(parent_findings) == 1
    assert parent_findings[0].severity == "hard-reject"


def test_new_milestone_form_number_must_match_in_text_and_link(
    vi,
    issue_types_with_milestone_parent,
    titles_task_only,
    body_format_task_only,
    board_config,
) -> None:
    """The regex requires the same N in `[#N]` and `../milestone/N`.

    Mismatched numbers (`[#6](../milestone/7)`) must hard-reject.
    """
    issue = _task_issue_with_first_line("Milestone: [#6](../milestone/7)")
    findings = vi._validate_issue(
        issue=issue,
        issue_types=issue_types_with_milestone_parent,
        titles=titles_task_only,
        body_format=body_format_task_only,
        config=board_config,
    )
    # Mismatched: back-reference fails, old form doesn't match either → hard-reject.
    parent_findings = [f for f in findings if "parent-ref" in f.label]
    assert len(parent_findings) == 1
    assert parent_findings[0].severity == "hard-reject"


# ---- placeholder detection (DEC-031) --------------------------------

CAPABILITY_ROOT = (
    REPO_ROOT
    / ".pkit"
    / "capabilities"
    / "project-management"
)


@pytest.fixture
def body_format_with_checkboxes() -> dict:
    """body-format fixture that declares has_checkboxes: true for task sections."""
    return {
        "bodies": {
            "task": {
                "required_sections": [
                    {
                        "heading": "## What",
                        "severity": "[validation-severity:hard-reject]",
                        "has_checkboxes": False,
                        "purpose": "What",
                    },
                    {
                        "heading": "## Acceptance criteria",
                        "severity": "[validation-severity:hard-reject]",
                        "has_checkboxes": True,
                        "purpose": "Criteria",
                    },
                    {
                        "heading": "## Doc impact",
                        "severity": "[validation-severity:hard-reject]",
                        "has_checkboxes": False,
                        "purpose": "Docs",
                    },
                ],
            },
            "epic": {
                "required_sections": [
                    {
                        "heading": "## Outcome",
                        "severity": "[validation-severity:hard-reject]",
                        "has_checkboxes": False,
                        "purpose": "Outcome",
                    },
                    {
                        "heading": "## Success criteria",
                        "severity": "[validation-severity:hard-reject]",
                        "has_checkboxes": True,
                        "purpose": "Criteria",
                    },
                ],
            },
        },
    }


def _make_full_task_issue(body: str, labels: list[str] | None = None) -> dict:
    """Helper: task issue with the given body."""
    return {
        "title": "[Task] Some authored task",
        "body": body,
        "labels": [{"name": lbl} for lbl in (labels or ["type:feature"])],
        "assignees": [{"login": "alice"}],
    }


# -- authored body passes without placeholder findings ----------------


def test_authored_task_body_no_placeholder_findings(
    vi,
    issue_types,
    titles,
    body_format_with_checkboxes,
    board_config,
) -> None:
    """A fully authored body with filled checkbox items produces no placeholder findings."""
    body = (
        "Feature: #1\n\n"
        "## What\n"
        "Implement the frobnication layer.\n\n"
        "## Acceptance criteria\n"
        "- [x] The frobnication layer is installed.\n"
        "- [x] Tests pass.\n\n"
        "## Doc impact\n"
        "No doc impact: internal refactor only.\n"
    )
    issue = _make_full_task_issue(body)
    findings = vi._validate_issue(
        issue=issue,
        issue_types=issue_types,
        titles=titles,
        body_format=body_format_with_checkboxes,
        config=board_config,
        capability_root=CAPABILITY_ROOT,
        phase="transition",
    )
    placeholder_findings = [
        f for f in findings if f.label.startswith("body.placeholder")
    ]
    assert placeholder_findings == [], f"unexpected: {placeholder_findings}"


# -- raw skeleton: empty checkbox section → hard-reject at transition --


def test_empty_checkbox_section_is_hard_reject_at_transition(
    vi,
    issue_types,
    titles,
    body_format_with_checkboxes,
    board_config,
) -> None:
    """A required checkbox section with zero filled items is a hard-reject at transition."""
    body = (
        "Feature: #1\n\n"
        "## What\n"
        "The concrete change being made. Outcome-focused, not implementation-focused.\n\n"
        "## Acceptance criteria\n"
        "- [ ]\n"
        "- [ ]\n\n"
        "## Doc impact\n"
        "- [ ]\n"
    )
    issue = _make_full_task_issue(body)
    findings = vi._validate_issue(
        issue=issue,
        issue_types=issue_types,
        titles=titles,
        body_format=body_format_with_checkboxes,
        config=board_config,
        capability_root=CAPABILITY_ROOT,
        phase="transition",
    )
    cb_findings = [f for f in findings if f.label == "body.placeholder.empty-checkbox-section"]
    assert len(cb_findings) >= 1, f"expected at least one finding, got: {findings}"
    assert all(f.severity == "hard-reject" for f in cb_findings)


# -- raw skeleton: empty checkbox section → warning at create ----------


def test_empty_checkbox_section_is_warning_at_create(
    vi,
    issue_types,
    titles,
    body_format_with_checkboxes,
    board_config,
) -> None:
    """A required checkbox section with zero filled items is only a warning at create."""
    body = (
        "Feature: #1\n\n"
        "## What\n"
        "The concrete change being made. Outcome-focused, not implementation-focused.\n\n"
        "## Acceptance criteria\n"
        "- [ ]\n"
        "- [ ]\n\n"
        "## Doc impact\n"
        "- [ ]\n"
    )
    issue = _make_full_task_issue(body)
    findings = vi._validate_issue(
        issue=issue,
        issue_types=issue_types,
        titles=titles,
        body_format=body_format_with_checkboxes,
        config=board_config,
        capability_root=CAPABILITY_ROOT,
        phase="create",
    )
    cb_findings = [f for f in findings if f.label == "body.placeholder.empty-checkbox-section"]
    assert len(cb_findings) >= 1, f"expected at least one finding, got: {findings}"
    assert all(f.severity == "warning" for f in cb_findings), (
        f"expected all warnings at create phase, got: {[f.severity for f in cb_findings]}"
    )


# -- lenient: trailing empty box alongside filled items is OK ----------


def test_trailing_empty_checkbox_alongside_filled_items_is_ok(
    vi,
    issue_types,
    titles,
    body_format_with_checkboxes,
    board_config,
) -> None:
    """A section with some filled and some empty checkboxes must NOT trigger the signal."""
    body = (
        "Feature: #1\n\n"
        "## What\n"
        "Implement the frobnication layer.\n\n"
        "## Acceptance criteria\n"
        "- [x] The frobnication layer is installed.\n"
        "- [ ] Leftover empty box.\n\n"  # trailing empty — lenient rule: should pass
        "## Doc impact\n"
        "No doc impact: internal refactor only.\n"
    )
    issue = _make_full_task_issue(body)
    findings = vi._validate_issue(
        issue=issue,
        issue_types=issue_types,
        titles=titles,
        body_format=body_format_with_checkboxes,
        config=board_config,
        capability_root=CAPABILITY_ROOT,
        phase="transition",
    )
    cb_findings = [
        f for f in findings if f.label == "body.placeholder.empty-checkbox-section"
    ]
    assert cb_findings == [], f"unexpected findings: {cb_findings}"


# -- placeholder prose: surviving template text → warning -------------


def test_surviving_template_prose_is_warning(
    vi,
    issue_types,
    titles,
    body_format_with_checkboxes,
    board_config,
) -> None:
    """A body still containing the template's placeholder prose emits a warning."""
    # Use the literal placeholder prose from Task.md:
    # "The concrete change being made. Outcome-focused, not implementation-focused."
    body = (
        "Feature: #1\n\n"
        "## What\n"
        "The concrete change being made. Outcome-focused, not implementation-focused.\n\n"
        "## Acceptance criteria\n"
        "- [x] Something real.\n\n"
        "## Doc impact\n"
        "No doc impact: internal refactor only.\n"
    )
    issue = _make_full_task_issue(body)
    findings = vi._validate_issue(
        issue=issue,
        issue_types=issue_types,
        titles=titles,
        body_format=body_format_with_checkboxes,
        config=board_config,
        capability_root=CAPABILITY_ROOT,
        phase="transition",
    )
    prose_findings = [f for f in findings if f.label == "body.placeholder.template-prose"]
    assert len(prose_findings) == 1, f"expected 1 prose finding, got: {findings}"
    assert prose_findings[0].severity == "warning"


# -- no false positive when capability_root is None -------------------


def test_no_placeholder_check_when_no_capability_root(
    vi,
    issue_types,
    titles,
    body_format_with_checkboxes,
    board_config,
) -> None:
    """When capability_root is None the placeholder check is skipped (no crash)."""
    body = (
        "Feature: #1\n\n"
        "## What\n"
        "The concrete change being made. Outcome-focused, not implementation-focused.\n\n"
        "## Acceptance criteria\n"
        "- [ ]\n\n"
        "## Doc impact\n"
        "- [ ]\n"
    )
    issue = _make_full_task_issue(body)
    # Should not raise, and should produce no placeholder findings.
    findings = vi._validate_issue(
        issue=issue,
        issue_types=issue_types,
        titles=titles,
        body_format=body_format_with_checkboxes,
        config=board_config,
        capability_root=None,  # explicitly no root
        phase="transition",
    )
    placeholder_findings = [
        f for f in findings if f.label.startswith("body.placeholder")
    ]
    assert placeholder_findings == []
