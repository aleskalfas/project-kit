"""Unit tests for the _lib/placeholder_detection helper (DEC-031).

Tests cover:

- ``extract_placeholder_phrases`` — template fingerprint extraction
- ``has_filled_checkbox_items`` — filled-item detection per section
- ``detect_placeholder_residuals`` — public API, both signals, both phases
"""

from __future__ import annotations

import sys
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
LIB_PATH = (
    REPO_ROOT
    / ".pkit"
    / "capabilities"
    / "project-management"
    / "scripts"
)
CAPABILITY_ROOT = REPO_ROOT / ".pkit" / "capabilities" / "project-management"

sys.path.insert(0, str(LIB_PATH))

from _lib.placeholder_detection import (  # noqa: E402
    PHASE_CREATE,
    PHASE_TRANSITION,
    detect_placeholder_residuals,
    extract_placeholder_phrases,
    has_filled_checkbox_items,
)


# ---- extract_placeholder_phrases ------------------------------------


def test_extract_phrases_returns_prose_lines(tmp_path: Path) -> None:
    """Prose lines that are not headings, checkboxes, or blank are returned."""
    template = tmp_path / "Task.md"
    template.write_text(
        textwrap.dedent("""\
            ## What

            The concrete change being made.

            ## Acceptance criteria

            - [ ]
            - [ ]
        """),
        encoding="utf-8",
    )
    phrases = extract_placeholder_phrases(template)
    assert "The concrete change being made." in phrases
    # Headings are excluded.
    assert "## What" not in phrases
    assert "## Acceptance criteria" not in phrases
    # Checkbox lines are excluded.
    assert "- [ ]" not in phrases


def test_extract_phrases_strips_html_comments(tmp_path: Path) -> None:
    """HTML comment blocks are removed before phrase extraction."""
    template = tmp_path / "Task.md"
    template.write_text(
        textwrap.dedent("""\
            ## What

            The concrete change being made.

            <!--
            This is an instructional comment.
            It should not appear in phrases.
            -->

            - [ ]
        """),
        encoding="utf-8",
    )
    phrases = extract_placeholder_phrases(template)
    assert "The concrete change being made." in phrases
    assert "This is an instructional comment." not in phrases
    assert "It should not appear in phrases." not in phrases


def test_extract_phrases_strips_frontmatter(tmp_path: Path) -> None:
    """YAML front-matter is stripped before phrase extraction."""
    template = tmp_path / "Task.md"
    template.write_text(
        textwrap.dedent("""\
            ---
            name: Task
            title: '[Task] '
            ---

            ## What

            The concrete change being made.
        """),
        encoding="utf-8",
    )
    phrases = extract_placeholder_phrases(template)
    assert "The concrete change being made." in phrases
    # Front-matter values must not appear.
    assert "name: Task" not in phrases
    assert "title: '[Task] '" not in phrases


def test_extract_phrases_excludes_parent_ref_placeholder(tmp_path: Path) -> None:
    """Parent-ref placeholder lines like ``Feature: #`` are excluded."""
    template = tmp_path / "Task.md"
    template.write_text(
        textwrap.dedent("""\
            Feature: #

            ## What

            The concrete change being made.
        """),
        encoding="utf-8",
    )
    phrases = extract_placeholder_phrases(template)
    assert "Feature: #" not in phrases
    assert "The concrete change being made." in phrases


def test_extract_phrases_nonexistent_template(tmp_path: Path) -> None:
    """A non-existent template path returns an empty list without error."""
    phrases = extract_placeholder_phrases(tmp_path / "Nonexistent.md")
    assert phrases == []


# ---- has_filled_checkbox_items --------------------------------------


def test_has_filled_items_true_with_checked_box() -> None:
    body = "## Acceptance criteria\n- [x] Something done.\n- [ ] Todo.\n"
    assert has_filled_checkbox_items(body, "## Acceptance criteria") is True


def test_has_filled_items_true_with_uppercase_x() -> None:
    body = "## Acceptance criteria\n- [X] Done.\n"
    assert has_filled_checkbox_items(body, "## Acceptance criteria") is True


