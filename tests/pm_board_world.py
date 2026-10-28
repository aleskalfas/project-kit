"""The in-memory tracker of `tests/pm_lifecycle_world.py`, with a Projects v2 board.

`BoardTracker` answers the `gh` calls the board's Status projection makes
(#2276): the project's id, its fields with the Status options, an issue's node
id, the issue's card, every card with its Status, a card added and a Status
written. Each card is keyed by the issue it holds; `foreign_cards` holds cards
the board carries for other repositories, pull requests and drafts.

The board has an owner, the repository's by default, and `gh` runs as someone
else. A `gh project` call that names no `--owner` looks among the boards of
whoever runs `gh`, as `gh` does, so it finds the board only under the owner it
names.

A config and a substrate map put the board in reach: `BOARD_CONFIG` configures
board #4, and `LABEL_STATE` binds the state to the kit's own labels, so the
board configured does not carry it (DEC-051) and its Status is a projection the
agent maintains (DEC-006).
"""

from __future__ import annotations

import json
import subprocess
from typing import Any

from tests.pm_lifecycle_world import Tracker

PROJECT_ID = "PVT_board4"
STATUS_FIELD_ID = "PVTSSF_status"
REPOSITORY = "acme/repo"
#: Who runs `gh`, and so the owner a `gh project` call with no `--owner` reads.
VIEWER = "octocat"
FIVE = ("Todo", "Backlog", "In Progress", "Review", "Done")

BOARD_CONFIG: dict[str, Any] = {"has_projects_v2_board": True, "projects_v2_board_id": 4}

#: The state bound to the kit's own `state:*` labels, by a map's `label:` arm.
LABEL_STATE: dict[str, Any] = {
    "state": {
        "label": {
            "remap": {
                state: f"state:{state}"
                for state in ("todo", "backlog", "in-progress", "review", "done")
            }
        }
    }
}


def _done(argv: list[str], returncode: int = 0, stdout: str = "", stderr: str = ""):
    return subprocess.CompletedProcess(argv, returncode, stdout, stderr)


def _option(argv: list[str], flag: str) -> str | None:
    return argv[argv.index(flag) + 1] if flag in argv else None


def _field(argv: list[str], name: str) -> str | None:
    """The value of a `-f name=value` or `-F name=value` field of `gh api graphql`."""
    for i, arg in enumerate(argv[:-1]):
        if arg in ("-f", "-F") and argv[i + 1].startswith(f"{name}="):
            return argv[i + 1].split("=", 1)[1]
    return None


