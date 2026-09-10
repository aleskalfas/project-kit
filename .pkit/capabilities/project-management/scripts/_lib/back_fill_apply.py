"""Corpus back-fill — the apply engine (T2b, DEC-037 §2 / ADR-031 §5).

The **highest-blast-radius** operation the capability performs: it mutates
hundreds of real, human-owned issues. The report half (T2a, ``back-fill.py``)
enumerates a plan; this module turns the reviewed plan into writes — or, in
``--emit-script`` mode, into a script the adopter runs themselves. The whole
point is the four safety properties (DEC-037 §2; recast as write-path
invariants in ADR-031 §5): without them, applying a stale plan blind-overwrites
concurrently-edited issues. With them, the apply is auditable and recoverable.

This module holds the parts that must be independently testable in isolation —
the **re-validate-at-apply / value-equality predicates**, the **apply loop**,
the **failure-summary / exit-code computation**, and the **emit-script
renderer**. ``back-fill.py`` wires these into the ``--apply`` / ``--emit-script``
modes and supplies the fresh per-issue state reads. Keeping the predicates here
(not buried in ``main``) is what makes them mutation-testable: a test can drive
:func:`classify_change` over hand-built (target, fresh-read) pairs and prove the
drift / idempotency boundary directly.

The four safety properties, and where each lives
------------------------------------------------
1. **Re-validate at apply (skip + report drift).** The plan enumerated state at
   plan time; humans may have edited issues since. Before each write, the caller
   re-reads *that issue's current state* (a :class:`FreshState`) and passes it in;
   :func:`classify_change` compares the plan's enumerated ``observed`` against the
   fresh read. If they differ, the change is ``DRIFTED`` → **skip + report**,
   never overwrite against stale enumeration. The plan's ``observed`` /
   ``prediction`` are NOT trusted as the write decision — they are re-derived here
   against the fresh read (T2a deliberately shaped the plan so this is mandatory).
2. **Per-issue value-equality idempotency.** "Already done" = the fresh-read
   current value already equals the target. Those are ``ALREADY_SATISFIED`` →
   skip. A re-run after a partial apply is a no-op for already-applied issues and
   completes the rest (partial-apply recoverable), because the predicate keys on
   the *current* value, not on any applied-state bookkeeping.
3. **Residual-pre-check gate.** Enforced by ``back-fill.py`` (it owns the plan +
   gate); this module's :func:`refuse_if_gate_failed` is the consume-a-saved-plan
   form — honor the plan's ``residual_pre_check.passed``.
4. **``--emit-script`` (draft-not-apply).** :func:`render_emit_script` emits the
   reviewed mutations as an idempotent shell script the adopter runs themselves.
   The script **re-checks value-equality itself** before each write, so it is
   safe to re-run — pm never touches the corpus in this mode.

Failure posture — audited skip/report (ADR-031 §6)
--------------------------------------------------
The bulk driver imposes the stricter **audited skip/report** posture, NOT
DEC-024's per-event report-and-continue-exit-0. On a write failure: record it in
the audit, continue the loop, and surface a summary (applied / skipped-idempotent
/ skipped-drift / blocked / failed). :func:`exit_code_for` returns non-zero when
any write failed, so the operator knows — a bulk apply that silently swallowed
failures would defeat the audit.

Construction routes through the seam (ADR-031)
----------------------------------------------
Every executed *non-label* write goes through ``_lib.substrate_writes`` executing
forms (``write_field_value`` / ``write_milestone``). This module NEVER
string-builds one of those — the sole-constructor guard
(``test_pm_substrate_write_seam``) covers it. The plan's ``argv`` is used only for
*display* and for the emit-script (where it is the exact reviewed write, rendered
verbatim, not re-derived).

The third kind is a LABEL write, and its seam is a different one
-----------------------------------------------------------------
``set-axis-label`` (the corpus-repair kind, #818) writes a classification axis's
value as a **label**. ADR-031's seam is *non-label by charter* — it owns the
Projects-v2 field value and the milestone — so the label write does not belong
there. The seam that governs a label write is ADR-026's: the label *string* is
produced only by ``axis_labels.resolve_write``, at plan time, in ``back-fill.py``.
By the time a ``PlannedChange`` reaches this module the substrate value is already
resolved (``change.target``), and what is left is the ``gh issue edit --add-label``
argv, constructed once here (:func:`axis_label_args`) and consumed by both the
plan and the apply so the two cannot desync. This module never composes an
``<axis>:<value>`` label itself — doing so would route around ADR-026's sole
constructor, which is exactly the unmanaged-label failure the substrate design
exists to prevent.
"""

from __future__ import annotations

import json
import shlex
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any

# Sibling seam — the sole constructor / executor of covered substrate writes
# (ADR-031). Imported the resilient way the other _lib modules are, so a test
# that loads this module by file path still resolves it.
try:
    import substrate_writes  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover
    from _lib import substrate_writes  # type: ignore[no-redef]

# ADR-026's label seam. Used here for ONE thing — the `<axis>:` prefix the emitted
# guard tests against. Asking the seam for it rather than spelling `f"{axis}:"`
# keeps the prefix's definition in the single place that owns it; a second spelling
# is how the two sides of a substrate question start to disagree.
try:
    import axis_labels  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover
    from _lib import axis_labels  # type: ignore[no-redef]

