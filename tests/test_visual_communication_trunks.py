"""Ties that share a trunk, where the part that draws their list declares a trunk end
(visual-communication DEC-043; #3083).

Each rule is drawn from components written as mappings in memory and read through an
in-memory `Env` (`tests/visual_engine.py`), on one page: cards laid in a column on the left,
each tied to one slot on the right, so their `to` ends meet the slot's left side.

- the junctions' places: the even places where they fit, else the least places, and none
  where nothing fits, checked against every place on a fine grid;
- two and three ties on one side, with a trunk and without, each tie a line of its own from
  end to end, drawn by the SVG renderer and the PDF renderer;
- a group that cannot be drawn clear, drawn spread and stated: no room, two of its ties that
  would cross, a crossing it would add, and a part placed by the measures that does not fit;
- ties that form no group: drawn otherwise, one drawing a part the other does not, a
  straight part beside one with corners, a radius that reads a line's frame, stated;
  straight and alike, drawing as without a trunk, and nothing said;
- the two measures of a line's own stretch, which read the frame's centre on a line that
  shares nothing, and a part placed by them, kept off the stretch its tie shares;
- a part placed otherwise that stands on a shared stretch, found in its component;
- a cell computed aside while a group is judged, forgotten even above the instance;
- a `trunk` on a list of no ties, naming no end field, or as a switch, refused, and an own
  measure of what is no line.
"""

from __future__ import annotations

import itertools
from typing import Any

import pytest

from tests.in_process import load
from tests.test_visual_communication_pdf import page_of
from tests.test_visual_communication_ties import (
    COLOURS,
    LISTED,
    SHAPE,
    card,
    finding,
    issues,
    lab,
    link,
    rendered,
)
from tests.visual_engine import FakeEnv, block, codes, draw, layout, top

trunks, pdf = load("visual-communication", "trunks", "plugins.pdf")

FACT = "fact"
SPREAD = "trunk-spread"
UNGROUPED = "trunk-ungrouped"
PART = "trunk-part"


# --- where the junctions lie ------------------------------------------------------------------


def cost(places: tuple[float, ...], length: float) -> float:
    """How far places lie from their even places, as the sum of the squares."""
    count = len(places)
    return sum((place - length * (at + 1) / (count + 1)) ** 2 for at, place in enumerate(places))


def keeps(
    places: tuple[float, ...], start: float, end: float, gap: float, limits: list[float]
) -> bool:
    """Whether places keep the junction span, the least gap and each branch's limit."""
    near = 1e-9
    return (
        places[0] >= start - near
        and places[-1] <= end + near
        and all(b - a >= gap - near for a, b in itertools.pairwise(places))
        and all(place <= limit + near for place, limit in zip(places, limits, strict=True))
    )


def test_the_junctions_take_their_even_places_where_they_fit() -> None:
    assert trunks.junctions(21, 232, 8, [208, 208], 240) == (80, 160)
    assert trunks.junctions(21, 104, 8, [208], 120) == (60,)


def test_a_junction_short_of_its_even_place_moves_only_as_its_limit_forces() -> None:
    # The first branch's far end lies close across, so it leaves at its limit, and the
    # second keeps its even place.
    assert trunks.junctions(21, 232, 8, [40, 208], 240) == (40, 160)


@pytest.mark.parametrize(
    ("start", "end", "gap", "limits", "length", "step"),
    [
        # The first even place lies within the span's start, the next beyond a limit.
        (60, 232, 8, [208, 70], 240, 0.5),
        # The first junction's limit lies below the second's even place.
        (10, 100, 5, [20, 200], 60, 0.25),
        # Three neighbours pressed together by the limit of the second.
        (21, 232, 30, [208, 60, 208], 240, 2),
    ],
)
def test_the_junctions_take_the_least_places_where_the_even_places_do_not_fit(
    start: float, end: float, gap: float, limits: list[float], length: float, step: float
) -> None:
    """The least places keep all four, and no places on a grid of `step` px that keep them
    lie nearer the even places, by the sum of the squares."""
    found = trunks.junctions(start, end, gap, limits, length)
    assert found is not None
    assert keeps(found, start, end, gap, limits)
    grid = [at * step for at in range(int(length / step) + 1)]
    best = min(
        cost(places, length)
        for places in itertools.combinations(grid, len(limits))
        if keeps(places, start, end, gap, limits)
    )
    assert cost(found, length) <= best + 1e-9


