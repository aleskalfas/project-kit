"""Where the substrate map binds the state to the board, its Status is the source (#2271).

[project-management:DEC-062-axes-chosen-in-the-map] point 5: where the map binds
`state: {board: true}`, an open issue stands where its card's Status places it,
and a closed issue is Done whatever its card says. [project-management:DEC-051-
axis-carriage-activation] point 6 says how it is read: the board cannot be read,
no card, no Status, and a Status naming no open state are four outcomes, each
its own, and none falls back to the labels or the milestone.

These tests pin the read in each of its consumers — the pure inference, the
lifecycle's classifier, `move-issue`, the early check of `start-work` and
`review-work`, the pool `next-task` takes from, and the listing of `seats` — and
the writes where the Status is the source: a move, the forward cascade. They run
the real scripts and the real engine against an in-memory GitHub with a board
(`tests/pm_board_world.py`).
"""

from __future__ import annotations

from pathlib import Path
from types import ModuleType

import pytest

from tests.pm_board_world import BOARD_CONFIG, STATE_ON_BOARD, BoardTracker
from tests.pm_lifecycle_world import (
    AUTHORED_BODY,
    CAPABILITY_ROOT,
    MILESTONE,
    World,
    load_script,
    make_engine_repo,
    predicates,
    wire,
)

CONTAINER_BODY = "## What\n\nA container.\n"


@pytest.fixture(scope="module")
def ci() -> ModuleType:
    return load_script("create-issue.py", "pm_create_issue_board_carried_state")


@pytest.fixture(scope="module")
def pi() -> ModuleType:
    return load_script("promote-issue.py", "pm_promote_issue_board_carried_state")


@pytest.fixture(scope="module")
def mi() -> ModuleType:
    return load_script("move-issue.py", "pm_move_issue_board_carried_state")


@pytest.fixture(scope="module")
def hist() -> ModuleType:
    return load_script("history.py", "pm_history_board_carried_state")


@pytest.fixture
def world(tmp_path: Path, ci, pi, mi, hist, monkeypatch: pytest.MonkeyPatch) -> World:
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


@pytest.fixture
def board(world: World) -> BoardTracker:
    assert isinstance(world.tracker, BoardTracker)
    return world.tracker


def _task(world: World, board: BoardTracker, status: str | None = "Todo", parent=None) -> int:
    body = f"Feature: #{parent}\n\n{AUTHORED_BODY}" if parent else AUTHORED_BODY
    number = world.file_issue(body=body)
    board.card(number, status)
    return number


def _container(world: World, board: BoardTracker, title: str, parent=None) -> int:
    body = f"EPIC: #{parent}\n\n{CONTAINER_BODY}" if parent else CONTAINER_BODY
    number = world.file_issue(body=body, title=title, labels=())
    board.card(number, "Todo")
    return number


# --- the inference is pure, and guesses nothing --------------------------------


def _infer(substrate_map, *, state="open", status=None, labels=(), milestone=None) -> str:
    return predicates.infer.infer_current_state(
        state=state,
        milestone=milestone,
        labels=list(labels),
        substrate_map=substrate_map,
        status=status,
    )


def test_an_open_issue_stands_where_its_status_places_it(mi) -> None:
    on_board = mi.axis_labels.SubstrateMap(axes=STATE_ON_BOARD)
    placed = predicates.infer.StatusRead("placed", state="review")

    assert _infer(on_board, status=placed) == "review"


def test_a_closed_issue_is_done_whatever_its_card_says(mi) -> None:
    on_board = mi.axis_labels.SubstrateMap(axes=STATE_ON_BOARD)
    placed = predicates.infer.StatusRead("placed", state="in-progress")

    assert _infer(on_board, state="closed", status=placed) == "done"
    assert _infer(on_board, state="closed") == "done"


@pytest.mark.parametrize("outcome", ["unreadable", "no-card", "unset", "not-open", None])
def test_a_status_that_does_not_place_the_issue_is_never_guessed(mi, outcome) -> None:
    """No fallback to the labels or the milestone (DEC-051 point 6)."""
    on_board = mi.axis_labels.SubstrateMap(axes=STATE_ON_BOARD)
    status = None if outcome is None else predicates.infer.StatusRead(outcome)

    position = _infer(on_board, status=status, labels=("state:in-progress",), milestone=MILESTONE)

    assert position == predicates.infer.UNDETERMINED
    assert position not in predicates.infer.STATE_ORDER


