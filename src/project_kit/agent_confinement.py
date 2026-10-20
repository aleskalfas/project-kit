"""The working copy of a confined agent run, its check and its files (ADR-066 points 6 and 7).

The backbone's run command (`agent_runs`) runs a confined agent in a clone of the
repository at a pinned commit. This module makes that clone and what stands around it,
checks it after the run, hands back the run's files and takes it all down.

- **The run root.** Every run's folder lies in one folder of the backbone's,
  `$XDG_STATE_HOME/pkit/agent-runs`, or `~/.local/state/pkit/agent-runs` where that
  variable is unset or not absolute: the user's state folder, not a temp folder the
  system or the harness shares. It is made only this user can use. It is
  refused when it is a link, when another user owns it, when the group or others can
  write it, or when it lies inside a shared temp folder or a working tree of the
  repository. Each run gets a
  fresh folder in it, holding a pid file. Each confined run first removes the folder
  of any run whose process is gone, as a killed run leaves its clone behind.
- **The clone.** It is made with `git clone --no-local --no-hardlinks --no-checkout`,
  so it shares no object file with the person's repository, by link or by reference.
  Where the clone lacks the commit, as when only a remote-tracking reference holds it,
  the commit is fetched from the person's repository by its id. Then the commit is
  checked out, detached, and HEAD must name it. These git calls leave out the person's
  global and system configuration, and run no hook.
- **Provisioned.** The clone's query commands are provisioned as the project's checks
  are (`provisioning`). A command that cannot be provisioned is a warning for the
  run's diagnostics, never a refusal.
- **The workspace.** The run command makes `.agent-workspace` in the clone, and its
  temp folder `.tmp` inside it. It refuses when the commit holds anything at that
  path. The workspace is no link.
- **The run's `pkit`.** A script in the run's own `bin` folder, outside the clone. It
  changes to the clone's root, points git at the clone's own git folder, starts `uv`
  with no configuration file, and runs this backbone's code under this interpreter, as
  the migration runner's `pkit` does (ADR-065 point 14).
- **The check.** Before the run, the clone's state is recorded by reading the file
  system, never git: each entry of the working tree outside `.git` and the workspace,
  ignored ones included, git's configuration, hooks and `info` folder, and the
  references. The index and the objects are left out. After the run, and after a failed start,
  the state is read again. Anything that changed, appeared or went is a breach, one
  line each. So is anything that cannot be read: the check fails closed.
- **The copy.** The run's files go from the workspace to the folder the caller named:
  regular files only, following no link, refusing a file with more than one link,
  bounded in total size, and refusing a name a file system may read as `.git`. The
  temp folder is never copied. Each refusal is a line of the check, and a breach.
- **The run's rules and exclusions.** `run_rules` reads the run's rules in the
  clone, and projects them through the permission core (ADR-066 point 5). On
  macOS, where the installed `uv` still needs it (ADR-027's test), the allowed
  commands whose work starts `uv` run outside the sandbox. The run's document
  names each (ADR-066 point 6).

`confinement` makes all of this for one run, and removes the run's folder on every
exit.
"""

from __future__ import annotations

import contextlib
import hashlib
import importlib
import os
import re
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
from collections.abc import Generator, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

#: Where the run root lies, under the user's state folder.
RUN_ROOT_PARTS = ("pkit", "agent-runs")

#: The name each run's folder starts with, and the file in it that holds the pid of the
#: process that made it.
RUN_PREFIX = "run-"
PID_FILE = "pid"

#: The run's folder holds the clone and the folder of the run's `pkit`.
CLONE = "clone"
BIN = "bin"

#: The run's workspace, at the clone's root, and its temp folder inside it.
WORKSPACE = ".agent-workspace"
TEMP = ".tmp"

#: The most the run's files may weigh together. The copy refuses a file past it.
COPY_LIMIT_BYTES = 64 * 1024 * 1024

#: How long one git call that makes the clone may take before the run is refused.
GIT_TIMEOUT_SECONDS = 600

