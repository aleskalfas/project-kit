#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "playwright==1.64.1",
# ]
# ///
"""Draw what a real browser shows of an HTML file, as one image in a folder.

A builder's tool of project-kit's own (PRJ-012 point 2). It lets whoever builds the HTML page
see the page as a reader's browser shows it. It reads a file the capability wrote and draws no
piece. It ships to no project, joins no check, and nothing compares its image, which may change
with the browser (visual-communication DEC-015 point 6).

- **The browser.** The machine's Chrome, headless, driven through Playwright. No browser is
  fetched. Playwright is this script's dependency alone, pinned in the header above, so it runs
  as a program of its own. The module imports with no Playwright.
- **One page of several.** `--selector` names the page's element, and it must name one. A style
  added from outside makes everything else transparent, so the file stays as it is and needs
  no hook. A page's arrows and gradients may rest on an id another page defines, and
  `display: none` or `visibility: hidden` on that other page would drop them. A second style
  moves the page to the document's corner, by paint alone, and the image is cut from there. So
  a document's own margins change neither where the page falls nor how its text is smoothed.
- **The size.** `--size` is the image's, in pixels. The page takes the device scale that gives
  its long edge that many pixels. That scale is known only once the page is laid out, so the
  browser opens twice: to measure, then to draw. The image is cut to the size named, not to
  the browser's rounding of a fractional height. A size further from the page's own shape than
  the viewing step rounds is refused, since a cropped page would also be exactly that size.
- **No selector.** The document as a window of that size shows it, at a device scale of 1.
- **Fonts.** Every face of the file is asked to load, and the run waits for them. It prints each
  face, and says whether it loaded.
- **A mode.** `--attribute` sets an attribute on the document's root, and on the element
  `--selector` names, before it draws. `--colour-scheme` sets what the page reads as the
  reader's preference. Neither changes the file.
- **The network.** Every request outside the file is refused, and printed as it is refused: the
  web, a web socket, and another file on this machine. Only the file itself, `data:` and
  `blob:` go through. A refused request stops nothing, so a page that asks for a picture
  from outside still draws, without it. A refused socket stays open in the page, with no
  server behind it.
- **What it leaves.** The browser runs on a throwaway profile, inside the folder, which the run
  removes. Chrome's crash database takes no notice of the profile, and would be the machine's
  own, so `BREAKPAD_DUMP_LOCATION` moves it into the profile too. Chrome clones its own app for
  each launch, under the system's folders, and removes the clone as it closes, so a browser
  killed outright leaves its clone there. The image is written last, so a run that stops
  writes none.

From the repository root:

    scripts/browser_look.py deck.html --size 1568x882 --folder out --selector "#page-2"

Exit codes:
  0  drawn: the image's path is printed last
  1  stopped: no browser was found, the browser died or did not answer, the file or the
     selector gave nothing to draw, or the size does not fit. It says which, and writes no image
  2  the arguments do not read
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import struct
import sys
import tempfile
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

#: Where a Mac keeps Chrome, and the names Chrome and Chromium go by on a path.
MAC_CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
CHROME_NAMES = ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser")

#: How long the browser has for each step, and the file's fonts to load, in milliseconds.
STEP_LIMIT = 30_000
FONT_LIMIT = 10_000

_SIZE = re.compile(r"^([1-9][0-9]*)x([1-9][0-9]*)$")

#: Every element the selector names, and the box of the one it must name, in the document.
_MEASURE = """selector => {
  let found;
  try { found = document.querySelectorAll(selector); } catch { return {count: null}; }
  if (found.length !== 1) return {count: found.length};
  const box = found[0].getBoundingClientRect();
  return {count: 1, x: box.x + scrollX, y: box.y + scrollY, width: box.width, height: box.height};
}"""

#: Sets each attribute on the document's root, and on the element the selector names.
_SET_ATTRIBUTES = """([selector, attributes]) => {
  const roots = [document.documentElement];
  if (selector) roots.push(document.querySelector(selector));
  for (const root of roots)
    for (const [name, value] of attributes) root.setAttribute(name, value);
}"""

#: Loads every face of the file, within the limit, and reads what became of each.
_LOAD_FACES = """async limit => {
  const faces = [...document.fonts];
  const loaded = Promise.allSettled(faces.map(face => face.load()));
  await Promise.race([loaded, new Promise(done => setTimeout(done, limit))]);
  return faces.map(face => ({
    family: face.family, weight: face.weight, style: face.style, status: face.status,
  }));
}"""


class Stop(Exception):
    """The run cannot draw. The message says which of the reasons it was."""


@dataclass(frozen=True)
class Size:
    """A width and a height in pixels."""

    width: int
    height: int

    def __str__(self) -> str:
        return f"{self.width}x{self.height}"


@dataclass(frozen=True)
class Box:
    """An element's box in the document, in the page's own units."""

    x: float
    y: float
    width: float
    height: float


@dataclass(frozen=True)
class Request:
    """What one run is asked to draw."""

    file: Path
    folder: Path
    size: Size
    browser: Path
    selector: str | None = None
    attributes: tuple[tuple[str, str], ...] = ()
    colour_scheme: str | None = None


def size_argument(text: str) -> Size:
    """`1568x882` as a `Size`."""
    match = _SIZE.match(text)
    if match is None:
        raise argparse.ArgumentTypeError(f"{text!r} is no size: write WIDTHxHEIGHT, as 1568x882")
    return Size(int(match[1]), int(match[2]))


def attribute_argument(text: str) -> tuple[str, str]:
    """`name=value` as a pair."""
    name, equals, value = text.partition("=")
    if not name or not equals:
        raise argparse.ArgumentTypeError(f"{text!r} is no attribute: write NAME=VALUE")
    return name, value


def parser() -> argparse.ArgumentParser:
    """The script's arguments."""
    result = argparse.ArgumentParser(
        description="Draw a page of an HTML file in the machine's headless Chrome, as an image.",
    )
    result.add_argument("file", type=Path, help="the HTML file")
    result.add_argument(
        "--size",
        type=size_argument,
        required=True,
        help="the image's size in pixels, as 1568x882: with no selector, the window's",
    )
    result.add_argument(
        "--folder", type=Path, required=True, help="where the image goes, as <file's name>.png"
    )
    result.add_argument(
        "--selector", help="the CSS selector of one page: left out, the window is drawn"
    )
    result.add_argument(
        "--attribute",
        type=attribute_argument,
        action="append",
        default=[],
        metavar="NAME=VALUE",
        help="an attribute for the page's root, set before drawing; give it once for each",
    )
    result.add_argument(
        "--colour-scheme",
        choices=("light", "dark"),
        help="the reader's preference the page reads: by default light",
    )
    result.add_argument(
        "--browser", type=Path, help="the browser's program: by default, the machine's Chrome"
    )
    return result


