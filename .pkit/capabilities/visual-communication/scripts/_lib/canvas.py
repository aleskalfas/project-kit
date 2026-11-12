"""The canvas: a scene projected onto a page, and written as SVG (visual-communication DEC-005
points 4, 5, 9 and 10).

The SVG renderer (`plugins/svg.py`) draws through it. A second renderer, or a second form of
the SVG renderer's file, subclasses it, and replaces only what differs, each in a method of
its own:

- **How a paint is written:** `_paint_attributes`. Which colour a role takes, and the loss of
  a role with none, stay here, in `_paint`.
- **The arrow markers:** `_markers`, which keys them on the colour a stroke is written in, so
  a subclass that writes a paint otherwise replaces it too. `_arrow_markers` defines what it
  recorded, each through `_marker`, which draws the triangle in the paint it is handed.
- **A rule of the page:** `_rules`, which writes nothing here. A subclass that repaints the
  page by a rule writes it after the page's style, once its elements are drawn.
- **A picture:** `_image`, which draws the picture of the combination drawn through
  `_picture`. A subclass that shows another picture in another combination draws each
  through `_picture` too.
- **The font faces:** `_font_faces`, which writes those of a page. A text records what it
  draws in each, whichever writes them.
- **A span's placing:** `_span_place`, handed where the engine's widths start each span
  (`placed`). Here it places a span only on a line that holds a sign or a ground.
- **A text as a whole:** `_text`, for a renderer that writes no SVG text. It reads a text
  through `_text_lines`, which keeps its baselines, the run of each span, and what each face
  draws, whichever writes them.

The rest is how a scene is projected, whatever writes it: a stroke's inset, a text's
anchoring, its baselines and the placing of its lines. What a subclass in another module
writes with lies here too: `number`, `attribute_text`, `font_families`, `css_string`, and
`find`, which finds a page in the tree.

The canvas is no plugin. It lies outside `plugins/`, so the seam never reads it as one, and a
renderer hands it its declaration, which names the renderer in each page and each loss and
says what it draws.

- **Colours** stay roles in the scene. The canvas takes each from the brand's resolved values
  in the combination it draws (`colours`), as `#rrggbb` with an opacity where the colour is
  translucent. A role with no colour there is left out, and reported.
- **Fonts** are embedded as `@font-face` from the brand's committed files, never the
  machine's: each family's file subset to the characters the page draws in it. A family's
  name is written as a CSS string (`css_string`), so no name a brand gives can end the
  style element, start another element, or leave the file malformed XML. A file the engine
  could measure from may still fail to subset, which raises `UnreadableFont`.
- **Text** is drawn as the engine measured it: each of its lines as given, at its own
  baseline, anchored at the start, the middle or the end of the text's width. The
  `<text>` takes the font and the paint of the text's first run; each span of a run that
  looks otherwise is a `<tspan>` with its own (DEC-012). A text of one run is drawn as
  format 1 drew it.
- **A run's sign and ground** (DEC-036 point 3). On a line that holds either, each span
  starts where the engine's widths place it, after the room the engine gave a ground's
  start and a sign (`placed`). Before the text, so behind it, each piece of a ground is a
  `<path>` in its role, its corners rounded where the ground starts and ends and square
  where a line breaks it (`ground_path`), and each sign is a `<path>` of its outline,
  moved to its square, filled by its rule in its run's paint. They name their text as
  `data-ground` and `data-sign`. A line of neither is drawn as before.
- **A line** whose route turns, a tie's connector, is a `<polyline>` through its points,
  and names the elements its ends meet (`data-start`, `data-end`). An arrowhead is a
  marker the page defines once for each colour a line draws one in. A line that holds
  neither its ends nor its points is refused, and left out.
- **A path**, such as a concept's sign, is a `<path>` of the outline the engine mapped into
  its frame, `d` as the scene holds it, filled by its rule, `fill-rule`, written only where
  it is `evenodd`, since SVG's default is the other. Its stroke lies on its outline, as
  SVG strokes a path. A path that holds no outline is refused, and left out.
- **A picture** is embedded whole, as the picture its image shows in the combination drawn
  (`seam.Shown`), whatever its source: PNG data for a PNG and JPEG data for a JPEG, its bytes
  as they are, so a colour profile it carries stays with it (DEC-025 points 5 and 7). An
  image handed no picture there is left out, and reported (`unshown`).
- **Every element carries its trace id** (`data-id`), and a group the component that drew
  it (`data-component`) with its library's version (`data-version`), the page's own group
  included, so a reader of the file finds where each element came from.

Lengths are written to 1/100 px and attributes in one order, so the same scene and values
give the same bytes. A change here that could give another output raises the version of each
renderer that draws through the canvas (DEC-005 point 9).
"""

