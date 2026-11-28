"""`pkit visual look <piece>` and `pkit visual pages <piece>` (visual-communication DEC-015,
DEC-020 points 5, 7 and 8): the viewing step's tool, what it reports of text drawn to
nothing, the images, frames and report it writes, and what it refuses. Then the HTML
renderer's pages drawn through a browser: its folder, its page files, its report and its
stop. Run in this process, the renderers standing in for the import a run makes when it
draws.

No test needs a browser. Where a run reads the HTML renderer's pages, a stand-in speaks the
browser's pipe (`visual_communication_browser`), or `viewing_browser.draw` is replaced. No
test here holds a pixel as a contract (DEC-015 point 6). One compares two drawings of one
run, or asks whether an image is blank, and so runs on any machine and any tool."""

from __future__ import annotations

import itertools
import json
import math
import re
import shutil
import struct
import subprocess
import sys
import xml.etree.ElementTree as ET
from collections.abc import Callable, Iterator, Mapping, Sequence
from pathlib import Path
from typing import Any

import pytest
from fontTools import subset
from fontTools.ttLib import TTFont
from ruamel.yaml import YAML

from tests import visual_communication_producer as producer
from tests.in_process import load, run_main
from tests.test_visual_communication_pipeline import (
    OUTPUT,
    PHONE,
    PIECE,
    PIECE_FOLDER,
    drawing_project,
    exported_up_to,
    filled,
    on_devices,
    parts_project,
    stamped,
    two_steps,
    write_content,
    write_picture,
)
from tests.test_visual_communication_starter import PIECES, TEST_NOTATION, UNRELEASED
from tests.test_visual_communication_svg import COLOURS, FONT, SEMIBOLD, element, line, run, scene
from tests.test_visual_communication_viewing_browser import FUNCTIONS, planted
from tests.test_visual_communication_viewing_browser import page as held_page
from tests.test_visual_communication_viewing_browser import span as held_span
from tests.test_visual_communication_viewing_browser import text as held_text
from tests.visual_communication_browser import called, logged, stand_in
from tests.visual_communication_project import (
    LOOK_REPORT,
    RELEASED_FOUNDATIONS,
    RELEASES,
    TEST_BRAND,
    bound,
    copy_library,
    importable,
    project,
    reports_held,
    write,
    write_list,
    yaml_text,
)

(
    look,
    pages,
    svg,
    html,
    seam,
    framing,
    viewing,
    viewing_tool,
    viewing_browser,
    islands,
    names,
    pl,
    exports,
) = load(
    "visual-communication",
    "look.py",
    "pages.py",
    "plugins.svg",
    "plugins.html",
    "plugins.seam",
    "framing",
    "viewing",
    "viewing_tool",
    "viewing_browser",
    "islands",
    "names",
    "pipeline",
    "exports",
)

LOCK = ["foundations 1.0.0", "test-brand 1.0.0", "tests 1.0.0"]
CODE = TEST_BRAND / "fonts" / "SourceCodePro-Regular.ttf"
BRAND_TOKENS = "visual/libraries/test-brand/1.0.0/tokens/base.tokens.json"


