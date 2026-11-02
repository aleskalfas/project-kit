"""The scene visual-communication's engine computes (DEC-005 point 5; #2428).

`compute_scene` draws a piece from its content and the components its libraries hold,
read through an in-memory `Env` (`tests/visual_engine.py`). The piece here is the
foundations' figure holding the test library's steps, whose last step is a callout: a
produced picture with a label at the point the picture exposes.

- the scene's tree: every element's trace id and frame, relative to its parent, rounded
  to 1/100 px; the label at the picture's point, mapped into the image's frame; no
  findings;
- the root's facts, and `to_dict` stable and ordered;
- each property's source, colours kept as role names, and an image holding its
  variants by key and its points;
- a text's record: lines, line height, measured height, font file and hash;
- a missing font, or a character no family measures, refused before layout.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from tests.visual_engine import FAMILY, FONT, draw, env, frame, text, top

CONTENT = {
    "body": {
        "use": "tests/steps",
        "steps": [
            {"id": "plan", "head": "Plan the work"},
            {"id": "build", "head": "Build it, test it and have it reviewed with care"},
            {
                "id": "note",
                "use": "tests/callout",
                "pictures": [{"id": "square", "output": "square"}],
                "label": "Here",
                "at": {"item": "square", "point": "tip"},
            },
        ],
    },
    "caption": "Three steps, the last a picture with a label at its tip.",
}

NOTE = "figure/body/steps[note]"


def figure(content: dict | None = None, **environment: Any) -> Any:
    return draw(CONTENT if content is None else content, use="foundations/figure", **environment)


def test_the_figure_draws_its_steps_and_a_label_at_the_pictures_point() -> None:
    result = figure()

    assert result.findings == []
    assert result.scene.pages == ["figure"]
    # The figure is as wide as its role, the body inset by @space.3 (16) on each side.
    assert frame(result, "figure")[:3] == (0.0, 0.0, 640.0)
    assert frame(result, "figure/body") == (16.0, 16.0, 608.0, frame(result, "figure/body")[3])
    # Three steps share the row's 608 px less two gaps of @space.2 (8) equally.
    assert [
        frame(result, f"figure/body/steps[{step}]")[0] for step in ("plan", "build", "note")
    ] == [
        0.0,
        205.33,
        410.67,
    ]
    assert frame(result, "figure/body/steps[plan]")[2] == 197.33
    # The square picture fills the callout's width; its tip (75, 25 of 100 px) maps into it.
    image = result.scene.find(f"{NOTE}/pictures[square]/image")
    assert image is not None
    assert frame(result, f"{NOTE}/pictures[square]/image")[2:] == (197.33, 197.33)
    assert image.properties["points"] == {"tip": {"x": 148.0, "y": 49.33}}
    # The label stands at the tip, offset by @space.1 (4) across.
    assert frame(result, f"{NOTE}/label")[:2] == (152.0, 49.33)
    # Every step is as tall as the tallest, the callout.
    heights = {frame(result, f"figure/body/steps[{s}]")[3] for s in ("plan", "build", "note")}
    assert heights == {197.33}


def test_every_element_carries_its_trace_in_tree_order() -> None:
    result = figure()

    traces = []

    def walk(element) -> None:
        traces.append(element.id)
        for child in element.children:
            walk(child)

    for child in result.scene.children:
        walk(child)
    assert traces == [
        "figure",
        "figure/background",
        "figure/body",
        "figure/body/steps",
        "figure/body/steps[plan]",
        "figure/body/steps[plan]/box",
        "figure/body/steps[plan]/head",
        "figure/body/steps[build]",
        "figure/body/steps[build]/box",
        "figure/body/steps[build]/head",
        NOTE,
        f"{NOTE}/pictures",
        f"{NOTE}/pictures[square]",
        f"{NOTE}/pictures[square]/image",
        f"{NOTE}/label",
        "figure/caption",
    ]


def test_an_item_without_an_id_is_traced_by_its_place() -> None:
    content = {"body": {"use": "tests/steps", "steps": [{"head": "One"}, {"head": "Two"}]}}

    result = figure(content)

    assert result.scene.find("figure/body/steps#2/head") is not None


def test_the_root_says_what_the_scene_is_and_to_dict_is_stable_and_ordered() -> None:
    first, second = figure().scene.to_dict(), figure().scene.to_dict()

    assert json.dumps(first) == json.dumps(second)
    assert list(first) == ["piece", "lock", "language", "size-key", "seam", "pages", "children"]
    assert (first["piece"], first["language"], first["size-key"], first["seam"]) == (
        "test-piece",
        "en",
        "default",
        1,
    )
    assert list(first["lock"]) == sorted(first["lock"])
    group = first["children"][0]
    assert list(group)[:8] == ["type", "id", "x", "y", "width", "height", "component", "version"]
    assert list(group)[-2:] == ["sources", "children"]
    assert (group["component"], group["version"], group["page"]) == (
        "foundations/figure",
        "1.0.0",
        True,
    )


def test_every_length_is_rounded_to_a_hundredth_of_a_px() -> None:
    def lengths(element: dict):
        for key in ("x", "y", "width", "height"):
            yield element[key]
        for child in element.get("children", []):
            yield from lengths(child)

    for value in lengths(figure().scene.to_dict()["children"][0]):
        assert round(value, 2) == value


def test_each_property_names_its_source() -> None:
    result = figure({**CONTENT, "body": {**CONTENT["body"], "spacing": "wide"}})

    root = result.scene.find("figure")
    head = result.scene.find("figure/body/steps[plan]/head")
    body = result.scene.find("figure/body")
    label = result.scene.find(f"{NOTE}/label")
    item = result.scene.find("figure/body/steps[build]")
    assert root is not None and head is not None and body is not None
    assert label is not None and item is not None
    assert root.sources["width"] == "role:size.figure"
    assert root.sources["height"] == "default:foundations/figure"
    assert head.sources["text"] == "content:body.steps[plan].head"
    assert head.sources["fill"] == "default:tests/card"
    assert head.sources["font-size"] == "role:type.body"
    assert head.sources["x"] == "role:space.2"
    assert head.sources["height"] == "engine"
    assert label.sources["x"] == "default:tests/callout"
    assert item.sources["x"] == "engine"
    assert body.sources["options.spacing"] == "content:body.spacing"
    assert body.properties["options"] == {"spacing": "wide"}
    # A wide spacing doubles the gap: @space.2 * 2.
    assert frame(result, "figure/body/steps[build]")[0] == round((608 - 32) / 3 + 16, 2)


def test_a_text_anchor_the_component_gives_none_of_is_the_engines_default() -> None:
    def anchor(given: dict[str, Any]) -> tuple[str, str]:
        props = {"content": "label", "style": "type.body", **given}
        component = top({"t": {"text": props}}, fields={"label": {"type": "string"}})
        element = draw({"label": "x"}, components={"lab/top": component}).scene.find("top/t")
        assert element is not None
        return element.properties["text-anchor"], element.sources["text-anchor"]

    assert anchor({}) == ("start", "engine")
    assert anchor({"text-anchor": "middle"}) == ("middle", "default:lab/top")


def test_colours_stay_role_names() -> None:
    box = figure().scene.find("figure/body/steps[plan]/box")

    assert box is not None
    assert (box.properties["fill"], box.properties["stroke"]) == ("surface", "line")
    assert box.properties["stroke-width"] == 1.0


def test_an_image_holds_its_variants_by_key_and_its_points() -> None:
    image = figure().scene.find(f"{NOTE}/pictures[square]/image")

    assert image is not None
    assert image.properties["output"] == "square"
    assert image.sources["output"] == "content:body.steps[note].pictures[square].output"
    assert image.properties["variants"] == {
        "colour-scheme.dark": {
            "file": "colour-scheme.dark.png",
            "pixels": {"width": 100, "height": 100},
        },
        "default": {"file": "default.png", "pixels": {"width": 100, "height": 100}},
    }
    assert image.properties["preserveAspectRatio"] == "xMidYMid meet"


def test_a_text_records_its_lines_and_how_it_was_measured() -> None:
    result = figure()
    head = result.scene.find("figure/body/steps[build]/head")

    assert head is not None
    props = head.properties
    assert len(props["lines"]) == 2
    assert " ".join(line["text"] for line in props["lines"]) == props["text"]
    assert all(line["width"] <= props["width"] for line in props["lines"])
    assert props["line-height"] == 22.4
    assert props["measured-height"] == props["height"] == 44.8
    assert props["font-family"] == [FAMILY]
    assert props["measured"] == "file"
    sha256 = text.Face(FAMILY, FONT).sha256
    assert props["fonts"] == [{"family": FAMILY, "file": FONT.name, "sha256": sha256}]
    assert 0 < props["baseline"] < props["line-height"]


def test_a_text_too_long_for_its_width_overflows_as_a_finding() -> None:
    content = {
        "body": {
            "use": "tests/steps",
            "steps": [{"head": "Pneumonoultramicroscopicsilicovolcanoconiosis"}] * 4,
        }
    }

    result = figure(content)

    overflow = [f for f in result.findings if f.code == "text-overflow"]
    assert [f.where for f in overflow] == [f"figure/body/steps#{n}/head" for n in range(1, 5)]
    head = result.scene.find("figure/body/steps#1/head")
    assert head is not None and head.properties["overflow"] is True
    assert head.properties["font-size"] == 16.0  # never shrunk to fit


def test_a_missing_font_refuses_the_scene_before_layout() -> None:
    environment = {"fonts": {}}

    with pytest.raises(env.MissingFont, match=FAMILY):
        figure(**environment)


def test_a_character_no_family_measures_refuses_the_scene_naming_it() -> None:
    content = {**CONTENT, "caption": "A caption in 中文"}

    with pytest.raises(text.MissingGlyph, match=r"U\+4E2D.*figure/caption"):
        figure(content)
