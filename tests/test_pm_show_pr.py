"""Tests for project-management's show-pr script's pure logic.

Covers the Conventional Commits parser, closing-issue extraction,
summary builder.
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
    / "show-pr.py"
)


@pytest.fixture(scope="module")
def sp():
    module_name = "pm_show_pr_under_test"
    spec = importlib.util.spec_from_file_location(module_name, SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


# --- Conventional Commits parser -------------------------------------


def test_parse_cc_with_scope(sp) -> None:
    out = sp._parse_conventional_commits("feat(cli): add new dispatcher")
    assert out["matched"] is True
    assert out["type"] == "feat"
    assert out["scope"] == "cli"
    assert out["summary"] == "add new dispatcher"


def test_parse_cc_without_scope(sp) -> None:
    out = sp._parse_conventional_commits("fix: correct off-by-one")
    assert out["matched"] is True
    assert out["type"] == "fix"
    assert out["scope"] is None
    assert out["summary"] == "correct off-by-one"


def test_parse_cc_returns_unmatched_for_non_cc(sp) -> None:
    out = sp._parse_conventional_commits("Random title")
    assert out["matched"] is False


def test_parse_cc_unmatched_for_capital_type(sp) -> None:
    # CC types are lowercase by convention; capital fails.
    out = sp._parse_conventional_commits("Feat: thing")
    assert out["matched"] is False


# --- closing-issue extraction ---------------------------------------


def test_extract_closes_simple(sp) -> None:
    assert sp._extract_closing_issues("Closes #42") == [42]


def test_extract_multiple(sp) -> None:
    out = sp._extract_closing_issues("Closes #1, fixes #2\nResolves #3")
    assert sorted(out) == [1, 2, 3]


def test_extract_dedupes(sp) -> None:
    assert sp._extract_closing_issues("Closes #1\nFixes #1\nResolves #1") == [1]


def test_extract_empty_for_no_keyword(sp) -> None:
    assert sp._extract_closing_issues("body without keyword") == []


# --- summary builder -------------------------------------------------


def test_summarise_picks_up_fields(sp) -> None:
    pr = {
        "title": "feat(cli): add new dispatcher",
        "body": "Closes #42\n\n## Doc impact\nupdated README.",
        "state": "OPEN",
        "isDraft": False,
        "headRefName": "feat/42-add-dispatcher",
        "baseRefName": "main",
        "mergedAt": None,
        "url": "https://github.com/owner/repo/pull/99",
        "reviewRequests": [{"login": "alice"}, {"login": "bob"}],
    }
    s = sp._summarise(pr)
    assert s["title"] == "feat(cli): add new dispatcher"
    assert s["state"] == "open"
    assert s["is_draft"] is False
    assert s["head"] == "feat/42-add-dispatcher"
    assert s["base"] == "main"
    assert s["conventional_commits"]["type"] == "feat"
    assert s["conventional_commits"]["scope"] == "cli"
    assert s["closes"] == [42]
    assert s["reviewers"] == ["alice", "bob"]
    assert s["has_doc_impact_section"] is True


def test_summarise_handles_missing_optional_fields(sp) -> None:
    pr = {
        "title": "plain title",
        "body": "no closes here",
        "state": "MERGED",
    }
    s = sp._summarise(pr)
    assert s["state"] == "merged"
    assert s["is_draft"] is False
    assert s["closes"] == []
    assert s["reviewers"] == []
    assert s["has_doc_impact_section"] is False


def test_summarise_detects_doc_impact_anywhere_in_body(sp) -> None:
    pr = {
        "title": "feat: x",
        "body": "Closes #1\n\nintro\n\n## Doc impact\n\n- updated foo",
        "state": "OPEN",
    }
    s = sp._summarise(pr)
    assert s["has_doc_impact_section"] is True
