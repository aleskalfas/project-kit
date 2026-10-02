"""Landing a pull request on the hosting service: the one merge mechanic.

Where these acts live, what each caller keeps and the obligations every caller
holds are decided in ADR-061 ("Landing a pull request on the hosting service
lives once, in the backbone"); how a pull request lands is COR-009's.

A pull request lands as one squash commit on its base branch
(project-management's DEC-013, "Merge mechanics"). Where the base merges
through a merge queue, the queue makes that merge: it builds the merge the PR
would make on top of the base and of whatever is queued ahead of it, runs the
base's required checks on that prospective merge commit, and merges it once
they pass, by the queue's own merge method and with a squash commit composed
from the repository's squash-commit defaults. A PR whose checks fail there, or
that no longer merges cleanly, leaves the queue unmerged. Merging directly on
such a base goes around the queue.

Every step of a landing that talks to the hosting service lives here, once:

- **the reading** (:func:`read`) — whether the base has a queue and its merge
  method; whether the PR is in it, its position, state and estimated time to
  merge; whether auto-merge holds it until its own required checks pass; its
  head; whether it has merged; and whether the queue's last word on it was to
  drop it, at which head and why. One GraphQL read answers all of it. Only an
  API that does not know `isMergeQueueEnabled` itself answers that there is no
  queue: when the full read fails on some other unknown field, that field
  alone is asked for, and a host that knows it has queues, so the read is
  unreadable rather than "no queue";
- **the repository's squash-commit defaults** (:func:`squash_commit_defaults`),
  which a queue composes its squash commit from;
- **the direct squash merge** (:func:`squash_merge`) and **the enqueue**
  (:func:`enqueue`), each pinned to the head the caller checked;
- **the wait for the queue's merge** (:func:`wait_for_merge`), which declares
  a PR out of the queue only on two readings running and stops at once when
  the head moves;
- **taking a PR out of the queue** (:func:`dequeue`);
- **deleting a merged PR's head branch** (:func:`delete_branch`), only while
  its tip is the head the PR merged at, which the caller names, and no other
  open PR uses it as its head or its base — as one compare-and-delete
  request;
- **the landing sequence** (:func:`land`), which composes the steps above but
  the deletion: one reading, the caller's options applied to it, the
  request, the wait, and the dequeue when the head moved — ending in one
  document that states how it ended, so no caller derives it.

Merged is what GitHub reports, never what a command's exit implies: on a base
that requires a queue, a plain merge request enqueues and exits 0, so a caller
reads the PR again after a direct merge before it counts it merged.

When to land, and what follows a landing, is the caller's: the gates it runs,
what it refuses, its own steps after the merge, and when the head branch is
deleted — after those steps. The local branch is the caller's too: it is not
on the hosting service. project-management's merge verbs reach this module
through `pkit pull-request` and its JSON documents, since they run as scripts
that do not import the package; `pkit release merge` lands through
:func:`land`, by import.

The requests that change the service's state — the merge, the enqueue, the
dequeue, the branch deletion — run the cross-repository guard (ADR-061 point
6, `session_guard`): each requires a clearance and the directory it acts in,
and runs `gh` there, with no client of the caller's, so a caller that imports
them can neither skip the guard nor clear one directory and act in another.
A landing takes one clearance, at its caller's entry, and hands it to each
request it makes. The readings and the wait change nothing and run no guard.

`gh` is the hosting service's client here. Every call runs it from the
caller's directory — it resolves the repository from the git remote — with the
caller's environment, so a host pinned through `GH_HOST` reaches it, through
the command runner's one bounded start (`command_runner.run_bounded`): in the
caller's process group, so a caller that ends the group `pkit` runs in ends a
`gh` in flight too, and bounded per call — :data:`GH_READ_SECONDS` for a
reading, :data:`GH_REQUEST_SECONDS` for a request — past which `gh` alone is
ended. A reading past its bound is unreadable.

A request is refused only on an answer this module recognises as one
(:func:`_send`): the service's GraphQL errors, `gh`'s `GraphQL:` or `HTTP 4xx`
line but a 408, `gh`'s own refusal before it sent anything, or `gh` not
started at all.
Anything else — ended at its bound, ended by a signal, a server error, a
broken connection, nothing back, words this module does not know — is no
usable answer: the request may have been made, so it is settled by reading
(:func:`_settle`). Its end state seen, it was made. Not seen on two readings,
the second taken no sooner than :data:`SETTLE_WINDOW_SECONDS` after the
request was sent, it was **not seen made** (:data:`NOT_MADE`) — what the
readings saw, never that it was not made, since the service may still apply
it later; one reading never concludes even that. A reading that cannot be
taken leaves it unconfirmed (:data:`UNANSWERED`), stating nothing it does not
know (ADR-061 point 5, the third obligation, and point 7). Settling is said
on standard error as it starts, so whoever interrupts the command knows a
request is in flight.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from contextvars import ContextVar
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from project_kit import command_runner, session_guard

#: The version of the documents `pkit pull-request --json` writes; a reader
#: refuses one it does not know.
SCHEMA_VERSION = 1

#: The queue merge method that makes the convention's one squash commit.
SQUASH = "SQUASH"

#: The repository's squash-commit defaults the convention needs: the queue
#: composes the squash commit from them, not from the merge command.
PR_TITLE = "PR_TITLE"
PR_BODY = "PR_BODY"

#: The bound on one `gh` call, by kind: a reading — one GraphQL query, or one
#: REST read — and a request that changes the service — `gh pr merge`, which
#: makes several calls of its own, or a GraphQL mutation. Past it `gh` is
#: ended — asked to stop, then killed `command_runner.END_GRACE_SECONDS`
#: later: a reading is then unreadable, and a request has no answer
#: (:func:`_settle`). The longest each subcommand can run, every call at its
#: bound, is :func:`longest_seconds`, which stays below the bound
#: project-management puts on that subcommand (`_lib/merge_queue.py`'s
#: `TIMEOUT_SECONDS`), so its document comes back.
GH_READ_SECONDS = 15.0
GH_REQUEST_SECONDS = 30.0

#: The most `gh` calls one reading makes (:func:`read`): the full read and —
#: where the API does not know one of its fields — the probe for merge queues
#: and the read without the queue's fields.
CALLS_PER_READING = 3

#: How long after a request with no usable answer was sent its second
#: settling reading is taken, at the earliest, whichever way the answer went
#: missing — ended at its bound, or a server error back at once — so every
#: request gets the same window to show (:func:`_settle`). It rests on an
#: assumption about the hosting service: that a change it accepted shows in a
#: reading within this time of the request that asked for it. A change it
#: applies later than that is read as not seen made, and shows to the next
#: run that reads the pull request, which every caller's re-run does first.
SETTLE_WINDOW_SECONDS = 40.0

#: The least time between two readings that settle a request, so that two
#: readings are two moments, however late the first was taken.
SETTLE_INTERVAL_SECONDS = 10.0

#: How many times a dequeue is sent when the one before was not seen made:
#: it is idempotent, and it is what keeps commits nothing checked out of the
#: queue (:func:`dequeue`).
DEQUEUE_ATTEMPTS = 2

#: How long the wait sleeps between two readings.
POLL_SECONDS = 15.0

#: A wait that follows the queue's own estimate waits that long plus this
#: margin, and never longer than the cap.
ETA_MARGIN_SECONDS = 120.0
MAX_WAIT_SECONDS = 30 * 60.0

#: How a wait ended (:class:`Wait`).
MERGED = "merged"
STILL_QUEUED = "queued"
LEFT = "left"
HEAD_MOVED = "head-moved"

#: How deleting a merged PR's head branch ended (:class:`BranchDeletion`):
#: deleted at the head that merged; kept, `reason_kind` saying why; gone — not
#: there, whoever removed it; refused, the deletion not asked for; or
#: unconfirmed — asked for, with no usable answer and no reading since, so
#: whether it was deleted is not known.
DELETED = "deleted"
KEPT = "kept"
GONE = "gone"
REFUSED = "refused"
UNCONFIRMED = "unconfirmed"

#: Why a head branch was kept: its tip is not the head that merged; another
#: open PR uses the branch as its head or as its base; the service answered
#: the deletion with an error (a protected branch, say); or the deletion got
#: no usable answer and a reading since finds the branch still at the head
#: that merged. :data:`UNANSWERED` is also why a deletion, a merge, an
#: enqueue or a dequeue is unconfirmed: it got no usable answer, and the PR
#: could not be read since.
TIP_MOVED = "tip-moved"
OPEN_PULL_REQUEST = "open-pull-request"
DELETION_REFUSED = "deletion-refused"
UNANSWERED = "unanswered"

#: Why a merge, an enqueue or a dequeue was not accepted though the service
#: refused nothing: it got no usable answer, and two readings since — the
#: second :data:`SETTLE_WINDOW_SECONDS` or more after it was sent — did not
#: see its end state (:func:`_settle`). It was not seen made: a reading, never
#: a fact, since the service may still apply it.
NOT_MADE = "not-made"

#: Why a deletion was refused, besides the cross-repository guard's
#: (`session_guard.FOREIGN_REPOSITORY`): the PR has not merged; its head is in
#: another repository, a fork; the head named is not the head the PR merged
#: at; the PR, or the open PRs that use its branch, could not be read.
#: :data:`NOT_READ` is also why a dequeue the service answered is
#: unconfirmed: the PR could not be read since to see it out of the queue;
#: and why a dequeue that sent nothing was not accepted: the PR could not be
#: read before it, or read out of the queue once and not again to confirm it.
NOT_MERGED = "not-merged"
CROSS_REPOSITORY = "cross-repository"
EXPECT_MISMATCH = "expect-mismatch"
NOT_READ = "unreadable"

#: Why a dequeue was not accepted: the PR has merged — :data:`MERGED`, the
#: value a wait ends with too — which no dequeue undoes.
HAS_MERGED = MERGED

#: Runs one `gh` command and answers what it did.
GhRunner = Callable[[Sequence[str]], "subprocess.CompletedProcess[str]"]

# What a GraphQL API answers when asked for a field it does not know.
_UNKNOWN_FIELD = "doesn't exist on type"

# The one field whose absence means the API knows no merge queues (an older
# GitHub Enterprise Server), so a base on such a host has none.
_QUEUE_FIELD = "isMergeQueueEnabled"

# What every API answers about a PR, merge queues or not.
_PR_FIELDS = """\
      id
      state
      mergedAt
      mergeCommit { oid }
      headRefOid
      headRefName
      isCrossRepository"""

_QUEUE_FIELDS = """\
      isMergeQueueEnabled
      isInMergeQueue
      mergeQueue { configuration { mergeMethod } }
      mergeQueueEntry { position state estimatedTimeToMerge }
      autoMergeRequest { enabledAt }
      timelineItems(
        itemTypes: [ADDED_TO_MERGE_QUEUE_EVENT, REMOVED_FROM_MERGE_QUEUE_EVENT], last: 20
      ) {
        nodes {
          __typename
          ... on RemovedFromMergeQueueEvent { createdAt reason beforeCommit { oid } }
        }
      }"""

_ADDED_EVENT = "AddedToMergeQueueEvent"
_REMOVED_EVENT = "RemovedFromMergeQueueEvent"

# GitHub's own mutation that takes a PR out of a merge queue.
_DEQUEUE = "mutation($id: ID!) { dequeuePullRequest(input: {id: $id}) { clientMutationId } }"

# How many of the open PRs that use a branch the deletion's readings name; they
# count them all.
_OPEN_PULL_REQUESTS_NAMED = 5

# What deleting a merged PR's head branch reads first, in one request: the PR —
# its head commit among it — the repository the request acts in, and the
# branch as it stands now: its tip, and the open PRs whose head it is.
# `headRef` is null once the branch is gone.
_BRANCH_FIELDS = f"""\
{_PR_FIELDS}
      repository {{ id }}
      headRef {{
        target {{ oid }}
        associatedPullRequests(states: [OPEN], first: {_OPEN_PULL_REQUESTS_NAMED}) {{
          totalCount
          nodes {{ number }}
        }}
      }}"""

# The open PRs whose base is a branch, read once the reading above has named
# it: a branch knows the PRs whose head it is, not those based on it.
_BASED_ON = f"""\
query($owner: String!, $repo: String!, $branch: String!) {{
  repository(owner: $owner, name: $repo) {{
    pullRequests(states: [OPEN], baseRefName: $branch, first: {_OPEN_PULL_REQUESTS_NAMED}) {{
      totalCount
      nodes {{ number }}
    }}
  }}
}}
"""

# GitHub's mutation that moves a repository's refs only from the commits it is
# told they are at, all of them or none: a branch moved to the all-zero commit
# is deleted, so naming its expected tip makes the compare and the delete one
# request.
_DELETE_AT = (
    "mutation($repository: ID!, $name: GitRefname!, $before: GitObjectID!, "
    "$after: GitObjectID!) { updateRefs(input: {repositoryId: $repository, "
    "refUpdates: [{name: $name, beforeOid: $before, afterOid: $after}]}) "
    "{ clientMutationId } }"
)
_NO_COMMIT = "0" * 40

# A full commit id: SHA-1's 40 hexadecimal characters, or SHA-256's 64.
_FULL_OBJECT_ID = re.compile(r"[0-9a-f]{40}|[0-9a-f]{64}")


class Unreadable(Exception):
    """The reading could not be taken; the message says why."""


class _UnknownField(Unreadable):
    """The API does not know a field the query asked for."""


@dataclass(frozen=True)
class Removal:
    """The queue dropping the PR, as GitHub records it."""

    at: str
    #: Why, in GitHub's words; empty when it gives none.
    reason: str
    #: The PR's head when it was dropped; empty when GitHub does not say.
    head_oid: str

    def as_json(self) -> dict[str, str]:
        return {"at": self.at, "reason": self.reason, "head_oid": self.head_oid}


@dataclass(frozen=True)
class Reading:
    """Where a PR stands with its base branch's merge queue."""

    #: The base branch merges through a queue.
    has_queue: bool
    #: The queue's merge method (`SQUASH`, `MERGE`, `REBASE`); empty without one.
    merge_method: str = ""
    #: The PR's node ID, which the queue's own mutations take.
    pr_id: str = ""
    #: The PR's state: `OPEN`, `CLOSED` or `MERGED`.
    pr_state: str = ""
    merged_at: str = ""
    #: The PR's head commit.
    head_oid: str = ""
    in_queue: bool = False
    #: The PR's place in the queue, 1 first; None outside it.
    position: int | None = None
    #: The entry's state: `QUEUED`, `AWAITING_CHECKS`, `MERGEABLE`,
    #: `UNMERGEABLE` or `LOCKED`; empty outside the queue.
    entry_state: str = ""
    eta_seconds: int | None = None
    #: Auto-merge holds the PR until its own required checks pass; it enters
    #: the queue then.
    waiting_to_enter: bool = False
    #: The PR has been in a merge queue at some point.
    ever_queued: bool = False
    #: The queue dropping the PR, when that is the queue's last word on it.
    removal: Removal | None = None
    #: The PR's head branch, by name.
    head_ref: str = ""
    #: The PR's head is in another repository than its base: a fork.
    cross_repository: bool = False
    #: The commit the PR's merge made on its base; empty until it has merged,
    #: or where the service names none.
    merge_commit: str = ""

    @property
    def merged(self) -> bool:
        return bool(self.merged_at) or self.pr_state == "MERGED"

    @property
    def queued(self) -> bool:
        """In the queue, or held by auto-merge until it may enter."""
        return self.in_queue or self.waiting_to_enter

    @property
    def squashes(self) -> bool:
        return self.merge_method == SQUASH

    @property
    def dropped_head(self) -> bool:
        """The queue dropped the PR at the head it has now, and it has not
        been queued or merged since. A removal that names no head is taken as
        this one's."""
        if self.removal is None or self.queued or self.merged:
            return False
        return self.removal.head_oid in ("", self.head_oid)

    def describe(self) -> str:
        """Where the PR stands, as one phrase for a command's output."""
        if self.merged:
            return f"merged at {self.merged_at}" if self.merged_at else "merged"
        if self.in_queue:
            parts = [
                f"position {self.position} in the queue"
                if self.position is not None
                else "in the queue"
            ]
            if self.entry_state:
                parts.append(self.entry_state.lower().replace("_", " "))
            if self.eta_seconds is not None:
                parts.append(f"{_duration(self.eta_seconds)} to merge")
            return ", ".join(parts)
        if self.waiting_to_enter:
            return "waiting for its required checks before it enters the queue"
        if self.pr_state == "CLOSED":
            return "closed without merging"
        return "not in the queue"

    def as_json(self) -> dict[str, Any]:
        """The reading as its document states it: what GitHub answered, and
        what the reading concludes from it, so no reader derives it again."""
        return {
            "has_queue": self.has_queue,
            "merge_method": self.merge_method,
            "pr_id": self.pr_id,
            "pr_state": self.pr_state,
            "merged_at": self.merged_at,
            "head_oid": self.head_oid,
            "in_queue": self.in_queue,
            "position": self.position,
            "entry_state": self.entry_state,
            "eta_seconds": self.eta_seconds,
            "waiting_to_enter": self.waiting_to_enter,
            "ever_queued": self.ever_queued,
            "removal": self.removal.as_json() if self.removal is not None else None,
            "head_ref": self.head_ref,
            "cross_repository": self.cross_repository,
            "merge_commit": self.merge_commit,
            "merged": self.merged,
            "queued": self.queued,
            "squashes": self.squashes,
            "dropped_head": self.dropped_head,
            "description": self.describe(),
        }


