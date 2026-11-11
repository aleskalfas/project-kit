"""The PDF renderer: a scene drawn as one PDF file, its pages in order, for each language
and combination of modes (visual-communication DEC-005 points 4, 5, 9 and 10, DEC-006
point 7).

- **What it draws** is its declaration (`pdf_declaration.py`): every primitive of format
  1's scene, the image among them. It draws only what it declares, so the losses the
  capability reads from the declaration before it runs are the ones it makes.
- **Pages.** Each page of the scene, in the scene's order, is a page of the file. Where the
  scene's root holds the physical size of the piece's top, every page is that size, at 72
  pt to 25.4 mm, and is drawn by one scale for the whole page: the page's width in pt over
  its width in px (DEC-034 point 3). Its height follows its width in that proportion, so
  the scale fits it too. Elsewhere a page is as large as its frame, each px of the scene
  0.75 pt of the page, CSS's 96 px to the inch, as the declaration's `unit` says.
- **The largest page.** A page of PDF is at most `LARGEST` pt on a side, as readers hold it.
  A page larger, such as a phone's page of a long site at 0.75 pt to a px, is drawn smaller,
  its proportions kept, its long side `LARGEST` pt. The page is reported, as drawn otherwise
  (DEC-022 point 7). Every other page draws as before.
- **Colours** stay roles in the scene. The renderer takes each from the brand's resolved
  values in the combination it draws (`colours`), as DeviceRGB, with an opacity where the
  colour is translucent. A role with no colour there is left out, and reported.
- **Fonts** are embedded from the brand's committed files, never the machine's: each
  family a run draws in once in the file, as a CID-keyed font (Type 0, `Identity-H`), its
  program subset to the glyphs the file draws in it, with a map from each glyph back to the
  characters it stands for (`ToUnicode`), so the text can be searched and copied. A CFF
  font's program is embedded as CFF, a TrueType font's as TrueType. A family whose file
  holds neither is never embedded: the text drawn in it is left out, in its place, and
  reported, as a font the renderer cannot draw (DEC-005 point 10). A family's name is
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
- **A picture** is drawn from the file its image shows in the combination drawn
  (`seam.Shown`), whatever its source, and from nothing else (DEC-025 point 7). It is
  drawn whole, centred, as large as its frame allows, as the scene's `xMidYMid meet` says
  (DEC-025 point 6). The picture reader (`_lib.pictures`) reads its size and its colour
  profile, which goes into the file with it, so a viewer draws it as a browser does
  (DEC-025 point 5). A JPEG is embedded as its own bytes (`/DCTDecode`). A PNG with no
  transparency, or a palette's, embeds its image data as the file holds it (`/FlateDecode`
  with the PNG predictors), and one colour a grey or an RGB PNG names transparent is a
  colour key (`/Mask`). An alpha channel, and the alpha a palette gives, are decoded
  (`_lib.png`) and drawn as a soft mask (`/SMask`). A PNG embedded as the file holds it is
  seen to decode first. Each picture lies once in the file, however often it is drawn. An
  image handed no picture, or one that cannot be read or decoded, such as a PNG too large to
  decode, is left out, and reported.

Output is fixed for a version: lengths are written to 1/100 px, a page's scale to six
decimals and colours to 1/10 000, objects in one order, the streams uncompressed, with no
date and no random id: the file's `/ID` is taken from its own bytes. A picture's data is the
file's own, and what the renderer decodes, a soft mask and the colours of a PNG with alpha,
is written uncompressed too, so it rests on no build of zlib. So the same scene and values
give the same bytes on every machine. A change that could give another output raises the
version, and the reference outputs pinned to it in the tests catch one made without it
(DEC-005 point 9).
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

from _lib import pictures, png
from _lib.canvas import shows, unshown
from _lib.plugins import seam
from _lib.plugins.pdf_declaration import DECLARATION

NAME: str = DECLARATION["name"]
VERSION: str = DECLARATION["version"]

#: How many pt of the page each px of the scene is (the declaration's `unit`), on a page
#: with no physical size.
SCALE: float = DECLARATION["unit"]["scale"]

#: How many pt of the page a millimetre of a physical size is: 72 pt to the inch, which is
#: 25.4 mm.
PT_PER_MM = 72 / 25.4

#: The most pt a page of the file takes on a side: the largest page readers of PDF hold, at
#: the user unit every file here keeps. At `SCALE`, 19,200 px of the scene.
LARGEST = 14400.0

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
    pictures: Mapping[str, seam.Shown],
) -> Drawn:
    """`scene` (`Scene.to_dict()`) drawn in the combination `key` as one PDF file: `colours`
    gives each colour role's value there, in canonical form; `font_file` the committed file
    of a font family; `pictures` the picture each image shows there, by the image's trace id
    (`seam.Shown`), whatever its source."""
    document = _Document(scene, key, colours, font_file, pictures)
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


# --- pictures -----------------------------------------------------------------------------------


@dataclass(frozen=True)
class _Image:
    """A picture as the file embeds it: its size in pixels; its data, and the entries that
    name the data's filter and its parameters, none for data written as it is; its bits for
    each sample; whether its colours are grey, else RGB; its palette, where its samples are
    indices into one; the ICC profile its colours are drawn by; and its transparency, as the
    one colour it names transparent (`key`), or as an alpha for each pixel, one byte each,
    row after row (`mask`)."""

    width: int
    height: int
    data: bytes
    filter: str
    bits: int
    grey: bool
    profile: bytes | None
    palette: bytes = b""
    key: tuple[int, ...] | None = None
    mask: bytes | None = None


#: Each picture read in this process, by the SHA-256 of its file's bytes, its name and the
#: kind it was handed as: the picture as a file embeds it, or why it cannot be drawn.
_IMAGES: dict[tuple[str, str, str], _Image | str] = {}

#: Each kind of picture, as a message names it.
_KIND_SAID = {seam.PNG: "PNG", seam.JPEG: "JPEG"}


def _picture(data: bytes, shown: seam.Shown, mark: str) -> _Image | str:
    """The picture whose file, handed as `shown`, holds `data`, whose SHA-256 is `mark`, as
    the file embeds it; or why it cannot be drawn. Each is read once in the process."""
    held = (mark, shown.file.name, shown.kind)
    if held not in _IMAGES:
        _IMAGES[held] = _read_picture(data, shown)
    return _IMAGES[held]


def _read_picture(data: bytes, shown: seam.Shown) -> _Image | str:
    """A picture read by the picture reader, of the kind it was handed as: a JPEG as its own
    bytes, a PNG as `_png` embeds it. What cannot be drawn is said in words: a file the
    reader refuses, or a PNG that cannot be decoded."""
    name = shown.file.name
    try:
        read = pictures.read(data, name)
    except pictures.Refused as refused:
        return refused.message
    except ValueError as exc:
        return str(exc)
    if read.kind != shown.kind:
        return f"`{name}` is no {_KIND_SAID[shown.kind]} by its bytes"
    if read.kind == pictures.JPEG:
        return _Image(
            read.width, read.height, data, " /Filter /DCTDecode", 8, read.grey, read.profile
        )
    try:
        return _png(png.read(data), read)
    except png.Undecodable as exc:
        return f"`{name}` cannot be decoded: {exc}"


def _png(decoded: png.Png, read: pictures.Picture) -> _Image:
    """A PNG as the file embeds it. One of a colour type with alpha is decoded, its colours
    and its alpha apart, each written as it is. Any other keeps its image data as the file
    holds it, which the PNG predictors undo, once it is seen to decode; a palette's alpha is
    decoded to a soft mask, and one colour a grey or an RGB picture names transparent is a
    colour key. So no file holds a picture the decoder refuses. Raises png.Undecodable."""
    if decoded.colour in png.WITH_ALPHA:
        colours, alpha = png.alpha_apart(decoded, png.samples(decoded))
        return _Image(
            decoded.width, decoded.height, colours, "", 8, read.grey, read.profile, mask=alpha
        )
    predicted = (
        f" /Filter /FlateDecode /DecodeParms << /Predictor 15 /Colors {decoded.channels} "
        f"/BitsPerComponent {decoded.depth} /Columns {decoded.width} >>"
    )
    if png.has_palette_alpha(decoded):
        mask = png.palette_alpha(decoded, png.samples(decoded))
    else:
        png.check(decoded)
        mask = None
    return _Image(
        decoded.width,
        decoded.height,
        decoded.data,
        predicted,
        decoded.depth,
        read.grey,
        read.profile,
        palette=decoded.palette,
        key=png.colour_key(decoded),
        mask=mask,
    )


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
        shown: Mapping[str, seam.Shown],
    ) -> None:
        self.scene = scene
        self.key = key
        self.colours = colours
        self.font_file = font_file
        self.shown = shown
        self.losses: list[seam.Loss] = []
        self.traces: list[str] = []
        self._pages: list[tuple[_Sheet, list[Part]]] = []
        self._faces: dict[str, _Face] = {}
        self._fonts: dict[str, _Font] = {}
        # Each opacity the pages take, by the operand it sets and its value: its name.
        self._opacities: dict[tuple[str, str], str] = {}
        # Each picture the pages draw, by the SHA-256 of its file: its name, and the picture.
        self._images: dict[str, tuple[str, _Image]] = {}

    def _lose(self, what: str, did: str, why: str) -> None:
        loss = seam.Loss(NAME, what, did, why)
        if loss not in self.losses:
            self.losses.append(loss)

    # -- a page

    def page(self, element: Mapping[str, Any]) -> None:
        self.traces.append(element["id"])
        parts = [part for child in element.get("children", []) for part in self._element(child)]
        width, height = float(element["width"]), float(element["height"])
        sheet = _sheet(width, height, self.scene.get("physical-size"))
        if sheet.fit < 1:
            measures = " by ".join(number(side) for side in sheet.measures)
            self._lose(
                element["id"],
                seam.APPROXIMATED,
                f"the page measures {measures} pt, past the {number(LARGEST)} pt a page of PDF "
                f"takes on a side, so it is drawn {number(sheet.fit, 4)} as large, its "
                "proportions kept",
            )
        self._pages.append((sheet, parts))

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

    def _image(self, element: Mapping[str, Any]) -> list[Part]:
        """An image, its picture drawn whole, centred and as large as its frame allows, its
        first row at the top. Nothing where its frame or the picture fitted has no size. One
        handed no picture in this combination, or one that cannot be read or decoded, is
        left out, and reported."""
        trace = str(element["id"])
        shown = self.shown.get(trace)
        if shown is None or not shown.file.is_file():
            self._lose(trace, seam.LEFT_OUT, unshown(element, self.key, self.scene.get("piece")))
            return []
        try:
            data = shown.file.read_bytes()
        except OSError as exc:
            why = f"`{shown.file.name}` cannot be read: {exc.strerror or exc}"
            self._lose(trace, seam.LEFT_OUT, f"{shows(element)} cannot be drawn: {why}")
            return []
        mark = hashlib.sha256(data).hexdigest()
        image = _picture(data, shown, mark)
        if isinstance(image, str):
            self._lose(trace, seam.LEFT_OUT, f"{shows(element)} cannot be drawn: {image}")
            return []
        x, y = float(element["x"]), float(element["y"])
        width, height = float(element["width"]), float(element["height"])
        scale = min(width / image.width, height / image.height)
        drawn_width, drawn_height = image.width * scale, image.height * scale
        if number(drawn_width) == "0" or number(drawn_height) == "0":
            return []
        name = self._images.setdefault(mark, (f"I{len(self._images)}", image))[0]
        left = x + (width - drawn_width) / 2
        bottom = y + (height + drawn_height) / 2
        return [
            f"q {number(drawn_width)} 0 0 {number(-drawn_height)} {_point(left, bottom)} cm "
            f"/{name} Do Q\n"
        ]

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
                    (run, face, font, glyphs)
                    for face, font, glyphs in self._pieces(element, run, span["text"])
                ]
            total = sum(_advance(face, glyphs, run) for run, face, _, glyphs in pieces)
            pen = at - {"middle": total / 2, "end": total}.get(anchor, 0.0)
            baseline = y + float(line["baseline"]) + index * step
            for run, face, font, glyphs in pieces:
                # A piece with no font is left out, and keeps its place in the line.
                if font is not None:
                    size = float(run.get("font-size", 0))
                    paint = self._paint({"id": element["id"], "fill": run.get("fill")}, "fill")
                    parts.append(look.change(self, font, size, paint))
                    parts.append(f"1 0 0 -1 {_point(pen, baseline)} Tm\n")
                    parts.append(_Shown(font, glyphs, size))
                pen += _advance(face, glyphs, run)
        if not any(isinstance(part, _Shown) for part in parts):
            return []
        return ["q BT\n", *parts, "ET Q\n"]

    def _pieces(
        self, element: Mapping[str, Any], run: Mapping[str, Any], text: str
    ) -> list[tuple[_Face, _Font | None, tuple[Glyph, ...]]]:
        """A span of a run in pieces of one font each, each character in the first family
        of the run's that has it, as the engine measured it, each piece shaped, with the
        font it is drawn in. A family is embedded only where a piece is drawn in it. One
        whose file holds neither CFF nor TrueType outlines is never embedded: its pieces
        have no font, and are a loss (DEC-005 point 10)."""
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
        shaped: list[tuple[_Face, _Font | None, tuple[Glyph, ...]]] = []
        for family, piece in pieces:
            face = self._face(family)
            glyphs = face.shape(piece)
            if face.outlines is None:
                self._lose(
                    element["id"],
                    seam.LEFT_OUT,
                    f"the font file of the family `{family}` holds neither CFF nor TrueType "
                    f"outlines, which a PDF embeds",
                )
                shaped.append((face, None, glyphs))
                continue
            font = self._font(family)
            font.use(glyphs)
            shaped.append((face, font, glyphs))
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
        profiles: dict[bytes, int] = {}
        images = {
            name: _embedded_image(image, add, profiles) for name, image in self._images.values()
        }
        kids = []
        for sheet, parts in self._pages:
            content = _stream(_content(sheet, parts).encode("latin-1"))
            contents = add(content)
            box = f"[0 0 {' '.join(number(side) for side in sheet.box)}]"
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
        # A file that draws no picture names no images, so its resources are as before.
        drawn = " ".join(f"/{name} {ref} 0 R" for name, ref in images.items())
        xobjects = f" /XObject << {drawn} >>" if images else ""
        objects[resources - 1] = (
            f"<< /Font << {font_list} >> /ExtGState << {opacities} >>{xobjects} >>".encode(
                "latin-1"
            )
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


def _advance(face: _Face, glyphs: Sequence[Glyph], run: Mapping[str, Any]) -> float:
    """How far shaped glyphs move the pen at a run's size, in px."""
    return sum(glyph.advance for glyph in glyphs) * float(run.get("font-size", 0)) / face.upem


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


