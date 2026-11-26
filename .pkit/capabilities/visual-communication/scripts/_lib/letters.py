"""The check of letters across lines: a text whose letters touch across its lines
(visual-communication DEC-053).

- **Which lines** (point 1). Each line of a text a page draws and the next one, as the
  engine sets them, across its paragraphs: the lower one set the text's step below the
  upper, each on its own baseline (`components.md`, "What a scene holds"). The lines of two
  texts are not compared, since the layout sets their distance.
- **What a line draws.** Its letters: each glyph the engine shapes for a span's text, from
  the face of its run's role that measures the character, a later family where the first
  lacks it, at its run's size, where the engine places it along the line and on the line's
  baseline (`text.Face.glyphs`). A run's sign counts with them, read from its drawing where
  the scene places it. A character a font draws to join the next line's (`JOINING`) does
  not count, and a glyph with no outline, such as a space's, draws nothing.
- **When they touch.** Their outlines, each curve flattened into segments none further
  than `TOLERANCE` of its letter's size from the curve, share a point. Two lines' *reach*
  is the step at and below which they do: at the one point along the line where it is
  greatest, how far the upper line's letters fall below its baseline, added to how far the
  lower line's rise above its own, less how much lower the lower line's baseline lies in
  its line than the upper's (`_touching`). Only two letters whose boxes meet at the step are
  read by their outlines, since a letter's box holds its outline, so the reach of two lines
  that touch is exact.
- **The finding** (point 2) asks the owner of the version that gives the step for attention,
  at the text, naming each two lines that touch, the letters that meet and their reach, and
  the step, with the role it comes from and the file and the field that give it (`Given`). It
  carries the version that holds a word that counts for the step (`Given.word`,
  `Finding.lies_over_in`), which validation reads as the fact `letters-touch-meant` where
  that version is released and still as it was released (`meant`, point 4). The viewing step
  reads every such finding as `letters-touch`.
- **Where it measures nothing** (point 5). A pair of lines that holds a letter the engine has
  no outline of is not measured, and the check states so at the text, as a fact: a letter
  of a run measured otherwise than from a font file, or one its face draws from a bitmap or
  an SVG of its own (`LETTERS_UNMEASURED`).

**It states its reach** (`LETTERS_CHECK`), beside its id, in the words of its entry in the
list of checks (DEC-063 point 1). It compares no scenes: each finding is one scene's.

Reads no file but the faces' fonts, and knows nothing of the brand or the check's run: the
check gives it the faces and the step each text's lines take, and places each finding.
"""

from __future__ import annotations

import functools
import io
import itertools
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from fontTools.pens.basePen import BasePen
from fontTools.ttLib import TTFont

from _lib.findings import ATTENTION, FACT, Finding
from _lib.outlines import segments_of
from _lib.scene import line_left
from _lib.scene_checks import Reach, SceneCheck
from _lib.text import MEASURED, Face, Faces

#: The call for attention on a text whose letters touch across its lines, and the fact
#: validation states in its place where a released version's word says they are meant
#: (DEC-053 points 2 and 4).
LETTERS_TOUCH = "letters-touch"
LETTERS_TOUCH_MEANT = "letters-touch-meant"

#: The fact the check states at a text, for each pair of its lines it could not measure
#: (DEC-053 point 5).
LETTERS_UNMEASURED = "letters-touch-unmeasured"

#: How far a flattened curve may lie from the curve, as a share of its letter's size: the
#: check reads letters that meet or part by less than about twice as much either way
#: (DEC-053 point 1).
TOLERANCE = 0.001

#: The characters a font draws to join the next line's, which do not count (DEC-053 point
#: 1): Unicode's Box Drawing, its Block Elements, and the pieces of a tall bracket or
#: integral, each a range of code points, both ends included.
JOINING = ((0x2500, 0x257F), (0x2580, 0x259F), (0x2320, 0x2321), (0x239B, 0x23B3))

