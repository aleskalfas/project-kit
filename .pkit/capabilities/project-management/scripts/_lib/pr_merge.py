"""The merge convention's mechanic — ONE implementation, shared by `done-work`
and `merge-pr` (git-conventions.yaml's `merge` entry, DEC-013).

The convention is stated by outcome: one squash commit on the base branch
whose subject is the PR title, no merge commits, and the head branch deleted
on merge. This module realises that outcome in three steps a verb composes:

  1. :func:`land` — the merge. On a base without a queue,
     :func:`squash_merge`: `gh pr merge --squash --subject <PR title>`,
     pinned with `--match-head-commit` to the head the caller's gates
     checked, and deliberately WITHOUT `--delete-branch`. That flag makes gh
     check out the default branch locally and delete the local head, and the
     whole command exits non-zero when the working tree cannot do so (a
     detached HEAD; the default branch checked out in another worktree) —
     AFTER the remote merge has already landed (#878, #587). Keeping the
     merge to the remote half means its exit code reports the merge and
     nothing else. On a base that merges through a queue (#1011,
     `_lib.merge_queue`), the queue makes the merge: :func:`enqueue` hands
     the PR to it and :func:`land` waits for it.
  2. :func:`delete_remote_branch` — the head ref goes through the API, which
     needs nothing from the working tree. Best-effort.
  3. :func:`cleanup_local` — `checkout <default>`, `pull --ff-only`,
     `branch -D <head>`. Every step warns with git's reason and continues;
     none can fail the verb.

A verb runs its own irreversible-merge follow-up (done-work's issue
transition, merge-pr's after-merge hooks) between 1 and 2, so no best-effort
step stands between the merge and the thing that must not be skipped — and
only once :func:`land` reports the PR merged, as GitHub says it, never as a
command's exit code implies.

The backbone's `pkit release merge` (`src/project_kit/release.py`) still
carries its own copy of this mechanic (#897), and does not yet go through a
merge queue; #1200 makes it land through the queue on this one mechanic.
"""

from __future__ import annotations

import argparse
import math
import subprocess
import sys
from dataclasses import dataclass
from typing import Any

from _lib import default_branch, merge_queue
from _lib.gh import gh_run

# How a landing ended (:class:`Landing`): the four ends of a wait for the
# queue; a direct merge gh accepted that no reading since could confirm; and
# three that stop before any merge or enqueue is made.
MERGED = merge_queue.MERGED
STILL_QUEUED = merge_queue.STILL_QUEUED
LEFT = merge_queue.LEFT
HEAD_MOVED = merge_queue.HEAD_MOVED
UNCONFIRMED = "unconfirmed"
REFUSED = "refused"
UNREADABLE = "unreadable"
FAILED = "failed"

_ALREADY_DELETED_MARKER = "Reference does not exist"

# GitHub's own mutation that takes a PR out of a merge queue.
_DEQUEUE = "mutation($id: ID!) { dequeuePullRequest(input: {id: $id}) { clientMutationId } }"


# ---- step 1: the merge ------------------------------------------------------


@dataclass(frozen=True)
class MergeRequest:
    """A verb's merge, once its gates have passed (:func:`land`)."""

    pr_number: int
    pr_title: str
    #: The head the verb's gates checked: the merge, the enqueue and the wait
    #: are pinned to it.
    head_oid: str
    #: The base branch, as the output names it.
    base: str
    admin: bool = False
    #: The verb was asked to bypass its CI gate.
    bypass_ci: bool = False
    #: Enqueue a head the queue already dropped.
    force: bool = False
    #: How long to wait for a queue's merge: None follows the queue's estimate
    #: (`merge_queue.wait_for_merge`), 0 returns at once.
    wait_seconds: float | None = None


