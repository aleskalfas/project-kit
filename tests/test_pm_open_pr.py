"""Tests for project-management's open-pr script's pure logic.

Covers issue-number extraction, type derivation, summary derivation,
branch-pattern lookup, body template substitution.
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
    / "open-pr.py"
)


@pytest.fixture(scope="module")
def op():
    module_name = "pm_open_pr_under_test"
    spec = importlib.util.spec_from_file_location(module_name, SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def classification() -> dict:
    return {
        "pr_type_mapping": [
            {"issue_label_value": "feature", "pr_conv_type": "feat"},
            {"issue_label_value": "bug", "pr_conv_type": "fix"},
            {"issue_label_value": "docs", "pr_conv_type": "docs"},
            {"issue_label_value": "test", "pr_conv_type": "test"},
            {"issue_label_value": "refactor", "pr_conv_type": "refactor"},
            {"issue_label_value": "maintenance", "pr_conv_type": "chore"},
        ],
    }


@pytest.fixture
def git_conventions() -> dict:
    return {
        "conventions": {
            "branch-name": {
                "pattern": r"^(feat|fix|docs|test|refactor|chore|ci)/[0-9]+-[a-z0-9][a-z0-9-]*$",
            },
        },
    }


# --- branch pattern extraction ---------------------------------------


def test_branch_pattern_returns_declared(op, git_conventions) -> None:
    p = op._branch_pattern(git_conventions)
    assert p == r"^(feat|fix|docs|test|refactor|chore|ci)/[0-9]+-[a-z0-9][a-z0-9-]*$"


def test_branch_pattern_returns_none_when_missing(op) -> None:
    assert op._branch_pattern({}) is None


# --- issue number extraction -----------------------------------------


def test_extract_issue_number_recognises_branch_form(op) -> None:
    assert op._extract_issue_number("feat/99-install-cli") == 99
    assert op._extract_issue_number("fix/77-render-tui") == 77
    assert op._extract_issue_number("chore/3-bump-deps") == 3


def test_extract_issue_number_returns_none_for_unconforming(op) -> None:
    assert op._extract_issue_number("main") is None
    assert op._extract_issue_number("install-cli") is None
    assert op._extract_issue_number("feat/install-cli") is None


# --- conv-type derivation --------------------------------------------


def test_conv_type_from_feature_label(op, classification) -> None:
    assert op._conv_type_from_issue_labels(["type:feature"], classification) == "feat"


def test_conv_type_from_bug_label(op, classification) -> None:
    assert op._conv_type_from_issue_labels(["type:bug"], classification) == "fix"


def test_conv_type_from_maintenance_label_picks_chore(op, classification) -> None:
    assert (
        op._conv_type_from_issue_labels(["type:maintenance"], classification)
        == "chore"
    )


def test_conv_type_returns_none_when_no_type_label(op, classification) -> None:
    assert op._conv_type_from_issue_labels(["priority:Medium"], classification) is None


def test_conv_type_uses_first_type_label_when_multiple(op, classification) -> None:
    # Multiple type labels is a validation error elsewhere; we don't
    # enforce here, but be deterministic.
    assert (
        op._conv_type_from_issue_labels(["type:bug", "type:feature"], classification)
        == "fix"
    )


# --- summary derivation ----------------------------------------------


def test_summary_strips_type_prefix_and_lowercases(op) -> None:
    title = "[Task] Install the Claude Code CLI inside the sandbox"
    assert op._summary_from_issue_title(title) == (
        "install the claude code cli inside the sandbox"
    )


def test_summary_strips_trailing_period(op) -> None:
    title = "[Task] Render TUI cleanly."
    assert op._summary_from_issue_title(title) == "render tui cleanly"


def test_summary_handles_title_without_prefix(op) -> None:
    title = "no bracket prefix"
    # Should still lowercase, even without a prefix to strip.
    assert op._summary_from_issue_title(title) == "no bracket prefix"


# --- HTML comment stripping ------------------------------------------


def test_strip_html_comments_removes_single_line_comment(op) -> None:
    text = "before\n<!-- comment -->\nafter"
    assert "comment" not in op._strip_html_comments(text)


def test_strip_html_comments_removes_multi_line_comment(op) -> None:
    text = "before\n<!--\n  multi line\n  comment\n-->\nafter"
    result = op._strip_html_comments(text)
    assert "multi line" not in result
    assert "before" in result
    assert "after" in result


def test_strip_html_comments_preserves_uncommented_text(op) -> None:
    text = "plain text without comments"
    assert op._strip_html_comments(text) == text


# --- body template substitution --------------------------------------


def test_build_pr_body_fills_closes_placeholder(op, tmp_path) -> None:
    template_dir = tmp_path / "templates"
    template_dir.mkdir()
    (template_dir / "PR.md").write_text(
        "Closes #\n\n## Summary\n\n## Test plan\n", encoding="utf-8"
    )
    body = op._build_pr_body(
        capability_root=tmp_path, issue_number=42, body_file=None
    )
    assert body is not None
    assert "Closes #42" in body


def test_build_pr_body_user_supplied_file(op, tmp_path) -> None:
    f = tmp_path / "custom.md"
    f.write_text("user-supplied body\n", encoding="utf-8")
    body = op._build_pr_body(
        capability_root=tmp_path, issue_number=42, body_file=f
    )
    assert body == "user-supplied body\n"


def test_build_pr_body_fallback_when_no_template(op, tmp_path) -> None:
    body = op._build_pr_body(
        capability_root=tmp_path, issue_number=42, body_file=None
    )
    assert body == "Closes #42\n"


def test_build_pr_body_template_without_closes_placeholder(op, tmp_path) -> None:
    template_dir = tmp_path / "templates"
    template_dir.mkdir()
    (template_dir / "PR.md").write_text("## Summary\n\nfoo\n", encoding="utf-8")
    body = op._build_pr_body(
        capability_root=tmp_path, issue_number=99, body_file=None
    )
    assert body is not None
    assert "Closes #99" in body
