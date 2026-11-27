"""Measure the SVG renderer's reads of cover and cut, as visual-communication DEC-045 gives
them: what the threshold and the measure of islands name and leave unnamed, what other rules
and settings would name, and what the reads cost. A maintainer reruns it when resvg, the face
or the reads change (DEC-045, the Revisit), each probe as below, and compares what it prints
with the figures the record gives.

    uv run python scripts/visual_svg_reads.py cover [--from EM] [--to EM] [--step EM]
        [--em EM]... [--scale SCALE]... [--face FILE]
    uv run python scripts/visual_svg_reads.py cut [the same]
    uv run python scripts/visual_svg_reads.py partial [the same]
    uv run python scripts/visual_svg_reads.py ogonek [the same]
    uv run python scripts/visual_svg_reads.py geometry [the same] [--mark MARK]...
    uv run python scripts/visual_svg_reads.py cost <piece> [look arguments]

Each probe but `cost` draws at each em from `--from` to `--to` (10 to 40 by default) in steps
of `--step` (0.1), or at each `--em` alone where any is given, in image pixels, and at each
scale (DEC-045's five by default). It draws its plants through the look's tests' own helpers
(`tests/test_visual_communication_look.py`), so a figure a test pins and a figure this prints
come from one plant, set in Source Sans Pro Regular or in the face `--face` names; the record's
figures are of Source Sans Pro Regular and Semibold and Source Code Pro, the faces of the
test brand (`tests/fixtures/visual-communication/libraries/test-brand/1.0.0/fonts`). The reads
take each span's ink at any level (`any_ink`), and count its strong ink among it, as the tool
does. A sweep of ten to forty by tenths at five scales takes some minutes for `cover` and
`cut`, and some hours for `partial`; two halves of the ems run side by side halve the wait.

- **cover.** It draws a later box over the háček of a ž, a later box whose top edge steps by
  half an image pixel across the foot of the descenders of "Typography gypsy", and a later box
  over the whole of each of five dots: a full stop after "end" and a decimal point in "3.5",
  each a run of its own, the dot of ż, and the same full stop and point inside their run,
  "end." and "3.5". The box over a dot is placed on all the dot's ink as a first draw finds
  it, a pixel past it on each side, and stops at the empty row or column between the dot and
  its neighbour (`dot_pixels`). It prints a line for each em and scale: the em the read takes,
  the threshold's pixels there, the pixels the háček loses, of the ž's strong ink, and in how
  many rows, the fewest pixels any step of the box hides of the descenders' foot, the *least
  graze*, then the next fewest, and for each dot the strong pixels the box hides of the dot's
  own, then all its ink, and the weakest level at which its run's ink falls into the dot's
  parts. Then, for each rule of the threshold DEC-045 weighs (`rules`), the draws of the háček
  and of each dot it leaves unnamed, the share of least grazes it names below an em of 25 and
  from 25 on, and whether it spares the least graze at an em of 40 at every scale,
  and names the row above it. Then what the reads as built name of each mark, by the threshold
  or by the measure of islands (`_takes_an_island`), of the draws the threshold as built and
  0.0125 each name with no pixel to spare how many the measure names too (`MARGINS`), and the
  graze steps the measure alone names. Last, for each setting of the measure (`Measure`), each
  mark's draws named by the threshold as built, by the measure, by both or by neither, where
  each dot is an island of its own, and the grazes the measure alone names.
- **cut.** It sets each of four marks past an edge of the page with the rest of its line on
  the page (`EDGES`), and draws the page through the reads as built: the full stop of "end."
  and a full stop that is a run of its own past the right edge, and the dot of ż and the háček
  of ž past the top. A first draw finds the mark's ink as the box over a dot finds it, and the
  text is moved by whole rows or columns so that the edge falls on the empty row or column
  between the mark and the rest. It prints a line for each em and scale, with what the reads
  name of each mark and whether the mark lay wholly past the edge and the rest on the page,
  then, for each mark, how many draws the reads named, by the threshold or by the measure
  alone, left unnamed, and could not place.
- **partial.** It lays each of the five dots under a box as `cover` does, then steps one edge
  of the box across the dot by eighths of an image pixel, from each side in turn (`crossed`),
  and steps the graze as `cover` does (`grazed`). At each step it reads what the box hides as
  the tool reads it, and judges it under each rule of `WEIGHED`: the threshold at a share of
  0.0125 or of 0.01, with an island taken as one of `TAKEN` says. A dot is *gone* at a step
  where no pixel of it is left in the page drawn whole at its own level, the darkest of the
  tool's levels its ink reaches. It prints a line for each em and scale, with each dot's level,
  its steps, those at which it is gone, and of those the steps each rule leaves unnamed, in
  the order of `WEIGHED`, and the graze steps each rule's island alone names. Then, for each
  dot, with strong ink and with none apart, the gone steps each rule leaves unnamed, at how
  many draws, at which ems and from which sides; for each rule the graze steps its island
  alone names, and the least grazes it names; and the steps at which the tool's own measure
  judged otherwise than the probe's setting of it, which is 0 while the two agree.
- **ogonek.** It lays a box over the ogonek of ą and of ę, rising from below the line to the
  baseline (`joined`), and judges what the box hides under each rule of `WEIGHED`. It prints a
  line for each em and scale, with the letter's strong pixels wholly below the baseline, those
  the box hides, the pixels it hides above the baseline, which the renderer's rounding of the
  box's edge to two decimals leaves, and the ways of taking an island under which it takes
  one; then, for each letter and rule, the draws left unnamed.
- **geometry.** It lays each mark `cut` sets, or those `--mark` names, by its geometry rather
  than its pixels: drawn sixteen times finer, the mark's box, and the line midway across the
  gap between it and its letter (`geometric`). It lays a box over the mark, its edge toward the
  letter on that line, and judges what it hides under each rule; and it sets the page's edge on
  the same line and reports what the reads as built name of the mark's run. It prints a line
  for each em and scale, then, for each mark, the draws at which `cover` and `cut` cannot place
  the mark by its pixels, and of those how many each rule names under the box and past the
  edge, and how many by the threshold alone.
- **cost.** It runs one look of `<piece>` through the SVG renderer, with any further
  arguments the look takes, under a profiler that counts the process's CPU time. It prints
  the look's CPU time, the time each read took and how many times it ran, the time the cut
  read spent walking its pixels rather than drawing, the time of a page drawn whole, and the
  time the measure of islands took. A loaded machine inflates CPU time less than the clock.

It writes nothing in the repository but what the look writes in the clone's local folder.
Exit codes: 0 when it measured, 1 when the look did not draw, 2 on a usage error.
"""

from __future__ import annotations

import argparse
import contextlib
import cProfile
import importlib
import math
import pstats
import sys
import tempfile
import time
from collections.abc import Callable, Collection, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
#: The capability's scripts, which hold the look and its `_lib`.
SCRIPTS = ROOT / ".pkit" / "capabilities" / "visual-communication" / "scripts"

#: The em, in image pixels, from which a least graze counts as large, for the shares a rule
#: names.
LARGE = 25.0

#: The levels of ink the island measure is probed at: the lightest a pixel's darkest sample may
#: be, drawn black on white, for the pixel to be ink at that level. The first three are the
#: tool's (`LEVELS`), the first its strong ink (`STRONG`). resvg 0.48 draws coverage in steps of
#: 16, so the last is any ink.
LEVELS = (127, 159, 191, 223, 254)
#: The tool's strong ink, the level the threshold counts.
STRONG_INK = LEVELS[0]
#: Any ink at all: the level the reads take a span's ink at while the probe runs.
ANY_INK = LEVELS[-1]
#: How the pixels of an island join: by a side alone, or by a side or a corner.
JOININGS = (4, 8)
#: What a cover must hide of an island for the island to be gone: all its pixels at its level, all
#: its strong pixels (all its pixels where it holds none), or more than half its pixels.
GONE = ("all of it", "its strong ink", "most of it")
SIDES = ((-1, 0), (1, 0), (0, -1), (0, 1))
CORNERS = ((-1, -1), (-1, 1), (1, -1), (1, 1))
#: The darkness a pixel with no ink is read at, lighter than any level.
NO_INK = 255


@dataclass(frozen=True)
class Measure:
    """A setting of the island measure: a cover is named where it hides a whole island of a
    span's ink, the island found at any of `levels`, its pixels joined by `joining` neighbours,
    and gone as `gone` says."""

    levels: tuple[int, ...]
    joining: int
    gone: str

    @property
    def name(self) -> str:
        joined = "sides" if self.joining == 4 else "sides and corners"
        at = ", ".join(str(level) for level in self.levels)
        return f"islands at {at}, joined by {joined}, gone when {self.gone} is hidden"


#: The levels the probe finds islands at, a cover named where it takes an island at any of them:
#: each level alone, then those from strong ink to 191, then all of them.
TOGETHER = (*((level,) for level in LEVELS), (127, 159, 191), LEVELS)

#: Every setting the probe judges.
MEASURES = tuple(
    Measure(levels, joining, gone) for levels in TOGETHER for joining in JOININGS for gone in GONE
)

#: The setting of the tool's levels and joining (`LEVELS`, `NEIGHBOURS`), with an island taken
#: where all of it is hidden: as the tool takes one past the page's edge, where a pixel is cut
#: or shows (`_takes_an_island` with no `shows`), and as (A) takes one under a box. Under a box
#: the tool reads what still shows of each pixel too (`TAKEN`), which `Loss.island` holds.
BUILT = Measure(TOGETHER[-2], 8, GONE[0])


