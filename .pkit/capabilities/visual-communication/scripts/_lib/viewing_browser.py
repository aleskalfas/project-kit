"""The viewing step's browser: a page file as images, and what the browser dropped
(visual-communication DEC-020 points 6 to 9, DEC-023 point 6, DEC-031 point 5, DEC-015 point 2,
DEC-024 points 1 and 4, DEC-027 points 2 to 4).

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
- **What it is not asked.** Over what lies over a text it asks nothing: a text under a later
  box, or in the colour of its ground, was drawn.
- **The first read.** Each start first reads a page of its own in the renderer's form,
  planted with one fault of each kind the four reads name, and with what they must leave
  unnamed. A read that names anything else stops the start, so a fault there shows as a stop,
  never as a clean report. The page also holds a mode for each signal the file reads, a box
  of its own, and the start stops where setting the signal does not repaint that box, since
  the keys that signal parts would read as one.
- **Under forced colours.** `draw_forced` draws a file in each of the browser's forced
  palettes (`PALETTES`), in a start of its own: the browser's flag forces its colours
  (`FORCING`), and every emulation sets `forced-colors: active` with the palette's signals.
  Under the flag, a page drawn without forced colours is no page a reader gets, so no start
  mixes the two. The emulation alone leaves text in the file's colours, so it never stands in
  for the flag. That start's first read keeps the planted page's mode boxes and its spans
  with no paint out of forcing, so its reads name each planted fault in each forced palette.
  It stops where one more span with no paint, left to forcing, shows no ink, since the forced
  palette did not reach the text, and where a forced palette's ground is not lighter than its
  text in the light one, and darker in the dark.
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
  a stop, with the planted page and what the browser said.

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

#: Why a span left nothing on the page.
NO_INK = "no ink"
OFF_THE_PAGE = "off the page"

#: How often a throwaway folder is tried, and the wait between: a helper of the browser may
#: outlive it by a moment, and write as it goes.
REMOVALS = 5
REMOVAL_WAIT = 0.2

#: What the throwaway folder holds beside the profile.
PROFILE = "profile"
SAID = "said.txt"
PLANTED_FILE = "planted.html"

#: The document's pages, each with its place and its texts, once its faces have settled. Each
#: span holds its place in the document, for the calls that name a span by it.
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
    };
  };
  return within(document, marks.page).map((page) => ({
    ...box(page),
    id: page.getAttribute(marks.page),
    texts: within(page, marks.text).map((text) => ({
      id: text.getAttribute(marks.text),
      lines: within(text, marks.line).map((line) => within(line, marks.span).map(read)),
    })),
  }));
}"""

#: The document as the ink read sees it: the layers hidden, on one ground, and of the spans
#: only the one that carries `ALONE_MARK`, which keeps its own paint.
GROUND = """(marks, ground, alone) => {
  const style = document.getElementById(alone) || document.createElement('style');
  style.id = alone;
  style.textContent = `
    [${marks.layer}], [${marks.span}]:not([${alone}]) {visibility: hidden !important}
    html, body, [${marks.page}] {background: ${ground} !important}`;
  document.head.append(style);
}"""

#: One span marked to show, or not, by its place in the document.
ALONE = """(mark, index, alone, shown) => {
  document.querySelectorAll(`[${mark}]`)[index].toggleAttribute(alone, shown);
}"""

#: The attribute that marks the span drawn alone, and the id of the style that does so.
ALONE_MARK = "data-pkit-alone"

#: The document as the file stands again, once the ink read is done: its style taken out.
UNGROUND = """(alone) => {
  const style = document.getElementById(alone);
  if (style) style.remove();
}"""

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
    """A span that left nothing, and why: `NO_INK` or `OFF_THE_PAGE`."""

    page: str
    element: str
    text: str
    why: str


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
            started.ask(UNGROUND, ALONE_MARK)
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
    """Each span that left nothing on its page. What one ground showed the next need not."""
    waiting = []
    for page, element, span in _spans(found):
        if span["text"].strip():
            if _outside(span, page):
                yield Dropped(page["id"], element, span["text"], OFF_THE_PAGE)
            else:
                waiting.append((page, element, span))
    for ground in GROUNDS:
        started.ask(GROUND, MARKS, ground, ALONE_MARK)
        blanks: dict[tuple[float, ...], bytes] = {}
        waiting = [each for each in waiting if not _left_ink(started, each[0], each[2], blanks)]
    for page, element, span in waiting:
        yield Dropped(page["id"], element, span["text"], NO_INK)


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
) -> bool:
    """Whether `span` alone changes the band of its page around it. Each band is compared with
    itself empty, since a clip's pixels depend on where it lies."""
    band = _band(span, page)
    key = tuple(band.values())
    if key not in blanks:
        blanks[key] = started.picture(band)
    started.ask(ALONE, MARKS["span"], span["index"], ALONE_MARK, True)
    picture = started.picture(band)
    started.ask(ALONE, MARKS["span"], span["index"], ALONE_MARK, False)
    return picture != blanks[key]


