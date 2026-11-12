"""A run's sign and ground (visual-communication DEC-036 point 3, DEC-012 points 2 and 4).

- **Chosen by the run's style.** A text part that shows a field of runs chooses by each run's
  style whether a run that names a concept draws its sign, and the run's ground, a paint or
  none. A part that chooses neither draws every run as before. Only such a part chooses
  either, and each reads its lengths from roles the foundations declare.
- **The sign** lies before the run's first character that is no space or line feed, on that
  character's line, as wide as the run's font size, with the gap after it. No line breaks
  between the two.
- **The ground** lies behind each piece of the run on each line it spans, its sign included,
  with room where it starts and where it ends, and square where a line breaks it. It is the
  fill the run is measured against.
- **One span for runs that run on.** Runs next to each other in one paragraph that name one
  concept and draw its sign draw one sign, before the first; runs that take one ground take
  it once, with room at its two ends alone.
- **Held with the run.** The scene's line holds each sign and ground with the run's piece and
  the room the engine gave them, and each renderer draws them with the run.
"""

from __future__ import annotations

import re
from typing import Any
from xml.etree import ElementTree

import pytest

from tests.in_process import load
from tests.test_visual_communication_html import draw as draw_html
from tests.test_visual_communication_html import forced, marked, styled
from tests.test_visual_communication_pdf import draw as draw_pdf
from tests.test_visual_communication_pdf import page_of
from tests.test_visual_communication_signs import CONCEPTS, FAMILIES, SIGNS
from tests.test_visual_communication_svg import draw as draw_svg
from tests.visual_communication_project import bound
from tests.visual_engine import (
    FONT,
    FOUNDATIONS,
    ROLES,
    RUN_FONTS,
    RUN_ROLES,
    FakeEnv,
    draw,
    layout,
    text,
    top,
)

checks, files, seam, tokens = load(
    "visual-communication", "checks", "files", "plugins.seam", "tokens"
)
svg_declaration, html_declaration, pdf_declaration = load(
    "visual-communication",
    "plugins.svg_declaration",
    "plugins.html_declaration",
    "plugins.pdf_declaration",
)


def px(value: float) -> dict[str, Any]:
    return {"value": value, "unit": "px"}


# --- measured within the line (text.py) ---------------------------------------------------------

BODY = text.Style.of_role("type.body", ROLES["type.body"], text.Faces(lambda _family: FONT))

#: The gap after a sign and the room at a ground's ends, as the foundations' roles give them.
MARKS = text.Marks(gap=3.0, room=2.0)

#: The square of a sign in the body's role: as wide as its font size.
SIGN = 16.0


def run(words: str, *, sign: str | None = None, ground: str | None = None) -> Any:
    return text.Run(words, BODY, sign, ground)


def broken(*runs: Any, width: float | None = None) -> Any:
    return text.break_runs(list(runs), width, "en", MARKS)


def laid(result: Any) -> list[list[tuple[str, bool, Any, Any]]]:
    """Each line's spans: its text, whether a sign lies before it, and the room before and
    after it where a ground starts or ends there, `-` where it lies in a ground that does
    neither, and None where it has no ground."""
    found = []
    for line in result.placed:
        spans = []
        for span in line.spans:
            ground = span.ground
            start = "-" if ground is not None else None
            end = "-" if ground is not None else None
            if ground is not None:
                start = ground.start if ground.start is not None else "-"
                end = ground.end if ground.end is not None else "-"
            spans.append((span.text, span.sign is not None, start, end))
        found.append(spans)
    return found


def test_a_text_whose_runs_take_neither_breaks_and_measures_as_before() -> None:
    runs = [run("Plan the "), run("work"), run(" now\nthen")]
    for width in (None, 60.0):
        before = text.break_runs(runs, width, "en")
        assert text.break_runs(runs, width, "en", MARKS) == before
        assert all(
            span.sign is None and span.ground is None
            for line in before.placed
            for span in line.spans
        )


def test_a_sign_lies_before_the_runs_first_character_that_is_no_space_or_line_feed() -> None:
    """The run goes on into the next paragraph past a line feed, so its sign lies there,
    on the line of its first letter, as wide as its font size, with the gap after it."""
    result = broken(run("Plan "), run(" \n the work", sign="sys/store"))

    assert laid(result) == [
        [("Plan", False, None, None)],
        [(" ", False, None, None), ("the work", True, None, None)],
    ]
    sign = result.placed[1].spans[1].sign
    assert (sign.size, sign.gap) == (SIGN, 3.0)
    middle = result.placed[1].baseline - (BODY.ascent - BODY.descent) / 2
    assert sign.top == pytest.approx(middle - SIGN / 2)
    assert result.placed[1].width == pytest.approx(BODY.advance(" the work") + SIGN + 3.0)


