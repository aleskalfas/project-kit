"""An order's colour steps (visual-communication DEC-032 points 3 to 7): how the engine spreads
a step between an order's two ends, how a pattern gives a list's places their steps under a
word, how the scene names them and hands their values on, how each renderer draws them, and
what the checks fail.

- **The spread** is tested against fixed values, worked out once and pinned here, so a run
  on any machine that gives another value fails. The suite runs on macOS, where it is
  built, and on Linux, in CI. A step halfway from black to white is Oklab's middle grey,
  whose value follows by hand: lightness 0.5 is linear light 0.125, which sRGB encodes as
  0.38857. A step between green and blue falls outside sRGB, and comes back by CSS Color 4's
  gamut mapping. Alpha is premultiplied, as CSS Color 4 interpolates. The values hold without
  `math.cbrt`, which Python 3.10, the scripts' declared floor, lacks.
- **The engine** gives place k of the n places a list draws the share (k - 1) / (n - 1), under
  the word of an option that gives the steps, every item counted, one that names its own
  component included; a concept and a state still come before a step, and an outer item
  passes its step to what sits in it. Under foundations that declare no ends, a place takes
  no step, which is stated at the piece's lock.
- **The findings** of point 7 this module builds: an order named where a family is named, or
  painted by its name in a library's component (`order-named`); a word that gives a list the
  steps and names a family for it (`order-steps-family`); and the shapes a pattern's switch of
  its places' families may not take.
- **The renderers** each draw a step from the value handed to them with the scene, and the
  pipeline hands each step's value in each combination, from that combination's own ends.
- **A step one of whose ends has no colour in a mode** has none there, as such a role has:
  each renderer draws nothing there and reports the loss, and the check reads it as a fill
  that draws nothing, in every mode.
"""

from __future__ import annotations

import math
from fractions import Fraction
from pathlib import Path
from typing import Any

import pytest

from tests.in_process import load
from tests.test_visual_communication_checks import box, page, text
from tests.test_visual_communication_pdf import page_of
from tests.test_visual_communication_svg import COLOURS, FONT, element, scene
from tests.visual_communication_project import (
    FOUNDATIONS,
    TEST_BRAND,
    bound,
    copy_library,
    importable,
    project,
    write,
    write_list,
    write_piece,
    yaml_text,
)
from tests.visual_engine import FakeEnv, Order, block, codes, draw, findings, layout, top

colour_steps, svg, html, pdf, pl, checks = load(
    "visual-communication",
    "colour_steps",
    "plugins.svg",
    "plugins.html",
    "plugins.pdf",
    "pipeline",
    "checks",
)

FIRST, LAST, TEXT = Order().first, Order().last, Order().text


def srgb(red: float, green: float, blue: float, alpha: float = 1) -> dict[str, Any]:
    return {"colorSpace": "srgb", "components": [red, green, blue], "alpha": alpha}


BLACK, WHITE = srgb(0, 0, 0), srgb(1, 1, 1)
GREEN, BLUE = srgb(0, 1, 0), srgb(0, 0, 1)


def step(share: str) -> str:
    """The name of the order's step at `share`, as the scene names it."""
    return f"step({FIRST},{LAST},{share})"


# --- the spread -----------------------------------------------------------------------------


def test_a_step_between_black_and_white_is_the_grey_oklab_puts_there() -> None:
    assert colour_steps.spread(BLACK, WHITE, Fraction(1, 2)) == srgb(0.3886, 0.3886, 0.3886)
    assert colour_steps.spread(BLACK, WHITE, Fraction(1, 3)) == srgb(0.2122, 0.2122, 0.2122)


def test_the_first_and_the_last_share_are_the_ends_as_given() -> None:
    first, last = srgb(0.0941, 0.1961, 0.4196), {"components": [0.851, 0.9059, 0.9725]}
    assert colour_steps.spread(first, last, Fraction(0)) == first
    assert colour_steps.spread(first, last, Fraction(1)) == srgb(0.851, 0.9059, 0.9725)


