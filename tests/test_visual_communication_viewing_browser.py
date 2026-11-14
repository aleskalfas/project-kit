"""The viewing step's browser (`_lib/viewing_browser.py`, visual-communication DEC-020 points 6
to 9, DEC-031 point 5, DEC-027 points 2 to 4, DEC-037, DEC-039 point 5): how it finds a browser,
what one start asks of it, the window that holds each page at its own size with its gutters,
the four reads, what the page shows of each span, the first read of a file with planted
faults, its bounds, what a stop says, and the start that forces its colours. The step's
browser also prints the renderer's page file here, as DEC-026 point 7 lets a test do and no
step.

A stand-in program speaks the pipe in the browser's place (`visual_communication_browser`), so
these tests need no browser. The ones that start a real browser skip where none is found, or
where a sandbox stops the one found. The one that holds that a start forced by the emulation
alone stops skips too where that browser's emulation forces the text. No test holds a pixel as
a contract (DEC-015 point 6).
"""

from __future__ import annotations

import ast
import base64
import contextlib
import copy
import dataclasses
import json
import os
import re
import sys
import time
from collections.abc import Iterator, Mapping, Sequence
from pathlib import Path
from typing import Any

import pytest
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.ttLib import TTFont

from tests.in_process import load
from tests.visual_communication_browser import (
    COLOURS,
    HELD_FONT,
    STRONG,
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
    "unground": viewing_browser.UNGROUND,
    "settle": viewing_browser.SETTLE,
    "colours": viewing_browser.COLOURS,
    "style": viewing_browser.STYLE,
    "marked": viewing_browser.MARKED,
    "tally": viewing_browser.TALLY,
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
    """A span as `READ` gives it, on the page's first rows, painted in the document's order,
    with what a stand-in adds."""
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
        "em": 16.0,
        "order": [0, index],
        "ink": DARK,
        **held,
    }


def page(id: str, width: float, height: float, *texts: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "id": id,
        "x": 0.0,
        "y": 0.0,
        "width": width,
        "height": height,
        "texts": list(texts),
        "parts": [],
    }


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


#: The share of its strong ink each plant the reads name as cut or covered loses, by its trace
#: id, as a stand-in draws the planted file.
PLANTED_LOSSES = {
    finding[1]: {finding[0]: 0.5}
    for finding in viewing_browser.PLANTED_FINDINGS
    if finding[0] in (viewing_browser.CUT, viewing_browser.COVERED)
}


def planted(forced: bool = False) -> dict[str, Any]:
    """The planted file as a browser reads it: each fault where the module planted it, its
    page of its own below its first. Where `forced`, as a start that forces its colours writes
    it, its text left to forcing showing ink."""
    index = 0
    pages = []
    top = 0.0
    held_pages = (
        (
            viewing_browser.PLANTED_ID,
            viewing_browser.PLANTED_HEIGHT,
            {
                **viewing_browser.PLANTED_TEXTS,
                **(viewing_browser.FORCED_TEXTS if forced else {}),
            },
        ),
        (viewing_browser.RAISED_ID, viewing_browser.RAISED_HEIGHT, viewing_browser.RAISED_TEXTS),
    )
    for trace, height, held_texts in held_pages:
        texts = []
        for row, (element, lines) in enumerate(held_texts.items()):
            drawn = []
            for line in lines:
                spans = []
                for planted_span in line:
                    held = (
                        planted_span.family == viewing_browser.HELD and planted_span.weight == 400
                    )
                    machine = planted_span.family != viewing_browser.HELD
                    spans.append(
                        span(
                            planted_span.text,
                            index,
                            family=planted_span.family,
                            weight=str(planted_span.weight),
                            face=held,
                            x=float(planted_span.left),
                            y=top + 10.0 + 20 * row,
                            fonts=[MACHINE_FONT if machine else HELD_FONT],
                            ink=(
                                ()
                                if planted_span.colour == viewing_browser.UNPAINTED
                                and not planted_span.forced
                                else DARK
                            ),
                            lost=PLANTED_LOSSES.get(element, {}),
                        )
                    )
                    index += 1
                drawn.append(spans)
            texts.append(text(element, *drawn))
        pages.append({**page(trace, viewing_browser.PLANTED_WIDTH, height, *texts), "y": top})
        top += height + 24
    document = {
        "pages": pages,
        "requests": [viewing_browser.NETWORK, f"file:///folder/{viewing_browser.BESIDE}"],
    }
    by_text = {each["id"]: each for held in pages for each in held["texts"]}
    by_text[viewing_browser.LACKED_FINDING[1]]["lines"][0][0]["fonts"] = [HELD_FONT, MACHINE_FONT]
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
    on = next(each for each in mended["pages"] if any(t["id"] == about for t in each["texts"]))
    held = next(each for each in on["texts"] if each["id"] == about)
    spans = [each for line in held["lines"] for each in line]
    if kind == viewing_browser.WORDS:
        [scene] = [
            each
            for page in viewing_browser.PLANTED_PAGES
            for each in page.texts
            if each.element == about
        ]
        # In the place of the span it holds, so no other span's place is taken.
        place = {side: spans[0][side] for side in ("index", "y")}
        on["texts"].remove(held)
        on["texts"].append(
            text(about, *[[span(each, **place) for each in line] for line in scene.lines])
        )
    elif kind == viewing_browser.NO_INK:
        next(each for each in spans if each["text"] == finding[2])["ink"] = DARK
    elif kind == viewing_browser.OFF_THE_PAGE:
        spans[0]["x"] = 8.0
    elif kind in (viewing_browser.CUT, viewing_browser.COVERED):
        spans[0]["lost"] = {}
    elif kind == viewing_browser.NO_FACE:
        spans[0]["face"] = True
    else:
        spans[0]["fonts"] = [HELD_FONT]
    return mended


def plan(**changes: Any) -> dict[str, Any]:
    """A plan under which a stand-in draws `clean` with nothing to say."""
    documents = {
        viewing_browser.PLANTED_FILE: planted(),
        viewing_browser.PLANTED_FORCED_FILE: planted(forced=True),
        FILE: clean(),
    }
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


def test_one_start_serves_one_file_at_the_callers_scale_and_the_widest_page_with_its_gutters(
    tmp_path: Path,
) -> None:
    """The window holds each page at its own size, with the gutter on each side, whichever
    pages the file holds (DEC-031 point 5)."""
    pages = [
        page("narrow", 400.5, 300.0, text("a", [span("a", 0)])),
        page("wide", 1280.0, 720.0, text("b", [span("b", 1)])),
    ]
    _, program = drawn(tmp_path, documents={FILE: {"pages": pages}}, scale=1.225)
    starts = [each["flags"] for each in logged(program) if "flags" in each]
    assert len(starts) == 1
    assert "--force-device-scale-factor=1.225" in starts[0]
    (window,) = [flag for flag in starts[0] if flag.startswith("--window-size=")]
    assert window.split("=")[1].split(",")[0] == "1344"


def test_the_gutter_is_the_one_the_renderer_declares() -> None:
    """The step takes it from the renderer's declaration, as it takes the file's marks, and
    widens the window by it on each side (DEC-031 point 5)."""
    declared = viewing_browser.html_declaration.DECLARATION["pages"]["fixed"]["gutter"]
    assert viewing_browser.GUTTER == declared["width"] == 32
    held = [viewing_browser.Page("one", 400.5, 300.0, ()), viewing_browser.Page("two", 90, 9, ())]
    assert viewing_browser.window_width(held) == 400.5 + 2 * 32


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
    assert [(each.page, each.width, each.height) for each in drawing.shown[0].images] == [
        ("one", 2560, 1440),
        ("two", 1600, 2200),
    ]
    assert {each.band for each in drawing.shown[0].images} == {0}
    assert file_clips(program) == [
        {"x": 0.0, "y": 0.0, "width": 1280.0, "height": 720.0, "scale": 1},
        {"x": 240.0, "y": 744.0, "width": 800.0, "height": 1100.0, "scale": 1},
    ]


def file_clips(program: Path) -> list[dict[str, Any]]:
    """The clips the file's images were drawn by, in its first mode: those taken after the
    file opened, and before the reads of what the page shows of each span."""
    messages = logged(program)
    methods = [each.get("method") for each in messages]
    file_opened = len(methods) - 1 - methods[::-1].index("Page.navigate")
    after = messages[file_opened:]
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


#: The bands of a phone's page 5,000 px tall, each a top and a height, as the caller hands them.
BANDS = ((0.0, 1700.0), (1677.6, 1700.0), (3355.2, 1644.8))


def test_a_page_handed_its_regions_is_drawn_by_a_clip_of_each_as_wide_as_the_page(
    tmp_path: Path,
) -> None:
    pages = [{**page("tall", 390.0, 5000.0, text("a", [span("a", 0)])), "x": 8.0, "y": 744.0}]
    [wanted] = as_scene(pages)
    held = dataclasses.replace(wanted, regions=BANDS)
    drawing, program = drawn(tmp_path, [held], documents={FILE: {"pages": pages}})
    images = drawing.shown[0].images
    assert [(each.page, each.band, each.width, each.height) for each in images] == [
        ("tall", 1, 780, 3400),
        ("tall", 2, 780, 3400),
        ("tall", 3, 780, 3290),
    ]
    assert file_clips(program) == [
        {"x": 8.0, "y": 744.0 + top, "width": 390.0, "height": height, "scale": 1}
        for top, height in BANDS
    ]


def test_a_page_in_bands_is_read_once_whole_a_span_in_an_overlap_among_it(tmp_path: Path) -> None:
    """The span with no ink lies where the first two bands overlap."""
    lost = span("lost", 0, ink=(), y=1690.0)
    pages = [page("tall", 390.0, 5000.0, text("a", [lost, span("kept", 1, y=4000.0)]))]
    [wanted] = as_scene(pages)
    held = dataclasses.replace(wanted, regions=BANDS)
    drawing, _ = drawn(tmp_path, [held], documents={FILE: {"pages": pages}})
    assert [each.band for each in drawing.shown[0].images] == [1, 2, 3]
    assert [(each.element, each.text) for each in drawing.shown[0].read.dropped] == [("a", "lost")]


