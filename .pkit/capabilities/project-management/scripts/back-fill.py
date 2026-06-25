#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml>=0.18",
# ]
# ///
"""Project-management capability — corpus back-fill (report + apply).

The one-time brownfield corpus back-fill, per
[project-management:DEC-037-adoption-ceremony] §2 and its write-path contract
[ADR-031](../../../../docs/architecture/decisions/ADR-031-substrate-write-path-contract.md).
A brownfield adopter wants a non-label substrate value seeded across every
existing issue — the AUJ grounding case: each issue's Projects-v2 `workstream`
field set to `Spyre`, and a time-based milestone assigned. That is a bulk
transform over hundreds of real, human-owned issues, so DEC-037 §2 makes it a
``migrate``-family operation governed by *enumerate → cite → confirm → apply*,
never a silent mass-edit.

It is the **same back-fill ceremony** in two phases, selected by mode flags
(DEC-037 §2 frames apply as the apply phase of this ceremony, not a separate
command):

  * **report** (default, T2a) — the **enumerate + cite + present** half. Prints
    the human-readable report, or ``--json`` emits the machine-stable plan T2b
    consumes. Mutates nothing — the report IS the gate.
  * **apply** (``--apply``, T2b) — drive the reviewed plan to writes, under the
    audited skip/report posture (DEC-037 §2 / ADR-031 §5+§6). Re-validates each
    issue at apply time; requires a confirmation gesture; the apply-loop and its
    predicates live in ``_lib/back_fill_apply.py``.
  * **emit-script** (``--emit-script``, T2b) — the symmetric draft-not-apply form:
    emit the reviewed mutations as an idempotent script the adopter runs
    themselves. pm never touches the corpus in this mode.

Apply / emit-script re-derive a fresh plan by default (they re-run the report's
enumeration so the plan reflects the live repo); pass ``--plan <file.json>`` to
consume a previously-saved ``--json`` plan instead (its ``schema_version`` is
pinned to ``back_fill_apply.CONSUMED_PLAN_SCHEMA_VERSION`` and its recorded
residual gate is honored).

The four DEC-037 §2 safety properties split across the phases:

  * **non-silent** (report half) — the report IS the gate. It enumerates the
    proposed per-issue changes and cites why each is proposed; nothing is written.
  * **residual-pre-check gate** (both halves) — refuse the whole operation if the
    residual hard-fail subset of ``pre-check`` fails. Four members (DEC-037 §2):
    ``gh`` auth invalid, repo inaccessible, ``substrate-map.yaml`` fails to parse,
    and — the fourth — a covered ``set-board-field`` intent IS declared yet the
    Projects-v2 board node id cannot be resolved at all (no board, or the board
    number does not resolve). The fourth is a CONJUNCTION computed *after* intent
    resolution: a field intent must be declared AND the board globally
    unresolvable. It is distinct from the *per-issue* case (the board resolves
    fine but a single issue simply isn't on it), which stays a per-issue
    ``blocked`` — global misconfiguration at the gate, per-issue membership gap per
    issue. A milestone-only back-fill (no field intent) does NOT gate on the board
    node id. DEC-036 made ``pre-check`` *degrade* a missing axis to a capability
    matrix rather than hard-refuse, so the gate is NOT "any pre-check failure" —
    only this residual subset that still breaks the plan's assumptions. A merely-
    degraded axis does NOT refuse the back-fill.
  * **re-validate at apply** and **value-equality idempotency** (apply half) —
    the report half only *reads* each issue's current state and *annotates*
    whether a write looks already-satisfied, so the human reviewing the report
    sees it; the binding "skip vs write" decision is the apply half's, made
    against a FRESH read at apply time (``_lib/back_fill_apply.classify_change``),
    never trusting the plan's stale ``observed``/``prediction``.
  * **--emit-script draft-not-apply** (apply half) — emit the reviewed mutations
    as an idempotent re-checking script the adopter runs themselves; pm executes
    no write in this mode.

Where the back-fill intent comes from (the convergence DEC-037 §3/§4 named)
--------------------------------------------------------------------------
DEC-037 §4 is explicit that population logic is **not a new slot** — it extends
[project-management:DEC-024-lifecycle-hooks]. The new-issue *default* is a DEC-024
``after_create_issue`` hook (``set-board-field`` for the Projects-v2 field;
``assign-milestone`` for the milestone); the one-time back-fill *"reuses the same
kind handlers, driven by the back-fill rather than by a lifecycle event"* (DEC-037
§4) and *"the one-time back-fill drives the same primitive"* (ADR-031 §2). So this
report reads its intent from exactly those two hook kinds declared on
``after_create_issue`` in ``project/hooks.yaml``: each such hook entry is one
back-fill *intent*, applied one-time across the corpus instead of once per create.
That is the single declaration point DEC-037 §4 points at — it avoids inventing a
new substrate-map ``field:`` binding (DEC-037 §3 / ADR-031 name that as deferred
trunk-Feature schema work, NOT this task), and it makes the **citation** concrete:
"hook entry N (kind=set-board-field) on after_create_issue".

An undeclared semantic this couples (surfaced in the report header): because the
back-fill reads its intent from the *same* ``after_create_issue`` hook that seeds
the go-forward new-issue default, **declaring a go-forward default automatically
enrols the entire historical corpus** as a back-fill intent. An adopter who wants a
go-forward default but NOT retroactive stamping (or vice versa) cannot express that
today — one declaration drives both. This is a known scope boundary for a later
task; a separate intent-declaration surface is deliberately NOT built here (DEC-037
§2 — the report IS the gate, so the report states the coupling to make acceptance
informed rather than silently enrolling the corpus).

The substrate-map is still read — for the **residual gate** (it must parse) and so
the report can cite a per-axis ``default:`` when one corroborates the hook intent
(DEC-036 carries per-axis ``default:``). The map is not the *source* of the
field/milestone ids the writes need (those are the hook's ``field_id`` /
``single_select_option_id`` / ``title``); it is read for the gate and the citation.

Constructing the planned write (ADR-031, never inline)
------------------------------------------------------
The report shows the **exact** ``gh`` write that would run, constructed through
``_lib/substrate_writes``'s ``*_args`` constructors — never string-built here. The
sole-constructor guard (``test_pm_substrate_write_seam``) holds for the planned
argv too: even though this half does not *execute* the write, it does not
*construct* it inline either. Where a Projects-v2 item id cannot be resolved for an
issue (the issue is not on the board), the field write is reported as
**blocked — needs board membership** rather than fabricating an argv; T2b acts on
that honestly.

The plan output shape T2b consumes (``--json``)
-----------------------------------------------
``--json`` emits a machine-stable plan: a top-level object with ``schema_version``,
the resolved ``intents`` (each with its citation), and a flat ``proposed`` list of
per-issue / per-intent entries. Each ``proposed`` entry carries the constructed
``argv`` (the exact write), the ``citation``, the ``observed`` current value read
at plan time, and an ``idempotent_prediction`` (``"already-satisfied"`` /
``"would-write"`` / ``"blocked"``). T2b re-reads each issue at apply time (it must
NOT trust ``observed`` — that is the re-validate-at-apply property), drives the
write through the same primitive, and applies its own posture. This half builds the
plan; it does not build re-validate-at-apply, value-equality idempotency,
``--emit-script``, or apply (those are T2b).

Self-contained via PEP 723 inline metadata; run via
  uv run --script .pkit/capabilities/project-management/scripts/back-fill.py
Or via the dispatcher (per COR-021):
  pkit project-management back-fill

Exit codes:
  0  report produced / apply completed with no write failures / emit-script
     written (including "no intents declared" / "nothing to propose")
  1  apply mode: one or more writes FAILED (audited skip/report posture — the
     loop continued and recorded each, but a write failed so the operator is
     told via a non-zero exit; ADR-031 §6). Skips (idempotent / drift) and
     blocks are NOT failures and do not set this code.
  2  usage error (capability not found; bad --plan; mutually-exclusive modes);
     the residual pre-check gate refused (auth / repo-access / map-parse /
     declared-field-intent-but-board-unresolvable); or apply was declined at the
     confirmation gate. No write runs in any of these cases.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
from _lib import axis_labels, back_fill_apply, substrate_writes  # noqa: E402
from _lib.gh import gh_run, load_adopter_config  # noqa: E402
from _lib.hooks import HOOKS_RELATIVE_PATH, load_hooks_file  # noqa: E402

CAPABILITY_NAME = "project-management"
PLAN_SCHEMA_VERSION = 1

# The back-fill drives exactly the two DEC-024 non-label-substrate kinds (DEC-037
# §4 / ADR-031 §2). The other two kinds (`post-comment`, `custom-script`) are not
# substrate writes and are out of the back-fill's scope.
BACK_FILL_KINDS: tuple[str, ...] = ("set-board-field", "assign-milestone")
# The back-fill applies a default-seeding intent declared for new issues to the
# EXISTING corpus, so it reads the new-issue event's hooks (DEC-037 §4 "the same
# kind handlers, driven by the back-fill rather than by a lifecycle event").
BACK_FILL_SOURCE_EVENT = "after_create_issue"


# ----- resolved intents (the cite half) ------------------------------


@dataclass(frozen=True)
class BackFillIntent:
    """One resolved back-fill intent — a non-label substrate write to seed corpus-wide.

    Sourced from one ``after_create_issue`` hook entry of a covered kind. ``citation``
    is the human-readable "why this is proposed" line (DEC-037 §2 propose-and-cite);
    ``axis_default_note`` corroborates it with the substrate-map per-axis ``default:``
    when one is declared (DEC-036), else empty.
    """

    kind: str            # "set-board-field" | "assign-milestone"
    citation: str        # why this intent is proposed
    axis_default_note: str = ""
    # set-board-field params (the field-value write inputs, ADR-031 / hook schema)
    field_id: str | None = None
    single_select_option_id: str | None = None
    text_value: str | None = None
    # assign-milestone params (the milestone write input)
    milestone_title: str | None = None


@dataclass
class ProposedChange:
    """One proposed per-issue write — an intent applied to one issue."""

    issue_number: int
    issue_title: str
    kind: str
    citation: str
    # The exact gh write constructed via substrate_writes *_args (ADR-031), or
    # None when blocked (e.g. the field write needs a board item id we can't
    # resolve for this issue — reported, not fabricated).
    argv: list[str] | None
    observed: str | None          # current value read at plan time (for the human)
    prediction: str               # "already-satisfied" | "would-write" | "blocked"
    blocked_reason: str = ""


# ----- script entry --------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Corpus back-fill — the auditable propose-and-cite REPORT half "
            "(DEC-037 §2). Enumerates the proposed per-issue non-label substrate "
            "writes (Projects-v2 field value; milestone), cites why each is "
            "proposed, and presents the report as the gate. Mutates nothing — "
            "applying the plan is a separate operation."
        ),
    )
    parser.add_argument(
        "--capability-root",
        type=Path,
        default=None,
        help=(
            "Path to the installed capability's directory "
            "(default: <repo-root>/.pkit/capabilities/project-management/)."
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help=(
            "Emit the machine-stable plan as JSON (the shape the apply engine "
            "consumes) instead of the human-readable report."
        ),
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=500,
        help="Maximum number of issues to enumerate from the corpus (default 500).",
    )
    parser.add_argument(
        "--state",
        choices=("open", "closed", "all"),
        default="all",
        help=(
            "Which issues to enumerate (default: all). A corpus back-fill "
            "typically targets every issue, open and closed."
        ),
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--apply",
        action="store_true",
        help=(
            "APPLY the reviewed plan: re-validate each issue at apply time and "
            "drive the writes (DEC-037 §2). The highest-blast-radius pm "
            "operation — requires a confirmation gesture (the reviewed-batch "
            "confirmation prompt, or --yes / --config for CI pre-approval). "
            "Mutually exclusive with --emit-script."
        ),
    )
    mode.add_argument(
        "--emit-script",
        action="store_true",
        help=(
            "Draft-not-apply (DEC-037 §2): emit the reviewed mutations as an "
            "idempotent re-checking shell script the adopter runs themselves. "
            "pm executes NO write in this mode. Mutually exclusive with --apply."
        ),
    )
    parser.add_argument(
        "--plan",
        type=Path,
        default=None,
        help=(
            "Apply / emit-script from a previously-saved --json plan file instead "
            "of re-deriving a fresh plan from the live repo. The plan's "
            "schema_version is pinned, and its recorded residual-pre-check gate is "
            "honored. WARNING: a saved plan is staler than a freshly-derived one; "
            "re-validate-at-apply still re-reads each issue, but prefer a fresh "
            "derivation unless you have a reason to pin the reviewed plan."
        ),
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help=(
            "Pre-approve the apply confirmation (CI / non-interactive). Mirrors "
            "migrate's pre-approval escape hatch. Has no effect outside --apply."
        ),
    )
    args = parser.parse_args()

    capability_root = _resolve_capability_root(args.capability_root)
    if capability_root is None:
        print(
            "error: project-management capability not found. Run this script "
            "from within an adopter project that has the capability installed "
            "at .pkit/capabilities/project-management/.",
            file=sys.stderr,
        )
        return 2

    config = load_adopter_config(capability_root)
    apply_mode = bool(args.apply or args.emit_script)

    # --plan consumes a previously-saved plan (apply / emit-script only) — skip the
    # live build and honor the plan's RECORDED gate (DEC-037 §2 property 3).
    if args.plan is not None:
        if not apply_mode:
            print(
                "error: --plan applies only to --apply / --emit-script (the report "
                "phase derives its own plan live).",
                file=sys.stderr,
            )
            return 2
        return _run_from_saved_plan(args, config, capability_root)

    # Otherwise derive the plan live: run the residual gate, resolve intents,
    # enumerate the corpus, build the proposed changes.
    plan, gate_failed = _derive_plan(capability_root, config, args)
    if gate_failed:
        return 2  # the gate refusal was already printed by _derive_plan.
    if plan is None:
        # No intents declared — nothing to propose. Phase-appropriate message.
        _print_no_intents(args)
        return 0

    if apply_mode:
        return _run_apply_or_emit(args, config, plan)

    # report phase (default).
    if args.json:
        print(json.dumps(plan, indent=2))
    else:
        if plan["truncated"]:
            _print_truncation_warning(args.limit)
        _print_report_from_plan(plan)
    return 0


# ----- plan derivation (shared by report + fresh apply/emit) ----------


def _derive_plan(
    capability_root: Path, config: dict[str, Any], args: argparse.Namespace
) -> tuple[dict[str, Any] | None, bool]:
    """Run the gate, resolve intents, enumerate, and build the live plan document.

    Returns ``(plan, gate_failed)``. ``gate_failed`` True means the residual gate
    refused (the refusal has already been printed); the caller returns 2. A
    ``None`` plan with ``gate_failed`` False means no intents are declared (nothing
    to propose) — the caller prints the phase-appropriate "nothing" message.

    The plan is the SAME machine-stable document the report half emits (T2a) —
    apply / emit-script consume it in-process exactly as if it had been saved and
    reloaded, so the report and the apply act on one shared plan shape.
    """
    # The residual-pre-check gate, arm 1 (DEC-037 §2). Auth / repo-access /
    # map-parse do not depend on the intents, so they run first.
    gate = _residual_pre_check(capability_root)
    if not gate.passed:
        _print_gate_refusal(gate)
        return None, True

    substrate_map = axis_labels.load_substrate_map(capability_root)
    intents, intent_errors = _resolve_intents(capability_root, substrate_map)

    # Arm 2 (the fourth residual member): a covered set-board-field intent IS
    # declared AND the board node id cannot be resolved at all → global refusal.
    has_field_intent = any(i.kind == "set-board-field" for i in intents)
    project_node_id = _resolve_project_node_id(config) if has_field_intent else None
    if has_field_intent and project_node_id is None:
        _add_board_unresolvable_failure(gate)
        _print_gate_refusal(gate)
        return None, True

    # Context header + gate-pass lines on the human-readable report phase only.
    human_report_phase = not args.json and not args.apply and not args.emit_script
    if human_report_phase:
        _print_context_header(capability_root, config)
        _print_gate_pass(gate)
        for err in intent_errors:
            print(f"  ! {err}")
        if intent_errors:
            print()

    if not intents:
        return None, False

    issues = _enumerate_corpus(config, limit=args.limit, state=args.state)
    truncated = len(issues) == args.limit
    target_repo = _resolve_repo_name_with_owner(config)
    item_ids = _resolve_board_item_ids(config, project_node_id, issues)
    proposed = _build_proposed_changes(
        intents, issues, item_ids, project_node_id, target_repo
    )
    return _plan_document(intents, proposed, gate, truncated=truncated), False


def _print_no_intents(args: argparse.Namespace) -> None:
    """The phase-appropriate 'no intents declared' message."""
    if args.json:
        # Emit a well-formed empty plan so a --json consumer parses it cleanly.
        empty_gate = GateResult(passed=True, checks=[])
        print(json.dumps(_plan_document([], [], empty_gate, truncated=False), indent=2))
        return
    print(
        "No back-fill intents declared. The corpus back-fill drives the "
        f"`{', '.join(BACK_FILL_KINDS)}` hooks on `{BACK_FILL_SOURCE_EVENT}` "
        f"in {HOOKS_RELATIVE_PATH} (DEC-037 §4); none are declared, so "
        "there is nothing to propose."
    )


# ----- apply / emit-script dispatch -----------------------------------


def _run_from_saved_plan(
    args: argparse.Namespace, config: dict[str, Any], capability_root: Path
) -> int:
    """Apply / emit-script from a saved --json plan file.

    Pins the plan's ``schema_version`` (refuse a plan this engine cannot read
    rather than mis-apply it) and enforces the residual gate (property 3) in TWO
    layers:

      1. The plan's RECORDED gate verdict is honored as a cheap pre-filter — a plan
         whose gate did not pass at plan time is refused outright.
      2. The LIVE gate is re-run before applying (G1). Auth / repo-access / board-
         resolvability can flip between plan-save and apply (token expired, repo
         archived, board deleted), and the recorded verdict is stale for exactly
         those members. The saved plan's enumerated per-issue ``observed``/``argv``
         is still trusted as the proposal (each issue is re-validated live in the
         apply loop anyway), but the GLOBAL precondition gate must be fresh — a
         stale "passed: true" must not authorise writes against now-failing
         prerequisites.
    """
    try:
        raw = args.plan.read_text(encoding="utf-8")
        plan = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"error: could not read --plan {args.plan}: {exc}", file=sys.stderr)
        return 2
    if not isinstance(plan, dict) or not back_fill_apply.plan_schema_ok(plan):
        print(
            f"error: --plan {args.plan} is not a back-fill plan of "
            f"schema_version {back_fill_apply.CONSUMED_PLAN_SCHEMA_VERSION} "
            "(refusing to apply a plan this engine cannot read; DEC-037 §2).",
            file=sys.stderr,
        )
        return 2
    refusal = back_fill_apply.refuse_if_gate_failed(plan)
    if refusal is not None:
        print(f"back-fill: REFUSED — {refusal}", file=sys.stderr)
        return 2

    # G1: re-run the LIVE residual gate — do not trust the recorded verdict for the
    # auth / repo / board members, any of which can flip after plan-save.
    live_gate = _residual_gate_for_saved_plan(plan, config, capability_root)
    if not live_gate.passed:
        print(
            "back-fill: REFUSED — the live residual pre-check gate now fails "
            "(re-checked at apply time; the saved plan's recorded verdict is "
            "stale for auth / repo / board prerequisites — DEC-037 §2).",
            file=sys.stderr,
        )
        _print_gate_refusal(live_gate)
        return 2

    return _run_apply_or_emit(args, config, plan)


def _residual_gate_for_saved_plan(
    plan: dict[str, Any], config: dict[str, Any], capability_root: Path
) -> GateResult:
    """Re-run the live residual gate against a saved plan (G1).

    The same gate the fresh path runs — auth / repo-access / substrate-map parse
    (:func:`_residual_pre_check`) plus the fourth member (a declared
    ``set-board-field`` intent whose Projects-v2 board cannot be resolved live). The
    board member is keyed off the SAVED plan's declared intents (the plan records
    each intent's ``kind``), so a plan that declared a field intent re-checks board
    resolvability against the live board, catching a board deleted since plan-save.
    """
    gate = _residual_pre_check(capability_root)
    if not gate.passed:
        return gate
    intents = plan.get("intents")
    declares_field_intent = isinstance(intents, list) and any(
        isinstance(i, dict) and i.get("kind") == "set-board-field" for i in intents
    )
    if declares_field_intent and _resolve_project_node_id(config) is None:
        _add_board_unresolvable_failure(gate)
    return gate


def _run_apply_or_emit(
    args: argparse.Namespace, config: dict[str, Any], plan: dict[str, Any]
) -> int:
    """Dispatch the apply (mutating) or emit-script (draft) phase over a plan."""
    changes = back_fill_apply.planned_changes_from_plan(plan)
    truncated = bool(plan.get("truncated"))

    if args.emit_script:
        # Draft-not-apply: pm executes NO write — it prints a script (DEC-037 §2).
        if truncated:
            print(
                "  !! WARNING: plan is TRUNCATED — the emitted script covers only "
                "the planned subset of the corpus (DEC-037 §2).",
                file=sys.stderr,
            )
        print(back_fill_apply.render_emit_script(changes, truncated=truncated))
        return 0

    # --apply: the mutating path. Confirm before any write (DEC-037 §2).
    if truncated:
        print(
            "!! WARNING: plan is TRUNCATED — this apply covers only the planned "
            "subset of the corpus, NOT every issue. Re-derive with a higher "
            "--limit to apply across the whole corpus (DEC-037 §2).",
            file=sys.stderr,
        )
    if not _confirm_apply(changes, pre_approved=args.yes):
        print("back-fill: apply declined at the confirmation gate; nothing written.")
        return 2

    records = back_fill_apply.apply_plan(
        changes, config, read_fresh=lambda c: _read_fresh_state(c, config)
    )
    summary = back_fill_apply.summarise(records)
    _print_apply_summary(records, summary)
    return back_fill_apply.exit_code_for(summary)


def _confirm_apply(
    changes: list[back_fill_apply.PlannedChange], *, pre_approved: bool
) -> bool:
    """The reviewed-batch confirmation gate (DEC-037 §2 / migrate-family posture).

    The human confirms ONCE for the reviewed batch (per-issue clicks become a
    rubber-stamp wall at corpus scale — DEC-037 Rationale). ``--yes`` pre-approves
    for CI, mirroring migrate's escape hatch. In a non-interactive shell with no
    pre-approval, default to NO (never silently bulk-mutate).
    """
    writeable = sum(1 for c in changes if c.argv is not None)
    print(
        f"  About to APPLY up to {writeable} write(s) across "
        f"{len({c.issue_number for c in changes})} issue(s). Each is "
        "re-validated against the issue's current state immediately before "
        "writing (drift → skip; already-set → skip)."
    )
    if pre_approved:
        print("  Pre-approved via --yes.")
        return True
    if not sys.stdin.isatty():
        print(
            "  ! Non-interactive shell and no --yes; refusing to bulk-mutate. "
            "Re-run from an interactive shell or pass --yes (CI).",
            file=sys.stderr,
        )
        return False
    try:
        response = input("  Apply this reviewed batch? [y/N]: ").strip().lower()
    except EOFError:
        return False
    return response in ("y", "yes")


# ----- residual pre-check gate ---------------------------------------


@dataclass
class GateResult:
    """The residual-pre-check gate outcome (DEC-037 §2 fourth property)."""

    passed: bool
    # (label, status, detail) per residual check, for the report.
    checks: list[tuple[str, str, str]] = field(default_factory=list)


def _residual_pre_check(capability_root: Path) -> GateResult:
    """Run ONLY the residual hard-fail subset of pre-check (DEC-037 §2).

    DEC-036 made pre-check degrade a missing axis to a capability matrix rather
    than hard-refuse, so the back-fill gates on the narrow subset that still
    hard-fails in brownfield — ``gh`` auth invalid, repo inaccessible, or
    ``substrate-map.yaml`` fails to parse — NOT the degraded-axis checks. To
    avoid drift, the three probes are pre-check's OWN check functions, loaded by
    file path (pre-check.py has a hyphen, so a plain import won't reach it) and
    reused verbatim rather than reimplemented (COR-007 — don't re-derive the
    diagnostic).

    A merely-degraded axis does NOT appear here and does NOT refuse the run.
    """
    pre_check = _load_pre_check_module(capability_root)
    checks: list[tuple[str, str, str]] = []

    if pre_check is None:
        # Defensive: the sibling diagnostic is missing/unloadable. Fail closed —
        # we cannot confirm the residual prerequisites, so we must not proceed to
        # propose writes against an unverified substrate.
        checks.append((
            "residual pre-check",
            "fail",
            "could not load pre-check.py to run the residual gate "
            "(auth / repo-access / map-parse). Refusing to proceed.",
        ))
        return GateResult(passed=False, checks=checks)

    # 1. gh auth, 2. repo accessible — always residual hard-fails.
    auth = pre_check._check_gh_auth()
    checks.append((auth.label, auth.status, auth.detail))
    repo = pre_check._check_repo_accessible()
    checks.append((repo.label, repo.status, repo.detail))

    # 3. substrate-map.yaml parse — only when a map is present (an absent map is
    #    greenfield, which is not a back-fill failure; and an absent map cannot
    #    "fail to parse"). The parse probe is pre-check's own, which distinguishes
    #    "present but unparseable / mis-shaped" (fail) from "parses" (ok).
    map_path = capability_root / axis_labels.SUBSTRATE_MAP_RELATIVE_PATH
    if map_path.is_file():
        parse = pre_check._check_substrate_map_parse(capability_root)
        checks.append((parse.label, parse.status, parse.detail))

    passed = all(status != "fail" for _, status, _ in checks)
    return GateResult(passed=passed, checks=checks)


def _add_board_unresolvable_failure(gate: GateResult) -> None:
    """Append the fourth residual-gate member's failure (DEC-037 §2) onto the gate.

    The conjunction "a covered set-board-field intent IS declared AND the
    Projects-v2 board node id cannot be resolved at all" is a *global* precondition
    failure computed after intent resolution. The caller has already established
    both conjuncts; this records the failure so the standard refusal path surfaces
    it once at the top, distinct from the per-issue membership block.
    """
    gate.passed = False
    gate.checks.append((
        "Projects v2 board resolvable",
        "fail",
        "declared set-board-field intent(s) cannot be served: no Projects v2 "
        "board resolvable (has_projects_v2_board false/unset, projects_v2_board_id "
        "missing, or the board number does not resolve via `gh project view`).",
    ))


def _load_pre_check_module(capability_root: Path) -> Any | None:
    """Load pre-check.py as a module by file path (its name has a hyphen).

    Reusing pre-check's exact residual-check logic (rather than reimplementing
    the auth/repo/parse probes) keeps the gate from drifting out of sync with the
    full diagnostic. Returns the loaded module, or None if it cannot be loaded.
    """
    pre_check_path = capability_root / "scripts" / "pre-check.py"
    if not pre_check_path.is_file():
        return None
    try:
        spec = importlib.util.spec_from_file_location(
            "pm_pre_check_for_back_fill", pre_check_path
        )
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    except Exception:
        return None


# ----- intent resolution (cite half) ---------------------------------


def _resolve_intents(
    capability_root: Path,
    substrate_map: axis_labels.SubstrateMap | None,
) -> tuple[list[BackFillIntent], list[str]]:
    """Resolve back-fill intents from the after_create_issue hooks (DEC-037 §4).

    Reads the covered kinds (``set-board-field`` / ``assign-milestone``) declared
    on ``after_create_issue`` in ``hooks.yaml`` and turns each into a
    :class:`BackFillIntent` with a concrete citation. Malformed entries are
    skipped with a reported error (the report shows them; they do not crash).

    Returns ``(intents, errors)``.
    """
    hooks_doc = load_hooks_file(capability_root)
    by_event = hooks_doc.get("hooks") if isinstance(hooks_doc.get("hooks"), dict) else {}
    entries = by_event.get(BACK_FILL_SOURCE_EVENT) if isinstance(by_event, dict) else None

    intents: list[BackFillIntent] = []
    errors: list[str] = []
    if not isinstance(entries, list):
        return intents, errors

    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            continue
        kind = str(entry.get("kind", "")).strip()
        if kind not in BACK_FILL_KINDS:
            continue  # post-comment / custom-script / unknown — not a substrate write
        cite_prefix = (
            f"hook entry {index} (kind={kind}) on {BACK_FILL_SOURCE_EVENT} "
            f"in {HOOKS_RELATIVE_PATH} (DEC-037 §4 — the same write the per-create "
            f"default seeds, applied one-time over the corpus)"
        )
        if kind == "set-board-field":
            intent, err = _intent_from_set_board_field(entry, cite_prefix, substrate_map)
        else:  # assign-milestone
            intent, err = _intent_from_assign_milestone(entry, cite_prefix, substrate_map)
        if err:
            errors.append(f"skipping hook entry {index} (kind={kind}): {err}")
        if intent is not None:
            intents.append(intent)

    return intents, errors


def _intent_from_set_board_field(
    entry: dict[str, Any],
    citation: str,
    substrate_map: axis_labels.SubstrateMap | None,
) -> tuple[BackFillIntent | None, str]:
    field_id = entry.get("field_id")
    option_id = entry.get("single_select_option_id")
    text_value = entry.get("text_value")
    if not isinstance(field_id, str) or not field_id:
        return None, "missing or empty `field_id`"
    if not (option_id or text_value):
        return None, "requires `single_select_option_id` or `text_value`"
    return (
        BackFillIntent(
            kind="set-board-field",
            citation=citation,
            axis_default_note=_workstream_default_note(substrate_map),
            field_id=field_id,
            single_select_option_id=str(option_id) if option_id else None,
            text_value=str(text_value) if text_value else None,
        ),
        "",
    )


def _intent_from_assign_milestone(
    entry: dict[str, Any],
    citation: str,
    substrate_map: axis_labels.SubstrateMap | None,
) -> tuple[BackFillIntent | None, str]:
    title = entry.get("title")
    if not isinstance(title, str) or not title:
        return None, "missing or empty `title`"
    return (
        BackFillIntent(
            kind="assign-milestone",
            citation=citation,
            milestone_title=title,
        ),
        "",
    )


def _workstream_default_note(
    substrate_map: axis_labels.SubstrateMap | None,
) -> str:
    """Cite the substrate-map per-axis `default:` for workstream when one exists.

    The AUJ field-value back-fill (`workstream=Spyre`) corroborates with the
    `workstream` axis's declared `default:` (DEC-036 carries per-axis `default:`).
    This is a supporting citation, not the source of the field id; empty when no
    default is declared (or greenfield).
    """
    default = axis_labels.axis_default("workstream", substrate_map)
    if default:
        return (
            f"corroborated by substrate-map.yaml `workstream` axis default "
            f"`{default}` (DEC-036 per-axis default:)"
        )
    return ""


# ----- corpus enumeration --------------------------------------------


def _enumerate_corpus(
    config: dict[str, Any], *, limit: int, state: str
) -> list[dict[str, Any]]:
    """List the corpus issues with the fields the report needs (a READ).

    Pulls ``number``, ``title``, and ``milestone`` (for value-equality
    annotation of the milestone intent). Board field-value current state is not
    available on the ``gh issue`` JSON surface, so the field intent's ``observed``
    is left unresolved (the human sees "unknown — re-validated at apply").
    """
    try:
        proc = gh_run(
            [
                "gh", "issue", "list",
                "--state", state,
                "--limit", str(limit),
                "--json", "number,title,milestone",
            ],
            config,
            check=False,
        )
    except FileNotFoundError:
        return []
    if proc.returncode != 0:
        return []
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


def _resolve_project_node_id(config: dict[str, Any]) -> str | None:
    """Resolve the Projects-v2 project GraphQL node id the way the rest of pm does.

    The field-value write needs the *project* node id, but no adopter declares it
    directly in config — the documented board config is ``has_projects_v2_board`` +
    ``projects_v2_board_id`` (a board *number*), exactly as ``create-issue.py`` /
    ``pre-check.py`` read it. So this resolves the board *number* to its node id via
    a ``gh project view`` read (the same read ``pre-check`` runs to verify the board
    resolves), keyed by the configured ``gh.default_owner`` (or, absent that, the
    current repo's owner from ``gh repo view``). A READ only.

    Returns ``None`` when no board is configured (``has_projects_v2_board`` falsey
    or ``projects_v2_board_id`` unset) or the board number does not resolve. The
    caller treats a ``None`` as "no board resolvable" — which, when a field intent
    is declared, the residual gate's fourth member turns into a global refusal
    (DEC-037 §2), and otherwise leaves the milestone-only back-fill unaffected.
    """
    if not config.get("has_projects_v2_board"):
        return None
    board_number = config.get("projects_v2_board_id")
    if board_number is None:
        return None

    owner = _resolve_board_owner(config)
    view_args = ["gh", "project", "view", str(board_number), "--format", "json"]
    if owner:
        view_args += ["--owner", owner]
    try:
        proc = gh_run(view_args, config, check=False)
    except FileNotFoundError:
        return None
    if proc.returncode != 0:
        return None
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None
    node_id = payload.get("id") if isinstance(payload, dict) else None
    return node_id if isinstance(node_id, str) and node_id else None


def _resolve_board_owner(config: dict[str, Any]) -> str | None:
    """The owner to scope the board lookup to: configured ``gh.default_owner``, else
    the current repo's owner (from ``gh repo view``). ``None`` if neither resolves —
    ``gh project view`` then falls back to its own default-owner behaviour."""
    gh_block = config.get("gh") if isinstance(config, dict) else None
    if isinstance(gh_block, dict):
        owner = gh_block.get("default_owner")
        if isinstance(owner, str) and owner:
            return owner
    repo = _resolve_repo_name_with_owner(config)
    if repo != "<unresolved>" and "/" in repo:
        return repo.split("/", 1)[0]
    return None


def _resolve_board_item_ids(
    config: dict[str, Any], project_node_id: str | None, issues: list[dict[str, Any]]
) -> dict[tuple[str, int], str]:
    """Map (repo, issue-number) → its Projects-v2 item node id, for the field write.

    The field-value write (`gh project item-edit --id <item>`) needs the issue's
    Projects-v2 *item* node id. Resolving it is a READ; this fetches the board's
    items once via the GraphQL surface and maps each item's content to its id.

    The map is keyed on **(repository nameWithOwner, issue number)**, not number
    alone: a Projects-v2 board can carry issues from multiple repos with colliding
    numbers, so issue #42 in the target repo and a #42 in another repo on the same
    board would otherwise resolve to whichever item the read saw last — a wrong
    item id flowing straight into the plan's argv. Keying on (repo, number) and
    matching only the target repo's issues (in :func:`_build_proposed_changes`)
    closes that collision.

    Returns ``{}`` when no board node id resolves or the read fails — every field
    intent then reports as blocked (needs membership) rather than guessing. Best-
    effort and bounded: a single paginated read.
    """
    if not isinstance(project_node_id, str) or not project_node_id:
        return {}

    query = (
        "query($project: ID!, $cursor: String) { node(id: $project) { "
        "... on ProjectV2 { items(first: 100, after: $cursor) { "
        "pageInfo { hasNextPage endCursor } nodes { id content { "
        "... on Issue { number repository { nameWithOwner } } } } } } } }"
    )
    out: dict[tuple[str, int], str] = {}
    cursor: str | None = None
    # Bound the pagination so a misconfigured board can't loop unboundedly.
    for _ in range(50):
        api_args = [
            "gh", "api", "graphql",
            "-f", f"query={query}",
            "-F", f"project={project_node_id}",
        ]
        if cursor:
            api_args += ["-F", f"cursor={cursor}"]
        try:
            proc = gh_run(api_args, config, check=False)
        except FileNotFoundError:
            return out
        if proc.returncode != 0:
            return out
        try:
            payload = json.loads(proc.stdout)
        except json.JSONDecodeError:
            return out
        items_block = (
            payload.get("data", {}).get("node", {}).get("items", {})
            if isinstance(payload, dict)
            else {}
        )
        for node in items_block.get("nodes") or []:
            if not isinstance(node, dict):
                continue
            content = node.get("content") or {}
            if not isinstance(content, dict):
                continue
            number = content.get("number")
            repo_block = content.get("repository") or {}
            repo = (
                repo_block.get("nameWithOwner")
                if isinstance(repo_block, dict)
                else None
            )
            item_id = node.get("id")
            if (
                isinstance(number, int)
                and isinstance(repo, str) and repo
                and isinstance(item_id, str) and item_id
            ):
                out[(repo, number)] = item_id
        page = items_block.get("pageInfo") or {}
        if not page.get("hasNextPage"):
            break
        cursor = page.get("endCursor")
        if not isinstance(cursor, str) or not cursor:
            break
    return out


# ----- proposed-change computation (the enumerate half) --------------


def _build_proposed_changes(
    intents: list[BackFillIntent],
    issues: list[dict[str, Any]],
    item_ids: dict[tuple[str, int], str],
    project_id: str | None,
    target_repo: str,
) -> list[ProposedChange]:
    """Compute one proposed change per (issue, intent), with the constructed argv.

    The write argv is constructed through ``substrate_writes`` ``*_args`` (ADR-031,
    never inline). ``observed`` + ``prediction`` annotate the current state so the
    human sees what looks already-satisfied — but the binding skip/write decision
    is T2b's, made against a fresh read at apply time (re-validate-at-apply).

    ``item_ids`` is keyed on (repo, number); the field-value path matches only
    ``target_repo``'s issues so a colliding number on another repo's board item
    cannot resolve. The global "no board resolvable" case is handled upstream by
    the residual gate (DEC-037 §2 fourth member); ``project_id`` is ``None`` here
    only when no field intent gated (milestone-only back-fill).
    """
    proposed: list[ProposedChange] = []
    for issue in issues:
        number = issue.get("number")
        title = str(issue.get("title", ""))
        if not isinstance(number, int):
            continue
        for intent in intents:
            if intent.kind == "set-board-field":
                proposed.append(
                    _propose_field_value(
                        intent, number, title, item_ids, project_id, target_repo
                    )
                )
            else:  # assign-milestone
                proposed.append(
                    _propose_milestone(intent, number, title, issue)
                )
    return proposed


def _propose_field_value(
    intent: BackFillIntent,
    number: int,
    title: str,
    item_ids: dict[tuple[str, int], str],
    project_id: str | None,
    target_repo: str,
) -> ProposedChange:
    """Propose one Projects-v2 field-value write for one issue.

    Blocked (no fabricated argv) when THIS issue's board item id can't be resolved
    — the issue is simply not on the board (recoverable by adding it). The *global*
    "no board resolvable at all" case does NOT reach here: when a field intent is
    declared it is caught upstream by the residual gate's fourth member (DEC-037 §2)
    and refuses the whole run once; ``project_id`` being ``None`` here only happens
    for a milestone-only back-fill that never declared a field intent, so it is
    reported as a per-issue block too. Either way: per-issue grain, no fabricated
    argv. T2b acts on the block (establish membership, then write) honestly.
    """
    item_id = item_ids.get((target_repo, number))
    if item_id is None or project_id is None:
        reason = (
            f"issue not on the configured Projects v2 board (no item id for "
            f"{target_repo}#{number})"
            if project_id is not None
            else "no Projects v2 board resolvable for this milestone-only back-fill"
        )
        return ProposedChange(
            issue_number=number,
            issue_title=title,
            kind="set-board-field",
            citation=_full_citation(intent),
            argv=None,
            observed=None,
            prediction="blocked",
            blocked_reason=reason,
        )
    # Constructed through the sole constructor (ADR-031) — never string-built here.
    argv = substrate_writes.field_value_args(
        item_id=item_id,
        field_id=intent.field_id or "",
        project_id=project_id,
        single_select_option_id=intent.single_select_option_id,
        text_value=intent.text_value,
    )
    # The gh `issue` JSON surface does not expose the board field's current value,
    # so observed is unknown here; T2b re-validates at apply (DEC-037 §2).
    return ProposedChange(
        issue_number=number,
        issue_title=title,
        kind="set-board-field",
        citation=_full_citation(intent),
        argv=argv,
        observed=None,
        prediction="would-write",
    )


def _propose_milestone(
    intent: BackFillIntent,
    number: int,
    title: str,
    issue: dict[str, Any],
) -> ProposedChange:
    """Propose one milestone write for one issue, annotated with value-equality.

    The milestone intent's current value IS on the ``gh issue`` JSON surface, so
    this annotates ``already-satisfied`` when the issue's milestone already equals
    the target (the value-equality DEC-037 §2 idempotency, surfaced for the human
    — the binding skip is still T2b's at apply time).
    """
    target = intent.milestone_title or ""
    current_ms = issue.get("milestone")
    observed = (
        current_ms.get("title")
        if isinstance(current_ms, dict) and isinstance(current_ms.get("title"), str)
        else None
    )
    # Constructed through the sole constructor (ADR-031) — never string-built here.
    argv = substrate_writes.milestone_edit_args(issue_number=number, title=target)
    prediction = "already-satisfied" if observed == target else "would-write"
    return ProposedChange(
        issue_number=number,
        issue_title=title,
        kind="assign-milestone",
        citation=_full_citation(intent),
        argv=argv,
        observed=observed,
        prediction=prediction,
    )


def _full_citation(intent: BackFillIntent) -> str:
    """The full why-line for an intent, including any corroborating default note."""
    if intent.axis_default_note:
        return f"{intent.citation}; {intent.axis_default_note}"
    return intent.citation


# ----- plan document (the machine-stable T2b seam) -------------------


def _plan_document(
    intents: list[BackFillIntent],
    proposed: list[ProposedChange],
    gate: GateResult,
    *,
    truncated: bool,
) -> dict[str, Any]:
    """The machine-stable plan T2b consumes (`--json`).

    Shape (versioned so T2b can pin it):
      schema_version: int
      truncated: bool
      residual_pre_check: {passed, checks: [{label, status, detail}]}
      intents: [{kind, citation, ...params}]
      proposed: [{issue_number, issue_title, kind, citation, argv|null,
                  observed|null, prediction, blocked_reason}]

    ``truncated`` is True when the corpus enumeration hit ``--limit`` exactly, so
    the plan may be an INCOMPLETE view of the corpus — T2b must treat a truncated
    plan as not-the-whole-corpus (DEC-037's non-silent posture; a truncated plan
    reviewed as complete is an audit gap).

    ``argv`` is the EXACT constructed write (or null when blocked). T2b re-reads
    each issue at apply time (it must NOT trust ``observed``/``prediction`` —
    re-validate-at-apply), drives the write through the same primitive, and
    applies its own posture.
    """
    return {
        "schema_version": PLAN_SCHEMA_VERSION,
        "truncated": truncated,
        "residual_pre_check": {
            "passed": gate.passed,
            "checks": [
                {"label": label, "status": status, "detail": detail}
                for label, status, detail in gate.checks
            ],
        },
        "intents": [
            {
                "kind": i.kind,
                "citation": _full_citation(i),
                "field_id": i.field_id,
                "single_select_option_id": i.single_select_option_id,
                "text_value": i.text_value,
                "milestone_title": i.milestone_title,
            }
            for i in intents
        ],
        "proposed": [
            {
                "issue_number": c.issue_number,
                "issue_title": c.issue_title,
                "kind": c.kind,
                "citation": c.citation,
                "argv": c.argv,
                "observed": c.observed,
                "prediction": c.prediction,
                "blocked_reason": c.blocked_reason,
            }
            for c in proposed
        ],
    }


# ----- human report --------------------------------------------------


def _print_context_header(capability_root: Path, config: dict[str, Any]) -> None:
    repo = _resolve_repo_name_with_owner(config)
    version = _read_capability_version(capability_root)
    print("back-fill (report): project-management capability")
    print(f"  target repo: {repo}")
    print(f"  capability:  {capability_root} (v{version})")
    print(f"  intent src:  {capability_root / HOOKS_RELATIVE_PATH} "
          f"({BACK_FILL_SOURCE_EVENT} hooks)")
    print(
        "  posture:     REPORT ONLY — no issue is mutated. Applying this plan "
        "is a separate operation (DEC-037 §2)."
    )
    print(
        "  scope note:  each `after_create_issue` hook of a covered kind "
        f"({', '.join(BACK_FILL_KINDS)}) is treated as a CORPUS-WIDE back-fill "
        "intent — so declaring a go-forward new-issue default automatically "
        "enrols the entire historical corpus. Separating a go-forward-only "
        "default from a retroactive back-fill is NOT yet expressible (one "
        "declaration drives both); known scope boundary, not built here."
    )
    print()


def _print_truncation_warning(limit: int) -> None:
    """Loudly warn that the corpus enumeration may have been truncated at --limit.

    The enumeration returned exactly ``limit`` issues, so there may be more the
    plan does not cover. DEC-037's posture is non-silent; a truncated corpus
    reviewed as the complete plan is an audit gap, so this is a prominent warning
    (the `--json` plan carries the same signal as a ``truncated`` boolean).
    """
    print(
        f"  !! WARNING: corpus may be TRUNCATED at {limit} issue(s) — the "
        f"enumeration returned exactly --limit ({limit}) issues, so the plan may "
        "be an INCOMPLETE view of the corpus. Re-run with a higher --limit to "
        "review the whole corpus (DEC-037 §2 — the report is the gate; a "
        "truncated plan reviewed as complete is an audit gap)."
    )
    print()


def _print_gate_pass(gate: GateResult) -> None:
    print("  Residual pre-check gate (auth / repo-access / map-parse):")
    for label, status, detail in gate.checks:
        marker = {"ok": "[ok]  ", "fail": "[fail]", "skip": "[skip]"}.get(status, "[?]")
        print(f"    {marker} {label} — {detail}")
    print("  → gate passed; proceeding under any merely-degraded axes (DEC-036).")
    print()


def _print_gate_refusal(gate: GateResult) -> None:
    print(
        "back-fill: REFUSED by the residual pre-check gate (DEC-037 §2).",
        file=sys.stderr,
    )
    print(
        "  The corpus back-fill gates on the residual hard-fail subset of "
        "pre-check — `gh` auth invalid, repo inaccessible, or substrate-map.yaml "
        "fails to parse. One of these failed:",
        file=sys.stderr,
    )
    for label, status, detail in gate.checks:
        if status == "fail":
            print(f"    [fail] {label} — {detail}", file=sys.stderr)
    print(
        "  A merely-degraded axis does NOT refuse the back-fill (DEC-036); only "
        "this residual subset does. Fix the failing prerequisite and re-run.",
        file=sys.stderr,
    )


def _print_report_from_plan(plan: dict[str, Any]) -> None:
    """Render the human-readable report from the machine-stable plan document.

    The report and the apply consume the SAME plan shape (the dict ``_derive_plan``
    builds), so the human report is a view over the exact plan T2b applies — there
    is no second representation to drift.
    """
    intents = plan.get("intents") or []
    proposed = plan.get("proposed") or []
    issue_count = len({c.get("issue_number") for c in proposed})

    print(f"  {len(intents)} back-fill intent(s) over {issue_count} corpus issue(s):")
    for intent in intents:
        print(f"    - {_describe_intent_dict(intent)}")
        print(f"      cite: {intent.get('citation', '')}")
    print()

    would_write = [c for c in proposed if c.get("prediction") == "would-write"]
    satisfied = [c for c in proposed if c.get("prediction") == "already-satisfied"]
    blocked = [c for c in proposed if c.get("prediction") == "blocked"]

    print(f"  Proposed per-issue changes ({len(proposed)} total):")
    for change in proposed:
        marker = {
            "would-write": "[write]  ",
            "already-satisfied": "[noop]   ",
            "blocked": "[blocked]",
        }.get(change.get("prediction"), "[?]      ")
        print(f"    {marker} #{change.get('issue_number')} {change.get('kind')}")
        if change.get("argv") is not None:
            print(f"               would run: {_render_argv(change['argv'])}")
        if change.get("observed") is not None:
            print(f"               observed: {change['observed']!r}")
        if change.get("prediction") == "already-satisfied":
            print("               (value already matches — likely a no-op; "
                  "re-validated at apply)")
        if change.get("prediction") == "blocked":
            print(f"               blocked: {change.get('blocked_reason', '')}")
    print()
    print(
        f"  Summary: {len(would_write)} would write, "
        f"{len(satisfied)} already satisfied (likely no-op), "
        f"{len(blocked)} blocked."
    )
    print(
        "  This report is the gate (DEC-037 §2). NO write has run. Apply this "
        "plan via `--apply` (or `--emit-script` for the draft form), which "
        "re-validates each issue at apply time (re-validate-at-apply) before "
        "writing."
    )


def _describe_intent_dict(intent: dict[str, Any]) -> str:
    if intent.get("kind") == "set-board-field":
        which = (
            f"single_select_option_id={intent.get('single_select_option_id')}"
            if intent.get("single_select_option_id")
            else f"text_value={intent.get('text_value')!r}"
        )
        return (
            f"set-board-field: Projects-v2 field_id={intent.get('field_id')} "
            f"→ {which} (across the corpus)"
        )
    return (
        f"assign-milestone: milestone={intent.get('milestone_title')!r} "
        "(across the corpus)"
    )


def _render_argv(argv: list[str]) -> str:
    """Render a constructed argv for human display (display only — not executed)."""
    out: list[str] = []
    for token in argv:
        out.append(f'"{token}"' if " " in token else token)
    return " ".join(out)


# ----- re-validate-at-apply: fresh per-issue reads (DEC-037 §2) -------


def _read_fresh_state(
    change: back_fill_apply.PlannedChange, config: dict[str, Any]
) -> back_fill_apply.FreshState:
    """Read THIS issue's current value for the change's attribute, at apply time.

    This is the re-validate-at-apply read (DEC-037 §2): the value the attribute
    holds *right now*, immediately before the write decision — never the plan's
    stale ``observed``. Routes by kind to the milestone read or the board
    field-value read. A read that fails returns ``read_ok=False`` so the predicate
    fails closed to a skip (never overwrite against an unconfirmed value).
    """
    try:
        if change.kind == "assign-milestone":
            return _read_current_milestone(change.issue_number, config)
        if change.kind == "set-board-field":
            return _read_current_field_value(change, config)
    except Exception:
        # Defensive backstop: a fresh read that throws (an unforeseen response
        # shape, a transport quirk) must NOT crash the whole corpus loop mid-apply.
        # Treat it as an indeterminate read → fail closed to a skip for THIS issue
        # (audited as drift), and let the loop continue. The per-issue reads above
        # already guard their own navigation; this catches anything they miss.
        return back_fill_apply.FreshState(current=None, read_ok=False)
    # Unknown kind — cannot confirm; fail closed.
    return back_fill_apply.FreshState(current=None, read_ok=False)


def _read_current_milestone(
    issue_number: int, config: dict[str, Any]
) -> back_fill_apply.FreshState:
    """The issue's current milestone title (or None if unset); read_ok False on a
    gh failure."""
    try:
        proc = gh_run(
            ["gh", "issue", "view", str(issue_number), "--json", "milestone"],
            config,
            check=False,
        )
    except FileNotFoundError:
        return back_fill_apply.FreshState(current=None, read_ok=False)
    if proc.returncode != 0:
        return back_fill_apply.FreshState(current=None, read_ok=False)
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return back_fill_apply.FreshState(current=None, read_ok=False)
    ms = data.get("milestone") if isinstance(data, dict) else None
    title = ms.get("title") if isinstance(ms, dict) else None
    return back_fill_apply.FreshState(
        current=title if isinstance(title, str) else None, read_ok=True
    )


def _read_current_field_value(
    change: back_fill_apply.PlannedChange, config: dict[str, Any]
) -> back_fill_apply.FreshState:
    """The board item's current single-select option id (or text) for the change's
    field — read via the Projects-v2 GraphQL field-values surface.

    Returns ``current`` as the option-id (single-select) or text the field carries
    now, matching what ``change.target`` compares against (the plan's target is the
    option-id or text). ``read_ok`` is True ONLY when the response positively
    confirms the current value — a successful payload whose ``fieldValues.nodes`` is
    a present list (an empty list is a genuine "unset"; a list containing the field
    is its value). Every non-confirming shape fails CLOSED (``read_ok=False``): a
    non-empty ``errors`` array (GraphQL returns exit 0 with ``errors`` populated and
    ``data`` null on rate-limits / transient errors), or a null/absent ``data`` /
    ``node`` / ``fieldValues`` at any navigation hop. Failing closed becomes a
    DRIFTED skip in :func:`classify_change` — never an overwrite against a value we
    could not actually read.

    This is a READ (a GraphQL ``query``, never the ``updateProjectV2ItemFieldValue``
    mutation) — it does not touch the corpus.
    """
    item_id = change.item_id
    field_id = change.field_id
    if not item_id or not field_id:
        return back_fill_apply.FreshState(current=None, read_ok=False)
    # Pull the item's field values; match the one whose field id equals field_id.
    # The query is the SINGLE shared constant the emit-script guard also consumes
    # (back_fill_apply.FIELD_REREAD_QUERY) — one source of truth, so the --apply
    # read and the emitted guard can never silently desync.
    query = back_fill_apply.FIELD_REREAD_QUERY
    try:
        proc = gh_run(
            ["gh", "api", "graphql", "-f", f"query={query}", "-F", f"item={item_id}"],
            config,
            check=False,
        )
    except FileNotFoundError:
        return back_fill_apply.FreshState(current=None, read_ok=False)
    if proc.returncode != 0:
        return back_fill_apply.FreshState(current=None, read_ok=False)
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return back_fill_apply.FreshState(current=None, read_ok=False)
    if not isinstance(payload, dict):
        return back_fill_apply.FreshState(current=None, read_ok=False)
    # GitHub GraphQL routinely returns exit 0 with a populated `errors` array and
    # a null `data`/`node`/`fieldValues` on rate-limits and transient errors. Any
    # of those means we did NOT positively read the current value, so we must fail
    # CLOSED (read_ok=False) — never treat an unread field as a confirmed unset
    # (which would classify as would-write and overwrite a value we never saw).
    # Only a successful response whose `fieldValues.nodes` is a PRESENT list yields
    # read_ok=True: an empty list `[]` is a genuine "no value", a list with the
    # field is the value, and anything else (null/absent at any hop) is fail-closed.
    if payload.get("errors"):
        return back_fill_apply.FreshState(current=None, read_ok=False)
    data = payload.get("data")
    node = data.get("node") if isinstance(data, dict) else None
    field_values = node.get("fieldValues") if isinstance(node, dict) else None
    nodes = field_values.get("nodes") if isinstance(field_values, dict) else None
    if not isinstance(nodes, list):
        # data / node / fieldValues / nodes was null or absent (as opposed to an
        # empty list) — the read did not positively confirm the current value.
        return back_fill_apply.FreshState(current=None, read_ok=False)
    for node in nodes:
        if not isinstance(node, dict):
            continue
        node_field = node.get("field") or {}
        if not isinstance(node_field, dict) or node_field.get("id") != field_id:
            continue
        value = node.get("optionId") or node.get("text")
        return back_fill_apply.FreshState(
            current=value if isinstance(value, str) else None, read_ok=True
        )
    # Field has no value on this item — confirmed unset.
    return back_fill_apply.FreshState(current=None, read_ok=True)


# ----- apply summary --------------------------------------------------


def _print_apply_summary(
    records: list[back_fill_apply.ApplyRecord],
    summary: back_fill_apply.ApplySummary,
) -> None:
    """Print the per-change audit + the failure summary (ADR-031 §6).

    Every change's outcome is shown (applied / skipped-idempotent / skipped-drift /
    blocked / failed) with its detail, then a one-line tally. The summary makes a
    write failure visible even when the loop continued past it — the operator must
    learn a mutation did not land."""
    marker = {
        back_fill_apply.ApplyOutcome.APPLIED: "[applied]  ",
        back_fill_apply.ApplyOutcome.SKIPPED_IDEMPOTENT: "[noop]     ",
        back_fill_apply.ApplyOutcome.SKIPPED_DRIFT: "[drift]    ",
        back_fill_apply.ApplyOutcome.BLOCKED: "[blocked]  ",
        back_fill_apply.ApplyOutcome.FAILED: "[FAILED]   ",
    }
    print()
    print("  Apply audit (DEC-037 §2 — re-validated each issue at apply time):")
    for r in records:
        print(f"    {marker[r.outcome]} #{r.issue_number} {r.kind}")
        if r.detail:
            print(f"                 → {r.detail}")
    print()
    print(
        f"  Summary: {summary.applied} applied, "
        f"{summary.skipped_idempotent} skipped (already satisfied), "
        f"{summary.skipped_drift} skipped (drift), "
        f"{summary.blocked} blocked, "
        f"{summary.failed} FAILED."
    )
    if summary.any_failed:
        print(
            "  ! One or more writes FAILED — exiting non-zero so the failure is "
            "not silent (the loop continued and applied every write it could; "
            "ADR-031 §6). Re-run to retry the failed writes (already-applied "
            "issues are skipped as idempotent)."
        )
    else:
        print(
            "  All writes that were attempted succeeded. Re-running is a no-op for "
            "the already-applied issues (value-equality idempotency)."
        )


# ----- shared resolution helpers -------------------------------------


def _resolve_repo_name_with_owner(config: dict[str, Any]) -> str:
    try:
        proc = gh_run(
            ["gh", "repo", "view", "--json", "nameWithOwner"], config, check=False
        )
    except FileNotFoundError:
        return "<unresolved>"
    if proc.returncode != 0:
        return "<unresolved>"
    try:
        return json.loads(proc.stdout).get("nameWithOwner", "<unresolved>")
    except json.JSONDecodeError:
        return "<unresolved>"


def _read_capability_version(capability_root: Path) -> str:
    pkg = capability_root / "package.yaml"
    if not pkg.is_file():
        return "<unknown>"
    try:
        from ruamel.yaml import YAML
        from ruamel.yaml.error import YAMLError
    except ImportError:  # pragma: no cover
        return "<unknown>"
    try:
        data = YAML(typ="safe").load(pkg.read_text(encoding="utf-8")) or {}
        return str(data.get("component", {}).get("version", "<unknown>"))
    except (OSError, YAMLError):
        return "<unknown>"


def _resolve_capability_root(explicit: Path | None) -> Path | None:
    if explicit is not None:
        return explicit if explicit.is_dir() else None
    cur = Path.cwd()
    while cur != cur.parent:
        candidate = cur / ".pkit" / "capabilities" / CAPABILITY_NAME
        if candidate.is_dir():
            return candidate
        cur = cur.parent
    return None


if __name__ == "__main__":
    sys.exit(main())
