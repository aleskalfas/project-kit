"""The geometry of ties that share a trunk (visual-communication DEC-043 points 3, 5 and 6):
where a group's branches leave the trunk's first leg, how two ties' routes meet, and where
the middle of a line's own stretch lies. The connector tool (`layout.Instance._anchors`)
reads it; it knows no tie, no part and no scene, only points and lengths.

- **Where the junctions lie** (`junctions`, point 3). Each lies on the trunk's first leg,
  within its junction span, at least the least gap from its neighbours, and short of its
  branch's limit. Where the even places, which split the first leg into equal parts, keep
  all four, the junctions take them. Otherwise they take the least places: of every set of
  places that keeps the four, the one whose distances from the even places, squared, add up
  least. Only one set does, and no junction of it could come nearer its even place without
  another going farther from its own. It is found by pooling neighbours (`_pooled`), each
  pool at the mean of its members' even places, held within the span and the limits. None
  where no set keeps the four: the group has no room.
- **How two routes meet** (`meetings`, point 5). Two legs *pass across* each other where
  they meet at a point, a touch included, and *run side by side* where they are parallel,
  overlap along their line, and lie nearer each other than a gap, on one line included. A
  meeting at a point the caller names, such as where both routes end, is none, nor is one
  where two legs meet at a point of a stretch the same two run side by side along.
- **The middle of a line's own stretch** (`own_point`, point 6): the point halfway along the
  part of its route that starts at a point of its first leg, or ends at one of its last,
  measured along the route's points, a round turn taken sharp.

Every point is across and down, in px. Lengths are compared within `NEAR`, the scene's
resolution, so the points the scene holds, rounded to it, meet where they touch.
"""

from __future__ import annotations

import itertools
import math
from collections.abc import Collection, Sequence

from _lib import formula as fm

#: A point, across and down.
Point = tuple[float, float]

#: The decimal places to which the scene holds a length (`scene.PLACES`).
PLACES = 2

#: How long an arrowhead is, in widths of its line's stroke: the primitive's (the capability's
#: `components.md`, *Primitives*), which every renderer draws.
HEAD = 5.0

#: Two lengths this close are one: the scene's resolution, 1/100 px.
NEAR = 10.0**-PLACES

#: Two places this close keep a bound that one of them names exactly: floating error, never
#: a length.
EXACT = 1e-9


def junctions(
    start: float, end: float, gap: float, limits: Sequence[float], length: float
) -> tuple[float, ...] | None:
    """Where the junctions of a group's branches lie, as their distances along the trunk's
    first leg from the group's point, in the branches' order, the one nearest the item first
    (DEC-043 point 3). `start` and `end` bound the junction span, `gap` is the least gap
    between neighbours, each of `limits` the farthest its branch may leave, and `length` the
    first leg's. The even places where they keep the span, the gap and the limits; else the
    least places; None where no places keep them."""
    count = len(limits)
    caps = [min(limit, end) for limit in limits]
    if any(start + place * gap > cap + EXACT for place, cap in enumerate(caps)):
        return None
    even = [length * (place + 1) / (count + 1) for place in range(count)]
    apart = all(second - first >= gap - EXACT for first, second in itertools.pairwise(even))
    if (
        apart
        and even[0] >= start - EXACT
        and all(place <= cap + EXACT for place, cap in zip(even, caps, strict=True))
    ):
        return tuple(even)
    # Shifted by the least gaps before each, the places only need to keep their order.
    targets = [place - index * gap for index, place in enumerate(even)]
    bounds = [cap - index * gap for index, cap in enumerate(caps)]
    shifted = _pooled(targets, start, bounds)
    return tuple(place + index * gap for index, place in enumerate(shifted))


def _pooled(targets: Sequence[float], least: float, bounds: Sequence[float]) -> list[float]:
    """The places, in order and never decreasing, each at least `least` and at most its own
    of `bounds`, whose distances from `targets`, squared, add up least: neighbours that would
    fall out of order are pooled at their targets' mean, held within the pool's bounds, until
    none does (the pool-adjacent-violators procedure, for a sum of squares bounded so). The
    caller has found that `least` lies within every bound."""
    pools: list[tuple[float, int, float]] = []  # each: its targets' sum, its size, its bound

    def place(pool: tuple[float, int, float]) -> float:
        total, size, bound = pool
        return min(max(total / size, least), bound)

    for target, bound in zip(targets, bounds, strict=True):
        pools.append((target, 1, bound))
        while len(pools) > 1 and place(pools[-2]) > place(pools[-1]):
            (total, size, held), (more, count, cap) = pools[-2], pools[-1]
            pools[-2:] = [(total + more, size + count, min(held, cap))]
    return [place(pool) for pool in pools for _ in range(pool[1])]