# The gh shell-out helper (adopter host/owner pinned per DEC-023). Imported the
# same defensive way `substrate_writes` imports it, for the one write this module
# executes itself: the label write, which ADR-031's non-label seam does not own.
try:
    from gh import gh_run  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover
    try:
        from _lib.gh import gh_run  # type: ignore[no-redef]
    except ImportError:  # pragma: no cover
        gh_run = None  # type: ignore[assignment]


# The plan schema_version this engine consumes. Pinned so a saved plan produced
# by a future, incompatible report half is refused rather than mis-applied
# (DEC-037 §2 — applying against a plan whose shape you misread is exactly the
# blind-overwrite failure mode the audit exists to rule out).
#
# NOT bumped by the `set-axis-label` kind (#818): every addition that kind makes
# to the plan document is *additive and optional* — new keys on the intent and
# proposed entries, and a new `kind` value. A plan saved by the two-kind engine is
# read by this one unchanged (the new keys read as absent), which is why refusing
# every previously-saved plan on upgrade would cost an adopter something and buy
# nothing. The residual exposure is the reverse direction — a plan saved HERE and
# applied by an older engine, which filters unknown kinds and would silently apply
# only the other two. That is an exotic downgrade-then-apply path against an
# ephemeral review artifact; bumping to close it would break the common path.
CONSUMED_PLAN_SCHEMA_VERSION = 1

# The kinds the back-fill can apply, and where each one's intent is DECLARED.
#
#   * the two hook-driven kinds read their write parameters from an
#     `after_create_issue` hook entry (DEC-037 §4) — the map cannot carry a
#     field-id / option-id / milestone-title;
#   * `set-axis-label` reads its value from the substrate-map's per-axis
#     `default:`, which DEC-037 §3 names as the single declaration point for a
#     LABEL-bound axis ("the default is the value the seam emits").
#
# The split is the substrate's, not an inconsistency: DEC-037 §3 is explicit that
# the declaration point differs by substrate kind.
HOOK_DRIVEN_KINDS: tuple[str, ...] = ("set-board-field", "assign-milestone")
SET_AXIS_LABEL_KIND = "set-axis-label"
APPLIABLE_KINDS: tuple[str, ...] = (*HOOK_DRIVEN_KINDS, SET_AXIS_LABEL_KIND)


# ----- classification: the re-validate / idempotency predicates ------------


class Disposition(str, Enum):  # noqa: UP042 — StrEnum is 3.11+; this script targets >=3.10 (PEP 723 header)
    """What the apply loop should do with one proposed change, re-derived at
    apply time against a FRESH per-issue read (never the plan's stale annotation).

    The ordering of checks in :func:`classify_change` is deliberate and is itself
    a safety property: BLOCKED and DRIFTED are evaluated before ALREADY_SATISFIED
    and WOULD_WRITE, so a change that cannot be applied (no argv) or whose issue
    drifted is never mistaken for an idempotent no-op or a clean write.
    """

    ALREADY_SATISFIED = "already-satisfied"  # fresh current == target → skip (idempotent)
    DRIFTED = "drifted"                       # fresh current != plan.observed → skip + report
    WOULD_WRITE = "would-write"               # fresh current differs from target, no drift → write
    BLOCKED = "blocked"                       # the plan could not construct a write (no argv)


@dataclass(frozen=True)
class FreshState:
    """The freshly-read current value of the target attribute for one issue.

    Read by the caller (``back-fill.py``) *immediately before* the write decision
    — this is the re-validate-at-apply read (DEC-037 §2). ``current`` is the value
    the attribute holds *right now* (the milestone title now on the issue; the
    single-select option-id / text now on the board field), or ``None`` when the
    attribute is unset. ``read_ok`` is False when the fresh read itself failed
    (gh error / indeterminate) — an indeterminate read fails CLOSED to a skip, the
    write-path analogue of ADR-026's fail-closed: never overwrite when we could not
    confirm the current state.
    """

    current: str | None
    read_ok: bool = True


@dataclass(frozen=True)
class PlannedChange:
    """One proposed change as consumed from the plan (T2a's ``proposed[]`` entry).

    Carries exactly the fields the apply decision needs. ``observed`` is the value
    the PLAN enumerated at plan time — used ONLY to detect drift against the fresh
    read, never as the write decision itself. ``target`` is the value the write
    would set (the milestone title; the single-select option-id or text). ``argv``
    is the exact constructed write (or ``None`` when the plan blocked it).
    """

    issue_number: int
    kind: str                 # one of APPLIABLE_KINDS
    target: str | None        # the value the write sets; None only when blocked upstream
    observed: str | None      # the plan-time enumerated value (drift reference only)
    argv: list[str] | None    # the exact reviewed write, or None when blocked
    citation: str = ""
    blocked_reason: str = ""
    # Field-value writes need these to drive the seam executor at apply time;
    # absent for milestone writes.
    item_id: str | None = None
    field_id: str | None = None
    project_id: str | None = None
    single_select_option_id: str | None = None
    text_value: str | None = None
    # `set-axis-label` writes only: which classification axis this change carries,
    # and the adopter's own label names for it. `carrier_labels` is the plan-time
    # snapshot of `axis_labels.axis_label_vocabulary` — the remapped values ONLY;
    # the kit's `<axis>:` labels are a prefix rather than a set and the guard tests
    # them as one. It travels in the plan because the EMITTED script has no way to
    # load a map (see `_axis_label_guarded_fragment`); `--apply` asks the live map.
    axis: str | None = None
    carrier_labels: tuple[str, ...] = ()


