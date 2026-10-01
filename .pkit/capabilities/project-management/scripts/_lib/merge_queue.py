"""Whether a PR's base branch merges through a queue, and where the PR stands
in it — the reading the merge verbs take before they merge (#1011,
[project-management:DEC-026-work-ownership-lifecycle]).

A merge queue takes a PR in and makes the merge itself. It builds the merge
the PR would make on top of the base branch and of whatever is queued ahead
of it, runs the base's required checks on that prospective merge commit, and
merges it once they pass, by the queue's own merge method. A PR whose checks
fail there, or that no longer merges cleanly, leaves the queue unmerged.
Merging directly on such a base goes around the queue, so the merge verbs read
this first and hand the PR to the queue (`_lib.pr_merge.land`).

One GraphQL read answers what a verb needs: whether the base has a queue and
its merge method; whether the PR is in it, with its position, state and
estimated time to merge; whether auto-merge holds it until its own required
checks pass, before it may enter; the PR's head; whether it has merged; and
whether the queue's last word on it was to drop it, at which head and why. The
repository's squash-commit defaults, which the queue composes its squash
commit from, are a second read (:func:`squash_commit_defaults`).
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from _lib.gh import gh_run

# The queue merge method that makes the convention's one squash commit (DEC-013).
SQUASH = "SQUASH"

# The repository's squash-commit defaults the convention needs (DEC-013): the
# queue composes the squash commit from them, not from the merge command.
PR_TITLE = "PR_TITLE"
PR_BODY = "PR_BODY"

# How long the wait sleeps between two readings.
POLL_SECONDS = 15.0

# A wait that follows the queue's own estimate waits that long plus this
# margin, and never longer than the cap.
ETA_MARGIN_SECONDS = 120.0
MAX_WAIT_SECONDS = 30 * 60.0

# How a wait ended (:class:`Wait`).
MERGED = "merged"
STILL_QUEUED = "queued"
LEFT = "left"
HEAD_MOVED = "head-moved"

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
        this one's: re-enqueueing what the queue refused needs `--force`."""
        if self.removal is None or self.queued or self.merged:
            return False
        return self.removal.head_oid in ("", self.head_oid)

    def describe(self) -> str:
        """Where the PR stands, as one phrase for a verb's output."""
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


@dataclass(frozen=True)
class Wait:
    """How a wait for the queue's merge ended: `ended` is :data:`MERGED`,
    :data:`STILL_QUEUED` (the time ran out), :data:`LEFT` or
    :data:`HEAD_MOVED`; `reading` is the last reading taken."""

    ended: str
    reading: Reading


def read(pr_number: int, config: dict[str, Any]) -> Reading:
    """Read where PR `pr_number` stands with its base branch's merge queue.

    The repository is the one `gh` resolves for the working directory, as for
    every other pm `gh` call. Raises :class:`Unreadable` when `gh` cannot
    answer. Only an API that does not know `isMergeQueueEnabled` itself answers
    that there is no queue: when the full read fails on some other unknown
    field, that field alone is asked for, and a host that knows it has queues,
    so the read is unreadable rather than "no queue".
    """
    try:
        pr = _pull_request(pr_number, f"{_PR_FIELDS}\n{_QUEUE_FIELDS}", config)
    except _UnknownField as exc:
        if _knows_merge_queues(pr_number, config):
            raise Unreadable(str(exc)) from None
        return _reading(_pull_request(pr_number, _PR_FIELDS, config))
    return _reading(pr)


def squash_commit_defaults(config: dict[str, Any]) -> tuple[str, str]:
    """The repository's default squash-commit title and message, as GitHub
    names them (`PR_TITLE` or `COMMIT_OR_PR_TITLE`; `PR_BODY`,
    `COMMIT_MESSAGES` or `BLANK`). A merge queue composes its squash commit
    from these and ignores what the merge command asks for. Raises
    :class:`Unreadable` when they cannot be read."""
    try:
        proc = gh_run(["gh", "api", "repos/{owner}/{repo}"], config, check=False)
    except FileNotFoundError as exc:
        raise Unreadable("`gh` not on PATH") from exc
    if proc.returncode != 0:
        raise Unreadable((proc.stderr or "").strip() or "gh answered nothing")
    try:
        repository = json.loads(proc.stdout or "null")
    except json.JSONDecodeError:
        repository = None
    if not isinstance(repository, dict):
        raise Unreadable("the answer names no repository")
    title = repository.get("squash_merge_commit_title")
    message = repository.get("squash_merge_commit_message")
    if not (isinstance(title, str) and isinstance(message, str)):
        raise Unreadable(
            "the repository's squash-commit defaults are not in the answer (an account "
            "without access to the repository's settings does not see them)"
        )
    return title, message