@dataclass(frozen=True)
class Loss:
    """What one cause hides of a span's strong ink: the span's em as the read takes it, in
    image pixels, how many pixels, in how many rows, whether they all lie in one outermost row
    or column of the span's ink, and how many pixels of strong ink the span holds. And the
    settings of the island measure under which the cause hides a whole island of its ink,
    whether the reads as built take an island of it, and whether they name it, by the threshold
    or by their measure of islands."""

    em: float
    pixels: int
    rows: int
    at_an_edge: bool
    ink: int = 0
    islands: frozenset[Measure] = frozenset()
    island: bool = False
    built: bool = False


@dataclass(frozen=True)
class Rule:
    """A rule for naming a loss: its name, the fewest pixels it names at an em in image pixels,
    and whether it spares a loss laid in one outermost row or column of the span's ink."""

    name: str
    fewest: Callable[[float], float]
    spares_an_edge: bool = False

    def names(self, loss: Loss) -> bool:
        if self.spares_an_edge and loss.at_an_edge:
            return False
        return loss.pixels >= self.fewest(loss.em)


def whole(share: float, em: float) -> int:
    """The whole pixels `share` of `em` squared holds."""
    return math.floor(round(share * em**2, 6))


def rules(least: Callable[[float], int]) -> tuple[Rule, ...]:
    """The rules of the threshold DEC-045 weighs, the module's own `least` first."""
    return (
        Rule("the threshold as built", least),
        Rule("0.0125 in whole pixels", lambda em: max(whole(0.0125, em), 1)),
        Rule("a floor of two", lambda em: max(whole(0.01, em), 2)),
        Rule("0.0125 as an area", lambda em: max(0.0125 * em**2, 1)),
        Rule("0.0095 as an area", lambda em: max(0.0095 * em**2, 1)),
        Rule("0.0095 as an area, never under two", lambda em: max(0.0095 * em**2, 2)),
        Rule("0.01 as an area", lambda em: max(0.01 * em**2, 1)),
        Rule("0.013 in whole pixels", lambda em: max(whole(0.013, em), 1)),
        Rule("0.015 in whole pixels", lambda em: max(whole(0.015, em), 1)),
        Rule("0.007 in whole pixels", lambda em: max(whole(0.007, em), 1)),
        Rule("two pixels or more", lambda _em: 2),
        Rule("the geometric test: two pixels or more, but not in an edge", lambda _em: 2, True),
    )


#: The rules whose margin the summary of the reads as built gives beside the measure: the
#: threshold as built, and 0.0125 in whole pixels, which DEC-045 weighs against it.
MARGINS = ("the threshold as built", "0.0125 in whole pixels")


Pixel = tuple[int, int]


def islands_of(
    ink: Mapping[Pixel, int], level: int, joining: int, holding: Iterable[Pixel]
) -> list[list[Pixel]]:
    """The islands of `ink`, each pixel's darkest sample by its row and column, at `level` that
    hold a pixel of `holding`: its pixels no lighter than `level`, in sets joined by a side, or
    by a side or a corner where `joining` is 8. Only the islands asked for are walked."""
    steps = SIDES if joining == 4 else SIDES + CORNERS
    seen: set[Pixel] = set()
    found: list[list[Pixel]] = []
    for start in holding:
        if start in seen or ink.get(start, NO_INK) > level:
            continue
        seen.add(start)
        island = [start]
        for row, column in island:
            for down, across in steps:
                near = (row + down, column + across)
                if near not in seen and ink.get(near, NO_INK) <= level:
                    seen.add(near)
                    island.append(near)
        found.append(island)
    return found


def is_gone(
    island: Sequence[Pixel], hidden: set[Pixel], ink: Mapping[Pixel, int], gone: str
) -> bool:
    """Whether a cover that hides `hidden` takes `island` of `ink` as `gone` says."""
    lost = sum(pixel in hidden for pixel in island)
    if gone == GONE[2]:
        return 2 * lost > len(island)
    if gone == GONE[1]:
        strong = [pixel for pixel in island if ink[pixel] <= STRONG_INK]
        if strong:
            return all(pixel in hidden for pixel in strong)
    return lost == len(island)


def gone_islands(
    ink: Mapping[Pixel, int], hidden: Sequence[Pixel], measures: Sequence[Measure] = MEASURES
) -> frozenset[Measure]:
    """Each of `measures` under which a cover that hides `hidden` of `ink` takes a whole
    island. The islands at each level and joining are walked once, whatever the measures that
    find them."""
    lost = set(hidden)
    if not lost:
        return frozenset()
    touched: dict[tuple[int, int], list[list[Pixel]]] = {}
    for each in measures:
        for level in each.levels:
            if (level, each.joining) not in touched:
                touched[level, each.joining] = islands_of(ink, level, each.joining, lost)
    return frozenset(
        each
        for each in measures
        if any(
            is_gone(island, lost, ink, each.gone)
            for level in each.levels
            for island in touched[level, each.joining]
        )
    )


@dataclass(frozen=True)
class Dot:
    """A dot a reader needs, as its plant sets it: what it is, the runs of its line, the place
    of the run that holds it, and where the run holds more: whether the dot stands apart from
    the rest by an empty row (`rows`) or column (`columns`), into how many parts such rows or
    columns split the run's ink, and which part is the dot. A dot that is its whole run stands
    apart by nothing."""

    name: str
    runs: tuple[str, ...]
    at: int
    apart: str = ""
    parts: int = 1
    part: int = 0


#: The dots the probe hides whole: a full stop and a decimal point, each a run of its own and
#: each inside its run, and the dot of ż.
DOTS = (
    Dot("full stop", ("end", "."), 1),
    Dot("decimal point", ("3", ".", "5"), 1),
    Dot("dot of ż", ("ż",), 0, "rows", 2, 0),
    Dot("full stop in its word", ("end.",), 0, "columns", 4, 3),
    Dot("decimal point in its number", ("3.5",), 0, "columns", 3, 1),
)


@dataclass(frozen=True)
class Hidden:
    """A dot under a box laid over all of it: the loss the reads find, the dot's pixels of any
    ink and of strong ink, whether the box hid all of them, how many pixels it hid beside
    them, the weakest level at which its run's ink falls into the dot's parts (`dot_pixels`, 0
    where it falls so at none), and at each level and joining whether the dot is an island of its
    own (`standing`), held at none where no level parts it, so no box was laid."""

    dot: Dot
    loss: Loss
    ink: int
    strong: int
    whole: bool
    beyond: int = 0
    apart: int = 0
    stands: Mapping[tuple[int, int], str] = field(default_factory=dict)


@dataclass(frozen=True)
class Drawn:
    """The plants at one em and scale: the háček's loss, the least graze, the next, every step
    of the graze, and each dot hidden whole."""

    em: float
    scale: float
    háček: Loss
    least: Loss
    next: Loss
    dots: tuple[Hidden, ...] = ()
    grazes: tuple[Loss, ...] = ()


@dataclass(frozen=True)
class Read:
    """What the reads found of one span: its characters, its strong ink, the pixels of its ink
    on the page a cause hides, the page's width in px, the darkest sample of each pixel of its
    ink on the page, and how much of each such pixel's ink the page drawn whole still shows."""

    text: str
    strong: Any
    hidden: list[Pixel]
    width: float
    ink: Mapping[Pixel, int] = field(default_factory=dict)
    shows: Mapping[Pixel, int] | None = None


def loss_of(strong: Any, hidden: Sequence[Pixel]) -> Loss:
    """The loss of `hidden`, the pixels of `strong`'s ink on the page a cause hides."""
    rows = {row for row, _ in hidden}
    columns = {column for _, column in hidden}
    ink_rows = [row for row, _ in strong.on_page]
    ink_columns = [column for _, column in strong.on_page]
    edge = bool(hidden) and (
        (len(rows) == 1 and rows <= {min(ink_rows), max(ink_rows)})
        or (len(columns) == 1 and columns <= {min(ink_columns), max(ink_columns)})
    )
    return Loss(strong.em, len(hidden), len(rows), edge, strong.found)


def measured(found: Read, tool: ModuleType) -> Loss:
    """The loss of what the reads `found`: of its strong ink for the threshold, and of all its
    ink for the island measure, and whether `tool`'s reads as built name it."""
    strong = [pixel for pixel in found.hidden if found.ink[pixel] <= STRONG_INK]
    loss = loss_of(found.strong, strong)
    island = tool._takes_an_island(found.ink, found.hidden, found.shows)
    built = len(strong) >= tool._least(loss.em) or island
    return replace(loss, islands=gone_islands(found.ink, found.hidden), island=island, built=built)


def on_page(strong: Any) -> dict[Pixel, int]:
    """The darkest sample of each pixel of the ink `strong` holds that lies on the page."""
    return {pixel: dark for pixel, dark in strong.ink.items() if pixel not in strong.beyond}


@contextlib.contextmanager
def any_ink(tool: ModuleType) -> Iterator[Callable[[Any], Mapping[Pixel, int]]]:
    """While it lasts, the tool's cut read takes each span's ink at `ANY_INK`, where it takes
    it at its lightest level (`FAINT`), and its strong ink as it does unpatched. It yields what
    gives, for the strong ink a read found, the darkest sample of each pixel of the span's ink
    on the page, drawn black on white."""
    names = vars(tool)
    held = names["FAINT"]
    names["FAINT"] = ANY_INK
    try:
        yield on_page
    finally:
        names["FAINT"] = held


