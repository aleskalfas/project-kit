"""The PDF renderer (visual-communication DEC-005 points 4, 5, 9 and 10, DEC-006 point 7,
DEC-025 points 5 to 7): what it declares, what it draws, and what it reports it lost.

The reference outputs below are pinned to the renderer's version, 1.6.0. A change that
gives another output for the same scene and values raises the version, and changes them
with it (DEC-005 point 9). Version 1.1.0 came to draw every image, from the picture it is
handed, whatever its source: a scene of no picture draws as 1.0.0 drew it, but for the
renderer's version it names. Version 1.2.0 came to draw a page past the largest a reader of
PDF holds smaller, to fit (DEC-022 point 7): every other page draws as 1.1.0 drew it, but for
the renderer's version the file names. Version 1.3.0 came to draw each page of a scene whose
root holds a physical size at that size (DEC-034 point 3): a scene with none draws as 1.2.0
drew it, but for the renderer's version the file names. Version 1.4.0 came to draw the path,
a concept's sign, at seam 7 (DEC-036 point 1): a scene of no path draws as 1.3.0 drew it, but
for the renderer's version the file names. Version 1.5.0 came to draw a run's sign and
ground, at seam 8 (DEC-036 point 3): a scene of neither draws as 1.4.0 drew it, but for the
renderer's version the file names. Version 1.6.0 came to stop a line at its arrowhead's base,
and to draw a connector's turns round at the radius it holds, `rx`, each a cubic Bézier curve
of its arc: a line with no arrowhead and no radius draws as 1.5.0 drew it, but for the
renderer's version the file names. A page's content is pinned whole.
An embedded font is pinned by the glyphs its subset holds and the characters its map gives
them, not by its bytes, which are fontTools'. A picture is pinned by its image's dictionary
and its data: a JPEG's own bytes, a PNG's image data as the file holds it, or what the
decoder gives (`test_visual_communication_png.py`). The pictures are those the SVG and HTML
renderers' tests draw. The files are read here by their own table of objects, as a reader
of PDF reads them (`read`); the export of a piece as PDF is
`test_visual_communication_export.py`'s.
"""

from __future__ import annotations

import hashlib
import io
import re
import struct
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from fontTools.cffLib import CFFFontSet
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont

from tests.in_process import load
from tests.test_visual_communication_png import built
from tests.test_visual_communication_svg import (
    COLOURS,
    ENCODINGS,
    FONT,
    HOSTILE,
    ROUNDED,
    SAID,
    SEMIBOLD,
    SHAPES,
    SOURCES,
    TIES,
    TITLE,
    element,
    image_of,
    line,
    named,
    run,
    scene,
)
from tests.visual_communication_project import TEST_PICTURES

pdf, pdf_declaration, svg_declaration, seam, pictures, png = load(
    "visual-communication",
    "plugins.pdf",
    "plugins.pdf_declaration",
    "plugins.svg_declaration",
    "plugins.seam",
    "pictures",
    "png",
)

#: The families of the runs below, each with its committed file.
FILES = {"Source Sans Pro": FONT, "Source Sans Pro Semibold": SEMIBOLD}


def draw(
    drawn: dict[str, Any], *, key: str = "default", files: Any = None, pictures: Any = None
) -> Any:
    found = files or FILES
    return pdf.render(
        drawn, key=key, colours=COLOURS, font_file=lambda family: found.get(family, FONT),
        pictures=pictures or {},
    )  # fmt: skip


# --- reading a file -----------------------------------------------------------------------------


@dataclass(frozen=True)
class Read:
    """A PDF file read by its table: each object's dictionary, or its value, and its stream,
    empty where it has none, by its number; and the trailer's dictionary."""

    objects: dict[int, tuple[str, bytes]]
    trailer: str

    def value(self, number: int) -> str:
        return self.objects[number][0]

    def stream(self, number: int) -> bytes:
        return self.objects[number][1]

    def ref(self, number: int, key: str) -> int:
        """The object the entry `key` of an object's dictionary refers to."""
        found = re.search(rf"/{key} (\d+) 0 R", self.value(number))
        assert found is not None, (number, key)
        return int(found[1])

    def descendant(self, font: int) -> int:
        """The CID font of a Type 0 font."""
        found = re.search(r"/DescendantFonts \[(\d+) 0 R\]", self.value(font))
        assert found is not None
        return int(found[1])

    def pages(self) -> list[int]:
        root = int(re.findall(r"/Root (\d+) 0 R", self.trailer)[0])
        kids = re.search(r"/Kids \[([^\]]*)\]", self.value(self.ref(root, "Pages")))
        assert kids is not None
        return [int(kid) for kid in re.findall(r"(\d+) 0 R", kids[1])]

    def content(self, page: int) -> str:
        return self.stream(self.ref(page, "Contents")).decode("latin-1")

    def images(self, page: int) -> dict[str, int]:
        """The image of each image resource of a page, by its resource's name."""
        listed = re.search(r"/XObject << ([^>]*) >>", self.value(self.ref(page, "Resources")))
        if listed is None:
            return {}
        return {name: int(ref) for name, ref in re.findall(r"/(\w+) (\d+) 0 R", listed[1])}

    def fonts(self, page: int) -> dict[str, int]:
        """The Type 0 font of each font resource of a page, by its resource's name."""
        listed = re.search(r"/Font << ([^>]*) >>", self.value(self.ref(page, "Resources")))
        assert listed is not None
        return {name: int(ref) for name, ref in re.findall(r"/(\w+) (\d+) 0 R", listed[1])}

    def unicode(self, font: int) -> dict[str, str]:
        """The characters each CID of a Type 0 font stands for, by its CID in hexadecimal."""
        cmap = self.stream(self.ref(font, "ToUnicode")).decode("ascii")
        pairs = "".join(re.findall(r"beginbfchar\n(.*?)endbfchar", cmap, re.DOTALL))
        return {
            cid: bytes.fromhex(text).decode("utf-16-be", "surrogatepass")
            for cid, text in re.findall(r"<([0-9A-F]{4})> <([0-9A-F]+)>", pairs)
        }

    def lines(self, page: int) -> list[str]:
        """The text a page shows, read back through each font's map to Unicode: each
        stretch the content places at one baseline, top to bottom."""
        maps = {name: self.unicode(font) for name, font in self.fonts(page).items()}
        shown: dict[float, str] = {}
        font, baseline = "", 0.0
        operators = r"/(\w+) [-\d.]+ Tf|1 0 0 -1 [-\d.]+ ([-\d.]+) Tm|<([0-9A-F]+)>"
        for found in re.finditer(operators, self.content(page)):
            if found[1]:
                font = found[1]
            elif found[2]:
                baseline = float(found[2])
            else:
                codes = [found[3][at : at + 4] for at in range(0, len(found[3]), 4)]
                said = "".join(maps[font].get(code, "") for code in codes)
                shown[baseline] = shown.get(baseline, "") + said
        return [shown[at] for at in sorted(shown)]