#: The check of letters across lines, with its reach (DEC-053 point 5, DEC-063 point 1).
LETTERS_CHECK = SceneCheck(
    "letters of a text's lines that touch across them",
    id="letters-across-lines",
    labels=(LETTERS_TOUCH, LETTERS_TOUCH_MEANT, LETTERS_UNMEASURED),
    reach=Reach(
        measures=(
            "each two lines that follow each other in a text a page draws, across its "
            "paragraphs, in each language and at each key over the size axes, for letters and "
            "runs' signs that meet at the text's step, each read from its outline as the engine "
            "places it (DEC-053 points 1 and 5)",
        ),
        leaves_out=(
            "two lines of two texts, whose distance the layout sets (DEC-053 point 1)",
            "the characters drawn to join the next line's: Unicode's Box Drawing, U+2500 to "
            "U+257F, its Block Elements, U+2580 to U+259F, and the pieces of a tall bracket or "
            "integral, U+2320, U+2321 and U+239B to U+23B3 (DEC-053 point 1)",
            "the lines of a renderer that wraps text itself, as a medium may by a declared "
            "choice, since the check reads the lines the engine sets (DEC-005 point 4, "
            "DEC-053 point 5)",
        ),
        states=(
            f"`{LETTERS_UNMEASURED}`, at a text, for each pair of its lines that holds a "
            "letter the engine has no outline of: one a font profile measures from a table of "
            "widths or by an estimate, or one its face draws from a bitmap or an SVG of its own "
            "(DEC-053 point 5)",
        ),
        statements=(LETTERS_UNMEASURED,),
    ),
)

#: How much nearer than its reach two lines may lie and still part: none, but for a float's
#: last digits.
_EXACT = 1e-9

#: How many stretches of its width a shape's segments are kept by, so that few are read at
#: one point along it.
_STRETCHES = 64


def joins(character: str) -> bool:
    """Whether `character` is one a font draws to join the next line's (`JOINING`)."""
    point = ord(character)
    return any(low <= point <= high for low, high in JOINING)


@dataclass(frozen=True)
class Given:
    """The step a text's lines take, as the brand gives it at the scene's key (DEC-053,
    Context): the typography role it comes from, its line height in px, `step`, and its
    font size in px; the file, as findings name it, and the field that hold the number its
    line height takes, with the version whose file that is and who owns it; and the version
    that holds a word that counts for the step, "" where none does (point 4). Where the step
    cannot be traced to a file, `file` and `field` are ""."""

    role: str
    step: float
    size: float
    file: str
    field: str
    version: str
    who: str
    word: str = ""


# --- the check ----------------------------------------------------------------------------------


def letters_touch(
    scene: Mapping[str, Any], faces: Faces, given: Callable[[Mapping[str, Any]], Given]
) -> list[Finding]:
    """For each text a page of `scene` draws: a finding where letters of two of its lines
    that follow each other touch at its step, which `given` gives for the text, naming each
    such pair; and the fact that it measured nothing at each pair that holds a letter the
    engine has no outline of. Each finding lies at the text's trace id, in the piece."""
    found: list[Finding] = []
    for text in _texts(scene):
        lines = text.get("lines") or []
        if len(lines) < 2:
            continue
        step = float(text.get("line-height", 0))
        drawn = [_line(text, line, faces) for line in lines]
        touching: list[tuple[int, float, list[tuple[str, str]]]] = []
        unmeasured: list[tuple[int, tuple[str, ...]]] = []
        for index, (upper, lower) in enumerate(itertools.pairwise(drawn)):
            why = (*upper.otherwise, *lower.otherwise)
            if why:
                unmeasured.append((index, why))
                continue
            met = _touching(upper, lower, step)
            if met is not None:
                touching.append((index, *met))
        trace = str(text.get("id", ""))
        if touching:
            found.append(_touch(trace, step, touching, given(text)))
        if unmeasured:
            found.append(_unmeasured(trace, unmeasured))
    return found


