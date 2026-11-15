"""Measure the HTML renderer's read of cover through a browser, as visual-communication DEC-037
gives it: which dots a later box hides whole the read names, and which it leaves unnamed
(project-kit#3262). A maintainer reruns it when the browser, the face or the read changes, and
compares what it prints with the figures a record gives.

    uv run python scripts/visual_html_reads.py dots [--from EM] [--to EM] [--step EM]
        [--em EM]... [--scale SCALE]... [--face FILE] [--browser PROGRAM]

It draws at each em from `--from` to `--to` (10 to 40 by default) in steps of `--step` (0.1),
or at each `--em` alone where any is given, in device pixels, and at each device scale (the
five of `tests/test_visual_communication_look.py` by default): the ems and scales
`scripts/visual_svg_reads.py` draws at. It sets the five dots that probe hides whole
(`DOTS` there): a full stop after "end" and a decimal point in "3.5", each a run of its own,
the dot of ż, and the same full stop and point inside their run, "end." and "3.5". It sets
them in Source Sans Pro Regular, or in the face `--face` names; the faces of the test brand
(`tests/fixtures/visual-communication/libraries/test-brand/1.0.0/fonts`) are the deck's. Each
dot at each em is a text of a page the HTML renderer writes, as the renderer's tests write one
(`tests/test_visual_communication_html.py`), and the browser `viewing_browser.find` finds, or
`--browser`, draws them through the viewing step's own module, in a start of each scale under
a light key and without forced colours.

- **Two draws at each scale.** The first reads every span of the probe's pages, as no
  pre-filter passes over one there, and finds each dot's ink in the read's own draw alone,
  as `scripts/visual_svg_reads.py` finds it (`dot_pixels` there). The second lays a box drawn
  after each dot over all of its ink, a device pixel past it on each side, and is the read as
  built. Both start with the step's first read of its planted file.
- **What it reads.** Each tally the read makes is read again, from its own four images, for
  each pixel of each span's ink (`INKED`): how dark the span's letters alone make it, and how
  much of that the page drawn whole still shows. So the probe counts what the read counts,
  and says where it counts otherwise.
- **A line for each em and scale.** The em the read takes, in device pixels, the sliver's
  area there, and for each dot its pixels of strong ink and of any ink, the strong pixels the
  box hid of its span, whether the box hid every pixel of the dot and how many of the span's
  other pixels it hid, and whether the read named the span as covered.
- **Then, for each dot,** the draws at which the box hid it whole, those at which it holds
  no strong ink, those the read named and those it left unnamed, by em, and its strong ink
  as a share of the em squared. For those left unnamed, what visual-communication DEC-045's
  two tests would name of them were they the browser's: its threshold, in whole pixels, and
  its measure of islands (`viewing_tool._least`, `viewing_tool._takes_an_island`).
- **Last, for each start,** the planted file's edge control and háček plant (DEC-037 point 5)
  under the same two tests, beside what the read names of them.

It writes nothing in the repository: the pages and the browser's profile lie in a throwaway
folder. Exit codes: 0 when it measured, 1 when the browser stopped, 2 on a usage error.
"""

from __future__ import annotations

import argparse
import contextlib
import importlib
import math
import sys
import tempfile
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parent.parent

Pixel = tuple[int, int]

#: The em, in device pixels, from which a draw counts as large in the summary, as
#: `scripts/visual_svg_reads.py` splits its own.
LARGE = 25.0

#: The name of the file the probe's pages are written to, and the prefix of its pages' ids.
FILE = "dots.html"
PAGE = "dots"

#: Each dot's cell on its page, in ems of its font: wide and high enough that the boxes of two
#: dots' spans, each widened by its em, never meet, and that each stays on its page, so the
#: read's room past the page's edges is none. The text's top and its baseline, in the same
#: ems, from the cell's top.
CELL_WIDTH = 6.0
CELL_HEIGHT = 4.5
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

#: The fill of the box over a dot, and the key the pages are drawn in.
BOX_FILL = "surface"
KEY = "default"

#: For each span a tally reads, each pixel of its box widened by its em where its letters
#: alone leave ink, from the tally's own four images, as the tally reads them
#: (`viewing_browser.TALLY`): its row and column in the images, how far its letters alone
#: change it, and how far they change it in the page drawn whole, each the most of the three
#: channels; with the two colours' difference.
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
  return {apart, spans: spans.map(({index, box}) => {
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
  })};
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


