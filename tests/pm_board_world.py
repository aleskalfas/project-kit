"""The in-memory tracker of `tests/pm_lifecycle_world.py`, with a Projects v2 board.

`BoardTracker` answers the `gh` calls the board's Status projection makes
(#2276): the project's id, its fields with the Status options, an issue's node
id, the cards of the issues a read lists by node id, every card with its Status,
a card added and a Status written. Each card is keyed by the issue it holds;
`foreign_cards` holds cards the board carries for other repositories, pull
requests and drafts.

The board has an owner, the repository's by default, and `gh` runs as someone
else. A `gh project` call that names no `--owner` looks among the boards of
whoever runs `gh`, as `gh` does, so it finds the board only under the owner it
names.

A config and a substrate map put the board in reach: `BOARD_CONFIG` configures
board #4, and `LABEL_STATE` binds the state to the kit's own labels, so the
board configured does not carry it (DEC-051) and its Status is a projection the
agent maintains (DEC-006). `STATE_ON_BOARD` binds the state to the board, so its
Status is the state's source (DEC-062 point 5).
"""

from __future__ import annotations

import json
import subprocess
from typing import Any

from tests.pm_board_graphql import GraphBoard, is_seam_read
from tests.pm_lifecycle_world import Tracker

PROJECT_ID = "PVT_board4"
STATUS_FIELD_ID = "PVTSSF_status"
REPOSITORY = "acme/repo"
#: The node id of this repository, by which a read of the board tells its issues.
REPOSITORY_ID = "R_repo"
#: The node id of the repository's old issue on the board, which only the
#: page of recent issues shows.
WITNESS_ID = "I_witness"
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

#: The state on the board, the other axes on the kit's own labels.
STATE_ON_BOARD: dict[str, Any] = {
    "type": {"kit-label": True},
    "priority": {"kit-label": True},
    "workstream": {"kit-label": True},
    "state": {"board": True},
}


def _done(argv: list[str], returncode: int = 0, stdout: str = "", stderr: str = ""):
    return subprocess.CompletedProcess(argv, returncode, stdout, stderr)


def _option(argv: list[str], flag: str) -> str | None:
    return argv[argv.index(flag) + 1] if flag in argv else None


def _field(argv: list[str], name: str) -> str | None:
    """The value of a `-f name=value` or `-F name=value` field of `gh api graphql`."""
    found = _fields(argv, name)
    return found[0] if found else None


def _fields(argv: list[str], name: str) -> list[str]:
    """Every value of a `-f name=value` or `-F name=value` field, in order, as
    `ids[]` passes a list."""
    return [
        argv[i + 1].split("=", 1)[1]
        for i, arg in enumerate(argv[:-1])
        if arg in ("-f", "-F") and argv[i + 1].startswith(f"{name}=")
    ]


