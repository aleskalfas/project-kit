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
import os
import subprocess
import sys
import time
from collections.abc import Callable, Sequence
from dataclasses import replace
from datetime import UTC, datetime
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


# The read of the repository's squash-commit defaults, and the convention's.
_DEFAULTS_READ = ["gh", "api", "repos/{owner}/{repo}"]
_CONVENTION = {"squash_merge_commit_title": "PR_TITLE", "squash_merge_commit_message": "PR_BODY"}


def _gh(
    answers: list[dict[str, Any]], calls: list[list[str]] | None = None
) -> Callable[[Sequence[str]], Completed]:
    """A `gh` answering each read with the next pull request of `answers`, the
    last one repeated once they run out, and the repository's squash-commit
    defaults with the convention's (:data:`_CONVENTION`), so a direct merge
    leaves the body to the service; any other command succeeds."""
    remaining = list(answers)

    def gh(argv: Sequence[str]) -> Completed:
        if calls is not None:
            calls.append(list(argv))
        if list(argv) == _DEFAULTS_READ:
            return _ok(argv, json.dumps(_CONVENTION))
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


@pytest.fixture(autouse=True)
def clock(monkeypatch: pytest.MonkeyPatch) -> fake.Clock:
    """The module's clock and sleep, which its settling readings run on: each
    sleep advances the clock, and none is slept."""
    ticking = fake.Clock()
    monkeypatch.setattr(landing, "_sleep", ticking.sleep)
    monkeypatch.setattr(landing, "_monotonic", ticking)
    return ticking


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
    assert outcome == landing.Outcome(True, 0, "", body=landing.BODY_COMPOSED)
    assert calls == [
        _DEFAULTS_READ,
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
        ],
    ]


def test_the_squash_merge_passes_admin_and_pins_nothing_without_a_head(
    here: dict[str, Any], acting: Callable[[landing.GhRunner], None]
) -> None:
    calls: list[list[str]] = []
    acting(_gh([_NO_QUEUE], calls))
    landing.squash_merge(42, subject="fix: x", admin=True, **here)
    assert calls == [
        _DEFAULTS_READ,
        ["gh", "pr", "merge", "42", "--squash", "--subject", "fix: x", "--admin"],
    ]


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


_HEAD_MODIFIED = (
    "GraphQL: Head branch was modified. Review and try the merge again. (mergePullRequest)"
)


def test_a_refused_request_carries_gh_s_reason(
    here: dict[str, Any], acting: Callable[[landing.GhRunner], None]
) -> None:
    def refusing(argv: Sequence[str]) -> Completed:
        if list(argv) == _DEFAULTS_READ:
            return _ok(argv, json.dumps(_CONVENTION))
        return subprocess.CompletedProcess(list(argv), 1, stdout="", stderr=f"{_HEAD_MODIFIED}\n")

    acting(refusing)
    assert landing.squash_merge(42, subject="x", **here) == landing.Outcome(
        False, 1, _HEAD_MODIFIED, body=landing.BODY_COMPOSED
    )


# --- the body of a direct merge (#1257) ----------------------------------------------

# A PR body as a caller's gates may judge it: a paragraph, an HTML comment and
# a co-author line of its own, which the service keeps in a body passed to it.
_BODY = (
    "Closes #42\n\nA paragraph.\n\n<!-- hidden -->\n\n"
    "Co-authored-by: Body Author <body@example.invalid>\n"
)


def _merge(here: dict[str, Any]) -> landing.Outcome:
    return landing.squash_merge(496, subject="fix: land it", head_oid=fake.HEAD, **here)


@pytest.mark.parametrize(
    ("defaults", "route", "asked"),
    [
        (("PR_TITLE", "PR_BODY"), landing.BODY_COMPOSED, [fake.DEFAULTS, fake.MERGE]),
        (
            ("PR_TITLE", "COMMIT_MESSAGES"),
            landing.BODY_PASSED,
            [fake.DEFAULTS, fake.BODY, fake.MERGE],
        ),
        (
            ("COMMIT_OR_PR_TITLE", "BLANK"),
            landing.BODY_PASSED,
            [fake.DEFAULTS, fake.BODY, fake.MERGE],
        ),
        (None, landing.BODY_PASSED, [fake.DEFAULTS, fake.BODY, fake.MERGE]),
    ],
    ids=["pr-body", "commit-messages", "blank", "unreadable"],
)
def test_a_direct_merge_lands_the_prs_title_and_body_by_the_route_that_loses_nothing(
    defaults: tuple[str, str] | None,
    route: str,
    asked: list[str],
    here: dict[str, Any],
    acting: Callable[[landing.GhRunner], None],
) -> None:
    """Where the default composes the PR's body, the service composes it —
    passing it could only lose what the service adds; under any other
    default, or one the account cannot read, the PR's body is read just
    before the merge and passed with it. Either way the commit is the PR's
    title and body (COR-009), and the outcome says which way the body went."""
    host = fake.HostingService(body=_BODY, squash_defaults=defaults)
    acting(_bounded(host))
    outcome = _merge(here)
    assert (outcome.accepted, outcome.body) == (True, route)
    assert host.kinds() == asked
    assert host.body_route() == route
    assert host.landed_message == f"fix: land it\n\n{_BODY}"


