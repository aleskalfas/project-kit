"""Tests for `pull_request_landing` — the one merge mechanic — and `pkit
pull-request`, its noun (#1011, #1200).

Covers the one GraphQL read (what it asks, how each answer reads, an API that
knows no merge queues against one that lacks only some other field, a failed
read), what the queue's last word on a PR says about its head, the
repository's squash-commit defaults, the merge requests (the direct squash
merge, the enqueue, the dequeue), the bounded wait for the queue's merge
(merged, left, closed, head moved, timed out — on a fixed deadline or the
queue's own estimate), and the noun's documents and exit codes — on a fake
`gh` and a fake clock.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable, Sequence
from typing import Any

import pytest
from click.testing import CliRunner

from project_kit import cli
from project_kit import pull_request_landing as landing

Completed = subprocess.CompletedProcess[str]


def _answer(pr: dict[str, Any] | None) -> str:
    """The GraphQL answer naming `pr` as the pull request."""
    return json.dumps({"data": {"repository": {"pullRequest": pr}}})


def _ok(argv: Sequence[str], stdout: str = "") -> Completed:
    return subprocess.CompletedProcess(list(argv), 0, stdout=stdout, stderr="")


def _gh(
    answers: list[dict[str, Any]], calls: list[list[str]] | None = None
) -> Callable[[Sequence[str]], Completed]:
    """A `gh` answering each read with the next pull request of `answers`, the
    last one repeated once they run out; any other command succeeds."""
    remaining = list(answers)

    def gh(argv: Sequence[str]) -> Completed:
        if calls is not None:
            calls.append(list(argv))
        if list(argv[:3]) != ["gh", "api", "graphql"] or "dequeuePullRequest" in _query(argv):
            return _ok(argv)
        pr = remaining.pop(0) if len(remaining) > 1 else remaining[0]
        return _ok(argv, _answer(pr))

    return gh


def _unknown(field: str, on_type: str = "PullRequest") -> Completed:
    error = f"Field '{field}' doesn't exist on type '{on_type}'"
    return subprocess.CompletedProcess(
        [], 1, stdout=json.dumps({"errors": [{"message": error}]}), stderr=f"gh: {error}"
    )


def _query(argv: Sequence[str]) -> str:
    return next((a for a in argv if a.startswith("query=")), "")


_QUEUED: dict[str, Any] = {
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


def test_the_read_asks_about_the_pr_in_the_working_directorys_repository() -> None:
    calls: list[list[str]] = []
    landing.read(496, gh=_gh([_QUEUED], calls))
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


def test_a_queued_pr_reads_its_position_state_time_to_merge_and_head() -> None:
    reading = landing.read(496, gh=_gh([_QUEUED]))
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
def test_each_answer_reads_as_one_phrase(pr: dict[str, Any], described: str) -> None:
    assert landing.read(496, gh=_gh([pr])).describe() == described


def test_a_base_without_a_queue_reads_as_none() -> None:
    reading = landing.read(496, gh=_gh([_NO_QUEUE]))
    assert not reading.has_queue
    assert reading.merge_method == ""
    assert not reading.ever_queued


def test_a_queue_that_does_not_squash_is_reported() -> None:
    pr = {**_QUEUED, "mergeQueue": {"configuration": {"mergeMethod": "MERGE"}}}
    reading = landing.read(496, gh=_gh([pr]))
    assert reading.has_queue and not reading.squashes
    assert reading.merge_method == "MERGE"


def test_an_api_without_merge_queues_answers_that_there_is_none() -> None:
    """An older GitHub Enterprise Server knows no `isMergeQueueEnabled`: asked
    for it alone, it still does not, so its bases have no queue, and the PR is
    read without the queue's fields — its state and head stay known."""
    calls: list[list[str]] = []

    def gh(argv: Sequence[str]) -> Completed:
        calls.append(list(argv))
        if "isMergeQueueEnabled" in _query(argv):
            return _unknown("isMergeQueueEnabled")
        pr = {"id": "PR_node", "state": "MERGED", "mergedAt": "t", "headRefOid": "sha-head"}
        return _ok(argv, _answer(pr))

    reading = landing.read(496, gh=gh)
    assert not reading.has_queue
    assert (reading.pr_state, reading.head_oid, reading.merged) == ("MERGED", "sha-head", True)
    assert len(calls) == 3
    probe = _query(calls[1])
    assert "isMergeQueueEnabled" in probe and "mergeQueueEntry" not in probe
    assert "headRefOid" not in probe