@dataclass(frozen=True)
class Landing:
    """How :func:`land` ended.

    `outcome` is :data:`MERGED`; :data:`STILL_QUEUED`, the PR was handed to
    the queue and has not been seen merged; :data:`UNCONFIRMED`, gh accepted a
    direct merge and GitHub could not be read since, so whether it merged is
    not known; :data:`LEFT` or :data:`HEAD_MOVED`, nothing merged; or
    :data:`REFUSED`, :data:`UNREADABLE` or :data:`FAILED`, no merge made and
    nothing enqueued. `reading` is the last reading taken, None when the wait
    lost sight of the PR; `message` says what happened where the outcome alone
    does not.
    """

    outcome: str
    reading: merge_queue.Reading | None = None
    message: str = ""


def land(request: MergeRequest, config: dict[str, Any]) -> Landing:
    """Merge the PR, or hand it to its base's merge queue and wait for the
    queue to merge it — the one landing both merge verbs make.

    The queue is read here, just before the decision, whatever the verb read
    before its gates: a queue switched on, or the PR dropped from one, while
    the gates ran is seen, and :func:`queue_refusal` judges it again. A PR
    already in the queue is waited for, not enqueued twice.

    Merged is what GitHub reports, never what a command's exit implies: on a
    base that requires a queue, `gh pr merge` without `--admin` enqueues and
    exits 0, so after a direct merge the PR is read once more, and anything
    but merged is waited for as a queued PR. When GitHub cannot be read after
    gh accepted a direct merge, the PR may have merged or been enqueued, and
    the landing is :data:`UNCONFIRMED`, never taken for a queued PR.
    """
    number = request.pr_number
    try:
        reading = merge_queue.read(number, config)
        refusal = queue_refusal(
            reading,
            base=request.base,
            admin=request.admin,
            bypass_ci=request.bypass_ci,
            force=request.force,
            config=config,
        )
    except merge_queue.Unreadable as exc:
        return Landing(UNREADABLE, message=f"cannot tell how {request.base} merges: {exc}")
    if refusal:
        return Landing(REFUSED, reading, refusal)
    if reading.merged:
        print(f"  PR #{number} has merged already ({reading.describe()})")
        return _merged(request, reading)
    if reading.has_queue:
        if reading.queued:
            print(f"  PR #{number} is already in the merge queue for {request.base}")
        else:
            if not enqueue(number, config=config, head_oid=request.head_oid):
                return Landing(FAILED, reading)
            print(f"  enqueued PR #{number} in the merge queue for {request.base}")
        return _wait(request, config)
    if not squash_merge(
        number,
        pr_title=request.pr_title,
        admin=request.admin,
        config=config,
        head_oid=request.head_oid,
    ):
        return Landing(FAILED, reading)
    try:
        after = merge_queue.read(number, config)
    except merge_queue.Unreadable as exc:
        print(
            f"[warn] could not confirm that PR #{number} merged: {exc}. Reading it again.",
            file=sys.stderr,
            flush=True,
        )
    else:
        if after.merged:
            print(f"  merged PR #{number}")
            return _merged(request, after)
        print(
            f"  gh pr merge returned, but GitHub does not report PR #{number} merged: "
            f"{request.base} may have begun to merge through a queue, which took the PR "
            "in. Waiting for it as for a queued PR.",
            flush=True,
        )
    return _wait(request, config, merged_directly=True)


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

    Returns True when `gh` accepted the merge, False otherwise (an error line
    is printed). True is not proof of a merge: on a base that requires a merge
    queue gh enqueues and exits 0, which is why :func:`land` reads the PR
    afterwards. No `--delete-branch` — see the module docstring.
    """
    if pr_number is None:
        print("error: no PR number to merge.", file=sys.stderr)
        return False
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
    if admin:
        cmd.append("--admin")
    return _run_merge(cmd, config)


def enqueue(
    pr_number: int | None,
    *,
    config: dict[str, Any],
    head_oid: str = "",
) -> bool:
    """Put the PR in its base branch's merge queue (#1011): `gh pr merge <N>
    --auto`, pinned to the head the caller's gates checked.

    The queue makes the merge (`_lib.merge_queue`): it runs the base's required
    checks on the merge it is about to make and merges once they pass, by its
    own merge method and with a squash commit composed from the repository's
    defaults. GitHub ignores a merge method, a subject and a body passed with a
    queued merge, so none is passed; :func:`queue_refusal` checks the method
    and the defaults instead. With `--auto`, a PR whose own required checks are
    still running is taken in once they pass. Never `--admin`, which merges
    around the queue.

    Returns True once GitHub has taken the PR in, False otherwise (an error
    line is printed). The PR has not merged when this returns.
    """
    if pr_number is None:
        print("error: no PR number to enqueue.", file=sys.stderr)
        return False
    cmd = ["gh", "pr", "merge", str(pr_number), "--auto"]
    if head_oid:
        cmd += ["--match-head-commit", head_oid]
    return _run_merge(cmd, config)


def dequeue(pr_number: int, reading: merge_queue.Reading, config: dict[str, Any]) -> bool:
    """Take the PR out of its base's merge queue — or, while auto-merge still
    holds it until its checks pass, cancel that — and confirm it is out.

    `gh pr merge --disable-auto` cancels the auto-merge. On a PR already in
    the queue gh answers "already queued to merge" and exits 0 without
    changing anything, so such a PR is taken out through GitHub's own
    `dequeuePullRequest`. Returns True once a reading shows the PR neither
    queued nor merged; False, with the reason printed, otherwise.
    """
    if reading.in_queue and reading.pr_id:
        cmd = ["gh", "api", "graphql", "-f", f"query={_DEQUEUE}", "-f", f"id={reading.pr_id}"]
    else:
        cmd = ["gh", "pr", "merge", str(pr_number), "--disable-auto"]
    try:
        proc = gh_run(cmd, config, check=False)
    except FileNotFoundError:
        print("error: `gh` not on PATH.", file=sys.stderr)
        return False
    if proc.returncode != 0:
        print(
            f"error: could not take PR #{pr_number} out of the merge queue: {proc.stderr.strip()}",
            file=sys.stderr,
        )
        return False
    try:
        after = merge_queue.read(pr_number, config)
    except merge_queue.Unreadable as exc:
        print(
            f"error: could not confirm PR #{pr_number} left the merge queue: {exc}",
            file=sys.stderr,
        )
        return False
    return not after.queued and not after.merged


def queue_refusal(
    reading: merge_queue.Reading,
    *,
    base: str,
    admin: bool,
    bypass_ci: bool,
    force: bool,
    config: dict[str, Any],
) -> str:
    """Why a merge verb may not land the PR through `base`'s queue, or "".

    A base with a queue takes merges only through it, so `--admin`, which
    merges around it, is refused. So is `--bypass-ci`: the queue runs the
    required checks itself and merges only once they pass, so a PR held by a
    red one would wait in the queue for ever while the bypass's audit comment
    said it was bypassed. The squash commit must be the convention's
    (DEC-013): the queue must squash, and since it composes the commit from the
    repository's squash-commit defaults, those must be the PR title and body.
    A head the queue dropped is not enqueued again unchanged unless `force`.

    Raises `merge_queue.Unreadable` when the repository's squash-commit
    defaults cannot be read: nothing is enqueued on an unknown commit shape.
    """
    if not reading.has_queue:
        return ""
    if admin:
        return (
            f"[refused] {base} merges through a queue, the only path to it; --admin "
            "would merge around the queue.\n"
            "          → drop --admin: the PR is enqueued and the queue merges it."
        )
    if bypass_ci:
        return (
            f"[refused] {base} merges through a queue, and --bypass-ci cannot bypass a "
            "check there: the queue runs the required checks itself and merges only "
            "once they pass, so the PR would wait in it for ever while the audit "
            "comment said the check was bypassed.\n"
            "          → drop --bypass-ci and make the checks pass, then re-run."
        )
    if not reading.squashes:
        method = reading.merge_method or "an unreported method"
        return (
            f"[refused] the merge queue on {base} merges by {method}, and the merge "
            "convention is one squash commit per PR (DEC-013).\n"
            "          → set the queue's merge method to squash in the repository's "
            "branch rules, then re-run."
        )
    removal = reading.removal
    if reading.dropped_head and removal is not None and not force:
        why = f"GitHub says: {removal.reason}" if removal.reason else "GitHub gives no reason"
        return (
            f"[refused] the merge queue on {base} dropped the PR at its current head "
            f"{reading.head_oid[:7]} at {removal.at} ({why}); the same head is not "
            "enqueued again unchanged.\n"
            "          → fix what made the queue drop it and push, then re-run; or "
            "pass --force to enqueue this head again."
        )
    title, message = merge_queue.squash_commit_defaults(config)
    if (title, message) != (merge_queue.PR_TITLE, merge_queue.PR_BODY):
        return (
            f"[refused] the merge queue on {base} composes the squash commit from the "
            f"repository's defaults, title {title} and message {message}, and the "
            "convention's squash commit is the PR title over the PR body (DEC-013).\n"
            "          → set them: `gh api -X PATCH repos/{owner}/{repo} -f "
            "squash_merge_commit_title=PR_TITLE -f squash_merge_commit_message=PR_BODY`, "
            "then re-run."
        )
    return ""


