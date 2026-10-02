"""The end documents of `pkit pull-request land`, valid and not: one table
that every decoder of the end is tested against — the backbone's
`pull_request_landing.decode_end`, and project-management's once its verbs
land through the command (#1220).

The values are written out here, not taken from the landing module, so the
table is an oracle of its own: a change to what the module states or accepts
shows as a failing case, not as a table that moved with it.

- :data:`ENDED` — each `ended`, with the `reason_kind`s it carries (`None`
  where the kind alone says it).
- :data:`VALID` — each (`ended`, `reason_kind`, `sent`) a landing can end
  with; :func:`document` builds the end document of one, every key in it.
- :data:`VALID_DOCUMENTS` — a valid document of each, and of the shapes a
  triple does not name: a head that moved with each thing taking the PR out
  came to, a dry run, a reading that names no head.
- :data:`INVALID_DOCUMENTS` — documents that are no end document, each with
  why.
"""

from __future__ import annotations

import hashlib
from typing import Any

MERGE = "merge"
ENQUEUE = "enqueue"

#: Every way a landing ends, with the `reason_kind`s it carries.
ENDED: dict[str, frozenset[str | None]] = {
    "merged": frozenset({None}),
    "merged-at-another-head": frozenset({None}),
    "closed": frozenset({None}),
    "planned": frozenset({None}),
    "queued": frozenset({None, "unreadable"}),
    "unconfirmed": frozenset({"unanswered", "unreadable"}),
    "head-moved": frozenset({None}),
    "dropped": frozenset({None}),
    "not-merged": frozenset({None}),
    "failed": frozenset({None, "not-made"}),
    "refused": frozenset(
        {
            "foreign-repository",
            "request-not-allowed",
            "admin-on-queue",
            "queue-not-allowed",
            "queue-not-squash",
            "dropped-head",
            "squash-defaults",
        }
    ),
    "unreadable": frozenset({None, "squash-defaults"}),
}

#: Every `reason_kind` any end carries, and `None`.
REASON_KINDS: frozenset[str | None] = frozenset().union(*ENDED.values())

#: What `sent` can say: nothing, a merge, an enqueue.
SENT: tuple[str | None, ...] = (None, MERGE, ENQUEUE)

_ANY = SENT
_NONE: tuple[str | None, ...] = (None,)

#: The request each end can state as `sent`, by `ended` and `reason_kind`.
_SENT_BY_END: dict[tuple[str, str | None], tuple[str | None, ...]] = {
    # A reading says merged: after a merge or an enqueue this run sent, or
    # with none — found merged, or found queued and waited for.
    ("merged", None): _ANY,
    ("merged-at-another-head", None): _ANY,
    # The first reading only, so nothing was sent.
    ("closed", None): _NONE,
    ("planned", None): _NONE,
    # The time ran out: found queued, enqueued, or a direct merge the
    # service queued instead.
    ("queued", None): _ANY,
    # A lost wait reading after an enqueue, or on a PR found queued.
    ("queued", "unreadable"): (None, ENQUEUE),
    # No usable answer, and no reading since.
    ("unconfirmed", "unanswered"): (MERGE, ENQUEUE),
    # A lost wait reading after a direct merge; or a reading that says
    # merged and names no head, whatever was sent.
    ("unconfirmed", "unreadable"): _ANY,
    ("head-moved", None): _ANY,
    ("dropped", None): _ANY,
    # Out on two readings with no queue seen: after a direct merge, or —
    # the base having lost its queue during the wait — an enqueue or none.
    ("not-merged", None): _ANY,
    # Refused on an answer, so nothing the service did not refuse.
    ("failed", None): _NONE,
    # Not seen made on two readings: sent.
    ("failed", "not-made"): (MERGE, ENQUEUE),
    **{("refused", kind): _NONE for kind in ENDED["refused"]},
    ("unreadable", None): _NONE,
    ("unreadable", "squash-defaults"): _NONE,
}

#: Every (`ended`, `reason_kind`, `sent`) a landing can end with.
VALID: frozenset[tuple[str, str | None, str | None]] = frozenset(
    (ended, kind, sent) for (ended, kind), sents in _SENT_BY_END.items() for sent in sents
)

HEAD = hashlib.sha1(b"head").hexdigest()
OTHER = hashlib.sha1(b"other").hexdigest()
MERGE_COMMIT = "c0ffee" + "0" * 34

_MERGED_ENDS = ("merged", "merged-at-another-head")
_REASONLESS = ("merged", "planned")

