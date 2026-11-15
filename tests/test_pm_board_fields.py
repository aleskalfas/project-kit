"""Tests for the Projects-v2 board READ seam (`_lib/board_fields`, #724).

The seam is what makes `set-field --priority High` writable on a board-carried
axis: it turns the names an adopter already speaks (board number, `Priority`,
`High`) into the four ids a field-value write needs. These tests pin

  * the argv each read issues (host/owner threading is the `gh` helper's job; the
    seam must ask for the right thing),
  * name → id matching, including the case-insensitive fallback,
  * the failure contract: `ok=False` with the service's words verbatim (the
    missing `read:project` scope is the likeliest board failure and its remedy
    is in that text), and the way out,
  * what counts as the board's answer ([pkit:ADR-096] point 1): an answer that
    names the configured board, and an absence only where a witness in the same
    request shows the board answered, and
  * the membership case — a card lookup the board answered that found no card
    is `ok=True, item_id=None`, distinct from a failed read.

Every `gh` invocation is a fake runner; nothing here touches a network.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

from tests.pm_board_archive import reads_archived
from tests.pm_board_graphql import GraphBoard, done, flag_value, flag_values, query_of

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"
MODULE_PATH = SCRIPTS / "_lib" / "board_fields.py"


@pytest.fixture(scope="module")
def bf():
    # `_lib` on the import path for this module's tests alone: left there, it outlived
    # them, and a later load took copies of its modules by path from it (#2353).
    lib = str(SCRIPTS / "_lib")
    added = lib not in sys.path
    if added:
        sys.path.insert(0, lib)
    spec = importlib.util.spec_from_file_location("pm_board_fields_under_test", MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["pm_board_fields_under_test"] = module
    spec.loader.exec_module(module)
    yield module
    if added:
        sys.path.remove(lib)


BOARD_CONFIG = {
    "has_projects_v2_board": True,
    "projects_v2_board_id": 7,
    "gh": {"default_owner": "an-org"},
}

FIELD_LIST_PAYLOAD = {
    "fields": [
        {"id": "PVTF_title", "name": "Title", "type": "ProjectV2Field"},
        {
            "id": "PVTSSF_priority",
            "name": "Priority",
            "type": "ProjectV2SingleSelectField",
            "options": [
                {"id": "opt_high", "name": "High"},
                {"id": "opt_low", "name": "Low"},
            ],
        },
    ]
}


def _runner(stdout: str = "{}", *, returncode: int = 0, stderr: str = "", calls=None):
    """A fake gh runner recording each argv it is handed."""

    def run(args, config, *, fallback_owner=None, check=False):
        if calls is not None:
            calls.append({"args": list(args), "fallback_owner": fallback_owner})
        return subprocess.CompletedProcess(args, returncode, stdout=stdout, stderr=stderr)

    return run


# --- config readers ---------------------------------------------------------


def test_board_number_reads_the_configured_number(bf) -> None:
    assert bf.board_number(BOARD_CONFIG) == "7"


def test_board_number_none_without_the_flag(bf) -> None:
    assert bf.board_number({"projects_v2_board_id": 7}) is None


def test_board_number_none_without_the_id(bf) -> None:
    assert bf.board_number({"has_projects_v2_board": True}) is None


def test_default_owner_reads_the_gh_block(bf) -> None:
    assert bf.default_owner(BOARD_CONFIG) == "an-org"
    assert bf.default_owner({}) is None


# --- the board's owner ------------------------------------------------------
# A single-owner adopter whose board lives in the repository's owner omits
# `gh.default_owner` (the capability's README, the `gh:` block). The board is
# then the repository's owner's, a person's or an organisation's.


def test_board_owner_is_the_default_owner_where_one_is_configured(bf) -> None:
    calls: list = []
    owner = bf.board_owner(BOARD_CONFIG, repository_owner="acme", gh_call=_runner(calls=calls))
    assert owner == "an-org"
    assert calls == []


def test_board_owner_is_the_repositorys_owner_the_caller_holds(bf) -> None:
    calls: list = []
    assert bf.board_owner({}, repository_owner="acme", gh_call=_runner(calls=calls)) == "acme"
    assert calls == []


def test_board_owner_reads_the_repositorys_owner_where_the_caller_holds_none(bf) -> None:
    calls: list = []
    payload = json.dumps({"nameWithOwner": "acme/repo"})
    assert bf.board_owner({}, gh_call=_runner(payload, calls=calls)) == "acme"
    assert [call["args"] for call in calls] == [["gh", "repo", "view", "--json", "nameWithOwner"]]


def test_board_owner_is_none_where_the_repository_cannot_be_read(bf) -> None:
    failed = _runner(returncode=1, stderr="not a git repository")
    assert bf.board_owner({}, gh_call=failed) is None
    assert bf.board_owner({}, gh_call=_runner(json.dumps({"nameWithOwner": ""}))) is None


@pytest.mark.parametrize(
    ("url", "owner"),
    [
        ("https://github.com/acme/repo/issues/42", "acme"),
        ("https://github.example.com/alice/repo/issues/1", "alice"),
        ("u", None),
        ("", None),
        (None, None),
    ],
)
def test_url_owner_reads_the_owner_a_url_names(bf, url, owner) -> None:
    assert bf.url_owner(url) == owner


# --- the board, answering the seam's GraphQL reads ----------------------------

#: The repository the issues of these tests lie in, by its node id.
REPOSITORY = "R_repo"
#: An issue of the same repository with a card on the board: the witness that
#: the credential's reads see the board ([pkit:ADR-096] point 1).
WITNESS = "I_witness"


class _Board(GraphBoard):
    """Board #7 of `an-org`, node `PVT_1`, as a test sets it.

    ``cards`` maps an issue's node id to its own cards on every board, each as
    `(item id, board node, option)`, the option `(id, name)` or None. Every
    issue lies in :data:`REPOSITORY`, whose page of recent issues holds the
    witness unless ``witness`` is False. ``more`` names the issues whose own
    cards run past the page their read takes."""

    def __init__(
        self,
        *,
        fields: list[dict] | None = None,
        cards: dict[str, list[tuple[str, str, tuple[str, str] | None]]] | None = None,
        witness: bool = True,
        more: tuple[str, ...] = (),
    ) -> None:
        super().__init__(node="PVT_1", number=7, owner="an-org")
        self._fields_held = list(fields or [])
        self.cards = dict(cards or {})
        self.witness = witness
        self.more = set(more)

    def fields(self) -> list[dict]:
        return self._fields_held

    def own_cards(self, issue_id: str, value_field: str | None) -> list[dict] | None:
        if issue_id == WITNESS:
            return [{"id": "PVTI_witness", "project": {"id": self.node}}]
        if issue_id not in self.cards:
            return None
        return [
            {
                "id": item_id,
                "project": {"id": project_id},
                "fieldValueByName": (
                    {"optionId": option[0], "name": option[1]} if option and value_field else None
                ),
            }
            for item_id, project_id, option in self.cards[issue_id]
        ]

    def more_cards(self, issue_id: str) -> bool:
        return issue_id in self.more

    def repository_of(self, issue_id: str) -> str | None:
        return REPOSITORY

    def recent_issues(self, repository_id: str, order: str) -> list[str]:
        return [WITNESS] if self.witness and order == "created" else []


def _graph_runner(board: GraphBoard, *, calls: list | None = None, fail_at: int | None = None):
    """A fake `gh` whose GraphQL reads the board answers. `fail_at` is the read,
    counted from 0, that fails whole with `HTTP 502`."""

    def run(args, config, *, fallback_owner=None, check=False):
        if calls is not None:
            calls.append(list(args))
        if fail_at is not None and len(board.graph_calls) == fail_at:
            board.graph_calls.append(list(args))
            return done(args, 1, stderr="HTTP 502")
        return board.reply(args)

    return run


# --- project node id --------------------------------------------------------


def _identity(node: str = "PVT_board7", number: int = 7, owner: str = "an-org") -> str:
    """The board's own answer to `gh project view --format json`: its names."""
    return json.dumps({"id": node, "number": number, "owner": {"login": owner}})


