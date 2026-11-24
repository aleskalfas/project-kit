"""The Projects-v2 board READ seam — every read of the board, and name → id resolution.

A field-value write (`_lib/substrate_writes.write_field_value`, ADR-031) needs
four **ids**: the project node id, the item (card) id for the issue, the field id,
and — for a single-select — the option id. An adopter's `project/config.yaml`
declares none of them: it carries the board *number* (`projects_v2_board_id`) and
an optional node id (`projects_v2_node_id`). This module resolves the ids from the
**names the adopter already speaks** (the board number in config, the Title-cased
axis name on the board, the classification value), and it is the single home for
every read of the board ([pkit:ADR-053] point 1): its identity, its fields, its
cards, and an issue's own cards on it. `back-fill`, `adopt-existing`,
`bootstrap`, `pre-check`, `create-issue`, `set-field`, `sync-board`,
`validate-issue` and the workstream commands read the board here, and a scan of
the scripts holds that no script outside the seam builds a read of it
([pkit:ADR-096] point 6).

What counts as the board's answer
---------------------------------
[pkit:ADR-096], under every credential alike, through `_lib/board_answer`, the
part of the seam that builds each request and judges its answer:

* **A read of the board itself answered** only where its answer names the
  configured board, agreeing with each of its names: its number, its owner as
  :func:`board_owner` resolves it, and its node where one is stored. An error, an
  answer with no board in it, or one naming another board, is a board that did
  not answer. A stored node id is a name, never an answer.
* **An absence counts only where the same request shows the board answered.** An
  issue's own cards list only what the credential may see, so the read of an
  issue's card (:func:`resolve_item_id`, :func:`read_issue_cards`) carries the
  board's own read and a search for a witness in the same request, and reports
  no card only where a witness shows the credential's reads see the board.
* **A read that is not whole answers nothing:** one cut short, asking for less
  than its question covers, or carrying an error on the board or its cards.

Reads only
----------
Nothing here mutates. The *write* is constructed and executed exclusively by
`_lib/substrate_writes` (ADR-031's sole constructor), and board **membership**
(`gh project item-add`) is deliberately absent — it is a different operation
(DEC-019, named OUT of ADR-031 point 3), and a verb that sets a *field* has no
business granting membership. A missing card is therefore *reported*
(`ItemLookup(ok=True, item_id=None)`), for the caller to refuse on with a
remediation, exactly as `back-fill` reports "blocked — needs board membership".

Failure-posture neutrality (as in `substrate_writes`)
----------------------------------------------------
Every read returns a result object carrying `ok` plus, where the board did not
answer, why in `error`: `gh`'s words verbatim where `gh` failed, or the fault the
seam names, with the way out its cause gives ([pkit:ADR-096] point 6). `named` is
True where `error` names the fault itself. A missing `read:project` scope is the
single most likely failure in practice, and its remedy lives in `gh`'s stderr
(`gh auth refresh -s project`) — so the seam never paraphrases or swallows it.
The caller decides what a failure means (refuse, skip, warn), within the limits
[pkit:ADR-096] point 4 sets; this module takes no view.

Injectable `gh_call`
--------------------
Each read accepts `gh_call`, the callable that actually shells out, defaulting to
the right constructor for the operation: `gh project` reads go through
`gh_project_run` (the #453 sole constructor that threads `GH_HOST` and splices
`--owner`), the GraphQL reads through `gh_run`. Callers that already own a `gh`
seam — the delegating `back-fill` / `adopt-existing` wrappers, and tests — pass
their own, keeping their existing invocation path and patch point unchanged.

Exports:

    ProjectLookup / BoardFieldsRead / ItemLookup — the three read results
    ItemValueRead                   — one issue's card, and the option it holds
    IssueCardsRead                  — the listed issues' cards, each as an ItemValueRead
    ItemsRead / BoardItem           — a walk of the board's cards, each marked archived or not
    CardRead                        — one card, read by the id an add answered with
    NO_BOARD                        — why a read is refused with no board configured
    EVERY_ARCHIVED_STATE            — the argument by which a walk of the cards reads them all
    FIELD_REREAD_QUERY              — back-fill's fresh read of one card's values
    board_number(config)            — the configured board NUMBER, or None
    default_owner(config)           — `gh.default_owner`, or None
    board_owner(config, ...)        — the board's owner: `gh.default_owner`, else the repo's
    configured_board(config, ...)   — the configured board by its names
    url_owner(url)                  — the owner a GitHub url names, or None
    read_project_node_id(...)       — board number → project node id (rich)
    resolve_project_node_id(...)    — the same, as a bare `str | None`
    read_fields(...)                — the board's live fields + their options, and its node
    resolve_item_id(...)            — the issue's card (item) id on that board
    read_issue_cards(...)           — the listed issues' cards, in batches of node ids
    read_item_value(...)            — one issue's card and the option it holds in one field
    read_items(...)                 — every card, with the option it holds in one field
    read_items_with_option(...)     — the cards whose value is one option
    read_card(...)                  — one card by its item id, and the option it holds
    find_field / field_names / field_type / is_single_select
    option_id / option_names        — name → id matching over a read field
"""

from __future__ import annotations

import dataclasses
import json
import re
import subprocess
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from typing import Any

