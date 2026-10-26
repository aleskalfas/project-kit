"""The instance-ownership marker seam — one read fold, one construction point
per write, two selectable substrates (ADR-041 / DEC-043 / DEC-035).

DEC-035 records which of one person's concurrent clones owns an issue. DEC-043
made the marker's substrate **selectable**: an ``instance:N`` GitHub *label* where
labels are creatable, and — where they are not — a **label-free** substrate that
is the subject of this module: an append-only log of ownership *events* (claim /
handoff / abandon / release) posted as issue comments (the source of truth), plus
a derived, regenerable **owner-mirror** in the issue description. The formal
contract this module realises is [pkit:ADR-041].

Two halves, mirroring ``_lib/containment.py``:

Read fold (the one resolver)
----------------------------
:func:`resolve_owner` is the single seam that answers "who owns this issue now,
and via which substrate?" It folds the per-instance append-only event log to the
current owner and, over a repo that carries *both* a lingering ``instance:N``
label and a comment-log marker, resolves **comment-log-wins** (ADR-041 §2). Every
pm-layer consumer — the DEC-035 clash guard, the signed listing, and the
description-mirror renderer — resolves through this function; none re-scans
comments itself (ADR-026's one-reader discipline, applied to the ownership axis).

The fold is **authenticity-filtered**: a marker comment is trusted only if it was
authored by the issue's expected assignee account (``author.login``) — a pasted
forgery from another account is ignored (DEC-043 D3). The same-instant clash
(DEC-035 D6) resolves **lowest-instance-wins**, computed identically from the
folded set by every clone; comment-create is per-object-atomic, so two concurrent
claims coexist as two markers rather than clobbering (the property a single
mutable comment or a whole-body region could not provide — DEC-043 rejected both).

The log is read whole through the shared reader (:func:`read_log`, the one
``_lib/comment_log`` the state-issue seam reads its logs with), and its events
are parsed by the audit-log facility (``_lib/audit_log``, DEC-044). The fold
takes the events in the order of their comments, which is the order of their ids.
It reads the stamps written before the facility as well (``pkit:instance-owner
v=1``), so an issue claimed under them keeps its owner (DEC-059 Implications).

Write construction (one point per side)
---------------------------------------
Two sole-constructors, each the *only* place its write is built (ADR-041 §3):

  * :func:`ownership_event_comment_args` — the ownership-event comment (claim /
    handoff / abandon / release). The audit-log facility builds its body: the
    stamp, a line a person reads and DEC-052's frame. In a project with a
    topology the event names the seat, the seat's number and the clone's key
    (ADR-041 point 7). Every ownership mutation obtains its event write only here.
  * :func:`render_mirror_body` — regenerates the derived owner-mirror region in the
    issue body by **full overwrite** from the folded resolution (never an append;
    the region is derived, the comment log is its regeneration spine — ADR-041 §4).

The label backend's add/remove (:func:`instance_label_args`) and its lazy
creation (:func:`instance_label_create_args`) are the other covered writes, kept
for the ``label`` selector (DEC-035's original mechanism).

When each write fires — the claim at filing and at start-work, the same-instant
back-off, the release on close — is ``_lib/instance_claims``'s, the lifecycle
side of DEC-035.

A project with a topology of seats (ADR-041 point 7)
----------------------------------------------------
In a project with a topology (DEC-059), every claim names the claimant's seat,
the seat's number and the clone's key, in the audit-log facility's stamp. The
fold then takes each seat's holder from its caller, as :class:`Holder`, and reads
no other seam: a claim counts only while the clone it names holds the seat it
names, judged when it is read. A claim that names no seat does not count, and a
claim whose seat was not read cannot be judged, which no consumer treats as free.
Renewal and lapse are not judged yet.

Realm-blindness (ADR-041 §6)
----------------------------
This seam feeds **only** the pm-layer guard, listing, and mirror. It is never an
input to a gate, a transition, or the DEC-034 cascade fold — the deliberate
inverse of ``containment.py``, whose read seam *is* a closure-fold consumer.

Failure-posture neutrality (ADR-041 §5)
---------------------------------------
Constructors build/execute and report a neutral outcome; the caller (claim vs.
back-off vs. durability-check vs. routine render) imposes its own posture. This
module owns the ``gh`` argv construction, the stamp format, the fold, and the
mirror render; it takes no view on what a race or a clobber *means*.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

# Sibling helpers, imported with the defensive fallback the other _lib seams use
# for file-path test loads: the gh helper (DEC-023 host/owner pinning), the
# audit-log facility's builder and parser, and the shared reader of a log.
try:
    from gh import gh_run  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover
    try:
        from _lib.gh import gh_run  # type: ignore[no-redef]
    except ImportError:  # pragma: no cover
        gh_run = None  # type: ignore[assignment]
try:
    from _lib import audit_log, comment_log
except ImportError:  # pragma: no cover - a test that puts `_lib` itself on the path
    import audit_log  # type: ignore[no-redef]
    import comment_log  # type: ignore[no-redef]


# ---- vocabulary ---------------------------------------------------------

#: The ownership event types carried by the append-only comment log (DEC-043 D3).
#: ``claim`` and ``handoff`` assert ownership; ``abandon`` / ``release`` relinquish
#: it. The fold reads them in the order of their comments.
EVENTS = audit_log.OWNERSHIP_EVENTS

#: Substrate selector values (DEC-043 D2). ``comment`` is the default (safe where
#: labels cannot be created); ``label`` is the opt-in for repos that can.
SUBSTRATES = ("comment", "label")
DEFAULT_SUBSTRATE = "comment"

# The derived owner-mirror region in the issue body — a fenced, do-not-edit block
# the read seam regenerates by full overwrite (ADR-041 §4; the DEC-009 derived-
# region class). Its content is never authoritative; the comment log is.
MIRROR_BEGIN = "<!-- pkit:instance-owner-mirror:begin -->"
MIRROR_END = "<!-- pkit:instance-owner-mirror:end -->"
_MIRROR_RE = re.compile(
    re.escape(MIRROR_BEGIN) + r".*?" + re.escape(MIRROR_END),
    re.DOTALL,
)


# ---- data carriers ------------------------------------------------------


@dataclass(frozen=True)
class OwnershipEvent:
    """One parsed, authenticated ownership event from the comment log.

    ``instance`` is the acting clone's number; ``to`` is the target on a handoff.
    ``assignee`` is the comment's ``author.login`` (the owning account — the
    ``(assignee, instance)`` pair's first half). ``ts`` is GitHub's time of the
    comment, where the comment carries it, or the time an old stamp holds; the
    fold orders by the comments, never by ``ts``. ``seat``, ``seat_number`` and
    ``clone`` are what a claim names in a project with a topology (ADR-041 point
    7), and ``act`` the id of the act. ``legacy`` marks an old stamp.
    Content-free about what the event *means* for the guard — that is the
    caller's posture.
    """

    event: str
    instance: int
    assignee: str
    ts: datetime | None = None
    to: int | None = None
    seat: str | None = None
    seat_number: int | None = None
    clone: str | None = None
    act: str | None = None
    legacy: bool = False


# ---- a project with a topology of seats (ADR-041 point 7) ---------------------

#: What a seat's state issue says of it, as the fold's caller read it.
SEAT_HELD = "held"
SEAT_FREE = "free"
SEAT_UNREAD = "unread"

#: How a claim is judged in a project with a topology: it counts, it does not
#: (it is void), or it cannot be judged, which no consumer treats as free.
COUNTS = "counts"
VOID = "void"
UNJUDGED = "unjudged"

#: Why a claim is void, or cannot be judged.
NO_SEAT = "it names no seat"
SEAT_RELEASED = "its clone no longer holds its seat"
SEAT_UNREAD_REASON = "its seat's holder could not be read"
SEAT_NOT_READ = "its seat is not among the seats read"


@dataclass(frozen=True)
class Holder:
    """Who holds one seat, as the caller read it from the seat's state issue
    (ADR-041 point 7): a clone, by its account and key, or free, or unread."""

    state: str
    login: str | None = None
    clone: str | None = None


@dataclass(frozen=True)
class ClaimJudgement:
    """How the fold judged one instance's claim in a project with a topology:
    the claim's seat, its clone's key, the verdict, and why where it is not
    ``COUNTS``."""

    instance: int
    seat: str | None
    clone: str | None
    verdict: str
    reason: str | None = None


@dataclass(frozen=True)
class OwnershipResolution:
    """The folded current ownership of one issue — the seam's return.

    ``owners`` is the set of currently-owning instance numbers (normally one;
    two-plus only in the same-instant-clash window before back-off). ``winner`` is
    the lowest-numbered owner (DEC-035 D6 lowest-wins), or ``None`` when the issue
    is unclaimed (a *commons* issue — the DEC-045 unassigned fallback and DEC-035
    ``start-work`` claim target). ``substrate`` records which substrate resolved
    the owner (``comment`` wins over a lingering ``label`` — ADR-041 §2).

    In a project with a topology, ``owners`` holds only the claims that count,
    and ``judgements`` says how each claim was judged (ADR-041 point 7).
    """

    assignee: str | None
    owners: frozenset[int]
    substrate: str | None
    events: tuple[OwnershipEvent, ...] = field(default_factory=tuple)
    judgements: tuple[ClaimJudgement, ...] = field(default_factory=tuple)

    @property
    def winner(self) -> int | None:
        return min(self.owners) if self.owners else None

    @property
    def claimed(self) -> bool:
        return bool(self.owners)

    @property
    def unjudged(self) -> tuple[ClaimJudgement, ...]:
        """The claims the fold could not judge (ADR-041 point 7)."""
        return tuple(j for j in self.judgements if j.verdict == UNJUDGED)

    @property
    def claimants(self) -> frozenset[int]:
        """Every instance whose claim counts or cannot be judged: no consumer
        treats such an issue as free (ADR-041 point 5)."""
        return self.owners | {j.instance for j in self.unjudged}

    def judgement(self, instance: int) -> ClaimJudgement | None:
        """How ``instance``'s claim was judged, or None where no topology is."""
        return next((j for j in self.judgements if j.instance == instance), None)


