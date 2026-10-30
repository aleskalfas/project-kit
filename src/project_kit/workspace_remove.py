"""Removing files from the agent workspace: `pkit workspace remove` (ADR-060 point 10).

An agent keeps its intermediate files in `.agent-workspace/` at its checkout's
root (`workspace.py`), and removes them here once it no longer needs them. A
shell `rm` cannot do it: the permission hook reads a command before the shell
expands it, so no reading of `rm` into the folder holds, and recursive `rm` is
denied everywhere (ADR-060 point 4). This command reads its paths after the
shell has expanded them, tests each one, and removes nothing unless every path
lies inside.

Three parts:

- :func:`plan` tests every path and removes nothing. A path is *inside* only
  where the permission hook's recogniser would place it (ADR-060 points 2 and
  3): in the `.agent-workspace` of a checkout of the project, as that checkout
  holds the folder, in no repository or worktree nested in it. The tests are
  the recogniser's own functions, taken from the running pkit's decision core
  (:func:`decision_core`), never from a file under the root the command acts
  on, which a branch or another checkout may hold changed (point 8).
  `tests/test_workspace_remove.py` holds the two to one table of paths.
  Besides the outside, it refuses the folder itself, a last part of `.` or
  `..`, a capability's lasting state (a path at or under a child of the folder
  named after a capability the manifest registers) and a nested checkout.
- :func:`remove` removes what a plan holds, and needs the cross-repository
  guard's clearance for the root (`session_guard.require`). It reaches each
  path from one handle on its workspace folder, opened through no symlink, and
  removes with calls relative to the folder it reached, never by a path's
  name. A part that has turned into a link since the test stops that path.
- :func:`unsafe_platform` says why the removal cannot run here, where the
  platform lacks the descriptor-relative calls the removal relies on.

A removal changes an entry of a folder, where a write changes the file its
target resolves to. So a path's parent is resolved and its last part taken as
written: a symlink given is removed as a link, never followed, and a file with
more than one link loses only the name given (point 10, "The place a removal
changes").
"""

from __future__ import annotations

import errno
import functools
import importlib.util
import os
import shutil
import stat
import sys
import unicodedata
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

from project_kit import session_guard
from project_kit.install import find_source_kit
from project_kit.manifest import read_backbone_manifest
from project_kit.workspace import WORKSPACE_DIR

#: How a folder on the way to a path is opened: as a folder, and never through
#: a symlink in its own place.
_FOLDER_FLAGS = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)

#: The errors an open with `O_NOFOLLOW | O_DIRECTORY` gives for a part that is
#: a symlink, or no longer a folder.
_TURNED = (errno.ELOOP, errno.ENOTDIR)

#: The folder's own name and the two that name no entry of a folder.
_NOT_AN_ENTRY = (".", "..")


@dataclass(frozen=True)
class Held:
    """A path the command does not remove, and why: refused by a test, or
    stopped on the way down."""

    given: str
    why: str


@dataclass(frozen=True)
class Target:
    """A path that passed every test: `folder` is the workspace folder holding
    it, resolved, and `parts` the way down from that folder, its last part as
    written."""

    given: str
    folder: str
    parts: tuple[str, ...]


@dataclass(frozen=True)
class Plan:
    """What a call would do, every path tested: the paths to remove, those
    that name nothing inside the folder, and those refused. One refused path
    refuses the whole call."""

    root: Path
    targets: tuple[Target, ...]
    missing: tuple[str, ...]
    refused: tuple[Held, ...]


@dataclass(frozen=True)
class Outcome:
    """What a removal did: the paths it removed, those already gone, and those
    it stopped or left partly removed."""

    removed: tuple[str, ...]
    gone: tuple[str, ...]
    stopped: tuple[Held, ...]


# ---- the running pkit's tests ---------------------------------------------------


@functools.cache
def decision_core() -> ModuleType:
    """The permission decision core of the running pkit, `permissions/decide.py`
    in the content it ships (`find_source_kit`): a source checkout's own when
    pkit runs from one, the bundled tree otherwise. Never the copy under the
    project root (ADR-060 point 8). Loading writes no bytecode beside it."""
    path = find_source_kit() / "permissions" / "decide.py"
    spec = importlib.util.spec_from_file_location("pkit_workspace_remove_decide", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"the running pkit's decision core cannot be loaded from {path}")
    module = importlib.util.module_from_spec(spec)
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module


