"""How a Projects v2 board answers the board read seam's GraphQL requests (ADR-096).

The seam (`_lib/board_fields`, `_lib/board_answer`) builds each read of the board
as one GraphQL request: the board's own read, addressed by its node or by its
number under its owner, with what it asks of the board beside its names (its
fields, or a page of its cards), and, for a read of issues' cards, the issues'
own cards, a page of each repository's recent issues and an issue carried in as
a witness. :class:`GraphBoard` answers such a request as GitHub does: the data of
each part, an error placed by its path on a part that failed, and `gh`'s non-zero
exit where any error is placed.

A read of one card by its item id asks for it beside the board's own read, under
the alias `card`.

A fake board subclasses it, or holds one, and says what the board holds through
the methods below; each method's default holds nothing. Nothing here touches a
network.
"""

from __future__ import annotations

import json
import re
import subprocess
from typing import Any

from tests.pm_board_archive import reads_archived

#: Who runs `gh`, whose boards a read under `viewer` reads.
VIEWER = "octocat"


def flag_values(argv: list[str], name: str) -> list[str]:
    """Every value of a `-f name=value` or `-F name=value` field, in order, as
    `ids[]` passes a list."""
    return [
        argv[i + 1].split("=", 1)[1]
        for i, arg in enumerate(argv[:-1])
        if arg in ("-f", "-F") and argv[i + 1].startswith(f"{name}=")
    ]


def flag_value(argv: list[str], name: str) -> str | None:
    """The value of a `-f name=value` or `-F name=value` field of `gh api graphql`."""
    found = flag_values(argv, name)
    return found[0] if found else None


def query_of(argv: list[str]) -> str:
    """The query a `gh api graphql` call sends."""
    return flag_value(argv, "query") or ""


def is_seam_read(argv: list[str]) -> bool:
    """Whether a `gh api graphql` call is a read the seam builds: one that reads
    the board itself under the alias `board`."""
    return argv[1:3] == ["api", "graphql"] and "board: " in query_of(argv)


def done(argv: list[str], returncode: int = 0, stdout: str = "", stderr: str = ""):
    return subprocess.CompletedProcess(argv, returncode, stdout, stderr)


def not_found(path: list[Any], message: str) -> dict[str, Any]:
    """An error GitHub places on one part of a request."""
    return {"type": "NOT_FOUND", "path": path, "message": message}


