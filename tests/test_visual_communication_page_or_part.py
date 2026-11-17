"""A drawing of a layout chooses by whether its instance is a page (visual-communication
DEC-034 point 7; #3022).

A drawing of a layout, the top's own or a brand's, reads the marked name `:as` in a switch
or a `when`: `page`, its default, where its instance is a page, and `part` where the
instance lies inside another page. The engine sets it from where the instance lies, never
from content, and a value a switch by it chose names `:as` as its source.

- a page alone, drawn by its own drawing or by a brand's, draws its page-only parts as the
  piece's top, and leaves them out placed in a slide's slot;
- a value the switch does not name takes the default's branch;
- each page of a deck is a page;
- what is refused: `:as` read by a component that is no drawing of a layout, a value it
  does not take, a switch that leaves out the default, and a branch that switches again;
- beside a part over the same list whose `when` reads a size, a part whose `when` reads
  `:as` may be drawn where it draws as either value;
- a drawing that reads no `:as` draws alike as a page and as a part.

The engine's rules are drawn from components written as mappings in memory (`FakeEnv`);
the check of a brand's drawing from the deck project of the drawings' tests.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest

from tests.test_visual_communication_drawings import cover, deck, judged
from tests.test_visual_communication_sizes import DEVICE, LISTED, ON_DESKTOP, item
from tests.visual_engine import COMPONENTS, FakeEnv, block, codes, draw, frame, layout, top

#: Drawn where its instance is a page, and left out where it is part of one.
ON_A_PAGE = {"by": ":as", "page": True, "part": False}

CAPTION = {
    "text": {"content": "caption", "style": "type.body", "fill": "text-primary"},
    "width": "=:width",
}

#: A backdrop as large as its instance.
BACKDROP = {"box": {"fill": "surface"}, "width": "=:width", "height": "=:height"}


def dressed(**caption: Any) -> dict[str, Any]:
    """A page alone's drawing: a backdrop drawn only where its instance is a page, and the
    caption, to which `caption` adds."""
    return {"backdrop": {**BACKDROP, "when": ON_A_PAGE}, "caption": {**CAPTION, **caption}}


def poster(parts: dict[str, Any]) -> dict[str, Any]:
    """`lab/top`, a page alone that takes a caption, drawn by `parts`."""
    return top(parts, fields={"caption": {"type": "string"}})


def look(parts: dict[str, Any]) -> dict[str, Any]:
    """A brand's drawing of `lab/top`'s one layout, drawn by `parts`."""
    return {
        "about": "A brand's drawing a test draws.",
        "draws": {"top": "lab/top", "layout": "frame"},
        "parts": parts,
        "preferred": {"width": "=@size.figure", "height": "=@space.4"},
    }


CHOICE = layout.Choice({("lab/top", "frame"): "brand/look"})

#: Where a slide of the deck places `lab/top`.
SLOT = "deck/slides[s]/visual"


def on_a_slide() -> dict[str, Any]:
    """A deck of one slide, whose visual is `lab/top`."""
    visual = {"use": "lab/top", "caption": "Placed."}
    return {"slides": [{"id": "s", "layout": "slide", "title": "A slide", "visual": visual}]}


def alone_and_placed(components: dict[str, Any], choice: Any = None) -> tuple[Any, Any]:
    """The scene of `lab/top` as the piece's top, and of a deck that places it in a slide's
    slot, each drawn as `choice` says."""
    alone = draw({"caption": "Alone."}, components=components, choice=choice)
    placed = draw(on_a_slide(), use="foundations/deck", components=components, choice=choice)
    return alone, placed


def found(result: Any, trace: str) -> Any:
    element = result.scene.find(trace)
    assert element is not None, f"no element {trace}"
    return element


# --- page or part -------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("components", "choice", "drawn_by"),
    [
        pytest.param({"lab/top": poster(dressed())}, None, "lab/top", id="its-own-drawing"),
        pytest.param(
            {"lab/top": poster({"caption": CAPTION}), "brand/look": look(dressed())},
            CHOICE,
            "brand/look",
            id="a-brands-drawing",
        ),
    ],
)
def test_a_page_alone_draws_its_page_only_parts_as_the_top_and_none_in_a_slot(
    components: dict[str, Any], choice: Any, drawn_by: str
) -> None:
    alone, placed = alone_and_placed(components, choice)

    assert codes(alone) == codes(placed) == []
    assert found(alone, "top").properties["component"] == drawn_by
    assert found(placed, SLOT).properties["component"] == drawn_by
    assert alone.scene.find("top/backdrop") is not None
    assert placed.scene.find(f"{SLOT}/backdrop") is None
    assert found(placed, f"{SLOT}/caption").properties["text"] == "Placed."


def test_a_value_chosen_by_as_names_it_as_its_source() -> None:
    """The engine sets `:as` to `page` for the piece's top and to `part` inside a slide,
    and a value it chose names `:as`, a kind of its own (DEC-005 point 5)."""
    by_place = {"by": ":as", "page": "=@space.4", "part": "=@space.1"}
    alone, placed = alone_and_placed({"lab/top": poster({"caption": {**CAPTION, "x": by_place}})})

    assert codes(alone) == codes(placed) == []
    assert frame(alone, "top/caption")[0] == 32.0
    assert frame(placed, f"{SLOT}/caption")[0] == 4.0
    assert found(alone, "top/caption").sources["x"] == layout.AS
    assert found(placed, f"{SLOT}/caption").sources["x"] == layout.AS


def test_a_value_the_switch_does_not_name_takes_the_defaults_branch() -> None:
    parts = {
        "mark": {**BACKDROP, "when": {"by": ":as", "page": True}},
        "caption": {**CAPTION, "x": {"by": ":as", "page": "=@space.4"}},
    }
    _, placed = alone_and_placed({"lab/top": poster(parts)})

    assert codes(placed) == []
    assert placed.scene.find(f"{SLOT}/mark") is not None
    assert frame(placed, f"{SLOT}/caption")[0] == 32.0


def test_each_page_of_a_deck_is_a_page() -> None:
    """A page of a top whose layouts are its pages' forms lies inside no page."""
    deck_data = copy.deepcopy(COMPONENTS["foundations/deck"])
    deck_data["layouts"]["cover"]["parts"]["rule"]["when"] = ON_A_PAGE
    result = draw(
        {"slides": [{"id": "c", "layout": "cover", "title": "A cover"}]},
        use="foundations/deck",
        components={"foundations/deck": deck_data},
    )

    assert codes(result) == []
    assert result.scene.find("deck/slides[c]/rule") is not None