def holding_folder(path: str, root: str) -> tuple[str, str] | None:
    """The checkout and the workspace folder that hold the resolved `path`, or
    None where the recogniser would place it in none.

    The same reading as the recogniser's `_inside`, from its own functions: a
    checkout of the project at `root` (`_checkouts`), its folder as the
    checkout holds it (`_folder_top`), `path` strictly inside, and no
    repository or worktree nested between (`_nested_checkout`). This returns
    the folder where `_inside` answers yes or no, since the removal starts
    from it."""
    core = decision_core()
    for checkout in core._checkouts(path, root):
        folder = core._folder_top(checkout, WORKSPACE_DIR)
        if folder is None or path == folder or os.path.commonpath([path, folder]) != folder:
            continue
        if not core._nested_checkout(path, folder):
            return str(checkout), str(folder)
    return None


def place(given: str, cwd: str) -> str | None:
    """The entry a removal of `given` changes: its parent resolved against
    `cwd`, symlinks included, and its last part as written, any trailing slash
    dropped. None where the last part is `.` or `..`, or the path is empty."""
    trimmed = given.rstrip("/")
    if not trimmed:
        return os.sep if given else None
    head, last = os.path.split(trimmed)
    if last in _NOT_AN_ENTRY:
        return None
    return os.path.join(os.path.realpath(os.path.join(cwd, head or os.curdir)), last)


def inside(given: str, cwd: str, root: str) -> bool:
    """Whether a removal of `given`, run in `cwd` under the project root `root`,
    changes an entry inside the agent workspace."""
    where = place(given, cwd)
    return where is not None and holding_folder(where, root) is not None


# ---- testing every path -----------------------------------------------------------


def plan(paths: Sequence[str], *, cwd: Path, root: Path) -> Plan:
    """Test every path, removing nothing.

    `cwd` is the directory the command runs in, against which a relative path
    is read, and `root` the project root resolved from it. A path that would
    lie inside the folder but names nothing is missing, and refuses nothing.
    """
    targets: list[Target] = []
    missing: list[str] = []
    refused: list[Held] = []
    names = _CapabilityNames()
    for given in paths:
        tested = _test(given, str(cwd), str(root), names)
        if isinstance(tested, Held):
            refused.append(tested)
        elif tested is None:
            missing.append(given)
        else:
            targets.append(tested)
    return Plan(root, tuple(targets), tuple(missing), tuple(refused))


def _test(given: str, cwd: str, root: str, names: _CapabilityNames) -> Target | Held | None:
    """`given` as a target, refused, or None where it names nothing inside."""
    where = place(given, cwd)
    if where is None:
        why = "names no path" if not given else "ends in `.` or `..`, which names no entry"
        return Held(given, why)
    held = holding_folder(where, root)
    if held is None:
        return Held(given, _why_outside(where, root))
    checkout, folder = held
    parts = tuple(os.path.relpath(where, folder).split(os.sep))
    lasting = names.lasting(parts[0], folder, (root, checkout))
    if lasting is not None:
        return Held(given, lasting)
    if not os.path.lexists(where):
        return None
    nested = _nested_below(where)
    if nested is not None:
        return Held(given, nested)
    return Target(given, folder, parts)


def _why_outside(where: str, root: str) -> str:
    """Why the recogniser places `where` in no workspace, in words."""
    core = decision_core()
    checkouts = [str(checkout) for checkout in core._checkouts(where, root)]
    for checkout in checkouts:
        own = os.path.join(checkout, WORKSPACE_DIR)
        if where == own:
            if os.path.islink(own):
                return f"is the checkout's {WORKSPACE_DIR}, a symlink, which is never the workspace"
            return (
                "is the workspace folder itself, which nothing would replace until the next "
                "`pkit sync`"
            )
        folder = core._folder_top(checkout, WORKSPACE_DIR)
        if folder is not None and os.path.commonpath([where, folder]) == folder:
            return _nested_why(_nested_above(where, str(folder)))
    if any(os.path.islink(os.path.join(checkout, WORKSPACE_DIR)) for checkout in checkouts):
        return (
            f"lies outside the agent workspace: this checkout's {WORKSPACE_DIR} is a symlink, "
            "which is never the workspace"
        )
    return "lies outside the agent workspace"


def _nested_above(where: str, folder: str) -> str:
    """The nearest folder from `where`'s parent up to `folder` that holds a
    `.git` entry: the nested checkout `where` lies in."""
    current = os.path.dirname(where)
    while current != folder and not os.path.lexists(os.path.join(current, ".git")):
        current = os.path.dirname(current)
    return current


def _nested_below(where: str) -> str | None:
    """Why `where`, a folder to remove, may not go: a `.git` entry anywhere in
    it, or a folder in it that cannot be read whole. None for a file or link,
    and for a folder that holds no `.git` entry. Links are not followed."""
    if not stat.S_ISDIR(os.lstat(where).st_mode):
        return None
    unread: list[OSError] = []
    for folder, folders, files in os.walk(where, onerror=unread.append):
        if ".git" in folders or ".git" in files:
            return _nested_why(folder)
    if unread:
        return f"cannot be read whole to look for a nested repository: {unread[0]}"
    return None


