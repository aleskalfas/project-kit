"""The viewing step's browser: a page file as images, and what the browser dropped
(visual-communication DEC-020 points 6 to 9, DEC-023 point 6, DEC-031 point 5, DEC-015 point 2,
DEC-024 points 1 and 4, DEC-027 points 2 to 4, DEC-037, DEC-039 point 5).

This module alone calls the browser. It reads the HTML renderer's page files. It stands on the
standard library and on the marks the renderer's declaration holds, so every other format
pays nothing for it. What it asks of a page it asks in JavaScript, which the browser runs.

- **Which browser.** `find` takes the program it is given, or else the first it finds where
  Chrome and Chromium install themselves, and starts nothing. It installs and pins none.
- **One start serves one file.** `draw` starts the browser over a pipe, with no port and no
  driver: messages of JSON, each ended by a NUL, on file descriptors 3 and 4. The pages share
  the one device scale the caller gives, set by the browser's own flag, since an emulated
  scale leaves HTML text on whole pixels. The window holds each page at its own size: it is
  as wide as the widest page, with the renderer's declared gutter on each side, so no page
  shrinks where the file shows fixed pages on a backdrop (DEC-031 point 5). It widens so for
  every file, and needs no knowledge of which pages are fixed.
- **One page an image.** Each image is cut to its page, or to a band of it, so the keyline
  and the backdrop around a fixed page lie outside every image.
- **Regions.** A page the caller hands with regions of its height, its bands, is drawn as an
  image of each, as wide as the page, in order (DEC-022 point 7). The reads read the whole
  page, once.
- **Each mode in that one start.** The caller names the reader's signals the file reads, each
  with the values it may take, and the signals of each mode to draw, each a set of CSS media
  features such as `prefers-color-scheme: dark`. The module knows no axis. It opens the file
  once, and for each mode sets every signal by the browser's emulation, so the machine's own
  settings play no part, and draws its images and runs the four reads, with no reload.
- **The four reads.** `Read` holds them. *The words:* each text's spans are matched to the
  document, element by element, in order and in number, since an HTML parser refuses
  nothing. *Ink:* each span is drawn alone, the other spans and the layers hidden from
  outside the file, on a white ground and then a black one. A span that changes nothing
  left no ink, whatever the cause. A span of spaces alone is not read for ink, as
  `viewing_tool` does not read one. *The font:* a span has a loaded face in the file where a
  family it names has one at its weight, since the engine may have measured it in any of
  them. A span drawn, even in part, in a font of the machine is named with that font.
  *Requests:* each but the page file's own and a `data:` address is refused, and named.
- **What the page shows of a span** (DEC-037). The ink read gives each page room past each
  of its edges, enough for every span's box widened by its em, and keeps each page's size. A
  span is *off the page* where its box lies wholly past its page, and is named so alone. Its
  *strong ink* is measured where its letters alone are drawn, in `CanvasText` on `Canvas`,
  with no other text and no text's ground: a pixel is strong where the two draws differ by
  more than half those two colours do. What the page shows of it is what changes in the page
  drawn whole when its letters alone change between those two colours. Strong ink past the
  page's edge is *cut*, and strong ink on the page that the page drawn whole does not show is
  *covered*. Each is named, with the share of the span's strong ink it loses, where it is at
  least `SLIVER` of the span's em², in device px. The *pre-filter* passes over a span whose
  box, widened by its em, stays inside its page and meets no other text's and no box of a
  part painted after it, by z-index and then by the document's order. Spans whose widened
  boxes do not meet are drawn alone, and their colours changed, at once.
- **What it is not asked.** A text in the colour of what lies under it, or that reads poorly
  through a translucent fill, shows, and stays the reviewer's.
- **The first read.** Each start first reads a file of its own in the renderer's form,
  planted with one fault of each kind the reads name, and with what they must leave unnamed
  (DEC-037 point 5). A read that names anything else stops the start, so a fault there shows
  as a stop, never as a clean report. Its first page carries no z-index; a page of its own
  holds the text a part covers by z-index, so each start meets the pre-filter on both kinds of
  page. The edge control and the háček plant are set in device pixels, from the start's
  device scale and the page's drawn width, so each holds the same share of its em in every
  start. The first page also holds a mode for each signal the file reads, a box of its own,
  and the start stops where setting the signal does not repaint that box, since the keys that
  signal parts would read as one.
- **Under forced colours.** `draw_forced` draws a file in each of the browser's forced
  palettes (`PALETTES`), in a start of its own: the browser's flag forces its colours
  (`FORCING`), and every emulation sets `forced-colors: active` with the palette's signals.
  Under the flag, a page drawn without forced colours is no page a reader gets, so no start
  mixes the two. The emulation alone forces the text in some browsers and leaves it in the
  file's colours in others, Chrome 157 among them, so it never stands in for the flag: only
  the flag forces the colours the same way in every browser the step reached. That start's
  first read keeps the planted file's mode boxes and its spans with no paint out of forcing,
  so its reads name each planted fault in each forced palette. Its planted pages take the
  renderer's forced form, the grounds of its texts and the edge inside a fill among it
  (DEC-039). It stops where a text left to forcing, of two lines with no paint at a step below
  its font's height, its first line with descenders, shows no ink on either line, or has a
  line named at all, since the forced palette did not reach the text, or a ground or a
  backplate covers its lines (DEC-039 point 5). It stops too where a forced palette's ground
  is not lighter than its text in the light one, and darker in the dark.
- **Bounds.** The browser's start has `START_SECONDS`, each call `CALL_SECONDS`, and its close
  `CLOSE_SECONDS`. A browser that hangs counts as one that stopped, at its close too, and is
  ended: its own process group, which only its start made, and no other process.
- **A stop.** `Stopped` says where `find` looked, or the program started and what that said.
  It gives no image: a drawing is all its pages or none. From those words it tells a sandbox
  that stopped the browser apart from a browser run as root, which refuses to start with its
  own sandbox on.
- **Its own sandbox.** No flag here turns off or weakens the sandbox of any of the browser's
  processes, merges them into one, or lets a page read past its own file (`FLAGS`).
- **Its profile** lies in a throwaway folder under the one the caller names, removed even on
  a stop, with the planted file and what the browser said.

The browser's pipe needs a POSIX system, so `PLACES` names none for another.
"""

from __future__ import annotations

import base64
import contextlib
import json
import math
import os
import re
import select
import shutil
import signal
import struct
import subprocess
import sys
import tempfile
import time
from collections.abc import Collection, Iterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, NoReturn

from _lib.plugins import html_declaration

#: The marks of the file, as the renderer that writes them declares them.
MARKS = html_declaration.MARKS

#: The width of backdrop the file may show at each side of a page, in px of the window, as
#: the renderer declares it: the window takes it on each side, for every file.
GUTTER: float = html_declaration.DECLARATION["pages"]["fixed"]["gutter"]["width"]

#: How long the browser has to start, for one call, and to close, in seconds. A start after an
#: update is the slowest. A page's image is the longest call: a tall page takes a second or two.
START_SECONDS = 60.0
CALL_SECONDS = 30.0
CLOSE_SECONDS = 10.0

#: Where Chrome and Chromium install themselves, then the names they go by on the PATH.
PLACES: Mapping[str, tuple[str, ...]] = {
    "darwin": (
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        "~/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "~/Applications/Chromium.app/Contents/MacOS/Chromium",
    ),
    "linux": ("/opt/google/chrome/chrome", "/snap/bin/chromium"),
}
NAMES = ("google-chrome-stable", "google-chrome", "chromium", "chromium-browser")

#: What each start asks of the browser, beside its profile, its window and its scale. None
#: touches its own sandbox (DEC-024 point 1).
FLAGS = (
    "--headless",
    "--remote-debugging-pipe",
    "--hide-scrollbars",
    "--disable-gpu",
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-background-networking",
    "--disable-component-update",
    "--disable-sync",
)

#: The browser's own flag that forces its colours, as a reader's forced palette does, which a
#: start that draws under forced colours adds to `FLAGS` (DEC-027 point 3). It touches no
#: sandbox either.
FORCING = "--force-high-contrast"

#: What every emulation of such a start sets, beside the signals of its forced palette.
FORCED = {"forced-colors": "active"}


@dataclass(frozen=True)
class Palette:
    """A forced palette the browser gives: its name, the reader's signals the browser sets with
    it, and whether its ground is lighter than its text."""

    name: str
    signals: Mapping[str, str]
    light: bool


#: The browser's two forced palettes, in the order a forced start draws them: dark text on a
#: light ground, and the reverse. Each sets the scheme of its darkness, as the emulation pairs
#: them, and more contrast, as the flag reported (DEC-027 point 2). These are facts of the
#: browser, so this module names them, and the step reads from them which key a file shows.
PALETTES = (
    Palette("light", {"prefers-color-scheme": "light", "prefers-contrast": "more"}, True),
    Palette("dark", {"prefers-color-scheme": "dark", "prefers-contrast": "more"}, False),
)

#: How high a window starts. Only its width bears on a page, and an image reaches past it.
WINDOW_HEIGHT = 800

#: The descriptors the browser reads its messages on and writes its answers on.
BROWSER_READS = 3
BROWSER_WRITES = 4

#: The grounds a span is drawn on: one shows what the other cannot.
GROUNDS = ("#ffffff", "#000000")

#: How far a page's measure may lie from the scene's, in px, for a browser's rounding.
MEASURE = 0.5

#: Where a PNG file's header gives the image's width and height.
PNG_SIZE = slice(16, 24)

#: How much of what the browser said a stop keeps, from its end.
SAID_LENGTH = 2000

#: What a browser says where a sandbox stopped it: its own that could not start, or one around
#: it that refused the local socket every start binds.
SANDBOX = re.compile(r"sandbox|SingletonSocket: Operation not permitted", re.IGNORECASE)

#: What Chrome says where it runs as root, and so refuses to start with its own sandbox on, as
#: a container may run it. Its words name its sandbox, so they are read before `SANDBOX`.
AS_ROOT = re.compile(r"Running as root without --no-sandbox is not supported")

#: What reading an answer of another form than the protocol's raises.
UNREADABLE = (AttributeError, KeyError, IndexError, TypeError, ValueError, struct.error)

#: Why a span is named in `dropped`, one cause an entry (DEC-037 point 2): it left no ink, it
#: lies wholly off its page, part of its strong ink lies past its page's edge, or the page drawn
#: whole hides part of its strong ink on the page.
NO_INK = "no ink"
OFF_THE_PAGE = "off the page"
CUT = "cut"
COVERED = "covered"

#: The order of the causes among a span's entries.
CAUSES = (OFF_THE_PAGE, NO_INK, CUT, COVERED)

#: The least a cut or a cover must lose of a span's strong ink to be named, in the span's em²
#: (DEC-037 point 1). Each cause is judged alone.
SLIVER = 0.01