def _wait(
    request: MergeRequest, config: dict[str, Any], *, merged_directly: bool = False
) -> Landing:
    """Wait for the queue to merge the PR, as long as the request says.

    `merged_directly`: gh accepted a direct merge of the PR, so when a reading
    cannot be taken the PR may have merged rather than be queued, and the
    landing is :data:`UNCONFIRMED`.
    """
    number = request.pr_number
    if request.wait_seconds != 0:
        print(
            f"  waiting for the queue to merge it, {_wait_limit(request.wait_seconds)} "
            "(--no-wait returns at once)",
            flush=True,
        )

    def report(reading: merge_queue.Reading) -> None:
        print(f"  queue:   PR #{number} {reading.describe()}", flush=True)

    try:
        wait = merge_queue.wait_for_merge(
            number,
            config,
            timeout_seconds=request.wait_seconds,
            on_change=report,
            head_oid=request.head_oid,
        )
    except merge_queue.Unreadable as exc:
        if merged_directly:
            return Landing(
                UNCONFIRMED,
                message=(
                    f"gh accepted the merge of PR #{number} into {request.base}, but GitHub "
                    f"could not be read to confirm that it merged: {exc}"
                ),
            )
        return Landing(STILL_QUEUED, message=f"lost sight of the merge queue: {exc}")
    if wait.ended == MERGED:
        print(f"  merged PR #{number} through the queue")
        return _merged(request, wait.reading)
    if wait.ended == HEAD_MOVED:
        moved = (
            f"PR #{number}'s head moved from {request.head_oid[:7]} to "
            f"{wait.reading.head_oid[:7]} after its gates checked it"
        )
        if dequeue(number, wait.reading, config):
            message = (
                f"{moved}; it was taken out of the merge queue, so nothing they did not "
                "check merges."
            )
        else:
            message = (
                f"{moved}, and taking it out of the merge queue failed: it may still "
                "merge commits nothing checked. Take it out yourself — in the PR's merge "
                f"box, or `gh pr merge {number} --disable-auto` while it waits to enter."
            )
        return Landing(HEAD_MOVED, wait.reading, message)
    return Landing(wait.ended, wait.reading)


