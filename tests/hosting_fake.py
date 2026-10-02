"""One fake of the hosting service, and of the clone and session a landing runs in.

A pull request lands through `done-work`, `merge-pr` and `pkit release merge`
(and `land-work`, which composes `done-work`), each asking `gh` and `git` from
its own code. This module answers all of it in this process, from one model:

- :class:`HostingService` is GitHub as `gh` reaches it: one pull request and
  its base — open, closed or merged; a head that can move; a base with or
  without a merge queue, the queue's merge method and the repository's
  squash-commit defaults; the PR queued, waiting to enter, or dropped at a
  head; a merge the service turns into an enqueue; auto-merge allowed or not;
  the remote branches, a protected one, and other open PRs on a branch. A
  queued PR moves on by one :data:`Step` per reading. A request can be
  refused, fail after it was made, or get no answer — made and the reply lost,
  or never received (:class:`NoAnswer`) — and a second actor can act before or
  after any request (:meth:`HostingService.before`, :meth:`~HostingService.after`).
  Every request is recorded, in order (:attr:`HostingService.requests`).
- :class:`LocalClone` is the clone the run is in: its branches and commits,
  and other repositories on the machine, which the cross-repository guards —
  project-management's and the backbone's — compare by their `git -C`
  answers, or find git not answering.
- :func:`install` routes every `subprocess.run` of `gh` and `git` to them, runs
  from the clone and sets the session anchor explicitly — the suite itself
  often runs inside a session that sets it. :func:`route_backbone` runs
  project-management's backbone seam in this process (`tests.pull_request_backbone`),
  ending a request the service never answers as the capability's bound ends
  it.

It merges what `test_pm_done_work.py`'s `_QUEUE_FAKE_GH` (a `gh` on PATH keeping
one PR and its queue) and `test_release_merge.py`'s `_Host` (the backbone's
`gh` in this process) model, so their tests can move onto it.
"""

from __future__ import annotations

import io
import json
import subprocess
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from project_kit import session_guard
from tests import pull_request_backbone

Completed = subprocess.CompletedProcess[str]

#: The session anchor: Claude Code's project directory, which
#: project-management's cross-repository guard and the backbone's compare with
#: the repository a mutation targets.
ANCHOR = session_guard.CLAUDE_CODE_ANCHOR

# ---- the requests, one kind each ----------------------------------------------

READ = "read"  # the GraphQL reading of the PR and its base's queue
DEFAULTS = "defaults"  # the repository's settings, read for its squash-commit defaults
MERGE = "merge"  # `gh pr merge --squash`
MERGE_ADMIN = "merge-admin"  # `gh pr merge --squash --admin`
ENQUEUE = "enqueue"  # `gh pr merge --auto`
DISABLE_AUTO = "disable-auto"  # `gh pr merge --disable-auto`
DEQUEUE = "dequeue"  # GitHub's `dequeuePullRequest` mutation
DELETE_REF = "delete-ref"  # `gh api -X DELETE …/git/refs/heads/<branch>`
VIEW = "view"  # `gh pr view`
LIST = "list"  # `gh pr list`
CHECKS = "checks"  # `gh pr checks`
ISSUE = "issue"  # `gh issue view`
ISSUE_MERGES = "issue-merges"  # the GraphQL read of the PRs that close an issue
UNKNOWN = "unknown"  # a request the fake does not model: answered with exit 1

#: The requests a landing makes of the service — the reading, the squash
#: defaults, the merge requests, the dequeue and the branch deletion — as
#: against the caller's own reads for its gates.
LANDING = frozenset(
    {READ, DEFAULTS, MERGE, MERGE_ADMIN, ENQUEUE, DISABLE_AUTO, DEQUEUE, DELETE_REF}
)

# ---- what became of a request ---------------------------------------------------

ANSWERED = "answered"
#: gh exits 1 with the service's reason; nothing was done.
REFUSED = "refused"
#: The request was made, then gh exited 1 — a 502 after the merge landed.
ERROR_AFTER = "made, then gh failed"
#: The request was made and the reply never came back (:class:`NoAnswer`).
LOST_REPLY = "made, no answer"
#: The request never reached the service, and nothing came back (:class:`NoAnswer`).
NEVER_RECEIVED = "not made, no answer"

