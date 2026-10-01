"""Tests for `_lib/merge_queue.py` — where a PR stands with its base branch's
merge queue (#1011).

Covers the one GraphQL read (what it asks, how each answer reads, an API that
knows no merge queues against one that lacks only some other field, a failed
read), what the queue's last word on a PR says about its head, the
repository's squash-commit defaults, and the bounded wait for the queue's
merge (merged, left, closed, head moved, timed out — on a fixed deadline or
the queue's own estimate), on a fake `gh_run` and a fake clock.
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


def _unknown(field: str, on_type: str = "PullRequest") -> subprocess.CompletedProcess[str]:
    error = f"Field '{field}' doesn't exist on type '{on_type}'"
    return subprocess.CompletedProcess(
        [], 1, stdout=json.dumps({"errors": [{"message": error}]}), stderr=f"gh: {error}"
    )


def _query(args: list[str]) -> str:
    return next(a for a in args if a.startswith("query="))


_QUEUED = {
    "id": "PR_node",
    "state": "OPEN",
    "mergedAt": None,
    "headRefOid": "sha-head",
    "isMergeQueueEnabled": True,
    "isInMergeQueue": True,
    "mergeQueue": {"configuration": {"mergeMethod": "SQUASH"}},
    "mergeQueueEntry": {"position": 2, "state": "AWAITING_CHECKS", "estimatedTimeToMerge": 250},
    "autoMergeRequest": {"enabledAt": "2026-10-01T10:00:00Z"},
    "timelineItems": {"nodes": [{"__typename": "AddedToMergeQueueEvent"}]},
}
_OUT = {**_QUEUED, "isInMergeQueue": False, "mergeQueueEntry": None, "autoMergeRequest": None}
_MERGED = {**_OUT, "state": "MERGED", "mergedAt": "2026-10-01T10:12:00Z"}
_NO_QUEUE = {**_OUT, "isMergeQueueEnabled": False, "mergeQueue": None, "timelineItems": None}


def _dropped(at_head: str | None, reason: str | None = "failed checks") -> dict[str, Any]:
    removal: dict[str, Any] = {
        "__typename": "RemovedFromMergeQueueEvent",
        "createdAt": "2026-10-01T10:05:00Z",
        "reason": reason,
        "beforeCommit": {"oid": at_head} if at_head is not None else None,
    }
    return {
        **_OUT,
        "timelineItems": {"nodes": [{"__typename": "AddedToMergeQueueEvent"}, removal]},
    }


# --- read -----------------------------------------------------------------


def test_the_read_asks_about_the_pr_in_the_working_directorys_repository(mq, monkeypatch) -> None:
    calls: list[list[str]] = []
    _gh(monkeypatch, mq, [_QUEUED], calls)
    mq.read(496, {})
    argv = calls[0]
    assert argv[:3] == ["gh", "api", "graphql"]
    assert {"owner={owner}", "repo={repo}", "number=496"} <= set(argv)
    query = _query(argv)
    for field in (
        "headRefOid",
        "isMergeQueueEnabled",
        "mergeQueueEntry",
        "mergeMethod",
        "autoMergeRequest",
        "REMOVED_FROM_MERGE_QUEUE_EVENT",
        "beforeCommit",
    ):
        assert field in query


def test_a_queued_pr_reads_its_position_state_time_to_merge_and_head(mq, monkeypatch) -> None:
    _gh(monkeypatch, mq, [_QUEUED])
    reading = mq.read(496, {})
    assert reading.has_queue and reading.squashes and reading.queued
    assert (reading.position, reading.entry_state, reading.eta_seconds) == (
        2,
        "AWAITING_CHECKS",
        250,
    )
    assert (reading.pr_id, reading.head_oid) == ("PR_node", "sha-head")
    assert reading.ever_queued and reading.removal is None
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
    assert not reading.ever_queued


def test_a_queue_that_does_not_squash_is_reported(mq, monkeypatch) -> None:
    _gh(monkeypatch, mq, [{**_QUEUED, "mergeQueue": {"configuration": {"mergeMethod": "MERGE"}}}])
    reading = mq.read(496, {})
    assert reading.has_queue and not reading.squashes
    assert reading.merge_method == "MERGE"


def test_an_api_without_merge_queues_answers_that_there_is_none(mq, monkeypatch) -> None:
    """An older GitHub Enterprise Server knows no `isMergeQueueEnabled`: asked
    for it alone, it still does not, so its bases have no queue, and the PR is
    read without the queue's fields — its state and head stay known."""
    calls: list[list[str]] = []

    def fake_gh_run(args, config, **kwargs):
        calls.append(list(args))
        query = _query(args)
        if "isMergeQueueEnabled" in query:
            return _unknown("isMergeQueueEnabled")
        pr = {"id": "PR_node", "state": "MERGED", "mergedAt": "t", "headRefOid": "sha-head"}
        return subprocess.CompletedProcess(args, 0, stdout=_answer(pr), stderr="")

    monkeypatch.setattr(mq, "gh_run", fake_gh_run)
    reading = mq.read(496, {})
    assert not reading.has_queue
    assert (reading.pr_state, reading.head_oid, reading.merged) == ("MERGED", "sha-head", True)
    assert len(calls) == 3
    probe = _query(calls[1])
    assert "isMergeQueueEnabled" in probe and "mergeQueueEntry" not in probe
    assert "headRefOid" not in probe


