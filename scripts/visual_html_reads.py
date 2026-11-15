"""Measure the HTML renderer's read of cover and cut through a browser, as visual-communication
DEC-037 gives it, beside what visual-communication DEC-045's measure of islands would name of
the same draws (project-kit#3262). A maintainer reruns it when the browser, the face or the read
changes, and compares what it prints with the figures a record gives.

    uv run python scripts/visual_html_reads.py dots [--mode MODE] [--from EM] [--to EM]
        [--step EM] [--em EM]... [--scale SCALE]... [--face FILE] [--browser PROGRAM]
    uv run python scripts/visual_html_reads.py grazes [--mode MODE] [--words WORDS]
        [--from EM] [--to EM] [--step EM] [--em EM]... [--scale SCALE]... [--face FILE]
        [--browser PROGRAM]
    uv run python scripts/visual_html_reads.py planted [--scale SCALE]... [--browser PROGRAM]
    uv run python scripts/visual_html_reads.py deck [PIECE] [--language LANGUAGE]...

`dots` and `grazes` draw at each em from `--from` to `--to` (10 to 40 for `dots`, 10 to 20 for
`grazes`, by default) in steps of `--step` (0.1), or at each `--em` alone where any is given,
in device pixels, and at each device scale (the five of `tests/test_visual_communication_look.py`
by default): the ems and scales `scripts/visual_svg_reads.py` draws at. They set their plants in
Source Sans Pro Regular, or in the face `--face` names; the faces of the test brand
(`tests/fixtures/visual-communication/libraries/test-brand/1.0.0/fonts`) are the deck's. Each
plant at each em is a text of a page the HTML renderer writes, as the renderer's tests write
one (`tests/test_visual_communication_html.py`), and the browser `viewing_browser.find` finds,
or `--browser`, draws them through the viewing step's own module.

- **The mode.** `--mode` draws the pages in a light key (`light`, the default), in a dark key
  (`dark`), whose file names the dark scheme alone, so the reads draw a span light on dark, or
  in the browser's two forced palettes, in a start of their own (`forced`), as the look draws a
  file with its forced colours asked (DEC-027 point 3).
- **Two draws at each scale.** The first reads every span of the probe's pages, as no
  pre-filter passes over one there, and finds each plant's ink in the read's own draw alone,
  in each palette the mode draws. The second lays a box drawn after each plant, and is the read
  as built. Both start with the step's first read of its planted file. Neither reads whether
  the probe's own spans left ink, which it never prints.
- **What it reads.** Each tally the read makes is read again, from its own four images, for
  each pixel of each span's ink (`INKED`): how dark the span's letters alone make it, and how
  much of that the page drawn whole still shows. So the probe counts what the read counts, and
  says where it counts otherwise. Each tally's palette is named from the two colours it read
  in: light or dark, and forced where the start forced its colours.
- **What DEC-045 would name.** For each span, beside what the read names, its measure of
  islands (`viewing_tool._takes_an_island`), at the levels and joining the outputs page holds,
  on the pixels the tally read: on the page, a pixel the page drawn whole does not change at all
  is hidden wholly, and how far it changes it is what shows; past the page's edge, each pixel
  is cut.

The commands:

- **dots.** It sets the five dots `scripts/visual_svg_reads.py` hides whole (`DOTS` there): a
  full stop after "end" and a decimal point in "3.5", each a run of its own, the dot of ż, and
  the same full stop and point inside their run, "end." and "3.5". The second draw lays a box
  over all of each dot's ink found in the first, a device pixel past it on each side. It prints
  a line for each em, scale and palette: the em the read takes, the sliver's area there, and
  for each dot its pixels of strong ink and of any ink, the strong pixels the box hid of its
  span, whether the box hid every pixel of the dot and how many of the span's other pixels it
  hid, and whether the read named the span as covered. Then, for each palette and dot, the
  draws at which the box hid it whole, those at which it holds no strong ink, those the read
  named and those it left unnamed, by em, and its strong ink as a share of the em squared; for
  those left unnamed, what DEC-045's threshold, in whole pixels, and its measure would name.
- **grazes.** It sets words with descenders, DEC-045's graze plant "Typography gypsy" or,
  with `--words edge-control`, the edge control's "jogging" (DEC-037 point 5), each step a text
  of its own, so each lies at its own place among the device's pixels. The second draw lays a
  box whose top edge lies at each of `GRAZE_STEPS`, in eighths of a device pixel above the foot
  of the words' counted ink, the lowest any palette found in the first, across the whole line.
  It prints a line for each em, scale and palette: at each step the strong pixels the box hid,
  marked where the read names it and where the measure takes an island the read leaves unnamed.
  Then, for each palette, the steps the read names, those at which the measure takes an island,
  and of those each the read leaves unnamed, with its em, scale and step; and for each draw's
  least graze, the first step that hides a strong pixel wholly, how often each names it.
- **planted.** At each scale, the planted file as each start's first read draws it, light and
  in each forced palette, and the same file in a dark key, its scheme dark, drawn as the file a
  look draws. It prints the edge control and the háček plant in each: the strong ink the box
  hid against the sliver, the counted ink it hid wholly, and whether DEC-045's threshold and
  its measure would name it.
- **deck.** One look of `PIECE` (the showcase deck, `showcase`, by default) through the HTML
  renderer, in each of its keys and its forced palettes, in its source language or each
  `--language`, the reads as built. For each file and palette it prints the spans the read
  tallied, the entries of cut and cover the sliver names, and those the measure would add, each
  by its text; and the planted file of each start, as `planted` does.

It writes nothing in the repository but what the look writes in the clone's local folder: the
probe's pages and the browser's profile lie in a throwaway folder. Exit codes: 0 when it
measured, 1 when the browser stopped or the look did not draw, 2 on a usage error.
"""

from __future__ import annotations

import argparse
import contextlib
import importlib
import json
import math
import sys
import tempfile
from collections.abc import Collection, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / ".pkit" / "capabilities" / "visual-communication" / "scripts"

Pixel = tuple[int, int]

#: The em, in device pixels, from which a draw counts as large in the summary, as
#: `scripts/visual_svg_reads.py` splits its own.
LARGE = 25.0

#: The name of the file the probe's pages are written to, and the prefix of its pages' ids.
FILE = "probe.html"
PAGE = "probe"

#: Each plant's cell on its page, in ems of its font: wide and high enough that the boxes of two
#: plants' spans, each widened by its em, never meet, and that each stays on its page, so the
#: read's room past the page's edges is none. A cell is at least `CELL_WIDTH` wide, and as wide
#: as its text, each character at most `ADVANCE`, with `TEXT_LEFT` on each side. The text's top
#: and its baseline, in the same ems, from the cell's top.
CELL_WIDTH = 6.0
CELL_HEIGHT = 4.5
ADVANCE = 0.6
TEXT_LEFT = 1.5
TEXT_TOP = 1.0
BASELINE = 1.2