def test_a_host_with_queues_that_lacks_another_field_is_unreadable() -> None:
    """Only `isMergeQueueEnabled` itself unknown means "no queue": a host that
    knows it, but not some field the read also asks for, cannot say where the
    PR stands, so nothing merges on a guess."""

    def gh(argv: Sequence[str]) -> Completed:
        if "estimatedTimeToMerge" in _query(argv):
            return _unknown("estimatedTimeToMerge", "MergeQueueEntry")
        return _ok(argv, _answer({"isMergeQueueEnabled": True}))

    with pytest.raises(landing.Unreadable, match="estimatedTimeToMerge"):
        landing.read(496, gh=gh)


def test_a_probe_that_fails_another_way_is_unreadable() -> None:
    def gh(argv: Sequence[str]) -> Completed:
        if "mergeQueueEntry" in _query(argv):
            return _unknown("autoMergeRequest")
        return subprocess.CompletedProcess(list(argv), 1, stdout="", stderr="HTTP 502")

    with pytest.raises(landing.Unreadable, match="HTTP 502"):
        landing.read(496, gh=gh)


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
    returncode: int, stdout: str, stderr: str, reason: str
) -> None:
    def gh(argv: Sequence[str]) -> Completed:
        return subprocess.CompletedProcess(list(argv), returncode, stdout=stdout, stderr=stderr)

    with pytest.raises(landing.Unreadable, match=reason):
        landing.read(496, gh=gh)


def test_gh_missing_is_unreadable() -> None:
    def missing(argv: Sequence[str]) -> Completed:
        raise FileNotFoundError("gh")

    with pytest.raises(landing.Unreadable, match="not on PATH"):
        landing.read(496, gh=missing)


# --- the queue's last word on the PR ----------------------------------------


def test_a_pr_dropped_at_its_current_head_reads_as_a_dropped_head() -> None:
    reading = landing.read(496, gh=_gh([_dropped("sha-head")]))
    assert reading.dropped_head
    assert reading.removal == landing.Removal(
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
    pr: dict[str, Any], dropped: bool
) -> None:
    """New commits since the drop are a new head; a removal that names no head
    is taken as this one's; a PR queued, or added, since is not dropped."""
    assert landing.read(496, gh=_gh([pr])).dropped_head is dropped


# --- the repository's squash-commit defaults ----------------------------------


def test_the_squash_commit_defaults_are_read_from_the_repository() -> None:
    calls: list[list[str]] = []

    def gh(argv: Sequence[str]) -> Completed:
        calls.append(list(argv))
        answer = {"squash_merge_commit_title": "PR_TITLE", "squash_merge_commit_message": "PR_BODY"}
        return _ok(argv, json.dumps(answer))

    assert landing.squash_commit_defaults(gh=gh) == ("PR_TITLE", "PR_BODY")
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
    returncode: int, stdout: str, reason: str
) -> None:
    def gh(argv: Sequence[str]) -> Completed:
        return subprocess.CompletedProcess(list(argv), returncode, stdout=stdout, stderr="HTTP 404")

    with pytest.raises(landing.Unreadable, match=reason):
        landing.squash_commit_defaults(gh=gh)


# --- the merge requests --------------------------------------------------------


