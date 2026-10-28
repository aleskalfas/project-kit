"""close-issue --mode completed --result <where> (#2282).

A Task whose work was not a pull request, such as an audit, an investigation or
a decision walked with the user, closes as completed once every checkbox is
ticked, on the person's authorisation, naming where the work's result lives
(DEC-006, the `manual-completed` closure trigger). The close comment carries the
result, GitHub records the Task as completed, its labels are reconciled to done,
and the move is journaled from where the Task was. Completed work is progress,
so the forward cascade then runs, through move-issue, before the closure
cascade. A Task in Review, a container, an unticked box and a missing result
are refused, writing nothing. Every `gh` call and the move-issue run are faked.
The person's authorisation is test_pm_close_issue's, the journal entry against
the real engine is test_pm_close_issue_journal's, and the ancestors the real
move-issue brings level are test_pm_move_issue_forward_cascade's.
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

# The line the faked move-issue prints, so its place in the output can be read.
MOVE_ISSUE_RAN = "[fake] move-issue ran"
CLOSURE_CASCADE = "[cascade] parents to check for eligibility: #10"


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
    move_issue_rc: int = 0,
    card=None,
) -> SimpleNamespace:
    """Run main() with every gate passed; record each `gh` call, each move
    handed to the engine, and each move-issue run, which exits `move_issue_rc`
    and prints a line saying it ran. With ``card``, a `StatusRead`, the map binds
    the state to the board and the open Task's card reads as ``card``."""
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
    on_board = (
        ci.axis_labels.SubstrateMap(axes={"state": {"board": True}}) if card is not None else None
    )
    monkeypatch.setattr(ci.axis_labels, "load_substrate_map", lambda *_a, **_k: on_board)
    if card is not None:
        monkeypatch.setattr(ci.issue_position, "read_status", lambda *_a, **_k: card)
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
    moved: list[tuple] = []

    def fake_move_issue(issue_number, target, **kwargs):
        moved.append((issue_number, target, kwargs))
        print(MOVE_ISSUE_RAN)
        return move_issue_rc

    monkeypatch.setattr(ci.composed_move, "invoke_move_issue", fake_move_issue)
    rc = ci.main()
    return SimpleNamespace(rc=rc, calls=calls, journaled=journaled, moved=moved)


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
    # Completed work is progress: the forward cascade runs from each origin.
    assert [(n, target) for n, target, _ in rec.moved] == [(42, "done")]


def test_a_task_recovered_from_its_kind_prefix_closes(ci, monkeypatch) -> None:
    """A Task's kind prefix, such as [Chore] or [Docs], is a Task's title."""
    rec = _run(ci, monkeypatch, COMPLETED, issue=_issue(title="[Docs] Write the guide"))
    assert rec.rc == 0


def _parent() -> dict:
    return {"title": "[EPIC] e", "state": "OPEN", "body": "## What\n", "labels": []}


def test_the_forward_cascade_runs_and_then_the_closure_cascade(ci, monkeypatch, capsys) -> None:
    """move-issue, run on the closed Task, brings its ancestors level first, so
    the closure cascade then reads them where the forward cascade left them."""
    rec = _run(ci, monkeypatch, COMPLETED, issue=_issue(), parents={10: _parent()})
    assert rec.rc == 0
    out = capsys.readouterr().out
    assert out.index("[ok] closed #42") < out.index(MOVE_ISSUE_RAN) < out.index(CLOSURE_CASCADE)
    assert "eligible to close: run `pkit pm close-issue 10 --mode=cascade-eligibility-close`" in out
    assert rec.moved == [(42, "done", {"capability_root_arg": None, "allow_foreign_repo": False})]


def test_move_issue_is_handed_the_capability_root_and_the_operator_s_confirmation(
    ci, monkeypatch, tmp_path: Path
) -> None:
    argv = [*COMPLETED, "--capability-root", str(tmp_path), "--allow-foreign-repo"]
    rec = _run(ci, monkeypatch, argv, issue=_issue())
    assert rec.rc == 0
    assert rec.moved == [
        (42, "done", {"capability_root_arg": tmp_path, "allow_foreign_repo": True})
    ]


def test_no_cascade_runs_neither_cascade(ci, monkeypatch, capsys) -> None:
    rec = _run(
        ci, monkeypatch, [*COMPLETED, "--no-cascade"], issue=_issue(), parents={10: _parent()}
    )
    assert rec.rc == 0
    assert rec.moved == []
    assert CLOSURE_CASCADE not in capsys.readouterr().out


