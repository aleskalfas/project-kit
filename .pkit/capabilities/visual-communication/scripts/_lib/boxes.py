"""The checks of boxes (visual-communication DEC-046 point 3): edges that nearly line up, among
the siblings of each scene and between the leaves of different groups on one page (DEC-067),
and boxes that overlap, among siblings.

Each check does the arithmetic and judges nothing. Each finding asks the reviewer for
attention, who judges on the image whether the place it names is a fault or is meant, and
none fails (DEC-002 point 7, DEC-030 point 7): a component may place one part on another on
purpose, and a box may differ from what is drawn in it. The one exception is an overlap a
released version says is meant, which validation states as a fact (below).

- **The boxes read** are the scene's: each element's frame, in px of its page, relative to
  its parent (`components.md`, "What a scene holds"). The frames the viewing step writes
  beside an image are those boxes scaled into the image's pixels, so a check that read them
  would judge a pixel of rounding and the brand's step of space in another unit than the
  scene's. Siblings are compared in the frame they share, and two parts of different groups
  where each lies on its page, its place with those of the groups it is nested in added
  (`_Part.placed`). The scene holds each length to a hundredth of a px, so a difference is
  taken to a hundredth too (`_apart`).
- **Siblings** are the elements one group holds directly, such as the items of one list or
  the parts of one component. Each pair is compared once, in drawing order, in the frame
  they share. Left out: a line, whose ends and arrowheads meet or cross what they join; a
  group that draws nothing but lines, such as a tie's; an element of no area, which shows
  nothing to line up; and a page, which shares no drawing with the pages beside it.
- **A pixel of rounding** (`ROUNDING`): two values no further apart are one value. The brand's
  smallest step of space (`Step`) is the least value it gives a shared step of space at the
  scene's key, `space.1` and its like (`smallest_step`).

`near_alignment` reports a place where two values nearly agree and do not: they differ by
more than a pixel of rounding and by less than the brand's smallest step, so no spacing the
brand offers, and hardly chosen.

- **Edges and centres.** A pair is compared on each axis on three lines: across, their left
  edges, centres and right edges; down, their tops, middles and bottoms. A pair that lines up
  on one line of an axis is not reported on another line of it, since that near miss follows
  from the line chosen, as an icon and a label centred in a row differ at their tops. One
  finding names every line of the axis on which the pair nearly lines up.
- **A text's room** (DEC-067 point 3). Only a text of one line given no width fills its
  width (`scene.fills_width`). Any other text is compared across only on the line on which
  its anchor stands its lines (`scene.stands`), since its box past its lines is room no reader
  sees, and two parts only on the lines both are compared on. Its insets across, and those of
  a part inside its box, are compared only where it stands its lines in the middle, and no
  gap across that starts or ends at its room is taken. Down, it is compared on every line.
- **A part another holds.** Where one of a pair holds the other, as a card's box holds its
  head, the held part's insets on the two sides of each axis are compared, not their centres:
  its left and right insets across, its top and bottom down. A part that lies on one edge of
  the other within a pixel lines up on it, so is not reported on that axis.
- **Gaps.** On each axis, each sibling's gap to the nearest sibling after it that stands
  beside it, sharing more than a pixel of its height across or of its width down. Gaps no
  more than a pixel apart are one spacing. One finding names two spacings of one group and
  axis that nearly agree, with the gaps of each.
- **Between groups** (DEC-067 points 1, 2 and 4). Every two *leaves* of different groups on
  one page, the compared parts that are no group, neither a tie's part, are compared as two
  siblings are. A tie's parts are the leaves nested in the group a tie's component draws,
  told by its connector, a line the scene marks with `attached`: the nearest entry's group
  below the page that the connector is nested in, whose trace id ends in `[<id>]` or
  `#<place>` (`_ENTRY`). A pair's *sides* are the two parts the nearest group both are
  nested in holds, that the two are or are nested in, the first the one drawn first. The near
  misses of one offset between two sides are one finding (`NEAR_ALIGNMENT_BETWEEN_GROUPS`),
  unless the finding of those two sides as siblings names them, or the finding of two lists
  whose gaps explain them does (`_placed`). The sums are kept to the pairs whose values on a
  line lie within a step of each other (`_candidates`).
- **Two lists** (DEC-067 point 5). A list is a group whose compared parts, two or more, are
  groups that one component draws. Two lists on one page whose items one component draws,
  each nested in as many groups that component draws as the other, are reported where a
  spacing of one and a spacing of the other nearly agree, unless one of the two has a spacing
  within a pixel of each, whose near miss it reports among that list's siblings.

`overlaps` reports two siblings whose boxes overlap by more than a pixel each way, where
neither holds the other, a text a sibling covers among them. It reads a text's whole box.

- **A meant overlap** (DEC-066 points 1 and 2). An element whose part names, under
  `lies-over`, parts drawn before it holds their trace ids, and the library version that
  holds the part, where one does (`components.md`, "What a scene holds"). An overlap of the
  element with one it names carries that version (`Finding.lies_over_in`), and its message is
  that of any overlap. Whether the version is released is read where the finding is read:
  validation states the overlap as a fact, `box-overlap-meant` (`meant`), where it is released
  and still as it was released, and reads it as `box-overlap` elsewhere; the viewing step
  reads every overlap as `box-overlap` (`checks.Reading`). Every two siblings are compared as
  before, so a pair named so is measured, and the check of edges compares it too.

**Each states its reach** (`NEAR_ALIGNMENT_CHECK`, `BOX_OVERLAP_CHECK`), beside its id, in
the words of its entry in the list of checks, since the reviewer leans on its silence
(DEC-063 point 1). Both compare no scenes: each finding is one scene's. Where the brand
gives no step of space at a scene's key, or one no longer than a pixel of rounding, nothing
can be near, so `near_alignment` states as a fact that it measured nothing there
(`NEAR_ALIGNMENT_UNMEASURED`, DEC-063 point 2).

Knows nothing of files, the lock or the check's run: the check places each finding.
"""

from __future__ import annotations

