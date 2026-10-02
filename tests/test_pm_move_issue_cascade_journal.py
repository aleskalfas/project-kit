"""A parent the forward cascade moves gets a journal entry of its own (#1214).

When an issue moves forward, `move-issue` bumps its parent's state label if the
parent is behind (DEC-006). The issue's own move was journaled by the process
engine and the parent's was not, so a move pkit made existed on the tracker and
nowhere in the journal, and `pkit pm history <parent> --check-drift` reported it
as drift. Each parent the cascade moves is now journaled the way the issue's own
move is: after its label write, from the state the parent held before it, by the
same actor, with the child's move named as the reason.

These tests run the real scripts and the real engine against an in-memory GitHub
(`tests/pm_lifecycle_world.py`).
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from types import ModuleType

import pytest

from tests.pm_lifecycle_world import (
    AUTHORED_BODY,
    INVOKER,
    REASON,
    Tracker,
    World,
    load_script,
    make_engine_repo,
    wire,
)
from tests.process_journal_support import set_journal_logging

ENGINE_WARNING = "the process engine refused this move"

#: (the container's title, the parent-ref word a child's body names it by)
CONTAINERS = [
    pytest.param("[Feature] A feature", "Feature", id="feature"),
    pytest.param("[EPIC] An epic", "EPIC", id="epic"),
]


@pytest.fixture(scope="module")
def ci() -> ModuleType:
    return load_script("create-issue.py", "pm_create_issue_cascade_journal")


@pytest.fixture(scope="module")
def pi() -> ModuleType:
    return load_script("promote-issue.py", "pm_promote_issue_cascade_journal")


@pytest.fixture(scope="module")
def mi() -> ModuleType:
    return load_script("move-issue.py", "pm_move_issue_cascade_journal")


@pytest.fixture(scope="module")
def hist() -> ModuleType:
    return load_script("history.py", "pm_history_cascade_journal")


@pytest.fixture
def engine_repo(tmp_path: Path) -> Path:
    return make_engine_repo(tmp_path)


@pytest.fixture
def world(engine_repo: Path, ci, pi, mi, hist, monkeypatch: pytest.MonkeyPatch) -> World:
    world = World(Tracker(), engine_repo, ci, pi, mi, hist)
    wire(world, monkeypatch)
    return world


def _file_child(
    world: World, parent: int, ref: str, labels: tuple[str, ...] = ("type:task",)
) -> int:
    """File a Task whose body names `parent` as its parent."""
    return world.file_issue(body=f"{ref}: #{parent}\n\n{AUTHORED_BODY}", labels=labels)


def _reason(child: int, move: str) -> str:
    return f"forward cascade from #{child}: {move}"


def _started_under(world: World, title: str, ref: str) -> tuple[int, int]:
    """A container filed in Todo with one Task under it, the Task promoted and
    then started — each move cascading the container one step."""
    parent = world.file_issue(title=title, labels=())
    child = _file_child(world, parent, ref)
    assert world.promote(child) == 0
    assert world.move(child, "in-progress") == 0
    return parent, child


# --- each cascaded move is journaled --------------------------------------


@pytest.mark.parametrize(("title", "ref"), CONTAINERS)
def test_each_cascaded_parent_move_is_journaled_from_where_the_parent_was(
    world: World, capsys: pytest.CaptureFixture[str], title: str, ref: str
) -> None:
    parent = world.file_issue(title=title, labels=())
    child = _file_child(world, parent, ref)
    assert world.views(parent) == ("todo", "todo")

    # The child's promotion takes the parent from Todo to Backlog.
    assert world.promote(child) == 0
    assert world.views(parent) == ("backlog", "backlog")
    assert world.moves(parent) == [("todo", "backlog", "promote-issue")]

    # The child's start takes it from Backlog to In Progress: one entry, from
    # Backlog.
    assert world.move(child, "in-progress") == 0
    assert ENGINE_WARNING not in capsys.readouterr().err
    assert world.views(parent) == ("in-progress", "in-progress")
    assert world.moves(parent) == [
        ("todo", "backlog", "promote-issue"),
        ("backlog", "in-progress", "start-work"),
    ]

    # Each entry names the child's move as its reason, by the child's actor.
    journal = world.journal(parent)
    assert [entry["reason"] for entry in journal] == [
        _reason(child, "todo → backlog"),
        _reason(child, "backlog → in-progress"),
    ]
    assert {entry["actor"] for entry in journal} == {INVOKER.github_login}
    # The child's own moves were asked for directly: its promotion carries the
    # justification its gate was bypassed with (#1232), its start no reason.
    assert world.moves(child) == [
        ("todo", "backlog", "promote-issue"),
        ("backlog", "in-progress", "start-work"),
    ]
    assert [entry.get("reason") for entry in world.journal(child)] == [f"bypass: {REASON}", None]


@pytest.mark.parametrize(("title", "ref"), CONTAINERS)
def test_check_drift_finds_no_drift_on_a_cascaded_parent(
    world: World, capsys: pytest.CaptureFixture[str], title: str, ref: str
) -> None:
    parent, child = _started_under(world, title, ref)
    capsys.readouterr()

    assert world.history(parent) == 0
    history = capsys.readouterr().out
    assert (
        f"backlog → in-progress (start-work) — {_reason(child, 'backlog → in-progress')}" in history
    )
    assert "2 governed move(s) journaled · 2 state-label change(s)" in history
    assert "no ungoverned state changes detected" in history


# --- a parent in Todo, a re-run, logging off ------------------------------


def test_a_parent_in_todo_is_taken_through_backlog_one_recorded_move_at_a_time(
    world: World, capsys: pytest.CaptureFixture[str]
) -> None:
    """#1229: a child starts from Backlog while its Feature and the Feature's
    EPIC are still in Todo. The workflow declares no Todo → In Progress, so
    each goes to Backlog and then to In Progress, two label writes and two
    recorded moves, each naming the child's start as its reason."""
    epic = world.file_issue(title="[EPIC] An epic", labels=())
    parent = world.file_issue(
        body=f"EPIC: #{epic}\n\n## What\n", title="[Feature] A feature", labels=()
    )
    child = _file_child(world, parent, "Feature", labels=("type:task", "state:backlog"))
    capsys.readouterr()

    assert world.move(child, "in-progress") == 0

    moved = capsys.readouterr()
    assert "[warn]" not in moved.err
    for number in (parent, epic):
        steps = f"[cascade] #{number}: todo → backlog\n[cascade] #{number}: backlog → in-progress\n"
        assert steps in moved.out
        assert world.moves(number) == [
            ("todo", "backlog", "promote-issue"),
            ("backlog", "in-progress", "start-work"),
        ]
        assert [entry["reason"] for entry in world.journal(number)] == [
            _reason(child, "backlog → in-progress")
        ] * 2
        assert world.labels(number) == ["state:in-progress"]
        assert world.views(number) == ("in-progress", "in-progress")
    # The child's own move is unaffected.
    assert world.moves(child) == [("backlog", "in-progress", "start-work")]

    # And the drift check finds every state change journaled.
    for number in (parent, epic):
        capsys.readouterr()
        assert world.history(number) == 0
        assert "2 governed move(s) journaled · 2 state-label change(s)" in capsys.readouterr().out


