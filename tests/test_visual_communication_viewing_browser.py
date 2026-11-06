"""The viewing step's browser (`_lib/viewing_browser.py`, visual-communication DEC-020 points 6
to 9): how it finds a browser, what one start asks of it, the four reads, the first read of a
page with planted faults, its bounds, and what a stop says.

A stand-in program speaks the pipe in the browser's place (`visual_communication_browser`), so
these tests need no browser. The one that starts a real browser skips where none is found, or
where a sandbox stops the one found. No test holds a pixel as a contract (DEC-015 point 6).
"""

from __future__ import annotations

import ast
import copy
import os
import sys
import time
from collections.abc import Iterator, Mapping, Sequence
from pathlib import Path
from typing import Any

import pytest

from tests.in_process import load
from tests.visual_communication_browser import (
    HELD_FONT,
    VERSION,
    called,
    logged,
    stand_in,
)

(viewing_browser,) = load("visual-communication", "viewing_browser")

MODULE = Path(str(viewing_browser.__file__))

#: The file a drawing reads, as the module opens it.
FILE = "page.html"

#: The font of the machine a stand-in draws in.
MACHINE_FONT = {"familyName": "Times", "isCustomFont": False, "glyphCount": 4}

WHITE, BLACK = viewing_browser.GROUNDS
DARK = (WHITE,)
FUNCTIONS = {
    "read": viewing_browser.READ,
    "ground": viewing_browser.GROUND,
    "alone": viewing_browser.ALONE,
}

#: What a sandbox's stop has made browsers say: Chrome and Chromium in a sandbox around them,
#: a headless shell whose own could not start, and Linux where unprivileged namespaces are off.
SANDBOX_WORDS = (
    "Failed to bind() /var/folders/T/com.google.Chrome.tT/SingletonSocket: "
    "Operation not permitted (1)",
    "sandbox initialization failed: Operation not permitted",
    "No usable sandbox! If you are running on Ubuntu 23.10+",
)


def span(text: str, index: int, **held: Any) -> dict[str, Any]:
    """A span as `READ` gives it, on the page's first rows, with what a stand-in adds."""
    return {
        "x": 10.0,
        "y": 10.0 + 20 * index,
        "width": 60.0,
        "height": 16.0,
        "index": index,
        "text": text,
        "family": "Held",
        "weight": "400",
        "face": True,
        "ink": DARK,
        **held,
    }


def page(id: str, width: float, height: float, *texts: Mapping[str, Any]) -> dict[str, Any]:
    return {"id": id, "x": 0.0, "y": 0.0, "width": width, "height": height, "texts": list(texts)}


