"""The SVG renderer: a scene drawn as SVG files, one for each page, language and
combination of modes (visual-communication DEC-005 points 4, 5, 9 and 10).

- **What it draws** is its declaration (`svg_declaration.py`): every primitive of format
  1's scene but the path. It draws only what it declares, so the losses the capability
  reads from the declaration before it runs are the ones it makes.
- **Colours** stay roles in the scene. The renderer takes each from the brand's resolved
  values in the combination it draws (`colours`), as `#rrggbb` with an opacity where the
  colour is translucent. A role with no colour there is left out, and reported.
- **Fonts** are embedded as `@font-face` from the brand's committed files, never the
  machine's: each family's file subset to the characters the page draws in it.
- **Text** is drawn as the engine measured it: each of its lines as given, at its
  baseline, anchored at the start, the middle or the end of the text's width.
- **A produced picture** is embedded as the variant that serves the combination drawn;
  where the record maps the combination to none, the picture is left out, and reported.
- **Every element carries its trace id** (`data-id`), and a group the component that drew
  it (`data-component`) with its library's version (`data-version`), the page's own group
  included, so a reader of the file finds where each element came from.

Output is fixed for a version: lengths are written to 1/100 px, attributes in one order,
so the same scene and values give the same bytes. A change that could give another output
raises the version, and the reference outputs pinned to it in the tests catch one made
without it (DEC-005 point 9).
"""

from __future__ import annotations

import base64
import io
import logging
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Any

from fontTools import subset
from fontTools.ttLib import TTFont

from _lib.plugins import seam
from _lib.plugins.svg_declaration import DECLARATION

NAME: str = DECLARATION["name"]
VERSION: str = DECLARATION["version"]

#: The weight a text without one is drawn in.
NORMAL = 400

logging.getLogger("fontTools.subset").setLevel(logging.ERROR)


@dataclass(frozen=True)
class Page:
    """One page drawn: its trace id and its SVG text."""

    id: str
    svg: str


@dataclass(frozen=True)
class Drawn:
    """What one scene drawn in one combination gives: its pages, and what the renderer
    could not draw as given."""

    pages: list[Page]
    losses: list[seam.Loss]


def render(
    scene: Mapping[str, Any],
    *,
    key: str,
    colours: Mapping[str, Mapping[str, Any]],
    font_file: Callable[[str], Path],
    pictures: Mapping[str, Path],
) -> Drawn:
    """`scene` (`Scene.to_dict()`) drawn in the combination `key`: `colours` gives each
    colour role's value there, in canonical form; `font_file` the committed file of a font
    family; `pictures` the file of each produced output's variant that serves `key`."""
    canvas = _Canvas(scene, key, colours, font_file, pictures)
    pages = []
    for trace in scene.get("pages", []):
        element = _find(scene.get("children", []), trace)
        if element is not None:
            pages.append(Page(trace, canvas.page(element)))
    return Drawn(pages, canvas.losses)


def colour_text(value: Mapping[str, Any]) -> tuple[str, float]:
    """A colour in canonical form as `#rrggbb`, each component rounded to 8 bits half up,
    and its alpha."""
    channels = "".join(f"{int(float(c) * 255 + 0.5):02x}" for c in value["components"])
    return f"#{channels}", float(value.get("alpha", 1))


def number(value: Any) -> str:
    """A number as SVG holds it: to 1/100, with no trailing zero and no negative zero."""
    rounded = round(float(value), 2) + 0.0
    if rounded == int(rounded):
        return str(int(rounded))
    return f"{rounded:.2f}".rstrip("0")


def _find(elements: list[Mapping[str, Any]], trace: str) -> Mapping[str, Any] | None:
    stack = list(reversed(elements))
    while stack:
        element = stack.pop()
        if element.get("id") == trace:
            return element
        stack.extend(reversed(element.get("children", [])))
    return None


def _attributes(pairs: list[tuple[str, Any]]) -> str:
    return " ".join(f'{name}="{_attribute(value)}"' for name, value in pairs if value is not None)


def _attribute(value: Any) -> str:
    """A value as the text of an attribute between double quotes."""
    return escape(str(value), quote=False).replace('"', "&quot;")


