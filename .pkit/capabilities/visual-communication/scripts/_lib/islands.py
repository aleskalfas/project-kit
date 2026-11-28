"""The measure of islands: whether a cause that hides some of a span's ink takes a piece of it
that stands apart, such as a dot (visual-communication DEC-045 point 1, DEC-054 points 1 and 2).

Both renderers' reads take it, resvg's (`viewing_tool`) and a browser's (`viewing_browser`), so
`island` means one thing in either report. So the levels and the joining are one set, and the
outputs page states them. Each read gives the measure its span's ink as a darkness for each
pixel, 0 where the span's letters alone change it by the whole difference between their two
colours and 255 where by none, as drawn black on white; and, for a cover, how much of each
pixel's ink the page drawn whole still shows, from 0 to `ALL`.

It stands on the standard library alone, so a read that needs no other tool pays nothing for it.
"""

from __future__ import annotations

from collections.abc import Collection, Mapping

#: A pixel of a span's ink: its row and its column, as the read that gives it places them.
Pixel = tuple[int, int]

#: The darkest a pixel may be, drawn black on white, for it to be strong ink: it lies nearer
#: black than white.
STRONG = 127

#: The levels at which a span's ink falls into islands, each the lightest a pixel may be,
#: drawn black on white, for the pixel to be ink at that level: strong ink, and two lighter. A
#: small dot may hold no strong ink, and at a lighter level it may meet its letter, so a cause
#: that takes an island at any of them is named (DEC-045 point 1).
LEVELS = (STRONG, 159, 191)

#: The lightest ink the reads take of a span, its counted ink: its lightest level.
FAINT = LEVELS[-1]

#: How much of a pixel's ink the page drawn whole shows where it shows all of it: the whole
#: difference between the span's two colours.
ALL = 255

#: Where the pixels of an island meet one another: by a side or by a corner.
NEIGHBOURS = ((-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1))


def takes_an_island(
    ink: Mapping[Pixel, int],
    lost: Collection[Pixel],
    shows: Mapping[Pixel, int] | None = None,
) -> bool:
    """Whether a cause that hides `lost` of `ink` wholly takes an island of it at any of
    `LEVELS`: of its pixels no lighter than the level, a set each of which meets another by a
    side or a corner, and meets no other such pixel (DEC-045 point 1). The cause hides wholly
    some pixel of the island, and leaves none of it showing at the level: where `shows` gives
    how much of each pixel's ink the page drawn whole still shows, a pixel shows at the level
    where it shows enough for it to be that dark (`shows_at`); where it gives none, as past
    the page's edge, every pixel the cause does not hide shows. Only the islands that hold a
    pixel of `lost` are walked."""
    gone = set(lost)
    for level in LEVELS:
        seen: set[Pixel] = set()
        for start in gone:
            if start in seen or ink.get(start, level + 1) > level:
                continue
            seen.add(start)
            island = [start]
            unseen = True
            for row, column in island:
                for down, across in NEIGHBOURS:
                    near = (row + down, column + across)
                    if near not in seen and ink.get(near, level + 1) <= level:
                        seen.add(near)
                        island.append(near)
                        if shows is None:
                            unseen = unseen and near in gone
                        else:
                            unseen = unseen and not shows_at(shows.get(near, ALL), level)
            if unseen:
                return True
    return False


def shows_at(shown: int, level: int) -> bool:
    """Whether a pixel of a span's ink, of which the page drawn whole shows `shown` of `ALL`,
    still shows at `level`: whether, drawn black on white, so much of its ink would make it
    that dark or darker (DEC-045 point 1)."""
    return ALL - shown <= level