@dataclass(frozen=True)
class Outcome:
    """What a request to the hosting service came to."""

    #: True once it was made: gh accepted it, or a reading since it got no
    #: usable answer finds its end state — for a dequeue, two readings
    #: running. False when it was not: the service refused it, gh could not be
    #: run, two readings since it got no usable answer did not see it made
    #: (:data:`NOT_MADE`), or a dequeue found the PR merged
    #: (:data:`HAS_MERGED`), still queued after the service accepted it, or
    #: could not read it before it sent anything (:data:`NOT_READ`).
    #: None when whether it was made is not known: no usable answer and no
    #: reading since (:data:`UNANSWERED`), or a dequeue the service accepted
    #: and no reading since to see the PR out (:data:`NOT_READ`) — unconfirmed.
    accepted: bool | None
    #: `gh`'s exit code; None when it could not be run, was ended at its
    #: bound, or the request was judged on a reading rather than on gh's exit.
    exit_code: int | None = 0
    #: Why it was not accepted, or why whether it was is not known: gh's own
    #: words, why gh could not run, or what the readings since found. A
    #: dequeue sent twice says so here, whatever the second came to.
    reason: str = ""
    #: :data:`NOT_MADE`, :data:`UNANSWERED`, :data:`HAS_MERGED` or
    #: :data:`NOT_READ`; "" otherwise.
    reason_kind: str = ""

    def as_json(self) -> dict[str, Any]:
        return {
            "accepted": self.accepted,
            "exit_code": self.exit_code,
            "reason": self.reason,
            "reason_kind": self.reason_kind or None,
        }


@dataclass(frozen=True)
class Wait:
    """How a wait for the queue's merge ended: `ended` is :data:`MERGED`,
    :data:`STILL_QUEUED` (the time ran out), :data:`LEFT` or
    :data:`HEAD_MOVED`; `reading` is the last reading taken."""

    ended: str
    reading: Reading


@dataclass(frozen=True)
class _Gh:
    """The module's own `gh`: run from `cwd` — None, the working directory —
    in this process's environment, through the command runner's one bounded
    start, so it stays in this process's group and is ended alone past its
    bound: :data:`GH_REQUEST_SECONDS` when its calls are `requests` that
    change the service, else :data:`GH_READ_SECONDS`. Raises
    `subprocess.TimeoutExpired` past it."""

    cwd: Path | None = None
    requests: bool = False

    def __call__(self, argv: Sequence[str]) -> subprocess.CompletedProcess[str]:
        seconds = GH_REQUEST_SECONDS if self.requests else GH_READ_SECONDS
        return command_runner.run_bounded(argv, cwd=self.cwd, seconds=seconds)


def run_gh(argv: Sequence[str]) -> subprocess.CompletedProcess[str]:
    """Run `gh` from the working directory, in this process's environment,
    bounded as a reading (:data:`GH_READ_SECONDS`)."""
    return _Gh()(argv)


def gh_runner(cwd: Path) -> GhRunner:
    """A runner of `gh` from `cwd`, for a caller whose repository is not the
    working directory's: bounded as a reading, and as a request where it makes
    one (:func:`_requesting`)."""
    return _Gh(cwd)


# ---- reading -----------------------------------------------------------------


def read(pr_number: int, *, gh: GhRunner | None = None) -> Reading:
    """Read where PR `pr_number` stands with its base branch's merge queue.

    Raises :class:`Unreadable` when `gh` cannot answer. Only an API that does
    not know `isMergeQueueEnabled` itself answers that there is no queue: when
    the full read fails on some other unknown field, that field alone is asked
    for, and a host that knows it has queues, so the read is unreadable rather
    than "no queue".
    """
    run = _runner(gh)
    try:
        pr = _pull_request(pr_number, f"{_PR_FIELDS}\n{_QUEUE_FIELDS}", run)
    except _UnknownField as exc:
        if _knows_merge_queues(pr_number, run):
            raise Unreadable(str(exc)) from None
        return _reading(_pull_request(pr_number, _PR_FIELDS, run))
    return _reading(pr)


def squash_commit_defaults(*, gh: GhRunner | None = None) -> tuple[str, str]:
    """The repository's default squash-commit title and message, as GitHub
    names them (`PR_TITLE` or `COMMIT_OR_PR_TITLE`; `PR_BODY`,
    `COMMIT_MESSAGES` or `BLANK`). A merge queue composes its squash commit
    from these and ignores what the merge command asks for. Raises
    :class:`Unreadable` when they cannot be read."""
    proc = _run(_runner(gh), ["gh", "api", "repos/{owner}/{repo}"])
    if proc.returncode != 0:
        raise Unreadable((proc.stderr or "").strip() or "gh answered nothing")
    repository = _mapping(_json(proc.stdout))
    if not repository:
        raise Unreadable("the answer names no repository")
    title = repository.get("squash_merge_commit_title")
    message = repository.get("squash_merge_commit_message")
    if not (isinstance(title, str) and isinstance(message, str)):
        raise Unreadable(
            "the repository's squash-commit defaults are not in the answer (an account "
            "without access to the repository's settings does not see them)"
        )
    return title, message


# ---- the merge requests ------------------------------------------------------


def squash_merge(
    pr_number: int,
    *,
    subject: str,
    cwd: Path,
    clearance: session_guard.Clearance,
    head_oid: str = "",
    admin: bool = False,
) -> Outcome:
    """Squash-merge the PR with `subject` as the landed commit's subject.

    `clearance` is the cross-repository guard's for `cwd`, the directory `gh`
    runs in (:func:`session_guard.require`). GitHub's
    default subject for a single-commit PR is the commit message, so the
    subject is always passed. `head_oid`, the head the caller checked, pins
    the merge (`--match-head-commit`): a push in between fails it instead of
    landing commits nothing checked. Deliberately without `--delete-branch`:
    that flag makes gh check out the base locally and delete the local head,
    and the whole command exits non-zero when the working tree cannot do so —
    after the remote merge has landed — so the exit code would no longer report
    the merge alone.

    Accepted is not proof of a merge: on a base that requires a queue, gh
    enqueues and exits 0. Read the PR afterwards (:func:`read`). A merge that
    got no usable answer is settled by reading (:func:`_settle`): made once
    the PR reads merged or queued, or dropped by the queue since the merge was
    sent.
    """
    run = _acting(clearance, cwd)
    cmd = ["gh", "pr", "merge", str(pr_number), "--squash", "--subject", subject]
    if head_oid:
        cmd += ["--match-head-commit", head_oid]
    if admin:
        cmd.append("--admin")
    return _request(pr_number, run, cmd, _MERGING)


def enqueue(
    pr_number: int,
    *,
    cwd: Path,
    clearance: session_guard.Clearance,
    head_oid: str = "",
) -> Outcome:
    """Put the PR in its base branch's merge queue: `gh pr merge <N> --auto`,
    pinned to the head the caller checked.

    `clearance` and `cwd` as for :func:`squash_merge`. GitHub ignores a merge
    method, a subject and a body passed with a queued merge, so none is
    passed; a caller checks the queue's method and the repository's
    squash-commit defaults instead. With `--auto`, a PR whose own required
    checks are still running is taken in once they pass. Never `--admin`,
    which merges around the queue. The PR has not merged when this returns.
    An enqueue that got no usable answer is settled by reading
    (:func:`_settle`): made once the PR reads queued or merged, or dropped by
    the queue since the enqueue was sent.
    """
    run = _acting(clearance, cwd)
    cmd = ["gh", "pr", "merge", str(pr_number), "--auto"]
    if head_oid:
        cmd += ["--match-head-commit", head_oid]
    return _request(pr_number, run, cmd, _ENQUEUING)


def dequeue(
    pr_number: int,
    *,
    cwd: Path,
    clearance: session_guard.Clearance,
) -> Outcome:
    """Take the PR out of its base's merge queue — or, while auto-merge still
    holds it until its checks pass, cancel that — and confirm it is out.

    `clearance` and `cwd` as for :func:`squash_merge`. The PR is read first.
    Merged, the dequeue is not accepted (:data:`HAS_MERGED`): no dequeue
    undoes a merge. Out of the queue, it is read once more after
    :data:`SETTLE_INTERVAL_SECONDS` — a PR the queue is merging can read out
    of it and not yet merged — and out again, nothing is sent: it is already
    out. Either reading not taken, nothing is sent and the dequeue is not
    accepted, :data:`NOT_READ`: whether the PR is in the queue is not known.
    Queued, the dequeue is sent: `gh pr merge --disable-auto` cancels
    the auto-merge; on a PR already in the queue gh answers "already queued
    to merge" and changes nothing, so such a PR is taken out through GitHub's
    own `dequeuePullRequest`.

    Out of the queue is concluded only from two readings running, as the wait
    concludes it, answered or not (:func:`_settle`). Answered, a PR still
    queued on the second reading was not taken out, and one that cannot be
    read since is unconfirmed (:data:`NOT_READ`): the answer is not the
    reading this command confirms on. A dequeue with no usable answer that
    was not seen made is sent once more (:data:`DEQUEUE_ATTEMPTS`) — it is
    idempotent, and it keeps commits nothing checked out of the queue — and
    the reason says so, whatever the second came to.
    """
    run = _acting(clearance, cwd)
    try:
        before = read(pr_number, gh=run)
    except Unreadable as exc:
        return Outcome(False, None, f"PR #{pr_number} could not be read: {exc}", NOT_READ)
    if not (before.merged or before.queued):
        _sleep(SETTLE_INTERVAL_SECONDS)
        try:
            before = read(pr_number, gh=run)
        except Unreadable as exc:
            return Outcome(
                False,
                None,
                f"PR #{pr_number} read out of the merge queue once, and could not be read "
                f"again to confirm it: {exc}",
                NOT_READ,
            )
        if not (before.merged or before.queued):
            return Outcome(True, None)
    if before.merged:
        return _has_merged(pr_number, before)
    taken = _take_out(pr_number, run, before)
    for _ in range(DEQUEUE_ATTEMPTS - 1):
        if taken.outcome.reason_kind != NOT_MADE or taken.reading is None:
            break
        again = _take_out(pr_number, run, taken.reading)
        taken = _Settled(_sent_again(taken.outcome, again.outcome), again.reading)
    return taken.outcome


def _take_out(pr_number: int, run: GhRunner, reading: Reading) -> _Settled:
    """Send the dequeue the PR's state in `reading` calls for, and settle it
    (:func:`_settle`); refused, it is not settled, and no reading is taken."""
    if reading.in_queue and reading.pr_id:
        cmd = ["gh", "api", "graphql", "-f", f"query={_DEQUEUE}", "-f", f"id={reading.pr_id}"]
    else:
        cmd = ["gh", "pr", "merge", str(pr_number), "--disable-auto"]
    sent = _send(_requesting(run), cmd, _DEQUEUING.name)
    if sent.ended == _NOT_APPLIED:
        return _Settled(Outcome(False, sent.exit_code, sent.said), None)
    return _settle(pr_number, run, _DEQUEUING, sent)


def _sent_again(first: Outcome, again: Outcome) -> Outcome:
    """What a dequeue sent once more came to — `again`'s outcome — its reason
    saying that the `first` was not seen made, and why."""
    came = again.reason or "two readings since show the PR out of the merge queue"
    return replace(again, reason=f"{first.reason}; it was sent once more: {came}")


def _has_merged(pr_number: int, reading: Reading) -> Outcome:
    """A dequeue's end on a PR `reading` finds merged: not accepted, saying at
    which head, where the reading has it."""
    head = f" at head {reading.head_oid[:7]}" if reading.head_oid else ""
    return Outcome(
        False,
        None,
        f"PR #{pr_number} has merged{head} ({reading.describe()}), which no dequeue undoes",
        HAS_MERGED,
    )