#: How wide a page's row of cells may run, and how high a page may grow, in device pixels, so
#: that no image the read takes of a page grows past what a browser draws at once.
ROW_PIXELS = 4000.0
PAGE_PIXELS = 1200.0

#: The fills a line's runs take by turns, so that each is a span of its own: the renderer
#: writes runs of one look as one span.
RUN_FILLS = ("ink", "accent")

#: The fill of the box over a plant, and the key a light page is drawn in.
BOX_FILL = "surface"
KEY = "default"

#: The modes a probe draws its pages in: a light key, a dark key, and the browser's forced
#: palettes, both in a start of its own (DEC-027 point 3). A tally's palette is named by the
#: first two, and by `FORCED` before one of them where the start forced its colours.
LIGHT = "light"
DARK = "dark"
FORCED = "forced"
MODES = (LIGHT, DARK, FORCED)

#: The signal every emulation of a start that forces its colours sets (`viewing_browser.FORCED`).
FORCED_SIGNAL = "forced-colors"

#: For each span a tally reads, each pixel of its box widened by its em where its letters
#: alone leave ink, from the tally's own four images, as the tally reads them
#: (`viewing_browser.TALLY`): its row and column in the images, how far its letters alone
#: change it, and how far they change it in the page drawn whole, each the most of the three
#: channels; with the two colours, their difference, and the images' size.
INKED = """async (images, clip, spans) => {
  const decode = async (data) => {
    const bytes = Uint8Array.from(atob(data), (character) => character.charCodeAt(0));
    const bitmap = await createImageBitmap(new Blob([bytes], {type: 'image/png'}), {
      colorSpaceConversion: 'none',
      premultiplyAlpha: 'none',
    });
    const canvas = new OffscreenCanvas(bitmap.width, bitmap.height);
    const context = canvas.getContext('2d', {willReadFrequently: true});
    context.drawImage(bitmap, 0, 0);
    return context.getImageData(0, 0, bitmap.width, bitmap.height);
  };
  const [strong, ground, shown, unshown] = await Promise.all(images.map(decode));
  const probe = document.createElement('div');
  probe.style.cssText = 'color:CanvasText;background-color:Canvas';
  document.body.append(probe);
  const channels = (colour) => (colour.match(/[\\d.]+/g) || []).slice(0, 3).map(Number);
  const text = channels(getComputedStyle(probe).color);
  const behind = channels(getComputedStyle(probe).backgroundColor);
  probe.remove();
  const apart = Math.max(...text.map((value, index) => Math.abs(value - behind[index])));
  const wide = strong.width, across = strong.width / clip.width, down = strong.height / clip.height;
  const most = (one, other, at) => Math.max(
    Math.abs(one.data[at] - other.data[at]),
    Math.abs(one.data[at + 1] - other.data[at + 1]),
    Math.abs(one.data[at + 2] - other.data[at + 2]),
  );
  return {apart, text, behind, width: strong.width, height: strong.height, spans: spans.map(
    ({index, box}) => {
      const left = Math.max(0, Math.floor((box.x - clip.x) * across));
      const right = Math.min(wide, Math.ceil((box.x + box.width - clip.x) * across));
      const top = Math.max(0, Math.floor((box.y - clip.y) * down));
      const bottom = Math.min(strong.height, Math.ceil((box.y + box.height - clip.y) * down));
      const pixels = [];
      for (let row = top; row < bottom; row++) {
        for (let column = left; column < right; column++) {
          const at = (row * wide + column) * 4;
          const alone = most(strong, ground, at);
          if (alone) pixels.push([row, column, alone, most(shown, unshown, at)]);
        }
      }
      return {index, pixels};
    },
  )};
}"""


@dataclass(frozen=True)
class Modules:
    """What the probe draws with: the SVG probe, for its dots and how it finds one in its run's
    ink; the look's tests, for the viewing step, its browser module and the SVG reads' two
    tests; and the HTML renderer's tests, for a scene and the renderer."""

    reads: ModuleType
    look: ModuleType
    html: ModuleType


def modules() -> Modules:
    """The modules the probe draws with, the repository's root put on the import path once."""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    return Modules(
        importlib.import_module("scripts.visual_svg_reads"),
        importlib.import_module("tests.test_visual_communication_look"),
        importlib.import_module("tests.test_visual_communication_html"),
    )


def picture_start(at: float, scale: float) -> int:
    """The device pixel a browser's picture of a clip starts at, on one axis, where the clip
    starts at `at` px and the browser draws `scale` device pixels to a px: the one nearest,
    a half rounding up. Each of the picture's pixels is the next device pixel, so a picture
    holds the clip's size times the scale, rounded. Measured of Chrome's pictures at the
    scales 0.5, 0.8167 and 1.225, where neither the clip's start nor its size need fall on
    a device pixel (project-kit#3262)."""
    return math.floor(at * scale + 0.5)


def palette_of(text: Sequence[float], behind: Sequence[float], forced: bool) -> str:
    """The palette a tally read in, from its two colours: `LIGHT` where its ground is lighter
    than its text, `DARK` otherwise, after `FORCED` where the start forced its colours."""
    scheme = LIGHT if sum(behind) > sum(text) else DARK
    return f"{FORCED} {scheme}" if forced else scheme


