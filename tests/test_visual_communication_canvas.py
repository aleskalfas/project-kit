"""The canvas (`_lib/canvas.py`): a second renderer subclasses it and replaces only what
differs from SVG, how a paint is written, the arrow markers, the font faces and a span's
placing, and every length still comes from the canvas. Every renderer draws a line along
the course the canvas gives it: its turns round at its radius, each fitted to its legs, and
each end that carries an arrowhead stopped at the head's base.
"""

from __future__ import annotations

import base64
import io
import math
import re
from collections.abc import Mapping
from typing import Any
from xml.etree import ElementTree

import pytest
from fontTools.ttLib import TTFont

from tests.in_process import load
from tests.test_visual_communication_svg import (
    COLOURS,
    FONT,
    ROUNDED,
    SAID,
    SEMIBOLD,
    SHAPES,
    SVG,
    TIES,
    TITLE,
    element,
    named,
    scene,
)

canvas, svg, svg_declaration, seam = load(
    "visual-communication", "canvas", "plugins.svg", "plugins.svg_declaration", "plugins.seam"
)

checks, pdf_declaration, html_declaration = load(
    "visual-communication", "checks", "plugins.pdf_declaration", "plugins.html_declaration"
)

DECLARATION = {**svg_declaration.DECLARATION, "name": "elsewhere", "version": "0.1.0"}

FILES = {"Source Sans Pro": FONT, "Source Sans Pro Semibold": SEMIBOLD}


class Elsewhere(canvas.Canvas):
    """A renderer that names each paint's role for a sheet to colour, keys an arrowhead on
    that role, keeps each face once for its file, and places every span of a line."""

    def __init__(self, *args: Any) -> None:
        super().__init__(*args)
        self.file_faces: dict[tuple[str, int], set[str]] = {}

    def _paint_attributes(self, prop: str, role: str | None) -> list[tuple[str, Any]]:
        if role is None:
            return super()._paint_attributes(prop, role)
        return [(f"data-{prop}", role)]

    def _markers(
        self, element: Mapping[str, Any], stroke: list[tuple[str, Any]]
    ) -> list[tuple[str, Any]]:
        found = []
        for which in canvas.ENDS:
            if element.get(f"marker-{which}") == "arrow":
                marker = f"arrow-{which}-{element['stroke']}"
                self._arrows[marker] = (which, "context-stroke", None)
                found.append((f"marker-{which}", f"url(#{marker})"))
        return found

    def _font_faces(self) -> str:
        for face, characters in self._faces.items():
            self.file_faces.setdefault(face, set()).update(characters)
        return ""

    def _span_place(self, line: Mapping[str, Any], pen: float) -> list[tuple[str, Any]]:
        return [("x", canvas.number(pen))] if len(line["spans"]) > 1 else []

    def sheet(self) -> str:
        """The file's `@font-face` rules, each face once."""
        self._faces = self.file_faces
        return super()._font_faces()


def elsewhere(drawn: Mapping[str, Any], declaration: Mapping[str, Any] = DECLARATION) -> Any:
    return Elsewhere(declaration, drawn, "default", COLOURS, FILES.__getitem__, {})


def page_of(drawn: Mapping[str, Any]) -> Mapping[str, Any]:
    return drawn["children"][0]


def drawn_by_svg(drawn: Mapping[str, Any]) -> str:
    [page] = svg.render(
        drawn, key="default", colours=COLOURS, font_file=FILES.__getitem__, pictures={}
    ).pages
    return page.svg


def what_no_replacement_reaches(page: str) -> str:
    """A page without what `Elsewhere` writes otherwise. What is left is the projection."""
    for replaced in (
        r' (data-)?(fill|stroke)(-opacity)?="[^"]*"',
        r' marker-(start|end)="[^"]*"',
        r"<marker .*?</marker>",
        r"@font-face\{[^}]*\}",
        r' data-renderer="[^"]*"',
    ):
        page = re.sub(replaced, "", page)
    return page


@pytest.mark.parametrize("drawn", [SHAPES, TIES, scene(TITLE)], ids=["shapes", "ties", "text"])
def test_a_subclass_replaces_the_writing_and_keeps_every_length_of_the_canvas(
    drawn: dict[str, Any],
) -> None:
    written = elsewhere(drawn).page(page_of(drawn))

    assert what_no_replacement_reaches(written) == what_no_replacement_reaches(drawn_by_svg(drawn))
    assert 'data-renderer="elsewhere 0.1.0"' in written
    assert not re.search(r' (fill|stroke)="#', written)


