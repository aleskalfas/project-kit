"""What counts as the board's answer: the requests of the board read seam ([pkit:ADR-096]).

This module is part of the board read seam, beside `_lib/board_fields`, and every
read of a Projects v2 board goes through the two ([pkit:ADR-053] point 1,
[pkit:ADR-096] point 6). `board_fields` holds the reads a command calls. This
module builds the request each one makes, and says what its answer counts as,
under every credential alike:

* **The board's own read.** It is addressed to the board by its node where one is
  held, or by its number under its owner (:func:`board_selection`). It answered
  only where its answer names the configured board, agreeing with each of the
  board's names (:class:`Board`). An error, an answer with no board or no node in
  it, or one naming another board, is a board that did not answer. A stored
  board id is only a name: it addresses the read, and its answer must agree.
* **An issue's own cards** list only the cards the credential may see, and leave
  out the rest without saying so. A card on the configured board found there is
  the board's answer that the issue is on it. An absence counts only where the
  same request read the board itself, the board answered, and a witness shows
  that the credential's reads see the board: a card on the configured board,
  among the own cards of an issue from the same repository, told by the
  repository's node id ([pkit:ADR-096] point 1). :func:`read_cards` builds the
  board's read, the issues' cards and the search for a witness into one request,
  so no caller pairs a filtered read with a stored id or an earlier answer.
* **The page** a witness is sought in is a fixed page of one repository's issues,
  added to the request: the issues most recently created, of every state, and the
  open ones most recently updated, :data:`PAGE_CREATED` and :data:`PAGE_UPDATED`
  of them, with no more than :data:`PAGE_CARDS` of each one's cards. It is read
  for a witness and nothing else, and an error placed on it takes a witness away
  and fails nothing.
* **A read made in several requests** carries a witness across them: an issue one
  request found carded is carried into each request after it, and each request
  before it that found no witness is made again once, after the last, carrying
  it. The request made again is the one that answers.
* **A read that is not whole answers nothing:** one cut short, asking for less
  than its question covers, or carrying an error on the board or its cards. An
  error is placed by its path: the page's and a carried issue's take a witness
  away, an issue's own node is that issue's read failing, and any other is the
  board's.

* **An add's answer.** An add keeps its own place, in each command that makes
  one (ADR-031 point 3), and counts as made only where the board answers with
  the issue's card ([pkit:ADR-096] point 3): :func:`added_card` reads that
  answer for each of them alike.

What an answer means to a command is the command's own ([pkit:ADR-096] point 4):
this module reports the board's answer, or why the board did not answer with the
way out its cause gives, and decides nothing else. A project with no board makes
no request: every read stops before the network where no board is configured
([pkit:ADR-053] point 3), which `board_fields` checks before it calls here.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

# Sibling module, imported as `_lib.board_fields` imports it, with a defensive
# fallback for a test that loads a module by its path.
try:
    from gh import gh_run  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - defensive import fallback
    try:
        from _lib.gh import gh_run  # type: ignore[no-redef]
    except ImportError:  # pragma: no cover
        gh_run = None  # type: ignore[assignment]


GhCall = Callable[..., "subprocess.CompletedProcess[str]"]

#: How many of a repository's issues the page takes most recently created, of
#: every state, and how many of its open issues most recently updated. A hundred
#: in all, no more than one batch of a listing ([pkit:ADR-096], its Rationale).
PAGE_CREATED = 50
PAGE_UPDATED = 50

#: How many of each page issue's own cards the page reads: enough for an issue on
#: ten boards. A card past them takes a witness away, and fails nothing.
PAGE_CARDS = 10

#: The most issue node ids one request names: the most GitHub's `nodes(ids:)` takes.
MAX_NODE_IDS = 100

#: The cards of one issue a read asks for. An issue whose cards run past them
#: without its card on the board is a read cut short, never an issue with no card.
MAX_ISSUE_CARDS = 100

# The board's owner, as a ProjectV2 names it: a person or an organisation.
_OWNER = "owner { ... on User { login } ... on Organization { login } }"

# What the board's own read asks of the board, by which its answer names it.
_IDENTITY = f"id number {_OWNER}"

# The way out of a cause the service's words give: the credential, or the service.
_SERVICE_WAY_OUT = "a credential the board answers, or a later try"

# The way out of an answer that names no board or another one.
_NAMES_WAY_OUT = (
    "put the configuration's names right: `projects_v2_board_id`, `gh.default_owner`, "
    "and `projects_v2_node_id` where it is stored"
)


# ----- the configured board ---------------------------------------------------


@dataclass(frozen=True)
class Board:
    """The configured board, by the names that make it the configured one.

    ``number`` is the board's number, ``owner`` the owner the capability resolves
    for it (`board_fields.board_owner`), None where none resolves, and ``node``
    its node id where one is held: stored in the configuration, or read from the
    board's own answer earlier in the run. A held node addresses the board's own
    read, and the answer must agree with it, as with each other name."""

    number: str
    owner: str | None = None
    node: str | None = None

    @property
    def name(self) -> str:
        """The board as a message names it: `board #4 of acme`."""
        return f"board #{self.number}" + (f" of {self.owner}" if self.owner else "")

    def disagreement(self, answer: Any) -> str | None:
        """Why ``answer``, the board's own answer, does not name this board; None
        where it names it, agreeing with each of its names."""
        if not isinstance(answer, dict):
            return "the answer names no board"
        node = answer.get("id")
        if not isinstance(node, str) or not node:
            return "the answer names no board's node"
        number = answer.get("number")
        if str(number) != self.number:
            return f"the answer names board #{number}, not #{self.number}"
        login = owner_login(answer)
        if self.owner and (login is None or login.lower() != self.owner.lower()):
            return f"the answer names a board of {login or 'no owner'}, not of {self.owner}"
        if self.node and node != self.node:
            return f"the answer names the board {node}, not {self.node}"
        return None


def owner_login(answer: Mapping[str, Any]) -> str | None:
    """The login of the owner a board's answer names, or None where it names none."""
    owner = answer.get("owner")
    login = owner.get("login") if isinstance(owner, dict) else None
    return login if isinstance(login, str) and login else None


