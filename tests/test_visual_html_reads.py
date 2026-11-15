"""`scripts/visual_html_reads.py`: the maintainer's measure of the HTML renderer's read of cover
through a browser (visual-communication DEC-037, project-kit#3262). It lays each dot of the SVG
probe at each em on pages the renderer writes, reads each tally the read makes from the tally's
own images, lays a box over each dot, and says what the read names. The tests here read its
parts in this process, and one draws through a real browser where the machine has one."""

from __future__ import annotations

import itertools
from collections.abc import Mapping
from types import ModuleType
from typing import Any

import pytest
from scripts import visual_html_reads as reads
from scripts import visual_svg_reads as svg_reads

from tests.test_visual_communication_viewing_browser import real_browser

#: A tally's clip, drawn at two device pixels to a px, and the page it lies on, in px of the
#: document.
CLIP = {"x": 4.0, "y": 6.0, "width": 10.0, "height": 10.0}
PAGE = {"x": 5.0, "y": 7.0, "width": 100.0, "height": 50.0}


def spot(
    pixels: Mapping[tuple[int, int], tuple[int, int]], counted: Mapping[str, int] | None = None
) -> reads.Spot:
    return reads.Spot(
        0, 10.0, PAGE, CLIP, 2.0, 255.0, pixels, counted or {"strong": 0, "hidden": 0}
    )


def test_each_dot_at_each_em_lies_in_a_cell_of_its_own_on_a_page_that_holds_it() -> None:
    ems = (10.0, 20.0, 40.0, 96.0)
    pages = reads.laid(svg_reads.DOTS, ems, 0.5)
    plants = [plant for page in pages for plant in page.plants]
    assert [(plant.em, plant.dot) for plant in plants] == list(
        itertools.product(ems, svg_reads.DOTS)
    )
    assert len({plant.text for plant in plants}) == len(plants)
    for page in pages:
        cells = []
        for plant in page.plants:
            assert plant.page == page.id
            assert plant.text.startswith(f"{page.id}/")
            assert plant.size == plant.em / 0.5
            right = plant.left + reads.CELL_WIDTH * plant.size
            bottom = plant.top + reads.CELL_HEIGHT * plant.size
            assert right <= page.width + 1e-9
            assert bottom <= page.height + 1e-9
            cells.append((plant.left, plant.top, right, bottom))
        for one, other in itertools.combinations(cells, 2):
            assert (
                one[2] <= other[0] or other[2] <= one[0] or one[3] <= other[1] or other[3] <= one[1]
            )


def test_a_row_and_a_page_stay_within_what_a_browser_draws_at_once() -> None:
    scale = 2.0
    pages = reads.laid(svg_reads.DOTS, tuple(tenth / 10 for tenth in range(100, 401)), scale)
    assert len(pages) > 1
    assert [page.id for page in pages] == [f"{reads.PAGE}-{at}" for at in range(len(pages))]
    for page in pages:
        assert page.width * scale <= reads.ROW_PIXELS
        assert page.height * scale <= reads.PAGE_PIXELS


def test_a_pixel_is_strong_where_the_letters_alone_change_it_by_more_than_half() -> None:
    found = spot({(0, 0): (255, 0), (0, 1): (128, 128), (0, 2): (127, 0)})
    assert [found.is_strong(pixel) for pixel in sorted(found.pixels)] == [True, True, False]
    assert found.ink == {(0, 0): 0, (0, 1): 127, (0, 2): 128}
    assert found.shows == {(0, 0): 0, (0, 1): 128, (0, 2): 0}
    assert found.hidden == [(0, 0), (0, 2)]


def test_the_probe_agrees_with_the_tally_where_it_counts_strong_ink_and_what_is_hidden_alike() -> (
    None
):
    pixels = {(0, 0): (255, 0), (0, 1): (200, 50), (0, 2): (40, 0)}
    assert spot(pixels, {"strong": 2, "past": 0, "hidden": 1}).agrees()
    assert not spot(pixels, {"strong": 2, "past": 0, "hidden": 2}).agrees()
    assert not spot(pixels, {"strong": 3, "past": 0, "hidden": 1}).agrees()