def test_a_subclass_writes_a_paint_as_it_chooses_on_every_primitive() -> None:
    written = elsewhere(SHAPES).page(page_of(SHAPES))
    assert (
        '<rect data-id="figure/back" x="1" y="1" width="198" height="98" rx="4" '
        'data-fill="surface" data-stroke="border" stroke-width="2"/>'
    ) in written
    assert 'cx="25" cy="15" rx="25" ry="15" data-fill="accent"/>' in written


def test_a_subclass_writes_its_arrow_markers_on_its_own_key() -> None:
    written = elsewhere(TIES).page(page_of(TIES))
    assert 'marker-end="url(#arrow-end-ink)"/>' in written
    assert 'marker-start="url(#arrow-start-shade)" marker-end="url(#arrow-end-shade)"/>' in written
    assert re.findall(r'<marker id="([^"]+)"', written) == [
        "arrow-end-ink",
        "arrow-end-shade",
        "arrow-start-shade",
    ]
    assert '<path d="M0,0L10,5L0,10z" fill="context-stroke"/>' in written


def test_a_subclass_keeps_each_face_once_for_its_file() -> None:
    first, second = scene(SAID), scene(named(["Source Sans Pro"]))
    file = elsewhere(first)
    pages = [file.page(page_of(first)), file.page(page_of(second))]

    assert not any("@font-face" in page for page in pages)
    sheet = file.sheet()
    assert re.findall(r'font-family:("[^"]*");font-weight:(\d+)', sheet) == [
        ('"Source Sans Pro"', "400"),
        ('"Source Sans Pro Semibold"', "600"),
    ]
    held = []
    for data in re.findall(r"base64,([A-Za-z0-9+/=]+)\)", sheet):
        cmap = TTFont(io.BytesIO(base64.b64decode(data))).getBestCmap()
        assert cmap is not None
        held.append({chr(code) for code in cmap})
    assert held == [set("Say nowAa"), set("<it> ")]


@pytest.mark.parametrize(
    ("anchor", "line_at", "spans_at"),
    [
        ("start", "0", ["0", "30", "70"]),
        ("middle", "100", ["50", "80", "120"]),
        ("end", "200", ["100", "130", "170"]),
    ],
)
def test_a_subclass_places_each_span_where_the_engines_widths_put_it(
    anchor: str, line_at: str, spans_at: list[str]
) -> None:
    drawn = scene({**SAID, "text-anchor": anchor})

    root = ElementTree.fromstring(elsewhere(drawn).page(page_of(drawn)))

    [line] = next(root.iter(f"{SVG}text"))
    assert line.get("x") == line_at
    assert [span.get("x") for span in line] == spans_at


def test_a_line_of_one_span_takes_no_place_of_its_own() -> None:
    written = elsewhere(scene(TITLE)).page(page_of(scene(TITLE)))
    assert '<tspan x="60" y="20.2">Plan &amp; &lt;do&gt;</tspan>' in written


def test_a_subclass_reports_its_losses_under_its_own_name_and_draws_what_it_declares() -> None:
    drawn = scene(
        element("box", "figure/odd", x=0, y=0, width=10, height=10, fill="no-such-role"),
        element("ellipse", "figure/dot", x=0, y=0, width=10, height=10, fill="accent"),
    )
    draws = {k: v for k, v in DECLARATION["draws"].items() if k != "ellipse"}
    file = elsewhere(drawn, {**DECLARATION, "draws": draws})

    written = file.page(page_of(drawn))

    assert [loss.as_dict() for loss in file.losses] == [
        {
            "plugin": "elsewhere",
            "what": "figure/odd",
            "did": "left-out",
            "why": "the brand gives the role `no-such-role` of its fill no colour in `default`",
        },
        {
            "plugin": "elsewhere",
            "what": "figure/dot",
            "did": "refused",
            "why": "the elsewhere renderer draws no `ellipse`",
        },
    ]
    assert '<rect data-id="figure/odd" x="0" y="0" width="10" height="10" fill="none"/>' in written
    assert "figure/dot" not in written


def test_a_number_takes_the_places_a_renderer_asks_of_it() -> None:
    assert canvas.number(1.23456789, 5) == "1.23457"
    assert canvas.number(1.5, 5) == "1.5"
    assert canvas.number(-0.000001, 5) == "0"
    assert canvas.number(1.23456789) == "1.23"


