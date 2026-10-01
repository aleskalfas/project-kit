"""Tests for `_lib/merge_queue.py` — where a PR stands with its base branch's
merge queue (#1011).

Covers the one GraphQL read (what it asks, how each answer reads, an API that
knows no merge queues, a failed read) and the bounded wait for the queue's
merge (merged, left the queue, closed, timed out), on a fake `gh_run` and a
fake clock.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"


@pytest.fixture(scope="module")
def mq():
    sys.path.insert(0, str(SCRIPTS_DIR))
    from _lib import merge_queue

    return merge_queue


def _answer(pr: dict[str, Any] | None) -> str:
    """The GraphQL answer naming `pr` as the pull request."""
    return json.dumps({"data": {"repository": {"pullRequest": pr}}})


def _gh(monkeypatch, mq, answers: list[dict[str, Any]], calls: list[list[str]] | None = None):
    """`gh_run` answering each read with the next pull request of `answers`,
    the last one repeated once they run out."""
    remaining = list(answers)

    def fake_gh_run(args, config, **kwargs):
        if calls is not None:
            calls.append(list(args))
        pr = remaining.pop(0) if len(remaining) > 1 else remaining[0]
        return subprocess.CompletedProcess(args, 0, stdout=_answer(pr), stderr="")

    monkeypatch.setattr(mq, "gh_run", fake_gh_run)


_QUEUED = {
    "state": "OPEN",
    "mergedAt": None,
    "isMergeQueueEnabled": True,
    "isInMergeQueue": True,
    "mergeQueue": {"configuration": {"mergeMethod": "SQUASH"}},
    "mergeQueueEntry": {"position": 2, "state": "AWAITING_CHECKS", "estimatedTimeToMerge": 250},
    "autoMergeRequest": {"enabledAt": "2026-10-01T10:00:00Z"},
}
_OUT = {**_QUEUED, "isInMergeQueue": False, "mergeQueueEntry": None, "autoMergeRequest": None}
_MERGED = {**_OUT, "state": "MERGED", "mergedAt": "2026-10-01T10:12:00Z"}
_NO_QUEUE = {**_OUT, "isMergeQueueEnabled": False, "mergeQueue": None}


# --- read -----------------------------------------------------------------


def test_the_read_asks_about_the_pr_in_the_working_directorys_repository(mq, monkeypatch) -> None:
    calls: list[list[str]] = []
    _gh(monkeypatch, mq, [_QUEUED], calls)
    mq.read(496, {})
    argv = calls[0]
    assert argv[:3] == ["gh", "api", "graphql"]
    assert {"owner={owner}", "repo={repo}", "number=496"} <= set(argv)
    query = next(a for a in argv if a.startswith("query="))
    for field in ("isMergeQueueEnabled", "mergeQueueEntry", "mergeMethod", "autoMergeRequest"):
        assert field in query


def test_a_queued_pr_reads_its_position_state_and_time_to_merge(mq, monkeypatch) -> None:
    _gh(monkeypatch, mq, [_QUEUED])
    reading = mq.read(496, {})
    assert reading.has_queue and reading.squashes and reading.queued
    assert (reading.position, reading.entry_state, reading.eta_seconds) == (
        2,
        "AWAITING_CHECKS",
        250,
    )
    assert not reading.merged
    assert reading.describe() == "position 2 in the queue, awaiting checks, about 4 min to merge"


@pytest.mark.parametrize(
    ("pr", "described"),
    [
        (_MERGED, "merged at 2026-10-01T10:12:00Z"),
        (_OUT, "not in the queue"),
        ({**_OUT, "state": "CLOSED"}, "closed without merging"),
        (
            {**_OUT, "autoMergeRequest": {"enabledAt": "x"}},
            "waiting for its required checks before it enters the queue",
        ),
        (
            {**_QUEUED, "mergeQueueEntry": {"position": 1, "state": "MERGEABLE"}},
            "position 1 in the queue, mergeable",
        ),
        (
            {
                **_QUEUED,
                "mergeQueueEntry": {**_QUEUED["mergeQueueEntry"], "estimatedTimeToMerge": 20},
            },
            "position 2 in the queue, awaiting checks, under a minute to merge",
        ),
    ],
    ids=["merged", "out", "closed", "waiting-to-enter", "no-eta", "under-a-minute"],
)
def test_each_answer_reads_as_one_phrase(mq, monkeypatch, pr, described) -> None:
    _gh(monkeypatch, mq, [pr])
    assert mq.read(496, {}).describe() == described


def test_a_base_without_a_queue_reads_as_none(mq, monkeypatch) -> None:
    _gh(monkeypatch, mq, [_NO_QUEUE])
    reading = mq.read(496, {})
    assert not reading.has_queue
    assert reading.merge_method == ""


def test_a_queue_that_does_not_squash_is_reported(mq, monkeypatch) -> None:
    _gh(monkeypatch, mq, [{**_QUEUED, "mergeQueue": {"configuration": {"mergeMethod": "MERGE"}}}])
    reading = mq.read(496, {})
    assert reading.has_queue and not reading.squashes
    assert reading.merge_method == "MERGE"


def test_an_api_without_merge_queues_answers_that_there_is_none(mq, monkeypatch) -> None:
    """An older GitHub Enterprise Server knows no merge-queue field: its bases
    have no queue, so done-work merges there as it always has."""
    error = "Field 'isMergeQueueEnabled' doesn't exist on type 'PullRequest'"

    def fake_gh_run(args, config, **kwargs):
        return subprocess.CompletedProcess(
            args, 1, stdout=json.dumps({"errors": [{"message": error}]}), stderr=f"gh: {error}"
        )

    monkeypatch.setattr(mq, "gh_run", fake_gh_run)
    assert mq.read(496, {}) == mq.Reading(has_queue=False)


@pytest.mark.parametrize(
    ("returncode", "stdout", "stderr", "reason"),
    [
        (1, "", "HTTP 502: Bad Gateway", "HTTP 502: Bad Gateway"),
        (0, json.dumps({"errors": [{"message": "rate limited"}]}), "", "rate limited"),
        (0, _answer(None), "", "no pull request #496"),
        (0, "not json", "", "no pull request #496"),
    ],
    ids=["gh-failed", "graphql-error", "no-pull-request", "not-json"],
)
def test_a_failed_read_is_unreadable_with_its_reason(
    mq, monkeypatch, returncode, stdout, stderr, reason
) -> None:
    def fake_gh_run(args, config, **kwargs):
        return subprocess.CompletedProcess(args, returncode, stdout=stdout, stderr=stderr)

    monkeypatch.setattr(mq, "gh_run", fake_gh_run)
    with pytest.raises(mq.Unreadable, match=reason):
        mq.read(496, {})


def test_gh_missing_is_unreadable(mq, monkeypatch) -> None:
    def missing(args, config, **kwargs):
        raise FileNotFoundError("gh")

    monkeypatch.setattr(mq, "gh_run", missing)
    with pytest.raises(mq.Unreadable, match="not on PATH"):
        mq.read(496, {})


# --- wait_for_merge ---------------------------------------------------------


class _Clock:
    """A clock the wait's sleeps advance, so no test sleeps."""

    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


