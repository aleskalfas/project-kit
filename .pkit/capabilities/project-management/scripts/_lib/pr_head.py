"""A pull request's head: where it is fetched from, and the one fetch of a commit
this clone lacks (#2663).

- `Source` is where a pull request's head is fetched from, and
  `pull_request_source` gives it. For a pull request from the base's own
  repository, it is the remote the branch is pushed to (`branch_remote`) and the
  branch. For one from a fork, it is the base's remote (`base_remote`) and the ref
  the base repository keeps for the pull request. `remote_branch` reads the remote
  and the branch of a base the backbone resolved to a remote-tracking reference.
- `fetch(oid, source)` fetches commit `oid` where this clone lacks it
  (`has_commit`): by `source`'s ref, or, given no source, by its object name from
  origin. It never prompts for credentials, since a pm script runs unattended, and
  it brings no tags. `Fetched` says whether the commit is here afterwards, and
  what git said where it is not. `fetch_head` is that fetch for a pull request's
  head, with why the head is still missing, as a line says it.

Every git call goes through a `Git`: this module's own, unless the caller passes
one. `author_delta` passes one that runs in its directory, through the runner its
tests stand in.
"""

from __future__ import annotations

import os
import subprocess
from collections.abc import Callable
from dataclasses import dataclass

# Sibling _lib import, dual-form as `friction_answers` imports it, so this module
# and that one share it whichever form loaded them.
try:
    import default_branch  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover
    from _lib import default_branch  # type: ignore[no-redef]

#: The remote a commit is fetched from by its object name, and the one a branch or
#: a base falls back to where it names none.
ORIGIN = "origin"
#: How many characters of a commit's id a line names.
SHORT = 7
#: What every fetch adds to the environment: git never prompts for credentials.
NO_PROMPT = {"GIT_TERMINAL_PROMPT": "0"}

#: A git call: its arguments after `git`, and `env`, the environment to run it in, or
#: None for this process's own. It returns git's completed process, its output text.
Git = Callable[..., subprocess.CompletedProcess[str]]


@dataclass(frozen=True)
class Source:
    """Where a pull request's head is fetched from, where this clone lacks it: a
    remote, and a ref in the repository it names. For a pull request from the base's
    own repository, the remote its branch is pushed to and the branch. For one from a
    fork, the base's remote, as `friction_answers` fetches the base, and the ref the
    base repository keeps for the pull request: the fork is a repository this clone
    may name no remote for."""

    remote: str
    ref: str


def pull_request_source(
    branch: str, number: int, *, cross_repository: bool, base: str, remote: str | None = None
) -> Source:
    """The `Source` of pull request `number`, opened from `branch` into the branch
    `base`. From a fork: the base's remote (`base_remote`) and `refs/pull/<number>/head`.
    Otherwise: `remote`, else the remote the branch is pushed to (`branch_remote`), and
    the branch."""
    if cross_repository:
        return Source(base_remote(base), f"refs/pull/{number}/head")
    return Source(remote or branch_remote(branch), f"refs/heads/{branch}")


def base_remote(base: str) -> str:
    """The remote the branch `base` is fetched from, as `friction_answers` fetches the
    base, and `origin` where it resolves to no remote's branch, as `branch_remote`
    falls back."""
    try:
        found = default_branch.check_base(base)
    except default_branch.Unanswered:
        return ORIGIN
    remote = remote_branch(found)
    return remote[0] if remote is not None else ORIGIN


def remote_branch(found: default_branch.Base) -> tuple[str, str] | None:
    """The remote and the branch of a base the backbone resolved to a remote-tracking
    reference, or None for any other base."""
    if found.resolved != "remote":
        return None
    remote, slash, branch = found.ref.partition("/")
    return (remote, branch) if slash and remote and branch else None


def branch_remote(branch: str) -> str:
    """The remote `branch` is pushed to — its push remote, else the remote it
    tracks — and `origin` when it names none, as start-work resolves a branch
    (COR-054 point 2)."""
    for atom in ("push:remotename", "upstream:remotename"):
        remote = _git("for-each-ref", f"--format=%({atom})", f"refs/heads/{branch}").stdout
        if remote.strip() and remote.strip() != ".":
            return remote.strip()
    return ORIGIN


def has_commit(oid: str, git: Git | None = None) -> bool:
    """Whether this clone holds commit `oid`."""
    return (git or _git)("cat-file", "-e", f"{oid}^{{commit}}").returncode == 0


@dataclass(frozen=True)
class Fetched:
    """Whether commit `oid` is in this clone after `fetch`. Where a fetch ran, the
    remote and the ref it fetched, how git exited and what git said, a line each,
    blank ones left out."""

    oid: str
    held: bool
    remote: str = ""
    ref: str = ""
    returncode: int = 0
    said: tuple[str, ...] = ()


def fetch(oid: str, source: Source | None = None, *, git: Git | None = None) -> Fetched:
    """Fetch commit `oid` where this clone lacks it: from `source`'s remote by its ref,
    or, where no source is given, from origin by the commit's object name. It never
    prompts for credentials and brings no tags."""
    run = git or _git
    if has_commit(oid, run):
        return Fetched(oid, held=True)
    remote, ref = (source.remote, source.ref) if source is not None else (ORIGIN, oid)
    proc = run("fetch", "--quiet", "--no-tags", remote, ref, env={**os.environ, **NO_PROMPT})
    said = tuple(line.strip() for line in (proc.stderr or "").splitlines() if line.strip())
    return Fetched(oid, has_commit(oid, run), remote, ref, proc.returncode, said)


def fetch_head(head: str, source: Source) -> str | None:
    """Fetch commit `head` from `source` where this clone lacks it: why it is still
    missing, or None."""
    found = fetch(head, source)
    if found.held:
        return None
    return f"the head {head[:SHORT]} is not in this clone, and fetching {source.ref} from " + (
        f"{source.remote} failed: {found.said[-1]}"
        if found.said
        else f"{source.remote} did not bring it"
    )


def _git(*argv: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *argv], capture_output=True, text=True, check=False, env=env)