_MERGED_AT = "2026-10-01T10:12:00Z"
_MERGE_COMMIT = "c0ffee" + "0" * 34


class NoAnswer(Exception):
    """`gh` sent the request, or tried to, and no answer came back: the run
    waits on it until something ends it."""


Step = Callable[["HostingService"], None]


@dataclass(frozen=True)
class Base:
    """A branch PRs merge into, and how."""

    queue: bool = False
    #: The queue's merge method: `SQUASH`, `MERGE` or `REBASE`.
    method: str = "SQUASH"


@dataclass
class OtherPullRequest:
    """Another PR whose head is one of this repository's branches."""

    number: int
    head_ref: str
    head_oid: str
    state: str = "OPEN"


@dataclass
class Request:
    """One request the service received, and what became of it."""

    kind: str
    argv: list[str]
    result: str = ANSWERED


@dataclass(frozen=True)
class _Fault:
    kind: str
    first: int
    #: How many occurrences from `first`; None, every one.
    count: int | None
    effect: str
    stderr: str

    def matches(self, kind: str, nth: int) -> bool:
        if kind != self.kind or nth < self.first:
            return False
        return self.count is None or nth < self.first + self.count


@dataclass(frozen=True)
class _Trigger:
    kind: str
    nth: int
    before: bool
    action: Step