#: The colours a span's letters take where its strength is measured, and between which they
#: change where the page drawn whole is read: CSS's text colour and ground colour, which
#: forcing keeps (DEC-037 point 3).
STRENGTH = ("CanvasText", "Canvas")

#: How often a throwaway folder is tried, and the wait between: a helper of the browser may
#: outlive it by a moment, and write as it goes.
REMOVALS = 5
REMOVAL_WAIT = 0.2

#: What the throwaway folder holds beside the profile.
PROFILE = "profile"
SAID = "said.txt"
PLANTED_FILE = "planted.html"

#: The document's pages, each with its place and its texts, once its faces have settled. Each
#: span holds its place in the document, for the calls that name a span by it, its em, and
#: where the browser paints it: its z-index, its text's, and its place among the document's
#: elements. Each page holds its parts, each shape of a layer and each line's ground with a
#: box, in the same order, each box widened for a stroke and its arrowheads.
READ = """async (marks) => {
  const bare = (name) => name.replace(/^["']|["']$/g, '').replace(/\\\\(.)/g, '$1');
  const named = (list) =>
    (list.match(/"(?:[^"\\\\]|\\\\.)*"|'(?:[^'\\\\]|\\\\.)*'|[^,\\s][^,]*/g) || []).map(bare);
  const key = (family, weight) =>
    `${family.toLowerCase()} ${{normal: '400', bold: '700'}[weight] || weight}`;
  const box = (element) => {
    const {left, top, width, height} = element.getBoundingClientRect();
    return {x: left + scrollX, y: top + scrollY, width, height};
  };
  const within = (element, mark) => [...element.querySelectorAll(`[${mark}]`)];
  const at = new Map([...document.querySelectorAll('*')].map((element, index) => [element, index]));
  const raised = (element) => {
    for (let held = element; held && !held.hasAttribute(marks.page); held = held.parentElement) {
      const z = getComputedStyle(held).zIndex;
      if (z !== 'auto') return Number(z);
    }
    return 0;
  };
  const order = (element) => [raised(element), at.get(element)];
  const part = (element) => {
    const held = box(element);
    const svg = element.ownerSVGElement;
    let by = 0;
    if (svg) {
      const stroke = parseFloat(getComputedStyle(element).strokeWidth) || 0;
      const scale = svg.getBoundingClientRect().width / (svg.viewBox.baseVal.width || 1);
      by = 5 * stroke * scale + 1;
    }
    return {
      x: held.x - by,
      y: held.y - by,
      width: held.width + 2 * by,
      height: held.height + 2 * by,
      order: order(element),
    };
  };
  document.body.getBoundingClientRect();
  await document.fonts.ready;
  const loaded = new Set(
    [...document.fonts]
      .filter((face) => face.status === 'loaded')
      .map((face) => key(bare(face.family), face.weight)),
  );
  const spans = within(document, marks.span);
  const read = (span) => {
    const style = getComputedStyle(span);
    const families = named(style.fontFamily);
    return {
      ...box(span),
      index: spans.indexOf(span),
      text: span.textContent,
      family: families[0] || '',
      weight: style.fontWeight,
      face: families.some((family) => loaded.has(key(family, style.fontWeight))),
      em: parseFloat(style.fontSize) || 0,
      order: order(span),
    };
  };
  return within(document, marks.page).map((page) => ({
    ...box(page),
    id: page.getAttribute(marks.page),
    texts: within(page, marks.text).map((text) => ({
      id: text.getAttribute(marks.text),
      lines: within(text, marks.line).map((line) => within(line, marks.span).map(read)),
    })),
    parts: [...page.querySelectorAll(`[${marks.layer}] [data-id], [${marks.ground}]`)]
      .map(part)
      .filter((each) => each.width > 0 && each.height > 0),
  }));
}"""

#: The document as the ink read sees it: the layers, the lines' grounds and the runs' signs
#: hidden, every span's ground taken away, on one ground, and of the spans only the one that
#: carries `ALONE_MARK`, which keeps its own paint. So only a span's letters leave ink.
GROUND = """(marks, ground, alone) => {
  const style = document.getElementById(alone) || document.createElement('style');
  style.id = alone;
  style.textContent = `
    [${marks.layer}], [${marks.ground}], [${marks.sign}], [${marks.span}]:not([${alone}]) {
      visibility: hidden !important}
    [${marks.span}] {background: none !important}
    html, body, [${marks.page}] {background: ${ground} !important}`;
  document.head.append(style);
}"""

#: One span marked to show, or not, by its place in the document.
ALONE = """(mark, index, alone, shown) => {
  document.querySelectorAll(`[${mark}]`)[index].toggleAttribute(alone, shown);
}"""

#: The attribute that marks the span drawn alone, and the id of the style that does so.
ALONE_MARK = "data-pkit-alone"

#: The read's own style of the document, by its id: `css` is all it holds.
STYLE = """(id, css) => {
  const style = document.getElementById(id) || document.createElement('style');
  style.id = id;
  style.textContent = css;
  document.head.append(style);
}"""

#: The spans that carry `mark`: those of `indices`, by their places among the document's spans,
#: and no other.
MARKED = """(span, mark, indices) => {
  const chosen = new Set(indices);
  document.querySelectorAll(`[${span}]`).forEach((each, index) => {
    each.toggleAttribute(mark, chosen.has(index));
  });
}"""

#: The ids of the read's own styles: the room past each page's edges, and the draw that reads
#: what the page shows of a span's strong ink.
ROOM_STYLE = "pkit-room"
DRAW_STYLE = "pkit-draw"

#: The attribute that marks each span whose strong ink a draw reads.
MEASURED_MARK = "data-pkit-measured"

#: How many device pixels of each span's strong ink lie past its page's edge, and how many on
#: its page the page drawn whole hides, from four images of one clip: the spans drawn alone
#: in each of the two colours, then the page drawn whole with their letters in each. A pixel
#: is strong where its letters alone change it by more than half the two colours'
#: difference. One on the page counts as hidden where the page drawn whole does not change
#: as the letters change. Each span is read within its box, widened by its em, which meets
#: no other's.
TALLY = """async (images, clip, spans) => {
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
  return spans.map(({box, page}) => {
    const left = Math.max(0, Math.floor((box.x - clip.x) * across));
    const right = Math.min(wide, Math.ceil((box.x + box.width - clip.x) * across));
    const top = Math.max(0, Math.floor((box.y - clip.y) * down));
    const bottom = Math.min(strong.height, Math.ceil((box.y + box.height - clip.y) * down));
    let found = 0, past = 0, hidden = 0;
    for (let row = top; row < bottom; row++) {
      const y = clip.y + (row + 0.5) / down;
      const outside = y < page.y || y >= page.y + page.height;
      for (let column = left; column < right; column++) {
        const at = (row * wide + column) * 4;
        let most = 0;
        for (let channel = 0; channel < 3; channel++) {
          most = Math.max(most, Math.abs(strong.data[at + channel] - ground.data[at + channel]));
        }
        if (2 * most <= apart) continue;
        found++;
        const x = clip.x + (column + 0.5) / across;
        if (outside || x < page.x || x >= page.x + page.width) past++;
        else if (
          shown.data[at] === unshown.data[at] &&
          shown.data[at + 1] === unshown.data[at + 1] &&
          shown.data[at + 2] === unshown.data[at + 2]
        ) hidden++;
      }
    }
    return {strong: found, past, hidden};
  });
}"""

#: The document as the file stands again, once the reads are done: the read's styles of `ids`
#: taken out, and each of `marks` taken off every element that carries it.
UNGROUND = """(ids, marks) => {
  for (const id of ids) {
    const style = document.getElementById(id);
    if (style) style.remove();
  }
  for (const mark of marks) {
    document.querySelectorAll(`[${mark}]`).forEach((each) => each.removeAttribute(mark));
  }
}"""

#: What `UNGROUND` takes out: every style and every mark of the reads.
READ_STYLES = (ALONE_MARK, ROOM_STYLE, DRAW_STYLE)
READ_MARKS = (ALONE_MARK, MEASURED_MARK)

#: A wait until the page has painted twice, after its signals were set.
SETTLE = """() => new Promise((done) => {
  requestAnimationFrame(() => requestAnimationFrame(() => done(null)));
})"""


class Stopped(Exception):
    """What stopped a drawing: `what`, where `find` looked, or the program started and what
    it said. As far as those words tell, `as_root` is whether the browser ran as root and so
    refused its own sandbox, and `sandbox` whether a sandbox stopped it otherwise."""

    def __init__(
        self, what: str, *, looked: Sequence[str] = (), program: str = "", said: str = ""
    ) -> None:
        super().__init__(what)
        self.what = what
        self.looked = tuple(looked)
        self.program = program
        self.said = said
        self.as_root = bool(AS_ROOT.search(said))
        self.sandbox = not self.as_root and bool(SANDBOX.search(said))

    def __str__(self) -> str:
        parts = [self.what]
        if self.looked:
            parts.append(f"looked at: {', '.join(self.looked)}")
        if self.program:
            parts.append(f"started: {self.program}")
        if self.said:
            parts.append(f"it said: {self.said}")
        return "; ".join(parts)


@dataclass(frozen=True)
class Text:
    """A text of the scene: its trace id, and the spans of each line as its `lines` hold
    them. A span is the part of a run on one line."""

    element: str
    lines: tuple[tuple[str, ...], ...]


@dataclass(frozen=True)
class Page:
    """A page wanted of the file: its trace id, its size in px, its texts, and the regions of
    its height to draw, each a top and a height in its px, none where it is drawn whole."""

    id: str
    width: float
    height: float
    texts: tuple[Text, ...]
    regions: tuple[tuple[float, float], ...] = ()


@dataclass(frozen=True)
class Image:
    """A page drawn: its trace id, the PNG file's bytes, its size in pixels, and the number of
    the region it shows, from 1, or 0 where it shows the page whole."""

    page: str
    image: bytes
    width: int
    height: int
    band: int = 0


@dataclass(frozen=True)
class Differs:
    """A text whose spans differ between the scene and the document: each line's, where it
    has any. `document` holds the lines of each element that carries its id."""

    page: str
    element: str
    scene: tuple[tuple[str, ...], ...]
    document: tuple[tuple[tuple[str, ...], ...], ...]


@dataclass(frozen=True)
class Dropped:
    """A span the page does not show in full, and why: `NO_INK`, `OFF_THE_PAGE`, `CUT` or
    `COVERED`, one cause an entry. A cut or covered entry gives the share of the span's strong
    ink its cause loses, from 0 to 1 (DEC-037 point 2)."""

    page: str
    element: str
    text: str
    why: str
    share: float | None = None


@dataclass(frozen=True)
class NoFace:
    """A span with no loaded face in the file: the first family it names, and its weight."""

    page: str
    element: str
    text: str
    family: str
    weight: str