def read(data: bytes) -> Read:
    """A file the renderer wrote, read by its table: each object at the offset the table
    gives, each stream at the length its dictionary gives, the table and the trailer where
    the file says."""
    assert data.startswith(b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n")
    assert data.endswith(b"%%EOF\n")
    table = int(data.rsplit(b"startxref\n", 1)[1].split(b"\n")[0])
    rows = data[table:].split(b"\n")
    assert rows[0] == b"xref" and rows[2] == b"0000000000 65535 f "
    size = int(rows[1].split()[1])
    offsets = [int(row.split()[0]) for row in rows[3 : 2 + size]]
    trailer = data[table:].split(b"trailer\n")[1].split(b"\nstartxref")[0].decode("latin-1")
    assert f"/Size {size} " in trailer
    objects = {}
    for number, offset in enumerate(offsets, start=1):
        opened = f"{number} 0 obj\n".encode()
        assert data[offset : offset + len(opened)] == opened
        body = data[offset + len(opened) :]
        found = re.match(rb"<< /Length (\d+)[^\n]* >>\nstream\n", body)
        if found is None:
            value = body.split(b"\nendobj\n", 1)[0]
            objects[number] = (value.decode("latin-1"), b"")
            continue
        start, length = found.end(), int(found[1])
        assert body[start + length :].startswith(b"\nendstream\nendobj\n")
        objects[number] = (body[:start].decode("latin-1"), body[start : start + length])
    return Read(objects, trailer)


def page_of(drawn: Any) -> tuple[Read, int]:
    """A drawing of one page, read, and its page's object."""
    file = read(drawn.document)
    [page] = file.pages()
    return file, page


#: How each page's content opens, for a page 200 px wide and 100 px tall: the scene's px
#: mapped onto the page's pt, down the page as the scene runs, with SVG's miter limit.
OPENING = "0.75 0 0 -0.75 0 75 cm 4 M\n"


# --- what it draws ------------------------------------------------------------------------------


def test_shapes_are_drawn_as_pinned_for_version_1_2_0() -> None:
    drawn = draw(SHAPES)
    assert drawn.losses == []
    assert drawn.pages == ["figure"]
    file, page = page_of(drawn)
    assert "/MediaBox [0 0 150 75]" in file.value(page)
    assert file.content(page) == (
        OPENING + "q 1 1 1 rg 0.5 0.5 0.5 RG 2 w\n"
        "5 1 m\n195 1 l\n197.21 1 199 2.79 199 5 c\n199 95 l\n199 97.21 197.21 99 195 99 c\n"
        "5 99 l\n2.79 99 1 97.21 1 95 c\n1 5 l\n1 2.79 2.79 1 5 1 c\nh\nB\nQ\n"
        "q 1 0 0 1 10.5 20 cm\n"
        "q 0.25 0.5 0.75 rg\n50 15 m\n50 23.28 38.81 30 25 30 c\n11.19 30 0 23.28 0 15 c\n"
        "0 6.72 11.19 0 25 0 c\n38.81 0 50 6.72 50 15 c\nh\nf\nQ\n"
        "q /A0 gs 0 0 0 RG 1.5 w\n0 40 m 50 40 l S\nQ\n"
        "Q\n"
    )
    resources = file.value(file.ref(page, "Resources"))
    assert resources == "<< /Font <<  >> /ExtGState << /A0 << /Type /ExtGState /CA 0.25 >> >> >>"


def test_a_connector_and_its_arrowheads_are_drawn_as_pinned_for_version_1_6_0() -> None:
    drawn = draw(TIES)
    assert drawn.losses == []
    file, page = page_of(drawn)
    # The connector through its points, its arrowhead a triangle ten px long (five strokes)
    # and ten across, its tip at the end and its base where the line stops; the rule with
    # one at each end, translucent, five px long, since it gives no stroke's width.
    assert file.content(page) == (
        OPENING + "q 0 0 0 RG 2 w\n10 20 m 60 20 l 60 60 l 100 60 l S\n"
        "0 0 0 rg\n100 65 m 110 60 l 100 55 l h f\nQ\n"
        "q /A0 gs 0 0 0 RG 1 w\n5 90 m 195 90 l S\n"
        "/A1 gs 0 0 0 rg\n5 87.5 m 0 90 l 5 92.5 l h f\n195 92.5 m 200 90 l 195 87.5 l h f\nQ\n"
    )
    resources = file.value(file.ref(page, "Resources"))
    assert "/A0 << /Type /ExtGState /CA 0.25 >> /A1 << /Type /ExtGState /ca 0.25 >>" in resources


def test_a_connectors_turns_are_drawn_round_as_pinned_for_version_1_6_0() -> None:
    drawn = draw(ROUNDED)
    assert drawn.losses == []
    file, page = page_of(drawn)
    # Each turn is the cubic Bézier curve of its arc, along the course the SVG renderer
    # draws: the first connector's at 8 px, the second's at half its shorter leg, counted
    # to its heads' bases.
    assert file.content(page) == (
        OPENING + "q 0 0 0 RG 2 w\n10 20 m 52 20 l 56.42 20 60 23.58 60 28 c 60 52 l "
        "60 56.42 63.58 60 68 60 c 100 60 l S\n"
        "0 0 0 rg\n100 65 m 110 60 l 100 55 l h f\nQ\n"
        "q 0 0 0 RG 1 w\n125 10 m 137.5 10 l 144.4 10 150 15.6 150 22.5 c 150 32.5 l "
        "150 42.16 157.84 50 167.5 50 c 185 50 l S\n"
        "0 0 0 rg\n125 7.5 m 120 10 l 125 12.5 l h f\n185 52.5 m 190 50 l 185 47.5 l h f\nQ\n"
    )


def test_a_line_with_no_stroke_draws_nothing() -> None:
    bare = element(
        "line", "figure/rule", x=0, y=0, width=10, height=0, x1=0, y1=0, x2=10, y2=0,
        **{"marker-end": "arrow"},
    )  # fmt: skip
    file, page = page_of(draw(scene(bare)))
    assert file.content(page) == OPENING


def test_text_is_drawn_as_its_measured_lines_in_its_embedded_font() -> None:
    drawn = draw(scene(TITLE))
    assert drawn.losses == []
    file, page = page_of(drawn)
    # Each line centred on the text's middle, 60 px across, by the advances shaped: 79.56
    # px and 9.34 px; at its own baseline, 20.2 px and 40.2 px down.
    assert file.content(page) == (
        OPENING + "q BT\n/F0 16 Tf 0 0 0 rg\n"
        "1 0 0 -1 20.22 20.2 Tm\n[<00020006000300070001000A0001000B00040008000C>] TJ\n"
        "1 0 0 -1 55.33 40.2 Tm\n[<00050009>] TJ\nET Q\n"
    )
    assert file.lines(page) == ["Plan & <do>", "it"]


def test_the_embedded_font_holds_the_glyphs_the_file_draws_and_no_other() -> None:
    file, page = page_of(draw(scene(TITLE)))
    [font] = file.fonts(page).values()
    cid_font = file.descendant(font)
    descriptor = file.ref(cid_font, "FontDescriptor")
    program = file.stream(file.ref(descriptor, "FontFile3"))
    assert "/Subtype /CIDFontType0C" in file.value(file.ref(descriptor, "FontFile3"))
    cff = CFFFontSet()
    cff.decompile(io.BytesIO(program), None)
    names = cff[cff.fontNames[0]].charset
    whole = TTFont(str(FONT))
    by_character = whole.getBestCmap()
    assert by_character is not None
    assert sorted(names) == sorted({".notdef", *(by_character[ord(c)] for c in "Plan & <do>it")})
    assert sorted(file.unicode(font).values()) == sorted(set("Plan & <do>it"))
    assert "/Subtype /CIDFontType0 " in file.value(cid_font)
    assert "/W [0 [653 200 566 504 555 246 255 547 542 338 609 497 497]]" in file.value(cid_font)


def test_glyphs_are_placed_at_the_advances_shaped_their_kerning_kept() -> None:
    kerned = element(
        "text", "figure/kerned", x=0, y=0, width=100, height=20, text="AVA",
        paragraphs=[[run("AVA", fill="ink")]], lines=[line(0, 15, (0, "AVA", 30))],
        **{"line-height": 20, "measured-height": 20},
    )  # fmt: skip
    file, page = page_of(draw(scene(kerned)))
    # The font's widths move the pen 544 and 515 thousandths after `A` and `V`; HarfBuzz
    # shaped 530 and 501, so the pen moves back 14 thousandths after each.
    assert "[<0001>14<0002>14<0001>] TJ" in file.content(page)
    [font] = file.fonts(page).values()
    assert "/W [0 [653 544 515]]" in file.value(file.descendant(font))


def test_a_run_that_looks_otherwise_is_drawn_in_its_own_font_and_paint_as_pinned() -> None:
    drawn = draw(scene(SAID))
    assert drawn.losses == []
    file, page = page_of(drawn)
    assert file.content(page) == (
        OPENING + "q BT\n/F0 16 Tf 0 0 0 rg\n"
        "1 0 0 -1 0 21.5 Tm\n[<0002000300070001>] TJ\n"
        "/F1 24 Tf 0.25 0.5 0.75 rg\n"
        "1 0 0 -1 27.28 21.5 Tm\n[<0003000100020004>] TJ\n"
        "/F0 16 Tf 0 0 0 rg\n"
        "1 0 0 -1 66.86 21.5 Tm\n[<000100040005>4<0006>] TJ\nET Q\n"
    )
    assert file.lines(page) == ["Say <it> now"]
    fonts = file.fonts(page)
    assert [
        re.findall(r"/BaseFont /\w{6}\+(\S+)", file.value(font)) for font in fonts.values()
    ] == [
        ["Source#20Sans#20Pro"],
        ["Source#20Sans#20Pro#20Semibold"],
    ]
    # Each family embedded once, with the characters drawn in it.
    regular, semibold = (set(file.unicode(font).values()) for font in fonts.values())
    assert (regular, semibold) == (set("Say now"), set("<it>"))


def test_a_translucent_run_takes_its_opacity_and_the_next_run_its_own() -> None:
    faint = element(
        "text", "figure/faint", x=0, y=0, width=200, height=20, text="ab",
        paragraphs=[[run("a", fill="shade"), run("b", fill="ink")]],
        lines=[line(0, 15, (0, "a", 10), (1, "b", 10))],
        **{"line-height": 20, "measured-height": 20},
    )  # fmt: skip
    file, page = page_of(draw(scene(faint)))
    content = file.content(page)
    assert "/F0 16 Tf 0 0 0 rg /A0 gs\n" in content
    assert "/A1 gs\n" in content
    resources = file.value(file.ref(page, "Resources"))
    assert "/A0 << /Type /ExtGState /ca 0.25 >> /A1 << /Type /ExtGState /ca 1 >>" in resources


def truetype(path: Path) -> Path:
    """A TrueType font of `.notdef`, `A`, `B` and a space, each letter a square."""
    builder = FontBuilder(1000, isTTF=True)
    builder.setupGlyphOrder([".notdef", "A", "B", "space"])
    builder.setupCharacterMap({ord("A"): "A", ord("B"): "B", ord(" "): "space"})
    glyphs = {}
    for glyph in (".notdef", "A", "B"):
        pen = TTGlyphPen(None)
        pen.moveTo((100, 0))
        pen.lineTo((100, 700))
        pen.lineTo((600, 700))
        pen.lineTo((600, 0))
        pen.closePath()
        glyphs[glyph] = pen.glyph()
    glyphs["space"] = TTGlyphPen(None).glyph()
    builder.setupGlyf(glyphs)
    builder.setupHorizontalMetrics(
        {".notdef": (700, 100), "A": (700, 100), "B": (700, 100), "space": (250, 0)}
    )
    builder.setupHorizontalHeader(ascent=800, descent=-200)
    builder.setupNameTable({"familyName": "Squares", "styleName": "Regular"})
    builder.setupOS2(sTypoAscender=800, usWinAscent=800, usWinDescent=200)
    builder.setupPost()
    builder.save(str(path))
    return path


def test_a_truetype_font_is_embedded_as_truetype_its_cids_its_glyphs(tmp_path: Path) -> None:
    squares = truetype(tmp_path / "Squares.ttf")
    text = element(
        "text", "figure/squares", x=0, y=0, width=100, height=20, text="B A",
        paragraphs=[[run("B A", fill="ink", **{"font-family": ["Squares"]})]],
        lines=[line(0, 15, (0, "B A", 30))], **{"line-height": 20, "measured-height": 20},
    )  # fmt: skip
    drawn = draw(scene(text), files={"Squares": squares})
    assert drawn.losses == []
    file, page = page_of(drawn)
    [font] = file.fonts(page).values()
    cid_font = file.descendant(font)
    assert "/Subtype /CIDFontType2 " in file.value(cid_font)
    assert "/CIDToGIDMap /Identity" in file.value(cid_font)
    descriptor = file.ref(cid_font, "FontDescriptor")
    embedded = TTFont(io.BytesIO(file.stream(file.ref(descriptor, "FontFile2"))))
    # The subset keeps the glyphs in the file's order, so each CID is its glyph's id there.
    assert embedded.getGlyphOrder() == [".notdef", "A", "B", "space"]
    assert "[<000200030001>] TJ" in file.content(page)
    assert file.lines(page) == ["B A"]
    assert "GSUB" not in embedded and "glyf" in embedded


# --- pictures -----------------------------------------------------------------------------------


def handed(name: str, trace: str = "figure/picture", folder: Path = TEST_PICTURES) -> Any:
    """What a renderer is handed for the image `trace` that shows the picture file `name`."""
    kind = seam.JPEG if name.endswith(".jpg") else seam.PNG
    return {trace: seam.Shown(folder / name, kind)}


def image_dictionary(file: Read, page: int) -> tuple[int, str]:
    """The one image a page draws: its object, and its dictionary."""
    [image] = file.images(page).values()
    return image, file.value(image)


#: The colour space each picture the SVG and HTML renderers' tests draw is embedded in, its
#: bits for each sample, and how its data is written: as the JPEG's own bytes, as the PNG's
#: image data with the predictors that undo its filters, or decoded and written as it is.
#: The palette is `palette.png`'s, of four colours, its last transparent.
EMBEDDED = {
    "palette.png": (
        "[/Indexed /DeviceRGB 3 <DC282828A03C2850C8FFFFFF>]",
        2,
        " /Filter /FlateDecode /DecodeParms << /Predictor 15 /Colors 1 /BitsPerComponent 2 "
        "/Columns 4 >>",
    ),
    "grey.png": (
        "/DeviceGray",
        8,
        " /Filter /FlateDecode /DecodeParms << /Predictor 15 /Colors 1 /BitsPerComponent 8 "
        "/Columns 4 >>",
    ),
    "alpha.png": ("/DeviceRGB", 8, ""),
    "profile.png": (
        "[/ICCBased {profile} 0 R]",
        8,
        " /Filter /FlateDecode /DecodeParms << /Predictor 15 /Colors 3 /BitsPerComponent 8 "
        "/Columns 4 >>",
    ),
    "colour.jpg": ("/DeviceRGB", 8, " /Filter /DCTDecode"),
    "grey.jpg": ("/DeviceGray", 8, " /Filter /DCTDecode"),
    "progressive.jpg": ("/DeviceRGB", 8, " /Filter /DCTDecode"),
    "profile.jpg": ("[/ICCBased {profile} 0 R]", 8, " /Filter /DCTDecode"),
}

#: The pictures whose transparency is a soft mask: an alpha channel's, and a palette's.
MASKED = ("alpha.png", "palette.png")


def data_of(data: bytes) -> tuple[bytes, bytes | None]:
    """The data a picture's image holds, and its soft mask's: a JPEG's own bytes; a PNG's image
    data as the file holds it, or its colours decoded where it holds an alpha channel; and the
    alpha the decoder gives each pixel, where it holds one."""
    if data.startswith(b"\xff\xd8"):
        return data, None
    decoded = png.read(data)
    if decoded.colour in png.WITH_ALPHA:
        return png.alpha_apart(decoded, png.samples(decoded))
    if png.has_palette_alpha(decoded):
        return decoded.data, png.palette_alpha(decoded, png.samples(decoded))
    return decoded.data, None


def test_a_picture_is_drawn_as_pinned_for_version_1_2_0() -> None:
    """A picture of 4 by 3 pixels in a frame 50 px square: 50 px wide and 37.5 px tall, its
    top 6.25 px down, its first row at the top."""
    drawn = draw(
        scene(image_of(SOURCES["a picture file of the piece"])), pictures=handed("colour.jpg")
    )
    assert drawn.losses == []
    file, page = page_of(drawn)
    assert file.content(page) == OPENING + "q 50 0 0 -37.5 0 43.75 cm /I0 Do Q\n"
    image, dictionary = image_dictionary(file, page)
    assert dictionary == (
        "<< /Length 680 /Type /XObject /Subtype /Image /Width 4 /Height 3 /ColorSpace /DeviceRGB "
        "/BitsPerComponent 8 /Interpolate true /Filter /DCTDecode >>\nstream\n"
    )
    assert file.stream(image) == (TEST_PICTURES / "colour.jpg").read_bytes()
    assert "/XObject << /I0 " in file.value(file.ref(page, "Resources"))


@pytest.mark.parametrize("source", list(SOURCES))
@pytest.mark.parametrize("name", list(ENCODINGS))
def test_each_encoding_read_is_embedded_as_its_kind_whatever_its_source(
    source: str, name: str
) -> None:
    """Every encoding the reader reads draws (DEC-025 point 5), from the file the renderer is
    handed alone, from a scene built by hand of each source, a picture role's included: a
    JPEG as its own bytes, a PNG's image data as the file holds it, its alpha channel's or its
    palette's transparency a soft mask, and its colour profile with it."""
    data = (TEST_PICTURES / name).read_bytes()

    drawn = draw(scene(image_of(SOURCES[source])), pictures=handed(name))

    assert drawn.losses == []
    file, page = page_of(drawn)
    assert file.content(page) == OPENING + "q 50 0 0 -37.5 0 43.75 cm /I0 Do Q\n"
    image, dictionary = image_dictionary(file, page)
    space, bits, written = EMBEDDED[name]
    profile = re.search(r"/ICCBased (\d+) 0 R", dictionary)
    space = space.format(profile=profile[1] if profile else "")
    colours, mask = data_of(data)
    masked = f" /SMask {file.ref(image, 'SMask')} 0 R" if name in MASKED else ""
    assert dictionary == (
        f"<< /Length {len(colours)} /Type /XObject /Subtype /Image /Width 4 /Height 3 "
        f"/ColorSpace {space} /BitsPerComponent {bits} /Interpolate true{masked}{written} >>"
        "\nstream\n"
    )
    assert file.stream(image) == colours
    if mask is not None:
        alpha = file.ref(image, "SMask")
        assert file.value(alpha) == (
            "<< /Length 12 /Type /XObject /Subtype /Image /Width 4 /Height 3 "
            "/ColorSpace /DeviceGray /BitsPerComponent 8 /Interpolate true >>\nstream\n"
        )
        assert file.stream(alpha) == mask
    if profile is not None:
        assert file.stream(int(profile[1])) == pictures.read(data, name).profile


def test_a_palettes_transparency_is_its_soft_mask_each_index_its_alpha() -> None:
    """`palette.png` makes its fourth colour transparent, so each pixel of that index is clear
    and every other opaque."""
    data = (TEST_PICTURES / "palette.png").read_bytes()
    decoded = png.read(data)
    assert decoded.transparency == bytes([255, 255, 255, 0])
    file, page = page_of(
        draw(scene(image_of({"role": "picture.logo"})), pictures=handed("palette.png"))
    )
    image, _ = image_dictionary(file, page)
    mask = file.stream(file.ref(image, "SMask"))
    indices = png.samples(decoded)
    each = [(byte >> shift) & 3 for byte in indices for shift in (6, 4, 2, 0)]
    assert list(mask) == [0 if index == 3 else 255 for index in each]
    assert 0 in mask and 255 in mask


def test_an_alpha_channel_is_the_soft_mask_and_the_colours_are_drawn_without_it() -> None:
    data = (TEST_PICTURES / "alpha.png").read_bytes()
    decoded = png.read(data)
    samples = png.samples(decoded)
    file, page = page_of(
        draw(scene(image_of(SOURCES["a picture file of a library"])), pictures=handed("alpha.png"))
    )
    image, dictionary = image_dictionary(file, page)
    assert "/Filter" not in dictionary
    assert file.stream(image) == bytes(b for at, b in enumerate(samples) if at % 4 != 3)
    assert file.stream(file.ref(image, "SMask")) == samples[3::4]


@pytest.mark.parametrize(
    ("frame", "placed"),
    [
        ((0, 0, 50, 50), "50 0 0 -37.5 0 43.75"),
        ((10, 20, 100, 30), "40 0 0 -30 40 50"),
        ((0, 0, 20, 100), "20 0 0 -15 0 57.5"),
        ((5, 5, 4, 3), "4 0 0 -3 5 8"),
    ],
    ids=["square", "wide", "tall", "its-own-size"],
)
def test_a_picture_lies_whole_centred_and_as_large_as_its_frame_allows(
    frame: tuple[float, float, float, float], placed: str
) -> None:
    """As the SVG renderer's `xMidYMid meet` draws it (DEC-025 point 6): scaled by the
    smaller of the two ratios of its frame to its pixels, and centred on the other axis."""
    x, y, width, height = frame
    image = element(
        "image", "figure/picture", x=x, y=y, width=width, height=height,
        preserveAspectRatio="xMidYMid meet", file="photo.jpg", library="piece",
    )  # fmt: skip
    file, page = page_of(draw(scene(image), pictures=handed("colour.jpg")))
    assert file.content(page) == OPENING + f"q {placed} cm /I0 Do Q\n"


def test_a_picture_in_a_group_lies_where_the_group_places_it() -> None:
    picture = image_of(SOURCES["a picture file of the piece"], "figure/card/picture")
    group = element(
        "group", "figure/card", x=10, y=20, width=60, height=60, component="tests/card",
        version="1.0.0", children=[picture],
    )  # fmt: skip
    file, page = page_of(draw(scene(group), pictures=handed("grey.png", "figure/card/picture")))
    assert file.content(page) == (
        OPENING + "q 1 0 0 1 10 20 cm\nq 50 0 0 -37.5 0 43.75 cm /I0 Do Q\nQ\n"
    )


def test_a_frame_of_no_size_draws_nothing_and_embeds_nothing() -> None:
    flat = element(
        "image", "figure/picture", x=0, y=0, width=50, height=0,
        preserveAspectRatio="xMidYMid meet", file="photo.jpg", library="piece",
    )  # fmt: skip
    drawn = draw(scene(flat), pictures=handed("colour.jpg"))
    assert drawn.losses == []
    file, page = page_of(drawn)
    assert file.content(page) == OPENING
    assert file.images(page) == {}


def test_each_picture_lies_once_in_the_file_however_often_it_is_drawn() -> None:
    """Two images of one file, on two pages, and a third of another: two images in the file,
    named in the order the pages first draw them, each page's resources naming both."""

    def slide(trace: str, *shown: str) -> dict[str, Any]:
        children = [
            image_of(SOURCES["a picture file of the piece"], f"{trace}/{at}") for at in shown
        ]
        return element(
            "group", trace, x=0, y=0, width=200, height=100, page=True, children=children
        )

    two = {
        **scene(),
        "pages": ["deck/a", "deck/b"],
        "children": [
            element("group", "deck", x=0, y=0, width=200, height=100,
                    children=[slide("deck/a", "first"), slide("deck/b", "again", "other")])
        ],
    }  # fmt: skip
    shown = {
        **handed("colour.jpg", "deck/a/first"),
        **handed("colour.jpg", "deck/b/again"),
        **handed("alpha.png", "deck/b/other"),
    }
    drawn = draw(two, pictures=shown)
    assert drawn.losses == []
    file = read(drawn.document)
    first, second = file.pages()
    assert re.findall(r"/(I\d) Do", file.content(first)) == ["I0"]
    assert re.findall(r"/(I\d) Do", file.content(second)) == ["I0", "I1"]
    images = file.images(first)
    assert images == file.images(second) and list(images) == ["I0", "I1"]
    data = [stream for _, stream in file.objects.values()]
    assert data.count((TEST_PICTURES / "colour.jpg").read_bytes()) == 1


def test_a_colour_profile_two_pictures_carry_lies_once_in_the_file() -> None:
    """`profile.png` and `profile.jpg` carry the same RGB profile: one stream holds it, with
    three components, and each picture's colour space names it."""
    shown = {**handed("profile.png", "figure/first"), **handed("profile.jpg", "figure/second")}
    first = image_of(SOURCES["a picture file of the piece"], "figure/first")
    second = image_of(SOURCES["a picture file of a library"], "figure/second")
    file, page = page_of(draw(scene(first, second), pictures=shown))
    profiles = {
        int(ref) for image in file.images(page).values()
        for ref in re.findall(r"/ICCBased (\d+) 0 R", file.value(image))
    }  # fmt: skip
    [profile] = profiles
    carried = pictures.read((TEST_PICTURES / "profile.jpg").read_bytes(), "profile.jpg").profile
    assert carried == pictures.read((TEST_PICTURES / "profile.png").read_bytes(), "x.png").profile
    assert file.value(profile) == (
        f"<< /Length {len(carried)} /N 3 /Alternate /DeviceRGB >>\nstream\n"
    )
    assert file.stream(profile) == carried


def with_chunk(data: bytes, kind: bytes, body: bytes) -> bytes:
    """The PNG `data` with the chunk `kind` holding `body` before its image data."""
    at = data.index(b"IDAT") - 4
    added = struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body))
    return data[:at] + added + data[at:]