def test_the_squash_merge_takes_the_subject_and_pins_the_head_without_deleting() -> None:
    """The subject is passed always (GitHub's default for a single-commit PR is
    the commit message); the head pins the merge; `--delete-branch` never — it
    makes gh touch the local checkout and fail after the remote merge landed."""
    calls: list[list[str]] = []
    outcome = landing.squash_merge(
        42, subject="chore(release): v1.2.0", head_oid="a" * 40, gh=_gh([_NO_QUEUE], calls)
    )
    assert outcome == landing.Outcome(True, 0, "")
    assert calls == [
        [
            "gh",
            "pr",
            "merge",
            "42",
            "--squash",
            "--subject",
            "chore(release): v1.2.0",
            "--match-head-commit",
            "a" * 40,
        ]
    ]


def test_the_squash_merge_passes_admin_and_pins_nothing_without_a_head() -> None:
    calls: list[list[str]] = []
    landing.squash_merge(42, subject="fix: x", admin=True, gh=_gh([_NO_QUEUE], calls))
    assert calls == [["gh", "pr", "merge", "42", "--squash", "--subject", "fix: x", "--admin"]]


def test_the_enqueue_is_auto_pinned_to_the_checked_head_and_nothing_else() -> None:
    """No `--squash`, no `--subject`: GitHub ignores them for a queued merge.
    Never `--admin`, which merges around the queue."""
    calls: list[list[str]] = []
    assert landing.enqueue(42, head_oid="a" * 40, gh=_gh([_QUEUED], calls)).accepted
    assert calls == [["gh", "pr", "merge", "42", "--auto", "--match-head-commit", "a" * 40]]


@pytest.mark.parametrize(
    ("raised", "reason"),
    [(FileNotFoundError("gh"), "`gh` not on PATH"), (PermissionError(13, "denied"), "could not")],
    ids=["missing", "unrunnable"],
)
def test_a_request_gh_cannot_run_is_refused_with_why(raised: OSError, reason: str) -> None:
    def broken(argv: Sequence[str]) -> Completed:
        raise raised

    outcome = landing.enqueue(42, gh=broken)
    assert not outcome.accepted and outcome.exit_code is None
    assert reason in outcome.reason


def test_a_refused_request_carries_gh_s_reason() -> None:
    def refusing(argv: Sequence[str]) -> Completed:
        return subprocess.CompletedProcess(
            list(argv), 1, stdout="", stderr="Head sha didn't match\n"
        )

    assert landing.squash_merge(42, subject="x", gh=refusing) == landing.Outcome(
        False, 1, "Head sha didn't match"
    )


@pytest.mark.parametrize(
    ("before", "command"),
    [
        (_QUEUED, ["api", "graphql"]),
        ({**_OUT, "autoMergeRequest": {"enabledAt": "x"}}, ["pr", "merge", "42", "--disable-auto"]),
    ],
    ids=["in-the-queue", "waiting-to-enter"],
)
def test_the_dequeue_takes_the_pr_out_the_way_its_state_needs(
    before: dict[str, Any], command: list[str]
) -> None:
    """A PR in the queue leaves through GitHub's dequeue mutation (gh's
    `--disable-auto` answers "already queued" there and does nothing); one
    auto-merge still holds has the auto-merge cancelled. Out is confirmed by a
    reading."""
    calls: list[list[str]] = []
    outcome = landing.dequeue(42, gh=_gh([before, _OUT], calls))
    assert outcome.accepted
    taken = calls[1]
    assert taken[1 : 1 + len(command)] == command
    if command[0] == "api":
        assert "dequeuePullRequest" in taken[4] and taken[-1] == "id=PR_node"


def test_a_dequeue_that_does_not_take_says_so() -> None:
    outcome = landing.dequeue(42, gh=_gh([_QUEUED, _QUEUED]))
    assert not outcome.accepted
    assert "still position 2 in the queue" in outcome.reason