@dataclass(frozen=True)
class MachineFont:
    """A span the browser drew, even in part, in a font of the machine, and each such font."""

    page: str
    element: str
    text: str
    fonts: tuple[str, ...]


@dataclass(frozen=True)
class Read:
    """What the four reads named of a document."""

    words: tuple[Differs, ...]
    dropped: tuple[Dropped, ...]
    no_face: tuple[NoFace, ...]
    machine_fonts: tuple[MachineFont, ...]
    refused: tuple[str, ...]


@dataclass(frozen=True)
class Shown:
    """One mode of a file drawn: the signals set, each page's image, what the four reads named,
    and the name of the forced palette it was drawn in, empty for none."""

    signals: Mapping[str, str]
    images: tuple[Image, ...]
    read: Read
    palette: str = ""


@dataclass(frozen=True)
class Drawing:
    """A file drawn: the browser with its version, and each mode or forced palette drawn, in
    order."""

    browser: str
    shown: tuple[Shown, ...]


def find(path: Path | None = None) -> Path:
    """The program to draw with: `path`, or else the first browser found where Chrome and
    Chromium install themselves. Starts nothing. Raises Stopped, naming where it looked."""
    if path is not None:
        if _runnable(path):
            return path
        raise Stopped("the browser named is no program that runs", looked=[str(path)])
    places = [Path(place).expanduser() for place in PLACES.get(sys.platform, ())]
    for place in places:
        if _runnable(place):
            return place
    for name in NAMES:
        found = shutil.which(name)
        if found:
            return Path(found)
    looked = [*(str(place) for place in places), *(f"`{name}` on the PATH" for name in NAMES)]
    raise Stopped("no browser of the Chromium family was found", looked=looked)


def _runnable(path: Path) -> bool:
    return path.is_file() and os.access(path, os.X_OK)


def draw(
    file: Path,
    pages: Sequence[Page],
    scale: float,
    browser: Path,
    folder: Path,
    *,
    signals: Mapping[str, Sequence[str]] | None = None,
    modes: Sequence[Mapping[str, str]] = ({},),
) -> Drawing:
    """The page file `file` through `browser`, in one start: for each of `modes`, in order, an
    image of each of `pages`, or of each region of one handed with its regions, at `scale`
    device pixels to a px, and what the four reads named.
    `signals` names each signal the file reads, with the values it may take, the first a
    reader's with no preference; each mode sets every one of them. The browser's profile lies
    under `folder`, which is made where it is missing, and which keeps nothing of this run.
    Raises Stopped, and gives no image, where a browser did not draw it all; ValueError where a
    mode does not set every signal named, or sets another."""
    read = dict(signals or {})
    for mode in modes:
        if set(mode) != set(read):
            raise ValueError(f"a mode sets {sorted(mode)}, and the file reads {sorted(read)}")
    return _start(file, pages, scale, browser, folder, read, [("", mode) for mode in modes])


def draw_forced(
    file: Path,
    pages: Sequence[Page],
    scale: float,
    browser: Path,
    folder: Path,
    *,
    signals: Mapping[str, Sequence[str]] | None = None,
) -> Drawing:
    """The page file `file` through `browser` in each forced palette of `PALETTES`, in their
    order, in a start of its own: the browser's flag forces its colours (`FORCING`), and each
    palette is set by emulating `FORCED` with the palette's signals. In all else as `draw`:
    the file opened once, at `scale`, an image of each of `pages` or of each of its regions,
    and the four reads, in each palette. Its first read checks that the palette reached the
    text, and that each palette is what its name says (DEC-027 points 3 and 4).
    `signals` names each signal the file reads, as `draw`'s does. Raises Stopped, and gives no
    image, where a browser did not draw it all; ValueError where a palette does not set a
    signal the file reads."""
    read = dict(signals or {})
    for palette in PALETTES:
        if not set(read) <= set(palette.signals):
            raise ValueError(
                f"the forced palette `{palette.name}` sets {sorted(palette.signals)}, and the "
                f"file reads {sorted(read)}"
            )
    modes = [(palette.name, {**palette.signals, **FORCED}) for palette in PALETTES]
    return _start(file, pages, scale, browser, folder, read, modes, forced=True)


def _start(
    file: Path,
    pages: Sequence[Page],
    scale: float,
    browser: Path,
    folder: Path,
    signals: Mapping[str, Sequence[str]],
    modes: Sequence[tuple[str, Mapping[str, str]]],
    *,
    forced: bool = False,
) -> Drawing:
    """One start of `browser` that draws `file` in each of `modes`, each the name of the forced
    palette it is, empty for none, with the signals it sets. `forced` is whether the start
    forces the browser's colours. The browser's profile lies under `folder`, which is made where
    it is missing, and which keeps nothing of this run."""
    folder.mkdir(parents=True, exist_ok=True)
    place = Path(tempfile.mkdtemp(prefix="browser-", dir=folder))
    try:
        started = _Started(browser, place, window_width(pages), scale, forced=forced)
        try:
            drawing = _drawn(started, place, file, pages, signals, modes, forced)
        except BaseException:
            started.close()
            raise
        if not started.close():
            raise started.stop("the browser did not close, so it was ended")
        return drawing
    finally:
        _remove(place)


def window_width(pages: Sequence[Page]) -> float:
    """The width of the window that holds each of `pages` at its own size: the widest, with
    the gutter on each side (DEC-031 point 5)."""
    return max(page.width for page in pages) + 2 * GUTTER


def _drawn(
    started: _Started,
    place: Path,
    file: Path,
    pages: Sequence[Page],
    signals: Mapping[str, Sequence[str]],
    modes: Sequence[tuple[str, Mapping[str, str]]],
    forced: bool,
) -> Drawing:
    """The first read, then the file, opened once: in each mode its images first, as it stands,
    then its reads, and the document made as the file stands again. A request refused as the
    file loaded counts in each mode. A browser whose answers take another form, after an
    update say, stops the drawing too."""
    try:
        version = started.call("Browser.getVersion", within=START_SECONDS)["product"]
        started.open_tab()
        _first_read(started, place, signals, forced=forced)
        started.open(file.resolve().as_uri())
        loaded = list(started.refused)
        shown = []
        for palette, mode in modes:
            started.emulate(mode)
            started.refused = list(loaded)
            found = _found(started, pages)
            for page, held in zip(pages, found, strict=True):
                _hold_to_its_size(started, page, held)
            images = tuple(
                image
                for page, held in zip(pages, found, strict=True)
                for image in _images(started, page, held)
            )
            shown.append(Shown(dict(mode), images, _read(started, pages, found), palette))
            started.ask(UNGROUND, READ_STYLES, READ_MARKS)
        return Drawing(version, tuple(shown))
    except UNREADABLE as exc:
        raise started.stop(f"the browser gave an answer that cannot be read: {exc!r}") from exc


def _hold_to_its_size(started: _Started, page: Page, held: Mapping[str, Any]) -> None:
    """Stop where a page does not measure what the scene says, so no image shows it shrunk."""
    if abs(held["width"] - page.width) > MEASURE or abs(held["height"] - page.height) > MEASURE:
        raise started.stop(
            f"page `{page.id}` measures {held['width']:g} by {held['height']:g} px in the "
            f"browser, and {page.width:g} by {page.height:g} px in the scene"
        )


def _opened(started: _Started, file: Path, pages: Sequence[Page]) -> list[Mapping[str, Any]]:
    """What the document holds of each of `pages`, once it has loaded."""
    started.open(file.resolve().as_uri())
    return _found(started, pages)


def _found(started: _Started, pages: Sequence[Page]) -> list[Mapping[str, Any]]:
    """What the open document holds of each of `pages`, as it stands."""
    held = {page["id"]: page for page in started.ask(READ, MARKS)}
    for page in pages:
        if page.id not in held:
            raise started.stop(f"the file holds no page `{page.id}`")
    return [held[page.id] for page in pages]


def _images(started: _Started, page: Page, held: Mapping[str, Any]) -> Iterator[Image]:
    """The images of `page`, which the document holds as `held`: one of the whole page, or one
    of each of its regions, each as wide as the page (DEC-022 point 7)."""
    if not page.regions:
        yield _image(started, held, {side: held[side] for side in ("x", "y", "width", "height")})
        return
    for number, (top, height) in enumerate(page.regions, 1):
        clip = {"x": held["x"], "y": held["y"] + top, "width": held["width"], "height": height}
        yield _image(started, held, clip, number)


def _image(
    started: _Started, held: Mapping[str, Any], clip: Mapping[str, float], band: int = 0
) -> Image:
    picture = started.picture(clip)
    width, height = struct.unpack(">II", picture[PNG_SIZE])
    return Image(held["id"], picture, width, height, band)


def _read(started: _Started, pages: Sequence[Page], found: Sequence[Mapping[str, Any]]) -> Read:
    """The four reads of what `found` holds of `pages`. The ink read comes last: it leaves the
    document unlike the file."""
    pairs = zip(pages, found, strict=True)
    words = tuple(each for page, held in pairs for each in _words(page, held))
    no_face = tuple(_no_face(found))
    machine_fonts = tuple(_machine_fonts(started, found))
    dropped = tuple(_dropped(started, found))
    return Read(words, dropped, no_face, machine_fonts, tuple(started.refused))


def _spans(found: Sequence[Mapping[str, Any]]) -> Iterator[tuple[Mapping[str, Any], str, Any]]:
    """Each span of `found`, with its page and the trace id of its text."""
    for page in found:
        for text in page["texts"]:
            for line in text["lines"]:
                for span in line:
                    yield page, text["id"], span


def _words(page: Page, held: Mapping[str, Any]) -> Iterator[Differs]:
    """Each text of `page` that differs from the document, and each the scene does not hold."""
    document: dict[str, list[tuple[tuple[str, ...], ...]]] = {}
    for text in held["texts"]:
        lines = tuple(tuple(span["text"] for span in line) for line in text["lines"])
        document.setdefault(text["id"], []).append(lines)
    for text in page.texts:
        found = document.pop(text.element, [])
        if found != [text.lines]:
            yield Differs(page.id, text.element, text.lines, tuple(found))
    for element, found in document.items():
        yield Differs(page.id, element, (), tuple(found))


def _no_face(found: Sequence[Mapping[str, Any]]) -> Iterator[NoFace]:
    """Each span with a text and no loaded face. A span with none asks for no face."""
    for page, element, span in _spans(found):
        if span["text"] and not span["face"]:
            yield NoFace(page["id"], element, span["text"], span["family"], span["weight"])


def _machine_fonts(started: _Started, found: Sequence[Mapping[str, Any]]) -> Iterator[MachineFont]:
    """Each span the browser drew, even in part, in a font of the machine."""
    root = started.call("DOM.getDocument")["root"]["nodeId"]
    nodes = started.call("DOM.querySelectorAll", nodeId=root, selector=f"[{MARKS['span']}]")
    for page, element, span in _spans(found):
        node = nodes["nodeIds"][span["index"]]
        fonts = started.call("CSS.getPlatformFontsForNode", nodeId=node)["fonts"]
        machine = tuple(font["familyName"] for font in fonts if not font["isCustomFont"])
        if machine:
            yield MachineFont(page["id"], element, span["text"], machine)