def test_steps_over_five_places_of_a_ramp_are_pinned() -> None:
    first, last = srgb(0.0941, 0.1961, 0.4196), srgb(0.851, 0.9059, 0.9725)
    spread = [colour_steps.spread(first, last, Fraction(k, 4))["components"] for k in (1, 2, 3)]
    assert spread == [
        [0.2636, 0.3641, 0.5561],
        [0.4475, 0.5376, 0.6936],
        [0.6439, 0.7182, 0.8323],
    ]


def test_a_step_outside_srgb_comes_back_by_css_gamut_mapping() -> None:
    """Green to blue in a straight line through Oklab leaves sRGB's range: halfway, its red
    falls below zero. CSS Color 4's mapping lowers its chroma, keeping its lightness and
    hue, until clipping it moves it less than a difference anyone sees."""
    spread = [colour_steps.spread(GREEN, BLUE, Fraction(k, 4))["components"] for k in (1, 2, 3)]
    assert spread == [[0.0, 0.8376, 0.5558], [0.0, 0.6572, 0.7289], [0.0, 0.4664, 0.8243]]


def test_alpha_is_premultiplied_as_css_color_4_interpolates() -> None:
    clear_red, half_red = srgb(1, 0, 0, alpha=0), srgb(1, 0, 0, alpha=0.5)
    assert colour_steps.spread(clear_red, BLUE, Fraction(1, 2)) == srgb(0, 0, 1, alpha=0.5)
    assert colour_steps.spread(half_red, BLUE, Fraction(1, 2)) == srgb(
        0.3963, 0.3047, 0.7613, alpha=0.75
    )


def test_each_component_and_the_alpha_is_rounded_to_ten_thousandths() -> None:
    first, last = srgb(0.2, 0.4, 0.6, alpha=0.8), srgb(0.9, 0.8, 0.1, alpha=0.4)
    assert colour_steps.spread(first, last, Fraction(1, 3)) == srgb(
        0.3411, 0.4885, 0.5655, alpha=0.6667
    )


