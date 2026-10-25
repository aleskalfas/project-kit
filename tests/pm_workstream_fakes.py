"""Fakes for the workstream mutators' `gh` calls (#1940): a repository and a board.

`FakeRepo` stands in for the repository's labels, issues, pull requests and
comments, answering the `gh` commands the mutators run through `gh_run`.
`FakeBoard` stands in for a Projects-v2 board with a `Workstream` single-select
field. It answers the board read seam's calls (`_lib/board_fields`, patched at
its `gh_project_run` / `gh_run`) and the write seam's (`_lib/substrate_writes`,
patched at its `_gh_call`), and it applies each write, so a read after a write
sees it. Nothing here touches a network.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any


def _proc(cmd, stdout: str = "", *, returncode: int = 0, stderr: str = ""):
    return subprocess.CompletedProcess(cmd, returncode, stdout=stdout, stderr=stderr)


def _flag(cmd: list[str], name: str) -> str | None:
    return cmd[cmd.index(name) + 1] if name in cmd else None


def stage_project(cap_root: Path, workstreams: str, *, board: bool = False) -> None:
    """A bootstrapped capability tree with `workstreams` as its workstreams.yaml."""
    project = cap_root / "project"
    project.mkdir(parents=True, exist_ok=True)
    config = "schema_version: 1\ndefault_branch: main\nworkstreams: []\n"
    if board:
        config += "has_projects_v2_board: true\nprojects_v2_board_id: 7\n"
    (project / "config.yaml").write_text(config, encoding="utf-8")
    (project / "bootstrap-stamp.yaml").write_text(
        "schema_version: 1\n"
        "bootstrap:\n"
        "  completed_at: '2026-01-01T00:00:00+00:00'\n"
        "  capability_version: 0.0.0-test\n"
        "  by: bootstrap\n"
        "  repo:\n",
        encoding="utf-8",
    )
    (project / "workstreams.yaml").write_text(workstreams, encoding="utf-8")


class FakeRepo:
    """A repository's labels, issues and comments, behind the `gh` commands.

    `issues` maps a number to `{"title", "labels", "body", "author"}`, and
    `comments` maps a number to a list of `{"id", "body", "login"}`.
    """

    def __init__(
        self,
        *,
        labels=(),
        issues=None,
        comments=None,
        login: str = "me",
        admin: bool = False,
        fail_edit: set[int] | None = None,
        fail_delete: set[str] | None = None,
    ) -> None:
        self.labels = set(labels)
        self.issues = issues or {}
        self.comments = comments or {}
        self.login = login
        self.admin = admin
        self.fail_edit = fail_edit or set()
        self.fail_delete = fail_delete or set()
        self.calls: list[list[str]] = []
        self.patched: dict[str, str] = {}

    def mutations(self) -> list[list[str]]:
        """Every call that would change the repository."""
        return [
            c
            for c in self.calls
            if c[1:3] in (["label", "create"], ["label", "edit"], ["label", "delete"])
            or c[1:3] == ["issue", "edit"]
            or "PATCH" in c
        ]

    def __call__(self, cmd, config, *, check=True, **kwargs):
        cmd = list(cmd)
        self.calls.append(cmd)
        verb = cmd[1:3]
        if verb == ["label", "list"]:
            return _proc(cmd, json.dumps([{"name": n} for n in sorted(self.labels)]))
        if verb == ["label", "create"]:
            if cmd[3] in self.labels:
                return _proc(cmd, returncode=1, stderr=f"label {cmd[3]} already exists")
            self.labels.add(cmd[3])
            return _proc(cmd)
        if verb == ["label", "edit"]:
            old, new = cmd[3], _flag(cmd, "--name")
            if old not in self.labels:
                return _proc(cmd, returncode=1, stderr="label not found")
            if new in self.labels:
                return _proc(cmd, returncode=1, stderr="Validation Failed: already_exists")
            self.labels.discard(old)
            self.labels.add(new)
            for issue in self.issues.values():
                if old in issue["labels"]:
                    issue["labels"] = [new if x == old else x for x in issue["labels"]]
            return _proc(cmd)
        if verb == ["label", "delete"]:
            if cmd[3] in self.fail_delete:
                return _proc(cmd, returncode=1, stderr="HTTP 502")
            self.labels.discard(cmd[3])
            for issue in self.issues.values():
                issue["labels"] = [x for x in issue["labels"] if x != cmd[3]]
            return _proc(cmd)
        if verb == ["issue", "list"] and "--label" in cmd:
            label = _flag(cmd, "--label")
            hits = [
                {"number": n, "title": i["title"]}
                for n, i in sorted(self.issues.items())
                if label in i["labels"]
            ]
            return _proc(cmd, json.dumps(hits))
        if verb in (["issue", "list"], ["pr", "list"]) and "--search" in cmd:
            if verb == ["pr", "list"]:
                return _proc(cmd, "[]")
            phrase = (_flag(cmd, "--search") or "").strip('"')
            hits = [
                {"number": n, "body": i.get("body", ""), "author": {"login": i.get("author", "")}}
                for n, i in sorted(self.issues.items())
                if phrase in i.get("body", "")
                or any(phrase in c["body"] for c in self.comments.get(n, []))
            ]
            return _proc(cmd, json.dumps(hits))
        if verb == ["issue", "edit"]:
            number = int(cmd[3])
            if number in self.fail_edit:
                return _proc(cmd, returncode=1, stderr="HTTP 502")
            issue = self.issues[number]
            add, remove = _flag(cmd, "--add-label"), _flag(cmd, "--remove-label")
            issue["labels"] = [x for x in issue["labels"] if x != remove] + [add]
            return _proc(cmd)
        if cmd[1] == "api":
            return self._api(cmd, kwargs)
        raise AssertionError(f"unexpected gh call: {cmd}")

    def _api(self, cmd, kwargs):
        if cmd[2] == "user":
            return _proc(cmd, self.login + "\n")
        if cmd[2] == "repos/{owner}/{repo}":
            return _proc(cmd, "true\n" if self.admin else "false\n")
        if "PATCH" in cmd:
            endpoint = cmd[cmd.index("PATCH") + 1]
            body = json.loads(kwargs["input"])["body"]
            self.patched[endpoint] = body
            return _proc(cmd)
        match = re.fullmatch(r"repos/\{owner\}/\{repo\}/issues/(\d+)/comments", cmd[2])
        if match:
            lines = [json.dumps(c) for c in self.comments.get(int(match.group(1)), [])]
            return _proc(cmd, "\n".join(lines))
        raise AssertionError(f"unexpected gh api call: {cmd}")


_OPTION = re.compile(
    r'\{(?:id: ("(?:[^"\\]|\\.)*"), )?name: ("(?:[^"\\]|\\.)*"), '
    r'color: (\w+), description: ("(?:[^"\\]|\\.)*")\}'
)


class FakeBoard:
    """A Projects-v2 board with a `Workstream` single-select field.

    `cards` maps an item id to `(issue number, option name or None)`.
    """

    def __init__(
        self,
        options=(),
        cards=None,
        *,
        field_type: str = "ProjectV2SingleSelectField",
        has_field: bool = True,
        fail_reads: bool = False,
    ) -> None:
        self.options = [
            {"id": f"opt_{name}", "name": name, "color": "GRAY", "description": ""}
            for name in options
        ]
        self.cards = {
            item: {"number": number, "option_id": f"opt_{name}" if name else None}
            for item, (number, name) in (cards or {}).items()
        }
        self.field_type = field_type
        self.has_field = has_field
        self.fail_reads = fail_reads
        self.writes: list[list[str]] = []
        self._next = 0

    def install(self, monkeypatch, board_fields, substrate_writes) -> None:
        monkeypatch.setattr(board_fields, "gh_project_run", self.read)
        monkeypatch.setattr(board_fields, "gh_run", self.read)
        monkeypatch.setattr(substrate_writes, "_gh_call", self.write)

    def option_names(self) -> list[str]:
        return [o["name"] for o in self.options]

    def card_option(self, item_id: str) -> str | None:
        oid = self.cards[item_id]["option_id"]
        return next((o["name"] for o in self.options if o["id"] == oid), None)

    def read(self, cmd, config, *, fallback_owner=None, check=False, **kwargs):
        cmd = list(cmd)
        if self.fail_reads:
            return _proc(cmd, returncode=1, stderr="missing the read:project scope")
        if cmd[1:3] == ["project", "view"]:
            return _proc(cmd, json.dumps({"id": "PVT_1"}))
        if cmd[1:3] == ["project", "field-list"]:
            fields: list[dict[str, Any]] = [
                {"id": "F_title", "name": "Title", "type": "ProjectV2Field"}
            ]
            if self.has_field:
                fields.append(
                    {
                        "id": "F_ws",
                        "name": "Workstream",
                        "type": self.field_type,
                        "options": [{"id": o["id"], "name": o["name"]} for o in self.options],
                    }
                )
            return _proc(cmd, json.dumps({"fields": fields}))
        query = next(a for a in cmd if a.startswith("query="))
        if "options { id name color description }" in query:
            return _proc(cmd, json.dumps({"data": {"node": {"options": self.options}}}))
        if "items(first: 100" in query:
            nodes = [
                {
                    "id": item,
                    "content": {"number": card["number"], "title": f"Issue {card['number']}"},
                    "fieldValueByName": {"optionId": card["option_id"]}
                    if card["option_id"]
                    else None,
                }
                for item, card in self.cards.items()
            ]
            payload = {
                "data": {
                    "node": {
                        "items": {
                            "pageInfo": {"hasNextPage": False, "endCursor": None},
                            "nodes": nodes,
                        }
                    }
                }
            }
            return _proc(cmd, json.dumps(payload))
        raise AssertionError(f"unexpected board read: {cmd}")

    def write(self, cmd, config):
        cmd = list(cmd)
        self.writes.append(cmd)
        if cmd[1:3] == ["project", "item-edit"]:
            self.cards[_flag(cmd, "--id")]["option_id"] = _flag(cmd, "--single-select-option-id")
            return _proc(cmd)
        query = cmd[4].removeprefix("query=")
        assert "updateProjectV2Field" in query
        options = []
        for oid, name, color, description in _OPTION.findall(query):
            if not oid:
                self._next += 1
                oid = json.dumps(f"opt_new{self._next}")
            options.append(
                {
                    "id": json.loads(oid),
                    "name": json.loads(name),
                    "color": color,
                    "description": json.loads(description),
                }
            )
        kept = {o["id"] for o in options}
        for card in self.cards.values():
            if card["option_id"] not in kept:
                card["option_id"] = None
        self.options = options
        return _proc(cmd)