def held(value: float) -> float:
    """A length as the scene holds it: rounded to `PLACES`, never a negative zero."""
    return fm.rounded(value, PLACES) + 0.0


def held_route(route: Sequence[Point]) -> list[Point]:
    """A route's points as the scene holds them."""
    return [(held(x), held(y)) for x, y in route]


def legs(route: Sequence[Point]) -> list[tuple[Point, Point]]:
    """The straight stretches of a route, each from one of its points to the next; a point
    that repeats the one before it starts none."""
    return [(first, second) for first, second in itertools.pairwise(route) if first != second]


def meetings(
    first: Sequence[Sequence[Point]],
    second: Sequence[Sequence[Point]],
    gap: float,
    skip: Collection[Point] = (),
) -> tuple[int, int]:
    """How often two ties meet, each drawn by the routes it gives (DEC-043 point 5): the
    points where their legs pass across each other, a touch included, and the pairs of their
    legs that run side by side nearer than `gap`, or on one line. A meeting at a point of
    `skip`, or at a point of a stretch along which the same two legs' ties run side by side,
    is none."""
    beside: list[tuple[tuple[Point, Point], tuple[Point, Point]]] = []
    across: list[Point] = []
    for one, other in itertools.product(
        [leg for route in first for leg in legs(route)],
        [leg for route in second for leg in legs(route)],
    ):
        kind, at = _meet(one, other, gap)
        if kind == "beside":
            beside.append((one, other))
        elif at is not None:
            across.append(at)
    points: list[Point] = []
    for at in across:
        if any(_close(at, each) for each in (*points, *skip)):
            continue
        if any(_on(at, one) and _on(at, other) for one, other in beside):
            continue
        points.append(at)
    return len(points), len(beside)


def _meet(
    one: tuple[Point, Point], other: tuple[Point, Point], gap: float
) -> tuple[str, Point | None]:
    """How two legs meet: `beside`, where they are parallel, overlap along their line and
    lie nearer than `gap`, or on one line; `across`, with the point, where they touch or pass
    across each other; else neither, with no point."""
    (ax, ay), (bx, by) = one
    (cx, cy), (dx, dy) = other
    ux, uy, vx, vy = bx - ax, by - ay, dx - cx, dy - cy
    size = math.hypot(ux, uy)
    cross = ux * vy - uy * vx
    if abs(cross) <= EXACT * size * math.hypot(vx, vy):
        # Parallel: how far apart their lines lie, and how far they overlap along them.
        apart = abs(ux * (cy - ay) - uy * (cx - ax)) / size
        along = [((px - ax) * ux + (py - ay) * uy) / size for px, py in other]
        overlap = min(size, max(along)) - max(0.0, min(along))
        # Nearer than the gap beyond the scene's resolution, as held points may be.
        if overlap > NEAR and (apart < gap - NEAR - EXACT or apart <= NEAR):
            return "beside", None
        if apart <= NEAR and overlap >= -NEAR:
            # They touch end to end, on one line.
            ends = [point for point in other if _on(point, one)] or [
                point for point in one if _on(point, other)
            ]
            return ("across", ends[0]) if ends else ("", None)
        return "", None
    # Where the two lines cross, as a share of each leg.
    t = ((cx - ax) * vy - (cy - ay) * vx) / cross
    s = ((cx - ax) * uy - (cy - ay) * ux) / cross
    reach = NEAR / size, NEAR / math.hypot(vx, vy)
    if -reach[0] <= t <= 1 + reach[0] and -reach[1] <= s <= 1 + reach[1]:
        return "across", (ax + t * ux, ay + t * uy)
    return "", None


def common_ends(first: Sequence[Sequence[Point]], second: Sequence[Sequence[Point]]) -> list[Point]:
    """The points where routes of both ties end."""
    theirs = [route[at] for route in second for at in (0, -1)]
    return [
        route[at]
        for route in first
        for at in (0, -1)
        if any(_close(route[at], point) for point in theirs)
    ]


