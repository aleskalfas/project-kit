"""The HTML renderer: a scene drawn as one page file for each language and each key over the
size axes, holding the modes a reader's signal names, each page real HTML text over SVG
shapes (visual-communication DEC-020 points 1 to 4, DEC-023, DEC-031 points 1 to 4, DEC-005
points 4, 5, 9 and 10).

- **What it draws** is its declaration (`html_declaration.py`): every primitive the SVG
  renderer draws. It draws only what it declares, so the losses the capability reads from
  the declaration before it runs are the ones it makes.
- **One call for a file.** `render` is handed the format, the scene, every key the file holds
  with its combination, the first naming the file, and each key's colours and pictures
  (DEC-023 point 2). The keys share the scene's size, so each key's colours are that size's.
- **The shapes** are the canvas's (`_lib/canvas.py`), with their arrowheads and their
  pictures as the SVG renderer writes them. Only how a paint is written differs, in methods
  of this module's own.
- **A paint is a custom property** (DEC-023 point 3): one for each colour role the file
  paints, in the CSS writer's spelling (`css.name_of`), which the renderer shares and never
  reads the writer's output for. A span's colour and a shape's fill and stroke read the same
  property, so an arrowhead lies once for each role, and a colour's alpha lies in its value.
  A role with no colour in one key takes `transparent` there, so it draws nothing, and that
  key reports the loss. A role with no colour in any key is written as no role is.
- **The reader's system picks a mode** (DEC-023 point 4). The plain rule holds the first
  key's values. Each other key's lie in a rule under the signals that part it from the first,
  after every rule of fewer, so a reader's signals always meet one key. The file holds no
  control and no script, and no rule on a window's width. CSS's `color-scheme` names the
  scheme of each mode the file holds that pairs with `prefers-color-scheme`, so a page with
  no ground lies on the browser's ground for that mode (DEC-023 point 7).
- **Under forced colours** one rule gives each line, stroke and arrowhead the reader's text
  colour, and each fill opaque in every key the reader's background colour, with an edge
  where it has no stroke of its own, as the declaration names (DEC-023 point 7).
- **A picture** draws as the first key shows it, embedded whole as the canvas embeds it, a
  PNG or a JPEG with the colour profile it carries. Each other key that shows another
  picture, such as another variant of a produced output, reports a loss (DEC-023 point 8).
  A picture file is the same in every key, so it reports none. A loss in one key of a file
  that holds several names that key.
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
  in it, each arrowhead once for its role, and every picture. It asks for nothing. Its
  head declares its encoding, its language and its viewport. Its pages follow each other
  down the document with the gap the declaration names, and it sets no colour value
  around them.
- **Fixed pages** (DEC-031 points 1 to 4). Where the scene's root says its pages are fixed
  pages, as a deck's slides are, the file shows each inside a keyline, on a backdrop that
  fills the window around and between them, as the declaration's `pages.fixed` names them.
  Each is a mix of the browser's text colour into its ground colour, so it follows the
  scheme the file names, and a browser that cannot mix keeps the text colour for the
  keyline and the ground for the backdrop. The keyline is an outline, so it takes no room
  and keeps its width in px as a page shrinks. Inside it each page lies on the browser's
  ground. The backdrop shows at the gutter on every side, which narrows with the window, and
  a page shrinks with the room the gutter leaves it. Under more contrast the keyline takes
  the text colour, and under forced colours the backdrop and each page take the reader's
  background colour, and the keyline their text colour. Each rule is for a screen alone, so
  a print holds none of them. Only the sheet gains these rules, and no element changes. A
  file of other pages holds none of them.
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
    ENDS,
    NORMAL,
    Canvas,
    Spans,
    attribute_text,
    colour_text,
    find,
    font_families,
    number,
    shows,
    unshown,
)
from _lib.plugins import seam
from _lib.plugins.css import name_of
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

#: The reader's signal whose values CSS's `color-scheme` names: a scheme of the browser's own.
SCHEMES = "prefers-color-scheme"

#: The paint of a role with no colour in one key: it draws nothing there.
NOTHING = "transparent"

#: The browser's own colours, CSS's system colours: its text colour and its ground colour. A
#: fixed page's keyline and backdrop mix them (DEC-031 point 3).
TEXT_COLOUR = "CanvasText"
GROUND_COLOUR = "Canvas"

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


def mixed(share: float) -> str:
    """`share` percent of the browser's text colour mixed into its ground colour, in sRGB."""
    return f"color-mix(in srgb,{TEXT_COLOUR} {number(share)}%,{GROUND_COLOUR})"


