"""Outlines: the form of a concept's sign, one outline in SVG's path data within a square
(visual-communication DEC-036 point 1).

An *outline* is `{d: <path data>, fill-rule: nonzero | evenodd, square: <side>}`: its path
in SVG's path data, the rule that fills it, and the side of the square its numbers lie
within. Its numbers are lengths within that square, so no brand gives it a value. The
foundations declare each shape as one, by its name, and a notation holds each concept's
icon as one.

`read_outline` reads one, or says why it cannot. It reads the path's data whole, every
command of SVG's path data, absolute or relative, and holds it as the absolute moves,
lines, cubic curves and closes it draws: a quadratic curve becomes the cubic it is, and an
arc the cubics that draw it, at most a quarter turn each. `Outline.mapped` fits it into a
frame by its square, whole, centred and as large as the frame allows (DEC-025 point 6), as
the path the scene holds, in the scene's one unit. Whether an outline closes and lies within
its square is the checks' to judge, not the reader's.

Knows nothing of files, notations, the foundations or the scene.
"""

from __future__ import annotations

import math
import re
from collections.abc import Mapping
from dataclasses import dataclass

from _lib import formula as fm

#: The rules that fill an outline, as SVG names them.
FILL_RULES = ("nonzero", "evenodd")

#: The keys of an outline, each required.
KEYS = frozenset({"d", "fill-rule", "square"})

#: A mapped path's numbers are rounded to this many decimal places, as the scene's lengths.
PLACES = 2

#: One segment of an outline: `M` or `L` with its point, `C` with its two control points
#: and its end, or `Z` with none, every point absolute within the outline's square.
Segment = tuple[str, tuple[float, ...]]


@dataclass(frozen=True)
class Outline:
    """One outline, read: its segments, the rule that fills it and its square's side."""

    segments: tuple[Segment, ...]
    fill_rule: str
    square: float

    def mapped(self, x: float, y: float, width: float, height: float) -> str:
        """The outline as SVG path data in the frame `x y width height`: scaled by its
        square to the frame's lesser side and centred in it."""
        scale = min(width, height) / self.square
        left = x + (width - self.square * scale) / 2
        top = y + (height - self.square * scale) / 2
        words: list[str] = []
        for command, points in self.segments:
            words.append(command)
            for index, value in enumerate(points):
                words.append(_number(value * scale + (top if index % 2 else left)))
        return " ".join(words)


def read_outline(raw: object) -> Outline | str:
    """The outline `raw` gives, or why it gives none: `raw` is a mapping of `d`, path data
    SVG reads, `fill-rule`, one of `FILL_RULES`, and `square`, a positive number."""
    if not isinstance(raw, Mapping) or set(raw) != KEYS:
        return "is not `{d: <path data>, fill-rule: nonzero | evenodd, square: <side>}`"
    fill_rule, square, data = raw["fill-rule"], raw["square"], raw["d"]
    if fill_rule not in FILL_RULES:
        return f"has the fill rule `{fill_rule}`, which is neither `nonzero` nor `evenodd`"
    if isinstance(square, bool) or not isinstance(square, int | float) or not square > 0:
        return f"has the square `{square}`, which is no positive number"
    if not isinstance(data, str):
        return "has a `d` that is no text of path data"
    try:
        segments = _segments(data)
    except _Unreadable as exc:
        return f"has a `d` that is no path data SVG reads: {exc}"
    return Outline(segments=segments, fill_rule=fill_rule, square=float(square))


def _number(value: float) -> str:
    """A number as a mapped path holds it: rounded as the scene's lengths are, with no
    trailing zero and no negative zero."""
    rounded = fm.rounded(value, PLACES) + 0.0
    if rounded == int(rounded):
        return str(int(rounded))
    return f"{rounded:.{PLACES}f}".rstrip("0")


# --- reading path data --------------------------------------------------------------------------


class _Unreadable(Exception):
    """Path data SVG does not read; the message says where."""


#: How many numbers each command takes, by its absolute letter.
_ARGUMENTS = {"M": 2, "L": 2, "H": 1, "V": 1, "C": 6, "S": 4, "Q": 4, "T": 2, "A": 7, "Z": 0}

#: An arc's two flags, by their place among its numbers.
_FLAGS = (3, 4)