# Sibling modules — the gh shell-out helpers that pin the adopter's host/owner
# (DEC-023), and the part of the seam that judges the board's answer. Imported the
# way `_lib.hooks` / `_lib.substrate_writes` do, with a defensive fallback for
# unusual import contexts (a test that loads a module by file path may not have
# `_lib` on sys.path).
try:
    from gh import gh_project_run, gh_run  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - defensive import fallback
    try:
        from _lib.gh import gh_project_run, gh_run  # type: ignore[no-redef]
    except ImportError:  # pragma: no cover
        gh_project_run = None  # type: ignore[assignment]
        gh_run = None  # type: ignore[assignment]

try:
    import board_answer  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - defensive import fallback
    from _lib import board_answer  # type: ignore[no-redef]

# The state-issue seam's one reader of the marker (ADR-071 point 6), by which the
# board's read sets a state issue's card aside.
try:
    from state_issues import is_state_issue  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - defensive import fallback
    from _lib.state_issues import is_state_issue  # type: ignore[no-redef]


GhCall = Callable[..., "subprocess.CompletedProcess[str]"]

# GraphQL type names Projects v2 uses for its field kinds. Only the single-select
# kind is resolvable to an option id from a NAME, which is the whole mechanism
# here; the others are named so a refusal can say which kind it found.
SINGLE_SELECT_TYPE = "ProjectV2SingleSelectField"

# Bound on the fields a read of the board's fields asks for. GitHub allows a board
# fifty, so a read past it is one cut short, and answers nothing.
_MAX_FIELDS = 100

#: Why a board read is refused where the configuration names no board, made
#: with no call.
NO_BOARD = (
    "no Projects v2 board configured — project/config.yaml needs "
    "`has_projects_v2_board: true` and `projects_v2_board_id: <number>`."
)


@dataclass(frozen=True)
class ProjectLookup:
    """Outcome of resolving the board NUMBER to its project node id.

    ``ok=True`` carries the node id of the board whose answer named the
    configured board. ``ok=False`` is a board that did not answer, with why."""

    ok: bool
    node_id: str | None = None
    error: str | None = None
    named: bool = False


@dataclass(frozen=True)
class BoardFieldsRead:
    """Outcome of reading the board's live fields (each with its options).

    ``project_id`` is the board's node, from the same answer as the fields."""

    ok: bool
    fields: tuple[dict[str, Any], ...] = ()
    error: str | None = None
    project_id: str | None = None
    named: bool = False


@dataclass(frozen=True)
class ItemLookup:
    """Outcome of resolving the issue's card (item) id on the board.

    `ok=True, item_id=None` is the **membership** case — the board answered, a
    witness showing it, and the issue is not on the board (board membership is a
    post-creation step, so a just-filed issue may have no card yet). That is
    distinct from `ok=False`, which means the board did not answer, or the
    issue's own read failed, and nothing is known.
    """

    ok: bool
    item_id: str | None = None
    error: str | None = None
    named: bool = False


# ----- config readers ----------------------------------------------------


def board_number(config: dict[str, Any]) -> str | None:
    """The configured board NUMBER as a string, or None when no board is configured.

    None covers both "the flag is off" (`has_projects_v2_board` falsey/absent) and
    "the flag is on but `projects_v2_board_id` is unset" — the two states every
    existing board reader collapses, since neither yields a board to read.
    pre-check is the gate that tells the adopter *which* of the two they are in.
    """
    if not isinstance(config, dict) or not config.get("has_projects_v2_board"):
        return None
    number = config.get("projects_v2_board_id")
    if number is None:
        return None
    return str(number)


def default_owner(config: dict[str, Any]) -> str | None:
    """The adopter's configured `gh.default_owner`, or None."""
    gh_block = config.get("gh") if isinstance(config, dict) else None
    if isinstance(gh_block, dict):
        owner = gh_block.get("default_owner")
        if isinstance(owner, str) and owner:
            return owner
    return None


def stored_node(config: dict[str, Any]) -> str | None:
    """The board's node id the configuration stores (`projects_v2_node_id`), or
    None. A name, read only to address the board's own read and to know the
    configured board's card ([pkit:ADR-096] point 6): never an answer."""
    node = config.get("projects_v2_node_id") if isinstance(config, dict) else None
    return node if isinstance(node, str) and node else None


def board_owner(
    config: dict[str, Any],
    *,
    repository_owner: str | None = None,
    gh_call: GhCall | None = None,
) -> str | None:
    """The board's owner, which a `gh project` read names: `gh.default_owner`,
    else the repository's owner.

    A single-owner adopter whose board lives in the repository's owner omits
    `gh.default_owner`, a person or an organisation alike. A `gh project` read
    with no `--owner` looks among the boards of whoever runs `gh`, so it misses an
    organisation's board, and may find a same-numbered board of that person's.

    ``repository_owner`` is the repository's owner where the caller holds it, such
    as from an issue's url. Where it holds none, `gh repo view` reads it, and only
    then. None where neither resolves: the read then names no owner."""
    owner = default_owner(config)
    if owner:
        return owner
    if repository_owner:
        return repository_owner
    proc, _error = _invoke(
        ["gh", "repo", "view", "--json", "nameWithOwner"], config, owner=None, gh_call=gh_call
    )
    payload = _parse_json(proc.stdout) if proc is not None else None
    name = payload.get("nameWithOwner") if isinstance(payload, dict) else None
    if isinstance(name, str) and "/" in name:
        return name.split("/", 1)[0] or None
    return None


