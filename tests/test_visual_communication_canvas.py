"""The canvas (`_lib/canvas.py`): a second renderer subclasses it and replaces only what
differs from SVG, how a paint is written, the arrow markers, the font faces and a span's
placing, and every length still comes from the canvas.
"""

from __future__ import annotations

import base64
import io
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


def test_the_canvas_is_read_as_no_renderer() -> None:
    assert not canvas.__name__.startswith("_lib.plugins")
    assert "canvas" not in seam.names()
    assert {seam.declaration(name)["module"] for name in seam.names(seam.RENDERER)} == {
        "svg",
        "pdf",
    }
    with pytest.raises(seam.PluginError):
        seam.implementation("canvas")