def test_a_page_asked_for_alone_is_read_alone(tmp_path: Path) -> None:
    pages = [
        page("one", 1280.0, 720.0, text("a", [span("a", 0, ink=())])),
        page("two", 1280.0, 720.0, text("b", [span("b", 1)])),
    ]
    wanted = as_scene(pages[1:])
    drawing, _ = drawn(tmp_path, wanted, documents={FILE: {"pages": pages}})
    assert [each.page for each in drawing.shown[0].images] == ["two"]
    assert drawing.shown[0].read.dropped == ()


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
    return drawn(tmp_path, scene, documents={FILE: document})[0].shown[0].read.words


def scene_page(*texts: Any) -> Any:
    return viewing_browser.Page("page", 1280.0, 720.0, tuple(texts))


def test_a_document_that_matches_the_scene_reports_no_difference(tmp_path: Path) -> None:
    drawing, _ = drawn(tmp_path)
    assert drawing.shown[0].read == viewing_browser.Read((), (), (), (), ())


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
    return drawn(tmp_path, documents={FILE: one_page(*spans)})[0].shown[0].read.dropped


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


def test_a_band_reaches_as_far_as_its_pages_room(tmp_path: Path) -> None:
    """The span crosses its page's foot, so the read gives the page room past each edge as far
    as the span's box, widened by its em, reaches: 22 px. Its band spans the page and that
    room, and the span's height either way (DEC-037 point 3)."""
    held = page("page", 400.0, 100.0, text("a", [span("low", 0)]))
    held["x"], held["y"] = 240.5, 50.0
    held["texts"][0]["lines"][0][0].update({"x": 300.0, "y": 140.0})
    _, program = drawn(tmp_path, documents={FILE: {"pages": [held]}})
    clip = called(program, "Page.captureScreenshot")[-1]["clip"]
    assert clip == {"x": 218.5, "y": 124, "width": 444.0, "height": 48, "scale": 1}


def test_a_band_and_a_clip_start_no_earlier_than_the_document() -> None:
    """A browser takes no clip before the document's start, so a page at its left edge has its
    room on the right alone, as a probe at a scale of 1.225 found."""
    held = {**page("page", 400.0, 100.0), "x": -1.9e-06}
    low = span("low", 0, x=2.0, y=2.0)
    assert viewing_browser._band(low, held, 22) == {
        "x": 0.0,
        "y": 0,
        "width": pytest.approx(422.0),
        "height": 34,
    }
    widened = viewing_browser._widened(low, low["em"])
    assert viewing_browser._clip([widened], held, 22) == {
        "x": 0,
        "y": 0,
        "width": 78,
        "height": 34,
    }


# What the page shows of a span (DEC-037).


def evaluated(program: Path, function: str) -> list[list[Any]]:
    """The arguments of each call of the module's JavaScript `function` the stand-in received,
    after the file opened."""
    messages = logged(program)
    methods = [each.get("method") for each in messages]
    after = messages[len(methods) - 1 - methods[::-1].index("Page.navigate") :]
    found = []
    for each in after:
        expression = each.get("params", {}).get("expression", "")
        if each.get("method") == "Runtime.evaluate" and expression.startswith(f"({function})"):
            found.append(json.loads(expression[len(function) + 2 :].strip("().")))
    return found


def tallied(program: Path) -> list[list[int]]:
    """The spans, by their places in the document, of each batch whose strong ink was read."""
    return [[each["index"] for each in asked] for _, _, asked in evaluated(program, TALLY)]


TALLY = viewing_browser.TALLY

#: A span alone in the middle of its page, which the pre-filter passes over, unless what a
#: test adds meets it.
APART = {"x": 600.0, "y": 300.0}


def test_a_span_cut_or_covered_is_an_entry_of_dropped_with_the_share_its_cause_loses(
    tmp_path: Path,
) -> None:
    """One entry for each cause, in the document's order, each cause's after a span's earlier
    ones: a span both cut and covered gives two (DEC-037 points 1 and 2)."""
    found = dropped(
        tmp_path,
        span("cut", 0, lost={"cut": 0.25}),
        span("covered", 1, lost={"covered": 0.5}),
        span("both", 2, lost={"covered": 0.125, "cut": 0.375}),
        span("shown", 3),
    )
    assert found == (
        viewing_browser.Dropped("page", "text-0", "cut", viewing_browser.CUT, 0.25),
        viewing_browser.Dropped("page", "text-1", "covered", viewing_browser.COVERED, 0.5),
        viewing_browser.Dropped("page", "text-2", "both", viewing_browser.CUT, 0.375),
        viewing_browser.Dropped("page", "text-2", "both", viewing_browser.COVERED, 0.125),
    )


def test_a_span_wholly_off_its_page_is_named_off_the_page_alone_and_its_ink_not_read(
    tmp_path: Path,
) -> None:
    held, program = drawn(
        tmp_path, documents={FILE: one_page(span("away", 0, x=4000.0, lost={"cut": 1.0}))}
    )
    assert held.shown[0].read.dropped == (
        viewing_browser.Dropped("page", "text-0", "away", viewing_browser.OFF_THE_PAGE),
    )
    assert tallied(program) == []


@pytest.mark.parametrize(
    ("em", "lost", "named"),
    [(16.0, 10, False), (16.0, 11, True), (32.0, 40, False), (32.0, 41, True)],
    ids=["below", "above", "below-at-twice-the-em", "above-at-twice-the-em"],
)
def test_a_loss_smaller_than_the_sliver_in_the_spans_em_names_no_entry(
    tmp_path: Path, em: float, lost: int, named: bool
) -> None:
    """At a device scale of 2, the sliver of a span of 16 px is 10.24 device px, and of one of
    32 px four times that. Each cause is judged alone (DEC-037 point 1)."""
    assert viewing_browser.SLIVER * (em * 2) ** 2 == pytest.approx(10.24 * (em / 16) ** 2)
    share = lost / STRONG
    found = dropped(tmp_path, span("graze", 0, em=em, lost={"covered": share, "cut": 1 / STRONG}))
    assert [(each.why, each.share) for each in found] == (
        [(viewing_browser.COVERED, share)] if named else []
    )


def test_the_pre_filter_passes_over_a_span_that_can_lose_nothing(tmp_path: Path) -> None:
    """Its box, widened by its em, stays on its page, with no other text near it and no part
    painted after it, so its strong ink is not read (DEC-037 point 3)."""
    document = one_page(span("apart", 0, **APART, lost={"covered": 0.5}))
    document["pages"][0]["parts"] = [
        {"x": 600.0, "y": 0.0, "width": 60.0, "height": 16.0, "order": [0, 9]},
        {"x": 0.0, "y": 300.0, "width": 1280.0, "height": 16.0, "order": [0, -1]},
        {"x": 0.0, "y": 300.0, "width": 1280.0, "height": 16.0, "order": [-1, 9]},
    ]
    held, program = drawn(tmp_path, documents={FILE: document})
    assert held.shown[0].read.dropped == ()
    assert tallied(program) == []


@pytest.mark.parametrize(
    "near",
    [
        {"span": {"x": 4.0}},
        {"span": {"y": 712.0}},
        {"other": {"x": 650.0, "y": 300.0}},
        {"part": {"order": [0, 1]}},
        {"part": {"order": [1, -1]}},
    ],
    ids=[
        "near-its-pages-left",
        "near-its-pages-foot",
        "another-text",
        "a-part-later-in-the-document",
        "a-part-earlier-raised-by-z-index",
    ],
)
def test_the_pre_filter_reads_a_span_that_something_may_cover_or_cut(
    tmp_path: Path, near: dict[str, Any]
) -> None:
    """A span whose widened box nears its page's edge, meets another text, or meets a part the
    browser paints after it, by its z-index and then the document's order, is read, never
    passed over by the document's order alone (DEC-037 point 3)."""
    held = span("near", 0, **{**APART, **near.get("span", {})}, lost={"covered": 0.5})
    spans = [held]
    if "other" in near:
        spans.append(span("other", 1, **near["other"]))
    document = one_page(*spans)
    if "part" in near:
        box = {"x": 590.0, "y": 290.0, "width": 10.0, "height": 10.0}
        document["pages"][0]["parts"] = [{**box, **near["part"]}]
    found, program = drawn(tmp_path, documents={FILE: document})
    assert [(each.text, each.why) for each in found.shown[0].read.dropped] == [
        ("near", viewing_browser.COVERED)
    ]
    assert [0] in tallied(program)


def test_spans_whose_widened_boxes_do_not_meet_are_drawn_alone_at_once(tmp_path: Path) -> None:
    """The first two spans' boxes, widened by their em, meet, so they lie in two batches; the
    third meets neither, and joins the first. Each batch is marked at once, and read from four
    draws, each the same clip (DEC-037 point 3)."""
    document = one_page(span("one", 0), span("two", 1), span("three", 2, y=400.0))
    _, program = drawn(tmp_path, documents={FILE: document})
    assert tallied(program) == [[0, 2], [1]]
    measured = [
        indices
        for _, mark, indices in evaluated(program, viewing_browser.MARKED)
        if mark == viewing_browser.MEASURED_MARK
    ]
    assert measured == [[0, 2], [1], []]
    assert [len(images) for images, _, _ in evaluated(program, TALLY)] == [4, 4]


def test_each_batch_is_read_in_its_letters_alone_then_in_the_page_drawn_whole(
    tmp_path: Path,
) -> None:
    """Its letters in `CanvasText`, then `Canvas`, drawn alone with no other text, no text's
    ground and no sign, on `Canvas`; then the page drawn whole, its letters in each colour
    again. The read's styles go once it is done (DEC-037 point 3)."""
    _, program = drawn(tmp_path, documents={FILE: one_page(span("one", 0))})
    draws = [
        css for held, css in evaluated(program, viewing_browser.STYLE)
        if held == viewing_browser.DRAW_STYLE
    ]  # fmt: skip
    marked = f"[{viewing_browser.MEASURED_MARK}]"
    alone = f"[{viewing_browser.MARKS['page']}] *{{visibility:hidden!important}}"
    *read, cleared = draws
    assert cleared == ""
    colours = ("CanvasText", "Canvas") * 2
    for number, (each, colour) in enumerate(zip(read, colours, strict=True)):
        assert each.endswith(f"{marked}{{color:{colour}!important}}")
        assert (alone in each) == (number < 2)
    assert f"[{viewing_browser.MARKS['sign']}]{{visibility:hidden!important}}" in draws[0]
    assert f"[{viewing_browser.MARKS['span']}]{{background:none!important}}" in draws[0]
    assert "{background:Canvas!important}" in draws[0]
    [unground] = evaluated(program, viewing_browser.UNGROUND)
    assert unground == [list(viewing_browser.READ_STYLES), list(viewing_browser.READ_MARKS)]