@dataclass(frozen=True)
class _Sheet:
    """How one page of the scene lies on a page of the file: the page's size in pt before it
    is fitted, `measures`; how large it is drawn, as a share of that size, `fit`; how many pt
    of the page each px of the scene is, fitted, `scale`; and how far above the page's foot
    the scene's top lies, in pt, `top`."""

    measures: tuple[float, float]
    fit: float
    scale: float
    top: float

    @property
    def box(self) -> tuple[float, float]:
        """The page's size in pt, as drawn."""
        return self.measures[0] * self.fit, self.measures[1] * self.fit


def _sheet(width: float, height: float, physical: Any) -> _Sheet:
    """How a page of `width` by `height` px is drawn. Where `physical`, the physical size the
    scene's root holds, is given, the page is that size, and its width sets one scale for
    the whole page (DEC-034 point 3). Elsewhere each px is `SCALE` pt. Either way a page
    whose long side would pass `LARGEST` pt is fitted to it."""
    if isinstance(physical, Mapping) and width > 0:
        measures = (float(physical["width"]) * PT_PER_MM, float(physical["height"]) * PT_PER_MM)
        fit = _fit(*measures)
        return _Sheet(measures, fit, measures[0] / width * fit, measures[1] * fit)
    measures = (width * SCALE, height * SCALE)
    fit = _fit(*measures)
    scale = SCALE * fit
    return _Sheet(measures, fit, scale, height * scale)