def test_a_body_passed_is_the_prs_body_byte_for_byte_and_nothing_more(
    here: dict[str, Any], acting: Callable[[landing.GhRunner], None]
) -> None:
    """The body passed is the PR's as read, its HTML comment and its own
    co-author line among it; the subject stays the caller's. The service adds
    no co-author trailer of the PR's commits to it, as it does after a body it
    composes from their messages — which, on this default, is what the merge
    would land without the body."""
    host = fake.HostingService(body=_BODY, squash_defaults=("PR_TITLE", "COMMIT_MESSAGES"))
    acting(_bounded(host))
    assert _merge(here).accepted
    [merge] = [request.argv for request in host.requests if request.kind == fake.MERGE]
    assert merge[merge.index("--body") + 1] == _BODY
    assert merge[merge.index("--subject") + 1] == "fix: land it"
    assert "Co-authored-by: Pair" not in host.landed_message


def test_an_empty_body_is_passed_as_empty(
    here: dict[str, Any], acting: Callable[[landing.GhRunner], None]
) -> None:
    """A PR with no description lands with none: its empty body is passed,
    not left to a default that composes something else."""
    host = fake.HostingService(body="", squash_defaults=("PR_TITLE", "COMMIT_MESSAGES"))
    acting(_bounded(host))
    assert _merge(here).body == landing.BODY_PASSED
    [merge] = [request.argv for request in host.requests if request.kind == fake.MERGE]
    assert merge[merge.index("--body") + 1] == ""
    assert host.landed_message == "fix: land it"


@pytest.mark.parametrize(
    "defaults",
    [("PR_TITLE", "PR_BODY"), ("PR_TITLE", "COMMIT_MESSAGES")],
    ids=["composed", "passed"],
)
def test_the_merge_carries_the_body_as_it_is_at_the_request_not_as_a_gate_read_it(
    defaults: tuple[str, str],
    here: dict[str, Any],
    acting: Callable[[landing.GhRunner], None],
) -> None:
    """The gap the reference names: a caller's gates judged the body as they
    read it; edited since, the merge carries the edited body — read just
    before the request, or composed by the service at the merge. No rule is
    made of a body that changed."""
    host = fake.HostingService(body="As the gates read it.\n", squash_defaults=defaults)
    host.before(fake.DEFAULTS, lambda service: setattr(service, "body", "Edited since.\n"))
    acting(_bounded(host))
    assert _merge(here).accepted
    assert host.landed_message == "fix: land it\n\nEdited since.\n"


def test_a_body_that_cannot_be_read_sends_no_merge(
    here: dict[str, Any], acting: Callable[[landing.GhRunner], None]
) -> None:
    """The body the merge is to carry cannot be read: no merge is sent — not
    accepted, `unreadable`, no exit code of gh's, no route taken."""
    host = fake.HostingService(squash_defaults=("PR_TITLE", "COMMIT_MESSAGES"))
    host.fail(fake.BODY)
    acting(_bounded(host))
    outcome = _merge(here)
    assert outcome == landing.Outcome(
        False,
        None,
        "the body of PR #496, which the merge is to carry, could not be read just before it, "
        "so no merge was sent: HTTP 502: Bad Gateway",
        landing.NOT_READ,
    )
    assert host.kinds() == [fake.DEFAULTS, fake.BODY]


def test_defaults_that_cannot_be_read_pass_the_body(
    here: dict[str, Any], acting: Callable[[landing.GhRunner], None]
) -> None:
    """A reading of the defaults that fails is no default that composes the
    PR's body: the body is passed, so the commit carries it whatever the
    default is."""
    host = fake.HostingService(body=_BODY, squash_defaults=("PR_TITLE", "COMMIT_MESSAGES"))
    host.fail(fake.DEFAULTS)
    acting(_bounded(host))
    assert _merge(here).body == landing.BODY_PASSED
    assert host.landed_message == f"fix: land it\n\n{_BODY}"


