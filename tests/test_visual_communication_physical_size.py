"""A top's physical size (visual-communication DEC-034 point 3): which components declare
one, the height the engine sets from it, wherever its top lies, and the scene's root, which
holds the physical size of the piece's top.

Each case is drawn in this process through `tests/visual_engine.py`, in components of the
tests' own written in memory. The width the tops ask for is the figure's role, 640 px."""

from __future__ import annotations

from typing import Any

import pytest

from tests.visual_engine import block, codes, draw, frame, top

#: A poster's trim size, A1 upright, in millimetres.
A1 = {"width": 594, "height": 841}

#: The width each top here asks for (`size.figure`), and the height A1 gives it.
WIDTH = 640
HEIGHT = round(WIDTH * 841 / 594, 2)

#: A component that paints a box over all it is given and asks for a fixed height.
FILL = {"box": {"fill": "surface"}, "width": "=:width", "height": "=:height"}


def poster(**keys: Any) -> dict[str, Any]:
    """A page alone at A1 that asks for its width alone; `keys` add to it or replace its
    defaults."""
    defaults = {"preferred": {"width": "=@size.figure"}, "physical-size": A1}
    return top({"back": FILL}, **{**defaults, **keys})


def handout(**keys: Any) -> dict[str, Any]:
    """A top whose layouts are its pages' forms, at A1, its one layout `sheet` drawing a box
    over its whole page."""
    sheet = {"slots": {"title": {"type": "string"}}, "parts": {"back": FILL}}
    return {
        "status": "experimental",
        "about": "A handout a test draws, each page printed at A1.",
        "fields": {
            "type": "object",
            "properties": {"pages": {"type": "array", "x-pkit-pages": True}},
        },
        "layouts": {"sheet": sheet},
        "preferred": {"width": "=@size.figure"},
        "physical-size": A1,
        **keys,
    }


def pages(*ids: str) -> dict[str, Any]:
    return {"pages": [{"id": id_, "layout": "sheet", "title": id_} for id_ in ids]}


def physical_findings(result: Any) -> list[str]:
    """Where each finding on a physical size lies."""
    return [finding.where for finding in result.findings if finding.code == "physical-size"]


# --- a page alone -------------------------------------------------------------------------------


def test_a_page_alone_is_as_tall_as_its_width_in_the_sizes_proportion() -> None:
    result = draw(components={"lab/top": poster()})
    assert codes(result) == []
    assert frame(result, "top") == (0, 0, WIDTH, HEIGHT)
    element = result.scene.find("top")
    assert element is not None
    assert element.sources["width"] == "role:size.figure"
    assert element.sources["height"] == "engine"


def test_the_root_holds_the_physical_size_of_the_pieces_top() -> None:
    root = draw(components={"lab/top": poster()}).scene.to_dict()
    assert root["physical-size"] == A1
    assert root["fixed-pages"] is False  # a page alone is no fixed page (DEC-031 point 2)
    assert root["pages"] == ["top"]


def test_a_size_in_another_unit_of_the_same_proportion_draws_the_same_scene() -> None:
    """Only the proportion sets the height: a size changed in the same proportion draws every
    element where it was, and the root alone names the other size."""
    half = {"width": 297, "height": 420.5}
    a1 = draw(components={"lab/top": poster()}).scene.to_dict()
    a2 = draw(components={"lab/top": poster(**{"physical-size": half})}).scene.to_dict()
    assert a2["children"] == a1["children"]
    assert a2["physical-size"] == half


# --- a top whose layouts are its pages' forms ---------------------------------------------------


def test_each_page_gets_the_height_the_proportion_gives_the_tops_width() -> None:
    result = draw(pages("one", "two"), use="lab/handout", components={"lab/handout": handout()})
    assert codes(result) == []
    for id_ in ("one", "two"):
        trace = f"handout/pages[{id_}]"
        assert frame(result, trace) == (0, 0, WIDTH, HEIGHT)
        element = result.scene.find(trace)
        assert element is not None
        assert element.sources["height"] == "engine"
    assert frame(result, "handout") == (0, 0, WIDTH, HEIGHT)
    root = result.scene.to_dict()
    assert (root["fixed-pages"], root["physical-size"]) == (True, A1)