@dataclass(frozen=True)
class Spot:
    """A span as a tally read it: its place among the document's spans, its font size in px,
    its page's box and the tally's clip in px of the document, the device pixels to a px the
    browser drew at, the two colours' difference, each pixel of its ink with how far its
    letters alone change it and how far the page drawn whole does, what the tally itself
    counted, its strong ink, and of that what lies past its page and what its page hides, and
    the size of the tally's images, in pixels."""

    index: int
    em: float
    page: Mapping[str, float]
    clip: Mapping[str, float]
    scale: float
    apart: float
    pixels: Mapping[Pixel, tuple[int, int]]
    counted: Mapping[str, int]
    size: tuple[int, int]

    def is_strong(self, pixel: Pixel) -> bool:
        """Whether its letters alone change `pixel` by more than half the two colours'
        difference, as the tally counts strong ink."""
        return 2 * self.pixels[pixel][0] > self.apart

    def is_past(self, pixel: Pixel) -> bool:
        """Whether `pixel` lies past its page's edge, as the tally places a pixel: by its
        centre, in px of the document."""
        row, column = pixel
        across = self.size[0] / self.clip["width"]
        down = self.size[1] / self.clip["height"]
        x = self.clip["x"] + (column + 0.5) / across
        y = self.clip["y"] + (row + 0.5) / down
        page = self.page
        return (
            y < page["y"]
            or y >= page["y"] + page["height"]
            or x < page["x"]
            or x >= page["x"] + page["width"]
        )

    @property
    def ink(self) -> dict[Pixel, int]:
        """Each pixel's darkness, drawn black on white: 0 where its letters alone change it by
        the whole difference between the two colours, 255 where by none."""
        return {
            pixel: 255 - round(255 * alone / self.apart)
            for pixel, (alone, _) in self.pixels.items()
        }

    @property
    def beyond(self) -> list[Pixel]:
        """The pixels of its ink past its page's edge."""
        return [pixel for pixel in self.pixels if self.is_past(pixel)]

    @property
    def shows(self) -> dict[Pixel, int]:
        """How much of each pixel's ink on its page the page drawn whole still shows, from 0 to
        255."""
        return {
            pixel: round(255 * whole / self.apart)
            for pixel, (_, whole) in self.pixels.items()
            if not self.is_past(pixel)
        }

    @property
    def hidden(self) -> list[Pixel]:
        """The pixels of its ink on its page the page drawn whole does not change at all."""
        return [
            pixel
            for pixel, (_, whole) in self.pixels.items()
            if not whole and not self.is_past(pixel)
        ]

    def agrees(self) -> bool:
        """Whether the probe counts its strong ink, of that what lies past its page and what its
        page hides, as the tally does."""
        strong = [pixel for pixel in self.pixels if self.is_strong(pixel)]
        past = [pixel for pixel in strong if self.is_past(pixel)]
        hidden = sum(not self.pixels[pixel][1] for pixel in strong if not self.is_past(pixel))
        counted = (self.counted["strong"], self.counted.get("past", 0), self.counted["hidden"])
        return (len(strong), len(past), hidden) == counted

    def page_box(self, pixels: Sequence[Pixel], margin: int = 0) -> dict[str, float]:
        """The box on its page, in its px, that holds each of `pixels` whole, `margin` pixels
        past them on each side, each pixel where the picture took it (`picture_start`)."""
        rows = [row for row, _ in pixels]
        columns = [column for _, column in pixels]
        column = picture_start(self.clip["x"], self.scale)
        row = picture_start(self.clip["y"], self.scale)
        left = (column + min(columns) - margin) / self.scale - self.page["x"]
        right = (column + max(columns) + 1 + margin) / self.scale - self.page["x"]
        top = (row + min(rows) - margin) / self.scale - self.page["y"]
        bottom = (row + max(rows) + 1 + margin) / self.scale - self.page["y"]
        return {"x": left, "y": top, "width": right - left, "height": bottom - top}

    def row_on_page(self, row: float) -> float:
        """Where the top of the picture's row `row` lies on its page, in its px."""
        return (picture_start(self.clip["y"], self.scale) + row) / self.scale - self.page["y"]


@dataclass(frozen=True)
class Placed:
    """A span of the document as the read found it: its page's id, its text's, the number of
    its line and its place in the line, its characters and its font size in px."""

    page: str
    text: str
    line: int
    at: int
    characters: str
    em: float


@dataclass
class Reading:
    """What the reads of one file asked of the browser under one emulation: each span of the
    last document they read, by its place among the document's spans, each span a tally read,
    and the palette the tallies read in (`palette_of`), empty where none tallied."""

    file: str
    placed: dict[int, Placed] = field(default_factory=dict[int, Placed])
    spots: dict[int, Spot] = field(default_factory=dict[int, Spot])
    palette: str = ""

    def spot(self, text: str, line: int = 0, at: int = 0) -> Spot | None:
        """The span a tally read of the text `text`, at `at` in its line `line`."""
        for index, placed in self.placed.items():
            if (placed.text, placed.line, placed.at) == (text, line, at):
                return self.spots.get(index)
        return None


@dataclass
class Capture:
    """What the reads asked of the browser, each file under each emulation a reading of its
    own, in the order they came, and the signals the browser emulates now."""

    readings: dict[tuple[str, str], Reading] = field(default_factory=dict[tuple[str, str], Reading])
    emulated: Mapping[str, str] = field(default_factory=dict[str, str])

    def _key(self, file: str) -> tuple[str, str]:
        return file, json.dumps(sorted(self.emulated.items()))

    def read(self, file: str, pages: Sequence[Mapping[str, Any]]) -> None:
        self.readings[self._key(file)] = Reading(
            file,
            {
                span["index"]: Placed(page["id"], text["id"], number, at, span["text"], span["em"])
                for page in pages
                for text in page["texts"]
                for number, line in enumerate(text["lines"])
                for at, span in enumerate(line)
            },
        )

    def tallied(
        self,
        file: str,
        clip: Mapping[str, float],
        scale: float,
        asked: Sequence[Mapping[str, Any]],
        counted: Sequence[Mapping[str, int]],
        inked: Mapping[str, Any],
    ) -> None:
        reading = self.readings.setdefault(self._key(file), Reading(file))
        reading.palette = palette_of(inked["text"], inked["behind"], FORCED_SIGNAL in self.emulated)
        by_index = {each["index"]: each for each in inked["spans"]}
        for each, count in zip(asked, counted, strict=True):
            index = each["index"]
            pixels = {
                (row, column): (alone, whole)
                for row, column, alone, whole in by_index[index]["pixels"]
            }
            placed = reading.placed.get(index)
            reading.spots[index] = Spot(
                index,
                placed.em if placed else 0.0,
                dict(each["page"]),
                dict(clip),
                scale,
                inked["apart"],
                pixels,
                dict(count),
                (inked["width"], inked["height"]),
            )

    def of(self, file: str) -> list[Reading]:
        """Each reading of `file` a tally read, in the order they came."""
        return [each for (held, _), each in self.readings.items() if held == file and each.spots]

    def files(self) -> list[str]:
        """Each file a tally read, in the order the reads first read it."""
        found: dict[str, None] = {}
        for (file, _), each in self.readings.items():
            if each.spots:
                found[file] = None
        return list(found)


def _is_probes(page: Mapping[str, Any]) -> bool:
    return str(page["id"]).startswith(PAGE)


@contextlib.contextmanager
def captured(browser: ModuleType, every: bool) -> Iterator[Capture]:
    """While it lasts, each document the browser module's reads read, and each tally they make,
    is kept in the capture it gives, by the name of the file open and the signals emulated.
    Where `every`, the pre-filter passes over no span of the probe's pages, so each is tallied.
    The read of whether a span left ink takes each of the probe's spans as inked, since the
    probe reads none of it."""
    started = browser._Started
    names = vars(browser)
    ask, emulate = started.ask, started.emulate
    passed_over, left_ink = names["_passed_over"], names["_left_ink"]
    capture = Capture()

    def asked(self: Any, function: str, *arguments: Any) -> Any:
        answer = ask(self, function, *arguments)
        file = str(self._own).rsplit("/", 1)[-1]
        if function == browser.READ:
            capture.read(file, answer)
        elif function == browser.TALLY:
            images, clip, spans = arguments
            inked = ask(self, INKED, images, clip, spans)
            capture.tallied(file, clip, self.scale, spans, answer, inked)
        return answer

    def emulated(self: Any, signals: Mapping[str, str]) -> None:
        capture.emulated = dict(signals)
        emulate(self, signals)

    def over(page: Mapping[str, Any], span: Mapping[str, Any], spans: Any) -> bool:
        if every and _is_probes(page):
            return False
        return passed_over(page, span, spans)

    def inked(started: Any, page: Mapping[str, Any], *rest: Any) -> bool:
        return True if _is_probes(page) else left_ink(started, page, *rest)

    started.ask, started.emulate = asked, emulated
    names["_passed_over"], names["_left_ink"] = over, inked
    try:
        yield capture
    finally:
        started.ask, started.emulate = ask, emulate
        names["_passed_over"], names["_left_ink"] = passed_over, left_ink