def test_a_drawing_that_reads_no_as_draws_alike_as_a_page_and_as_a_part() -> None:
    parts = {"backdrop": BACKDROP, "caption": CAPTION}
    alone, placed = alone_and_placed({"lab/top": poster(parts)})

    assert codes(alone) == codes(placed) == []
    for part in parts:
        assert found(alone, f"top/{part}").properties.keys() == (
            found(placed, f"{SLOT}/{part}").properties.keys()
        )


# --- what is refused ------------------------------------------------------------------------


def issues(component: dict[str, Any], *, use: str = "lab/top") -> list[tuple[str, str, str]]:
    """What reading `component` as `use` finds, beside `lab/top` as a page alone."""
    env = FakeEnv(components={"lab/top": poster({"caption": CAPTION}), use: component})
    read = layout.Context(env, "en").component(use)
    assert read is not None
    return read.issues


@pytest.mark.parametrize(
    ("component", "where", "said"),
    [
        pytest.param(
            block({"b": {**BACKDROP, "when": ON_A_PAGE}}),
            "parts.b.when",
            "`when` switches on `:as`, which only a drawing of a layout reads",
            id="a-when-in-a-block",
        ),
        pytest.param(
            block({"b": {**BACKDROP, "x": {"by": ":as", "page": "=0", "part": "=@space.1"}}}),
            "parts.b.x",
            "switches on `:as`, which only a drawing of a layout reads",
            id="a-switch-in-a-block",
        ),
        pytest.param(
            poster({"b": {**BACKDROP, "when": {"by": ":as", "part": True}}}),
            "parts.b.when",
            "names no branch for `page`, its default",
            id="no-default",
        ),
        pytest.param(
            poster({"b": {**BACKDROP, "when": {"by": ":as", "page": True, "slide": False}}}),
            "parts.b.when.slide",
            "names `slide`, which is no value of it (its values: page, part)",
            id="a-value-it-does-not-take",
        ),
        pytest.param(
            poster({"b": {**BACKDROP, "x": {"by": ":as", "page": "=0", "sheet": "=0"}}}),
            "parts.b.x.sheet",
            "names `sheet`, which is no value of it",
            id="a-switch-with-a-value-it-does-not-take",
        ),
    ],
)
def test_a_switch_by_as_that_breaks_its_rules_fails(
    component: dict[str, Any], where: str, said: str
) -> None:
    found_here = [
        (w, m) for code, w, m in issues(component, use="lab/b") if code == layout.AS_SWITCH
    ]

    assert [w for w, _ in found_here] == [where]
    assert said in found_here[0][1]


