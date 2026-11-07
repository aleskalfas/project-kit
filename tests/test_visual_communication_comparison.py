"""The release's comparison of two versions of one library (visual-communication DEC-003
points 6 and 7, DEC-004 point 5, DEC-008 to DEC-013): each break and addition it names,
the segment it finds, and what it refuses to compare.

Each test builds a location in its own folder that holds both versions, and the shipped
foundations they build on, and reads each version in full (`full_read.read`) before it
compares them. A component library `parts` carries one component of each shape the records
name: a pattern of fields, options, states, an exposed part, a list and runs; a pattern of
ties and the component that draws them; a top whose layouts are its pages' forms; a top of
one layout; a deprecated component; and two experimental ones. For each record, a change it
names as a break is found as one, and a change it names as none is not.
"""

from __future__ import annotations

import copy
import json
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

import pytest

from tests.in_process import load
from tests.visual_communication_project import (
    FOUNDATIONS,
    TEST_BRAND,
    add_library,
    bound,
    copy_library,
    project,
    write,
    yaml_text,
)

comparison, full_read, libraries, reading = load(
    "visual-communication", "comparison", "full_read", "libraries", "reading"
)

LOCATION = "visual"

#: A change made to a copy of a library's data, in place.
Change = Callable[[Any], Any]

#: A stable pattern: its fields, one of them of runs, its options, a state, an exposed
#: part, and a list whose items name their component and carry an arrangement field. It
#: paints and spaces with the library's own roles.
CARD = bound(
    "component",
    status="stable",
    about="A card: its title, a note in two styles, and its tags.",
    fields={
        "type": "object",
        "required": ["title"],
        "properties": {
            "title": {"type": "string"},
            "note": {"type": "string", "x-pkit-runs": ["plain", "strong"]},
            "count": {"type": ["number", "null"]},
            "tags": {"type": "array", "items": {"type": "object"}},
            "tag": {"type": "object"},
        },
    },
    options={"tone": ["quiet", "loud"], "at": {"item": "tags"}},
    states={"done": {"colour": "green"}},
    exposes=["title"],
    lists={"tags": {"component": "tag", "arrangement": {"span": {"words": ["narrow", "wide"]}}}},
    parts={
        "back": {"box": {"fill": "parts.paper"}, "width": "=:width", "height": "=:height"},
        "title": {
            "text": {"content": "title", "style": "type.heading", "fill": "parts.ink"},
            "width": "=:width",
        },
        "note": {
            "when": "note",
            "text": {
                "content": "note",
                "style": {"by": "note", "plain": "type.body", "strong": "type.heading"},
                "fill": "text-secondary",
            },
            "y": "=title.bottom",
            "width": "=:width",
        },
        "tags": {
            "repeat": "tags",
            "draw": "parts/tag",
            "y": "=note.bottom",
            "width": "=:width",
            "row": {"gap": "=@parts.gap"},
        },
    },
    preferred={"width": "=@size.figure", "height": "=tags.bottom"},
)

#: A stable pattern of ties: its nodes, and the links between them, each a tie.
DIAGRAM = bound(
    "component",
    status="stable",
    about="Nodes, and the links between them.",
    fields={
        "type": "object",
        "properties": {
            "nodes": {"type": "array", "items": {"type": "object"}},
            "links": {"type": "array", "items": {"type": "object"}},
            "kind": {"type": "object"},
        },
    },
    lists={"links": {"ends": ["from", "to"]}},
    parts={
        "nodes": {
            "repeat": "nodes",
            "draw": "parts/tag",
            "width": "=:width",
            "row": {"gap": "=@space.2"},
        },
        "links": {"repeat": "links", "draw": "parts/arrow"},
    },
)

#: A stable component that takes ends, a tie's connector.
ARROW = bound(
    "component",
    status="stable",
    about="An arrow from a tie's start to its end.",
    ends=True,
    parts={"line": {"line": {"stroke": "line", "marker-end": "arrow"}, "connect": "straight"}},
)

#: A stable top whose layouts are its pages' forms.
SLIDES = bound(
    "component",
    status="stable",
    about="Slides, each in a layout of its own.",
    fields={
        "type": "object",
        "required": ["slides"],
        "properties": {
            "slides": {"type": "array", "items": {"type": "object"}, "x-pkit-pages": True}
        },
    },
    layouts={
        "cover": {
            "slots": {"title": {"type": "string"}, "subtitle": {"type": "string"}},
            "required": ["title"],
            "parts": {
                "title": {
                    "text": {"content": "title", "style": "type.heading", "fill": "text-primary"},
                    "width": "=:width",
                }
            },
        },
        "points": {
            "slots": {"title": {"type": "string"}, "points": {"type": "array"}},
            "required": ["title"],
            "parts": {
                "title": {
                    "text": {"content": "title", "style": "type.heading", "fill": "text-primary"},
                    "width": "=:width",
                },
                "points": {
                    "repeat": "points",
                    "draw": "parts/tag",
                    "y": "=title.bottom",
                    "width": "=:width",
                    "column": {},
                },
            },
        },
    },
    preferred={"width": "=@size.slide", "height": "=@size.slide * 9 / 16"},
)