@dataclass(frozen=True)
class Spot:
    """A span as a tally read it: its place among the document's spans, its font size in px,
    its page's box and the tally's clip in px of the document, the device pixels to a px the
    browser drew at, the two colours' difference, each pixel of its ink with how far its
    letters alone change it and how far the page drawn whole does, and what the tally itself
    counted: its strong ink, and of that what lies past its page and what its page hides."""

    index: int
    em: float
    page: Mapping[str, float]
    clip: Mapping[str, float]
    scale: float
    apart: float
    pixels: Mapping[Pixel, tuple[int, int]]
    counted: Mapping[str, int]

    def is_strong(self, pixel: Pixel) -> bool:
        """Whether its letters alone change `pixel` by more than half the two colours'
        difference, as the tally counts strong ink."""
        return 2 * self.pixels[pixel][0] > self.apart

    @property
    def ink(self) -> dict[Pixel, int]:
        """Each pixel's darkness, drawn black on white: 0 where its letters alone change it by
        the whole difference between the two colours, 255 where by none."""
        return {
            pixel: 255 - round(255 * alone / self.apart)
            for pixel, (alone, _) in self.pixels.items()
        }

    @property
    def shows(self) -> dict[Pixel, int]:
        """How much of each pixel's ink the page drawn whole still shows, from 0 to 255."""
        return {pixel: round(255 * whole / self.apart) for pixel, (_, whole) in self.pixels.items()}

    @property
    def hidden(self) -> list[Pixel]:
        """The pixels of its ink the page drawn whole does not change at all."""
        return [pixel for pixel, (_, whole) in self.pixels.items() if not whole]

    def agrees(self) -> bool:
        """Whether the probe counts its strong ink, and of that what its page hides, as the
        tally does. The probe's pages lie wholly on their pages, so none of it lies past."""
        strong = [pixel for pixel in self.pixels if self.is_strong(pixel)]
        hidden = sum(not self.pixels[pixel][1] for pixel in strong)
        return (len(strong), hidden) == (self.counted["strong"], self.counted["hidden"])

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
class Capture:
    """What the reads asked of the browser of each file, by its name: each span of the last
    document it read, by its place among the document's spans, and each span a tally read."""

    placed: dict[str, dict[int, Placed]] = field(default_factory=dict)
    spots: dict[str, dict[int, Spot]] = field(default_factory=dict)

    def read(self, file: str, pages: Sequence[Mapping[str, Any]]) -> None:
        self.placed[file] = {
            span["index"]: Placed(page["id"], text["id"], number, at, span["text"], span["em"])
            for page in pages
            for text in page["texts"]
            for number, line in enumerate(text["lines"])
            for at, span in enumerate(line)
        }

    def tallied(
        self,
        file: str,
        clip: Mapping[str, float],
        scale: float,
        asked: Sequence[Mapping[str, Any]],
        counted: Sequence[Mapping[str, int]],
        inked: Mapping[str, Any],
    ) -> None:
        held = self.spots.setdefault(file, {})
        placed = self.placed.get(file, {})
        by_index = {each["index"]: each for each in inked["spans"]}
        for each, count in zip(asked, counted, strict=True):
            index = each["index"]
            pixels = {
                (row, column): (alone, whole)
                for row, column, alone, whole in by_index[index]["pixels"]
            }
            em = placed[index].em if index in placed else 0.0
            held[index] = Spot(
                index,
                em,
                dict(each["page"]),
                dict(clip),
                scale,
                inked["apart"],
                pixels,
                dict(count),
            )

    def spot(self, file: str, text: str, line: int = 0, at: int = 0) -> Spot | None:
        """The span a tally read of the text `text` of `file`, at `at` in its line `line`."""
        for index, placed in self.placed.get(file, {}).items():
            if (placed.text, placed.line, placed.at) == (text, line, at):
                return self.spots.get(file, {}).get(index)
        return None


@contextlib.contextmanager
def captured(browser: ModuleType, every: bool) -> Iterator[Capture]:
    """While it lasts, each document the browser module's reads read, and each tally they make,
    is kept in the capture it gives, by the name of the file open. Where `every`, the pre-filter
    passes over no span of the probe's pages, so each is tallied."""
    started = browser._Started
    names = vars(browser)
    ask, passed_over = started.ask, names["_passed_over"]
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

    def over(page: Mapping[str, Any], span: Mapping[str, Any], spans: Any) -> bool:
        if every and str(page["id"]).startswith(PAGE):
            return False
        return passed_over(page, span, spans)

    started.ask = asked
    names["_passed_over"] = over
    try:
        yield capture
    finally:
        started.ask = ask
        names["_passed_over"] = passed_over