def test_has_filled_items_false_all_empty() -> None:
    body = "## Acceptance criteria\n- [ ]\n- [ ]\n"
    assert has_filled_checkbox_items(body, "## Acceptance criteria") is False


def test_has_filled_items_false_missing_section() -> None:
    body = "## What\nSomething.\n"
    assert has_filled_checkbox_items(body, "## Acceptance criteria") is False


def test_has_filled_items_does_not_bleed_across_sections() -> None:
    """Filled items in a later section do not affect an earlier section's result."""
    body = (
        "## Acceptance criteria\n"
        "- [ ]\n"
        "## Doc impact\n"
        "- [x] Updated README.\n"
    )
    # Acceptance criteria section has zero filled items.
    assert has_filled_checkbox_items(body, "## Acceptance criteria") is False
    # Doc impact section has a filled item.
    assert has_filled_checkbox_items(body, "## Doc impact") is True


# ---- detect_placeholder_residuals — public API ----------------------


@pytest.fixture
def body_format_task() -> dict:
    return {
        "bodies": {
            "task": {
                "required_sections": [
                    {
                        "heading": "## What",
                        "has_checkboxes": False,
                        "severity": "[validation-severity:hard-reject]",
                        "purpose": "What",
                    },
                    {
                        "heading": "## Acceptance criteria",
                        "has_checkboxes": True,
                        "severity": "[validation-severity:hard-reject]",
                        "purpose": "Criteria",
                    },
                    {
                        "heading": "## Doc impact",
                        "has_checkboxes": False,
                        "severity": "[validation-severity:hard-reject]",
                        "purpose": "Docs",
                    },
                ],
            },
        },
    }


def _authored_task_body() -> str:
    return (
        "Feature: #1\n\n"
        "## What\n"
        "Implement the frobnication layer.\n\n"
        "## Acceptance criteria\n"
        "- [x] The frobnication layer is installed.\n\n"
        "## Doc impact\n"
        "No doc impact: internal refactor only.\n"
    )


def _skeleton_task_body() -> str:
    """Body stamped verbatim from the Task template (unedited)."""
    return (
        "Feature: #1\n\n"
        "## What\n"
        "The concrete change being made. Outcome-focused, not implementation-focused.\n\n"
        "## Acceptance criteria\n"
        "- [ ]\n"
        "- [ ]\n\n"
        "## Doc impact\n"
        "- [ ]\n"
    )


def test_authored_body_produces_no_findings(body_format_task: dict) -> None:
    """A fully authored body with filled items and no placeholder prose is clean."""
    results = detect_placeholder_residuals(
        body=_authored_task_body(),
        structural_type="task",
        body_format=body_format_task,
        capability_root=CAPABILITY_ROOT,
        phase=PHASE_TRANSITION,
    )
    assert results == [], f"unexpected findings: {results}"


def test_skeleton_body_hard_rejects_at_transition(body_format_task: dict) -> None:
    """A skeleton body emits a hard-reject for the empty checkbox section at transition."""
    results = detect_placeholder_residuals(
        body=_skeleton_task_body(),
        structural_type="task",
        body_format=body_format_task,
        capability_root=CAPABILITY_ROOT,
        phase=PHASE_TRANSITION,
    )
    labels = [label for _, label, _ in results]
    assert "body.placeholder.empty-checkbox-section" in labels
    cb_findings = [r for r in results if r[1] == "body.placeholder.empty-checkbox-section"]
    assert all(sev == "hard-reject" for sev, _, _ in cb_findings)


def test_skeleton_body_warns_at_create(body_format_task: dict) -> None:
    """A skeleton body emits only warnings at create phase."""
    results = detect_placeholder_residuals(
        body=_skeleton_task_body(),
        structural_type="task",
        body_format=body_format_task,
        capability_root=CAPABILITY_ROOT,
        phase=PHASE_CREATE,
    )
    labels = [label for _, label, _ in results]
    assert "body.placeholder.empty-checkbox-section" in labels
    cb_findings = [r for r in results if r[1] == "body.placeholder.empty-checkbox-section"]
    assert all(sev == "warning" for sev, _, _ in cb_findings)