def test_without_the_binding_the_status_is_not_read(mi) -> None:
    """With no map, the kit's labels carry the state, board or no board."""
    placed = predicates.infer.StatusRead("placed", state="review")

    assert _infer(None, status=placed, labels=("state:backlog",)) == "backlog"


# --- the lifecycle's classifier -----------------------------------------------


def test_the_classifier_reads_the_cards_status(world: World, board: BoardTracker) -> None:
    task = _task(world, board, "In Progress")
    world.tracker.issues[task]["milestone"] = MILESTONE  # ignored: the board carries it

    answer = predicates.classify_state(task)

    assert answer["state"] == "in-progress"
    assert world._engine(task).resolve_position().state_id == "in-progress"


@pytest.mark.parametrize(
    ("status", "says"),
    [
        (None, "has no Status"),
        ("Done", "has the Status 'Done', which names no open state"),
        ("no card", "has no card on board #4"),
    ],
)
def test_the_classifier_places_an_unplaced_issue_in_no_state_and_says_why(
    world: World, board: BoardTracker, status: str | None, says: str
) -> None:
    task = _task(world, board, None if status == "no card" else status)
    if status == "no card":
        del board.cards[task]

    answer = predicates.classify_state(task)

    assert answer["state"] is None
    assert says in answer["reason"]


def test_the_classifier_has_no_answer_where_the_board_cannot_be_read(
    world: World, board: BoardTracker, capsys: pytest.CaptureFixture[str]
) -> None:
    task = _task(world, board, "Todo")
    board.fail_reads.add("fields")

    answer = predicates.classify_state(task)

    assert answer.get(predicates.INDETERMINATE_KEY) is True
    assert "missing required scopes [read:project]" in capsys.readouterr().err
    assert world._engine(task).resolve_position().indeterminate


def test_the_classifier_reads_no_board_for_a_closed_issue(
    world: World, board: BoardTracker
) -> None:
    task = _task(world, board, "Review")
    world.tracker.close(task, "COMPLETED")
    board.calls.clear()

    assert predicates.classify_state(task)["state"] == "done"
    assert board.board_calls() == []


# --- move-issue: the Status is the source, and its write is the move ----------


def test_a_move_writes_the_cards_status_and_no_label(world: World, board: BoardTracker) -> None:
    task = _task(world, board, "Backlog")

    assert world.move(task, "in-progress") == 0

    assert board.status(task) == "In Progress"
    assert board.edits == [(task, "In Progress")]
    assert not [label for label in world.labels(task) if label.startswith("state:")]
    assert world.moves(task)[-1][:2] == ("backlog", "in-progress")


def test_a_status_write_that_fails_leaves_the_move_unmade(
    world: World, board: BoardTracker, capsys: pytest.CaptureFixture[str]
) -> None:
    task = _task(world, board, "Backlog")
    board.fail_edits.add(task)

    assert world.move(task, "in-progress") == 3

    assert board.status(task) == "Backlog"
    assert world.journal(task) == []
    err = capsys.readouterr().err
    assert "the board's Status was not set to 'In Progress'" in err
    assert "did not move: nothing was journaled" in err


@pytest.mark.parametrize(
    ("status", "code", "says"),
    [
        (None, 1, "has no Status"),
        ("Done", 1, "names no open state"),
        ("no card", 1, "has no card on board #4"),
        ("unreadable", 3, "could not be read: missing required scopes [read:project]"),
    ],
)
def test_a_move_of_an_issue_its_status_does_not_place_is_refused(
    world: World,
    board: BoardTracker,
    capsys: pytest.CaptureFixture[str],
    status: str | None,
    code: int,
    says: str,
) -> None:
    """Each outcome refuses with its own message, and nothing is written: no
    Status, no label, no journal entry (DEC-051 point 6)."""
    task = _task(world, board, status if status not in ("no card", "unreadable") else "Todo")
    world.tracker.issues[task]["milestone"] = MILESTONE
    world.tracker.issues[task]["labels"].append("state:backlog")
    if status == "no card":
        del board.cards[task]
    if status == "unreadable":
        board.fail_reads.add("fields")
    labels = list(world.labels(task))

    assert world.move(task, "in-progress") == code

    assert board.edits == [] and world.journal(task) == []
    assert world.labels(task) == labels
    err = capsys.readouterr().err
    assert f"[refused] #{task} does not move to in-progress" in err
    assert says in err
    assert "never guessed from the labels or the milestone" in err


