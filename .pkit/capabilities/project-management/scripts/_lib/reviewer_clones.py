"""Where `review-pr`'s reviewers work in a seat's clone (ADR-102 points 1, 2 and 4).

In a seat's clone, each reviewer works in a clone of its own, which the backbone's
run command makes from the code host and removes once the run ends. So the seat's
working tree stays where the seat left it, whatever a reviewer does in its working
folder, and no reviewer works where another does. Elsewhere, reviewers work in the
checkout the command runs in, as before (ADR-066 point 10).

- `in_seat_clone` tells a seat's clone as the build command does (ADR-073 point 8):
  the runtime folder's identity names a seat (DEC-059 point 6), read as a hint
  alone (ADR-100 point 5). A linked worktree is never one, until a record decides
  how it reads its clone's identity (DEC-059 point 6).
- `read_clone` reads, from the code host, what the run command needs to make the
  clone (`agent_runs.ReviewerClone`): the default branch's head as the code host
  holds it when the review starts, the address it gives for the base repository,
  and the references to fetch: the change's base and the code host's reference for
  the change's head, which must resolve to the head the review names. The remote
  takes the name of the one the default branch resolves through (COR-054).
- `brief` is what the reviewer's brief says of its clone (point 4): its working
  tree holds the default branch's head, not the change, and it reads the change by
  its diff and by its files at the head's commit.
- `RUN_FOLDER_WAY_OUT` names a review at the person's own terminal, where the run
  command cannot write its folder for the run, as from inside a sandbox on Linux.
"""

from __future__ import annotations

import json
import re
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

from _lib import agent_runs, default_branch, instance_identity, pr_head
from _lib.gh import gh_run

#: A full commit id, as the code host gives one.
COMMIT_ID = re.compile(r"[0-9a-f]{40}")

#: The prefixes of an address git reaches over ssh.
SSH_PREFIXES = ("git@", "ssh://")

#: The query of the code host for the base repository's addresses and the default
#: branch's head, in one call.
QUERY = (
    "query($owner: String!, $repo: String!, $ref: String!) "
    "{ repository(owner: $owner, name: $repo) "
    "{ url sshUrl ref(qualifiedName: $ref) { target { oid } } } }"
)

#: What a reviewer is told of a refusal where the run command cannot write its
#: folder for the run (ADR-102 point 2).
RUN_FOLDER_WAY_OUT = (
    "the backbone cannot write its folder for the reviewer's clone here, as from inside "
    "a sandbox on Linux. Run `pkit pm review-pr {issue}` at your own terminal, outside "
    "the sandbox, to review in a seat's clone"
)

#: A git call: its arguments after `git`, run in the folder given, answering its
#: completed process.
Git = Callable[..., subprocess.CompletedProcess[str]]


def in_seat_clone(capability_root: Path, repo_root: Path, git: Git | None = None) -> bool:
    """Whether `repo_root` is a seat's clone: its runtime folder names a seat, and it
    is not a linked worktree. Where git cannot tell whether it is one, it reads as a
    seat's clone, so its reviewers work in clones of their own."""
    if instance_identity.read_seat_hint(capability_root) is None:
        return False
    return not _linked_worktree(repo_root, git or _git)


def _linked_worktree(repo_root: Path, git: Git) -> bool:
    """Whether `repo_root` is a linked worktree: its git folder is not its
    repository's common one. False where git cannot tell."""
    try:
        done = git(
            "rev-parse", "--path-format=absolute", "--git-dir", "--git-common-dir", cwd=repo_root
        )
    except OSError:
        return False
    lines = [line.strip() for line in done.stdout.splitlines() if line.strip()]
    if done.returncode != 0 or len(lines) != 2:
        return False
    own, common = (Path(line).resolve() for line in lines)
    return own != common


def _git(*argv: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *argv], cwd=cwd, capture_output=True, text=True, check=False)


def read_clone(
    pr_number: int,
    head: str,
    base: str | None,
    config: dict[str, Any],
    *,
    git: Git | None = None,
) -> agent_runs.ReviewerClone | str:
    """The clone a reviewer of pull request `pr_number` works in, at `head`, the head
    the review names, against the branch `base`; or why none can be asked for."""
    if not COMMIT_ID.fullmatch(head):
        return (
            f"PR #{pr_number}'s head could not be read, so no reviewer's clone can be "
            "checked against it"
        )
    try:
        default = default_branch.name(config)
    except default_branch.Unanswered as exc:
        return f"the default branch cannot be read: {exc}"
    remote = pr_head.base_remote(default)
    found = _read_host(default, config)
    if isinstance(found, str):
        return f"the code host's base repository cannot be read: {found}"
    url, ssh_url, commit = found
    address = ssh_url if _over_ssh(remote, git or _git) else url
    branches = (base,) if base and base != default else ()
    return agent_runs.ReviewerClone(
        commit=commit,
        remote=remote,
        url=address,
        default_branch=default,
        branches=branches,
        head_ref=f"refs/pull/{pr_number}/head",
        head=head,
    )


def _over_ssh(remote: str, git: Git) -> bool:
    """Whether this checkout reaches `remote` over ssh, so its clone does too, with
    the person's own credentials."""
    try:
        done = git("remote", "get-url", remote)
    except OSError:
        return False
    return done.returncode == 0 and done.stdout.strip().startswith(SSH_PREFIXES)


def _read_host(default: str, config: dict[str, Any]) -> tuple[str, str, str] | str:
    """The base repository's https and ssh addresses, and the head of branch
    `default`, as the code host gives them; or why it did not answer."""
    argv = ["gh", "api", "graphql", "-f", f"query={QUERY}", "-F", "owner={owner}"]
    argv += ["-F", "repo={repo}", "-f", f"ref=refs/heads/{default}"]
    try:
        proc = gh_run(argv, config, check=False)
    except FileNotFoundError:
        return "`gh` not on PATH"
    if proc.returncode != 0:
        return (proc.stderr or "").strip() or f"gh exited {proc.returncode}"
    try:
        payload = json.loads(proc.stdout or "null")
    except ValueError:
        return "gh's answer is not JSON"
    repository = _dig(payload, "data", "repository")
    if not isinstance(repository, dict):
        return "gh's answer names no repository"
    url, ssh_url = repository.get("url"), repository.get("sshUrl")
    oid = _dig(repository, "ref", "target", "oid")
    if not isinstance(url, str) or not url or not isinstance(ssh_url, str) or not ssh_url:
        return "gh's answer gives no address of the repository"
    if not isinstance(oid, str) or not COMMIT_ID.fullmatch(oid):
        return f"gh's answer gives no head of `{default}`"
    return url, ssh_url, oid


def _dig(value: object, *keys: str) -> object:
    """`value[k1][k2]...`, or None where a step is not a mapping holding the key."""
    for key in keys:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def brief(clone: agent_runs.ReviewerClone, sha: str) -> str:
    """What a reviewer's brief says of the clone it works in (ADR-102 point 4)."""
    return (
        "You work in a clone of your own, made for this review and removed once it ends. "
        f"Its working tree holds the default branch's head, {clone.commit}, not the change. "
        f"Read the change by its diff and by its files at the head's commit, as `git show "
        f"{sha}:<path>` reads one; the clone fetched the head from the code host. A file "
        "you write, a checkout or a program you run here stays in your clone."
    )
