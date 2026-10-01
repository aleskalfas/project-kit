"""Schema-shape tests for the two detection modes (COR-033 point 5, ADR-062).

Validates `process` definition fragments against the shape contract
(`_defs/process.schema.json#/$defs/process`):

- a definition whose states all declare `inferred` validates, as before,
- one whose states all declare `classified` validates,
- one whose states declare both is rejected — the one-mode rule, stated as an
  `anyOf` with one branch per mode,
- a mode the shape does not name is rejected.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

_SCHEMA_PATH = (
    Path(__file__).resolve().parents[1] / ".pkit" / "schemas" / "_defs" / "process.schema.json"
)


def _errors(definition: dict[str, Any]) -> list[str]:
    full = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    schema = dict(full["$defs"]["process"])
    schema["$defs"] = full["$defs"]
    return [e.message for e in Draft202012Validator(schema).iter_errors(definition)]


def _definition(*modes: str) -> dict[str, Any]:
    states = [
        {
            "id": f"s{index}",
            "meaning": f"State {index}.",
            "detection": {"mode": mode, "predicate": {"run": "classify"}},
        }
        for index, mode in enumerate(modes)
    ]
    return {
        "id": "demo",
        "version": 1,
        "subject": {"cardinality": "keyed", "key": "item"},
        "states": states,
        "transitions": [{"from": "s0", "to": "s1", "trigger": "go", "authorisation": "user"}],
    }


@pytest.mark.parametrize("mode", ["inferred", "classified"])
def test_a_definition_in_one_mode_validates(mode: str) -> None:
    assert _errors(_definition(mode, mode, mode)) == []


def test_a_definition_that_mixes_modes_is_rejected() -> None:
    errors = _errors(_definition("classified", "classified", "inferred"))
    assert len(errors) == 1
    assert "is not valid under any of the given schemas" in errors[0]


@pytest.mark.parametrize("mode", ["stored", "hybrid", "Classified"])
def test_a_mode_the_shape_does_not_name_is_rejected(mode: str) -> None:
    errors = _errors(_definition(mode, mode))
    assert any("is not one of ['inferred', 'classified']" in e for e in errors)