def test_a_grey_pictures_profile_is_for_grey_colours(tmp_path: Path) -> None:
    """A grey PNG's profile is for one component, and its alternate grey."""
    rgb = pictures.read((TEST_PICTURES / "profile.png").read_bytes(), "profile.png").profile
    grey = rgb[:16] + b"GRAY" + rgb[20:]
    data = with_chunk(
        (TEST_PICTURES / "grey.png").read_bytes(), b"iCCP", b"grey\0\0" + zlib.compress(grey)
    )
    (tmp_path / "grey.png").write_bytes(data)
    file, page = page_of(
        draw(
            scene(image_of(SOURCES["a picture file of the piece"])),
            pictures=handed("grey.png", folder=tmp_path),
        )
    )
    _, dictionary = image_dictionary(file, page)
    profile = int(re.findall(r"/ICCBased (\d+) 0 R", dictionary)[0])
    assert file.value(profile).startswith(f"<< /Length {len(grey)} /N 1 /Alternate /DeviceGray >>")
    assert file.stream(profile) == grey


@pytest.mark.parametrize(
    ("name", "given", "key"),
    [
        ("grey.png", struct.pack(">H", 128), "[128 128]"),
        ("profile.png", struct.pack(">HHH", 1, 2, 3), "[1 1 2 2 3 3]"),
    ],
    ids=["grey", "rgb"],
)
def test_a_colour_a_png_names_transparent_is_a_colour_key(
    tmp_path: Path, name: str, given: bytes, key: str
) -> None:
    (tmp_path / name).write_bytes(with_chunk((TEST_PICTURES / name).read_bytes(), b"tRNS", given))
    file, page = page_of(
        draw(
            scene(image_of(SOURCES["a picture file of the piece"])),
            pictures=handed(name, folder=tmp_path),
        )
    )
    _, dictionary = image_dictionary(file, page)
    assert f" /Mask {key}" in dictionary
    assert "/SMask" not in dictionary