def text(id: str, *lines: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    return {"id": id, "lines": [list(line) for line in lines]}


def as_scene(pages: Sequence[Mapping[str, Any]]) -> list[Any]:
    """The pages a caller asks for, from what the document holds of them."""
    return [
        viewing_browser.Page(
            held["id"],
            held["width"],
            held["height"],
            tuple(
                viewing_browser.Text(
                    each["id"],
                    tuple(tuple(one["text"] for one in line) for line in each["lines"]),
                )
                for each in held["texts"]
            ),
        )
        for held in pages
    ]


def one_page(*spans: Mapping[str, Any]) -> dict[str, Any]:
    """A document of one page, with a text of one line for each span."""
    texts = [text(f"text-{each['index']}", [each]) for each in spans]
    return {"pages": [page("page", 1280.0, 720.0, *texts)]}


def clean() -> dict[str, Any]:
    return one_page(span("hello", 0), span("world", 1))


def planted() -> dict[str, Any]:
    """The planted page as a browser reads it: each fault where the module planted it."""
    index = 0
    texts = []
    for element, lines in viewing_browser.PLANTED_TEXTS.items():
        drawn = []
        for line in lines:
            spans = []
            for planted_span in line:
                held = planted_span.family == viewing_browser.HELD and planted_span.weight == 400
                machine = planted_span.family != viewing_browser.HELD
                spans.append(
                    span(
                        planted_span.text,
                        index,
                        family=planted_span.family,
                        weight=str(planted_span.weight),
                        face=held,
                        x=float(planted_span.left),
                        fonts=[MACHINE_FONT if machine else HELD_FONT],
                        ink=() if planted_span.colour == viewing_browser.UNPAINTED else DARK,
                    )
                )
                index += 1
            drawn.append(spans)
        texts.append(text(element, *drawn))
    document = {
        "pages": [
            page(
                viewing_browser.PLANTED_ID,
                viewing_browser.PLANTED_WIDTH,
                viewing_browser.PLANTED_HEIGHT,
                *texts,
            )
        ],
        "requests": [viewing_browser.NETWORK, f"file:///folder/{viewing_browser.BESIDE}"],
    }
    by_text = {each["id"]: each for each in texts}
    by_text["character-the-face-lacks"]["lines"][0][0]["fonts"] = [HELD_FONT, MACHINE_FONT]
    by_text["run-swallowed"]["lines"][0][0]["text"] = "swal"
    by_text["colour-of-its-ground"]["lines"][0][0]["ink"] = (BLACK,)
    return document


def cured(document: dict[str, Any], finding: tuple[str, ...]) -> dict[str, Any]:
    """`document` with the fault behind `finding` gone, so the reads have nothing to name."""
    mended = copy.deepcopy(document)
    kind, about = finding[0], finding[1]
    if kind == viewing_browser.REFUSED:
        mended["requests"] = [each for each in mended["requests"] if not each.endswith(about)]
        return mended
    held = next(each for each in mended["pages"][0]["texts"] if each["id"] == about)
    spans = [each for line in held["lines"] for each in line]
    if kind == viewing_browser.WORDS:
        scene = next(each for each in viewing_browser.PLANTED_PAGE.texts if each.element == about)
        mended["pages"][0]["texts"].remove(held)
        mended["pages"][0]["texts"].append(
            text(about, *[[span(each, 0) for each in line] for line in scene.lines])
        )
    elif kind == viewing_browser.NO_INK:
        next(each for each in spans if each["text"] == finding[2])["ink"] = DARK
    elif kind == viewing_browser.OFF_THE_PAGE:
        spans[0]["x"] = 8.0
    elif kind == viewing_browser.NO_FACE:
        spans[0]["face"] = True
    else:
        spans[0]["fonts"] = [HELD_FONT]
    return mended


def plan(**changes: Any) -> dict[str, Any]:
    """A plan under which a stand-in draws `clean` with nothing to say."""
    documents = {viewing_browser.PLANTED_FILE: planted(), FILE: clean()}
    documents.update(changes.pop("documents", {}))
    return {"functions": FUNCTIONS, "documents": documents, **changes}


def drawn(
    tmp_path: Path, wanted: Sequence[Any] | None = None, scale: float = 2.0, **changes: Any
) -> tuple[Any, Path]:
    """What `draw` gives under `plan(**changes)`, and the stand-in that gave it."""
    program, pages = _started(tmp_path, wanted, changes)
    return viewing_browser.draw(_file(tmp_path), pages, scale, program, tmp_path / "local"), program


def stopped(
    tmp_path: Path, wanted: Sequence[Any] | None = None, **changes: Any
) -> tuple[Any, Path]:
    """The stop `draw` raises under `plan(**changes)`, and the stand-in that gave it."""
    program, pages = _started(tmp_path, wanted, changes)
    with pytest.raises(viewing_browser.Stopped) as stop:
        viewing_browser.draw(_file(tmp_path), pages, 2.0, program, tmp_path / "local")
    return stop.value, program


def _started(
    tmp_path: Path, wanted: Sequence[Any] | None, changes: dict[str, Any]
) -> tuple[Path, Sequence[Any]]:
    held = plan(**changes)
    program = stand_in(tmp_path / "program", held)
    return program, wanted or as_scene(held["documents"][FILE]["pages"])


def _file(tmp_path: Path) -> Path:
    return tmp_path / FILE


def ended(process: int) -> bool:
    """Whether `process` is gone, as far as a moment's wait shows: a child its parent left
    behind is taken up by the system."""
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        try:
            os.kill(process, 0)
        except ProcessLookupError:
            return True
        time.sleep(0.05)
    return False


# What the module rests on.


def test_the_module_imports_the_standard_library_and_the_renderers_declaration_alone() -> None:
    tree = ast.parse(MODULE.read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module == "_lib.plugins":
                names.update(f"{node.module}.{alias.name}" for alias in node.names)
            else:
                names.add(node.module or "")
    outside = {name for name in names if name.split(".")[0] not in sys.stdlib_module_names}
    assert outside == {"_lib.plugins.html_declaration"}


# `find`


def write_program(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/bin/sh\ntouch started\n", encoding="utf-8")
    path.chmod(0o755)
    return path


def test_find_takes_the_program_it_is_given(tmp_path: Path) -> None:
    program = write_program(tmp_path / "another browser")
    assert viewing_browser.find(program) == program


@pytest.mark.parametrize("runs", [False, True])
def test_find_refuses_a_path_that_is_no_program_that_runs(tmp_path: Path, runs: bool) -> None:
    path = tmp_path / "nothing"
    if runs:
        path.write_text("not a program", encoding="utf-8")
    with pytest.raises(viewing_browser.Stopped) as stop:
        viewing_browser.find(path)
    assert stop.value.looked == (str(path),)
    assert str(path) in str(stop.value)


def test_find_takes_the_first_place_that_holds_a_browser(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    second = write_program(tmp_path / "second")
    third = write_program(tmp_path / "third")
    places = (str(tmp_path / "first"), str(second), str(third))
    monkeypatch.setattr(viewing_browser, "PLACES", {sys.platform: places})
    assert viewing_browser.find() == second


def test_find_looks_on_the_path_after_the_places(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    program = write_program(tmp_path / viewing_browser.NAMES[-1])
    monkeypatch.setattr(viewing_browser, "PLACES", {sys.platform: (str(tmp_path / "none"),)})
    monkeypatch.setenv("PATH", str(tmp_path))
    assert viewing_browser.find() == program


def test_find_says_where_it_looked_when_it_finds_none(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(viewing_browser, "PLACES", {sys.platform: (str(tmp_path / "none"),)})
    monkeypatch.setenv("PATH", str(tmp_path))
    with pytest.raises(viewing_browser.Stopped) as stop:
        viewing_browser.find()
    assert str(tmp_path / "none") in stop.value.looked
    assert all(any(name in each for each in stop.value.looked) for name in viewing_browser.NAMES)
    assert str(tmp_path / "none") in str(stop.value)


def test_find_starts_nothing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    viewing_browser.find(write_program(tmp_path / "program"))
    assert not (tmp_path / "started").exists()


def test_the_places_are_where_chrome_and_chromium_install_themselves() -> None:
    for places in viewing_browser.PLACES.values():
        assert any("chrome" in place.lower() for place in places)
        assert any("chromium" in place.lower() for place in places)


# One start.


def test_one_start_serves_one_file_at_the_callers_scale_and_the_widest_page(
    tmp_path: Path,
) -> None:
    pages = [
        page("narrow", 400.5, 300.0, text("a", [span("a", 0)])),
        page("wide", 1280.0, 720.0, text("b", [span("b", 1)])),
    ]
    _, program = drawn(tmp_path, documents={FILE: {"pages": pages}}, scale=1.225)
    starts = [each["flags"] for each in logged(program) if "flags" in each]
    assert len(starts) == 1
    assert "--force-device-scale-factor=1.225" in starts[0]
    (window,) = [flag for flag in starts[0] if flag.startswith("--window-size=")]
    assert window.split("=")[1].split(",")[0] == "1280"


def test_a_program_whose_path_holds_spaces_starts(tmp_path: Path) -> None:
    held = plan()
    program = stand_in(tmp_path / "Google Chrome.app", held)
    scene = as_scene(held["documents"][FILE]["pages"])
    drawing = viewing_browser.draw(tmp_path / FILE, scene, 1.0, program, tmp_path / "local")
    assert drawing.browser == VERSION


def test_it_says_which_browser_drew_with_its_version(tmp_path: Path) -> None:
    drawing, _ = drawn(tmp_path)
    assert drawing.browser == VERSION


def test_it_reads_the_planted_page_before_the_file(tmp_path: Path) -> None:
    _, program = drawn(tmp_path)
    opened = [each["url"].rsplit("/", 1)[-1] for each in called(program, "Page.navigate")]
    assert opened == [viewing_browser.PLANTED_FILE, FILE]


def test_it_draws_each_page_by_a_clip_as_the_file_stands(tmp_path: Path) -> None:
    pages = [
        {**page("one", 1280.0, 720.0, text("a", [span("a", 0)])), "x": 0.0},
        {**page("two", 800.0, 1100.0, text("b", [span("b", 1)])), "x": 240.0, "y": 744.0},
    ]
    drawing, program = drawn(tmp_path, documents={FILE: {"pages": pages}})
    assert [(each.page, each.width, each.height) for each in drawing.images] == [
        ("one", 2560, 1440),
        ("two", 1600, 2200),
    ]
    messages = logged(program)
    methods = [each.get("method") for each in messages]
    file_opened = len(methods) - 1 - methods[::-1].index("Page.navigate")
    after = messages[file_opened:]
    first_ground = next(
        index
        for index, each in enumerate(after)
        if each.get("method") == "Runtime.evaluate"
        and each["params"]["expression"].startswith(f"({viewing_browser.GROUND})")
    )
    clips = [
        each["params"]["clip"]
        for each in after[:first_ground]
        if each.get("method") == "Page.captureScreenshot"
    ]
    assert clips == [
        {"x": 0.0, "y": 0.0, "width": 1280.0, "height": 720.0, "scale": 1},
        {"x": 240.0, "y": 744.0, "width": 800.0, "height": 1100.0, "scale": 1},
    ]


def test_a_page_asked_for_alone_is_read_alone(tmp_path: Path) -> None:
    pages = [
        page("one", 1280.0, 720.0, text("a", [span("a", 0, ink=())])),
        page("two", 1280.0, 720.0, text("b", [span("b", 1)])),
    ]
    wanted = as_scene(pages[1:])
    drawing, _ = drawn(tmp_path, wanted, documents={FILE: {"pages": pages}})
    assert [each.page for each in drawing.images] == ["two"]
    assert drawing.read.dropped == ()


def test_a_page_the_file_does_not_hold_stops_the_drawing(tmp_path: Path) -> None:
    wanted = [viewing_browser.Page("elsewhere", 1280.0, 720.0, ())]
    stop, _ = stopped(tmp_path, wanted)
    assert "`elsewhere`" in stop.what


def test_a_page_of_another_size_than_the_scenes_stops_the_drawing(tmp_path: Path) -> None:
    wanted = [viewing_browser.Page("page", 1000.0, 720.0, ())]
    stop, _ = stopped(tmp_path, wanted)
    assert "measures 1280 by 720 px" in stop.what


# The words.


def words(tmp_path: Path, document: Mapping[str, Any], scene: Sequence[Any]) -> Any:
    return drawn(tmp_path, scene, documents={FILE: document})[0].read.words


def scene_page(*texts: Any) -> Any:
    return viewing_browser.Page("page", 1280.0, 720.0, tuple(texts))


def test_a_document_that_matches_the_scene_reports_no_difference(tmp_path: Path) -> None:
    drawing, _ = drawn(tmp_path)
    assert drawing.read == viewing_browser.Read((), (), (), (), ())


@pytest.mark.parametrize(
    "lines",
    [
        (("first", "second"),),
        (("first",),),
        (("second", "first"),),
        (("first", "second", "third"),),
        (("first",), ("second",)),
        (("first", "seco"),),
    ],
    ids=["same", "a-span-gone", "out-of-order", "a-span-added", "another-line", "a-run-cut"],
)
def test_each_texts_spans_are_matched_in_order_and_in_number(
    tmp_path: Path, lines: tuple[tuple[str, ...], ...]
) -> None:
    held = text("a", [span("first", 0), span("second", 1)])
    document = {"pages": [page("page", 1280.0, 720.0, held)]}
    found = words(tmp_path, document, [scene_page(viewing_browser.Text("a", lines))])
    if lines == (("first", "second"),):
        assert found == ()
    else:
        assert found == (viewing_browser.Differs("page", "a", lines, ((("first", "second"),),)),)


def test_a_text_the_document_does_not_hold_is_reported(tmp_path: Path) -> None:
    wanted = viewing_browser.Text("gone", (("words",),))
    document = {"pages": [page("page", 1280.0, 720.0)]}
    assert words(tmp_path, document, [scene_page(wanted)]) == (
        viewing_browser.Differs("page", "gone", (("words",),), ()),
    )


def test_a_text_the_scene_does_not_hold_is_reported(tmp_path: Path) -> None:
    document = {"pages": [page("page", 1280.0, 720.0, text("stray", [span("words", 0)]))]}
    assert words(tmp_path, document, [scene_page()]) == (
        viewing_browser.Differs("page", "stray", (), ((("words",),),)),
    )


def test_two_elements_of_one_trace_id_are_reported(tmp_path: Path) -> None:
    twice = [text("a", [span("words", 0)]), text("a", [span("words", 1)])]
    document = {"pages": [page("page", 1280.0, 720.0, *twice)]}
    wanted = viewing_browser.Text("a", (("words",),))
    assert words(tmp_path, document, [scene_page(wanted)]) == (
        viewing_browser.Differs("page", "a", (("words",),), ((("words",),), (("words",),))),
    )


# Ink.


def dropped(tmp_path: Path, *spans: Mapping[str, Any]) -> Any:
    return drawn(tmp_path, documents={FILE: one_page(*spans)})[0].read.dropped


def test_a_span_that_changes_nothing_left_no_ink(tmp_path: Path) -> None:
    assert dropped(tmp_path, span("seen", 0), span("gone", 1, ink=())) == (
        viewing_browser.Dropped("page", "text-1", "gone", viewing_browser.NO_INK),
    )


@pytest.mark.parametrize("ink", [(WHITE,), (BLACK,), (WHITE, BLACK)], ids=["dark", "light", "mid"])
def test_a_span_that_shows_on_either_ground_was_drawn(tmp_path: Path, ink: tuple[str, ...]) -> None:
    assert dropped(tmp_path, span("shown", 0, ink=ink)) == ()


def test_a_span_with_no_ink_is_read_on_both_grounds(tmp_path: Path) -> None:
    _, program = drawn(tmp_path, documents={FILE: one_page(span("gone", 0, ink=()))})
    expressions = [each["expression"] for each in called(program, "Runtime.evaluate")]
    grounds = [each for each in expressions if each.startswith(f"({viewing_browser.GROUND})")]
    assert [WHITE in each for each in grounds[-2:]] == [True, False]
    assert [BLACK in each for each in grounds[-2:]] == [False, True]


@pytest.mark.parametrize(
    "place",
    [{"x": 4000.0}, {"x": -500.0}, {"y": 800.0}, {"y": -100.0}],
    ids=["right", "left", "below", "above"],
)
def test_a_span_outside_the_page_is_reported(tmp_path: Path, place: dict[str, float]) -> None:
    assert dropped(tmp_path, span("away", 0, **place)) == (
        viewing_browser.Dropped("page", "text-0", "away", viewing_browser.OFF_THE_PAGE),
    )


def test_a_span_partly_on_the_page_is_read_for_ink(tmp_path: Path) -> None:
    assert dropped(tmp_path, span("half", 0, x=1250.0)) == ()


def test_a_span_with_an_empty_box_left_no_ink(tmp_path: Path) -> None:
    assert dropped(tmp_path, span("empty", 0, width=0.0, ink=())) == (
        viewing_browser.Dropped("page", "text-0", "empty", viewing_browser.NO_INK),
    )


@pytest.mark.parametrize("spaces", [" ", "   ", "\u00a0"])
def test_a_span_of_spaces_alone_is_not_read_for_ink(tmp_path: Path, spaces: str) -> None:
    assert dropped(tmp_path, span(spaces, 0, ink=())) == ()


def test_each_band_is_compared_with_itself_empty(tmp_path: Path) -> None:
    """A stand-in's picture differs by its clip, as a browser's pixels may, so a blank taken
    of another band would read as ink."""
    assert dropped(tmp_path, span("gone", 0, ink=()), span("gone too", 1, ink=())) == (
        viewing_browser.Dropped("page", "text-0", "gone", viewing_browser.NO_INK),
        viewing_browser.Dropped("page", "text-1", "gone too", viewing_browser.NO_INK),
    )


def test_a_band_stays_on_its_page(tmp_path: Path) -> None:
    held = page("page", 400.0, 100.0, text("a", [span("low", 0, y=90.0, height=16.0)]))
    held["x"], held["y"] = 240.5, 50.0
    held["texts"][0]["lines"][0][0].update({"x": 300.0, "y": 140.0})
    _, program = drawn(tmp_path, documents={FILE: {"pages": [held]}})
    clip = called(program, "Page.captureScreenshot")[-1]["clip"]
    assert clip == {"x": 240.5, "y": 124, "width": 400.0, "height": 26, "scale": 1}


# The font.


def test_a_span_with_no_loaded_face_is_reported_by_family_and_weight(tmp_path: Path) -> None:
    held = span("words", 0, family="Brand & Co", weight="700", face=False)
    document = one_page(held)
    assert drawn(tmp_path, documents={FILE: document})[0].read.no_face == (
        viewing_browser.NoFace("page", "text-0", "words", "Brand & Co", "700"),
    )


def test_a_span_with_no_characters_asks_for_no_face(tmp_path: Path) -> None:
    document = one_page(span("", 0, face=False, ink=()))
    assert drawn(tmp_path, documents={FILE: document})[0].read.no_face == ()


@pytest.mark.parametrize(
    "fonts", [[MACHINE_FONT], [HELD_FONT, MACHINE_FONT]], ids=["whole", "in-part"]
)
def test_a_span_drawn_in_a_font_of_the_machine_is_reported_with_that_font(
    tmp_path: Path, fonts: list[Mapping[str, Any]]
) -> None:
    document = one_page(span("words", 0, fonts=fonts))
    assert drawn(tmp_path, documents={FILE: document})[0].read.machine_fonts == (
        viewing_browser.MachineFont("page", "text-0", "words", ("Times",)),
    )


# Requests.


def test_each_request_but_the_files_own_and_a_data_address_is_refused_and_named(
    tmp_path: Path,
) -> None:
    asked = ["https://example.org/a.png", "data:image/png;base64,AAAA", "file:///beside.png"]
    document = {**clean(), "requests": asked}
    drawing, program = drawn(tmp_path, documents={FILE: document})
    assert drawing.read.refused == (asked[0], asked[2])
    assert len(called(program, "Fetch.failRequest")) == 4  # two on the planted page
    assert len(called(program, "Fetch.continueRequest")) == 3


def test_the_first_reads_requests_are_not_the_files(tmp_path: Path) -> None:
    assert drawn(tmp_path)[0].read.refused == ()


def test_each_request_is_held_from_before_a_page_opens(tmp_path: Path) -> None:
    _, program = drawn(tmp_path)
    methods = [each.get("method") for each in logged(program)]
    assert methods.index("Fetch.enable") < methods.index("Page.navigate")
    (held,) = called(program, "Fetch.enable")
    assert held["patterns"] == [{"urlPattern": "*"}]


# The first read.


def test_the_planted_page_holds_each_row_of_the_records_table() -> None:
    named = {finding[1] for finding in viewing_browser.PLANTED_FINDINGS}
    assert named >= {
        "no-paint-alone",
        "no-paint-between",
        "no-paint-beside",
        "off-the-page",
        "face-left-out",
        "face-broken",
        "weight-with-no-face",
        "character-the-face-lacks",
        "run-swallowed",
        "span-taken-out",
    }
    assert {"network.png", viewing_browser.BESIDE} <= named
    unnamed = set(viewing_browser.PLANTED_TEXTS) - named
    assert unnamed == {"clean", "under-a-later-box", "colour-of-its-ground"}


def test_the_planted_page_is_in_the_renderers_form() -> None:
    (html,) = load("visual-communication", "plugins.html")
    assert viewing_browser.PLANTED_SHEET == html.SHEET
    planted_html = viewing_browser._planted_html(b"a face")
    for mark in viewing_browser.MARKS.values():
        assert f" {mark}" in planted_html
    assert viewing_browser.LACKED in planted_html
    assert "swal<lowed" in planted_html


@pytest.mark.parametrize(
    "finding",
    sorted(viewing_browser.PLANTED_FINDINGS),
    ids=lambda finding: "-".join(finding[:2]).replace(" ", "-"),
)
def test_a_planted_fault_the_reads_do_not_name_stops_the_start(
    tmp_path: Path, finding: tuple[str, ...]
) -> None:
    document = cured(planted(), finding)
    stop, program = stopped(tmp_path, documents={viewing_browser.PLANTED_FILE: document})
    assert "did not name" in stop.what
    assert " ".join(finding) in stop.what
    assert "named" not in stop.what.split("did not name")[1]
    assert not [each for each in called(program, "Page.navigate") if each["url"].endswith(FILE)]


@pytest.mark.parametrize("element", ["face-left-out", "face-broken"])
def test_a_planted_span_of_the_machine_named_with_no_font_stops_the_start(
    tmp_path: Path, element: str
) -> None:
    document = planted()
    held = next(each for each in document["pages"][0]["texts"] if each["id"] == element)
    held["lines"][0][0]["fonts"] = [{"familyName": "", "isCustomFont": False}]
    stop, _ = stopped(tmp_path, documents={viewing_browser.PLANTED_FILE: document})
    assert f"{viewing_browser.MACHINE_FONT} {element}" in stop.what


@pytest.mark.parametrize(
    ("element", "change"),
    [
        ("clean", {"ink": ()}),
        ("under-a-later-box", {"ink": ()}),
        ("colour-of-its-ground", {"ink": ()}),
        ("clean", {"face": False}),
        ("clean", {"fonts": [MACHINE_FONT]}),
    ],
    ids=["clean-ink", "under-a-box", "ground", "clean-face", "clean-font"],
)
def test_a_read_that_names_what_is_clean_stops_the_start(
    tmp_path: Path, element: str, change: dict[str, Any]
) -> None:
    document = planted()
    held = next(each for each in document["pages"][0]["texts"] if each["id"] == element)
    held["lines"][0][0].update(change)
    stop, _ = stopped(tmp_path, documents={viewing_browser.PLANTED_FILE: document})
    assert "which the page does not plant" in stop.what
    assert element in stop.what


def test_a_first_read_with_no_face_to_embed_stops_the_start(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(viewing_browser, "PLANTED_FACE", tmp_path / "no face")
    stop, _ = stopped(tmp_path)
    assert "no page to read" in stop.what


# Bounds.


@pytest.fixture
def tight(monkeypatch: pytest.MonkeyPatch) -> None:
    """Bounds a test can wait out, past what a stand-in that runs takes to answer. Its start
    keeps its own, so a slow machine reaches the call a test strikes."""
    monkeypatch.setattr(viewing_browser, "CALL_SECONDS", 1.0)
    monkeypatch.setattr(viewing_browser, "CLOSE_SECONDS", 0.5)


@pytest.mark.usefixtures("tight")
@pytest.mark.parametrize(
    "fault",
    [
        {"method": "Target.createTarget"},
        {"method": "Page.navigate", "document": viewing_browser.PLANTED_FILE},
        {"method": "Page.navigate", "document": FILE},
        {"method": "Runtime.evaluate", "document": FILE},
        {"method": "CSS.getPlatformFontsForNode", "document": FILE},
        {"method": "Page.captureScreenshot", "document": FILE},
    ],
    ids=lambda fault: f"{fault['method']}-{fault.get('document', 'any')}",
)
def test_a_browser_that_hangs_on_a_call_counts_as_stopped_and_is_ended(
    tmp_path: Path, fault: dict[str, str]
) -> None:
    stop, program = stopped(tmp_path, fault={"kind": "hang", **fault})
    assert fault["method"] in stop.what and "was ended" in stop.what
    messages = logged(program)
    assert ended(messages[0]["process"])
    assert all(ended(each["helper"]) for each in messages if "helper" in each)


def test_a_browser_that_never_answers_is_bounded_by_its_start(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(viewing_browser, "START_SECONDS", 3.0)
    monkeypatch.setattr(viewing_browser, "CLOSE_SECONDS", 0.5)
    stop, program = stopped(tmp_path, fault={"kind": "hang", "method": "Browser.getVersion"})
    assert "Browser.getVersion" in stop.what and "was ended" in stop.what
    assert ended(logged(program)[0]["process"])


@pytest.mark.usefixtures("tight")
def test_a_load_that_never_comes_is_bounded(tmp_path: Path) -> None:
    fault = {"kind": "hang", "method": "Fetch.continueRequest", "document": FILE}
    stop, _ = stopped(tmp_path, fault=fault)
    assert "was ended" in stop.what


@pytest.mark.usefixtures("tight")
def test_a_browser_that_will_not_close_counts_as_stopped_and_is_ended(tmp_path: Path) -> None:
    stop, program = stopped(tmp_path, ignores_close=True)
    assert "did not close" in stop.what
    assert ended(logged(program)[0]["process"])


def test_a_browser_is_asked_to_close_outside_its_tab(tmp_path: Path) -> None:
    _, program = drawn(tmp_path)
    (close,) = [each for each in logged(program) if each.get("method") == "Browser.close"]
    assert "sessionId" not in close


def test_a_drawing_leaves_no_process_behind(tmp_path: Path) -> None:
    _, program = drawn(tmp_path)
    assert ended(logged(program)[0]["process"])


# A stop.


def test_a_browser_that_stops_at_once_says_what_it_said(tmp_path: Path) -> None:
    stop, program = stopped(tmp_path, says="I cannot start\n", exit=21)
    assert stop.program == str(program)
    assert stop.said == "I cannot start"
    assert "exit 21" in stop.what
    assert str(program) in str(stop) and "I cannot start" in str(stop)


def test_a_program_that_is_no_browser_stops_the_drawing(tmp_path: Path) -> None:
    stop, _ = stopped(tmp_path, fault={"kind": "garbage", "method": "Browser.getVersion"})
    assert "protocol" in stop.what


@pytest.mark.parametrize(
    "method", ["Page.captureScreenshot", "CSS.getPlatformFontsForNode", "DOM.getDocument"]
)
def test_a_browser_that_stops_part_way_gives_a_stop_and_no_image(
    tmp_path: Path, method: str
) -> None:
    fault = {"kind": "die", "method": method, "document": FILE, "says": "aw snap\n", "exit": 5}
    stop, _ = stopped(tmp_path, fault=fault)
    assert method in stop.what and "exit 5" in stop.what
    assert stop.said == "aw snap"


def test_a_call_the_browser_refuses_stops_the_drawing(tmp_path: Path) -> None:
    stop, _ = stopped(tmp_path, fault={"kind": "refuse", "method": "Page.captureScreenshot"})
    assert "Page.captureScreenshot" in stop.what and "not today" in stop.what


@pytest.mark.parametrize(
    "method", ["Browser.getVersion", "Target.attachToTarget", "Page.captureScreenshot"]
)
def test_an_answer_of_another_form_stops_the_drawing(tmp_path: Path, method: str) -> None:
    stop, _ = stopped(tmp_path, fault={"kind": "empty", "method": method})
    assert "cannot be read" in stop.what


def test_a_page_it_cannot_open_stops_the_drawing(tmp_path: Path) -> None:
    fault = {"kind": "error text", "method": "Page.navigate", "document": FILE}
    stop, _ = stopped(tmp_path, fault=fault)
    assert "ERR_FILE_NOT_FOUND" in stop.what


def test_a_read_that_throws_stops_the_drawing(tmp_path: Path) -> None:
    stop, _ = stopped(tmp_path, fault={"kind": "throw", "method": "Runtime.evaluate"})
    assert "no such thing" in stop.what


@pytest.mark.parametrize("words", SANDBOX_WORDS)
def test_a_browser_its_sandbox_stopped_is_told_apart(tmp_path: Path, words: str) -> None:
    stop, _ = stopped(tmp_path, says=words, exit=21)
    assert stop.sandbox


def test_a_browser_that_stopped_otherwise_is_not_said_to_be_sandboxed(tmp_path: Path) -> None:
    stop, _ = stopped(tmp_path, says="Trace/BPT trap: 5", exit=133)
    assert not stop.sandbox


def test_only_the_end_of_what_a_browser_said_is_kept(tmp_path: Path) -> None:
    words = "x" * (viewing_browser.SAID_LENGTH + 100) + "the end"
    stop, _ = stopped(tmp_path, says=words, exit=1)
    assert stop.said.endswith("the end")
    assert len(stop.said) == viewing_browser.SAID_LENGTH


# Its own sandbox.


def test_no_flag_touches_the_browsers_own_sandbox(tmp_path: Path) -> None:
    _, program = drawn(tmp_path)
    flags = logged(program)[0]["flags"]
    named = {flag.split("=")[0] for flag in flags}
    assert named == {
        *viewing_browser.FLAGS,
        "--user-data-dir",
        "--force-device-scale-factor",
        "--window-size",
        "about:blank",
    }
    assert not [
        flag for flag in flags if "sandbox" in flag.split("=")[0] or "zygote" in flag.split("=")[0]
    ]


# Its profile.


def profile_of(program: Path) -> Path:
    (flag,) = [each for each in logged(program)[0]["flags"] if each.startswith("--user-data-dir=")]
    return Path(flag.split("=", 1)[1])


def test_its_profile_is_a_throwaway_folder_under_the_one_named(tmp_path: Path) -> None:
    (tmp_path / "local").mkdir()
    (tmp_path / "local" / "kept").write_text("mine", encoding="utf-8")
    _, program = drawn(tmp_path)
    profile = profile_of(program)
    assert (tmp_path / "local") in profile.parents
    assert [each.name for each in (tmp_path / "local").iterdir()] == ["kept"]


def test_two_runs_share_no_profile(tmp_path: Path) -> None:
    _, first = drawn(tmp_path / "one")
    held = plan()
    second = stand_in(tmp_path / "two", held)
    viewing_browser.draw(
        tmp_path / FILE,
        as_scene(held["documents"][FILE]["pages"]),
        2.0,
        second,
        tmp_path / "one" / "local",
    )
    assert profile_of(first) != profile_of(second)


@pytest.mark.usefixtures("tight")
@pytest.mark.parametrize(
    "changes",
    [
        {"says": "no", "exit": 1},
        {"fault": {"kind": "hang", "method": "Page.navigate", "document": FILE}},
        {"fault": {"kind": "die", "method": "Page.captureScreenshot"}},
        {"documents": {viewing_browser.PLANTED_FILE: clean()}},
        {"ignores_close": True},
    ],
    ids=["exit", "hang", "died", "first-read", "close"],
)
def test_its_profile_is_removed_even_on_a_stop(tmp_path: Path, changes: dict[str, Any]) -> None:
    stopped(tmp_path, **changes)
    assert list((tmp_path / "local").iterdir()) == []


def test_the_folder_named_is_made_where_it_is_missing(tmp_path: Path) -> None:
    held = plan()
    program = stand_in(tmp_path / "program", held)
    scene = as_scene(held["documents"][FILE]["pages"])
    folder = tmp_path / "deep" / "er"
    viewing_browser.draw(tmp_path / FILE, scene, 1.0, program, folder)
    assert folder.is_dir()


# A real browser.


def found_browser() -> Path | None:
    try:
        return viewing_browser.find()
    except viewing_browser.Stopped:
        return None


real_browser = pytest.mark.skipif(found_browser() is None, reason="no browser on this machine")


@real_browser
def test_a_real_browser_names_each_planted_fault_of_a_file(tmp_path: Path) -> None:
    """Each start reads the planted page. Read as a file too, it shows what the reads give.
    What drew the page, and how it looks, this test leaves to the machine."""
    file = tmp_path / "planted.html"
    file.write_text(
        viewing_browser._planted_html(viewing_browser.PLANTED_FACE.read_bytes()),
        encoding="utf-8",
    )
    page = viewing_browser.PLANTED_PAGE
    browser = found_browser()
    assert browser is not None
    try:
        drawing = viewing_browser.draw(file, [page], 2.0, browser, tmp_path / "local")
    except viewing_browser.Stopped as stop:
        if stop.sandbox:
            pytest.skip(f"a sandbox stopped the browser: {stop}")
        raise
    assert viewing_browser._named(drawing.read) == viewing_browser.PLANTED_FINDINGS
    assert drawing.browser
    (image,) = drawing.images
    assert (image.width, image.height) == (page.width * 2, page.height * 2)
    assert all(each.fonts for each in drawing.read.machine_fonts)
    assert list((tmp_path / "local").iterdir()) == []


def scene_pages(scene: Mapping[str, Any]) -> list[Any]:
    """The pages of a scene, each text's spans as its `lines` hold them."""

    def texts(parent: Mapping[str, Any]) -> Iterator[Mapping[str, Any]]:
        for child in parent.get("children", []):
            if child.get("type") == "group":
                yield from texts(child)
            elif child.get("type") == "text":
                yield child

    found = []
    for held in scene["children"]:
        lines = [
            viewing_browser.Text(
                each["id"],
                tuple(tuple(one["text"] for one in row["spans"]) for row in each["lines"]),
            )
            for each in texts(held)
        ]
        found.append(viewing_browser.Page(held["id"], held["width"], held["height"], tuple(lines)))
    return found


@real_browser
def test_a_real_browser_reads_the_renderers_reference_file_clean(tmp_path: Path) -> None:
    """A picture, an ellipse, a run in two families, a text under a later box and pages of two
    sizes, as the renderer writes them: the reads name nothing."""
    from tests.test_visual_communication_html import REFERENCE, draw, reference_picture

    file = tmp_path / "reference.html"
    file.write_bytes(draw(REFERENCE, pictures={"square": reference_picture(tmp_path)}).document)
    browser = found_browser()
    assert browser is not None
    pages = scene_pages(REFERENCE)
    try:
        drawing = viewing_browser.draw(file, pages, 1.225, browser, tmp_path / "local")
    except viewing_browser.Stopped as stop:
        if stop.sandbox:
            pytest.skip(f"a sandbox stopped the browser: {stop}")
        raise
    assert drawing.read == viewing_browser.Read((), (), (), (), ())
    assert [each.page for each in drawing.images] == [page.id for page in pages]
