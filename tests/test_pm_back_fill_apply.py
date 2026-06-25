"""Corpus back-fill — the APPLY engine (T2b, DEC-037 §2 / ADR-031 §5+§6).

The apply engine turns a reviewed plan into writes (``--apply``) or into an
idempotent script the adopter runs themselves (``--emit-script``). It is the
highest-blast-radius pm operation, so the four DEC-037 §2 safety properties are
the contract, and these tests pin every one of them — not just the happy path:

  * **clean apply** — would-write changes execute through the substrate_writes
    seam (never string-built); the loop reports applied;
  * **re-validate at apply / drift-skip** — an issue that drifted from the plan's
    enumeration since plan time is SKIPPED and reported, NOT overwritten;
  * **value-equality idempotency** — a change whose fresh-read current already
    equals the target is skipped; a re-run after a partial apply is a no-op for
    already-applied issues and COMPLETES THE REST (partial-apply recoverable);
  * **audited skip/report failure posture** — a write failure is recorded, the
    loop continues, and the summary surfaces a NON-ZERO exit (ADR-031 §6) — NOT
    DEC-024's report-and-continue-exit-0;
  * **--emit-script** — emits an idempotent re-checking script and executes NO
    write itself;
  * **residual-gate refusal** — a saved plan whose recorded gate failed is
    refused (property 3); a fresh apply re-runs the live gate;
  * **confirmation gate** — no silent bulk mutation; --yes / non-interactive
    behaviour matches the migrate-family posture;
  * **sole-constructor guard stays green** — covered by
    ``test_pm_substrate_write_seam`` over the whole scripts tree; here we pin that
    every executed write went through the seam by patching the seam's executors.

The predicates (``classify_change`` / ``exit_code_for`` / the emit-script
renderer) are MUTATION-TESTED: each test drives the boundary directly over
hand-built (target, fresh-read) pairs, so a green run proves the drift /
idempotency frontier, not merely that the happy path runs.

A brownfield FIXTURE corpus (``FIXTURE_ISSUES`` + a saved plan) grounds the
end-to-end cases in a concrete multi-issue, multi-intent shape.
"""

from __future__ import annotations

import importlib.util
import json
import shlex
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"
LIB_DIR = SCRIPTS_DIR / "_lib"
SCRIPT = SCRIPTS_DIR / "back-fill.py"

TARGET_REPO = "ai-platform-incubation/spyre"


