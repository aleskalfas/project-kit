"""The merge convention's mechanic as the merge verbs compose it — ONE
implementation, shared by `done-work` and `merge-pr` (git-conventions.yaml's
`merge` entry, DEC-013).

The convention is stated by outcome: one squash commit on the base branch
whose subject is the PR title, no merge commits, and the head branch deleted
on merge. This module realises that outcome in three steps a verb composes:

  1. :func:`land` — the merge. On a base without a queue,
     :func:`squash_merge`: a squash merge whose subject is the PR title,
     pinned to the head the caller's gates checked, and deliberately
     WITHOUT `--delete-branch`. That flag makes gh
     check out the default branch locally and delete the local head, and the
     whole command exits non-zero when the working tree cannot do so (a
     detached HEAD; the default branch checked out in another worktree) —
     AFTER the remote merge has already landed (#878, #587). Keeping the
     merge to the remote half means its exit code reports the merge and
     nothing else. On a base that merges through a queue (#1011,
     `_lib.merge_queue`), the queue makes the merge: :func:`enqueue` hands
     the PR to it and :func:`land` waits for it.
  2. :func:`delete_branch` — the head branch on GitHub, deleted by the
     backbone (`pkit pull-request delete-branch`) only while its tip is the
     head that merged. Whatever it comes to is said in one line — naming the
     command that deletes it later where it was not deleted — and never
     fails the verb; it is answered for step 3.
  3. :func:`cleanup_local` — `checkout <default>`, `pull --ff-only`,
     `branch -D <head>`, the last only when the branch on GitHub was deleted
     or is gone and everything on the local one merged. Every step warns with
     git's reason and continues; none can fail the verb.

A verb runs its own irreversible-merge follow-up (done-work's issue
transition, merge-pr's after-merge hooks) between 1 and 2, so no best-effort
step stands between the merge and the thing that must not be skipped — and
only once :func:`land` reports the PR merged, as GitHub says it, never as a
command's exit code implies.

The requests themselves — the squash merge, the enqueue, the wait for the
queue, taking a PR out of it and deleting the head branch — are the
backbone's (`pkit pull-request`, read through `_lib.merge_queue`): the one
mechanic the backbone's `pkit release merge` lands a release PR with too
(#1200). What this module decides is the verbs' own: when to land, what to
refuse, and what follows the merge.

The backbone runs the cross-repository guard before each request that changes
the service (ADR-061 point 6), with no terminal to ask: the verb's own guard
ran first. A request carries `--allow-foreign-repo` exactly when the operator
confirmed at the verb — gave the flag on its command line, or answered yes at
its prompt (:attr:`MergeRequest.allow_foreign_repo`) — so the operator is
asked once and nothing is confirmed that they did not confirm. Should the
backbone still refuse — its comparison and the verb's disagree, and the
operator confirmed nothing — the landing is :data:`REFUSED`, naming both
verdicts, and nothing was requested.
"""

from __future__ import annotations

import argparse
import math
import os
import subprocess
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from _lib import default_branch, merge_queue

# How a landing ended (:class:`Landing`): the four ends of a wait for the
# queue; a merge or an enqueue that no reading since could confirm; and three
# that stop before any merge or enqueue is made.
MERGED = merge_queue.MERGED
STILL_QUEUED = merge_queue.STILL_QUEUED
LEFT = merge_queue.LEFT
HEAD_MOVED = merge_queue.HEAD_MOVED
UNCONFIRMED = "unconfirmed"
REFUSED = "refused"
UNREADABLE = "unreadable"
FAILED = "failed"

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
    #: How the verb's own cross-repository guard let it proceed
    #: (`session_guard.how_passed`); "" when it does not say.
    guard_passed: str = ""
    #: The operator confirmed a change in another repository at the verb — the
    #: flag on its command line, or a yes at its prompt
    #: (`session_guard.confirmed`): the backbone is told so, and only then.
    allow_foreign_repo: bool = False


class GuardRefused(Exception):
    """The backbone's cross-repository guard refused a request, which it did
    not make; `outcome` is its answer."""

    def __init__(self, outcome: merge_queue.Outcome) -> None:
        super().__init__(outcome.reason)
        self.outcome = outcome


