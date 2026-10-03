"""How a pull request lands today, for every caller: one table of scenarios (#1253).

Three copies of the landing sequence exist — project-management's
(`_lib.pr_merge.land`, run by `done-work` and `merge-pr`), the backbone's
`pkit release merge` (`release.merge_release_pr`), and `land-work`, which lands
through `done-work`. The landing series (#1220) moves them into one command;
this table pins, before any of it moves, what each caller does in each
scenario, so every change in the series shows as an edited cell with its
reason.

Each row is a scenario of the series' design note (the scratchpad note
`landing-sequence`, "The scenario table"). Each
caller runs through its real entry point — `done_work.run`, merge-pr's `main`,
`pkit release merge` through the CLI, land-work's `main` — on one fake of the
hosting service and the clone (`tests.hosting_fake`); project-management's
`pkit pull-request` calls run the real backbone in this process. Stubbed are
only what the callers' own tests stub: the membership and bootstrap gates,
the capability's configuration, the approval gate (the reviewers), the moves
`done-work` makes after a merge and merge-pr's after-merge hooks (both
recorded), and the backbone's naming of the default branch — and, in the rows
where the two disagree, project-management's copy of the cross-repository
guard's comparison. The backbone's guard runs as it is, recorded.

A row's cells (:class:`Row`) are in one order — done-work, merge-pr, release
merge, land-work. A cell (:class:`Cell`) records what the caller's run came
to, the landing's requests the service received, in order, whether the steps
after the merge ran, what became of the remote and the local head branch, and
how the backbone's deletion of the remote one ended. A cell no run can fill
today is :class:`NotToday`, with why. A `note` says why
a cell is as it is where the outcome does not: an accident a later PR of the
series changes, or a difference by design.
"""

from __future__ import annotations

import importlib.util
import json
import os
import stat
import sys
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Any

import click
import pytest

from project_kit import cli, pull_request_landing, session_guard
from tests import hosting_fake as fake

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"

ISSUE = 42
PR = 496

DONE_WORK = "done-work"
MERGE_PR = "merge-pr"
RELEASE = "release merge"
LAND_WORK = "land-work"
CALLERS = (DONE_WORK, MERGE_PR, RELEASE, LAND_WORK)

# The options a scenario asks of a caller, as each caller spells them; a
# caller without one cannot run that scenario (its cell is NotToday).
_OPTIONS: Mapping[str, Mapping[str, list[str]]] = {
    DONE_WORK: {
        "admin": ["--admin"],
        "bypass-ci": ["--bypass-ci", "a flaky check"],
        "force": ["--force"],
        "short-wait": ["--wait-minutes", "1"],
        "allow-foreign-repo": ["--allow-foreign-repo"],
    },
    MERGE_PR: {
        "admin": ["--admin"],
        "bypass-ci": ["--bypass-ci", "a flaky check"],
        "force": ["--force"],
        "short-wait": ["--wait-minutes", "1"],
        "allow-foreign-repo": ["--allow-foreign-repo"],
    },
    RELEASE: {
        "force": ["--force"],
        "short-wait": ["--wait-minutes", "1"],
        "allow-foreign-repo": ["--allow-foreign-repo"],
    },
    LAND_WORK: {
        "short-wait": ["--wait-minutes", "1"],
        "allow-foreign-repo": ["--allow-foreign-repo"],
    },
}


# ---- the table's cells ---------------------------------------------------------------


@dataclass(frozen=True)
class Cell:
    """What one caller's run came to in one scenario.

    `outcome` — done-work: its `DoneWorkRun` kind and exit, and `retry` when
    it says running again can help; merge-pr: its exit, and the record it left
    in the clone (`record=owed` or `record=ran`); release: its exit — before
    #1256, `hangs` when a request that is never answered held the run;
    land-work: its exit and the gist of its last step line. A scenario that
    runs the caller again says each run's end in turn (`a → b`).
    `requests` — the landing's requests the service received, in order
    (`hosting_fake.LANDING`; `read×3` is three running).
    `after` — the steps after the merge ran: done-work's move to Done and its
    closes, merge-pr's after-merge hooks, release's branch clean-up (its only
    step after the merge).
    `remote` — what became of the PR's head branch on the service: `none` (not
    asked), or what the deletion did (`deleted`, `gone`, `refused, protected`,
    `deleted, tip … moved`, `deleted, closed #N`).
    `local` — the local clean-up: `deleted`, `kept`, `absent` (the clone had
    no such branch) or `none` (no clean-up ran).
    `asked` — the questions a terminal was asked.
    `guard` — the backbone's cross-repository guard (#1254), wherever it did
    not find the session's own repository: how it cleared each change, as its
    documents' `cleared` says it (`undetermined`, `flag`, `terminal`), or
    `refused` where `cleared` is null; empty where it cleared as `same-repo`,
    and where it did not run, as before #1254.
    `deletion` — the backbone's deletion of the head branch on the service
    (#1255), wherever one ran: how it ended, as its document's `outcome`
    says it, with its `reason_kind` (`deleted`, `kept tip-moved`, `gone`,
    `refused cross-repository`); empty where none ran, as before #1255.
    """

    outcome: str
    requests: str = ""
    after: bool = False
    remote: str = "none"
    local: str = "none"
    asked: int = 0
    guard: str = ""
    deletion: str = ""
    note: str = field(default="", compare=False)


def merged(
    outcome: str,
    requests: str,
    *,
    remote: str = "deleted",
    local: str = "deleted",
    asked: int = 0,
    guard: str = "",
    deletion: str = "",
    note: str = "",
) -> Cell:
    """A run after whose merge every step ran."""
    return Cell(outcome, requests, True, remote, local, asked, guard, deletion, note)


def stopped(
    outcome: str, requests: str = "", *, asked: int = 0, guard: str = "", note: str = ""
) -> Cell:
    """A run that ended with no step after a merge run, and no branch deleted."""
    return Cell(outcome, requests, asked=asked, guard=guard, note=note)


def _deleted(
    outcome: str,
    requests: str,
    *,
    local: str = "deleted",
    asked: int = 0,
    guard: str = "",
    note: str = "",
) -> Cell:
    """A run after whose merge every step ran, the head branch deleted by the
    backbone (#1255): one reading of the branch (`branch`), one of the open
    PRs based on it (`based-on`, #1285), then one compare-and-delete at the
    head that merged (`delete-ref`)."""
    return merged(
        outcome, requests, local=local, asked=asked, guard=guard, deletion="deleted", note=note
    )


@dataclass(frozen=True)
class NotToday:
    """A cell no run fills today, and why: the caller has no such option, or
    the scenario needs what does not exist yet."""

    why: str


@dataclass(frozen=True)
class Row:
    """A scenario's cells, one per caller, in the callers' order."""

    done_work: Cell | NotToday
    merge_pr: Cell | NotToday
    release: Cell | NotToday
    land_work: Cell | NotToday

    def cell(self, caller: str) -> Cell | NotToday:
        cells = {
            DONE_WORK: self.done_work,
            MERGE_PR: self.merge_pr,
            RELEASE: self.release,
            LAND_WORK: self.land_work,
        }
        return cells[caller]


@dataclass(frozen=True)
class Scenario:
    """One row: what the scenario is, how it is set up, and each caller's cell."""

    id: str
    what: str
    setup: Callable[[World], None]
    today: Row
    #: The cell a later PR of the landing series expects, by caller: where one
    #: is named, the test holds the caller to it, and `today` keeps what the
    #: caller did before that PR.
    after: Mapping[str, Cell | NotToday] = field(default_factory=dict)

    def expected(self, caller: str) -> Cell | NotToday:
        return self.after.get(caller, self.today.cell(caller))


@dataclass
class World:
    """One run's world, which a scenario's setup shapes before the run."""

    host: fake.HostingService
    clone: fake.LocalClone
    tmp: Path
    #: The session anchor; None runs outside any session.
    anchor: Path | None
    stdin: fake.Terminal | fake.NoTerminal = field(default_factory=fake.NoTerminal)
    #: The options asked of the caller (`_OPTIONS`).
    options: tuple[str, ...] = ()
    #: The backbone project-management asks: the current one, or one that
    #: predates `pkit pull-request`.
    backbone_has_the_noun: bool = True
    rewrite: fake.Rewrite | None = None
    #: project-management's copy of the guard's comparison finds the session's
    #: own repository, whatever the backbone's finds: the two disagree.
    pm_reads_same_repository: bool = False
    #: How many times the caller is run, one after the other, on the same
    #: service and clone: a re-run sees what the runs before it left.
    runs: int = 1

    def elsewhere(self) -> Path:
        """Another repository on the machine, the anchor of a session rooted there."""
        other = self.tmp / "other"
        other.mkdir(exist_ok=True)
        self.clone.elsewhere[other] = "https://github.com/octo/other.git"
        return other


# ---- the scenarios' setups -----------------------------------------------------------


def _direct(world: World) -> None:
    """A base without a queue: the fake's default."""


def _queue(world: World, *, method: str = "SQUASH") -> None:
    world.host.set_base(fake.Base(queue=True, method=method))


def _queue_merges(world: World) -> None:
    _queue(world)
    world.host.progress = [fake.at(2), fake.at(1, "MERGEABLE"), fake.lands()]


def _checks_pending(world: World) -> None:
    _queue(world)
    world.host.checks_pending = True
    world.host.progress = [fake.unchanged(), fake.at(2), fake.at(1, "MERGEABLE"), fake.lands()]


def _already_queued(world: World, *, method: str = "SQUASH") -> None:
    _queue(world, method=method)
    world.host.enter_queue()
    world.host.entry = (1, "MERGEABLE")
    world.host.progress = [fake.at(1, "MERGEABLE"), fake.at(1, "MERGEABLE"), fake.lands()]


def _out_of_the_queue_after_the_first_read(world: World) -> None:
    """Queued at the checked head at the caller's first reading — release's
    plan — and dropped by the queue just after it."""
    _already_queued(world)
    world.host.after(fake.READ, lambda host: host.drop())


def _wait_runs_out(world: World) -> None:
    _queue(world)
    world.options = ("short-wait",)
    world.host.progress = [fake.at(3, "QUEUED")]


def _merge_only_enqueued(world: World) -> None:
    world.host.merge_enqueues = True
    world.host.progress = [fake.at(1), fake.lands()]


def _auto_merge_held_on_a_direct_base(world: World) -> None:
    """Auto-merge holds the PR, and the base's requirements are met by the
    time the caller merges: the fake's direct merge goes through."""
    world.host.auto_merge = True
    world.host.progress = [fake.unchanged(), fake.unchanged(), fake.unchanged(), fake.lands()]


def _auto_merge_held_for_unmet_requirements(world: World) -> None:
    """The same, the base's requirements unmet — what auto-merge holds the PR
    for: gh refuses the plain merge, and auto-merge stays armed."""
    _auto_merge_held_on_a_direct_base(world)
    world.host.requirements_met = False


def _queue_switched_on(world: World) -> None:
    world.host.after(fake.READ, lambda host: host.set_base(fake.Base(queue=True)))
    world.host.progress = [fake.at(1), fake.lands()]


def _base_changed(world: World) -> None:
    _queue(world)
    world.host.after(
        fake.READ, lambda host: host.retarget("develop", fake.Base(queue=True, method="MERGE"))
    )
    world.host.progress = [fake.at(1), fake.lands()]


def _admin_on_a_queue(world: World) -> None:
    _queue(world)
    world.options = ("admin",)


def _bypass_ci_on_a_queue(world: World) -> None:
    _queue(world)
    world.options = ("bypass-ci",)


def _not_squash(world: World) -> None:
    _queue(world, method="MERGE")


def _defaults_not_the_convention(world: World) -> None:
    _queue(world)
    world.host.squash_defaults = ("COMMIT_OR_PR_TITLE", "COMMIT_MESSAGES")


def _defaults_unreadable(world: World) -> None:
    _queue(world)
    world.host.squash_defaults = None


def _already_queued_not_squash(world: World) -> None:
    _already_queued(world, method="MERGE")


def _dropped_head(world: World) -> None:
    _queue(world)
    world.host.dropped_before()


def _dropped_head_forced(world: World) -> None:
    _dropped_head(world)
    world.options = ("force",)
    world.host.progress = [fake.at(1), fake.lands()]


def _head_moves_while_queued(world: World) -> None:
    _queue(world)
    world.host.progress = [fake.at(2), fake.pushes(fake.oid("pushed"))]


def _head_moves_dequeue_fails(world: World) -> None:
    _head_moves_while_queued(world)
    world.host.fail(fake.DEQUEUE, count=None, stderr="GraphQL: Something went wrong")


def _queued_at_another_head(world: World) -> None:
    _already_queued(world)
    world.host.progress = []
    world.host.before(fake.READ, lambda host: host.push(fake.oid("pushed")))