def test_read_project_node_id_resolves_the_board_number(bf) -> None:
    calls: list = []
    lookup = bf.read_project_node_id(
        BOARD_CONFIG, owner="an-org", gh_call=_runner(_identity(), calls=calls)
    )
    assert lookup.ok is True and lookup.node_id == "PVT_board7"
    assert calls[0]["args"] == ["gh", "project", "view", "7", "--format", "json"]
    assert calls[0]["fallback_owner"] == "an-org"


@pytest.mark.parametrize(
    ("answer", "config", "says"),
    [
        pytest.param(
            json.dumps({"id": "PVT_board7"}), BOARD_CONFIG, "names board #None", id="no-number"
        ),
        pytest.param(
            _identity(number=8), BOARD_CONFIG, "names board #8, not #7", id="another-number"
        ),
        pytest.param(
            _identity(owner="someone"),
            BOARD_CONFIG,
            "a board of someone, not of an-org",
            id="another-owner",
        ),
        pytest.param(
            _identity(),
            {**BOARD_CONFIG, "projects_v2_node_id": "PVT_stored"},
            "the board PVT_board7, not PVT_stored",
            id="another-node",
        ),
    ],
)
def test_read_project_node_id_counts_only_an_answer_naming_the_configured_board(
    bf, answer, config, says
) -> None:
    """A stored node is a name the answer must agree with, never the answer
    ([pkit:ADR-096] point 1)."""
    lookup = bf.read_project_node_id(config, gh_call=_runner(answer))
    assert lookup.ok is False and lookup.node_id is None and lookup.named is True
    assert says in (lookup.error or "")