@dataclass(frozen=True)
class Landing:
    """How :func:`land` ended.

    `outcome` is :data:`MERGED`; :data:`STILL_QUEUED`, the PR was handed to
    the queue and has not been seen merged; :data:`UNCONFIRMED`, gh accepted a
    direct merge, or a merge or an enqueue got no answer back, and GitHub
    could not be read since, so whether it merged is not known;
    :data:`LEFT` or :data:`HEAD_MOVED`, nothing merged; or :data:`REFUSED`,
    :data:`UNREADABLE` or :data:`FAILED`, no merge made and nothing enqueued.
    `reading` is the last reading taken, None when the wait lost sight of the
    PR; `message` says what happened where the outcome alone does not.
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
    the landing is :data:`UNCONFIRMED`, never taken for a queued PR. A merge
    or an enqueue that gets no answer back may have been made all the same,
    so it is never taken for one that failed: the PR is read before anything
    is decided (:func:`_unanswered`).
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
            try:
                enqueued = enqueue(
                    number,
                    config=config,
                    head_oid=request.head_oid,
                    allow_foreign_repo=request.allow_foreign_repo,
                )
            except GuardRefused as refused:
                return Landing(REFUSED, reading, _guard_refusal(request, refused, "enqueue"))
            if enqueued is None:
                return _unanswered(request, config, merged_directly=False)
            if not enqueued:
                return Landing(FAILED, reading)
            print(f"  enqueued PR #{number} in the merge queue for {request.base}")
        return _wait(request, config)
    try:
        merged = squash_merge(
            number,
            pr_title=request.pr_title,
            admin=request.admin,
            config=config,
            head_oid=request.head_oid,
            allow_foreign_repo=request.allow_foreign_repo,
        )
    except GuardRefused as refused:
        return Landing(REFUSED, reading, _guard_refusal(request, refused, "merge"))
    if merged is None:
        return _unanswered(request, config, merged_directly=True)
    if not merged:
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


def _unanswered(request: MergeRequest, config: dict[str, Any], *, merged_directly: bool) -> Landing:
    """A merge — `merged_directly` — or an enqueue the backbone gave no answer to.

    The request may have been made — the run may have ended after gh
    accepted it — so the PR is read before anything is decided: merged, it is
    the merge; in the queue, it is waited for; neither, the request was not
    made and nothing merged. When the PR cannot be read the landing is
    :data:`UNCONFIRMED`: whether it merged, or entered the queue, is not
    known, and what follows the merge is owed to a re-run.
    """
    number = request.pr_number
    asked = "merge" if merged_directly else "enqueue"
    try:
        after = merge_queue.read(number, config)
    except merge_queue.Unreadable as exc:
        return Landing(
            UNCONFIRMED,
            message=(
                f"the {asked} of PR #{number} into {request.base} got no answer back, and "
                f"GitHub could not be read since to tell whether it merged or entered the "
                f"merge queue: {exc}"
            ),
        )
    if after.merged:
        print(f"  merged PR #{number}, as GitHub reports it ({after.describe()})")
        return _merged(request, after)
    if after.queued:
        print(f"  PR #{number} is in the merge queue for {request.base} ({after.describe()})")
        return _wait(request, config, merged_directly=merged_directly)
    print(
        f"error: GitHub reports PR #{number} neither merged nor queued ({after.describe()}): "
        f"the {asked} was not made, and nothing merged.",
        file=sys.stderr,
    )
    return Landing(FAILED, after)


def squash_merge(
    pr_number: int | None,
    *,
    pr_title: str,
    admin: bool,
    config: dict[str, Any],
    head_oid: str = "",
    allow_foreign_repo: bool = False,
) -> bool | None:
    """Squash-merge the PR with the PR title as the landed commit subject —
    the backbone's direct merge (`pkit pull-request merge`).

    `allow_foreign_repo` passes the operator's confirmation of a change in
    another repository on to the backbone's guard; raises
    :class:`GuardRefused` when that guard refused the merge, unmade.

    `head_oid`, when given, is the head commit the caller's gate checked: the
    merge is pinned to it, so a push between the gate and the merge fails the
    merge instead of landing commits nothing checked. The subject is always
    the PR title: GitHub's default for a single-commit PR is the commit
    message, which would defeat the title gate (DEC-013; fixes #33).

    Returns True when gh accepted the merge, False when it did not (an error
    line is printed), and None when the backbone gave no answer back (a
    warning is printed): the merge may have been made, and :func:`land` reads
    the PR before it decides. True is not proof of a merge either: on a base
    that requires a merge queue gh enqueues and exits 0, which is why
    :func:`land` reads the PR afterwards. The head branch is never deleted
    here — see the module docstring.
    """
    if pr_number is None:
        print("error: no PR number to merge.", file=sys.stderr)
        return False
    args = ["merge", str(pr_number), "--subject", pr_title]
    if head_oid:
        args += ["--head", head_oid]
    if admin:
        args.append("--admin")
    return _request(_confirming(args, allow_foreign_repo), config)


def enqueue(
    pr_number: int | None,
    *,
    config: dict[str, Any],
    head_oid: str = "",
    allow_foreign_repo: bool = False,
) -> bool | None:
    """Put the PR in its base branch's merge queue (#1011), pinned to the head
    the caller's gates checked — the backbone's enqueue (`pkit pull-request
    enqueue`, `gh pr merge <N> --auto`). `allow_foreign_repo` and
    :class:`GuardRefused` as for :func:`squash_merge`.

    The queue makes the merge (`_lib.merge_queue`): it runs the base's required
    checks on the merge it is about to make and merges once they pass, by its
    own merge method and with a squash commit composed from the repository's
    defaults. GitHub ignores a merge method, a subject and a body passed with a
    queued merge, so :func:`queue_refusal` checks the method and the defaults
    instead. A PR whose own required checks are still running is taken in once
    they pass. Never `--admin`, which merges around the queue.

    Returns True once GitHub has taken the PR in, False when it did not (an
    error line is printed), and None when the backbone gave no answer back (a
    warning is printed): the PR may have entered the queue all the same. The
    PR has not merged when this returns.
    """
    if pr_number is None:
        print("error: no PR number to enqueue.", file=sys.stderr)
        return False
    args = ["enqueue", str(pr_number)]
    if head_oid:
        args += ["--head", head_oid]
    return _request(_confirming(args, allow_foreign_repo), config)


def dequeue(pr_number: int, config: dict[str, Any], *, allow_foreign_repo: bool = False) -> bool:
    """Take the PR out of its base's merge queue — or, while auto-merge still
    holds it until its checks pass, cancel that — and confirm it is out: the
    backbone's dequeue (`pkit pull-request dequeue`), which reads the PR first.
    `allow_foreign_repo` as for :func:`squash_merge`.

    Returns True once a reading shows the PR neither queued nor merged; False,
    with the reason printed, otherwise — the backbone's guard refusing it
    among them, when the command that takes the PR out is printed with the
    flag that confirms it, since running the verb again does not repeat the
    dequeue.
    """
    args = _confirming(["dequeue", str(pr_number)], allow_foreign_repo)
    try:
        outcome = merge_queue.request(args, config)
    except merge_queue.Unreadable as exc:
        print(
            f"error: could not take PR #{pr_number} out of the merge queue: {exc}", file=sys.stderr
        )
        return False
    if outcome.reason_kind == merge_queue.FOREIGN_REPOSITORY:
        print(
            f"error: the backbone's cross-repository guard refused to take PR #{pr_number} out "
            f"of the merge queue, and nothing was asked of GitHub: "
            f"{_backbones_comparison(outcome)}. To take it out there, run "
            f"`pkit pull-request dequeue {pr_number} --allow-foreign-repo` from "
            f"{os.getcwd()}, or use the PR's merge box.",
            file=sys.stderr,
        )
        return False
    if not outcome.accepted:
        print(
            f"error: could not take PR #{pr_number} out of the merge queue: {outcome.reason}",
            file=sys.stderr,
        )
    return outcome.accepted


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
        if dequeue(number, config, allow_foreign_repo=request.allow_foreign_repo):
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


def _request(args: list[str], config: dict[str, Any]) -> bool | None:
    """Ask the backbone to make a merge request: True when it was accepted;
    False, with gh's reason printed, when it was not; None, with why printed,
    when no answer came back — the request may have been made all the same.
    Raises :class:`GuardRefused` when the backbone's guard refused it."""
    try:
        outcome = merge_queue.request(args, config)
    except merge_queue.Unreadable as exc:
        print(
            f"[warn] the {args[0]} of PR #{args[1]} got no answer back from the backbone: "
            f"{exc}. Reading the PR to see what it came to.",
            file=sys.stderr,
            flush=True,
        )
        return None
    if outcome.accepted:
        return True
    if outcome.reason_kind == merge_queue.FOREIGN_REPOSITORY:
        raise GuardRefused(outcome)
    if outcome.exit_code is None:
        print(f"error: {outcome.reason}.", file=sys.stderr)
    else:
        print(
            f"error: gh pr merge failed (exit {outcome.exit_code}): {outcome.reason}",
            file=sys.stderr,
        )
    return False


def _confirming(args: list[str], allow_foreign_repo: bool) -> list[str]:
    """`args`, with the operator's confirmation of a change in another
    repository passed on to the backbone's guard when there is one."""
    return [*args, "--allow-foreign-repo"] if allow_foreign_repo else args


def _backbones_comparison(outcome: merge_queue.Outcome) -> str:
    """What the backbone's guard compared, as its document states it: its
    verdict, and the session's anchor and the target where it names them."""
    guard: Mapping[str, Any] = outcome.guard or {}
    verdict = str(guard.get("verdict") or "another repository")
    anchor, target = guard.get("anchor"), guard.get("target")
    where = f" (the session's anchor {anchor}, the target {target})" if anchor and target else ""
    return f"its comparison reads {verdict}{where}"


def _guard_refusal(request: MergeRequest, refused: GuardRefused, asked: str) -> str:
    """Why the landing stopped when the backbone's cross-repository guard
    refused a request this verb's own guard had let through with no
    confirmation from the operator: the two comparisons disagree. Names both
    verdicts; nothing was requested."""
    ours = request.guard_passed or "a pass it did not report"
    return (
        f"[refused] the backbone's cross-repository guard refused the {asked} of PR "
        f"#{request.pr_number}: {_backbones_comparison(refused.outcome)}, where this verb's "
        f"own guard passed it as {ours}. The two comparisons disagree, and with no "
        "confirmation a disagreement refuses: nothing was asked of GitHub.\n"
        "          → if the change is meant for that repository, run the verb again with "
        "--allow-foreign-repo, which it passes on; otherwise run it from a session rooted "
        "in the target repository. Either way, report the disagreement — the two "
        "comparisons are held to answer alike."
    )


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
        type=minutes,
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


def minutes(value: str) -> float:
    """`--wait-minutes`: a number of minutes, 0 or more (an argparse `type`)."""
    try:
        minutes = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"not a number of minutes: {value!r}") from None
    if not math.isfinite(minutes) or minutes < 0:
        raise argparse.ArgumentTypeError(f"not a wait of 0 minutes or more: {value!r}")
    return minutes