def find_browser(named: Path | None) -> Path:
    """The browser's program: the one named, else the machine's Chrome. Stops where none is."""
    if named is not None:
        if named.is_file() and os.access(named, os.X_OK):
            return named
        raise Stop(f"no browser found: {named} is no program")
    if os.access(MAC_CHROME, os.X_OK):
        return Path(MAC_CHROME)
    for name in CHROME_NAMES:
        found = shutil.which(name)
        if found is not None:
            return Path(found)
    raise Stop(
        f"no browser found: looked for {MAC_CHROME} and, on the path, "
        f"{', '.join(CHROME_NAMES)}. Name one with --browser"
    )


def outside_style(selector: str) -> str:
    """The style added from outside: all but the element `selector` names made transparent.

    It selects each element beside the page or beside an element that holds it. Inside `:is()`
    the selector is read against the whole document, so a selector that starts at an element
    above `:has()`'s own works too. The elements stay laid out and painted, so what another
    page defines, such as an arrow's marker, still draws here.

    The room after the document is for a last page the size names a pixel or two past its own
    end. Playwright trims a cut to the document.
    """
    page = f":is({selector})"
    return (
        f":has({page}) > :not(:has({page}), {page}) {{ opacity: 0 !important; }} "
        'html::after { content: ""; display: block; height: 8px; }'
    )