#: A stable top of one layout, a page alone.
FRAME = bound(
    "component",
    status="stable",
    about="A frame: its body, and a caption below it.",
    fields={
        "type": "object",
        "properties": {"body": {"type": "object"}, "caption": {"type": "string"}},
    },
    layouts={"frame": {"slots": {"body": {}, "caption": {}}}},
    parts={
        "body": {"slot": "body", "width": "=:width"},
        "caption": {
            "when": "caption",
            "text": {"content": "caption", "style": "type.body", "fill": "text-secondary"},
            "y": "=body.bottom",
            "width": "=:width",
        },
    },
    preferred={"width": "=@size.figure", "height": "=caption.bottom"},
)

#: A deprecated component.
OLD = bound(
    "component",
    status="deprecated",
    about="A box, replaced by the card.",
    parts={"box": {"box": {"fill": "surface"}, "width": "=:width", "height": "=:height"}},
)

#: An experimental component, the only one that reads the library's role `parts.glow`.
SKETCH = bound(
    "component",
    status="experimental",
    about="A glowing box, small or large.",
    options={"size": ["small", "large"]},
    parts={"box": {"box": {"fill": "parts.glow"}, "width": "=:width", "height": "=:height"}},
)

#: An experimental component the patterns draw their items with.
TAG = bound(
    "component",
    status="experimental",
    about="A tag.",
    parts={"box": {"box": {"fill": "surface"}, "width": "=:width", "height": "=:height"}},
)

#: The library's own roles: its ink, paper and gap end their chains at shared roles; its
#: glow has no default, and only an experimental component reads it.
ROLES = {
    "parts.ink": {"type": "color", "default": "{text-primary}"},
    "parts.paper": {"type": "color", "default": "{background}"},
    "parts.gap": {"type": "dimension", "default": "{space.2}"},
    "parts.glow": {"type": "color"},
}
PAIRS = [{"text": "parts.ink", "under": "parts.paper", "level": "text"}]

#: The library `parts` at its earlier version, from which each test's later one is changed.
PARTS: dict[str, Any] = {
    "components": {
        "card": CARD,
        "diagram": DIAGRAM,
        "arrow": ARROW,
        "slides": SLIDES,
        "frame": FRAME,
        "old": OLD,
        "sketch": SKETCH,
        "tag": TAG,
    },
    "roles": ROLES,
    "pairs": PAIRS,
    "builds_on": {"foundations": 1},
}


def write_parts(root: Path, version: str, spec: Mapping[str, Any]) -> Path:
    """A version of the library `parts` written from `spec`: its components, roles and
    pairs, and the libraries it builds on."""
    folder = add_library(root, "parts", version, builds_on=spec["builds_on"])
    for name, data in spec["components"].items():
        write(folder / "components" / f"{name}.yaml", yaml_text(data))
    if spec["roles"]:
        declared = {"roles": spec["roles"], **({"pairs": spec["pairs"]} if spec["pairs"] else {})}
        write(folder / "roles.yaml", yaml_text(bound("roles", **declared)))
    return folder


def foundations(root: Path, version: str = "1.0.0", change: Change | None = None) -> Path:
    """The shipped foundations, copied at `version`, their `roles.yaml` changed by `change`."""
    folder = copy_library(root, FOUNDATIONS, "foundations", version)
    edit(folder / "library.yaml", lambda data: data.update(version=version))
    if change is not None:
        edit(folder / "roles.yaml", change)
    return folder


def edit(path: Path, change: Change) -> None:
    """A YAML file, read, changed by `change` in place, and written again."""
    data = reading.read_yaml(path)
    change(data)
    write(path, yaml_text(data))


def compared(root: Path, name: str, earlier: str, later: str) -> Any:
    """The comparison of two versions of `name` the location at `root` holds."""
    held = libraries.Held(root, LOCATION)
    return comparison.compare(
        full_read.read(held, name, libraries.Version.parse(earlier)),
        full_read.read(held, name, libraries.Version.parse(later)),
    )


def compared_parts(tmp: Path, change: Change, later: str = "1.1.0") -> Any:
    """`parts` 1.0.0 compared with the version `later`, changed by `change`, in a location
    that holds the foundations' first two majors."""
    root = project(tmp)
    foundations(root)
    foundations(root, "2.0.0")
    spec = copy.deepcopy(PARTS)
    change(spec)
    write_parts(root, "1.0.0", PARTS)
    write_parts(root, later, spec)
    return compared(root, "parts", "1.0.0", later)


def said(changes: Any) -> list[str]:
    return [str(change) for change in changes]


# --- the library's components, its roles and its pairs -----------------------------------------


def card(spec: Any) -> Any:
    return spec["components"]["card"]


def fields_of(spec: Any, component: str = "card") -> Any:
    return spec["components"][component]["fields"]["properties"]


def slots_of(spec: Any, layout: str = "cover") -> Any:
    return spec["components"]["slides"]["layouts"][layout]["slots"]


def put(target: Any, key: str, value: Any) -> None:
    target[key] = value


def new_cover_slot(required: bool) -> Change:
    def change(spec: Any) -> None:
        cover = spec["components"]["slides"]["layouts"]["cover"]
        cover["slots"]["date"] = {"type": "string"}
        if required:
            cover["required"].append("date")

    return change


def as_one_layout(spec: Any) -> None:
    """The slides, no longer a top whose layouts are its pages' forms: one layout, whose
    slot of pages holds them."""
    slides = spec["components"]["slides"]
    del slides["fields"]["properties"]["slides"]["x-pkit-pages"]
    slides["layouts"] = {"deck": {"slots": {"slides": {"pages": True}}}}
    slides["parts"] = {"slides": {"slot": "slides", "width": "=:width"}}