def classify_change(change: PlannedChange, fresh: FreshState) -> Disposition:
    """Re-derive the apply decision for one change against a FRESH read.

    This is the load-bearing predicate — the place properties 1 and 2 live. It is
    pure (no I/O) so it can be mutation-tested directly. The check order encodes
    the safety priority:

      1. **BLOCKED** — the plan never constructed a write (no ``argv``). Nothing to
         apply; surfaced as blocked, never silently dropped.
      2. **indeterminate fresh read → DRIFTED** — if the re-validate read failed we
         cannot confirm the current state, so we fail closed to skip (treated as
         drift for reporting). Never overwrite against an unknown current value.
      3. **ALREADY_SATISFIED** — the fresh current already equals the target. This
         is value-equality idempotency (property 2): skip. A re-run after a partial
         apply lands here for the issues already written.
      4. **DRIFTED** — the fresh current differs from what the plan enumerated
         (``observed``). A human edited the issue since plan time; the plan is
         stale for this issue. Skip + report (property 1) — never overwrite against
         stale enumeration.
      5. **WOULD_WRITE** — fresh current differs from target AND matches the plan's
         enumeration (no drift). The clean case: apply.

    Note the ALREADY_SATISFIED-before-DRIFTED ordering: if a human concurrently set
    the field to *exactly the target value*, that is not a write we need to fight
    over — it is already done, idempotent, regardless of what the plan enumerated.
    Only a drift to some *other* value blocks the write.

    This predicate is NOT widened for ``set-axis-label``'s stricter "only ever fill
    a gap, never replace a value" rule, and that is the point. The label kind
    proposes a change only for an issue carrying no value on the axis, so its
    ``observed`` is always ``None`` — and this predicate then yields exactly the
    stricter behaviour on its own: a value that appeared since plan time is either
    the target (ALREADY_SATISFIED) or something else (DRIFTED), and both skip. One
    guard, three kinds; a second drift predicate beside this one would be the drift
    it exists to prevent.
    """
    if change.argv is None:
        return Disposition.BLOCKED
    if not fresh.read_ok:
        # Could not confirm current state → fail closed to skip (reported as drift).
        return Disposition.DRIFTED
    if fresh.current == change.target:
        return Disposition.ALREADY_SATISFIED
    if fresh.current != change.observed:
        # The issue moved since plan time (and not to the target) — stale plan.
        return Disposition.DRIFTED
    return Disposition.WOULD_WRITE


# ----- the apply loop ------------------------------------------------------


class ApplyOutcome(str, Enum):  # noqa: UP042 — StrEnum is 3.11+; this script targets >=3.10 (PEP 723 header)
    """The recorded outcome of one change after the apply loop handled it."""

    APPLIED = "applied"
    SKIPPED_IDEMPOTENT = "skipped-idempotent"
    SKIPPED_DRIFT = "skipped-drift"
    BLOCKED = "blocked"
    FAILED = "failed"


@dataclass
class ApplyRecord:
    """One line of the apply audit — what happened to one change, and why."""

    issue_number: int
    kind: str
    outcome: ApplyOutcome
    detail: str = ""


# A fresh-read function: given a PlannedChange, return the issue's current value
# for that change's attribute. Injected by back-fill.py (it owns the gh reads);
# parameterised here so the loop is testable with a stub reader.
FreshReader = Callable[[PlannedChange], FreshState]


def apply_plan(
    changes: list[PlannedChange],
    config: dict[str, Any],
    *,
    read_fresh: FreshReader,
) -> list[ApplyRecord]:
    """Drive the reviewed plan to writes under the audited skip/report posture.

    For each change: re-read the issue's current state (``read_fresh``), classify
    against it (:func:`classify_change`), and act:

      * BLOCKED            → record blocked, no write;
      * ALREADY_SATISFIED  → record skipped-idempotent, no write;
      * DRIFTED            → record skipped-drift, no write (NEVER overwrite);
      * WOULD_WRITE        → execute through the seam; record applied or failed.

    On a write failure the loop **records and continues** (audited skip/report,
    ADR-031 §6) — it does not abort the remaining corpus, because a half-applied
    corpus that stopped at the first failure is worse than one that applied every
    write it could and reported the rest. The non-zero exit comes from
    :func:`exit_code_for` over the returned records, so the operator still learns a
    write failed.
    """
    records: list[ApplyRecord] = []
    for change in changes:
        try:
            fresh = read_fresh(change)
        except Exception as exc:  # noqa: BLE001 — a single bad read must not abort the corpus
            # A fresh read that throws is treated as an indeterminate read for THIS
            # issue: fail closed to an audited skip (never overwrite against an
            # unconfirmed value), and continue the loop — a half-applied corpus that
            # aborts at one bad read is worse than one that skips it and reports.
            records.append(ApplyRecord(
                change.issue_number, change.kind, ApplyOutcome.SKIPPED_DRIFT,
                _drift_detail(change, FreshState(current=None, read_ok=False))
                + f" (fresh read raised: {exc})",
            ))
            continue
        disposition = classify_change(change, fresh)

        if disposition is Disposition.BLOCKED:
            records.append(ApplyRecord(
                change.issue_number, change.kind, ApplyOutcome.BLOCKED,
                change.blocked_reason or "no write could be constructed for this change",
            ))
            continue
        if disposition is Disposition.ALREADY_SATISFIED:
            records.append(ApplyRecord(
                change.issue_number, change.kind, ApplyOutcome.SKIPPED_IDEMPOTENT,
                f"already equals target {change.target!r}",
            ))
            continue
        if disposition is Disposition.DRIFTED:
            records.append(ApplyRecord(
                change.issue_number, change.kind, ApplyOutcome.SKIPPED_DRIFT,
                _drift_detail(change, fresh),
            ))
            continue

        # WOULD_WRITE — execute through the sole constructor (ADR-031).
        records.append(_execute_change(change, config))
    return records


