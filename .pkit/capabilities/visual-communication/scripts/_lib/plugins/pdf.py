"""The PDF renderer: a scene drawn as one PDF file, its pages in order, for each language
and combination of modes (visual-communication DEC-005 points 4, 5, 9 and 10, DEC-006
point 7).

- **What it draws** is its declaration (`pdf_declaration.py`): every primitive of format
  1's scene but the path and the image. It draws only what it declares, so the losses the
  capability reads from the declaration before it runs are the ones it makes.
- **Pages.** Each page of the scene, in the scene's order, is a page of the file, as large
  as the page's frame. Each px of the scene is 0.75 pt of the page, CSS's 96 px to the
  inch, as the declaration's `unit` says.
- **Colours** stay roles in the scene. The renderer takes each from the brand's resolved
  values in the combination it draws (`colours`), as DeviceRGB, with an opacity where the
  colour is translucent. A role with no colour there is left out, and reported.
- **Fonts** are embedded from the brand's committed files, never the machine's: each
  family a run draws in once in the file, as a CID-keyed font (Type 0, `Identity-H`), its
  program subset to the glyphs the file draws in it, with a map from each glyph back to the
  characters it stands for (`ToUnicode`), so the text can be searched and copied. A CFF
  font's program is embedded as CFF, a TrueType font's as TrueType. A family's name is
  written as a PDF name (`pdf_name`), so no name a brand gives can end the dictionary that
  holds it, or leave the file malformed.
- **Text** is drawn as the engine measured it: each of its lines as given, at its own
  baseline, anchored at the start, the middle or the end of the text's width, each span in
  its run's font, size and paint (DEC-012). Each span is shaped again with HarfBuzz from
  the committed file, in pieces of one font each, as the engine shaped it (DEC-005 point
  4), and its glyphs are placed at the advances shaped.
- **A line**, or a tie's connector through each of its points, is stroked as the SVG
  renderer strokes it; an arrowhead is the triangle it draws, five strokes long, its tip
  at the line's end, in the line's stroke. A line that holds neither its ends nor its
  points is refused, and left out.
- **Shapes.** A box's stroke lies inside its frame. Rounded corners and ellipses are cubic
  Bézier curves.

Output is fixed for a version: lengths are written to 1/100 px and colours to 1/10 000,
objects in one order, the streams uncompressed, with no date and no random id: the file's
`/ID` is taken from its own bytes. So the same scene and values give the same bytes on
every machine. A change that could give another output raises the version, and the
reference outputs pinned to it in the tests catch one made without it (DEC-005 point 9).
"""

from __future__ import annotations

import hashlib
import io
import logging
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import uharfbuzz as hb
from fontTools import subset
from fontTools.ttLib import TTFont

from _lib.plugins import seam
from _lib.plugins.pdf_declaration import DECLARATION

NAME: str = DECLARATION["name"]
VERSION: str = DECLARATION["version"]

#: How many pt of the page each px of the scene is (the declaration's `unit`).
SCALE: float = DECLARATION["unit"]["scale"]

#: A line's two ends, each of which may carry an arrowhead.
ENDS = ("start", "end")

#: Where a line's two ends lie, as a scene holds them.
ENDS_OF_LINE = ("x1", "y1", "x2", "y2")

#: Where the control points of a quarter of an ellipse lie, drawn as one cubic Bézier
#: curve, as a share of its radius.
KAPPA = 0.5522847498307936

#: How the file opens: its version, then a comment of four bytes above 127, so that a
#: reader takes it as binary.
HEADER = b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n"

#: The regular characters a PDF name does not hold as themselves.
_DELIMITERS = frozenset(b"()<>[]{}/%#")

#: The width of a font's stems the file declares, in thousandths of an em. A reader uses
#: it only to stand in for a font it lacks, and every font is embedded.
STEM = 80

logging.getLogger("fontTools.subset").setLevel(logging.ERROR)


