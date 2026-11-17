"""The SVG renderer (visual-communication DEC-005 points 4, 5, 9 and 10): what it declares,
what it draws, and what it reports it lost.

The reference outputs below are pinned to the renderer's version, 1.5.0. A change that
gives another output for the same scene and values raises the version, and changes them
with it (DEC-005 point 9). Version 1.5.0 came, at seam 9, to give the arrowhead of a step of
an order an id of its own in a switching file (DEC-032 point 5): a scene of no step draws as
1.4.0 drew it, but for the renderer's version it names. Version 1.4.0 came to stop a line at
its arrowhead's base, and to draw a connector's turns round at the radius it holds, `rx`, as
a path: a line with no arrowhead and no radius draws as 1.3.0 drew it, but for the
renderer's version it names.
Version 1.3.0 came to draw a run's sign and ground, at seam 8
(DEC-036 point 3): a scene of neither draws as 1.2.0 drew it, but for the renderer's version
it names. Version 1.2.0 came to draw the path, a concept's sign, at seam 7
(DEC-036 point 1): a scene of no path draws as 1.1.0 drew it, but for the renderer's version
it names. Version 1.1.0 came with seam 5, which hands the renderer the
picture each image shows, a PNG or a JPEG, whatever its source (DEC-025 point 7): a scene
of no picture draws as 1.0.1 drew it, but for the renderer's version it names. The font a
text embeds is pinned by the characters its subset holds, not by its bytes, which are
fontTools'. A text of one run is drawn as it was
before runs (DEC-012 point 7), so runs left the version as it was; a text of several runs
draws each run that looks otherwise than its first in a span of its own. A line with no
arrowhead and no corners is drawn as it was before ties (DEC-011), so ties left it too;
a tie's connector with corners is a polyline, and an arrowhead a marker in its colour.
"""

from __future__ import annotations

import base64
import io
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

import pytest
from fontTools.ttLib import TTFont

from tests.in_process import load
from tests.visual_communication_producer import png
from tests.visual_communication_project import TEST_BRAND, TEST_PICTURES

svg, svg_declaration, seam, env, text, canvas = load(
    "visual-communication",
    "plugins.svg",
    "plugins.svg_declaration",
    "plugins.seam",
    "env",
    "text",
    "canvas",
)

FONT = TEST_BRAND / "fonts" / "SourceSansPro-Regular.otf"
SEMIBOLD = TEST_BRAND / "fonts" / "SourceSansPro-Semibold.otf"

COLOURS = {
    "surface": {"components": [1, 1, 1], "alpha": 1},
    "border": {"components": [0.5, 0.5, 0.5], "alpha": 1},
    "accent": {"components": [0.25, 0.5, 0.75], "alpha": 1},
    "shade": {"components": [0, 0, 0], "alpha": 0.25},
    "ink": {"components": [0, 0, 0], "alpha": 1},
}


def element(kind: str, trace: str, **properties: Any) -> dict[str, Any]:
    return {"type": kind, "id": trace, **properties, "sources": {}}


def scene(*children: dict[str, Any], width: float = 200, height: float = 100) -> dict[str, Any]:
    """A scene of one page, `figure`, holding `children`."""
    page = element(
        "group",
        "figure",
        x=0,
        y=0,
        width=width,
        height=height,
        component="foundations/figure",
        version="1.0.0",
        page=True,
        children=list(children),
    )
    return {
        "piece": "flow",
        "lock": {"foundations": "1.0.0"},
        "language": "en",
        "size-key": "default",
        "seam": 9,
        "pages": ["figure"],
        "children": [page],
    }


def draw(drawn: dict[str, Any], *, key: str = "default", pictures: Any = None) -> Any:
    return svg.render(
        drawn, key=key, colours=COLOURS, font_file=lambda _family: FONT, pictures=pictures or {}
    )


HEAD = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="200" height="100" viewBox="0 0 200 100" '
    'data-piece="flow" data-page="figure" data-language="en" data-key="default" '
    'data-renderer="svg 1.5.0">'
)

