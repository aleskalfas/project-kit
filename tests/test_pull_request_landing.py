"""Tests for `pull_request_landing` — the one merge mechanic — and `pkit
pull-request`, its noun (#1011, #1200).

Covers the one GraphQL read (what it asks, how each answer reads, an API that
knows no merge queues against one that lacks only some other field, a failed
read), what the queue's last word on a PR says about its head, the
repository's squash-commit defaults, the merge requests (the direct squash
merge, the enqueue, the dequeue) and one that gets no answer, settled by
reading — made, not made on two readings running, or unconfirmed — while one
the service refused stays a refusal (#1256), every `gh` call bounded by its
kind, the bounded wait for the queue's merge
(merged, left, closed, head moved, timed out — on a fixed deadline or the
queue's own estimate), and the noun's documents and exit codes — on a fake
`gh` and a fake clock.
"""

from __future__ import annotations

import inspect
import json
import subprocess
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from project_kit import cli, command_runner, session_guard
from project_kit import pull_request_landing as landing
from tests import hosting_fake as fake
from tests import sessions

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


@pytest.fixture
def here(tmp_path: Path) -> dict[str, Any]:
    """Where a request that changes the service is made, and the
    cross-repository guard's clearance for it — outside any session, so it
    passes undetermined — as the request's `cwd` and `clearance`."""
    cleared = session_guard.clear(tmp_path, confirmed=False, interactive=False)
    assert isinstance(cleared, session_guard.Clearance)
    return {"cwd": tmp_path, "clearance": cleared}


@pytest.fixture
def acting(monkeypatch: pytest.MonkeyPatch) -> Callable[[landing.GhRunner], None]:
    """`acting(gh)` makes `gh` the client a request runs where its clearance
    covers — the module's own seam (`landing.gh_runner`), since a request
    takes no client from its caller."""

    def install(gh: landing.GhRunner) -> None:
        monkeypatch.setattr(landing, "gh_runner", lambda cwd: gh)

    return install


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


@pytest.mark.parametrize("fork", [False, True], ids=["same-repository", "fork"])
def test_the_reading_names_the_head_branch_and_whether_it_is_in_a_fork(fork: bool) -> None:
    """Two facts the reading states for a caller (#1255): the head's ref name,
    and whether the head is in another repository."""
    calls: list[list[str]] = []
    pr = {**_QUEUED, "headRefName": "fix/42-x", "isCrossRepository": fork}
    reading = landing.read(496, gh=_gh([pr], calls))
    assert "headRefName" in _query(calls[0]) and "isCrossRepository" in _query(calls[0])
    assert (reading.head_ref, reading.cross_repository) == ("fix/42-x", fork)
    document = reading.as_json()
    assert (document["head_ref"], document["cross_repository"]) == ("fix/42-x", fork)


def test_a_reading_that_does_not_say_where_the_head_is_reads_as_a_forks() -> None:
    """Nothing is done on a branch that may not be the PR's: an answer without
    `isCrossRepository` reads as a head in another repository."""
    reading = landing.read(496, gh=_gh([_QUEUED]))
    assert reading.cross_repository is True


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


def test_the_squash_merge_takes_the_subject_and_pins_the_head_without_deleting(
    here: dict[str, Any], acting: Callable[[landing.GhRunner], None]
) -> None:
    """The subject is passed always (GitHub's default for a single-commit PR is
    the commit message); the head pins the merge; `--delete-branch` never — it
    makes gh touch the local checkout and fail after the remote merge landed."""
    calls: list[list[str]] = []
    acting(_gh([_NO_QUEUE], calls))
    outcome = landing.squash_merge(42, subject="chore(release): v1.2.0", head_oid="a" * 40, **here)
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


def test_the_squash_merge_passes_admin_and_pins_nothing_without_a_head(
    here: dict[str, Any], acting: Callable[[landing.GhRunner], None]
) -> None:
    calls: list[list[str]] = []
    acting(_gh([_NO_QUEUE], calls))
    landing.squash_merge(42, subject="fix: x", admin=True, **here)
    assert calls == [["gh", "pr", "merge", "42", "--squash", "--subject", "fix: x", "--admin"]]


def test_the_enqueue_is_auto_pinned_to_the_checked_head_and_nothing_else(
    here: dict[str, Any], acting: Callable[[landing.GhRunner], None]
) -> None:
    """No `--squash`, no `--subject`: GitHub ignores them for a queued merge.
    Never `--admin`, which merges around the queue."""
    calls: list[list[str]] = []
    acting(_gh([_QUEUED], calls))
    assert landing.enqueue(42, head_oid="a" * 40, **here).accepted
    assert calls == [["gh", "pr", "merge", "42", "--auto", "--match-head-commit", "a" * 40]]


@pytest.mark.parametrize(
    ("raised", "reason"),
    [(FileNotFoundError("gh"), "`gh` not on PATH"), (PermissionError(13, "denied"), "could not")],
    ids=["missing", "unrunnable"],
)
def test_a_request_gh_cannot_run_is_refused_with_why(
    raised: OSError, reason: str, here: dict[str, Any], acting: Callable[[landing.GhRunner], None]
) -> None:
    def broken(argv: Sequence[str]) -> Completed:
        raise raised

    acting(broken)
    outcome = landing.enqueue(42, **here)
    assert not outcome.accepted and outcome.exit_code is None
    assert reason in outcome.reason


def test_a_refused_request_carries_gh_s_reason(
    here: dict[str, Any], acting: Callable[[landing.GhRunner], None]
) -> None:
    def refusing(argv: Sequence[str]) -> Completed:
        return subprocess.CompletedProcess(
            list(argv), 1, stdout="", stderr="Head sha didn't match\n"
        )

    acting(refusing)
    assert landing.squash_merge(42, subject="x", **here) == landing.Outcome(
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
    before: dict[str, Any],
    command: list[str],
    here: dict[str, Any],
    acting: Callable[[landing.GhRunner], None],
) -> None:
    """A PR in the queue leaves through GitHub's dequeue mutation (gh's
    `--disable-auto` answers "already queued" there and does nothing); one
    auto-merge still holds has the auto-merge cancelled. Out is confirmed by a
    reading."""
    calls: list[list[str]] = []
    acting(_gh([before, _OUT], calls))
    outcome = landing.dequeue(42, **here)
    assert outcome.accepted
    taken = calls[1]
    assert taken[1 : 1 + len(command)] == command
    if command[0] == "api":
        assert "dequeuePullRequest" in taken[4] and taken[-1] == "id=PR_node"


def test_a_dequeue_that_does_not_take_says_so(
    here: dict[str, Any], acting: Callable[[landing.GhRunner], None]
) -> None:
    acting(_gh([_QUEUED, _QUEUED]))
    outcome = landing.dequeue(42, **here)
    assert not outcome.accepted
    assert "still position 2 in the queue" in outcome.reason