def test_read_project_node_id_refuses_without_a_configured_board(bf) -> None:
    lookup = bf.read_project_node_id({}, gh_call=_runner())
    assert lookup.ok is False
    assert "has_projects_v2_board" in (lookup.error or "")


def test_read_project_node_id_gives_the_services_words(bf) -> None:
    stderr = "error: could not resolve to a ProjectV2 with the number 7"
    lookup = bf.read_project_node_id(BOARD_CONFIG, gh_call=_runner(returncode=1, stderr=stderr))
    assert lookup.ok is False and stderr in (lookup.error or "")
    assert lookup.named is False


def test_resolve_project_node_id_is_the_lossy_form(bf) -> None:
    assert bf.resolve_project_node_id(BOARD_CONFIG, gh_call=_runner(_identity())) == "PVT_board7"
    assert bf.resolve_project_node_id(BOARD_CONFIG, gh_call=_runner(returncode=1)) is None


# --- field list + options ---------------------------------------------------


def test_read_fields_returns_fields_with_their_options(bf) -> None:
    board = _Board(fields=FIELD_LIST_PAYLOAD["fields"])
    read = bf.read_fields(BOARD_CONFIG, gh_call=_graph_runner(board))
    assert read.ok is True and read.project_id == "PVT_1"
    assert bf.field_names(read.fields) == ["Title", "Priority"]
    assert [o["name"] for o in read.fields[1]["options"]] == ["High", "Low"]
    [argv] = board.graph_calls
    assert "repositoryOwner(login: $owner)" in query_of(argv)
    assert (flag_value(argv, "owner"), flag_value(argv, "number")) == ("an-org", "7")


def test_read_fields_addresses_a_stored_node_and_counts_it_only_where_the_board_names_it(
    bf,
) -> None:
    board = _Board(fields=FIELD_LIST_PAYLOAD["fields"])
    stored = bf.read_fields(
        {**BOARD_CONFIG, "projects_v2_node_id": "PVT_1"}, gh_call=_graph_runner(board)
    )
    assert stored.ok is True and flag_value(board.graph_calls[0], "board") == "PVT_1"
    stale = bf.read_fields(
        {**BOARD_CONFIG, "projects_v2_node_id": "PVT_stale"}, gh_call=_graph_runner(board)
    )
    assert stale.ok is False and stale.fields == ()
    assert "PVT_stale" in (stale.error or "")


def test_read_fields_surfaces_a_missing_scope_in_the_services_words(bf) -> None:
    stderr = (
        "error: your authentication token is missing required scopes "
        "[read:project]. To request it, run: gh auth refresh -s read:project"
    )
    board = _Board()
    board.failing["fields"] = stderr
    read = bf.read_fields(BOARD_CONFIG, gh_call=_graph_runner(board))
    assert read.ok is False and stderr in (read.error or "")


def test_read_fields_reports_non_json_output(bf) -> None:
    read = bf.read_fields(BOARD_CONFIG, gh_call=_runner("not json"))
    assert read.ok is False and "returned no data" in (read.error or "")