class _Canvas:
    """Draws the pages of one scene in one combination, collecting the losses."""

    def __init__(
        self,
        scene: Mapping[str, Any],
        key: str,
        colours: Mapping[str, Mapping[str, Any]],
        font_file: Callable[[str], Path],
        pictures: Mapping[str, Path],
    ) -> None:
        self.scene = scene
        self.key = key
        self.colours = colours
        self.font_file = font_file
        self.pictures = pictures
        self.losses: list[seam.Loss] = []
        self._faces: dict[tuple[str, int], set[str]] = {}

    def _lose(self, what: str, did: str, why: str) -> None:
        loss = seam.Loss(NAME, what, did, why)
        if loss not in self.losses:
            self.losses.append(loss)

    # -- a page

    def page(self, element: Mapping[str, Any]) -> str:
        self._faces = {}
        body = "".join(self._element(child) for child in element.get("children", []))
        width, height = number(element["width"]), number(element["height"])
        head = _attributes(
            [
                ("xmlns", "http://www.w3.org/2000/svg"),
                ("width", width),
                ("height", height),
                ("viewBox", f"0 0 {width} {height}"),
                ("data-piece", self.scene.get("piece")),
                ("data-page", element["id"]),
                ("data-language", self.scene.get("language")),
                ("data-key", self.key),
                ("data-renderer", f"{NAME} {VERSION}"),
            ]
        )
        group = _attributes(
            [
                ("data-id", element["id"]),
                ("data-component", element.get("component")),
                ("data-version", element.get("version")),
            ]
        )
        style = f"<style>{self._font_faces()}text{{white-space:pre}}</style>"
        return f"<svg {head}><defs>{style}</defs><g {group}>{body}</g></svg>\n"

    def _element(self, element: Mapping[str, Any]) -> str:
        kind = element.get("type")
        if kind not in DECLARATION["draws"]:
            self._lose(element["id"], seam.REFUSED, f"the {NAME} renderer draws no `{kind}`")
            return ""
        return getattr(self, f"_{kind}")(element)

    # -- the primitives

    def _group(self, element: Mapping[str, Any]) -> str:
        inner = "".join(self._element(child) for child in element.get("children", []))
        x, y = float(element.get("x", 0)), float(element.get("y", 0))
        moved = f"translate({number(x)},{number(y)})" if x or y else None
        attributes = _attributes(
            [
                ("data-id", element["id"]),
                ("data-component", element.get("component")),
                ("data-version", element.get("version")),
                ("transform", moved),
            ]
        )
        return f"<g {attributes}>{inner}</g>"

    def _paint(self, element: Mapping[str, Any], prop: str) -> list[tuple[str, Any]]:
        role = element.get(prop)
        if role is None:
            return [(prop, "none")] if prop == "fill" else []
        value = self.colours.get(role)
        if value is None:
            self._lose(
                element["id"],
                seam.LEFT_OUT,
                f"the brand gives the role `{role}` of its {prop} no colour in `{self.key}`",
            )
            return [(prop, "none")] if prop == "fill" else []
        text, alpha = colour_text(value)
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
        attributes = _attributes(
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
        attributes = _attributes(
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
        attributes = _attributes(
            [
                ("data-id", element["id"]),
                *((end, number(element[end])) for end in ("x1", "y1", "x2", "y2")),
                *self._stroke(element),
            ]
        )
        return f"<line {attributes}/>"

    def _text(self, element: Mapping[str, Any]) -> str:
        x, width = float(element["x"]), float(element["width"])
        anchor = element.get("text-anchor", "start")
        at = {"start": x, "middle": x + width / 2, "end": x + width}.get(anchor, x)
        top = float(element["y"]) + float(element["baseline"])
        step = float(element["line-height"])
        weight = element.get("font-weight")
        families = list(element.get("font-family", []))
        drawn = "".join(line["text"] for line in element.get("lines", []))
        for face in element.get("fonts", []):
            mark = (face["family"], int(weight) if isinstance(weight, (int, float)) else NORMAL)
            self._faces.setdefault(mark, set()).update(drawn)
        spans = "".join(
            f"<tspan {_attributes([('x', number(at)), ('y', number(top + index * step))])}>"
            f"{escape(line['text'], quote=False)}</tspan>"
            for index, line in enumerate(element.get("lines", []))
        )
        attributes = _attributes(
            [
                ("data-id", element["id"]),
                ("xml:space", "preserve"),
                ("font-family", ", ".join(f"'{family}'" for family in families)),
                ("font-size", number(element["font-size"])),
                ("font-weight", weight if weight not in (None, NORMAL) else None),
                ("text-anchor", anchor if anchor != "start" else None),
                *self._paint(element, "fill"),
            ]
        )
        return f"<text {attributes}>{spans}</text>"

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
        attributes = _attributes(
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

    # -- fonts

    def _font_faces(self) -> str:
        faces = []
        for family, weight in sorted(self._faces):
            characters = "".join(sorted(self._faces[(family, weight)]))
            data, form, mime = _subset(self.font_file(family), characters)
            faces.append(
                f"@font-face{{font-family:'{family}';font-weight:{weight};"
                f"src:url(data:{mime};base64,{data}) format('{form}');}}"
            )
        return "".join(faces)


_SUBSETS: dict[tuple[str, str], tuple[str, str, str]] = {}


def _subset(path: Path, characters: str) -> tuple[str, str, str]:
    """A font file subset to `characters`, base64, with its format and media type."""
    mark = (str(path), characters)
    if mark not in _SUBSETS:
        font = TTFont(str(path), recalcTimestamp=False)
        options = subset.Options()
        options.layout_features = ["*"]
        options.name_IDs = ["*"]
        options.notdef_outline = True
        subsetter = subset.Subsetter(options)
        subsetter.populate(text=characters + " ")
        subsetter.subset(font)
        out = io.BytesIO()
        font.save(out)
        font.close()
        form, mime = (
            ("opentype", "font/otf") if font.sfntVersion == "OTTO" else ("truetype", "font/ttf")
        )
        _SUBSETS[mark] = (base64.b64encode(out.getvalue()).decode("ascii"), form, mime)
    return _SUBSETS[mark]
