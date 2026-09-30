"""The default branch: declared once, resolved one way (COR-054).

A project declares the branch its settled work lands on once, in the backbone
configuration — `repository.default-branch`, `main` when absent (point 1) —
and every reader of settled state resolves it here (point 5):

- **The default branch** (`resolve`): the declared name, then the commit it
  resolves to — the remote-tracking reference `origin/<name>` when it names a
  commit, else the local branch `<name>` (point 2). When neither does, the
  answer carries no commit and says why, with the fixes; nothing is guessed
  (point 4).
- **The base of a comparison** (`base`): the reference a run names — an
  explicit one, else `$PKIT_CHECK_BASE` — or else the default branch (point
  3); the commit it names, where HEAD left it (their merge-base, the *fork*)
  and whether it moved on since. The friction change check compares with it
  (`friction_check.resolve_base`), and a capability's script reads it in `pkit
  friction artefacts --json`, so none resolves a base or computes a
  merge-base of its own.

The override is a base, never a declaration: `$PKIT_CHECK_BASE` changes what a
comparison compares with, and never what `resolve` answers.

Reading is forgiving (COR-048 point 4): a configuration that does not parse,
or a value that is not a branch name, reads as the default; the value is kept
in `DefaultBranch.warning` for a reading command to print, and `pkit validate`
reports the file. Git is asked, never written to, and a git that cannot run is
an answer without commits, never an exception.
"""

from __future__ import annotations

import os
import re
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from project_kit.project_config import PROJECT_CONFIG_RELPATH, read_config

#: The configuration block and key the default branch is declared under (point 1).
BLOCK = "repository"
KEY = "default-branch"
DOTTED_KEY = f"{BLOCK}.{KEY}"

#: The name read when none is declared (point 1).
DEFAULT_NAME = "main"

#: The remote whose tracking reference is looked at first (point 2).
REMOTE = "origin"

#: The environment variable a pipeline sets once to name every comparison's base (point 3).
CHECK_BASE_ENV = "PKIT_CHECK_BASE"

#: A value the reading takes as a branch name: no whitespace, and not an option.
#: The configuration schema's pattern for the key is the same.
BRANCH_NAME = re.compile(r"^[^\s-]\S*$")

#: Where a default branch's name came from.
DECLARED = "configuration"
DEFAULTED = "default"

#: Where a comparison's base came from.
OPTION = "option"
ENVIRONMENT = "environment"
DEFAULT_BRANCH = "default-branch"


@dataclass(frozen=True)
class DefaultBranch:
    """The default branch as declared and resolved (points 1, 2 and 4)."""

    name: str
    source: str  # DECLARED or DEFAULTED
    ref: str | None  # `origin/<name>` or `<name>`; `None` when neither names a commit
    commit: str | None
    warning: str | None = None  # a declared value read as the default, and why

    @property
    def problem(self) -> str | None:
        """Why the default branch names no commit here, with the fixes; `None` when it does."""
        if self.commit is not None:
            return None
        return (
            f"the default branch {self.name!r} resolves neither as {remote_ref(self.name)!r} nor "
            f"as {self.name!r} in this repository: fetch it (e.g. `git fetch {REMOTE} "
            f"{self.name}`), declare the right one (`{DOTTED_KEY}` in "
            f"{PROJECT_CONFIG_RELPATH.as_posix()}), or name a base with --base or "
            f"{CHECK_BASE_ENV}."
        )

    def as_json(self) -> dict[str, Any]:
        return {"name": self.name, "source": self.source, "ref": self.ref, "commit": self.commit}


@dataclass(frozen=True)
class Base:
    """What a comparison against settled state compares with (points 3 and 4).

    `ref` is the reference as named, or the default branch's resolved reference
    — its name when neither of its references resolves. `tip` is the commit
    `ref` names; `fork` the merge-base of the tip and HEAD, where HEAD left the
    base; `outdated` whether the tip moved on since (it is not an ancestor of
    HEAD). `problem` is the first reason no comparison can be made — the base
    names no commit, HEAD names none yet, or the two share no history — and
    `None` when one can; the fields after it are then `None`.
    """

    ref: str
    source: str  # OPTION, ENVIRONMENT or DEFAULT_BRANCH
    tip: str | None
    fork: str | None
    outdated: bool | None
    problem: str | None

    def as_json(self) -> dict[str, Any]:
        return {
            "ref": self.ref,
            "source": self.source,
            "tip": self.tip,
            "fork": self.fork,
            "outdated": self.outdated,
            "problem": self.problem,
        }


def remote_ref(name: str) -> str:
    """The remote-tracking reference of the branch `name`."""
    return f"{REMOTE}/{name}"


def declared(target_root: Path) -> tuple[str, str, str | None]:
    """The declared name, where it came from, and — for a value read as the
    default — why: `(name, source, warning)`, forgivingly (COR-048 point 4)."""
    block = read_config(target_root).get(BLOCK)
    value: Any = cast(Mapping[str, Any], block).get(KEY) if isinstance(block, Mapping) else None
    if value is None:
        return DEFAULT_NAME, DEFAULTED, None
    if isinstance(value, str) and BRANCH_NAME.match(value):
        return value, DECLARED, None
    return (
        DEFAULT_NAME,
        DEFAULTED,
        f"{DOTTED_KEY} {value!r} is not a branch name; read as {DEFAULT_NAME!r} — "
        f"`pkit validate` fails on it",
    )


