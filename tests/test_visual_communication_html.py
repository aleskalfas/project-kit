"""The HTML renderer (visual-communication DEC-020 points 1 to 4, DEC-005 points 4, 5, 9 and
10): what it declares, what its page file holds, and what it reports it lost.

These tests read the file, as DEC-020 point 5 gives them, and start no browser. The file is
well-formed XML, so `ElementTree` reads it; an HTML parser reads the same elements
(`html_elements`). What a browser makes of the file is the viewing step's to see.

The reference output below is pinned to the renderer's version, 1.0.0. A change that gives
another output for the same scene and values raises the version, and changes it with it
(DEC-005 point 9). A font and a picture are pinned by what they hold, not by their bytes.
"""

from __future__ import annotations

import base64
import io
import re
from collections.abc import Iterator, Mapping
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

import pytest
from fontTools.ttLib import TTFont

from tests.in_process import load
from tests.test_visual_communication_pipeline import drawing_project, project_of
from tests.test_visual_communication_svg import (
    COLOURS,
    FONT,
    HOSTILE,
    SAID,
    SEMIBOLD,
    SHAPES,
    TIES,
    TITLE,
    css_strings,
    element,
    line,
    run,
    scene,
)
from tests.visual_communication_producer import png
from tests.visual_communication_project import importable

html, html_declaration, svg, svg_declaration, seam, pl, checks = load(
    "visual-communication",
    "plugins.html",
    "plugins.html_declaration",
    "plugins.svg",
    "plugins.svg_declaration",
    "plugins.seam",
    "pipeline",
    "checks",
)

MARKS = html_declaration.MARKS

#: The families of the runs below, each with its committed file. A name of `HOSTILE` draws
#: in the first file, as any name does in `drawn_as_named`.
FILES = {"Source Sans Pro": FONT, "Source Sans Pro Semibold": SEMIBOLD}

#: The most a length of the page may lie from the engine's, in px of the page.
WITHIN = 0.01


def draw(drawn: Mapping[str, Any], *, pictures: Any = None) -> Any:
    return html.render(
        drawn,
        key="default",
        colours=COLOURS,
        font_file=FILES.__getitem__,
        pictures=pictures or {},
    )


def read(drawn: Mapping[str, Any], *, pictures: Any = None) -> ElementTree.Element:
    """The file `drawn` gives, as a tree of its elements."""
    return ElementTree.fromstring(draw(drawn, pictures=pictures).document)


def marked(root: ElementTree.Element, what: str) -> list[ElementTree.Element]:
    """Each element of the file that bears the mark of `what`, in the document's order."""
    return [node for node in root.iter() if MARKS[what] in node.attrib]


def styled(node: ElementTree.Element) -> dict[str, str]:
    """An element's `style`, each declaration by its property."""
    style = node.get("style", "")
    return dict(part.split(":", 1) for part in style.split(";") if part)


def px(share: str, width: float) -> float:
    """A share of a page `width` px wide, in px of that page."""
    assert share.endswith("cqw")
    return float(share.removesuffix("cqw")) * width / 100


def sheet(root: ElementTree.Element) -> str:
    """The file's one style element, its faces cut short."""
    [style] = root.iter("style")
    assert style.text is not None
    return shown(style.text)


def rule(root: ElementTree.Element, what: str) -> str:
    """What the file's sheet says of the mark of `what`."""
    [found] = re.findall(rf"(?<!\+)\[{MARKS[what]}\]\{{([^}}]*)\}}", sheet(root))
    return found


def shown(text: str) -> str:
    """`text` without the bytes of what the file embeds."""
    return re.sub(r"base64,[A-Za-z0-9+/=]+", "base64,…", text)


def page_of(trace: str, width: float, height: float, *children: dict[str, Any]) -> dict[str, Any]:
    return element(
        "group",
        trace,
        x=0,
        y=0,
        width=width,
        height=height,
        component="foundations/figure",
        version="1.0.0",
        page=True,
        children=list(children),
    )


def of_pages(*pages: dict[str, Any]) -> dict[str, Any]:
    """A scene of `pages`, each with a frame of its own."""
    return {**scene(), "pages": [page["id"] for page in pages], "children": list(pages)}


def box(trace: str, **look: Any) -> dict[str, Any]:
    return element("box", trace, x=0, y=0, width=20, height=20, fill="accent", **look)


def arrow(trace: str) -> dict[str, Any]:
    """A line with an arrowhead, in the ink."""
    return element(
        "line",
        trace,
        x=0,
        y=5,
        width=50,
        height=0,
        x1=0,
        y1=5,
        x2=50,
        y2=5,
        stroke="ink",
        **{"marker-end": "arrow"},
    )


def said(
    trace: str, words: str, *, width: float = 60, families: list[str] | None = None
) -> dict[str, Any]:
    """A text of one line and one run, at the page's top left, in `families` where given."""
    look = {"font-family": families} if families else {}
    return element(
        "text",
        trace,
        x=0,
        y=0,
        width=width,
        height=20,
        text=words,
        paragraphs=[[run(words, fill="ink", **look)]],
        lines=[line(0, 15, (0, words, 40))],
        **{"line-height": 20, "measured-height": 20},
    )