SHAPES = scene(
    element(
        "box",
        "figure/back",
        x=0,
        y=0,
        width=200,
        height=100,
        fill="surface",
        stroke="border",
        **{"stroke-width": 2},
        rx=4,
    ),
    element(
        "group",
        "figure/mark",
        x=10.5,
        y=20,
        width=50,
        height=50,
        component="tests/card",
        version="1.0.0",
        children=[
            element("ellipse", "figure/mark/dot", x=0, y=0, width=50, height=30, fill="accent"),
            element(
                "line",
                "figure/mark/rule",
                x=0,
                y=40,
                width=50,
                height=0,
                x1=0,
                y1=40,
                x2=50,
                y2=40,
                stroke="shade",
                **{"stroke-width": 1.5},
            ),
        ],
    ),
)


def test_shapes_are_drawn_as_pinned_for_version_1_1_0() -> None:
    drawn = draw(SHAPES)
    assert drawn.losses == []
    [page] = drawn.pages
    assert page.id == "figure"
    assert page.svg == (
        HEAD + "<defs><style>text{white-space:pre}</style></defs>"
        '<g data-id="figure" data-component="foundations/figure" data-version="1.0.0">'
        '<rect data-id="figure/back" x="1" y="1" width="198" height="98" rx="4" '
        'fill="#ffffff" stroke="#808080" stroke-width="2"/>'
        '<g data-id="figure/mark" data-component="tests/card" data-version="1.0.0" '
        'transform="translate(10.5,20)">'
        '<ellipse data-id="figure/mark/dot" cx="25" cy="15" rx="25" ry="15" fill="#4080bf"/>'
        '<line data-id="figure/mark/rule" x1="0" y1="40" x2="50" y2="40" stroke="#000000" '
        'stroke-opacity="0.25" stroke-width="1.5"/>'
        "</g></g></svg>\n"
    )


#: A tie's connector with corners and an arrowhead at its end, and a straight line with an
#: arrowhead at both ends, in another colour.
TIES = scene(
    element(
        "line",
        "figure/links[ab]/l",
        x=10,
        y=20,
        width=100,
        height=40,
        x1=10,
        y1=20,
        x2=110,
        y2=60,
        points=[{"x": 10, "y": 20}, {"x": 60, "y": 20}, {"x": 60, "y": 60}, {"x": 110, "y": 60}],
        attached={
            "start": {"id": "figure/steps[a]", "side": "right"},
            "end": {"id": "figure/steps[b]", "side": "left"},
        },
        stroke="ink",
        **{"stroke-width": 2, "marker-end": "arrow"},
    ),
    element(
        "line",
        "figure/rule",
        x=0,
        y=90,
        width=200,
        height=0,
        x1=0,
        y1=90,
        x2=200,
        y2=90,
        stroke="shade",
        **{"marker-start": "arrow", "marker-end": "arrow"},
    ),
)


def test_a_connector_and_its_arrowheads_are_drawn_as_pinned_for_version_1_4_0() -> None:
    drawn = draw(TIES)
    assert drawn.losses == []
    [page] = drawn.pages
    # Each arrowhead is placed by its base, where its line stops: the connector, of a
    # stroke 2 px wide, ten px before its end, and the rule, of none, five px before each.
    assert page.svg == (
        HEAD + "<defs><style>text{white-space:pre}</style>"
        '<marker id="pkit-arrow-end-000000" viewBox="0 0 10 10" refX="0" refY="5" '
        'markerWidth="5" markerHeight="5" orient="auto">'
        '<path d="M0,0L10,5L0,10z" fill="#000000"/></marker>'
        '<marker id="pkit-arrow-end-000000-025" viewBox="0 0 10 10" refX="0" refY="5" '
        'markerWidth="5" markerHeight="5" orient="auto">'
        '<path d="M0,0L10,5L0,10z" fill="#000000" fill-opacity="0.25"/></marker>'
        '<marker id="pkit-arrow-start-000000-025" viewBox="0 0 10 10" refX="10" refY="5" '
        'markerWidth="5" markerHeight="5" orient="auto">'
        '<path d="M10,0L0,5L10,10z" fill="#000000" fill-opacity="0.25"/></marker>'
        "</defs>"
        '<g data-id="figure" data-component="foundations/figure" data-version="1.0.0">'
        '<polyline data-id="figure/links[ab]/l" data-start="figure/steps[a]" '
        'data-end="figure/steps[b]" points="10,20 60,20 60,60 100,60" fill="none" '
        'stroke="#000000" stroke-width="2" marker-end="url(#pkit-arrow-end-000000)"/>'
        '<line data-id="figure/rule" x1="5" y1="90" x2="195" y2="90" stroke="#000000" '
        'stroke-opacity="0.25" marker-start="url(#pkit-arrow-start-000000-025)" '
        'marker-end="url(#pkit-arrow-end-000000-025)"/>'
        "</g></svg>\n"
    )
    # The same scene gives the same file.
    assert draw(TIES).pages[0].svg == page.svg
    ElementTree.fromstring(page.svg)