# ---- the log and its events ---------------------------------------------


def read_log(issue_number: int, gh: comment_log.Gh) -> comment_log.LogRead:
    """The issue's whole comment log, through the reader both seams share.

    A fold reads the log whole, paged to its end, and never the comments a
    listing returns, which may be cut short (ADR-041 point 1). ``gh`` runs one
    call; the caller's posture decides what an incomplete read means.
    """
    return comment_log.read_log(issue_number, gh)


def _parse_ts(raw: str | None) -> datetime | None:
    """Parse an ISO-8601 time; tolerate a trailing ``Z``. None when absent or
    unreadable."""
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def _field(comment: Any, name: str) -> Any:
    if isinstance(comment, dict):
        return comment.get(name)
    return getattr(comment, name, None)


def _author_of(comment: Any) -> str:
    """The comment's author: a log comment's ``author``, or the ``author`` /
    ``user`` login of a comment as ``gh`` returns it."""
    if isinstance(comment, dict):
        for key in ("author", "user"):
            who = comment.get(key)
            if isinstance(who, dict) and who.get("login"):
                return str(who["login"])
        return ""
    return str(getattr(comment, "author", "") or "")


def _created_at(comment: Any) -> str | None:
    for name in ("created_at", "createdAt"):
        value = _field(comment, name)
        if value:
            return str(value)
    return None