def test_no_line_breaks_between_a_sign_and_its_character() -> None:
    """A width that holds the words alone, and not with the sign: the run's word moves to the
    next line with its sign."""
    width = BODY.advance("Plan the") + text.BREAK_MARGIN * 16 + 5
    plain = text.break_runs([run("Plan "), run("the")], width, "en", MARKS)
    signed = broken(run("Plan "), run("the", sign="sys/store"), width=width)

    assert list(plain.lines) == ["Plan the"]
    assert list(signed.lines) == ["Plan", "the"]
    assert laid(signed)[1] == [("the", True, None, None)]


def test_a_ground_lies_behind_each_piece_on_each_line_with_room_at_its_ends_alone() -> None:
    """Broken over three lines, the ground starts with room on the first, runs on square
    across the second, and ends with room on the third. Each piece takes one top and one
    height on its line."""
    result = broken(run("go "), run("one two three", ground="accent"), run(" end"), width=48.0)

    lines = laid(result)
    grounded = [span for line in lines for span in line if span[2] is not None]
    assert [span[0] for span in grounded] == ["one", "two", "three"]
    assert [(span[2], span[3]) for span in grounded] == [(2.0, "-"), ("-", "-"), ("-", 2.0)]
    for line in result.placed:
        pieces = {(span.ground.top, span.ground.height) for span in line.spans if span.ground}
        assert len(pieces) <= 1


def test_a_grounds_room_and_a_sign_count_in_the_lines_width_and_each_spans_advance() -> None:
    result = broken(run("go "), run("there", sign="sys/store", ground="accent"), run(" now"))

    [line] = result.placed
    assert line.width == pytest.approx(sum(span.advance for span in line.spans))
    assert line.width == pytest.approx(BODY.advance("go there now") + 2 * 2.0 + SIGN + 3.0)


def test_spaces_at_a_runs_ends_lie_outside_its_ground_and_before_its_sign() -> None:
    result = broken(run("a"), run(" two ", sign="sys/store", ground="accent"), run("b"))

    assert laid(result) == [
        [
            ("a", False, None, None),
            (" ", False, None, None),
            ("two", True, 2.0, 2.0),
            (" ", False, None, None),
            ("b", False, None, None),
        ]
    ]


def test_runs_that_run_on_draw_one_sign_and_take_one_ground() -> None:
    """Two runs of one concept draw one sign, before the first; a third of another concept
    draws its own. One ground behind all three takes room at its two ends alone."""
    result = broken(
        run("a ", sign="sys/store", ground="accent"),
        run("b", sign="sys/store", ground="accent"),
        run(" c", sign="sys/user", ground="accent"),
    )

    assert laid(result) == [
        [
            ("a ", True, 2.0, "-"),
            ("b", False, "-", "-"),
            (" ", False, "-", "-"),
            ("c", True, "-", 2.0),
        ]
    ]


def test_runs_in_two_paragraphs_share_no_sign_and_no_ground() -> None:
    result = broken(
        run("a\n", sign="sys/store", ground="accent"), run("b", sign="sys/store", ground="accent")
    )

    assert laid(result) == [[("a", True, 2.0, 2.0)], [("b", True, 2.0, 2.0)]]


# --- chosen by the run's style, and held in the scene -------------------------------------------

#: The roles of a run's sign and ground, each a length of its own, beside the runs' roles.
MARK_ROLES = {
    **RUN_ROLES,
    "space.sign-gap": px(3),
    "space.ground-room": px(2),
    "space.ground-corner": px(5),
}

#: A field of runs of two words, and a text part that draws a run of `named` in the heading,
#: from its family, with its concept's sign and on its family's fill.
FIELDS = {"says": {"type": "string", "x-pkit-runs": ["plain", "named"]}}
SAYS = {
    "content": "says",
    "style": {"by": "says", "plain": "type.body", "named": "type.heading"},
    "fill": {"by": "says", "plain": "ink", "named": ":colour.line"},
    "sign": {"by": "says", "plain": False, "named": True},
    "ground": {"by": "says", "plain": None, "named": ":colour.fill"},
}