def test_a_pr_out_of_the_queue_needs_no_dequeue() -> None:
    calls: list[list[str]] = []
    assert landing.dequeue(42, gh=_gh([_OUT], calls)).accepted
    assert len(calls) == 1


def test_a_merged_pr_cannot_be_dequeued() -> None:
    outcome = landing.dequeue(42, gh=_gh([_MERGED]))
    assert not outcome.accepted and "has merged" in outcome.reason


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


def _wait(
    answers: list[dict[str, Any]], *, timeout: float | None = 300.0, head_oid: str = ""
) -> tuple[landing.Wait, list[str], _Clock]:
    clock = _Clock()
    seen: list[str] = []
    wait = landing.wait_for_merge(
        496,
        timeout_seconds=timeout,
        on_change=lambda r: seen.append(r.describe()),
        head_oid=head_oid,
        gh=_gh(answers),
        interval_seconds=15,
        sleep=clock.sleep,
        clock=clock,
    )
    return wait, seen, clock


def test_the_wait_ends_when_the_queue_merges_and_reports_each_change() -> None:
    second = {**_QUEUED, "mergeQueueEntry": {"position": 1, "state": "MERGEABLE"}}
    wait, seen, clock = _wait([_QUEUED, _QUEUED, second, _MERGED])
    assert wait.ended == landing.MERGED and wait.reading.merged
    assert seen == [
        "position 2 in the queue, awaiting checks, about 4 min to merge",
        "position 1 in the queue, mergeable",
        "merged at 2026-10-01T10:12:00Z",
    ]
    assert clock.sleeps == [15, 15, 15]


def test_the_wait_ends_with_the_pr_still_queued_when_the_time_runs_out() -> None:
    wait, seen, clock = _wait([_QUEUED], timeout=40)
    assert wait.ended == landing.STILL_QUEUED and wait.reading.queued
    assert clock.sleeps == [15, 15, 10]
    assert len(seen) == 1


def test_a_timeout_of_zero_reads_once() -> None:
    wait, seen, clock = _wait([_QUEUED, _MERGED], timeout=0)
    assert wait.ended == landing.STILL_QUEUED
    assert len(seen) == 1
    assert clock.sleeps == []


def test_a_pr_seen_out_of_the_queue_twice_running_has_left_it() -> None:
    """One reading out of the queue may be taken just as GitHub takes the PR
    in; two running are a PR the queue dropped."""
    wait, _, clock = _wait([_QUEUED, _OUT, _QUEUED, _OUT, _OUT])
    assert wait.ended == landing.LEFT
    assert not wait.reading.queued and not wait.reading.merged
    assert len(clock.sleeps) == 4


@pytest.mark.parametrize(
    ("answers", "ended"),
    [([_OUT, _QUEUED], "queued"), ([_OUT, _OUT], "left"), ([_OUT, _MERGED], "merged")],
    ids=["back-in", "out-again", "merged"],
)
def test_one_reading_out_at_the_deadline_is_followed_by_one_more(
    answers: list[dict[str, Any]], ended: str
) -> None:
    """The PR is never declared out of the queue on a single reading, not even
    when the time has run out: one more reading, after the interval, decides."""
    wait, _, clock = _wait(answers, timeout=0)
    assert wait.ended == ended
    assert clock.sleeps == [15]


def test_a_closed_pr_ends_the_wait_at_once() -> None:
    wait, _, clock = _wait([_QUEUED, {**_OUT, "state": "CLOSED"}])
    assert wait.ended == landing.LEFT and wait.reading.pr_state == "CLOSED"
    assert clock.sleeps == [15]


def test_a_head_that_moves_ends_the_wait_at_once() -> None:
    """Commits pushed after the caller checked the head must not merge: the wait
    hands the caller the moved head instead of waiting for the merge."""
    moved = {**_QUEUED, "headRefOid": "sha-pushed"}
    wait, _, clock = _wait([_QUEUED, moved, _MERGED], head_oid="sha-head")
    assert wait.ended == landing.HEAD_MOVED
    assert wait.reading.head_oid == "sha-pushed"
    assert clock.sleeps == [15]


