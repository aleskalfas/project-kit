"""Whether a PR's base branch merges through a queue, and where the PR stands
in it — the reading the merge verbs take before they merge (#1011,
[project-management:DEC-026-work-ownership-lifecycle]).

A merge queue takes a PR in and makes the merge itself. It builds the merge
the PR would make on top of the base branch and of whatever is queued ahead
of it, runs the base's required checks on that prospective merge commit, and
merges it once they pass, by the queue's own merge method. A PR whose checks
fail there, or that no longer merges cleanly, leaves the queue unmerged.
Merging directly on such a base goes around the queue, so the merge verbs read
this first: `done-work` enqueues and waits for the merge, `merge-pr` refuses.

One GraphQL read answers everything a verb needs: whether the base has a
queue and its merge method; whether the PR is in it, with its position, state
and estimated time to merge; whether auto-merge holds it until its own
required checks pass, before it may enter; and whether it has merged.
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

# How long the wait sleeps between two readings.
POLL_SECONDS = 15.0

# What a GraphQL API without merge queues answers when asked about one (an
# older GitHub Enterprise Server): a base on such a host has no queue.
_UNKNOWN_FIELD = "doesn't exist on type"

_QUERY = """\
query($owner: String!, $repo: String!, $number: Int!) {
  repository(owner: $owner, name: $repo) {
    pullRequest(number: $number) {
      state
      mergedAt
      isMergeQueueEnabled
      isInMergeQueue
      mergeQueue { configuration { mergeMethod } }
      mergeQueueEntry { position state estimatedTimeToMerge }
      autoMergeRequest { enabledAt }
    }
  }
}
"""


class Unreadable(Exception):
    """The reading could not be taken; the message says why."""


@dataclass(frozen=True)
class Reading:
    """Where a PR stands with its base branch's merge queue."""

    #: The base branch merges through a queue.
    has_queue: bool
    #: The queue's merge method (`SQUASH`, `MERGE`, `REBASE`); empty without one.
    merge_method: str = ""
    #: The PR's state: `OPEN`, `CLOSED` or `MERGED`.
    pr_state: str = ""
    merged_at: str = ""
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


def read(pr_number: int, config: dict[str, Any]) -> Reading:
    """Read where PR `pr_number` stands with its base branch's merge queue.

    The repository is the one `gh` resolves for the working directory, as for
    every other pm `gh` call. Raises :class:`Unreadable` when `gh` cannot
    answer; an API that does not know merge queues answers that there is none.
    """
    try:
        proc = gh_run(
            [
                "gh",
                "api",
                "graphql",
                "-f",
                f"query={_QUERY}",
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
            return Reading(has_queue=False)
        raise Unreadable(reason)
    data = payload.get("data") if isinstance(payload, dict) else None
    repository = data.get("repository") if isinstance(data, dict) else None
    pr = repository.get("pullRequest") if isinstance(repository, dict) else None
    if not isinstance(pr, dict):
        raise Unreadable(f"the answer names no pull request #{pr_number}")
    return _reading(pr)


def wait_for_merge(
    pr_number: int,
    config: dict[str, Any],
    *,
    timeout_seconds: float,
    on_change: Callable[[Reading], None],
    interval_seconds: float = POLL_SECONDS,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
) -> Reading:
    """Read the queue until the PR merges, leaves it, or the time runs out.

    Returns the last reading: merged; out of the queue, closed or seen out of
    it twice running, so a reading taken just as GitHub takes the PR in is not
    mistaken for one that left; or still queued when `timeout_seconds` passed.
    The first reading is always taken, so a timeout of 0 reads once.
    `on_change` is handed each reading whose description differs from the one
    before. Raises :class:`Unreadable` when a reading cannot be taken.
    """
    deadline = clock() + timeout_seconds
    last_description = ""
    seen_out = False
    while True:
        reading = read(pr_number, config)
        if reading.describe() != last_description:
            last_description = reading.describe()
            on_change(reading)
        if reading.merged:
            return reading
        if reading.queued:
            seen_out = False
        elif seen_out or reading.pr_state == "CLOSED":
            return reading
        else:
            seen_out = True
        remaining = deadline - clock()
        if remaining <= 0:
            return reading
        sleep(min(interval_seconds, remaining))


def _reading(pr: dict[str, Any]) -> Reading:
    queue = pr.get("mergeQueue") if isinstance(pr.get("mergeQueue"), dict) else {}
    configuration = queue.get("configuration") if isinstance(queue, dict) else None
    entry = pr.get("mergeQueueEntry") if isinstance(pr.get("mergeQueueEntry"), dict) else {}
    return Reading(
        has_queue=bool(pr.get("isMergeQueueEnabled")),
        merge_method=str((configuration or {}).get("mergeMethod") or ""),
        pr_state=str(pr.get("state") or ""),
        merged_at=str(pr.get("mergedAt") or ""),
        in_queue=bool(pr.get("isInMergeQueue")) or bool(entry),
        position=_int_or_none(entry.get("position")),
        entry_state=str(entry.get("state") or ""),
        eta_seconds=_int_or_none(entry.get("estimatedTimeToMerge")),
        waiting_to_enter=bool(pr.get("autoMergeRequest")),
    )


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