import re
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, field, replace
from typing import Any

from _lib.findings import ATTENTION, FACT, Finding
from _lib.scene import IDS, LIBRARY, LIES_OVER, fills_width, stands
from _lib.scene_checks import Reach, SceneCheck

#: The calls for attention of the two checks of boxes: edges that nearly line up among
#: siblings, and between groups (DEC-067 point 4), and boxes that overlap.
NEAR_ALIGNMENT = "near-alignment"
NEAR_ALIGNMENT_BETWEEN_GROUPS = "near-alignment-between-groups"
BOX_OVERLAP = "box-overlap"

#: The fact validation states, in place of `BOX_OVERLAP`, at an overlap that a released
#: version, still as it was released, says is meant (DEC-066 point 2).
BOX_OVERLAP_MEANT = "box-overlap-meant"

#: The fact the check of edges that nearly line up states at a key where it could measure
#: nothing (DEC-063 point 2).
NEAR_ALIGNMENT_UNMEASURED = "near-alignment-unmeasured"

#: What each check of boxes leaves out, by the base they share (DEC-046 point 3).
_BOTH_LEAVE_OUT = (
    "a line, and a group below which every element but a group is a line or of no area, "
    "such as a tie's (DEC-046 point 3)",
    "an element of no area (DEC-046 point 3)",
    "a page (DEC-046 point 3)",
)

#: The check of edges that nearly line up, with its reach (DEC-046 point 3, DEC-063 points 1
#: and 2, DEC-067).
NEAR_ALIGNMENT_CHECK = SceneCheck(
    "edges and centres of siblings, and of parts of different groups, that nearly line up, "
    "and spacings that nearly agree",
    id="edges-nearly-in-line",
    labels=(NEAR_ALIGNMENT, NEAR_ALIGNMENT_BETWEEN_GROUPS, NEAR_ALIGNMENT_UNMEASURED),
    reach=Reach(
        measures=(
            "the left edges, centres and right edges, and the tops, middles and bottoms, of "
            "each two siblings neither of which holds the other within a pixel "
            "(DEC-046 point 3)",
            "the insets on the two sides of each axis of a part inside a sibling's box "
            "(DEC-046 point 3)",
            "the spacings of one group's siblings on each axis, each gap taken from a sibling "
            "to the nearest one after it that stands beside it (DEC-046 point 3)",
            "the lines and the insets of each two leaves of different groups on one page, the "
            "parts it compares among siblings that are no group, each where it lies on its "
            "page, as of two siblings (DEC-067 point 1)",
            "the spacings of each two lists on one page whose items one component draws, each "
            "nested in as many groups that component draws as the other: a list is a group "
            "whose compared parts are two or more groups whose field `component` names one "
            "component (DEC-067 point 5)",
        ),
        leaves_out=(
            *_BOTH_LEAVE_OUT,
            "two parts, or two lists, that no one page holds: on two pages, or one of them "
            "nested in no group the scene's `pages` names (DEC-067 point 6)",
            "a group, with a part that is not its sibling: a part of another group, or a part "
            "nested in it (DEC-067 point 1)",
            "a tie's part, with a part of another group: a part nested in the nearest group "
            "below its page whose trace id ends in `[<id>]` or `#<place>`, of the groups a "
            "line the scene marks with `attached` is nested in (DEC-067 point 1)",
            "across, each line but the one on which a text that does not fill its width "
            "stands its lines by its `text-anchor`, its left edge at `start`, its centre at "
            "`middle` and its right edge at `end`, and so two parts that share no line across "
            "on which both are compared: a text fills its width only where it has one line "
            "and the scene names `engine` as its width's source (DEC-067 point 3)",
            "the insets across of a text that does not fill its width inside another part's "
            "box, and of a part inside its box, unless it stands its lines at `middle` "
            "(DEC-067 point 3)",
            "a gap across that starts or ends at a side of a text that does not fill its "
            "width on which it does not stand its lines (DEC-067 point 3)",
            "the spacings of other groups: a group that is no list, two lists whose items "
            "different components draw, and two lists whose items one component draws nested "
            "in different numbers of the groups whose field `component` names it, a list and "
            "one nested in it among them (DEC-067 point 5)",
            "the gap between two parts of different groups (DEC-067 point 5)",
            "a spacing of one list near a spacing of another where one of the two lists has a "
            "spacing within a pixel of each, which it compares among that list's siblings "
            "(DEC-067 point 5)",
            "the other lines of an axis on which a pair, of siblings or of leaves of different "
            "groups, lines up on one line within a pixel, of those on which both are compared "
            "(DEC-046 point 3, DEC-067 point 2)",
            "the edges and centres of a pair one of which holds the other within a pixel, "
            "whose insets it measures instead (DEC-046 point 3, DEC-067 point 2)",
            "the insets on an axis of a part inside another's box that lies within a pixel of "
            "one of that box's edges on that axis (DEC-046 point 3, DEC-067 point 2)",
            "the gap between two siblings that share no more than a pixel of the other axis "
            "(DEC-063 point 1)",
        ),
        states=(
            f"`{NEAR_ALIGNMENT_UNMEASURED}`, at a key whose brand gives no step of space, or "
            "one no longer than a pixel of rounding, which covers every place it measures at "
            "that key: every pair and group of siblings, every two leaves of different groups "
            "on one page, and every two lists there whose items one component draws, each "
            "nested in as many groups that component draws as the other (DEC-063 point 2, "
            "DEC-067 point 7)",
        ),
        statements=(NEAR_ALIGNMENT_UNMEASURED,),
    ),
)

#: The check of boxes that overlap, with its reach (DEC-046 point 3, DEC-063 point 1).
BOX_OVERLAP_CHECK = SceneCheck(
    "boxes of siblings that overlap",
    id="boxes-that-overlap",
    labels=(BOX_OVERLAP, BOX_OVERLAP_MEANT),
    reach=Reach(
        measures=(
            "the boxes of each two siblings, for an overlap of more than a pixel across and "
            "down (DEC-046 point 3)",
        ),
        leaves_out=(
            "two parts of different groups, since it compares siblings alone (DEC-046 point 3)",
            *_BOTH_LEAVE_OUT,
            "two siblings one of which holds the other within a pixel (DEC-046 point 3)",
        ),
    ),
)

