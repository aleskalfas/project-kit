"""The SVG renderer (visual-communication DEC-005 points 4, 5, 9 and 10): what it declares,
what it draws, and what it reports it lost.

The reference outputs below are pinned to the renderer's version, 1.0.1. A change that
gives another output for the same scene and values raises the version, and changes them
with it (DEC-005 point 9). The font a text embeds is pinned by the characters its subset
holds, not by its bytes, which are fontTools'. A text of one run is drawn as it was
before runs (DEC-012 point 7), so runs left the version as it was; a text of several runs
draws each run that looks otherwise than its first in a span of its own. A line with no
arrowhead and no corners is drawn as it was before ties (DEC-011), so ties left it too;
a tie's connector with corners is a polyline, and an arrowhead a marker in its colour.
"""

from __future__ import annotations

import base64
import io
import re
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

import pytest
from fontTools.ttLib import TTFont

from tests.in_process import load
from tests.visual_communication_producer import png
from tests.visual_communication_project import TEST_BRAND

svg, svg_declaration, seam, env, text = load(
    "visual-communication", "plugins.svg", "plugins.svg_declaration", "plugins.seam", "env", "text"
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
        "seam": 3,
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
    'data-renderer="svg 1.0.1">'
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


def test_shapes_are_drawn_as_pinned_for_version_1_0_1() -> None:
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


def test_a_connector_and_its_arrowheads_are_drawn_as_pinned_for_version_1_0_1() -> None:
    drawn = draw(TIES)
    assert drawn.losses == []
    [page] = drawn.pages
    assert page.svg == (
        HEAD + "<defs><style>text{white-space:pre}</style>"
        '<marker id="pkit-arrow-end-000000" viewBox="0 0 10 10" refX="10" refY="5" '
        'markerWidth="5" markerHeight="5" orient="auto">'
        '<path d="M0,0L10,5L0,10z" fill="#000000"/></marker>'
        '<marker id="pkit-arrow-end-000000-025" viewBox="0 0 10 10" refX="10" refY="5" '
        'markerWidth="5" markerHeight="5" orient="auto">'
        '<path d="M0,0L10,5L0,10z" fill="#000000" fill-opacity="0.25"/></marker>'
        '<marker id="pkit-arrow-start-000000-025" viewBox="0 0 10 10" refX="0" refY="5" '
        'markerWidth="5" markerHeight="5" orient="auto">'
        '<path d="M10,0L0,5L10,10z" fill="#000000" fill-opacity="0.25"/></marker>'
        "</defs>"
        '<g data-id="figure" data-component="foundations/figure" data-version="1.0.0">'
        '<polyline data-id="figure/links[ab]/l" data-start="figure/steps[a]" '
        'data-end="figure/steps[b]" points="10,20 60,20 60,60 110,60" fill="none" '
        'stroke="#000000" stroke-width="2" marker-end="url(#pkit-arrow-end-000000)"/>'
        '<line data-id="figure/rule" x1="0" y1="90" x2="200" y2="90" stroke="#000000" '
        'stroke-opacity="0.25" marker-start="url(#pkit-arrow-start-000000-025)" '
        'marker-end="url(#pkit-arrow-end-000000-025)"/>'
        "</g></svg>\n"
    )
    # The same scene gives the same file.
    assert draw(TIES).pages[0].svg == page.svg
    ElementTree.fromstring(page.svg)


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
    assert svg.VERSION == "1.0.1"


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
    assert svg.css_string('A "b" \\ <&>\x07\n￿\ud800\x85 é') == (
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