@dataclass
class HostingService:
    """GitHub, as `gh` reaches it, holding one pull request and its base.

    Called as `gh` is (a runner of `["gh", ...]`). The PR's base is one of
    `bases`; the repository's squash-commit defaults are `squash_defaults`,
    None when the account cannot read the repository's settings. While the PR
    is queued — in the queue or held by auto-merge until it may enter — each
    reading first applies the next of `progress`.
    """

    number: int = 496
    title: str = "fix: land it"
    body: str = "Closes #42\n\n## Test plan\n\n- [x] It lands.\n"
    head_ref: str = "fix/42-land-it"
    head_oid: str = "sha-head"
    base: str = "main"
    state: str = "OPEN"
    merged_at: str = ""
    #: The head the PR merged at; empty until it merges.
    merged_head: str = ""
    merge_commit: str = ""
    cross_repository: bool = False
    draft: bool = False
    mergeable: str = "MERGEABLE"
    checks: list[dict[str, Any]] = field(
        default_factory=lambda: [
            {
                "__typename": "CheckRun",
                "name": "checks",
                "status": "COMPLETED",
                "conclusion": "SUCCESS",
            }
        ]
    )
    node_id: str = "PR_node"
    bases: dict[str, Base] = field(default_factory=lambda: {"main": Base()})
    squash_defaults: tuple[str, str] | None = ("PR_TITLE", "PR_BODY")
    #: The repository lets a PR be merged automatically once its checks pass.
    auto_merge_allowed: bool = True
    #: The PR's own required checks are still running when it is handed to the
    #: queue: auto-merge holds it until they pass.
    checks_pending: bool = False
    #: A direct merge enqueues, though the reading names no queue.
    merge_enqueues: bool = False

    in_queue: bool = False
    #: The PR's place and state in the queue; None before the queue reports one.
    entry: tuple[int, str] | None = None
    eta_seconds: int | None = 300
    #: Auto-merge holds the PR until its own checks pass.
    auto_merge: bool = False
    #: The queue's added and removed events on the PR, oldest first.
    timeline: list[dict[str, Any]] = field(default_factory=list)
    progress: list[Step] = field(default_factory=list)

    #: The remote branches and their tips.
    refs: dict[str, str] = field(default_factory=dict)
    #: Branches protected from deletion.
    protected: set[str] = field(default_factory=set)
    others: list[OtherPullRequest] = field(default_factory=list)
    #: The issue the PR closes, as `gh issue view` answers it.
    issue: dict[str, Any] = field(
        default_factory=lambda: {
            "number": 42,
            "title": "[Task] Land it",
            "labels": [{"name": "state:review"}],
            "body": "## Acceptance criteria\n\n- [x] It lands.\n",
            "state": "OPEN",
            "closedAt": None,
            "milestone": None,
        }
    )

    requests: list[Request] = field(default_factory=list)
    _seen: dict[str, int] = field(default_factory=dict)
    _faults: list[_Fault] = field(default_factory=list)
    _triggers: list[_Trigger] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.refs.setdefault(self.base, "sha-base")
        self.refs.setdefault(self.head_ref, self.head_oid)

    # ---- the PR, as GitHub keeps it ---------------------------------------

    @property
    def queued(self) -> bool:
        return self.in_queue or self.auto_merge

    def merge_now(self, head: str = "") -> None:
        """The PR merges — through the queue, or by someone else — at `head`
        (a push to it first) or at its head."""
        if head:
            self.push(head)
        self.state = "MERGED"
        self.merged_at = _MERGED_AT
        self.merged_head = self.head_oid
        self.merge_commit = _MERGE_COMMIT
        self._leave_queue()

    def push(self, oid: str) -> None:
        """A push to the PR's branch: its head moves to `oid`."""
        self.head_oid = oid
        if self.head_ref in self.refs:
            self.refs[self.head_ref] = oid

    def move_branch(self, oid: str) -> None:
        """The PR's head branch moves to `oid` after the PR merged, whose head
        stays the one it merged at."""
        self.refs[self.head_ref] = oid

    def close(self) -> None:
        self.state = "CLOSED"
        self._leave_queue()

    def enter_queue(self) -> None:
        """The queue takes the PR in."""
        self.in_queue = True
        self.auto_merge = False
        self.timeline.append({"__typename": "AddedToMergeQueueEvent"})

    def drop(self, reason: str = "failed checks") -> None:
        """The queue drops the PR at its head."""
        self._leave_queue()
        self.timeline.append(
            {
                "__typename": "RemovedFromMergeQueueEvent",
                "createdAt": "2026-10-01T10:05:00Z",
                "reason": reason,
                "beforeCommit": {"oid": self.head_oid},
            }
        )

    def dropped_before(self, reason: str = "failed checks") -> None:
        """The PR was in the queue once, and the queue dropped it at its head."""
        self.enter_queue()
        self.drop(reason)

    def retarget(self, base: str, rules: Base) -> None:
        """The PR's base becomes `base`, merging by `rules`."""
        self.bases[base] = rules
        self.base = base

    def set_base(self, rules: Base) -> None:
        """The PR's base comes to merge by `rules`."""
        self.bases[self.base] = rules

    def _leave_queue(self) -> None:
        self.in_queue = False
        self.entry = None
        self.auto_merge = False
        self.progress = []

    # ---- what a test scripts --------------------------------------------------

    def fail(
        self,
        kind: str,
        *,
        first: int | None = None,
        count: int | None = 1,
        stderr: str = "HTTP 502: Bad Gateway",
    ) -> None:
        """Refuse `count` requests of `kind` (None: every one) from the
        `first`th (None: the next): gh exits 1 with `stderr`."""
        self._add_fault(kind, first, count, REFUSED, stderr)

    def error_after(self, kind: str, *, stderr: str = "HTTP 502: Bad Gateway") -> None:
        """The next request of `kind` is made, then gh exits 1 with `stderr`."""
        self._add_fault(kind, None, 1, ERROR_AFTER, stderr)

    def lose_reply(self, kind: str) -> None:
        """The next request of `kind` is made, and its answer never comes back."""
        self._add_fault(kind, None, 1, LOST_REPLY, "")

    def never_receive(self, kind: str) -> None:
        """The next request of `kind` never reaches the service, and nothing
        comes back."""
        self._add_fault(kind, None, 1, NEVER_RECEIVED, "")

    def before(self, kind: str, action: Step, *, nth: int = 1) -> None:
        """Run `action` — a second actor, say — just before the `nth` request
        of `kind` is answered."""
        self._triggers.append(_Trigger(kind, nth, True, action))

    def after(self, kind: str, action: Step, *, nth: int = 1) -> None:
        """Run `action` just after the `nth` request of `kind` was answered."""
        self._triggers.append(_Trigger(kind, nth, False, action))

    def _add_fault(
        self, kind: str, first: int | None, count: int | None, effect: str, stderr: str
    ) -> None:
        start = first if first is not None else self._seen.get(kind, 0) + 1
        self._faults.append(_Fault(kind, start, count, effect, stderr))

    # ---- what a test reads ----------------------------------------------------

    def seen(self, kind: str) -> int:
        """How many requests of `kind` the service has received."""
        return self._seen.get(kind, 0)

    def kinds(self) -> list[str]:
        """The kind of every request, in order."""
        return [request.kind for request in self.requests]

    def landing(self) -> list[str]:
        """The kind of every request of the landing (:data:`LANDING`), in order."""
        return [kind for kind in self.kinds() if kind in LANDING]

    def remote_deletion(self) -> str:
        """What deleting the PR's head branch came to: `none` when it was not
        asked for; else what the last request to delete it did."""
        asked = [
            request
            for request in self.requests
            if request.kind == DELETE_REF and request.argv[-1].endswith(f"/heads/{self.head_ref}")
        ]
        return asked[-1].result if asked else "none"

    # ---- gh ----------------------------------------------------------------------

    def __call__(self, argv: Sequence[str]) -> Completed:
        args = [str(arg) for arg in argv]
        if args[:1] == ["gh"]:
            args = args[1:]
        kind = _kind(args)
        nth = self._seen[kind] = self._seen.get(kind, 0) + 1
        request = Request(kind, args)
        self.requests.append(request)
        self._fire(kind, nth, before=True)
        fault = next((f for f in self._faults if f.matches(kind, nth)), None)
        if fault is not None and fault.effect in (REFUSED, NEVER_RECEIVED):
            request.result = fault.effect
            if fault.effect == NEVER_RECEIVED:
                raise NoAnswer(f"`gh {' '.join(args[:3])}` got no answer")
            return _done(args, 1, stderr=fault.stderr)
        answered = self._answer(kind, args, request)
        self._fire(kind, nth, before=False)
        if fault is None:
            return answered
        request.result = fault.effect
        if fault.effect == LOST_REPLY:
            raise NoAnswer(f"`gh {' '.join(args[:3])}` got no answer")
        return _done(args, 1, stderr=fault.stderr)

    def _fire(self, kind: str, nth: int, *, before: bool) -> None:
        for trigger in list(self._triggers):
            if (trigger.kind, trigger.nth, trigger.before) == (kind, nth, before):
                self._triggers.remove(trigger)
                trigger.action(self)

    def _answer(self, kind: str, args: list[str], request: Request) -> Completed:
        if kind == READ:
            if self.queued and self.progress:
                self.progress.pop(0)(self)
            return _done(
                args, stdout=json.dumps({"data": {"repository": {"pullRequest": self._node()}}})
            )
        if kind == DEFAULTS:
            settings: dict[str, Any] = {"name": "project"}
            if self.squash_defaults is not None:
                title, message = self.squash_defaults
                settings.update(
                    squash_merge_commit_title=title, squash_merge_commit_message=message
                )
            return _done(args, stdout=json.dumps(settings))
        if kind in (MERGE, MERGE_ADMIN, ENQUEUE, DISABLE_AUTO):
            return self._pr_merge(kind, args)
        if kind == DEQUEUE:
            if not self.in_queue:
                return _done(args, 1, stderr="GraphQL: the pull request is not in a merge queue")
            self._leave_queue()
            return _done(args)
        if kind == DELETE_REF:
            return self._delete_ref(args, request)
        if kind == VIEW:
            return self._view(args)
        if kind == LIST:
            return self._list(args)
        if kind == CHECKS:
            checks = [{"name": c.get("name"), "state": c.get("conclusion")} for c in self.checks]
            return _done(args, stdout=json.dumps(checks))
        if kind == ISSUE:
            fields = (_option(args, "--json") or "").split(",")
            return _done(args, stdout=json.dumps({f: self.issue.get(f) for f in fields if f}))
        if kind == ISSUE_MERGES:
            merged = [self._merged_node()] if self.state == "MERGED" else []
            issue = {
                "closedByPullRequestsReferences": {"nodes": merged},
                "timelineItems": {"nodes": []},
            }
            return _done(args, stdout=json.dumps({"data": {"repository": {"issue": issue}}}))
        return _done(
            args, 1, stderr=f"the fake hosting service does not answer `gh {' '.join(args)}`"
        )

    def _pr_merge(self, kind: str, args: list[str]) -> Completed:
        """`gh pr merge`, as gh 2.x answers it: a PR in the queue is left as it
        is and gh exits 1; a merged PR is not merged again and gh exits 0; a
        merge or an enqueue pinned to another head than the PR's is refused."""
        if self.in_queue:
            return _done(
                args, 1, stderr=f"! Pull request #{self.number} is already queued to merge"
            )
        if kind == DISABLE_AUTO:
            self.auto_merge = False
            return _done(args)
        if self.state == "MERGED":
            return _done(args, stderr=f"! Pull request #{self.number} was already merged")
        if self.state == "CLOSED":
            return _done(args, 1, stderr="GraphQL: Pull request is closed (mergePullRequest)")
        pinned = _option(args, "--match-head-commit")
        if pinned and pinned != self.head_oid:
            return _done(
                args, 1, stderr="GraphQL: Head branch was modified. Review and try the merge again."
            )
        if kind == ENQUEUE:
            if not self.auto_merge_allowed:
                return _done(
                    args,
                    1,
                    stderr="GraphQL: Auto merge is not allowed for this repository "
                    "(enablePullRequestAutoMerge)",
                )
            if self.bases[self.base].queue and not self.checks_pending:
                self.enter_queue()
            else:
                self.auto_merge = True
            return _done(args)
        if (self.bases[self.base].queue or self.merge_enqueues) and kind != MERGE_ADMIN:
            # A base that requires a queue takes a plain merge as an enqueue.
            self.enter_queue()
            return _done(args)
        self.merge_now()
        return _done(args)

    def _delete_ref(self, args: list[str], request: Request) -> Completed:
        branch = args[-1].split("/git/refs/heads/", 1)[-1]
        if branch in self.protected:
            request.result = "refused, protected"
            return _done(args, 1, stderr="gh: Cannot delete this protected branch (HTTP 422)")
        if branch not in self.refs:
            request.result = "gone"
            return _done(args, 1, stderr="gh: Reference does not exist (HTTP 422)")
        tip = self.refs.pop(branch)
        result = "deleted"
        if branch == self.head_ref and tip != (self.merged_head or self.head_oid):
            result += f", tip {tip} moved"
        for other in self.others:
            if other.head_ref == branch and other.state == "OPEN":
                other.state = "CLOSED"
                result += f", closed #{other.number}"
        request.result = result
        return _done(args)

    def _node(self) -> dict[str, Any]:
        """The PR as the GraphQL reading answers it."""
        rules = self.bases[self.base]
        entry = None
        if self.in_queue and self.entry is not None:
            position, state = self.entry
            entry = {"position": position, "state": state, "estimatedTimeToMerge": self.eta_seconds}
        return {
            "id": self.node_id,
            "state": self.state,
            "mergedAt": self.merged_at or None,
            "headRefOid": self.head_oid,
            "isMergeQueueEnabled": rules.queue,
            "isInMergeQueue": self.in_queue,
            "mergeQueue": {"configuration": {"mergeMethod": rules.method}} if rules.queue else None,
            "mergeQueueEntry": entry,
            "autoMergeRequest": {"enabledAt": "2026-10-01T10:00:00Z"} if self.auto_merge else None,
            "timelineItems": {"nodes": list(self.timeline)},
        }

    def _view_fields(self) -> dict[str, Any]:
        """The PR as `gh pr view --json` answers it."""
        merged = self.state == "MERGED"
        return {
            "number": self.number,
            "title": self.title,
            "body": self.body,
            "state": self.state,
            "url": f"https://github.com/octo/project/pull/{self.number}",
            "headRefName": self.head_ref,
            "headRefOid": self.head_oid,
            "baseRefName": self.base,
            "isCrossRepository": self.cross_repository,
            "isDraft": self.draft,
            "mergeable": self.mergeable,
            "statusCheckRollup": self.checks,
            "mergedAt": self.merged_at or None,
            "mergeCommit": {"oid": self.merge_commit} if merged else None,
            "author": {"login": "author"},
            "closingIssuesReferences": [{"number": self.issue["number"]}],
        }

    def _merged_node(self) -> dict[str, Any]:
        view = self._view_fields()
        return {
            key: view[key]
            for key in (
                "number",
                "state",
                "mergedAt",
                "headRefName",
                "headRefOid",
                "isCrossRepository",
                "body",
            )
        }

    def _view(self, args: list[str]) -> Completed:
        if args[2:3] != [str(self.number)]:
            return _done(
                args, 1, stderr=f"GraphQL: Could not resolve to a PullRequest ({args[2:3]})"
            )
        view = self._view_fields()
        fields = (_option(args, "--json") or "").split(",")
        return _done(args, stdout=json.dumps({f: view.get(f) for f in fields if f}))

    def _list(self, args: list[str]) -> Completed:
        head, wanted = _option(args, "--head"), (_option(args, "--state") or "open").upper()
        fields = (_option(args, "--json") or "").split(",")
        found: list[dict[str, Any]] = []
        if self.head_ref == head and wanted in (self.state, "ALL"):
            found.append(self._view_fields())
        for other in self.others:
            if other.head_ref == head and wanted in (other.state, "ALL"):
                found.append(
                    {
                        **self._view_fields(),
                        "number": other.number,
                        "headRefOid": other.head_oid,
                        "state": other.state,
                    }
                )
        return _done(args, stdout=json.dumps([{f: pr.get(f) for f in fields if f} for pr in found]))


