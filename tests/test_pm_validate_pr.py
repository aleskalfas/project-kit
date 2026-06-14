"""Tests for project-management's validate-pr script's pure logic.

Covers title-pattern checks, closing-keyword detection, doc-impact
detection, type-vs-label cross-check, and residual-placeholder
detection per DEC-031.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = (
    REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"
)
SCRIPT_PATH = SCRIPTS_DIR / "validate-pr.py"

# Ensure _lib is importable for direct imports in test bodies.
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


@pytest.fixture(scope="module")
def vp():
    module_name = "pm_validate_pr_under_test"
    spec = importlib.util.spec_from_file_location(module_name, SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def titles() -> dict:
    return {
        "formats": {
            "pr": {
                "pattern": r"^(feat|fix|docs|test|refactor|chore|ci)(\([^)]+\))?: .+$",
            },
        },
    }


@pytest.fixture
def classification() -> dict:
    return {
        "pr_type_mapping": [
            {"issue_label_value": "feature", "pr_conv_type": "feat"},
            {"issue_label_value": "bug", "pr_conv_type": "fix"},
            {"issue_label_value": "docs", "pr_conv_type": "docs"},
            {
                "issue_label_value": "maintenance",
                "pr_conv_type": "chore",
                "alternates": ["ci"],
            },
        ],
    }


@pytest.fixture
def git_conv() -> dict:
    return {}


def _labels(findings) -> list[str]:
    return [f.label for f in findings]


# --- valid PR --------------------------------------------------------


def test_valid_pr_no_findings(vp, titles, classification, git_conv) -> None:
    findings = vp._validate_pr(
        pr_title="feat(cli): add new dispatcher",
        pr_body="Closes #42\n\n## Summary\nfoo\n\n## Doc impact\nupdated README.",
        titles=titles,
        classification=classification,
        git_conv=git_conv,
        closing_type_labels=["type:feature"],
    )
    assert findings == []


# --- title pattern ---------------------------------------------------


def test_invalid_title_pattern_is_hard_reject(
    vp, titles, classification, git_conv
) -> None:
    findings = vp._validate_pr(
        pr_title="Sandbox: add CLI",
        pr_body="Closes #1\n\n## Doc impact\nnone.",
        titles=titles,
        classification=classification,
        git_conv=git_conv,
        closing_type_labels=[],
    )
    assert "title.pattern" in _labels(findings)


def test_title_type_mismatch_is_hard_reject(
    vp, titles, classification, git_conv
) -> None:
    findings = vp._validate_pr(
        pr_title="feat(cli): add dispatcher",
        pr_body="Closes #1\n\n## Doc impact\nnone.",
        titles=titles,
        classification=classification,
        git_conv=git_conv,
        closing_type_labels=["type:bug"],
    )
    assert "title.type-mismatch" in _labels(findings)


def test_title_type_match_passes(
    vp, titles, classification, git_conv
) -> None:
    findings = vp._validate_pr(
        pr_title="fix(tui): correct off-by-one",
        pr_body="Closes #5\n\n## Doc impact\nnone.",
        titles=titles,
        classification=classification,
        git_conv=git_conv,
        closing_type_labels=["type:bug"],
    )
    assert "title.type-mismatch" not in _labels(findings)


def test_title_type_alternates_accepted(
    vp, titles, classification, git_conv
) -> None:
    """`ci` is an alternate to chore for type:maintenance."""
    findings = vp._validate_pr(
        pr_title="ci: bump runner version",
        pr_body="Closes #1\n\n## Doc impact\nnone.",
        titles=titles,
        classification=classification,
        git_conv=git_conv,
        closing_type_labels=["type:maintenance"],
    )
    assert "title.type-mismatch" not in _labels(findings)


def test_multi_issue_type_mismatch_is_warning(
    vp, titles, classification, git_conv
) -> None:
    """Mixed closing-issue types degrade the mismatch from hard-reject to warning."""
    findings = vp._validate_pr(
        pr_title="feat(cli): add dispatcher",
        pr_body="Closes #1, closes #2\n\n## Doc impact\nnone.",
        titles=titles,
        classification=classification,
        git_conv=git_conv,
        closing_type_labels=["type:bug", "type:docs"],
    )
    type_mismatch = [f for f in findings if f.label == "title.type-mismatch"]
    assert len(type_mismatch) == 1
    assert type_mismatch[0].severity == "warning"


# --- body rules ------------------------------------------------------


def test_missing_closes_keyword_is_hard_reject(
    vp, titles, classification, git_conv
) -> None:
    findings = vp._validate_pr(
        pr_title="feat: add thing",
        pr_body="## Summary\nfoo\n\n## Doc impact\nnone.",
        titles=titles,
        classification=classification,
        git_conv=git_conv,
        closing_type_labels=[],
    )
    assert "body.closes" in _labels(findings)


def test_missing_doc_impact_is_hard_reject(
    vp, titles, classification, git_conv
) -> None:
    findings = vp._validate_pr(
        pr_title="feat: add thing",
        pr_body="Closes #1\n\n## Summary\nfoo.",
        titles=titles,
        classification=classification,
        git_conv=git_conv,
        closing_type_labels=["type:feature"],
    )
    assert "body.doc-impact" in _labels(findings)


# --- expected types --------------------------------------------------


def test_expected_conv_types_lists_mapped_value(vp, classification) -> None:
    assert vp._expected_conv_types(["type:feature"], classification) == ["feat"]


def test_expected_conv_types_includes_alternates(vp, classification) -> None:
    out = vp._expected_conv_types(["type:maintenance"], classification)
    assert "chore" in out
    assert "ci" in out


def test_expected_conv_types_empty_for_unknown_label(vp, classification) -> None:
    assert vp._expected_conv_types(["type:bogus"], classification) == []


# --- closing-issue extraction ---------------------------------------


def test_extract_closes_simple(vp) -> None:
    assert vp._extract_closing_issues("Closes #42") == [42]


def test_extract_dedupes(vp) -> None:
    assert vp._extract_closing_issues("Closes #1\nFixes #1") == [1]


def test_extract_returns_empty_when_no_keyword(vp) -> None:
    assert vp._extract_closing_issues("plain body") == []


# --- placeholder detection (DEC-031) ---------------------------------

CAPABILITY_ROOT = (
    REPO_ROOT / ".pkit" / "capabilities" / "project-management"
)


def _authored_pr_body() -> str:
    """A PR body that has been fully authored (no skeleton residuals)."""
    return (
        "Closes #42\n\n"
        "## Summary\n\n"
        "Implement the frobnication subsystem per the design.\n\n"
        "## Test plan\n\n"
        "- [ ] Unit tests pass under `uv run pytest`.\n"
        "- [ ] Integration smoke-test runs clean.\n\n"
        "## Doc impact\n\n"
        "Updated README.md install section.\n"
    )


def _skeleton_pr_body() -> str:
    """A PR body still carrying the raw PR.md skeleton."""
    return (
        "Closes #\n\n"
        "## Summary\n\n"
        "<!-- 1–3 paragraphs: the why and how. -->\n\n"
        "## Test plan\n\n"
        "- [ ]\n\n"
        "## Doc impact\n\n"
        "-\n"
    )


def test_authored_pr_body_no_placeholder_findings(
    vp, titles, classification, git_conv
) -> None:
    """A fully authored PR body produces no placeholder findings."""
    from _lib.placeholder_detection import PHASE_CREATE, PHASE_TRANSITION
    for phase in (PHASE_CREATE, PHASE_TRANSITION):
        findings = vp._validate_pr(
            pr_title="feat(pm): implement frobnication",
            pr_body=_authored_pr_body(),
            titles=titles,
            classification=classification,
            git_conv=git_conv,
            closing_type_labels=["type:feature"],
            capability_root=CAPABILITY_ROOT,
            phase=phase,
        )
        placeholder_findings = [
            f for f in findings
            if f.label.startswith("body.placeholder.")
        ]
        assert placeholder_findings == [], (
            f"unexpected placeholder findings at phase={phase!r}: "
            f"{placeholder_findings}"
        )


def test_skeleton_pr_body_warns_at_open(
    vp, titles, classification, git_conv
) -> None:
    """At create/open phase an empty ## Test plan section is a warning (not hard-reject)."""
    from _lib.placeholder_detection import PHASE_CREATE
    findings = vp._validate_pr(
        pr_title="feat(pm): skeleton pr",
        pr_body=(
            "Closes #1\n\n"
            "## Summary\n\nfoo\n\n"
            "## Test plan\n\n- [ ]\n\n"
            "## Doc impact\n\nnone.\n"
        ),
        titles=titles,
        classification=classification,
        git_conv=git_conv,
        closing_type_labels=["type:feature"],
        capability_root=CAPABILITY_ROOT,
        phase=PHASE_CREATE,
    )
    cb_findings = [
        f for f in findings
        if f.label == "body.placeholder.empty-checkbox-section"
    ]
    assert cb_findings, "expected empty-checkbox-section warning at open phase"
    assert all(f.severity == "warning" for f in cb_findings), (
        f"expected warning severity at open, got: {cb_findings}"
    )