# --- the declaration ----------------------------------------------------------------------------


def test_it_is_shipped_through_the_seam_as_plain_data() -> None:
    assert seam.declaration("html", seam.RENDERER) == html_declaration.DECLARATION
    assert html.NAME == "html"
    assert html.VERSION == "1.0.0"


def test_it_declares_what_it_draws_and_needs() -> None:
    declared = html_declaration.DECLARATION
    assert declared["draws"] == svg_declaration.DECLARATION["draws"]
    assert declared["profile"] == "default"
    assert declared["programs"] == []
    assert declared["services"] == []


def test_it_declares_each_choice_the_scene_leaves_open() -> None:
    assert html_declaration.DECLARATION["pages"] == {
        "lie": "one under another, each in the middle of the window",
        "gap": 24,
        "scale": "shrinks with a narrower window and never grows",
    }


def test_its_module_holds_the_marks_as_data() -> None:
    assert html_declaration.MARKS == {
        "page": "data-page",
        "layer": "data-layer",
        "text": "data-text",
        "line": "data-line",
        "strut": "data-strut",
        "span": "data-span",
    }
    assert html_declaration.DECLARATION["marks"] == html_declaration.MARKS


# --- a text -------------------------------------------------------------------------------------


def test_each_text_is_one_element_at_its_frame_and_none_lies_in_svg() -> None:
    root = read(scene(*SHAPES["children"][0]["children"], TITLE))

    assert not {"text", "tspan"} & {node.tag for node in root.iter()}
    [text] = marked(root, "text")
    assert text.tag == "div"
    assert text.get(MARKS["text"]) == "figure/title"
    frame = styled(text)
    assert px(frame["left"], 200) == pytest.approx(10, abs=WITHIN)
    assert px(frame["top"], 200) == pytest.approx(5, abs=WITHIN)
    assert px(frame["width"], 200) == pytest.approx(100, abs=WITHIN)
    assert rule(root, "text") == "position:absolute"


def test_each_line_is_a_child_placed_alone_that_never_wraps() -> None:
    root = read(scene(TITLE))

    [text] = marked(root, "text")
    assert [node.tag for node in text] == ["div", "div"]
    assert all(MARKS["line"] in node.attrib for node in text)
    assert [[span.text for span in marked(node, "span")] for node in text] == [
        ["Plan & <do>"],
        ["it"],
    ]
    assert rule(root, "line") == (
        "position:absolute;left:0;width:100%;font-size:0;line-height:0;white-space:pre"
    )


def test_a_strut_opens_each_line_and_the_lines_top_is_its_baseline_less_its_height() -> None:
    root = read(scene(TITLE))

    [text] = marked(root, "text")
    for index, node in enumerate(text):
        strut = node[0]
        assert MARKS["strut"] in strut.attrib
        assert strut.tag == "span" and strut.text is None and len(strut) == 0
        height = px(styled(strut)["height"], 200)
        assert height == pytest.approx(16, abs=WITHIN)
        baseline = 15.2 + index * 20
        assert px(styled(node)["top"], 200) == pytest.approx(baseline - 16, abs=WITHIN)
    assert rule(root, "strut") == "display:inline-block;width:0"


@pytest.mark.parametrize(("largest", "strut"), [(24, 24), (13.5, 14), (0.25, 1)])
def test_a_strut_is_a_whole_number_of_page_px_taller_than_any_run_rises(
    largest: float, strut: int
) -> None:
    text = element(
        "text",
        "figure/said",
        x=0,
        y=0,
        width=100,
        height=30,
        text="ab",
        paragraphs=[
            [
                run("a", fill="ink", **{"font-size": 0.25}),
                run("b", fill="ink", **{"font-size": largest}),
            ]
        ],
        lines=[line(0, 20, (0, "a", 10), (1, "b", 10))],
        **{"line-height": 30, "measured-height": 30},
    )

    [found] = marked(read(scene(text)), "strut")

    assert px(styled(found)["height"], 200) == pytest.approx(strut, abs=WITHIN)


def test_a_line_of_no_span_still_stands_on_a_strut() -> None:
    blank = {**TITLE, "lines": [line(0, 15)]}
    [found] = marked(read(scene(blank)), "strut")
    assert px(styled(found)["height"], 200) == pytest.approx(1, abs=WITHIN)


@pytest.mark.parametrize(
    ("anchor", "aligned"), [("start", None), ("middle", "center"), ("end", "end")]
)
def test_a_lines_alignment_in_the_frame_is_its_texts_anchor(
    anchor: str, aligned: str | None
) -> None:
    [text] = marked(read(scene({**TITLE, "text-anchor": anchor})), "text")
    assert styled(text).get("text-align") == aligned


@pytest.mark.parametrize(
    ("anchor", "left", "width"), [("middle", -20, 140), ("end", -40, 140), ("start", None, None)]
)
def test_a_line_wider_than_its_frame_keeps_the_place_its_anchor_gives_it(
    anchor: str, left: float | None, width: float | None
) -> None:
    wide = {**said("figure/wide", "Antidisestablishment"), "text-anchor": anchor, "width": 100}
    wide["lines"] = [line(0, 15, (0, "Antidisestablishment", 140))]

    [found] = marked(read(scene(wide)), "line")

    place = styled(found)
    if left is None:
        assert "left" not in place and "width" not in place
    else:
        assert px(place["left"], 200) == pytest.approx(left, abs=WITHIN)
        assert px(place["width"], 200) == pytest.approx(width, abs=WITHIN)


