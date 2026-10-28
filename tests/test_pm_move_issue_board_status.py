"""A move writes the board's Status, the projection of the issue's state (#2276).

Where a board is configured and the state is not carried on it, DEC-006 makes
the board's Status a projection the agent maintains. `move-issue`, and so every
wrapper over it, writes the card's Status to the issue's new state, and the
forward cascade writes each ancestor's. A write that fails is one line and the
move stands: the native state is the source. Where the board carries the state,
nothing changes here: that path is #2271's.

These tests run the real scripts and the real engine against an in-memory GitHub
with a board (`tests/pm_board_world.py`).
"""

from __future__ import annotations

from pathlib import Path
from types import ModuleType

import pytest

from tests.pm_board_world import BOARD_CONFIG, LABEL_STATE, BoardTracker
from tests.pm_lifecycle_world import (
    AUTHORED_BODY,
    MILESTONE,
    World,
    load_script,
    make_engine_repo,
    wire,
)

CONTAINER_BODY = "## What\n\nA container.\n"


@pytest.fixture(scope="module")
def ci() -> ModuleType:
    return load_script("create-issue.py", "pm_create_issue_board_status")


@pytest.fixture(scope="module")
def pi() -> ModuleType:
    return load_script("promote-issue.py", "pm_promote_issue_board_status")


@pytest.fixture(scope="module")
def mi() -> ModuleType:
    return load_script("move-issue.py", "pm_move_issue_board_status")


@pytest.fixture(scope="module")
def hist() -> ModuleType:
    return load_script("history.py", "pm_history_board_status")


@pytest.fixture
def world(tmp_path: Path, ci, pi, mi, hist, monkeypatch: pytest.MonkeyPatch) -> World:
    world = World(BoardTracker(), make_engine_repo(tmp_path), ci, pi, mi, hist)
    wire(world, monkeypatch)
    return world


@pytest.fixture
def board(world: World) -> BoardTracker:
    assert isinstance(world.tracker, BoardTracker)
    return world.tracker


def _with_config(world: World, monkeypatch: pytest.MonkeyPatch, config: dict) -> None:
    read_yaml = world.mi._read_yaml

    def read(path: Path, loader):
        return dict(config) if path.name == "config.yaml" else read_yaml(path, loader)

    monkeypatch.setattr(world.mi, "_read_yaml", read)


def _with_substrate_map(world: World, monkeypatch: pytest.MonkeyPatch, axes: dict | None) -> None:
    substrate_map = None if axes is None else world.mi.axis_labels.SubstrateMap(axes=axes)
    monkeypatch.setattr(world.mi.axis_labels, "load_substrate_map", lambda *a, **kw: substrate_map)


@pytest.fixture
def kept(world: World, monkeypatch: pytest.MonkeyPatch) -> None:
    """Board #4 configured, and the state on the kit's own labels: the board's
    Status is a projection the agent keeps."""
    _with_config(world, monkeypatch, BOARD_CONFIG)
    _with_substrate_map(world, monkeypatch, LABEL_STATE)


def _task(world: World, board: BoardTracker, parent: int | None = None, **card) -> int:
    body = f"Feature: #{parent}\n\n{AUTHORED_BODY}" if parent else AUTHORED_BODY
    number = world.file_issue(body=body)
    board.card(number, card.get("status", "Todo"))
    return number


def _container(world: World, board: BoardTracker, title: str, parent: int | None = None) -> int:
    body = f"EPIC: #{parent}\n\n{CONTAINER_BODY}" if parent else CONTAINER_BODY
    number = world.file_issue(body=body, title=title, labels=())
    board.card(number, "Todo")
    return number


# --- the write on a move ------------------------------------------------------


@pytest.mark.usefixtures("kept")
def test_each_move_writes_the_cards_status(
    world: World, board: BoardTracker, capsys: pytest.CaptureFixture[str]
) -> None:
    task = _task(world, board)

    assert world.promote(task, milestone=MILESTONE["title"]) == 0
    assert board.status(task) == "Backlog"
    assert world.move(task, "in-progress") == 0
    assert board.status(task) == "In Progress"
    assert world.move(task, "review") == 0

    assert board.status(task) == "Review"
    assert board.edits == [(task, "Backlog"), (task, "In Progress"), (task, "Review")]
    assert f"[board] #{task}: Status set to 'Review'" in capsys.readouterr().out


@pytest.mark.usefixtures("kept")
def test_the_forward_cascade_writes_each_ancestors_status(
    world: World, board: BoardTracker
) -> None:
    epic = _container(world, board, "[EPIC] An epic")
    feature = _container(world, board, "[Feature] A feature", epic)
    task = _task(world, board, feature)
    world.tracker.issues[task]["labels"].append("state:backlog")

    assert world.move(task, "in-progress") == 0

    assert world.labels(feature)[-1] == world.labels(epic)[-1] == "state:in-progress"
    assert board.status(feature) == board.status(epic) == "In Progress"
    # One write per ancestor, for the state it reached, however many steps it took.
    assert board.edits == [(task, "In Progress"), (feature, "In Progress"), (epic, "In Progress")]


@pytest.mark.usefixtures("kept")
def test_a_move_already_made_writes_the_status_it_reads(world: World, board: BoardTracker) -> None:
    """`done-work` moves an issue the merge closed to Done: the move finds it
    there, and the card still says Review until this write."""
    task = _task(world, board, status="Review")
    world.tracker.issues[task]["labels"].append("state:review")
    world.tracker.close(task, "COMPLETED")

    assert world.move(task, "done") == 0

    assert board.status(task) == "Done"


