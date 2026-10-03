#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml>=0.18",
#   "pathspec>=0.12",
# ]
# ///
"""Project-management capability — land-work (#1203).

Lands an issue's pull request in one command: waits for the checks on the PR's
head, has the reviewers whose verdicts are not fresh review that head, lists
the answers the change wrote, and merges it through `done-work`. It composes
the verbs' own functions — the CI gate's reading (`_lib.ci_checks`),
`review-pr`'s review, `done-work`'s merge — and adds no review loop or merge
mechanic of its own. The one rule it adds is on its own authorisation: where
the change wrote friction answers, a `--yes` run merges only a head whose list
it found already in the description ([project-management:DEC-055-pr-lists-answers]).

    land-work <N> [--yes [--expect-head SHA]] [--wait-minutes M | --no-wait]
                  [--dry-run]

Each step prints one line; the verbs it composes print their detail above it.
It stops at the first step that cannot go on, and its last line says why.

  head    The issue's branch and its open PR, found as `done-work` finds them
          — "gh did not answer" is never read as "no open PR". The PR's head
          on GitHub is read once and pinned (`--expect-head` stops the run when
          it is not the head named). Refused when the local branch holds
          commits that head lacks (the line gives the push) or has diverged
          from it. A local branch behind the head, or a checkout on another
          branch, is noted: land-work lands the head on GitHub, never the
          working tree. With no open PR it hands over to `done-work` only to
          complete a PR that has merged.
  ci      The PR's checks on the pinned head, read with the head they belong
          to and judged by the CI gate `done-work` applies, waited for up to
          `--wait-minutes` (default 30; `--no-wait` reads once). No check
          reported yet is never green. A failed check, and a PR that conflicts
          with its base (on which no `pull_request` workflow runs), stop the
          run before the review.
  review  In agent review mode, `review-pr`'s review on the pinned head: a
          verdict judged fresh for that head is kept, a stale or missing one
          re-run. A CHANGES_REQUESTED, kept or new, stops the run before the
          merge with the first line of each blocking finding; a reviewer that
          could not be run stops it too. The advisories of the approvals are
          printed. In human mode, and with no local reviewer registered, there
          is nothing to run: the approval is `done-work`'s gate.
  answers The change check's list of the answers the change wrote, derived
          at the pinned head (`_lib.friction_answers`), printed word for word
          and written into the PR's description, last before its footer,
          where it is not there already. Refused: a derivation that cannot be
          read (nothing is merged on a guess), a file the change touches whose
          front matter does not parse, a reason that reads as a closing
          reference, a list the description cannot hold, and — where the
          change wrote answers — a base that moved on after the head left it.
  merge   `done-work` with the pinned head. Without `--yes`, off a terminal,
          land-work merges nothing: it runs `done-work`'s gates as a dry run
          and stops with a `ready:` line naming the head and the command that
          merges it. At a terminal, `done-work`'s prompt asks, after the
          answers. Where the change wrote answers, a `--yes` run merges only
          with `--expect-head` and the list found already in the description;
          one that had to write it, or named no head, stops at `ready:`. Its
          gates, refusals and queue handling are done-work's own; land-work
          decides on how its run ended (`done_work.run`), never on its exit
          code.

There is no flag that skips the checks or the review: the bypasses are
`done-work`'s, with their audit. Run again, land-work resumes: green checks on
the same head are not waited for, fresh verdicts are not re-run, and a PR that
merged is completed through `done-work`.

Exit codes: the table in the capability README, "Landing a pull request in
one command", is the one list of them; `EXIT_*` below name them.
"""

from __future__ import annotations

import argparse
import contextlib
import importlib.util
import json
import re
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from types import ModuleType
from typing import Any

from ruamel.yaml import YAML

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
from _lib import (
    bootstrap_gate,
    friction_answers,
    merge_queue,
    pr_merge,
    provenance,
    session_guard,
)
from _lib.agent_verdicts import APPROVED, CHANGES_REQUESTED
from _lib.audit import short_sha
from _lib.ci_checks import FAILED, NO_RUN, PASSED, CiGateResult, evaluate_ci_gate
from _lib.gh import gh_get_issue, gh_run, load_adopter_config
from _lib.membership import (
    CAPABILITY_NAME,
    check_membership,
    resolve_capability_root,
    resolve_invoker_identity,
)
from _lib.review_mode import resolve_mode


