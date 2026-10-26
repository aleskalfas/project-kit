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
`this_clone` that instance id, with no file written under the real capability,
in a project whose default branch declares no topology.

A project with a topology of seats (DEC-059) is stood in for by
`topology_with(module, monkeypatch, topology, key)`: every `this_clone` reads
that reading of the topology, as `read_topology` builds it from one run's
snapshot, and `key` as this clone's key, as its runtime file keeps it, beside
the name of the seat the reading gives. The stamp that names a seat is the
audit-log facility's own.
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
    whatever file the capability root holds, and the default branch as one that
    declares no topology."""
    monkeypatch.setattr(module, "read_instance_id", lambda _root: instance)
    monkeypatch.setattr(module, "_snapshot", lambda _root, _config, _login: None)


#: The versions a snapshot's footers name.
_VERSIONS = {"tree": "1.2.3", "capability": "0.9.0", "cli": "1.2.3"}


def seat_issue(
    module: Any, repo: Any, number: int, name: str, holder: tuple[str, str] | None = None
) -> None:
    """The state issue `number` of the seat `name`, in `repo` (a
    `pm_state_issue_fakes.FakeRepo`), held by the clone `holder`, an account and
    a key, where given."""
    si = module.state_issues
    versions = module.provenance.Versions(**_VERSIONS)
    repo.add(number, si.description("seat", name, si.Fold(None), versions), title=f"Seat {name}")
    repo.post(number, si.marker_comment("seat", name, versions))
    if holder is not None:
        account, key = holder
        claim = si.audit_log.event(si.CLAIM, key=name, clone=key, place="host:/clone")
        repo.post(number, si.audit_log.build(claim, versions=versions), author=account)


def seat_snapshot(
    module: Any,
    doc: dict[str, Any],
    repo: Any,
    *,
    login: str = "me",
    key: str = "k2",
    writers: tuple[str, ...] = ("me", "you"),
) -> Any:
    """One run's snapshot of the topology `doc` declares, as the default branch
    holds it, its seats' state issues in `repo`, for this clone of `login` with
    `key`. `writers` are the members who may write on a state issue."""
    tp, si = module.topology, module.state_issues
    topology = tp.parse(doc, ref="origin/main", commit="c0ffee")
    run = si.StateRun(repo, si.Writers.closed(writers), module.provenance.Versions(**_VERSIONS))
    return tp.Snapshot(topology, run, si.Clone(login, key, "host:/clone"))


def snapshot_with(
    module: Any,
    monkeypatch: pytest.MonkeyPatch,
    snapshot: Any,
    *,
    hint: str | None,
    key: str | None = "k2",
) -> None:
    """Every `this_clone` of the loaded `instance_claims` reads `snapshot` as the
    run's snapshot (None: the default branch declares no topology), `hint` as the
    seat its runtime file names and `key` as its key. The run starts with no
    commit named, and the commit it names is forgotten after the test."""
    monkeypatch.setenv(module.topology.NAMED_ENV, "")
    monkeypatch.setattr(module, "_snapshot", lambda _root, _config, _login: snapshot)
    monkeypatch.setattr(module, "read_seat_hint", lambda _root: hint)
    monkeypatch.setattr(module, "read_clone_key", lambda _root: key)
    monkeypatch.setattr(module, "clear_seat_hint", lambda _root: hint is not None)


def topology_with(
    module: Any, monkeypatch: pytest.MonkeyPatch, topology: Any, key: str | None = None
) -> None:
    """Every `this_clone` of the loaded `instance_claims` reads `topology` as the
    run's reading of the project's topology (None: the project has none), and
    `key` as this clone's key (None: its runtime file keeps none). The clone took
    the seat the reading gives, where it gives one."""
    seat = getattr(topology, "seat", None)
    monkeypatch.setattr(module, "read_topology", lambda _root, _config, **_kw: topology)
    monkeypatch.setattr(module, "read_clone_key", lambda _root: key)
    monkeypatch.setattr(module, "read_seat_hint", lambda _root: seat.name if seat else None)