@pytest.mark.usefixtures("kept")
def test_a_failed_write_is_one_line_and_the_move_stands(
    world: World, board: BoardTracker, capsys: pytest.CaptureFixture[str]
) -> None:
    task = _task(world, board)
    board.fail_edits.add(task)
    world.tracker.issues[task]["labels"].append("state:backlog")

    assert world.move(task, "in-progress") == 0

    assert world.labels(task)[-1] == "state:in-progress"
    assert board.status(task) == "Todo"
    err = capsys.readouterr().err
    warning = [line for line in err.splitlines() if f"#{task}: the board's Status" in line]
    assert warning == [
        f"[warn] #{task}: the board's Status was not set to 'In Progress': "
        "gh project item-edit failed: HTTP 502: Bad Gateway; the move stands, "
        "and `sync-board` sets it"
    ]


@pytest.mark.usefixtures("kept")
def test_an_issue_with_no_card_is_said_and_the_move_stands(
    world: World, board: BoardTracker, capsys: pytest.CaptureFixture[str]
) -> None:
    task = world.file_issue()
    world.tracker.issues[task]["labels"].append("state:backlog")

    assert world.move(task, "in-progress") == 0

    assert world.labels(task)[-1] == "state:in-progress"
    said = f"#{task} has no card on board #4; the move stands, and `sync-board` sets it"
    assert said in capsys.readouterr().err


@pytest.mark.parametrize(
    ("repository", "owner", "default_owner"),
    [
        pytest.param("acme/repo", "acme", None, id="an-organisations-board-no-default-owner"),
        pytest.param("alice/repo", "alice", None, id="a-persons-board-no-default-owner"),
        pytest.param("alice/repo", "acme", "acme", id="a-board-of-another-owner-named"),
    ],
)
def test_a_move_finds_the_board_under_its_owner(
    world: World,
    board: BoardTracker,
    monkeypatch: pytest.MonkeyPatch,
    repository: str,
    owner: str,
    default_owner: str | None,
) -> None:
    """With no `gh.default_owner`, the board is the repository's owner's (the
    README, the `gh:` block), never that of the person who runs `gh`."""
    config = (
        dict(BOARD_CONFIG, gh={"default_owner": default_owner}) if default_owner else BOARD_CONFIG
    )
    _with_config(world, monkeypatch, config)
    _with_substrate_map(world, monkeypatch, LABEL_STATE)
    board.repository, board.owner = repository, owner
    task = _task(world, board)
    world.tracker.issues[task]["labels"].append("state:backlog")

    assert world.move(task, "in-progress") == 0

    assert board.status(task) == "In Progress"
    reads = [argv for argv in board.calls if argv[1:2] == ["project"] and argv[2] != "item-edit"]
    assert reads and {argv[argv.index("--owner") + 1] for argv in reads} == {owner}


@pytest.mark.usefixtures("kept")
def test_a_move_back_writes_the_cards_status(world: World, board: BoardTracker) -> None:
    """The card follows the move back from In Progress as it follows every move
    (DEC-006)."""
    task = _task(world, board)
    assert world.promote(task, milestone=MILESTONE["title"]) == 0
    assert world.move(task, "in-progress") == 0

    assert world.move(task, "backlog", "--reason", "the work stopped") == 0

    assert world.labels(task)[-1] == "state:backlog"
    assert board.status(task) == "Backlog"
    assert board.edits[-1] == (task, "Backlog")


@pytest.mark.usefixtures("kept")
def test_a_dry_run_names_the_write_and_writes_nothing(
    world: World, board: BoardTracker, capsys: pytest.CaptureFixture[str]
) -> None:
    task = _task(world, board)
    world.tracker.issues[task]["labels"].append("state:backlog")

    assert world.move(task, "in-progress", "--dry-run") == 0

    assert "  ~ set the card's Status on board #4 to 'In Progress'" in capsys.readouterr().out
    assert board.edits == [] and board.board_calls() == []


# --- where nothing is written -------------------------------------------------


def test_with_no_board_no_board_call_is_made(
    world: World, board: BoardTracker, monkeypatch: pytest.MonkeyPatch
) -> None:
    _with_config(world, monkeypatch, {})
    task = _task(world, board)

    assert world.promote(task, milestone=MILESTONE["title"]) == 0
    assert world.move(task, "in-progress") == 0

    assert board.board_calls() == []


def test_where_the_board_carries_the_state_nothing_changes(
    world: World,
    board: BoardTracker,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The map binds the state to the board: the Status is then the state's
    source, and the move only narrates it, as before (#2271)."""
    _with_config(world, monkeypatch, BOARD_CONFIG)
    _with_substrate_map(world, monkeypatch, {"state": {"board": True}})
    task = _task(world, board)
    world.tracker.issues[task]["milestone"] = MILESTONE

    assert world.move(task, "in-progress") == 0

    assert board.board_calls() == [] and board.status(task) == "Todo"
    out = capsys.readouterr().out
    assert "[ok] (board adopter) plan recorded; manual board edit may be required." in out
    # The note cites what decides the Status, not DEC-019, which is about membership.
    assert "the agent maintains the Status (DEC-006)" in out
    assert "DEC-019" not in out
