"""Tests for the landing sequence — `pull_request_landing.land` (#1258;
ADR-061 points 5, 7 and 8).

The state-by-option table, cell by cell, through the shared fake of the hosting
service (`tests.hosting_fake`), as a landing and as its dry run; the one
refusal order and the two stops no option lifts; each way the wait ends, and
each way a request with no usable answer settles, for the merge and the
enqueue; a head that moved before any request and during the wait, with each
thing taking the PR out of the queue came to; the events; the end document —
every key in every one, decoded strictly by its `ended` — and its bound.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from project_kit import pull_request_landing as landing
from project_kit import session_guard
from tests import hosting_fake as fake

Completed = subprocess.CompletedProcess[str]

PR = 496
HEAD = fake.HEAD
PUSHED = fake.oid("pushed")
OTHER = fake.oid("other")


@pytest.fixture(autouse=True)
def clock(monkeypatch: pytest.MonkeyPatch) -> fake.Clock:
    """The module's clock and sleep: each sleep advances the clock, and none
    is slept."""
    ticking = fake.Clock()
    monkeypatch.setattr(landing, "_sleep", ticking.sleep)
    monkeypatch.setattr(landing, "_monotonic", ticking)
    return ticking


@pytest.fixture
def here(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Where the landing runs, and the guard's clearance for it — outside any
    session, so it passes undetermined."""
    monkeypatch.delenv(session_guard.CLAUDE_CODE_ANCHOR, raising=False)
    cleared = session_guard.clear(tmp_path, confirmed=False, interactive=False)
    assert isinstance(cleared, session_guard.Clearance)
    return {"cwd": tmp_path, "clearance": cleared}


@pytest.fixture
def host(monkeypatch: pytest.MonkeyPatch) -> fake.HostingService:
    """The hosting service every `gh` of the landing reaches, as through the
    bounded start: a request it never answers is ended at its bound."""
    service = fake.HostingService()
    monkeypatch.setattr(landing, "gh_runner", lambda cwd: _bounded(service))
    monkeypatch.setattr(landing, "run_gh", _bounded(service))
    return service


def _bounded(service: fake.HostingService) -> landing.GhRunner:
    def run(argv: Sequence[str]) -> Completed:
        try:
            return service(argv)
        except fake.NoAnswer:
            raise subprocess.TimeoutExpired(list(argv), landing.GH_REQUEST_SECONDS) from None

    return run


def _land(
    here: dict[str, Any],
    *,
    dry_run: bool = False,
    events: list[dict[str, Any]] | None = None,
    **options: Any,
) -> landing.Landing:
    return landing.land(
        PR,
        head=HEAD,
        subject="fix: land it",
        options=landing.LandOptions(**options),
        dry_run=dry_run,
        on_event=events.append if events is not None else None,
        **here,
    )


def _requests(service: fake.HostingService) -> str:
    return " ".join(service.landing())


def _fail_every_read(service: fake.HostingService) -> None:
    service.fail(fake.READ, count=None)


def _queue(service: fake.HostingService, *, method: str = "SQUASH") -> None:
    service.set_base(fake.Base(queue=True, method=method))


# ---- the state-by-option table, cell by cell -----------------------------------


@dataclass(frozen=True)
class Cell:
    """What a landing came to in one cell of the table, and what its dry run
    came to: `ended`, with `(reason_kind)` and `→would` where it has them,
    then the landing's requests in order."""

    run: str
    plan: str


def _same(run: str, plan: str | None = None) -> dict[str, Cell]:
    """A row whose every option ends alike."""
    cell = Cell(run, plan if plan is not None else run)
    return {column: cell for column in _COLUMNS}


def _unreadable(service: fake.HostingService) -> None:
    _fail_every_read(service)


def _merged_at_the_head(service: fake.HostingService) -> None:
    service.merge_now()


def _merged_at_another_head(service: fake.HostingService) -> None:
    service.merge_now(head=OTHER)


def _closed(service: fake.HostingService) -> None:
    service.close()


def _queued_at_another_head(service: fake.HostingService) -> None:
    _queue(service)
    service.enter_queue()
    service.push(PUSHED)


def _held_at_another_head_without_a_queue(service: fake.HostingService) -> None:
    service.auto_merge = True
    service.push(PUSHED)


def _open_at_another_head(service: fake.HostingService) -> None:
    service.push(PUSHED)


def _queued_at_the_head(service: fake.HostingService) -> None:
    _queue(service)
    service.enter_queue()
    service.entry = (1, "MERGEABLE")
    service.progress = [fake.at(1, "MERGEABLE"), fake.lands()]


def _dropped_at_the_head(service: fake.HostingService) -> None:
    _queue(service)
    service.dropped_before()
    service.progress = [fake.at(1), fake.lands()]