def test_runs_follow_each_other_and_no_span_takes_a_place_of_its_own() -> None:
    root = read(scene(SAID))

    spans = marked(root, "span")
    assert [span.text for span in spans] == ["Say ", "<it>", " now"]
    assert [set(styled(span)) - {"font-weight"} for span in spans] == [
        {"font-family", "font-size", "color"}
    ] * 3
    assert rule(root, "line").count("position") == 1
    assert styled(spans[1])["font-weight"] == "600"
    assert styled(spans[1])["font-family"] == '"Source Sans Pro Semibold"'
    assert px(styled(spans[1])["font-size"], 200) == pytest.approx(24, abs=WITHIN)
    assert styled(spans[1])["color"] == "#4080bf"


def test_a_run_across_a_line_break_is_a_span_on_each_line() -> None:
    two = {
        **said("figure/two", "one two"),
        "lines": [line(0, 15, (0, "one", 20)), line(0, 15, (0, "two", 20))],
    }
    root = read(scene(two))
    assert [span.text for span in marked(root, "span")] == ["one", "two"]
    assert len(marked(root, "line")) == 2


# --- lengths ------------------------------------------------------------------------------------


def test_every_length_of_a_text_lies_within_a_hundredth_of_a_px_at_the_pages_own_size() -> None:
    odd = element(
        "text",
        "figure/odd",
        x=33.337,
        y=71.113,
        width=401.771,
        height=40,
        text="Odd",
        paragraphs=[[run("Odd", fill="ink", **{"font-size": 17.333})]],
        lines=[line(0, 19.391, (0, "Odd", 30))],
        **{"line-height": 22.219, "measured-height": 22.219},
    )
    moved = element(
        "group",
        "figure/moved",
        x=1000.123,
        y=500.457,
        width=300,
        height=100,
        children=[odd],
    )

    root = read(scene(moved, width=1280, height=720))

    [text] = marked(root, "text")
    [row] = marked(root, "line")
    [strut] = marked(root, "strut")
    [span] = marked(root, "span")
    for share, length in (
        (styled(text)["left"], 1033.46),
        (styled(text)["top"], 571.57),
        (styled(text)["width"], 401.771),
        (styled(strut)["height"], 18),
        (styled(row)["top"], 19.391 - 18),
        (styled(span)["font-size"], 17.333),
    ):
        assert px(share, 1280) == pytest.approx(length, abs=WITHIN)


def test_a_page_writes_no_length_but_a_share_of_its_width() -> None:
    root = read(scene(SAID, TITLE))

    [page] = marked(root, "page")
    declared = [
        (prop, value)
        for node in page.iter()
        if node is not page
        for prop, value in styled(node).items()
        if prop not in ("font-family", "font-weight", "color", "text-align")
    ]
    assert {prop for prop, _ in declared} == {"left", "top", "width", "height", "font-size"}
    assert all(value.endswith("cqw") for _, value in declared)


# --- shapes -------------------------------------------------------------------------------------


@pytest.mark.parametrize("drawn", [SHAPES, TIES], ids=["shapes", "ties"])
def test_a_shape_is_written_as_the_svg_renderer_writes_it(drawn: dict[str, Any]) -> None:
    file = draw(drawn).document.decode()
    [page] = svg.render(
        drawn, key="default", colours=COLOURS, font_file=FILES.__getitem__, pictures={}
    ).pages
    shapes = re.findall(r"<(?:rect|ellipse|line|polyline) [^>]*/>", page.svg)
    assert shapes
    assert all(shape in file for shape in shapes)


def test_a_picture_is_written_as_the_svg_renderer_writes_it(tmp_path: Path) -> None:
    picture = tmp_path / "default.png"
    picture.write_bytes(png(2, 2, (200, 30, 30, 255)))
    image = element(
        "image",
        "figure/picture",
        x=5,
        y=6,
        width=50,
        height=40,
        output="square",
        preserveAspectRatio="xMidYMid meet",
    )
    drawn = scene(image)
    [page] = svg.render(
        drawn,
        key="default",
        colours=COLOURS,
        font_file=FILES.__getitem__,
        pictures={"square": picture},
    ).pages
    [written] = re.findall(r"<image [^>]*/>", page.svg)

    assert written in draw(drawn, pictures={"square": picture}).document.decode()
    assert f"base64,{base64.b64encode(picture.read_bytes()).decode()}" in written


def test_a_shape_keeps_the_moves_of_its_groups_and_no_group_is_an_element() -> None:
    inner = element(
        "group",
        "figure/outer/inner",
        x=1.5,
        y=2,
        width=30,
        height=30,
        children=[box("figure/outer/inner/dot")],
    )
    outer = element(
        "group", "figure/outer", x=10, y=20, width=50, height=50, component="tests/card",
        children=[inner, box("figure/outer/back")],
    )  # fmt: skip

    root = read(scene(outer))

    [layer] = marked(root, "layer")
    assert [
        (node.get("transform"), [shape.get("data-id") for shape in node]) for node in layer
    ] == [
        ("translate(11.5,22)", ["figure/outer/inner/dot"]),
        ("translate(10,20)", ["figure/outer/back"]),
    ]
    assert "figure/outer" not in {node.get("data-id") for node in root.iter()}