def _nested_why(checkout: str) -> str:
    """Why a path in or holding the nested checkout at `checkout` is refused,
    and who removes it."""
    core = decision_core()
    marker = os.path.join(checkout, ".git")
    common = core._common_git_dir(checkout) if os.path.isfile(marker) else None
    if common is not None and core._same_repository(checkout, common):
        return (
            f"holds or lies in a worktree git registered, {checkout}: remove it with "
            f"`git worktree remove {checkout}`"
        )
    return (
        f"holds or lies in a repository or worktree nested in the workspace, {checkout}, "
        "which may hold work no commit saved: the operator removes it by hand"
    )


class _CapabilityNames:
    """The capabilities the manifest of each checkout registers, read once
    each. A capability keeps its lasting state in the folder under a direct
    child named after itself (ADR-060 point 10)."""

    def __init__(self) -> None:
        self._read: dict[str, frozenset[str] | str] = {}

    def lasting(self, child: str, folder: str, checkouts: Iterable[str]) -> str | None:
        """Why a path under the folder's direct child `child` is a capability's
        lasting state, by the manifest of any of `checkouts`; None where it is
        none. A manifest that cannot be read refuses the path."""
        for checkout in checkouts:
            names = self._names(checkout)
            if isinstance(names, str):
                return names
            for name in names:
                if _same_child(child, name, folder):
                    return (
                        f"lies at or under {WORKSPACE_DIR}/{name}/, the lasting state of the "
                        f"capability {name}"
                    )
        return None

    def _names(self, checkout: str) -> frozenset[str] | str:
        if checkout not in self._read:
            self._read[checkout] = _registered_capabilities(checkout)
        return self._read[checkout]


def _registered_capabilities(checkout: str) -> frozenset[str] | str:
    """The names of the capabilities the checkout's manifest registers, or why
    they cannot be read."""
    try:
        manifest = read_backbone_manifest(Path(checkout))
    except Exception as exc:  # whatever stops the reading refuses the path, never passes it
        return (
            f"the manifest of {checkout} cannot be read, so which children of the folder are a "
            f"capability's lasting state is unknown: {exc}"
        )
    if manifest is None:
        return frozenset()
    return frozenset(c.name for c in manifest.components if c.kind == "capability")


def _same_child(child: str, name: str, folder: str) -> bool:
    """Whether the folder's child `child` is the child named `name`: the same
    name once case and Unicode form are folded, as a file system may fold them,
    or the same entry on disk. Folding can only refuse more."""
    if _folded(child) == _folded(name):
        return True
    try:
        return os.path.samestat(
            os.lstat(os.path.join(folder, child)), os.lstat(os.path.join(folder, name))
        )
    except OSError:
        return False


def _folded(name: str) -> str:
    return unicodedata.normalize("NFC", name).casefold()


# ---- removing --------------------------------------------------------------------


def unsafe_platform() -> str | None:
    """Why the removal cannot run on this platform, or None where it can: it
    needs `shutil.rmtree` to resist symlink attacks, and descriptor-relative
    calls that follow no link."""
    if not getattr(shutil.rmtree, "avoids_symlink_attacks", False):
        return (
            "this platform's shutil.rmtree does not resist symlink attacks, so a folder "
            "swapped for a link could carry a removal out of the workspace; nothing was removed"
        )
    needed = (os.open, os.stat, os.unlink)
    if not (
        hasattr(os, "O_NOFOLLOW")
        and hasattr(os, "O_DIRECTORY")
        and all(call in os.supports_dir_fd for call in needed)
        and os.stat in os.supports_follow_symlinks
    ):
        return (
            "this platform lacks the descriptor-relative calls that keep a removal from "
            "following a link; nothing was removed"
        )
    return None