def test_the_read_gives_each_page_room_past_its_edges_and_keeps_its_size(tmp_path: Path) -> None:
    """As far as a span's box, widened by its em, reaches past an edge: here 56 px past the
    right edge of a page 400 px wide. The keyline is hidden there, and the pages lie apart by
    their room (DEC-037 point 3, DEC-031 point 5)."""
    held = page("page", 400.0, 300.0, text("a", [span("past", 0, x=380.0, y=100.0)]))
    _, program = drawn(tmp_path, documents={FILE: {"pages": [held]}})
    [room] = [
        css for named, css in evaluated(program, viewing_browser.STYLE)
        if named == viewing_browser.ROOM_STYLE
    ]  # fmt: skip
    page_mark = f"[{viewing_browser.MARKS['page']}]"
    assert room == (
        "body{width:400.0px!important;padding:56px!important;margin:0!important}"
        f"{page_mark}{{margin:0 auto!important;outline:none!important}}"
        f"{page_mark}+{page_mark}{{margin-top:112px!important}}"
    )


def test_a_page_with_no_span_near_an_edge_takes_no_room() -> None:
    held = page("page", 1280.0, 720.0, text("a", [span("apart", 0, **APART)]))
    assert viewing_browser._room([held]) == 0


def test_the_cut_and_the_cover_are_read_in_each_mode_alone(tmp_path: Path) -> None:
    """A span covered in the dark key alone, as a key may paint a part over it."""
    dim = span("dim", 1, **{"lost-when": {"prefers-color-scheme:dark": {"covered": 1}}})
    drawing, _ = in_modes(tmp_path, documents={FILE: one_page(span("hello", 0), dim)})
    covered = (viewing_browser.Dropped("page", "text-1", "dim", viewing_browser.COVERED, 1.0),)
    assert [each.read.dropped for each in drawing.shown] == [(), (), covered, covered]


# The font.


def test_a_span_with_no_loaded_face_is_reported_by_family_and_weight(tmp_path: Path) -> None:
    held = span("words", 0, family="Brand & Co", weight="700", face=False)
    document = one_page(held)
    assert drawn(tmp_path, documents={FILE: document})[0].shown[0].read.no_face == (
        viewing_browser.NoFace("page", "text-0", "words", "Brand & Co", "700"),
    )


def test_a_span_with_no_characters_asks_for_no_face(tmp_path: Path) -> None:
    document = one_page(span("", 0, face=False, ink=()))
    assert drawn(tmp_path, documents={FILE: document})[0].shown[0].read.no_face == ()


@pytest.mark.parametrize(
    "fonts", [[MACHINE_FONT], [HELD_FONT, MACHINE_FONT]], ids=["whole", "in-part"]
)
def test_a_span_drawn_in_a_font_of_the_machine_is_reported_with_that_font(
    tmp_path: Path, fonts: list[Mapping[str, Any]]
) -> None:
    document = one_page(span("words", 0, fonts=fonts))
    assert drawn(tmp_path, documents={FILE: document})[0].shown[0].read.machine_fonts == (
        viewing_browser.MachineFont("page", "text-0", "words", ("Times",)),
    )


# Requests.


def test_each_request_but_the_files_own_and_a_data_address_is_refused_and_named(
    tmp_path: Path,
) -> None:
    asked = ["https://example.org/a.png", "data:image/png;base64,AAAA", "file:///beside.png"]
    document = {**clean(), "requests": asked}
    drawing, program = drawn(tmp_path, documents={FILE: document})
    assert drawing.shown[0].read.refused == (asked[0], asked[2])
    assert len(called(program, "Fetch.failRequest")) == 4  # two on the planted page
    assert len(called(program, "Fetch.continueRequest")) == 3


def test_the_first_reads_requests_are_not_the_files(tmp_path: Path) -> None:
    assert drawn(tmp_path)[0].shown[0].read.refused == ()


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
    assert unnamed == {"clean", "colour-of-its-ground"} | LEFT_UNNAMED


#: The plants of what the page shows of a span that the reads leave unnamed (DEC-037 point 5).
LEFT_UNNAMED = {
    viewing_browser.OVER_ANOTHER,
    viewing_browser.UNDER_A_TRANSLUCENT_FILL,
    viewing_browser.EDGE_CONTROL,
}


def test_the_planted_file_plants_each_loss_of_what_the_page_shows() -> None:
    """A span cut past its page's top edge, and as covered: the text under a later box, the
    háček plant, a span wholly under another text, never named as one with no ink, and the
    text a part covers by z-index, on a page of its own (DEC-037 point 5)."""
    named = {
        finding[:2]
        for finding in viewing_browser.PLANTED_FINDINGS
        if finding[0] in (viewing_browser.CUT, viewing_browser.COVERED)
    }
    assert named == {
        (viewing_browser.CUT, viewing_browser.CUT_PAST_THE_TOP),
        (viewing_browser.COVERED, viewing_browser.UNDER_A_BOX),
        (viewing_browser.COVERED, viewing_browser.HACEK),
        (viewing_browser.COVERED, viewing_browser.UNDER_ANOTHER),
        (viewing_browser.COVERED, viewing_browser.RAISED),
    }
    assert not {
        finding
        for finding in viewing_browser.PLANTED_FINDINGS
        if finding[1] in (viewing_browser.UNDER_ANOTHER, viewing_browser.RAISED)
        and finding[0] != viewing_browser.COVERED
    }
    first, own = viewing_browser.PLANTED_PAGES
    assert [each.element for each in own.texts] == [viewing_browser.RAISED]
    assert viewing_browser.RAISED not in {each.element for each in first.texts}


def test_the_span_under_another_text_is_covered_by_that_texts_run_ground() -> None:
    """The plant of a span wholly under another text relies on the text over it, on its row and
    later in the tree, drawing its run's ground (DEC-037 point 5). A change to grounds that
    stops that text drawing one fails here by name, rather than leave the plant to its
    letters."""
    page = viewing_browser._first_page(1.0, False)
    laid = [each for each in page if isinstance(each, viewing_browser._Laid)]
    by_element = {each.element: each for each in laid}
    under = by_element[viewing_browser.UNDER_ANOTHER]
    over = by_element[viewing_browser.OVER_ANOTHER]
    assert laid.index(under) < laid.index(over)
    assert over.baseline == under.baseline
    assert all(span.grounded for line in over.lines for span in line)
    assert ";background:" in viewing_browser._planted_text(over, False)


def test_the_planted_page_is_in_the_renderers_form() -> None:
    (html,) = load("visual-communication", "plugins.html")
    assert viewing_browser.PLANTED_SHEET == html.SHEET
    planted_html = viewing_browser._planted_html(b"a face")
    for mark in viewing_browser.MARKS.values():
        assert f" {mark}" in planted_html
    assert viewing_browser.LACKED in planted_html
    assert "swal<lowed" in planted_html


def test_the_planted_face_lacks_the_planted_character_and_holds_the_rest_of_its_span() -> None:
    cmap = TTFont(viewing_browser.PLANTED_FACE).getBestCmap()
    assert cmap is not None
    text = viewing_browser.LACKED_FINDING[2]
    assert ord(viewing_browser.LACKED) not in cmap
    assert all(ord(each) in cmap for each in text.replace(viewing_browser.LACKED, ""))


def _bounds(glyphs: Any, name: str) -> tuple[float, float, float, float]:
    """The bounds of the glyph `name` of `glyphs`, in its face's units."""
    pen = BoundsPen(glyphs)
    glyphs[name].draw(pen)
    assert pen.bounds is not None
    return pen.bounds


def _contours(glyphs: Any, name: str) -> list[tuple[float, float]]:
    """The lowest and the highest point of each contour of the glyph `name` of `glyphs`, its
    components drawn out, in its face's units."""
    pen = DecomposingRecordingPen(glyphs)
    glyphs[name].draw(pen)
    found, points = [], []
    for operator, arguments in pen.value:
        if operator == "moveTo":
            points = list(arguments)
        elif operator in ("lineTo", "curveTo", "qCurveTo"):
            points += arguments
        elif points:
            found.append((min(y for _, y in points), max(y for _, y in points)))
            points = []
    return found


def test_the_planted_files_measures_of_its_face_are_the_faces() -> None:
    """A line's ground reaches as far as the face does, as the renderer reads it (DEC-039 point
    2). The edge control's box starts at its word's lowest descender, and the háček plant's
    ends between the top of a `z` and the foot of the háček over it, so it covers the háček
    alone (DEC-037 point 5)."""
    (html,) = load("visual-communication", "plugins.html")
    reach = html.face_reach(viewing_browser.PLANTED_FACE)
    assert pytest.approx(reach) == (viewing_browser.ASCENT, viewing_browser.DESCENT)
    [[control]] = viewing_browser.PLANTED_TEXTS[viewing_browser.EDGE_CONTROL]
    [[hacek]] = viewing_browser.PLANTED_TEXTS[viewing_browser.HACEK]
    with TTFont(viewing_browser.PLANTED_FACE) as font:
        cmap, glyphs = font.getBestCmap(), font.getGlyphSet()
        assert cmap is not None
        upem = font["head"].unitsPerEm  # pyright: ignore[reportAttributeAccessIssue] fontTools types no table's fields
        foot = -min(_bounds(glyphs, cmap[ord(each)])[1] for each in control.text) / upem
        top = _bounds(glyphs, cmap[ord("z")])[3] / upem
        over = [low for low, _ in _contours(glyphs, cmap[ord(hacek.text)]) if low > top * upem]
    assert foot == pytest.approx(viewing_browser.FOOT)
    assert top < viewing_browser.UNDER_THE_HACEK < min(over) / upem