@contextlib.contextmanager
def hidden_pixels(tests: ModuleType, face: Path | None) -> Iterator[list[Read]]:
    """While it lasts, the look's tests' reads keep what they find of each span with ink on
    the page in the list it gives, all its ink and the pixels of it a cause hides, and name
    nothing; their plants are set in `face` where it is given, since a plant reads its face
    from the tests' `FONT` as it is drawn."""
    reads = tests.viewing_tool._Page
    names = vars(tests)
    kept: list[Read] = []
    held = reads._partly, names["FONT"]
    with any_ink(tests.viewing_tool) as ink_of:

        def partly(page: Any, span: Any, strong: Any, element: str) -> Iterator[Any]:
            ink = ink_of(strong)
            if ink:
                shows = page._shown(span, strong)
                hidden = [pixel for pixel, shown in shows.items() if not shown]
                kept.append(Read(span.text or "", strong, hidden, page.width, ink, shows))
            return iter(())

        reads._partly = partly
        if face is not None:
            names["FONT"] = face
        try:
            yield kept
        finally:
            reads._partly, names["FONT"] = held


def dot_pixels(dot: Dot, ink: Mapping[Pixel, int]) -> tuple[list[Pixel], list[Pixel], int]:
    """The pixels of `ink` that are `dot`, those that are the rest of its run, and the weakest
    of `LEVELS` at which the run's ink falls into the dot's parts. A dot that is its run is all
    of `ink`, at any ink. Otherwise the ink no lighter than a level is split by its empty rows
    or columns, from the weakest level on, until it falls into the dot's parts: the dot is all
    the ink in its part's rows or columns, and the rest all the ink in the others'. Neither, at
    level 0, where no level splits it so. For the dot of ż that level is where it stands apart
    from its letter; for a dot in a word, where every letter of the word stands apart, which
    may be stronger than where the dot does."""
    if not dot.apart:
        return list(ink), [], ANY_INK
    axis = 0 if dot.apart == "rows" else 1
    for level in reversed(LEVELS):
        lines = sorted({pixel[axis] for pixel, dark in ink.items() if dark <= level})
        parts = _runs_of(lines)
        if len(parts) == dot.parts:
            first, last = parts[dot.part]
            others = [part for at, part in enumerate(parts) if at != dot.part % dot.parts]
            mine = [pixel for pixel in ink if first <= pixel[axis] <= last]
            rest = [pixel for pixel in ink if any(lo <= pixel[axis] <= hi for lo, hi in others)]
            return mine, rest, level
    return [], [], 0


def _runs_of(lines: Sequence[int]) -> list[tuple[int, int]]:
    """The first and last of each run of consecutive numbers in `lines`, sorted."""
    runs: list[tuple[int, int]] = []
    for each in lines:
        if runs and each == runs[-1][1] + 1:
            runs[-1] = (runs[-1][0], each)
        else:
            runs.append((each, each))
    return runs


def standing(
    mine: Sequence[Pixel], rest: Sequence[Pixel], ink: Mapping[Pixel, int]
) -> dict[tuple[int, int], str]:
    """At each level and joining, whether the dot `mine` of `ink` is an island of its own: `own`,
    `merged` with an island of the `rest` of its run, `split` into more than one island, or with
    `no ink` at that level."""
    others = set(rest)
    found: dict[tuple[int, int], str] = {}
    for level in LEVELS:
        for joining in JOININGS:
            held = islands_of(ink, level, joining, mine)
            if not held:
                found[level, joining] = "no ink"
            elif any(others.intersection(island) for island in held):
                found[level, joining] = "merged"
            else:
                found[level, joining] = "split" if len(held) > 1 else "own"
    return found


#: A box laid over a plant: from where its text's baseline lies and its font size in px, the
#: box's fields, as the look's tests' plants take it.
Over = Callable[[float, float], Mapping[str, Any]]


def drawn_at(tests: ModuleType, kept: list[Read], em: float, scale: float) -> Drawn:
    """The háček, the graze and each dot at `em` and `scale`, each read through the look's
    tests' plants."""

    def read(words: str | Sequence[str], over: Over | None) -> list[Read]:
        kept.clear()
        with tempfile.TemporaryDirectory() as folder:
            tests.set_at(Path(folder), words, em, scale, over)
        return list(kept)

    def alone(words: str, over: Over) -> Loss:
        [found] = read(words, over)
        return measured(found, tests.viewing_tool)

    háček = alone(tests.HACEK, tests.háček_box)
    grazes = [alone(tests.DESCENDERS, tests.graze_box(step, scale)) for step in tests.GRAZE_STEPS]
    levels = sorted({graze.pixels for graze in grazes if graze.pixels})
    least = next(graze for graze in grazes if graze.pixels == levels[0])
    after = next(graze for graze in grazes if graze.pixels == levels[min(1, len(levels) - 1)])
    dots = tuple(hidden_dot(dot, read, tests) for dot in DOTS)
    return Drawn(em, scale, háček, least, after, dots, tuple(grazes))


def hidden_dot(
    dot: Dot, read: Callable[[Sequence[str], Over | None], list[Read]], tests: ModuleType
) -> Hidden:
    """`dot` drawn, then drawn again under a box over all of it, as the look's `tests` lay
    one (`box_over`)."""
    held = [found for found in read(dot.runs, None) if found.text == dot.runs[dot.at]]
    nothing = Hidden(dot, Loss(0.0, 0, 0, False), 0, 0, False)
    if not held:
        return nothing
    ink = held[0].ink
    mine, rest, apart = dot_pixels(dot, ink)
    if not mine:
        return nothing
    [found] = [
        each
        for each in read(dot.runs, tests.box_over(mine, held[0].strong, held[0].width))
        if each.text == dot.runs[dot.at]
    ]
    lost = set(found.hidden)
    return Hidden(
        dot,
        measured(found, tests.viewing_tool),
        len(mine),
        sum(ink[pixel] <= STRONG_INK for pixel in mine),
        lost.issuperset(mine),
        len(lost.difference(mine)),
        apart,
        standing(mine, rest, ink),
    )


def line(drawn: Drawn, threshold: int) -> str:
    """One em and scale, as `cover` prints it."""
    háček = drawn.háček
    dots = ", ".join(
        f"{each.dot.name} {each.loss.pixels} of {each.strong}, ink"
        f" {'whole' if each.whole else 'part'} of {each.ink}, +{each.beyond}, apart {each.apart}"
        for each in drawn.dots
    )
    return (
        f"em {drawn.em:5.1f}  scale {drawn.scale:<6g}  read em {háček.em:7.3f}"
        f"  threshold {threshold:3d}"
        f"  háček {háček.pixels:3d} px of {háček.ink:4d}, in {háček.rows} row(s)"
        f"{', all in an edge' if háček.at_an_edge else ''}"
        f"  least graze {drawn.least.pixels:3d} px, next {drawn.next.pixels:3d} px"
        f"  dots hidden: {dots}"
    )


def _dot_losses(every: Sequence[Drawn], dot: Dot) -> list[tuple[Drawn, Hidden]]:
    return [(drawn, each) for drawn in every for each in drawn.dots if each.dot == dot]


def summary(every: Sequence[Drawn], weighed: Sequence[Rule], graze_em: float) -> list[str]:
    """For each rule `weighed`, what it leaves of the háček and of each dot, the draws of each
    a pixel less would leave, the least grazes it names, and the least graze at `graze_em`.
    First, the dots the box did not hide whole, and those with no strong ink apart from their
    letter."""
    lines: list[str] = []
    small = [each for each in every if each.em < LARGE]
    large = [each for each in every if each.em >= LARGE]
    at_graze_em = [each for each in every if each.em == graze_em]
    marks = [("háček", [(drawn, drawn.háček) for drawn in every])]
    for dot in DOTS:
        hidden = _dot_losses(every, dot)
        apart = [each for _, each in hidden if each.strong]
        lines.append(
            f"{dot.name}: hidden whole at {sum(each.whole for each in apart)} of {len(hidden)}"
            f" draws, {len(hidden) - len(apart)} with no strong ink of its own,"
            f" {min((each.strong for each in apart), default=0)} to"
            f" {max((each.strong for each in apart), default=0)} pixels"
        )
        marks.append((dot.name, [(drawn, each.loss) for drawn, each in hidden]))
    for rule in weighed:
        lines.append(rule.name)
        for name, losses in marks:
            missed = [
                (drawn, loss) for drawn, loss in losses if loss.pixels and not rule.names(loss)
            ]
            held = [
                (drawn, loss)
                for drawn, loss in losses
                if rule.names(loss) and not rule.names(replace(loss, pixels=loss.pixels - 1))
            ]
            lines.append(f"  {name} draws unnamed: {len(missed)} of {len(losses)}{_where(missed)}")
            lines.append(f"  {name} draws a pixel from unnamed: {len(held)}{_where(held)}")
        named_small = sum(rule.names(each.least) for each in small)
        named_large = sum(rule.names(each.least) for each in large)
        lines.append(
            f"  least grazes named: {named_small} of {len(small)} below an em of {LARGE:g},"
            f" {named_large} of {len(large)} from {LARGE:g} on"
        )
        if at_graze_em:
            spared = all(
                not rule.names(each.least) and rule.names(each.next) for each in at_graze_em
            )
            lines.append(_least_graze(graze_em, spared))
    return lines