def test_skeleton_pr_body_hard_rejects_at_merge_gate(
    vp, titles, classification, git_conv
) -> None:
    """At transition/merge-gate phase an empty ## Test plan section is a hard-reject."""
    from _lib.placeholder_detection import PHASE_TRANSITION
    findings = vp._validate_pr(
        pr_title="feat(pm): skeleton pr",
        pr_body=(
            "Closes #1\n\n"
            "## Summary\n\nfoo\n\n"
            "## Test plan\n\n- [ ]\n\n"
            "## Doc impact\n\nnone.\n"
        ),
        titles=titles,
        classification=classification,
        git_conv=git_conv,
        closing_type_labels=["type:feature"],
        capability_root=CAPABILITY_ROOT,
        phase=PHASE_TRANSITION,
    )
    cb_findings = [
        f for f in findings
        if f.label == "body.placeholder.empty-checkbox-section"
    ]
    assert cb_findings, "expected empty-checkbox-section hard-reject at merge gate"
    assert all(f.severity == "hard-reject" for f in cb_findings), (
        f"expected hard-reject severity at merge gate, got: {cb_findings}"
    )


def test_authored_but_unticked_pr_body_no_false_positive(
    vp, titles, classification, git_conv
) -> None:
    """Regression: authored but unchecked ## Test plan items must NOT be flagged.

    An unchecked checkbox with real text (e.g. '- [ ] Run the test suite')
    is authored. Checking for authorship must be checked-state-independent.
    """
    from _lib.placeholder_detection import PHASE_TRANSITION
    body = (
        "Closes #7\n\n"
        "## Summary\n\nReplace the widget factory with a new impl.\n\n"
        "## Test plan\n\n"
        "- [ ] Run the test suite with `uv run pytest`.\n"
        "- [ ] Manual smoke test the widget creation flow.\n\n"
        "## Doc impact\n\nNone — internal refactor only.\n"
    )
    findings = vp._validate_pr(
        pr_title="refactor(widget): replace factory",
        pr_body=body,
        titles=titles,
        classification=classification,
        git_conv=git_conv,
        closing_type_labels=["type:refactor"],
        capability_root=CAPABILITY_ROOT,
        phase=PHASE_TRANSITION,
    )
    cb_findings = [
        f for f in findings
        if f.label == "body.placeholder.empty-checkbox-section"
    ]
    assert cb_findings == [], (
        "authored-but-unticked PR body falsely flagged as skeleton: "
        f"{cb_findings}"
    )


def test_no_capability_root_no_placeholder_check(
    vp, titles, classification, git_conv
) -> None:
    """When capability_root is None the placeholder check is skipped gracefully."""
    from _lib.placeholder_detection import PHASE_TRANSITION
    body = (
        "Closes #1\n\n"
        "## Summary\n\nfoo\n\n"
        "## Test plan\n\n- [ ]\n\n"
        "## Doc impact\n\nnone.\n"
    )
    findings = vp._validate_pr(
        pr_title="feat: add thing",
        pr_body=body,
        titles=titles,
        classification=classification,
        git_conv=git_conv,
        closing_type_labels=["type:feature"],
        capability_root=None,
        phase=PHASE_TRANSITION,
    )
    placeholder_findings = [
        f for f in findings if f.label.startswith("body.placeholder.")
    ]
    assert placeholder_findings == [], (
        "placeholder check must be skipped when capability_root is None"
    )