@dataclass(frozen=True)
class Drawn:
    """What one scene drawn in one combination gives: the PDF file, which holds every
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
    """`scene` (`Scene.to_dict()`) drawn in the combination `key` as one PDF file: `colours`
    gives each colour role's value there, in canonical form; `font_file` the committed file
    of a font family. `pictures`, the file of each produced output's variant, is handed to
    every renderer; this one refuses the image, so it reads none."""
    document = _Document(scene, key, colours, font_file)
    for trace in scene.get("pages", []):
        element = _find(scene.get("children", []), trace)
        if element is not None:
            document.page(element)
    return Drawn(document.written(), document.traces, document.losses)


# --- the PDF's syntax ---------------------------------------------------------------------------


def number(value: Any, places: int = 2) -> str:
    """A number as the file holds it: to `places` decimals, with no trailing zero, no
    exponent and no negative zero."""
    rounded = round(float(value), places) + 0.0
    if rounded == int(rounded):
        return str(int(rounded))
    return f"{rounded:.{places}f}".rstrip("0")


def pdf_name(text: str) -> str:
    """`text` as a PDF name, `/` first: its UTF-8 bytes, each regular character but `#` as
    itself, and every other byte as `#` and its two hexadecimal digits. A name cannot hold
    the byte 0, so U+0000 is written as U+FFFD; a lone surrogate is written as the three
    bytes UTF-8 would give it. So any name reaches the file as one name, and ends no
    dictionary or array it lies in."""
    data = text.replace("\0", "�").encode("utf-8", "surrogatepass")
    return "/" + "".join(
        chr(byte) if 0x21 <= byte <= 0x7E and byte not in _DELIMITERS else f"#{byte:02X}"
        for byte in data
    )


def pdf_string(text: str) -> str:
    """`text` as a PDF literal string, as a text string holds it: its bytes in ASCII, or
    UTF-16BE after its byte order mark where it holds another character; `(`, `)` and `\\`
    with a `\\` before them, and each byte that is not printable ASCII as its octal
    escape."""
    data = (
        text.encode("ascii")
        if text.isascii()
        else b"\xfe\xff" + text.encode("utf-16-be", "surrogatepass")
    )
    out = []
    for byte in data:
        if byte in b"()\\":
            out.append("\\" + chr(byte))
        elif 0x20 <= byte <= 0x7E:
            out.append(chr(byte))
        else:
            out.append(f"\\{byte:03o}")
    return "(" + "".join(out) + ")"


def colour_text(value: Mapping[str, Any]) -> tuple[str, float]:
    """A colour in canonical form as DeviceRGB's three components, each to 1/10 000, and
    its alpha."""
    return " ".join(number(c, 4) for c in value["components"]), float(value.get("alpha", 1))


def _find(elements: Sequence[Mapping[str, Any]], trace: str) -> Mapping[str, Any] | None:
    stack = list(reversed(elements))
    while stack:
        element = stack.pop()
        if element.get("id") == trace:
            return element
        stack.extend(reversed(element.get("children", [])))
    return None


def _point(x: float, y: float) -> str:
    return f"{number(x)} {number(y)}"


# --- fonts --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Glyph:
    """One glyph shaped: its id in the font file, how far it moves the pen and how far it
    is moved from the pen, in the font's units, and the characters it stands for, empty
    where another glyph of its cluster stands for them."""

    id: int
    advance: int
    x_offset: int
    y_offset: int
    text: str


class _Face:
    """One committed font file: its glyphs and metrics, and HarfBuzz's font to shape with
    as the engine shapes (`_lib.text`)."""

    def __init__(self, data: bytes, mark: str) -> None:
        self.data = data
        self.mark = mark
        font = TTFont(io.BytesIO(data), lazy=True)
        try:
            self.order = font.getGlyphOrder()
            self.cmap = frozenset(font.getBestCmap() or {})
            self.upem = int(font["head"].unitsPerEm)
            metrics = font["hmtx"].metrics
            self.widths = [int(metrics[name][0]) for name in self.order]
            head = font["head"]
            self.bbox = (head.xMin, head.yMin, head.xMax, head.yMax)
            self.ascent = int(font["hhea"].ascent)
            self.descent = int(font["hhea"].descent)
            os2 = font.get("OS/2")
            capital = getattr(os2, "sCapHeight", 0) if os2 is not None and os2.version >= 2 else 0
            self.cap_height = int(capital or self.ascent)
            self.italic = float(font["post"].italicAngle)
            self.fixed = bool(font["post"].isFixedPitch)
            self.outlines = "CFF " if "CFF " in font else "glyf" if "glyf" in font else None
        finally:
            font.close()
        self._font = hb.Font(hb.Face(hb.Blob(data)))
        self._shaped: dict[str, tuple[Glyph, ...]] = {}

    def has(self, character: str) -> bool:
        return ord(character) in self.cmap

    def shape(self, text: str) -> tuple[Glyph, ...]:
        """`text` shaped with the font's default features, as the engine measures it; each
        cluster's characters with its first glyph."""
        if text not in self._shaped:
            buffer = hb.Buffer()
            buffer.add_str(text)
            buffer.guess_segment_properties()
            hb.shape(self._font, buffer)
            starts = sorted({info.cluster for info in buffer.glyph_infos})
            ends = dict(zip(starts, [*starts[1:], len(text)], strict=True))
            seen: set[int] = set()
            glyphs = []
            for info, place in zip(buffer.glyph_infos, buffer.glyph_positions, strict=True):
                cluster = info.cluster
                said = "" if cluster in seen else text[cluster : ends[cluster]]
                seen.add(cluster)
                glyphs.append(
                    Glyph(info.codepoint, place.x_advance, place.x_offset, place.y_offset, said)
                )
            self._shaped[text] = tuple(glyphs)
        return self._shaped[text]