def _open_on_a_queue(service: fake.HostingService) -> None:
    _queue(service)
    service.progress = [fake.at(1), fake.lands()]


def _open_without_a_queue(service: fake.HostingService) -> None:
    """The fake's default: a base without a queue."""


def _held_at_the_head_without_a_queue(service: fake.HostingService) -> None:
    """Auto-merge holds the PR at the checked head on a base with no queue:
    the direct row (#1258's definition), not the wait."""
    service.auto_merge = True
    service.progress = [fake.unchanged(), fake.unchanged()]


def _no_option(service: fake.HostingService) -> dict[str, Any]:
    return {}


def _admin(service: fake.HostingService) -> dict[str, Any]:
    return {"admin": True}


def _direct_only(service: fake.HostingService) -> dict[str, Any]:
    return {"direct_only": True}


def _bad_shape(service: fake.HostingService) -> None:
    """A queue that would not make the squash commit — it merges by MERGE —
    where the base has one; repository defaults that are not the convention
    where it has none, which nothing reads there."""
    rules = service.bases[service.base]
    service.bases[service.base] = fake.Base(queue=rules.queue, method="MERGE")
    service.squash_defaults = ("COMMIT_OR_PR_TITLE", "COMMIT_MESSAGES")


def _bad_shape_refused(service: fake.HostingService) -> dict[str, Any]:
    _bad_shape(service)
    return {"queued_bad_shape": landing.SHAPE_REFUSE}


def _bad_shape_warned(service: fake.HostingService) -> dict[str, Any]:
    _bad_shape(service)
    return {"queued_bad_shape": landing.SHAPE_WARN}


def _allow_dropped_head(service: fake.HostingService) -> dict[str, Any]:
    return {"allow_dropped_head": True}


_COLUMNS: dict[str, Callable[[fake.HostingService], dict[str, Any]]] = {
    "no-option": _no_option,
    "admin": _admin,
    "direct-only": _direct_only,
    "shape-bad-refuse": _bad_shape_refused,
    "shape-bad-warn": _bad_shape_warned,
    "allow-dropped-head": _allow_dropped_head,
}

_DEQUEUED = "head-moved: read read dequeue read read"
_WAITED = "merged: read defaults read"
_ENQUEUED = "merged: read defaults enqueue read read"
_MERGED = "merged: read merge read"
_ADMIN_MERGED = "merged: read merge-admin read"

#: The table (`spec-1220.md`, "The command", with #1258's addendum C): each
#: row a PR's state at the reading, each column the caller's options.
TABLE: dict[str, tuple[Callable[[fake.HostingService], None], dict[str, Cell]]] = {
    "unreadable": (_unreadable, _same("unreadable: read")),
    "merged-at-the-head": (_merged_at_the_head, _same("merged: read")),
    "merged-at-another-head": (_merged_at_another_head, _same("merged-at-another-head: read")),
    "closed": (_closed, _same("closed: read")),
    "queued-at-another-head": (
        _queued_at_another_head,
        _same(_DEQUEUED, "planned→dequeue: read"),
    ),
    "held-at-another-head-without-a-queue": (
        _held_at_another_head_without_a_queue,
        _same("head-moved: read read disable-auto read read", "planned→dequeue: read"),
    ),
    "open-at-another-head": (_open_at_another_head, _same("head-moved: read")),
    "queued-at-the-head": (
        _queued_at_the_head,
        {
            "no-option": Cell(_WAITED, "planned→wait: read defaults"),
            "admin": Cell("refused(admin-on-queue): read", "refused(admin-on-queue): read"),
            "direct-only": Cell(
                "refused(queue-not-allowed): read", "refused(queue-not-allowed): read"
            ),
            "shape-bad-refuse": Cell(
                "refused(queue-not-squash): read", "refused(queue-not-squash): read"
            ),
            "shape-bad-warn": Cell("merged: read read", "planned→wait: read"),
            "allow-dropped-head": Cell(_WAITED, "planned→wait: read defaults"),
        },
    ),
    "dropped-at-the-head": (
        _dropped_at_the_head,
        {
            "no-option": Cell("refused(dropped-head): read", "refused(dropped-head): read"),
            "admin": Cell("refused(admin-on-queue): read", "refused(admin-on-queue): read"),
            "direct-only": Cell(
                "refused(queue-not-allowed): read", "refused(queue-not-allowed): read"
            ),
            "shape-bad-refuse": Cell(
                "refused(queue-not-squash): read", "refused(queue-not-squash): read"
            ),
            "shape-bad-warn": Cell(
                "refused(queue-not-squash): read", "refused(queue-not-squash): read"
            ),
            "allow-dropped-head": Cell(_ENQUEUED, "planned→enqueue: read defaults"),
        },
    ),
    "open-on-a-queue": (
        _open_on_a_queue,
        {
            "no-option": Cell(_ENQUEUED, "planned→enqueue: read defaults"),
            "admin": Cell("refused(admin-on-queue): read", "refused(admin-on-queue): read"),
            "direct-only": Cell(
                "refused(queue-not-allowed): read", "refused(queue-not-allowed): read"
            ),
            "shape-bad-refuse": Cell(
                "refused(queue-not-squash): read", "refused(queue-not-squash): read"
            ),
            "shape-bad-warn": Cell(
                "refused(queue-not-squash): read", "refused(queue-not-squash): read"
            ),
            "allow-dropped-head": Cell(_ENQUEUED, "planned→enqueue: read defaults"),
        },
    ),
    "open-without-a-queue": (
        _open_without_a_queue,
        {
            **_same(_MERGED, "planned→merge: read"),
            "admin": Cell(_ADMIN_MERGED, "planned→merge: read"),
        },
    ),
    "held-at-the-head-without-a-queue": (
        _held_at_the_head_without_a_queue,
        {
            **_same(_MERGED, "planned→merge: read"),
            "admin": Cell(_ADMIN_MERGED, "planned→merge: read"),
        },
    ),
}