def test_read_fields_missing_gh_binary_is_a_failure_not_a_crash(bf) -> None:
    def boom(args, config, *, fallback_owner=None, check=False):
        raise FileNotFoundError

    read = bf.read_fields(BOARD_CONFIG, gh_call=boom)
    assert read.ok is False and "not on PATH" in (read.error or "")


# --- name → id matching -----------------------------------------------------


def test_find_field_matches_exactly_then_case_insensitively(bf) -> None:
    fields = ({"name": "priority", "id": "lower"}, {"name": "Priority", "id": "exact"})
    assert bf.find_field(fields, "Priority")["id"] == "exact"
    assert bf.find_field(fields, "PRIORITY")["id"] == "lower"  # first case-insensitive hit
    assert bf.find_field(fields, "Workstream") is None


def test_is_single_select_discriminates_the_supported_kind(bf) -> None:
    assert bf.is_single_select({"type": "ProjectV2SingleSelectField"}) is True
    assert bf.is_single_select({"type": "ProjectV2Field"}) is False
    assert bf.is_single_select({"type": "ProjectV2IterationField"}) is False
    assert bf.field_type({}) == "<unknown>"


def test_option_id_matches_exactly_then_case_insensitively(bf) -> None:
    field = FIELD_LIST_PAYLOAD["fields"][1]
    assert bf.option_id(field, "High") == "opt_high"
    assert bf.option_id(field, "hIgH") == "opt_high"
    assert bf.option_id(field, "Medium") is None


def test_option_id_prefers_an_exact_match_over_an_earlier_case_variant(bf) -> None:
    field = {"options": [{"id": "loose", "name": "high"}, {"id": "exact", "name": "High"}]}
    assert bf.option_id(field, "High") == "exact"


def test_option_names_lists_what_the_field_offers(bf) -> None:
    assert bf.option_names(FIELD_LIST_PAYLOAD["fields"][1]) == ["High", "Low"]
    assert bf.option_names({"type": "ProjectV2Field"}) == []


# --- the card (item) lookup -------------------------------------------------


def test_resolve_item_id_finds_the_card_on_the_right_board(bf) -> None:
    board = _Board(
        cards={"I_issue42": [("PVTI_other", "PVT_other", None), ("PVTI_card42", "PVT_1", None)]}
    )
    lookup = bf.resolve_item_id(
        BOARD_CONFIG,
        issue_node_id="I_issue42",
        project_node_id="PVT_1",
        gh_call=_graph_runner(board),
    )
    assert lookup.ok is True and lookup.item_id == "PVTI_card42"
    [argv] = board.graph_calls
    assert flag_values(argv, "ids[]") == ["I_issue42"]
    assert flag_value(argv, "board") == "PVT_1"


def test_resolve_item_id_reports_the_membership_case_as_no_card(bf) -> None:
    """A read that found no card on THIS board, a witness showing the board
    answered: `ok=True, item_id=None` — the caller refuses with a remediation
    rather than treating it as a read error."""
    board = _Board(cards={"I_issue42": [("PVTI_other", "PVT_other", None)]})
    lookup = bf.resolve_item_id(
        BOARD_CONFIG,
        issue_node_id="I_issue42",
        project_node_id="PVT_1",
        gh_call=_graph_runner(board),
    )
    assert lookup.ok is True and lookup.item_id is None


def test_resolve_item_id_tells_no_absence_without_a_witness(bf) -> None:
    """An issue's own cards list only what the credential may see, so with no
    issue of the repository showing a card on the board, an absence is no
    answer ([pkit:ADR-096] point 1)."""
    board = _Board(cards={"I_issue42": []}, witness=False)
    lookup = bf.resolve_item_id(
        BOARD_CONFIG,
        issue_node_id="I_issue42",
        project_node_id="PVT_1",
        gh_call=_graph_runner(board),
    )
    assert lookup.ok is False and lookup.item_id is None and lookup.named is True
    assert "no issue this read saw from the repository shows a card" in (lookup.error or "")


def test_resolve_item_id_surfaces_a_scope_failure_in_the_services_words(bf) -> None:
    stderr = (
        "your token has not been granted the required scopes to execute this query. "
        "missing: 'read:project'"
    )
    board = _Board(cards={"I_issue42": []})
    board.failing["cards"] = stderr
    lookup = bf.resolve_item_id(
        BOARD_CONFIG,
        issue_node_id="I_issue42",
        project_node_id="PVT_1",
        gh_call=_graph_runner(board),
    )
    assert lookup.ok is False and stderr in (lookup.error or "")
    assert lookup.item_id is None