def test_a_move_reads_and_writes_cards_by_the_node_ids_its_issue_reads_gave(
    world: World, board: BoardTracker
) -> None:
    """The issue's node id is an input of the card's read, from the command's
    own read of the issue, and of the ancestors' reads its cascade makes: no
    issue is read again for it, so a failed issue read is never an unreadable
    board."""
    epic = _container(world, board, "[EPIC] An epic")
    feature = _container(world, board, "[Feature] A feature", epic)
    task = _task(world, board, "Backlog", parent=feature)
    board.calls.clear()

    assert world.move(task, "in-progress") == 0

    assert board.status(epic) == "In Progress"
    assert [argv for argv in board.board_calls() if argv[1:3] == ["issue", "view"]] == []


def test_with_no_board_configured_a_move_refuses_and_calls_no_board(
    world: World,
    board: BoardTracker,
    mi,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A map binding the state to the board under a configuration naming no
    board makes no `gh` call for the state (ADR-053 point 3), and the refusal
    names the missing board."""
    task = _task(world, board, "Backlog")
    read_yaml = mi._read_yaml

    def read(path: Path, loader):
        return {} if path.name == "config.yaml" else read_yaml(path, loader)

    monkeypatch.setattr(mi, "_read_yaml", read)
    monkeypatch.setattr(predicates, "_config", lambda _root: {})
    board.calls.clear()

    assert world.move(task, "in-progress") == 3

    assert board.board_calls() == []
    assert not [argv for argv in board.calls if argv[1:3] == ["repo", "view"]]
    err = capsys.readouterr().err
    assert "no Projects v2 board configured" in err
    assert "#None" not in err
    assert "fix what is named above" in err


@pytest.mark.parametrize(
    ("setup", "says"),
    [
        ("unreadable", "could not be read: HTTP 502: Bad Gateway"),
        ("Done", "has the Status 'Done', which names no open state"),
    ],
)
def test_a_closed_issue_whose_card_places_nothing_names_the_card_not_a_close_reason(
    world: World,
    board: BoardTracker,
    capsys: pytest.CaptureFixture[str],
    setup: str,
    says: str,
) -> None:
    """Where the board carries the state, a closed issue's card says where the
    work stood. A read of it that places nothing is named as such, with what the
    board said, never as a close reason missing."""
    feature = _container(world, board, "[Feature] A feature")
    task = _task(world, board, "Done" if setup == "Done" else "Review", parent=feature)
    world.tracker.close(task, None)
    if setup == "unreadable":
        board.fail_reads.add("card")

    assert world.move(task, "done") == 0

    captured = capsys.readouterr()
    said = captured.out + captured.err
    assert "the forward cascade moves no ancestor" in said
    assert says in said
    assert "no close reason is reported" not in said
    assert board.status(feature) == "Todo"


def test_a_closed_issue_moved_to_done_has_its_card_set_to_done(
    world: World, board: BoardTracker
) -> None:
    """A merge's close moves the issue to Done with no move of ours; the card may
    still say Review, and is set to Done."""
    task = _task(world, board, "Review")
    world.tracker.close(task, "COMPLETED")

    assert world.move(task, "done") == 0

    assert board.status(task) == "Done"


def test_a_move_back_is_refused_where_the_board_carries_the_state(
    world: World, board: BoardTracker, capsys: pytest.CaptureFixture[str]
) -> None:
    task = _task(world, board, "In Progress")
    world.tracker.issues[task]["milestone"] = MILESTONE

    assert world.move(task, "backlog", "--reason", "the work stopped") == 1

    assert board.edits == [] and world.journal(task) == []
    assert "where it does, a move back is refused (DEC-006)" in capsys.readouterr().err


def test_a_dry_run_names_the_status_write_and_writes_nothing(
    world: World, board: BoardTracker, capsys: pytest.CaptureFixture[str]
) -> None:
    task = _task(world, board, "Backlog")

    assert world.move(task, "in-progress", "--dry-run") == 0

    out = capsys.readouterr().out
    assert "~ set the card's Status on board #4 to 'In Progress', the state's source" in out
    assert board.edits == []


# --- the forward cascade writes each ancestor's Status ------------------------


def test_the_forward_cascade_writes_each_ancestors_status_step_by_step(
    world: World, board: BoardTracker
) -> None:
    epic = _container(world, board, "[EPIC] An epic")
    feature = _container(world, board, "[Feature] A feature", epic)
    task = _task(world, board, "Backlog", parent=feature)

    assert world.move(task, "in-progress") == 0

    assert board.status(feature) == board.status(epic) == "In Progress"
    assert board.edits == [
        (task, "In Progress"),
        (feature, "Backlog"),
        (feature, "In Progress"),
        (epic, "Backlog"),
        (epic, "In Progress"),
    ]
    for ancestor in (feature, epic):
        assert [move[:2] for move in world.moves(ancestor)] == [
            ("todo", "backlog"),
            ("backlog", "in-progress"),
        ]


def test_an_ancestor_its_status_does_not_place_stops_the_walk(
    world: World, board: BoardTracker, capsys: pytest.CaptureFixture[str]
) -> None:
    epic = _container(world, board, "[EPIC] An epic")
    feature = _container(world, board, "[Feature] A feature", epic)
    task = _task(world, board, "Backlog", parent=feature)
    del board.cards[feature]

    assert world.move(task, "in-progress") == 0

    assert board.status(task) == "In Progress"
    assert board.status(epic) == "Todo"
    err = capsys.readouterr().err
    assert f"#{feature} has no card on board #4" in err
    assert "the walk stops there" in err


# --- the early check of start-work and review-work ----------------------------


def test_the_early_check_reads_the_status_and_refuses_an_unplaced_issue(
    world: World, board: BoardTracker
) -> None:
    from _lib import issue_position

    task = _task(world, board, None)
    on_board = predicates.axis_labels.SubstrateMap(axes=STATE_ON_BOARD)
    issue = {"state": "OPEN", "milestone": MILESTONE, "id": f"I_{task}"}
    workflow = predicates._workflow(CAPABILITY_ROOT)

    status = issue_position.read_status(task, issue, dict(BOARD_CONFIG), on_board, workflow)
    current = issue_position.current_state(issue, ["state:backlog"], on_board, status)

    assert status is not None and status.outcome == "unset"
    assert current == predicates.infer.UNDETERMINED
    refusal = issue_position.unplaced_refusal("start-work", task, status, untouched="no branch")
    assert f"[refused] start-work #{task}: #{task}'s card on board #4 has no Status" in refusal
    assert "Nothing was changed (no branch)" in refusal


def test_the_early_check_reads_no_board_where_the_map_carries_the_state_off_it(
    world: World, board: BoardTracker
) -> None:
    from _lib import issue_position

    board.calls.clear()
    status = issue_position.read_status(1, {"state": "OPEN"}, dict(BOARD_CONFIG), None, {})

    assert status is None and board.board_calls() == []


@pytest.mark.parametrize(
    "script", ["start-work.py", "review-work.py", "close-issue.py", "move-issue.py"]
)
def test_each_command_reading_one_issues_card_reads_its_node_id_and_url(
    script: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The issue's node id finds its card, so the board read asks only the
    board; its url names the board's owner where `gh.default_owner` is unset,
    so no repository is read for it."""
    module = load_script(script, f"pm_{script.replace('-', '_')}_issue_fields")
    asked: list[str] = []

    def read(_number, _config, *, fields):
        asked.append(fields)

    monkeypatch.setattr(module, "gh_get_issue", read)
    module._gh_get_issue(7, {})

    assert {"id", "url"} <= set(asked[0].split(","))