def _int(value: str | None) -> int | None:
    """The number ``value`` holds, ASCII digits of bounded length, or None, so
    no text a comment carries can make the fold fail."""
    if value is None or not re.fullmatch(r"[0-9]{1,9}", value):
        return None
    return int(value)


def parse_events(comments: Iterable[Any], assignee_login: str | None) -> list[OwnershipEvent]:
    """Extract authenticated ownership events from an issue's comments.

    ``comments`` are the log's (:func:`read_log`) or ``gh``'s comment entries.
    The authenticity filter (ADR-041 §1 / DEC-043 D3): a stamped comment counts
    **only** if its author equals the issue's expected ``assignee_login`` — a
    forged stamp pasted from another account is ignored. With no assignee
    (``None``), no marker authenticates, so the issue reads as unclaimed. Returned
    in the order of the comments, which GitHub lists in the order of their ids.
    """
    out: list[OwnershipEvent] = []
    if not assignee_login:
        return out
    for c in comments:
        author = _author_of(c)
        if author != assignee_login:
            continue  # forgery / another account — not trusted
        ev = audit_log.parse(str(_field(c, "body") or ""))
        if ev is None or ev.type not in EVENTS:
            continue
        instance = _int(ev.get("instance"))
        if instance is None:
            continue
        out.append(
            OwnershipEvent(
                event=ev.type,
                instance=instance,
                assignee=author,
                ts=_parse_ts(ev.get("ts") if ev.legacy else _created_at(c)),
                to=_int(ev.get("to")),
                seat=ev.get("seat"),
                seat_number=_int(ev.get("seat_number")),
                clone=ev.get("clone"),
                act=ev.act,
                legacy=ev.legacy,
            )
        )
    return out


