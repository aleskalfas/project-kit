"""The audit-log facility: one builder and one parser of event comments (DEC-044).

[project-management:DEC-044-audit-log-facility] builds every event comment the
same way, from a structured record: a hidden, versioned **machine stamp** that
tooling reads, and a line a person reads. This module is that facility's one
builder and its one parser. Two seams post events through it, and each keeps a
fold of its own:

  * the ownership seam (``_lib/instance_ownership``, [pkit:ADR-041] point 3):
    ``claim``, ``handoff``, ``abandon`` and ``release`` on an issue of work;
  * the state-issue seam (``_lib/state_issues``, [pkit:ADR-071] point 5):
    ``state-claim``, ``state-release`` and ``state-force-release`` on a state
    issue ([project-management:DEC-058-state-issues]).

Each seam names its event types and their payload, here in :data:`EVENT_TYPES`
and in the capability's ``audit-log`` schema. Neither builds a stamp itself.

The stamp
---------
One line of its own, ``<!-- pkit:audit v=1 event=<type> <field>=<value> ... -->``.
Each value is percent-encoded, so no value holds a space, a ``>`` or a run of
two hyphens, and no value can end the stamp. Every stamp carries ``id``, made
once for each act (:func:`new_act_id`): a retry of the act finds its own comment
by it (:func:`posted`), and a second act with the same fields never does. The
stamp carries no time: a fold takes each event's time from GitHub's record of
the comment, never from a stamp.

The parser reads the stamps written before this facility too: an ownership
event's ``<!-- pkit:instance-owner v=1 ... -->`` comes back as the same event,
with ``legacy`` set (DEC-059 Implications: readers still accept the old stamps).

The frame
---------
Each comment wears the frame of [project-management:DEC-052-comment-house-style]:
a payload line ``<icon> <kind> — <payload>``, the stamp, the kind's marker
``<!-- pkit-<type> -->`` and the provenance footer, whose versions the caller
passes. Each event type is a kind of DEC-052's roster.

Pure: no ``gh`` call and no file read, so it is tested with no repository.
"""

from __future__ import annotations

import re
import secrets
import string
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any
from urllib.parse import unquote

try:
    from _lib.body_rules import lines_outside_fences
    from _lib.provenance import render_comment_footer
except ImportError:  # pragma: no cover - a test that puts `_lib` itself on the path
    from body_rules import lines_outside_fences  # type: ignore[no-redef]
    from provenance import render_comment_footer  # type: ignore[no-redef]

#: The stamp's signature and its version. The version changes only with the
#: grammar, never for how a comment looks.
STAMP_PREFIX = "pkit:audit"
STAMP_VERSION = 1

#: The ownership stamp written before this facility, still read.
LEGACY_OWNERSHIP_PREFIX = "pkit:instance-owner"

#: The families of events, one for each seam that posts them.
OWNERSHIP = "ownership"
STATE_ISSUE = "state-issue"


@dataclass(frozen=True)
class EventType:
    """One event type: its family, its payload fields in stamp order, the
    fields it needs, and the icon and label of its payload line."""

    name: str
    family: str
    fields: tuple[str, ...]
    required: tuple[str, ...]
    icon: str
    label: str


_OWNER_FIELDS = ("instance", "seat", "seat_number", "clone", "name", "id")