#: How far apart, in px of the page, two values may lie and still be one: a pixel of
#: rounding (DEC-046 point 3).
ROUNDING = 1.0

#: The places of a px the scene holds a length to, so a difference is taken to as many.
PLACES = 2

#: A shared step of space: `space.` and a number, as `space.1`.
STEP = re.compile(r"space\.[0-9]+")

#: The trace id of an entry's group: its `repeat` part's id followed by `[<id>]`, or by
#: `#<place>` (`components.md`, "Trace ids").
_ENTRY = re.compile(r"(\[[^\]]*\]|#[0-9]+)$")

#: Who each finding asks for attention (DEC-046 point 3).
REVIEWER = (
    "the reviewer, `graphic-design-reviewer`, who judges on the image whether the place is a "
    "fault or is meant"
)

#: What mends a near miss that is a fault, a spacing missed between two lists, and an
#: overlap that is one.
ALIGN_IT = (
    "where it is a fault, put the parts on one line, or a step of space apart, where its fix "
    "belongs; where it is meant, leave it"
)
SPACE_IT = (
    "where it is a fault, give the two lists one spacing, or spacings a step of space apart, "
    "where its fix belongs; where it is meant, leave it"
)
PART_IT = (
    "where it is a fault, set the parts apart, or one inside the other, where its fix belongs; "
    "where it is meant, leave it"
)

#: The two axes, each with its three lines, by name.
ACROSS = "across"
DOWN = "down"
LINES = {
    ACROSS: ("left edges", "centres", "right edges"),
    DOWN: ("tops", "middles", "bottoms"),
}

#: Where each line of an axis lies in a box, as a share of its size from its start: its
#: start, its centre and its end. A text stands its lines at one of them (`scene.STANDS`).
SHARES = (0.0, 0.5, 1.0)

#: Where a text stands its lines in its middle, so that its room lies alike on its two sides.
MIDDLE = SHARES[1]

#: The two sides of each axis on which a held part's insets lie, by name.
SIDES = {
    ACROSS: ("on the left", "on the right"),
    DOWN: ("at the top", "at the bottom"),
}

#: The name of a near miss of insets, where a near miss of lines names its line.
INSETS = "insets"


@dataclass(frozen=True)
class Step:
    """The brand's smallest step of space at one key: the shared role that gives it, and its
    length in px."""

    role: str
    value: float

    def said(self) -> str:
        return f"the brand's smallest step of space, `{self.role}`, {_px(self.value)}"


@dataclass(frozen=True)
class Box:
    """A part's box: its trace id, its type, and its place and size in px. `stands` is,
    for a text that does not fill its width, the share of its width at which it stands its
    lines (`SHARES`), its room on the side or sides it does not stand them on; None for any
    other part, which draws to every edge of its box (DEC-067 point 3). Where its part names
    siblings drawn before it under `lies-over`, `lies_over` holds their trace ids, and
    `lies_over_in` the library version that holds the part, "" where none does (DEC-066
    point 2)."""

    trace: str
    type: str
    x: float
    y: float
    width: float
    height: float
    stands: float | None = None
    lies_over: tuple[str, ...] = ()
    lies_over_in: str = ""

    def start(self, axis: str) -> float:
        return self.x if axis == ACROSS else self.y

    def size(self, axis: str) -> float:
        return self.width if axis == ACROSS else self.height

    def end(self, axis: str) -> float:
        return self.start(axis) + self.size(axis)

    def lines(self, axis: str) -> tuple[float, float, float]:
        """Its start, its centre and its end on `axis`."""
        start, size = self.start(axis), self.size(axis)
        return (start + SHARES[0] * size, start + SHARES[1] * size, start + SHARES[2] * size)

    def compared_on(self, axis: str) -> tuple[int, ...]:
        """The lines of `axis` it is compared on, by their places in `LINES`: every line,
        but across only the one a text with room stands its lines on."""
        if axis == DOWN or self.stands is None:
            return (0, 1, 2)
        return (SHARES.index(self.stands),)

    def room_before(self, axis: str) -> bool:
        """Whether its box reaches past what it draws at its start on `axis`."""
        return axis == ACROSS and self.stands is not None and self.stands > SHARES[0]

    def room_after(self, axis: str) -> bool:
        """Whether its box reaches past what it draws at its end on `axis`."""
        return axis == ACROSS and self.stands is not None and self.stands < SHARES[2]

    def shares(self, other: Box, axis: str) -> float:
        """How much of `axis` this box and `other` share: less than zero where they lie
        apart on it."""
        return min(self.end(axis), other.end(axis)) - max(self.start(axis), other.start(axis))

    def holds(self, other: Box) -> bool:
        """Whether `other` lies inside this box, within a pixel of rounding on each side."""
        return all(
            self.start(axis) - ROUNDING <= other.start(axis)
            and other.end(axis) <= self.end(axis) + ROUNDING
            for axis in LINES
        )

    def overlaps(self, other: Box) -> bool:
        """Whether this box and `other` overlap by more than a pixel of rounding each way."""
        return all(self.shares(other, axis) > ROUNDING for axis in LINES)


def smallest_step(values: Mapping[str, Any]) -> Step | None:
    """The brand's smallest step of space, of the values of roles `values` gives by token
    path: the least length in px of a shared step of space (`STEP`) longer than zero, the
    first by path where two are as long; None where it gives none."""
    found: Step | None = None
    for path in sorted(values):
        value = values[path]
        if not STEP.fullmatch(path) or not isinstance(value, Mapping):
            continue
        length = value.get("value")
        if value.get("unit") != "px" or isinstance(length, bool):
            continue
        if isinstance(length, (int, float)) and length > 0:
            if found is None or length < found.value:
                found = Step(path, float(length))
    return found


# --- the parts of a scene -----------------------------------------------------------------------