def test_the_merges_longest_run_counts_its_readings_before_the_request() -> None:
    """The defaults and the body, one `gh` call each at its bound, come before
    the merge and nowhere before an enqueue."""
    one_call = landing.GH_READ_SECONDS + command_runner.END_GRACE_SECONDS
    assert landing.longest_seconds("merge") == landing.longest_seconds("enqueue") + 2 * one_call


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
    auto-merge still holds has the auto-merge cancelled. Out is confirmed by
    two readings running, the second no sooner than the window after the
    request, as for any request whose end state is an absence."""
    calls: list[list[str]] = []
    acting(_gh([before, _OUT], calls))
    outcome = landing.dequeue(42, **here)
    assert outcome == landing.Outcome(True, 0)
    taken = calls[1]
    assert taken[1 : 1 + len(command)] == command
    if command[0] == "api":
        assert "dequeuePullRequest" in taken[4] and taken[-1] == "id=PR_node"
    assert len(calls) == 4


def test_a_dequeue_that_does_not_take_says_so(
    here: dict[str, Any], acting: Callable[[landing.GhRunner], None]
) -> None:
    """The service accepted the dequeue, and the PR still reads queued on the
    second reading: not taken out, saying what the readings saw."""
    acting(_gh([_QUEUED, _QUEUED]))
    outcome = landing.dequeue(42, **here)
    assert (outcome.accepted, outcome.exit_code, outcome.reason_kind) == (False, 0, "")
    assert outcome.reason == (
        "the service accepted the dequeue of PR #42, and it was not seen out of the merge queue "
        "on two readings 40 s apart, the second 40 s after it was sent: PR #42 reads queued "
        "(position 2 in the queue, awaiting checks, about 4 min to merge)"
    )


def test_a_pr_out_of_the_queue_needs_no_dequeue(
    here: dict[str, Any], acting: Callable[[landing.GhRunner], None], clock: fake.Clock
) -> None:
    """Out of the queue on two readings running, the interval apart: already
    out, and nothing is sent."""
    calls: list[list[str]] = []
    acting(_gh([_OUT], calls))
    assert landing.dequeue(42, **here) == landing.Outcome(True, None)
    assert len(calls) == 2
    assert clock.sleeps == [landing.SETTLE_INTERVAL_SECONDS]


def test_a_pr_read_out_of_the_queue_once_and_queued_after_is_taken_out(
    here: dict[str, Any], acting: Callable[[landing.GhRunner], None]
) -> None:
    """One reading out of the queue is not that it is out — the queue may be
    taking it in, or merging it: queued on the second, it is taken out."""
    calls: list[list[str]] = []
    acting(_gh([_OUT, _QUEUED, _OUT], calls))
    assert landing.dequeue(42, **here).accepted
    assert "dequeuePullRequest" in _query(calls[2])


def test_a_merged_pr_cannot_be_dequeued(
    here: dict[str, Any], acting: Callable[[landing.GhRunner], None]
) -> None:
    acting(_gh([_MERGED]))
    outcome = landing.dequeue(42, **here)
    assert (outcome.accepted, outcome.reason_kind) == (False, landing.HAS_MERGED)
    assert outcome.reason == (
        "PR #42 has merged at head sha-hea (merged at 2026-10-01T10:12:00Z), which no dequeue "
        "undoes"
    )


def test_an_answered_dequeue_whose_pr_cannot_be_read_since_is_unconfirmed(
    here: dict[str, Any], acting: Callable[[landing.GhRunner], None]
) -> None:
    """The service accepted the dequeue, and no reading since can show the PR
    out: more evidence than an unanswered one, so never reported as failed —
    unconfirmed, `unreadable`, with gh's exit."""
    answered = _gh([_QUEUED])

    def unreadable_after_the_dequeue(argv: Sequence[str]) -> Completed:
        if calls and "dequeuePullRequest" in _query(calls[-1]):
            return subprocess.CompletedProcess(list(argv), 1, stdout="", stderr="HTTP 502")
        calls.append(list(argv))
        return answered(argv)

    calls: list[list[str]] = []
    acting(unreadable_after_the_dequeue)
    outcome = landing.dequeue(42, **here)
    assert (outcome.accepted, outcome.exit_code, outcome.reason_kind) == (
        None,
        0,
        landing.NOT_READ,
    )
    assert outcome.reason == (
        "the service accepted the dequeue of PR #42, and PR #42 could not be read since to see "
        "it out of the merge queue (HTTP 502): whether it left the queue is not known"
    )