def test_no_junctions_fit_where_no_places_keep_the_span_the_gap_and_the_limits() -> None:
    # Two junctions 8 px apart from 21 px on, and the second may lie no farther than 24.
    assert trunks.junctions(21, 32, 8, [24, 24], 40) is None
    # The span is shorter than its own start.
    assert trunks.junctions(21, 16, 8, [208], 24) is None


# --- the page the ties are drawn on -----------------------------------------------------------


def arrow(connect: Any = "corners", **parts: Any) -> dict[str, Any]:
    """A component that takes ends and draws a connector between them, with corners at a
    radius of 8 px and an arrowhead at its end, and `parts` beside it."""
    line = {"stroke": "line", "rx": "=@space.2", "marker-end": "arrow"}
    return block({"l": {"line": line, "connect": connect}, **parts}, ends=True)


def tag(x: str, y: str, width: str = "=@space.2", height: str = "=@space.2") -> dict[str, Any]:
    """A box a tie's component draws beside its line."""
    return {"box": {"fill": "surface"}, "x": x, "y": y, "width": width, "height": height}


#: A tag placed halfway along its line's own stretch, and one at the centre of its frame.
BY_MEASURES = tag("=l.own-center - t.width / 2", "=l.own-middle - t.height / 2")
BY_FRAME = tag("=l.center - t.width / 2", "=l.middle - t.height / 2")


def pattern(trunk: Any = None, *, slot_y: str = "=@space.4 * 2", **more: Any) -> dict[str, Any]:
    """A top whose `steps` lie in a column 32 px apart, whose one slot lies 272 px across,
    and whose `links` it draws with `lab/arrow`, sharing a trunk at `trunk` where it names
    one. The cards are 32 px square."""
    links: dict[str, Any] = {"repeat": "links", "draw": "lab/arrow"}
    if trunk is not None:
        links["trunk"] = trunk
    parts = {
        "steps": {
            "repeat": "steps",
            "draw": "lab/card",
            "column": {"gap": more.pop("gap", "=@space.4")},
        },
        "slots": {
            "repeat": "slots",
            "draw": "lab/card",
            "row": {},
            "x": more.pop("slot_x", "=@space.4 * 8.5"),
            "y": slot_y,
        },
        **more.pop("parts", {}),
        "links": links,
    }
    return top(
        parts,
        fields={"steps": LISTED, "slots": LISTED, "links": LISTED, "marks": LISTED},
        lists={"links": {"ends": ["from", "to"]}},
        preferred=more.pop("preferred", {"width": "=@size.figure", "height": "=@space.4 * 7"}),
        **more,
    )


def drawn(
    ids: str, trunk: Any = None, *, links: Any = None, components: Any = None, **more: Any
) -> Any:
    """The scene of cards `ids` each tied to the slot `s`, its links' trunk at `trunk`."""
    content: dict[str, Any] = {
        "steps": [{"id": key} for key in ids],
        "slots": [{"id": "s"}],
        "links": links or [link(f"{key}s", f"steps[{key}]", "slots[s]") for key in ids],
        **more.pop("content", {}),
    }
    found = lab(
        **{"top": pattern(trunk, **more), "card": card(), "arrow": arrow(), **(components or {})}
    )
    return draw(content, components=found)


def points(result: Any, trace: str) -> list[tuple[float, float]]:
    """A connector's route as the scene holds it: its points, or its two ends."""
    element = result.scene.find(trace)
    assert element is not None, f"no element {trace}"
    props = element.properties
    if "points" in props:
        return [(point["x"], point["y"]) for point in props["points"]]
    return [(props["x1"], props["y1"]), (props["x2"], props["y2"])]


def facts(result: Any, code: str) -> list[Any]:
    return [each for each in result.findings if each.code == code]


# --- two and three ties on one side ------------------------------------------------------------