def meant(finding: Finding) -> Finding:
    """A `letters-touch` finding as validation reads it where the version that holds the
    role's word, `lies_over_in`, is released and still as it was released (DEC-053 point 4):
    the fact `letters-touch-meant`, which asks no act, so names no one and no fix. Its message
    is the finding's, and says that the role's token carries `tight-lines`."""
    return replace(
        finding,
        code=LETTERS_TOUCH_MEANT,
        level=FACT,
        message=f"{finding.message}; the role's token carries `tight-lines` in "
        f"{finding.lies_over_in}, released, which says the letters are meant",
        fix="",
        who="",
    )


def _texts(scene: Mapping[str, Any]) -> Iterator[Mapping[str, Any]]:
    """Each text a page of `scene` draws, once, in drawing order."""
    pages = {str(page) for page in scene.get("pages", [])}
    seen: set[int] = set()

    def below(elements: Sequence[Mapping[str, Any]], on_page: bool) -> Iterator[Mapping[str, Any]]:
        for element in elements:
            here = on_page or str(element.get("id", "")) in pages
            if here and element.get("type") == "text" and id(element) not in seen:
                seen.add(id(element))
                yield element
            if element.get("type") == "group":
                yield from below(element.get("children") or [], here)

    yield from below(scene.get("children") or [], False)


def _touch(
    trace: str, step: float, touching: Sequence[tuple[int, float, list[tuple[str, str]]]], at: Given
) -> Finding:
    """The call for attention on a text whose letters touch across its lines, naming each two
    lines that touch, the letters that meet and their reach, and the step with the role it
    comes from and where it is given (DEC-053 point 2)."""
    size = at.size if at.size > 0 else step
    gives = f"{at.field} in {at.file}" if at.file else "the brand"
    pairs = "; ".join(
        f"lines {index + 1} and {index + 2}, {_and([f'`{u}` over `{v}`' for u, v in met])}, "
        f"their reach {_px(reach)}, {_em(reach / size)}"
        for index, reach, met in touching
    )
    widest = max(reach for _, reach, _ in touching)
    return Finding(
        LETTERS_TOUCH,
        ATTENTION,
        f"`{trace}`: letters of its lines touch across them at its line step of {_px(step)}, "
        f"{_em(step / size)} of the {size:g} px of `{at.role}`, which {gives} gives: {pairs}. "
        "Two lines part at a step above their reach",
        where=trace,
        fix=f"a wider line step for `{at.role}`, above {_em(widest / size)}, at {gives}; where "
        "its brand means the setting, its owner may mark the role's token `tight-lines` instead",
        who=at.who,
        lies_over_in=at.word,
    )


def _unmeasured(trace: str, pairs: Sequence[tuple[int, tuple[str, ...]]]) -> Finding:
    """The fact that the check measured nothing at each pair of a text's lines that holds a
    letter the engine has no outline of, and why (DEC-053 point 5, DEC-063 point 2). It asks
    no act: nothing in the piece's files is wrong."""
    said = _and([f"lines {index + 1} and {index + 2}" for index, _ in pairs])
    why = list(dict.fromkeys(reason for _, reasons in pairs for reason in reasons))
    return Finding(
        LETTERS_UNMEASURED,
        FACT,
        f"`{trace}`: the check of letters across lines measured nothing at {said}, which hold "
        f"a letter the engine has no outline of: {'; '.join(why)}",
        where=trace,
    )


# --- what a line draws --------------------------------------------------------------------------


@dataclass(frozen=True)
class _Line:
    """A line as the check reads it: its baseline below its top, each shape it draws, and why
    it holds a letter the engine has no outline of, where it holds one."""

    baseline: float
    shapes: tuple[_Shape, ...]
    otherwise: tuple[str, ...]