# ----- why the board did not answer ---------------------------------------------


@dataclass(frozen=True)
class Unanswered:
    """Why the board did not answer, on one line, with the way out its cause gives.

    ``said`` is the cause, with the service's words verbatim where it gave any,
    and the way out ([pkit:ADR-096] point 6). ``named`` is True where the seam
    names the fault itself, such as an answer naming another board, a read not
    whole or an absence with no witness, and False where ``said`` is what the
    service said."""

    said: str
    named: bool = False


def from_service(words: str) -> Unanswered:
    """The board did not answer, in the service's words."""
    return Unanswered(f"{one_line(words) or 'no words given'} ({_SERVICE_WAY_OUT})")


def no_board(board: Board, why: str) -> Unanswered:
    """The board's own answer named no board, or another one."""
    return Unanswered(f"{board.name} did not answer: {why}; {_NAMES_WAY_OUT}", named=True)


def not_whole(board: Board, what: str) -> Unanswered:
    """The read was cut short, or asked for less than its question covers."""
    return Unanswered(
        f"{board.name} did not answer in full: {what}, and a read in part is never "
        "taken for the whole; try again later",
        named=True,
    )


def no_witness(board: Board, page_words: str | None = None) -> Unanswered:
    """An absence with no witness: no issue the read saw shows a card on the
    board, so no issue's card can be told absent. Names both causes it can be."""
    said = (
        f"{board.name} answered, but no issue this read saw from the repository shows a "
        "card on it, so an issue with no card cannot be told from one this credential "
        "cannot see: where the issue is off the board, add it to the board; where it is "
        "on it, use a credential whose reads see the board's cards"
    )
    if page_words:
        said += f" (the page of the repository's recent issues was not read: {page_words})"
    return Unanswered(said, named=True)