def test_two_ties_that_share_a_trunk_meet_the_slot_at_one_point() -> None:
    result = drawn("ab", "to", slot_y="=@space.4")

    assert result.findings == []
    # The cards' centres lie at 16 and 80 down, the slot's left side at 32 to 64, so the
    # group meets it at the middle, 48. Both ties reach 32 px; the first is the trunk, with
    # corners halfway between its ends, and the second branches off its first leg at its
    # even place, halfway along that leg, then turns again into its last leg.
    assert points(result, "top/links[as]/l") == [(32, 16), (152, 16), (152, 48), (272, 48)]
    assert points(result, "top/links[bs]/l") == [(32, 80), (212, 80), (212, 48), (272, 48)]
    element = result.scene.find("top/links[bs]/l")
    assert element is not None
    # Each tie keeps its ends' elements and sides, as every connector does.
    assert element.properties["attached"] == {
        "start": {"id": "top/steps[b]", "side": "right"},
        "end": {"id": "top/slots[s]", "side": "left"},
    }


def test_two_ties_with_no_trunk_spread_along_the_slots_side() -> None:
    result = drawn("ab", slot_y="=@space.4")

    assert result.findings == []
    assert points(result, "top/links[as]/l") == [(32, 16), (152, 16), (152, 42.67), (272, 42.67)]
    assert points(result, "top/links[bs]/l") == [(32, 80), (152, 80), (152, 53.33), (272, 53.33)]


def test_three_ties_branch_off_one_trunk_the_farthest_reaching_nearest_the_slot() -> None:
    result = drawn("abc", "to")

    assert result.findings == []
    # `b` reaches least, none, so it is the trunk, straight; `a` and `c` reach as far, so
    # `a`, first in the ties' order, leaves nearest the slot. The junctions take their even
    # places, splitting the trunk's 240 px into three.
    assert points(result, "top/links[bs]/l") == [(32, 80), (272, 80)]
    assert points(result, "top/links[as]/l") == [(32, 16), (192, 16), (192, 80), (272, 80)]
    assert points(result, "top/links[cs]/l") == [(32, 144), (112, 144), (112, 80), (272, 80)]


def test_three_ties_with_no_trunk_spread_along_the_slots_side() -> None:
    result = drawn("abc")

    assert result.findings == []
    assert points(result, "top/links[as]/l") == [(32, 16), (152, 16), (152, 72), (272, 72)]
    assert points(result, "top/links[bs]/l") == [(32, 80), (272, 80)]
    assert points(result, "top/links[cs]/l") == [(32, 144), (152, 144), (152, 88), (272, 88)]


def test_ties_that_share_a_trunk_at_their_start_branch_off_it_towards_their_ends() -> None:
    links = [link(f"s{key}", "slots[s]", f"steps[{key}]") for key in "abc"]
    result = drawn("abc", "from", links=links)

    assert result.findings == []
    assert points(result, "top/links[sb]/l") == [(272, 80), (32, 80)]
    assert points(result, "top/links[sa]/l") == [(272, 80), (192, 80), (192, 16), (32, 16)]
    assert points(result, "top/links[sc]/l") == [(272, 80), (112, 80), (112, 144), (32, 144)]


def test_ties_that_meet_the_top_of_an_item_share_a_trunk_down_to_it() -> None:
    row = {"repeat": "steps", "draw": "lab/card", "row": {"gap": "=@space.4"}}
    result = drawn(
        "abc",
        "to",
        parts={"steps": row},
        slot_x="=@space.4 * 2",
        slot_y="=@space.4 * 8.5",
        preferred={"width": "=@size.figure", "height": "=@space.4 * 10"},
    )

    assert result.findings == []
    assert points(result, "top/links[bs]/l") == [(80, 32), (80, 272)]
    assert points(result, "top/links[as]/l") == [(16, 32), (16, 192), (80, 192), (80, 272)]
    assert points(result, "top/links[cs]/l") == [(144, 32), (144, 112), (80, 112), (80, 272)]


def test_the_svg_renderer_draws_each_tie_whole_its_branch_along_the_trunk() -> None:
    [page] = rendered(drawn("abc", "to")).pages

    # Each tie is its own path, its turns round at 8 px, stopping at its arrowhead's base.
    assert (
        'd="M 32 16 L 184 16 A 8 8 0 0 1 192 24 L 192 72 A 8 8 0 0 0 200 80 L 267 80"' in page.svg
    )
    assert 'x1="32" y1="80" x2="267" y2="80"' in page.svg
    assert (
        'd="M 32 144 L 104 144 A 8 8 0 0 0 112 136 L 112 88 A 8 8 0 0 1 120 80 L 267 80"'
        in page.svg
    )
    [spread] = rendered(drawn("abc")).pages
    assert 'd="M 32 16 L 144 16 A 8 8 0 0 1 152 24 L 152 64 A 8 8 0 0 0 160 72 L 267 72"' in (
        spread.svg
    )


