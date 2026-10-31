"""A merge's close is journaled from where the work stood, wherever the state lives (#2307).

When a pull request merges, GitHub closes each issue it names with no move of
pkit's, and `close-issue --mode=pr-merge`, which `done-work` runs on each of
them, records the move to Done from where the merge found the issue
([project-management:DEC-049-audit-journal-model]). Where the kit's labels carry
the state, the stale state label says where that was. Where the substrate map
binds the state to the board, no label does: the card's Status says it until the
card is set to Done ([pkit:ADR-074] point 4), and a card that places the issue
nowhere records no move, with a warning naming which of the four outcomes it is
([project-management:DEC-051-axis-carriage-activation] point 6). `move-issue
--to done`, which `done-work` runs first on its own issue, records that close
as it sets the card to Done, and the journal, not the card, says whether a
close is recorded already, so a landing records each close once.

These tests run the real scripts and the real engine against an in-memory GitHub
(`tests/pm_lifecycle_world.py`), with a board where the state lives on it
(`tests/pm_board_world.py`).
"""

from __future__ import annotations

import argparse
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from tests.pm_board_world import BOARD_CONFIG, STATE_ON_BOARD, BoardTracker
from tests.pm_lifecycle_world import (
    CAPABILITY_ROOT,
    Tracker,
    World,
    load_script,
    make_engine_repo,
    predicates,
    wire,
)
from tests.process_journal_support import set_journal_logging

PR = 500
CLOSED_BY = f"pr-merge close: closed by merged PR #{PR}"
ENGINE_WARNING = "the process engine refused this move"
UNRECORDED = "this move was not recorded"
MERGE_CLOSE = ["--mode", "pr-merge", "--pr", str(PR)]


@pytest.fixture(scope="module")
def ci() -> ModuleType:
    return load_script("create-issue.py", "pm_create_issue_merge_close_journal")


@pytest.fixture(scope="module")
def pi() -> ModuleType:
    return load_script("promote-issue.py", "pm_promote_issue_merge_close_journal")


@pytest.fixture(scope="module")
def mi() -> ModuleType:
    return load_script("move-issue.py", "pm_move_issue_merge_close_journal")


@pytest.fixture(scope="module")
def hist() -> ModuleType:
    return load_script("history.py", "pm_history_merge_close_journal")


@pytest.fixture(scope="module")
def cl() -> ModuleType:
    return load_script("close-issue.py", "pm_close_issue_merge_close_journal")


@pytest.fixture(scope="module")
def dw() -> ModuleType:
    return load_script("done-work.py", "pm_done_work_merge_close_journal")


@pytest.fixture
def label_world(tmp_path: Path, ci, pi, mi, hist, cl, dw, monkeypatch: pytest.MonkeyPatch) -> World:
    """The kit's own labels carry the state: no map, no board."""
    world = World(Tracker(), make_engine_repo(tmp_path), ci, pi, mi, hist, cl)
    wire(world, monkeypatch)
    _no_branch_cleanup(dw, monkeypatch)
    return world


@pytest.fixture
def board_world(tmp_path: Path, ci, pi, mi, hist, cl, dw, monkeypatch: pytest.MonkeyPatch) -> World:
    """The map binds the state to board #4, and every script reads that board."""
    world = World(BoardTracker(), make_engine_repo(tmp_path), ci, pi, mi, hist, cl)
    wire(world, monkeypatch)
    _no_branch_cleanup(dw, monkeypatch)
    read_yaml = mi._read_yaml

    def read(path: Path, loader):
        return dict(BOARD_CONFIG) if path.name == "config.yaml" else read_yaml(path, loader)

    monkeypatch.setattr(mi, "_read_yaml", read)
    monkeypatch.setattr(cl, "load_adopter_config", lambda _root: dict(BOARD_CONFIG))
    monkeypatch.setattr(predicates, "_config", lambda _root: dict(BOARD_CONFIG))
    substrate_map = mi.axis_labels.SubstrateMap(axes=STATE_ON_BOARD)
    monkeypatch.setattr(mi.axis_labels, "load_substrate_map", lambda *a, **kw: substrate_map)
    return world


@pytest.fixture(params=["label", "board"])
def world(request: pytest.FixtureRequest) -> World:
    """Each carriage of the state in turn: the kit's labels, then the board."""
    return request.getfixturevalue(f"{request.param}_world")


@pytest.fixture
def board(board_world: World) -> BoardTracker:
    assert isinstance(board_world.tracker, BoardTracker)
    return board_world.tracker


