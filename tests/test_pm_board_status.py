"""The board's Status kept as the projection of each issue's state (#2276).

DEC-006: "When a Projects v2 board exists, its Status field is a projection the
agent maintains. When the board and native primitives disagree, native wins."
`_lib/board_status` is where every writer writes it. These tests pin when it
applies (a board configured, and the state not carried on it), the option each
state takes, the reads it makes once per run, and that a write it cannot make
comes back as one line rather than an error.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from ruamel.yaml import YAML

from tests.pm_board_world import BOARD_CONFIG, LABEL_STATE, BoardTracker

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"
sys.path.insert(0, str(SCRIPTS))
from _lib import axis_labels, board_status  # noqa: E402

WORKFLOW = YAML(typ="safe").load(
    (SCRIPTS.parent / "schemas" / "workflow.yaml").read_text(encoding="utf-8")
)
LABEL_MAP = axis_labels.SubstrateMap(axes=LABEL_STATE)


@pytest.fixture
def board(monkeypatch: pytest.MonkeyPatch) -> BoardTracker:
    tracker = BoardTracker()

    def run(argv, *args, **kwargs):
        argv = [str(arg) for arg in argv]
        assert argv[0] == "gh", argv
        return tracker.gh(argv)

    monkeypatch.setattr(subprocess, "run", run)
    tracker.issues[7] = {"title": "t", "body": "", "state": "OPEN", "labels": [], "milestone": None}
    return tracker


# --- when the Status is a projection -----------------------------------------


@pytest.mark.parametrize(
    "substrate_map",
    [
        LABEL_MAP,
        None,  # no map: the kit's own labels carry the state (DEC-062 point 1)
        axis_labels.SubstrateMap(axes={"state": {"kit-label": True}}),
    ],
)
def test_the_status_is_kept_where_a_board_is_configured_and_does_not_carry_the_state(
    substrate_map,
) -> None:
    assert board_status.maintained(BOARD_CONFIG, substrate_map) is True


@pytest.mark.parametrize(
    ("config", "substrate_map"),
    [
        ({}, None),
        ({"has_projects_v2_board": True}, LABEL_MAP),  # a flag with no board number
        # The map binds state to the board: its Status is the source.
        (BOARD_CONFIG, axis_labels.SubstrateMap(axes={"state": {"board": True}})),
        # A present map leaves state out: the state degrades, and no Status is
        # written for it (DEC-062 point 5).
        (BOARD_CONFIG, axis_labels.SubstrateMap(axes={})),
        (BOARD_CONFIG, axis_labels.SubstrateMap(axes={"state": {"unsupported": True}})),
    ],
)
def test_the_status_is_not_kept_with_no_board_or_where_the_board_carries_the_state(
    config: dict, substrate_map
) -> None:
    assert board_status.maintained(config, substrate_map) is False


def test_each_state_takes_its_display_name_and_a_state_outside_the_five_takes_none() -> None:
    assert [board_status.option_name(WORKFLOW, s) for s in ("todo", "in-progress", "done")] == [
        "Todo",
        "In Progress",
        "Done",
    ]
    assert board_status.option_name(WORKFLOW, "open") is None


# --- the write ---------------------------------------------------------------


def test_a_write_sets_the_cards_status_and_reads_the_board_once_per_run(
    board: BoardTracker,
) -> None:
    board.card(7, "Todo")
    board.issues[8] = dict(board.issues[7])
    board.card(8)
    status = board_status.StatusBoard(BOARD_CONFIG, WORKFLOW)

    first = status.write(7, "in-progress")
    second = status.write(8, "backlog")

    assert first.ok and second.ok
    assert board.edits == [(7, "In Progress"), (8, "Backlog")]
    reads = [argv[2] for argv in board.board_calls() if argv[1] == "project"]
    assert reads.count("view") == 1 and reads.count("field-list") == 1
    assert first.line() == "[board] #7: Status set to 'In Progress'"


def test_a_write_given_the_card_looks_up_no_card(board: BoardTracker) -> None:
    board.card(7)
    status = board_status.StatusBoard(BOARD_CONFIG, WORKFLOW)

    assert status.write(7, "todo", item_id="PVTI_7").ok

    assert not [argv for argv in board.board_calls() if argv[1] != "project"]
    assert board.edits == [(7, "Todo")]


def test_a_write_given_the_issues_node_id_reads_no_issue(board: BoardTracker) -> None:
    board.card(7)
    status = board_status.StatusBoard(BOARD_CONFIG, WORKFLOW)

    assert status.write(7, "todo", issue_node_id="I_7").ok

    assert not [argv for argv in board.calls if argv[1:3] == ["issue", "view"]]
    assert board.edits == [(7, "Todo")]


@pytest.mark.parametrize(
    ("setup", "state", "says"),
    [
        ("no card", "review", "#7 has no card on board #4"),
        ("fields", "review", "missing required scopes [read:project]"),
        ("card", "review", "HTTP 502: Bad Gateway"),
        ("edit", "review", "gh project item-edit failed: HTTP 502: Bad Gateway"),
        ("no option", "review", "the board's Status field has no 'Review' option"),
        ("derived", "open", "the state 'open' has no Status option"),
    ],
)
def test_a_write_that_cannot_be_made_says_why_in_one_line(
    board: BoardTracker, setup: str, state: str, says: str
) -> None:
    if setup != "no card":
        board.card(7, "Todo")
    if setup in ("fields", "card"):
        board.fail_reads.add(setup)
    if setup == "edit":
        board.fail_edits.add(7)
    if setup == "no option":
        del board.options["Review"]

    written = board_status.StatusBoard(BOARD_CONFIG, WORKFLOW).write(7, state)

    assert not written.ok
    assert written.failure is not None and says in written.failure
    assert "\n" not in written.line()
    assert board.status(7) in (None, "Todo")


# --- the board's owner ---------------------------------------------------------
# A single-owner adopter whose board lives in the repository's owner omits
# `gh.default_owner` (the capability's README, the `gh:` block). The board is then
# found under the repository's owner, whether a person or an organisation owns it.
# A `gh project` read with no `--owner` would look among the boards of whoever
# runs `gh`, here someone else (`pm_board_world.VIEWER`).


def _owners(board: BoardTracker) -> set[str | None]:
    """The owner each read of the board named, None for a read that named none."""
    reads = [argv for argv in board.calls if argv[1:2] == ["project"] and argv[2] != "item-edit"]
    return {argv[argv.index("--owner") + 1] if "--owner" in argv else None for argv in reads}


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
    board: BoardTracker, repository: str, owner: str, default_owner: str | None
) -> None:
    board.repository, board.owner = repository, owner
    board.card(7, "Todo")
    config = (
        dict(BOARD_CONFIG, gh={"default_owner": default_owner}) if default_owner else BOARD_CONFIG
    )

    written = board_status.StatusBoard(config, WORKFLOW).write(7, "review")

    assert written.ok, written.failure
    assert board.edits == [(7, "Review")]
    assert _owners(board) == {owner}
    # The repository is read for its owner only where no field names the board's.
    reads = [argv for argv in board.calls if argv[1:3] == ["repo", "view"]]
    assert len(reads) == (0 if default_owner else 1)


def test_a_caller_that_holds_the_repositorys_owner_reads_no_repository(
    board: BoardTracker,
) -> None:
    board.card(7)

    assert (
        board_status.StatusBoard(BOARD_CONFIG, WORKFLOW, repository_owner="acme")
        .write(7, "todo")
        .ok
    )

    assert _owners(board) == {"acme"}
    assert not [argv for argv in board.calls if argv[1:3] == ["repo", "view"]]


# --- the Status field and its options ----------------------------------------


def test_the_options_the_status_lacks_are_named(board: BoardTracker) -> None:
    del board.options["Backlog"]
    del board.options["Review"]
    read = board_status.read_status_field(BOARD_CONFIG)

    assert read.field is not None
    assert board_status.missing_options(read.field, WORKFLOW) == ["Backlog", "Review"]


def test_a_board_with_no_status_field_says_which_fields_it_has(board: BoardTracker) -> None:
    board.field_name = "Stage"
    read = board_status.read_status_field(BOARD_CONFIG)

    assert read.field is None
    assert read.error == "the board has no `Status` field (its fields: Title, Stage)"


def test_a_status_field_that_is_no_single_select_is_named(board: BoardTracker) -> None:
    board.field_type = "ProjectV2Field"
    read = board_status.read_status_field(BOARD_CONFIG)

    assert read.field is None
    assert read.error == "the board's `Status` field is a ProjectV2Field, not a single-select"


# --- what the Status is to a project (DEC-062 point 5) -------------------------

ON_BOARD = axis_labels.SubstrateMap(axes={"state": {"board": True}})


@pytest.mark.parametrize(
    ("config", "substrate_map", "role"),
    [
        (BOARD_CONFIG, ON_BOARD, "source"),
        # The map binds state to the board; the board missing from the config is
        # a read that fails, never a projection (ADR-053 point 2).
        ({}, ON_BOARD, "source"),
        (BOARD_CONFIG, None, "projection"),
        (BOARD_CONFIG, LABEL_MAP, "projection"),
        (BOARD_CONFIG, axis_labels.SubstrateMap(axes={}), None),
        ({}, None, None),
    ],
)
def test_the_status_is_the_source_the_projection_or_nothing(config, substrate_map, role) -> None:
    assert board_status.role(config, substrate_map) == role


# --- reading a board-carried state (DEC-051 point 6) ---------------------------


def test_a_status_naming_an_open_state_places_the_issue(board: BoardTracker) -> None:
    board.card(7, "In Progress")

    read = board_status.StatusBoard(BOARD_CONFIG, WORKFLOW).read(7, issue_node_id="I_7")

    assert (read.outcome, read.state) == ("placed", "in-progress")
    assert read.finding(7) == ""


def test_the_read_asks_only_the_board_for_the_issue_whose_node_id_it_is_given(
    board: BoardTracker,
) -> None:
    """The issue's node id comes from the command's own read of the issue, so a
    failed issue read is never reported as a board that could not be read."""
    board.card(7, "Review")

    board_status.StatusBoard(BOARD_CONFIG, WORKFLOW).read(7, issue_node_id="I_7")

    assert not [argv for argv in board.calls if argv[1:3] == ["issue", "view"]]


@pytest.mark.parametrize("config", [{}, {"has_projects_v2_board": True}])
def test_with_no_board_configured_the_read_refuses_with_no_call(
    board: BoardTracker, config: dict
) -> None:
    """A map binding the state to the board under a configuration naming no board
    makes no `gh` call for the state (ADR-053 point 3), and names the missing
    board."""
    read = board_status.StatusBoard(config, WORKFLOW).read(7, issue_node_id="I_7")

    assert board.calls == []
    assert read.outcome == "unreadable"
    assert "no Projects v2 board configured" in read.finding(7)
    assert "#None" not in read.finding(7) + read.remedy(7)
    assert read.remedy(7) == "fix what is named above, then run this again"


@pytest.mark.parametrize(
    ("setup", "remedy"),
    [
        ("no field", "fix what is named above, then run this again"),
        ("no single-select", "fix what is named above, then run this again"),
        ("fields", "fix what `gh` said above, then run this again"),
    ],
)
def test_the_remedy_of_an_unreadable_status_points_at_what_named_the_fault(
    board: BoardTracker, setup: str, remedy: str
) -> None:
    """A board with no single-select Status answers, and the read names the
    field; a read `gh` refused carries what `gh` said."""
    board.card(7, "Todo")
    if setup == "no field":
        board.field_name = "Stage"
    elif setup == "no single-select":
        board.field_type = "ProjectV2Field"
    else:
        board.fail_reads.add("fields")

    read = board_status.StatusBoard(BOARD_CONFIG, WORKFLOW).read(7, issue_node_id="I_7")

    assert read.outcome == "unreadable"
    assert read.remedy(7) == remedy


@pytest.mark.parametrize(
    ("setup", "outcome", "says"),
    [
        ("fields", "unreadable", "the board's Status of #7 could not be read: missing required"),
        ("card", "unreadable", "could not be read: HTTP 502: Bad Gateway"),
        ("no card", "no-card", "#7 has no card on board #4"),
        ("unset", "unset", "#7's card on board #4 has no Status"),
        ("done", "not-open", "has the Status 'Done', which names no open state"),
        ("blocked", "not-open", "has the Status 'Blocked', which names no open state"),
    ],
)
def test_each_status_that_does_not_place_the_issue_is_its_own_outcome(
    board: BoardTracker, setup: str, outcome: str, says: str
) -> None:
    """Four outcomes, each its own message, none placing the issue: the board
    cannot be read, no card, no Status, a Status naming no open state."""
    board.options["Blocked"] = "opt-blocked"
    if setup != "no card":
        status = {"unset": None, "done": "Done", "blocked": "Blocked"}.get(setup, "Todo")
        board.card(7, status)
    if setup in ("fields", "card"):
        board.fail_reads.add(setup)

    read = board_status.StatusBoard(BOARD_CONFIG, WORKFLOW).read(7, issue_node_id="I_7")

    assert read.outcome == outcome
    assert read.state is None
    assert says in read.finding(7)
    assert board.edits == []


def test_an_option_is_read_back_to_its_state_whatever_its_case() -> None:
    assert board_status.state_of_option(WORKFLOW, "In Progress") == "in-progress"
    assert board_status.state_of_option(WORKFLOW, "in progress") == "in-progress"
    assert board_status.state_of_option(WORKFLOW, "Blocked") is None


def test_a_listing_reads_the_listed_issues_cards_and_no_others(board: BoardTracker) -> None:
    """One read of the cards of the issues listed, joined by node id; a card of an
    issue the listing does not name is never read (ADR-053 point 5)."""
    for number, status in ((7, "Backlog"), (8, None), (9, "Done"), (11, "Review")):
        board.issues[number] = dict(board.issues[7])
        board.card(number, status)
    board.issues[10] = dict(board.issues[7])

    listed, failure = board_status.read_listed(
        BOARD_CONFIG, WORKFLOW, ["I_7", "I_8", "I_9", "I_10"]
    )

    assert listed is not None and failure == ""
    assert (listed.read("I_7").outcome, listed.read("I_7").state) == ("placed", "backlog")
    assert listed.read("I_8").outcome == "unset"
    assert listed.read("I_9").outcome == "not-open"
    assert listed.read("I_10").outcome == "no-card"
    # An issue the listing did not read is no finding about its card.
    assert listed.read("I_11").outcome == "unreadable"
    assert listed.read(None).outcome == "unreadable"
    reads = [argv for argv in board.board_calls() if argv[1:3] == ["api", "graphql"]]
    assert len(reads) == 1
    assert "items(first" not in " ".join(reads[0])


def test_a_listing_with_no_issues_reads_no_board(board: BoardTracker) -> None:
    listed, failure = board_status.read_listed(BOARD_CONFIG, WORKFLOW, [])

    assert listed is not None and failure == ""
    assert board.calls == []


@pytest.mark.parametrize(("fails", "says"), [("card", "HTTP 502"), ("fields", "read:project")])
def test_a_listing_of_a_board_that_cannot_be_read_is_none_and_says_why(
    board: BoardTracker, fails: str, says: str
) -> None:
    board.card(7, "Todo")
    board.fail_reads.add(fails)

    listed, failure = board_status.read_listed(BOARD_CONFIG, WORKFLOW, ["I_7"])

    assert listed is None
    assert says in failure