def _load_verb(script: str, module_name: str) -> ModuleType:
    """A sibling verb's script, loaded as a module (its name has a hyphen), so
    land-work calls that verb's own functions rather than copies of them."""
    spec = importlib.util.spec_from_file_location(module_name, _HERE / script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


done_work = _load_verb("done-work.py", "pm_land_work_done_work")
review_pr = _load_verb("review-pr.py", "pm_land_work_review_pr")

# The exit codes, one per action the caller takes; the README's table says
# what each covers and what to do.
#: Merged — or a PR that had merged completed — and the issue done.
EXIT_MERGED = 0
#: Something on the PR must change: hand it back.
EXIT_NEEDS_CHANGE = 1
#: Nothing was changed: a usage error, a refused invocation, or a reading.
EXIT_UNREADABLE = 2
#: The PR's head is not the one pinned, or not the one authorised.
EXIT_HEAD_MOVED = 3
#: Accepted, not yet seen merged: queued or unconfirmed (done-work's 4).
EXIT_ACCEPTED = done_work.EXIT_ACCEPTED
#: The wait for the checks ran out.
EXIT_CI_PENDING = 5
#: A reviewer could not be run, so the review is not complete.
EXIT_REVIEW_INCOMPLETE = 6
#: A step failed where running again completes it.
EXIT_RETRY = 7
#: Ready to merge, and not authorised to: nothing was merged.
EXIT_READY = 8

#: How long the checks are waited for when `--wait-minutes` does not say.
DEFAULT_WAIT_MINUTES = 30.0
#: How often the checks are read while they are waited for.
POLL_SECONDS = 20.0

# The wait's sleep and clock, looked up when a wait runs.
_sleep: Callable[[float], None] = time.sleep
_monotonic: Callable[[], float] = time.monotonic


def _interactive() -> bool:
    """Whether a person can answer done-work's prompt (`move-issue`'s test)."""
    return sys.stdin.isatty()


# How a verdict's bullet is tagged, at the head of its text: bracketed
# (`[block]`), bold (`**[block]**`, `**block**`), backticked or followed by a
# colon. Blocking: `[block]`, as the software-engineering panel writes it, and
# `hard-reject` / `bypassable-with-audit`, the severities pm-reviewer
# classifies findings by. Advisory: `[advisory]`, and pm-reviewer's `warning`.
_BLOCKING_TAGS = ("block", "hard-reject", "bypassable-with-audit")
_ADVISORY_TAGS = ("advisory", "warning")
_BULLET = r"^\s*(?:[-*+]|\d+[.)])\s+"


def _tag_pattern(tags: tuple[str, ...]) -> re.Pattern[str]:
    tag = "(?:" + "|".join(re.escape(t) for t in tags) + ")"
    return re.compile(
        _BULLET + rf"(?:\[{tag}\]|\*\*\[?{tag}\]?\*\*|`{tag}`|{tag}\s*:)", re.IGNORECASE
    )


_BLOCKING_BULLET = _tag_pattern(_BLOCKING_TAGS)
_ADVISORY_BULLET = _tag_pattern(_ADVISORY_TAGS)
#: How many lines of a CHANGES_REQUESTED with no tagged finding are printed.
_UNTAGGED_LINES = 3


class _Stop(Exception):
    """A step that cannot go on: the run's exit code and its last line."""

    def __init__(self, code: int, line: str) -> None:
        super().__init__(line)
        self.code = code
        self.line = line


@dataclass(frozen=True)
class _Head:
    """The PR head land-work pins, and where it was found."""

    issue: int
    pr_number: int
    branch: str
    oid: str
    #: The PR's base branch, as a line says it.
    base: str
    #: The remote the branch is pushed to and fetched from.
    remote: str
    #: The PR's base branch as GitHub names it; empty when it named none.
    base_branch: str = ""


@dataclass(frozen=True)
class _Checks:
    """One reading of the PR, with the checks on the head it was read at."""

    head: str = ""
    state: str = ""
    rollup: list[dict[str, Any]] = field(default_factory=list)
    gate: CiGateResult | None = None
    #: GitHub's `mergeable`: MERGEABLE, CONFLICTING or UNKNOWN.
    mergeable: str = ""
    #: Why the PR could not be read; empty when it was.
    problem: str = ""

    @property
    def conflicting(self) -> bool:
        return self.mergeable == "CONFLICTING"


@dataclass(frozen=True)
class _ReviewEnd:
    """How the review step ended, when it did not stop the run."""

    #: Every required reviewer approved — False only for a dry run that would
    #: run a reviewer.
    clear: bool
    #: What the approval is, as the `ready:` line says it.
    approval: str


@dataclass(frozen=True)
class _AnswersEnd:
    """How the answers step ended, when it did not stop the run."""

    #: How many answers the change wrote.
    count: int
    #: The description carried the list for the pinned head before this run.
    found: bool

    def held(self, args: argparse.Namespace) -> str | None:
        """Why this run's `--yes` does not cover the answers, or None when it
        does — or when there is nothing for it to cover (DEC-055 point 3)."""
        if not self.count:
            return None
        if not args.expect_head:
            return "this run's --yes names no head"
        if not self.found:
            return "this run wrote them to the description, after the --yes was given"
        return None


# How the ci step ended, when it did not stop the run.
_CI_PASSED = "passed"
_CI_WOULD_WAIT = "would-wait"
_CI_PR_MERGED = "merged"


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    capability_root = resolve_capability_root(args.capability_root)
    if capability_root is None:
        print(f"error: {CAPABILITY_NAME} capability not found.", file=sys.stderr)
        return EXIT_UNREADABLE
    # The composed verbs gate each of these again; land-work gates them first
    # so a run they would refuse stops before it waits for any check.
    if not bootstrap_gate.enforce("land-work", capability_root=capability_root):
        return EXIT_UNREADABLE
    config = load_adopter_config(capability_root)
    members = done_work._read_members(capability_root, YAML(typ="safe"))
    membership = check_membership(members, resolve_invoker_identity(config=config))
    if not membership.allowed:
        print(membership.refusal_message, file=sys.stderr)
        return EXIT_UNREADABLE
    guard = session_guard.enforce(override=args.allow_foreign_repo)
    if not guard:
        return EXIT_UNREADABLE
    # A confirmation given here — the flag, or a yes at the terminal — is
    # passed on to the verbs it composes, so their guards pass by it and the
    # operator is asked once; and only then (`_passed_through`). A flag the
    # operator gave stays given, whatever this comparison found.
    if session_guard.confirmed(guard):
        args.allow_foreign_repo = True
    try:
        return _land(args, config, capability_root)
    except _Stop as stop:
        _say(stop.line)
        return stop.code


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Land an issue's pull request: wait for the checks on its head, have the "
            "reviewers whose verdicts are not fresh review it, and merge it through "
            "done-work. One line per step; a re-run resumes where a run stopped."
        ),
    )
    parser.add_argument("issue_number", type=int)
    wait = parser.add_mutually_exclusive_group()
    wait.add_argument(
        "--wait-minutes",
        type=pr_merge.minutes,
        default=None,
        metavar="MINUTES",
        help=(
            f"How long to wait for the checks on the PR's head (default "
            f"{DEFAULT_WAIT_MINUTES:g}), and, where the base merges through a queue, "
            "for the queue to merge it (passed to done-work)."
        ),
    )
    wait.add_argument(
        "--no-wait",
        action="store_true",
        help=(
            "Read the checks once, and return once the PR is queued where the base "
            "merges through a queue (exit 4). Run land-work again to go on."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what each step would do; review and merge nothing.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help=(
            "The authorisation to merge. Without it, off a terminal, land-work checks, "
            "reviews and runs done-work's gates, then stops with a `ready:` line (exit "
            "8); at a terminal, done-work asks. Where the change wrote friction answers, "
            "it covers them only with --expect-head and the list already in the PR's "
            "description; otherwise the run stops at `ready:` too."
        ),
    )
    parser.add_argument(
        "--expect-head",
        type=_commit,
        default=None,
        metavar="SHA",
        help=(
            "The PR head the merge is authorised for (7 to 40 hex digits): the run "
            "stops (exit 3) when the PR's head is another. The `ready:` line names it."
        ),
    )
    parser.add_argument(
        "--capability-root",
        type=Path,
        default=None,
        help=f"Default: <repo-root>/.pkit/capabilities/{CAPABILITY_NAME}/.",
    )
    session_guard.add_override_argument(parser)
    return parser


def _commit(value: str) -> str:
    """`--expect-head`: a commit id or a prefix of one, 7 to 40 hex digits."""
    commit = value.strip().lower()
    if not re.fullmatch(r"[0-9a-f]{7,40}", commit):
        raise argparse.ArgumentTypeError(f"{value!r} is not a commit id (7 to 40 hex digits)")
    return commit


def _land(args: argparse.Namespace, config: dict[str, Any], capability_root: Path) -> int:
    head = _pin_head(args, config)
    if head is None:
        return _merge(args, None, config)
    ci = _wait_for_checks(
        head, wait_seconds=_wait_seconds(args), dry_run=args.dry_run, config=config
    )
    if ci == _CI_PR_MERGED:
        return _merge(args, None, config)
    review = _review(args, head, config)
    answers = _answers(args, head, config, capability_root)
    if args.dry_run and (ci != _CI_PASSED or not review.clear):
        _say(
            f"merge: (dry-run) would hand PR #{head.pr_number} at {short_sha(head.oid)} to "
            "done-work once the checks pass and the review approves"
        )
        return EXIT_MERGED
    if args.dry_run:
        return _merge(args, head, config)
    if args.yes and answers.held(args) is not None:
        return _ready(args, head, review, config, answers)
    if not args.yes and not _interactive():
        return _ready(args, head, review, config, answers)
    return _merge(args, head, config)


# ---- head ----------------------------------------------------------------


def _pin_head(args: argparse.Namespace, config: dict[str, Any]) -> _Head | None:
    """The PR head to land, pinned; None when gh answered that the branch has
    no open PR (or there is no local branch to have one)."""
    issue = args.issue_number
    branch = done_work._find_issue_branch(issue)
    if branch is None:
        _say(
            f"head: no local branch */{issue}-* — done-work completes a PR that has merged already"
        )
        return None
    lookup = done_work._lookup_prs(branch, "open", done_work._OPEN_PR_FIELDS, config)
    if lookup.problem:
        raise _Stop(
            EXIT_UNREADABLE,
            f"head: whether {branch} has an open PR could not be read: {lookup.problem}. "
            f"Nothing was done; run `land-work {issue}` again once gh answers",
        )
    pr = lookup.first
    if pr is None:
        _say(f"head: no open PR for {branch} — done-work completes a PR that has merged already")
        return None
    number = int(pr["number"])
    oid = str(pr.get("headRefOid") or "")
    if pr.get("isDraft"):
        raise _Stop(
            EXIT_NEEDS_CHANGE,
            f"head: refused — PR #{number} is a draft; mark it ready with `review-work {issue}`",
        )
    if not oid:
        raise _Stop(EXIT_UNREADABLE, f"head: PR #{number}'s head could not be read")
    if args.expect_head and not oid.startswith(args.expect_head):
        raise _Stop(
            EXIT_HEAD_MOVED,
            f"head: stopped — PR #{number}'s head is {short_sha(oid)}, not "
            f"{args.expect_head[:7]}, the head the merge was authorised for: an "
            f"authorisation is for one head. Nothing was done; `land-work {issue}` checks "
            "and reviews the new one",
        )
    cross = bool(pr.get("isCrossRepository"))
    head = _Head(
        issue,
        number,
        branch,
        oid,
        base=str(pr.get("baseRefName") or "") or "the base branch",
        remote=_branch_remote(branch),
        base_branch=str(pr.get("baseRefName") or ""),
    )
    notes = _local_notes(head, cross_repository=cross)
    _say(f"head: {short_sha(oid)} (PR #{number}, {branch})" + "".join(f"; {n}" for n in notes))
    return head


def _branch_remote(branch: str) -> str:
    """The remote `branch` is pushed to — its push remote, else the remote it
    tracks — and `origin` when it names none, as start-work resolves a branch
    (COR-054 point 2)."""
    for atom in ("push:remotename", "upstream:remotename"):
        remote = _git("for-each-ref", f"--format=%({atom})", f"refs/heads/{branch}").stdout
        if remote.strip() and remote.strip() != ".":
            return remote.strip()
    return "origin"


def _local_notes(head: _Head, *, cross_repository: bool) -> list[str]:
    """What the local checkout says about the pinned head; refuses a local
    branch holding commits the head lacks."""
    branch, oid, remote = head.branch, head.oid, head.remote
    tip = _git("rev-parse", "--verify", "--quiet", f"refs/heads/{branch}").stdout.strip()
    notes: list[str] = []
    if tip and tip != oid:
        if not _has_commit(oid) and not cross_repository:
            _git("fetch", "--quiet", remote, f"refs/heads/{branch}")
        if not _has_commit(oid):
            raise _Stop(
                EXIT_UNREADABLE,
                f"head: cannot tell whether local {branch} (at {short_sha(tip)}) holds commits "
                f"PR #{head.pr_number}'s head {short_sha(oid)} lacks: this clone does not have "
                f"that head. Fetch it (`git fetch {remote} {branch}`) and run "
                f"`land-work {head.issue}` again",
            )
        ahead = _count_commits(f"{oid}..{tip}")
        behind = _count_commits(f"{tip}..{oid}")
        if ahead is None or behind is None:
            raise _Stop(
                EXIT_UNREADABLE,
                f"head: cannot compare local {branch} with PR #{head.pr_number}'s head "
                f"{short_sha(oid)}",
            )
        if ahead and behind:
            # No command is offered: when the PR's branch was force-pushed, a
            # pull would put back the commits the push replaced.
            raise _Stop(
                EXIT_NEEDS_CHANGE,
                f"head: refused — local {branch} and PR #{head.pr_number}'s head "
                f"{short_sha(oid)} have diverged ({_commits(ahead)} only here, "
                f"{_commits(behind)} only on the PR). Nothing was done",
            )
        if ahead:
            raise _Stop(
                EXIT_NEEDS_CHANGE,
                f"head: refused — local {branch} has {_commits(ahead)} PR "
                f"#{head.pr_number}'s head {short_sha(oid)} lacks. Push first: "
                f"`git push {remote} {branch}`",
            )
        notes.append(f"local {branch} is {_commits(behind)} behind it")
    current = _git("symbolic-ref", "--quiet", "--short", "HEAD").stdout.strip()
    if current != branch:
        notes.append(f"this checkout is on {current or 'a detached HEAD'}, not {branch}")
    return notes


def _git(*argv: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *argv], capture_output=True, text=True, check=False)