def test_a_box_over_pixels_lies_a_pixel_past_them_in_px_of_their_page() -> None:
    """Columns 3 and 4 and rows 2 and 3 of a clip at (4, 6), two image pixels to a px, on a page
    at (5, 7): a pixel past them on each side runs from column 2 to 5 and row 1 to 4."""
    found = spot({(2, 3): (255, 0), (3, 4): (255, 0)})
    assert found.page_box([(2, 3), (3, 4)], 1) == {"x": 0.0, "y": -0.5, "width": 2.0, "height": 2.0}
    assert found.page_box([(2, 3)]) == {"x": 0.5, "y": 0.0, "width": 0.5, "height": 0.5}


def test_a_picture_starts_at_the_device_pixel_nearest_its_clip_a_half_rounding_up() -> None:
    """As Chrome took its pictures of clips at whole px, at scales whose device pixels fall
    between them."""
    assert reads.picture_start(2350, 0.5) == 1175
    assert reads.picture_start(2351, 0.5) == 1176
    assert reads.picture_start(2353, 0.8167) == 1922
    assert reads.picture_start(2354, 0.8167) == 1923
    assert reads.picture_start(2355, 0.8167) == 1923
    assert reads.picture_start(2353, 1.225) == 2882
    assert reads.picture_start(2354, 1.225) == 2884


def test_a_box_over_pixels_starts_where_the_picture_does_not_where_its_clip_does() -> None:
    """A clip at (2351, 2351), drawn at half a device pixel to a px, starts its picture at
    device pixel 1176, px 2352: its first pixel lies a px past the clip's start, and each
    pixel runs two px."""
    clip = {"x": 2351.0, "y": 2351.0, "width": 2205.0, "height": 2205.0}
    found = reads.Spot(0, 10.0, {"x": 0.0, "y": 0.0}, clip, 0.5, 255.0, {}, {})
    assert found.page_box([(0, 0), (1100, 1100)]) == {
        "x": 2352.0,
        "y": 2352.0,
        "width": 2202.0,
        "height": 2202.0,
    }


def document() -> list[dict[str, Any]]:
    """A document of one page, holding one text of a line of two spans, "end" and "."."""
    spans = [{"index": 4, "text": "end", "em": 20.0}, {"index": 5, "text": ".", "em": 20.0}]
    return [{"id": "dots-0", "texts": [{"id": "dots-0/0-0", "lines": [spans]}]}]


#: What the probe's own reading of a tally gives of the span "." of `document`.
INKED = {
    "apart": 255,
    "spans": [{"index": 5, "pixels": [[1, 2, 255, 0]]}],
}
ASKED = [{"index": 5, "box": dict(CLIP), "page": dict(PAGE)}]
COUNTED = [{"strong": 1, "past": 0, "hidden": 1}]


def test_a_capture_finds_a_tallied_span_by_its_file_its_text_its_line_and_its_place() -> None:
    capture = reads.Capture()
    capture.read(reads.FILE, document())
    capture.tallied(reads.FILE, CLIP, 2.0, ASKED, COUNTED, INKED)
    found = capture.spot(reads.FILE, "dots-0/0-0", 0, 1)
    assert found is not None
    assert (found.index, found.em, found.pixels, found.page, found.clip, found.scale) == (
        5,
        20.0,
        {(1, 2): (255, 0)},
        PAGE,
        CLIP,
        2.0,
    )
    assert found.agrees()
    assert capture.spot(reads.FILE, "dots-0/0-0", 0, 0) is None
    assert capture.spot("planted.html", "dots-0/0-0", 0, 1) is None