#: Two connectors with corners whose turns are round: one at a radius that fits, with an
#: arrowhead at its end; one at a radius larger than half the legs of either turn, with an
#: arrowhead at each end, so each turn takes half its shorter leg, counted to a head's base.
ROUNDED = scene(
    element(
        "line",
        "figure/links[ab]/l",
        x=10,
        y=20,
        width=100,
        height=40,
        x1=10,
        y1=20,
        x2=110,
        y2=60,
        points=[{"x": 10, "y": 20}, {"x": 60, "y": 20}, {"x": 60, "y": 60}, {"x": 110, "y": 60}],
        stroke="ink",
        rx=8,
        **{"stroke-width": 2, "marker-end": "arrow"},
    ),
    element(
        "line",
        "figure/links[cd]/l",
        x=120,
        y=10,
        width=70,
        height=40,
        x1=120,
        y1=10,
        x2=190,
        y2=50,
        points=[{"x": 120, "y": 10}, {"x": 150, "y": 10}, {"x": 150, "y": 50}, {"x": 190, "y": 50}],
        stroke="ink",
        rx=40,
        **{"marker-start": "arrow", "marker-end": "arrow"},
    ),
)


def test_a_connectors_turns_are_drawn_round_as_pinned_for_version_1_4_0() -> None:
    drawn = draw(ROUNDED)
    assert drawn.losses == []
    [page] = drawn.pages
    # The first turns at 8 px both times. The second's legs run 30, 40 and 40 px, and its
    # heads, five px long, leave 25 and 35 of the first and the last: its turns take half
    # of 25 and half of 35, and leave 10 px of its middle leg straight.
    assert page.svg == (
        HEAD + "<defs><style>text{white-space:pre}</style>"
        '<marker id="pkit-arrow-end-000000" viewBox="0 0 10 10" refX="0" refY="5" '
        'markerWidth="5" markerHeight="5" orient="auto">'
        '<path d="M0,0L10,5L0,10z" fill="#000000"/></marker>'
        '<marker id="pkit-arrow-start-000000" viewBox="0 0 10 10" refX="10" refY="5" '
        'markerWidth="5" markerHeight="5" orient="auto">'
        '<path d="M10,0L0,5L10,10z" fill="#000000"/></marker>'
        "</defs>"
        '<g data-id="figure" data-component="foundations/figure" data-version="1.0.0">'
        '<path data-id="figure/links[ab]/l" '
        'd="M 10 20 L 52 20 A 8 8 0 0 1 60 28 L 60 52 A 8 8 0 0 0 68 60 L 100 60" '
        'fill="none" stroke="#000000" stroke-width="2" marker-end="url(#pkit-arrow-end-000000)"/>'
        '<path data-id="figure/links[cd]/l" '
        'd="M 125 10 L 137.5 10 A 12.5 12.5 0 0 1 150 22.5 L 150 32.5 '
        'A 17.5 17.5 0 0 0 167.5 50 L 185 50" fill="none" stroke="#000000" '
        'marker-start="url(#pkit-arrow-start-000000)" marker-end="url(#pkit-arrow-end-000000)"/>'
        "</g></svg>\n"
    )
    ElementTree.fromstring(page.svg)


@pytest.mark.parametrize("radius", [0, None])
def test_a_connector_of_radius_0_or_of_none_turns_on_sharp_corners(radius: float | None) -> None:
    connector = {**ROUNDED["children"][0]["children"][0]}
    del connector["rx"]
    if radius is not None:
        connector["rx"] = radius
    [page] = draw(scene(connector)).pages
    assert 'points="10,20 60,20 60,60 100,60"' in page.svg
    assert "<path " not in page.svg.split("</defs>")[1]


def test_a_line_with_no_stroke_draws_no_arrowhead() -> None:
    bare = scene(
        element(
            "line",
            "figure/rule",
            x=0,
            y=0,
            width=10,
            height=0,
            x1=0,
            y1=0,
            x2=10,
            y2=0,
            **{"marker-end": "arrow"},
        )
    )
    [page] = draw(bare).pages
    assert "marker" not in page.svg


