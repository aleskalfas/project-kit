"""The author's changes to a pull request since a reviewed head (#1179).

A reviewer's verdict names the PR head it was shown (`<!-- pkit-verdict
sha=<oid> -->`). Whether it still stands depends on what the author changed
after that head (`_lib.verdict_freshness`), and this module computes that
change from the local repository: the union of the paths each commit after
the reviewed head changed, walking the branch's own line of commits (first
parents) from the PR head back to it.

  * **A merge of the base branch** — a merge commit whose second parent is on
    the base branch — contributes only what the author changed while making
    it: the paths where the merge as committed differs from the clean
    three-way merge of its parents (`git merge-tree --write-tree`). A clean
    merge contributes nothing, so bringing the base branch in leaves every
    verdict standing; a conflict the author resolved, or an edit made inside
    the merge, is the author's change.
  * **Any other commit** contributes its own diff against its first parent —
    a merge of anything other than the base branch included, since what it
    brings in has been reviewed nowhere on this PR.

The computation needs the commits locally and git 2.38 or later (for
`merge-tree --write-tree`). When it cannot run — the reviewed head is no
longer in the branch's history after a rebase or force-push, a commit is not
in this checkout, git is too old or missing — the result is an error rather
than a set of paths, and the freshness rule holds the verdict stale (fail
closed).

This module owns only the `git` wiring. The runner is injectable so the
consumers' tests can stand it in, and it runs in the current directory —
every pm script runs from the project root.
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

try:
    from _lib.audit import short_sha
except ImportError:  # pragma: no cover - exercised via spec-loaded fallback
    from audit import short_sha  # type: ignore[no-redef]


@dataclass(frozen=True)
class AuthorDelta:
    """The paths the author changed since a reviewed head, or why they cannot
    be read.

    `ok` is False when `error` is set; `paths` is then empty and means
    nothing — a consumer reads `error` first.
    """

    paths: tuple[str, ...] = ()
    error: str = ""

    @property
    def ok(self) -> bool:
        return not self.error


# The `subprocess.run`-shaped runner every git call goes through.
RunFn = Callable[..., subprocess.CompletedProcess]


class _GitFailed(Exception):
    """A git step could not establish what it was asked; the message says
    which and why, in words an operator can act on."""


def author_delta(
    since: str,
    head: str,
    *,
    base_tip: str,
    cwd: str | Path | None = None,
    run: RunFn = subprocess.run,
) -> AuthorDelta:
    """The author's changes from `since` (a reviewed head) to `head`.

    `base_tip` is the base branch's head commit (the PR's `baseRefOid`): a
    merge whose second parent it contains is a merge of the base branch. See
    the module docstring for what each commit contributes and when the
    result is an error.
    """
    if not head:
        return AuthorDelta(error="the pull request's head is unknown")
    if since == head:
        return AuthorDelta()
    git = _Git(cwd, run)
    try:
        git.require_commit(since, "the reviewed head")
        git.require_commit(head, "the pull request's head")
        if not git.is_ancestor(since, head):
            raise _GitFailed(
                f"{short_sha(since)} is no longer in the branch's history — "
                "the branch was rebased or force-pushed"
            )
        base = _BaseBranch(git, base_tip)
        paths: set[str] = set()
        for commit, parents in git.first_parent_line(since, head):
            if len(parents) == 2 and base.contains(parents[1]):
                merged = git.clean_merge(parents[0], parents[1])
                paths |= git.changed_paths(merged, commit)
            else:
                paths |= git.changed_paths(parents[0], commit)
    except _GitFailed as exc:
        return AuthorDelta(error=str(exc))
    return AuthorDelta(paths=tuple(sorted(paths)))


class _Git:
    """The git steps `author_delta` takes, each failing as `_GitFailed`."""

    def __init__(self, cwd: str | Path | None, run: RunFn) -> None:
        self._cwd = cwd
        self._run = run

    def __call__(self, *args: str) -> subprocess.CompletedProcess:
        try:
            return self._run(
                ["git", *args],
                cwd=self._cwd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
        except OSError as exc:
            raise _GitFailed(f"git could not run: {exc}") from None

    def has_commit(self, oid: str) -> bool:
        return self("cat-file", "-e", f"{oid}^{{commit}}").returncode == 0

    def require_commit(self, oid: str, what: str) -> None:
        if not self.has_commit(oid):
            raise _GitFailed(
                f"{what}, {short_sha(oid)}, is not in this checkout — fetch "
                "the pull request's branch"
            )

    def is_ancestor(self, ancestor: str, descendant: str) -> bool:
        proc = self("merge-base", "--is-ancestor", ancestor, descendant)
        if proc.returncode in (0, 1):
            return proc.returncode == 0
        raise _GitFailed(f"git merge-base failed: {proc.stderr.strip()}")

    def first_parent_line(self, since: str, head: str) -> list[tuple[str, list[str]]]:
        """The commits from `head` back to `since` along first parents, each
        with its parents, newest first; `since` must be on that line."""
        proc = self("rev-list", "--first-parent", "--parents", f"{since}..{head}")
        if proc.returncode != 0:
            raise _GitFailed(f"git rev-list failed: {proc.stderr.strip()}")
        line: list[tuple[str, list[str]]] = []
        for text in proc.stdout.splitlines():
            oids = text.split()
            if len(oids) < 2:
                raise _GitFailed(f"git rev-list listed a commit without parents: {text!r}")
            line.append((oids[0], oids[1:]))
        if not line or line[-1][1][0] != since:
            raise _GitFailed(
                f"{short_sha(since)} is not on the branch's own line of commits "
                "— it reached the branch through a merge"
            )
        return line

    def clean_merge(self, first: str, second: str) -> str:
        """The tree a clean three-way merge of the two commits produces."""
        proc = self("merge-tree", "--write-tree", first, second)
        # 0: merged cleanly; 1: merged with conflicts, the tree carries them.
        if proc.returncode in (0, 1) and proc.stdout.strip():
            return proc.stdout.split("\n", 1)[0].strip()
        raise _GitFailed(
            "git merge-tree --write-tree failed (it needs git 2.38 or later): "
            f"{proc.stderr.strip()}"
        )

    def changed_paths(self, before: str, after: str) -> set[str]:
        proc = self(
            "diff-tree",
            "-r",
            "--name-only",
            "--no-renames",
            "-z",
            before,
            after,
        )
        if proc.returncode != 0:
            raise _GitFailed(f"git diff-tree failed: {proc.stderr.strip()}")
        return {path for path in proc.stdout.split("\0") if path}


class _BaseBranch:
    """Whether a commit is on the base branch, its head checked once and only
    when a merge needs it — a PR without merges never reads it."""

    def __init__(self, git: _Git, tip: str) -> None:
        self._git = git
        self._tip = tip
        self._checked = False

    def contains(self, commit: str) -> bool:
        if not self._checked:
            if not self._tip:
                raise _GitFailed(
                    "the base branch's head is unknown, so a merge of it "
                    "cannot be told from the author's own changes"
                )
            if not self._git.has_commit(self._tip):
                raise _GitFailed(
                    f"the base branch's head, {short_sha(self._tip)}, is not "
                    "in this checkout — fetch the base branch"
                )
            self._checked = True
        return self._git.is_ancestor(commit, self._tip)
