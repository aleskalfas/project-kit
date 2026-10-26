"""An in-memory GitHub for instance ownership's claims and releases.

`FakeGitHub` answers the `gh` calls `_lib/instance_claims` makes — one read of an
issue (`gh issue view --json assignees,labels,comments,body`), an event comment,
a label added or removed, a label created and a body written from a file — over
issues it holds in memory. Every comment it is handed is authored by `author`,
as GitHub authors a comment by the account `gh` runs as. No test reaches GitHub.

`on_view` runs before each read of an issue, with the issue's number and how
many times it was read before: a test posts another clone's claim there to stand
for a claim made in the same instant. `failing` holds the verbs whose next call
fails once (`"comment"`, `"add-label"`, `"remove-label"`, `"body"`, `"view"`,
`"label-create"`). With `labels_must_exist`, adding a label the repository does
not hold fails, as GitHub refuses it.

`use(module, monkeypatch, fake)` routes a loaded `instance_claims` through the
fake, and `clone_with(module, monkeypatch, instance)` gives every caller of
`this_clone` that instance id, with no file written under the real capability.

A project with a topology of seats (DEC-059) is stood in for in two parts.
`topology_with(module, monkeypatch, topology)` gives every `this_clone` that
reading of the topology, as the module that reads it (#2140, #2141) will.
`stub_seat_stamps(ownership, monkeypatch)` stands in for the audit-log
facility's builder and parser of a stamp that names a seat (#2138), with a stamp
of the tests' own that the stub parser reads back.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest


@dataclass
class FakeIssue:
    assignees: list[str]
    labels: list[str]
    comments: list[dict[str, Any]]
    body: str


@dataclass
class FakeGitHub:
    author: str = "me"
    issues: dict[int, FakeIssue] = field(default_factory=dict)
    repo_labels: set[str] = field(default_factory=set)
    labels_must_exist: bool = False
    failing: set[str] = field(default_factory=set)
    calls: list[list[str]] = field(default_factory=list)
    on_view: Callable[[int, int], None] | None = None
    views: dict[int, int] = field(default_factory=dict)

    def add(
        self,
        number: int,
        *,
        assignees: tuple[str, ...] = ("me",),
        labels: tuple[str, ...] = (),
        comments: tuple[dict[str, Any], ...] = (),
        body: str = "## What\n\nx\n",
    ) -> FakeIssue:
        issue = FakeIssue(list(assignees), list(labels), list(comments), body)
        self.issues[number] = issue
        return issue

    def post(self, number: int, body: str, author: str | None = None) -> None:
        """A comment on the issue, authored by `author` (the fake's own by default),
        with the authorship fields an audit writer's retry reads."""
        login = author or self.author
        self.issues[number].comments.append(
            {
                "author": {"login": login},
                "body": body,
                "viewerDidAuthor": login == self.author,
                "includesCreatedEdit": False,
            }
        )

    def writes(self) -> list[list[str]]:
        """Every call that changed something: all but the reads."""
        return [argv for argv in self.calls if argv[1:3] != ["issue", "view"]]

    def __call__(self, argv: list[str]) -> subprocess.CompletedProcess[str]:
        argv = [str(a) for a in argv]
        self.calls.append(argv)
        if argv[1:3] == ["label", "create"]:
            if self._fails("label-create"):
                return _done(argv, 1, stderr="HTTP 403: Must have admin rights")
            self.repo_labels.add(argv[3])
            return _done(argv)
        assert argv[1] == "issue", f"unexpected gh call: {argv}"
        verb, number = argv[2], int(argv[3])
        issue = self.issues[number]
        if verb == "view":
            seen = self.views.get(number, 0)
            self.views[number] = seen + 1
            if self.on_view is not None:
                self.on_view(number, seen)
            if self._fails("view"):
                return _done(argv, 1, stderr="HTTP 502: Bad Gateway")
            record = {
                "assignees": [{"login": a} for a in issue.assignees],
                "labels": [{"name": n} for n in issue.labels],
                "comments": list(issue.comments),
                "body": issue.body,
            }
            fields = argv[argv.index("--json") + 1].split(",")
            return _done(argv, stdout=json.dumps({f: record[f] for f in fields}))
        if verb == "comment":
            if self._fails("comment"):
                return _done(argv, 1, stderr="HTTP 502: Bad Gateway")
            self.post(number, argv[argv.index("--body") + 1])
            return _done(argv)
        if verb == "edit":
            return self._edit(argv, issue)
        raise AssertionError(f"unexpected gh call: {argv}")

    def _edit(self, argv: list[str], issue: FakeIssue) -> subprocess.CompletedProcess[str]:
        if "--add-label" in argv:
            name = argv[argv.index("--add-label") + 1]
            if self._fails("add-label"):
                return _done(argv, 1, stderr="HTTP 502: Bad Gateway")
            if self.labels_must_exist and name not in self.repo_labels:
                return _done(argv, 1, stderr=f"could not add label: '{name}' not found")
            issue.labels.append(name)
            return _done(argv)
        if "--remove-label" in argv:
            if self._fails("remove-label"):
                return _done(argv, 1, stderr="HTTP 502: Bad Gateway")
            name = argv[argv.index("--remove-label") + 1]
            if name in issue.labels:
                issue.labels.remove(name)
            return _done(argv)
        if "--body-file" in argv:
            if self._fails("body"):
                return _done(argv, 1, stderr="HTTP 502: Bad Gateway")
            issue.body = Path(argv[argv.index("--body-file") + 1]).read_text(encoding="utf-8")
            return _done(argv)
        raise AssertionError(f"unexpected gh issue edit: {argv}")

    def _fails(self, verb: str) -> bool:
        if verb in self.failing:
            self.failing.discard(verb)
            return True
        return False


def _done(argv: list[str], rc: int = 0, stdout: str = "", stderr: str = ""):
    return subprocess.CompletedProcess(argv, rc, stdout, stderr)


def use(module: Any, monkeypatch: pytest.MonkeyPatch, fake: FakeGitHub) -> None:
    """Route every `gh` call of the loaded `instance_claims` module through `fake`."""
    monkeypatch.setattr(module, "_gh", lambda args, _config: fake(args))


def clone_with(module: Any, monkeypatch: pytest.MonkeyPatch, instance: int | None) -> None:
    """Every `this_clone` reads `instance` as this clone's id (None: no id set),
    whatever file the capability root holds."""
    monkeypatch.setattr(module, "read_instance_id", lambda _root: instance)


def topology_with(module: Any, monkeypatch: pytest.MonkeyPatch, topology: Any) -> None:
    """Every `this_clone` of the loaded `instance_claims` reads `topology` as the
    run's reading of the project's topology (None: the project has none)."""
    monkeypatch.setattr(module, "read_topology", lambda _root, _config: topology)


#: The opening of the tests' own stamp that names a seat.
SEAT_STAMP_OPENING = "<!-- test-seat-stamp "


def stub_seat_stamps(ownership: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    """Stand in for the builder and the parser of a stamp that names a seat,
    the audit-log facility's (#2138), in the loaded `instance_ownership`."""

    def build(stamp: Any) -> str:
        to = f" to={stamp.to}" if stamp.to is not None else ""
        return (
            f"{SEAT_STAMP_OPENING}event={stamp.event} instance={stamp.instance} "
            f"seat={stamp.seat} key={stamp.key}{to} -->"
        )

    def read(body: str) -> Any:
        if SEAT_STAMP_OPENING not in body:
            return None
        inner = body.split(SEAT_STAMP_OPENING, 1)[1].split(" -->", 1)[0]
        fields = dict(part.split("=", 1) for part in inner.split())
        return ownership.SeatStamp(
            fields["event"],
            int(fields["instance"]),
            fields["seat"],
            fields["key"],
            int(fields["to"]) if "to" in fields else None,
        )

    monkeypatch.setattr(ownership, "build_seat_stamp", build)
    monkeypatch.setattr(ownership, "read_seat_stamp", read)