class BoardTracker(Tracker):
    """The tracker, and board #4 with a single-select Status of `options`.

    `cards` maps an issue to its card: `{"id": <item id>, "status": <option name
    or None>}`. `edits` lists each Status written, `(issue, option name)`.
    `fail_reads` names the board reads that fail (`fields`, `items`, `card`),
    `fail_edits` the issues whose Status write fails, and `fail_adds` those whose
    card cannot be added. `repository` is this repository's `owner/name`, and
    `owner` the board's owner, the repository's unless a test sets another."""

    def __init__(self, options: tuple[str, ...] = FIVE, *, field: str = "Status") -> None:
        super().__init__()
        self.repository = REPOSITORY
        self.owner = REPOSITORY.split("/", 1)[0]
        self.options = {name: f"opt-{name.lower().replace(' ', '-')}" for name in options}
        self.field_name = field
        self.field_type = "ProjectV2SingleSelectField"
        self.cards: dict[int, dict[str, Any]] = {}
        self.foreign_cards: list[dict[str, Any]] = []
        self.edits: list[tuple[int, str]] = []
        self.adds: list[int] = []
        self.fail_reads: set[str] = set()
        self.fail_edits: set[int] = set()
        self.fail_adds: set[int] = set()

    # --- what a test sets up ------------------------------------------------

    def card(self, number: int, status: str | None = None) -> None:
        """Put the issue on the board, its card's Status `status`."""
        self.cards[number] = {"id": f"PVTI_{number}", "status": status}

    def status(self, number: int) -> str | None:
        return self.cards[number]["status"] if number in self.cards else None

    def board_calls(self) -> list[list[str]]:
        """The `gh` calls that reached the board, or read an issue's node id for it."""
        return [
            argv
            for argv in self.calls
            if argv[1] == "project"
            or (argv[1] == "api" and argv[2:3] == ["graphql"])
            or (argv[1:3] == ["issue", "view"] and _option(argv, "--json") == "id")
        ]

    # --- gh -----------------------------------------------------------------

    def gh(self, argv: list[str]) -> subprocess.CompletedProcess[str]:
        if argv[1] == "project":
            self.calls.append(argv)
            return self._project(argv)
        if argv[1:3] == ["api", "graphql"]:
            self.calls.append(argv)
            return self._graphql(argv)
        if argv[1:3] == ["issue", "view"] and _option(argv, "--json") == "id":
            self.calls.append(argv)
            return _done(argv, stdout=json.dumps({"id": f"I_{argv[3]}"}))
        if argv[1:3] == ["repo", "view"]:
            self.calls.append(argv)
            return _done(argv, stdout=json.dumps({"nameWithOwner": self.repository}))
        if argv[1:3] == ["issue", "list"]:
            self.calls.append(argv)
            return self._list(argv)
        return super().gh(argv)

    def _project(self, argv: list[str]) -> subprocess.CompletedProcess[str]:
        verb = argv[2]
        owner = _option(argv, "--owner") or VIEWER
        if verb in ("view", "field-list", "item-add") and owner != self.owner:
            number = argv[3]
            stderr = f"GraphQL: Could not resolve to a ProjectV2 with the number {number}."
            return _done(argv, 1, stderr=stderr)
        if verb == "view":
            return _done(argv, stdout=json.dumps({"id": PROJECT_ID, "number": 4}))
        if verb == "field-list":
            if "fields" in self.fail_reads:
                return _done(argv, 1, stderr="missing required scopes [read:project]")
            status = {
                "id": STATUS_FIELD_ID,
                "name": self.field_name,
                "type": self.field_type,
                "options": [{"id": oid, "name": name} for name, oid in self.options.items()],
            }
            title = {"id": "PVTF_title", "name": "Title", "type": "ProjectV2Field"}
            return _done(argv, stdout=json.dumps({"fields": [title, status]}))
        if verb == "item-edit":
            return self._edit_card(argv)
        if verb == "item-add":
            number = int(str(_option(argv, "--url")).rsplit("/", 1)[1])
            if number in self.fail_adds:
                return _done(argv, 1, stderr="HTTP 502: Bad Gateway")
            self.adds.append(number)
            self.card(number)
            return _done(argv, stdout=json.dumps({"id": self.cards[number]["id"]}))
        raise AssertionError(f"unexpected gh project call: {argv}")

    def _edit_card(self, argv: list[str]) -> subprocess.CompletedProcess[str]:
        assert _option(argv, "--project-id") == PROJECT_ID
        assert _option(argv, "--field-id") == STATUS_FIELD_ID
        item = _option(argv, "--id")
        number = next(n for n, card in self.cards.items() if card["id"] == item)
        if number in self.fail_edits:
            return _done(argv, 1, stderr="HTTP 502: Bad Gateway")
        option = _option(argv, "--single-select-option-id")
        name = next(name for name, oid in self.options.items() if oid == option)
        self.cards[number]["status"] = name
        self.edits.append((number, name))
        return _done(argv)

    def _graphql(self, argv: list[str]) -> subprocess.CompletedProcess[str]:
        query = str(_field(argv, "query"))
        if "projectItems" in query:
            if "card" in self.fail_reads:
                return _done(argv, 1, stderr="HTTP 502: Bad Gateway")
            number = int(str(_field(argv, "issue")).removeprefix("I_"))
            nodes = (
                [{"id": self.cards[number]["id"], "project": {"id": PROJECT_ID}}]
                if number in self.cards
                else []
            )
            return _done(
                argv, stdout=json.dumps({"data": {"node": {"projectItems": {"nodes": nodes}}}})
            )
        if "items(first" in query:
            if "items" in self.fail_reads:
                return _done(argv, 1, stderr="missing required scopes [read:project]")
            nodes = [self._card_node(n) for n in sorted(self.cards)] + self.foreign_cards
            page = {"pageInfo": {"hasNextPage": False, "endCursor": None}, "nodes": nodes}
            return _done(argv, stdout=json.dumps({"data": {"node": {"items": page}}}))
        raise AssertionError(f"unexpected gh api graphql call: {argv}")

    def _card_node(self, number: int) -> dict[str, Any]:
        card = self.cards[number]
        issue = self.issues[number]
        status = card["status"]
        value = {"optionId": self.options[status], "name": status} if status else None
        return {
            "id": card["id"],
            "content": {
                "__typename": "Issue",
                "number": number,
                "title": issue["title"],
                "body": issue["body"],
                "state": issue["state"],
                "repository": {"nameWithOwner": self.repository},
            },
            "fieldValueByName": value,
        }

    def _list(self, argv: list[str]) -> subprocess.CompletedProcess[str]:
        """`gh issue list`, honouring `--state` and giving each issue its url."""
        state = _option(argv, "--state") or "open"
        fields = str(_option(argv, "--json")).split(",")
        rows = []
        for number, issue in self.issues.items():
            if state != "all" and issue["state"].lower() != state:
                continue
            row = {
                "number": number,
                "title": issue["title"],
                "body": issue["body"],
                "state": issue["state"],
                "labels": [{"name": name} for name in issue["labels"]],
                "milestone": issue["milestone"],
                "url": f"https://github.com/{self.repository}/issues/{number}",
            }
            rows.append({field: row[field] for field in fields})
        return _done(argv, stdout=json.dumps(rows))


def foreign_card(item_id: str, kind: str, number: int | None, repository: str = "") -> dict:
    """A card the board carries for something other than this repository's issue."""
    content: dict[str, Any] = {"__typename": kind, "title": kind}
    if number is not None:
        content["number"] = number
    if kind == "Issue":
        content.update(state="OPEN", body="", repository={"nameWithOwner": repository})
    return {"id": item_id, "content": content, "fieldValueByName": None}