#: Each font file read in this process, by the SHA-256 of its bytes.
_FACES: dict[str, _Face] = {}


def _face(path: Path) -> _Face:
    data = path.read_bytes()
    mark = hashlib.sha256(data).hexdigest()
    if mark not in _FACES:
        _FACES[mark] = _Face(data, mark)
    return _FACES[mark]


@dataclass(frozen=True)
class _Subset:
    """A font's program cut down to some of its glyphs: the program's bytes, and the CID
    each glyph is drawn by."""

    program: bytes
    cids: dict[int, int]


#: Each subset made in this process, by its font's SHA-256 and its glyphs.
_SUBSETS: dict[tuple[str, tuple[int, ...]], _Subset] = {}

#: The tables of a font file a subset keeps: its outlines, CFF or TrueType with the
#: TrueType instructions, and the tables a font file needs whole. Layout, bitmaps, colour
#: and variations are dropped: the glyphs are shaped already, and drawn from their outlines.
KEPT = frozenset(
    ("CFF ", "glyf", "loca", "cvt ", "fpgm", "prep", "head", "hhea", "hmtx", "maxp", "cmap")
) | frozenset(("post", "name", "OS/2"))


def _subset(face: _Face, glyphs: Sequence[int]) -> _Subset:
    """The font's program subset to `glyphs` and `.notdef`, with only the tables of
    `KEPT`. A CFF font gives its CFF table, a TrueType font the whole file. A glyph's CID
    is its place in the subset, or, in a CID-keyed CFF font, its CID there."""
    mark = (face.mark, tuple(sorted(glyphs)))
    if mark not in _SUBSETS:
        font = TTFont(io.BytesIO(face.data), recalcTimestamp=False)
        for tag in [tag for tag in font.reader.tables if tag not in KEPT]:
            del font[tag]
        options = subset.Options()
        options.layout_features = []
        options.notdef_outline = True
        subsetter = subset.Subsetter(options)
        subsetter.populate(glyphs=sorted({face.order[glyph] for glyph in glyphs}))
        subsetter.subset(font)
        order = font.getGlyphOrder()
        if face.outlines == "CFF ":
            keyed = hasattr(font["CFF "].cff.topDictIndex[0], "ROS")
            places = {
                name: int(name[3:]) if keyed and name.startswith("cid") else place
                for place, name in enumerate(order)
            }
            program = font["CFF "].compile(font)
        else:
            places = {name: place for place, name in enumerate(order)}
            out = io.BytesIO()
            font.save(out)
            program = out.getvalue()
        font.close()
        _SUBSETS[mark] = _Subset(program, {glyph: places[face.order[glyph]] for glyph in glyphs})
    return _SUBSETS[mark]


class _Font:
    """A family embedded in one file: its face, the name of its resource, and each glyph
    the file draws in it with the characters it stands for."""

    def __init__(self, family: str, face: _Face, resource: str) -> None:
        self.family = family
        self.face = face
        self.resource = resource
        self.glyphs: set[int] = {0}
        self.text: dict[int, str] = {}
        self.embedded: _Subset | None = None

    def use(self, glyphs: Sequence[Glyph]) -> None:
        for glyph in glyphs:
            self.glyphs.add(glyph.id)
            if glyph.text and glyph.id not in self.text:
                self.text[glyph.id] = glyph.text

    def embed(self) -> _Subset:
        if self.embedded is None:
            self.embedded = _subset(self.face, sorted(self.glyphs))
        return self.embedded

    def width(self, glyph: int) -> str:
        """How far a glyph moves the pen as the file's widths say, in thousandths of an
        em."""
        return number(self.face.widths[glyph] * 1000 / self.face.upem)

    def shown(self, glyphs: Sequence[Glyph], size: float) -> str:
        """`glyphs` as operators that show them at `size`: each glyph by its CID, a `TJ`
        for each run of glyphs at one rise above the baseline, and before a glyph the
        shift that moves the pen from where the file's widths put it to where the glyph was
        shaped."""
        cids = self.embed().cids
        scale = 1000 / self.face.upem
        out: list[str] = []
        array: list[str] = []
        codes: list[str] = []
        rise = 0.0
        shift = 0.0

        def flush_codes() -> None:
            if codes:
                array.append(f"<{''.join(codes)}>")
                codes.clear()

        def flush_array() -> None:
            flush_codes()
            if array:
                out.append(f"[{''.join(array)}] TJ")
                array.clear()

        for glyph in glyphs:
            raised = glyph.y_offset * size / self.face.upem
            if number(raised) != number(rise):
                flush_array()
                out.append(f"{number(raised)} Ts")
                rise = raised
            shift -= glyph.x_offset * scale
            if number(shift) != "0":
                flush_codes()
                array.append(number(shift))
            codes.append(f"{cids[glyph.id]:04X}")
            shift = float(self.width(glyph.id)) + (glyph.x_offset - glyph.advance) * scale
        flush_array()
        if number(rise) != "0":
            out.append("0 Ts")
        return " ".join(out)