def test_without_a_timeout_the_wait_follows_the_queues_estimate() -> None:
    """An estimate of 250 s waits that long plus the margin."""
    wait, _, clock = _wait([_QUEUED], timeout=None)
    assert wait.ended == landing.STILL_QUEUED
    assert sum(clock.sleeps) == 250 + landing.ETA_MARGIN_SECONDS


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
def test_the_estimated_wait_never_passes_the_cap(pr: dict[str, Any]) -> None:
    wait, _, clock = _wait([pr], timeout=None)
    assert wait.ended == landing.STILL_QUEUED
    assert sum(clock.sleeps) == landing.MAX_WAIT_SECONDS


def test_a_reading_that_fails_mid_wait_is_raised() -> None:
    def failing(argv: Sequence[str]) -> Completed:
        return subprocess.CompletedProcess(list(argv), 1, stdout="", stderr="HTTP 502")

    with pytest.raises(landing.Unreadable, match="HTTP 502"):
        landing.wait_for_merge(496, timeout_seconds=60, on_change=lambda r: None, gh=failing)


def test_the_wait_limit_reads_as_a_phrase() -> None:
    assert landing.wait_limit(None) == "as long as the queue estimates plus 2 min, at most 30 min"
    assert landing.wait_limit(1200) == "up to 20 min"


# --- `pkit pull-request` ---------------------------------------------------------


@pytest.fixture
def fake_gh(monkeypatch: pytest.MonkeyPatch) -> Callable[..., list[list[str]]]:
    """Install a fake `gh` as the noun's: `fake_gh(answers)` → the commands it runs."""

    def install(answers: list[dict[str, Any]]) -> list[list[str]]:
        calls: list[list[str]] = []
        monkeypatch.setattr(landing, "run_gh", _gh(answers, calls))
        clock = _Clock()
        monkeypatch.setattr(landing, "_sleep", clock.sleep)
        monkeypatch.setattr(landing, "_monotonic", clock)
        return calls

    return install


def _invoke(*args: str) -> Any:
    return CliRunner().invoke(cli.main, ["pull-request", *args])


def _lines(output: str) -> list[dict[str, Any]]:
    return [json.loads(line) for line in output.splitlines() if line.strip()]


def test_read_writes_the_reading_as_one_line_of_json(fake_gh: Any) -> None:
    fake_gh([_QUEUED])
    result = _invoke("read", "496", "--json")
    assert result.exit_code == 0
    [document] = _lines(result.stdout)
    assert document["schema_version"] == landing.SCHEMA_VERSION
    assert document["pull_request"] == 496 and document["unreadable"] is None
    reading = document["reading"]
    assert reading["queued"] is True and reading["merged"] is False
    assert reading["position"] == 2 and reading["head_oid"] == "sha-head"
    assert (
        reading["description"] == "position 2 in the queue, awaiting checks, about 4 min to merge"
    )


def test_read_says_where_the_pr_stands_and_how_the_base_merges(fake_gh: Any) -> None:
    fake_gh([_QUEUED])
    result = _invoke("read", "496")
    assert result.exit_code == 0
    assert result.stdout == (
        "PR #496: position 2 in the queue, awaiting checks, about 4 min to merge\n"
        "Base: merges through a queue, by squash\n"
    )


def test_a_read_github_cannot_answer_exits_1_with_why(monkeypatch: pytest.MonkeyPatch) -> None:
    def failing(argv: Sequence[str]) -> Completed:
        return subprocess.CompletedProcess(list(argv), 1, stdout="", stderr="HTTP 502")

    monkeypatch.setattr(landing, "run_gh", failing)
    result = _invoke("read", "496", "--json")
    assert result.exit_code == 1
    assert _lines(result.stdout)[0]["unreadable"] == "HTTP 502"