def test_the_spread_needs_no_cube_root_newer_than_the_scripts_python(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The scripts declare Python 3.10, which has no `math.cbrt`: without it, a step between
    the ends and one the gamut mapping brings back keep their pinned values."""
    monkeypatch.delattr(math, "cbrt", raising=False)
    assert colour_steps.spread(BLACK, WHITE, Fraction(1, 2)) == srgb(0.3886, 0.3886, 0.3886)
    assert colour_steps.spread(GREEN, BLUE, Fraction(1, 2))["components"] == [0.0, 0.6572, 0.7289]


# --- a step's name --------------------------------------------------------------------------


def test_place_k_of_n_takes_the_share_k_less_one_over_n_less_one() -> None:
    shares = [colour_steps.placed(FIRST, LAST, k, 4).share for k in range(1, 5)]
    assert shares == [Fraction(0), Fraction(1, 3), Fraction(2, 3), Fraction(1)]
    assert colour_steps.placed(FIRST, LAST, 1, 1).share == 0
    names = [colour_steps.placed(FIRST, LAST, k, 3).name for k in (1, 2, 3)]
    assert names == [step("0"), step("1/2"), step("1")]


def test_a_step_is_read_back_from_its_name_and_no_role_reads_as_one() -> None:
    assert colour_steps.read(step("2/3")) == colour_steps.Step(FIRST, LAST, Fraction(2, 3))
    for named in (step("2/4"), step("3/2"), FIRST, "step(a,b)", None):
        assert not colour_steps.is_step(named)


def test_a_step_paints_as_a_family_its_text_the_orders_text() -> None:
    assert colour_steps.members(step("1/2"), TEXT) == {
        "fill": step("1/2"),
        "line": step("1/2"),
        "text": TEXT,
    }


def test_the_values_of_a_scene_s_steps_are_spread_from_its_combination_s_ends() -> None:
    run = {"text": "A", "fill": TEXT, "ground": step("1")}
    painted = scene(
        element("box", "figure/a", fill=step("1/2"), stroke=step("0")),
        element("text", "figure/t", paragraphs=[[run]]),
    )
    values = colour_steps.values_at(painted, {FIRST: BLACK, LAST: WHITE})
    assert values == {
        step("1/2"): srgb(0.3886, 0.3886, 0.3886),
        step("0"): BLACK,
        step("1"): WHITE,
    }
    assert colour_steps.values_at(painted, {FIRST: BLACK}) == {}


def test_a_step_one_of_whose_ends_has_no_colour_has_none_as_such_a_role_has() -> None:
    painted = scene(element("box", "figure/a", fill=step("1/2"), stroke=step("1")))
    assert colour_steps.values_at(painted, {FIRST: None, LAST: WHITE}) == {
        step("1/2"): None,
        step("1"): None,
    }


# --- a pattern gives a list's places their steps ----------------------------------------------

#: The pattern's switch of its places' families: blue under `plain`, the steps under `steps`.
STEPPED = {"by": "shade", "plain": "blue", "steps": ":steps"}

#: The colour families the foundations declare in these tests, and the concept that maps to
#: one of them.
FAMILIES = {
    name: {member: f"family.{name}.{member}" for member in ("fill", "line", "text")}
    for name in ("blue", "red", "grey")
}
CONCEPTS = {"sys/store": "red"}

ITEMS = {"items": {"type": "array", "items": {"type": "object"}}}


def card(**keys: Any) -> dict[str, Any]:
    """An item component that paints its box and its label from its family."""
    return block(
        {
            "b": {
                "box": {"fill": ":colour.fill", "stroke": ":colour.line"},
                "width": "=@space.1",
                "height": "=@space.1",
            },
            "t": {"text": {"content": "label", "style": "type.body", "fill": ":colour.text"}},
        },
        **{"fields": {"label": {"type": "string"}}, "states": {"marked": {"colour": "red"}}} | keys,
    )


def pattern(colour: Any = STEPPED, **keys: Any) -> dict[str, Any]:
    parts = {"items": {"repeat": "items", "draw": "lab/card", "colour": colour, "row": {}}}
    return top(parts, fields=ITEMS, options={"shade": ["plain", "steps"]}, **keys)


def components(**more: Any) -> dict[str, Any]:
    found = {"lab/top": pattern(), "lab/card": card(colour="grey"), "lab/bare": card()}
    return {**found, **{f"lab/{name}": each for name, each in more.items()}}


def stepped(*items: Any, shade: str = "steps", order: Any = None, **more: Any) -> Any:
    """The scene of the pattern over `items`, under the word `shade`, the order's roles those
    of `order`, or the foundations'."""
    return draw(
        {"shade": shade, "items": list(items)},
        components=components(**more),
        families=FAMILIES,
        concepts=CONCEPTS,
        order=Order() if order is None else order,
    )


def painted(result: Any, item: str, part: str = "b", prop: str = "fill") -> tuple[Any, Any]:
    found = result.scene.find(f"top/items[{item}]/{part}")
    assert found is not None, f"no element top/items[{item}]/{part}"
    return found.properties.get(prop), found.sources.get(prop)


def run_fill(result: Any, item: str) -> Any:
    found = result.scene.find(f"top/items[{item}]/t")
    assert found is not None
    [[run]] = found.properties["paragraphs"]
    return run["fill"]


def test_under_its_word_each_place_drawn_takes_its_step_and_a_concept_or_state_comes_first() -> (
    None
):
    """Five places are drawn, the item that names its own component among them, and the
    item that is no mapping left out, so the shares run 0, 1/4, 1/2, 3/4 and 1. The item that
    names a concept takes its concept's family, and the one in a state its state's."""
    result = stepped(
        {"id": "a", "label": "A"},
        {"id": "b", "label": "B", "concept": "sys/store"},
        "no item",
        {"id": "c", "label": "C", "state": "marked"},
        {"id": "d", "label": "D", "use": "lab/bare"},
        {"id": "e", "label": "E"},
    )

    assert codes(result) == ["content-shape"]
    assert painted(result, "a") == (step("0"), "option:shade")
    assert painted(result, "a", prop="stroke") == (step("0"), "option:shade")
    assert run_fill(result, "a") == TEXT
    assert painted(result, "b") == ("family.red.fill", "content:items[b].concept")
    assert painted(result, "c") == ("family.red.fill", "content:items[c].state")
    assert painted(result, "d") == (step("3/4"), "option:shade")
    assert painted(result, "e") == (step("1"), "option:shade")


def test_under_another_word_the_places_take_the_family_it_names() -> None:
    result = stepped({"id": "a", "label": "A"}, {"id": "b", "label": "B"}, shade="plain")

    assert result.findings == []
    assert painted(result, "a") == ("family.blue.fill", "option:shade")
    assert run_fill(result, "b") == "family.blue.text"


def test_a_list_of_one_place_takes_the_first_end() -> None:
    result = stepped({"id": "a", "label": "A"})
    assert painted(result, "a")[0] == step("0")


def test_an_outer_item_passes_its_step_to_what_sits_in_it() -> None:
    holder = block(
        {"in": {"use": "lab/bare", "width": "=:width", "height": "=@space.4"}},
        fields={"label": {"type": "string"}},
    )
    result = stepped(
        {"id": "a", "label": "A", "use": "lab/holder"},
        {"id": "b", "label": "B", "use": "lab/holder"},
        holder=holder,
    )

    found = result.scene.find("top/items[b]/in/b")
    assert found is not None
    assert found.properties["fill"] == step("1")


def test_under_foundations_with_no_ends_a_place_takes_no_step_and_the_lock_states_it() -> None:
    result = draw(
        {"shade": "steps", "items": [{"id": "a", "label": "A"}]},
        components=components(),
        families=FAMILIES,
    )

    assert painted(result, "a") == ("family.grey.fill", "default:lab/card")
    stated = [f for f in result.findings if f.code == layout.ORDER_NO_ENDS]
    assert [(f.level, f.where, f.extra) for f in stated] == [
        (findings.FACT, "lock", {"piece": True})
    ]
    assert "the list `items` of lab/top takes an order's steps by `shade: steps`" in (
        stated[0].message
    )


def test_a_list_drawn_more_than_once_under_foundations_with_no_ends_is_stated_once() -> None:
    """The pattern is drawn twice, as the items of an outer list: each of its lists takes no
    step and states so, and the drawing holds the one fact once."""
    listed = block(
        {"items": {"repeat": "items", "draw": "lab/card", "colour": STEPPED, "row": {}}},
        fields=ITEMS,
        options={"shade": ["plain", "steps"]},
    )
    rows = top(
        {"rows": {"repeat": "rows", "draw": "lab/list", "column": {}}},
        fields={"rows": {"type": "array", "items": {"type": "object"}}},
    )
    content = {
        "rows": [
            {"id": name, "shade": "steps", "items": [{"id": "a", "label": "A"}]}
            for name in ("x", "y")
        ]
    }
    result = draw(
        content, components=components(list=listed, rows=rows), families=FAMILIES, use="lab/rows"
    )

    for name in ("x", "y"):
        found = result.scene.find(f"rows/rows[{name}]/items[a]/b")
        assert found is not None
        assert found.properties["fill"] == "family.grey.fill"
    assert [f.code for f in result.findings] == [layout.ORDER_NO_ENDS]


def test_a_step_s_members_are_the_step_and_the_order_s_text_and_no_other() -> None:
    ctx = layout.Context(FakeEnv(order=Order()), "en")
    assert ctx.family(step("1/3")) == {"fill": step("1/3"), "line": step("1/3"), "text": TEXT}
    assert ctx.family("step(a,b,1/3)") is None
    assert layout.Context(FakeEnv(), "en").family(step("1/3")) is None


# --- what the checks fail -------------------------------------------------------------------


def issues(**more: Any) -> list[tuple[str, str]]:
    """The code and the key path of each finding on the components, read alone."""
    env = FakeEnv(components=components(**more), families=FAMILIES, order=Order())
    ctx = layout.Context(env, "en")
    for use in ("lab/top", *(f"lab/{name}" for name in more)):
        ctx.component(use)
    return [(f.code, f.where) for f in ctx.findings]


def test_an_order_named_where_a_family_is_named_is_a_finding_where_it_is_named() -> None:
    named = issues(
        top=pattern(colour={"by": "shade", "plain": "order", "steps": ":steps"}),
        own=card(colour="order"),
        stated=card(states={"marked": {"colour": FIRST}}),
        listed=pattern(colour="order"),
    )

    assert named == [
        (layout.ORDER_NAMED, "parts.items.colour.plain"),
        (layout.ORDER_NAMED, "colour"),
        (layout.ORDER_NAMED, "states.marked.colour"),
        (layout.ORDER_NAMED, "parts.items.colour"),
    ]


def test_a_library_s_part_that_paints_with_an_order_s_role_by_its_name_is_a_finding() -> None:
    by_name = block({"b": {"box": {"fill": FIRST}, "width": "=@space.1", "height": "=@space.1"}})
    ruled = block({"b": {"box": {"fill": {"by": "tone", "lit": LAST, "dim": "surface"}},
                         "width": "=@space.1", "height": "=@space.1"}},
                  options={"tone": ["lit", "dim"]})  # fmt: skip

    assert issues(swatch=by_name, ruled=ruled) == [
        (layout.ORDER_NAMED, "parts.b.box.fill"),
        (layout.ORDER_NAMED, "parts.b.box.fill.lit"),
    ]
    env = FakeEnv(components={"piece/swatch": by_name}, order=Order())
    ctx = layout.Context(env, "en")
    ctx.component("piece/swatch")
    assert ctx.findings == []


def test_a_word_that_gives_a_list_the_steps_names_no_family_for_any_place_of_it() -> None:
    def twice(other: dict[str, Any]) -> dict[str, Any]:
        parts = {
            "first": {"repeat": "items", "draw": "lab/card", "colour": STEPPED, "row": {}},
            "second": {"repeat": "items", "draw": "lab/card", "row": {}, **other},
        }
        return top(parts, fields=ITEMS, options={"shade": ["plain", "steps"], "tone": ["a", "b"]})

    clash = (layout.ORDER_STEPS_FAMILY, "parts.first.colour.steps")
    assert issues(top=twice({"colour": "blue"})) == [clash]
    assert issues(top=twice({"colour": {"by": "tone", "a": "blue", "b": None}})) == [clash]
    assert issues(top=twice({"colour": "blue", "when": {"shade": ["plain"]}})) == []
    assert issues(top=twice({"colour": {"by": "shade", "plain": "red", "steps": None}})) == []
    assert issues(top=twice({})) == []


@pytest.mark.parametrize(
    ("colour", "where", "said"),
    [
        (":steps", "parts.items.colour", "under no word"),
        ({"by": ":width", "default": ":steps"}, "parts.items.colour", "no option of words"),
        ({"by": "shade", "plain": {"by": "shade"}, "steps": ":steps"}, "parts.items.colour.plain",
         "holds a mapping"),
    ],
)  # fmt: skip
def test_a_switch_of_a_list_s_families_takes_the_steps_under_a_word_of_an_option(
    colour: Any, where: str, said: str
) -> None:
    env = FakeEnv(components={"lab/top": pattern(colour=colour)}, order=Order())
    ctx = layout.Context(env, "en")
    ctx.component("lab/top")
    [found] = ctx.findings
    assert (found.code, found.where) == ("component-shape", where)
    assert said in found.message


# --- the renderers draw a step from the value that comes with the scene ---------------------

#: A box filled with a step, and a line stroked with another, ending in an arrowhead.
STEPPED_SCENE = scene(
    element("box", "figure/a", x=0, y=0, width=20, height=10, fill=step("1/2")),
    element(
        "line", "figure/l", x=0, y=20, width=50, height=0, x1=0, y1=20, x2=50, y2=20,
        stroke=step("1"), **{"stroke-width": 2, "marker-end": "arrow"},
    ),
)  # fmt: skip

#: Each key's colours, with each step's value as the pipeline hands it.
LIGHT = {**COLOURS, step("1/2"): srgb(0.3886, 0.3886, 0.3886), step("1"): srgb(1, 1, 1)}
DARK = {**COLOURS, step("1/2"): srgb(0.2122, 0.2122, 0.2122), step("1"): srgb(0, 0, 0)}


def test_the_svg_and_the_pdf_renderer_paint_a_step_with_its_value_in_the_key_drawn() -> None:
    drawn = svg.render(
        STEPPED_SCENE, key="default", colours=LIGHT, font_file=lambda _f: FONT, pictures={}
    )
    [page] = drawn.pages
    assert 'fill="#636363"' in page.svg and 'stroke="#ffffff"' in page.svg
    assert drawn.losses == []

    printed = pdf.render(
        STEPPED_SCENE, key="default", colours=DARK, font_file=lambda _f: FONT, pictures={}
    )
    file, page_object = page_of(printed)
    assert "0.2122 0.2122 0.2122 rg" in file.content(page_object)
    assert printed.losses == []


KEYS = {"default": {"colour-scheme": "light"}, "colour-scheme.dark": {"colour-scheme": "dark"}}


def test_a_switching_file_marks_a_step_and_its_arrowhead_takes_an_id_of_its_own() -> None:
    drawn = svg.render(
        STEPPED_SCENE,
        form="svg-modes",
        keys=KEYS,
        colours={"default": LIGHT, "colour-scheme.dark": DARK},
        font_file=lambda _f: FONT,
        pictures={key: {} for key in KEYS},
    )
    [page] = drawn.pages
    assert f'data-fill="{step("1/2")}"' in page.svg
    assert 'marker-end="url(#pkit-arrow-end--_step-1)"' in page.svg
    assert f'[data-fill="{step("1/2")}"]{{fill:#363636;fill-opacity:1}}' in page.svg
    assert drawn.losses == []


def test_the_html_renderer_paints_each_step_with_a_custom_property_of_its_own() -> None:
    drawn = html.render(
        STEPPED_SCENE,
        form="html",
        keys=KEYS,
        colours={"default": LIGHT, "colour-scheme.dark": DARK},
        font_file=lambda _f: FONT,
        pictures={key: {} for key in KEYS},
    )
    page = drawn.document.decode()
    assert 'fill="var(--_step-1)"' in page and 'stroke="var(--_step-2)"' in page
    assert 'marker-end="url(#pkit-arrow-end--_step-2)"' in page
    assert ":root{color-scheme:light dark;--_step-2:#ffffff;--_step-1:#636363}" in page
    assert "@media (prefers-color-scheme:dark){:root{--_step-2:#000000;--_step-1:#363636}}" in (
        page
    )
    assert drawn.losses == []


#: Each key's colours where the order's first end has no colour in the dark scheme, so its
#: steps have none there, as the pipeline hands them.
UNLIT = {"default": LIGHT, "colour-scheme.dark": {**DARK, step("1/2"): None, step("1"): None}}


def test_a_file_of_both_keys_draws_a_step_with_no_colour_in_one_as_nothing_there() -> None:
    """Each renderer of a file that holds several keys reads a step with no colour in one of
    them as it reads such a role: it draws nothing there, and reports the loss there."""
    switching = svg.render(
        STEPPED_SCENE, form="svg-modes", keys=KEYS, colours=UNLIT, font_file=lambda _f: FONT,
        pictures={key: {} for key in KEYS},
    )  # fmt: skip
    [page] = switching.pages
    assert 'fill="#636363"' in page.svg
    assert f'[data-fill="{step("1/2")}"]{{fill:none}}' in page.svg
    assert f'[data-stroke="{step("1")}"]{{stroke:none}}' in page.svg

    page_file = html.render(
        STEPPED_SCENE, form="html", keys=KEYS, colours=UNLIT, font_file=lambda _f: FONT,
        pictures={key: {} for key in KEYS},
    )  # fmt: skip
    dark = "@media (prefers-color-scheme:dark){:root{--_step-2:transparent;--_step-1:transparent}}"
    assert dark in page_file.document.decode()

    lost = {("colour-scheme.dark", "figure/a"), ("colour-scheme.dark", "figure/l")}
    for drawn in (switching, page_file):
        assert {(loss.key, loss.what) for loss in drawn.losses} == lost


# --- a piece whose list takes the steps -----------------------------------------------------

#: A piece's own pattern of three cards, which takes the steps under `shade: steps`.
PIECE_PATTERN = bound(
    "component",
    status="experimental",
    about="Three cards in a row, which take an order's steps under `shade: steps`.",
    fields={"type": "object", "required": ["items"], "properties": ITEMS},
    options={"shade": ["plain", "steps"]},
    parts={
        "items": {
            "repeat": "items",
            "draw": "piece/card",
            "colour": {"by": "shade", "plain": "neutral", "steps": ":steps"},
            "width": "=:width",
            "row": {"gap": "=@space.2", "sizes": "equal", "align-items": "stretch"},
        }
    },
    preferred={"height": "=items.height"},
)
PIECE_CARD = bound(
    "component",
    status="experimental",
    about="A card of its family, its name on it.",
    fields={
        "type": "object",
        "required": ["name"],
        "properties": {"name": {"type": "string", "x-pkit-prose": True}},
    },
    parts={
        "box": {"box": {"fill": ":colour.fill"}, "width": "=:width", "height": "=:height"},
        "name": {
            "text": {"content": "name", "style": "type.body", "fill": ":colour.text"},
            "x": "=@space.2",
            "y": "=@space.2",
            "width": "=:width - 2 * @space.2",
        },
    },
    preferred={"height": "=name.bottom + @space.2"},
)


#: A version listed as not released yet.
UNRELEASED = {"released": False}


def ordered_project(
    tmp_path: Path, text: str = "{text-primary}", exports: tuple[str, ...] = ()
) -> Any:
    """The foundations being built, which declare an order's roles, the test brand, which
    gives the order its ends, blue first and the surface last, and its text, `text`, and the
    piece `ordered`: the pattern over three cards under `shade: steps`, in both colour
    schemes, exported as `exports` says."""
    root = project(tmp_path)
    copy_library(root, FOUNDATIONS, "foundations", "1.2.0")
    brand = copy_library(root, TEST_BRAND, "test-brand", "1.0.0")
    tokens = brand / "tokens" / "base.tokens.json"
    given = tokens.read_text(encoding="utf-8").replace(
        '"neutral": {',
        '"order": {"first": {"$value": "{scheme.blue.fill}"}, "last": {"$value": "{surface}"}, '
        f'"text": {{"$value": "{text}"}}}},\n    "neutral": {{',
        1,
    )
    tokens.write_text(given, encoding="utf-8")
    write_list(
        root,
        {
            "foundations": {"source": {"kind": "shipped"}, "versions": {"1.2.0": UNRELEASED}},
            "test-brand": {"source": {"kind": "project"}, "versions": {"1.0.0": UNRELEASED}},
        },
    )
    write_piece(
        root,
        "ordered",
        modes={"colour-scheme": ["light", "dark"]},
        lock={"foundations": "1.2.0", "test-brand": "1.0.0"},
        exports=list(exports),
    )
    folder = root / "visual" / "pieces" / "ordered"
    write(folder / "components" / "pattern.yaml", yaml_text(PIECE_PATTERN))
    write(folder / "components" / "card.yaml", yaml_text(PIECE_CARD))
    cards = [{"id": name, "name": name.title()} for name in ("source", "middle", "sink")]
    body = {"use": "piece/pattern", "shade": "steps", "items": cards}
    write(folder / "content.en.yaml", yaml_text(bound("content", body=body, caption="An order.")))
    piece = pl.read_piece(root, "visual", "ordered")
    return pl.Project(piece, piece.lock, pl.Held(root, "visual"))


def test_a_piece_s_steps_come_with_its_scene_in_each_mode_and_are_drawn_from_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    importable(monkeypatch, html)
    project = ordered_project(tmp_path)
    results = project.scenes(facts=project.piece.stand_ins)
    [(_, result)] = results
    fills = [
        result.scene.find(f"figure/body/items[{name}]/box").properties["fill"]
        for name in ("source", "middle", "sink")
    ]
    assert fills == [step("0"), step("1/2"), step("1")]

    document = project.values()
    for key in ("default", "colour-scheme.dark"):
        colours = pl.colours_at(document, key, result.scene.to_dict())
        ends = colours["family.order.first"], colours["family.order.last"]
        assert colours[step("1/2")] == colour_steps.spread(*ends, Fraction(1, 2))
        assert colours[step("0")] == colour_steps.spread(*ends, Fraction(0))
        assert step("1/2") not in pl.colours_at(document, key)
    assert (
        colours[step("1/2")]
        != pl.colours_at(document, "default", result.scene.to_dict())[step("1/2")]
    )

    [(_, _, page_file)] = list(pl.drawn(project, results, "html"))
    assert "--_step-2:" in page_file.document.decode()
    assert page_file.losses == []
    assert [f for f in checks.scene_findings(project, results) if f.level != findings.FACT] == []


def test_the_check_measures_a_text_on_a_step_in_the_step_s_value(tmp_path: Path) -> None:
    """The order's text as the surface, the last end, vanishes on the last card in every
    combination: the check measures each text on a step as drawn, in the value that comes
    with the scene."""
    project = ordered_project(tmp_path, text="{surface}")
    results = project.scenes(facts=project.piece.stand_ins)

    failed = [f for f in checks.scene_findings(project, results) if f.code == checks.CONTRAST_DRAWN]

    on_sink = [f.message for f in failed if f.where == "figure/body/items[sink]/name"]
    assert len(on_sink) == 2
    assert all(f"`{TEXT}` on `{step('1')}` has the contrast 1.00" in each for each in on_sink)


# --- a step with no colour in one mode ------------------------------------------------------

DARK_KEY = "colour-scheme.dark"


def test_the_check_measures_what_lies_under_a_step_with_no_colour_in_a_mode() -> None:
    """In the dark scheme the step has no colour, so it draws nothing there: a text on it is
    measured against the paper under it, a text painted with it is not measured there, and
    a sign filled with it is measured in its stroke alone."""
    half = step("1/2")
    colours = {
        "paper": {"default": WHITE, DARK_KEY: BLACK},
        "ink": {"default": BLACK, DARK_KEY: srgb(0.1, 0.1, 0.1)},
        half: {"default": srgb(0.9, 0.9, 0.9), DARK_KEY: None},
    }
    sign = {"type": "path", "id": "figure/sign", "x": 200, "y": 40, "width": 20, "height": 20,
            "d": "M0 0L20 20", "fill": half, "stroke": "ink", "stroke-width": 1}  # fmt: skip
    shown = page(
        box("figure/back", "paper"),
        box("figure/step", half),
        text("figure/on", "ink"),
        text("figure/with", half, x=120),
        sign,
    )

    found = checks.drawn_contrast(shown, colours, ["default", DARK_KEY])

    assert [(f.where, f.message.split(", ")[0]) for f in found] == [
        ("figure/on", f"`ink` on `paper` has the contrast 1.20 in the combination `{DARK_KEY}`"),
        ("figure/with", f"`{half}` on `{half}` has the contrast 1.00 in the combination `default`"),
        ("figure/sign", f"the sign paints `ink` (1.20) on `paper` in the combination `{DARK_KEY}`"),
    ]


def test_where_an_end_has_no_colour_in_one_mode_the_steps_have_none_and_the_check_reads_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The first end has no colour in the dark scheme, so no step has one there. The pipeline
    hands each step there as None, as a role with none, and the switching file draws it as
    nothing there. The check reads every step in each mode, so its measure of each card's
    name, and its look at a page's own ground for a switching file, read them too."""
    importable(monkeypatch, svg)
    project = ordered_project(tmp_path, exports=("svg-modes",))
    document = project.values()
    document["tokens"][FIRST]["values"][DARK_KEY] = None
    results = project.scenes(facts=project.piece.stand_ins)
    [(_, result)] = results
    shown = result.scene.to_dict()

    assert pl.colours_at(document, DARK_KEY, shown)[step("1/2")] is None
    assert pl.colours_at(document, "default", shown)[step("1/2")] is not None
    [(_, _, switching)] = list(pl.drawn(project, results, "svg", form="svg-modes"))
    assert {(loss.key, loss.what) for loss in switching.losses} == {
        (DARK_KEY, f"figure/body/items[{name}]/box") for name in ("source", "middle", "sink")
    }
    assert [f for f in checks.scene_findings(project, results) if f.level != findings.FACT] == []