@dataclass(frozen=True)
class _Shown:
    """Glyphs of one font at one size, in a page's content, written once the font's
    subset gives their CIDs."""

    font: _Font
    glyphs: tuple[Glyph, ...]
    size: float


#: A part of a page's content: operators, or glyphs written once their font is embedded.
Part = str | _Shown


# --- a document ---------------------------------------------------------------------------------


class _Document:
    """Draws the pages of one scene in one combination into one file, collecting the
    losses, the fonts the pages draw in and the opacities they take."""

    def __init__(
        self,
        scene: Mapping[str, Any],
        key: str,
        colours: Mapping[str, Mapping[str, Any]],
        font_file: Callable[[str], Path],
    ) -> None:
        self.scene = scene
        self.key = key
        self.colours = colours
        self.font_file = font_file
        self.losses: list[seam.Loss] = []
        self.traces: list[str] = []
        self._pages: list[tuple[float, float, list[Part]]] = []
        self._faces: dict[str, _Face] = {}
        self._fonts: dict[str, _Font] = {}
        # Each opacity the pages take, by the operand it sets and its value: its name.
        self._opacities: dict[tuple[str, str], str] = {}

    def _lose(self, what: str, did: str, why: str) -> None:
        loss = seam.Loss(NAME, what, did, why)
        if loss not in self.losses:
            self.losses.append(loss)

    # -- a page

    def page(self, element: Mapping[str, Any]) -> None:
        self.traces.append(element["id"])
        parts = [part for child in element.get("children", []) for part in self._element(child)]
        self._pages.append((float(element["width"]), float(element["height"]), parts))

    def _element(self, element: Mapping[str, Any]) -> list[Part]:
        kind = element.get("type")
        if kind not in DECLARATION["draws"]:
            self._lose(element["id"], seam.REFUSED, f"the {NAME} renderer draws no `{kind}`")
            return []
        return getattr(self, f"_{kind}")(element)

    # -- the primitives

    def _group(self, element: Mapping[str, Any]) -> list[Part]:
        inner = [part for child in element.get("children", []) for part in self._element(child)]
        x, y = float(element.get("x", 0)), float(element.get("y", 0))
        if not inner or (number(x) == "0" and number(y) == "0"):
            return inner
        return [f"q 1 0 0 1 {_point(x, y)} cm\n", *inner, "Q\n"]

    def _paint(self, element: Mapping[str, Any], prop: str) -> tuple[str, float] | None:
        """A paint's colour and alpha; none where it names no role, or a role the brand
        gives no colour in the combination drawn, which is a loss."""
        role = element.get(prop)
        if role is None:
            return None
        value = self.colours.get(role)
        if value is None:
            self._lose(
                element["id"],
                seam.LEFT_OUT,
                f"the brand gives the role `{role}` of its {prop} no colour in `{self.key}`",
            )
            return None
        return colour_text(value)

    def _opacity(self, operand: str, alpha: float) -> str:
        """The operator that sets the opacity of a fill (`ca`) or of a stroke (`CA`)."""
        mark = (operand, number(alpha, 4))
        name = self._opacities.setdefault(mark, f"A{len(self._opacities)}")
        return f"/{name} gs"

    def _shape(self, element: Mapping[str, Any], path: str | None) -> list[Part]:
        """A closed shape filled and stroked as its paints say; nothing where it takes
        neither, or has no `path` since it has no size, its paints still read."""
        fill = self._paint(element, "fill")
        stroke = self._paint(element, "stroke")
        width = float(element.get("stroke-width", 1))
        if width <= 0:
            stroke = None
        if path is None or (fill is None and stroke is None):
            return []
        ops = ["q"]
        if fill is not None:
            ops += [self._opacity("ca", fill[1])] if fill[1] < 1 else []
            ops.append(f"{fill[0]} rg")
        if stroke is not None:
            ops += [self._opacity("CA", stroke[1])] if stroke[1] < 1 else []
            ops += [f"{stroke[0]} RG", f"{number(width)} w"]
        paint = "B" if fill and stroke else "f" if fill else "S"
        return [f"{' '.join(ops)}\n{path}{paint}\nQ\n"]

    def _box(self, element: Mapping[str, Any]) -> list[Part]:
        # The stroke is drawn inside the frame: the box is inset by half its width.
        inset = float(element.get("stroke-width", 1)) / 2 if element.get("stroke") else 0.0
        x, y = float(element["x"]) + inset, float(element["y"]) + inset
        width = max(float(element["width"]) - 2 * inset, 0.0)
        height = max(float(element["height"]) - 2 * inset, 0.0)
        rx = float(element.get("rx") or 0)
        drawn = width > 0 and height > 0
        return self._shape(element, _rectangle(x, y, width, height, rx) if drawn else None)

    def _ellipse(self, element: Mapping[str, Any]) -> list[Part]:
        rx, ry = float(element["width"]) / 2, float(element["height"]) / 2
        cx, cy = float(element["x"]) + rx, float(element["y"]) + ry
        return self._shape(element, _ellipse(cx, cy, rx, ry) if rx > 0 and ry > 0 else None)

    def _line(self, element: Mapping[str, Any]) -> list[Part]:
        """A line, or a tie's connector through each of its points, stroked, with an
        arrowhead at each end that carries one, in the stroke's colour. A line that holds
        neither its ends nor its points is refused, as an element the renderer does not
        draw is."""
        points = element.get("points")
        if not points and any(end not in element for end in ENDS_OF_LINE):
            self._lose(
                element["id"],
                seam.REFUSED,
                f"the line holds neither its ends, `{' '.join(ENDS_OF_LINE)}`, nor its points",
            )
            return []
        route = (
            [(float(p["x"]), float(p["y"])) for p in points]
            if points
            else [
                (float(element["x1"]), float(element["y1"])),
                (float(element["x2"]), float(element["y2"])),
            ]
        )
        stroke = self._paint(element, "stroke")
        width = float(element.get("stroke-width", 1))
        if stroke is None or width <= 0:
            return []
        rgb, alpha = stroke
        ops = ["q"]
        if alpha < 1:
            ops.append(self._opacity("CA", alpha))
        ops += [f"{rgb} RG", f"{number(width)} w"]
        path = f"{_point(*route[0])} m " + "".join(f"{_point(*p)} l " for p in route[1:])
        drawn = [f"{' '.join(ops)}\n{path}S\n"]
        heads = [
            _arrowhead(route, which, width)
            for which in ENDS
            if element.get(f"marker-{which}") == "arrow"
        ]
        if heads:
            fill = [self._opacity("ca", alpha)] if alpha < 1 else []
            drawn.append(f"{' '.join([*fill, f'{rgb} rg'])}\n{''.join(heads)}")
        drawn.append("Q\n")
        return ["".join(drawn)]

    def _text(self, element: Mapping[str, Any]) -> list[Part]:
        x, width = float(element["x"]), float(element["width"])
        anchor = element.get("text-anchor", "start")
        at = {"start": x, "middle": x + width / 2, "end": x + width}.get(anchor, x)
        y = float(element["y"])
        step = float(element["line-height"])
        paragraphs = element.get("paragraphs") or [[{}]]
        parts: list[Part] = []
        look = _Look()
        for index, line in enumerate(element.get("lines", [])):
            runs = paragraphs[line.get("paragraph", 0)]
            pieces = []
            for span in line.get("spans", []):
                run = runs[span["run"]]
                pieces += [
                    (run, font, glyphs) for font, glyphs in self._pieces(element, run, span["text"])
                ]
            total = sum(_advance(font, glyphs, run) for run, font, glyphs in pieces)
            pen = at - {"middle": total / 2, "end": total}.get(anchor, 0.0)
            baseline = y + float(line["baseline"]) + index * step
            for run, font, glyphs in pieces:
                size = float(run.get("font-size", 0))
                paint = self._paint({"id": element["id"], "fill": run.get("fill")}, "fill")
                parts.append(look.change(self, font, size, paint))
                parts.append(f"1 0 0 -1 {_point(pen, baseline)} Tm\n")
                parts.append(_Shown(font, glyphs, size))
                pen += _advance(font, glyphs, run)
        if not any(isinstance(part, _Shown) for part in parts):
            return []
        return ["q BT\n", *parts, "ET Q\n"]

    def _pieces(
        self, element: Mapping[str, Any], run: Mapping[str, Any], text: str
    ) -> list[tuple[_Font, tuple[Glyph, ...]]]:
        """A span of a run in pieces of one font each, each character in the first family
        of the run's that has it, as the engine measured it, each piece shaped. A family
        is embedded only where a piece is drawn in it."""
        families = [(family, self._face(family)) for family in run.get("font-family", [])]
        if not families or not text:
            return []
        pieces: list[tuple[str, str]] = []
        for character in text:
            family = next((f for f, face in families if face.has(character)), families[0][0])
            if pieces and pieces[-1][0] == family:
                pieces[-1] = (family, pieces[-1][1] + character)
            else:
                pieces.append((family, character))
        shaped = []
        for family, piece in pieces:
            font = self._font(family)
            if font.face.outlines is None:
                self._lose(
                    element["id"],
                    seam.LEFT_OUT,
                    f"the font file of the family `{family}` holds outlines a PDF does not embed",
                )
                continue
            glyphs = font.face.shape(piece)
            font.use(glyphs)
            shaped.append((font, glyphs))
        return shaped

    def _face(self, family: str) -> _Face:
        """A family's face, its file read once in the document."""
        if family not in self._faces:
            self._faces[family] = _face(self.font_file(family))
        return self._faces[family]

    def _font(self, family: str) -> _Font:
        """A family's font in the file, its resource named in the order the pages first
        draw in it."""
        if family not in self._fonts:
            self._fonts[family] = _Font(family, self._face(family), f"F{len(self._fonts)}")
        return self._fonts[family]

    # -- the file

    def written(self) -> bytes:
        """The file: its catalog, its pages, its resources and fonts, then the table of
        where each object lies, and the trailer, whose `/ID` is taken from the bytes before
        it."""
        objects: list[bytes] = []

        def add(body: str | bytes) -> int:
            objects.append(body.encode("latin-1") if isinstance(body, str) else body)
            return len(objects)

        catalog, tree, info, resources = (add(""), add(""), add(""), add(""))
        fonts = {font.resource: _embedded(font, add) for font in self._fonts.values()}
        kids = []
        for width, height, parts in self._pages:
            content = _stream(_content(width, height, parts).encode("latin-1"))
            contents = add(content)
            box = f"[0 0 {number(width * SCALE)} {number(height * SCALE)}]"
            kids.append(
                add(
                    f"<< /Type /Page /Parent {tree} 0 R /MediaBox {box} "
                    f"/Resources {resources} 0 R /Contents {contents} 0 R >>"
                )
            )
        language = self.scene.get("language")
        lang = f" /Lang {pdf_string(str(language))}" if language else ""
        objects[catalog - 1] = f"<< /Type /Catalog /Pages {tree} 0 R{lang} >>".encode("latin-1")
        listed = " ".join(f"{kid} 0 R" for kid in kids)
        objects[tree - 1] = f"<< /Type /Pages /Kids [{listed}] /Count {len(kids)} >>".encode(
            "latin-1"
        )
        objects[info - 1] = (
            f"<< /Producer {pdf_string(f'pkit visual-communication {NAME} {VERSION}')} >>"
        ).encode("latin-1")
        font_list = " ".join(f"/{name} {ref} 0 R" for name, ref in fonts.items())
        opacities = " ".join(
            f"/{name} << /Type /ExtGState /{operand} {value} >>"
            for (operand, value), name in self._opacities.items()
        )
        objects[resources - 1] = (
            f"<< /Font << {font_list} >> /ExtGState << {opacities} >> >>".encode("latin-1")
        )
        return _file(objects, catalog, info)


