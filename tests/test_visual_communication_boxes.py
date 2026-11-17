"""The checks of boxes (visual-communication DEC-046 point 3): edges that nearly line up, and
boxes that overlap, among the siblings of each scene.

- **Edges that nearly line up** (`near-alignment`): two siblings whose edges or centres on one
  axis differ by more than a pixel of rounding and by less than the brand's smallest step of
  space, unless they line up on another line of that axis; a part another holds whose insets
  on the two sides of one axis differ by as much, unless it lies on an edge of that axis; and
  two spacings between the siblings of a group that nearly agree.
- **Boxes that overlap** (`box-overlap`): two siblings whose boxes overlap, where neither
  holds the other, a text a sibling covers among them.
- **Both** leave lines and arrows out, ask the reviewer for attention and never fail
  (DEC-002 point 7). The step follows the brand at each key over the size axes.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from tests.in_process import load
from tests.test_visual_communication_checks import LOCAL, local, project_of
from tests.test_visual_communication_pipeline import NARROW, PHONE, add_device, drawing_project
from tests.test_visual_communication_pipeline import write_content as write_body
from tests.visual_communication_project import write

boxes, findings, checks = load("visual-communication", "boxes", "findings", "checks")

#: The brand's smallest step of space in the scenes these tests write.
STEP = boxes.Step("space.1", 4.0)


def element(
    trace: str,
    kind: str = "box",
    *,
    x: float = 0,
    y: float = 0,
    width: float = 40,
    height: float = 40,
) -> dict[str, Any]:
    return {"type": kind, "id": trace, "x": x, "y": y, "width": width, "height": height}


def group(trace: str, *children: dict[str, Any], **frame: float) -> dict[str, Any]:
    return {**element(trace, "group", **frame), "children": list(children)}


def scene(*children: dict[str, Any]) -> dict[str, Any]:
    """A scene of one page, the figure, 400 by 200 px, that holds `children`."""
    return {"pages": ["figure"], "children": [group("figure", *children, width=400, height=200)]}


def line(trace: str, x1: float, y1: float, x2: float, y2: float) -> dict[str, Any]:
    """A line from `x1 y1` to `x2 y2`, its frame from its ends, with an arrowhead at its end."""
    frame = element(trace, "line", x=min(x1, x2), y=min(y1, y2))
    frame.update(width=abs(x2 - x1), height=abs(y2 - y1), x1=x1, y1=y1, x2=x2, y2=y2)
    return {**frame, "marker-end": "arrow"}


def near(found: list[Any]) -> list[str]:
    return [each.message for each in found if each.code == boxes.NEAR_ALIGNMENT]


# --- edges that nearly line up ------------------------------------------------------------------


def test_two_edges_a_little_apart_ask_the_reviewer_for_attention_and_never_fail() -> None:
    found = boxes.near_alignment(scene(element("figure/a"), element("figure/b", x=2.5, y=60)), STEP)
    [finding] = found
    assert (finding.code, finding.level, finding.where, finding.file) == (
        "near-alignment",
        findings.ATTENTION,
        "figure/a",
        "",
    )
    assert finding.message == (
        "`figure/a` and `figure/b` nearly line up across: their left edges lie 2.5 px apart, "
        "their centres lie 2.5 px apart and their right edges lie 2.5 px apart, more than a "
        "pixel of rounding and less than the brand's smallest step of space, `space.1`, 4 px"
    )
    assert finding.who == boxes.REVIEWER
    assert "graphic-design-reviewer" in finding.who
    assert finding.fix == boxes.ALIGN_IT


@pytest.mark.parametrize(
    ("offset", "reported"),
    [(0.6, False), (1.0, False), (1.01, True), (3.99, True), (4.0, False), (9, False)],
    ids=["rounding", "a-pixel", "past-a-pixel", "under-the-step", "the-step", "past-the-step"],
)
def test_only_a_difference_past_a_pixel_and_short_of_the_step_is_near(
    offset: float, reported: bool
) -> None:
    given = scene(element("figure/a"), element("figure/b", x=offset, y=60))
    assert bool(boxes.near_alignment(given, STEP)) is reported


def test_a_step_no_longer_than_a_pixel_leaves_nothing_near_and_says_so() -> None:
    """Where the brand gives no step of space at a key, or one no longer than a pixel of
    rounding, nothing can be near: the check states as a fact, at the brand, that it measured
    nothing at that key (DEC-063 point 2)."""
    given = scene(element("figure/a"), element("figure/b", x=0.9, y=60))
    [short] = boxes.near_alignment(given, boxes.Step("space.1", 1.0))
    [none] = boxes.near_alignment(given, None)
    for stated in (short, none):
        assert (stated.code, stated.level, stated.where) == (
            boxes.NEAR_ALIGNMENT_UNMEASURED,
            findings.FACT,
            "brand",
        )
        assert stated.message.endswith(
            "so nothing is near: the check of edges that nearly line up measured no pair or "
            "group of siblings at this key"
        )
        assert not stated.fix and not stated.who
    assert short.message.startswith(
        "the brand's smallest step of space, `space.1`, 1 px, is no longer than a pixel of "
        "rounding, so"
    )
    assert none.message.startswith("the brand gives no step of space at this key, so")


def test_centres_a_little_apart_are_near_where_the_edges_lie_far_apart() -> None:
    given = scene(element("figure/wide", width=100), element("figure/narrow", x=32, y=60, width=40))
    [message] = near(boxes.near_alignment(given, STEP))
    assert message.startswith(
        "`figure/wide` and `figure/narrow` nearly line up across: their centres lie 2 px apart, "
    )


def test_an_icon_and_a_label_centred_in_a_row_are_not_near_at_their_tops() -> None:
    """The label is shorter than the icon and centred beside it, so its top and its bottom
    lie 2.4 px from the icon's: a near miss on two lines that follows from the middle they
    share."""
    icon = element("figure/row/icon", width=24, height=24)
    label = element("figure/row/label", "text", x=32, y=2.4, width=100, height=19.2)
    assert boxes.near_alignment(scene(group("figure/row", icon, label, height=24)), STEP) == []


def test_an_icon_and_a_label_a_little_off_their_middle_are_near() -> None:
    icon = element("figure/row/icon", width=24, height=24)
    label = element("figure/row/label", "text", x=32, y=6, width=100, height=19.2)
    [message] = near(boxes.near_alignment(scene(group("figure/row", icon, label)), STEP))
    assert message.startswith(
        "`figure/row/icon` and `figure/row/label` nearly line up down: their middles lie 3.6 "
        "px apart and their bottoms lie 1.2 px apart, "
    )


def test_texts_of_different_widths_on_one_left_edge_are_not_near_at_their_right_edges() -> None:
    first = element("figure/first", "text", width=100, height=20)
    second = element("figure/second", "text", y=28, width=97, height=20)
    assert boxes.near_alignment(scene(first, second), STEP) == []


def test_texts_a_little_off_one_left_edge_are_near() -> None:
    first = element("figure/first", "text", width=100, height=20)
    second = element("figure/second", "text", x=2, y=28, width=90, height=20)
    [message] = near(boxes.near_alignment(scene(first, second), STEP))
    assert message.startswith(
        "`figure/first` and `figure/second` nearly line up across: their left edges lie 2 px "
        "apart and their centres lie 3 px apart, "
    )


def card(left: float, right: float, *, top: float = 10, bottom: float = 10) -> dict[str, Any]:
    """A card whose box, 100 by 40 px, holds its head, a text set in from the box's edges by
    `left` and `right` across and by `top` and `bottom` down: the two are siblings of one
    component."""
    head = element(
        "figure/card/head",
        "text",
        x=left,
        y=top,
        width=100 - left - right,
        height=40 - top - bottom,
    )
    box = element("figure/card/box", width=100, height=40)
    return group("figure/card", box, head, width=100, height=40)


def test_a_part_whose_insets_nearly_agree_in_the_box_that_holds_it_is_near() -> None:
    [finding] = boxes.near_alignment(scene(card(6, 8)), STEP)
    assert (finding.code, finding.level, finding.where, finding.who, finding.fix) == (
        "near-alignment",
        findings.ATTENTION,
        "figure/card/box",
        boxes.REVIEWER,
        boxes.ALIGN_IT,
    )
    assert finding.message == (
        "`figure/card/box` holds `figure/card/head` with insets across that nearly agree: 6 px "
        "on the left and 8 px on the right, 2 px apart, more than a pixel of rounding and less "
        "than the brand's smallest step of space, `space.1`, 4 px"
    )


def test_the_insets_of_a_held_part_are_compared_down_as_across() -> None:
    [message] = near(boxes.near_alignment(scene(card(8, 8, top=9, bottom=12)), STEP))
    assert message.startswith(
        "`figure/card/box` holds `figure/card/head` with insets down that nearly agree: 9 px at "
        "the top and 12 px at the bottom, 3 px apart, "
    )


@pytest.mark.parametrize(
    ("left", "right", "reported"),
    [
        (10, 13.9, True),
        (10, 10.8, False),
        (8, 4, False),
        (2, 8, False),
        (0, 3, False),
        (0.5, 3.4, False),
    ],
    ids=[
        "near",
        "within-a-pixel",
        "centres-near",
        "an-edge-near",
        "on-an-edge",
        "on-an-edge-within-a-pixel",
    ],
)
def test_a_held_part_is_near_only_where_its_insets_nearly_agree(
    left: float, right: float, reported: bool
) -> None:
    """The held part's insets are compared, not its centre or its edges with the other's: a
    head set in 8 px on the left and 4 px on the right has its centre 2 px from the box's,
    and one set in 2 px on the left has its left edge 2 px from the box's, and neither is
    near. A head on one of the box's edges lines up on it."""
    assert bool(boxes.near_alignment(scene(card(left, right)), STEP)) is reported