from __future__ import annotations

import base64
import io
import logging
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Any

from fontTools import subset
from fontTools.ttLib import TTFont

from _lib.env import UnreadableFont
from _lib.plugins import seam

#: A line's two ends, each of which may carry an arrowhead.
ENDS = ("start", "end")

#: Where a line's two ends lie, as a scene holds them.
ENDS_OF_LINE = ("x1", "y1", "x2", "y2")

#: The weight a text without one is drawn in.
NORMAL = 400

#: How much of a width lies before the place an anchor holds it at.
ANCHORED = {"middle": 0.5, "end": 1.0}

#: Where the control points of a quarter circle lie, drawn as one cubic Bézier curve, as a
#: share of its radius.
KAPPA = 0.5522847498307936

#: The spans of a line, each with the run it is part of.
Spans = list[tuple[Mapping[str, Any], Mapping[str, Any]]]

#: The media type each kind of picture is embedded as.
MEDIA = {seam.PNG: "image/png", seam.JPEG: "image/jpeg"}

logging.getLogger("fontTools.subset").setLevel(logging.ERROR)


def colour_text(value: Mapping[str, Any]) -> tuple[str, float]:
    """A colour in canonical form as `#rrggbb`, each component rounded to 8 bits half up,
    and its alpha."""
    channels = "".join(f"{int(float(c) * 255 + 0.5):02x}" for c in value["components"])
    return f"#{channels}", float(value.get("alpha", 1))


def number(value: Any, places: int = 2) -> str:
    """A number as SVG holds it: to `places` decimals, 1/100 where none are given, with no
    trailing zero and no negative zero."""
    rounded = round(float(value), places) + 0.0
    if rounded == int(rounded):
        return str(int(rounded))
    return f"{rounded:.{places}f}".rstrip("0")


def css_string(name: str) -> str:
    """A name as a CSS string between double quotes: `"` and `\\` escaped, and as the
    escape of its code point each character that could end the style element or start
    another (`<`, `>`, `&`), each control character, and each character XML 1.0 does not
    allow. So any name reaches the file as one name, and the file stays well-formed XML."""
    # The CSS code writer's `_quoted` (`plugins/css.py`) writes a family name the same way,
    # escaping less. It is kept apart so that the CSS writer's output and version do not
    # move: a change to how either writes a CSS string is weighed for the other too.
    out = []
    for char in name:
        if char in ('"', "\\"):
            out.append("\\" + char)
        elif char in "<>&" or not _plain(char):
            out.append(f"\\{ord(char):x} ")
        else:
            out.append(char)
    return '"' + "".join(out) + '"'


def _plain(char: str) -> bool:
    """Whether a character is neither a control character (U+0000 to U+001F, U+007F to
    U+009F) nor one XML 1.0 does not allow (a surrogate, U+FFFE, U+FFFF)."""
    code = ord(char)
    return not (
        code < 0x20 or 0x7F <= code <= 0x9F or 0xD800 <= code <= 0xDFFF or code in (0xFFFE, 0xFFFF)
    )


def font_families(run: Mapping[str, Any]) -> str:
    """A run's font families, as the value of `font-family`."""
    return ", ".join(css_string(family) for family in run.get("font-family", []))


def attribute_text(pairs: list[tuple[str, Any]]) -> str:
    return " ".join(f'{name}="{_attribute(value)}"' for name, value in pairs if value is not None)


def _attribute(value: Any) -> str:
    """A value as the text of an attribute between double quotes."""
    return escape(str(value), quote=False).replace('"', "&quot;")


