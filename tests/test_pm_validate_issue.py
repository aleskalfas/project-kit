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
def classification() -> dict:
    """Minimal classification.yaml fixture carrying the DEC-011 restriction."""
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
                    "mismatch_severity": "[validation-severity:hard-reject]",
                },
            }
        }
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


def test_kind_structural_mismatch_at_create_is_hard_reject(
    vi, issue_types, titles, body_format, classification, label_fallback_config
) -> None:
    # A Feature labelled type:bug is the DEC-011 mismatch. At --phase create it
    # is a hard-reject (refused at the point of manufacture) carrying the
    # schema's mismatch_severity token.
    issue = _make_issue(
        title="[Feature] deliver the widget",
        body="EPIC: #1\n\n## What\nx.",
        labels=["type:bug", "priority:Medium", "workstream:cli"],
    )
    findings = vi._validate_issue(
        issue=issue,
        issue_types=issue_types,
        titles=titles,
        body_format=body_format,
        classification=classification,
        config=label_fallback_config,
        phase=vi.PHASE_CREATE,
    )
    mismatch = [
        f for f in findings if f.label == "classification.type.structural-mismatch"
    ]
    assert len(mismatch) == 1
    assert mismatch[0].severity == "hard-reject"


def test_kind_structural_mismatch_at_transition_is_warning(
    vi, issue_types, titles, body_format, classification, label_fallback_config
) -> None:
    # Phase-split (#410): the SAME mismatch at --phase transition is a warning,
    # not a hard-reject — a pre-existing container-kind mismatch corrupts the
    # closing-PR conv-type derivation (a create-PR concern), not the transition
    # in flight, so it must not wall traversal of a mismatched live ancestor.
    issue = _make_issue(
        title="[Feature] deliver the widget",
        body="EPIC: #1\n\n## What\nx.",
        labels=["type:bug", "priority:Medium", "workstream:cli"],
    )
    findings = vi._validate_issue(
        issue=issue,
        issue_types=issue_types,
        titles=titles,
        body_format=body_format,
        classification=classification,
        config=label_fallback_config,
        phase=vi.PHASE_TRANSITION,
    )
    mismatch = [
        f for f in findings if f.label == "classification.type.structural-mismatch"
    ]
    assert len(mismatch) == 1
    assert mismatch[0].severity == "warning"
    # It must be non-blocking: no hard-reject / bypassable severity on it.
    assert mismatch[0].severity not in (
        vi.SEVERITY_HARD_REJECT,
        vi.SEVERITY_BYPASSABLE,
    )


def test_kind_structural_mismatch_default_phase_is_warning(
    vi, issue_types, titles, body_format, classification, label_fallback_config
) -> None:
    # validate-issue's default phase is transition (DEC-031); an unqualified
    # call therefore reports the mismatch as a warning rather than blocking.
    issue = _make_issue(
        title="[Feature] deliver the widget",
        body="EPIC: #1\n\n## What\nx.",
        labels=["type:bug", "priority:Medium", "workstream:cli"],
    )
    findings = vi._validate_issue(
        issue=issue,
        issue_types=issue_types,
        titles=titles,
        body_format=body_format,
        classification=classification,
        config=label_fallback_config,
    )
    mismatch = [
        f for f in findings if f.label == "classification.type.structural-mismatch"
    ]
    assert len(mismatch) == 1
    assert mismatch[0].severity == "warning"


@pytest.mark.parametrize("phase", ["create", "transition"])
def test_feature_kind_on_feature_passes(
    vi, issue_types, titles, body_format, classification, label_fallback_config, phase
) -> None:
    # The legitimate case: a [Feature] carrying its implicit kind `feature`.
    # Clean in BOTH phases — the phase-split only governs mismatch severity.
    issue = _make_issue(
        title="[Feature] deliver the widget",
        body="EPIC: #1\n\n## What\nx.",
        labels=["type:feature", "priority:Medium", "workstream:cli"],
    )
    findings = vi._validate_issue(
        issue=issue,
        issue_types=issue_types,
        titles=titles,
        body_format=body_format,
        classification=classification,
        config=label_fallback_config,
        phase=phase,
    )
    assert "classification.type.structural-mismatch" not in _labels(findings)


@pytest.mark.parametrize("phase", ["create", "transition"])
def test_bug_kind_on_task_passes(
    vi, issue_types, titles, body_format, classification, label_fallback_config, phase
) -> None:
    # A [Bug] Task carrying type:bug is the correct shape — no mismatch finding
    # in either phase.
    issue = _make_issue(
        title="[Bug] fix the crash",
        body=(
            "Feature: #1\n\n## What\nx\n## Acceptance criteria\n- [ ] x\n"
            "## Doc impact\nnone."
        ),
        labels=["type:bug", "priority:Medium", "workstream:cli"],
    )
    findings = vi._validate_issue(
        issue=issue,
        issue_types=issue_types,
        titles=titles,
        body_format=body_format,
        classification=classification,
        config=label_fallback_config,
        phase=phase,
    )
    assert "classification.type.structural-mismatch" not in _labels(findings)