def _dropped(started: _Started, found: Sequence[Mapping[str, Any]]) -> Iterator[Dropped]:
    """Each span the page does not show in full, one cause an entry, in the document's order
    (DEC-020 point 6, DEC-037 points 1 to 3). Each page is read with room past its edges, as
    the document holds it then. A span wholly off its page is named so alone. Each other is
    read for ink in its own paint, alone, on one ground and then on another, since what one
    shows the next need not; and, where the pre-filter does not pass over it, for its strong
    ink past its page's edge and hidden on its page."""
    room = _room(found)
    started.ask(STYLE, ROOM_STYLE, _room_sheet(found, room))
    held = {page["id"]: page for page in started.ask(READ, MARKS)}
    laid = [held[page["id"]] for page in found]
    named: list[tuple[int, int, Dropped]] = []
    waiting = []
    for page, element, span in _spans(laid):
        if not span["text"].strip():
            continue
        if _outside(span, page):
            named.append(_entry(page, element, span, OFF_THE_PAGE))
        else:
            waiting.append((page, element, span))
    named += [
        _entry(page, element, span, why, share)
        for page, element, span, why, share in _lost(started, laid, waiting, room)
    ]
    started.ask(STYLE, DRAW_STYLE, "")
    started.ask(MARKED, MARKS["span"], MEASURED_MARK, [])
    for ground in GROUNDS:
        started.ask(GROUND, MARKS, ground, ALONE_MARK)
        blanks: dict[tuple[float, ...], bytes] = {}
        waiting = [
            each for each in waiting if not _left_ink(started, each[0], each[2], blanks, room)
        ]
    named += [_entry(page, element, span, NO_INK) for page, element, span in waiting]
    for *_, entry in sorted(named, key=lambda each: each[:2]):
        yield entry


def _entry(
    page: Mapping[str, Any],
    element: str,
    span: Mapping[str, Any],
    why: str,
    share: float | None = None,
) -> tuple[int, int, Dropped]:
    """An entry of `dropped`, with the span's place in the document and its cause's, which
    order the entries."""
    dropped = Dropped(page["id"], element, span["text"], why, share)
    return span["index"], CAUSES.index(why), dropped


def _widened(box: Mapping[str, Any], by: float) -> dict[str, float]:
    """`box` widened by `by` on each side."""
    return {
        "x": box["x"] - by,
        "y": box["y"] - by,
        "width": box["width"] + 2 * by,
        "height": box["height"] + 2 * by,
    }


def _meet(one: Mapping[str, Any], other: Mapping[str, Any]) -> bool:
    """Whether two boxes share some area. A box with no area meets none."""
    if min(one["width"], one["height"], other["width"], other["height"]) <= 0:
        return False
    return (
        one["x"] < other["x"] + other["width"]
        and other["x"] < one["x"] + one["width"]
        and one["y"] < other["y"] + other["height"]
        and other["y"] < one["y"] + one["height"]
    )


def _within(box: Mapping[str, Any], page: Mapping[str, Any]) -> bool:
    """Whether `box` lies wholly on `page`."""
    return (
        box["x"] >= page["x"]
        and box["y"] >= page["y"]
        and box["x"] + box["width"] <= page["x"] + page["width"]
        and box["y"] + box["height"] <= page["y"] + page["height"]
    )


def _room(found: Sequence[Mapping[str, Any]]) -> int:
    """How much room the read gives each page past each of its edges, in px: as far as the box
    of a span on a page, widened by its em, reaches past one, so it holds all the span's ink
    (DEC-037 point 3)."""
    reach = 0.0
    for page, _, span in _spans(found):
        if not span["text"].strip() or _outside(span, page):
            continue
        box = _widened(span, span["em"])
        reach = max(
            reach,
            page["x"] - box["x"],
            page["y"] - box["y"],
            box["x"] + box["width"] - page["x"] - page["width"],
            box["y"] + box["height"] - page["y"] - page["height"],
        )
    return math.ceil(reach)


def _room_sheet(found: Sequence[Mapping[str, Any]], room: int) -> str:
    """The style that gives each page `room` px past each of its edges and keeps its size as
    drawn: the document as wide as the widest page drawn, with the room around it, and each
    page apart from the next by its room and the next's. No keyline lies past a page's edge."""
    widest = max((float(page["width"]) for page in found), default=0.0)
    page = f"[{MARKS['page']}]"
    return (
        f"body{{width:{widest}px!important;padding:{room}px!important;margin:0!important}}"
        f"{page}{{margin:0 auto!important;outline:none!important}}"
        f"{page}+{page}{{margin-top:{2 * room}px!important}}"
    )


def _passed_over(
    page: Mapping[str, Any], span: Mapping[str, Any], spans: Sequence[Mapping[str, Any]]
) -> bool:
    """Whether the pre-filter passes over `span`, of `spans` on `page`: its box, widened by its
    em, stays on its page, meets no other span's box, and meets no part painted after it, by
    their z-index, then their place in the document (DEC-037 point 3)."""
    box = _widened(span, span["em"])
    if not _within(box, page):
        return False
    if any(_meet(box, other) for other in spans if other["index"] != span["index"]):
        return False
    after = tuple(span["order"])
    return not any(_meet(box, part) and tuple(part["order"]) > after for part in page["parts"])


def _batches(
    waiting: Sequence[tuple[Mapping[str, Any], str, Mapping[str, Any]]],
) -> list[list[tuple[Mapping[str, Any], str, Mapping[str, Any]]]]:
    """`waiting` in batches whose spans' boxes, each widened by its em, meet none of another's
    of the batch, so they are drawn at once."""
    batches: list[list[tuple[Mapping[str, Any], str, Mapping[str, Any]]]] = []
    for each in waiting:
        box = _widened(each[2], each[2]["em"])
        for batch in batches:
            if not any(_meet(box, _widened(other[2], other[2]["em"])) for other in batch):
                batch.append(each)
                break
        else:
            batches.append([each])
    return batches


def _strength_draws() -> tuple[str, ...]:
    """The four draws a batch is read in, as the style of each: its spans alone, their letters
    in each of the two colours of `STRENGTH`, on the second, with no other text, no text's
    ground and no sign; then the page drawn whole, their letters in each colour, all else as
    it stands (DEC-037 point 3)."""
    page, marked = f"[{MARKS['page']}]", f"[{MEASURED_MARK}]"
    alone = (
        f"{page} *{{visibility:hidden!important}}{marked}{{visibility:visible!important}}"
        f"{marked} [{MARKS['sign']}]{{visibility:hidden!important}}"
        f"[{MARKS['span']}]{{background:none!important}}"
        f"html,body,{page}{{background:{STRENGTH[1]}!important}}"
    )
    return tuple(
        f"{drawn}{marked}{{color:{colour}!important}}"
        for drawn in (alone, "")
        for colour in STRENGTH
    )


def _clip(boxes: Sequence[Mapping[str, Any]], page: Mapping[str, Any], room: int) -> dict[str, int]:
    """The clip that holds each of `boxes` on `page`, as far as the page's room reaches, in
    whole px, and never before the document's start, where a browser takes no clip."""
    left = max(math.floor(max(min(box["x"] for box in boxes), page["x"] - room)), 0)
    top = max(math.floor(max(min(box["y"] for box in boxes), page["y"] - room)), 0)
    right = math.ceil(
        min(max(box["x"] + box["width"] for box in boxes), page["x"] + page["width"] + room)
    )
    bottom = math.ceil(
        min(max(box["y"] + box["height"] for box in boxes), page["y"] + page["height"] + room)
    )
    return {"x": left, "y": top, "width": max(right - left, 1), "height": max(bottom - top, 1)}


def _lost(
    started: _Started,
    found: Sequence[Mapping[str, Any]],
    waiting: Sequence[tuple[Mapping[str, Any], str, Mapping[str, Any]]],
    room: int,
) -> Iterator[tuple[Mapping[str, Any], str, Mapping[str, Any], str, float]]:
    """Each span of `waiting` whose strong ink past its page's edge, or hidden on its page,
    passes the sliver, with its cause and its share of the span's strong ink (DEC-037 points
    1 and 3). The pre-filter passes over a span that can lose none, and the others are drawn
    in batches."""
    on = {page["id"]: [span for _, _, span in _spans([page])] for page in found}
    measured = [each for each in waiting if not _passed_over(each[0], each[2], on[each[0]["id"]])]
    draws = _strength_draws()
    for batch in _batches(measured):
        started.ask(MARKED, MARKS["span"], MEASURED_MARK, [span["index"] for _, _, span in batch])
        pages: dict[str, list[tuple[Mapping[str, Any], str, Mapping[str, Any]]]] = {}
        for each in batch:
            pages.setdefault(each[0]["id"], []).append(each)
        clips = {
            held: _clip([_widened(span, span["em"]) for _, _, span in spans], spans[0][0], room)
            for held, spans in pages.items()
        }
        images: dict[str, list[str]] = {held: [] for held in pages}
        for draw in draws:
            started.ask(STYLE, DRAW_STYLE, draw)
            for held, clip in clips.items():
                images[held].append(base64.b64encode(started.picture(clip)).decode("ascii"))
        for held, spans in pages.items():
            asked = [
                {
                    "index": span["index"],
                    "box": _widened(span, span["em"]),
                    "page": {side: page[side] for side in ("x", "y", "width", "height")},
                }
                for page, _, span in spans
            ]
            counted = started.ask(TALLY, images[held], clips[held], asked)
            for (page, element, span), count in zip(spans, counted, strict=True):
                least = SLIVER * (span["em"] * started.scale) ** 2
                strong = count["strong"]
                for why, lost in ((CUT, count["past"]), (COVERED, count["hidden"])):
                    if strong and lost >= least:
                        yield page, element, span, why, lost / strong


def _outside(span: Mapping[str, Any], page: Mapping[str, Any]) -> bool:
    """Whether a span's box meets none of its page. An empty box is no sign of where it lies."""
    if span["width"] <= 0 or span["height"] <= 0:
        return False
    return (
        span["x"] + span["width"] <= page["x"]
        or span["x"] >= page["x"] + page["width"]
        or span["y"] + span["height"] <= page["y"]
        or span["y"] >= page["y"] + page["height"]
    )