@dataclass(eq=False)
class _Part:
    """An element of a scene as the checks read it: its box in the frame of the group that
    holds it (`box`), and on its page (`placed`); the group that holds it, and its place among
    what that group holds, in drawing order; the page it lies on, where it lies on one; and,
    for a group, the parts it holds."""

    element: Mapping[str, Any]
    box: Box
    placed: Box
    holder: _Part | None
    order: int
    page: _Part | None
    parts: list[_Part] = field(default_factory=list)

    @property
    def trace(self) -> str:
        return self.box.trace

    @property
    def compared(self) -> bool:
        return _compared(self.element)

    @property
    def leaf(self) -> bool:
        """Whether it is a leaf: a part the checks compare among siblings that is no group."""
        return self.compared and self.element.get("type") != "group"

    def holders(self) -> Iterator[_Part]:
        """Each group it is nested in, the nearest first."""
        holder = self.holder
        while holder is not None:
            yield holder
            holder = holder.holder

    def below(self) -> Iterator[_Part]:
        """Each part nested in it, in the order the scene draws them."""
        for part in self.parts:
            yield part
            yield from part.below()

    def siblings(self) -> list[_Part]:
        """The parts it holds that the checks compare with each other, in drawing order."""
        return [part for part in self.parts if part.compared]


def _tree(scene: Mapping[str, Any]) -> _Part:
    """The parts of `scene`, from its root, which holds its top elements."""
    pages = {str(page) for page in scene.get("pages", [])}
    origin = Box("", "group", 0.0, 0.0, 0.0, 0.0)
    root = _Part(scene, origin, origin, None, 0, None)

    def grow(holder: _Part) -> None:
        children: Sequence[Mapping[str, Any]] = holder.element.get("children") or []
        for order, child in enumerate(children):
            box = _box(child)
            placed = replace(
                box,
                x=round(holder.placed.x + box.x, PLACES),
                y=round(holder.placed.y + box.y, PLACES),
            )
            part = _Part(child, box, placed, holder, order, holder.page)
            if part.page is None and part.trace in pages:
                part.page = part
            holder.parts.append(part)
            if child.get("type") == "group":
                grow(part)

    grow(root)
    return root


def _groups(root: _Part) -> Iterator[_Part]:
    """Each group of the scene, its root first, in drawing order."""
    yield root
    for part in root.below():
        if part.element.get("type") == "group":
            yield part


def _compared(element: Mapping[str, Any]) -> bool:
    """Whether the checks compare `element` with its siblings: it draws something that is no
    line, has an area, and is no page."""
    if element.get("page") is True:
        return False
    if float(element.get("width", 0)) <= 0 or float(element.get("height", 0)) <= 0:
        return False
    if element.get("type") == "group":
        return _draws_more_than_lines(element)
    return element.get("type") != "line"


def _draws_more_than_lines(group: Mapping[str, Any]) -> bool:
    """Whether a group draws anything but lines: an element below it that is no group and no
    line, of an area."""
    for child in group.get("children") or []:
        if child.get("type") == "group":
            if _draws_more_than_lines(child):
                return True
        elif child.get("type") != "line":
            if float(child.get("width", 0)) > 0 and float(child.get("height", 0)) > 0:
                return True
    return False


def _box(element: Mapping[str, Any]) -> Box:
    trace, kind = str(element.get("id", "")), str(element.get("type", ""))
    x, y = float(element.get("x", 0)), float(element.get("y", 0))
    width, height = float(element.get("width", 0)), float(element.get("height", 0))
    room = kind == "text" and not fills_width(element)
    at = stands(element) if room else None
    named = element.get(LIES_OVER)
    if not isinstance(named, Mapping):
        return Box(trace, kind, x, y, width, height, at)
    ids = tuple(str(each) for each in named.get(IDS) or ())
    return Box(trace, kind, x, y, width, height, at, ids, str(named.get(LIBRARY) or ""))


def _apart(first: float, second: float) -> float:
    """`second` less `first`, to the hundredth of a px the scene holds each length to."""
    return round(second - first, PLACES) + 0.0  # no negative zero


# --- edges that nearly line up ------------------------------------------------------------------


def near_alignment(scene: Mapping[str, Any], step: Step | None) -> list[Finding]:
    """Each place of `scene` where two values nearly agree and do not, each on one axis:
    edges and centres of two siblings, and the spacings between the siblings of a group;
    edges and centres of two leaves of different groups on one page, and the spacings of two
    lists there whose items one component draws, at one level (DEC-067). Where the brand
    gives no step of space, or one no longer than a pixel of rounding, nothing is near, and
    the check states so (`unmeasured`)."""
    if step is None or step.value <= ROUNDING:
        return [unmeasured(step)]
    root = _tree(scene)
    # Each group's near misses among its siblings, and the findings of its spacings.
    among: list[tuple[list[_Miss], list[Finding]]] = []
    for group in _groups(root):
        compared = group.siblings()
        if len(compared) < 2:
            continue
        misses = []
        for index, first in enumerate(compared):
            for second in compared[index + 1 :]:
                for axis in LINES:
                    miss = _miss(first, second, first.box, second.box, axis, step)
                    if miss is not None:
                        misses.append(miss)
        spaced = [
            found for axis in LINES for found in _near_gaps(group.trace, compared, axis, step)
        ]
        among.append((misses, spaced))
    every = [miss for misses, _ in among for miss in misses]
    # The pairs of leaves each finding of two siblings names, by the siblings' near miss.
    named: dict[int, list[_Pair]] = {}
    between = [
        found
        for page in _groups(root)
        if page.page is page
        for found in _between_groups(page, every, named, step)
    ]
    found = []
    for misses, spaced in among:
        found.extend(_sibling_finding(miss, named.get(id(miss)), step) for miss in misses)
        found.extend(spaced)
    return [*found, *between]