def _has_commit(oid: str) -> bool:
    return _git("cat-file", "-e", f"{oid}^{{commit}}").returncode == 0


def _count_commits(revisions: str) -> int | None:
    proc = _git("rev-list", "--count", revisions)
    if proc.returncode != 0:
        return None
    try:
        return int(proc.stdout.strip())
    except ValueError:
        return None


def _commits(count: int) -> str:
    return f"{count} commit" + ("" if count == 1 else "s")


# ---- ci --------------------------------------------------------------------


def _wait_seconds(args: argparse.Namespace) -> float:
    if args.no_wait:
        return 0.0
    minutes = DEFAULT_WAIT_MINUTES if args.wait_minutes is None else args.wait_minutes
    return minutes * 60


def _wait_for_checks(
    head: _Head, *, wait_seconds: float, dry_run: bool, config: dict[str, Any]
) -> str:
    """Wait for the checks on the pinned head, as long as `wait_seconds`.

    Returns how it ended when the run goes on — the checks passed, a dry run
    would wait for them, or the PR merged meanwhile — and stops the run
    otherwise. The checks are read with the head they belong to, so a run on
    another head never counts: a head that moved stops the run.
    """
    issue, number = head.issue, head.pr_number
    started = _monotonic()
    said = ""
    while True:
        checks = _read_pr(number, config)
        if checks.problem:
            progress = f"the checks could not be read: {checks.problem}"
            if dry_run or _monotonic() - started >= wait_seconds:
                raise _Stop(
                    EXIT_UNREADABLE,
                    f"ci: PR #{number}'s checks could not be read: {checks.problem}. "
                    f"Run `land-work {issue}` again",
                )
        elif checks.state == "MERGED":
            _say(f"ci: PR #{number} has merged meanwhile")
            return _CI_PR_MERGED
        elif checks.state != "OPEN":
            raise _Stop(
                EXIT_NEEDS_CHANGE,
                f"ci: PR #{number} is {checks.state.lower() or 'not open'}; nothing to land",
            )
        elif checks.head != head.oid:
            raise _Stop(
                EXIT_HEAD_MOVED,
                f"ci: stopped — PR #{number}'s head moved from {short_sha(head.oid)} to "
                f"{short_sha(checks.head)} while its checks were awaited. Nothing was "
                f"reviewed or merged; `land-work {issue}` checks and reviews the new head",
            )
        elif checks.conflicting:
            raise _Stop(EXIT_NEEDS_CHANGE, _conflict_line("ci", head))
        else:
            gate = checks.gate
            assert gate is not None
            if gate.state == PASSED:
                _say(f"ci: passed on {short_sha(head.oid)}{_passed_detail(checks.rollup)}")
                return _CI_PASSED
            if gate.state == FAILED:
                failed = "; ".join(
                    f"{check.name} ({check.outcome})" + (f" {check.url}" if check.url else "")
                    for check in gate.failed
                )
                raise _Stop(
                    EXIT_NEEDS_CHANGE,
                    f"ci: failed on {short_sha(head.oid)} — {failed}. Review and merge not started",
                )
            progress = (
                f"no check has been reported for {short_sha(head.oid)} yet"
                if gate.state == NO_RUN
                else f"running on {short_sha(head.oid)}: {', '.join(gate.running)}"
            )
            if dry_run:
                _say(f"ci: (dry-run) {progress} — would wait up to {_duration(wait_seconds)}")
                return _CI_WOULD_WAIT
            waited = _monotonic() - started
            if waited >= wait_seconds:
                raise _Stop(EXIT_CI_PENDING, _ran_out(head, gate, waited, wait_seconds))
        if progress != said:
            print(f"  ci: {progress}", flush=True)
            said = progress
        _sleep(max(0.0, min(POLL_SECONDS, wait_seconds - (_monotonic() - started))))