@pytest.fixture(scope="module")
def apply_mod():
    """The apply engine module (`_lib/back_fill_apply.py`)."""
    if str(LIB_DIR) not in sys.path:
        sys.path.insert(0, str(LIB_DIR))
    spec = importlib.util.spec_from_file_location(
        "pm_back_fill_apply_under_test", LIB_DIR / "back_fill_apply.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["pm_back_fill_apply_under_test"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def bf():
    """The back-fill driver module (`back-fill.py`) for end-to-end main() tests."""
    sys.path.insert(0, str(SCRIPTS_DIR))
    spec = importlib.util.spec_from_file_location("pm_back_fill_driver_under_test", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["pm_back_fill_driver_under_test"] = module
    spec.loader.exec_module(module)
    return module


# ============================================================================
# The brownfield FIXTURE corpus + a saved plan over it
# ============================================================================
#
# A small but representative corpus: two intents (a Projects-v2 field-value
# `workstream=Spyre` and a milestone), four issues with varied current state —
# unset, already-satisfied, drifted, and not-on-board. Each end-to-end test
# layers a fresh-read stub over this so the apply decision is exercised against a
# realistic mix, not a single shape.


def _plan(intents: list[dict], proposed: list[dict], *, truncated: bool = False) -> dict:
    """Build a schema_version-1 plan document (the T2a `--json` shape)."""
    return {
        "schema_version": 1,
        "truncated": truncated,
        "residual_pre_check": {"passed": True, "checks": []},
        "intents": intents,
        "proposed": proposed,
    }


MILESTONE_INTENT = {
    "kind": "assign-milestone",
    "citation": "hook entry 0 (kind=assign-milestone) on after_create_issue",
    "field_id": None,
    "single_select_option_id": None,
    "text_value": None,
    "milestone_title": "Milestone 1",
}
FIELD_INTENT = {
    "kind": "set-board-field",
    "citation": "hook entry 1 (kind=set-board-field) on after_create_issue",
    "field_id": "FIELD_WS",
    "single_select_option_id": "OPT_SPYRE",
    "text_value": None,
    "milestone_title": None,
}


def _milestone_change(number: int, observed) -> dict:
    return {
        "issue_number": number,
        "issue_title": f"issue {number}",
        "kind": "assign-milestone",
        "citation": MILESTONE_INTENT["citation"],
        "argv": ["gh", "issue", "edit", str(number), "--milestone", "Milestone 1"],
        "observed": observed,
        "prediction": "would-write" if observed != "Milestone 1" else "already-satisfied",
        "blocked_reason": "",
    }


def _field_change(number: int, item_id: str | None) -> dict:
    if item_id is None:
        return {
            "issue_number": number,
            "issue_title": f"issue {number}",
            "kind": "set-board-field",
            "citation": FIELD_INTENT["citation"],
            "argv": None,
            "observed": None,
            "prediction": "blocked",
            "blocked_reason": f"issue not on the configured Projects v2 board ({number})",
        }
    return {
        "issue_number": number,
        "issue_title": f"issue {number}",
        "kind": "set-board-field",
        "citation": FIELD_INTENT["citation"],
        "argv": [
            "gh", "project", "item-edit",
            "--id", item_id, "--field-id", "FIELD_WS",
            "--project-id", "PROJ_NODE",
            "--single-select-option-id", "OPT_SPYRE",
        ],
        "observed": None,
        "prediction": "would-write",
        "blocked_reason": "",
    }


@pytest.fixture
def fixture_plan() -> dict:
    """A saved plan over the fixture corpus, used by the end-to-end tests."""
    return _plan(
        intents=[MILESTONE_INTENT, FIELD_INTENT],
        proposed=[
            _milestone_change(1, observed=None),            # unset → would-write
            _milestone_change(2, observed="Milestone 1"),   # already set → idempotent
            _milestone_change(3, observed=None),            # plan saw unset...
            _field_change(1, item_id="ITEM_1"),             # on board → would-write
            _field_change(4, item_id=None),                 # not on board → blocked
        ],
    )


# ============================================================================
# Property 1+2: classify_change — the re-validate / idempotency predicate
# (mutation-tested: drive the boundary directly)
# ============================================================================


def _change(apply_mod, *, target, observed, argv=("x",), kind="assign-milestone"):
    return apply_mod.PlannedChange(
        issue_number=1, kind=kind, target=target, observed=observed,
        argv=list(argv) if argv is not None else None,
    )


def test_classify_would_write_when_unset_and_no_drift(apply_mod) -> None:
    """The clean case: fresh current matches the plan's enumeration (no drift) and
    differs from the target → WOULD_WRITE."""
    change = _change(apply_mod, target="M1", observed=None)
    fresh = apply_mod.FreshState(current=None, read_ok=True)
    assert apply_mod.classify_change(change, fresh) is apply_mod.Disposition.WOULD_WRITE


def test_classify_already_satisfied_by_value_equality(apply_mod) -> None:
    """Property 2: fresh current already EQUALS the target → ALREADY_SATISFIED,
    regardless of what the plan enumerated. Value-equality, not presence."""
    change = _change(apply_mod, target="M1", observed=None)
    fresh = apply_mod.FreshState(current="M1", read_ok=True)
    assert apply_mod.classify_change(change, fresh) is apply_mod.Disposition.ALREADY_SATISFIED


def test_classify_drift_skips_when_current_differs_from_plan(apply_mod) -> None:
    """Property 1: the fresh current differs from the plan's enumerated `observed`
    (and is not the target) → DRIFTED → skip. A human edited the issue since plan
    time; never overwrite against stale enumeration."""
    change = _change(apply_mod, target="M2", observed=None)
    fresh = apply_mod.FreshState(current="HumanSetThis", read_ok=True)
    assert apply_mod.classify_change(change, fresh) is apply_mod.Disposition.DRIFTED


def test_classify_idempotent_wins_over_drift_when_human_set_target(apply_mod) -> None:
    """MUTATION-PROOF on the check ORDER: a human who concurrently set the field to
    EXACTLY the target is idempotent, not drift — we don't fight a write that is
    already done. ALREADY_SATISFIED must be checked before DRIFTED."""
    # plan enumerated None; human set it to the target M1 since.
    change = _change(apply_mod, target="M1", observed=None)
    fresh = apply_mod.FreshState(current="M1", read_ok=True)
    assert apply_mod.classify_change(change, fresh) is apply_mod.Disposition.ALREADY_SATISFIED


def test_classify_no_drift_when_current_matches_plan_observed(apply_mod) -> None:
    """MUTATION-PROOF on the drift predicate's reference: when the plan enumerated a
    non-None observed and the fresh read STILL equals it (no concurrent edit), and
    it differs from the target, the change is WOULD_WRITE — not a false drift."""
    change = _change(apply_mod, target="M2", observed="M1")
    fresh = apply_mod.FreshState(current="M1", read_ok=True)
    assert apply_mod.classify_change(change, fresh) is apply_mod.Disposition.WOULD_WRITE


def test_classify_indeterminate_read_fails_closed_to_skip(apply_mod) -> None:
    """The re-validate read itself failed (read_ok False) → fail CLOSED to a skip
    (reported as drift). Never overwrite against an unconfirmed current value —
    the write-path analogue of ADR-026's fail-closed."""
    change = _change(apply_mod, target="M1", observed=None)
    fresh = apply_mod.FreshState(current=None, read_ok=False)
    assert apply_mod.classify_change(change, fresh) is apply_mod.Disposition.DRIFTED


def test_classify_blocked_when_no_argv(apply_mod) -> None:
    """A change the plan never constructed a write for (argv None) → BLOCKED,
    checked first so it is never mistaken for a clean write or a no-op."""
    change = _change(apply_mod, target="M1", observed=None, argv=None)
    fresh = apply_mod.FreshState(current="anything", read_ok=True)
    assert apply_mod.classify_change(change, fresh) is apply_mod.Disposition.BLOCKED


# ============================================================================
# The apply loop: clean apply, drift-skip, idempotency, write-failure
# ============================================================================


def _milestone_planned(apply_mod, number, *, target, observed, argv=True):
    return apply_mod.PlannedChange(
        issue_number=number, kind="assign-milestone", target=target, observed=observed,
        argv=(["gh", "issue", "edit", str(number), "--milestone", target] if argv else None),
    )


def test_clean_apply_executes_writes_through_the_seam(apply_mod, monkeypatch) -> None:
    """Clean apply: a would-write change runs THROUGH substrate_writes.write_milestone
    (the seam, ADR-031) — not a string-built gh call — and is recorded applied."""
    seam_calls: list[tuple] = []

    def fake_write_milestone(config, *, issue_number, title):
        seam_calls.append(("milestone", issue_number, title))
        return apply_mod.substrate_writes.SubstrateWriteResult(
            ok=True, executed=True, argv=("gh", "issue", "edit", str(issue_number),
                                          "--milestone", title), detail="set",
        )

    monkeypatch.setattr(apply_mod.substrate_writes, "write_milestone", fake_write_milestone)

    changes = [_milestone_planned(apply_mod, 1, target="M1", observed=None)]
    records = apply_mod.apply_plan(
        changes, {}, read_fresh=lambda c: apply_mod.FreshState(current=None, read_ok=True)
    )
    assert [r.outcome for r in records] == [apply_mod.ApplyOutcome.APPLIED]
    # The write went through the seam executor, with the right inputs.
    assert seam_calls == [("milestone", 1, "M1")]


def test_drift_skip_does_not_overwrite(apply_mod, monkeypatch) -> None:
    """Property 1 end-to-end: an issue that drifted since plan time is SKIPPED and
    reported as drift — the seam executor is NEVER called for it (no overwrite)."""
    called = {"wrote": False}

    def fake_write_milestone(config, **kw):
        called["wrote"] = True
        return apply_mod.substrate_writes.SubstrateWriteResult(ok=True, executed=True)

    monkeypatch.setattr(apply_mod.substrate_writes, "write_milestone", fake_write_milestone)

    changes = [_milestone_planned(apply_mod, 7, target="M2", observed=None)]
    # Fresh read shows a human-set value (drift from the plan's None, not the target).
    records = apply_mod.apply_plan(
        changes, {},
        read_fresh=lambda c: apply_mod.FreshState(current="HumanSet", read_ok=True),
    )
    assert [r.outcome for r in records] == [apply_mod.ApplyOutcome.SKIPPED_DRIFT]
    assert called["wrote"] is False, "a drifted issue must NOT be overwritten"


def test_value_equality_idempotency_skips_already_set(apply_mod, monkeypatch) -> None:
    """Property 2: a change whose fresh current already equals the target is skipped
    idempotent — no write issued."""
    called = {"wrote": False}

    def fake_write_milestone(config, **kw):
        called["wrote"] = True
        return apply_mod.substrate_writes.SubstrateWriteResult(ok=True, executed=True)

    monkeypatch.setattr(apply_mod.substrate_writes, "write_milestone", fake_write_milestone)

    changes = [_milestone_planned(apply_mod, 2, target="M1", observed="M1")]
    records = apply_mod.apply_plan(
        changes, {},
        read_fresh=lambda c: apply_mod.FreshState(current="M1", read_ok=True),
    )
    assert [r.outcome for r in records] == [apply_mod.ApplyOutcome.SKIPPED_IDEMPOTENT]
    assert called["wrote"] is False


def test_partial_apply_rerun_is_noop_for_applied_and_completes_rest(
    apply_mod, monkeypatch
) -> None:
    """Property 2 (recoverability): simulate a re-run after a partial apply that
    died after issue 1. On the re-run, issue 1's fresh read equals the target (it
    was applied) → skipped idempotent; issue 2 is still unset → applied. The re-run
    is a no-op for the already-done one and COMPLETES THE REST."""
    written: list[int] = []

    def fake_write_milestone(config, *, issue_number, title):
        written.append(issue_number)
        return apply_mod.substrate_writes.SubstrateWriteResult(ok=True, executed=True, detail="ok")

    monkeypatch.setattr(apply_mod.substrate_writes, "write_milestone", fake_write_milestone)

    changes = [
        _milestone_planned(apply_mod, 1, target="M1", observed=None),
        _milestone_planned(apply_mod, 2, target="M1", observed=None),
    ]
    # Re-run state: #1 already carries M1 (applied last time), #2 still unset.
    fresh_by_issue = {1: "M1", 2: None}
    records = apply_mod.apply_plan(
        changes, {},
        read_fresh=lambda c: apply_mod.FreshState(
            current=fresh_by_issue[c.issue_number], read_ok=True
        ),
    )
    outcomes = {r.issue_number: r.outcome for r in records}
    assert outcomes[1] is apply_mod.ApplyOutcome.SKIPPED_IDEMPOTENT
    assert outcomes[2] is apply_mod.ApplyOutcome.APPLIED
    assert written == [2], "the re-run must only write the not-yet-applied issue"


def test_write_failure_is_audited_loop_continues_and_exit_nonzero(
    apply_mod, monkeypatch
) -> None:
    """Failure posture (ADR-031 §6): a write FAILURE is recorded, the loop CONTINUES
    to the next change, and the summary yields a NON-ZERO exit — NOT report-and-
    continue-exit-0. The second (good) write still lands."""
    def fake_write_milestone(config, *, issue_number, title):
        if issue_number == 1:
            return apply_mod.substrate_writes.SubstrateWriteResult(
                ok=False, executed=True, error="boom", detail="gh failed: boom",
            )
        return apply_mod.substrate_writes.SubstrateWriteResult(ok=True, executed=True, detail="ok")

    monkeypatch.setattr(apply_mod.substrate_writes, "write_milestone", fake_write_milestone)

    changes = [
        _milestone_planned(apply_mod, 1, target="M1", observed=None),
        _milestone_planned(apply_mod, 2, target="M1", observed=None),
    ]
    records = apply_mod.apply_plan(
        changes, {},
        read_fresh=lambda c: apply_mod.FreshState(current=None, read_ok=True),
    )
    outcomes = {r.issue_number: r.outcome for r in records}
    assert outcomes[1] is apply_mod.ApplyOutcome.FAILED
    assert outcomes[2] is apply_mod.ApplyOutcome.APPLIED  # loop continued past the failure

    summary = apply_mod.summarise(records)
    assert summary.failed == 1 and summary.applied == 1
    assert apply_mod.exit_code_for(summary) == 1, "any failure must surface non-zero"


def test_blocked_change_is_recorded_not_written(apply_mod, monkeypatch) -> None:
    """A blocked change (no argv) is recorded blocked and never executed — and a
    blocked-only batch is exit 0 (a block is not a failure)."""
    monkeypatch.setattr(
        apply_mod.substrate_writes, "write_field_value",
        lambda *a, **k: pytest.fail("a blocked change must not be written"),
    )
    changes = [apply_mod.PlannedChange(
        issue_number=9, kind="set-board-field", target="OPT", observed=None,
        argv=None, blocked_reason="issue not on board",
    )]
    records = apply_mod.apply_plan(
        changes, {}, read_fresh=lambda c: apply_mod.FreshState(current=None, read_ok=True)
    )
    assert records[0].outcome is apply_mod.ApplyOutcome.BLOCKED
    assert apply_mod.exit_code_for(apply_mod.summarise(records)) == 0


def test_field_value_apply_routes_through_the_seam(apply_mod, monkeypatch) -> None:
    """A field-value would-write executes through substrate_writes.write_field_value
    with the item/field/project ids the plan pinned — the seam, not an inline build."""
    captured: dict = {}

    def fake_write_field_value(config, **kw):
        captured.update(kw)
        return apply_mod.substrate_writes.SubstrateWriteResult(ok=True, executed=True, detail="set")

    monkeypatch.setattr(apply_mod.substrate_writes, "write_field_value", fake_write_field_value)

    change = apply_mod.PlannedChange(
        issue_number=1, kind="set-board-field", target="OPT_SPYRE", observed=None,
        argv=["gh", "project", "item-edit", "--id", "ITEM_1"],
        item_id="ITEM_1", field_id="FIELD_WS", project_id="PROJ_NODE",
        single_select_option_id="OPT_SPYRE",
    )
    records = apply_mod.apply_plan(
        [change], {}, read_fresh=lambda c: apply_mod.FreshState(current=None, read_ok=True)
    )
    assert records[0].outcome is apply_mod.ApplyOutcome.APPLIED
    assert captured["item_id"] == "ITEM_1"
    assert captured["field_id"] == "FIELD_WS"
    assert captured["single_select_option_id"] == "OPT_SPYRE"


# ============================================================================
# exit_code_for — mutation-tested boundary
# ============================================================================


def test_exit_code_zero_when_no_failure(apply_mod) -> None:
    s = apply_mod.ApplySummary(
        applied=3, skipped_idempotent=2, skipped_drift=1, blocked=1, failed=0
    )
    assert apply_mod.exit_code_for(s) == 0


def test_exit_code_one_when_any_failure(apply_mod) -> None:
    """MUTATION-PROOF: a single failure flips the code, even amid many successes —
    so a bulk apply that failed one write is never mistaken for clean."""
    s = apply_mod.ApplySummary(
        applied=99, skipped_idempotent=0, skipped_drift=0, blocked=0, failed=1
    )
    assert apply_mod.exit_code_for(s) == 1


def test_skips_and_blocks_are_not_failures(apply_mod) -> None:
    """A corpus that was entirely skipped (drift / idempotent) or blocked is exit 0
    — the audited posture working as designed, not an error."""
    s = apply_mod.ApplySummary(
        applied=0, skipped_idempotent=5, skipped_drift=3, blocked=2, failed=0
    )
    assert apply_mod.exit_code_for(s) == 0


# ============================================================================
# --emit-script: idempotent, re-checking, executes NO write
# ============================================================================


def test_emit_script_executes_no_write(apply_mod, monkeypatch) -> None:
    """The draft-not-apply form: rendering the script calls NO seam executor — it
    is pure text. pm never touches the corpus in this mode (DEC-037 §2)."""
    monkeypatch.setattr(
        apply_mod.substrate_writes, "write_milestone",
        lambda *a, **k: pytest.fail("emit-script must execute no write"),
    )
    monkeypatch.setattr(
        apply_mod.substrate_writes, "write_field_value",
        lambda *a, **k: pytest.fail("emit-script must execute no write"),
    )
    changes = [_milestone_planned(apply_mod, 1, target="M1", observed=None)]
    script = apply_mod.render_emit_script(changes)
    # M1 has no space → renders unquoted.
    assert "gh issue edit 1 --milestone M1" in script


def test_emit_script_is_idempotent_by_recheck(apply_mod) -> None:
    """The emitted milestone write is guarded by a fresh value re-read that skips
    when the current milestone already equals the target — so the script is safe to
    re-run (property 2 pushed into the script)."""
    changes = [_milestone_planned(apply_mod, 5, target="Milestone 1", observed=None)]
    script = apply_mod.render_emit_script(changes)
    # Guarded: reads current, compares to target, only writes on difference.
    assert "gh issue view 5 --json milestone" in script
    assert 'if [ "$current" != ' in script
    assert "already satisfied" in script
    # set -euo pipefail makes a partial run fail loudly rather than silently skip.
    assert "set -euo pipefail" in script


def test_emit_script_uses_the_plans_exact_argv(apply_mod) -> None:
    """The emitted write renders the plan's exact reviewed argv verbatim (shlex-
    quoted) — what runs is what the human reviewed, not a re-derivation."""
    change = apply_mod.PlannedChange(
        issue_number=3, kind="assign-milestone", target="My Milestone", observed=None,
        argv=["gh", "issue", "edit", "3", "--milestone", "My Milestone"],
    )
    script = apply_mod.render_emit_script([change])
    # The space in the title forces shlex quoting — the reviewed argv is preserved.
    assert "gh issue edit 3 --milestone 'My Milestone'" in script


def test_emit_script_renders_blocked_as_comment(apply_mod) -> None:
    """A blocked change (no argv) is emitted as a commented note, not a broken
    write line."""
    change = apply_mod.PlannedChange(
        issue_number=4, kind="set-board-field", target="OPT", observed=None,
        argv=None, blocked_reason="issue not on board",
    )
    script = apply_mod.render_emit_script([change])
    assert "# [blocked] #4" in script
    assert "issue not on board" in script


def test_emit_script_warns_on_truncation(apply_mod) -> None:
    changes = [_milestone_planned(apply_mod, 1, target="M1", observed=None)]
    script = apply_mod.render_emit_script(changes, truncated=True)
    assert "TRUNCATED" in script


# ============================================================================
# Property 3: residual-gate refusal on a saved plan
# ============================================================================


def test_saved_plan_with_failed_gate_is_refused(apply_mod) -> None:
    """Property 3: a saved plan whose recorded residual gate did NOT pass is refused
    — applying anyway writes against the prerequisites the gate protects."""
    plan = _plan(intents=[MILESTONE_INTENT], proposed=[])
    plan["residual_pre_check"]["passed"] = False
    refusal = apply_mod.refuse_if_gate_failed(plan)
    assert refusal is not None
    assert "did NOT pass" in refusal


def test_saved_plan_with_no_gate_block_is_refused(apply_mod) -> None:
    """A saved plan missing the residual_pre_check block cannot confirm the gate
    passed → refuse (fail closed)."""
    plan = {"schema_version": 1, "intents": [], "proposed": []}
    assert apply_mod.refuse_if_gate_failed(plan) is not None


def test_saved_plan_with_passing_gate_is_accepted(apply_mod) -> None:
    plan = _plan(intents=[MILESTONE_INTENT], proposed=[])
    assert apply_mod.refuse_if_gate_failed(plan) is None


def test_schema_version_is_pinned(apply_mod) -> None:
    """A saved plan of an unrecognised schema_version is not consumable — refuse
    rather than mis-apply a plan whose shape this engine cannot read."""
    assert apply_mod.plan_schema_ok({"schema_version": 1}) is True
    assert apply_mod.plan_schema_ok({"schema_version": 2}) is False
    assert apply_mod.plan_schema_ok({}) is False


# ============================================================================
# planned_changes_from_plan — reconstruct apply inputs from a saved plan
# ============================================================================


def test_planned_changes_recover_target_and_seam_inputs(apply_mod, fixture_plan) -> None:
    """The apply inputs are reconstructed from the saved plan: the milestone target
    from the intent; the field write's item/field/project ids from the plan's EXACT
    argv flag values (not re-derived)."""
    changes = apply_mod.planned_changes_from_plan(fixture_plan)
    by = {(c.issue_number, c.kind): c for c in changes}

    ms = by[(1, "assign-milestone")]
    assert ms.target == "Milestone 1"

    field = by[(1, "set-board-field")]
    assert field.target == "OPT_SPYRE"
    assert field.item_id == "ITEM_1"           # recovered from argv --id
    assert field.field_id == "FIELD_WS"
    assert field.project_id == "PROJ_NODE"     # recovered from argv --project-id
    assert field.single_select_option_id == "OPT_SPYRE"

    blocked = by[(4, "set-board-field")]
    assert blocked.argv is None
    assert "not on" in blocked.blocked_reason


# ============================================================================
# End-to-end through back-fill.py main(): --apply, --emit-script, confirmation
# ============================================================================


def _write_plan_file(tmp_path: Path, plan: dict) -> Path:
    p = tmp_path / "plan.json"
    p.write_text(json.dumps(plan), encoding="utf-8")
    return p


def _stub_live_gate_passing(bf, monkeypatch) -> None:
    """Stub the saved-plan live residual gate (G1) to PASS.

    The saved-plan apply path re-runs the live residual gate (G1) before applying,
    which would otherwise shell out to the real ``pre-check.py`` (real ``gh`` auth /
    repo probes). Tests that target the apply loop — not the gate — stub it to a
    clean pass so they exercise the write decision in isolation. The dedicated G1
    test stubs it to FAIL instead, and asserts the refusal."""
    monkeypatch.setattr(
        bf, "_residual_gate_for_saved_plan",
        lambda _plan, _config, _root: bf.GateResult(passed=True, checks=[]),
    )


def _patch_all_gh(bf, monkeypatch, fake_gh_run) -> None:
    """Patch EVERY gh entry point the apply path can reach, so no real `gh` runs.

    The apply loop executes writes through ``bf.back_fill_apply.substrate_writes``
    (the exact module object the driver's apply engine calls — its ``gh_run`` name
    is the binding the seam's ``_gh_call`` uses). The fresh reads go through
    ``bf.gh_run``. Patching both — plus the shared ``_lib.gh`` source — captures any
    reachable call regardless of which import binding reaches it."""
    monkeypatch.setattr(bf, "gh_run", fake_gh_run)
    monkeypatch.setattr(bf.back_fill_apply.substrate_writes, "gh_run", fake_gh_run)
    if str(LIB_DIR) not in sys.path:
        sys.path.insert(0, str(LIB_DIR))
    import gh as gh_source  # the `_lib.gh` module
    monkeypatch.setattr(gh_source, "gh_run", fake_gh_run)


def test_main_emit_script_from_saved_plan_writes_no_corpus(
    bf, tmp_path, monkeypatch, capsys
) -> None:
    """End-to-end: `--emit-script --plan <file>` prints a script and issues NO
    mutating gh call (caught at the shared seam)."""
    plan = _plan(
        intents=[MILESTONE_INTENT],
        proposed=[_milestone_change(1, observed=None)],
    )
    plan_file = _write_plan_file(tmp_path, plan)

    issued: list[list[str]] = []

    def fake_gh_run(args, config=None, **kw):
        issued.append(list(args))
        return subprocess.CompletedProcess(args, 0, stdout="{}", stderr="")

    _patch_all_gh(bf, monkeypatch, fake_gh_run)
    _stub_live_gate_passing(bf, monkeypatch)
    monkeypatch.setattr(bf, "load_adopter_config", lambda _r: {})
    monkeypatch.setattr(
        sys, "argv",
        ["back-fill.py", "--capability-root", str(tmp_path), "--emit-script",
         "--plan", str(plan_file)],
    )
    rc = bf.main()
    assert rc == 0
    out = capsys.readouterr().out
    # The argv is shlex-quoted; "Milestone 1" carries a space → single-quoted.
    assert "gh issue edit 1 --milestone 'Milestone 1'" in out
    # No write was executed by pm in emit-script mode — nothing reached gh at all.
    assert issued == [], "emit-script must execute no gh call from this process"


def test_main_apply_from_saved_plan_clean(bf, tmp_path, monkeypatch, capsys) -> None:
    """End-to-end clean apply: `--apply --plan <file> --yes` re-validates each issue
    (fresh reads stubbed to unset), writes through the seam, and exits 0."""
    plan = _plan(
        intents=[MILESTONE_INTENT],
        proposed=[_milestone_change(1, observed=None), _milestone_change(2, observed=None)],
    )
    plan_file = _write_plan_file(tmp_path, plan)

    writes: list[int] = []

    def fake_gh_run(args, config=None, **kw):
        # Fresh-read: every issue's milestone is unset (so all would-write).
        if args[:3] == ["gh", "issue", "view"]:
            return subprocess.CompletedProcess(
                args, 0, stdout=json.dumps({"milestone": None}), stderr="")
        # The write itself.
        if args[:3] == ["gh", "issue", "edit"] and "--milestone" in args:
            writes.append(int(args[3]))
            return subprocess.CompletedProcess(args, 0, stdout="", stderr="")
        return subprocess.CompletedProcess(args, 0, stdout="{}", stderr="")

    _patch_all_gh(bf, monkeypatch, fake_gh_run)
    _stub_live_gate_passing(bf, monkeypatch)
    monkeypatch.setattr(bf, "load_adopter_config", lambda _r: {})
    monkeypatch.setattr(
        sys, "argv",
        ["back-fill.py", "--capability-root", str(tmp_path), "--apply",
         "--plan", str(plan_file), "--yes"],
    )
    rc = bf.main()
    assert rc == 0
    assert sorted(writes) == [1, 2]
    out = capsys.readouterr().out
    assert "2 applied" in out


def test_main_apply_drift_skip_end_to_end(bf, tmp_path, monkeypatch, capsys) -> None:
    """End-to-end drift: an issue whose fresh milestone read differs from the plan's
    enumeration is SKIPPED (drift) and NOT written; the summary reports it."""
    plan = _plan(
        intents=[MILESTONE_INTENT],
        proposed=[_milestone_change(1, observed=None)],  # plan saw unset
    )
    plan_file = _write_plan_file(tmp_path, plan)

    writes: list[int] = []

    def fake_gh_run(args, config=None, **kw):
        if args[:3] == ["gh", "issue", "view"]:
            # The human set a DIFFERENT milestone since plan time → drift.
            return subprocess.CompletedProcess(
                args, 0, stdout=json.dumps({"milestone": {"title": "HumanChose"}}), stderr="")
        if args[:3] == ["gh", "issue", "edit"] and "--milestone" in args:
            writes.append(int(args[3]))
            return subprocess.CompletedProcess(args, 0, stdout="", stderr="")
        return subprocess.CompletedProcess(args, 0, stdout="{}", stderr="")

    _patch_all_gh(bf, monkeypatch, fake_gh_run)
    _stub_live_gate_passing(bf, monkeypatch)
    monkeypatch.setattr(bf, "load_adopter_config", lambda _r: {})
    monkeypatch.setattr(
        sys, "argv",
        ["back-fill.py", "--capability-root", str(tmp_path), "--apply",
         "--plan", str(plan_file), "--yes"],
    )
    rc = bf.main()
    assert rc == 0
    assert writes == [], "a drifted issue must NOT be overwritten"
    out = capsys.readouterr().out
    assert "1 skipped (drift)" in out


def test_main_apply_write_failure_exits_nonzero(bf, tmp_path, monkeypatch, capsys) -> None:
    """End-to-end failure posture: a write that fails is audited, the loop continues,
    and main() exits NON-ZERO (ADR-031 §6)."""
    plan = _plan(
        intents=[MILESTONE_INTENT],
        proposed=[_milestone_change(1, observed=None), _milestone_change(2, observed=None)],
    )
    plan_file = _write_plan_file(tmp_path, plan)

    def fake_gh_run(args, config=None, **kw):
        if args[:3] == ["gh", "issue", "view"]:
            return subprocess.CompletedProcess(
                args, 0, stdout=json.dumps({"milestone": None}), stderr="")
        if args[:3] == ["gh", "issue", "edit"] and "--milestone" in args:
            if args[3] == "1":
                return subprocess.CompletedProcess(args, 1, stdout="", stderr="permission denied")
            return subprocess.CompletedProcess(args, 0, stdout="", stderr="")
        return subprocess.CompletedProcess(args, 0, stdout="{}", stderr="")

    _patch_all_gh(bf, monkeypatch, fake_gh_run)
    _stub_live_gate_passing(bf, monkeypatch)
    monkeypatch.setattr(bf, "load_adopter_config", lambda _r: {})
    monkeypatch.setattr(
        sys, "argv",
        ["back-fill.py", "--capability-root", str(tmp_path), "--apply",
         "--plan", str(plan_file), "--yes"],
    )
    rc = bf.main()
    assert rc == 1, "a write failure must surface a non-zero exit"
    out = capsys.readouterr().out
    assert "1 FAILED" in out
    assert "1 applied" in out  # the loop continued past the failure


def test_main_apply_refuses_saved_plan_with_failed_gate(bf, tmp_path, monkeypatch, capsys) -> None:
    """A saved plan whose recorded gate failed is refused (exit 2) before any read
    or write (property 3)."""
    plan = _plan(intents=[MILESTONE_INTENT], proposed=[_milestone_change(1, observed=None)])
    plan["residual_pre_check"]["passed"] = False
    plan_file = _write_plan_file(tmp_path, plan)

    monkeypatch.setattr(
        bf, "gh_run",
        lambda *a, **k: pytest.fail("a refused plan must issue no gh call"),
    )
    monkeypatch.setattr(bf, "load_adopter_config", lambda _r: {})
    monkeypatch.setattr(
        sys, "argv",
        ["back-fill.py", "--capability-root", str(tmp_path), "--apply",
         "--plan", str(plan_file), "--yes"],
    )
    rc = bf.main()
    assert rc == 2
    assert "REFUSED" in capsys.readouterr().err


def test_main_apply_refuses_unknown_schema_version(bf, tmp_path, monkeypatch, capsys) -> None:
    plan = {"schema_version": 99, "residual_pre_check": {"passed": True}, "proposed": []}
    plan_file = _write_plan_file(tmp_path, plan)
    monkeypatch.setattr(bf, "load_adopter_config", lambda _r: {})
    monkeypatch.setattr(
        sys, "argv",
        ["back-fill.py", "--capability-root", str(tmp_path), "--apply",
         "--plan", str(plan_file), "--yes"],
    )
    rc = bf.main()
    assert rc == 2
    assert "schema_version" in capsys.readouterr().err


def test_main_apply_declines_in_non_interactive_without_yes(
    bf, tmp_path, monkeypatch, capsys
) -> None:
    """Confirmation gate (DEC-037 §2): no --yes and a non-interactive shell → the
    apply is DECLINED (exit 2) and nothing is written. No silent bulk mutation."""
    plan = _plan(intents=[MILESTONE_INTENT], proposed=[_milestone_change(1, observed=None)])
    plan_file = _write_plan_file(tmp_path, plan)

    def fake_gh_run(args, config=None, **kw):
        # A read is fine; a write would be a violation of the gate.
        if args[:3] == ["gh", "issue", "edit"] and "--milestone" in args:
            pytest.fail("nothing may be written when the confirmation gate declines")
        return subprocess.CompletedProcess(args, 0, stdout="{}", stderr="")

    monkeypatch.setattr(bf, "gh_run", fake_gh_run)
    _stub_live_gate_passing(bf, monkeypatch)
    monkeypatch.setattr(bf, "load_adopter_config", lambda _r: {})
    # Force non-interactive.
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    monkeypatch.setattr(
        sys, "argv",
        ["back-fill.py", "--capability-root", str(tmp_path), "--apply",
         "--plan", str(plan_file)],  # NO --yes
    )
    rc = bf.main()
    assert rc == 2
    out = capsys.readouterr().out
    assert "declined" in out.lower()


def test_main_apply_yes_pre_approves(bf, tmp_path, monkeypatch, capsys) -> None:
    """`--yes` pre-approves the confirmation even non-interactively (CI path),
    mirroring migrate's escape hatch — the write proceeds."""
    plan = _plan(intents=[MILESTONE_INTENT], proposed=[_milestone_change(1, observed=None)])
    plan_file = _write_plan_file(tmp_path, plan)
    wrote = {"n": 0}

    def fake_gh_run(args, config=None, **kw):
        if args[:3] == ["gh", "issue", "view"]:
            return subprocess.CompletedProcess(
                args, 0, stdout=json.dumps({"milestone": None}), stderr="")
        if args[:3] == ["gh", "issue", "edit"] and "--milestone" in args:
            wrote["n"] += 1
            return subprocess.CompletedProcess(args, 0, stdout="", stderr="")
        return subprocess.CompletedProcess(args, 0, stdout="{}", stderr="")

    _patch_all_gh(bf, monkeypatch, fake_gh_run)
    _stub_live_gate_passing(bf, monkeypatch)
    monkeypatch.setattr(bf, "load_adopter_config", lambda _r: {})
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    monkeypatch.setattr(
        sys, "argv",
        ["back-fill.py", "--capability-root", str(tmp_path), "--apply",
         "--plan", str(plan_file), "--yes"],
    )
    rc = bf.main()
    assert rc == 0
    assert wrote["n"] == 1


def test_main_rejects_plan_in_report_mode(bf, tmp_path, monkeypatch, capsys) -> None:
    """--plan only applies to --apply / --emit-script; passing it to the report
    phase is a usage error (the report derives its own plan live)."""
    plan_file = _write_plan_file(tmp_path, _plan([], []))
    monkeypatch.setattr(bf, "load_adopter_config", lambda _r: {})
    monkeypatch.setattr(
        sys, "argv",
        ["back-fill.py", "--capability-root", str(tmp_path), "--plan", str(plan_file)],
    )
    rc = bf.main()
    assert rc == 2
    assert "--plan applies only to" in capsys.readouterr().err


# ============================================================================
# Fresh-read functions (the re-validate-at-apply reads) — fail closed
# ============================================================================


def test_fresh_milestone_read_returns_current_title(bf, monkeypatch, apply_mod) -> None:
    def fake_gh_run(args, config, **kw):
        return subprocess.CompletedProcess(
            args, 0, stdout=json.dumps({"milestone": {"title": "M1"}}), stderr="")

    monkeypatch.setattr(bf, "gh_run", fake_gh_run)
    change = apply_mod.PlannedChange(
        issue_number=1, kind="assign-milestone", target="M1", observed=None, argv=["x"]
    )
    fresh = bf._read_fresh_state(change, {})
    assert fresh.current == "M1"
    assert fresh.read_ok is True


def test_fresh_milestone_read_fails_closed_on_gh_error(bf, monkeypatch, apply_mod) -> None:
    """A gh failure on the re-validate read → read_ok False, so classify fails
    closed to skip (never overwrite against an unconfirmed value)."""
    def fake_gh_run(args, config, **kw):
        return subprocess.CompletedProcess(args, 1, stdout="", stderr="boom")

    monkeypatch.setattr(bf, "gh_run", fake_gh_run)
    change = apply_mod.PlannedChange(
        issue_number=1, kind="assign-milestone", target="M1", observed=None, argv=["x"]
    )
    fresh = bf._read_fresh_state(change, {})
    assert fresh.read_ok is False


def test_fresh_field_value_read_matches_field_id(bf, monkeypatch, apply_mod) -> None:
    """The field-value re-read returns the option id of the matching field (by
    field id) from the GraphQL field-values surface."""
    def fake_gh_run(args, config, **kw):
        return subprocess.CompletedProcess(
            args, 0,
            stdout=json.dumps({"data": {"node": {"fieldValues": {"nodes": [
                {"optionId": "OPT_OTHER", "field": {"id": "FIELD_OTHER"}},
                {"optionId": "OPT_SPYRE", "field": {"id": "FIELD_WS"}},
            ]}}}}),
            stderr="")

    monkeypatch.setattr(bf, "gh_run", fake_gh_run)
    change = apply_mod.PlannedChange(
        issue_number=1, kind="set-board-field", target="OPT_SPYRE", observed=None,
        argv=["x"], item_id="ITEM_1", field_id="FIELD_WS",
    )
    fresh = bf._read_fresh_state(change, {})
    assert fresh.current == "OPT_SPYRE"
    assert fresh.read_ok is True


def test_fresh_field_value_read_confirmed_unset_when_field_absent(
    bf, monkeypatch, apply_mod
) -> None:
    """When the item carries no value for the field, the read is a CONFIRMED unset
    (read_ok True, current None) — not a failure. So an unset field is a clean
    would-write, not a fail-closed skip."""
    def fake_gh_run(args, config, **kw):
        return subprocess.CompletedProcess(
            args, 0,
            stdout=json.dumps({"data": {"node": {"fieldValues": {"nodes": []}}}}),
            stderr="")

    monkeypatch.setattr(bf, "gh_run", fake_gh_run)
    change = apply_mod.PlannedChange(
        issue_number=1, kind="set-board-field", target="OPT_SPYRE", observed=None,
        argv=["x"], item_id="ITEM_1", field_id="FIELD_WS",
    )
    fresh = bf._read_fresh_state(change, {})
    assert fresh.current is None
    assert fresh.read_ok is True


def test_field_value_read_does_not_issue_a_mutation(bf, monkeypatch, apply_mod) -> None:
    """The re-validate field read is a GraphQL QUERY, never the
    updateProjectV2ItemFieldValue mutation — the read must not mutate the corpus."""
    seen: list[str] = []

    def fake_gh_run(args, config, **kw):
        seen.append(" ".join(args))
        return subprocess.CompletedProcess(
            args, 0, stdout=json.dumps({"data": {"node": {"fieldValues": {"nodes": []}}}}),
            stderr="")

    monkeypatch.setattr(bf, "gh_run", fake_gh_run)
    change = apply_mod.PlannedChange(
        issue_number=1, kind="set-board-field", target="OPT", observed=None,
        argv=["x"], item_id="ITEM_1", field_id="FIELD_WS",
    )
    bf._read_fresh_state(change, {})
    assert seen, "the field read should have issued a gh call"
    assert not any("updateProjectV2ItemFieldValue" in s for s in seen)
    assert all("mutation" not in s.lower() for s in seen)


def test_apply_and_emit_field_reread_share_one_query_constant(
    bf, apply_mod, monkeypatch
) -> None:
    """The --apply field read and the emit-script field guard must read the SAME
    GraphQL query — one shared source of truth (back_fill_apply.FIELD_REREAD_QUERY),
    not two byte-identical literals that a future edit could silently desync.

    Asserts both consume the one constant: (a) the emitted guard embeds it, and
    (b) the apply path's fresh read issues it. If either site forks to its own
    literal, this fails."""
    # The single shared constant exists in the _lib module.
    shared = apply_mod.FIELD_REREAD_QUERY
    assert "ProjectV2ItemFieldSingleSelectValue" in shared  # sanity: it's the query.

    # (a) the emit-script field guard embeds the shared constant verbatim.
    change = _field_planned(apply_mod, 1, target="OPT_TARGET", observed=None)
    script = apply_mod.render_emit_script([change])
    assert shared in script, "the emit guard must embed the shared query constant"

    # (b) the --apply fresh read issues the shared constant (captured off gh args).
    seen: list[list[str]] = []

    def fake_gh_run(args, config, **kw):
        seen.append(list(args))
        return subprocess.CompletedProcess(
            args, 0,
            stdout=json.dumps({"data": {"node": {"fieldValues": {"nodes": []}}}}),
            stderr="")

    monkeypatch.setattr(bf, "gh_run", fake_gh_run)
    bf._read_fresh_state(change, {})
    issued = [a for call in seen for a in call]
    assert f"query={shared}" in issued, \
        "the --apply field read must issue the shared query constant, not a copy"


# ============================================================================
# R1: the field-value fresh read fails CLOSED on every non-confirming GraphQL
# response. GitHub GraphQL routinely returns exit 0 with `errors` populated and
# `data`/`node`/`fieldValues` null on rate-limits / transient errors — none of
# those is a confirmed read, so each must yield read_ok=False (→ DRIFTED skip in
# classify_change), NEVER a confirmed-unset (which would would-write and overwrite
# a value never actually read), and NEVER an uncaught crash mid-corpus. These
# trace the REAL `_read_current_field_value`, not an injected FreshState.
# ============================================================================


def _field_change_obj(apply_mod, *, observed="OPT_PLAN"):
    """A set-board-field PlannedChange wired for the fresh read + classify trace."""
    return apply_mod.PlannedChange(
        issue_number=7, kind="set-board-field", target="OPT_SPYRE", observed=observed,
        argv=["gh", "project", "item-edit", "--id", "ITEM_1"],
        item_id="ITEM_1", field_id="FIELD_WS",
    )


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param({"data": {"node": None}}, id="node-null"),
        pytest.param({"data": {"node": {"fieldValues": None}}}, id="fieldValues-null"),
        pytest.param({"data": None}, id="data-null"),
        pytest.param({"data": {}}, id="node-absent"),
        pytest.param(
            {"data": None, "errors": [{"message": "API rate limit exceeded"}]},
            id="errors-bearing-exit-0",
        ),
        pytest.param(
            {"data": {"node": {"fieldValues": {"nodes": None}}}}, id="nodes-null",
        ),
    ],
)
def test_field_read_fails_closed_on_non_confirming_graphql(
    bf, monkeypatch, apply_mod, payload
) -> None:
    """Every non-confirming GraphQL shape (null at any hop, or an errors-bearing
    exit-0) yields read_ok=False — a fail-closed read, never a confirmed unset and
    never a crash. This is the disconfirming-instance class the original suite
    missed: each of these previously either crashed (`None.get()`) or returned a
    false confirmed-unset that would overwrite an unread value."""
    def fake_gh_run(args, config, **kw):
        return subprocess.CompletedProcess(args, 0, stdout=json.dumps(payload), stderr="")

    monkeypatch.setattr(bf, "gh_run", fake_gh_run)
    change = _field_change_obj(apply_mod)
    fresh = bf._read_fresh_state(change, {})  # the REAL read, not an injected state
    assert fresh.read_ok is False, "a non-confirming GraphQL response must fail closed"
    # And it must classify as DRIFTED (skip), NOT would-write.
    assert apply_mod.classify_change(change, fresh) is apply_mod.Disposition.DRIFTED