def unmeasured(step: Step | None) -> Finding:
    """The fact that the check of edges that nearly line up measured nothing at the scene's
    key, since the brand gives no step of space there, or `step`, no longer than a pixel of
    rounding (DEC-063 point 2). It covers every place the check measures at that key, and
    lies at the brand, which gives the steps. It asks no act: a brand may give no step by
    choice."""
    if step is None:
        why = "the brand gives no step of space at this key"
    else:
        why = f"{step.said()}, is no longer than a pixel of rounding"
    return Finding(
        NEAR_ALIGNMENT_UNMEASURED,
        FACT,
        f"{why}, so nothing is near: the check of edges that nearly line up measured no place "
        "at this key, no pair or group of siblings, no two parts of different groups and no "
        "two lists",
        where="brand",
    )


def _near(offset: float, step: Step) -> bool:
    return ROUNDING < abs(offset) < step.value


@dataclass(frozen=True)
class _Miss:
    """A near miss of two parts on one axis, `first` drawn first. By their lines, `near`
    holds each line of the axis on which they nearly agree, by its name, with their offset
    there, the second's value less the first's. By insets, where one lies inside the other's
    box, `insets` holds the inner part's insets on the axis's two sides, and `near` its
    offset, its inset at the start less its inset at the end (DEC-067, "The words it uses")."""

    first: _Part
    second: _Part
    axis: str
    near: tuple[tuple[str, float], ...]
    insets: tuple[float, float] | None = None
    outer: _Part | None = None
    inner: _Part | None = None

    @property
    def kind(self) -> str:
        return INSETS if self.insets is not None else "lines"

    @property
    def offset(self) -> float:
        """Its offset on the axis: the least in size of its offsets, the first in line order
        where two are as small to a hundredth of a px."""
        return min((offset for _, offset in self.near), key=lambda each: round(abs(each), 2))


def _miss(first: _Part, second: _Part, a: Box, b: Box, axis: str, step: Step) -> _Miss | None:
    """The near miss on `axis` of `first` and `second`, whose boxes `a` and `b` are taken in
    one frame: on no line of it within a pixel of rounding, of those both are compared on, and
    on one or more of them within the step. Where one holds the other, their insets are
    compared instead (`_insets_miss`)."""
    if a.holds(b) or b.holds(a):
        return _insets_miss(first, second, a, b, axis, step)
    shared = [index for index in a.compared_on(axis) if index in b.compared_on(axis)]
    if not shared:
        return None
    first_lines, second_lines = a.lines(axis), b.lines(axis)
    offsets = [(index, _apart(first_lines[index], second_lines[index])) for index in shared]
    if any(abs(offset) <= ROUNDING for _, offset in offsets):
        return None
    near = tuple((LINES[axis][index], offset) for index, offset in offsets if _near(offset, step))
    return _Miss(first, second, axis, near) if near else None


def _insets_miss(
    first: _Part, second: _Part, a: Box, b: Box, axis: str, step: Step
) -> _Miss | None:
    """The near miss on `axis` of the insets of the part one of `first` and `second` holds:
    its insets from the other's edges on the axis's two sides differ by more than a pixel of
    rounding and by less than the step. A part whose edge lies on the other's edge, within a
    pixel, lines up on it, so is not reported on that axis. Across, a text with room is
    compared by its insets only where it stands its lines in its middle."""
    (outer, outer_box), (inner, inner_box) = (
        ((first, a), (second, b)) if a.holds(b) else ((second, b), (first, a))
    )
    if axis == ACROSS and any(box.stands not in (None, MIDDLE) for box in (outer_box, inner_box)):
        return None
    insets = (
        _apart(outer_box.start(axis), inner_box.start(axis)),
        _apart(inner_box.end(axis), outer_box.end(axis)),
    )
    if min(insets) <= ROUNDING:
        return None
    offset = _apart(insets[1], insets[0])
    if not _near(offset, step):
        return None
    return _Miss(first, second, axis, ((INSETS, offset),), insets, outer, inner)


def _sibling_finding(miss: _Miss, pairs: Sequence[_Pair] | None, step: Step) -> Finding:
    """The finding of two siblings' near miss. Where one of them is a group, or both are, and
    they lie on a page, it names the pairs of leaves of different groups that show it,
    `pairs`, or says that none does (DEC-067 point 4)."""
    if miss.insets is not None:
        assert miss.outer is not None and miss.inner is not None
        said = (
            f"`{miss.outer.trace}` holds `{miss.inner.trace}` with insets {miss.axis} that "
            f"nearly agree: {_insets_said(miss)}, more than a pixel of rounding and less than "
            f"{step.said()}"
        )
    else:
        said = (
            f"`{miss.first.trace}` and `{miss.second.trace}` nearly line up {miss.axis}: "
            f"{_and([f'their {name} lie {_px(offset)} apart' for name, offset in miss.near])}, "
            f"more than a pixel of rounding and less than {step.said()}"
        )
    if pairs:
        said += (
            ". Parts of different groups that are these or lie in them show it: "
            f"{_pairs_said(pairs)}"
        )
    elif pairs is not None:
        said += (
            ". No two parts of different groups that are these or lie in them show it: it "
            "lies only at the edge of the room a group was given, where nothing is drawn"
        )
    return Finding(
        NEAR_ALIGNMENT,
        ATTENTION,
        said,
        where=miss.first.trace,
        fix=ALIGN_IT,
        who=REVIEWER,
    )


@dataclass(frozen=True)
class _Gap:
    """The gap on one axis between a part and the nearest one after it beside it."""

    before: Box
    after: Box
    length: float

    def said(self) -> str:
        return f"between `{self.before.trace}` and `{self.after.trace}`"


def _gaps(boxes: Sequence[Box], axis: str) -> list[_Gap]:
    """Each part's gap on `axis` to the nearest part after it there that stands beside it,
    sharing more than a pixel of the other axis, in the parts' order. One that overlaps it on
    `axis` by more than a pixel lies on it, not after it. A gap that starts or ends at a
    text's room is no gap a reader sees, and is not taken (DEC-067 point 3)."""
    other = DOWN if axis == ACROSS else ACROSS
    found = []
    for box in boxes:
        after = [
            each
            for each in boxes
            if each is not box
            and each.start(axis) >= box.end(axis) - ROUNDING
            and box.shares(each, other) > ROUNDING
        ]
        if after:
            nearest = min(after, key=lambda each: each.start(axis))
            if box.room_after(axis) or nearest.room_before(axis):
                continue
            found.append(_Gap(box, nearest, _apart(box.end(axis), nearest.start(axis))))
    return found