# --- gaps that nearly agree ---------------------------------------------------------------------


def row(*xs: float, width: float = 40) -> dict[str, Any]:
    """A row of boxes, one at each of `xs`, as the items of one list."""
    items = [element(f"figure/row#{n}", x=x, width=width) for n, x in enumerate(xs, 1)]
    return group("figure/row", *items, width=400, height=40)


def test_two_spacings_of_one_row_that_nearly_agree_are_one_finding_naming_each_gap() -> None:
    [finding] = boxes.near_alignment(scene(row(0, 48, 96, 146)), STEP)
    assert finding.where == "figure/row"
    assert finding.message == (
        "the gaps across in `figure/row` nearly agree: 8 px, between `figure/row#1` and "
        "`figure/row#2` and between `figure/row#2` and `figure/row#3`; and 10 px, between "
        "`figure/row#3` and `figure/row#4`: 2 px apart, more than a pixel of rounding and less "
        "than the brand's smallest step of space, `space.1`, 4 px"
    )


@pytest.mark.parametrize(
    "xs",
    [(0, 48, 96, 144), (0, 48, 96, 144.6), (0, 48, 96, 152), (0, 48)],
    ids=["even", "within-a-pixel", "a-step-apart", "one-gap"],
)
def test_even_gaps_and_gaps_a_step_apart_are_not_near(xs: tuple[float, ...]) -> None:
    assert boxes.near_alignment(scene(row(*xs)), STEP) == []


