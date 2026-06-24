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

     Where the safety actually comes from TODAY, stated honestly: there is no
     `*_severity` knob on the invariants to flip, AND no consumer yet reads the
     seam's fourth-arm (value-unresolvable) signal to soften a rule — severity-
     knob handling is deferred to the DEC-036 severity-knob work. So a degrade
     signal CANNOT soften these rules because nothing wires it to them. The
     load-bearing test is `test_containment_invariants_carry_no_severity_knob`:
     it pins the structural premise (no knob exists). The companion
     `test_mutation_no_knob_stays_hard_proof` is NOT a guard over shipped code —
     there is no production `effective_severity` function for it to catch a
     regression in; it models the right-vs-wrong fail-safe rule abstractly to
     document why "no-knob ⇒ advisory" would be wrong. Do not read it as a
     structural catch on shipped behaviour.
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


def test_mutation_no_knob_stays_hard_proof() -> None:
    """DOCUMENTATION (not a guard over shipped code): why "no-knob ⇒ advisory"
    would be the wrong fail-safe.

    HONEST SCOPE: there is no production `effective_severity` function — the two
    `effective_severity_*` definitions below live INSIDE this test and model the
    rule abstractly. This test therefore does NOT catch a softening of shipped
    code; nothing reads the seam's fourth-arm (value-unresolvable) signal to
    pick a severity yet (deferred to the DEC-036 severity-knob work). It exists
    to spell out the rule a future severity-knob consumer must implement: a
    degraded rule with no knob stays HARD. The real, load-bearing pin is
    `test_containment_invariants_carry_no_severity_knob` (no knob exists to
    flip); this is its rationale, written executably.

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