_CELLS = [
    pytest.param(row, column, dry_run, id=f"{row}-{column}-{'plan' if dry_run else 'run'}")
    for row in TABLE
    for column in _COLUMNS
    for dry_run in (False, True)
]


def _said(end: landing.Landing, service: fake.HostingService) -> str:
    kind = f"({end.reason_kind})" if end.reason_kind else ""
    would = f"→{end.would}" if end.would else ""
    return f"{end.ended}{kind}{would}: {_requests(service)}"


@pytest.mark.parametrize(("row", "column", "dry_run"), _CELLS)
def test_the_table_cell_by_cell(
    row: str,
    column: str,
    dry_run: bool,
    here: dict[str, Any],
    host: fake.HostingService,
) -> None:
    """Every cell of the table, as a landing and as its dry run: the first
    matching row decides, the options applied to it; a dry run sends
    nothing, and ends planned where the landing would send or wait, as the
    landing would everywhere else. No cell deletes a branch, every end
    document carries every key, and it decodes by its own `ended`."""
    setup, cells = TABLE[row]
    setup(host)
    options = _COLUMNS[column](host)
    end = _land(here, dry_run=dry_run, **options)
    expected = cells[column]
    assert _said(end, host) == (expected.plan if dry_run else expected.run)
    assert fake.BRANCH not in host.kinds() and fake.DELETE_REF not in host.kinds()
    document = end.as_json()
    assert set(document) == landing.END_KEYS
    assert landing.decode_end(json.loads(json.dumps(document))) == document
    assert document["dry_run"] is dry_run and document["checked_head"] == HEAD


def test_a_dry_run_sends_nothing_in_any_cell(here: dict[str, Any]) -> None:
    """No cell's dry run sends a request: its requests are readings alone."""
    for row, (setup, _) in TABLE.items():
        for column, option in _COLUMNS.items():
            service = fake.HostingService()
            setup(service)
            options = option(service)
            with pytest.MonkeyPatch.context() as patched:
                patched.setattr(landing, "gh_runner", lambda cwd, s=service: _bounded(s))
                _land(here, dry_run=True, **options)
            assert set(service.landing()) <= {fake.READ, fake.DEFAULTS}, (row, column)


def test_under_warn_a_queued_pr_with_a_bad_shape_is_planned_as_a_wait_with_its_warning(
    here: dict[str, Any], host: fake.HostingService
) -> None:
    _queued_at_the_head(host)
    host.squash_defaults = ("COMMIT_OR_PR_TITLE", "PR_BODY")
    plan = _land(here, dry_run=True, queued_bad_shape=landing.SHAPE_WARN)
    assert (plan.ended, plan.would) == (landing.END_PLANNED, landing.WAIT)
    [warning] = plan.warnings
    assert warning.reason_kind == landing.SQUASH_DEFAULTS
    assert "title COMMIT_OR_PR_TITLE and message PR_BODY" in warning.reason
    assert plan.shape == landing.Shape(True, "COMMIT_OR_PR_TITLE", "PR_BODY", False)


# ---- the refusal order and the stops no option lifts -------------------------------