def _line(text: Mapping[str, Any], line: Mapping[str, Any], faces: Faces) -> _Line:
    """What `line` of `text` draws, each shape across from the text's left edge and up from
    the line's baseline: each span's sign and letters, where the scene places the span (the
    contrast check walks a line's spans alike)."""
    paragraphs = text.get("paragraphs") or []
    place = int(line.get("paragraph", 0))
    runs = paragraphs[place] if place < len(paragraphs) else []
    baseline = float(line.get("baseline", 0))
    at = line_left(text, line)
    shapes: list[_Shape] = []
    otherwise: list[str] = []
    for span in line.get("spans") or []:
        index = int(span.get("run", 0))
        run: Mapping[str, Any] = runs[index] if index < len(runs) else {}
        size = float(run.get("font-size", 0))
        ground = span.get("ground") or {}
        at += float(ground.get("start", 0))
        sign = span.get("sign")
        if isinstance(sign, Mapping):
            shape = _sign(sign, at, baseline, size)
            if shape is not None:
                shapes.append(shape)
            at += float(sign.get("size", 0)) + float(sign.get("gap", 0))
        said = str(span.get("text", ""))
        measured = run.get("measured", MEASURED)
        if measured != MEASURED:
            if said.strip():
                otherwise.append(
                    f"the letters of `{run.get('style')}` are measured `{measured}`, from no "
                    "font file"
                )
        else:
            shapes.extend(_letters(said, run, faces, at, size, otherwise))
        at += float(span.get("width", 0)) + float(ground.get("end", 0))
    return _Line(baseline, tuple(shapes), tuple(otherwise))


def _letters(
    said: str,
    run: Mapping[str, Any],
    faces: Faces,
    at: float,
    size: float,
    otherwise: list[str],
) -> Iterator[_Shape]:
    """Each letter of a span's text `said`, which starts `at` px from the text's left edge, in
    its run's faces at `size`: shaped in pieces of one face each, each character by the first
    family of the run's role that has it, as the engine shapes it. A letter its face draws
    from a bitmap or an SVG of its own goes into `otherwise`, why it is not measured."""
    families = [str(family) for family in run.get("font-family") or []]
    if not families or not said:
        return
    held = [faces.face(family) for family in families]
    pen = 0.0
    for face, piece in _pieces(held, said):
        font = _font(face.path, face.sha256)
        glyphs = face.glyphs(piece)
        starts = sorted({glyph.cluster for glyph in glyphs})
        ends = dict(zip(starts, [*starts[1:], len(piece)], strict=True))
        for glyph in glyphs:
            characters = piece[glyph.cluster : ends[glyph.cluster]]
            if characters and all(joins(character) for character in characters):
                continue
            if font.drawn_otherwise(glyph.id):
                otherwise.append(
                    f"the face of `{face.family}` draws `{characters}` from a bitmap or an SVG of "
                    "its own"
                )
                continue
            outline = font.outline(glyph.id)
            if outline is not None:
                x, y = at + (pen + glyph.x) * size, glyph.y * size
                yield _Shape(characters, outline, x, y, size)
        pen += face.advance(piece)


def _pieces(held: Sequence[Face], said: str) -> list[tuple[Face, str]]:
    """`said` in pieces of one face each: each character measured by the first face that has
    it, else the first, as `text.Style` cuts a run's text."""
    pieces: list[tuple[Face, str]] = []
    for character in said:
        face = next((each for each in held if each.has(character)), held[0])
        if pieces and pieces[-1][0] is face:
            pieces[-1] = (face, pieces[-1][1] + character)
        else:
            pieces.append((face, character))
    return pieces


def _sign(sign: Mapping[str, Any], at: float, baseline: float, size: float) -> _Shape | None:
    """A run's sign, read from its drawing as the scene maps it into its square: the square's
    left edge `at` px from the text's, its top `sign.top` below the line's (DEC-036 point
    3). None where it draws nothing."""
    data = sign.get("d")
    if not isinstance(data, str) or not data.strip():
        return None
    try:
        drawn = segments_of(data)
    except ValueError:
        return None
    tolerance = TOLERANCE * (size if size > 0 else float(sign.get("size", 0)))
    rings: list[list[tuple[float, float]]] = []
    for command, points in drawn:
        if command == "M":
            rings.append([(points[0], -points[1])])
        elif command == "L":
            rings[-1].append((points[0], -points[1]))
        elif command == "C":
            start = rings[-1][-1]
            controls = [(points[n], -points[n + 1]) for n in (0, 2, 4)]
            rings[-1].extend(_flattened(start, *controls, tolerance))
    outline = _Outline.of(rings)
    if outline is None:
        return None
    return _Shape("a run's sign", outline, at, baseline - float(sign.get("top", 0)), 1.0)


