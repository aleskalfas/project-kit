"""The files the capability reads, as git sees them (lean-business DEC-002 points 1 and 14).

The backbone's data validation reads the working tree's one listing, the files git sees:
those it tracks, and those it does not track but does not ignore (ADR-057 point 2). The
check reads the same listing, so a file the backbone shape-checks is one the check sees,
and a file git ignores is neither's. Outside a git repository, as in a copy of a fixture,
the files are walked as they lie.

Either way a link is passed over, a linked folder is never entered, and a tracked file the
working tree no longer holds is no file. Which of the files a reader takes, such as none
in a hidden folder, is the reader's to say.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path, PurePosixPath


class ListingFailed(Exception):
    """git could not list the files."""


def files(root: Path, folder: str = "") -> list[str]:
    """The files under `folder`, relative to `root`, or every file of `root` where `folder`
    is empty: tracked by git, or untracked but not ignored, or walked outside a git
    repository. In path order, without links. Raises ListingFailed where git fails."""
    listed = _git_listed(root, folder) if _in_repository(root) else _walked(root, folder)
    return sorted(rel for rel in listed if _plain(root, rel))


def hidden(rel: str) -> bool:
    """Whether the path `rel` lies in a hidden folder or names a hidden file."""
    return any(part.startswith(".") for part in PurePosixPath(rel).parts)


def _plain(root: Path, rel: str) -> bool:
    """Whether `rel` is a file reached through no link."""
    parts = PurePosixPath(rel).parts
    path = root / rel
    if path.is_symlink() or not path.is_file():
        return False
    return not any(root.joinpath(*parts[:depth]).is_symlink() for depth in range(1, len(parts)))


def _git_listed(root: Path, folder: str) -> set[str]:
    args = ["git", "--literal-pathspecs", "ls-files", "-z", "--cached", "--others"]
    args += ["--exclude-standard", "--", folder or "."]
    try:
        proc = subprocess.run(args, cwd=root, capture_output=True, check=False)
    except OSError as exc:
        raise ListingFailed(f"git could not be run ({exc})") from exc
    if proc.returncode != 0:
        detail = [line for line in proc.stderr.decode("utf-8", "replace").splitlines() if line]
        raise ListingFailed(detail[-1] if detail else f"git ls-files exited {proc.returncode}")
    return {entry for entry in proc.stdout.decode("utf-8").split("\0") if entry}


def _walked(root: Path, folder: str) -> set[str]:
    top = root / folder if folder else root
    if not top.is_dir() or top.is_symlink():
        return set()
    found: set[str] = set()
    for current, dirs, names in os.walk(top, followlinks=False):
        here = Path(current)
        dirs[:] = [d for d in dirs if not (here / d).is_symlink()]
        found.update((here / name).relative_to(root).as_posix() for name in names)
    return found


def _in_repository(root: Path) -> bool:
    return any((folder / ".git").exists() for folder in (root, *root.parents))