def _spacings(parts: Sequence[_Part], axis: str) -> list[list[_Gap]]:
    """The spacings of `parts` on `axis`, the least first: each the gaps no more than a pixel
    of rounding apart from the least of them."""
    spacings: list[list[_Gap]] = []
    for gap in sorted(_gaps([part.box for part in parts], axis), key=lambda each: each.length):
        if spacings and gap.length - spacings[-1][0].length <= ROUNDING:
            spacings[-1].append(gap)
        else:
            spacings.append([gap])
    return spacings


def _spacing_said(spacing: Sequence[_Gap]) -> str:
    return f"{_px(spacing[0].length)}, {_and([gap.said() for gap in spacing])}"


def _near_gaps(parent: str, parts: Sequence[_Part], axis: str, step: Step) -> Iterator[Finding]:
    """A finding for each two spacings of `parent`'s siblings on `axis` that nearly agree."""
    spacings = _spacings(parts, axis)
    for index, first in enumerate(spacings):
        for second in spacings[index + 1 :]:
            difference = _apart(first[0].length, second[0].length)
            if not _near(difference, step):
                continue
            yield Finding(
                NEAR_ALIGNMENT,
                ATTENTION,
                f"the gaps {axis} in `{parent}` nearly agree: {_spacing_said(first)}; and "
                f"{_spacing_said(second)}: {_px(difference)} apart, more than a pixel of "
                f"rounding and less than {step.said()}",
                where=parent,
                fix=ALIGN_IT,
                who=REVIEWER,
            )


# --- between groups -----------------------------------------------------------------------------


@dataclass(frozen=True)
class _Pair:
    """A near miss of two leaves of different groups on one axis, `miss`, the leaf at the
    first side first; the two sides; and where the scene draws the pair, by the places of its
    two leaves among the page's leaves, the one drawn first first."""

    miss: _Miss
    sides: tuple[_Part, _Part]
    drawn: tuple[int, int]

    @property
    def key(self) -> tuple[int, int, str, str]:
        """The two sides, the axis and the way of comparing, which one finding shares."""
        return (id(self.sides[0]), id(self.sides[1]), self.miss.axis, self.miss.kind)


@dataclass(frozen=True)
class _Lists:
    """Two lists on one page whose items one component, `drawn_by`, draws, at one level, the
    one drawn first first, with each pair of their spacings that nearly agree, by its axis."""

    first: _Part
    second: _Part
    drawn_by: str
    spacings: tuple[tuple[str, tuple[_Gap, ...], tuple[_Gap, ...]], ...]

    @property
    def axes(self) -> set[str]:
        return {axis for axis, _, _ in self.spacings}


def _between_groups(
    page: _Part, misses: Sequence[_Miss], named: dict[int, list[_Pair]], step: Step
) -> list[Finding]:
    """The findings of `page` between groups (DEC-067 points 4 and 5): each pair of leaves of
    different groups that nearly agree is named once, in the finding of its two sides as
    siblings among `misses`, which `named` keeps by the miss, in the finding of two lists
    whose gaps explain it, or in a finding of its own, one for each offset between two
    sides."""
    lists = _near_lists(page, step)
    explained: list[list[_Pair]] = [[] for _ in lists]
    among = {(id(miss.first), id(miss.second), miss.axis, miss.kind): miss for miss in misses}
    by_key: dict[tuple[int, int, str, str], list[_Pair]] = {}
    for pair in _pairs(page, step):
        by_key.setdefault(pair.key, []).append(pair)
    own: list[list[_Pair]] = []
    for key, pairs in by_key.items():
        sibling = among.get(key)
        rest = []
        for pair in pairs:
            if sibling is not None and _shows(pair.miss.near, sibling.near, same_line=True):
                named.setdefault(id(sibling), []).append(pair)
                continue
            found = next((n for n, each in enumerate(lists) if _explains(each, pair)), None)
            if found is not None:
                explained[found].append(pair)
                continue
            rest.append(pair)
        own.extend(_placed(rest))
    for miss in misses:
        if miss.first.page is page and _in_a_group(miss):
            named.setdefault(id(miss), [])
    return [
        *(_lists_finding(each, pairs, step) for each, pairs in zip(lists, explained, strict=True)),
        *(_own_finding(pairs, step) for pairs in own),
    ]


def _in_a_group(miss: _Miss) -> bool:
    """Whether one of the two siblings of `miss` is a group, so that leaves nested in it may
    show its near miss."""
    return any(part.element.get("type") == "group" for part in (miss.first, miss.second))


def _shows(
    near: Sequence[tuple[str, float]], offsets: Sequence[tuple[str, float]], *, same_line: bool
) -> bool:
    """Whether one of the offsets `near` gives lies within a pixel of rounding of one of
    `offsets`, on the same line where `same_line`, else on whichever line."""
    return any(
        (not same_line or name == other) and abs(_apart(offset, value)) <= ROUNDING
        for name, value in near
        for other, offset in offsets
    )


def _placed(pairs: Sequence[_Pair]) -> list[list[_Pair]]:
    """The findings of their own of the pairs of two sides, axis and way of comparing that
    no other finding names (DEC-067 point 4): placed those of fewest near lines first, and
    among those by the size of their offset on the axis, the least first, in drawing order
    where two are as small to a hundredth of a px. Each joins the first finding whose first
    pair has an offset within a pixel of one of its own, on whichever line, or starts one."""
    order = sorted(pairs, key=lambda p: (len(p.miss.near), round(abs(p.miss.offset), 2), p.drawn))
    findings: list[list[_Pair]] = []
    for pair in order:
        for found in findings:
            if _shows(pair.miss.near, found[0].miss.near, same_line=False):
                found.append(pair)
                break
        else:
            findings.append([pair])
    return findings