def _wait(mq, monkeypatch, answers, *, timeout: float = 300.0):
    _gh(monkeypatch, mq, answers)
    clock = _Clock()
    seen: list[str] = []
    reading = mq.wait_for_merge(
        496,
        {},
        timeout_seconds=timeout,
        on_change=lambda r: seen.append(r.describe()),
        interval_seconds=15,
        sleep=clock.sleep,
        clock=clock,
    )
    return reading, seen, clock


def test_the_wait_ends_when_the_queue_merges_and_reports_each_change(mq, monkeypatch) -> None:
    second = {**_QUEUED, "mergeQueueEntry": {"position": 1, "state": "MERGEABLE"}}
    reading, seen, clock = _wait(mq, monkeypatch, [_QUEUED, _QUEUED, second, _MERGED])
    assert reading.merged
    assert seen == [
        "position 2 in the queue, awaiting checks, about 4 min to merge",
        "position 1 in the queue, mergeable",
        "merged at 2026-10-01T10:12:00Z",
    ]
    assert clock.sleeps == [15, 15, 15]


def test_the_wait_ends_with_the_pr_still_queued_when_the_time_runs_out(mq, monkeypatch) -> None:
    reading, seen, clock = _wait(mq, monkeypatch, [_QUEUED], timeout=40)
    assert reading.queued and not reading.merged
    assert clock.sleeps == [15, 15, 10]
    assert len(seen) == 1


def test_a_timeout_of_zero_reads_once(mq, monkeypatch) -> None:
    reading, seen, clock = _wait(mq, monkeypatch, [_QUEUED, _MERGED], timeout=0)
    assert reading.queued
    assert len(seen) == 1
    assert clock.sleeps == []


def test_a_pr_seen_out_of_the_queue_twice_running_has_left_it(mq, monkeypatch) -> None:
    """One reading out of the queue may be taken just as GitHub takes the PR
    in; two running are a PR the queue dropped."""
    reading, _, clock = _wait(mq, monkeypatch, [_QUEUED, _OUT, _QUEUED, _OUT, _OUT])
    assert not reading.queued and not reading.merged
    assert len(clock.sleeps) == 4


def test_a_closed_pr_ends_the_wait_at_once(mq, monkeypatch) -> None:
    reading, _, clock = _wait(mq, monkeypatch, [_QUEUED, {**_OUT, "state": "CLOSED"}])
    assert reading.pr_state == "CLOSED"
    assert clock.sleeps == [15]


def test_a_reading_that_fails_mid_wait_is_raised(mq, monkeypatch) -> None:
    def failing(args, config, **kwargs):
        return subprocess.CompletedProcess(args, 1, stdout="", stderr="HTTP 502")

    monkeypatch.setattr(mq, "gh_run", failing)
    with pytest.raises(mq.Unreadable, match="HTTP 502"):
        mq.wait_for_merge(496, {}, timeout_seconds=60, on_change=lambda r: None)