# ----- one request --------------------------------------------------------------


@dataclass(frozen=True)
class Reply:
    """One request's reply: its data, and the errors placed in it; or, in
    ``failed``, why it failed whole, with the service's words."""

    data: Mapping[str, Any] = field(default_factory=dict)
    errors: tuple[Mapping[str, Any], ...] = ()
    failed: str | None = None


def send(
    query: str, flags: Iterable[str], config: dict[str, Any], *, gh_call: GhCall | None = None
) -> Reply:
    """Make one GraphQL request through `gh api graphql`, with ``flags`` its
    variables, and read its reply whatever `gh` exits with: GitHub answers a
    request whose part failed with that part's error beside the data of the
    rest, and `gh` then exits non-zero. A reply with no data fails whole."""
    args = ["gh", "api", "graphql", "-f", f"query={query}", *flags]
    runner = gh_call or gh_run
    if runner is None:  # pragma: no cover - defensive import fallback
        return Reply(failed="the `gh` helper is unavailable in this import context.")
    try:
        proc = runner(args, config, check=False)
    except FileNotFoundError:
        return Reply(failed="`gh` not on PATH. Install GitHub CLI.")
    payload = _parse_json(proc.stdout or "")
    data = payload.get("data") if isinstance(payload, dict) else None
    raw = payload.get("errors") if isinstance(payload, dict) else None
    errors = tuple(e for e in raw if isinstance(e, dict)) if isinstance(raw, list) else ()
    stderr = one_line(proc.stderr or "")
    if not isinstance(data, dict):
        words = "; ".join(_message(e) for e in errors) or stderr
        return Reply(errors=errors, failed=words or "`gh api graphql` returned no data")
    if proc.returncode != 0 and not errors:
        return Reply(failed=stderr or f"`gh api graphql` exited {proc.returncode}")
    return Reply(data, errors)


def board_selection(board: Board, inner: str = "") -> tuple[str, list[str], list[str]]:
    """The board's own read, under the alias `board`, with ``inner`` asked of it
    beside its names: the selection, its variable declarations, and the flags
    that pass them. By its node where one is held, else by its number under its
    owner, else, where no owner resolves, under the account `gh` runs as."""
    body = f"{_IDENTITY} {inner}".strip()
    if board.node:
        selection = f"board: node(id: $board) {{ ... on ProjectV2 {{ {body} }} }}"
        return selection, ["$board: ID!"], ["-f", f"board={board.node}"]
    number = ["-F", f"number={board.number}"]
    if board.owner:
        selection = (
            "board: repositoryOwner(login: $owner) { ... on ProjectV2Owner { "
            f"projectV2(number: $number) {{ {body} }} }} }}"
        )
        return (
            selection,
            ["$owner: String!", "$number: Int!"],
            ["-f", f"owner={board.owner}", *number],
        )
    selection = f"board: viewer {{ projectV2(number: $number) {{ {body} }} }}"
    return selection, ["$number: Int!"], number


def board_answer(board: Board, reply: Reply) -> tuple[dict[str, Any] | None, Unanswered | None]:
    """The board's own answer in ``reply``, made by :func:`board_selection`, or
    why the board did not answer: the reply failed, an error lies on the board's
    read, or its answer names no board or another one."""
    if reply.failed is not None:
        return None, from_service(reply.failed)
    for error in reply.errors:
        if _path(error)[:1] == ("board",):
            return None, from_service(_message(error))
    block = reply.data.get("board")
    answer = block if board.node else (block.get("projectV2") if isinstance(block, dict) else None)
    why = board.disagreement(answer)
    if why is not None:
        return None, no_board(board, why)
    assert isinstance(answer, dict)
    return answer, None