def remove(the_plan: Plan, clearance: session_guard.Clearance) -> Outcome:
    """Remove every target of `the_plan`, which must refuse nothing, once the
    cross-repository guard has cleared its root.

    Each workspace folder is opened once, through no symlink, and each path
    reached from it part by part without following a link. A part that has
    turned into a link, or into no folder, since the test stops that path. A
    folder is removed with `shutil.rmtree` relative to the folder holding it,
    which removes a link inside it as a link. An I/O error partway through
    stops that path and leaves it partly removed.
    """
    session_guard.require(clearance, the_plan.root)
    if the_plan.refused:
        raise ValueError("a plan that refuses a path removes nothing")
    removed: list[str] = []
    gone: list[str] = []
    stopped: list[Held] = []
    opened: dict[str, int | Held] = {}
    try:
        for target in the_plan.targets:
            handle = opened.get(target.folder)
            if handle is None:
                handle = opened[target.folder] = _open_folder(target.folder)
            if isinstance(handle, Held):
                stopped.append(Held(target.given, handle.why))
                continue
            result = _remove_from(handle, target)
            if result is None:
                removed.append(target.given)
            elif result is _GONE:
                gone.append(target.given)
            else:
                stopped.append(result)
    finally:
        for handle in opened.values():
            if isinstance(handle, int):
                os.close(handle)
    return Outcome(tuple(removed), tuple(gone), tuple(stopped))


#: A path found gone on the way down: removed by an earlier path of the call,
#: or by something else since the test.
_GONE = Held("", "gone")


def _open_folder(folder: str) -> int | Held:
    """A handle on the workspace folder at the resolved `folder`, reached from
    the file-system root part by part through no symlink; or why not."""
    handle = os.open(os.sep, _FOLDER_FLAGS)
    try:
        for part in folder.strip(os.sep).split(os.sep):
            following = os.open(part, _FOLDER_FLAGS, dir_fd=handle)
            os.close(handle)
            handle = following
    except OSError as exc:
        os.close(handle)
        if exc.errno in _TURNED:
            return Held("", f"the way to {folder} has turned into a link since the test")
        return Held("", f"{folder} cannot be opened: {exc.strerror or exc}")
    return handle


def _remove_from(folder: int, target: Target) -> Held | None:
    """Remove `target` from the open workspace `folder`: None when removed,
    `_GONE` when already gone, or why it stopped."""
    handles: list[int] = []
    current = folder
    try:
        for part in target.parts[:-1]:
            current = os.open(part, _FOLDER_FLAGS, dir_fd=current)
            handles.append(current)
        name = target.parts[-1]
        entry = os.stat(name, dir_fd=current, follow_symlinks=False)
        if stat.S_ISDIR(entry.st_mode):
            shutil.rmtree(name, dir_fd=current)
        else:
            os.unlink(name, dir_fd=current)
    except FileNotFoundError:
        return _GONE
    except OSError as exc:
        if exc.errno in _TURNED and len(handles) < len(target.parts) - 1:
            part = target.parts[len(handles)]
            return Held(
                target.given,
                f"{part} has turned into a link, or into no folder, since the test; not removed",
            )
        return Held(target.given, f"stopped partway, so it may be partly removed: {exc}")
    finally:
        for handle in handles:
            os.close(handle)
    return None


# ---- what the command says ---------------------------------------------------------


def guard_refusal(refusal: session_guard.Refusal) -> str:
    """The cross-repository guard's refusal, in the command's words: it takes
    no confirmation with the call, so it names none (ADR-060 point 10)."""
    comparison = refusal.comparison
    where = comparison.target or refusal.directory
    return (
        f"the cross-repository guard refused: {comparison.reason} (COR-039). Run it from a "
        f"session rooted in {where}, or at a terminal, which asks. Nothing was removed."
    )


def refusal_lines(the_plan: Plan) -> list[str]:
    """One line for each refused path and why, then that nothing was removed."""
    rows = [("refused", held.given, held.why) for held in the_plan.refused]
    return [*_rows(rows), "Nothing was removed."]


def plan_lines(the_plan: Plan) -> list[str]:
    """What a dry run would remove, and the paths that name nothing."""
    rows = [("would remove", target.given, "") for target in the_plan.targets]
    rows += [("missing", given, "names nothing in the workspace") for given in the_plan.missing]
    return [*_rows(rows), "Dry run: nothing removed."]


def outcome_lines(the_plan: Plan, outcome: Outcome) -> tuple[list[str], list[str]]:
    """What a removal says: the lines for standard output — each path removed,
    and those that named nothing — and those for standard error, each path
    stopped."""
    rows = [("removed", given, "") for given in outcome.removed]
    rows += [("missing", given, "names nothing in the workspace") for given in the_plan.missing]
    rows += [("missing", given, "gone before it was reached") for given in outcome.gone]
    stopped = [("stopped", held.given, held.why) for held in outcome.stopped]
    width = max((len(verb) for verb, _, _ in rows + stopped), default=0)
    return _rows(rows, width), _rows(stopped, width)


def _rows(rows: list[tuple[str, str, str]], width: int | None = None) -> list[str]:
    pad = width if width is not None else max((len(verb) for verb, _, _ in rows), default=0)
    return [f"{verb:<{pad}}  {given}" + (f" — {why}" if why else "") for verb, given, why in rows]
