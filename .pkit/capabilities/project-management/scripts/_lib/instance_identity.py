"""Clone-local instance identity — which clone am I (DEC-035 point 1).

The instance-ownership feature is opt-in per clone: ``set-instance <N>`` writes
this clone's numeric **instance id** to a git-ignored runtime file under the
capability's ``project/instance/`` directory (declared in ``runtime_ignore:`` per
[pkit:ADR-009] rule 7, so it is never committed). A clone with no id set
reads ``None``, and every ownership behaviour — marking, the clash guard, signed
listings — no-ops. The presence of the id is the **sole activation gate**
(DEC-035 point 1): a non-participating clone is byte-for-byte unchanged.

A clone includes its linked git worktrees (DEC-035 point 1). A worktree with no
id file of its own reads the main working tree's, found through git's common
directory (:func:`_lib.session_guard.work_tree_and_common_dir`): a session in a
worktree, such as a subagent's, acts as its clone. A worktree that sets its own
id keeps it, and a worktree of a bare repository, which has no main working
tree, reads its own file alone. Writing and clearing stay local, so a worktree
can take a number of its own.

This is deliberately NOT the ownership marker. The marker is *per issue*, lives on
GitHub, and is substrate-selectable (``_lib/instance_ownership`` / DEC-043). This
file is *per clone*, local, never shared, and substrate-independent — it answers
only "which of my clones is this," the first half of the ``(assignee, instance)``
owner pair (DEC-035 point 2).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from _lib import session_guard

#: The clone-local identity file, relative to the capability root. Git-ignored via
#: the capability's ``runtime_ignore:`` glob (package.yaml) so it never commits.
IDENTITY_RELATIVE = "project/instance/clone.json"


def identity_path(capability_root: Path) -> Path:
    """The clone-local identity file path under ``capability_root``."""
    return capability_root / IDENTITY_RELATIVE


def main_work_tree_identity_path(capability_root: Path) -> Path | None:
    """The main working tree's identity file, for a capability root in a linked worktree.

    The main working tree is the parent of git's common directory when that
    directory is a ``.git`` inside a repository that is not bare. None in the
    main working tree itself, outside git, in a worktree of a bare repository,
    where the common directory is not a ``.git`` directory, or when git could
    not run: each reads the local file alone.
    """
    try:
        root = capability_root.resolve()
    except OSError:
        return None
    layout = session_guard.work_tree_and_common_dir(root)
    if layout is None:
        return None
    work_tree, common_dir = layout
    main = common_dir.parent
    if common_dir.name != ".git" or main == work_tree or not _has_main_work_tree(work_tree):
        return None
    try:
        relative = root.relative_to(work_tree)
    except ValueError:
        return None
    return identity_path(main / relative)


def _has_main_work_tree(work_tree: Path) -> bool:
    """Whether the repository of ``work_tree`` has a main working tree.

    Only a ``core.bare`` that reads ``false`` says so. A bare repository, a
    value git does not give, and a git that cannot run all read as no main
    working tree, so the read falls back to the local file.
    """
    try:
        proc = subprocess.run(
            ["git", "-C", str(work_tree), "config", "--bool", "core.bare"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return proc.returncode == 0 and proc.stdout.strip() == "false"


def identity_source(capability_root: Path) -> Path | None:
    """The file this clone's instance id is read from, or ``None`` when there is none.

    The local file when it exists, whatever it holds: a worktree that sets its
    own id keeps it. Otherwise the main working tree's, for a linked worktree
    whose clone has set one.
    """
    local = identity_path(capability_root)
    if local.is_file():
        return local
    shared = main_work_tree_identity_path(capability_root)
    if shared is not None and shared.is_file():
        return shared
    return None


def read_instance_id(capability_root: Path) -> int | None:
    """This clone's instance id, or ``None`` when unset (the no-op default).

    Read from :func:`identity_source`. Tolerant: a missing file, unreadable
    file, malformed JSON, or a non-integer ``instance`` value all read as
    ``None`` — an unset clone, never an error. The activation gate must fail
    *closed* to the no-op default, so a corrupt runtime file degrades a clone to
    non-participating rather than crashing an ownership read on every command.
    """
    path = identity_source(capability_root)
    if path is None:
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    n = data.get("instance") if isinstance(data, dict) else None
    return n if isinstance(n, int) and not isinstance(n, bool) else None


def write_instance_id(capability_root: Path, instance: int) -> Path:
    """Set this clone's instance id; return the file path written.

    Always the local file, so a worktree that sets an id takes a number of its
    own. ``ValueError`` on a non-positive id — an instance number is 1-based
    (DEC-035's per-assignee pool). Creates the ``project/instance/`` directory
    on first use.
    """
    if not isinstance(instance, int) or isinstance(instance, bool) or instance < 1:
        raise ValueError("instance id must be a positive integer")
    path = identity_path(capability_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"instance": instance}) + "\n", encoding="utf-8")
    return path


def clear_instance_id(capability_root: Path) -> bool:
    """Unset this clone's identity (revert to the no-op default).

    Removes the local file only: a worktree that clears its own id reads its
    clone's again. Returns ``True`` if a file was removed, ``False`` if none was
    set. Idempotent — clearing an already-unset clone is a no-op, not an error.
    """
    path = identity_path(capability_root)
    if path.is_file():
        path.unlink()
        return True
    return False