def unplaced_error(reply: Reply, roots: Iterable[str] = ("board",)) -> str | None:
    """The words of the first error in ``reply`` that lies outside ``roots``,
    or that the seam cannot place: an error on the board, its fields or its
    cards, which makes the board not answer. None where there is none."""
    kept = tuple(roots)
    for error in reply.errors:
        path = _path(error)
        if path and str(path[0]) in kept:
            continue
        return _message(error)
    return None


# ----- the issues' own cards, and the search for a witness ------------------------


@dataclass(frozen=True)
class Card:
    """An issue's card on the configured board: its item id, and the
    single-select option it holds in the field read, where one was."""

    item_id: str
    option_id: str | None = None
    option_name: str | None = None


@dataclass(frozen=True)
class CardsRead:
    """Outcome of reading the cards of listed issues on the configured board.

    Whole or nothing. ``unanswered`` says why the board did not answer, and
    ``issue_failed`` why an issue's own read failed, which is never the
    board's; with either, nothing is known. Otherwise ``cards`` maps each issue
    node id asked for to its :class:`Card`, or to None where the board answered
    that the issue has none, a witness showing it. ``project_id`` is the board's
    node, as the request's own read of the board named it."""

    cards: Mapping[str, Card | None] = field(default_factory=dict)
    unanswered: Unanswered | None = None
    issue_failed: str | None = None
    project_id: str | None = None

    @property
    def ok(self) -> bool:
        return self.unanswered is None and self.issue_failed is None


@dataclass(frozen=True)
class _Request:
    """What one request of :func:`read_cards` carries beside the board's read:
    its batch of issues, a page for each repository by its node id, or, where
    no repository is known yet, the page of the repository of ``anchor``, an
    issue of the batch; and an issue carried in for each repository as a
    witness, by the repository's node id."""

    batch: tuple[str, ...]
    pages: tuple[str, ...] = ()
    anchor: str | None = None
    carried: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class _Judged:
    """One request of :func:`read_cards`, judged: the cards found, or why the
    board did not answer, or why an issue's own read failed; and, for the read
    made in several requests, the witnesses it found by repository, the
    repositories it read issues of, those a page covered, and those with an
    issue whose absence it found no witness for."""

    cards: dict[str, Card | None] = field(default_factory=dict)
    unanswered: Unanswered | None = None
    issue_failed: str | None = None
    project_id: str | None = None
    witnesses: dict[str, str] = field(default_factory=dict)
    seen: frozenset[str] = frozenset()
    paged: frozenset[str] = frozenset()
    lacking: frozenset[str | None] = frozenset()
    page_words: str | None = None