def test_the_refusals_come_in_one_order_the_squash_defaults_read_last(
    here: dict[str, Any], host: fake.HostingService
) -> None:
    """Every refusal applies at once; lifting each in turn shows the next:
    admin-on-queue, queue-not-allowed, queue-not-squash, dropped-head,
    squash-defaults — the defaults read only for the last."""
    _queue(host, method="MERGE")
    host.dropped_before()
    host.squash_defaults = ("COMMIT_OR_PR_TITLE", "COMMIT_MESSAGES")
    steps: list[tuple[dict[str, Any], str, str]] = [
        ({"admin": True, "direct_only": True}, landing.ADMIN_ON_QUEUE, "read"),
        ({"direct_only": True}, landing.QUEUE_NOT_ALLOWED, "read"),
        ({}, landing.QUEUE_NOT_SQUASH, "read"),
    ]
    for options, kind, asked in steps:
        host.requests.clear()
        end = _land(here, **options)
        assert (end.ended, end.reason_kind, _requests(host)) == (landing.END_REFUSED, kind, asked)
    _queue(host)
    host.requests.clear()
    end = _land(here)
    assert (end.reason_kind, _requests(host)) == (landing.DROPPED_HEAD, "read")
    assert end.shape == landing.Shape(True)
    host.requests.clear()
    end = _land(here, allow_dropped_head=True)
    assert (end.reason_kind, _requests(host)) == (landing.SQUASH_DEFAULTS, "read defaults")
    assert end.shape == landing.Shape(True, "COMMIT_OR_PR_TITLE", "COMMIT_MESSAGES", False)


def test_defaults_that_cannot_be_read_end_unreadable_and_are_a_warning_under_warn(
    here: dict[str, Any], host: fake.HostingService
) -> None:
    _open_on_a_queue(host)
    host.squash_defaults = None
    end = _land(here)
    assert (end.ended, end.reason_kind, end.sent) == (
        landing.END_UNREADABLE,
        landing.SQUASH_DEFAULTS,
        None,
    )
    assert end.shape is not None and end.shape.unreadable == end.reason
    assert end.shape.conforms is None and end.shape.title is None
    _queued_at_the_head(host)
    waited = _land(here, queued_bad_shape=landing.SHAPE_WARN)
    assert waited.ended == landing.END_MERGED
    assert [w.reason_kind for w in waited.warnings] == [landing.SQUASH_DEFAULTS]


@pytest.mark.parametrize(
    "options",
    [
        {"admin": True},
        {"admin": True, "queued_bad_shape": landing.SHAPE_WARN},
        {"admin": True, "allow_dropped_head": True},
        {"admin": True, "direct_only": True},
    ],
)
@pytest.mark.parametrize("state", ["open", "queued", "dropped"])
def test_no_option_makes_an_administrator_merge_on_a_queue_base(
    options: dict[str, Any], state: str, here: dict[str, Any], host: fake.HostingService
) -> None:
    {"open": _open_on_a_queue, "queued": _queued_at_the_head, "dropped": _dropped_at_the_head}[
        state
    ](host)
    end = _land(here, **options)
    assert (end.ended, end.reason_kind) == (landing.END_REFUSED, landing.ADMIN_ON_QUEUE)
    assert _requests(host) == "read"


@pytest.mark.parametrize(
    "options",
    [
        {},
        {"queued_bad_shape": landing.SHAPE_WARN},
        {"allow_dropped_head": True},
        {"allow_dropped_head": True, "queued_bad_shape": landing.SHAPE_WARN},
    ],
)
@pytest.mark.parametrize("bad", ["method", "defaults"])
@pytest.mark.parametrize("state", ["open", "dropped"])
def test_no_option_hands_a_pr_to_a_queue_that_would_not_make_its_commit(
    options: dict[str, Any],
    bad: str,
    state: str,
    here: dict[str, Any],
    host: fake.HostingService,
) -> None:
    """A queue that does not squash, or composes from other defaults, is
    handed nothing, whatever the options: `warn` relaxes only a PR already
    queued, which gets no request."""
    (_open_on_a_queue if state == "open" else _dropped_at_the_head)(host)
    if bad == "method":
        _queue(host, method="REBASE")
    else:
        host.squash_defaults = ("PR_TITLE", "BLANK")
    end = _land(here, **options)
    assert end.ended == landing.END_REFUSED
    assert end.reason_kind in (
        landing.QUEUE_NOT_SQUASH,
        landing.SQUASH_DEFAULTS,
        landing.DROPPED_HEAD,
    )
    assert fake.ENQUEUE not in host.kinds() and fake.MERGE not in host.kinds()


# ---- the wait's ends ----------------------------------------------------------------


def _enqueued(service: fake.HostingService, *progress: fake.Step) -> None:
    _queue(service)
    service.progress = list(progress)