@dataclass(frozen=True)
class Plant:
    """A dot set at an em: its page's trace id and its text's, the dot as the SVG probe gives
    it, the em in device pixels, its font size in px, and its cell's left and top on its page."""

    page: str
    text: str
    dot: Any
    em: float
    size: float
    left: float
    top: float


@dataclass(frozen=True)
class Laid:
    """A page of plants: its trace id, its size in px, and its plants."""

    id: str
    width: float
    height: float
    plants: tuple[Plant, ...]


def laid(dots: Sequence[Any], ems: Sequence[float], scale: float) -> list[Laid]:
    """Each dot at each of `ems`, drawn at `scale`, in cells laid left to right in rows no wider
    than `ROW_PIXELS`, and rows down pages no higher than `PAGE_PIXELS`, at least one cell to a
    row and one row to a page. A page is as wide as its widest row."""
    cells = [(em, dot) for em in ems for dot in dots]
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

    for em, dot in cells:
        size = em / scale
        wide, tall = CELL_WIDTH * size, CELL_HEIGHT * size
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
        rows[-1].append(Plant(page, text, dot, em, size, across, height))
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
    spans = [(at, words, 0.6 * size * len(words)) for at, words in enumerate(plant.dot.runs)]
    return html_tests.element(
        "text",
        plant.text,
        x=plant.left + TEXT_LEFT * size,
        y=plant.top + TEXT_TOP * size,
        width=(CELL_WIDTH - TEXT_LEFT) * size,
        height=CELL_HEIGHT * size / 2,
        text="".join(plant.dot.runs),
        paragraphs=[runs],
        lines=[html_tests.line(0, BASELINE * size, *spans)],
        **{"line-height": CELL_HEIGHT * size / 2, "measured-height": CELL_HEIGHT * size / 2},
    )


@dataclass(frozen=True)
class Drawn:
    """One draw of the probe's pages at a scale: what the reads asked of the browser, and what
    they named of each file."""

    capture: Capture
    named: frozenset[tuple[str, str, str]]


def drawn(
    found: Modules,
    face: Path,
    pages: Sequence[Laid],
    scale: float,
    program: Path,
    boxes: Mapping[str, Any],
    *,
    every: bool,
) -> Drawn:
    """`pages` written by the HTML renderer in `face`, with `boxes`, and drawn at `scale` by
    `program` through the viewing step's browser module. Raises its Stopped."""
    browser = found.look.viewing_browser
    viewing = found.look.viewing
    html_tests = found.html
    scene = scene_of(html_tests, pages, boxes)
    written = html_tests.html.render(
        scene,
        form="html",
        keys={KEY: html_tests.LIGHT},
        colours={KEY: html_tests.COLOURS},
        font_file=lambda _family: face,
        pictures={KEY: {}},
    )
    wanted = [viewing.browser_page(page) for page in viewing.pages_of(scene)]
    with tempfile.TemporaryDirectory(prefix="visual-html-reads-") as folder:
        file = Path(folder) / FILE
        file.write_bytes(written.document)
        with captured(browser, every) as capture:
            drawing = browser.draw(file, wanted, scale, program, Path(folder) / "local")
    named = frozenset((each.element, each.text, each.why) for each in drawing.shown[0].read.dropped)
    return Drawn(capture, named)


def boxes_over(found: Modules, pages: Sequence[Laid], first: Drawn) -> dict[str, Any]:
    """For each plant whose dot the first draw found in its run's ink, a box over all of the
    dot, a device pixel past it on each side, in px of its page."""
    boxes: dict[str, Any] = {}
    for page in pages:
        for plant in page.plants:
            spot = first.capture.spot(FILE, plant.text, 0, plant.dot.at)
            if spot is None:
                continue
            mine, _, _ = found.reads.dot_pixels(plant.dot, spot.ink)
            if mine:
                boxes[plant.text] = spot.page_box(mine, 1)
    return boxes


@dataclass(frozen=True)
class Hidden:
    """A dot under a box laid over all of it, as the read as built found it: the em the read
    takes, in device pixels, and the scale; the dot's pixels of any ink and of strong ink;
    whether the box hid every pixel of it, and how many of its span's other pixels it hid; the
    strong pixels of its span the box hid and the span's strong pixels, as the tally counts
    them; whether the read named the span as covered; the weakest level at which its run's ink
    falls into the dot's parts; whether DEC-045's threshold and its measure of islands would
    name it; whether the probe counts the span as the tally does; and the strong pixels the box
    hid of the plant's other spans. A dot the first draw did not find holds no ink."""

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

    @property
    def sliver(self) -> float:
        """The sliver's area at the em, in device pixels: the least the read names."""
        return 0.01 * self.em**2


