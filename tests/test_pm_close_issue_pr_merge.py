"""close-issue --mode pr-merge --pr <M> (#1049).

A leaf whose work landed in a merged PR that closed another issue is closed as
completed through that PR: the PR is verified merged through the gh seam, the
checkbox close-gate runs, the reference is posted as a comment, and the
closure cascade runs. Without --pr the mode behaves as before. Every `gh` call
is faked.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
CAP_ROOT = REPO_ROOT / ".pkit" / "capabilities" / "project-management"
SCRIPT_PATH = CAP_ROOT / "scripts" / "close-issue.py"


@pytest.fixture(scope="module")
def ci():
    module_name = "pm_close_issue_pr_merge_under_test"
    spec = importlib.util.spec_from_file_location(module_name, SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _issue(*, title="[Task] landed elsewhere", state="OPEN", body="EPIC: #10\n\n## What\nx\n",
           labels=("state:in-progress",)) -> dict:
    return {
        "title": title,
        "body": body,
        "state": state,
        "labels": [{"name": n} for n in labels],
        "milestone": None,
    }


MERGED = {"number": 1042, "state": "MERGED", "mergedAt": "2026-09-27T10:00:00Z", "url": "u"}
OPEN_PR = {"number": 1042, "state": "OPEN", "mergedAt": None, "url": "u"}


def _run(ci, monkeypatch, argv: list[str], *, issue: dict, pr: dict | None = MERGED,
         comments: list | None = None, parents: dict | None = None) -> SimpleNamespace:
    """Run main() with every gate passed; record each `gh` write."""
    monkeypatch.setattr(sys, "argv", ["close-issue", *argv])
    monkeypatch.setattr(ci, "resolve_capability_root", lambda _explicit: CAP_ROOT)
    monkeypatch.setattr(ci.bootstrap_gate, "enforce", lambda *a, **k: True)
    monkeypatch.setattr(ci.session_guard, "enforce", lambda **k: True)
    monkeypatch.setattr(ci, "load_adopter_config", lambda _root: {})
    monkeypatch.setattr(ci, "_read_members", lambda *a: [])
    monkeypatch.setattr(ci, "resolve_invoker_identity", lambda **k: SimpleNamespace(github_login="me"))
    monkeypatch.setattr(ci, "check_membership", lambda *a: SimpleNamespace(allowed=True))
    monkeypatch.setattr(ci.axis_labels, "load_substrate_map", lambda *_a, **_k: None)
    monkeypatch.setattr(ci, "fire_hooks", lambda *a, **k: None)

    issues = {42: issue, **(parents or {})}
    monkeypatch.setattr(ci, "_gh_get_issue", lambda n, _config: issues.get(n))
    pr_reads: list[int] = []

    def fake_get_pr(n, _config):
        pr_reads.append(n)
        return pr

    monkeypatch.setattr(ci, "_gh_get_pr", fake_get_pr)

    calls: list[list[str]] = []

    def fake_gh_run(cmd, config, **kwargs):
        calls.append(cmd)
        stdout = ""
        if cmd[:3] == ["gh", "issue", "view"] and "comments" in cmd:
            stdout = json.dumps({"comments": comments or []})
        return subprocess.CompletedProcess(cmd, 0, stdout=stdout, stderr="")

    monkeypatch.setattr(ci, "gh_run", fake_gh_run)
    rc = ci.main()
    return SimpleNamespace(rc=rc, calls=calls, pr_reads=pr_reads)


def _writes(rec) -> list[list[str]]:
    return [c for c in rec.calls if c[:3] != ["gh", "issue", "view"]]


def test_closes_an_open_leaf_as_completed_through_a_merged_pr(ci, monkeypatch, capsys) -> None:
    parent = {"title": "[EPIC] e", "state": "OPEN", "body": "- [ ] open box\n", "labels": []}
    rec = _run(ci, monkeypatch, ["42", "--mode", "pr-merge", "--pr", "1042", "--yes"],
               issue=_issue(), parents={10: parent})
    assert rec.rc == 0
    assert rec.pr_reads == [1042]
    writes = _writes(rec)
    comment = next(c for c in writes if c[:3] == ["gh", "issue", "comment"])
    body = comment[comment.index("--body") + 1]
    assert body.startswith("[pr-merge close] completed by merged PR #1042.")
    assert ["gh", "issue", "close", "42", "--reason", "completed"] in writes
    label_edit = next(c for c in writes if c[:3] == ["gh", "issue", "edit"])
    assert label_edit[label_edit.index("--add-label") + 1] == "state:done"
    out = capsys.readouterr().out
    # The closure cascade ran over the parent the first line names.
    assert "[cascade] parents to check for eligibility: #10" in out


def test_the_comment_is_posted_once_across_a_retry(ci, monkeypatch) -> None:
    """A run that posted the reference and then failed to close finds it on the
    re-run and does not post it again (the shared audit idempotence)."""
    _key, body = ci._pr_merge_close_comment(1042)
    posted = [{"body": body, "viewerDidAuthor": True, "includesCreatedEdit": False}]
    rec = _run(ci, monkeypatch, ["42", "--mode", "pr-merge", "--pr", "1042", "--yes"],
               issue=_issue(), comments=posted)
    assert rec.rc == 0
    assert not any(c[:3] == ["gh", "issue", "comment"] for c in _writes(rec))
    assert ["gh", "issue", "close", "42", "--reason", "completed"] in _writes(rec)


def test_refuses_a_pr_that_is_not_merged(ci, monkeypatch, capsys) -> None:
    rec = _run(ci, monkeypatch, ["42", "--mode", "pr-merge", "--pr", "1042", "--yes"],
               issue=_issue(), pr=OPEN_PR)
    assert rec.rc == 1
    assert _writes(rec) == []
    assert "not merged" in capsys.readouterr().err


def test_an_unreadable_pr_is_a_usage_error(ci, monkeypatch) -> None:
    rec = _run(ci, monkeypatch, ["42", "--mode", "pr-merge", "--pr", "1042", "--yes"],
               issue=_issue(), pr=None)
    assert rec.rc == 2
    assert _writes(rec) == []


def test_refuses_a_container(ci, monkeypatch, capsys) -> None:
    rec = _run(ci, monkeypatch, ["42", "--mode", "pr-merge", "--pr", "1042", "--yes"],
               issue=_issue(title="[Feature] a container"))
    assert rec.rc == 2
    assert rec.pr_reads == []
    assert "cascade-eligibility-close" in capsys.readouterr().err


def test_the_checkbox_gate_applies(ci, monkeypatch, capsys) -> None:
    rec = _run(ci, monkeypatch, ["42", "--mode", "pr-merge", "--pr", "1042", "--yes"],
               issue=_issue(body="EPIC: #10\n\n- [ ] not yet\n"))
    assert rec.rc == 1
    assert _writes(rec) == []
    assert "not yet" in capsys.readouterr().err


def test_dry_run_writes_nothing(ci, monkeypatch) -> None:
    rec = _run(ci, monkeypatch, ["42", "--mode", "pr-merge", "--pr", "1042", "--dry-run"],
               issue=_issue())
    assert rec.rc == 0
    assert _writes(rec) == []


def test_pr_outside_pr_merge_mode_is_a_usage_error(ci, monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", ["close-issue", "42", "--mode", "wont-do", "--pr", "1"])
    assert ci.main() == 2


def test_already_closed_issue_only_reconciles_labels(ci, monkeypatch, capsys) -> None:
    rec = _run(ci, monkeypatch, ["42", "--mode", "pr-merge", "--pr", "1042", "--yes"],
               issue=_issue(state="CLOSED"))
    assert rec.rc == 0
    writes = _writes(rec)
    assert not any(c[:3] in (["gh", "issue", "comment"], ["gh", "issue", "close"]) for c in writes)
    assert "[noop]" in capsys.readouterr().out


def test_without_pr_an_open_issue_is_only_relabelled_as_before(ci, monkeypatch, capsys) -> None:
    """The unchanged path: no close, no comment — a warning and the label
    reconcile, exactly as pr-merge mode always did."""
    rec = _run(ci, monkeypatch, ["42", "--mode", "pr-merge", "--yes"], issue=_issue())
    assert rec.rc == 0
    assert rec.pr_reads == []
    writes = _writes(rec)
    assert not any(c[:3] in (["gh", "issue", "comment"], ["gh", "issue", "close"]) for c in writes)
    assert any(c[:3] == ["gh", "issue", "edit"] for c in writes)
    assert "still open" in capsys.readouterr().err
