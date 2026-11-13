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
- **A run's sign and ground** (DEC-036 point 3). A run may draw a sign, a square as wide as
  its font size, before its first character that is no space or line feed, with a gap after
  it, and take a ground behind its text, from its first such character to its last, with
  room at each end. Runs next to each other in one paragraph that share a sign draw one,
  and those that share a ground take one, with room at its two ends alone. Each is measured
  with the character it lies beside, so no line breaks between them, and a line's spans are
  cut where a sign or a ground's end lies, so each lies at a span's edge (`Marks`,
  `SignAt`, `GroundAt`).
"""

from __future__ import annotations

import bisect
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

#: The characters a run's sign and ground pass over at the run's ends (DEC-036 point 3).
BLANK = " \n"


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
    """A span of a text set in one style (DEC-012 point 1). Where it draws its concept's
    sign, `sign` names what the runs next to it share to draw one sign with it, its concept;
    where it takes a ground, `ground` names what they share to take one ground with it, its
    paint (DEC-036 point 3)."""

    text: str
    style: Style
    sign: str | None = None
    ground: str | None = None


@dataclass(frozen=True)
class Marks:
    """The lengths a run's sign and ground take within its line, in px (DEC-036 point 3):
    the gap between a sign and the character after it, and the room a ground leaves at each
    end of its span."""

    gap: float = 0.0
    room: float = 0.0


@dataclass(frozen=True)
class SignAt:
    """A sign before a span's text: the side of its square, its run's font size; the top
    of the square below the line's top, centred on the run's letters; and the gap after
    it."""

    size: float
    top: float
    gap: float


@dataclass(frozen=True)
class GroundAt:
    """The part of a ground behind a span: the top of the ground's piece on the line below
    the line's top, and its height, alike for every span of the piece; and the room before
    the span where the ground starts at it, and after it where the ground ends at it, else
    None."""

    top: float
    height: float
    start: float | None = None
    end: float | None = None


@dataclass(frozen=True)
class Span:
    """The part of one run that lies on a line: the run's place among its paragraph's
    runs, from 0, its text, and how far its text moves the pen, in px; with the sign before
    its text and the ground behind it, where it has them. The spaces that end a line belong
    to no span."""

    run: int
    text: str
    width: float
    sign: SignAt | None = None
    ground: GroundAt | None = None

    @property
    def advance(self) -> float:
        """How far the span moves the pen: its ground's room, its sign and the sign's gap,
        and its text."""
        ground, sign = self.ground, self.sign
        rooms = (ground.start or 0.0) + (ground.end or 0.0) if ground is not None else 0.0
        return rooms + (sign.size + sign.gap if sign is not None else 0.0) + self.width


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


def break_runs(
    runs: Sequence[Run], width: float | None, language: str, marks: Marks | None = None
) -> Broken:
    """A text of `runs` broken into lines for a planned width, across its runs; with no
    width, each paragraph is one line, as wide as it is. A text with no characters has no
    lines. `marks` gives the lengths of the runs' signs and grounds (`Marks`)."""
    if not runs:
        return Broken((), (), False)
    line_height = max(run.style.line_height for run in runs)
    split = paragraphs([run.text for run in runs])
    placed: list[Line] = []
    if any(run.text for run in runs):
        size = max(run.style.size for run in runs)
        marked = _Marked(runs, marks or Marks())
        for index, parts in enumerate(split):
            styled = _Paragraph([(runs[run].style, text) for run, text in parts])
            marked.mark(styled, index)
            for start, end in styled.lines(width, size, language):
                placed.append(styled.line(index, start, end, line_height))
    texts = tuple(line.text for line in placed)
    widths = tuple(line.width for line in placed)
    overflow = width is not None and any(w > width for w in widths)
    frozen = tuple(tuple(parts) for parts in split)
    return Broken(texts, widths, overflow, tuple(placed), frozen, line_height)


@dataclass(frozen=True)
class _Ground:
    """A ground within one paragraph: its first and last character there, and whether it
    starts and ends there, where it takes room."""

    first: int
    last: int
    starts: bool
    ends: bool