@pytest.fixture(autouse=True)
def plugins(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """The renderers stand in for the import a run makes when it draws, and the test
    producer is registered, for the length of the test."""
    importable(monkeypatch, svg, html)
    producer.register(seam)
    yield
    seam.unregister(producer.NAME)
    seam.unregister("svg")


@pytest.fixture(autouse=True)
def reports_hold_their_schema(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Each report a look of the test writes holds to the report's schema."""
    refused = reports_held(monkeypatch, viewing)
    yield
    assert refused == []


def run_look(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return run_main(look, *args, cwd=root)


def folder_of(root: Path, piece: str = PIECE) -> Path:
    return root / viewing.FOLDER / piece


def report_of(root: Path, piece: str = PIECE) -> dict[str, Any]:
    return json.loads((folder_of(root, piece) / viewing.REPORT).read_text(encoding="utf-8"))


def on_white(root: Path) -> None:
    """The brand's background made clear, so a page draws no ground of its own."""
    tokens = root / BRAND_TOKENS
    held = json.loads(tokens.read_text(encoding="utf-8"))
    held["background"]["$value"] = {"colorSpace": "srgb", "components": [1, 1, 1], "alpha": 0}
    tokens.write_text(json.dumps(held), encoding="utf-8")


def written(root: Path) -> dict[str, bytes]:
    """Every file of the project but the libraries', with its bytes."""
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file() and "libraries" not in path.parts
    }


def blank(image: bytes) -> bytes:
    """An image of the size of `image` with nothing drawn on it, on the ground."""
    width, height = struct.unpack(">II", image[16:24])
    empty = f'<svg xmlns="{viewing_tool.SVG_NAMESPACE}" width="{width}" height="{height}"/>'
    return bytes(
        viewing_tool.resvg_py.svg_to_bytes(svg_string=empty, background=viewing_tool.GROUND)
    )


def faceless(words: str, family: str, **look: Any) -> dict[str, Any]:
    """A run of a family the page embeds no face of, so one the tool cannot match."""
    return {**run(words, **{"font-family": [family]}, **look), "fonts": []}


def text_element(trace: str, *runs: dict[str, Any], y: float = 0, **fields: Any) -> dict[str, Any]:
    """A text of one line on the page, of `runs`, each its own span."""
    spans = [(at, each["text"], 40) for at, each in enumerate(runs)]
    return element(
        "text",
        trace,
        **{
            "x": 10,
            "y": y,
            "width": 180,
            "height": 22,
            "text": "".join(each["text"] for each in runs),
            "paragraphs": [list(runs)],
            "lines": [line(0, 16, *spans)],
            "line-height": 22,
            "measured-height": 22,
            **fields,
        },
    )


def drawn_page(*children: dict[str, Any], **sizes: Any) -> str:
    """The SVG page the renderer draws of `children`."""
    files = {
        "Source Sans Pro": FONT,
        "Source Sans Pro Semibold": SEMIBOLD,
        "Source Code Pro": CODE,
    }
    drawn = svg.render(
        scene(*children, **sizes),
        key="default",
        colours=COLOURS,
        font_file=lambda family: files.get(family, FONT),
        pictures={},
    )
    [page] = drawn.pages
    return page.svg


def tool(tmp_path: Path, *children: dict[str, Any], long_edge: int = 800, **sizes: Any) -> Any:
    """The page of `children` drawn whole, at the scale that sets its long edge `long_edge`
    pixels long."""
    [page] = viewing.pages_of(scene(*children, **sizes))
    edge = max(float(page["width"]), float(page["height"])) or 1.0
    return tool_at(tmp_path, long_edge / edge, *children, **sizes)


def tool_at(tmp_path: Path, scale: float, *children: dict[str, Any], **sizes: Any) -> Any:
    """The page of `children` drawn whole, at `scale` image pixels to a px."""
    [page] = viewing.pages_of(scene(*children, **sizes))
    drawn = drawn_page(*children, **sizes)
    return viewing_tool.draw(drawn, scale, tmp_path, viewing.line_widths(page))


#: The fills a line's runs take by turns where `set_at` sets more than one: the renderer writes
#: runs of one look as one span.
RUN_FILLS = ("ink", "accent")


def plant(
    tmp_path: Path,
    words: str | Sequence[str],
    em: float,
    scale: float,
    over: Callable[[float, float], dict[str, Any]] | None = None,
    *,
    moved: tuple[float, float] = (0.0, 0.0),
) -> Any:
    """The page of `words` set `em` image pixels high at `scale`, drawn whole. `words` is one
    run, or a run for each of a sequence, on one line, in ink and accent by turns, so that each
    is a span of its own. `over` gives the box drawn after the text, from where the text's
    baseline lies and its font size in px, as the box's fields. `moved` moves the text so many
    px across and down from where it is set, and leaves the page as it is."""
    children, sizes = plant_of(words, em, scale, over, moved=moved)
    return tool_at(tmp_path, scale, *children, **sizes)


def baseline_of(size: float) -> float:
    """Where `plant` sets the baseline of a line whose font is `size` px, in the page's px: 16
    px below its text's top, and low enough for the line's ascenders."""
    return max(46.0, 0.85 * size)


def plant_of(
    words: str | Sequence[str],
    em: float,
    scale: float,
    over: Callable[[float, float], dict[str, Any]] | None = None,
    *,
    moved: tuple[float, float] = (0.0, 0.0),
) -> tuple[list[dict[str, Any]], dict[str, float]]:
    """The elements of the page `plant` draws, in order, and its width and height in px."""
    size = em / scale
    baseline = baseline_of(size)
    said = text_element(
        "figure/said",
        *(
            run(each, fill=RUN_FILLS[at % len(RUN_FILLS)], **{"font-size": size})
            for at, each in enumerate([words] if isinstance(words, str) else words)
        ),
        x=10 + moved[0],
        y=baseline + moved[1] - 16,
        width=11 * size,
    )
    children = [said]
    if over is not None:
        box = over(baseline + moved[1], size)
        children.append(element("box", "figure/over", fill="surface", **box))
    return children, {"width": 12 * size, "height": baseline + 0.6 * size}


def set_at(
    tmp_path: Path,
    words: str | Sequence[str],
    em: float,
    scale: float,
    over: Callable[[float, float], dict[str, Any]] | None = None,
) -> list[tuple[str, float]]:
    """What the page shows of `words` set `em` image pixels high at `scale`, as `plant` sets
    them, as the cause and the share of its strong ink each loses."""
    return [(each.why, each.share) for each in plant(tmp_path, words, em, scale, over).lost]


def dropped_of(
    tmp_path: Path, *children: dict[str, Any], **sizes: Any
) -> list[tuple[str, str, bool]]:
    return [
        (each.element, each.text, each.whole) for each in tool(tmp_path, *children, **sizes).dropped
    ]


def lost_of(
    tmp_path: Path, *children: dict[str, Any], **sizes: Any
) -> list[tuple[str, str, str, float]]:
    """Each span the page shows in part, as the tool reports it, its share to a percent."""
    return [
        (each.element, each.text, each.why, round(each.share, 2))
        for each in tool(tmp_path, *children, **sizes).lost
    ]


# --- the tool: an image, and the faces handed over ----------------------------------------------


def test_a_page_is_drawn_at_the_long_edge_asked_for_with_each_face_handed_over(
    tmp_path: Path,
) -> None:
    said = text_element("figure/said", run("Say it", fill="ink"))
    drawn = tool(tmp_path, said, long_edge=800)
    [image] = drawn.images
    assert (image.width, image.height) == (800, 400)
    assert image.image != blank(image.image)
    assert drawn.dropped == ()
    assert [path.suffix for path in tmp_path.iterdir()] == [".font"]


def test_a_tall_page_takes_the_long_edge_on_its_height(tmp_path: Path) -> None:
    said = text_element("figure/said", run("Say it", fill="ink"))
    [image] = tool(tmp_path, said, width=100, height=200, long_edge=800).images
    assert (image.width, image.height) == (400, 800)


def test_a_page_that_draws_no_ground_lies_on_white(tmp_path: Path) -> None:
    [image] = tool(tmp_path, long_edge=800).images
    assert image.image == blank(image.image)


def test_a_true_type_face_and_two_weights_of_one_family_each_draw(tmp_path: Path) -> None:
    code = run("pkit status", fill="ink", **{"font-family": ["Source Code Pro"]})
    plain = run("Plain ", fill="ink")
    strong = run("strong", fill="accent", **{"font-weight": 600})
    assert dropped_of(tmp_path, text_element("figure/code", code)) == []
    assert dropped_of(tmp_path, text_element("figure/both", plain, strong)) == []


@pytest.mark.parametrize(
    "family",
    ['H&M "Sans"', "A & B", 'Quote"d', "Back\\slash", "Ends in slash\\", "<Tag>", "Plain"],
)
def test_a_family_name_a_css_string_escapes_still_draws(tmp_path: Path, family: str) -> None:
    said = text_element("figure/said", run("Say it", fill="ink", **{"font-family": [family]}))
    assert dropped_of(tmp_path, said) == []


def test_the_tool_reads_no_font_of_the_machine(tmp_path: Path) -> None:
    """A family the page embeds no face for matches nothing, whatever the machine holds."""
    named = faceless("Say it", "Arial", fill="ink")
    assert dropped_of(tmp_path, text_element("figure/said", named)) == [
        ("figure/said", "Say it", True)
    ]


def test_a_size_past_what_the_tool_is_asked_fails_and_never_reaches_it(tmp_path: Path) -> None:
    """The tool's own failure at such a size ends the process, so this test would too."""
    said = text_element("figure/said", run("Say it", fill="ink"))
    with pytest.raises(viewing_tool.ToolFailed, match="more than 134217728"):
        tool(tmp_path, said, long_edge=10**7)


def test_the_most_pixels_asked_for_still_draw(tmp_path: Path) -> None:
    [image] = tool(tmp_path, width=2, height=1, long_edge=16384).images
    assert (image.width, image.height) == (16384, 8192)


@pytest.mark.parametrize(("width", "height"), [(960, 0), (0, 540), (0, 0)])
def test_a_page_with_no_size_fails_naming_it(tmp_path: Path, width: int, height: int) -> None:
    with pytest.raises(viewing_tool.ToolFailed, match=f"{width} by {height} px"):
        tool(tmp_path, width=width, height=height)


# --- each span shaped alone, as the engine measured it ------------------------------------------


def strong_run(words: str) -> dict[str, Any]:
    """A run in a semibold family of its own, as a brand gives a weight its own file."""
    look = {"font-family": ["Source Sans Pro Semibold"], "font-weight": 600}
    return run(words, fill="ink", **look)


def page_handed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, *children: dict[str, Any]
) -> ET.Element:
    """The page as the tool is asked to draw it."""
    asked: list[str] = []
    real = viewing_tool.resvg_py.svg_to_bytes

    def asking(**given: Any) -> bytes:
        asked.append(given["svg_string"])
        return real(**given)

    monkeypatch.setattr(viewing_tool.resvg_py, "svg_to_bytes", asking)
    tool(tmp_path, *children)
    return ET.fromstring(asked[0])


def chunks_of(page: ET.Element) -> list[list[tuple[str, str | None]]]:
    """The page's chunks in order, as SVG reads them, each its text and its font: a chunk
    starts at each absolute `x` or `y`, and the tool shapes a chunk whole in each of its fonts."""
    chunks: list[list[tuple[str, str | None]]] = []

    def read(node: ET.Element, font: str | None, starts: bool) -> None:
        starts = starts or "x" in node.attrib or "y" in node.attrib
        font = node.get("font-family", font)
        if node.text:
            if starts:
                chunks.append([])
            chunks[-1].append((node.text, font))
            starts = False
        for child in node:
            read(child, font, starts)
            starts = False
            if child.tail:
                chunks[-1].append((child.tail, font))

    for text in page.iter(viewing_tool.TEXT):
        read(text, None, False)
    return chunks


def test_each_span_of_a_line_is_handed_over_as_a_chunk_of_its_own(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Shaped in one chunk, a strong run takes the weight of the face that holds its line's
    other characters, and nothing says so: the fault of `showcase`, page 3 (#2712)."""
    said = text_element("figure/said", strong_run("Say: "), run("every way", fill="accent"))
    assert chunks_of(page_handed(monkeypatch, tmp_path, said)) == [
        [("Say: ", "pkit-face-1")],
        [("every way", "pkit-face-0")],
    ]


def test_a_plain_run_is_handed_over_apart_from_the_strong_run_before_and_after_it(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A strong first run is the text's own, so the renderer writes it bare, and again after
    the plain run, where it lies in that run's tail."""
    runs = [strong_run("One "), run("two ", fill="accent"), strong_run("three")]
    assert chunks_of(page_handed(monkeypatch, tmp_path, text_element("figure/said", *runs))) == [
        [("One ", "pkit-face-1")],
        [("two ", "pkit-face-0")],
        [("three", "pkit-face-1")],
    ]


def test_a_span_set_apart_keeps_its_line_s_baseline_and_the_pen_of_the_span_before_it(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    said = text_element("figure/said", strong_run("Say: "), run("it", fill="accent"), y=30)
    page = page_handed(monkeypatch, tmp_path, said)
    [line_handed] = next(page.iter(viewing_tool.TEXT)).findall(viewing_tool.SPAN)
    second = list(line_handed)[1]
    assert second.get("y") == line_handed.get("y") == "46"
    assert second.get("x") is None


def test_the_lines_of_a_text_are_each_set_apart(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    said = text_element("figure/said", strong_run("One "), run("two", fill="accent"))
    said["lines"].append(line(0, 38, (0, "One ", 40), (1, "more", 40)))
    assert [chunk[0][0] for chunk in chunks_of(page_handed(monkeypatch, tmp_path, said))] == [
        "One ",
        "two",
        "One ",
        "more",
    ]


def test_a_text_of_one_span_is_handed_over_as_the_renderer_set_it(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    said = text_element("figure/said", run("Say it", fill="ink"))
    said["text-anchor"] = "end"
    page = page_handed(monkeypatch, tmp_path, said)
    assert chunks_of(page) == [[("Say it", "pkit-face-0")]]
    [line_handed] = next(page.iter(viewing_tool.TEXT)).findall(viewing_tool.SPAN)
    assert line_handed.get("x") == "190"
    assert line_handed.get("text-anchor") is None


@pytest.mark.parametrize(("anchor", "start"), [("middle", 60.0), ("end", 110.0)])
def test_a_line_of_spans_starts_where_its_measured_width_puts_its_anchor(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, anchor: str, start: float
) -> None:
    """The tool anchors each chunk alone, so anchored spans would lie over each other. The
    text is 180 wide from 10, and its two spans measure 40 each."""
    runs = [strong_run("Say: "), run("it", fill="accent")]
    said = text_element("figure/said", *runs)
    said["text-anchor"] = anchor
    page = page_handed(monkeypatch, tmp_path, said)
    [line_handed] = next(page.iter(viewing_tool.TEXT)).findall(viewing_tool.SPAN)
    assert float(line_handed.attrib["x"]) == start
    assert line_handed.get("text-anchor") == "start"


def test_each_line_s_width_is_the_engine_s_by_its_text() -> None:
    said = text_element("figure/said", strong_run("One "), run("two", fill="accent"))
    said["lines"].append(line(0, 38, (0, "more", 30)))
    box = element("box", "figure/box", x=0, y=0, width=10, height=10)
    [page] = viewing.pages_of(scene(box, said))
    assert viewing.line_widths(page) == {"figure/said": [80.0, 30.0]}


def test_a_run_of_the_step_hands_the_tool_the_page_s_measured_lines(
    flow: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    given: list[Mapping[str, Any]] = []
    real = viewing_tool.draw

    def drawing(
        svg_page: str, at: float, folder: Path, widths: Mapping[str, Any], **regions: Any
    ) -> Any:
        given.append(widths)
        return real(svg_page, at, folder, widths, **regions)

    monkeypatch.setattr(viewing.viewing_tool, "draw", drawing)
    assert run_look(flow, PIECE).returncode == 0
    assert given[0]["figure/body/steps[plan]/head"][0] > 0


# --- what the tool dropped (DEC-015 point 3) ----------------------------------------------------


def test_a_text_whose_role_has_no_colour_drew_nothing(tmp_path: Path) -> None:
    gone = text_element("figure/gone", run("Lost", fill="no-such-role"))
    kept = text_element("figure/kept", run("Kept", fill="ink"), y=40)
    assert dropped_of(tmp_path, gone, kept) == [("figure/gone", "Lost", True)]


def test_a_text_the_engine_painted_nothing_drew_nothing_though_no_loss_says_so(
    tmp_path: Path,
) -> None:
    unpainted = text_element("figure/gone", run("Lost"))
    assert 'fill="none"' in drawn_page(unpainted)
    assert dropped_of(tmp_path, unpainted) == [("figure/gone", "Lost", True)]


def test_a_colour_with_no_opacity_drew_nothing(tmp_path: Path) -> None:
    seen = run("Seen ", fill="ink")
    clear = run("clear", fill="see-through")
    colours = {**COLOURS, "see-through": {"components": [0, 0, 0], "alpha": 0}}
    drawn = svg.render(
        scene(text_element("figure/said", seen, clear)),
        key="default",
        colours=colours,
        font_file=lambda _family: FONT,
        pictures={},
    )
    [page] = drawn.pages
    found = viewing_tool.draw(page.svg, 4.0, tmp_path, {}).dropped
    assert [(each.text, each.whole) for each in found] == [("clear", False)]


def test_one_run_the_tool_could_not_match_is_lost_from_a_line_of_several(tmp_path: Path) -> None:
    first = run("Kept ", fill="ink")
    lost = faceless("lost", "No Such Face", fill="accent")
    last = run(" kept", fill="ink")
    assert dropped_of(tmp_path, text_element("figure/said", first, lost, last)) == [
        ("figure/said", "lost", False)
    ]


def test_one_run_with_no_colour_is_lost_from_a_line_and_the_runs_after_it_stay(
    tmp_path: Path,
) -> None:
    first = run("Kept ", fill="ink")
    lost = run("lost", fill="no-such-role")
    last = run(" kept", fill="ink")
    assert dropped_of(tmp_path, text_element("figure/said", first, lost, last)) == [
        ("figure/said", "lost", False)
    ]


def test_a_first_run_lost_from_its_line_is_the_text_the_renderer_writes_bare(
    tmp_path: Path,
) -> None:
    lost = faceless("lost ", "No Such Face")
    kept = run("kept", fill="ink")
    assert dropped_of(tmp_path, text_element("figure/said", lost, kept)) == [
        ("figure/said", "lost ", False)
    ]


def test_every_run_of_a_text_lost_is_the_whole_text_once(tmp_path: Path) -> None:
    runs = [run("One ", fill="no-such-role"), run("two", fill="no-other-role")]
    assert dropped_of(tmp_path, text_element("figure/said", *runs)) == [
        ("figure/said", "One two", True)
    ]


def test_a_text_lost_on_each_of_its_lines_is_its_lines_in_order(tmp_path: Path) -> None:
    said = text_element("figure/said", run("One", fill="no-such-role"))
    second = run("two", fill="no-such-role")
    said["paragraphs"] = [[said["paragraphs"][0][0]], [second]]
    said["lines"] = [line(0, 16, (0, "One", 40)), line(1, 38, (0, "two", 40))]
    assert dropped_of(tmp_path, said) == [("figure/said", "One two", True)]


def test_a_run_of_spaces_is_no_loss(tmp_path: Path) -> None:
    runs = [run("Kept", fill="ink"), run("   ", fill="accent")]
    assert dropped_of(tmp_path, text_element("figure/said", *runs)) == []


def test_a_text_over_a_picture_of_its_own_colour_was_drawn(tmp_path: Path) -> None:
    """An image holds no ink of such a text. The tool drew it, and the reviewer judges it."""
    picture = tmp_path / "red.png"
    picture.write_bytes(producer.png(100, 100, (255, 0, 0, 255)))
    colours = {**COLOURS, "red": {"components": [1, 0, 0], "alpha": 1}}
    over = element(
        "image", "figure/picture", x=0, y=0, width=200, height=100, output="red", variants={}
    )
    drawn = svg.render(
        scene(over, text_element("figure/said", run("Over it", fill="red"))),
        key="default",
        colours=colours,
        font_file=lambda _family: FONT,
        pictures={"figure/picture": seam.Shown(picture, seam.PNG)},
    )
    [page] = drawn.pages
    faces = tmp_path / "faces"
    faces.mkdir()
    assert viewing_tool.draw(page.svg, 4.0, faces, {}).dropped == ()


def test_a_white_text_on_white_was_drawn(tmp_path: Path) -> None:
    said = text_element("figure/said", run("Seen by nobody", fill="surface"))
    assert dropped_of(tmp_path, said) == []


def test_a_text_inside_moved_groups_is_found_where_it_stands(tmp_path: Path) -> None:
    said = text_element("figure/group/said", run("Say it", fill="ink"), x=0, y=0)
    inner = element("group", "figure/group", x=20, y=30, width=50, height=30, children=[said])
    outer = element("group", "figure/outer", x=5, y=260, width=50, height=30, children=[inner])
    assert dropped_of(tmp_path, outer, width=200, height=400) == []


# --- what the page shows of a span (DEC-045) ----------------------------------------------------


def test_a_text_the_pages_edge_cuts_is_named_cut_with_the_share_of_its_ink_past_the_edge(
    tmp_path: Path,
) -> None:
    said = text_element("figure/said", run("Cut by the edge", fill="ink"), x=170, y=30)
    found = lost_of(tmp_path, said, width=200, height=100)
    [(element_, text, why, share)] = found
    assert (element_, text, why) == ("figure/said", "Cut by the edge", viewing_tool.CUT)
    assert 0.5 < share < 1


def test_a_text_a_later_part_covers_is_named_covered_with_the_share_it_hides(
    tmp_path: Path,
) -> None:
    said = text_element("figure/said", run("Under a box", fill="ink"), y=30)
    over = element("box", "figure/over", x=0, y=0, width=60, height=100, fill="surface")
    [(_, text, why, share)] = lost_of(tmp_path, said, over)
    assert (text, why) == ("Under a box", viewing_tool.COVERED)
    assert 0.2 < share < 0.9


def test_a_box_drawn_before_a_text_covers_none_of_it(tmp_path: Path) -> None:
    under = element("box", "figure/under", x=0, y=0, width=200, height=100, fill="surface")
    said = text_element("figure/said", run("On a box", fill="ink"), y=30)
    assert lost_of(tmp_path, under, said) == []


def test_a_text_inside_its_page_and_uncovered_is_named_neither_cut_nor_covered(
    tmp_path: Path,
) -> None:
    said = text_element("figure/said", run("Whole", fill="ink"), y=30)
    assert lost_of(tmp_path, said) == []


def test_a_span_both_cut_and_covered_gives_two_entries(tmp_path: Path) -> None:
    said = text_element("figure/said", run("Cut and covered", fill="ink"), x=150, y=30)
    over = element("box", "figure/over", x=140, y=0, width=30, height=100, fill="surface")
    found = lost_of(tmp_path, said, over, width=200, height=100)
    assert [why for _, _, why, _ in found] == [viewing_tool.CUT, viewing_tool.COVERED]


def test_a_graze_under_the_threshold_is_named_neither(tmp_path: Path) -> None:
    said = text_element("figure/said", run("Edge", fill="ink"), x=10, y=30)
    over = element("box", "figure/over", x=0, y=0, width=10.3, height=100, fill="surface")
    assert lost_of(tmp_path, said, over) == []


def test_a_text_of_double_spaces_keeps_its_ink_where_the_page_puts_it_in_the_swaths(
    tmp_path: Path,
) -> None:
    """The swaths carry the page's rules, `text{white-space:pre}` among them, so the advance
    and the spaces of a text in a swath are the page's. resvg 0.48 reads that rule in neither,
    and collapses the spaces alike. Were the swaths' ink to lie elsewhere than the page's, the cover
    read would find the page's pixels alike in both draws and name the text covered with
    nothing over it."""
    said = text_element("figure/said", run("A   B   C   D", fill="ink"), y=30)
    assert "white-space:pre" in drawn_page(said)
    assert lost_of(tmp_path, said) == []


def test_the_pages_root_carries_nothing_a_text_inherits_and_one_that_does_fails_the_read(
    tmp_path: Path,
) -> None:
    said = text_element("figure/said", run("Say it", fill="ink"))
    page = drawn_page(said)
    root = ET.fromstring(page)
    assert {name for name in root.attrib if not name.startswith("data-")} <= {
        "width",
        "height",
        "viewBox",
    }
    inherited = page.replace("<svg ", '<svg font-size="99" ', 1)
    with pytest.raises(viewing_tool.ToolFailed, match="font-size"):
        viewing_tool.draw(inherited, 2.0, tmp_path, {})


def test_a_line_that_lies_off_the_page_drew_nothing(tmp_path: Path) -> None:
    said = text_element("figure/said", run("Below it", fill="ink"), y=500)
    assert dropped_of(tmp_path, said) == [("figure/said", "Below it", True)]


# --- why the tool dropped a text (DEC-045 point 2) ---------------------------------------------


def whys_of(tmp_path: Path, *children: dict[str, Any], **sizes: Any) -> list[str]:
    return [each.why for each in tool(tmp_path, *children, **sizes).dropped]


def test_a_text_with_no_ink_in_its_paint_is_dropped_for_no_ink(tmp_path: Path) -> None:
    gone = text_element("figure/gone", run("Lost", fill="no-such-role"))
    assert whys_of(tmp_path, gone) == [viewing_tool.NO_INK]


def test_a_text_wholly_below_its_page_is_dropped_off_the_page_and_never_for_no_ink(
    tmp_path: Path,
) -> None:
    said = text_element("figure/said", run("Below it", fill="ink"), y=500)
    assert whys_of(tmp_path, said) == [viewing_tool.OFF_THE_PAGE]
    assert tool(tmp_path, said).lost == ()


def test_a_text_wholly_past_a_side_is_dropped_off_the_page_alone(tmp_path: Path) -> None:
    said = text_element("figure/said", run("Beyond", fill="ink"), x=260, y=30)
    drawing = tool(tmp_path, said, width=200, height=100)
    assert [(each.element, each.why) for each in drawing.dropped] == [
        ("figure/said", viewing_tool.OFF_THE_PAGE)
    ]
    assert drawing.lost == ()


@pytest.mark.parametrize("x", (700, -900))
def test_a_text_that_starts_further_past_a_side_than_the_room_is_dropped_off_the_page(
    tmp_path: Path, x: float
) -> None:
    """The bands reach a page's width past each side, and a text further past finds no ink in
    them. It is told from a text with no ink by the engine's own geometry of its line, so the
    cure goes to the layout and not to the paint."""
    said = text_element("figure/said", run("Beyond", fill="ink"), x=x, y=30)
    drawing = tool(tmp_path, said, width=200, height=100)
    assert [(each.why, each.whole) for each in drawing.dropped] == [
        (viewing_tool.OFF_THE_PAGE, True)
    ]
    assert drawing.lost == ()


def test_a_text_past_a_side_all_but_a_little_is_cut_and_not_dropped(tmp_path: Path) -> None:
    said = text_element("figure/said", run("Beyond", fill="ink"), x=198, y=30)
    drawing = tool(tmp_path, said, width=200, height=100)
    assert drawing.dropped == ()
    [(why, share)] = [(each.why, each.share) for each in drawing.lost]
    assert why == viewing_tool.CUT
    assert 0.9 < share < 1


def test_a_text_wholly_under_a_later_box_is_covered_with_all_its_ink_and_never_dropped(
    tmp_path: Path,
) -> None:
    said = text_element("figure/said", run("Under it", fill="ink"), y=30)
    over = element("box", "figure/over", x=0, y=0, width=200, height=100, fill="surface")
    drawing = tool(tmp_path, said, over)
    assert drawing.dropped == ()
    assert [(each.why, round(each.share, 2)) for each in drawing.lost] == [
        (viewing_tool.COVERED, 1.0)
    ]


def test_a_text_whose_runs_left_for_two_causes_is_dropped_run_by_run(tmp_path: Path) -> None:
    first = run("One ", fill="no-such-role")
    second = run("two", fill="ink")
    said = text_element("figure/said", first, second, x=190, y=30)
    drawing = tool(tmp_path, said, width=200, height=100)
    assert [(each.text, each.whole, each.why) for each in drawing.dropped] == [
        ("One ", False, viewing_tool.NO_INK),
        ("two", False, viewing_tool.OFF_THE_PAGE),
    ]


# --- what stands round a text (DEC-045 point 1) ------------------------------------------------


def test_a_group_that_clips_what_it_holds_fails_the_read_naming_it(tmp_path: Path) -> None:
    said = text_element("figure/group/said", run("Say it", fill="ink"), x=0, y=0)
    inner = element("group", "figure/group", x=20, y=30, width=50, height=30, children=[said])
    page = drawn_page(inner).replace(
        '<g data-id="figure/group"', '<g clip-path="url(#c)" data-id="figure/group"'
    )
    assert "clip-path" in page
    with pytest.raises(viewing_tool.ToolFailed, match=r"figure/group.*clip-path"):
        viewing_tool.draw(page, 2.0, tmp_path, {})


def test_a_group_that_turns_what_it_holds_fails_the_read_naming_it(tmp_path: Path) -> None:
    said = text_element("figure/group/said", run("Say it", fill="ink"), x=0, y=0)
    inner = element("group", "figure/group", x=20, y=30, width=50, height=30, children=[said])
    page = drawn_page(inner).replace("translate(20,30)", "rotate(10)")
    assert "rotate(10)" in page
    with pytest.raises(viewing_tool.ToolFailed, match=r"figure/group.*rotate"):
        viewing_tool.draw(page, 2.0, tmp_path, {})


def test_the_groups_the_renderer_writes_hold_a_move_and_marks_alone(tmp_path: Path) -> None:
    """The reads follow a group's move alone (DEC-045 point 1), so this fails if the renderer
    comes to write anything else round a text."""
    said = text_element("figure/group/said", run("Say it", fill="ink"), x=0, y=0)
    inner = element("group", "figure/group", x=20, y=30, width=50, height=30, children=[said])
    outer = element("group", "figure/outer", x=5, y=60, width=50, height=30, children=[inner])
    root = ET.fromstring(drawn_page(outer, width=200, height=400))
    groups = [each for each in root.iter() if each.tag == viewing_tool.GROUP]
    assert len(groups) == 3
    assert {name for each in groups for name in each.attrib} <= {
        "data-id",
        "data-component",
        "data-version",
        "transform",
    }
    texts = [each for each in root.iter() if each.tag == viewing_tool.TEXT]
    assert {name for each in texts for name in each.attrib}.isdisjoint(
        {"transform", "clip-path", "mask", "opacity", "filter"}
    )


# --- what a graze and a háček lose (DEC-045 point 1) -------------------------------------------

#: The em, in image pixels, at which a test holds the least graze, a box's edge across the last
#: row of a text's descenders, unnamed at every scale in Source Sans Pro Regular, and the row
#: above it named (DEC-045 point 1).
LEAST_GRAZE_EM = 40
#: The scales the probes drew at: DEC-037's four, and 0.8167, at which a 1920 by 1080 page is
#: drawn 1568 pixels wide (DEC-015 point 5). `scripts/visual_svg_reads.py` draws at them too.
SCALES = (0.5, 0.8167, 1.0, 1.225, 2.0)
#: The ems, in image pixels, the probes' table gives a háček and a graze at (DEC-045).
EMS = (10, 12, 16, 20, 24, 30, 35, 40)
#: Ems at which a háček loses as many pixels as the threshold holds at some scale, or one
#: more: one pixel at 10.2 to 10.7 and two at 14.3, fewer than the threshold's area of the em
#: squared, and one more than the threshold at 14.4, 14.5, 17.6 and 17.7
#: (`scripts/visual_svg_reads.py`).
HACEK_AT_THE_THRESHOLD = (10.2, 10.3, 10.4, 10.5, 10.6, 10.7, 14.3, 14.4, 14.5, 17.6, 17.7)
#: The ems at which a graze's least row holds the threshold's whole pixels at every scale.
ROW_HOLDS_THE_THRESHOLD = (10, 12, 16, 24)
#: The em, in image pixels, of 24 px text on a 1920 page drawn at 0.8167 (DEC-015 point 5).
DECK_TEXT = 19.6
#: The text whose háček a later box covers, and the text whose descenders' foot a later box's
#: edge grazes.
HACEK = "ž"
DESCENDERS = "Typography gypsy"
#: The steps of a graze's edge, each half an image pixel, from three pixels above where the
#: foot of the descenders lies to three below.
GRAZE_STEPS = range(-6, 7)


def háček_box(base: float, size: float) -> dict[str, Any]:
    """A box over a ž's háček, its baseline at `base` and its font `size` px: from the page's
    top down to 0.56 of the font size above the baseline."""
    return {"x": 0, "y": 0, "width": 12 * size, "height": base - 0.56 * size}


def graze_box(step: int, scale: float) -> Callable[[float, float], dict[str, Any]]:
    """A box whose top edge lies `step` half image pixels below 0.2 of the font size under the
    baseline, across the foot of the descenders, drawn at `scale`."""
    return lambda base, size: {
        "x": 0,
        "y": base + 0.2 * size + step / 2 / scale,
        "width": 12 * size,
        "height": 0.5 * size + 10,
    }


def box_over(
    pixels: Sequence[tuple[int, int]], strong: Any, width: float
) -> Callable[[float, float], dict[str, Any]]:
    """A box over `pixels` of `strong`'s swath, a pixel past them on each side, as a plant's
    `over` gives it, on a page `width` px wide. Beside a dot that stands apart from its
    neighbour, that pixel is the empty row or column between them."""
    to_page = width / strong.columns
    to_swath = 2 * strong.reach / strong.rows
    rows = [row for row, _ in pixels]
    columns = [column for _, column in pixels]
    top = strong.top + (min(rows) - 1) * to_swath
    left = (min(columns) - 1) * to_page
    box = {
        "x": left,
        "y": top,
        "width": (max(columns) + 2) * to_page - left,
        "height": strong.top + (max(rows) + 2) * to_swath - top,
    }
    return lambda _baseline, _size: dict(box)


def box_into(
    pixels: Sequence[tuple[int, int]], strong: Any, width: float, side: str, eighths: int
) -> Callable[[float, float], dict[str, Any]]:
    """A box over `pixels` as `box_over` lays one, but for its `side` edge, which lies
    `eighths` eighths of a pixel inside their outermost column or row on that side, as the
    probe's `partial` steps it (`scripts/visual_svg_reads.py`)."""
    to_page = width / strong.columns
    to_swath = 2 * strong.reach / strong.rows
    rows = [row for row, _ in pixels]
    columns = [column for _, column in pixels]
    inside = eighths / 8
    edges = {
        "left": (min(columns) - 1) * to_page,
        "right": (max(columns) + 2) * to_page,
        "top": strong.top + (min(rows) - 1) * to_swath,
        "bottom": strong.top + (max(rows) + 2) * to_swath,
    }
    edges[side] = {
        "left": (min(columns) + inside) * to_page,
        "right": (max(columns) + 1 - inside) * to_page,
        "top": strong.top + (min(rows) + inside) * to_swath,
        "bottom": strong.top + (max(rows) + 1 - inside) * to_swath,
    }[side]
    box = {
        "x": edges["left"],
        "y": edges["top"],
        "width": edges["right"] - edges["left"],
        "height": edges["bottom"] - edges["top"],
    }
    return lambda _baseline, _size: dict(box)


def háček_at(tmp_path: Path, em: float, scale: float) -> list[tuple[str, float]]:
    """The háček of a ž set `em` image pixels high, a later box over it alone."""
    return set_at(tmp_path, HACEK, em, scale, over=háček_box)


def graze_rows(
    tmp_path: Path, em: float, scale: float, monkeypatch: pytest.MonkeyPatch
) -> tuple[Callable[[int], list[str]], dict[int, int], int]:
    """A later box whose top edge steps by half an image pixel across the foot of the
    descenders of "Typography gypsy" set `em` image pixels high: what each step hides of the
    text with nothing unnamed, in image pixels, the causes a step names as it is, and the fewest
    pixels the read names at the text's em as it reads it."""

    def edge(step: int) -> Callable[[float, float], dict[str, Any]]:
        return graze_box(step, scale)

    read: list[Any] = []
    strong = viewing_tool._Page._strong

    def kept(page: Any, *args: Any) -> Any:
        read.append(strong(page, *args))
        return read[-1]

    hides: dict[int, int] = {}
    with monkeypatch.context() as unbound:
        unbound.setattr(viewing_tool, "THRESHOLD", 0.0)
        unbound.setattr(viewing_tool, "FEWEST", 0)
        unbound.setattr(viewing_tool._Page, "_strong", kept)
        for step in GRAZE_STEPS:
            found = set_at(tmp_path, DESCENDERS, em, scale, edge(step))
            share = sum(share for why, share in found if why == viewing_tool.COVERED)
            hides[step] = round(share * read[-1].found)

    def named(step: int) -> list[str]:
        return [why for why, _ in set_at(tmp_path, DESCENDERS, em, scale, edge(step))]

    return named, hides, viewing_tool._least(read[-1].em)


def least_graze(hides: Mapping[int, int]) -> tuple[int, int]:
    """The step that hides the fewest pixels of any that hide some, and how many."""
    fewest = min(hidden for hidden in hides.values() if hidden)
    return next(step for step, hidden in hides.items() if hidden == fewest), fewest


@pytest.mark.parametrize(
    ("em", "fewest"),
    (
        (5, 1),
        (9.9, 1),
        (10, 1),
        (14.1, 1),
        (14.2, 2),
        (14.3, 2),
        (17.3, 2),
        (17.4, 3),
        (19.6, 3),
        (20, 4),
        (40, 16),
    ),
)
def test_the_threshold_is_counted_in_the_whole_pixels_it_holds_and_never_under_one(
    em: float, fewest: int
) -> None:
    """0.01 of the em squared, rounded down to whole pixels, and one at the least (DEC-045
    point 1). Rounded up, a háček's two pixels at an em of 14.3 would fall under it. At 10, 20
    and 40 the threshold falls on a whole pixel, and takes it."""
    assert viewing_tool._least(em) == fewest


@pytest.mark.parametrize("em", (*EMS, *HACEK_AT_THE_THRESHOLD))
@pytest.mark.parametrize("scale", SCALES)
def test_a_háček_under_a_box_is_named_at_every_em_and_scale(
    tmp_path: Path, em: float, scale: float
) -> None:
    """The háček is named wherever it loses a pixel or more, from the floor to 40. At 10.2 to
    10.7 it loses its one pixel at some scales, and at 14.3 two pixels at one, under 0.01 of the
    em squared as read, fewer than the threshold's area but not than its whole pixels."""
    assert [why for why, _ in háček_at(tmp_path, em, scale)] == [viewing_tool.COVERED]


@pytest.mark.parametrize("scale", SCALES)
def test_the_least_graze_at_an_em_of_40_is_named_at_no_scale_and_the_row_above_it_is(
    tmp_path: Path, scale: float, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A text of descenders set at 40 image pixels in Source Sans Pro Regular, a later box whose
    top edge steps across their foot. resvg hides whole rows, so the box hides the last row,
    then more: the last row, the least graze, stays unnamed, and the row above it is named."""
    named, hides, _ = graze_rows(tmp_path, LEAST_GRAZE_EM, scale, monkeypatch)
    levels = sorted({hidden for hidden in hides.values() if hidden})
    graze, more = levels[0], levels[1]
    for step, hidden in hides.items():
        if hidden == graze:
            assert named(step) == [], step
        if hidden == more:
            assert named(step) == [viewing_tool.COVERED], step


@pytest.mark.parametrize("scale", SCALES)
@pytest.mark.parametrize("em", ROW_HOLDS_THE_THRESHOLD)
def test_a_graze_whose_least_row_holds_the_threshold_at_every_scale_is_named(
    tmp_path: Path, em: float, scale: float, monkeypatch: pytest.MonkeyPatch
) -> None:
    """At these ems a single row of the descenders' foot hides 0.0156 to 0.13 of the em squared
    at every scale, as much as a háček and more than the threshold, so the least graze is
    named."""
    named, hides, least = graze_rows(tmp_path, em, scale, monkeypatch)
    step, fewest = least_graze(hides)
    assert fewest >= least
    assert named(step) == [viewing_tool.COVERED]


@pytest.mark.parametrize("scale", SCALES)
def test_a_descenders_foot_a_box_touches_in_24_px_text_on_a_1920_page_is_named_at_every_scale(
    tmp_path: Path, scale: float, monkeypatch: pytest.MonkeyPatch
) -> None:
    """24 px text on a 1920 page drawn at 0.8167 is set at an em of 19.6 image pixels. There
    the least row of the descenders' foot holds 17 to 20 pixels at each scale, more than the
    threshold's 3, so the least graze is named (DEC-045 point 1)."""
    named, hides, least = graze_rows(tmp_path, DECK_TEXT, scale, monkeypatch)
    step, fewest = least_graze(hides)
    assert fewest >= least
    assert named(step) == [viewing_tool.COVERED]


def test_at_an_em_of_20_a_graze_is_spared_at_some_scales_and_named_at_others(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """At an em of 20 image pixels the least row of the descenders' foot holds 2 pixels at some
    scales, fewer than the threshold's 4, and more than 20 at others. So whether a graze is
    named turns on where its last row falls among the pixels, which the text's size does not
    tell (DEC-045 point 1). At each scale the least graze is named where its row holds the
    threshold's whole pixels, and spared where it holds fewer."""
    spared: list[bool] = []
    for scale in SCALES:
        named, hides, least = graze_rows(tmp_path, 20, scale, monkeypatch)
        step, fewest = least_graze(hides)
        assert named(step) == ([viewing_tool.COVERED] if fewest >= least else []), scale
        spared.append(fewest < least)
    assert any(spared)
    assert not all(spared)


#: Runs that meet on one line, each a span of its own: a word split in two, pairs a face
#: kerns, a decimal point between its figures, and quotes round a word.
MEETING_RUNS = (
    ("Typo", "graphy"),
    ("T", "y"),
    ("A", "V"),
    ("f", "j"),
    ("3", ".", "5"),
    ("“", "Jo", "”"),
)


@pytest.mark.parametrize("em", (10, 11, 12, 16, 40))
@pytest.mark.parametrize("scale", SCALES)
def test_runs_that_meet_on_one_line_hide_none_of_each_other(
    tmp_path: Path, em: float, scale: float
) -> None:
    """Up to an em of about 14.1 a cause that hides a single pixel is named, and at any em a
    cause that takes an island of a span's ink (DEC-045 point 1). A run drawn after
    another on its line hides a pixel of the other's ink only where its letters cover all of
    that pixel, which runs that meet do not."""
    for runs in MEETING_RUNS:
        assert set_at(tmp_path, runs, em, scale) == [], runs


def found_of(
    tmp_path: Path,
    words: Sequence[str],
    em: float,
    scale: float,
    wanted: str,
    *,
    moved: tuple[float, float] = (0.0, 0.0),
    over: Callable[[float, float], dict[str, Any]] | None = None,
) -> tuple[Any, float, Any]:
    """What the reads find of the run `wanted` of `words`, set as `plant` sets them, its
    strong ink and its ink; the page's width in px; and the page drawn."""
    found: list[tuple[Any, float]] = []
    strong = viewing_tool._Page._strong

    def kept(page: Any, text: Any, line: Any, index: int, *rest: Any) -> Any:
        read = strong(page, text, line, index, *rest)
        if line[index].text == wanted:
            found.append((read, page.width))
        return read

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(viewing_tool._Page, "_strong", kept)
        drawing = plant(tmp_path, words, em, scale, over, moved=moved)
    [(read, width)] = found
    return read, width, drawing


def on_the_page(strong: Any) -> list[tuple[int, int]]:
    """The pixels of a span's ink that lie on the page."""
    return [pixel for pixel in strong.ink if pixel not in strong.beyond]


def dot_rows(strong: Any) -> list[tuple[int, int]]:
    """The pixels of a span's ink above the first row of its ink that holds none: the dot of
    an ż, or a háček, where it stands apart from its letter."""
    rows = {row for row, _ in strong.ink}
    gap = next(row for row in range(min(rows), max(rows)) if row not in rows)
    return [pixel for pixel in strong.ink if pixel[0] < gap]


def test_an_island_is_ink_at_a_level_each_pixel_meeting_another_by_a_side_or_a_corner() -> None:
    """A stroke of strong ink, a speck that meets it by a corner alone, and a faint pixel that
    meets the stroke by a side: at strong ink the speck is part of the stroke's island, and the
    faint pixel at 159 is an island of its own, which at 191 meets the stroke (DEC-045 point
    1)."""
    stroke = {(row, 0): 0 for row in range(4)}
    speck = {(4, 1): 100}
    faint = {(0, 2): 150, (0, 3): 150}
    near = {(0, 1): 180}
    ink = {**stroke, **speck, **faint, **near}
    assert not islands.takes_an_island(ink, speck)
    assert islands.takes_an_island(ink, [*stroke, *speck])
    assert islands.takes_an_island(ink, faint)
    assert not islands.takes_an_island(ink, [(0, 2)])
    assert not islands.takes_an_island({(0, 0): 230}, [(0, 0)])
    assert not islands.takes_an_island(ink, [])
    assert islands.LEVELS == (islands.STRONG, 159, 191)


def test_a_cover_takes_an_island_it_hides_in_part_and_leaves_showing_at_its_level_nowhere() -> None:
    """Where the page drawn whole shows how much of each pixel's ink is left, a cause takes an
    island where it hides some of it wholly and leaves none of it showing at the island's level:
    a dot whose last column a box's edge leaves at under half its ink. A dot that still shows a
    pixel at its level, under a translucent box that hides no pixel wholly, or a pixel past the
    page's edge, which the cover leaves to the cut, is not taken (DEC-045 point 1)."""
    dot = {(0, 0): 0, (0, 1): 0, (1, 0): 0, (1, 1): 0}
    stroke = {(row, 4): 0 for row in range(4)}
    ink = {**dot, **stroke}
    shown = {pixel: islands.ALL for pixel in ink}
    edge = {**shown, (0, 1): 0, (1, 1): 0, (0, 0): 100, (1, 0): 100}
    assert islands.takes_an_island(ink, [(0, 1), (1, 1)], edge)
    assert not islands.takes_an_island(ink, [(0, 1), (1, 1)])
    kept = {**edge, (1, 0): 160}
    assert not islands.takes_an_island(ink, [(0, 1), (1, 1)], kept)
    veiled = {**shown, **dict.fromkeys(dot, 51)}
    assert not islands.takes_an_island(ink, [], veiled)
    past = {pixel: shows for pixel, shows in edge.items() if pixel != (1, 0)}
    assert not islands.takes_an_island(ink, [(0, 1), (1, 1)], past)
    assert islands.takes_an_island(ink, list(dot), {**shown, **dict.fromkeys(dot, 0)})
    assert islands.shows_at(160, viewing_tool.STRONG)
    assert not islands.shows_at(100, viewing_tool.STRONG)
    assert islands.shows_at(100, 159)


#: Dots a reader needs, each hidden whole under a later box at a scale of 1: the runs of its
#: line, the run that holds it, and the em it is set at. The full stop holds as many strong
#: pixels as the threshold at 20, the point and the dot of ż fewer at 22.5 and at 40, and the
#: point at 11.1 none (`scripts/visual_svg_reads.py cover`).
HIDDEN_DOTS = (
    (("end", "."), ".", 20),
    (("3", ".", "5"), ".", 22.5),
    (("ż",), "ż", 40),
    (("3", ".", "5"), ".", 11.1),
)


@pytest.mark.parametrize(("runs", "dot", "em"), HIDDEN_DOTS)
def test_a_dot_hidden_whole_is_named_covered_as_an_island_of_its_span_s_ink(
    tmp_path: Path, runs: tuple[str, ...], dot: str, em: float
) -> None:
    """A box over all of a dot's ink hides all of an island of it, and so takes it: the cover
    is named, whatever the threshold holds, with `island` (DEC-045 point 1). The share is of
    the span's strong ink: all of it for a full stop or a point that is a run of its own, and a
    part for the dot of ż. A point with no strong ink loses all its ink, at the lightest level
    read (point 2)."""
    strong, width, _ = found_of(tmp_path, runs, em, 1.0, dot)
    pixels = dot_rows(strong) if dot == "ż" else on_the_page(strong)
    drawing = plant(tmp_path, runs, em, 1.0, box_over(pixels, strong, width))
    assert [(each.text, each.why, each.island) for each in drawing.lost] == [
        (dot, viewing_tool.COVERED, True)
    ]
    [lost] = drawing.lost
    hidden = sum(strong.ink[pixel] <= viewing_tool.STRONG for pixel in pixels)
    assert hidden <= viewing_tool._least(strong.em)
    assert lost.share == (hidden / strong.found if strong.found else 1.0)
    assert drawing.dropped == ()


def shown_under(
    tmp_path: Path,
    runs: tuple[str, ...],
    em: float,
    dot: str,
    over: Callable[[float, float], dict[str, Any]],
) -> tuple[Any, dict[tuple[int, int], int]]:
    """The page of `runs` at a scale of 1 under the box `over` gives, and how much of each
    pixel of the run `dot`'s ink the cover read finds the page drawn whole still shows."""
    found: list[dict[tuple[int, int], int]] = []
    shown = viewing_tool._Page._shown

    def kept(page: Any, span: Any, strong: Any) -> dict[tuple[int, int], int]:
        shows = shown(page, span, strong)
        if span.text == dot:
            found.append(shows)
        return shows

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(viewing_tool._Page, "_shown", kept)
        drawing = plant(tmp_path, runs, em, 1.0, over)
    [shows] = found
    return drawing, shows


#: A dot under a box a pixel past it on each side but one, whose edge on that side lies four
#: eighths of a pixel inside the dot's outermost column or row: the runs of its line, the run
#: that holds it, its em, and the side (`scripts/visual_svg_reads.py partial`).
EDGE_IN_A_DOT = (
    (("end", "."), ".", 20, "left"),
    (("3", ".", "5"), ".", 22.5, "bottom"),
)


@pytest.mark.parametrize(("runs", "dot", "em", "side"), EDGE_IN_A_DOT)
def test_a_box_whose_edge_leaves_a_dot_a_faint_line_takes_the_dot_and_is_named(
    tmp_path: Path, runs: tuple[str, ...], dot: str, em: float, side: str
) -> None:
    """The box hides part of the dot wholly, and leaves its outermost column or row at under
    half its ink, so none of it still shows as strong ink. It hides fewer strong pixels than
    the threshold and not all of the dot, yet takes the dot's island, so the cover is named with
    `island` (DEC-045 point 1)."""
    strong, width, _ = found_of(tmp_path, runs, em, 1.0, dot)
    pixels = on_the_page(strong)
    drawing, shows = shown_under(tmp_path, runs, em, dot, box_into(pixels, strong, width, side, 4))
    hidden = [pixel for pixel, shown in shows.items() if not shown]
    assert sum(strong.ink[pixel] <= viewing_tool.STRONG for pixel in hidden) < viewing_tool._least(
        strong.em
    )
    assert not islands.takes_an_island(strong.ink, hidden)
    assert [(each.text, each.why, each.island) for each in drawing.lost] == [
        (dot, viewing_tool.COVERED, True)
    ]


@pytest.mark.parametrize(("runs", "dot", "em", "side"), EDGE_IN_A_DOT)
def test_a_box_whose_edge_leaves_a_dot_showing_at_its_level_is_left_unnamed(
    tmp_path: Path, runs: tuple[str, ...], dot: str, em: float, side: str
) -> None:
    """With its edge seven eighths inside the dot's outermost column or row, the box leaves
    that column or row showing as strong ink: the dot is not taken, and the box hides fewer
    strong pixels than the threshold, so nothing is named (DEC-045 point 1)."""
    strong, width, _ = found_of(tmp_path, runs, em, 1.0, dot)
    pixels = on_the_page(strong)
    drawing, shows = shown_under(tmp_path, runs, em, dot, box_into(pixels, strong, width, side, 7))
    assert any(
        islands.shows_at(shows[pixel], viewing_tool.STRONG)
        for pixel in pixels
        if strong.ink[pixel] <= viewing_tool.STRONG
    )
    assert drawing.lost == ()


@pytest.mark.parametrize("opacity", (0.8, 0.5))
def test_a_dot_under_a_translucent_box_is_not_named(
    tmp_path: Path, opacity: float, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A box of the ground's colour, less than opaque, over all of a dot fades it below strong
    ink and hides none of it wholly. Covered means hidden, so it takes no island and is not
    named: whether the dot reads through it is the reviewer's (DEC-045 point 1)."""
    runs, dot, em = ("end", "."), ".", 20
    strong, width, _ = found_of(tmp_path, runs, em, 1.0, dot)
    box = box_over(on_the_page(strong), strong, width)(0.0, 0.0)
    monkeypatch.setitem(COLOURS, "veil", {"components": [1, 1, 1], "alpha": opacity})
    children, sizes = plant_of(runs, em, 1.0)
    children.append(element("box", "figure/over", fill="veil", **box))
    drawing = tool_at(tmp_path, 1.0, *children, **sizes)
    assert drawing.lost == ()


@pytest.mark.parametrize(
    ("em", "scale"), ((15.3, 0.8167), *((LEAST_GRAZE_EM, scale) for scale in SCALES))
)
def test_a_graze_the_threshold_leaves_takes_no_island_and_is_left_unnamed(
    tmp_path: Path, em: float, scale: float, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A box's edge across the foot of the descenders hides part of a stroke, never all of an
    island: a strong pixel at a descender's foot that meets the rest of its letter by a corner
    alone is part of the letter's island. So each step of the edge that hides fewer pixels than
    the threshold is left unnamed: at 15.3, at the scale where a step hides that pixel alone,
    which islands joined by sides alone would name, and at an em of 40 (DEC-045 point 1)."""
    named, hides, least = graze_rows(tmp_path, em, scale, monkeypatch)
    spared = [step for step, hidden in hides.items() if 0 < hidden < least]
    assert spared
    for step in spared:
        assert named(step) == [], step


@pytest.mark.parametrize("alpha", (0.4, 0.2))
def test_a_graze_of_a_text_in_a_translucent_colour_takes_no_island_and_is_left_unnamed(
    tmp_path: Path, alpha: float, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A text in a colour less than opaque, which its span takes from the text, under a later
    box over one strong pixel near the middle of its letters and a pixel past it on each side.
    The box hides fewer pixels than the threshold. The page drawn whole changes the span's
    letters between two opaque colours, whatever the alpha of its paint, so the rest of the
    letter still shows as strong ink: the box takes no island and is left unnamed (DEC-045
    point 1)."""
    words, em = "Hello", 40
    monkeypatch.setitem(COLOURS, "ink", {"components": [0, 0, 0], "alpha": alpha})
    strong, width, _ = found_of(tmp_path, words, em, 1.0, words)
    pixels = sorted(
        pixel for pixel in on_the_page(strong) if strong.ink[pixel] <= viewing_tool.STRONG
    )
    over = box_over([pixels[len(pixels) // 2]], strong, width)
    drawing, shows = shown_under(tmp_path, (words,), em, words, over)
    hidden = [pixel for pixel, shown in shows.items() if not shown]
    lost = sum(strong.ink[pixel] <= viewing_tool.STRONG for pixel in hidden)
    assert 0 < lost < viewing_tool._least(strong.em)
    assert drawing.lost == ()


@pytest.mark.parametrize(("em", "scale"), ((40, 1.0), (20, 1.225), (12.5, 1.0)))
def test_the_dot_of_a_ż_past_the_page_s_top_is_named_cut_as_an_island(
    tmp_path: Path, em: float, scale: float
) -> None:
    """The text is moved up by whole rows of its swath until the page's top lies on the empty
    row between the dot and its letter. The dot is cut whole, so the cut is named with
    `island`, though the strong ink past the edge is fewer pixels than the threshold, and at
    12.5 none (DEC-045 point 1)."""
    strong, _, _ = found_of(tmp_path, ("ż",), em, scale, "ż")
    last = max(row for row, _ in dot_rows(strong))
    moved = (0.0, -(strong.top + (last + 1) * 2 * strong.reach / strong.rows))
    cut, _, drawing = found_of(tmp_path, ("ż",), em, scale, "ż", moved=moved)
    assert set(dot_rows(cut)) == set(cut.beyond)
    assert cut.past < viewing_tool._least(cut.em)
    assert [(each.why, each.island) for each in drawing.lost] == [(viewing_tool.CUT, True)]
    assert drawing.dropped == ()


def test_a_full_stop_of_its_own_past_the_page_s_side_lies_off_the_page(tmp_path: Path) -> None:
    """The text is moved across by whole columns until the page's right edge lies on the empty
    column between the word and its full stop, a run of its own: the full stop's ink lies
    wholly past the edge, so it is dropped as off the page, and the word is whole (DEC-045
    point 2)."""
    runs = ("end", ".")
    strong, width, _ = found_of(tmp_path, runs, 20, 1.0, ".")
    first = min(column for _, column in on_the_page(strong))
    moved = ((strong.columns - first) * width / strong.columns, 0.0)
    drawing = plant(tmp_path, runs, 20, 1.0, moved=moved)
    assert [(each.text, each.whole, each.why) for each in drawing.dropped] == [
        (".", False, viewing_tool.OFF_THE_PAGE)
    ]
    assert drawing.lost == ()


# --- what a run draws (DEC-015 point 5) ---------------------------------------------------------


@pytest.fixture
def flow(tmp_path: Path) -> Path:
    """The piece `flow` in both colour schemes, with its picture."""
    root = drawing_project(tmp_path)
    write_picture(root, framing)
    return root


def starter_project(tmp_path: Path) -> Path:
    """The starter's release 1.0.0, the test brand and notation, and the starter's reference
    pieces, which hold more than one page, two languages and four keys."""
    root = project(tmp_path)
    copy_library(root, RELEASED_FOUNDATIONS, "foundations", "1.0.0")
    copy_library(root, RELEASES / "starter" / "1.0.0", "starter", "1.0.0")
    copy_library(root, TEST_BRAND, "test-brand", "1.0.0")
    copy_library(root, TEST_NOTATION, "test-notation", "1.0.0")
    write_list(
        root,
        {
            "foundations": {"source": {"kind": "shipped"}, "versions": UNRELEASED},
            "starter": {"source": {"kind": "shipped"}, "versions": UNRELEASED},
            "test-brand": {"source": {"kind": "project"}, "versions": UNRELEASED},
            "test-notation": {"source": {"kind": "project"}, "versions": UNRELEASED},
        },
    )
    shutil.copytree(PIECES, root / "visual" / "pieces")
    return root


def test_by_default_it_draws_every_page_in_the_source_language_and_the_first_key(
    tmp_path: Path,
) -> None:
    root = starter_project(tmp_path)
    shown = run_look(root, "tag")
    assert shown.returncode == 0, shown.stderr
    report = report_of(root, "tag")
    assert [image["image"] for image in report["images"]] == [
        "tag.en.default.1.png",
        "tag.en.default.2.png",
    ]
    assert report["dropped"] == [] and report["losses"] == []
    assert shown.stdout.splitlines()[0] == f"look: 2 image(s) in {viewing.FOLDER}/tag/"


def test_it_draws_one_image_for_each_page_language_and_key_and_none_is_blank(
    tmp_path: Path,
) -> None:
    root = starter_project(tmp_path)
    shown = run_look(root, "tag", "--every-language", "--every-key")
    assert shown.returncode == 0, shown.stderr
    images = sorted(folder_of(root, "tag").glob("*.png"))
    assert len(images) == 2 * 2 * 4
    assert all(path.read_bytes() != blank(path.read_bytes()) for path in images)
    assert report_of(root, "tag")["dropped"] == []


def test_the_caller_picks_pages_languages_and_keys(tmp_path: Path) -> None:
    root = starter_project(tmp_path)
    shown = run_look(root, "panels", "--page", "2", "--language", "de", "--key", "contrast.high")
    assert shown.returncode == 0, shown.stderr
    assert [image["image"] for image in report_of(root, "panels")["images"]] == [
        "panels.de.contrast.high.2.png"
    ]
    trace = "deck/slides[nested]"
    assert run_look(root, "panels", "--page", trace).returncode == 0
    assert [image["number"] for image in report_of(root, "panels")["images"]] == [3]


@pytest.mark.parametrize(
    ("args", "said"),
    [
        pytest.param(
            ["--language", "fr"], "`tag` has no language `fr`: it has `en`, `de`", id="language"
        ),
        pytest.param(
            ["--key", "contrast.low"],
            "`tag` has no key `contrast.low`: it has `default`,",
            id="key",
        ),
        pytest.param(
            ["--page", "3"], "`tag` has no page `3` in `en`: it has 2, from 1", id="number"
        ),
        pytest.param(["--page", "0"], "`tag` has no page `0` in `en`", id="zero"),
        pytest.param(["--page", "no/such"], "`tag` has no page `no/such` in `en`", id="trace"),
    ],
)
def test_what_the_piece_does_not_have_is_refused_with_nothing_written(
    tmp_path: Path, args: list[str], said: str
) -> None:
    root = starter_project(tmp_path)
    before = written(root)
    shown = run_look(root, "tag", *args)
    assert shown.returncode == 1
    assert said in shown.stderr
    assert written(root) == before


def test_a_piece_on_a_size_axis_has_an_image_for_each_key_drawn_from_its_size_s_scene(
    tmp_path: Path,
) -> None:
    dark = "colour-scheme.dark"
    keys = ["default", dark, PHONE, f"{dark}+{PHONE}"]
    root = on_devices(
        tmp_path, modes={"colour-scheme": ["light", "dark"], "device": ["desktop", "phone"]}
    )
    shown = run_look(root, PIECE, "--every-key")
    assert shown.returncode == 0, shown.stderr
    images = report_of(root)["images"]
    assert [image["key"] for image in images] == keys
    shapes = {
        image["key"]: image["pixels"]["width"] / image["pixels"]["height"] for image in images
    }
    assert shapes["default"] == shapes[dark] > shapes[PHONE] == shapes[f"{dark}+{PHONE}"]

    def frames(key: str) -> list[Any]:
        data = (folder_of(root) / f"flow.en.{key}.frames.json").read_text(encoding="utf-8")
        return json.loads(data)["elements"]

    assert frames(PHONE) == frames(f"{dark}+{PHONE}") != frames("default")
    assert run_look(root, PIECE, "--key", PHONE).returncode == 0
    assert [image["key"] for image in report_of(root)["images"]] == [PHONE]


def test_the_default_key_is_the_combination_of_defaults_wherever_the_piece_names_it(
    tmp_path: Path,
) -> None:
    root = drawing_project(tmp_path, modes={"colour-scheme": ["dark", "light"]})
    write_picture(root, framing)
    assert run_look(root, PIECE).returncode == 0
    assert [image["key"] for image in report_of(root)["images"]] == ["default"]


def test_a_piece_of_no_default_takes_the_first_key_in_variant_order(tmp_path: Path) -> None:
    root = drawing_project(tmp_path, modes={"colour-scheme": ["dark"]})
    write_picture(root, framing)
    assert run_look(root, PIECE).returncode == 0
    assert [image["key"] for image in report_of(root)["images"]] == ["colour-scheme.dark"]


def long_edge(page: Mapping[str, Any]) -> int:
    """How many pixels the long edge of `page`'s image takes through the SVG renderer."""
    edge = max(float(page["width"]), float(page["height"]))
    return viewing.pixels(edge, viewing.page_scale(page))


def text_page(width: float, height: float, size: float) -> dict[str, Any]:
    """A page of `width` by `height` px whose smallest text is `size` px."""
    small = {"paragraphs": [[{"font-size": size}]]}
    return {"width": width, "height": height, "children": [small]}


def test_the_scale_rises_where_a_page_s_smallest_text_would_land_under_what_reads() -> None:
    """A page so drawn past the long edge is drawn in bands, or as wide as it allows."""
    assert long_edge(text_page(1280, 640, 16)) == 1568
    assert long_edge({"width": 300, "height": 200}) == 1568
    assert viewing.scale(text_page(390, 5000, 16)) == viewing.SMALLEST_TEXT / 16
    assert viewing.page_scale(text_page(390, 5000, 16)) == viewing.SMALLEST_TEXT / 16


def test_a_large_page_with_no_text_takes_the_long_edge_of_every_page() -> None:
    assert long_edge({"width": 1920, "height": 1080}) == 1568
    assert long_edge({"width": 700, "height": 300}) == 1568


# --- what lies beside the images ----------------------------------------------------------------


def test_beside_each_image_lie_its_frames_with_their_trace_ids_and_the_lock(flow: Path) -> None:
    assert run_look(flow, PIECE).returncode == 0
    names = sorted(path.name for path in folder_of(flow).iterdir())
    assert names == ["flow.en.default.frames.json", "flow.en.default.png", viewing.REPORT]
    frames = json.loads((folder_of(flow) / names[0]).read_text(encoding="utf-8"))
    assert frames["image"] == "flow.en.default.png"
    assert frames["lock"] == {"foundations": "1.0.0", "test-brand": "1.0.0", "tests": "1.0.0"}
    assert frames["page"] == "figure"
    traces = [entry["id"] for entry in frames["elements"]]
    assert traces[0] == "figure"
    assert "figure/body/steps[plan]/head" in traces


def test_a_frame_lies_in_the_image_s_pixels_through_every_group_above_it() -> None:
    inner = element("box", "page/group/box", x=10, y=20, width=30, height=40)
    group = element("group", "page/group", x=100, y=50, width=60, height=70, children=[inner])
    page = element("group", "page", x=999, y=999, width=200, height=100, children=[group])
    shown = viewing.frames(page, 400, 200)
    assert shown == [
        {"id": "page", "type": "group", "x": 0.0, "y": 0.0, "width": 400.0, "height": 200.0},
        {
            "id": "page/group",
            "type": "group",
            "x": 200.0,
            "y": 100.0,
            "width": 120.0,
            "height": 140.0,
        },
        {
            "id": "page/group/box",
            "type": "box",
            "x": 220.0,
            "y": 140.0,
            "width": 60.0,
            "height": 80.0,
        },
    ]


@pytest.mark.parametrize(
    ("box", "ground"),
    [
        pytest.param(
            {"x": 0, "y": 0, "width": 200, "height": 100, "fill": "surface"}, True, id="full"
        ),
        pytest.param(
            {"x": 0, "y": 0, "width": 199, "height": 100, "fill": "surface"}, False, id="short"
        ),
        pytest.param(
            {"x": 0, "y": 0, "width": 200, "height": 100, "fill": "shade"}, False, id="clear"
        ),
        pytest.param({"x": 0, "y": 0, "width": 200, "height": 100}, False, id="unpainted"),
        pytest.param(
            {"x": 0, "y": 0, "width": 200, "height": 100, "fill": "no-such"}, False, id="lost"
        ),
    ],
)
def test_a_page_s_ground_is_an_opaque_box_over_its_whole_frame(
    box: Mapping[str, Any], ground: bool
) -> None:
    page = element("group", "page", width=200, height=100, children=[element("box", "b", **box)])
    assert viewing.draws_ground(page, COLOURS) is ground


def test_the_report_says_which_page_lies_on_white(flow: Path) -> None:
    assert run_look(flow, PIECE).returncode == 0
    [image] = report_of(flow)["images"]
    assert image["on-white"] is False
    on_white(flow)
    shown = run_look(flow, PIECE)
    assert shown.returncode == 0, shown.stderr
    [image] = report_of(flow)["images"]
    assert image["on-white"] is True
    assert "on white: figure (en, default) draws no ground of its own" in shown.stdout.splitlines()


def test_the_report_names_the_lock_the_renderer_and_the_tool(flow: Path) -> None:
    shown = run_look(flow, PIECE)
    assert shown.returncode == 0, shown.stderr
    report = report_of(flow)
    assert report["lock"] == {"foundations": "1.0.0", "test-brand": "1.0.0", "tests": "1.0.0"}
    assert report["renderer"] == {"name": "svg", "version": svg.VERSION}
    assert report["tool"] == viewing_tool.TOOL
    assert report["tool"]["name"] == "resvg"
    assert f"renderer: svg {svg.VERSION}" in shown.stdout.splitlines()


def test_a_run_replaces_what_an_earlier_run_left_for_the_piece(flow: Path) -> None:
    assert run_look(flow, PIECE, "--key", "colour-scheme.dark").returncode == 0
    assert (folder_of(flow) / "flow.en.colour-scheme.dark.png").is_file()
    (folder_of(flow) / "left-by-a-person.txt").write_text("gone", encoding="utf-8")
    assert run_look(flow, PIECE).returncode == 0
    assert sorted(path.name for path in folder_of(flow).iterdir()) == [
        "flow.en.default.frames.json",
        "flow.en.default.png",
        viewing.REPORT,
    ]


def test_it_moves_no_lock_and_writes_nothing_outside_its_folder(flow: Path) -> None:
    before = written(flow)
    assert run_look(flow, PIECE).returncode == 0
    after = written(flow)
    made = {name: data for name, data in after.items() if name not in before}
    assert all(name.startswith(f"{viewing.FOLDER}/{PIECE}/") for name in made)
    assert {name: after[name] for name in before} == before


def test_the_faces_are_gone_when_the_run_ends(flow: Path) -> None:
    assert run_look(flow, PIECE).returncode == 0
    assert [path.name for path in (flow / viewing.FOLDER).parent.iterdir()] == ["look"]


def test_a_folder_reached_through_a_link_is_refused(flow: Path, tmp_path: Path) -> None:
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (flow / viewing.FOLDER).parent.mkdir(parents=True)
    (flow / viewing.FOLDER).symlink_to(elsewhere)
    shown = run_look(flow, PIECE)
    assert shown.returncode == 1
    assert "is reached through the link" in shown.stderr
    assert list(elsewhere.iterdir()) == []


# --- what the report holds (DEC-015 point 3) ----------------------------------------------------


def test_a_real_text_with_no_colour_is_a_loss_and_a_text_dropped_both_named(tmp_path: Path) -> None:
    root = parts_project(tmp_path, warning=True)
    shown = run_look(root, "tags")
    assert shown.returncode == 0, shown.stderr
    report = report_of(root, "tags")
    place = {"language": "en", "key": "default", "page": "figure"}
    assert report["dropped"] == [
        {
            **place,
            "element": "figure/body/label",
            "text": "Ready",
            "why": viewing_tool.NO_INK,
            "whole": True,
        }
    ]
    assert report["losses"] == [
        {
            **place,
            "plugin": "svg",
            "what": "figure/body/label",
            "did": "left-out",
            "why": "the brand gives the role `test-parts.warning` of its fill no colour in "
            "`default`",
            "accepted": False,
        }
    ]
    assert (
        "dropped: figure (en, default): the tool drew nothing of the text `figure/body/label`: "
        "'Ready'"
    ) in shown.stdout.splitlines()
    assert any(
        each.startswith("loss: figure (en, default): ") for each in shown.stdout.splitlines()
    )


def test_through_the_svg_renderer_the_report_no_longer_says_cover_and_cut_were_not_read(
    tmp_path: Path,
) -> None:
    """The tool reads cover and cut, so a report that names neither holds none (DEC-045)."""
    root = parts_project(tmp_path)
    shown = run_look(root, "tags")
    assert shown.returncode == 0, shown.stderr
    report = report_of(root, "tags")
    assert report["dropped"] == []
    assert "dropped-not-read" not in report
    assert not any(
        "is not named: read the images for it" in each for each in shown.stdout.splitlines()
    )


def test_through_the_svg_renderer_the_report_names_each_text_cut_or_covered_with_its_share(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """What the tool says a page shows in part is an entry of `dropped`, as a browser's is,
    and the command prints it in words for its cause. An entry whose cause takes an island of
    the span's ink says so in `island`, whatever its share, and another holds no such key. A
    faint mark lost whole loses all its ink (DEC-045 point 2)."""
    root = parts_project(tmp_path)
    real = viewing.viewing_tool.draw
    label = "figure/body/label"

    def drawing(*given: Any, **regions: Any) -> Any:
        drawn = real(*given, **regions)
        found = (
            viewing_tool.Lost(label, "Go", viewing_tool.CUT, 0.36322869955),
            viewing_tool.Lost(label, "Go", viewing_tool.COVERED, 0.5),
            viewing_tool.Lost(label, "end.", viewing_tool.COVERED, 0.004, True),
            viewing_tool.Lost(label, ".", viewing_tool.COVERED, 1.0, True),
        )
        return viewing_tool.Drawing(drawn.images, drawn.dropped, found)

    monkeypatch.setattr(viewing.viewing_tool, "draw", drawing)
    shown = run_look(root, "tags")
    assert shown.returncode == 0, shown.stderr
    place = {"language": "en", "key": "default", "page": "figure", "element": label}
    assert report_of(root, "tags")["dropped"] == [
        {**place, "text": "Go", "why": "cut", "share": 0.363},
        {**place, "text": "Go", "why": "covered", "share": 0.5},
        {**place, "text": "end.", "why": "covered", "share": 0.004, "island": True},
        {**place, "text": ".", "why": "covered", "share": 1.0, "island": True},
    ]
    lines = shown.stdout.splitlines()
    span = f"dropped: figure (en, default): a span of the text `{label}`"
    assert f"{span} is cut by its page's edge, past which 36% of its ink lies: 'Go'" in lines
    assert f"{span} is covered by a part over it, which hides 50% of its ink: 'Go'" in lines
    assert (
        f"{span} is covered by a part over it, which hides under 1% of its ink"
        " (one island of it gone, such as a dot): 'end.'"
    ) in lines
    assert (
        f"{span} is covered by a part over it, which hides 100% of its ink"
        " (one island of it gone, such as a dot): '.'"
    ) in lines


def test_a_loss_the_piece_accepted_is_still_reported_and_so_is_the_text_it_drops(
    tmp_path: Path,
) -> None:
    root = parts_project(tmp_path, warning=True)
    piece = root / "visual" / "pieces" / "tags" / "piece.yaml"
    accepted = "accept-losses:\n  - plugin: svg\n    what: figure/body/label\n    reason: Known.\n"
    piece.write_text(piece.read_text(encoding="utf-8") + accepted, encoding="utf-8")
    shown = run_look(root, "tags")
    assert shown.returncode == 0, shown.stderr
    report = report_of(root, "tags")
    assert [each["accepted"] for each in report["losses"]] == [True]
    assert [each["element"] for each in report["dropped"]] == ["figure/body/label"]
    assert any(
        each.startswith("loss (accepted): figure (en, default): ")
        for each in shown.stdout.splitlines()
    )


def test_a_picture_with_no_variant_for_the_key_is_a_loss_and_the_run_goes_on(flow: Path) -> None:
    """The step runs no producer, and draws what it has: an export refuses this."""
    record = flow / PIECE_FOLDER / "produced" / OUTPUT / "record.yaml"
    held = YAML(typ="safe").load(record)
    del held["combinations"]["default"]
    record.write_text(yaml_text(held), encoding="utf-8")
    shown = run_look(flow, PIECE)
    assert shown.returncode == 0, shown.stderr
    [loss] = report_of(flow)["losses"]
    assert loss["what"] == "figure/body/steps[note]/pictures[square]/image"
    assert loss["did"] == "left-out"


def test_a_page_with_no_size_refuses_naming_the_check_with_nothing_written(tmp_path: Path) -> None:
    """A picture never produced leaves the scene no height, and `check` says why."""
    root = drawing_project(tmp_path)
    before = written(root)
    shown = run_look(root, PIECE)
    assert shown.returncode == 1
    assert shown.stderr == (
        "error: the tool cannot draw page figure of `flow`: the page measures 960 by 0 px. "
        "`pkit visual check flow` names what the piece still owes\n"
    )
    assert written(root) == before


def test_a_final_page_with_no_size_refuses_naming_no_check(tmp_path: Path) -> None:
    """The check reads no picture of a final piece, so it could name nothing the piece owes."""
    root = drawing_project(tmp_path, state="final")
    before = written(root)
    shown = run_look(root, PIECE)
    assert shown.returncode == 1
    assert shown.stderr == (
        "error: the tool cannot draw page figure of `flow`: the page measures 960 by 0 px\n"
    )
    assert written(root) == before


def test_a_page_of_no_width_and_no_height_refuses_naming_the_check(tmp_path: Path) -> None:
    """A page 0 by 0 reaches the same refusal, not a division by its long edge."""
    root = drawing_project(tmp_path)
    tokens = root / BRAND_TOKENS
    data = json.loads(tokens.read_text(encoding="utf-8"))
    data["size"]["figure"]["$value"]["value"] = 0
    tokens.write_text(json.dumps(data), encoding="utf-8")
    shown = run_look(root, PIECE)
    assert shown.returncode == 1
    assert "Traceback" not in shown.stderr
    assert shown.stderr == (
        "error: the tool cannot draw page figure of `flow`: the page measures 0 by 0 px. "
        "`pkit visual check flow` names what the piece still owes\n"
    )


def test_a_local_folder_that_cannot_be_made_ends_in_an_error_line(flow: Path) -> None:
    local = flow / viewing.LOCAL
    if local.exists():
        shutil.rmtree(local)
    local.parent.mkdir(parents=True, exist_ok=True)
    local.write_text("a file where the folder goes", encoding="utf-8")
    shown = run_look(flow, PIECE)
    assert shown.returncode == 1
    assert shown.stderr.startswith("error: ")
    assert "Traceback" not in shown.stderr


def test_a_stale_picture_is_drawn_as_it_stands(flow: Path) -> None:
    """Nothing about a picture's staleness stops the step, or runs its producer."""
    piece = flow / PIECE_FOLDER / "piece.yaml"
    held = piece.read_text(encoding="utf-8")
    assert "width: 100" in held
    piece.write_text(held.replace("width: 100", "width: 120"), encoding="utf-8")
    before = written(flow)
    shown = run_look(flow, PIECE)
    assert shown.returncode == 0, shown.stderr
    assert report_of(flow)["losses"] == []
    assert {name: written(flow)[name] for name in before} == before


def a_brand_of_two_families(root: Path) -> None:
    """The test brand with a body type of two families: a cut of Source Sans Pro with no
    `ř`, then Source Sans Pro, which measures it."""
    brand = root / "visual" / "libraries" / "test-brand" / "1.0.0"
    font = TTFont(brand / "fonts" / "SourceSansPro-Regular.otf")
    held = [code for code in font.getBestCmap() or {} if code != ord("ř")]
    options = subset.Options()
    options.notdef_outline = True
    subsetter = subset.Subsetter(options)
    subsetter.populate(unicodes=held)
    subsetter.subset(font)
    font.save(brand / "fonts" / "Cut.otf")
    tokens = root / BRAND_TOKENS
    data = json.loads(tokens.read_text(encoding="utf-8"))
    body = data["font"]["body"]
    body["$value"] = ["Cut", "Source Sans Pro"]
    files = body["$extensions"]["pkit.visual-communication"]["files"]
    files["Cut"] = "fonts/Cut.otf"
    tokens.write_text(json.dumps(data), encoding="utf-8")


def test_a_run_measured_in_more_than_one_family_is_reported(tmp_path: Path) -> None:
    root = drawing_project(tmp_path, picture=False, head="Přehled")
    a_brand_of_two_families(root)
    shown = run_look(root, PIECE)
    assert shown.returncode == 0, shown.stderr
    report = report_of(root)
    place = {"language": "en", "key": "default", "page": "figure"}
    assert report["drawn-otherwise"] == [
        {
            **place,
            "element": "figure/body/steps[plan]/head",
            "text": "Přehled",
            "families": ["Cut", "Source Sans Pro"],
        }
    ]
    assert report["dropped"] == []
    assert any(each.startswith("drawn otherwise: figure ") for each in shown.stdout.splitlines())


def test_a_run_measured_in_one_family_of_two_is_not_reported(tmp_path: Path) -> None:
    root = drawing_project(tmp_path, picture=False, head="Plan")
    a_brand_of_two_families(root)
    assert run_look(root, PIECE).returncode == 0
    assert report_of(root)["drawn-otherwise"] == []


@pytest.mark.parametrize("family", ['H&M "Sans"', "A & B"])
def test_a_brand_s_family_name_holding_a_mark_draws_through_the_whole_step(
    tmp_path: Path, family: str
) -> None:
    root = drawing_project(tmp_path, picture=False)
    tokens = root / BRAND_TOKENS
    data = json.loads(tokens.read_text(encoding="utf-8"))
    body = data["font"]["body"]
    body["$value"] = [family]
    extension = body["$extensions"]["pkit.visual-communication"]
    extension["files"] = {family: extension["files"]["Source Sans Pro"]}
    tokens.write_text(json.dumps(data), encoding="utf-8")
    shown = run_look(root, PIECE)
    assert shown.returncode == 0, shown.stderr
    assert report_of(root)["dropped"] == []


# --- what it refuses ----------------------------------------------------------------------------


def test_a_piece_with_no_lock_is_refused_naming_render_its_files_left_as_they_were(
    tmp_path: Path,
) -> None:
    root = drawing_project(tmp_path, lock=None)
    (root / PIECE_FOLDER / "exports.yaml").write_text(
        "pkit_schema: visual-communication:exports\nschema_version: 1\nversions: []\n",
        encoding="utf-8",
    )
    before = written(root)
    shown = run_look(root, PIECE)
    assert shown.returncode == 1
    assert "`pkit visual render flow`" in shown.stderr
    assert shown.stderr.startswith(
        "error: the lock of visual/pieces/flow/piece.yaml cannot be drawn"
    )
    assert written(root) == before


@pytest.mark.parametrize(
    ("state", "fix"),
    [
        pytest.param(
            "final",
            "write back the lock of the version handed out, which is no move of it",
            id="final",
        ),
        pytest.param(
            "published",
            "the piece is published, so no render moves its lock: set it back to a draft and "
            "run `pkit visual render flow`",
            id="published",
        ),
    ],
)
def test_a_lock_no_render_moves_is_refused_and_told_of_its_state_and_of_no_pin(
    tmp_path: Path, state: str, fix: str
) -> None:
    root = drawing_project(tmp_path, state=state, pinned=True, lock=None)
    shown = run_look(root, PIECE)
    assert shown.returncode == 1
    assert shown.stderr == (
        f"error: the lock of visual/pieces/flow/piece.yaml cannot be drawn: the piece has no "
        f"lock yet, so its scenes cannot be drawn — {fix}\n"
    )


@pytest.mark.parametrize("state", ["final", "published"])
def test_a_version_not_yet_released_stops_no_drawing(tmp_path: Path, state: str) -> None:
    root = drawing_project(tmp_path, state=state, released=False, picture=False)
    shown = run_look(root, PIECE)
    assert shown.returncode == 0, shown.stderr
    assert (folder_of(root) / viewing.REPORT).is_file()


def test_a_published_lock_that_does_not_hold_still_stops_the_drawing(tmp_path: Path) -> None:
    lock = {"foundations": "1.0.0", "test-brand": "1.0.0", "tests": "1.2.0"}
    root = drawing_project(tmp_path, state="published", released=False, picture=False, lock=lock)
    shown = run_look(root, PIECE)
    assert shown.returncode == 1
    assert "tests@1.2.0, which the project does not hold" in shown.stderr
    assert "not yet released" not in shown.stderr


def test_a_library_a_final_pieces_content_uses_still_stops_the_drawing(tmp_path: Path) -> None:
    root = drawing_project(
        tmp_path, state="final", picture=False, lock={"foundations": "1.0.0", "test-brand": "1.0.0"}
    )
    shown = run_look(root, PIECE)
    assert shown.returncode == 1
    assert "the lock does not name `tests`, which the piece uses" in shown.stderr


def test_a_piece_the_location_lacks_is_refused(flow: Path) -> None:
    shown = run_look(flow, "no-such-piece")
    assert shown.returncode == 1
    assert "the location holds no piece `no-such-piece`" in shown.stderr


def test_a_project_with_no_visual_work_is_refused_and_records_no_location(tmp_path: Path) -> None:
    root = project(tmp_path)
    shown = run_look(root, PIECE)
    assert shown.returncode == 1
    assert shown.stderr == f"error: the project holds no visual work, so no piece `{PIECE}`\n"
    assert written(root) == {}


def test_a_lock_that_does_not_hold_is_refused(tmp_path: Path) -> None:
    root = drawing_project(
        tmp_path, lock={"foundations": "1.0.0", "test-brand": "2.0.0", "tests": "1.0.0"}
    )
    shown = run_look(root, PIECE)
    assert shown.returncode == 1
    assert "the lock of visual/pieces/flow/piece.yaml cannot be drawn" in shown.stderr


def test_a_font_with_no_file_refuses_before_anything_is_written(flow: Path) -> None:
    (flow / "visual/libraries/test-brand/1.0.0/fonts/SourceSansPro-Regular.otf").unlink()
    before = written(flow)
    shown = run_look(flow, PIECE)
    assert shown.returncode == 1
    assert shown.stderr.startswith("error: ")
    assert written(flow) == before


def test_a_page_the_tool_cannot_draw_refuses_with_nothing_written(
    flow: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def failing(_svg: str, _at: float, _folder: Path, _widths: Any, **_regions: Any) -> Any:
        raise viewing_tool.ToolFailed("Failed to create pixmap")

    monkeypatch.setattr(viewing.viewing_tool, "draw", failing)
    shown = run_look(flow, PIECE)
    assert shown.returncode == 1
    assert shown.stderr == (
        "error: the tool cannot draw page figure of `flow`: Failed to create pixmap. "
        "`pkit visual check flow` names what the piece still owes\n"
    )
    assert not folder_of(flow).exists()


# --- the HTML renderer's pages, through a browser (DEC-020 points 5, 7 and 8) ------------------


def write_config(root: Path, lines: str) -> None:
    """The capability's configuration, holding `lines` after its binding."""
    config = root / ".pkit" / "capabilities" / "visual-communication" / "project" / "config.yaml"
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text(
        f"pkit_schema: visual-communication:config\nschema_version: 1\n{lines}", encoding="utf-8"
    )


def name_browser(root: Path, program: Path) -> Path:
    """The configuration names `program` as the browser, and gives it."""
    write_config(root, f"browser: {json.dumps(str(program))}\n")
    return program


def write_program(path: Path) -> Path:
    """A program that leaves a file beside it when it runs."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f'#!/bin/sh\ntouch "{path.parent / "started"}"\n', encoding="utf-8")
    path.chmod(0o755)
    return path


def no_browser_here(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """No browser where the step looks."""
    monkeypatch.setattr(viewing_browser, "PLACES", {sys.platform: (str(tmp_path / "no-browser"),)})
    monkeypatch.setenv("PATH", str(tmp_path / "no-path"))


def html_folder(root: Path, piece: str = PIECE) -> Path:
    return root / viewing.folder_of(piece, "html")


def html_report(root: Path, piece: str = PIECE) -> dict[str, Any]:
    return json.loads((html_folder(root, piece) / viewing.REPORT).read_text(encoding="utf-8"))


def previewed(project: Any) -> Any:
    """What fills the facts of an export in the scenes the step draws: what a preview fills."""
    return exports.preview_filling(project.piece).facts


def scene_of(root: Path, piece: str, language: str) -> dict[str, Any]:
    project = viewing.opened(root, piece)
    [(_, result)] = viewing.scenes(project, [language], facts=previewed(project))
    return result.scene.to_dict()


def page_file_of(root: Path, piece: str, language: str, key: str) -> bytes:
    """The page file the HTML renderer writes of `piece`, apart from any run of the step."""
    project = viewing.opened(root, piece)
    results = viewing.scenes(project, [language], facts=previewed(project))
    [(_, _, drawn)] = list(viewing.pl.drawn(project, results, "html", [key]))
    return bytes(drawn.document)


def as_read(root: Path, piece: str, language: str) -> dict[str, Any]:
    """The page file of `piece` in `language` as a browser's reads find it, each span drawn in
    a face of the file and leaving ink: what a stand-in answers."""
    index = 0
    held = []
    for page in viewing.pages_of(scene_of(root, piece, language)):
        wanted = viewing.browser_page(page)
        texts = []
        for each in wanted.texts:
            lines = []
            for words in each.lines:
                lines.append([held_span(word, index + at, y=10.0) for at, word in enumerate(words)])
                index += len(words)
            texts.append(held_text(each.element, *lines))
        held.append(held_page(wanted.id, wanted.width, wanted.height, *texts))
    return {"pages": held}


def browser_for(
    root: Path, tmp_path: Path, piece: str, files: Mapping[str, str], **plan: Any
) -> Path:
    """A stand-in browser for the page files `files` names, each by its language, under
    `plan`, named in the configuration."""
    documents = {name: as_read(root, piece, language) for name, language in files.items()}
    held = {
        "functions": FUNCTIONS,
        "documents": {
            viewing_browser.PLANTED_FILE: planted(),
            viewing_browser.PLANTED_FORCED_FILE: planted(forced=True),
            **documents,
        },
        **plan,
    }
    return name_browser(root, stand_in(tmp_path / "browser", held))


class Browser:
    """`viewing_browser.draw` in a browser's place, and `draw_forced` as `forced`: what each
    call was handed, the file's bytes as it read them among it. It draws each page in each mode,
    or each forced palette, at the scale it is given, an image of each region a page is handed
    with, as `read` says, or as it says of that mode where it is a function of one, or raises
    `stops` at the call of that number, from 1."""

    def __init__(
        self,
        read: Any = None,
        stops: Mapping[int, Exception] | None = None,
        version: str = "Chrome/157.0.1.2",
    ) -> None:
        self.read = read or viewing_browser.Read((), (), (), (), ())
        self.stops = dict(stops or {})
        self.version = version
        self.calls: list[dict[str, Any]] = []

    def __call__(
        self,
        file: Path,
        wanted: Any,
        scale: float,
        program: Path,
        folder: Path,
        *,
        signals: Mapping[str, Sequence[str]] | None = None,
        modes: Sequence[Mapping[str, str]] = ({},),
    ) -> Any:
        return self._drawn(file, wanted, scale, program, folder, signals, [("", m) for m in modes])

    def forced(
        self,
        file: Path,
        wanted: Any,
        scale: float,
        program: Path,
        folder: Path,
        *,
        signals: Mapping[str, Sequence[str]] | None = None,
    ) -> Any:
        palettes = [
            (each.name, {**each.signals, **viewing_browser.FORCED})
            for each in viewing_browser.PALETTES
        ]
        return self._drawn(file, wanted, scale, program, folder, signals, palettes)

    def _drawn(
        self,
        file: Path,
        wanted: Any,
        scale: float,
        program: Path,
        folder: Path,
        signals: Mapping[str, Sequence[str]] | None,
        modes: Sequence[tuple[str, Mapping[str, str]]],
    ) -> Any:
        self.calls.append(
            {
                "name": file.name,
                "bytes": file.read_bytes(),
                "pages": list(wanted),
                "scale": scale,
                "program": program,
                "folder": folder,
                "signals": dict(signals or {}),
                "modes": [dict(mode) for _, mode in modes],
                "palettes": [palette for palette, _ in modes if palette],
            }
        )
        if len(self.calls) in self.stops:
            raise self.stops[len(self.calls)]
        images = tuple(
            viewing_browser.Image(
                each.id,
                b"\x89PNG " + f"{each.id} {band}".encode(),
                round(each.width * scale),
                round(height * scale),
                band,
            )
            for each in wanted
            for band, (_, height) in (
                enumerate(each.regions, 1) if each.regions else [(0, (0.0, each.height))]
            )
        )
        return viewing_browser.Drawing(
            self.version,
            tuple(
                viewing_browser.Shown(
                    dict(mode),
                    images,
                    self.read(mode) if callable(self.read) else self.read,
                    palette,
                )
                for palette, mode in modes
            ),
        )


@pytest.fixture
def browser(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Browser]:
    """The browser `draw` is handed, in place of one."""
    drawn = Browser()
    monkeypatch.setattr(viewing.viewing_browser, "draw", drawn)
    monkeypatch.setattr(viewing.viewing_browser, "draw_forced", drawn.forced)
    yield drawn


def html_flow(tmp_path: Path, program: bool = True, **fields: Any) -> Path:
    """`flow` in both colour schemes with its picture, and a program the configuration names
    as the browser, which `Browser` stands in for; `fields` are the piece's own, such as its
    `exports`."""
    root = drawing_project(tmp_path, **fields)
    write_picture(root, framing)
    if program:
        name_browser(root, write_program(tmp_path / "browser" / "chromium"))
    return root


def test_the_html_renderer_draws_one_image_for_each_page_language_and_key_with_its_frames(
    tmp_path: Path,
) -> None:
    """Both keys lie in one file of each language, which one start draws in each mode."""
    root = starter_project(tmp_path)
    files = {f"tag.{language}.default.html": language for language in ("en", "de")}
    program = browser_for(root, tmp_path, "tag", files)
    shown = run_look(
        root,
        "tag",
        "--renderer",
        "html",
        "--every-language",
        "--key",
        "default",
        "--key",
        "contrast.high",
    )
    assert shown.returncode == 0, shown.stderr
    report = html_report(root, "tag")
    images = [image["image"] for image in report["images"]]
    assert images == [
        f"tag.{language}.{key}.{number}.png"
        for language in ("en", "de")
        for key in ("default", "contrast.high")
        for number in (1, 2)
    ]
    held = sorted(path.name for path in html_folder(root, "tag").iterdir())
    frames = [image.replace(".png", ".frames.json") for image in images]
    assert held == sorted([*images, *frames, *files, viewing.REPORT])
    first = json.loads((html_folder(root, "tag") / frames[0]).read_text(encoding="utf-8"))
    assert first["elements"][0]["id"] == first["page"]
    assert first["lock"] == report["lock"]
    starts = [each for each in logged(program) if "flags" in each]
    assert len(starts) == len(files)
    opened = [each["url"].rsplit("/", 1)[-1] for each in called(program, "Page.navigate")]
    assert opened == [name for file in files for name in (viewing_browser.PLANTED_FILE, file)]


def test_the_svg_renderer_is_named_as_it_is_by_default(flow: Path) -> None:
    shown = run_look(flow, PIECE, "--renderer", "svg")
    assert shown.returncode == 0, shown.stderr
    assert report_of(flow)["renderer"]["name"] == "svg"
    assert not html_folder(flow).exists()


@pytest.mark.parametrize("renderer", ["pdf", "html5", ""])
def test_a_renderer_of_another_name_is_refused_with_nothing_written(
    flow: Path, renderer: str
) -> None:
    before = written(flow)
    shown = run_look(flow, PIECE, "--renderer", renderer)
    assert shown.returncode == 1
    assert shown.stderr == (
        f"error: the viewing step reads no renderer `{renderer}`: it reads `svg` and `html`\n"
    )
    assert written(flow) == before


@pytest.mark.parametrize(
    ("formats", "renderer"),
    [
        ([], "svg"),
        (["svg"], "svg"),
        (["pdf"], "svg"),
        (["svg", "pdf"], "svg"),
        (["html"], "html"),
        (["pdf", "html"], "html"),
    ],
)
def test_a_piece_that_declares_html_is_read_through_it_and_any_other_through_svg(
    tmp_path: Path, formats: list[str], renderer: str
) -> None:
    root = drawing_project(tmp_path, picture=False, exports=formats)
    piece = viewing.pl.read_piece(root, "visual", PIECE)
    assert viewing.renderer_of(piece) == renderer


def test_a_piece_that_declares_html_is_drawn_through_it_with_no_renderer_named(
    tmp_path: Path, browser: Browser
) -> None:
    root = html_flow(tmp_path, exports=["html"])
    shown = run_look(root, PIECE)
    assert shown.returncode == 0, shown.stderr
    assert html_report(root)["renderer"]["name"] == "html"
    assert not folder_of(root).exists()


def test_a_piece_that_declares_html_still_reaches_the_svg_renderers_images_when_named(
    tmp_path: Path, browser: Browser
) -> None:
    root = html_flow(tmp_path, exports=["html"])
    shown = run_look(root, PIECE, "--renderer", "svg")
    assert shown.returncode == 0, shown.stderr
    assert report_of(root)["renderer"]["name"] == "svg"
    assert sorted(path.name for path in folder_of(root).iterdir()) == [
        "flow.en.default.frames.json",
        "flow.en.default.png",
        viewing.REPORT,
    ]
    assert not html_folder(root).exists()
    assert browser.calls == []


def test_with_no_renderer_named_a_piece_that_does_not_declare_html_draws_as_before(
    flow: Path,
) -> None:
    assert run_look(flow, PIECE).returncode == 0
    assert sorted(path.name for path in folder_of(flow).iterdir()) == [
        "flow.en.default.frames.json",
        "flow.en.default.png",
        viewing.REPORT,
    ]
    assert sorted(path.name for path in (flow / viewing.FOLDER).iterdir()) == [PIECE]


def test_its_folder_lies_beside_the_svg_renderers_under_a_name_no_piece_can_take() -> None:
    assert viewing.folder_of(PIECE, "svg") == f"{viewing.FOLDER}/{PIECE}"
    assert viewing.folder_of(PIECE, "html") == f"{viewing.FOLDER}/{PIECE}.html"
    assert names.is_name(PIECE)
    assert not names.is_name(f"{PIECE}.html")


def test_a_run_replaces_only_its_own_folder_and_a_stop_deletes_no_svg_image(
    tmp_path: Path, browser: Browser
) -> None:
    root = html_flow(tmp_path)
    assert run_look(root, PIECE).returncode == 0
    drawn_by_svg = {path.name: path.read_bytes() for path in folder_of(root).iterdir()}
    assert (
        run_look(root, PIECE, "--renderer", "html", "--key", "colour-scheme.dark").returncode == 0
    )
    (html_folder(root) / "left-by-a-person.txt").write_text("gone", encoding="utf-8")
    assert run_look(root, PIECE, "--renderer", "html").returncode == 0
    assert sorted(path.name for path in html_folder(root).iterdir()) == [
        "flow.en.default.frames.json",
        "flow.en.default.html",
        "flow.en.default.png",
        viewing.REPORT,
    ]
    browser.stops[len(browser.calls) + 1] = viewing_browser.Stopped("the browser stopped")
    assert run_look(root, PIECE, "--renderer", "html").returncode == look.STOPPED
    assert {path.name: path.read_bytes() for path in folder_of(root).iterdir()} == drawn_by_svg


def test_the_browser_reads_the_page_file_as_the_renderer_wrote_it(
    tmp_path: Path, browser: Browser
) -> None:
    """Both keys lie in one file, named by the first, which one call draws in each mode."""
    root = html_flow(tmp_path)
    shown = run_look(root, PIECE, "--renderer", "html", "--every-key")
    assert shown.returncode == 0, shown.stderr
    [call] = browser.calls
    assert call["name"] == f"{PIECE}.en.default.html"
    assert call["bytes"] == page_file_of(root, PIECE, "en", "default")
    assert call["bytes"] == page_file_of(root, PIECE, "en", "colour-scheme.dark")
    assert (html_folder(root) / call["name"]).read_bytes() == call["bytes"]
    assert call["folder"] == root / viewing.LOCAL


def test_a_piece_on_a_size_axis_is_read_through_a_browser_at_each_key_from_its_size_s_scene(
    tmp_path: Path, browser: Browser
) -> None:
    dark = "colour-scheme.dark"
    keys = ["default", dark, PHONE, f"{dark}+{PHONE}"]
    root = on_devices(
        tmp_path, modes={"colour-scheme": ["light", "dark"], "device": ["desktop", "phone"]}
    )
    name_browser(root, write_program(tmp_path / "browser" / "chromium"))
    shown = run_look(root, PIECE, "--renderer", "html", "--every-key")
    assert shown.returncode == 0, shown.stderr
    files = {"default": ("default", dark), PHONE: (PHONE, f"{dark}+{PHONE}")}
    assert [call["name"] for call in browser.calls] == [f"{PIECE}.en.{key}.html" for key in files]
    widths = {key: call["pages"][0].width for key, call in zip(files, browser.calls, strict=True)}
    assert widths["default"] > widths[PHONE]
    for held, call in zip(files.values(), browser.calls, strict=True):
        assert all(call["bytes"] == page_file_of(root, PIECE, "en", key) for key in held)
        assert [mode["prefers-color-scheme"] for mode in call["modes"]] == ["light", "dark"]
    assert [image["key"] for image in html_report(root)["images"]] == keys
    assert run_look(root, PIECE, "--renderer", "html", "--key", PHONE).returncode == 0
    assert browser.calls[-1]["pages"][0].width == widths[PHONE]
    assert len(browser.calls[-1]["modes"]) == 1
    assert [image["key"] for image in html_report(root)["images"]] == [PHONE]


def test_the_pages_handed_to_the_browser_are_the_scenes_with_each_texts_spans(
    tmp_path: Path, browser: Browser
) -> None:
    root = html_flow(tmp_path)
    assert run_look(root, PIECE, "--renderer", "html").returncode == 0
    [call] = browser.calls
    [page] = call["pages"]
    [held] = viewing.pages_of(scene_of(root, PIECE, "en"))
    assert (page.id, page.width, page.height) == (held["id"], held["width"], held["height"])
    head = next(each for each in page.texts if each.element == "figure/body/steps[plan]/head")
    assert head.lines == (("Plan the work.",),)


def test_a_run_leaves_the_page_file_beside_the_images_and_writes_nothing_else(
    tmp_path: Path, browser: Browser
) -> None:
    """No number, no `exports.yaml`, no preview: nothing outside the renderer's folder."""
    root = html_flow(tmp_path)
    before = written(root)
    shown = run_look(root, PIECE, "--renderer", "html")
    assert shown.returncode == 0, shown.stderr
    after = written(root)
    made = sorted(name for name in after if name not in before)
    assert all(name.startswith(f"{viewing.folder_of(PIECE, 'html')}/") for name in made)
    assert {name: after[name] for name in before} == before
    assert f"{viewing.folder_of(PIECE, 'html')}/flow.en.default.html" in made
    assert [path.name for path in (root / viewing.LOCAL).iterdir()] == ["look"]
    assert html_report(root)["page-files"] == [
        {
            "language": "en",
            "key": "default",
            "keys": ["default", "colour-scheme.dark"],
            "file": "flow.en.default.html",
        }
    ]
    assert (
        f"page file: {viewing.folder_of(PIECE, 'html')}/flow.en.default.html, to open in your "
        "own browser"
    ) in shown.stdout.splitlines()


def test_the_pages_of_one_file_share_the_largest_scale_any_of_them_asks(
    tmp_path: Path, browser: Browser
) -> None:
    root = starter_project(tmp_path)
    name_browser(root, write_program(tmp_path / "browser" / "chromium"))
    assert run_look(root, "tag", "--renderer", "html").returncode == 0
    [call] = browser.calls
    every = viewing.pages_of(scene_of(root, "tag", "en"))
    assert call["scale"] == viewing.device_scale(every)
    places = 10**-viewing.SCALE_PLACES
    assert all(call["scale"] > viewing.scale(page) - places for page in every)
    report = html_report(root, "tag")
    edges = [max(each["pixels"].values()) for each in report["images"]]
    assert all(edge == viewing.LONG_EDGE for edge in edges)


def test_a_device_scale_is_the_largest_a_page_asks_rounded_up_as_far_as_the_widest_fits() -> None:
    small = {"width": 960, "height": 540}
    tiny_text = text_page(960, 540, 4)
    assert viewing.scale(small) == viewing.LONG_EDGE / 960
    assert viewing.device_scale([text_page(390, 5000, 15)]) == 0.667
    assert viewing.device_scale([small, text_page(390, 5000, 15)]) == 1.633
    assert viewing.device_scale([small]) == 1.633
    assert viewing.device_scale([small, tiny_text]) == 1.633
    assert viewing.too_wide(tiny_text, 1.633)
    assert not viewing.too_wide(small, 1.633)
    assert viewing.device_scale([{"width": 784, "height": 100}]) == 2.0


def test_the_browsers_profile_lies_in_the_local_folder_and_a_run_removes_it(
    tmp_path: Path,
) -> None:
    root = drawing_project(tmp_path, picture=False)
    program = browser_for(root, tmp_path, PIECE, {"flow.en.default.html": "en"})
    shown = run_look(root, PIECE, "--renderer", "html")
    assert shown.returncode == 0, shown.stderr
    [start] = [each for each in logged(program) if "flags" in each]
    [profile] = [flag for flag in start["flags"] if flag.startswith("--user-data-dir=")]
    assert Path(profile.split("=", 1)[1]).is_relative_to(root / viewing.LOCAL)
    assert [path.name for path in (root / viewing.LOCAL).iterdir()] == ["look"]


@pytest.mark.parametrize(
    "fault",
    [
        pytest.param({"method": "Page.captureScreenshot", "kind": "die"}, id="dies"),
        pytest.param({"method": "Page.captureScreenshot", "kind": "hang"}, id="hangs"),
    ],
)
def test_a_browser_that_stops_part_way_leaves_the_page_file_a_report_and_no_image(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: dict[str, Any]
) -> None:
    monkeypatch.setattr(viewing_browser, "CALL_SECONDS", 1.0)
    monkeypatch.setattr(viewing_browser, "CLOSE_SECONDS", 0.5)
    root = drawing_project(tmp_path, picture=False)
    plan = {"fault": {**fault, "document": "flow.en.default.html"}}
    browser_for(root, tmp_path, PIECE, {"flow.en.default.html": "en"}, **plan)
    shown = run_look(root, PIECE, "--renderer", "html")
    assert shown.returncode == look.STOPPED, shown.stderr
    assert sorted(path.name for path in html_folder(root).iterdir()) == [
        "flow.en.default.html",
        viewing.REPORT,
    ]
    report = html_report(root)
    assert report["images"] == []
    assert report["stopped"]["what"].startswith("the browser ")
    assert [path.name for path in (root / viewing.LOCAL).iterdir()] == ["look"]


def test_a_first_read_that_fails_stops_the_run(tmp_path: Path) -> None:
    root = drawing_project(tmp_path, picture=False)
    program = browser_for(root, tmp_path, PIECE, {"flow.en.default.html": "en"})
    plan = json.loads((program.parent / "plan.json").read_text(encoding="utf-8"))
    for held in plan["documents"][viewing_browser.PLANTED_FILE]["pages"][0]["texts"]:
        for spans in held["lines"]:
            for each in spans:
                each["ink"] = ["#ffffff", "#000000"]
    (program.parent / "plan.json").write_text(json.dumps(plan), encoding="utf-8")
    shown = run_look(root, PIECE, "--renderer", "html")
    assert shown.returncode == look.STOPPED
    stop = html_report(root)["stopped"]
    assert stop["what"].startswith("the first read did not name ")
    assert stop["program"] == str(program)
    assert called(program, "Page.captureScreenshot")
    assert not list(html_folder(root).glob("*.png"))


def test_a_browser_that_stops_at_a_later_file_leaves_no_partial_images(
    tmp_path: Path, browser: Browser
) -> None:
    root = on_devices(
        tmp_path, modes={"colour-scheme": ["light", "dark"], "device": ["desktop", "phone"]}
    )
    name_browser(root, write_program(tmp_path / "browser" / "chromium"))
    browser.stops[2] = viewing_browser.Stopped("the browser stopped at `Page.captureScreenshot`")
    shown = run_look(root, PIECE, "--renderer", "html", "--every-key")
    assert shown.returncode == look.STOPPED
    assert len(browser.calls) == 2
    assert sorted(path.name for path in html_folder(root).iterdir()) == [
        "flow.en.default.html",
        f"flow.en.{PHONE}.html",
        viewing.REPORT,
    ]


def test_where_no_browser_runs_the_report_says_what_stopped_it_under_which_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, browser: Browser
) -> None:
    root = html_flow(tmp_path, program=False)
    no_browser_here(tmp_path, monkeypatch)
    shown = run_look(root, PIECE, "--renderer", "html")
    assert shown.returncode == look.STOPPED
    assert browser.calls == []
    report = html_report(root)
    assert report["lock"] == {"foundations": "1.0.0", "test-brand": "1.0.0", "tests": "1.0.0"}
    assert report["renderer"] == {"name": "html", "version": html.VERSION}
    assert report["tool"] is None and report["images"] == []
    stop = report["stopped"]
    assert stop["what"] == "no browser of the Chromium family was found"
    assert str(tmp_path / "no-browser") in stop["looked"]
    assert stop["sandbox"] is False and stop["as-root"] is False
    assert stop["go-on"] == viewing.ways_on(PIECE)
    lines = shown.stderr.splitlines()
    assert lines[0].startswith("stopped: no browser of the Chromium family was found; looked at:")
    assert lines[1] == (
        f"stopped: no image; the page files and report.json lie in "
        f"{viewing.folder_of(PIECE, 'html')}/"
    )
    assert lines[2] == "lock: foundations 1.0.0, test-brand 1.0.0, tests 1.0.0"
    assert lines[4:] == [
        *(f"go on: {way}" for way in viewing.ways_on(PIECE)),
        f"for an agent: {viewing.FOR_AN_AGENT}",
    ]
    assert shown.stdout == ""


def test_a_stop_names_the_ways_on_in_their_order() -> None:
    """A build pipeline's drawings, a way a project may take, of a pushed commit; the same
    look, addressed to a person, outside any sandbox; then the SVG renderer's pages
    (DEC-024 point 4)."""
    pipeline, person, svg_pages = viewing.ways_on(PIECE)
    assert pipeline.startswith("a build pipeline's drawings, where the project has its pipeline ")
    assert "`visual-drawings-<commit>`" in pipeline
    assert "They show a pushed commit, not the working tree" in pipeline
    assert person.startswith(f"for a person: run `pkit visual look {PIECE} --renderer html` once ")
    assert "outside any sandbox, such as in your own terminal" in person
    assert "with your rights" in person
    assert svg_pages.startswith(f"`pkit visual look {PIECE} --renderer svg` draws the same scenes")


def test_the_page_a_stop_names_holds_the_section_on_a_pipeline_s_drawings() -> None:
    page = Path(__file__).resolve().parents[1] / viewing.DRAWINGS_PAGE
    assert f"### {viewing.DRAWINGS_SECTION}\n" in page.read_text(encoding="utf-8")
    assert viewing.DRAWINGS.replace("<commit>", "") in page.read_text(encoding="utf-8")


def test_a_stop_a_sandbox_made_says_so(tmp_path: Path, browser: Browser) -> None:
    root = html_flow(tmp_path)
    said = "Failed to bind() /var/folders/T/SingletonSocket: Operation not permitted (1)"
    browser.stops[1] = viewing_browser.Stopped("the browser stopped", program="b", said=said)
    shown = run_look(root, PIECE, "--renderer", "html")
    assert shown.returncode == look.STOPPED
    stop = html_report(root)["stopped"]
    assert stop["sandbox"] is True and stop["as-root"] is False
    lines = shown.stderr.splitlines()
    assert lines[0] == f"stopped: the browser stopped; started: b; it said: {said}"
    assert lines[1] == "stopped: a sandbox stopped the browser"
    assert [line for line in lines if line.startswith("go on: ")] == [
        f"go on: {way}" for way in viewing.ways_on(PIECE)
    ]


def test_a_stop_with_no_sandbox_in_its_words_names_what_the_browser_said(
    tmp_path: Path, browser: Browser
) -> None:
    root = html_flow(tmp_path)
    said = "Trace/BPT trap: 5"
    browser.stops[1] = viewing_browser.Stopped("the browser stopped", program="b", said=said)
    shown = run_look(root, PIECE, "--renderer", "html")
    assert shown.returncode == look.STOPPED
    stop = html_report(root)["stopped"]
    assert stop["sandbox"] is False and stop["as-root"] is False and stop["said"] == said
    lines = shown.stderr.splitlines()
    assert lines[0] == f"stopped: the browser stopped; started: b; it said: {said}"
    assert [line for line in lines if line.startswith("stopped: ")] == [
        lines[0],
        f"stopped: no image; the page files and report.json lie in "
        f"{viewing.folder_of(PIECE, 'html')}/",
    ]


#: What Chrome says where it runs as root, which refuses to start with its own sandbox on.
AS_ROOT = (
    "[1107/101010.000000:ERROR:zygote_host_impl_linux.cc(128)] Running as root without "
    "--no-sandbox is not supported. See https://crbug.com/638180."
)


def test_a_browser_run_as_root_gets_a_stop_of_its_own_with_the_same_ways_on(
    tmp_path: Path, browser: Browser
) -> None:
    root = html_flow(tmp_path)
    browser.stops[1] = viewing_browser.Stopped("the browser stopped", program="b", said=AS_ROOT)
    shown = run_look(root, PIECE, "--renderer", "html")
    assert shown.returncode == look.STOPPED
    stop = html_report(root)["stopped"]
    assert stop["as-root"] is True and stop["sandbox"] is False
    assert stop["go-on"] == viewing.ways_on(PIECE)
    lines = shown.stderr.splitlines()
    assert lines[1] == (
        "stopped: the browser runs as root, where it refuses to start with its own sandbox on, "
        "and the step never turns that sandbox off"
    )
    assert "stopped: a sandbox stopped the browser" not in lines
    assert [line for line in lines if line.startswith("go on: ")] == [
        f"go on: {way}" for way in viewing.ways_on(PIECE)
    ]


#: What no stop names, outside the browser's own words: the harness's escape, the model's
#: command that applies an exclusion, any exclusion, whether of the viewing command, of
#: `pkit` or of `uv`, and any form of the command that runs through `uv` (DEC-024 point 4).
NEVER_NAMED = (
    r"exclu",
    r"dangerous",
    r"escape",
    r"permissions",
    r"unsandboxed",
    r"\buv\b",
    r"no-sandbox",
)


@pytest.mark.parametrize(
    "said",
    [
        pytest.param("", id="no-browser"),
        pytest.param("sandbox initialization failed: Operation not permitted", id="sandbox"),
        pytest.param(AS_ROOT, id="as-root"),
        pytest.param("Trace/BPT trap: 5", id="otherwise"),
    ],
)
def test_no_stop_names_a_way_out_of_the_sandbox(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, browser: Browser, said: str
) -> None:
    """The browser's own words, and where the step looked, are left out of what is read."""
    root = html_flow(tmp_path, program=bool(said))
    if said:
        browser.stops[1] = viewing_browser.Stopped("the browser stopped", program="b", said=said)
    else:
        no_browser_here(tmp_path, monkeypatch)
    shown = run_look(root, PIECE, "--renderer", "html")
    assert shown.returncode == look.STOPPED
    stop = html_report(root)["stopped"]
    held = {key: value for key, value in stop.items() if key not in ("said", "looked")}
    printed = shown.stderr.replace(said, "") if said else shown.stderr
    for place in stop["looked"]:
        printed = printed.replace(place, "")
    written = [printed, json.dumps(held)]
    for words in NEVER_NAMED:
        for each in written:
            assert not re.search(words, each, re.IGNORECASE), (words, each)


def test_a_stop_is_an_exit_of_its_own_and_a_refusal_leaves_the_folder_as_it_was(
    tmp_path: Path, browser: Browser
) -> None:
    root = html_flow(tmp_path)
    assert look.STOPPED not in (0, 1, 2)
    assert f"  {look.STOPPED}  stopped:" in str(look.__doc__)
    assert run_look(root, PIECE, "--renderer", "html").returncode == 0
    before = written(root)
    shown = run_look(root, PIECE, "--renderer", "html", "--page", "9")
    assert shown.returncode == 1
    assert written(root) == before


def drawn_by_both(root: Path, *args: str) -> list[tuple[int, str]]:
    """What a run of each renderer ends with: its exit and what it said."""
    return [
        (shown.returncode, shown.stderr)
        for shown in (
            run_look(root, PIECE, *args, "--renderer", renderer) for renderer in ("svg", "html")
        )
    ]


@pytest.mark.parametrize(
    "args",
    [
        pytest.param(["--page", "2"], id="page"),
        pytest.param(["--language", "fr"], id="language"),
        pytest.param(["--key", "contrast.low"], id="key"),
    ],
)
def test_what_refuses_an_svg_run_refuses_an_html_run_before_any_write(
    tmp_path: Path, browser: Browser, args: list[str]
) -> None:
    root = html_flow(tmp_path)
    before = written(root)
    [by_svg, by_html] = drawn_by_both(root, *args)
    assert by_svg[0] == by_html[0] == 1
    assert by_svg[1] == by_html[1]
    assert written(root) == before
    assert browser.calls == []


def test_a_page_with_no_size_refuses_an_html_run_naming_the_check(
    tmp_path: Path, browser: Browser
) -> None:
    root = drawing_project(tmp_path)
    name_browser(root, write_program(tmp_path / "browser" / "chromium"))
    before = written(root)
    shown = run_look(root, PIECE, "--renderer", "html")
    assert shown.returncode == 1
    assert shown.stderr == (
        "error: the browser cannot draw page figure of `flow`: the page measures 960 by 0 px. "
        "`pkit visual check flow` names what the piece still owes\n"
    )
    assert written(root) == before
    assert not (root / viewing.LOCAL).exists()
    assert browser.calls == []


def test_a_page_past_the_most_pixels_refuses_an_html_run(
    tmp_path: Path, browser: Browser, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = html_flow(tmp_path)
    monkeypatch.setattr(viewing.viewing_tool, "MOST_PIXELS", 1000)
    shown = run_look(root, PIECE, "--renderer", "html")
    assert shown.returncode == 1
    assert "the page takes more than 1000" in shown.stderr
    assert browser.calls == []


@pytest.mark.parametrize(
    "case",
    ["no lock", "a lock that does not hold", "a font with no file", "no visual work"],
)
def test_a_piece_that_cannot_be_drawn_refuses_either_renderer_alike(
    tmp_path: Path, browser: Browser, case: str
) -> None:
    if case == "no lock":
        root = drawing_project(tmp_path, lock=None)
    elif case == "a lock that does not hold":
        lock = {"foundations": "1.0.0", "test-brand": "2.0.0", "tests": "1.0.0"}
        root = drawing_project(tmp_path, lock=lock)
    elif case == "a font with no file":
        root = html_flow(tmp_path, program=False)
        (root / "visual/libraries/test-brand/1.0.0/fonts/SourceSansPro-Regular.otf").unlink()
    else:
        root = project(tmp_path)
    name_browser(root, write_program(tmp_path / "browser" / "chromium"))
    before = written(root)
    [by_svg, by_html] = drawn_by_both(root)
    assert by_svg[0] == by_html[0] == 1
    assert by_svg[1] == by_html[1]
    assert written(root) == before
    assert browser.calls == []


def test_a_project_names_its_browser_in_the_configuration(
    tmp_path: Path, browser: Browser, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = html_flow(tmp_path, program=False)
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    for given, program in (
        ("~/browsers/chromium", home / "browsers" / "chromium"),
        ("tools/chromium", root / "tools" / "chromium"),
        (str(tmp_path / "pinned" / "chrome"), tmp_path / "pinned" / "chrome"),
    ):
        write_program(program)
        write_config(root, f"browser: {json.dumps(given)}\n")
        shown = run_look(root, PIECE, "--renderer", "html")
        assert shown.returncode == 0, shown.stderr
        assert browser.calls[-1]["program"] == program
        assert html_report(root)["tool"]["program"] == str(program)
        assert not (program.parent / "started").exists()


def test_a_browser_named_that_is_no_program_stops_the_run_naming_it(
    tmp_path: Path, browser: Browser
) -> None:
    root = html_flow(tmp_path, program=False)
    name_browser(root, tmp_path / "no-such-browser")
    shown = run_look(root, PIECE, "--renderer", "html")
    assert shown.returncode == look.STOPPED
    stop = html_report(root)["stopped"]
    assert stop["what"] == "the browser named is no program that runs"
    assert stop["looked"] == [str(tmp_path / "no-such-browser")]


@pytest.mark.parametrize("value", ["", "3", "[a]", "null"])
def test_a_configuration_whose_browser_names_no_program_refuses_the_run(
    tmp_path: Path, browser: Browser, value: str
) -> None:
    root = html_flow(tmp_path, program=False)
    write_config(root, f"browser: {value}\n")
    before = written(root)
    shown = run_look(root, PIECE, "--renderer", "html")
    assert shown.returncode == 1
    assert "which names no program: write the path of the browser there" in shown.stderr
    assert written(root) == before


def test_no_flag_and_no_environment_variable_names_a_browser() -> None:
    """The choice lies in a file the project reviews (DEC-020 point 7)."""
    shown = run_main(look, "--help")
    assert "--browser" not in shown.stdout
    for module in (viewing, viewing_browser, look):
        source = Path(str(module.__file__)).read_text(encoding="utf-8")
        assert "os.environ" not in source and "getenv" not in source


def test_the_report_names_the_browser_and_says_an_image_stands_for_it_alone(
    tmp_path: Path, browser: Browser
) -> None:
    root = html_flow(tmp_path)
    shown = run_look(root, PIECE, "--renderer", "html")
    assert shown.returncode == 0, shown.stderr
    report = html_report(root)
    assert report["renderer"] == {"name": "html", "version": html.VERSION}
    assert report["tool"] == {
        "name": "Chrome",
        "version": "157.0.1.2",
        "program": str(tmp_path / "browser" / "chromium"),
    }
    assert report["stands-for"] == (
        "each image shows how Chrome 157.0.1.2 drew the page, and stands for no other browser"
    )
    assert report["stopped"] is None
    lines = shown.stdout.splitlines()
    assert f"renderer: html {html.VERSION}" in lines
    assert f"stands for: {report['stands-for']}" in lines


def test_the_report_holds_each_read_of_the_browser_and_each_loss_of_the_renderer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = parts_project(tmp_path, warning=True)
    name_browser(root, write_program(tmp_path / "browser" / "chromium"))
    label = "figure/body/label"
    read = viewing_browser.Read(
        words=(viewing_browser.Differs("figure", label, (("Ready",),), ((("Rea",),),)),),
        dropped=(
            viewing_browser.Dropped("figure", label, "Ready", viewing_browser.NO_INK),
            viewing_browser.Dropped("figure", label, "Set", viewing_browser.OFF_THE_PAGE),
            viewing_browser.Dropped("figure", label, "Go", viewing_browser.CUT, 0.36322869955),
            viewing_browser.Dropped("figure", label, "Go", viewing_browser.COVERED, 0.004),
            viewing_browser.Dropped("figure", label, ".", viewing_browser.COVERED, 1.0, True),
        ),
        no_face=(viewing_browser.NoFace("figure", label, "Ready", "Held", "700"),),
        machine_fonts=(viewing_browser.MachineFont("figure", label, "Ready", ("Times",)),),
        refused=("https://example.invalid/a.png",),
    )
    monkeypatch.setattr(viewing.viewing_browser, "draw", Browser(read))
    shown = run_look(root, "tags", "--renderer", "html")
    assert shown.returncode == 0, shown.stderr
    report = html_report(root, "tags")
    place = {
        "language": "en",
        "key": "default",
        viewing.FORCED: None,
        "page": "figure",
        "element": label,
    }
    assert report["words"] == [{**place, "scene": [["Ready"]], "document": [[["Rea"]]]}]
    assert report["dropped"] == [
        {**place, "text": "Ready", "why": "no ink"},
        {**place, "text": "Set", "why": "off the page"},
        {**place, "text": "Go", "why": "cut", "share": 0.363},
        {**place, "text": "Go", "why": "covered", "share": 0.004},
        {**place, "text": ".", "why": "covered", "share": 1.0, "island": True},
    ]
    assert report["drawn-otherwise"] == [
        {**place, "text": "Ready", "why": "no face", "family": "Held", "weight": "700"},
        {**place, "text": "Ready", "why": "font of the machine", "fonts": ["Times"]},
    ]
    assert report["refused"] == [
        {
            "language": "en",
            "key": "default",
            viewing.FORCED: None,
            "url": "https://example.invalid/a.png",
        }
    ]
    [loss] = report["losses"]
    assert (loss["plugin"], loss["what"], loss["did"]) == ("html", label, "left-out")
    lines = shown.stdout.splitlines()
    assert any(each.startswith("words: figure (en, default): the text `") for each in lines)
    span = "dropped: figure (en, default): a span of the text `figure/body/label`"
    assert [each for each in lines if each.startswith(span)] == [
        f"{span} left no ink: 'Ready'",
        f"{span} lies off its page: 'Set'",
        f"{span} is cut by its page's edge, past which 36% of its ink lies: 'Go'",
        f"{span} is covered by a part over it, which hides under 1% of its ink: 'Go'",
        f"{span} is covered by a part over it, which hides 100% of its ink"
        " (one island of it gone, such as a dot): '.'",
    ]
    assert any(each.endswith("a font of the machine: 'Ready'") for each in lines)
    assert any("has no face of Held at weight 700" in each for each in lines)
    assert "refused: en, default: a request for https://example.invalid/a.png" in lines
    assert any(each.startswith("loss: figure (en, default): ") for each in lines)


# --- the report's schema (DEC-062, Implications) -------------------------------------------------
#
# Each report a look of this module writes holds to it (`reports_hold_their_schema`). These
# show that the schema names every key the report carries, and keeps each renderer's apart.


def refused_of(report: Mapping[str, Any]) -> str:
    """What the report's schema refuses in `report`, one refusal a line; empty where it
    holds."""
    return "\n".join(viewing.files.shape_problems(report, LOOK_REPORT))


def without(held: Mapping[str, Any], key: str) -> dict[str, Any]:
    return {each: value for each, value in held.items() if each != key}


def test_the_schema_names_every_key_of_the_report_and_refuses_another(flow: Path) -> None:
    assert run_look(flow, PIECE).returncode == 0
    report = report_of(flow)
    [image] = report["images"]
    check, reach = next(iter(report["reaches"].items()))
    assert refused_of(report) == ""
    unexpected = "'unknown' was unexpected"
    assert unexpected in refused_of({**report, "unknown": True})
    assert unexpected in refused_of({**report, "images": [{**image, "unknown": True}]})
    assert unexpected in refused_of({**report, "reaches": {check: {**reach, "unknown": True}}})
    for key in ("capability", "reaches", "on-no-image", "dropped", "losses"):
        assert f"'{key}' is a required property" in refused_of(without(report, key))
    for key in ("findings", "measured-by", "not-measured", "on-white"):
        held = {**report, "images": [without(image, key)]}
        assert f"'{key}' is a required property" in refused_of(held)


def test_the_schema_keeps_the_keys_of_each_renderer_s_report_apart(
    tmp_path: Path, browser: Browser
) -> None:
    root = html_flow(tmp_path)
    assert run_look(root, PIECE).returncode == 0
    assert run_look(root, PIECE, "--renderer", "html").returncode == 0
    through_svg, through_html = report_of(root), html_report(root)
    assert refused_of(through_svg) == refused_of(through_html) == ""
    [svg_image], [html_image] = through_svg["images"], through_html["images"]
    assert "'stopped' was unexpected" in refused_of({**through_svg, "stopped": None})
    assert "'profiles' was unexpected" in refused_of({**through_html, "profiles": []})
    assert refused_of({**through_svg, "images": [{**svg_image, viewing.FORCED: None}]})
    assert refused_of({**through_html, "images": [{**html_image, viewing.ON_WHITE: False}]})
    renamed = {**through_svg, "renderer": {**through_svg["renderer"], "name": viewing.HTML}}
    assert "'stopped' is a required property" in refused_of(renamed)


def test_the_schema_holds_each_entry_the_svg_renderer_drops_to_the_fields_of_its_cause(
    flow: Path,
) -> None:
    """A text or run the tool drew nothing of gives `whole`, and a cut or covered span gives
    `share`, with `island` only as true; neither gives the other's (DEC-045 point 2)."""
    assert run_look(flow, PIECE).returncode == 0
    report = report_of(flow)
    place = {"language": "en", "key": "default", "page": "page", "element": "page/text"}
    drew_none = {**place, "text": "Go", "why": viewing_tool.NO_INK, "whole": True}
    in_part = {**place, "text": "Go", "why": viewing_tool.COVERED, "share": 0.5}

    def refused(*entries: Mapping[str, Any]) -> str:
        return refused_of({**report, "dropped": list(entries)})

    assert refused(drew_none, in_part, {**in_part, viewing.ISLAND: True}) == ""
    assert refused({**drew_none, "share": 0.5})
    assert refused({**drew_none, viewing.ISLAND: True})
    assert refused(without(drew_none, "whole"))
    assert refused(without(in_part, "share"))
    assert refused({**in_part, "whole": False})
    assert refused({**in_part, viewing.ISLAND: False})
    assert "'why' is a required property" in refused(without(in_part, "why"))


def test_the_schema_holds_each_entry_the_html_renderer_drops_to_the_fields_of_its_cause(
    tmp_path: Path, browser: Browser
) -> None:
    """A cut or covered span gives `share`, with `island` only as true, and an entry of another
    cause gives neither (DEC-037 point 2, DEC-054 point 3)."""
    root = html_flow(tmp_path)
    assert run_look(root, PIECE, "--renderer", "html").returncode == 0
    report = html_report(root)
    place = {
        "language": "en",
        "key": "default",
        viewing.FORCED: None,
        "page": "page",
        "element": "page/text",
    }
    no_ink = {**place, "text": "Go", "why": viewing_browser.NO_INK}
    in_part = {**place, "text": "Go", "why": viewing_browser.COVERED, "share": 0.5}

    def refused(*entries: Mapping[str, Any]) -> str:
        return refused_of({**report, "dropped": list(entries)})

    assert refused(no_ink, in_part, {**in_part, viewing.ISLAND: True}) == ""
    assert refused({**no_ink, "share": 0.5})
    assert refused({**no_ink, viewing.ISLAND: True})
    assert refused(without(in_part, "share"))
    assert refused({**in_part, viewing.ISLAND: False})


# --- the modes a page file holds (DEC-023 point 6) -----------------------------------------------

DARK_KEY = "colour-scheme.dark"

#: The signals of each key of `flow`, as the HTML renderer's declaration pairs them.
LIGHT_SIGNALS = {"prefers-color-scheme": "light", "prefers-contrast": "no-preference"}
DARK_SIGNALS = {**LIGHT_SIGNALS, "prefers-color-scheme": "dark"}


def emulated_after_the_file(program: Path) -> list[dict[str, str]]:
    """The signals each emulation set once the stand-in opened the page file."""
    messages = logged(program)
    methods = [each.get("method") for each in messages]
    after = messages[len(methods) - 1 - methods[::-1].index("Page.navigate") :]
    return [
        {each["name"]: each["value"] for each in message["params"]["features"]}
        for message in after
        if message.get("method") == "Emulation.setEmulatedMedia"
    ]


def test_every_key_of_a_file_is_drawn_from_one_start_with_its_signals_set_and_no_reload(
    tmp_path: Path,
) -> None:
    root = drawing_project(tmp_path, picture=False)
    program = browser_for(root, tmp_path, PIECE, {"flow.en.default.html": "en"})
    shown = run_look(root, PIECE, "--renderer", "html", "--every-key")
    assert shown.returncode == 0, shown.stderr
    assert len([each for each in logged(program) if "flags" in each]) == 1
    opened = [each["url"].rsplit("/", 1)[-1] for each in called(program, "Page.navigate")]
    assert opened == [viewing_browser.PLANTED_FILE, "flow.en.default.html"]
    assert emulated_after_the_file(program) == [LIGHT_SIGNALS, DARK_SIGNALS]
    assert [image["key"] for image in html_report(root)["images"]] == ["default", DARK_KEY]


def test_a_key_asked_alone_is_drawn_out_of_the_file_that_holds_its_group(
    tmp_path: Path, browser: Browser
) -> None:
    """The file is the renderer's, named by the first key it serves and holding each."""
    root = html_flow(tmp_path)
    shown = run_look(root, PIECE, "--renderer", "html", "--key", DARK_KEY)
    assert shown.returncode == 0, shown.stderr
    [call] = browser.calls
    assert call["name"] == f"{PIECE}.en.default.html"
    assert call["bytes"] == page_file_of(root, PIECE, "en", DARK_KEY)
    assert call["modes"] == [DARK_SIGNALS]
    assert call["signals"] == {
        "prefers-color-scheme": ("light", "dark"),
        "prefers-contrast": ("no-preference", "more"),
    }
    report = html_report(root)
    assert [image["key"] for image in report["images"]] == [DARK_KEY]
    assert [entry["keys"] for entry in report["page-files"]] == [["default", DARK_KEY]]
    assert sorted(path.name for path in html_folder(root).iterdir()) == [
        f"{PIECE}.en.{DARK_KEY}.frames.json",
        f"{PIECE}.en.{DARK_KEY}.png",
        f"{PIECE}.en.default.html",
        viewing.REPORT,
    ]


def test_a_text_with_no_ink_in_one_key_alone_is_reported_in_that_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = html_flow(tmp_path)
    label = "figure/body/steps[plan]/head"
    dim = viewing_browser.Read(
        (),
        (viewing_browser.Dropped("figure", label, "Plan the work.", viewing_browser.NO_INK),),
        (),
        (),
        (),
    )
    clean = viewing_browser.Read((), (), (), (), ())
    monkeypatch.setattr(
        viewing.viewing_browser,
        "draw",
        Browser(lambda mode: dim if mode["prefers-color-scheme"] == "dark" else clean),
    )
    shown = run_look(root, PIECE, "--renderer", "html", "--every-key")
    assert shown.returncode == 0, shown.stderr
    assert [(each["key"], each["element"]) for each in html_report(root)["dropped"]] == [
        (DARK_KEY, label)
    ]


def a_dark_picture_of_its_own(root: Path) -> None:
    """`flow` whose picture takes another file in dark, as a producer can give it."""
    folder = root / PIECE_FOLDER / "produced" / OUTPUT
    (folder / f"{DARK_KEY}.png").write_bytes(producer.png(100, 100, (0, 0, 255, 255)))


def test_a_loss_in_one_key_of_a_file_is_reported_in_that_key_and_accepted_by_plugin_and_what(
    tmp_path: Path, browser: Browser
) -> None:
    root = html_flow(tmp_path)
    a_dark_picture_of_its_own(root)
    shown = run_look(root, PIECE, "--renderer", "html", "--every-key")
    assert shown.returncode == 0, shown.stderr
    [loss] = html_report(root)["losses"]
    assert (loss["key"], loss["plugin"], loss["did"], loss["accepted"]) == (
        DARK_KEY,
        "html",
        "approximated",
        False,
    )
    assert f"`{DARK_KEY}` takes another" in loss["why"]
    assert any(
        each.startswith(f"loss: {loss['page']} (en, {DARK_KEY}): ")
        for each in shown.stdout.splitlines()
    )
    piece = root / PIECE_FOLDER / "piece.yaml"
    accepted = f"accept-losses:\n  - plugin: html\n    what: {loss['what']}\n    reason: Known.\n"
    piece.write_text(piece.read_text(encoding="utf-8") + accepted, encoding="utf-8")
    assert run_look(root, PIECE, "--renderer", "html", "--every-key").returncode == 0
    assert [each["accepted"] for each in html_report(root)["losses"]] == [True]


def test_an_image_of_a_page_with_no_ground_is_said_to_lie_on_the_browsers_own_ground(
    tmp_path: Path, browser: Browser
) -> None:
    root = html_flow(tmp_path)
    on_white(root)
    shown = run_look(root, PIECE, "--renderer", "html", "--key", DARK_KEY)
    assert shown.returncode == 0, shown.stderr
    [image] = html_report(root)["images"]
    assert image[viewing.ON_BROWSER_GROUND] is True
    assert viewing.ON_WHITE not in image
    assert (
        f"on the browser's ground: {image['page']} (en, {DARK_KEY}) draws no ground of its own, "
        f"so it lies on Chrome's own ground in `{DARK_KEY}`, not on white"
    ) in shown.stdout.splitlines()


def test_an_image_of_a_page_with_a_ground_says_nothing_of_the_browsers(
    tmp_path: Path, browser: Browser
) -> None:
    root = html_flow(tmp_path)
    shown = run_look(root, PIECE, "--renderer", "html")
    assert shown.returncode == 0, shown.stderr
    [image] = html_report(root)["images"]
    assert image[viewing.ON_BROWSER_GROUND] is False
    assert "on the browser's ground" not in shown.stdout


# --- under forced colours (DEC-027) --------------------------------------------------------------

FORCED = viewing.ASK_FORCED

#: The emulation of each forced palette, in the order a forced start draws them.
PALETTE_MODES = [
    {**palette.signals, **viewing_browser.FORCED} for palette in viewing_browser.PALETTES
]


def every_image(root: Path, piece: str = PIECE) -> list[str]:
    """Each image of the HTML renderer's folder, at its path within it."""
    folder = html_folder(root, piece)
    return sorted(path.relative_to(folder).as_posix() for path in folder.rglob("*.png"))


def test_forced_colours_draw_each_page_file_in_both_palettes_after_its_keys(
    tmp_path: Path, browser: Browser
) -> None:
    """The caller's key picks the file; each palette picks the key it shows: the light one the
    light key, the dark one the dark key."""
    root = html_flow(tmp_path)
    shown = run_look(root, PIECE, "--renderer", "html", FORCED)
    assert shown.returncode == 0, shown.stderr
    plain, forced = browser.calls
    assert plain["name"] == forced["name"] == f"{PIECE}.en.default.html"
    assert plain["modes"] == [LIGHT_SIGNALS] and plain["palettes"] == []
    assert forced["modes"] == PALETTE_MODES and forced["palettes"] == ["light", "dark"]
    assert forced["scale"] == plain["scale"] and forced["signals"] == plain["signals"]
    report = html_report(root)
    assert [(each["key"], each[viewing.FORCED], each["image"]) for each in report["images"]] == [
        ("default", None, f"{PIECE}.en.default.png"),
        ("default", "light", f"forced-light/{PIECE}.en.default.png"),
        (DARK_KEY, "dark", f"forced-dark/{PIECE}.en.{DARK_KEY}.png"),
    ]
    assert every_image(root) == sorted(each["image"] for each in report["images"])
    frames = json.loads(
        (html_folder(root) / f"forced-dark/{PIECE}.en.{DARK_KEY}.frames.json").read_text(
            encoding="utf-8"
        )
    )
    assert (frames["key"], frames[viewing.FORCED]) == (DARK_KEY, "dark")
    assert frames["image"] == f"forced-dark/{PIECE}.en.{DARK_KEY}.png"


def test_the_report_names_the_forced_palettes_their_flag_their_folders_and_what_they_miss(
    tmp_path: Path, browser: Browser
) -> None:
    root = html_flow(tmp_path)
    shown = run_look(root, PIECE, "--renderer", "html", FORCED)
    assert shown.returncode == 0, shown.stderr
    said = html_report(root)[viewing.FORCED]
    assert said["palettes"] == ["light", "dark"]
    assert said["flag"] == viewing_browser.FORCING == "--force-high-contrast"
    assert said["folders"] == {"light": "forced-light/", "dark": "forced-dark/"}
    assert said["does-not-show"].startswith(
        "each forced image shows Chrome 157.0.1.2's own forced palette, not a reader's own, "
    )
    folder = f"{viewing.folder_of(PIECE, 'html')}/"
    lines = shown.stdout.splitlines()
    assert (
        f"forced colours: light, dark, forced by Chrome's flag `--force-high-contrast`; their "
        f"images lie in {folder}forced-light/, {folder}forced-dark/"
    ) in lines
    assert f"forced colours do not show: {said['does-not-show']}" in lines


def test_a_run_that_asks_for_no_forced_colours_draws_none_and_names_none(
    tmp_path: Path, browser: Browser
) -> None:
    root = html_flow(tmp_path)
    shown = run_look(root, PIECE, "--renderer", "html", "--every-key")
    assert shown.returncode == 0, shown.stderr
    assert [call["palettes"] for call in browser.calls] == [[]]
    report = html_report(root)
    assert report[viewing.FORCED] is None
    assert {each[viewing.FORCED] for each in report["images"]} == {None}
    assert not [path for path in html_folder(root).iterdir() if path.is_dir()]
    assert "forced" not in shown.stdout


def test_a_forced_run_replaces_the_forced_folders_an_earlier_run_left(
    tmp_path: Path, browser: Browser
) -> None:
    root = html_flow(tmp_path)
    assert run_look(root, PIECE, "--renderer", "html", FORCED).returncode == 0
    assert run_look(root, PIECE, "--renderer", "html").returncode == 0
    assert every_image(root) == [f"{PIECE}.en.default.png"]


@pytest.mark.parametrize(
    ("args", "default"),
    [
        pytest.param(["--renderer", "svg"], False, id="named"),
        pytest.param([], True, id="by-default"),
    ],
)
def test_forced_colours_of_the_svg_renderer_are_refused_with_its_folder_as_it_was(
    flow: Path, browser: Browser, args: list[str], default: bool
) -> None:
    assert run_look(flow, PIECE, "--renderer", "svg").returncode == 0
    before = written(flow)
    shown = run_look(flow, PIECE, *args, FORCED)
    assert shown.returncode == 1
    assert shown.stderr.startswith(
        "error: resvg draws the SVG renderer's pages and knows no forced colours, so "
        "`--forced-colours` draws only the HTML renderer's"
    )
    way_on = f"`pkit visual look {PIECE} --renderer html --forced-colours`"
    assert (way_on in shown.stderr) == default
    assert written(flow) == before
    assert browser.calls == []


@pytest.mark.parametrize(
    ("palette", "key"),
    [
        ("light", "contrast.high"),
        ("dark", "colour-scheme.dark+contrast.high"),
    ],
)
def test_each_forced_palette_shows_the_key_a_file_of_both_value_axes_holds_for_it(
    tmp_path: Path, palette: str, key: str
) -> None:
    root = starter_project(tmp_path)
    project = viewing.opened(root, "tag")
    held = dict(zip(project.keys, project.combinations, strict=True))
    signals = next(each.signals for each in viewing_browser.PALETTES if each.name == palette)
    declared = seam.declaration("html", seam.RENDERER)
    assert viewing.key_shown(declared, "html", held, signals) == key


@pytest.mark.parametrize(
    ("held", "shown"),
    [
        pytest.param(
            {"default": {"colour-scheme": "light"}, "dark": {"colour-scheme": "dark"}},
            ["default", "dark"],
            id="two-schemes",
        ),
        pytest.param(
            {"default": {"colour-scheme": "dark"}}, ["default", "default"], id="one-scheme"
        ),
        pytest.param(
            {"default": {"contrast": "standard"}, "high": {"contrast": "high"}},
            ["high", "high"],
            id="contrast-alone",
        ),
        pytest.param({"default": {}}, ["default", "default"], id="no-value-axis"),
    ],
)
def test_a_file_shows_each_forced_palette_the_key_its_rules_give_those_signals(
    held: dict[str, dict[str, str]], shown: list[str]
) -> None:
    declared = seam.declaration("html", seam.RENDERER)
    assert [
        viewing.key_shown(declared, "html", held, palette.signals)
        for palette in viewing_browser.PALETTES
    ] == shown


def test_the_command_names_the_forced_palette_wherever_it_names_a_forced_image(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = html_flow(tmp_path)
    label = "figure/body/steps[plan]/head"
    dim = viewing_browser.Read(
        (),
        (viewing_browser.Dropped("figure", label, "Plan the work.", viewing_browser.NO_INK),),
        (),
        (),
        ("https://example.invalid/a.png",),
    )
    clean = viewing_browser.Read((), (), (), (), ())
    drawn = Browser(lambda mode: dim if mode.get("prefers-color-scheme") == "dark" else clean)
    monkeypatch.setattr(viewing.viewing_browser, "draw", drawn)
    monkeypatch.setattr(viewing.viewing_browser, "draw_forced", drawn.forced)
    shown = run_look(root, PIECE, "--renderer", "html", FORCED)
    assert shown.returncode == 0, shown.stderr
    report = html_report(root)
    assert [(each["key"], each[viewing.FORCED]) for each in report["dropped"]] == [
        (DARK_KEY, "dark")
    ]
    assert [each[viewing.FORCED] for each in report["refused"]] == ["dark"]
    lines = shown.stdout.splitlines()
    assert (
        f"dropped: figure (en, {DARK_KEY}, forced dark): a span of the text `{label}` left no "
        f"ink: 'Plan the work.'"
    ) in lines
    assert (
        f"refused: en, {DARK_KEY}, forced dark: a request for https://example.invalid/a.png"
    ) in lines


def test_a_loss_of_the_key_a_forced_palette_shows_lies_on_its_image(
    tmp_path: Path, browser: Browser
) -> None:
    """The dark key is not asked for, yet the dark palette shows it, with its loss."""
    root = html_flow(tmp_path)
    a_dark_picture_of_its_own(root)
    shown = run_look(root, PIECE, "--renderer", "html", FORCED)
    assert shown.returncode == 0, shown.stderr
    [loss] = html_report(root)["losses"]
    assert (loss["key"], loss[viewing.FORCED], loss["did"]) == (DARK_KEY, "dark", "approximated")
    assert any(
        each.startswith(f"loss: {loss['page']} (en, {DARK_KEY}, forced dark): ")
        for each in shown.stdout.splitlines()
    )


def test_a_forced_image_of_a_page_with_no_ground_lies_on_its_palettes_ground(
    tmp_path: Path, browser: Browser
) -> None:
    root = html_flow(tmp_path)
    on_white(root)
    shown = run_look(root, PIECE, "--renderer", "html", FORCED)
    assert shown.returncode == 0, shown.stderr
    images = html_report(root)["images"]
    assert [each[viewing.ON_BROWSER_GROUND] for each in images] == [True, True, True]
    lines = shown.stdout.splitlines()
    assert (
        f"on the forced palette's ground: {images[1]['page']} (en, default, forced light) draws "
        f"no ground of its own, so it lies on the ground of Chrome's `light` forced palette"
    ) in lines
    assert not [each for each in lines if "on the browser's ground" in each and "forced" in each]


def test_a_stop_of_the_forced_start_leaves_no_image_and_names_a_run_without_forced_colours(
    tmp_path: Path, browser: Browser
) -> None:
    root = html_flow(tmp_path)
    what = (
        "the first read set the forced palette `light`, and a span with no paint, left to "
        "forcing, left no ink, so the forced palette did not reach the text"
    )
    browser.stops[2] = viewing_browser.Stopped(what, program="b")
    shown = run_look(root, PIECE, "--renderer", "html", FORCED)
    assert shown.returncode == look.STOPPED
    assert every_image(root) == []
    stop = html_report(root)["stopped"]
    assert stop["what"] == what and stop["forcing"] is True
    assert stop["go-on"] == viewing.ways_on(PIECE, True)
    assert stop["go-on"][:-1] == viewing.ways_on(PIECE)
    assert stop["go-on"][-1] == (
        f"`pkit visual look {PIECE} --renderer html`, without `--forced-colours`, draws the "
        f"same page files in their own colours, in a start that forces none"
    )
    assert [line for line in shown.stderr.splitlines() if line.startswith("go on: ")] == [
        f"go on: {way}" for way in stop["go-on"]
    ]


def test_a_stop_of_the_plain_start_of_a_forced_run_names_no_run_without_them(
    tmp_path: Path, browser: Browser
) -> None:
    root = html_flow(tmp_path)
    browser.stops[1] = viewing_browser.Stopped("the browser stopped", program="b")
    shown = run_look(root, PIECE, "--renderer", "html", FORCED)
    assert shown.returncode == look.STOPPED
    assert len(browser.calls) == 1
    stop = html_report(root)["stopped"]
    assert stop["forcing"] is False and stop["go-on"] == viewing.ways_on(PIECE)


def test_a_forced_run_starts_the_browser_again_for_a_file_forcing_its_colours(
    tmp_path: Path,
) -> None:
    """Through the stand-in's pipe: the file's own start, then one under the flag, whose first
    read is its own and whose every emulation forces the colours."""
    root = drawing_project(tmp_path, picture=False)
    program = browser_for(root, tmp_path, PIECE, {"flow.en.default.html": "en"})
    shown = run_look(root, PIECE, "--renderer", "html", FORCED)
    assert shown.returncode == 0, shown.stderr
    starts = [each["flags"] for each in logged(program) if "flags" in each]
    assert [viewing_browser.FORCING in flags for flags in starts] == [False, True]
    opened = [each["url"].rsplit("/", 1)[-1] for each in called(program, "Page.navigate")]
    assert opened == [
        viewing_browser.PLANTED_FILE,
        "flow.en.default.html",
        viewing_browser.PLANTED_FORCED_FILE,
        "flow.en.default.html",
    ]
    assert emulated_after_the_file(program) == PALETTE_MODES
    assert [(each["key"], each[viewing.FORCED]) for each in html_report(root)["images"]] == [
        ("default", None),
        ("default", "light"),
        (DARK_KEY, "dark"),
    ]


# --- a page too tall for one image, in bands, and one too wide (DEC-022 point 7) -----------------


#: How many steps a phone's page holds, one card each, so it is some 5,000 px tall.
PHONE_STEPS = 91

#: A phone's width, which the test brand's figure takes in a test of bands.
PHONE_WIDTH = 390

#: The piece's own column: its steps down one column, each a card of the `tests` library,
#: a space apart, as a phone shows a page.
COLUMN = bound(
    "component",
    status="experimental",
    about="The steps of a flow down one column, as a phone shows them.",
    fields={
        "type": "object",
        "required": ["steps"],
        "properties": {"steps": {"type": "array", "items": {"type": "object"}}},
    },
    parts={
        "down": {
            "repeat": "steps",
            "draw": "tests/card",
            "width": "=:width",
            "column": {"gap": "=@space.3"},
        }
    },
    preferred={"height": "=down.bottom"},
)


def figure_width(root: Path, width: float) -> None:
    """The test brand's figure made `width` px wide, in the project's copy of its tokens."""
    tokens = root / BRAND_TOKENS
    held = json.loads(tokens.read_text(encoding="utf-8"))
    held["size"]["figure"]["$value"]["value"] = width
    tokens.write_text(json.dumps(held), encoding="utf-8")


def tall_page(tmp_path: Path, steps: int = PHONE_STEPS, **fields: Any) -> Path:
    """`flow` without its picture, a page as wide as a phone and some 5,000 px tall: its body
    the piece's own column of `steps` cards, each head a line of the body's 16 px text, under
    the test brand 1.0.0 and the released foundations. `fields` are the piece's own."""
    root = drawing_project(tmp_path, picture=False, **fields)
    figure_width(root, PHONE_WIDTH)
    write(root / PIECE_FOLDER / "components" / "column.yaml", yaml_text(COLUMN))
    heads = [{"id": f"s{number}", "head": f"Step {number}."} for number in range(1, steps + 1)]
    write_content(root, body={"use": "piece/column", "steps": heads})
    return root


@pytest.fixture
def tall(tmp_path: Path) -> Path:
    return tall_page(tmp_path)


def page_of(root: Path) -> Mapping[str, Any]:
    """The one page `flow` has in English, as its scene holds it."""
    [page] = viewing.pages_of(scene_of(root, PIECE, "en"))
    return page


def bands_of(report: Mapping[str, Any], key: str = "default") -> list[dict[str, Any]]:
    """Each band of the report's images in `key`, in the report's order."""
    return [image["band"] for image in report["images"] if image["key"] == key]


def frames_of(root: Path, image: Mapping[str, Any], renderer: str = "svg") -> dict[str, Any]:
    folder = folder_of(root) if renderer == "svg" else html_folder(root)
    return json.loads((folder / image["frames"]).read_text(encoding="utf-8"))


def test_the_tall_page_is_a_phone_s_some_5000_px_tall_with_16_px_text(tall: Path) -> None:
    page = page_of(tall)
    assert page["width"] == PHONE_WIDTH
    assert 4900 < page["height"] < 5100
    assert viewing._smallest_text(page) == 16


def test_a_page_too_tall_for_one_image_is_drawn_in_bands_none_past_the_long_edge(
    tall: Path,
) -> None:
    shown = run_look(tall, PIECE)
    assert shown.returncode == 0, shown.stderr
    report = report_of(tall)
    images = report["images"]
    assert len(images) > 1
    assert [image["band"]["number"] for image in images] == list(range(1, len(images) + 1))
    assert {image["band"]["of"] for image in images} == {len(images)}
    assert [image["image"] for image in images] == [
        f"flow.en.default.band-{number}.png" for number in range(1, len(images) + 1)
    ]
    for image in images:
        assert max(image["pixels"].values()) <= viewing.LONG_EDGE
        assert (folder_of(tall) / image["image"]).is_file()
        assert frames_of(tall, image)["band"] == image["band"]


def test_its_bands_share_one_scale_at_which_its_smallest_text_reads_each_as_wide_as_the_page(
    tall: Path,
) -> None:
    assert run_look(tall, PIECE).returncode == 0
    page, images = page_of(tall), report_of(tall)["images"]
    scale = viewing.page_scale(page)
    assert scale * 16 >= viewing.SMALLEST_TEXT
    for image in images:
        assert image["pixels"] == {
            "width": viewing.pixels(PHONE_WIDTH, scale),
            "height": viewing.pixels(image["band"]["height"], scale),
        }
        assert frames_of(tall, image)["elements"][0]["width"] == image["pixels"]["width"]


def test_the_bands_cover_the_page_each_overlapping_the_next_by_its_tallest_line(
    tall: Path,
) -> None:
    assert run_look(tall, PIECE).returncode == 0
    page, bands = page_of(tall), bands_of(report_of(tall))
    tallest = viewing._tallest_line(page)
    assert tallest == 16 * 1.4
    assert bands[0]["top"] == 0
    assert bands[-1]["top"] + bands[-1]["height"] == pytest.approx(page["height"])
    for above, below in itertools.pairwise(bands):
        assert above["top"] < below["top"]
        assert round(above["top"] + above["height"] - below["top"], 2) >= tallest


def covering(page: Mapping[str, Any], y: float) -> list[str]:
    """The drawn elements of `page` whose frame covers `y`, but a box over the whole page."""
    width, height = float(page["width"]), float(page["height"])
    return [
        element["id"]
        for element, left, top in viewing._placed(page)
        if element.get("type") != "group"
        and not (
            element.get("type") == "box"
            and left <= 0
            and top <= 0
            and left + float(element["width"]) >= width
            and top + float(element["height"]) >= height
        )
        and top <= y <= top + float(element["height"])
    ]


def test_a_cut_falls_in_a_gap_between_elements_where_its_overlap_holds_one(tall: Path) -> None:
    """The cards stand a space apart. One overlap of the page holds such a gap, and one lies
    on a card alone, where the cut crosses it."""
    assert run_look(tall, PIECE).returncode == 0
    page, bands = page_of(tall), bands_of(report_of(tall))
    held = []
    for above, below in itertools.pairwise(bands):
        cut = above["top"] + above["height"]
        steps = range(math.ceil(below["top"] * 10), math.floor(cut * 10) + 1)
        gap = any(covering(page, step / 10) == [] for step in steps)
        assert (covering(page, cut) == []) == gap
        held.append(gap)
    assert sorted(held) == [False, True]


def test_the_svg_and_the_html_renderer_s_pages_are_cut_alike(tmp_path: Path) -> None:
    root = tall_page(tmp_path, exports=["svg", "html"])
    assert run_look(root, PIECE, "--renderer", "svg").returncode == 0
    program = browser_for(root, tmp_path, PIECE, {"flow.en.default.html": "en"})
    shown = run_look(root, PIECE, "--renderer", "html")
    assert shown.returncode == 0, shown.stderr
    through_svg, through_html = report_of(root), html_report(root)
    assert bands_of(through_html) == bands_of(through_svg)
    scale = viewing.page_scale(page_of(root))
    [start] = [each["flags"] for each in logged(program) if "flags" in each]
    assert f"--force-device-scale-factor={scale:g}" in start
    assert drawn_clips(program) == [
        {"x": 0.0, "y": band["top"], "width": PHONE_WIDTH, "height": band["height"], "scale": 1}
        for band in bands_of(through_svg)
    ]
    assert [image["image"] for image in through_html["images"]] == [
        f"flow.en.default.band-{band['number']}.png" for band in bands_of(through_svg)
    ]


def drawn_clips(program: Path) -> list[dict[str, Any]]:
    """The clips a stand-in browser drew the file's images by, in its first mode: those taken
    after it opened the file, and before its reads of what the page shows of each span."""
    messages = logged(program)
    methods = [each.get("method") for each in messages]
    after = messages[len(methods) - 1 - methods[::-1].index("Page.navigate") :]
    first_style = next(
        index
        for index, each in enumerate(after)
        if each.get("method") == "Runtime.evaluate"
        and each["params"]["expression"].startswith(f"({viewing_browser.STYLE})")
    )
    return [
        each["params"]["clip"]
        for each in after[:first_style]
        if each.get("method") == "Page.captureScreenshot"
    ]


def test_beside_each_band_lie_the_frames_of_what_it_shows_in_its_own_pixels(tall: Path) -> None:
    """An element in an overlap, or across a cut, is framed in each band it shows in."""
    assert run_look(tall, PIECE).returncode == 0
    page, images = page_of(tall), report_of(tall)["images"]
    placed = {element["id"]: (element, top) for element, _, top in viewing._placed(page)}
    held = [frames_of(tall, image) for image in images]
    for image, frames in zip(images, held, strict=True):
        band, down = image["band"], image["pixels"]["height"] / image["band"]["height"]
        [whole, *shown] = frames["elements"]
        assert whole["id"] == page["id"]
        assert whole["y"] == round(-band["top"] * down, 2)
        for frame in shown:
            element, top = placed[frame["id"]]
            bottom = top + float(element["height"])
            assert top < band["top"] + band["height"] and bottom > band["top"]
            assert frame["y"] == round((top - band["top"]) * down, 2)
        inside = [
            name
            for name, (element, top) in placed.items()
            if band["top"] <= top and top + float(element["height"]) <= band["top"] + band["height"]
        ]
        assert set(inside) <= {frame["id"] for frame in shown}
    [first, second, *_] = [{frame["id"] for frame in each["elements"]} for each in held]
    across = {"figure/body", "figure/body/down"}
    in_both = first & second
    assert across < in_both
    assert any(name.endswith("/head") for name in in_both)


def test_a_text_drawn_to_nothing_on_a_page_in_bands_is_reported_once(tall: Path) -> None:
    """Every head is clear, those in an overlap among them."""
    tokens = tall / BRAND_TOKENS
    held = json.loads(tokens.read_text(encoding="utf-8"))
    held["text-primary"]["$value"] = {"colorSpace": "srgb", "components": [0, 0, 0], "alpha": 0}
    tokens.write_text(json.dumps(held), encoding="utf-8")
    shown = run_look(tall, PIECE)
    assert shown.returncode == 0, shown.stderr
    report = report_of(tall)
    heads = [each["element"] for each in report["dropped"] if each["element"].endswith("/head")]
    assert sorted(heads) == sorted({*heads})
    assert len(heads) == PHONE_STEPS
    first, second = (frames_of(tall, image) for image in report["images"][:2])
    in_both = {frame["id"] for frame in first["elements"]} & {
        frame["id"] for frame in second["elements"]
    }
    assert any(name in in_both for name in heads)


def test_the_report_lists_each_page_s_bands_in_order_and_the_run_prints_them(
    tmp_path: Path,
) -> None:
    root = tall_page(tmp_path)
    shown = run_look(root, PIECE, "--every-key")
    assert shown.returncode == 0, shown.stderr
    images = report_of(root)["images"]
    count = images[0]["band"]["of"]
    assert [(image["key"], image["band"]["number"]) for image in images] == [
        (key, number) for key in ("default", "colour-scheme.dark") for number in range(1, count + 1)
    ]
    lines = shown.stdout.splitlines()
    for key in ("default", "colour-scheme.dark"):
        names = ", ".join(f"flow.en.{key}.band-{number}.png" for number in range(1, count + 1))
        assert f"bands: figure (en, {key}): {count}, top to bottom: {names}" in lines


def test_a_page_too_wide_for_its_smallest_text_to_read_is_drawn_as_wide_as_the_long_edge(
    tmp_path: Path,
) -> None:
    root = drawing_project(tmp_path, picture=False)
    figure_width(root, 5000)
    shown = run_look(root, PIECE)
    assert shown.returncode == 0, shown.stderr
    [image] = report_of(root)["images"]
    assert image["pixels"]["width"] == viewing.LONG_EDGE
    assert image[viewing.TOO_WIDE] is True
    assert "band" not in image
    assert (
        f"too wide: figure (en, default) is drawn {viewing.LONG_EDGE} pixels wide, so its "
        f"smallest text may not read"
    ) in shown.stdout.splitlines()


def test_a_page_too_wide_through_a_browser_is_said_so_too(tmp_path: Path, browser: Browser) -> None:
    root = drawing_project(tmp_path, picture=False, exports=["html"])
    figure_width(root, 5000)
    name_browser(root, write_program(tmp_path / "browser" / "chromium"))
    assert run_look(root, PIECE).returncode == 0
    [call] = browser.calls
    assert call["scale"] == math.floor(viewing.LONG_EDGE / 5000 * 1000) / 1000
    assert all(image[viewing.TOO_WIDE] for image in html_report(root)["images"])


def test_a_page_that_fits_one_image_is_drawn_whole_as_before(
    flow: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    asked: list[dict[str, Any]] = []
    real = viewing_tool.resvg_py.svg_to_bytes

    def asking(**given: Any) -> bytes:
        asked.append(given)
        return real(**given)

    monkeypatch.setattr(viewing_tool.resvg_py, "svg_to_bytes", asking)
    assert run_look(flow, PIECE).returncode == 0
    [image] = report_of(flow)["images"]
    assert image["image"] == "flow.en.default.png"
    assert "band" not in image and viewing.TOO_WIDE not in image
    assert "band" not in frames_of(flow, image)
    assert asked[0]["width"] == viewing.LONG_EDGE
    assert "preserveAspectRatio" not in asked[0]["svg_string"].split(">", 1)[0]


# --- bands, as computed (DEC-022 point 7) ------------------------------------------------------


def column_page(height: float, *boxes: tuple[float, float], line: float = 22.4) -> dict[str, Any]:
    """A page of a phone's width and `height`, on a ground, holding a box from each top to
    each bottom `boxes` give, and a text whose lines are `line` px tall."""
    ground = element("box", "page/ground", x=0, y=0, width=PHONE_WIDTH, height=height)
    held = [
        element("box", f"page/box-{at}", x=16, y=top, width=358, height=bottom - top)
        for at, (top, bottom) in enumerate(boxes)
    ]
    said = element("text", "page/said", x=16, y=0, width=358, height=line, **{"line-height": line})
    page = element(
        "group", "page", x=0, y=0, width=PHONE_WIDTH, height=height, page=True, children=[]
    )
    page["children"] = [ground, said, *held]
    return page


def test_a_page_whose_height_fits_is_one_region_of_the_whole_page() -> None:
    page = column_page(2000.0)
    assert viewing.bands(page, viewing.LONG_EDGE / 2000) == (viewing.Region(0.0, 2000.0),)


def test_bands_are_of_about_one_height_none_past_the_long_edge() -> None:
    page = column_page(5000.0, (0, 5000))
    found = viewing.bands(page, 0.625)
    heights = [band.height for band in found]
    assert len(found) == 3
    assert max(viewing.pixels(each, 0.625) for each in heights) <= viewing.LONG_EDGE
    assert min(heights) > max(heights) * 0.95


def test_with_no_gap_in_its_overlap_a_band_ends_at_the_overlap_s_bottom() -> None:
    """The overlap is the page's tallest line, so its bottom is where a band of the height
    asked for ends."""
    page = column_page(5000.0, (0, 5000))
    first, second, *_ = viewing.bands(page, 0.625)
    asked = (5000 + 2 * 22.4) / 3
    assert first.height == pytest.approx(asked, abs=0.01)
    assert first.height - second.top == pytest.approx(22.4, abs=0.01)


def test_a_band_ends_in_the_middle_of_the_lowest_gap_its_overlap_holds() -> None:
    asked = (5000 + 2 * 22.4) / 3
    page = column_page(5000.0, (0, asked - 20), (asked - 15, asked - 5), (asked - 2, 5000))
    first, *_ = viewing.bands(page, 0.625)
    assert first.height == pytest.approx(asked - 3.5, abs=0.01)
    assert covering(page, first.height) == []


def test_a_ground_over_the_whole_page_closes_no_gap() -> None:
    asked = (5000 + 2 * 22.4) / 3
    page = column_page(5000.0, (0, asked - 10), (asked, 5000))
    first, *_ = viewing.bands(page, 0.625)
    assert first.height == pytest.approx(asked - 5, abs=0.01)


def test_an_overlap_takes_a_quarter_of_a_band_at_most() -> None:
    """A line as tall as a band still moves each band on down the page."""
    page = column_page(5000.0, (0, 5000), line=3000)
    found = viewing.bands(page, 0.625)
    most = math.floor(viewing.LONG_EDGE / 0.625 * 100) / 100
    for above, below in itertools.pairwise(found):
        assert above.top < below.top
        assert above.top + above.height - below.top == pytest.approx(
            most * viewing.MOST_OVERLAP, abs=0.01
        )
    assert found[-1].top + found[-1].height == pytest.approx(5000)


# --- what fills an export's facts (DEC-016 point 5) ---------------------------------------------


def test_a_look_fills_this_clones_next_number_as_a_preview_does(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = stamped(tmp_path, "number")
    exported_up_to(root, 41)
    taken = filled(monkeypatch, pl)
    shown = run_look(root, PIECE)
    assert shown.returncode == 0, shown.stderr
    assert [facts.version for facts in taken] == ["v42"]
    assert "stand-in" not in shown.stdout


def test_a_final_pieces_look_takes_the_stand_ins_and_says_so_after_the_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = stamped(tmp_path, "date", state="final")
    on_white(root)
    taken = filled(monkeypatch, pl)
    shown = run_look(root, PIECE)
    assert shown.returncode == 0, shown.stderr
    assert taken == [pl.read_piece_file(root, "visual", PIECE).stand_ins]
    *_, reported, said, report = shown.stdout.splitlines()
    assert reported.startswith("on white: ")
    assert said == (
        "look: a final piece has no next export, so a stand-in shows: `date` at `figure/body/date`"
    )
    assert report.startswith("report: ")


def test_the_pages_listed_are_computed_as_a_preview_fills_them(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = stamped(tmp_path, "number")
    exported_up_to(root, 41)
    taken = filled(monkeypatch, pl)
    assert run_pages(root, PIECE).returncode == 0
    assert [facts.version for facts in taken] == ["v42"]


# --- `pkit visual pages` ------------------------------------------------------------------------


def run_pages(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return run_main(pages, *args, cwd=root)


def test_it_lists_the_languages_the_keys_the_pages_and_each_renderers_tool(
    tmp_path: Path,
) -> None:
    root = starter_project(tmp_path)
    program = name_browser(root, write_program(tmp_path / "browser" / "chromium"))
    shown = run_pages(root, "tag")
    assert shown.returncode == 0, shown.stderr
    lines = shown.stdout.splitlines()
    assert lines[0] == "languages: en, de (by default en)"
    assert lines[1] == (
        "keys: default, colour-scheme.dark, contrast.high, colour-scheme.dark+contrast.high "
        "(by default default)"
    )
    assert lines[2] == "pages in en:"
    assert lines[3].startswith("  1: deck/slides[")
    tool_line = viewing_tool.TOOL
    assert lines[-4:] == [
        "renderer: svg by default",
        f"tool of svg: resvg {tool_line['version']}, through resvg-py {tool_line['wheel']}",
        f"tool of html: a browser, named in the configuration: {program}",
        "forced palettes of html: light, dark, drawn where `look` is asked `--forced-colours`",
    ]


def test_it_lists_a_document_for_a_machine(tmp_path: Path) -> None:
    root = starter_project(tmp_path)
    program = name_browser(root, write_program(tmp_path / "browser" / "chromium"))
    shown = run_pages(root, "--json", "tag")
    assert shown.returncode == 0, shown.stderr
    listed = json.loads(shown.stdout)
    assert listed["drawn-by-default"] == {"language": "en", "key": "default"}
    assert sorted(listed["pages"]) == ["de", "en"]
    assert len(listed["pages"]["en"]) == 2
    assert listed["renderer"] == "svg"
    assert listed["tools"] == {
        "svg": viewing_tool.TOOL,
        "html": {
            "program": str(program),
            "named": True,
            "looked": [],
            "forced-palettes": ["light", "dark"],
        },
    }


def test_it_starts_no_browser(tmp_path: Path) -> None:
    """It finds the browser as a run would, and so names no version."""
    root = starter_project(tmp_path)
    program = name_browser(root, write_program(tmp_path / "browser" / "chromium"))
    assert run_pages(root, "tag").returncode == 0
    assert not (program.parent / "started").exists()


def test_it_says_where_it_looked_where_no_browser_is_found(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = starter_project(tmp_path)
    no_browser_here(tmp_path, monkeypatch)
    shown = run_pages(root, "--json", "tag")
    assert shown.returncode == 0, shown.stderr
    found = json.loads(shown.stdout)["tools"]["html"]
    assert found["program"] is None and found["named"] is False
    assert str(tmp_path / "no-browser") in found["looked"]
    assert found["forced-palettes"] == ["light", "dark"]
    plain = run_pages(root, "tag").stdout.splitlines()[-2]
    assert plain.startswith(
        "tool of html: none, so a run stops: no browser of the Chromium family was found; "
        "looked at: "
    )


@pytest.mark.parametrize(("formats", "renderer"), [(["html"], "html"), (["svg"], "svg")])
def test_it_reads_through_the_html_renderer_by_default_a_piece_that_declares_it(
    tmp_path: Path, formats: list[str], renderer: str
) -> None:
    root = drawing_project(tmp_path, picture=False, exports=formats)
    shown = run_pages(root, "--json", PIECE)
    assert shown.returncode == 0, shown.stderr
    assert json.loads(shown.stdout)["renderer"] == renderer


def test_it_lists_each_key_of_a_piece_on_a_size_axis(tmp_path: Path) -> None:
    root = on_devices(tmp_path, languages=["en", "cs"])
    write_content(root, "cs", body=two_steps("Naplánovat."))
    listed = json.loads(run_pages(root, "--json", PIECE).stdout)
    assert listed["keys"] == ["default", PHONE]
    assert listed["drawn-by-default"] == {"language": "en", "key": "default"}
    assert listed["pages"] == {"en": ["figure"], "cs": ["figure"]}


def test_it_only_reads(tmp_path: Path) -> None:
    root = starter_project(tmp_path)
    before = written(root)
    assert run_pages(root, "tag").returncode == 0
    assert written(root) == before


def test_a_piece_with_no_lock_lists_nothing_naming_render(tmp_path: Path) -> None:
    root = drawing_project(tmp_path, lock=None)
    shown = run_pages(root, PIECE)
    assert shown.returncode == 1
    assert "`pkit visual render flow`" in shown.stderr


def test_a_configuration_that_names_no_browser_is_refused(tmp_path: Path) -> None:
    root = starter_project(tmp_path)
    write_config(root, "browser: 3\n")
    shown = run_pages(root, "tag")
    assert shown.returncode == 1
    assert "records `browser: 3`, which names no program" in shown.stderr
