"""The HTML renderer: a scene drawn as one page file for each language, at one key, each
page real HTML text over SVG shapes (visual-communication DEC-020 points 1 to 4, DEC-005
points 4, 5, 9 and 10).

- **What it draws** is its declaration (`html_declaration.py`): every primitive the SVG
  renderer draws. It draws only what it declares, so the losses the capability reads from
  the declaration before it runs are the ones it makes.
- **The shapes** are the canvas's (`_lib/canvas.py`), with their paint, their arrowheads and
  their pictures as the SVG renderer writes them.
- **The tree's order is the file's.** The renderer walks a page's tree in order. Each text
  is written where it comes, and each run of shapes between two texts is one layer: an
  `svg` the size of the page, which takes no pointer. A group is no element of the page. A
  shape keeps its groups' moves in a `g`, and a text's left and top sum them.
- **A text** is one element at its frame: its left, top and width. Each of its lines is a
  child placed alone, which never wraps, and takes its alignment from the text's anchor. A
  strut opens each line. It is an empty inline block a whole number of page px high, whose
  foot sits on the baseline, so the line's top is its baseline less that height and the
  font's metrics place nothing. Each span follows the one before it, at the browser's own
  widths. A line's own font size and every line height are 0, so only the strut holds the
  line up.
- **Lengths** on a page are shares of its width (`cqw`), so a page scales with no script.
  A share is written to more places than a length of px is, since 1/100 of it is over
  1/10 px on a wide page.
- **The file** holds all it needs: each face once, subset to every character the file draws
  in it, each arrowhead once for its colour, and every picture. It asks for nothing. Its
  head declares its encoding, its language and its viewport. Its pages follow each other
  down the document with the gap the declaration names, and it sets no colour around them.
- **The text of the file** is HTML and well-formed XML alike. Whatever a brand or a piece
  names is escaped, so it can neither end the style element nor start another element.

Output is fixed for a version: the same scene and values give the same bytes. A change that
could give another output, here or in the canvas, raises the version, and the reference
outputs pinned to it in the tests catch one made without it (DEC-005 point 9).
"""

from __future__ import annotations

import math
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Any

from _lib.canvas import (
    ANCHORED,
    NORMAL,
    Canvas,
    Spans,
    attribute_text,
    find,
    font_families,
    number,
)
from _lib.plugins import seam
from _lib.plugins.html_declaration import DECLARATION, MARKS

NAME: str = DECLARATION["name"]
VERSION: str = DECLARATION["version"]

#: How many decimals a share of a page's width is written to: within 0.01 px of the engine's
#: length on any page under 200 000 px wide.
PLACES = 5

#: The CSS value of `text-align` for each anchor but the start, which is the browser's own.
ALIGNED = {"middle": "center", "end": "end"}

#: What the head says of the window, so no browser draws the page in a wider one of its own.
VIEWPORT = "width=device-width,initial-scale=1"

#: The rules every page file holds, after its faces. None sets a colour or clips anything.
SHEET = "".join(
    (
        "body{margin:0}",
        f"[{MARKS['page']}]{{position:relative;container-type:inline-size;margin:0 auto}}",
        f"[{MARKS['page']}]+[{MARKS['page']}]{{margin-top:{DECLARATION['pages']['gap']}px}}",
        f"[{MARKS['layer']}]{{position:absolute;left:0;top:0;width:100%;height:100%;"
        "pointer-events:none}",
        f"[{MARKS['text']}]{{position:absolute}}",
        f"[{MARKS['line']}]{{position:absolute;left:0;width:100%;font-size:0;line-height:0;"
        "white-space:pre}",
        f"[{MARKS['strut']}]{{display:inline-block;width:0}}",
    )
)


@dataclass(frozen=True)
class Drawn:
    """What one scene drawn in one combination gives: the page file, which holds every
    page; the trace id of each page it holds, in order; and what the renderer could not
    draw as given."""

    document: bytes
    pages: list[str]
    losses: list[seam.Loss]