# --- shapes and their reach ---------------------------------------------------------------------


class _Outline:
    """A shape as the segments that bound it, in its own units, y up: its bounds, the x of each
    end of a segment, and its segments kept by the stretches of its width each covers, so that
    few are read at one point along it."""

    def __init__(self, segments: Sequence[tuple[float, float, float, float]]) -> None:
        self.segments = tuple(segments)
        xs = [x for x0, _, x1, _ in self.segments for x in (x0, x1)]
        ys = [y for _, y0, _, y1 in self.segments for y in (y0, y1)]
        self.left, self.right = min(xs), max(xs)
        self.bottom, self.top = min(ys), max(ys)
        self.xs = tuple(sorted(set(xs)))
        self._stretch = (self.right - self.left) / _STRETCHES or 1.0
        self._kept: list[list[tuple[float, float, float, float]]] = [[] for _ in range(_STRETCHES)]
        for segment in self.segments:
            x0, _, x1, _ = segment
            for stretch in range(self._at(min(x0, x1)), self._at(max(x0, x1)) + 1):
                self._kept[stretch].append(segment)

    @classmethod
    def of(cls, rings: Sequence[Sequence[tuple[float, float]]]) -> _Outline | None:
        """The outline whose parts are `rings`, each closed back to its first point as a fill
        closes it. None where it bounds nothing."""
        segments = []
        for ring in rings:
            for (x0, y0), (x1, y1) in zip(ring, [*ring[1:], ring[0]], strict=True):
                if (x0, y0) != (x1, y1):
                    segments.append((x0, y0, x1, y1))
        return cls(segments) if segments else None

    def _at(self, x: float) -> int:
        return min(_STRETCHES - 1, max(0, int((x - self.left) / self._stretch)))

    def over(self, x: float) -> tuple[float, float] | None:
        """The lowest and the highest of the shape at `x`, in its units; None where it does not
        reach `x`."""
        near = 1e-9 * max(1.0, abs(x))
        if x < self.left - near or x > self.right + near:
            return None
        found: list[float] = []
        for x0, y0, x1, y1 in self._kept[self._at(x)]:
            first, last = min(x0, x1), max(x0, x1)
            if not first - near <= x <= last + near:
                continue
            if last - first <= near:
                found.extend((y0, y1))
            else:
                held = min(max(x, first), last)
                found.append(y0 + (held - x0) * (y1 - y0) / (x1 - x0))
        return (min(found), max(found)) if found else None


@dataclass(frozen=True)
class _Shape:
    """A letter or a sign a line draws: what it is, in words; its outline, in its own units;
    and where the outline's origin stands, in px across from the text's left edge and up from
    the line's baseline, at `scale` px to its unit."""

    said: str
    outline: _Outline
    x: float
    y: float
    scale: float

    @property
    def left(self) -> float:
        return self.x + self.outline.left * self.scale

    @property
    def right(self) -> float:
        return self.x + self.outline.right * self.scale

    @property
    def bottom(self) -> float:
        return self.y + self.outline.bottom * self.scale

    @property
    def top(self) -> float:
        return self.y + self.outline.top * self.scale

    def xs(self) -> Iterator[float]:
        return (self.x + x * self.scale for x in self.outline.xs)

    def over(self, x: float) -> tuple[float, float] | None:
        """Its lowest and highest at `x` px, in px up from its line's baseline."""
        found = self.outline.over((x - self.x) / self.scale)
        if found is None:
            return None
        return self.y + found[0] * self.scale, self.y + found[1] * self.scale