class _Look:
    """The font, size and paint a text object draws in now, so that each is set only where
    it changes."""

    def __init__(self) -> None:
        self.font: tuple[str, str] | None = None
        self.colour: str | None = None
        self.alpha = "1"
        self.hidden = False

    def change(
        self, document: _Document, font: _Font, size: float, paint: tuple[str, float] | None
    ) -> str:
        ops = []
        if (font.resource, number(size)) != self.font:
            self.font = (font.resource, number(size))
            ops.append(f"/{font.resource} {number(size)} Tf")
        hidden = paint is None
        if hidden != self.hidden:
            ops.append("3 Tr" if hidden else "0 Tr")
            self.hidden = hidden
        if paint is not None:
            rgb, alpha = paint
            if rgb != self.colour:
                ops.append(f"{rgb} rg")
                self.colour = rgb
            if number(alpha, 4) != self.alpha:
                ops.append(document._opacity("ca", alpha))
                self.alpha = number(alpha, 4)
        return " ".join(ops) + "\n" if ops else ""


def _advance(font: _Font, glyphs: Sequence[Glyph], run: Mapping[str, Any]) -> float:
    """How far shaped glyphs move the pen at a run's size, in px."""
    return sum(glyph.advance for glyph in glyphs) * float(run.get("font-size", 0)) / font.face.upem