def read_cards(
    config: dict[str, Any],
    *,
    board: Board,
    issue_node_ids: Iterable[str],
    field_name: str | None = None,
    gh_call: GhCall | None = None,
) -> CardsRead:
    """The card on ``board`` of each issue whose node id is listed, and, where
    ``field_name`` is given, the single-select option it holds in that field.

    One request for each batch of up to :data:`MAX_NODE_IDS` issues, each
    carrying the board's own read, the issues' own cards, an archived card
    included, and the search for a witness. A batch whose absences found no
    witness, where a later batch found one for its repository, is made again
    once after the last, carrying it, and that request answers for it. Whole or
    nothing: one request whose board did not answer, an issue whose cards run
    past those read without its card, or an absence no request could witness,
    fails the whole read."""
    ids = list(dict.fromkeys(issue_node_ids))
    batches = [
        tuple(ids[start : start + MAX_NODE_IDS]) for start in range(0, len(ids), MAX_NODE_IDS)
    ]
    found: dict[str, str] = {}
    pages: set[str] = set()
    judged: dict[int, _Judged] = {}
    for index, batch in enumerate(batches):
        request = _Request(
            batch,
            pages=tuple(sorted(pages)),
            anchor=None if pages else batch[0],
            carried=dict(found),
        )
        result = _ask(config, board, request, field_name, gh_call)
        if result.unanswered is not None or result.issue_failed is not None:
            return _failed(result)
        pages |= result.seen
        for repository, issue in result.witnesses.items():
            found.setdefault(repository, issue)
        judged[index] = result
    for index, result in list(judged.items()):
        if not result.lacking:
            continue
        lacking = {repository for repository in result.lacking if repository}
        carry = {repository: found[repository] for repository in lacking if repository in found}
        unpaged = lacking - result.paged
        if None in result.lacking or not (carry or unpaged):
            return CardsRead(unanswered=no_witness(board, result.page_words))
        again = _Request(batches[index], pages=tuple(sorted(result.paged | unpaged)), carried=carry)
        result = _ask(config, board, again, field_name, gh_call)
        if result.unanswered is not None or result.issue_failed is not None:
            return _failed(result)
        if result.lacking:
            return CardsRead(unanswered=no_witness(board, result.page_words))
        judged[index] = result
    cards: dict[str, Card | None] = {}
    project_id: str | None = None
    for result in judged.values():
        cards.update(result.cards)
        project_id = project_id or result.project_id
    return CardsRead(cards=cards, project_id=project_id)


def _failed(result: _Judged) -> CardsRead:
    return CardsRead(unanswered=result.unanswered, issue_failed=result.issue_failed)


def _ask(
    config: dict[str, Any],
    board: Board,
    request: _Request,
    field_name: str | None,
    gh_call: GhCall | None,
) -> _Judged:
    """Make one request of :func:`read_cards`, and judge its reply."""
    query, flags = _cards_query(board, request, field_name)
    reply = send(query, flags, config, gh_call=gh_call)
    return _judge(board, request, reply)


def _cards_query(board: Board, request: _Request, field_name: str | None) -> tuple[str, list[str]]:
    """The query of one request of :func:`read_cards`, and its flags."""
    selection, variables, flags = board_selection(board)
    value = (
        " fieldValueByName(name: $field) { ... on ProjectV2ItemFieldSingleSelectValue "
        "{ optionId name } }"
        if field_name is not None
        else ""
    )
    parts = [
        selection,
        "issues: nodes(ids: $ids) { ... on Issue { id repository { id } "
        f"projectItems(first: {MAX_ISSUE_CARDS}, includeArchived: true) "
        f"{{ pageInfo {{ hasNextPage }} nodes {{ id project {{ id }}{value} }} }} }} }}",
    ]
    variables.append("$ids: [ID!]!")
    flags = list(flags)
    for issue in request.batch:
        flags += ["-f", f"ids[]={issue}"]
    if field_name is not None:
        variables.append("$field: String!")
        flags += ["-f", f"field={field_name}"]
    if request.anchor is not None:
        parts.append(
            f"page0: node(id: $page0) {{ ... on Issue {{ repository {{ id {_page_orders()} }} }} }}"
        )
        variables.append("$page0: ID!")
        flags += ["-f", f"page0={request.anchor}"]
    for index, repository in enumerate(request.pages):
        parts.append(
            f"page{index}: node(id: $page{index}) {{ ... on Repository {{ id {_page_orders()} }} }}"
        )
        variables.append(f"$page{index}: ID!")
        flags += ["-f", f"page{index}={repository}"]
    for index, issue in enumerate(request.carried.values()):
        parts.append(
            f"carried{index}: node(id: $carried{index}) {{ ... on Issue {{ id repository {{ id }} "
            f"projectItems(first: {MAX_ISSUE_CARDS}, includeArchived: true) "
            "{ nodes { project { id } } } } }"
        )
        variables.append(f"$carried{index}: ID!")
        flags += ["-f", f"carried{index}={issue}"]
    return f"query({', '.join(variables)}) {{ {' '.join(parts)} }}", flags