def configured_board(
    config: dict[str, Any], *, owner: str | None = None, node: str | None = None
) -> board_answer.Board | None:
    """The configured board by its names: its number, ``owner``, and its node,
    ``node`` where the caller holds one from the board's own answer, else the one
    the configuration stores. None where no board is configured."""
    number = board_number(config)
    if number is None:
        return None
    return board_answer.Board(number, owner, node or stored_node(config))


def url_owner(url: str | None) -> str | None:
    """The owner a GitHub url names, as `https://<host>/<owner>/<repo>/…` does,
    such as an issue's; None for a url that names none."""
    match = re.match(r"https?://[^/]+/([^/]+)/", url or "")
    return match.group(1) if match else None


def _owner(config: dict[str, Any], owner: str | None, gh_call: GhCall | None) -> str | None:
    """The owner a read addresses the board under, as :func:`board_owner`
    resolves it: `gh.default_owner`, else ``owner``, the repository's owner where
    the caller holds it, else the repository's read by `gh repo view`. So every
    read names the board under one owner, the one the `gh project` constructor
    splices too."""
    return board_owner(config, repository_owner=owner, gh_call=gh_call)


# ----- the board's own reads ---------------------------------------------


def read_project_node_id(
    config: dict[str, Any],
    *,
    owner: str | None = None,
    gh_call: GhCall | None = None,
) -> ProjectLookup:
    """Resolve the board NUMBER to its Projects-v2 project node id (`PVT_…`).

    A `gh project view --format json` read: its answer names the board by its
    `id`, `number` and `owner`, and counts only where those agree with the
    configured board's names — the number, the owner (:func:`_owner`) and the
    stored `projects_v2_node_id` where there is one. A stored
    node is never taken for the answer: it was written under some credential at
    some time, and says nothing of this one ([pkit:ADR-096] point 1).

    Returns `ok=False` with `gh`'s stderr verbatim when the read fails, and with
    the fault named where the answer names no board or another one.
    """
    number = board_number(config)
    if number is None:
        return ProjectLookup(ok=False, error=NO_BOARD, named=True)
    owner = _owner(config, owner, gh_call)
    board = board_answer.Board(number, owner, stored_node(config))
    args = ["gh", "project", "view", number, "--format", "json"]
    proc, error = _invoke(args, config, owner=owner, gh_call=gh_call)
    if proc is None:
        return ProjectLookup(ok=False, error=board_answer.from_service(error or "").said)
    payload = _parse_json(proc.stdout)
    why = board.disagreement(payload)
    if why is not None:
        return ProjectLookup(ok=False, error=board_answer.no_board(board, why).said, named=True)
    return ProjectLookup(ok=True, node_id=str(payload["id"]))


def resolve_project_node_id(
    config: dict[str, Any],
    *,
    owner: str | None = None,
    gh_call: GhCall | None = None,
) -> str | None:
    """The board's project node id, or None on any failure.

    The lossy form of :func:`read_project_node_id`, for callers whose contract is
    already "None means no board resolvable" (`back-fill`'s residual gate,
    `adopt-existing`'s inventory).
    """
    return read_project_node_id(config, owner=owner, gh_call=gh_call).node_id


# The fields the board's own read asks for: each field's kind, id and name, and a
# single-select's options in full, colour and description included.
_FIELDS_SELECTION = (
    f"fields(first: {_MAX_FIELDS}) {{ pageInfo {{ hasNextPage }} nodes {{ __typename "
    "... on ProjectV2FieldCommon { id name } "
    "... on ProjectV2SingleSelectField { options { id name color description } } } }"
)


def read_fields(
    config: dict[str, Any],
    *,
    owner: str | None = None,
    gh_call: GhCall | None = None,
) -> BoardFieldsRead:
    """The board's live fields, each with its `id`, `name`, `type` and `options`,
    and the board's node, from one read of the board itself.

    One GraphQL read, addressed to the board by its stored node, else by its
    number under its owner (:func:`_owner`, ``owner`` the repository's), whose
    answer names the board: it counts only where it names the configured board
    ([pkit:ADR-096] point 1), and only where it read every field (point 2). Each
    single-select's options come back on the same read, with their colour and
    description, which is what lets a refusal name what the board actually
    offers, and a write of a field's option list keep the value each card holds.

    `ok=False` carries `gh`'s words verbatim — the missing-`read:project`-scope
    case, whose remedy is in that text — or the fault the seam names.
    """
    if board_number(config) is None:
        return BoardFieldsRead(ok=False, error=NO_BOARD, named=True)
    board = configured_board(config, owner=_owner(config, owner, gh_call))
    assert board is not None
    selection, variables, flags = board_answer.board_selection(board, _FIELDS_SELECTION)
    query = f"query({', '.join(variables)}) {{ {selection} }}"
    reply = board_answer.send(query, flags, config, gh_call=_graphql(gh_call))
    answer, unanswered = board_answer.board_answer(board, reply)
    if unanswered is None:
        words = board_answer.unplaced_error(reply, roots=())
        if words is not None:
            unanswered = board_answer.from_service(words)
    if unanswered is not None:
        return BoardFieldsRead(ok=False, error=unanswered.said, named=unanswered.named)
    assert answer is not None
    block = answer.get("fields")
    nodes = block.get("nodes") if isinstance(block, dict) else None
    page = block.get("pageInfo") if isinstance(block, dict) else None
    if not isinstance(nodes, list) or (isinstance(page, dict) and page.get("hasNextPage")):
        unanswered = board_answer.not_whole(board, "the board's fields were not all read")
        return BoardFieldsRead(ok=False, error=unanswered.said, named=True)
    fields = tuple(_field(node) for node in nodes if isinstance(node, dict) and node.get("id"))
    return BoardFieldsRead(ok=True, fields=fields, project_id=str(answer["id"]))