def test_field_read_confirmed_unset_only_on_present_empty_node_list(
    bf, monkeypatch, apply_mod
) -> None:
    """The ONLY confirmed-unset is a successful response whose fieldValues.nodes is
    a PRESENT empty list — distinct from a null nodes (which fails closed). This
    pins the boundary the R1 fix turns on: `[]` is a real read of "no value", and
    against an unset target that is a clean would-write."""
    def fake_gh_run(args, config, **kw):
        return subprocess.CompletedProcess(
            args, 0,
            stdout=json.dumps({"data": {"node": {"fieldValues": {"nodes": []}}}}),
            stderr="")

    monkeypatch.setattr(bf, "gh_run", fake_gh_run)
    # observed=None so an unset-confirmed read is no-drift → would-write.
    change = _field_change_obj(apply_mod, observed=None)
    fresh = bf._read_fresh_state(change, {})
    assert fresh.read_ok is True and fresh.current is None
    assert apply_mod.classify_change(change, fresh) is apply_mod.Disposition.WOULD_WRITE


def test_apply_loop_survives_a_throwing_fresh_read(apply_mod) -> None:
    """R1 defensive backstop: a fresh read that RAISES must not crash the whole
    corpus loop — it is audited as a fail-closed skip for that issue and the loop
    continues to the next, applying every write it can."""
    boom = _milestone_planned(apply_mod, 1, target="M1", observed=None)
    ok = _milestone_planned(apply_mod, 2, target="M2", observed=None)

    def read_fresh(change):
        if change.issue_number == 1:
            raise RuntimeError("transient GraphQL transport error")
        return apply_mod.FreshState(current=None, read_ok=True)

    applied: list[int] = []
    import types
    result_ok = types.SimpleNamespace(ok=True, detail="done", error="")
    # Stub the seam so issue 2's write "succeeds" without touching gh.
    orig = apply_mod.substrate_writes.write_milestone
    apply_mod.substrate_writes.write_milestone = (
        lambda *a, **k: (applied.append(k.get("issue_number")), result_ok)[1]
    )
    try:
        records = apply_mod.apply_plan([boom, ok], {}, read_fresh=read_fresh)
    finally:
        apply_mod.substrate_writes.write_milestone = orig

    by = {r.issue_number: r for r in records}
    assert by[1].outcome is apply_mod.ApplyOutcome.SKIPPED_DRIFT, \
        "a throwing read is a fail-closed skip, not a crash"
    assert "raised" in by[1].detail
    assert by[2].outcome is apply_mod.ApplyOutcome.APPLIED, \
        "the loop must continue past the bad read and apply the rest"