@pytest.mark.parametrize("source", list(SOURCES))
def test_an_image_handed_no_picture_is_left_out_and_says_why(source: str) -> None:
    drawn = draw(scene(image_of(SOURCES[source])), pictures={})
    [loss] = drawn.losses
    assert (loss.what, loss.did) == ("figure/picture", "left-out")
    assert (
        loss.why
        == {
            "a picture file of the piece": "the picture file `photo.jpg` of `piece` is not found "
            "to draw in `default`: `pkit visual check flow` names why",
            "a picture file of a library": "the picture file `logo.png` of `tests@1.0.0` is not "
            "found to draw in `default`: `pkit visual check flow` names why",
            "a picture role": "the brand gives the picture role `picture.logo` no file in "
            "`default`",
        }[source]
    )
    file, page = page_of(drawn)
    assert file.content(page) == OPENING


def damaged_image_data(data: bytes) -> bytes:
    """The PNG `data` with its image data damaged, its chunk's checksum still whole, so the
    picture reader reads it and only a decoder finds the damage."""
    at = data.index(b"IDAT") - 4
    (length,) = struct.unpack(">I", data[at : at + 4])
    body = b"\x78\x9c" + b"\xff" * (length - 2)
    whole = b"IDAT" + body
    return (
        data[:at]
        + struct.pack(">I", length)
        + whole
        + struct.pack(">I", zlib.crc32(whole))
        + data[at + 12 + length :]
    )