#: Git's own files and folders in the clone that a later git call reads as
#: configuration or runs: a changed `core.fsmonitor`, or a planted hook, runs code.
#: The check reads them, byte for byte, beside the working tree.
GIT_FILES = ("config", "hooks", "info")

#: The clone's references, as the check reads them.
REFERENCES = ("HEAD", "packed-refs", "refs")

#: The folders the system or the harness shares as temp folders, beside the one
#: `tempfile` finds and `$TMPDIR`. The run root lies in none of them.
SHARED_TEMP_FOLDERS = ("/tmp", "/private/tmp", "/var/folders", "/private/var/folders")

#: The check's verdicts.
CLEAN = "clean"
BREACH = "breach"
NOT_RUN = "not-run"

# The brief's markers, each replaced with the run's value before the runner reads it.
_MARKER = re.compile(r"\{\{pkit:(working-copy|workspace|temp|commit)\}\}")

# The characters HFS+ ignores in a name, as git's own guard lists them.
_HFS_IGNORED = frozenset(
    chr(code)
    for code in (*range(0x200C, 0x2010), *range(0x202A, 0x202F), *range(0x206A, 0x2070), 0xFEFF)
)

# A name NTFS may read as `.git`: `.git` or its short name `git~1`, then only dots and
# spaces, up to the end, a stream's `:` or a folder separator.
_NTFS_GIT = re.compile(r"(?:\.git|git~1)[. ]*(?:[:\\].*)?", re.DOTALL)

# The variables that move git off the clone's own repository. The run's `pkit` unsets
# them, and sets `GIT_DIR` and `GIT_WORK_TREE` itself.
_GIT_LOCATORS = (
    "GIT_INDEX_FILE",
    "GIT_OBJECT_DIRECTORY",
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    "GIT_COMMON_DIR",
    "GIT_NAMESPACE",
)

_PKIT = """#!/bin/sh
# The run's `pkit` (ADR-066 point 6): the clone's root, its own git folder, no uv
# configuration file, and this backbone's code under its own interpreter.
cd {clone} || exit 1
unset {locators}
GIT_DIR={git_dir}
GIT_WORK_TREE={clone}
UV_NO_CONFIG=1
PYTHONDONTWRITEBYTECODE=1
export GIT_DIR GIT_WORK_TREE UV_NO_CONFIG PYTHONDONTWRITEBYTECODE
exec {python} -P -m project_kit "$@"
"""


class Projection(Protocol):
    """What this module reads of the run's rules as the permission core projects them
    (`run_rules.RunProjection`)."""

    @property
    def allow(self) -> Sequence[Mapping[str, Any]]: ...

    @property
    def deny(self) -> Sequence[Mapping[str, Any]]: ...

    @property
    def excluded_candidates(self) -> Sequence[Sequence[str]]: ...


class Refused(Exception):
    """A confined run cannot be made. The reason says why, for the run's document."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class Check:
    """The check after a run (ADR-066 point 7): its verdict, and each change, one line
    each. `not-run` when the run never reached its runner."""

    verdict: str
    changes: tuple[str, ...] = ()

    def with_refusals(self, refusals: Sequence[str]) -> Check:
        """The check with what the copy refused. Each refusal is a breach."""
        if not refusals:
            return self
        return Check(BREACH, (*self.changes, *refusals))

    def as_json(self) -> dict[str, Any]:
        return {"verdict": self.verdict, "changes": list(self.changes)}


CHECK_NOT_RUN = Check(NOT_RUN)


@dataclass(frozen=True)
class Confinement:
    """One confined run's folders, as `confinement` made them. `warnings` are the
    provisioning failures, for the run's diagnostics."""

    project_root: Path
    commit: str
    folder: Path
    clone: Path
    workspace: Path
    temp: Path
    pkit_folder: Path
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class State:
    """The clone as read before or after a run: each entry of the working tree outside
    `.git` and the workspace, each reference file, and what could not be read."""

    entries: Mapping[str, str]
    references: Mapping[str, str]
    unread: tuple[str, ...] = field(default=())


