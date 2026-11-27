"""A reviewer's clone: where a reviewer works in a seat's clone (ADR-102 point 2).

In a seat's clone, the review command asks the backbone's run command (`agent_runs`)
to run each reviewer in a clone of its own, and names the commit, the remote and the
references the clone fetches (`ReviewerClone`). So the seat's working tree stays where
the seat left it, and no reviewer works where another does. This module makes that
clone and the folder that holds its run's rules, and removes both once the run ends,
whatever its verdict (`reviewer_clone`):

- **Where it lies.** In the backbone's run root, where a confined run's clone lies
  (`agent_confinement.run_root`): a folder only the person's account writes, outside
  every working tree and outside the per-user temp folder. Each reviewer's run gets a
  folder of its own there, which records the process that made it by the name the
  backbone gives it. Before it makes one, a run removes each folder whose process
  the backbone reads as ended, as a killed review leaves its clone, and keeps one
  whose process runs or of which the backbone cannot tell (ADR-103). Where the run
  root or the run's folder cannot be made or written, as from inside a sandbox on
  Linux, the run is refused with the cause `agent_confinement.RUN_FOLDER`.
- **The clone,** made from the code host, never from the seat's repository: a git
  folder of its own, sharing no object with the seat's, and borrowing none. It
  fetches the default branch with no file contents but those its checkout reads, a
  later read fetching the rest from the code host, and no tag.
- **One remote,** at the address the caller names and under the name it gives, the
  one the default branch resolves through (COR-054). Its default-branch reference is
  set, and its push address is one no push can use.
- **What it fetches:** the default branch, each branch the caller names besides, such
  as the change's base, and the change's head through the code host's reference for
  it. A head that does not resolve to the commit the caller names, the one the
  review stamps in its verdict's marker, refuses the run.
- **At the default branch's head,** the commit the caller names, checked out with no
  branch. A clone that does not hold it refuses the run.
- **No hook.** The clone's git folder holds no hook, and its configuration names
  none, so no git call in it runs one. These git calls run no hook either, and ask
  for no credentials at a terminal. They keep the person's own configuration, which
  reaches the code host as their other git calls do.
- **Its agent workspace,** `.agent-workspace`, made by the run command with the
  guards ADR-060 points 1 and 2 give. A commit that holds anything at that path
  refuses the run.
- **The folder for the run's rules,** beside the clone in the run's folder, where the
  runner writes the settings it passes the harness (ADR-102 point 3). The run does
  not work in it.
"""

from __future__ import annotations

import contextlib
import os
import re
import subprocess
from collections.abc import Generator
from dataclasses import dataclass
from pathlib import Path

from project_kit import agent_confinement, default_branch
from project_kit import recorded_processes as rp
from project_kit.agent_confinement import Refused

#: The folder, beside the clone in the run's folder, that holds the run's rules.
RULES = "rules"

#: A full commit id.
COMMIT_ID = re.compile(r"[0-9a-f]{40}")

#: A remote's name: a letter or digit, then letters, digits, dots, underscores and
#: hyphens, with no `..` and no ending a reference refuses.
REMOTE_NAME = re.compile(r"(?!.*\.\.)(?!.*\.lock$)(?!.*\.$)[A-Za-z0-9][A-Za-z0-9._-]{0,63}")

#: A reference's prefix, and a branch's.
REFS = "refs/"
HEADS = "refs/heads/"

#: How long one git call that makes the clone may take before the run is refused.
GIT_TIMEOUT_SECONDS = 900

#: The variables of git's own that reach these git calls: those that pick the
#: person's own configuration files, and those that carry their way to the code
#: host. Every other variable of git's is left out, so none points a call at another
#: repository or its objects, or adds configuration of its own.
GIT_VARIABLES = (
    "GIT_CONFIG_GLOBAL",
    "GIT_CONFIG_SYSTEM",
    "GIT_CONFIG_NOSYSTEM",
    "GIT_ASKPASS",
    "GIT_SSH",
    "GIT_SSH_COMMAND",
    "GIT_SSH_VARIANT",
    "GIT_PROXY_COMMAND",
    "GIT_SSL_CAINFO",
    "GIT_SSL_CAPATH",
)