@dataclass(frozen=True)
class Plant:
    """A plant set at an em: its page's trace id and its text's, its mark as the SVG probe's
    `Dot` gives it, the em in device pixels, its font size in px, its cell's left and top on its
    page, and for a graze the step of its box's edge (`GRAZE_STEPS`)."""

    page: str
    text: str
    dot: Any
    em: float
    size: float
    left: float
    top: float
    step: int = 0


@dataclass(frozen=True)
class Laid:
    """A page of plants: its trace id, its size in px, and its plants."""

    id: str
    width: float
    height: float
    plants: tuple[Plant, ...]


def cell_width(dot: Any) -> float:
    """How wide `dot`'s cell is, in ems: as wide as its text, each character at most `ADVANCE`,
    with `TEXT_LEFT` on each side, and at least `CELL_WIDTH`."""
    return max(CELL_WIDTH, 2 * TEXT_LEFT + ADVANCE * len("".join(dot.runs)))


def laid(
    dots: Sequence[Any], ems: Sequence[float], scale: float, steps: Sequence[int] = (0,)
) -> list[Laid]:
    """Each of `dots` at each of `ems` and each of `steps`, drawn at `scale`, in cells laid left
    to right in rows no wider than `ROW_PIXELS`, and rows down pages no higher than
    `PAGE_PIXELS`, at least one cell to a row and one row to a page. A page is as wide as its
    widest row."""
    cells = [(em, dot, step) for em in ems for dot in dots for step in steps]
    pages: list[Laid] = []
    rows: list[list[Plant]] = []
    width = height = across = high = 0.0
    page = f"{PAGE}-0"

    def close() -> None:
        nonlocal rows, width, height
        if rows:
            plants = tuple(plant for row in rows for plant in row)
            pages.append(Laid(page, width, height, plants))
        rows, width, height = [], 0.0, 0.0

    for em, dot, step in cells:
        size = em / scale
        wide, tall = cell_width(dot) * size, CELL_HEIGHT * size
        if rows and (across + wide) * scale > ROW_PIXELS:
            height += high
            across, high = 0.0, 0.0
            if (height + tall) * scale > PAGE_PIXELS:
                close()
                page = f"{PAGE}-{len(pages)}"
            rows.append([])
        if not rows:
            rows.append([])
        text = f"{page}/{len(rows) - 1}-{len(rows[-1])}"
        rows[-1].append(Plant(page, text, dot, em, size, across, height, step))
        across += wide
        high = max(high, tall)
        width = max(width, across)
    height += high
    close()
    return pages


def scene_of(html_tests: ModuleType, pages: Sequence[Laid], boxes: Mapping[str, Any]) -> Any:
    """The scene of `pages`, each plant a text of one line of its dot's runs, each run a span of
    its own, and where `boxes` holds a box for its text, that box drawn after it."""
    children = []
    for page in pages:
        held = []
        for plant in page.plants:
            held.append(text_of(html_tests, plant))
            if plant.text in boxes:
                box = boxes[plant.text]
                held.append(html_tests.element("box", f"{plant.text}/over", fill=BOX_FILL, **box))
        children.append(html_tests.page_of(page.id, page.width, page.height, *held))
    return html_tests.of_pages(*children)


def text_of(html_tests: ModuleType, plant: Plant) -> dict[str, Any]:
    """The text of `plant`: its dot's runs on one line, its baseline `BASELINE` ems below its
    top, as wide as its cell."""
    size = plant.size
    runs = [
        html_tests.run(words, fill=RUN_FILLS[at % len(RUN_FILLS)], **{"font-size": size})
        for at, words in enumerate(plant.dot.runs)
    ]
    spans = [(at, words, ADVANCE * size * len(words)) for at, words in enumerate(plant.dot.runs)]
    return html_tests.element(
        "text",
        plant.text,
        x=plant.left + TEXT_LEFT * size,
        y=plant.top + TEXT_TOP * size,
        width=(cell_width(plant.dot) - TEXT_LEFT) * size,
        height=CELL_HEIGHT * size / 2,
        text="".join(plant.dot.runs),
        paragraphs=[runs],
        lines=[html_tests.line(0, BASELINE * size, *spans)],
        **{"line-height": CELL_HEIGHT * size / 2, "measured-height": CELL_HEIGHT * size / 2},
    )


def written(html_tests: ModuleType, scene: Any, face: Path, mode: str) -> bytes:
    """The page file the HTML renderer writes of `scene` in `face`, holding the one key `mode`
    draws: the dark key where it is `DARK`, so the file names the dark scheme alone, and the
    light key otherwise."""
    key, combination = (DARK, html_tests.DARK) if mode == DARK else (KEY, html_tests.LIGHT)
    return html_tests.html.render(
        scene,
        form="html",
        keys={key: combination},
        colours={key: html_tests.COLOURS},
        font_file=lambda _family: face,
        pictures={key: {}},
    ).document


def palette_shown(shown: Any, mode: str) -> str:
    """The palette a mode of a drawing was drawn in, as `palette_of` names a tally's: the forced
    palette's name after `FORCED`, or the mode's own key."""
    return f"{FORCED} {shown.palette}" if shown.palette else mode


@dataclass(frozen=True)
class Drawn:
    """One draw of the probe's pages at a scale: what the reads asked of the browser, and what
    they named of the probe's file in each palette, by its name (`palette_shown`)."""

    capture: Capture
    named: Mapping[str, frozenset[tuple[str, str, str]]]


def drawn(
    found: Modules,
    face: Path,
    pages: Sequence[Laid],
    scale: float,
    program: Path,
    boxes: Mapping[str, Any],
    mode: str = LIGHT,
    *,
    every: bool,
) -> Drawn:
    """`pages` written by the HTML renderer in `face`, with `boxes`, and drawn at `scale` by
    `program` through the viewing step's browser module, in `mode`. Raises its Stopped."""
    browser = found.look.viewing_browser
    viewing = found.look.viewing
    scene = scene_of(found.html, pages, boxes)
    document = written(found.html, scene, face, mode)
    wanted = [viewing.browser_page(page) for page in viewing.pages_of(scene)]
    with tempfile.TemporaryDirectory(prefix="visual-html-reads-") as folder:
        file = Path(folder) / FILE
        file.write_bytes(document)
        local = Path(folder) / "local"
        with captured(browser, every) as capture:
            if mode == FORCED:
                drawing = browser.draw_forced(file, wanted, scale, program, local)
            else:
                drawing = browser.draw(file, wanted, scale, program, local)
    named = {
        palette_shown(shown, mode): frozenset(
            (each.element, each.text, each.why) for each in shown.read.dropped
        )
        for shown in drawing.shown
    }
    return Drawn(capture, named)