def shows(element: Mapping[str, Any]) -> str:
    """What an image shows, in words, by its source: a produced output, a picture file and
    where it lies, or a picture role."""
    if "output" in element:
        return f"the produced output `{element['output']}`"
    if "file" in element:
        return f"the picture file `{element['file']}` of `{element.get('library')}`"
    return f"the picture role `{element.get('role')}`"


def unshown(element: Mapping[str, Any], key: str, piece: Any) -> str:
    """Why an image is handed no picture to draw in the combination `key`, by its source,
    with what mends it: a produced output with no variant for it, a picture file not found, a
    picture role the brand gives no file there."""
    if "output" in element:
        output = element["output"]
        return (
            f"the produced output `{output}` has no variant for `{key}`: run "
            f"`pkit visual produce {piece} {output}`"
        )
    if "file" in element:
        return (
            f"{shows(element)} is not found to draw in `{key}`: `pkit visual check {piece}` "
            f"names why"
        )
    return f"the brand gives {shows(element)} no file in `{key}`"


@dataclass(frozen=True)
class GroundPiece:
    """A piece of a run's ground on one line (DEC-036 point 3): its left and its right, its
    top below the line's top and its height, the radius of its corners, the role it paints,
    and whether the ground starts and ends in it, where its corners are rounded."""

    left: float
    right: float
    top: float
    height: float
    rx: float
    role: str | None
    starts: bool
    ends: bool


@dataclass(frozen=True)
class Placed:
    """A line's spans placed as the engine measured them, from where the line starts
    (DEC-036 point 3): where each span's text starts; each sign the line draws, with the
    left of its square, its span and its run; and each piece of a ground."""

    starts: tuple[float, ...]
    signs: tuple[tuple[float, Mapping[str, Any], Mapping[str, Any]], ...]
    grounds: tuple[GroundPiece, ...]


def marked(line: Mapping[str, Any]) -> bool:
    """Whether a line's spans hold a sign or a ground (DEC-036 point 3)."""
    return any("sign" in span or "ground" in span for span in line.get("spans", []))


def room(span: Mapping[str, Any]) -> float:
    """How far a span's sign and ground move the pen beside its text: its ground's room
    before it and after it, and its sign and the sign's gap (DEC-036 point 3)."""
    ground, sign = span.get("ground") or {}, span.get("sign")
    extra = float(ground.get("start", 0)) + float(ground.get("end", 0))
    return extra + (float(sign["size"]) + float(sign["gap"]) if sign is not None else 0.0)


def placed(spans: Spans, pen: float, widths: Sequence[float] | None = None) -> Placed:
    """The spans of a line placed from `pen`: each span's ground's room before it, its sign
    and the sign's gap, its text, as wide as `widths` gives, else as the span's own width,
    and its ground's room after it (DEC-036 point 3). A ground's piece runs from the room
    before its first span to the room after its last, and a new piece starts where the
    ground starts again, or where the next span takes another or none."""
    starts: list[float] = []
    signs: list[tuple[float, Mapping[str, Any], Mapping[str, Any]]] = []
    grounds: list[GroundPiece] = []
    piece: tuple[float, Mapping[str, Any], str | None, bool] | None = None
    for place, (span, run) in enumerate(spans):
        ground = span.get("ground")
        role = run.get("ground")
        if piece is not None and (ground is None or "start" in ground or role != piece[2]):
            grounds.append(_piece(piece, pen, ends=False))
            piece = None
        if ground is not None and piece is None:
            piece = (pen, ground, role, "start" in ground)
        if ground is not None:
            pen += float(ground.get("start", 0))
        sign = span.get("sign")
        if sign is not None:
            signs.append((pen, span, run))
            pen += float(sign["size"]) + float(sign["gap"])
        starts.append(pen)
        pen += float(widths[place] if widths is not None else span["width"])
        if ground is not None:
            pen += float(ground.get("end", 0))
        if piece is not None and ground is not None and "end" in ground:
            grounds.append(_piece(piece, pen, ends=True))
            piece = None
    if piece is not None:
        grounds.append(_piece(piece, pen, ends=False))
    return Placed(tuple(starts), tuple(signs), tuple(grounds))


