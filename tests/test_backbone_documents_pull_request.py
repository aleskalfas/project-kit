"""The documents `pkit pull-request` prints hold their contracts (ADR-097 point 7).

Each command runs once against the shared fake of the hosting service
(`tests.hosting_fake`), and the documents it prints in states the fake does not reach
cheaply are built by the functions the command prints them through: a request's
outcome, the guard's clearance or refusal, a branch's deletion, a wait's lines, and a
landing's end. A reading is built by the module's own reading, given the reading it
would have taken. `tests/test_backbone_documents.py` gathers the contracts here into
its ratchet.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable, Iterator, Mapping, Sequence
from pathlib import Path
from typing import Any

import pytest

from project_kit import pull_request_landing as landing
from project_kit import session_guard as guard
from tests import hosting_fake as fake
from tests.backbone_documents import JSON_OPTION, document_of, documents_of, invoke
from tests.document_contracts import Contract, Form, check

PR = 496
HEAD = fake.HEAD
PR_ARGUMENT = str(PR)

#: What GitHub names a pull request's state, a queue's merge method and an entry's
#: state, as a reading passes them on; empty where there is no queue, or no entry.
_PR_STATES = frozenset({"OPEN", "CLOSED", "MERGED"})
_MERGE_METHODS = frozenset({"SQUASH", "MERGE", "REBASE", ""})
_ENTRY_STATES = frozenset({"QUEUED", "AWAITING_CHECKS", "MERGEABLE", "UNMERGEABLE", "LOCKED", ""})

#: Where a pull request stands, as `Reading.as_json` builds it wherever a document holds
#: one.
READING = Form(
    keys={
        "has_queue": "bool",
        "merge_method": "str",
        "pr_id": "str",
        "pr_state": "str",
        "merged_at": "str",
        "head_oid": "str",
        "in_queue": "bool",
        "position": "int|null",
        "entry_state": "str",
        "eta_seconds": "int|null",
        "waiting_to_enter": "bool",
        "ever_queued": "bool",
        "removal": "object|null",
        "removal.at": "str",
        "removal.reason": "str",
        "removal.head_oid": "str",
        "head_ref": "str",
        "cross_repository": "bool",
        "merge_commit": "str",
        "ahead": "list",
        "ahead[]": "int",
        "merged": "bool",
        "queued": "bool",
        "squashes": "bool",
        "dropped_head": "bool",
        "description": "str",
    }
)

#: The cross-repository guard, as `session_guard` gives it wherever a document holds it.
GUARD = Form(
    keys={
        "verdict": "str",
        "undetermined_kind": "str|null",
        "anchor": "str|null",
        "target": "str|null",
        "cleared": "str|null",
    }
)

_READING_SETS = {
    "reading:pr_state": _PR_STATES,
    "reading:merge_method": _MERGE_METHODS,
    "reading:entry_state": _ENTRY_STATES,
}
_GUARD_SETS = {
    "guard:verdict": frozenset({"same-repo", "diverged", "undetermined"}),
    "guard:undetermined_kind": frozenset({"noncoverage", "fault"}),
    "guard:cleared": frozenset({"same-repo", "undetermined", "flag", "terminal"}),
}
_SQUASH_TITLES = frozenset({"PR_TITLE", "COMMIT_OR_PR_TITLE"})
_SQUASH_MESSAGES = frozenset({"PR_BODY", "COMMIT_MESSAGES", "BLANK"})

READ = Contract(
    name="pkit pull-request read --json",
    version=1,
    forms={
        "answer": Form(
            keys={
                "schema_version": "int",
                "pull_request": "int",
                "reading": "object|null",
                "unreadable": "str|null",
            }
        )
    },
    shapes={"reading": READING},
    refs={"reading": "reading"},
    sets=_READING_SETS,
)

SQUASH_DEFAULTS = Contract(
    name="pkit pull-request squash-defaults --json",
    version=1,
    forms={
        "answer": Form(
            keys={
                "schema_version": "int",
                "title": "str|null",
                "message": "str|null",
                "unreadable": "str|null",
            }
        )
    },
    sets={"title": _SQUASH_TITLES, "message": _SQUASH_MESSAGES},
)

_REQUEST_KEYS = {
    "accepted": "bool|null",
    "exit_code": "int|null",
    "reason": "str",
    "reason_kind": "str|null",
}

#: Why a request was not made, or whether it was is not known, as `merge` and `enqueue`
#: name it; `dequeue` names two more.
_REQUEST_KINDS = frozenset({"foreign-repository", "not-made", "unanswered"})
_DEQUEUE_KINDS = _REQUEST_KINDS | {"merged", "unreadable"}


def _request(command: str, kinds: frozenset[str]) -> Contract:
    return Contract(
        name=f"pkit pull-request {command} --json",
        version=1,
        forms={
            "answer": Form(
                keys={
                    "schema_version": "int",
                    "pull_request": "int",
                    **_REQUEST_KEYS,
                    "guard": "object",
                }
            )
        },
        shapes={"guard": GUARD},
        refs={"guard": "guard"},
        sets={"reason_kind": kinds, **_GUARD_SETS},
    )


MERGE = _request("merge", _REQUEST_KINDS)
ENQUEUE = _request("enqueue", _REQUEST_KINDS)
DEQUEUE = _request("dequeue", _DEQUEUE_KINDS)

_DELETION_OUTCOMES = frozenset({"deleted", "kept", "gone", "refused", "unconfirmed"})
_DELETION_KINDS = frozenset(
    {
        "tip-moved",
        "open-pull-request",
        "deletion-refused",
        "unanswered",
        "not-merged",
        "cross-repository",
        "expect-mismatch",
        "unreadable",
        "foreign-repository",
    }
)

DELETE_BRANCH = Contract(
    name="pkit pull-request delete-branch --json",
    version=1,
    forms={
        "answer": Form(
            keys={
                "schema_version": "int",
                "pull_request": "int",
                "expected": "str",
                "outcome": "str",
                "branch": "str|null",
                "tip": "str|null",
                "reason_kind": "str|null",
                "reason": "str|null",
                "merged_head": "str|null",
                "guard": "object",
            }
        )
    },
    shapes={"guard": GUARD},
    refs={"guard": "guard"},
    sets={"outcome": _DELETION_OUTCOMES, "reason_kind": _DELETION_KINDS, **_GUARD_SETS},
)

_STREAM = {"schema_version": "int", "pull_request": "int", "event": "str"}

WAIT = Contract(
    name="pkit pull-request wait --json",
    version=1,
    forms={
        "reading": Form(keys={**_STREAM, "reading": "object"}),
        "end": Form(
            keys={
                **_STREAM,
                "ended": "str|null",
                "reading": "object|null",
                "unreadable": "str|null",
            }
        ),
    },
    shapes={"reading": READING},
    refs={"reading": "reading"},
    sets={
        "event": frozenset({"reading", "end"}),
        "ended": frozenset({"merged", "queued", "left", "head-moved"}),
        **_READING_SETS,
    },
)

_ENDS = frozenset(
    {
        "merged",
        "merged-at-another-head",
        "closed",
        "planned",
        "queued",
        "unconfirmed",
        "head-moved",
        "dropped",
        "not-merged",
        "failed",
        "refused",
        "unreadable",
    }
)
#: Why a landing ended as it did, by its `reason_kind`, and why a request it made was not
#: made, or whether it was is not known: one key in two forms.
_LANDING_KINDS = frozenset(
    {
        "foreign-repository",
        "request-not-allowed",
        "admin-on-queue",
        "queue-not-allowed",
        "queue-not-squash",
        "dropped-head",
        "queued-ahead",
        "squash-defaults",
        "unreadable",
        "unanswered",
        "not-made",
    }
)
_MERGED_ENDS = ("merged", "merged-at-another-head")
_REQUESTS = frozenset({"merge", "enqueue", "dequeue"})
_WARNINGS = frozenset(
    {"queue-not-squash", "squash-defaults", "unreadable", "auto-merge-armed", "enqueued-instead"}
)

LAND = Contract(
    name="pkit pull-request land --json",
    version=1,
    forms={
        "reading": Form(keys={**_STREAM, "reading": "object"}),
        "requesting": Form(
            keys={**_STREAM, "request": "str", "head": "str|null", "attempt": "int"}
        ),
        "requested": Form(keys={**_STREAM, "request": "str", **_REQUEST_KEYS}),
        "end": Form(
            keys={
                **_STREAM,
                "dry_run": "bool",
                "ended": "str",
                "reason_kind": "str|null",
                "reason": "str|null",
                "would": "str|null",
                "path": "str|null",
                "checked_head": "str",
                "merged_head": "str|null",
                "merge_commit": "str|null",
                "sent": "str|null",
                "dequeue": "object|null",
                **{f"dequeue.{key}": kind for key, kind in _REQUEST_KEYS.items()},
                "reading": "object|null",
                "shape": "object|null",
                "shape.squashes": "bool",
                "shape.title": "str|null",
                "shape.message": "str|null",
                "shape.conforms": "bool|null",
                "shape.unreadable": "str|null",
                "warnings": "list",
                "warnings[]": "object",
                "warnings[].reason_kind": "str",
                "warnings[].reason": "str",
                "guard": "object",
                "bound_seconds": "float",
            }
        ),
    },
    shapes={"reading": READING, "guard": GUARD},
    refs={"reading": "reading", "guard": "guard"},
    sets={
        "event": frozenset({"reading", "requesting", "requested", "end"}),
        "request": _REQUESTS,
        "ended": _ENDS,
        "reason_kind": _LANDING_KINDS,
        "would": frozenset({"merge", "enqueue", "wait", "dequeue"}),
        "path": frozenset({"queue", "direct"}),
        "sent": frozenset({"merge", "enqueue"}),
        "dequeue.reason_kind": _DEQUEUE_KINDS - {"foreign-repository"},
        "shape.title": _SQUASH_TITLES,
        "shape.message": _SQUASH_MESSAGES,
        "warnings[].reason_kind": _WARNINGS,
        **_READING_SETS,
        **_GUARD_SETS,
    },
)


# --- the service, and what a document is built from --------------------------------------


Serve = Callable[[fake.HostingService], fake.HostingService]


@pytest.fixture
def serve(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Serve:
    """`serve(service)` makes `service` the hosting service every `gh` of the noun
    reaches, on a clock that sleeps no time, run outside any session from a directory of
    the test's own."""
    clock = fake.Clock()
    monkeypatch.setattr(landing, "_sleep", clock.sleep)
    monkeypatch.setattr(landing, "_monotonic", clock)
    monkeypatch.delenv(guard.CLAUDE_CODE_ANCHOR, raising=False)
    monkeypatch.chdir(tmp_path)

    def install(service: fake.HostingService) -> fake.HostingService:
        monkeypatch.setattr(landing, "gh_runner", lambda cwd: service)
        monkeypatch.setattr(landing, "run_gh", service)
        return service

    return install


