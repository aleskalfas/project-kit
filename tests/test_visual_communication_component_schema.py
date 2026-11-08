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
    FOUNDATIONS / "components" / "deck.yaml",
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
    required = set(part["required"])
    if kind == "line":
        # A line gives its ends, or connects its component's (DEC-011 point 1).
        given, connects = part["oneOf"]
        required |= set(given["required"])
        assert connects["required"] == ["connect"]
    assert required == {kind, *engine.REQUIRED.get(kind, ())}


@pytest.mark.parametrize("kind", engine.PRIMITIVES)
def test_each_primitive_takes_the_properties_the_engine_reads(kind: str) -> None:
    properties = DEFS[kind]
    assert properties["additionalProperties"] is False
    assert set(properties["properties"]) == set(engine.PROPERTIES[kind])
    assert set(properties.get("required", ())) == set(engine.REQUIRED_PROPERTIES.get(kind, ()))


#: The properties of words that share one definition of their words.
SHARED = {"marker-start": "marker", "marker-end": "marker"}


@pytest.mark.parametrize("prop", sorted(engine.WORDS))
def test_each_property_of_words_takes_the_engines_words(prop: str) -> None:
    (words, _switch) = DEFS[f"{SHARED.get(prop, prop)}-value"]["anyOf"]
    assert words["enum"] == list(engine.WORDS[prop])


def test_a_text_takes_the_engines_facts() -> None:
    assert DEFS["text"]["properties"]["fact"]["enum"] == list(engine.FACTS)
    assert DEFS["text"]["oneOf"] == [{"required": ["content"]}, {"required": ["fact"]}]


def test_an_image_shows_exactly_one_of_the_engines_sources() -> None:
    assert DEFS["image"]["oneOf"] == [{"required": [source]} for source in engine.IMAGE_SOURCES]


@pytest.mark.parametrize(
    "image",
    [{"produced": "text"}, {"content": "text"}, {"file": "logo.png"}, {"role": "picture.logo"}],
    ids=["produced", "content", "file", "role"],
)
def test_an_image_of_each_source_holds_the_schema_and_the_engine(image: dict[str, str]) -> None:
    data = changed("parts.extra", {"image": image, "width": "=:width"})
    assert problems(data) == []
    assert engine_issues(data) == []


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
        *(("parts.stamp.text.fact", word) for word in engine.FACTS),
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
    ("a text that names neither a field nor a fact", "parts.label.text.content", ...),
    ("a text that names a field and a fact", "parts.label.text.fact", "version"),
    ("a word no fact takes", "parts.stamp.text.fact", "number"),
    (
        "a fact chosen by a switch",
        "parts.stamp.text.fact",
        {"by": "emphasis", "normal": "version", "strong": "date"},
    ),
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


# --- a switch and a `when` by a size (DEC-021 point 3) ------------------------------------------


class _Device:
    """The size axis `device`, as the foundations will declare it."""

    modes = ("desktop", "tablet", "phone")
    default = "desktop"


def sized_issues(data: Any) -> list[tuple[str, str, str]]:
    """What the engine finds in a component when it reads it where the size axis `device`
    is one a piece can name."""
    sizes = engine.Sizes({"device": _Device()})
    return engine.Component("lab/x", data, engine.Context(FakeEnv(), "en", sizes=sizes)).issues


BY_SIZE: list[tuple[str, Any]] = [
    ("parts.label.x", {"by": ":device", "desktop": "=pad", "phone": "=@space.1"}),
    ("parts.box.box.fill", {"by": ":device", "desktop": "surface", "phone": None}),
    (
        "values.pad",
        {
            "by": ":device",
            "desktop": {"by": "emphasis", "normal": "=@space.1", "strong": "=@space.2"},
            "tablet": "=@space.1",
        },
    ),
    ("parts.label.text.text-anchor", {"by": ":device", "desktop": "start", "phone": "end"}),
    ("parts.label.when", {"by": ":device", "desktop": True, "phone": "tags"}),
    ("parts.label.when", {"by": ":device", "desktop": {"emphasis": ["strong"]}, "phone": False}),
]


@pytest.mark.parametrize(("path", "value"), BY_SIZE)
def test_the_format_takes_a_switch_and_a_when_by_a_size(path: str, value: Any) -> None:
    data = changed(path, value)
    assert problems(data) == []
    assert sized_issues(data) == []


REFUSED_BY_SIZE: list[tuple[str, str, Any]] = [
    ("a `when` by a size alone", "parts.label.when", {"by": ":device"}),
    (
        "a `when` by a size that switches again",
        "parts.label.when",
        {"by": ":device", "desktop": {"by": ":device", "desktop": True}},
    ),
    ("a branch of a `when` that is no `when`", "parts.label.when", {"by": ":device", "desktop": 3}),
    (
        "a `when` that switches on an option",
        "parts.label.when",
        {"by": "emphasis", "normal": True, "strong": False},
    ),
    (
        "a switch by a name that is no marked name",
        "parts.label.x",
        {"by": "::device", "desktop": "=pad"},
    ),
]


