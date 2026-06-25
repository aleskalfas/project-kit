"""Write-side substrate-map rewire — create-issue + move-issue (ADR-026, Task #265).

Where `test_pm_substrate_map_seam` pins the SEAM's resolution layer in isolation,
this file pins two of the WRITE-APPLY consumers Task #265 routes through it.

NOTE on the write-apply surface (corrected, #265): create-issue + move-issue are
NOT the only state-write-apply sites. There are at least three —
**close-issue** is now rewired through the same seam too (its
`reconcile_state_labels_to_done` resolves the `state`/`done` write through
`resolve_write`, skipping the kit `state:*` add on a derive/unsupported map; see
`test_pm_close_issue.py`) — PLUS the workstream-label mutator CLASS
(add/remove/merge/rename/split-workstream), which is gated by
`axis_labels.workstream_mutator_refusal` to refuse before any `gh label` op when
the workstream axis is unsupported (see `test_pm_workstream_mutator_gate.py`).
This file covers the create-issue / move-issue pair:

  * `create-issue._build_labels` — the applied-label list is constructed by
    `resolve_write` per axis. Under a present map it emits the adopter's MAPPED
    substrate labels and NEVER the kit's `type:`/`priority:`/`workstream:` labels;
    an unsupported axis is omitted (advisory), not kit-written. A per-axis
    `default:` seeds an axis the caller left blank. The resolved-by-axis map it
    returns is the single source the pre-flight display reads (G-2).
  * `move-issue._compute_plan` — the `state` write routes through
    `resolve_write("state", target, map)`. A derive-bound (or unsupported) state
    writes NO kit `state:*` label (the open/closed substrate carries state),
    while the wrapper's domain side-effects still fire (the empty plan returns 0).

Two tests are MUTATION-PROOFS (analogous to the seam guard's reintroduce-and-catch
proofs): they assert the fail-closed property AND demonstrate, via a deliberately
wrong coercion in the test body, that the assertion catches a kit label leaking
onto a brownfield issue.

The fixture map is the AUJ shape from #258 (mirrors `test_pm_substrate_map_seam`):
  * priority → P0/P1/P2 label remap, default P1;
  * type → `[Task]`/`[Epic]` title-prefix, NO `[Feature]`/`[Umbrella]`;
  * workstream → unsupported;
  * state → a derive predicate (open/closed + blocked).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from _lib import axis_labels  # noqa: E402


# The AUJ-shaped fixture map (#258), built in-process so the test does not depend
# on any example file's exact contents.
AUJ_MAP = axis_labels.SubstrateMap(
    axes={
        "priority": {
            "label": {"remap": {"High": "P0", "Medium": "P1", "Low": "P2"}},
            "default": "P1",
        },
        "type": {"title-prefix": {"remap": {"task": "[Task]", "epic": "[Epic]"}}},
        "workstream": {"unsupported": True},
        "state": {
            "derive": {
                "from": "open-closed",
                "states": {"open": "open & not Blocked", "done": "closed"},
            }
        },
    }
)


def _load(name: str, filename: str):
    """Import a pm script as a module for direct call into its pure helpers."""
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def ci():
    return _load("pm_create_issue_rewire", "create-issue.py")


@pytest.fixture(scope="module")
def mi():
    return _load("pm_move_issue_rewire", "move-issue.py")


# --- create-issue: mapped labels under a present map ----------------------


def test_create_issue_emits_mapped_priority_label_not_kit_label(ci) -> None:
    """`--priority High` under the AUJ map emits the adopter's `P0`, never the
    kit's `priority:High`."""
    labels, advisories, _ = ci._build_labels(
        kind="task",
        priority="High",
        workstream="cli",
        has_board=False,
        substrate_map=AUJ_MAP,
    )
    assert "P0" in labels
    assert "priority:High" not in labels
    # And no kit `priority:` / `type:` / `workstream:` label leaks in.
    assert not any(lbl.startswith(("priority:", "type:", "workstream:")) for lbl in labels)


def test_create_issue_emits_mapped_type_prefix_label(ci) -> None:
    """`--kind task` (the classification `type` axis) resolves to `[Task]`,
    the adopter's title-prefix substrate, never `type:task`."""
    labels, _, resolved = ci._build_labels(
        kind="task",
        priority="High",
        workstream=None,
        has_board=True,  # board ⇒ only the type axis is labelled
        substrate_map=AUJ_MAP,
    )
    assert labels == ["[Task]"]
    # G-2: the resolved-by-axis map carries the same value the pre-flight
    # display reads, so display and applied label cannot diverge.
    assert resolved["type"] == "[Task]"