def new_list_of_ties(spec: Any) -> None:
    diagram = spec["components"]["diagram"]
    diagram["fields"]["properties"]["routes"] = {"type": "array", "items": {"type": "object"}}
    diagram["lists"]["routes"] = {"ends": ["from", "to"]}
    diagram["parts"]["routes"] = {"repeat": "routes", "draw": "parts/arrow"}


def new_role(default: str | None) -> Change:
    """A new role of the library, which the card's back strokes with."""

    def change(spec: Any) -> None:
        spec["roles"]["parts.edge"] = {"type": "color", **({"default": default} if default else {})}
        card(spec)["parts"]["back"]["box"]["stroke"] = "parts.edge"

    return change


#: Each change, the breaks the comparison names for it, and an addition among those it
#: names, or None.
CASES: dict[str, tuple[Change, list[str], str | None]] = {
    # DEC-003 point 6: a component's names, and what each means.
    "a field removed": (
        lambda s: fields_of(s).pop("count"),
        ["`parts/card`, field `count`: is removed (DEC-003 point 6)"],
        None,
    ),
    "a field narrowed": (
        lambda s: fields_of(s)["count"].update(type="number"),
        ["`parts/card`, field `count`: no longer takes `null` (DEC-003 point 6)"],
        None,
    ),
    "a field that becomes required": (
        lambda s: card(s)["fields"]["required"].append("note"),
        ["`parts/card`, field `note`: is required, where it was optional (DEC-009 point 7)"],
        None,
    ),
    "a new required field": (
        lambda s: (
            fields_of(s).update(kicker={"type": "string"}),
            card(s)["fields"]["required"].append("kicker"),
        ),
        ["`parts/card`, field `kicker`: is new, and required (DEC-009 point 7)"],
        None,
    ),
    "a new optional field": (
        lambda s: fields_of(s).update(kicker={"type": "string"}),
        [],
        "`parts/card`, field `kicker`: is new (DEC-009 point 7)",
    ),
    "a field's description": (
        lambda s: fields_of(s)["title"].update(description="What the card says."),
        [],
        None,
    ),
    "an option removed": (
        lambda s: card(s)["options"].pop("tone"),
        ["`parts/card`, option `tone`: is removed (DEC-003 point 6)"],
        None,
    ),
    "an option's word removed": (
        lambda s: put(card(s)["options"], "tone", ["quiet"]),
        ["`parts/card`, option `tone`, word `loud`: is removed (DEC-003 point 6)"],
        None,
    ),
    "an option that names another thing": (
        lambda s: put(card(s)["options"], "at", {"item": "tags", "point": True}),
        [
            "`parts/card`, option `at`: names an item of `tags`, and its point, where it "
            "named an item of `tags` (DEC-003 point 6)"
        ],
        None,
    ),
    "a new option": (
        lambda s: put(card(s)["options"], "edge", ["none", "thin"]),
        [],
        "`parts/card`, option `edge`: is new (DEC-009 point 7)",
    ),
    "a new word": (
        lambda s: put(card(s)["options"], "tone", ["quiet", "loud", "bold"]),
        [],
        "`parts/card`, option `tone`, word `bold`: is new (DEC-009 point 7)",
    ),
    "an option's default": (
        lambda s: put(card(s)["options"], "tone", ["loud", "quiet"]),
        [],
        None,
    ),
    "a state removed": (
        lambda s: put(card(s), "states", {}),
        ["`parts/card`, state `done`: is removed (DEC-003 point 6)"],
        None,
    ),
    "a new state": (
        lambda s: card(s)["states"].update(late={"colour": "red"}),
        [],
        "`parts/card`, state `late`: is new (DEC-003 point 1)",
    ),
    "a state's colour": (
        lambda s: put(card(s)["states"], "done", {"colour": "blue"}),
        [],
        None,
    ),
    "an exposed part removed": (
        lambda s: put(card(s), "exposes", []),
        ["`parts/card`, exposed part `title`: is removed (DEC-003 point 6, DEC-005 point 3)"],
        None,
    ),
    "a new exposed part": (
        lambda s: put(card(s), "exposes", ["title", "back"]),
        [],
        "`parts/card`, exposed part `back`: is new (DEC-009 point 7)",
    ),
    "a part's look": (
        lambda s: put(card(s)["parts"]["back"]["box"], "fill", "surface"),
        [],
        None,
    ),
    "a library it builds on at a new major": (
        lambda s: put(s, "builds_on", {"foundations": 2}),
        ["`parts`, builds on `foundations`: major 2, where it built on major 1 (DEC-003 point 6)"],
        None,
    ),
    # DEC-003 point 7: what each status promises.
    "a deprecated component removed": (
        lambda s: s["components"].pop("old"),
        ["`parts/old`: is removed, where it was deprecated (DEC-003 point 7)"],
        None,
    ),
    "a stable component marked experimental": (
        lambda s: put(card(s), "status", "experimental"),
        ["`parts/card`: is marked experimental, where it was stable (DEC-003 point 7)"],
        None,
    ),
    "a stable component marked deprecated": (
        lambda s: put(card(s), "status", "deprecated"),
        [],
        None,
    ),
    "an experimental component's option removed": (
        lambda s: s["components"]["sketch"].pop("options"),
        [],
        None,
    ),
    "an experimental component removed": (
        lambda s: s["components"].pop("sketch"),
        [],
        None,
    ),
    "a new component": (
        lambda s: s["components"].update(badge=TAG),
        [],
        "`parts/badge`: is new (DEC-003 point 1)",
    ),
    # DEC-009 point 7: a top's layouts and slots.
    "a layout removed": (
        lambda s: s["components"]["slides"]["layouts"].pop("points"),
        ["`parts/slides`, layout `points`: is removed (DEC-003 point 6)"],
        None,
    ),
    "a new layout": (
        lambda s: s["components"]["slides"]["layouts"].update(
            quote=copy.deepcopy(SLIDES["layouts"]["cover"])
        ),
        [],
        "`parts/slides`, layout `quote`: is new (DEC-009 point 7)",
    ),
    "a slot removed": (
        lambda s: slots_of(s).pop("subtitle"),
        ["`parts/slides`, layout `cover`, slot `subtitle`: is removed (DEC-003 point 6)"],
        None,
    ),
    "a new required slot": (
        new_cover_slot(required=True),
        ["`parts/slides`, layout `cover`, slot `date`: is new, and required (DEC-009 point 7)"],
        None,
    ),
    "a new optional slot": (
        new_cover_slot(required=False),
        [],
        "`parts/slides`, layout `cover`, slot `date`: is new (DEC-009 point 7)",
    ),
    "a slot of one layout removed": (
        lambda s: s["components"]["frame"]["layouts"]["frame"]["slots"].pop("caption"),
        ["`parts/frame`, layout `frame`, slot `caption`: is removed (DEC-003 point 6)"],
        None,
    ),
    "a slot that comes to hold pages": (
        lambda s: put(
            s["components"]["frame"]["layouts"]["frame"]["slots"], "body", {"pages": True}
        ),
        ["`parts/frame`, layout `frame`, slot `body`: comes to hold pages (DEC-003 point 6)"],
        None,
    ),
    # DEC-010 point 7: a list's component field, its arrangement fields, a top's pages.
    "a field it held marked as a list's component field": (
        lambda s: put(s["components"]["diagram"]["lists"], "nodes", {"component": "kind"}),
        [
            "`parts/diagram`, list `nodes`: marks the field `kind` it held as its component "
            "field (DEC-010 point 7)"
        ],
        None,
    ),
    "a new component field": (
        lambda s: (
            fields_of(s, "diagram").update(shape={"type": "object"}),
            put(s["components"]["diagram"]["lists"], "nodes", {"component": "shape"}),
        ),
        [],
        "`parts/diagram`, list `nodes`: names its component in the new field `shape` "
        "(DEC-010 point 7)",
    ),
    "a list's component field removed": (
        lambda s: card(s)["lists"]["tags"].pop("component"),
        [
            "`parts/card`, list `tags`: no longer names its component in the field `tag` "
            "(DEC-010 point 7)"
        ],
        None,
    ),
    "an arrangement field's word removed": (
        lambda s: put(card(s)["lists"]["tags"]["arrangement"]["span"], "words", ["narrow"]),
        [
            "`parts/card`, list `tags`, arrangement field `span`, word `wide`: is removed "
            "(DEC-010 point 7)"
        ],
        None,
    ),
    "a new arrangement field": (
        lambda s: card(s)["lists"]["tags"]["arrangement"].update(lean={"words": ["start", "end"]}),
        [],
        "`parts/card`, list `tags`, arrangement field `lean`: is new (DEC-010 point 7)",
    ),
    "an arrangement field's new word": (
        lambda s: put(
            card(s)["lists"]["tags"]["arrangement"]["span"], "words", ["narrow", "wide", "full"]
        ),
        [],
        "`parts/card`, list `tags`, arrangement field `span`, word `full`: is new "
        "(DEC-010 point 7)",
    ),
    "an arrangement field's default": (
        lambda s: put(card(s)["lists"]["tags"]["arrangement"]["span"], "words", ["wide", "narrow"]),
        [],
        None,
    ),
    "a top that ceases to make its layouts its pages' forms": (
        as_one_layout,
        ["`parts/slides`: ceases to make its layouts its pages' forms (DEC-010 point 7)"],
        None,
    ),
    # DEC-011 point 6: end fields, and a component that takes ends.
    "end fields declared for a list it held": (
        lambda s: put(s["components"]["diagram"]["lists"], "nodes", {"ends": ["from", "to"]}),
        [
            "`parts/diagram`, list `nodes`: declares the end fields `from` and `to` for a list "
            "it held (DEC-011 point 6)"
        ],
        None,
    ),
    "end fields swapped": (
        lambda s: put(s["components"]["diagram"]["lists"]["links"], "ends", ["to", "from"]),
        [
            "`parts/diagram`, list `links`: swaps its end fields: each tie starts at `to`, "
            "where it started at `from` (DEC-011 point 6)"
        ],
        None,
    ),
    "an end field renamed": (
        lambda s: put(s["components"]["diagram"]["lists"]["links"], "ends", ["from", "target"]),
        ["`parts/diagram`, list `links`, end field `to`: is removed (DEC-011 point 6)"],
        None,
    ),
    "a component that ceases to take ends": (
        lambda s: s["components"]["arrow"].pop("ends"),
        ["`parts/arrow`: ceases to take ends (DEC-011 point 6)"],
        None,
    ),
    "a new list of ties": (
        new_list_of_ties,
        [],
        "`parts/diagram`, list `routes`: is a new list of ties (DEC-011 point 6)",
    ),
    # DEC-012 point 6: fields of runs.
    "a field that ceases to take runs": (
        lambda s: fields_of(s)["note"].pop("x-pkit-runs"),
        ["`parts/card`, field `note`: ceases to take runs (DEC-012 point 6)"],
        None,
    ),
    "a change of the first run style": (
        lambda s: put(fields_of(s)["note"], "x-pkit-runs", ["strong", "plain"]),
        [
            "`parts/card`, field `note`: takes runs of `strong` first, where it took `plain` "
            "(DEC-012 point 6)"
        ],
        None,
    ),
    "a run style removed": (
        lambda s: put(fields_of(s)["note"], "x-pkit-runs", ["plain"]),
        ["`parts/card`, field `note`, run style `strong`: is removed (DEC-012 point 6)"],
        None,
    ),
    "a new run style after the first": (
        lambda s: put(fields_of(s)["note"], "x-pkit-runs", ["plain", "strong", "faint"]),
        [],
        "`parts/card`, field `note`, run style `faint`: is new (DEC-012 point 6)",
    ),
    "a field that comes to take runs": (
        lambda s: put(fields_of(s)["title"], "x-pkit-runs", ["plain"]),
        [],
        "`parts/card`, field `title`: comes to take runs (DEC-012 point 6)",
    ),
    "a slot that comes to take runs": (
        lambda s: put(slots_of(s)["title"], "x-pkit-runs", ["plain"]),
        [],
        "`parts/slides`, layout `cover`, slot `title`: comes to take runs (DEC-012 point 6)",
    ),
    # DEC-008 point 7: the library's own roles, and its pairs.
    "a role a stable component reads removed": (
        lambda s: s["roles"].pop("parts.gap"),
        ["role `parts.gap`: is removed (DEC-003 point 6, DEC-008 point 7)"],
        None,
    ),
    "a role whose chain no longer ends at a shared role": (
        lambda s: s["roles"]["parts.ink"].pop("default"),
        [
            "role `parts.ink`: no longer ends its chain of defaults at a shared role "
            "(DEC-008 point 7)"
        ],
        None,
    ),
    "a default pointed along a chain that ends at a shared role": (
        lambda s: put(s["roles"]["parts.ink"], "default", "{text-secondary}"),
        [],
        None,
    ),
    "a new role a stable component reads, with no default": (
        new_role(None),
        [
            "role `parts.edge`: is new, read by a stable or deprecated component, and its "
            "chain of defaults ends at no shared role (DEC-008 point 7)"
        ],
        None,
    ),
    "a new role whose chain ends at a shared role": (
        new_role("{line}"),
        [],
        "role `parts.edge`: is new (DEC-008 point 7)",
    ),
    "a role only an experimental component reads removed": (
        lambda s: s["roles"].pop("parts.glow"),
        [],
        None,
    ),
    "a pair removed": (
        lambda s: put(s, "pairs", []),
        ["pair `parts.ink` on `parts.paper`: is removed (DEC-008 point 7)"],
        None,
    ),
    "a pair's level lowered": (
        lambda s: put(s["pairs"][0], "level", "large-text"),
        [
            "pair `parts.ink` on `parts.paper`: is at `large-text`, where it was at `text` "
            "(DEC-008 point 7)"
        ],
        None,
    ),
    "a pair written the other way round": (
        lambda s: put(s, "pairs", [{"text": "parts.paper", "under": "parts.ink", "level": "text"}]),
        [],
        None,
    ),
    "a new pair": (
        lambda s: s["pairs"].append(
            {"text": "parts.glow", "under": "parts.paper", "level": "marks"}
        ),
        [],
        "pair `parts.glow` on `parts.paper`: is new (DEC-008 point 7)",
    ),
}