def test_a_pr_out_of_the_queue_needs_no_dequeue(
    here: dict[str, Any], acting: Callable[[landing.GhRunner], None]
) -> None:
    calls: list[list[str]] = []
    acting(_gh([_OUT], calls))
    assert landing.dequeue(42, **here).accepted
    assert len(calls) == 1


def test_a_merged_pr_cannot_be_dequeued(
    here: dict[str, Any], acting: Callable[[landing.GhRunner], None]
) -> None:
    acting(_gh([_MERGED]))
    outcome = landing.dequeue(42, **here)
    assert not outcome.accepted and "has merged" in outcome.reason


# --- a request with no answer (#1256) ------------------------------------------------


def _bounded(host: fake.HostingService) -> landing.GhRunner:
    """`host` as the module's own `gh` reaches it, through the bounded start: a
    request it never answers is ended at its bound."""

    def run(argv: Sequence[str]) -> Completed:
        try:
            return host(argv)
        except fake.NoAnswer:
            raise subprocess.TimeoutExpired(list(argv), landing.GH_REQUEST_SECONDS) from None

    return run


@pytest.fixture
def slept(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    """The module's sleeps, recorded and never slept."""
    sleeps: list[float] = []
    monkeypatch.setattr(landing, "_sleep", sleeps.append)
    return sleeps


def _queue(host: fake.HostingService) -> fake.HostingService:
    host.set_base(fake.Base(queue=True))
    return host


def _ask(request_: str, here: dict[str, Any]) -> landing.Outcome:
    if request_ == "merge":
        return landing.squash_merge(496, subject="fix: land it", head_oid=fake.HEAD, **here)
    if request_ == "enqueue":
        return landing.enqueue(496, head_oid=fake.HEAD, **here)
    return landing.dequeue(496, **here)


_ENDED_AT_ITS_BOUND = "`gh` did not answer within 30 s, and was ended"


@pytest.mark.parametrize(
    ("setup", "request_"),
    [
        (lambda host: host.lose_reply(fake.MERGE), "merge"),
        (lambda host: _queue(host).lose_reply(fake.MERGE), "merge"),
        (lambda host: _queue(host).lose_reply(fake.ENQUEUE), "enqueue"),
        (lambda host: host.error_after(fake.MERGE), "merge"),
        (lambda host: host.error_after(fake.MERGE, stderr=""), "merge"),
        (
            lambda host: host.error_after(
                fake.MERGE,
                stderr='Post "https://api.github.com/graphql": read tcp 10.0.0.2:51234->'
                "140.82.112.6:443: read: connection reset by peer",
            ),
            "merge",
        ),
        (lambda host: _queue(host).error_after(fake.ENQUEUE, stderr="unexpected EOF"), "enqueue"),
    ],
    ids=[
        "merge-ended-at-its-bound-reads-merged",
        "merge-on-a-queue-ended-at-its-bound-reads-queued",
        "enqueue-ended-at-its-bound-reads-queued",
        "merge-answered-502-reads-merged",
        "merge-answered-nothing-reads-merged",
        "merge-reset-reads-merged",
        "enqueue-eof-reads-queued",
    ],
)
def test_a_request_with_no_answer_whose_end_state_one_reading_finds_was_made(
    setup: Callable[[fake.HostingService], Any],
    request_: str,
    here: dict[str, Any],
    acting: Callable[[landing.GhRunner], None],
    slept: list[float],
) -> None:
    """Ended at its bound, or its answer lost on the way — a server error, a
    reset, nothing back — the request may have been made: one reading at its
    end state (merged; queued — a merge on a base that requires a queue
    enqueues) says it was, with no exit code of gh's to report."""
    host = fake.HostingService()
    setup(host)
    acting(_bounded(host))
    assert _ask(request_, here) == landing.Outcome(True, None)
    assert host.kinds() == [fake.ENQUEUE if request_ == "enqueue" else fake.MERGE, fake.READ]
    assert slept == []


def test_a_request_the_service_was_still_making_shows_in_the_second_reading(
    here: dict[str, Any], acting: Callable[[landing.GhRunner], None], slept: list[float]
) -> None:
    host = fake.HostingService()
    host.never_receive(fake.MERGE)
    host.after(fake.READ, lambda service: service.merge_now())
    acting(_bounded(host))
    assert _ask("merge", here) == landing.Outcome(True, None)
    assert host.kinds() == [fake.MERGE, fake.READ, fake.READ]
    assert slept == [landing.SETTLE_INTERVAL_SECONDS]


@pytest.mark.parametrize(
    ("request_", "setup", "found"),
    [
        ("merge", lambda host: host, "neither merged nor queued (not in the queue)"),
        ("enqueue", _queue, "neither queued nor merged (not in the queue)"),
        ("dequeue", lambda host: _queue(host).enter_queue(), "still queued (in the queue)"),
    ],
)
def test_a_request_with_no_answer_read_short_of_its_end_twice_running_was_not_made(
    request_: str,
    setup: Callable[[fake.HostingService], Any],
    found: str,
    here: dict[str, Any],
    acting: Callable[[landing.GhRunner], None],
    slept: list[float],
) -> None:
    """Never received, nothing back: two readings running, the interval apart,
    find its end state not reached — only then is it not made (ADR-061 point
    7), not accepted with `reason_kind` `not-made`, and no exit code of gh's."""
    host = fake.HostingService()
    setup(host)
    kind = {"merge": fake.MERGE, "enqueue": fake.ENQUEUE, "dequeue": fake.DEQUEUE}[request_]
    host.never_receive(kind)
    acting(_bounded(host))
    outcome = _ask(request_, here)
    assert (outcome.accepted, outcome.exit_code, outcome.reason_kind) == (
        False,
        None,
        landing.NOT_MADE,
    )
    assert outcome.reason == (
        f"the {request_} of PR #496 got no answer ({_ENDED_AT_ITS_BOUND}), and two readings "
        f"since, 10 s apart, find PR #496 {found}: the {request_} was not made"
    )
    assert host.kinds()[-3:] == [kind, fake.READ, fake.READ]
    assert slept == [landing.SETTLE_INTERVAL_SECONDS]


@pytest.mark.parametrize("readable", [0, 1], ids=["no-reading", "one-reading-then-none"])
@pytest.mark.parametrize("request_", ["merge", "enqueue", "dequeue"])
def test_a_request_with_no_answer_and_no_reading_to_settle_it_is_unconfirmed(
    request_: str,
    readable: int,
    here: dict[str, Any],
    acting: Callable[[landing.GhRunner], None],
    slept: list[float],
) -> None:
    """A reading that cannot be taken leaves the request unconfirmed:
    `accepted` and `exit_code` None — whether it was made, and how gh would
    have ended, are not known — `reason_kind` `unanswered`, and a reason that
    states no refusal."""
    host = fake.HostingService()
    if request_ != "merge":
        _queue(host)
    if request_ == "dequeue":
        host.enter_queue()
    kind = {"merge": fake.MERGE, "enqueue": fake.ENQUEUE, "dequeue": fake.DEQUEUE}[request_]
    host.never_receive(kind)

    def unreadable_since(service: fake.HostingService) -> None:
        service.fail(fake.READ, first=service.seen(fake.READ) + 1 + readable, count=None)

    host.before(kind, unreadable_since)
    acting(_bounded(host))
    outcome = _ask(request_, here)
    assert (outcome.accepted, outcome.exit_code, outcome.reason_kind) == (
        None,
        None,
        landing.UNANSWERED,
    )
    assert outcome.reason == (
        f"the {request_} of PR #496 got no answer ({_ENDED_AT_ITS_BOUND}), and PR #496 could "
        f"not be read since (HTTP 502: Bad Gateway): whether the {request_} was made is not "
        "known"
    )
    assert slept == [landing.SETTLE_INTERVAL_SECONDS] * readable


def test_a_dequeue_with_no_answer_that_reads_merged_since_was_not_accepted(
    here: dict[str, Any], acting: Callable[[landing.GhRunner], None], slept: list[float]
) -> None:
    """The queue merged the PR while it was being taken out: no dequeue undoes
    that, so it is not accepted, saying so — not a request that was not made."""
    host = _queue(fake.HostingService())
    host.enter_queue()
    host.never_receive(fake.DEQUEUE)
    host.before(fake.READ, lambda service: service.merge_now(), nth=2)
    acting(_bounded(host))
    outcome = _ask("dequeue", here)
    assert (outcome.accepted, outcome.reason_kind) == (False, "")
    assert outcome.reason.startswith("PR #496 has merged (merged at ")


@pytest.mark.parametrize(
    "stderr",
    [
        "GraphQL: Head branch was modified. Review and try the merge again. (mergePullRequest)",
        "GraphQL: Pull request is not mergeable (mergePullRequest)",
        "HTTP 403: Resource not accessible by integration (https://api.github.com/graphql)",
        "X Pull request #496 is not mergeable: the base branch policy prohibits the merge.",
    ],
)
def test_a_request_the_service_answered_with_an_error_is_refused_in_its_words_unread(
    stderr: str,
    here: dict[str, Any],
    acting: Callable[[landing.GhRunner], None],
    slept: list[float],
) -> None:
    """The service said no: a refusal with its words, as before — never taken
    for a request with no answer, and nothing is read to settle it."""
    host = fake.HostingService()
    host.fail(fake.MERGE, stderr=stderr)
    acting(_bounded(host))
    assert _ask("merge", here) == landing.Outcome(False, 1, stderr)
    assert host.kinds() == [fake.MERGE]
    assert slept == []


def test_a_reading_gh_does_not_answer_within_its_bound_is_unreadable() -> None:
    def hung(argv: Sequence[str]) -> Completed:
        raise subprocess.TimeoutExpired(list(argv), landing.GH_READ_SECONDS)

    with pytest.raises(landing.Unreadable, match=r"`gh` did not answer within 15 s, and was ended"):
        landing.read(496, gh=hung)


def test_the_modules_own_gh_is_bounded_by_the_kind_of_each_call(
    here: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Every `gh` call goes through the command runner's one bounded start,
    from the directory the request acts in: a reading bounded as a reading, a
    request as a request."""
    host = _queue(fake.HostingService())
    host.enter_queue()
    started: list[tuple[Path | None, float]] = []

    def bounded(argv: Sequence[str], *, cwd: Path | None, seconds: float) -> Completed:
        started.append((cwd, seconds))
        return host(argv)

    monkeypatch.setattr(command_runner, "run_bounded", bounded)
    assert landing.dequeue(496, **here).accepted
    landing.read(496)
    where = Path(here["cwd"]).resolve()
    read, request = landing.GH_READ_SECONDS, landing.GH_REQUEST_SECONDS
    assert host.kinds() == [fake.READ, fake.DEQUEUE, fake.READ, fake.READ]
    assert started == [(where, read), (where, request), (where, read), (None, read)]


# --- the guard on the requests ---------------------------------------------------


@pytest.mark.parametrize("request_", ["merge", "enqueue", "dequeue"])
def test_a_request_is_made_only_where_its_clearance_was_given(
    request_: str, here: dict[str, Any], tmp_path: Path, acting: Callable[[landing.GhRunner], None]
) -> None:
    """A clearance covers the directory the guard looked at; a request aimed
    at another is not made."""
    calls: list[list[str]] = []
    acting(_gh([_QUEUED], calls))
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    kwargs: dict[str, Any] = {"cwd": elsewhere, "clearance": here["clearance"]}
    with pytest.raises(ValueError, match="the clearance is for"):
        if request_ == "merge":
            landing.squash_merge(42, subject="fix: x", **kwargs)
        elif request_ == "enqueue":
            landing.enqueue(42, **kwargs)
        else:
            landing.dequeue(42, **kwargs)
    assert calls == []


@pytest.mark.parametrize("request_", ["merge", "enqueue", "dequeue"])
def test_a_request_runs_gh_where_the_guard_looked_and_nowhere_else(
    request_: str, here: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A request takes no client from its caller: it runs `gh` from the
    directory its clearance covers, so a clearance for one directory cannot
    run `gh` in another."""
    places: list[Path] = []

    def runner(cwd: Path) -> landing.GhRunner:
        places.append(cwd)
        return _gh([_QUEUED, _OUT])

    monkeypatch.setattr(landing, "gh_runner", runner)
    if request_ == "merge":
        assert landing.squash_merge(42, subject="fix: x", **here).accepted
    elif request_ == "enqueue":
        assert landing.enqueue(42, **here).accepted
    else:
        assert landing.dequeue(42, **here).accepted
    assert places == [Path(here["cwd"]).resolve()]
    for request in (landing.squash_merge, landing.enqueue, landing.dequeue):
        assert "gh" not in inspect.signature(request).parameters


# --- delete_branch: the head branch, only at the head that merged (#1255) ------------


def _merged_host(**fields: Any) -> fake.HostingService:
    """The shared fake GitHub, its PR merged at its head `fake.HEAD`, whose
    branch is still there."""
    host = fake.HostingService(**fields)
    host.merge_now()
    return host


def _delete(
    host: fake.HostingService,
    here: dict[str, Any],
    acting: Callable[[landing.GhRunner], None],
    expect: str = fake.HEAD,
) -> landing.BranchDeletion:
    acting(host)
    return landing.delete_branch(496, expect=expect, **here)


def _stacked(host: fake.HostingService, number: int = 503) -> None:
    """Another open PR, based on the PR's head branch: stacked on it."""
    host.others.append(
        fake.OtherPullRequest(
            number, f"fix/{number}-on-top", fake.oid("on-top"), base_ref=host.head_ref
        )
    )


def test_a_branch_at_the_head_that_merged_is_deleted_in_one_compare_and_delete(
    here: dict[str, Any], acting: Callable[[landing.GhRunner], None]
) -> None:
    """Two readings — the PR and its branch, then the open PRs based on the
    branch — then one request that deletes the branch only while it is at
    the head named: GitHub's `updateRefs`, the all-zero commit as its end."""
    host = _merged_host()
    deletion = _delete(host, here, acting)
    assert deletion == landing.BranchDeletion(
        landing.DELETED, "fix/42-land-it", merged_head=fake.HEAD
    )
    assert host.kinds() == [fake.BRANCH, fake.BASED_ON, fake.DELETE_REF]
    assert "branch=fix/42-land-it" in host.requests[1].argv
    request = host.requests[2].argv
    assert {
        "repository=R_project",
        "name=refs/heads/fix/42-land-it",
        f"before={fake.HEAD}",
        "after=" + "0" * 40,
    } <= set(request)
    assert "fix/42-land-it" not in host.refs


@pytest.mark.parametrize(
    ("setup", "outcome", "reason_kind", "tip", "kinds"),
    [
        (
            lambda host: host.move_branch("sha-later"),
            "kept",
            "tip-moved",
            "sha-later",
            [fake.BRANCH],
        ),
        (lambda host: host.refs.pop(host.head_ref), "gone", "", "", [fake.BRANCH]),
        (
            lambda host: setattr(host, "cross_repository", True),
            "refused",
            "cross-repository",
            "",
            [fake.BRANCH],
        ),
        (
            lambda host: host.others.append(
                fake.OtherPullRequest(501, host.head_ref, host.head_oid)
            ),
            "kept",
            "open-pull-request",
            fake.HEAD,
            [fake.BRANCH, fake.BASED_ON],
        ),
        (
            _stacked,
            "kept",
            "open-pull-request",
            fake.HEAD,
            [fake.BRANCH, fake.BASED_ON],
        ),
        (
            lambda host: (
                host.move_branch("sha-new"),
                host.others.append(fake.OtherPullRequest(502, host.head_ref, "sha-new")),
            ),
            "kept",
            "tip-moved",
            "sha-new",
            [fake.BRANCH],
        ),
    ],
    ids=[
        "tip-moved",
        "already-gone",
        "fork",
        "another-open-pr-uses-it-as-its-head",
        "another-open-pr-is-based-on-it",
        "reused-branch-name",
    ],
)
def test_what_the_readings_find_decides_and_no_deletion_is_asked(
    here: dict[str, Any],
    acting: Callable[[landing.GhRunner], None],
    setup: Callable[[fake.HostingService], object],
    outcome: str,
    reason_kind: str,
    tip: str,
    kinds: list[str],
) -> None:
    """A tip moved since the merge — a push, or a branch of the same name made
    since — is kept, with its tip; a branch gone is gone; a fork's is refused;
    one another open PR uses as its head or its base is kept. The readings
    alone tell, so no deletion is asked for."""
    host = _merged_host()
    setup(host)
    deletion = _delete(host, here, acting)
    assert (deletion.outcome, deletion.reason_kind, deletion.tip) == (outcome, reason_kind, tip)
    assert deletion.merged_head == fake.HEAD
    assert host.kinds() == kinds
    assert all(other.state == "OPEN" for other in host.others)


def test_a_branch_another_open_pr_uses_as_its_head_is_kept_for_it(
    here: dict[str, Any], acting: Callable[[landing.GhRunner], None]
) -> None:
    host = _merged_host()
    host.others.append(fake.OtherPullRequest(501, host.head_ref, host.head_oid))
    assert _delete(host, here, acting).reason == (
        "another open pull request uses this branch as its head (#501): deleting it would "
        "close that pull request"
    )


def test_a_branch_open_prs_are_based_on_is_kept_and_none_of_them_is_touched(
    here: dict[str, Any], acting: Callable[[landing.GhRunner], None]
) -> None:
    """A stacked PR, an integration branch, a long-lived branch others merge
    into: whatever the service would do to the PRs based on a deleted branch,
    the branch is kept, and the reason says how many use it and which."""
    host = _merged_host()
    _stacked(host, 503)
    _stacked(host, 504)
    deletion = _delete(host, here, acting)
    assert (deletion.outcome, deletion.reason_kind) == ("kept", "open-pull-request")
    assert deletion.reason == (
        "2 other open pull requests are based on this branch (#503, #504), and a branch an "
        "open pull request merges into is kept"
    )
    assert host.remote_deletion() == "none" and host.head_ref in host.refs


def test_more_open_prs_than_the_readings_name_are_counted(
    here: dict[str, Any], acting: Callable[[landing.GhRunner], None]
) -> None:
    """The readings name the first few open PRs on the branch and count them
    all, as their head and as their base alike; the PR being deleted for is
    never one of them."""
    host = _merged_host()
    for number in range(501, 509):
        host.others.append(fake.OtherPullRequest(number, host.head_ref, host.head_oid))
    _stacked(host, 510)
    deletion = _delete(host, here, acting)
    assert (deletion.outcome, deletion.reason_kind) == ("kept", "open-pull-request")
    assert deletion.reason == (
        "8 other open pull requests use this branch as their head (#501, #502, #503, #504, "
        "#505 and 3 more): deleting it would close them; another open pull request is based "
        "on this branch (#510), and a branch an open pull request merges into is kept"
    )


def _malformed(path: str) -> Callable[[landing.GhRunner], landing.GhRunner]:
    """A `gh` answering as `host` does, but with the count at `path` — the
    reading's `associatedPullRequests` or the second reading's
    `pullRequests` — missing or not a number."""

    def wrap(host: landing.GhRunner) -> landing.GhRunner:
        def gh(argv: Sequence[str]) -> Completed:
            done = host(argv)
            answer = json.loads(done.stdout or "null")
            if not isinstance(answer, dict):
                return done
            repository = answer["data"]["repository"]
            if path == "head" and "pullRequest" in repository:
                repository["pullRequest"]["headRef"].pop("associatedPullRequests")
            elif path == "head-count" and "pullRequest" in repository:
                repository["pullRequest"]["headRef"]["associatedPullRequests"]["totalCount"] = "7"
            elif path == "base" and "pullRequests" in repository:
                repository.pop("pullRequests")
            elif path == "base-count" and "pullRequests" in repository:
                repository["pullRequests"]["totalCount"] = None
            return subprocess.CompletedProcess(done.args, 0, stdout=json.dumps(answer), stderr="")

        return gh

    return wrap


@pytest.mark.parametrize("path", ["head", "head-count", "base", "base-count"])
def test_an_open_pr_count_the_answer_does_not_give_is_refused_never_read_as_none(
    here: dict[str, Any], acting: Callable[[landing.GhRunner], None], path: str
) -> None:
    """A missing or malformed count of the open PRs that use the branch — as
    their head or as their base — is not taken for none: refused, unreadable,
    nothing sent, as a missing `isCrossRepository` reads as a fork."""
    host = _merged_host()
    acting(_malformed(path)(host))
    deletion = landing.delete_branch(496, expect=fake.HEAD, **here)
    assert (deletion.outcome, deletion.reason_kind) == ("refused", "unreadable")
    assert fake.DELETE_REF not in host.kinds() and host.head_ref in host.refs


def test_a_pr_that_has_not_merged_is_refused_and_nothing_is_deleted(
    here: dict[str, Any], acting: Callable[[landing.GhRunner], None]
) -> None:
    host = fake.HostingService()
    deletion = _delete(host, here, acting)
    assert (deletion.outcome, deletion.reason_kind) == ("refused", "not-merged")
    assert host.kinds() == [fake.BRANCH] and host.head_ref in host.refs


def test_a_head_other_than_the_one_the_pr_merged_at_is_refused_and_nothing_is_sent(
    here: dict[str, Any], acting: Callable[[landing.GhRunner], None]
) -> None:
    """`expect` is checked against the PR's own head: the branch is deleted
    only at the head that merged, whatever the caller believes it to be. The
    reason names both."""
    host = _merged_host()
    other = fake.oid("other")
    deletion = _delete(host, here, acting, expect=other)
    assert deletion == landing.BranchDeletion(
        landing.REFUSED,
        "fix/42-land-it",
        reason_kind="expect-mismatch",
        reason=f"the head named, {other}, is not the head PR #496 merged at, {fake.HEAD}: its "
        "head branch is deleted only at that head",
        merged_head=fake.HEAD,
    )
    assert host.kinds() == [fake.BRANCH] and host.head_ref in host.refs


def test_a_branch_protected_from_deletion_is_kept_with_what_the_service_said(
    here: dict[str, Any], acting: Callable[[landing.GhRunner], None]
) -> None:
    """The service answers the deletion with an error — only that something
    went wrong, as it answers any refused `updateRefs` — and a second reading
    finds the branch still at the head that merged: kept, the service's
    answer carried as it is."""
    host = _merged_host()
    host.protected.add(host.head_ref)
    deletion = _delete(host, here, acting)
    assert (deletion.outcome, deletion.reason_kind, deletion.tip) == (
        "kept",
        "deletion-refused",
        fake.HEAD,
    )
    assert deletion.reason == f"the service did not delete it: {fake.NO_REASON}"
    assert host.kinds() == [fake.BRANCH, fake.BASED_ON, fake.DELETE_REF, fake.BRANCH]


def test_a_push_between_the_reading_and_the_request_is_not_lost(
    here: dict[str, Any], acting: Callable[[landing.GhRunner], None]
) -> None:
    """The compare and the delete are one request: a push that lands after
    the reading fails the deletion, and the reading after it tells why."""
    host = _merged_host()
    host.before(fake.DELETE_REF, lambda h: h.move_branch("sha-raced"))
    deletion = _delete(host, here, acting)
    assert (deletion.outcome, deletion.reason_kind, deletion.tip) == (
        "kept",
        "tip-moved",
        "sha-raced",
    )
    assert host.refs[host.head_ref] == "sha-raced"
    assert host.remote_deletion() == "refused, tip sha-raced"


def test_a_branch_deleted_between_the_reading_and_the_request_is_gone(
    here: dict[str, Any], acting: Callable[[landing.GhRunner], None]
) -> None:
    host = _merged_host()

    def deleted_meanwhile(h: fake.HostingService) -> None:
        del h.refs[h.head_ref]

    host.before(fake.DELETE_REF, deleted_meanwhile)
    assert _delete(host, here, acting).outcome == "gone"


def test_a_pr_that_cannot_be_read_is_refused_and_nothing_is_asked(
    here: dict[str, Any], acting: Callable[[landing.GhRunner], None]
) -> None:
    host = _merged_host()
    host.fail(fake.BRANCH, count=None)
    deletion = _delete(host, here, acting)
    assert (deletion.outcome, deletion.reason_kind) == ("refused", "unreadable")
    assert deletion.reason == "PR #496 could not be read: HTTP 502: Bad Gateway"
    assert host.kinds() == [fake.BRANCH]


def test_open_prs_based_on_the_branch_that_cannot_be_read_refuse_the_deletion(
    here: dict[str, Any], acting: Callable[[landing.GhRunner], None]
) -> None:
    host = _merged_host()
    host.fail(fake.BASED_ON)
    deletion = _delete(host, here, acting)
    assert (deletion.outcome, deletion.reason_kind) == ("refused", "unreadable")
    assert deletion.reason == (
        "which open pull requests are based on 'fix/42-land-it' could not be read: HTTP 502: "
        "Bad Gateway"
    )
    assert host.kinds() == [fake.BRANCH, fake.BASED_ON]


def test_a_refused_deletion_with_no_reading_after_it_is_kept_at_the_tip_read_before(
    here: dict[str, Any], acting: Callable[[landing.GhRunner], None]
) -> None:
    """The service answered, so this request deleted nothing: kept, at the
    tip read before the request, whatever the branch has become since."""
    host = _merged_host()
    host.protected.add(host.head_ref)
    host.fail(fake.BRANCH, first=2)
    deletion = _delete(host, here, acting)
    assert (deletion.outcome, deletion.reason_kind, deletion.tip) == (
        "kept",
        "deletion-refused",
        fake.HEAD,
    )
    assert deletion.reason.endswith("; the branch could not be read since (HTTP 502: Bad Gateway)")


# The deletion request made and its answer lost — a 502 after the service
# acted, a reset — or never applied: gh fails with nothing from the service in
# what it prints. The reading after it tells which, where it can be taken.


def test_an_answer_lost_after_the_branch_was_deleted_reads_it_gone(
    here: dict[str, Any], acting: Callable[[landing.GhRunner], None]
) -> None:
    """Whether this request deleted it is not provable, but the branch is not
    there, which is what was asked: gone."""
    host = _merged_host()
    host.error_after(fake.DELETE_REF)
    deletion = _delete(host, here, acting)
    assert (deletion.outcome, deletion.reason_kind, deletion.tip) == ("gone", "", "")
    assert host.remote_deletion() == fake.ERROR_AFTER
    assert host.kinds() == [fake.BRANCH, fake.BASED_ON, fake.DELETE_REF, fake.BRANCH]


def test_an_answer_lost_with_the_branch_still_at_the_head_is_kept_unanswered(
    here: dict[str, Any], acting: Callable[[landing.GhRunner], None]
) -> None:
    """The reading since finds the branch where it was: the request was not
    applied, and the branch is kept, with its tip."""
    host = _merged_host()
    host.fail(fake.DELETE_REF)
    deletion = _delete(host, here, acting)
    assert (deletion.outcome, deletion.reason_kind, deletion.tip) == (
        "kept",
        "unanswered",
        fake.HEAD,
    )
    assert deletion.reason == (
        "the deletion got no usable answer (HTTP 502: Bad Gateway), and a reading since finds "
        f"the branch still at {fake.HEAD[:7]}: the request was not applied"
    )
    assert host.head_ref in host.refs


def test_an_answer_lost_with_no_reading_since_is_unconfirmed_and_states_no_tip(
    here: dict[str, Any], acting: Callable[[landing.GhRunner], None]
) -> None:
    """The case that was misreported: the branch may be gone, so no tip and
    no refusal are stated — only that whether it was deleted is not known."""
    host = _merged_host()
    host.error_after(fake.DELETE_REF)
    host.fail(fake.BRANCH, first=2)
    deletion = _delete(host, here, acting)
    assert deletion == landing.BranchDeletion(
        landing.UNCONFIRMED,
        "fix/42-land-it",
        reason_kind="unanswered",
        reason="the deletion got no usable answer (HTTP 502: Bad Gateway), and the branch "
        "could not be read since (HTTP 502: Bad Gateway)",
        merged_head=fake.HEAD,
    )
    assert host.head_ref not in host.refs
    assert deletion.describe().startswith(
        "whether remote branch 'fix/42-land-it' was deleted is not known: "
    )


@pytest.mark.parametrize(
    ("value", "full"),
    [
        ("a" * 40, "a" * 40),
        ("B" * 64, "b" * 64),
        (f"  {'c' * 40}\n", "c" * 40),
        ("a" * 7, ""),
        ("a" * 39, ""),
        ("a" * 41, ""),
        ("g" * 40, ""),
        ("", ""),
    ],
    ids=[
        "sha-1",
        "sha-256-upper",
        "surrounded",
        "abbreviated",
        "short",
        "long",
        "not-hex",
        "empty",
    ],
)
def test_a_full_object_id_is_40_or_64_hexadecimal_characters(value: str, full: str) -> None:
    assert landing.full_object_id(value) == full


def test_the_deletion_is_made_only_where_its_clearance_was_given(
    here: dict[str, Any], tmp_path: Path, acting: Callable[[landing.GhRunner], None]
) -> None:
    host = _merged_host()
    acting(host)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    with pytest.raises(ValueError, match="the clearance is for"):
        landing.delete_branch(496, expect=fake.HEAD, cwd=elsewhere, clearance=here["clearance"])
    assert host.requests == []


def test_the_deletion_runs_gh_where_the_guard_looked_and_takes_no_client(
    here: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    places: list[Path] = []
    host = _merged_host()

    def runner(cwd: Path) -> landing.GhRunner:
        places.append(cwd)
        return host

    monkeypatch.setattr(landing, "gh_runner", runner)
    assert landing.delete_branch(496, expect=fake.HEAD, **here).outcome == "deleted"
    assert places == [Path(here["cwd"]).resolve()]
    assert "gh" not in inspect.signature(landing.delete_branch).parameters


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
        runner = _gh(answers, calls)
        monkeypatch.setattr(landing, "run_gh", runner)
        monkeypatch.setattr(landing, "gh_runner", lambda cwd: runner)
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
        {
            "schema_version": 1,
            "pull_request": 42,
            "accepted": True,
            "exit_code": 0,
            "reason": "",
            "reason_kind": None,
            "guard": {
                "verdict": "undetermined",
                "undetermined_kind": "noncoverage",
                "anchor": None,
                "target": None,
                "cleared": "undetermined",
            },
        }
    ]
    result = _invoke("merge", "42", "--subject", "fix: x", "--head", "sha")
    assert result.exit_code == 0
    assert "gh accepted the squash merge of PR #42" in result.stdout
    assert calls[-1][-2:] == ["--match-head-commit", "sha"]


def test_a_refused_request_exits_1(monkeypatch: pytest.MonkeyPatch) -> None:
    def refusing(argv: Sequence[str]) -> Completed:
        return subprocess.CompletedProcess(list(argv), 1, stdout="", stderr="not mergeable")

    monkeypatch.setattr(landing, "gh_runner", lambda cwd: refusing)
    result = _invoke("merge", "42", "--subject", "fix: x", "--json")
    assert result.exit_code == 1
    [document] = _lines(result.stdout)
    assert document["reason"] == "not mergeable" and document["reason_kind"] is None


def _unanswered_host(monkeypatch: pytest.MonkeyPatch, ends: str) -> fake.HostingService:
    """The noun's `gh`: the shared fake, whose merge gets no answer and which,
    since, reads the PR merged (`made`), open twice (`not-made`) or not at all
    (`unconfirmed`); the interval not slept."""
    host = fake.HostingService()
    if ends == "made":
        host.lose_reply(fake.MERGE)
    else:
        host.never_receive(fake.MERGE)
    if ends == "unconfirmed":
        host.before(fake.MERGE, lambda service: service.fail(fake.READ, count=None))
    monkeypatch.setattr(landing, "gh_runner", lambda cwd: _bounded(host))
    monkeypatch.setattr(landing, "_sleep", lambda seconds: None)
    return host


@pytest.mark.parametrize(
    ("ends", "code", "accepted", "reason_kind"),
    [
        ("made", 0, True, None),
        ("not-made", 1, False, "not-made"),
        ("unconfirmed", 1, None, "unanswered"),
    ],
)
def test_a_merge_with_no_answer_writes_how_it_settled_and_exits_by_it(
    monkeypatch: pytest.MonkeyPatch,
    ends: str,
    code: int,
    accepted: bool | None,
    reason_kind: str | None,
) -> None:
    """Made: accepted, exit 0, no exit code of gh's. Not made on two readings
    running: not accepted, `not-made`, exit 1. Unconfirmed: `accepted` null —
    the one null it takes, saying whether it was made is not known —
    `unanswered`, exit 1, as `delete-branch`'s unconfirmed exits."""
    _unanswered_host(monkeypatch, ends)
    result = _invoke("merge", "496", "--subject", "fix: land it", "--json")
    assert result.exit_code == code
    [document] = _lines(result.stdout)
    assert (document["accepted"], document["exit_code"], document["reason_kind"]) == (
        accepted,
        None,
        reason_kind,
    )
    assert set(document) == {
        "schema_version",
        "pull_request",
        "accepted",
        "exit_code",
        "reason",
        "reason_kind",
        "guard",
    }


def test_a_merge_with_no_answer_says_how_it_settled_to_a_person(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _unanswered_host(monkeypatch, "made")
    made = _invoke("merge", "496", "--subject", "fix: land it")
    assert made.stdout == (
        "the squash merge of PR #496 got no answer, and a reading since shows it made\n"
    )
    _unanswered_host(monkeypatch, "unconfirmed")
    unknown = _invoke("merge", "496", "--subject", "fix: land it")
    assert unknown.exit_code == 1
    assert unknown.stderr == (
        f"error: the merge of PR #496 got no answer ({_ENDED_AT_ITS_BOUND}), and PR #496 could "
        "not be read since (HTTP 502: Bad Gateway): whether the merge was made is not known. "
        "Read where PR #496 stands: `pkit pull-request read 496`.\n"
    )


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


# --- `pkit pull-request`: the cross-repository guard -------------------------------


@pytest.fixture
def foreign(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A session rooted in one repository, run from another: the target."""
    _, target = sessions.rooted_elsewhere(tmp_path, monkeypatch)
    monkeypatch.chdir(target)
    return target


_REQUESTS = [
    ["merge", "42", "--subject", "fix: x", "--head", "sha"],
    ["enqueue", "42", "--head", "sha"],
    ["dequeue", "42"],
]


@pytest.mark.parametrize("args", _REQUESTS, ids=["merge", "enqueue", "dequeue"])
def test_a_request_in_another_repository_with_no_terminal_is_refused_unmade(
    args: list[str], fake_gh: Any, foreign: Path
) -> None:
    """No terminal to ask (the runner's input is not one) and no flag: the
    document says the guard refused, and nothing was asked of GitHub."""
    calls = fake_gh([_QUEUED, _OUT])
    result = _invoke(*args, "--json")
    assert result.exit_code == 1
    [document] = _lines(result.stdout)
    assert document["accepted"] is False and document["exit_code"] is None
    assert document["reason_kind"] == "foreign-repository"
    assert document["guard"]["verdict"] == "diverged"
    assert document["guard"]["cleared"] is None
    assert document["guard"]["target"] == str(foreign.resolve())
    assert "--allow-foreign-repo" in document["reason"]
    assert document["schema_version"] == landing.SCHEMA_VERSION
    assert calls == []


def test_a_refusal_says_why_and_names_the_flag(fake_gh: Any, foreign: Path) -> None:
    calls = fake_gh([_QUEUED])
    result = _invoke("enqueue", "42")
    assert result.exit_code == 1
    assert "the cross-repository guard refused" in result.stderr
    assert "--allow-foreign-repo" in result.stderr
    assert "Nothing was asked of GitHub" in result.stderr
    assert calls == []


@pytest.mark.parametrize("args", _REQUESTS, ids=["merge", "enqueue", "dequeue"])
def test_the_flag_confirms_a_request_in_another_repository(
    args: list[str], fake_gh: Any, foreign: Path
) -> None:
    calls = fake_gh([_QUEUED, _OUT])
    result = _invoke(*args, "--allow-foreign-repo", "--json")
    assert result.exit_code == 0
    [document] = _lines(result.stdout)
    assert document["accepted"] is True and document["reason_kind"] is None
    assert (document["guard"]["verdict"], document["guard"]["cleared"]) == ("diverged", "flag")
    assert calls


@pytest.mark.parametrize("where", ["checkout", "worktree"])
@pytest.mark.parametrize("args", _REQUESTS, ids=["merge", "enqueue", "dequeue"])
def test_in_the_sessions_own_repository_a_request_clears_as_same_repo_and_is_made(
    args: list[str],
    where: str,
    fake_gh: Any,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Through the CLI, on real git: a session rooted in a repository, and the
    request run from that repository — its checkout, or a linked worktree of
    it, which shares its common directory — clears as `same-repo`, asks
    nothing, and is made."""
    anchor = sessions.repository(tmp_path / "project", "https://github.com/octo/project.git")
    identity = ["-c", "user.name=t", "-c", "user.email=t@e"]
    subprocess.run(
        ["git", *identity, "commit", "-q", "--allow-empty", "-m", "init"], cwd=anchor, check=True
    )
    subprocess.run(
        ["git", "worktree", "add", "-q", "-b", "fix/42-x", str(tmp_path / "worktree")],
        cwd=anchor,
        check=True,
        capture_output=True,
    )
    monkeypatch.setenv(session_guard.CLAUDE_CODE_ANCHOR, str(anchor))
    monkeypatch.chdir(anchor if where == "checkout" else tmp_path / "worktree")
    calls = fake_gh([_QUEUED, _OUT])
    result = _invoke(*args, "--json")
    assert result.exit_code == 0, result.output
    [document] = _lines(result.stdout)
    assert document["accepted"] is True and document["reason_kind"] is None
    assert (document["guard"]["verdict"], document["guard"]["cleared"]) == (
        "same-repo",
        "same-repo",
    )
    assert document["guard"]["anchor"] == str(anchor.resolve())
    assert calls
    assert "Make the change there anyway?" not in result.stderr


def test_the_readings_and_the_wait_run_no_guard(fake_gh: Any, foreign: Path) -> None:
    fake_gh([_QUEUED, _MERGED])
    assert _invoke("read", "496", "--json").exit_code == 0
    assert _invoke("wait", "496", "--json").exit_code == 0


# --- `pkit pull-request delete-branch` (#1255) ----------------------------------------

#: The keys of `delete-branch`'s document, each always present.
_DELETION_KEYS = {
    "schema_version",
    "pull_request",
    "expected",
    "outcome",
    "branch",
    "tip",
    "reason_kind",
    "reason",
    "merged_head",
    "guard",
}


@pytest.fixture
def hosted(monkeypatch: pytest.MonkeyPatch) -> fake.HostingService:
    """The shared fake GitHub as the command's `gh`: its PR merged at
    `fake.HEAD`, whose head branch is still there."""
    host = _merged_host()
    monkeypatch.setattr(landing, "gh_runner", lambda cwd: host)
    return host


def _delete_branch(*options: str, expect: str = fake.HEAD) -> Any:
    return _invoke("delete-branch", "496", "--expect", expect, *options)


def _lost_answer_unread(host: fake.HostingService) -> None:
    """The deletion made, its answer lost, and no reading since."""
    host.error_after(fake.DELETE_REF)
    host.fail(fake.BRANCH, first=2)


@pytest.mark.parametrize(
    ("setup", "outcome", "reason_kind", "tip", "code"),
    [
        (lambda host: None, "deleted", None, None, 0),
        (lambda host: host.move_branch("sha-later"), "kept", "tip-moved", "sha-later", 0),
        (lambda host: host.refs.pop(host.head_ref), "gone", None, None, 0),
        (
            lambda host: host.protected.add(host.head_ref),
            "kept",
            "deletion-refused",
            fake.HEAD,
            0,
        ),
        (
            lambda host: host.others.append(
                fake.OtherPullRequest(501, host.head_ref, host.head_oid)
            ),
            "kept",
            "open-pull-request",
            fake.HEAD,
            0,
        ),
        (_stacked, "kept", "open-pull-request", fake.HEAD, 0),
        (lambda host: host.fail(fake.DELETE_REF), "kept", "unanswered", fake.HEAD, 0),
        (lambda host: host.error_after(fake.DELETE_REF), "gone", None, None, 0),
        (_lost_answer_unread, "unconfirmed", "unanswered", None, 1),
        (
            lambda host: setattr(host, "cross_repository", True),
            "refused",
            "cross-repository",
            None,
            1,
        ),
        (
            lambda host: (setattr(host, "state", "OPEN"), setattr(host, "merged_at", "")),
            "refused",
            "not-merged",
            None,
            1,
        ),
    ],
    ids=[
        "deleted",
        "tip-moved",
        "gone",
        "protected",
        "in-use-as-head",
        "in-use-as-base",
        "unanswered-still-there",
        "unanswered-gone",
        "unconfirmed",
        "fork",
        "not-merged",
    ],
)
def test_delete_branch_writes_one_document_and_exits_by_its_outcome(
    hosted: fake.HostingService,
    setup: Callable[[fake.HostingService], object],
    outcome: str,
    reason_kind: str | None,
    tip: str | None,
    code: int,
) -> None:
    """Exit 0 when the command reached an end it can state — deleted, kept or
    gone; 1 when refused, or unconfirmed. The document carries every key, null
    where it does not apply."""
    setup(hosted)
    result = _delete_branch("--json")
    assert result.exit_code == code, result.output
    [document] = _lines(result.stdout)
    assert set(document) == _DELETION_KEYS
    assert document["schema_version"] == landing.SCHEMA_VERSION
    assert (document["pull_request"], document["expected"]) == (496, fake.HEAD)
    assert (document["outcome"], document["reason_kind"], document["tip"]) == (
        outcome,
        reason_kind,
        tip,
    )
    assert (document["branch"], document["merged_head"]) == ("fix/42-land-it", fake.HEAD)
    assert (document["reason"] is None) is (reason_kind is None)
    assert document["guard"]["cleared"] == "undetermined"


def test_an_unconfirmed_deletion_states_no_tip_and_exits_1(hosted: fake.HostingService) -> None:
    """Whether the branch was deleted is not known, so the document states no
    tip and no refusal, and the exit says the end state is not known."""
    _lost_answer_unread(hosted)
    result = _delete_branch("--json")
    assert result.exit_code == 1
    [document] = _lines(result.stdout)
    assert document == {
        "schema_version": 1,
        "pull_request": 496,
        "expected": fake.HEAD,
        "outcome": "unconfirmed",
        "branch": "fix/42-land-it",
        "tip": None,
        "reason_kind": "unanswered",
        "reason": "the deletion got no usable answer (HTTP 502: Bad Gateway), and the branch "
        "could not be read since (HTTP 502: Bad Gateway)",
        "merged_head": fake.HEAD,
        "guard": document["guard"],
    }


def test_a_head_other_than_the_merged_one_is_refused_with_both_named(
    hosted: fake.HostingService,
) -> None:
    other = fake.oid("other")
    result = _delete_branch("--json", expect=other)
    assert result.exit_code == 1
    [document] = _lines(result.stdout)
    assert (document["outcome"], document["reason_kind"]) == ("refused", "expect-mismatch")
    assert (document["expected"], document["merged_head"]) == (other, fake.HEAD)
    assert other in document["reason"] and fake.HEAD in document["reason"]
    assert hosted.kinds() == [fake.BRANCH]


def test_delete_branch_says_what_became_of_the_branch(hosted: fake.HostingService) -> None:
    result = _delete_branch()
    assert (result.exit_code, result.stdout) == (
        0,
        "PR #496: deleted remote branch 'fix/42-land-it'\n",
    )
    hosted.cross_repository = True
    refused = _delete_branch()
    assert refused.exit_code == 1
    assert refused.stderr.startswith("error: remote branch 'fix/42-land-it' not deleted: PR #496's")
    assert refused.stderr.endswith("Nothing was deleted.\n")


def test_delete_branch_says_when_whether_it_deleted_is_not_known(
    hosted: fake.HostingService,
) -> None:
    _lost_answer_unread(hosted)
    result = _delete_branch()
    assert result.exit_code == 1
    assert result.stderr.startswith(
        "error: whether remote branch 'fix/42-land-it' was deleted is not known: the deletion "
        "got no usable answer"
    )
    assert result.stderr.endswith("Run the command again: it reads the branch first.\n")


def test_a_gone_branch_is_said_not_there_whoever_removed_it(hosted: fake.HostingService) -> None:
    hosted.refs.pop(hosted.head_ref)
    result = _delete_branch()
    assert (result.exit_code, result.stdout) == (
        0,
        "PR #496: remote branch 'fix/42-land-it' is not there; nothing to delete\n",
    )


@pytest.mark.parametrize(
    "expect",
    [" ", "a1b2c3d", "a" * 39, "a" * 41, "z" * 40],
    ids=["blank", "abbreviated", "short", "long", "not-hex"],
)
def test_delete_branch_takes_a_full_commit_id(hosted: fake.HostingService, expect: str) -> None:
    """An abbreviated head would let a branch be deleted at a commit nobody
    named in full: anything but 40 or 64 hexadecimal characters is a usage
    error, and nothing is read or sent."""
    result = _delete_branch(expect=expect)
    assert result.exit_code == 2
    assert "is not a full commit id" in result.output
    assert hosted.requests == []


def test_delete_branch_takes_a_commit_id_in_any_case_and_states_it_lower_cased(
    hosted: fake.HostingService,
) -> None:
    result = _delete_branch("--json", expect=fake.HEAD.upper())
    assert result.exit_code == 0
    [document] = _lines(result.stdout)
    assert (document["outcome"], document["expected"]) == ("deleted", fake.HEAD)


def test_in_another_repository_with_no_terminal_the_deletion_is_refused_and_nothing_sent(
    hosted: fake.HostingService, foreign: Path
) -> None:
    """The guard runs before the reading: refused, nothing is asked of the
    service at all, and the document says why in the noun's terms."""
    result = _delete_branch("--json")
    assert result.exit_code == 1
    [document] = _lines(result.stdout)
    assert set(document) == _DELETION_KEYS
    assert (document["outcome"], document["reason_kind"]) == ("refused", "foreign-repository")
    assert (document["branch"], document["tip"], document["merged_head"]) == (None, None, None)
    assert (document["guard"]["verdict"], document["guard"]["cleared"]) == ("diverged", None)
    assert "--allow-foreign-repo" in document["reason"]
    assert hosted.requests == []
    assert hosted.head_ref in hosted.refs


def test_the_flag_confirms_a_deletion_in_another_repository(
    hosted: fake.HostingService, foreign: Path
) -> None:
    result = _delete_branch("--allow-foreign-repo", "--json")
    assert result.exit_code == 0
    [document] = _lines(result.stdout)
    assert document["outcome"] == "deleted"
    assert (document["guard"]["verdict"], document["guard"]["cleared"]) == ("diverged", "flag")


def test_with_no_anchor_the_deletion_needs_no_flag(hosted: fake.HostingService) -> None:
    """No anchor, no fire: outside any session the guard passes undetermined,
    never same-repo, and the deletion goes ahead."""
    result = _delete_branch("--json")
    assert result.exit_code == 0
    [document] = _lines(result.stdout)
    assert document["outcome"] == "deleted"
    assert document["guard"] == {
        "verdict": "undetermined",
        "undetermined_kind": "noncoverage",
        "anchor": None,
        "target": None,
        "cleared": "undetermined",
    }
