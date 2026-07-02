"""Schema-shape tests for the COR-040 open-region slot.

Validates `process` definition fragments against the shape contract
(`_defs/process.schema.json#/$defs/process`), covering the two additive fields
the slot adds — both keeping the additive guarantee (a definition declaring
neither validates byte-unchanged, exercised by the invariants schema test's
base-definition case):

- an invariant's optional `applies_to` scope (a state id, accepted; bad pattern
  rejected),
- a state's optional `open_region: true` marker (accepted; non-boolean
  rejected).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

_SCHEMA_PATH = (
    Path(__file__).resolve().parents[1] / ".pkit" / "schemas" / "_defs" / "process.schema.json"
)


def _process_validator() -> Draft202012Validator:
    full = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    defs = full["$defs"]
    schema = dict(defs["process"])
    schema["$defs"] = defs
    return Draft202012Validator(schema)


def _errors(definition: dict[str, Any]) -> list[str]:
    return [e.message for e in _process_validator().iter_errors(definition)]


def _base_definition() -> dict[str, Any]:
    """A minimal valid singleton process with one open-region state + one exit."""
    return {
        "id": "demo",
        "version": 1,
        "subject": {"cardinality": "singleton"},
        "states": [
            {
                "id": "build",
                "meaning": "Build (open region).",
                "detection": {"mode": "inferred", "predicate": {"run": "detect-build"}},
            },
            {
                "id": "ready",
                "meaning": "Ready.",
                "terminal": True,
                "detection": {"mode": "inferred", "predicate": {"run": "detect-ready"}},
            },
        ],
        "transitions": [
            {
                "from": "build",
                "to": "ready",
                "trigger": "leave",
                "authorisation": "agent-autonomous",
                "gate": {"kind": "deterministic", "predicate": {"run": "exit-ready"}},
            }
        ],
    }


# --- applies_to (invariant scope) -----------------------------------------


def test_invariant_applies_to_accepted() -> None:
    definition = _base_definition()
    definition["invariants"] = [
        {
            "id": "evidence-backed",
            "check": {"run": "check-evidence"},
            "why": "Every factual claim resolves to an evidence record.",
            "applies_to": "build",
        }
    ]
    assert _errors(definition) == []


def test_invariant_without_applies_to_still_accepted() -> None:
    # Additive: an unscoped invariant (COR-035) is unchanged.
    definition = _base_definition()
    definition["invariants"] = [
        {"id": "evidence-backed", "check": {"run": "c"}, "why": "w"}
    ]
    assert _errors(definition) == []


def test_invariant_applies_to_bad_pattern_rejected() -> None:
    definition = _base_definition()
    definition["invariants"] = [
        {"id": "x", "check": {"run": "c"}, "why": "w", "applies_to": "Bad State"}
    ]
    assert _errors(definition) != []


# --- open_region (state marker) -------------------------------------------


def test_state_open_region_true_accepted() -> None:
    definition = _base_definition()
    definition["states"][0]["open_region"] = True
    assert _errors(definition) == []


def test_state_open_region_non_boolean_rejected() -> None:
    definition = _base_definition()
    definition["states"][0]["open_region"] = "yes"
    assert _errors(definition) != []