def _pairs(page: _Part, step: Step) -> list[_Pair]:
    """Each near miss of two leaves of different groups on `page`, neither a tie's part, in
    the order the scene draws them (DEC-067 point 1)."""
    ties = _tie_groups(page)
    leaves = [
        part
        for part in page.below()
        if part.leaf and not any(id(holder) in ties for holder in part.holders())
    ]
    found: list[_Pair] = []
    for axis in LINES:
        for one, other in sorted(_candidates(leaves, axis, step)):
            a, b = leaves[one], leaves[other]
            if a.holder is b.holder:
                continue
            sides = _sides(a, b)
            first, second = (a, b) if _is_at(a, sides[0]) else (b, a)
            miss = _miss(first, second, first.placed, second.placed, axis, step)
            if miss is not None:
                found.append(_Pair(miss, sides, (one, other)))
    return sorted(found, key=lambda pair: (pair.drawn, pair.miss.axis != ACROSS))


def _candidates(leaves: Sequence[_Part], axis: str, step: Step) -> set[tuple[int, int]]:
    """The pairs of `leaves`, by their places, whose values on a line of `axis` lie within a
    step of each other: the only pairs that may nearly agree on that axis, by their lines or
    by their insets, which differ by twice as much as their centres do."""
    found: set[tuple[int, int]] = set()
    for index in range(len(SHARES)):
        values = sorted((leaf.placed.lines(axis)[index], n) for n, leaf in enumerate(leaves))
        for at, (value, one) in enumerate(values):
            for later, other in values[at + 1 :]:
                if _apart(value, later) > step.value:
                    break
                found.add((min(one, other), max(one, other)))
    return found


def _tie_groups(page: _Part) -> set[int]:
    """The groups on `page` that a tie's component draws: for each connector, a line the
    scene marks with `attached`, the nearest group below the page that it is nested in whose
    trace id is an entry's (`_ENTRY`, DEC-067 point 1)."""
    found: set[int] = set()
    for part in page.below():
        if part.element.get("type") != "line" or not part.element.get("attached"):
            continue
        for holder in part.holders():
            if holder is page:
                break
            if _ENTRY.search(holder.trace):
                found.add(id(holder))
                break
    return found


def _sides(a: _Part, b: _Part) -> tuple[_Part, _Part]:
    """The sides of `a` and `b`: the two parts the nearest group both are nested in holds,
    that the two are or are nested in, the one it holds first first."""
    chain = [a, *a.holders()]
    places = {id(part): index for index, part in enumerate(chain)}
    previous = b
    for holder in b.holders():
        if id(holder) in places:
            side = chain[places[id(holder)] - 1]
            return (side, previous) if side.order < previous.order else (previous, side)
        previous = holder
    raise ValueError(f"`{a.trace}` and `{b.trace}` lie in no one group")


def _is_at(part: _Part, side: _Part) -> bool:
    """Whether `part` is `side` or is nested in it."""
    return part is side or any(holder is side for holder in part.holders())


def _own_finding(pairs: Sequence[_Pair], step: Step) -> Finding:
    """The finding of one offset between two sides, naming each pair of leaves that shows it
    (DEC-067 point 4)."""
    first_side, second_side = pairs[0].sides
    axis = pairs[0].miss.axis
    return Finding(
        NEAR_ALIGNMENT_BETWEEN_GROUPS,
        ATTENTION,
        f"at `{first_side.trace}` and `{second_side.trace}`, parts of different groups nearly "
        f"line up {axis}, by more than a pixel of rounding and less than {step.said()}: "
        f"{_pairs_said(pairs)}",
        where=first_side.trace,
        fix=ALIGN_IT,
        who=REVIEWER,
    )


def _pairs_said(pairs: Sequence[_Pair]) -> str:
    """The pairs of leaves a finding names, in words, one after the other."""
    return "; ".join(_pair_said(pair.miss) for pair in pairs)


def _pair_said(miss: _Miss) -> str:
    """A pair of leaves and each line or inset on which it nearly agrees, in words."""
    if miss.insets is not None:
        assert miss.outer is not None and miss.inner is not None
        return (
            f"`{miss.outer.trace}` holds `{miss.inner.trace}` with insets {miss.axis} of "
            f"{_insets_said(miss)}"
        )
    lines = _and([f"{name} {_px(offset)} apart" for name, offset in miss.near])
    return f"`{miss.first.trace}` and `{miss.second.trace}`, their {lines}"


def _insets_said(miss: _Miss) -> str:
    assert miss.insets is not None
    sides = SIDES[miss.axis]
    said = [f"{_px(inset)} {side}" for side, inset in zip(sides, miss.insets, strict=True)]
    return f"{_and(said)}, {_px(miss.offset)} apart"


# --- two lists ----------------------------------------------------------------------------------


def _drawn_by(group: _Part) -> str | None:
    """The component that draws each item of `group`, where it is a list: its compared parts
    are two or more groups whose field `component` names one component. None where it is no
    list."""
    items = group.siblings()
    if len(items) < 2 or any(item.element.get("type") != "group" for item in items):
        return None
    components = {str(item.element.get("component") or "") for item in items}
    if len(components) != 1 or "" in components:
        return None
    return components.pop()


def _level(group: _Part, drawn_by: str) -> int:
    """How many groups `group` is nested in whose field `component` names `drawn_by`, the
    component that draws its items, whether or not each is an item (DEC-067 point 5)."""
    return sum(1 for holder in group.holders() if holder.element.get("component") == drawn_by)