def test_the_hacek_plant_is_set_at_the_commands_text_floor() -> None:
    """In device pixels, as the viewing step keeps a page's text (DEC-037 point 5, DEC-015
    point 5)."""
    (viewing,) = load("visual-communication", "viewing")
    assert viewing_browser.TEXT_FLOOR == viewing.SMALLEST_TEXT


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
    assert (viewing_browser.NO_FONT_HOLDS in stop.what) == (
        finding == viewing_browser.LACKED_FINDING
    )
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
        ("under-another-text", {"ink": ()}),
        ("over-another-text", {"lost": {"covered": 0.5}}),
        ("under-a-translucent-fill", {"lost": {"covered": 0.5}}),
        ("edge-control", {"lost": {"covered": 0.5}}),
        ("clean", {"lost": {"cut": 0.5}}),
    ],
    ids=[
        "clean-ink",
        "under-a-box",
        "ground",
        "clean-face",
        "clean-font",
        "under-another-as-no-ink",
        "over-another",
        "translucent",
        "edge-control",
        "clean-cut",
    ],
)
def test_a_read_that_names_what_is_clean_stops_the_start(
    tmp_path: Path, element: str, change: dict[str, Any]
) -> None:
    document = planted()
    held = next(each for each in document["pages"][0]["texts"] if each["id"] == element)
    held["lines"][0][0].update(change)
    stop, _ = stopped(tmp_path, documents={viewing_browser.PLANTED_FILE: document})
    assert "which the page does not plant" in stop.what
    assert element in stop.what.split("named")[-1]


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


@pytest.mark.parametrize("kind", ["no object", "error of no object"])
def test_a_message_of_another_form_stops_the_drawing(tmp_path: Path, kind: str) -> None:
    stop, _ = stopped(tmp_path, fault={"kind": kind, "method": "Browser.getVersion"})
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
    assert not stop.as_root


#: What Chrome says where it runs as root, as a container may run it: it refuses to start with
#: its own sandbox on, and its words name that sandbox.
AS_ROOT_WORDS = (
    "[1107/101010.000000:ERROR:zygote_host_impl_linux.cc(128)] Running as root without "
    "--no-sandbox is not supported. See https://crbug.com/638180."
)


def test_a_browser_run_as_root_is_told_apart_from_a_sandbox_that_stopped_it(
    tmp_path: Path,
) -> None:
    stop, _ = stopped(tmp_path, says=AS_ROOT_WORDS, exit=1)
    assert stop.as_root
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


#: Flags that turn off or weaken the sandbox of a browser's processes, merge them into one, or
#: let a page read past its own file: the module passes none (DEC-024 point 1).
UNSAFE_FLAGS = (
    "--no-sandbox",
    "--disable-setuid-sandbox",
    "--disable-gpu-sandbox",
    "--disable-seccomp-filter-sandbox",
    "--disable-namespace-sandbox",
    "--no-zygote",
    "--single-process",
    "--in-process-gpu",
    "--disable-site-isolation-trials",
    "--disable-web-security",
    "--allow-file-access-from-files",
    "--allow-file-access",
    "--allow-running-insecure-content",
    "--disable-features",
    "--unsafely-treat-insecure-origin-as-secure",
)

#: Words in a flag's name that touch the browser's own sandbox or its processes' isolation.
UNSAFE_WORDS = ("sandbox", "zygote", "single-process", "in-process", "unsafe", "security", "file")


def test_no_flag_the_module_passes_weakens_the_browser_or_lets_a_page_read_past_its_file(
    tmp_path: Path,
) -> None:
    _, program = drawn(tmp_path)
    names = {flag.split("=")[0] for flag in logged(program)[0]["flags"]}
    assert not names & set(UNSAFE_FLAGS)
    assert not [name for name in names for word in UNSAFE_WORDS if word in name]
    assert not set(viewing_browser.FLAGS) & set(UNSAFE_FLAGS)


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


# Each mode.

#: The signals a file of both value axes reads, each with its values, the first a reader's with
#: no preference.
SIGNALS = {
    "prefers-color-scheme": ("light", "dark"),
    "prefers-contrast": ("no-preference", "more"),
}

#: Each mode of such a file, as its keys' signals give it.
MODES = [
    {"prefers-color-scheme": scheme, "prefers-contrast": contrast}
    for scheme in SIGNALS["prefers-color-scheme"]
    for contrast in SIGNALS["prefers-contrast"]
]


def in_modes(
    tmp_path: Path,
    modes: Sequence[Mapping[str, str]] = MODES,
    signals: Mapping[str, Sequence[str]] = SIGNALS,
    **changes: Any,
) -> tuple[Any, Path]:
    """What `draw` gives in `modes` under `plan(**changes)`, and the stand-in that gave it."""
    program, pages = _started(tmp_path, None, changes)
    drawing = viewing_browser.draw(
        _file(tmp_path), pages, 2.0, program, tmp_path / "local", signals=signals, modes=modes
    )
    return drawing, program


def after_the_file_opened(program: Path) -> list[dict[str, Any]]:
    """What the program received once the file was opened."""
    messages = logged(program)
    methods = [each.get("method") for each in messages]
    return messages[len(methods) - 1 - methods[::-1].index("Page.navigate") :]


def emulated(messages: Sequence[Mapping[str, Any]]) -> list[dict[str, str]]:
    """The signals each emulation among `messages` set."""
    return [
        {each["name"]: each["value"] for each in message["params"]["features"]}
        for message in messages
        if message.get("method") == "Emulation.setEmulatedMedia"
    ]


def test_each_mode_sets_every_signal_the_file_reads_in_the_order_asked(tmp_path: Path) -> None:
    drawing, program = in_modes(tmp_path)
    assert [dict(each.signals) for each in drawing.shown] == MODES
    assert emulated(after_the_file_opened(program)) == MODES
    for call in called(program, "Emulation.setEmulatedMedia"):
        assert [each["name"] for each in call["features"]] == sorted(SIGNALS)


def test_every_mode_draws_from_one_start_and_the_file_opened_once(tmp_path: Path) -> None:
    drawing, program = in_modes(tmp_path)
    assert len([each for each in logged(program) if "flags" in each]) == 1
    opened = [each["url"].rsplit("/", 1)[-1] for each in called(program, "Page.navigate")]
    assert opened == [viewing_browser.PLANTED_FILE, FILE]
    assert len(drawing.shown) == len(MODES)


def test_each_modes_images_show_the_file_as_it_stands_in_that_mode(tmp_path: Path) -> None:
    """The ink read leaves a ground behind it, which the next mode's images do not show."""
    drawing, _ = in_modes(tmp_path)
    for shown in drawing.shown:
        (image,) = shown.images
        document, ground, _, alone, media = json.loads(image.image[24:])
        assert (document, ground, alone, media) == (FILE, "", None, dict(shown.signals))


def test_each_mode_reads_the_file_in_that_mode_alone(tmp_path: Path) -> None:
    """A text with no ink in one mode alone is named in that mode, and in no other."""
    dim = span("dim", 1, **{"ink-when": {"prefers-color-scheme:dark": []}})
    drawing, _ = in_modes(tmp_path, documents={FILE: one_page(span("hello", 0), dim)})
    dropped = {
        (each.signals["prefers-color-scheme"], each.signals["prefers-contrast"]): [
            (found.text, found.why) for found in each.read.dropped
        ]
        for each in drawing.shown
    }
    assert dropped == {
        ("light", "no-preference"): [],
        ("light", "more"): [],
        ("dark", "no-preference"): [("dim", viewing_browser.NO_INK)],
        ("dark", "more"): [("dim", viewing_browser.NO_INK)],
    }


def test_a_request_refused_as_the_file_loaded_counts_in_each_mode(tmp_path: Path) -> None:
    asked = ["https://example.com/a.png"]
    document = {**clean(), "requests": asked}
    drawing, _ = in_modes(tmp_path, documents={FILE: document})
    assert [each.read.refused for each in drawing.shown] == [tuple(asked)] * len(MODES)


@pytest.mark.parametrize(
    "mode",
    [{"prefers-color-scheme": "dark"}, {**MODES[0], "prefers-reduced-motion": "reduce"}],
    ids=["a signal unset", "a signal the file does not read"],
)
def test_a_mode_that_does_not_set_every_signal_the_file_reads_is_refused(
    tmp_path: Path, mode: Mapping[str, str]
) -> None:
    program, pages = _started(tmp_path, None, {})
    with pytest.raises(ValueError):
        viewing_browser.draw(
            _file(tmp_path), pages, 2.0, program, tmp_path / "local", signals=SIGNALS, modes=[mode]
        )
    assert logged(program) == []


def test_a_file_that_reads_no_signal_is_drawn_once_and_emulates_nothing(tmp_path: Path) -> None:
    drawing, program = drawn(tmp_path)
    assert [dict(each.signals) for each in drawing.shown] == [{}]
    assert called(program, "Emulation.setEmulatedMedia") == [{"features": []}]


def test_the_first_read_sets_each_later_value_of_each_signal_the_others_at_their_first(
    tmp_path: Path,
) -> None:
    _, program = in_modes(tmp_path)
    messages = logged(program)
    methods = [each.get("method") for each in messages]
    file_opened = len(methods) - 1 - methods[::-1].index("Page.navigate")
    first = MODES[0]
    assert emulated(messages[:file_opened]) == [
        first,
        {**first, "prefers-color-scheme": "dark"},
        {**first, "prefers-contrast": "more"},
        first,
    ]


def test_the_first_read_judges_each_signal_by_its_own_mode_box(tmp_path: Path) -> None:
    """Each box is drawn once with every signal at its first value, then again as its own
    signal takes each later value: the clip of each box, in the page's px."""
    _, program = in_modes(tmp_path)
    messages = logged(program)
    methods = [each.get("method") for each in messages]
    file_opened = len(methods) - 1 - methods[::-1].index("Page.navigate")
    clips = [
        {side: each["params"]["clip"][side] for side in ("x", "y", "width", "height")}
        for each in messages[:file_opened]
        if each.get("method") == "Page.captureScreenshot"
    ]
    top = float(viewing_browser.MODE_TOP)
    first, second = (
        {"x": float(left), "y": top, "width": 24.0, "height": 24.0} for left in (8, 56)
    )
    assert clips[:4] == [first, second, first, second]


def test_a_mode_box_is_clipped_where_a_narrower_window_shrinks_the_planted_page() -> None:
    page = {"x": 10.0, "y": 20.0, "width": 240.0, "height": 240.0}
    assert viewing_browser._mode_box(page, 1) == {
        "x": 10.0 + 28.0,
        "y": 20.0 + viewing_browser.MODE_TOP / 2,
        "width": 12.0,
        "height": 12.0,
    }


