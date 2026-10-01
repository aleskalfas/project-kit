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
head, has the reviewers whose verdicts are not fresh review that head, and
merges it through `done-work`. It composes the verbs' own functions — the CI
gate's reading (`_lib.ci_checks`), `review-pr`'s review, `done-work`'s merge —
and adds no gate, review loop or merge mechanic of its own.

    land-work <N> [--wait-minutes M | --no-wait] [--dry-run] [--yes]

Each step prints one line; the verbs it composes print their detail above it.
It stops at the first step that cannot go on, and its last line says why.

  head    The issue's branch and its open PR, found as `done-work` finds them.
          The PR's head on GitHub is read once and pinned: every later step
          checks it and is handed it. Refused when the local branch holds
          commits that head lacks (the line gives the push). A local branch
          behind the head, or a checkout on another branch, is noted: land-work
          lands the head on GitHub, never the working tree, so it runs from
          any checkout of the clone that has the branch. With no open PR it
          goes straight to `done-work`, which completes a PR already merged.
  ci      The PR's checks on the pinned head, judged by the CI gate
          `done-work` applies, waited for up to `--wait-minutes` (default 30;
          `--no-wait` reads once). No check reported yet is a run that has
          not started, never green. A failed check stops the run before the
          review, naming the check and where to read it.
  review  In agent review mode, `review-pr`'s review on the pinned head: a
          fresh verdict is kept, a stale or missing one re-run. A
          CHANGES_REQUESTED, kept or new, stops the run before the merge and
          prints the first line of each `[block]` finding with its reviewer;
          a reviewer that could not be run stops it too. In human mode, and
          with no local reviewer registered, there is nothing to run: the
          approval is `done-work`'s gate.
  merge   `done-work` with the pinned head, `--yes` and `--dry-run` passed
          through, and the wait flags bounding its wait for a merge queue.
          Its gates, refusals, queue handling and exit codes are its own.

There is no flag that skips the checks or the review: the bypasses are
`done-work`'s, with their audit. Run again, land-work resumes: green checks on the
same head are not waited for, fresh verdicts are not re-run, and a PR that
merged is completed through `done-work`.

Exit codes:
  0  merged, and the issue done
  1  stopped on something to change: unpushed commits, a failed check, a
     CHANGES_REQUESTED verdict, or `done-work` refused the merge
  2  usage error; the PR, its head or its checks could not be read
  3  the PR's head moved from the pinned one; or `done-work`'s merge failed
     or the PR left the merge queue unmerged
  4  accepted, not yet seen merged: the PR is in the merge queue, or the
     merge could not be confirmed (`done-work`'s 4) — run land-work again
  5  the wait for the checks ran out: no run had started, or one still runs —
     run land-work again
  6  a reviewer could not be run, so the review is not complete
"""

from __future__ import annotations

import argparse
import contextlib
import importlib.util
import io
import json
import re
import subprocess
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from types import ModuleType
from typing import Any, TextIO, TypeVar

from ruamel.yaml import YAML

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
from _lib import bootstrap_gate, merge_queue, pr_merge, session_guard
from _lib.agent_verdicts import CHANGES_REQUESTED
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

EXIT_MERGED = 0
EXIT_STOPPED = 1
EXIT_UNREADABLE = 2
EXIT_HEAD_MOVED = 3
EXIT_ACCEPTED = done_work.EXIT_ACCEPTED
EXIT_CI_PENDING = 5
EXIT_REVIEW_INCOMPLETE = 6

#: How long the checks are waited for when `--wait-minutes` does not say.
DEFAULT_WAIT_MINUTES = 30.0
#: How often the checks are read while they are waited for.
POLL_SECONDS = 20.0

# The wait's sleep and clock, looked up when a wait runs.
_sleep: Callable[[float], None] = time.sleep
_monotonic: Callable[[], float] = time.monotonic

# What a reviewer's verdict tags a blocking finding with: a bullet whose text
# starts `[block]`, as the software-engineering review panel writes them.
_BLOCK_BULLET = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+(?:\*\*)?\[block\]")

# The lines another verb's output opens a refusal or an error with.
_REASON_PREFIXES = ("[refused]", "[hard-reject]", "error:")


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


@dataclass(frozen=True)
class _Checks:
    """One reading of the PR's checks, with the head and state it was read at."""

    head: str = ""
    state: str = ""
    rollup: list[dict[str, Any]] = field(default_factory=list)
    gate: CiGateResult | None = None
    #: Why the checks could not be read; empty when they were.
    problem: str = ""


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
    # The composed verbs gate each of these again; land-work gates them first so a
    # run they would refuse stops before it waits for any check.
    if not bootstrap_gate.enforce("land-work", capability_root=capability_root):
        return EXIT_UNREADABLE
    config = load_adopter_config(capability_root)
    members = done_work._read_members(capability_root, YAML(typ="safe"))
    membership = check_membership(members, resolve_invoker_identity(config=config))
    if not membership.allowed:
        print(membership.refusal_message, file=sys.stderr)
        return EXIT_STOPPED
    if not session_guard.enforce(override=args.allow_foreign_repo):
        return EXIT_STOPPED
    try:
        return _land(args, config)
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
        help="Merge without done-work's confirmation prompt.",
    )
    parser.add_argument(
        "--capability-root",
        type=Path,
        default=None,
        help=f"Default: <repo-root>/.pkit/capabilities/{CAPABILITY_NAME}/.",
    )
    session_guard.add_override_argument(parser)
    return parser