@pytest.mark.parametrize(
    ("readings", "accepted", "count"),
    [
        ([_QUEUED, _QUEUED, _OUT, _OUT], True, 3),
        ([_QUEUED, _QUEUED, _OUT, _QUEUED], False, 3),
        ([_QUEUED, _OUT, _QUEUED], False, 2),
    ],
    ids=["queued-out-out", "queued-out-queued", "out-queued"],
)
def test_out_of_the_queue_rests_on_two_readings_running_and_no_more_than_its_most(
    readings: list[dict[str, Any]],
    accepted: bool,
    count: int,
    here: dict[str, Any],
    acting: Callable[[landing.GhRunner], None],
) -> None:
    """Read queued, then out: one reading out is not enough, so a third
    decides. The longest sequence takes as many readings as the module says a
    dequeue's settling can (`most_readings`) — the figure its bound counts."""
    calls: list[list[str]] = []
    acting(_gh(readings, calls))
    assert landing.dequeue(42, **here).accepted is accepted
    settling = len(calls) - 2  # the reading first, and the request
    assert settling == count <= landing._DEQUEUING.most_readings


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
def slept(clock: fake.Clock) -> list[float]:
    """The module's sleeps, recorded and never slept."""
    return clock.sleeps


def _queue(host: fake.HostingService) -> fake.HostingService:
    host.set_base(fake.Base(queue=True))
    return host


def _ask(request_: str, here: dict[str, Any]) -> landing.Outcome:
    """Make the request on the shared fake, whose defaults compose the PR's
    body: a merge leaves its body to the service, which these tests of what a
    request came to then set aside."""
    if request_ == "merge":
        outcome = landing.squash_merge(496, subject="fix: land it", head_oid=fake.HEAD, **here)
        assert outcome.body == landing.BODY_COMPOSED
        return replace(outcome, body="")
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
    asked = [fake.ENQUEUE] if request_ == "enqueue" else [fake.DEFAULTS, fake.MERGE]
    assert host.kinds() == [*asked, fake.READ]
    assert slept == []


def test_a_request_the_service_was_still_making_shows_in_the_second_reading(
    here: dict[str, Any], acting: Callable[[landing.GhRunner], None], slept: list[float]
) -> None:
    host = fake.HostingService()
    host.never_receive(fake.MERGE)
    host.after(fake.READ, lambda service: service.merge_now())
    acting(_bounded(host))
    assert _ask("merge", here) == landing.Outcome(True, None)
    assert host.kinds() == [fake.DEFAULTS, fake.MERGE, fake.READ, fake.READ]
    assert slept == [landing.SETTLE_WINDOW_SECONDS]


@pytest.mark.parametrize(
    ("request_", "setup", "found"),
    [
        ("merge", lambda host: host, "neither merged nor queued (not in the queue)"),
        ("enqueue", _queue, "neither queued nor merged (not in the queue)"),
    ],
)
def test_a_request_with_no_answer_read_short_of_its_end_twice_was_not_seen_made(
    request_: str,
    setup: Callable[[fake.HostingService], Any],
    found: str,
    here: dict[str, Any],
    acting: Callable[[landing.GhRunner], None],
    slept: list[float],
) -> None:
    """Never received, nothing back: two readings, the second the window after
    the request, find its end state not reached — only then is it not seen
    made (ADR-061 point 7), not accepted with `reason_kind` `not-made`, and no
    exit code of gh's. The reason says what the readings saw, never that the
    request was not made."""
    host = fake.HostingService()
    setup(host)
    kind = {"merge": fake.MERGE, "enqueue": fake.ENQUEUE}[request_]
    host.never_receive(kind)
    acting(_bounded(host))
    outcome = _ask(request_, here)
    assert (outcome.accepted, outcome.exit_code, outcome.reason_kind) == (
        False,
        None,
        landing.NOT_MADE,
    )
    assert outcome.reason == (
        f"the {request_} of PR #496 got no usable answer ({_ENDED_AT_ITS_BOUND}), and was not "
        f"seen made on two readings 40 s apart, the second 40 s after it was sent: PR #496 "
        f"reads {found}"
    )
    assert "was not made" not in outcome.reason
    assert host.kinds()[-3:] == [kind, fake.READ, fake.READ]
    assert slept == [landing.SETTLE_WINDOW_SECONDS]


def _ends_at_its_bound(
    host: fake.HostingService, clock: fake.Clock, *, request: float, first_reading: float = 0.0
) -> landing.GhRunner:
    """`host` through the bounded start, on `clock`: the merge never answers
    and is ended after `request` seconds; the first reading after it takes
    `first_reading` seconds. What is read before the merge takes no time."""
    read_after: list[float] = []

    def run(argv: Sequence[str]) -> Completed:
        if list(argv[:3]) == ["gh", "pr", "merge"]:
            clock.now += request
            read_after.append(first_reading)
            raise subprocess.TimeoutExpired(list(argv), request)
        clock.now += read_after.pop() if read_after else 0.0
        return host(argv)

    return run