@pytest.mark.parametrize(
    ("case", "path", "value"), REFUSED_BY_SIZE, ids=[case for case, _, _ in REFUSED_BY_SIZE]
)
def test_the_schema_refuses_a_size_the_engine_refuses(case: str, path: str, value: Any) -> None:
    data = changed(path, value)
    assert problems(data) != [], case
    assert sized_issues(data) != [], case


def repeat(**more: Any) -> dict[str, Any]:
    part = {"repeat": "tags", "draw": "lab/tag", "width": "=:width", "row": {"gap": "=@space.1"}}
    return {**part, **more}


@pytest.mark.parametrize(
    ("case", "part"),
    [
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
        ("an image that shows nothing", {"image": {}, "width": "=:width"}),
        (
            "an image of a produced output and a picture file",
            {"image": {"produced": "text", "file": "logo.png"}, "width": "=:width"},
        ),
        (
            "an image of the content's picture file and the library's",
            {"image": {"content": "text", "file": "logo.png"}, "width": "=:width"},
        ),
        (
            "an image of every source",
            {"image": {"produced": "text", "content": "text", "file": "a.png"}, "width": "=:width"},
        ),
        (
            "an image of a picture role and a picture file",
            {"image": {"role": "picture.logo", "file": "logo.png"}, "width": "=:width"},
        ),
        ("an image of a role that is no path", {"image": {"role": "Logo"}, "width": "=:width"}),
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


# --- a top whose layouts are its pages' forms (#2558) ------------------------------------------


def forms(**layouts: Any) -> dict[str, Any]:
    """The reference instance as a top whose layouts are its pages' forms: `tags` marked
    as holding its pages, no parts of its own, and `layouts`."""
    data = changed("layouts", layouts)
    data["fields"]["properties"]["tags"]["x-pkit-pages"] = True
    data["fields"]["properties"]["tags"]["items"] = {"type": "object"}
    del data["parts"], data["exposes"], data["preferred"]
    return data


DRAWN = {
    "slots": {"head": {"type": "string", "x-pkit-prose": True}},
    "required": ["head"],
    "parts": {"head": {"text": {"content": "head", "style": "type.body"}}},
}


def test_a_top_may_declare_several_layouts_each_with_its_own_drawing() -> None:
    data = forms(cover=DRAWN, slide=DRAWN)
    assert problems(data) == []
    assert engine_issues(data) == []


@pytest.mark.parametrize(
    ("case", "layouts"),
    [
        ("a layout without its drawing", {"cover": DRAWN, "slide": {"slots": DRAWN["slots"]}}),
        ("a slot named `layout`", {"cover": {**DRAWN, "slots": {"layout": {}}, "required": []}}),
        ("a slot named as a reserved key", {"cover": {**DRAWN, "slots": {"use": {}}}}),
        (
            "a slot that holds pages",
            {"cover": {**DRAWN, "slots": {**DRAWN["slots"], "more": {"x-pkit-pages": True}}}},
        ),
        ("a slot of format 1's shape", {"cover": {**DRAWN, "slots": {"head": {"pages": True}}}}),
        ("a required slot of format 1", {"cover": {"slots": {}, "required": ["head"]}}),
    ],
    ids=lambda value: value if isinstance(value, str) else "",
)
def test_the_schema_refuses_a_page_form_the_engine_refuses(
    case: str, layouts: dict[str, Any]
) -> None:
    data = forms(**layouts)
    assert problems(data) != [], case
    assert engine_issues(data) != [], case


# --- a pattern's lists (#2560) -----------------------------------------------------------------

SPAN = {"words": ["narrow", "wide"], "shares": {"narrow": 1, "wide": 2}}


def listing(sizes: str = "own", **lists: Any) -> dict[str, Any]:
    """The reference instance as a pattern that repeats over its list `tags` in a row of
    `sizes`, with a field `kind` and the fields of its lists `lists`."""
    data = changed("parts.tags", repeat(row={"sizes": sizes}))
    data["fields"]["properties"]["tags"]["items"] = {"type": "object"}
    data["fields"]["properties"]["kind"] = {"type": "object"}
    data["lists"] = lists
    return data


def test_a_pattern_declares_a_component_field_and_arrangement_fields_for_a_list() -> None:
    data = listing("shares", tags={"component": "kind", "arrangement": {"span": SPAN}})
    assert problems(data) == []
    assert engine_issues(data) == []


@pytest.mark.parametrize(
    ("case", "entry"),
    [
        ("a key the entry does not take", {"draw": "lab/tag"}),
        ("a component field that is no name", {"component": "Kind"}),
        ("an arrangement field of no words", {"arrangement": {"span": {"words": []}}}),
        ("a word twice", {"arrangement": {"span": {"words": ["wide", "wide"]}}}),
        ("the switch's key as a word", {"arrangement": {"span": {"words": ["by"]}}}),
        ("a reserved key's name", {"arrangement": {"state": {"words": ["on"]}}}),
        ("a key an arrangement field does not take", {"arrangement": {"span": {**SPAN, "x": 1}}}),
        (
            "a share of zero",
            {"arrangement": {"span": {**SPAN, "shares": {"narrow": 0, "wide": 1}}}},
        ),
        (
            "a share that is no number",
            {"arrangement": {"span": {**SPAN, "shares": {"narrow": "1", "wide": 2}}}},
        ),
    ],
    ids=lambda value: value if isinstance(value, str) else "",
)
def test_the_schema_refuses_a_lists_fields_the_engine_refuses(
    case: str, entry: dict[str, Any]
) -> None:
    data = listing(tags=entry)
    assert problems(data) != [], case
    assert engine_issues(data) != [], case


# --- ties (#2561) ------------------------------------------------------------------------------


def tying(**lists: Any) -> dict[str, Any]:
    """The reference instance as a pattern that draws each tie of its list `links` with
    `lab/arrow`, between the end fields its `lists` gives, `from` and `to` by default."""
    data = copy.deepcopy(reference())
    data["fields"]["properties"]["links"] = {"type": "array", "items": {"type": "object"}}
    data["parts"]["links"] = {"repeat": "links", "draw": "lab/arrow"}
    data["lists"] = lists or {"links": {"ends": ["from", "to"]}}
    return data


def arrow(**line: Any) -> dict[str, Any]:
    """A component that takes ends and connects them, its line's part changed by `line`."""
    part = {"line": {"stroke": "line", "marker-end": "arrow"}, "connect": "corners", **line}
    return {
        "pkit_schema": "visual-communication:component",
        "schema_version": 1,
        "status": "experimental",
        "about": "An arrow between two items.",
        "ends": True,
        "parts": {"l": {k: v for k, v in part.items() if v is not ...}},
    }


def test_a_pattern_declares_a_list_of_ties_and_a_component_takes_ends() -> None:
    assert problems(tying()) == []
    assert engine_issues(tying()) == []
    assert problems(arrow()) == []
    assert engine_issues(arrow()) == []
    switched = {**arrow(connect={"by": "shape", "flat": "straight", "bent": "corners"})}
    switched["options"] = {"shape": ["flat", "bent"]}
    assert problems(switched) == []
    assert engine_issues(switched) == []


def test_a_list_of_ties_is_arranged_by_neither_operator_and_any_other_list_by_one() -> None:
    """Whether a list holds ties crosses keys, so the engine alone refuses a list that is
    arranged by neither operator and holds no ties."""
    neither = changed("parts.extra", {k: v for k, v in repeat().items() if k != "row"})
    assert problems(neither) == []
    assert engine_issues(neither) != []


@pytest.mark.parametrize(
    ("case", "data"),
    [
        ("`ends` other than true", {**arrow(), "ends": False}),
        ("one end field", tying(links={"ends": ["from"]})),
        ("three end fields", tying(links={"ends": ["from", "to", "via"]})),
        ("an end field twice", tying(links={"ends": ["from", "from"]})),
        ("an end field that is no name", tying(links={"ends": ["from", "To"]})),
        ("an end field with a reserved key's name", tying(links={"ends": ["from", "use"]})),
        ("a connector that gives an end of its own", arrow(x1="=0")),
        ("a connector of a word it does not take", arrow(connect="bent")),
        (
            "an arrowhead of a word it does not take",
            arrow(line={"stroke": "line", "marker-end": "dot"}),
        ),
        ("a line with neither its ends nor `connect`", arrow(connect=...)),
    ],
    ids=lambda value: value if isinstance(value, str) else "",
)
def test_the_schema_refuses_ties_the_engine_refuses(case: str, data: dict[str, Any]) -> None:
    assert problems(data) != [], case
    assert engine_issues(data) != [], case


def test_a_layout_that_draws_a_page_declares_a_list_of_ties_among_its_slots() -> None:
    board = {
        "slots": {"steps": {"type": "array"}, "links": {"type": "array"}},
        "lists": {"links": {"ends": ["from", "to"]}},
        "parts": {
            "steps": {"repeat": "steps", "draw": "lab/tag", "row": {}},
            "links": {"repeat": "links", "draw": "lab/arrow"},
        },
    }
    assert problems(forms(board=board)) == []
    assert engine_issues(forms(board=board)) == []
    # A layout of format 1, which draws no page, takes no `lists`.
    lists = {"slots": {"text": {"pages": True}}, "lists": {"text": {"ends": ["from", "to"]}}}
    assert problems(changed("layouts", {"frame": lists})) != []
