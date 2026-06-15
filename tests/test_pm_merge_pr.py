"""Tests for project-management's merge-pr script's pure logic.

Covers closing-issue extraction, checkbox detection, PR-title pattern
lookup.
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
    / "merge-pr.py"
)


@pytest.fixture(scope="module")
def mp():
    module_name = "pm_merge_pr_under_test"
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


# --- closing-issue extraction ---------------------------------------


def test_extract_closes_single(mp) -> None:
    body = "Closes #42\n\n## Summary"
    assert mp._extract_closing_issues(body) == [42]


def test_extract_fixes_single(mp) -> None:
    body = "Fixes #99"
    assert mp._extract_closing_issues(body) == [99]


def test_extract_resolves_single(mp) -> None:
    body = "Resolves #100"
    assert mp._extract_closing_issues(body) == [100]


def test_extract_multiple_keywords(mp) -> None:
    body = "Closes #42, closes #43\nFixes #44"
    result = mp._extract_closing_issues(body)
    assert sorted(result) == [42, 43, 44]


def test_extract_dedupes_repeated_numbers(mp) -> None:
    body = "Closes #42\nFixes #42\nResolves #42"
    assert mp._extract_closing_issues(body) == [42]


def test_extract_returns_empty_when_no_keyword(mp) -> None:
    assert mp._extract_closing_issues("body without keyword") == []


def test_extract_handles_empty_body(mp) -> None:
    assert mp._extract_closing_issues("") == []


def test_extract_case_insensitive(mp) -> None:
    body = "CLOSES #1\nfixes #2\nResolves #3"
    assert sorted(mp._extract_closing_issues(body)) == [1, 2, 3]


# --- unticked-box detection ------------------------------------------


def test_unticked_boxes_detects_dash_style(mp) -> None:
    body = "- [ ] First\n- [x] Second\n- [ ] Third"
    assert len(mp._unticked_boxes(body)) == 2


def test_unticked_boxes_handles_indentation(mp) -> None:
    body = "  - [ ] one\n    - [ ] two\n- [x] three"
    assert len(mp._unticked_boxes(body)) == 2


def test_unticked_boxes_returns_empty_for_ticked(mp) -> None:
    body = "- [x] Done\n- [x] Also done"
    assert mp._unticked_boxes(body) == []


def test_unticked_boxes_returns_empty_for_no_boxes(mp) -> None:
    body = "## Plain prose section with no checkboxes."
    assert mp._unticked_boxes(body) == []


# --- pr title pattern ------------------------------------------------


def test_pr_title_pattern_returns_declared(mp, titles) -> None:
    p = mp._pr_title_pattern(titles)
    assert p == r"^(feat|fix|docs|test|refactor|chore|ci)(\([^)]+\))?: .+$"


def test_pr_title_pattern_returns_none_when_missing(mp) -> None:
    assert mp._pr_title_pattern({}) is None


def test_pr_title_pattern_matches_valid_titles(mp, titles) -> None:
    import re

    pattern = mp._pr_title_pattern(titles)
    assert re.match(pattern, "feat(cli): add new dispatcher")
    assert re.match(pattern, "fix: address regression")
    assert re.match(pattern, "docs(readme): update install")


def test_pr_title_pattern_rejects_invalid_titles(mp, titles) -> None:
    import re

    pattern = mp._pr_title_pattern(titles)
    assert re.match(pattern, "Sandbox: install CLI") is None
    assert re.match(pattern, "[Task] add CLI") is None


# --- squash-merge subject regression (issue #33) ---------------------


def test_gh_merge_uses_pr_title_as_subject(mp, monkeypatch) -> None:
    """_gh_merge passes --subject <PR title> to `gh pr merge --squash`.

    Regression for #33: GitHub defaults the squash subject to the commit
    message for single-commit PRs, defeating the PR-title type-alignment gate
    (DEC-013).  The --subject flag locks the landed subject to the PR title.
    """
    import subprocess

    captured: list[list[str]] = []

    def fake_run(args, **kwargs):
        captured.append(list(args))
        return subprocess.CompletedProcess(
            args=args, returncode=0, stdout="", stderr="",
        )

    monkeypatch.setattr(mp.subprocess, "run", fake_run)
    result = mp._gh_merge(
        99,
        pr_title="fix(pm-scripts): squash subject uses PR title",
        admin=False,
        config={},
    )

    assert result is True
    assert captured, "Expected subprocess.run to be called"
    argv = captured[0]
    assert "--squash" in argv
    assert "--subject" in argv, "--subject must be present so the landed commit subject equals the PR title"
    subject_idx = argv.index("--subject")
    assert argv[subject_idx + 1] == "fix(pm-scripts): squash subject uses PR title", (
        f"--subject value must be the PR title; got {argv[subject_idx + 1]!r}"
    )


def test_gh_merge_subject_not_commit_message(mp, monkeypatch) -> None:
    """For a single-commit PR the squash subject must be the PR title, not the commit message.

    Simulates the live bug (PR #32): the commit carried 'feat(...)' but the PR
    title was 'fix(...)'.  Asserts that _gh_merge passes the PR title argument
    verbatim and not any commit-derived subject.
    """
    import subprocess

    pr_title = "fix(pm-permissions): correct enforcement runtime"
    commit_subject = "feat(pm-permissions): implement runtime enforcement"

    captured: list[list[str]] = []

    def fake_run(args, **kwargs):
        captured.append(list(args))
        return subprocess.CompletedProcess(
            args=args, returncode=0, stdout="", stderr="",
        )

    monkeypatch.setattr(mp.subprocess, "run", fake_run)
    mp._gh_merge(32, pr_title=pr_title, admin=False, config={})

    argv = captured[0]
    assert "--subject" in argv
    subject_idx = argv.index("--subject")
    landed_subject = argv[subject_idx + 1]
    assert landed_subject == pr_title
    assert landed_subject != commit_subject, (
        "Squash subject must be the PR title, not the commit message."
    )
