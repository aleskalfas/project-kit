"""substrate-map.yaml schema accept/reject + the no-knob-stays-hard fail-safe.

Two concerns, both pinned by DEC-036 / ADR-026:

  1. **Schema shape** — the companion JSON Schema accepts a well-formed
     substrate-map (one binding per axis, optional `default`) and rejects the
     malformed shapes: two bindings on one axis, no binding, an unknown axis, an
     unknown binding key, `unsupported: false`.

  2. **No-knob-stays-hard fail-safe (ADR-026 §2)** — the `issue-types.yaml`
     containment invariants are authored in prose with NO `*_severity` knob, and
     DEC-036 D4 holds them HARD even in brownfield. The fail-safe rule: a
     degrade-signalled rule with no severity field stays at its authored (hard)
     severity — it does NOT silently become advisory.

     Where containment-stays-hard actually comes from TODAY, stated plainly, is
     structural-by-absence: (i) there is no `*_severity` knob on the invariants
     to flip, AND (ii) there is no consumer that reads any degrade signal (the
     seam's fourth-arm value-unresolvable signal, or the hierarchy mode) and
     wires it to a containment severity — severity-knob handling is deferred to
     the DEC-036 severity-knob work. So a degrade signal CANNOT soften these
     rules because nothing wires it to them. The single load-bearing test is
     `test_containment_invariants_carry_no_severity_knob`: it pins premise (i),
     the structural premise (no knob exists to flip).

     The three companion `_illustration` tests below
     (`test_no_knob_stays_hard_rule_illustration`,
     `test_advisory_must_not_soften_containment_rule_illustration`,
     `test_advisory_softening_containment_would_be_wrong_illustration`) are NOT
     guards over shipped code. There is no production `effective_severity` /
     `containment_effective_severity` function for them to catch a regression in
     — each defines its model LOCALLY in the test body. They exist to document,
     executably, the right-vs-wrong rule a FUTURE severity-knob consumer must
     adopt (no-knob / advisory-hierarchy must keep containment hard). A future
     maintainer must not read them as regression guards on current behaviour; the
     real protection is premises (i) + (ii) above.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from ruamel.yaml import YAML

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMAS = REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "schemas"
SUBSTRATE_MAP_COMPANION = SCHEMAS / "substrate-map.schema.json"
SUBSTRATE_MAP_YAML = SCHEMAS / "substrate-map.yaml"
ISSUE_TYPES_YAML = SCHEMAS / "issue-types.yaml"


@pytest.fixture(scope="module")
def validator() -> Draft202012Validator:
    schema = json.loads(SUBSTRATE_MAP_COMPANION.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def _errors(validator: Draft202012Validator, doc: dict) -> list[str]:
    return [e.message for e in validator.iter_errors(doc)]


def _doc(axes: dict) -> dict:
    return {"schema_version": 1, "axes": axes}


# --- accept ---------------------------------------------------------------


def test_reference_instance_validates(validator: Draft202012Validator) -> None:
    """The shipped reference instance (the AUJ example) validates clean — it is
    the schema's self-test instance."""
    data = YAML(typ="safe").load(SUBSTRATE_MAP_YAML.read_text(encoding="utf-8"))
    assert _errors(validator, data) == []


def test_empty_axes_accepted(validator: Draft202012Validator) -> None:
    """A present-but-empty map (every axis degrades) is well-formed."""
    assert _errors(validator, _doc({})) == []


def test_label_binding_accepted(validator: Draft202012Validator) -> None:
    assert _errors(validator, _doc({"priority": {"label": {"remap": {"High": "P0"}}}})) == []


def test_title_prefix_binding_accepted(validator: Draft202012Validator) -> None:
    assert _errors(validator, _doc({"type": {"title-prefix": {"remap": {"task": "[Task]"}}}})) == []


def test_unsupported_binding_accepted(validator: Draft202012Validator) -> None:
    assert _errors(validator, _doc({"workstream": {"unsupported": True}})) == []


def test_derive_binding_accepted(validator: Draft202012Validator) -> None:
    doc = _doc({"state": {"derive": {"from": "open-closed", "states": {"done": "closed"}}}})
    assert _errors(validator, doc) == []


def test_default_alongside_binding_accepted(validator: Draft202012Validator) -> None:
    doc = _doc({"priority": {"label": {"remap": {"High": "P0"}}, "default": "P1"}})
    assert _errors(validator, doc) == []


# --- reject ---------------------------------------------------------------


def test_two_bindings_on_one_axis_rejected(validator: Draft202012Validator) -> None:
    """Exactly one binding per axis (the `oneOf`): label + unsupported together
    is malformed."""
    doc = _doc({"priority": {"label": {"remap": {"High": "P0"}}, "unsupported": True}})
    assert _errors(validator, doc)