def _merged_before(world: World) -> None:
    world.host.merge_now()


def _merged_by_the_queue_before(world: World) -> None:
    _queue(world)
    world.host.enter_queue()
    world.host.merge_now()


def _merged_meanwhile(world: World) -> None:
    world.host.before(fake.READ, lambda host: host.merge_now())


def _merged_meanwhile_elsewhere(world: World) -> None:
    world.host.before(fake.READ, lambda host: host.merge_now(head=fake.oid("other")))


def _race_on_a_direct_base(world: World) -> None:
    world.host.before(fake.MERGE, lambda host: host.merge_now())


def _race_on_a_queue(world: World) -> None:
    _queue(world)
    world.host.before(fake.ENQUEUE, lambda host: host.enter_queue())
    world.host.progress = [fake.at(1), fake.lands()]


def _closed_before(world: World) -> None:
    world.host.close()


def _closed_meanwhile(world: World) -> None:
    world.host.before(fake.READ, lambda host: host.close())


def _unanswered_then_merged(world: World) -> None:
    world.host.lose_reply(fake.MERGE)


def _unanswered_then_queued(world: World) -> None:
    _queue(world)
    world.host.lose_reply(fake.ENQUEUE)
    world.host.progress = [fake.at(1), fake.lands()]


def _unanswered_then_neither(world: World) -> None:
    world.host.never_receive(fake.MERGE)


def _merged_after_the_readings(world: World) -> None:
    """The merge gets no answer and the two readings that settle it do not
    see it made; the service applies it just after the second of them, and
    the caller is run again."""
    world.runs = 2

    def late(host: fake.HostingService) -> None:
        host.after(fake.READ, lambda service: service.merge_now(), nth=host.seen(fake.READ) + 2)

    world.host.never_receive(fake.MERGE)
    world.host.before(fake.MERGE, late)


def _unanswered_then_unreadable(world: World) -> None:
    world.host.lose_reply(fake.MERGE)
    world.host.after(fake.MERGE, _fail_every_read)


def _enqueue_unanswered_then_unreadable(world: World) -> None:
    _queue(world)
    world.host.lose_reply(fake.ENQUEUE)
    world.host.after(fake.ENQUEUE, _fail_every_read)


def _killed_mid_merge_made(world: World) -> None:
    world.host.kill_mid_request(fake.MERGE, made=True)


def _killed_mid_merge_unmade(world: World) -> None:
    world.host.kill_mid_request(fake.MERGE, made=False)


def _fail_the_next_read(host: fake.HostingService) -> None:
    host.fail(fake.READ)


def _read_fails_once_after_a_merge(world: World) -> None:
    world.host.after(fake.MERGE, _fail_the_next_read)


def _made_then_gh_failed(world: World) -> None:
    world.host.error_after(fake.MERGE)


def _fail_every_read(host: fake.HostingService) -> None:
    host.fail(fake.READ, count=None)


def _read_fails_after_a_merge(world: World) -> None:
    world.host.after(fake.MERGE, _fail_every_read)


def _read_fails_after_an_enqueue(world: World) -> None:
    _queue(world)
    world.host.after(fake.ENQUEUE, _fail_every_read)


def _rate_limit_mid_wait(world: World) -> None:
    _queue_merges(world)

    def limit(host: fake.HostingService) -> None:
        host.fail(
            fake.READ,
            first=host.seen(fake.READ) + 2,
            stderr="gh: API rate limit exceeded for user ID 1. (HTTP 403)",
        )

    world.host.after(fake.ENQUEUE, limit)


def _auto_merge_not_allowed(world: World) -> None:
    _queue(world)
    world.host.auto_merge_allowed = False


def _not_drivable(world: World) -> None:
    raise AssertionError("a row no caller can run today has no setup to run")


def _tip_moved(world: World) -> None:
    world.host.after(fake.MERGE, lambda host: host.move_branch("sha-later"))


def _tip_gone(world: World) -> None:
    def deleted_on_merge(host: fake.HostingService) -> None:
        host.refs.pop(host.head_ref, None)

    world.host.after(fake.MERGE, deleted_on_merge)


def _fork(world: World) -> None:
    world.host.cross_repository = True


def _protected(world: World) -> None:
    world.host.protected.add(world.host.head_ref)


def _another_open_pr(world: World) -> None:
    host = world.host
    host.others.append(fake.OtherPullRequest(501, host.head_ref, host.head_oid))


def _another_open_pr_based_on_it(world: World) -> None:
    host = world.host
    host.others.append(
        fake.OtherPullRequest(503, "fix/43-on-top", fake.oid("on-top"), base_ref=host.head_ref)
    )


def _reused_name(world: World) -> None:
    _merged_by_the_queue_before(world)
    host = world.host
    host.move_branch("sha-new")
    host.others.append(fake.OtherPullRequest(502, host.head_ref, "sha-new"))
    world.clone.branches.pop(host.head_ref)
    world.clone.current = "main"


def _foreign_refused(world: World) -> None:
    world.anchor = world.elsewhere()


def _foreign_flagged(world: World) -> None:
    world.anchor = world.elsewhere()
    world.options = ("allow-foreign-repo",)


def _foreign_at_a_terminal(world: World) -> None:
    world.anchor = world.elsewhere()
    world.stdin = fake.Terminal("y")


def _foreign_declined_at_a_terminal(world: World) -> None:
    world.anchor = world.elsewhere()
    world.stdin = fake.Terminal("n")


def _comparisons_disagree(world: World) -> None:
    world.anchor = world.elsewhere()
    world.pm_reads_same_repository = True


def _comparisons_disagree_flagged(world: World) -> None:
    _comparisons_disagree(world)
    world.options = ("allow-foreign-repo",)


def _comparison_faults(world: World) -> None:
    world.clone.comparison_fault = True


def _no_anchor(world: World) -> None:
    world.anchor = None


def _backbone_without_the_noun(world: World) -> None:
    world.backbone_has_the_noun = False


def _unknown_end(world: World) -> None:
    _queue_merges(world)

    def rewrite(args: list[str], document: dict[str, Any]) -> dict[str, Any]:
        if args[0] == "wait" and document.get("event") == "end":
            return {**document, "ended": "landed"}
        return document

    world.rewrite = rewrite


def _missing_key(world: World) -> None:
    def rewrite(args: list[str], document: dict[str, Any]) -> dict[str, Any]:
        reading = document.get("reading")
        if args[0] == "read" and isinstance(reading, dict):
            return {**document, "reading": {k: v for k, v in reading.items() if k != "queued"}}
        return document

    world.rewrite = rewrite


# ---- the table -----------------------------------------------------------------------
#
# Each row's cells are in the callers' order: done-work, merge-pr, release
# merge, land-work. The requests: `read` the queue reading, `defaults` the
# repository's squash-commit defaults, `merge` and `enqueue` the requests,
# `dequeue`, `branch` the backbone's reading of the head branch before it
# deletes it (#1255), `based-on` its reading of the open PRs based on that
# branch (#1285), and `delete-ref` the head branch's deletion.

_NO_ADMIN = NotToday("takes no --admin")
_NO_BYPASS_CI = NotToday("takes no --bypass-ci: its CI gate has no override")
_NO_FORCE = NotToday("takes no --force: a dropped head is done-work's refusal")
_NO_FOREIGN_FLAG = NotToday("takes no --allow-foreign-repo: the command has no guard")
_NO_NOUN = NotToday("is the backbone: it imports the landing module and asks no command")
_NO_DOCUMENTS = NotToday("imports the landing module: no document passes between processes")
_NO_REQUESTING = NotToday(
    "no `requesting` event exists yet (it comes with `land`, #1258); the request-unanswered "
    "rows are the nearest today"
)

_UNGUARDED = (
    "accident: `pkit release merge` has no cross-repository guard (ADR-061 point 6); #1254 adds it"
)
_UNGUARDED_REQUEST = (
    "accident: the backbone's merge request runs no guard of its own, so the verb's comparison "
    "alone decides (ADR-061 point 6); #1254 adds the backbone's"
)
_REFUSED_AT_ENTRY = (
    "its guard runs at the entry and refuses, with no yes and no flag: nothing is read or merged"
)
_FLAG_PASSED_ON = (
    "the backbone's guard runs on the merge and on the branch's deletion, and passes each by the "
    "flag the verb passes on, its own guard having passed by it"
)
_YES_PASSED_ON = (
    "asked once, by the verb's own guard; the yes is passed on, so the backbone's guard passes "
    "by the flag"
)
_FAILS_CLOSED = (
    "the backbone's guard refuses the merge the verb's let through: a disagreement with no "
    "confirmation fails closed, nothing is asked of GitHub, and the verb names both verdicts"
)
_FLAG_OVERRIDES = (
    "the operator's flag is passed on whatever the verb's own comparison found, so the "
    "backbone's guard passes by it: a disagreement yields to the operator's confirmation"
)
_SIBLINGS_STUBBED = (
    "the moves and closes after the merge are stubbed here, so their own guards do not run; "
    "that they are handed the confirmation is test_pm_done_work's"
)
_FAULT = "both guards warn and go on: a git fault is no refusal; the backbone's passes undetermined"
_NO_FIRE = (
    "no anchor, no fire: the backbone's guard passes undetermined, never same-repo, and needs "
    "no flag"
)
_TIP_UNCHECKED = (
    "accident: the branch is deleted without its tip being checked against the merged head "
    "(ADR-061's fifth obligation); #1255 deletes only at that head"
)
_TIP_KEPT = (
    "kept: the branch's tip moved after the merge, so the push is not lost; nothing but the "
    "reading is asked of the service, and the local branch stays with it"
)
_FOUND_GONE = (
    "the repository deleted the branch as the PR merged: the reading finds it gone, and nothing "
    "more is asked"
)
_FORK_REFUSED = (
    "the backbone refuses: the head is in a fork, whose owner keeps its branches; the reading "
    "says so, and nothing more is asked"
)
_PROTECTED_KEPT = (
    "kept, with what the service said: it answers the compare-and-delete with an error that says "
    "only that something went wrong, and a second reading finds the branch still at the head "
    "that merged; the local branch stays with it"
)
_IN_USE_KEPT = (
    "kept, as ruled for #1255: deleting the branch would close #501, which uses it as its head; "
    "nothing but the readings is asked, and the local branch stays with it"
)
_BASE_UNCHECKED = (
    "accident: the branch #503 is based on is deleted, whatever the service then does to #503; "
    "the round of #1285 keeps it"
)
_BASE_KEPT = (
    "kept: #503 is based on the branch, and what the service does to a PR whose base is deleted "
    "is not gambled on; nothing but the readings is asked, and the local branch stays with it"
)
_REUSED_KEPT = (
    "kept: the branch's tip is #502's, not the head that merged, so the newer PR keeps its branch"
)
_HANGS = (
    "accident: release bounds no `gh` call and has no path for a request that gets no "
    "answer: the run waits on it for ever (#1256)"
)
_ONE_READING = (
    "accident: one reading neither merged nor queued is taken for 'the request was not made' "
    "(#1256 reads twice)"
)
_NOT_READ_AGAIN = (
    "accident: release reads the queue once, before its gates, and not again before the request"
)
_MADE_THEN_FAILED = (
    "accident: a request gh reports failed after the service made it is taken for a failed "
    "one, so what follows the merge does not run"
)
_SETTLED_MADE = (
    "the backbone's bound ends the `gh` that never answers, and its reading since finds the "
    "request made: the landing goes on as made (#1256); the caller reads once more after a "
    "merge it is told was made"
)
_LOST_ANSWER_SETTLED = (
    "a 502 is an answer lost on the way, not the service's refusal: the backbone reads the PR "
    "merged since, and the landing goes on as merged (#1256)"
)
_SETTLED_NOT_MADE = (
    "neither merged nor queued on two readings, the second the window after the request: the "
    "backbone says the merge was not seen made — what the readings saw — and the caller stops "
    "as for a failed request, its re-run reading the PR first (#1256)"
)
_OUT_ON_TWO_READINGS = (
    "out of the queue rests on two readings running, as the wait's does: the dequeue is "
    "confirmed by a second reading, no sooner than the window after it was sent (#1256)"
)
_OWED_ON_A_SENT_REQUEST = (
    "merge-pr records the after-merge steps as owed whenever its run sent a merge or an "
    "enqueue GitHub did not refuse and did not see merged, so its re-run completes a merge "
    "that shows later (#1256)"
)
_MERGED_LATE = (
    "the merge got no answer, two readings did not see it made, and the service applied it "
    "just after them: every caller's re-run reads the PR first and completes it — merge-pr's "
    "because its first run left the after-merge steps owed (#1256)"
)
_SETTLED_UNCONFIRMED = (
    "unconfirmed, exit 4, nothing after the merge run: before #1256 pm's own reading after no "
    "document failed; since, the backbone's bound ends the `gh`, its reading fails, and pm "
    "takes the unconfirmed from its document, reading nothing more — the same requests"
)
_RELEASE_UNCONFIRMED = (
    "the bound ends the `gh` that never answers, and with GitHub unreadable since the report "
    "is unconfirmed — what was asked, that whether it was made is not known, the reading that "
    "tells — exit 4, nothing deleted (#1256)"
)
_KILLED_ONE_READING = (
    "pm's bound ended the `pkit` group, the `gh` in it, so no document came back; one reading "
    "neither merged nor queued is unconfirmed, never 'not made' (#1256)"
)
_NO_ONE_LEFT = NotToday(
    "imports the landing module: a kill ends its own run, with nothing left to read what the "
    "request came to"
)
_PLANNED = (
    "release lands through the backbone's landing (#1258): it plans first, a dry run of the "
    "landing — one reading, and the squash-commit defaults where the base has a queue — and "
    "the landing reads both again before its request"
)
_MERGED_IN_THE_PLAN = (
    "merged is taken from the landing's plan, not from release's own view (#1258): the plan's "
    "reading"
)
_CLOSED_IN_THE_PLAN = (
    "by design: nothing to merge; closed is taken from the landing's plan, not from release's "
    "own view (#1258): the plan's reading"
)
_ALREADY_QUEUED = (
    "by design: a release PR the queue holds is waited for without its gates; the plan reads "
    "it and the squash-commit defaults, and the landing reads both again before it waits (#1258)"
)
_HELD_ON_A_DIRECT_BASE = (
    "auto-merge's hold on a base without a queue is the direct row (#1258): release gates and "
    "merges directly, as project-management does, where it used to take the hold for a queue, "
    "warn of a queue that does not squash, and wait without its gates"
)
_PM_HELD_UNMET = (
    "gh refuses the plain merge; project-management's copy reports the refusal and says "
    "nothing of the auto-merge left armed, which merges the PR, unpinned, once the "
    "requirements are met (#1220)"
)
_HELD_TODAY = NotToday(
    "took auto-merge's hold for a queue before #1258 and waited without its gates, sending no "
    "merge; the row with the requirements met records that"
)
_HELD_UNMET = (
    "the direct row (#1258): release gates and sends the direct merge, which gh refuses, so the "
    "landing fails, nothing sent, with a warning that auto-merge is still armed and merges the "
    "PR, unpinned, once the requirements are met — the fake's model of the service, not a real "
    "call's"
)
_BASE_CHANGED = (
    "the landing reads the PR just before its request, finds the new base's queue merging by "
    "MERGE, and refuses, as project-management does: the accident is gone (#1258)"
)
_QUEUE_SWITCHED_ON = (
    "the landing reads the PR just before its request, finds the queue switched on, reads the "
    "squash-commit defaults and enqueues, as project-management does: the accident is gone (#1258)"
)
_QUEUED_ELSEWHERE = (
    f"{_OUT_ON_TWO_READINGS}; the plan finds the PR queued at another head and skips the gates, "
    "and the landing takes it out, reading no squash-commit defaults for a PR it does not wait "
    "for (#1258)"
)
_CLOSED_MEANWHILE = (
    "closed is taken from the landing's plan, not from release's own view (#1258): the plan "
    "reads it closed — nothing to merge, exit 0, as for a PR closed before the run — where "
    "release, its view open, used to send a merge gh refused"
)
_DROPPED_HEAD_FIRST = (
    "the one refusal order reads the squash-commit defaults last, after the dropped head: the "
    "plan refuses on its first reading, as project-management does (#1258)"
)
_PM_READS_AGAIN = (
    "it reads the PR again after the squash-commit defaults, finds it dropped at the checked "
    "head, and refuses the dropped head, nothing sent"
)
_NO_PLAN = NotToday(
    "planned nothing before #1258: release read the queue once, so no reading came between a "
    "plan and the landing for the PR to leave the queue in"
)
_LEFT_AFTER_THE_PLAN = (
    "the plan finds the PR queued at the checked head and skips the gates, so the landing "
    "allows no request (#1258): it finds the PR out of the queue and refuses, nothing sent, and "
    "a re-run plans afresh and gates"
)
_REQUESTING_ON_LAND = NotToday(
    "imports the landing (#1258): `requesting` is written by `pkit pull-request land`, where "
    "the kill between it and the request is tested; a kill ends release's own run, with nothing "
    "left to read the line"
)