def _rectangle(x: float, y: float, width: float, height: float, rx: float) -> str:
    """A rectangle's path, its corners rounded as SVG rounds them: by `rx` across and down,
    each at most half the side."""
    across, down = min(rx, width / 2), min(rx, height / 2)
    if across <= 0 or down <= 0:
        return f"{_point(x, y)} {_point(width, height)} re\n"
    kx, ky = across * (1 - KAPPA), down * (1 - KAPPA)
    right, bottom = x + width, y + height
    return (
        f"{_point(x + across, y)} m\n"
        f"{_point(right - across, y)} l\n"
        f"{_point(right - kx, y)} {_point(right, y + ky)} {_point(right, y + down)} c\n"
        f"{_point(right, bottom - down)} l\n"
        f"{_point(right, bottom - ky)} {_point(right - kx, bottom)} "
        f"{_point(right - across, bottom)} c\n"
        f"{_point(x + across, bottom)} l\n"
        f"{_point(x + kx, bottom)} {_point(x, bottom - ky)} {_point(x, bottom - down)} c\n"
        f"{_point(x, y + down)} l\n"
        f"{_point(x, y + ky)} {_point(x + kx, y)} {_point(x + across, y)} c\nh\n"
    )


def _ellipse(cx: float, cy: float, rx: float, ry: float) -> str:
    """An ellipse's path: four cubic Bézier curves, one for each quarter."""
    kx, ky = rx * KAPPA, ry * KAPPA
    return (
        f"{_point(cx + rx, cy)} m\n"
        f"{_point(cx + rx, cy + ky)} {_point(cx + kx, cy + ry)} {_point(cx, cy + ry)} c\n"
        f"{_point(cx - kx, cy + ry)} {_point(cx - rx, cy + ky)} {_point(cx - rx, cy)} c\n"
        f"{_point(cx - rx, cy - ky)} {_point(cx - kx, cy - ry)} {_point(cx, cy - ry)} c\n"
        f"{_point(cx + kx, cy - ry)} {_point(cx + rx, cy - ky)} {_point(cx + rx, cy)} c\nh\n"
    )