def test_a_rerun_or_a_siblings_move_adds_no_second_entry(
    world: World, capsys: pytest.CaptureFixture[str]
) -> None:
    parent, child = _started_under(world, "[Feature] A feature", "Feature")
    journaled = world.journal(parent)
    assert len(journaled) == 2

    # The same move again finds the child at the target and does nothing.
    assert world.move(child, "in-progress") == 0
    # A sibling's moves find the parent at or beyond their target.
    sibling = _file_child(world, parent, "Feature")
    assert world.promote(sibling) == 0
    assert world.move(sibling, "in-progress") == 0

    assert ENGINE_WARNING not in capsys.readouterr().err
    assert world.journal(parent) == journaled
    assert world.history(parent) == 0
    assert "no ungoverned state changes detected" in capsys.readouterr().out


def test_with_journal_logging_off_a_cascade_prints_no_engine_warning(
    world: World, capsys: pytest.CaptureFixture[str]
) -> None:
    set_journal_logging(world.engine_repo, enabled=False)

    parent, _child = _started_under(world, "[Feature] A feature", "Feature")

    assert ENGINE_WARNING not in capsys.readouterr().err
    assert world.views(parent) == ("in-progress", "in-progress")
    assert world.journal_files() == []


# --- what reaches the engine ----------------------------------------------


def test_a_reason_reaches_the_engine_only_when_one_is_given(
    mi, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A move with no reason — asked for directly, no gate bypassed — keeps the
    argv it had, so it reaches the engine the same way it did before a cascaded
    or a bypassed move named one."""
    calls: list[list[str]] = []

    def run(argv, **kwargs):
        calls.append(list(argv))
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(subprocess, "run", run)
    mi._journal_move(7, "backlog", "in-progress", "octocat")
    mi._journal_move(8, "backlog", "in-progress", "octocat", reason=_reason(7, "a → b"))

    direct, cascaded = calls
    assert "--reason" not in direct
    assert cascaded[cascaded.index("--reason") + 1] == _reason(7, "a → b")