def test_the_pdf_renderer_draws_each_tie_whole_its_branch_along_the_trunk() -> None:
    def content(result: Any) -> str:
        file, page = page_of(
            pdf.render(
                result.scene.to_dict(),
                key="default",
                colours=COLOURS,
                font_file=lambda family: pytest.fail(
                    f"no text is drawn, and {family} is asked for"
                ),
                pictures={},
            )
        )
        return file.content(page)

    trunk = content(drawn("ab", "to", slot_y="=@space.4"))
    # The trunk, then the branch, each to its arrowhead's base, five px short of the slot.
    assert "32 16 m 144 16 l 148.42 16 152 19.58 152 24 c 152 40 l" in trunk
    assert "32 80 m 204 80 l 208.42 80 212 76.42 212 72 c 212 56 l" in trunk
    assert trunk.count("267 48 l S") == 2
    spread = content(drawn("ab", slot_y="=@space.4"))
    assert "267 42.67 l S" in spread
    assert "267 53.33 l S" in spread


# --- a group that cannot be drawn clear ---------------------------------------------------------


def test_a_group_with_no_room_on_its_trunks_first_leg_is_drawn_spread_and_stated() -> None:
    # The slot lies 40 px from the cards, too near for two branches to leave the trunk
    # with full turns, 8 px apart.
    result = drawn("abc", "to", slot_x="=@space.4 * 2.25")

    [said] = facts(result, SPREAD)
    assert said.level == FACT
    assert said.where == "links[as]"
    assert said.message.startswith(
        "top/links[as]: the ties `top/links[as]`, `top/links[bs]`, `top/links[cs]` meet the "
        "left side of `top/slots[s]` at their end `to`, and are drawn spread along it, sharing "
        "no trunk: its trunk's first leg, 40 px long, has no room for 2 branches"
    )
    assert "move the items the ties join, in the content" in said.fix
    assert codes(result) == [SPREAD]
    assert [points(result, f"top/links[{key}s]/l")[-1] for key in "abc"] == [
        (72, 72),
        (72, 80),
        (72, 88),
    ]


def test_a_group_two_of_whose_ties_would_cross_is_drawn_spread_and_stated() -> None:
    """Two ties that reach as far one way run level: the branch's last leg would run along
    the trunk's first leg, on one line."""
    row = {"repeat": "steps", "draw": "lab/card", "row": {"gap": "=@space.4"}}
    result = drawn("ab", "to", slot_y="=@space.4 * 4", parts={"steps": row})

    [said] = facts(result, SPREAD)
    assert said.message.endswith(
        "sharing no trunk: its ties `top/links[as]` and `top/links[bs]` would cross"
    )
    assert points(result, "top/links[as]/l")[-1] == (272, 138.67)
    assert points(result, "top/links[bs]/l")[-1] == (272, 149.33)


def test_a_group_that_would_add_a_crossing_is_drawn_spread_and_stated() -> None:
    """A tie between two marks below the trunk, straight down, crosses the branch's last
    leg, and no spread tie: the group would add the crossing."""
    marks = {
        "repeat": "marks",
        "draw": "lab/card",
        "column": {"gap": "=@space.4 * 1.5"},
        "x": "=@space.4 * 5.5",
        "y": "=@space.4 * 3",
    }
    links = [
        link("as", "steps[a]", "slots[s]"),
        link("cs", "steps[c]", "slots[s]"),
        link("uv", "marks[u]", "marks[v]"),
    ]
    result = drawn(
        "ac",
        "to",
        gap="=@space.4 * 3",
        links=links,
        parts={"marks": marks},
        content={"marks": [{"id": "u"}, {"id": "v"}]},
    )

    [said] = facts(result, SPREAD)
    assert said.message.endswith(
        "sharing no trunk: it would add a crossing of the ties `top/links[cs]` and `top/links[uv]`"
    )
    assert points(result, "top/links[cs]/l") == [(32, 144), (152, 144), (152, 85.33), (272, 85.33)]