def test_a_layout_may_ask_for_its_pages_height_and_one_that_asks_for_more_gets_less() -> None:
    """The top asks for a height through its physical size, so a layout need not say one, and
    one that says more than the page gets is reported as any element is (DEC-005 point 14)."""
    tall = handout()
    tall["layouts"]["sheet"]["preferred"] = {"height": "=@size.figure * 2"}
    result = draw(pages("one"), use="lab/handout", components={"lab/handout": tall})
    assert codes(result) == ["gets-less"]
    assert result.findings[0].where == "handout/pages[one]"
    assert frame(result, "handout/pages[one]") == (0, 0, WIDTH, HEIGHT)


# --- where it may lie ---------------------------------------------------------------------------


def test_a_top_that_asks_for_a_height_by_a_formula_fails() -> None:
    both = poster(preferred={"width": "=@size.figure", "height": "=@space.4"})
    result = draw(components={"lab/top": both})
    assert physical_findings(result) == ["preferred.height"]
    assert frame(result, "top")[3] == HEIGHT  # the proportion sets it all the same


def test_a_component_that_is_no_top_declares_no_physical_size() -> None:
    """A drawing is such a component: it declares no layouts (DEC-034 point 1)."""
    panel = block({"back": FILL}, **{"physical-size": A1})
    result = draw({"body": {"use": "lab/panel"}}, components={
        "lab/top": top({"body": {"slot": "body", "width": "=:width"}}, fields={"body": {}}),
        "lab/panel": panel,
    })  # fmt: skip
    assert physical_findings(result) == ["physical-size"]
    # It asks for the height its `preferred` says, as though it declared no size.
    assert frame(result, "top/body")[3] == 32


def test_a_top_whose_slot_holds_pages_declares_no_physical_size() -> None:
    book = top(
        {"body": {"slot": "body", "width": "=:width"}},
        fields={"body": {}},
        layouts={"frame": {"slots": {"body": {"pages": True}}}},
        **{"physical-size": A1},
    )
    result = draw(components={"lab/top": book})
    assert physical_findings(result) == ["physical-size"]
    assert result.scene.to_dict()["physical-size"] is None


@pytest.mark.parametrize(
    "value",
    [
        {"width": 0, "height": 841},
        {"width": 594, "height": -1},
        {"width": "594", "height": 841},
        {"width": True, "height": 841},
        {"width": 594},
        {"width": 594, "height": 841, "unit": "in"},
        "a1",
    ],
)
def test_a_physical_size_that_is_not_two_positive_numbers_fails(value: Any) -> None:
    result = draw(components={"lab/top": poster(**{"physical-size": value})})
    assert "physical-size" in physical_findings(result)
    assert result.scene.to_dict()["physical-size"] is None


# --- placed elsewhere ---------------------------------------------------------------------------


def test_placed_in_a_slot_it_asks_for_its_size_as_alone_and_gets_what_its_placer_gives() -> None:
    """Its height still follows the proportion, and only the piece's top prints at its size.
    One given half the width it asks for is reported as any element is (DEC-005 point 14)."""
    holder = top(
        {
            "asked": {"slot": "asked"},
            "given": {"slot": "given", "y": "=asked.bottom", "width": "=:width / 2"},
        },
        fields={"asked": {}, "given": {}},
        preferred={"width": "=@size.figure", "height": "=given.bottom"},
    )
    content = {"asked": {"use": "lab/poster"}, "given": {"use": "lab/poster"}}
    result = draw(content, components={"lab/top": holder, "lab/poster": poster()})
    assert [(f.code, f.where) for f in result.findings] == [("gets-less", "top/given")]
    assert "of width" in result.findings[0].message
    assert frame(result, "top/asked") == (0, 0, WIDTH, HEIGHT)
    assert frame(result, "top/given")[2:] == (WIDTH / 2, HEIGHT)
    element = result.scene.find("top/asked")
    assert element is not None
    assert element.sources["height"] == "engine"
    assert result.scene.to_dict()["physical-size"] is None


def test_a_page_of_another_top_drawn_by_it_gets_that_tops_size() -> None:
    """A page drawn by its own component, under a top that asks for a height, gets the top's,
    and asks for its own height in its proportion."""
    deck = handout(**{"physical-size": {"width": 1000, "height": 1000}})
    content = {"pages": [{"id": "poster", "use": "lab/poster"}]}
    components = {"lab/handout": deck, "lab/poster": poster()}
    result = draw(content, use="lab/handout", components=components)
    assert codes(result) == ["gets-less"]  # it asks for HEIGHT, and gets a square
    assert frame(result, "handout/pages[poster]") == (0, 0, WIDTH, WIDTH)
    assert result.scene.to_dict()["physical-size"] == {"width": 1000, "height": 1000}