# ---- the module's clocks -----------------------------------------------------
#
# The sleep and the clock the settling readings and the wait run on, and the
# wall clock a request's sending is dated by, looked up at each use so a test
# drives them and no test sleeps.

_sleep: Callable[[float], None] = time.sleep
_monotonic: Callable[[], float] = time.monotonic


def _now_utc() -> datetime:
    return datetime.now(UTC)


_utcnow: Callable[[], datetime] = _now_utc


# ---- sending a request -------------------------------------------------------


@dataclass(frozen=True)
class _Sent:
    """What a request came to as gh ended (:func:`_send`): `ended` is
    :data:`_APPLIED`, :data:`_NOT_APPLIED` or :data:`_NO_ANSWER`; `said` is
    what the service or gh answered, or why there is no usable answer;
    `exit_code` is gh's, None when it could not be run or was ended at its
    bound. `at` is when it was sent, on the module's clock (`_monotonic`), and
    `wall` the same moment in UTC, to set against the service's own dates."""

    ended: str
    said: str = ""
    exit_code: int | None = None
    at: float = 0.0
    wall: datetime | None = None


# How a request ended (:class:`_Sent`): applied; not applied — an answer this
# module recognises as one said so (:data:`_ANSWERED`), or gh could not be
# started and nothing was sent; or no usable answer — anything else, so it may
# have been applied or not.
_APPLIED = "applied"
_NOT_APPLIED = "not-applied"
_NO_ANSWER = "no-answer"

# The words on gh's standard error that are an answer saying the request was
# not applied: the service's GraphQL error (`GraphQL: …`), an HTTP 4xx status
# (`HTTP 422: …`, `gh: … (HTTP 403)`) but 408 — a request that timed out on
# the way, which the service may have acted on — and gh's own refusal before
# it sent anything, which it marks with its failure or warning sign (`X Pull
# request #N is not mergeable: …`, `! Pull request #N is already queued to
# merge`). Nothing else is taken for an answer.
_ANSWERED = re.compile(r"^GraphQL: |\bHTTP 4(?!08)\d\d\b|^[X!] Pull request ", re.MULTILINE)


#: Told of each request — its name, and the command that sends it — just
#: before it is sent, while a landing runs (:func:`land`): this is the one
#: place every request passes, so while the landing's output takes them, its
#: `requesting` line is out before `gh` starts. A write that fails before any
#: request stops the landing, nothing sent; one that fails after a
#: `requesting` line is out stops the writing and not the landing, whose
#: later requests no line names. Unset, nothing is told.
_ON_SEND: ContextVar[Callable[[str, Sequence[str]], None] | None] = ContextVar(
    "pull_request_landing_on_send", default=None
)


def _send(run: GhRunner, cmd: list[str], name: str) -> _Sent:
    """Send the request `name`, telling three ends apart, and date it.

    Whoever a landing set to be told (:data:`_ON_SEND`) is told first, before
    `gh` starts; should that fail, nothing is sent.

    Applied: gh exited 0 and the answer names no errors. Not applied, only on
    an answer recognised as one: the GraphQL errors the answer carries, or
    gh's words in a shape :data:`_ANSWERED` knows — the service's `GraphQL:`
    error, an HTTP 4xx, gh's own refusal before it sent anything — or gh
    could not be started, so nothing was sent. No usable answer otherwise: gh
    ended at its bound, or by a signal — a negative exit, whatever it printed
    — or any other failure, its words kept in `said`; the request may have
    been applied or not.
    """
    told = _ON_SEND.get()
    if told is not None:
        told(name, cmd)
    at, wall = _monotonic(), _utcnow()
    try:
        proc = run(cmd)
    except FileNotFoundError:
        return _Sent(_NOT_APPLIED, "`gh` not on PATH, so nothing was sent", at=at, wall=wall)
    except OSError as exc:
        return _Sent(
            _NOT_APPLIED, f"`gh` could not be run ({exc}), so nothing was sent", at=at, wall=wall
        )
    except subprocess.TimeoutExpired as exc:
        return _Sent(
            _NO_ANSWER,
            f"`gh` did not answer within {exc.timeout:g} s, and was ended",
            at=at,
            wall=wall,
        )
    said = (proc.stderr or "").strip()
    if proc.returncode < 0:
        ended = f"`gh` was ended by signal {-proc.returncode}"
        return _Sent(_NO_ANSWER, f"{ended}: {said}" if said else ended, proc.returncode, at, wall)
    errors = _mapping(_json(proc.stdout)).get("errors")
    named = _list(errors)
    if named:
        return _Sent(_NOT_APPLIED, _error_text(proc.stderr, named), proc.returncode, at, wall)
    if proc.returncode == 0 and not errors:
        return _Sent(_APPLIED, exit_code=0, at=at, wall=wall)
    if proc.returncode != 0 and _ANSWERED.search(said):
        return _Sent(_NOT_APPLIED, said, proc.returncode, at, wall)
    return _Sent(_NO_ANSWER, said or "gh answered nothing", proc.returncode, at, wall)


# ---- what a request came to, as the PR reads since ---------------------------


def _merged_or_queued(pr_number: int, reading: Reading, sent: _Sent) -> bool:
    """Whether `reading` shows a merge's or an enqueue's end state: the PR
    merged or queued — a merge on a base that requires a queue enqueues — or
    dropped by the queue since the request was sent (:func:`_dropped_since`)."""
    return reading.merged or reading.queued or _dropped_since(reading, sent)


def _out_of_the_queue(pr_number: int, reading: Reading, sent: _Sent) -> Outcome | bool:
    """Whether `reading` shows a dequeue's end state, the PR out of the queue;
    merged, the dequeue is over and not accepted (:func:`_has_merged`)."""
    if reading.merged:
        return _has_merged(pr_number, reading)
    return not reading.queued


def _dropped_since(reading: Reading, sent: _Sent) -> bool:
    """The queue's last word on the PR is a drop GitHub dated no earlier than
    the request was `sent`: the request put the PR in the queue, which dropped
    it since, so it was made, and its caller sees the drop as any reading
    shows it.

    The two dates come from two clocks, GitHub's and this machine's: a drop
    GitHub dates by a clock ahead of this one may read as made though it came
    before the request, one behind as not seen made though it came after. A
    drop dated in a form this module does not read tells nothing."""
    removal = reading.removal
    if removal is None or sent.wall is None:
        return False
    dropped = _instant(removal.at)
    return dropped is not None and dropped >= sent.wall


def _instant(text: str) -> datetime | None:
    """A date as GitHub writes it — ISO 8601, `Z` for UTC — or None when it is
    not one, or names no zone."""
    try:
        when = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    return when if when.tzinfo is not None else None


@dataclass(frozen=True)
class _Asked:
    """A request, as :func:`_settle` reads what it came to: its name; how the
    PR reads short of the request's end state; what one reading shows
    (`judge`) — True at the end state, False short of it, or the outcome it
    settles at once; and how many readings running at the end state make the
    request made (`confirmations`): one where the end state is something seen,
    two where it is an absence."""

    name: str
    unsettled: str
    judge: Callable[[int, Reading, _Sent], Outcome | bool]
    confirmations: int = 1

    @property
    def most_readings(self) -> int:
        """The most readings :func:`_settle` takes for this request: once
        short of the end state, then at it as often as it confirms on, or
        short of it again — every other sequence ends sooner."""
        return self.confirmations + 1


#: The requests a landing sends, by name — its events' `request`, its end's
#: `sent` (a merge or an enqueue) — and, with :data:`WAIT`, what a dry run
#: says it would do (`would`).
MERGE_REQUEST = "merge"
ENQUEUE_REQUEST = "enqueue"
DEQUEUE_REQUEST = "dequeue"
WAIT = "wait"

_MERGING = _Asked(MERGE_REQUEST, "neither merged nor queued", _merged_or_queued)
_ENQUEUING = _Asked(ENQUEUE_REQUEST, "neither queued nor merged", _merged_or_queued)
_DEQUEUING = _Asked(DEQUEUE_REQUEST, "queued", _out_of_the_queue, confirmations=2)


@dataclass(frozen=True)
class _Settled:
    """What :func:`_settle` came to, and the last reading it took — None when
    it took none."""

    outcome: Outcome
    reading: Reading | None


def _request(pr_number: int, run: GhRunner, cmd: list[str], asked: _Asked) -> Outcome:
    """Send a request on `run`, bounded as a request, and say what it came to:
    accepted when gh accepted it; refused, in the words of the answer, when an
    answer said so or gh could not be run; and, with no usable answer, settled
    by reading (:func:`_settle`)."""
    sent = _send(_requesting(run), cmd, asked.name)
    if sent.ended == _APPLIED:
        return Outcome(True, sent.exit_code)
    if sent.ended == _NOT_APPLIED:
        return Outcome(False, sent.exit_code, sent.said)
    return _settle(pr_number, run, asked, sent).outcome


def _settle(pr_number: int, run: GhRunner, asked: _Asked, sent: _Sent) -> _Settled:
    """What a request came to, as the PR reads since it was `sent` (ADR-061
    point 5, the third obligation; point 7): a request with no usable answer,
    or a dequeue, whose end state only readings show.

    The PR is read at once, then again no sooner than
    :data:`SETTLE_WINDOW_SECONDS` after the request was sent and
    :data:`SETTLE_INTERVAL_SECONDS` after the reading before, so a request
    the service was still making shows. Its end state seen on as many readings
    running as `asked` confirms on, it was made — `exit_code` gh's where gh
    answered, else None. Not seen on the second reading or a later one, it was
    not seen made (:data:`NOT_MADE`) — or, for a dequeue the service answered,
    not seen out of the queue — which one reading never concludes, and which
    is what the readings saw, never that the request was not made. It takes
    no more readings than `asked`'s most (:attr:`_Asked.most_readings`), the
    count its longest is stated for: past them, it was not seen made. A reading
    that cannot be taken leaves it unconfirmed: :data:`UNANSWERED` with no
    usable answer — `accepted` and `exit_code` None, since whether it was
    made, and how gh would have ended, are not known — and :data:`NOT_READ`
    for a dequeue the service answered.

    With no usable answer, one line on standard error says so as settling
    starts — what was asked, that no usable answer came, that the PR is being
    read and for how long at most — so whoever interrupts the command knows a
    request is in flight.
    """
    answered = sent.ended == _APPLIED
    if not answered:
        _say_settling(pr_number, asked, sent)
    taken: list[float] = []
    streak = 0
    reading: Reading | None = None
    for _ in range(asked.most_readings):
        if taken:
            _sleep(max(SETTLE_INTERVAL_SECONDS, sent.at + SETTLE_WINDOW_SECONDS - _monotonic()))
        taken.append(_monotonic())
        try:
            reading = read(pr_number, gh=run)
        except Unreadable as exc:
            return _Settled(_unconfirmed(pr_number, asked, sent, exc), reading)
        seen = asked.judge(pr_number, reading, sent)
        if isinstance(seen, Outcome):
            return _Settled(seen, reading)
        if seen:
            streak += 1
            if streak == asked.confirmations:
                return _Settled(Outcome(True, sent.exit_code if answered else None), reading)
            continue
        streak = 0
        if len(taken) > 1:
            return _Settled(_not_seen(pr_number, asked, sent, taken, reading), reading)
    # Its most readings taken and its end state not confirmed on them: not
    # seen made, as on any other sequence that does not confirm it. Every
    # sequence ends above before this one does; the bound holds the count
    # the settling's longest is stated for, whatever a judge comes to say.
    last = cast(Reading, reading)
    return _Settled(_not_seen(pr_number, asked, sent, taken, last), last)


def _lost(pr_number: int, asked: _Asked, sent: _Sent) -> str:
    return f"the {asked.name} of PR #{pr_number} got no usable answer ({sent.said})"


def _say_settling(pr_number: int, asked: _Asked, sent: _Sent) -> None:
    """The line on standard error as settling starts (:func:`_settle`)."""
    longest = _settling_longest(asked, _monotonic() - sent.at)
    print(
        f"[warn] {_lost(pr_number, asked, sent)}: reading where PR #{pr_number} stands to "
        f"tell whether it was made — the second reading no sooner than "
        f"{SETTLE_WINDOW_SECONDS:g} s after it was sent, up to {longest:.0f} s in all",
        file=sys.stderr,
        flush=True,
    )


def _unconfirmed(pr_number: int, asked: _Asked, sent: _Sent, exc: Unreadable) -> Outcome:
    """A request whose settling reading could not be taken: unconfirmed."""
    if sent.ended == _APPLIED:
        return Outcome(
            None,
            sent.exit_code,
            f"the service accepted the {asked.name} of PR #{pr_number}, and PR #{pr_number} "
            f"could not be read since to see it out of the merge queue ({exc}): whether it "
            "left the queue is not known",
            NOT_READ,
        )
    return Outcome(
        None,
        None,
        f"{_lost(pr_number, asked, sent)}, and PR #{pr_number} could not be read since "
        f"({exc}): whether the {asked.name} was made is not known",
        UNANSWERED,
    )


def _not_seen(
    pr_number: int, asked: _Asked, sent: _Sent, taken: list[float], reading: Reading
) -> Outcome:
    """A request whose end state the readings `taken` did not see: what they
    saw, and when — never that it was not made."""
    found = f"PR #{pr_number} reads {asked.unsettled} ({reading.describe()})"
    over = _readings(taken, sent)
    if sent.ended == _APPLIED:
        return Outcome(
            False,
            sent.exit_code,
            f"the service accepted the {asked.name} of PR #{pr_number}, and it was not seen "
            f"out of the merge queue on {over}: {found}",
        )
    return Outcome(
        False,
        None,
        f"{_lost(pr_number, asked, sent)}, and was not seen made on {over}: {found}",
        NOT_MADE,
    )


_COUNTED = {2: "two", 3: "three"}


def _readings(taken: list[float], sent: _Sent) -> str:
    """The readings `taken` since the request was `sent`, as a phrase: how
    many, how far apart, and how long after the request the last was taken."""
    apart = taken[-1] - taken[0]
    since = taken[-1] - sent.at
    count = _COUNTED.get(len(taken), str(len(taken)))
    if len(taken) == 2:
        return f"two readings {apart:.0f} s apart, the second {since:.0f} s after it was sent"
    return (
        f"{count} readings, the first and last {apart:.0f} s apart, the last {since:.0f} s "
        "after it was sent"
    )


# ---- how long a subcommand can run -------------------------------------------


def _call_longest(seconds: float) -> float:
    """The longest one `gh` call bounded by `seconds` takes: its bound, then
    the grace it has, once asked to stop, before it is killed."""
    return seconds + command_runner.END_GRACE_SECONDS