@pytest.mark.parametrize(
    ("setup", "options", "ended", "reason_kind", "sent"),
    [
        (
            lambda s: _enqueued(s, fake.at(1), fake.lands()),
            {},
            landing.END_MERGED,
            None,
            landing.ENQUEUE_REQUEST,
        ),
        (
            lambda s: _enqueued(s, fake.at(1), lambda h: h.merge_now(head=OTHER)),
            {},
            landing.END_MERGED_ELSEWHERE,
            None,
            landing.ENQUEUE_REQUEST,
        ),
        (
            lambda s: _enqueued(s, fake.at(3, "QUEUED")),
            {"seconds": 60},
            landing.END_QUEUED,
            None,
            landing.ENQUEUE_REQUEST,
        ),
        (
            lambda s: _enqueued(s, fake.at(1), fake.drops()),
            {},
            landing.END_DROPPED,
            None,
            landing.ENQUEUE_REQUEST,
        ),
        (
            lambda s: (_enqueued(s), s.after(fake.ENQUEUE, _fail_every_read)),
            {},
            landing.END_QUEUED,
            landing.NOT_READ,
            landing.ENQUEUE_REQUEST,
        ),
        (
            lambda s: (_queued_at_the_head(s), s.after(fake.DEFAULTS, _fail_every_read)),
            {},
            landing.END_QUEUED,
            landing.NOT_READ,
            None,
        ),
        (
            lambda s: s.after(fake.MERGE, _fail_every_read),
            {},
            landing.END_UNCONFIRMED,
            landing.NOT_READ,
            landing.MERGE_REQUEST,
        ),
        (
            lambda s: s.after(fake.MERGE, _unmerge),
            {},
            landing.END_NOT_MERGED,
            None,
            landing.MERGE_REQUEST,
        ),
        (
            lambda s: (s.after(fake.MERGE, _unmerge), s.after(fake.READ, _close_it, nth=2)),
            {},
            landing.END_NOT_MERGED,
            None,
            landing.MERGE_REQUEST,
        ),
    ],
    ids=[
        "merged",
        "merged-at-another-head",
        "time-ran-out",
        "out-on-two-readings-a-queue-seen",
        "unreadable-after-an-enqueue",
        "unreadable-found-queued",
        "unreadable-after-a-direct-merge",
        "out-on-two-readings-no-queue-seen",
        "closed-after-the-merge-no-queue-seen",
    ],
)
def test_each_way_the_wait_ends(
    setup: Callable[[fake.HostingService], Any],
    options: dict[str, Any],
    ended: str,
    reason_kind: str | None,
    sent: str | None,
    here: dict[str, Any],
    host: fake.HostingService,
) -> None:
    setup(host)
    end = _land(here, **options)
    assert (end.ended, end.reason_kind, end.sent) == (ended, reason_kind, sent)
    if ended in (landing.END_MERGED, landing.END_MERGED_ELSEWHERE):
        assert end.merged_head == host.merged_head
        assert end.merge_commit == host.merge_commit
    else:
        assert end.merged_head is None and end.merge_commit is None
    if reason_kind == landing.NOT_READ:
        assert end.reason == "HTTP 502: Bad Gateway"


def _unmerge(service: fake.HostingService) -> None:
    """gh accepted the merge, and the service shows nothing of it."""
    service.state, service.merged_at, service.merged_head, service.merge_commit = "OPEN", "", "", ""


def _close_it(service: fake.HostingService) -> None:
    service.close()


def test_a_reading_after_a_direct_merge_that_fails_is_one_warning_then_the_wait(
    here: dict[str, Any], host: fake.HostingService
) -> None:
    host.after(fake.MERGE, lambda s: s.fail(fake.READ))
    end = _land(here)
    assert (end.ended, end.sent) == (landing.END_MERGED, landing.MERGE_REQUEST)
    assert end.warnings == (landing.Notice(landing.NOT_READ, "HTTP 502: Bad Gateway"),)
    assert _requests(host) == "read merge read read"


# ---- a request with no usable answer, settled inside the landing ----------------------


@pytest.mark.parametrize("request_", ["merge", "enqueue"])
@pytest.mark.parametrize(
    ("ends", "ended", "reason_kind", "sent"),
    [
        ("made", landing.END_MERGED, None, True),
        ("not-seen-made", landing.END_FAILED, landing.NOT_MADE, True),
        ("unconfirmed", landing.END_UNCONFIRMED, landing.UNANSWERED, True),
        ("refused", landing.END_FAILED, None, False),
    ],
)
def test_each_way_a_request_settles(
    request_: str,
    ends: str,
    ended: str,
    reason_kind: str | None,
    sent: bool,
    here: dict[str, Any],
    host: fake.HostingService,
) -> None:
    """Made on a reading, the landing goes on; not seen made on two readings,
    it fails — never saying it was not made — the request `sent`;
    unconfirmed, it says so, `sent`; refused on an answer, it fails in gh's
    words, nothing `sent`."""
    kind = fake.ENQUEUE if request_ == "enqueue" else fake.MERGE
    if request_ == "enqueue":
        _enqueued(host, fake.at(1), fake.lands())
    if ends == "made":
        host.lose_reply(kind)
    elif ends == "refused":
        host.fail(kind, stderr="GraphQL: Head branch was modified. Review and try the merge again.")
    else:
        host.never_receive(kind)
    if ends == "unconfirmed":
        host.before(kind, _fail_every_read)
    events: list[dict[str, Any]] = []
    end = _land(here, events=events)
    assert (end.ended, end.reason_kind, end.sent) == (
        ended,
        reason_kind,
        request_ if sent else None,
    )
    if ends == "not-seen-made":
        assert "was not made" not in (end.reason or "")
        assert "was not seen made on two readings" in (end.reason or "")
    if ends == "refused":
        assert end.reason == "GraphQL: Head branch was modified. Review and try the merge again."
    [requested] = [e for e in events if e["event"] == "requested"]
    assert requested["request"] == request_
    assert set(requested) == {
        "schema_version",
        "pull_request",
        "event",
        "request",
        "accepted",
        "exit_code",
        "reason",
        "reason_kind",
    }


