"""Text measured from committed fonts, and lines broken by the engine (visual-communication
DEC-005 point 4, DEC-004 point 9, DEC-012 point 4).

- **Runs.** A text is one or more runs, each a span of it set in one typography role
  (`Run`), joined in order. A text of one role is one run.
- **Measured from files.** Each run is shaped with HarfBuzz (uharfbuzz), in pieces of
  one font each, from the committed font file a family names, and the font's metrics are
  read with fontTools. A font role gives a list of families: the first measures each
  character it has, the next the rest. Never a font found on the machine.
- **Refused before layout.** A family with no committed file raises `MissingFont`, a file
  that cannot be read as a font `UnreadableFont`, and a character no family measures
  `MissingGlyph`, each naming what is missing.
- **Lines.** Each paragraph (the text split at its line feeds, a run going on into the
  next paragraph) is broken across its runs at Unicode's break opportunities (UAX #14,
  through uniseg) and the language's own rules, kept as data here (`LANGUAGE_RULES`).
  Each part of a line is measured in its own run's role. Lines are filled greedily
  against the planned width minus a margin of 2 % of the em (`BREAK_MARGIN`), taken at
  the greatest font size among the runs' roles, and placed in the planned width, so a
  renderer's slightly different metrics move no word.
- **One line height, one baseline a line.** Each line takes the greatest line height
  among the runs' roles. Its runs stand on one baseline: the leading split evenly
  around the greatest ascent and the greatest descent among the first families of the
  roles its runs take on it.
- **No shrinking.** A word longer than its line breaks after a `/`, or is left whole
  and the text overflows.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

import uharfbuzz as hb
from fontTools.ttLib import TTFont
from uniseg.linebreak import line_break_boundaries

from _lib.env import MissingFont, UnreadableFont

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
    """One committed font file, measured exactly. Raises `UnreadableFont` where it cannot be
    read as a font."""

    def __init__(self, family: str, path: Path) -> None:
        data = path.read_bytes()
        self.family = family
        self.path = path
        self.sha256 = hashlib.sha256(data).hexdigest()
        try:
            with TTFont(str(path), lazy=True) as font:
                self._cmap = frozenset(font.getBestCmap() or {})
                self.upem = font["head"].unitsPerEm
                self.ascender = font["hhea"].ascent / self.upem
                self.descender = -font["hhea"].descent / self.upem
        except Exception as exc:  # the font library has no one error for a file it cannot read
            raise UnreadableFont(path, exc) from exc
        self._font = hb.Font(hb.Face(hb.Blob(data)))
        self._advances: dict[str, float] = {}

    def has(self, character: str) -> bool:
        return ord(character) in self._cmap

    def advance(self, text: str) -> float:
        """How far a piece of text moves the pen, in ems, shaped with the font's default
        features."""
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
        """A family's face. Raises `MissingFont` where it has no committed file, and
        `UnreadableFont` where that file cannot be read as a font."""
        if family not in self._faces:
            path = self._font_file(family)
            if not path.is_file():
                raise MissingFont(f"the font family {family!r} has no file at {path}")
            self._faces[family] = Face(family, path)
        return self._faces[family]


@dataclass(frozen=True)
class Style:
    """A typography role resolved for measuring: its faces, size, weight and line height,
    and how it is measured."""

    role: str
    families: tuple[str, ...]
    faces: tuple[Face, ...] = field(compare=False)
    size: float
    weight: float | str | None
    line_height: float
    measured: str = MEASURED

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

    def _pieces(self, text: str) -> list[tuple[Face, str]]:
        """`text` in pieces of one font each: each character measured by the first family
        that has it."""
        pieces: list[tuple[Face, str]] = []
        for character in text:
            face = next((f for f in self.faces if f.has(character)), self.faces[0])
            if pieces and pieces[-1][0] is face:
                pieces[-1] = (face, pieces[-1][1] + character)
            else:
                pieces.append((face, character))
        return pieces

    def advance(self, text: str) -> float:
        """How far `text` moves the pen, in px, its spaces included."""
        return sum(face.advance(piece) for face, piece in self._pieces(text)) * self.size

    def width(self, text: str) -> float:
        """How wide a text is drawn, in px: trailing spaces do not count."""
        return self.advance(text.rstrip(" "))

    def faces_used(self, text: str) -> tuple[Face, ...]:
        """The faces that measure some character of `text`, in the role's order; the
        first family's where it has no character."""
        used = {face.family for face, _ in self._pieces(text.replace("\n", ""))}
        return tuple(face for face in self.faces if face.family in used) or self.faces[:1]

    @property
    def ascent(self) -> float:
        """How far the first family's letters reach above the baseline, in px."""
        return self.faces[0].ascender * self.size

    @property
    def descent(self) -> float:
        """How far the first family's letters reach below the baseline, in px."""
        return self.faces[0].descender * self.size

    def baseline_in(self, line_height: float) -> float:
        """The baseline below the top of a line of `line_height`, the leading split evenly
        around the first family's letters."""
        face = self.faces[0]
        content = (face.ascender + face.descender) * self.size
        return (line_height - content) / 2 + face.ascender * self.size

    @property
    def baseline(self) -> float:
        """The first baseline below the top of a line, the leading split evenly, from the
        first family's metrics."""
        return self.baseline_in(self.line_height)


@dataclass(frozen=True)
class Run:
    """A span of a text set in one style (DEC-012 point 1)."""

    text: str
    style: Style


@dataclass(frozen=True)
class Span:
    """The part of one run that lies on a line: the run's place among its paragraph's
    runs, from 0, its text, and how far it moves the pen, in px. The spaces that end a
    line belong to no span."""

    run: int
    text: str
    width: float


