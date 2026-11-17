"""The checks of boxes (visual-communication DEC-046 point 3): edges that nearly line up, and
boxes that overlap, among the siblings of each scene.

Each check does the arithmetic and judges nothing. Each finding asks the reviewer for
attention, who judges on the image whether the place it names is a fault or is meant, and
none fails (DEC-002 point 7, DEC-030 point 7): a component may place one part on another on
purpose, and a box may differ from what is drawn in it.

- **The boxes read** are the scene's: each element's frame, in px of its page, relative to
  its parent (`components.md`, "What a scene holds"). The frames the viewing step writes
  beside an image are those boxes scaled into the image's pixels, so a check that read them
  would judge a pixel of rounding and the brand's step of space in another unit than the
  scene's.
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
- **A part another holds.** Where one of a pair holds the other, as a card's box holds its
  head, the held part's insets on the two sides of each axis are compared, not their centres:
  its left and right insets across, its top and bottom down. A part that lies on one edge of
  the other within a pixel lines up on it, so is not reported on that axis.
- **Gaps.** On each axis, each sibling's gap to the nearest sibling after it that stands
  beside it, sharing more than a pixel of its height across or of its width down. Gaps no
  more than a pixel apart are one spacing. One finding names two spacings of one group and
  axis that nearly agree, with the gaps of each.

`overlaps` reports two siblings whose boxes overlap by more than a pixel each way, where
neither holds the other, a text a sibling covers among them.

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
from dataclasses import dataclass
from typing import Any

from _lib.findings import ATTENTION, FACT, Finding
from _lib.scene_checks import Reach, SceneCheck

#: The calls for attention of the two checks of boxes.
NEAR_ALIGNMENT = "near-alignment"
BOX_OVERLAP = "box-overlap"

#: The fact the check of edges that nearly line up states at a key where it could measure
#: nothing (DEC-063 point 2).
NEAR_ALIGNMENT_UNMEASURED = "near-alignment-unmeasured"

#: What each check of boxes leaves out, by the base they share (DEC-046 point 3).
_BOTH_LEAVE_OUT = (
    "two parts of different groups, since it compares siblings alone (DEC-046 point 3)",
    "a line, and a group below which every element but a group is a line or of no area, "
    "such as a tie's (DEC-046 point 3)",
    "an element of no area (DEC-046 point 3)",
    "a page (DEC-046 point 3)",
)

#: The check of edges that nearly line up, with its reach (DEC-046 point 3, DEC-063 points 1
#: and 2).
NEAR_ALIGNMENT_CHECK = SceneCheck(
    "edges and centres of siblings that nearly line up, and spacings that nearly agree",
    id="edges-nearly-in-line",
    labels=(NEAR_ALIGNMENT, NEAR_ALIGNMENT_UNMEASURED),
    reach=Reach(
        measures=(
            "the left edges, centres and right edges, and the tops, middles and bottoms, of "
            "each two siblings neither of which holds the other within a pixel "
            "(DEC-046 point 3)",
            "the insets on the two sides of each axis of a part inside a sibling's box "
            "(DEC-046 point 3)",
            "the spacings of one group's siblings on each axis, each gap taken from a sibling "
            "to the nearest one after it that stands beside it (DEC-046 point 3)",
        ),
        leaves_out=(
            *_BOTH_LEAVE_OUT,
            "the other lines of an axis on which a pair lines up on one line within a pixel "
            "(DEC-046 point 3)",
            "the edges and centres of two siblings one of which holds the other within a "
            "pixel, whose insets it measures instead (DEC-046 point 3)",
            "the insets on an axis of a part inside a sibling's box that lies within a pixel "
            "of one of that box's edges on that axis (DEC-046 point 3)",
            "the gap between two siblings that share no more than a pixel of the other axis "
            "(DEC-063 point 1)",
        ),
        states=(
            f"`{NEAR_ALIGNMENT_UNMEASURED}`, at a key whose brand gives no step of space, or "
            "one no longer than a pixel of rounding, which covers every pair and group of "
            "siblings at that key (DEC-063 point 2)",
        ),
        statements=(NEAR_ALIGNMENT_UNMEASURED,),
    ),
)

#: The check of boxes that overlap, with its reach (DEC-046 point 3, DEC-063 point 1).
BOX_OVERLAP_CHECK = SceneCheck(
    "boxes of siblings that overlap",
    id="boxes-that-overlap",
    labels=(BOX_OVERLAP,),
    reach=Reach(
        measures=(
            "the boxes of each two siblings, for an overlap of more than a pixel across and "
            "down (DEC-046 point 3)",
        ),
        leaves_out=(
            *_BOTH_LEAVE_OUT,
            "two siblings one of which holds the other within a pixel (DEC-046 point 3)",
        ),
    ),
)

#: How far apart, in px of the page, two values may lie and still be one: a pixel of
#: rounding (DEC-046 point 3).
ROUNDING = 1.0

#: A shared step of space: `space.` and a number, as `space.1`.
STEP = re.compile(r"space\.[0-9]+")

#: Who each finding asks for attention (DEC-046 point 3).
REVIEWER = (
    "the reviewer, `graphic-design-reviewer`, who judges on the image whether the place is a "
    "fault or is meant"
)

#: What mends a near miss that is a fault, and an overlap that is one.
ALIGN_IT = (
    "where it is a fault, put the parts on one line, or a step of space apart, where its fix "
    "belongs; where it is meant, leave it"
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

#: The two sides of each axis on which a held part's insets lie, by name.
SIDES = {
    ACROSS: ("on the left", "on the right"),
    DOWN: ("at the top", "at the bottom"),
}


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
    """A sibling's box, in the frame of the group that holds it: its trace id, its type, and
    its place and size in px."""

    trace: str
    type: str
    x: float
    y: float
    width: float
    height: float

    def start(self, axis: str) -> float:
        return self.x if axis == ACROSS else self.y

    def size(self, axis: str) -> float:
        return self.width if axis == ACROSS else self.height

    def end(self, axis: str) -> float:
        return self.start(axis) + self.size(axis)

    def lines(self, axis: str) -> tuple[float, float, float]:
        """Its start, its centre and its end on `axis`."""
        start, size = self.start(axis), self.size(axis)
        return (start, start + size / 2, start + size)

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


def siblings(scene: Mapping[str, Any]) -> Iterator[tuple[str, list[Box]]]:
    """Each group of `scene` with the boxes of the siblings it holds that the checks compare,
    in drawing order: the group's trace id, and their boxes. A group with fewer than two is
    passed over."""

    def walk(group: Mapping[str, Any]) -> Iterator[tuple[str, list[Box]]]:
        children: Sequence[Mapping[str, Any]] = group.get("children") or []
        compared = [_box(child) for child in children if _compared(child)]
        if len(compared) > 1:
            yield str(group.get("id", "")), compared
        for child in children:
            if child.get("type") == "group":
                yield from walk(child)

    return walk(scene)


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
    return Box(trace, kind, x, y, width, height)


# --- edges that nearly line up ------------------------------------------------------------------


def near_alignment(scene: Mapping[str, Any], step: Step | None) -> list[Finding]:
    """Each place among the siblings of `scene` where two values nearly agree and do not:
    edges and centres of a pair, and the spacings between the siblings of a group, each on one
    axis. Where the brand gives no step of space, or one no longer than a pixel of rounding,
    nothing is near, and the check states so (`unmeasured`)."""
    if step is None or step.value <= ROUNDING:
        return [unmeasured(step)]
    found = []
    for parent, boxes in siblings(scene):
        for index, first in enumerate(boxes):
            for second in boxes[index + 1 :]:
                found.extend(_near_lines(first, second, step))
        for axis in LINES:
            found.extend(_near_gaps(parent, boxes, axis, step))
    return found


def unmeasured(step: Step | None) -> Finding:
    """The fact that the check of edges that nearly line up measured nothing at the scene's
    key, since the brand gives no step of space there, or `step`, no longer than a pixel of
    rounding (DEC-063 point 2). It covers every pair and group of siblings at that key, and
    lies at the brand, which gives the steps. It asks no act: a brand may give no step by
    choice."""
    if step is None:
        why = "the brand gives no step of space at this key"
    else:
        why = f"{step.said()}, is no longer than a pixel of rounding"
    return Finding(
        NEAR_ALIGNMENT_UNMEASURED,
        FACT,
        f"{why}, so nothing is near: the check of edges that nearly line up measured no pair "
        "or group of siblings at this key",
        where="brand",
    )


def _near(difference: float, step: Step) -> bool:
    return ROUNDING < difference < step.value


def _near_lines(first: Box, second: Box, step: Step) -> Iterator[Finding]:
    """A finding for each axis on which `first` and `second` nearly line up: on no line of it
    within a pixel of rounding, and on one or more of its lines within the step. Where one
    holds the other, their insets are compared instead (`_near_insets`)."""
    if first.holds(second) or second.holds(first):
        yield from _near_insets(first, second, step)
        return
    for axis, names in LINES.items():
        apart = [abs(a - b) for a, b in zip(first.lines(axis), second.lines(axis), strict=True)]
        if any(difference <= ROUNDING for difference in apart):
            continue
        near = [(name, d) for name, d in zip(names, apart, strict=True) if _near(d, step)]
        if not near:
            continue
        said = [f"their {name} lie {_px(d)} apart" for name, d in near]
        yield Finding(
            NEAR_ALIGNMENT,
            ATTENTION,
            f"`{first.trace}` and `{second.trace}` nearly line up {axis}: {_and(said)}, more "
            f"than a pixel of rounding and less than {step.said()}",
            where=first.trace,
            fix=ALIGN_IT,
            who=REVIEWER,
        )


def _near_insets(first: Box, second: Box, step: Step) -> Iterator[Finding]:
    """A finding for each axis on which the part one of `first` and `second` holds has insets
    that nearly agree: its insets from the other's edges on the axis's two sides differ by
    more than a pixel of rounding and by less than the step. A part whose edge lies on the
    other's edge, within a pixel, lines up on it, so is not reported on that axis."""
    outer, inner = (first, second) if first.holds(second) else (second, first)
    for axis, sides in SIDES.items():
        insets = (inner.start(axis) - outer.start(axis), outer.end(axis) - inner.end(axis))
        if min(insets) <= ROUNDING:
            continue
        difference = abs(insets[0] - insets[1])
        if not _near(difference, step):
            continue
        said = [f"{_px(inset)} {side}" for side, inset in zip(sides, insets, strict=True)]
        yield Finding(
            NEAR_ALIGNMENT,
            ATTENTION,
            f"`{outer.trace}` holds `{inner.trace}` with insets {axis} that nearly agree: "
            f"{_and(said)}, {_px(difference)} apart, more than a pixel of rounding and less "
            f"than {step.said()}",
            where=first.trace,
            fix=ALIGN_IT,
            who=REVIEWER,
        )