def fixed_sheet(fixed: Mapping[str, Any]) -> str:
    """The rules a file of fixed pages holds, as `fixed`, the declaration's `pages.fixed`,
    names them (DEC-031 points 1 to 4), each for a screen alone. The backdrop is the
    document's background, and the gutter the body's padding. Each page lies on the browser's
    ground inside its keyline, an outline. A browser that cannot mix colours keeps the plain
    colour written before each mix."""
    page = f"[{MARKS['page']}]"
    keyline, backdrop, gutter = fixed["keyline"], fixed["backdrop"], fixed["gutter"]
    plain = "".join(
        (
            f"html{{background:{GROUND_COLOUR};background:{mixed(backdrop['share'])}}}",
            f"body{{padding:min({number(gutter['width'])}px,{number(gutter['window-share'])}vw)}}",
            f"{page}{{background:{GROUND_COLOUR};"
            f"outline:{number(keyline['width'])}px solid {TEXT_COLOUR};"
            f"outline-color:{mixed(keyline['share'])}}}",
        )
    )
    more = f"{page}{{outline-color:{TEXT_COLOUR}}}"
    forced = f"html,{page}{{background:{GROUND_COLOUR}}}{page}{{outline-color:{TEXT_COLOUR}}}"
    return (
        f"@media screen{{{plain}}}"
        f"@media screen and (prefers-contrast:more){{{more}}}"
        f"@media screen and (forced-colors:active){{{forced}}}"
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
    form: str,
    keys: Mapping[str, Mapping[str, str]],
    colours: Mapping[str, Mapping[str, Mapping[str, Any]]],
    font_file: Callable[[str], Path],
    pictures: Mapping[str, Mapping[str, seam.Shown]],
) -> Drawn:
    """`scene` (`Scene.to_dict()`) drawn as one page file of the format `form`, holding each of
    `keys`: each key with its combination, every axis's mode, in key order, the first naming
    the file. By key, `colours` gives each colour role's value, in canonical form, and
    `pictures` the picture each image shows there, by the image's trace id (`seam.Shown`),
    whatever its source; `font_file` gives
    the committed file of a font family. Raises ValueError for a format the declaration does
    not name, or keys that differ in a mode it pairs with no signal."""
    file = PageFile(DECLARATION, scene, form, keys, colours, font_file, pictures)
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


def _value(colour: Mapping[str, Any] | None) -> str:
    """A colour's value as a custom property holds it: `#rrggbb`, its alpha after it where it is
    translucent, as the canvas rounds an opacity, or `NOTHING` for no colour."""
    if colour is None:
        return NOTHING
    text, alpha = colour_text(colour)
    return text if alpha >= 1 else f"{text}{round(float(number(alpha)) * 255):02x}"


def _opaque(colour: Mapping[str, Any] | None) -> bool:
    return colour is not None and colour_text(colour)[1] >= 1