def _touching(
    upper: _Line, lower: _Line, step: float
) -> tuple[float, list[tuple[str, str]]] | None:
    """Whether the letters of `upper` and of `lower`, the next line, touch at `step`: their
    reach, as a step, and each two letters that meet, the upper's first. None where they part.
    The lower line's baseline lies `step` below the upper's, and lower still by as much as it
    lies lower in its line."""
    drop = lower.baseline - upper.baseline
    apart = step + drop
    reach: float | None = None
    met: list[tuple[str, str]] = []
    for one in upper.shapes:
        for other in lower.shapes:
            if one.right < other.left or other.right < one.left:
                continue
            if other.top - one.bottom < apart - _EXACT:
                continue  # their boxes part at the step, so their outlines do
            found = _reach(one, other)
            if found is None:
                continue
            reach = found if reach is None else max(reach, found)
            if found >= apart - _EXACT and (one.said, other.said) not in met:
                met.append((one.said, other.said))
    if not met or reach is None:
        return None
    return reach - drop, met


def _reach(upper: _Shape, lower: _Shape) -> float | None:
    """How far apart the baselines of `upper` and of `lower` may lie and their outlines still
    meet: at the one point along them where it is greatest, how far `upper` falls below its
    baseline, added to how far `lower` rises above its own. Each is bounded by straight
    segments, so that point lies at an end of one of them. None where no point along them
    holds both."""
    low, high = max(upper.left, lower.left), min(upper.right, lower.right)
    if low > high:
        return None
    places = {low, high}
    places.update(x for x in upper.xs() if low <= x <= high)
    places.update(x for x in lower.xs() if low <= x <= high)
    best: float | None = None
    for x in places:
        under, over = upper.over(x), lower.over(x)
        if under is None or over is None:
            continue
        found = over[1] - under[0]
        best = found if best is None else max(best, found)
    return best


# --- outlines from a face -----------------------------------------------------------------------


class _Font:
    """The outlines of one committed font file, each glyph's read once, in ems, y up; and the
    glyphs its face draws from a bitmap or an SVG of its own."""

    def __init__(self, path: Path) -> None:
        self._font = TTFont(io.BytesIO(path.read_bytes()), lazy=True)
        self._order = self._font.getGlyphOrder()
        self._set = self._font.getGlyphSet()
        self._upem = float(self._font["head"].unitsPerEm)
        self._otherwise = _drawn_otherwise(self._font)
        self._outlines: dict[int, _Outline | None] = {}

    def drawn_otherwise(self, glyph: int) -> bool:
        return glyph in self._otherwise

    def outline(self, glyph: int) -> _Outline | None:
        """The glyph's outline in ems, each curve flattened within `TOLERANCE`; None where it
        draws nothing."""
        if glyph not in self._outlines:
            pen = _Flattening(self._set, TOLERANCE * self._upem)
            self._set[self._order[glyph]].draw(pen)
            rings = [[(x / self._upem, y / self._upem) for x, y in ring] for ring in pen.rings]
            self._outlines[glyph] = _Outline.of(rings)
        return self._outlines[glyph]


@functools.lru_cache(maxsize=32)
def _font(path: Path, sha256: str) -> _Font:
    """The outlines of the font file at `path`, read once for its bytes, which `sha256` names."""
    del sha256  # it keys the cache: a file changed in place is read again
    return _Font(path)


def _drawn_otherwise(font: TTFont) -> frozenset[int]:
    """The glyphs a face draws from a bitmap or an SVG of its own: each its `SVG ` table holds
    a document for, and each one of its strikes of bitmaps, `sbix`, `CBDT` or `EBDT`, holds an
    image of."""
    found: set[int] = set()
    if "SVG " in font:
        for document in font["SVG "].docList:
            found.update(range(int(document.startGlyphID), int(document.endGlyphID) + 1))
    names: set[str] = set()
    if "sbix" in font:
        for strike in font["sbix"].strikes.values():
            names.update(
                name
                for name, glyph in strike.glyphs.items()
                if getattr(glyph, "imageData", None)
                or getattr(glyph, "graphicType", None) == "dupe"
            )
    for table in ("CBDT", "EBDT"):
        if table in font:
            for strike in font[table].strikeData:
                names.update(strike)
    found.update(font.getGlyphID(name) for name in names)
    return frozenset(found)