# ---- how a queued PR moves on, one step per reading --------------------------------


def at(position: int, state: str = "AWAITING_CHECKS") -> Step:
    """The PR at `position` in the queue, its entry `state`."""

    def step(host: HostingService) -> None:
        if not host.in_queue:
            host.enter_queue()
        host.entry = (position, state)

    return step


def lands() -> Step:
    """The queue merges the PR at its head."""

    def step(host: HostingService) -> None:
        host.merge_now()

    return step


def drops(reason: str = "failed checks") -> Step:
    """The queue drops the PR at its head."""

    def step(host: HostingService) -> None:
        host.drop(reason)

    return step


def pushes(oid: str) -> Step:
    """A push to the PR's branch while it is queued: its head moves to `oid`."""

    def step(host: HostingService) -> None:
        host.push(oid)

    return step


def unchanged() -> Step:
    """A reading that finds the PR as the one before did."""

    def step(host: HostingService) -> None:
        return None

    return step


# ---- the clone --------------------------------------------------------------------


@dataclass
class LocalClone:
    """The clone a run is in, as `git` answers for it, and the other
    repositories on the machine, which answer only who they are."""

    root: Path
    origin: str | None = "https://github.com/octo/project.git"
    branches: dict[str, str] = field(default_factory=dict)
    current: str | None = None
    #: Each commit the clone has, and its parent.
    commits: dict[str, str | None] = field(default_factory=dict)
    #: Other repositories: their root and their `origin`.
    elsewhere: dict[Path, str | None] = field(default_factory=dict)
    #: Branches checked out in another worktree: a checkout of one fails.
    held_elsewhere: set[str] = field(default_factory=set)
    #: git does not answer the cross-repository guards' questions — those it is
    #: asked about another directory (`git -C`) — in time.
    comparison_fault: bool = False
    calls: list[list[str]] = field(default_factory=list)
    deleted: list[str] = field(default_factory=list)
    checkouts: list[str] = field(default_factory=list)

    def local_deletion(self, branch: str) -> str:
        """What the local clean-up did with `branch`: `deleted`; `kept` or
        `absent` when a clean-up ran and did not delete it; `none` when none ran."""
        if branch in self.deleted:
            return "deleted"
        if not self.checkouts:
            return "none"
        return "kept" if branch in self.branches else "absent"

    def __call__(self, argv: Sequence[str], *, cwd: str | Path | None = None) -> Completed:
        args = [str(arg) for arg in argv][1:]
        where = Path(cwd) if cwd is not None else Path.cwd()
        if args[:1] == ["-C"]:
            if self.comparison_fault:
                raise subprocess.TimeoutExpired(["git", *args], 5)
            where, args = Path(args[1]), args[2:]
        self.calls.append(args)
        root, origin = self._repository(where)
        if root is None:
            return _done(
                args,
                128,
                stderr="fatal: not a git repository (or any of the parent directories): .git",
            )
        if args == ["rev-parse", "--show-toplevel"]:
            return _done(args, stdout=f"{root}\n")
        if args == ["rev-parse", "--git-common-dir"]:
            return _done(args, stdout=f"{root / '.git'}\n")
        if args == ["remote", "get-url", "origin"]:
            if origin is None:
                return _done(args, 2, stderr="error: No such remote 'origin'")
            return _done(args, stdout=f"{origin}\n")
        if root != self.root.resolve():
            return _done(args, 1, stderr=f"the fake clone answers only who {root} is")
        return self._in_clone(args)

    def _repository(self, where: Path) -> tuple[Path | None, str | None]:
        place = where.resolve()
        for root, origin in [(self.root, self.origin), *self.elsewhere.items()]:
            resolved = root.resolve()
            if place == resolved or resolved in place.parents:
                return resolved, origin
        return None, None

    def _in_clone(self, args: list[str]) -> Completed:
        if args[:2] == ["branch", "--list"]:
            return _done(args, stdout="".join(f"{name}\n" for name in self.branches))
        if args[:3] == ["rev-parse", "--verify", "--quiet"]:
            tip = self.branches.get(args[3].removeprefix("refs/heads/"))
            return _done(args, stdout=f"{tip}\n") if tip else _done(args, 1)
        if args[:2] == ["rev-list", "--count"]:
            older, _, newer = args[2].partition("..")
            ours, theirs = self._ancestry(newer), self._ancestry(older)
            if ours is None or theirs is None:
                return _done(args, 128, stderr=f"fatal: bad revision '{args[2]}'")
            return _done(args, stdout=f"{len(ours - theirs)}\n")
        if args[:2] == ["cat-file", "-e"]:
            return _done(args, 0 if args[2].removesuffix("^{commit}") in self.commits else 1)
        if args[:1] == ["for-each-ref"]:
            return _done(args, stdout="origin\n" if "upstream" in args[1] else "\n")
        if args[:3] == ["symbolic-ref", "--quiet", "--short"]:
            return _done(args, stdout=f"{self.current}\n") if self.current else _done(args, 1)
        if args[:1] == ["checkout"]:
            self.checkouts.append(args[1])
            if args[1] in self.held_elsewhere:
                return _done(args, 128, stderr=f"fatal: '{args[1]}' is already used by worktree")
            if args[1] not in self.branches:
                return _done(args, 1, stderr=f"error: pathspec '{args[1]}' did not match")
            self.current = args[1]
            return _done(args)
        if args[:1] in (["pull"], ["fetch"]):
            return _done(args)
        if args[:2] == ["branch", "-D"]:
            name = args[2]
            if name == self.current:
                return _done(args, 1, stderr=f"error: cannot delete branch '{name}' checked out")
            if self.branches.pop(name, None) is None:
                return _done(args, 1, stderr=f"error: branch '{name}' not found")
            self.deleted.append(name)
            return _done(args)
        return _done(args, 1, stderr=f"the fake clone does not run `git {' '.join(args)}`")

    def _ancestry(self, oid: str) -> set[str] | None:
        """`oid` and every commit before it, or None when the clone lacks it."""
        if oid not in self.commits:
            return None
        seen: set[str] = set()
        current: str | None = oid
        while current is not None and current not in seen:
            seen.add(current)
            current = self.commits.get(current)
        return seen