@pytest.mark.parametrize("change,breaks,addition", CASES.values(), ids=CASES.keys())
def test_each_change_of_a_component_library_is_named_as_its_record_counts_it(
    tmp_path: Path, change: Change, breaks: list[str], addition: str | None
) -> None:
    found = compared_parts(tmp_path, change)

    assert said(found.breaks) == breaks
    if addition is not None:
        assert addition in said(found.additions)


def test_a_version_that_changes_nothing_needs_a_patch(tmp_path: Path) -> None:
    found = compared_parts(tmp_path, lambda spec: None)

    assert (found.breaks, found.additions, found.segment, found.allowed) == ((), (), "patch", True)


def test_a_stable_field_removed_in_a_minor_is_refused_and_in_a_major_allowed(
    tmp_path: Path,
) -> None:
    def removed(spec: Any) -> None:
        fields_of(spec).pop("count")

    minor = compared_parts(tmp_path / "minor", removed)
    major = compared_parts(tmp_path / "major", removed, later="2.0.0")

    assert (minor.segment, minor.allowed) == ("major", False)
    assert minor.lines() == [
        "parts 1.0.0 to 1.1.0: the number needs a major, and 1.1.0 keeps major 1",
        "  break: `parts/card`, field `count`: is removed (DEC-003 point 6)",
    ]
    assert said(major.breaks) == said(minor.breaks)
    assert (major.segment, major.allowed) == ("major", True)
    assert major.lines()[0] == "parts 1.0.0 to 2.0.0: the number needs a major"