SCENARIOS: tuple[Scenario, ...] = (
    # ---- landing ---------------------------------------------------------------------
    Scenario(
        "no-queue",
        "A base without a queue: one direct squash merge, pinned to the checked head.",
        _direct,
        Row(
            merged("merged 0", "read×2 merge read delete-ref"),
            merged("0 record=ran", "read×2 merge read delete-ref"),
            merged("0", "read merge read delete-ref"),
            merged("0 merge: merged", "read×2 merge read delete-ref"),
        ),
        after={
            DONE_WORK: _deleted("merged 0", "read×2 merge read branch based-on delete-ref"),
            MERGE_PR: _deleted("0 record=ran", "read×2 merge read branch based-on delete-ref"),
            RELEASE: _deleted("0", "read×2 merge read branch based-on delete-ref", note=_PLANNED),
            LAND_WORK: _deleted("0 merge: merged", "read×2 merge read branch based-on delete-ref"),
        },
    ),
    Scenario(
        "queue-merges-within-the-wait",
        "The PR is enqueued, moves up the queue, and the queue merges it within the wait.",
        _queue_merges,
        Row(
            merged("merged 0", "read defaults read defaults enqueue read×3 delete-ref"),
            merged("0 record=ran", "read defaults read defaults enqueue read×3 delete-ref"),
            merged("0", "read defaults enqueue read×3 delete-ref"),
            merged("0 merge: merged", "read defaults read defaults enqueue read×3 delete-ref"),
        ),
        after={
            DONE_WORK: _deleted(
                "merged 0", "read defaults read defaults enqueue read×3 branch based-on delete-ref"
            ),
            MERGE_PR: _deleted(
                "0 record=ran",
                "read defaults read defaults enqueue read×3 branch based-on delete-ref",
            ),
            RELEASE: _deleted(
                "0",
                "read defaults read defaults enqueue read×3 branch based-on delete-ref",
                note=_PLANNED,
            ),
            LAND_WORK: _deleted(
                "0 merge: merged",
                "read defaults read defaults enqueue read×3 branch based-on delete-ref",
            ),
        },
    ),
    Scenario(
        "queue-checks-pending",
        "Its required checks still running, the PR is held by auto-merge, then enters the "
        "queue, which merges it.",
        _checks_pending,
        Row(
            merged("merged 0", "read defaults read defaults enqueue read×4 delete-ref"),
            merged("0 record=ran", "read defaults read defaults enqueue read×4 delete-ref"),
            merged("0", "read defaults enqueue read×4 delete-ref"),
            merged("0 merge: merged", "read defaults read defaults enqueue read×4 delete-ref"),
        ),
        after={
            DONE_WORK: _deleted(
                "merged 0", "read defaults read defaults enqueue read×4 branch based-on delete-ref"
            ),
            MERGE_PR: _deleted(
                "0 record=ran",
                "read defaults read defaults enqueue read×4 branch based-on delete-ref",
            ),
            RELEASE: _deleted(
                "0",
                "read defaults read defaults enqueue read×4 branch based-on delete-ref",
                note=_PLANNED,
            ),
            LAND_WORK: _deleted(
                "0 merge: merged",
                "read defaults read defaults enqueue read×4 branch based-on delete-ref",
            ),
        },
    ),
    Scenario(
        "already-queued",
        "A re-run while the queue holds the PR: waited for, not enqueued again.",
        _already_queued,
        Row(
            merged("merged 0", "read defaults read defaults read delete-ref"),
            merged("0 record=ran", "read defaults read defaults read delete-ref"),
            merged(
                "0",
                "read defaults read×2 delete-ref",
                note="by design: a release PR the queue holds is waited for without its gates",
            ),
            merged("0 merge: merged", "read defaults read defaults read delete-ref"),
        ),
        after={
            DONE_WORK: _deleted(
                "merged 0", "read defaults read defaults read branch based-on delete-ref"
            ),
            MERGE_PR: _deleted(
                "0 record=ran", "read defaults read defaults read branch based-on delete-ref"
            ),
            RELEASE: _deleted(
                "0",
                "read defaults read defaults read branch based-on delete-ref",
                note=_ALREADY_QUEUED,
            ),
            LAND_WORK: _deleted(
                "0 merge: merged", "read defaults read defaults read branch based-on delete-ref"
            ),
        },
    ),
    Scenario(
        "out-of-the-queue-after-the-first-read",
        "Queued at the checked head at the caller's first reading, then dropped by the queue "
        "before the landing's.",
        _out_of_the_queue_after_the_first_read,
        Row(
            stopped("refused 1", "read defaults read", note=_PM_READS_AGAIN),
            stopped("1", "read defaults read", note=_PM_READS_AGAIN),
            _NO_PLAN,
            stopped("1 merge: refused", "read defaults read", note=_PM_READS_AGAIN),
        ),
        after={RELEASE: stopped("1", "read defaults read", note=_LEFT_AFTER_THE_PLAN)},
    ),
    Scenario(
        "wait-runs-out",
        "The queue holds the PR past a one-minute wait.",
        _wait_runs_out,
        Row(
            stopped("queued 4", "read defaults read defaults enqueue read×5"),
            stopped("4 record=owed", "read defaults read defaults enqueue read×5"),
            stopped("4", "read defaults enqueue read×5"),
            stopped("4 merge: queued", "read defaults read defaults enqueue read×6"),
        ),
        after={RELEASE: stopped("4", "read defaults read defaults enqueue read×5", note=_PLANNED)},
    ),
    Scenario(
        "merge-only-enqueued",
        "The reading names no queue, yet gh's direct merge only enqueues the PR, which the "
        "queue then merges.",
        _merge_only_enqueued,
        Row(
            merged("merged 0", "read×2 merge read×2 delete-ref"),
            merged("0 record=ran", "read×2 merge read×2 delete-ref"),
            merged("0", "read merge read×2 delete-ref"),
            merged("0 merge: merged", "read×2 merge read×2 delete-ref"),
        ),
        after={
            DONE_WORK: _deleted("merged 0", "read×2 merge read×2 branch based-on delete-ref"),
            MERGE_PR: _deleted("0 record=ran", "read×2 merge read×2 branch based-on delete-ref"),
            RELEASE: _deleted("0", "read×2 merge read×2 branch based-on delete-ref", note=_PLANNED),
            LAND_WORK: _deleted(
                "0 merge: merged", "read×2 merge read×2 branch based-on delete-ref"
            ),
        },
    ),
    Scenario(
        "auto-merge-held-on-a-direct-base",
        "A base without a queue, where auto-merge holds the PR until GitHub merges it; the "
        "base's requirements are met by the time the caller merges.",
        _auto_merge_held_on_a_direct_base,
        Row(
            merged("merged 0", "read×2 merge read delete-ref"),
            merged("0 record=ran", "read×2 merge read delete-ref"),
            merged(
                "0",
                "read×4 delete-ref",
                note="release reads auto-merge's hold as the queue: it skips its gates, warns "
                "that the queue merges by an unreported method on a base with no queue, and "
                "waits for GitHub's merge",
            ),
            merged("0 merge: merged", "read×2 merge read delete-ref"),
        ),
        after={
            DONE_WORK: _deleted("merged 0", "read×2 merge read branch based-on delete-ref"),
            MERGE_PR: _deleted("0 record=ran", "read×2 merge read branch based-on delete-ref"),
            RELEASE: _deleted(
                "0", "read×2 merge read branch based-on delete-ref", note=_HELD_ON_A_DIRECT_BASE
            ),
            LAND_WORK: _deleted("0 merge: merged", "read×2 merge read branch based-on delete-ref"),
        },
    ),
    Scenario(
        "auto-merge-held-for-unmet-requirements",
        "A base without a queue, where auto-merge holds the PR because the base's "
        "requirements are not met, so gh refuses a plain merge.",
        _auto_merge_held_for_unmet_requirements,
        Row(
            stopped("refused 3 retry", "read×2 merge", note=_PM_HELD_UNMET),
            stopped("3", "read×2 merge", note=_PM_HELD_UNMET),
            _HELD_TODAY,
            stopped("7 merge: not merged", "read×2 merge", note=_PM_HELD_UNMET),
        ),
        after={RELEASE: stopped("1", "read×2 merge", note=_HELD_UNMET)},
    ),
    Scenario(
        "queue-switched-on-after-the-first-read",
        "The base starts merging through a queue after the caller's first reading.",
        _queue_switched_on,
        Row(
            merged("merged 0", "read×2 defaults enqueue read×2 delete-ref"),
            merged("0 record=ran", "read×2 defaults enqueue read×2 delete-ref"),
            merged(
                "0",
                "read merge read×2 delete-ref",
                note=f"{_NOT_READ_AGAIN}: gh's direct merge is enqueued, and the queue composes "
                "the commit from defaults release never read",
            ),
            merged("0 merge: merged", "read×2 defaults enqueue read×2 delete-ref"),
        ),
        after={
            DONE_WORK: _deleted(
                "merged 0", "read×2 defaults enqueue read×2 branch based-on delete-ref"
            ),
            MERGE_PR: _deleted(
                "0 record=ran", "read×2 defaults enqueue read×2 branch based-on delete-ref"
            ),
            RELEASE: _deleted(
                "0",
                "read×2 defaults enqueue read×2 branch based-on delete-ref",
                note=_QUEUE_SWITCHED_ON,
            ),
            LAND_WORK: _deleted(
                "0 merge: merged", "read×2 defaults enqueue read×2 branch based-on delete-ref"
            ),
        },
    ),
    Scenario(
        "base-changed-after-the-first-read",
        "After the caller's first reading the PR is retargeted to a base whose queue merges "
        "by MERGE.",
        _base_changed,
        Row(
            stopped("refused 1", "read defaults read"),
            stopped("1", "read defaults read"),
            merged(
                "0",
                "read defaults enqueue read×2 delete-ref",
                note=f"{_NOT_READ_AGAIN}: it enqueues into the new base's queue, which lands "
                "the PR as a merge commit",
            ),
            stopped("1 merge: refused", "read defaults read"),
        ),
        after={
            RELEASE: stopped("1", "read defaults read", note=_BASE_CHANGED),
        },
    ),
    # ---- refusals --------------------------------------------------------------------
    Scenario(
        "admin-on-a-queued-base",
        "--admin where the base merges through a queue.",
        _admin_on_a_queue,
        Row(stopped("refused 1", "read"), stopped("1", "read"), _NO_ADMIN, _NO_ADMIN),
    ),
    Scenario(
        "bypass-ci-on-a-queued-base",
        "--bypass-ci where the base merges through a queue.",
        _bypass_ci_on_a_queue,
        Row(stopped("refused 1", "read"), stopped("1", "read"), _NO_BYPASS_CI, _NO_BYPASS_CI),
    ),
    Scenario(
        "queue-not-squash",
        "The queue merges by MERGE.",
        _not_squash,
        Row(
            stopped("refused 1", "read"),
            stopped("1", "read"),
            stopped("1", "read"),
            stopped("1 merge: refused", "read"),
        ),
    ),
    Scenario(
        "squash-defaults-not-the-convention",
        "The repository's squash defaults are not the PR title over the PR body.",
        _defaults_not_the_convention,
        Row(
            stopped("refused 1", "read defaults"),
            stopped("1", "read defaults"),
            stopped("1", "read defaults"),
            stopped("1 merge: refused", "read defaults"),
        ),
    ),
    Scenario(
        "squash-defaults-unreadable",
        "The account cannot read the repository's squash defaults.",
        _defaults_unreadable,
        Row(
            stopped("unreadable 2", "read defaults"),
            stopped("3", "read defaults"),
            stopped("1", "read defaults", note="a refusal here; unreadable in project-management"),
            stopped("2 merge: stopped", "read defaults"),
        ),
    ),
    Scenario(
        "already-queued-not-squash",
        "A re-run while the queue holds the PR, and the queue merges by MERGE.",
        _already_queued_not_squash,
        Row(
            stopped(
                "refused 1",
                "read",
                note="refused, and the PR stays in the queue, which may still merge it",
            ),
            stopped("1", "read", note="refused, and the PR stays in the queue"),
            merged(
                "0",
                "read×3 delete-ref",
                note="by design: warns the commit will not be a release's, and lands it",
            ),
            stopped("1 merge: refused", "read", note="refused, and the PR stays in the queue"),
        ),
        after={
            RELEASE: _deleted("0", "read×3 branch based-on delete-ref"),
        },
    ),
    Scenario(
        "dropped-head",
        "The queue dropped the PR at its current head before the run.",
        _dropped_head,
        Row(
            stopped("refused 1", "read"),
            stopped("1", "read"),
            stopped(
                "1",
                "read defaults",
                note="accident: refused after its gates and the squash defaults; "
                "project-management refuses on the first reading",
            ),
            stopped("1 merge: refused", "read"),
        ),
        after={RELEASE: stopped("1", "read", note=_DROPPED_HEAD_FIRST)},
    ),
    Scenario(
        "dropped-head-forced",
        "The same head enqueued again with --force, and the queue merges it.",
        _dropped_head_forced,
        Row(
            merged("merged 0", "read defaults read defaults enqueue read×2 delete-ref"),
            merged("0 record=ran", "read defaults read defaults enqueue read×2 delete-ref"),
            merged("0", "read defaults enqueue read×2 delete-ref"),
            _NO_FORCE,
        ),
        after={
            DONE_WORK: _deleted(
                "merged 0", "read defaults read defaults enqueue read×2 branch based-on delete-ref"
            ),
            MERGE_PR: _deleted(
                "0 record=ran",
                "read defaults read defaults enqueue read×2 branch based-on delete-ref",
            ),
            RELEASE: _deleted(
                "0",
                "read defaults read defaults enqueue read×2 branch based-on delete-ref",
                note=_PLANNED,
            ),
        },
    ),
    # ---- the head moves ---------------------------------------------------------------
    Scenario(
        "head-moves-while-queued",
        "A push while the queue holds the PR: taken out of the queue.",
        _head_moves_while_queued,
        Row(
            stopped("head-moved 3", "read defaults read defaults enqueue read×3 dequeue read"),
            stopped("3", "read defaults read defaults enqueue read×3 dequeue read"),
            stopped("3", "read defaults enqueue read×3 dequeue read"),
            stopped("3 merge: stopped", "read defaults read defaults enqueue read×3 dequeue read"),
        ),
        after={
            DONE_WORK: stopped(
                "head-moved 3",
                "read defaults read defaults enqueue read×3 dequeue read×2",
                note=_OUT_ON_TWO_READINGS,
            ),
            MERGE_PR: stopped(
                "3 record=owed",
                "read defaults read defaults enqueue read×3 dequeue read×2",
                note=f"{_OUT_ON_TWO_READINGS}; {_OWED_ON_A_SENT_REQUEST}",
            ),
            RELEASE: stopped(
                "3",
                "read defaults read defaults enqueue read×3 dequeue read×2",
                note=f"{_OUT_ON_TWO_READINGS}; {_PLANNED}",
            ),
            LAND_WORK: stopped(
                "3 merge: stopped",
                "read defaults read defaults enqueue read×3 dequeue read×2",
                note=_OUT_ON_TWO_READINGS,
            ),
        },
    ),
    Scenario(
        "head-moves-dequeue-fails",
        "A push while the queue holds the PR, and taking it out fails.",
        _head_moves_dequeue_fails,
        Row(
            stopped("head-moved 3", "read defaults read defaults enqueue read×3 dequeue"),
            stopped("3", "read defaults read defaults enqueue read×3 dequeue"),
            stopped("3", "read defaults enqueue read×3 dequeue"),
            stopped("3 merge: stopped", "read defaults read defaults enqueue read×3 dequeue"),
        ),
        after={
            MERGE_PR: stopped(
                "3 record=owed",
                "read defaults read defaults enqueue read×3 dequeue",
                note=_OWED_ON_A_SENT_REQUEST,
            ),
            RELEASE: stopped(
                "3", "read defaults read defaults enqueue read×3 dequeue", note=_PLANNED
            ),
        },
    ),
    Scenario(
        "queued-at-another-head-on-a-rerun",
        "A re-run while the queue holds the PR, whose head moves after the caller read it.",
        _queued_at_another_head,
        Row(
            stopped("head-moved 3", "read defaults read defaults read×2 dequeue read"),
            stopped("3", "read defaults read defaults read×2 dequeue read"),
            stopped("3", "read defaults read×2 dequeue read"),
            stopped("3 merge: stopped", "read defaults read defaults read×2 dequeue read"),
        ),
        after={
            DONE_WORK: stopped(
                "head-moved 3",
                "read defaults read defaults read×2 dequeue read×2",
                note=_OUT_ON_TWO_READINGS,
            ),
            MERGE_PR: stopped(
                "3",
                "read defaults read defaults read×2 dequeue read×2",
                note=f"{_OUT_ON_TWO_READINGS}; this run sent no request — the PR was queued "
                "already — so nothing is owed",
            ),
            RELEASE: stopped("3", "read×3 dequeue read×2", note=_QUEUED_ELSEWHERE),
            LAND_WORK: stopped(
                "3 merge: stopped",
                "read defaults read defaults read×2 dequeue read×2",
                note=_OUT_ON_TWO_READINGS,
            ),
        },
    ),
    # ---- merged or closed by someone else -----------------------------------------------
    Scenario(
        "merged-before-the-run",
        "Someone else merged the PR directly, before the run.",
        _merged_before,
        Row(
            merged(
                "merged 0",
                "delete-ref",
                note="completes any merged PR that closes the issue",
            ),
            stopped(
                "1",
                "read",
                note="by design: a PR merged without a queue and owed nothing from this clone "
                "is refused",
            ),
            merged("0", "delete-ref"),
            merged("0 merge: #42 completed through its merged PR", "delete-ref"),
        ),
        after={
            DONE_WORK: _deleted("merged 0", "branch based-on delete-ref"),
            RELEASE: _deleted("0", "read branch based-on delete-ref", note=_MERGED_IN_THE_PLAN),
            LAND_WORK: _deleted(
                "0 merge: #42 completed through its merged PR", "branch based-on delete-ref"
            ),
        },
    ),
    Scenario(
        "merged-by-the-queue-before-the-run",
        "The queue merged the PR after an earlier run returned: what follows the merge is left.",
        _merged_by_the_queue_before,
        Row(
            merged("merged 0", "delete-ref"),
            merged("0 record=ran", "read delete-ref"),
            merged("0", "delete-ref"),
            merged("0 merge: #42 completed through its merged PR", "delete-ref"),
        ),
        after={
            DONE_WORK: _deleted("merged 0", "branch based-on delete-ref"),
            MERGE_PR: _deleted("0 record=ran", "read branch based-on delete-ref"),
            RELEASE: _deleted("0", "read branch based-on delete-ref", note=_MERGED_IN_THE_PLAN),
            LAND_WORK: _deleted(
                "0 merge: #42 completed through its merged PR", "branch based-on delete-ref"
            ),
        },
    ),
    Scenario(
        "merged-meanwhile",
        "Someone else merges the PR at the checked head after the caller found it open.",
        _merged_meanwhile,
        Row(
            merged("merged 0", "read×2 delete-ref"),
            merged("0 record=ran", "read×2 delete-ref"),
            merged("0", "read delete-ref"),
            merged("0 merge: merged", "read×2 delete-ref"),
        ),
        after={
            DONE_WORK: _deleted("merged 0", "read×2 branch based-on delete-ref"),
            MERGE_PR: _deleted("0 record=ran", "read×2 branch based-on delete-ref"),
            RELEASE: _deleted("0", "read branch based-on delete-ref"),
            LAND_WORK: _deleted("0 merge: merged", "read×2 branch based-on delete-ref"),
        },
    ),
    Scenario(
        "merged-meanwhile-at-another-head",
        "Someone else pushes and merges the PR after the caller found it open.",
        _merged_meanwhile_elsewhere,
        Row(
            merged("merged 0", "read×2 delete-ref", local="kept"),
            merged("0 record=ran", "read×2 delete-ref", local="kept"),
            merged("0", "read delete-ref", local="kept"),
            merged("0 merge: merged", "read×2 delete-ref", local="kept"),
        ),
        after={
            DONE_WORK: _deleted("merged 0", "read×2 branch based-on delete-ref", local="kept"),
            MERGE_PR: _deleted("0 record=ran", "read×2 branch based-on delete-ref", local="kept"),
            RELEASE: _deleted("0", "read branch based-on delete-ref", local="kept"),
            LAND_WORK: _deleted(
                "0 merge: merged", "read×2 branch based-on delete-ref", local="kept"
            ),
        },
    ),
    Scenario(
        "two-landings-race-on-a-direct-base",
        "Another landing merges the PR just before this one's merge request.",
        _race_on_a_direct_base,
        Row(
            merged("merged 0", "read×2 merge read delete-ref"),
            merged("0 record=ran", "read×2 merge read delete-ref"),
            merged("0", "read merge read delete-ref"),
            merged("0 merge: merged", "read×2 merge read delete-ref"),
        ),
        after={
            DONE_WORK: _deleted("merged 0", "read×2 merge read branch based-on delete-ref"),
            MERGE_PR: _deleted("0 record=ran", "read×2 merge read branch based-on delete-ref"),
            RELEASE: _deleted("0", "read×2 merge read branch based-on delete-ref", note=_PLANNED),
            LAND_WORK: _deleted("0 merge: merged", "read×2 merge read branch based-on delete-ref"),
        },
    ),
    Scenario(
        "two-landings-race-on-a-queue",
        "Another landing enqueues the PR just before this one's enqueue, which gh refuses.",
        _race_on_a_queue,
        Row(
            stopped(
                "refused 3 retry",
                "read defaults read defaults enqueue",
                note="taken for a failed request while the PR sits in the queue",
            ),
            stopped("3", "read defaults read defaults enqueue"),
            stopped("1", "read defaults enqueue"),
            stopped(
                "7 merge: not merged",
                "read defaults read defaults enqueue",
                note="the PR's state it reads again does not show the queue",
            ),
        ),
        after={RELEASE: stopped("1", "read defaults read defaults enqueue", note=_PLANNED)},
    ),
    Scenario(
        "closed-before-the-run",
        "The PR was closed without merging before the run.",
        _closed_before,
        Row(
            stopped("refused 2", note="no open PR for the branch"),
            stopped("1"),
            stopped("0", note="by design: nothing to merge"),
            stopped("1 merge: refused"),
        ),
        after={RELEASE: stopped("0", "read", note=_CLOSED_IN_THE_PLAN)},
    ),
    Scenario(
        "closed-meanwhile",
        "The PR is closed after the caller found it open.",
        _closed_meanwhile,
        Row(
            stopped("refused 3 retry", "read×2 merge", note="gh's refusal of the merge"),
            stopped("3", "read×2 merge"),
            stopped("1", "read merge"),
            stopped("7 merge: not merged", "read×2 merge"),
        ),
        after={RELEASE: stopped("0", "read", note=_CLOSED_MEANWHILE)},
    ),
    # ---- requests and answers -------------------------------------------------------------
    Scenario(
        "request-unanswered-then-merged",
        "The merge is made and its answer never comes back; the PR reads merged.",
        _unanswered_then_merged,
        Row(
            merged("merged 0", "read×2 merge read delete-ref"),
            merged("0 record=ran", "read×2 merge read delete-ref"),
            stopped("hangs", "read merge", note=_HANGS),
            merged("0 merge: merged", "read×2 merge read delete-ref"),
        ),
        after={
            DONE_WORK: _deleted(
                "merged 0", "read×2 merge read×2 branch based-on delete-ref", note=_SETTLED_MADE
            ),
            MERGE_PR: _deleted(
                "0 record=ran", "read×2 merge read×2 branch based-on delete-ref", note=_SETTLED_MADE
            ),
            RELEASE: _deleted(
                "0",
                "read×2 merge read×2 branch based-on delete-ref",
                note=f"{_SETTLED_MADE}; {_PLANNED}",
            ),
            LAND_WORK: _deleted(
                "0 merge: merged",
                "read×2 merge read×2 branch based-on delete-ref",
                note=_SETTLED_MADE,
            ),
        },
    ),
    Scenario(
        "request-unanswered-then-queued",
        "The enqueue is made and its answer never comes back; the PR reads queued.",
        _unanswered_then_queued,
        Row(
            merged("merged 0", "read defaults read defaults enqueue read×2 delete-ref"),
            merged("0 record=ran", "read defaults read defaults enqueue read×2 delete-ref"),
            stopped("hangs", "read defaults enqueue", note=_HANGS),
            merged("0 merge: merged", "read defaults read defaults enqueue read×2 delete-ref"),
        ),
        after={
            DONE_WORK: _deleted(
                "merged 0", "read defaults read defaults enqueue read×2 branch based-on delete-ref"
            ),
            MERGE_PR: _deleted(
                "0 record=ran",
                "read defaults read defaults enqueue read×2 branch based-on delete-ref",
            ),
            RELEASE: _deleted(
                "0",
                "read defaults read defaults enqueue read×2 branch based-on delete-ref",
                note=f"{_SETTLED_MADE}; {_PLANNED}",
            ),
            LAND_WORK: _deleted(
                "0 merge: merged",
                "read defaults read defaults enqueue read×2 branch based-on delete-ref",
            ),
        },
    ),
    Scenario(
        "request-unanswered-then-neither",
        "The merge never reaches the service and nothing comes back.",
        _unanswered_then_neither,
        Row(
            stopped("refused 3 retry", "read×2 merge read", note=_ONE_READING),
            stopped("3", "read×2 merge read", note=_ONE_READING),
            stopped("hangs", "read merge", note=_HANGS),
            stopped("7 merge: not merged", "read×2 merge read", note=_ONE_READING),
        ),
        after={
            DONE_WORK: stopped("refused 3 retry", "read×2 merge read×2", note=_SETTLED_NOT_MADE),
            MERGE_PR: stopped(
                "3 record=owed",
                "read×2 merge read×2",
                note=f"{_SETTLED_NOT_MADE}; {_OWED_ON_A_SENT_REQUEST}",
            ),
            RELEASE: stopped("1", "read×2 merge read×2", note=f"{_SETTLED_NOT_MADE}; {_PLANNED}"),
            LAND_WORK: stopped(
                "7 merge: not merged", "read×2 merge read×2", note=_SETTLED_NOT_MADE
            ),
        },
    ),
    Scenario(
        "request-unanswered-then-merged-late",
        "The merge never answers, and two readings do not see it made; the service applies it "
        "just after them, and the caller is run again.",
        _merged_after_the_readings,
        Row(
            _deleted(
                "refused 3 retry → merged 0",
                "read×2 merge read×2 branch based-on delete-ref",
                note=_MERGED_LATE,
            ),
            _deleted(
                "3 record=owed → 0 record=ran",
                "read×2 merge read×3 branch based-on delete-ref",
                note=_MERGED_LATE,
            ),
            _deleted("1 → 0", "read merge read×2 branch based-on delete-ref", note=_MERGED_LATE),
            _deleted(
                "7 merge: merged meanwhile → 0 merge: #42 completed through its merged PR",
                "read×2 merge read×2 branch based-on delete-ref",
                note=f"{_MERGED_LATE}; land-work's own reading after done-work's end already "
                "finds it merged, and asks for the re-run",
            ),
        ),
        after={
            RELEASE: _deleted(
                "1 → 0",
                "read×2 merge read×3 branch based-on delete-ref",
                note=f"{_MERGED_LATE}; {_PLANNED}; the re-run's plan reads it merged",
            )
        },
    ),
    Scenario(
        "request-unanswered-then-unreadable",
        "The merge is made and its answer never comes back; GitHub cannot be read since.",
        _unanswered_then_unreadable,
        Row(
            stopped("unconfirmed 4", "read×2 merge read", note=_SETTLED_UNCONFIRMED),
            stopped("4 record=owed", "read×2 merge read", note=_SETTLED_UNCONFIRMED),
            stopped("hangs", "read merge", note=_HANGS),
            stopped("4 merge: unconfirmed", "read×2 merge read×2", note=_SETTLED_UNCONFIRMED),
        ),
        after={
            RELEASE: stopped("4", "read×2 merge read", note=f"{_RELEASE_UNCONFIRMED}; {_PLANNED}")
        },
    ),
    Scenario(
        "enqueue-unanswered-then-unreadable",
        "The enqueue is made and its answer never comes back; GitHub cannot be read since.",
        _enqueue_unanswered_then_unreadable,
        Row(
            stopped(
                "unconfirmed 4",
                "read defaults read defaults enqueue read",
                note=_SETTLED_UNCONFIRMED,
            ),
            stopped(
                "4 record=owed",
                "read defaults read defaults enqueue read",
                note=_SETTLED_UNCONFIRMED,
            ),
            stopped("hangs", "read defaults enqueue", note=_HANGS),
            stopped(
                "4 merge: unconfirmed",
                "read defaults read defaults enqueue read×2",
                note=_SETTLED_UNCONFIRMED,
            ),
        ),
        after={
            RELEASE: stopped(
                "4",
                "read defaults read defaults enqueue read",
                note=f"{_RELEASE_UNCONFIRMED}; {_PLANNED}",
            ),
        },
    ),
    Scenario(
        "request-made-then-gh-failed",
        "The merge is made, then gh exits with a 502.",
        _made_then_gh_failed,
        Row(
            stopped("refused 3 retry", "read×2 merge", note=_MADE_THEN_FAILED),
            stopped("3", "read×2 merge", note=_MADE_THEN_FAILED),
            stopped("1", "read merge", note=_MADE_THEN_FAILED),
            stopped(
                "7 merge: merged meanwhile",
                "read×2 merge",
                note="it reads the PR merged, and asks for a re-run",
            ),
        ),
        after={
            DONE_WORK: _deleted(
                "merged 0",
                "read×2 merge read×2 branch based-on delete-ref",
                note=_LOST_ANSWER_SETTLED,
            ),
            MERGE_PR: _deleted(
                "0 record=ran",
                "read×2 merge read×2 branch based-on delete-ref",
                note=_LOST_ANSWER_SETTLED,
            ),
            RELEASE: _deleted(
                "0",
                "read×2 merge read×2 branch based-on delete-ref",
                note=f"{_LOST_ANSWER_SETTLED}; {_PLANNED}",
            ),
            LAND_WORK: _deleted(
                "0 merge: merged",
                "read×2 merge read×2 branch based-on delete-ref",
                note=_LOST_ANSWER_SETTLED,
            ),
        },
    ),
    Scenario(
        "killed-mid-request-then-merged",
        "The landing's `pkit` is killed while gh waits on the merge, which the service made.",
        _killed_mid_merge_made,
        Row(
            _deleted(
                "merged 0",
                "read×2 merge read branch based-on delete-ref",
                note="no document: pm reads the PR merged, and that is the merge",
            ),
            _deleted("0 record=ran", "read×2 merge read branch based-on delete-ref"),
            _NO_ONE_LEFT,
            _deleted("0 merge: merged", "read×2 merge read branch based-on delete-ref"),
        ),
    ),
    Scenario(
        "killed-mid-request-then-neither",
        "The landing's `pkit` is killed while gh waits on the merge, which the service never got.",
        _killed_mid_merge_unmade,
        Row(
            stopped("refused 3 retry", "read×2 merge read", note=_ONE_READING),
            stopped("3", "read×2 merge read", note=_ONE_READING),
            _NO_ONE_LEFT,
            stopped("7 merge: not merged", "read×2 merge read", note=_ONE_READING),
        ),
        after={
            DONE_WORK: stopped("unconfirmed 4", "read×2 merge read", note=_KILLED_ONE_READING),
            MERGE_PR: stopped("4 record=owed", "read×2 merge read", note=_KILLED_ONE_READING),
            LAND_WORK: stopped(
                "4 merge: unconfirmed",
                "read×2 merge read×2",
                note=f"{_KILLED_ONE_READING}; land-work's own reading since keeps it unconfirmed",
            ),
        },
    ),
    Scenario(
        "read-fails-after-a-direct-merge",
        "gh accepts the direct merge, and every reading since fails.",
        _read_fails_after_a_merge,
        Row(
            stopped("unconfirmed 4", "read×2 merge read×2"),
            stopped("4 record=owed", "read×2 merge read×2"),
            stopped("4", "read merge read×2"),
            stopped("4 merge: unconfirmed", "read×2 merge read×3"),
        ),
        after={RELEASE: stopped("4", "read×2 merge read×2", note=_PLANNED)},
    ),
    Scenario(
        "read-fails-after-an-enqueue",
        "gh accepts the enqueue, and every reading since fails.",
        _read_fails_after_an_enqueue,
        Row(
            stopped("queued 4", "read defaults read defaults enqueue read"),
            stopped("4 record=owed", "read defaults read defaults enqueue read"),
            stopped("4", "read defaults enqueue read"),
            stopped("4 merge: queued", "read defaults read defaults enqueue read×2"),
        ),
        after={RELEASE: stopped("4", "read defaults read defaults enqueue read", note=_PLANNED)},
    ),
    Scenario(
        "read-fails-once-after-a-direct-merge",
        "gh accepts the direct merge, the next reading fails, and the one after reads it merged.",
        _read_fails_once_after_a_merge,
        Row(
            _deleted(
                "merged 0",
                "read×2 merge read×2 branch based-on delete-ref",
                note="one failed reading after an accepted merge is read again, never taken "
                "for a merge or for none",
            ),
            _deleted("0 record=ran", "read×2 merge read×2 branch based-on delete-ref"),
            _deleted("0", "read merge read×2 branch based-on delete-ref"),
            _deleted("0 merge: merged", "read×2 merge read×2 branch based-on delete-ref"),
        ),
        after={
            RELEASE: _deleted("0", "read×2 merge read×2 branch based-on delete-ref", note=_PLANNED)
        },
    ),
    Scenario(
        "rate-limit-mid-wait",
        "One reading of the wait is refused for the rate limit.",
        _rate_limit_mid_wait,
        Row(
            stopped(
                "queued 4",
                "read defaults read defaults enqueue read×2",
                note="one refused reading ends the wait, in both copies",
            ),
            stopped("4 record=owed", "read defaults read defaults enqueue read×2"),
            stopped("4", "read defaults enqueue read×2"),
            stopped("4 merge: queued", "read defaults read defaults enqueue read×3"),
        ),
        after={RELEASE: stopped("4", "read defaults read defaults enqueue read×2", note=_PLANNED)},
    ),
    Scenario(
        "auto-merge-not-allowed",
        "The repository does not allow auto-merge, so gh refuses the enqueue.",
        _auto_merge_not_allowed,
        Row(
            stopped(
                "refused 3 retry",
                "read defaults read defaults enqueue",
                note="said to be worth a re-run, though a setting must change",
            ),
            stopped("3", "read defaults read defaults enqueue"),
            stopped("1", "read defaults enqueue"),
            stopped("7 merge: not merged", "read defaults read defaults enqueue"),
        ),
        after={RELEASE: stopped("1", "read defaults read defaults enqueue", note=_PLANNED)},
    ),
    Scenario(
        "killed-after-requesting",
        "The landing process is killed after it wrote that it sends a request.",
        _not_drivable,
        Row(_NO_REQUESTING, _NO_REQUESTING, _NO_REQUESTING, _NO_REQUESTING),
        after={RELEASE: _REQUESTING_ON_LAND},
    ),
    # ---- the head branch's deletion -------------------------------------------------------
    Scenario(
        "remote-tip-equals",
        "The remote head branch is at the head the PR merged at.",
        _direct,
        Row(
            merged("merged 0", "read×2 merge read delete-ref"),
            merged("0 record=ran", "read×2 merge read delete-ref"),
            merged("0", "read merge read delete-ref"),
            merged("0 merge: merged", "read×2 merge read delete-ref"),
        ),
        after={
            DONE_WORK: _deleted("merged 0", "read×2 merge read branch based-on delete-ref"),
            MERGE_PR: _deleted("0 record=ran", "read×2 merge read branch based-on delete-ref"),
            RELEASE: _deleted("0", "read×2 merge read branch based-on delete-ref", note=_PLANNED),
            LAND_WORK: _deleted("0 merge: merged", "read×2 merge read branch based-on delete-ref"),
        },
    ),
    Scenario(
        "remote-tip-moved",
        "A push to the head branch after the merge.",
        _tip_moved,
        Row(
            merged(
                "merged 0",
                "read×2 merge read delete-ref",
                remote="deleted, tip sha-later moved",
                note=_TIP_UNCHECKED,
            ),
            merged(
                "0 record=ran",
                "read×2 merge read delete-ref",
                remote="deleted, tip sha-later moved",
                note=_TIP_UNCHECKED,
            ),
            merged(
                "0",
                "read merge read delete-ref",
                remote="deleted, tip sha-later moved",
                note=_TIP_UNCHECKED,
            ),
            merged(
                "0 merge: merged",
                "read×2 merge read delete-ref",
                remote="deleted, tip sha-later moved",
                note=_TIP_UNCHECKED,
            ),
        ),
        after={
            DONE_WORK: merged(
                "merged 0",
                "read×2 merge read branch",
                remote="none",
                local="kept",
                deletion="kept tip-moved",
                note=_TIP_KEPT,
            ),
            MERGE_PR: merged(
                "0 record=ran",
                "read×2 merge read branch",
                remote="none",
                local="kept",
                deletion="kept tip-moved",
                note=_TIP_KEPT,
            ),
            RELEASE: merged(
                "0",
                "read×2 merge read branch",
                remote="none",
                local="kept",
                deletion="kept tip-moved",
                note=f"{_TIP_KEPT}; {_PLANNED}",
            ),
            LAND_WORK: merged(
                "0 merge: merged",
                "read×2 merge read branch",
                remote="none",
                local="kept",
                deletion="kept tip-moved",
                note=_TIP_KEPT,
            ),
        },
    ),
    Scenario(
        "remote-tip-gone",
        "The repository deleted the head branch as the PR merged.",
        _tip_gone,
        Row(
            merged("merged 0", "read×2 merge read delete-ref", remote="gone"),
            merged("0 record=ran", "read×2 merge read delete-ref", remote="gone"),
            merged("0", "read merge read delete-ref", remote="gone"),
            merged("0 merge: merged", "read×2 merge read delete-ref", remote="gone"),
        ),
        after={
            DONE_WORK: merged(
                "merged 0",
                "read×2 merge read branch",
                remote="none",
                deletion="gone",
                note=_FOUND_GONE,
            ),
            MERGE_PR: merged(
                "0 record=ran",
                "read×2 merge read branch",
                remote="none",
                deletion="gone",
                note=_FOUND_GONE,
            ),
            RELEASE: merged(
                "0",
                "read×2 merge read branch",
                remote="none",
                deletion="gone",
                note=f"{_FOUND_GONE}; {_PLANNED}",
            ),
            LAND_WORK: merged(
                "0 merge: merged",
                "read×2 merge read branch",
                remote="none",
                deletion="gone",
                note=_FOUND_GONE,
            ),
        },
    ),
    Scenario(
        "fork",
        "The PR's head lives in a fork.",
        _fork,
        Row(
            merged("merged 0", "read×2 merge read", remote="none", local="kept"),
            merged("0 record=ran", "read×2 merge read", remote="none", local="kept"),
            merged("0", "read merge read", remote="none", local="kept"),
            merged("0 merge: merged", "read×2 merge read", remote="none", local="kept"),
        ),
        after={
            DONE_WORK: merged(
                "merged 0",
                "read×2 merge read branch",
                remote="none",
                local="kept",
                deletion="refused cross-repository",
                note=_FORK_REFUSED,
            ),
            MERGE_PR: merged(
                "0 record=ran",
                "read×2 merge read branch",
                remote="none",
                local="kept",
                deletion="refused cross-repository",
                note=_FORK_REFUSED,
            ),
            RELEASE: merged(
                "0",
                "read×2 merge read branch",
                remote="none",
                local="kept",
                deletion="refused cross-repository",
                note=f"{_FORK_REFUSED}; {_PLANNED}",
            ),
            LAND_WORK: merged(
                "0 merge: merged",
                "read×2 merge read branch",
                remote="none",
                local="kept",
                deletion="refused cross-repository",
                note=_FORK_REFUSED,
            ),
        },
    ),
    Scenario(
        "branch-protected",
        "The head branch is protected from deletion.",
        _protected,
        Row(
            merged("merged 0", "read×2 merge read delete-ref", remote="refused, protected"),
            merged("0 record=ran", "read×2 merge read delete-ref", remote="refused, protected"),
            merged("0", "read merge read delete-ref", remote="refused, protected"),
            merged("0 merge: merged", "read×2 merge read delete-ref", remote="refused, protected"),
        ),
        after={
            DONE_WORK: merged(
                "merged 0",
                "read×2 merge read branch based-on delete-ref branch",
                remote="refused, protected",
                local="kept",
                deletion="kept deletion-refused",
                note=_PROTECTED_KEPT,
            ),
            MERGE_PR: merged(
                "0 record=ran",
                "read×2 merge read branch based-on delete-ref branch",
                remote="refused, protected",
                local="kept",
                deletion="kept deletion-refused",
                note=_PROTECTED_KEPT,
            ),
            RELEASE: merged(
                "0",
                "read×2 merge read branch based-on delete-ref branch",
                remote="refused, protected",
                local="kept",
                deletion="kept deletion-refused",
                note=f"{_PROTECTED_KEPT}; {_PLANNED}",
            ),
            LAND_WORK: merged(
                "0 merge: merged",
                "read×2 merge read branch based-on delete-ref branch",
                remote="refused, protected",
                local="kept",
                deletion="kept deletion-refused",
                note=_PROTECTED_KEPT,
            ),
        },
    ),
    Scenario(
        "branch-used-by-another-open-pr",
        "Another open PR, #501, has the same head branch.",
        _another_open_pr,
        Row(
            merged(
                "merged 0",
                "read×2 merge read delete-ref",
                remote="deleted, closed #501",
                note=_TIP_UNCHECKED,
            ),
            merged(
                "0 record=ran",
                "read×2 merge read delete-ref",
                remote="deleted, closed #501",
                note=_TIP_UNCHECKED,
            ),
            merged(
                "0",
                "read merge read delete-ref",
                remote="deleted, closed #501",
                note=_TIP_UNCHECKED,
            ),
            merged(
                "0 merge: merged",
                "read×2 merge read delete-ref",
                remote="deleted, closed #501",
                note=_TIP_UNCHECKED,
            ),
        ),
        after={
            DONE_WORK: merged(
                "merged 0",
                "read×2 merge read branch based-on",
                remote="none",
                local="kept",
                deletion="kept open-pull-request",
                note=_IN_USE_KEPT,
            ),
            MERGE_PR: merged(
                "0 record=ran",
                "read×2 merge read branch based-on",
                remote="none",
                local="kept",
                deletion="kept open-pull-request",
                note=_IN_USE_KEPT,
            ),
            RELEASE: merged(
                "0",
                "read×2 merge read branch based-on",
                remote="none",
                local="kept",
                deletion="kept open-pull-request",
                note=f"{_IN_USE_KEPT}; {_PLANNED}",
            ),
            LAND_WORK: merged(
                "0 merge: merged",
                "read×2 merge read branch based-on",
                remote="none",
                local="kept",
                deletion="kept open-pull-request",
                note=_IN_USE_KEPT,
            ),
        },
    ),
    Scenario(
        "branch-based-on-by-another-open-pr",
        "Another open PR, #503, is based on the head branch: stacked on it.",
        _another_open_pr_based_on_it,
        Row(
            merged("merged 0", "read×2 merge read delete-ref", note=_BASE_UNCHECKED),
            merged("0 record=ran", "read×2 merge read delete-ref", note=_BASE_UNCHECKED),
            merged("0", "read merge read delete-ref", note=_BASE_UNCHECKED),
            merged("0 merge: merged", "read×2 merge read delete-ref", note=_BASE_UNCHECKED),
        ),
        after={
            DONE_WORK: merged(
                "merged 0",
                "read×2 merge read branch based-on",
                remote="none",
                local="kept",
                deletion="kept open-pull-request",
                note=_BASE_KEPT,
            ),
            MERGE_PR: merged(
                "0 record=ran",
                "read×2 merge read branch based-on",
                remote="none",
                local="kept",
                deletion="kept open-pull-request",
                note=_BASE_KEPT,
            ),
            RELEASE: merged(
                "0",
                "read×2 merge read branch based-on",
                remote="none",
                local="kept",
                deletion="kept open-pull-request",
                note=f"{_BASE_KEPT}; {_PLANNED}",
            ),
            LAND_WORK: merged(
                "0 merge: merged",
                "read×2 merge read branch based-on",
                remote="none",
                local="kept",
                deletion="kept open-pull-request",
                note=_BASE_KEPT,
            ),
        },
    ),
    Scenario(
        "reused-branch-name",
        "Completing a PR the queue merged, from a clone without its branch, whose name a new "
        "PR, #502, now uses.",
        _reused_name,
        Row(
            merged(
                "merged 0",
                "delete-ref",
                remote="deleted, tip sha-new moved, closed #502",
                local="absent",
                note=_TIP_UNCHECKED,
            ),
            merged(
                "0 record=ran",
                "read delete-ref",
                remote="deleted, tip sha-new moved, closed #502",
                local="absent",
                note=_TIP_UNCHECKED,
            ),
            merged(
                "0",
                "delete-ref",
                remote="deleted, tip sha-new moved, closed #502",
                local="absent",
                note=_TIP_UNCHECKED,
            ),
            merged(
                "0 merge: #42 completed through its merged PR",
                "delete-ref",
                remote="deleted, tip sha-new moved, closed #502",
                local="absent",
                note=_TIP_UNCHECKED,
            ),
        ),
        after={
            DONE_WORK: merged(
                "merged 0",
                "branch",
                remote="none",
                local="absent",
                deletion="kept tip-moved",
                note=_REUSED_KEPT,
            ),
            MERGE_PR: merged(
                "0 record=ran",
                "read branch",
                remote="none",
                local="absent",
                deletion="kept tip-moved",
                note=_REUSED_KEPT,
            ),
            RELEASE: merged(
                "0",
                "read branch",
                remote="none",
                local="absent",
                deletion="kept tip-moved",
                note=f"{_REUSED_KEPT}; {_MERGED_IN_THE_PLAN}",
            ),
            LAND_WORK: merged(
                "0 merge: #42 completed through its merged PR",
                "branch",
                remote="none",
                local="absent",
                deletion="kept tip-moved",
                note=_REUSED_KEPT,
            ),
        },
    ),
    # ---- the session ---------------------------------------------------------------------
    Scenario(
        "foreign-repository-refused",
        "A session rooted in another repository, with no terminal and no flag.",
        _foreign_refused,
        Row(
            stopped("refused 1"),
            stopped("1"),
            merged("0", "read merge read delete-ref", note=_UNGUARDED),
            stopped("2", note="its own guard refuses before any step"),
        ),
        after={
            RELEASE: stopped("1", guard="refused", note=_REFUSED_AT_ENTRY),
        },
    ),
    Scenario(
        "foreign-repository-flagged",
        "A session rooted in another repository, and --allow-foreign-repo.",
        _foreign_flagged,
        Row(
            merged("merged 0", "read×2 merge read delete-ref"),
            merged("0 record=ran", "read×2 merge read delete-ref"),
            _NO_FOREIGN_FLAG,
            merged("0 merge: merged", "read×2 merge read delete-ref"),
        ),
        after={
            DONE_WORK: _deleted(
                "merged 0",
                "read×2 merge read branch based-on delete-ref",
                guard="flag×2",
                note=f"{_FLAG_PASSED_ON}; {_SIBLINGS_STUBBED}",
            ),
            MERGE_PR: _deleted(
                "0 record=ran",
                "read×2 merge read branch based-on delete-ref",
                guard="flag×2",
                note=_FLAG_PASSED_ON,
            ),
            RELEASE: _deleted(
                "0",
                "read×2 merge read branch based-on delete-ref",
                guard="flag",
                note="it takes --allow-foreign-repo now: its guard at the entry passes by it, "
                "for the merge and the branch's deletion alike; " + _PLANNED,
            ),
            LAND_WORK: _deleted(
                "0 merge: merged",
                "read×2 merge read branch based-on delete-ref",
                guard="flag×2",
                note="its flag reaches done-work, which passes it on to the backbone's guard; "
                + _SIBLINGS_STUBBED,
            ),
        },
    ),
    Scenario(
        "foreign-repository-confirmed-at-a-terminal",
        "A session rooted in another repository; the operator confirms at a terminal.",
        _foreign_at_a_terminal,
        Row(
            merged("merged 0", "read×2 merge read delete-ref", asked=1),
            merged("0 record=ran", "read×2 merge read delete-ref", asked=1),
            merged("0", "read merge read delete-ref", note=_UNGUARDED),
            merged(
                "0 merge: merged",
                "read×2 merge read delete-ref",
                asked=2,
                note="asked twice: by land-work's guard, then by done-work's",
            ),
        ),
        after={
            DONE_WORK: _deleted(
                "merged 0",
                "read×2 merge read branch based-on delete-ref",
                asked=1,
                guard="flag×2",
                note=f"{_YES_PASSED_ON}; {_SIBLINGS_STUBBED}",
            ),
            MERGE_PR: _deleted(
                "0 record=ran",
                "read×2 merge read branch based-on delete-ref",
                asked=1,
                guard="flag×2",
                note=_YES_PASSED_ON,
            ),
            RELEASE: _deleted(
                "0",
                "read×2 merge read branch based-on delete-ref",
                asked=1,
                guard="terminal",
                note=f"its guard asks once, at the entry, before it reads the PR; {_PLANNED}",
            ),
            LAND_WORK: _deleted(
                "0 merge: merged",
                "read×2 merge read branch based-on delete-ref",
                asked=1,
                guard="flag×2",
                note="asked once: land-work's yes is passed on to done-work, whose guard and "
                f"the backbone's pass by it; {_SIBLINGS_STUBBED}",
            ),
        },
    ),
    Scenario(
        "foreign-repository-declined-at-a-terminal",
        "A session rooted in another repository; the operator declines at a terminal.",
        _foreign_declined_at_a_terminal,
        Row(
            stopped("refused 1", asked=1),
            stopped("1", asked=1),
            merged("0", "read merge read delete-ref", note=_UNGUARDED),
            stopped("2", asked=1, note="its own guard asks, and refuses before any step"),
        ),
        after={
            RELEASE: stopped("1", asked=1, guard="refused", note=_REFUSED_AT_ENTRY),
        },
    ),
    Scenario(
        "the-two-comparisons-disagree",
        "A session rooted in another repository, which project-management's copy of the "
        "comparison takes for the session's own and the backbone's does not.",
        _comparisons_disagree,
        Row(
            merged("merged 0", "read×2 merge read delete-ref", note=_UNGUARDED_REQUEST),
            merged("0 record=ran", "read×2 merge read delete-ref", note=_UNGUARDED_REQUEST),
            NotToday("holds one comparison: its guard is the backbone's alone"),
            merged("0 merge: merged", "read×2 merge read delete-ref", note=_UNGUARDED_REQUEST),
        ),
        after={
            DONE_WORK: stopped("refused 1", "read×2", guard="refused", note=_FAILS_CLOSED),
            MERGE_PR: stopped("1", "read×2", guard="refused", note=_FAILS_CLOSED),
            LAND_WORK: stopped("1 merge: refused", "read×2", guard="refused", note=_FAILS_CLOSED),
        },
    ),
    Scenario(
        "the-two-comparisons-disagree-with-the-flag",
        "As the row above, and the operator gives --allow-foreign-repo.",
        _comparisons_disagree_flagged,
        Row(
            merged("merged 0", "read×2 merge read delete-ref", note=_UNGUARDED_REQUEST),
            merged("0 record=ran", "read×2 merge read delete-ref", note=_UNGUARDED_REQUEST),
            NotToday("holds one comparison: its guard is the backbone's alone"),
            merged("0 merge: merged", "read×2 merge read delete-ref", note=_UNGUARDED_REQUEST),
        ),
        after={
            DONE_WORK: _deleted(
                "merged 0",
                "read×2 merge read branch based-on delete-ref",
                guard="flag×2",
                note=f"{_FLAG_OVERRIDES}; {_SIBLINGS_STUBBED}",
            ),
            MERGE_PR: _deleted(
                "0 record=ran",
                "read×2 merge read branch based-on delete-ref",
                guard="flag×2",
                note=_FLAG_OVERRIDES,
            ),
            LAND_WORK: _deleted(
                "0 merge: merged",
                "read×2 merge read branch based-on delete-ref",
                guard="flag×2",
                note=f"{_FLAG_OVERRIDES}; {_SIBLINGS_STUBBED}",
            ),
        },
    ),
    Scenario(
        "the-comparison-faults",
        "git does not answer the guards' questions about the session's anchor and the target.",
        _comparison_faults,
        Row(
            merged("merged 0", "read×2 merge read delete-ref"),
            merged("0 record=ran", "read×2 merge read delete-ref"),
            merged("0", "read merge read delete-ref", note=_UNGUARDED),
            merged("0 merge: merged", "read×2 merge read delete-ref"),
        ),
        after={
            DONE_WORK: _deleted(
                "merged 0",
                "read×2 merge read branch based-on delete-ref",
                guard="undetermined×2",
                note=_FAULT,
            ),
            MERGE_PR: _deleted(
                "0 record=ran",
                "read×2 merge read branch based-on delete-ref",
                guard="undetermined×2",
                note=_FAULT,
            ),
            RELEASE: _deleted(
                "0",
                "read×2 merge read branch based-on delete-ref",
                guard="undetermined",
                note=f"{_FAULT}; {_PLANNED}",
            ),
            LAND_WORK: _deleted(
                "0 merge: merged",
                "read×2 merge read branch based-on delete-ref",
                guard="undetermined×2",
                note=_FAULT,
            ),
        },
    ),
    Scenario(
        "outside-any-session",
        "No session anchor, as in a pipeline: the guard has nothing to compare.",
        _no_anchor,
        Row(
            merged("merged 0", "read×2 merge read delete-ref"),
            merged("0 record=ran", "read×2 merge read delete-ref"),
            merged("0", "read merge read delete-ref"),
            merged("0 merge: merged", "read×2 merge read delete-ref"),
        ),
        after={
            DONE_WORK: _deleted(
                "merged 0",
                "read×2 merge read branch based-on delete-ref",
                guard="undetermined×2",
                note=_NO_FIRE,
            ),
            MERGE_PR: _deleted(
                "0 record=ran",
                "read×2 merge read branch based-on delete-ref",
                guard="undetermined×2",
                note=_NO_FIRE,
            ),
            RELEASE: _deleted(
                "0",
                "read×2 merge read branch based-on delete-ref",
                guard="undetermined",
                note=f"{_NO_FIRE}; {_PLANNED}",
            ),
            LAND_WORK: _deleted(
                "0 merge: merged",
                "read×2 merge read branch based-on delete-ref",
                guard="undetermined×2",
                note=_NO_FIRE,
            ),
        },
    ),
    # ---- what project-management reads of the backbone ------------------------------------
    Scenario(
        "backbone-without-the-noun",
        "The backbone predates `pkit pull-request` — today's form of a `pkit` without `land`.",
        _backbone_without_the_noun,
        Row(
            stopped("unreadable 2", note="the backbone's 'no such command', named"),
            stopped("3"),
            _NO_NOUN,
            stopped("2 merge: stopped"),
        ),
    ),
    Scenario(
        "wait-ends-in-an-unknown-way",
        "The wait's end document names an end project-management does not know.",
        _unknown_end,
        Row(
            stopped(
                "queued 4",
                "read defaults read defaults enqueue read×3",
                note="an unknown end is no answer: reported queued, though the queue merged it",
            ),
            stopped("4 record=owed", "read defaults read defaults enqueue read×3"),
            _NO_DOCUMENTS,
            stopped(
                "7 merge: merged meanwhile",
                "read defaults read defaults enqueue read×4",
                note="it reads the PR merged, and asks for a re-run",
            ),
        ),
    ),
    Scenario(
        "reading-without-a-deciding-key",
        "The backbone's reading lacks `queued`.",
        _missing_key,
        Row(
            stopped("unreadable 2", "read"),
            stopped("3", "read"),
            _NO_DOCUMENTS,
            stopped("2 merge: stopped", "read"),
        ),
    ),
)


