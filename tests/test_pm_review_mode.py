"""Tests for _lib/review_mode.py (DEC-027 three-layer resolution)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
RM_PY = (
    REPO_ROOT / ".pkit" / "capabilities" / "project-management"
    / "scripts" / "_lib" / "review_mode.py"
)


@pytest.fixture(scope="module")
def rm():
    spec = importlib.util.spec_from_file_location("pm_review_mode_under_test", RM_PY)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["pm_review_mode_under_test"] = module
    spec.loader.exec_module(module)
    return module


# ---- Layer 1: project default --------------------------------------


def test_resolve_kit_default_when_no_config(rm) -> None:
    r = rm.resolve_mode({})
    assert r.mode == "agent"
    assert "kit default" in r.source


def test_resolve_project_default_agent(rm) -> None:
    r = rm.resolve_mode({"review": {"mode": "agent"}})
    assert r.mode == "agent"
    assert r.source == "project default"


def test_resolve_project_default_human(rm) -> None:
    r = rm.resolve_mode({"review": {"mode": "human"}})
    assert r.mode == "human"
    assert r.source == "project default"


def test_resolve_ignores_invalid_mode(rm) -> None:
    """Bogus mode value falls through to kit default."""
    r = rm.resolve_mode({"review": {"mode": "lol"}})
    assert r.mode == "agent"
    assert "kit default" in r.source


# ---- Layer 2: per-issue label --------------------------------------


def test_label_human_overrides_project_default(rm) -> None:
    r = rm.resolve_mode(
        {"review": {"mode": "agent"}},
        issue_labels=["type:feature", "review:human"],
    )
    assert r.mode == "human"
    assert "review:human" in r.source


def test_label_agent_overrides_project_default(rm) -> None:
    r = rm.resolve_mode(
        {"review": {"mode": "human"}},
        issue_labels=["review:agent"],
    )
    assert r.mode == "agent"
    assert "review:agent" in r.source


# ---- Layer 3: --require-human flag ---------------------------------


def test_require_human_flag_wins_over_label_agent(rm) -> None:
    """Per DEC-027 Layer 3 conflict rule: flag wins."""
    r = rm.resolve_mode(
        {"review": {"mode": "agent"}},
        issue_labels=["review:agent"],
        require_human=True,
    )
    assert r.mode == "human"
    assert "--require-human" in r.source


def test_require_human_flag_wins_over_label_human(rm) -> None:
    """Redundant but correct."""
    r = rm.resolve_mode({}, issue_labels=["review:human"], require_human=True)
    assert r.mode == "human"
    assert "--require-human" in r.source


def test_require_human_flag_wins_over_project_default(rm) -> None:
    r = rm.resolve_mode({"review": {"mode": "agent"}}, require_human=True)
    assert r.mode == "human"


# ---- role_based_reviewers ----------------------------------------


def test_role_based_reviewers_filters_by_role(rm) -> None:
    members = [
        {"github_login": "alice", "role": "PM"},
        {"github_login": "bob", "role": "Implementer"},
        {"github_login": "carol", "role": "Implementer"},
    ]
    assert rm.role_based_reviewers(members, "Implementer") == ["bob", "carol"]
    assert rm.role_based_reviewers(members, "PM") == ["alice"]


def test_role_based_reviewers_excludes_author(rm) -> None:
    members = [
        {"github_login": "alice", "role": "Implementer"},
        {"github_login": "bob", "role": "Implementer"},
    ]
    assert rm.role_based_reviewers(
        members, "Implementer", exclude_login="alice"
    ) == ["bob"]


def test_role_based_reviewers_empty_when_no_match(rm) -> None:
    members = [{"github_login": "alice", "role": "PM"}]
    assert rm.role_based_reviewers(members, "Implementer") == []


def test_role_based_reviewers_skips_members_without_role(rm) -> None:
    members = [
        {"github_login": "alice"},  # no role
        {"github_login": "bob", "role": "Implementer"},
    ]
    assert rm.role_based_reviewers(members, "Implementer") == ["bob"]


def test_role_based_reviewers_empty_role(rm) -> None:
    assert rm.role_based_reviewers([{"role": "x", "github_login": "y"}], "") == []


# ---- reviewer_role_from_config ----------------------------------


def test_reviewer_role_returns_value(rm) -> None:
    config = {"review": {"human_review": {"reviewer_role": "Implementer"}}}
    assert rm.reviewer_role_from_config(config) == "Implementer"


def test_reviewer_role_absent(rm) -> None:
    assert rm.reviewer_role_from_config({}) is None
    assert rm.reviewer_role_from_config({"review": {}}) is None
    assert rm.reviewer_role_from_config({"review": {"human_review": {}}}) is None


def test_reviewer_role_handles_non_dict_review(rm) -> None:
    assert rm.reviewer_role_from_config({"review": "lol"}) is None