def test_a_shape_with_no_move_takes_no_group_around_it() -> None:
    [layer] = marked(read(scene(box("figure/plain"))), "layer")
    assert [node.tag for node in layer] == ["rect"]


# --- layers and the tree's order ----------------------------------------------------------------


def leaves(elements: list[dict[str, Any]]) -> Iterator[str]:
    """The trace id of each element of a page's tree that is no group, in the tree's order."""
    for child in elements:
        if child["type"] == "group":
            yield from leaves(child["children"])
        else:
            yield child["id"]


def document_order(page: ElementTree.Element) -> list[str]:
    """Each text and shape of a page, in the document's order."""
    found = []
    for child in page:
        if MARKS["text"] in child.attrib:
            found.append(str(child.get(MARKS["text"])))
        else:
            found.extend(
                str(node.get("data-id")) for node in child.iter() if "data-id" in node.attrib
            )
    return found


#: A tree of text, shape, text, shape, the first text and the second shape inside groups.
ORDERED = scene(
    element(
        "group",
        "figure/top",
        x=4,
        y=4,
        width=100,
        height=50,
        children=[said("figure/top/title", "Over"), box("figure/top/first")],
    ),
    said("figure/lead", "Under"),
    element(
        "group",
        "figure/rest",
        x=8,
        y=8,
        width=100,
        height=50,
        children=[box("figure/rest/second"), box("figure/rest/third")],
    ),
)


def test_the_documents_order_is_the_trees_order() -> None:
    [page] = marked(read(ORDERED), "page")

    assert document_order(page) == list(leaves(ORDERED["children"]))
    assert [node.tag for node in page] == ["div", "svg", "div", "svg"]


def test_a_layer_out_of_the_trees_order_fails() -> None:
    [page] = marked(read(ORDERED), "page")
    moved = page[1]
    page.remove(moved)
    page.append(moved)

    assert document_order(page) != list(leaves(ORDERED["children"]))


def test_each_run_of_shapes_between_two_texts_is_one_layer() -> None:
    run_of_shapes = scene(box("figure/a"), box("figure/b"), TITLE, box("figure/c"), box("figure/d"))

    root = read(run_of_shapes)

    assert [
        [node.get("data-id") for node in layer if node.get("data-id")]
        for layer in marked(root, "layer")
    ] == [["figure/a", "figure/b"], ["figure/c", "figure/d"]]


def test_a_text_with_no_shape_beside_it_takes_no_layer() -> None:
    assert marked(read(scene(TITLE)), "layer") == []


def test_a_layer_is_the_size_of_its_page_and_takes_no_pointer() -> None:
    root = read(scene(box("figure/a"), width=300, height=150))

    [layer] = marked(root, "layer")
    assert layer.tag == "svg"
    assert layer.get("viewBox") == "0 0 300 150"
    assert rule(root, "layer") == (
        "position:absolute;left:0;top:0;width:100%;height:100%;pointer-events:none"
    )


# --- the file -----------------------------------------------------------------------------------


def test_the_head_declares_the_encoding_the_language_and_the_viewport() -> None:
    file = draw(scene(TITLE)).document
    root = ElementTree.fromstring(file)

    assert file.startswith(b"<!DOCTYPE html>\n<html ")
    assert root.get("lang") == "en"
    head = root.find("head")
    assert head is not None
    charset, viewport = head.findall("meta")
    assert charset.get("charset") == "utf-8"
    assert viewport.get("name") == "viewport"
    assert viewport.get("content") == "width=device-width,initial-scale=1"
    assert file.index(b"<meta charset") < 1024  # a browser looks no further for it


def test_the_file_is_utf_8_so_czech_reaches_it_as_written() -> None:
    words = "Příliš žluťoučký kůň"
    file = draw(scene(said("figure/czech", words))).document
    assert words.encode("utf-8") in file


def test_the_file_names_its_piece_key_and_renderer() -> None:
    root = read(scene(TITLE))
    assert root.get("data-piece") == "flow"
    assert root.get("data-key") == "default"
    assert root.get("data-renderer") == "html 1.0.0"


def test_pages_follow_each_other_in_the_middle_of_the_window_with_the_declared_gap() -> None:
    root = read(of_pages(page_of("first", 100, 50), page_of("second", 100, 50)))

    assert [page.get(MARKS["page"]) for page in marked(root, "page")] == ["first", "second"]
    assert "margin:0 auto" in rule(root, "page")
    gap = html_declaration.DECLARATION["pages"]["gap"]
    assert f"[data-page]+[data-page]{{margin-top:{gap}px}}" in sheet(root)
    assert "body{margin:0}" in sheet(root)


def test_the_file_sets_no_colour_around_its_pages() -> None:
    root = read(scene(TITLE))
    rules = re.sub(r"@font-face\{[^}]*\}", "", sheet(root))
    assert not re.search(r"background|color", rules)
    [page] = marked(root, "page")
    assert set(styled(page)) == {"width", "aspect-ratio"}