def _field(node: dict[str, Any]) -> dict[str, Any]:
    """One field as the reads give it: `id`, `name`, `type`, and a
    single-select's `options`, each with `id`, `name`, `color` and `description`."""
    field: dict[str, Any] = {
        "id": node.get("id"),
        "name": node.get("name"),
        "type": node.get("__typename") or "",
    }
    options = node.get("options")
    if isinstance(options, list):
        field["options"] = [
            {
                "id": option.get("id"),
                "name": option.get("name"),
                "color": str(option.get("color") or ""),
                "description": str(option.get("description") or ""),
            }
            for option in options
            if isinstance(option, dict)
            and isinstance(option.get("id"), str)
            and isinstance(option.get("name"), str)
        ]
    return field


# ----- an issue's own cards ----------------------------------------------


def resolve_item_id(
    config: dict[str, Any],
    *,
    issue_node_id: str,
    project_node_id: str | None = None,
    owner: str | None = None,
    gh_call: GhCall | None = None,
) -> ItemLookup:
    """The issue's card (item) node id on the configured board, from one request.

    Keyed on the ISSUE's own node id (`gh issue view --json id`) rather than on
    (repo, number): the issue is the thing we hold, and asking it for its
    `projectItems` needs no owner/repo re-derivation and cannot collide with a
    same-numbered issue from another repo on the same board. The board is
    addressed by ``project_node_id`` where the caller holds it from the board's
    own answer, else by its stored node, else by its number under its owner
    (:func:`_owner`, ``owner`` the repository's), and the request's own read of the
    board must name the configured board.

    Archived cards are included: an archived item still has field values worth
    writing, so reporting it as "not on the board" would send the adopter to add a
    duplicate card. An issue whose cards run past those read without its card on
    this board is a read cut short, never an issue with no card.

    Returns `ok=True, item_id=None` only where a witness in the same request shows
    the credential's reads see the board ([pkit:ADR-096] point 1: the membership
    case, which the caller refuses with a remediation), and `ok=False` where the
    board did not answer, with why and the way out, or the issue's own read failed.
    """
    if board_number(config) is None:
        return ItemLookup(ok=False, error=NO_BOARD, named=True)
    board = configured_board(config, owner=_owner(config, owner, gh_call), node=project_node_id)
    assert board is not None
    read = board_answer.read_cards(
        config, board=board, issue_node_ids=[issue_node_id], gh_call=_graphql(gh_call)
    )
    if not read.ok:
        error, named = _failure(read)
        return ItemLookup(ok=False, error=error, named=named)
    card = read.cards.get(issue_node_id)
    return ItemLookup(ok=True, item_id=card.item_id if card is not None else None)


@dataclass(frozen=True)
class ItemValueRead:
    """Outcome of reading one issue's card on a board, and the single-select
    option it holds in one field.

    Three answers, kept apart ([pkit:ADR-053] point 5): ``ok=False`` is a board
    that did not answer, with why in ``error``; ``ok=True, item_id=None`` is a
    board that answered, a witness showing it, and holds no card for the issue;
    ``ok=True`` with a card and ``option_name=None`` is a card whose field is
    unset. The caller decides what each means."""

    ok: bool
    item_id: str | None = None
    option_id: str | None = None
    option_name: str | None = None
    error: str | None = None
    named: bool = False


@dataclass(frozen=True)
class IssueCardsRead:
    """Outcome of reading the cards of listed issues on a board, and the option
    each holds in one field.

    Whole or nothing: ``ok=False`` is a listing that could not be read in full,
    with why in ``error``, and carries no card. ``ok=True`` carries in ``cards``
    one :class:`ItemValueRead` for each issue node id asked for, by that id, each
    with ``ok=True``: the issue's card on the board, or none."""

    ok: bool
    cards: Mapping[str, ItemValueRead] = dataclasses.field(default_factory=dict)
    error: str | None = None
    named: bool = False


