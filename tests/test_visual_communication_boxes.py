"""The checks of boxes (visual-communication DEC-046 point 3): edges that nearly line up, and
boxes that overlap, among the siblings of each scene.

- **Edges that nearly line up** (`near-alignment`): two siblings whose edges or centres on one
  axis differ by more than a pixel of rounding and by less than the brand's smallest step of
  space, unless they line up on another line of that axis; and two spacings between the
  siblings of a group that nearly agree.
- **Boxes that overlap** (`box-overlap`): two siblings whose boxes overlap, where neither
  holds the other. A text drawn under its sibling is left out where the viewing step's report
  names each text a part covers (DEC-037 point 1).
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


def test_a_step_no_longer_than_a_pixel_leaves_nothing_near() -> None:
    given = scene(element("figure/a"), element("figure/b", x=0.9, y=60))
    assert boxes.near_alignment(given, boxes.Step("space.1", 1.0)) == []
    assert boxes.near_alignment(given, None) == []


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


def test_a_part_inset_a_little_in_the_box_that_holds_it_is_near() -> None:
    """A box and the text it holds are siblings of one component: an inset of 2 px on one
    side nearly lines the text up with the box's edge."""
    card = group(
        "figure/card",
        element("figure/card/box", width=100, height=40),
        element("figure/card/head", "text", x=2, y=10, width=90, height=20),
        width=100,
        height=40,
    )
    [message] = near(boxes.near_alignment(scene(card), STEP))
    assert message.startswith("`figure/card/box` and `figure/card/head` nearly line up across: ")


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
    assert boxes.overlaps(given, cover_read=False) == []


def test_a_group_that_draws_only_lines_is_left_out_as_a_line_is() -> None:
    """A tie's item lies in its pattern's whole frame and draws its connector alone, so it
    would hold and nearly line up with everything beside it."""
    arrow = line("figure/links[a-b]/arrow", 2, 18, 100, 22)
    tie = group("figure/links[a-b]", arrow, x=2, width=398, height=200)
    given = scene(element("figure/card", x=0, width=100), tie)
    assert boxes.near_alignment(given, STEP) == []
    assert boxes.overlaps(given, cover_read=False) == []


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
    assert boxes.overlaps(pages, cover_read=False) == []


def test_only_siblings_are_compared() -> None:
    """Two boxes 2 px apart in two cards are no siblings: the cards, which line up, are."""
    first = group("figure/one", element("figure/one/box"), width=40, height=40)
    second = group("figure/two", element("figure/two/box", x=2), y=60, width=40, height=40)
    assert boxes.near_alignment(scene(first, second), STEP) == []


# --- boxes that overlap -------------------------------------------------------------------------


def test_two_boxes_that_overlap_where_neither_holds_the_other_ask_the_reviewer() -> None:
    [finding] = boxes.overlaps(
        scene(element("figure/a"), element("figure/b", x=30, y=20)), cover_read=False
    )
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
    assert boxes.overlaps(held, cover_read=False) == []
    within = scene(element("figure/a", width=100, height=100), element("figure/b", x=-0.5, y=8))
    assert boxes.overlaps(within, cover_read=False) == []
    grazing = scene(element("figure/a"), element("figure/b", x=39.2, y=20))
    assert boxes.overlaps(grazing, cover_read=False) == []


def written(
    trace: str, *widths: float, anchor: str = "start", x: float = 0, width: float = 100
) -> dict[str, Any]:
    """A text of a line of each of `widths`, 20 px high, standing by `anchor` in its width."""
    lines = [{"text": "Words", "width": each, "baseline": 15, "paragraph": 0} for each in widths]
    text = element(trace, "text", x=x, width=width, height=20 * len(widths))
    return {**text, "text-anchor": anchor, "line-height": 20, "lines": lines}


def test_a_text_under_its_sibling_is_left_to_the_report_where_it_reads_cover() -> None:
    """The note is drawn first and the legend over the end of its line. Where the viewing
    step's report names each text a part covers, as through a browser, it names the note, so
    the check does not report it again. Elsewhere it is the check's to report."""
    given = scene(
        written("figure/note", 100), element("figure/legend", x=80, y=10, width=60, height=30)
    )
    assert boxes.overlaps(given, cover_read=True) == []
    [finding] = boxes.overlaps(given, cover_read=False)
    assert finding.where == "figure/note"


@pytest.mark.parametrize(
    ("anchor", "reported"),
    [("start", True), ("middle", True), ("end", False)],
    ids=["start", "middle", "end"],
)
def test_a_text_is_left_out_only_where_its_sibling_lies_over_one_of_its_lines(
    anchor: str, reported: bool
) -> None:
    """A line 40 px wide in a text 100 px wide: at its start or its middle, the legend lies
    over none of it, only over the room the line leaves, so the report names nothing there and
    the check reports the overlap; at its end, the legend lies over the line."""
    given = scene(
        written("figure/note", 40, anchor=anchor),
        element("figure/legend", x=75, y=10, width=60, height=30),
    )
    assert bool(boxes.overlaps(given, cover_read=True)) is reported


def test_each_line_of_a_text_stands_under_the_one_before() -> None:
    """A long first line and a short second: a legend beside the second line, below the
    first, lies over neither."""
    beside = element("figure/legend", x=80, y=25, width=60, height=30)
    assert boxes.overlaps(scene(written("figure/note", 100, 30), beside), cover_read=True)
    over = element("figure/legend", x=80, y=10, width=60, height=30)
    assert boxes.overlaps(scene(written("figure/note", 100, 30), over), cover_read=True) == []


def test_a_text_drawn_over_its_sibling_is_reported_where_the_report_reads_cover() -> None:
    """A label over a picture covers none of its own letters, so the report names nothing,
    and the check reports the overlap."""
    given = scene(
        element("figure/picture", "image", width=100, height=100),
        written("figure/label", 60, x=80, width=60),
    )
    [finding] = boxes.overlaps(given, cover_read=True)
    assert finding.message.endswith("`figure/label` is drawn over `figure/picture`")


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


@pytest.mark.parametrize(
    ("exports", "reported"),
    [(["svg"], True), (["svg", "html"], False)],
    ids=["through-svg", "through-a-browser"],
)
def test_a_covered_text_is_left_to_the_report_of_a_piece_read_through_a_browser(
    tmp_path: Path, exports: list[str], reported: bool
) -> None:
    """The viewing step reads a piece that exports `html` through a browser by default, and
    its report then names the head the badge covers: the check reports the overlap of a piece
    read through the SVG renderer alone, at the piece's own file."""
    root = drawing_project(tmp_path, picture=False, exports=exports)
    write(root / LOCAL / "covered.yaml", COVERED)
    write_body(root, body={"use": "piece/covered", "head": "Plan the work."})
    found = [f for f in checks.computed(project_of(root)) if f.code == boxes.BOX_OVERLAP]
    assert [(f.file, f.where) for f in found] == (
        [("piece.yaml", "figure/body/head")] if reported else []
    )