def test_a_page_shrinks_with_the_window_and_keeps_its_proportions_and_never_grows() -> None:
    root = read(scene(TITLE, width=1280, height=720))

    [page] = marked(root, "page")
    assert styled(page) == {"width": "min(100%,1280px)", "aspect-ratio": "1280/720"}
    assert "container-type:inline-size" in rule(root, "page")


def test_no_rule_of_the_file_clips_a_text() -> None:
    file = shown(draw(scene(SAID, *TIES["children"][0]["children"], TITLE)).document.decode())
    assert not re.search(r"overflow|clip|hidden", file)


def test_pages_of_two_sizes_each_keep_their_own_size_and_their_own_shares() -> None:
    wide = page_of("wide", 400, 100, said("wide/said", "Wide", width=100))
    small = page_of("small", 200, 200, said("small/said", "Small", width=100))

    root = read(of_pages(wide, small))

    assert [styled(page) for page in marked(root, "page")] == [
        {"width": "min(100%,400px)", "aspect-ratio": "400/100"},
        {"width": "min(100%,200px)", "aspect-ratio": "200/200"},
    ]
    assert [styled(text)["width"] for text in marked(root, "text")] == ["25cqw", "50cqw"]


def test_drawn_says_which_pages_the_file_holds_in_order() -> None:
    drawn = draw(of_pages(page_of("first", 100, 50), page_of("second", 100, 50)))
    assert drawn.pages == ["first", "second"]
    assert isinstance(drawn.document, bytes)


def test_a_page_the_tree_does_not_hold_is_not_drawn() -> None:
    drawn = draw({**scene(TITLE), "pages": ["figure", "gone"]})
    assert drawn.pages == ["figure"]


# --- a file asks for nothing --------------------------------------------------------------------


def faces(root: ElementTree.Element) -> dict[tuple[str, str], set[str]]:
    """Each face the file's sheet holds, by its family and weight, with its characters."""
    [style] = root.iter("style")
    assert style.text is not None
    found: dict[tuple[str, str], set[str]] = {}
    rules = re.findall(
        r'@font-face\{font-family:"([^"]*)";font-weight:(\d+);src:url\(data:[^;]*;base64,'
        r"([A-Za-z0-9+/=]+)\)",
        style.text,
    )
    for family, weight, data in rules:
        assert (family, weight) not in found
        cmap = TTFont(io.BytesIO(base64.b64decode(data))).getBestCmap()
        assert cmap is not None
        found[(family, weight)] = {chr(code) for code in cmap}
    return found


def test_each_face_lies_once_subset_to_every_character_the_file_draws_in_it() -> None:
    first = page_of("first", 200, 100, said("first/said", "Ab"))
    second = page_of("second", 100, 100, said("second/said", "cd"))

    root = read(of_pages(first, second))

    assert faces(root) == {("Source Sans Pro", "400"): set("Abcd ")}
    assert sheet(root).count("@font-face") == 1


def test_a_run_in_two_families_embeds_each() -> None:
    text = said("figure/both", "Ab", families=["Source Sans Pro", "Source Sans Pro Semibold"])
    root = read(scene(text))

    assert faces(root) == {
        ("Source Sans Pro", "400"): set("Ab "),
        ("Source Sans Pro Semibold", "400"): set("Ab "),
    }
    [span] = marked(root, "span")
    assert styled(span)["font-family"] == '"Source Sans Pro", "Source Sans Pro Semibold"'


def test_the_file_finds_no_address_but_a_data_one(tmp_path: Path) -> None:
    picture = tmp_path / "default.png"
    picture.write_bytes(png(2, 2, (200, 30, 30, 255)))
    image = element(
        "image", "figure/picture", x=0, y=0, width=50, height=50, output="square",
    )  # fmt: skip

    file = draw(
        scene(image, SAID, *TIES["children"][0]["children"]), pictures={"square": picture}
    ).document.decode()

    addresses = re.findall(r"""url\(([^)]*)\)|\b(?:href|src|action)=["']([^"']*)""", file)
    held = [one or other for one, other in addresses]
    assert any(address.startswith("data:font/") for address in held)
    assert any(address.startswith("data:image/") for address in held)
    assert all(address.startswith(("data:", "#")) for address in held)
    assert not re.search(r"@import|http|//|<link|<script", shown(file))


# --- ids and arrowheads -------------------------------------------------------------------------


def test_a_marker_defined_once_serves_two_pages_of_one_colour_of_arrow() -> None:
    first = page_of("first", 100, 50, arrow("first/a"), said("first/said", "Ab"), arrow("first/b"))
    second = page_of("second", 100, 50, arrow("second/a"))

    root = read(of_pages(first, second))

    ids = [str(node.get("id")) for node in root.iter() if "id" in node.attrib]
    assert ids == ["pkit-arrow-end-000000"]
    [marker] = root.iter("marker")
    assert [path.get("fill") for path in marker] == ["#000000"]
    used = [node.get("marker-end") for node in root.iter("line")]
    assert used == ["url(#pkit-arrow-end-000000)"] * 3
    assert len(marked(root, "layer")) == 3