def _no_branch_cleanup(dw: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    """The branch clean-up after a landing's closes is another test's subject."""
    monkeypatch.setattr(dw.pr_merge, "delete_branch", lambda *a, **kw: None)
    monkeypatch.setattr(dw.pr_merge, "cleanup_local", lambda *a, **kw: None)


# --- the issues a pull request closes -----------------------------------------


def _backlog_task(world: World) -> int:
    """A Task in Backlog: its label says so, or its card does."""
    number = world.file_issue()
    if isinstance(world.tracker, BoardTracker):
        world.tracker.card(number, "Backlog")
    else:
        assert world.promote(number) == 0
    return number


def _task_in_review(world: World) -> int:
    number = _backlog_task(world)
    assert world.move(number, "in-progress") == 0
    assert world.move(number, "review") == 0
    return number


#: (the issue's set-up, where the merge found it, the trigger the workflow names
#: the move to Done from there by)
ORIGINS = [
    pytest.param(_backlog_task, "backlog", "close-issue", id="backlog"),
    pytest.param(_task_in_review, "review", "done-work", id="review"),
]
ORIGIN_FIELDS = ("set_up", "origin", "trigger")


def _engine_calls_during(world: World, step: Callable[[], Any]) -> tuple[Any, list[str]]:
    """Run `step`; return what it returned and the `pkit process` verbs it ran."""
    before = len(world.engine_calls)
    result = step()
    return result, [call[2] for call in world.engine_calls[before:]]


def _moves_to_done(world: World, number: int) -> list[dict[str, Any]]:
    return [entry for entry in world.journal(number) if entry["to"] == "done"]


# --- close-issue records the merge's close ------------------------------------


@pytest.mark.parametrize(ORIGIN_FIELDS, ORIGINS)
def test_a_merge_s_close_is_journaled_from_where_the_work_stood(
    world: World,
    capsys: pytest.CaptureFixture[str],
    set_up: Callable[[World], int],
    origin: str,
    trigger: str,
) -> None:
    number = set_up(world)
    world.tracker.merge(PR, [number])
    capsys.readouterr()

    assert world.close(number, *MERGE_CLOSE) == 0

    err = capsys.readouterr().err
    assert ENGINE_WARNING not in err and UNRECORDED not in err
    assert world.moves(number)[-1] == (origin, "done", trigger)
    [entry] = _moves_to_done(world, number)
    assert entry["reason"] == CLOSED_BY


@pytest.mark.parametrize(ORIGIN_FIELDS, ORIGINS)
def test_closing_it_again_records_nothing_more(
    world: World,
    capsys: pytest.CaptureFixture[str],
    set_up: Callable[[World], int],
    origin: str,
    trigger: str,
) -> None:
    """The label says Done after the first close, and where the board carries
    the state, the journal says the move is recorded: the card still says where
    the work stood, as a close leaves it."""
    number = set_up(world)
    world.tracker.merge(PR, [number])
    assert world.close(number, *MERGE_CLOSE) == 0
    journaled = world.journal(number)
    capsys.readouterr()

    rc, verbs = _engine_calls_during(world, lambda: world.close(number, *MERGE_CLOSE))

    assert rc == 0
    assert "move" not in verbs
    assert world.journal(number) == journaled
    assert UNRECORDED not in capsys.readouterr().err


# --- a card that places the closed issue nowhere ------------------------------


def _close(world: World, number: int) -> int:
    return world.close(number, *MERGE_CLOSE)


def _move_to_done(world: World, number: int) -> int:
    return world.move(number, "done", "--merged-pr", str(PR))


#: (the card's Status, or how the read fails; what the warning names)
UNPLACED = [
    pytest.param(
        "unreadable",
        "the board's Status of #{n} could not be read: HTTP 502: Bad Gateway",
        id="unreadable",
    ),
    pytest.param("no card", "#{n} has no card on board #4", id="no-card"),
    pytest.param(None, "#{n}'s card on board #4 has no Status", id="unset"),
    pytest.param(
        "Done",
        "#{n}'s card on board #4 has the Status 'Done', which names no open state",
        id="not-open",
    ),
]


@pytest.mark.parametrize("command", [_close, _move_to_done], ids=["close-issue", "move-issue"])
@pytest.mark.parametrize(("card", "names"), UNPLACED)
def test_a_card_that_places_the_issue_nowhere_records_no_move_and_says_which(
    board_world: World,
    board: BoardTracker,
    capsys: pytest.CaptureFixture[str],
    command: Callable[[World, int], int],
    card: str | None,
    names: str,
) -> None:
    """The board cannot be read, no card, no Status, or a Status naming no open
    state, such as a card a board's own automation set to Done as the issue
    closed: each is named, and nothing is guessed from the labels."""
    number = _backlog_task(board_world)
    board_world.tracker.issues[number]["labels"].append("state:review")
    board.card(number, card if card in (None, "Done") else "Review")
    if card == "no card":
        del board.cards[number]
    if card == "unreadable":
        board.fail_reads.add("card")
    board_world.tracker.merge(PR, [number])
    capsys.readouterr()

    assert command(board_world, number) == 0

    err = capsys.readouterr().err
    assert f"[warn] {UNRECORDED}: {names.format(n=number)}" in err
    assert f"`pkit pm history {number} --check-drift` will show the gap" in err
    assert board_world.journal(number) == []


# --- move-issue records the close it moves the card for ------------------------


def test_moving_a_merged_issue_to_done_records_the_close_from_its_card(
    board_world: World, board: BoardTracker, capsys: pytest.CaptureFixture[str]
) -> None:
    """The card is read before it is set to Done, so the close is recorded from
    where the card said the work stood; a move again records nothing more."""
    number = _task_in_review(board_world)
    board_world.tracker.merge(PR, [number])
    capsys.readouterr()

    assert _move_to_done(board_world, number) == 0

    assert board.status(number) == "Done"
    assert board_world.moves(number)[-1] == ("review", "done", "done-work")
    [entry] = _moves_to_done(board_world, number)
    assert entry["reason"] == CLOSED_BY
    journaled = board_world.journal(number)

    assert _move_to_done(board_world, number) == 0

    assert board_world.journal(number) == journaled
    assert UNRECORDED not in capsys.readouterr().err


# --- a done-work landing -------------------------------------------------------


def _land(world: World, dw: ModuleType, primary: int, further: int) -> int:
    """What done-work runs once the merge it made has landed: move-issue on its
    own issue, then close-issue on each issue the pull request closed."""
    run = dw._after_merge(
        argparse.Namespace(
            issue_number=primary,
            capability_root=CAPABILITY_ROOT,
            skip_checkbox_gate=False,
        ),
        pr_number=PR,
        to_close=[primary, further],
        branch=f"fix/{primary}-a-task",
        cross=False,
        merged_head="0" * 40,
        config={},
        confirmed=False,
    )
    return int(run.exit_code)


def test_a_landing_journals_each_close_once(
    world: World, dw: ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    """move-issue records the close of the landing's own issue, and close-issue
    the other's; the label at Done, or the journal where the board carries the
    state, keeps close-issue from recording the first again."""
    primary, further = _task_in_review(world), _backlog_task(world)
    world.tracker.merge(PR, [primary, further])
    capsys.readouterr()

    assert _land(world, dw, primary, further) == 0

    err = capsys.readouterr().err
    assert ENGINE_WARNING not in err and UNRECORDED not in err
    assert world.moves(primary)[-1] == ("review", "done", "done-work")
    assert world.moves(further)[-1] == ("backlog", "done", "close-issue")
    for number in (primary, further):
        [entry] = _moves_to_done(world, number)
        assert entry["reason"] == CLOSED_BY

    journals = {number: world.journal(number) for number in (primary, further)}
    assert _land(world, dw, primary, further) == 0
    assert {number: world.journal(number) for number in (primary, further)} == journals
    assert UNRECORDED not in capsys.readouterr().err


# --- where nothing is recorded -------------------------------------------------


def test_with_journal_logging_off_a_merge_s_close_reads_no_card_and_warns_nothing(
    board_world: World, board: BoardTracker, capsys: pytest.CaptureFixture[str]
) -> None:
    """With no journal kept, nothing is recorded and nothing is missed: the close
    asks the engine once, which says so, and reads no card."""
    set_journal_logging(board_world.engine_repo, enabled=False)
    number = _backlog_task(board_world)
    board.card(number, "Done")
    board_world.tracker.merge(PR, [number])
    board.calls.clear()
    capsys.readouterr()

    rc, verbs = _engine_calls_during(board_world, lambda: _close(board_world, number))

    assert rc == 0
    assert verbs == ["status"]
    assert board.board_calls() == []
    assert UNRECORDED not in capsys.readouterr().err
    assert board_world.journal_files() == []


def test_a_dry_run_reads_neither_the_journal_nor_the_card(
    board_world: World, board: BoardTracker
) -> None:
    number = _backlog_task(board_world)
    board_world.tracker.merge(PR, [number])
    board.calls.clear()

    rc, verbs = _engine_calls_during(
        board_world, lambda: board_world.close(number, *MERGE_CLOSE, "--dry-run")
    )

    assert rc == 0
    assert verbs == []
    assert board.board_calls() == []
