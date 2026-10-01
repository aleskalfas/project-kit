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
- **taking a PR out of the queue** (:func:`dequeue`).

Merged is what GitHub reports, never what a command's exit implies: on a base
that requires a queue, a plain merge request enqueues and exits 0, so a caller
reads the PR again after a direct merge before it counts it merged.

When to land, and what follows a landing, is the caller's: the gates it runs,
what it refuses, the branch clean-up. project-management's merge verbs reach
this module through `pkit pull-request` and its JSON documents, since they run
as scripts that do not import the package; `pkit release merge` imports it.

The requests that change the service's state — the merge, the enqueue, the
dequeue — run the cross-repository guard (ADR-061 point 6, `session_guard`):
each requires a clearance and the directory it acts in, and runs `gh` there
unless handed a client of its own, so a caller that imports them can neither
skip the guard nor clear one directory and act in another. The readings and the
wait change nothing and run no guard.

`gh` is the hosting service's client here. Every call runs it from the
caller's directory — it resolves the repository from the git remote — with the
caller's environment, so a host pinned through `GH_HOST` reaches it.
"""

from __future__ import annotations

import json
import subprocess
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from project_kit import session_guard

#: The version of the documents `pkit pull-request --json` writes; a reader
#: refuses one it does not know.
SCHEMA_VERSION = 1

#: The queue merge method that makes the convention's one squash commit.
SQUASH = "SQUASH"

#: The repository's squash-commit defaults the convention needs: the queue
#: composes the squash commit from them, not from the merge command.
PR_TITLE = "PR_TITLE"
PR_BODY = "PR_BODY"

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
      headRefOid"""

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
            "merged": self.merged,
            "queued": self.queued,
            "squashes": self.squashes,
            "dropped_head": self.dropped_head,
            "description": self.describe(),
        }


@dataclass(frozen=True)
class Outcome:
    """What a request to the hosting service came to."""

    accepted: bool
    #: `gh`'s exit code; None when it could not be run, or the request was
    #: judged on a reading rather than on gh's exit.
    exit_code: int | None = 0
    #: Why it was not accepted: gh's own words, or why gh could not run.
    reason: str = ""

    def as_json(self) -> dict[str, Any]:
        return {"accepted": self.accepted, "exit_code": self.exit_code, "reason": self.reason}


@dataclass(frozen=True)
class Wait:
    """How a wait for the queue's merge ended: `ended` is :data:`MERGED`,
    :data:`STILL_QUEUED` (the time ran out), :data:`LEFT` or
    :data:`HEAD_MOVED`; `reading` is the last reading taken."""

    ended: str
    reading: Reading


def run_gh(argv: Sequence[str]) -> subprocess.CompletedProcess[str]:
    """Run `gh` from the working directory, in this process's environment."""
    return subprocess.run(list(argv), capture_output=True, text=True, check=False)