def test_a_branch_of_a_when_by_as_switches_no_further() -> None:
    again = {"by": ":as", "page": {"by": ":as", "page": True}}
    found_here = issues(poster({"b": {**BACKDROP, "when": again}}), use="lab/b")

    assert [(code, where) for code, where, _ in found_here] == [
        ("component-shape", "parts.b.when.page")
    ]
    assert "a branch of a `when` by `:as` takes `true`, `false`, a field" in found_here[0][2]


def test_a_brands_drawing_reads_as_and_a_scene_fails_a_component_that_is_no_drawing() -> None:
    """In a brand's drawing `:as` is read; in a block the scene's finding fails."""
    assert issues(look(dressed()), use="brand/look") == []
    holder = block({"b": {**BACKDROP, "when": ON_A_PAGE}})
    result = draw(components={"lab/holder": holder}, use="lab/holder")

    [finding] = [f for f in result.findings if f.code == layout.AS_SWITCH]
    assert (finding.level, finding.where, finding.extra) == (
        "fails",
        "parts.b.when",
        {"component": "lab/holder"},
    )


@pytest.mark.parametrize(
    ("down", "said"),
    [
        pytest.param(
            {"by": ":as", "page": False, "part": True},
            "at `desktop` of `device` 2 of them may be drawn",
            id="drawn-as-a-part",
        ),
        pytest.param(
            {"by": ":as", "page": False},
            "at `phone` of `device` 0 of them may be drawn",
            id="drawn-as-neither",
        ),
    ],
)
def test_a_part_over_a_list_whose_when_reads_as_counts_where_either_value_draws_it(
    down: dict[str, Any], said: str
) -> None:
    """Beside a part over the same list whose `when` reads a size, a part whose `when` reads
    `:as` may be drawn at a mode where it draws as a page or as a part, since its instance
    may lie as either (DEC-021 point 4)."""
    parts = {
        "across": {"repeat": "items", "draw": "lab/item", "when": ON_DESKTOP, "row": {}},
        "down": {"repeat": "items", "draw": "lab/item", "when": down, "column": {}},
    }
    env = FakeEnv(components={"lab/top": top(parts, fields=LISTED), "lab/item": item()})
    sizes = layout.Sizes({"device": DEVICE})
    read = layout.Context(env, "en", sizes=sizes).component("lab/top")
    assert read is not None

    [message] = [m for code, _, m in read.issues if code == layout.SIZE_REPEAT]
    assert said in message


# --- the check ----------------------------------------------------------------------------------


def test_the_brand_checked_alone_judges_its_drawings_reading_of_as(tmp_path: Path) -> None:
    """A drawing of the deck's cover that reads `:as` passes where its brand is checked
    alone, and one that leaves out the default fails in its own file."""
    reads = {"by": ":as", "page": "author", "part": False}
    root = deck(tmp_path / "reads", drawing=cover(parts__author__when=reads))
    assert judged(root, layout.AS_SWITCH) == []

    no_default = {"by": ":as", "part": "author"}
    root = deck(tmp_path / "no-default", drawing=cover(parts__author__when=no_default))
    assert judged(root, layout.AS_SWITCH) == [
        ("fails", "visual/libraries/test-brand/1.1.0/components/cover.yaml", "parts.author.when")
    ]
