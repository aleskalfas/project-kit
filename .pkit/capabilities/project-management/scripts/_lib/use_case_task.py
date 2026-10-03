"""A declined use-case Task, kept in this checkout until the next day (DEC-054 point 5).

Over an empty use-case set, batch planning offers a prerequisite Task to author the
use cases ahead of work that touches what users do. When the user revises that Task
out of a plan and approves the plan, ``decline-use-case-task`` keeps the answer
here: the UTC time of the approval, truncated to the second, in a git-ignored
runtime file under the capability's ``project/instance/`` directory (the
capability's ``runtime_ignore:`` glob covers it, so it is never committed). The
file lives in the working tree's own capability folder, so each clone and each
worktree keeps its own answer.

The answer counts as declined until the calendar day on which it was given ends,
in the machine's local time, and has expired from local midnight on. The time zone
is read when the answer is read, never stored. Nothing that can go wrong with the
file hides the Task: a missing file is ``none``, and a file that cannot be read —
not JSON, not an object, no time, a time in another form, a time later than now —
is ``unreadable``. Planning offers the Task in both. :func:`read` never raises over
the file's contents.

This file is not the clone's instance identity (``instance_identity``, DEC-035): it
says nothing about which clone this is, and its presence switches nothing on.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone, tzinfo
from pathlib import Path
from typing import Any

#: The kept answer, relative to the capability root. Git-ignored through the
#: capability's ``runtime_ignore:`` glob (package.yaml), so it never commits.
RELATIVE = "project/instance/use-case-task.json"

#: The one key the file holds: the UTC time of the answer.
KEY = "declined_at"

#: How the time is written and the only form read back.
_UTC_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
#: How a time is shown to people: local, to the minute, with the zone's name.
_LOCAL_FORMAT = "%Y-%m-%d %H:%M %Z"

DECLINED = "declined"
EXPIRED = "expired"
NONE = "none"
UNREADABLE = "unreadable"


@dataclass(frozen=True)
class Kept:
    """The kept answer as of one moment.

    ``state`` is one of ``declined``, ``expired``, ``none`` and ``unreadable``.
    ``declined_at`` is the UTC time of the answer and ``offered_again_at`` the
    first moment of the next local day, also in UTC; both are set only when the
    answer was read (``declined`` or ``expired``). ``why`` says what was wrong
    with an ``unreadable`` file.
    """

    state: str
    declined_at: datetime | None = None
    offered_again_at: datetime | None = None
    why: str | None = None


def path_of(capability_root: Path) -> Path:
    """The file that keeps the answer, under ``capability_root``."""
    return capability_root / RELATIVE


def record(capability_root: Path, now: datetime) -> Path:
    """Keep the answer given at ``now``; return the file written.

    The time is truncated to the second, never rounded, so it can never read as
    later than the moment it was given. The file is written whole or not at all: a
    temporary file beside it, renamed over it. The temporary file's name ends in
    ``.json`` so that the ignore glob covers it too. ``now`` must carry a time zone.
    """
    given = _as_utc(now).replace(microsecond=0)
    path = path_of(capability_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps({KEY: given.strftime(_UTC_FORMAT)}) + "\n"
    handle, temporary = tempfile.mkstemp(dir=path.parent, prefix=f".{path.stem}.", suffix=".json")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            stream.write(content)
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise
    return path


def read(capability_root: Path, now: datetime, zone: tzinfo | None = None) -> Kept:
    """The kept answer as of ``now``.

    ``zone`` is the time zone whose calendar day the answer lasts; ``None`` is the
    machine's local time zone, as it stands at this call. ``now`` must carry a time
    zone. Never raises over the file's contents.
    """
    path = path_of(capability_root)
    try:
        content = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return Kept(NONE)
    except (OSError, UnicodeDecodeError) as error:
        return Kept(UNREADABLE, why=f"{path.name} could not be read ({error})")
    try:
        data = json.loads(content)
    except ValueError:
        return Kept(UNREADABLE, why=f"{path.name} is not JSON")
    if not isinstance(data, dict):
        return Kept(UNREADABLE, why=f"{path.name} holds no object")
    given: object = data.get(KEY)
    if not isinstance(given, str):
        return Kept(UNREADABLE, why=f"{path.name} holds no `{KEY}` time")
    try:
        declined_at = datetime.strptime(given, _UTC_FORMAT).replace(tzinfo=timezone.utc)
    except ValueError:
        return Kept(
            UNREADABLE,
            why=f"{path.name} holds `{given}`, not a UTC time of the form YYYY-MM-DDTHH:MM:SSZ",
        )
    current = _as_utc(now)
    if declined_at > current:
        return Kept(UNREADABLE, why=f"{path.name} holds {given}, a time later than now")
    try:
        offered_again_at = start_of_next_day(declined_at, zone)
    except (OverflowError, OSError, ValueError):
        return Kept(UNREADABLE, why=f"{path.name} holds {given}, outside the local calendar")
    state = DECLINED if current < offered_again_at else EXPIRED
    return Kept(state, declined_at, offered_again_at)


def clear(capability_root: Path) -> bool:
    """Discard the kept answer. ``True`` if a file was removed; safe to repeat."""
    path = path_of(capability_root)
    try:
        path.unlink()
    except FileNotFoundError:
        return False
    return True


def start_of_next_day(moment: datetime, zone: tzinfo | None = None) -> datetime:
    """The first moment of the calendar day after ``moment``'s, in ``zone``, in UTC.

    ``zone`` ``None`` is the machine's local time zone. Midnight is placed with the
    offset in force at that midnight, so a daylight-saving change during the day
    moves it to where the local clock shows it.
    """
    following = moment.astimezone(zone).date() + timedelta(days=1)
    midnight = datetime.combine(following, time())
    # A naive time converts as the machine's local time; an aware one in its zone.
    start = midnight.astimezone() if zone is None else midnight.replace(tzinfo=zone)
    return start.astimezone(timezone.utc)


def local_text(moment: datetime, zone: tzinfo | None = None) -> str:
    """``moment`` as people read it: local date and time to the minute, and the zone."""
    return moment.astimezone(zone).strftime(_LOCAL_FORMAT).strip()


def document(kept: Kept, zone: tzinfo | None = None) -> dict[str, Any]:
    """The kept answer as ``decline-use-case-task --show --json`` prints it."""
    return {
        "state": kept.state,
        "declined_at": _utc_text(kept.declined_at),
        "offered_again_at": _utc_text(kept.offered_again_at),
        "declined_at_local": _local_or_none(kept.declined_at, zone),
        "offered_again_at_local": _local_or_none(kept.offered_again_at, zone),
        "why": kept.why,
    }


def describe(kept: Kept, zone: tzinfo | None = None) -> str:
    """One line naming the state and, where the answer was read, the local times."""
    declined_at, offered_again_at = kept.declined_at, kept.offered_again_at
    if kept.state == UNREADABLE:
        return f"unreadable: {kept.why}; the Task is offered."
    if declined_at is None or offered_again_at is None:
        return "none: no declined answer is kept in this checkout; the Task is offered."
    given = local_text(declined_at, zone)
    again = local_text(offered_again_at, zone)
    if kept.state == DECLINED:
        clock = declined_at.astimezone(zone).strftime("%H:%M")
        return (
            f"declined: at {clock} today ({given}); "
            f"the Task is offered again from tomorrow ({again})."
        )
    return f"expired: declined at {given}; the Task is offered again since {again}."


def _as_utc(moment: datetime) -> datetime:
    if moment.tzinfo is None or moment.utcoffset() is None:
        raise ValueError("the time must carry a time zone")
    return moment.astimezone(timezone.utc)


def _utc_text(moment: datetime | None) -> str | None:
    return None if moment is None else moment.astimezone(timezone.utc).strftime(_UTC_FORMAT)


def _local_or_none(moment: datetime | None, zone: tzinfo | None) -> str | None:
    return None if moment is None else local_text(moment, zone)
