"""Tests for project-management's `promote-issue` workflow wrapper (DEC-026).

Focused on the wrapper-specific gates and helpers — the state-transition
mechanics live in `move-issue.py` and are tested separately.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = (
    REPO_ROOT
    / ".pkit"
    / "capabilities"
    / "project-management"
    / "scripts"
    / "promote-issue.py"
)


@pytest.fixture(scope="module")
def pi():
    """Load promote-issue.py via importlib."""
    lib_dir = SCRIPT.parent
    sys.path.insert(0, str(lib_dir))
    spec = importlib.util.spec_from_file_location("pm_promote_issue_under_test", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["pm_promote_issue_under_test"] = module
    spec.loader.exec_module(module)
    yield module
    sys.path.remove(str(lib_dir))


# ---- milestone resolution (moved to _lib/milestone.py in #217) ---------
#
# `_parse_concatenated_json_arrays` and `_milestone_exists_open` were
# extracted to `_lib/milestone.py` as part of #217's symmetry fix
# (both create-issue and promote-issue now use the lib resolver).
# Direct coverage lives in `tests/test_pm_milestone.py`; the
# tests that previously sat here were dropped along with the
# wrapper-local functions.


# ---- _detect_state_from_labels (idempotency path, #219) ----------------


def test_detect_state_from_labels_returns_bare_state(pi, monkeypatch) -> None:
    """Issue with `state:backlog` label → returns `"backlog"`."""
    def fake_gh_run(args, config, **kwargs):
        import subprocess
        return subprocess.CompletedProcess(
            args=args, returncode=0,
            stdout=json.dumps({
                "labels": [
                    {"name": "type:bug"},
                    {"name": "state:backlog"},
                    {"name": "priority:Medium"},
                ],
            }),
            stderr="",
        )
    monkeypatch.setattr(pi, "gh_run", fake_gh_run)
    assert pi._detect_state_from_labels(42, {}) == "backlog"


def test_detect_state_from_labels_none_when_no_state_label(pi, monkeypatch) -> None:
    """No `state:*` label → returns None (the issue is at the implicit Todo state)."""
    def fake_gh_run(args, config, **kwargs):
        import subprocess
        return subprocess.CompletedProcess(
            args=args, returncode=0,
            stdout=json.dumps({"labels": [{"name": "type:bug"}]}),
            stderr="",
        )
    monkeypatch.setattr(pi, "gh_run", fake_gh_run)
    assert pi._detect_state_from_labels(42, {}) is None


def test_detect_state_from_labels_gh_failure_returns_none(pi, monkeypatch) -> None:
    """gh view failure → None (caller treats as "unknown state, proceed to transition")."""
    def fake_gh_run(args, config, **kwargs):
        import subprocess
        return subprocess.CompletedProcess(
            args=args, returncode=1, stdout="", stderr="boom",
        )
    monkeypatch.setattr(pi, "gh_run", fake_gh_run)
    assert pi._detect_state_from_labels(42, {}) is None


def test_detect_state_from_labels_recognises_in_progress(pi, monkeypatch) -> None:
    """All four post-Todo states are recognised — promote-issue exits cleanly on any of them."""
    for state in ("backlog", "in-progress", "review", "done"):
        def fake_gh_run(args, config, _state=state, **kwargs):
            import subprocess
            return subprocess.CompletedProcess(
                args=args, returncode=0,
                stdout=json.dumps({"labels": [{"name": f"state:{_state}"}]}),
                stderr="",
            )
        monkeypatch.setattr(pi, "gh_run", fake_gh_run)
        assert pi._detect_state_from_labels(42, {}) == state, (
            f"state:{state} label not recognised"
        )


# ---- _post_audit_comment_idempotent -----------------------------------


def test_post_audit_comment_skips_when_stamp_exists(pi, monkeypatch, capsys) -> None:
    calls: list = []

    def fake_gh_run(args, config, **kwargs):
        import subprocess
        calls.append(args)
        if "view" in args:
            return subprocess.CompletedProcess(
                args=args, returncode=0,
                stdout=json.dumps({
                    "comments": [
                        {"body": "Random comment"},
                        {"body": f"{pi.AUDIT_STAMP}\n\nPromoted Todo → Backlog ..."},
                    ]
                }),
                stderr="",
            )
        # `gh issue comment` — should NOT be called if stamp exists
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(pi, "gh_run", fake_gh_run)
    result = pi._post_audit_comment_idempotent(42, "ignored", {})
    assert result is True
    # `gh issue comment` shouldn't have been called.
    assert not any("comment" in args and "view" not in args for args in calls)


def test_post_audit_comment_posts_when_absent(pi, monkeypatch) -> None:
    calls: list = []

    def fake_gh_run(args, config, **kwargs):
        import subprocess
        calls.append(args)
        if "view" in args:
            return subprocess.CompletedProcess(
                args=args, returncode=0,
                stdout=json.dumps({"comments": []}), stderr="",
            )
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(pi, "gh_run", fake_gh_run)
    result = pi._post_audit_comment_idempotent(42, "test body", {})
    assert result is True
    # `gh issue comment` was called.
    assert any(args[1:3] == ["issue", "comment"] for args in calls)


def test_post_audit_comment_propagates_failure(pi, monkeypatch, capsys) -> None:
    def fake_gh_run(args, config, **kwargs):
        import subprocess
        if "view" in args:
            return subprocess.CompletedProcess(
                args=args, returncode=0,
                stdout=json.dumps({"comments": []}), stderr="",
            )
        return subprocess.CompletedProcess(
            args=args, returncode=1, stdout="", stderr="comment failed"
        )

    monkeypatch.setattr(pi, "gh_run", fake_gh_run)
    result = pi._post_audit_comment_idempotent(42, "test", {})
    assert result is False
    assert "gh issue comment failed" in capsys.readouterr().err


# ---- _attach_milestone -------------------------------------------------


def test_attach_milestone_success(pi, monkeypatch) -> None:
    def fake_gh_run(args, config, **kwargs):
        import subprocess
        assert args[1:5] == ["issue", "edit", "42", "--milestone"]
        assert args[5] == "v1.0"
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(pi, "gh_run", fake_gh_run)
    assert pi._attach_milestone(42, "v1.0", {}) is True


def test_attach_milestone_failure(pi, monkeypatch, capsys) -> None:
    def fake_gh_run(args, config, **kwargs):
        import subprocess
        return subprocess.CompletedProcess(
            args=args, returncode=1, stdout="", stderr="cannot attach"
        )

    monkeypatch.setattr(pi, "gh_run", fake_gh_run)
    assert pi._attach_milestone(42, "v1.0", {}) is False
    assert "cannot attach" in capsys.readouterr().err