def test_a_host_with_queues_that_lacks_another_field_is_unreadable(mq, monkeypatch) -> None:
    """Only `isMergeQueueEnabled` itself unknown means "no queue": a host that
    knows it, but not some field the read also asks for, cannot say where the
    PR stands, so nothing merges on a guess."""

    def fake_gh_run(args, config, **kwargs):
        query = _query(args)
        if "estimatedTimeToMerge" in query:
            return _unknown("estimatedTimeToMerge", "MergeQueueEntry")
        return subprocess.CompletedProcess(
            args, 0, stdout=_answer({"isMergeQueueEnabled": True}), stderr=""
        )

    monkeypatch.setattr(mq, "gh_run", fake_gh_run)
    with pytest.raises(mq.Unreadable, match="estimatedTimeToMerge"):
        mq.read(496, {})


def test_a_probe_that_fails_another_way_is_unreadable(mq, monkeypatch) -> None:
    def fake_gh_run(args, config, **kwargs):
        if "mergeQueueEntry" in _query(args):
            return _unknown("autoMergeRequest")
        return subprocess.CompletedProcess(args, 1, stdout="", stderr="HTTP 502")

    monkeypatch.setattr(mq, "gh_run", fake_gh_run)
    with pytest.raises(mq.Unreadable, match="HTTP 502"):
        mq.read(496, {})


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


# --- the queue's last word on the PR ----------------------------------------


def test_a_pr_dropped_at_its_current_head_reads_as_a_dropped_head(mq, monkeypatch) -> None:
    _gh(monkeypatch, mq, [_dropped("sha-head")])
    reading = mq.read(496, {})
    assert reading.dropped_head
    assert reading.removal == mq.Removal(
        at="2026-10-01T10:05:00Z", reason="failed checks", head_oid="sha-head"
    )


@pytest.mark.parametrize(
    ("pr", "dropped"),
    [
        (_dropped("sha-older"), False),
        (_dropped(None, reason=None), True),
        ({**_dropped("sha-head"), "autoMergeRequest": {"enabledAt": "x"}}, False),
        (
            {
                **_OUT,
                "timelineItems": {
                    "nodes": [
                        *_dropped("sha-head")["timelineItems"]["nodes"],
                        {"__typename": "AddedToMergeQueueEvent"},
                    ]
                },
            },
            False,
        ),
    ],
    ids=["an-older-head", "no-head-named", "queued-again", "added-since"],
)
def test_only_the_queues_last_word_at_this_head_is_a_dropped_head(
    mq, monkeypatch, pr, dropped
) -> None:
    """New commits since the drop are a new head; a removal that names no head
    is taken as this one's; a PR queued, or added, since is not dropped."""
    _gh(monkeypatch, mq, [pr])
    assert mq.read(496, {}).dropped_head is dropped


# --- the repository's squash-commit defaults ----------------------------------


def test_the_squash_commit_defaults_are_read_from_the_repository(mq, monkeypatch) -> None:
    calls: list[list[str]] = []

    def fake_gh_run(args, config, **kwargs):
        calls.append(list(args))
        answer = {"squash_merge_commit_title": "PR_TITLE", "squash_merge_commit_message": "PR_BODY"}
        return subprocess.CompletedProcess(args, 0, stdout=json.dumps(answer), stderr="")

    monkeypatch.setattr(mq, "gh_run", fake_gh_run)
    assert mq.squash_commit_defaults({}) == ("PR_TITLE", "PR_BODY")
    assert calls == [["gh", "api", "repos/{owner}/{repo}"]]


@pytest.mark.parametrize(
    ("returncode", "stdout", "reason"),
    [
        (1, "", "HTTP 404"),
        (0, json.dumps({"name": "project-kit"}), "squash-commit defaults are not in the answer"),
        (0, "not json", "names no repository"),
    ],
    ids=["gh-failed", "not-in-the-answer", "not-json"],
)
def test_squash_commit_defaults_that_cannot_be_read_are_unreadable(
    mq, monkeypatch, returncode, stdout, reason
) -> None:
    def fake_gh_run(args, config, **kwargs):
        return subprocess.CompletedProcess(args, returncode, stdout=stdout, stderr="HTTP 404")

    monkeypatch.setattr(mq, "gh_run", fake_gh_run)
    with pytest.raises(mq.Unreadable, match=reason):
        mq.squash_commit_defaults({})


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


def _wait(mq, monkeypatch, answers, *, timeout: float | None = 300.0, head_oid: str = ""):
    _gh(monkeypatch, mq, answers)
    clock = _Clock()
    seen: list[str] = []
    wait = mq.wait_for_merge(
        496,
        {},
        timeout_seconds=timeout,
        on_change=lambda r: seen.append(r.describe()),
        head_oid=head_oid,
        interval_seconds=15,
        sleep=clock.sleep,
        clock=clock,
    )
    return wait, seen, clock