def render(
    scene: Mapping[str, Any],
    *,
    key: str,
    colours: Mapping[str, Mapping[str, Any]],
    font_file: Callable[[str], Path],
    pictures: Mapping[str, Path],
) -> Drawn:
    """`scene` (`Scene.to_dict()`) drawn in the combination `key` as one page file: `colours`
    gives each colour role's value there, in canonical form; `font_file` the committed file
    of a font family; `pictures` the file of each produced output's variant that serves
    `key`."""
    file = PageFile(DECLARATION, scene, key, colours, font_file, pictures)
    traces, pages = [], []
    for trace in scene.get("pages", []):
        element = find(scene.get("children", []), trace)
        if element is not None:
            traces.append(trace)
            pages.append(file.page(element))
    return Drawn(file.document("".join(pages)), traces, file.losses)


def _style(pairs: list[tuple[str, Any]]) -> str:
    """CSS declarations, as the value of a `style` attribute."""
    return ";".join(f"{name}:{value}" for name, value in pairs if value is not None)


def _leaves(
    element: Mapping[str, Any], x: float, y: float
) -> Iterator[tuple[Mapping[str, Any], float, float]]:
    """Each element under `element` that is no group, in the tree's order, with the move of
    the groups around it, which starts at (`x`, `y`)."""
    for child in element.get("children", []):
        if child.get("type") == "group":
            moved_x, moved_y = x + float(child.get("x", 0)), y + float(child.get("y", 0))
            yield from _leaves(child, moved_x, moved_y)
        else:
            yield child, x, y


def _moved(drawn: str, x: float, y: float) -> str:
    """A shape as written, inside the move of its groups."""
    if not drawn or not (x or y):
        return drawn
    return f'<g transform="translate({number(x)},{number(y)})">{drawn}</g>'


def _strut(spans: Spans) -> int:
    """The height of a line's strut, in whole px of the page: the largest font size among
    its runs, rounded up. A run's line height is 0, so it rises half of what its ascent
    passes its descent by, well within its font size."""
    largest = max((float(run.get("font-size", 0)) for _, run in spans), default=0.0)
    return max(math.ceil(largest), 1)


