"""The agent workspace: one git-excluded folder per checkout for intermediate files.

An agent keeps what it writes only to get its work done — a pull-request body,
a script, captured output — in `.agent-workspace/` at the repository root, and
nowhere else outside the repository (`rules/core.md`, the workspace rule; #1043).
`pkit init` and `pkit sync` create the folder and exclude it from version control;
`pkit status` reports both.

The exclusion goes in the repository's local exclude file,
`<git common dir>/info/exclude`. That file belongs to the clone and is never
committed, so it is not one of the fixed-path files the adapter merges into
(COR-002's merge primitive); the backbone appends its one entry directly and
never touches another line. Resolving the *common* git directory makes the one
entry cover every worktree of the clone: the anchored pattern matches the folder
at each worktree's own root, which is where an agent working in that worktree
keeps its files.

The folder must be a real directory. A symlink named `.agent-workspace` is never
the workspace — the permission model's grant would follow it to wherever it
points — so init and sync refuse it rather than adopting it, and status reports
it.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

WORKSPACE_DIR = ".agent-workspace"
"""The workspace folder's name, at the root of every checkout."""

EXCLUDE_ENTRY = f"/{WORKSPACE_DIR}/"
"""The exclude-file line init and sync add: anchored at the root, directory only."""


@dataclass(frozen=True)
class WorkspaceState:
    """What `pkit status` reports about a project's workspace."""

    present: bool  # a real folder, not a symlink
    in_git: bool  # the project root is inside a git repository
    excluded: bool  # git ignores the folder, whichever rule does it
    symlinked: bool = False  # a symlink sits where the folder belongs


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str] | None:
    """`git -C <root> <args>`, or `None` when git is not installed."""
    try:
        return subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return None


def exclude_file(root: Path) -> Path | None:
    """The exclude file every worktree of `root`'s repository reads, or `None`
    when git does not recognise `root` as inside a repository (or is absent)."""
    result = _git(root, "rev-parse", "--git-common-dir")
    if result is None or result.returncode != 0 or not result.stdout.strip():
        return None
    common = Path(result.stdout.strip())
    if not common.is_absolute():
        common = root / common
    return common.resolve() / "info" / "exclude"


def _names_workspace(line: str) -> bool:
    """True for an exclude line that ignores the workspace at the root, however
    it is spelled: with or without the leading anchor and the trailing slash."""
    entry = line.strip()
    return bool(entry) and not entry.startswith(("#", "!")) and entry.strip("/") == WORKSPACE_DIR


def _has_entry(exclude: Path) -> bool:
    try:
        lines = exclude.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return False
    return any(_names_workspace(line) for line in lines)


def _append_entry(exclude: Path) -> None:
    exclude.parent.mkdir(parents=True, exist_ok=True)
    existing = exclude.read_text(encoding="utf-8") if exclude.is_file() else ""
    separator = "" if not existing or existing.endswith("\n") else "\n"
    with exclude.open("a", encoding="utf-8") as fh:
        fh.write(f"{separator}# agent workspace — intermediate files, never committed (pkit)\n")
        fh.write(f"{EXCLUDE_ENTRY}\n")


def _shown(path: Path, root: Path) -> str:
    """`path` relative to `root` when it lies inside it, else absolute — a
    worktree's exclude file lives in the main checkout's git directory."""
    try:
        return path.relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path)


def ensure(root: Path, *, dry_run: bool = False) -> list[tuple[str, str]]:
    """Create the workspace folder and its exclude entry where either is missing.

    Returns `(verb, detail)` status lines for the caller to print. Idempotent: a
    second run changes nothing and reports each part `unchanged`. A project that
    is not in a git repository gets the folder and a note that there is nothing
    to exclude it from.
    """
    lines: list[tuple[str, str]] = []
    folder = root / WORKSPACE_DIR
    if folder.is_symlink():
        lines.append(
            ("refused", f"{WORKSPACE_DIR} is a symlink, never the workspace — remove the link so a folder can take its place")
        )
    elif folder.is_dir():
        lines.append(("unchanged", f"{WORKSPACE_DIR}/"))
    elif folder.exists():
        lines.append(("skipped", f"{WORKSPACE_DIR} exists and is not a folder — move it aside"))
    else:
        if not dry_run:
            folder.mkdir()
        lines.append(("would create" if dry_run else "created", f"{WORKSPACE_DIR}/"))

    exclude = exclude_file(root)
    if exclude is None:
        lines.append(
            ("skipped", f"{WORKSPACE_DIR}/ exclusion — not a git repository, nothing to exclude it from")
        )
    elif _has_entry(exclude):
        lines.append(("unchanged", f"{WORKSPACE_DIR}/ excluded in {_shown(exclude, root)}"))
    else:
        if not dry_run:
            _append_entry(exclude)
        verb = "would exclude" if dry_run else "excluded"
        lines.append((verb, f"{WORKSPACE_DIR}/ in {_shown(exclude, root)}"))
    return lines


def inspect(root: Path) -> WorkspaceState:
    """Whether the workspace exists and whether git ignores it. Read-only."""
    folder = root / WORKSPACE_DIR
    symlinked = folder.is_symlink()
    present = folder.is_dir() and not symlinked
    # check-ignore exits 0 (ignored), 1 (not ignored) or 128 (not a repository);
    # the trailing slash asks about the folder even before it exists.
    result = _git(root, "check-ignore", "-q", f"{WORKSPACE_DIR}/")
    if result is None or result.returncode not in (0, 1):
        return WorkspaceState(present=present, in_git=False, excluded=False, symlinked=symlinked)
    return WorkspaceState(
        present=present, in_git=True, excluded=result.returncode == 0, symlinked=symlinked
    )