def _least_graze(graze_em: float, spared: bool) -> str:
    """Whether a rule spares the least graze at `graze_em` at every scale and names the row
    above it."""
    said = "spared, the row above named" if spared else "not spared, or the row above not named"
    return f"  the least graze at {graze_em:g}: {said}"


def _marks(every: Sequence[Drawn]) -> list[tuple[str, list[tuple[Drawn, Loss]]]]:
    """The háček, each dot a box was laid over, and the least graze, each with its losses."""
    marks = [("háček", [(drawn, drawn.háček) for drawn in every])]
    for dot in DOTS:
        hidden = [(drawn, each) for drawn, each in _dot_losses(every, dot) if each.ink]
        marks.append((dot.name, [(drawn, each.loss) for drawn, each in hidden]))
    marks.append(("least graze", [(drawn, drawn.least) for drawn in every]))
    return marks


def built_summary(
    every: Sequence[Drawn], thresholds: Sequence[Rule], levels: Sequence[int], graze_em: float
) -> list[str]:
    """What the reads as built name of each mark, by the first of `thresholds`, the threshold as
    built, or by their measure of islands at `levels`, and where they leave one unnamed; at how
    many draws the measure takes an island of it; of the draws each of `thresholds` names with
    no pixel to spare, how many the measure names too; the graze steps the measure alone names;
    and the least graze at `graze_em`."""
    threshold = thresholds[0]
    at = ", ".join(str(level) for level in levels)
    lines = [f"as built: the threshold, or an island taken at {at}, joined by sides and corners"]
    for name, losses in _marks(every):
        named = [(drawn, loss) for drawn, loss in losses if loss.built]
        alone = [(drawn, loss) for drawn, loss in named if not threshold.names(loss)]
        unnamed = [(drawn, loss) for drawn, loss in losses if not loss.built]
        taken = sum(loss.island for _, loss in losses)
        margins = "; ".join(_margin(losses, each) for each in thresholds)
        lines.append(
            f"  {name}: named {len(named)} of {len(losses)}, taken by the measure {taken}, by the"
            f" measure alone {len(alone)}, unnamed {len(unnamed)}{_where(unnamed)}; {margins}"
        )
    alone = [
        (drawn, graze)
        for drawn in every
        for graze in drawn.grazes
        if graze.built and not threshold.names(graze)
    ]
    steps = sum(len(drawn.grazes) for drawn in every)
    lines.append(f"  graze steps the measure alone names: {len(alone)} of {steps}{_where(alone)}")
    at_graze_em = [drawn for drawn in every if drawn.em == graze_em]
    if at_graze_em:
        spared = all(not each.least.built and each.next.built for each in at_graze_em)
        lines.append(_least_graze(graze_em, spared))
    return lines


def _margin(losses: Sequence[tuple[Drawn, Loss]], threshold: Rule) -> str:
    """Of `losses`, the draws `threshold` names with no pixel to spare, and how many of them the
    measure of islands as built names too."""
    held = [
        (drawn, loss)
        for drawn, loss in losses
        if threshold.names(loss) and not threshold.names(replace(loss, pixels=loss.pixels - 1))
    ]
    both = [(drawn, loss) for drawn, loss in held if loss.island]
    return (
        f"a pixel from unnamed by {threshold.name} {len(held)},"
        f" named by the measure too {len(both)}{_where(both)}"
    )


def island_summary(every: Sequence[Drawn], threshold: Rule, graze_em: float) -> list[str]:
    """For each setting of the island measure, each mark's draws named by `threshold`, by the
    measure, by both or by neither; where each dot is an island of its own; and the grazes the
    measure names that `threshold` spares. First, the weakest level at which each dot's run falls
    into the dot's parts."""
    lines: list[str] = []
    for dot in DOTS:
        if dot.apart:
            hidden = _dot_losses(every, dot)
            counted = {
                level: [drawn for drawn, each in hidden if each.apart == level]
                for level in (*reversed(LEVELS), 0)
            }
            lines.append(
                f"{dot.name}, its run's ink in its parts: "
                + ", ".join(
                    f"from {level or 'no level'}: {len(drawns)}{_ems(drawns)}"
                    for level, drawns in counted.items()
                    if drawns
                )
            )
    for measure in MEASURES:
        lines.append(measure.name)
        for name, losses in _marks(every):
            lines.append(f"  {name}: " + _classes(losses, threshold, measure))
        for dot in DOTS:
            states: dict[str, list[Drawn]] = {}
            for drawn, each in _dot_losses(every, dot):
                state = _best(each.stands, measure)
                states.setdefault(state, []).append(drawn)
            lines.append(
                f"  {dot.name} as an island: "
                + ", ".join(f"{state} {len(at)}{_ems(at)}" for state, at in sorted(states.items()))
            )
        alone = [
            (drawn, graze)
            for drawn in every
            for graze in drawn.grazes
            if measure in graze.islands and not threshold.names(graze)
        ]
        steps = sum(len(drawn.grazes) for drawn in every)
        lines.append(
            f"  graze steps the islands alone name: {len(alone)} of {steps}{_where(alone)}"
        )
        at_graze_em = [drawn for drawn in every if drawn.em == graze_em]
        if at_graze_em:
            named = [drawn for drawn in at_graze_em if measure in drawn.least.islands]
            lines.append(
                f"  the least graze at {graze_em:g}: "
                + (f"named by the islands at {len(named)} scale(s)" if named else "spared")
            )
    return lines


#: How a dot stands where the probe found no dot to hide: no level parts it from its run.
NOT_FOUND = "not found"
#: How a dot stands at a level, from what the measure can name to what it cannot.
STANDINGS = ("own", "split", "merged", "no ink", NOT_FOUND)


def _best(stands: Mapping[tuple[int, int], str], measure: Measure) -> str:
    """How a dot stands under `measure`: the best it stands at any of the measure's levels."""
    found = [stands.get((level, measure.joining), NOT_FOUND) for level in measure.levels]
    return min(found, key=STANDINGS.index)


def _classes(losses: Sequence[tuple[Drawn, Loss]], threshold: Rule, measure: Measure) -> str:
    """How many of `losses` `threshold` and `measure` each name, and where the neither lie."""
    kinds: dict[str, list[tuple[Drawn, Loss]]] = {
        "both": [],
        "the threshold alone": [],
        "the islands alone": [],
        "neither": [],
    }
    for drawn, loss in losses:
        by_threshold, by_islands = threshold.names(loss), measure in loss.islands
        kind = ("both" if by_islands else "the threshold alone") if by_threshold else None
        kind = kind or ("the islands alone" if by_islands else "neither")
        kinds[kind].append((drawn, loss))
    return ", ".join(f"{kind} {len(found)}" for kind, found in kinds.items()) + (
        f"; neither{_where(kinds['neither'])}" if kinds["neither"] else ""
    )


def _ems(drawns: Sequence[Drawn]) -> str:
    if not drawns:
        return ""
    ems = sorted({drawn.em for drawn in drawns})
    return f" (ems {ems[0]:g} to {ems[-1]:g})"


def _where(missed: Sequence[tuple[Drawn, Loss]]) -> str:
    if not missed:
        return ""
    ems = sorted({drawn.em for drawn, _ in missed})
    pixels = sorted({loss.pixels for _, loss in missed})
    return f", at ems {ems[0]:g} to {ems[-1]:g}, of {', '.join(str(p) for p in pixels)} pixel(s)"


def importable(folder: Path) -> None:
    """Put `folder` on the import path, once."""
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))


def ems_of(args: argparse.Namespace) -> tuple[float, ...]:
    """The ems a probe draws at: each `--em`, or every `--step` from `--from` to `--to`."""
    if args.em:
        return tuple(args.em)
    tenths = range(round(args.start / args.step), round(args.end / args.step) + 1)
    return tuple(round(at * args.step, 6) for at in tenths)


def cover(args: argparse.Namespace) -> int:
    importable(ROOT)
    tests = importlib.import_module("tests.test_visual_communication_look")
    scales = tuple(args.scale) or tuple(tests.SCALES)
    every: list[Drawn] = []
    with hidden_pixels(tests, args.face) as kept:
        for em in ems_of(args):
            for scale in scales:
                drawn = drawn_at(tests, kept, em, scale)
                every.append(drawn)
                print(line(drawn, tests.viewing_tool._least(drawn.háček.em)), flush=True)
    print()
    weighed = rules(tests.viewing_tool._least)
    print("\n".join(summary(every, weighed, float(tests.LEAST_GRAZE_EM))))
    print()
    levels = tests.viewing_tool.LEVELS
    margins = [each for each in weighed if each.name in MARGINS]
    print("\n".join(built_summary(every, margins, levels, float(tests.LEAST_GRAZE_EM))))
    print()
    print("\n".join(island_summary(every, weighed[0], float(tests.LEAST_GRAZE_EM))))
    return 0


@dataclass(frozen=True)
class Edge:
    """A mark a reader needs, set past an edge of the page, `right` or `top`, with the rest of
    its line on the page: the mark as `Dot` gives it, and for a mark that is a run of its own,
    the place of the run beside it, which stays on the page."""

    dot: Dot
    edge: str
    beside: int | None = None


#: The marks the cut probe sets past an edge: a full stop inside its word and one that is a
#: run of its own, past the right edge, and the dot of ż and the háček of ž, past the top.
EDGES = (
    Edge(Dot("full stop in its word", ("end.",), 0, "columns", 4, 3), "right"),
    Edge(Dot("full stop", ("end", "."), 1), "right", 0),
    Edge(Dot("dot of ż", ("ż",), 0, "rows", 2, 0), "top"),
    Edge(Dot("háček", ("ž",), 0, "rows", 2, 0), "top"),
)