def _execute_change(change: PlannedChange, config: dict[str, Any]) -> ApplyRecord:
    """Execute one WOULD_WRITE change through its substrate's write path.

    Routes by kind: the two non-label kinds go to ``substrate_writes``' executing
    forms and are never string-built here (ADR-031); the label kind goes to
    :func:`write_axis_label`, whose argv has its own single construction point in
    this module and whose label VALUE was resolved by ADR-026's seam at plan time.
    Each returns a failure-posture-neutral result; THIS is the layer that imposes
    the back-fill's posture on it (record applied on ok, failed on not-ok; never
    raise, never abort the loop).
    """
    if change.kind == "assign-milestone":
        result = substrate_writes.write_milestone(
            config, issue_number=change.issue_number, title=change.target or "",
        )
    elif change.kind == "set-board-field":
        result = substrate_writes.write_field_value(
            config,
            item_id=change.item_id or "",
            field_id=change.field_id or "",
            project_id=change.project_id or "",
            single_select_option_id=change.single_select_option_id,
            text_value=change.text_value,
        )
    elif change.kind == SET_AXIS_LABEL_KIND:
        result = write_axis_label(
            config, issue_number=change.issue_number, label=change.target or "",
        )
    else:  # pragma: no cover — kinds are constrained upstream to the covered ones
        return ApplyRecord(
            change.issue_number, change.kind, ApplyOutcome.FAILED,
            f"unknown back-fill kind {change.kind!r}",
        )

    if result.ok:
        return ApplyRecord(
            change.issue_number, change.kind, ApplyOutcome.APPLIED, result.detail,
        )
    return ApplyRecord(
        change.issue_number, change.kind, ApplyOutcome.FAILED,
        result.error or result.detail or "write failed",
    )


# ----- the label write (ADR-026's substrate, not ADR-031's) ----------------


@dataclass(frozen=True)
class LabelWriteResult:
    """Outcome of one axis-label write — the neutral carrier for the third kind.

    Deliberately NOT ``substrate_writes.SubstrateWriteResult``: that type belongs
    to ADR-031's *non-label* contract, and reusing it here would quietly file a
    label write under a seam whose charter excludes it. It carries the same three
    fields ``_execute_change``'s shared tail reads (``ok`` / ``detail`` /
    ``error``), so the tail treats all three kinds alike, and it is
    failure-posture-neutral for the same reason its sibling is: it records what
    happened, and the apply loop decides what that means.
    """

    ok: bool
    detail: str = ""
    error: str = ""


def axis_label_args(*, issue_number: int | str, label: str) -> list[str]:
    """Construct the ``gh issue edit <n> --add-label <label>`` argv.

    The one construction point for the ``set-axis-label`` write, consumed by BOTH
    the plan (``back-fill.py`` renders it as the reviewed argv) and the apply
    (:func:`write_axis_label` re-derives it at write time), so what the human
    reviewed and what runs cannot drift apart.

    ``label`` is the **already-resolved substrate value** — whatever
    ``axis_labels.resolve_write`` returned for this (axis, value) under the
    adopter's map. This function neither composes nor validates a label name: a
    label it was not handed is a label it must not invent (ADR-026 part (i)).

    ``--add-label`` and not a remove-then-add: the change kind proposes ONLY for
    issues carrying no value on the axis (the no-overwrite rule lives at
    enumeration), so there is never a stale value of this axis to strip. That is
    what distinguishes this from ``set-field``'s label surgery, which is a
    deliberate re-set and therefore does remove the stale label.
    """
    return ["gh", "issue", "edit", str(issue_number), "--add-label", label]


def write_axis_label(
    config: dict[str, Any], *, issue_number: int | str, label: str
) -> LabelWriteResult:
    """Construct AND execute one axis-label write; return the neutral result.

    Never raises on a failed write — a non-zero ``gh`` exit (or a missing binary)
    yields ``ok=False`` with the stderr in ``error``, for the apply loop's audited
    skip/report posture to act on (ADR-031 §6's posture, applied to the label
    substrate).
    """
    args = axis_label_args(issue_number=issue_number, label=label)
    try:
        proc = _gh_call(args, config)
    except FileNotFoundError:
        return LabelWriteResult(
            ok=False,
            detail="gh issue edit --add-label failed: `gh` not on PATH",
            error="`gh` not on PATH",
        )
    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip() or "no stderr"
        return LabelWriteResult(
            ok=False,
            detail=f"gh issue edit --add-label failed: {stderr}",
            error=stderr,
        )
    return LabelWriteResult(ok=True, detail=f"added label {label!r} to #{issue_number}")