def said(*runs: Any, part: dict[str, Any] | None = None, given: Any = None, **keys: Any) -> Any:
    """The scene of a text part, `SAYS` or `part`, as wide as the figure, showing `runs`;
    `given` adds to the content and `keys` to the component."""
    shown = {"text": part or SAYS, "width": "=@size.figure"}
    components = {"lab/top": top({"says": shown}, fields=FIELDS, **keys)}
    return draw(
        {"says": list(runs), **(given or {})},
        components=components,
        families=FAMILIES,
        concepts=CONCEPTS,
        signs=SIGNS,
        roles=MARK_ROLES,
        fonts=RUN_FONTS,
    )


def held(result: Any) -> tuple[Any, Any]:
    """The text's lines and its paragraphs of runs, as the scene holds them."""
    found = result.scene.find("top/says")
    assert found is not None
    return found.properties["lines"], found.properties["paragraphs"]


def test_the_scene_holds_each_runs_sign_and_ground_with_its_piece_and_their_sources() -> None:
    result = said("Plan ", {"text": "the store", "style": "named", "concept": "sys/store"})

    assert result.findings == []
    [line], [runs] = held(result)
    plain, named = runs
    assert ("sign" in plain, "ground" in plain) == (False, False)
    assert (named["sign"], named["ground"], named["fill"]) == (True, "surface", "border")
    assert named["sources"]["sign"] == "content:says#2.style"
    assert named["sources"]["ground"] == "content:says#2.concept"
    first, second = line["spans"]
    assert set(first) == {"run", "text", "width"}
    # Measured in the run's role, the heading: its square as wide as its font size.
    assert second["sign"] == {
        "d": "M 0 0 L 24 0 L 24 24 L 0 24 Z",
        "fill-rule": "nonzero",
        "size": 24,
        "top": second["sign"]["top"],
        "gap": 3,
    }
    assert second["ground"] == {
        "top": second["ground"]["top"],
        "height": second["ground"]["height"],
        "rx": 5,
        "start": 2,
        "end": 2,
    }
    # The ground holds the sign: from its square's top to its foot, or the letters' reach.
    sign, ground = second["sign"], second["ground"]
    assert ground["top"] <= sign["top"]
    assert ground["top"] + ground["height"] >= sign["top"] + sign["size"]
    room = 2 + 24 + 3 + 2
    assert line["width"] == pytest.approx(first["width"] + second["width"] + room, abs=0.02)


def test_a_part_that_chooses_neither_draws_every_run_as_before() -> None:
    plain = {key: value for key, value in SAYS.items() if key not in ("sign", "ground")}
    runs = ("Plan ", {"text": "the store", "style": "named", "concept": "sys/store"})

    [line], [paragraph] = held(said(*runs, part=plain))
    assert all(set(span) == {"run", "text", "width"} for span in line["spans"])
    assert all("sign" not in each and "ground" not in each for each in paragraph)
    assert line["width"] == pytest.approx(sum(span["width"] for span in line["spans"]), abs=0.02)


def test_a_run_whose_concept_has_no_sign_or_that_names_none_draws_no_sign() -> None:
    """Its ground it takes all the same: here a role of its own where the run names no
    concept, since a family's member would have no family to come from."""
    signless = said({"text": "plain", "style": "named", "concept": "sys/plain"})
    fixed = {**SAYS, "fill": "ink", "ground": {"by": "says", "plain": None, "named": "accent"}}
    unnamed = said({"text": "bare", "style": "named"}, part=fixed)

    for result, ground in ((signless, "surface"), (unnamed, "accent")):
        assert result.findings == []
        [line], [[run_]] = held(result)
        assert ("sign" in run_, run_["ground"]) == (False, ground)
        assert all("sign" not in span and "ground" in span for span in line["spans"])


def test_a_state_changes_a_runs_paint_and_ground_and_never_its_sign() -> None:
    result = said(
        {"text": "store", "style": "named", "concept": "sys/store"},
        states={"marked": {"colour": "red"}},
        given={"state": "marked"},
    )

    assert result.findings == []
    [line], [[named]] = held(result)
    assert (named["fill"], named["ground"], named["sign"]) == ("ink", "accent", True)
    assert line["spans"][0]["sign"]["d"] == "M 0 0 L 24 0 L 24 24 L 0 24 Z"


# --- what the component may choose --------------------------------------------------------------


def issues(part: dict[str, Any], *, roles: Any = None, fields: Any = None) -> list[str]:
    component = top({"says": {"text": part}}, fields=fields or FIELDS)
    ctx = layout.Context(FakeEnv(roles=MARK_ROLES if roles is None else roles), "en")
    found = layout.Component("lab/x", component, ctx).issues
    return [message.removeprefix("lab/x: ") for _, _, message in found]