def test_a_first_read_whose_page_does_not_repaint_as_a_signal_is_set_stops(
    tmp_path: Path,
) -> None:
    program, pages = _started(tmp_path, None, {"repaints": False})
    with pytest.raises(viewing_browser.Stopped) as stop:
        viewing_browser.draw(
            _file(tmp_path), pages, 2.0, program, tmp_path / "local", signals=SIGNALS, modes=MODES
        )
    assert "`prefers-color-scheme: dark`" in stop.value.what
    assert "did not repaint" in stop.value.what
    opened = [each["url"].rsplit("/", 1)[-1] for each in called(program, "Page.navigate")]
    assert opened == [viewing_browser.PLANTED_FILE]


def test_a_page_that_does_not_repaint_stops_no_file_that_reads_no_signal(tmp_path: Path) -> None:
    drawing, _ = drawn(tmp_path, repaints=False)
    assert drawing.shown[0].read == viewing_browser.Read((), (), (), (), ())


def test_the_planted_page_holds_a_mode_for_each_signal_the_file_reads() -> None:
    page = viewing_browser._planted_html(viewing_browser.PLANTED_FACE.read_bytes(), SIGNALS)
    white, black = viewing_browser.MODE_COLOURS
    assert f":root{{--pkit-mode-0:{white};--pkit-mode-1:{white}}}" in page
    assert f"@media (prefers-color-scheme:dark){{:root{{--pkit-mode-0:{black}}}}}" in page
    assert f"@media (prefers-contrast:more){{:root{{--pkit-mode-1:{black}}}}}" in page
    assert page.count("background:var(--pkit-mode-") == len(SIGNALS)
    plain = viewing_browser._planted_html(viewing_browser.PLANTED_FACE.read_bytes())
    assert "--pkit-mode-" not in plain


# Under forced colours.


def forced_drawn(
    tmp_path: Path, signals: Mapping[str, Sequence[str]] = SIGNALS, **changes: Any
) -> tuple[Any, Path]:
    """What `draw_forced` gives under `plan(**changes)`, and the stand-in that gave it."""
    program, pages = _started(tmp_path, None, changes)
    drawing = viewing_browser.draw_forced(
        _file(tmp_path), pages, 2.0, program, tmp_path / "local", signals=signals
    )
    return drawing, program


def forced_stopped(tmp_path: Path, **changes: Any) -> tuple[Any, Path]:
    """The stop `draw_forced` raises under `plan(**changes)`, and the stand-in that gave it."""
    program, pages = _started(tmp_path, None, changes)
    with pytest.raises(viewing_browser.Stopped) as stop:
        viewing_browser.draw_forced(
            _file(tmp_path), pages, 2.0, program, tmp_path / "local", signals=SIGNALS
        )
    return stop.value, program


#: Each emulation of a forced palette, in the order a forced start draws them.
PALETTE_MODES = [
    {**palette.signals, **viewing_browser.FORCED} for palette in viewing_browser.PALETTES
]


def test_the_forced_palettes_are_the_browsers_light_and_dark_with_more_contrast() -> None:
    assert [(each.name, dict(each.signals), each.light) for each in viewing_browser.PALETTES] == [
        ("light", {"prefers-color-scheme": "light", "prefers-contrast": "more"}, True),
        ("dark", {"prefers-color-scheme": "dark", "prefers-contrast": "more"}, False),
    ]
    assert viewing_browser.FORCED == {"forced-colors": "active"}


def test_a_forced_start_passes_the_flag_that_forces_the_browsers_colours(tmp_path: Path) -> None:
    _, program = forced_drawn(tmp_path / "forced")
    assert viewing_browser.FORCING in logged(program)[0]["flags"]
    _, plain = drawn(tmp_path / "plain")
    assert viewing_browser.FORCING not in logged(plain)[0]["flags"]


def test_a_forced_start_holds_each_page_at_its_own_size_with_its_gutters(tmp_path: Path) -> None:
    """Its window is the first start's: the widest page, with the gutter on each side, so a
    fixed page keeps its size under forced colours too (DEC-031 point 5)."""
    pages = [
        page("narrow", 400.5, 300.0, text("a", [span("a", 0)])),
        page("wide", 1280.0, 720.0, text("b", [span("b", 1)])),
    ]
    _, program = forced_drawn(tmp_path, documents={FILE: {"pages": pages}})
    (window,) = [flag for flag in logged(program)[0]["flags"] if flag.startswith("--window-size=")]
    assert window.split("=")[1].split(",")[0] == "1344"


def test_no_flag_of_a_forced_start_touches_or_weakens_the_browsers_sandbox(
    tmp_path: Path,
) -> None:
    _, program = forced_drawn(tmp_path)
    names = {flag.split("=")[0] for flag in logged(program)[0]["flags"]}
    assert names == {
        *viewing_browser.FLAGS,
        viewing_browser.FORCING,
        "--user-data-dir",
        "--force-device-scale-factor",
        "--window-size",
        "about:blank",
    }
    assert not names & set(UNSAFE_FLAGS)
    assert not [name for name in names for word in UNSAFE_WORDS if word in name]


def test_each_forced_palette_is_drawn_with_forced_colours_and_its_signals_in_order(
    tmp_path: Path,
) -> None:
    drawing, program = forced_drawn(tmp_path)
    assert [each.palette for each in drawing.shown] == ["light", "dark"]
    assert [dict(each.signals) for each in drawing.shown] == PALETTE_MODES
    assert emulated(after_the_file_opened(program)) == PALETTE_MODES
    opened = [each["url"].rsplit("/", 1)[-1] for each in called(program, "Page.navigate")]
    assert opened == [viewing_browser.PLANTED_FORCED_FILE, FILE]
    assert len([each for each in logged(program) if "flags" in each]) == 1


def test_each_forced_palettes_images_and_reads_are_its_own(tmp_path: Path) -> None:
    dim = span("dim", 1, **{"ink-when": {"prefers-color-scheme:dark": []}})
    drawing, _ = forced_drawn(tmp_path, documents={FILE: one_page(span("hello", 0), dim)})
    light, dark = drawing.shown
    assert light.read.dropped == ()
    assert [(each.text, each.why) for each in dark.read.dropped] == [
        ("dim", viewing_browser.NO_INK)
    ]
    (image,) = dark.images
    *_, media = json.loads(image.image[24:])
    assert media == PALETTE_MODES[1]


def test_a_plain_draw_draws_in_no_forced_palette(tmp_path: Path) -> None:
    drawing, program = in_modes(tmp_path)
    assert {each.palette for each in drawing.shown} == {""}
    opened = [each["url"].rsplit("/", 1)[-1] for each in called(program, "Page.navigate")]
    assert opened == [viewing_browser.PLANTED_FILE, FILE]
    assert not [each for each in emulated(logged(program)) if "forced-colors" in each]


def test_the_forced_first_read_sets_forced_colours_in_every_emulation(tmp_path: Path) -> None:
    """The repaint of each signal's box, then the reads in each forced palette."""
    _, program = forced_drawn(tmp_path)
    messages = logged(program)
    methods = [each.get("method") for each in messages]
    file_opened = len(methods) - 1 - methods[::-1].index("Page.navigate")
    first = {**MODES[0], **viewing_browser.FORCED}
    assert emulated(messages[:file_opened]) == [
        first,
        {**first, "prefers-color-scheme": "dark"},
        {**first, "prefers-contrast": "more"},
        first,
        *PALETTE_MODES,
    ]


def test_a_forced_palette_that_does_not_reach_the_text_stops_the_start(tmp_path: Path) -> None:
    document = planted(forced=True)
    held = next(
        each for each in document["pages"][0]["texts"] if each["id"] == viewing_browser.FORCED_TEXT
    )
    held["lines"][0][0]["ink"] = ()
    stop, program = forced_stopped(
        tmp_path, documents={viewing_browser.PLANTED_FORCED_FILE: document}
    )
    assert stop.what == (
        "the first read set the forced palette `light`, and a span with no paint, left to "
        "forcing, left no ink, so the forced palette did not reach the text"
    )
    assert not [each for each in called(program, "Page.navigate") if each["url"].endswith(FILE)]


@pytest.mark.parametrize(
    ("scheme", "than"),
    [("light", "lighter"), ("dark", "darker")],
)
def test_a_forced_palette_that_is_not_what_its_name_says_stops_the_start(
    tmp_path: Path, scheme: str, than: str
) -> None:
    colours = {"light": COLOURS["light"], "dark": COLOURS["dark"]}
    colours[scheme] = {"ground": "rgb(18, 18, 18)", "text": "rgb(18, 18, 18)"}
    stop, _ = forced_stopped(tmp_path, colours=colours)
    assert stop.what == (
        f"the first read set the forced palette `{scheme}`, and the browser gave it a ground of "
        f"rgb(18, 18, 18), not {than} than its text of rgb(18, 18, 18), so its images would "
        f"show what their name denies"
    )


def test_a_forced_palettes_colour_of_another_form_stops_the_start(tmp_path: Path) -> None:
    colours = {**COLOURS, "light": {"ground": "Canvas", "text": "CanvasText"}}
    stop, _ = forced_stopped(tmp_path, colours=colours)
    assert stop.what.startswith("the browser gave an answer that cannot be read: ")
    assert "Canvas" in stop.what


@pytest.mark.parametrize(
    ("colour", "luminance"),
    [
        ("rgb(255, 255, 255)", 1.0),
        ("rgb(0, 0, 0)", 0.0),
        ("rgba(255, 255, 255, 0)", 1.0),
        ("rgb(18, 18, 18)", 0.006),
    ],
)
def test_a_colour_the_browser_computes_is_read_for_its_luminance(
    colour: str, luminance: float
) -> None:
    assert viewing_browser._luminance(colour) == pytest.approx(luminance, abs=0.001)


@pytest.mark.parametrize(
    "finding",
    [(viewing_browser.NO_INK, "no-paint-alone", "alone"), (viewing_browser.WORDS, "run-swallowed")],
    ids=["ink", "words"],
)
def test_a_planted_fault_unnamed_in_a_forced_palette_stops_the_start(
    tmp_path: Path, finding: tuple[str, ...]
) -> None:
    document = cured(planted(forced=True), finding)
    stop, _ = forced_stopped(tmp_path, documents={viewing_browser.PLANTED_FORCED_FILE: document})
    assert stop.what.startswith(
        f"the first read in the forced palette `light` did not name {' '.join(finding)}"
    )


