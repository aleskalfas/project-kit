"""The canvas: a scene projected onto a page, and written as SVG (visual-communication DEC-005
points 4, 5, 9 and 10).

The SVG renderer (`plugins/svg.py`) draws through it. A second renderer subclasses it, and
replaces only what differs from SVG, each in a method of its own:

- **How a paint is written:** `_paint_attributes`. Which colour a role takes, and the loss of
  a role with none, stay here.
- **The arrow markers:** `_markers`, which keys them on the colour a stroke is written in, so
  a subclass that writes a paint otherwise replaces it too. `_arrow_markers` defines what it
  recorded.
- **The font faces:** `_font_faces`, which writes those of a page. A text records what it
  draws in each, whichever writes them.
- **A span's placing:** `_span_place`. Where the engine's widths start a span stays here.
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
- **A line** whose route turns, a tie's connector, is a `<polyline>` through its points,
  and names the elements its ends meet (`data-start`, `data-end`). An arrowhead is a
  marker the page defines once for each colour a line draws one in. A line that holds
  neither its ends nor its points is refused, and left out.
- **A produced picture** is embedded as the variant that serves the combination drawn;
  where the record maps the combination to none, the picture is left out, and reported.
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
from collections.abc import Callable, Mapping
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

#: The spans of a line, each with the run it is part of.
Spans = list[tuple[Mapping[str, Any], Mapping[str, Any]]]

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
        pictures: Mapping[str, Path],
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
        defs = f"{style}{self._arrow_markers()}"
        return f"<svg {head}><defs>{defs}</defs><g {group}>{body}</g></svg>\n"

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
        lines = []
        for baseline, line, spans in self._text_lines(element, float(element["y"])):
            pen = at - before * float(line["width"])
            drawn = []
            for span, run in spans:
                shown = escape(span["text"], quote=False)
                look = [*self._span_place(line, pen), *self._look(element, run, first)]
                drawn.append(f"<tspan {attribute_text(look)}>{shown}</tspan>" if look else shown)
                pen += float(span["width"])
            place = [("x", number(at)), ("y", number(baseline))]
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
        return f"<text {attributes}>{''.join(lines)}</text>"

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
        `pen`. None here: a span follows the one before it."""
        return []

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
        paint = self._paint({"id": element["id"], "fill": run.get("fill")}, "fill")
        if len(paint) == 2 and paint[1][1] is None:
            paint[1] = ("fill-opacity", "1")  # the text's own opacity is not the run's
        return [
            ("font-family", font_families(run)),
            ("font-size", number(run.get("font-size", 0))),
            ("font-weight", weight if weight is not None else NORMAL),
            *paint,
        ]

    def _image(self, element: Mapping[str, Any]) -> str:
        output = element.get("output")
        path = self.pictures.get(str(output))
        if path is None or not path.is_file():
            self._lose(
                element["id"],
                seam.LEFT_OUT,
                f"the produced output `{output}` has no variant for `{self.key}`: run "
                f"`pkit visual produce {self.scene.get('piece')} {output}`",
            )
            return ""
        data = base64.b64encode(path.read_bytes()).decode("ascii")
        attributes = attribute_text(
            [
                ("data-id", element["id"]),
                ("x", number(element["x"])),
                ("y", number(element["y"])),
                ("width", number(element["width"])),
                ("height", number(element["height"])),
                ("preserveAspectRatio", element.get("preserveAspectRatio")),
                ("href", f"data:image/png;base64,{data}"),
            ]
        )
        return f"<image {attributes}/>"

    # -- arrowheads

    def _arrow_markers(self) -> str:
        """The arrowhead markers the page draws, in the order of their ids: a triangle as
        long as five strokes are wide, its tip at the line's end, pointing away from the
        line."""
        markers = []
        for marker, (which, colour, alpha) in sorted(self._arrows.items()):
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
            fill = attribute_text([("d", shape), ("fill", colour), ("fill-opacity", alpha)])
            markers.append(f"<marker {attributes}><path {fill}/></marker>")
        return "".join(markers)

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