def test_no_binding_rejected(validator: Draft202012Validator) -> None:
    """An axis with only a `default` and no binding is malformed."""
    assert _errors(validator, _doc({"priority": {"default": "P1"}}))


def test_unknown_axis_rejected(validator: Draft202012Validator) -> None:
    assert _errors(validator, _doc({"severity": {"unsupported": True}}))


def test_unknown_binding_key_rejected(validator: Draft202012Validator) -> None:
    assert _errors(validator, _doc({"priority": {"board-field": {"id": "x"}}}))


def test_unsupported_false_rejected(validator: Draft202012Validator) -> None:
    """`unsupported` is `const: true` — `unsupported: false` is meaningless and
    rejected (omit the axis instead)."""
    assert _errors(validator, _doc({"workstream": {"unsupported": False}}))


def test_label_binding_without_remap_rejected(validator: Draft202012Validator) -> None:
    assert _errors(validator, _doc({"priority": {"label": {}}}))


def test_missing_axes_field_rejected(validator: Draft202012Validator) -> None:
    assert _errors(validator, {"schema_version": 1})


def test_wrong_schema_version_rejected(validator: Draft202012Validator) -> None:
    assert _errors(validator, {"schema_version": 2, "axes": {}})


# --- the top-level hierarchy declaration (DEC-036 D4, #272) ---------------


def test_hierarchy_gated_accepted(validator: Draft202012Validator) -> None:
    doc = _doc({})
    doc["hierarchy"] = "gated"
    assert _errors(validator, doc) == []


def test_hierarchy_advisory_accepted(validator: Draft202012Validator) -> None:
    doc = _doc({})
    doc["hierarchy"] = "advisory"
    assert _errors(validator, doc) == []


def test_hierarchy_absent_accepted(validator: Draft202012Validator) -> None:
    """The key is optional — an absent `hierarchy:` is well-formed (and reads as
    `gated` at runtime, the greenfield default)."""
    assert "hierarchy" not in _doc({})
    assert _errors(validator, _doc({})) == []


def test_hierarchy_invalid_value_rejected(validator: Draft202012Validator) -> None:
    """Only `gated` / `advisory` — any other value (e.g. a typo `flat`) is
    rejected at validate time so it cannot silently misread at runtime."""
    doc = _doc({})
    doc["hierarchy"] = "flat"
    assert _errors(validator, doc)


def test_reference_instance_declares_advisory_hierarchy() -> None:
    """The shipped AUJ reference instance is a flat tracker — it declares
    `hierarchy: advisory` (and the schema accepts it, pinned above)."""
    data = YAML(typ="safe").load(SUBSTRATE_MAP_YAML.read_text(encoding="utf-8"))
    assert data.get("hierarchy") == "advisory"


# --- the top-level containment declaration (DEC-039 D2 / ADR-035, #357) ----


def test_containment_native_accepted(validator: Draft202012Validator) -> None:
    doc = _doc({})
    doc["containment"] = "native"
    assert _errors(validator, doc) == []


def test_containment_textual_accepted(validator: Draft202012Validator) -> None:
    doc = _doc({})
    doc["containment"] = "textual"
    assert _errors(validator, doc) == []


def test_containment_absent_accepted(validator: Draft202012Validator) -> None:
    """The key is optional — an absent `containment:` is well-formed (and reads
    as `native` at runtime, the greenfield default)."""
    assert "containment" not in _doc({})
    assert _errors(validator, _doc({})) == []


def test_containment_invalid_value_rejected(validator: Draft202012Validator) -> None:
    """Only `native` / `textual` — any other value (e.g. a typo `none`) is
    rejected at validate time so it cannot silently misread at runtime."""
    doc = _doc({})
    doc["containment"] = "none"
    assert _errors(validator, doc)


def test_reference_instance_declares_textual_containment() -> None:
    """The shipped AUJ reference instance is a no-native-sub-issues tracker — it
    declares `containment: textual` (and the schema accepts it, pinned above)."""
    data = YAML(typ="safe").load(SUBSTRATE_MAP_YAML.read_text(encoding="utf-8"))
    assert data.get("containment") == "textual"


# --- the parent-requiredness severity knob (DEC-036's honest-gap fix) -----


def _issue_types() -> dict:
    return YAML(typ="safe").load(ISSUE_TYPES_YAML.read_text(encoding="utf-8"))