@dataclass(frozen=True)
class Line:
    """A line as the engine broke it: its text, its drawn width, its paragraph's place
    among the text's paragraphs, from 0, its spans in order, and its baseline below its
    top."""

    text: str
    width: float
    paragraph: int
    spans: tuple[Span, ...]
    baseline: float


def paragraphs(texts: Sequence[str]) -> list[list[tuple[int, str]]]:
    """The runs whose texts are `texts`, joined in order, split into paragraphs at their
    line feeds: each paragraph its runs' parts, each with its run's place in `texts`. A run
    whose text holds a line feed goes on into the next paragraph. A part with no text is
    left out, but where a paragraph holds no other, its first."""
    found: list[list[tuple[int, str]]] = [[]]
    for index, text in enumerate(texts):
        for step, part in enumerate(text.split("\n")):
            if step:
                found.append([])
            found[-1].append((index, part))
    return [[part for part in paragraph if part[1]] or paragraph[:1] for paragraph in found]


@dataclass(frozen=True)
class Broken:
    """A text broken into lines: each line, its drawn width, and whether one is wider
    than the planned width; with each line placed (`placed`), the text's paragraphs, each
    its runs' parts with their place among the runs (`paragraphs`), and the line height
    every line takes."""

    lines: tuple[str, ...]
    widths: tuple[float, ...]
    overflow: bool
    placed: tuple[Line, ...] = ()
    paragraphs: tuple[tuple[tuple[int, str], ...], ...] = ()
    line_height: float = 0.0

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
    return break_runs([Run(text, style)], width, language)


def break_runs(runs: Sequence[Run], width: float | None, language: str) -> Broken:
    """A text of `runs` broken into lines for a planned width, across its runs; with no
    width, each paragraph is one line, as wide as it is. A text with no characters has no
    lines."""
    if not runs:
        return Broken((), (), False)
    line_height = max(run.style.line_height for run in runs)
    split = paragraphs([run.text for run in runs])
    placed: list[Line] = []
    if any(run.text for run in runs):
        size = max(run.style.size for run in runs)
        for index, parts in enumerate(split):
            styled = _Paragraph([(runs[run].style, text) for run, text in parts])
            for start, end in styled.lines(width, size, language):
                placed.append(styled.line(index, start, end, line_height))
    texts = tuple(line.text for line in placed)
    widths = tuple(line.width for line in placed)
    overflow = width is not None and any(w > width for w in widths)
    frozen = tuple(tuple(parts) for parts in split)
    return Broken(texts, widths, overflow, tuple(placed), frozen, line_height)


class _Paragraph:
    """One paragraph of a text: its runs' parts, each in its style, joined."""

    def __init__(self, parts: Sequence[tuple[Style, str]]) -> None:
        self.parts = list(parts)
        self.text = "".join(text for _, text in parts)
        self.bounds: list[tuple[int, int]] = []
        start = 0
        for _, text in parts:
            self.bounds.append((start, start + len(text)))
            start += len(text)

    def _spans(self, start: int, end: int) -> list[tuple[int, str, Style]]:
        """The parts of the runs between two places of the paragraph, each with its
        part's place."""
        found = []
        for place, ((low, high), (style, _)) in enumerate(
            zip(self.bounds, self.parts, strict=True)
        ):
            text = self.text[max(low, start) : min(high, end)]
            if text:
                found.append((place, text, style))
        return found

    def _end(self, start: int, end: int) -> int:
        """`end`, moved back past the spaces that end the text between the two places."""
        return start + len(self.text[start:end].rstrip(" "))

    def width(self, start: int, end: int) -> float:
        """How wide the text between two places is drawn, each part in its own style;
        trailing spaces do not count."""
        spans = self._spans(start, self._end(start, end))
        return sum((style.advance(text) for _, text, style in spans), 0.0)

    def lines(self, width: float | None, size: float, language: str) -> list[tuple[int, int]]:
        """Where each line starts and ends, filled greedily against the planned width less
        the margin at the font size `size`."""
        if width is None:
            return [(0, self._end(0, len(self.text)))]
        limit = width - BREAK_MARGIN * size
        lines: list[tuple[int, int]] = []
        start = at = 0
        for unit in _units(self.text, language):
            pieces = _after_slashes(unit) if self.width(at, at + len(unit)) > limit else [unit]
            for piece in pieces:
                end = at + len(piece)
                if at > start and self.width(start, end) > limit:
                    lines.append((start, self._end(start, at)))
                    start = at
                at = end
        lines.append((start, self._end(start, at)))
        return lines

    def line(self, paragraph: int, start: int, end: int, line_height: float) -> Line:
        """The line between two places, its spans measured, standing on its baseline."""
        spans = tuple(
            Span(place, text, style.advance(text)) for place, text, style in self._spans(start, end)
        )
        styles = [self.parts[span.run][0] for span in spans] or [self.parts[0][0]]
        baseline = _baseline(styles, line_height)
        width = self.width(start, end)
        return Line(self.text[start:end], width, paragraph, spans, baseline)


def _baseline(styles: Sequence[Style], line_height: float) -> float:
    """The baseline below the top of a line whose runs take `styles`: as one style places
    it where they take one role, else the leading split evenly around the greatest ascent
    and the greatest descent among them."""
    roles = {style.role for style in styles}
    if len(roles) == 1:
        return styles[0].baseline_in(line_height)
    ascent = max(style.ascent for style in styles)
    descent = max(style.descent for style in styles)
    return (line_height - (ascent + descent)) / 2 + ascent