def _reading_longest() -> float:
    """The longest one reading (:func:`read`) takes: every call it can make,
    each at its bound."""
    return CALLS_PER_READING * _call_longest(GH_READ_SECONDS)


def _settling_longest(asked: _Asked, since_sent: float) -> float:
    """The longest :func:`_settle` takes for `asked`, starting `since_sent`
    seconds after the request was sent: the first reading; the wait until the
    window has passed, or the interval after the first reading if that is
    later; the second reading; and, for each further reading it may take, the
    interval and the reading."""
    reading = _reading_longest()
    second = max(SETTLE_WINDOW_SECONDS - since_sent, reading + SETTLE_INTERVAL_SECONDS)
    further = (asked.most_readings - 2) * (SETTLE_INTERVAL_SECONDS + reading)
    return second + reading + further


def longest_seconds(subcommand: str) -> float:
    """The longest `pkit pull-request <subcommand>` can run, computed from this
    module's constants: every `gh` call at its bound and ended there
    (:data:`GH_READ_SECONDS`, :data:`GH_REQUEST_SECONDS`, each with
    `command_runner.END_GRACE_SECONDS`), every reading at its most calls
    (:data:`CALLS_PER_READING`), every settling reading the request may take
    (:data:`SETTLE_WINDOW_SECONDS`, :data:`SETTLE_INTERVAL_SECONDS`), a
    dequeue sent :data:`DEQUEUE_ATTEMPTS` times, and every git question of the
    cross-repository guard at its bound (`session_guard.LONGEST_SECONDS`)
    where the subcommand runs it. project-management's bound on the
    subcommand must hold it. `wait` runs as long as it is asked to, and past
    that by at most :func:`wait_overrun_seconds`.
    """
    reading = _reading_longest()
    one_call = _call_longest(GH_READ_SECONDS)
    request = _call_longest(GH_REQUEST_SECONDS)
    guard = session_guard.LONGEST_SECONDS
    if subcommand == "read":
        return reading
    if subcommand == "squash-defaults":
        return one_call
    if subcommand in ("merge", "enqueue"):
        # The guard, the request, and the readings that settle it.
        return guard + request + _settling_longest(_MERGING, request)
    if subcommand == "dequeue":
        # The guard; the reading first and, read out of the queue, the one
        # after the interval that finds it queued after all; then each
        # attempt: the request, and the readings that settle it.
        attempt = request + _settling_longest(_DEQUEUING, request)
        return guard + reading + SETTLE_INTERVAL_SECONDS + reading + DEQUEUE_ATTEMPTS * attempt
    if subcommand == "delete-branch":
        # The guard; the branch's reading and the open PRs based on it, one
        # call each; the request; and the branch's reading again.
        return guard + 2 * one_call + request + one_call
    raise ValueError(f"`pkit pull-request` has no subcommand {subcommand!r} that ends by itself")


def wait_overrun_seconds() -> float:
    """How long a wait (:func:`wait_for_merge`) can run past its limit: the
    reading in flight at its deadline, then — one reading out of the queue
    there — the poll interval and one more reading."""
    return 2 * _reading_longest() + POLL_SECONDS


# ---- the head branch ---------------------------------------------------------


@dataclass(frozen=True)
class BranchDeletion:
    """What deleting a merged PR's head branch came to (:func:`delete_branch`)."""

    #: :data:`DELETED`, :data:`KEPT`, :data:`GONE`, :data:`REFUSED` or
    #: :data:`UNCONFIRMED`.
    outcome: str
    #: The head branch, by name; empty when the PR was not read.
    branch: str = ""
    #: The branch's tip, when it was kept.
    tip: str = ""
    #: Why it was kept (:data:`TIP_MOVED`, :data:`OPEN_PULL_REQUEST`,
    #: :data:`DELETION_REFUSED`, :data:`UNANSWERED`), unconfirmed
    #: (:data:`UNANSWERED`) or refused (:data:`NOT_MERGED`,
    #: :data:`CROSS_REPOSITORY`, :data:`EXPECT_MISMATCH`, :data:`NOT_READ`, or
    #: the guard's); empty when it was deleted or gone.
    reason_kind: str = ""
    reason: str = ""
    #: The PR's head, as the reading found it: the head it merged at, once it
    #: has; empty when the PR was not read.
    merged_head: str = ""

    def as_json(self) -> dict[str, Any]:
        return {
            "outcome": self.outcome,
            "branch": self.branch or None,
            "tip": self.tip or None,
            "reason_kind": self.reason_kind or None,
            "reason": self.reason or None,
            "merged_head": self.merged_head or None,
        }

    def describe(self) -> str:
        """What became of the branch, as one phrase for a command's output —
        with no closing full stop, which the service's words may carry."""
        branch = f"remote branch {self.branch!r}" if self.branch else "the remote head branch"
        reason = self.reason.rstrip(".")
        if self.outcome == DELETED:
            return f"deleted {branch}"
        if self.outcome == GONE:
            return f"{branch} is not there; nothing to delete"
        if self.outcome == KEPT:
            return f"kept {branch}: {reason}"
        if self.outcome == UNCONFIRMED:
            return f"whether {branch} was deleted is not known: {reason}"
        return f"{branch} not deleted: {reason}"


@dataclass(frozen=True)
class _OpenPullRequests:
    """The open PRs, other than the one whose branch is being deleted, that
    use the branch one way: how many, and the first few by number."""

    count: int
    numbers: tuple[int, ...]

    def named(self) -> str:
        """The numbers, as a parenthesis for a reason; empty when none is named."""
        named = ", ".join(f"#{number}" for number in self.numbers)
        more = self.count - len(self.numbers)
        if named and more > 0:
            named += f" and {more} more"
        return f" ({named})" if named else ""


@dataclass(frozen=True)
class _HeadBranch:
    """A PR's head branch as one reading finds it."""

    pr_state: str
    merged: bool
    #: The PR's head commit: the head it merged at, once it has.
    head_oid: str
    name: str
    cross_repository: bool
    #: The repository the request acts in, as the GraphQL API names it.
    repository_id: str
    #: The branch's tip; empty once the branch is gone.
    tip: str
    #: The open PRs whose head the branch is; None when the reading does not
    #: say how many, which is never taken for none.
    heads: _OpenPullRequests | None

    def ended(
        self, outcome: str, tip: str = "", reason_kind: str = "", reason: str = ""
    ) -> BranchDeletion:
        """The deletion of this branch, ended as `outcome`."""
        return BranchDeletion(outcome, self.name, tip, reason_kind, reason, self.head_oid)


def full_object_id(value: str) -> str:
    """`value` as a full commit id, lower-cased — 40 or 64 hexadecimal
    characters, nothing abbreviated — or "" when it is not one: the form
    :func:`delete_branch`'s `expect` is named in on the command line, and the
    only form :func:`land` takes its head in."""
    candidate = value.strip().lower()
    return candidate if _FULL_OBJECT_ID.fullmatch(candidate) else ""


def delete_branch(
    pr_number: int,
    *,
    expect: str,
    cwd: Path,
    clearance: session_guard.Clearance,
) -> BranchDeletion:
    """Delete merged PR `pr_number`'s head branch on the service, only while
    its tip is `expect`, the head the PR merged at (ADR-061 point 1, and the
    fifth obligation of point 5).

    `clearance` and `cwd` as for :func:`squash_merge`. One reading comes
    first. Nothing more is asked, and the deletion is :data:`REFUSED`, for a
    PR that has not merged; one whose head is in another repository — a fork,
    whose owner keeps its branches, and a branch of the same name here is not
    the PR's; one whose head is not `expect`, so the branch is deleted only at
    the head that merged; and a reading that cannot be taken. A branch not
    there is :data:`GONE`. A branch whose tip is not `expect` — a push since
    the merge, or a branch of the same name made since — is :data:`KEPT`,
    with its tip. Then a second reading asks which open PRs are based on the
    branch: a branch another open PR uses as its head or as its base is kept;
    a count either reading does not give is refused, never taken for none.

    Otherwise the deletion is one compare-and-delete request: GitHub's
    `updateRefs`, naming `expect` as the branch's tip, deletes it only while
    it is there, so a push between the reading and the request is never lost.
    Applied, the branch is :data:`DELETED`; otherwise it is read again
    (:func:`_not_deleted`).
    """
    run = _acting(clearance, cwd)
    try:
        head = _head_branch(pr_number, run)
    except Unreadable as exc:
        return BranchDeletion(
            REFUSED, reason_kind=NOT_READ, reason=f"PR #{pr_number} could not be read: {exc}"
        )
    refused = _refusal(pr_number, head, expect)
    if refused is not None:
        return refused
    standing = _standing(pr_number, head, expect)
    if standing is not None:
        return standing
    if head.heads is None:
        return head.ended(
            REFUSED,
            reason_kind=NOT_READ,
            reason=f"the reading of PR #{pr_number} does not say how many open pull requests "
            "use its head branch as their head",
        )
    try:
        based = _based_on(pr_number, head.name, run)
    except Unreadable as exc:
        return head.ended(
            REFUSED,
            reason_kind=NOT_READ,
            reason=f"which open pull requests are based on {head.name!r} could not be read: {exc}",
        )
    in_use = _in_use(head, head.heads, based)
    if in_use is not None:
        return in_use
    cmd = [
        "gh",
        "api",
        "graphql",
        "-f",
        f"query={_DELETE_AT}",
        "-f",
        f"repository={head.repository_id}",
        "-f",
        f"name=refs/heads/{head.name}",
        "-f",
        f"before={expect}",
        "-f",
        f"after={_NO_COMMIT}",
    ]
    sent = _send(_requesting(run), cmd, "delete-branch")
    if sent.ended == _APPLIED:
        return head.ended(DELETED)
    return _not_deleted(pr_number, head, expect, sent, run)


def _refusal(pr_number: int, head: _HeadBranch, expect: str) -> BranchDeletion | None:
    """Why the deletion is not asked for at all, as `head` finds the PR — not
    merged, a fork's, not named fully, or not at `expect` — or None."""
    if not head.merged:
        state = head.pr_state.lower() or "of no reported state"
        return head.ended(
            REFUSED,
            reason_kind=NOT_MERGED,
            reason=f"PR #{pr_number} has not merged (it is {state}); its head branch is deleted "
            "only once it has",
        )
    if head.cross_repository:
        return head.ended(
            REFUSED,
            reason_kind=CROSS_REPOSITORY,
            reason=f"PR #{pr_number}'s head is in another repository, a fork, whose owner keeps "
            "its branches; a branch of that name here is not the PR's",
        )
    if not (head.name and head.repository_id and head.head_oid):
        return head.ended(
            REFUSED,
            reason_kind=NOT_READ,
            reason=f"the reading of PR #{pr_number} names no head branch, head commit or "
            "repository",
        )
    if expect != head.head_oid:
        return head.ended(
            REFUSED,
            reason_kind=EXPECT_MISMATCH,
            reason=f"the head named, {expect or 'none'}, is not the head PR #{pr_number} merged "
            f"at, {head.head_oid}: its head branch is deleted only at that head",
        )
    return None


def _standing(pr_number: int, head: _HeadBranch, expect: str) -> BranchDeletion | None:
    """The branch as `head` finds it, when that ends the deletion — gone, or
    its tip not `expect` — or None when it stands at `expect`."""
    if not head.tip:
        return head.ended(GONE)
    if head.tip != expect:
        return head.ended(
            KEPT,
            head.tip,
            TIP_MOVED,
            f"its tip is {head.tip[:7]}, not {expect[:7]}, the head PR #{pr_number} merged at: "
            "a push since the merge, or a branch of that name made since, is not deleted",
        )
    return None


def _in_use(
    head: _HeadBranch, heads: _OpenPullRequests, based: _OpenPullRequests
) -> BranchDeletion | None:
    """The branch kept for the other open PRs that use it — `heads` as their
    head, `based` as their base — or None when none does."""
    uses: list[str] = []
    if heads.count:
        who = (
            "another open pull request uses"
            if heads.count == 1
            else f"{heads.count} other open pull requests use"
        )
        whose, them = ("its", "that pull request") if heads.count == 1 else ("their", "them")
        uses.append(
            f"{who} this branch as {whose} head{heads.named()}: deleting it would close {them}"
        )
    if based.count:
        who = (
            "another open pull request is"
            if based.count == 1
            else f"{based.count} other open pull requests are"
        )
        uses.append(
            f"{who} based on this branch{based.named()}, and a branch an open pull request "
            "merges into is kept"
        )
    if not uses:
        return None
    return head.ended(KEPT, head.tip, OPEN_PULL_REQUEST, "; ".join(uses))


def _not_deleted(
    pr_number: int, head: _HeadBranch, expect: str, sent: _Sent, run: GhRunner
) -> BranchDeletion:
    """What became of the branch after a deletion not seen applied: the
    branch is read again.

    An answer said it was not applied — the service's errors, which is all a
    refused `updateRefs` says, often only a generic error; or another answer
    :func:`_send` recognises — so this request deleted nothing: the reading
    tells the branch gone, moved, or still at `expect`, kept
    (:data:`DELETION_REFUSED`); with no reading, kept at the tip read before
    the request. No usable answer — anything else — so it may have been
    applied: the branch
    gone is :data:`GONE`, the state asked for; still at `expect`, it was not
    applied (:data:`KEPT`, :data:`UNANSWERED`); with no reading,
    :data:`UNCONFIRMED`, stating no tip and no refusal it does not know.
    """
    unanswered = sent.ended == _NO_ANSWER
    if unanswered:
        asked = f"the deletion got no usable answer ({sent.said})"
    else:
        asked = f"the service did not delete it: {sent.said}"
    try:
        after = _head_branch(pr_number, run)
    except Unreadable as exc:
        since = f"the branch could not be read since ({exc})"
        if unanswered:
            return head.ended(UNCONFIRMED, reason_kind=UNANSWERED, reason=f"{asked}, and {since}")
        return head.ended(KEPT, head.tip, DELETION_REFUSED, f"{asked}; {since}")
    standing = _standing(pr_number, after, expect)
    if standing is not None:
        return standing
    if unanswered:
        return head.ended(
            KEPT,
            after.tip,
            UNANSWERED,
            f"{asked}, and a reading since finds the branch still at {expect[:7]}: the request "
            "was not applied",
        )
    return head.ended(KEPT, after.tip, DELETION_REFUSED, asked)


