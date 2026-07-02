"""Tests for `review-work` wrapper (DEC-026)."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = (
    REPO_ROOT / ".pkit" / "capabilities" / "project-management"
    / "scripts" / "review-work.py"
)


@pytest.fixture(scope="module")
def rw():
    lib_dir = SCRIPT.parent
    sys.path.insert(0, str(lib_dir))
    spec = importlib.util.spec_from_file_location("pm_review_work_under_test", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["pm_review_work_under_test"] = module
    spec.loader.exec_module(module)
    yield module
    sys.path.remove(str(lib_dir))


# ---- _derive_branch_prefix --------------------------------------------
#
# review-work's derivation is the verbatim twin of start-work's: kit type value
# through the ADR-026 read seam (label OR title-prefix), mapped via
# classification.yaml's `pr_type_mapping`. Same fixture, same two arms.

_CLASSIFICATION = {
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
    "pr_type_mapping": [
        {"issue_label_value": "feature", "pr_conv_type": "feat"},
        {"issue_label_value": "bug", "pr_conv_type": "fix"},
        {"issue_label_value": "docs", "pr_conv_type": "docs"},
        {"issue_label_value": "test", "pr_conv_type": "test"},
        {"issue_label_value": "refactor", "pr_conv_type": "refactor"},
        {"issue_label_value": "maintenance", "pr_conv_type": "chore"},
    ],
}


def test_derive_branch_prefix_returns_expected(rw) -> None:
    assert rw._derive_branch_prefix(["type:feature"], "[Task] x", _CLASSIFICATION) == "feat"
    assert rw._derive_branch_prefix(["type:bug"], "[Bug] x", _CLASSIFICATION) == "fix"
    assert rw._derive_branch_prefix(["type:docs"], "[Docs] x", _CLASSIFICATION) == "docs"


def test_derive_branch_prefix_missing_returns_none(rw) -> None:
    assert rw._derive_branch_prefix(["priority:High"], "no prefix", _CLASSIFICATION) is None


def test_derive_branch_prefix_brownfield_bug_title_no_label(rw) -> None:
    """DEC-013 cross-check must resolve `fix` for a brownfield `[Bug]`-titled Task
    that carries NO type:* label — via the title-prefix arm of the seam."""
    assert rw._derive_branch_prefix([], "[Bug] hostname mismatch", _CLASSIFICATION) == "fix"


def test_derive_branch_prefix_greenfield_label_still_wins(rw) -> None:
    """Greenfield stays byte-identical: the `type:bug` label resolves `fix`."""
    assert rw._derive_branch_prefix(["type:bug"], "no bracket prefix", _CLASSIFICATION) == "fix"


# ---- _derive_pr_title --------------------------------------------------


def test_pr_title_strips_issue_prefix(rw) -> None:
    assert rw._derive_pr_title(
        {"title": "[Feature] add foo"}, "feat/42-add-foo"
    ) == "feat: add foo"


def test_pr_title_default_prefix_when_branch_malformed(rw) -> None:
    assert rw._derive_pr_title({"title": "x"}, "weird") == "feat: x"


# ---- _find_pr_for_branch ----------------------------------------------


def test_find_pr_only_returns_open_state(rw, monkeypatch) -> None:
    """Closed/merged PRs for the same branch shouldn't be returned."""
    def fake_gh_run(args, config, **kwargs):
        import subprocess
        return subprocess.CompletedProcess(
            args=args, returncode=0,
            stdout=json.dumps([
                {"number": 1, "state": "CLOSED", "isDraft": False,
                 "headRefName": "feat/42-foo"},
                {"number": 2, "state": "OPEN", "isDraft": True,
                 "headRefName": "feat/42-foo"},
            ]),
            stderr="",
        )
    monkeypatch.setattr(rw, "gh_run", fake_gh_run)
    pr = rw._find_pr_for_branch("feat/42-foo", {})
    assert pr is not None
    assert pr["number"] == 2  # The OPEN one


def test_find_pr_returns_none_when_no_open(rw, monkeypatch) -> None:
    def fake_gh_run(args, config, **kwargs):
        import subprocess
        return subprocess.CompletedProcess(
            args=args, returncode=0,
            stdout=json.dumps([
                {"number": 1, "state": "CLOSED", "headRefName": "feat/42-foo"},
            ]),
            stderr="",
        )
    monkeypatch.setattr(rw, "gh_run", fake_gh_run)
    assert rw._find_pr_for_branch("feat/42-foo", {}) is None


# ---- _gh_pr_add_reviewers --------------------------------------------


def test_pr_add_reviewers_strips_at_prefix(rw, monkeypatch) -> None:
    captured = {}

    def fake_gh_run(args, config, **kwargs):
        import subprocess
        captured["args"] = args
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(rw, "gh_run", fake_gh_run)
    rw._gh_pr_add_reviewers(99, ["@alice", "bob"], {})
    args = captured["args"]
    # The args list has --add-reviewer pairs
    assert "alice" in args
    assert "bob" in args
    assert "@alice" not in args  # @ stripped
    # Verify --add-reviewer appears twice
    assert args.count("--add-reviewer") == 2


def test_pr_add_reviewers_propagates_failure(rw, monkeypatch, capsys) -> None:
    def fake_gh_run(args, config, **kwargs):
        import subprocess
        return subprocess.CompletedProcess(
            args=args, returncode=1, stdout="", stderr="not authorised",
        )
    monkeypatch.setattr(rw, "gh_run", fake_gh_run)
    assert rw._gh_pr_add_reviewers(99, ["@alice"], {}) is False
    assert "not authorised" in capsys.readouterr().err


# ---- _gh_pr_ready -----------------------------------------------------


def test_pr_ready_handles_none_pr_number(rw, capsys) -> None:
    assert rw._gh_pr_ready(None, {}) is False
    assert "no PR number resolved" in capsys.readouterr().err


def test_pr_ready_propagates_gh_failure(rw, monkeypatch, capsys) -> None:
    def fake_gh_run(args, config, **kwargs):
        import subprocess
        return subprocess.CompletedProcess(
            args=args, returncode=1, stdout="", stderr="already ready",
        )
    monkeypatch.setattr(rw, "gh_run", fake_gh_run)
    assert rw._gh_pr_ready(99, {}) is False


def test_pr_ready_returns_true_on_success(rw, monkeypatch) -> None:
    def fake_gh_run(args, config, **kwargs):
        import subprocess
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")
    monkeypatch.setattr(rw, "gh_run", fake_gh_run)
    assert rw._gh_pr_ready(99, {}) is True