def _left_ink(
    started: _Started,
    page: Mapping[str, Any],
    span: Mapping[str, Any],
    blanks: dict[tuple[float, ...], bytes],
    room: int = 0,
) -> bool:
    """Whether `span` alone changes the band of its page around it, as far as the page's room
    reaches. Each band is compared with itself empty, since a clip's pixels depend on where it
    lies."""
    band = _band(span, page, room)
    key = tuple(band.values())
    if key not in blanks:
        blanks[key] = started.picture(band)
    started.ask(ALONE, MARKS["span"], span["index"], ALONE_MARK, True)
    picture = started.picture(band)
    started.ask(ALONE, MARKS["span"], span["index"], ALONE_MARK, False)
    return picture != blanks[key]


def _band(span: Mapping[str, Any], page: Mapping[str, Any], room: int = 0) -> dict[str, float]:
    """The band of `page` around `span`: the span's box and its height either way, and the
    page's width, each as far as the page's `room` past its edges reaches, and never before the
    document's start, where a browser takes no clip."""
    top = max(math.floor(span["y"] - span["height"]), math.floor(page["y"] - room), 0)
    bottom = min(
        math.ceil(span["y"] + 2 * span["height"]),
        math.ceil(page["y"] + page["height"] + room),
    )
    left = max(page["x"] - room, 0.0)
    return {
        "x": left,
        "y": top,
        "width": page["x"] + page["width"] + room - left,
        "height": max(bottom - top, 1),
    }


class _Started:
    """A browser this module started, and the one tab it reads in."""

    def __init__(
        self, program: Path, place: Path, width: float, scale: float, *, forced: bool = False
    ) -> None:
        self.program = str(program)
        self.scale = scale
        self.window = math.ceil(width)
        self.refused: list[str] = []
        self._said = place / SAID
        self._held = bytearray()
        self._calls = 0
        self._session = ""
        self._own = ""
        self._loaded: set[str] = set()
        self._ended = False
        flags = [
            *FLAGS,
            *((FORCING,) if forced else ()),
            f"--user-data-dir={place / PROFILE}",
            f"--force-device-scale-factor={scale:g}",
            f"--window-size={self.window},{WINDOW_HEIGHT}",
            "about:blank",
        ]
        its_reads, self._to = os.pipe()
        self._from, its_writes = os.pipe()
        os.set_blocking(self._to, False)
        self._process = self._start(flags, its_reads, its_writes)

    def _start(self, flags: Sequence[str], reads: int, writes: int) -> subprocess.Popen[bytes]:
        """Start the program in a process group of its own, its messages on the descriptors the
        protocol names. Python cannot set them itself, so a shell puts them there first. The
        pipes took the lowest free descriptors, so a copy of an end lies above those two. It
        opens each by its path, since a redirect of the form `3<&12` takes one digit in some
        shells, dash among them."""
        handed = [os.dup(reads), os.dup(writes)]
        redirected = f"{BROWSER_READS}</dev/fd/{handed[0]} {BROWSER_WRITES}>/dev/fd/{handed[1]}"
        try:
            with self._said.open("wb") as said:
                return subprocess.Popen(
                    ["/bin/sh", "-c", f'exec "$0" "$@" {redirected}', self.program, *flags],
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=said,
                    pass_fds=handed,
                    start_new_session=True,
                )
        except OSError as exc:
            os.close(self._to)
            os.close(self._from)
            raise Stopped(f"the browser did not start: {exc}", program=self.program) from exc
        finally:
            for end in (reads, writes, *handed):
                os.close(end)

    def stop(self, what: str) -> Stopped:
        """A stop that says what the program said so far."""
        said = self._said.read_bytes()[-SAID_LENGTH:].decode("utf-8", "replace").strip()
        return Stopped(what, program=self.program, said=said)

    def open_tab(self) -> None:
        """Open the tab every read lies in, with each request held for `_heard`."""
        target = self.call("Target.createTarget", url="about:blank")["targetId"]
        self._session = self.call("Target.attachToTarget", targetId=target, flatten=True)[
            "sessionId"
        ]
        for domain in ("Page", "DOM", "CSS"):
            self.call(f"{domain}.enable")
        self.call("Page.setLifecycleEventsEnabled", enabled=True)
        self.call("Fetch.enable", patterns=[{"urlPattern": "*"}])

    def open(self, url: str) -> None:
        """Read `url` in the tab, as far as its load event."""
        self._own = url
        self.refused = []
        opened = self.call("Page.navigate", url=url)
        if "errorText" in opened:
            raise self.stop(f"the browser could not open {url}: {opened['errorText']}")
        deadline = time.monotonic() + CALL_SECONDS
        while opened.get("loaderId") not in self._loaded:
            self._heard(self._next(deadline, "the page's load"))

    def emulate(self, signals: Mapping[str, str]) -> None:
        """Set each of `signals` by the browser's emulation of a reader's media features, every
        other one at the browser's own, and wait until the page has painted."""
        features = [{"name": name, "value": value} for name, value in sorted(signals.items())]
        self.call("Emulation.setEmulatedMedia", features=features)
        self.ask(SETTLE)

    def ask(self, function: str, *arguments: Any) -> Any:
        """What `function` of JavaScript gives, called in the page with `arguments`."""
        answer = self.call(
            "Runtime.evaluate",
            expression=f"({function})(...{json.dumps(arguments)})",
            awaitPromise=True,
            returnByValue=True,
        )
        if "exceptionDetails" in answer:
            details = answer["exceptionDetails"]
            said = details.get("exception", {}).get("description") or details.get("text")
            raise self.stop(f"the browser could not read the page: {said}")
        return answer["result"].get("value")

    def picture(self, clip: Mapping[str, float]) -> bytes:
        """The PNG of a part of the document, past the window where it reaches past it."""
        taken = self.call(
            "Page.captureScreenshot",
            format="png",
            captureBeyondViewport=True,
            clip={**clip, "scale": 1},
        )
        return base64.b64decode(taken["data"])

    def call(self, method: str, within: float | None = None, **params: Any) -> dict[str, Any]:
        """The browser's answer to one call, `within` seconds or `CALL_SECONDS`. Raises Stopped
        where it refuses, stops or hangs."""
        deadline = time.monotonic() + (within or CALL_SECONDS)
        mine = self._post(method, params, deadline)
        while True:
            got = self._next(deadline, f"`{method}`")
            if got.get("id") != mine:
                self._heard(got)
            elif "error" in got:
                raise self.stop(f"the browser refused `{method}`: {got['error'].get('message')}")
            else:
                return got.get("result", {})

    def close(self) -> bool:
        """Bring the browser down: by asking, then within `CLOSE_SECONDS` by force, unless it
        hung already. Gives whether it closed by itself."""
        self._session = ""
        with contextlib.suppress(Stopped):
            if not self._ended:
                self._post("Browser.close", {}, time.monotonic() + CLOSE_SECONDS)
        closed = True
        try:
            self._process.wait(0 if self._ended else CLOSE_SECONDS)
        except subprocess.TimeoutExpired:
            closed = False
            # Not yet waited for, so its id, and the group's, are still its own.
            with contextlib.suppress(OSError):
                os.killpg(self._process.pid, signal.SIGKILL)
            with contextlib.suppress(subprocess.TimeoutExpired):
                self._process.wait(CLOSE_SECONDS)
        os.close(self._to)
        os.close(self._from)
        return closed

    def _post(self, method: str, params: Mapping[str, Any], deadline: float) -> int:
        """Send one call by `deadline`, and give its id."""
        self._calls += 1
        message: dict[str, Any] = {"id": self._calls, "method": method, "params": params}
        if self._session:
            message["sessionId"] = self._session
        self._send(message, deadline, f"`{method}`")
        return self._calls

    def _send(self, message: Mapping[str, Any], deadline: float, doing: str) -> None:
        left = memoryview(json.dumps(message).encode() + b"\0")
        while left:
            if not select.select([], [self._to], [], self._until(deadline))[1]:
                self._hung(doing)
            try:
                left = left[os.write(self._to, left) :]
            except BrokenPipeError:
                self._died(doing)

    def _next(self, deadline: float, doing: str) -> dict[str, Any]:
        """The browser's next message, by `deadline`."""
        searched = 0
        while True:
            end = self._held.find(b"\0", searched)
            if end >= 0:
                message = bytes(self._held[:end])
                del self._held[: end + 1]
                try:
                    return json.loads(message)
                except ValueError:
                    raise self.stop("the program does not speak a browser's protocol") from None
            searched = len(self._held)
            if not select.select([self._from], [], [], self._until(deadline))[0]:
                self._hung(doing)
            data = os.read(self._from, 1 << 20)
            if not data:
                self._died(doing)
            self._held += data

    def _until(self, deadline: float) -> float:
        return max(deadline - time.monotonic(), 0.0)

    def _hung(self, doing: str) -> NoReturn:
        self._ended = True
        raise self.stop(f"the browser did not answer {doing} in time, and was ended")

    def _died(self, doing: str) -> NoReturn:
        self._ended = True
        with contextlib.suppress(subprocess.TimeoutExpired):
            self._process.wait(CLOSE_SECONDS)
        raise self.stop(f"the browser stopped at {doing}, exit {self._process.returncode}")

    def _heard(self, message: Mapping[str, Any]) -> None:
        """A message no call waits for: a load, or a request held, let through or refused."""
        params = message.get("params", {})
        if message.get("method") == "Page.lifecycleEvent" and params["name"] == "load":
            self._loaded.add(params["loaderId"])
        elif message.get("method") == "Fetch.requestPaused":
            url, request = params["request"]["url"], {"requestId": params["requestId"]}
            deadline = time.monotonic() + CALL_SECONDS
            if url == self._own or url.startswith("data:"):
                self._post("Fetch.continueRequest", request, deadline)
            else:
                self.refused.append(url)
                refusal = {**request, "errorReason": "BlockedByClient"}
                self._post("Fetch.failRequest", refusal, deadline)


def _remove(place: Path) -> None:
    """Remove a throwaway folder, trying again while a helper of the browser still writes."""
    for _ in range(REMOVALS):
        shutil.rmtree(place, ignore_errors=True)
        if not place.exists():
            return
        time.sleep(REMOVAL_WAIT)


# The first read: a file of its own, in the renderer's form.

#: The planted file's pages, by their trace ids, each with its size in px: its first, which
#: holds every plant but one, and the page of the span a part covers by z-index, which the
#: first page carries none of (DEC-037 point 5). Their lengths are shares of their width, so
#: they fit any window.
PLANTED_ID = "planted"
PLANTED_WIDTH = 480
PLANTED_HEIGHT = 800
RAISED_ID = "planted-raised"
RAISED_HEIGHT = 48

#: How far apart the planted rows lie, how high each line's strut is, how wide a text's frame,
#: and the size most texts take, in px of a page. A text's first baseline lies a row below its
#: frame's top.
ROW = 24
STRUT = 32
TEXT_WIDTH = 464
SIZE = 14