def _arrowhead(route: Sequence[tuple[float, float]], which: str, width: float) -> str:
    """The arrowhead at one end of a route, as the SVG renderer's marker draws it: a
    triangle five strokes long and five wide, its tip at the end, pointing away from the
    line along its last stretch, or across to the right where the line has no length."""
    ordered = list(route) if which == "end" else list(reversed(route))
    tip = ordered[-1]
    dx, dy = 1.0, 0.0
    for before in reversed(ordered[:-1]):
        length = ((tip[0] - before[0]) ** 2 + (tip[1] - before[1]) ** 2) ** 0.5
        if length > 0:
            dx, dy = (tip[0] - before[0]) / length, (tip[1] - before[1]) / length
            break
    else:
        if which == "start":
            dx = -1.0
    back = (tip[0] - 5 * width * dx, tip[1] - 5 * width * dy)
    side = (-dy * 2.5 * width, dx * 2.5 * width)
    left = (back[0] + side[0], back[1] + side[1])
    right = (back[0] - side[0], back[1] - side[1])
    return f"{_point(*left)} m {_point(*tip)} l {_point(*right)} l h f\n"


def _content(width: float, height: float, parts: Sequence[Part]) -> str:
    """A page's content: the scene's px mapped onto the page's pt, down the page as the
    scene runs, with SVG's miter limit, then what the page draws."""
    head = f"{number(SCALE)} 0 0 {number(-SCALE)} 0 {number(height * SCALE)} cm 4 M\n"
    drawn = (
        part.font.shown(part.glyphs, part.size) + "\n" if isinstance(part, _Shown) else part
        for part in parts
    )
    return head + "".join(drawn)


def _stream(data: bytes, entries: str = "") -> bytes:
    return f"<< /Length {len(data)}{entries} >>\nstream\n".encode("latin-1") + data + b"\nendstream"