def _page_orders() -> str:
    """The page's two orders, each issue with its first cards."""
    cards = (
        f"projectItems(first: {PAGE_CARDS}, includeArchived: true) "
        "{ nodes { project { id } } }"
    )
    created = (
        f"created: issues(first: {PAGE_CREATED}, orderBy: {{field: CREATED_AT, direction: DESC}}) "
        f"{{ nodes {{ id {cards} }} }}"
    )
    updated = (
        f"updated: issues(first: {PAGE_UPDATED}, states: [OPEN], "
        f"orderBy: {{field: UPDATED_AT, direction: DESC}}) {{ nodes {{ id {cards} }} }}"
    )
    return f"{created} {updated}"


def _judge(board: Board, request: _Request, reply: Reply) -> _Judged:
    """Judge one reply of :func:`read_cards`: the board's answer first, then
    each error by its path, then each issue's cards, then the witnesses."""
    answer, unanswered = board_answer(board, reply)
    if unanswered is not None:
        return _Judged(unanswered=unanswered)
    assert answer is not None
    project_id = str(answer["id"])
    page_words: list[str] = []
    issue_errors: dict[int, str] = {}
    for error in reply.errors:
        path = _path(error)
        root = str(path[0]) if path else ""
        if root.startswith(("page", "carried")):
            page_words.append(_message(error))
        elif root == "issues" and len(path) >= 2 and isinstance(path[1], int):
            if len(path) > 2 and path[2] == "projectItems":
                return _Judged(unanswered=from_service(_message(error)))
            issue_errors[path[1]] = _message(error)
        elif root != "board":
            return _Judged(unanswered=from_service(_message(error)))
    nodes = reply.data.get("issues")
    if not isinstance(nodes, list) or len(nodes) != len(request.batch):
        return _Judged(unanswered=not_whole(board, "the reply carries no cards for the issues"))
    cards: dict[str, Card | None] = {}
    witnesses: dict[str, str] = {}
    absent: dict[str, str | None] = {}
    seen: set[str] = set()
    for index, (issue, node) in enumerate(zip(request.batch, nodes, strict=True)):
        if not isinstance(node, dict) or node.get("id") != issue:
            said = issue_errors.get(index) or "the reply names no issue for it"
            return _Judged(issue_failed=f"the issue {issue} could not be read: {said}")
        repository = _repository(node)
        if repository:
            seen.add(repository)
        items = node.get("projectItems")
        listed = items.get("nodes") if isinstance(items, dict) else None
        if not isinstance(listed, list):
            return _Judged(unanswered=not_whole(board, f"the reply carries no cards for {issue}"))
        card = _card(listed, project_id)
        if card is not None:
            cards[issue] = card
            if repository:
                witnesses.setdefault(repository, issue)
            continue
        page = items.get("pageInfo") if isinstance(items, dict) else None
        if isinstance(page, dict) and page.get("hasNextPage"):
            return _Judged(
                unanswered=not_whole(
                    board,
                    f"the issue {issue} has cards on more than {MAX_ISSUE_CARDS} boards, and "
                    "its card on this one is not among those read",
                )
            )
        cards[issue] = None
        absent[issue] = repository
    paged: set[str] = set()
    for alias, block in reply.data.items():
        if not str(alias).startswith("page") or not isinstance(block, dict):
            continue
        holder = block.get("repository") if request.anchor is not None else block
        repository = holder.get("id") if isinstance(holder, dict) else None
        if not isinstance(repository, str) or not repository:
            continue
        paged.add(repository)
        seen.add(repository)
        for order in ("created", "updated"):
            for page_issue in _order_nodes(holder, order):
                if _on_board(_listed(page_issue), project_id):
                    witnesses.setdefault(repository, str(page_issue.get("id") or ""))
    for alias, block in reply.data.items():
        if not str(alias).startswith("carried") or not isinstance(block, dict):
            continue
        repository = _repository(block)
        if repository and _on_board(_listed(block), project_id):
            witnesses.setdefault(repository, str(block.get("id") or ""))
    lacking = frozenset(r for r in absent.values() if r is None or r not in witnesses)
    return _Judged(
        cards=cards,
        project_id=project_id,
        witnesses={r: i for r, i in witnesses.items() if i},
        seen=frozenset(seen),
        paged=frozenset(paged),
        lacking=lacking,
        page_words="; ".join(page_words) or None,
    )