def test_no_mismatch_finding_without_classification(
    vi, issue_types, titles, body_format, label_fallback_config
) -> None:
    # Backward-compat: with no classification passed (or an empty one), the
    # predicate degrades permissive — no mismatch finding is manufactured.
    issue = _make_issue(
        title="[Feature] deliver the widget",
        body="EPIC: #1\n\n## What\nx.",
        labels=["type:bug", "priority:Medium", "workstream:cli"],
    )
    findings = vi._validate_issue(
        issue=issue,
        issue_types=issue_types,
        titles=titles,
        body_format=body_format,
        config=label_fallback_config,
    )
    assert "classification.type.structural-mismatch" not in _labels(findings)


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


def test_parent_ref_found_beneath_dec013_integration_marker(
    vi, issue_types, titles, body_format, label_fallback_config
) -> None:
    """DEC-013 (#763): a marked descendant carries `Integration: integration/<slug>`
    as its first body line, above the parent-ref. Validation must skip the marker
    and recognise the parent-ref on the next content line — NOT hard-reject the
    marker as a malformed first line (the bug #763 fixes)."""
    issue = _make_issue(
        title="[Task] Wire the claim seam into start-work",
        body=(
            "Integration: integration/508-multi-instance-ownership\n"
            "Feature: #510\n\n"
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
    assert "body.parent-ref" not in _labels(findings)


def test_malformed_integration_marker_is_a_precise_hard_reject(
    vi, issue_types, titles, body_format, label_fallback_config
) -> None:
    """DEC-013 (#763) AC3: a first line that attempts the marker but is malformed
    hard-rejects as `body.integration-marker` naming the expected form — NOT the
    misleading `body.parent-ref` a fall-through would produce."""
    issue = _make_issue(
        title="[Task] Wire the claim seam into start-work",
        body=(
            "Integration: integration/Foo_Bar!!\n"
            "Feature: #510\n\n"
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
    labels = _labels(findings)
    assert "body.integration-marker" in labels
    assert "body.parent-ref" not in labels


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


def test_missing_parent_ref_degrades_to_warning_under_advisory_hierarchy(
    vi, issue_types, titles, body_format, label_fallback_config
) -> None:
    """DEC-036 D4: the body-format.yaml parent-ref rule is one of the two
    parent-requiredness rules `hierarchy: advisory` relaxes. A flat-tracker issue
    with NO machine-checkable parent-ref first line must NOT hard-reject at
    validate-issue — otherwise a flat adopter who files parentless through
    create-issue (advisory) hits a wall at the first transition. Under advisory
    the finding degrades to a warning (still surfaced, never gated)."""
    issue = _make_issue(
        title="[Task] Install the Claude Code CLI inside the sandbox",
        # Body opens directly with content; no parent-ref line.
        body="## What\nx\n## Acceptance criteria\n- [ ] x\n## Doc impact\nnone.",
        labels=["type:feature", "priority:Medium", "workstream:cli"],
    )
    findings = vi._validate_issue(
        issue=issue,
        issue_types=issue_types,
        titles=titles,
        body_format=body_format,
        config=label_fallback_config,
        hierarchy=vi.axis_labels.HIERARCHY_ADVISORY,
    )
    parent_findings = [f for f in findings if f.label == "body.parent-ref"]
    # Still surfaced — but as a warning, NOT a hard-reject.
    assert len(parent_findings) == 1
    assert parent_findings[0].severity == vi.SEVERITY_WARNING
    # No hard-reject anywhere on the parent-ref axis under advisory.
    assert vi.SEVERITY_HARD_REJECT not in _severities(parent_findings)


def test_missing_parent_ref_still_hard_rejects_under_greenfield(
    vi, issue_types, titles, body_format, label_fallback_config
) -> None:
    """Greenfield parity (the other direction): with no substrate-map the
    hierarchy defaults to gated, so the SAME parentless body that degrades under
    advisory still hard-rejects. The default `hierarchy` arg is gated, so a caller
    that passes nothing gets the byte-unchanged greenfield gate."""
    issue = _make_issue(
        title="[Task] Install the Claude Code CLI inside the sandbox",
        body="## What\nx\n## Acceptance criteria\n- [ ] x\n## Doc impact\nnone.",
        labels=["type:feature", "priority:Medium", "workstream:cli"],
    )
    findings = vi._validate_issue(
        issue=issue,
        issue_types=issue_types,
        titles=titles,
        body_format=body_format,
        config=label_fallback_config,
        # hierarchy omitted ⇒ gated default (greenfield).
    )
    parent_findings = [f for f in findings if f.label == "body.parent-ref"]
    assert len(parent_findings) == 1
    assert parent_findings[0].severity == vi.SEVERITY_HARD_REJECT


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


# --- brownfield type-presence (substrate-map bound to title-prefix) ----
# #553: validate-issue's type-presence gate must route through the SAME
# substrate-map seam pre-check uses. When `type` is bound to the adopter's own
# substrate (title-prefix), no kit `type:*` label is written, so demanding one
# false-fails every issue while pre-check on the same repo reports the axis
# served. These pin the fix and the greenfield parity (the other direction).


@pytest.fixture(scope="module")
def precheck():
    """Load pre-check.py as a module — for the gate-agreement disposition test."""
    script_path = (
        REPO_ROOT
        / ".pkit"
        / "capabilities"
        / "project-management"
        / "scripts"
        / "pre-check.py"
    )
    module_name = "pm_pre_check_under_test"
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def brownfield_type_prefix_map(vi):
    """A substrate-map binding `type` to the adopter's title-prefix substrate.

    The brownfield shape #553 is about: `type` served via `title-prefix`, so the
    kit writes no `type:*` label (never-write-an-unmanaged-label). A present map
    means the seam is in effect — `axis_expects_kit_labels("type", map)` is False.
    """
    return vi.axis_labels.SubstrateMap(
        axes={
            "type": {
                "title-prefix": {
                    "remap": {
                        # The adopter's OWN bracket prefixes (as the shipped AUJ
                        # reference declares them) — note `epic` is `[Epic]`, NOT
                        # the kit's rendered `[EPIC]`. That divergence is the R1
                        # false-reject: the kit vocabulary would fail `[Epic]`.
                        "task": "[Task]",
                        "epic": "[Epic]",
                        "umbrella": "[Umbrella]",
                        "feature": "[Feature]",
                    }
                }
            }
        }
    )


@pytest.fixture
def brownfield_type_label_map(vi):
    """A substrate-map binding `type` to an adopter LABEL remap.

    The G1 shape: `type` served via a value→label remap onto the adopter's own
    labels (not the kit `type:*`). Presence must be checked against those remapped
    labels — a missing one is a genuine missing-value (hard-reject), a present one
    is clean.
    """
    return vi.axis_labels.SubstrateMap(
        axes={
            "type": {
                "label": {
                    "remap": {
                        "feature": "kind/feature",
                        "epic": "kind/epic",
                        "task": "kind/task",
                        "umbrella": "kind/umbrella",
                    }
                }
            }
        }
    )


def test_brownfield_no_type_label_does_not_hard_reject(
    vi, issue_types, titles, body_format, board_config, brownfield_type_prefix_map
) -> None:
    """(a) Brownfield: a correctly-prefixed issue with ZERO `type:*` labels does
    NOT emit `classification.type.missing`; it relies on the parsed structural
    type. Board config so unrelated priority/workstream label demands stay out of
    the way — the assertion is scoped to the type axis (the #553 fix)."""
    issue = _make_issue(
        title="[Task] Install the Claude Code CLI inside the sandbox",
        body=(
            "Feature: #1\n\n"
            "## What\nx\n## Acceptance criteria\n- [ ] x\n## Doc impact\nnone."
        ),
        labels=[],  # no kit labels at all — a real brownfield tracker
    )
    findings = vi._validate_issue(
        issue=issue,
        issue_types=issue_types,
        titles=titles,
        body_format=body_format,
        config=board_config,
        substrate_map=brownfield_type_prefix_map,
    )
    assert "classification.type.missing" not in _labels(findings)
    # And it validates clean overall (no blocking findings) — the type axis is
    # satisfied by the [Task] prefix, everything else is in order.
    blocking = [
        f
        for f in findings
        if f.severity in (vi.SEVERITY_HARD_REJECT, vi.SEVERITY_BYPASSABLE)
    ]
    assert blocking == [], f"unexpected blocking findings: {_labels(findings)}"


def test_greenfield_missing_type_label_still_hard_rejects(
    vi, issue_types, titles, body_format, label_fallback_config
) -> None:
    """(b) Greenfield parity: with no substrate-map (or `type` served by kit
    labels), a missing `type:*` label is still a hard-reject — unchanged."""
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
        substrate_map=None,  # greenfield, explicit
    )
    assert "classification.type.missing" in _labels(findings)


def test_dec011_cross_check_still_fires_greenfield(
    vi, issue_types, titles, body_format, classification, label_fallback_config
) -> None:
    """(c) DEC-011 kind/structural cross-check still fires in greenfield: a
    [Feature] carrying `type:bug` is the mismatch, reported at --phase create."""
    issue = _make_issue(
        title="[Feature] deliver the widget",
        body="EPIC: #1\n\n## What\nx.",
        labels=["type:bug", "priority:Medium", "workstream:cli"],
    )
    findings = vi._validate_issue(
        issue=issue,
        issue_types=issue_types,
        titles=titles,
        body_format=body_format,
        classification=classification,
        config=label_fallback_config,
        phase=vi.PHASE_CREATE,
        substrate_map=None,
    )
    assert "classification.type.structural-mismatch" in _labels(findings)


def test_dec011_cross_check_demands_no_label_in_brownfield(
    vi,
    issue_types,
    titles,
    body_format,
    classification,
    board_config,
    brownfield_type_prefix_map,
) -> None:
    """(c, other direction) In brownfield the cross-check has no `type:*` label to
    evaluate — it must neither fire the mismatch nor newly-demand a label. A
    [Feature] with zero labels is clean on the type axis."""
    issue = _make_issue(
        title="[Feature] deliver the widget",
        body="EPIC: #1\n\n## What\nx.",
        labels=[],
    )
    findings = vi._validate_issue(
        issue=issue,
        issue_types=issue_types,
        titles=titles,
        body_format=body_format,
        classification=classification,
        config=board_config,
        phase=vi.PHASE_CREATE,
        substrate_map=brownfield_type_prefix_map,
    )
    assert "classification.type.missing" not in _labels(findings)
    assert "classification.type.structural-mismatch" not in _labels(findings)


def test_brownfield_bad_prefix_surfaces_title_format_not_label_error(
    vi, issue_types, titles, body_format, board_config, brownfield_type_prefix_map
) -> None:
    """(d) Brownfield with a bad/absent title prefix: the REAL error surfaces —
    title.format (the type can't be inferred) — NOT a spurious type-label error.
    The prefix, not a label, is the type substrate here, so a broken prefix is
    the thing to report."""
    issue = _make_issue(
        title="Random title with no prefix",
        body="Feature: #1\n\n## What\nx.",
        labels=[],
    )
    findings = vi._validate_issue(
        issue=issue,
        issue_types=issue_types,
        titles=titles,
        body_format=body_format,
        config=board_config,
        substrate_map=brownfield_type_prefix_map,
    )
    assert "title.format" in _labels(findings)
    assert "classification.type.missing" not in _labels(findings)


def test_validate_issue_and_pre_check_agree_on_type_disposition(
    vi, precheck, brownfield_type_prefix_map
) -> None:
    """Gate-agreement (the #553 acceptance): validate-issue and pre-check must
    reach the SAME "are kit type labels required?" disposition on the same repo.

    Both route through the one seam predicate — pre-check via its thin
    `_axis_expects_kit_labels` adapter, validate-issue via the seam directly — so
    they cannot disagree. Proven at the disposition seam in both substrates."""
    # Brownfield: a present map binding type→title-prefix ⇒ kit labels NOT required.
    assert (
        vi.axis_labels.axis_expects_kit_labels("type", brownfield_type_prefix_map)
        is False
    )
    assert (
        precheck._axis_expects_kit_labels("type", brownfield_type_prefix_map) is False
    )
    # Greenfield: no map ⇒ kit labels ARE required, both agree.
    assert vi.axis_labels.axis_expects_kit_labels("type", None) is True
    assert precheck._axis_expects_kit_labels("type", None) is True
    # And they agree value-for-value in both substrates (one source of truth).
    for smap in (None, brownfield_type_prefix_map):
        assert vi.axis_labels.axis_expects_kit_labels(
            "type", smap
        ) == precheck._axis_expects_kit_labels("type", smap)


# --- R1: title-prefix inference is substrate-aware ---------------------
# The blocker #553 exists to remove, one check earlier than the label gate: an
# adopter's `[Epic]` prefix (bound in substrate-map.yaml) diverges from the kit's
# rendered `[EPIC]`, so the old kit-vocabulary `title.format` hard-rejected it.


def test_brownfield_adopter_epic_prefix_validates_clean(
    vi, issue_types, titles, body_format, board_config, brownfield_type_prefix_map
) -> None:
    """(R1) An AUJ-style `[Epic]` title (adopter prefix ≠ the kit's `[EPIC]`),
    zero labels, validates clean — the structural type resolves via the adopter's
    declared prefixes, not the kit vocabulary. This is the R1 false-reject closed."""
    issue = _make_issue(
        title="[Epic] Stand up the sandbox backbone",
        body=(
            "Parent: #1\n\n"
            "## Outcome\nDe-risk the backbone.\n"
            "## Success criteria\n- [ ] the sandbox boots.\n"
        ),
        labels=[],
    )
    findings = vi._validate_issue(
        issue=issue,
        issue_types=issue_types,
        titles=titles,
        body_format=body_format,
        config=board_config,
        substrate_map=brownfield_type_prefix_map,
    )
    assert "title.format" not in _labels(findings)
    assert "title.pattern" not in _labels(findings)  # kit regex does not apply
    blocking = [
        f
        for f in findings
        if f.severity in (vi.SEVERITY_HARD_REJECT, vi.SEVERITY_BYPASSABLE)
    ]
    assert blocking == [], f"unexpected blocking findings: {_labels(findings)}"


def test_brownfield_adopter_epic_infers_structural_type_via_seam(
    vi, issue_types, brownfield_type_prefix_map
) -> None:
    """The `[Epic]` prefix resolves to the `epic` structural type through the seam
    (not the kit `[EPIC]`), and the kit vocabulary would NOT have matched it."""
    assert (
        vi._infer_structural_type(
            "[Epic] x", issue_types, brownfield_type_prefix_map
        )
        == "epic"
    )
    # The kit greenfield vocabulary renders `[EPIC]`, so it does NOT match `[Epic]`.
    assert vi._infer_structural_type("[Epic] x", issue_types, None) is None


def test_brownfield_unknown_prefix_hard_rejects_undeterminable_type(
    vi, issue_types, titles, body_format, board_config, brownfield_type_prefix_map
) -> None:
    """(b, architect ruling) A title matching NONE of the adopter's declared
    prefixes resolves to no structural type — an undeterminable close-gate
    failure. It surfaces the REAL error (`title.format`, not a spurious label
    error) and HARD-REJECTS, exactly as greenfield hard-rejects an unknown prefix
    and as the label-remap arm hard-rejects a missing remapped label; only the
    message vocabulary differs, naming the adopter's declared prefixes."""
    issue = _make_issue(
        title="[Spike] not an adopter prefix",
        body="Parent: #1\n\n## What\nx.",
        labels=[],
    )
    findings = vi._validate_issue(
        issue=issue,
        issue_types=issue_types,
        titles=titles,
        body_format=body_format,
        config=board_config,
        substrate_map=brownfield_type_prefix_map,
    )
    title_format = [f for f in findings if f.label == "title.format"]
    assert title_format, "expected the real title.format error to surface"
    assert title_format[0].severity == vi.SEVERITY_HARD_REJECT
    # Adopter vocabulary, not the kit's — names the declared prefixes.
    assert "adopter's declared" in title_format[0].detail
    assert "classification.type.missing" not in _labels(findings)


# --- G1: label-bound type axis gets a presence check ------------------


def test_brownfield_label_bound_type_missing_label_hard_rejects(
    vi, issue_types, titles, body_format, board_config, brownfield_type_label_map
) -> None:
    """(c, G1) `type` bound to a label remap: a missing remapped label is a
    genuine missing-value — hard-reject, exactly as greenfield gates a missing
    `type:*`. This closes the false-ACCEPT the incomplete cut left open."""
    issue = _make_issue(
        title="Add the widget",  # no prefix — type is label-carried here
        body="Parent: #1\n\n## What\nx.",
        labels=[],  # none of the adopter's remapped type labels present
    )
    findings = vi._validate_issue(
        issue=issue,
        issue_types=issue_types,
        titles=titles,
        body_format=body_format,
        config=board_config,
        substrate_map=brownfield_type_label_map,
    )
    type_missing = [f for f in findings if f.label == "classification.type.missing"]
    assert type_missing, "a label-bound type with no remapped label must be demanded"
    assert type_missing[0].severity == vi.SEVERITY_HARD_REJECT


def test_brownfield_label_bound_type_present_label_clean(
    vi, issue_types, titles, body_format, board_config, brownfield_type_label_map
) -> None:
    """(c) `type` bound to a label remap with a remapped label PRESENT — clean on
    the type axis (resolve_read reverse-maps `kind/feature` → `feature`)."""
    issue = _make_issue(
        title="Add the widget",
        body="Parent: #1\n\n## What\nx.",
        labels=["kind/feature"],  # an adopter-remapped type label
    )
    findings = vi._validate_issue(
        issue=issue,
        issue_types=issue_types,
        titles=titles,
        body_format=body_format,
        config=board_config,
        substrate_map=brownfield_type_label_map,
    )
    assert "classification.type.missing" not in _labels(findings)
    # And no spurious title finding — type is label-carried, not title-carried.
    assert "title.format" not in _labels(findings)


# --- gate-agreement across ALL type bindings (the #553 acceptance) -----


def test_gate_agreement_across_all_type_bindings(
    vi, precheck, brownfield_type_prefix_map, brownfield_type_label_map
) -> None:
    """validate-issue and pre-check reach the SAME type-substrate disposition on
    the same repo across every binding — kit-label, title-prefix (incl. the
    `[Epic]` vs kit `[EPIC]` mismatch), label-remap, derive, unsupported. Both
    route through the one seam, so they cannot drift.

    Proven at the seam predicates the two consumers share: the kit-label
    disposition (`axis_expects_kit_labels`, via pre-check's thin adapter) and the
    title-prefix vocabulary (`axis_title_prefix_remap`, which validate-issue's
    inference and pre-check's alignment both read)."""
    derive_map = vi.axis_labels.SubstrateMap(
        axes={"type": {"derive": {"from": "open-closed"}}}
    )
    unsupported_map = vi.axis_labels.SubstrateMap(
        axes={"type": {"unsupported": True}}
    )
    all_maps = {
        "greenfield": None,
        "title-prefix": brownfield_type_prefix_map,
        "label-remap": brownfield_type_label_map,
        "derive": derive_map,
        "unsupported": unsupported_map,
    }
    for name, smap in all_maps.items():
        # (1) kit-label disposition agrees between the two consumers.
        assert vi.axis_labels.axis_expects_kit_labels(
            "type", smap
        ) == precheck._axis_expects_kit_labels("type", smap), name
        # (2) both read the adopter's title-prefix vocabulary through the SAME
        # seam accessor — identical remap (or None) for every binding.
        assert vi.axis_labels.axis_title_prefix_remap(
            "type", smap
        ) == precheck.axis_labels.axis_title_prefix_remap("type", smap), name

    # Only greenfield expects the kit's own type labels.
    assert vi.axis_labels.axis_expects_kit_labels("type", None) is True
    for smap in (brownfield_type_prefix_map, brownfield_type_label_map, derive_map):
        assert vi.axis_labels.axis_expects_kit_labels("type", smap) is False

    # The `[Epic]` mismatch specifically: the adopter's `[Epic]` is in the vocab
    # both consumers validate against (so neither false-rejects it against the kit
    # `[EPIC]`), and validate-issue's reverse read resolves it to `epic`.
    remap = vi.axis_labels.axis_title_prefix_remap("type", brownfield_type_prefix_map)
    assert "[Epic]" in remap.values()
    assert (
        vi.axis_labels.resolve_title_prefix_read(
            "type", "[Epic] x", brownfield_type_prefix_map
        )
        == "epic"
    )

    # The label-remap binding: both agree it is NOT kit-label-served, and
    # validate-issue reads the axis as label-bound (so it demands the remapped
    # label rather than skipping the axis — the G1 fix).
    assert precheck._axis_expects_kit_labels("type", brownfield_type_label_map) is False
    assert (
        vi.axis_labels.axis_is_label_bound("type", brownfield_type_label_map) is True
    )


# --- board membership: unverified is not missing, and not satisfied (#740) ---


_MANDATORY_STATE_BOARD = {
    "required_fields": {
        "board_membership": {"drift_severity": "[validation-severity:warning]"},
    }
}


def _membership_labels(
    vi, issue_types, titles, body_format, board_config, project_items, *, present=True
):
    """Validator output for a board-configured adopter with a given
    `projectItems` payload; returns the finding labels.

    `present=False` omits the key entirely — the shape returned when the field
    could not be resolved at all, distinct from an explicit null. Both are
    undeterminable and neither may be silent.
    """
    issue = _make_issue(
        title="[Task] Wire the sandbox allowlist",
        body=(
            "Feature: #1\n\n"
            "## What\nx\n## Acceptance criteria\n- [ ] x\n## Doc impact\nnone."
        ),
        labels=["type:feature"],
    )
    if present:
        issue["projectItems"] = project_items
    return _labels(
        vi._validate_issue(
            issue=issue,
            issue_types=issue_types,
            titles=titles,
            body_format=body_format,
            config=board_config,
            mandatory_state=_MANDATORY_STATE_BOARD,
        )
    )


def test_board_membership_null_is_unverified_not_silent(
    vi, issue_types, titles, body_format, board_config
) -> None:
    """A null `projectItems` means membership could not be DETERMINED. The old
    condition (`is not None and isinstance(list) and len==0`) skipped the branch,
    so an unreadable board was indistinguishable from a satisfied check — a gate
    that passes on a value it could not read is indistinguishable from a gate
    that does not exist."""
    labels = _membership_labels(vi, issue_types, titles, body_format, board_config, None)
    assert "board_membership.unverified" in labels
    # ...and it must NOT accuse the adopter of an off-board issue.
    assert "board_membership.missing" not in labels


def test_board_membership_absent_key_is_unverified(
    vi, issue_types, titles, body_format, board_config
) -> None:
    """The key omitted entirely (field unresolvable) is the same undeterminable
    state as an explicit null — not satisfied, not missing."""
    labels = _membership_labels(
        vi, issue_types, titles, body_format, board_config, None, present=False
    )
    assert "board_membership.unverified" in labels
    assert "board_membership.missing" not in labels


def test_board_membership_non_list_is_unverified(
    vi, issue_types, titles, body_format, board_config
) -> None:
    """A malformed (non-list) payload is undeterminable, never a definite empty."""
    labels = _membership_labels(
        vi, issue_types, titles, body_format, board_config, {"unexpected": "shape"}
    )
    assert "board_membership.unverified" in labels
    assert "board_membership.missing" not in labels


def test_board_membership_definite_empty_still_reports_missing(
    vi, issue_types, titles, body_format, board_config
) -> None:
    """The determinate case is UNCHANGED: an empty list is a definite answer —
    the issue is not on the board — and keeps reporting `.missing`."""
    labels = _membership_labels(vi, issue_types, titles, body_format, board_config, [])
    assert "board_membership.missing" in labels
    assert "board_membership.unverified" not in labels


def test_board_membership_populated_is_clean(
    vi, issue_types, titles, body_format, board_config
) -> None:
    """A populated list satisfies the check — no membership finding either way."""
    labels = _membership_labels(
        vi, issue_types, titles, body_format, board_config, [{"title": "Board 42"}]
    )
    assert "board_membership.missing" not in labels
    assert "board_membership.unverified" not in labels


def test_board_membership_unverified_is_dec019_severity(
    vi, issue_types, titles, body_format, board_config
) -> None:
    """Reported at DEC-019's OWN drift_severity (warning) — this fix adds no
    severity, no verdict token, no exit-code change. A hard-reject here would
    contradict DEC-019's explicit rationale for warning (historical issues
    predate adoption; blocking them mid-flight is the wrong trade)."""
    issue = _make_issue(
        title="[Task] Wire the sandbox allowlist",
        body=(
            "Feature: #1\n\n"
            "## What\nx\n## Acceptance criteria\n- [ ] x\n## Doc impact\nnone."
        ),
        labels=["type:feature"],
    )
    issue["projectItems"] = None
    findings = vi._validate_issue(
        issue=issue,
        issue_types=issue_types,
        titles=titles,
        body_format=body_format,
        config=board_config,
        mandatory_state=_MANDATORY_STATE_BOARD,
    )
    unverified = [f for f in findings if f.label == "board_membership.unverified"]
    assert len(unverified) == 1
    assert unverified[0].severity == vi.SEVERITY_WARNING


def test_label_only_adopter_gets_no_membership_finding(
    vi, issue_types, titles, body_format, label_fallback_config
) -> None:
    """No board configured ⇒ the branch never runs: label-only adopters see no
    new finding, no new call, no new scope requirement."""
    issue = _make_issue(
        title="[Task] Wire the sandbox allowlist",
        body=(
            "Feature: #1\n\n"
            "## What\nx\n## Acceptance criteria\n- [ ] x\n## Doc impact\nnone."
        ),
        labels=["type:feature", "priority:Medium", "workstream:cli"],
    )
    issue["projectItems"] = None
    labels = _labels(
        vi._validate_issue(
            issue=issue,
            issue_types=issue_types,
            titles=titles,
            body_format=body_format,
            config=label_fallback_config,
            mandatory_state=_MANDATORY_STATE_BOARD,
        )
    )
    assert "board_membership.unverified" not in labels
    assert "board_membership.missing" not in labels


# --- no-board adopter with label-bound priority/workstream (#742) -----------


@pytest.fixture
def brownfield_priority_ws_label_map(vi):
    """A NO-BOARD brownfield map binding priority + workstream to the adopter's
    own labels (their native `P0/P1/P2` and `area/*`), with `type` left on the
    kit label.

    This is the shape that had no coverage and no alarm: `create-issue` wrote
    the REMAPPED label through the write seam while the presence gate demanded
    the kit `priority:*`, and pre-check's substrate-conflict check (#709) skips
    because there is no board.
    """
    return vi.axis_labels.SubstrateMap(
        axes={
            "priority": {"label": {"remap": {"High": "P0", "Medium": "P1", "Low": "P2"}}},
            "workstream": {"label": {"remap": {"cli": "area/cli", "docs": "area/docs"}}},
        }
    )


@pytest.fixture
def brownfield_type_only_map(vi):
    """A present map binding ONLY `type` — priority and workstream are OMITTED.

    Per DEC-036 D2 an omitted axis DEGRADES; it must not fall back to demanding
    kit labels the adopter may be unable to create.
    """
    return vi.axis_labels.SubstrateMap(
        axes={"type": {"label": {"remap": {"feature": "kind/feature", "task": "kind/task"}}}}
    )


def _no_board_labels(
    vi, issue_types, titles, body_format, label_fallback_config, *, labels, substrate_map
):
    issue = _make_issue(
        title="[Task] Wire the sandbox allowlist",
        body=(
            "Feature: #1\n\n"
            "## What\nx\n## Acceptance criteria\n- [ ] x\n## Doc impact\nnone."
        ),
        labels=labels,
    )
    return _labels(
        vi._validate_issue(
            issue=issue,
            issue_types=issue_types,
            titles=titles,
            body_format=body_format,
            config=label_fallback_config,
            substrate_map=substrate_map,
        )
    )


def test_no_board_label_bound_axes_accept_the_remapped_labels(
    vi, issue_types, titles, body_format, label_fallback_config, brownfield_priority_ws_label_map
) -> None:
    """THE BUG (#742): the adopter's own `P1` / `area/cli` — what `create-issue`
    actually writes through the seam — must satisfy the gate. Before the fix the
    gate demanded the kit `priority:*` / `workstream:*`, so the writer and the
    reader disagreed and nothing detected it."""
    found = _no_board_labels(
        vi,
        issue_types,
        titles,
        body_format,
        label_fallback_config,
        labels=["type:feature", "P1", "area/cli"],
        substrate_map=brownfield_priority_ws_label_map,
    )
    assert "classification.priority.missing" not in found
    assert "classification.workstream.missing" not in found


def test_no_board_label_bound_axes_still_refuse_when_absent(
    vi, issue_types, titles, body_format, label_fallback_config, brownfield_priority_ws_label_map
) -> None:
    """The fix must not become a hole: a bound axis with NONE of the adopter's
    remapped labels is a genuine missing value — hard-reject, exactly as
    greenfield gates a missing kit label."""
    found = _no_board_labels(
        vi,
        issue_types,
        titles,
        body_format,
        label_fallback_config,
        labels=["type:feature"],
        substrate_map=brownfield_priority_ws_label_map,
    )
    assert "classification.priority.missing" in found
    assert "classification.workstream.missing" in found


def test_no_board_label_bound_does_not_demand_the_kit_label(
    vi, issue_types, titles, body_format, label_fallback_config, brownfield_priority_ws_label_map
) -> None:
    """The kit prefix is no longer demanded for a bound axis — the message must
    name the adopter's remap, not `priority:*`, so the diagnosis points at the
    substrate that actually carries the axis."""
    issue = _make_issue(
        title="[Task] Wire the sandbox allowlist",
        body=(
            "Feature: #1\n\n"
            "## What\nx\n## Acceptance criteria\n- [ ] x\n## Doc impact\nnone."
        ),
        labels=["type:feature"],
    )
    findings = vi._validate_issue(
        issue=issue,
        issue_types=issue_types,
        titles=titles,
        body_format=body_format,
        config=label_fallback_config,
        substrate_map=brownfield_priority_ws_label_map,
    )
    detail = next(
        f.detail for f in findings if f.label == "classification.priority.missing"
    )
    assert "substrate-map.yaml" in detail
    assert "priority:*" not in detail


def test_no_board_omitted_axis_degrades_not_kit_fallback(
    vi, issue_types, titles, body_format, label_fallback_config, brownfield_type_only_map
) -> None:
    """DEC-036 D2: an axis OMITTED from a present map degrades — it must not
    fall back to demanding kit labels the adopter may be unable to create. The
    old code demanded them, which is the same hazard D2 exists to prevent."""
    found = _no_board_labels(
        vi,
        issue_types,
        titles,
        body_format,
        label_fallback_config,
        labels=["kind/task"],
        substrate_map=brownfield_type_only_map,
    )
    assert "classification.priority.missing" not in found
    assert "classification.workstream.missing" not in found


def test_greenfield_no_board_behaviour_is_unchanged(
    vi, issue_types, titles, body_format, label_fallback_config
) -> None:
    """No map at all ⇒ byte-unchanged: kit labels demanded, same findings."""
    missing = _no_board_labels(
        vi,
        issue_types,
        titles,
        body_format,
        label_fallback_config,
        labels=["type:feature"],
        substrate_map=None,
    )
    assert "classification.priority.missing" in missing
    assert "classification.workstream.missing" in missing
    clean = _no_board_labels(
        vi,
        issue_types,
        titles,
        body_format,
        label_fallback_config,
        labels=["type:feature", "priority:Medium", "workstream:cli"],
        substrate_map=None,
    )
    assert "classification.priority.missing" not in clean
    assert "classification.workstream.missing" not in clean


def test_greenfield_multiple_kit_labels_still_reported(
    vi, issue_types, titles, body_format, label_fallback_config
) -> None:
    """The multiplicity check survives the refactor for the greenfield arm."""
    found = _no_board_labels(
        vi,
        issue_types,
        titles,
        body_format,
        label_fallback_config,
        labels=["type:feature", "priority:High", "priority:Low", "workstream:cli"],
        substrate_map=None,
    )
    assert "classification.priority.multiple" in found
