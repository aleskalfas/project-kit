"""One reading of an issue's state, shared by move-issue and the verbs composing over it (#1242).

`_lib/issue_position` is where move-issue, start-work and review-work take an
issue's current state from: the process engine's position, else the issue's
own fields. `_lib/composed_move` is what start-work and review-work share
around it: the early refusal, the move-issue run that is handed the reading,
and the failure naming what a run left behind. The verbs' own tests drive these
through their `main()`; this file pins the pieces, and that a composing verb's
move-issue judges from the status the verb read instead of asking the engine
again.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"
CAPABILITY_ROOT = SCRIPTS_DIR.parent

sys.path.insert(0, str(SCRIPTS_DIR))
from _lib import axis_labels, composed_move, issue_position  # noqa: E402

TASK = {"title": "[Task] a thing", "state": "OPEN", "milestone": None, "body": ""}
NO_BOARD: dict[str, Any] = {}
BOARD = {"has_projects_v2_board": True}


def _status(state: str | None, *, indeterminate: bool = False) -> dict[str, Any]:
    return {"position": {"state": state, "indeterminate": indeterminate}, "journal": [{}]}


def _read(status, labels, config=NO_BOARD, substrate_map=None, issue=TASK):
    return issue_position.read(
        issue, status, labels=labels, config=config, substrate_map=substrate_map
    )


# ---- read: the engine first, else the issue's fields --------------------


def test_the_engine_position_wins_over_the_label() -> None:
    status = _status("in-progress")
    position = _read(status, ["state:backlog"])
    assert position == issue_position.Position("in-progress", status)


@pytest.mark.parametrize(
    "status",
    [None, _status(None, indeterminate=True), _status(None), {"position": "garbled"}],
    ids=["no-answer", "indeterminate", "no-state", "garbled"],
)
def test_without_an_engine_position_the_label_is_read(status) -> None:
    position = _read(status, ["state:backlog"])
    assert position.state == "backlog"
    assert position.unread is None
    assert position.status is status


def test_no_state_label_and_no_milestone_reads_todo_as_before() -> None:
    assert _read(None, ["type:task"]) == issue_position.Position("todo")


def test_a_milestone_reads_backlog_and_a_closed_issue_done() -> None:
    assert _read(None, [], issue={**TASK, "milestone": {"title": "M1"}}).state == "backlog"
    assert _read(None, ["state:review"], issue={**TASK, "state": "CLOSED"}).state == "done"


def test_a_derive_bound_state_is_read_off_open_or_closed() -> None:
    derive = axis_labels.SubstrateMap(axes={"state": {"derive": {"predicate": "open-closed"}}})
    position = _read(None, ["state:todo"], config=BOARD, substrate_map=derive)
    assert position.unread is None  # the map binds state, so the board does not carry it
    assert position.state == axis_labels.derive_state(is_closed=False, labels=["state:todo"])


def test_a_board_state_without_an_engine_position_is_flagged_unread() -> None:
    position = _read(None, ["state:backlog"], config=BOARD)
    assert position.state == "backlog"  # the stand-in move-issue still moves from
    assert position.unread == issue_position.UNREAD_ON_BOARD


def test_a_board_state_the_engine_places_is_a_reading() -> None:
    status = _status("review")
    assert _read(status, [], config=BOARD) == issue_position.Position("review", status)


# ---- engine_status: asked once per run ----------------------------------


class _NoSubprocess:
    def __call__(self, *a: Any, **kw: Any) -> Any:
        raise AssertionError(f"the engine was asked: {a}")


def test_a_handed_down_status_is_taken_without_asking_the_engine(monkeypatch) -> None:
    status = _status("backlog")
    monkeypatch.setenv(*_entry(issue_position.handed_down(42, status)))
    monkeypatch.setattr(issue_position.subprocess, "run", _NoSubprocess())
    assert issue_position.engine_status(42) == status
    assert issue_position.HANDED_DOWN_ENV not in issue_position.os.environ


def test_a_handed_down_none_says_the_engine_gave_nothing_in_this_run(monkeypatch) -> None:
    monkeypatch.setenv(*_entry(issue_position.handed_down(42, None)))
    monkeypatch.setattr(issue_position.subprocess, "run", _NoSubprocess())
    assert issue_position.engine_status(42) is None


def test_a_status_handed_down_for_another_issue_is_dropped_and_the_engine_asked(
    monkeypatch,
) -> None:
    monkeypatch.setenv(*_entry(issue_position.handed_down(7, _status("review"))))
    asked: list[list[str]] = []

    def run(argv, **kw):
        asked.append(argv)
        return subprocess.CompletedProcess(argv, 0, json.dumps(_status("backlog")), "")

    monkeypatch.setattr(issue_position.subprocess, "run", run)
    assert issue_position.engine_status(42) == _status("backlog")
    assert asked == [
        [
            "pkit",
            "process",
            "status",
            issue_position.PROCESS_ADDRESS,
            "--subject",
            "42",
            "--json",
        ]
    ]
    assert issue_position.HANDED_DOWN_ENV not in issue_position.os.environ


@pytest.mark.parametrize(
    "outcome",
    [
        subprocess.CompletedProcess([], 1, "", "boom"),
        subprocess.CompletedProcess([], 0, "not json", ""),
        subprocess.CompletedProcess([], 0, "[]", ""),
    ],
    ids=["failed", "unparseable", "not-an-object"],
)
def test_an_engine_that_cannot_answer_reads_none(monkeypatch, outcome) -> None:
    monkeypatch.setattr(issue_position.subprocess, "run", lambda argv, **kw: outcome)
    assert issue_position.engine_status(42) is None


def test_no_pkit_on_path_reads_none(monkeypatch) -> None:
    def missing(argv, **kw):
        raise FileNotFoundError("pkit")

    monkeypatch.setattr(issue_position.subprocess, "run", missing)
    assert issue_position.engine_status(42) is None


def _entry(env: dict[str, str]) -> tuple[str, str]:
    ((name, value),) = env.items()
    return name, value


# ---- composed_move: the shared refusal, run and failure -----------------


def test_the_move_issue_run_is_handed_the_status_the_check_read(monkeypatch) -> None:
    status = _status("backlog")
    seen: list[tuple[list[str], dict[str, str]]] = []

    def run(cmd, check, env):
        seen.append((cmd, env))
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(composed_move.subprocess, "run", run)
    rc = composed_move.invoke_move_issue(
        42,
        "in-progress",
        issue_position.Position("backlog", status),
        capability_root_arg=Path("/cap"),
        allow_foreign_repo=True,
    )
    assert rc == 0
    ((cmd, env),) = seen
    assert cmd[1].endswith("move-issue.py")
    assert cmd[2:] == [
        "42",
        "--to",
        "in-progress",
        "--yes",
        "--allow-foreign-repo",
        "--capability-root",
        "/cap",
    ]
    assert json.loads(env[issue_position.HANDED_DOWN_ENV]) == {"issue": 42, "status": status}
    # Only the child's environment carries it.
    assert issue_position.HANDED_DOWN_ENV not in issue_position.os.environ


def test_the_shortest_legal_path_names_each_move_on_the_way() -> None:
    workflow = _shipped_workflow()
    assert composed_move.moves_before(workflow, "todo", "review", "task") == [
        "backlog",
        "in-progress",
    ]
    assert composed_move.moves_before(workflow, "todo", "in-progress", "task") == ["backlog"]
    assert composed_move.moves_before(workflow, "review", "in-progress", "task") == []


def test_the_late_failure_names_what_was_left_and_how_to_undo_it() -> None:
    message = composed_move.late_failure_message(
        "start-work",
        42,
        "in-progress",
        3,
        left=[("branch 'fix/42-x' (created and checked out)", "git branch -D fix/42-x")],
        nothing_left="This run created no branch and wrote no assignee.",
        reuses="the branch",
    )
    assert message.splitlines()[1:] == [
        "[failed] start-work #42: move-issue --to in-progress failed (exit 3); "
        "the issue did not move.",
        "  Left behind by this run:",
        "  - branch 'fix/42-x' (created and checked out). Undo: `git branch -D fix/42-x`",
        "  Fix the cause above and re-run `start-work 42` (it reuses the branch).",
    ]


def test_the_late_failure_of_a_run_that_left_nothing_says_so() -> None:
    message = composed_move.late_failure_message(
        "review-work",
        42,
        "review",
        2,
        left=[],
        nothing_left="This run opened no PR, made none ready and requested no reviewers.",
        reuses="the ready PR",
    )
    assert "Left behind" not in message
    assert "  This run opened no PR, made none ready and requested no reviewers." in message


def _shipped_workflow() -> dict[str, Any]:
    from ruamel.yaml import YAML

    return YAML(typ="safe").load((CAPABILITY_ROOT / "schemas" / "workflow.yaml").read_text())


# ---- move-issue moves from the handed-down reading ----------------------


@pytest.fixture(scope="module")
def mi():
    spec = importlib.util.spec_from_file_location(
        "pm_move_issue_position_under_test", SCRIPTS_DIR / "move-issue.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["pm_move_issue_position_under_test"] = module
    spec.loader.exec_module(module)
    return module


def test_move_issue_moves_from_the_handed_down_status_without_asking_again(mi, monkeypatch) -> None:
    """The label says Todo, the status start-work handed down says Backlog: the
    move to In Progress is made from Backlog, and the engine is not asked for a
    status again (`pkit process move` still journals it)."""
    invoker = SimpleNamespace(github_login="octocat", email="o@e.com")
    monkeypatch.setattr(mi, "resolve_capability_root", lambda arg: CAPABILITY_ROOT)
    monkeypatch.setattr(mi, "_read_members", lambda root, loader: [])
    monkeypatch.setattr(mi, "resolve_invoker_identity", lambda config=None: invoker)
    monkeypatch.setattr(mi, "check_membership", lambda m, i: SimpleNamespace(allowed=True))
    monkeypatch.setattr(mi.session_guard, "enforce", lambda **kw: True)
    monkeypatch.setattr(mi.bootstrap_gate, "enforce", lambda *a, **kw: True)
    monkeypatch.setattr(
        mi,
        "_gh_get_issue",
        lambda n, config: {
            "title": "[Task] a thing",
            "body": "",
            "state": "OPEN",
            "labels": [{"name": "type:task"}, {"name": "state:todo"}],
            "milestone": None,
        },
    )
    monkeypatch.setattr(mi.axis_carriage, "is_board_carried", lambda *a, **kw: False)
    monkeypatch.setattr(mi, "detect_placeholder_residuals", lambda **kw: [])
    plans: list[Any] = []

    def apply_label(n: int, plan: Any, config: dict) -> bool:
        plans.append(plan)
        return True

    monkeypatch.setattr(mi, "_gh_apply_state_label", apply_label)
    monkeypatch.setattr(mi, "fire_hooks", lambda name, **kw: None)
    pkit_calls: list[list[str]] = []

    def run(argv, **kw):
        pkit_calls.append(list(argv))
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(mi.subprocess, "run", run)
    monkeypatch.setenv(*_entry(issue_position.handed_down(42, _status("backlog"))))
    monkeypatch.setattr(
        sys, "argv", ["move-issue.py", "42", "--to", "in-progress", "--yes", "--no-cascade"]
    )

    assert mi.main() == 0
    assert [call[:3] for call in pkit_calls] == [["pkit", "process", "move"]]
    move = pkit_calls[0]
    assert move[move.index("--from") + 1] == "backlog"
    (plan,) = plans
    assert (plan.add_label, plan.remove_label) == ("state:in-progress", "state:todo")