#: The rules of the planted file, which a test holds to the renderer's.
PLANTED_SHEET = "".join(
    (
        "body{margin:0}",
        f"[{MARKS['page']}]{{position:relative;container-type:inline-size;margin:0 auto}}",
        f"[{MARKS['page']}]+[{MARKS['page']}]"
        f"{{margin-top:{html_declaration.DECLARATION['pages']['gap']}px}}",
        f"[{MARKS['layer']}]{{position:absolute;left:0;top:0;width:100%;height:100%;"
        "pointer-events:none}",
        f"[{MARKS['text']}]{{position:absolute}}",
        f"[{MARKS['line']}]{{position:absolute;left:0;width:100%;font-size:0;line-height:0;"
        "white-space:pre}",
        f"[{MARKS['strut']}]{{display:inline-block;width:0}}",
        f"[{MARKS['ground']}]{{position:absolute;display:none;pointer-events:none}}",
        "[data-inset]{display:none}",
    )
)

#: What the forced form's rules are, as the renderer's declaration names them (DEC-023 point 7,
#: DEC-039): the colours of a line, a fill and its edge, and a line's ground with its margin.
FORCED_COLOURS: Mapping[str, Any] = html_declaration.DECLARATION["forced-colours"]
EDGE: float = FORCED_COLOURS["edge"]["width"]
MARGIN: float = FORCED_COLOURS["grounds"]["margin"]

#: What the planted file holds under forced colours whatever it draws, as each of the
#: renderer's files does, which a test holds to the renderer's (DEC-039 points 1, 3 and 4).
PLANTED_FORCED_SHEET = "".join(
    (
        f"[{MARKS['ground']}]{{display:block;background:{FORCED_COLOURS['grounds']['colour']}}}",
        f"[{MARKS['line']}]{{forced-color-adjust:none}}",
        f"[{MARKS['span']}]{{forced-color-adjust:auto;background:none!important}}",
        f"[data-inset]{{display:inline;fill:{FORCED_COLOURS['opaque-fills']}}}",
    )
)

#: The face the file holds, which the capability ships, and the families it plants a fault in.
PLANTED_FACE = (
    Path(__file__).resolve().parents[2] / "libraries/neutral/fonts/SourceSansPro-Regular.otf"
)
HELD = "pkit-held"
LEFT_OUT = "pkit-left-out"
BROKEN = "pkit-broken"

#: The face's reach above its baseline and below it, in ems, as the engine reads it, which
#: sizes each line's ground. For the plants set in device pixels: the foot of the descenders
#: of the edge control's word, and a height between the top of a `z` and the foot of the
#: háček over it, in ems. A test holds each to the face.
ASCENT = 0.984
DESCENT = 0.273
FOOT = 0.224
UNDER_THE_HACEK = 0.53

#: The edge control's em, and the command's text floor, which the háček plant's em takes, in
#: device pixels (DEC-037 point 5, DEC-015 point 5). The outputs page states the first, and a
#: test holds the second to the viewing step's.
CONTROL_EM = 40
TEXT_FLOOR = 10

#: The fill of the planted file's boxes, opaque in every key, and of its translucent one.
BOX = "#808080"
TRANSLUCENT = "#80808080"

#: A character the face lacks, and the requests the page makes. The character, "identical to",
#: lies in the faces a machine falls back to: macOS's, and on Linux fontconfig's defaults and
#: those Chrome's package installs. A character of one script alone, such as Chinese, has no
#: font on a machine without that script's, and there the browser draws it in the face, as a
#: box.
LACKED = "≡"
NETWORK = "https://example.invalid/network.png"
BESIDE = "beside.png"


@dataclass(frozen=True)
class _Planted:
    """A span of the planted file, with what it looks like. Under forced colours, a span with no
    paint is kept out of forcing unless it is `forced`. A `marked` span draws a run's sign and
    ground, inked, which are no ink of its letters (DEC-036 point 3). A `grounded` one draws a
    run's ground alone, which under forced colours lies in its line's (DEC-039 point 3)."""

    text: str
    family: str = HELD
    weight: int = 400
    colour: str = "#000000"
    left: int = 8
    forced: bool = False
    marked: bool = False
    grounded: bool = False


#: A span's paint where it has none, and the texts of the plants that the reads name or leave
#: unnamed by where they lie: a text whose document lacks a span of the scene's, one cut past
#: its page's top edge, one under a later box, one wholly under another text, whose run's
#: ground covers it, with a part between them, one under a translucent fill, the háček plant,
#: the edge control, and the text a part covers by z-index (DEC-037 point 5).
UNPAINTED = "transparent"
SPAN_TAKEN_OUT = "span-taken-out"
CUT_PAST_THE_TOP = "cut-past-the-top"
UNDER_A_BOX = "under-a-later-box"
UNDER_ANOTHER = "under-another-text"
OVER_ANOTHER = "over-another-text"
UNDER_A_TRANSLUCENT_FILL = "under-a-translucent-fill"
HACEK = "hacek-under-a-box"
EDGE_CONTROL = "edge-control"
RAISED = "covered-by-z-index"

#: Each text of the planted file's first page, by a trace id that says what it holds, in the
#: tree's order: the text cut past the top, then the texts set in rows from the top down,
#: then the plants set in device pixels.
PLANTED_TEXTS: Mapping[str, tuple[tuple[_Planted, ...], ...]] = {
    CUT_PAST_THE_TOP: ((_Planted("Cut off"),),),
    "clean": ((_Planted("clean"),),),
    "no-paint-alone": ((_Planted("alone", colour=UNPAINTED),),),
    "no-paint-between": (
        (_Planted("above"),),
        (_Planted("between", colour=UNPAINTED),),
        (_Planted("below"),),
    ),
    "no-paint-beside": ((_Planted("painted "), _Planted("beside", colour=UNPAINTED)),),
    "no-paint-marked": ((_Planted("marked", colour=UNPAINTED, marked=True),),),
    "off-the-page": ((_Planted("away", left=4000),),),
    "face-left-out": ((_Planted("left out", family=LEFT_OUT),),),
    "face-broken": ((_Planted("broken", family=BROKEN),),),
    "weight-with-no-face": ((_Planted("heavy", weight=700),),),
    "character-the-face-lacks": ((_Planted(f"lacks {LACKED}"),),),
    # Written as it stands, so the parser swallows the rest of the run.
    "run-swallowed": ((_Planted("swal<lowed"),),),
    SPAN_TAKEN_OUT: ((_Planted("kept "),),),
    UNDER_A_BOX: ((_Planted("covered"),),),
    "colour-of-its-ground": ((_Planted("unseen", colour="#ffffff"),),),
    UNDER_ANOTHER: ((_Planted("beneath"),),),
    OVER_ANOTHER: ((_Planted("beneath", grounded=True),),),
    UNDER_A_TRANSLUCENT_FILL: ((_Planted("faint"),),),
    HACEK: ((_Planted("ž"),),),
    EDGE_CONTROL: ((_Planted("jogging"),),),
}

#: The texts set in rows, in order. The text over another lies in the row of the one under it.
ROWED = tuple(
    element for element in PLANTED_TEXTS if element not in (CUT_PAST_THE_TOP, HACEK, EDGE_CONTROL)
)

#: Where the texts not set in rows lie, by their first baselines in px of the page, and how far
#: apart the lines of the text left to forcing lie: below its size's height, as DEC-039 point 5
#: sets it. Each place leaves room for the plants set in device pixels at any device scale
#: down to 0.4.
CUT_BASELINE = 6
HACEK_BASELINE = 520
CONTROL_BASELINE = 640
FORCED_BASELINE = 720
FORCED_STEP = 15

#: The text of the planted file's page of its own, which a part earlier in the document covers
#: by z-index.
RAISED_TEXTS: Mapping[str, tuple[tuple[_Planted, ...], ...]] = {RAISED: ((_Planted("raised"),),)}

#: A span the scene holds and the planted document does not.
TAKEN_OUT = "taken"

#: The text a start that forces its colours adds to the planted file's first page, below the
#: others: two lines with no paint, left to forcing, the first with descenders, at a step below
#: their size's height, on the file's grounds. Each shows ink only where the forced palette
#: reached the text, and loses none to the line below where no backplate covers it (DEC-027
#: point 4, DEC-039 point 5).
FORCED_TEXT = "no-paint-forced"
FORCED_FIRST = "jumpy"
FORCED_SPAN = "forced"
FORCED_TEXTS: Mapping[str, tuple[tuple[_Planted, ...], ...]] = {
    FORCED_TEXT: (
        (_Planted(FORCED_FIRST, colour=UNPAINTED, forced=True),),
        (_Planted(FORCED_SPAN, colour=UNPAINTED, forced=True),),
    ),
}

#: The file such a start writes the planted file to.
PLANTED_FORCED_FILE = "planted.forced.html"


def _scene_text(element: str, lines: Sequence[Sequence[_Planted]]) -> Text:
    """A text of the planted file as the scene holds it."""
    held = tuple(tuple(span.text for span in line) for line in lines)
    return Text(element, ((*held[0], TAKEN_OUT),) if element == SPAN_TAKEN_OUT else held)


def _scene_texts(texts: Mapping[str, Sequence[Sequence[_Planted]]]) -> tuple[Text, ...]:
    return tuple(_scene_text(element, lines) for element, lines in texts.items())


#: The planted file's pages as the scene holds them, and as they are under forced colours.
PLANTED_PAGES = (
    Page(PLANTED_ID, PLANTED_WIDTH, PLANTED_HEIGHT, _scene_texts(PLANTED_TEXTS)),
    Page(RAISED_ID, PLANTED_WIDTH, RAISED_HEIGHT, _scene_texts(RAISED_TEXTS)),
)
PLANTED_FORCED_PAGES = (
    Page(
        PLANTED_ID,
        PLANTED_WIDTH,
        PLANTED_HEIGHT,
        _scene_texts({**PLANTED_TEXTS, **FORCED_TEXTS}),
    ),
    PLANTED_PAGES[1],
)

#: The kinds of finding of the four reads, beside the causes of `dropped`.
WORDS = "words"
NO_FACE = "no face"
MACHINE_FONT = "font of the machine"
REFUSED = "refused"

#: What the ink read names of the text left to forcing where the forced palette did not reach
#: the text.
FORCED_FINDINGS = frozenset(
    (NO_INK, FORCED_TEXT, span.text) for line in FORCED_TEXTS[FORCED_TEXT] for span in line
)

#: What the font read names of the span with the character the face lacks, and what a stop
#: adds where it does not.
LACKED_FINDING = (MACHINE_FONT, "character-the-face-lacks", f"lacks {LACKED}")
NO_FONT_HOLDS = (
    f"Where no font of the machine holds {LACKED}, the browser draws it in the file's own face, "
    "as a box"
)