def test_a_part_chooses_either_only_where_it_shows_a_field_of_runs() -> None:
    fields = {"plain": {"type": "string"}}
    part = {"content": "plain", "style": "type.body", "sign": True, "ground": "surface"}

    assert issues(part, fields=fields) == [
        "the text `says` chooses a run's sign, and shows no field of runs",
        "the text `says` chooses a run's ground, and shows no field of runs",
    ]


def test_a_sign_is_true_or_false_and_a_ground_a_paint_or_none() -> None:
    assert issues(SAYS) == []
    assert issues({**SAYS, "sign": "yes"}) == ["`yes` is neither `true` nor `false`"]
    assert issues({**SAYS, "ground": "Not A Role"}) == [
        "`Not A Role` is not a role's token path, nor `:colour.<member>`"
    ]


def test_a_part_that_chooses_only_a_runs_sign_by_its_words_chooses_by_them() -> None:
    """Of a field of more than one word, one text part chooses by the words: here its sign
    alone, which counts (DEC-012 point 2)."""
    part = {
        "content": "says",
        "style": "type.body",
        "sign": {"by": "says", "plain": False, "named": True},
    }
    assert issues(part) == []
    assert any("no text part chooses" in each for each in issues({**part, "sign": True}))


def test_the_lengths_come_from_roles_the_brand_must_give() -> None:
    said_ = issues(SAYS, roles=RUN_ROLES)
    assert said_ == [
        "a run's sign, reading `@space.sign-gap`, names a role the brand gives no value",
        "a run's ground, reading `@space.ground-room`, names a role the brand gives no value",
        "a run's ground, reading `@space.ground-corner`, names a role the brand gives no value",
    ]
    numbered = {**MARK_ROLES, "space.sign-gap": 3}
    assert issues(SAYS, roles=numbered) == [
        "a run's sign, reading `@space.sign-gap`, takes a number, not a length"
    ]


def test_a_component_that_chooses_a_runs_sign_and_ground_holds_the_schema() -> None:
    component = bound("component", **top({"says": {"text": SAYS}}, fields=FIELDS))
    assert files.shape_problems(component, "component") == []
    wrong = {**SAYS, "sign": "yes"}
    refused = bound("component", **top({"says": {"text": wrong}}, fields=FIELDS))
    assert files.shape_problems(refused, "component") != []


def test_the_foundations_declare_the_lengths_each_at_their_smallest_space() -> None:
    declared = tokens.read_declarations(FOUNDATIONS / "roles.yaml")
    for path in (layout.SIGN_GAP, layout.GROUND_ROOM, layout.GROUND_CORNER):
        assert declared.roles[path] == tokens.Role(path, "dimension", "space.1")


# --- each renderer draws them with the run ------------------------------------------------------

#: A text of a plain line and a line with a sign and a ground, as the engine gives it.
RUNS = ("Plan\n", {"text": "the store", "style": "named", "concept": "sys/store"}, " now")


def drawn_scene(**changes: Any) -> dict[str, Any]:
    """The scene of `RUNS`, its text's anchor and its paints changed as `changes` say."""
    result = said(*RUNS)
    assert result.findings == []
    scene = result.scene.to_dict()
    page = scene["children"][0]
    [shown] = page["children"]
    shown.update(changes)
    return scene


def test_each_renderer_rose_to_draw_them_at_the_seams_version() -> None:
    assert seam.SEAM_VERSION == 8
    versions = {
        declaration.DECLARATION["name"]: declaration.DECLARATION["version"]
        for declaration in (svg_declaration, html_declaration, pdf_declaration)
    }
    assert versions == {"svg": "1.3.0", "html": "1.6.0", "pdf": "1.5.0"}
    scene = drawn_scene()
    for declaration in (svg_declaration, html_declaration, pdf_declaration):
        assert declaration.DECLARATION["seam"] == seam.SEAM_VERSION
        assert checks.losses(scene, declaration.DECLARATION) == []


