"""Clone-local instance identity — which clone am I (DEC-035 point 1).

The instance-ownership feature is opt-in per clone: ``set-instance <N>`` writes
this clone's numeric **instance id** to a git-ignored runtime file under the
capability's ``project/instance/`` directory (declared in ``runtime_ignore:`` per
[pkit:ADR-009] rule 7, so it is never committed). A clone with no id set
reads ``None``, and every ownership behaviour — marking, the clash guard, signed
listings — no-ops. The presence of the id is the **sole activation gate**
(DEC-035 point 1). The one exception: such a clone cannot release an owner, so a
move back from In Progress on an owned issue refuses (DEC-035 point 4).

This is deliberately NOT the ownership marker. The marker is *per issue*, lives on
GitHub, and is substrate-selectable (``_lib/instance_ownership`` / DEC-043). This
file is *per clone*, local, never shared, and substrate-independent — it answers
only "which of my clones is this," the first half of the ``(assignee, instance)``
owner pair (DEC-035 point 2).

The same file keeps the clone's **key**, which the clone generates the first
time it claims on a state issue (DEC-035 point 1, refined for
[project-management:DEC-058-state-issues]). Writing or clearing the instance id
keeps the key.

In a project with a topology of seats it also keeps the name of the seat the
clone took, as a **hint** of where to look ([project-management:
DEC-059-topology-of-seats] point 6). The hint never says that the clone holds
the seat: a command reads the seat's state issue, by the clone's key, before it
acts as the seat's instance. Writing or clearing the hint keeps the key and the
instance id.
"""

from __future__ import annotations

import json
import secrets
from pathlib import Path

#: The clone-local identity file, relative to the capability root. Git-ignored via
#: the capability's ``runtime_ignore:`` glob (package.yaml) so it never commits.
IDENTITY_RELATIVE = "project/instance/clone.json"


def identity_path(capability_root: Path) -> Path:
    """The clone-local identity file path under ``capability_root``."""
    return capability_root / IDENTITY_RELATIVE


def read_instance_id(capability_root: Path) -> int | None:
    """This clone's instance id, or ``None`` when unset (the no-op default).

    Tolerant: a missing file, unreadable file, malformed JSON, or a non-integer
    ``instance`` value all read as ``None`` — an unset clone, never an error. The
    activation gate must fail *closed* to the no-op default, so a corrupt runtime
    file degrades a clone to non-participating rather than crashing an ownership
    read on every command.
    """
    path = identity_path(capability_root)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    n = data.get("instance") if isinstance(data, dict) else None
    return n if isinstance(n, int) and not isinstance(n, bool) else None


def write_instance_id(capability_root: Path, instance: int) -> Path:
    """Set this clone's instance id; return the file path written.

    ``ValueError`` on a non-positive id — an instance number is 1-based
    (DEC-035's per-assignee pool). Creates the ``project/instance/`` directory on
    first use.
    """
    if not isinstance(instance, int) or isinstance(instance, bool) or instance < 1:
        raise ValueError("instance id must be a positive integer")
    return _write_field(capability_root, "instance", instance)


def clear_instance_id(capability_root: Path) -> bool:
    """Unset this clone's identity (revert to the no-op default).

    Returns ``True`` if an id was removed, ``False`` if none was set. Idempotent —
    clearing an already-unset clone is a no-op, not an error. The clone's key
    stays: it names the clone, whatever its number.
    """
    path = identity_path(capability_root)
    data = _read_data(path)
    if data is None:
        if path.is_file():
            path.unlink()
            return True
        return False
    if "instance" not in data:
        return False
    del data["instance"]
    if data:
        path.write_text(json.dumps(data) + "\n", encoding="utf-8")
    else:
        path.unlink()
    return True


# ---- the clone's key (DEC-058 point 5) ---------------------------------------

#: The bytes of randomness in a clone's key.
_KEY_BYTES = 16


def read_clone_key(capability_root: Path) -> str | None:
    """This clone's key, or ``None`` when it has none yet.

    The key tells one clone's claim on a state issue from another's under one
    account, whether or not either has an instance number ([project-management:
    DEC-058-state-issues] point 5). It sits beside the instance id in the same
    git-ignored runtime file, and is never committed. A file that cannot be read
    holds no key.
    """
    data = _read_data(identity_path(capability_root))
    key = data.get("key") if data is not None else None
    return key if isinstance(key, str) and key else None


def ensure_clone_key(capability_root: Path) -> str:
    """This clone's key, generated and kept the first time it is asked for.

    The first claim on a state issue asks for it, so a clone that never claims
    one writes nothing. Whoever copies a clone clears its runtime file, since two
    clones that share a key cannot be told apart (DEC-058 point 5).
    """
    existing = read_clone_key(capability_root)
    if existing is not None:
        return existing
    key = secrets.token_hex(_KEY_BYTES)
    _write_field(capability_root, "key", key)
    return key


# ---- the seat's hint (DEC-059 point 6) ----------------------------------------


def read_seat_hint(capability_root: Path) -> str | None:
    """The name of the seat this clone took, or ``None`` when it took none.

    A hint of where to look, never proof that the clone holds the seat. A file
    that cannot be read holds no hint."""
    data = _read_data(identity_path(capability_root))
    seat = data.get("seat") if data is not None else None
    return seat if isinstance(seat, str) and seat else None


def write_seat_hint(capability_root: Path, seat: str) -> Path:
    """Keep ``seat`` as the seat this clone took; return the file path written."""
    if not seat:
        raise ValueError("a seat's name is not empty")
    return _write_field(capability_root, "seat", seat)


def clear_seat_hint(capability_root: Path) -> bool:
    """Forget the seat this clone took. ``True`` where a hint was removed. The
    key and the instance id stay."""
    path = identity_path(capability_root)
    data = _read_data(path)
    if data is None or "seat" not in data:
        return False
    del data["seat"]
    if data:
        path.write_text(json.dumps(data) + "\n", encoding="utf-8")
    else:
        path.unlink()
    return True


def _read_data(path: Path) -> dict | None:
    """The runtime file's fields, or None when it is absent or unreadable."""
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def _write_field(capability_root: Path, name: str, value: object) -> Path:
    """Set one field of the runtime file, keeping the others."""
    path = identity_path(capability_root)
    data = _read_data(path) or {}
    data[name] = value
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data) + "\n", encoding="utf-8")
    return path
