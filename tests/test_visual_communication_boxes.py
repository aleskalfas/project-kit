"""The checks of boxes (visual-communication DEC-046 point 3): edges that nearly line up, among
the siblings of each scene and between groups (DEC-067), and boxes that overlap, among the
siblings.

- **Edges that nearly line up** (`near-alignment`): two siblings whose edges or centres on one
  axis differ by more than a pixel of rounding and by less than the brand's smallest step of
  space, unless they line up on another line of that axis; a part another holds whose insets
  on the two sides of one axis differ by as much, unless it lies on an edge of that axis; and
  two spacings between the siblings of a group that nearly agree. A text is compared by its
  room: on every line where it fills its width, and else on the line it stands its lines on.
  A finding of two siblings, one of them a group, names the pairs of leaves that show it.
- **Between groups** (`near-alignment-between-groups`): two leaves of different groups on one
  page, neither a tie's part, gathered into one finding for each offset between two sides; and
  two lists whose items one component draws, at one level, whose spacings nearly agree.
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


def text(
    trace: str,
    *,
    x: float = 0,
    y: float = 0,
    width: float = 40,
    height: float = 20,
    lines: tuple[float, ...] | None = None,
    anchor: str = "start",
    given: bool = True,
) -> dict[str, Any]:
    """A text standing its lines at `anchor`, with a line of each width `lines` gives, by
    default one as wide as the text, whose component gave it its width where `given`, and
    else none, which the scene says by naming the engine as its width's source."""
    drawn = (width,) if lines is None else lines
    held = {
        **element(trace, "text", x=x, y=y, width=width, height=height),
        "text-anchor": anchor,
        "lines": [{"text": "Words", "width": each} for each in drawn],
    }
    return {**held, "sources": {"width": "engine"}} if not given else held


def filling(
    trace: str, *, x: float = 0, y: float = 0, width: float = 40, height: float = 20
) -> dict[str, Any]:
    """A text of one line given no width, as wide as its line, so it fills its width."""
    return text(trace, x=x, y=y, width=width, height=height, given=False)


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
            "so nothing is near: the check of edges that nearly line up measured no place at "
            "this key, no pair or group of siblings, no two parts of different groups and no "
            "two lists"
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
    first = filling("figure/first", width=100)
    second = filling("figure/second", y=28, width=97)
    assert boxes.near_alignment(scene(first, second), STEP) == []


def test_texts_that_fill_their_widths_a_little_off_one_left_edge_are_near_on_each_line() -> None:
    """A text of one line given no width is as wide as its line, so it draws to both its
    edges and is compared on every line (DEC-067 point 3)."""
    first = filling("figure/first", width=100)
    second = filling("figure/second", x=2, y=28, width=90)
    [message] = near(boxes.near_alignment(scene(first, second), STEP))
    assert message.startswith(
        "`figure/first` and `figure/second` nearly line up across: their left edges lie 2 px "
        "apart and their centres lie 3 px apart, "
    )


