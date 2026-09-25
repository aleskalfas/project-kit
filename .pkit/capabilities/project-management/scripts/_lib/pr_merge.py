"""The merge convention's mechanic — ONE implementation, shared by `done-work`
and `merge-pr` (git-conventions.yaml's `merge` entry, DEC-013).

The convention is stated by outcome: one squash commit on the base branch
whose subject is the PR title, no merge commits, and the head branch deleted
on merge. This module realises that outcome in three steps a verb composes:

  1. :func:`squash_merge` — `gh pr merge --squash --subject <PR title>`,
     deliberately WITHOUT `--delete-branch`. That flag makes gh check out the
     default branch locally and delete the local head, and the whole command
     exits non-zero when the working tree cannot do so (a detached HEAD; the
     default branch checked out in another worktree) — AFTER the remote merge
     has already landed (#878, #587). Keeping the merge to the remote half
     means its exit code reports the merge and nothing else.
  2. :func:`delete_remote_branch` — the head ref goes through the API, which
     needs nothing from the working tree. Best-effort.
  3. :func:`cleanup_local` — `checkout <default>`, `pull --ff-only`,
     `branch -D <head>`. Every step warns with git's reason and continues;
     none can fail the verb.

A verb runs its own irreversible-merge follow-up (done-work's issue
transition, merge-pr's after-merge hooks) between 1 and 2, so no best-effort
step stands between the merge and the thing that must not be skipped.
"""

from __future__ import annotations

import subprocess
import sys
from typing import Any

from _lib.gh import gh_run

_ALREADY_DELETED_MARKER = "Reference does not exist"


def squash_merge(
    pr_number: int | None, *, pr_title: str, admin: bool, config: dict[str, Any]
) -> bool:
    """Squash-merge the PR with the PR title as the landed commit subject.

    Returns True when the remote merge landed, False otherwise (an error line
    is printed). No `--delete-branch` — see the module docstring.
    """
    if pr_number is None:
        print("error: no PR number to merge.", file=sys.stderr)
        return False
    # Force --subject to the PR title so the squash-commit subject equals the
    # gate-validated title for both single- and multi-commit PRs.  GitHub's
    # default for a single-commit PR is the commit message, not the title —
    # the --subject flag overrides that (DEC-013; fixes #33).
    cmd = [
        "gh", "pr", "merge", str(pr_number),
        "--squash",
        "--subject", pr_title,
    ]
    if admin:
        cmd.append("--admin")
    try:
        proc = gh_run(cmd, config, check=False)
    except FileNotFoundError:
        print("error: `gh` not on PATH.", file=sys.stderr)
        return False
    if proc.returncode != 0:
        print(
            f"error: gh pr merge failed (exit {proc.returncode}): "
            f"{proc.stderr.strip()}",
            file=sys.stderr,
        )
        return False
    return True


def delete_remote_branch(
    branch: str, config: dict[str, Any], *, cross_repository: bool,
) -> None:
    """Delete the PR's remote head ref through the API — best-effort.

    `cross_repository` is required and has no default: the ref is deleted in
    the BASE repository (`{owner}/{repo}` resolves there), so for a PR whose
    head lives in a fork the head-branch name is chosen by the fork's author
    and may name an unrelated branch of the base repo. Such a PR's head is
    never deleted here — the fork owns its branch. Every caller must state
    which case it is in, so a later caller cannot reintroduce the hole.

    The API call needs nothing from the working tree, so a detached HEAD or a
    default branch held by another worktree cannot fail it. A ref that is
    already gone (a repository that auto-deletes head branches on merge) is
    reported, not warned about. Every other failure, `gh` missing from PATH
    included, is a warning; this never raises.
    """
    if cross_repository:
        print(
            f"  head branch {branch} lives in a fork; not deleting a "
            f"base-repository ref of that name"
        )
        return
    try:
        proc = gh_run(
            ["gh", "api", "-X", "DELETE",
             f"repos/{{owner}}/{{repo}}/git/refs/heads/{branch}"],
            config, check=False,
        )
    except FileNotFoundError:
        reason = "`gh` not on PATH"
    else:
        if proc.returncode == 0:
            print(f"  deleted remote branch {branch}")
            return
        reason = proc.stderr.strip()
        if _ALREADY_DELETED_MARKER in reason:
            print(f"  remote branch {branch} already deleted")
            return
    print(
        f"[warn] could not delete remote branch {branch}: {reason}. The merge "
        f"is durable; delete it by hand (`git push origin --delete {branch}`).",
        file=sys.stderr,
    )


def cleanup_local(
    branch: str, config: dict[str, Any], *, cross_repository: bool,
) -> None:
    """Switch to the default branch, fast-forward it, delete the local head — best-effort.

    The default branch is the adopter's `default_branch` (`main` when the
    config does not declare one). Every step warns with git's reason and
    continues; none can fail the run. When the checkout cannot happen
    (detached HEAD, the default branch checked out in another worktree) the
    pull is skipped — pulling into whatever IS checked out would be wrong —
    but the branch delete is still attempted, since it needs only that the
    branch is not the one checked out here. `-D` (not `-d`) because a
    squash-merged branch is never an ancestor of the base branch.

    For a cross-repository PR the local delete is skipped: a local branch
    sharing the fork branch's name is not that PR's head, and `-D` would
    discard its unpushed work.
    """
    default_branch = str(config.get("default_branch") or "main")

    def _git(*argv: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *argv], capture_output=True, text=True, check=False,
        )

    proc = _git("checkout", default_branch)
    if proc.returncode != 0:
        print(
            f"[warn] git checkout {default_branch} failed: {proc.stderr.strip()}",
            file=sys.stderr,
        )
    else:
        proc = _git("pull", "--ff-only")
        if proc.returncode != 0:
            print(
                f"[warn] git pull failed: {proc.stderr.strip()}",
                file=sys.stderr,
            )
    if cross_repository:
        return
    proc = _git("branch", "-D", branch)
    if proc.returncode != 0:
        print(
            f"[warn] git branch -D {branch} failed: {proc.stderr.strip()}",
            file=sys.stderr,
        )
