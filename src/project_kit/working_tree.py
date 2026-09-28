"""The one listing of the working tree (ADR-057 point 2).

Validation, the friction writers, the configuration pass's pattern check and
the change check's head side all ask which files the working tree holds, and
they ask here — so from one state of the repository they find the same files,
and the same artefacts in them:

- **Inside a git work tree** (`WorkingTree`): the files git sees — tracked
  ones, and untracked ones git does not ignore — each a regular file or a
  link. A file deleted from disk but still in the index is not held, and
  nothing beneath a nested repository is. This is the change check's head
  (COR-050 point 6), and what every other reader of the working tree lists.
- **Where git gives no view of it** (`FilesystemTree`) — outside a git work
  tree, or without git — there is no change check to agree with, and every
  regular file and link under the root is listed, `.git` left out. That is the
  one difference between the two listings: git's own rules — its ignore rules,
  and not looking inside a nested repository — do not apply, so a file they
  would leave out is listed. `tests/test_working_tree.py` pins it.

In both, a link is a file of the listing: listed, never followed — nothing is
listed beneath a link to a folder — and never read (`read_file` answers
`None`), as git's listing of a commit never follows one either. A file's
content is its bytes on disk.

Within one run of `pkit validate` the listing is taken once (`working_tree`,
through `validators.once_per_run`); outside a run it is taken afresh.
"""

from __future__ import annotations

import os
import stat
import subprocess
from collections.abc import Mapping, Sequence
from functools import cached_property
from pathlib import Path

import click

from project_kit import validators

# git's own store, never a file of the working tree.
GIT_DIR = ".git"


class WorkingTreeError(click.ClickException):
    """The working tree could not be listed or read: git failed, or a file would not open."""


def nul_separated(raw: bytes) -> list[str]:
    """The items of NUL-separated git output (`-z`), as text."""
    return [item.decode("utf-8", "surrogateescape") for item in raw.split(b"\0") if item]


class WorkingTree:
    """The working tree as git sees it: tracked files and untracked ones git does not ignore.

    A `RepositoryTree` (`friction_discovery`). A file deleted from disk but
    still in the index is not held; an ignored file is not either, so the
    working tree and a commit are listed alike.
    """

    def __init__(self, root: Path) -> None:
        self.root = root

    def files(self) -> Sequence[str]:
        """Every file held, links included: repository-relative POSIX paths, sorted."""
        return self._files

    @cached_property
    def _files(self) -> tuple[str, ...]:
        try:
            completed = subprocess.run(
                ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
                cwd=self.root,
                capture_output=True,
                check=False,
            )
        except OSError as exc:
            raise WorkingTreeError(f"cannot run git: {exc}") from exc
        if completed.returncode != 0:
            detail = completed.stderr.decode("utf-8", "replace").strip()
            raise WorkingTreeError(
                f"`git ls-files` failed: {detail or f'exit status {completed.returncode}'}"
            )
        # A path in conflict is listed once per stage: held once.
        listed = set(nul_separated(completed.stdout))
        return tuple(sorted(rel for rel in listed if self._holds(rel)))

    def _holds(self, rel: str) -> bool:
        """A regular file or a link; not a folder (a nested repository), not a deleted file."""
        try:
            mode = os.lstat(self.root / rel).st_mode
        except OSError:
            return False  # deleted in the working tree
        return stat.S_ISREG(mode) or stat.S_ISLNK(mode)

    def read_file(self, rel: str) -> bytes | None:
        """The file's bytes; `None` for a link or a path the tree does not hold as a file.

        Raises `OSError` when the file will not open; each reader decides what that means.
        """
        path = self.root / rel
        if path.is_symlink() or not path.is_file():
            return None
        return path.read_bytes()

    def read_bytes(self, paths: Sequence[str]) -> Mapping[str, bytes | None]:
        """Each path's content (`read_file`); a file that will not open refuses the read."""
        contents: dict[str, bytes | None] = {}
        for rel in paths:
            try:
                contents[rel] = self.read_file(rel)
            except OSError as exc:
                raise WorkingTreeError(f"cannot read {rel}: {exc}") from exc
        return contents


class FilesystemTree(WorkingTree):
    """The working tree where git gives no view of it: every regular file and link under the root.

    It differs from `WorkingTree` only in its listing — git's ignore rules and
    nested repositories do not apply — and reads files the same way.
    """

    @cached_property
    def _files(self) -> tuple[str, ...]:
        held: list[str] = []
        for directory, folders, names in os.walk(self.root):
            base = Path(directory)
            if base == self.root:
                folders[:] = [f for f in folders if f != GIT_DIR]
                names = [n for n in names if n != GIT_DIR]
            for folder in list(folders):
                if (base / folder).is_symlink():
                    folders.remove(folder)  # a link is listed, never followed
                    names.append(folder)
            for name in names:
                rel = (base / name).relative_to(self.root).as_posix()
                if self._holds(rel):
                    held.append(rel)
        return tuple(sorted(held))


def in_git_work_tree(root: Path) -> bool:
    """Whether git gives a view of the working tree at `root`."""
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=root,
            capture_output=True,
            check=False,
        )
    except OSError:
        return False  # no git at all
    return completed.returncode == 0 and completed.stdout.strip() == b"true"


def working_tree(target_root: Path) -> WorkingTree:
    """The working tree's one listing: git's view inside a git work tree, every file elsewhere.

    Taken once per run of `pkit validate` and shared by every member that reads it.
    """
    return validators.once_per_run(
        ("working-tree", target_root.resolve()),
        lambda: WorkingTree(target_root)
        if in_git_work_tree(target_root)
        else FilesystemTree(target_root),
    )
