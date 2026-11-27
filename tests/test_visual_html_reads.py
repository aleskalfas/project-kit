"""`scripts/visual_html_reads.py`: the maintainer's measure of the HTML renderer's read of cover
and cut through a browser (visual-communication DEC-037, DEC-054, project-kit#3262). It lays
plants at each em on pages the renderer writes, in a light key, a dark key or the forced
palettes, reads each tally the read makes from the tally's own images, lays a box over each
plant, and says what the read names by its sliver and what the measure of islands names. The
tests here read its parts in this process, and some draw through a real browser where the
machine has one: those of DEC-054's Implications, which draw the dots, a full stop past the
page's edge and a graze through the read as built, on the probe's pages."""

from __future__ import annotations

import contextlib
import itertools
from collections import Counter
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, replace
from types import ModuleType
from typing import Any

import pytest
from scripts import visual_html_reads as reads
from scripts import visual_svg_reads as svg_reads

from tests.in_process import load
from tests.test_visual_communication_viewing_browser import real_browser

viewing_tool, viewing_browser, islands = load(
    "visual-communication", "viewing_tool", "viewing_browser", "islands"
)

#: A tally's clip, drawn at two device pixels to a px, its images' size, and the page it lies
#: on, in px of the document. A pixel's centre lies on the page from row 2 and column 2.
CLIP = {"x": 4.0, "y": 6.0, "width": 10.0, "height": 10.0}
SIZE = (20, 20)
PAGE = {"x": 5.0, "y": 7.0, "width": 100.0, "height": 50.0}


