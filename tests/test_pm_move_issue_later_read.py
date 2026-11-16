"""A move writes only from a read made after its prompt (#3261).

`move-issue` reads where the issue stands, previews the move and, at a terminal,
asks the person, whose answer may come minutes later. Just before its first
write, the audit comment included, it reads the issue again. Where that read
places the issue where the preview did, the move is made as previewed, with no
second prompt, and its gates, its writes and its journal entry come from that
read. Where it places the issue elsewhere, nothing is written or journaled, and
the run says where the issue now stands and that the move run again previews it
afresh, exiting 1. Where it cannot place the issue, the move exits as one whose
first read could not place it.

Each case runs where the kit's labels carry the state and where the board's
Status does (DEC-062 point 5), against the real scripts and the real engine on
an in-memory GitHub (`tests/pm_lifecycle_world.py`, `tests/pm_board_world.py`).
"""

from __future__ import annotations

import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from tests.pm_board_world import BOARD_CONFIG, STATE_ON_BOARD, BoardTracker
from tests.pm_lifecycle_world import (
    AUDIT_MARKER,
    CAPABILITY_ROOT,
    MILESTONE,
    Tracker,
    World,
    load_script,
    make_engine_repo,
    predicates,
    wire,
)

#: The board's option for each open state.
OPTION = {"todo": "Todo", "backlog": "Backlog", "in-progress": "In Progress", "review": "Review"}
#: The justification the move under test bypasses its gate with.
OWN_REASON = "scheduled in the planning session"


@pytest.fixture(scope="module")
def ci() -> ModuleType:
    return load_script("create-issue.py", "pm_create_issue_later_read")


@pytest.fixture(scope="module")
def pi() -> ModuleType:
    return load_script("promote-issue.py", "pm_promote_issue_later_read")


@pytest.fixture(scope="module")
def mi() -> ModuleType:
    return load_script("move-issue.py", "pm_move_issue_later_read")


@pytest.fixture(scope="module")
def hist() -> ModuleType:
    return load_script("history.py", "pm_history_later_read")


@pytest.fixture
def labels_world(tmp_path: Path, ci, pi, mi, hist, monkeypatch: pytest.MonkeyPatch) -> World:
    """No map and no board: the kit's own labels carry the state."""
    world = World(Tracker(), make_engine_repo(tmp_path), ci, pi, mi, hist)
    wire(world, monkeypatch)
    return world


@pytest.fixture
def board_world(tmp_path: Path, ci, pi, mi, hist, monkeypatch: pytest.MonkeyPatch) -> World:
    """Board #4 configured, and the map binding the state to it: the card's
    Status is the source of an open issue's position."""
    world = World(BoardTracker(), make_engine_repo(tmp_path), ci, pi, mi, hist)
    wire(world, monkeypatch)
    read_yaml = mi._read_yaml

    def read(path: Path, loader):
        return dict(BOARD_CONFIG) if path.name == "config.yaml" else read_yaml(path, loader)

    monkeypatch.setattr(mi, "_read_yaml", read)
    monkeypatch.setattr(predicates, "_config", lambda _root: dict(BOARD_CONFIG))
    substrate_map = mi.axis_labels.SubstrateMap(axes=STATE_ON_BOARD)
    monkeypatch.setattr(mi.axis_labels, "load_substrate_map", lambda *a, **kw: substrate_map)
    return world


@pytest.fixture(params=["labels", "board"])
def world(request: pytest.FixtureRequest) -> World:
    """Each substrate in turn: the kit's labels, then the board's Status."""
    return request.getfixturevalue(f"{request.param}_world")


def _on_board(world: World) -> BoardTracker | None:
    return world.tracker if isinstance(world.tracker, BoardTracker) else None


def _stand(world: World, number: int, state: str) -> None:
    """Put the issue in `state` by hand, on the substrate that carries it, as a
    person does who drags its card or edits its labels."""
    board = _on_board(world)
    if board is not None:
        board.cards[number]["status"] = OPTION[state]
        return
    labels = world.labels(number)
    labels[:] = [label for label in labels if not label.startswith("state:")]
    labels.append(f"state:{state}")


def _where(world: World, number: int) -> tuple[str | None, str | None]:
    """Where the issue stands: as the substrate carrying its state says, and as
    the engine places it."""
    board = _on_board(world)
    if board is not None:
        carried = {option: state for state, option in OPTION.items()}.get(
            board.status(number) or ""
        )
    else:
        carried = world.tracker.state_of(number)
    return carried, world._engine(number).resolve_position().state_id


def _task(world: World, state: str) -> int:
    """A Task standing in `state`, on the board where the world has one."""
    number = world.file_issue()
    board = _on_board(world)
    if board is not None:
        board.card(number, "Todo")
    _stand(world, number, state)
    return number