# ============================================================================
# G3: field-read value-kind (optionId vs text) consistency. The fresh read
# returns optionId-or-text; the single-select case must surface the optionId
# (matching a target that is an option id). Text-field back-fill compares text.
# ============================================================================


def test_field_read_value_kind_matches_single_select_target(
    bf, monkeypatch, apply_mod
) -> None:
    """Single-select: the fresh read returns the optionId (the value-kind the
    single-select target compares against), idempotency holds when it equals the
    target."""
    def fake_gh_run(args, config, **kw):
        return subprocess.CompletedProcess(
            args, 0,
            stdout=json.dumps({"data": {"node": {"fieldValues": {"nodes": [
                {"optionId": "OPT_SPYRE", "field": {"id": "FIELD_WS"}},
            ]}}}}),
            stderr="")

    monkeypatch.setattr(bf, "gh_run", fake_gh_run)
    change = apply_mod.PlannedChange(
        issue_number=1, kind="set-board-field", target="OPT_SPYRE", observed="OPT_SPYRE",
        argv=["x"], item_id="ITEM_1", field_id="FIELD_WS",
    )
    fresh = bf._read_fresh_state(change, {})
    assert fresh.current == "OPT_SPYRE"  # an option id, not text
    assert apply_mod.classify_change(change, fresh) is apply_mod.Disposition.ALREADY_SATISFIED


