"""Tests for `create-draft` wrapper (DEC-026)."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = (
    REPO_ROOT / ".pkit" / "capabilities" / "project-management"
    / "scripts" / "create-draft.py"
)


@pytest.fixture(scope="module")
def cd():
    lib_dir = SCRIPT.parent
    sys.path.insert(0, str(lib_dir))
    spec = importlib.util.spec_from_file_location("pm_create_draft_under_test", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["pm_create_draft_under_test"] = module
    spec.loader.exec_module(module)
    yield module
    sys.path.remove(str(lib_dir))


# ---- _derive_pr_title -----------------------------------------------


def test_derive_pr_title_strips_issue_type_prefix(cd) -> None:
    assert cd._derive_pr_title(
        {"title": "[Feature] add gh helper"}, "feat/42-add-gh-helper"
    ) == "feat: add gh helper"


def test_derive_pr_title_uses_branch_prefix(cd) -> None:
    assert cd._derive_pr_title(
        {"title": "fix hostname mismatch"}, "fix/177-hostname"
    ) == "fix: fix hostname mismatch"


def test_derive_pr_title_default_prefix_when_branch_malformed(cd) -> None:
    """If the branch doesn't carry a conventional-commit prefix, default to feat."""
    assert cd._derive_pr_title(
        {"title": "do thing"}, "weird-branch-name"
    ) == "feat: do thing"


def test_derive_pr_title_empty_title(cd) -> None:
    assert cd._derive_pr_title({}, "feat/42-foo") == "feat:"


# ---- _find_pr_for_branch -------------------------------------------


def test_find_pr_returns_existing_match(cd, monkeypatch) -> None:
    def fake_gh_run(args, config, **kwargs):
        import subprocess
        return subprocess.CompletedProcess(
            args=args, returncode=0,
            stdout=json.dumps([{
                "number": 99, "state": "OPEN", "isDraft": True,
                "headRefName": "feat/42-foo",
            }]),
            stderr="",
        )
    monkeypatch.setattr(cd, "gh_run", fake_gh_run)
    pr = cd._find_pr_for_branch("feat/42-foo", {})
    assert pr is not None
    assert pr["number"] == 99
    assert pr["isDraft"] is True


def test_find_pr_returns_none_when_no_match(cd, monkeypatch) -> None:
    def fake_gh_run(args, config, **kwargs):
        import subprocess
        return subprocess.CompletedProcess(
            args=args, returncode=0, stdout="[]", stderr="",
        )
    monkeypatch.setattr(cd, "gh_run", fake_gh_run)
    assert cd._find_pr_for_branch("feat/42-foo", {}) is None


def test_find_pr_returns_none_on_gh_failure(cd, monkeypatch) -> None:
    def fake_gh_run(args, config, **kwargs):
        import subprocess
        return subprocess.CompletedProcess(
            args=args, returncode=1, stdout="", stderr="error",
        )
    monkeypatch.setattr(cd, "gh_run", fake_gh_run)
    assert cd._find_pr_for_branch("feat/42-foo", {}) is None


def test_find_pr_filters_by_head_ref(cd, monkeypatch) -> None:
    """gh sometimes returns PRs from forks; only matching head names count."""
    def fake_gh_run(args, config, **kwargs):
        import subprocess
        return subprocess.CompletedProcess(
            args=args, returncode=0,
            stdout=json.dumps([
                {"number": 1, "headRefName": "fork:feat/42-foo"},
                {"number": 2, "headRefName": "feat/42-foo"},
            ]),
            stderr="",
        )
    monkeypatch.setattr(cd, "gh_run", fake_gh_run)
    pr = cd._find_pr_for_branch("feat/42-foo", {})
    assert pr is not None
    assert pr["number"] == 2


# ---- _gh_pr_create_draft -------------------------------------------


def test_gh_pr_create_draft_passes_correct_args(cd, monkeypatch) -> None:
    captured = {}

    def fake_gh_run(args, config, **kwargs):
        import subprocess
        captured["args"] = args
        return subprocess.CompletedProcess(
            args=args, returncode=0,
            stdout="https://github.com/o/r/pull/99\n", stderr="",
        )
    monkeypatch.setattr(cd, "gh_run", fake_gh_run)
    url = cd._gh_pr_create_draft(
        "feat/42-foo", "main", "feat: do thing", "Closes #42", {}
    )
    assert url == "https://github.com/o/r/pull/99"
    assert "--draft" in captured["args"]
    assert "--head" in captured["args"]
    assert "feat/42-foo" in captured["args"]


def test_gh_pr_create_draft_returns_none_on_failure(cd, monkeypatch, capsys) -> None:
    def fake_gh_run(args, config, **kwargs):
        import subprocess
        return subprocess.CompletedProcess(
            args=args, returncode=1, stdout="", stderr="branch already has PR",
        )
    monkeypatch.setattr(cd, "gh_run", fake_gh_run)
    url = cd._gh_pr_create_draft("feat/42-foo", "main", "t", "b", {})
    assert url is None
    assert "branch already has PR" in capsys.readouterr().err
