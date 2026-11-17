"""The viewing step's tool: a renderer's drawn page as an image, and what the tool dropped
(visual-communication DEC-015 points 2 and 3).

This module alone calls the tool, resvg, through the pinned `resvg-py` wheel, as a library
in the command's own process. It reads the SVG renderer's pages. Reading them is how the
step works today, not what the step is, so nothing else of the step reads an SVG page.

- **The faces.** The tool ignores `@font-face`, so each face is taken out of the page's
  rules and handed over as a file, at the weight its rule names, in `folder`. The tool
  reads no font of the machine (DEC-004 point 9).
- **Family names.** Each family takes a name made here, in the faces and in the
  `font-family` the tool reads. The tool's parser keeps a CSS string's escapes in the name
  it looks up, so a brand's `&` or `"` would otherwise match no face, and its text would
  drop in silence. A rule and a text write one family as the same CSS string, so the
  names are joined on that string, undecoded.
- **Spans.** The tool shapes a chunk of text whole in each span's font, and keeps that
  span's part. Where the font lacks a character of the chunk, in any span, it turns to a
  face that holds it, and a face that holds the whole chunk replaces all of it. A page's
  faces hold only what they draw, so a strong span would mostly take the weight of the plain
  span beside it, or the reverse, and nothing says so. Each span is made a chunk of its own,
  so the tool shapes it alone, as the engine measured it (DEC-012 point 4).
- **What it dropped.** The tool returns only the image. It logs a family it could not
  match to the process's output, which names no run, and a text over a picture defeats a
  look for its ink in the image. So each span is drawn again alone: its line as the page
  sets it, the line's other spans unpainted, so nothing moves, on a band of the page around
  its baseline. A span whose band comes back as the same band empty left no ink. That
  holds whatever the cause: a font the tool could not match, no paint, a colour with no
  opacity, a line off the page. Over the page's other elements it asks nothing: a text
  under a later box, or in the colour of what lies beneath it, was drawn.
- **Regions.** The caller hands it the bands of a page too tall for one image, each a top
  and a height in the page's px, and it draws each as an image as wide as the page, at the
  one scale the caller gives (DEC-022 point 7). Handed none, it draws the page whole. What
  it dropped it reads on the whole page, once.
- **What it is not asked.** A page with no size, or an image past `MOST_PIXELS`, fails here.
  The tool's own failure at such a size takes the process down, which no caller can catch.
"""

from __future__ import annotations

import base64
import copy
import io
import math
import re
import struct
import xml.etree.ElementTree as ET
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import resvg_py
from fontTools.ttLib import TTFont

#: The tool and what it reaches the capability through, as a report names them.
TOOL = {"name": "resvg", "version": resvg_py.__resvg_version__, "wheel": resvg_py.__version__}

#: The ground of every image: a page that draws none of its own lies on it (DEC-015 point 5).
GROUND = "#ffffff"

#: How far from a baseline a span's ink is looked for, in its font sizes, either way. Ink
#: beyond it is reported dropped, which a reader can see is wrong; it is never missed.
BAND = 2

#: The most pixels an image takes, 512 MiB as the tool holds it. It draws so many in some two
#: seconds. Far past it the tool runs for minutes, then ends the process (`draw`).
MOST_PIXELS = 2**27

#: Where a PNG file's header gives the image's width and height.
PNG_SIZE = slice(16, 24)

SVG_NAMESPACE = "http://www.w3.org/2000/svg"
GROUP = f"{{{SVG_NAMESPACE}}}g"
STYLE = f"{{{SVG_NAMESPACE}}}style"
TEXT = f"{{{SVG_NAMESPACE}}}text"
SPAN = f"{{{SVG_NAMESPACE}}}tspan"

#: A CSS string as the canvas (`canvas.py`) writes one.
CSS_STRING = r'"(?:[^"\\]|\\.)*"'

#: An `@font-face` rule of the SVG renderer's.
FACE = re.compile(
    rf"@font-face\{{font-family:(?P<family>{CSS_STRING});font-weight:(?P<weight>\d+);"
    r"src:url\(data:font/\w+;base64,(?P<data>[A-Za-z0-9+/=]+)\)[^}]*\}"
)

#: A group's move, the only transform the SVG renderer writes.
MOVE = re.compile(r"translate\(([^,]+),([^)]+)\)")

#: The name records of a font that could name it otherwise than the family given it.
FONT_NAMES = (1, 2, 3, 4, 6, 16, 17, 21, 22)

#: How much of a line's width lies before the place an anchor holds it at.
ANCHORED = {"middle": 0.5, "end": 1.0}

ET.register_namespace("", SVG_NAMESPACE)


class ToolFailed(Exception):
    """The tool could not draw a page."""


@dataclass(frozen=True)
class Dropped:
    """What the tool drew nothing of in one text: its trace id, the characters, and whether
    they are the whole text or one span of it, the part of a run on one line."""

    element: str
    text: str
    whole: bool


@dataclass(frozen=True)
class Image:
    """A page drawn whole, or one of its bands: the PNG file's bytes, and its size in pixels."""

    image: bytes
    width: int
    height: int