def test_a_palette_that_does_not_set_a_signal_the_file_reads_is_refused(tmp_path: Path) -> None:
    program, pages = _started(tmp_path, None, {})
    with pytest.raises(ValueError, match="the forced palette `light` sets"):
        viewing_browser.draw_forced(
            _file(tmp_path),
            pages,
            2.0,
            program,
            tmp_path / "local",
            signals={**SIGNALS, "prefers-reduced-motion": ("no-preference", "reduce")},
        )
    assert logged(program) == []


def test_the_forced_planted_page_keeps_its_mode_boxes_and_its_spans_with_no_paint_out(
    tmp_path: Path,
) -> None:
    """Out of forcing, so each box repaints by its own signal and each span with no paint
    stays a planted fault; the text left to forcing is the one that is not kept out."""
    face = viewing_browser.PLANTED_FACE.read_bytes()
    page = viewing_browser._planted_html(face, SIGNALS, forced=True)
    kept = viewing_browser.KEPT_OUT
    assert page.count(f"background:var(--pkit-mode-0);{kept}") == 1
    assert page.count(f"background:var(--pkit-mode-1);{kept}") == 1
    assert page.count(f"color:{viewing_browser.UNPAINTED};{kept}") == 3
    assert page.count(f'color:{viewing_browser.UNPAINTED}"') == 2
    held = f'{viewing_browser.MARKS["text"]}="{viewing_browser.FORCED_TEXT}"'
    forced_text = page.split(held)[1].split("</div></div>")[0]
    for each in (viewing_browser.FORCED_FIRST, viewing_browser.FORCED_SPAN):
        assert f">{each}</span>" in forced_text
    assert kept not in forced_text
    assert f"{viewing_browser.GROUND_MARK} " in page
    assert f"background:{viewing_browser.GROUND_COLOUR}" in page


def test_the_text_left_to_forcing_is_two_lines_on_their_grounds_closer_than_their_height() -> None:
    """Its first line with descenders, at a step below its font's height, each on a ground of
    its own beneath both lines, which no backplate covers (DEC-039 point 5)."""
    face = viewing_browser.PLANTED_FACE.read_bytes()
    page = viewing_browser._planted_html(face, SIGNALS, forced=True)
    lines = viewing_browser.FORCED_TEXTS[viewing_browser.FORCED_TEXT]
    assert [[each.text for each in line] for line in lines] == [
        [viewing_browser.FORCED_FIRST],
        [viewing_browser.FORCED_SPAN],
    ]
    cmap = TTFont(viewing_browser.PLANTED_FACE).getBestCmap()
    assert cmap is not None
    with TTFont(viewing_browser.PLANTED_FACE) as font:
        glyphs = font.getGlyphSet()
        upem = font["head"].unitsPerEm  # pyright: ignore[reportAttributeAccessIssue] fontTools types no table's fields
        foot = min(_bounds(glyphs, cmap[ord(each)])[1] for each in viewing_browser.FORCED_FIRST)
    assert foot < -0.15 * upem
    height = (viewing_browser.ASCENT + viewing_browser.DESCENT) * viewing_browser.SIZE
    assert height > viewing_browser.FORCED_STEP
    ground = f'{viewing_browser.MARKS["ground"]}="{viewing_browser.FORCED_TEXT}"'
    assert page.count(ground) == 2
    assert page.rindex(ground) < page.index(
        f'{viewing_browser.MARKS["text"]}="{viewing_browser.FORCED_TEXT}"'
    )


def test_the_forced_planted_files_layers_take_the_renderers_rules_under_forced_colours() -> None:
    """The browser forces no colour a shape's attribute holds, so the file mirrors the rules the
    renderer writes for a box opaque in every key with no stroke, from the declaration: its fill
    in the reader's text colour under its inset shape, in the reader's background colour, an
    edge's width inside it. The translucent box takes neither (DEC-037 point 5, DEC-039 point
    4)."""
    (html_declaration,) = load("visual-communication", "plugins.html_declaration")
    forced = html_declaration.DECLARATION["forced-colours"]
    face = viewing_browser.PLANTED_FACE.read_bytes()
    page = viewing_browser._planted_html(face, SIGNALS, forced=True)
    box = f'[data-layer] rect[fill="{viewing_browser.BOX}"]'
    assert (
        f"@media (forced-colors:active){{{box}{{fill:{forced['opaque-fills']}}}"
        f"{box}:not([stroke]){{fill:{forced['edge']['colour']}}}"
        f"{viewing_browser.PLANTED_FORCED_SHEET}}}"
    ) in page
    assert viewing_browser.TRANSLUCENT not in page.split("<style>")[1].split("</style>")[0]
    edge = forced["edge"]["width"]
    for shape, inset in re.findall(
        r'(<rect data-id="[^"]+"[^>]*/>)(<rect data-inset[^>]*/>)?', page
    ):
        geometry = {
            name: float(value) for name, value in re.findall(r'(x|y|width|height)="([^"]+)"', shape)
        }
        if (
            f'fill="{viewing_browser.BOX}"' in shape
            and min(geometry["width"], geometry["height"]) > 2 * edge
        ):
            held = {
                name: float(value)
                for name, value in re.findall(r'(x|y|width|height)="([^"]+)"', inset)
            }
            assert held == pytest.approx(
                {
                    "x": geometry["x"] + edge,
                    "y": geometry["y"] + edge,
                    "width": geometry["width"] - 2 * edge,
                    "height": geometry["height"] - 2 * edge,
                }
            )
        else:
            assert not inset


def test_the_planted_files_forced_rules_are_the_renderers() -> None:
    """What each of the renderer's files holds under forced colours, whatever it draws, the
    planted file holds too, so its grounds and its spans are forced as a piece's are."""
    (html,) = load("visual-communication", "plugins.html")
    assert viewing_browser.PLANTED_FORCED_SHEET == html.FORCED_SHEET


def test_the_plain_planted_page_holds_nothing_of_forcing() -> None:
    face = viewing_browser.PLANTED_FACE.read_bytes()
    page = viewing_browser._planted_html(face, SIGNALS)
    assert "forced-color" not in page
    assert viewing_browser.FORCED_TEXT not in page
    assert viewing_browser.GROUND_MARK not in page


def test_the_forced_planted_file_as_the_scene_holds_it_adds_the_text_left_to_forcing() -> None:
    (plain, own), (forced, forced_own) = (
        viewing_browser.PLANTED_PAGES,
        viewing_browser.PLANTED_FORCED_PAGES,
    )
    assert forced.texts == (
        *plain.texts,
        viewing_browser.Text(
            viewing_browser.FORCED_TEXT,
            ((viewing_browser.FORCED_FIRST,), (viewing_browser.FORCED_SPAN,)),
        ),
    )
    assert forced_own == own
    assert not viewing_browser.FORCED_FINDINGS & viewing_browser.PLANTED_FINDINGS


@pytest.mark.parametrize(
    "changes",
    [
        {"fault": {"kind": "die", "method": "Page.captureScreenshot", "document": FILE}},
        {"colours": {**COLOURS, "dark": COLOURS["light"]}},
    ],
    ids=["died", "first-read"],
)
def test_a_forced_starts_profile_is_removed_even_on_a_stop(
    tmp_path: Path, changes: dict[str, Any]
) -> None:
    forced_stopped(tmp_path, **changes)
    assert list((tmp_path / "local").iterdir()) == []


# A real browser.


def found_browser() -> Path | None:
    try:
        return viewing_browser.find()
    except viewing_browser.Stopped:
        return None


real_browser = pytest.mark.skipif(found_browser() is None, reason="no browser on this machine")


@real_browser
@pytest.mark.parametrize("scale", [0.625, 1.225, 2.0])
def test_a_real_browser_draws_each_loss_and_names_each_planted_fault_of_a_file(
    tmp_path: Path, scale: float
) -> None:
    """Each start reads the planted file. Read as a file too, at the smallest device scale a
    start draws at, at one between whole pixels and at the step's own, it shows what the reads
    give: each loss of what the page shows among it, with the share its cause loses, and the
    plants on either side of the sliver. What drew the page, and how it looks, this test
    leaves to the machine (DEC-037 point 5)."""
    file = tmp_path / "planted.html"
    face = viewing_browser.PLANTED_FACE.read_bytes()
    file.write_text(viewing_browser._planted_html(face, device=scale), encoding="utf-8")
    pages = list(viewing_browser.PLANTED_PAGES)
    browser = found_browser()
    assert browser is not None
    try:
        drawing = viewing_browser.draw(file, pages, scale, browser, tmp_path / "local")
    except viewing_browser.Stopped as stop:
        if stop.sandbox:
            pytest.skip(f"a sandbox stopped the browser: {stop}")
        raise
    read = drawing.shown[0].read
    assert viewing_browser._named(read) == viewing_browser.PLANTED_FINDINGS
    lost = {
        each.element: each.share
        for each in read.dropped
        if each.why in (viewing_browser.CUT, viewing_browser.COVERED)
    }
    assert all(share is not None and 0 < share <= 1 for share in lost.values())
    assert lost[viewing_browser.HACEK] < 1
    assert drawing.browser
    images = drawing.shown[0].images
    assert [each.page for each in images] == [page.id for page in pages]
    for image, page in zip(images, pages, strict=True):
        assert abs(image.width - page.width * scale) <= 1
        assert abs(image.height - page.height * scale) <= 1
    assert all(each.fonts for each in read.machine_fonts)
    assert list((tmp_path / "local").iterdir()) == []