class _Marked:
    """Where the signs and grounds of a text's runs lie (DEC-036 point 3), by the place of
    each character in the runs' texts joined, and how each paragraph takes them."""

    def __init__(self, runs: Sequence[Run], marks: Marks) -> None:
        self.marks = marks
        texts = [run.text for run in runs]
        joined = "".join(texts)
        self.paragraph_starts = [0] + [at + 1 for at, char in enumerate(joined) if char == "\n"]
        starts = [sum(len(text) for text in texts[:index]) for index in range(len(texts))]
        firsts = [_first(text, start) for text, start in zip(texts, starts, strict=True)]
        lasts = [_last(text, start) for text, start in zip(texts, starts, strict=True)]
        # Each sign's character, and each ground's first and last, in the joined text.
        self.signs: list[int] = []
        self.grounds: list[tuple[int, int]] = []
        for group in _groups(runs, texts, lambda run: run.sign):
            found = [firsts[index] for index in group if firsts[index] is not None]
            if found:
                self.signs.append(found[0])
        for group in _groups(runs, texts, lambda run: run.ground):
            first = [firsts[index] for index in group if firsts[index] is not None]
            last = [lasts[index] for index in group if lasts[index] is not None]
            if first and last:
                self.grounds.append((first[0], last[-1]))

    def _local(self, at: int) -> tuple[int, int]:
        """The paragraph that holds the character `at` of the joined text, and its place in
        that paragraph."""
        paragraph = bisect.bisect_right(self.paragraph_starts, at) - 1
        return paragraph, at - self.paragraph_starts[paragraph]

    def mark(self, styled: _Paragraph, index: int) -> None:
        """Gives the paragraph `index` the signs and the grounds that lie in it."""
        styled.marks = self.marks
        for at in self.signs:
            paragraph, local = self._local(at)
            if paragraph == index:
                styled.signs.add(local)
        for first, last in self.grounds:
            (start_paragraph, start), (end_paragraph, end) = self._local(first), self._local(last)
            if not start_paragraph <= index <= end_paragraph:
                continue
            low = start if index == start_paragraph else 0
            high = end if index == end_paragraph else len(styled.text) - 1
            if low <= high:
                styled.grounds.append(
                    _Ground(low, high, index == start_paragraph, index == end_paragraph)
                )


def _first(text: str, start: int) -> int | None:
    """The place of `text`'s first character that is no space or line feed, in the joined
    text where `text` starts at `start`; None where it holds none."""
    stripped = text.lstrip(BLANK)
    return start + len(text) - len(stripped) if stripped else None


def _last(text: str, start: int) -> int | None:
    """The place of `text`'s last character that is no space or line feed; None where it
    holds none."""
    stripped = text.rstrip(BLANK)
    return start + len(stripped) - 1 if stripped else None


def _groups(
    runs: Sequence[Run], texts: Sequence[str], key: Callable[[Run], str | None]
) -> list[list[int]]:
    """The runs that share one sign, or one ground, by `key`: each group runs next to each
    other in one paragraph, with the same key. A run of no key is in none."""
    groups: list[list[int]] = []
    for index, run in enumerate(runs):
        named = key(run)
        if named is None:
            continue
        before = index - 1
        joined = (
            groups
            and groups[-1][-1] == before
            and key(runs[before]) == named
            and not texts[before].endswith("\n")
            and not texts[index].startswith("\n")
        )
        if joined:
            groups[-1].append(index)
        else:
            groups.append([index])
    return groups