def test_a_forward_cascade_move_issue_could_not_run_is_a_warning_and_the_close_stands(
    ci, monkeypatch, capsys
) -> None:
    rec = _run(ci, monkeypatch, COMPLETED, issue=_issue(), parents={10: _parent()}, move_issue_rc=1)
    assert rec.rc == 0
    assert ["gh", "issue", "close", "42", "--reason", "completed"] in _writes(rec)
    out, err = capsys.readouterr()
    assert (
        "[warn] the forward cascade from #42 did not run: move-issue exited 1, and the "
        "close stands."
    ) in err
    assert "run `move-issue 42 --to done`: the cascade is idempotent" in err
    assert CLOSURE_CASCADE in out


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
    assert rec.moved == []
    assert "[dry-run]" in capsys.readouterr().out


def test_an_issue_already_closed_is_left_as_it_is(ci, monkeypatch, capsys) -> None:
    rec = _run(ci, monkeypatch, COMPLETED, issue=_issue(state="CLOSED"))
    assert rec.rc == 0
    assert _writes(rec) == []
    assert rec.moved == []
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
    assert rec.moved == []
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
    assert rec.moved == []
    err = capsys.readouterr().err
    assert "[refused] #42 is in Review" in err
    assert "done-work 42" in err


# --- a board-carried state (DEC-062 point 5, DEC-051 point 6) -------------------


def test_where_the_board_carries_the_state_the_card_says_where_the_task_was(
    ci, monkeypatch
) -> None:
    """The card's Status, not the label, is where the move to done comes from."""
    card = ci.infer.StatusRead("placed", state="backlog")
    rec = _run(ci, monkeypatch, COMPLETED, issue=_issue(labels=("state:review",)), card=card)
    assert rec.rc == 0
    assert ["gh", "issue", "close", "42", "--reason", "completed"] in _writes(rec)
    [move] = rec.journaled
    assert move[:3] == (42, "backlog", "done")


def test_a_card_in_review_is_refused(ci, monkeypatch, capsys) -> None:
    card = ci.infer.StatusRead("placed", state="review")
    rec = _run(ci, monkeypatch, COMPLETED, issue=_issue(labels=()), card=card)
    assert rec.rc == 1
    assert _writes(rec) == []
    assert "[refused] #42 is in Review" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("card", "rc", "finding"),
    [
        (("unreadable", None, "gh: timeout"), 3, "the board's Status of #42 could not be read"),
        (("no-card", None, ""), 1, "#42 has no card on the board"),
        (("unset", None, ""), 1, "#42's card on the board has no Status"),
        (("not-open", None, "Done"), 1, "has the Status 'Done', which names no open state"),
    ],
)
def test_a_card_that_places_the_task_nowhere_refuses_the_close(
    ci, monkeypatch, capsys, card: tuple, rc: int, finding: str
) -> None:
    """Nothing can tell a Task in Review then, so nothing is guessed: no write,
    no move journaled, no cascade (DEC-051 point 6)."""
    outcome, state, said = card
    read = ci.infer.StatusRead(outcome, state=state, said=said)
    rec = _run(ci, monkeypatch, COMPLETED, issue=_issue(labels=("state:in-progress",)), card=read)
    assert rec.rc == rc
    assert _writes(rec) == []
    assert rec.journaled == []
    assert rec.moved == []
    err = capsys.readouterr().err
    assert "[refused] close-issue #42: " in err
    assert finding in err
    assert "Nothing was changed (the Task is still open)" in err


def test_a_won_t_do_close_of_a_task_its_card_places_nowhere_closes_and_warns(
    ci, monkeypatch, capsys
) -> None:
    """A won't-do close needs no origin: it closes, and its move is not recorded
    from a guessed one."""
    card = ci.infer.StatusRead("unset")
    argv = ["42", "--reason", "superseded", "--yes"]
    rec = _run(ci, monkeypatch, argv, issue=_issue(labels=("state:todo",)), card=card)
    assert rec.rc == 0
    assert ["gh", "issue", "close", "42", "--reason", "not planned"] in _writes(rec)
    assert rec.journaled == []
    assert "this move was not recorded: #42's card on the board has no Status" in (
        capsys.readouterr().err
    )


@pytest.mark.parametrize(
    "title", ["[Feature] a container", "[EPIC] an epic", "[CR] an unrecognised prefix"]
)
def test_anything_but_a_task_is_refused(ci, monkeypatch, capsys, title: str) -> None:
    rec = _run(ci, monkeypatch, COMPLETED, issue=_issue(title=title))
    assert rec.rc == 2
    assert _writes(rec) == []
    assert rec.moved == []
    assert "--mode=completed closes a Task" in capsys.readouterr().err


def test_result_outside_completed_mode_is_a_usage_error(ci, monkeypatch, capsys) -> None:
    argv = ["close-issue", "42", "--reason", "superseded", "--result", RESULT]
    monkeypatch.setattr(sys, "argv", argv)
    assert ci.main() == 2
    assert "--result applies to --mode=completed only" in capsys.readouterr().err