# ---- running a caller ---------------------------------------------------------------


@dataclass(frozen=True)
class _Scripts:
    done_work: ModuleType
    merge_pr: ModuleType
    land_work: ModuleType


def _load(script: str, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def scripts() -> Iterator[_Scripts]:
    sys.path.insert(0, str(SCRIPTS))
    yield _Scripts(
        done_work=_load("done-work.py", "pm_landing_scenarios_done_work"),
        merge_pr=_load("merge-pr.py", "pm_landing_scenarios_merge_pr"),
        land_work=_load("land-work.py", "pm_landing_scenarios_land_work"),
    )
    sys.path.remove(str(SCRIPTS))


#: The capability's configuration: human review, so the approval gate is the
#: one reviewer seam, and it is stubbed.
_CONFIG: dict[str, Any] = {"review": {"mode": "human"}}

# A backbone older than `pkit pull-request`, in the words click answers with.
_PKIT_WITHOUT_THE_NOUN = """#!/bin/sh
echo "Usage: pkit [OPTIONS] COMMAND [ARGS]..." >&2
echo "Error: No such command 'pull-request'." >&2
exit 2
"""

# The lines land-work prints for its steps.
_STEPS = ("head", "ci", "review", "merge")


@dataclass
class _Run:
    """What the stubs saw during one caller's run."""

    moves: list[str] = field(default_factory=list)
    hooks: list[str] = field(default_factory=list)


class _Allowed:
    allowed = True
    refusal_message = None


def _stub_gates(monkeypatch: pytest.MonkeyPatch, module: ModuleType, cap: Path) -> None:
    """The gates a pm verb runs before its own, stubbed as the verbs' tests stub them."""
    monkeypatch.setattr(module, "resolve_capability_root", lambda arg: cap)
    monkeypatch.setattr(module, "load_adopter_config", lambda root: dict(_CONFIG))
    monkeypatch.setattr(module, "resolve_invoker_identity", lambda config=None: "octocat")
    monkeypatch.setattr(module, "check_membership", lambda members, invoker: _Allowed())


def _stub_done_work(monkeypatch: pytest.MonkeyPatch, dw: ModuleType, run: _Run) -> None:
    """done-work's reviewer gate, its placeholder check (which reads the
    capability's templates), and the moves it makes after a merge, recorded."""

    def approved(pr_number: int, pr: dict[str, Any], reason: str | None, config: Any) -> Any:
        return dw._GateResult(passed=True, passed_via="approved (stubbed reviewer)")

    def move(issue_number: int, target: str, root: Path | None, **kwargs: Any) -> int:
        run.moves.append(f"move #{issue_number} to {target}")
        return 0

    def close(issue_number: int, pr_number: int, root: Path | None, **kwargs: Any) -> int:
        run.moves.append(f"close #{issue_number}")
        return 0

    monkeypatch.setattr(dw, "_check_approval_gate", approved)
    monkeypatch.setattr(dw, "_check_pr_placeholder", lambda body, pr_number, root: [])
    monkeypatch.setattr(dw, "_invoke_move_issue", move)
    monkeypatch.setattr(dw, "_invoke_close_issue", close)


def _world(caller: str, tmp_path: Path) -> World:
    """A PR whose checks are green and whose issue's boxes are ticked, its head
    branch checked out in the clone, and a session rooted in the clone."""
    if caller == RELEASE:
        host = fake.HostingService(
            title="chore(release): v1.150.0",
            head_ref="release/v1.150.0",
            body="The release.\n",
        )
    else:
        host = fake.HostingService()
    root = tmp_path / "clone"
    (root / ".git").mkdir(parents=True)
    clone = fake.LocalClone(
        root=root,
        branches={"main": "sha-base", host.head_ref: host.head_oid},
        current=host.head_ref,
        commits={"sha-base": None, host.head_oid: "sha-base"},
    )
    return World(host=host, clone=clone, tmp=tmp_path, anchor=root)


def _argv(caller: str, options: tuple[str, ...]) -> list[str]:
    spelled: list[str] = []
    for option in options:
        if option not in _OPTIONS[caller]:
            raise AssertionError(f"{caller} has no {option}: its cell must be NotToday")
        spelled += _OPTIONS[caller][option]
    return spelled


def _gist(line: str) -> str:
    """A step line up to its detail: `merge: merged as c0ffee0` → `merge: merged`."""
    for mark in (" — ", " (", ";", ",", " as "):
        line = line.split(mark, 1)[0]
    return line


def _record(clone: fake.LocalClone) -> str:
    """The state of merge-pr's record of the PR in the clone, or ""."""
    path = clone.root / ".git" / "pkit" / "merge-pr" / f"{PR}.json"
    if not path.is_file():
        return ""
    return str(json.loads(path.read_text(encoding="utf-8"))["state"])


def _requests(kinds: list[str]) -> str:
    """The kinds in order, a run of one kind as `kind×n`."""
    runs: list[tuple[str, int]] = []
    for kind in kinds:
        if runs and runs[-1][0] == kind:
            runs[-1] = (kind, runs[-1][1] + 1)
        else:
            runs.append((kind, 1))
    return " ".join(kind if n == 1 else f"{kind}×{n}" for kind, n in runs)


def land(
    caller: str,
    scenario: Scenario,
    scripts: _Scripts,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> Cell:
    """Run `caller` on `scenario`, and say what it came to."""
    world = _world(caller, tmp_path)
    scenario.setup(world)
    argv = _argv(caller, world.options)
    host, clone = world.host, world.clone
    fake.install(monkeypatch, host, clone, anchor=world.anchor, stdin=world.stdin)
    monkeypatch.delenv("PM_INVOKER_LOGIN", raising=False)
    clock = fake.Clock()
    if world.backbone_has_the_noun:
        fake.route_backbone(
            monkeypatch, scripts.done_work.merge_queue, clock, rewrite=world.rewrite
        )
    else:
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        pkit = bin_dir / "pkit"
        pkit.write_text(_PKIT_WITHOUT_THE_NOUN, encoding="utf-8")
        pkit.chmod(pkit.stat().st_mode | stat.S_IXUSR)
        monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}")
    cap = tmp_path / "capability"
    run = _Run()
    monkeypatch.setattr(scripts.done_work.bootstrap_gate, "enforce", lambda *a, **k: True)
    monkeypatch.setattr(
        scripts.done_work.pr_merge.default_branch, "name", lambda config, **kwargs: "main"
    )
    guarded = _record_the_backbones_guard(monkeypatch)
    deletions = _record_the_backbones_deletions(monkeypatch)
    if world.pm_reads_same_repository:
        _pm_reads_same_repository(monkeypatch, scripts.done_work.session_guard)

    if caller == DONE_WORK:
        dw = scripts.done_work
        _stub_gates(monkeypatch, dw, cap)
        _stub_done_work(monkeypatch, dw, run)

        def once() -> str:
            ended = dw.run([str(ISSUE), "--yes", *argv])
            return f"{ended.kind} {ended.exit_code}" + (" retry" if ended.retry else "")

    elif caller == MERGE_PR:
        mp = scripts.merge_pr
        _stub_gates(monkeypatch, mp, cap)
        monkeypatch.setattr(mp, "fire_hooks", lambda event, **kwargs: run.hooks.append(event))
        monkeypatch.setattr(sys, "argv", ["merge-pr.py", str(PR), "--yes", *argv])

        def once() -> str:
            code = mp.main()
            record = _record(clone)
            return f"{code}" + (f" record={record}" if record else "")

    elif caller == RELEASE:
        monkeypatch.setattr(cli, "_target_kit", lambda: clone.root / ".pkit")

        def once() -> str:
            return _release(["release", "merge", str(PR), *argv])

    else:
        lw = scripts.land_work
        _stub_gates(monkeypatch, lw, cap)
        _stub_gates(monkeypatch, lw.done_work, cap)
        _stub_done_work(monkeypatch, lw.done_work, run)
        _the_change_wrote_no_answers(monkeypatch, lw.friction_answers)
        monkeypatch.setattr(lw, "_sleep", clock.sleep)
        monkeypatch.setattr(lw, "_monotonic", clock)

        def once() -> str:
            code = lw.main([str(ISSUE), "--yes", *argv])
            out = capsys.readouterr().out
            steps = [line for line in out.splitlines() if line.split(":", 1)[0] in _STEPS]
            return f"{code} {_gist(steps[-1])}" if steps else f"{code}"

    # Each run's end, a re-run's after the run before it.
    outcome = " → ".join(once() for _ in range(world.runs))
    if caller == MERGE_PR:
        after = "after_merge_pr" in run.hooks
    elif caller == RELEASE:
        # Release's one step after the merge is the branch clean-up, which
        # starts by checking out the base.
        after = bool(clone.checkouts)
    else:
        after = f"move #{ISSUE} to done" in run.moves
    unknown = [request.argv for request in host.requests if request.kind == fake.UNKNOWN]
    assert not unknown, f"the fake answered requests it does not model: {unknown}"
    return Cell(
        outcome,
        _requests(host.landing()),
        after,
        host.remote_deletion(),
        clone.local_deletion(host.head_ref),
        world.stdin.asked,
        _requests([passed for passed in guarded if passed != session_guard.SAME_REPO]),
        "; ".join(deletions),
    )


def _the_change_wrote_no_answers(monkeypatch: pytest.MonkeyPatch, answers: ModuleType) -> None:
    """land-work's `answers` step, answered as for a change that wrote none: the
    landings these rows walk are the ones a change with no answers takes, which
    the step leaves as they were (project-management DEC-055)."""

    def derive(head: str, base: str | None) -> Any:
        document = {"schema_version": 1, "base": {"commit": "", "outdated": False}}
        return answers.Derivation(head, document={**document, "answers": [], "unreadable": []})

    monkeypatch.setattr(answers, "derive", derive)
    monkeypatch.setattr(answers, "check_base_for", lambda base, config: None)


def _release(args: list[str]) -> str:
    """`pkit release merge` through the CLI in this process, and its exit. It
    runs with the scenario's own standard input, a terminal where the scenario
    has one, which a `CliRunner` would replace with its own. A request the
    service never answers no longer holds it: the backbone's bound on `gh`
    ends it (#1256)."""
    try:
        cli.main.main(args, prog_name="pkit", standalone_mode=False)
    except click.ClickException as exc:
        exc.show()
        return str(exc.exit_code)
    except SystemExit as exc:
        return str(exc.code or 0)
    return "0"


def _record_the_backbones_guard(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """How the backbone's cross-repository guard passed each change it was
    asked to clear, in order — `refused` for one it refused."""
    passes: list[str] = []
    clear = session_guard.clear

    def recording(*args: Any, **kwargs: Any) -> session_guard.Clearance | session_guard.Refusal:
        passage = clear(*args, **kwargs)
        passes.append(passage.passed if isinstance(passage, session_guard.Clearance) else "refused")
        return passage

    monkeypatch.setattr(session_guard, "clear", recording)
    return passes


def _record_the_backbones_deletions(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """How each of the backbone's deletions of a head branch ended, in order —
    its `outcome`, and its `reason_kind` where it has one — whether a caller
    asked for it by command or imported it."""
    ended: list[str] = []
    delete = pull_request_landing.delete_branch

    def recording(*args: Any, **kwargs: Any) -> pull_request_landing.BranchDeletion:
        deletion = delete(*args, **kwargs)
        ended.append(" ".join(part for part in (deletion.outcome, deletion.reason_kind) if part))
        return deletion

    monkeypatch.setattr(pull_request_landing, "delete_branch", recording)
    return ended


def _pm_reads_same_repository(monkeypatch: pytest.MonkeyPatch, guard: ModuleType) -> None:
    """project-management's copy of the comparison finds the session's own
    repository, whatever the backbone's finds."""

    def same(**kwargs: Any) -> Any:
        return guard.GuardOutcome(
            verdict=guard.SAME_REPO, anchor_repo=None, target_repo=None, reason="a stand-in"
        )

    monkeypatch.setattr(guard, "evaluate", same)


_CASES = [
    pytest.param(scenario, caller, id=f"{scenario.id}-{caller.replace(' ', '-')}")
    for scenario in SCENARIOS
    for caller in CALLERS
    if isinstance(scenario.expected(caller), Cell)
]


@pytest.mark.parametrize(("scenario", "caller"), _CASES)
def test_the_landing_today(
    scenario: Scenario,
    caller: str,
    scripts: _Scripts,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    cell = land(caller, scenario, scripts, tmp_path, monkeypatch, capsys)
    assert cell == scenario.expected(caller)


def test_every_empty_cell_says_why() -> None:
    for scenario in SCENARIOS:
        for caller in CALLERS:
            cell = scenario.today.cell(caller)
            if isinstance(cell, NotToday):
                assert cell.why, (scenario.id, caller)


def test_the_rows_are_told_apart() -> None:
    ids = [scenario.id for scenario in SCENARIOS]
    assert len(ids) == len(set(ids))


_BY_ID = {scenario.id: scenario for scenario in SCENARIOS}


@pytest.mark.parametrize("caller", CALLERS, ids=[c.replace(" ", "-") for c in CALLERS])
def test_every_caller_deletes_the_head_branch_only_through_the_backbone(
    caller: str,
    scripts: _Scripts,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """No caller keeps a copy of the deletion (#1255): the one request to
    delete the head branch the service receives is made inside the backbone's
    `delete_branch`, which project-management reaches by command and release
    by import. A deletion of the old form would be a request the fake does not
    model, which `land` refuses."""
    inside: list[bool] = []
    asked_inside: list[bool] = []
    delete = pull_request_landing.delete_branch

    def tracked(*args: Any, **kwargs: Any) -> pull_request_landing.BranchDeletion:
        inside.append(True)
        try:
            return delete(*args, **kwargs)
        finally:
            inside.pop()

    answer = fake.HostingService._delete_ref

    def deleting(self: fake.HostingService, args: list[str], request: fake.Request) -> Any:
        asked_inside.append(bool(inside))
        return answer(self, args, request)

    monkeypatch.setattr(pull_request_landing, "delete_branch", tracked)
    monkeypatch.setattr(fake.HostingService, "_delete_ref", deleting)
    cell = land(caller, _BY_ID["remote-tip-equals"], scripts, tmp_path, monkeypatch, capsys)
    assert cell.deletion == "deleted"
    assert asked_inside == [True]


@pytest.mark.parametrize(
    "row",
    [
        "remote-tip-moved",
        "remote-tip-gone",
        "fork",
        "branch-protected",
        "branch-used-by-another-open-pr",
        "branch-based-on-by-another-open-pr",
    ],
)
def test_a_branch_kept_gone_or_refused_never_fails_the_landing(row: str) -> None:
    """However the deletion ends, every caller's run ends as it does when the
    branch is deleted, with every step after the merge run."""
    for caller in CALLERS:
        cell, deleted = _BY_ID[row].expected(caller), _BY_ID["remote-tip-equals"].expected(caller)
        assert isinstance(cell, Cell) and isinstance(deleted, Cell)
        assert (cell.outcome, cell.after) == (deleted.outcome, True), (row, caller)
        assert cell.deletion != "deleted", (row, caller)