class GraphBoard:
    """A Projects v2 board that answers the seam's GraphQL requests.

    ``node``, ``number`` and ``owner`` are the board's names. A subclass says
    what the board holds: :meth:`fields`, :meth:`own_cards`, :meth:`more_cards`,
    :meth:`repository_of`, :meth:`recent_issues`, :meth:`walk` and
    :meth:`card_by_id`. ``failing`` maps a part of a read (`fields`, `cards`,
    `items`) to the words of a request that fails whole on it, a read of one card
    by its id among `cards`; ``placed`` maps a part to the words of an error placed
    on that part alone, the rest of the request answering (`board`, `cards`,
    `page`, `issue:<node id>`, `card`)."""

    def __init__(self, *, node: str, number: int, owner: str) -> None:
        self.node = node
        self.number = number
        self.owner = owner
        self.failing: dict[str, str] = {}
        self.placed: dict[str, str] = {}
        self.graph_calls: list[list[str]] = []

    # --- what the board holds -------------------------------------------------

    def fields(self) -> list[dict[str, Any]]:
        """The board's fields, as the seam's reads give them: `id`, `name`,
        `type` and a single-select's `options`."""
        return []

    def own_cards(self, issue_id: str, value_field: str | None) -> list[dict[str, Any]] | None:
        """An issue's own cards, as GitHub lists them on the issue, each with its
        `id`, `project` and, where ``value_field`` is asked, its
        `fieldValueByName`; None for a node id that names no issue."""
        return None

    def more_cards(self, issue_id: str) -> bool:
        """Whether an issue's own cards run past the page its read takes."""
        return False

    def repository_of(self, issue_id: str) -> str | None:
        """The node id of the repository an issue lies in."""
        return None

    def recent_issues(self, repository_id: str, order: str) -> list[str]:
        """The node ids of a repository's issues in one of the page's orders:
        `created`, every state, most recently created first, or `updated`, the
        open ones most recently updated first."""
        return []

    def walk(self, value_field: str | None, archived: bool) -> list[dict[str, Any]]:
        """Every card on the board as its card list gives them, archived ones
        only where ``archived`` is asked."""
        return []

    def card_by_id(self, item_id: str, value_field: str | None) -> dict[str, Any] | None:
        """The card whose item id is ``item_id``, with its `id`, `isArchived`,
        `project` and, where ``value_field`` is asked, its `fieldValueByName`;
        None for an id that names no card."""
        return None

    # --- the answer -------------------------------------------------------------

    def identity(self) -> dict[str, Any]:
        return {"id": self.node, "number": self.number, "owner": {"login": self.owner}}

    def reply(self, argv: list[str]) -> subprocess.CompletedProcess[str]:
        """Answer one of the seam's requests."""
        self.graph_calls.append(list(argv))
        query = query_of(argv)
        part = (
            "items"
            if "items(first:" in query
            else "fields"
            if "fields(first:" in query
            else "cards"
        )
        if part in self.failing:
            return done(argv, 1, stderr=self.failing[part])
        errors: list[dict[str, Any]] = []
        data: dict[str, Any] = {}
        board = self._board(argv, query, errors)
        if board is not None:
            if part == "fields":
                board["fields"] = self._fields()
            elif part == "items":
                board["items"] = self._items(argv, query)
        data["board"] = self._addressed(query, board)
        if "issues: nodes(ids:" in query:
            self._cards(argv, query, data, errors)
        if "card: node(id: $item)" in query:
            self._card(argv, query, data, errors)
        if errors:
            return done(argv, 1, json.dumps({"data": data, "errors": errors}), errors[0]["message"])
        return done(argv, 0, json.dumps({"data": data}))

    def _board(self, argv: list[str], query: str, errors: list[dict[str, Any]]) -> dict | None:
        if "board" in self.placed:
            errors.append(not_found(["board"], self.placed["board"]))
            return None
        if "board: node(id: $board)" in query:
            node = flag_value(argv, "board")
            if node != self.node:
                errors.append(
                    not_found(
                        ["board"], f"Could not resolve to a node with the global id of '{node}'"
                    )
                )
                return None
            return self.identity()
        number = flag_value(argv, "number")
        owner = flag_value(argv, "owner") if "repositoryOwner" in query else VIEWER
        if owner != self.owner or str(number) != str(self.number):
            errors.append(
                not_found(
                    ["board", "projectV2"],
                    f"Could not resolve to a ProjectV2 with the number {number}.",
                )
            )
            return None
        return self.identity()

    @staticmethod
    def _addressed(query: str, board: dict | None) -> Any:
        if "board: node(id: $board)" in query:
            return board
        return {"projectV2": board}

    def _fields(self) -> dict[str, Any]:
        nodes = []
        for field in self.fields():
            node: dict[str, Any] = {
                "__typename": field.get("type", "ProjectV2Field"),
                "id": field["id"],
                "name": field["name"],
            }
            if "options" in field:
                node["options"] = [
                    {
                        "id": option["id"],
                        "name": option["name"],
                        "color": option.get("color", "GRAY"),
                        "description": option.get("description", ""),
                    }
                    for option in field["options"]
                ]
            nodes.append(node)
        return {"pageInfo": {"hasNextPage": False}, "nodes": nodes}

    def _items(self, argv: list[str], query: str) -> dict[str, Any]:
        value_field = flag_value(argv, "field") if "fieldValueByName" in query else None
        nodes = self.walk(value_field, reads_archived(query))
        return {"pageInfo": {"hasNextPage": False, "endCursor": None}, "nodes": nodes}

    def _cards(
        self, argv: list[str], query: str, data: dict[str, Any], errors: list[dict[str, Any]]
    ) -> None:
        value_field = flag_value(argv, "field") if "fieldValueByName" in query else None
        nodes: list[Any] = []
        for index, issue_id in enumerate(flag_values(argv, "ids[]")):
            node = self._issue(issue_id, value_field)
            if f"issue:{issue_id}" in self.placed:
                errors.append(not_found(["issues", index], self.placed[f"issue:{issue_id}"]))
                node = None
            elif node is None:
                errors.append(
                    not_found(
                        ["issues", index],
                        f"Could not resolve to a node with the global id of '{issue_id}'",
                    )
                )
            elif "cards" in self.placed:
                errors.append(not_found(["issues", index, "projectItems"], self.placed["cards"]))
                node["projectItems"] = None
            nodes.append(node)
        data["issues"] = nodes
        for alias in re.findall(r"(page\d+): node\(id: \$page\d+\)", query):
            if "page" in self.placed:
                errors.append(not_found([alias], self.placed["page"]))
                data[alias] = None
                continue
            anchored = re.search(rf"{alias}: node\(id: \${alias}\) {{ \.\.\. on Issue", query)
            target = flag_value(argv, alias) or ""
            repository = self.repository_of(target) if anchored else target
            if repository is None:
                errors.append(
                    not_found(
                        [alias], f"Could not resolve to a node with the global id of '{target}'"
                    )
                )
                data[alias] = None
                continue
            page: dict[str, Any] = {"id": repository}
            for order in ("created", "updated"):
                page[order] = {
                    "nodes": [
                        {"id": i, "projectItems": {"nodes": self._page_cards(i)}}
                        for i in self.recent_issues(repository, order)
                    ]
                }
            data[alias] = {"repository": page} if anchored else page
        for alias in re.findall(r"(carried\d+): node\(id: \$carried\d+\)", query):
            issue_id = flag_value(argv, alias) or ""
            data[alias] = self._issue(issue_id, None)

    def _card(
        self, argv: list[str], query: str, data: dict[str, Any], errors: list[dict[str, Any]]
    ) -> None:
        """One card by its item id, as GitHub answers a node: null, with a
        not-found error on it, for an id that names none."""
        item_id = flag_value(argv, "item") or ""
        if "card" in self.placed:
            errors.append({"type": "FORBIDDEN", "path": ["card"], "message": self.placed["card"]})
            data["card"] = None
            return
        value_field = flag_value(argv, "field") if "fieldValueByName" in query else None
        node = self.card_by_id(item_id, value_field)
        if node is None:
            errors.append(
                not_found(
                    ["card"], f"Could not resolve to a node with the global id of '{item_id}'"
                )
            )
        data["card"] = node

    def _issue(self, issue_id: str, value_field: str | None) -> dict[str, Any] | None:
        cards = self.own_cards(issue_id, value_field)
        if cards is None:
            return None
        return {
            "id": issue_id,
            "repository": {"id": self.repository_of(issue_id)},
            "projectItems": {
                "pageInfo": {"hasNextPage": self.more_cards(issue_id)},
                "nodes": cards,
            },
        }

    def _page_cards(self, issue_id: str) -> list[dict[str, Any]]:
        cards = self.own_cards(issue_id, None) or []
        return [{"project": card["project"]} for card in cards][:10]


class FieldsBoard(GraphBoard):
    """A board whose fields a test sets, and which holds no cards."""

    def __init__(
        self, fields: list[dict[str, Any]], *, node: str = "PVT_1", number: int = 7, owner: str
    ) -> None:
        super().__init__(node=node, number=number, owner=owner)
        self._fields_held = fields

    def fields(self) -> list[dict[str, Any]]:
        return self._fields_held
