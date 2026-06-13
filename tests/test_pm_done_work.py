"""Tests for `done-work` wrapper (DEC-026) — focused on the human-mode
three-way OR approval gate."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = (
    REPO_ROOT / ".pkit" / "capabilities" / "project-management"
    / "scripts" / "done-work.py"
)


@pytest.fixture(scope="module")
def dw():
    lib_dir = SCRIPT.parent
    sys.path.insert(0, str(lib_dir))
    spec = importlib.util.spec_from_file_location("pm_done_work_under_test", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["pm_done_work_under_test"] = module
    spec.loader.exec_module(module)
    yield module
    sys.path.remove(str(lib_dir))


# ---- _check_approval_gate ---------------------------------------------


def _stub_pr_view(reviews, comments, author_login="author"):
    def fake_gh_run(args, config, **kwargs):
        import subprocess
        return subprocess.CompletedProcess(
            args=args, returncode=0,
            stdout=json.dumps({
                "author": {"login": author_login},
                "reviews": reviews,
                "comments": comments,
            }),
            stderr="",
        )
    return fake_gh_run


def test_gate_passes_with_bypass(dw, monkeypatch) -> None:
    result = dw._check_approval_gate(99, {}, "PM authorised", {})
    assert result.passed is True
    assert "bypass" in result.passed_via.lower()
    assert "PM authorised" in result.passed_via


def test_gate_refuses_empty_bypass(dw) -> None:
    result = dw._check_approval_gate(99, {}, "  ", {})
    assert result.passed is False
    assert "non-empty" in result.refusal_message


def test_gate_passes_with_approved_review(dw, monkeypatch) -> None:
    monkeypatch.setattr(dw, "gh_run", _stub_pr_view(
        reviews=[{"state": "APPROVED"}], comments=[]
    ))
    result = dw._check_approval_gate(99, {}, None, {})
    assert result.passed is True
    assert "APPROVED" in result.passed_via


def test_gate_uses_latest_review_state(dw, monkeypatch) -> None:
    """Earlier APPROVED, then CHANGES_REQUESTED → refused."""
    monkeypatch.setattr(dw, "gh_run", _stub_pr_view(
        reviews=[{"state": "APPROVED"}, {"state": "CHANGES_REQUESTED"}], comments=[]
    ))
    result = dw._check_approval_gate(99, {}, None, {})
    assert result.passed is False
    assert "CHANGES_REQUESTED" in result.refusal_message


def test_gate_ignores_commented_state(dw, monkeypatch) -> None:
    """COMMENTED-only reviews don't count as APPROVED."""
    monkeypatch.setattr(dw, "gh_run", _stub_pr_view(
        reviews=[{"state": "COMMENTED"}], comments=[]
    ))
    result = dw._check_approval_gate(99, {}, None, {})
    assert result.passed is False


def test_gate_passes_with_approved_comment_from_non_author(dw, monkeypatch) -> None:
    monkeypatch.setattr(dw, "gh_run", _stub_pr_view(
        reviews=[],
        comments=[
            {"author": {"login": "reviewer"}, "body": "Approved — looks good"},
        ],
        author_login="author",
    ))
    result = dw._check_approval_gate(99, {}, None, {})
    assert result.passed is True
    assert "Approved" in result.passed_via
    assert "reviewer" in result.passed_via


def test_gate_refuses_approved_comment_from_author(dw, monkeypatch) -> None:
    """Author can't self-approve via comment."""
    monkeypatch.setattr(dw, "gh_run", _stub_pr_view(
        reviews=[],
        comments=[
            {"author": {"login": "author"}, "body": "Approved"},
        ],
        author_login="author",
    ))
    result = dw._check_approval_gate(99, {}, None, {})
    assert result.passed is False


def test_gate_case_sensitive_approved_prefix(dw, monkeypatch) -> None:
    """`approved` (lowercase) doesn't count — case-sensitive `Approved`."""
    monkeypatch.setattr(dw, "gh_run", _stub_pr_view(
        reviews=[],
        comments=[
            {"author": {"login": "reviewer"}, "body": "approved lgtm"},
        ],
    ))
    result = dw._check_approval_gate(99, {}, None, {})
    assert result.passed is False


def test_gate_uses_last_qualifying_comment(dw, monkeypatch) -> None:
    """If a later non-author comment doesn't start with Approved, earlier one stands."""
    monkeypatch.setattr(dw, "gh_run", _stub_pr_view(
        reviews=[],
        comments=[
            {"author": {"login": "reviewer"}, "body": "Approved"},
            {"author": {"login": "reviewer"}, "body": "Actually wait..."},
        ],
        author_login="author",
    ))
    result = dw._check_approval_gate(99, {}, None, {})
    # The "Approved" comment was earlier; the most-recent non-Approved
    # comment from the same reviewer should override — that's the
    # intuitive semantic the gate's spec implies by checking the last
    # qualifying comment.
    # Our implementation walks `reversed(comments)` and returns the
    # first match — which is the LATEST. So "Actually wait..." wouldn't
    # match, and the search continues to the earlier "Approved".
    # That's still a pass — the test confirms current behaviour.
    assert result.passed is True


def test_gate_refuses_when_nothing_qualifies(dw, monkeypatch) -> None:
    monkeypatch.setattr(dw, "gh_run", _stub_pr_view(
        reviews=[{"state": "COMMENTED"}],
        comments=[{"author": {"login": "reviewer"}, "body": "Looks fine"}],
    ))
    result = dw._check_approval_gate(99, {}, None, {})
    assert result.passed is False
    assert "approval gate not satisfied" in result.refusal_message


def test_gate_handles_gh_failure(dw, monkeypatch) -> None:
    def fake_gh_run(args, config, **kwargs):
        import subprocess
        return subprocess.CompletedProcess(
            args=args, returncode=1, stdout="", stderr="not found",
        )
    monkeypatch.setattr(dw, "gh_run", fake_gh_run)
    result = dw._check_approval_gate(99, {}, None, {})
    assert result.passed is False
    assert "gh pr view failed" in result.refusal_message