def test_resolve_item_id_includes_archived_cards_in_the_query(bf) -> None:
    """An archived card still has field values worth writing; reporting it as "not on
    the board" would send the adopter to add a duplicate."""
    board = _Board(cards={"I_issue42": []})
    bf.resolve_item_id(
        BOARD_CONFIG,
        issue_node_id="I_issue42",
        project_node_id="PVT_1",
        gh_call=_graph_runner(board),
    )
    assert "includeArchived: true" in query_of(board.graph_calls[0])


# --- the workstream mutators' reads (#1940) ----------------------------------


def _card(item_id: str, number: int | None, option_id: str | None) -> dict:
    value = {"optionId": option_id} if option_id else None
    content = {"number": number, "title": f"Issue {number}"} if number else {"title": "draft"}
    return {"id": item_id, "content": content, "fieldValueByName": value}


def _page(cards: list[dict], *, next_cursor: str | None = None) -> str:
    """One page of a walk of board #7's cards, under the board's own answer."""
    return json.dumps(
        {
            "data": {
                "board": {
                    "id": "PVT_1",
                    "number": 7,
                    "owner": {"login": "an-org"},
                    "items": {
                        "pageInfo": {"hasNextPage": bool(next_cursor), "endCursor": next_cursor},
                        "nodes": cards,
                    },
                }
            }
        }
    )


def test_read_items_with_option_keeps_the_cards_of_that_option_across_pages(bf) -> None:
    pages = [
        _page([_card("I1", 1, "opt_cli"), _card("I2", 2, "opt_docs")], next_cursor="c1"),
        _page([_card("I3", None, "opt_cli"), _card("I4", 4, None)]),
    ]
    calls: list = []

    def run(args, config, *, fallback_owner=None, check=False):
        calls.append(list(args))
        return subprocess.CompletedProcess(args, 0, stdout=pages[len(calls) - 1], stderr="")

    read = bf.read_items_with_option(
        BOARD_CONFIG,
        project_node_id="PVT_1",
        field_name="Workstream",
        option_id="opt_cli",
        gh_call=run,
    )
    assert read.ok is True
    assert [(i.item_id, i.number) for i in read.items] == [("I1", 1), ("I3", None)]
    # The second page asks for the cards after the first page's cursor.
    assert "after=c1" in calls[1]
    assert "field=Workstream" in calls[0]


def test_read_items_with_option_leaves_a_state_issues_card_out(bf) -> None:
    """A state issue holds no work, so the board's read leaves its card out by
    its marker (DEC-058 point 3, ADR-071 point 6)."""
    state = _card("I9", 9, "opt_cli")
    state["content"]["body"] = "<!-- pkit:state-issue v=1 kind=seat key=planner -->\n"
    work = _card("I1", 1, "opt_cli")
    work["content"]["body"] = "## What\n\nwork\n"
    calls: list = []
    read = bf.read_items_with_option(
        BOARD_CONFIG,
        project_node_id="PVT_1",
        field_name="Workstream",
        option_id="opt_cli",
        gh_call=_runner(_page([state, work]), calls=calls),
    )
    assert [i.number for i in read.items] == [1]
    assert "number title body" in " ".join(calls[0]["args"])


def test_read_items_with_option_fails_rather_than_counting_in_part(bf) -> None:
    read = bf.read_items_with_option(
        BOARD_CONFIG,
        project_node_id="PVT_1",
        field_name="Workstream",
        option_id="opt_cli",
        gh_call=_runner(returncode=1, stderr="boom"),
    )
    assert read.ok is False
    assert "boom" in (read.error or "")


# --- every card, with its value (#2276) ---------------------------------------


def _issue_card(
    item_id: str,
    number: int,
    *,
    option: tuple[str, str] | None = None,
    repository: str = "acme/repo",
    state: str = "OPEN",
    body: str = "## What\n\nwork\n",
) -> dict:
    value = {"optionId": option[0], "name": option[1]} if option else None
    content = {
        "__typename": "Issue",
        "number": number,
        "title": f"Issue {number}",
        "body": body,
        "state": state,
        "repository": {"nameWithOwner": repository},
    }
    return {"id": item_id, "content": content, "fieldValueByName": value}