#: Every event type the facility builds, by name. The ownership types keep
#: the names DEC-043 point 3 gives them. A handoff's seat, number and key are
#: those of the instance it goes to (ADR-041 point 7).
EVENT_TYPES: dict[str, EventType] = {
    t.name: t
    for t in (
        EventType("claim", OWNERSHIP, _OWNER_FIELDS, ("instance",), "🔖", "claim"),
        EventType(
            "handoff",
            OWNERSHIP,
            ("instance", "to", "seat", "seat_number", "clone", "name", "id"),
            ("instance", "to"),
            "🤝",
            "handoff",
        ),
        EventType("abandon", OWNERSHIP, _OWNER_FIELDS, ("instance",), "🚪", "abandon"),
        EventType("release", OWNERSHIP, _OWNER_FIELDS, ("instance",), "✅", "release"),
        EventType(
            "state-claim",
            STATE_ISSUE,
            ("key", "clone", "place", "id"),
            ("key", "clone", "place"),
            "🪑",
            "state claim",
        ),
        EventType(
            "state-release",
            STATE_ISSUE,
            ("key", "clone", "place", "id"),
            ("key", "clone", "place"),
            "🪑",
            "state release",
        ),
        EventType(
            "state-force-release",
            STATE_ISSUE,
            ("key", "clone", "place", "reason", "id"),
            ("key", "clone", "place", "reason"),
            "⚠️",
            "state release by force",
        ),
    )
}

OWNERSHIP_EVENTS = tuple(n for n, t in EVENT_TYPES.items() if t.family == OWNERSHIP)
STATE_EVENTS = tuple(n for n, t in EVENT_TYPES.items() if t.family == STATE_ISSUE)

_STAMP = re.compile(
    r"<!--\s*pkit:audit\s+v=(?P<v>\d+)\s+event=(?P<event>[a-z][a-z0-9-]*)"
    r"(?P<fields>(?:\s+[a-z][a-z0-9_]*=[^\s>]*)*)\s*-->"
)
_LEGACY = re.compile(
    r"<!--\s*pkit:instance-owner\s+v=1\s+event=(?P<event>\w+)"
    r"\s+instance=(?P<instance>\d+)(?:\s+to=(?P<to>\d+))?"
    r"\s+ts=(?P<ts>\S+)\s*-->"
)
_PAIR = re.compile(r"([a-z][a-z0-9_]*)=([^\s>]*)")

# Kept as they are in a value: letters, digits and a few marks that cannot
# end an HTML comment. A hyphen that follows a hyphen is encoded.
_SAFE = frozenset(string.ascii_letters + string.digits + "._~:/@+-")


@dataclass(frozen=True)
class Event:
    """One event: its type and payload, as built or as parsed from a comment.

    ``payload`` holds the fields in stamp order, each value a string.
    ``legacy`` marks an event read from a stamp written before this facility.
    """

    type: str
    payload: tuple[tuple[str, str], ...] = ()
    version: int = STAMP_VERSION
    legacy: bool = False

    def get(self, name: str) -> str | None:
        """The value of the field ``name``, or None when the event has none."""
        for field, value in self.payload:
            if field == name:
                return value
        return None

    @property
    def act(self) -> str | None:
        """The id of the act this event records."""
        return self.get("id")

    @property
    def family(self) -> str | None:
        known = EVENT_TYPES.get(self.type)
        return known.family if known else None


def new_act_id() -> str:
    """An id for one act, made once and passed again on its retry."""
    return secrets.token_hex(8)


def event(type_name: str, **payload: Any) -> Event:
    """The event of type ``type_name`` with ``payload``, its id made where none is passed.

    ``ValueError`` on an unknown type, a field the type does not carry, or a
    missing field it needs. A field passed as None is left out.
    """
    known = EVENT_TYPES.get(type_name)
    if known is None:
        raise ValueError(f"unknown event type: {type_name!r}")
    values = {k: str(v) for k, v in payload.items() if v is not None}
    unknown = sorted(set(values) - set(known.fields))
    if unknown:
        raise ValueError(f"event {type_name!r} carries no field {', '.join(unknown)}")
    missing = [f for f in known.required if not values.get(f)]
    if missing:
        raise ValueError(f"event {type_name!r} needs {', '.join(missing)}")
    values.setdefault("id", new_act_id())
    ordered = tuple((f, values[f]) for f in known.fields if f in values)
    return Event(type=type_name, payload=ordered)


def stamp(ev: Event) -> str:
    """The machine stamp of ``ev``: the one line tooling reads."""
    fields = "".join(f" {name}={encode(value)}" for name, value in ev.payload)
    return f"<!-- {STAMP_PREFIX} v={STAMP_VERSION} event={ev.type}{fields} -->"