def _band(span: Mapping[str, Any], page: Mapping[str, Any]) -> dict[str, float]:
    """The band of `page` around `span`: the span's box and its height either way."""
    top = max(math.floor(span["y"] - span["height"]), math.floor(page["y"]))
    bottom = min(math.ceil(span["y"] + 2 * span["height"]), math.ceil(page["y"] + page["height"]))
    return {"x": page["x"], "y": top, "width": page["width"], "height": max(bottom - top, 1)}


class _Started:
    """A browser this module started, and the one tab it reads in."""

    def __init__(
        self, program: Path, place: Path, width: float, scale: float, *, forced: bool = False
    ) -> None:
        self.program = str(program)
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
            f"--window-size={math.ceil(width)},{WINDOW_HEIGHT}",
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


# The first read: a page of its own, in the renderer's form.

#: The planted page's size in px. Its lengths are shares of its width, so it fits any window.
PLANTED_WIDTH = 480
PLANTED_HEIGHT = 480

#: How far apart its lines lie, how high each one's strut is, and how wide a text's frame.
ROW = 24
STRUT = 32
TEXT_WIDTH = 464

#: The rules of the planted page, which a test holds to the renderer's.
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
    )
)

#: The planted page's trace id.
PLANTED_ID = "planted"

#: The face the page holds, which the capability ships, and the families it plants a fault in.
PLANTED_FACE = (
    Path(__file__).resolve().parents[2] / "libraries/neutral/fonts/SourceSansPro-Regular.otf"
)
HELD = "pkit-held"
LEFT_OUT = "pkit-left-out"
BROKEN = "pkit-broken"

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
    """A span of the planted page, with what it looks like. Under forced colours, a span with no
    paint is kept out of forcing unless it is `forced`."""

    text: str
    family: str = HELD
    weight: int = 400
    colour: str = "#000000"
    left: int = 8
    forced: bool = False


#: A span's paint where it has none, the text a later box lies over, and the text whose
#: document lacks a span of the scene's.
UNPAINTED = "transparent"
UNDER_A_BOX = "under-a-later-box"
SPAN_TAKEN_OUT = "span-taken-out"

#: Each text of the planted page, by a trace id that says what it holds, from the top down.
PLANTED_TEXTS: Mapping[str, tuple[tuple[_Planted, ...], ...]] = {
    "clean": ((_Planted("clean"),),),
    "no-paint-alone": ((_Planted("alone", colour=UNPAINTED),),),
    "no-paint-between": (
        (_Planted("above"),),
        (_Planted("between", colour=UNPAINTED),),
        (_Planted("below"),),
    ),
    "no-paint-beside": ((_Planted("painted "), _Planted("beside", colour=UNPAINTED)),),
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
}

#: A span the scene holds and the planted document does not.
TAKEN_OUT = "taken"

#: The text a start that forces its colours adds to the planted page, below the others: a span
#: with no paint, left to forcing, which shows ink only where the forced palette reached the
#: text (DEC-027 point 4).
FORCED_TEXT = "no-paint-forced"
FORCED_SPAN = "forced"
FORCED_TEXTS: Mapping[str, tuple[tuple[_Planted, ...], ...]] = {
    FORCED_TEXT: ((_Planted(FORCED_SPAN, colour=UNPAINTED, forced=True),),),
}

#: The file such a start writes the planted page to.
PLANTED_FORCED_FILE = "planted.forced.html"


def _scene_text(element: str, lines: Sequence[Sequence[_Planted]]) -> Text:
    """A text of the planted page as the scene holds it."""
    held = tuple(tuple(span.text for span in line) for line in lines)
    return Text(element, ((*held[0], TAKEN_OUT),) if element == SPAN_TAKEN_OUT else held)


#: The planted page as the scene holds it, and as it is under forced colours.
PLANTED_PAGE = Page(
    PLANTED_ID,
    PLANTED_WIDTH,
    PLANTED_HEIGHT,
    tuple(_scene_text(element, lines) for element, lines in PLANTED_TEXTS.items()),
)
PLANTED_FORCED_PAGE = Page(
    PLANTED_ID,
    PLANTED_WIDTH,
    PLANTED_HEIGHT,
    (
        *PLANTED_PAGE.texts,
        *(_scene_text(element, lines) for element, lines in FORCED_TEXTS.items()),
    ),
)

#: The kinds of finding of the four reads, beside `NO_INK` and `OFF_THE_PAGE`.
WORDS = "words"
NO_FACE = "no face"
MACHINE_FONT = "font of the machine"
REFUSED = "refused"