def _repository(node: Mapping[str, Any]) -> str | None:
    """The node id of the repository an issue's node names, or None."""
    repository = node.get("repository")
    value = repository.get("id") if isinstance(repository, dict) else None
    return value if isinstance(value, str) and value else None


def _listed(node: Any) -> list[Any]:
    """The cards an issue's node lists, or none."""
    items = node.get("projectItems") if isinstance(node, dict) else None
    listed = items.get("nodes") if isinstance(items, dict) else None
    return listed if isinstance(listed, list) else []


def _order_nodes(holder: Mapping[str, Any], order: str) -> list[dict[str, Any]]:
    """The issues one order of the page lists."""
    block = holder.get(order)
    nodes = block.get("nodes") if isinstance(block, dict) else None
    return [n for n in nodes if isinstance(n, dict)] if isinstance(nodes, list) else []


def _on_board(listed: Iterable[Any], project_id: str) -> bool:
    """Whether an issue's cards hold one on the board ``project_id``: a witness."""
    for item in listed:
        project = item.get("project") if isinstance(item, dict) else None
        if isinstance(project, dict) and project.get("id") == project_id:
            return True
    return False


def _card(listed: Iterable[Any], project_id: str) -> Card | None:
    """The card on the board ``project_id`` among an issue's cards, with its id,
    or None."""
    for item in listed:
        if not isinstance(item, dict):
            continue
        project = item.get("project")
        item_id = item.get("id")
        if not isinstance(project, dict) or project.get("id") != project_id:
            continue
        if not isinstance(item_id, str) or not item_id:
            continue
        value = item.get("fieldValueByName")
        value = value if isinstance(value, dict) else {}
        option = value.get("optionId")
        name = value.get("name")
        return Card(
            item_id=item_id,
            option_id=option if isinstance(option, str) and option else None,
            option_name=name if isinstance(name, str) and name else None,
        )
    return None


# ----- an add's answer -----------------------------------------------------------


def added_card(stdout: str, url: str) -> tuple[str | None, str]:
    """The card an add made, from the board's answer to `gh project item-add
    --format json`: its id, or None and why the add is not made.

    The add counts as made only where the board answers with the issue's card
    ([pkit:ADR-096] point 3): an answer that names a card, and, where it names
    what the card holds, names the issue at ``url``. Anything else is an add
    not made, whatever the tool's exit status."""
    payload = _parse_json(stdout or "")
    item_id = payload.get("id") if isinstance(payload, dict) else None
    if not isinstance(item_id, str) or not item_id:
        return None, "the board's answer to the add names no card"
    held = payload.get("url")
    if isinstance(held, str) and held and held.rstrip("/") != url.rstrip("/"):
        return None, f"the board answered the add with a card holding {held}, not {url}"
    return item_id, ""


# ----- helpers ------------------------------------------------------------------------


def one_line(text: str) -> str:
    """``text`` on one line, as it was said."""
    return " ".join(text.split())


def _path(error: Mapping[str, Any]) -> tuple[Any, ...]:
    path = error.get("path")
    return tuple(path) if isinstance(path, list) else ()


def _message(error: Mapping[str, Any]) -> str:
    message = error.get("message")
    return one_line(message) if isinstance(message, str) and message else "an error with no message"


def _parse_json(stdout: str) -> Any:
    try:
        return json.loads(stdout)
    except (json.JSONDecodeError, ValueError):
        return None
