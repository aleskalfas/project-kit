"""`sync-board` writes the board's Status again from every issue's state (#2276).

DEC-006 makes the board's Status a projection the agent maintains, and native
wins where the two disagree. `sync-board` reads every issue's state as
`_lib/lifecycle_inference` does, writes the Status only on the cards that
differ, adds a card for an open issue that has none, and names each card whose
Status disagreed. `--dry-run` prints the plan, and `--yes` runs it with nobody
at a terminal. These tests run the script against an in-memory GitHub with a
board (`tests/pm_board_world.py`).
"""

from __future__ import annotations

import subprocess
import sys
from types import ModuleType

import pytest

from tests.pm_board_world import (
    BOARD_CONFIG,
    LABEL_STATE,
    BoardTracker,
    foreign_card,
)
from tests.pm_lifecycle_world import CAPABILITY_ROOT, INVOKER, MILESTONE, load_script


@pytest.fixture(scope="module")
def sb() -> ModuleType:
    return load_script("sync-board.py", "pm_sync_board_under_test")


@pytest.fixture
def board(sb: ModuleType, monkeypatch: pytest.MonkeyPatch) -> BoardTracker:
    tracker = BoardTracker()

    def run(argv, *args, **kwargs):
        argv = [str(arg) for arg in argv]
        assert argv[0] == "gh", argv
        return tracker.gh(argv)

    monkeypatch.setattr(subprocess, "run", run)
    monkeypatch.setattr(sb.session_guard, "enforce", lambda **kw: True)
    monkeypatch.setattr(sb.bootstrap_gate, "enforce", lambda *a, **kw: True)
    monkeypatch.setattr(sb, "resolve_invoker_identity", lambda config=None: INVOKER)
    _configure(sb, monkeypatch, BOARD_CONFIG, LABEL_STATE)
    return tracker


def _configure(sb: ModuleType, monkeypatch, config: dict, axes: dict | None) -> None:
    substrate_map = None if axes is None else sb.axis_labels.SubstrateMap(axes=axes)
    monkeypatch.setattr(sb, "load_adopter_config", lambda root: dict(config))
    monkeypatch.setattr(sb.axis_labels, "load_substrate_map", lambda *a, **kw: substrate_map)


def _issue(board: BoardTracker, *labels: str, closed: bool = False, milestone=None) -> int:
    number = len(board.issues) + 1
    board.issues[number] = {
        "title": f"[Task] Issue {number}",
        "body": "## What\n\nwork\n",
        "state": "CLOSED" if closed else "OPEN",
        "labels": list(labels),
        "assignees": [],
        "milestone": milestone,
    }
    return number


def _sync(sb: ModuleType, *options: str) -> int:
    saved = sys.argv
    sys.argv = ["sync-board.py", *options, "--capability-root", str(CAPABILITY_ROOT)]
    try:
        return sb.main()
    finally:
        sys.argv = saved


def _a_board_out_of_step(board: BoardTracker) -> dict[str, int]:
    """Issues whose cards differ from their states, one that agrees, one with no
    card, and cards that are not this repository's issues."""
    started = _issue(board, "type:task", "state:in-progress")
    scheduled = _issue(board, "type:task", milestone=MILESTONE)
    closed = _issue(board, "type:task", "state:review", closed=True)
    level = _issue(board, "type:task")
    no_card = _issue(board, "type:task")
    board.card(started, "Todo")
    board.card(scheduled)
    board.card(closed, "Review")
    board.card(level, "Todo")
    board.foreign_cards += [
        foreign_card("PVTI_other", "Issue", 1, repository="acme/other"),
        foreign_card("PVTI_pr", "PullRequest", 99),
        foreign_card("PVTI_draft", "DraftIssue", None),
    ]
    return {
        "started": started,
        "scheduled": scheduled,
        "closed": closed,
        "level": level,
        "no_card": no_card,
    }


# --- the plan and the run ----------------------------------------------------


def test_it_writes_only_the_cards_that_differ_and_adds_the_missing_ones(
    sb: ModuleType, board: BoardTracker, capsys: pytest.CaptureFixture[str]
) -> None:
    n = _a_board_out_of_step(board)

    assert _sync(sb, "--yes") == 0

    assert board.edits == [
        (n["started"], "In Progress"),
        (n["scheduled"], "Backlog"),
        (n["closed"], "Done"),
        (n["no_card"], "Todo"),
    ]
    assert board.adds == [n["no_card"]]
    out = capsys.readouterr().out
    assert (
        "The cards whose Status differs from their issue's state, which wins (DEC-006):\n"
        f"  #{n['started']}: Todo → In Progress\n"
        f"  #{n['scheduled']}: no Status → Backlog\n"
        f"  #{n['closed']}: Review → Done\n"
    ) in out
    assert f"The open issues with no card, to be added:\n  #{n['no_card']}: → Todo\n" in out
    assert "plan: 3 cards to set, 1 card to add, 1 card already right" in out
    assert "done: 4 Status set, 1 card added, 0 failed" in out


def test_a_dry_run_prints_the_plan_and_writes_nothing(
    sb: ModuleType, board: BoardTracker, capsys: pytest.CaptureFixture[str]
) -> None:
    n = _a_board_out_of_step(board)

    assert _sync(sb, "--dry-run") == 0

    out = capsys.readouterr().out
    assert f"  #{n['started']}: Todo → In Progress\n" in out
    assert "[dry-run] nothing written." in out
    assert board.edits == [] and board.adds == []


def test_a_board_in_step_writes_nothing(
    sb: ModuleType, board: BoardTracker, capsys: pytest.CaptureFixture[str]
) -> None:
    board.card(_issue(board, "state:review"), "Review")
    board.card(_issue(board, closed=True), "Done")

    assert _sync(sb, "--yes") == 0

    assert board.edits == [] and board.adds == []
    assert "every card's Status matches its issue's state; nothing to write." in (
        capsys.readouterr().out
    )


