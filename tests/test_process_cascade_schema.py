"""Schema-shape tests for the COR-037 cascade additions.

Validates a `process` definition fragment against the shape contract
(`_defs/process.schema.json#/$defs/process`), covering:

- the optional `cascade` block ({runs, members, membership, reducer}) accepted,
  for both `all` and `count` reducers;
- the `count` reducer requires a `threshold`; `all` forbids one;
- a `cascade-outcome` gate (forbids both predicate and a per-gate outcome);
- rejection of a malformed `cascade.runs` address and an incomplete cascade;
- the `awaiting-cascade-outcome` blocked reason (accepted; forbids `resume_when`);
- the additive guarantee: a definition carrying no cascade validates unchanged,
  and the COR-036 composition shapes still validate (no regression).
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
    """A minimal valid keyed process — no cascade."""
    return {
        "id": "area-discovery",
        "version": 1,
        "subject": {"cardinality": "keyed", "key": "area-id"},
        "states": [
            {
                "id": "discovering",
                "meaning": "Discovering an area.",
                "detection": {"mode": "inferred", "predicate": {"run": "detect-discovering"}},
            },
            {
                "id": "discovered",
                "meaning": "Discovered.",
                "terminal": True,
                "detection": {"mode": "inferred", "predicate": {"run": "detect-discovered"}},
            },
        ],
        "transitions": [
            {
                "from": "discovering",
                "to": "discovered",
                "trigger": "close",
                "authorisation": "agent-autonomous",
            }
        ],
    }


def _all_cascade() -> dict[str, Any]:
    return {
        "runs": "fixture:poi-verification",
        "members": {"run": "area-pois"},
        "membership": {"run": "poi-in-area"},
        "reducer": {"op": "all", "outcome": "verified"},
    }


def test_cascade_free_definition_validates() -> None:
    # The additive guarantee: a definition with no cascade fields is valid.
    assert _errors(_base_definition()) == []


def test_all_cascade_accepted() -> None:
    d = _base_definition()
    d["cascade"] = _all_cascade()
    assert _errors(d) == []


def test_count_cascade_with_threshold_accepted() -> None:
    d = _base_definition()
    cascade = _all_cascade()
    cascade["reducer"] = {"op": "count", "outcome": "verified", "threshold": 3}
    d["cascade"] = cascade
    assert _errors(d) == []


def test_count_cascade_without_threshold_rejected() -> None:
    d = _base_definition()
    cascade = _all_cascade()
    cascade["reducer"] = {"op": "count", "outcome": "verified"}
    d["cascade"] = cascade
    assert _errors(d), "a `count` reducer must name a `threshold`"


def test_all_cascade_with_threshold_rejected() -> None:
    d = _base_definition()
    cascade = _all_cascade()
    cascade["reducer"] = {"op": "all", "outcome": "verified", "threshold": 2}
    d["cascade"] = cascade
    assert _errors(d), "an `all` reducer forbids a `threshold`"


def test_incomplete_cascade_rejected() -> None:
    d = _base_definition()
    # Missing `membership` and `reducer`.
    d["cascade"] = {"runs": "fixture:poi-verification", "members": {"run": "area-pois"}}
    assert _errors(d), "a cascade requires runs / members / membership / reducer"


def test_malformed_cascade_runs_address_rejected() -> None:
    d = _base_definition()
    cascade = _all_cascade()
    cascade["runs"] = "no-colon-here"
    d["cascade"] = cascade
    assert _errors(d), "`runs` must be a <capability>:<process-id> address"


def test_cascade_outcome_gate_accepted() -> None:
    d = _base_definition()
    d["cascade"] = _all_cascade()
    d["transitions"][0]["gate"] = {"kind": "cascade-outcome"}
    assert _errors(d) == []


def test_cascade_outcome_gate_with_predicate_rejected() -> None:
    d = _base_definition()
    d["transitions"][0]["gate"] = {"kind": "cascade-outcome", "predicate": {"run": "nope"}}
    assert _errors(d), "a cascade-outcome gate forbids a capability predicate"


def test_cascade_outcome_gate_with_outcome_rejected() -> None:
    d = _base_definition()
    d["transitions"][0]["gate"] = {"kind": "cascade-outcome", "outcome": "verified"}
    assert _errors(d), "a cascade-outcome gate forbids a per-gate outcome (it lives in the reducer)"


def test_awaiting_cascade_outcome_blocked_reason_accepted() -> None:
    d = _base_definition()
    d["subject"]["blocked"] = {"blocked_on": "awaiting-cascade-outcome"}
    assert _errors(d) == []


def test_awaiting_cascade_outcome_forbids_resume_when() -> None:
    d = _base_definition()
    d["subject"]["blocked"] = {
        "blocked_on": "awaiting-cascade-outcome",
        "resume_when": {"run": "nope"},
    }
    assert _errors(d), (
        "awaiting-cascade-outcome carries no resume_when (the fold is the check)"
    )


def test_subprocess_outcome_gate_still_accepted() -> None:
    # No regression: the COR-036 subprocess-outcome gate still validates under
    # the widened gate if/then.
    d = _base_definition()
    d["states"][0]["subprocess"] = {"runs": "fixture:verification"}
    d["transitions"][0]["gate"] = {"kind": "subprocess-outcome", "outcome": "verified"}
    assert _errors(d) == []


def test_deterministic_gate_still_accepted() -> None:
    # No regression: an ordinary predicate-backed gate still validates.
    d = _base_definition()
    d["transitions"][0]["gate"] = {"kind": "deterministic", "predicate": {"run": "check"}}
    assert _errors(d) == []