def test_a_gap_is_taken_only_to_a_sibling_beside_it() -> None:
    """Down a column of two, and a third beside the column: the gaps down are the column's
    alone, and no gap across is taken between two boxes that share no height."""
    column = group(
        "figure/grid",
        element("figure/grid/a"),
        element("figure/grid/b", y=48),
        element("figure/grid/c", x=200, y=150),
        width=400,
        height=200,
    )
    assert boxes.near_alignment(scene(column), STEP) == []


# --- what the checks leave out ------------------------------------------------------------------


def test_an_arrow_that_stops_short_of_a_card_is_left_out_of_both_checks() -> None:
    """The arrow leaves the first card and ends 3 px short of the second's left edge, and a
    line crosses the second card. Counted as boxes, the arrow would leave gaps of 0 and 3 px,
    and the line would overlap the card: a line neither lines up nor overlaps."""
    given = scene(
        element("figure/start", width=40, height=40),
        line("figure/arrow", 40, 18, 97, 22),
        element("figure/card", x=100, width=80, height=40),
        line("figure/rule", 110, 0, 130, 60),
    )
    assert boxes.near_alignment(given, STEP) == []
    assert boxes.overlaps(given) == []


def test_a_group_that_draws_only_lines_is_left_out_as_a_line_is() -> None:
    """A tie's item lies in its pattern's whole frame and draws its connector alone, so it
    would hold and nearly line up with everything beside it."""
    arrow = line("figure/links[a-b]/arrow", 2, 18, 100, 22)
    tie = group("figure/links[a-b]", arrow, x=2, width=398, height=200)
    given = scene(element("figure/card", x=0, width=100), tie)
    assert boxes.near_alignment(given, STEP) == []
    assert boxes.overlaps(given) == []