# ---- the read fold seam -------------------------------------------------


def fold_events(events: list[OwnershipEvent]) -> frozenset[int]:
    """Fold the append-only event log to the set of currently-owning instances.

    Per-instance semantics: a ``claim`` (or a ``handoff to=N``) adds an owner; an
    ``abandon`` / ``release`` by an instance (or a ``handoff`` *away* from it)
    removes it. Replaying in the order of the comments yields the live owner set —
    normally a singleton, two-plus only in the same-instant clash window (both
    claimants' markers coexist because comment-create is atomic; DEC-035 D6). The
    caller reads :attr:`OwnershipResolution.winner` for the lowest-wins tie-break.
    """
    return frozenset(_owning_events(events))


def _owning_events(events: list[OwnershipEvent]) -> dict[int, OwnershipEvent]:
    """Each owning instance, with the event that made it the owner: its claim,
    or the handoff to it, which names the target's seat and key (ADR-041
    point 7)."""
    owners: dict[int, OwnershipEvent] = {}
    for e in events:
        if e.event == "claim":
            owners[e.instance] = e
        elif e.event == "handoff":
            owners.pop(e.instance, None)
            if e.to is not None:
                owners[e.to] = e
        elif e.event in ("abandon", "release"):
            owners.pop(e.instance, None)
    return owners


def judge_claim(
    instance: int, event: OwnershipEvent, holders: Mapping[str, Holder]
) -> ClaimJudgement:
    """Judge ``instance``'s claim, made by ``event``, against the seats' holders
    (ADR-041 point 7).

    It counts only while the clone it names holds the seat it names: the seat's
    holder has the claim's key, and its account where the holder names one. A
    claim that names no seat, or whose seat is free or held by another clone, is
    void. A seat that is unread, or not among the holders, leaves it unjudged."""
    if not event.seat:
        return ClaimJudgement(instance, None, event.clone, VOID, NO_SEAT)
    holder = holders.get(event.seat)
    if holder is None:
        return ClaimJudgement(instance, event.seat, event.clone, UNJUDGED, SEAT_NOT_READ)
    if holder.state == SEAT_UNREAD:
        return ClaimJudgement(instance, event.seat, event.clone, UNJUDGED, SEAT_UNREAD_REASON)
    same_account = holder.login is None or holder.login == event.assignee
    if holder.state == SEAT_HELD and holder.clone == event.clone and same_account:
        return ClaimJudgement(instance, event.seat, event.clone, COUNTS)
    return ClaimJudgement(instance, event.seat, event.clone, VOID, SEAT_RELEASED)


def _resolve_with_seats(
    comments: Iterable[Any],
    labels: Iterable[dict[str, Any] | str],
    assignee_login: str | None,
    holders: Mapping[str, Holder],
) -> OwnershipResolution:
    """The fold in a project with a topology (ADR-041 point 7): each owner
    judged against the seats' holders. A label names no seat, so a label owner
    with no comment marker is void."""
    events = parse_events(comments, assignee_login)
    owning = _owning_events(events)
    judgements = [judge_claim(n, owning[n], holders) for n in sorted(owning)]
    judgements += [
        ClaimJudgement(n, None, None, VOID, NO_SEAT)
        for n in sorted(_label_owners(labels) - set(owning))
    ]
    owners = frozenset(j.instance for j in judgements if j.verdict == COUNTS)
    return OwnershipResolution(
        assignee=assignee_login if owners else None,
        owners=owners,
        substrate="comment" if owners else None,
        events=tuple(events),
        judgements=tuple(judgements),
    )


def _label_owners(labels: Iterable[dict[str, Any] | str]) -> frozenset[int]:
    """Instance numbers carried by ``instance:N`` labels (the label backend)."""
    out: set[int] = set()
    for lab in labels:
        name = lab if isinstance(lab, str) else (lab.get("name") or "")
        m = re.fullmatch(r"instance:(\d+)", name)
        if m:
            out.add(int(m.group(1)))
    return frozenset(out)