def test_required_parent_types_carry_a_severity_knob() -> None:
    """The parent-REQUIREDNESS rules gain the `*_severity` knob DEC-036 named as
    in-scope schema work — every type that requires a parent
    (`parent_ref_optional: false`) carries `parent_ref_required_severity`, so the
    rule has a field to flip under advisory hierarchy."""
    types = (_issue_types().get("types") or {})
    requiring = {
        name: t for name, t in types.items()
        if not bool(t.get("parent_ref_optional", False))
    }
    assert requiring, "expected at least one type with a required parent-ref"
    for name, t in requiring.items():
        assert t.get("parent_ref_required_severity") == "[validation-severity:hard-reject]", (
            f"type {name!r} must carry an explicit hard-reject "
            f"parent_ref_required_severity (the authored, gated severity)"
        )


def test_severity_knob_is_validation_severity_token() -> None:
    """The knob's value is a typed validation-severity token (COR-019) so the
    schema validator catches a malformed severity at validate time."""
    schema = json.loads(SUBSTRATE_MAP_COMPANION.read_text(encoding="utf-8"))  # noqa: F841
    types = (_issue_types().get("types") or {})
    for name, t in types.items():
        sev = t.get("parent_ref_required_severity")
        if sev is not None:
            assert sev.startswith("[validation-severity:") and sev.endswith("]"), name


# --- no-knob-stays-hard fail-safe (ADR-026 §2) ---------------------------


def _containment_invariants() -> list[dict]:
    data = YAML(typ="safe").load(ISSUE_TYPES_YAML.read_text(encoding="utf-8"))
    return data.get("containment_invariants") or []


def test_containment_invariants_carry_no_severity_knob() -> None:
    """The containment invariants are authored in prose with NO `*_severity`
    field — they are hard by construction (DEC-036 point 3's honest gap). This is
    the structural premise of no-knob-stays-hard: there is no knob to flip, so a
    degrade signal cannot soften them."""
    invariants = _containment_invariants()
    assert invariants, "expected containment_invariants in issue-types.yaml"
    # The Feature-in-Feature invariant is present.
    assert any("Feature does not contain Feature" in (inv.get("rule") or "") for inv in invariants)
    for inv in invariants:
        knobs = [k for k in inv.keys() if k.endswith("severity")]
        assert knobs == [], (
            f"a containment invariant grew a severity knob {knobs} — if a knob is "
            f"added it must be a deliberate DEC-036 schema change, not an "
            f"accident; the no-knob-stays-hard fail-safe assumes none today"
        )


def test_no_knob_stays_hard_rule_illustration() -> None:
    """ILLUSTRATION (not a guard over shipped code): why "no-knob ⇒ advisory"
    would be the wrong fail-safe.

    HONEST SCOPE: there is no production `effective_severity` function — the two
    `effective_severity_*` definitions below live INSIDE this test and model the
    rule abstractly. This test therefore does NOT catch a softening of shipped
    code; nothing reads the seam's fourth-arm (value-unresolvable) signal to
    pick a severity yet (deferred to the DEC-036 severity-knob work). It exists
    to spell out, executably, the rule a future severity-knob consumer must
    implement: a degraded rule with no knob stays HARD. The real, load-bearing
    pin is `test_containment_invariants_carry_no_severity_knob` (no knob exists
    to flip); this is its rationale, not a regression guard.

    The invariant is keyed on `type` and DEC-036 D4 holds it hard even when a
    type VALUE (e.g. `feature`) is value-unresolvable in a brownfield map. When
    a future consumer wires the seam's value-unresolvable signal to severity, it
    must NOT cascade into softening this rule — the `_RIGHT` model below shows
    the behaviour that consumer must adopt.
    """
    invariants = _containment_invariants()
    feature_in_feature = next(
        inv for inv in invariants
        if "Feature does not contain Feature" in (inv.get("rule") or "")
    )

    # The rule has no severity knob today.
    assert not any(k.endswith("severity") for k in feature_in_feature.keys())

    def effective_severity_WRONG(rule: dict, degraded: bool) -> str:
        """The rejected fail-safe: a degraded rule with no knob defaults to
        advisory. This SOFTENS the containment invariant — the bug."""
        knob = next((rule[k] for k in rule if k.endswith("severity")), None)
        if knob is not None:
            return knob
        return "advisory" if degraded else "hard"

    def effective_severity_RIGHT(rule: dict, degraded: bool) -> str:
        """The ADR-026 fail-safe: a degraded rule with NO knob stays at its
        authored (hard) severity. The knob must be added explicitly to soften."""
        knob = next((rule[k] for k in rule if k.endswith("severity")), None)
        if knob is not None:
            return knob
        return "hard"  # no-knob-stays-hard, regardless of degradation

    # Under a brownfield degrade signal on the type axis:
    # the WRONG default softens the containment invariant (the failure we guard).
    assert effective_severity_WRONG(feature_in_feature, degraded=True) == "advisory"
    # the RIGHT default keeps it hard — exactly DEC-036 D4.
    assert effective_severity_RIGHT(feature_in_feature, degraded=True) == "hard"

    # Why the no-knob structural premise matters: because the invariant carries
    # no knob, the ONLY way it could soften is a future consumer adopting the
    # WRONG default. These two assertions document that contrast on the modelled
    # functions — they do not exercise shipped code. The actual protection today
    # is that no such consumer exists and no knob exists to flip
    # (`test_containment_invariants_carry_no_severity_knob` pins the latter).
    with pytest.raises(AssertionError):
        assert effective_severity_WRONG(feature_in_feature, degraded=True) == "hard"
    assert effective_severity_RIGHT(feature_in_feature, degraded=True) == "hard"