def run(words: str, **look: Any) -> dict[str, Any]:
    """A run of `words` in the look `look` gives, Source Sans Pro by default."""
    families = look.pop("font-family", ["Source Sans Pro"])
    return {
        "text": words,
        "style": "type.body",
        "font-family": families,
        "font-size": 16,
        **look,
        "fonts": [{"family": family, "file": FONT.name, "sha256": "pinned"} for family in families],
        "measured": "file",
        "sources": {},
    }


def line(paragraph: int, baseline: float, *spans: tuple[int, str, float]) -> dict[str, Any]:
    """A line of `paragraph`, of `spans`, each a run's place, its text and its width."""
    return {
        "text": "".join(text for _, text, _ in spans),
        "width": sum(width for _, _, width in spans),
        "baseline": baseline,
        "paragraph": paragraph,
        "spans": [{"run": at, "text": text, "width": width} for at, text, width in spans],
    }


TITLE = element(
    "text",
    "figure/title",
    x=10,
    y=5,
    width=100,
    height=40,
    text="Plan & <do> it",
    paragraphs=[[run("Plan & <do> it", fill="ink", style="type.heading", **{"font-weight": 600})]],
    lines=[line(0, 15.2, (0, "Plan & <do>", 80)), line(0, 15.2, (0, "it", 9))],
    **{"text-anchor": "middle", "line-height": 20, "measured-height": 40},
)


def test_text_is_drawn_as_its_measured_lines_with_its_font_embedded() -> None:
    drawn = draw(scene(TITLE))
    assert drawn.losses == []
    [page] = drawn.pages
    shown = re.sub(r"base64,[A-Za-z0-9+/=]+\)", "base64,…)", page.svg)
    assert shown == (
        HEAD + "<defs><style>"
        '@font-face{font-family:"Source Sans Pro";font-weight:600;'
        "src:url(data:font/otf;base64,…) format('opentype');}"
        "text{white-space:pre}</style></defs>"
        '<g data-id="figure" data-component="foundations/figure" data-version="1.0.0">'
        '<text data-id="figure/title" xml:space="preserve" '
        'font-family="&quot;Source Sans Pro&quot;" '
        'font-size="16" font-weight="600" text-anchor="middle" fill="#000000">'
        '<tspan x="60" y="20.2">Plan &amp; &lt;do&gt;</tspan><tspan x="60" y="40.2">it</tspan>'
        "</text></g></svg>\n"
    )


def test_the_embedded_font_holds_the_characters_the_page_draws_and_no_other() -> None:
    [page] = draw(scene(TITLE)).pages
    [data] = re.findall(r"base64,([A-Za-z0-9+/=]+)\)", page.svg)
    cmap = TTFont(io.BytesIO(base64.b64decode(data))).getBestCmap()
    assert cmap is not None
    held = {chr(code) for code in cmap}
    assert held == set("Plan & <do>it")