class _Paragraph:
    """One paragraph of a text: its runs' parts, each in its style, joined; with the place
    of each sign that lies in it, and each ground's part in it (`_Marked.mark`)."""

    def __init__(self, parts: Sequence[tuple[Style, str]]) -> None:
        self.parts = list(parts)
        self.text = "".join(text for _, text in parts)
        self.bounds: list[tuple[int, int]] = []
        start = 0
        for _, text in parts:
            self.bounds.append((start, start + len(text)))
            start += len(text)
        self.marks = Marks()
        self.signs: set[int] = set()
        self.grounds: list[_Ground] = []

    def _cuts(self) -> list[int]:
        """Where a span ends beside its run's: before each sign, and at each end of each
        ground."""
        cuts = set(self.signs)
        for ground in self.grounds:
            cuts.update((ground.first, ground.last + 1))
        return sorted(cuts)

    def _spans(self, start: int, end: int) -> list[tuple[int, int, int, Style]]:
        """The parts of the runs between two places of the paragraph, each cut where a sign
        or a ground's end lies, with its part's place, where it starts and where it ends."""
        cuts = self._cuts()
        found = []
        for place, ((low, high), (style, _)) in enumerate(
            zip(self.bounds, self.parts, strict=True)
        ):
            low, high = max(low, start), min(high, end)
            if low >= high:
                continue
            inner = [cut for cut in cuts if low < cut < high]
            for begin, finish in zip([low, *inner], [*inner, high], strict=True):
                found.append((place, begin, finish, style))
        return found

    def _end(self, start: int, end: int) -> int:
        """`end`, moved back past the spaces that end the text between the two places."""
        return start + len(self.text[start:end].rstrip(" "))

    def _extra(self, low: int, high: int, style: Style) -> float:
        """What a part from `low` to `high` takes beside its text: a sign and its gap before
        it, and the room of a ground that starts or ends in it."""
        extra = 0.0
        if low in self.signs:
            extra += style.size + self.marks.gap
        for ground in self.grounds:
            if ground.starts and low <= ground.first < high:
                extra += self.marks.room
            if ground.ends and low <= ground.last < high:
                extra += self.marks.room
        return extra

    def width(self, start: int, end: int) -> float:
        """How wide the text between two places is drawn, each part in its own style, with
        the signs and the grounds' room that lie in it; trailing spaces do not count."""
        spans = self._spans(start, self._end(start, end))
        return sum(
            (
                style.advance(self.text[low:high]) + self._extra(low, high, style)
                for _, low, high, style in spans
            ),
            0.0,
        )

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
        """The line between two places, its spans measured, standing on its baseline, each
        with the sign before it and the ground behind it where it has them."""
        parts = self._spans(start, end)
        styles = [style for _, _, _, style in parts] or [self.parts[0][0]]
        baseline = _baseline(styles, line_height)
        signs = {
            low: _sign_at(style, baseline, self.marks.gap)
            for _, low, _, style in parts
            if low in self.signs
        }
        grounds = [self._ground_of(low) for _, low, _, _ in parts]
        spans = []
        for (place, low, high, style), ground in zip(parts, grounds, strict=True):
            text = self.text[low:high]
            at = None
            if ground is not None:
                piece = [
                    (part[3], signs.get(part[1]))
                    for part, other in zip(parts, grounds, strict=True)
                    if other is ground
                ]
                top, bottom = _extent(piece, baseline)
                room = self.marks.room
                at = GroundAt(
                    top,
                    bottom - top,
                    room if ground.starts and low == ground.first else None,
                    room if ground.ends and high - 1 == ground.last else None,
                )
            spans.append(Span(place, text, style.advance(text), signs.get(low), at))
        width = self.width(start, end)
        return Line(self.text[start:end], width, paragraph, tuple(spans), baseline)

    def _ground_of(self, low: int) -> _Ground | None:
        """The ground behind the span that starts at `low`, if one is."""
        for ground in self.grounds:
            if ground.first <= low <= ground.last:
                return ground
        return None


def _sign_at(style: Style, baseline: float, gap: float) -> SignAt:
    """A sign as wide as `style`'s font size, centred on its letters on a line whose
    baseline lies at `baseline`, with `gap` after it."""
    middle = baseline - (style.ascent - style.descent) / 2
    return SignAt(style.size, middle - style.size / 2, gap)


def _extent(piece: Sequence[tuple[Style, SignAt | None]], baseline: float) -> tuple[float, float]:
    """The top and the bottom of a ground's piece on a line, below the line's top: from the
    highest reach of its spans' letters and signs to the lowest."""
    tops = [baseline - style.ascent for style, _ in piece]
    bottoms = [baseline + style.descent for style, _ in piece]
    for _, sign in piece:
        if sign is not None:
            tops.append(sign.top)
            bottoms.append(sign.top + sign.size)
    return min(tops), max(bottoms)


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