def test_it_finds_an_element_anywhere_in_the_tree_by_its_trace_id() -> None:
    children = SHAPES["children"]
    found = canvas.find(children, "figure/mark/dot")
    assert found is not None
    assert found["type"] == "ellipse"
    assert canvas.find(children, "figure/gone") is None


def test_the_canvas_is_read_as_no_renderer() -> None:
    assert not canvas.__name__.startswith("_lib.plugins")
    assert "canvas" not in seam.names()
    assert {seam.declaration(name)["module"] for name in seam.names(seam.RENDERER)} == {
        "svg",
        "pdf",
        "html",
    }
    with pytest.raises(seam.PluginError):
        seam.implementation("canvas")


# --- a line's course: its turns drawn round, its ends at its arrowheads' bases (#3082) --------

#: A route whose legs run 40, 60 and 60 px, turning right and then left on the page.
ROUTE = [(0.0, 0.0), (40.0, 0.0), (40.0, 60.0), (100.0, 60.0)]


def through_middle(arc: Any, centre: tuple[float, float]) -> float:
    """How far from `centre` the cubic Bézier curve that draws `arc` lies halfway along it."""
    (x0, y0), (x1, y1), (x2, y2), (x3, y3) = arc.start, *arc.controls, arc.end
    middle = ((x0 + 3 * x1 + 3 * x2 + x3) / 8, (y0 + 3 * y1 + 3 * y2 + y3) / 8)
    return math.dist(middle, centre)


@pytest.mark.parametrize("radius", [0.0, -4.0])
def test_a_course_of_no_radius_turns_on_sharp_corners(radius: float) -> None:
    assert canvas.course(ROUTE, radius, {}) == canvas.Course(tuple(ROUTE), {}, {})


@pytest.mark.parametrize("radius", [4.0, 16.0, 20.0])
def test_each_turn_is_an_arc_of_the_radius_that_leaves_each_leg_as_far_from_its_corner(
    radius: float,
) -> None:
    drawn = canvas.course(ROUTE, radius, {})

    assert drawn.points == tuple(ROUTE)
    right, left = drawn.arcs[1], drawn.arcs[2]
    # Down the page, a right turn is clockwise and a left one is not.
    assert (right.clockwise, left.clockwise) == (True, False)
    assert right.radius == pytest.approx(radius)
    assert right.start == pytest.approx((40 - radius, 0))
    assert right.end == pytest.approx((40, radius))
    assert through_middle(right, (40 - radius, radius)) == pytest.approx(radius)
    assert left.radius == pytest.approx(radius)
    assert left.start == pytest.approx((40, 60 - radius))
    assert left.end == pytest.approx((40 + radius, 60))
    assert through_middle(left, (40 + radius, 60 - radius)) == pytest.approx(radius)


def test_a_turn_too_large_for_its_legs_is_reduced_to_half_the_shorter_leg() -> None:
    """Of the 40 px a turn asks, the first takes 20, half its first leg, and the second 30,
    half of either of its legs: neither is refused."""
    drawn = canvas.course(ROUTE, 40.0, {})

    assert drawn.arcs[1].radius == pytest.approx(20)
    assert drawn.arcs[2].radius == pytest.approx(30)
    assert drawn.arcs[1].end == pytest.approx((40, 20))
    assert drawn.arcs[2].start == pytest.approx((40, 30))


def test_two_turns_on_one_short_leg_meet_at_its_middle_and_never_cross() -> None:
    drawn = canvas.course([(0.0, 0.0), (40.0, 0.0), (40.0, 10.0), (80.0, 10.0)], 16.0, {})

    assert drawn.arcs[1].end == pytest.approx(drawn.arcs[2].start)
    assert drawn.arcs[1].end == pytest.approx((40, 5))
    # Where the two arcs meet, the path draws no line between them.
    assert canvas.course_path(drawn) == "M 0 0 L 35 0 A 5 5 0 0 1 40 5 A 5 5 0 0 0 45 10 L 80 10"


def test_a_turn_that_goes_straight_on_or_back_on_itself_is_drawn_sharp() -> None:
    assert canvas.course([(0.0, 0.0), (10.0, 0.0), (20.0, 0.0)], 8.0, {}).arcs == {}
    assert canvas.course([(0.0, 0.0), (10.0, 0.0), (0.0, 0.0)], 8.0, {}).arcs == {}
    # A point that repeats the one before it is no turn.
    repeated = canvas.course([(0.0, 0.0), (10.0, 0.0), (10.0, 0.0), (10.0, 10.0)], 4.0, {})
    assert repeated.points == ((0, 0), (10, 0), (10, 10))
    assert list(repeated.arcs) == [1]