@pytest.mark.parametrize(
    ("request_seconds", "first_reading", "sleeps"),
    [
        (0.0, 0.0, [40.0]),
        (32.0, 0.0, [10.0]),
        (32.0, 5.0, [10.0]),
        (1.0, 3.0, [36.0]),
    ],
    ids=["back-at-once", "ended-at-its-bound", "a-slow-first-reading", "a-fast-failure"],
)
def test_every_unanswered_request_gets_the_same_window_before_its_second_reading(
    request_seconds: float,
    first_reading: float,
    sleeps: list[float],
    here: dict[str, Any],
    acting: Callable[[landing.GhRunner], None],
    clock: fake.Clock,
) -> None:
    """However the answer went missing — a server error back at once, or a
    request ended at its bound — the second reading is taken no sooner than
    the window after the request was sent, and the interval after the first
    reading: a late merge has the same time to show on every path."""
    host = fake.HostingService()
    seen_at: list[float] = []
    host.after(fake.READ, lambda service: seen_at.append(clock.now), nth=1)
    host.after(fake.READ, lambda service: seen_at.append(clock.now), nth=2)
    acting(_ends_at_its_bound(host, clock, request=request_seconds, first_reading=first_reading))
    outcome = _ask("merge", here)
    assert outcome.reason_kind == landing.NOT_MADE
    assert clock.sleeps == sleeps
    first, second = seen_at
    assert second >= landing.SETTLE_WINDOW_SECONDS
    assert second - first >= landing.SETTLE_INTERVAL_SECONDS


def test_a_request_dropped_by_the_queue_since_it_was_sent_was_made(
    here: dict[str, Any],
    acting: Callable[[landing.GhRunner], None],
    monkeypatch: pytest.MonkeyPatch,
    slept: list[float],
) -> None:
    """The enqueue was made and its answer lost, and the queue dropped the PR
    before it was read: the reading's drop, dated after the request was sent,
    is the request made — the caller sees the drop as any reading shows it."""
    host = _queue(fake.HostingService())
    host.lose_reply(fake.ENQUEUE)
    host.after(fake.ENQUEUE, lambda service: service.drop("failed checks"))
    monkeypatch.setattr(landing, "_utcnow", lambda: datetime(2026, 10, 1, 10, 4, tzinfo=UTC))
    acting(_bounded(host))
    assert _ask("enqueue", here) == landing.Outcome(True, None)
    assert host.kinds() == [fake.ENQUEUE, fake.READ]
    assert slept == []