def test_an_addition_alone_needs_at_least_a_minor(tmp_path: Path) -> None:
    found = compared_parts(tmp_path, lambda spec: spec["components"].update(badge=TAG))

    assert (found.segment, found.allowed) == ("minor", True)
    assert found.lines() == [
        "parts 1.0.0 to 1.1.0: the number needs at least a minor",
        "  addition: `parts/badge`: is new (DEC-003 point 1)",
    ]


def test_two_libraries_and_a_version_not_read_with_its_bases_are_not_compared(
    tmp_path: Path,
) -> None:
    root = project(tmp_path)
    foundations(root)
    write_parts(root, "1.0.0", PARTS)
    write_parts(root, "1.1.0", {**PARTS, "builds_on": {"foundations": 2}})
    held = libraries.Held(root, LOCATION)
    version = libraries.Version.parse

    with pytest.raises(comparison.ComparisonError, match="versions of two libraries"):
        comparison.compare(
            full_read.read(held, "parts", version("1.0.0")),
            full_read.read(held, "foundations", version("1.0.0")),
        )
    with pytest.raises(comparison.ComparisonError, match=r"parts@1\.1\.0 cannot be compared"):
        compared(root, "parts", "1.0.0", "1.1.0")


# --- the foundations ----------------------------------------------------------------------------