def moving_rule(selector: str, box: Box) -> str:
    """A style that moves the page from `box` to the document's corner, by paint alone.

    Chrome smooths a page's text by where it falls on the device's pixels. A page at 176.4 pixels
    would draw otherwise than the same page at 0, though nothing has moved inside it. The
    `translate` property adds to any transform the file sets, and moves nothing else.
    """
    return f":is({selector}) {{ translate: {-box.x}px {-box.y}px !important; }}"


def scale_of(box: Box, size: Size) -> float:
    """The device scale that gives the box's long edge `size`'s, or a stop where it cannot fit.

    The long edge decides, as the viewing step sizes an image by it. The step's tool rounds the
    other edge of the page to a whole number, scales it and rounds up, which a fit allows for.
    """
    scale = max(size.width, size.height) / max(box.width, box.height)
    allowed = scale / 2 + 1
    if max(abs(box.width * scale - size.width), abs(box.height * scale - size.height)) > allowed:
        raise Stop(
            f"the size does not fit the page: {size} asked, and the page is "
            f"{box.width}x{box.height}, so {box.width * scale:.1f}x{box.height * scale:.1f} there"
        )
    return scale


def image_size(png: bytes) -> Size:
    """The size a PNG's header gives."""
    width, height = struct.unpack(">II", png[16:24])
    return Size(width, height)


def _first_line(error: Exception) -> str:
    return str(error).strip().splitlines()[0]


def _refuser(own: str) -> tuple[Callable[[Any], None], Callable[[Any], None]]:
    """The handlers that refuse what is outside the file `own`, each named once in the run."""
    named: set[str] = set()

    def name(url: str) -> None:
        if url not in named:
            named.add(url)
            print(f"refused: {url}", flush=True)

    def request(route: Any) -> None:
        url = route.request.url
        if url.split("#")[0] == own or url.startswith(("data:", "blob:")):
            route.continue_()
        else:
            name(url)
            route.abort()

    def socket(route: Any) -> None:
        # A socket routed and never connected reaches no server. Closing it from this handler
        # hangs the run: with Playwright 1.64.1, even `goto`'s own timeout no longer fires.
        name(route.url)

    return request, socket


@dataclass(frozen=True)
class _Run:
    """What each opening of the file in one run shares."""

    playwright: Any
    request: Request
    profile: str
    refuse: tuple[Callable[[Any], None], Callable[[Any], None]]


@contextmanager
def _opened(run: _Run, scale: float) -> Iterator[tuple[Any, list[dict[str, str]]]]:
    """The file open at `scale`, set as asked, with its fonts settled, and its faces."""
    request = run.request
    context = run.playwright.chromium.launch_persistent_context(
        run.profile,
        executable_path=str(request.browser),
        headless=True,
        args=["--disable-gpu"],
        env={**os.environ, "BREAKPAD_DUMP_LOCATION": run.profile},
        viewport={"width": request.size.width, "height": request.size.height},
        device_scale_factor=scale,
        color_scheme=request.colour_scheme,
        timeout=STEP_LIMIT,
    )
    try:
        context.set_default_timeout(STEP_LIMIT)
        refuse_request, refuse_socket = run.refuse
        context.route(re.compile(""), refuse_request)
        context.route_web_socket(re.compile(""), refuse_socket)
        page = context.pages[0] if context.pages else context.new_page()
        page.goto(request.file.as_uri(), wait_until="load")
        if request.selector is not None:
            _measured(page, request.selector)
        page.evaluate(_SET_ATTRIBUTES, [request.selector, list(request.attributes)])
        if request.selector is not None:
            page.add_style_tag(content=outside_style(request.selector))
        yield page, page.evaluate(_LOAD_FACES, FONT_LIMIT)
    finally:
        context.close()


