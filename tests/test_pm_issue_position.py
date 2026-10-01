"""The reading of an issue's state that start-work, review-work and move-issue share (#1242).

`_lib/issue_position` is where the three take the state of the issue being
moved from: the process engine's position, else the issue's own fields. Each
reads it at its own moment — the verb for its early check, move-issue again
when it moves. `_lib/composed_move` is what start-work and review-work share
around it: the early refusal, the move-issue run and the failure naming what a
run left behind. The verbs' own tests drive these through their `main()`; this
file pins the pieces, and that nothing in the environment stands in for
move-issue's own read.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from tests.pm_composed_move_support import (
    CAPABILITY_ROOT,
    SCRIPTS_DIR,
    FakeEngine,
    MoveIssueInProcess,
    status_at,
)

sys.path.insert(0, str(SCRIPTS_DIR))
from _lib import axis_labels, composed_move, issue_position

TASK = {"title": "[Task] a thing", "state": "OPEN", "milestone": None, "body": ""}
NO_BOARD: dict[str, Any] = {}
BOARD = {"has_projects_v2_board": True}
NO_ANSWER = issue_position.EngineAnswer(failure="`pkit` was not found on PATH")
# The variable an earlier revision of #1242 handed the engine's answer down in.
# Nothing reads it; the tests below hold that.
HAND_DOWN_ENV = "PKIT_PM_ISSUE_STATUS"


def _answer(status: dict[str, Any] | None) -> issue_position.EngineAnswer:
    return issue_position.EngineAnswer(status)


def _read(engine, labels, config=NO_BOARD, substrate_map=None, issue=TASK):
    return issue_position.read(
        issue, engine, labels=labels, config=config, substrate_map=substrate_map
    )


# ---- read: the engine first, else the issue's fields --------------------


def test_the_engine_position_wins_over_the_label() -> None:
    # The shipped engine reads these same labels, so the two disagree only when
    # the labels changed between the reads; the resolver takes the engine's.
    engine = _answer(status_at("in-progress"))
    position = _read(engine, ["state:backlog"])
    assert position == issue_position.Position("in-progress", engine.status)


@pytest.mark.parametrize(
    "engine",
    [
        NO_ANSWER,
        _answer({"position": {"state": None, "indeterminate": True}}),
        _answer({"position": {"state": None, "indeterminate": False}}),
        _answer({"subject": "42", "position": "garbled"}),
        _answer({"subject": "42", "position": {"state": {"id": "done"}}}),
        _answer({"subject": "42"}),
    ],
    ids=["no-answer", "indeterminate", "no-state", "garbled", "state-not-a-string", "no-position"],
)
def test_without_an_engine_position_the_label_is_read(engine) -> None:
    position = _read(engine, ["state:backlog"])
    assert position.state == "backlog"
    assert position.unread is None
    assert position.status is engine.status


def test_no_state_label_and_no_milestone_reads_todo_as_before() -> None:
    assert _read(NO_ANSWER, ["type:task"]) == issue_position.Position("todo")


def test_a_milestone_reads_backlog_and_a_closed_issue_done() -> None:
    assert _read(NO_ANSWER, [], issue={**TASK, "milestone": {"title": "M1"}}).state == "backlog"
    assert _read(NO_ANSWER, ["state:review"], issue={**TASK, "state": "CLOSED"}).state == "done"


def test_a_derive_bound_state_is_read_off_open_or_closed() -> None:
    derive = axis_labels.SubstrateMap(axes={"state": {"derive": {"predicate": "open-closed"}}})
    position = _read(NO_ANSWER, ["state:todo"], config=BOARD, substrate_map=derive)
    assert position.unread is None  # the map binds state, so the board does not carry it
    assert position.state == axis_labels.derive_state(is_closed=False, labels=["state:todo"])


def test_a_board_state_without_an_engine_position_is_flagged_unread() -> None:
    position = _read(NO_ANSWER, ["state:backlog"], config=BOARD)
    assert position.state == "backlog"  # the stand-in move-issue still moves from
    assert position.unread == issue_position.Unread("`pkit` was not found on PATH")


def test_a_board_state_the_engine_places_is_not_flagged() -> None:
    # The shipped engine places the issue from these same labels; where it
    # answers, its position is taken and nothing is flagged.
    engine = _answer(status_at("review"))
    assert _read(engine, ["state:review"], config=BOARD) == issue_position.Position(
        "review", engine.status
    )


@pytest.mark.parametrize(
    "status",
    [
        {"subject": "42", "position": "garbled"},
        {"subject": "42", "position": {"state": 7}},
        {"subject": "42", "position": {"indeterminate": True, "unevaluated": 5}},
        {"subject": "42", "position": {"indeterminate": True, "unevaluated": ["x", 1]}},
        {"subject": "42", "position": {"indeterminate": True, "unevaluated": "garbled"}},
    ],
    ids=["position", "state", "unevaluated-int", "unevaluated-entries", "unevaluated-str"],
)
def test_a_malformed_answer_that_names_the_issue_reads_as_no_position(status) -> None:
    """An answer naming the issue whose position is not in the engine's shape
    is the engine giving nothing: not trusted, and no crash."""
    position = _read(_answer(status), ["state:backlog"], config=BOARD)
    assert position.state == "backlog"
    assert position.unread is not None
    assert position.unread.said == ""


# ---- why the engine gave no position: three causes told apart ------------


def _ask(monkeypatch, outcome) -> issue_position.EngineAnswer:
    def run(argv, **kw):
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome

    monkeypatch.setattr(issue_position.subprocess, "run", run)
    return issue_position.ask_engine(42)


def test_an_engine_answer_is_its_payload(monkeypatch) -> None:
    asked: list[list[str]] = []

    def run(argv, **kw):
        asked.append(argv)
        return subprocess.CompletedProcess(argv, 0, json.dumps(status_at("backlog")), "")

    monkeypatch.setattr(issue_position.subprocess, "run", run)
    assert issue_position.ask_engine(42) == issue_position.EngineAnswer(status_at("backlog"))
    assert asked == [
        ["pkit", "process", "status", issue_position.PROCESS_ADDRESS, "--subject", "42", "--json"]
    ]


def test_no_pkit_on_path_says_so(monkeypatch) -> None:
    answer = _ask(monkeypatch, FileNotFoundError("pkit"))
    assert answer == issue_position.EngineAnswer(failure="`pkit` was not found on PATH")
    assert issue_position.why_no_position(answer).cause == "`pkit` was not found on PATH"


def test_a_pkit_that_cannot_start_says_so(monkeypatch) -> None:
    answer = _ask(monkeypatch, PermissionError(13, "Permission denied"))
    assert answer.status is None
    assert answer.failure == "`pkit` could not start: [Errno 13] Permission denied"


def test_a_failed_run_names_its_exit_and_what_it_said(monkeypatch) -> None:
    outcome = subprocess.CompletedProcess([], 2, "", "Error: unknown process 'x'\n")
    answer = _ask(monkeypatch, outcome)
    assert answer == issue_position.EngineAnswer(
        failure="`pkit process status` exited 2", said="Error: unknown process 'x'"
    )
    unread = issue_position.why_no_position(answer)
    assert (unread.cause, unread.said_by) == (
        "`pkit process status` exited 2",
        "`pkit process status`",
    )


@pytest.mark.parametrize("stdout", ["not json", "[]", '"x"', "null"])
def test_output_that_is_no_json_object_says_so(monkeypatch, stdout) -> None:
    answer = _ask(monkeypatch, subprocess.CompletedProcess([], 0, stdout, ""))
    assert answer == issue_position.EngineAnswer(
        failure="`pkit process status` printed no JSON object"
    )


def test_an_indeterminate_position_names_the_detection_and_what_its_predicate_said() -> None:
    status = {
        "position": {
            "state": None,
            "indeterminate": True,
            "unevaluated": [
                {
                    "state": "backlog",
                    "reason": "couldn't evaluate detection predicate 'detect': exited 2",
                    "stderr_tail": "run `pkit project-management bootstrap`",
                }
            ],
        }
    }
    assert issue_position.why_no_position(_answer(status)) == issue_position.Unread(
        "it could not evaluate the detection of 'backlog': "
        "couldn't evaluate detection predicate 'detect': exited 2",
        "run `pkit project-management bootstrap`",
        "the 'backlog' detection predicate",
    )


def test_a_position_no_detection_matched_says_so() -> None:
    status = {"position": {"state": None, "indeterminate": False, "unevaluated": []}}
    assert issue_position.why_no_position(_answer(status)) == issue_position.Unread(
        "no state's detection matched the issue"
    )


def test_what_was_said_is_bounded_and_cannot_rewrite_the_terminal() -> None:
    noisy = "\x1b[31mred\x1b[0m\tline\x07\n" + "".join(f"line {n}\n" for n in range(10))
    said = issue_position.said_tail(noisy)
    assert said.startswith("…")
    assert said.splitlines()[1:] == [f"line {n}" for n in range(6, 10)]
    assert "\x1b" not in said and "\x07" not in said
    assert issue_position.said_tail("\x1b]0;title\x07red\tline\n\n") == "red line"
    assert len(issue_position.said_tail("x" * 5000)) == issue_position.SAID_CHARS


# ---- nothing in the environment stands in for the engine's answer --------


def test_the_engine_is_asked_whatever_the_environment_holds(monkeypatch) -> None:
    monkeypatch.setenv(HAND_DOWN_ENV, json.dumps({"issue": 42, "status": status_at("done")}))
    engine = FakeEngine(status_at("todo"))
    engine.install(monkeypatch, issue_position)
    assert issue_position.ask_engine(42) == issue_position.EngineAnswer(status_at("todo"))
    assert len(engine.asks) == 1


def test_move_issue_reads_its_own_state_whatever_the_environment_holds(monkeypatch, capsys) -> None:
    """A value exported in the shell saying the issue is Done: `move-issue
    --to done` from Todo is judged from the engine's Todo, so it reaches the
    user-authorised Todo → Done gate instead of the no-op branch."""
    monkeypatch.setenv(HAND_DOWN_ENV, json.dumps({"issue": 42, "status": status_at("done")}))
    engine = FakeEngine(status_at("todo"))
    engine.install(monkeypatch, issue_position)
    move = MoveIssueInProcess(
        monkeypatch,
        {**TASK, "labels": [{"name": "type:task"}, {"name": "state:todo"}]},
    )
    rc = move.run([sys.executable, "move-issue.py", "42", "--to", "done"]).returncode
    out, err = capsys.readouterr()
    assert rc == 1
    assert "[noop]" not in out
    assert "[refused] transition 'todo' → 'done' is user-authorised" in err
    assert len(engine.asks) == 1


# ---- composed_move: the shared refusal, run and failure -----------------


def test_the_move_issue_run_carries_its_arguments_and_nothing_else(monkeypatch) -> None:
    seen: list[tuple[list[str], dict[str, Any]]] = []

    def run(cmd, **kw):
        seen.append((cmd, kw))
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(composed_move.subprocess, "run", run)
    rc = composed_move.invoke_move_issue(
        42, "in-progress", capability_root_arg=Path("/cap"), allow_foreign_repo=True
    )
    assert rc == 0
    ((cmd, kw),) = seen
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
    assert kw == {"check": False}  # the child inherits this environment as it is


def test_an_unread_state_refuses_saying_what_failed_and_what_was_said() -> None:
    unread = issue_position.Unread(
        "`pkit process status` exited 1", "Error: one\nError: two", "`pkit process status`"
    )
    refusal = composed_move.transition_refusal(
        "start-work",
        42,
        TASK,
        ["type:task"],
        issue_position.Position("backlog", None, unread),
        target="in-progress",
        untouched="no branch, no assignee",
        workflow=_shipped_workflow(),
        issue_types=_shipped_schema("issue-types.yaml"),
        classification=_shipped_schema("classification.yaml"),
    )
    assert refusal is not None
    assert refusal.splitlines() == [
        "[refused] start-work #42: cannot read the issue's state: "
        f"{issue_position.BOARD_CARRIES_STATE}, and the process engine gave no position: "
        "`pkit process status` exited 1. Nothing was changed (no branch, no assignee).",
        "  `pkit process status` said:",
        "    Error: one",
        "    Error: two",
        f"  → make `pkit process status {issue_position.PROCESS_ADDRESS} --subject 42` "
        "give a position, then re-run `start-work 42`.",
    ]


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


def _shipped_schema(name: str) -> dict[str, Any]:
    from ruamel.yaml import YAML

    return YAML(typ="safe").load((CAPABILITY_ROOT / "schemas" / name).read_text())


def _shipped_workflow() -> dict[str, Any]:
    return _shipped_schema("workflow.yaml")