def test_read_items_returns_every_card_with_its_value_across_pages(bf) -> None:
    """The board's whole Status, card by card: what `sync-board` compares with each
    issue's state. Each card says what it holds — an issue, a pull request or a
    draft — the issue's repository and whether it is closed, and the option it
    holds, or none."""
    pull = {
        "id": "I5",
        "content": {"__typename": "PullRequest", "number": 5, "title": "A PR"},
        "fieldValueByName": None,
    }
    draft = {"id": "I6", "content": {"__typename": "DraftIssue", "title": "draft"}}
    pages = [
        _page(
            [_issue_card("I1", 1, option=("opt_todo", "Todo")), _issue_card("I2", 2)],
            next_cursor="c1",
        ),
        _page([_issue_card("I3", 3, repository="acme/other", state="CLOSED"), pull, draft]),
    ]
    calls: list = []

    def run(args, config, *, fallback_owner=None, check=False):
        calls.append(list(args))
        return subprocess.CompletedProcess(args, 0, stdout=pages[len(calls) - 1], stderr="")

    read = bf.read_items(BOARD_CONFIG, project_node_id="PVT_1", field_name="Status", gh_call=run)

    assert read.ok is True
    assert [(i.item_id, i.number, i.kind, i.repository, i.closed) for i in read.items] == [
        ("I1", 1, "Issue", "acme/repo", False),
        ("I2", 2, "Issue", "acme/repo", False),
        ("I3", 3, "Issue", "acme/other", True),
        ("I5", 5, "PullRequest", "", False),
        ("I6", None, "DraftIssue", "", False),
    ]
    assert [(i.option_id, i.option_name) for i in read.items[:2]] == [
        ("opt_todo", "Todo"),
        (None, None),
    ]
    assert "field=Status" in calls[0] and "after=c1" in calls[1]


def test_read_items_leaves_a_state_issues_card_out(bf) -> None:
    state = _issue_card("I9", 9, body="<!-- pkit:state-issue v=1 kind=seat key=planner -->\n")
    read = bf.read_items(
        BOARD_CONFIG,
        project_node_id="PVT_1",
        field_name="Status",
        gh_call=_runner(_page([state, _issue_card("I1", 1)])),
    )
    assert [i.number for i in read.items] == [1]
    assert [i.number for i in read.set_aside] == [9]


def _withheld(item_id: str, option: str | None = None, *, value_read: bool = True) -> dict:
    """A card whose issue lies in a repository the credential may not read."""
    card: dict = {"id": item_id, "type": "REDACTED", "content": None}
    if value_read:
        card["fieldValueByName"] = {"optionId": option, "name": "x"} if option else {}
    return card


def test_a_withheld_card_is_kept_apart_from_the_cards_counted(bf) -> None:
    """The board returns a card whose issue the credential may not read with
    nothing of its issue: it is withheld, never counted ([pkit:ADR-096] point 2)."""
    read = bf.read_items(
        BOARD_CONFIG,
        project_node_id="PVT_1",
        field_name="Status",
        gh_call=_runner(_page([_withheld("W1"), _issue_card("I1", 1)])),
    )
    assert read.ok is True
    assert [i.item_id for i in read.items] == ["I1"]
    assert [(i.item_id, i.withheld) for i in read.withheld] == [("W1", True)]


def test_a_withheld_card_that_may_hold_the_option_is_named_with_it(bf) -> None:
    """A withheld card holding the option, or whose value the board did not
    return, may hold it; one holding another option does not."""
    cards = [
        _withheld("W_cli", "opt_cli"),
        _withheld("W_docs", "opt_docs"),
        _withheld("W_unread", value_read=False),
    ]
    read = bf.read_items_with_option(
        BOARD_CONFIG,
        project_node_id="PVT_1",
        field_name="Workstream",
        option_id="opt_cli",
        gh_call=_runner(_page(cards)),
    )
    assert [i.item_id for i in read.withheld] == ["W_cli", "W_unread"]


def test_a_walk_counts_only_an_answer_naming_the_configured_board(bf) -> None:
    """A page whose board's own answer names another board answers nothing."""
    page = json.loads(_page([_issue_card("I1", 1)]))
    page["data"]["board"]["number"] = 8
    read = bf.read_items(
        BOARD_CONFIG,
        project_node_id="PVT_1",
        field_name="Status",
        gh_call=_runner(json.dumps(page)),
    )
    assert read.ok is False and read.items == ()
    assert "names board #8, not #7" in (read.error or "")