_SPACE = " \t\r\n\f"

_NUMBER = re.compile(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?")


class _Data:
    """Path data, read from its start."""

    def __init__(self, text: str) -> None:
        self.text = text
        self.at = 0

    def space(self) -> None:
        while self.at < len(self.text) and self.text[self.at] in _SPACE:
            self.at += 1

    def separator(self) -> None:
        """Spaces, with at most one comma among them."""
        self.space()
        if self.at < len(self.text) and self.text[self.at] == ",":
            self.at += 1
            self.space()

    def done(self) -> bool:
        return self.at >= len(self.text)

    def command(self) -> str:
        """The command at this place, read; raises where there is none."""
        if self.done() or self.text[self.at].upper() not in _ARGUMENTS:
            raise _Unreadable(f"no command at character {self.at + 1}")
        self.at += 1
        return self.text[self.at - 1]

    def more(self) -> bool:
        """Whether the command read last repeats: a comma or a number follows."""
        self.space()
        return not self.done() and (
            self.text[self.at] == "," or _NUMBER.match(self.text, self.at) is not None
        )

    def number(self) -> float:
        found = _NUMBER.match(self.text, self.at)
        if found is None:
            raise _Unreadable(f"no number at character {self.at + 1}")
        self.at = found.end()
        return float(found.group())

    def flag(self) -> float:
        if self.done() or self.text[self.at] not in "01":
            raise _Unreadable(f"no flag, 0 or 1, at character {self.at + 1}")
        self.at += 1
        return float(self.text[self.at - 1])

    def arguments(self, command: str, first: bool) -> list[float]:
        """The numbers of one use of `command`, absolute letter; `first` where they follow
        its letter, which no comma may."""
        values: list[float] = []
        for index in range(_ARGUMENTS[command]):
            if index or not first:
                self.separator()
            else:
                self.space()
            flag = command == "A" and index in _FLAGS
            values.append(self.flag() if flag else self.number())
        return values


def _segments(text: str) -> tuple[Segment, ...]:
    """The segments `text` draws, as absolute moves, lines, cubic curves and closes."""
    data = _Data(text)
    data.space()
    if data.done():
        raise _Unreadable("it is empty")
    out: list[Segment] = []
    x = y = start_x = start_y = 0.0
    control: tuple[float, float] | None = None  # a curve's last control point, to reflect
    quadratic: tuple[float, float] | None = None
    closed = False
    letter = data.command()
    if letter not in "Mm":
        raise _Unreadable("it does not start with a move, `M` or `m`")
    while True:
        command, relative = letter.upper(), letter.islower()
        if command == "Z":
            out.append(("Z", ()))
            x, y, closed = start_x, start_y, True
            control = quadratic = None
        else:
            first = True
            while first or data.more():
                values = data.arguments(command, first)
                first = False
                if closed and command != "M":
                    out.append(("M", (x, y)))
                closed = False
                if relative:
                    values = _absolute(command, values, x, y)
                drawn, control, quadratic = _drawn(command, values, x, y, control, quadratic)
                if command == "M":
                    start_x, start_y = values
                    command = "L"  # a move's further points are lines
                out.extend(drawn)
                x, y = _end(drawn, x, y)
        data.space()
        if data.done():
            return tuple(out)
        letter = data.command()


def _absolute(command: str, values: list[float], x: float, y: float) -> list[float]:
    """The numbers of one use of a relative `command`, absolute letter, made absolute from
    the current point `x y`."""
    if command == "H":
        return [values[0] + x]
    if command == "V":
        return [values[0] + y]
    if command == "A":
        return [*values[:5], values[5] + x, values[6] + y]
    return [value + (y if index % 2 else x) for index, value in enumerate(values)]


def _end(drawn: list[Segment], x: float, y: float) -> tuple[float, float]:
    """Where the segments `drawn` leave the current point, from `x y`."""
    if not drawn:
        return x, y
    points = drawn[-1][1]
    return points[-2], points[-1]


def _drawn(
    command: str,
    values: list[float],
    x: float,
    y: float,
    control: tuple[float, float] | None,
    quadratic: tuple[float, float] | None,
) -> tuple[list[Segment], tuple[float, float] | None, tuple[float, float] | None]:
    """The segments one use of `command` draws from `x y`, its numbers absolute, with the
    cubic and the quadratic control points a next `S` or `T` reflects."""
    if command == "M":
        return [("M", (values[0], values[1]))], None, None
    if command == "L":
        return [("L", (values[0], values[1]))], None, None
    if command == "H":
        return [("L", (values[0], y))], None, None
    if command == "V":
        return [("L", (x, values[0]))], None, None
    if command in "CS":
        if command == "S":
            first = (2 * x - control[0], 2 * y - control[1]) if control else (x, y)
            values = [*first, *values]
        return [("C", tuple(values))], (values[2], values[3]), None
    if command in "QT":
        if command == "T":
            values = [
                *((2 * x - quadratic[0], 2 * y - quadratic[1]) if quadratic else (x, y)),
                *values,
            ]
        qx, qy, ex, ey = values
        first = (x + 2 / 3 * (qx - x), y + 2 / 3 * (qy - y))
        second = (ex + 2 / 3 * (qx - ex), ey + 2 / 3 * (qy - ey))
        return [("C", (*first, *second, ex, ey))], None, (qx, qy)
    return _arc(x, y, *values), None, None


def _arc(
    x1: float,
    y1: float,
    rx: float,
    ry: float,
    rotation: float,
    large: float,
    sweep: float,
    x2: float,
    y2: float,
) -> list[Segment]:
    """The cubics that draw an arc from `x1 y1` to `x2 y2`, at most a quarter turn each,
    as SVG's implementation notes convert an arc from its ends to its centre."""
    if (x1, y1) == (x2, y2):
        return []
    rx, ry = abs(rx), abs(ry)
    if rx == 0 or ry == 0:
        return [("L", (x2, y2))]
    cos_phi, sin_phi = math.cos(math.radians(rotation)), math.sin(math.radians(rotation))
    half_x, half_y = (x1 - x2) / 2, (y1 - y2) / 2
    x1p = cos_phi * half_x + sin_phi * half_y
    y1p = -sin_phi * half_x + cos_phi * half_y
    grown = (x1p / rx) ** 2 + (y1p / ry) ** 2
    if grown > 1:
        rx, ry = rx * math.sqrt(grown), ry * math.sqrt(grown)
    across = (rx * y1p) ** 2 + (ry * x1p) ** 2
    root = math.sqrt(max(0.0, ((rx * ry) ** 2 - across) / across))
    if large == sweep:
        root = -root
    cxp, cyp = root * rx * y1p / ry, -root * ry * x1p / rx
    cx = cos_phi * cxp - sin_phi * cyp + (x1 + x2) / 2
    cy = sin_phi * cxp + cos_phi * cyp + (y1 + y2) / 2
    start = _angle(1.0, 0.0, (x1p - cxp) / rx, (y1p - cyp) / ry)
    turn = _angle((x1p - cxp) / rx, (y1p - cyp) / ry, (-x1p - cxp) / rx, (-y1p - cyp) / ry)
    if not sweep and turn > 0:
        turn -= 2 * math.pi
    elif sweep and turn < 0:
        turn += 2 * math.pi
    count = max(1, math.ceil(abs(turn) / (math.pi / 2) - 1e-9))
    step = turn / count
    reach = 4 / 3 * math.tan(step / 4)

    def point(u: float, v: float) -> tuple[float, float]:
        """A point of the unit circle's plane, on the arc's ellipse."""
        return (
            cx + rx * cos_phi * u - ry * sin_phi * v,
            cy + rx * sin_phi * u + ry * cos_phi * v,
        )

    out: list[Segment] = []
    for index in range(count):
        a, b = start + index * step, start + (index + 1) * step
        first = point(math.cos(a) - reach * math.sin(a), math.sin(a) + reach * math.cos(a))
        second = point(math.cos(b) + reach * math.sin(b), math.sin(b) - reach * math.cos(b))
        end = (x2, y2) if index == count - 1 else point(math.cos(b), math.sin(b))
        out.append(("C", (*first, *second, *end)))
    return out


def _angle(ux: float, uy: float, vx: float, vy: float) -> float:
    """The signed angle from the vector `u` to `v`, in radians."""
    return math.atan2(ux * vy - uy * vx, ux * vx + uy * vy)