@dataclass(frozen=True)
class Drawing:
    """A page drawn: an image of the whole page, or of each region handed, in order, and what
    the tool dropped on the page."""

    images: tuple[Image, ...]
    dropped: tuple[Dropped, ...]


def draw(
    svg: str,
    scale: float,
    folder: Path,
    widths: Mapping[str, Sequence[float]],
    *,
    regions: Sequence[tuple[float, float]] = (),
) -> Drawing:
    """The SVG page `svg` at `scale` image pixels to a px, on the ground: an image of each of
    `regions`, each a top and a height in the page's px, as wide as the page, or one image of
    the whole page where it holds none. `widths` gives the width the engine measured of each
    line of each text, by its trace id. Writes the page's faces in `folder`, which the caller
    removes. Raises ToolFailed."""
    page = _Page(svg, folder, widths)
    if regions:
        images = tuple(
            page.region(top, height, scale, number)
            for number, (top, height) in enumerate(regions, 1)
        )
    else:
        images = (page.image(scale),)
    return Drawing(images, tuple(page.dropped(images[0].width / page.width)))


def _pixels(length: float, scale: float) -> int:
    """How many pixels of an image `length` px take at `scale`, whole."""
    return math.ceil(round(length * scale, 6))


class _Page:
    """A page as the tool is given it: its faces in files, its fonts named for them, and each
    span of a line an element and a chunk of its own."""

    def __init__(self, svg: str, folder: Path, widths: Mapping[str, Sequence[float]]) -> None:
        self.root = ET.fromstring(svg)
        self.width = float(self.root.attrib["width"])
        self.height = float(self.root.attrib["height"])
        self.fonts: list[str] = []
        self._blanks: dict[tuple[int, int], bytes] = {}
        self._hand_over_faces(folder)
        self._set_spans_apart(widths)

    def _hand_over_faces(self, folder: Path) -> None:
        """Write each face of the page's rules as a file, and name the page's fonts for
        them. A text whose family no rule names keeps its name, which matches no face."""
        style = next(self.root.iter(STYLE))
        names: dict[str, str] = {}
        for number, face in enumerate(FACE.finditer(style.text or "")):
            name = names.setdefault(face["family"], f"pkit-face-{len(names)}")
            path = folder / f"{name}-{number}.font"
            _save_as(base64.b64decode(face["data"]), name, int(face["weight"]), path)
            self.fonts.append(str(path))
        style.text = FACE.sub("", style.text or "")
        for element in self.root.iter():
            family = element.get("font-family")
            if family:
                named = re.sub(CSS_STRING, lambda found: names.get(found[0], found[0]), family)
                element.set("font-family", named)

    def _set_spans_apart(self, widths: Mapping[str, Sequence[float]]) -> None:
        """Make each span of a line a chunk of its own. An absolute `y` starts one, and leaves
        the pen where the span before it stopped. The tool anchors each chunk alone, so a line
        of spans anchored at its middle or its end starts where its width puts it."""
        for text in self.root.iter(TEXT):
            before = ANCHORED.get(text.get("text-anchor", ""), 0.0)
            for place, line in enumerate(text.findall(SPAN)):
                spans = _spans(line)
                for span in spans[1:]:
                    span.set("y", line.attrib["y"])
                if before and len(spans) > 1:
                    width = widths[text.attrib["data-id"]][place]
                    line.set("x", str(float(line.attrib["x"]) - before * width))
                    line.set("text-anchor", "start")

    def image(self, scale: float) -> Image:
        """The whole page at `scale`, its long edge set whole."""
        self._sized()
        longest = max(self.width, self.height)
        long_edge = _pixels(longest, scale)
        if self.width * self.height * (long_edge / longest) ** 2 > MOST_PIXELS:
            raise ToolFailed(
                f"at {long_edge} pixels on its long edge the page takes more than {MOST_PIXELS}"
            )
        side = "width" if self.width >= self.height else "height"
        svg = ET.tostring(self.root, encoding="unicode")
        return _image(self._tool(svg, background=GROUND, **{side: long_edge}))

    def region(self, top: float, height: float, scale: float, number: int) -> Image:
        """Band `number` of the page, from `top` down `height` px, as wide as the page, at
        `scale`: the page's own view of it, stretched to whole pixels."""
        self._sized()
        size = (_pixels(self.width, scale), _pixels(height, scale))
        if size[0] * size[1] > MOST_PIXELS:
            raise ToolFailed(
                f"at {scale:g} pixels to a px band {number} of the page takes more than "
                f"{MOST_PIXELS}"
            )
        view = {
            "width": str(size[0]),
            "height": str(size[1]),
            "viewBox": f"0 {top!r} {self.width!r} {height!r}",
            "preserveAspectRatio": "none",
        }
        held = {name: self.root.get(name) for name in view}
        self.root.attrib.update(view)
        try:
            svg = ET.tostring(self.root, encoding="unicode")
        finally:
            for name, value in held.items():
                if value is None:
                    self.root.attrib.pop(name, None)
                else:
                    self.root.set(name, value)
        return _image(self._tool(svg, background=GROUND))

    def _sized(self) -> None:
        if min(self.width, self.height) <= 0:
            raise ToolFailed(f"the page measures {self.width:g} by {self.height:g} px")

    def dropped(self, scale: float) -> Iterator[Dropped]:
        """What the tool drew nothing of on this page, at `scale` image pixels to a px."""
        for text, x, y in self._texts(self.root, 0.0, 0.0):
            element = text.get("data-id", "")
            lost: list[str] = []
            shown = False
            lines = text.findall(SPAN)
            for line in lines:
                for index, span in enumerate(line):
                    if (span.text or "").strip():
                        if self._drew(text, line, index, (x, y), scale):
                            shown = True
                        else:
                            lost.append(span.text or "")
            if lost and not shown:
                yield Dropped(element, " ".join("".join(each.itertext()) for each in lines), True)
            else:
                yield from (Dropped(element, part, False) for part in lost)

    def _texts(
        self, node: ET.Element, x: float, y: float
    ) -> Iterator[tuple[ET.Element, float, float]]:
        """Each text under `node`, with where it stands in the page: the sum of its groups'
        moves."""
        for child in node:
            if child.tag == TEXT:
                yield child, x, y
            elif child.tag == GROUP:
                moved = MOVE.fullmatch(child.get("transform", ""))
                dx, dy = (float(moved[1]), float(moved[2])) if moved else (0.0, 0.0)
                yield from self._texts(child, x + dx, y + dy)

    def _drew(
        self,
        text: ET.Element,
        line: ET.Element,
        index: int,
        at: tuple[float, float],
        scale: float,
    ) -> bool:
        """Whether span `index` of `line` leaves any ink: drawn alone, its line kept whole
        and every other span unpainted, on the band of the page around the line."""
        sizes = [float(each.get("font-size", "0")) for each in (text, *line)]
        reach = BAND * max(sizes)
        baseline = at[1] + float(line.get("y", "0"))
        top = max(baseline - reach, 0.0)
        height = min(baseline + reach, self.height) - top
        if height <= 0:
            return False
        size = (math.ceil(self.width * scale), math.ceil(height * scale))
        band = ET.Element(
            f"{{{SVG_NAMESPACE}}}svg",
            {
                "width": str(size[0]),
                "height": str(size[1]),
                "viewBox": f"{-at[0]} {top - at[1]} {self.width} {height}",
            },
        )
        alone = ET.SubElement(band, TEXT, text.attrib)
        drawn = copy.deepcopy(line)
        for place, span in enumerate(drawn):
            if place != index:
                span.set("fill", "none")
                span.attrib.pop("fill-opacity", None)
        alone.append(drawn)
        return self._tool(ET.tostring(band, encoding="unicode")) != self._blank(size)

    def _blank(self, size: tuple[int, int]) -> bytes:
        """The band of `size` pixels with nothing drawn on it."""
        if size not in self._blanks:
            empty = ET.Element(
                f"{{{SVG_NAMESPACE}}}svg", {"width": str(size[0]), "height": str(size[1])}
            )
            self._blanks[size] = self._tool(ET.tostring(empty, encoding="unicode"))
        return self._blanks[size]

    def _tool(self, svg: str, **options: Any) -> bytes:
        """The one call of the tool. It reads the page's faces, and none of the machine's."""
        try:
            return bytes(
                resvg_py.svg_to_bytes(
                    svg_string=svg, font_files=self.fonts, skip_system_fonts=True, **options
                )
            )
        except ValueError as exc:
            raise ToolFailed(str(exc)) from exc