def _union(boxes: Sequence[Mapping[str, float]]) -> dict[str, float]:
    """The least box that holds each of `boxes`."""
    left = min(box["x"] for box in boxes)
    top = min(box["y"] for box in boxes)
    right = max(box["x"] + box["width"] for box in boxes)
    bottom = max(box["y"] + box["height"] for box in boxes)
    return {"x": left, "y": top, "width": right - left, "height": bottom - top}


def boxes_over(found: Modules, pages: Sequence[Laid], first: Drawn) -> dict[str, Any]:
    """For each plant whose dot the first draw found in its run's ink, in any palette, a box
    over all of the dot in each palette that found it, a device pixel past it on each side, in
    px of its page."""
    boxes: dict[str, Any] = {}
    readings = first.capture.of(FILE)
    for page in pages:
        for plant in page.plants:
            held = []
            for reading in readings:
                spot = reading.spot(plant.text, 0, plant.dot.at)
                if spot is None:
                    continue
                mine, _, _ = found.reads.dot_pixels(plant.dot, spot.ink)
                if mine:
                    held.append(spot.page_box(mine, 1))
            if held:
                boxes[plant.text] = _union(held)
    return boxes


@dataclass(frozen=True)
class Hidden:
    """A dot under a box laid over all of it, as the read as built found it in one palette:
    the em the read takes, in device pixels, and the scale; the dot's pixels of any ink and of
    strong ink; whether the box hid every pixel of it, and how many of its span's other pixels
    it hid; the strong pixels of its span the box hid and the span's strong pixels, as the
    tally counts them; whether the read named the span as covered; the weakest level at which
    its run's ink falls into the dot's parts; whether DEC-045's threshold and its measure of
    islands would name it; whether the probe counts the span as the tally does; the strong
    pixels the box hid of the plant's other spans; and the palette. A dot the first draw did
    not find holds no ink."""

    dot: Any
    em: float
    scale: float
    ink: int = 0
    strong: int = 0
    whole: bool = False
    beyond: int = 0
    lost: int = 0
    found: int = 0
    named: bool = False
    apart: int = 0
    threshold: bool = False
    island: bool = False
    agrees: bool = True
    neighbours: int = 0
    palette: str = LIGHT

    @property
    def sliver(self) -> float:
        """The sliver's area at the em, in device pixels: the least the read names."""
        return 0.01 * self.em**2


def hidden_of(
    found: Modules, plant: Plant, scale: float, reading: Reading, named: Collection[Any]
) -> Hidden:
    """What `reading`, the second draw in one palette, found of `plant`'s dot under its box,
    where the read named `named` in that palette."""
    nothing = Hidden(plant.dot, plant.em, scale, palette=reading.palette)
    spot = reading.spot(plant.text, 0, plant.dot.at)
    if spot is None:
        return nothing
    ink = spot.ink
    mine, _, apart = found.reads.dot_pixels(plant.dot, ink)
    if not mine:
        return nothing
    hidden = set(spot.hidden)
    tool = found.look.viewing_tool
    em = spot.em * scale
    lost = spot.counted["hidden"]
    strong_hidden = sum(spot.is_strong(pixel) for pixel in hidden)
    others = [
        other
        for at in range(len(plant.dot.runs))
        if at != plant.dot.at
        for other in [reading.spot(plant.text, 0, at)]
        if other is not None
    ]
    covered = found.look.viewing_browser.COVERED
    return Hidden(
        plant.dot,
        em,
        scale,
        len(mine),
        sum(spot.is_strong(pixel) for pixel in mine),
        hidden.issuperset(mine),
        len(hidden.difference(mine)),
        lost,
        spot.counted["strong"],
        (plant.text, plant.dot.runs[plant.dot.at], covered) in named,
        apart,
        strong_hidden >= tool._least(em),
        tool._takes_an_island(ink, list(hidden), spot.shows),
        spot.agrees(),
        sum(other.counted["hidden"] for other in others),
        reading.palette,
    )


def line_of(em: float, scale: float, read: Sequence[Hidden]) -> str:
    """One em, scale and palette, as `dots` prints it."""
    said = []
    for each in read:
        if not each.ink:
            said.append(f"{each.dot.name} not found")
            continue
        said.append(
            f"{each.dot.name} {each.strong} of {each.ink}, hid {each.lost} of {each.found}"
            f" {'whole' if each.whole else 'part'} +{each.beyond},"
            f" {'named' if each.named else 'UNNAMED'}"
        )
    read_em = next((each.em for each in read if each.ink), em)
    palette = next((each.palette for each in read), "")
    return (
        f"em {em:5.1f}  scale {scale:<6g}  {palette:<12}  read em {read_em:7.3f}"
        f"  sliver {0.01 * read_em**2:6.2f} px  " + "; ".join(said)
    )


def summary(dots: Sequence[Any], every: Sequence[Hidden]) -> list[str]:
    """For each dot, what the read named and left unnamed of it, and what DEC-045's two tests
    would name of what it left; then where the probe counted otherwise than the read, and where
    a box hid a neighbour's strong ink."""
    lines: list[str] = []
    for dot in dots:
        held = [each for each in every if each.dot == dot]
        found = [each for each in held if each.ink]
        whole = [each for each in found if each.whole]
        faint = [each for each in found if not each.strong]
        named = [each for each in found if each.named]
        unnamed = [each for each in whole if not each.named]
        lines.append(
            f"{dot.name}: {len(held)} draws, found at {len(found)}, hidden whole at"
            f" {len(whole)}, with no strong ink at {len(faint)}{_ems(faint)}"
        )
        lines.append(
            f"  named by the read at {len(named)}; hidden whole and left unnamed at"
            f" {len(unnamed)}: {sum(each.em < LARGE for each in unnamed)} below an em of"
            f" {LARGE:g}, {sum(each.em >= LARGE for each in unnamed)} from {LARGE:g} on"
            f"{_ems(unnamed)}{_strong(unnamed)}"
        )
        if unnamed:
            by_threshold = [each for each in unnamed if each.threshold]
            by_island = [each for each in unnamed if each.island]
            neither = [each for each in unnamed if not (each.threshold or each.island)]
            lines.append(
                f"  of those, DEC-045's threshold names {len(by_threshold)}{_ems(by_threshold)},"
                f" its measure of islands {len(by_island)}{_ems(by_island)},"
                f" neither {len(neither)}{_ems(neither)}"
            )
            by_scale = {
                scale: sum(each.scale == scale for each in unnamed)
                for scale in sorted({each.scale for each in held})
            }
            lines.append(
                "  left unnamed by scale: "
                + ", ".join(f"{scale:g} {count}" for scale, count in by_scale.items())
            )
        shares = [each.strong / each.em**2 for each in found if each.strong]
        if shares:
            lines.append(
                f"  its strong ink, of the em squared: {min(shares):.4f} to {max(shares):.4f}"
            )
    otherwise = [each for each in every if each.ink and not each.agrees]
    clipped = [each for each in every if each.neighbours]
    lines.append(f"spans the probe counted otherwise than the read: {len(otherwise)}")
    lines.append(
        f"draws at which a box hid a neighbour's strong ink: {len(clipped)}{_ems(clipped)}"
    )
    return lines