class PageFile(Canvas):
    """The pages of one scene in one combination, as one page file. The faces and the
    arrowheads the canvas records gather over every page, since the file holds each once."""

    #: The width of the page being written, of which every length on it is a share.
    _page_width: float = 1.0

    def _share(self, length: Any) -> str:
        """A length in px of the page, as a share of the page's width."""
        return f"{number(float(length) / self._page_width * 100, PLACES)}cqw"

    # -- the file

    def document(self, pages: str) -> bytes:
        """The page file that holds `pages`. Its faces and arrowheads are those `page`
        recorded, so it is written after every page."""
        head = attribute_text(
            [
                ("lang", self.scene.get("language")),
                ("data-piece", self.scene.get("piece")),
                ("data-key", self.key),
                ("data-renderer", f"{NAME} {VERSION}"),
            ]
        )
        title = escape(str(self.scene.get("piece", "")), quote=False)
        return (
            "<!DOCTYPE html>\n"
            f"<html {head}>\n"
            "<head>\n"
            '<meta charset="utf-8"/>\n'
            f'<meta name="viewport" content="{VIEWPORT}"/>\n'
            f"<title>{title}</title>\n"
            f"<style>{self._font_faces()}{SHEET}</style>\n"
            "</head>\n"
            f"<body>{self._arrowheads()}{pages}</body>\n"
            "</html>\n"
        ).encode()

    def _arrowheads(self) -> str:
        """The arrowheads every layer of the file draws, in an `svg` of no size. A layer
        reaches them by their ids, so each is defined once. Nothing where none is drawn."""
        markers = self._arrow_markers()
        if not markers:
            return ""
        return f'<svg width="0" height="0" style="position:absolute"><defs>{markers}</defs></svg>'

    # -- a page

    def page(self, element: Mapping[str, Any]) -> str:
        """A page: as wide as its frame, or as the window where that is narrower, and in the
        frame's proportions, its texts and layers in the tree's order."""
        self._page_width = float(element["width"])
        width, height = number(element["width"]), number(element["height"])
        size = f"width:min(100%,{width}px);aspect-ratio:{width}/{height}"
        written: list[str] = []
        shapes: list[str] = []
        for leaf, x, y in _leaves(element, 0.0, 0.0):
            if leaf.get("type") == "text":
                written += [self._layer(element, shapes), self._text(leaf, x, y)]
                shapes = []
            else:
                shapes.append(_moved(self._element(leaf), x, y))
        written.append(self._layer(element, shapes))
        head = attribute_text([(MARKS["page"], element["id"]), ("style", size)])
        return f"<div {head}>{''.join(written)}</div>"

    def _layer(self, page: Mapping[str, Any], shapes: list[str]) -> str:
        """A run of shapes as one layer, on the page's own coordinates. Nothing where the
        run drew nothing."""
        drawn = "".join(shapes)
        if not drawn:
            return ""
        view = f"0 0 {number(page['width'])} {number(page['height'])}"
        return f"<svg {attribute_text([(MARKS['layer'], ''), ('viewBox', view)])}>{drawn}</svg>"

    # -- a text

    def _text(self, element: Mapping[str, Any], x: float = 0.0, y: float = 0.0) -> str:
        """A text at its frame, which the groups around it move by (`x`, `y`)."""
        style = _style(
            [
                ("left", self._share(x + float(element["x"]))),
                ("top", self._share(y + float(element["y"]))),
                ("width", self._share(element["width"])),
                ("text-align", ALIGNED.get(element.get("text-anchor", "start"))),
            ]
        )
        lines = "".join(
            self._text_line(element, baseline, line, spans)
            for baseline, line, spans in self._text_lines(element, 0.0)
        )
        head = attribute_text([(MARKS["text"], element["id"]), ("style", style)])
        return f"<div {head}>{lines}</div>"

    def _text_line(
        self,
        element: Mapping[str, Any],
        baseline: float,
        line: Mapping[str, Any],
        spans: Spans,
    ) -> str:
        """A line whose baseline lies `baseline` below its text's top. A browser starts a
        line too wide for its box at the box's start, whatever its alignment, so the box of
        such a line grows to hold it, and the anchor keeps the place the engine gave it."""
        strut = _strut(spans)
        width = float(element["width"])
        over = max(float(line["width"]) - width, 0.0)
        before = ANCHORED.get(element.get("text-anchor", "start"), 0.0)
        wider = before > 0 and over > 0
        style = _style(
            [
                ("top", self._share(baseline - strut)),
                ("left", self._share(-before * over) if wider else None),
                ("width", self._share(width + over) if wider else None),
            ]
        )
        opening = attribute_text([(MARKS["strut"], ""), ("style", f"height:{self._share(strut)}")])
        drawn = "".join(self._span(element, span, run) for span, run in spans)
        head = attribute_text([(MARKS["line"], ""), ("style", style)])
        return f"<div {head}><span {opening}></span>{drawn}</div>"

    def _span(
        self, element: Mapping[str, Any], span: Mapping[str, Any], run: Mapping[str, Any]
    ) -> str:
        """The part of a run on one line, each span written whole, in its run's font, size
        and paint. It takes no place of its own."""
        weight = run.get("font-weight")
        style = _style(
            [
                ("font-family", font_families(run) or None),
                ("font-size", self._share(run.get("font-size", 0))),
                ("font-weight", weight if weight not in (None, NORMAL) else None),
                ("color", self._colour(element, run)),
            ]
        )
        head = attribute_text([(MARKS["span"], ""), ("style", style)])
        return f"<span {head}>{escape(span['text'], quote=False)}</span>"

    def _colour(self, element: Mapping[str, Any], run: Mapping[str, Any]) -> str:
        """The CSS colour of a run: its fill as the canvas paints it, with its opacity as
        the colour's alpha. A run with no paint is transparent, so it never takes the
        browser's own colour."""
        paint = dict(self._paint({"id": element["id"], "fill": run.get("fill")}, "fill"))
        fill, opacity = paint["fill"], paint.get("fill-opacity")
        if fill == "none":
            return "transparent"
        return fill if opacity is None else f"{fill}{round(float(opacity) * 255):02x}"