@dataclass(frozen=True)
class _Written:
    """What the tracker and the engine hold of an issue, to compare with later."""

    labels: tuple[str, ...]
    status: str | None
    edits: tuple[tuple[int, str], ...]
    comments: tuple[str, ...]
    journal: tuple[tuple[str | None, str, str], ...]

    @classmethod
    def of(cls, world: World, number: int) -> _Written:
        board = _on_board(world)
        return cls(
            labels=tuple(world.labels(number)),
            status=board.status(number) if board is not None else None,
            edits=tuple(board.edits) if board is not None else (),
            comments=tuple(comment["body"] for comment in world.tracker.comments[number]),
            journal=tuple(world.moves(number)),
        )


class _Terminal:
    """Standard input at a terminal, where `move-issue` asks the person."""

    def isatty(self) -> bool:
        return True


def _at_a_terminal(
    world: World,
    monkeypatch: pytest.MonkeyPatch,
    number: int,
    target: str,
    *options: str,
    meanwhile: Callable[[], Any] = lambda: None,
) -> tuple[int, int]:
    """Run `move-issue` on the issue at a terminal, with no `--yes`, the person
    answering yes once `meanwhile` has happened, as it happens while the question
    stands. The exit code, and how many times the person was asked."""
    asked: list[str] = []

    def answer(question: str) -> str:
        asked.append(question)
        meanwhile()
        return "y"

    monkeypatch.setattr(sys, "stdin", _Terminal())
    monkeypatch.setattr("builtins.input", answer)
    argv = ["move-issue.py", str(number), "--to", target, *options]
    monkeypatch.setattr(sys, "argv", [*argv, "--capability-root", str(CAPABILITY_ROOT)])
    return world.mi.main(), len(asked)


# --- the read places the issue where the preview did ---------------------------