def test_field_read_value_kind_matches_text_target(bf, monkeypatch, apply_mod) -> None:
    """Text field: the fresh read returns the text value (text-field back-fill
    compares text), so a text target compares against text."""
    def fake_gh_run(args, config, **kw):
        return subprocess.CompletedProcess(
            args, 0,
            stdout=json.dumps({"data": {"node": {"fieldValues": {"nodes": [
                {"text": "Spyre", "field": {"id": "FIELD_TXT"}},
            ]}}}}),
            stderr="")

    monkeypatch.setattr(bf, "gh_run", fake_gh_run)
    change = apply_mod.PlannedChange(
        issue_number=1, kind="set-board-field", target="Spyre", observed="Spyre",
        argv=["x"], item_id="ITEM_1", field_id="FIELD_TXT", text_value="Spyre",
    )
    fresh = bf._read_fresh_state(change, {})
    assert fresh.current == "Spyre"
    assert apply_mod.classify_change(change, fresh) is apply_mod.Disposition.ALREADY_SATISFIED


# ============================================================================
# R2: the emit-script field write carries a GUARD symmetric with the milestone
# guard — it re-reads the board field and writes only on the clean no-drift case,
# never blind-overwriting a concurrent edit. The header must not claim re-check
# idempotency it does not deliver on the field substrate.
# ============================================================================