# ---- the head moves ------------------------------------------------------------------


def test_a_head_that_moved_before_any_request_ends_with_nothing_sent(
    here: dict[str, Any], host: fake.HostingService
) -> None:
    _open_at_another_head(host)
    events: list[dict[str, Any]] = []
    end = _land(here, events=events)
    assert (end.ended, end.dequeue, end.sent) == (landing.END_HEAD_MOVED, None, None)
    assert [e["event"] for e in events] == ["reading"]
    assert end.reason is not None and PUSHED[:7] in end.reason and HEAD[:7] in end.reason


def _moves_while_queued(service: fake.HostingService) -> None:
    _enqueued(service, fake.at(2), fake.pushes(PUSHED))


@pytest.mark.parametrize(
    ("setup", "dequeue"),
    [
        (lambda s: None, {"accepted": True, "reason_kind": None}),
        (
            lambda s: (s.never_receive(fake.DEQUEUE), s.before(fake.DEQUEUE, _fail_every_read)),
            {"accepted": None, "reason_kind": landing.UNANSWERED},
        ),
        (
            lambda s: s.before(fake.READ, lambda h: h.merge_now(), nth=4),
            {"accepted": False, "reason_kind": landing.HAS_MERGED},
        ),
        (
            lambda s: s.fail(fake.DEQUEUE, count=None, stderr="GraphQL: Something went wrong"),
            {"accepted": False, "reason_kind": None},
        ),
        (
            lambda s: s.after(fake.READ, _fail_every_read, nth=3),
            {"accepted": False, "reason_kind": landing.NOT_READ},
        ),
        (
            lambda s: s.never_receive(fake.DEQUEUE),
            {"accepted": True, "reason_kind": None},
        ),
    ],
    ids=["taken-out", "unconfirmed", "merged-meanwhile", "refused", "unreadable", "sent-twice"],
)
def test_a_head_that_moved_during_the_wait_is_taken_out_and_the_dequeue_embedded(
    setup: Callable[[fake.HostingService], Any],
    dequeue: dict[str, Any],
    here: dict[str, Any],
    host: fake.HostingService,
) -> None:
    """Whatever taking it out came to, the landing ends head-moved — a PR the
    queue merged meanwhile among them — and `dequeue` says it, as `pkit
    pull-request dequeue` would."""
    _moves_while_queued(host)
    setup(host)
    events: list[dict[str, Any]] = []
    end = _land(here, events=events)
    assert (end.ended, end.sent) == (landing.END_HEAD_MOVED, landing.ENQUEUE_REQUEST)
    assert end.dequeue is not None
    embedded = end.as_json()["dequeue"]
    assert set(embedded) == {"accepted", "exit_code", "reason", "reason_kind"}
    assert {k: embedded[k] for k in dequeue} == dequeue
    dequeues = [e for e in events if e.get("request") == landing.DEQUEUE_REQUEST]
    if dequeue["reason_kind"] in (landing.NOT_READ, landing.HAS_MERGED):
        assert dequeues == []  # nothing was sent
    else:
        assert dequeues[-1]["event"] == "requested"
        assert dequeues.count(dequeues[-1]) == 1


def test_a_dequeue_sent_once_more_writes_two_requesting_and_one_requested(
    here: dict[str, Any], host: fake.HostingService
) -> None:
    _moves_while_queued(host)
    host.never_receive(fake.DEQUEUE)
    events: list[dict[str, Any]] = []
    _land(here, events=events)
    dequeues = [
        (e["event"], e.get("attempt"), e.get("head"))
        for e in events
        if e.get("request") == landing.DEQUEUE_REQUEST
    ]
    assert dequeues == [("requesting", 1, None), ("requesting", 2, None), ("requested", None, None)]


# ---- the events ------------------------------------------------------------------------


