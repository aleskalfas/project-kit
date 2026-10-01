"""Shared CI-status gate for the pm merge paths (`merge-pr`, `done-work`).

Both merge scripts must refuse to land a PR whose GitHub checks are red or
still running (the #498 hole: a reviewer APPROVED verdict is not evidence CI
passed — PR #496 merged with a failing check). This module owns the fact-
reduction and the gate verdict so the two call sites share one definition
rather than each re-deriving it.

Two layers, mirroring `src/project_kit/release.py`'s #475 release-merge gate
(the pm scripts are a separate layer from core `src/project_kit`, so the
`summarize_checks` logic is **mirrored here**, not imported — there is no
shared seam to import across that boundary):

  * `summarize_checks(rollup)` — pure reduction of a `statusCheckRollup` to
    (all-passing, non-passing-check-labels). No I/O.
  * `evaluate_ci_gate(rollup)` — the gate verdict (`CiGateResult`): pass, or
    refuse naming the offending checks. The verdict also tells apart the four
    states a head's checks can be in (`CiGateResult.state`) — none reported
    yet, still running, failed, passed — for a reader that waits for them
    (`land-work`, #1203): the merge gate passes a head with no check reported, and
    a reader that waits must not take that for green.

The gh round-trip (`gh pr view --json statusCheckRollup`) stays at the call
site so each script threads its own adopter config through the pm `gh` helper.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# CheckRun conclusions / StatusContext states that count as "not blocking a
# merge". SKIPPED and NEUTRAL are non-failures; everything else that is not
# SUCCESS (a failure, or a still-running/pending check) blocks the merge.
# Mirrors release.py's `_CHECK_PASSING_OUTCOMES`.
_CHECK_PASSING_OUTCOMES = frozenset({"SUCCESS", "NEUTRAL", "SKIPPED"})

# The outcomes of a check that finished without passing. Every other outcome
# that does not pass — IN_PROGRESS, QUEUED, PENDING, WAITING, REQUESTED,
# EXPECTED, or one GitHub adds later — is a check still running, so a reader
# that waits for the checks waits on it rather than call it failed.
_CHECK_FAILED_OUTCOMES = frozenset(
    {"FAILURE", "ERROR", "CANCELLED", "TIMED_OUT", "ACTION_REQUIRED", "STARTUP_FAILURE", "STALE"}
)

# The states a head's checks are in (`CiGateResult.state`).
NO_RUN = "no-run"
RUNNING = "running"
FAILED = "failed"
PASSED = "passed"


@dataclass(frozen=True)
class FailedCheck:
    """A check that finished without passing, and where to read it."""

    name: str
    outcome: str
    #: A CheckRun's `detailsUrl`, a StatusContext's `targetUrl`; empty when
    #: GitHub gives none.
    url: str = ""


@dataclass(frozen=True)
class CiGateResult:
    """The CI gate's verdict on a PR's `statusCheckRollup`.

    `passing` and `failing_checks` are the merge gate's: every check passed,
    or the ones that did not, failed and still running alike. The other
    fields tell those apart for a reader that waits for the checks (`state`).
    """

    passing: bool
    failing_checks: tuple[str, ...] = field(default_factory=tuple)
    #: No check reported at all. The merge gate passes it — a repository that
    #: runs no checks — but it is also what GitHub reports for a head just
    #: pushed, before any check has started, so a reader that waits for the
    #: checks reads it as :data:`NO_RUN`, never as green.
    no_checks: bool = False
    #: The checks that finished without passing.
    failed: tuple[FailedCheck, ...] = field(default_factory=tuple)
    #: The checks still running, labelled as `failing_checks` labels them.
    running: tuple[str, ...] = field(default_factory=tuple)

    @property
    def state(self) -> str:
        """:data:`NO_RUN`; :data:`FAILED` when any check failed, others still
        running or not; :data:`RUNNING`; else :data:`PASSED`."""
        if self.no_checks:
            return NO_RUN
        if self.failed:
            return FAILED
        if self.running:
            return RUNNING
        return PASSED


def _check_identity(check: dict) -> str:
    """The identity a check re-runs under — `name` (CheckRun) / `context` (StatusContext)."""
    return check.get("name") or check.get("context") or "check"


def _check_timestamp(check: dict) -> str:
    """The instant a check's latest run reports, for ordering re-runs.

    A CheckRun carries `completedAt` (terminal) / `startedAt` (running); a
    StatusContext carries `createdAt`. ISO-8601 strings sort chronologically as
    plain strings, so the raw value is enough. Missing ⇒ empty string, which
    sorts first — so a timestamped run always wins over an untimed one, and ties
    (all untimed / equal) fall through to GitHub's roughly-chronological order.
    """
    return check.get("completedAt") or check.get("startedAt") or check.get("createdAt") or ""


def _check_url(check: dict) -> str:
    """Where a check's run can be read — `detailsUrl` (CheckRun) / `targetUrl`
    (StatusContext) — or "" when GitHub gives none."""
    return str(check.get("detailsUrl") or check.get("targetUrl") or "")


def _check_outcome(check: dict) -> str:
    """A check's outcome: a StatusContext's `state`; a CheckRun's `status`
    while it runs, its `conclusion` once completed (PENDING when it has none)."""
    state = str(check.get("state") or "").upper()
    status = str(check.get("status") or "").upper()
    conclusion = str(check.get("conclusion") or "").upper()
    if state:  # StatusContext
        return state
    if status and status != "COMPLETED":  # CheckRun still running/queued
        return status
    return conclusion or "PENDING"  # completed CheckRun


def dedupe_to_latest_run(rollup: list[dict]) -> list[dict]:
    """Collapse a `statusCheckRollup` to the latest run per check identity.

    GitHub retains *every* run of a check in the rollup — so a check that failed
    then re-ran green (a fix-and-repush, a label re-trigger) appears twice, and a
    naive reduction counts the stale FAILURE. This keeps only the latest run per
    identity (by timestamp; ties broken by last-listed, GitHub returning roughly
    chronological), matching how `gh pr checks` reports. Output preserves each
    identity's first-seen order so the reduced failing-check list stays stable.
    """
    latest: dict[str, dict] = {}
    for check in rollup:
        identity = _check_identity(check)
        current = latest.get(identity)
        # `>=` keeps the last-listed on a timestamp tie (chronological input).
        if current is None or _check_timestamp(check) >= _check_timestamp(current):
            latest[identity] = check
    return list(latest.values())


def summarize_checks(rollup: list[dict] | None) -> tuple[bool, tuple[str, ...]]:
    """Reduce a `statusCheckRollup` to (all-passing, non-passing-check-labels).

    Handles both node shapes GitHub returns: a CheckRun carries `status`
    (COMPLETED / IN_PROGRESS / QUEUED) + `conclusion` (SUCCESS / FAILURE / …);
    a StatusContext carries `state` (SUCCESS / FAILURE / PENDING / ERROR). A
    check passes only when its outcome is a non-failing terminal one; a
    still-running check blocks (a PR must be green before merging). An empty
    rollup (no checks configured) is treated as passing.

    The rollup is first deduped to the latest run per check identity
    (`dedupe_to_latest_run`) — GitHub keeps stale runs, so a check that failed
    then re-ran green would otherwise wrongly block the merge (#504).

    Mirrors `src/project_kit/release.py:summarize_checks` — kept in lockstep
    by intent, not by import (cross-layer boundary; see the module docstring).
    """
    failing: list[str] = []
    for check in dedupe_to_latest_run(rollup or []):
        outcome = _check_outcome(check)
        if outcome not in _CHECK_PASSING_OUTCOMES:
            failing.append(f"{_check_identity(check)} ({outcome})")
    return (not failing, tuple(failing))


def evaluate_ci_gate(rollup: list[dict] | None) -> CiGateResult:
    """Decide whether a PR's CI status permits a merge — pure, no I/O.

    A green (or check-free) rollup passes; any failing or still-pending check
    refuses, naming the offending checks so the operator sees exactly what
    blocks. The caller decides how a `--bypass` overrides a refusal.

    The verdict also separates a rollup with no check at all, the checks that
    failed and those still running (`CiGateResult.state`), each read off the
    same latest run per check the gate judges.
    """
    passing, failing = summarize_checks(rollup)
    failed: list[FailedCheck] = []
    running: list[str] = []
    for check in dedupe_to_latest_run(rollup or []):
        outcome = _check_outcome(check)
        if outcome in _CHECK_PASSING_OUTCOMES:
            continue
        name = _check_identity(check)
        if outcome in _CHECK_FAILED_OUTCOMES:
            failed.append(FailedCheck(name, outcome, _check_url(check)))
        else:
            running.append(f"{name} ({outcome})")
    return CiGateResult(
        passing=passing,
        failing_checks=failing,
        no_checks=not rollup,
        failed=tuple(failed),
        running=tuple(running),
    )