# ---- the session ------------------------------------------------------------------


class Terminal(io.StringIO):
    """Standard input from a terminal whose operator answers every question
    `answer`; :attr:`asked` counts the questions."""

    def __init__(self, answer: str = "y") -> None:
        super().__init__()
        self.answer = answer
        self.asked = 0

    def isatty(self) -> bool:
        return True

    def readline(self, size: int | None = -1) -> str:
        self.asked += 1
        return f"{self.answer}\n"


class Screen(io.StringIO):
    """Standard error on the terminal a :class:`Terminal`'s operator reads: a
    question is asked only where both ends are a terminal."""

    def isatty(self) -> bool:
        return True


class NoTerminal(io.StringIO):
    """Standard input that is not a terminal and holds nothing: a pipeline's,
    an agent's."""

    asked = 0

    def isatty(self) -> bool:
        return False


def install(
    monkeypatch: pytest.MonkeyPatch,
    host: HostingService,
    clone: LocalClone,
    *,
    anchor: Path | None,
    stdin: io.StringIO,
) -> None:
    """Answer every `gh` and `git` this process runs from `host` and `clone`;
    run from the clone, with standard input `stdin` — and, where that is a
    terminal, standard error on the same terminal (:class:`Screen`) — and the
    session anchor at `anchor` — None unsets it, as outside any session. Any
    other program a run starts fails the test: the scenario must not reach
    past the fakes."""

    def run(args: Sequence[str], *_: Any, **kwargs: Any) -> Completed:
        argv = [str(arg) for arg in args]
        if argv[:1] == ["gh"]:
            done = host(argv)
        elif argv[:1] == ["git"]:
            done = clone(argv, cwd=kwargs.get("cwd"))
        else:
            raise AssertionError(f"a landing scenario ran {argv}, which no fake answers")
        if kwargs.get("check") and done.returncode:
            raise subprocess.CalledProcessError(done.returncode, argv, done.stdout, done.stderr)
        return done

    monkeypatch.setattr(subprocess, "run", run)
    monkeypatch.chdir(clone.root)
    monkeypatch.setattr("sys.stdin", stdin)
    if stdin.isatty():
        monkeypatch.setattr("sys.stderr", Screen())
    if anchor is None:
        monkeypatch.delenv(ANCHOR, raising=False)
    else:
        monkeypatch.setenv(ANCHOR, str(anchor))