def _ems(found: Sequence[Any]) -> str:
    if not found:
        return ""
    ems = sorted(each.em for each in found)
    return f" (ems {ems[0]:.1f} to {ems[-1]:.1f})"


def _strong(found: Sequence[Hidden]) -> str:
    if not found:
        return ""
    strong = sorted(each.strong for each in found)
    return f", the dot's strong pixels {strong[0]} to {strong[-1]}"


def palettes_of(every: Sequence[Any]) -> list[str]:
    """Each palette among `every`, in the order it first comes."""
    return list(dict.fromkeys(each.palette for each in every))


#: The planted file's plants the summary of each start reads (DEC-037 point 5): the edge
#: control, which the read leaves unnamed, and the háček plant, which it names.
PLANTED = ("edge-control", "hacek-under-a-box")

#: The file the planted file is written to, in a dark key, by `planted`.
PLANTED_DARK = "planted.dark.html"


def planted_lines(
    tool: ModuleType, browser: ModuleType, scale: float, capture: Capture
) -> list[str]:
    """The planted file's edge control and háček plant at `scale`, in each reading of the
    planted file `capture` holds, and of it in a dark key: the em the read takes, the strong
    pixels the box hid against the sliver, the counted pixels it hid wholly, and whether
    DEC-045's threshold and its measure of islands would name each."""
    lines = []
    for file in (browser.PLANTED_FILE, browser.PLANTED_FORCED_FILE, PLANTED_DARK):
        for reading in capture.of(file):
            if file == PLANTED_DARK and reading.palette.startswith(FORCED):
                continue
            where = "in a dark key, as a look's file" if file == PLANTED_DARK else "first read"
            for text in PLANTED:
                spot = reading.spot(text)
                if spot is None:
                    lines.append(f"  {text} at scale {scale:g}, {reading.palette}: not tallied")
                    continue
                lines.append(f"  {planted_line(tool, spot, text, scale, reading.palette)}, {where}")
    return lines


def planted_line(tool: ModuleType, spot: Spot, text: str, scale: float, palette: str) -> str:
    """One plant of the planted file, as `planted_lines` gives it."""
    em = spot.em * scale
    hidden = spot.hidden
    ink = spot.ink
    least = tool._least(em)
    strong = sum(spot.is_strong(pixel) for pixel in hidden)
    counted = sum(ink[pixel] <= tool.FAINT for pixel in hidden)
    named = strong >= least
    taken = tool._takes_an_island(ink, hidden, spot.shows)
    return (
        f"{text} at scale {scale:g}, {palette}: read em {em:.3f}, hid"
        f" {spot.counted['hidden']} of {spot.counted['strong']} strong against a sliver of"
        f" {0.01 * em**2:.2f} px, {counted} counted wholly;"
        f" DEC-045's threshold {least} px {'names it' if named else 'leaves it'},"
        f" its measure of islands {'takes one' if taken else 'takes none'}"
    )


def dots(args: argparse.Namespace) -> int:
    found = modules()
    browser = found.look.viewing_browser
    tool = found.look.viewing_tool
    face = args.face or found.look.FONT
    scales = tuple(args.scale) or tuple(found.look.SCALES)
    ems = found.reads.ems_of(args)
    dots_ = found.reads.DOTS
    every: list[Hidden] = []
    planted: list[str] = []
    try:
        program = browser.find(args.browser)
        for scale in scales:
            pages = laid(dots_, ems, scale)
            first = drawn(found, face, pages, scale, program, {}, args.mode, every=True)
            boxes = boxes_over(found, pages, first)
            second = drawn(found, face, pages, scale, program, boxes, args.mode, every=False)
            planted += planted_lines(tool, browser, scale, second.capture)
            plants = [plant for page in pages for plant in page.plants]
            for reading in second.capture.of(FILE):
                named = second.named.get(reading.palette, frozenset())
                for em in ems:
                    read = [
                        hidden_of(found, plant, scale, reading, named)
                        for plant in plants
                        if plant.em == em
                    ]
                    every += read
                    print(line_of(em, scale, read), flush=True)
    except browser.Stopped as stop:
        print(f"the browser stopped: {stop}", file=sys.stderr)
        return 1
    for palette in palettes_of(every):
        print()
        print(f"in the {palette} palette")
        print("\n".join(summary(dots_, [each for each in every if each.palette == palette])))
    print()
    print("the planted file, read by each start")
    print("\n".join(planted))
    return 0


# Grazes: a box's edge across the foot of a line's descenders.

#: The words a box's edge grazes, by the name `--words` takes: those of DEC-045's graze plant,
#: and the edge control's (DEC-037 point 5).
GRAZED = {"descenders": "Typography gypsy", "edge-control": "jogging"}

#: How many steps a device pixel holds, and the steps of the graze box's top edge, each an
#: eighth of a device pixel, above the foot of the words' counted ink: from half a device pixel
#: below it to two and a half above it.
EIGHTHS = 8
GRAZE_STEPS = range(-4, 21)


@dataclass(frozen=True)
class Words:
    """The words a graze plant sets, as the SVG probe's `Dot` gives a dot: its name, its runs,
    and the run the box grazes."""

    name: str
    runs: tuple[str, ...]
    at: int = 0


def graze_box(spot: Spot, step: int, size: float, faint: int) -> dict[str, float]:
    """A box over `spot`'s line, a device pixel past its ink on each side, whose top edge lies
    `step` eighths of a device pixel above the foot of its counted ink, the ink no lighter than
    `faint`, and which runs an em of `size` px below that foot, in px of its page."""
    ink = spot.ink
    counted = [pixel for pixel, dark in ink.items() if dark <= faint]
    across = spot.page_box(list(ink), 1)
    foot = spot.row_on_page(max(row for row, _ in counted) + 1)
    top = foot - step / EIGHTHS / spot.scale
    return {"x": across["x"], "y": top, "width": across["width"], "height": foot + size - top}


def graze_boxes(pages: Sequence[Laid], first: Drawn, faint: int) -> dict[str, dict[str, float]]:
    """For each plant whose words the first draw found, in any palette, the box of its step
    over them (`graze_box`): as wide as the widest palette's, its edge set from the lowest foot
    of any palette's, so that each palette meets every step from below its own foot."""
    boxes: dict[str, dict[str, float]] = {}
    readings = first.capture.of(FILE)
    for page in pages:
        for plant in page.plants:
            held = []
            for reading in readings:
                spot = reading.spot(plant.text)
                if spot is not None and spot.pixels:
                    held.append(graze_box(spot, plant.step, plant.size, faint))
            if held:
                across = _union(held)
                top = max(box["y"] for box in held)
                bottom = across["y"] + across["height"]
                boxes[plant.text] = {**across, "y": top, "height": bottom - top}
    return boxes