#: What the four reads must name of the planted file, in `_named`'s form, and nothing else.
#: The edge control, the text under a translucent fill, the text over another and the text in
#: the colour of its ground are left unnamed (DEC-037 point 5).
PLANTED_FINDINGS = frozenset(
    {
        (WORDS, "run-swallowed"),
        (WORDS, SPAN_TAKEN_OUT),
        (NO_INK, "no-paint-alone", "alone"),
        (NO_INK, "no-paint-between", "between"),
        (NO_INK, "no-paint-beside", "beside"),
        (NO_INK, "no-paint-marked", "marked"),
        (OFF_THE_PAGE, "off-the-page", "away"),
        (CUT, CUT_PAST_THE_TOP, "Cut off"),
        (COVERED, UNDER_A_BOX, "covered"),
        (COVERED, UNDER_ANOTHER, "beneath"),
        (COVERED, HACEK, "ž"),
        (COVERED, RAISED, "raised"),
        (NO_FACE, "face-left-out", LEFT_OUT, "400"),
        (NO_FACE, "face-broken", BROKEN, "400"),
        (NO_FACE, "weight-with-no-face", HELD, "700"),
        (MACHINE_FONT, "face-left-out", "left out"),
        (MACHINE_FONT, "face-broken", "broken"),
        LACKED_FINDING,
        (REFUSED, Path(NETWORK).name),
        (REFUSED, BESIDE),
    }
)


def _first_read(
    started: _Started, place: Path, signals: Mapping[str, Sequence[str]], *, forced: bool = False
) -> None:
    """Read the planted file. Raises Stopped where setting a signal of `signals` does not
    repaint its mode box, and where the reads do not name each fault, with the font that drew
    each span of the machine's, or name what is clean. Where the character the face lacks is
    not named, the stop says what a machine with no font for it does. The plants set in device
    pixels take the start's scale, and the width the window draws the first page at.
    In a start that `forced` its colours, every emulation sets `FORCED`, and the reads run in
    each forced palette (`_forced_read`)."""
    file = place / (PLANTED_FORCED_FILE if forced else PLANTED_FILE)
    device = started.scale * min(PLANTED_WIDTH, started.window) / PLANTED_WIDTH
    try:
        written = _planted_html(PLANTED_FACE.read_bytes(), signals, forced=forced, device=device)
        file.write_text(written, encoding="utf-8")
    except OSError as exc:
        raise started.stop(f"the first read has no page to read: {exc}") from exc
    pages = PLANTED_FORCED_PAGES if forced else PLANTED_PAGES
    found = _opened(started, file, pages)
    _repaints(started, found[0], signals, FORCED if forced else {})
    if not forced:
        _names_the_plants(started, _named(_read(started, pages, found)))
        return
    for palette in PALETTES:
        _forced_read(started, pages, found, palette)


def _forced_read(
    started: _Started, pages: Sequence[Page], found: Sequence[Mapping[str, Any]], palette: Palette
) -> None:
    """The planted file read in the forced palette `palette`. Raises Stopped where its ground is
    not lighter than its text in a light palette, or not darker in a dark one, where a line of
    the text left to forcing shows no ink or is named otherwise, and where the reads do not
    name each fault, or name what is clean (DEC-027 point 4, DEC-039 point 5)."""
    where = f"the forced palette `{palette.name}`"
    started.emulate({**palette.signals, **FORCED})
    colours = started.ask(COLOURS, GROUND_MARK, FORCED_SELECTOR)
    ground, text = _luminance(colours["ground"]), _luminance(colours["text"])
    if not (ground > text if palette.light else ground < text):
        than = "lighter" if palette.light else "darker"
        raise started.stop(
            f"the first read set {where}, and the browser gave it a ground of "
            f"{colours['ground']}, not {than} than its text of {colours['text']}, so its "
            f"images would show what their name denies"
        )
    named = _named(_read(started, pages, found))
    if named & FORCED_FINDINGS:
        raise started.stop(
            f"the first read set {where}, and a span with no paint, left to forcing, left no "
            f"ink, so the forced palette did not reach the text"
        )
    held = sorted(each for each in named if each[1] == FORCED_TEXT)
    if held:
        raise started.stop(
            f"the first read set {where}, and named {_listed(held)}, of the text with no paint "
            f"left to forcing, so a ground or a backplate covers its lines"
        )
    _names_the_plants(started, named, f" in {where}")
    started.ask(UNGROUND, READ_STYLES, READ_MARKS)


def _names_the_plants(started: _Started, named: set[tuple[str, ...]], where: str = "") -> None:
    """Raise Stopped where `named`, what the reads named of the planted file `where`, is not
    each planted fault and nothing else."""
    unnamed, wrong = PLANTED_FINDINGS - named, named - PLANTED_FINDINGS
    if unnamed or wrong:
        said = [f"did not name {_listed(unnamed)}" if unnamed else ""]
        said += [f"named {_listed(wrong)}, which the page does not plant" if wrong else ""]
        why = f". {NO_FONT_HOLDS}" if LACKED_FINDING in unnamed else ""
        raise started.stop(
            f"the first read{where} {' and '.join(each for each in said if each)}{why}"
        )


#: The colours a forced palette gives the planted file: the ground of the box it forces, and
#: the colour of the span with no paint left to forcing, as the browser computes them.
COLOURS = """(ground, text) => ({
  ground: getComputedStyle(document.querySelector(`[${ground}]`)).backgroundColor,
  text: getComputedStyle(document.querySelector(text)).color,
})"""

#: The span left to forcing, as a selector of the document.
FORCED_SELECTOR = f'[{MARKS["text"]}="{FORCED_TEXT}"] [{MARKS["span"]}]'

#: A colour as the browser computes it: its first three numbers are its channels.
RGB = re.compile(r"rgba?\(\s*([\d.]+)[\s,]+([\d.]+)[\s,]+([\d.]+)")