def resolve_owner(
    *,
    comments: Iterable[Any],
    labels: Iterable[dict[str, Any] | str],
    assignee_login: str | None,
    selector: str = DEFAULT_SUBSTRATE,
    holders: Mapping[str, Holder] | None = None,
) -> OwnershipResolution:
    """The one seam: resolve an issue's current owner, comment-log-wins on a mix.

    Consumers (clash guard, signed listing, mirror renderer) call *this*, never a
    private comment scan. Resolution (ADR-041 §2):

      * fold the authenticated comment event log → comment-log owner set;
      * if that set is non-empty it is authoritative (``substrate='comment'``) and
        any coexisting ``instance:N`` label is treated as **residual** — the
        comment-log-wins invariant over the label→comment forward-switch union;
      * else fall back to the label owner set (``substrate='label'``), i.e. either a
        ``label``-selector repo or a comment-mode repo not yet claimed via a marker.

    ``holders`` is each seat's holder, which the caller passes in a project with
    a topology: the comment log is then the substrate, and each owner is judged
    against the holders (ADR-041 point 7).

    Returns an :class:`OwnershipResolution`; an empty ``owners`` means *commons*
    (unclaimed) — the DEC-035 ``start-work`` claim target and the DEC-045
    unassigned-workstream fallback.
    """
    if holders is not None:
        return _resolve_with_seats(comments, labels, assignee_login, holders)
    events = parse_events(comments, assignee_login)
    comment_owners = fold_events(events)
    label_owners = _label_owners(labels)
    # The selector picks which substrate is primary. `comment` mode (default) is
    # comment-log-wins — the label→comment forward-switch union where a lingering
    # `instance:N` label is residual (ADR-041 §2). `label` mode is the symmetric
    # case: the label is authoritative and a stray comment marker is the residual.
    if selector == "label":
        primary, primary_sub = label_owners, "label"
        secondary, secondary_sub = comment_owners, "comment"
    else:
        primary, primary_sub = comment_owners, "comment"
        secondary, secondary_sub = label_owners, "label"
    if primary:
        owners, substrate = primary, primary_sub
    elif secondary:
        owners, substrate = secondary, secondary_sub
    else:
        owners, substrate = frozenset(), None
    return OwnershipResolution(
        assignee=assignee_login if owners else None,
        owners=owners,
        substrate=substrate,
        events=tuple(events),
    )


# ---- comment-event sole-constructor (comment backend) -------------------


def ownership_event(
    *,
    event: str,
    instance: int,
    to: int | None = None,
    name: str | None = None,
    seat: str | None = None,
    seat_number: int | None = None,
    clone: str | None = None,
    act: str | None = None,
) -> audit_log.Event:
    """The ownership event, as the audit-log facility records it (DEC-044).

    ``name`` is the optional DEC-045 display name, shown for a person. In a
    project with a topology, ``seat``, ``seat_number`` and ``clone`` name the
    claim's seat, its number and the clone's key; a handoff names those of the
    instance it goes to (ADR-041 point 7). ``act`` is the id the caller made once
    for this act, so a retry finds the comment it already posted; the facility
    makes one where none is passed. ``ValueError`` on an unknown event.
    """
    if event not in EVENTS:
        raise ValueError(f"unknown ownership event: {event!r}")
    return audit_log.event(
        event,
        instance=instance,
        to=to if event == "handoff" else None,
        seat=seat,
        seat_number=seat_number,
        clone=clone,
        name=name,
        id=act,
    )


def format_event_comment(*, versions: Any = None, **fields: Any) -> str:
    """Compose one ownership-event comment body, through the audit-log facility.

    The sole composer of a marker comment body: :func:`ownership_event` takes
    ``fields``, and the facility builds the stamp, the line a person reads and
    the kind's marker. ``versions`` adds DEC-052's provenance footer. The stamp
    carries the instance numbers and, in a project with a topology, the seat
    and the clone's key, never the assignee, which is the comment's author.
    """
    return audit_log.build(ownership_event(**fields), versions=versions)


def ownership_event_comment_args(
    *, issue_number: int | str, versions: Any = None, **fields: Any
) -> list[str]:
    """Construct the ``gh issue comment`` argv for an ownership event.

    The sole constructor of the ownership-event comment write (ADR-041 §3). Every
    ownership mutation — ``create-issue`` claim, ``start-work`` commons-claim,
    ``handoff-issue``, terminal release — obtains its event write only here; no
    script string-builds ``gh issue comment`` for a marker inline. The guard test
    enforces that structurally. ``fields`` are :func:`ownership_event`'s.
    """
    body = format_event_comment(versions=versions, **fields)
    return ["gh", "issue", "comment", str(issue_number), "--body", body]


# ---- label backend (label selector) -------------------------------------


