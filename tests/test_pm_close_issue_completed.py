"""close-issue --mode completed --result <where> (#2282).

A Task whose work was not a pull request, such as an audit, an investigation or
a decision walked with the user, closes as completed once every checkbox is
ticked, on the person's authorisation, naming where the work's result lives
(DEC-006, the `manual-completed` closure trigger). The close comment carries the
result, GitHub records the Task as completed, its labels are reconciled to done,
and the move is journaled from where the Task was. A Task in Review, a
container, an unticked box and a missing result are refused, writing nothing.
Every `gh` call is faked; the person's authorisation is
test_pm_close_issue's, and the journal entry against the real engine is
test_pm_close_issue_journal's.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from ruamel.yaml import YAML

REPO_ROOT = Path(__file__).resolve().parent.parent
CAP_ROOT = REPO_ROOT / ".pkit" / "capabilities" / "project-management"
SCRIPT_PATH = CAP_ROOT / "scripts" / "close-issue.py"

RESULT = "the findings are filed as #908"
COMPLETED = ["42", "--mode", "completed", "--result", RESULT, "--yes"]


@pytest.fixture(scope="module")
def ci():
    module_name = "pm_close_issue_completed_under_test"
    spec = importlib.util.spec_from_file_location(module_name, SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _issue(
    *,
    title="[Chore] Audit the merged pull requests",
    state="OPEN",
    body="EPIC: #10\n\n## What\nx\n\n## Acceptance criteria\n\n- [x] audited\n",
    labels=("state:in-progress",),
) -> dict:
    return {
        "title": title,
        "body": body,
        "state": state,
        "labels": [{"name": n} for n in labels],
        "milestone": None,
    }


def _run(
    ci,
    monkeypatch,
    argv: list[str],
    *,
    issue: dict,
    comments: list | None = None,
    parents: dict | None = None,
) -> SimpleNamespace:
    """Run main() with every gate passed; record each `gh` call and each move
    handed to the engine."""
    monkeypatch.setattr(sys, "argv", ["close-issue", *argv])
    monkeypatch.setattr(ci, "resolve_capability_root", lambda _explicit: CAP_ROOT)
    monkeypatch.setattr(ci.bootstrap_gate, "enforce", lambda *a, **k: True)
    monkeypatch.setattr(ci.session_guard, "enforce", lambda **k: True)
    monkeypatch.setattr(ci, "load_adopter_config", lambda _root: {})
    monkeypatch.setattr(ci, "_read_members", lambda *a: [])
    monkeypatch.setattr(
        ci, "resolve_invoker_identity", lambda **k: SimpleNamespace(github_login="me")
    )
    monkeypatch.setattr(ci, "check_membership", lambda *a: SimpleNamespace(allowed=True))
    monkeypatch.setattr(ci.axis_labels, "load_substrate_map", lambda *_a, **_k: None)
    monkeypatch.setattr(ci, "fire_hooks", lambda *a, **k: None)
    journaled: list[tuple] = []
    monkeypatch.setattr(ci, "journal_move", lambda *a, **k: journaled.append((*a, k)))

    issues = {42: issue, **(parents or {})}
    monkeypatch.setattr(ci, "_gh_get_issue", lambda n, _config: issues.get(n))
    monkeypatch.setattr(ci, "_engine_cascade_fold", lambda _n: {"opened": True})
    monkeypatch.setattr(
        ci.containment,
        "read_issue_record",
        lambda _config, *, issue_number: ci.containment.IssueRecord(
            issue=issues[int(issue_number)], parent=None
        ),
    )

    def no_pr_read(_n, _config):
        raise AssertionError("a completed close reads no pull request")

    monkeypatch.setattr(ci, "_gh_get_pr", no_pr_read)
    calls: list[list[str]] = []

    def fake_gh_run(cmd, config, **kwargs):
        calls.append(cmd)
        stdout = ""
        if cmd[:3] == ["gh", "issue", "view"] and "comments" in cmd:
            stdout = json.dumps({"comments": comments or []})
        return subprocess.CompletedProcess(cmd, 0, stdout=stdout, stderr="")

    monkeypatch.setattr(ci, "gh_run", fake_gh_run)
    rc = ci.main()
    return SimpleNamespace(rc=rc, calls=calls, journaled=journaled)


def _writes(rec) -> list[list[str]]:
    return [c for c in rec.calls if c[:3] != ["gh", "issue", "view"]]


def _comment(rec) -> str:
    comment = next(c for c in _writes(rec) if c[:3] == ["gh", "issue", "comment"])
    return comment[comment.index("--body") + 1]


# --- the shipped workflow -----------------------------------------------------


def _shipped_workflow() -> dict:
    return YAML(typ="safe").load((CAP_ROOT / "schemas" / "workflow.yaml").read_text())


@pytest.mark.parametrize("origin", ["todo", "backlog", "in-progress"])
def test_the_shipped_workflow_declares_a_task_s_close_from_each_state_it_takes(
    origin: str,
) -> None:
    """Todo, Backlog and In Progress → Done are declared for a Task, made by
    close-issue, held by the user at hard-reject, gated on every checkbox."""
    process = _shipped_workflow()["process"]
    (close,) = [
        t
        for t in process["transitions"]
        if (t["from"], t["to"]) == (origin, "done") and t["command"] == "close-issue"
    ]
    assert "[issue-types:task]" in close["applies_to"]
    assert (close["authorisation"], close["severity"]) == (
        "user",
        "[validation-severity:hard-reject]",
    )
    assert close["gate"]["predicate"]["run"] == "gate-checkboxes-ticked"


def test_review_to_done_stays_the_merge_s_alone() -> None:
    process = _shipped_workflow()["process"]
    closes = [t for t in process["transitions"] if (t["from"], t["to"]) == ("review", "done")]
    assert [t["command"] for t in closes] == ["done-work"]


def test_the_shipped_workflow_names_the_closure_trigger() -> None:
    triggers = {t["id"]: t for t in _shipped_workflow()["closure_triggers"]}
    assert triggers["manual-completed"]["applies_to"] == ["[issue-types:task]"]
    assert triggers["manual-completed"]["target_state"] == "done"


# --- the close ----------------------------------------------------------------


@pytest.mark.parametrize("origin", ["todo", "backlog", "in-progress"])
def test_closes_a_task_as_completed_naming_where_its_result_lives(
    ci, monkeypatch, capsys, origin: str
) -> None:
    rec = _run(ci, monkeypatch, COMPLETED, issue=_issue(labels=(f"state:{origin}",)))
    assert rec.rc == 0
    writes = _writes(rec)
    body = _comment(rec)
    assert body.startswith(f"[completed close] the work's result: {RESULT}\n")
    assert "close-issue --mode=completed" in body
    assert ["gh", "issue", "close", "42", "--reason", "completed"] in writes
    # The comment comes before the close, so a failed close leaves the result named.
    comment_at = next(i for i, c in enumerate(writes) if c[:3] == ["gh", "issue", "comment"])
    assert comment_at < writes.index(["gh", "issue", "close", "42", "--reason", "completed"])
    label_edit = next(c for c in writes if c[:3] == ["gh", "issue", "edit"])
    assert label_edit[label_edit.index("--add-label") + 1] == "state:done"
    [move] = rec.journaled
    assert move[:3] == (42, origin, "done")
    assert move[-1]["reason"] == f"completed close: {RESULT}"
    out = capsys.readouterr().out
    assert f"result: {RESULT}" in out
    assert "[ok] closed #42 (completed, without a pull request)." in out


def test_a_task_recovered_from_its_kind_prefix_closes(ci, monkeypatch) -> None:
    """A Task's kind prefix, such as [Chore] or [Docs], is a Task's title."""
    rec = _run(ci, monkeypatch, COMPLETED, issue=_issue(title="[Docs] Write the guide"))
    assert rec.rc == 0


def test_the_closure_cascade_runs_on_the_parent(ci, monkeypatch, capsys) -> None:
    parent = {"title": "[EPIC] e", "state": "OPEN", "body": "## What\n", "labels": []}
    rec = _run(ci, monkeypatch, COMPLETED, issue=_issue(), parents={10: parent})
    assert rec.rc == 0
    out = capsys.readouterr().out
    assert "[cascade] parents to check for eligibility: #10" in out
    assert "eligible to close: run `pkit pm close-issue 10 --mode=cascade-eligibility-close`" in out


def test_the_comment_is_posted_once_across_a_retry(ci, monkeypatch) -> None:
    """A run that posted the result and then failed to close finds it on the
    re-run and does not post it again (the shared audit idempotence)."""
    _key, body = ci._completed_close_comment(RESULT)
    posted = [{"body": body, "viewerDidAuthor": True, "includesCreatedEdit": False}]
    rec = _run(ci, monkeypatch, COMPLETED, issue=_issue(), comments=posted)
    assert rec.rc == 0
    assert not any(c[:3] == ["gh", "issue", "comment"] for c in _writes(rec))
    assert ["gh", "issue", "close", "42", "--reason", "completed"] in _writes(rec)


def test_the_result_is_stripped_before_it_is_posted(ci, monkeypatch) -> None:
    argv = ["42", "--mode", "completed", "--result", f"  {RESULT}\n", "--yes"]
    rec = _run(ci, monkeypatch, argv, issue=_issue())
    assert rec.rc == 0
    assert _comment(rec).startswith(f"[completed close] the work's result: {RESULT}\n")


def test_dry_run_writes_nothing(ci, monkeypatch, capsys) -> None:
    argv = ["42", "--mode", "completed", "--result", RESULT, "--dry-run"]
    rec = _run(ci, monkeypatch, argv, issue=_issue())
    assert rec.rc == 0
    assert _writes(rec) == []
    assert rec.journaled == []
    assert "[dry-run]" in capsys.readouterr().out


def test_an_issue_already_closed_is_left_as_it_is(ci, monkeypatch, capsys) -> None:
    rec = _run(ci, monkeypatch, COMPLETED, issue=_issue(state="CLOSED"))
    assert rec.rc == 0
    assert _writes(rec) == []
    assert "[noop] issue already closed." in capsys.readouterr().out


# --- what is refused ----------------------------------------------------------


@pytest.mark.parametrize("extra", [[], ["--skip-checkbox-gate"]], ids=["plain", "skip-asked"])
def test_an_unticked_box_is_refused_and_the_gate_is_not_skippable(
    ci, monkeypatch, capsys, extra: list[str]
) -> None:
    body = "EPIC: #10\n\n## Acceptance criteria\n\n- [x] audited\n- [ ] findings filed\n"
    rec = _run(ci, monkeypatch, [*COMPLETED, *extra], issue=_issue(body=body))
    assert rec.rc == 1
    assert _writes(rec) == []
    assert rec.journaled == []
    err = capsys.readouterr().err
    assert "findings filed" in err
    assert "not skippable" in err


@pytest.mark.parametrize("result", [None, "", "   "], ids=["missing", "empty", "blank"])
def test_a_close_that_names_no_result_is_refused(
    ci, monkeypatch, capsys, result: str | None
) -> None:
    argv = ["42", "--mode", "completed", "--yes"]
    if result is not None:
        argv += ["--result", result]
    rec = _run(ci, monkeypatch, argv, issue=_issue())
    assert rec.rc == 2
    assert _writes(rec) == []
    assert "--result is required in completed mode" in capsys.readouterr().err


def test_a_task_in_review_is_refused(ci, monkeypatch, capsys) -> None:
    """A Task in Review has a pull request open: it closes through its merge."""
    rec = _run(ci, monkeypatch, COMPLETED, issue=_issue(labels=("state:review",)))
    assert rec.rc == 1
    assert _writes(rec) == []
    assert rec.journaled == []
    err = capsys.readouterr().err
    assert "[refused] #42 is in Review" in err
    assert "done-work 42" in err


@pytest.mark.parametrize(
    "title", ["[Feature] a container", "[EPIC] an epic", "[CR] an unrecognised prefix"]
)
def test_anything_but_a_task_is_refused(ci, monkeypatch, capsys, title: str) -> None:
    rec = _run(ci, monkeypatch, COMPLETED, issue=_issue(title=title))
    assert rec.rc == 2
    assert _writes(rec) == []
    assert "--mode=completed closes a Task" in capsys.readouterr().err


def test_result_outside_completed_mode_is_a_usage_error(ci, monkeypatch, capsys) -> None:
    argv = ["close-issue", "42", "--reason", "superseded", "--result", RESULT]
    monkeypatch.setattr(sys, "argv", argv)
    assert ci.main() == 2
    assert "--result applies to --mode=completed only" in capsys.readouterr().err
