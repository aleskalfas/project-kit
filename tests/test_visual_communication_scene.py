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
- a missing font, or a character no family measures, refused before layout;
- under a part that passes a list on under another name: each content source names the
  keys the content file writes, and a field no part passes on is the placing
  component's;
- a top whose layouts are its pages' forms: the scene's `pages` names each page in
  order, each a group of the top at its origin, as large as the top;
- a text's runs (DEC-012 points 3, 4 and 8, DEC-005 point 14): its paragraphs of runs,
  each with its role, its paint, its fonts and its sources, and its lines of spans; a
  run that names a concept and shows it in no colour; a text measured in part otherwise
  than from a font file, which overflows asking for attention;
- a fact of the export (DEC-006 point 7, DEC-016 point 5): each shown as one run of what
  fills it, with its source and in the scene's result, what fills it a required argument,
  the stand-ins the reference holds, and a fact's text that overflows, a finding that
  names the component.
"""

from __future__ import annotations

import dataclasses
import inspect
import json
from typing import Any

import pytest

from tests.visual_communication_project import CAPABILITY
from tests.visual_engine import (
    FAMILY,
    FONT,
    RUN_FONTS,
    RUN_ROLES,
    SEMIBOLD,
    SEMIBOLD_FONT,
    block,
    codes,
    draw,
    env,
    frame,
    layout,
    scene,
    text,
    top,
)

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
        4,
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
    run = head.properties["paragraphs"][0][0]
    assert run["sources"]["text"] == "content:body.steps[plan].head"
    assert run["sources"]["fill"] == "default:tests/card"
    assert run["sources"]["style"] == "default:tests/card"
    assert run["sources"]["font-size"] == "role:type.body"
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
    assert head.sources["line-height"] == "role:type.body"
    assert props["measured-height"] == props["height"] == 44.8
    [[run]] = props["paragraphs"]
    assert run["text"] == props["text"]
    assert (run["style"], run["font-family"], run["font-size"]) == ("type.body", [FAMILY], 16.0)
    assert run["measured"] == "file"
    sha256 = text.Face(FAMILY, FONT).sha256
    assert run["fonts"] == [{"family": FAMILY, "file": FONT.name, "sha256": sha256}]
    for line in props["lines"]:
        assert 0 < line["baseline"] < props["line-height"]
        assert line["paragraph"] == 0
        assert line["spans"] == [{"run": 0, "text": line["text"], "width": line["width"]}]


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
    assert head.properties["paragraphs"][0][0]["font-size"] == 16.0  # never shrunk to fit


def test_a_missing_font_refuses_the_scene_before_layout() -> None:
    environment = {"fonts": {}}

    with pytest.raises(env.MissingFont, match=FAMILY):
        figure(**environment)


def test_a_character_no_family_measures_refuses_the_scene_naming_it() -> None:
    content = {**CONTENT, "caption": "A caption in 中文"}

    with pytest.raises(text.MissingGlyph, match=r"U\+4E2D.*figure/caption"):
        figure(content)


# --- a list a part passes on under another name ---------------------------------------------

LISTED = {"type": "array", "items": {"type": "object"}}

#: A flow that passes its `stages` on to the steps as `steps`, and a stage that passes its
#: `shots`, `says` and `at` on to the callout as `pictures`, `label` and `at`.
PASSING = {
    "lab/flow": block(
        {"p": {"use": "tests/steps", "fields": {"steps": "stages"}, "width": "=:width"}},
        fields={"stages": LISTED},
        preferred={"height": "=p.height"},
    ),
    "lab/shot": block(
        {
            "p": {
                "use": "tests/callout",
                "fields": {"pictures": "shots", "label": "says", "at": "at"},
                "width": "=:width",
            }
        },
        fields={"shots": LISTED, "says": {"type": "string"}, "at": {"type": "object"}},
        preferred={"height": "=p.height"},
    ),
}

STAGES = {
    "body": {
        "use": "lab/flow",
        "stages": [
            {"id": "plan", "head": "Plan the work"},
            {"head": "Build it"},
            {
                "id": "note",
                "use": "lab/shot",
                "shots": [{"id": "square", "output": "square"}],
                "says": "Here",
                "at": {"item": "square", "point": "tip"},
            },
        ],
    },
    "caption": "Three stages, passed on to the steps.",
}


def test_a_source_under_a_part_that_passes_a_list_on_names_the_keys_the_content_writes() -> None:
    result = figure(STAGES, components=PASSING)

    assert result.findings == []
    sources = {}
    for trace, key in (
        ("steps[plan]/head", "text"),
        ("steps#2/head", "text"),
        ("steps[note]/p/pictures[square]/image", "output"),
        ("steps[note]/p/label", "text"),
        ("steps[note]/p", "options.at"),
    ):
        element = result.scene.find(f"figure/body/p/{trace}")
        assert element is not None, trace
        sources[trace] = element.sources[key]
    assert sources == {
        "steps[plan]/head": "content:body.stages[plan].head",
        "steps#2/head": "content:body.stages#2.head",
        "steps[note]/p/pictures[square]/image": "content:body.stages[note].shots[square].output",
        "steps[note]/p/label": "content:body.stages[note].says",
        "steps[note]/p": "content:body.stages[note].at",
    }


def test_a_field_the_content_leaves_out_names_its_key_and_one_no_part_passes_on_does_not() -> None:
    """A field a part passes on that the content leaves out names the key the content file
    would write. A field the part does not pass on has no key in the content file: the
    component whose part placed it gives it, and gives nothing."""
    shot = PASSING["lab/shot"]
    parts = {"p": {**shot["parts"]["p"], "fields": {"pictures": "shots", "at": "at"}}}
    unpassed = {**PASSING, "lab/shot": {**shot, "parts": parts}}
    note = {key: value for key, value in STAGES["body"]["stages"][2].items() if key != "says"}
    left_out = {**STAGES, "body": {"use": "lab/flow", "stages": [note]}}
    label = "figure/body/p/steps[note]/p/label"

    for content, components, source in (
        (left_out, PASSING, "content:body.stages[note].says"),
        (STAGES, unpassed, "default:lab/shot"),
    ):
        element = figure(content, components=components).scene.find(label)
        assert element is not None
        assert (element.properties["text"], element.sources["text"]) == ("", source)


# --- a top whose layouts are its pages' forms (#2558) ------------------------------------------

DECK = {
    "slides": [
        {"id": "cover", "layout": "cover", "title": "Building with AI"},
        {"id": "rules", "layout": "slide", "title": "Where permissions come from"},
        {"layout": "slide", "title": "How it fits"},
    ]
}


def test_a_decks_scene_names_each_page_in_order_each_a_group_of_the_top() -> None:
    result = draw(DECK, use="foundations/deck")
    tree = result.scene.to_dict()

    assert result.findings == []
    assert tree["pages"] == ["deck/slides[cover]", "deck/slides[rules]", "deck/slides#3"]
    deck = tree["children"][0]
    assert "page" not in deck
    assert (deck["sources"]["width"], deck["sources"]["height"]) == (
        "role:size.slide",
        "default:foundations/deck",
    )
    pages = [child for child in deck["children"] if child.get("page")]
    assert [page["id"] for page in pages] == tree["pages"]
    for page in pages:
        assert page["component"] == "foundations/deck"
        assert (page["x"], page["y"], page["width"], page["height"]) == (0, 0, 1280, 720)
        assert {page["sources"][key] for key in ("x", "y", "width", "height")} == {"engine"}


# --- a text's runs ------------------------------------------------------------------------------

#: A sentence whose strong runs are painted from the colour family, its plain ones with a
#: role, in a width of 100 px.
SAYING = top(
    {
        "say": {
            "text": {
                "content": "say",
                "style": {"by": "say", "plain": "type.body", "strong": "type.heading"},
                "fill": {"by": "say", "plain": "text-primary", "strong": ":colour.text"},
            },
            "width": "=@space.4 * 3",
        }
    },
    fields={"say": {"type": "string", "x-pkit-runs": ["plain", "strong"]}},
    colour="blue",
)


def saying(say: Any, **environment: Any) -> Any:
    return draw(
        {"say": say, **environment.pop("given", {})},
        components={"lab/top": SAYING},
        roles=RUN_ROLES,
        fonts=RUN_FONTS,
        families={"blue": {"text": "accent"}, "red": {"text": "text-secondary"}},
        concepts={"flow/queue": "red"},
        **environment,
    )


def test_a_text_holds_its_paragraphs_of_runs_and_its_lines_of_spans() -> None:
    result = saying(["One ", {"text": "two", "style": "strong"}, "\nthree"])

    element = result.scene.find("top/say")
    assert element is not None
    props = element.properties
    assert result.findings == []
    assert list(props) == [
        "x",
        "y",
        "width",
        "height",
        "text-anchor",
        "line-height",
        "text",
        "paragraphs",
        "lines",
        "measured-height",
    ]
    first, second = props["paragraphs"]
    assert [run["text"] for run in first] == ["One ", "two"]
    assert [run["text"] for run in second] == ["three"]
    strong = first[1]
    assert list(strong) == [
        "text",
        "fill",
        "style",
        "font-family",
        "font-size",
        "font-weight",
        "fonts",
        "measured",
        "sources",
    ]
    sha256 = text.Face(SEMIBOLD, SEMIBOLD_FONT).sha256
    assert strong["fonts"] == [{"family": SEMIBOLD, "file": SEMIBOLD_FONT.name, "sha256": sha256}]
    assert (strong["fill"], strong["sources"]["fill"]) == ("accent", "default:lab/top")
    # A run that goes on into the next paragraph is the same run of the field, by its place.
    assert second[0]["sources"]["text"] == "content:say#3"
    assert [line["paragraph"] for line in props["lines"]] == [0, 1]
    assert props["lines"][0]["spans"] == [
        {"run": 0, "text": "One ", "width": round(advance("type.body", "One "), 2)},
        {"run": 1, "text": "two", "width": round(advance("type.heading", "two"), 2)},
    ]
    assert props["measured-height"] == round(2 * 28.8, 2)


def advance(role: str, words: str) -> float:
    """How far `words` move the pen in the run role `role`."""
    faces = text.Faces(lambda family: RUN_FONTS[family])
    return text.Style.of_role(role, RUN_ROLES[role], faces).advance(words)


def test_a_run_that_names_a_concept_shown_in_no_colour_asks_for_attention() -> None:
    coloured = saying([{"text": "the queue", "style": "strong", "concept": "flow/queue"}])
    by_style = saying([{"text": "the queue", "concept": "flow/queue"}])
    overridden = saying(
        [{"text": "the queue", "style": "strong", "concept": "flow/queue"}],
        given={"override": {"say": "accent"}},
    )

    assert coloured.findings == []
    run = coloured.scene.find("top/say").properties["paragraphs"][0][0]
    assert (run["fill"], run["sources"]["fill"]) == ("text-secondary", "content:say#1.concept")
    for result, why in (
        (by_style, "its style `plain`"),
        (overridden, "the `override` of its part"),
    ):
        [found] = [f for f in result.findings if f.code == "concept-uncoloured"]
        assert (found.level, found.where, found.who) == (
            "attention",
            "top/say",
            "the piece's author",
        )
        assert "the run say#1 names the concept `flow/queue`" in found.message
        assert why in found.message


def test_an_overflowing_text_measured_in_part_otherwise_than_from_a_file_asks_for_attention(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    long = "Pneumonoultramicroscopicsilicovolcanoconiosis"
    all_files = saying([long, {"text": " b", "style": "strong"}])
    of_role = text.Style.of_role

    def tabled(role: str, value: Any, faces: Any) -> Any:
        found = of_role(role, value, faces)
        return dataclasses.replace(found, measured="table") if role == "type.heading" else found

    monkeypatch.setattr(text.Style, "of_role", staticmethod(tabled))
    in_part = saying([long, {"text": " b", "style": "strong"}])

    [fails] = [f for f in all_files.findings if f.code == "text-overflow"]
    [asks] = [f for f in in_part.findings if f.code == "text-overflow"]
    assert (fails.level, fails.who) == ("fails", "")
    assert (asks.level, asks.who) == ("attention", "the piece's author")
    assert asks.message == f"{fails.message}, measured in part table, not from a font file"
    runs = in_part.scene.find("top/say").properties["paragraphs"][0]
    assert [run["measured"] for run in runs] == ["file", "table"]


# --- the facts of an export ---------------------------------------------------------------------

#: What fills the facts in these tests, with no stand-in among it.
FILLED = layout.Facts("v3", "2026-11-06", "published")


def showing(word: Any, *, language: str = "en", facts: Any = FILLED, **props: Any) -> Any:
    """A top that shows the fact `word` in a text as wide as the figure role."""
    shown = {"text": {"fact": word, "style": "type.body", **props}, "width": "=:width"}
    return draw(language=language, facts=facts, components={"lab/top": top({"t": shown})})


@pytest.mark.parametrize(
    ("word", "shown"),
    [
        ("version", "v3"),
        ("date", "2026-11-06"),
        ("language", "cs"),
        ("state", "published"),
    ],
)
def test_a_text_shows_each_fact_as_one_run_of_what_fills_it(word: str, shown: str) -> None:
    result = showing(word, language="cs", fill="text-primary")
    assert result.findings == []
    element = result.scene.find("top/t")
    assert element is not None
    assert element.properties["text"] == shown
    assert element.sources["text"] == f"fact:{word}"
    [[run]] = element.properties["paragraphs"]
    assert (run["text"], run["style"]) == (shown, "type.body")
    assert run["sources"]["text"] == f"fact:{word}"
    assert run["sources"]["style"] == run["sources"]["fill"] == "default:lab/top"


def test_a_scenes_result_says_which_facts_it_shows_and_where() -> None:
    def shown(word: str, **geometry: Any) -> dict[str, Any]:
        return {"text": {"fact": word, "style": "type.body"}, **geometry}

    parts = {
        "first": shown("date"),
        "second": shown("date"),
        "state": shown("state"),
        "absent": shown("version", when="never"),
    }
    result = draw(facts=FILLED, components={"lab/top": top(parts)})
    assert result.facts == {"date": ["top/first", "top/second"], "state": ["top/state"]}


def test_what_fills_the_facts_is_a_required_argument_of_a_scene() -> None:
    required = inspect.signature(scene.compute_scene).parameters["facts"]
    assert required.default is inspect.Parameter.empty


def test_two_scenes_with_one_root_differ_only_in_the_text_of_a_fact() -> None:
    def held(facts: Any) -> dict[str, Any]:
        return showing("version", facts=facts).scene.to_dict()

    first, second = held(FILLED), held(dataclasses.replace(FILLED, version="v4"))
    assert first != second
    assert json.loads(json.dumps(first).replace('"v3"', '"v4"')) == second


def test_a_piece_that_shows_no_fact_draws_the_same_whatever_fills_them() -> None:
    other = layout.Facts("v1", "2000-01-01", "draft")
    drawn, again = figure(facts=FILLED), figure(facts=other)
    assert drawn.scene.to_dict() == again.scene.to_dict()
    assert drawn.facts == {}
    assert "fact:" not in json.dumps(drawn.scene.to_dict())


def test_the_stand_ins_are_those_the_reference_holds() -> None:
    assert layout.stand_ins("final") == layout.Facts("v88", "2088-08-28", "final")
    page = (CAPABILITY / "components.md").read_text(encoding="utf-8")
    assert all(f"`{text_}`" in page for text_ in layout.STAND_INS.values())


def narrow(word: str = "version") -> Any:
    """A top that shows the fact `word` in a text too narrow for its stand-in."""
    shown = {"text": {"fact": word, "style": "type.body"}, "width": "=@space.1"}
    return draw(facts=layout.stand_ins("draft"), components={"lab/top": top({"t": shown})})


@pytest.mark.parametrize("word", ["version", "date"])
def test_a_stand_in_is_one_word_so_too_narrow_a_text_overflows_rather_than_breaks_it(
    word: str,
) -> None:
    held = narrow(word).scene.find("top/t")
    assert held is not None
    assert held.properties["overflow"] is True
    assert [line["text"] for line in held.properties["lines"]] == [layout.STAND_INS[word]]


def test_a_fact_that_overflows_is_a_finding_at_its_element_naming_the_component() -> None:
    result = narrow()
    [found] = [f for f in result.findings if f.code == "text-overflow"]
    assert (found.level, found.where) == ("fails", "top/t")
    assert (found.library, found.extra) == ("lab@1.0.0", {"component": "lab/top"})
    assert found.message.startswith(
        "top/t: a word of fact:version in `lab/top` is wider than the text's width 4.0 px: "
    )
    assert found.fix == "give the text `t` of `lab/top` more width"


def test_a_fact_that_overflows_measured_otherwise_than_from_a_file_asks_for_attention(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fails = narrow()
    of_role = text.Style.of_role

    def tabled(role: str, value: Any, faces: Any) -> Any:
        return dataclasses.replace(of_role(role, value, faces), measured="table")

    monkeypatch.setattr(text.Style, "of_role", staticmethod(tabled))
    [asks] = [f for f in narrow().findings if f.code == "text-overflow"]
    [failing] = [f for f in fails.findings if f.code == "text-overflow"]
    assert (asks.level, asks.who, asks.library) == ("attention", "the piece's author", "lab@1.0.0")
    assert asks.message == f"{failing.message}, measured in part table, not from a font file"


def test_a_field_that_overflows_stays_in_the_content() -> None:
    result = figure({"body": {"use": "tests/steps", "steps": [{"head": "W" * 60}]}})
    [found] = [f for f in result.findings if f.code == "text-overflow"]
    assert (found.library, found.extra, found.fix) == ("", {}, "")
    assert " in `" not in found.message


@pytest.mark.parametrize(
    ("props", "where"),
    [
        ({"fact": "number"}, "parts.t.text.fact"),
        ({"fact": "version", "content": "say"}, "parts.t.text"),
        ({}, "parts.t.text"),
    ],
    ids=["no-such-fact", "both", "neither"],
)
def test_a_text_that_names_no_one_thing_to_show_is_refused_and_computes(
    props: dict[str, Any], where: str
) -> None:
    fields = {"say": {"type": "string"}}
    part = {"text": {"style": "type.body", **props}, "width": "=:width"}
    result = draw(facts=FILLED, components={"lab/top": top({"t": part}, fields=fields)})
    assert codes(result) == ["component-shape"]
    assert result.findings[0].where == where