@pytest.mark.parametrize(
    ("name", "make", "why"),
    [
        (
            "deep.png",
            None,
            "`deep.png` is a PNG of 16 bits for each sample, which the capability does not read",
        ),
        (
            "alpha.png",
            damaged_image_data,
            "`alpha.png` cannot be decoded: its image data, `IDAT`, is damaged",
        ),
        (
            "palette.png",
            damaged_image_data,
            "`palette.png` cannot be decoded: its image data, `IDAT`, is damaged",
        ),
        (
            "grey.png",
            damaged_image_data,
            "`grey.png` cannot be decoded: its image data, `IDAT`, is damaged",
        ),
        (
            "profile.png",
            damaged_image_data,
            "`profile.png` cannot be decoded: its image data, `IDAT`, is damaged",
        ),
        (
            "grey.png",
            lambda data: built(2**27 + 1, 1, 1, png.GREY, [], data=zlib.compress(bytes(2**24 + 2))),
            "`grey.png` cannot be decoded: its 134217729 × 1 pixels would take 129 MiB decoded, "
            "more than the 128 MiB decoded here",
        ),
        (
            "colour.jpg",
            lambda data: data[:200],
            "`colour.jpg` cannot be read: a segment runs past the end of the file",
        ),
    ],
    ids=[
        "refused-by-the-reader",
        "alpha-undecodable",
        "palette-undecodable",
        "grey-undecodable",
        "rgb-undecodable",
        "too-large",
        "cut-short",
    ],
)
def test_a_picture_that_cannot_be_read_or_decoded_is_left_out_and_says_why(
    tmp_path: Path, name: str, make: Any, why: str
) -> None:
    data = (TEST_PICTURES / name).read_bytes()
    (tmp_path / name).write_bytes(make(data) if make else data)
    shown = {**handed(name, folder=tmp_path), **handed("colour.jpg", "figure/other")}
    drawn = draw(
        scene(
            image_of(SOURCES["a picture role"]),
            image_of(SOURCES["a picture file of the piece"], "figure/other"),
        ),
        pictures=shown,
    )
    assert [loss.as_dict() for loss in drawn.losses] == [
        {
            "plugin": "pdf",
            "what": "figure/picture",
            "did": "left-out",
            "why": f"the picture role `picture.logo` cannot be drawn: {why}",
        }
    ]
    file, page = page_of(drawn)
    assert file.content(page) == OPENING + "q 50 0 0 -37.5 0 43.75 cm /I0 Do Q\n"