def test_a_direct_merge_writes_its_events_in_order(
    here: dict[str, Any], host: fake.HostingService
) -> None:
    events: list[dict[str, Any]] = []
    end = _land(here, events=events)
    assert [e["event"] for e in events] == ["reading", "requesting", "requested", "reading"]
    assert events[1] == {
        "schema_version": 1,
        "pull_request": PR,
        "event": "requesting",
        "request": "merge",
        "head": HEAD,
        "attempt": 1,
    }
    assert events[2] == {
        "schema_version": 1,
        "pull_request": PR,
        "event": "requested",
        "request": "merge",
        "accepted": True,
        "exit_code": 0,
        "reason": "",
        "reason_kind": None,
    }
    assert set(events[0]) == {"schema_version", "pull_request", "event", "reading"}
    assert end.ended == landing.END_MERGED


def test_the_requesting_line_is_written_before_gh_is_started(
    here: dict[str, Any], host: fake.HostingService, monkeypatch: pytest.MonkeyPatch
) -> None:
    """In this process: when the merge reaches `gh`, its `requesting` is
    already written."""
    events: list[dict[str, Any]] = []
    seen_by_gh: list[list[str]] = []
    host.before(fake.MERGE, lambda s: seen_by_gh.append([e["event"] for e in events]))
    _land(here, events=events)
    assert seen_by_gh == [["reading", "requesting"]]


def test_the_wait_writes_each_reading_that_changed(
    here: dict[str, Any], host: fake.HostingService
) -> None:
    _enqueued(host, fake.at(2), fake.at(2), fake.at(1, "MERGEABLE"), fake.lands())
    events: list[dict[str, Any]] = []
    _land(here, events=events)
    readings = [e["reading"]["description"] for e in events if e["event"] == "reading"]
    assert readings == [
        "not in the queue",
        "position 2 in the queue, awaiting checks, about 5 min to merge",
        "position 1 in the queue, mergeable, about 5 min to merge",
        "merged at 2026-10-01T10:12:00Z",
    ]


def test_a_dry_run_writes_a_reading_and_nothing_else(
    here: dict[str, Any], host: fake.HostingService
) -> None:
    events: list[dict[str, Any]] = []
    plan = _land(here, dry_run=True, events=events)
    assert [e["event"] for e in events] == ["reading"]
    assert (plan.ended, plan.would, plan.reason, plan.sent) == (
        landing.END_PLANNED,
        landing.MERGE_REQUEST,
        None,
        None,
    )


# ---- the end document ------------------------------------------------------------------


def test_a_merge_states_the_head_and_commit_it_merged_at(
    here: dict[str, Any], host: fake.HostingService
) -> None:
    end = _land(here).as_json()
    assert (end["merged_head"], end["merge_commit"], end["path"]) == (
        HEAD,
        host.merge_commit,
        landing.PATH_DIRECT,
    )
    assert end["reason"] is None and end["shape"] is None and end["warnings"] == []
    assert end["guard"] == {
        "verdict": "undetermined",
        "undetermined_kind": "noncoverage",
        "anchor": None,
        "target": None,
        "cleared": "undetermined",
    }


def test_the_shape_is_null_on_a_base_without_a_queue_and_judged_on_one(
    here: dict[str, Any], host: fake.HostingService
) -> None:
    assert _land(here, dry_run=True).shape is None
    _open_on_a_queue(host)
    plan = _land(here, dry_run=True)
    assert plan.shape == landing.Shape(True, "PR_TITLE", "PR_BODY", True)
    assert plan.path == landing.PATH_QUEUE


def _a_valid_end() -> dict[str, Any]:
    return landing.Landing(
        PR,
        landing.END_MERGED,
        HEAD,
        session_guard.Clearance(
            Path("/repo"),
            session_guard.UNDETERMINED,
            session_guard.Comparison(
                session_guard.UNDETERMINED, session_guard.NONCOVERAGE, None, None, "none"
            ),
        ),
        1.0,
        reading=landing.Reading(has_queue=False, pr_state="MERGED", head_oid=HEAD),
    ).as_json()


@pytest.mark.parametrize("key", sorted(landing.END_KEYS))
def test_an_end_document_missing_a_key_is_no_answer(key: str) -> None:
    document = _a_valid_end()
    del document[key]
    with pytest.raises(landing.NotAnEnd, match=f"`{key}`"):
        landing.decode_end(document)


@pytest.mark.parametrize(
    ("changed", "says"),
    [
        ({"ended": "landed"}, "names no way a landing ends"),
        ({"ended": None}, "names no way a landing ends"),
        ({"reason_kind": "not-made"}, "carries no `reason_kind`"),
        ({"would": "merge"}, "cannot say it would"),
        ({"merged_head": None}, "cannot name `merged_head`"),
        ({"dequeue": {"accepted": True}}, "ran no dequeue"),
        ({"sent": "dequeue"}, "sends no"),
        ({"schema_version": 2}, "not a version-1 end"),
        ({"event": "reading"}, "not a version-1 end"),
        ({"warnings": None}, "`warnings` or `guard`"),
    ],
)
def test_an_end_document_decodes_strictly_by_its_ended(changed: dict[str, Any], says: str) -> None:
    """An unknown `ended`, or a key its `ended` does not carry, is no answer."""
    with pytest.raises(landing.NotAnEnd, match=says):
        landing.decode_end({**_a_valid_end(), **changed})