def test_surviving_placeholder_prose_is_always_warning(body_format_task: dict) -> None:
    """Placeholder prose warning fires regardless of phase."""
    body = (
        "Feature: #1\n\n"
        "## What\n"
        "The concrete change being made. Outcome-focused, not implementation-focused.\n\n"
        "## Acceptance criteria\n"
        "- [x] Real criterion.\n\n"
        "## Doc impact\n"
        "No doc impact: internal refactor only.\n"
    )
    for phase in (PHASE_CREATE, PHASE_TRANSITION):
        results = detect_placeholder_residuals(
            body=body,
            structural_type="task",
            body_format=body_format_task,
            capability_root=CAPABILITY_ROOT,
            phase=phase,
        )
        prose_findings = [r for r in results if r[1] == "body.placeholder.template-prose"]
        assert prose_findings, f"expected prose warning at phase={phase!r}"
        assert all(sev == "warning" for sev, _, _ in prose_findings)


def test_lenient_trailing_empty_alongside_filled_passes(body_format_task: dict) -> None:
    """A section with at least one filled item does not trigger empty-checkbox signal."""
    body = (
        "Feature: #1\n\n"
        "## What\n"
        "Implement the frobnication layer.\n\n"
        "## Acceptance criteria\n"
        "- [x] Main criterion satisfied.\n"
        "- [ ] Leftover empty.\n\n"
        "## Doc impact\n"
        "No doc impact: internal refactor only.\n"
    )
    results = detect_placeholder_residuals(
        body=body,
        structural_type="task",
        body_format=body_format_task,
        capability_root=CAPABILITY_ROOT,
        phase=PHASE_TRANSITION,
    )
    cb_findings = [r for r in results if r[1] == "body.placeholder.empty-checkbox-section"]
    assert cb_findings == [], f"unexpected findings: {cb_findings}"


def test_missing_template_produces_no_prose_finding(
    tmp_path: Path, body_format_task: dict
) -> None:
    """When the template file does not exist the prose check silently skips."""
    # Use tmp_path as capability_root — templates/ directory won't exist.
    results = detect_placeholder_residuals(
        body=_skeleton_task_body(),
        structural_type="task",
        body_format=body_format_task,
        capability_root=tmp_path,
        phase=PHASE_TRANSITION,
    )
    prose_findings = [r for r in results if r[1] == "body.placeholder.template-prose"]
    assert prose_findings == []


def test_no_finding_when_section_missing_from_body(body_format_task: dict) -> None:
    """When the checkbox section heading is absent the check is skipped (no double-report)."""
    # Body is entirely missing the "## Acceptance criteria" section.
    body = (
        "Feature: #1\n\n"
        "## What\n"
        "Implement the frobnication layer.\n\n"
        "## Doc impact\n"
        "No doc impact: internal refactor only.\n"
    )
    results = detect_placeholder_residuals(
        body=body,
        structural_type="task",
        body_format=body_format_task,
        capability_root=CAPABILITY_ROOT,
        phase=PHASE_TRANSITION,
    )
    # The empty-checkbox signal must not fire when the section itself is absent
    # (the required-section check is the one that fires for that case).
    cb_findings = [r for r in results if r[1] == "body.placeholder.empty-checkbox-section"]
    assert cb_findings == []


def test_partial_but_real_body_passes(body_format_task: dict) -> None:
    """A partial but genuinely authored body (some criteria filled) passes the checkbox gate."""
    body = (
        "Feature: #1\n\n"
        "## What\n"
        "Implement the first phase of frobnication.\n\n"
        "## Acceptance criteria\n"
        "- [x] Phase 1 complete.\n\n"
        "## Doc impact\n"
        "No doc impact: scope is internal.\n"
    )
    results = detect_placeholder_residuals(
        body=body,
        structural_type="task",
        body_format=body_format_task,
        capability_root=CAPABILITY_ROOT,
        phase=PHASE_TRANSITION,
    )
    assert results == [], f"unexpected findings: {results}"