# ---- steps 2 and 3: the head branch, on GitHub and here ----------------------


#: What became of the head branch on GitHub when no deletion was asked for:
#: the head the PR merged at is not known (:func:`delete_branch`).
NOT_ASKED = "not-asked"

#: The ends of the deletion on GitHub after which the local branch may go
#: too: the branch there was deleted, or is not there.
_REMOTE_GONE = (merge_queue.DELETED, merge_queue.GONE)


def delete_branch(
    pr_number: int,
    merged_head: str,
    config: dict[str, Any],
    *,
    allow_foreign_repo: bool,
    rerun_note: str = "",
) -> str:
    """Delete the merged PR's head branch on GitHub — the backbone's deletion
    (`pkit pull-request delete-branch`), only while the branch's tip is
    `merged_head`, the head the PR merged at, so a push since the merge is not
    lost — and answer what became of it, for :func:`cleanup_local`.

    The backbone reads the PR and decides: a PR whose head is in a fork, that
    has not merged, or whose head is not `merged_head` is refused; a branch
    whose tip moved, that another open PR uses as its head or its base, or
    that GitHub will not delete is kept; one not there is gone; and one asked
    for with no usable answer and no reading since is unconfirmed. What it came
    to is said in one line — a refusal other than a fork's, and an unconfirmed
    one, as a warning — and nothing here fails the verb: the merge is durable.
    Where the branch was not deleted, the line names the command that deletes
    it later, then `rerun_note` — what the verb's own re-run does about it,
    when the verb has something to say.

    Answers the backbone's `outcome` (`merge_queue.DELETED`, `GONE`, `KEPT`,
    `REFUSED`, `UNCONFIRMED`); `UNCONFIRMED` too when the backbone gave no
    answer, and :data:`NOT_ASKED` when no merged head is known.
    `allow_foreign_repo` passes the operator's confirmation of a change in
    another repository on to the backbone's guard, as for :func:`squash_merge`.
    """
    if not merged_head:
        print(
            f"[warn] the head PR #{pr_number} merged at is not known, so its head branch on "
            "GitHub is kept. " + _delete_later(pr_number, "", allow_foreign_repo, rerun_note),
            file=sys.stderr,
        )
        return NOT_ASKED
    args = _confirming([str(pr_number), "--expect", merged_head], allow_foreign_repo)
    try:
        deletion = merge_queue.deletion(args, config)
    except merge_queue.Unreadable as exc:
        print(
            f"[warn] whether PR #{pr_number}'s head branch on GitHub was deleted is not known: "
            f"{exc}. The merge is durable. "
            + _delete_later(pr_number, merged_head, allow_foreign_repo, rerun_note),
            file=sys.stderr,
        )
        return merge_queue.UNCONFIRMED
    branch = f"remote branch {deletion.branch}" if deletion.branch else "the remote head branch"
    # The service's words may end a sentence of their own.
    reason = deletion.reason.rstrip(".")
    later = _delete_later(
        pr_number, deletion.merged_head or merged_head, allow_foreign_repo, rerun_note
    )
    if deletion.outcome == merge_queue.DELETED:
        print(f"  deleted {branch}")
    elif deletion.outcome == merge_queue.GONE:
        print(f"  {branch} is not there; nothing to delete")
    elif deletion.outcome == merge_queue.KEPT:
        print(f"  kept {branch}: {reason}. {later}")
    elif deletion.outcome == merge_queue.UNCONFIRMED:
        print(
            f"[warn] whether {branch} was deleted is not known: {reason}. {later}",
            file=sys.stderr,
        )
    elif deletion.reason_kind == merge_queue.CROSS_REPOSITORY:
        print(f"  {branch} not deleted: {reason}")
    else:
        print(f"[warn] {branch} not deleted: {reason}. {later}", file=sys.stderr)
    return deletion.outcome