def test_a_picture_is_handed_by_the_images_trace_id_not_by_its_name() -> None:
    first = image_of({"file": "photo.jpg", "library": "piece"}, "figure/first")
    second = image_of({"file": "photo.jpg", "library": "piece"}, "figure/second")
    drawn = draw(scene(first, second), pictures=handed("colour.jpg", "figure/second"))
    assert [loss.what for loss in drawn.losses] == ["figure/first"]
    file, page = page_of(drawn)
    assert file.content(page).count(" Do Q") == 1


def test_a_picture_drawn_twice_gives_the_same_bytes_its_decoded_data_uncompressed() -> None:
    """What the renderer decodes, a soft mask and the colours of a PNG with alpha, is written
    as it is, so no build of zlib can move a byte of it; a JPEG and a PNG's image data are the
    file's own."""
    children = [image_of(SOURCES["a picture file of the piece"], f"figure/{at}") for at in range(3)]
    shown = {
        **handed("alpha.png", "figure/0"),
        **handed("palette.png", "figure/1"),
        **handed("profile.jpg", "figure/2"),
    }
    first, second = (draw(scene(*children), pictures=shown) for _ in range(2))
    assert first.document == second.document
    file = read(first.document)
    filters = [re.findall(r"/Filter /(\w+)", value) for value, _ in file.objects.values()]
    assert sorted(found for each in filters for found in each) == ["DCTDecode", "FlateDecode"]


# --- pages --------------------------------------------------------------------------------------


def test_each_page_of_the_scene_is_a_page_of_the_file_in_order_at_its_size() -> None:
    def slide(trace: str, width: float, words: str) -> dict[str, Any]:
        said = dict(named(["Source Sans Pro"]), id=f"{trace}/head", text=words)
        said["paragraphs"] = [[run(words, fill="ink")]]
        said["lines"] = [line(0, 15, (0, words, 40))]
        return element(
            "group", trace, x=0, y=0, width=width, height=100, page=True, children=[said]
        )

    three = {
        **scene(),
        "pages": ["deck/slides[a]", "deck/slides[b]", "deck/slides[c]"],
        "children": [
            element(
                "group",
                "deck",
                x=0,
                y=0,
                width=400,
                height=300,
                children=[
                    slide("deck/slides[a]", 400, "One"),
                    slide("deck/slides[b]", 200, "Two"),
                    slide("deck/slides[c]", 400, "Three"),
                ],
            )
        ],
    }
    drawn = draw(three)
    assert drawn.pages == ["deck/slides[a]", "deck/slides[b]", "deck/slides[c]"]
    file = read(drawn.document)
    pages = file.pages()
    assert [file.lines(page) for page in pages] == [["One"], ["Two"], ["Three"]]
    assert [re.findall(r"/MediaBox \[([^\]]*)\]", file.value(page)) for page in pages] == [
        ["0 0 300 75"],
        ["0 0 150 75"],
        ["0 0 300 75"],
    ]
    assert "/Count 3 >>" in file.value(2)
    # One font for the file, shared by its pages, holding every page's characters.
    assert len({font for page in pages for font in file.fonts(page).values()}) == 1


def tall(height: float, width: float = 390) -> dict[str, Any]:
    """A scene of one page, `width` by `height` px, holding the pinned shapes."""
    return {**SHAPES, "children": [{**SHAPES["children"][0], "width": width, "height": height}]}


def test_a_page_past_the_largest_a_reader_holds_is_drawn_smaller_its_proportions_kept() -> None:
    """A phone's page of 30,000 px is 22,500 pt tall: drawn 0.64 as large, it fits."""
    drawn = draw(tall(30000))
    file, page = page_of(drawn)
    assert re.findall(r"/MediaBox \[([^\]]*)\]", file.value(page)) == ["0 0 187.2 14400"]
    assert file.content(page).startswith("0.48 0 0 -0.48 0 14400 cm 4 M\n")
    assert drawn.losses == [
        seam.Loss(
            "pdf",
            "figure",
            seam.APPROXIMATED,
            "the page measures 292.5 by 22500 pt, past the 14400 pt a page of PDF takes on a "
            "side, so it is drawn 0.64 as large, its proportions kept",
        )
    ]


def test_a_page_too_wide_for_a_reader_is_drawn_smaller_by_its_width() -> None:
    drawn = draw(tall(100, width=40000))
    file, page = page_of(drawn)
    assert re.findall(r"/MediaBox \[([^\]]*)\]", file.value(page)) == ["0 0 14400 36"]
    assert file.content(page).startswith("0.36 0 0 -0.36 0 36 cm 4 M\n")
    assert [loss.what for loss in drawn.losses] == ["figure"]