def read_issue_cards(
    config: dict[str, Any],
    *,
    issue_node_ids: Iterable[str],
    project_node_id: str | None = None,
    field_name: str,
    owner: str | None = None,
    gh_call: GhCall | None = None,
) -> IssueCardsRead:
    """The card on the configured board of each issue whose node id is listed, and
    the option it holds in the single-select `field_name`.

    One GraphQL request for each batch of up to a hundred ids, keyed on the
    issues' own node ids, as :func:`resolve_item_id` is, so the read is bounded by
    what is listed and a fixed page for each repository, not by the board. Each
    request carries the board's own read, addressed as :func:`resolve_item_id`
    addresses it, and the search for a witness, and a batch whose absences found
    none is made again once, carrying a witness a later batch found
    ([pkit:ADR-096] point 1). Each issue's own cards are read, an archived card
    included, so an archived card is its issue's card. Whole or nothing: a batch
    whose board did not answer, an id that resolves to no issue, an issue whose
    cards run past one page without its card on this board, or an absence no
    witness shows, fails the whole read. Neutral: it reports what the board said,
    and takes no view on it."""
    if board_number(config) is None:
        return IssueCardsRead(ok=False, error=NO_BOARD, named=True)
    board = configured_board(config, owner=_owner(config, owner, gh_call), node=project_node_id)
    assert board is not None
    read = board_answer.read_cards(
        config,
        board=board,
        issue_node_ids=issue_node_ids,
        field_name=field_name,
        gh_call=_graphql(gh_call),
    )
    if not read.ok:
        error, named = _failure(read)
        return IssueCardsRead(ok=False, error=error, named=named)
    cards: dict[str, ItemValueRead] = {}
    for issue_node_id, card in read.cards.items():
        if card is None:
            cards[issue_node_id] = ItemValueRead(ok=True)
            continue
        cards[issue_node_id] = ItemValueRead(
            ok=True,
            item_id=card.item_id,
            option_id=card.option_id,
            option_name=card.option_name,
        )
    return IssueCardsRead(ok=True, cards=cards)


def read_item_value(
    config: dict[str, Any],
    *,
    issue_node_id: str,
    project_node_id: str | None = None,
    field_name: str,
    owner: str | None = None,
    gh_call: GhCall | None = None,
) -> ItemValueRead:
    """The issue's card on the configured board, and the option it holds in the
    single-select `field_name`: :func:`read_issue_cards` for one issue, so one
    issue and many are read by one account of which card is an issue's."""
    read = read_issue_cards(
        config,
        issue_node_ids=[issue_node_id],
        project_node_id=project_node_id,
        field_name=field_name,
        owner=owner,
        gh_call=gh_call,
    )
    if not read.ok:
        return ItemValueRead(ok=False, error=read.error, named=read.named)
    return read.cards[issue_node_id]


def _failure(read: board_answer.CardsRead) -> tuple[str, bool]:
    """Why a read of issues' cards failed, and whether the seam names the fault."""
    if read.unanswered is not None:
        return read.unanswered.said, read.unanswered.named
    return read.issue_failed or "the issues' cards could not be read", True


# ----- a walk of the board's cards ---------------------------------------


@dataclass(frozen=True)
class BoardItem:
    """One card on the board: its item id and the issue or pull request it holds.

    `number` is None for a draft card, which holds no issue. `kind` is what the
    card holds, as GitHub names it: `Issue`, `PullRequest` or `DraftIssue`.
    `repository` is an issue's `owner/name`, empty for anything else, and
    `closed` whether that issue is closed. `issue_id` is the issue's own node
    id, by which a listing of issues is joined to its card, empty for anything
    but an issue. `option_id` and `option_name` are the single-select option
    the card holds in the field read, None where it holds none.

    `withheld` marks a card whose issue lies in a repository the credential may
    not read: the board returns it with nothing of its issue. `value_read` says
    whether the board returned the card's value in the field read, which for a
    withheld card it may not ([pkit:ADR-096] point 2). `archived` says whether
    the card is archived, which the board's views hide: an archived card is a
    card all the same (ADR-096 point 5).
    """

    item_id: str
    number: int | None = None
    issue_id: str = ""
    title: str = ""
    kind: str = ""
    repository: str = ""
    closed: bool = False
    option_id: str | None = None
    option_name: str | None = None
    withheld: bool = False
    value_read: bool = True
    archived: bool = False


@dataclass(frozen=True)
class ItemsRead:
    """Outcome of a walk of the board's cards.

    ``items`` holds each card the walk counted. ``withheld`` holds each card the
    board withheld ([pkit:ADR-096] point 2), and ``set_aside`` each card the walk
    set aside for a reason of its own, a state issue's: neither is among
    ``items``. A command that acts only on its own repository's issues sets both
    aside; one that would clear or alter a value a card may hold refuses while
    one of them may hold it."""

    ok: bool
    items: tuple[BoardItem, ...] = ()
    error: str | None = None
    withheld: tuple[BoardItem, ...] = ()
    set_aside: tuple[BoardItem, ...] = ()
    named: bool = False


# Bound on the pages a card scan reads, at 100 cards a page. A board larger than
# this is reported as an error rather than read in part, since a caller counting
# cards must not take a partial count for the whole.
_MAX_ITEM_PAGES = 100

#: The argument by which a walk of the board's cards reads every card, archived
#: or not. Unasked, the board's card list leaves archived cards out, since its
#: `archivedStates` defaults to `[NOT_ARCHIVED]`. A board's own workflow archives
#: cards as a matter of course, so a walk that left them out would take an issue
#: whose only card is archived for one with no card, and an option only archived
#: cards hold for one no card holds (#3191).
EVERY_ARCHIVED_STATE = "archivedStates: [ARCHIVED, NOT_ARCHIVED]"