_GUARD = {
    "verdict": "same-repo",
    "undetermined_kind": None,
    "anchor": "/repo",
    "target": "/repo",
    "cleared": "same-repo",
}
_GUARD_REFUSED = {**_GUARD, "verdict": "diverged", "anchor": "/elsewhere", "cleared": None}


def reading(*, state: str = "OPEN", head: str = HEAD, merged: bool = False) -> dict[str, Any]:
    """A reading as `pkit pull-request read` states it."""
    return {
        "has_queue": False,
        "merge_method": "",
        "pr_id": "PR_node",
        "pr_state": state,
        "merged_at": "2026-10-01T10:12:00Z" if merged else "",
        "head_oid": head,
        "in_queue": False,
        "position": None,
        "entry_state": "",
        "eta_seconds": None,
        "waiting_to_enter": False,
        "ever_queued": False,
        "removal": None,
        "head_ref": "fix/42-land-it",
        "cross_repository": False,
        "merge_commit": MERGE_COMMIT if merged else "",
        "merged": merged,
        "queued": False,
        "squashes": False,
        "dropped_head": False,
        "description": "merged" if merged else "not in the queue",
    }


def document(
    ended: str, reason_kind: str | None = None, sent: str | None = None, /, **changes: Any
) -> dict[str, Any]:
    """The end document of a landing that ends `ended`, `reason_kind`,
    having sent `sent`, every key in it — with `changes` over it, any key
    among them."""
    nothing_read = (ended, reason_kind) in (("refused", "foreign-repository"), ("unreadable", None))
    merged_head = {"merged": HEAD, "merged-at-another-head": OTHER}.get(ended)
    state = "MERGED" if ended in _MERGED_ENDS else "CLOSED" if ended == "closed" else "OPEN"
    head = OTHER if ended in ("merged-at-another-head", "head-moved") else HEAD
    taken = reading(state=state, head=head, merged=ended in _MERGED_ENDS)
    end: dict[str, Any] = {
        "schema_version": 1,
        "pull_request": 496,
        "event": "end",
        "dry_run": ended == "planned",
        "ended": ended,
        "reason_kind": reason_kind,
        "reason": None if ended in _REASONLESS else f"why the landing ended {ended}",
        "would": MERGE if ended == "planned" else None,
        "path": None if nothing_read else "direct",
        "checked_head": HEAD,
        "merged_head": merged_head,
        "merge_commit": MERGE_COMMIT if merged_head else None,
        "sent": sent,
        "dequeue": None,
        "reading": None if nothing_read else taken,
        "shape": None,
        "warnings": [],
        "guard": _GUARD_REFUSED if reason_kind == "foreign-repository" else _GUARD,
        "bound_seconds": 2732.0,
    }
    return {**end, **changes}


def _dequeue(
    accepted: object, exit_code: object, reason: object, reason_kind: object
) -> dict[str, Any]:
    """What taking the PR out of the queue came to, as `pkit pull-request
    dequeue` states it — or, in the invalid cases, does not."""
    return {
        "accepted": accepted,
        "exit_code": exit_code,
        "reason": reason,
        "reason_kind": reason_kind,
    }


#: A valid end document of each triple, and of the shapes no triple names.
VALID_DOCUMENTS: tuple[tuple[str, dict[str, Any]], ...] = (
    *(
        (f"{ended} {kind} sent={sent}", document(ended, kind, sent))
        for ended, kind, sent in sorted(VALID, key=str)
    ),
    *(
        (f"head-moved, its dequeue {why}", document("head-moved", None, ENQUEUE, dequeue=out))
        for why, out in (
            ("taken out", _dequeue(True, 0, "", None)),
            ("already out", _dequeue(True, None, "", None)),
            ("unconfirmed", _dequeue(None, None, "no usable answer", "unanswered")),
            ("merged meanwhile", _dequeue(False, None, "PR #496 has merged", "merged")),
            ("refused", _dequeue(False, 1, "GraphQL: Something went wrong", None)),
            ("not read", _dequeue(False, None, "PR #496 could not be read", "unreadable")),
        )
    ),
    *(
        (f"planned, would {would}", document("planned", would=would))
        for would in ("merge", "enqueue", "wait", "dequeue")
    ),
    ("a dry run refused", document("refused", "dropped-head", dry_run=True)),
    ("a dry run the guard refused", document("refused", "foreign-repository", dry_run=True)),
    (
        "unreadable, the first reading naming no head",
        document("unreadable", None, reading=reading(head=""), path="direct"),
    ),
    ("a whole number of seconds", document("merged", bound_seconds=932)),
    (
        "merged with a warning",
        document(
            "merged", None, MERGE, warnings=[{"reason_kind": "unreadable", "reason": "HTTP 502"}]
        ),
    ),
)