def _gh_call(args: list[str], config: dict[str, Any]) -> Any:
    """Call ``gh`` through the helper (DEC-023 host/owner pinning).

    Mirrors ``substrate_writes._gh_call``, including its direct-subprocess
    fallback for the import contexts where the helper is unreachable, so the label
    write's execution path matches the non-label ones.
    """
    if gh_run is not None:
        return gh_run(args, config, check=False)
    return subprocess.run(args, capture_output=True, text=True, check=False)


def _drift_detail(change: PlannedChange, fresh: FreshState) -> str:
    if not fresh.read_ok:
        return (
            "could not re-read current state at apply time — failing closed to "
            "skip (never overwrite against an unconfirmed value)"
        )
    return (
        f"issue drifted since plan time: plan enumerated {change.observed!r}, "
        f"current is {fresh.current!r} (target {change.target!r}); skipping to "
        "avoid overwriting a concurrent edit"
    )


# ----- failure summary / exit code -----------------------------------------


@dataclass(frozen=True)
class ApplySummary:
    """Counts per outcome, for the summary line and the exit code."""

    applied: int
    skipped_idempotent: int
    skipped_drift: int
    blocked: int
    failed: int

    @property
    def any_failed(self) -> bool:
        return self.failed > 0


def summarise(records: list[ApplyRecord]) -> ApplySummary:
    """Tally the apply records into per-outcome counts."""
    def count(outcome: ApplyOutcome) -> int:
        return sum(1 for r in records if r.outcome is outcome)

    return ApplySummary(
        applied=count(ApplyOutcome.APPLIED),
        skipped_idempotent=count(ApplyOutcome.SKIPPED_IDEMPOTENT),
        skipped_drift=count(ApplyOutcome.SKIPPED_DRIFT),
        blocked=count(ApplyOutcome.BLOCKED),
        failed=count(ApplyOutcome.FAILED),
    )


def exit_code_for(summary: ApplySummary) -> int:
    """The apply exit code: non-zero iff any write FAILED (ADR-031 §6).

    Skips (idempotent / drift) and blocks are NOT failures — they are the audited
    skip/report posture working as designed, and a clean re-run / a concurrently-
    edited corpus must not look like an error. Only an actual write failure
    (a non-zero ``gh`` exit) surfaces a non-zero code, so the operator knows a
    mutation they expected did not land.
    """
    return 1 if summary.any_failed else 0


# ----- --emit-script: the draft-not-apply form -----------------------------


_EMIT_SCRIPT_HEADER = """\
#!/usr/bin/env bash
# Corpus back-fill — emitted apply script (DEC-037 §2 --emit-script,
# the draft-not-apply form). pm did NOT touch your corpus; you run this.
#
# IDEMPOTENT BY RE-CHECK: each write below re-reads the issue's current value
# before writing, on EVERY substrate — the milestone write re-reads the issue's
# milestone, the board-field write re-reads the field value via GraphQL, and the
# axis-label write re-reads the issue's labels. Each skips when the current value
# already equals the target (idempotent) AND skips when the current value is some
# OTHER non-target value (a concurrent edit / drift), never overwriting it. So this
# script is safe to re-run, and a re-run after a partial apply completes only the
# rest.
#
# WHAT A *FAILED* RE-READ DOES DIFFERS BY SUBSTRATE, and the difference is a known
# defect rather than a design:
#
#   * milestone + board-field — FAILS OPEN ON A FAILED RE-READ. The guards above
#     only protect a SUCCESSFUL re-read. If the re-read itself FAILS (a `gh` error /
#     rate-limit / network drop), the current value reads as empty and
#     the write RUNS — even if the attribute actually holds a concurrent human
#     edit the failed read could not see. Filed as a defect (#816), ruled to raise.
#   * axis-label — FAILS CLOSED: a failed re-read SKIPS the write, matching
#     `--apply`. It is the newer guard and deliberately does not copy the shape
#     above.
#
# `pm back-fill --apply` is the drift-safe path on every substrate: it fails CLOSED
# on an indeterminate read (skips rather than overwrites a value it could not
# confirm).
#
# It also does NOT re-validate against the plan's enumerated `observed` the way
# `pm back-fill --apply` does (that drift check needs pm's plan and is strictly
# stronger) — prefer `--apply` when the corpus may have changed materially since
# the plan was drafted; review before running either way.
set -euo pipefail
"""