class PageFile(Canvas):
    """The pages of one scene in the combinations `keys` holds, as one page file. The faces,
    the arrowheads and the roles painted gather over every page, since the file holds each
    once. The canvas draws in the first key, whose pictures the page shows."""

    #: The width of the page being written, of which every length on it is a share.
    _page_width: float = 1.0

    def __init__(
        self,
        declaration: Mapping[str, Any],
        scene: Mapping[str, Any],
        form: str,
        keys: Mapping[str, Mapping[str, str]],
        colours: Mapping[str, Mapping[str, Mapping[str, Any]]],
        font_file: Callable[[str], Path],
        pictures: Mapping[str, Mapping[str, seam.Shown]],
    ) -> None:
        if form not in declaration["holds-modes"]:
            raise ValueError(f"the {declaration['name']} renderer writes no format `{form}`")
        if not keys:
            raise ValueError("a page file holds at least one key")
        first = next(iter(keys))
        super().__init__(declaration, scene, first, colours[first], font_file, pictures[first])
        self.pairs: Mapping[str, Mapping[str, Any]] = declaration["holds-modes"][form]
        self.keys = dict(keys)
        self.colours_of = colours
        self.pictures_of = pictures
        # The roles the file paints, and those a shape fills, by their names.
        self._painted: set[str] = set()
        self._filled: set[str] = set()
        self._parted = {key: self._parting(key) for key in self.keys}

    def _parting(self, key: str) -> dict[str, str]:
        """The signals that part `key` from the first key, each with its value: one for each
        axis whose mode differs. Raises ValueError where that mode pairs with no signal."""
        first = self.keys[self.key]
        found = {}
        for axis, mode in self.keys[key].items():
            if mode == first.get(axis):
                continue
            pair = self.pairs.get(axis, {})
            if mode not in pair.get("pairs", {}):
                raise ValueError(
                    f"`{key}` and `{self.key}` differ in `{axis}`, whose mode `{mode}` pairs "
                    f"with no signal, so no file holds both"
                )
            found[pair["signal"]] = pair["pairs"][mode]
        return found

    def _lose_in(self, key: str, what: str, did: str, why: str) -> None:
        """A loss in the one combination `key`, which names it where the file holds several."""
        loss = seam.Loss(
            self.declaration["name"], what, did, why, key if len(self.keys) > 1 else None
        )
        if loss not in self.losses:
            self.losses.append(loss)

    # -- paint

    def _role(self, what: str, prop: str, role: str | None) -> str | None:
        """`role`, the paint `prop` of `what`, where some key gives it a colour, and None where
        none does. Each key that gives it none reports the loss."""
        if role is None:
            return None
        missing = [key for key in self.keys if self.colours_of[key].get(role) is None]
        for key in missing:
            self._lose_in(
                key,
                what,
                seam.LEFT_OUT,
                f"the brand gives the role `{role}` of its {prop} no colour in `{key}`",
            )
        if len(missing) == len(self.keys):
            return None
        self._painted.add(role)
        return role

    def _paint(self, element: Mapping[str, Any], prop: str) -> list[tuple[str, Any]]:
        return self._paint_attributes(prop, self._role(element["id"], prop, element.get(prop)))

    def _paint_attributes(self, prop: str, role: str | None) -> list[tuple[str, Any]]:
        """A shape's paint: its role's custom property, so each key's value reaches it. With no
        `role`, a fill of none, and nothing for a stroke."""
        if role is None:
            return [(prop, "none")] if prop == "fill" else []
        if prop == "fill":
            self._filled.add(role)
        return [(prop, f"var({name_of(role)})")]

    def _markers(
        self, element: Mapping[str, Any], stroke: list[tuple[str, Any]]
    ) -> list[tuple[str, Any]]:
        """The arrowheads a line draws, each a marker the file defines once for its stroke's
        role, which paints it in each key. A line with no stroke draws none."""
        paint = dict(stroke)
        if "stroke" not in paint:
            return []
        found = []
        for which in ENDS:
            if element.get(f"marker-{which}") == "arrow":
                marker = f"pkit-arrow-{which}{name_of(element['stroke'])}"
                self._arrows[marker] = (which, paint["stroke"], None)
                found.append((f"marker-{which}", f"url(#{marker})"))
        return found

    def _share(self, length: Any) -> str:
        """A length in px of the page, as a share of the page's width."""
        return f"{number(float(length) / self._page_width * 100, PLACES)}cqw"

    # -- the file

    def document(self, pages: str) -> bytes:
        """The page file that holds `pages`. Its faces, arrowheads and paints are those `page`
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
        fixed = fixed_sheet(self.declaration["pages"]["fixed"]) if self._fixed() else ""
        return (
            "<!DOCTYPE html>\n"
            f"<html {head}>\n"
            "<head>\n"
            '<meta charset="utf-8"/>\n'
            f'<meta name="viewport" content="{VIEWPORT}"/>\n'
            f"<title>{title}</title>\n"
            f"<style>{self._font_faces()}{self._modes()}{SHEET}{fixed}{self._forced()}</style>\n"
            "</head>\n"
            f"<body>{self._arrowheads()}{pages}</body>\n"
            "</html>\n"
        ).encode()

    def _fixed(self) -> bool:
        """Whether the scene's root says its pages are fixed pages (DEC-031 point 2). A root
        that does not say so holds none."""
        return self.scene.get("fixed-pages") is True

    def _modes(self) -> str:
        """The values of every role the file paints in each key it holds: the plain rule the
        first key's, with the schemes of the file, and each other key's under the signals
        that part it from the first, fewer signals first, so the rule of a reader's own key
        comes after every other they meet. Nothing where the file paints nothing and names no
        scheme."""
        roles = sorted(self._painted)
        schemes = self._schemes()
        plain = [f"color-scheme:{' '.join(schemes)}"] if schemes else []
        rules = [self._values(self.key, roles, plain)] if roles or plain else []
        others = sorted(
            (key for key in self.keys if key != self.key),
            key=lambda key: len(self._parted[key]),
        )
        for key in others if roles else ():
            signals = " and ".join(
                f"({signal}:{value})" for signal, value in sorted(self._parted[key].items())
            )
            rules.append(f"@media {signals}{{{self._values(key, roles)}}}")
        return "".join(rules)

    def _values(self, key: str, roles: list[str], first: list[str] | None = None) -> str:
        """A rule of the root holding `first`, then each of `roles` at its value in `key`."""
        colours = self.colours_of[key]
        held = [*(first or []), *(f"{name_of(role)}:{_value(colours.get(role))}" for role in roles)]
        return f":root{{{';'.join(held)}}}"

    def _schemes(self) -> list[str]:
        """The scheme of each mode the file holds that pairs with `SCHEMES`, in key order."""
        found: dict[str, None] = {}
        for combination in self.keys.values():
            for axis, mode in combination.items():
                pair = self.pairs.get(axis, {})
                if pair.get("signal") == SCHEMES and mode in pair.get("pairs", {}):
                    found[pair["pairs"][mode]] = None
        return list(found)

    def _forced(self) -> str:
        """What the file gives its shapes under forced colours, as the declaration names it:
        each line, stroke and arrowhead the reader's text colour, and each fill opaque in every
        key the reader's background colour, with an edge where it has no stroke of its own."""
        forced = self.declaration["forced-colours"]
        layer, lines = f"[{MARKS['layer']}]", forced["lines"]
        rules = [f"{layer} [stroke]{{stroke:{lines}}}", f"marker path{{fill:{lines}}}"]
        opaque = [
            f'{layer} [fill="var({name_of(role)})"]'
            for role in sorted(self._filled)
            if all(_opaque(self.colours_of[key].get(role)) for key in self.keys)
        ]
        if opaque:
            edge = forced["edge"]
            unstroked = ",".join(f"{each}:not([stroke])" for each in opaque)
            rules.append(f"{','.join(opaque)}{{fill:{forced['opaque-fills']}}}")
            rules.append(f"{unstroked}{{stroke:{edge['colour']};stroke-width:{edge['width']}px}}")
        return f"@media (forced-colors:active){{{''.join(rules)}}}"

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
        """The CSS colour of a run: its fill's custom property. A run with no paint is
        transparent, so it never takes the browser's own colour."""
        role = self._role(element["id"], "fill", run.get("fill"))
        return NOTHING if role is None else f"var({name_of(role)})"

    # -- a picture

    def _image(self, element: Mapping[str, Any]) -> str:
        """A picture as the first key shows it. Each other key that shows another picture
        reports the loss, and each key it is handed no picture in (DEC-023 point 8). A
        picture file is the same in every key, so it reports none."""
        trace = str(element["id"])
        handed = {key: self.pictures_of[key].get(trace) for key in self.keys}
        first = handed[self.key]
        shown = first is not None and first.file.is_file()
        drawn = first.file.read_bytes() if first is not None and shown else None
        # A produced output's picture is a variant; any other is a file.
        held = "variant" if "output" in element else "picture"
        for key, each in handed.items():
            if each is None or not each.file.is_file():
                why = unshown(element, key, self.scene.get("piece"))
                self._lose_in(key, trace, seam.LEFT_OUT, why)
            elif each != first and each.file.read_bytes() != drawn:
                self._lose_in(
                    key,
                    trace,
                    seam.APPROXIMATED if shown else seam.LEFT_OUT,
                    f"the page draws the {held} of `{self.key}` of {shows(element)}, and `{key}` "
                    f"takes another",
                )
        return super()._image(element) if shown else ""
