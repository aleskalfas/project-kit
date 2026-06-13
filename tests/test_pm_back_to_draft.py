"""Tests for `back-to-draft` wrapper (DEC-026)."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = (
    REPO_ROOT / ".pkit" / "capabilities" / "project-management"
    / "scripts" / "back-to-draft.py"
)


@pytest.fixture(scope="module")
def b2d():
    lib_dir = SCRIPT.parent
    sys.path.insert(0, str(lib_dir))
    spec = importlib.util.spec_from_file_location("pm_back_to_draft_under_test", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["pm_back_to_draft_under_test"] = module
    spec.loader.exec_module(module)
    yield module
    sys.path.remove(str(lib_dir))


def test_pr_ready_undo_handles_none(b2d) -> None:
    assert b2d._gh_pr_ready_undo(None, {}) is False


def test_pr_ready_undo_propagates_failure(b2d, monkeypatch, capsys) -> None:
    def fake_gh_run(args, config, **kwargs):
        import subprocess
        return subprocess.CompletedProcess(
            args=args, returncode=1, stdout="", stderr="already draft",
        )
    monkeypatch.setattr(b2d, "gh_run", fake_gh_run)
    assert b2d._gh_pr_ready_undo(99, {}) is False
    assert "already draft" in capsys.readouterr().err


def test_pr_ready_undo_success(b2d, monkeypatch) -> None:
    captured = {}

    def fake_gh_run(args, config, **kwargs):
        import subprocess
        captured["args"] = args
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(b2d, "gh_run", fake_gh_run)
    assert b2d._gh_pr_ready_undo(99, {}) is True
    assert "--undo" in captured["args"]
    assert "99" in captured["args"]


def test_dismiss_approved_zero_when_no_reviews(b2d, monkeypatch) -> None:
    def fake_gh_run(args, config, **kwargs):
        import subprocess
        return subprocess.CompletedProcess(
            args=args, returncode=0,
            stdout=json.dumps({"reviews": []}), stderr="",
        )
    monkeypatch.setattr(b2d, "gh_run", fake_gh_run)
    assert b2d._dismiss_approved_reviews(99, {}) == 0


def test_dismiss_approved_counts_only_approved(b2d, monkeypatch) -> None:
    calls = []

    def fake_gh_run(args, config, **kwargs):
        import subprocess
        calls.append(args)
        if "view" in args:
            return subprocess.CompletedProcess(
                args=args, returncode=0,
                stdout=json.dumps({"reviews": [
                    {"state": "APPROVED"},
                    {"state": "COMMENTED"},
                    {"state": "APPROVED"},
                    {"state": "CHANGES_REQUESTED"},
                ]}),
                stderr="",
            )
        # The dismiss invocation
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")
    monkeypatch.setattr(b2d, "gh_run", fake_gh_run)
    count = b2d._dismiss_approved_reviews(99, {})
    assert count == 2


def test_dismiss_approved_handles_none(b2d) -> None:
    assert b2d._dismiss_approved_reviews(None, {}) == 0


def test_find_pr_returns_only_open(b2d, monkeypatch) -> None:
    def fake_gh_run(args, config, **kwargs):
        import subprocess
        # --state open should be in args
        assert "open" in args
        return subprocess.CompletedProcess(
            args=args, returncode=0,
            stdout=json.dumps([
                {"number": 99, "isDraft": False, "headRefName": "feat/42-foo"},
            ]),
            stderr="",
        )
    monkeypatch.setattr(b2d, "gh_run", fake_gh_run)
    pr = b2d._find_pr_for_branch("feat/42-foo", {})
    assert pr is not None
    assert pr["number"] == 99
    assert pr["isDraft"] is False