@pytest.fixture
def host(serve: Serve) -> fake.HostingService:
    """The hosting service of one pull request, open on a base without a queue."""
    return serve(fake.HostingService())


def _queue(service: fake.HostingService, *, queued: bool = True) -> None:
    service.set_base(fake.Base(queue=True))
    if queued:
        service.in_queue = True
        service.entry = (1, "AWAITING_CHECKS")


def _readings() -> list[landing.Reading]:
    """A reading of each state, method and entry GitHub names, with a removal, PRs
    ahead, a fork's head and a merge's commit among them."""
    removal = landing.Removal("2026-10-01T10:05:00Z", "failed checks", HEAD)
    queued = [
        landing.Reading(
            True,
            "SQUASH",
            "PR_node",
            "OPEN",
            head_oid=HEAD,
            in_queue=True,
            position=2,
            entry_state=state,
            eta_seconds=300,
            ever_queued=True,
            head_ref="fix/42-land-it",
            ahead=(7,),
        )
        for state in sorted(_ENTRY_STATES - {""})
    ]
    return [
        *queued,
        landing.Reading(
            True,
            "MERGE",
            "PR_node",
            "CLOSED",
            head_oid=HEAD,
            ever_queued=True,
            removal=removal,
            cross_repository=True,
        ),
        landing.Reading(True, "REBASE", "PR_node", "OPEN", head_oid=HEAD, waiting_to_enter=True),
        landing.Reading(
            False,
            "",
            "PR_node",
            "MERGED",
            "2026-10-01T10:12:00Z",
            HEAD,
            merge_commit="c" * 40,
        ),
    ]