def _measured(page: Any, selector: str) -> Box:
    """The box of the one element `selector` names, or a stop that says what it named."""
    found = page.evaluate(_MEASURE, selector)
    if found["count"] is None:
        raise Stop(f"the selector does not read: {selector}")
    if found["count"] != 1:
        raise Stop(f"the selector names {found['count']} elements, not one: {selector}")
    box = Box(found["x"], found["y"], found["width"], found["height"])
    if not box.width or not box.height:
        raise Stop(f"the selector names an element with no size: {selector}")
    return box


def _drawn(run: _Run) -> tuple[bytes, list[dict[str, str]]]:
    """The image and the file's faces, as `draw` gives them."""
    request = run.request
    if request.selector is None:
        with _opened(run, 1) as (page, faces):
            return page.screenshot(animations="disabled"), faces
    with _opened(run, 1) as (page, _):
        scale = scale_of(_measured(page, request.selector), request.size)
    with _opened(run, scale) as (page, faces):
        page.add_style_tag(content=moving_rule(request.selector, _measured(page, request.selector)))
        clip = {
            "x": 0,
            "y": 0,
            "width": request.size.width / scale,
            "height": request.size.height / scale,
        }
        return page.screenshot(clip=clip, full_page=True, animations="disabled"), faces


def draw(request: Request) -> tuple[bytes, list[dict[str, str]]]:
    """The image `request` asks for, and each face of the file with what became of it.

    Runs the browser on a throwaway profile in the request's folder, which it removes.
    """
    try:
        import playwright.sync_api as api  # pyright: ignore[reportMissingImports] only this file's header pins it
    except ImportError as error:
        raise Stop(f"no Playwright here: run the script itself, {__file__}") from error
    with tempfile.TemporaryDirectory(
        prefix="profile-", dir=request.folder, ignore_cleanup_errors=True
    ) as profile:
        try:
            with api.sync_playwright() as playwright:
                run = _Run(playwright, request, profile, _refuser(request.file.as_uri()))
                png, faces = _drawn(run)
        except api.TimeoutError as error:
            raise Stop(f"the browser did not answer: {_first_line(error)}") from error
        except api.Error as error:
            raise Stop(f"the browser died: {_first_line(error)}") from error
    if image_size(png) != request.size:
        raise Stop(f"the browser drew {image_size(png)}, not {request.size}")
    return png, faces


def look(arguments: argparse.Namespace) -> Path:
    """Draw as `arguments` ask, and give the image's path. Prints each face it reads."""
    browser = find_browser(arguments.browser)
    file = arguments.file.resolve()
    if not file.is_file():
        raise Stop(f"no such file: {arguments.file}")
    folder = arguments.folder.resolve()
    folder.mkdir(parents=True, exist_ok=True)
    png, faces = draw(
        Request(
            file=file,
            folder=folder,
            size=arguments.size,
            browser=browser,
            selector=arguments.selector,
            attributes=tuple(arguments.attribute),
            colour_scheme=arguments.colour_scheme,
        )
    )
    for face in faces:
        state = "loaded" if face["status"] == "loaded" else f"not loaded ({face['status']})"
        print(f"face {state}: {face['family']} {face['weight']} {face['style']}")
    image = folder / f"{file.stem}.png"
    image.write_bytes(png)
    return image


def main(argv: Sequence[str] | None = None) -> int:
    """Run the script. See the module's docstring for what it writes and its exit codes."""
    arguments = parser().parse_args(argv)
    try:
        image = look(arguments)
    except Stop as stop:
        print(f"stopped: {stop}", file=sys.stderr)
        return 1
    print(f"image: {image}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
