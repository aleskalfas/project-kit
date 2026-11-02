"""Text measured from committed fonts, and lines broken by the engine (visual-communication
DEC-005 point 4, DEC-004 point 9).

- **Measured from files.** Each run of text is shaped with HarfBuzz (uharfbuzz) from the
  committed font file a family names, and the font's metrics are read with fontTools.
  A font role gives a list of families: the first measures each character it has, the
  next the rest. Never a font found on the machine.
- **Refused before layout.** A family with no committed file raises `MissingFont`, and a
  character no family measures raises `MissingGlyph`, each naming what is missing.
- **Lines.** Each paragraph (the text split at its line feeds) is broken at Unicode's
  break opportunities (UAX #14, through uniseg) and the language's own rules, kept as
  data here (`LANGUAGE_RULES`). Lines are filled greedily against the planned width
  minus a margin of 2 % of the em (`BREAK_MARGIN`), and placed in the planned width, so
  a renderer's slightly different metrics move no word.
- **No shrinking.** A word longer than its line breaks after a `/`, or is left whole
  and the text overflows.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path

import uharfbuzz as hb
from fontTools.ttLib import TTFont
from uniseg.linebreak import line_break_boundaries

from _lib.env import MissingFont

#: Lines are broken against the planned width minus this share of the em.
BREAK_MARGIN = 0.02

#: How the engine measures every text in the default font profile.
MEASURED = "file"

#: The rule that keeps a one-letter word off a line's end: it moves to the next line
#: with the word after it.
ONE_LETTER_WORD = "one-letter-word"

#: Each language's line-breaking rules beyond Unicode's, by its primary language subtag.
#: A new language's rules arrive with a release of the capability (DEC-005 point 4).
LANGUAGE_RULES: Mapping[str, frozenset[str]] = {
    "cs": frozenset({ONE_LETTER_WORD}),
}

_ONE_LETTER = re.compile(r"(?<!\w)[^\W\d_] +")


class MissingGlyph(MissingFont):
    """A character no family of a font role measures."""


class Face:
    """One committed font file, measured exactly."""

    def __init__(self, family: str, path: Path) -> None:
        data = path.read_bytes()
        self.family = family
        self.path = path
        self.sha256 = hashlib.sha256(data).hexdigest()
        font = TTFont(str(path), lazy=True)
        try:
            self._cmap = frozenset(font.getBestCmap() or {})
            self.upem = font["head"].unitsPerEm
            self.ascender = font["hhea"].ascent / self.upem
            self.descender = -font["hhea"].descent / self.upem
        finally:
            font.close()
        self._font = hb.Font(hb.Face(hb.Blob(data)))
        self._advances: dict[str, float] = {}

    def has(self, character: str) -> bool:
        return ord(character) in self._cmap

    def advance(self, text: str) -> float:
        """How far a run moves the pen, in ems, shaped with the font's default features."""
        if text not in self._advances:
            buffer = hb.Buffer()
            buffer.add_str(text)
            buffer.guess_segment_properties()
            hb.shape(self._font, buffer)
            self._advances[text] = sum(p.x_advance for p in buffer.glyph_positions) / self.upem
        return self._advances[text]


class Faces:
    """The faces one scene measures with, each file read once."""

    def __init__(self, font_file: Callable[[str], Path]) -> None:
        self._font_file = font_file
        self._faces: dict[str, Face] = {}

    def face(self, family: str) -> Face:
        """A family's face. Raises `MissingFont` where it has no committed file."""
        if family not in self._faces:
            path = self._font_file(family)
            if not path.is_file():
                raise MissingFont(f"the font family {family!r} has no file at {path}")
            self._faces[family] = Face(family, path)
        return self._faces[family]