def test_a_group_whose_part_placed_by_the_measures_does_not_fit_is_drawn_spread() -> None:
    tall = tag(
        "=l.own-center - t.width / 2",
        "=l.own-middle - t.height / 2",
        width="=@space.4 * 6",
        height="=@space.4 * 2.5",
    )
    result = drawn("ab", "to", slot_y="=@space.4", components={"arrow": arrow(t=tall)})

    [said] = facts(result, SPREAD)
    assert said.message.endswith(
        "sharing no trunk: the part `t` of `top/links[as]`, which `lab/arrow` places halfway "
        "along its line's own stretch, does not fit there: it stands on the stretch its tie "
        "shares"
    )
    assert "give the part `t` of `lab/arrow` room on the stretch its tie alone runs" in said.fix
    # Spread, its line shares nothing, so its tag stands at its frame's centre.
    assert points(result, "top/links[as]/l")[-1] == (272, 42.67)
    assert codes(result) == [SPREAD]


# --- ties that form no group -------------------------------------------------------------------


def test_ties_that_draw_otherwise_form_no_group_and_it_is_stated() -> None:
    links = [
        link("as", "steps[a]", "slots[s]"),
        link("bs", "steps[b]", "slots[s]", use="lab/other"),
    ]
    result = drawn("ab", "to", slot_y="=@space.4", links=links, components={"other": arrow()})

    [said] = facts(result, UNGROUPED)
    assert said.level == FACT
    assert said.message == (
        "top/links[as]: the ties `top/links[as]`, `top/links[bs]` meet the left side of "
        "`top/slots[s]` at their end `to`, and form no group, so share no trunk: "
        "`top/links[bs]` draws otherwise than `top/links[as]`, by its component"
    )
    assert points(result, "top/links[as]/l")[-1] == (272, 42.67)


@pytest.mark.parametrize(
    ("paints", "named"),
    [({"fill": "surface"}, "t.fill"), ({}, "t.fill")],
    ids=["painted", "unpainted"],
)
def test_ties_of_which_one_draws_a_part_the_other_does_not_form_no_group(
    paints: dict[str, str], named: str
) -> None:
    """A part whose `when` holds on the second tie alone gives it paints the first has
    none of, painted or not, and the two draw otherwise."""
    shown = {**tag("=@space.1", "=@space.1"), "box": paints, "when": "note"}
    noted = block(
        arrow(t=shown)["parts"],
        ends=True,
        fields={"note": {"type": "string"}},
    )
    links = [
        link("as", "steps[a]", "slots[s]"),
        link("bs", "steps[b]", "slots[s]", note="the second"),
    ]
    result = drawn("ab", "to", slot_y="=@space.4", links=links, components={"arrow": noted})

    [said] = facts(result, UNGROUPED)
    assert said.message.endswith(
        f"`top/links[bs]` draws otherwise than `top/links[as]`, by its paint `{named}`"
    )
    assert points(result, "top/links[as]/l")[-1] == (272, 42.67)


def test_a_straight_part_beside_one_with_corners_forms_no_group_and_it_is_stated() -> None:
    under = {"line": {"stroke": "line"}, "connect": "straight"}
    result = drawn("ab", "to", slot_y="=@space.4", components={"arrow": arrow(u=under)})

    [said] = facts(result, UNGROUPED)
    assert said.message.endswith("`lab/arrow` draws its part `u` straight, beside one with corners")


def test_a_radius_that_reads_a_lines_frame_forms_no_group_and_it_is_stated() -> None:
    reading = arrow()
    reading["parts"]["l"]["line"]["rx"] = "=l.height / 8"
    result = drawn("ab", "to", slot_y="=@space.4", components={"arrow": reading})

    [said] = facts(result, UNGROUPED)
    assert "`lab/arrow` draws the line of `top/links[as]` by the formula `=l.height / 8`" in (
        said.message
    )
    assert "change that formula of `lab/arrow`" in said.fix


def test_straight_ties_that_draw_alike_draw_as_without_a_trunk_and_nothing_is_said() -> None:
    straight = {"arrow": arrow("straight")}
    declared = drawn("abc", "to", components=straight)
    plain = drawn("abc", components=straight)

    assert declared.findings == plain.findings == []
    assert declared.scene.to_dict() == plain.scene.to_dict()


# --- the measures of a line's own stretch ------------------------------------------------------