# --- the run root ---------------------------------------------------------------------


def run_root(project_root: Path) -> Path:
    """The folder every run's folder lies in, made if need be, and resolved.

    Raises `Refused` when it cannot be made, when it is a link or no folder, when
    another user owns it, when the group or others can write it, or when it lies
    inside a shared temp folder or a working tree of the repository at
    `project_root`. A run root inside a temp folder is refused before anything is
    made there."""
    state = os.environ.get("XDG_STATE_HOME", "")
    try:
        base = Path(state) if os.path.isabs(state) else Path.home() / ".local" / "state"
    except RuntimeError as exc:  # no home folder can be found
        raise Refused(f"the run root cannot be placed: {exc}") from exc
    root = base.joinpath(*RUN_ROOT_PARTS)
    _refuse_in_a_temp_folder(root.resolve())
    try:
        root.parent.mkdir(parents=True, exist_ok=True)
        with contextlib.suppress(FileExistsError):
            root.mkdir(mode=0o700)
        held = os.lstat(root)
    except OSError as exc:
        raise Refused(f"the run root {root} cannot be made: {exc.strerror or exc}") from exc
    if stat.S_ISLNK(held.st_mode):
        raise Refused(f"the run root {root} is a symbolic link")
    if not stat.S_ISDIR(held.st_mode):
        raise Refused(f"the run root {root} is not a folder")
    if held.st_uid != os.getuid():
        raise Refused(f"the run root {root} is owned by another user")
    if held.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
        raise Refused(f"the run root {root} can be written by its group or by others")
    resolved = root.resolve()
    _refuse_in_a_temp_folder(resolved)
    for tree in _working_trees(project_root):
        if resolved.is_relative_to(tree):
            raise Refused(f"the run root {resolved} lies inside the working tree {tree}")
    return resolved


def temp_folders() -> list[Path]:
    """The temp folders the system or the harness shares, resolved: the one
    `tempfile` finds, `$TMPDIR`, and `SHARED_TEMP_FOLDERS`."""
    named = [tempfile.gettempdir(), os.environ.get("TMPDIR", ""), *SHARED_TEMP_FOLDERS]
    return [Path(folder).resolve() for folder in named if os.path.isabs(folder)]


def _refuse_in_a_temp_folder(resolved: Path) -> None:
    """Refuse a run root that lies inside a shared temp folder (ADR-066 point 7)."""
    for folder in temp_folders():
        if resolved.is_relative_to(folder):
            raise Refused(
                f"the run root {resolved} lies inside the temp folder {folder}, which the "
                "system or the harness shares; a run's clone never lies there (ADR-066 "
                "point 7). Set XDG_STATE_HOME to a folder of your own"
            )


def _working_trees(project_root: Path) -> list[Path]:
    """Every working tree of the repository at `project_root`, resolved. Raises
    `Refused` when git cannot list them, since the run root cannot then be judged."""
    listed = _git(project_root, "worktree", "list", "--porcelain", timeout=60)
    if isinstance(listed, str):
        raise Refused(f"the working trees of the repository cannot be listed: {listed}")
    return [
        Path(line.removeprefix("worktree ")).resolve()
        for line in listed
        if line.startswith("worktree ")
    ]


def remove_stale(root: Path) -> None:
    """Remove the folder of each run in `root` whose process is gone. A run's process
    is the pid its pid file holds, else the pid its folder's name holds, as a run
    killed before it wrote the file leaves it. A folder with neither is not a run's,
    and is left alone, as is a link."""
    try:
        entries = list(os.scandir(root))
    except OSError:
        return
    for entry in entries:
        if not entry.name.startswith(RUN_PREFIX) or entry.is_symlink():
            continue
        pid = _pid_of(Path(entry.path))
        if pid is not None and not _alive(pid):
            remove_tree(Path(entry.path))