def compared_foundations(tmp: Path, later: Change, earlier: Change | None = None) -> Any:
    """The foundations 1.0.0, changed by `earlier`, compared with 1.1.0, changed by
    `later`."""
    root = project(tmp)
    foundations(root, "1.0.0", earlier)
    foundations(root, "1.1.0", later)
    return compared(root, "foundations", "1.0.0", "1.1.0")


def roles(data: Any) -> Any:
    return data["roles"]


def axis(name: str) -> Callable[[Any], Any]:
    return lambda data: data["axes"][name]


def dim(data: Any) -> None:
    """A third mode of the colour scheme."""
    axis("colour-scheme")(data)["modes"].append("dim")


FOUNDATIONS_CASES: dict[str, tuple[Change, Change | None, list[str], str | None]] = {
    "a new shared role with no default": (
        lambda d: roles(d).update({"space.5": {"type": "dimension"}}),
        None,
        ["shared role `space.5`: is new, with no default (DEC-004 point 5)"],
        None,
    ),
    "a new shared role with a default": (
        lambda d: roles(d).update({"space.5": {"type": "dimension", "default": "{space.4}"}}),
        None,
        [],
        "shared role `space.5`: is new, with a default (DEC-004 point 5)",
    ),
    "a shared role removed": (
        lambda d: roles(d).pop("line"),
        None,
        ["shared role `line`: is removed (DEC-003 point 6)"],
        None,
    ),
    "a shared role of another type": (
        lambda d: put(roles(d), "stroke.thin", {"type": "number"}),
        None,
        [
            "shared role `stroke.thin`: is of type `number`, where it was `dimension` "
            "(DEC-004 point 5)"
        ],
        None,
    ),
    "a shared role that loses its default": (
        lambda d: roles(d).update({"space.5": {"type": "dimension"}}),
        lambda d: roles(d).update({"space.5": {"type": "dimension", "default": "{space.4}"}}),
        [
            "shared role `space.5`: loses its default, so every brand gives it a value "
            "(DEC-004 points 5 and 7)"
        ],
        None,
    ),
    "a mode removed": (
        lambda d: None,
        dim,
        ["shared axis `colour-scheme`, mode `dim`: is removed (DEC-004 point 5)"],
        None,
    ),
    "a new mode": (
        dim,
        None,
        [],
        "shared axis `colour-scheme`, mode `dim`: is new (DEC-004 point 5)",
    ),
    "an axis's default changed": (
        lambda d: put(axis("colour-scheme")(d), "default", "dark"),
        None,
        [
            "shared axis `colour-scheme`: takes `dark` by default, where it took `light` "
            "(DEC-004 point 5)"
        ],
        None,
    ),
    "a value axis turned into a size axis": (
        lambda d: put(axis("contrast")(d), "kind", "size"),
        None,
        ["shared axis `contrast`: is a size axis, where it was a value axis (DEC-004 point 5)"],
        None,
    ),
    "an axis removed": (
        lambda d: d["axes"].pop("contrast"),
        None,
        ["shared axis `contrast`: is removed (DEC-004 point 5)"],
        None,
    ),
    "a new shared axis": (
        lambda d: d["axes"].update(
            density={"kind": "size", "modes": ["compact", "roomy"], "default": "roomy"}
        ),
        None,
        [],
        "shared axis `density`: is new (DEC-004 point 5)",
    ),
    "a pair's level lowered": (
        lambda d: put(d["pairs"][0], "level", "large-text"),
        None,
        [
            "pair `text-primary` on `background`: is at `large-text`, where it was at `text` "
            "(DEC-008 point 7)"
        ],
        None,
    ),
    "a pair removed": (
        lambda d: d["pairs"].pop(0),
        None,
        ["pair `text-primary` on `background`: is removed (DEC-008 point 7)"],
        None,
    ),
    "a new pair": (
        lambda d: d["pairs"].append({"text": "accent", "under": "surface", "level": "marks"}),
        None,
        [],
        "pair `accent` on `surface`: is new (DEC-008 point 7)",
    ),
    "a colour family removed": (
        lambda d: d["families"].pop("red"),
        None,
        ["colour family `red`: is removed (DEC-003 point 6)"],
        None,
    ),
}


@pytest.mark.parametrize(
    "later,earlier,breaks,addition", FOUNDATIONS_CASES.values(), ids=FOUNDATIONS_CASES.keys()
)
def test_each_change_of_the_foundations_is_named_whatever_reads_it(
    tmp_path: Path,
    later: Change,
    earlier: Change | None,
    breaks: list[str],
    addition: str | None,
) -> None:
    """The foundations' components are all experimental: their shared roles, axes, colour
    families and pairs are compared all the same."""
    found = compared_foundations(tmp_path, later, earlier)

    assert said(found.breaks) == breaks
    if addition is not None:
        assert addition in said(found.additions)