def hidden_of(found: Modules, plant: Plant, scale: float, second: Drawn) -> Hidden:
    """What the second draw found of `plant`'s dot under its box."""
    nothing = Hidden(plant.dot, plant.em, scale)
    spot = second.capture.spot(FILE, plant.text, 0, plant.dot.at)
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
        for other in [second.capture.spot(FILE, plant.text, 0, at)]
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
        (plant.text, plant.dot.runs[plant.dot.at], covered) in second.named,
        apart,
        strong_hidden >= tool._least(em),
        tool._takes_an_island(ink, list(hidden), spot.shows),
        spot.agrees(),
        sum(other.counted["hidden"] for other in others),
    )


def line_of(em: float, scale: float, read: Sequence[Hidden]) -> str:
    """One em and scale, as `dots` prints it."""
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
    return (
        f"em {em:5.1f}  scale {scale:<6g}  read em {read_em:7.3f}"
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


def _ems(found: Sequence[Hidden]) -> str:
    if not found:
        return ""
    ems = sorted(each.em for each in found)
    return f" (ems {ems[0]:.1f} to {ems[-1]:.1f})"


def _strong(found: Sequence[Hidden]) -> str:
    if not found:
        return ""
    strong = sorted(each.strong for each in found)
    return f", the dot's strong pixels {strong[0]} to {strong[-1]}"


#: The planted file's plants the summary of each start reads (DEC-037 point 5): the edge
#: control, which the read leaves unnamed, and the háček plant, which it names.
PLANTED = ("edge-control", "hacek-under-a-box")


def planted_lines(found: Modules, scale: float, start: Drawn) -> list[str]:
    """The planted file's edge control and háček plant at `scale`, as the first read of the
    start `start` found them: the em the read takes, the strong pixels the box hid and the
    sliver there, and whether DEC-045's threshold and its measure of islands would name them."""
    browser = found.look.viewing_browser
    tool = found.look.viewing_tool
    lines = []
    for text in PLANTED:
        spot = start.capture.spot(browser.PLANTED_FILE, text)
        if spot is None:
            lines.append(f"  {text} at scale {scale:g}: not tallied")
            continue
        em = spot.em * scale
        hidden = spot.hidden
        least = tool._least(em)
        named = sum(spot.is_strong(pixel) for pixel in hidden) >= least
        taken = tool._takes_an_island(spot.ink, hidden, spot.shows)
        lines.append(
            f"  {text} at scale {scale:g}: read em {em:.3f}, hid {spot.counted['hidden']} of"
            f" {spot.counted['strong']} strong, sliver {0.01 * em**2:.2f} px;"
            f" DEC-045's threshold {least} px {'names it' if named else 'leaves it'},"
            f" its measure of islands {'takes one' if taken else 'takes none'}"
        )
    return lines


def dots(args: argparse.Namespace) -> int:
    found = modules()
    browser = found.look.viewing_browser
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
            first = drawn(found, face, pages, scale, program, {}, every=True)
            boxes = boxes_over(found, pages, first)
            second = drawn(found, face, pages, scale, program, boxes, every=False)
            planted += planted_lines(found, scale, second)
            plants = [plant for page in pages for plant in page.plants]
            for em in ems:
                read = [
                    hidden_of(found, plant, scale, second) for plant in plants if plant.em == em
                ]
                every += read
                print(line_of(em, scale, read), flush=True)
    except browser.Stopped as stop:
        print(f"the browser stopped: {stop}", file=sys.stderr)
        return 1
    print()
    print("\n".join(summary(dots_, every)))
    print()
    print("the planted file, read by each start")
    print("\n".join(planted))
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="visual_html_reads.py",
        description="Measure the HTML renderer's read of cover through a browser (DEC-037).",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    probe = commands.add_parser("dots", help="what the read names of a dot a box hides whole")
    probe.add_argument("--from", dest="start", type=float, default=10.0)
    probe.add_argument("--to", dest="end", type=float, default=40.0)
    probe.add_argument("--step", type=float, default=0.1)
    probe.add_argument("--em", type=float, action="append", default=[])
    probe.add_argument("--scale", type=float, action="append", default=[])
    probe.add_argument("--face", type=Path, help="the face the plants are set in")
    probe.add_argument("--browser", type=Path, help="the browser to draw with")
    probe.set_defaults(run=dots)
    args = parser.parse_args(argv)
    return args.run(args)


if __name__ == "__main__":
    sys.exit(main())