#: Documents that are no end document, each with why.
INVALID_DOCUMENTS: tuple[tuple[str, object], ...] = (
    ("not a document", ["merged"]),
    ("a key missing", {k: v for k, v in document("merged").items() if k != "sent"}),
    ("another version", document("merged", schema_version=2)),
    ("not an end", document("merged", event="reading")),
    ("an `ended` no landing has", document("merged", ended="landed")),
    ("no `ended`", document("merged", ended=None)),
    ("a `reason_kind` its end does not carry", document("queued", "not-made")),
    ("a refusal with no `reason_kind`", document("refused", None)),
    ("a `dry_run` that is not a boolean", document("merged", dry_run="false")),
    ("planned and not a dry run", document("planned", dry_run=False)),
    ("an abbreviated `checked_head`", document("merged", checked_head=HEAD[:7])),
    ("an upper-case `checked_head`", document("merged", checked_head=HEAD.upper())),
    ("no `checked_head`", document("merged", checked_head=None)),
    ("`bound_seconds` in words", document("merged", bound_seconds="2732")),
    ("`bound_seconds` a boolean", document("merged", bound_seconds=True)),
    ("a reason on a merged end", document("merged", reason="merged")),
    ("a reason on a planned end", document("planned", reason="it would merge")),
    ("no reason on a closed end", document("closed", reason=None)),
    ("an empty reason on a failed end", document("failed", reason="")),
    ("no reason where it merged at another head", document("merged-at-another-head", reason=None)),
    ("`would` on an end that is not planned", document("closed", would="merge")),
    ("planned with nothing it would do", document("planned", would=None)),
    ("planned to do what no landing does", document("planned", would="delete-branch")),
    ("merged and naming no `merged_head`", document("merged", merged_head=None)),
    ("merged and naming an empty `merged_head`", document("merged", merged_head="")),
    ("a `merged_head` where it did not merge", document("closed", merged_head=HEAD)),
    ("a request sent where none can be", document("closed", None, MERGE)),
    ("a request a landing never sends", document("merged", None, "dequeue")),
    ("unconfirmed with nothing sent", document("unconfirmed", "unanswered", None)),
    ("failed on a refusal, yet sent", document("failed", None, ENQUEUE)),
    ("not seen made, and nothing sent", document("failed", "not-made", None)),
    ("refused, yet sent", document("refused", "dropped-head", ENQUEUE)),
    ("queued after a lost reading, a merge sent", document("queued", "unreadable", MERGE)),
    ("a dequeue on an end that ran none", document("merged", dequeue=_dequeue(True, 0, "", None))),
    (
        "a dequeue missing a key",
        document("head-moved", dequeue={"accepted": True, "exit_code": 0, "reason": ""}),
    ),
    (
        "a dequeue with a key it does not have",
        document("head-moved", dequeue={**_dequeue(True, 0, "", None), "outcome": "out"}),
    ),
    (
        "a dequeue accepted in words",
        document("head-moved", dequeue=_dequeue("yes", 0, "", None)),
    ),
    (
        "a dequeue accepted as a number",
        document("head-moved", dequeue=_dequeue(1, 0, "", None)),
    ),
    (
        "a dequeue exit code that is a boolean",
        document("head-moved", dequeue=_dequeue(True, True, "", None)),
    ),
    (
        "a dequeue with no reason",
        document("head-moved", dequeue=_dequeue(True, 0, None, None)),
    ),
    (
        "a dequeue reason kind that is a number",
        document("head-moved", dequeue=_dequeue(False, 1, "", 7)),
    ),
    ("a dequeue that is not a document", document("head-moved", dequeue="taken out")),
    ("merged, naming no reading", document("merged", reading=None)),
    ("refused after a reading, naming none", document("refused", "dropped-head", reading=None)),
    (
        "refused by the guard, yet naming a reading",
        document("refused", "foreign-repository", reading=reading()),
    ),
    ("a reading that is not a document", document("closed", reading="closed")),
    ("`warnings` that are not a list", document("merged", warnings=None)),
    ("a `guard` that is not a document", document("merged", guard=None)),
)