def _pid_of(folder: Path) -> int | None:
    """The pid of the process that made a run's folder, or None."""
    with contextlib.suppress(OSError, ValueError):
        return int((folder / PID_FILE).read_text(encoding="utf-8").strip())
    named = folder.name.removeprefix(RUN_PREFIX).split("-", 1)[0]
    return int(named) if named.isdigit() else None


def _alive(pid: int) -> bool:
    """Whether a process `pid` exists. One of another user's counts."""
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _make_run_folder(root: Path) -> Path:
    """A fresh folder for one run in `root`, its pid in its name and in its pid file."""
    try:
        folder = Path(tempfile.mkdtemp(prefix=f"{RUN_PREFIX}{os.getpid()}-", dir=root))
    except OSError as exc:
        raise Refused(f"the run's folder cannot be made in {root}: {exc.strerror or exc}") from exc
    try:
        (folder / PID_FILE).write_text(f"{os.getpid()}\n", encoding="utf-8")
    except OSError as exc:
        remove_tree(folder)
        raise Refused(f"the run's folder cannot be written: {exc.strerror or exc}") from exc
    return folder


def remove_tree(folder: Path) -> None:
    """Remove `folder` and all it holds, following no link and never raising. Where a
    folder inside cannot be emptied, as when a run took away its owner's write, each
    folder is made writable to its owner, and the removal is tried again."""
    try:
        shutil.rmtree(folder)
    except OSError:
        if not os.path.lexists(folder):
            return
        _make_folders_writable(folder)
        shutil.rmtree(folder, ignore_errors=True)


def _make_folders_writable(folder: Path) -> None:
    """Give the owner full use of `folder` and of each folder inside it. A link is
    never followed."""
    stack = [str(folder)]
    while stack:
        path = stack.pop()
        try:
            if not stat.S_ISDIR(os.lstat(path).st_mode):
                continue
            os.chmod(path, 0o700)
            stack.extend(entry.path for entry in os.scandir(path))
        except OSError:
            continue


# --- the clone ------------------------------------------------------------------------


def _git_environment() -> dict[str, str]:
    """The environment of the git calls that make the clone: the caller's, with no
    variable of git's, and with the person's global and system configuration and
    attributes left out."""
    env = {name: value for name, value in os.environ.items() if not name.startswith("GIT_")}
    env.update(
        GIT_CONFIG_NOSYSTEM="1",
        GIT_CONFIG_GLOBAL=os.devnull,
        GIT_ATTR_NOSYSTEM="1",
        GIT_TERMINAL_PROMPT="0",
    )
    return env