def _piece(
    piece: tuple[float, Mapping[str, Any], str | None, bool], right: float, *, ends: bool
) -> GroundPiece:
    left, ground, role, starts = piece
    return GroundPiece(
        left,
        right,
        float(ground["top"]),
        float(ground["height"]),
        float(ground.get("rx", 0)),
        role,
        starts,
        ends,
    )


def ground_path(piece: GroundPiece, top: float) -> str:
    """A ground's piece as SVG path data, on a line whose top lies at `top`: a rectangle
    whose corners are rounded by its radius, at most half its height or its width, where
    the ground starts and where it ends, and square where a line breaks it. Its moves,
    lines, cubic curves and closes are absolute, as an outline the engine maps is."""
    left, right = piece.left, piece.right
    upper, lower = top + piece.top, top + piece.top + piece.height
    radius = max(min(piece.rx, piece.height / 2, (right - left) / 2), 0.0)
    before = radius if piece.starts else 0.0
    after = radius if piece.ends else 0.0
    words = ["M", number(left + before), number(upper), "L", number(right - after), number(upper)]
    if after:
        k = after * KAPPA
        words += ["C", number(right - after + k), number(upper), number(right)]
        words += [number(upper + after - k), number(right), number(upper + after)]
    words += ["L", number(right), number(lower - after)]
    if after:
        k = after * KAPPA
        words += ["C", number(right), number(lower - after + k), number(right - after + k)]
        words += [number(lower), number(right - after), number(lower)]
    words += ["L", number(left + before), number(lower)]
    if before:
        k = before * KAPPA
        words += ["C", number(left + before - k), number(lower), number(left)]
        words += [number(lower - before + k), number(left), number(lower - before)]
    words += ["L", number(left), number(upper + before)]
    if before:
        k = before * KAPPA
        words += ["C", number(left), number(upper + before - k), number(left + before - k)]
        words += [number(upper), number(left + before), number(upper)]
    return " ".join([*words, "Z"])


def find(elements: list[Mapping[str, Any]], trace: str) -> Mapping[str, Any] | None:
    """The element of the trace id `trace`, in the tree under `elements`."""
    stack = list(reversed(elements))
    while stack:
        element = stack.pop()
        if element.get("id") == trace:
            return element
        stack.extend(reversed(element.get("children", [])))
    return None