def test_a_font_that_measures_and_cannot_be_subset_is_refused_naming_its_file(
    tmp_path: Path,
) -> None:
    whole = FONT.read_bytes()
    cut = tmp_path / "Cut.otf"
    cut.write_bytes(whole[: len(whole) * 3 // 4])
    assert text.Face("Cut", cut).upem

    with pytest.raises(env.UnreadableFont) as raised:
        svg.render(
            scene(TITLE), key="default", colours=COLOURS, font_file=lambda _: cut, pictures={}
        )

    assert str(raised.value).startswith(f"the font file {cut} cannot be read: ")


def test_the_same_scene_and_values_give_the_same_bytes() -> None:
    assert draw(scene(TITLE)).pages == draw(scene(TITLE)).pages


def test_a_picture_is_embedded_as_the_variant_that_serves_the_combination(
    tmp_path: Path,
) -> None:
    picture = tmp_path / "colour-scheme.dark.png"
    picture.write_bytes(png(2, 2, (200, 30, 30, 255)))
    image = element(
        "image",
        "figure/picture",
        x=0,
        y=0,
        width=50,
        height=50,
        output="square",
        preserveAspectRatio="xMidYMid meet",
        variants={},
        points={},
    )
    handed = {"figure/picture": seam.Shown(picture, seam.PNG)}
    drawn = draw(scene(image), key="colour-scheme.dark", pictures=handed)
    assert drawn.losses == []
    encoded = base64.b64encode(picture.read_bytes()).decode("ascii")
    assert (
        '<image data-id="figure/picture" x="0" y="0" width="50" height="50" '
        f'preserveAspectRatio="xMidYMid meet" href="data:image/png;base64,{encoded}"/>'
    ) in drawn.pages[0].svg


#: An image of each source a scene holds (DEC-025 point 7), each 50 px square at the left.
SOURCES = {
    "a picture file of the piece": {"file": "photo.jpg", "library": "piece"},
    "a picture file of a library": {"file": "logo.png", "library": "tests@1.0.0"},
    "a picture role": {"role": "picture.logo"},
}


def image_of(source: Mapping[str, Any], trace: str = "figure/picture") -> dict[str, Any]:
    return element(
        "image",
        trace,
        x=0,
        y=0,
        width=50,
        height=50,
        preserveAspectRatio="xMidYMid meet",
        **source,
    )


#: The data a picture of each test file is embedded as.
ENCODINGS = {
    "palette.png": "image/png",
    "grey.png": "image/png",
    "alpha.png": "image/png",
    "profile.png": "image/png",
    "colour.jpg": "image/jpeg",
    "grey.jpg": "image/jpeg",
    "progressive.jpg": "image/jpeg",
    "profile.jpg": "image/jpeg",
}


@pytest.mark.parametrize("source", list(SOURCES))
@pytest.mark.parametrize("name", list(ENCODINGS))
def test_each_encoding_read_is_embedded_whole_as_its_kind_whatever_its_source(
    source: str, name: str
) -> None:
    """Every encoding the reader reads draws (DEC-025 point 5), its bytes as they are, so a
    colour profile it carries stays with it: JPEG data for a JPEG, PNG data for a PNG. The
    renderer draws what it is handed, from a scene built by hand of each source, a picture
    role's included, and reads no document of values for it."""
    path = TEST_PICTURES / name
    kind = seam.JPEG if name.endswith(".jpg") else seam.PNG
    handed = {"figure/picture": seam.Shown(path, kind)}

    drawn = draw(scene(image_of(SOURCES[source])), pictures=handed)

    assert drawn.losses == []
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    assert (
        '<image data-id="figure/picture" x="0" y="0" width="50" height="50" '
        f'preserveAspectRatio="xMidYMid meet" href="data:{ENCODINGS[name]};base64,{encoded}"/>'
    ) in drawn.pages[0].svg


def test_a_colour_profile_stays_with_the_picture() -> None:
    page = draw(
        scene(image_of(SOURCES["a picture file of the piece"])),
        pictures={"figure/picture": seam.Shown(TEST_PICTURES / "profile.jpg", seam.JPEG)},
    ).pages[0]
    image = ElementTree.fromstring(page.svg).find(".//{*}image")
    assert image is not None
    href = image.get("href")
    assert href is not None
    embedded = base64.b64decode(href.partition(",")[2])
    assert b"ICC_PROFILE" in embedded
    assert embedded == (TEST_PICTURES / "profile.jpg").read_bytes()


@pytest.mark.parametrize("source", list(SOURCES))
def test_an_image_handed_no_picture_is_left_out_and_says_why(source: str) -> None:
    drawn = draw(scene(image_of(SOURCES[source])), pictures={})
    [loss] = drawn.losses
    assert (loss.what, loss.did) == ("figure/picture", "left-out")
    assert (
        loss.why
        == {
            "a picture file of the piece": "the picture file `photo.jpg` of `piece` is not found "
            "to draw in `default`: `pkit visual check flow` names why",
            "a picture file of a library": "the picture file `logo.png` of `tests@1.0.0` is not "
            "found to draw in `default`: `pkit visual check flow` names why",
            "a picture role": "the brand gives the picture role `picture.logo` no file in "
            "`default`",
        }[source]
    )
    assert "figure/picture" not in drawn.pages[0].svg


def test_a_picture_is_handed_by_the_images_trace_id_not_by_its_name() -> None:
    first = image_of({"file": "photo.jpg", "library": "piece"}, "figure/first")
    second = image_of({"file": "photo.jpg", "library": "piece"}, "figure/second")
    handed = {"figure/second": seam.Shown(TEST_PICTURES / "colour.jpg", seam.JPEG)}

    drawn = draw(scene(first, second), pictures=handed)

    assert [loss.what for loss in drawn.losses] == ["figure/first"]
    assert 'data-id="figure/second"' in drawn.pages[0].svg


# --- losses -------------------------------------------------------------------------------------


def test_what_it_cannot_draw_is_a_loss_in_the_seams_form() -> None:
    drawn = draw(
        scene(
            element("polygon", "figure/arrow", x=0, y=0, width=10, height=10),
            element("box", "figure/odd", x=0, y=0, width=10, height=10, fill="no-such-role"),
            element("image", "figure/missing", x=0, y=0, width=10, height=10, output="square"),
        )
    )
    assert [loss.as_dict() for loss in drawn.losses] == [
        {
            "plugin": "svg",
            "what": "figure/arrow",
            "did": "refused",
            "why": "the svg renderer draws no `polygon`",
        },
        {
            "plugin": "svg",
            "what": "figure/odd",
            "did": "left-out",
            "why": "the brand gives the role `no-such-role` of its fill no colour in `default`",
        },
        {
            "plugin": "svg",
            "what": "figure/missing",
            "did": "left-out",
            "why": "the produced output `square` has no variant for `default`: run "
            "`pkit visual produce flow square`",
        },
    ]
    page = drawn.pages[0].svg
    assert "figure/arrow" not in page
    assert '<rect data-id="figure/odd" x="0" y="0" width="10" height="10" fill="none"/>' in page
    assert "figure/missing" not in page


def test_a_line_that_holds_neither_its_ends_nor_its_points_is_refused() -> None:
    # As a connector the engine could not route once was: its frame, its paint, no ends.
    endless = element(
        "line", "figure/links[ab]/l", x=0, y=0, width=0, height=0, stroke="ink",
        **{"marker-end": "arrow"},
    )  # fmt: skip
    halved = element("line", "figure/half", x=0, y=0, width=10, height=0, x1=0, y1=0)

    drawn = draw(scene(endless, halved, element("box", "figure/b", x=0, y=0, width=5, height=5)))

    why = "the line holds neither its ends, `x1 y1 x2 y2`, nor its points"
    assert [loss.as_dict() for loss in drawn.losses] == [
        {"plugin": "svg", "what": "figure/links[ab]/l", "did": "refused", "why": why},
        {"plugin": "svg", "what": "figure/half", "did": "refused", "why": why},
    ]
    page = drawn.pages[0].svg
    assert "figure/links[ab]/l" not in page and "figure/half" not in page
    assert "<marker" not in page  # an arrowhead of a line left out is not defined
    assert '<rect data-id="figure/b"' in page
    ElementTree.fromstring(page)


def test_a_colour_rounds_half_up_and_keeps_its_alpha() -> None:
    assert canvas.colour_text({"components": [0.5, 1 / 255 / 2, 1], "alpha": 0.5}) == (
        "#8001ff",
        0.5,
    )
    assert canvas.number(-0.001) == "0"
    assert canvas.number(2.505) == "2.5"
    assert canvas.number(3.10) == "3.1"


# --- the declaration ----------------------------------------------------------------------------


def test_it_draws_every_primitive_it_declares_and_declares_every_one_it_draws() -> None:
    declared = set(svg_declaration.DECLARATION["draws"])
    assert declared == {"group", "box", "ellipse", "line", "text", "image", "path"}
    drawn_by = {name[1:] for name in vars(canvas.Canvas) if name[1:] in declared}
    assert drawn_by == declared


def test_it_is_shipped_through_the_seam_as_plain_data() -> None:
    assert seam.declaration("svg", seam.RENDERER) == svg_declaration.DECLARATION
    assert svg.NAME == "svg"
    assert svg.VERSION == "1.5.0"


#: Each plugin the capability ships, with its own version.
SHIPPED = {"svg": "1.5.0", "pdf": "1.6.0", "html": "1.9.0", "css": "1.0.0", "json": "1.0.0"}


def test_the_seam_rose_once_and_every_shipped_plugin_reads_it_at_its_own_version() -> None:
    """The seam's version rose to 9 for a step of an order, which a paint may name and whose
    value comes with the scene (DEC-032 point 5): the SVG and the HTML renderers came to give
    it an id and a custom property of its own, so their versions rose, and the PDF renderer
    paints it as any colour it is handed, so its version stands. It rose to 8 for a run's sign
    and ground, which a scene's line holds with the run's piece (DEC-036 points 3 and 7), and
    to 7 for the path, a concept's sign the
    engine mapped into its frame (DEC-036 points 1 and 7). Each renderer came to draw them, so
    its version rose; the code writers read no scene, so theirs stand. It rose to 6 for the
    physical size of the piece's top, which the scene's root holds (DEC-034 point 3)."""
    assert seam.SEAM_VERSION == 9
    declared = {name: seam.declaration(name) for name in SHIPPED}
    assert {name: each["seam"] for name, each in declared.items()} == dict.fromkeys(SHIPPED, 9)
    assert {name: each["version"] for name, each in declared.items()} == SHIPPED
    assert set(SHIPPED) <= set(seam.names())


def test_it_declares_each_property_of_an_image_of_every_source() -> None:
    """A produced output's, a picture file's and a picture role's (DEC-025 point 7), so no
    image of any source is a loss known before it runs."""
    image = svg_declaration.DECLARATION["draws"]["image"]
    every = {"output", "variants", "points", "file", "library", "role", "preserveAspectRatio"}
    assert every <= set(image)


def test_a_loss_names_a_key_in_a_field_no_other_loss_carries() -> None:
    held = {"plugin": "html", "what": "figure/back", "did": "left-out", "why": "no colour"}
    assert seam.Loss(**held).as_dict() == held
    assert seam.Loss(**held, key="colour-scheme.dark").as_dict() == {
        **held,
        "key": "colour-scheme.dark",
    }


# --- a family's name ----------------------------------------------------------------------------

#: Family names a brand may give, each holding what could end the style element, break the
#: CSS around it, or leave the file malformed XML.
HOSTILE = [
    "</style><script>alert(1)</script>",
    "Joe's Sans",
    'The "Sans"',
    "Back\\slash",
    "Line\nbreak",
    "Not￿a character",
]

SVG = "{http://www.w3.org/2000/svg}"

#: A CSS string between double quotes, and an escape inside one.
CSS_STRING = re.compile(r'"(?:[^"\\]|\\.)*"', re.DOTALL)
CSS_ESCAPE = re.compile(r"\\([0-9a-fA-F]{1,6})[ \t\n]?|\\(.)", re.DOTALL)


def css_strings(text: str) -> list[str]:
    """Each CSS string in `text`, read back to the code points its escapes name."""
    return [
        CSS_ESCAPE.sub(lambda m: chr(int(m[1], 16)) if m[1] else m[2], quoted[1:-1])
        for quoted in CSS_STRING.findall(text)
    ]


def named(families: list[str]) -> dict[str, Any]:
    """A text drawn in `families`, each of them embedded."""
    return element(
        "text",
        "figure/named",
        x=0,
        y=0,
        width=100,
        height=20,
        text="Aa",
        paragraphs=[[run("Aa", fill="ink", **{"font-family": families})]],
        lines=[line(0, 15, (0, "Aa", 20))],
        **{"line-height": 20, "measured-height": 20},
    )


def test_a_familys_name_is_written_as_a_css_string_as_pinned() -> None:
    assert canvas.css_string('A "b" \\ <&>\x07\n￿\ud800\x85 é') == (
        '"A \\"b\\" \\\\ \\3c \\26 \\3e \\7 \\a \\ffff \\d800 \\85  é"'
    )


def test_a_familys_name_reaches_the_file_whole_and_as_nothing_else() -> None:
    drawn = draw(scene(named(HOSTILE)))
    assert drawn.losses == []
    root = ElementTree.fromstring(drawn.pages[0].svg)
    assert {node.tag.removeprefix(SVG) for node in root.iter()} == {
        "svg",
        "defs",
        "style",
        "g",
        "text",
        "tspan",
    }
    [style] = root.iter(f"{SVG}style")
    assert style.text is not None and not set(style.text) & set("<>&")
    assert sorted(css_strings(style.text)) == sorted(HOSTILE)
    rest = re.sub(r"base64,[A-Za-z0-9+/=]+\)", "base64,…)", CSS_STRING.sub("…", style.text))
    face = (
        "@font-face{font-family:…;font-weight:400;"
        "src:url(data:font/otf;base64,…) format('opentype');}"
    )
    assert rest == face * len(HOSTILE) + "text{white-space:pre}"
    [text] = root.iter(f"{SVG}text")
    listed = text.get("font-family", "")
    assert css_strings(listed) == HOSTILE
    assert CSS_STRING.sub("…", listed) == ", ".join(["…"] * len(HOSTILE))


def test_every_name_a_brand_may_give_draws_as_itself() -> None:
    every = "".join(chr(code) for code in range(0x10000)) + "\U0001f600\U0010ffff"
    drawn = draw(scene(named([every])))
    root = ElementTree.fromstring(drawn.pages[0].svg)
    [style] = root.iter(f"{SVG}style")
    [text] = root.iter(f"{SVG}text")
    assert style.text is not None
    assert css_strings(style.text) == [every]
    assert css_strings(text.get("font-family", "")) == [every]


# --- runs ---------------------------------------------------------------------------------------

#: A line of three runs: the middle one in the semibold family, larger and in the accent.
SAID = element(
    "text",
    "figure/said",
    x=0,
    y=0,
    width=200,
    height=30,
    text="Say <it> now",
    paragraphs=[
        [
            run("Say ", fill="ink"),
            run(
                "<it>",
                fill="accent",
                style="type.heading",
                **{
                    "font-family": ["Source Sans Pro Semibold"],
                    "font-size": 24,
                    "font-weight": 600,
                },
            ),
            run(" now", fill="ink"),
        ]
    ],
    lines=[line(0, 21.5, (0, "Say ", 30), (1, "<it>", 40), (2, " now", 30))],
    **{"line-height": 30, "measured-height": 30},
)


def drawn_runs(*children: dict[str, Any]) -> Any:
    files = {"Source Sans Pro": FONT, "Source Sans Pro Semibold": SEMIBOLD}
    return svg.render(
        scene(*children), key="default", colours=COLOURS, font_file=files.__getitem__, pictures={}
    )


def test_a_run_that_looks_otherwise_is_drawn_in_a_span_of_its_own_as_pinned() -> None:
    drawn = drawn_runs(SAID)
    assert drawn.losses == []
    [page] = drawn.pages
    shown = re.sub(r"base64,[A-Za-z0-9+/=]+\)", "base64,…)", page.svg)
    assert shown == (
        HEAD + "<defs><style>"
        '@font-face{font-family:"Source Sans Pro";font-weight:400;'
        "src:url(data:font/otf;base64,…) format('opentype');}"
        '@font-face{font-family:"Source Sans Pro Semibold";font-weight:600;'
        "src:url(data:font/otf;base64,…) format('opentype');}"
        "text{white-space:pre}</style></defs>"
        '<g data-id="figure" data-component="foundations/figure" data-version="1.0.0">'
        '<text data-id="figure/said" xml:space="preserve" '
        'font-family="&quot;Source Sans Pro&quot;" font-size="16" fill="#000000">'
        '<tspan x="0" y="21.5">Say '
        '<tspan font-family="&quot;Source Sans Pro Semibold&quot;" font-size="24" '
        'font-weight="600" fill="#4080bf" fill-opacity="1">&lt;it&gt;</tspan> now</tspan>'
        "</text></g></svg>\n"
    )
    assert drawn_runs(SAID).pages == drawn.pages


def test_each_font_a_run_draws_in_is_embedded_with_the_characters_drawn_in_it() -> None:
    [page] = drawn_runs(SAID).pages
    held = []
    for data in re.findall(r"base64,([A-Za-z0-9+/=]+)\)", page.svg):
        cmap = TTFont(io.BytesIO(base64.b64decode(data))).getBestCmap()
        assert cmap is not None
        held.append({chr(code) for code in cmap})
    regular, semibold = held
    # Each subset holds a space too, as every subset the renderer makes does.
    assert regular == set("Say now")
    assert semibold == set("<it> ")


def test_a_run_painted_with_a_role_the_brand_gives_no_colour_is_a_loss() -> None:
    lost = element(
        "text",
        "figure/lost",
        x=0,
        y=0,
        width=200,
        height=20,
        text="ab",
        paragraphs=[[run("a", fill="ink"), run("b", fill="no-such-role")]],
        lines=[line(0, 15, (0, "a", 10), (1, "b", 10))],
        **{"line-height": 20, "measured-height": 20},
    )
    drawn = drawn_runs(lost)
    assert [loss.as_dict() for loss in drawn.losses] == [
        {
            "plugin": "svg",
            "what": "figure/lost",
            "did": "left-out",
            "why": "the brand gives the role `no-such-role` of its fill no colour in `default`",
        }
    ]
    assert (
        '<tspan font-family="&quot;Source Sans Pro&quot;" font-size="16" font-weight="400" '
        'fill="none">b</tspan>' in drawn.pages[0].svg
    )