@real_browser
def test_a_real_browser_draws_each_region_of_a_page_as_wide_as_the_page(tmp_path: Path) -> None:
    """Two bands of the planted file's first page, which overlap, at a scale of 2: the reads
    still read it whole, once."""
    file = tmp_path / "planted.html"
    face = viewing_browser.PLANTED_FACE.read_bytes()
    file.write_text(viewing_browser._planted_html(face, device=2.0), encoding="utf-8")
    page, own = viewing_browser.PLANTED_PAGES
    half = page.height / 2
    regions = ((0.0, half + 10), (half - 10, page.height - half + 10))
    browser = found_browser()
    assert browser is not None
    try:
        drawing = viewing_browser.draw(
            file,
            [dataclasses.replace(page, regions=regions), own],
            2.0,
            browser,
            tmp_path / "local",
        )
    except viewing_browser.Stopped as stop:
        if stop.sandbox:
            pytest.skip(f"a sandbox stopped the browser: {stop}")
        raise
    assert viewing_browser._named(drawing.shown[0].read) == viewing_browser.PLANTED_FINDINGS
    assert [(each.band, each.width, each.height) for each in drawing.shown[0].images] == [
        *((number, page.width * 2, height * 2) for number, (_, height) in enumerate(regions, 1)),
        (0, own.width * 2, own.height * 2),
    ]


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
    from tests.test_visual_communication_html import REFERENCE, draw, reference_picture, seam

    file = tmp_path / "reference.html"
    shown = seam.Shown(reference_picture(tmp_path), seam.PNG)
    file.write_bytes(draw(REFERENCE, pictures={"first/picture": shown}).document)
    browser = found_browser()
    assert browser is not None
    pages = scene_pages(REFERENCE)
    try:
        drawing = viewing_browser.draw(file, pages, 1.225, browser, tmp_path / "local")
    except viewing_browser.Stopped as stop:
        if stop.sandbox:
            pytest.skip(f"a sandbox stopped the browser: {stop}")
        raise
    assert drawing.shown[0].read == viewing_browser.Read((), (), (), (), ())
    assert [each.page for each in drawing.shown[0].images] == [page.id for page in pages]


@real_browser
def test_a_real_browser_draws_the_reference_file_in_each_of_its_modes_clean(
    tmp_path: Path,
) -> None:
    """Its two keys, light and dark, from one start: each mode reads clean, each repaints the
    file, and the first read finds that setting the signal repaints its own page."""
    from tests.test_visual_communication_html import reference, reference_picture

    file = tmp_path / "reference.html"
    file.write_bytes(reference({"square": reference_picture(tmp_path)}).document)
    browser = found_browser()
    assert browser is not None
    pages = scene_pages(REFERENCE_SCENE())
    signals = {"prefers-color-scheme": ("light", "dark")}
    modes = [{"prefers-color-scheme": "light"}, {"prefers-color-scheme": "dark"}]
    try:
        drawing = viewing_browser.draw(
            file, pages, 1.0, browser, tmp_path / "local", signals=signals, modes=modes
        )
    except viewing_browser.Stopped as stop:
        if stop.sandbox:
            pytest.skip(f"a sandbox stopped the browser: {stop}")
        raise
    light, dark = drawing.shown
    assert light.read == dark.read == viewing_browser.Read((), (), (), (), ())
    assert [each.image for each in light.images] != [each.image for each in dark.images]


@real_browser
@pytest.mark.parametrize("scale", [1.0, 2.0])
def test_a_real_browser_finds_each_loss_of_a_page_the_renderer_wrote(
    tmp_path: Path, scale: float
) -> None:
    """A text that runs past its page's right edge, and a text under a box drawn after it, as
    the renderer writes them: the read names the first as cut and the second as covered, each
    with the share it loses, and the text clear of both not at all (DEC-037 points 1 to 3)."""
    from tests.test_visual_communication_html import draw, element, of_pages, page_of, said

    losses = of_pages(
        page_of(
            "losses",
            200,
            100,
            {**said("losses/cut", "Spills"), "x": 170},
            {**said("losses/covered", "Under"), "y": 40},
            element("box", "losses/over", x=0, y=40, width=80, height=20, fill="surface"),
            {**said("losses/clear", "Clear"), "x": 100, "y": 70},
        )
    )
    file = tmp_path / "losses.html"
    file.write_bytes(draw(losses).document)
    read = drawn_by_a_real_browser(file, scene_pages(losses), scale, tmp_path).shown[0].read
    assert [(each.element, each.why) for each in read.dropped] == [
        ("losses/cut", viewing_browser.CUT),
        ("losses/covered", viewing_browser.COVERED),
    ]
    cut, covered = (each.share for each in read.dropped)
    assert cut is not None and 0 < cut < 1
    assert covered is not None and 0 < covered <= 1


def REFERENCE_SCENE() -> Mapping[str, Any]:
    from tests.test_visual_communication_html import REFERENCE

    return REFERENCE


@real_browser
def test_a_real_browser_under_forced_colours_names_each_planted_fault_in_each_palette(
    tmp_path: Path,
) -> None:
    """The forced start reads its own planted file first; read as a file too, each palette's
    reads name each planted fault, each loss of what the page shows among it, and each line of
    the text left to forcing shows ink in each, unnamed (DEC-037 point 5, DEC-039 point 5)."""
    file = tmp_path / "planted.html"
    face = viewing_browser.PLANTED_FACE.read_bytes()
    file.write_text(
        viewing_browser._planted_html(face, SIGNALS, forced=True, device=2.0), encoding="utf-8"
    )
    browser = found_browser()
    assert browser is not None
    try:
        drawing = viewing_browser.draw_forced(
            file,
            list(viewing_browser.PLANTED_FORCED_PAGES),
            2.0,
            browser,
            tmp_path / "local",
            signals=SIGNALS,
        )
    except viewing_browser.Stopped as stop:
        if stop.sandbox:
            pytest.skip(f"a sandbox stopped the browser: {stop}")
        raise
    light, dark = drawing.shown
    for shown in (light, dark):
        assert viewing_browser._named(shown.read) == viewing_browser.PLANTED_FINDINGS
    assert light.images[0].image != dark.images[0].image
    assert list((tmp_path / "local").iterdir()) == []


@real_browser
def test_a_real_browser_draws_the_reference_file_in_each_forced_palette_clean(
    tmp_path: Path,
) -> None:
    from tests.test_visual_communication_html import reference, reference_picture

    file = tmp_path / "reference.html"
    file.write_bytes(reference({"square": reference_picture(tmp_path)}).document)
    browser = found_browser()
    assert browser is not None
    pages = scene_pages(REFERENCE_SCENE())
    signals = {"prefers-color-scheme": ("light", "dark")}
    try:
        drawing = viewing_browser.draw_forced(
            file, pages, 1.0, browser, tmp_path / "local", signals=signals
        )
    except viewing_browser.Stopped as stop:
        if stop.sandbox:
            pytest.skip(f"a sandbox stopped the browser: {stop}")
        raise
    light, dark = drawing.shown
    assert light.read == dark.read == viewing_browser.Read((), (), (), (), ())
    assert [each.image for each in light.images] != [each.image for each in dark.images]


@dataclasses.dataclass(frozen=True)
class EmulationAlone:
    """What the browser found shows of the span left to forcing where only the emulation
    forces its colours: the browser, with its version and its program, and the forced palettes,
    in order, in which the span showed no ink."""

    browser: str
    unreached: tuple[str, ...]


@pytest.fixture(scope="module")
def emulation_alone(tmp_path_factory: pytest.TempPathFactory) -> EmulationAlone:
    """The forced start's first read's probe, in a start without the flag that forces the
    browser's colours: the planted file as that read writes it, read in each forced palette's
    emulation, and whether the text left to forcing left ink (DEC-027 point 4). Some browsers
    force the text under the emulation alone, and some leave it in the file's colours."""
    place = tmp_path_factory.mktemp("emulation-alone")
    file = place / viewing_browser.PLANTED_FORCED_FILE
    face = viewing_browser.PLANTED_FACE.read_bytes()
    file.write_text(
        viewing_browser._planted_html(face, SIGNALS, forced=True, device=2.0), encoding="utf-8"
    )
    program = found_browser()
    assert program is not None
    modes = [
        (palette.name, {**palette.signals, **viewing_browser.FORCED})
        for palette in viewing_browser.PALETTES
    ]
    try:
        drawing = viewing_browser._start(
            file,
            list(viewing_browser.PLANTED_FORCED_PAGES),
            2.0,
            program,
            place / "local",
            SIGNALS,
            modes,
        )
    except viewing_browser.Stopped as stop:
        if stop.sandbox:
            pytest.skip(f"a sandbox stopped the browser: {stop}")
        raise
    unreached = tuple(
        shown.palette
        for shown in drawing.shown
        if viewing_browser.FORCED_FINDINGS & viewing_browser._named(shown.read)
    )
    return EmulationAlone(f"{drawing.browser} ({program})", unreached)