def _guards() -> tuple[list[guard.Clearance], guard.Refusal]:
    """A clearance in each way the guard lets a change through, and its refusal."""
    here = Path("/work/project")
    there = Path("/work/elsewhere")
    same = guard.Comparison(guard.SAME_REPO, None, here, here, "one repository")
    diverged = guard.Comparison(guard.DIVERGED, None, there, here, "two repositories")
    unanchored = guard.Comparison(guard.UNDETERMINED, guard.NONCOVERAGE, None, None, "no anchor")
    fault = guard.Comparison(guard.UNDETERMINED, guard.FAULT, None, here, "git did not answer")
    cleared = [
        guard.Clearance(here, guard.SAME_REPO, same),
        guard.Clearance(here, guard.FLAG, diverged),
        guard.Clearance(here, guard.TERMINAL, diverged),
        guard.Clearance(here, guard.UNDETERMINED, unanchored),
        guard.Clearance(here, guard.UNDETERMINED, fault),
    ]
    return cleared, guard.Refusal(here, diverged, "another repository; pass the flag")


def _cleared(index: int) -> guard.Clearance:
    cleared, _refusal = _guards()
    return cleared[index % len(cleared)]


def _read_as(monkeypatch: pytest.MonkeyPatch, reading: landing.Reading) -> dict[str, Any]:
    """`read`'s document, the module's reading answering `reading`."""
    monkeypatch.setattr(landing, "read", lambda number, gh=None: reading)
    return landing.reading_document(PR)


