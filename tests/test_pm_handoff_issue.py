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


def _completed(args, stdout="", returncode=0, stderr=""):
    import subprocess
    return subprocess.CompletedProcess(
        args=args, returncode=returncode, stdout=stdout, stderr=stderr,
    )


def test_audit_key_includes_the_reason(hi) -> None:
    """The key names the specific handoff: from, to, the stripped reason and the
    assignment-event count (#902) — not just from→to, as the old stamp did."""
    key = hi._handoff_audit_key("alice", "bob", "vacation", 3)
    assert key.startswith("<!-- pkit-audit-key: handoff-issue:")
    assert key == hi._handoff_audit_key("alice", "bob", "  vacation ", 3)
    assert key != hi._handoff_audit_key("alice", "bob", "reorg", 3)
    assert key != hi._handoff_audit_key("bob", "alice", "vacation", 3)
    assert key != hi._handoff_audit_key("alice", "bob", "vacation", 5)


def test_audit_body_shape(hi) -> None:
    key = hi._handoff_audit_key("alice", "bob", "vacation", 3)
    body = hi._handoff_audit_body("alice", "bob", " vacation ", "2026-09-26", key)
    lines = body.splitlines()
    assert lines[0] == hi.HANDOFF_AUDIT_MARKER
    assert "Handoff: @alice → @bob (2026-09-26, reason: vacation)" in lines
    assert lines[-1] == key


def test_assignment_event_count_reads_the_timeline_total(hi, monkeypatch) -> None:
    captured = {}

    def fake_gh_run(args, config, **kwargs):
        captured["args"] = list(args)
        return _completed(args, json.dumps({"data": {"repository": {"issue": {
            "timelineItems": {"totalCount": 4}}}}}))

    monkeypatch.setattr(hi, "gh_run", fake_gh_run)
    assert hi._assignment_event_count(42, {}) == 4
    args = captured["args"]
    assert args[:3] == ["gh", "api", "graphql"]
    assert "number=42" in args
    assert "owner={owner}" in args and "name={repo}" in args


@pytest.mark.parametrize(
    "result",
    [
        pytest.param({"returncode": 1, "stderr": "boom"}, id="gh-failure"),
        pytest.param({"stdout": "not json"}, id="not-json"),
        pytest.param({"stdout": json.dumps({"data": {"repository": None}})}, id="no-issue"),
        pytest.param(
            {"stdout": json.dumps({"data": {"repository": {"issue": {
                "timelineItems": {"totalCount": "4"}}}}})},
            id="non-integer",
        ),
    ],
)
def test_assignment_event_count_is_none_when_unreadable(hi, monkeypatch, result) -> None:
    monkeypatch.setattr(hi, "gh_run", lambda args, config, **kw: _completed(args, **result))
    assert hi._assignment_event_count(42, {}) is None


def test_audit_posts_when_only_someone_elses_legacy_stamp_exists(hi, monkeypatch) -> None:
    """The old from→to stamp, in anyone's comment, used to suppress the record."""
    posts = []

    def fake_gh_run(args, config, **kwargs):
        if args[:3] == ["gh", "api", "graphql"]:
            return _completed(args, json.dumps({"data": {"repository": {"issue": {
                "timelineItems": {"totalCount": 0}}}}}))
        if "view" in args:
            return _completed(args, json.dumps({"comments": [{
                "body": "<!-- pkit-hook: handoff-issue:alice->bob --> ...",
                "viewerDidAuthor": False, "includesCreatedEdit": False,
            }]}))
        posts.append(args)
        return _completed(args)

    monkeypatch.setattr(hi, "gh_run", fake_gh_run)
    assert hi._post_handoff_audit(42, "alice", "bob", "vacation", {}) is True
    assert len(posts) == 1 and posts[0][1:3] == ["issue", "comment"]