@dataclass(frozen=True)
class ReviewerClone:
    """What a caller names for a reviewer's clone (ADR-066 point 2, ADR-102 point 2):
    the `commit` it is checked out at, the default branch's head; the `remote`'s name
    and its `url`; the `default_branch`, whose reference the remote's default-branch
    reference names; the `branches` fetched besides it; and `head_ref`, the code
    host's reference for the change's head, which must resolve to `head`."""

    commit: str
    remote: str
    url: str
    default_branch: str
    branches: tuple[str, ...]
    head_ref: str
    head: str

    def problem(self) -> str | None:
        """Why the clone cannot be asked for as it stands, or None."""
        for named, value in (("commit", self.commit), ("head", self.head)):
            if not COMMIT_ID.fullmatch(value):
                return (
                    f"the reviewer's clone's {named} {value!r} is not a full commit id, 40 "
                    "lowercase hex digits"
                )
        if not REMOTE_NAME.fullmatch(self.remote):
            return f"the reviewer's clone's remote {self.remote!r} is not a remote's name"
        if not self.url or self.url.startswith("-") or _unprintable(self.url):
            return f"the reviewer's clone's address {self.url!r} is not an address"
        for branch in (self.default_branch, *self.branches):
            if not default_branch.is_branch_name(branch):
                return f"the reviewer's clone's branch {branch!r} is not a branch's name"
        if not self.head_ref.startswith(REFS) or not default_branch.is_branch_name(
            self.head_ref.removeprefix(REFS)
        ):
            return f"the reviewer's clone's head reference {self.head_ref!r} is not a reference"
        return None

    def tracking(self, ref: str) -> str:
        """The reference of the clone that holds the code host's `ref`: under the
        remote's own references, a branch by its name, any other reference by its
        name below `refs/`."""
        name = ref.removeprefix(HEADS) if ref.startswith(HEADS) else ref.removeprefix(REFS)
        return f"refs/remotes/{self.remote}/{name}"


@dataclass(frozen=True)
class Made:
    """One reviewer's run's folders, as `reviewer_clone` made them: the run's
    `folder`, the `clone` in it, the clone's `workspace`, and the folder for the run's
    `rules`."""

    folder: Path
    clone: Path
    workspace: Path
    rules: Path


def _unprintable(text: str) -> bool:
    """Whether `text` holds whitespace or a character that is not printable."""
    return any(char.isspace() or not char.isprintable() for char in text)


def _environment() -> dict[str, str]:
    """The environment of the git calls that make the clone: the caller's, with only
    the variables of git's that `GIT_VARIABLES` names, and no prompt for credentials
    at a terminal."""
    env = {
        name: value
        for name, value in os.environ.items()
        if not name.startswith("GIT_") or name in GIT_VARIABLES
    }
    env["GIT_TERMINAL_PROMPT"] = "0"
    return env


def _git(cwd: Path, *args: str) -> str | list[str]:
    """Run git with `args` from `cwd`, with no hook and no external transport, in
    `_environment`. Its standard output as lines when it exits 0; else why it failed,
    as one string."""
    try:
        done = subprocess.run(
            [
                "git",
                "-c",
                f"core.hooksPath={os.devnull}",
                "-c",
                "protocol.ext.allow=never",
                *args,
            ],
            cwd=cwd,
            env=_environment(),
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=GIT_TIMEOUT_SECONDS,
            check=False,
        )
    except FileNotFoundError:
        return "git is not on the PATH"
    except subprocess.TimeoutExpired:
        return f"git {args[0]} did not finish within {GIT_TIMEOUT_SECONDS} s"
    except OSError as exc:
        return f"git could not start: {exc}"
    if done.returncode != 0:
        said = [line.strip() for line in done.stderr.splitlines() if line.strip()]
        return f"git {args[0]} exited {done.returncode}" + (f": {said[-1]}" if said else "")
    return done.stdout.splitlines()


def _must(cwd: Path, what: str, *args: str) -> list[str]:
    """Run git as `_git` does; raise `Refused` naming `what` where it fails."""
    done = _git(cwd, *args)
    if isinstance(done, str):
        raise Refused(f"the reviewer's clone {what}: {done}")
    return done