def _merged(request: MergeRequest, reading: merge_queue.Reading) -> Landing:
    """The PR merged; say so if it merged at a head its gates did not check."""
    if request.head_oid and reading.head_oid and reading.head_oid != request.head_oid:
        print(
            f"[warn] PR #{request.pr_number} merged at head {reading.head_oid[:7]}, not "
            f"at {request.head_oid[:7]}, the head its gates checked.",
            file=sys.stderr,
        )
    return Landing(MERGED, reading)


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


# ---- the merge verbs' queue flags -------------------------------------------


def add_queue_arguments(parser: argparse.ArgumentParser) -> None:
    """The flags both merge verbs take for a base that merges through a queue."""
    wait = parser.add_mutually_exclusive_group()
    wait.add_argument(
        "--no-wait",
        action="store_true",
        help=(
            "Where the base merges through a queue: return once the PR is queued "
            "(exit 4). Run the same command again once it has merged to complete "
            "what follows the merge."
        ),
    )
    wait.add_argument(
        "--wait-minutes",
        type=_minutes,
        default=None,
        metavar="MINUTES",
        help=(
            "Where the base merges through a queue: how long to wait for the queue "
            "to merge the PR. Default: as long as the queue estimates, plus "
            f"{merge_queue.ETA_MARGIN_SECONDS / 60:g} min, at most "
            f"{merge_queue.MAX_WAIT_SECONDS / 60:g} min."
        ),
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help=(
            "Where the base merges through a queue: enqueue a head the queue already "
            "dropped. Without it, such a head is refused until new commits are pushed."
        ),
    )


