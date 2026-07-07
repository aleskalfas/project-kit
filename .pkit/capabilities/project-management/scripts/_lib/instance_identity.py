"""Clone-local instance identity — which clone am I (DEC-035 point 1).

The instance-ownership feature is opt-in per clone: ``set-instance <N>`` writes
this clone's numeric **instance id** to a git-ignored runtime file under the
capability's ``project/instance/`` directory (declared in ``runtime_ignore:`` per
[pkit:ADR-009] Amendment 1, so it is never committed). A clone with no id set
reads ``None``, and every ownership behaviour — marking, the clash guard, signed
listings — no-ops. The presence of the id is the **sole activation gate**
(DEC-035 point 1): a non-participating clone is byte-for-byte unchanged.

This is deliberately NOT the ownership marker. The marker is *per issue*, lives on
GitHub, and is substrate-selectable (``_lib/instance_ownership`` / DEC-043). This
file is *per clone*, local, never shared, and substrate-independent — it answers
only "which of my clones is this," the first half of the ``(assignee, instance)``
owner pair (DEC-035 point 2).
"""

from __future__ import annotations

import json
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
    path = identity_path(capability_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"instance": instance}) + "\n", encoding="utf-8")
    return path


def clear_instance_id(capability_root: Path) -> bool:
    """Unset this clone's identity (revert to the no-op default).

    Returns ``True`` if a file was removed, ``False`` if none was set. Idempotent —
    clearing an already-unset clone is a no-op, not an error.
    """
    path = identity_path(capability_root)
    if path.is_file():
        path.unlink()
        return True
    return False