# The type GitHub gives a card whose issue the credential may not read.
_WITHHELD = "REDACTED"


def _items_selection(field_name: str | None) -> str:
    """One page of the walk, asked of the board beside its names: each card, an
    archived one included and marked so, its type, what it holds, and the
    single-select option it holds in one field."""
    value = (
        " fieldValueByName(name: $field) { ... on ProjectV2ItemFieldSingleSelectValue "
        "{ optionId name } }"
        if field_name is not None
        else ""
    )
    return (
        f"items(first: 100, after: $after, {EVERY_ARCHIVED_STATE}) {{ pageInfo "
        "{ hasNextPage endCursor } nodes { id type isArchived content { __typename "
        "... on Issue { id number title body state repository { nameWithOwner } } "
        f"... on PullRequest {{ number title }} ... on DraftIssue {{ title }} }}{value} }} }}"
    )


def read_items(
    config: dict[str, Any],
    *,
    project_node_id: str,
    field_name: str | None = None,
    owner: str | None = None,
    gh_call: GhCall | None = None,
) -> ItemsRead:
    """Every card on the board, with the single-select option it holds in
    `field_name` where one is named.

    Reads the board's cards a page at a time through GraphQL, each page carrying
    the board's own read, addressed by ``project_node_id`` and counted only where
    its answer names the configured board, its owner (:func:`_owner`, ``owner``
    the repository's) among its names. The whole board or nothing: a
    board read in part, or a page carrying an error, is never returned as the
    whole. An archived card is read as any other, so it still places its issue.
    A withheld card goes in `withheld`, and a card that holds a state issue in
    `set_aside`, since a state issue holds no work
    ([project-management:DEC-058-state-issues] point 3).
    """
    if board_number(config) is None:
        return ItemsRead(ok=False, error=NO_BOARD, named=True)
    board = configured_board(config, owner=_owner(config, owner, gh_call), node=project_node_id)
    assert board is not None
    selection, variables, flags = board_answer.board_selection(board, _items_selection(field_name))
    variables.append("$after: String")
    if field_name is not None:
        variables.append("$field: String!")
        flags += ["-f", f"field={field_name}"]
    query = f"query({', '.join(variables)}) {{ {selection} }}"
    counted: list[BoardItem] = []
    withheld: list[BoardItem] = []
    set_aside: list[BoardItem] = []
    after: str | None = None
    for _page in range(_MAX_ITEM_PAGES):
        page_flags = [*flags, "-f", f"after={after}"] if after else flags
        reply = board_answer.send(query, page_flags, config, gh_call=_graphql(gh_call))
        answer, unanswered = board_answer.board_answer(board, reply)
        if unanswered is None:
            words = board_answer.unplaced_error(reply, roots=())
            if words is not None:
                unanswered = board_answer.from_service(words)
        if unanswered is not None:
            return ItemsRead(ok=False, error=unanswered.said, named=unanswered.named)
        assert answer is not None
        items = answer.get("items")
        if not isinstance(items, dict) or not isinstance(items.get("nodes"), list):
            unanswered = board_answer.not_whole(board, "the reply carries no cards")
            return ItemsRead(ok=False, error=unanswered.said, named=True)
        for item in items["nodes"]:
            card = _board_item(item, value_asked=field_name is not None)
            if card is None:
                continue
            if card.withheld:
                withheld.append(card)
            elif _holds_state_issue(item):
                set_aside.append(card)
            else:
                counted.append(card)
        page_info = items.get("pageInfo") if isinstance(items.get("pageInfo"), dict) else {}
        if not page_info.get("hasNextPage"):
            return ItemsRead(
                ok=True,
                items=tuple(counted),
                withheld=tuple(withheld),
                set_aside=tuple(set_aside),
            )
        after = page_info.get("endCursor") if isinstance(page_info.get("endCursor"), str) else None
        if not after:
            unanswered = board_answer.not_whole(board, "a next page came with no cursor")
            return ItemsRead(ok=False, error=unanswered.said, named=True)
    unanswered = board_answer.not_whole(
        board, f"the board holds more than {_MAX_ITEM_PAGES * 100} cards"
    )
    return ItemsRead(ok=False, error=unanswered.said, named=True)


def read_items_with_option(
    config: dict[str, Any],
    *,
    project_node_id: str,
    field_name: str,
    option_id: str,
    owner: str | None = None,
    gh_call: GhCall | None = None,
) -> ItemsRead:
    """Every card on the board whose `field_name` value is the option `option_id`.

    The cards :func:`read_items` reads, kept where their single-select value is
    that option. Cards from every repository on the board count, since the field
    and its options are the board's, and so does an archived card. A withheld
    card that holds the option, or whose value the board did not return, goes in
    `withheld`, and a set-aside card that holds it in `set_aside`: a card that
    may hold the option whose value was not counted ([pkit:ADR-096] point 2).
    """
    read = read_items(
        config, project_node_id=project_node_id, field_name=field_name, owner=owner, gh_call=gh_call
    )
    if not read.ok:
        return read
    return ItemsRead(
        ok=True,
        items=tuple(i for i in read.items if i.option_id == option_id),
        withheld=tuple(i for i in read.withheld if not i.value_read or i.option_id == option_id),
        set_aside=tuple(i for i in read.set_aside if i.option_id == option_id),
    )


