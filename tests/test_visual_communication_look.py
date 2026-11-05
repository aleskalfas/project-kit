"""`pkit visual look <piece>` and `pkit visual pages <piece>` (visual-communication DEC-015):
the viewing step's tool, what it reports of text drawn to nothing, the images, frames and
report it writes, and what it refuses. Run in this process, the SVG renderer standing in for
the import a run makes when it draws.

No test here holds a pixel as a contract (DEC-015 point 6). One compares two drawings of one
run, or asks whether an image is blank, and so runs on any machine and any tool."""

from __future__ import annotations

import json
import shutil
import struct
import subprocess
from collections.abc import Iterator, Mapping
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
    PIECE,
    PIECE_FOLDER,
    drawing_project,
    parts_project,
    write_picture,
)
from tests.test_visual_communication_starter import PIECES, STARTER, TEST_NOTATION, UNRELEASED
from tests.test_visual_communication_svg import COLOURS, FONT, SEMIBOLD, element, line, run, scene
from tests.visual_communication_project import (
    FOUNDATIONS,
    TEST_BRAND,
    copy_library,
    importable,
    project,
    write_list,
    yaml_text,
)

look, pages, svg, seam, framing, viewing, viewing_tool = load(
    "visual-communication",
    "look.py",
    "pages.py",
    "plugins.svg",
    "plugins.seam",
    "framing",
    "viewing",
    "viewing_tool",
)

LOCK = ["foundations 1.0.0", "test-brand 1.0.0", "tests 1.0.0"]
CODE = TEST_BRAND / "fonts" / "SourceCodePro-Regular.ttf"
BRAND_TOKENS = "visual/libraries/test-brand/1.0.0/tokens/base.tokens.json"