def test_a_course_of_round_turns_is_written_as_svg_path_data() -> None:
    assert canvas.course_path(canvas.course(ROUTE, 16.0, {})) == (
        "M 0 0 L 24 0 A 16 16 0 0 1 40 16 L 40 44 A 16 16 0 0 0 56 60 L 100 60"
    )


@pytest.mark.parametrize(
    ("ends", "first", "last"),
    [
        ({"start": 5.0}, (5, 0), (100, 60)),
        ({"end": 5.0}, (0, 0), (95, 60)),
        ({"start": 5.0, "end": 5.0}, (5, 0), (95, 60)),
    ],
    ids=["start", "end", "both"],
)
def test_a_line_stops_at_the_base_of_the_arrowhead_at_either_end(
    ends: dict[str, float], first: tuple[float, float], last: tuple[float, float]
) -> None:
    drawn = canvas.course(ROUTE, 0.0, ends)

    assert drawn.points == (first, (40, 0), (40, 60), last)
    away = {"start": canvas.Head(first, (-1, 0)), "end": canvas.Head(last, (1, 0))}
    assert drawn.heads == {which: away[which] for which in ends}


def test_an_arrowhead_is_five_widths_of_its_lines_stroke_long_and_only_an_arrow_is_one() -> None:
    assert canvas.heads({"marker-end": "arrow"}) == {"end": 5}
    assert canvas.heads({"stroke-width": 2, "marker-start": "arrow", "marker-end": "arrow"}) == {
        "start": 10,
        "end": 10,
    }
    assert canvas.heads({"marker-end": "none"}) == {}


def test_a_turn_fits_the_leg_an_arrowhead_leaves_it() -> None:
    """The last leg runs 60 px, and its head, 20 px long, leaves 40 of it: the second turn
    takes at most 20."""
    drawn = canvas.course(ROUTE, 30.0, {"end": 20.0})

    assert drawn.points[-1] == (80, 60)
    assert drawn.arcs[1].radius == pytest.approx(20)
    assert drawn.arcs[2].radius == pytest.approx(20)


def test_an_arrowhead_longer_than_its_leg_keeps_the_least_of_it_to_point_along() -> None:
    lone = canvas.course([(0.0, 0.0), (3.0, 0.0)], 0.0, {"end": 5.0})
    assert lone.points[0] == (0, 0)
    assert lone.points[1] == pytest.approx((canvas.LEAST, 0))
    assert lone.heads["end"].towards == (1, 0)
    # Two heads on a line of one leg share it, each keeping the least of its half.
    shared = canvas.course([(0.0, 0.0), (6.0, 0.0)], 0.0, {"start": 5.0, "end": 5.0})
    assert shared.points[0] == pytest.approx((3 - canvas.LEAST, 0))
    assert shared.points[1] == pytest.approx((3 + canvas.LEAST, 0))


def test_a_line_of_no_length_draws_as_it_stands_its_heads_pointing_across() -> None:
    drawn = canvas.course([(5.0, 5.0), (5.0, 5.0)], 8.0, {"start": 5.0, "end": 5.0})

    assert drawn == canvas.Course(
        ((5, 5), (5, 5)),
        {},
        {"start": canvas.Head((5, 5), (-1, 0)), "end": canvas.Head((5, 5), (1, 0))},
    )


def test_each_renderer_declares_the_radius_of_a_turn_and_one_that_does_not_loses_it() -> None:
    """A renderer that does not declare `rx` would draw sharp corners, so the capability
    reports it before the renderer runs, and the seam need not rise (DEC-005 point 9)."""
    for declared in (svg_declaration, pdf_declaration, html_declaration):
        assert "rx" in declared.DECLARATION["draws"]["line"]
        assert checks.losses(ROUNDED, declared.DECLARATION) == []
    line = {k: v for k, v in DECLARATION["draws"]["line"].items() if k != "rx"}
    sharp = {**DECLARATION, "draws": {**DECLARATION["draws"], "line": line}}
    assert [loss.as_dict() for loss in checks.losses(ROUNDED, sharp)] == [
        {
            "plugin": "elsewhere",
            "what": f"figure/links[{tie}]/l",
            "did": "left-out",
            "why": "the elsewhere renderer draws no `rx` of a line",
        }
        for tie in ("ab", "cd")
    ]