def _land(args: argparse.Namespace, config: dict[str, Any]) -> int:
    head = _pin_head(args.issue_number, config)
    if head is None:
        return _merge(args, None, config)
    ci = _wait_for_checks(
        head, wait_seconds=_wait_seconds(args), dry_run=args.dry_run, config=config
    )
    if ci == _CI_PR_MERGED:
        return _merge(args, None, config)
    review_clear = _review(args, head, config)
    if args.dry_run and (ci != _CI_PASSED or not review_clear):
        _say(
            f"merge: (dry-run) would hand PR #{head.pr_number} at {short_sha(head.oid)} to "
            "done-work once the checks pass and the review approves"
        )
        return EXIT_MERGED
    return _merge(args, head, config)


# ---- head ----------------------------------------------------------------


def _pin_head(issue: int, config: dict[str, Any]) -> _Head | None:
    """The PR head to land, pinned; None when there is no open PR to pin."""
    branch = done_work._find_issue_branch(issue)
    pr = done_work._find_pr_for_branch(branch, config) if branch is not None else None
    if branch is None or pr is None:
        missing = f"no open PR for {branch}" if branch else f"no local branch */{issue}-*"
        _say(f"head: {missing} — done-work completes a PR that has merged already")
        return None
    number = int(pr["number"])
    oid = str(pr.get("headRefOid") or "")
    if pr.get("isDraft"):
        raise _Stop(
            EXIT_UNREADABLE,
            f"head: refused — PR #{number} is a draft; mark it ready with `review-work {issue}`",
        )
    if not oid:
        raise _Stop(EXIT_UNREADABLE, f"head: PR #{number}'s head could not be read")
    head = _Head(issue, number, branch, oid)
    notes = _local_notes(head, cross_repository=bool(pr.get("isCrossRepository")))
    _say(f"head: {short_sha(oid)} (PR #{number}, {branch})" + "".join(f"; {n}" for n in notes))
    return head