@dataclass(frozen=True)
class _Gap:
    """The gap on one axis between a sibling and the nearest one after it beside it."""

    before: Box
    after: Box
    length: float

    def said(self) -> str:
        return f"between `{self.before.trace}` and `{self.after.trace}`"


def _gaps(boxes: Sequence[Box], axis: str) -> list[_Gap]:
    """Each sibling's gap on `axis` to the nearest sibling after it there that stands beside
    it, sharing more than a pixel of the other axis, in the siblings' order. One that overlaps
    it on `axis` by more than a pixel lies on it, not after it."""
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
            found.append(_Gap(box, nearest, nearest.start(axis) - box.end(axis)))
    return found


def _near_gaps(parent: str, boxes: Sequence[Box], axis: str, step: Step) -> Iterator[Finding]:
    """A finding for each two spacings of `parent`'s siblings on `axis` that nearly agree. A
    spacing is the gaps no more than a pixel of rounding apart from the least of them."""
    spacings: list[list[_Gap]] = []
    for gap in sorted(_gaps(boxes, axis), key=lambda each: each.length):
        if spacings and gap.length - spacings[-1][0].length <= ROUNDING:
            spacings[-1].append(gap)
        else:
            spacings.append([gap])
    for index, first in enumerate(spacings):
        for second in spacings[index + 1 :]:
            difference = second[0].length - first[0].length
            if not _near(difference, step):
                continue
            pair = (first, second)
            said = [f"{_px(each[0].length)}, {_and([g.said() for g in each])}" for each in pair]
            yield Finding(
                NEAR_ALIGNMENT,
                ATTENTION,
                f"the gaps {axis} in `{parent}` nearly agree: {said[0]}; and {said[1]}: "
                f"{_px(difference)} apart, more than a pixel of rounding and less than "
                f"{step.said()}",
                where=parent,
                fix=ALIGN_IT,
                who=REVIEWER,
            )


# --- boxes that overlap -------------------------------------------------------------------------


def overlaps(scene: Mapping[str, Any]) -> list[Finding]:
    """Each two siblings of `scene` whose boxes overlap by more than a pixel of rounding each
    way, where neither holds the other."""
    found = []
    for _, boxes in siblings(scene):
        for index, under in enumerate(boxes):
            for over in boxes[index + 1 :]:
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
                    )
                )
    return found


def _px(length: float) -> str:
    return f"{round(length, 2):g} px"


def _and(said: Sequence[str]) -> str:
    """`said` joined as a list in words."""
    if len(said) < 3:
        return " and ".join(said)
    return f"{', '.join(said[:-1])} and {said[-1]}"
