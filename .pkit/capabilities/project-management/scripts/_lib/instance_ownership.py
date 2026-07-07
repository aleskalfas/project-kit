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

Write construction (one point per side)
---------------------------------------
Two sole-constructors, each the *only* place its write is built (ADR-041 §3):

  * :func:`ownership_event_comment` — the ownership-event comment (claim / handoff
    / abandon / release; a hidden machine stamp + visible human text). Every
    ownership mutation obtains its event write only here.
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
from datetime import UTC, datetime
from typing import Any

# Sibling gh helper (DEC-023 host/owner pinning), imported with the defensive
# fallback the other _lib seams use for file-path test loads.
try:
    from gh import gh_run  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover
    try:
        from _lib.gh import gh_run  # type: ignore[no-redef]
    except ImportError:  # pragma: no cover
        gh_run = None  # type: ignore[assignment]


# ---- vocabulary ---------------------------------------------------------

#: The ownership event types carried by the append-only comment log (DEC-043 D3).
#: ``claim`` and ``handoff`` assert ownership; ``abandon`` / ``release`` relinquish
#: it. The fold reads them in timestamp order.
EVENTS = ("claim", "handoff", "abandon", "release")

#: Substrate selector values (DEC-043 D2). ``comment`` is the default (safe where
#: labels cannot be created); ``label`` is the opt-in for repos that can.
SUBSTRATES = ("comment", "label")
DEFAULT_SUBSTRATE = "comment"

#: The stamp version — bumped only on an explicit format change, never for
#: aesthetics (the human-render layer absorbs those). Tooling parses this line;
#: the audit-log facility (DEC-044) owns the shared stamp grammar this conforms to.
STAMP_VERSION = 1

# The hidden machine stamp. Carries event + instance + timestamp ONLY — never the
# assignee (that is the comment's author.login, resolved live; DEC-043 D3 / the
# methodology-review S1 correction). ``to`` is present on a handoff.
_STAMP_RE = re.compile(
    r"<!--\s*pkit:instance-owner\s+v=(?P<v>\d+)\s+event=(?P<event>\w+)"
    r"\s+instance=(?P<instance>\d+)(?:\s+to=(?P<to>\d+))?"
    r"\s+ts=(?P<ts>\S+)\s*-->"
)

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
    ``(assignee, instance)`` pair's first half). ``ts`` orders the append-only
    fold. Content-free about what the event *means* for the guard — that is the
    caller's posture.
    """

    event: str
    instance: int
    assignee: str
    ts: datetime
    to: int | None = None


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


# ---- stamp parse / format ----------------------------------------------


def _parse_ts(raw: str) -> datetime:
    """Parse an ISO-8601 stamp timestamp; tolerate a trailing ``Z``."""
    return datetime.fromisoformat(raw.replace("Z", "+00:00"))


def format_stamp(event: str, instance: int, ts: datetime, to: int | None = None) -> str:
    """Build the hidden machine stamp line (the parseable half of a marker).

    The sole formatter of the stamp — carries event + instance + timestamp (+ ``to``
    on a handoff), never the assignee. ``format_event_comment`` composes this with
    the human-readable half; nothing else string-builds the stamp.
    """
    if event not in EVENTS:
        raise ValueError(f"unknown ownership event: {event!r}")
    to_frag = f" to={to}" if to is not None else ""
    iso = ts.astimezone(UTC).isoformat()
    return (
        f"<!-- pkit:instance-owner v={STAMP_VERSION} event={event} "
        f"instance={instance}{to_frag} ts={iso} -->"
    )


def parse_events(
    comments: Iterable[dict[str, Any]], assignee_login: str | None
) -> list[OwnershipEvent]:
    """Extract authenticated ownership events from an issue's comments.

    The authenticity filter (ADR-041 §1 / DEC-043 D3): a stamped comment counts
    **only** if its ``author.login`` equals the issue's expected ``assignee_login``
    — a forged stamp pasted from another account is ignored. With no assignee
    (``None``), no marker authenticates, so the issue reads as unclaimed. Returned
    in timestamp order for the fold.
    """
    out: list[OwnershipEvent] = []
    if not assignee_login:
        return out
    for c in comments:
        body = c.get("body") or ""
        m = _STAMP_RE.search(body)
        if not m:
            continue
        author = ((c.get("author") or {}).get("login")) or ""
        if author != assignee_login:
            continue  # forgery / another account — not trusted
        out.append(
            OwnershipEvent(
                event=m.group("event"),
                instance=int(m.group("instance")),
                assignee=author,
                ts=_parse_ts(m.group("ts")),
                to=int(m.group("to")) if m.group("to") else None,
            )
        )
    out.sort(key=lambda e: e.ts)
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
    comments: Iterable[dict[str, Any]],
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

# The human-readable render's verbosity is per-event (DEC-044 §4): authorisation-
# weight events (handoff) read fuller; routine churn (claim/abandon/release) stays
# a compact line. The shared audit-log facility (DEC-044) will own the final
# template; this is the seam's built-in default until that lands.
_EVENT_TITLE = {
    "claim": "🔖 Claimed",
    "handoff": "🤝 Handoff",
    "abandon": "🚪 Abandoned",
    "release": "✅ Released",
}


def format_event_comment(
    *, event: str, instance: int, ts: datetime, to: int | None = None, name: str | None = None
) -> str:
    """Compose one ownership-event comment body: human text + hidden stamp.

    The sole composer of a marker comment body. ``name`` is the optional DEC-045
    display name of the instance, shown for readability; the machine stamp carries
    only the numeric ``instance`` (+ ``to``). The visible text keeps the comment
    from rendering blank (a stamp-only comment would — DEC-044).
    """
    who = f"instance {instance}" + (f" ({name})" if name else "")
    if event == "handoff" and to is not None:
        line = f"**{_EVENT_TITLE[event]}** — {who} → instance {to}"
    else:
        line = f"**{_EVENT_TITLE[event]}** — {who}"
    return f"{line}\n{format_stamp(event, instance, ts, to)}"


def ownership_event_comment_args(
    *, issue_number: int | str, event: str, instance: int, to: int | None = None,
    name: str | None = None, ts: datetime | None = None,
) -> list[str]:
    """Construct the ``gh issue comment`` argv for an ownership event.

    The sole constructor of the ownership-event comment write (ADR-041 §3). Every
    ownership mutation — ``create-issue`` claim, ``start-work`` commons-claim,
    ``handoff-issue``, terminal release — obtains its event write only here; no
    script string-builds ``gh issue comment`` for a marker inline. The guard test
    enforces that structurally.
    """
    ts = ts or datetime.now(UTC)
    body = format_event_comment(event=event, instance=instance, ts=ts, to=to, name=name)
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