def _read_pr(pr_number: int, config: dict[str, Any]) -> _Checks:
    """The PR's head, state, mergeability and checks, in one reading: the
    checks GitHub reports are the ones on the head it reports with them."""
    try:
        proc = gh_run(
            [
                "gh",
                "pr",
                "view",
                str(pr_number),
                "--json",
                "headRefOid,state,mergeable,statusCheckRollup",
            ],
            config,
            check=False,
        )
    except OSError as exc:
        return _Checks(problem=f"`gh` could not be run ({exc})")
    if proc.returncode != 0:
        return _Checks(problem=(proc.stderr or "").strip() or f"gh exited {proc.returncode}")
    try:
        data = json.loads(proc.stdout)
    except ValueError:
        return _Checks(problem="gh's answer is not JSON")
    if not isinstance(data, dict):
        return _Checks(problem="gh's answer names no pull request")
    raw = data.get("statusCheckRollup")
    rollup = [check for check in raw if isinstance(check, dict)] if isinstance(raw, list) else []
    return _Checks(
        head=str(data.get("headRefOid") or ""),
        state=str(data.get("state") or "").upper(),
        rollup=rollup,
        gate=evaluate_ci_gate(rollup),
        mergeable=str(data.get("mergeable") or "").upper(),
    )


def _conflict_line(step: str, head: _Head) -> str:
    return (
        f"{step}: stopped — PR #{head.pr_number} conflicts with {head.base}, and GitHub runs "
        "no pull_request workflow on a PR that conflicts with its base. Merge "
        f"{head.base} into {head.branch} (`git merge {head.remote}/{head.base}`), resolve "
        f"the conflicts, push, and run `land-work {head.issue}` again"
    )


