"""The component's schema, format 1 (visual-communication DEC-001 points 4 and 6, DEC-005 points
1 to 3): strict to the format the engine reads. Its keys follow the engine's own tables
(`_lib/layout.py`), the shipped and fixture components hold it, and what the engine refuses
in a component's shape the schema refuses too. Broken components are mappings in memory:
the repository's validation reads every bound YAML file under `tests/`."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from tests.in_process import load
from tests.visual_communication_project import FIXTURES, FOUNDATIONS, SCHEMAS
from tests.visual_engine import FakeEnv
from tests.visual_engine import layout as engine

files, reading = load("visual-communication", "files", "reading")

SCHEMA = json.loads((SCHEMAS / "component.schema.json").read_text(encoding="utf-8"))
DEFS = SCHEMA["$defs"]

COMPONENTS = [
    FOUNDATIONS / "components" / "figure.yaml",
    *sorted((FIXTURES / "libraries" / "tests" / "1.0.0" / "components").glob("*.yaml")),
    SCHEMAS / "component.yaml",
]


def problems(data: Any) -> list[str]:
    return files.shape_problems(data, "component")


def engine_issues(data: Any) -> list[tuple[str, str, str]]:
    """What the engine finds in a component when it reads it."""
    return engine.Component("lab/x", data, engine.Context(FakeEnv(), "en")).issues


def reference() -> dict[str, Any]:
    return reading.read_yaml(SCHEMAS / "component.yaml")


def changed(path: str, value: Any, data: dict[str, Any] | None = None) -> dict[str, Any]:
    """The reference instance with the value at the dotted `path` set to `value`, or
    removed where `value` is `...`."""
    found = copy.deepcopy(data if data is not None else reference())
    *parents, last = path.split(".")
    at = found
    for key in parents:
        at = at[key]
    if value is ...:
        del at[last]
    else:
        at[last] = value
    return found


# --- the schema follows the engine --------------------------------------------------------------


def test_a_component_takes_the_keys_the_engine_reads() -> None:
    assert list(SCHEMA["properties"]) == list(engine.COMPONENT_KEYS)
    assert SCHEMA["additionalProperties"] is False


@pytest.mark.parametrize("kind", engine.KINDS)
def test_each_kind_of_part_takes_the_keys_the_engine_reads(kind: str) -> None:
    part = DEFS[f"{kind}-part"]
    assert part["additionalProperties"] is False
    assert set(part["properties"]) == {kind, "when", *engine.PART_KEYS[kind]}
    assert set(part["required"]) == {kind, *engine.REQUIRED.get(kind, ())}


@pytest.mark.parametrize("kind", engine.PRIMITIVES)
def test_each_primitive_takes_the_properties_the_engine_reads(kind: str) -> None:
    properties = DEFS[kind]
    assert properties["additionalProperties"] is False
    assert set(properties["properties"]) == set(engine.PROPERTIES[kind])
    assert set(properties.get("required", ())) == set(engine.REQUIRED_PROPERTIES.get(kind, ()))


@pytest.mark.parametrize("prop", sorted(engine.WORDS))
def test_each_property_of_words_takes_the_engines_words(prop: str) -> None:
    (words, _switch) = DEFS[f"{prop}-value"]["anyOf"]
    assert words["enum"] == list(engine.WORDS[prop])


def test_a_part_is_exactly_one_kind_of_the_engines() -> None:
    assert [one["required"] for one in DEFS["part"]["oneOf"]] == [[kind] for kind in engine.KINDS]


def test_the_operators_take_the_engines_settings() -> None:
    assert set(DEFS["operator"]["properties"]) == {"gap", *engine.OPERATOR_WORDS}
    assert {"row", "column"} == set(engine.OPERATORS)


# --- what holds ---------------------------------------------------------------------------------


@pytest.mark.parametrize("path", COMPONENTS, ids=lambda path: path.stem)
def test_the_shipped_and_fixture_components_hold_the_schema_and_the_engine(path: Path) -> None:
    data = reading.read_yaml(path)
    assert problems(data) == []
    assert engine_issues(data) == []


@pytest.mark.parametrize(
    ("path", "value"),
    [
        ("parts.label.text.fill", ":colour.fill"),
        ("parts.box.box.stroke", {"by": "emphasis", "normal": None, "strong": "line"}),
        ("parts.label.when", "tags"),
        ("parts.label.when", {"emphasis": ["strong"]}),
        ("parts.label.when", {"emphasis": "strong"}),
        ("parts.label.text.text-anchor", {"by": "emphasis", "normal": "start", "strong": "end"}),
        ("states", {"done": {"colour": "success"}, "idle": {}}),
        ("options.at", {"item": "tags"}),
    ],
)
def test_the_format_takes_each_way_of_writing_a_value(path: str, value: Any) -> None:
    """The schema alone: what crosses keys, such as an item option's list being repeated
    over, the engine judges when it reads the component."""
    assert problems(changed(path, value)) == []


# --- what format 1 refuses ----------------------------------------------------------------------


REFUSED: list[tuple[str, str, Any]] = [
    # (case, dotted path, value) on the reference instance; `...` removes the key.
    ("a key no component takes", "define", {"x": {}}),
    ("a part of no kind", "parts.label", {"x": "=0"}),
    ("a part of two kinds", "parts.box.slot", "text"),
    ("a key its kind does not take", "parts.box.x1", "=0"),
    ("a text's height, which its measured text owns", "parts.label.height", "=0"),
    ("a box without its size", "parts.box.height", ...),
    ("a text without its style", "parts.label.text.style", ...),
    ("a property its primitive does not take", "parts.label.text.rx", "=@space.1"),
    ("a length that is no formula", "parts.box.width", 120),
    ("a formula's switch on no option", "values.pad", {"normal": "=@space.1"}),
    ("a paint that is no role", "parts.box.box.fill", "Surface"),
    ("a paint written as a formula", "parts.label.text.fill", "=@accent"),
    ("a word the property does not take", "parts.label.text.text-anchor", "left"),
    ("an option of no words", "options.emphasis", []),
    ("an option with a repeated word", "options.emphasis", ["normal", "normal"]),
    ("an option taking the switch's key as a word", "options.emphasis", ["normal", "by"]),
    ("an option named as a reserved key", "options.state", ["on", "off"]),
    (
        "an item option with a point that is not true",
        "options.at",
        {"item": "tags", "point": False},
    ),
    ("a preferred size that is no size", "preferred.depth", "=@space.1"),
    ("an exposed part that is no name", "exposes", ["Label"]),
    ("a part that is no name", "parts.Label", {"slot": "text"}),
    ("a `when` of two options", "parts.label.when", {"a": "x", "b": "y"}),
]


@pytest.mark.parametrize(("case", "path", "value"), REFUSED, ids=[case for case, _, _ in REFUSED])
def test_the_schema_refuses_what_the_engine_refuses(case: str, path: str, value: Any) -> None:
    data = changed(path, value)
    assert problems(data) != [], case
    assert engine_issues(data) != [], case


def repeat(**more: Any) -> dict[str, Any]:
    part = {"repeat": "tags", "draw": "lab/tag", "width": "=:width", "row": {"gap": "=@space.1"}}
    return {**part, **more}


@pytest.mark.parametrize(
    ("case", "part"),
    [
        ("a list arranged by neither operator", {k: v for k, v in repeat().items() if k != "row"}),
        ("a list arranged by both operators", repeat(column={})),
        ("an operator setting it does not take", repeat(row={"wrap": "yes"})),
        ("a list drawn by no component", {k: v for k, v in repeat().items() if k != "draw"}),
        ("a list drawn by no use", repeat(draw="tag")),
        ("sizes the operator does not take", repeat(row={"sizes": "fill"})),
        ("a use passing a field that is no name", {"use": "lab/tag", "fields": {"text": "A b"}}),
        ("a use with a colour", {"use": "lab/tag", "colour": "accent"}),
        ("a use with a state", {"use": "lab/tag", "state": "done"}),
        ("a use that is no use", {"use": "tag"}),
        ("a line without its ends", {"line": {"stroke": "line"}, "x1": "=0", "y1": "=0"}),
        ("a line without its stroke", {"line": {}, "x1": "=0", "y1": "=0", "x2": "=0", "y2": "=0"}),
        ("an image without its output", {"image": {}, "width": "=:width"}),
    ],
    ids=lambda value: value if isinstance(value, str) else "",
)
def test_the_schema_refuses_a_part_the_engine_refuses(case: str, part: dict[str, Any]) -> None:
    data = changed("parts.extra", part)
    assert problems(data) != [], case
    assert engine_issues(data) != [], case


@pytest.mark.parametrize(
    ("case", "layouts"),
    [
        ("no layout", {}),
        ("two layouts, which format 1 does not take", {"a": {"slots": {}}, "b": {"slots": {}}}),
        ("a layout without slots", {"frame": {}}),
    ],
)
def test_a_top_components_layouts_take_one_layout_with_its_slots(
    case: str, layouts: dict[str, Any]
) -> None:
    data = changed("layouts", layouts)
    assert problems(data) != [], case
    assert engine_issues(data) != [], case
    assert problems(changed("layouts", {"frame": {"slots": {"text": {"pages": True}}}})) == []


@pytest.mark.parametrize(
    ("case", "path", "value"),
    [
        (
            "a slot that says its items are not pages",
            "layouts",
            {"f": {"slots": {"text": {"pages": False}}}},
        ),
        ("a primitive with no mapping of properties", "parts.box.box", None),
        ("an operator with no mapping of settings", "parts.extra", repeat(row=None)),
        ("a state with no mapping", "states", {"done": None}),
        ("a state of another shape", "states", {"done": "success"}),
        ("a slot of another shape", "layouts", {"f": {"slots": {"text": {"pages": "yes"}}}}),
        ("a colour family that is no name", "colour", "Brand Blue"),
    ],
)
def test_format_1_is_stricter_than_the_engine_where_the_engine_reads_nothing(
    case: str, path: str, value: Any
) -> None:
    """The engine reads these as saying nothing, or does not judge them yet, such as a colour
    family before notations name families. Format 1 refuses them, so a later format may give
    these spellings a meaning as an addition."""
    data = changed(path, value)
    assert problems(data) != [], case
    assert engine_issues(data) == [], case