@dataclass
class Clock:
    """The waits' clock: each sleep advances it."""

    now: float = 0.0
    sleeps: list[float] = field(default_factory=list)

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


Rewrite = Callable[[list[str], dict[str, Any]], dict[str, Any]]


def route_backbone(
    monkeypatch: pytest.MonkeyPatch,
    mq: Any,
    clock: Clock,
    *,
    rewrite: Rewrite | None = None,
) -> None:
    """Run project-management's `pkit pull-request` seam (`mq._answers`) in this
    process, on the `gh` :func:`install` answers and `clock`.

    A request the service never answers (:class:`NoAnswer`) ends the run as
    project-management's bound ends it: no document, the reading pm takes as
    no answer. `rewrite`, handed the subcommand's arguments and each document,
    stands in for a backbone that answers otherwise.
    """
    pull_request_backbone.in_process(monkeypatch, mq, sleep=clock.sleep, clock=clock)
    inner = mq._answers

    def answers(
        args: list[str], config: dict[str, Any], *, timeout_seconds: float | None = None
    ) -> Iterator[dict[str, Any]]:
        bound = mq.TIMEOUT_SECONDS[args[0]] if timeout_seconds is None else timeout_seconds
        try:
            for document in inner(args, config, timeout_seconds=timeout_seconds):
                yield rewrite(args, document) if rewrite is not None else document
        except NoAnswer:
            raise mq.Unreadable(
                f"`pkit pull-request {args[0]}` gave no answer within {bound:g} s, and was stopped"
            ) from None

    monkeypatch.setattr(mq, "_answers", answers)


