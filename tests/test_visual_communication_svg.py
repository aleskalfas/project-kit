"""The SVG renderer (visual-communication DEC-005 points 4, 5, 9 and 10): what it declares,
what it draws, and what it reports it lost.

The reference outputs below are pinned to the renderer's version, 1.0.0. A change that
gives another output for the same scene and values raises the version, and changes them
with it (DEC-005 point 9). The font a text embeds is pinned by the characters its subset
holds, not by its bytes, which are fontTools'.
"""

from __future__ import annotations

import base64
import io
import re
from pathlib import Path
from typing import Any

from fontTools.ttLib import TTFont

from tests.in_process import load
from tests.visual_communication_producer import png
from tests.visual_communication_project import TEST_BRAND

svg, svg_declaration, seam = load(
    "visual-communication", "plugins.svg", "plugins.svg_declaration", "plugins.seam"
)

FONT = TEST_BRAND / "fonts" / "SourceSansPro-Regular.otf"

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
        "seam": 1,
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
    'data-renderer="svg 1.0.0">'
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


def test_shapes_are_drawn_as_pinned_for_version_1_0_0() -> None:
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


TITLE = element(
    "text",
    "figure/title",
    x=10,
    y=5,
    width=100,
    height=40,
    fill="ink",
    style="type.heading",
    text="Plan & <do> it",
    lines=[{"text": "Plan & <do>", "width": 80}, {"text": "it", "width": 9}],
    fonts=[{"family": "Source Sans Pro", "file": FONT.name, "sha256": "pinned-by-the-scene"}],
    baseline=15.2,
    measured="file",
    **{
        "text-anchor": "middle",
        "font-family": ["Source Sans Pro"],
        "font-size": 16,
        "font-weight": 600,
        "line-height": 20,
        "measured-height": 40,
    },
)


def test_text_is_drawn_as_its_measured_lines_with_its_font_embedded() -> None:
    drawn = draw(scene(TITLE))
    assert drawn.losses == []
    [page] = drawn.pages
    shown = re.sub(r"base64,[A-Za-z0-9+/=]+\)", "base64,…)", page.svg)
    assert shown == (
        HEAD + "<defs><style>"
        "@font-face{font-family:'Source Sans Pro';font-weight:600;"
        "src:url(data:font/otf;base64,…) format('opentype');}"
        "text{white-space:pre}</style></defs>"
        '<g data-id="figure" data-component="foundations/figure" data-version="1.0.0">'
        '<text data-id="figure/title" xml:space="preserve" font-family="\'Source Sans Pro\'" '
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
    drawn = draw(scene(image), key="colour-scheme.dark", pictures={"square": picture})
    assert drawn.losses == []
    encoded = base64.b64encode(picture.read_bytes()).decode("ascii")
    assert (
        '<image data-id="figure/picture" x="0" y="0" width="50" height="50" '
        f'preserveAspectRatio="xMidYMid meet" href="data:image/png;base64,{encoded}"/>'
    ) in drawn.pages[0].svg


# --- losses -------------------------------------------------------------------------------------


def test_what_it_cannot_draw_is_a_loss_in_the_seams_form() -> None:
    drawn = draw(
        scene(
            element("path", "figure/arrow", x=0, y=0, width=10, height=10),
            element("box", "figure/odd", x=0, y=0, width=10, height=10, fill="no-such-role"),
            element("image", "figure/missing", x=0, y=0, width=10, height=10, output="square"),
        )
    )
    assert [loss.as_dict() for loss in drawn.losses] == [
        {
            "plugin": "svg",
            "what": "figure/arrow",
            "did": "refused",
            "why": "the svg renderer draws no `path`",
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


def test_a_colour_rounds_half_up_and_keeps_its_alpha() -> None:
    assert svg.colour_text({"components": [0.5, 1 / 255 / 2, 1], "alpha": 0.5}) == (
        "#8001ff",
        0.5,
    )
    assert svg.number(-0.001) == "0"
    assert svg.number(2.505) == "2.5"
    assert svg.number(3.10) == "3.1"


# --- the declaration ----------------------------------------------------------------------------


def test_it_draws_every_primitive_it_declares_and_declares_every_one_it_draws() -> None:
    declared = set(svg_declaration.DECLARATION["draws"])
    assert declared == {"group", "box", "ellipse", "line", "text", "image"}
    drawn_by = {name[1:] for name in vars(svg._Canvas) if name[1:] in declared | {"path"}}
    assert drawn_by == declared


def test_it_is_shipped_through_the_seam_as_plain_data() -> None:
    assert seam.declaration("svg", seam.RENDERER) == svg_declaration.DECLARATION
    assert svg.NAME == "svg"
    assert svg.VERSION == "1.0.0"