def _holds_state_issue(item: Any) -> bool:
    """Whether a card of a page holds a state issue, by its marker."""
    content = item.get("content") if isinstance(item, dict) else None
    return isinstance(content, dict) and is_state_issue(str(content.get("body") or ""))


def _board_item(item: Any, *, value_asked: bool = True) -> BoardItem | None:
    """One card of a page as :func:`read_items` returns it, or None for a node that
    is no card."""
    if not isinstance(item, dict):
        return None
    item_id = item.get("id")
    if not isinstance(item_id, str) or not item_id:
        return None
    value = item.get("fieldValueByName")
    value_read = isinstance(value, dict)
    value = value if isinstance(value, dict) else {}
    option = value.get("optionId")
    option_name = value.get("name")
    archived = item.get("isArchived") is True
    if item.get("type") == _WITHHELD:
        return BoardItem(
            item_id=item_id,
            option_id=option if isinstance(option, str) and option else None,
            option_name=option_name if isinstance(option_name, str) else None,
            withheld=True,
            value_read=value_asked and value_read,
            archived=archived,
        )
    content = item.get("content") if isinstance(item.get("content"), dict) else {}
    number = content.get("number")
    repository = content.get("repository")
    name = repository.get("nameWithOwner") if isinstance(repository, dict) else None
    kind = str(content.get("__typename") or "")
    issue_id = content.get("id") if kind == "Issue" else None
    return BoardItem(
        item_id=item_id,
        number=number if isinstance(number, int) else None,
        issue_id=issue_id if isinstance(issue_id, str) else "",
        title=str(content.get("title") or ""),
        kind=kind,
        repository=name if isinstance(name, str) else "",
        closed=str(content.get("state") or "").upper() == "CLOSED",
        option_id=option if isinstance(option, str) and option else None,
        option_name=option_name if isinstance(option_name, str) else None,
        archived=archived,
    )


# ----- one card, by the id an add answered with ------------------------------


@dataclass(frozen=True)
class CardRead:
    """Outcome of reading one card on the configured board by its item id.

    Three answers, kept apart ([pkit:ADR-096] point 4): ``ok=False`` is a board
    that did not answer, with why in ``error``; ``ok=True, found=False`` is a
    board that answered, in the same request, with no such card on it; and
    ``ok=True, found=True`` is the card, with the single-select option it holds
    in the field read, ``option_name=None`` for none."""

    ok: bool
    found: bool = False
    option_id: str | None = None
    option_name: str | None = None
    archived: bool = False
    error: str | None = None
    named: bool = False


def _card_selection(field_name: str | None) -> str:
    """The card asked for by its item id, beside the board's own read: the board
    it lies on, whether it is archived, and the option it holds in one field."""
    value = (
        " fieldValueByName(name: $field) { ... on ProjectV2ItemFieldSingleSelectValue "
        "{ optionId name } }"
        if field_name is not None
        else ""
    )
    return (
        "card: node(id: $item) { ... on ProjectV2Item { id isArchived project { id }"
        f"{value} }} }}"
    )


def read_card(
    config: dict[str, Any],
    *,
    item_id: str,
    project_node_id: str,
    field_name: str | None = None,
    owner: str | None = None,
    gh_call: GhCall | None = None,
) -> CardRead:
    """The card whose item id is ``item_id``, as the board holds it now, and the
    option it holds in the single-select ``field_name`` where one is named.

    The id is one the board answered an add with ([pkit:ADR-096] point 3), so
    the read decides nothing of which card is an issue's: it reads a card it
    knows already, not the issue's own cards, which can lag an add just made.
    One GraphQL request carries the board's own read, addressed by
    ``project_node_id`` and counted only where its answer names the configured
    board, beside the card. The card counts as not found only where the board
    answered: no card by that id, or one that lies on another board."""
    if board_number(config) is None:
        return CardRead(ok=False, error=NO_BOARD, named=True)
    board = configured_board(config, owner=_owner(config, owner, gh_call), node=project_node_id)
    assert board is not None
    selection, variables, flags = board_answer.board_selection(board)
    variables.append("$item: ID!")
    flags += ["-f", f"item={item_id}"]
    if field_name is not None:
        variables.append("$field: String!")
        flags += ["-f", f"field={field_name}"]
    query = f"query({', '.join(variables)}) {{ {selection} {_card_selection(field_name)} }}"
    reply = board_answer.send(query, flags, config, gh_call=_graphql(gh_call))
    node, unanswered = board_answer.card_answer(board, reply)
    if unanswered is not None:
        return CardRead(ok=False, error=unanswered.said, named=unanswered.named)
    if node is None:
        return CardRead(ok=True, found=False)
    value = node.get("fieldValueByName")
    value = value if isinstance(value, dict) else {}
    option = value.get("optionId")
    name = value.get("name")
    return CardRead(
        ok=True,
        found=True,
        option_id=option if isinstance(option, str) and option else None,
        option_name=name if isinstance(name, str) and name else None,
        archived=node.get("isArchived") is True,
    )


# ----- one card's values, read again before a write ------------------------