def test_an_element_of_no_area_and_a_page_are_left_out() -> None:
    empty = element("figure/picture", "image", x=2, width=0, height=40)
    assert boxes.near_alignment(scene(element("figure/a"), empty), STEP) == []

    def slide(name: str, x: float) -> dict[str, Any]:
        """A page of the deck, which draws a box: 2 px apart, two such boxes would be near."""
        held = element(f"deck/slides[{name}]/box")
        return {**group(f"deck/slides[{name}]", held, x=x, width=400, height=200), "page": True}

    deck = group("deck", slide("a", 0), slide("b", 2), width=400, height=200)
    pages = {"pages": ["deck/slides[a]", "deck/slides[b]"], "children": [deck]}
    assert boxes.near_alignment(pages, STEP) == []
    assert boxes.overlaps(pages) == []


def test_only_siblings_are_compared() -> None:
    """Two boxes 2 px apart in two cards are no siblings: the cards, which line up, are."""
    first = group("figure/one", element("figure/one/box"), width=40, height=40)
    second = group("figure/two", element("figure/two/box", x=2), y=60, width=40, height=40)
    assert boxes.near_alignment(scene(first, second), STEP) == []


# --- boxes that overlap -------------------------------------------------------------------------


def test_two_boxes_that_overlap_where_neither_holds_the_other_ask_the_reviewer() -> None:
    [finding] = boxes.overlaps(scene(element("figure/a"), element("figure/b", x=30, y=20)))
    assert (finding.code, finding.level, finding.where, finding.who, finding.fix) == (
        "box-overlap",
        findings.ATTENTION,
        "figure/a",
        boxes.REVIEWER,
        boxes.PART_IT,
    )
    assert finding.message == (
        "the boxes of `figure/a` and `figure/b` overlap by 10 px across and 20 px down, and "
        "neither holds the other: `figure/b` is drawn over `figure/a`"
    )


def test_a_box_that_holds_another_and_boxes_that_meet_within_a_pixel_do_not_overlap() -> None:
    held = scene(element("figure/back", width=100, height=100), element("figure/in", x=8, y=8))
    assert boxes.overlaps(held) == []
    within = scene(element("figure/a", width=100, height=100), element("figure/b", x=-0.5, y=8))
    assert boxes.overlaps(within) == []
    grazing = scene(element("figure/a"), element("figure/b", x=39.2, y=20))
    assert boxes.overlaps(grazing) == []


def test_a_text_a_sibling_covers_is_reported_as_any_other_part_is() -> None:
    """The note is drawn first and the legend over the end of its line: the check reports the
    note, whatever the viewing step's report names."""
    note = {
        **element("figure/note", "text", width=100, height=20),
        "line-height": 20,
        "lines": [{"text": "Words", "width": 100, "baseline": 15, "paragraph": 0}],
    }
    given = scene(note, element("figure/legend", x=80, y=10, width=60, height=30))
    [finding] = boxes.overlaps(given)
    assert finding.where == "figure/note"
    assert finding.message.endswith("`figure/legend` is drawn over `figure/note`")