def test_read_items_surfaces_stderr_verbatim(bf) -> None:
    read = bf.read_items(
        BOARD_CONFIG,
        project_node_id="PVT_1",
        field_name="Status",
        gh_call=_runner(returncode=1, stderr="missing: 'read:project'"),
    )
    assert read.ok is False and "missing: 'read:project'" in (read.error or "")


def test_read_items_names_the_issue_each_card_holds_by_its_node_id(bf) -> None:
    """A listing of issues is joined to its cards by the issue's node id (#2271);
    a card holding no issue names none."""
    card = _issue_card("I1", 1)
    card["content"]["id"] = "I_kwDO1"
    pull = {"id": "I5", "content": {"__typename": "PullRequest", "id": "PR_x", "number": 5}}
    read = bf.read_items(
        BOARD_CONFIG,
        project_node_id="PVT_1",
        field_name="Status",
        gh_call=_runner(_page([card, pull])),
    )
    assert [i.issue_id for i in read.items] == ["I_kwDO1", ""]


def test_read_items_reads_an_archived_card_as_any_other(bf) -> None:
    """The board gives a walk its archived cards only where the walk asks for them
    (#3191), so the walk asks, and an archived card is read with the others."""
    archived = _issue_card("I2", 2, option=("opt_cli", "cli"))

    def run(args, config, *, fallback_owner=None, check=False):
        query = next(arg for arg in args if arg.startswith("query="))
        cards = [_issue_card("I1", 1)] + ([archived] if reads_archived(query) else [])
        return subprocess.CompletedProcess(args, 0, stdout=_page(cards), stderr="")

    read = bf.read_items(
        BOARD_CONFIG, project_node_id="PVT_1", field_name="Workstream", gh_call=run
    )
    assert [i.item_id for i in read.items] == ["I1", "I2"]
    with_option = bf.read_items_with_option(
        BOARD_CONFIG,
        project_node_id="PVT_1",
        field_name="Workstream",
        option_id="opt_cli",
        gh_call=run,
    )
    assert [i.item_id for i in with_option.items] == ["I2"]


# --- one issue's card, and the option it holds (#2271) --------------------------


def _read_value(bf, board: _Board, issue: str = "I_1"):
    return bf.read_item_value(
        BOARD_CONFIG,
        issue_node_id=issue,
        project_node_id="PVT_1",
        field_name="Status",
        gh_call=_graph_runner(board),
    )


def test_read_item_value_reads_the_option_the_issues_card_holds(bf) -> None:
    board = _Board(
        cards={
            "I_1": [
                ("PVTI_other", "PVT_2", ("opt_x", "Done")),
                ("PVTI_1", "PVT_1", ("opt_ip", "In Progress")),
            ]
        }
    )
    read = _read_value(bf, board)
    assert (read.ok, read.item_id, read.option_id, read.option_name) == (
        True,
        "PVTI_1",
        "opt_ip",
        "In Progress",
    )
    [argv] = board.graph_calls
    assert flag_value(argv, "field") == "Status" and flag_values(argv, "ids[]") == ["I_1"]


def test_read_item_value_keeps_no_card_unset_and_unread_apart(bf) -> None:
    """Three answers the caller tells apart (ADR-053 point 5): no card on this
    board, a witness showing it, a card whose field is unset, and a read that
    failed."""
    no_card = _read_value(bf, _Board(cards={"I_1": [("PVTI_other", "PVT_2", None)]}))
    unset = _read_value(bf, _Board(cards={"I_1": [("PVTI_1", "PVT_1", None)]}))
    failing = _Board(cards={"I_1": []})
    failing.failing["cards"] = "missing: 'read:project'"
    unread = _read_value(bf, failing)
    assert (no_card.ok, no_card.item_id) == (True, None)
    assert (unset.ok, unset.item_id, unset.option_name) == (True, "PVTI_1", None)
    assert unread.ok is False and "missing: 'read:project'" in (unread.error or "")


def test_read_item_value_refuses_a_payload_with_no_cards(bf) -> None:
    read = bf.read_item_value(
        BOARD_CONFIG,
        issue_node_id="I_1",
        project_node_id="PVT_1",
        field_name="Status",
        gh_call=_runner("{}"),
    )
    assert read.ok is False