def kind_marker(type_name: str) -> str:
    """The marker of an event's kind in DEC-052's roster."""
    return f"<!-- pkit-{type_name} -->"


def build(ev: Event, *, versions: Any = None) -> str:
    """The whole comment for ``ev``: the payload line, the stamp, the kind's
    marker and, where ``versions`` is given, the provenance footer."""
    parts = [render(ev), "", stamp(ev), kind_marker(ev.type)]
    if versions is not None:
        parts += ["", render_comment_footer(versions)]
    return "\n".join(parts)


def render(ev: Event) -> str:
    """The lines a person reads: the payload line, and a reason on its own
    paragraph where the event carries one (DEC-052)."""
    known = EVENT_TYPES[ev.type]
    head = f"{known.icon} {known.label} — "
    if known.family == OWNERSHIP:
        head += _owner_payload(ev)
    else:
        head += _state_payload(ev)
    reason = ev.get("reason")
    return f"{head}\n\n{reason}" if reason else head


def _owner_payload(ev: Event) -> str:
    who = f"instance {ev.get('instance')}"
    if ev.get("name"):
        who += f" ({ev.get('name')})"
    if ev.type == "handoff":
        who += f" → instance {ev.get('to')}"
    seat = ev.get("seat")
    if seat:
        who += f" · seat {_code(seat)}"
        if ev.get("seat_number"):
            who += f" (number {ev.get('seat_number')})"
    if ev.get("clone"):
        who += f" · clone {_code(ev.get('clone') or '')}"
    return who


def _state_payload(ev: Event) -> str:
    return (
        f"{_code(ev.get('key') or '')} · clone {_code(ev.get('clone') or '')}"
        f" at {ev.get('place') or 'an unnamed place'}"
    )


def _code(value: str) -> str:
    return "`" + value.replace("`", "'") + "`"


def parse(body: str) -> Event | None:
    """The event a comment's body records, or None.

    The stamp counts on a line of its own outside a fenced code block, so a
    comment that quotes one in a code block records nothing. A stamp of a later
    version than this reader knows reads as None.
    """
    for line in lines_outside_fences(body or ""):
        text = line.strip()
        match = _STAMP.fullmatch(text)
        if match:
            if int(match.group("v")) > STAMP_VERSION:
                return None
            pairs: list[tuple[str, str]] = []
            seen: set[str] = set()
            for name, value in _PAIR.findall(match.group("fields")):
                if name not in seen:
                    seen.add(name)
                    pairs.append((name, unquote(value)))
            return Event(
                type=match.group("event"), payload=tuple(pairs), version=int(match.group("v"))
            )
        legacy = _LEGACY.fullmatch(text)
        if legacy:
            pairs = [("instance", legacy.group("instance"))]
            if legacy.group("to"):
                pairs.append(("to", legacy.group("to")))
            pairs.append(("ts", legacy.group("ts")))
            return Event(type=legacy.group("event"), payload=tuple(pairs), version=1, legacy=True)
    return None


def posted(bodies: Iterable[str], act: str) -> bool:
    """Whether a comment among ``bodies`` records the act ``act`` (DEC-044 point 2).

    A retry of an act reads the log first and posts nothing where it finds
    its own id. Two acts with the same fields carry two ids, so a second act
    never reads as its predecessor's retry.
    """
    for body in bodies:
        ev = parse(body)
        if ev is not None and ev.act == act:
            return True
    return False


def encode(value: str) -> str:
    """A value encoded for a stamp or a marker: no space, no ``>`` and no run
    of two hyphens survive, so no value can end the HTML comment it sits in.
    ``urllib.parse.unquote`` reads it back."""
    out: list[str] = []
    previous = ""
    for ch in value:
        if ch in _SAFE and not (ch == "-" and previous == "-"):
            out.append(ch)
        else:
            out.extend(f"%{b:02X}" for b in ch.encode("utf-8"))
        previous = ch
    return "".join(out)