def test_a_page_as_large_as_a_reader_holds_draws_as_before() -> None:
    drawn = draw(tall(pdf.LARGEST / pdf.SCALE))
    file, page = page_of(drawn)
    assert pdf.LARGEST / pdf.SCALE == 19200
    assert re.findall(r"/MediaBox \[([^\]]*)\]", file.value(page)) == ["0 0 292.5 14400"]
    assert file.content(page).startswith("0.75 0 0 -0.75 0 14400 cm 4 M\n")
    assert drawn.losses == []


def test_beside_a_page_drawn_smaller_every_other_page_of_the_file_draws_as_before() -> None:
    small = {**SHAPES["children"][0], "id": "deck/small", "page": True}
    large = {**small, "id": "deck/large", "height": 30000}
    both = {**SHAPES, "pages": ["deck/small", "deck/large"], "children": [small, large]}
    alone = {**SHAPES, "pages": ["deck/small"], "children": [small]}
    drawn = draw(both)
    file = read(drawn.document)
    first, second = file.pages()
    held, page = page_of(draw(alone))
    assert file.content(first) == held.content(page)
    boxes = [
        re.findall(r"/MediaBox \[([^\]]*)\]", each.value(at))
        for each, at in ((file, first), (held, page))
    ]
    assert boxes == [["0 0 150 75"], ["0 0 150 75"]]
    assert file.content(second).startswith("0.48 0 0 -0.48 0 14400 cm 4 M\n")
    assert [loss.what for loss in drawn.losses] == ["deck/large"]


# --- a physical size ----------------------------------------------------------------------------

#: A poster's trim size, A1 upright, in millimetres, and its page, 640 px wide and as tall as
#: the proportion makes it, as the engine sets it (DEC-034 point 3).
A1 = {"width": 594, "height": 841}


def poster(physical: dict[str, Any] = A1, *ids: str) -> dict[str, Any]:
    """A scene of the pinned shapes on one page, or on a page for each of `ids`, 640 px wide,
    whose root holds `physical`."""
    height = round(640 * physical["height"] / physical["width"], 2)
    page = {**SHAPES["children"][0], "width": 640, "height": height}
    pages = [{**page, "id": id_} for id_ in ids] or [page]
    return {
        **SHAPES,
        "pages": [each["id"] for each in pages],
        "children": pages,
        "physical-size": physical,
    }


def test_a_page_of_a_top_with_a_physical_size_is_that_size_by_one_scale() -> None:
    """594 by 841 mm is 1683.78 by 2383.94 pt, and the page's 640 px are 1683.78 pt."""
    drawn = draw(poster())
    file, page = page_of(drawn)
    assert re.findall(r"/MediaBox \[([^\]]*)\]", file.value(page)) == ["0 0 1683.78 2383.94"]
    assert file.content(page).startswith("2.630906 0 0 -2.630906 0 2383.94 cm 4 M\n")
    assert drawn.losses == []


def test_every_page_of_the_scene_takes_the_physical_size() -> None:
    file = read(draw(poster(A1, "deck/one", "deck/two")).document)
    boxes = [re.findall(r"/MediaBox \[([^\]]*)\]", file.value(page)) for page in file.pages()]
    assert boxes == [["0 0 1683.78 2383.94"], ["0 0 1683.78 2383.94"]]


def test_the_shapes_draw_as_on_a_page_with_none_but_for_the_scale() -> None:
    """One scale maps the scene onto the page: what the page draws is the same."""
    unit = read(draw(tall(round(640 * 841 / 594, 2), width=640)).document)
    physical = read(draw(poster()).document)
    [unit_page], [physical_page] = unit.pages(), physical.pages()
    head = re.compile(r"\A[^\n]* cm 4 M\n")
    assert head.sub("", physical.content(physical_page)) == head.sub("", unit.content(unit_page))


def test_a_physical_size_past_the_largest_a_reader_holds_is_drawn_smaller() -> None:
    """6 m by 1 m is 17007.87 pt wide: drawn 0.8467 as large, it fits."""
    drawn = draw(poster({"width": 6000, "height": 1000}))
    file, page = page_of(drawn)
    assert re.findall(r"/MediaBox \[([^\]]*)\]", file.value(page)) == ["0 0 14400 2400"]
    assert file.content(page).startswith("22.5 0 0 -22.5 0 2400 cm 4 M\n")
    assert drawn.losses == [
        seam.Loss(
            "pdf",
            "figure",
            seam.APPROXIMATED,
            "the page measures 17007.87 by 2834.65 pt, past the 14400 pt a page of PDF takes "
            "on a side, so it is drawn 0.8467 as large, its proportions kept",
        )
    ]


def test_the_file_names_its_language_and_its_renderer() -> None:
    file = read(draw(SHAPES).document)
    root = int(re.findall(r"/Root (\d+) 0 R", file.trailer)[0])
    assert file.value(root) == "<< /Type /Catalog /Pages 2 0 R /Lang (en) >>"
    info = int(re.findall(r"/Info (\d+) 0 R", file.trailer)[0])
    assert file.value(info) == "<< /Producer (pkit visual-communication pdf 1.6.0) >>"


# --- the same bytes -----------------------------------------------------------------------------


def test_the_same_scene_and_values_give_the_same_bytes() -> None:
    first, second = draw(scene(TITLE, SAID)), draw(scene(TITLE, SAID))
    assert first.document == second.document
    data = first.document
    assert b"CreationDate" not in data and b"ModDate" not in data
    # The file's /ID is the first 16 bytes of the SHA-256 of what lies before its table.
    table = data.rindex(b"\nxref\n") + 1
    identity = hashlib.sha256(data[:table]).hexdigest()[:32].upper()
    assert f"/ID [<{identity}> <{identity}>]".encode() in data
    assert draw(scene(TITLE)).document != data


# --- a family's name ----------------------------------------------------------------------------

#: A name's characters a PDF name holds as themselves: the regular characters but `#`.
REGULAR = re.compile(r"/[!-~]*")


def name_text(written: str) -> str:
    """A PDF name read back: each `#` and two hexadecimal digits as the byte they give,
    the bytes as UTF-8."""
    data = re.sub(rb"#([0-9A-F]{2})", lambda m: bytes([int(m[1], 16)]), written[1:].encode())
    return data.decode("utf-8", "surrogatepass")


def test_a_familys_name_is_written_as_a_pdf_name_as_pinned() -> None:
    assert pdf.pdf_name("A b/(c)<d>[e]{f}%#\x00é") == (
        "/A#20b#2F#28c#29#3Cd#3E#5Be#5D#7Bf#7D#25#23#EF#BF#BD#C3#A9"
    )
    assert pdf.pdf_string("a(b)\\c") == "(a\\(b\\)\\\\c)"
    assert pdf.pdf_string("é\n") == "(\\376\\377\\000\\351\\000\\012)"


def test_a_familys_name_reaches_each_font_dictionary_as_one_name_and_nothing_else() -> None:
    families = [*HOSTILE, "Nul\x00l", "Space and /slash"]
    drawn = draw(scene(named(families)), files={})
    assert drawn.losses == []
    file, page = page_of(drawn)
    [font] = file.fonts(page).values()
    # The text is drawn in the first family; its name in the Type 0 font, its CID font and
    # its descriptor is one token each, of regular characters alone.
    cid_font = file.descendant(font)
    descriptor = file.ref(cid_font, "FontDescriptor")
    for number, key in ((font, "BaseFont"), (cid_font, "BaseFont"), (descriptor, "FontName")):
        [written] = re.findall(rf"/{key} (\S+) ", file.value(number))
        assert REGULAR.fullmatch(written)
        tag, _, family = name_text(written).partition("+")
        assert re.fullmatch("[A-Z]{6}", tag) and family == HOSTILE[0]
    for family in families:
        tag, _, back = name_text(pdf.pdf_name(f"ABCDEF+{family}")).partition("+")
        assert back == family.replace("\x00", "�")