# --- containment STAYS HARD under advisory hierarchy (illustrations) ---
# NOTE: neither test below guards shipped code. The real structural pins for
# containment-stays-hard are (i) `test_containment_invariants_carry_no_severity_knob`
# (no knob exists to flip) + (ii) the absence of any consumer that wires the
# hierarchy mode to a containment severity. These two tests model, executably,
# the rule a FUTURE consumer must adopt — their `containment_effective_severity`
# functions are LOCAL to the test body, not production code.


def test_advisory_must_not_soften_containment_rule_illustration() -> None:
    """ILLUSTRATION (not a guard over shipped code): the rule a future consumer
    must adopt — `hierarchy: advisory` relaxes parent-REQUIREDNESS but must keep
    the containment invariants HARD (DEC-036 D4).

    This DOES exercise the real seam signal (`hierarchy_disposition` reads
    `advisory` off a real `SubstrateMap`), but the containment-severity it asserts
    against comes from a LOCAL `containment_effective_severity` modelled in this
    test body — there is no production function that maps a containment invariant
    to a severity under a hierarchy mode. So this is not a regression guard on
    current behaviour; it pins the correct wiring a severity-knob consumer must
    implement. The load-bearing structural pin remains
    `test_containment_invariants_carry_no_severity_knob` (no knob exists to flip).
    """
    import sys

    scripts = REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    from _lib import axis_labels  # noqa: PLC0415

    advisory_map = axis_labels.SubstrateMap(axes={}, hierarchy="advisory")
    assert axis_labels.hierarchy_disposition(advisory_map) == "advisory"

    feature_in_feature = next(
        inv for inv in _containment_invariants()
        if "Feature does not contain Feature" in (inv.get("rule") or "")
    )

    def containment_effective_severity(rule: dict, hierarchy: str) -> str:
        """LOCAL model (not production): the ONLY correct wiring — containment
        carries no knob, so it is HARD in EVERY hierarchy mode. The hierarchy
        argument is accepted to make the independence explicit, and is
        deliberately unused for containment."""
        del hierarchy  # containment is mode-independent (DEC-036 D4)
        knob = next((rule[k] for k in rule if k.endswith("severity")), None)
        return knob if knob is not None else "hard"

    # Hard under advisory AND gated — advisory must not soften it.
    assert containment_effective_severity(feature_in_feature, "advisory") == "hard"
    assert containment_effective_severity(feature_in_feature, "gated") == "hard"


def test_advisory_softening_containment_would_be_wrong_illustration() -> None:
    """ILLUSTRATION (not a guard over shipped code): the wrong wiring — letting
    `hierarchy: advisory` soften the containment invariant to advisory — and the
    assertion that would reject it.

    HONEST SCOPE: the `containment_effective_severity_buggy` below is LOCAL to
    this test; there is no production function it mutates. So this does NOT catch
    a softening of shipped code — it documents, executably, the over-reach
    DEC-036 D4 forbids (advisory relaxes ONLY requiredness, never nesting) so a
    future severity-knob consumer has the wrong-vs-right contrast spelled out.
    The real protection is structural-by-absence (no knob + no consumer), pinned
    by `test_containment_invariants_carry_no_severity_knob`.
    """
    feature_in_feature = next(
        inv for inv in _containment_invariants()
        if "Feature does not contain Feature" in (inv.get("rule") or "")
    )

    def containment_effective_severity_buggy(rule: dict, hierarchy: str) -> str:
        """LOCAL model of the BUG (not production): treats advisory hierarchy as
        softening containment too — the over-reach DEC-036 D4 forbids."""
        knob = next((rule[k] for k in rule if k.endswith("severity")), None)
        if knob is not None:
            return knob
        return "advisory" if hierarchy == "advisory" else "hard"

    # The buggy model softens containment under advisory...
    assert containment_effective_severity_buggy(feature_in_feature, "advisory") == "advisory"
    # ...which a containment-stays-hard assertion would reject:
    with pytest.raises(AssertionError):
        assert containment_effective_severity_buggy(feature_in_feature, "advisory") == "hard"