# --- a brand ------------------------------------------------------------------------------------


def brand_location(
    tmp: Path, version: str, foundations_change: Change | None, brand_change: Change | None
) -> Any:
    """A location that holds the foundations, changed by `foundations_change`, and the test
    brand at `version`, its `library.yaml` changed by `brand_change`."""
    root = project(tmp)
    foundations(root, "1.0.0", foundations_change)
    folder = copy_library(root, TEST_BRAND, "test-brand", version)
    edit(folder / "library.yaml", lambda data: data.update(version=version))
    if brand_change is not None:
        edit(folder / "library.yaml", brand_change)
    return libraries.Held(root, LOCATION)


def compared_brand(
    tmp: Path,
    *,
    earlier: tuple[Change | None, Change | None] = (None, None),
    later: tuple[Change | None, Change | None] = (None, None),
) -> Any:
    """The test brand 1.0.0 compared with 1.1.0, each over foundations of its own."""
    was = brand_location(tmp / "earlier", "1.0.0", *earlier)
    now = brand_location(tmp / "later", "1.1.0", *later)
    version = libraries.Version.parse
    return comparison.compare(
        full_read.read(was, "test-brand", version("1.0.0")),
        full_read.read(now, "test-brand", version("1.1.0")),
    )


def poster(data: Any) -> None:
    """A shared role with a default, which every brand exports."""
    roles(data).update({"size.poster": {"type": "dimension", "default": "{size.slide}"}})


def test_a_brands_mode_removed_breaks_it(tmp_path: Path) -> None:
    """The brand varies the colour scheme in a third mode, `dim`, which its later
    foundations no longer hold, nor its Resolver document."""
    was = brand_location(tmp_path / "earlier", "1.0.0", dim, None)
    resolver = (
        was.root / LOCATION / "libraries" / "test-brand" / "1.0.0" / "test-brand.resolver.json"
    )
    document = json.loads(resolver.read_text(encoding="utf-8"))
    document["modifiers"]["colour-scheme"]["contexts"]["dim"] = []
    resolver.write_text(json.dumps(document), encoding="utf-8")
    now = brand_location(tmp_path / "later", "1.1.0", None, None)
    version = libraries.Version.parse

    found = comparison.compare(
        full_read.read(was, "test-brand", version("1.0.0")),
        full_read.read(now, "test-brand", version("1.1.0")),
    )

    assert said(found.breaks) == ["axis `colour-scheme`, mode `dim`: is removed (DEC-004 point 5)"]


def test_a_brands_exported_token_removed_breaks_it_and_a_new_one_is_an_addition(
    tmp_path: Path,
) -> None:
    removed = compared_brand(tmp_path / "removed", earlier=(poster, None))
    added = compared_brand(tmp_path / "added", later=(poster, None))

    assert said(removed.breaks) == ["exported token `size.poster`: is removed (DEC-004 point 5)"]
    assert (said(added.breaks), said(added.additions)) == (
        [],
        ["exported token `size.poster`: is new (DEC-004 point 5)"],
    )


def test_a_role_taken_off_a_bases_open_roles_breaks_it_and_a_newly_opened_one_does_not(
    tmp_path: Path,
) -> None:
    closed = compared_brand(tmp_path / "closed", later=(None, lambda d: put(d, "open", ["accent"])))
    opened = compared_brand(
        tmp_path / "opened", later=(None, lambda d: put(d, "open", ["accent", "space", "line"]))
    )

    assert said(closed.breaks) == [
        f"open role `space.{n}`: is no longer open (DEC-004 point 5)" for n in range(1, 5)
    ]
    assert (said(opened.breaks), said(opened.additions)) == (
        [],
        ["open role `line`: is newly open (DEC-004 point 5)"],
    )


def test_a_brands_changed_value_is_no_break(tmp_path: Path) -> None:
    now = brand_location(tmp_path / "later", "1.1.0", None, None)
    palette = (
        now.root
        / LOCATION
        / "libraries"
        / "test-brand"
        / "1.1.0"
        / "tokens"
        / "palette.tokens.json"
    )
    tokens = json.loads(palette.read_text(encoding="utf-8"))
    tokens["palette"]["white"]["$value"] = {"colorSpace": "srgb", "components": [0.99, 0.99, 0.99]}
    palette.write_text(json.dumps(tokens), encoding="utf-8")
    was = brand_location(tmp_path / "earlier", "1.0.0", None, None)
    version = libraries.Version.parse

    found = comparison.compare(
        full_read.read(was, "test-brand", version("1.0.0")),
        full_read.read(now, "test-brand", version("1.1.0")),
    )

    assert (found.breaks, found.additions) == ((), ())


def device(data: Any) -> None:
    """The size axis `device`, beside the foundations' value axes (DEC-021 point 1)."""
    data["axes"]["device"] = {
        "kind": "size",
        "modes": ["desktop", "tablet", "phone"],
        "default": "desktop",
    }


