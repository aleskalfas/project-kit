"""The PDF renderer (visual-communication DEC-005 points 4, 5, 9 and 10, DEC-006 point 7):
what it declares, what it draws, and what it reports it lost.

The reference outputs below are pinned to the renderer's version, 1.0.0. A change that
gives another output for the same scene and values raises the version, and changes them
with it (DEC-005 point 9). A page's content is pinned whole. An embedded font is pinned by
the glyphs its subset holds and the characters its map gives them, not by its bytes,
which are fontTools'. The files are read here by their own table of objects, as a reader
of PDF reads them (`read`); the export of a piece as PDF is
`test_visual_communication_export.py`'s.
"""

from __future__ import annotations

import hashlib
import io
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fontTools.cffLib import CFFFontSet
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont

from tests.in_process import load
from tests.test_visual_communication_svg import (
    COLOURS,
    FONT,
    HOSTILE,
    SAID,
    SEMIBOLD,
    SHAPES,
    TIES,
    TITLE,
    element,
    line,
    named,
    run,
    scene,
)

pdf, pdf_declaration, seam = load(
    "visual-communication", "plugins.pdf", "plugins.pdf_declaration", "plugins.seam"
)

#: The families of the runs below, each with its committed file.
FILES = {"Source Sans Pro": FONT, "Source Sans Pro Semibold": SEMIBOLD}


def draw(drawn: dict[str, Any], *, key: str = "default", files: Any = None) -> Any:
    found = files or FILES
    return pdf.render(
        drawn, key=key, colours=COLOURS, font_file=lambda family: found.get(family, FONT),
        pictures={},
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


def test_shapes_are_drawn_as_pinned_for_version_1_0_0() -> None:
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


def test_a_connector_and_its_arrowheads_are_drawn_as_pinned_for_version_1_0_0() -> None:
    drawn = draw(TIES)
    assert drawn.losses == []
    file, page = page_of(drawn)
    # The connector through its points, its arrowhead a triangle ten px long (five strokes)
    # and ten across, its tip at the end; the rule with one at each end, translucent.
    assert file.content(page) == (
        OPENING + "q 0 0 0 RG 2 w\n10 20 m 60 20 l 60 60 l 110 60 l S\n"
        "0 0 0 rg\n100 65 m 110 60 l 100 55 l h f\nQ\n"
        "q /A0 gs 0 0 0 RG 1 w\n0 90 m 200 90 l S\n"
        "/A1 gs 0 0 0 rg\n5 87.5 m 0 90 l 5 92.5 l h f\n195 92.5 m 200 90 l 195 87.5 l h f\nQ\n"
    )
    resources = file.value(file.ref(page, "Resources"))
    assert "/A0 << /Type /ExtGState /CA 0.25 >> /A1 << /Type /ExtGState /ca 0.25 >>" in resources


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


def test_the_file_names_its_language_and_its_renderer() -> None:
    file = read(draw(SHAPES).document)
    root = int(re.findall(r"/Root (\d+) 0 R", file.trailer)[0])
    assert file.value(root) == "<< /Type /Catalog /Pages 2 0 R /Lang (en) >>"
    info = int(re.findall(r"/Info (\d+) 0 R", file.trailer)[0])
    assert file.value(info) == "<< /Producer (pkit visual-communication pdf 1.0.0) >>"


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
            element("path", "figure/arrow", x=0, y=0, width=10, height=10),
            element("box", "figure/odd", x=0, y=0, width=10, height=10, fill="no-such-role"),
            element("image", "figure/picture", x=0, y=0, width=10, height=10, output="square"),
        )
    )
    assert [loss.as_dict() for loss in drawn.losses] == [
        {
            "plugin": "pdf",
            "what": "figure/arrow",
            "did": "refused",
            "why": "the pdf renderer draws no `path`",
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
            "did": "refused",
            "why": "the pdf renderer draws no `image`",
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


# --- the declaration ----------------------------------------------------------------------------


def test_it_draws_every_primitive_it_declares_and_declares_every_one_it_draws() -> None:
    declared = set(pdf_declaration.DECLARATION["draws"])
    assert declared == {"group", "box", "ellipse", "line", "text"}
    kinds = declared | {"path", "image"}
    drawn_by = {name[1:] for name in vars(pdf._Document) if name[1:] in kinds}
    assert drawn_by == declared


def test_it_is_shipped_through_the_seam_as_plain_data_at_the_seams_version() -> None:
    declared = seam.declaration("pdf", seam.RENDERER)
    assert declared == pdf_declaration.DECLARATION
    assert (pdf.NAME, pdf.VERSION, declared["seam"]) == ("pdf", "1.0.0", seam.SEAM_VERSION)
    assert (declared["programs"], declared["services"], declared["profile"]) == ([], [], "default")
    assert declared["unit"] == {"scene": "px", "page": "pt", "scale": 0.75}
    assert declared["not-carried"] == ["alternative text", "reading order", "structure"]