def _head_branch(pr_number: int, run: GhRunner) -> _HeadBranch:
    """PR `pr_number`'s head branch as it stands, in one reading. Raises
    :class:`Unreadable` when it cannot be read."""
    pr = _pull_request(pr_number, _BRANCH_FIELDS, run)
    ref = _mapping(pr.get("headRef"))
    return _HeadBranch(
        pr_state=str(pr.get("state") or ""),
        merged=bool(pr.get("mergedAt")) or pr.get("state") == "MERGED",
        head_oid=str(pr.get("headRefOid") or ""),
        name=str(pr.get("headRefName") or ""),
        cross_repository=_cross_repository(pr),
        repository_id=str(_mapping(pr.get("repository")).get("id") or ""),
        tip=str(_mapping(ref.get("target")).get("oid") or ""),
        heads=_open_others(pr_number, ref.get("associatedPullRequests")),
    )


def _based_on(pr_number: int, branch: str, run: GhRunner) -> _OpenPullRequests:
    """The open PRs other than `pr_number` whose base is `branch`. Raises
    :class:`Unreadable` when they cannot be read, or the answer does not say
    how many."""
    data = _graphql(
        run, _BASED_ON, ["-F", "owner={owner}", "-F", "repo={repo}", "-f", f"branch={branch}"]
    )
    based = _open_others(pr_number, _mapping(data.get("repository")).get("pullRequests"))
    if based is None:
        raise Unreadable(
            f"the answer does not say how many open pull requests are based on {branch!r}"
        )
    return based


def _open_others(pr_number: int, connection: object) -> _OpenPullRequests | None:
    """The open PRs a connection's answer counts and names, less PR
    `pr_number`; None when it does not say how many — which reads as not
    known, never as none."""
    answer = _mapping(connection)
    count = _int_or_none(answer.get("totalCount"))
    if count is None or count < 0:
        return None
    listed = [
        number
        for number in (
            _int_or_none(_mapping(node).get("number")) for node in _list(answer.get("nodes"))
        )
        if number is not None
    ]
    numbers = tuple(number for number in listed if number != pr_number)
    others = count - (len(listed) - len(numbers))
    return _OpenPullRequests(max(others, len(numbers)), numbers)


# ---- the wait ----------------------------------------------------------------


def wait_for_merge(
    pr_number: int,
    *,
    timeout_seconds: float | None,
    on_change: Callable[[Reading], None],
    head_oid: str = "",
    gh: GhRunner | None = None,
    interval_seconds: float = POLL_SECONDS,
    sleep: Callable[[float], None] | None = None,
    clock: Callable[[], float] | None = None,
    on_reading: Callable[[Reading], None] | None = None,
) -> Wait:
    """Read the queue until the PR merges, leaves it, or the time runs out.

    `timeout_seconds` None follows the queue's estimate: the first reading
    that carries one sets the deadline to that estimate plus
    :data:`ETA_MARGIN_SECONDS`, never past :data:`MAX_WAIT_SECONDS` from the
    start, which is also the deadline while no estimate has come — a PR still
    waiting for its own checks before it enters has none. A number is a fixed
    deadline; 0 reads once.

    A PR is declared out of the queue only on two readings running: closed,
    or seen out of the queue twice, so a reading taken just as GitHub takes the
    PR in is not mistaken for one that left. A single reading out of the queue
    at the deadline is followed by one more after the interval. With
    `head_oid`, the head the caller checked, a reading whose head differs ends
    the wait at once (:data:`HEAD_MOVED`): commits nobody checked must not
    merge, and the caller takes the PR out (:func:`dequeue`). `on_reading`,
    when given, is handed each reading as it is taken; `on_change` each
    whose description differs from the one before, once the wait has judged
    it: what a reading ends — the head check among it — never waits on a
    write. Raises :class:`Unreadable` when a reading cannot be taken.
    """
    run = _runner(gh)
    pause = sleep if sleep is not None else _sleep
    now = clock if clock is not None else _monotonic
    start = now()
    deadline = start + (MAX_WAIT_SECONDS if timeout_seconds is None else timeout_seconds)
    last_description = ""
    seen_out = False
    estimated = timeout_seconds is not None
    while True:
        reading = read(pr_number, gh=run)
        if on_reading is not None:
            on_reading(reading)
        ended = _wait_ended(reading, head_oid, seen_out)
        if reading.describe() != last_description:
            last_description = reading.describe()
            on_change(reading)
        if ended is not None:
            return Wait(ended, reading)
        seen_out = not reading.queued
        if not estimated and reading.eta_seconds is not None:
            estimated = True
            deadline = min(
                start + MAX_WAIT_SECONDS,
                now() + reading.eta_seconds + ETA_MARGIN_SECONDS,
            )
        remaining = deadline - now()
        if remaining <= 0:
            if not seen_out:
                return Wait(STILL_QUEUED, reading)
            pause(interval_seconds)
            continue
        pause(min(interval_seconds, remaining))


def _wait_ended(reading: Reading, head_oid: str, seen_out: bool) -> str | None:
    """How `reading` ends a wait pinned to `head_oid` — merged; at another
    head; closed, or out of the queue on the reading before too — or None
    while it goes on."""
    if reading.merged:
        return MERGED
    if head_oid and reading.head_oid and reading.head_oid != head_oid:
        return HEAD_MOVED
    if reading.pr_state == "CLOSED" or (seen_out and not reading.queued):
        return LEFT
    return None


def wait_limit(seconds: float | None) -> str:
    """How long a wait of `seconds` lasts, as a phrase: None follows the
    queue's estimate (:func:`wait_for_merge`)."""
    if seconds is None:
        return (
            f"as long as the queue estimates plus {ETA_MARGIN_SECONDS / 60:g} min, "
            f"at most {MAX_WAIT_SECONDS / 60:g} min"
        )
    return f"up to {seconds / 60:g} min"


# ---- the landing -------------------------------------------------------------
#
# The landing sequence in one call (ADR-061 point 5): the guard's clearance,
# taken once by the caller and handed down; one reading; the caller's options
# applied to it, the first matching row of one table; the request, pinned to
# the head the caller checked; the wait; and, when the head moved, the PR
# taken out of the queue. It reports each request as the request documents
# do, and its own end as `ended`, so no caller derives it. It never deletes a
# branch: when to delete is the caller's.

#: How a landing ended — its end document's `ended`, one of twelve
#: (:data:`LANDING_ENDS`).
END_MERGED = "merged"
END_MERGED_ELSEWHERE = "merged-at-another-head"
END_CLOSED = "closed"
END_PLANNED = "planned"
END_QUEUED = "queued"
END_UNCONFIRMED = "unconfirmed"
END_HEAD_MOVED = "head-moved"
END_DROPPED = "dropped"
END_NOT_MERGED = "not-merged"
END_FAILED = "failed"
END_REFUSED = "refused"
END_UNREADABLE = "unreadable"

#: Why a landing was refused before any request, besides the guard's
#: (`session_guard.FOREIGN_REPOSITORY`), in the one order it judges them, the
#: squash-commit defaults read last: a merge or an enqueue the caller allowed
#: no request for (`no_request`), on any base; then, on a base that merges
#: through a queue, an administrator merge asked for there; a direct merge
#: asked for there (`--direct-only`); a queue that does not squash; a head the
#: queue dropped, not enqueued again unchanged unless the caller allows it;
#: and squash-commit defaults that are not the PR's title and body. No option
#: lifts the administrator merge, nor the two that say the queue would not
#: make COR-009's commit (ADR-061 points 5 and 8). :data:`SQUASH_DEFAULTS` is
#: also why a landing is unreadable when the defaults cannot be read.
REQUEST_NOT_ALLOWED = "request-not-allowed"
ADMIN_ON_QUEUE = "admin-on-queue"
QUEUE_NOT_ALLOWED = "queue-not-allowed"
QUEUE_NOT_SQUASH = "queue-not-squash"
DROPPED_HEAD = "dropped-head"
SQUASH_DEFAULTS = "squash-defaults"

#: Each way a landing ends, with the `reason_kind`s it carries — None among
#: them where the kind alone says it. A reader takes a document with any
#: other `ended`, or a `reason_kind` its `ended` does not carry, for no
#: answer (:func:`decode_end`).
LANDING_ENDS: Mapping[str, frozenset[str | None]] = {
    END_MERGED: frozenset({None}),
    END_MERGED_ELSEWHERE: frozenset({None}),
    END_CLOSED: frozenset({None}),
    END_PLANNED: frozenset({None}),
    END_QUEUED: frozenset({None, NOT_READ}),
    END_UNCONFIRMED: frozenset({UNANSWERED, NOT_READ}),
    END_HEAD_MOVED: frozenset({None}),
    END_DROPPED: frozenset({None}),
    END_NOT_MERGED: frozenset({None}),
    END_FAILED: frozenset({None, NOT_MADE}),
    END_REFUSED: frozenset(
        {
            session_guard.FOREIGN_REPOSITORY,
            REQUEST_NOT_ALLOWED,
            ADMIN_ON_QUEUE,
            QUEUE_NOT_ALLOWED,
            QUEUE_NOT_SQUASH,
            DROPPED_HEAD,
            SQUASH_DEFAULTS,
        }
    ),
    END_UNREADABLE: frozenset({None, SQUASH_DEFAULTS}),
}

_ANY_SENT: frozenset[str | None] = frozenset({None, MERGE_REQUEST, ENQUEUE_REQUEST})
_NONE_SENT: frozenset[str | None] = frozenset({None})

#: The request each end can state as `sent` — the merge or the enqueue this
#: run sent that the service did not refuse — by its `ended` and
#: `reason_kind`. A reader takes a document whose `sent` its end cannot
#: carry for no answer (:func:`decode_end`). `queued` carries a merge the
#: service queued instead; `not-merged` a request, or none, before the base
#: lost its queue; `unconfirmed`, `unreadable`, any where a reading after the
#: first says merged and names no head — a first reading that names no head
#: ends `unreadable`, nothing sent.
LANDING_SENT: Mapping[tuple[str, str | None], frozenset[str | None]] = {
    (END_MERGED, None): _ANY_SENT,
    (END_MERGED_ELSEWHERE, None): _ANY_SENT,
    (END_CLOSED, None): _NONE_SENT,
    (END_PLANNED, None): _NONE_SENT,
    (END_QUEUED, None): _ANY_SENT,
    (END_QUEUED, NOT_READ): frozenset({None, ENQUEUE_REQUEST}),
    (END_UNCONFIRMED, UNANSWERED): frozenset({MERGE_REQUEST, ENQUEUE_REQUEST}),
    (END_UNCONFIRMED, NOT_READ): _ANY_SENT,
    (END_HEAD_MOVED, None): _ANY_SENT,
    (END_DROPPED, None): _ANY_SENT,
    (END_NOT_MERGED, None): _ANY_SENT,
    (END_FAILED, None): _NONE_SENT,
    (END_FAILED, NOT_MADE): frozenset({MERGE_REQUEST, ENQUEUE_REQUEST}),
    **{(END_REFUSED, kind): _NONE_SENT for kind in LANDING_ENDS[END_REFUSED]},
    (END_UNREADABLE, None): _NONE_SENT,
    (END_UNREADABLE, SQUASH_DEFAULTS): _NONE_SENT,
}

#: The ends at which a reading says the PR merged.
_MERGED_ENDS = (END_MERGED, END_MERGED_ELSEWHERE)

#: The ends that may come with no reading — the guard refused, nothing read;
#: the first reading failed — and the one that must.
_UNREAD_ENDS = ((END_REFUSED, session_guard.FOREIGN_REPOSITORY), (END_UNREADABLE, None))
_NOTHING_READ = (END_REFUSED, session_guard.FOREIGN_REPOSITORY)

#: What a landing states of taking a PR out of the queue: `pkit pull-request
#: dequeue`'s keys.
_DEQUEUE_KEYS = frozenset({"accepted", "exit_code", "reason", "reason_kind"})

#: What a dry run says it would do (`would`).
_WOULD = (MERGE_REQUEST, ENQUEUE_REQUEST, WAIT, DEQUEUE_REQUEST)

#: What a landing does with a PR already queued in a queue that would not
#: make the squash commit (`--queued-bad-shape`): refuse — the PR stays
#: queued, and may still merge — or wait for it with a warning.
SHAPE_REFUSE = "refuse"
SHAPE_WARN = "warn"

#: A landing's `path`: through a merge queue — the last reading shows one on
#: the base, or the PR was ever in one — or directly.
PATH_QUEUE = "queue"
PATH_DIRECT = "direct"

#: Every key of a landing's end document, each present in every one.
END_KEYS = frozenset(
    {
        "schema_version",
        "pull_request",
        "event",
        "dry_run",
        "ended",
        "reason_kind",
        "reason",
        "would",
        "path",
        "checked_head",
        "merged_head",
        "merge_commit",
        "sent",
        "dequeue",
        "reading",
        "shape",
        "warnings",
        "guard",
        "bound_seconds",
    }
)


@dataclass(frozen=True)
class LandOptions:
    """The caller's choices, which a landing applies to the reading it takes
    just before its request, where no caller can stand (ADR-061 point 5): how
    long to wait for the queue's merge (`seconds`; None as long as the queue
    estimates, at most :data:`MAX_WAIT_SECONDS`; 0 reads once); whether a head
    the queue already dropped is enqueued again; an administrator merge
    (refused on a base that merges through a queue); a direct merge only
    (refused on such a base); what to do with a PR already queued in a queue
    that would not make the squash commit (:data:`SHAPE_REFUSE`,
    :data:`SHAPE_WARN`); and no request (`no_request`): the caller allows no
    merge and no enqueue in this landing — a PR found queued at the checked
    head is waited for, one queued at another head is still taken out, and a
    row that would send a merge or an enqueue is refused
    (:data:`REQUEST_NOT_ALLOWED`), nothing sent."""

    seconds: float | None = None
    allow_dropped_head: bool = False
    admin: bool = False
    direct_only: bool = False
    queued_bad_shape: str = SHAPE_REFUSE
    no_request: bool = False


@dataclass(frozen=True)
class Shape:
    """Whether the squash commit a base's merge queue makes would be the one
    a PR lands as (COR-009; ADR-061 point 8), as a landing judged it: whether
    the queue squashes, from the reading; the repository's squash-commit
    defaults, None where they were not read — an earlier refusal ended the
    landing, or the queue does not squash — or could not be (`unreadable`,
    why); and whether it would (`conforms`), None where that is not known."""

    squashes: bool
    title: str | None = None
    message: str | None = None
    conforms: bool | None = None
    unreadable: str | None = None

    def as_json(self) -> dict[str, Any]:
        return {
            "squashes": self.squashes,
            "title": self.title,
            "message": self.message,
            "conforms": self.conforms,
            "unreadable": self.unreadable,
        }


#: Why a landing warns (:class:`Notice`), besides :data:`QUEUE_NOT_SQUASH`,
#: :data:`SQUASH_DEFAULTS` and :data:`NOT_READ`: auto-merge left armed on a
#: PR it held, whose direct merge ends failed or unconfirmed — it merges the
#: PR on its own, unpinned, once the base's requirements are met; and a
#: direct merge the service queued instead, whose queue's commit shape no
#: reading judged.
AUTO_MERGE_ARMED = "auto-merge-armed"
ENQUEUED_INSTEAD = "enqueued-instead"