def _ran_out(head: _Head, gate: CiGateResult, waited: float, wait_seconds: float) -> str:
    sha, issue = short_sha(head.oid), head.issue
    after = "(--no-wait)" if wait_seconds == 0 else f"after {_duration(waited)}"
    if gate.state == NO_RUN:
        return (
            f"ci: no check has been reported for {sha} {after}: its run has not started, or "
            "none will — no workflow runs on pull requests here, the workflows skip the "
            "paths this PR changes, its head commit asks to skip CI ([skip ci]), or a run "
            f"from a fork awaits approval. Run `land-work {issue}` again to keep waiting. "
            "Only in a project that runs no checks on pull requests — never because a "
            f"wait ran out — review it with `review-pr {issue}` and merge it with "
            f"`done-work {issue}`: `done-work` does not wait for a check nobody reported"
        )
    return (
        f"ci: still running on {sha} {after}: {', '.join(gate.running)}. "
        f"Run `land-work {issue}` again to keep waiting"
    )


def _passed_detail(rollup: list[dict[str, Any]]) -> str:
    """` (8m, run <url>)` — how long the checks took and where to read them."""
    parts = [part for part in (_checks_took(rollup), _run_url(rollup)) if part]
    return f" ({', '.join(parts)})" if parts else ""


def _checks_took(rollup: list[dict[str, Any]]) -> str:
    started = [_instant(check.get("startedAt")) for check in rollup]
    completed = [_instant(check.get("completedAt")) for check in rollup]
    first = min((t for t in started if t is not None), default=None)
    last = max((t for t in completed if t is not None), default=None)
    if first is None or last is None or last < first:
        return ""
    return _duration((last - first).total_seconds())


def _run_url(rollup: list[dict[str, Any]]) -> str:
    """The workflow run the checks belong to, else the first check's page."""
    urls = [str(check.get("detailsUrl") or check.get("targetUrl") or "") for check in rollup]
    for url in urls:
        run = re.match(r"(https?://\S+/actions/runs/\d+)", url)
        if run:
            return f"run {run.group(1)}"
    first = next((url for url in urls if url), "")
    return f"run {first}" if first else ""