class BoardTracker(Tracker):
    """The tracker, and board #4 with a single-select Status of `options`.

    `cards` maps an issue to its card: `{"id": <item id>, "status": <option name
    or None>, "archived": <bool>}`. `edits` lists each Status written, `(issue,
    option name)`.
    `fail_reads` names the board reads that fail (`fields`, `items`, `card`),
    `fail_edits` the issues whose Status write fails, and `fail_adds` those whose
    card cannot be added. `repository` is this repository's `owner/name`, and
    `owner` the board's owner, the repository's unless a test sets another.

    The board answers the seam's GraphQL reads through `graph`
    (`tests/pm_board_graphql.py`), reading the cards held here: an issue's own
    cards, its repository, and the page of the repository's recent issues by
    number, highest first. `graph.placed` places an error on one part of a
    read, such as the page.

    As on a board in use, the repository holds one more issue on the board, an
    old one no test lists (`WITNESS_ID`): it falls last in the page of recent
    issues and shows a card, so a read sees that the board answers it, and an
    issue with no card is told as such (ADR-096 point 1). `graph.witness =
    False` takes it away, for a board whose cards the credential cannot see."""

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
        self.graph = _TrackerBoard(self)

    # --- what a test sets up ------------------------------------------------

    def card(self, number: int, status: str | None = None, *, archived: bool = False) -> None:
        """Put the issue on the board, its card's Status `status`, the card
        archived where `archived` is set. A walk of the board's cards reads an
        archived card only where it asks for one (`tests/pm_board_archive.py`)."""
        self.cards[number] = {"id": f"PVTI_{number}", "status": status, "archived": archived}

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
            identity = {"id": PROJECT_ID, "number": 4, "owner": {"login": self.owner}}
            return _done(argv, stdout=json.dumps(identity))
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
        if is_seam_read(argv):
            self.graph.failing = {
                part: words
                for read, part, words in (
                    ("fields", "fields", "missing required scopes [read:project]"),
                    ("card", "cards", "HTTP 502: Bad Gateway"),
                    ("items", "items", "missing required scopes [read:project]"),
                )
                if read in self.fail_reads
            }
            return self.graph.reply(argv)
        raise AssertionError(f"unexpected gh api graphql call: {argv}")

    def _value(self, number: int) -> dict[str, Any] | None:
        """The Status the issue's card holds, as GraphQL gives a single-select's
        value, or None for a card with none."""
        status = self.cards[number]["status"]
        return {"optionId": self.options[status], "name": status} if status else None

    def _card_node(self, number: int) -> dict[str, Any]:
        card = self.cards[number]
        issue = self.issues[number]
        value = self._value(number)
        return {
            "id": card["id"],
            "type": "ISSUE",
            "content": {
                "__typename": "Issue",
                "id": f"I_{number}",
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
                "id": f"I_{number}",
                "title": issue["title"],
                "body": issue["body"],
                "state": issue["state"],
                "labels": [{"name": name} for name in issue["labels"]],
                "assignees": [{"login": login} for login in issue.get("assignees") or []],
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
    kinds = {"Issue": "ISSUE", "PullRequest": "PULL_REQUEST", "DraftIssue": "DRAFT_ISSUE"}
    return {"id": item_id, "type": kinds[kind], "content": content, "fieldValueByName": None}


def withheld_card(item_id: str) -> dict:
    """A card whose issue lies in a repository the credential may not read: the
    board returns it with nothing of its issue (ADR-096 point 2)."""
    return {"id": item_id, "type": "REDACTED", "content": None, "fieldValueByName": None}


class _TrackerBoard(GraphBoard):
    """Board #4 as the tracker's cards make it, answering the seam's reads."""

    def __init__(self, tracker: BoardTracker) -> None:
        super().__init__(node=PROJECT_ID, number=4, owner=tracker.owner)
        self.tracker = tracker
        self.witness = True

    def identity(self) -> dict[str, Any]:
        self.owner = self.tracker.owner
        return super().identity()

    def reply(self, argv: list[str]) -> subprocess.CompletedProcess[str]:
        self.owner = self.tracker.owner
        return super().reply(argv)

    def fields(self) -> list[dict[str, Any]]:
        tracker = self.tracker
        status = {
            "id": STATUS_FIELD_ID,
            "name": tracker.field_name,
            "type": tracker.field_type,
            "options": [{"id": oid, "name": name} for name, oid in tracker.options.items()],
        }
        return [{"id": "PVTF_title", "name": "Title", "type": "ProjectV2Field"}, status]

    def own_cards(self, issue_id: str, value_field: str | None) -> list[dict[str, Any]] | None:
        if issue_id == WITNESS_ID:
            return [{"id": "PVTI_witness", "project": {"id": PROJECT_ID}}] if self.witness else []
        number = _number(issue_id)
        if number is None or number not in self.tracker.issues:
            return None
        if number not in self.tracker.cards:
            return []
        card: dict[str, Any] = {
            "id": self.tracker.cards[number]["id"],
            "project": {"id": PROJECT_ID},
        }
        if value_field is not None:
            card["fieldValueByName"] = self.tracker._value(number)
        return [card]

    def repository_of(self, issue_id: str) -> str | None:
        if issue_id == WITNESS_ID:
            return REPOSITORY_ID
        number = _number(issue_id)
        return REPOSITORY_ID if number is not None and number in self.tracker.issues else None

    def recent_issues(self, repository_id: str, order: str) -> list[str]:
        if repository_id != REPOSITORY_ID:
            return []
        numbers = sorted(self.tracker.issues, reverse=True)
        if order == "updated":
            numbers = [n for n in numbers if self.tracker.issues[n]["state"] == "OPEN"]
            return [f"I_{n}" for n in numbers]
        # The old issue is closed, so only the page's created order shows it.
        return [f"I_{n}" for n in numbers] + [WITNESS_ID]

    def walk(self, value_field: str | None, archived: bool) -> list[dict[str, Any]]:
        tracker = self.tracker
        walked = [
            number
            for number in sorted(tracker.cards)
            if archived or not tracker.cards[number]["archived"]
        ]
        return [tracker._card_node(n) for n in walked] + tracker.foreign_cards


def _number(issue_id: str) -> int | None:
    """The issue number a fake node id `I_<n>` names."""
    tail = issue_id.removeprefix("I_")
    return int(tail) if tail.isdigit() else None