def _local_notes(head: _Head, *, cross_repository: bool) -> list[str]:
    """What the local checkout says about the pinned head; refuses a local
    branch holding commits the head lacks."""
    branch, oid = head.branch, head.oid
    tip = _git("rev-parse", "--verify", "--quiet", f"refs/heads/{branch}").stdout.strip()
    notes: list[str] = []
    if tip and tip != oid:
        if not _has_commit(oid) and not cross_repository:
            _git("fetch", "--quiet", "origin", f"refs/heads/{branch}")
        if not _has_commit(oid):
            raise _Stop(
                EXIT_UNREADABLE,
                f"head: cannot tell whether local {branch} (at {short_sha(tip)}) holds commits "
                f"PR #{head.pr_number}'s head {short_sha(oid)} lacks: this clone does not have "
                f"that head. Fetch it (`git fetch origin {branch}`) and run land-work again",
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
            raise _Stop(
                EXIT_STOPPED,
                f"head: refused — local {branch} and PR #{head.pr_number}'s head "
                f"{short_sha(oid)} have diverged ({_commits(ahead)} only here, "
                f"{_commits(behind)} only on the PR). Reconcile them "
                f"(`git pull --rebase origin {branch}`), push (`git push origin {branch}`), "
                "and run land-work again",
            )
        if ahead:
            raise _Stop(
                EXIT_STOPPED,
                f"head: refused — local {branch} has {_commits(ahead)} PR "
                f"#{head.pr_number}'s head {short_sha(oid)} lacks. Push first: "
                f"`git push origin {branch}`",
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
        checks = _read_checks(number, config)
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
                EXIT_STOPPED,
                f"ci: PR #{number} is {checks.state.lower() or 'not open'}; nothing to land",
            )
        elif checks.head != head.oid:
            raise _Stop(
                EXIT_HEAD_MOVED,
                f"ci: stopped — PR #{number}'s head moved from {short_sha(head.oid)} to "
                f"{short_sha(checks.head)} while its checks were awaited; run `land-work {issue}` "
                "again to land the new head",
            )
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
                    EXIT_STOPPED,
                    f"ci: failed on {short_sha(head.oid)} — {failed}. Review and merge not started",
                )
            progress = (
                f"no run has started for {short_sha(head.oid)} yet"
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


def _read_checks(pr_number: int, config: dict[str, Any]) -> _Checks:
    """The PR's head, state and checks, in one reading: the checks GitHub
    reports are the ones on the head it reports with them."""
    try:
        proc = gh_run(
            [
                "gh",
                "pr",
                "view",
                str(pr_number),
                "--json",
                "headRefOid,state,statusCheckRollup",
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
    )


def _ran_out(head: _Head, gate: CiGateResult, waited: float, wait_seconds: float) -> str:
    sha, issue = short_sha(head.oid), head.issue
    after = "(--no-wait)" if wait_seconds == 0 else f"after {_duration(waited)}"
    if gate.state == NO_RUN:
        return (
            f"ci: no run has started for {sha} {after}. Run `land-work {issue}` again to keep "
            "waiting; if this repository runs no checks on pull requests there is none to "
            f"wait for — review with `review-pr {issue}` and merge with `done-work {issue}`"
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


def _review(args: argparse.Namespace, head: _Head, config: dict[str, Any]) -> bool:
    """Have the reviewers whose verdicts are not fresh review the pinned head.

    Returns whether the review is clear — every required reviewer approved —
    which is False only for a dry run that would run a reviewer; every other
    outcome that is not clear stops the run.
    """
    issue = head.issue
    labels = done_work._label_names(gh_get_issue(issue, config, fields="labels"))
    mode = resolve_mode(config, issue_labels=labels)
    if mode.mode == "human":
        _say(
            f"review: human review mode ({mode.source}) — no reviewer agent to run; "
            "the approval is done-work's gate"
        )
        return True
    if not review_pr._get_local_registered(config):
        _say(
            "review: no local reviewer is registered — done-work's gate reads the "
            "remote reviewers' verdicts"
        )
        return True
    argv = [str(issue), *_passed_through(args, review=True)]
    run, said = _teed(lambda: review_pr.review(argv, pinned_head=head.oid))
    if run.moved_to is not None:
        raise _Stop(
            EXIT_HEAD_MOVED,
            f"review: stopped — PR #{head.pr_number}'s head is {short_sha(run.moved_to)}, "
            f"not {short_sha(head.oid)}, the head whose checks passed; run `land-work {issue}` "
            "again to land the new head",
        )
    if run.failed:
        could_not = "; ".join(f"{name}: {why}" for name, why in run.failed.items())
        raise _Stop(
            EXIT_REVIEW_INCOMPLETE,
            f"review: stopped — a reviewer could not be run, so the review is not "
            f"complete ({could_not}). Run `land-work {issue}` again once it can run",
        )
    if run.exit_code != 0:
        reason = _first_reason(said) or f"review-pr exited {run.exit_code}"
        raise _Stop(EXIT_UNREADABLE, f"review: stopped — {reason}")
    requested = {
        name: body for name, body in run.kept_bodies.items() if run.kept[name] == CHANGES_REQUESTED
    }
    requested.update(
        (name, body) for name, (token, body) in run.posted.items() if token == CHANGES_REQUESTED
    )
    if requested:
        for name, body in requested.items():
            findings = _blocking_findings(body)
            if not findings:
                print(
                    f"  [{name}] CHANGES_REQUESTED with no [block] bullet — read it with "
                    f"`show-pr {head.pr_number} --field review`"
                )
            for finding in findings:
                print(f"  [{name}] {finding}")
        raise _Stop(
            EXIT_STOPPED,
            f"review: changes requested by {', '.join(requested)} — the blocking findings "
            "are above; merge not started",
        )
    kept, ran = len(run.kept), len(run.posted)
    if args.dry_run:
        would = f"run {', '.join(run.would_run)}" if run.would_run else "run none"
        _say(f"review: (dry-run) would keep {kept} fresh and {would}")
        return not run.would_run
    _say(f"review: {kept} kept fresh, {ran} re-run — all approved")
    return True


def _blocking_findings(body: str) -> list[str]:
    """The first line of each `[block]` bullet in a verdict's body."""
    return [
        re.sub(r"^\s*(?:[-*+]|\d+[.)])\s+", "", line).strip()
        for line in body.splitlines()
        if _BLOCK_BULLET.match(line)
    ]


# ---- merge -----------------------------------------------------------------


def _merge(args: argparse.Namespace, head: _Head | None, config: dict[str, Any]) -> int:
    """Hand over to done-work — with the pinned head, or none when there is no
    open PR — and say in one line how it ended."""
    issue = args.issue_number
    argv = [str(issue), *_passed_through(args, review=False)]
    run, said = _teed(
        lambda: (
            done_work.run(argv, merged_only=True)
            if head is None
            else done_work.run(argv, pinned_head=head.oid)
        )
    )
    rc = run.exit_code
    reason = _first_reason(said)
    if args.dry_run:
        _say(
            "merge: (dry-run) done-work's plan is above"
            if rc == EXIT_MERGED
            else f"merge: (dry-run) done-work would stop: {reason or f'exit {rc}'}"
        )
        return rc
    if head is None:
        _say(
            f"merge: #{issue} completed through its merged PR"
            if rc == EXIT_MERGED
            else f"merge: not merged: {reason or f'done-work exited {rc}'}"
        )
        return rc
    number = head.pr_number
    if rc == EXIT_ACCEPTED:
        return _accepted(head, config)
    merged, merge_commit = _merge_state(number, config)
    if merged is True:
        landed = f"merged as {short_sha(merge_commit)}" if merge_commit else "merged"
        if rc == EXIT_MERGED:
            _say(f"merge: {landed}")
            return EXIT_MERGED
        _say(f"merge: {landed}, but not everything after the merge ran: {reason or f'exit {rc}'}")
        return rc
    if rc == EXIT_MERGED:
        if merged is None:
            _say("merge: merged, as done-work reports; the merge commit could not be read")
            return EXIT_MERGED
        _say(f"merge: not merged — done-work returned without merging PR #{number}")
        return EXIT_STOPPED
    verdict = "refused" if rc == EXIT_STOPPED else "not merged"
    _say(f"merge: {verdict}: {reason or f'done-work exited {rc}'}")
    return rc


def _accepted(head: _Head, config: dict[str, Any]) -> int:
    """done-work's 4, said as GitHub now reports the PR."""
    again = f"run `land-work {head.issue}` again once it merges"
    try:
        reading = merge_queue.read(head.pr_number, config)
    except merge_queue.Unreadable:
        reading = None
    if reading is not None and reading.merged:
        _say(
            f"merge: merged meanwhile — run `land-work {head.issue}` again to complete "
            f"#{head.issue}"
        )
    elif reading is not None and reading.queued:
        _say(f"merge: queued — PR #{head.pr_number} {reading.describe()}; {again}")
    else:
        _say(f"merge: unconfirmed — whether PR #{head.pr_number} merged is not known; {again}")
    return EXIT_ACCEPTED


def _merge_state(pr_number: int, config: dict[str, Any]) -> tuple[bool | None, str]:
    """Whether the PR has merged and its merge commit; None when unreadable."""
    try:
        proc = gh_run(
            ["gh", "pr", "view", str(pr_number), "--json", "state,mergeCommit"],
            config,
            check=False,
        )
    except OSError:
        return None, ""
    if proc.returncode != 0:
        return None, ""
    try:
        data = json.loads(proc.stdout)
    except ValueError:
        return None, ""
    if not isinstance(data, dict):
        return None, ""
    commit = data.get("mergeCommit")
    oid = str(commit.get("oid") or "") if isinstance(commit, dict) else ""
    return str(data.get("state") or "").upper() == "MERGED", oid


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


T = TypeVar("T")


class _Tee(io.TextIOBase):
    """A stream that writes through to another and keeps what was written."""

    def __init__(self, stream: TextIO) -> None:
        super().__init__()
        self._stream = stream
        self.kept = io.StringIO()

    def write(self, s: str) -> int:
        self._stream.write(s)
        self.kept.write(s)
        return len(s)

    def flush(self) -> None:
        self._stream.flush()

    def close(self) -> None:
        """Nothing to close: the stream written through is not this one's."""


def _teed(call: Callable[[], T]) -> tuple[T, str]:
    """Run `call`, its standard error shown as it comes and kept to say why it
    stopped."""
    tee = _Tee(sys.stderr)
    with contextlib.redirect_stderr(tee):
        result = call()
    return result, tee.kept.getvalue()


def _first_reason(said: str) -> str:
    """The line another verb opened its refusal or error with."""
    lines = [line.strip() for line in said.splitlines() if line.strip()]
    return next((line for line in lines if line.startswith(_REASON_PREFIXES)), "")


def _say(line: str) -> None:
    sys.stderr.flush()
    print(line, flush=True)


if __name__ == "__main__":
    sys.exit(main())
