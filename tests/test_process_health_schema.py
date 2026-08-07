"""Schema-shape tests for the COR-042 `handoff` sub-block on a `depends_on`
entry — the opt-in evaluable hand-off contract.

Validates a `process` definition fragment against the shape contract
(`_defs/process.schema.json#/$defs/process`), covering:

- the optional `handoff` sub-block accepted on a well-formed entry (trigger +
  the two ADR-048 seam predicates, `candidates` / `resolve`);
- the additive guarantee: entries WITHOUT a `handoff` block validate unchanged
  (COR-042: the field is additive; existing definitions validate byte-
  unchanged, and an entry without a contract keeps its full inert status);
- rejection of every malformed shape: missing/empty `trigger`, missing
  `candidates` / `resolve`, a predicate without `run`, an extra property.

Shape lint here is LOCAL well-formedness only (COR-042 point 1): whether the
contract can be INTERPRETED — the upstream address resolves, the trigger is a
real state of that upstream — is checked at health time, where it fails closed
(asserted in test_process_health.py). A syntactically valid contract naming a
phantom trigger is deliberately ACCEPTED here.
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
    cross-references (`state`, `depends_on`, `predicate`, ...) resolve."""
    full = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    defs = full["$defs"]
    schema = dict(defs["process"])
    schema["$defs"] = defs
    return Draft202012Validator(schema)


def _errors(definition: dict[str, Any]) -> list[str]:
    return [e.message for e in _process_validator().iter_errors(definition)]


def _base_definition() -> dict[str, Any]:
    """A minimal valid singleton process -- no depends_on."""
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


def _handoff() -> dict[str, Any]:
    """A well-formed hand-off contract sub-block."""
    return {
        "trigger": "implementation-ready",
        "candidates": {"run": "list-ready-screens"},
        "resolve": {"run": "unit-for-screen"},
    }


def _entry(handoff: dict[str, Any] | None = None) -> dict[str, Any]:
    """A well-formed depends_on entry, optionally carrying a contract."""
    entry: dict[str, Any] = {
        "upstream": "design:screen",
        "relation": "triggered-by",
        "mode": "push",
        "why": "A unit builds a screen the design process readied.",
    }
    if handoff is not None:
        entry["handoff"] = handoff
    return entry


def _with_entry(entry: dict[str, Any]) -> dict[str, Any]:
    d = _base_definition()
    d["states"][0]["depends_on"] = [entry]
    return d


# --- additive guarantee ---------------------------------------------------


def test_entry_without_handoff_validates_unchanged() -> None:
    # COR-042: the contract is OPT-IN and additive -- an entry without it is
    # exactly the COR-038 shape, valid as before.
    assert _errors(_with_entry(_entry())) == []


# --- well-formed contracts accepted ---------------------------------------


def test_well_formed_handoff_accepted() -> None:
    assert _errors(_with_entry(_entry(_handoff()))) == []


def test_handoff_on_any_relation_and_mode_accepted() -> None:
    # COR-042: the contract is ORTHOGONAL to relation and mode -- a push-mode
    # triggered-by edge and a pull constrained-with edge alike may carry one
    # (no adopter is forced to relabel an edge to get checking).
    for relation, mode in (
        ("constrained-with", "pull"),
        ("triggered-by", "push"),
        ("informational", "pull"),
        ("gates-on-readiness", "pull"),
    ):
        entry = _entry(_handoff())
        entry["relation"] = relation
        entry["mode"] = mode
        assert _errors(_with_entry(entry)) == [], f"{relation}/{mode} should carry a contract"


def test_predicates_may_carry_with_args() -> None:
    handoff = _handoff()
    handoff["candidates"] = {"run": "list-ready-screens", "with": {"root": "design/screens"}}
    assert _errors(_with_entry(_entry(handoff))) == []


def test_phantom_trigger_is_not_a_shape_concern() -> None:
    # Shape lint is LOCAL well-formedness: whether the trigger is a real state
    # of the upstream is a HEALTH-time question (where it fails closed as
    # indeterminate), not a schema one. Any non-empty string passes here.
    handoff = _handoff()
    handoff["trigger"] = "no-such-state-anywhere"
    assert _errors(_with_entry(_entry(handoff))) == []


# --- malformed shapes rejected --------------------------------------------


def test_missing_trigger_rejected() -> None:
    handoff = _handoff()
    del handoff["trigger"]
    assert _errors(_with_entry(_entry(handoff))), "`trigger` is required"


def test_empty_trigger_rejected() -> None:
    handoff = _handoff()
    handoff["trigger"] = ""
    assert _errors(_with_entry(_entry(handoff))), "`trigger` must be non-empty"


def test_missing_candidates_rejected() -> None:
    handoff = _handoff()
    del handoff["candidates"]
    assert _errors(_with_entry(_entry(handoff))), "`candidates` is required"


def test_missing_resolve_rejected() -> None:
    handoff = _handoff()
    del handoff["resolve"]
    assert _errors(_with_entry(_entry(handoff))), "`resolve` is required"


def test_predicate_without_run_rejected() -> None:
    handoff = _handoff()
    handoff["resolve"] = {"with": {"root": "delivery/units"}}
    assert _errors(_with_entry(_entry(handoff))), (
        "a seam predicate must name a registered command (`run`)"
    )


def test_extra_property_rejected() -> None:
    handoff = _handoff()
    handoff["on_miss"] = "block"
    assert _errors(_with_entry(_entry(handoff))), (
        "the contract is a closed shape -- no enforcement/remediation fields "
        "(report-only is the COR-042 boundary)"
    )