def test_the_markers_lie_outside_every_page_and_layer_in_an_svg_of_no_size() -> None:
    root = read(scene(arrow("figure/a")))

    body = root.find("body")
    assert body is not None
    holder, page = body
    assert (holder.tag, holder.get("width"), holder.get("height")) == ("svg", "0", "0")
    assert MARKS["layer"] not in holder.attrib
    assert styled(holder) == {"position": "absolute"}
    assert MARKS["page"] in page.attrib


def test_a_file_with_no_arrowhead_holds_no_marker_sheet() -> None:
    body = read(scene(TITLE)).find("body")
    assert body is not None
    assert [MARKS["page"] in node.attrib for node in body] == [True]


def test_an_arrowhead_of_each_colour_lies_once_and_every_id_is_unique() -> None:
    root = read(TIES)

    ids = [str(node.get("id")) for node in root.iter() if "id" in node.attrib]
    assert len(ids) == 3
    assert len(set(ids)) == 3


# --- marks --------------------------------------------------------------------------------------


def test_the_file_marks_each_page_layer_text_line_strut_and_span() -> None:
    root = read(scene(box("figure/back"), SAID, TITLE))

    assert [page.get(MARKS["page"]) for page in marked(root, "page")] == ["figure"]
    assert [layer.tag for layer in marked(root, "layer")] == ["svg"]
    assert [text.get(MARKS["text"]) for text in marked(root, "text")] == [
        "figure/said",
        "figure/title",
    ]
    assert len(marked(root, "line")) == 3
    assert len(marked(root, "strut")) == 3
    assert len(marked(root, "span")) == 5


def test_a_shape_keeps_the_canvass_mark_and_a_text_takes_none_of_it() -> None:
    root = read(scene(box("figure/back"), TITLE))
    assert [node.get("data-id") for node in root.iter() if "data-id" in node.attrib] == [
        "figure/back"
    ]


# --- colours and losses -------------------------------------------------------------------------


def test_a_run_whose_role_has_no_colour_is_written_with_no_paint_and_is_a_loss() -> None:
    text = said("figure/lost", "Ab")
    text["paragraphs"] = [[run("Ab", fill="no-such-role")]]

    drawn = draw(scene(text))

    assert [loss.as_dict() for loss in drawn.losses] == [
        {
            "plugin": "html",
            "what": "figure/lost",
            "did": "left-out",
            "why": "the brand gives the role `no-such-role` of its fill no colour in `default`",
        }
    ]
    [span] = marked(ElementTree.fromstring(drawn.document), "span")
    assert styled(span)["color"] == "transparent"


def test_a_run_with_no_fill_takes_no_colour_of_the_browsers() -> None:
    text = said("figure/bare", "Ab")
    text["paragraphs"] = [[run("Ab")]]

    drawn = draw(scene(text))

    assert drawn.losses == []
    [span] = marked(ElementTree.fromstring(drawn.document), "span")
    assert styled(span)["color"] == "transparent"


def test_a_translucent_run_keeps_its_alpha_in_its_colour() -> None:
    text = said("figure/faint", "Ab")
    text["paragraphs"] = [[run("Ab", fill="shade")]]

    [span] = marked(read(scene(text)), "span")

    assert styled(span)["color"] == "#00000040"


def test_a_shape_whose_role_has_no_colour_is_a_loss_under_its_name() -> None:
    drawn = draw(scene(element("box", "figure/odd", x=0, y=0, width=9, height=9, fill="gone")))

    assert [(loss.plugin, loss.what, loss.did) for loss in drawn.losses] == [
        ("html", "figure/odd", "left-out")
    ]
    assert 'fill="none"' in drawn.document.decode()


def test_a_picture_with_no_variant_is_left_out_and_leaves_no_layer() -> None:
    image = element("image", "figure/picture", x=0, y=0, width=50, height=50, output="square")

    drawn = draw(scene(image))

    assert [(loss.plugin, loss.what, loss.did) for loss in drawn.losses] == [
        ("html", "figure/picture", "left-out")
    ]
    assert marked(ElementTree.fromstring(drawn.document), "layer") == []


def test_a_line_that_holds_neither_its_ends_nor_its_points_is_refused() -> None:
    halved = element("line", "figure/half", x=0, y=0, width=10, height=0, x1=0, y1=0)

    drawn = draw(scene(halved))

    assert [(loss.plugin, loss.what, loss.did) for loss in drawn.losses] == [
        ("html", "figure/half", "refused")
    ]
    assert "figure/half" not in drawn.document.decode()


def test_a_primitive_it_does_not_declare_is_refused_under_its_name() -> None:
    drawn = draw(scene(element("path", "figure/path", x=0, y=0, width=9, height=9)))

    assert [(loss.plugin, loss.what, loss.did) for loss in drawn.losses] == [
        ("html", "figure/path", "refused")
    ]


# --- what a brand or a piece names --------------------------------------------------------------