def _instant(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _duration(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.0f}s"
    return f"{seconds / 60:.0f}m"


# ---- review ----------------------------------------------------------------


def _review(args: argparse.Namespace, head: _Head, config: dict[str, Any]) -> _ReviewEnd:
    """Have the reviewers whose verdicts are not fresh review the pinned head.

    Returns how the review ended when the run goes on, and stops it otherwise.
    The stop is chosen in this order: the head moved; a CHANGES_REQUESTED;
    something could not be read; a reviewer could not be run — so one
    reviewer's block is reported even when another timed out.
    """
    issue = head.issue
    labels = done_work._label_names(gh_get_issue(issue, config, fields="labels"))
    mode = resolve_mode(config, issue_labels=labels)
    if mode.mode == "human":
        _say(
            f"review: human review mode ({mode.source}) — no reviewer agent to run; "
            "the approval is done-work's gate"
        )
        return _ReviewEnd(clear=True, approval="the PR is approved")
    agents = _ReviewEnd(clear=True, approval="all required verdicts approved")
    if not review_pr._get_local_registered(config):
        _say(
            "review: no local reviewer is registered — done-work's gate reads the "
            "remote reviewers' verdicts"
        )
        return agents
    argv = [str(issue), *_passed_through(args, review=True)]
    try:
        run = review_pr.review(argv, pinned_head=head.oid)
    except (Exception, SystemExit) as exc:
        raise _Stop(
            EXIT_REVIEW_INCOMPLETE,
            f"review: stopped — review-pr failed ({_described(exc)}), so the review is not "
            f"complete. Run `land-work {issue}` again once it can run",
        ) from exc
    verdicts = {name: (token, run.kept_bodies.get(name, "")) for name, token in run.kept.items()}
    verdicts.update(run.posted)
    requested = [name for name, (token, _) in verdicts.items() if token == CHANGES_REQUESTED]
    for name in requested:
        for line in _blocking_lines(verdicts[name][1], head.pr_number):
            print(f"  [{name}] {line}")
    advisories = 0
    for name, (token, body) in verdicts.items():
        if token == APPROVED:
            for line in _tagged_lines(body, _ADVISORY_BULLET):
                print(f"  [{name}] {line}")
                advisories += 1
    if run.moved_to is not None:
        raise _Stop(
            EXIT_HEAD_MOVED,
            f"review: stopped — PR #{head.pr_number}'s head is {short_sha(run.moved_to)}, "
            f"not {short_sha(head.oid)}, the head whose checks passed. Nothing was merged; "
            f"`land-work {issue}` checks and reviews the new head",
        )
    if requested:
        raise _Stop(
            EXIT_NEEDS_CHANGE,
            f"review: changes requested by {', '.join(requested)} — the blocking findings "
            "are above; merge not started",
        )
    if run.reason:
        raise _Stop(EXIT_UNREADABLE, f"review: stopped — {run.reason}")
    if run.failed:
        could_not = "; ".join(f"{name}: {why}" for name, why in run.failed.items())
        raise _Stop(
            EXIT_REVIEW_INCOMPLETE,
            f"review: stopped — a reviewer could not be run, so the review is not "
            f"complete ({could_not}). Run `land-work {issue}` again once it can run",
        )
    if run.exit_code != 0:
        raise _Stop(
            EXIT_REVIEW_INCOMPLETE,
            f"review: stopped — review-pr exited {run.exit_code}, so the review is not complete",
        )
    kept, ran = len(run.kept), len(run.posted)
    if args.dry_run:
        would = f"run {', '.join(run.would_run)}" if run.would_run else "run none"
        _say(f"review: (dry-run) would keep {kept} fresh and {would}")
        return _ReviewEnd(clear=not run.would_run, approval=agents.approval)
    noted = (
        f"; {advisories} advisor{'y' if advisories == 1 else 'ies'} above (every verdict in "
        f"full: `show-pr {head.pr_number} --field review`)"
        if advisories
        else ""
    )
    _say(f"review: {kept} kept fresh, {ran} re-run — all approved{noted}")
    return agents


def _blocking_lines(body: str, pr_number: int) -> list[str]:
    """What a CHANGES_REQUESTED says blocks: the first line of each finding
    tagged blocking, else the verdict's first lines and where to read it all."""
    tagged = _tagged_lines(body, _BLOCKING_BULLET)
    if tagged:
        return tagged
    text = [
        line.strip()
        for line in body.splitlines()
        if line.strip() and not line.lstrip().startswith(("Reviewer agent (", "<!--"))
    ]
    pointer = (
        f"(no finding tagged blocking — read it all with `show-pr {pr_number} --field review`)"
    )
    return [*text[:_UNTAGGED_LINES], pointer]


def _tagged_lines(body: str, tagged: re.Pattern[str]) -> list[str]:
    """The first line of each bullet `tagged` matches, the bullet mark dropped."""
    return [re.sub(_BULLET, "", line).strip() for line in body.splitlines() if tagged.match(line)]


# ---- answers ---------------------------------------------------------------


def _answers(
    args: argparse.Namespace, head: _Head, config: dict[str, Any], capability_root: Path
) -> _AnswersEnd:
    """The change check's list of the answers the change wrote, derived at the
    pinned head, printed word for word, and written into the PR's description
    where it is not there already (DEC-055). Stops the run on a list it cannot
    read or must not write; a dry run writes nothing."""
    issue, number, sha = head.issue, head.pr_number, short_sha(head.oid)
    base = friction_answers.check_base_for(head.base_branch, config) if head.base_branch else None
    derived = friction_answers.derive(head.oid, base)
    document = derived.document
    if document is None:
        raise _Stop(
            EXIT_UNREADABLE,
            f"answers: the change check's list at {sha} could not be read — {derived.problem}. "
            f"Nothing was merged; run `land-work {issue}` again",
        )
    touched = _unreadable_in_change(derived)
    if touched:
        raise _Stop(
            EXIT_NEEDS_CHANGE,
            f"answers: refused — front matter the change check cannot read, in "
            f"{_files(touched)} this change touches, so its words cannot be listed. Fix it "
            f"(`pkit validate` names the problem), push, and run `land-work {issue}` again",
        )
    body = _read_body(head, config)
    count = len(derived.answers)
    if not count:
        return _no_answers(args, head, body, config, capability_root)
    if derived.outdated:
        raise _Stop(
            EXIT_NEEDS_CHANGE,
            f"answers: refused — {head.base} moved on after PR #{number}'s head left it, so "
            f"its merge can land words the list at {sha} does not show. Merge {head.base} into "
            f"{head.branch} (`git merge {head.remote}/{head.base}`), push, and run "
            f"`land-work {issue}` again",
        )
    closing = friction_answers.closing_reference(document)
    if closing is not None:
        location, words = closing
        raise _Stop(
            EXIT_NEEDS_CHANGE,
            f"answers: refused — the words on {location} read as a closing reference "
            f"({words}): in the description and the squash commit they would close an issue "
            f"at merge. Reword them on the artefact, push, and run `land-work {issue}` again. "
            "Nothing was written",
        )
    section = friction_answers.render(document, head.oid)
    for line in friction_answers.lines(document):
        print(f"  {line}")
    written = f"{count} written by this change"
    where = f"listed above and in PR #{number}'s description"
    if friction_answers.current(body, section):
        _say(f"answers: {written}, {where}")
        return _AnswersEnd(count, found=True)
    new_body = _stamped(body, section, capability_root)
    if not friction_answers.fits(new_body):
        raise _Stop(
            EXIT_NEEDS_CHANGE,
            f"answers: refused — PR #{number}'s description with the list is {len(new_body)} "
            f"characters, past the {friction_answers.BODY_LIMIT} the host keeps: split the "
            "change or narrow the anchor. Nothing was written",
        )
    if args.dry_run:
        _say(f"answers: (dry-run) {written}, {where} (would write)")
        return _AnswersEnd(count, found=False)
    _write_body(head, new_body, config, what="the list")
    _say(f"answers: {written}, {where} (written now)")
    return _AnswersEnd(count, found=False)


def _no_answers(
    args: argparse.Namespace,
    head: _Head,
    body: str,
    config: dict[str, Any],
    capability_root: Path,
) -> _AnswersEnd:
    """A change that wrote no answers: the run goes on as it would without the
    step, and a list an earlier head left in the description is removed."""
    if friction_answers.current(body, None):
        _say("answers: none written by this change")
    elif args.dry_run:
        _say(
            f"answers: (dry-run) none written by this change — would remove the list an "
            f"earlier head left in PR #{head.pr_number}'s description"
        )
    else:
        _write_body(head, _stamped(body, None, capability_root), config, what="the earlier list")
        _say(
            f"answers: none written by this change — removed the list an earlier head left "
            f"in PR #{head.pr_number}'s description"
        )
    return _AnswersEnd(0, found=True)


def _unreadable_in_change(derived: friction_answers.Derivation) -> list[str]:
    """The files whose front matter does not parse at the head that the change
    touched: words on them may be answers the list cannot show. A file the
    change did not touch holds no word of it. Where the change's files cannot
    be read, every such file counts."""
    if not derived.unreadable:
        return []
    proc = _git("diff", "--name-only", "-z", "--no-renames", derived.merge_base, derived.head)
    if proc.returncode != 0 or not derived.merge_base:
        return list(derived.unreadable)
    changed = set(proc.stdout.split("\0"))
    return [path for path in derived.unreadable if path in changed]


def _files(paths: list[str]) -> str:
    shown = ", ".join(paths[:3]) + (f" and {len(paths) - 3} more" if len(paths) > 3 else "")
    return f"{len(paths)} file{'' if len(paths) == 1 else 's'} ({shown})"


def _read_body(head: _Head, config: dict[str, Any]) -> str:
    """The PR's description as GitHub has it; stops the run when it cannot be read."""
    pr_number = head.pr_number
    problem = ""
    try:
        proc = gh_run(["gh", "pr", "view", str(pr_number), "--json", "body"], config, check=False)
    except OSError as exc:
        problem = f"`gh` could not be run ({exc})"
    else:
        if proc.returncode != 0:
            problem = (proc.stderr or "").strip() or f"gh exited {proc.returncode}"
        else:
            try:
                data = json.loads(proc.stdout)
            except ValueError:
                data = None
            if isinstance(data, dict):
                return str(data.get("body") or "")
            problem = "gh's answer names no pull request"
    raise _Stop(
        EXIT_UNREADABLE,
        f"answers: PR #{pr_number}'s description could not be read: {problem}. Nothing was "
        f"merged; run `land-work {head.issue}` again",
    )


def _stamped(body: str, section: str | None, capability_root: Path) -> str:
    """`body` with the list `section` — or none — last, and the provenance footer
    after it, as every body-writing script writes one (ADR-037)."""
    listed = friction_answers.stamp(provenance.strip_footer(body), section)
    return provenance.stamp(listed, provenance.read_versions(capability_root))


def _write_body(head: _Head, body: str, config: dict[str, Any], *, what: str) -> None:
    """Write the PR's description; stops the run (a re-run completes it) when it fails."""
    with tempfile.NamedTemporaryFile("w", suffix=".md", encoding="utf-8", delete=False) as f:
        f.write(body)
        path = f.name
    try:
        argv = ["gh", "pr", "edit", str(head.pr_number), "--body-file", path]
        try:
            proc = gh_run(argv, config, check=False)
            problem = (
                ""
                if proc.returncode == 0
                else (proc.stderr or "").strip() or f"gh exited {proc.returncode}"
            )
        except OSError as exc:
            problem = f"`gh` could not be run ({exc})"
    finally:
        with contextlib.suppress(OSError):
            Path(path).unlink()
    if problem:
        raise _Stop(
            EXIT_RETRY,
            f"answers: {what} could not be written to PR #{head.pr_number}'s description: "
            f"{problem}. Nothing was merged; run `land-work {head.issue}` again",
        )


# ---- merge -----------------------------------------------------------------


def _ready(
    args: argparse.Namespace,
    head: _Head,
    review: _ReviewEnd,
    config: dict[str, Any],
    answers: _AnswersEnd,
) -> int:
    """No authorisation to merge — none given, or a `--yes` that does not cover
    the answers above (DEC-055 point 3): run done-work's gates as a dry run on
    the pinned head, and say the head is ready, with the command that merges it."""
    argv = [str(head.issue), *_passed_through(args, review=False), "--dry-run"]
    end = _run_done_work(argv, head, config, merging=False)
    if end.kind != done_work.PLANNED:
        code, line = _judged(end, head, args, config)
        _say(line)
        return code
    to_read = ""
    if answers.count:
        noun = "answer" if answers.count == 1 else "answers"
        held = answers.held(args) if args.yes else None
        to_read = f", {answers.count} {noun} above to read" + (
            f" ({held}, so it does not cover them)" if held else ""
        )
    _say(
        f"ready: {short_sha(head.oid)} — CI passed, {review.approval}{to_read}; merge with: "
        f"pkit pm land-work {head.issue} --yes --expect-head {head.oid}"
    )
    return EXIT_READY


def _merge(args: argparse.Namespace, head: _Head | None, config: dict[str, Any]) -> int:
    """Hand over to done-work — to land the pinned head, or, with no open PR,
    only to complete a PR that has merged — and say in one line how it ended."""
    argv = [str(args.issue_number), *_passed_through(args, review=False)]
    end = _run_done_work(argv, head, config, merging=not args.dry_run)
    if end.kind == done_work.PLANNED:
        _say("merge: (dry-run) done-work's plan is above")
        return EXIT_MERGED
    code, line = _judged(end, head, args, config)
    _say(f"merge: (dry-run) {line.removeprefix('merge: ')}" if args.dry_run else line)
    return code


def _run_done_work(
    argv: list[str], head: _Head | None, config: dict[str, Any], *, merging: bool
) -> Any:
    """How done-work's run ended (`done_work.DoneWorkRun`). When it raised,
    the run stops, with what GitHub reports of the PR."""
    try:
        if head is None:
            return done_work.run(argv, merged_only=True)
        return done_work.run(argv, pinned_head=head.oid)
    except (Exception, SystemExit) as exc:
        issue = int(argv[0])
        failed = _done_work_failed(_described(exc), issue, head, config, merging=merging)
        raise _Stop(*failed) from exc


def _done_work_failed(
    failure: str, issue: int, head: _Head | None, config: dict[str, Any], *, merging: bool
) -> tuple[int, str]:
    """The code and the line for a done-work run that raised: what happened to
    the PR is read from GitHub — when the run was one that could merge it.
    One reading that does not find it merged says what it found, never that
    it did not merge: a request done-work sent before it raised may still
    show, and the re-run reads the PR first."""
    if head is None:
        return EXIT_RETRY, (
            f"merge: stopped — done-work failed ({failure}) completing #{issue}'s merged PR. "
            f"Run `land-work {issue}` again to complete it"
        )
    number = head.pr_number
    if not merging:
        return EXIT_RETRY, (
            f"merge: not merged — done-work failed ({failure}). Run `land-work {issue}` again"
        )
    reading = _read_pr(number, config)
    if reading.problem:
        return EXIT_ACCEPTED, (
            f"merge: unconfirmed — done-work failed ({failure}), and whether PR #{number} "
            f"merged could not be read: {reading.problem}. Run `land-work {issue}` again once "
            "GitHub answers"
        )
    if reading.state == "MERGED":
        return EXIT_RETRY, (
            f"merge: merged{_as_commit(number, config)}, but done-work failed after the merge "
            f"({failure}). Run `land-work {issue}` again to complete #{issue}"
        )
    state = reading.state.lower() or "of no reported state"
    return EXIT_RETRY, (
        f"merge: not seen merged — done-work failed ({failure}), and one reading since finds "
        f"PR #{number} {state}. Run `land-work {issue}` again: it reads the PR first, and "
        "completes it if it has merged"
    )


def _judged(
    end: Any, head: _Head | None, args: argparse.Namespace, config: dict[str, Any]
) -> tuple[int, str]:
    """The exit code and the line for how done-work's run ended."""
    issue = args.issue_number
    kind, reason = end.kind, end.reason
    again = f"run `land-work {issue}` again"
    if head is None:
        if kind == done_work.MERGED:
            return EXIT_MERGED, f"merge: #{issue} completed through its merged PR"
        if kind == done_work.FOLLOW_UP_OWED:
            return EXIT_RETRY, (
                f"merge: #{issue}'s PR has merged, but a step after the merge failed: "
                f"{reason} — {again} to complete it"
            )
        if kind == done_work.DECLINED:
            return EXIT_READY, f"merge: declined — #{issue}'s merged PR was not completed"
        if kind == done_work.REFUSED and end.retry:
            return EXIT_RETRY, (
                f"merge: not completed — {reason} Run `land-work {issue}` again to check, "
                "review and land it"
            )
        if kind == done_work.UNREADABLE:
            return EXIT_UNREADABLE, f"merge: stopped — {reason}"
        return EXIT_NEEDS_CHANGE, f"merge: refused — {reason}"
    number = head.pr_number
    if kind == done_work.MERGED:
        return EXIT_MERGED, f"merge: merged{_as_commit(number, config)}"
    if kind == done_work.FOLLOW_UP_OWED:
        return EXIT_RETRY, (
            f"merge: merged{_as_commit(number, config)}, but a step after the merge failed: "
            f"{reason} — {again} to complete #{issue}"
        )
    if kind in (done_work.QUEUED, done_work.UNCONFIRMED):
        return _accepted(head, queued=kind == done_work.QUEUED, config=config)
    if kind == done_work.DECLINED:
        return EXIT_READY, (
            f"merge: declined — PR #{number} at {short_sha(head.oid)} was not merged"
        )
    if kind == done_work.HEAD_MOVED:
        return EXIT_HEAD_MOVED, f"merge: stopped — {reason}"
    if kind == done_work.UNREADABLE:
        return EXIT_UNREADABLE, f"merge: stopped — {reason}"
    if kind == done_work.REFUSED and end.retry and not args.dry_run:
        return _request_failed(head, reason, config)
    if kind == done_work.REFUSED and end.retry:
        return EXIT_RETRY, f"merge: not merged — {reason}; {again}"
    return EXIT_NEEDS_CHANGE, f"merge: refused — {reason}"


def _request_failed(head: _Head, reason: str, config: dict[str, Any]) -> tuple[int, str]:
    """done-work merged nothing, and a re-run may help: what GitHub reports of
    the PR now says which — a head that moved, a conflict, a merge meanwhile."""
    issue, number = head.issue, head.pr_number
    again = f"run `land-work {issue}` again"
    now = _read_pr(number, config)
    if now.problem:
        return EXIT_RETRY, f"merge: not merged — {reason}; {again}"
    if now.state == "MERGED":
        return EXIT_RETRY, (
            f"merge: merged meanwhile{_as_commit(number, config)}, though done-work reports "
            f"{reason} — {again} to complete #{issue}"
        )
    if now.head and now.head != head.oid:
        return EXIT_HEAD_MOVED, (
            f"merge: stopped — PR #{number}'s head moved from {short_sha(head.oid)} to "
            f"{short_sha(now.head)} before the merge. Nothing was merged; `land-work {issue}` "
            "checks and reviews the new head"
        )
    if now.conflicting:
        return EXIT_NEEDS_CHANGE, _conflict_line("merge", head)
    return EXIT_RETRY, f"merge: not merged — {reason}; {again}"


def _accepted(head: _Head, *, queued: bool, config: dict[str, Any]) -> tuple[int, str]:
    """done-work's queued or unconfirmed end, said as GitHub now reports the PR.

    A queued PR read neither merged nor queued left the queue: not merged. An
    unconfirmed one read so stays unconfirmed — its request may still show,
    and one reading never says it was not made."""
    issue, number = head.issue, head.pr_number
    again = f"run `land-work {issue}` again once it merges"
    try:
        reading: merge_queue.Reading | None = merge_queue.read(number, config)
    except merge_queue.Unreadable:
        reading = None
    if reading is None:
        if queued:
            return EXIT_ACCEPTED, (
                f"merge: queued, as done-work reports — PR #{number} could not be read again; "
                f"{again}"
            )
        return EXIT_ACCEPTED, (
            f"merge: unconfirmed — whether PR #{number} merged is not known; {again}"
        )
    if reading.merged:
        return EXIT_RETRY, (
            f"merge: merged meanwhile — run `land-work {issue}` again to complete #{issue}"
        )
    if reading.queued:
        return EXIT_ACCEPTED, f"merge: queued — PR #{number} {reading.describe()}; {again}"
    if not queued:
        # An unconfirmed merge or enqueue may still show: one reading of neither
        # does not say it was not made (ADR-061 point 7), so it stays unconfirmed.
        return EXIT_ACCEPTED, (
            f"merge: unconfirmed — PR #{number} reads neither merged nor queued "
            f"({reading.describe()}), which does not tell whether the request was made; read "
            f"it with `pkit pull-request read {number}`, and run `land-work {issue}` again: "
            "it merges the PR if it has not merged"
        )
    return EXIT_RETRY, (
        f"merge: not merged — PR #{number} is neither merged nor in the merge queue "
        f"({reading.describe()}); run `land-work {issue}` again to merge it"
    )


def _as_commit(pr_number: int, config: dict[str, Any]) -> str:
    """` as <merge commit>` — for a PR GitHub reports merged — or "" when the
    merge commit cannot be read."""
    try:
        proc = gh_run(
            ["gh", "pr", "view", str(pr_number), "--json", "mergeCommit"], config, check=False
        )
    except OSError:
        return ""
    if proc.returncode != 0:
        return ""
    try:
        data = json.loads(proc.stdout)
    except ValueError:
        return ""
    commit = data.get("mergeCommit") if isinstance(data, dict) else None
    oid = str(commit.get("oid") or "") if isinstance(commit, dict) else ""
    return f" as {short_sha(oid)}" if oid else ""


# ---- composing the verbs ---------------------------------------------------


def _passed_through(args: argparse.Namespace, *, review: bool) -> list[str]:
    """The flags a composed verb is handed: review-pr takes the dry run and
    the root; done-work also takes `--yes` and the wait for a queue."""
    argv: list[str] = []
    if args.dry_run:
        argv.append("--dry-run")
    if args.capability_root is not None:
        argv += ["--capability-root", str(args.capability_root)]
    if args.allow_foreign_repo:
        argv.append("--allow-foreign-repo")
    if review:
        return argv
    if args.yes:
        argv.append("--yes")
    if args.no_wait:
        argv.append("--no-wait")
    elif args.wait_minutes is not None:
        argv += ["--wait-minutes", f"{args.wait_minutes:g}"]
    return argv


def _described(exc: BaseException) -> str:
    """An exception a composed verb raised, in a few words."""
    if isinstance(exc, SystemExit):
        return f"it exited {exc.code}"
    text = str(exc).strip()
    return f"{type(exc).__name__}: {text}" if text else type(exc).__name__


def _say(line: str) -> None:
    sys.stderr.flush()
    print(line, flush=True)


if __name__ == "__main__":
    sys.exit(main())
