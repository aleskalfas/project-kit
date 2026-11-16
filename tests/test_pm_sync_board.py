"""`sync-board` brings the board in line with the issues (#2276, #3301).

DEC-006 makes the board's Status a projection the agent maintains, and native
wins where the two disagree. Where it is the projection, `sync-board` reads every
issue's state as `_lib/lifecycle_inference` does, writes the Status only on the
cards that differ, adds a card for an open issue that has none, and names each
card whose Status disagreed. Wherever a board is configured, it gives each open
issue with no card its card, and where the board holds the state, or the state
degrades, it writes no Status: where the board holds it, it adds only in a run at
a terminal or with the project's switch on, reads each added card back, and names
each open issue whose card does not place it
([project-management:DEC-072-sync-gives-missing-cards]). `--dry-run` prints the
plan, and `--yes` runs it with nobody at a terminal. These tests run the script
against an in-memory GitHub with a board (`tests/pm_board_world.py`).
"""

from __future__ import annotations

import subprocess
import sys
from types import ModuleType

import pytest

from tests.pm_board_graphql import flag_value, query_of
from tests.pm_board_world import (
    BOARD_CONFIG,
    LABEL_STATE,
    STATE_ON_BOARD,
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


def test_an_issue_whose_only_card_is_archived_has_a_card(
    sb: ModuleType, board: BoardTracker, capsys: pytest.CaptureFixture[str]
) -> None:
    """An archived card is its issue's card, as any other (#3191): no card is
    added for its issue, and its Status is kept in step with the issue's state."""
    in_review = _issue(board, "type:task", "state:review")
    started = _issue(board, "type:task", "state:in-progress")
    board.card(in_review, "Review", archived=True)
    board.card(started, "Todo", archived=True)

    assert _sync(sb, "--yes") == 0

    assert board.adds == []
    assert board.edits == [(started, "In Progress")]
    assert "plan: 1 card to set, 0 cards to add, 1 card already right" in capsys.readouterr().out


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


def test_with_no_map_the_status_is_kept_and_synced(
    sb: ModuleType,
    board: BoardTracker,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The board flag carries no axis (DEC-062 point 1): with no map, the kit's
    labels carry the state, and the board's Status is their projection."""
    _configure(sb, monkeypatch, BOARD_CONFIG, None)
    number = _issue(board, "state:backlog")
    board.card(number, "Todo")

    assert _sync(sb, "--yes") == 0

    assert board.status(number) == "Backlog"


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


@pytest.mark.parametrize(
    ("field_name", "field_type", "said"),
    [
        pytest.param(
            "Stage",
            "ProjectV2SingleSelectField",
            "the board has no `Status` field (its fields: Title, Stage)",
            id="no-status-field",
        ),
        pytest.param(
            "Status",
            "ProjectV2Field",
            "the board's `Status` field is a ProjectV2Field, not a single-select",
            id="a-status-field-not-single-select",
        ),
    ],
)
def test_a_board_with_no_single_select_status_stops_it_as_a_usage_fault(
    sb: ModuleType,
    board: BoardTracker,
    capsys: pytest.CaptureFixture[str],
    field_name: str,
    field_type: str,
    said: str,
) -> None:
    """A Status field the board answered without is a fault the read names, so
    the run exits 2, as its help says (#3188)."""
    _a_board_out_of_step(board)
    board.field_name, board.field_type = field_name, field_type

    assert _sync(sb, "--yes") == 2

    assert board.edits == [] and board.adds == []
    assert f"error: the board's Status could not be read: {said}" in capsys.readouterr().err


def test_a_status_field_gh_could_not_read_stops_it_as_a_gh_failure(
    sb: ModuleType, board: BoardTracker, capsys: pytest.CaptureFixture[str]
) -> None:
    """A Status field `gh` failed to read is a `gh` failure, so the run exits 3,
    with what `gh` said (#3188)."""
    _a_board_out_of_step(board)
    board.fail_reads.add("fields")

    assert _sync(sb, "--yes") == 3

    assert board.edits == [] and board.adds == []
    assert (
        "error: the board's Status could not be read: missing required scopes [read:project]"
    ) in capsys.readouterr().err


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


# --- only the issues a run names (DEC-072 point 1) ----------------------------


def test_a_run_naming_issues_writes_plans_and_reports_only_for_them(
    sb: ModuleType, board: BoardTracker, capsys: pytest.CaptureFixture[str]
) -> None:
    """Where the Status is the projection, a run naming issues writes no other
    card's Status, and lists each named issue it does nothing for, with why."""
    n = _a_board_out_of_step(board)

    named = (n["started"], n["no_card"], n["level"], 999)
    assert _sync(sb, "--yes", *(str(number) for number in named)) == 0

    assert board.edits == [(n["started"], "In Progress"), (n["no_card"], "Todo")]
    assert board.adds == [n["no_card"]]
    out = capsys.readouterr().out
    assert f"#{n['scheduled']}" not in out and f"#{n['closed']}" not in out
    assert (
        "The issues named that this run does nothing for:\n"
        f"  #{n['level']}: on the board already, with nothing to write\n"
        "  #999: not among this repository's open issues this run read, and no card on the "
        "board holds it: a closed issue, or a number no issue holds\n"
    ) in out
    assert "4 issues named" in out


def test_a_named_state_issue_is_listed_as_one(
    sb: ModuleType,
    board: BoardTracker,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _configure(sb, monkeypatch, BOARD_CONFIG, STATE_ON_BOARD)
    held = _issue(board, "type:task")
    board.issues[held]["body"] = "<!-- pkit:state-issue v=1 kind=seat key=planner -->\n"

    assert _sync(sb, "--yes", str(held)) == 0

    assert board.adds == []
    out = capsys.readouterr().out
    assert f"  #{held}: a state issue, which holds no work and takes no card" in out


def test_an_issue_number_must_be_a_number(sb: ModuleType, board: BoardTracker) -> None:
    with pytest.raises(SystemExit) as exited:
        _sync(sb, "--yes", "twelve")
    assert exited.value.code == 2
    assert board.calls == []


# --- where the board holds the state (DEC-072 points 2 to 4) ------------------


class _Terminal:
    """Standard input on a terminal, as a run at a terminal has it."""

    def isatty(self) -> bool:
        return True


def _at_terminal(monkeypatch: pytest.MonkeyPatch, answer: str = "y") -> list[str]:
    """A run whose standard input is a terminal, its standard output captured as
    a pipe would take it, answering ``answer`` to each question. The questions
    asked are returned."""
    asked: list[str] = []
    monkeypatch.setattr(sys, "stdin", _Terminal())

    def reply(prompt: str = "") -> str:
        asked.append(prompt)
        return answer

    monkeypatch.setattr("builtins.input", reply)
    return asked


def _switch(sb: ModuleType, monkeypatch: pytest.MonkeyPatch, *, on: bool) -> None:
    said = "`sync_board.adds_with_no_terminal` is on" if on else "it is off"
    monkeypatch.setattr(
        sb.sync_switch, "read", lambda config, root, **kw: sb.sync_switch.Switch(on, said)
    )


def _a_board_holding_the_state(
    sb: ModuleType, board: BoardTracker, monkeypatch: pytest.MonkeyPatch
) -> dict[str, int]:
    """Open issues with a card that places them, a card with no Status, a card
    whose Status names no open state, an archived card, and no card; and a closed
    issue whose card is short of Done."""
    _configure(sb, monkeypatch, BOARD_CONFIG, STATE_ON_BOARD)
    placed = _issue(board, "type:task")
    unset = _issue(board, "type:task")
    done = _issue(board, "type:task")
    archived = _issue(board, "type:task")
    no_card = _issue(board, "type:task", "state:in-progress")
    closed = _issue(board, "type:task", closed=True)
    board.card(placed, "In Progress")
    board.card(unset)
    board.card(done, "Done")
    board.card(archived, "Review", archived=True)
    board.card(closed, "Review")
    return {
        "placed": placed,
        "unset": unset,
        "done": done,
        "archived": archived,
        "no_card": no_card,
        "closed": closed,
    }


def test_at_a_terminal_it_adds_the_missing_cards_and_writes_no_status(
    sb: ModuleType,
    board: BoardTracker,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A run whose standard input is a terminal and whose output goes to a pipe
    is asked, and on a yes adds the cards. No Status is written, a closed issue's
    card included, and the plan says what the position then is."""
    n = _a_board_holding_the_state(sb, board, monkeypatch)
    asked = _at_terminal(monkeypatch)

    assert _sync(sb) == 0

    assert asked == ["Write 1 card? [y/N] "]
    assert board.adds == [n["no_card"]]
    assert board.edits == []
    assert board.status(n["no_card"]) is None
    out = capsys.readouterr().out
    assert "which holds the state: it gives each open issue its card, and writes no Status" in out
    assert f"The open issues with no card, to be added:\n  #{n['no_card']}\n" in out
    assert (
        "The sync writes no Status on a card it adds, and the board's own automation may "
        "set one when the card is added."
    ) in out
    assert (
        "Each added issue's position stays undetermined until a person sets its card's "
        "Status on the board, and every command would read a Status the automation set as "
        "the issue's position (DEC-051 point 6)."
    ) in out
    assert "plan: 1 card to add, 4 issues already on the board" in out
    assert f"  [board] #{n['no_card']}: card added, with no Status" in out
    assert "done: 1 card added, 0 failed" in out


def test_it_names_each_open_issue_whose_card_does_not_place_it(
    sb: ModuleType,
    board: BoardTracker,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The state's reader sorts each outcome from the walk; a card that places
    its issue is not named, and an archived one is named as hidden."""
    n = _a_board_holding_the_state(sb, board, monkeypatch)

    assert _sync(sb, "--dry-run") == 0

    out = capsys.readouterr().out
    unplaced = out.split("The open issues whose card does not place them")[1].split("\n\n")[0]
    assert (
        f"  #{n['unset']}'s card on board #4 has no Status, so its position cannot be read "
        "from it\n"
    ) in unplaced + "\n"
    assert f"  #{n['done']}'s card on board #4 has the Status 'Done'" in unplaced
    assert f"  #{n['placed']}'s" not in unplaced and f"  #{n['archived']}'s" not in unplaced
    assert (
        "The open issues whose only card is archived, which the board's views hide:\n"
        f"  #{n['archived']}: restore its card on the board to see it there\n"
    ) in out
    assert board.edits == [] and board.adds == []


@pytest.mark.parametrize("options", [(), ("--yes",)], ids=["no-yes", "yes"])
def test_with_no_terminal_and_the_switch_off_it_adds_no_card(
    sb: ModuleType,
    board: BoardTracker,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    options: tuple[str, ...],
) -> None:
    """With cards to add, a run neither at a terminal nor with the switch on
    prints its plan, says the cards are added only at a terminal or with the
    switch on, gives the command to run at a terminal, and refuses, whatever
    option it passes."""
    n = _a_board_holding_the_state(sb, board, monkeypatch)
    _switch(sb, monkeypatch, on=False)

    assert _sync(sb, *options) == 2

    assert board.adds == [] and board.edits == []
    captured = capsys.readouterr()
    assert f"  #{n['no_card']}\n" in captured.out
    assert (
        "a card the sync adds there is added only in a run at a terminal, or with the "
        "project's switch `sync_board.adds_with_no_terminal` on, whatever option the run "
        "passes"
    ) in captured.err
    assert (
        f"run this at a terminal:\n  pkit pm sync-board --capability-root {CAPABILITY_ROOT}\n"
        in (captured.err)
    )


def test_with_no_terminal_and_none_to_add_it_passes_clean(
    sb: ModuleType,
    board: BoardTracker,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    n = _a_board_holding_the_state(sb, board, monkeypatch)
    del board.issues[n["no_card"]]
    _switch(sb, monkeypatch, on=False)

    assert _sync(sb, "--yes") == 0

    out = capsys.readouterr().out
    assert (
        f"  #{n['unset']}'s card on board #4 has no Status, so its position cannot be read from it"
    ) in out
    assert "every open issue has its card; nothing to write." in out


def test_a_dry_run_says_which_adds_would_need_a_terminal_or_the_switch(
    sb: ModuleType,
    board: BoardTracker,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _a_board_holding_the_state(sb, board, monkeypatch)

    assert _sync(sb, "--dry-run") == 0

    out = capsys.readouterr().out
    assert (
        "[dry-run] 1 card to add would need a run at a terminal, or the project's switch "
        "`sync_board.adds_with_no_terminal` on."
    ) in out
    assert board.adds == []


def test_with_the_switch_on_a_run_with_no_terminal_adds_the_cards_with_yes(
    sb: ModuleType,
    board: BoardTracker,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    n = _a_board_holding_the_state(sb, board, monkeypatch)
    _switch(sb, monkeypatch, on=True)

    assert _sync(sb, "--yes") == 0

    assert board.adds == [n["no_card"]] and board.edits == []
    assert "so a run with no terminal adds the cards above" in capsys.readouterr().out


def test_with_the_switch_on_a_run_with_no_terminal_still_needs_yes(
    sb: ModuleType,
    board: BoardTracker,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _a_board_holding_the_state(sb, board, monkeypatch)
    _switch(sb, monkeypatch, on=True)

    assert _sync(sb) == 2

    assert board.adds == []
    assert "run again with --yes" in capsys.readouterr().err


def test_where_the_board_holds_the_state_a_run_naming_issues_plans_only_for_them(
    sb: ModuleType,
    board: BoardTracker,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Its adds, the cards it names as not placing their issue, and the issues
    whose only card is archived, are only the named issues'."""
    n = _a_board_holding_the_state(sb, board, monkeypatch)
    other = _issue(board, "type:task")
    _at_terminal(monkeypatch)

    assert _sync(sb, str(n["no_card"]), str(n["unset"]), str(n["placed"])) == 0

    assert board.adds == [n["no_card"]] and board.edits == []
    out = capsys.readouterr().out
    assert "3 issues named" in out
    assert f"  #{n['unset']}'s card on board #4 has no Status" in out
    assert f"#{n['done']}'s" not in out and f"#{other}" not in out
    assert "only card is archived" not in out
    assert f"  #{n['placed']}: on the board already, with nothing to write\n" in out


# --- the read-back (DEC-072 point 3) ---------------------------------------


def _added_by_switch(
    sb: ModuleType, board: BoardTracker, monkeypatch: pytest.MonkeyPatch
) -> dict[str, int]:
    n = _a_board_holding_the_state(sb, board, monkeypatch)
    _switch(sb, monkeypatch, on=True)
    return n


def _card_reads(board: BoardTracker) -> list[list[str]]:
    return [argv for argv in board.graph.graph_calls if "card: node(id: $item)" in query_of(argv)]


def test_the_read_back_names_a_status_the_sync_did_not_write(
    sb: ModuleType,
    board: BoardTracker,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """It reads through the seam, by the card the add answered with, names the
    Status for the person to check, claims no setter and suggests no clearing."""
    n = _added_by_switch(sb, board, monkeypatch)
    board.automation = "Todo"

    assert _sync(sb, "--yes") == 0

    [read] = _card_reads(board)
    assert flag_value(read, "item") == board.cards[n["no_card"]]["id"]
    assert "board: node(id: $board)" in query_of(read)
    out = capsys.readouterr().out
    assert (
        f"  #{n['no_card']}: its card shows the Status 'Todo', which the sync did not write, "
        "and every command now reads it as the issue's position: check it on the board"
    ) in out
    assert "clear" not in out.lower()
    assert board.edits == []


def test_the_read_back_of_a_card_with_no_status_is_no_all_clear(
    sb: ModuleType,
    board: BoardTracker,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    n = _added_by_switch(sb, board, monkeypatch)

    assert _sync(sb, "--yes") == 0

    out = capsys.readouterr().out
    assert (
        f"  #{n['no_card']}: its card showed no Status when read, and the board's automation "
        "may set one later"
    ) in out
    assert "check each card added on the board" in out


def test_a_card_the_read_back_does_not_find_is_not_confirmed(
    sb: ModuleType,
    board: BoardTracker,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    n = _added_by_switch(sb, board, monkeypatch)
    monkeypatch.setattr(board.graph, "card_by_id", lambda item_id, value_field: None)

    assert _sync(sb, "--yes") == 0

    out = capsys.readouterr().out
    assert (
        f"  #{n['no_card']}: its card was not found when read again, so it is not confirmed" in out
    )


def test_a_read_back_the_board_did_not_answer_is_said_and_takes_no_code(
    sb: ModuleType,
    board: BoardTracker,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    n = _added_by_switch(sb, board, monkeypatch)
    board.graph.placed["card"] = "Resource not accessible by integration"

    assert _sync(sb, "--yes") == 0

    out = capsys.readouterr().out
    assert f"  #{n['no_card']}: the board did not answer the read of its card:" in out
    assert "Resource not accessible by integration" in out
    assert board.adds == [n["no_card"]]


# --- a board with no Status field (DEC-072 point 1) --------------------------


def _no_status_field(board: BoardTracker) -> None:
    board.field_name, board.field_type = "Stage", "ProjectV2SingleSelectField"


def test_where_the_board_holds_the_state_with_no_status_field_the_adds_go_on(
    sb: ModuleType,
    board: BoardTracker,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The fault is named once, no issue's outcome is reported as a finding, and
    a run that made adds takes no code that reads as the adds not made."""
    n = _added_by_switch(sb, board, monkeypatch)
    _no_status_field(board)

    assert _sync(sb, "--yes") == 0

    assert board.adds == [n["no_card"]]
    out = capsys.readouterr().out
    assert out.count("[warn] the board can place no issue:") == 1
    assert "the board has no `Status` field" in out
    assert "does not place them" not in out
    assert "so its position cannot be read from it" not in out


def test_where_the_board_holds_the_state_with_no_status_field_no_adds_take_its_code(
    sb: ModuleType,
    board: BoardTracker,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    n = _added_by_switch(sb, board, monkeypatch)
    del board.issues[n["no_card"]]
    _no_status_field(board)

    assert _sync(sb, "--yes") == 2

    assert "[warn] the board can place no issue:" in capsys.readouterr().out


# --- where the state degrades (DEC-072 points 1 and 2) -----------------------


@pytest.mark.parametrize("axes", [{}, {"state": {"unsupported": True}}])
def test_where_the_state_degrades_it_adds_the_cards_and_writes_no_status(
    sb: ModuleType,
    board: BoardTracker,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    axes: dict,
) -> None:
    """A run with no terminal adds the cards with the option that skips the
    question alone: the switch is not read, and nothing is read back."""
    _configure(sb, monkeypatch, BOARD_CONFIG, axes)
    carded = _issue(board, "state:review")
    board.card(carded, "Todo")
    missing = _issue(board, "state:in-progress")

    def not_read(*args, **kwargs):
        raise AssertionError("the switch is not read where the state degrades")

    monkeypatch.setattr(sb.sync_switch, "read", not_read)

    assert _sync(sb, "--yes") == 0

    assert board.adds == [missing] and board.edits == []
    assert board.status(carded) == "Todo"
    assert _card_reads(board) == []
    out = capsys.readouterr().out
    assert "where the state degrades" in out
    assert "the board's own automation may set one when the card is added" in out
    assert "undetermined" not in out


def test_where_the_state_degrades_a_board_with_no_status_field_does_not_stop_the_adds(
    sb: ModuleType,
    board: BoardTracker,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure(sb, monkeypatch, BOARD_CONFIG, {})
    missing = _issue(board)
    _no_status_field(board)

    assert _sync(sb, "--yes") == 0

    assert board.adds == [missing]


def test_where_the_state_degrades_a_dry_run_writes_nothing(
    sb: ModuleType,
    board: BoardTracker,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _configure(sb, monkeypatch, BOARD_CONFIG, {})
    missing = _issue(board)

    assert _sync(sb, "--dry-run") == 0

    assert board.adds == [] and board.edits == []
    out = capsys.readouterr().out
    assert f"The open issues with no card, to be added:\n  #{missing}\n" in out
    assert "[dry-run] nothing written." in out
    assert "would need a run at a terminal" not in out


def test_where_the_state_degrades_a_named_issue_whose_only_card_is_archived_is_listed(
    sb: ModuleType,
    board: BoardTracker,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _configure(sb, monkeypatch, BOARD_CONFIG, {})
    hidden = _issue(board)
    board.card(hidden, "Todo", archived=True)

    assert _sync(sb, "--yes", str(hidden)) == 0

    assert f"  #{hidden}: restore its card on the board to see it there" in capsys.readouterr().out


# --- what the run says after it (DEC-072 point 4) ---------------------------


def test_where_the_hooks_seed_a_board_field_it_names_the_back_fill(
    sb: ModuleType,
    board: BoardTracker,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    n = _a_board_out_of_step(board)
    monkeypatch.setattr(sb.hooks, "seeds_board_field", lambda root: True)

    assert _sync(sb, "--yes") == 0

    assert board.adds == [n["no_card"]]
    out = capsys.readouterr().out
    assert "`pkit pm back-fill` seeds it" in out
    assert "not only on the cards this run added (DEC-037 point 2)" in out


def test_the_help_says_where_it_writes_a_status_and_what_the_switch_does(
    sb: ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    saved = sys.argv
    sys.argv = ["sync-board.py", "--help"]
    try:
        with pytest.raises(SystemExit):
            sb.main()
    finally:
        sys.argv = saved
    text = " ".join(capsys.readouterr().out.split())
    assert "give each open issue with no card its card, wherever a board is configured" in text
    assert "a run with no terminal adds cards only with the project's switch" in text
    assert "this option is no consent to the board's own automation" in text