def _field_planned(apply_mod, number, *, target, observed):
    return apply_mod.PlannedChange(
        issue_number=number, kind="set-board-field", target=target, observed=observed,
        argv=[
            "gh", "project", "item-edit", "--id", f"ITEM_{number}",
            "--field-id", "FIELD_WS", "--project-id", "PROJ_NODE",
            "--single-select-option-id", target,
        ],
        item_id=f"ITEM_{number}", field_id="FIELD_WS", project_id="PROJ_NODE",
        single_select_option_id=target,
    )


def test_emit_script_field_write_is_guarded_not_bare(apply_mod) -> None:
    """The field-value emit line is GUARDED (a GraphQL field re-read + a conditional),
    symmetric with the milestone guard — NOT a bare unguarded item-edit."""
    change = _field_planned(apply_mod, 3, target="OPT_SPYRE", observed=None)
    script = apply_mod.render_emit_script([change])
    # The guard re-reads the field via the SAME GraphQL field-values surface.
    assert "gh api graphql" in script
    assert "fieldValues" in script
    # Three-way conditional: idempotent skip, drift skip, else write.
    assert 'if [ "$current" = ' in script
    assert 'elif [ -n "$current" ]; then' in script
    assert "DRIFT" in script
    # The reviewed item-edit is the else (clean) branch, not an unconditional line.
    idx_else = script.index("else")
    idx_edit = script.index("gh project item-edit")
    assert idx_edit > idx_else, "the item-edit must sit in the no-drift else branch"