# --- the brand's smallest step of space ---------------------------------------------------------


def px(value: float) -> dict[str, Any]:
    return {"value": value, "unit": "px"}


def test_the_smallest_step_is_the_least_shared_step_of_space_the_brand_gives() -> None:
    values = {
        "space.1": px(6),
        "space.2": px(3),
        "space.3": px(3),
        "space.sign-gap": px(1),
        "space.4": px(0),
        "stroke.thin": px(1),
    }
    assert boxes.smallest_step(values) == boxes.Step("space.2", 3.0)
    assert boxes.smallest_step({"stroke.thin": px(1)}) is None


#: What the test brand gives a phone in the test of the step: half the figure's width, and
#: half its smallest step of space.
HALF_STEP: dict[str, Any] = {
    **NARROW,
    "space": {
        "$type": "dimension",
        "1": {"$value": px(2)},
        "2": {"$value": px(4)},
    },
}

#: Two boxes, the second 3 px to the right of the first and below it: a near miss under a
#: step of 4 px, and a spacing under a step of 2 px.
PAIR = local(
    about="Two squares, one under the other, the second a little to the right.",
    fields={"type": "object", "properties": {}},
    parts={
        "first": {
            "box": {"fill": "surface"},
            "width": "=@space.4",
            "height": "=@space.4",
        },
        "second": {
            "box": {"fill": "surface"},
            "x": "=@space.3 * 0.1875",
            "y": "=@space.4 * 2",
            "width": "=@space.4",
            "height": "=@space.4",
        },
    },
    preferred={"height": "=second.bottom"},
)


def test_the_step_follows_the_brand_at_each_key_over_the_size_axes(tmp_path: Path) -> None:
    """The test brand's smallest step is 4 px on a desktop and 2 px on a phone, where the
    pair is drawn alike: 3 px apart is near on the desktop alone."""
    root = drawing_project(tmp_path, picture=False, modes={"device": ["desktop", "phone"]})
    add_device(root, HALF_STEP)
    write(root / LOCAL / "pair.yaml", PAIR)
    write_body(root, body={"use": "piece/pair"})
    found = [f for f in checks.computed(project_of(root)) if f.code == boxes.NEAR_ALIGNMENT]
    [finding] = found
    assert (finding.file, finding.where, finding.level) == (
        "piece.yaml",
        "figure/body/first",
        findings.ATTENTION,
    )
    assert finding.message.startswith(
        "`default`: `figure/body/first` and `figure/body/second` nearly line up across: "
    )
    assert finding.message.endswith("`space.1`, 4 px")
    assert PHONE not in json.dumps([f.message for f in found])


#: A head and a badge drawn after it over the end of its line.
COVERED = local(
    about="A head, and a badge over the end of it.",
    fields={"type": "object", "required": ["head"], "properties": {"head": {"type": "string"}}},
    parts={
        "head": {
            "text": {"content": "head", "style": "type.body", "fill": "text-primary"},
            "width": "=@space.4 * 4",
        },
        "badge": {
            "box": {"fill": "surface"},
            "x": "=@space.4 * 2",
            "y": "=@space.1",
            "width": "=@space.4 * 3",
            "height": "=@space.4",
        },
    },
    preferred={"height": "=badge.bottom"},
)


@pytest.mark.parametrize("exports", [["svg"], ["svg", "html"]], ids=["svg", "html"])
def test_a_covered_text_is_reported_whatever_the_piece_exports(
    tmp_path: Path, exports: list[str]
) -> None:
    """The badge is drawn over the end of the head: the check reports the head at the piece's
    own file, whether the viewing step reads the piece through the SVG renderer or, as for a
    piece that exports `html`, through a browser."""
    root = drawing_project(tmp_path, picture=False, exports=exports)
    write(root / LOCAL / "covered.yaml", COVERED)
    write_body(root, body={"use": "piece/covered", "head": "Plan the work."})
    found = [f for f in checks.computed(project_of(root)) if f.code == boxes.BOX_OVERLAP]
    assert [(f.file, f.where) for f in found] == [("piece.yaml", "figure/body/head")]