def fake_browser() -> ModuleType:
    """A module of the browser module's shape, whose reads give `document`, its tally and the
    probe's own reading of it, and whose pre-filter passes over every span."""
    module = ModuleType("fake_browser")

    class Started:
        def __init__(self, own: str) -> None:
            self._own = own
            self.scale = 2.0

        def ask(self, function: str, *arguments: Any) -> Any:
            return {"read": document(), "tally": COUNTED, reads.INKED: INKED}[function]

    vars(module).update(READ="read", TALLY="tally", _Started=Started, _passed_over=lambda *_: True)
    return module


def test_while_captured_each_read_and_tally_of_a_file_is_kept_and_the_module_left_as_it_was() -> (
    None
):
    module = fake_browser()
    names = vars(module)
    ask, passed_over = names["_Started"].ask, names["_passed_over"]
    with reads.captured(module, every=True) as capture:
        started = names["_Started"](f"file:///somewhere/{reads.FILE}")
        started.ask("read")
        started.ask("tally", ["strong", "ground", "shown", "unshown"], CLIP, ASKED)
        assert not names["_passed_over"]({"id": "dots-0"}, {}, [])
        assert names["_passed_over"]({"id": "planted"}, {}, [])
    assert names["_Started"].ask is ask
    assert names["_passed_over"] is passed_over
    assert capture.spot(reads.FILE, "dots-0/0-0", 0, 1) is not None
    with reads.captured(module, every=False):
        assert names["_passed_over"]({"id": "dots-0"}, {}, [])


def hidden(dot: Any, em: float, **found: Any) -> reads.Hidden:
    return reads.Hidden(dot, em, 1.0, ink=4, strong=2, whole=True, **found)


def test_the_summary_counts_the_dots_the_read_leaves_unnamed_and_what_dec_045_would_name() -> None:
    stop, *_ = svg_reads.DOTS
    every = [
        hidden(stop, 10.0, lost=2, found=2, named=True),
        hidden(stop, 20.0, lost=2, found=2, threshold=False, island=True),
        hidden(stop, 30.0, lost=2, found=2, threshold=True, island=True),
        reads.Hidden(stop, 40.0, 1.0),
    ]
    lines = reads.summary([stop], every)
    assert lines[0] == (
        "full stop: 4 draws, found at 3, hidden whole at 3, with no strong ink at 0"
    )
    assert lines[1].startswith(
        "  named by the read at 1; hidden whole and left unnamed at 2: 1 below an em of 25, 1"
    )
    assert lines[2] == (
        "  of those, DEC-045's threshold names 1 (ems 30.0 to 30.0), its measure of islands 2"
        " (ems 20.0 to 30.0), neither 0"
    )
    assert lines[-2:] == [
        "spans the probe counted otherwise than the read: 0",
        "draws at which a box hid a neighbour's strong ink: 0",
    ]
    assert hidden(stop, 20.0).sliver == pytest.approx(4.0)


@real_browser
def test_a_real_browser_names_a_dot_hidden_whole_where_its_loss_reaches_the_sliver() -> None:
    """Each dot at an em of 20, at a scale of 1: the box hides it whole and no neighbour's
    strong ink, the probe counts each span as the read does, and the read names each dot whose
    loss reaches the sliver and no other. What the face draws, and so which dots those are, this
    test leaves to the machine."""
    found = reads.modules()
    browser = found.look.viewing_browser
    program = browser.find()
    pages = reads.laid(found.reads.DOTS, (20.0,), 1.0)
    try:
        first = reads.drawn(found, found.look.FONT, pages, 1.0, program, {}, every=True)
        boxes = reads.boxes_over(found, pages, first)
        second = reads.drawn(found, found.look.FONT, pages, 1.0, program, boxes, every=False)
    except browser.Stopped as stop:
        if stop.sandbox:
            pytest.skip(f"a sandbox stopped the browser: {stop}")
        raise
    read = [reads.hidden_of(found, plant, 1.0, second) for page in pages for plant in page.plants]
    assert len(read) == len(found.reads.DOTS)
    for each in read:
        assert each.ink and each.whole and each.agrees and not each.neighbours
        assert each.em == pytest.approx(20.0)
        assert each.named == (each.found > 0 and each.lost >= each.sliver)
