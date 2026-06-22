"""Schema-shape tests for the COR-035 invariants declaration.

Validates a `process` definition fragment against the shape contract
(`_defs/process.schema.json#/$defs/process`), covering:

- the optional `invariants` list on a process (accepted),
- each invariant's required `{id, check, why}`,
- rejection of a malformed invariant (missing `id`, missing `check`, unknown
  sub-field, bad `id` pattern),
- the additive guarantee: a definition carrying NO invariants validates
  byte-unchanged (no `invariants` key needed).
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
    """A validator for the `process` $def, with sibling $defs carried so the
    cross-references (`subject`, `transition`, `invariant`, `predicate`)
    resolve."""
    full = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    defs = full["$defs"]
    schema = dict(defs["process"])
    schema["$defs"] = defs
    return Draft202012Validator(schema)


def _errors(definition: dict[str, Any]) -> list[str]:
    return [e.message for e in _process_validator().iter_errors(definition)]


def _base_definition() -> dict[str, Any]:
    """A minimal valid singleton process, no invariants."""
    return {
        "id": "demo",
        "version": 1,
        "subject": {"cardinality": "singleton"},
        "states": [
            {
                "id": "open",
                "meaning": "Open.",
                "detection": {"mode": "inferred", "predicate": {"run": "detect-open"}},
            }
        ],
        "transitions": [],
    }


def test_base_definition_without_invariants_validates() -> None:
    # Additive guarantee: a definition declaring no invariants is valid as-is.
    assert _errors(_base_definition()) == []


def test_invariants_list_accepted() -> None:
    definition = _base_definition()
    definition["invariants"] = [
        {
            "id": "evidence-backed",
            "check": {"run": "check-evidence"},
            "why": "Every factual claim must resolve to an evidence record.",
        },
        {
            "id": "scope-containment",
            "check": {"run": "check-scope", "with": {"corridor": "declared"}},
            "why": "Discovery stays inside the declared corridor.",
        },
    ]
    assert _errors(definition) == []


def test_invariant_missing_id_rejected() -> None:
    definition = _base_definition()
    definition["invariants"] = [{"check": {"run": "c"}, "why": "no id"}]
    assert _errors(definition) != []


def test_invariant_missing_check_rejected() -> None:
    definition = _base_definition()
    definition["invariants"] = [{"id": "x", "why": "no check"}]
    assert _errors(definition) != []


def test_invariant_missing_why_rejected() -> None:
    definition = _base_definition()
    definition["invariants"] = [{"id": "x", "check": {"run": "c"}}]
    assert _errors(definition) != []


def test_invariant_unknown_subfield_rejected() -> None:
    # additionalProperties false on the invariant object: no `applies-to`,
    # no `severity` (both explicitly deferred per COR-035).
    definition = _base_definition()
    definition["invariants"] = [
        {"id": "x", "check": {"run": "c"}, "why": "w", "applies-to": ["open"]}
    ]
    assert _errors(definition) != []

    definition["invariants"] = [
        {"id": "x", "check": {"run": "c"}, "why": "w", "severity": "hard"}
    ]
    assert _errors(definition) != []


def test_invariant_bad_id_pattern_rejected() -> None:
    definition = _base_definition()
    definition["invariants"] = [{"id": "Bad ID", "check": {"run": "c"}, "why": "w"}]
    assert _errors(definition) != []