def _delete_later(pr_number: int, head: str, allow_foreign_repo: bool, rerun_note: str) -> str:
    """The sentence that names the command deleting the branch later, at
    `head` — or, with none known, how to find it — then `rerun_note`."""
    flag = " --allow-foreign-repo" if allow_foreign_repo else ""
    if head:
        sentence = (
            f"To delete it later: `pkit pull-request delete-branch {pr_number} --expect "
            f"{head}{flag}`."
        )
    else:
        sentence = (
            f"To delete it later, read the head it merged at (`pkit pull-request read "
            f"{pr_number}`, `head_oid`), then run `pkit pull-request delete-branch {pr_number} "
            f"--expect <that head>{flag}`."
        )
    return f"{sentence} {rerun_note}" if rerun_note else sentence


def cleanup_local(
    branch: str,
    config: dict[str, Any],
    *,
    cross_repository: bool,
    merged_head: str,
    remote: str,
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

    The local branch goes only with the one on GitHub: it is deleted only when
    `remote`, what became of that one (:func:`delete_branch`), is deleted or
    gone. One kept, refused, unconfirmed or not asked for keeps the local
    branch too, said in one line. And it is deleted only when everything on
    it merged: its tip is `merged_head`, the head the PR merged at, or behind
    it. A branch holding commits the merge does not — work since, a clone that
    cannot tell, or no merged head known — is kept with a warning, and a clone
    without the branch has nothing to delete.

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
    tip = _git("rev-parse", "--verify", "--quiet", f"refs/heads/{branch}").stdout.strip()
    if not tip:
        return
    if remote not in _REMOTE_GONE:
        print(
            f"  kept local branch {branch}: its branch on GitHub was not deleted ({remote}), "
            f"and the local one goes only with it (`git branch -D {branch}` once it has)"
        )
        return
    # The commits on the branch the merged head does not hold: none, and
    # everything on it merged. A head this clone does not have — or none
    # known — fails the count, which keeps the branch too.
    unmerged = _git("rev-list", "--count", f"{merged_head}..{tip}") if merged_head else None
    if unmerged is None or unmerged.returncode != 0 or unmerged.stdout.strip() != "0":
        print(
            f"[warn] local branch {branch} (at {tip[:7]}) holds commits the merge at "
            f"{merged_head[:7] or 'an unknown head'} does not, or this clone cannot tell; it "
            f"is kept. Delete it yourself once nothing on it is needed "
            f"(`git branch -D {branch}`).",
            file=sys.stderr,
        )
        return
    proc = _git("branch", "-D", branch)
    if proc.returncode != 0:
        print(
            f"[warn] git branch -D {branch} failed: {proc.stderr.strip()}",
            file=sys.stderr,
        )