def wait_for_merge(
    pr_number: int,
    config: dict[str, Any],
    *,
    timeout_seconds: float | None,
    on_change: Callable[[Reading], None],
    head_oid: str = "",
    interval_seconds: float = POLL_SECONDS,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
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
    `head_oid`, the head the caller's gates checked, a reading whose head
    differs ends the wait at once (:data:`HEAD_MOVED`): commits nobody checked
    must not merge. `on_change` is handed each reading whose description
    differs from the one before. Raises :class:`Unreadable` when a reading
    cannot be taken.
    """
    start = clock()
    deadline = start + (MAX_WAIT_SECONDS if timeout_seconds is None else timeout_seconds)
    last_description = ""
    seen_out = False
    estimated = timeout_seconds is not None
    while True:
        reading = read(pr_number, config)
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
                clock() + reading.eta_seconds + ETA_MARGIN_SECONDS,
            )
        remaining = deadline - clock()
        if remaining <= 0:
            if not seen_out:
                return Wait(STILL_QUEUED, reading)
            sleep(interval_seconds)
            continue
        sleep(min(interval_seconds, remaining))


def _pull_request(pr_number: int, fields: str, config: dict[str, Any]) -> dict[str, Any]:
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
    try:
        proc = gh_run(
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
            config,
            check=False,
        )
    except FileNotFoundError as exc:
        raise Unreadable("`gh` not on PATH") from exc
    try:
        payload = json.loads(proc.stdout or "null")
    except json.JSONDecodeError:
        payload = None
    errors = payload.get("errors") if isinstance(payload, dict) else None
    if proc.returncode != 0 or errors:
        reason = _error_text(proc.stderr, errors)
        if _UNKNOWN_FIELD in reason:
            raise _UnknownField(reason)
        raise Unreadable(reason)
    data = payload.get("data") if isinstance(payload, dict) else None
    repository = data.get("repository") if isinstance(data, dict) else None
    pr = repository.get("pullRequest") if isinstance(repository, dict) else None
    if not isinstance(pr, dict):
        raise Unreadable(f"the answer names no pull request #{pr_number}")
    return pr


def _knows_merge_queues(pr_number: int, config: dict[str, Any]) -> bool:
    """Whether the API knows `isMergeQueueEnabled`, asked for alone so that no
    other field it lacks answers for it. Raises :class:`Unreadable` on any
    other failure."""
    try:
        _pull_request(pr_number, f"      {_QUEUE_FIELD}", config)
    except _UnknownField as exc:
        if f"'{_QUEUE_FIELD}'" in str(exc):
            return False
        raise Unreadable(str(exc)) from None
    return True


def _reading(pr: dict[str, Any]) -> Reading:
    queue = _mapping(pr.get("mergeQueue"))
    entry = _mapping(pr.get("mergeQueueEntry"))
    events = [e for e in _mapping(pr.get("timelineItems")).get("nodes") or [] if _mapping(e)]
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


def _mapping(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _int_or_none(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _duration(seconds: int) -> str:
    if seconds < 60:
        return "under a minute"
    return f"about {round(seconds / 60)} min"


def _error_text(stderr: str, errors: object) -> str:
    """The reason a read failed: the GraphQL errors' messages, else gh's stderr."""
    if isinstance(errors, list):
        messages = [str(e.get("message")) for e in errors if isinstance(e, dict)]
        if any(messages):
            return "; ".join(m for m in messages if m)
    return (stderr or "").strip() or "gh answered nothing"