def spot(
    pixels: Mapping[tuple[int, int], tuple[int, int]],
    counted: Mapping[str, int] | None = None,
    em: float = 10.0,
) -> reads.Spot:
    return reads.Spot(
        0,
        em,
        PAGE,
        CLIP,
        2.0,
        255.0,
        pixels,
        counted or {"strong": 0, "past": 0, "hidden": 0},
        SIZE,
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
            right = plant.left + reads.cell_width(plant.dot) * plant.size
            bottom = plant.top + reads.CELL_HEIGHT * plant.size
            assert right <= page.width + 1e-9
            assert bottom <= page.height + 1e-9
            cells.append((plant.left, plant.top, right, bottom))
        for one, other in itertools.combinations(cells, 2):
            assert (
                one[2] <= other[0] or other[2] <= one[0] or one[3] <= other[1] or other[3] <= one[1]
            )


def test_each_step_of_a_graze_is_a_plant_of_its_own_in_a_cell_as_wide_as_its_words() -> None:
    words = reads.Words("descenders", (reads.GRAZED["descenders"],))
    pages = reads.laid((words,), (10.0, 20.0), 1.0, reads.GRAZE_STEPS)
    plants = [plant for page in pages for plant in page.plants]
    assert [(plant.em, plant.step) for plant in plants] == list(
        itertools.product((10.0, 20.0), reads.GRAZE_STEPS)
    )
    assert reads.cell_width(words) == 2 * reads.TEXT_LEFT + reads.ADVANCE * 16
    assert reads.cell_width(svg_reads.DOTS[0]) == reads.CELL_WIDTH


def test_a_row_and_a_page_stay_within_what_a_browser_draws_at_once() -> None:
    scale = 2.0
    pages = reads.laid(svg_reads.DOTS, tuple(tenth / 10 for tenth in range(100, 401)), scale)
    assert len(pages) > 1
    assert [page.id for page in pages] == [f"{reads.PAGE}-{at}" for at in range(len(pages))]
    for page in pages:
        assert page.width * scale <= reads.ROW_PIXELS
        assert page.height * scale <= reads.PAGE_PIXELS


def test_a_palette_is_light_where_its_ground_is_lighter_than_its_text_and_forced_where_so() -> None:
    black, white = (0, 0, 0), (255, 255, 255)
    assert reads.palette_of(black, white, False) == "light"
    assert reads.palette_of(white, black, False) == "dark"
    assert reads.palette_of(white, black, True) == "forced dark"
    assert reads.palette_shown(viewing_browser.Shown({}, (), _empty_read(), "light"), "dark") == (
        "forced light"
    )
    assert reads.palette_shown(viewing_browser.Shown({}, (), _empty_read()), "dark") == "dark"


def _empty_read() -> Any:
    return viewing_browser.Read((), (), (), (), ())


def test_a_pixel_is_strong_where_the_letters_alone_change_it_by_more_than_half() -> None:
    found = spot({(2, 2): (255, 0), (2, 3): (128, 128), (2, 4): (127, 0)})
    assert [found.is_strong(pixel) for pixel in sorted(found.pixels)] == [True, True, False]
    assert found.ink == {(2, 2): 0, (2, 3): 127, (2, 4): 128}
    assert found.shows == {(2, 2): 0, (2, 3): 128, (2, 4): 0}
    assert found.hidden == [(2, 2), (2, 4)]


def test_a_pixel_past_the_page_is_cut_and_neither_hidden_nor_shown() -> None:
    """Rows 0 and 1, and columns 0 and 1, lie before the page's edges: their centres fall at
    6.25 and 6.75 px, against the page's top at 7, and at 4.25 and 4.75, against its left at
    5."""
    found = spot({(1, 2): (255, 0), (2, 1): (255, 0), (2, 2): (255, 0), (3, 3): (255, 255)})
    assert found.beyond == [(1, 2), (2, 1)]
    assert found.hidden == [(2, 2)]
    assert found.shows == {(2, 2): 0, (3, 3): 255}


def test_the_probe_agrees_with_the_tally_where_it_counts_strong_ink_past_and_hidden_alike() -> None:
    pixels = {(1, 2): (255, 0), (2, 2): (255, 0), (2, 3): (200, 50), (2, 4): (40, 0)}
    assert spot(pixels, {"strong": 3, "past": 1, "hidden": 1}).agrees()
    assert not spot(pixels, {"strong": 3, "past": 0, "hidden": 1}).agrees()
    assert not spot(pixels, {"strong": 3, "past": 1, "hidden": 2}).agrees()
    assert not spot(pixels, {"strong": 4, "past": 1, "hidden": 1}).agrees()


def test_a_box_over_pixels_lies_a_pixel_past_them_in_px_of_their_page() -> None:
    """Columns 3 and 4 and rows 2 and 3 of a clip at (4, 6), two image pixels to a px, on a page
    at (5, 7): a pixel past them on each side runs from column 2 to 5 and row 1 to 4."""
    found = spot({(2, 3): (255, 0), (3, 4): (255, 0)})
    assert found.page_box([(2, 3), (3, 4)], 1) == {"x": 0.0, "y": -0.5, "width": 2.0, "height": 2.0}
    assert found.page_box([(2, 3)]) == {"x": 0.5, "y": 0.0, "width": 0.5, "height": 0.5}
    assert found.row_on_page(4) == 1.0


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
    found = reads.Spot(0, 10.0, {"x": 0.0, "y": 0.0}, clip, 0.5, 255.0, {}, {}, (1103, 1103))
    assert found.page_box([(0, 0), (1100, 1100)]) == {
        "x": 2352.0,
        "y": 2352.0,
        "width": 2202.0,
        "height": 2202.0,
    }


def test_a_graze_box_lies_its_steps_in_eighths_of_a_device_pixel_above_the_counted_foot() -> None:
    """The counted ink's lowest row is row 3, the faint pixel of row 4 aside, so its foot lies
    at row 4: a px down the page, two device pixels to a px. Step 8 lies a device pixel, half a
    px, above it, step -4 half a device pixel below it, and the box runs an em of 5 px below
    the foot, from a pixel left of the ink to a pixel right of it."""
    found = spot({(2, 3): (255, 0), (3, 5): (128, 128), (4, 4): (20, 20)})
    assert found.ink[(4, 4)] > viewing_tool.FAINT
    assert reads.graze_box(found, 0, 5.0, viewing_tool.FAINT) == {
        "x": 0.0,
        "y": 1.0,
        "width": 2.5,
        "height": 5.0,
    }
    assert reads.graze_box(found, 8, 5.0, viewing_tool.FAINT)["y"] == 0.5
    assert reads.graze_box(found, -4, 5.0, viewing_tool.FAINT)["y"] == 1.25


def test_a_graze_box_drawn_in_two_palettes_takes_the_lowest_foot_and_the_widest_reach() -> None:
    words = reads.Words("descenders", ("gy",))
    [page] = reads.laid((words,), (10.0,), 2.0, (0,))
    [plant] = page.plants
    capture = reads.Capture()
    for palette, pixels in (("light", {(2, 3): (255, 0)}), ("dark", {(3, 5): (255, 0)})):
        capture.emulated = {"forced-colors": "active", "palette": palette}
        capture.read(reads.FILE, [_document_of(plant.text, ("gy",))])
        held = {"apart": 255, "width": 20, "height": 20, "spans": [_inked(4, pixels)]}
        held.update(_colours(palette))
        capture.tallied(reads.FILE, CLIP, 2.0, [_asked(4)], [COUNTED[0]], held)
    first = reads.Drawn(capture, {})
    [(text, box)] = reads.graze_boxes([page], first, viewing_tool.FAINT).items()
    assert text == plant.text
    assert box == {"x": 0.0, "y": 1.0, "width": 2.5, "height": 5.0}


def document() -> list[dict[str, Any]]:
    """A document of one page, holding one text of a line of two spans, "end" and "."."""
    spans = [{"index": 4, "text": "end", "em": 20.0}, {"index": 5, "text": ".", "em": 20.0}]
    return [{"id": "probe-0", "texts": [{"id": "probe-0/0-0", "lines": [spans]}]}]


def _document_of(text: str, runs: tuple[str, ...]) -> dict[str, Any]:
    spans = [{"index": 4 + at, "text": words, "em": 5.0} for at, words in enumerate(runs)]
    return {"id": "probe-0", "texts": [{"id": text, "lines": [spans]}]}


def _inked(index: int, pixels: Mapping[tuple[int, int], tuple[int, int]]) -> dict[str, Any]:
    return {"index": index, "pixels": [[*pixel, *values] for pixel, values in pixels.items()]}


def _asked(index: int) -> dict[str, Any]:
    return {"index": index, "box": dict(CLIP), "page": dict(PAGE)}


def _colours(palette: str) -> dict[str, list[int]]:
    black, white = [0, 0, 0], [255, 255, 255]
    return (
        {"text": black, "behind": white} if palette == "light" else {"text": white, "behind": black}
    )


#: What the probe's own reading of a tally gives of the span "." of `document`.
INKED = {
    "apart": 255,
    "text": [0, 0, 0],
    "behind": [255, 255, 255],
    "width": 20,
    "height": 20,
    "spans": [_inked(5, {(3, 2): (255, 0)})],
}
ASKED = [_asked(5)]
COUNTED = [{"strong": 1, "past": 0, "hidden": 1}]


def test_a_capture_finds_a_tallied_span_by_its_file_its_text_its_line_and_its_place() -> None:
    capture = reads.Capture()
    capture.read(reads.FILE, document())
    capture.tallied(reads.FILE, CLIP, 2.0, ASKED, COUNTED, INKED)
    [reading] = capture.of(reads.FILE)
    assert reading.palette == "light"
    found = reading.spot("probe-0/0-0", 0, 1)
    assert found is not None
    assert (found.index, found.em, found.pixels, found.page, found.clip, found.scale) == (
        5,
        20.0,
        {(3, 2): (255, 0)},
        PAGE,
        CLIP,
        2.0,
    )
    assert found.agrees()
    assert reading.spot("probe-0/0-0", 0, 0) is None
    assert capture.of("planted.html") == []
    assert capture.files() == [reads.FILE]


def test_a_reading_gives_each_span_of_a_text_in_order_and_none_for_one_no_tally_read() -> None:
    capture = reads.Capture()
    capture.read(reads.FILE, document())
    capture.tallied(reads.FILE, CLIP, 2.0, ASKED, COUNTED, INKED)
    [reading] = capture.of(reads.FILE)
    [(end, unread), (stop, read)] = reading.spots_of("probe-0/0-0")
    assert (end.characters, end.at, unread) == ("end", 0, None)
    assert (stop.characters, stop.at) == (".", 1)
    assert read is reading.spot("probe-0/0-0", 0, 1)
    assert reading.spots_of("another") == []


def test_a_capture_keeps_a_reading_for_each_emulation_named_by_the_colours_it_read_in() -> None:
    capture = reads.Capture()
    for palette in ("light", "dark"):
        capture.emulated = {"forced-colors": "active", "prefers-color-scheme": palette}
        capture.read(reads.FILE, document())
        capture.tallied(reads.FILE, CLIP, 2.0, ASKED, COUNTED, {**INKED, **_colours(palette)})
    assert [reading.palette for reading in capture.of(reads.FILE)] == [
        "forced light",
        "forced dark",
    ]


def fake_browser() -> ModuleType:
    """A module of the browser module's shape, whose reads give `document`, its tally and the
    probe's own reading of it, whose pre-filter passes over every span, and whose read of ink
    finds none."""
    module = ModuleType("fake_browser")

    class Started:
        def __init__(self, own: str) -> None:
            self._own = own
            self.scale = 2.0
            self.emulated: dict[str, str] = {}

        def ask(self, function: str, *arguments: Any) -> Any:
            return {"read": document(), "tally": COUNTED, reads.INKED: INKED}[function]

        def emulate(self, signals: Mapping[str, str]) -> None:
            self.emulated = dict(signals)

    vars(module).update(
        READ="read",
        TALLY="tally",
        _Started=Started,
        _passed_over=lambda *_: True,
        _left_ink=lambda *_: False,
    )
    return module


def test_while_captured_each_read_and_tally_of_a_file_is_kept_and_the_module_left_as_it_was() -> (
    None
):
    module = fake_browser()
    names = vars(module)
    held = (names["_Started"].ask, names["_Started"].emulate)
    passed_over, left_ink = names["_passed_over"], names["_left_ink"]
    with reads.captured(module, every=True) as capture:
        started = names["_Started"](f"file:///somewhere/{reads.FILE}")
        started.emulate({"forced-colors": "active"})
        assert started.emulated == {"forced-colors": "active"}
        started.ask("read")
        started.ask("tally", ["strong", "ground", "shown", "unshown"], CLIP, ASKED)
        assert not names["_passed_over"]({"id": "probe-0"}, {}, [])
        assert names["_passed_over"]({"id": "planted"}, {}, [])
        assert names["_left_ink"](started, {"id": "probe-0"}, {}, {}, 0)
        assert not names["_left_ink"](started, {"id": "planted"}, {}, {}, 0)
    assert (names["_Started"].ask, names["_Started"].emulate) == held
    assert (names["_passed_over"], names["_left_ink"]) == (passed_over, left_ink)
    [reading] = capture.of(reads.FILE)
    assert reading.palette == "forced light"
    assert reading.spot("probe-0/0-0", 0, 1) is not None
    with reads.captured(module, every=False):
        assert names["_passed_over"]({"id": "probe-0"}, {}, [])


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
    assert reads.palettes_of([*every, hidden(stop, 10.0, palette="dark")]) == ["light", "dark"]


def grazed(step: int, lost: int, **found: Any) -> reads.Grazed:
    return reads.Grazed(12.0, 1.0, step, "light", strong=200, lost=lost, **found)


def test_the_graze_summary_lists_each_step_whose_island_the_read_leaves_unnamed() -> None:
    every = [
        grazed(0, 0),
        grazed(8, 0, counted=9),
        grazed(9, 1, counted=11, island=True, level=127),
        grazed(16, 23, counted=30, named=True, island=True, level=127),
        grazed(17, 23, counted=30, named=True),
    ]
    lines = reads.graze_summary(every)
    assert lines[0] == (
        "5 steps at 1 draws (ems 12.0 to 12.0): hiding nothing wholly at 1, counted ink alone"
        " at 1, strong ink at 3"
    )
    assert lines[1] == "  named by the read at 2 (ems 12.0 to 12.0)"
    assert lines[2] == (
        "  the measure takes an island at 2 (ems 12.0 to 12.0); the read leaves unnamed 1 of"
        " those (ems 12.0 to 12.0)"
    )
    assert lines[3] == (
        "    em 12.000, scale 1, step 9: hid 1 of 200 strong against a sliver of 1.44 px,"
        " 11 counted wholly, an island at 127"
    )
    assert lines[4] == "    by scale: 1 1"
    assert lines[5] == (
        "  the least graze, at 1 of 1 draws: named by the read at 0, an island taken at 1, by"
        " the measure alone at 1"
    )
    assert reads.graze_line(12.0, 1.0, every).endswith("steps 0..17: 0 0 1! 23* 23*")


def test_island_level_asks_the_measure_at_each_level_alone_and_leaves_its_levels_as_they_were() -> (
    None
):
    """A strong pixel whose neighbours are faint is an island at 127 of its own, and at 159
    meets them, so a cause that hides it alone takes an island first at 127."""
    ink = {(0, 0): 100, (0, 1): 150, (1, 0): 150}
    shows = {(0, 1): 255, (1, 0): 255}
    levels = islands.LEVELS
    assert reads.island_level(islands, ink, [(0, 0)], shows) == 127
    assert reads.island_level(islands, ink, [(0, 0)], {**shows, (0, 0): 0}) == 127
    assert reads.island_level(islands, {(0, 0): 100, (0, 1): 100}, [(0, 0)], shows) == 0
    assert levels == islands.LEVELS


def test_the_deck_names_a_cause_by_the_sliver_or_by_an_island_the_cause_takes() -> None:
    """At an em of 5.5 px, two device pixels to a px, the sliver is an area of 1.21 device
    pixels. One strong pixel past the page, an island of its own, is cut by the measure alone;
    two hidden on the page reach the sliver, and a stroke's pixel hidden with the rest of it
    showing takes no island."""
    pixels = {(1, 5): (255, 0), (5, 5): (255, 0), (8, 8): (255, 0), (8, 9): (255, 255)}
    counted = {"strong": 4, "past": 1, "hidden": 2}
    found = spot(pixels, counted, em=5.5)
    entries = reads.entries_of(viewing_tool, viewing_browser, found, "a.")
    assert [(entry.why, entry.sliver, entry.island) for entry in entries] == [
        ("cut", False, True),
        ("covered", True, True),
    ]
    assert entries[1].share == 0.5
    stroke = spot({(5, 5): (255, 0), (5, 6): (255, 255)}, {"strong": 2, "past": 0, "hidden": 1})
    assert reads.entries_of(viewing_tool, viewing_browser, stroke, "l") == []


def test_a_span_with_no_strong_ink_takes_the_share_of_its_counted_ink_the_cause_loses() -> None:
    """A faint dot of 155 hidden whole, a lighter pixel of 225 hidden beside it, which is no
    counted ink, and a faint pixel apart that shows: the cover takes the dot's island, and its
    share is one of the span's two counted pixels."""
    pixels = {(2, 2): (100, 0), (2, 3): (30, 0), (8, 8): (100, 100)}
    faint = spot(pixels, {"strong": 0, "past": 0, "hidden": 0})
    [entry] = reads.entries_of(viewing_tool, viewing_browser, faint, "ż")
    assert (entry.why, entry.sliver, entry.island) == ("covered", False, True)
    assert entry.share == 0.5


def test_the_planted_file_in_a_dark_key_names_the_dark_scheme_alone() -> None:
    written = reads.planted_dark(viewing_browser, 1.0)
    assert "<style>:root{color-scheme:dark}" in written
    assert written.replace(":root{color-scheme:dark}", "", 1) == viewing_browser._planted_html(
        viewing_browser.PLANTED_FACE.read_bytes(), device=1.0
    )


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
    [reading] = second.capture.of(reads.FILE)
    named = second.named[reading.palette]
    read = [
        reads.hidden_of(found, plant, 1.0, reading, named)
        for page in pages
        for plant in page.plants
    ]
    assert len(read) == len(found.reads.DOTS)
    for each in read:
        assert each.ink and each.whole and each.agrees and not each.neighbours
        assert each.em == pytest.approx(20.0)
        assert each.named == (each.found > 0 and each.lost >= each.sliver)


# The read as built, through a real browser (DEC-054's Implications).

#: The ems the dots are drawn at, a tenth of a device pixel apart, at a scale of 1: where
#: DEC-054's probe found the sliver leaving each of the three dots hidden whole, in the look's
#: face, and some dots of ż holding no strong ink.
LOW_EMS = tuple(10 + tenth / 10 for tenth in range(26))

#: The dots DEC-054's Implications have a browser's read name as covered with `island`: a full
#: stop and a decimal point, each a run of its own, and the dot of ż.
NAMED_DOTS = tuple(
    dot for dot in svg_reads.DOTS if dot.name in ("full stop", "decimal point", "dot of ż")
)

#: How far above its baseline the page's foot lies where the full stop is cut, in ems of its
#: text: below the foot of its letters' line box and above the top of a full stop.
CUT_ABOVE_THE_BASELINE = 0.4


@contextlib.contextmanager
def a_real_browser() -> Iterator[tuple[reads.Modules, Any]]:
    """The probe's modules and the browser found; a test skips where a sandbox stops it."""
    found = reads.modules()
    browser = found.look.viewing_browser
    try:
        yield found, browser.find()
    except browser.Stopped as stop:
        if stop.sandbox:
            pytest.skip(f"a sandbox stopped the browser: {stop}")
        raise


@dataclass(frozen=True)
class UnderBoxes:
    """The three dots at `LOW_EMS`, each under a box over all of it: each plant the box hid
    whole, as the probe reads it, with the read's entry of its span as covered, if any."""

    hidden: tuple[tuple[Any, Any, Any], ...]


@pytest.fixture(scope="module")
def under_boxes() -> UnderBoxes:
    """Drawn once for the tests that read it, each marked `real_browser`, so none draws it on
    a machine with no browser."""
    with a_real_browser() as (found, program):
        pages = reads.laid(NAMED_DOTS, LOW_EMS, 1.0)
        first = reads.drawn(found, found.look.FONT, pages, 1.0, program, {}, every=True)
        boxes = reads.boxes_over(found, pages, first)
        second = reads.drawn(found, found.look.FONT, pages, 1.0, program, boxes, every=False)
    [reading] = second.capture.of(reads.FILE)
    covered = found.look.viewing_browser.COVERED
    entries = {
        (each.element, each.text, each.why): each for each in second.dropped[reading.palette]
    }
    held = []
    for page in pages:
        for plant in page.plants:
            hidden = reads.hidden_of(found, plant, 1.0, reading, ())
            if hidden.ink and hidden.whole:
                entry = entries.get((plant.text, plant.dot.runs[plant.dot.at], covered))
                held.append((plant, hidden, entry))
    return UnderBoxes(tuple(held))


@real_browser
def test_a_real_browser_names_each_dot_hidden_whole_as_covered_with_island(
    under_boxes: UnderBoxes,
) -> None:
    """A full stop and a decimal point, each a run of its own, and the dot of ż, each hidden
    whole by a later box at each em from 10 to 12.5: the read names each as covered with
    `island`, and each of the three at one em at least where its loss lies under the sliver,
    so the measure alone names it (DEC-054 points 1 and 3). At which ems the sliver leaves each,
    this test leaves to the machine."""
    left: Counter[str] = Counter()
    for plant, _, entry in under_boxes.hidden:
        assert entry is not None and entry.island, (plant.dot.name, plant.em)
        left[plant.dot.name] += not entry.by_size
    assert set(left) == {dot.name for dot in NAMED_DOTS}
    assert all(left.values()), left


@real_browser
def test_a_real_browser_names_a_faint_dot_of_z_hidden_whole(under_boxes: UnderBoxes) -> None:
    """A dot of ż that holds no strong ink, hidden whole: the read names it as covered with
    `island`, though it loses no strong ink (DEC-054 point 1). Whether the face draws such a
    dot at these ems is the machine's: the test skips where it draws none."""
    faint = [
        (plant, entry)
        for plant, hidden, entry in under_boxes.hidden
        if plant.dot.name == "dot of ż" and not hidden.strong
    ]
    if not faint:
        pytest.skip("the browser drew every dot of ż from an em of 10 to 12.5 with strong ink")
    for plant, entry in faint:
        assert entry is not None and entry.island, plant.em


@real_browser
def test_a_real_browser_names_a_full_stop_past_the_pages_edge_as_cut_with_island() -> None:
    """A full stop, a run of its own, its page's foot laid between its letters' line box's foot
    and its own top, so its span lies partly on the page and its ink wholly past it: the read
    names it as cut with `island`, since the cut takes all of an island (DEC-054 point 1). The
    page is as wide as the planted file's, so the window draws the first read's plants at the
    start's own scale."""
    full_stop = next(dot for dot in NAMED_DOTS if dot.name == "full stop")
    with a_real_browser() as (found, program):
        [page] = reads.laid((full_stop,), (12.0,), 1.0)
        [plant] = page.plants
        foot = reads.TEXT_TOP + reads.BASELINE - CUT_ABOVE_THE_BASELINE
        width = max(page.width, found.look.viewing_browser.PLANTED_WIDTH)
        cut = replace(page, width=width, height=plant.top + foot * plant.size)
        drawn = reads.drawn(found, found.look.FONT, [cut], 1.0, program, {}, every=True)
    [entries] = drawn.dropped.values()
    [entry] = [each for each in entries if each.text == "."]
    assert entry.why == found.look.viewing_browser.CUT
    assert entry.island


@real_browser
def test_a_real_browser_leaves_unnamed_a_graze_under_the_sliver_that_takes_no_island() -> None:
    """A box's top edge stepped across the foot of a p at an em of 20, an eighth of a device
    pixel a step: at each step that hides strong ink wholly, under the sliver, and takes no
    island by the measure on the tally's own pixels, the read names nothing; and one step at
    least is such a graze (DEC-054 point 1)."""
    stem = reads.Words("stem", ("p",))
    with a_real_browser() as (found, program):
        pages = reads.laid((stem,), (20.0,), 1.0, reads.GRAZE_STEPS)
        first = reads.drawn(found, found.look.FONT, pages, 1.0, program, {}, every=True)
        boxes = reads.graze_boxes(pages, first, islands.FAINT)
        second = reads.drawn(found, found.look.FONT, pages, 1.0, program, boxes, every=False)
    [reading] = second.capture.of(reads.FILE)
    named = {each.element for each in second.dropped[reading.palette]}
    grazes: Sequence[Any] = [
        plant
        for page in pages
        for plant in page.plants
        for grazed in [reads.grazed_of(found, plant, 1.0, reading, ())]
        if grazed.lost and grazed.lost < grazed.sliver and not grazed.island
    ]
    assert grazes
    assert not {plant.text for plant in grazes} & named