#: Every kind of warning a landing gives (:class:`Notice`).
LANDING_WARNINGS = frozenset(
    {QUEUE_NOT_SQUASH, SQUASH_DEFAULTS, NOT_READ, AUTO_MERGE_ARMED, ENQUEUED_INSTEAD}
)


@dataclass(frozen=True)
class Notice:
    """A warning a landing gives as it goes on: why, by kind —
    :data:`QUEUE_NOT_SQUASH` or :data:`SQUASH_DEFAULTS` for a PR it waits for
    in a queue that would not make the squash commit, :data:`NOT_READ` for a
    reading after a direct merge that could not be taken,
    :data:`AUTO_MERGE_ARMED` for auto-merge left armed on a PR whose direct
    merge failed or is unconfirmed, :data:`ENQUEUED_INSTEAD` for a direct
    merge the service queued — and in words."""

    reason_kind: str
    reason: str

    def as_json(self) -> dict[str, str]:
        return {"reason_kind": self.reason_kind, "reason": self.reason}


@dataclass(frozen=True)
class Landing:
    """How a landing ended (:func:`land`), as its end document states it
    (:meth:`as_json`): `ended` from :data:`LANDING_ENDS`, with its
    `reason_kind` and, but where it merged or was planned, its `reason` —
    where a reading the landing needed failed, the reading's failure as the
    reading states it; what a dry run would do; the head the caller checked;
    the last reading taken; the merge or the enqueue it sent that the service
    did not refuse; what taking the PR out of the queue came to; the shape it
    judged; its warnings; the guard; and the longest it could run with these
    options."""

    pull_request: int
    ended: str
    checked_head: str
    guard: session_guard.Clearance | session_guard.Refusal
    bound_seconds: float
    dry_run: bool = False
    reason_kind: str | None = None
    reason: str | None = None
    #: :data:`MERGE_REQUEST`, :data:`ENQUEUE_REQUEST`, :data:`WAIT` or
    #: :data:`DEQUEUE_REQUEST` on a planned end; None otherwise.
    would: str | None = None
    reading: Reading | None = None
    #: :data:`MERGE_REQUEST` or :data:`ENQUEUE_REQUEST`: the request this run
    #: sent that the service did not refuse — made, not seen made, or
    #: unconfirmed; None when none was, or the one sent was refused.
    sent: str | None = None
    #: What taking the PR out of the queue came to, as `pkit pull-request
    #: dequeue` states it; None where no dequeue was run.
    dequeue: Outcome | None = None
    shape: Shape | None = None
    warnings: tuple[Notice, ...] = ()

    @property
    def path(self) -> str | None:
        """:data:`PATH_QUEUE` or :data:`PATH_DIRECT`; None with no reading."""
        if self.reading is None:
            return None
        return PATH_QUEUE if self.reading.has_queue or self.reading.ever_queued else PATH_DIRECT

    @property
    def merged_head(self) -> str | None:
        """The head of the reading that said merged — what a caller deletes
        the head branch at; None but where it merged."""
        if self.ended not in _MERGED_ENDS or self.reading is None:
            return None
        return self.reading.head_oid or None

    @property
    def merge_commit(self) -> str | None:
        """The commit the merge made; None but where it merged and the service
        names one."""
        if self.ended not in _MERGED_ENDS or self.reading is None:
            return None
        return self.reading.merge_commit or None

    def as_json(self) -> dict[str, Any]:
        """The end document: every key in every document (:data:`END_KEYS`)."""
        return _document(
            self.pull_request,
            event="end",
            dry_run=self.dry_run,
            ended=self.ended,
            reason_kind=self.reason_kind,
            reason=self.reason,
            would=self.would,
            path=self.path,
            checked_head=self.checked_head,
            merged_head=self.merged_head,
            merge_commit=self.merge_commit,
            sent=self.sent,
            dequeue=self.dequeue.as_json() if self.dequeue is not None else None,
            reading=self.reading.as_json() if self.reading is not None else None,
            shape=self.shape.as_json() if self.shape is not None else None,
            warnings=[notice.as_json() for notice in self.warnings],
            guard=self.guard.as_json(),
            bound_seconds=self.bound_seconds,
        )


#: Told each event of a landing as it happens: its document.
OnEvent = Callable[[dict[str, Any]], None]


def land(
    pr_number: int,
    *,
    head: str,
    subject: str,
    cwd: Path,
    clearance: session_guard.Clearance,
    options: LandOptions | None = None,
    dry_run: bool = False,
    on_event: OnEvent | None = None,
) -> Landing:
    """Land PR `pr_number` at `head`, the head the caller's gates checked,
    with `subject` as the squash commit's subject: the landing sequence, in
    one call (ADR-061 point 5).

    `clearance` is the cross-repository guard's for `cwd`, taken once by the
    caller and handed down, so a request made late — taking a PR out of the
    queue after a long wait — never waits on a question (ADR-061 point 6).
    One reading, then the first row of the table that matches it, the
    caller's `options` applied:

    - unreadable, or naming no head: :data:`END_UNREADABLE`; merged:
      :data:`END_MERGED`, or :data:`END_MERGED_ELSEWHERE` at another head
      than `head`; closed: :data:`END_CLOSED`; neither open, closed nor
      merged — a reading that names no state — :data:`END_UNREADABLE`, so
      only an open PR gets a request;
    - queued, on any base, at another head: taken out of the queue
      (:func:`dequeue`), then :data:`END_HEAD_MOVED`; open and not queued at
      another head: :data:`END_HEAD_MOVED`, nothing sent;
    - a row that would send a merge or an enqueue, with `options.no_request`:
      refused, :data:`REQUEST_NOT_ALLOWED`, nothing sent — the first refusal
      in the one order;
    - on a base that merges through a queue, the refusals in their one order
      (:data:`ADMIN_ON_QUEUE` … :data:`SQUASH_DEFAULTS`): refused, nothing
      sent, the PR left as it is; else queued already, the wait — a shape the
      caller waits for under :data:`SHAPE_WARN` noted as a warning — and
      otherwise the enqueue, then the wait;
    - on a base without a queue — a PR auto-merge holds there among them —
      the direct squash merge (:func:`squash_merge`, as it is), an
      administrator one with `options.admin`, then one reading: merged, it
      ends; not, the wait; not read, a warning, then the wait.

    A request the service refused ends :data:`END_FAILED` in its words; one
    not seen made, :data:`END_FAILED` with :data:`NOT_MADE`; one unconfirmed,
    :data:`END_UNCONFIRMED`. The wait ends merged, at `head` or another;
    queued, the time run out (:data:`END_QUEUED`); out of the queue, or
    closed, :data:`END_DROPPED` where a queue was seen and
    :data:`END_NOT_MERGED` where none was; at another head, the PR taken out
    of the queue, :data:`END_HEAD_MOVED`; and with a reading that cannot be
    taken, :data:`END_UNCONFIRMED` after a merge it sent — whether it merged
    is not known — else :data:`END_QUEUED`, both :data:`NOT_READ`.

    A `dry_run` takes the reading, and the squash-commit defaults where the
    table reaches them, and sends nothing: a row that sends a request or
    waits ends :data:`END_PLANNED`, saying what it would do; every other row
    ends as the landing would — refused, with `options.no_request`, where a
    merge or an enqueue would follow.

    `on_event` is told each event as it happens, as its document, while it
    takes them: the readings — the first, the one after a direct merge, each
    of the wait's that changed — and, for each request, `requesting`, before
    `gh` starts, and `requested` once it is settled. Should telling it fail
    before any request, the landing stops, nothing sent, and the failure is
    raised; after a `requesting` is out, the telling stops and the landing
    goes on — its wait, and its dequeue where the head moved — with no event
    told. So a reader left with a `requesting` and no end does not take the
    events it has for all the landing did: it may be running, and may have
    sent a dequeue no event names. The landing never deletes a branch.

    `head` is a full commit id, in any case (:func:`full_object_id`): its
    lower-cased form is what the readings are compared with, what each
    request is pinned to, and what the end's `checked_head` names. An
    abbreviated head would read as another head, and take a healthy PR out
    of the queue, so any other form is refused before anything is read
    (ADR-061 point 5, the second obligation), whether the landing is called
    as a command or imported. Raises `TypeError` or `ValueError` where
    `clearance` is not a clearance for `cwd`, and `ValueError` where `head`
    is not a full commit id.
    """
    where = session_guard.require(clearance, cwd)
    lander = _Lander(
        pr_number,
        head=_checked_head(head),
        subject=subject,
        where=where,
        clearance=clearance,
        options=options if options is not None else LandOptions(),
        dry_run=dry_run,
        on_event=on_event,
    )
    told = _ON_SEND.set(lander.requesting)
    try:
        return lander.lands()
    finally:
        _ON_SEND.reset(told)


def refused_by_the_guard(
    pr_number: int,
    *,
    head: str,
    refusal: session_guard.Refusal,
    options: LandOptions | None = None,
    dry_run: bool = False,
) -> Landing:
    """The end of a landing the cross-repository guard refused at its entry:
    nothing read, nothing sent, the guard's reason — which, for a dry run,
    says a run at a terminal would ask. `head` as for :func:`land`: a full
    commit id, else `ValueError`."""
    chosen = options if options is not None else LandOptions()
    return Landing(
        pr_number,
        END_REFUSED,
        _checked_head(head),
        refusal,
        landing_longest_seconds(chosen.seconds),
        dry_run=dry_run,
        reason_kind=session_guard.FOREIGN_REPOSITORY,
        reason=refusal.reason,
    )


def _checked_head(head: str) -> str:
    """The head a landing is pinned to, as a full commit id lower-cased;
    `ValueError` for any other form (:func:`land`)."""
    checked = full_object_id(head)
    if not checked:
        raise ValueError(
            f"a landing is pinned to the head the caller checked, named as a full commit id "
            f"(40 or 64 hexadecimal characters), and {head!r} is not one"
        )
    return checked


def landing_longest_seconds(seconds: float | None) -> float:
    """The longest `pkit pull-request land` can run, waiting `seconds` for the
    queue's merge (None: :data:`MAX_WAIT_SECONDS`): a function of the options
    alone, never of a reading — the PR can change before the landing — so a
    dry run states the figure the landing it plans has. Every leg it can run,
    each at its longest: the plan's (:func:`planning_longest_seconds` — the
    guard, one reading, the squash-commit defaults); the merge or the enqueue
    with the readings that settle it (`longest_seconds`, less the guard the
    landing runs once); one reading after a direct merge; the wait, and how
    far it runs past its limit (:func:`wait_overrun_seconds`); and taking the
    PR out of the queue (`longest_seconds("dequeue")`, less the guard)."""
    guard = session_guard.LONGEST_SECONDS
    request = max(longest_seconds(MERGE_REQUEST), longest_seconds(ENQUEUE_REQUEST)) - guard
    limit = MAX_WAIT_SECONDS if seconds is None else seconds
    taking_out = longest_seconds(DEQUEUE_REQUEST) - guard
    return (
        planning_longest_seconds()
        + request
        + _reading_longest()
        + limit
        + wait_overrun_seconds()
        + taking_out
    )


def planning_longest_seconds() -> float:
    """The longest a dry run of `pkit pull-request land` can run: the guard,
    one reading, and the repository's squash-commit defaults."""
    return session_guard.LONGEST_SECONDS + _reading_longest() + _call_longest(GH_READ_SECONDS)


class NotAnEnd(ValueError):
    """A document that is not a landing's end document: no answer."""


def decode_end(document: object) -> dict[str, Any]:
    """`document` as a landing's end document, decoded strictly by its
    `ended`: every key present (:data:`END_KEYS`), this version; an `ended`
    from :data:`LANDING_ENDS` with a `reason_kind` it carries; `dry_run` a
    boolean, true on a planned end; `checked_head` a full commit id;
    `bound_seconds` a number; `reason` null exactly where it ended `merged`
    or `planned`, words on every other end; `would` exactly on a planned end;
    `merged_head` exactly where it merged; `sent` one its end can carry
    (:data:`LANDING_SENT`); `dequeue` only with a head that moved, in
    `pkit pull-request dequeue`'s keys and types; and `reading` null only
    where nothing could be read — the guard refused, which reads nothing,
    or the first reading failed. Raises :class:`NotAnEnd` for anything else:
    no answer, so how the landing ended is not known."""
    if not isinstance(document, Mapping):
        raise NotAnEnd("the answer is not a document")
    doc = cast(Mapping[str, Any], document)
    missing = sorted(END_KEYS - set(doc))
    if missing:
        raise NotAnEnd(f"the end document has no {', '.join(f'`{key}`' for key in missing)}")
    if doc["schema_version"] != SCHEMA_VERSION or doc["event"] != "end":
        raise NotAnEnd(
            f"the document is not a version-{SCHEMA_VERSION} end (`schema_version` "
            f"{doc['schema_version']!r}, `event` {doc['event']!r})"
        )
    ended = doc["ended"]
    if not isinstance(ended, str) or ended not in LANDING_ENDS:
        raise NotAnEnd(f"the end document names no way a landing ends (`ended`: {ended!r})")
    reason_kind = doc["reason_kind"]
    if reason_kind not in LANDING_ENDS[ended]:
        raise NotAnEnd(f"a landing that ends {ended} carries no `reason_kind` {reason_kind!r}")
    _decode_types(doc)
    if ended == END_PLANNED and doc["dry_run"] is not True:
        raise NotAnEnd("a landing that ends planned is a dry run")
    reason = doc["reason"]
    if not (
        reason is None if ended in (END_MERGED, END_PLANNED) else isinstance(reason, str) and reason
    ):
        raise NotAnEnd(f"a landing that ends {ended} cannot give the `reason` {reason!r}")
    would = doc["would"]
    if not (would in _WOULD if ended == END_PLANNED else would is None):
        raise NotAnEnd(f"a landing that ends {ended} cannot say it would {would!r}")
    merged_head = doc["merged_head"]
    if not (
        isinstance(merged_head, str) and merged_head
        if ended in _MERGED_ENDS
        else merged_head is None
    ):
        raise NotAnEnd(f"a landing that ends {ended} cannot name `merged_head` {merged_head!r}")
    sent = doc["sent"]
    if sent not in LANDING_SENT[(ended, reason_kind)]:
        raise NotAnEnd(f"a landing that ends {ended} ({reason_kind}) cannot have sent {sent!r}")
    _decode_dequeue(ended, doc["dequeue"])
    _decode_reading(ended, reason_kind, doc["reading"])
    if not isinstance(doc["warnings"], list) or not isinstance(doc["guard"], Mapping):
        raise NotAnEnd("the end document's `warnings` or `guard` is not what it states")
    return dict(doc)