def test_a_drop_dated_before_the_request_was_sent_is_not_the_request_made(
    here: dict[str, Any],
    acting: Callable[[landing.GhRunner], None],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A drop from before the request — a head enqueued again with `--force`
    — tells nothing of this request: two readings decide, as without one."""
    host = _queue(fake.HostingService())
    host.dropped_before()
    host.never_receive(fake.ENQUEUE)
    monkeypatch.setattr(landing, "_utcnow", lambda: datetime(2026, 10, 1, 10, 6, tzinfo=UTC))
    acting(_bounded(host))
    outcome = _ask("enqueue", here)
    assert outcome.reason_kind == landing.NOT_MADE


def test_settling_says_on_standard_error_that_a_request_is_in_flight(
    here: dict[str, Any],
    acting: Callable[[landing.GhRunner], None],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """As settling starts, one line on standard error says what was asked,
    that no usable answer came, that the PR is being read, and for how long
    at most — a `[warn]` line, which project-management passes on as it comes."""
    host = fake.HostingService()
    host.never_receive(fake.MERGE)
    acting(_bounded(host))
    _ask("merge", here)
    longest = landing._settling_longest(landing._MERGING, 0.0)
    assert capsys.readouterr().err == (
        f"[warn] the merge of PR #496 got no usable answer ({_ENDED_AT_ITS_BOUND}): reading "
        f"where PR #496 stands to tell whether it was made — the second reading no sooner "
        f"than 40 s after it was sent, up to {longest:.0f} s in all\n"
    )


def test_a_request_answered_or_refused_says_nothing_on_standard_error(
    here: dict[str, Any],
    acting: Callable[[landing.GhRunner], None],
    capsys: pytest.CaptureFixture[str],
) -> None:
    host = fake.HostingService()
    host.fail(fake.MERGE, stderr=_HEAD_MODIFIED)
    acting(_bounded(host))
    _ask("merge", here)
    assert capsys.readouterr().err == ""


def test_a_dequeue_not_seen_made_is_sent_once_more_and_says_so(
    here: dict[str, Any], acting: Callable[[landing.GhRunner], None]
) -> None:
    """Taking a PR whose head moved out of the queue is what keeps commits
    nothing checked from merging: a dequeue not seen made is sent once more,
    and the reason says so, whatever the second came to."""
    host = _queue(fake.HostingService())
    host.enter_queue()
    host.never_receive(fake.DEQUEUE)
    acting(_bounded(host))
    outcome = _ask("dequeue", here)
    assert outcome == landing.Outcome(
        True,
        0,
        f"the dequeue of PR #496 got no usable answer ({_ENDED_AT_ITS_BOUND}), and was not seen "
        "made on two readings 40 s apart, the second 40 s after it was sent: PR #496 reads "
        "queued (in the queue); it was sent once more: two readings since show the PR out of "
        "the merge queue",
    )
    assert host.kinds() == [
        fake.READ,
        fake.DEQUEUE,
        fake.READ,
        fake.READ,
        fake.DEQUEUE,
        fake.READ,
        fake.READ,
    ]
    assert not host.in_queue


def test_a_dequeue_not_seen_made_twice_is_not_seen_made_naming_both(
    here: dict[str, Any], acting: Callable[[landing.GhRunner], None]
) -> None:
    host = _queue(fake.HostingService())
    host.enter_queue()
    host.never_receive(fake.DEQUEUE)
    host.after(fake.READ, lambda service: service.never_receive(fake.DEQUEUE), nth=3)
    acting(_bounded(host))
    outcome = _ask("dequeue", here)
    assert (outcome.accepted, outcome.exit_code, outcome.reason_kind) == (
        False,
        None,
        landing.NOT_MADE,
    )
    first, _, second = outcome.reason.partition("; it was sent once more: ")
    assert first.startswith("the dequeue of PR #496 got no usable answer")
    assert second.startswith("the dequeue of PR #496 got no usable answer")
    assert host.kinds().count(fake.DEQUEUE) == landing.DEQUEUE_ATTEMPTS


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
        f"the {request_} of PR #496 got no usable answer ({_ENDED_AT_ITS_BOUND}), and PR #496 "
        f"could not be read since (HTTP 502: Bad Gateway): whether the {request_} was made is "
        "not known"
    )
    assert slept == [landing.SETTLE_WINDOW_SECONDS] * readable


def test_a_dequeue_with_no_answer_that_reads_merged_since_was_not_accepted(
    here: dict[str, Any], acting: Callable[[landing.GhRunner], None], slept: list[float]
) -> None:
    """The queue merged the PR while it was being taken out: no dequeue undoes
    that, so it is not accepted, `merged`, saying at which head — not a
    request that was not seen made, and not sent again."""
    host = _queue(fake.HostingService())
    host.enter_queue()
    host.never_receive(fake.DEQUEUE)
    host.before(fake.READ, lambda service: service.merge_now(), nth=2)
    acting(_bounded(host))
    outcome = _ask("dequeue", here)
    assert (outcome.accepted, outcome.reason_kind) == (False, landing.HAS_MERGED)
    assert outcome.reason.startswith(f"PR #496 has merged at head {fake.HEAD[:7]} (merged at ")
    assert host.kinds().count(fake.DEQUEUE) == 1


# What gh prints when the service, or gh itself before it sent anything,
# answered the request: the shapes the module recognises as an answer.
_ANSWERED = [
    "GraphQL: Head branch was modified. Review and try the merge again. (mergePullRequest)",
    "GraphQL: Pull request is not mergeable (mergePullRequest)",
    "HTTP 403: Resource not accessible by integration (https://api.github.com/graphql)",
    "gh: Validation Failed (HTTP 422)",
    "X Pull request #496 is not mergeable: the base branch policy prohibits the merge.",
    "! Pull request #496 is already queued to merge",
]

# What gh prints when the request's answer went missing on the way: no
# answer, whatever the request came to.
_TRANSPORT = [
    'Post "https://api.github.com/graphql": http2: client connection lost',
    'Post "https://api.github.com/graphql": read tcp 10.0.0.2:51234->140.82.112.6:443: '
    "read: operation timed out",
    'Post "https://api.github.com/graphql": net/http: timeout awaiting response headers',
    'Post "https://api.github.com/graphql": http2: Transport: cannot retry err [http2: '
    "Transport received Server's graceful shutdown GOAWAY] after Request.Body was written; "
    "transport connection broken",
    'Post "https://api.github.com/graphql": write tcp 10.0.0.2:51234->140.82.112.6:443: use '
    "of closed network connection",
    "unexpected end of JSON input",
    "HTTP 502: Bad Gateway (https://api.github.com/graphql)",
    "",
]


@pytest.mark.parametrize("stderr", _ANSWERED)
def test_a_request_the_service_answered_with_an_error_is_refused_in_its_words_unread(
    stderr: str,
    here: dict[str, Any],
    acting: Callable[[landing.GhRunner], None],
    slept: list[float],
) -> None:
    """An answer the module recognises said no: a refusal with its words —
    never taken for a request with no answer, and nothing is read."""
    host = fake.HostingService()
    host.fail(fake.MERGE, stderr=stderr)
    acting(_bounded(host))
    assert _ask("merge", here) == landing.Outcome(False, 1, stderr)
    assert host.kinds() == [fake.DEFAULTS, fake.MERGE]
    assert slept == []


@pytest.mark.parametrize("stderr", _TRANSPORT)
def test_words_the_module_does_not_recognise_as_an_answer_are_settled_by_reading(
    stderr: str,
    here: dict[str, Any],
    acting: Callable[[landing.GhRunner], None],
) -> None:
    """Refused only on a recognised answer: any other failure — a transport
    error the module has never seen among them — is no usable answer, and the
    request is settled by reading. Not seen made, the reason carries gh's
    words, so a refusal misread as no answer still ends not accepted, in
    them."""
    host = fake.HostingService()
    host.fail(fake.MERGE, stderr=stderr)
    acting(_bounded(host))
    outcome = _ask("merge", here)
    assert (outcome.accepted, outcome.exit_code, outcome.reason_kind) == (
        False,
        None,
        landing.NOT_MADE,
    )
    assert outcome.reason.startswith(
        f"the merge of PR #496 got no usable answer ({stderr or 'gh answered nothing'})"
    )
    assert host.kinds() == [fake.DEFAULTS, fake.MERGE, fake.READ, fake.READ]


def test_an_unrecognised_refusal_still_ends_not_accepted_in_gh_s_words(
    here: dict[str, Any], acting: Callable[[landing.GhRunner], None]
) -> None:
    """A refusal in words the module does not know costs two readings, and
    ends as a refusal would: not accepted, gh's words in the reason."""
    host = fake.HostingService()
    host.fail(fake.MERGE, stderr="Pull request is in clean status")
    acting(_bounded(host))
    outcome = _ask("merge", here)
    assert outcome.accepted is False
    assert "(Pull request is in clean status)" in outcome.reason


@pytest.mark.parametrize("request_", ["merge", "dequeue"])
def test_gh_ended_by_a_signal_is_no_answer_whatever_it_printed(
    request_: str, here: dict[str, Any], acting: Callable[[landing.GhRunner], None]
) -> None:
    """A negative exit is a `gh` ended by a signal: no usable answer,
    whatever its words — even a refusal's — so the request is read."""
    host = _queue(fake.HostingService()) if request_ == "dequeue" else fake.HostingService()
    if request_ == "dequeue":
        host.enter_queue()

    def signalled(argv: Sequence[str]) -> Completed:
        args = list(argv)
        if args[:3] == ["gh", "pr", "merge"] or "dequeuePullRequest" in _query(args):
            host.requests.append(fake.Request("signalled", args))
            return subprocess.CompletedProcess(args, -15, stdout="", stderr=_HEAD_MODIFIED)
        return host(argv)

    acting(signalled)
    outcome = _ask(request_, here)
    assert outcome.reason_kind == landing.NOT_MADE
    assert f"(`gh` was ended by signal 15: {_HEAD_MODIFIED})" in outcome.reason
    assert host.seen(fake.READ) >= 2


def test_a_deletion_whose_gh_was_ended_by_a_signal_reads_the_branch_again(
    here: dict[str, Any], acting: Callable[[landing.GhRunner], None]
) -> None:
    """The one classifier answers for every request, the deletion's too: a
    signal is no usable answer, and the branch is read again."""
    host = _merged_host()

    def signalled(argv: Sequence[str]) -> Completed:
        if "updateRefs" in _query(argv):
            return subprocess.CompletedProcess(list(argv), -9, stdout="", stderr="")
        return host(argv)

    acting(signalled)
    deletion = landing.delete_branch(496, expect=fake.HEAD, **here)
    assert (deletion.outcome, deletion.reason_kind) == ("kept", "unanswered")
    assert deletion.reason.startswith("the deletion got no usable answer (`gh` was ended by signal")
    assert host.kinds() == [fake.BRANCH, fake.BASED_ON, fake.BRANCH]


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
    assert host.kinds() == [fake.READ, fake.DEQUEUE, fake.READ, fake.READ, fake.READ]
    assert started == [
        (where, read),
        (where, request),
        (where, read),
        (where, read),
        (None, read),
    ]


# A stand-in `gh` on PATH: it never answers `gh pr merge` — it writes its pid
# and sleeps — and answers every reading with the PR open on a base without a
# queue.
_HANGING_GH = """\
import json, os, sys, time
if sys.argv[1:3] == ["pr", "merge"]:
    with open(os.environ["FAKE_GH_PIDFILE"], "w", encoding="utf-8") as out:
        out.write(str(os.getpid()))
    time.sleep(60)
    sys.exit(0)
if sys.argv[1:3] == ["api", "repos/{owner}/{repo}"]:
    print(json.dumps({"squash_merge_commit_title": "PR_TITLE",
                      "squash_merge_commit_message": "PR_BODY"}))
    sys.exit(0)
print(json.dumps({"data": {"repository": {"pullRequest": json.loads(%r)}}}))
"""


def test_a_gh_that_never_answers_is_ended_at_its_bound_and_the_request_read_since(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, here: dict[str, Any]
) -> None:
    """End to end on real processes: the module's own `gh` (`_Gh`), the
    command runner's bounded start, the classifier and the settling, on a
    stand-in `gh` that never answers the merge — with small bounds, so no
    test waits out a real one. The `gh` is ended at its bound and is gone;
    the merge is read since, and not seen made."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    gh = bin_dir / "gh"
    gh.write_text(f"#!{sys.executable}\n{_HANGING_GH % json.dumps(_NO_QUEUE)}", encoding="utf-8")
    gh.chmod(0o755)
    pidfile = tmp_path / "gh.pid"
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}")
    monkeypatch.setenv("FAKE_GH_PIDFILE", str(pidfile))
    monkeypatch.setattr(landing, "GH_REQUEST_SECONDS", 1.0)
    monkeypatch.setattr(landing, "GH_READ_SECONDS", 20.0)
    monkeypatch.setattr(command_runner, "END_GRACE_SECONDS", 0.5)
    started = time.monotonic()
    outcome = landing.squash_merge(496, subject="fix: land it", **here)
    assert time.monotonic() - started < 30
    assert (outcome.accepted, outcome.reason_kind) == (False, landing.NOT_MADE)
    assert outcome.reason.startswith(
        "the merge of PR #496 got no usable answer (`gh` did not answer within 1 s, and was "
        "ended), and was not seen made on two readings"
    )
    pid = int(pidfile.read_text(encoding="utf-8"))
    with pytest.raises(ProcessLookupError):
        os.kill(pid, 0)


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
    refusal = "GraphQL: Pull request is not mergeable (mergePullRequest)"

    def refusing(argv: Sequence[str]) -> Completed:
        if list(argv) == _DEFAULTS_READ:
            return _ok(argv, json.dumps(_CONVENTION))
        return subprocess.CompletedProcess(list(argv), 1, stdout="", stderr=refusal)

    monkeypatch.setattr(landing, "gh_runner", lambda cwd: refusing)
    result = _invoke("merge", "42", "--subject", "fix: x", "--json")
    assert result.exit_code == 1
    [document] = _lines(result.stdout)
    assert document["reason"] == refusal and document["reason_kind"] is None
    assert document["body"] == landing.BODY_COMPOSED


@pytest.mark.parametrize(
    ("message", "body"),
    [("PR_BODY", "composed"), ("COMMIT_MESSAGES", "passed")],
)
def test_merge_writes_which_way_the_body_went(
    monkeypatch: pytest.MonkeyPatch, message: str, body: str
) -> None:
    """`body` is additive to the request's document, on `merge` alone: the
    other requests' documents do not carry it."""
    host = fake.HostingService(squash_defaults=("PR_TITLE", message))
    monkeypatch.setattr(landing, "gh_runner", lambda cwd: _bounded(host))
    result = _invoke("merge", "496", "--subject", "fix: land it", "--json")
    assert result.exit_code == 0
    [document] = _lines(result.stdout)
    assert (document["accepted"], document["body"]) == (True, body)


def test_merge_whose_body_cannot_be_read_writes_it_unsent_and_exits_1(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    host = fake.HostingService(squash_defaults=("PR_TITLE", "BLANK"))
    host.fail(fake.BODY)
    monkeypatch.setattr(landing, "gh_runner", lambda cwd: _bounded(host))
    result = _invoke("merge", "496", "--subject", "fix: land it", "--json")
    assert result.exit_code == 1
    [document] = _lines(result.stdout)
    assert (document["accepted"], document["exit_code"], document["reason_kind"]) == (
        False,
        None,
        "unreadable",
    )
    assert document["body"] is None
    assert fake.MERGE not in host.kinds()


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
        "body",
    }
    assert document["body"] == landing.BODY_COMPOSED


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
    warned, said = unknown.stderr.splitlines()
    assert warned.startswith("[warn] the merge of PR #496 got no usable answer")
    assert said == (
        f"error: the merge of PR #496 got no usable answer ({_ENDED_AT_ITS_BOUND}), and PR #496 "
        "could not be read since (HTTP 502: Bad Gateway): whether the merge was made is not "
        "known. Read where PR #496 stands: `pkit pull-request read 496`."
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
    # A merge's document says no body went: no merge was sent. `body` is the
    # merge's alone.
    if args[0] == "merge":
        assert document["body"] is None
    else:
        assert "body" not in document


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