@dataclass(frozen=True)
class Grazed:
    """A step of a graze box's edge, as the read as built found it in one palette: the em the
    read takes, in device pixels, the scale and the step; the span's strong pixels and those
    the box hid, as the tally counts them; the pixels of its counted ink the box hid wholly;
    whether the read named the span as covered; whether the measure takes an island of its
    ink, and at which of its levels first; and whether the probe counts the span as the tally
    does. A span the second draw did not tally holds no strong ink."""

    em: float
    scale: float
    step: int
    palette: str
    strong: int = 0
    lost: int = 0
    counted: int = 0
    named: bool = False
    island: bool = False
    level: int = 0
    agrees: bool = True

    @property
    def sliver(self) -> float:
        """The sliver's area at the em, in device pixels."""
        return 0.01 * self.em**2

    @property
    def alone(self) -> bool:
        """Whether the measure takes an island the read leaves unnamed."""
        return self.island and not self.named


def island_level(
    tool: ModuleType,
    ink: Mapping[Pixel, int],
    hidden: Sequence[Pixel],
    shows: Mapping[Pixel, int],
) -> int:
    """The first of the measure's levels at which a cause that hides `hidden` wholly takes an
    island of `ink`, `shows` of each pixel still showing, or 0 at none: the measure asked at
    each level alone, in its order."""
    names = vars(tool)
    levels = names["LEVELS"]
    try:
        for level in levels:
            names["LEVELS"] = (level,)
            if tool._takes_an_island(ink, hidden, shows):
                return level
    finally:
        names["LEVELS"] = levels
    return 0


def grazed_of(
    found: Modules, plant: Plant, scale: float, reading: Reading, named: Collection[Any]
) -> Grazed:
    """What `reading`, the second draw in one palette, found of `plant`'s words under the box
    of its step, where the read named `named` in that palette."""
    spot = reading.spot(plant.text)
    if spot is None:
        return Grazed(plant.em, scale, plant.step, reading.palette)
    tool = found.look.viewing_tool
    covered = found.look.viewing_browser.COVERED
    ink = spot.ink
    hidden = spot.hidden
    level = island_level(tool, ink, hidden, spot.shows)
    return Grazed(
        spot.em * scale,
        scale,
        plant.step,
        reading.palette,
        spot.counted["strong"],
        spot.counted["hidden"],
        sum(ink[pixel] <= tool.FAINT for pixel in hidden),
        (plant.text, plant.dot.runs[0], covered) in named,
        bool(level),
        level,
        spot.agrees(),
    )


def graze_line(em: float, scale: float, read: Sequence[Grazed]) -> str:
    """One em, scale and palette of a graze, as `grazes` prints it: at each step the strong
    pixels the box hid, after `*` where the read names it, and `!` where the measure takes an
    island the read leaves unnamed."""
    said = " ".join(
        f"{each.lost}{'*' if each.named else ''}{'!' if each.alone else ''}" for each in read
    )
    read_em = next((each.em for each in read if each.strong), em)
    palette = next((each.palette for each in read), "")
    return (
        f"em {em:5.1f}  scale {scale:<6g}  {palette:<12}  read em {read_em:7.3f}"
        f"  sliver {0.01 * read_em**2:6.2f} px  steps {read[0].step}..{read[-1].step}: {said}"
    )


#: How many of the steps the measure alone names a summary lists, each with its em, scale and
#: step.
LISTED = 40


def graze_summary(every: Sequence[Grazed]) -> list[str]:
    """For one palette's steps: how many hide nothing wholly, counted ink alone and strong ink;
    those the read names; those at which the measure takes an island, and of those each the
    read leaves unnamed; and for each draw's least graze, the first step that hides a strong
    pixel wholly, whether the read and the measure name it. A draw is an em, to a tenth, and a
    scale: the em the read takes lies a hair off the em set on some pages."""
    found = [each for each in every if each.strong]
    draws: dict[tuple[float, float], list[Grazed]] = {}
    for each in found:
        draws.setdefault((round(each.em, 1), each.scale), []).append(each)
    nothing = [each for each in found if not each.counted]
    faint = [each for each in found if each.counted and not each.lost]
    strong = [each for each in found if each.lost]
    named = [each for each in found if each.named]
    island = [each for each in found if each.island]
    alone = [each for each in found if each.alone]
    lines = [
        f"{len(found)} steps at {len(draws)} draws{_ems(found)}: hiding nothing wholly at"
        f" {len(nothing)}, counted ink alone at {len(faint)}, strong ink at {len(strong)}",
        f"  named by the read at {len(named)}{_ems(named)}",
        f"  the measure takes an island at {len(island)}{_ems(island)}; the read leaves"
        f" unnamed {len(alone)} of those{_ems(alone)}",
    ]
    for each in alone[:LISTED]:
        lines.append(
            f"    em {each.em:.3f}, scale {each.scale:g}, step {each.step}: hid {each.lost} of"
            f" {each.strong} strong against a sliver of {each.sliver:.2f} px, {each.counted}"
            f" counted wholly, an island at {each.level}"
        )
    if len(alone) > LISTED:
        lines.append(f"    and {len(alone) - LISTED} more")
    if alone:
        by_scale = {
            scale: sum(each.scale == scale for each in alone)
            for scale in sorted({each.scale for each in found})
        }
        lines.append(
            "    by scale: " + ", ".join(f"{scale:g} {count}" for scale, count in by_scale.items())
        )
    least = [
        next(each for each in steps if each.lost)
        for steps in draws.values()
        if any(each.lost for each in steps)
    ]
    lines.append(
        f"  the least graze, at {len(least)} of {len(draws)} draws: named by the read at"
        f" {sum(each.named for each in least)}, an island taken at"
        f" {sum(each.island for each in least)}, by the measure alone at"
        f" {sum(each.alone for each in least)}"
    )
    otherwise = [each for each in found if not each.agrees]
    lines.append(f"  spans the probe counted otherwise than the read: {len(otherwise)}")
    return lines


def grazes(args: argparse.Namespace) -> int:
    found = modules()
    browser = found.look.viewing_browser
    tool = found.look.viewing_tool
    face = args.face or found.look.FONT
    scales = tuple(args.scale) or tuple(found.look.SCALES)
    ems = found.reads.ems_of(args)
    words = (Words(args.words, (GRAZED[args.words],)),)
    every: list[Grazed] = []
    planted: list[str] = []
    try:
        program = browser.find(args.browser)
        for scale in scales:
            pages = laid(words, ems, scale, GRAZE_STEPS)
            first = drawn(found, face, pages, scale, program, {}, args.mode, every=True)
            boxes = graze_boxes(pages, first, tool.FAINT)
            second = drawn(found, face, pages, scale, program, boxes, args.mode, every=False)
            planted += planted_lines(tool, browser, scale, second.capture)
            plants = [plant for page in pages for plant in page.plants]
            for reading in second.capture.of(FILE):
                named = second.named.get(reading.palette, frozenset())
                for em in ems:
                    read = [
                        grazed_of(found, plant, scale, reading, named)
                        for plant in plants
                        if plant.em == em
                    ]
                    every += read
                    print(graze_line(em, scale, read), flush=True)
    except browser.Stopped as stop:
        print(f"the browser stopped: {stop}", file=sys.stderr)
        return 1
    for palette in palettes_of(every):
        print()
        print(f"in the {palette} palette, {GRAZED[args.words]!r}")
        print("\n".join(graze_summary([each for each in every if each.palette == palette])))
    print()
    print("the planted file, read by each start")
    print("\n".join(planted))
    return 0