def gh_runner(cwd: Path) -> GhRunner:
    """A runner of `gh` from `cwd`, for a caller whose repository is not the
    working directory's."""

    def run(argv: Sequence[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(list(argv), capture_output=True, text=True, cwd=cwd, check=False)

    return run


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
    gh: GhRunner | None = None,
) -> Outcome:
    """Squash-merge the PR with `subject` as the landed commit's subject.

    `clearance` is the cross-repository guard's for `cwd`, the directory `gh`
    runs in unless `gh` is given (:func:`session_guard.require`). GitHub's
    default subject for a single-commit PR is the commit message, so the
    subject is always passed. `head_oid`, the head the caller checked, pins
    the merge (`--match-head-commit`): a push in between fails it instead of
    landing commits nothing checked. Deliberately without `--delete-branch`:
    that flag makes gh check out the base locally and delete the local head,
    and the whole command exits non-zero when the working tree cannot do so —
    after the remote merge has landed — so the exit code would no longer report
    the merge alone.

    Accepted is not proof of a merge: on a base that requires a queue, gh
    enqueues and exits 0. Read the PR afterwards (:func:`read`).
    """
    run = _acting(gh, clearance, cwd)
    cmd = ["gh", "pr", "merge", str(pr_number), "--squash", "--subject", subject]
    if head_oid:
        cmd += ["--match-head-commit", head_oid]
    if admin:
        cmd.append("--admin")
    return _request(run, cmd)


def enqueue(
    pr_number: int,
    *,
    cwd: Path,
    clearance: session_guard.Clearance,
    head_oid: str = "",
    gh: GhRunner | None = None,
) -> Outcome:
    """Put the PR in its base branch's merge queue: `gh pr merge <N> --auto`,
    pinned to the head the caller checked.

    `clearance` and `cwd` as for :func:`squash_merge`. GitHub ignores a merge
    method, a subject and a body passed with a queued merge, so none is
    passed; a caller checks the queue's method and the repository's
    squash-commit defaults instead. With `--auto`, a PR whose own required
    checks are still running is taken in once they pass. Never `--admin`,
    which merges around the queue. The PR has not merged when this returns.
    """
    run = _acting(gh, clearance, cwd)
    cmd = ["gh", "pr", "merge", str(pr_number), "--auto"]
    if head_oid:
        cmd += ["--match-head-commit", head_oid]
    return _request(run, cmd)


def dequeue(
    pr_number: int,
    *,
    cwd: Path,
    clearance: session_guard.Clearance,
    gh: GhRunner | None = None,
) -> Outcome:
    """Take the PR out of its base's merge queue — or, while auto-merge still
    holds it until its checks pass, cancel that — and confirm it is out.

    `clearance` and `cwd` as for :func:`squash_merge`. The PR is read first.
    `gh pr merge --disable-auto` cancels the auto-merge; on a PR already in
    the queue gh answers "already queued to merge" and changes nothing, so
    such a PR is taken out through GitHub's own `dequeuePullRequest`. Accepted
    once a reading shows the PR neither queued nor merged.
    """
    run = _acting(gh, clearance, cwd)
    try:
        before = read(pr_number, gh=run)
    except Unreadable as exc:
        return Outcome(False, None, f"PR #{pr_number} could not be read: {exc}")
    if before.merged:
        return Outcome(False, None, f"PR #{pr_number} has merged ({before.describe()})")
    if not before.queued:
        return Outcome(True, None)
    if before.in_queue and before.pr_id:
        cmd = ["gh", "api", "graphql", "-f", f"query={_DEQUEUE}", "-f", f"id={before.pr_id}"]
    else:
        cmd = ["gh", "pr", "merge", str(pr_number), "--disable-auto"]
    outcome = _request(run, cmd)
    if not outcome.accepted:
        return outcome
    try:
        after = read(pr_number, gh=run)
    except Unreadable as exc:
        return Outcome(
            False, None, f"whether PR #{pr_number} left the queue could not be read: {exc}"
        )
    if after.merged or after.queued:
        return Outcome(False, None, f"PR #{pr_number} is still {after.describe()}")
    return Outcome(True, outcome.exit_code)


# ---- the wait ----------------------------------------------------------------

# The wait's clock and sleep, looked up when a wait starts.
_sleep: Callable[[float], None] = time.sleep
_monotonic: Callable[[], float] = time.monotonic


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
    guard that let it be made: `refused_by` null, `guard` how it passed."""
    return {
        "schema_version": SCHEMA_VERSION,
        "pull_request": pr_number,
        **outcome.as_json(),
        "refused_by": None,
        "guard": clearance.as_json(),
    }


def refusal_document(pr_number: int, refusal: session_guard.Refusal) -> dict[str, Any]:
    """The document of a request the cross-repository guard refused: nothing
    was asked of the service, `accepted` false, `refused_by`
    `foreign-repository`, and `guard` what it compared."""
    return {
        "schema_version": SCHEMA_VERSION,
        "pull_request": pr_number,
        "accepted": False,
        "exit_code": None,
        "reason": refusal.reason,
        "refused_by": session_guard.FOREIGN_REPOSITORY,
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


def _acting(gh: GhRunner | None, clearance: session_guard.Clearance, cwd: Path) -> GhRunner:
    """The runner a request that changes the service runs on, once `clearance`
    covers `cwd`: `gh`, else `gh` from `cwd` — where the guard looked."""
    where = session_guard.require(clearance, cwd)
    return gh if gh is not None else gh_runner(where)


def _run(run: GhRunner, cmd: list[str]) -> subprocess.CompletedProcess[str]:
    """Run `cmd`, raising :class:`Unreadable` when `gh` cannot be run."""
    try:
        return run(cmd)
    except FileNotFoundError as exc:
        raise Unreadable("`gh` not on PATH") from exc
    except OSError as exc:  # on PATH but not runnable: permissions, bad binary
        raise Unreadable(f"`gh` could not be run ({exc})") from exc


def _request(run: GhRunner, cmd: list[str]) -> Outcome:
    """Run a request; its outcome, with gh's reason when it was refused."""
    try:
        proc = run(cmd)
    except FileNotFoundError:
        return Outcome(False, None, "`gh` not on PATH")
    except OSError as exc:
        return Outcome(False, None, f"`gh` could not be run ({exc})")
    if proc.returncode != 0:
        return Outcome(False, proc.returncode, (proc.stderr or "").strip())
    return Outcome(True, proc.returncode)


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
    proc = _run(
        run,
        [
            "gh",
            "api",
            "graphql",
            "-f",
            f"query={query}",
            "-F",
            "owner={owner}",
            "-F",
            "repo={repo}",
            "-F",
            f"number={pr_number}",
        ],
    )
    payload = _mapping(_json(proc.stdout))
    errors = payload.get("errors")
    if proc.returncode != 0 or errors:
        reason = _error_text(proc.stderr, errors)
        if _UNKNOWN_FIELD in reason:
            raise _UnknownField(reason)
        raise Unreadable(reason)
    data = _mapping(payload.get("data"))
    pr = _mapping(_mapping(data.get("repository")).get("pullRequest"))
    if not pr:
        raise Unreadable(f"the answer names no pull request #{pr_number}")
    return pr


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