def _unreadable(number: int, gh: Any = None) -> landing.Reading:
    raise landing.Unreadable("HTTP 502")


# --- `read` and `squash-defaults` ------------------------------------------------------------


def test_the_reading_documents_hold_their_contract(
    host: fake.HostingService, monkeypatch: pytest.MonkeyPatch
) -> None:
    printed = document_of(invoke("pull-request", "read", PR_ARGUMENT, JSON_OPTION))
    _queue(host)
    queued = document_of(invoke("pull-request", "read", PR_ARGUMENT, JSON_OPTION))
    built = [_read_as(monkeypatch, reading) for reading in _readings()]
    monkeypatch.setattr(landing, "read", _unreadable)
    check(READ, {"answer": [printed, queued, *built, landing.reading_document(PR)]})


def _defaults(title: str, message: str) -> landing.GhRunner:
    answer = {"squash_merge_commit_title": title, "squash_merge_commit_message": message}

    def gh(argv: Sequence[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(list(argv), 0, stdout=json.dumps(answer), stderr="")

    return gh


def test_the_squash_defaults_document_holds_its_contract(host: fake.HostingService) -> None:
    printed = document_of(invoke("pull-request", "squash-defaults", JSON_OPTION))
    named = [
        landing.squash_defaults_document(gh=_defaults(title, message))
        for title, message in zip(sorted(_SQUASH_TITLES), ("COMMIT_MESSAGES", "BLANK"), strict=True)
    ]
    host.squash_defaults = None
    unreadable = document_of(invoke("pull-request", "squash-defaults", JSON_OPTION))
    check(SQUASH_DEFAULTS, {"answer": [printed, *named, unreadable]})


# --- `merge`, `enqueue` and `dequeue` --------------------------------------------------------


def _outcomes(kinds: frozenset[str]) -> Iterator[landing.Outcome]:
    """A request made, refused, and each way it was not made or is not known, but the
    guard's refusal."""
    yield landing.Outcome(True)
    yield landing.Outcome(False, 1, "GraphQL: not mergeable")
    for kind in sorted(kinds - {guard.FOREIGN_REPOSITORY}):
        accepted = None if kind == landing.UNANSWERED else False
        yield landing.Outcome(accepted, None, "what the readings since found", kind)


def _request_documents(kinds: frozenset[str]) -> list[dict[str, Any]]:
    cleared, refusal = _guards()
    built = [
        landing.outcome_document(PR, outcome, clearance)
        for outcome in _outcomes(kinds)
        for clearance in cleared
    ]
    return [*built, landing.refusal_document(PR, refusal)]


def test_the_request_documents_hold_their_contracts(host: fake.HostingService) -> None:
    merged = document_of(
        invoke("pull-request", "merge", PR_ARGUMENT, "--subject", "fix: it", JSON_OPTION)
    )
    check(MERGE, {"answer": [merged, *_request_documents(_REQUEST_KINDS)]})
    _queue(host, queued=False)
    queued = document_of(invoke("pull-request", "enqueue", PR_ARGUMENT, JSON_OPTION))
    check(ENQUEUE, {"answer": [queued, *_request_documents(_REQUEST_KINDS)]})
    dequeued = document_of(invoke("pull-request", "dequeue", PR_ARGUMENT, JSON_OPTION))
    check(DEQUEUE, {"answer": [dequeued, *_request_documents(_DEQUEUE_KINDS)]})


# --- `delete-branch` ---------------------------------------------------------------------


def _deletions() -> Iterator[landing.BranchDeletion]:
    """A branch deleted, gone, and kept, refused or unconfirmed for each reason."""
    yield landing.BranchDeletion(landing.DELETED, "fix/42", merged_head=HEAD)
    yield landing.BranchDeletion(landing.GONE, "fix/42", merged_head=HEAD)
    kept = (
        landing.TIP_MOVED,
        landing.OPEN_PULL_REQUEST,
        landing.DELETION_REFUSED,
        landing.UNANSWERED,
    )
    for kind in kept:
        yield landing.BranchDeletion(landing.KEPT, "fix/42", "t" * 40, kind, "why", HEAD)
    refused = (
        landing.NOT_MERGED,
        landing.CROSS_REPOSITORY,
        landing.EXPECT_MISMATCH,
        landing.NOT_READ,
    )
    for kind in refused:
        yield landing.BranchDeletion(landing.REFUSED, "fix/42", reason_kind=kind, reason="why")
    yield landing.BranchDeletion(
        landing.UNCONFIRMED, "fix/42", reason_kind=landing.UNANSWERED, reason="why"
    )


def test_the_branch_deletion_document_holds_its_contract(host: fake.HostingService) -> None:
    host.merge_now()
    printed = document_of(
        invoke("pull-request", "delete-branch", PR_ARGUMENT, "--expect", HEAD, JSON_OPTION)
    )
    _cleared_all, refusal = _guards()
    built = [
        landing.deletion_document(PR, HEAD, deletion, _cleared(index))
        for index, deletion in enumerate(_deletions())
    ]
    refused = landing.deletion_refusal_document(PR, HEAD, refusal)
    check(DELETE_BRANCH, {"answer": [printed, *built, refused]})


# --- `wait` --------------------------------------------------------------------------------


def _by_event(documents: Sequence[Mapping[str, Any]]) -> dict[str, list[Mapping[str, Any]]]:
    found: dict[str, list[Mapping[str, Any]]] = {}
    for document in documents:
        found.setdefault(str(document["event"]), []).append(document)
    return found


def test_the_wait_documents_hold_their_contract(host: fake.HostingService) -> None:
    _queue(host)
    host.progress = [fake.at(1), fake.lands()]
    printed = documents_of(invoke("pull-request", "wait", PR_ARGUMENT, "--head", HEAD, JSON_OPTION))
    readings = _readings()
    built = [landing.wait_reading_document(PR, reading) for reading in readings]
    built += [
        landing.wait_end_document(PR, landing.Wait(ended, reading))
        for ended, reading in zip(
            (landing.MERGED, landing.STILL_QUEUED, landing.LEFT, landing.HEAD_MOVED),
            readings,
            strict=False,
        )
    ]
    built.append(landing.wait_end_document(PR, None, "HTTP 502"))
    check(WAIT, _by_event([*printed, *built]))


# --- `land` --------------------------------------------------------------------------------


def _land(*args: str) -> list[dict[str, Any]]:
    return documents_of(
        invoke(
            "pull-request",
            "land",
            PR_ARGUMENT,
            "--head",
            HEAD,
            "--subject",
            "fix: land it",
            *args,
            JSON_OPTION,
        )
    )


def _ends() -> Iterator[landing.Landing]:
    """A landing's end of each kind, with each reason it carries and a request it sent;
    planned for each thing it would do; with a dequeue, a shape and every warning; and
    refused by the guard, nothing read."""
    readings = _readings()
    merged = readings[-1]
    queued = readings[0]
    warnings = tuple(landing.Notice(kind, "why") for kind in sorted(_WARNINGS))
    shape = landing.Shape(True, "PR_TITLE", "PR_BODY", True)
    for index, ((ended, kind), sents) in enumerate(sorted(landing.LANDING_SENT.items(), key=str)):
        sent = next((name for name in sorted(sents, key=str) if name is not None), None)
        quiet = ended in (landing.END_MERGED, landing.END_PLANNED)
        yield landing.Landing(
            PR,
            ended,
            HEAD,
            _cleared(index),
            932.0,
            reason_kind=kind,
            reason=None if quiet else "why",
            would=landing.WAIT if ended == landing.END_PLANNED else None,
            reading=merged if ended in _MERGED_ENDS else queued,
            sent=sent,
        )
    for would in (landing.MERGE_REQUEST, landing.ENQUEUE_REQUEST, landing.DEQUEUE_REQUEST):
        yield landing.Landing(
            PR,
            landing.END_PLANNED,
            HEAD,
            _cleared(0),
            98.0,
            dry_run=True,
            would=would,
            reading=queued,
            shape=landing.Shape(True, "COMMIT_OR_PR_TITLE", "BLANK", False),
            warnings=warnings,
        )
    dequeues = list(_outcomes(_DEQUEUE_KINDS))
    for index, reading in enumerate(readings):
        dequeue = dequeues[index % len(dequeues)]
        yield landing.Landing(
            PR,
            landing.END_HEAD_MOVED,
            HEAD,
            _cleared(index),
            932.0,
            reason="the head moved",
            reading=reading,
            sent=landing.ENQUEUE_REQUEST,
            dequeue=dequeue,
            shape=landing.Shape(False, None, "COMMIT_MESSAGES", None, "no access"),
        )
    yield landing.Landing(
        PR,
        landing.END_MERGED,
        HEAD,
        _cleared(1),
        932.0,
        reading=readings[-1],
        shape=shape,
    )
    _cleared_all, refusal = _guards()
    yield landing.Landing(
        PR,
        landing.END_REFUSED,
        HEAD,
        refusal,
        932.0,
        reason_kind=guard.FOREIGN_REPOSITORY,
        reason=refusal.reason,
    )


def test_the_landing_documents_hold_their_contract(serve: Serve) -> None:
    serve(fake.HostingService())
    direct = _land()
    enqueued = serve(fake.HostingService())
    _queue(enqueued, queued=False)
    enqueued.progress = [fake.at(1), fake.lands()]
    queued = _land()
    moved = serve(fake.HostingService())
    _queue(moved)
    moved.push(fake.oid("pushed"))
    head_moved = _land()
    built = [end.as_json() for end in _ends()]
    check(
        LAND,
        _by_event([*direct, *queued, *head_moved, *built]),
        enumerations={
            "ended": landing.LANDING_ENDS,
            "reason_kind": (
                kind for kinds in landing.LANDING_ENDS.values() for kind in kinds if kind
            ),
            "warnings[].reason_kind": landing.LANDING_WARNINGS,
        },
    )


#: The contracts of each `pkit pull-request` command, by the command's words.
CONTRACTS: Mapping[str, tuple[Contract, ...]] = {
    "pull-request read": (READ,),
    "pull-request squash-defaults": (SQUASH_DEFAULTS,),
    "pull-request merge": (MERGE,),
    "pull-request enqueue": (ENQUEUE,),
    "pull-request dequeue": (DEQUEUE,),
    "pull-request delete-branch": (DELETE_BRANCH,),
    "pull-request wait": (WAIT,),
    "pull-request land": (LAND,),
}