def make_clone(wanted: ReviewerClone, clone: Path) -> None:
    """Make the reviewer's clone `wanted` names in `clone`, from the code host, at its
    commit, with no branch checked out.

    Raises `Refused` where the clone cannot be made or fetched, borrows objects from
    another repository, holds no such commit, or where the change's head does not
    resolve to the head `wanted` names."""
    _must(
        clone.parent,
        "cannot be made",
        "clone",
        "--quiet",
        "--no-local",
        "--no-hardlinks",
        "--no-checkout",
        "--filter=blob:none",
        "--single-branch",
        "--branch",
        wanted.default_branch,
        "--no-tags",
        "--template=",
        "--origin",
        wanted.remote,
        "--",
        wanted.url,
        str(clone),
    )
    _must(clone, "cannot be configured", "config", "core.hooksPath", os.devnull)
    _must(clone, "cannot be configured", "config", f"remote.{wanted.remote}.pushurl", os.devnull)
    branches = [branch for branch in wanted.branches if branch != wanted.default_branch]
    refspecs = [f"+{HEADS}{branch}:{wanted.tracking(HEADS + branch)}" for branch in branches]
    refspecs.append(f"+{wanted.head_ref}:{wanted.tracking(wanted.head_ref)}")
    _must(clone, "cannot fetch", "fetch", "--quiet", "--no-tags", wanted.remote, *refspecs)
    if os.path.lexists(clone / ".git" / "objects" / "info" / "alternates"):
        raise Refused("the reviewer's clone borrows objects from another repository")
    _check_head(wanted, clone)
    if isinstance(_git(clone, "cat-file", "-e", f"{wanted.commit}^{{commit}}"), str):
        raise Refused(
            f"the reviewer's clone does not hold {wanted.commit}, the head of "
            f"`{wanted.default_branch}` the review names"
        )
    _must(
        clone,
        f"cannot be checked out at {wanted.commit}",
        "-c",
        "advice.detachedHead=false",
        "checkout",
        "--quiet",
        "--detach",
        wanted.commit,
    )
    _must(
        clone,
        "cannot set its remote's default branch",
        "remote",
        "set-head",
        wanted.remote,
        wanted.default_branch,
    )
    try:
        held = (clone / ".git" / "HEAD").read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise Refused(f"the reviewer's clone has no HEAD to read: {exc.strerror or exc}") from exc
    if held != wanted.commit:
        raise Refused(
            f"the reviewer's clone is at {held!r} after the checkout, not at {wanted.commit}"
        )


def _check_head(wanted: ReviewerClone, clone: Path) -> None:
    """Refuse the run where the change's head, as the clone fetched it, is not the
    head `wanted` names (ADR-102 point 2)."""
    local = wanted.tracking(wanted.head_ref)
    found = _git(clone, "rev-parse", "--verify", "--quiet", f"{local}^{{commit}}")
    resolved = found[0].strip() if isinstance(found, list) and found else ""
    if resolved != wanted.head:
        shown = resolved or "no commit"
        raise Refused(
            f"the change's head, `{wanted.head_ref}` at the code host, resolves to {shown}, "
            f"not {wanted.head}, the head the review names, so no other commit is reviewed"
        )


@contextlib.contextmanager
def reviewer_clone(project_root: Path, wanted: ReviewerClone) -> Generator[Made]:
    """The folders of one reviewer's run, for the length of the block.

    Makes the run root and removes the folders of runs whose process the backbone
    reads as ended, then makes the run's folder, the clone, its workspace and the
    folder for the run's rules. Raises `Refused` when any of these cannot be made.
    The run's folder, the clone with it, is removed on every exit."""
    root = agent_confinement.run_root(project_root)
    system = rp.this_system()
    asking = agent_confinement.reader(project_root, system)
    agent_confinement.remove_stale(root, asking, system)
    folder = agent_confinement.make_run_folder(root, asking, system)
    try:
        clone = folder / agent_confinement.CLONE
        make_clone(wanted, clone)
        workspace = agent_confinement.make_agent_workspace(clone)
        rules = folder / RULES
        try:
            rules.mkdir(mode=0o700)
        except OSError as exc:
            raise Refused(
                f"the folder for the run's rules cannot be made: {exc.strerror or exc}",
                cause=agent_confinement.RUN_FOLDER,
            ) from exc
        yield Made(folder=folder, clone=clone, workspace=workspace, rules=rules)
    finally:
        agent_confinement.remove_tree(folder)