def _embedded(font: _Font, add: Callable[[str | bytes], int]) -> int:
    """A family's font, embedded, as its objects: the Type 0 font and its CID font, the
    font's descriptor and program, and its map back to Unicode. Gives the Type 0 font's
    number."""
    face = font.face
    embedded = font.embed()
    tag = "".join(chr(65 + byte % 26) for byte in hashlib.sha256(embedded.program).digest()[:6])
    name = pdf_name(f"{tag}+{font.family}")
    scale = 1000 / face.upem
    if face.outlines == "CFF ":
        program = add(_stream(embedded.program, " /Subtype /CIDFontType0C"))
        kind, held, mapped = "CIDFontType0", "FontFile3", ""
    else:
        program = add(_stream(embedded.program, f" /Length1 {len(embedded.program)}"))
        kind, held, mapped = "CIDFontType2", "FontFile2", " /CIDToGIDMap /Identity"
    flags = 4 | (1 if face.fixed else 0) | (64 if face.italic else 0)
    bbox = " ".join(number(value * scale, 0) for value in face.bbox)
    descriptor = add(
        f"<< /Type /FontDescriptor /FontName {name} /Flags {flags} /FontBBox [{bbox}] "
        f"/ItalicAngle {number(face.italic)} /Ascent {number(face.ascent * scale, 0)} "
        f"/Descent {number(face.descent * scale, 0)} "
        f"/CapHeight {number(face.cap_height * scale, 0)} /StemV {STEM} "
        f"/{held} {program} 0 R >>"
    )
    by_cid = sorted((embedded.cids[glyph], glyph) for glyph in font.glyphs)
    widths = _widths([(cid, font.width(glyph)) for cid, glyph in by_cid])
    system = "<< /Registry (Adobe) /Ordering (Identity) /Supplement 0 >>"
    descendant = add(
        f"<< /Type /Font /Subtype /{kind} /BaseFont {name} /CIDSystemInfo {system} "
        f"/FontDescriptor {descriptor} 0 R /W [{widths}]{mapped} >>"
    )
    unicode = add(_stream(_to_unicode([(cid, font.text.get(glyph, "")) for cid, glyph in by_cid])))
    return add(
        f"<< /Type /Font /Subtype /Type0 /BaseFont {name} /Encoding /Identity-H "
        f"/DescendantFonts [{descendant} 0 R] /ToUnicode {unicode} 0 R >>"
    )


def _widths(widths: Sequence[tuple[int, str]]) -> str:
    """The `/W` array of a CID font: each stretch of consecutive CIDs, its first CID and
    each width."""
    out: list[str] = []
    stretch: list[str] = []
    first = last = -2
    for cid, width in widths:
        if cid != last + 1 and stretch:
            out.append(f"{first} [{' '.join(stretch)}]")
            stretch = []
        if not stretch:
            first = cid
        stretch.append(width)
        last = cid
    if stretch:
        out.append(f"{first} [{' '.join(stretch)}]")
    return " ".join(out)


def _to_unicode(texts: Sequence[tuple[int, str]]) -> bytes:
    """A CMap from each CID to the characters its glyph stands for, in UTF-16BE; a glyph
    that stands for none is left out."""
    pairs = [
        f"<{cid:04X}> <{text.encode('utf-16-be', 'surrogatepass').hex().upper()}>"
        for cid, text in texts
        if text
    ]
    chunks = [pairs[at : at + 100] for at in range(0, len(pairs), 100)]
    mapped = "".join(
        f"{len(chunk)} beginbfchar\n" + "\n".join(chunk) + "\nendbfchar\n" for chunk in chunks
    )
    return (
        "/CIDInit /ProcSet findresource begin\n12 dict begin\nbegincmap\n"
        "/CIDSystemInfo << /Registry (Adobe) /Ordering (UCS) /Supplement 0 >> def\n"
        "/CMapName /Adobe-Identity-UCS def\n/CMapType 2 def\n"
        "1 begincodespacerange\n<0000> <FFFF>\nendcodespacerange\n"
        f"{mapped}endcmap\nCMapName currentdict /CMap defineresource pop\nend\nend"
    ).encode("ascii")


def _file(objects: Sequence[bytes], catalog: int, info: int) -> bytes:
    """The file of `objects`, numbered from 1 in order: the header, each object, the table
    of where each lies, and the trailer, its `/ID` the first 16 bytes of the SHA-256 of
    what comes before the table."""
    out = bytearray(HEADER)
    offsets = []
    for number_, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{number_} 0 obj\n".encode("latin-1") + body + b"\nendobj\n"
    identity = hashlib.sha256(out).hexdigest()[:32].upper()
    table = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode("latin-1")
    out += "".join(f"{offset:010d} 00000 n \n" for offset in offsets).encode("latin-1")
    out += (
        f"trailer\n<< /Size {len(objects) + 1} /Root {catalog} 0 R /Info {info} 0 R "
        f"/ID [<{identity}> <{identity}>] >>\nstartxref\n{table}\n%%EOF\n"
    ).encode("latin-1")
    return bytes(out)