def wait_seconds(args: argparse.Namespace) -> float | None:
    """The wait the queue flags ask for: 0 with `--no-wait`, the minutes given,
    else None — the queue's estimate."""
    if args.no_wait:
        return 0
    if args.wait_minutes is not None:
        return args.wait_minutes * 60
    return None


def wait_phrase(seconds: float | None) -> str:
    """What a run does once the PR is queued, as a phrase for a verb's output."""
    if seconds == 0:
        return "return once it is queued (--no-wait)"
    return f"wait for the queue to merge it, {_wait_limit(seconds)}"


def _wait_limit(seconds: float | None) -> str:
    if seconds is None:
        return (
            f"as long as the queue estimates plus {merge_queue.ETA_MARGIN_SECONDS / 60:g} min, "
            f"at most {merge_queue.MAX_WAIT_SECONDS / 60:g} min"
        )
    return f"up to {seconds / 60:g} min"


def _minutes(value: str) -> float:
    """`--wait-minutes`: a number of minutes, 0 or more."""
    try:
        minutes = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"not a number of minutes: {value!r}") from None
    if not math.isfinite(minutes) or minutes < 0:
        raise argparse.ArgumentTypeError(f"not a wait of 0 minutes or more: {value!r}")
    return minutes


# ---- steps 2 and 3: the clean-up -------------------------------------------


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
    merged_head: str = "",
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

    With `merged_head`, the head the PR merged at, the local branch is deleted
    only when everything on it merged: its tip is that head or behind it. A
    branch holding commits the merge does not — work since, or a clone that
    cannot tell — is kept with a warning, and a clone without the branch has
    nothing to delete.

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
    if merged_head:
        tip = _git("rev-parse", "--verify", "--quiet", f"refs/heads/{branch}").stdout.strip()
        if not tip:
            return
        # The commits on the branch the merged head does not hold: none, and
        # everything on it merged. A head this clone does not have fails the
        # count, which keeps the branch too.
        unmerged = _git("rev-list", "--count", f"{merged_head}..{tip}")
        if unmerged.returncode != 0 or unmerged.stdout.strip() != "0":
            print(
                f"[warn] local branch {branch} (at {tip[:7]}) holds commits the merge at "
                f"{merged_head[:7]} does not, or this clone cannot tell; it is kept. "
                f"Delete it yourself once nothing on it is needed (`git branch -D {branch}`).",
                file=sys.stderr,
            )
            return
    proc = _git("branch", "-D", branch)
    if proc.returncode != 0:
        print(
            f"[warn] git branch -D {branch} failed: {proc.stderr.strip()}",
            file=sys.stderr,
        )