def card(left: float, right: float, *, top: float = 10, bottom: float = 10) -> dict[str, Any]:
    """A card whose box, 100 by 40 px, holds its head, a text as wide as its one line, set in
    from the box's edges by `left` and `right` across and by `top` and `bottom` down: the two
    are siblings of one component."""
    head = filling(
        "figure/card/head", x=left, y=top, width=100 - left - right, height=40 - top - bottom
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


def test_two_boxes_in_two_cards_that_line_up_are_compared_between_groups() -> None:
    """Two boxes 2 px apart in two cards are no siblings: the cards, which line up, are, and
    the boxes are compared as two leaves of different groups (DEC-067 point 1)."""
    first = group("figure/one", element("figure/one/box"), width=40, height=40)
    second = group("figure/two", element("figure/two/box", x=2), y=60, width=40, height=40)
    [finding] = boxes.near_alignment(scene(first, second), STEP)
    assert (finding.code, finding.where) == (boxes.NEAR_ALIGNMENT_BETWEEN_GROUPS, "figure/one")


# --- a text's room ------------------------------------------------------------------------------


def on_page(*children: dict[str, Any]) -> dict[str, Any]:
    """A scene of one page, 800 by 600 px, that holds `children`."""
    return {"pages": ["page"], "children": [group("page", *children, width=800, height=600)]}


def found_in(given: dict[str, Any]) -> list[tuple[str, str]]:
    """Each finding of the check of edges that nearly line up in `given`, by its label and
    where it lies."""
    return [(f.code, f.where) for f in boxes.near_alignment(given, STEP)]


def margin(
    *body: dict[str, Any],
    title: dict[str, Any] | None = None,
    body_x: float = 43,
    body_w: float = 717,
) -> dict[str, Any]:
    """The margin of DEC-067's Context: a header 40 px from the page's left edge and 720 px
    wide, holding a title, and a body `body_x` from it and `body_w` wide, by default 43 px and
    717 px, so their right edges agree. Each text is given the width left to it."""
    held = title or text("page/header/title", width=720, height=40, lines=(300,))
    return on_page(
        group("page/header", held, x=40, y=20, width=720, height=60),
        group("page/body", *body, x=body_x, y=100, width=body_w, height=400),
    )


PARAGRAPH = text("page/body/paragraph", width=717, height=100, lines=(600,))
LIST = text("page/body/list", y=120, width=717, height=100, lines=(500,))
STEP_SAID = "the brand's smallest step of space, `space.1`, 4 px"


def test_the_margin_names_the_title_with_the_paragraph_and_the_list_in_one_finding() -> None:
    """Each text takes the rest of its group's width, so the three boxes agree at their right
    edges, in their room: the title's left edge is named 3 px off the paragraph's and the
    list's, in one finding at the header and the body (DEC-067 points 3 and 4)."""
    [finding] = boxes.near_alignment(margin(PARAGRAPH, LIST), STEP)
    assert (finding.code, finding.level, finding.where, finding.who, finding.fix) == (
        boxes.NEAR_ALIGNMENT_BETWEEN_GROUPS,
        findings.ATTENTION,
        "page/header",
        boxes.REVIEWER,
        boxes.ALIGN_IT,
    )
    assert finding.message == (
        "at `page/header` and `page/body`, parts of different groups nearly line up across, "
        f"by more than a pixel of rounding and less than {STEP_SAID}: `page/header/title` "
        "and `page/body/paragraph`, their left edges 3 px apart; `page/header/title` and "
        "`page/body/list`, their left edges 3 px apart"
    )


@pytest.mark.parametrize(
    ("body", "title"),
    [
        (
            (
                text("page/body/paragraph", width=717, height=100, lines=(716.6, 690, 412)),
                text("page/body/list", y=120, width=717, height=100, lines=(700, 716.2)),
            ),
            None,
        ),
        ((text("page/body/paragraph", width=717, height=100, lines=(717,)),), None),
        (
            (text("page/body/paragraph", width=717, height=100, lines=(716.5,)),),
            text("page/header/title", width=720, height=40, lines=(720,)),
        ),
        (
            (text("page/body/paragraph", width=717, height=100, lines=(716.6, 690, 412)),),
            text("page/header/title", width=720, height=40, lines=(719.6, 380)),
        ),
        (
            (text("page/body/paragraph", width=717, height=30, lines=(731,)),),
            text("page/header/title", width=720, height=40, lines=(720,)),
        ),
    ],
    ids=[
        "wrapped-widest-at-the-width",
        "one-line-reaching-its-width",
        "both-of-one-line-reaching-their-widths",
        "both-wrapped-widest-at-their-widths",
        "overflowing-beside-a-line-at-its-width",
    ],
)
def test_a_text_given_a_width_or_of_more_lines_is_compared_on_its_anchor_s_line_alone(
    body: tuple[dict[str, Any], ...], title: dict[str, Any] | None
) -> None:
    """However near its width its widest line ends, or past it, a text given its width, or of
    more lines than one, has room no reader sees past its lines: its right edge passes no
    near miss over, and the margin gives one finding (DEC-067 point 3)."""
    found = boxes.near_alignment(margin(*body, title=title), STEP)
    assert [(f.code, f.where) for f in found] == [
        (boxes.NEAR_ALIGNMENT_BETWEEN_GROUPS, "page/header")
    ]
    assert "`page/header/title` and `page/body/paragraph`, their left edges 3 px apart" in (
        found[0].message
    )


def test_texts_of_one_line_given_no_width_are_compared_on_every_line() -> None:
    """Two labels as wide as their words, in two groups 3 px apart: the groups' finding names
    the labels' left edges, which show its near miss, and their other lines differ by more
    than a step."""
    first = group("page/a", filling("page/a/label", width=120, height=30), x=40, y=20, width=300)
    second = group("page/b", filling("page/b/label", width=150, height=30), x=43, y=100, width=300)
    [finding] = boxes.near_alignment(on_page(first, second), STEP)
    assert (finding.code, finding.where) == (boxes.NEAR_ALIGNMENT, "page/a")
    assert finding.message.endswith(
        ". Parts of different groups that are these or lie in them show it: `page/a/label` and "
        "`page/b/label`, their left edges 3 px apart"
    )


def tag(label: dict[str, Any]) -> dict[str, Any]:
    """A tag's box, 100 by 30 px, round its label."""
    return group("page/tag", element("page/tag/box", width=100, height=30), label, x=20, y=20)


@pytest.mark.parametrize(
    ("label", "reported"),
    [
        (filling("page/tag/label", x=8, y=4, width=82, height=22), True),
        (text("page/tag/label", x=8, y=4, width=82, height=22), False),
        (text("page/tag/label", x=8, y=4, width=82, height=22, lines=(95,)), False),
        (text("page/tag/label", x=8, y=4, width=82, height=22, anchor="middle"), True),
    ],
    ids=["given-no-width", "given-its-width", "overflowing", "standing-in-the-middle"],
)
def test_a_text_s_insets_across_are_compared_only_where_it_fills_or_stands_in_the_middle(
    label: dict[str, Any], reported: bool
) -> None:
    """A label 8 px in on the left and 10 px on the right of its tag's box: as wide as its
    words, or standing its lines in the middle, its insets are compared; given its width and
    standing them at the start, one of its insets reaches into its room (DEC-067 point 3)."""
    assert bool(boxes.near_alignment(on_page(tag(label)), STEP)) is reported


def test_a_title_set_in_its_card_given_its_width_takes_no_finding_of_insets() -> None:
    card_ = group(
        "page/card",
        element("page/card/box", width=240, height=200),
        text("page/card/title", x=16, y=16, width=206, height=30, lines=(120,)),
        x=20,
        y=20,
        width=240,
        height=200,
    )
    assert boxes.near_alignment(on_page(card_), STEP) == []


@pytest.mark.parametrize(
    ("anchor", "x", "reported"),
    [("start", 2, True), ("middle", 2, False), ("middle", -48.5, True), ("end", -97, True)],
    ids=["start-on-the-left", "middle-not-on-the-left", "middle-on-the-centre", "end"],
)
def test_a_text_with_room_is_compared_on_the_line_it_stands_its_lines_on(
    anchor: str, x: float, reported: bool
) -> None:
    """A box 100 px wide, and below it a text 200 px wide, given its width: the text is
    compared with the box on its left edge where it stands its lines at the start, its centre
    in the middle and its right edge at the end, and on no other line."""
    box = element("page/box", width=100, height=20)
    lead = text("page/lead", x=x, y=60, width=200, height=20, lines=(80,), anchor=anchor)
    assert bool(boxes.near_alignment(on_page(box, lead), STEP)) is reported


def test_two_texts_with_room_that_share_no_line_are_not_compared_across() -> None:
    first = text("page/first", width=200, lines=(80,))
    second = text("page/second", x=-97.5, y=40, width=200, lines=(80,), anchor="middle")
    assert boxes.near_alignment(on_page(first, second), STEP) == []


def test_no_gap_across_that_starts_or_ends_at_a_text_s_room_is_taken() -> None:
    """A row of three texts 200 px wide, set 16 px and 19 px apart: each gap starts in a
    text's room, so no spacing is taken (DEC-067 point 3)."""
    row_ = group(
        "page/row",
        text("page/row/a", width=200, height=30, lines=(120,)),
        text("page/row/b", x=216, width=200, height=30, lines=(90,)),
        text("page/row/c", x=435, width=200, height=30, lines=(150,)),
        x=20,
        y=20,
        width=700,
        height=40,
    )
    assert boxes.near_alignment(on_page(row_), STEP) == []
    filled = group(
        "page/row",
        filling("page/row/a", width=200, height=30),
        filling("page/row/b", x=216, width=200, height=30),
        filling("page/row/c", x=435, width=200, height=30),
        x=20,
        y=20,
        width=700,
        height=40,
    )
    assert found_in(on_page(filled)) == [(boxes.NEAR_ALIGNMENT, "page/row")]


# --- between groups -----------------------------------------------------------------------------


def test_a_finding_of_two_siblings_names_the_pairs_that_show_it_by_the_same_line() -> None:
    """A header 40 px from the page's left edge and 720 px wide, beside a body 43.5 px from it
    and 718 px wide: they nearly agree by 3.5 px at their left edges, 2.5 px at their centres
    and 1.5 px at their right edges. Their texts show the 3.5 px at their left, so the
    groups' finding names them, and they take none of their own (DEC-067 point 4)."""
    body = text("page/body/paragraph", width=718, height=100, lines=(700, 650))
    [finding] = boxes.near_alignment(margin(body, body_x=43.5, body_w=718), STEP)
    assert finding.message == (
        "`page/header` and `page/body` nearly line up across: their left edges lie 3.5 px "
        "apart, their centres lie 2.5 px apart and their right edges lie 1.5 px apart, more "
        f"than a pixel of rounding and less than {STEP_SAID}. Parts of different groups that "
        "are these or lie in them show it: `page/header/title` and `page/body/paragraph`, "
        "their left edges 3.5 px apart"
    )


def test_a_pair_that_shows_none_of_the_siblings_differences_on_its_line_takes_its_own() -> None:
    """A box in the body 2.2 px right of the title lies within a pixel of the 2.5 px at the
    centres and of the 1.5 px at the right edges, but its left edge shows no placement of the
    body: it takes a finding of its own beside the groups'."""
    box = element("page/body/box", x=-1.3, width=200, height=60)
    found = boxes.near_alignment(margin(box, body_x=43.5, body_w=718), STEP)
    assert [(f.code, f.where) for f in found] == [
        (boxes.NEAR_ALIGNMENT, "page/header"),
        (boxes.NEAR_ALIGNMENT_BETWEEN_GROUPS, "page/header"),
    ]
    assert found[0].message.endswith(
        ". No two parts of different groups that are these or lie in them show it: it lies "
        "only at the edge of the room a group was given, where nothing is drawn"
    )
    assert found[1].message.endswith(
        "`page/header/title` and `page/body/box`, their left edges 2.2 px apart"
    )


def test_a_finding_of_two_groups_that_no_pair_of_leaves_shows_says_so() -> None:
    """A header whose room starts 3 px left of the body's, while its title is set 10 px in."""
    header = group(
        "page/header",
        text("page/header/title", x=10, width=300, height=40, lines=(200,)),
        x=40,
        y=20,
        width=700,
        height=60,
    )
    body = group("page/body", PARAGRAPH, x=43, y=100, width=717, height=400)
    [finding] = boxes.near_alignment(on_page(header, body), STEP)
    assert (finding.code, finding.where) == (boxes.NEAR_ALIGNMENT, "page/header")
    assert "No two parts of different groups that are these or lie in them show it" in (
        finding.message
    )


def plain_card(n: int, y: float) -> dict[str, Any]:
    """A card of a row, its box and its title set 16 px in."""
    trace = f"page/row#{n}"
    return {
        **group(
            trace,
            element(f"{trace}/box", width=240, height=200),
            text(f"{trace}/title", x=16, y=16, width=208, height=30, lines=(150,)),
            x=20 + (n - 1) * 260,
            y=y,
            width=240,
            height=200,
        ),
        "component": "tests/card",
    }


def test_a_card_set_2_px_lower_is_one_finding_naming_its_box_and_its_title() -> None:
    row_ = group("page/row", plain_card(1, 40), plain_card(2, 42), width=800, height=300)
    [finding] = boxes.near_alignment(on_page(row_), STEP)
    assert (finding.code, finding.where) == (boxes.NEAR_ALIGNMENT, "page/row#1")
    assert finding.message.endswith(
        "show it: `page/row#1/box` and `page/row#2/box`, their tops 2 px apart, middles 2 px "
        "apart and bottoms 2 px apart; `page/row#1/title` and `page/row#2/title`, their tops "
        "2 px apart, middles 2 px apart and bottoms 2 px apart"
    )


def content_card(n: int, low: float, title: float = 30, foot: float = 60) -> dict[str, Any]:
    """A card whose content is set `low` px below 16 px, holding a title `title` px tall and,
    at its foot, a text `foot` px tall."""
    trace = f"page/row#{n}"
    content = group(
        f"{trace}/content",
        text(f"{trace}/content/title", width=208, height=title, lines=(150,)),
        text(f"{trace}/content/foot", y=168 - foot, width=208, height=foot, lines=(100,)),
        x=16,
        y=16 + low,
        width=208,
        height=168,
    )
    box = element(f"{trace}/box", width=240, height=200)
    held = group(trace, box, content, x=20 + (n - 1) * 260, y=40, width=240, height=200)
    return {**held, "component": "tests/card"}


def test_a_card_s_content_2_px_low_is_a_finding_with_each_card_beside_it() -> None:
    cards = [content_card(1, 0), content_card(2, 2), content_card(3, 0)]
    found = boxes.near_alignment(on_page(group("page/row", *cards, width=800)), STEP)
    assert [(f.code, f.where) for f in found] == [
        (boxes.NEAR_ALIGNMENT_BETWEEN_GROUPS, "page/row#1"),
        (boxes.NEAR_ALIGNMENT_BETWEEN_GROUPS, "page/row#2"),
    ]
    assert [f.message.count("; ") + 1 for f in found] == [2, 2]


def test_two_pairs_of_one_placement_on_different_lines_are_one_finding() -> None:
    """The second card's content is set 2 px low, and its title and its foot are taller: the
    placement shows at the titles' tops and the feet's bottoms, one finding (DEC-067 point
    4, "A later pair joined to a finding on the same line alone")."""
    cards = [content_card(1, 0, 30, 20), content_card(2, 2, 60, 40)]
    [finding] = boxes.near_alignment(on_page(group("page/row", *cards, width=800)), STEP)
    assert finding.message.endswith(
        "`page/row#1/content/title` and `page/row#2/content/title`, their tops 2 px apart; "
        "`page/row#1/content/foot` and `page/row#2/content/foot`, their bottoms 2 px apart"
    )


def section(trace: str, y: float, inset: float = 0) -> dict[str, Any]:
    """A section of a page on its margin, 40 px from the page's left edge: a title set
    `inset` px in, and a text below it."""
    return group(
        trace,
        text(f"{trace}/title", x=inset, width=720 - inset, height=30, lines=(200,)),
        text(f"{trace}/text", y=40, width=720, height=30, lines=(400,)),
        x=40,
        y=y,
        width=720,
        height=80,
    )


def test_one_placement_repeats_its_finding_with_each_side_that_shares_its_line() -> None:
    """A title 3 px off a margin that a header, three sections and a footer share: four
    findings between groups, one with each other side, each naming the title with that
    side's two texts, beside the one among its section's siblings (DEC-067, "What it
    costs")."""
    parts = [
        section("page/header", 0),
        section("page/s1", 100),
        section("page/s2", 200, inset=3),
        section("page/s3", 300),
        section("page/footer", 400),
    ]
    found = boxes.near_alignment(on_page(*parts), STEP)
    assert [(f.code, f.where) for f in found] == [
        (boxes.NEAR_ALIGNMENT, "page/s2/title"),
        (boxes.NEAR_ALIGNMENT_BETWEEN_GROUPS, "page/header"),
        (boxes.NEAR_ALIGNMENT_BETWEEN_GROUPS, "page/s1"),
        (boxes.NEAR_ALIGNMENT_BETWEEN_GROUPS, "page/s2"),
        (boxes.NEAR_ALIGNMENT_BETWEEN_GROUPS, "page/s2"),
    ]
    assert [f.message.count("`page/s2/title` and `") for f in found[1:]] == [0, 0, 2, 2]
    assert [f.message.count("and `page/s2/title`, their left edges 3 px") for f in found[1:3]] == [
        2,
        2,
    ]


def test_a_dot_centred_on_each_card_s_top_edge_repeats_with_each_other_card() -> None:
    """A row of four cards, a dot centred on each one's top edge: twelve findings between
    groups, beside the four among each card's siblings."""

    def dotted(n: int) -> dict[str, Any]:
        trace = f"page/row/c{n}"
        box = element(f"{trace}/box", width=140, height=100)
        dot = element(f"{trace}/dot", "path", x=67, y=-3, width=6, height=6)
        return group(trace, box, dot, x=20 + n * 150, y=40, width=140, height=100)

    found = boxes.near_alignment(on_page(group("page/row", *map(dotted, range(4)))), STEP)
    assert [f.code for f in found].count(boxes.NEAR_ALIGNMENT) == 4
    assert [f.code for f in found].count(boxes.NEAR_ALIGNMENT_BETWEEN_GROUPS) == 12


def beside_a_sign(*first: dict[str, Any], sign_first: bool = False) -> dict[str, Any]:
    """A group holding `first`, and a group 400 px right of it holding a sign 16 px square,
    100 px down."""
    one = group("page/g1", *first, width=300, height=300)
    sign = element("page/g2/sign", "path", x=100, y=100, width=16, height=16)
    two = group("page/g2", sign, x=400, width=300, height=300)
    return on_page(two, one) if sign_first else on_page(one, two)


def test_a_box_and_a_label_beside_a_sign_off_their_middle_are_one_finding() -> None:
    """The sign's middle lies 1.60 px below the box's and the label's, and its bottom 1.59 px
    above the label's: the box's pair starts the finding at the middles, and the label's
    joins it there (DEC-067, "A pair placed by its offset on the axis alone")."""
    box = element("page/g1/box", y=86.40, width=100, height=40)
    label = element("page/g1/label", x=120, y=95.21, width=60, height=22.38)
    [finding] = boxes.near_alignment(beside_a_sign(box, label), STEP)
    assert finding.message.endswith(
        "`page/g1/box` and `page/g2/sign`, their middles 1.6 px apart; `page/g1/label` and "
        "`page/g2/sign`, their middles 1.6 px apart and bottoms 1.59 px apart"
    )


@pytest.mark.parametrize("sign_first", [False, True], ids=["label-first", "sign-first"])
def test_one_placement_whose_pairs_differ_in_their_least_line_is_one_finding_in_each_order(
    sign_first: bool,
) -> None:
    """A label as wide as its words and a dot, centred on one middle, beside a sign 1.60 px
    below it: the label's pair nearly agrees at the middles and the bottoms, its least
    offset 1.59 px at the bottoms, and the dot's at the tops and the middles. One finding,
    whichever group is drawn first (DEC-067 point 4)."""
    label = filling("page/g1/label", x=120, y=95.21, width=60, height=22.38)
    dot = element("page/g1/dot", "path", x=200, y=103.00, width=6.80, height=6.80)
    found = boxes.near_alignment(beside_a_sign(label, dot, sign_first=sign_first), STEP)
    assert [(f.code, f.message.count("; ") + 1) for f in found] == [
        (boxes.NEAR_ALIGNMENT_BETWEEN_GROUPS, 2)
    ]
    first = "page/g2" if sign_first else "page/g1"
    assert found[0].where == first


def tied(*, connector: bool = True) -> dict[str, Any]:
    """Two cards joined by a tie, whose sign its component stands halfway along its line,
    2 px off the cards' middle; the scene holds the tie's connector where `connector`."""
    left = element("page/body/cards[a]", width=100, height=60)
    right = element("page/body/cards[b]", x=300, width=100, height=60)
    arrow = {
        **line("page/body/links[a-b]/arrow", 100, 30, 300, 30),
        "attached": {"start": {"id": "page/body/cards[a]"}, "end": {"id": "page/body/cards[b]"}},
    }
    sign = element("page/body/links[a-b]/sign", "path", x=192, y=24, width=16, height=16)
    parts = (arrow, sign) if connector else (sign,)
    links = group(
        "page/body/links",
        group("page/body/links[a-b]", *parts, width=400, height=60),
        width=400,
        height=60,
    )
    cards = group("page/body/cards", left, right, width=400, height=60)
    return on_page(group("page/body", cards, links, x=20, y=20, width=400, height=60))


def test_a_tie_s_part_is_compared_with_no_part_of_another_group() -> None:
    """The tie's sign lies where the tie's ends put it, 2 px below the cards' middle: no
    finding points at it. Where the scene holds no connector for the tie, its sign is
    compared as a leaf is (DEC-067 point 1)."""
    assert found_in(tied()) == []
    assert found_in(tied(connector=False)) == [
        (boxes.NEAR_ALIGNMENT_BETWEEN_GROUPS, "page/body/cards")
    ]


def test_two_parts_that_no_one_page_holds_are_not_compared() -> None:
    def slide(name: str) -> dict[str, Any]:
        inner = group(f"deck/slides[{name}]/body", element(f"deck/slides[{name}]/body/box"))
        return group(f"deck/slides[{name}]", inner, width=400, height=200)

    first, second = slide("a"), slide("b")
    second["children"][0]["children"][0]["x"] = 2
    deck = group("deck", first, second, width=400, height=200)
    pages = {"pages": ["deck/slides[a]", "deck/slides[b]"], "children": [deck]}
    assert boxes.near_alignment(pages, STEP) == []
    off_any_page = {"pages": [], "children": [group("figure", first["children"][0], width=400)]}
    assert boxes.near_alignment(off_any_page, STEP) == []


def test_a_group_is_compared_with_no_part_that_is_not_its_sibling() -> None:
    """A group's left edge lies 2 px from a box of another group, and its own box is set 20
    px in on the left and 22 px on the right: a group's box is room, compared with no part
    of another group and none nested in it (DEC-067 point 1)."""
    one = group("page/one", element("page/one/box", x=20, width=58), width=100)
    two = group("page/two", element("page/two/box", x=52, width=30), x=-50, y=100, width=300)
    assert boxes.near_alignment(on_page(one, two), STEP) == []


# --- two lists ----------------------------------------------------------------------------------


def items(
    trace: str, x: float, gap: float, *, top: float = 40, drawn_by: str = "tests/item"
) -> dict[str, Any]:
    """A list of four items `drawn_by` draws, each 30 px tall holding a text, `gap` px
    apart down."""
    entries = [
        {
            **group(
                f"{trace}#{n}",
                text(f"{trace}#{n}/text", width=200, height=30, lines=(120,)),
                y=(n - 1) * (30 + gap),
                width=200,
                height=30,
            ),
            "component": drawn_by,
        }
        for n in range(1, 5)
    ]
    return group(trace, *entries, x=x, y=top, width=200, height=300)


def test_two_lists_whose_spacings_nearly_agree_are_one_finding_naming_both() -> None:
    """Two lists of like items set 12 px and 14 px apart from one top: one finding, at the
    list drawn first, naming the two spacings and the pair of their second items' texts,
    2 px apart, which the lists' gaps explain (DEC-067 point 5)."""
    given = on_page(items("page/a", 20, 12), items("page/b", 400, 14))
    [finding] = boxes.near_alignment(given, STEP)
    assert (finding.code, finding.where, finding.fix) == (
        boxes.NEAR_ALIGNMENT_BETWEEN_GROUPS,
        "page/a",
        boxes.SPACE_IT,
    )
    gaps = (
        "between `{0}#1` and `{0}#2`, between `{0}#2` and `{0}#3` and between `{0}#3` and `{0}#4`"
    )
    assert finding.message == (
        "the spacings of the lists `page/a` and `page/b`, whose items `tests/item` draws, "
        f"nearly agree, by more than a pixel of rounding and less than {STEP_SAID}: down, "
        f"12 px, {gaps.format('page/a')} in `page/a`, and 14 px, {gaps.format('page/b')} in "
        "`page/b`, 2 px apart. The parts their gaps set off their match: `page/a#2/text` and "
        "`page/b#2/text`, their tops 2 px apart, middles 2 px apart and bottoms 2 px apart"
    )


def test_two_lists_12_and_13_5_px_apart_are_one_finding_naming_both_pairs_of_texts() -> None:
    """The second items' texts lie 1.5 px apart and the third items' 3.0 px, as much as the
    lengths of gaps before those items differ, and the fourth items' 4.5 px, a step or
    more."""
    [finding] = boxes.near_alignment(
        on_page(items("page/a", 20, 12), items("page/b", 400, 13.5)), STEP
    )
    assert finding.message.endswith(
        "set off their match: `page/a#2/text` and `page/b#2/text`, their tops 1.5 px apart, "
        "middles 1.5 px apart and bottoms 1.5 px apart; `page/a#3/text` and `page/b#3/text`, "
        "their tops 3 px apart, middles 3 px apart and bottoms 3 px apart"
    )


def test_two_lists_that_start_apart_and_miss_one_spacing_are_three_findings() -> None:
    """Lists set 12 px and 13.5 px apart, the second starting 2 px lower: the two lists' as
    siblings, naming their first items' texts, the two lists' spacings, and their second
    items' texts, 3.5 px apart, which neither explains (DEC-067, "What it costs")."""
    found = boxes.near_alignment(
        on_page(items("page/a", 20, 12), items("page/b", 400, 13.5, top=42)), STEP
    )
    assert [(f.code, f.where) for f in found] == [
        (boxes.NEAR_ALIGNMENT, "page/a"),
        (boxes.NEAR_ALIGNMENT_BETWEEN_GROUPS, "page/a"),
        (boxes.NEAR_ALIGNMENT_BETWEEN_GROUPS, "page/a"),
    ]
    assert found[0].message.endswith(
        "`page/a#1/text` and `page/b#1/text`, their tops 2 px apart, middles 2 px apart and "
        "bottoms 2 px apart"
    )
    assert "set off their match" not in found[1].message
    assert found[2].message.endswith(
        "`page/a#2/text` and `page/b#2/text`, their tops 3.5 px apart, middles 3.5 px apart "
        "and bottoms 3.5 px apart"
    )


def test_two_lists_whose_items_different_components_draw_are_not_compared() -> None:
    given = on_page(items("page/a", 20, 12), items("page/b", 400, 14, drawn_by="tests/tag"))
    assert found_in(given) == [(boxes.NEAR_ALIGNMENT_BETWEEN_GROUPS, "page/a")]
    [finding] = boxes.near_alignment(given, STEP)
    assert finding.message.startswith("at `page/a` and `page/b`, parts of different groups")


def test_a_spacing_near_one_list_s_own_is_reported_among_its_siblings_alone() -> None:
    """The first list's gaps are 12 px and 14 px, and the second's 14 px: the near miss lies
    among the first list's own spacings."""
    first = items("page/a", 20, 12)
    for n, entry in enumerate(first["children"][2:], start=3):
        entry["y"] = (n - 1) * 42 + 2
    given = on_page(first, items("page/b", 400, 14))
    assert [code for code, _ in found_in(given)].count(boxes.NEAR_ALIGNMENT) == 1
    assert not any(
        f.message.startswith("the spacings of the lists") for f in boxes.near_alignment(given, STEP)
    )


def test_the_gap_between_two_parts_of_different_groups_is_no_spacing() -> None:
    """Three boxes in a row, the first two in one group 8 px apart and the third in another
    group, 10 px after the second: no spacing is taken across the two groups."""
    one = group("page/one", element("page/one/a"), element("page/one/b", x=48), width=88)
    two = group("page/two", element("page/two/c", x=10, width=40), x=88, width=50)
    assert boxes.near_alignment(on_page(one, two), STEP) == []


def node(
    trace: str, y: float, width: float, gaps_below: tuple[float, ...]
) -> tuple[dict[str, Any], float]:
    """A node a tree's component draws, which draws its children with itself: its text, and,
    where `gaps_below` gives a gap, a list of two children that gap apart down, the first
    holding the next level. With its height."""
    parts: list[dict[str, Any]] = [text(f"{trace}/text", width=width, height=24, lines=(120,))]
    height = 24.0
    if gaps_below:
        children, top = [], 0.0
        for n in range(1, 3):
            child, tall = node(
                f"{trace}/children#{n}", top, width - 24, gaps_below[1:] if n == 1 else ()
            )
            children.append(child)
            top += tall + gaps_below[0]
        inner = top - gaps_below[0]
        parts.append(
            group(f"{trace}/children", *children, x=24, y=32, width=width - 24, height=inner)
        )
        height = 32 + inner
    held = group(trace, *parts, y=y, width=width, height=height)
    return {**held, "component": "tests/node"}, height


@pytest.mark.parametrize(
    ("b_gap", "lists"), [(14, []), (15.5, [("page/tree#1/children", "page/tree#2/children")])]
)
def test_a_tree_s_lists_are_compared_at_one_level_alone(
    b_gap: float, lists: list[tuple[str, str]]
) -> None:
    """A root list R, its items A and B 12 px apart; A holds LA and B holds LB, their items
    14 px apart, and the first item of each holds LA' or LB', 16 px apart. No two levels
    are compared, in one branch or in two; with LB's items 15.5 px apart, LA with LB is one
    finding (DEC-067 point 5)."""
    first, tall = node("page/tree#1", 0, 300, (14, 16))
    second, other = node("page/tree#2", tall + 12, 300, (b_gap, 16))
    tree = group("page/tree", first, second, x=20, y=20, width=300, height=tall + 12 + other)
    found = boxes.near_alignment(on_page(tree), STEP)
    assert [f.message.split("`")[1:4:2] for f in found if f.message.startswith("the spacings")] == [
        list(each) for each in lists
    ]


def test_cards_placed_by_use_and_the_sub_cards_one_holds_lie_at_different_levels() -> None:
    """A component places two cards 12 px apart, neither an entry's group, and the first
    holds a list of sub-cards 14 px apart, which the card draws too: the sub-cards lie in a
    card, at the next level, so the two lists are not compared."""

    def sub_card(trace: str, y: float) -> dict[str, Any]:
        box = element(f"{trace}/box", width=200, height=30)
        title = text(f"{trace}/title", x=8, y=5, width=184, height=20, lines=(100,))
        return {**group(trace, box, title, y=y, width=200, height=30), "component": "tests/card"}

    subs = group(
        "page/stack/c1/subs",
        sub_card("page/stack/c1/subs#1", 0),
        sub_card("page/stack/c1/subs#2", 44),
        x=16,
        y=40,
        width=200,
        height=74,
    )
    c1 = group(
        "page/stack/c1",
        element("page/stack/c1/box", width=300, height=130),
        text("page/stack/c1/title", x=16, y=16, width=268, height=20, lines=(150,)),
        subs,
        width=300,
        height=130,
    )
    c2 = group(
        "page/stack/c2",
        element("page/stack/c2/box", width=300, height=60),
        text("page/stack/c2/title", x=16, y=16, width=268, height=20, lines=(150,)),
        y=142,
        width=300,
        height=60,
    )
    placed = [{**c1, "component": "tests/card"}, {**c2, "component": "tests/card"}]
    stack = {**group("page/stack", *placed, x=20, y=20, width=300, height=202), "component": "d"}
    assert boxes.near_alignment(on_page(stack), STEP) == []


@pytest.mark.parametrize(
    ("children_gap", "lists"),
    [
        (14, []),
        (
            15.5,
            [
                ("page/left/children", "page/tree#1/children"),
                ("page/left/children", "page/tree#2/children"),
            ],
        ),
    ],
)
def test_a_tree_rooted_in_one_node_beside_a_tree_rooted_in_a_list(
    children_gap: float, lists: list[tuple[str, str]]
) -> None:
    """A tree rooted in one node, its children 14 px apart, beside a tree rooted in a list of
    nodes 12 px apart, each node's children `children_gap` apart: the one node is a node of
    its tree as an item is, so its children lie at the level of the second tree's children,
    not of its roots."""
    alone, _ = node("page/left", 20, 300, (14,))
    alone["x"] = 20
    first, tall = node("page/tree#1", 0, 300, (children_gap,))
    second, other = node("page/tree#2", tall + 12, 300, (children_gap,))
    tree = group("page/tree", first, second, x=400, y=20, width=300, height=tall + 12 + other)
    found = boxes.near_alignment(on_page(alone, tree), STEP)
    spacings = [f for f in found if f.message.startswith("the spacings")]
    assert [f.message.split("`")[1:4:2] for f in spacings] == [list(each) for each in lists]
    assert [f for f in found if f.code == boxes.NEAR_ALIGNMENT] == []
    if lists:
        assert "set off their match: `page/left/children#2/text` and" in spacings[0].message
        assert "set off their match" not in spacings[1].message


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
