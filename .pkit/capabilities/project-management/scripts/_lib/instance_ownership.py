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

The label backend's add/remove (:func:`instance_label`) is the third covered
write, kept for the ``label`` selector (DEC-035's original mechanism).

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
from collections.abc import Iterable
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


@dataclass(frozen=True)
class OwnershipResolution:
    """The folded current ownership of one issue — the seam's return.

    ``owners`` is the set of currently-owning instance numbers (normally one;
    two-plus only in the same-instant-clash window before back-off). ``winner`` is
    the lowest-numbered owner (DEC-035 D6 lowest-wins), or ``None`` when the issue
    is unclaimed (a *commons* issue — the DEC-045 unassigned fallback and DEC-035
    ``start-work`` claim target). ``substrate`` records which substrate resolved
    the owner (``comment`` wins over a lingering ``label`` — ADR-041 §2).
    """

    assignee: str | None
    owners: frozenset[int]
    substrate: str | None
    events: tuple[OwnershipEvent, ...] = field(default_factory=tuple)

    @property
    def winner(self) -> int | None:
        return min(self.owners) if self.owners else None

    @property
    def claimed(self) -> bool:
        return bool(self.owners)


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
    removes it. Replaying in timestamp order yields the live owner set — normally a
    singleton, two-plus only in the same-instant clash window (both claimants'
    markers coexist because comment-create is atomic; DEC-035 D6). The caller reads
    :attr:`OwnershipResolution.winner` for the lowest-wins tie-break.
    """
    owners: set[int] = set()
    for e in events:
        if e.event in ("claim",):
            owners.add(e.instance)
        elif e.event == "handoff":
            owners.discard(e.instance)
            if e.to is not None:
                owners.add(e.to)
        elif e.event in ("abandon", "release"):
            owners.discard(e.instance)
    return frozenset(owners)


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

    Returns an :class:`OwnershipResolution`; an empty ``owners`` means *commons*
    (unclaimed) — the DEC-035 ``start-work`` claim target and the DEC-045
    unassigned-workstream fallback.
    """
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
    that opt into DEC-035's original label mechanism; a comment-mode repo never
    calls it. Label *creation* is out of scope here — a label-mode repo has the
    labels (bootstrap/greenfield); comment-mode is precisely the label-locked case.
    """
    flag = "--remove-label" if remove else "--add-label"
    return ["gh", "issue", "edit", str(issue_number), flag, instance_label(instance)]


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
