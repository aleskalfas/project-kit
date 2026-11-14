"""References read from the remote itself (`git ls-remote`), never from the clone.

A clone may lack a tag cut elsewhere, or hold a branch the remote has moved on from,
so a reader that must see what the remote holds now asks the remote, and refuses
where it cannot. Three readers do: the stranded-script guard, which finds the newest
final release tag (ADR-092 point 8), and a candidate's cut, which counts every
candidate tag (ADR-092 point 3) and checks that its commit has taken in the default
branch's head (ADR-092 point 2). Each refuses in its own words, with the reason
`Unread` carries.
"""

from __future__ import annotations

import shlex
import subprocess
from pathlib import Path

from project_kit import default_branch

#: The remote read: the one `pkit version tag --push` pushes a tag to.
REMOTE = default_branch.REMOTE

#: How long one read of the remote may take before it counts as unread.
TIMEOUT_SECONDS = 60

#: How the remote lists a tag's reference: `refs/tags/<name>`.
TAG_PREFIX = "refs/tags/"

#: How the remote lists a branch's reference: `refs/heads/<name>`.
BRANCH_PREFIX = "refs/heads/"

#: The suffix of the line the remote adds for an annotated tag, naming its commit.
_PEELED = "^{}"


class Unread(Exception):
    """What was asked of the remote cannot be read. The message says why, and the way
    on."""


def tags(root: Path) -> dict[str, str]:
    """Each tag the remote holds, by its full reference (`refs/tags/<name>`), with the
    commit it names: for an annotated tag, the commit it points to. Raises `Unread`
    where the remote's tags cannot be read."""
    named: dict[str, str] = {}
    peeled: dict[str, str] = {}
    for commit, ref in _listed(root, ["--tags"], [], what="the remote's tags"):
        if not ref.startswith(TAG_PREFIX):
            continue
        if ref.endswith(_PEELED):
            peeled[ref.removesuffix(_PEELED)] = commit
        else:
            named[ref] = commit
    named.update(peeled)
    return named


def branch_head(root: Path, name: str) -> str | None:
    """The commit the branch `name` is at on the remote, or None where the remote has
    no such branch. Raises `Unread` where the remote cannot be read."""
    ref = f"{BRANCH_PREFIX}{name}"
    listed = _listed(root, [], [ref], what=f"the head of {name} on {REMOTE}")
    return next((commit for commit, listed_ref in listed if listed_ref == ref), None)


def _listed(
    root: Path, options: list[str], patterns: list[str], *, what: str
) -> list[tuple[str, str]]:
    """Each `(commit, reference)` the remote lists for `git ls-remote <options> origin
    <patterns>`. Raises `Unread`, naming `what` cannot be read, where the command
    fails, cannot run, or gives no answer within `TIMEOUT_SECONDS`."""
    command = ["git", "ls-remote", *options, REMOTE, *patterns]
    shown = shlex.join(command)
    try:
        completed = subprocess.run(
            command,
            cwd=root,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired:
        raise Unread(
            f"{what} cannot be read: `{shown}` gave no answer within {TIMEOUT_SECONDS} "
            "seconds. Reach the remote, and run again."
        ) from None
    except (OSError, subprocess.SubprocessError) as exc:
        raise Unread(f"{what} cannot be read: `{shown}` could not run ({exc}).") from None
    if completed.returncode != 0:
        said = [line.strip() for line in completed.stderr.splitlines() if line.strip()]
        detail = said[0] if said else f"exit status {completed.returncode}"
        raise Unread(
            f"{what} cannot be read: `{shown}` failed (git says: {detail}). "
            "Reach the remote, and run again."
        )
    listed: list[tuple[str, str]] = []
    for line in completed.stdout.splitlines():
        commit, tab, ref = line.partition("\t")
        if tab:
            listed.append((commit.strip(), ref.strip()))
    return listed