def _image(png: bytes) -> Image:
    width, height = struct.unpack(">II", png[PNG_SIZE])
    return Image(png, width, height)


def _spans(line: ET.Element) -> list[ET.Element]:
    """The spans of `line`, in order, each made an element of its own: a span the renderer
    wrote bare, as the text's own, takes a `<tspan>` of no attributes, so it can be set apart
    and unpainted alone."""
    spans: list[ET.Element] = []
    bare = line.text
    line.text = None
    if bare:
        spans.append(_bare(line, 0, bare))
    for child in list(line)[len(spans) :]:
        spans.append(child)
        tail = child.tail
        child.tail = None
        if tail:
            spans.append(_bare(line, list(line).index(child) + 1, tail))
    return spans


def _bare(line: ET.Element, place: int, text: str) -> ET.Element:
    span = ET.Element(SPAN)
    span.text = text
    line.insert(place, span)
    return span


def _save_as(data: bytes, family: str, weight: int, path: Path) -> None:
    """Write the font `data` at `path`, under `family` at `weight` alone."""
    font = TTFont(io.BytesIO(data), recalcTimestamp=False)
    names = font["name"]
    for number in FONT_NAMES:
        names.removeNames(nameID=number)
    for number in (1, 4, 6):
        names.setName(family, number, 3, 1, 0x409)
    font["OS/2"].usWeightClass = weight
    font.save(path)