def render_emit_script(
    changes: list[PlannedChange],
    *,
    truncated: bool = False,
) -> str:
    """Render the reviewed mutations as an idempotent re-checking shell script.

    The symmetric draft-not-apply form (DEC-037 §2 property 4): instead of pm
    applying, it emits a script the adopter runs at their chosen moment. THE
    SCRIPT EXECUTES NO WRITE FROM THIS PROCESS — it is text. Two guarantees the
    emitted script itself carries:

      * **idempotent + drift-safe** — BOTH substrates are guarded by a fresh
        value-read: the milestone write re-reads the issue's milestone, and the
        board-field write re-reads the field value (the same GraphQL field-values
        query ``--apply`` uses). Each skips when the current value already equals
        the target (idempotent) and skips — never overwrites — when it is some other
        non-target value (a concurrent human edit). Re-running is a no-op for
        already-applied issues and completes the rest (property 2 in the script);
      * **uses the plan's exact reviewed argv** — each write renders the plan's
        ``argv`` verbatim (``shlex.quote``-d), so what runs is exactly what the
        human reviewed, not a re-derivation.

    Blocked changes (no argv) are emitted as commented-out lines noting why, so the
    adopter sees them without the script trying to run a write that has no
    target. ``truncated`` emits a loud banner that the plan covered only a subset
    of the corpus.
    """
    lines: list[str] = [_EMIT_SCRIPT_HEADER]
    if truncated:
        lines.append(
            'echo "!! WARNING: the plan was TRUNCATED — this script covers only '
            'the planned subset of the corpus, not every issue." >&2'
        )
        lines.append("")

    for change in changes:
        lines.append(_emit_one(change))
    lines.append("")
    lines.append('echo "back-fill emit-script complete." >&2')
    return "\n".join(lines) + "\n"


def _emit_one(change: PlannedChange) -> str:
    """Render one change as an idempotent, value-re-checking script fragment."""
    if change.argv is None:
        return (
            f"# [blocked] #{change.issue_number} {change.kind}: "
            f"{change.blocked_reason or 'no write could be constructed'} — skipped."
        )
    quoted = " ".join(shlex.quote(token) for token in change.argv)
    cite = f"  # cite: {change.citation}" if change.citation else ""

    if change.kind == "set-board-field":
        # The field write carries its OWN guard, symmetric with the milestone one
        # (R2): re-read the current board-field value and skip both the idempotent
        # case (already the target) AND the drift case (a concurrent edit to some
        # other value) — never blind-overwrite a human's concurrent edit. This
        # mirrors `--apply`'s drift-skip on the same substrate.
        return _field_guarded_fragment(change, quoted, cite)

    if change.kind == SET_AXIS_LABEL_KIND:
        return _axis_label_guarded_fragment(change, quoted, cite)

    guard = _milestone_guard(change)
    return (
        f"# #{change.issue_number} {change.kind}{cite}\n"
        f"{guard}\n"
        f"  {quoted}\n"
        f"else\n"
        f'  echo "skip #{change.issue_number} {change.kind}: already satisfied" >&2\n'
        f"fi"
    )


def _milestone_guard(change: PlannedChange) -> str:
    """A bash guard that runs the milestone write only if the issue's current
    milestone differs from the target (idempotent re-check)."""
    target = change.target or ""
    return (
        f'current=$(gh issue view {change.issue_number} '
        f'--json milestone --jq ".milestone.title // \\"\\"" 2>/dev/null || echo "")\n'
        f'if [ "$current" != {shlex.quote(target)} ]; then'
    )


# The GraphQL field-values re-read — the SINGLE source of truth for this query,
# consumed by BOTH read surfaces so they can never silently desync:
#   * the emit-script field guard embeds it (`_field_guarded_fragment` below), and
#   * the `--apply` path's fresh read issues it (`_read_current_field_value` in
#     back-fill.py imports THIS constant — not a copied literal).
# Both re-check the board field identically because both read the same string.
# `--jq` extracts the matching field's optionId-or-text in one bash line.
FIELD_REREAD_QUERY = (
    "query($item: ID!) { node(id: $item) { ... on ProjectV2Item { "
    "fieldValues(first: 50) { nodes { "
    "... on ProjectV2ItemFieldSingleSelectValue { optionId "
    "field { ... on ProjectV2FieldCommon { id } } } "
    "... on ProjectV2ItemFieldTextValue { text "
    "field { ... on ProjectV2FieldCommon { id } } } } } } } }"
)