def test_every_family_a_run_draws_in_is_named_as_itself() -> None:
    every = "".join(chr(code) for code in range(1, 0x10000)) + "\U0001f600\U0010ffff"
    written = pdf.pdf_name(every)
    assert REGULAR.fullmatch(written)
    assert name_text(written) == every


# --- losses -------------------------------------------------------------------------------------


def test_what_it_cannot_draw_is_a_loss_in_the_seams_form() -> None:
    drawn = draw(
        scene(
            element("polygon", "figure/arrow", x=0, y=0, width=10, height=10),
            element("box", "figure/odd", x=0, y=0, width=10, height=10, fill="no-such-role"),
            element("image", "figure/picture", x=0, y=0, width=10, height=10, output="square"),
        )
    )
    no_variant = "the produced output `square` has no variant for `default`"
    assert [loss.as_dict() for loss in drawn.losses] == [
        {
            "plugin": "pdf",
            "what": "figure/arrow",
            "did": "refused",
            "why": "the pdf renderer draws no `polygon`",
        },
        {
            "plugin": "pdf",
            "what": "figure/odd",
            "did": "left-out",
            "why": "the brand gives the role `no-such-role` of its fill no colour in `default`",
        },
        {
            "plugin": "pdf",
            "what": "figure/picture",
            "did": "left-out",
            "why": f"{no_variant}: run `pkit visual produce flow square`",
        },
    ]
    file, page = page_of(drawn)
    assert file.content(page) == OPENING


def test_a_line_that_holds_neither_its_ends_nor_its_points_is_refused() -> None:
    endless = element(
        "line", "figure/links[ab]/l", x=0, y=0, width=0, height=0, stroke="ink",
        **{"marker-end": "arrow"},
    )  # fmt: skip
    drawn = draw(scene(endless))
    why = "the line holds neither its ends, `x1 y1 x2 y2`, nor its points"
    assert [loss.as_dict() for loss in drawn.losses] == [
        {"plugin": "pdf", "what": "figure/links[ab]/l", "did": "refused", "why": why}
    ]
    file, page = page_of(drawn)
    assert file.content(page) == OPENING


def test_a_run_painted_with_a_role_the_brand_gives_no_colour_is_a_loss_and_not_shown() -> None:
    lost = element(
        "text", "figure/lost", x=0, y=0, width=200, height=20, text="ab",
        paragraphs=[[run("a", fill="ink"), run("b", fill="no-such-role")]],
        lines=[line(0, 15, (0, "a", 10), (1, "b", 10))],
        **{"line-height": 20, "measured-height": 20},
    )  # fmt: skip
    drawn = draw(scene(lost))
    assert [loss.as_dict() for loss in drawn.losses] == [
        {
            "plugin": "pdf",
            "what": "figure/lost",
            "did": "left-out",
            "why": "the brand gives the role `no-such-role` of its fill no colour in `default`",
        }
    ]
    # The run is drawn unpainted, so its text is still read, as the SVG renderer leaves it.
    file, page = page_of(drawn)
    assert "3 Tr\n" in file.content(page)
    assert file.lines(page) == ["ab"]


def no_outlines(path: Path) -> Path:
    """The test font with its CFF table taken out, so it holds no outlines a PDF embeds."""
    font = TTFont(str(FONT))
    del font["CFF "]
    font.save(str(path))
    return path


def test_text_in_a_family_with_no_outlines_is_a_loss_left_out_in_its_place(
    tmp_path: Path,
) -> None:
    def text(first: str) -> dict[str, Any]:
        return element(
            "text", "figure/bare", x=0, y=0, width=200, height=20, text="Hi there",
            paragraphs=[
                [run("Hi", fill="ink", **{"font-family": [first]}), run(" there", fill="ink")]
            ],
            lines=[line(0, 15, (0, "Hi", 14), (1, " there", 40))],
            **{"line-height": 20, "measured-height": 20},
        )  # fmt: skip

    bare = no_outlines(tmp_path / "Bare.otf")
    drawn = draw(scene(text("Bare")), files={"Bare": bare})
    why = "the font file of the family `Bare` holds neither CFF nor TrueType outlines"
    assert [loss.as_dict() for loss in drawn.losses] == [
        {
            "plugin": "pdf",
            "what": "figure/bare",
            "did": "left-out",
            "why": f"{why}, which a PDF embeds",
        }
    ]
    file, page = page_of(drawn)
    # The family is not embedded: the file holds one font, the run's that is drawn.
    [font] = file.fonts(page).values()
    assert re.findall(r"/BaseFont /\w{6}\+(\S+)", file.value(font)) == ["Source#20Sans#20Pro"]
    fonts = [value for value, _ in file.objects.values() if "/Subtype /Type0 " in value]
    assert len(fonts) == 1
    assert b"/FontFile2" not in drawn.document
    assert file.lines(page) == [" there"]
    # The run drawn stays where the engine placed it, after the text left out.
    placed = r"1 0 0 -1 [-\d.]+ [-\d.]+ Tm"
    whole, whole_page = page_of(draw(scene(text("Source Sans Pro"))))
    [_, after] = re.findall(placed, whole.content(whole_page))
    assert re.findall(placed, file.content(page)) == [after]


# --- the declaration ----------------------------------------------------------------------------


def test_it_draws_every_primitive_it_declares_and_declares_every_one_it_draws() -> None:
    declared = set(pdf_declaration.DECLARATION["draws"])
    assert declared == {"group", "box", "ellipse", "line", "text", "image", "path"}
    drawn_by = {name[1:] for name in vars(pdf._Document) if name[1:] in declared}
    assert drawn_by == declared


def test_it_declares_each_property_of_an_image_of_every_source_as_the_svg_renderer_does() -> None:
    """So no image is a `refused` loss, nor any of its properties `left-out`, whatever it
    shows (DEC-025 point 7)."""
    image = pdf_declaration.DECLARATION["draws"]["image"]
    assert image == svg_declaration.DECLARATION["draws"]["image"]
    assert set(image) == {"x", "y", "width", "height", *pdf_declaration.IMAGE}
    assert set(pdf_declaration.IMAGE) >= {"output", "variants", "points", "file", "library", "role"}


def test_it_is_shipped_through_the_seam_as_plain_data_at_the_seams_version() -> None:
    declared = seam.declaration("pdf", seam.RENDERER)
    assert declared == pdf_declaration.DECLARATION
    assert (pdf.NAME, pdf.VERSION, declared["seam"]) == ("pdf", "1.6.0", seam.SEAM_VERSION)
    assert (declared["programs"], declared["services"], declared["profile"]) == ([], [], "default")
    assert declared["unit"] == {"scene": "px", "page": "pt", "scale": 0.75}
    assert declared["physical-size"] == {"page": True, "maps": True}
    assert declared["not-carried"] == ["alternative text", "reading order", "structure"]