class HtmlElements(HTMLParser):
    """The element names an HTML parser reads, and the text it reads in a `span`."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tags: list[str] = []
        self.spans: list[str] = []
        self._in_span = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags.append(tag)
        self._in_span = tag == "span" and MARKS["span"] in dict(attrs)

    def handle_endtag(self, tag: str) -> None:
        self._in_span = False

    def handle_data(self, data: str) -> None:
        if self._in_span:
            self.spans.append(data)


def html_elements(file: bytes) -> HtmlElements:
    parser = HtmlElements()
    parser.feed(file.decode("utf-8"))
    parser.close()
    return parser


def drawn_as_named(families: list[str], words: str = "Aa") -> Any:
    """`words` drawn in `families`, each in the first committed file."""
    text = said("figure/named", words, families=families)
    return html.render(
        scene(text), key="default", colours=COLOURS, font_file=lambda _: FONT, pictures={}
    )


def test_a_familys_name_reaches_the_file_whole_and_as_nothing_else() -> None:
    file = drawn_as_named(HOSTILE).document
    root = ElementTree.fromstring(file)

    assert "script" not in {node.tag for node in root.iter()}
    assert "script" not in html_elements(file).tags
    [style] = root.iter("style")
    assert style.text is not None and not set(style.text) & set("<&")
    assert sorted(css_strings(style.text)) == sorted(HOSTILE)
    [span] = marked(root, "span")
    assert css_strings(span.get("style", "")) == HOSTILE


def test_a_text_that_holds_a_style_end_and_a_script_stays_text() -> None:
    words = "a < b </style><script>alert(1)</script>"
    file = drawn_as_named(["</style><script>"], words).document
    root = ElementTree.fromstring(file)

    assert [span.text for span in marked(root, "span")] == [words]
    assert "script" not in {node.tag for node in root.iter()}
    read_as_html = html_elements(file)
    assert "script" not in read_as_html.tags
    assert read_as_html.spans == [words]


def test_a_piece_named_to_end_its_title_ends_nothing() -> None:
    named_badly = {**scene(TITLE), "piece": "</title><script>"}
    file = draw(named_badly).document
    root = ElementTree.fromstring(file)
    assert root.get("data-piece") == "</title><script>"
    assert "script" not in html_elements(file).tags


def test_a_trace_id_reaches_its_mark_as_written() -> None:
    trace = 'figure/steps["a"]<b>'
    [text] = marked(read(scene({**TITLE, "id": trace})), "text")
    assert text.get(MARKS["text"]) == trace


def test_an_html_parser_reads_the_elements_the_xml_reader_reads() -> None:
    file = draw(scene(SHAPES["children"][0]["children"][0], SAID, *TIES["children"][0]["children"]))
    root = ElementTree.fromstring(file.document)

    assert html_elements(file.document).tags == [node.tag.lower() for node in root.iter()]


# --- the same bytes -----------------------------------------------------------------------------


def reference_picture(folder: Path) -> Path:
    picture = folder / "default.png"
    picture.write_bytes(png(2, 2, (200, 30, 30, 255)))
    return picture


#: The reference scene: each primitive, a picture and an ellipse among them, a run in two
#: families, a text under a later box, and pages of two sizes that draw one colour of arrow.
REFERENCE = of_pages(
    page_of(
        "first",
        200,
        100,
        element(
            "box",
            "first/back",
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
            "image",
            "first/picture",
            x=150,
            y=10,
            width=40,
            height=40,
            output="square",
            preserveAspectRatio="xMidYMid meet",
        ),
        element(
            "group",
            "first/mark",
            x=10.5,
            y=20,
            width=120,
            height=60,
            component="tests/card",
            version="1.0.0",
            children=[
                element("ellipse", "first/mark/dot", x=0, y=0, width=50, height=30, fill="accent"),
                {
                    **said(
                        "first/mark/both",
                        "Aé",
                        width=100,
                        families=["Source Sans Pro", "Source Sans Pro Semibold"],
                    ),
                    "y": 30,
                    "text-anchor": "middle",
                },
                arrow("first/mark/arrow"),
            ],
        ),
        element(
            "box",
            "first/over",
            x=20,
            y=50,
            width=30,
            height=10,
            fill="shade",
        ),
    ),
    page_of(
        "second",
        120,
        60,
        said("second/said", "Ab <c>"),
        arrow("second/arrow"),
    ),
)

PINNED = (
    "<!DOCTYPE html>\n"
    '<html lang="en" data-piece="flow" data-key="default" data-renderer="html 1.0.0">\n'
    "<head>\n"
    '<meta charset="utf-8"/>\n'
    '<meta name="viewport" content="width=device-width,initial-scale=1"/>\n'
    "<title>flow</title>\n"
    '<style>@font-face{font-family:"Source Sans Pro";font-weight:400;'
    "src:url(data:font/otf;base64,…) format('opentype');}"
    '@font-face{font-family:"Source Sans Pro Semibold";font-weight:400;'
    "src:url(data:font/otf;base64,…) format('opentype');}"
    "body{margin:0}"
    "[data-page]{position:relative;container-type:inline-size;margin:0 auto}"
    "[data-page]+[data-page]{margin-top:24px}"
    "[data-layer]{position:absolute;left:0;top:0;width:100%;height:100%;pointer-events:none}"
    "[data-text]{position:absolute}"
    "[data-line]{position:absolute;left:0;width:100%;font-size:0;line-height:0;white-space:pre}"
    "[data-strut]{display:inline-block;width:0}</style>\n"
    "</head>\n"
    '<body><svg width="0" height="0" style="position:absolute"><defs>'
    '<marker id="pkit-arrow-end-000000" viewBox="0 0 10 10" refX="10" refY="5" '
    'markerWidth="5" markerHeight="5" orient="auto">'
    '<path d="M0,0L10,5L0,10z" fill="#000000"/></marker></defs></svg>'
    '<div data-page="first" style="width:min(100%,200px);aspect-ratio:200/100">'
    '<svg data-layer="" viewBox="0 0 200 100">'
    '<rect data-id="first/back" x="1" y="1" width="198" height="98" rx="4" '
    'fill="#ffffff" stroke="#808080" stroke-width="2"/>'
    '<image data-id="first/picture" x="150" y="10" width="40" height="40" '
    'preserveAspectRatio="xMidYMid meet" href="data:image/png;base64,…"/>'
    '<g transform="translate(10.5,20)">'
    '<ellipse data-id="first/mark/dot" cx="25" cy="15" rx="25" ry="15" fill="#4080bf"/>'
    "</g></svg>"
    '<div data-text="first/mark/both" style="left:5.25cqw;top:25cqw;width:50cqw;'
    'text-align:center">'
    '<div data-line="" style="top:-0.5cqw">'
    '<span data-strut="" style="height:8cqw"></span>'
    '<span data-span="" style="font-family:&quot;Source Sans Pro&quot;, '
    '&quot;Source Sans Pro Semibold&quot;;font-size:8cqw;color:#000000">Aé</span>'
    "</div></div>"
    '<svg data-layer="" viewBox="0 0 200 100">'
    '<g transform="translate(10.5,20)">'
    '<line data-id="first/mark/arrow" x1="0" y1="5" x2="50" y2="5" stroke="#000000" '
    'marker-end="url(#pkit-arrow-end-000000)"/></g>'
    '<rect data-id="first/over" x="20" y="50" width="30" height="10" '
    'fill="#000000" fill-opacity="0.25"/>'
    "</svg></div>"
    '<div data-page="second" style="width:min(100%,120px);aspect-ratio:120/60">'
    '<div data-text="second/said" style="left:0cqw;top:0cqw;width:50cqw">'
    '<div data-line="" style="top:-0.83333cqw">'
    '<span data-strut="" style="height:13.33333cqw"></span>'
    '<span data-span="" style="font-family:&quot;Source Sans Pro&quot;;'
    'font-size:13.33333cqw;color:#000000">Ab &lt;c&gt;</span>'
    "</div></div>"
    '<svg data-layer="" viewBox="0 0 120 60">'
    '<line data-id="second/arrow" x1="0" y1="5" x2="50" y2="5" stroke="#000000" '
    'marker-end="url(#pkit-arrow-end-000000)"/>'
    "</svg></div></body>\n"
    "</html>\n"
)


def test_the_reference_scene_is_drawn_as_pinned_for_version_1_0_0(
    tmp_path: Path,
) -> None:
    pictures = {"square": reference_picture(tmp_path)}

    drawn = draw(REFERENCE, pictures=pictures)

    assert drawn.losses == []
    assert drawn.pages == ["first", "second"]
    assert shown(drawn.document.decode()) == PINNED
    assert faces(ElementTree.fromstring(drawn.document)) == {
        ("Source Sans Pro", "400"): set("Aé Ab<c>"),
        ("Source Sans Pro Semibold", "400"): set("Aé "),
    }
    data = re.search(r'href="data:image/png;base64,([A-Za-z0-9+/=]+)"', drawn.document.decode())
    assert data is not None
    assert base64.b64decode(data[1]) == pictures["square"].read_bytes()


def test_the_same_scene_and_values_give_the_same_bytes(tmp_path: Path) -> None:
    pictures = {"square": reference_picture(tmp_path)}
    assert (
        draw(REFERENCE, pictures=pictures).document == draw(REFERENCE, pictures=pictures).document
    )


def test_the_svg_renderers_version_stays() -> None:
    assert svg.VERSION == "1.0.1"


# --- a piece through the engine -----------------------------------------------------------------


def test_a_piece_the_engine_computes_is_drawn_with_every_text_it_holds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    importable(monkeypatch, html)
    project = project_of(drawing_project(tmp_path, picture=False))
    results = project.scenes(facts=project.piece.stand_ins)

    drawn = list(pl.drawn(project, results, "html"))

    assert [key for _, key, _ in drawn] == list(project.keys)
    declared = html_declaration.DECLARATION
    for language, result in results:
        held = result.scene.to_dict()
        assert checks.losses(held, declared) == []
        for _, _, file in (each for each in drawn if each[0] == language):
            assert file.losses == []
            assert file.pages == held["pages"]
            root = ElementTree.fromstring(file.document)
            assert root.get("lang") == language
            words = [span.text for span in marked(root, "span")]
            assert words == [
                span["text"]
                for node, _, _ in checks._walk(held["children"])
                if node.get("type") == "text"
                for row in node.get("lines", [])
                for span in row.get("spans", [])
            ]
