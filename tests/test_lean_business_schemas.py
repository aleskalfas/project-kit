"""lean-business's schemas (DEC-002): each reference instance and each fixture file is
valid, a shape the records refuse is refused, and the ids the check reads are the ids the
schemas allow."""

from __future__ import annotations

import copy
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from project_kit import data_validate as dv
from tests.in_process import load

(ids, reading) = load("lean-business", "ids", "reading")

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMAS = REPO_ROOT / ".pkit/capabilities/lean-business/schemas"
FIXTURES = Path(__file__).resolve().parent / "fixtures/lean-business"
IDEA = FIXTURES / "repo/lean-business/meal-plan"

DOCUMENTS = ("config", "goal", "canvas", "assumptions", "experiment", "cycle")


def _registry() -> Registry[Any]:
    resources = []
    for path in sorted(SCHEMAS.glob("*.schema.json")):
        schema = json.loads(path.read_text(encoding="utf-8"))
        resources.append((schema["$id"], Resource.from_contents(schema)))
    return Registry().with_resources(resources)


REGISTRY = _registry()


def validator(name: str) -> Draft202012Validator:
    schema = json.loads((SCHEMAS / f"{name}.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, registry=REGISTRY)


def errors(name: str, data: Any) -> list[str]:
    return [error.message for error in validator(name).iter_errors(data)]


def fixture(rel: str) -> dict[str, Any]:
    return reading.read_yaml(IDEA / rel)


# --- what is valid ------------------------------------------------------------------------------


@pytest.mark.parametrize("name", DOCUMENTS)
def test_each_reference_instance_is_valid(name: str) -> None:
    assert errors(name, reading.read_yaml(SCHEMAS / f"{name}.yaml")) == []


def test_every_fixture_file_is_valid_under_data_validation() -> None:
    report = dv.validate_path(FIXTURES, REPO_ROOT)
    assert [(i.location, i.message) for i in report.issues] == []
    assert len(dv.discover_data_files(FIXTURES)) == 7


def test_the_shared_shapes_allow_the_ids_and_references_the_check_reads() -> None:
    shapes = json.loads((SCHEMAS / "shapes.schema.json").read_text(encoding="utf-8"))["$defs"]
    assert shapes["segment"]["pattern"] == f"^{ids.SEGMENT}$"
    assert shapes["idea-qualified-id"]["pattern"] == f"^{ids.IDEA_QUALIFIED}$"
    assert shapes["variant-qualified-id"]["pattern"] == f"^{ids.VARIANT_QUALIFIED}$"
    for name, namespace in (
        ("canvas-ref", ids.CANVAS),
        ("assumption-ref", ids.ASSUMPTIONS),
        ("experiment-ref", ids.EXPERIMENT),
        ("cycle-ref", ids.CYCLE),
    ):
        assert shapes[name]["pattern"] == f"^{ids.REF_PATTERN[namespace]}$"


def test_an_id_is_read_as_the_schemas_allow_it() -> None:
    assert ids.is_idea_qualified("meal-plan.direct")
    assert ids.is_variant_qualified("meal-plan.direct.planning-takes-long")
    assert not ids.is_idea_qualified("Meal-plan.direct")
    assert not ids.is_segment("meal--plan")
    assert ids.parse_ref("[canvas:meal-plan.direct]", ids.CANVAS) == ("canvas", "meal-plan.direct")
    assert ids.parse_ref("[cycle:meal-plan.direct]", ids.CANVAS) is None
    assert ids.parse_ref("canvas:meal-plan.direct", ids.CANVAS) is None
    assert ids.idea_of("meal-plan.direct.x") == "meal-plan"
    assert ids.qualifier("meal-plan.direct.x") == "meal-plan.direct"
    assert ids.own("meal-plan.direct.x") == "x"
    assert ids.ref(ids.CYCLE, "meal-plan.first") == "[cycle:meal-plan.first]"


# --- what is refused ----------------------------------------------------------------------------


def _set(path: tuple[Any, ...], value: Any) -> Callable[[Any], None]:
    def change(data: Any) -> None:
        node = data
        for key in path[:-1]:
            node = node[key]
        if value is _DROP:
            del node[path[-1]]
        else:
            node[path[-1]] = value

    return change


_DROP = object()

REFUSED: list[tuple[str, str, str, Callable[[Any], None]]] = [
    ("an-upper-case-id", "canvas", "variants/direct/canvas.yaml", _set(("id",), "Meal.direct")),
    (
        "a-bare-reference",
        "experiment",
        "experiments/first-interviews.yaml",
        _set(("cycle",), "meal-plan.first"),
    ),
    (
        "a-reference-into-another-namespace",
        "experiment",
        "experiments/first-interviews.yaml",
        _set(("assumption",), "[canvas:meal-plan.direct]"),
    ),
    (
        "a-shortlisting-without-its-fingerprint",
        "canvas",
        "variants/direct/canvas.yaml",
        _set(("outcome", "fingerprint"), _DROP),
    ),
    (
        "a-shelving-without-its-reason",
        "canvas",
        "variants/two-sided/canvas.yaml",
        _set(("outcome", "reason"), _DROP),
    ),
    (
        "an-answer-written-as-a-flag",
        "canvas",
        "variants/direct/canvas.yaml",
        _set(("verdicts", "desirability", "answer"), True),
    ),
    (
        "a-short-digest",
        "cycle",
        "cycles/first.yaml",
        _set(("planned", "fingerprint", "sha256"), "abc"),
    ),
    (
        "a-generative-experiment-with-an-action",
        "experiment",
        "experiments/first-interviews.yaml",
        _set(("action",), "Show a page"),
    ),
    (
        "an-evaluative-experiment-with-a-stopping-rule-reached",
        "experiment",
        "experiments/landing-page.yaml",
        _set(("stopped",), {"by": "A. Founder", "when": "2026-12-20"}),
    ),
    (
        "a-threshold-beside-a-range",
        "experiment",
        "experiments/landing-page.yaml",
        _set(("expected", "threshold"), 0.05),
    ),
    (
        "a-day-with-a-time",
        "goal",
        "goal.yaml",
        _set(("when",), "2026-10-01T10:00:00"),
    ),
    (
        "an-assumption-from-an-entry-and-an-input",
        "assumptions",
        "variants/direct/assumptions.yaml",
        _set(("assumptions", 0, "source", "input"), "price"),
    ),
    (
        "a-suspension-without-its-reason",
        "cycle",
        "cycles/first.yaml",
        _set(("suspensions", 0, "reason"), _DROP),
    ),
    (
        "a-cycle-exploring-nothing",
        "cycle",
        "cycles/first.yaml",
        _set(("variants",), []),
    ),
    (
        "a-field-the-schema-does-not-name",
        "goal",
        "goal.yaml",
        _set(("currency",), "EUR"),
    ),
]


@pytest.mark.parametrize(
    ("name", "rel", "change"), [r[1:] for r in REFUSED], ids=[r[0] for r in REFUSED]
)
def test_a_shape_the_records_refuse_is_refused(
    name: str, rel: str, change: Callable[[Any], None]
) -> None:
    data = copy.deepcopy(fixture(rel))
    assert errors(name, data) == []
    change(data)
    assert errors(name, data)


@pytest.mark.parametrize(
    "location", ["/ideas", "\\ideas", ""], ids=["absolute", "backslash", "empty"]
)
def test_the_configuration_refuses_a_location_that_is_no_relative_path(location: str) -> None:
    config = {"pkit_schema": "lean-business:config", "schema_version": 1, "location": location}
    assert errors("config", config)


def test_a_split_names_the_variants_it_went_into() -> None:
    data = copy.deepcopy(fixture("variants/two-sided/canvas.yaml"))
    outcome: dict[str, Any] = {"kind": "split", "by": "A. Founder", "when": "2026-10-05"}
    data["outcome"] = outcome
    assert errors("canvas", data)
    outcome["into"] = ["[canvas:meal-plan.cooks]"]
    assert errors("canvas", data) == []


def test_a_split_control_names_the_share_exposed() -> None:
    data = copy.deepcopy(fixture("experiments/landing-page.yaml"))
    control: dict[str, Any] = {"kind": "split"}
    data["control"] = control
    assert errors("experiment", data)
    control["exposed"] = 0.5
    assert errors("experiment", data) == []