def resolve(target_root: Path) -> DefaultBranch:
    """The default branch: declared, then resolved remote-tracking reference first
    (point 2). Each is looked up by its full reference, so a tag or another ref of
    the same short name never stands in for the branch."""
    name, source, warning = declared(target_root)
    candidates = ((remote_ref(name), f"refs/remotes/{REMOTE}/{name}"), (name, f"refs/heads/{name}"))
    for ref, full in candidates:
        commit = commit_of(target_root, full)
        if commit is not None:
            return DefaultBranch(name, source, ref, commit, warning)
    return DefaultBranch(name, source, None, None, warning)


def base(target_root: Path, explicit: str | None = None) -> Base:
    """The base a comparison against settled state compares HEAD with (point 3):
    `explicit`, else `$PKIT_CHECK_BASE`, else the default branch — its commit, the
    fork and whether it moved on, or the problem that stops a comparison."""
    from_environment = os.environ.get(CHECK_BASE_ENV)
    if explicit is not None:
        return _compared(target_root, explicit, OPTION)
    if from_environment:
        return _compared(target_root, from_environment, ENVIRONMENT)
    branch = resolve(target_root)
    if branch.ref is None or branch.commit is None:
        return Base(branch.name, DEFAULT_BRANCH, None, None, None, branch.problem)
    return _compared(target_root, branch.ref, DEFAULT_BRANCH, branch.commit)


def _compared(target_root: Path, ref: str, source: str, tip: str | None = None) -> Base:
    """`ref`'s commit — `tip` when already resolved — where HEAD left it and whether it
    moved on, or why not."""
    if not ref or ref.startswith("-"):
        return _refused(ref, source, f"the base {ref!r} is not a revision name.")
    tip = tip or commit_of(target_root, ref)
    if tip is None:
        return _refused(
            ref,
            source,
            f"the base {ref!r} does not resolve to a commit in this repository: fetch it "
            f"(e.g. `git fetch {REMOTE} {DEFAULT_NAME}`), or name another with --base or "
            f"{CHECK_BASE_ENV}.",
        )
    head = commit_of(target_root, "HEAD")
    if head is None:
        return Base(
            ref,
            source,
            tip,
            None,
            None,
            "HEAD names no commit yet; a branch is compared with its base, so commit first.",
        )
    found = _git(target_root, "merge-base", tip, head)
    fork = found.stdout.strip() if found is not None and found.returncode == 0 else ""
    if not fork:
        return Base(
            ref,
            source,
            tip,
            None,
            None,
            f"HEAD and the base {ref!r} share no history to compare; in a shallow clone, "
            f"fetch the history back to where the branch left the base (e.g. `git fetch "
            f"--unshallow`).",
        )
    return Base(ref, source, tip, fork, fork != tip, None)


def _refused(ref: str, source: str, problem: str) -> Base:
    return Base(ref, source, None, None, None, problem)


def reading(target_root: Path, explicit: str | None = None) -> dict[str, Any]:
    """What `pkit friction artefacts` adds to its document (point 5): `default_branch`
    as `resolve` answers it, and `base` as `base` answers it for HEAD — whichever
    state the document reads, since both describe the repository as it stands."""
    return {
        "default_branch": resolve(target_root).as_json(),
        "base": base(target_root, explicit).as_json(),
    }


#: How many characters of a commit the human view shows.
_SHORT = 12

#: Where a base came from, in the human view.
_BASE_SOURCES = {
    OPTION: "--base",
    ENVIRONMENT: f"${CHECK_BASE_ENV}",
    DEFAULT_BRANCH: "the default branch",
}


def render_human(document: Mapping[str, Any]) -> str:
    """Two lines for `reading`'s keys: the default branch, and the base."""
    branch = document["default_branch"]
    resolved = (
        f"{branch['ref']} at {branch['commit'][:_SHORT]}"
        if branch["commit"]
        else "resolves to no commit here"
    )
    lines = [f"Default branch: {branch['name']} ({branch['source']}) → {resolved}"]
    found = document["base"]
    line = f"Base: {found['ref']} ({_BASE_SOURCES.get(found['source'], found['source'])})"
    if found["problem"] is not None:
        line += f" — {found['problem']}"
    else:
        line += f" at {found['tip'][:_SHORT]}; HEAD left it at {found['fork'][:_SHORT]}"
        if found["outdated"]:
            line += " (it moved on since)"
    lines.append(line)
    return "\n".join(lines) + "\n"


def commit_of(target_root: Path, name: str) -> str | None:
    """The commit `name` resolves to, or `None` — for a name that is none, or a git
    that cannot answer."""
    if not name or name.startswith("-"):
        return None
    completed = _git(target_root, "rev-parse", "--verify", "--quiet", f"{name}^{{commit}}")
    if completed is None or completed.returncode != 0:
        return None
    return completed.stdout.strip() or None


def _git(target_root: Path, *args: str) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(
            ["git", *args], cwd=target_root, capture_output=True, text=True, check=False
        )
    except OSError:
        return None