#: What the ink read names of the span left to forcing where the forced palette did not reach
#: the text.
FORCED_FINDING = (NO_INK, FORCED_TEXT, FORCED_SPAN)

#: What the font read names of the span with the character the face lacks, and what a stop
#: adds where it does not.
LACKED_FINDING = (MACHINE_FONT, "character-the-face-lacks", f"lacks {LACKED}")
NO_FONT_HOLDS = (
    f"Where no font of the machine holds {LACKED}, the browser draws it in the file's own face, "
    "as a box"
)

#: What the four reads must name of the planted page, in `_named`'s form, and nothing else.
PLANTED_FINDINGS = frozenset(
    {
        (WORDS, "run-swallowed"),
        (WORDS, SPAN_TAKEN_OUT),
        (NO_INK, "no-paint-alone", "alone"),
        (NO_INK, "no-paint-between", "between"),
        (NO_INK, "no-paint-beside", "beside"),
        (OFF_THE_PAGE, "off-the-page", "away"),
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
    """Read the planted page. Raises Stopped where setting a signal of `signals` does not
    repaint its mode box, and where the reads do not name each fault, with the font that drew
    each span of the machine's, or name what is clean. Where the character the face lacks is
    not named, the stop says what a machine with no font for it does.
    In a start that `forced` its colours, every emulation sets `FORCED`, and the reads run in
    each forced palette (`_forced_read`)."""
    file = place / (PLANTED_FORCED_FILE if forced else PLANTED_FILE)
    try:
        written = _planted_html(PLANTED_FACE.read_bytes(), signals, forced=forced)
        file.write_text(written, encoding="utf-8")
    except OSError as exc:
        raise started.stop(f"the first read has no page to read: {exc}") from exc
    pages = (PLANTED_FORCED_PAGE if forced else PLANTED_PAGE,)
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
    """The planted page read in the forced palette `palette`. Raises Stopped where its ground is
    not lighter than its text in a light palette, or not darker in a dark one, where the span
    left to forcing shows no ink, and where the reads do not name each fault, or name what is
    clean (DEC-027 point 4)."""
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
    if FORCED_FINDING in named:
        raise started.stop(
            f"the first read set {where}, and a span with no paint, left to forcing, left no "
            f"ink, so the forced palette did not reach the text"
        )
    _names_the_plants(started, named, f" in {where}")
    started.ask(UNGROUND, ALONE_MARK)


def _names_the_plants(started: _Started, named: set[tuple[str, ...]], where: str = "") -> None:
    """Raise Stopped where `named`, what the reads named of the planted page `where`, is not
    each planted fault and nothing else."""
    unnamed, wrong = PLANTED_FINDINGS - named, named - PLANTED_FINDINGS
    if unnamed or wrong:
        said = [f"did not name {_listed(unnamed)}" if unnamed else ""]
        said += [f"named {_listed(wrong)}, which the page does not plant" if wrong else ""]
        why = f". {NO_FONT_HOLDS}" if LACKED_FINDING in unnamed else ""
        raise started.stop(
            f"the first read{where} {' and '.join(each for each in said if each)}{why}"
        )


#: The colours a forced palette gives the planted page: the ground of the box it forces, and
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
    mode box of the planted page, every other signal at its first value. Each emulation sets
    `also` too. A change of scheme repaints the whole page under forced colours, so each signal
    is judged by its own box. The page's own reads then run with every signal at its first
    value."""
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


#: Where the planted page's modes lie: a box for each signal, in a row below its texts. The
#: box a forced palette paints in its ground ends that row, marked `GROUND_MARK`.
MODE_TOP = 440
MODE_SIZE = 24
GROUND_MARK = "data-pkit-ground"
GROUND_LEFT = PLANTED_WIDTH - 8 - MODE_SIZE

#: The colour of a mode's box under the first value of its signal, and under each other.
MODE_COLOURS = ("#ffffff", "#000000")

#: The colour the box `GROUND_MARK` marks is painted, which a forced palette gives its ground.
GROUND_COLOUR = "#808080"

#: What keeps an element of the planted page out of forcing.
KEPT_OUT = "forced-color-adjust:none"


def _mode_left(index: int) -> int:
    """Where the box of the signal of `index` lies from the planted page's left, in its px."""
    return 8 + index * MODE_SIZE * 2


def _mode_box(page: Mapping[str, Any], index: int) -> dict[str, float]:
    """The clip of the box of the signal of `index`, on the planted page `page` as the document
    holds it, whose lengths are shares of its width."""
    unit = page["width"] / PLANTED_WIDTH
    return {
        "x": page["x"] + _mode_left(index) * unit,
        "y": page["y"] + MODE_TOP * unit,
        "width": MODE_SIZE * unit,
        "height": MODE_SIZE * unit,
    }


def _planted_modes(signals: Mapping[str, Sequence[str]], forced: bool = False) -> tuple[str, str]:
    """The planted page's modes: their rules, and a box for each signal the file reads, painted
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
    """What a start that forces its colours adds to the planted page: the renderer's rule for a
    layer's opaque fill under forced colours, as the declaration names it, since the browser
    forces no colour a shape's attribute holds, and the box it paints in its ground."""
    forced = html_declaration.DECLARATION["forced-colours"]
    edge = forced["edge"]
    sheet = (
        f"@media (forced-colors:active){{[{MARKS['layer']}] rect{{fill:{forced['opaque-fills']};"
        f"stroke:{edge['colour']};stroke-width:{edge['width']}px}}}}"
    )
    place = (
        f"position:absolute;left:{_share(GROUND_LEFT)};top:{_share(MODE_TOP)};"
        f"width:{_share(MODE_SIZE)};height:{_share(MODE_SIZE)};background:{GROUND_COLOUR}"
    )
    return sheet, f'<div {GROUND_MARK} style="{place}"></div>'


def _planted_html(
    face: bytes, signals: Mapping[str, Sequence[str]] | None = None, *, forced: bool = False
) -> str:
    """The planted page, written as the renderer writes a page, each text in the tree's order,
    with a mode for each of `signals`. Where `forced`, it holds what a start that forces its
    colours reads too: `FORCED_TEXTS`, and `_planted_forced`'s."""
    data = base64.b64encode(face).decode("ascii")
    faces = (
        f"@font-face{{font-family:{HELD};font-weight:400;"
        f"src:url(data:font/otf;base64,{data}) format('opentype')}}"
        f"@font-face{{font-family:{BROKEN};font-weight:400;"
        "src:url(data:font/otf;base64,AAAA) format('opentype')}"
    )
    size = f"width:min(100%,{PLANTED_WIDTH}px);aspect-ratio:{PLANTED_WIDTH}/{PLANTED_HEIGHT}"
    written = []
    row = 0
    texts = {**PLANTED_TEXTS, **(FORCED_TEXTS if forced else {})}
    for element, lines in texts.items():
        row += 1
        left, top = _share(lines[0][0].left), _share(row * ROW)
        place = f"left:{left};top:{top};width:{_share(TEXT_WIDTH)}"
        drawn = "".join(
            _planted_line(line, index * ROW, forced) for index, line in enumerate(lines)
        )
        written.append(f'<div {MARKS["text"]}="{element}" style="{place}">{drawn}</div>')
        if element == UNDER_A_BOX:
            written.append(_planted_layer(row * ROW))
        row += len(lines) - 1
    modes, boxes = _planted_modes(signals or {}, forced)
    more, ground = _planted_forced() if forced else ("", "")
    return (
        '<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="utf-8"/>\n'
        f"<title>planted</title>\n<style>{faces}{modes}{PLANTED_SHEET}{more}</style>\n</head>\n"
        f'<body><div {MARKS["page"]}="{PLANTED_ID}" style="{size}">{"".join(written)}{boxes}'
        f'{ground}<img src="{NETWORK}" alt=""/><img src="{BESIDE}" alt=""/></div>'
        "</body>\n</html>\n"
    )


def _share(length: float) -> str:
    """A length in px of the planted page, as a share of its width."""
    return f"{length / PLANTED_WIDTH * 100:.5f}cqw"


def _planted_line(spans: Sequence[_Planted], top: int, forced: bool = False) -> str:
    """A line `top` below its text's top, opened by its strut. Where `forced`, a span with no
    paint is kept out of forcing, but for the one left to it."""

    def style(span: _Planted) -> str:
        kept = forced and span.colour == UNPAINTED and not span.forced
        return (
            f"font-family:{span.family};font-size:{_share(14)};font-weight:{span.weight};"
            f"color:{span.colour}{';' + KEPT_OUT if kept else ''}"
        )

    drawn = "".join(
        f'<span {MARKS["span"]} style="{style(span)}">{span.text}</span>' for span in spans
    )
    place = f"top:{_share(top + ROW - STRUT)}"
    strut = f'<span {MARKS["strut"]} style="height:{_share(STRUT)}"></span>'
    return f'<div {MARKS["line"]} style="{place}">{strut}{drawn}</div>'


def _planted_layer(top: int) -> str:
    """A layer whose one opaque box lies over the row at `top`."""
    return (
        f'<svg {MARKS["layer"]} viewBox="0 0 {PLANTED_WIDTH} {PLANTED_HEIGHT}">'
        f'<rect x="0" y="{top}" width="{PLANTED_WIDTH}" height="{ROW + 4}" fill="#808080"/></svg>'
    )