def test_create_issue_omits_unsupported_workstream_with_advisory(ci) -> None:
    """workstream is `unsupported` under the AUJ map ⇒ omitted from labels
    (no kit `workstream:cli`) and surfaced as an advisory."""
    labels, advisories, resolved = ci._build_labels(
        kind="task",
        priority="High",
        workstream="cli",
        has_board=False,
        substrate_map=AUJ_MAP,
    )
    assert "workstream:cli" not in labels
    assert not any(lbl.startswith("workstream:") for lbl in labels)
    assert any("workstream" in a for a in advisories), advisories
    # The degraded axis is absent from the resolved-by-axis map.
    assert "workstream" not in resolved


def test_create_issue_omits_value_unresolvable_type_with_advisory(ci) -> None:
    """`--kind feature` has no `[Feature]` prefix in the AUJ map (the fourth arm,
    value-unresolvable) ⇒ omitted, advisory; never `type:feature`."""
    labels, advisories, resolved = ci._build_labels(
        kind="feature",
        priority="High",
        workstream=None,
        has_board=True,
        substrate_map=AUJ_MAP,
    )
    assert labels == []
    assert "type:feature" not in labels
    assert any("type" in a for a in advisories), advisories
    # value-unresolvable type ⇒ absent from resolved-by-axis ⇒ display shows
    # "(not labelled …)" (G-2: no independent re-resolution to diverge).
    assert "type" not in resolved


def test_create_issue_applies_axis_default_when_value_blank(ci) -> None:
    """An adopter `default:` seeds an axis the caller left blank.

    Workstream is unsupported in the AUJ map, so to exercise the default path we
    use a map where workstream is `label`-bound with a declared default.
    """
    map_with_ws_default = axis_labels.SubstrateMap(
        axes={
            "workstream": {
                "label": {"remap": {"cli": "area/cli", "core": "area/core"}},
                "default": "core",
            },
        }
    )
    # Caller passes no workstream ⇒ the default `core` resolves to `area/core`.
    labels, _, _ = ci._build_labels(
        kind="task",
        priority="High",
        workstream=None,
        has_board=False,
        substrate_map=map_with_ws_default,
    )
    assert "area/core" in labels


def test_create_issue_filer_value_overrides_axis_default(ci) -> None:
    """The per-axis `default:` fills ONLY when the filer supplies none (DEC-037 §3
    filer-override). A filer-supplied workstream wins over the declared default."""
    map_with_ws_default = axis_labels.SubstrateMap(
        axes={
            "workstream": {
                "label": {"remap": {"cli": "area/cli", "core": "area/core"}},
                "default": "core",
            },
        }
    )
    # Caller passes `cli` ⇒ the filer value resolves; the default `core` does NOT.
    labels, _, _ = ci._build_labels(
        kind="task",
        priority="High",
        workstream="cli",
        has_board=False,
        substrate_map=map_with_ws_default,
    )
    assert "area/cli" in labels
    assert "area/core" not in labels


def test_create_issue_greenfield_parity_byte_identical(ci) -> None:
    """No map ⇒ the exact same label list as the pre-rewire output: the kit's own
    `type:<kind>` (+ `priority:*` / `workstream:*` in label-fallback mode)."""
    # Label-fallback mode (no board): type + priority + workstream.
    labels, advisories, resolved = ci._build_labels(
        kind="bug",
        priority="High",
        workstream="cli",
        has_board=False,
        substrate_map=None,
    )
    assert labels == ["type:bug", "priority:High", "workstream:cli"]
    assert advisories == []
    # Greenfield: the resolved-by-axis map carries the kit's own labels.
    assert resolved == {
        "type": "type:bug",
        "priority": "priority:High",
        "workstream": "workstream:cli",
    }

    # Board mode: only the type axis is labelled.
    board_labels, _, board_resolved = ci._build_labels(
        kind="feature",
        priority="Medium",
        workstream=None,
        has_board=True,
        substrate_map=None,
    )
    assert board_labels == ["type:feature"]
    assert board_resolved == {"type": "type:feature"}


# --- move-issue: derive-bound state writes no kit state label -------------


def test_move_issue_derive_bound_state_writes_no_state_label(mi) -> None:
    """A transition to a derive-bound state (AUJ map) produces an EMPTY plan —
    no kit `state:*` add and no removal — because the open/closed substrate
    carries state (ADR-026 §5). The domain side-effects still fire (the empty
    plan is applied as a no-op, returning success)."""
    plan = mi._compute_plan(
        issue_number=42,
        current_state="in-progress",
        target_state="done",
        has_board=False,
        labels=["priority:High"],  # a stale kit state label would be here in greenfield
        substrate_map=AUJ_MAP,
    )
    assert plan.add_label is None
    assert plan.remove_label is None