def test_with_nobody_to_ask_and_no_yes_it_refuses_and_writes_nothing(
    sb: ModuleType, board: BoardTracker, capsys: pytest.CaptureFixture[str]
) -> None:
    _a_board_out_of_step(board)

    assert _sync(sb) == 2

    assert board.edits == [] and board.adds == []
    assert "pkit pm sync-board" in capsys.readouterr().err


# --- the board's owner -------------------------------------------------------
# With no `gh.default_owner`, the board is the repository's owner's, a person's or
# an organisation's (the capability's README, the `gh:` block). Every read and
# card added names that owner, never the person who runs `gh`.


@pytest.mark.parametrize(
    ("repository", "owner", "default_owner"),
    [
        pytest.param("acme/repo", "acme", None, id="an-organisations-board-no-default-owner"),
        pytest.param("acme/repo", "acme", "acme", id="an-organisations-board-its-default-owner"),
        pytest.param("alice/repo", "alice", None, id="a-persons-board-no-default-owner"),
        pytest.param("alice/repo", "alice", "alice", id="a-persons-board-its-default-owner"),
        pytest.param("alice/repo", "acme", "acme", id="a-board-of-another-owner-named"),
    ],
)
def test_the_board_is_found_under_its_owner(
    sb: ModuleType,
    board: BoardTracker,
    monkeypatch: pytest.MonkeyPatch,
    repository: str,
    owner: str,
    default_owner: str | None,
) -> None:
    board.repository, board.owner = repository, owner
    if default_owner:
        _configure(
            sb, monkeypatch, dict(BOARD_CONFIG, gh={"default_owner": default_owner}), LABEL_STATE
        )
    n = _a_board_out_of_step(board)

    assert _sync(sb, "--yes") == 0

    assert (n["started"], "In Progress") in board.edits
    assert board.adds == [n["no_card"]]
    reads = [argv for argv in board.calls if argv[1:2] == ["project"] and argv[2] != "item-edit"]
    assert {argv[argv.index("--owner") + 1] if "--owner" in argv else None for argv in reads} == {
        owner
    }


# --- the Status options ----------------------------------------------------


def test_a_missing_option_is_named_with_its_remedy_and_its_cards_are_left(
    sb: ModuleType, board: BoardTracker, capsys: pytest.CaptureFixture[str]
) -> None:
    del board.options["Review"]
    in_review = _issue(board, "state:review")
    started = _issue(board, "state:in-progress")
    board.card(in_review, "Todo")
    board.card(started, "Todo")

    assert _sync(sb, "--yes") == 0

    assert board.edits == [(started, "In Progress")]
    captured = capsys.readouterr()
    assert (
        "[warn] the board's Status field has no option for Review: add it to the field "
        "on the board, then run sync-board again"
    ) in captured.err
    assert (
        "The cards left as they are:\n"
        f"  #{in_review}: the board's Status field has no 'Review' option\n"
    ) in captured.out


# --- what stops it -----------------------------------------------------------


def test_with_no_board_configured_it_refuses_and_reads_no_board(
    sb: ModuleType,
    board: BoardTracker,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _configure(sb, monkeypatch, {}, LABEL_STATE)

    assert _sync(sb, "--yes") == 2

    assert board.calls == []
    assert "no Projects v2 board is configured" in capsys.readouterr().err


def test_where_the_board_carries_the_state_it_refuses_and_writes_nothing(
    sb: ModuleType,
    board: BoardTracker,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _configure(sb, monkeypatch, BOARD_CONFIG, None)

    assert _sync(sb, "--yes") == 2

    assert board.calls == []
    assert "the Status is the state's source" in capsys.readouterr().err


def test_a_non_member_is_refused(
    sb: ModuleType, board: BoardTracker, monkeypatch: pytest.MonkeyPatch
) -> None:
    refused = type("Refused", (), {"allowed": False, "refusal_message": "not a member"})()
    monkeypatch.setattr(sb, "check_membership", lambda members, invoker: refused)

    assert _sync(sb, "--yes") == 1

    assert board.calls == []


def test_the_foreign_repo_guard_refuses_before_any_write(
    sb: ModuleType, board: BoardTracker, monkeypatch: pytest.MonkeyPatch
) -> None:
    _a_board_out_of_step(board)
    monkeypatch.setattr(sb.session_guard, "enforce", lambda **kw: False)

    assert _sync(sb, "--yes") == 1

    assert board.edits == [] and board.adds == []


def test_an_unreadable_board_stops_it_with_what_gh_said(
    sb: ModuleType, board: BoardTracker, capsys: pytest.CaptureFixture[str]
) -> None:
    _a_board_out_of_step(board)
    board.fail_reads.add("items")

    assert _sync(sb, "--yes") == 3

    assert board.edits == []
    assert "missing required scopes [read:project]" in capsys.readouterr().err


def test_a_write_that_fails_is_said_and_the_others_are_made(
    sb: ModuleType, board: BoardTracker, capsys: pytest.CaptureFixture[str]
) -> None:
    n = _a_board_out_of_step(board)
    board.fail_edits.add(n["started"])
    board.fail_adds.add(n["no_card"])

    assert _sync(sb, "--yes") == 3

    assert board.edits == [(n["scheduled"], "Backlog"), (n["closed"], "Done")]
    out = capsys.readouterr().out
    assert f"  [fail] #{n['no_card']}: its card could not be added: HTTP 502: Bad Gateway" in out
    assert "done: 2 Status set, 0 cards added, 2 failed" in out