def test_the_own_measures_read_the_frames_centre_of_a_line_that_shares_nothing() -> None:
    by_measures = drawn("abc", components={"arrow": arrow(t=BY_MEASURES)})
    by_frame = drawn("abc", components={"arrow": arrow(t=BY_FRAME)})

    for key in "abc":
        trace = f"top/links[{key}s]/t"
        assert by_measures.scene.find(trace).properties == by_frame.scene.find(trace).properties


def test_a_part_placed_by_the_measures_stands_halfway_along_its_lines_own_stretch() -> None:
    result = drawn("abc", "to", components={"arrow": arrow(t=BY_MEASURES)})

    assert result.findings == []

    def centre(key: str) -> tuple[float, float]:
        element = result.scene.find(f"top/links[{key}s]/t")
        assert element is not None
        props = element.properties
        return props["x"] + props["width"] / 2, props["y"] + props["height"] / 2

    # `a` runs alone from its junction, 192 px across, back to its start: 224 px, halfway
    # at 144 across on its first leg. `b`, the trunk, alone from the last junction, 112
    # across, to its start; `c` alone from its junction, 112 across, to its start.
    assert centre("a") == (144, 16)
    assert centre("b") == (72, 80)
    assert centre("c") == (104, 144)


def test_a_part_placed_otherwise_on_a_shared_stretch_is_found_in_its_component() -> None:
    result = drawn("abc", "to", components={"arrow": arrow(t=BY_FRAME)})

    # The trunk's frame centres its tag on the stretch the branches share with it.
    [found] = facts(result, PART)
    assert found.level == "fails"
    assert found.where == "parts.t"
    assert found.extra["component"] == "lab/arrow"
    assert found.message == (
        "top/links[bs]/t: `lab/arrow` places its part `t` otherwise than halfway along its "
        "line's own stretch, and where its tie shares a trunk, it stands on the stretch its "
        "tie shares: place it by its line's `own-center` and `own-middle`, which the engine "
        "keeps clear, or off the stretch its tie shares"
    )
    # The ties still share their trunk: the fault is the component's.
    assert points(result, "top/links[bs]/l") == [(32, 80), (272, 80)]


# --- what a round computes aside --------------------------------------------------------------


def test_a_cell_computed_aside_above_the_instance_is_forgotten_and_found_again() -> None:
    """A cell above the instance whose groups are judged, first computed while a round is
    computed aside, and failing, is forgotten after: where it is next read, it fails again
    and its finding is recorded (`Instance._aside`)."""
    outer = top({"in": {"use": "lab/card"}}, preferred={"width": "=@size.figure"})
    ctx = layout.Context(FakeEnv(components=lab(outer=outer, card=card())), "en")
    root = layout.place_top(ctx, "lab/outer", {})
    assert root is not None
    inner = root.nodes["in"].child
    assert inner is not None

    def height() -> float | None:
        return ctx.attempt(lambda: root.get("preferred", "height"), None)

    with inner._aside():
        assert height() is None
    assert ctx.findings == []
    assert height() is None
    assert [each.code for each in ctx.findings] == ["no-size"]


# --- what is refused ---------------------------------------------------------------------------


def test_a_trunk_on_a_list_of_no_ties_or_naming_no_end_field_is_refused() -> None:
    assert issues(pattern("to")) == []
    assert issues(pattern("from")) == []
    assert issues(pattern("via")) == [(SHAPE, "parts.links.trunk")]
    assert issues(pattern({"by": "kind", "a": "to"})) == [(SHAPE, "parts.links.trunk")]
    on_cards = pattern()
    on_cards["parts"]["steps"]["trunk"] = "to"
    assert issues(on_cards) == [(SHAPE, "parts.steps.trunk")]


def test_a_trunk_naming_no_end_field_draws_its_ties_spread() -> None:
    result = drawn("ab", "via", slot_y="=@space.4")

    assert finding(result, SHAPE).where == "parts.links.trunk"
    assert points(result, "top/links[as]/l")[-1] == (272, 42.67)


def test_an_own_measure_of_what_is_no_line_is_refused() -> None:
    on_box = arrow(
        t=tag("=@space.1", "=@space.1"),
        u=tag("=t.own-center", "=@space.1"),
    )
    assert issues(on_box) == [("formula-reach", "parts.u.x")]
    from_end = arrow(u=tag("={start}.own-middle", "=@space.1"))
    assert issues(from_end) == [("formula-reach", "parts.u.x")]