@dataclass(frozen=True)
class AtEdge:
    """A mark set past an edge, as the reads as built read it: whether it lay wholly past the
    edge and the rest of its line on the page, what the reads named of the mark's run, a cause
    to each, the pixels of the run's strong ink past the edge, the threshold's there, whether all
    of an island of the run's ink lay past the edge, and what they named of the line's other
    runs."""

    edge: Edge
    placed: bool
    named: tuple[str, ...] = ()
    past: int = 0
    threshold: int = 0
    island: bool = False
    others: tuple[str, ...] = ()


@contextlib.contextmanager
def set_in(tests: ModuleType, face: Path | None) -> Iterator[None]:
    """While it lasts, the look's tests' plants are set in `face`, where it is given."""
    names = vars(tests)
    held = names["FONT"]
    if face is not None:
        names["FONT"] = face
    try:
        yield
    finally:
        names["FONT"] = held


@dataclass
class Found:
    """What the reads found of a page: the strong ink and the ink of each span, by its
    characters, and the page's width in px."""

    spans: dict[str, Any] = field(default_factory=dict[str, Any])
    width: float = 0.0


@contextlib.contextmanager
def strong_found(tool: ModuleType) -> Iterator[Found]:
    """While it lasts, the tool's reads keep what they find of each span and of the page, and
    read as they do unpatched."""
    page = tool._Page
    held = page._strong
    found = Found()

    def strong(self: Any, text: Any, line: Any, index: int, *rest: Any) -> Any:
        read = held(self, text, line, index, *rest)
        found.spans[line[index].text or ""] = read
        found.width = self.width
        return read

    page._strong = strong
    try:
        yield found
    finally:
        page._strong = held


def moved_past(edge: Edge, found: Found) -> tuple[float, float] | None:
    """How far to move a plant, in px across and down, for `edge`'s mark to lie past its edge
    and the rest of its line on the page, from what a first draw `found` of each run: by whole
    rows or columns, so the edge falls on the empty row or column between them. None where no
    level parts the mark from the rest."""
    strong = found.spans.get(edge.dot.runs[edge.dot.at])
    if strong is None:
        return None
    ink = on_page(strong)
    if edge.beside is None:
        mine, rest, _ = dot_pixels(edge.dot, ink)
    else:
        mine, rest = list(ink), list(on_page(found.spans[edge.dot.runs[edge.beside]]))
    if not mine:
        return None
    if edge.edge == "top":
        last = max(row for row, _ in mine)
        return 0.0, -(strong.top + (last + 1) * 2 * strong.reach / strong.rows)
    first = min(column for _, column in mine)
    if rest and max(column for _, column in rest) >= first:
        return None
    return (strong.columns - first) * found.width / strong.columns, 0.0


def at_edge(tests: ModuleType, edge: Edge, em: float, scale: float) -> AtEdge:
    """`edge`'s mark set past its edge at `em` and `scale`, read by the reads as built."""
    tool = tests.viewing_tool
    runs = edge.dot.runs
    text = runs[edge.dot.at]
    with tempfile.TemporaryDirectory() as folder:
        with any_ink(tool), strong_found(tool) as first:
            tests.plant(Path(folder), runs, em, scale)
        moved = moved_past(edge, first)
        if moved is None:
            return AtEdge(edge, False)
        with strong_found(tool) as found:
            drawing = tests.plant(Path(folder), runs, em, scale, moved=moved)
    strong = found.spans[text]
    beside = None if edge.beside is None else found.spans[runs[edge.beside]]
    if beside is None:
        mine, rest, _ = dot_pixels(edge.dot, strong.ink)
        beyond = set(strong.beyond)
    else:
        mine, rest = list(strong.ink), list(beside.ink)
        beyond = set(strong.beyond) | set(beside.beyond)
    placed = bool(mine) and beyond.issuperset(mine) and not beyond.intersection(rest)
    named = tuple(
        [
            f"{each.why}{', an island' if each.island else ''}"
            for each in drawing.lost
            if each.text == text
        ]
        + [each.why for each in drawing.dropped if each.text == text]
    )
    others = tuple(each.why for each in (*drawing.lost, *drawing.dropped) if each.text != text)
    return AtEdge(
        edge,
        placed,
        named,
        strong.past,
        tool._least(strong.em),
        tool._takes_an_island(strong.ink, strong.beyond),
        others,
    )


def edge_line(em: float, scale: float, read: Sequence[AtEdge]) -> str:
    """One em and scale, as `cut` prints it."""
    marks = "; ".join(
        f"{each.edge.dot.name}: "
        + (
            f"named {', '.join(each.named) or 'nothing'}, strong past {each.past} of the"
            f" threshold's {each.threshold}{', an island past' if each.island else ''}"
            + (f", the rest named {', '.join(each.others)}" if each.others else "")
            if each.placed
            else "not placed"
        )
        for each in read
    )
    return f"em {em:5.1f}  scale {scale:<6g}  {marks}"


def edge_summary(every: Sequence[tuple[float, AtEdge]]) -> list[str]:
    """For each mark, of its draws, how many lay past the edge, how many of those the reads
    named, by the threshold or by the measure alone or dropped as off the page, and where they
    left one unnamed or could not place it."""
    lines: list[str] = []
    for edge in EDGES:
        drawn = [(em, each) for em, each in every if each.edge == edge]
        placed = [(em, each) for em, each in drawn if each.placed]
        named = [(em, each) for em, each in placed if each.named]
        off = [each for _, each in named if OFF_THE_PAGE in each.named]
        by_threshold = [
            each
            for _, each in named
            if OFF_THE_PAGE not in each.named and each.past >= each.threshold
        ]
        unnamed = [em for em, each in placed if not each.named]
        unplaced = [em for em, each in drawn if not each.placed]
        others = [em for em, each in placed if each.others]
        lines.append(
            f"{edge.dot.name}, past the {edge.edge} edge: placed {len(placed)} of {len(drawn)},"
            f" named {len(named)} (by the threshold {len(by_threshold)},"
            f" by the measure alone {len(named) - len(by_threshold) - len(off)},"
            f" off the page {len(off)}), unnamed {len(unnamed)}{_span(unnamed)},"
            f" not placed {len(unplaced)}{_span(unplaced)},"
            f" the rest named {len(others)}{_span(others)}"
        )
    return lines


#: The cause the reads give a span whose ink lies wholly past the page.
OFF_THE_PAGE = "off the page"


def _span(ems: Sequence[float]) -> str:
    return f" (ems {min(ems):g} to {max(ems):g})" if ems else ""


def cut(args: argparse.Namespace) -> int:
    importable(ROOT)
    tests = importlib.import_module("tests.test_visual_communication_look")
    scales = tuple(args.scale) or tuple(tests.SCALES)
    every: list[tuple[float, AtEdge]] = []
    with set_in(tests, args.face):
        for em in ems_of(args):
            for scale in scales:
                read = [at_edge(tests, edge, em, scale) for edge in EDGES]
                every.extend((em, each) for each in read)
                print(edge_line(em, scale, read), flush=True)
    print()
    print("\n".join(edge_summary(every)))
    return 0