@pytest.mark.parametrize(
    ("ended", "reason_kind", "would"),
    [
        (landing.END_PLANNED, None, None),
        (landing.END_REFUSED, None, None),
        (landing.END_UNCONFIRMED, None, None),
        (landing.END_QUEUED, landing.NOT_MADE, None),
        (landing.END_HEAD_MOVED, None, landing.MERGE_REQUEST),
    ],
)
def test_each_ended_carries_only_its_own_reason_kinds_and_would(
    ended: str, reason_kind: str | None, would: str | None
) -> None:
    document = {
        **_a_valid_end(),
        "ended": ended,
        "reason_kind": reason_kind,
        "would": would,
        "merged_head": None,
    }
    with pytest.raises(landing.NotAnEnd):
        landing.decode_end(document)


def test_the_closed_sets_of_ends_and_their_reason_kinds() -> None:
    assert dict(landing.LANDING_ENDS) == {
        "merged": {None},
        "merged-at-another-head": {None},
        "closed": {None},
        "planned": {None},
        "queued": {None, "unreadable"},
        "unconfirmed": {"unanswered", "unreadable"},
        "head-moved": {None},
        "dropped": {None},
        "not-merged": {None},
        "failed": {None, "not-made"},
        "refused": {
            "foreign-repository",
            "admin-on-queue",
            "queue-not-allowed",
            "queue-not-squash",
            "dropped-head",
            "squash-defaults",
        },
        "unreadable": {None, "squash-defaults"},
    }


# ---- the bound ---------------------------------------------------------------------------


def test_the_bound_is_the_sum_of_every_leg_a_landing_can_run() -> None:
    """The composition (#1258's addendum D): the guard, one reading, the
    squash-commit defaults, the merge or the enqueue less the guard, one
    reading after a direct merge, the wait's limit and its overrun, and the
    dequeue less the guard — from the module's own helpers, so a leg that
    grows flows in."""
    guard = session_guard.LONGEST_SECONDS
    reading = landing.longest_seconds("read")
    defaults = landing.longest_seconds("squash-defaults")
    request = max(landing.longest_seconds("merge"), landing.longest_seconds("enqueue")) - guard
    taking_out = landing.longest_seconds("dequeue") - guard
    overrun = landing.wait_overrun_seconds()
    assert landing.planning_longest_seconds() == guard + reading + defaults
    for seconds, limit in ((None, landing.MAX_WAIT_SECONDS), (0.0, 0.0), (90.0, 90.0)):
        assert landing.landing_longest_seconds(seconds) == (
            guard + reading + defaults + request + reading + limit + overrun + taking_out
        )


def test_the_dry_run_plans_within_its_own_bound() -> None:
    """The dry run's longest — the guard, one reading, the defaults — with
    the constants as they stand."""
    assert landing.planning_longest_seconds() == 98.0


@pytest.mark.parametrize("seconds", [None, 0.0, 120.0])
@pytest.mark.parametrize(
    "setup", [_open_without_a_queue, _open_on_a_queue, _queued_at_the_head, _unreadable]
)
def test_the_bound_is_the_same_in_the_dry_run_and_the_landing(
    seconds: float | None,
    setup: Callable[[fake.HostingService], None],
    here: dict[str, Any],
    host: fake.HostingService,
) -> None:
    """A function of the options alone, never of what was read: the dry run
    states the bound of the landing it plans."""
    setup(host)
    plan = _land(here, dry_run=True, seconds=seconds)
    run = _land(here, seconds=seconds)
    assert plan.bound_seconds == run.bound_seconds == landing.landing_longest_seconds(seconds)


# ---- the guard ------------------------------------------------------------------------


def test_a_landing_needs_a_clearance_for_where_it_acts(
    tmp_path: Path, host: fake.HostingService, here: dict[str, Any]
) -> None:
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    with pytest.raises(ValueError, match="the clearance is for"):
        landing.land(PR, head=HEAD, subject="x", cwd=elsewhere, clearance=here["clearance"])
    with pytest.raises(TypeError):
        landing.land(PR, head=HEAD, subject="x", cwd=tmp_path, clearance=None)  # pyright: ignore[reportArgumentType] a caller with no clearance, for the module's own check
    with pytest.raises(ValueError, match="none was named"):
        landing.land(PR, head="", subject="x", **here)
    assert host.requests == []