class _Flattening(BasePen):
    """A pen that draws a glyph as rings of points, each curve flattened into chords none
    further than `tolerance` from it, in the glyph's units."""

    def __init__(self, glyph_set: Any, tolerance: float) -> None:
        super().__init__(glyph_set)
        self.tolerance = tolerance
        self.rings: list[list[tuple[float, float]]] = []

    def _moveTo(self, pt: tuple[float, float]) -> None:
        self.rings.append([pt])

    def _lineTo(self, pt: tuple[float, float]) -> None:
        self.rings[-1].append(pt)

    def _curveToOne(
        self, pt1: tuple[float, float], pt2: tuple[float, float], pt3: tuple[float, float]
    ) -> None:
        start = self._getCurrentPoint()
        self.rings[-1].extend(_flattened(start, pt1, pt2, pt3, self.tolerance))

    def _qCurveToOne(self, pt1: tuple[float, float], pt2: tuple[float, float]) -> None:
        (x0, y0), (x1, y1), (x2, y2) = self._getCurrentPoint(), pt1, pt2
        first = (x0 + 2 / 3 * (x1 - x0), y0 + 2 / 3 * (y1 - y0))
        second = (x2 + 2 / 3 * (x1 - x2), y2 + 2 / 3 * (y1 - y2))
        self.rings[-1].extend(_flattened((x0, y0), first, second, (x2, y2), self.tolerance))

    def _closePath(self) -> None:
        pass  # each ring closes back to its first point (`_Outline.of`)

    def _endPath(self) -> None:
        pass


def _flattened(
    start: tuple[float, float],
    first: tuple[float, float],
    second: tuple[float, float],
    end: tuple[float, float],
    tolerance: float,
    depth: int = 0,
) -> list[tuple[float, float]]:
    """The points after `start` that draw a cubic curve as chords, each within `tolerance` of
    the curve: it is halved until each control point lies so near the chord, which then holds
    the curve within that distance, as the curve lies within its control points' hull."""
    if depth >= 24 or (
        _off(first, start, end) <= tolerance and _off(second, start, end) <= tolerance
    ):
        return [end]
    a, b, c = _middle(start, first), _middle(first, second), _middle(second, end)
    d, e = _middle(a, b), _middle(b, c)
    middle = _middle(d, e)
    return [
        *_flattened(start, a, d, middle, tolerance, depth + 1),
        *_flattened(middle, e, c, end, tolerance, depth + 1),
    ]


def _middle(one: tuple[float, float], other: tuple[float, float]) -> tuple[float, float]:
    return ((one[0] + other[0]) / 2, (one[1] + other[1]) / 2)


def _off(point: tuple[float, float], start: tuple[float, float], end: tuple[float, float]) -> float:
    """How far `point` lies from the chord between `start` and `end`."""
    (px, py), (ax, ay), (bx, by) = point, start, end
    dx, dy = bx - ax, by - ay
    length = dx * dx + dy * dy
    share = 0.0 if length == 0 else min(1.0, max(0.0, ((px - ax) * dx + (py - ay) * dy) / length))
    return ((px - ax - share * dx) ** 2 + (py - ay - share * dy) ** 2) ** 0.5


def _px(length: float) -> str:
    return f"{round(length, 2):g} px"


def _em(share: float) -> str:
    return f"{round(share, 3):g} em"


def _and(said: Sequence[str]) -> str:
    """`said` joined as a list in words."""
    if len(said) < 3:
        return " and ".join(said)
    return f"{', '.join(said[:-1])} and {said[-1]}"