@dataclass(frozen=True)
class Style:
    """A typography role resolved for measuring: its faces, size, weight and line height."""

    role: str
    families: tuple[str, ...]
    faces: tuple[Face, ...] = field(compare=False)
    size: float
    weight: float | str | None
    line_height: float

    @classmethod
    def of_role(cls, role: str, value: Mapping, faces: Faces) -> Style:
        """A typography role's resolved value as a style: DTCG's `fontFamily` (a family or
        a list), `fontSize` in px, `lineHeight` as a ratio of the size, `fontWeight`, and a
        `letterSpacing` of zero if any. Raises `ValueError` where the value is not a
        typography the engine measures, and `MissingFont`."""
        if not isinstance(value, Mapping):
            raise ValueError(f"the role @{role} is not a typography")
        families = value.get("fontFamily")
        if isinstance(families, str):
            families = [families]
        if not isinstance(families, list) or not families:
            raise ValueError(f"the role @{role} names no font family")
        size = value.get("fontSize")
        if not isinstance(size, Mapping) or size.get("unit") != "px":
            raise ValueError(f"the role @{role} gives no font size in px")
        ratio = value.get("lineHeight")
        if not isinstance(ratio, (int, float)) or isinstance(ratio, bool):
            raise ValueError(f"the role @{role} gives no line height as a number")
        spacing = value.get("letterSpacing")
        if isinstance(spacing, Mapping) and spacing.get("value") not in (0, 0.0):
            raise ValueError(
                f"the role @{role} spaces its letters, which format 1 does not measure"
            )
        px = float(size["value"])
        return cls(
            role=role,
            families=tuple(str(family) for family in families),
            faces=tuple(faces.face(str(family)) for family in families),
            size=px,
            weight=value.get("fontWeight"),
            line_height=px * float(ratio),
        )

    def check(self, text: str, where: str) -> None:
        """Raises `MissingGlyph` for the first character of `text` no family measures."""
        for character in text:
            if character != "\n" and not any(face.has(character) for face in self.faces):
                raise MissingGlyph(
                    f"no font family of @{self.role} ({', '.join(self.families)}) measures "
                    f"{character!r} (U+{ord(character):04X}) in {where}"
                )

    def _runs(self, text: str) -> list[tuple[Face, str]]:
        runs: list[tuple[Face, str]] = []
        for character in text:
            face = next((f for f in self.faces if f.has(character)), self.faces[0])
            if runs and runs[-1][0] is face:
                runs[-1] = (face, runs[-1][1] + character)
            else:
                runs.append((face, character))
        return runs

    def width(self, text: str) -> float:
        """How wide a text is drawn, in px: trailing spaces do not count."""
        return sum(face.advance(run) for face, run in self._runs(text.rstrip(" "))) * self.size

    def faces_used(self, text: str) -> tuple[Face, ...]:
        """The faces that measure some character of `text`, in the role's order; the
        first family's where it has no character."""
        used = {face.family for face, _ in self._runs(text.replace("\n", ""))}
        return tuple(face for face in self.faces if face.family in used) or self.faces[:1]

    @property
    def baseline(self) -> float:
        """The first baseline below the top of a line, the leading split evenly, from the
        first family's metrics."""
        face = self.faces[0]
        content = (face.ascender + face.descender) * self.size
        return (self.line_height - content) / 2 + face.ascender * self.size


@dataclass(frozen=True)
class Broken:
    """A text broken into lines: each line, its drawn width, and whether one is wider
    than the planned width."""

    lines: tuple[str, ...]
    widths: tuple[float, ...]
    overflow: bool

    @property
    def natural(self) -> float:
        return max(self.widths, default=0.0)


def _units(paragraph: str, language: str) -> list[str]:
    """The paragraph cut at each break opportunity Unicode's rules and the language's
    allow; each unit keeps its trailing spaces."""
    ends = [end for end in line_break_boundaries(paragraph) if 0 < end < len(paragraph)]
    if ONE_LETTER_WORD in LANGUAGE_RULES.get(language.split("-")[0].lower(), frozenset()):
        bound = {match.end() for match in _ONE_LETTER.finditer(paragraph)}
        ends = [end for end in ends if end not in bound]
    units, start = [], 0
    for end in [*ends, len(paragraph)]:
        units.append(paragraph[start:end])
        start = end
    return units


def _after_slashes(unit: str) -> list[str]:
    pieces = re.split(r"(?<=/)", unit)
    return [piece for piece in pieces if piece]


def break_lines(text: str, width: float | None, style: Style, language: str) -> Broken:
    """`text` broken into lines for a planned width; with no width, each paragraph is one
    line, as wide as it is."""
    lines: list[str] = []
    if text:
        for paragraph in text.split("\n"):
            lines.extend(
                [paragraph.rstrip(" ")]
                if width is None
                else _paragraph(paragraph, width, style, language)
            )
    widths = tuple(style.width(line) for line in lines)
    overflow = width is not None and any(w > width for w in widths)
    return Broken(tuple(lines), widths, overflow)


def _paragraph(paragraph: str, width: float, style: Style, language: str) -> list[str]:
    limit = width - BREAK_MARGIN * style.size
    lines: list[str] = []
    current = ""
    for unit in _units(paragraph, language):
        pieces = _after_slashes(unit) if style.width(unit) > limit else [unit]
        for piece in pieces:
            if current and style.width(current + piece) > limit:
                lines.append(current.rstrip(" "))
                current = piece
            else:
                current += piece
    lines.append(current.rstrip(" "))
    return lines