def test_move_issue_derive_bound_state_does_not_strip_a_prior_label(mi) -> None:
    """Even if a stray `state:*` label is present on the issue, a derive-bound
    map touches NO state label — neither adds the new one nor removes the old.
    The seam owns the encoding; under a present derive map the kit manages no
    state labels at all.

    SCOPE (G-1, #265): this is the WRITE side only — the *plan* is empty, so the
    mutator writes/removes no kit `state:*` label. It does NOT assert that a
    leftover `state:*` label is harmless on the READ side: `infer_current_state`
    is not yet derive-aware, so a stray label still shadows the open/closed read
    (a known wedge). Making the empty plan ALSO strip the stray label was
    rejected — stripping is itself a kit `state:*` write, the very thing the
    derive binding forbids. The proper fix is the derive READ detector
    (#263/lifecycle); see `lifecycle_inference.infer_current_state`'s SIBLING GAP
    note. So this test must NOT be read as "derive-bound move is wedge-free" — it
    only pins that the move writes no unmanaged label."""
    plan = mi._compute_plan(
        issue_number=42,
        current_state="in-progress",
        target_state="done",
        has_board=False,
        labels=["state:in-progress"],
        substrate_map=AUJ_MAP,
    )
    assert plan.add_label is None
    assert plan.remove_label is None


def test_move_issue_greenfield_parity_byte_identical(mi) -> None:
    """No map ⇒ the exact pre-rewire plan: add `state:<target>`, remove a stale
    `state:*` label (the Task-A/B greenfield bar)."""
    plan = mi._compute_plan(
        issue_number=42,
        current_state="todo",
        target_state="backlog",
        has_board=False,
        labels=["state:todo", "type:feature"],
        substrate_map=None,
    )
    assert plan.add_label == "state:backlog"
    assert plan.remove_label == "state:todo"


def test_move_issue_greenfield_default_arg_is_none_map(mi) -> None:
    """The substrate_map parameter defaults to None (greenfield) so every existing
    call site that does not pass it keeps the kit's own `state:*` behaviour."""
    plan = mi._compute_plan(
        issue_number=7,
        current_state="todo",
        target_state="backlog",
        has_board=False,
        labels=[],
    )
    assert plan.add_label == "state:backlog"


# --- MUTATION-PROOF: fail-closed at the call site -------------------------
# These demonstrate the safety property would catch a kit label leaking onto a
# brownfield issue — the call-site analogue of the seam guard's proofs.


def test_mutation_create_issue_coerced_degrade_leaks_kit_label_is_caught(ci) -> None:
    """If `_build_labels` WRONGLY coerced a DEGRADE to the kit's own label on the
    unsupported workstream axis, a kit `workstream:cli` would leak onto a
    brownfield issue. We model the bug in the test body and confirm the
    fail-closed assertion the real tests rely on catches it; then confirm the
    real `_build_labels` does NOT leak it."""

    def _buggy_build_labels(kind, priority, workstream, substrate_map):
        """DELIBERATELY WRONG: coerces DEGRADE back to the kit's own label."""
        out: list[str] = []
        for axis, value in (("type", kind), ("priority", priority), ("workstream", workstream)):
            resolved = axis_labels.resolve_write(axis, value, substrate_map)
            if isinstance(resolved, str):
                out.append(resolved)
            else:
                out.append(axis_labels.label(axis, value))  # BUG: coerce DEGRADE → kit label
        return out

    buggy = _buggy_build_labels("task", "High", "cli", AUJ_MAP)
    # The bug is present: the kit's `workstream:cli` leaked onto the label list.
    assert "workstream:cli" in buggy

    def assert_no_kit_label_leak(labels):
        for lbl in labels:
            assert not lbl.startswith(("type:", "priority:", "workstream:", "state:")), lbl

    with pytest.raises(AssertionError):
        assert_no_kit_label_leak(buggy)

    # The real builder fails closed: the unsupported axis is omitted, not coerced.
    real_labels, _, _ = ci._build_labels(
        kind="task",
        priority="High",
        workstream="cli",
        has_board=False,
        substrate_map=AUJ_MAP,
    )
    assert_no_kit_label_leak(real_labels)
    assert "workstream:cli" not in real_labels


def test_mutation_move_issue_coerced_degrade_leaks_state_label_is_caught(mi) -> None:
    """If `_compute_plan` WRONGLY coerced a derive-bound state DEGRADE to the
    kit's own `state:*` label, a kit state label would be written onto a
    brownfield issue. Model the bug; confirm the assertion catches it; confirm
    the real `_compute_plan` does NOT add a state label."""
    buggy_add = axis_labels.label("state", "done")  # the fail-open coercion
    assert buggy_add == "state:done"

    def assert_no_kit_state_write(add_label):
        if add_label is None:
            return
        assert not add_label.startswith("state:"), add_label

    with pytest.raises(AssertionError):
        assert_no_kit_state_write(buggy_add)

    real_plan = mi._compute_plan(
        issue_number=42,
        current_state="in-progress",
        target_state="done",
        has_board=False,
        labels=[],
        substrate_map=AUJ_MAP,
    )
    assert_no_kit_state_write(real_plan.add_label)
    assert real_plan.add_label is None