@pytest.fixture(autouse=True)
def plugins(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """The renderer stands in for the import a run makes when it draws, and the test
    producer is registered, for the length of the test."""
    importable(monkeypatch, svg)
    producer.register(seam)
    yield
    seam.unregister(producer.NAME)
    seam.unregister("svg")


def run_look(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return run_main(look, *args, cwd=root)


def folder_of(root: Path, piece: str = PIECE) -> Path:
    return root / viewing.FOLDER / piece


def report_of(root: Path, piece: str = PIECE) -> dict[str, Any]:
    return json.loads((folder_of(root, piece) / viewing.REPORT).read_text(encoding="utf-8"))


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
    return viewing_tool.draw(drawn_page(*children, **sizes), long_edge, tmp_path)


def dropped_of(
    tmp_path: Path, *children: dict[str, Any], **sizes: Any
) -> list[tuple[str, str, bool]]:
    return [
        (each.element, each.text, each.whole) for each in tool(tmp_path, *children, **sizes).dropped
    ]


# --- the tool: an image, and the faces handed over ----------------------------------------------


def test_a_page_is_drawn_at_the_long_edge_asked_for_with_each_face_handed_over(
    tmp_path: Path,
) -> None:
    said = text_element("figure/said", run("Say it", fill="ink"))
    drawn = tool(tmp_path, said, long_edge=800)
    assert (drawn.width, drawn.height) == (800, 400)
    assert drawn.image != blank(drawn.image)
    assert drawn.dropped == ()
    assert [path.suffix for path in tmp_path.iterdir()] == [".font"]


def test_a_tall_page_takes_the_long_edge_on_its_height(tmp_path: Path) -> None:
    said = text_element("figure/said", run("Say it", fill="ink"))
    drawn = tool(tmp_path, said, width=100, height=200, long_edge=800)
    assert (drawn.width, drawn.height) == (400, 800)


def test_a_page_that_draws_no_ground_lies_on_white(tmp_path: Path) -> None:
    drawn = tool(tmp_path, long_edge=800)
    assert drawn.image == blank(drawn.image)


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
    drawn = tool(tmp_path, width=2, height=1, long_edge=16384)
    assert (drawn.width, drawn.height) == (16384, 8192)


@pytest.mark.parametrize(("width", "height"), [(960, 0), (0, 540), (0, 0)])
def test_a_page_with_no_size_fails_naming_it(tmp_path: Path, width: int, height: int) -> None:
    with pytest.raises(viewing_tool.ToolFailed, match=f"{width} by {height} px"):
        tool(tmp_path, width=width, height=height)


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
    found = viewing_tool.draw(page.svg, 800, tmp_path).dropped
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
        pictures={"red": picture},
    )
    [page] = drawn.pages
    faces = tmp_path / "faces"
    faces.mkdir()
    assert viewing_tool.draw(page.svg, 800, faces).dropped == ()


def test_a_white_text_on_white_was_drawn(tmp_path: Path) -> None:
    said = text_element("figure/said", run("Seen by nobody", fill="surface"))
    assert dropped_of(tmp_path, said) == []


def test_a_text_inside_moved_groups_is_found_where_it_stands(tmp_path: Path) -> None:
    said = text_element("figure/group/said", run("Say it", fill="ink"), x=0, y=0)
    inner = element("group", "figure/group", x=20, y=30, width=50, height=30, children=[said])
    outer = element("group", "figure/outer", x=5, y=260, width=50, height=30, children=[inner])
    assert dropped_of(tmp_path, outer, width=200, height=400) == []


def test_a_line_that_lies_off_the_page_drew_nothing(tmp_path: Path) -> None:
    said = text_element("figure/said", run("Below it", fill="ink"), y=500)
    assert dropped_of(tmp_path, said) == [("figure/said", "Below it", True)]


# --- what a run draws (DEC-015 point 5) ---------------------------------------------------------


@pytest.fixture
def flow(tmp_path: Path) -> Path:
    """The piece `flow` in both colour schemes, with its picture."""
    root = drawing_project(tmp_path)
    write_picture(root, framing)
    return root


def starter_project(tmp_path: Path) -> Path:
    """The starter, the test brand and notation, and the starter's reference pieces, which
    hold more than one page, two languages and four keys."""
    root = project(tmp_path)
    copy_library(root, FOUNDATIONS, "foundations", "1.0.0")
    copy_library(root, STARTER, "starter", "1.0.0")
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


def test_the_long_edge_rises_where_a_page_s_smallest_text_would_land_under_what_reads() -> None:
    def page(width: float, size: float) -> dict[str, Any]:
        small = {"paragraphs": [[{"font-size": size}]]}
        return {"width": width, "height": width / 2, "children": [small]}

    assert viewing.long_edge(page(1280, 16)) == 1568
    assert viewing.long_edge({"width": 300, "height": 200}) == 1568
    assert viewing.long_edge(page(5000, 16)) == 3125


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
    tokens = flow / BRAND_TOKENS
    held = json.loads(tokens.read_text(encoding="utf-8"))
    held["background"]["$value"] = {"colorSpace": "srgb", "components": [1, 1, 1], "alpha": 0}
    tokens.write_text(json.dumps(held), encoding="utf-8")
    shown = run_look(flow, PIECE)
    assert shown.returncode == 0, shown.stderr
    [image] = report_of(flow)["images"]
    assert image["on-white"] is True
    assert "on white: figure (en, default) draws no ground of its own" in shown.stdout.splitlines()


def test_the_report_names_the_lock_and_the_tool(flow: Path) -> None:
    assert run_look(flow, PIECE).returncode == 0
    report = report_of(flow)
    assert report["lock"] == {"foundations": "1.0.0", "test-brand": "1.0.0", "tests": "1.0.0"}
    assert report["tool"] == viewing_tool.TOOL
    assert report["tool"]["name"] == "resvg"


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
        {**place, "element": "figure/body/label", "text": "Ready", "whole": True}
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
    (root / PIECE_FOLDER / "exports.yaml").write_text("versions: []\n", encoding="utf-8")
    before = written(root)
    shown = run_look(root, PIECE)
    assert shown.returncode == 1
    assert "`pkit visual render flow`" in shown.stderr
    assert shown.stderr.startswith(
        "error: the lock of visual/pieces/flow/piece.yaml cannot be drawn"
    )
    assert written(root) == before


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
    def failing(_svg: str, _edge: int, _folder: Path) -> Any:
        raise viewing_tool.ToolFailed("Failed to create pixmap")

    monkeypatch.setattr(viewing.viewing_tool, "draw", failing)
    shown = run_look(flow, PIECE)
    assert shown.returncode == 1
    assert shown.stderr == (
        "error: the tool cannot draw page figure of `flow`: Failed to create pixmap. "
        "`pkit visual check flow` names what the piece still owes\n"
    )
    assert not folder_of(flow).exists()


# --- `pkit visual pages` ------------------------------------------------------------------------


def run_pages(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return run_main(pages, *args, cwd=root)


def test_it_lists_the_languages_the_keys_the_pages_and_the_tool(tmp_path: Path) -> None:
    root = starter_project(tmp_path)
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
    assert lines[-1] == (
        f"tool: resvg {tool_line['version']}, through resvg-py {tool_line['wheel']}"
    )


def test_it_lists_a_document_for_a_machine(tmp_path: Path) -> None:
    root = starter_project(tmp_path)
    shown = run_pages(root, "--json", "tag")
    assert shown.returncode == 0, shown.stderr
    listed = json.loads(shown.stdout)
    assert listed["drawn-by-default"] == {"language": "en", "key": "default"}
    assert sorted(listed["pages"]) == ["de", "en"]
    assert len(listed["pages"]["en"]) == 2
    assert listed["tool"] == viewing_tool.TOOL


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