def test_an_archived_card_still_places_its_issue(bf) -> None:
    """Both reads ask for the issue's archived cards, so an archived card is the
    issue's card on the board, for one issue and for many (ADR-053 point 5)."""
    board = _Board(cards={"I_1": []})
    _read_value(bf, board)
    query = query_of(board.graph_calls[0])
    assert "includeArchived: true" in query
    assert "items(first" not in query


@pytest.mark.parametrize("read", ["one", "listing"])
def test_cards_past_one_page_without_the_boards_card_are_a_failed_read(bf, read) -> None:
    """An issue on more boards than one page holds, whose card on this board is
    not among them, is never taken for an issue with no card."""
    board = _Board(cards={"I_1": [("PVTI_x", "PVT_9", None)]}, more=("I_1",))
    if read == "one":
        result = _read_value(bf, board)
    else:
        result = bf.read_issue_cards(
            BOARD_CONFIG,
            issue_node_ids=["I_1"],
            project_node_id="PVT_1",
            field_name="Status",
            gh_call=_graph_runner(board),
        )
    assert result.ok is False
    assert result.error is not None and "more than 100 boards" in result.error


def test_the_boards_card_on_a_first_page_with_more_to_follow_is_read(bf) -> None:
    board = _Board(cards={"I_1": [("PVTI_1", "PVT_1", ("o", "Todo"))]}, more=("I_1",))
    read = _read_value(bf, board)
    assert (read.ok, read.item_id, read.option_name) == (True, "PVTI_1", "Todo")


# --- the listed issues' cards, in batches (#2271) --------------------------------


def _listed_board(count: int, *, null: str | None = None) -> _Board:
    """Issues `I_1` to `I_<count>`: each even one has a card on the board whose
    Status is `S<n>`, each odd one none, and `null` names no issue."""
    cards: dict[str, list[tuple[str, str, tuple[str, str] | None]]] = {}
    for n in range(1, count + 1):
        issue = f"I_{n}"
        if issue == null:
            continue
        cards[issue] = [(f"PVTI_{n}", "PVT_1", (f"o{n}", f"S{n}"))] if n % 2 == 0 else []
    return _Board(cards=cards)


def test_the_listed_issues_cards_are_read_in_batches_of_a_hundred(bf) -> None:
    board = _listed_board(150)
    ids = [f"I_{n}" for n in range(1, 151)]

    read = bf.read_issue_cards(
        BOARD_CONFIG,
        issue_node_ids=ids,
        project_node_id="PVT_1",
        field_name="Status",
        gh_call=_graph_runner(board),
    )

    assert read.ok
    assert [len(flag_values(argv, "ids[]")) for argv in board.graph_calls] == [100, 50]
    assert set(read.cards) == set(ids)
    assert (read.cards["I_4"].item_id, read.cards["I_4"].option_name) == ("PVTI_4", "S4")
    assert (read.cards["I_3"].ok, read.cards["I_3"].item_id) == (True, None)
    query = query_of(board.graph_calls[0])
    assert "nodes(ids: $ids)" in query and "includeArchived: true" in query


def test_a_listing_with_no_issues_reads_nothing(bf) -> None:
    board = _listed_board(0)
    read = bf.read_issue_cards(
        BOARD_CONFIG,
        issue_node_ids=[],
        project_node_id="PVT_1",
        field_name="Status",
        gh_call=_graph_runner(board),
    )
    assert read.ok and dict(read.cards) == {} and board.graph_calls == []


@pytest.mark.parametrize(
    ("fail_at", "null", "says"),
    [
        (1, None, "HTTP 502"),
        (None, "I_120", "the issue I_120 could not be read"),
    ],
)
def test_a_failed_batch_or_a_null_node_fails_the_whole_listing(bf, fail_at, null, says) -> None:
    """Whole or nothing: the issues of a failed batch are never taken for issues
    with no card, and neither is an id GitHub resolves to no issue."""
    board = _listed_board(150, null=null)
    read = bf.read_issue_cards(
        BOARD_CONFIG,
        issue_node_ids=[f"I_{n}" for n in range(1, 151)],
        project_node_id="PVT_1",
        field_name="Status",
        gh_call=_graph_runner(board, fail_at=fail_at),
    )
    assert read.ok is False and dict(read.cards) == {}
    assert read.error is not None and says in read.error