def instance_label(instance: int) -> str:
    """The ``instance:N`` label name for the label backend (DEC-035 point 2)."""
    return f"instance:{instance}"


def instance_label_args(
    *, issue_number: int | str, instance: int, remove: bool = False
) -> list[str]:
    """Construct the ``gh issue edit`` add/remove argv for an ``instance:N`` label.

    The label backend's write constructor (the ``label`` selector). Kept for repos
    that opt into DEC-035's original label mechanism. A comment-mode repo calls it
    only to remove a residual label left from a label-mode past (ADR-041 §2). The
    label's creation is :func:`instance_label_create_args`.
    """
    flag = "--remove-label" if remove else "--add-label"
    return ["gh", "issue", "edit", str(issue_number), flag, instance_label(instance)]


def instance_label_create_args(*, instance: int) -> list[str]:
    """Construct the ``gh label create`` argv for an ``instance:N`` label.

    DEC-035 point 2 creates the label lazily, on its first use, so bootstrap
    stays untouched: a ``label``-mode claim whose add fails asks for this once,
    then adds again. Only a repo that selected ``label`` calls it, which is the
    adopter's word that labels are creatable there (DEC-043 point 2).
    """
    return [
        "gh",
        "label",
        "create",
        instance_label(instance),
        "--description",
        f"Owned by instance {instance} of its assignee (instance ownership)",
    ]


# ---- derived owner-mirror (description regenerator) ----------------------


def render_mirror_region(
    resolution: OwnershipResolution, *, names: dict[int, str] | None = None
) -> str:
    """Render the derived owner-mirror block from a folded resolution.

    A derived view (ADR-041 §4) — never authoritative; the comment log is its
    spine. Fenced by the do-not-edit markers so :func:`render_mirror_body` can
    full-overwrite it and validate-body (the DEC-009 derived-region class) can
    exempt it from wording/scope checks.
    """
    names = names or {}
    if not resolution.claimed:
        inner = "_Unclaimed_ — no instance currently owns this issue."
    else:
        who = ", ".join(
            f"instance {n}" + (f" ({names[n]})" if n in names else "")
            for n in sorted(resolution.owners)
        )
        tie = (
            ""
            if len(resolution.owners) == 1
            else f" (contested — instance {resolution.winner} wins)"
        )
        inner = f"**Owner:** {who}{tie} · via {resolution.substrate}-log"
    return f"{MIRROR_BEGIN}\n> [!NOTE]\n> {inner}\n{MIRROR_END}"


def render_mirror_body(body: str, region: str) -> str:
    """Full-overwrite the owner-mirror region into an issue body (never append).

    The sole constructor of the mirror region in the body (ADR-041 §3/§4). If the
    fenced region exists it is replaced wholesale (regeneration from the log heals
    any human edit / drift — the region is derived); otherwise the region is
    appended once. Returns the new body; the caller runs the ``gh issue edit
    --body`` write. A per-instance *append* is deliberately impossible here — the
    whole-body read-modify-write race DEC-043 rejected.
    """
    body = body or ""
    if _MIRROR_RE.search(body):
        return _MIRROR_RE.sub(lambda _m: region, body)
    sep = "" if body.endswith("\n\n") else ("\n" if body.endswith("\n") else "\n\n")
    return f"{body}{sep}{region}\n"


# ---- selector resolution ------------------------------------------------


def resolve_substrate(settings: dict[str, Any] | None) -> str:
    """Resolve the active ownership substrate (DEC-043 D2), default ``comment``.

    ``settings`` is the adopter's parsed ``instance-ownership.yaml`` — this marker's
    own schema home, **not** ``substrate-map.yaml`` (whose mere presence would
    degrade unlisted axes under DEC-036 emergent activation) — or ``None`` / ``{}``
    when the file is absent. Absent ⇒ the safe default ``comment`` (works on
    label-locked repos); ``label`` is the explicit opt-in, valid only where labels
    are creatable (a precondition bootstrap establishes — not re-derived here). An
    unrecognised value falls back to the safe default.
    """
    if not settings:
        return DEFAULT_SUBSTRATE
    sub = settings.get("substrate")
    return sub if sub in SUBSTRATES else DEFAULT_SUBSTRATE


def gh_call(args: list[str], config: dict[str, Any]) -> Any:
    """Execute a constructed ownership write through the gh helper (DEC-023)."""
    if gh_run is not None:
        return gh_run(args, config, check=False)
    import subprocess

    return subprocess.run(args, capture_output=True, text=True, check=False)