def _fit(width: float, height: float) -> float:
    """How large a page of `width` by `height` pt is drawn, as a share of its size: 1, or less
    where its long side would pass `LARGEST` pt."""
    longest = max(width, height)
    return LARGEST / longest if longest > LARGEST else 1.0


def _content(sheet: _Sheet, parts: Sequence[Part]) -> str:
    """A page's content: the scene's px mapped onto the page's pt at the sheet's scale, down
    the page as the scene runs, with SVG's miter limit, then what the page draws."""
    scale = sheet.scale
    head = f"{number(scale, 6)} 0 0 {number(-scale, 6)} 0 {number(sheet.top)} cm 4 M\n"
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


def _embedded_image(
    image: _Image, add: Callable[[str | bytes], int], profiles: dict[bytes, int]
) -> int:
    """A picture, embedded, as its objects: its colour profile, once in the file however many
    pictures carry it (`profiles`, each profile's number by its bytes), its soft mask, and
    the image, drawn smoothed where it is scaled, as a browser draws it. Gives the image's
    number."""
    space = "/DeviceGray" if image.grey else "/DeviceRGB"
    if image.profile is not None:
        if image.profile not in profiles:
            channels = 1 if image.grey else 3
            entries = f" /N {channels} /Alternate {space}"
            profiles[image.profile] = add(_stream(image.profile, entries))
        space = f"[/ICCBased {profiles[image.profile]} 0 R]"
    if image.palette:
        top = len(image.palette) // 3 - 1
        space = f"[/Indexed {space} {top} <{image.palette.hex().upper()}>]"
    size = f" /Type /XObject /Subtype /Image /Width {image.width} /Height {image.height}"
    entries = f"{size} /ColorSpace {space} /BitsPerComponent {image.bits} /Interpolate true"
    if image.mask is not None:
        grey = f"{size} /ColorSpace /DeviceGray /BitsPerComponent 8 /Interpolate true"
        entries += f" /SMask {add(_stream(image.mask, grey))} 0 R"
    elif image.key is not None:
        entries += f" /Mask [{' '.join(f'{sample} {sample}' for sample in image.key)}]"
    return add(_stream(image.data, entries + image.filter))


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