class Canvas:
    """Draws the pages of one scene in one combination for the renderer `declaration`
    declares, collecting the losses."""

    def __init__(
        self,
        declaration: Mapping[str, Any],
        scene: Mapping[str, Any],
        key: str,
        colours: Mapping[str, Mapping[str, Any]],
        font_file: Callable[[str], Path],
        pictures: Mapping[str, seam.Shown],
    ) -> None:
        self.declaration = declaration
        self.scene = scene
        self.key = key
        self.colours = colours
        self.font_file = font_file
        self.pictures = pictures
        self.losses: list[seam.Loss] = []
        self._faces: dict[tuple[str, int], set[str]] = {}
        # Each arrowhead marker the page draws, by its id: which end, its colour, opacity.
        self._arrows: dict[str, tuple[str, str, str | None]] = {}

    def _lose(self, what: str, did: str, why: str) -> None:
        loss = seam.Loss(self.declaration["name"], what, did, why)
        if loss not in self.losses:
            self.losses.append(loss)

    # -- a page

    def page(self, element: Mapping[str, Any]) -> str:
        self._faces = {}
        self._arrows = {}
        body = "".join(self._element(child) for child in element.get("children", []))
        width, height = number(element["width"]), number(element["height"])
        renderer = f"{self.declaration['name']} {self.declaration['version']}"
        head = attribute_text(
            [
                ("xmlns", "http://www.w3.org/2000/svg"),
                ("width", width),
                ("height", height),
                ("viewBox", f"0 0 {width} {height}"),
                ("data-piece", self.scene.get("piece")),
                ("data-page", element["id"]),
                ("data-language", self.scene.get("language")),
                ("data-key", self.key),
                ("data-renderer", renderer),
            ]
        )
        group = attribute_text(
            [
                ("data-id", element["id"]),
                ("data-component", element.get("component")),
                ("data-version", element.get("version")),
            ]
        )
        style = f"<style>{self._font_faces()}text{{white-space:pre}}</style>"
        defs = f"{style}{self._rules()}{self._arrow_markers()}"
        return f"<svg {head}><defs>{defs}</defs><g {group}>{body}</g></svg>\n"

    def _rules(self) -> str:
        """What the page's `<defs>` holds after its style, before its arrowheads: nothing here.
        A subclass that repaints the page by a rule of its own writes that rule here, once the
        page's elements are drawn."""
        return ""

    def _element(self, element: Mapping[str, Any]) -> str:
        kind = element.get("type")
        if kind not in self.declaration["draws"]:
            name = self.declaration["name"]
            self._lose(element["id"], seam.REFUSED, f"the {name} renderer draws no `{kind}`")
            return ""
        return getattr(self, f"_{kind}")(element)

    # -- the primitives

    def _group(self, element: Mapping[str, Any]) -> str:
        inner = "".join(self._element(child) for child in element.get("children", []))
        x, y = float(element.get("x", 0)), float(element.get("y", 0))
        moved = f"translate({number(x)},{number(y)})" if x or y else None
        attributes = attribute_text(
            [
                ("data-id", element["id"]),
                ("data-component", element.get("component")),
                ("data-version", element.get("version")),
                ("transform", moved),
            ]
        )
        return f"<g {attributes}>{inner}</g>"

    def _paint(self, element: Mapping[str, Any], prop: str) -> list[tuple[str, Any]]:
        """The paint `prop` of `element`, as `_paint_attributes` writes it. A role with no
        colour in this combination is a loss, and draws as no role does."""
        role = element.get(prop)
        if role is not None and self.colours.get(role) is None:
            self._lose(
                element["id"],
                seam.LEFT_OUT,
                f"the brand gives the role `{role}` of its {prop} no colour in `{self.key}`",
            )
            role = None
        return self._paint_attributes(prop, role)

    def _paint_attributes(self, prop: str, role: str | None) -> list[tuple[str, Any]]:
        """How a paint is written: the attributes of `role`'s colour in this combination.
        With no `role`, a fill of none, and nothing for a stroke."""
        if role is None:
            return [(prop, "none")] if prop == "fill" else []
        text, alpha = colour_text(self.colours[role])
        return [(prop, text), (f"{prop}-opacity", number(alpha) if alpha < 1 else None)]

    def _stroke(self, element: Mapping[str, Any]) -> list[tuple[str, Any]]:
        stroke = self._paint(element, "stroke")
        if stroke and "stroke-width" in element:
            stroke.append(("stroke-width", number(element["stroke-width"])))
        return stroke

    def _box(self, element: Mapping[str, Any]) -> str:
        # The stroke is drawn inside the frame: the box is inset by half its width.
        inset = float(element.get("stroke-width", 1)) / 2 if element.get("stroke") else 0.0
        x, y = float(element["x"]) + inset, float(element["y"]) + inset
        width = max(float(element["width"]) - 2 * inset, 0.0)
        height = max(float(element["height"]) - 2 * inset, 0.0)
        rx = element.get("rx")
        attributes = attribute_text(
            [
                ("data-id", element["id"]),
                ("x", number(x)),
                ("y", number(y)),
                ("width", number(width)),
                ("height", number(height)),
                ("rx", number(rx) if rx else None),
                *self._paint(element, "fill"),
                *self._stroke(element),
            ]
        )
        return f"<rect {attributes}/>"

    def _ellipse(self, element: Mapping[str, Any]) -> str:
        width, height = float(element["width"]), float(element["height"])
        attributes = attribute_text(
            [
                ("data-id", element["id"]),
                ("cx", number(float(element["x"]) + width / 2)),
                ("cy", number(float(element["y"]) + height / 2)),
                ("rx", number(width / 2)),
                ("ry", number(height / 2)),
                *self._paint(element, "fill"),
                *self._stroke(element),
            ]
        )
        return f"<ellipse {attributes}/>"

    def _path(self, element: Mapping[str, Any]) -> str:
        """A path, such as a concept's sign (DEC-036 point 1): the outline the engine mapped
        into its frame, filled by its rule. A path that holds no outline is refused, as an
        element the renderer does not draw is."""
        outline = element.get("d")
        if not isinstance(outline, str) or not outline:
            self._lose(element["id"], seam.REFUSED, "the path holds no outline, `d`")
            return ""
        rule = element.get("fill-rule")
        attributes = attribute_text(
            [
                ("data-id", element["id"]),
                ("d", outline),
                ("fill-rule", rule if rule == "evenodd" else None),
                *self._paint(element, "fill"),
                *self._stroke(element),
            ]
        )
        return f"<path {attributes}/>"

    def _line(self, element: Mapping[str, Any]) -> str:
        """A line, or a tie's connector: a `<polyline>` through its points where its route
        turns, which names the elements its ends meet (`data-start`, `data-end`). An
        arrowhead is a marker in the line's stroke colour. A line that holds neither its
        ends nor its points is refused, as an element the renderer does not draw is."""
        points = element.get("points")
        if not points and any(end not in element for end in ENDS_OF_LINE):
            self._lose(
                element["id"],
                seam.REFUSED,
                f"the line holds neither its ends, `{' '.join(ENDS_OF_LINE)}`, nor its points",
            )
            return ""
        attached = element.get("attached") or {}
        stroke = self._stroke(element)
        shape = (
            [("points", " ".join(f"{number(p['x'])},{number(p['y'])}" for p in points))]
            if points
            else [(end, number(element[end])) for end in ENDS_OF_LINE]
        )
        attributes = attribute_text(
            [
                ("data-id", element["id"]),
                *((f"data-{which}", attached[which]["id"]) for which in ENDS if which in attached),
                *shape,
                *(self._paint_attributes("fill", None) if points else []),
                *stroke,
                *self._markers(element, stroke),
            ]
        )
        return f"<polyline {attributes}/>" if points else f"<line {attributes}/>"

    def _markers(
        self, element: Mapping[str, Any], stroke: list[tuple[str, Any]]
    ) -> list[tuple[str, Any]]:
        """The arrowheads a line draws, each a marker the page defines once for its colour.
        A line with no stroke draws none."""
        paint = dict(stroke)
        if "stroke" not in paint:
            return []
        found = []
        for which in ENDS:
            if element.get(f"marker-{which}") == "arrow":
                colour, alpha = paint["stroke"], paint.get("stroke-opacity")
                key = f"{which}-{colour.lstrip('#')}" + (f"-{alpha}" if alpha else "")
                marker = f"pkit-arrow-{key.replace('.', '')}"
                self._arrows[marker] = (which, colour, alpha)
                found.append((f"marker-{which}", f"url(#{marker})"))
        return found

    def _text(self, element: Mapping[str, Any]) -> str:
        x, width = float(element["x"]), float(element["width"])
        anchor = element.get("text-anchor", "start")
        before = ANCHORED.get(anchor, 0.0)
        at = x + before * width
        paragraphs = element.get("paragraphs") or [[{}]]
        first = paragraphs[0][0] if paragraphs[0] else {}
        lines, marks = [], []
        for baseline, line, spans in self._text_lines(element, float(element["y"])):
            where = placed(spans, at - before * float(line["width"]))
            if marked(line):
                marks.append(self._marks(element, baseline - float(line["baseline"]), where))
            drawn = []
            for (span, run), pen in zip(spans, where.starts, strict=True):
                shown = escape(span["text"], quote=False)
                look = [*self._span_place(line, pen), *self._look(element, run, first)]
                drawn.append(f"<tspan {attribute_text(look)}>{shown}</tspan>" if look else shown)
            # On a line that holds a sign or a ground each span is placed at its own start,
            # anchored there.
            restart = marked(line) and anchor != "start"
            place = [
                ("x", number(at)),
                ("y", number(baseline)),
                ("text-anchor", "start" if restart else None),
            ]
            lines.append(f"<tspan {attribute_text(place)}>{''.join(drawn)}</tspan>")
        weight = first.get("font-weight")
        attributes = attribute_text(
            [
                ("data-id", element["id"]),
                ("xml:space", "preserve"),
                ("font-family", font_families(first)),
                ("font-size", number(first.get("font-size", 0))),
                ("font-weight", weight if weight not in (None, NORMAL) else None),
                ("text-anchor", anchor if anchor != "start" else None),
                *self._paint({"id": element["id"], "fill": first.get("fill")}, "fill"),
            ]
        )
        return f"{''.join(marks)}<text {attributes}>{''.join(lines)}</text>"

    def _marks(self, element: Mapping[str, Any], top: float, where: Placed) -> str:
        """The grounds and the signs of a line whose top lies at `top`, drawn before its
        text, so behind it (DEC-036 point 3). A ground's piece is a path in its role; a sign
        is its outline, moved to its square's place and filled by its rule in its run's
        paint. Each names its text's trace id, as `data-ground` and `data-sign`."""
        drawn = []
        for piece in where.grounds:
            if piece.role is None:
                continue
            attributes = attribute_text(
                [
                    ("data-ground", element["id"]),
                    ("d", ground_path(piece, top)),
                    *self._paint({"id": element["id"], "fill": piece.role}, "fill"),
                ]
            )
            drawn.append(f"<path {attributes}/>")
        for left, span, run in where.signs:
            sign = span["sign"]
            moved = f"translate({number(left)},{number(top + float(sign['top']))})"
            rule = sign.get("fill-rule")
            attributes = attribute_text(
                [
                    ("data-sign", element["id"]),
                    ("d", sign["d"]),
                    ("transform", moved),
                    ("fill-rule", rule if rule == "evenodd" else None),
                    *self._paint({"id": element["id"], "fill": run.get("fill")}, "fill"),
                ]
            )
            drawn.append(f"<path {attributes}/>")
        return "".join(drawn)

    def _text_lines(
        self, element: Mapping[str, Any], top: float
    ) -> list[tuple[float, Mapping[str, Any], Spans]]:
        """Each line of a text whose top lies at `top`: its baseline, the line, and each of
        its spans with its run. Records what each span draws under the faces of its run."""
        step = float(element["line-height"])
        paragraphs = element.get("paragraphs") or [[{}]]
        for runs in paragraphs:
            for run in runs:
                for face in run.get("fonts", []):
                    self._faces.setdefault(self._face(face, run), set())
        lines = []
        for index, line in enumerate(element.get("lines", [])):
            runs = paragraphs[line.get("paragraph", 0)]
            spans = [(span, runs[span["run"]]) for span in line.get("spans", [])]
            for span, run in spans:
                for face in run.get("fonts", []):
                    self._faces[self._face(face, run)].update(span["text"])
            lines.append((top + float(line["baseline"]) + index * step, line, spans))
        return lines

    def _span_place(self, line: Mapping[str, Any], pen: float) -> list[tuple[str, Any]]:
        """The attributes that place a span of `line`, which the engine's widths start at
        `pen`. On a line that holds a sign or a ground, the span starts there, so the room the
        engine gave them lies before it, and its line anchors it at its start (DEC-036 point
        3). None on any other line: a span follows the one before it."""
        return [("x", number(pen))] if marked(line) else []

    def _face(self, face: Mapping[str, Any], run: Mapping[str, Any]) -> tuple[str, int]:
        """The `@font-face` a run draws a font in: its family, at the run's weight."""
        weight = run.get("font-weight")
        return face["family"], int(weight) if isinstance(weight, (int, float)) else NORMAL

    def _look(
        self, element: Mapping[str, Any], run: Mapping[str, Any], first: Mapping[str, Any]
    ) -> list[tuple[str, Any]]:
        """The font and the paint of a run that looks otherwise than the text's first run,
        each written whole; none where it looks the same."""
        keys = ("font-family", "font-size", "font-weight", "fill")
        if all(run.get(key) == first.get(key) for key in keys):
            return []
        weight = run.get("font-weight")
        paint = [
            # the text's own opacity is not the run's
            ("fill-opacity", "1") if name == "fill-opacity" and value is None else (name, value)
            for name, value in self._paint({"id": element["id"], "fill": run.get("fill")}, "fill")
        ]
        return [
            ("font-family", font_families(run)),
            ("font-size", number(run.get("font-size", 0))),
            ("font-weight", weight if weight is not None else NORMAL),
            *paint,
        ]

    def _image(self, element: Mapping[str, Any]) -> str:
        """An image, its picture embedded whole as the data of its kind. One handed no
        picture in this combination is left out, and reported."""
        shown = self.pictures.get(str(element["id"]))
        if shown is None or not shown.file.is_file():
            why = unshown(element, self.key, self.scene.get("piece"))
            self._lose(element["id"], seam.LEFT_OUT, why)
            return ""
        return self._picture(element, shown)

    def _picture(
        self, element: Mapping[str, Any], shown: seam.Shown, *more: tuple[str, Any]
    ) -> str:
        """An image drawn as the picture `shown`, embedded whole as the data of its kind, with
        `more` attributes after its trace id."""
        data = base64.b64encode(shown.file.read_bytes()).decode("ascii")
        attributes = attribute_text(
            [
                ("data-id", element["id"]),
                *more,
                ("x", number(element["x"])),
                ("y", number(element["y"])),
                ("width", number(element["width"])),
                ("height", number(element["height"])),
                ("preserveAspectRatio", element.get("preserveAspectRatio")),
                ("href", f"data:{MEDIA[shown.kind]};base64,{data}"),
            ]
        )
        return f"<image {attributes}/>"

    # -- arrowheads

    def _arrow_markers(self) -> str:
        """The arrowhead markers the page draws, in the order of their ids: a triangle as
        long as five strokes are wide, its tip at the line's end, pointing away from the
        line."""
        return "".join(
            self._marker(marker, which, [("fill", colour), ("fill-opacity", alpha)])
            for marker, (which, colour, alpha) in sorted(self._arrows.items())
        )

    def _marker(self, marker: str, which: str, paint: list[tuple[str, Any]]) -> str:
        """The arrowhead marker `marker` at the end `which`, its triangle painted by `paint`."""
        tip, shape = ("10", "M0,0L10,5L0,10z") if which == "end" else ("0", "M10,0L0,5L10,10z")
        attributes = attribute_text(
            [
                ("id", marker),
                ("viewBox", "0 0 10 10"),
                ("refX", tip),
                ("refY", "5"),
                ("markerWidth", "5"),
                ("markerHeight", "5"),
                ("orient", "auto"),
            ]
        )
        return f"<marker {attributes}><path {attribute_text([('d', shape), *paint])}/></marker>"

    # -- fonts

    def _font_faces(self) -> str:
        """The `@font-face` rules of the faces `self._faces` holds, each subset to the
        characters drawn in it."""
        faces = []
        for family, weight in sorted(self._faces):
            characters = "".join(sorted(self._faces[(family, weight)]))
            data, form, mime = _subset(self.font_file(family), characters)
            faces.append(
                f"@font-face{{font-family:{css_string(family)};font-weight:{weight};"
                f"src:url(data:{mime};base64,{data}) format('{form}');}}"
            )
        return "".join(faces)


_SUBSETS: dict[tuple[str, str], tuple[str, str, str]] = {}


def _subset(path: Path, characters: str) -> tuple[str, str, str]:
    """A font file subset to `characters`, base64, with its format and media type. Raises
    `UnreadableFont` where it cannot be read as a font, which measuring, reading only some of
    its tables, may not have found."""
    mark = (str(path), characters)
    if mark not in _SUBSETS:
        out = io.BytesIO()
        try:
            font = TTFont(str(path), recalcTimestamp=False)
            options = subset.Options()
            options.layout_features = ["*"]
            options.name_IDs = ["*"]
            options.notdef_outline = True
            subsetter = subset.Subsetter(options)
            subsetter.populate(text=characters + " ")
            subsetter.subset(font)
            font.save(out)
            font.close()
        except Exception as exc:  # the font library has no one error for a file it cannot read
            raise UnreadableFont(path, exc) from exc
        form, mime = (
            ("opentype", "font/otf") if font.sfntVersion == "OTTO" else ("truetype", "font/ttf")
        )
        _SUBSETS[mark] = (base64.b64encode(out.getvalue()).decode("ascii"), form, mime)
    return _SUBSETS[mark]
