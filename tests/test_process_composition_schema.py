"""Schema-shape tests for the COR-036 composition additions.

Validates a `process` definition fragment against the shape contract
(`_defs/process.schema.json#/$defs/process`), covering:

- the optional `interface` ({inputs, outcomes}) block (accepted),
- a `subprocess` state embedding an inner process by address (accepted),
- a keyed inner's determinate `subject` on the `subprocess` (accepted),
- a `subprocess-outcome` gate (requires `outcome`, forbids `predicate`),
- rejection of a `subprocess-outcome` gate without `outcome`,
- rejection of a predicate-backed gate carrying a stray `outcome`,
- rejection of a malformed `subprocess.runs` address,
- the `awaiting-subprocess-outcome` blocked reason (accepted; forbids
  `resume_when`),
- the additive guarantee: a definition carrying none validates unchanged.
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
    """A minimal valid singleton process — no interface / subprocess."""
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
        "transitions": [
            {"from": "open", "to": "done", "trigger": "go", "authorisation": "user"}
        ],
    }


def test_composition_free_definition_validates() -> None:
    # The additive guarantee: a definition with no composition fields is valid.
    assert _errors(_base_definition()) == []


def test_interface_block_accepted() -> None:
    d = _base_definition()
    d["interface"] = {
        "inputs": [{"name": "point-ref", "meaning": "Which point.", "required": True}],
        "outcomes": [{"name": "verified", "meaning": "Checks out."}],
    }
    assert _errors(d) == []


def test_subprocess_state_accepted() -> None:
    d = _base_definition()
    d["states"][0]["subprocess"] = {"runs": "fixture:verification"}
    assert _errors(d) == []


def test_subprocess_with_keyed_inner_subject_accepted() -> None:
    d = _base_definition()
    d["states"][0]["subprocess"] = {
        "runs": "fixture:point",
        "subject": "p1",
        "inputs": {"point-ref": "p1"},
    }
    assert _errors(d) == []


def test_subprocess_outcome_gate_accepted() -> None:
    d = _base_definition()
    d["states"][0]["subprocess"] = {"runs": "fixture:verification"}
    d["transitions"][0]["authorisation"] = "agent-autonomous"
    d["transitions"][0]["gate"] = {"kind": "subprocess-outcome", "outcome": "verified"}
    assert _errors(d) == []


def test_subprocess_outcome_gate_without_outcome_rejected() -> None:
    d = _base_definition()
    d["transitions"][0]["authorisation"] = "agent-autonomous"
    d["transitions"][0]["gate"] = {"kind": "subprocess-outcome"}
    assert _errors(d), "a subprocess-outcome gate must name an `outcome`"


def test_subprocess_outcome_gate_with_predicate_rejected() -> None:
    d = _base_definition()
    d["transitions"][0]["authorisation"] = "agent-autonomous"
    d["transitions"][0]["gate"] = {
        "kind": "subprocess-outcome",
        "outcome": "verified",
        "predicate": {"run": "nope"},
    }
    assert _errors(d), "a subprocess-outcome gate forbids a capability predicate"


def test_predicate_gate_with_stray_outcome_rejected() -> None:
    d = _base_definition()
    d["transitions"][0]["authorisation"] = "agent-autonomous"
    d["transitions"][0]["gate"] = {
        "kind": "deterministic",
        "predicate": {"run": "check"},
        "outcome": "verified",
    }
    assert _errors(d), "a predicate-backed gate must not carry an `outcome`"


def test_malformed_subprocess_address_rejected() -> None:
    d = _base_definition()
    d["states"][0]["subprocess"] = {"runs": "no-colon-here"}
    assert _errors(d), "`runs` must be a <capability>:<process-id> address"


def test_awaiting_subprocess_outcome_blocked_reason_accepted() -> None:
    d = _base_definition()
    d["subject"]["blocked"] = {"blocked_on": "awaiting-subprocess-outcome"}
    assert _errors(d) == []


def test_awaiting_subprocess_outcome_forbids_resume_when() -> None:
    d = _base_definition()
    d["subject"]["blocked"] = {
        "blocked_on": "awaiting-subprocess-outcome",
        "resume_when": {"run": "nope"},
    }
    assert _errors(d), (
        "awaiting-subprocess-outcome carries no resume_when (the resolution is the check)"
    )
