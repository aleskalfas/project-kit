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
  request.

Merged is what GitHub reports, never what a command's exit implies: on a base
that requires a queue, a plain merge request enqueues and exits 0, so a caller
reads the PR again after a direct merge before it counts it merged.

When to land, and what follows a landing, is the caller's: the gates it runs,
what it refuses, its own steps after the merge, and when the head branch is
deleted — after those steps. The local branch is the caller's too: it is not
on the hosting service. project-management's merge verbs reach this module
through `pkit pull-request` and its JSON documents, since they run as scripts
that do not import the package; `pkit release merge` imports it.

The requests that change the service's state — the merge, the enqueue, the
dequeue, the branch deletion — run the cross-repository guard (ADR-061 point
6, `session_guard`): each requires a clearance and the directory it acts in,
and runs `gh` there, with no client of the caller's, so a caller that imports
them can neither skip the guard nor clear one directory and act in another.
The readings and the wait change nothing and run no guard.

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
line, `gh`'s own refusal before it sent anything, or `gh` not started at all.
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
#: unconfirmed: the PR could not be read since to see it out of the queue.
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
    #: (:data:`HAS_MERGED`) or still queued after the service accepted it.
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
    out. Queued, the dequeue is sent: `gh pr merge --disable-auto` cancels
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
        return Outcome(False, None, f"PR #{pr_number} could not be read: {exc}")
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
    sent = _send(_requesting(run), cmd)
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
# (`HTTP 422: …`, `gh: … (HTTP 403)`), and gh's own refusal before it sent
# anything, which it marks with its failure or warning sign (`X Pull request
# #N is not mergeable: …`, `! Pull request #N is already queued to merge`).
# Nothing else is taken for an answer.
_ANSWERED = re.compile(r"^GraphQL: |\bHTTP 4\d\d\b|^[X!] Pull request ", re.MULTILINE)


def _send(run: GhRunner, cmd: list[str]) -> _Sent:
    """Send a request, telling three ends apart, and date it.

    Applied: gh exited 0 and the answer names no errors. Not applied, only on
    an answer recognised as one: the GraphQL errors the answer carries, or
    gh's words in a shape :data:`_ANSWERED` knows — the service's `GraphQL:`
    error, an HTTP 4xx, gh's own refusal before it sent anything — or gh
    could not be started, so nothing was sent. No usable answer otherwise: gh
    ended at its bound, or by a signal — a negative exit, whatever it printed
    — or any other failure, its words kept in `said`; the request may have
    been applied or not.
    """
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


_MERGING = _Asked("merge", "neither merged nor queued", _merged_or_queued)
_ENQUEUING = _Asked("enqueue", "neither queued nor merged", _merged_or_queued)
_DEQUEUING = _Asked("dequeue", "queued", _out_of_the_queue, confirmations=2)


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
    sent = _send(_requesting(run), cmd)
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
    is what the readings saw, never that the request was not made. A reading
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
    while True:
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
    :func:`delete_branch`'s `expect` is named in on the command line."""
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
    sent = _send(_requesting(run), cmd)
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
    merge, and the caller takes the PR out (:func:`dequeue`). `on_change` is
    handed each reading whose description differs from the one before. Raises
    :class:`Unreadable` when a reading cannot be taken.
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
        if reading.describe() != last_description:
            last_description = reading.describe()
            on_change(reading)
        if reading.merged:
            return Wait(MERGED, reading)
        if head_oid and reading.head_oid and reading.head_oid != head_oid:
            return Wait(HEAD_MOVED, reading)
        if reading.pr_state == "CLOSED":
            return Wait(LEFT, reading)
        if reading.queued:
            seen_out = False
        elif seen_out:
            return Wait(LEFT, reading)
        else:
            seen_out = True
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


def wait_limit(seconds: float | None) -> str:
    """How long a wait of `seconds` lasts, as a phrase: None follows the
    queue's estimate (:func:`wait_for_merge`)."""
    if seconds is None:
        return (
            f"as long as the queue estimates plus {ETA_MARGIN_SECONDS / 60:g} min, "
            f"at most {MAX_WAIT_SECONDS / 60:g} min"
        )
    return f"up to {seconds / 60:g} min"


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