def _field_guarded_fragment(change: PlannedChange, quoted: str, cite: str) -> str:
    """A bash fragment that re-reads the board field and writes only on the clean
    no-drift case — symmetric with the milestone guard (R2).

    Three-way, mirroring ``--apply``'s ``classify_change``:
      * current == target          → idempotent, skip (echo);
      * current non-empty & != target → DRIFT (a concurrent edit), skip + echo —
        never overwrite (this is what an unguarded ``item-edit`` got wrong);
      * current empty / unset       → run the reviewed ``item-edit`` write.

    The re-read uses the same GraphQL field-values query the apply path uses; the
    ``--jq`` selects the value of the field whose id matches this change's field.
    If the GraphQL read itself fails (empty ``current``), the field is treated as
    unset and the write runs — the same posture as the report-time enumeration; the
    drift-safe ``--apply`` path remains the stronger option and the header says so.
    """
    target = change.target or ""
    field_id = change.field_id or ""
    item_id = change.item_id or ""
    # --jq: from the field-values nodes, pick the one whose field id == this field,
    # emit its optionId or text; default empty when absent/unreadable. The leading
    # `?` keeps a transient null `data`/`node`/`fieldValues` from raising a jq error
    # (it yields empty → treated as unset), so a rate-limited re-read degrades to the
    # same "field unset" posture as a failed read rather than aborting the script.
    # The field id is embedded as a JSON string literal (`json.dumps`), NOT shell-
    # quoted — jq needs a quoted string literal in `== "<id>"`, and json.dumps gives
    # exactly that (and escapes any quote in the id); the whole jq program is then
    # shell-quoted as one token below.
    jq = (
        f'(.data.node.fieldValues.nodes? // [])'
        f' | map(select(.field.id == {json.dumps(field_id)}))'
        f' | (.[0].optionId // .[0].text // "")'
    )
    reread = (
        f"current=$(gh api graphql "
        f"-f query={shlex.quote(FIELD_REREAD_QUERY)} "
        f"-F item={shlex.quote(item_id)} "
        f"--jq {shlex.quote(jq)} 2>/dev/null || echo \"\")"
    )
    return (
        f"# #{change.issue_number} {change.kind}{cite}\n"
        f"# guard fails OPEN: a FAILED re-read reads empty and the write runs "
        f"below (use pm back-fill --apply for the drift-safe, fail-closed read).\n"
        f"{reread}\n"
        f'if [ "$current" = {shlex.quote(target)} ]; then\n'
        f'  echo "skip #{change.issue_number} {change.kind}: already satisfied" >&2\n'
        f'elif [ -n "$current" ]; then\n'
        f'  echo "skip #{change.issue_number} {change.kind}: DRIFT — current '
        f'value is $current, not the planned target; not overwriting a '
        f'concurrent edit (use pm back-fill --apply for the drift-safe path)" '
        f">&2\n"
        f"else\n"
        f"  {quoted}\n"
        f"fi"
    )


def _axis_label_carrier_jq(axis_prefix: str, carrier_labels: tuple[str, ...]) -> str:
    """A jq program selecting the first label on the issue that carries the axis.

    Mirrors ``axis_labels.carried_labels``' rule exactly — the UNION of the kit's
    own ``<axis>:`` prefix and the adopter's remapped vocabulary — because the same
    rule has to hold on both apply paths. ``--apply`` gets it by calling the seam;
    a static shell script cannot, so the vocabulary travels in the plan and this
    renders it. Emits ``""`` when the issue carries no value for the axis, which is
    the only case the guard below lets through to a write.

    The prefix and each vocabulary entry are embedded as JSON string literals
    (``json.dumps``) — jq needs quoted literals here, and json.dumps escapes any
    quote or backslash an adopter's label name contains.
    """
    tests = [f"startswith({json.dumps(axis_prefix)})"]
    tests += [f". == {json.dumps(name)}" for name in carrier_labels]
    return (
        f"[.labels[]?.name] | map(select({' or '.join(tests)})) | (.[0] // \"\")"
    )


def _axis_label_guarded_fragment(change: PlannedChange, quoted: str, cite: str) -> str:
    """A bash fragment that re-reads the issue's labels and writes only when the
    axis is still unvalued — the fail-CLOSED guard.

    Three-way, mirroring ``--apply``'s ``classify_change``:

      * **re-read FAILED** → skip. This is where it deliberately parts company with
        the two older fragments, which treat an unreadable substrate as an unset one
        and write anyway (#816). A failed read here proves nothing about the issue,
        and this kind's whole contract is "only fill a gap" — so an unproven gap is
        not a gap. `if ! current=$(...)` is what makes the distinction available at
        all: it separates a non-zero `gh` exit from a successful read that returned
        the empty string, which a bare ``|| echo ""`` collapses into one.
      * **current non-empty** → the issue already carries a value for this axis
        (the target, or another one a human set since plan time); skip either way.
        Both are the same instruction — do not overwrite.
      * **current empty** → the confirmed gap this change exists to fill; write.

    The guard is inside an ``if`` condition, so ``set -e`` does not abort the script
    on the failing read — the skip is reported and the loop continues, which is the
    audited skip/report posture the ``--apply`` path also takes.
    """
    axis = change.axis or ""
    jq = _axis_label_carrier_jq(axis_labels.prefix(axis), change.carrier_labels)
    reread = (
        f"gh issue view {change.issue_number} --json labels "
        f"--jq {shlex.quote(jq)} 2>/dev/null"
    )
    tag = f"#{change.issue_number} {change.kind} ({axis})"
    return (
        f"# {tag}{cite}\n"
        f"# guard fails CLOSED: a FAILED re-read SKIPS the write (never fills a gap "
        f"it could not confirm).\n"
        f"if ! current=$({reread}); then\n"
        f'  echo "skip {tag}: could not re-read labels — failing closed, '
        f'nothing written" >&2\n'
        f'elif [ -n "$current" ]; then\n'
        f'  echo "skip {tag}: already carries $current for {axis}; '
        f'not overwriting" >&2\n'
        f"else\n"
        f"  {quoted}\n"
        f"fi"
    )


# ----- consume-a-saved-plan helpers ----------------------------------------