def _decode_types(doc: Mapping[str, Any]) -> None:
    """The end's `dry_run`, `checked_head` and `bound_seconds`, by type."""
    if not isinstance(doc["dry_run"], bool):
        raise NotAnEnd(f"the end's `dry_run` is not a boolean: {doc['dry_run']!r}")
    head = doc["checked_head"]
    if not (isinstance(head, str) and full_object_id(head) == head):
        raise NotAnEnd(f"the end's `checked_head` is not a full commit id: {head!r}")
    bound = doc["bound_seconds"]
    if isinstance(bound, bool) or not isinstance(bound, int | float):
        raise NotAnEnd(f"the end's `bound_seconds` is not a number: {bound!r}")


def _decode_dequeue(ended: str, dequeue: object) -> None:
    """The end's `dequeue`: null, or — only with a head that moved — what
    `pkit pull-request dequeue` states, in its keys and types."""
    if dequeue is None:
        return
    if ended != END_HEAD_MOVED:
        raise NotAnEnd(f"a landing that ends {ended} ran no dequeue")
    if not isinstance(dequeue, Mapping):
        raise NotAnEnd(f"the end's `dequeue` is not a document: {dequeue!r}")
    out = cast(Mapping[str, Any], dequeue)
    accepted, exit_code = out.get("accepted"), out.get("exit_code")
    reason_kind = out.get("reason_kind")
    if not (
        frozenset(out) == _DEQUEUE_KEYS
        and (accepted is None or isinstance(accepted, bool))
        and (exit_code is None or (isinstance(exit_code, int) and not isinstance(exit_code, bool)))
        and isinstance(out["reason"], str)
        and (reason_kind is None or isinstance(reason_kind, str))
    ):
        raise NotAnEnd(
            f"the end's `dequeue` is not what `pkit pull-request dequeue` states: {out!r}"
        )


def _decode_reading(ended: str, reason_kind: str | None, reading: object) -> None:
    """The end's `reading`: null where nothing could be read — always for a
    landing the guard refused — else the last reading, a document."""
    if reading is None:
        if (ended, reason_kind) not in _UNREAD_ENDS:
            raise NotAnEnd(f"a landing that ends {ended} took a reading, and names none")
        return
    if (ended, reason_kind) == _NOTHING_READ:
        raise NotAnEnd("a landing the guard refused read nothing, and names a reading")
    if not isinstance(reading, Mapping):
        raise NotAnEnd(f"the end's `reading` is not a document: {reading!r}")


class _Lander:
    """One landing as it runs (:func:`land`): what it has read, judged and
    sent so far, and how it ends."""

    def __init__(
        self,
        pr_number: int,
        *,
        head: str,
        subject: str,
        where: Path,
        clearance: session_guard.Clearance,
        options: LandOptions,
        dry_run: bool,
        on_event: OnEvent | None,
    ) -> None:
        self.pr_number = pr_number
        self.head = head
        self.subject = subject
        self.where = where
        self.clearance = clearance
        self.options = options
        self.dry_run = dry_run
        self.on_event = on_event
        self.run = gh_runner(where)
        self.reading: Reading | None = None
        self.shape: Shape | None = None
        self.sent: str | None = None
        self.warnings: list[Notice] = []
        # Each request's sends so far, and the requests sent and not yet settled.
        self.attempts: dict[str, int] = {}
        self.in_flight: set[str] = set()
        # Whether a request has gone out, its `requesting` written — from then
        # on a write that fails stops the writing, never the landing — and
        # whether the events are still written.
        self.sending = False
        self.writing = True

    # ---- the sequence ------------------------------------------------------

    def lands(self) -> Landing:
        """One reading, then the table's first matching row."""
        n = self.pr_number
        try:
            first = read(n, gh=self.run)
        except Unreadable as exc:
            return self.end(END_UNREADABLE, reason=str(exc))
        self.took(first)
        if not first.head_oid:
            return self.end(END_UNREADABLE, reason=f"the reading of PR #{n} names no head commit")
        if first.merged:
            return self.merged(first)
        if first.pr_state == "CLOSED":
            return self.end(END_CLOSED, reason=f"PR #{n} is closed without merging")
        if first.pr_state != "OPEN":
            return self.end(
                END_UNREADABLE,
                reason=f"the reading of PR #{n} names it neither open, closed nor merged (its "
                f"state: {first.pr_state or 'none'})",
            )
        if first.has_queue:
            self.shape = Shape(first.squashes, conforms=None if first.squashes else False)
        if first.head_oid != self.head:
            if not first.queued:
                return self.end(
                    END_HEAD_MOVED,
                    reason=f"{self.moved(first)}; it is in no merge queue, and nothing was sent",
                )
            if self.dry_run:
                return self.end(END_PLANNED, would=DEQUEUE_REQUEST)
            return self.take_out()
        if not first.has_queue:
            if self.options.no_request:
                return self.not_allowed(first, MERGE_REQUEST)
            if self.dry_run:
                return self.end(END_PLANNED, would=MERGE_REQUEST)
            return self.merge()
        if not first.queued and self.options.no_request:
            return self.not_allowed(first, ENQUEUE_REQUEST)
        refused = self.judged(first)
        if refused is not None:
            return refused
        if first.queued:
            if self.dry_run:
                return self.end(END_PLANNED, would=WAIT)
            return self.wait()
        if self.dry_run:
            return self.end(END_PLANNED, would=ENQUEUE_REQUEST)
        return self.enqueue()

    def judged(self, reading: Reading) -> Landing | None:
        """The landing refused on a base that merges through a queue, in the
        one order, the squash-commit defaults read last — or None, the shape
        judged and a warning noted where the caller waits for a bad one."""
        n, options = self.pr_number, self.options
        if options.admin:
            return self.refused(
                ADMIN_ON_QUEUE,
                f"PR #{n}'s base merges through a merge queue, the single merge path, and an "
                "administrator merge would go around it: none is made on such a base",
            )
        if options.direct_only:
            return self.refused(
                QUEUE_NOT_ALLOWED,
                f"PR #{n}'s base merges through a merge queue, and the landing was to merge "
                "directly only",
            )
        lenient = reading.queued and options.queued_bad_shape == SHAPE_WARN
        if not reading.squashes:
            method = reading.merge_method or "an unreported method"
            return self.bad_shape(
                QUEUE_NOT_SQUASH,
                f"the merge queue on PR #{n}'s base merges by {method}, so it would not make the "
                "one squash commit a pull request lands as",
                lenient,
            )
        if reading.dropped_head and not options.allow_dropped_head:
            return self.refused(DROPPED_HEAD, self.dropped(reading))
        try:
            title, message = squash_commit_defaults(gh=self.run)
        except Unreadable as exc:
            self.shape = Shape(True, unreadable=str(exc))
            if lenient:
                self.warnings.append(Notice(SQUASH_DEFAULTS, str(exc)))
                return None
            return self.end(END_UNREADABLE, reason_kind=SQUASH_DEFAULTS, reason=str(exc))
        conforms = (title, message) == (PR_TITLE, PR_BODY)
        self.shape = Shape(True, title, message, conforms)
        if conforms:
            return None
        return self.bad_shape(
            SQUASH_DEFAULTS,
            f"the merge queue composes the squash commit from the repository's defaults, title "
            f"{title} and message {message}, not {PR_TITLE} and {PR_BODY}",
            lenient,
        )

    def merge(self) -> Landing:
        """The direct squash merge (:meth:`merge_directly`), and the
        auto-merge it leaves armed warned of (:meth:`left_armed`)."""
        first = cast(Reading, self.reading)
        landed = self.merge_directly(first)
        armed = self.left_armed(first, landed)
        if armed is None:
            return landed
        return replace(landed, warnings=(*landed.warnings, armed))

    def merge_directly(self, first: Reading) -> Landing:
        """The direct squash merge, then one reading: merged, it ends; not —
        or not read, with a warning — the wait. That reading finding the PR
        queued where the `first` did not is a merge the service queued
        instead: warned."""
        outcome = squash_merge(
            self.pr_number,
            subject=self.subject,
            cwd=self.where,
            clearance=self.clearance,
            head_oid=self.head,
            admin=self.options.admin,
        )
        stopped = self.unless_made(MERGE_REQUEST, outcome)
        if stopped is not None:
            return stopped
        try:
            after = read(self.pr_number, gh=self.run)
        except Unreadable as exc:
            self.warnings.append(Notice(NOT_READ, str(exc)))
            return self.wait()
        self.took(after)
        if after.merged:
            return self.merged(after)
        # A PR auto-merge held reads queued before the merge as after it, so
        # for it only a queue entry it did not have is one the service made:
        # the reading tells the entry (`in_queue`) from the hold
        # (`waiting_to_enter`), and a hold that merely stays is no enqueue.
        held = first.waiting_to_enter
        entered = (after.in_queue and not first.in_queue) if held else after.queued
        if entered:
            self.warnings.append(
                Notice(
                    ENQUEUED_INSTEAD,
                    f"the service queued PR #{self.pr_number} instead of merging it: the queue "
                    "composes the squash commit, and its shape was not judged",
                )
            )
        return self.wait()

    def left_armed(self, first: Reading, landed: Landing) -> Notice | None:
        """The warning that auto-merge is left armed, on a PR it held at the
        `first` reading, where the landing ends neither merged nor taken out
        of the queue — failed, or unconfirmed — and its last reading still
        shows the hold; None otherwise. Not on a merge not seen made: while
        the hold shows, a merge with no usable answer reads as made
        (:func:`_merged_or_queued`), so the readings that did not see it saw
        the hold gone. A merge refused on such a PR — `gh` refuses one whose
        base's requirements, which auto-merge waits for, are unmet — leaves
        it armed; an unconfirmed one leaves it armed if it was not made."""
        last = landed.reading
        if not (first.waiting_to_enter and last is not None and last.waiting_to_enter):
            return None
        if last.merged or (landed.ended, landed.reason_kind) == (END_FAILED, NOT_MADE):
            return None
        n = self.pr_number
        if landed.ended == END_FAILED:
            armed = f"auto-merge is still enabled on PR #{n}"
        elif landed.ended == END_UNCONFIRMED:
            armed = (
                f"whether the merge of PR #{n} was made is not known; if it was not, auto-merge "
                "is still enabled on it"
            )
        else:
            return None
        return Notice(
            AUTO_MERGE_ARMED,
            f"{armed}: GitHub merges it on its own once the base's requirements are met, at "
            f"whatever head it has then — not pinned to {self.head[:7]}, the head that was checked",
        )

    def enqueue(self) -> Landing:
        """The enqueue, then the wait."""
        outcome = enqueue(
            self.pr_number, cwd=self.where, clearance=self.clearance, head_oid=self.head
        )
        stopped = self.unless_made(ENQUEUE_REQUEST, outcome)
        if stopped is not None:
            return stopped
        return self.wait()

    def wait(self) -> Landing:
        """The wait for the merge, and how it ended. Each reading it takes is
        the landing's last; each that changed is written. A reading that
        cannot be taken ends it on the last one that could."""
        n = self.pr_number
        try:
            waited = wait_for_merge(
                n,
                timeout_seconds=self.options.seconds,
                on_change=self.written,
                on_reading=self.saw,
                head_oid=self.head,
                gh=self.run,
            )
        except Unreadable as exc:
            if self.sent == MERGE_REQUEST:
                return self.end(END_UNCONFIRMED, reason_kind=NOT_READ, reason=str(exc))
            return self.end(END_QUEUED, reason_kind=NOT_READ, reason=str(exc))
        reading = self.reading = waited.reading
        if waited.ended == MERGED:
            return self.merged(reading)
        if waited.ended == HEAD_MOVED:
            return self.take_out()
        if waited.ended == STILL_QUEUED:
            return self.end(
                END_QUEUED,
                reason=f"PR #{n} is still queued as the wait ends ({reading.describe()})",
            )
        if reading.has_queue or reading.ever_queued:
            removal = reading.removal
            why = f"; GitHub says: {removal.reason}" if removal and removal.reason else ""
            return self.end(
                END_DROPPED,
                reason=f"PR #{n} left the merge queue without merging ({reading.describe()}){why}",
            )
        made = (
            f"the {self.sent} of PR #{n} was made"
            if self.sent is not None
            else f"nothing was sent: PR #{n} was waited for as it was found queued"
        )
        return self.end(
            END_NOT_MERGED,
            reason=f"{made}, and PR #{n} reads {reading.describe()}, with no merge queue seen",
        )

    def take_out(self) -> Landing:
        """The PR, at another head than the one checked, taken out of the queue."""
        outcome = dequeue(self.pr_number, cwd=self.where, clearance=self.clearance)
        self.requested(DEQUEUE_REQUEST, outcome)
        moved = self.moved(cast(Reading, self.reading))
        return self.end(END_HEAD_MOVED, reason=moved, dequeue=outcome)

    # ---- its parts -----------------------------------------------------------

    def unless_made(self, name: str, outcome: Outcome) -> Landing | None:
        """Said what request `name` came to, the landing ended unless it was
        made: refused on an answer, or not seen made — failed; unconfirmed.
        A request the service did not refuse is the one this run `sent`."""
        self.requested(name, outcome)
        if outcome.accepted is not False or outcome.reason_kind == NOT_MADE:
            self.sent = name
        if outcome.accepted:
            return None
        if outcome.accepted is None:
            return self.end(END_UNCONFIRMED, reason_kind=UNANSWERED, reason=outcome.reason)
        if outcome.reason_kind == NOT_MADE:
            return self.end(END_FAILED, reason_kind=NOT_MADE, reason=outcome.reason)
        return self.end(
            END_FAILED, reason=outcome.reason or f"the {name} of PR #{self.pr_number} was refused"
        )

    def merged(self, reading: Reading) -> Landing:
        """A reading that says merged: at the checked head, or at another —
        and one that names no head is no merge the landing can state, since
        a caller deletes the head branch at the head it names: unconfirmed,
        at which head it merged not known."""
        if not reading.head_oid:
            return self.end(
                END_UNCONFIRMED,
                reason_kind=NOT_READ,
                reason=f"a reading says PR #{self.pr_number} merged and names no head commit: "
                "at which head it merged is not known",
            )
        if reading.head_oid == self.head:
            return self.end(END_MERGED)
        return self.end(
            END_MERGED_ELSEWHERE,
            reason=f"PR #{self.pr_number} merged at head {reading.head_oid[:7]}, not at "
            f"{self.head[:7]}, the head that was checked",
        )

    def refused(self, reason_kind: str, reason: str) -> Landing:
        return self.end(END_REFUSED, reason_kind=reason_kind, reason=reason)

    def not_allowed(self, reading: Reading, name: str) -> Landing:
        """Refused before request `name`, which the caller allowed none of —
        the first refusal in the one order."""
        return self.refused(
            REQUEST_NOT_ALLOWED,
            f"PR #{self.pr_number} reads {reading.describe()}, so landing it takes a {name}, "
            "and the landing allows no merge and no enqueue: nothing was sent",
        )

    def bad_shape(self, reason_kind: str, reason: str, lenient: bool) -> Landing | None:
        """A queue that would not make the squash commit: refused, or — for a
        PR the caller waits for in it — a warning."""
        if not lenient:
            return self.refused(reason_kind, reason)
        self.warnings.append(Notice(reason_kind, reason))
        return None

    def moved(self, reading: Reading) -> str:
        return (
            f"a reading finds PR #{self.pr_number} at head {reading.head_oid[:7]}, not at "
            f"{self.head[:7]}, the head that was checked"
        )

    def dropped(self, reading: Reading) -> str:
        removal = reading.removal
        when = f" at {removal.at}" if removal is not None and removal.at else ""
        why = f" (GitHub says: {removal.reason})" if removal is not None and removal.reason else ""
        return (
            f"the merge queue dropped PR #{self.pr_number} at its current head "
            f"{reading.head_oid[:7]}{when}{why}; that head is not enqueued again unchanged "
            "unless the landing allows a dropped head"
        )

    def took(self, reading: Reading) -> None:
        """A reading taken, and written."""
        self.saw(reading)
        self.written(reading)

    def saw(self, reading: Reading) -> None:
        """A reading taken: the landing's last."""
        self.reading = reading

    def written(self, reading: Reading) -> None:
        self.emit(wait_reading_document(self.pr_number, reading))

    def requesting(self, name: str, cmd: Sequence[str]) -> None:
        """Written before request `name` is sent (:data:`_ON_SEND`): its pin,
        and which attempt it is."""
        attempt = self.attempts.get(name, 0) + 1
        self.attempts[name] = attempt
        self.in_flight.add(name)
        self.emit(
            _document(
                self.pr_number,
                event="requesting",
                request=name,
                head=_pinned(cmd),
                attempt=attempt,
            )
        )
        self.sending = True

    def requested(self, name: str, outcome: Outcome) -> None:
        """Written once request `name` is settled — only after its
        `requesting`: a dequeue that sent nothing writes neither."""
        if name not in self.in_flight:
            return
        self.in_flight.discard(name)
        self.emit(_document(self.pr_number, event="requested", request=name, **outcome.as_json()))

    def emit(self, document: dict[str, Any]) -> None:
        """Tell `on_event` of one event. A write that fails — the stream
        closed: an `OSError`, as a broken pipe raises, or a `ValueError`, as
        a closed file does — before any request ends the landing with nothing
        sent: a `requesting` not written is a request not sent. Once a
        request has gone out, it stops the writing and not the landing,
        which finishes its wait and its dequeue: a PR handed to the queue is
        never left unwatched for a stream nobody reads."""
        if self.on_event is None or not self.writing:
            return
        try:
            self.on_event(document)
        except (OSError, ValueError):
            if not self.sending:
                raise
            self.writing = False

    def end(
        self,
        ended: str,
        *,
        reason_kind: str | None = None,
        reason: str | None = None,
        would: str | None = None,
        dequeue: Outcome | None = None,
    ) -> Landing:
        return Landing(
            self.pr_number,
            ended,
            self.head,
            self.clearance,
            landing_longest_seconds(self.options.seconds),
            dry_run=self.dry_run,
            reason_kind=reason_kind,
            reason=reason,
            would=would,
            reading=self.reading,
            sent=self.sent,
            dequeue=dequeue,
            shape=self.shape,
            warnings=tuple(self.warnings),
        )


