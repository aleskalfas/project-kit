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
    refuse naming the offending checks.

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


@dataclass(frozen=True)
class CiGateResult:
    """The CI gate's verdict on a PR's `statusCheckRollup`."""

    passing: bool
    failing_checks: tuple[str, ...] = field(default_factory=tuple)


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
    return (
        check.get("completedAt")
        or check.get("startedAt")
        or check.get("createdAt")
        or ""
    )


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
        name = _check_identity(check)
        state = str(check.get("state") or "").upper()
        status = str(check.get("status") or "").upper()
        conclusion = str(check.get("conclusion") or "").upper()
        if state:  # StatusContext
            outcome = state
        elif status and status != "COMPLETED":  # CheckRun still running/queued
            outcome = status
        else:  # completed CheckRun
            outcome = conclusion or "PENDING"
        if outcome not in _CHECK_PASSING_OUTCOMES:
            failing.append(f"{name} ({outcome})")
    return (not failing, tuple(failing))


def evaluate_ci_gate(rollup: list[dict] | None) -> CiGateResult:
    """Decide whether a PR's CI status permits a merge — pure, no I/O.

    A green (or check-free) rollup passes; any failing or still-pending check
    refuses, naming the offending checks so the operator sees exactly what
    blocks. The caller decides how a `--bypass` overrides a refusal.
    """
    passing, failing = summarize_checks(rollup)
    return CiGateResult(passing=passing, failing_checks=failing)