def _close(first: Point, second: Point) -> bool:
    return math.hypot(first[0] - second[0], first[1] - second[1]) <= NEAR


def holds(frame: tuple[float, float, float, float], point: Point) -> bool:
    """Whether a frame holds a point, its edges included, within `NEAR`."""
    x, y, width, height = frame
    px, py = point
    return x - NEAR <= px <= x + width + NEAR and y - NEAR <= py <= y + height + NEAR


def _on(point: Point, leg: tuple[Point, Point]) -> bool:
    """Whether a point lies on a leg, within `NEAR`."""
    return distance(point, leg) <= NEAR


def distance(point: Point, leg: tuple[Point, Point]) -> float:
    """How far a point lies from a leg: from its nearest point."""
    (px, py), ((ax, ay), (bx, by)) = point, leg
    ux, uy = bx - ax, by - ay
    size = ux * ux + uy * uy
    share = 0.0 if size == 0 else min(max(((px - ax) * ux + (py - ay) * uy) / size, 0.0), 1.0)
    return math.hypot(px - (ax + share * ux), py - (ay + share * uy))


def length(route: Sequence[Point]) -> float:
    """How long a route is, along its points."""
    return sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in itertools.pairwise(route))


def along(route: Sequence[Point], at: float) -> Point:
    """The point `at` px along a route from its first point; its last point past its end."""
    for (ax, ay), (bx, by) in itertools.pairwise(route):
        size = math.hypot(bx - ax, by - ay)
        if at <= size and size > 0:
            return ax + (bx - ax) * at / size, ay + (by - ay) * at / size
        at -= size
    return route[-1]


def stretch(route: Sequence[Point], start: float, end: float) -> list[Point]:
    """The part of a route from `start` px along it to `end` px."""
    points = [along(route, start)]
    walked = 0.0
    for first, second in itertools.pairwise(route):
        walked += math.hypot(second[0] - first[0], second[1] - first[1])
        if start < walked < end:
            points.append(second)
    points.append(along(route, end))
    return points


def own_point(route: Sequence[Point], since: Point, from_start: bool) -> Point:
    """The point halfway along a line's own stretch (DEC-043 point 6). The line shares the
    stretch of its route from its first point to `since`, a point of its first leg, where
    `from_start`; else from `since`, a point of its last leg, to its last point."""
    whole = length(route)
    if from_start:
        shared = math.hypot(since[0] - route[0][0], since[1] - route[0][1])
        return along(route, (shared + whole) / 2)
    shared = math.hypot(route[-1][0] - since[0], route[-1][1] - since[1])
    return along(route, (whole - shared) / 2)


def shared_stretch(route: Sequence[Point], since: Point, from_start: bool) -> list[Point]:
    """The stretch of a route a line shares: from its first point to `since` where
    `from_start`, else from `since` to its last point."""
    whole = length(route)
    if from_start:
        return stretch(route, 0.0, math.hypot(since[0] - route[0][0], since[1] - route[0][1]))
    return stretch(
        route, whole - math.hypot(route[-1][0] - since[0], route[-1][1] - since[1]), whole
    )


def trimmed(route: Sequence[Point], by: float, from_start: bool) -> list[Point]:
    """A route with its first `by` px left out where `from_start`, else its last."""
    whole = length(route)
    return stretch(route, by, whole) if from_start else stretch(route, 0.0, whole - by)


def frame_meets(frame: tuple[float, float, float, float], route: Sequence[Point]) -> bool:
    """Whether a route passes through a frame, more than `NEAR` inside its edges."""
    x, y, width, height = frame
    left, top, right, bottom = x + NEAR, y + NEAR, x + width - NEAR, y + height - NEAR
    if right <= left or bottom <= top:
        return False
    for (ax, ay), (bx, by) in legs(route):
        low, high = 0.0, 1.0
        for p, q in (
            (ax - bx, ax - left),
            (bx - ax, right - ax),
            (ay - by, ay - top),
            (by - ay, bottom - ay),
        ):
            if p == 0:
                if q < 0:
                    break
                continue
            share = q / p
            if p < 0:
                low = max(low, share)
            else:
                high = min(high, share)
        else:
            if low <= high:
                return True
    return False