def vary(held: Any, version: str, axis: str, contexts: Mapping[str, Any] | None) -> None:
    """The test brand at `version` made to vary `axis` by `contexts`, each a list of
    sources, or to leave it out where `contexts` is None."""
    resolver = (
        held.root / LOCATION / "libraries" / "test-brand" / version / "test-brand.resolver.json"
    )
    document = json.loads(resolver.read_text(encoding="utf-8"))
    order = document["resolutionOrder"]
    if contexts is None:
        del document["modifiers"][axis]
        order.remove({"$ref": f"#/modifiers/{axis}"})
    else:
        default = next(iter(contexts))
        if axis not in document["modifiers"]:
            order.append({"$ref": f"#/modifiers/{axis}"})
        document["modifiers"][axis] = {"contexts": dict(contexts), "default": default}
    resolver.write_text(json.dumps(document), encoding="utf-8")


def compared_sizes(tmp: Path, earlier: list[str] | None, later: list[str] | None) -> Any:
    """The test brand 1.0.0 compared with 1.1.0, both over foundations that declare
    `device`, each giving the sizes named, or none where None."""
    was = brand_location(tmp / "earlier", "1.0.0", device, None)
    now = brand_location(tmp / "later", "1.1.0", device, None)
    for held, version, sizes in ((was, "1.0.0", earlier), (now, "1.1.0", later)):
        if sizes is not None:
            vary(held, version, "device", {size: [] for size in sizes})
    version = libraries.Version.parse
    return comparison.compare(
        full_read.read(was, "test-brand", version("1.0.0")),
        full_read.read(now, "test-brand", version("1.1.0")),
    )


def test_a_size_a_brand_comes_to_give_is_an_addition_and_one_it_ceases_to_give_breaks(
    tmp_path: Path,
) -> None:
    came = compared_sizes(tmp_path / "came", None, ["desktop", "phone"])
    more = compared_sizes(tmp_path / "more", ["desktop"], ["desktop", "phone"])
    ceased = compared_sizes(tmp_path / "ceased", ["desktop", "phone"], None)
    fewer = compared_sizes(tmp_path / "fewer", ["desktop", "phone"], ["desktop"])
    none = compared_sizes(tmp_path / "none", None, None)

    assert (said(came.breaks), said(came.additions)) == (
        [],
        ["axis `device`: is new (DEC-004 point 5)"],
    )
    assert (said(more.breaks), said(more.additions)) == (
        [],
        ["axis `device`, mode `phone`: is new (DEC-004 point 5)"],
    )
    assert said(ceased.breaks) == ["axis `device`: is removed (DEC-004 point 5)"]
    assert said(fewer.breaks) == ["axis `device`, mode `phone`: is removed (DEC-004 point 5)"]
    assert (none.breaks, none.additions) == ((), ())


def test_a_value_mode_a_brand_ceases_to_give_is_no_break(tmp_path: Path) -> None:
    """The later version gives the contrast at `standard` alone: `high` takes its values at
    the default, a changed value, and the brand still has the mode."""
    was = brand_location(tmp_path / "earlier", "1.0.0", None, None)
    now = brand_location(tmp_path / "later", "1.1.0", None, None)
    vary(now, "1.1.0", "contrast", {"standard": []})
    version = libraries.Version.parse

    found = comparison.compare(
        full_read.read(was, "test-brand", version("1.0.0")),
        full_read.read(now, "test-brand", version("1.1.0")),
    )

    assert (found.breaks, found.additions) == ((), ())


# --- a shape that follows a size (DEC-021 points 3 and 7) ---------------------------------------

#: The size axis a test adds to its copy of the foundations.
DEVICE = {"kind": "size", "modes": ["desktop", "phone"], "default": "desktop"}


def with_device(data: Any) -> None:
    data["axes"]["device"] = dict(DEVICE)


def following_a_size(spec: Any) -> None:
    """The card's title narrows on a phone, and its tags are drawn on a desktop alone."""
    card(spec)["parts"]["title"]["width"] = {
        "by": ":device",
        "desktop": "=:width",
        "phone": "=:width * 0.5",
    }
    card(spec)["parts"]["tags"]["when"] = {"by": ":device", "desktop": True, "phone": False}


@pytest.mark.parametrize("device", [True, False], ids=["the-axis", "no-axis"])
def test_a_version_read_in_full_reads_a_switch_by_a_size_against_its_foundations(
    tmp_path: Path, device: bool
) -> None:
    """A library checked alone places nothing: it reads the switch against the size axes of
    the foundations it is read with, as a piece does."""
    root = project(tmp_path)
    foundations(root, change=with_device if device else None)
    spec = copy.deepcopy(PARTS)
    following_a_size(spec)
    write_parts(root, "1.0.0", spec)

    read = full_read.read(libraries.Held(root, LOCATION), "parts", libraries.Version.parse("1.0.0"))
    found = [finding for finding in read.findings if finding.code == "size-switch"]

    if device:
        assert found == []
        return
    assert [(f.where, f.library, f.extra) for f in found] == [
        ("parts.title.width", "parts@1.0.0", {"component": "parts/card"}),
        ("parts.tags.when", "parts@1.0.0", {"component": "parts/card"}),
    ]
    assert all("(the size axes: none)" in finding.message for finding in found)


def test_a_shape_that_follows_a_size_changes_how_a_piece_looks_and_needs_a_patch(
    tmp_path: Path,
) -> None:
    root = project(tmp_path)
    foundations(root, change=with_device)
    spec = copy.deepcopy(PARTS)
    following_a_size(spec)
    write_parts(root, "1.0.0", PARTS)
    write_parts(root, "1.1.0", spec)

    found = compared(root, "parts", "1.0.0", "1.1.0")

    assert (found.breaks, found.additions, found.segment) == ((), (), "patch")