def test_the_wait_ends_when_the_queue_merges_and_reports_each_change(mq, monkeypatch) -> None:
    second = {**_QUEUED, "mergeQueueEntry": {"position": 1, "state": "MERGEABLE"}}
    wait, seen, clock = _wait(mq, monkeypatch, [_QUEUED, _QUEUED, second, _MERGED])
    assert wait.ended == mq.MERGED and wait.reading.merged
    assert seen == [
        "position 2 in the queue, awaiting checks, about 4 min to merge",
        "position 1 in the queue, mergeable",
        "merged at 2026-10-01T10:12:00Z",
    ]
    assert clock.sleeps == [15, 15, 15]


def test_the_wait_ends_with_the_pr_still_queued_when_the_time_runs_out(mq, monkeypatch) -> None:
    wait, seen, clock = _wait(mq, monkeypatch, [_QUEUED], timeout=40)
    assert wait.ended == mq.STILL_QUEUED and wait.reading.queued
    assert clock.sleeps == [15, 15, 10]
    assert len(seen) == 1


def test_a_timeout_of_zero_reads_once(mq, monkeypatch) -> None:
    wait, seen, clock = _wait(mq, monkeypatch, [_QUEUED, _MERGED], timeout=0)
    assert wait.ended == mq.STILL_QUEUED
    assert len(seen) == 1
    assert clock.sleeps == []


def test_a_pr_seen_out_of_the_queue_twice_running_has_left_it(mq, monkeypatch) -> None:
    """One reading out of the queue may be taken just as GitHub takes the PR
    in; two running are a PR the queue dropped."""
    wait, _, clock = _wait(mq, monkeypatch, [_QUEUED, _OUT, _QUEUED, _OUT, _OUT])
    assert wait.ended == mq.LEFT
    assert not wait.reading.queued and not wait.reading.merged
    assert len(clock.sleeps) == 4


@pytest.mark.parametrize(
    ("answers", "ended"),
    [([_OUT, _QUEUED], "queued"), ([_OUT, _OUT], "left"), ([_OUT, _MERGED], "merged")],
    ids=["back-in", "out-again", "merged"],
)
def test_one_reading_out_at_the_deadline_is_followed_by_one_more(
    mq, monkeypatch, answers, ended
) -> None:
    """The PR is never declared out of the queue on a single reading, not even
    when the time has run out: one more reading, after the interval, decides."""
    wait, _, clock = _wait(mq, monkeypatch, answers, timeout=0)
    assert wait.ended == ended
    assert clock.sleeps == [15]


def test_a_closed_pr_ends_the_wait_at_once(mq, monkeypatch) -> None:
    wait, _, clock = _wait(mq, monkeypatch, [_QUEUED, {**_OUT, "state": "CLOSED"}])
    assert wait.ended == mq.LEFT and wait.reading.pr_state == "CLOSED"
    assert clock.sleeps == [15]


def test_a_head_that_moves_ends_the_wait_at_once(mq, monkeypatch) -> None:
    """Commits pushed after the gates checked the head must not merge: the wait
    hands the caller the moved head instead of waiting for the merge."""
    moved = {**_QUEUED, "headRefOid": "sha-pushed"}
    wait, _, clock = _wait(mq, monkeypatch, [_QUEUED, moved, _MERGED], head_oid="sha-head")
    assert wait.ended == mq.HEAD_MOVED
    assert wait.reading.head_oid == "sha-pushed"
    assert clock.sleeps == [15]


def test_without_a_timeout_the_wait_follows_the_queues_estimate(mq, monkeypatch) -> None:
    """An estimate of 250 s waits that long plus the margin."""
    wait, _, clock = _wait(mq, monkeypatch, [_QUEUED], timeout=None)
    assert wait.ended == mq.STILL_QUEUED
    assert sum(clock.sleeps) == 250 + mq.ETA_MARGIN_SECONDS


@pytest.mark.parametrize(
    "pr",
    [
        {**_OUT, "autoMergeRequest": {"enabledAt": "x"}},
        {
            **_QUEUED,
            "mergeQueueEntry": {**_QUEUED["mergeQueueEntry"], "estimatedTimeToMerge": 4000},
        },
    ],
    ids=["no-estimate", "estimate-past-the-cap"],
)
def test_the_estimated_wait_never_passes_the_cap(mq, monkeypatch, pr) -> None:
    wait, _, clock = _wait(mq, monkeypatch, [pr], timeout=None)
    assert wait.ended == mq.STILL_QUEUED
    assert sum(clock.sleeps) == mq.MAX_WAIT_SECONDS


def test_a_reading_that_fails_mid_wait_is_raised(mq, monkeypatch) -> None:
    def failing(args, config, **kwargs):
        return subprocess.CompletedProcess(args, 1, stdout="", stderr="HTTP 502")

    monkeypatch.setattr(mq, "gh_run", failing)
    with pytest.raises(mq.Unreadable, match="HTTP 502"):
        mq.wait_for_merge(496, {}, timeout_seconds=60, on_change=lambda r: None)