def forced_without_the_flag(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Any:
    """The planted file drawn by the forced start of the browser found, its flag that forces
    the browser's colours swapped for one that changes nothing, so the emulation alone forces
    them: the drawing, or the stop its first read raised. The test skips where a sandbox stopped
    the browser."""
    monkeypatch.setattr(viewing_browser, "FORCING", "--no-first-run")
    file = tmp_path / "planted.html"
    face = viewing_browser.PLANTED_FACE.read_bytes()
    file.write_text(viewing_browser._planted_html(face, device=2.0), encoding="utf-8")
    browser = found_browser()
    assert browser is not None
    try:
        return viewing_browser.draw_forced(
            file,
            list(viewing_browser.PLANTED_PAGES),
            2.0,
            browser,
            tmp_path / "local",
            signals=SIGNALS,
        )
    except viewing_browser.Stopped as stop:
        if stop.sandbox:
            pytest.skip(f"a sandbox stopped the browser: {stop}")
        return stop


@real_browser
def test_a_real_browser_whose_colours_only_the_emulation_forces_stops_the_forced_start(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, emulation_alone: EmulationAlone
) -> None:
    """Where the emulation alone forces the shapes and leaves the text in the file's colours,
    as Chrome 157 does, the span left to forcing shows no ink without the flag, and the first
    read stops. Where it forces the text too, the span shows ink, and the first read rightly
    passes (DEC-027 point 4): the test skips there, naming the browser."""
    if not emulation_alone.unreached:
        pytest.skip(
            f"{emulation_alone.browser} forces the text under its emulation alone, so the span "
            "left to forcing shows ink in each forced palette without the flag"
        )
    stop = forced_without_the_flag(tmp_path, monkeypatch)
    assert isinstance(stop, viewing_browser.Stopped)
    assert stop.what.endswith("so the forced palette did not reach the text")


@real_browser
def test_a_real_browsers_forced_start_stops_exactly_where_the_span_left_to_forcing_shows_no_ink(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, emulation_alone: EmulationAlone
) -> None:
    """In any browser, without the flag: the first read stops, naming the first forced palette
    in which the span left to forcing showed no ink, and draws where it showed ink in each
    (DEC-027 point 4)."""
    drawn_or_stopped = forced_without_the_flag(tmp_path, monkeypatch)
    stopped = (
        drawn_or_stopped.what if isinstance(drawn_or_stopped, viewing_browser.Stopped) else None
    )
    expected = (
        f"the first read set the forced palette `{emulation_alone.unreached[0]}`, and a span "
        "with no paint, left to forcing, left no ink, so the forced palette did not reach the "
        "text"
        if emulation_alone.unreached
        else None
    )
    assert stopped == expected, emulation_alone.browser


def drawn_by_a_real_browser(file: Path, pages: Sequence[Any], scale: float, tmp_path: Path) -> Any:
    """`file` drawn by the browser found, at `scale`; the test skips where a sandbox stopped
    it."""
    browser = found_browser()
    assert browser is not None
    try:
        return viewing_browser.draw(file, pages, scale, browser, tmp_path / "local")
    except viewing_browser.Stopped as stop:
        if stop.sandbox:
            pytest.skip(f"a sandbox stopped the browser: {stop}")
        raise


@real_browser
def test_a_real_browser_draws_each_fixed_page_alone_at_its_own_size_and_clean(
    tmp_path: Path,
) -> None:
    """The reference file, its pages fixed pages (DEC-031 point 5), its arrow clear of the text
    it crosses: the window holds each at its own size with its gutters, so none stops the
    drawing, each image is its page alone, and the reads read clean. What lies around a page
    is the file's tests' to read: no test holds a pixel (DEC-015 point 6)."""
    from tests.test_visual_communication_html import REFERENCE, draw, reference_picture, seam

    shown = seam.Shown(reference_picture(tmp_path), seam.PNG)
    file = tmp_path / "fixed.html"
    clear = clear_of_its_text(REFERENCE)
    file.write_bytes(
        draw({**clear, "fixed-pages": True}, pictures={"first/picture": shown}).document
    )
    pages = scene_pages(clear)

    drawn = drawn_by_a_real_browser(file, pages, 2.0, tmp_path).shown[0]

    assert drawn.read == viewing_browser.Read((), (), (), (), ())
    assert [(each.page, each.band) for each in drawn.images] == [(page.id, 0) for page in pages]
    assert [(each.width, each.height) for each in drawn.images] == [
        (page.width * 2, page.height * 2) for page in pages
    ]


def clear_of_its_text(scene: Mapping[str, Any]) -> dict[str, Any]:
    """The reference scene with its second page's arrow below the text it crosses. Its line
    runs over the text's first letters, so at a device scale of 2, where it fills its device
    rows, it hides some of their strong ink, which the read names as covered (DEC-037 point
    1)."""
    clear = copy.deepcopy(dict(scene))
    [arrow] = [
        each
        for page in clear["children"]
        for each in page["children"]
        if each.get("id") == "second/arrow"
    ]
    arrow.update(y=40, y1=40, y2=40)
    return clear


#: What the browser holds of the document's first page and of the window.
MEASURED = """() => {
  const {width, left, top} = document.querySelector('[data-page]').getBoundingClientRect();
  return {width, left, top, window: innerWidth, scrolls: document.documentElement.scrollWidth};
}"""


@real_browser
def test_in_a_real_browsers_narrow_window_a_fixed_page_shrinks_and_nothing_scrolls_sideways(
    tmp_path: Path,
) -> None:
    """A deck's slide 1280 px wide in a window 500 px wide, as DEC-031's test drew it (point 4):
    the gutter narrows to its share of the window, 20 px, the slide shrinks to the 460 px it
    leaves, and the document is no wider than the window."""
    from tests.test_visual_communication_html import SLIDES, draw

    file = tmp_path / "slides.html"
    file.write_bytes(draw(SLIDES).document)

    with opened_by_a_real_browser(file, tmp_path, 500) as started:
        measured = started.ask(MEASURED)

    assert (measured["window"], measured["scrolls"]) == (500, 500)
    assert (measured["width"], measured["left"], measured["top"]) == (460, 20, 20)


@contextlib.contextmanager
def opened_by_a_real_browser(file: Path, tmp_path: Path, window: float) -> Iterator[Any]:
    """`file` open in the browser found, in a window `window` px wide, at a scale of 1. The
    test skips where a sandbox stopped the browser."""
    browser = found_browser()
    assert browser is not None
    place = tmp_path / "browser"
    place.mkdir()
    started = viewing_browser._Started(browser, place, window, 1.0)
    try:
        started.call("Browser.getVersion", within=viewing_browser.START_SECONDS)
        started.open_tab()
        started.open(file.resolve().as_uri())
        yield started
    except viewing_browser.Stopped as stop:
        if stop.sandbox:
            pytest.skip(f"a sandbox stopped the browser: {stop}")
        raise
    finally:
        started.close()


# A real browser's print (DEC-026 point 7). The test prints the file in the step's browser and
# counts its sheets, as no step does. It asserts no mode, and nothing of where a page that runs
# on breaks.

#: A sheet of A4, upright and turned, in inches, at the margins of Chrome's print dialog: an
#: area 717 px wide and 1,045 px high upright, at CSS's 96 px to the inch.
A4_UPRIGHT = {"paperWidth": 8.27, "paperHeight": 11.69}
A4_TURNED = {"paperWidth": 11.69, "paperHeight": 8.27}
MARGINS = {f"margin{side}": 0.4 for side in ("Top", "Bottom", "Left", "Right")}


def sheets_of(pdf: bytes) -> int:
    """How many sheets a PDF the browser printed holds: its objects of a page."""
    return len(re.findall(rb"/Type\s*/Page\b", pdf))


def printed_by_a_real_browser(
    drawn: Mapping[str, Any], tmp_path: Path, *sheets: Mapping[str, float]
) -> list[int]:
    """The page file of `drawn`, printed by the browser found on each of `sheets` with no
    background, as the dialog defaults: how many sheets each print takes."""
    from tests.test_visual_communication_html import draw

    file = tmp_path / "printed.html"
    file.write_bytes(draw(drawn).document)
    with opened_by_a_real_browser(file, tmp_path, 500) as started:
        printed = [started.call("Page.printToPDF", **sheet, **MARGINS)["data"] for sheet in sheets]
    return [sheets_of(base64.b64decode(each)) for each in printed]


def slides(count: int) -> dict[str, Any]:
    """A deck of `count` slides 1,280 by 720 px, as fixed pages."""
    from tests.test_visual_communication_html import fixed, of_pages, page_of, said

    return fixed(
        of_pages(
            *(
                page_of(f"deck/slides[{n}]", 1280, 720, said(f"deck/slides[{n}]/title", f"S{n}"))
                for n in range(count)
            )
        )
    )


def pages(count: int, width: float, height: float) -> dict[str, Any]:
    """`count` pages of one size that are no fixed pages, each with a text."""
    from tests.test_visual_communication_html import of_pages, page_of, said

    return of_pages(
        *(
            page_of(f"site/{n}", width, height, said(f"site/{n}/title", f"P{n}"))
            for n in range(count)
        )
    )


@real_browser
def test_a_real_browser_prints_a_decks_slides_two_to_a_sheet_of_a4_upright_and_one_turned(
    tmp_path: Path,
) -> None:
    """Points 1 to 3: four 16:9 slides each print whole inside its keyline. On A4 upright two
    share a sheet, at about 0.56 of their size; turned, each takes a sheet of its own."""
    assert printed_by_a_real_browser(slides(4), tmp_path, A4_UPRIGHT, A4_TURNED) == [2, 4]


@real_browser
def test_a_real_browser_moves_a_page_that_does_not_fit_the_rest_of_a_sheet_whole_to_the_next(
    tmp_path: Path,
) -> None:
    """Point 1: three pages 650 px high, each more than half a sheet, print on a sheet each. A
    page cut at a sheet's foot would let them take two."""
    assert printed_by_a_real_browser(pages(3, 600, 650), tmp_path, A4_UPRIGHT) == [3]


@real_browser
def test_a_real_browser_runs_a_page_taller_than_a_sheet_on(tmp_path: Path) -> None:
    """Point 1: a page 2,500 px high at its own width runs on across three sheets of A4
    upright."""
    assert printed_by_a_real_browser(pages(1, 600, 2500), tmp_path, A4_UPRIGHT) == [3]


#: What the browser holds of each page as it lays the document out for print, and of the
#: document.
PRINT_MEASURED = """() => [...document.querySelectorAll('[data-page]')].map((page) => {
  const {width, height} = page.getBoundingClientRect();
  const held = getComputedStyle(page);
  return {
    width, height, drawing: page.clientWidth, border: held.borderTopWidth,
    page: held.printColorAdjust, document: getComputedStyle(document.body).printColorAdjust,
  };
})"""


@real_browser
@pytest.mark.parametrize("fixed_pages", [True, False], ids=["fixed pages", "pages that are none"])
def test_in_a_real_browsers_print_the_area_is_the_window_and_a_fixed_page_lies_inside_its_border(
    tmp_path: Path, fixed_pages: bool
) -> None:
    """Points 2, 3 and 5, as the browser lays the file out for print in an area 500 px wide: a
    slide 1,280 px wide prints at the area, its drawing 2 px narrower inside a border of 1 px,
    in its own proportions. A page that is none fills the area with no border. Each page keeps
    its colours exactly, and the document around it does not."""
    from tests.test_visual_communication_html import draw

    drawn = slides(1) if fixed_pages else {**slides(1), "fixed-pages": False}
    file = tmp_path / "printed.html"
    file.write_bytes(draw(drawn).document)

    with opened_by_a_real_browser(file, tmp_path, 500) as started:
        started.call("Emulation.setEmulatedMedia", media="print")
        [measured] = started.ask(PRINT_MEASURED)

    drawing = 498 if fixed_pages else 500
    border = (500 - drawing) / 2
    assert (measured["width"], measured["drawing"]) == (500, drawing)
    assert measured["height"] == drawing * 720 / 1280 + 2 * border
    assert measured["border"] == f"{border:g}px"
    assert (measured["page"], measured["document"]) == ("exact", "economy")