def test_the_svg_renderer_draws_ground_and_sign_behind_the_text_and_places_its_spans() -> None:
    scene = drawn_scene(**{"text-anchor": "middle"})
    shown = scene["children"][0]["children"][0]
    _, marked_line = shown["lines"]
    [page] = draw_svg(scene).pages

    root = ElementTree.fromstring(page.svg)
    drawn = [node for node in root.iter() if node.tag.rsplit("}", 1)[1] in ("path", "text")]
    kinds = [node.tag.rsplit("}", 1)[1] for node in drawn]
    assert kinds == ["path", "path", "text"]
    ground, sign, written = drawn
    assert ground.get("data-ground") == sign.get("data-sign") == "top/says"
    assert ground.get("fill") == "#ffffff"
    assert (sign.get("d"), sign.get("fill")) == ("M 0 0 L 24 0 L 24 24 L 0 24 Z", "#808080")
    # The plain line draws as before; the marked one places each span at its own start.
    first, second = written
    assert first.get("text-anchor") is None and all(span.get("x") is None for span in first)
    assert second.get("text-anchor") == "start"
    start = 320 - float(marked_line["width"]) / 2
    spans = list(second)
    assert float(spans[0].get("x", "")) == pytest.approx(start + 2 + 24 + 3, abs=0.01)
    moved = re.fullmatch(r"translate\(([\d.]+),([\d.]+)\)", sign.get("transform", ""))
    assert moved is not None
    assert float(moved[1]) == pytest.approx(start + 2, abs=0.01)
    # Its corners are curves where it starts and ends.
    outline = ground.get("d", "")
    assert outline.startswith("M ") and " C " in outline


def test_the_html_page_draws_the_ground_as_the_spans_background_and_the_sign_within_it() -> None:
    root = ElementTree.fromstring(draw_html(drawn_scene()).document)

    spans = marked(root, "span")
    marked_span = next(span for span in spans if marked(span, "sign"))
    style = styled(marked_span)
    assert style["background"] == "var(--surface)"
    assert style["padding-left"] == style["padding-right"] == "0.3125cqw"
    assert style["border-radius"] == "0.78125cqw 0.78125cqw 0.78125cqw 0.78125cqw"
    [sign] = marked(marked_span, "sign")
    assert (sign.get("viewBox"), sign.get("aria-hidden")) == ("0 0 24 24", "true")
    assert styled(sign)["margin-right"] == "0.46875cqw"
    [path] = list(sign)
    assert (path.get("d"), path.get("fill")) == ("M 0 0 L 24 0 L 24 24 L 0 24 Z", "var(--border)")
    assert "".join(marked_span.itertext()) == "the store"
    others = [span for span in spans if span is not marked_span]
    assert [("".join(span.itertext()), "background" in styled(span)) for span in others] == [
        ("Plan", False),
        (" now", False),
    ]
    assert not any(marked(span, "sign") for span in others)
    # Under forced colours a sign takes the shapes' rules: its fill the ground's colour.
    assert '[data-sign] [fill="var(--border)"]{fill:Canvas}' in forced(root)


def test_the_pdf_renderer_draws_the_ground_and_the_sign_before_the_text() -> None:
    file, page = page_of(draw_pdf(drawn_scene()))

    content = file.content(page)
    text_at = content.index("q BT\n")
    ground_at = content.index("q 1 1 1 rg\n")
    sign_at = content.index(" cm\nq 0.5 0.5 0.5 rg\n")
    assert ground_at < sign_at < text_at
    assert " c\n" in content[ground_at:sign_at]


# --- the checks ---------------------------------------------------------------------------------


def grey(level: float) -> dict[str, Any]:
    return {"colorSpace": "srgb", "components": [level, level, level], "alpha": 1}


def test_a_run_is_measured_against_its_ground_and_a_ground_with_no_colour_is_found() -> None:
    scene = drawn_scene()
    page = scene["children"][0]
    back = {
        "type": "box",
        "id": "top/back",
        "x": 0,
        "y": 0,
        "width": 640,
        "height": 200,
        "fill": "paper",
    }
    page["children"].insert(0, back)
    colours = {
        "paper": {"default": grey(1)},
        "ink": {"default": grey(0)},
        "border": {"default": grey(0.5)},
        "surface": {"default": grey(0.55)},
    }

    found = checks.drawn_contrast(scene, colours, ["default"])
    assert [(each.code, each.message.split(" in ")[0]) for each in found] == [
        ("contrast-drawn", "`border` on `surface` has the contrast 1.19")
    ]
    lacking = {key: value for key, value in colours.items() if key != "surface"}
    unknown = checks._unknown_colours(
        scene, {key: value["default"] for key, value in lacking.items()}
    )
    assert [each.message for each in unknown] == [
        "paints its ground with `surface`, which is no colour role of the brand"
    ]