def _near_lists(page: _Part, step: Step) -> list[_Lists]:
    """Each two lists on `page` whose items one component draws, at one level, whose
    spacings on one axis nearly agree, unless one of the two lists has a spacing within a
    pixel of each, the one drawn first first (DEC-067 point 5)."""
    lists = []
    for part in page.below():
        if part.element.get("type") == "group":
            drawn_by = _drawn_by(part)
            if drawn_by is not None:
                lists.append((part, drawn_by, _level(part, drawn_by)))
    found = []
    for index, (first, drawn_by, level) in enumerate(lists):
        for second, other_by, other_level in lists[index + 1 :]:
            if other_by != drawn_by or other_level != level:
                continue
            near = []
            for axis in LINES:
                own, others = _spacings(first.siblings(), axis), _spacings(second.siblings(), axis)
                for one in own:
                    for other in others:
                        if not _near(_apart(one[0].length, other[0].length), step):
                            continue
                        if _has(own, other) or _has(others, one):
                            continue
                        near.append((axis, tuple(one), tuple(other)))
            if near:
                found.append(_Lists(first, second, drawn_by, tuple(near)))
    return found


def _has(spacings: Sequence[Sequence[_Gap]], spacing: Sequence[_Gap]) -> bool:
    """Whether one of `spacings` lies within a pixel of rounding of `spacing`."""
    return any(abs(_apart(each[0].length, spacing[0].length)) <= ROUNDING for each in spacings)


def _explains(lists: _Lists, pair: _Pair) -> bool:
    """Whether the gaps of `lists` explain `pair`'s near miss (DEC-067 point 5): it compares
    lines on an axis of a pair of spacings the lists name, its two leaves are nested one in an
    item of each list, and its offset on one of its near lines lies within a pixel of the
    length of gaps before its item at the second side less that before its item at the
    first."""
    miss = pair.miss
    if miss.insets is not None or miss.axis not in lists.axes:
        return False
    for at_first, at_second in ((lists.first, lists.second), (lists.second, lists.first)):
        first, second = _item_of(miss.first, at_first), _item_of(miss.second, at_second)
        if first is None or second is None:
            continue
        drift = _apart(_gaps_before(first, miss.axis), _gaps_before(second, miss.axis))
        if any(abs(_apart(drift, offset)) <= ROUNDING for _, offset in miss.near):
            return True
    return False


def _item_of(part: _Part, group: _Part) -> _Part | None:
    """The part `group` holds that `part` is nested in, if any."""
    below = part
    for holder in part.holders():
        if holder is group:
            return below
        below = holder
    return None


def _gaps_before(item: _Part, axis: str) -> float:
    """The length of gaps before `item` on `axis`: from the first of its list's items to its
    start, the length no item of its list covers."""
    assert item.holder is not None
    items = [each.box for each in item.holder.siblings()]
    first = min(each.start(axis) for each in items)
    upto = item.box.start(axis)
    spans = sorted(
        (max(each.start(axis), first), min(each.end(axis), upto))
        for each in items
        if each.start(axis) < upto
    )
    covered, reach = 0.0, first
    for start, end in spans:
        if end <= reach:
            continue
        covered += end - max(start, reach)
        reach = end
    return _apart(covered, upto - first)


def _lists_finding(lists: _Lists, pairs: Sequence[_Pair], step: Step) -> Finding:
    """The finding of two lists' spacings that nearly agree, naming each pair of their
    spacings and each pair of leaves their gaps explain (DEC-067 point 5)."""
    said = [
        f"{axis}, {_spacing_said(one)} in `{lists.first.trace}`, and {_spacing_said(other)} in "
        f"`{lists.second.trace}`, {_px(abs(_apart(one[0].length, other[0].length)))} apart"
        for axis, one, other in lists.spacings
    ]
    message = (
        f"the spacings of the lists `{lists.first.trace}` and `{lists.second.trace}`, whose "
        f"items `{lists.drawn_by}` draws, nearly agree, by more than a pixel of rounding and "
        f"less than {step.said()}: {'; and '.join(said)}"
    )
    if pairs:
        message += f". The parts their gaps set off their match: {_pairs_said(pairs)}"
    return Finding(
        NEAR_ALIGNMENT_BETWEEN_GROUPS,
        ATTENTION,
        message,
        where=lists.first.trace,
        fix=SPACE_IT,
        who=REVIEWER,
    )


# --- boxes that overlap -------------------------------------------------------------------------


def overlaps(scene: Mapping[str, Any]) -> list[Finding]:
    """Each two siblings of `scene` whose boxes overlap by more than a pixel of rounding each
    way, where neither holds the other. Where the one drawn over names the other under
    `lies-over`, the finding carries the library version that holds that word, and reads as
    any other until it is read (`meant`)."""
    found = []
    for group in _groups(_tree(scene)):
        compared = [part.box for part in group.siblings()]
        for index, under in enumerate(compared):
            for over in compared[index + 1 :]:
                if not under.overlaps(over) or under.holds(over) or over.holds(under):
                    continue
                across, down = under.shares(over, ACROSS), under.shares(over, DOWN)
                found.append(
                    Finding(
                        BOX_OVERLAP,
                        ATTENTION,
                        f"the boxes of `{under.trace}` and `{over.trace}` overlap by "
                        f"{_px(across)} across and {_px(down)} down, and neither holds the "
                        f"other: `{over.trace}` is drawn over `{under.trace}`",
                        where=under.trace,
                        fix=PART_IT,
                        who=REVIEWER,
                        lies_over_in=over.lies_over_in if under.trace in over.lies_over else "",
                    )
                )
    return found


def meant(finding: Finding) -> Finding:
    """An overlap's finding as validation reads it where the library version that holds its
    word, `lies_over_in`, is released and still as it was released (DEC-066 point 2): the
    fact `box-overlap-meant`, which asks no act, so names no one and no fix. Its message is
    the overlap's, and says that the part on top names the part beneath under `lies-over`."""
    return replace(
        finding,
        code=BOX_OVERLAP_MEANT,
        level=FACT,
        message=f"{finding.message}; the part on top names the one beneath under `lies-over` "
        f"in {finding.lies_over_in}, released, which says the overlap is meant",
        fix="",
        who="",
    )


def _px(length: float) -> str:
    return f"{round(abs(length), 2):g} px"


def _and(said: Sequence[str]) -> str:
    """`said` joined as a list in words."""
    if len(said) < 3:
        return " and ".join(said)
    return f"{', '.join(said[:-1])} and {said[-1]}"
