"""Schema-shape tests for the COR-038 `depends_on` additions.

Validates a `process` definition fragment against the shape contract
(`_defs/process.schema.json#/$defs/process`), covering:

- the optional per-state `depends_on` list accepted (well-formed entries);
- each entry's required `{upstream, relation, mode, why}`;
- the CLOSED relation set is exactly the four COR-038 values -- and the
  derive-don't-annotate exclusions `composed-subprocess` / `aggregates` are
  REJECTED (those edges are derived from subprocess/cascade, never annotated);
- rejection of every malformed shape: bad `upstream` address, `relation` outside
  the closed set, bad `mode`, missing / empty `why`, an extra property;
- the additive guarantee: a definition carrying NO `depends_on` validates
  byte-unchanged (no `depends_on` key needed);
- COR-053's additive fields: a role-addressed `upstream`
  (`<publisher>::<role>:<point>`), the `mandatory` mark (only with a reason),
  the targeted interface `version`, and an `interface.version` -- with every
  process definition the corpus ships validating unchanged against the widened
  contract.

The connection metadata is INERT -- the engine never reads it (asserted in
test_process_depends_on_engine.py). Here we pin only its SHAPE, the static
authoring concern the schema owns.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012
from ruamel.yaml import YAML

_REPO = Path(__file__).resolve().parents[1]
_SCHEMA_PATH = _REPO / ".pkit" / "schemas" / "_defs" / "process.schema.json"
_yaml = YAML(typ="safe")

# The exact closed relation set COR-038 declares -- enforced visible in the
# schema enum, asserted whole below.
_CLOSED_RELATION_SET = {
    "informational",
    "gates-on-readiness",
    "triggered-by",
    "constrained-with",
}


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


def _entry() -> dict[str, Any]:
    """A well-formed depends_on entry."""
    return {
        "upstream": "design:screen-ladder",
        "relation": "gates-on-readiness",
        "mode": "pull",
        "why": "This stage may only start once the screen design is approved upstream.",
    }


def _with_entry(entry: dict[str, Any]) -> dict[str, Any]:
    d = _base_definition()
    d["states"][0]["depends_on"] = [entry]
    return d


# --- additive guarantee ---------------------------------------------------


def test_base_definition_without_depends_on_validates() -> None:
    # Additive guarantee: a definition declaring no depends_on is valid as-is.
    d = _base_definition()
    assert "depends_on" not in d["states"][0]
    assert _errors(d) == []


# --- well-formed entries accepted -----------------------------------------


def test_well_formed_entry_accepted() -> None:
    assert _errors(_with_entry(_entry())) == []


def test_multiple_entries_accepted() -> None:
    d = _base_definition()
    d["states"][0]["depends_on"] = [
        _entry(),
        {
            "upstream": "project-management:issue",
            "relation": "triggered-by",
            "mode": "push",
            "why": "A connector kicks this process off when the issue is promoted.",
        },
    ]
    assert _errors(d) == []


def test_each_closed_relation_value_accepted() -> None:
    for relation in _CLOSED_RELATION_SET:
        entry = _entry()
        entry["relation"] = relation
        assert _errors(_with_entry(entry)) == [], f"{relation} should be accepted"


def test_both_modes_accepted() -> None:
    for mode in ("pull", "push"):
        entry = _entry()
        entry["mode"] = mode
        assert _errors(_with_entry(entry)) == [], f"mode {mode} should be accepted"


# --- the closed relation set ----------------------------------------------


def test_closed_relation_set_is_exactly_the_four_values() -> None:
    full = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    enum = full["$defs"]["depends_on"]["properties"]["relation"]["enum"]
    assert set(enum) == _CLOSED_RELATION_SET
    assert len(enum) == len(_CLOSED_RELATION_SET) == 4


def test_composed_subprocess_relation_rejected() -> None:
    # Derive-don't-annotate: a composition edge is declared by `subprocess`,
    # never annotated -- so `composed-subprocess` is NOT a valid relation value.
    entry = _entry()
    entry["relation"] = "composed-subprocess"
    assert _errors(_with_entry(entry)), (
        "composed-subprocess must be rejected -- composition edges are derived "
        "from `subprocess`, never annotated"
    )


def test_aggregates_relation_rejected() -> None:
    # Derive-don't-annotate: an aggregation edge is declared by `cascade`,
    # never annotated -- so `aggregates` is NOT a valid relation value.
    entry = _entry()
    entry["relation"] = "aggregates"
    assert _errors(_with_entry(entry)), (
        "aggregates must be rejected -- aggregation edges are derived from "
        "`cascade`, never annotated"
    )


def test_unknown_relation_rejected() -> None:
    entry = _entry()
    entry["relation"] = "depends"
    assert _errors(_with_entry(entry)), "a relation outside the closed set is rejected"


# --- malformed shapes rejected --------------------------------------------


def test_malformed_upstream_address_rejected() -> None:
    entry = _entry()
    entry["upstream"] = "no-colon-here"
    assert _errors(_with_entry(entry)), "`upstream` must be a <capability>:<process-id> address"


def test_bad_mode_rejected() -> None:
    entry = _entry()
    entry["mode"] = "poll"
    assert _errors(_with_entry(entry)), "`mode` is a closed two-value enum (pull | push)"


def test_missing_why_rejected() -> None:
    entry = _entry()
    del entry["why"]
    assert _errors(_with_entry(entry)), "`why` is required on every entry"


def test_empty_why_rejected() -> None:
    entry = _entry()
    entry["why"] = ""
    assert _errors(_with_entry(entry)), "`why` must be a non-empty string"


def test_missing_upstream_rejected() -> None:
    entry = _entry()
    del entry["upstream"]
    assert _errors(_with_entry(entry)), "`upstream` is required on every entry"


def test_missing_relation_rejected() -> None:
    entry = _entry()
    del entry["relation"]
    assert _errors(_with_entry(entry)), "`relation` is required on every entry"


def test_missing_mode_rejected() -> None:
    entry = _entry()
    del entry["mode"]
    assert _errors(_with_entry(entry)), "`mode` is required on every entry"


def test_extra_property_rejected() -> None:
    # additionalProperties false on the entry: no smuggled fields (e.g. an
    # `enforce` flag that would imply the engine acts on it -- it never does).
    entry = _entry()
    entry["enforce"] = True
    assert _errors(_with_entry(entry)), "an entry forbids additional properties"


# --- connections by role (COR-053, additive) ---------------------------------


def test_role_addressed_upstream_accepted() -> None:
    # COR-053 point 2: `<publisher>::<role>:<point>` names a process offered under
    # a role, whichever capability provides it.
    entry = _entry()
    entry["upstream"] = "pkit::work-tracking:issue-lifecycle"
    assert _errors(_with_entry(entry)) == []


def test_malformed_role_addresses_rejected() -> None:
    for upstream in (
        "pkit::work-tracking",  # a role, not a point
        "pkit::work-tracking:issue:extra",  # one point too many
        "pkit:::issue",  # empty role
        "Pkit::work-tracking:issue",  # not a word
        "::work-tracking:issue",  # no publisher
    ):
        entry = _entry()
        entry["upstream"] = upstream
        assert _errors(_with_entry(entry)), f"{upstream!r} must be rejected"


def test_mandatory_mark_with_a_reason_accepted() -> None:
    entry = _entry()
    entry["mandatory"] = {"reason": "Delivery cannot start without an approved design."}
    assert _errors(_with_entry(entry)) == []


def test_mandatory_mark_without_a_reason_rejected() -> None:
    # COR-053 point 6: optional is the norm; the mark is valid only with a reason.
    for mark in ({}, {"reason": ""}, True, "yes", {"reason": "why", "strict": True}):
        entry = _entry()
        entry["mandatory"] = mark
        assert _errors(_with_entry(entry)), f"mandatory {mark!r} must be rejected"


def test_targeted_interface_version_accepted_as_a_positive_integer() -> None:
    entry = _entry()
    entry["version"] = 2
    assert _errors(_with_entry(entry)) == []
    for bad in (0, -1, "2", 1.5, True):
        entry["version"] = bad
        assert _errors(_with_entry(entry)), f"version {bad!r} must be rejected"


def test_interface_version_accepted_as_a_positive_integer() -> None:
    # COR-036 as refined by COR-053 point 5: the interface carries its own integer,
    # distinct from the definition's `version`.
    d = _base_definition()
    d["states"][0]["terminal"] = True
    d["interface"] = {"version": 3, "outcomes": [{"name": "open"}]}
    assert _errors(d) == []
    for bad in (0, "3", True):
        d["interface"]["version"] = bad
        assert _errors(d), f"interface version {bad!r} must be rejected"


def test_every_shipped_definition_validates_unchanged() -> None:
    # The additive guarantee, on the real corpus: every process definition a
    # capability ships validates against the widened shape contract as it is.
    definitions = _shipped_definitions()
    assert definitions, "the corpus ships at least one process definition"
    validator = _registry_validator()
    for path, process in definitions:
        errors = [e.message for e in validator.iter_errors(process)]
        assert errors == [], f"{path.relative_to(_REPO)}: {errors}"


def _shipped_definitions() -> list[tuple[Path, Any]]:
    """Every capability schema file carrying a top-level `process:` block."""
    out: list[tuple[Path, Any]] = []
    for path in sorted((_REPO / ".pkit" / "capabilities").glob("*/schemas/*.yaml")):
        document = _yaml.load(path.read_text(encoding="utf-8"))
        if isinstance(document, dict) and isinstance(document.get("process"), dict):
            out.append((path, document["process"]))
    return out


def _registry_validator() -> Draft202012Validator:
    """The `process` $def with every shared `_defs` schema registered, so the
    cross-file references a real definition exercises (a transition's severity
    token) resolve."""
    registry: Registry = Registry()
    for path in sorted(_SCHEMA_PATH.parent.glob("*.schema.json")):
        document = json.loads(path.read_text(encoding="utf-8"))
        registry = registry.with_resource(
            uri=document.get("$id", path.name),
            resource=Resource.from_contents(document, default_specification=DRAFT202012),
        )
    full = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    return Draft202012Validator({"$ref": f"{full['$id']}#/$defs/process"}, registry=registry)
