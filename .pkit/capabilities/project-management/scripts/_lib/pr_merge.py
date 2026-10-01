"""The merge convention's mechanic — ONE implementation, shared by `done-work`
and `merge-pr` (git-conventions.yaml's `merge` entry, DEC-013).

The convention is stated by outcome: one squash commit on the base branch
whose subject is the PR title, no merge commits, and the head branch deleted
on merge. This module realises that outcome in three steps a verb composes:

  1. :func:`squash_merge` — `gh pr merge --squash --subject <PR title>`,
     pinned with `--match-head-commit` to the head a caller's gate checked
     when the caller names one, and deliberately WITHOUT `--delete-branch`.
     That flag makes gh check out the default branch locally and delete the
     local head, and the whole command exits non-zero when the working tree
     cannot do so (a detached HEAD; the default branch checked out in another
     worktree) — AFTER the remote merge has already landed (#878, #587).
     Keeping the merge to the remote half means its exit code reports the
     merge and nothing else.
  2. :func:`delete_remote_branch` — the head ref goes through the API, which
     needs nothing from the working tree. Best-effort.
  3. :func:`cleanup_local` — `checkout <default>`, `pull --ff-only`,
     `branch -D <head>`. Every step warns with git's reason and continues;
     none can fail the verb.

A verb runs its own irreversible-merge follow-up (done-work's issue
transition, merge-pr's after-merge hooks) between 1 and 2, so no best-effort
step stands between the merge and the thing that must not be skipped.

Where the base branch merges through a queue (`_lib.merge_queue`), the queue
makes the merge instead of step 1: :func:`enqueue` hands the PR to it with the
same command and `--auto`, and the verb's follow-up and steps 2 and 3 wait
until the queue has merged it.

The backbone's `pkit release merge` (`src/project_kit/release.py`,
`_gh_pr_merge` / `_gh_delete_remote_branch` / `_git_cleanup_local`) carries a
deliberate duplicate of this mechanic (#897): the backbone must not depend on
a capability, and these scripts run as standalone `uv run --script`s that do
not import `project_kit`. Keep the two in step — a fix to either (the fork-PR
guard, the already-deleted answer) belongs in both.
"""

from __future__ import annotations

import subprocess
import sys
from typing import Any

from _lib import default_branch
from _lib.gh import gh_run

_ALREADY_DELETED_MARKER = "Reference does not exist"


def squash_merge(
    pr_number: int | None,
    *,
    pr_title: str,
    admin: bool,
    config: dict[str, Any],
    head_oid: str = "",
) -> bool:
    """Squash-merge the PR with the PR title as the landed commit subject.

    `head_oid`, when given, is the head commit the caller's gate checked: the
    merge is pinned to it (`--match-head-commit`), so a push between the gate
    and the merge fails the merge instead of landing commits nothing checked.

    Returns True when the remote merge landed, False otherwise (an error line
    is printed). No `--delete-branch` — see the module docstring.
    """
    if pr_number is None:
        print("error: no PR number to merge.", file=sys.stderr)
        return False
    cmd = _merge_command(pr_number, pr_title, head_oid)
    if admin:
        cmd.append("--admin")
    return _run_merge(cmd, config)


def enqueue(
    pr_number: int | None,
    *,
    pr_title: str,
    config: dict[str, Any],
    head_oid: str = "",
) -> bool:
    """Put the PR in its base branch's merge queue (#1011): the merge command,
    pinned and subject-forced as :func:`squash_merge` makes it, with `--auto`.

    The queue makes the merge (`_lib.merge_queue`): it runs the base's required
    checks on the merge it is about to make and squashes once they pass. With
    `--auto`, a PR whose own required checks are still running is taken in
    once they pass. Never `--admin`, which merges around the queue.

    Returns True once GitHub has taken the PR in, False otherwise (an error
    line is printed). The PR has not merged when this returns.
    """
    if pr_number is None:
        print("error: no PR number to enqueue.", file=sys.stderr)
        return False
    return _run_merge([*_merge_command(pr_number, pr_title, head_oid), "--auto"], config)


def _merge_command(pr_number: int, pr_title: str, head_oid: str) -> list[str]:
    """`gh pr merge <N> --squash --subject <title> [--match-head-commit <head>]`."""
    # Force --subject to the PR title so the squash-commit subject equals the
    # gate-validated title for both single- and multi-commit PRs.  GitHub's
    # default for a single-commit PR is the commit message, not the title —
    # the --subject flag overrides that (DEC-013; fixes #33).
    cmd = [
        "gh",
        "pr",
        "merge",
        str(pr_number),
        "--squash",
        "--subject",
        pr_title,
    ]
    if head_oid:
        cmd += ["--match-head-commit", head_oid]
    return cmd


def _run_merge(cmd: list[str], config: dict[str, Any]) -> bool:
    """Run a `gh pr merge` command; False, with gh's reason printed, when it fails."""
    try:
        proc = gh_run(cmd, config, check=False)
    except FileNotFoundError:
        print("error: `gh` not on PATH.", file=sys.stderr)
        return False
    if proc.returncode != 0:
        print(
            f"error: gh pr merge failed (exit {proc.returncode}): {proc.stderr.strip()}",
            file=sys.stderr,
        )
        return False
    return True


def delete_remote_branch(
    branch: str,
    config: dict[str, Any],
    *,
    cross_repository: bool,
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
            ["gh", "api", "-X", "DELETE", f"repos/{{owner}}/{{repo}}/git/refs/heads/{branch}"],
            config,
            check=False,
        )
    except FileNotFoundError:
        reason = "`gh` not on PATH"
    except OSError as exc:  # on PATH but not runnable: permissions, bad binary
        reason = f"`gh` could not be run ({exc})"
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
    branch: str,
    config: dict[str, Any],
    *,
    cross_repository: bool,
) -> None:
    """Switch to the default branch, fast-forward it, delete the local head — best-effort.

    The default branch is the project's, as the backbone declares it (COR-054;
    `_lib/default_branch`); when the backbone cannot say which it is, the
    clean-up is skipped with the cause rather than switch to a guessed branch.
    Every step warns with git's reason and
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
    try:
        settled = default_branch.name(config)
    except default_branch.Unanswered as exc:
        print(
            f"[warn] the local clean-up is skipped: {exc}. Switch to the default branch, "
            f"pull it and delete {branch} yourself.",
            file=sys.stderr,
        )
        return

    def _git(*argv: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *argv],
            capture_output=True,
            text=True,
            check=False,
        )

    proc = _git("checkout", settled)
    if proc.returncode != 0:
        print(
            f"[warn] git checkout {settled} failed: {proc.stderr.strip()}",
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
