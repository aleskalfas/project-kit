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


def summarize_checks(rollup: list[dict] | None) -> tuple[bool, tuple[str, ...]]:
    """Reduce a `statusCheckRollup` to (all-passing, non-passing-check-labels).

    Handles both node shapes GitHub returns: a CheckRun carries `status`
    (COMPLETED / IN_PROGRESS / QUEUED) + `conclusion` (SUCCESS / FAILURE / …);
    a StatusContext carries `state` (SUCCESS / FAILURE / PENDING / ERROR). A
    check passes only when its outcome is a non-failing terminal one; a
    still-running check blocks (a PR must be green before merging). An empty
    rollup (no checks configured) is treated as passing.

    Mirrors `src/project_kit/release.py:summarize_checks` — kept in lockstep
    by intent, not by import (cross-layer boundary; see the module docstring).
    """
    failing: list[str] = []
    for check in rollup or []:
        name = check.get("name") or check.get("context") or "check"
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