# ---- answering ----------------------------------------------------------------------


def _kind(args: list[str]) -> str:
    if args[:2] == ["pr", "merge"]:
        if "--disable-auto" in args:
            return DISABLE_AUTO
        if "--auto" in args:
            return ENQUEUE
        return MERGE_ADMIN if "--admin" in args else MERGE
    if args[:2] == ["api", "graphql"]:
        query = next((arg for arg in args if arg.startswith("query=")), "")
        if "dequeuePullRequest" in query:
            return DEQUEUE
        if "closedByPullRequestsReferences" in query:
            return ISSUE_MERGES
        if "pullRequest(number:" in query:
            return READ
        return UNKNOWN
    if args[:3] == ["api", "-X", "DELETE"] and "/git/refs/heads/" in args[-1]:
        return DELETE_REF
    if args[:2] == ["api", "repos/{owner}/{repo}"]:
        return DEFAULTS
    kinds: Mapping[tuple[str, str], str] = {
        ("pr", "view"): VIEW,
        ("pr", "list"): LIST,
        ("pr", "checks"): CHECKS,
        ("issue", "view"): ISSUE,
    }
    return kinds.get((args[0], args[1]) if len(args) > 1 else ("", ""), UNKNOWN)


def _option(args: list[str], name: str) -> str | None:
    return args[args.index(name) + 1] if name in args[:-1] else None


def _done(args: list[str], returncode: int = 0, *, stdout: str = "", stderr: str = "") -> Completed:
    return subprocess.CompletedProcess(args, returncode, stdout=stdout, stderr=stderr)