def test_squash_defaults_writes_the_title_and_message(monkeypatch: pytest.MonkeyPatch) -> None:
    answer = {"squash_merge_commit_title": "PR_TITLE", "squash_merge_commit_message": "PR_BODY"}
    monkeypatch.setattr(landing, "run_gh", lambda argv: _ok(argv, json.dumps(answer)))
    result = _invoke("squash-defaults", "--json")
    assert result.exit_code == 0
    assert _lines(result.stdout) == [
        {"schema_version": 1, "title": "PR_TITLE", "message": "PR_BODY", "unreadable": None}
    ]


def test_enqueue_and_merge_write_what_they_came_to(fake_gh: Any) -> None:
    calls = fake_gh([_QUEUED])
    result = _invoke("enqueue", "42", "--head", "sha", "--json")
    assert result.exit_code == 0
    assert _lines(result.stdout) == [
        {"schema_version": 1, "pull_request": 42, "accepted": True, "exit_code": 0, "reason": ""}
    ]
    result = _invoke("merge", "42", "--subject", "fix: x", "--head", "sha")
    assert result.exit_code == 0
    assert "gh accepted the squash merge of PR #42" in result.stdout
    assert calls[-1][-2:] == ["--match-head-commit", "sha"]


def test_a_refused_request_exits_1(monkeypatch: pytest.MonkeyPatch) -> None:
    def refusing(argv: Sequence[str]) -> Completed:
        return subprocess.CompletedProcess(list(argv), 1, stdout="", stderr="not mergeable")

    monkeypatch.setattr(landing, "run_gh", refusing)
    result = _invoke("merge", "42", "--subject", "fix: x", "--json")
    assert result.exit_code == 1
    assert _lines(result.stdout)[0]["reason"] == "not mergeable"


@pytest.mark.parametrize(
    ("answers", "args", "code", "ended"),
    [
        ([_QUEUED, _MERGED], [], 0, "merged"),
        ([_QUEUED], ["--seconds", "0"], 4, "queued"),
        ([_QUEUED, _OUT, _OUT], [], 3, "left"),
        (
            [_QUEUED, {**_QUEUED, "headRefOid": "sha-pushed"}],
            ["--head", "sha-head"],
            3,
            "head-moved",
        ),
    ],
    ids=["merged", "still-queued", "left", "head-moved"],
)
def test_wait_streams_each_change_and_exits_by_how_it_ended(
    fake_gh: Any, answers: list[dict[str, Any]], args: list[str], code: int, ended: str
) -> None:
    fake_gh(answers)
    result = _invoke("wait", "496", *args, "--json")
    assert result.exit_code == code
    lines = _lines(result.stdout)
    assert [line["event"] for line in lines[:-1]] == ["reading"] * (len(lines) - 1)
    assert lines[0]["reading"]["position"] == 2
    assert lines[-1]["event"] == "end" and lines[-1]["ended"] == ended


def test_a_wait_github_cannot_answer_ends_unreadable(monkeypatch: pytest.MonkeyPatch) -> None:
    def failing(argv: Sequence[str]) -> Completed:
        return subprocess.CompletedProcess(list(argv), 1, stdout="", stderr="HTTP 502")

    monkeypatch.setattr(landing, "run_gh", failing)
    result = _invoke("wait", "496", "--json")
    assert result.exit_code == 1
    [end] = _lines(result.stdout)
    assert (end["event"], end["ended"], end["unreadable"]) == ("end", None, "HTTP 502")


def test_dequeue_writes_whether_the_pr_is_out(fake_gh: Any) -> None:
    fake_gh([_QUEUED, _OUT])
    result = _invoke("dequeue", "42")
    assert result.exit_code == 0
    assert "PR #42 is out of the merge queue" in result.stdout