def test_a_move_the_later_read_confirms_is_made_with_one_prompt(
    world: World, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    task = _task(world, "backlog")

    rc, asked = _at_a_terminal(world, monkeypatch, task, "in-progress")

    assert (rc, asked) == (0, 1)
    assert _where(world, task) == ("in-progress", "in-progress")
    assert [move[:2] for move in world.moves(task)] == [("backlog", "in-progress")]
    assert f"[ok] transitioned #{task}: backlog → in-progress" in capsys.readouterr().out


def test_the_labels_are_worked_out_from_the_later_read(
    labels_world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The preview places the issue in Backlog by its milestone alone. While the
    question stands, someone puts the Backlog label on it, which leaves it where
    it was. The move takes that label off, so the issue keeps one state label
    (RS-PM-003)."""
    world = labels_world
    task = world.file_issue()
    world.tracker.issues[task]["milestone"] = MILESTONE

    rc, _ = _at_a_terminal(
        world,
        monkeypatch,
        task,
        "in-progress",
        meanwhile=lambda: world.labels(task).append("state:backlog"),
    )

    assert rc == 0
    states = [label for label in world.labels(task) if label.startswith("state:")]
    assert states == ["state:in-progress"]


# --- the read places the issue elsewhere --------------------------------------


def _moved_on(world: World, number: int) -> None:
    """Another run moves the issue on to In Progress."""
    assert world.move(number, "in-progress") == 0


def _put_back(world: World, number: int) -> None:
    """A person puts the issue back in Todo by hand."""
    _stand(world, number, "todo")


@pytest.mark.parametrize(
    ("meanwhile", "now"),
    [
        pytest.param(_moved_on, "in-progress", id="another-run-moved-it-on"),
        pytest.param(_put_back, "todo", id="a-person-put-it-back"),
    ],
)
def test_a_move_whose_issue_moved_since_the_preview_writes_and_journals_nothing(
    world: World,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    meanwhile: Callable[[World, int], None],
    now: str,
) -> None:
    """The preview places the issue in Backlog. While the question stands, it
    moves. The move from Backlog is not made from where it stands now, which
    would record a step from Backlog twice, or set In Progress from Todo, a move
    the lifecycle does not declare (DEC-006)."""
    task = _task(world, "backlog")
    held: list[_Written] = []

    def move_it() -> None:
        meanwhile(world, task)
        held.append(_Written.of(world, task))

    rc, asked = _at_a_terminal(world, monkeypatch, task, "in-progress", meanwhile=move_it)

    assert (rc, asked) == (1, 1)
    assert _Written.of(world, task) == held[0]
    assert _where(world, task) == (now, now)
    err = capsys.readouterr().err
    assert f"[refused] #{task} moved since the preview: it stood in backlog, and now " in err
    assert f"stands in {now}." in err
    assert "Nothing was written or journaled." in err
    assert f"→ run the move again: it previews the move to in-progress from {now}." in err


def test_with_no_prompt_the_move_still_reads_the_issue_again_before_it_writes(
    world: World, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Passed `--yes`, the move asks nothing, and the read it writes from is
    still made after its preview: the issue put back while the preview printed
    does not move."""
    task = _task(world, "backlog")
    preview = world.mi._print_plan
    held: list[_Written] = []

    def print_plan(*args: Any, **kwargs: Any) -> None:
        preview(*args, **kwargs)
        _put_back(world, task)
        held.append(_Written.of(world, task))

    monkeypatch.setattr(world.mi, "_print_plan", print_plan)

    assert world.move(task, "in-progress") == 1

    assert _Written.of(world, task) == held[0]
    assert held[0].journal == ()
    assert _where(world, task) == ("todo", "todo")
    assert "moved since the preview" in capsys.readouterr().err


def test_the_audit_comment_waits_on_the_later_read(
    world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A bypass's justification is posted just before the move's first write,
    and so after the later read: a move refused there posts none. The other
    run's own comment stands."""
    task = _task(world, "todo")
    other = "promoted by another run"

    def promote() -> None:
        assert world.move(task, "backlog", "--bypass", "--bypass-reason", other) == 0

    rc, _ = _at_a_terminal(
        world,
        monkeypatch,
        task,
        "backlog",
        "--bypass",
        "--bypass-reason",
        OWN_REASON,
        meanwhile=promote,
    )

    assert rc == 1
    audits = [c["body"] for c in world.tracker.comments[task] if AUDIT_MARKER in c["body"]]
    assert len(audits) == 1
    assert other in audits[0] and OWN_REASON not in audits[0]
    assert [move[:2] for move in world.moves(task)] == [("todo", "backlog")]


# --- the read cannot place the issue ------------------------------------------


def _unreadable_issue(world: World, number: int) -> None:
    world.tracker.views_fail.add(number)


def _stray_label(world: World, number: int) -> None:
    """A state label naming no state of the lifecycle."""
    labels = world.labels(number)
    labels[labels.index("state:backlog")] = "state:blocked"


def _status(option: str | None) -> Callable[[World, int], None]:
    """The card's Status set to `option`, or unset where it is None."""

    def set_status(world: World, number: int) -> None:
        board = _on_board(world)
        assert board is not None
        board.cards[number]["status"] = option

    return set_status


def _board_unreadable(world: World, number: int) -> None:
    board = _on_board(world)
    assert board is not None
    board.fail_reads.add("fields")


def _refused_as_a_first_read(
    world: World,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    unplace: Callable[[World, int], None],
    code: int,
    says: str,
) -> None:
    """The issue, in Backlog at the preview, cannot be placed by the later read.
    Nothing is written, and the exit code and the reason are those of a move
    whose first read meets the same issue."""
    task = _task(world, "backlog")
    held: list[_Written] = []

    def unplace_it() -> None:
        unplace(world, task)
        held.append(_Written.of(world, task))

    rc, asked = _at_a_terminal(world, monkeypatch, task, "in-progress", meanwhile=unplace_it)

    assert (rc, asked) == (code, 1)
    assert _Written.of(world, task) == held[0]
    assert says in capsys.readouterr().err
    assert world.move(task, "in-progress") == code
    assert says in capsys.readouterr().err


@pytest.mark.parametrize(
    ("unplace", "code", "says"),
    [
        pytest.param(_unreadable_issue, 2, "HTTP 502: Bad Gateway", id="unreadable-issue"),
        pytest.param(_stray_label, 2, "no transition 'blocked' → 'in-progress'", id="stray-label"),
    ],
)
def test_where_labels_carry_the_state_a_later_read_placing_nothing_refuses_as_a_first_read(
    labels_world: World,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    unplace: Callable[[World, int], None],
    code: int,
    says: str,
) -> None:
    _refused_as_a_first_read(labels_world, monkeypatch, capsys, unplace, code, says)


@pytest.mark.parametrize(
    ("unplace", "code", "says"),
    [
        pytest.param(_unreadable_issue, 2, "HTTP 502: Bad Gateway", id="unreadable-issue"),
        pytest.param(_status(None), 1, "has no Status", id="no-status"),
        pytest.param(_status("Done"), 1, "names no open state", id="not-open"),
        pytest.param(
            _board_unreadable,
            3,
            "could not be read: missing required scopes [read:project]",
            id="unreadable-board",
        ),
    ],
)
def test_where_the_board_carries_the_state_a_later_read_placing_nothing_refuses_as_a_first_read(
    board_world: World,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    unplace: Callable[[World, int], None],
    code: int,
    says: str,
) -> None:
    _refused_as_a_first_read(board_world, monkeypatch, capsys, unplace, code, says)


def test_a_later_read_that_cannot_read_the_issue_says_nothing_was_written(
    world: World, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    task = _task(world, "backlog")

    rc, _ = _at_a_terminal(
        world, monkeypatch, task, "in-progress", meanwhile=lambda: _unreadable_issue(world, task)
    )

    assert rc == 2
    err = capsys.readouterr().err
    assert f"→ #{task} was not read again before the write, so nothing was written." in err