# The planted file, light, dark and in each forced palette.


def planted_dark(browser: ModuleType, scale: float) -> str:
    """The planted file as a start at `scale` writes it, its plants set in device pixels, in a
    dark key: its root names the dark scheme alone, as the renderer's file of a dark key does."""
    written = browser._planted_html(browser.PLANTED_FACE.read_bytes(), device=scale)
    return written.replace("<style>", "<style>:root{color-scheme:dark}", 1)


def planted(args: argparse.Namespace) -> int:
    found = modules()
    browser = found.look.viewing_browser
    tool = found.look.viewing_tool
    scales = tuple(args.scale) or tuple(found.look.SCALES)
    try:
        program = browser.find(args.browser)
        for scale in scales:
            with tempfile.TemporaryDirectory(prefix="visual-html-reads-") as folder:
                file = Path(folder) / PLANTED_DARK
                file.write_text(planted_dark(browser, scale), encoding="utf-8")
                local = Path(folder) / "local"
                pages = browser.PLANTED_PAGES
                with captured(browser, every=False) as capture:
                    browser.draw(file, pages, scale, program, local)
                    browser.draw_forced(file, pages, scale, program, local)
            print("\n".join(planted_lines(tool, browser, scale, capture)), flush=True)
    except browser.Stopped as stop:
        print(f"the browser stopped: {stop}", file=sys.stderr)
        return 1
    return 0


# One look of a deck, the reads as built, and what the measure would add.


@dataclass(frozen=True)
class Entry:
    """A cause of a span's loss, as the sliver or the measure names it: the span's characters
    and its em in device pixels, the cause, the share of its strong ink lost, whether the
    loss reaches the sliver, and whether the cause takes an island of its ink."""

    text: str
    em: float
    why: str
    share: float
    sliver: bool
    island: bool


def entries_of(tool: ModuleType, browser: ModuleType, spot: Spot, text: str) -> list[Entry]:
    """Each cause, cut then covered, that loses at least the sliver of `spot`'s strong ink, as
    the read as built names it, or takes an island of its ink, as the measure would."""
    em = spot.em * spot.scale
    least = browser.SLIVER * em**2
    strong = spot.counted["strong"]
    ink = spot.ink
    found = []
    causes = (
        (browser.CUT, spot.counted.get("past", 0), spot.beyond, None),
        (browser.COVERED, spot.counted["hidden"], spot.hidden, spot.shows),
    )
    for why, lost, pixels, shows in causes:
        by_sliver = bool(strong) and lost >= least
        island = tool._takes_an_island(ink, pixels, shows)
        if by_sliver or island:
            found.append(Entry(text, em, why, lost / strong if strong else 1.0, by_sliver, island))
    return found


def entry_line(entry: Entry) -> str:
    """An entry of the deck, as `deck` prints it."""
    by = (
        "the sliver and the measure"
        if entry.sliver and entry.island
        else ("the sliver alone" if entry.sliver else "the measure alone")
    )
    return f"    {entry.text!r} at an em of {entry.em:.2f}, {entry.why} {entry.share:.0%}, by {by}"


def deck(args: argparse.Namespace) -> int:
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    look = importlib.import_module("look")
    browser = importlib.import_module("_lib.viewing_browser")
    tool = importlib.import_module("_lib.viewing_tool")
    viewing = importlib.import_module("_lib.viewing")
    languages = [part for language in args.language for part in ("--language", language)]
    asked = ["look.py", args.piece, "--renderer", "html", "--every-key", viewing.ASK_FORCED]
    held = sys.argv
    sys.argv = [*asked, *languages]
    try:
        with captured(browser, every=False) as capture:
            code = look.main()
    finally:
        sys.argv = held
    if code != 0:
        print(f"the look did not draw: exit {code}", file=sys.stderr)
        return 1
    planted_files = (browser.PLANTED_FILE, browser.PLANTED_FORCED_FILE)
    for file in capture.files():
        if file in planted_files:
            continue
        for reading in capture.of(file):
            entries = [
                entry
                for spot in reading.spots.values()
                for entry in entries_of(tool, browser, spot, reading.placed[spot.index].characters)
            ]
            by_sliver = [entry for entry in entries if entry.sliver]
            alone = [entry for entry in entries if not entry.sliver]
            otherwise = sum(not spot.agrees() for spot in reading.spots.values())
            print(
                f"{file}, {reading.palette}: {len(reading.spots)} spans tallied, of"
                f" {len(reading.placed)}; entries by the sliver {len(by_sliver)}, with the measure"
                f" {len(entries)}, by the measure alone {len(alone)}; spans the probe counted"
                f" otherwise than the read: {otherwise}"
            )
            print("\n".join(entry_line(entry) for entry in entries))
    scale = next(
        (spot.scale for each in capture.of(browser.PLANTED_FILE) for spot in each.spots.values()),
        0.0,
    )
    print()
    print("the planted file, read by each start")
    print("\n".join(planted_lines(tool, browser, scale, capture)))
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="visual_html_reads.py",
        description="Measure the HTML renderer's read of cover and cut through a browser "
        "(DEC-037), beside DEC-045's measure of islands.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    probes = (
        ("dots", "what the read names of a dot a box hides whole", dots, 40.0),
        ("grazes", "what the read names of a box's edge across a line's foot", grazes, 20.0),
    )
    for name, said, run, end in probes:
        probe = commands.add_parser(name, help=said)
        probe.add_argument("--mode", choices=MODES, default=LIGHT)
        probe.add_argument("--from", dest="start", type=float, default=10.0)
        probe.add_argument("--to", dest="end", type=float, default=end)
        probe.add_argument("--step", type=float, default=0.1)
        probe.add_argument("--em", type=float, action="append", default=[])
        probe.add_argument("--scale", type=float, action="append", default=[])
        probe.add_argument("--face", type=Path, help="the face the plants are set in")
        probe.add_argument("--browser", type=Path, help="the browser to draw with")
        if name == "grazes":
            probe.add_argument("--words", choices=sorted(GRAZED), default="descenders")
        probe.set_defaults(run=run)
    held = commands.add_parser("planted", help="the planted file in each key and forced palette")
    held.add_argument("--scale", type=float, action="append", default=[])
    held.add_argument("--browser", type=Path, help="the browser to draw with")
    held.set_defaults(run=planted)
    looked = commands.add_parser("deck", help="one look of a piece, with what the measure adds")
    looked.add_argument("piece", nargs="?", default="showcase")
    looked.add_argument("--language", action="append", default=[])
    looked.set_defaults(run=deck)
    args = parser.parse_args(argv)
    return args.run(args)


if __name__ == "__main__":
    sys.exit(main())
