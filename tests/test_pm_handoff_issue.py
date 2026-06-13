"""Tests for `handoff-issue` wrapper (DEC-026)."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = (
    REPO_ROOT / ".pkit" / "capabilities" / "project-management"
    / "scripts" / "handoff-issue.py"
)


@pytest.fixture(scope="module")
def hi():
    lib_dir = SCRIPT.parent
    sys.path.insert(0, str(lib_dir))
    spec = importlib.util.spec_from_file_location("pm_handoff_issue_under_test", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["pm_handoff_issue_under_test"] = module
    spec.loader.exec_module(module)
    yield module
    sys.path.remove(str(lib_dir))


def test_reassign_calls_add_and_remove(hi, monkeypatch) -> None:
    captured = {}

    def fake_gh_run(args, config, **kwargs):
        import subprocess
        captured["args"] = args
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(hi, "gh_run", fake_gh_run)
    hi._reassign(42, "alice", "bob", {})
    args = captured["args"]
    assert "--add-assignee" in args and "bob" in args
    assert "--remove-assignee" in args and "alice" in args


def test_reassign_skips_remove_when_unassigned(hi, monkeypatch) -> None:
    captured = {}

    def fake_gh_run(args, config, **kwargs):
        import subprocess
        captured["args"] = args
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(hi, "gh_run", fake_gh_run)
    hi._reassign(42, "(unassigned)", "bob", {})
    args = captured["args"]
    assert "--add-assignee" in args
    assert "--remove-assignee" not in args


def test_reassign_propagates_failure(hi, monkeypatch, capsys) -> None:
    def fake_gh_run(args, config, **kwargs):
        import subprocess
        return subprocess.CompletedProcess(
            args=args, returncode=1, stdout="", stderr="not a collaborator",
        )
    monkeypatch.setattr(hi, "gh_run", fake_gh_run)
    assert hi._reassign(42, "alice", "bob", {}) is False
    assert "not a collaborator" in capsys.readouterr().err


def test_audit_comment_idempotent_skips_when_stamp_exists(hi, monkeypatch) -> None:
    calls = []

    def fake_gh_run(args, config, **kwargs):
        import subprocess
        calls.append(args)
        if "view" in args:
            return subprocess.CompletedProcess(
                args=args, returncode=0,
                stdout=json.dumps({
                    "comments": [
                        {"body": "Other"},
                        {"body": "<!-- pkit-hook: handoff-issue:alice->bob --> ..."},
                    ]
                }),
                stderr="",
            )
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(hi, "gh_run", fake_gh_run)
    result = hi._post_audit_comment_idempotent(
        42, "<!-- pkit-hook: handoff-issue:alice->bob -->", "body", {},
    )
    assert result is True
    # No `gh issue comment` call should have happened.
    assert not any(args[1:3] == ["issue", "comment"] for args in calls)


def test_audit_comment_posts_when_absent(hi, monkeypatch) -> None:
    calls = []

    def fake_gh_run(args, config, **kwargs):
        import subprocess
        calls.append(args)
        if "view" in args:
            return subprocess.CompletedProcess(
                args=args, returncode=0,
                stdout=json.dumps({"comments": []}), stderr="",
            )
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(hi, "gh_run", fake_gh_run)
    result = hi._post_audit_comment_idempotent(42, "stamp", "body", {})
    assert result is True
    assert any(args[1:3] == ["issue", "comment"] for args in calls)


def test_audit_comment_stamp_includes_from_to(hi) -> None:
    """The stamp marker discriminates by from→to so successive handoffs each get their own."""
    # Just verify the prefix shape; main() composes the full stamp.
    assert hi.AUDIT_STAMP_PREFIX == "<!-- pkit-hook: handoff-issue:"