# The GraphQL field-values re-read of one card, by its item id — the SINGLE source
# of truth for this query, consumed by both of back-fill's read surfaces so they
# can never silently desync: the emitted script's field guard embeds it
# (`back_fill_apply._field_guarded_fragment`), and `--apply`'s fresh read issues
# it (`back-fill._read_current_field_value`). Both re-check the board field
# identically because both read the same string. It lives in the seam, which owns
# every read of the board ([pkit:ADR-096] point 6).
FIELD_REREAD_QUERY = (
    "query($item: ID!) { node(id: $item) { ... on ProjectV2Item { "
    "fieldValues(first: 50) { nodes { "
    "... on ProjectV2ItemFieldSingleSelectValue { optionId "
    "field { ... on ProjectV2FieldCommon { id } } } "
    "... on ProjectV2ItemFieldTextValue { text "
    "field { ... on ProjectV2FieldCommon { id } } } } } } } }"
)


# ----- name → id matching over a read field ------------------------------


def find_field(
    fields: tuple[dict[str, Any], ...] | list[dict[str, Any]], name: str
) -> dict[str, Any] | None:
    """The field whose NAME is `name` — exact match first, then case-insensitive.

    Exact-first so an adopter with two fields differing only in case gets the one
    they named; the case-insensitive fallback is there because the kit derives the
    name it looks for by Title-casing an axis (`priority` → `Priority`) and a board
    that spells it `PRIORITY` means the same field. Returns None when nothing
    matches — the caller then names what the board does offer.
    """
    for field in fields:
        if field.get("name") == name:
            return field
    lowered = name.lower()
    for field in fields:
        candidate = field.get("name")
        if isinstance(candidate, str) and candidate.lower() == lowered:
            return field
    return None


def field_names(fields: tuple[dict[str, Any], ...] | list[dict[str, Any]]) -> list[str]:
    """Every field name on the board, in read order — for a diagnostic."""
    return [f["name"] for f in fields if isinstance(f.get("name"), str)]


def field_type(field: dict[str, Any]) -> str:
    """The field's Projects-v2 type name (e.g. `ProjectV2SingleSelectField`)."""
    value = field.get("type")
    return value if isinstance(value, str) else "<unknown>"


def is_single_select(field: dict[str, Any]) -> bool:
    """True when `field` is a single-select — the only kind resolvable by NAME.

    A text / number / date / iteration field has no option vocabulary to match a
    classification value against, so writing one would mean inventing a
    serialisation for the value. Out of scope by decision (#724): the caller
    refuses with the type it found rather than mangling it.
    """
    return field_type(field) == SINGLE_SELECT_TYPE


def option_names(field: dict[str, Any]) -> list[str]:
    """Every option name declared on a single-select field, in board order."""
    options = field.get("options")
    if not isinstance(options, list):
        return []
    return [o["name"] for o in options if isinstance(o, dict) and isinstance(o.get("name"), str)]


def option_id(field: dict[str, Any], value: str) -> str | None:
    """The option id whose NAME is `value` — exact match first, then case-insensitive.

    Same matching rule as :func:`find_field`, for the same reason: the value comes
    from the adopter's classification vocabulary and the board's own spelling of it
    may differ only in case. None when no option matches.
    """
    options = field.get("options")
    if not isinstance(options, list):
        return None
    lowered = value.lower()
    fallback: str | None = None
    for option in options:
        if not isinstance(option, dict):
            continue
        name = option.get("name")
        oid = option.get("id")
        if not (isinstance(name, str) and isinstance(oid, str) and oid):
            continue
        if name == value:
            return oid
        if fallback is None and name.lower() == lowered:
            fallback = oid
    return fallback


# ----- invocation --------------------------------------------------------


def _invoke(
    args: list[str],
    config: dict[str, Any],
    *,
    owner: str | None,
    gh_call: GhCall | None,
) -> tuple[subprocess.CompletedProcess[str] | None, str | None]:
    """Run one `gh` read; return `(proc, None)` on success or `(None, verbatim_error)`.

    `gh project` reads go through `gh_project_run` (the #453 sole constructor,
    which owns the `--owner` flag and threads `GH_HOST`); anything else through
    `gh_run`. A caller-supplied `gh_call` replaces the default and receives the
    same keyword arguments, so a caller that owns its own `gh` seam keeps it.
    """
    is_project_call = args[:2] == ["gh", "project"]
    runner = gh_call
    if runner is None:
        runner = gh_project_run if is_project_call else gh_run
    if runner is None:  # pragma: no cover - defensive import fallback
        return None, "the `gh` helper is unavailable in this import context."
    try:
        if is_project_call:
            proc = runner(args, config, fallback_owner=owner, check=False)
        else:
            proc = runner(args, config, check=False)
    except FileNotFoundError:
        return None, "`gh` not on PATH. Install GitHub CLI."
    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip() or "no stderr"
        return None, stderr
    return proc, None


def _graphql(gh_call: GhCall | None) -> GhCall | None:
    """The runner a GraphQL read goes through: the caller's, else this module's
    `gh_run`, looked up at the call, so a test that patches it reaches every read."""
    return gh_call if gh_call is not None else gh_run


def _parse_json(stdout: str) -> Any:
    """Parse `stdout` as JSON, or return None when it is not JSON at all."""
    try:
        return json.loads(stdout)
    except (json.JSONDecodeError, ValueError):
        return None