def _pinned(cmd: Sequence[str]) -> str | None:
    """The head a request is pinned to (`--match-head-commit`); None unpinned."""
    args = list(cmd)
    if "--match-head-commit" in args[:-1]:
        return args[args.index("--match-head-commit") + 1]
    return None


# ---- the documents `pkit pull-request --json` writes --------------------------


def reading_document(pr_number: int, *, gh: GhRunner | None = None) -> dict[str, Any]:
    """`pkit pull-request read`'s document: the reading, or why there is none."""
    try:
        reading = read(pr_number, gh=gh)
    except Unreadable as exc:
        return _document(pr_number, reading=None, unreadable=str(exc))
    return _document(pr_number, reading=reading.as_json(), unreadable=None)


def squash_defaults_document(*, gh: GhRunner | None = None) -> dict[str, Any]:
    """`pkit pull-request squash-defaults`'s document: the title and message
    defaults, or why they could not be read."""
    try:
        title, message = squash_commit_defaults(gh=gh)
    except Unreadable as exc:
        return {
            "schema_version": SCHEMA_VERSION,
            "title": None,
            "message": None,
            "unreadable": str(exc),
        }
    return {
        "schema_version": SCHEMA_VERSION,
        "title": title,
        "message": message,
        "unreadable": None,
    }


def outcome_document(
    pr_number: int, outcome: Outcome, clearance: session_guard.Clearance
) -> dict[str, Any]:
    """The document of a request — `merge`, `enqueue`, `dequeue` — and of the
    guard that let it be made: `accepted` null when whether it was made is
    not known (unconfirmed); `reason_kind` `not-made`, `unanswered` or null;
    `guard` how it cleared."""
    return {
        "schema_version": SCHEMA_VERSION,
        "pull_request": pr_number,
        **outcome.as_json(),
        "guard": clearance.as_json(),
    }


def refusal_document(pr_number: int, refusal: session_guard.Refusal) -> dict[str, Any]:
    """The document of a request the cross-repository guard refused: nothing
    was asked of the service, `accepted` false, `reason_kind`
    `foreign-repository`, and `guard` what it compared."""
    return {
        "schema_version": SCHEMA_VERSION,
        "pull_request": pr_number,
        "accepted": False,
        "exit_code": None,
        "reason": refusal.reason,
        "reason_kind": session_guard.FOREIGN_REPOSITORY,
        "guard": refusal.as_json(),
    }


def deletion_document(
    pr_number: int, expected: str, deletion: BranchDeletion, clearance: session_guard.Clearance
) -> dict[str, Any]:
    """`pkit pull-request delete-branch`'s document: the head that was
    expected, the PR's own head (`merged_head`), what became of the branch,
    and how the guard cleared."""
    return {
        "schema_version": SCHEMA_VERSION,
        "pull_request": pr_number,
        "expected": expected,
        **deletion.as_json(),
        "guard": clearance.as_json(),
    }


def deletion_refusal_document(
    pr_number: int, expected: str, refusal: session_guard.Refusal
) -> dict[str, Any]:
    """The document of a branch deletion the cross-repository guard refused:
    nothing was read or asked of the service, `outcome` refused, `reason_kind`
    `foreign-repository`, `merged_head` null, and `guard` what it compared."""
    deletion = BranchDeletion(
        REFUSED, reason_kind=session_guard.FOREIGN_REPOSITORY, reason=refusal.reason
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "pull_request": pr_number,
        "expected": expected,
        **deletion.as_json(),
        "guard": refusal.as_json(),
    }


def wait_reading_document(pr_number: int, reading: Reading) -> dict[str, Any]:
    """One line of `pkit pull-request wait`'s stream: a reading that changed."""
    return _document(pr_number, event="reading", reading=reading.as_json())


def wait_end_document(
    pr_number: int, wait: Wait | None, unreadable: str | None = None
) -> dict[str, Any]:
    """The last line of `pkit pull-request wait`'s stream: how it ended, or why
    a reading could not be taken."""
    return _document(
        pr_number,
        event="end",
        ended=wait.ended if wait is not None else None,
        reading=wait.reading.as_json() if wait is not None else None,
        unreadable=unreadable,
    )


def render_json(document: Mapping[str, Any]) -> str:
    """A document as one line of JSON, keys sorted, so a stream of them reads
    line by line."""
    return json.dumps(document, sort_keys=True, ensure_ascii=False)


def _document(pr_number: int, **fields: Any) -> dict[str, Any]:
    return {"schema_version": SCHEMA_VERSION, "pull_request": pr_number, **fields}


# ---- reading GitHub ----------------------------------------------------------


def _runner(gh: GhRunner | None) -> GhRunner:
    """`gh`, else the module's runner, looked up at call time."""
    return gh if gh is not None else run_gh


def _acting(clearance: session_guard.Clearance, cwd: Path) -> GhRunner:
    """The runner a request that changes the service runs on, once `clearance`
    covers `cwd`: `gh` from `cwd` — where the guard looked, and nowhere else."""
    return gh_runner(session_guard.require(clearance, cwd))


def _requesting(run: GhRunner) -> GhRunner:
    """`run` for a request: the module's own `gh` bounded as a request is
    (:data:`GH_REQUEST_SECONDS`); a runner handed in, as it is."""
    return _Gh(run.cwd, requests=True) if isinstance(run, _Gh) else run


def _run(run: GhRunner, cmd: list[str]) -> subprocess.CompletedProcess[str]:
    """Run a reading, raising :class:`Unreadable` when `gh` cannot be run or
    does not answer within its bound."""
    try:
        return run(cmd)
    except FileNotFoundError as exc:
        raise Unreadable("`gh` not on PATH") from exc
    except OSError as exc:  # on PATH but not runnable: permissions, bad binary
        raise Unreadable(f"`gh` could not be run ({exc})") from exc
    except subprocess.TimeoutExpired as exc:
        raise Unreadable(f"`gh` did not answer within {exc.timeout:g} s, and was ended") from None


def _cross_repository(pr: Mapping[str, Any]) -> bool:
    """Whether the PR's head is in another repository; an answer that does not
    say reads as one that is, so nothing is done on a branch that may not be
    the PR's."""
    return pr.get("isCrossRepository", True) is not False


def _pull_request(pr_number: int, fields: str, run: GhRunner) -> dict[str, Any]:
    """The pull request's `fields`, as the GraphQL API answers them."""
    query = (
        "query($owner: String!, $repo: String!, $number: Int!) {\n"
        "  repository(owner: $owner, name: $repo) {\n"
        "    pullRequest(number: $number) {\n"
        f"{fields}\n"
        "    }\n"
        "  }\n"
        "}\n"
    )
    data = _graphql(
        run, query, ["-F", "owner={owner}", "-F", "repo={repo}", "-F", f"number={pr_number}"]
    )
    pr = _mapping(_mapping(data.get("repository")).get("pullRequest"))
    if not pr:
        raise Unreadable(f"the answer names no pull request #{pr_number}")
    return pr


def _graphql(run: GhRunner, query: str, variables: list[str]) -> dict[str, Any]:
    """The `data` GitHub's GraphQL API answers `query` with, given `variables`
    as gh's `-f`/`-F` arguments. Raises :class:`Unreadable` when gh fails or
    the answer carries errors — :class:`_UnknownField` for a field the API
    does not know."""
    proc = _run(run, ["gh", "api", "graphql", "-f", f"query={query}", *variables])
    payload = _mapping(_json(proc.stdout))
    errors = payload.get("errors")
    if proc.returncode != 0 or errors:
        reason = _error_text(proc.stderr, errors)
        if _UNKNOWN_FIELD in reason:
            raise _UnknownField(reason)
        raise Unreadable(reason)
    return _mapping(payload.get("data"))


def _knows_merge_queues(pr_number: int, run: GhRunner) -> bool:
    """Whether the API knows `isMergeQueueEnabled`, asked for alone so that no
    other field it lacks answers for it. Raises :class:`Unreadable` on any
    other failure."""
    try:
        _pull_request(pr_number, f"      {_QUEUE_FIELD}", run)
    except _UnknownField as exc:
        if f"'{_QUEUE_FIELD}'" in str(exc):
            return False
        raise Unreadable(str(exc)) from None
    return True


def _reading(pr: Mapping[str, Any]) -> Reading:
    queue = _mapping(pr.get("mergeQueue"))
    entry = _mapping(pr.get("mergeQueueEntry"))
    events = [
        _mapping(e) for e in _list(_mapping(pr.get("timelineItems")).get("nodes")) if _mapping(e)
    ]
    return Reading(
        has_queue=bool(pr.get("isMergeQueueEnabled")),
        merge_method=str(_mapping(queue.get("configuration")).get("mergeMethod") or ""),
        pr_id=str(pr.get("id") or ""),
        pr_state=str(pr.get("state") or ""),
        merged_at=str(pr.get("mergedAt") or ""),
        head_oid=str(pr.get("headRefOid") or ""),
        in_queue=bool(pr.get("isInMergeQueue")) or bool(entry),
        position=_int_or_none(entry.get("position")),
        entry_state=str(entry.get("state") or ""),
        eta_seconds=_int_or_none(entry.get("estimatedTimeToMerge")),
        waiting_to_enter=bool(pr.get("autoMergeRequest")),
        ever_queued=any(e.get("__typename") == _ADDED_EVENT for e in events),
        removal=_last_removal(events),
        head_ref=str(pr.get("headRefName") or ""),
        cross_repository=_cross_repository(pr),
        merge_commit=str(_mapping(pr.get("mergeCommit")).get("oid") or ""),
    )


def _last_removal(events: list[dict[str, Any]]) -> Removal | None:
    """The queue dropping the PR, when that is the last thing the queue did with it."""
    if not events or events[-1].get("__typename") != _REMOVED_EVENT:
        return None
    last = events[-1]
    return Removal(
        at=str(last.get("createdAt") or ""),
        reason=str(last.get("reason") or ""),
        head_oid=str(_mapping(last.get("beforeCommit")).get("oid") or ""),
    )


def _json(text: str | None) -> object:
    try:
        return cast(object, json.loads(text or "null"))
    except json.JSONDecodeError:
        return None


def _mapping(value: object) -> dict[str, Any]:
    return cast(dict[str, Any], value) if isinstance(value, dict) else {}


def _list(value: object) -> list[object]:
    return cast(list[object], value) if isinstance(value, list) else []


def _int_or_none(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _duration(seconds: int) -> str:
    if seconds < 60:
        return "under a minute"
    return f"about {round(seconds / 60)} min"


def _error_text(stderr: str | None, errors: object) -> str:
    """The reason a read failed: the GraphQL errors' messages, else gh's stderr."""
    messages = [str(_mapping(e).get("message")) for e in _list(errors) if _mapping(e)]
    if any(messages):
        return "; ".join(m for m in messages if m)
    return (stderr or "").strip() or "gh answered nothing"