def _luminance(colour: str) -> float:
    """The relative luminance of `colour`, as the browser computes it, from 0 for black to 1 for
    white. Raises ValueError for a colour of another form."""
    found = RGB.match(colour)
    if found is None:
        raise ValueError(f"a colour of another form: {colour!r}")
    linear = [
        share / 12.92 if share <= 0.04045 else ((share + 0.055) / 1.055) ** 2.4
        for share in (float(channel) / 255 for channel in found.groups())
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _repaints(
    started: _Started,
    page: Mapping[str, Any],
    signals: Mapping[str, Sequence[str]],
    also: Mapping[str, str],
) -> None:
    """Raise Stopped where setting a signal to a value after its first does not repaint its own
    mode box of the planted file's first page, every other signal at its first value. Each
    emulation sets `also` too. A change of scheme repaints the whole page under forced colours,
    so each signal is judged by its own box. The page's own reads then run with every signal at
    its first value."""
    if not signals:
        return
    first = {**{signal: values[0] for signal, values in signals.items()}, **also}
    boxes = [_mode_box(page, index) for index in range(len(signals))]
    started.emulate(first)
    before = [started.picture(box) for box in boxes]
    for (feature, values), box, held in zip(sorted(signals.items()), boxes, before, strict=True):
        for value in values[1:]:
            started.emulate({**first, feature: value})
            if started.picture(box) == held:
                raise started.stop(
                    f"the first read set `{feature}: {value}`, and the page did not repaint, so "
                    f"the keys that signal parts would read as one"
                )
    started.emulate(first)


def _named(read: Read) -> set[tuple[str, ...]]:
    """What a read named, each finding as `PLANTED_FINDINGS` writes it. A font of the machine
    counts only with its name."""
    return {
        *((WORDS, each.element) for each in read.words),
        *((each.why, each.element, each.text) for each in read.dropped),
        *((NO_FACE, each.element, each.family, each.weight) for each in read.no_face),
        *(
            (MACHINE_FONT, each.element, each.text)
            for each in read.machine_fonts
            if all(each.fonts)
        ),
        *((REFUSED, url.rsplit("/", 1)[-1]) for url in read.refused),
    }


def _listed(findings: Collection[tuple[str, ...]]) -> str:
    return "; ".join(" ".join(each) for each in sorted(findings))


#: Where the planted file's modes lie: a box for each signal, in a row below its first page's
#: texts. The box a forced palette paints in its ground ends that row, marked `GROUND_MARK`.
MODE_TOP = 760
MODE_SIZE = 24
GROUND_MARK = "data-pkit-ground"
GROUND_LEFT = PLANTED_WIDTH - 8 - MODE_SIZE

#: The colour of a mode's box under the first value of its signal, and under each other.
MODE_COLOURS = ("#ffffff", "#000000")

#: The colour the box `GROUND_MARK` marks is painted, which a forced palette gives its ground.
GROUND_COLOUR = "#808080"

#: What keeps an element of the planted file out of forcing.
KEPT_OUT = "forced-color-adjust:none"


def _mode_left(index: int) -> int:
    """Where the box of the signal of `index` lies from the left of the planted file's first
    page, in its px."""
    return 8 + index * MODE_SIZE * 2


def _mode_box(page: Mapping[str, Any], index: int) -> dict[str, float]:
    """The clip of the box of the signal of `index`, on the planted file's first page `page` as
    the document holds it, whose lengths are shares of its width."""
    unit = page["width"] / PLANTED_WIDTH
    return {
        "x": page["x"] + _mode_left(index) * unit,
        "y": page["y"] + MODE_TOP * unit,
        "width": MODE_SIZE * unit,
        "height": MODE_SIZE * unit,
    }


def _planted_modes(signals: Mapping[str, Sequence[str]], forced: bool = False) -> tuple[str, str]:
    """The planted file's modes: their rules, and a box for each signal the file reads, painted
    by a custom property each of its values after the first sets otherwise. Where `forced`,
    each box is kept out of forcing, so it repaints by its own signal alone."""
    rules, boxes = [], []
    plain = []
    for index, (feature, values) in enumerate(sorted(signals.items())):
        name = f"--pkit-mode-{index}"
        plain.append(f"{name}:{MODE_COLOURS[0]}")
        rules.extend(
            f"@media ({feature}:{value}){{:root{{{name}:{MODE_COLOURS[1]}}}}}"
            for value in values[1:]
        )
        place = (
            f"position:absolute;left:{_share(_mode_left(index))};top:{_share(MODE_TOP)};"
            f"width:{_share(MODE_SIZE)};height:{_share(MODE_SIZE)};background:var({name})"
        )
        boxes.append(f'<div style="{place}{";" + KEPT_OUT if forced else ""}"></div>')
    sheet = f":root{{{';'.join(plain)}}}{''.join(rules)}" if plain else ""
    return sheet, "".join(boxes)


def _planted_forced() -> tuple[str, str]:
    """What a start that forces its colours adds to the planted file: the renderer's rules for
    a layer's box opaque in every key under forced colours, its fill in the reader's text
    colour under its inset shape, as the declaration names them, since the browser forces no
    colour a shape's attribute holds; what every file of the renderer holds under forced
    colours; and the box it paints in its ground (DEC-039 point 4)."""
    held = f'[{MARKS["layer"]}] rect[fill="{BOX}"]'
    sheet = (
        f"@media (forced-colors:active){{{held}{{fill:{FORCED_COLOURS['opaque-fills']}}}"
        f"{held}:not([stroke]){{fill:{FORCED_COLOURS['edge']['colour']}}}"
        f"{PLANTED_FORCED_SHEET}}}"
    )
    place = (
        f"position:absolute;left:{_share(GROUND_LEFT)};top:{_share(MODE_TOP)};"
        f"width:{_share(MODE_SIZE)};height:{_share(MODE_SIZE)};background:{GROUND_COLOUR}"
    )
    return sheet, f'<div {GROUND_MARK} style="{place}"></div>'


@dataclass(frozen=True)
class _Laid:
    """A text of the planted file where it lies: its trace id and its lines, the baseline of
    its first line, its size and how far apart its lines lie, in px of its page."""

    element: str
    lines: tuple[tuple[_Planted, ...], ...]
    baseline: float
    size: float = SIZE
    step: float = ROW


@dataclass(frozen=True)
class _Layer:
    """A layer of the planted file: each box it draws, a left, a top, a width, a height and a
    fill, in px of its page, and its z-index, None for none."""

    boxes: tuple[tuple[float, float, float, float, str], ...]
    z: int | None = None


def _over(baseline: float, size: float, fill: str = BOX) -> tuple[float, float, float, float, str]:
    """A box over the line of `size` whose baseline lies at `baseline`, as wide as the page,
    from the face's ascent to its descent, so it meets no other line."""
    top = baseline - ASCENT * size
    return 0.0, top, float(PLANTED_WIDTH), (ASCENT + DESCENT) * size, fill


def _first_page(device: float, forced: bool) -> list[_Laid | _Layer]:
    """The planted file's first page, in the tree's order, its plants set in device pixels at
    `device` device pixels to its px; where `forced`, with the text left to forcing."""
    drawn: list[_Laid | _Layer] = [
        _Laid(CUT_PAST_THE_TOP, PLANTED_TEXTS[CUT_PAST_THE_TOP], CUT_BASELINE)
    ]
    row = 0
    for element in ROWED:
        lines = PLANTED_TEXTS[element]
        if element != OVER_ANOTHER:
            row += 1
        baseline = (row + 1) * ROW
        drawn.append(_Laid(element, lines, baseline))
        if element == UNDER_A_BOX:
            drawn.append(_Layer((_over(baseline, SIZE),)))
        elif element == UNDER_A_TRANSLUCENT_FILL:
            drawn.append(_Layer((_over(baseline, SIZE, TRANSLUCENT),)))
        elif element == UNDER_ANOTHER:
            # A part between the two texts, which meets neither, so they lie in two runs.
            drawn.append(_Layer(((PLANTED_WIDTH - 40, baseline - SIZE, 16, 6, BOX),)))
        row += len(lines) - 1
    hacek, control = TEXT_FLOOR / device, CONTROL_EM / device
    over_the_hacek = HACEK_BASELINE - ASCENT * hacek
    drawn += [
        _Laid(HACEK, PLANTED_TEXTS[HACEK], HACEK_BASELINE, hacek),
        _Layer(
            (
                (
                    0.0,
                    over_the_hacek,
                    float(PLANTED_WIDTH),
                    HACEK_BASELINE - UNDER_THE_HACEK * hacek - over_the_hacek,
                    BOX,
                ),
            )
        ),
        _Laid(EDGE_CONTROL, PLANTED_TEXTS[EDGE_CONTROL], CONTROL_BASELINE, control),
        _Layer(((0.0, CONTROL_BASELINE + FOOT * control, float(PLANTED_WIDTH), control / 2, BOX),)),
    ]
    if forced:
        drawn += [_Laid(FORCED_TEXT, FORCED_TEXTS[FORCED_TEXT], FORCED_BASELINE, step=FORCED_STEP)]
    return drawn


def _raised_page() -> list[_Laid | _Layer]:
    """The planted file's page of its own: a layer earlier in the document, raised over the
    text after it by z-index (DEC-037 point 5)."""
    baseline = ROW
    return [_Layer((_over(baseline, SIZE),), z=1), _Laid(RAISED, RAISED_TEXTS[RAISED], baseline)]


def _planted_html(
    face: bytes,
    signals: Mapping[str, Sequence[str]] | None = None,
    *,
    forced: bool = False,
    device: float = 1.0,
) -> str:
    """The planted file, written as the renderer writes a file: its pages, each text in the
    tree's order, the grounds of each run of texts before its first, with a mode for each of
    `signals` on its first page. Its plants set in device pixels take `device` device pixels
    to a px of the page. Where `forced`, it holds what a start that forces its colours reads
    too: `FORCED_TEXTS`, and `_planted_forced`'s."""
    data = base64.b64encode(face).decode("ascii")
    faces = (
        f"@font-face{{font-family:{HELD};font-weight:400;"
        f"src:url(data:font/otf;base64,{data}) format('opentype')}}"
        f"@font-face{{font-family:{BROKEN};font-weight:400;"
        "src:url(data:font/otf;base64,AAAA) format('opentype')}"
    )
    modes, boxes = _planted_modes(signals or {}, forced)
    more, ground = _planted_forced() if forced else ("", "")
    requests = f'<img src="{NETWORK}" alt=""/><img src="{BESIDE}" alt=""/>'
    first = _planted_page(
        PLANTED_ID, PLANTED_HEIGHT, _first_page(device, forced), forced, boxes + ground + requests
    )
    raised = _planted_page(RAISED_ID, RAISED_HEIGHT, _raised_page(), forced)
    return (
        '<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="utf-8"/>\n'
        f"<title>planted</title>\n<style>{faces}{modes}{PLANTED_SHEET}{more}</style>\n</head>\n"
        f"<body>{first}{raised}</body>\n</html>\n"
    )


def _planted_page(
    trace: str, height: int, drawn: Sequence[_Laid | _Layer], forced: bool, after: str = ""
) -> str:
    """A page of the planted file: each of `drawn` in order, the grounds of each run of texts
    before its first text, a layer ending a run (DEC-039 point 1), then `after`."""
    size = f"width:min(100%,{PLANTED_WIDTH}px);aspect-ratio:{PLANTED_WIDTH}/{height}"
    written: list[str] = []
    grounds: list[str] = []
    texts: list[str] = []
    for index, each in enumerate(drawn):
        if isinstance(each, _Layer):
            written += [*grounds, *texts, _planted_layer(trace, index, height, each)]
            grounds, texts = [], []
        else:
            grounds.append(_planted_grounds(each))
            texts.append(_planted_text(each, forced))
    written += [*grounds, *texts]
    return f'<div {MARKS["page"]}="{trace}" style="{size}">{"".join(written)}{after}</div>'


def _planted_text(laid: _Laid, forced: bool) -> str:
    """A text of the planted file at its place, each line opened by its strut."""
    left, top = _share(laid.lines[0][0].left), _share(laid.baseline - ROW)
    place = f"left:{left};top:{top};width:{_share(TEXT_WIDTH)}"
    drawn = "".join(
        _planted_line(line, index * laid.step, laid.size, forced)
        for index, line in enumerate(laid.lines)
    )
    return f'<div {MARKS["text"]}="{laid.element}" style="{place}">{drawn}</div>'


def _planted_grounds(laid: _Laid) -> str:
    """The ground of each line of a planted text, which shows under forced colours alone: as
    wide as its frame, widened by the declared margin at each end, and from the face's ascent
    to its descent at its size, and a sign's square (DEC-039 points 1 and 2)."""
    grounds = []
    for index, line in enumerate(laid.lines):
        baseline = laid.baseline + index * laid.step
        high = baseline - ASCENT * laid.size
        if any(span.marked for span in line):
            high = min(high, baseline - SIZE)
        place = (
            f"left:{_share(line[0].left - MARGIN)};top:{_share(high)};"
            f"width:{_share(TEXT_WIDTH + 2 * MARGIN)};"
            f"height:{_share(baseline + DESCENT * laid.size - high)}"
        )
        grounds.append(f'<div {MARKS["ground"]}="{laid.element}" style="{place}"></div>')
    return "".join(grounds)


def _share(length: float) -> str:
    """A length in px of the planted file's pages, as a share of their width."""
    return f"{length / PLANTED_WIDTH * 100:.5f}cqw"


def _planted_line(spans: Sequence[_Planted], top: float, size: float, forced: bool = False) -> str:
    """A line `top` below its text's first line, opened by its strut, its spans at `size`.
    Where `forced`, a span with no paint is kept out of forcing, but for one left to it."""

    def style(span: _Planted) -> str:
        kept = forced and span.colour == UNPAINTED and not span.forced
        ground = (
            f";background:#000000;padding:0 {_share(2)}" if span.marked or span.grounded else ""
        )
        return (
            f"font-family:{span.family};font-size:{_share(size)};font-weight:{span.weight};"
            f"color:{span.colour}{ground}{';' + KEPT_OUT if kept else ''}"
        )

    def sign(span: _Planted) -> str:
        if not span.marked:
            return ""
        square = _share(SIZE)
        return (
            f'<svg {MARKS["sign"]}="" viewBox="0 0 14 14" aria-hidden="true" '
            f'style="width:{square};height:{square};margin-right:{_share(4)}">'
            '<path d="M 0 0 L 14 0 L 14 14 L 0 14 Z" fill="#808080"/></svg>'
        )

    drawn = "".join(
        f'<span {MARKS["span"]} style="{style(span)}">{sign(span)}{span.text}</span>'
        for span in spans
    )
    place = f"top:{_share(top + ROW - STRUT)}"
    strut = f'<span {MARKS["strut"]} style="height:{_share(STRUT)}"></span>'
    return f'<div {MARKS["line"]} style="{place}">{strut}{drawn}</div>'


def _planted_layer(trace: str, index: int, height: int, layer: _Layer) -> str:
    """A layer of the planted file, each box a part with its own id. A box opaque in every key
    and more than twice the edge's width thick takes the inset shape the renderer gives it,
    which shows under forced colours alone (DEC-039 point 4)."""
    shapes = []
    for number, (x, y, width, height_of, fill) in enumerate(layer.boxes):
        shapes.append(
            f'<rect data-id="{trace}/box-{index}-{number}" x="{x:.4f}" y="{y:.4f}" '
            f'width="{width:.4f}" height="{height_of:.4f}" fill="{fill}"/>'
        )
        if fill == BOX and min(width, height_of) > 2 * EDGE:
            shapes.append(
                f'<rect data-inset="" x="{x + EDGE:.4f}" y="{y + EDGE:.4f}" '
                f'width="{width - 2 * EDGE:.4f}" height="{height_of - 2 * EDGE:.4f}"/>'
            )
    raised = f' style="z-index:{layer.z}"' if layer.z is not None else ""
    return (
        f'<svg {MARKS["layer"]}="" viewBox="0 0 {PLANTED_WIDTH} {height}"{raised}>'
        f"{''.join(shapes)}</svg>"
    )
