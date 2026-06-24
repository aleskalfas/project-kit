"""Brownfield substrate-map resolution through the axis-label seam (ADR-026, Task B).

Where `test_pm_axis_label_seam_parity` pins the GREENFIELD (no-map) identity arm
and `test_pm_axis_label_seam_guard` pins the sole-constructor structural half,
this file pins the grown resolution layer Task B adds: the ADR-026 ternary
(bound / unsupported / absent-treated-as-unsupported), the value-unresolvable
fourth arm, and the fail-closed posture (`resolve_write` never emits the kit's
own label as a write target in a present-map world).

The fixture map is AUJ-shaped per Task B:
  * priority → P0/P1/P2 label remap (bound);
  * type → `[Task]`/`[Epic]` title-prefix WITH NO `[Feature]`/`[Umbrella]` (so
    `feature`/`umbrella` exercise the value-unresolvable fourth arm);
  * workstream → unsupported (no native encoding);
  * state → a derive predicate (open/closed + blocked).

Two of the tests are MUTATION-PROOFS: they assert the safety property AND
demonstrate (via a deliberately wrong resolver in the test body) that the test
would catch the unsafe direction. They are the resolution-layer analogue of the
guard's `test_guard_detects_a_reintroduced_*` proofs.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from _lib import axis_labels  # noqa: E402


# The AUJ-shaped fixture map (parsed view). Mirrors the reference instance in
# schemas/substrate-map.yaml; built in-process so the test does not depend on
# the example file's exact contents.
AUJ_MAP = axis_labels.SubstrateMap(
    axes={
        "priority": {"label": {"remap": {"High": "P0", "Medium": "P1", "Low": "P2"}}, "default": "P1"},
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


# --- the ternary: axis_disposition ----------------------------------------


def test_no_map_every_axis_served() -> None:
    """No substrate-map ⇒ greenfield: every axis is served (identity arm)."""
    for axis in axis_labels.AXES:
        assert axis_labels.axis_disposition(axis, None) == "served"


def test_bound_axes_are_served() -> None:
    assert axis_labels.axis_disposition("priority", AUJ_MAP) == "served"
    assert axis_labels.axis_disposition("type", AUJ_MAP) == "served"
    assert axis_labels.axis_disposition("state", AUJ_MAP) == "served"


def test_unsupported_axis_degrades() -> None:
    assert axis_labels.axis_disposition("workstream", AUJ_MAP) == "unsupported"


def test_absent_axis_is_treated_as_unsupported_not_greenfield() -> None:
    """The load-bearing rule: an axis ABSENT from a present map degrades exactly
    as `unsupported`, NOT as greenfield (ADR-026 §2)."""
    # A map that mentions only priority — type/workstream/state are all absent.
    partial = axis_labels.SubstrateMap(
        axes={"priority": {"label": {"remap": {"High": "P0"}}}}
    )
    assert axis_labels.axis_disposition("priority", partial) == "served"
    for absent in ("type", "workstream", "state"):
        assert axis_labels.axis_disposition(absent, partial) == "unsupported", absent


def test_malformed_binding_fails_closed_to_unsupported() -> None:
    """A binding mapping with none of the four arms is malformed ⇒ degrade."""
    bad = axis_labels.SubstrateMap(axes={"priority": {"default": "P1"}})
    assert axis_labels.axis_disposition("priority", bad) == "unsupported"


# --- bound resolution: resolve_write --------------------------------------


def test_label_binding_resolves_to_adopter_substrate() -> None:
    """A `label`-bound axis resolves to the adopter's OWN label, never the kit's
    `<axis>:<value>` form."""
    assert axis_labels.resolve_write("priority", "High", AUJ_MAP) == "P0"
    assert axis_labels.resolve_write("priority", "Medium", AUJ_MAP) == "P1"
    assert axis_labels.resolve_write("priority", "Low", AUJ_MAP) == "P2"
    # The kit's own `priority:High` is never emitted under a present map.
    assert axis_labels.resolve_write("priority", "High", AUJ_MAP) != "priority:High"


def test_title_prefix_binding_resolves_known_values() -> None:
    assert axis_labels.resolve_write("type", "task", AUJ_MAP) == "[Task]"
    assert axis_labels.resolve_write("type", "epic", AUJ_MAP) == "[Epic]"


def test_no_map_resolve_write_is_greenfield_identity() -> None:
    """No map ⇒ resolve_write returns the kit's own label (greenfield identity);
    byte-identical to `label`."""
    for axis, value in (("priority", "High"), ("type", "feature"), ("state", "done")):
        assert axis_labels.resolve_write(axis, value, None) == axis_labels.label(axis, value)


# --- the fourth arm: value-unresolvable within a BOUND axis ---------------


def test_value_unresolvable_degrades_only_that_value_not_the_axis() -> None:
    """`type` is bound (SERVED) but `feature`/`umbrella` have no `[Feature]` /
    `[Umbrella]` prefix — those values degrade WITHOUT the axis degrading. This
    is the distinction that keeps the type-keyed containment invariant hard."""
    # The axis is served...
    assert axis_labels.axis_disposition("type", AUJ_MAP) == "served"
    # ...the resolvable values resolve...
    assert axis_labels.resolve_write("type", "task", AUJ_MAP) == "[Task]"
    # ...but the missing value degrades (fourth arm), and does so as DEGRADE,
    # never by falling through to the kit's `type:feature`.
    result = axis_labels.resolve_write("type", "feature", AUJ_MAP)
    assert result is axis_labels.DEGRADE
    assert result != "type:feature"
    assert axis_labels.resolve_write("type", "umbrella", AUJ_MAP) is axis_labels.DEGRADE


# --- fail-closed: resolve_write never emits the kit's own write-label ------


def test_unsupported_axis_resolve_write_degrades() -> None:
    assert axis_labels.resolve_write("workstream", "cli", AUJ_MAP) is axis_labels.DEGRADE
    # Never the kit's own `workstream:cli`.
    assert axis_labels.resolve_write("workstream", "cli", AUJ_MAP) != "workstream:cli"


def test_absent_axis_resolve_write_degrades() -> None:
    partial = axis_labels.SubstrateMap(
        axes={"priority": {"label": {"remap": {"High": "P0"}}}}
    )
    assert axis_labels.resolve_write("workstream", "cli", partial) is axis_labels.DEGRADE
    assert axis_labels.resolve_write("type", "task", partial) is axis_labels.DEGRADE


def test_derive_axis_has_no_write_label() -> None:
    """A `derive`-bound axis (lifecycle-state) has no write-label — state is
    written by closing/opening, not labelling. resolve_write degrades."""
    assert axis_labels.resolve_write("state", "done", AUJ_MAP) is axis_labels.DEGRADE
    assert axis_labels.resolve_write("state", "done", AUJ_MAP) != "state:done"


def test_degrade_sentinel_is_not_a_string_and_is_falsy() -> None:
    """DEGRADE cannot be mistaken for a label: not a str, falsy, distinct repr."""
    assert not isinstance(axis_labels.DEGRADE, str)
    assert not axis_labels.DEGRADE
    # Singleton identity holds across constructions.
    assert axis_labels.DEGRADE is axis_labels._Degrade()


def test_present_map_resolve_write_never_emits_a_kit_label_for_any_axis_value() -> None:
    """Exhaustive fail-closed check: across every axis × a grid of methodology
    values, with the AUJ map present, resolve_write NEVER returns a string of the
    kit's `<axis>:<value>` shape. It returns the adopter's substrate or DEGRADE."""
    grid = {
        "type": ["feature", "task", "epic", "bug", "umbrella"],
        "priority": ["High", "Medium", "Low"],
        "workstream": ["cli", "schemas"],
        "state": ["todo", "in-progress", "done"],
    }
    for axis, values in grid.items():
        for value in values:
            result = axis_labels.resolve_write(axis, value, AUJ_MAP)
            if result is axis_labels.DEGRADE:
                continue
            assert isinstance(result, str)
            # The forbidden shape is the kit's own `<axis>:<value>` label.
            assert result != axis_labels.label(axis, value), (
                f"resolve_write fell through to the kit's own label for "
                f"{axis}={value} under a present map — fail-closed violated"
            )
            assert not result.startswith(f"{axis}:"), (
                f"resolve_write emitted a `{axis}:`-prefixed kit label for "
                f"{axis}={value} — fail-closed violated"
            )


# --- defaults --------------------------------------------------------------


def test_axis_default_surfaced_when_declared() -> None:
    assert axis_labels.axis_default("priority", AUJ_MAP) == "P1"


def test_axis_default_none_when_absent_or_greenfield() -> None:
    assert axis_labels.axis_default("type", AUJ_MAP) is None  # no default declared
    assert axis_labels.axis_default("priority", None) is None  # greenfield


# --- MUTATION-PROOF (a): fail-closed -------------------------------------
# Demonstrate that a resolver which WRONGLY falls through to the kit's own label
# on an unsupported axis would be caught by the fail-closed assertion. This is
# the resolution-layer analogue of the guard's reintroduce-and-catch proofs.


def _buggy_resolve_write_open_to_kit_label(axis, value, substrate_map):
    """A DELIBERATELY WRONG resolver: on unsupported/absent, it falls open to the
    kit's own label instead of degrading. The real `resolve_write` must NOT do
    this; this models the bug the fail-closed test must catch."""
    if substrate_map is None:
        return axis_labels.label(axis, value)
    binding = substrate_map.axes.get(axis)
    if binding is None or binding.get("unsupported") is True:
        return axis_labels.label(axis, value)  # BUG: fail-open to kit label
    return axis_labels.resolve_write(axis, value, substrate_map)


def test_mutation_fail_closed_proof() -> None:
    """If resolve_write fell open to the kit's label on an unsupported axis, the
    fail-closed property would be violated. We show the buggy resolver triggers
    the exact assertion the real-resolver tests rely on, then confirm the real
    resolver does NOT."""
    # The bug: workstream (unsupported) resolves to the kit's `workstream:cli`.
    buggy = _buggy_resolve_write_open_to_kit_label("workstream", "cli", AUJ_MAP)
    assert buggy == axis_labels.label("workstream", "cli")  # the bug is present

    # The same assertion the real tests use catches it:
    def assert_fail_closed(result, axis, value):
        if result is axis_labels.DEGRADE:
            return
        assert result != axis_labels.label(axis, value)

    with pytest.raises(AssertionError):
        assert_fail_closed(buggy, "workstream", "cli")

    # The real resolver passes the same assertion (it degrades).
    real = axis_labels.resolve_write("workstream", "cli", AUJ_MAP)
    assert_fail_closed(real, "workstream", "cli")
    assert real is axis_labels.DEGRADE


def test_mutation_fail_closed_proof_for_value_unresolvable() -> None:
    """The fourth-arm sibling: a resolver that fell open to `type:feature` for
    the value-unresolvable `feature` would be caught the same way."""
    buggy = axis_labels.label("type", "feature")  # the fail-open value
    assert buggy == "type:feature"

    def assert_fail_closed(result, axis, value):
        if result is axis_labels.DEGRADE:
            return
        assert result != axis_labels.label(axis, value)

    with pytest.raises(AssertionError):
        assert_fail_closed(buggy, "type", "feature")

    real = axis_labels.resolve_write("type", "feature", AUJ_MAP)
    assert_fail_closed(real, "type", "feature")
    assert real is axis_labels.DEGRADE