def _git(cwd: Path, *args: str, timeout: float = GIT_TIMEOUT_SECONDS) -> str | list[str]:
    """Run git with `args` from `cwd`, with no hook, in `_git_environment`. Its
    standard output as lines when it exits 0; else why it failed, as one string."""
    try:
        done = subprocess.run(
            ["git", "-c", f"core.hooksPath={os.devnull}", *args],
            cwd=cwd,
            env=_git_environment(),
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError:
        return "git is not on the PATH"
    except subprocess.TimeoutExpired:
        return f"git {args[0]} did not finish within {timeout:g} s"
    except OSError as exc:
        return f"git could not start: {exc}"
    if done.returncode != 0:
        said = [line.strip() for line in done.stderr.splitlines() if line.strip()]
        return f"git {args[0]} exited {done.returncode}" + (f": {said[-1]}" if said else "")
    return done.stdout.splitlines()


def holds_commit(project_root: Path, commit: str) -> bool:
    """Whether the repository at `project_root` holds the commit `commit`."""
    return not isinstance(_git(project_root, "cat-file", "-e", f"{commit}^{{commit}}"), str)


def make_clone(project_root: Path, commit: str, clone: Path) -> None:
    """Clone the repository at `project_root` into `clone`, at `commit`, detached.

    The clone shares no object file with the repository, by link or by reference.
    Raises `Refused` when it cannot be made, holds no such commit, borrows objects
    from elsewhere, or its HEAD does not name the commit after the checkout."""
    cloned = _git(
        clone.parent,
        "clone",
        "--quiet",
        "--no-local",
        "--no-hardlinks",
        "--no-checkout",
        "--template=",
        "--",
        str(project_root),
        str(clone),
    )
    if isinstance(cloned, str):
        raise Refused(f"the run's clone cannot be made: {cloned}")
    if not holds_commit(clone, commit):
        fetched = _git(clone, "fetch", "--quiet", "--no-tags", "origin", commit)
        if isinstance(fetched, str) or not holds_commit(clone, commit):
            why = fetched if isinstance(fetched, str) else "the fetch did not bring it"
            raise Refused(f"the run's clone does not hold the commit {commit}: {why}")
    if os.path.lexists(clone / ".git" / "objects" / "info" / "alternates"):
        raise Refused("the run's clone borrows objects from another repository")
    checked = _git(
        clone, "-c", "advice.detachedHead=false", "checkout", "--quiet", "--detach", commit
    )
    if isinstance(checked, str):
        raise Refused(f"the run's clone cannot be checked out at {commit}: {checked}")
    try:
        head = (clone / ".git" / "HEAD").read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise Refused(f"the run's clone has no HEAD to read: {exc.strerror or exc}") from exc
    if head != commit:
        raise Refused(f"the run's clone is at {head!r} after the checkout, not at {commit}")


def _provision(clone: Path) -> tuple[str, ...]:
    """Provision the clone's query commands, as the project's checks are. Each command
    that cannot be provisioned is a warning, never a refusal."""
    from project_kit import provisioning

    try:
        lines = provisioning.ensure(clone)
    except Exception as exc:  # a failure here is a warning, whatever its cause
        return (f"provisioning: the clone's query commands were not provisioned: {exc}",)
    failed = provisioning.State.NOT_PROVISIONED.value
    return tuple(f"provisioning: {detail}" for verb, detail in lines if verb == failed)


def make_workspace(clone: Path) -> tuple[Path, Path]:
    """Make the run's workspace in `clone`, and its temp folder inside it. Raises
    `Refused` when the commit holds anything at the workspace's path, or either
    folder cannot be made as a folder of its own."""
    workspace = clone / WORKSPACE
    if os.path.lexists(workspace):
        raise Refused(
            f"the commit holds something at `{WORKSPACE}`, where the run's workspace goes"
        )
    temp = workspace / TEMP
    try:
        workspace.mkdir(mode=0o700)
        temp.mkdir(mode=0o700)
        held = os.lstat(workspace)
    except OSError as exc:
        raise Refused(
            f"the run's workspace or its temp folder cannot be made: {exc.strerror or exc}"
        ) from exc
    if not stat.S_ISDIR(held.st_mode):
        raise Refused("the run's workspace is not a folder of its own")
    return workspace, temp


def write_pkit(folder: Path, clone: Path) -> Path:
    """Write the run's `pkit` into a `bin` folder of `folder`, and return that folder."""
    bin_folder = folder / BIN
    bin_folder.mkdir(mode=0o700)
    script = bin_folder / "pkit"
    script.write_text(
        _PKIT.format(
            clone=shlex.quote(str(clone)),
            git_dir=shlex.quote(str(clone / ".git")),
            locators=" ".join(_GIT_LOCATORS),
            python=shlex.quote(sys.executable),
        ),
        encoding="utf-8",
    )
    script.chmod(0o755)
    return bin_folder


@contextlib.contextmanager
def confinement(project_root: Path, commit: str) -> Generator[Confinement]:
    """The folders of one confined run at `commit`, for the length of the block.

    Makes the run root and removes stale runs' folders, then makes the run's folder,
    the clone, its provisioning, its workspace and the run's `pkit`. Raises `Refused`
    when any of these cannot be made. The run's folder, the clone with it, is removed
    on every exit."""
    root = run_root(project_root)
    remove_stale(root)
    folder = _make_run_folder(root)
    try:
        clone = folder / CLONE
        make_clone(project_root, commit, clone)
        warnings = _provision(clone)
        workspace, temp = make_workspace(clone)
        pkit_folder = write_pkit(folder, clone)
        yield Confinement(
            project_root=project_root.resolve(),
            commit=commit,
            folder=folder,
            clone=clone,
            workspace=workspace,
            temp=temp,
            pkit_folder=pkit_folder,
            warnings=warnings,
        )
    finally:
        remove_tree(folder)


# --- the run's rules, its exclusions and its request ------------------------------------


def project(made: Confinement, rules_of: str, agent: str) -> Projection | str:
    """The run's rules, as the permission core projects them from the clone
    (`run_rules.project_run`): a projection, or the reason the run is refused. The
    module is imported here, when a confined run needs it."""
    run_rules = importlib.import_module("project_kit.run_rules")
    projected: Projection | str = run_rules.project_run(
        made.clone, rules_of, agent, working_copy=made.clone, workspace=made.workspace
    )
    return projected


def exclusions(clone: Path, projection: Projection) -> tuple[tuple[str, ...], ...]:
    """The allowed commands that run outside the sandbox (ADR-066 point 6): the
    projection's candidates, where ADR-027's test shows the installed `uv` still needs
    it, which holds only on macOS; otherwise none."""
    candidates = tuple(tuple(command) for command in projection.excluded_candidates)
    if not candidates:
        return ()
    from project_kit import permissions

    return candidates if permissions.uv_required_exclusion(clone) else ()


def request_block(
    made: Confinement, projection: Projection, excluded: Sequence[Sequence[str]]
) -> dict[str, Any]:
    """The request's `confined` block, as the runner reads it (ADR-066 point 2): the
    run's folders, the person's checkout, the run's rules and its exclusions."""
    return {
        "working_copy": str(made.clone),
        "workspace": str(made.workspace),
        "temp": str(made.temp),
        "pkit_folder": str(made.pkit_folder),
        "project_root": str(made.project_root),
        "rules": {
            "allow": [dict(rule) for rule in projection.allow],
            "deny": [dict(rule) for rule in projection.deny],
        },
        "excluded": [list(command) for command in excluded],
    }


def replace_markers(brief: str, made: Confinement) -> str:
    """The brief with each of its markers replaced by the run's value, every
    occurrence, in one pass, so no value is read as a marker in turn."""
    values = {
        "working-copy": str(made.clone),
        "workspace": str(made.workspace),
        "temp": str(made.temp),
        "commit": made.commit,
    }
    return _MARKER.sub(lambda match: values[match.group(1)], brief)


# --- the check ------------------------------------------------------------------------


def record(clone: Path) -> State:
    """The clone's state, read from the file system and never through git.

    Each entry is recorded by its type, its mode and its content's hash, a link by
    its target. The entries are those of the working tree outside `.git` and the
    workspace, which are recorded only as entries themselves, and git's own files a
    later git call reads as configuration or runs (`GIT_FILES`). The references are
    `.git/HEAD`, `.git/packed-refs` and everything under `.git/refs`. The index and
    the objects are left out."""
    entries: dict[str, str] = {}
    references: dict[str, str] = {}
    unread: list[str] = []
    _record_under(str(clone), "", entries, unread, shallow=frozenset({".git", WORKSPACE}))
    git = clone / ".git"
    for name in GIT_FILES:
        _record_entry(git / name, f".git/{name}", entries, unread)
    for name in REFERENCES:
        _record_entry(git / name, f".git/{name}", references, unread)
    return State(entries, references, tuple(unread))


def _record_entry(path: Path, name: str, into: dict[str, str], unread: list[str]) -> None:
    """Record the entry at `path` as `name`, and everything under it when it is a
    folder. An entry that does not exist is not recorded."""
    if not os.path.lexists(path):
        return
    described = _described(str(path), name, unread)
    if described is None:
        return
    into[name] = described
    if described.startswith("folder"):
        _record_under(str(path), name, into, unread)


def _record_under(
    folder: str,
    rel: str,
    into: dict[str, str],
    unread: list[str],
    *,
    shallow: frozenset[str] = frozenset(),
) -> None:
    """Record everything under `folder`, named from `rel`, following no link. An
    entry `shallow` names, directly in `folder`, is recorded by its type alone, and
    nothing under it is."""
    stack: list[tuple[str, str]] = [(folder, rel)]
    while stack:
        path, prefix = stack.pop()
        try:
            listing = sorted(os.scandir(path), key=lambda entry: entry.name)
        except OSError as exc:
            unread.append(f"{_shown(prefix or '.')}: {exc.strerror or exc}")
            continue
        for entry in listing:
            name = f"{prefix}/{entry.name}" if prefix else entry.name
            described = _described(entry.path, name, unread)
            if described is None:
                continue
            if prefix == rel and entry.name in shallow:
                into[name] = described.split(" ", 1)[0]
                continue
            into[name] = described
            if described.startswith("folder"):
                stack.append((entry.path, name))


def _described(path: str, name: str, unread: list[str]) -> str | None:
    """One entry, as the state records it, or None when it cannot be read (the reason
    added to `unread`)."""
    try:
        held = os.lstat(path)
        kind = stat.S_IFMT(held.st_mode)
        mode = f"{stat.S_IMODE(held.st_mode):o}"
        if kind == stat.S_IFDIR:
            return f"folder {mode}"
        if kind == stat.S_IFLNK:
            return f"link {os.readlink(path)}"
        if kind == stat.S_IFREG:
            return f"file {mode} {_hash(path, held)}"
        return f"other {kind:o} {mode}"
    except OSError as exc:
        unread.append(f"{_shown(name)}: {exc.strerror or exc}")
        return None


def _hash(path: str, held: os.stat_result) -> str:
    """The hash of a regular file's content, read through no link. Raises `OSError`
    when the file is no longer the one `held` describes."""
    handle = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(handle, "rb") as stream:
        opened = os.fstat(stream.fileno())
        if (opened.st_dev, opened.st_ino) != (held.st_dev, held.st_ino):
            raise OSError(f"{path} changed while it was read")
        return hashlib.file_digest(stream, "sha256").hexdigest()


def check(clone: Path, before: State) -> Check:
    """The check after a run (ADR-066 point 7): the clone's state read again and
    compared with `before`. Each entry that changed, appeared or went, each reference
    that moved, appeared or went, and each entry that cannot be read is one line, and
    any line is a breach."""
    after = record(clone)
    changes: list[str] = []
    for name in sorted(before.entries.keys() | after.entries.keys()):
        was, now = before.entries.get(name), after.entries.get(name)
        if was == now:
            continue
        if was is None:
            changes.append(f"appeared: {_shown(name)}")
        elif now is None:
            changes.append(f"removed: {_shown(name)}")
        else:
            changes.append(f"changed: {_shown(name)}")
    for name in sorted(before.references.keys() | after.references.keys()):
        was, now = before.references.get(name), after.references.get(name)
        if was == now:
            continue
        if was is None:
            changes.append(f"reference appeared: {_shown(name)}")
        elif now is None:
            changes.append(f"reference removed: {_shown(name)}")
        else:
            changes.append(f"reference moved: {_shown(name)}")
    changes.extend(f"unreadable: {line}" for line in after.unread)
    return Check(BREACH if changes else CLEAN, tuple(changes))


def _shown(name: str) -> str:
    """A path as a line of the check shows it: as it is, or quoted with its escapes
    where it holds a character that is not printable, so it stays one line."""
    return name if name.isprintable() else repr(name)


# --- the copy -------------------------------------------------------------------------


def names_git(name: str) -> bool:
    """Whether a file system may read `name` as `.git`, as git's own guard judges it:
    without regard to case, with trailing dots and spaces, an NTFS stream, the short
    name `git~1`, and the characters HFS+ ignores."""
    stripped = "".join(char for char in name if char not in _HFS_IGNORED)
    return any(_NTFS_GIT.fullmatch(form.casefold()) for form in (name, stripped))


def copy_files(workspace: Path, files_to: Path) -> list[str]:
    """Copy the run's files from `workspace` into `files_to`, and return what was
    refused, one line each.

    Only regular files are copied, and folders made for them. No link is followed. A
    file with more than one link is refused, as is one past `COPY_LIMIT_BYTES` of the
    run's files together, any entry whose name a file system may read as `.git`, and
    any entry that already exists in `files_to`. The temp folder is never copied."""
    refused: list[str] = []
    budget = COPY_LIMIT_BYTES
    stack: list[tuple[str, Path, str]] = [(str(workspace), files_to, "")]
    while stack:
        path, target, rel = stack.pop()
        try:
            listing = sorted(os.scandir(path), key=lambda entry: entry.name)
        except OSError as exc:
            refused.append(f"refused: {_shown(rel or '.')}: cannot be read: {exc.strerror or exc}")
            continue
        for entry in listing:
            name = f"{rel}/{entry.name}" if rel else entry.name
            if not rel and entry.name == TEMP:
                continue
            if names_git(entry.name):
                refused.append(f"refused: {_shown(name)}: a name a file system may read as .git")
                continue
            try:
                held = entry.stat(follow_symlinks=False)
            except OSError as exc:
                refused.append(f"refused: {_shown(name)}: cannot be read: {exc.strerror or exc}")
                continue
            destination = target / entry.name
            if stat.S_ISLNK(held.st_mode):
                refused.append(f"refused: {_shown(name)}: a symbolic link")
            elif stat.S_ISDIR(held.st_mode):
                try:
                    os.mkdir(destination, 0o700)
                except OSError as exc:
                    refused.append(f"refused: {_shown(name)}: {exc.strerror or exc}")
                    continue
                stack.append((entry.path, destination, name))
            elif not stat.S_ISREG(held.st_mode):
                refused.append(f"refused: {_shown(name)}: not a regular file")
            elif held.st_nlink > 1:
                refused.append(f"refused: {_shown(name)}: a file with more than one link")
            elif held.st_size > budget:
                refused.append(
                    f"refused: {_shown(name)}: past the bound of {COPY_LIMIT_BYTES} bytes on "
                    "the run's files"
                )
            else:
                copied = _copy_file(entry.path, destination, held, budget)
                if isinstance(copied, str):
                    refused.append(f"refused: {_shown(name)}: {copied}")
                else:
                    budget -= copied
    return refused


def _copy_file(source: str, destination: Path, held: os.stat_result, budget: int) -> int | str:
    """Copy one regular file, through no link, into a file of its own that did not
    exist. The bytes copied, or why it was refused, the destination then removed."""
    try:
        handle = os.open(source, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except OSError as exc:
        return f"cannot be read: {exc.strerror or exc}"
    with os.fdopen(handle, "rb") as reader:
        opened = os.fstat(reader.fileno())
        if (
            (opened.st_dev, opened.st_ino) != (held.st_dev, held.st_ino)
            or not stat.S_ISREG(opened.st_mode)
            or opened.st_nlink > 1
        ):
            return "changed while it was copied"
        try:
            written = os.open(
                destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
            )
        except OSError as exc:
            return f"cannot be written: {exc.strerror or exc}"
        size = 0
        with os.fdopen(written, "wb") as writer:
            while chunk := reader.read(1024 * 1024):
                size += len(chunk)
                if size > budget:
                    break
                writer.write(chunk)
    if size > budget:
        destination.unlink(missing_ok=True)
        return f"past the bound of {COPY_LIMIT_BYTES} bytes on the run's files"
    return size