def test_emit_script_field_guard_skips_a_concurrent_drift(apply_mod, tmp_path) -> None:
    """Execute the emitted field fragment against a simulated CONCURRENT DRIFT and
    assert it does NOT run the item-edit — the guard echoes a drift skip instead.

    A fake `gh` on PATH returns the field's current value as some OTHER option id
    (a concurrent human edit). The guard must take the drift branch (no item-edit),
    proving the emitted script is drift-safe — the property the old bare line lacked.
    """
    import os
    import stat
    import subprocess as sp

    change = _field_planned(apply_mod, 9, target="OPT_TARGET", observed=None)
    fragment = apply_mod._emit_one(change)

    # A fake `gh`: for `api graphql` (the re-read) print a drifted other-value via
    # the --jq path; for `project item-edit` (the write) record that it ran.
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    edit_marker = tmp_path / "item-edit-ran"
    fake_gh = bin_dir / "gh"
    fake_gh.write_text(
        "#!/usr/bin/env bash\n"
        'if [ "$1" = "api" ]; then echo "OPT_HUMAN_DRIFT"; exit 0; fi\n'
        'if [ "$1" = "project" ] && [ "$2" = "item-edit" ]; then\n'
        f'  touch {shlex.quote(str(edit_marker))}\n'
        "  exit 0\n"
        "fi\n"
        "exit 0\n",
        encoding="utf-8",
    )
    fake_gh.chmod(fake_gh.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    env = dict(os.environ, PATH=f"{bin_dir}:{os.environ['PATH']}")
    script = "set -euo pipefail\n" + fragment + "\n"
    result = sp.run(
        ["bash", "-c", script], env=env, capture_output=True, text=True, check=True,
    )
    assert not edit_marker.exists(), \
        "the guard must NOT run item-edit when the field drifted to another value"
    assert "DRIFT" in result.stderr


def test_emit_script_field_guard_writes_on_clean_unset(apply_mod, tmp_path) -> None:
    """The complement: when the field re-reads as UNSET (no drift), the guard DOES
    run the reviewed item-edit — the guard skips drift without mis-skipping a real
    write."""
    import os
    import stat
    import subprocess as sp

    change = _field_planned(apply_mod, 9, target="OPT_TARGET", observed=None)
    fragment = apply_mod._emit_one(change)

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    edit_marker = tmp_path / "item-edit-ran"
    fake_gh = bin_dir / "gh"
    fake_gh.write_text(
        "#!/usr/bin/env bash\n"
        'if [ "$1" = "api" ]; then echo ""; exit 0; fi\n'   # field is unset
        'if [ "$1" = "project" ] && [ "$2" = "item-edit" ]; then\n'
        f'  touch {shlex.quote(str(edit_marker))}\n'
        "  exit 0\n"
        "fi\n"
        "exit 0\n",
        encoding="utf-8",
    )
    fake_gh.chmod(fake_gh.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    env = dict(os.environ, PATH=f"{bin_dir}:{os.environ['PATH']}")
    script = "set -euo pipefail\n" + fragment + "\n"
    sp.run(["bash", "-c", script], env=env, capture_output=True, text=True, check=True)
    assert edit_marker.exists(), "an unset field (no drift) must run the reviewed write"


def _extract_emit_jq(apply_mod, change) -> str:
    """Pull the exact --jq program out of the emitted field fragment, so the jq
    test exercises the REAL expression the script ships (not a copy that can drift)."""
    fragment = apply_mod._emit_one(change)
    # The fragment embeds `--jq <quoted-program>`; recover it via shell tokenisation.
    reread_line = next(
        line for line in fragment.split("\n") if line.startswith("current=$(")
    )
    tokens = shlex.split(reread_line)
    return tokens[tokens.index("--jq") + 1]


@pytest.mark.parametrize(
    "payload,expected",
    [
        pytest.param(
            {"data": {"node": {"fieldValues": {"nodes": [
                {"optionId": "OPT_TARGET", "field": {"id": "FIELD_WS"}}]}}}},
            "OPT_TARGET", id="single-select-match",
        ),
        pytest.param(
            {"data": {"node": {"fieldValues": {"nodes": [
                {"text": "Some Text", "field": {"id": "FIELD_WS"}}]}}}},
            "Some Text", id="text-match",
        ),
        pytest.param(
            {"data": {"node": {"fieldValues": {"nodes": []}}}}, "", id="empty-unset",
        ),
        pytest.param({"data": {"node": None}}, "", id="node-null-degrades-to-empty"),
        pytest.param(
            {"data": {"node": {"fieldValues": None}}}, "",
            id="fieldValues-null-degrades-to-empty",
        ),
    ],
)
def test_emit_field_jq_program_is_valid_over_graphql_shapes(
    apply_mod, payload, expected
) -> None:
    """The embedded --jq program is valid jq over every GraphQL shape: it extracts
    the matching field's optionId/text, and degrades a transient null node to empty
    (treated as unset) WITHOUT a jq error that would abort the script."""
    import subprocess as sp

    change = _field_planned(apply_mod, 9, target="OPT_TARGET", observed=None)
    jq_program = _extract_emit_jq(apply_mod, change)
    result = sp.run(
        ["jq", "-r", jq_program],
        input=json.dumps(payload), capture_output=True, text=True, check=True,
    )
    assert result.stdout.strip() == expected


def test_emit_header_does_not_falsely_claim_field_recheck(apply_mod) -> None:
    """The emit header must be substrate-accurate: it must NOT lean on the old
    'item-edit of an identical value is a server-side no-op' hand-wave that ignored
    concurrent drift; it must describe BOTH substrates as guarded by a re-read."""
    change = _field_planned(apply_mod, 1, target="OPT_SPYRE", observed=None)
    script = apply_mod.render_emit_script([change])
    # The old weak claim is gone.
    assert "server-side\nno-op" not in script
    assert "server-side no-op" not in script
    # The header now describes a field re-read guard.
    assert "board-field write re-reads" in script or "board-field write re-reads" in script.replace("\n", " ")


def test_emit_script_is_honest_about_fail_open_on_failed_reread(apply_mod) -> None:
    """Honesty-in-the-emitted-artifact: the emit-script guards FAIL OPEN — a re-read
    that FAILS reads empty and the write RUNS (it can't see a concurrent edit it
    failed to read). The emitted text must say so, and must point at
    `pm back-fill --apply` as the drift-safe (fail-closed) path. Without this line
    the header only advertised the protected (successful-read) case."""
    change = _field_planned(apply_mod, 1, target="OPT_TARGET", observed=None)
    script = apply_mod.render_emit_script([change])
    flat = script.replace("\n", " ")
    # The header states the fail-open posture and names the failed re-read.
    assert "FAILS OPEN" in flat
    assert "fail" in flat.lower() and "re-read" in flat.lower()
    assert "the write RUNS" in flat
    # It points at --apply as the drift-safe path that fails closed.
    assert "fails CLOSED" in flat
    assert "pm back-fill --apply" in flat
    # The per-change field guard also carries the honest fail-open note inline.
    assert "guard fails OPEN" in flat


# ============================================================================
# G1: the saved-plan (--plan) apply path re-runs the LIVE residual gate before
# applying — it must NOT trust a stale recorded "passed: true" when the live gate
# (auth / repo / board) now fails.
# ============================================================================


def test_main_apply_saved_plan_refuses_when_live_gate_now_fails(
    bf, tmp_path, monkeypatch, capsys
) -> None:
    """A saved plan recorded `passed: true`, but the LIVE gate now fails (e.g. auth
    invalid / board deleted since plan-save). The apply must REFUSE (exit 2) and
    issue no write — the recorded verdict is stale for the auth/repo/board members."""
    plan = _plan(
        intents=[MILESTONE_INTENT],
        proposed=[_milestone_change(1, observed=None)],
    )  # recorded gate passes
    plan_file = _write_plan_file(tmp_path, plan)

    def fake_gh_run(args, config=None, **kw):
        if args[:3] == ["gh", "issue", "edit"] and "--milestone" in args:
            pytest.fail("no write may run when the live gate refuses")
        return subprocess.CompletedProcess(args, 0, stdout="{}", stderr="")

    _patch_all_gh(bf, monkeypatch, fake_gh_run)
    monkeypatch.setattr(bf, "load_adopter_config", lambda _r: {})
    # The LIVE gate now FAILS (auth flipped invalid after plan-save).
    monkeypatch.setattr(
        bf, "_residual_gate_for_saved_plan",
        lambda _plan, _config, _root: bf.GateResult(
            passed=False,
            checks=[("gh auth", "fail", "token expired since plan-save")],
        ),
    )
    monkeypatch.setattr(
        sys, "argv",
        ["back-fill.py", "--capability-root", str(tmp_path), "--apply",
         "--plan", str(plan_file), "--yes"],
    )
    rc = bf.main()
    assert rc == 2, "a now-failing live gate must refuse the saved-plan apply"
    assert "REFUSED" in capsys.readouterr().err


def test_saved_plan_live_gate_rechecks_board_for_field_intent(
    bf, tmp_path, monkeypatch
) -> None:
    """The live re-gate keys the board-resolvability member off the SAVED plan's
    declared intents: a plan declaring a set-board-field intent re-checks the board
    against the live repo, so a board deleted since plan-save fails the gate."""
    field_plan = _plan(intents=[FIELD_INTENT], proposed=[])
    # Residual subset passes, but the live board no longer resolves.
    monkeypatch.setattr(bf, "_residual_pre_check",
                        lambda _root: bf.GateResult(passed=True, checks=[]))
    monkeypatch.setattr(bf, "_resolve_project_node_id", lambda _config: None)
    gate = bf._residual_gate_for_saved_plan(field_plan, {}, tmp_path)
    assert gate.passed is False, "a declared field intent with no live board must fail"
    assert any(status == "fail" for _, status, _ in gate.checks)


def test_saved_plan_live_gate_skips_board_check_without_field_intent(
    bf, tmp_path, monkeypatch
) -> None:
    """A plan declaring only a milestone intent does not re-check board
    resolvability — the board member is conjoined on a declared field intent."""
    ms_plan = _plan(intents=[MILESTONE_INTENT], proposed=[])
    monkeypatch.setattr(bf, "_residual_pre_check",
                        lambda _root: bf.GateResult(passed=True, checks=[]))
    monkeypatch.setattr(
        bf, "_resolve_project_node_id",
        lambda _config: pytest.fail("board must not be probed without a field intent"),
    )
    gate = bf._residual_gate_for_saved_plan(ms_plan, {}, tmp_path)
    assert gate.passed is True