#: What a cause must take of an island for the island to be named: all of it; all of it but
#: one pixel; or all of it at strong ink and most of it at the two lighter levels, each counting
#: a pixel where the page drawn whole shows none of its ink. Or all of it, counting a pixel of
#: an island where it no longer shows at the island's level, so that an island is taken where
#: none of it still shows at its level (DEC-045's rule (B)); then the same where the cause also
#: hides wholly some pixel of the span's ink, or some pixel of that island, as an opaque part
#: does and a translucent one does not, the last as built (`AS_BUILT`); and last, the third or
#: the sixth. The threshold counts the pixels the cause hides under each.
TAKEN = (
    "all of it",
    "all of it but one pixel",
    "all of it at 127, most of it at 159 and 191",
    "none of it still shows at its level",
    "none of it still shows at its level, and a pixel of the span's ink hidden wholly",
    "none of it still shows at its level, and a pixel of it hidden wholly",
    "the third or the sixth",
)
#: The way of taking an island the tool holds (`_takes_an_island`).
AS_BUILT = TAKEN[5]
#: The shares of the em squared the threshold is weighed at.
SHARES = (0.0125, 0.01)
#: Each rule `partial`, `ogonek` and `geometry` weigh: a share with a way of taking an island.
WEIGHED = tuple((share, taken) for share in SHARES for taken in TAKEN)
#: The tool's levels, at which the rules of `TAKEN` find islands, joined by a side or a corner.
TOOL_LEVELS = LEVELS[:3]
#: How many steps a box's edge takes across a pixel.
EIGHTHS = 8
#: The sides of a dot a box's edge steps in from.
SIDES_IN = ("top", "bottom", "left", "right")
#: The trace id of the box a plant draws after its text.
BOX = "figure/over"
#: A box's place before a probe moves it: a pixel at the page's top left, which no plant's text
#: reaches.
AWAY = {"x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0}


def takes(ink: Mapping[Pixel, int], lost: Collection[Pixel], taken: str) -> bool:
    """Whether a cause that hides `lost` of `ink` takes an island at any of the tool's levels,
    its pixels joined by a side or a corner, as `taken` says, of the first three of `TAKEN`."""
    gone = set(lost)
    for level in TOOL_LEVELS:
        for island in islands_of(ink, level, 8, gone):
            hidden = sum(pixel in gone for pixel in island)
            if taken == TAKEN[1]:
                whole = hidden >= len(island) - 1
            elif taken == TAKEN[2] and level != STRONG_INK:
                whole = 2 * hidden > len(island)
            else:
                whole = hidden == len(island)
            if whole:
                return True
    return False


def unseen(
    ink: Mapping[Pixel, int], shows: Mapping[Pixel, int], hit: Collection[Pixel] | None = None
) -> bool:
    """Whether, of `ink`, an island at any of the tool's levels, its pixels joined by a side or
    a corner, no longer shows at its level anywhere in the page drawn whole, `shows` giving how
    much of each pixel's ink still shows there; and, where `hit` is given, holds a pixel of
    `hit`."""
    for level in TOOL_LEVELS:
        faded = {
            pixel
            for pixel, dark in ink.items()
            if dark <= level and pixel in shows and NO_INK - shows[pixel] > level
        }
        for island in islands_of(ink, level, 8, faded):
            if set(island) <= faded and (hit is None or not set(hit).isdisjoint(island)):
                return True
    return False


@dataclass(frozen=True)
class Cause:
    """What a cause hides of a span, as the rules of `WEIGHED` judge it: the span's em as the
    read takes it, the pixels of its strong ink the cause hides, and the ways of taking an
    island under which the cause takes one."""

    em: float
    strong: int
    taking: frozenset[str] = frozenset()

    def by_threshold(self, share: float) -> bool:
        return self.strong >= max(whole(share, self.em), 1)

    def named(self, rule: tuple[float, str]) -> bool:
        share, taken = rule
        return self.by_threshold(share) or taken in self.taking

    def by_island_alone(self, rule: tuple[float, str]) -> bool:
        share, taken = rule
        return taken in self.taking and not self.by_threshold(share)


def cause_of(
    ink: Mapping[Pixel, int],
    lost: Collection[Pixel],
    em: float,
    shows: Mapping[Pixel, int] | None = None,
) -> Cause:
    """A cause that hides `lost` of `ink`, at the span's `em`. Where `shows` gives how much of
    each pixel's ink still shows, the fourth to the sixth of `TAKEN` read it; and else, where
    nothing of a pixel shows but what the cause leaves, they take what the first does."""
    taking = {taken for taken in TAKEN[:3] if takes(ink, lost, taken)}
    if shows is None:
        if TAKEN[0] in taking:
            taking.update(TAKEN[3:6])
    elif unseen(ink, shows):
        taking.add(TAKEN[3])
        if lost:
            taking.add(TAKEN[4])
        if unseen(ink, shows, lost):
            taking.add(TAKEN[5])
    if taking & {TAKEN[2], TAKEN[5]}:
        taking.add(TAKEN[6])
    return Cause(em, sum(ink[pixel] <= STRONG_INK for pixel in lost), frozenset(taking))


@dataclass
class Laid:
    """A plant's page as the tool's reads take it, with the box drawn after its text, which a
    probe moves: the page, the box's element, each span by its characters with its text, its
    line, its place on the line and where its groups move it, the scale, and how the renderer
    writes a number."""

    page: Any
    box: Any
    spans: dict[str, tuple[Any, Any, int, tuple[float, float]]]
    scale: float
    number: Callable[[float], str]

    def strong(self, key: str) -> Any:
        """What the cut read finds of the span `key`: its strong ink and its ink."""
        text, line, index, at = self.spans[key]
        return self.page._strong(text, line, index, at, self.scale)

    def place(self, box: Mapping[str, float]) -> None:
        """Move the box to `box`, by its edges, its fields written as the renderer writes them."""
        fields = {
            "x": box["left"],
            "y": box["top"],
            "width": box["right"] - box["left"],
            "height": box["bottom"] - box["top"],
        }
        for name, value in fields.items():
            self.box.set(name, self.number(value))


def laid(
    tests: ModuleType, folder: Path, words: str | Sequence[str], em: float, scale: float
) -> Laid:
    """The page `tests.plant` draws of `words` at `em` and `scale`, with its box set away from
    the text, as the tool's reads take it, its faces written in `folder`."""
    children, sizes = tests.plant_of(words, em, scale, lambda _base, _size: dict(AWAY))
    svg = tests.drawn_page(*children, **sizes)
    [page] = tests.viewing.pages_of(tests.scene(*children, **sizes))
    tool = tests.viewing_tool
    drawn = tool._Page(svg, folder, tests.viewing.line_widths(page))
    spans: dict[str, tuple[Any, Any, int, tuple[float, float]]] = {}
    for text, x, y in drawn._texts(drawn.root, 0.0, 0.0):
        for line in text.findall(tool.SPAN):
            for index, span in enumerate(line):
                if (span.text or "").strip():
                    spans[span.text or ""] = (text, line, index, (x, y))
    [box] = [each for each in drawn.root.iter() if each.get("data-id") == BOX]
    # The reads take the scale the image drawn whole gives, as `draw` hands it to them.
    read_at = drawn.image(scale).width / drawn.width
    return Laid(drawn, box, spans, read_at, tests.svg.number)


def edges_of(box: Mapping[str, float]) -> dict[str, float]:
    """A box's fields, as a plant's `over` gives them, by its edges."""
    return {
        "left": box["x"],
        "top": box["y"],
        "right": box["x"] + box["width"],
        "bottom": box["y"] + box["height"],
    }


def covered(plant: Laid, key: str, strong: Any) -> tuple[list[Pixel], dict[Pixel, int]]:
    """As the tool's cover read finds them, the pixels of the span `key`'s ink on the page the
    box hides, and how much of each pixel's ink still shows in the page drawn whole: the
    greatest difference of its samples between the read's two draws, the span's letters black
    and then white, from 0 for none of it to 255 for all of it."""
    _, line, index, _ = plant.spans[key]
    shows = plant.page._shown(line[index], strong)
    return [pixel for pixel, shown in shows.items() if not shown], shows


def left_at(shows: Mapping[Pixel, int], pixels: Iterable[Pixel], level: int) -> int:
    """How many of `pixels` still show in the page drawn whole at `level` or darker."""
    return sum(NO_INK - shows.get(pixel, 0) <= level for pixel in pixels)


@dataclass(frozen=True)
class Stepped:
    """A box's edge at one step across a dot: the side it comes in from, how many eighths of a
    pixel past the dot's edge, whether the dot is gone from the page drawn whole, no pixel of
    it left at its own level, and what the box hides as the rules judge it."""

    side: str
    eighths: int
    gone: bool
    cause: Cause


@dataclass(frozen=True)
class Crossed:
    """A dot a box's edge stepped across at one em and scale: the dot, the darkest of the
    tool's levels its ink reaches, its own level, 0 where it was not placed or reaches none,
    each step, and the steps at which the tool's own measure judged otherwise than the
    probe's."""

    dot: Dot
    level: int
    steps: tuple[Stepped, ...] = ()
    disagree: int = 0


def crossed(tests: ModuleType, folder: Path, dot: Dot, em: float, scale: float) -> Crossed:
    """`dot` drawn at `em` and `scale` under a box a pixel past it on each side, as the cover
    probe lays one, but for one side, whose edge steps from the dot's edge across it by eighths
    of a pixel, from each side in turn."""
    key = dot.runs[dot.at]
    plant = laid(tests, folder, dot.runs, em, scale)
    strong = plant.strong(key)
    ink = on_page(strong)
    mine, _, _ = dot_pixels(dot, ink)
    if not mine:
        return Crossed(dot, 0)
    darkest = min(ink[pixel] for pixel in mine)
    level = next((each for each in TOOL_LEVELS if darkest <= each), 0)
    if not level:
        return Crossed(dot, 0)
    rows = [row for row, _ in mine]
    columns = [column for _, column in mine]
    to_page = plant.page.width / strong.columns
    to_swath = 2 * strong.reach / strong.rows
    edges = {
        "top": strong.top + min(rows) * to_swath,
        "bottom": strong.top + (max(rows) + 1) * to_swath,
        "left": min(columns) * to_page,
        "right": (max(columns) + 1) * to_page,
    }
    inward = {"top": to_swath, "bottom": -to_swath, "left": to_page, "right": -to_page}
    across = {
        "top": max(rows) - min(rows) + 1,
        "bottom": max(rows) - min(rows) + 1,
        "left": max(columns) - min(columns) + 1,
        "right": max(columns) - min(columns) + 1,
    }
    steps: list[Stepped] = []
    disagree = 0
    for side in SIDES_IN:
        for eighths in range(EIGHTHS * across[side] + 1):
            box = {each: edges[each] - inward[each] for each in SIDES_IN}
            box[side] = edges[side] + inward[side] * eighths / EIGHTHS
            plant.place(box)
            hidden, shows = covered(plant, key, strong)
            cause = cause_of(strong.ink, hidden, strong.em, shows)
            disagree += tests.viewing_tool._takes_an_island(strong.ink, hidden, shows) != (
                AS_BUILT in cause.taking
            )
            steps.append(Stepped(side, eighths, not left_at(shows, mine, level), cause))
    return Crossed(dot, level, tuple(steps), disagree)


def grazed(tests: ModuleType, folder: Path, em: float, scale: float) -> list[Cause]:
    """Each step of the cover probe's graze at `em` and `scale`, as the rules judge it."""
    key = tests.DESCENDERS
    plant = laid(tests, folder, key, em, scale)
    strong = plant.strong(key)
    size = em / scale
    base = tests.baseline_of(size)
    found: list[Cause] = []
    for step in tests.GRAZE_STEPS:
        plant.place(edges_of(tests.graze_box(step, scale)(base, size)))
        hidden, shows = covered(plant, key, strong)
        found.append(cause_of(strong.ink, hidden, strong.em, shows))
    return found


def _rule(rule: tuple[float, str]) -> str:
    return f"{rule[0]:g} and {rule[1]}"


def partial_line(em: float, scale: float, dots: Sequence[Crossed], grazes: Sequence[Cause]) -> str:
    """One em and scale, as `partial` prints it: for each dot, its level, its steps, those at
    which it is gone, and of those the steps each rule of `WEIGHED` leaves unnamed; and of the
    graze's steps, those each rule's island alone names."""
    marks = "; ".join(
        f"{each.dot.name}: "
        + (
            f"level {each.level}, gone {sum(step.gone for step in each.steps)} of"
            f" {len(each.steps)}, unnamed "
            + ",".join(
                str(sum(step.gone and not step.cause.named(rule) for step in each.steps))
                for rule in WEIGHED
            )
            if each.level
            else "not placed"
        )
        for each in dots
    )
    alone = ",".join(str(sum(each.by_island_alone(rule) for each in grazes)) for rule in WEIGHED)
    return f"em {em:5.1f}  scale {scale:<6g}  {marks}; grazes by the island alone {alone}"


def partial_summary(
    dots: Sequence[tuple[float, float, Crossed]],
    grazes: Sequence[tuple[float, float, Sequence[Cause]]],
    graze_em: float,
) -> list[str]:
    """For each dot, at strong ink and at a lighter level apart, the steps at which it is gone,
    and for each rule the steps it leaves gone and unnamed; then for each rule the graze steps
    its island alone names, the least grazes it names, and the least graze at `graze_em`."""
    lines = [f"rules, in order: {'; '.join(_rule(rule) for rule in WEIGHED)}"]
    lines.append(
        f"steps at which the tool's measure judged otherwise than the probe's:"
        f" {sum(each.disagree for _, _, each in dots)}"
    )
    for dot in DOTS:
        held = [(em, scale, each) for em, scale, each in dots if each.dot == dot]
        unplaced = [em for em, _, each in held if not each.level]
        lines.append(f"{dot.name}: not placed {len(unplaced)}{_span(unplaced)}")
        for faint in (False, True):
            at = [
                (em, scale, each)
                for em, scale, each in held
                if each.level and (each.level != STRONG_INK) == faint
            ]
            if not at:
                continue
            gone = [(em, scale, step) for em, scale, each in at for step in each.steps if step.gone]
            lines.append(
                f"  {'with no strong ink' if faint else 'with strong ink'}: {len(at)} draws,"
                f" {sum(len(each.steps) for _, _, each in at)} steps, gone at {len(gone)}"
            )
            for rule in WEIGHED:
                missed = [
                    (em, scale, step) for em, scale, step in gone if not step.cause.named(rule)
                ]
                draws = {(em, scale) for em, scale, _ in missed}
                sides = sorted({step.side for _, _, step in missed})
                lines.append(
                    f"    {_rule(rule)}: gone and unnamed at {len(missed)} steps, of"
                    f" {len(draws)} draws{_span([em for em, _ in draws])}"
                    + (f", from the {', '.join(sides)}" if sides else "")
                )
    lines.append("grazes")
    small = [each for each in grazes if each[0] < LARGE]
    large = [each for each in grazes if each[0] >= LARGE]
    for rule in WEIGHED:
        alone = [
            (em, cause) for em, _, steps in grazes for cause in steps if cause.by_island_alone(rule)
        ]
        lines.append(
            f"  {_rule(rule)}: steps the island alone names {len(alone)} of"
            f" {sum(len(steps) for _, _, steps in grazes)}{_span([em for em, _ in alone])};"
            f" least grazes named {sum(least_of(steps).named(rule) for _, _, steps in small)}"
            f" of {len(small)} below {LARGE:g},"
            f" {sum(least_of(steps).named(rule) for _, _, steps in large)} of {len(large)}"
            f" from {LARGE:g} on; the least graze at {graze_em:g} named at"
            f" {sum(least_of(steps).named(rule) for em, _, steps in grazes if em == graze_em)}"
            " scale(s)"
        )
    return lines


def least_of(steps: Sequence[Cause]) -> Cause:
    """The graze step that hides the fewest strong pixels of any that hide some."""
    fewest = min(each.strong for each in steps if each.strong)
    return next(each for each in steps if each.strong == fewest)


def partial(args: argparse.Namespace) -> int:
    importable(ROOT)
    tests = importlib.import_module("tests.test_visual_communication_look")
    scales = tuple(args.scale) or tuple(tests.SCALES)
    dots: list[tuple[float, float, Crossed]] = []
    grazes: list[tuple[float, float, list[Cause]]] = []
    with (
        set_in(tests, args.face),
        any_ink(tests.viewing_tool),
        tempfile.TemporaryDirectory() as folder,
    ):
        for em in ems_of(args):
            for scale in scales:
                each = [crossed(tests, Path(folder), dot, em, scale) for dot in DOTS]
                steps = grazed(tests, Path(folder), em, scale)
                dots.extend((em, scale, dot) for dot in each)
                grazes.append((em, scale, steps))
                print(partial_line(em, scale, each, steps), flush=True)
    print()
    print("\n".join(partial_summary(dots, grazes, float(tests.LEAST_GRAZE_EM))))
    return 0


#: The marks joined to their letter the `ogonek` probe hides: the ogonek of ą and of ę.
OGONEKS = ("ą", "ę")


@dataclass(frozen=True)
class Joined:
    """A mark joined to its letter under a box rising from below to the baseline: the box's
    cover as the rules judge it, the letter's strong pixels wholly below the baseline, and the
    pixels the box hides that are not."""

    letter: str
    cause: Cause
    below: int
    above: int


def joined(tests: ModuleType, folder: Path, letter: str, em: float, scale: float) -> Joined:
    """The ogonek of `letter` at `em` and `scale` under a box from the baseline down."""
    plant = laid(tests, folder, letter, em, scale)
    strong = plant.strong(letter)
    size = em / scale
    base = tests.baseline_of(size)
    to_swath = 2 * strong.reach / strong.rows
    plant.place({"left": 0.0, "top": base, "right": 12 * size, "bottom": base + 0.6 * size + 10})
    hidden, shows = covered(plant, letter, strong)
    below = [
        pixel
        for pixel, dark in strong.ink.items()
        if dark <= STRONG_INK and strong.top + pixel[0] * to_swath >= base
    ]
    above = [pixel for pixel in hidden if strong.top + pixel[0] * to_swath < base]
    return Joined(letter, cause_of(strong.ink, hidden, strong.em, shows), len(below), len(above))


def ogonek(args: argparse.Namespace) -> int:
    importable(ROOT)
    tests = importlib.import_module("tests.test_visual_communication_look")
    scales = tuple(args.scale) or tuple(tests.SCALES)
    every: list[tuple[float, float, Joined]] = []
    with (
        set_in(tests, args.face),
        any_ink(tests.viewing_tool),
        tempfile.TemporaryDirectory() as folder,
    ):
        for em in ems_of(args):
            for scale in scales:
                read = [joined(tests, Path(folder), letter, em, scale) for letter in OGONEKS]
                every.extend((em, scale, each) for each in read)
                print(
                    f"em {em:5.1f}  scale {scale:<6g}  "
                    + "; ".join(
                        f"{each.letter}: strong below the baseline {each.below}, hidden"
                        f" {each.cause.strong}, above it {each.above}, islands"
                        f" {', '.join(sorted(each.cause.taking)) or 'none'}"
                        for each in read
                    ),
                    flush=True,
                )
    print()
    for letter in OGONEKS:
        held = [(em, each) for em, _, each in every if each.letter == letter]
        lines = [
            f"{letter}: {len(held)} draws, strong below the baseline"
            f" {min(each.below for _, each in held)} to {max(each.below for _, each in held)},"
            f" hidden above it at most {max(each.above for _, each in held)}"
        ]
        for rule in WEIGHED:
            unnamed = [em for em, each in held if not each.cause.named(rule)]
            lines.append(f"  {_rule(rule)}: unnamed {len(unnamed)}{_span(unnamed)}")
        print("\n".join(lines))
    return 0


#: How many times finer `geometry` draws a mark to find where it lies.
FINER = 16


def geometric(
    tests: ModuleType, folder: Path, dot: Dot, em: float, scale: float
) -> tuple[dict[str, float], float] | None:
    """Where `dot` lies by geometry at `em` and `scale`, in the page's px: drawn `FINER` times
    finer, where it stands apart from its letter, its box, and the line midway across the gap
    between it and the rest of its run. None where it stands apart there at no level."""
    fine = laid(tests, folder, dot.runs, em * FINER, scale * FINER)
    strong = fine.strong(dot.runs[dot.at])
    mine, rest, _ = dot_pixels(dot, on_page(strong))
    if not mine or not rest:
        return None
    to_page = fine.page.width / strong.columns
    to_swath = 2 * strong.reach / strong.rows
    rows = [row for row, _ in mine]
    columns = [column for _, column in mine]
    box = {
        "top": strong.top + min(rows) * to_swath,
        "bottom": strong.top + (max(rows) + 1) * to_swath,
        "left": min(columns) * to_page,
        "right": (max(columns) + 1) * to_page,
    }
    if dot.apart == "rows":
        gap = (box["bottom"] + strong.top + min(row for row, _ in rest) * to_swath) / 2
    else:
        gap = ((max(column for _, column in rest) + 1) * to_page + box["left"]) / 2
    return box, gap


@dataclass(frozen=True)
class ByGeometry:
    """A mark laid by geometry at one em and scale: whether the cover probe places it by its
    pixels; what a box over it, its edge toward the letter midway across the gap, hides as the
    rules judge it, and the mark's strong pixels left in the page drawn whole, those whose
    centre lies on the mark's side of the gap; and with the page's edge laid there instead,
    what the reads as built name of the mark's run, and the cut as the rules judge it."""

    name: str
    placed: bool
    cover: Cause | None = None
    left: int = 0
    cut: Cause | None = None
    named: tuple[str, ...] = ()


def by_geometry(tests: ModuleType, folder: Path, edge: Edge, em: float, scale: float) -> ByGeometry:
    """`edge`'s mark at `em` and `scale`, laid by geometry under a box and past the page's
    edge."""
    dot = edge.dot
    key = dot.runs[dot.at]
    found = geometric(tests, folder, dot, em, scale)
    plant = laid(tests, folder, dot.runs, em, scale)
    strong = plant.strong(key)
    placed = bool(dot_pixels(dot, on_page(strong))[0])
    if found is None:
        return ByGeometry(dot.name, placed)
    mark, gap = found
    to_page = plant.page.width / strong.columns
    to_swath = 2 * strong.reach / strong.rows
    box = {
        "top": mark["top"] - to_swath,
        "bottom": mark["bottom"] + to_swath,
        "left": mark["left"] - to_page,
        "right": mark["right"] + to_page,
    }
    box["bottom" if edge.edge == "top" else "left"] = gap
    plant.place(box)
    hidden, shows = covered(plant, key, strong)
    if edge.edge == "top":
        here = [pixel for pixel in strong.ink if strong.top + (pixel[0] + 0.5) * to_swath < gap]
        moved = (0.0, -gap)
    else:
        here = [pixel for pixel in strong.ink if (pixel[1] + 0.5) * to_page > gap]
        moved = (plant.page.width - gap, 0.0)
    left = left_at(shows, here, STRONG_INK)
    cover_cause = cause_of(strong.ink, hidden, strong.em, shows)
    tool = tests.viewing_tool
    with strong_found(tool) as cut_found:
        drawing = tests.plant(folder, dot.runs, em, scale, moved=moved)
    cut_strong = cut_found.spans[key]
    named = tuple(
        f"{each.why}{', an island' if each.island else ''}"
        for each in drawing.lost
        if each.text == key
    ) + tuple(each.why for each in drawing.dropped if each.text == key)
    return ByGeometry(
        dot.name,
        placed,
        cover_cause,
        left,
        cause_of(cut_strong.ink, cut_strong.beyond, cut_strong.em),
        named,
    )


def geometry(args: argparse.Namespace) -> int:
    importable(ROOT)
    tests = importlib.import_module("tests.test_visual_communication_look")
    scales = tuple(args.scale) or tuple(tests.SCALES)
    marks = [
        each
        for each in EDGES
        if each.beside is None and (not args.mark or each.dot.name in args.mark)
    ]
    every: list[tuple[float, ByGeometry]] = []
    with set_in(tests, args.face), tempfile.TemporaryDirectory() as folder:
        for em in ems_of(args):
            for scale in scales:
                with any_ink(tests.viewing_tool):
                    read = [by_geometry(tests, Path(folder), edge, em, scale) for edge in marks]
                every.extend((em, each) for each in read)
                print(
                    f"em {em:5.1f}  scale {scale:<6g}  "
                    + "; ".join(_by_geometry(each) for each in read),
                    flush=True,
                )
    print()
    for edge in marks:
        held = [(em, each) for em, each in every if each.name == edge.dot.name]
        unplaced = [(em, each) for em, each in held if not each.placed and each.cover]
        lines = [
            f"{edge.dot.name}: {len(held)} draws, not placed by its pixels {len(unplaced)}"
            f"{_span([em for em, _ in unplaced])}"
        ]
        for rule in WEIGHED:
            for cause in ("cover", "cut"):
                found = [getattr(each, cause) for _, each in unplaced]
                lines.append(
                    f"  {_rule(rule)}, {cause}: named {sum(each.named(rule) for each in found)},"
                    f" by the threshold {sum(each.by_threshold(rule[0]) for each in found)}"
                )
        print("\n".join(lines))
    return 0


def _by_geometry(each: ByGeometry) -> str:
    if each.cover is None or each.cut is None:
        return f"{each.name}: apart at no level when drawn finer"
    return (
        f"{each.name}: {'placed' if each.placed else 'not placed'} by its pixels; under a box"
        f" strong hidden {each.cover.strong}, strong left {each.left}, islands"
        f" {', '.join(sorted(each.cover.taking)) or 'none'}; past the edge strong"
        f" {each.cut.strong}, islands {', '.join(sorted(each.cut.taking)) or 'none'}, named"
        f" {', '.join(each.named) or 'nothing'}"
    )


#: The reads, as the profile names them in the tool's module, with what each is.
READS = {
    "_strong": "the cut read, a span drawn alone on its swath",
    "_swath": "  of which, one swath drawn and walked",
    "_shown": "the cover read, the page drawn twice on a span's ink",
    "_with_ink": "  of which, one draw of the page",
    "_drew": "the check for ink",
    "image": "a page drawn whole",
    "region": "a band of a page drawn whole",
    "_takes_an_island": "the measure of islands, of the cut and the cover",
}


#: The module whose functions the profile is read for.
TOOL_MODULE = "viewing_tool.py"


def cost_lines(stats: pstats.Stats, total: float) -> list[str]:
    """What `cost` prints of a look's profile: its CPU time, and each read's. pstats keeps its
    rows in `stats`, by file, line and function, each the calls, the function's own time, its
    time with what it called, and its callers."""
    rows: Mapping[tuple[str, int, str], Any] = vars(stats)["stats"]
    found: dict[str, tuple[int, float]] = {}
    drawing = 0.0
    for (file, _, name), row in rows.items():
        if not file.endswith(TOOL_MODULE):
            continue
        if name in READS:
            found[name] = (row[1], row[3])
        if name == "_tool":
            drawing += sum(
                timed[3]
                for (caller, _, of), timed in row[4].items()
                if caller.endswith(TOOL_MODULE) and of == "_swath"
            )
    lines = [f"the look: {total:.1f} s of CPU"]
    reads = 0.0
    for name, what in READS.items():
        if name in found:
            calls, spent = found[name]
            lines.append(f"{what}: {spent:.1f} s over {calls} call(s), {spent / calls:.3f} s each")
            if name in ("_strong", "_shown", "_takes_an_island"):
                reads += spent
    if "_swath" in found:
        walked = found["_swath"][1] - drawing
        lines.append(f"the cut read's walk over its pixels: {walked:.1f} s, draws {drawing:.1f} s")
    lines.append(f"the look less the cut and cover reads: {total - reads:.1f} s")
    return lines


def cost(args: argparse.Namespace) -> int:
    importable(SCRIPTS)
    look = importlib.import_module("look")
    profile = cProfile.Profile(time.process_time, builtins=False)
    held = sys.argv
    sys.argv = ["look.py", args.piece, "--renderer", "svg", *args.look]
    started = time.process_time()
    try:
        code = profile.runcall(look.main)
    finally:
        sys.argv = held
    total = time.process_time() - started
    if code != 0:
        print(f"the look did not draw: exit {code}", file=sys.stderr)
        return 1
    print("\n".join(cost_lines(pstats.Stats(profile), total)))
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="visual_svg_reads.py",
        description="Measure the SVG renderer's reads of cover and cut (DEC-045).",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    probes = (
        ("cover", "what the threshold and the measure name and leave at each em", cover),
        ("cut", "what the reads name of a mark past the page's edge at each em", cut),
        (
            "partial",
            "a box's edge stepped across each dot, and the graze, under each rule",
            partial,
        ),
        ("ogonek", "an ogonek under a box rising to the baseline, under each rule", ogonek),
        ("geometry", "a mark that meets its letter, laid under a box by geometry", geometry),
    )
    for name, said, run in probes:
        probe = commands.add_parser(name, help=said)
        probe.add_argument("--from", dest="start", type=float, default=10.0)
        probe.add_argument("--to", dest="end", type=float, default=40.0)
        probe.add_argument("--step", type=float, default=0.1)
        probe.add_argument("--em", type=float, action="append", default=[])
        probe.add_argument("--scale", type=float, action="append", default=[])
        probe.add_argument("--face", type=Path, help="the face the plants are set in")
        if name == "geometry":
            marks = [each.dot.name for each in EDGES if each.beside is None]
            probe.add_argument("--mark", action="append", choices=marks, default=[])
        probe.set_defaults(run=run)
    timed = commands.add_parser("cost", help="what one look's reads cost, in CPU time")
    timed.add_argument("piece")
    timed.add_argument("look", nargs=argparse.REMAINDER, help="further arguments of the look")
    timed.set_defaults(run=cost)
    args = parser.parse_args(argv)
    return args.run(args)


if __name__ == "__main__":
    sys.exit(main())