def refuse_if_gate_failed(plan: dict[str, Any]) -> str | None:
    """When consuming a SAVED plan, honor its residual-pre-check gate (property 3).

    Returns a refusal message when the saved plan's ``residual_pre_check.passed``
    is False (the gate refused at plan time — applying anyway would write against
    the very prerequisites the gate exists to protect), else ``None``. A fresh
    apply re-runs the live gate in ``back-fill.py``; this is only for the
    ``--plan <file>`` path where the gate already ran and its verdict is recorded.
    """
    gate = plan.get("residual_pre_check")
    if not isinstance(gate, dict):
        return (
            "saved plan has no residual_pre_check block — cannot confirm the "
            "residual gate passed; refusing to apply (DEC-037 §2)."
        )
    if not gate.get("passed"):
        return (
            "saved plan's residual pre-check gate did NOT pass — refusing to apply "
            "(DEC-037 §2). Re-run the report on the live repo and resolve the "
            "failing prerequisite first."
        )
    return None


def plan_schema_ok(plan: dict[str, Any]) -> bool:
    """True iff the saved plan's schema_version is the one this engine consumes."""
    return plan.get("schema_version") == CONSUMED_PLAN_SCHEMA_VERSION


def planned_changes_from_plan(plan: dict[str, Any]) -> list[PlannedChange]:
    """Reconstruct :class:`PlannedChange` objects from a saved ``--json`` plan.

    Maps each ``proposed[]`` entry back into the apply engine's input shape. The
    ``target`` is derived per kind: the milestone title for ``assign-milestone``;
    the single-select option-id (or text) for ``set-board-field`` — read off the
    matching intent so the value-equality predicate has the right comparison
    value. Field-value writes also recover the ``item_id`` / ``field_id`` /
    ``project_id`` from the constructed ``argv`` (the plan's argv is the exact
    write, so its flag values are the seam inputs) — no re-derivation, no
    string-building of a new write. A ``set-axis-label`` entry recovers its target
    (the resolved label) and its axis from the matching intent.

    Intents are keyed by ``(kind, axis)`` rather than by kind alone, because a plan
    can declare a ``set-axis-label`` intent for more than one axis and keying on
    kind would collapse them onto whichever came first — writing `priority`'s label
    for `workstream`'s change. For the two hook-driven kinds the axis is absent, so
    the key degenerates to ``(kind, "")`` and the lookup is exactly what it was.
    """
    intents = plan.get("intents") or []
    intent_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for intent in intents:
        if isinstance(intent, dict) and isinstance(intent.get("kind"), str):
            intent_by_key.setdefault(_intent_key(intent), intent)

    out: list[PlannedChange] = []
    for entry in plan.get("proposed") or []:
        if not isinstance(entry, dict):
            continue
        kind = entry.get("kind")
        if kind not in APPLIABLE_KINDS:
            continue
        argv = entry.get("argv")
        argv = argv if isinstance(argv, list) else None
        intent = intent_by_key.get(_intent_key(entry), {})
        target, seam_inputs = _target_and_inputs(kind, intent, argv)
        out.append(PlannedChange(
            issue_number=int(entry.get("issue_number", 0)),
            kind=str(kind),
            target=target,
            observed=entry.get("observed"),
            argv=argv,
            citation=str(entry.get("citation", "")),
            blocked_reason=str(entry.get("blocked_reason", "")),
            **seam_inputs,
        ))
    return out


def _intent_key(entry: dict[str, Any]) -> tuple[str, str]:
    """The ``(kind, axis)`` key matching a proposed entry to its intent.

    ``axis`` is empty for every kind but ``set-axis-label``, so the two hook-driven
    kinds key exactly as they did when the map was kind-only.
    """
    axis = entry.get("axis")
    return str(entry.get("kind", "")), axis if isinstance(axis, str) else ""


def _target_and_inputs(
    kind: str, intent: dict[str, Any], argv: list[str] | None
) -> tuple[str | None, dict[str, Any]]:
    """Derive (target value, seam-input kwargs) for one change from intent + argv.

    The target is what value-equality compares the fresh read against. The seam
    inputs (item/field/project ids for a field write) are recovered from the
    plan's exact ``argv`` flag values — not re-derived — so the apply executes the
    same write the human reviewed.
    """
    if kind == "assign-milestone":
        return intent.get("milestone_title"), {}
    if kind == SET_AXIS_LABEL_KIND:
        # `label_value` is what `axis_labels.resolve_write` returned at plan time —
        # the adopter's own substrate value. It is READ from the plan, never
        # recomposed here: this module has no business constructing a label.
        carriers = intent.get("carrier_labels")
        return intent.get("label_value"), {
            "axis": intent.get("axis"),
            "carrier_labels": tuple(
                name for name in (carriers or []) if isinstance(name, str)
            ),
        }
    # set-board-field
    option_id = intent.get("single_select_option_id")
    text_value = intent.get("text_value")
    target = option_id or text_value
    inputs = {
        "item_id": _argv_flag(argv, "--id"),
        "field_id": intent.get("field_id") or _argv_flag(argv, "--field-id"),
        "project_id": _argv_flag(argv, "--project-id"),
        "single_select_option_id": option_id,
        "text_value": text_value,
    }
    return target, inputs


def _argv_flag(argv: list[str] | None, flag: str) -> str | None:
    """The value following ``flag`` in ``argv`` (the plan's exact reviewed write),
    or ``None`` when the flag is absent. Reads the plan's argv — does not build one."""
    if not argv:
        return None
    for i, token in enumerate(argv[:-1]):
        if token == flag:
            return argv[i + 1]
    return None
