"""What start-work and review-work share around their composed move-issue (#1242).

`_lib/issue_position` is where both read the issue's state for their early
check: the inference from its labels and milestone, the one the process
engine's detectors apply to the same fields. `_lib/composed_move` is what they
share around it: the early refusal, the move-issue run and the failure naming
what a run left behind. The verbs' own tests drive these through their
`main()`; this file pins the pieces, that the early check agrees with the
engine's detectors, and that nothing in the environment stands in for
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
from _lib import lifecycle_predicates as predicates

TASK = {"title": "[Task] a thing", "state": "OPEN", "milestone": None, "body": ""}
DERIVE = axis_labels.SubstrateMap(axes={"state": {"derive": {"predicate": "open-closed"}}})
# The variable an earlier revision of #1242 handed the engine's answer down in.
# Nothing reads it; the tests below hold that.
HAND_DOWN_ENV = "PKIT_PM_ISSUE_STATUS"


# ---- current_state: the issue's own fields ------------------------------


@pytest.mark.parametrize(
    "issue, labels, expected",
    [
        (TASK, ["type:task", "state:backlog"], "backlog"),
        (TASK, ["type:task"], "todo"),
        ({**TASK, "milestone": {"title": "M1"}}, [], "backlog"),
        ({**TASK, "milestone": {"title": "M1"}}, ["state:review"], "review"),
        ({**TASK, "state": "CLOSED"}, ["state:review"], "done"),
    ],
    ids=["state-label", "nothing-reads-todo", "milestone", "label-over-milestone", "closed"],
)
def test_the_state_is_read_off_the_issue_s_fields(issue, labels, expected) -> None:
    assert issue_position.current_state(issue, labels, None) == expected


def test_a_derive_bound_state_is_read_off_open_or_closed() -> None:
    state = issue_position.current_state(TASK, ["state:todo"], DERIVE)
    assert state == axis_labels.derive_state(is_closed=False, labels=["state:todo"])


def test_the_reading_starts_no_process(monkeypatch) -> None:
    def refuse(*args: Any, **_kw: Any) -> Any:
        raise AssertionError(f"the early check started a process: {args}")

    monkeypatch.setattr(subprocess, "run", refuse)
    assert issue_position.current_state(TASK, ["state:in-progress"], None) == "in-progress"


@pytest.mark.parametrize(
    "issue, labels, substrate_map",
    [
        (TASK, ["type:task", "state:in-progress"], None),
        (TASK, ["type:task"], None),
        ({**TASK, "milestone": {"title": "M1"}}, [], None),
        ({**TASK, "state": "CLOSED"}, ["state:review"], None),
        (TASK, ["state:review"], DERIVE),
        ({**TASK, "state": "CLOSED"}, [], DERIVE),
    ],
    ids=["label", "todo", "milestone", "closed", "derive-open", "derive-closed"],
)
def test_the_early_check_agrees_with_the_engine_s_detectors(
    monkeypatch, issue, labels, substrate_map
) -> None:
    """The engine's detector, on the same issue, infers the state the early
    check reads, so the check needs no engine run of its own (#1242)."""
    fetched = {**issue, "labels": [{"name": name} for name in labels]}
    monkeypatch.setattr(predicates, "_capability_root", lambda: CAPABILITY_ROOT)
    monkeypatch.setattr(predicates, "_config", lambda _root: {})
    monkeypatch.setattr(predicates, "_fetch_issue", lambda _n, _c, _f: fetched)
    monkeypatch.setattr(predicates.axis_labels, "load_substrate_map", lambda _r: substrate_map)
    read = issue_position.current_state(issue, labels, substrate_map)
    detected = predicates.detect_state(42, read)
    assert detected["result"] is True
    assert detected["detail"]["inferred_state"] == read


# ---- nothing in the environment stands in for move-issue's own read -----


def test_move_issue_reads_its_own_state_whatever_the_environment_holds(monkeypatch, capsys) -> None:
    """A value exported in the shell saying the issue is Done: `move-issue
    --to done` from Todo is judged from the engine's Todo, so it reaches the
    user-authorised Todo → Done gate instead of the no-op branch."""
    monkeypatch.setenv(HAND_DOWN_ENV, json.dumps({"issue": 42, "status": status_at("done")}))
    engine = FakeEngine(status_at("todo"))
    engine.install(monkeypatch)
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


def _refusal(current: str, target: str) -> str | None:
    return composed_move.transition_refusal(
        "review-work",
        42,
        TASK,
        ["type:task"],
        current,
        target=target,
        untouched="no PR opened or made ready, no reviewers requested",
        workflow=_shipped_workflow(),
        issue_types=_shipped_schema("issue-types.yaml"),
        classification=_shipped_schema("classification.yaml"),
    )


def test_a_legal_move_or_one_already_made_is_not_refused() -> None:
    assert _refusal("in-progress", "review") is None
    assert _refusal("review", "review") is None


def test_a_refusal_names_each_move_to_make_first() -> None:
    assert _refusal("todo", "review") == (
        "[refused] review-work #42: the issue is in 'todo', and workflow.yaml declares "
        "no move 'todo' → 'review' for 'task'. Nothing was changed (no PR opened or "
        "made ready, no reviewers requested).\n"
        "  → move it first: `move-issue 42 --to backlog`, then `move-issue 42 --to "
        "in-progress`, then re-run `review-work 42`."
    )


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
