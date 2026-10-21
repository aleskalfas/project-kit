"""The chain of use cases: what makes each precondition true (DEC-001 points 1, 2 and 12).

A use case starts only from what is already true. Each of its preconditions
names its producers, the use cases in force of its analysis that make it
true, any one of them enough (RS-SAN-009, the rule of logical consequence):

- **The data.** A use case's optional `after` lists, for each precondition in
  its order, its producers: use-case ids, its own among them, and
  `environment` beside them, never alone. Its schema holds that shape always.
  It draws no anchor, since a use case that names itself, or a loop of
  producers, would close a cycle (COR-050 point 5). An initial use case writes
  none.
- **The words.** Each line of its *Preconditions*, the part whose permanent id
  is `preconditions`, opens with its producers, such as `**From UC-003:**` or
  `**From UC-059, or Environment:**` (`forms.preconditions`).
- **The areas.** A use case's area is the folder of the use cases' place that
  holds it (`Analysis.area`). A number may open the area's name, such as
  `010-develop`, and gives one valid order in which the areas build on each
  other (`model.area_number`). A producer lies in a *later* area only where
  both areas carry numbers and the producer's is the higher (DEC-003 point 5).

**What the check holds** (`check._after`), of a use case in force that writes
`after`, where RS-SAN-009 binds and at its status, as `SAN` declares under its
`checks`:

- each producer is a use case in force of its own analysis, the use case itself
  among them, or `environment`;
- `after` holds one entry for each precondition its words write, in their
  order, and each entry names the producers its precondition's opening names;
- where its area carries a number, each entry names a producer in no later
  area: the environment, a use case of an area whose number is no higher, or a
  use case of an area without a number or of no area. A reviewer judges the
  last two, and every use case that writes no `after`.

**What the chain draws** (`diagrams`, DEC-003 point 5): an arrow from each
producer to its use case, dotted from a later area. A solid arrow is left out
where other solid arrows lead from its producer's node to its use case's node
through a third node, the use cases of one loop of solid arrows counting as
one node (`left_out`). A dotted arrow, an arrow from a use case to itself and an
arrow within a loop are never left out.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence

from _lib import forms, structure
from _lib.model import AFTER, Artefact, area_number

#: How a part of the words opens, as `forms.Precondition` reads it.
Precondition = forms.Precondition


def writes_after(artefact: Artefact) -> bool:
    """Whether the use case writes `after` at all, whatever it holds."""
    return AFTER in artefact.fields


def producers(artefact: Artefact) -> tuple[tuple[str, ...], ...] | None:
    """A use case's `after`, one entry for each precondition, each its producers as
    written; `None` where it writes none, or one that is no list of lists of texts, which
    the use case's schema reports."""
    value = artefact.fields.get(AFTER)
    if not isinstance(value, list):
        return None
    entries: list[tuple[str, ...]] = []
    for entry in value:
        if not isinstance(entry, list) or not all(isinstance(p, str) for p in entry):
            return None
        entries.append(tuple(entry))
    return tuple(entries)


def later(producer_area: str | None, area: str | None) -> bool:
    """Whether a producer in `producer_area` lies in a later area than a use case in
    `area`: both carry numbers, and the producer's is the higher (DEC-003 point 5)."""
    theirs, own = area_number(producer_area), area_number(area)
    return theirs is not None and own is not None and theirs > own


def words(text: str, kind: structure.Kind) -> tuple[structure.Element, list[Precondition]] | None:
    """A use case's *Preconditions*, as `kind` gives its parts, and each precondition its
    words write, in order: `None` where the body carries no such part, which the format
    rule reports."""
    for element, part in structure.parts(structure.body_lines(text), kind):
        if element.id == structure.PRECONDITIONS and not element.added:
            return element, forms.preconditions(part)
    return None


def left_out(solid: Iterable[tuple[str, str]]) -> set[tuple[str, str]]:
    """The solid arrows, `(producer, use case)`, that the chain leaves out (DEC-003 point
    5). The nodes on one loop of solid arrows count as one node. An arrow between two such
    nodes is left out where other solid arrows lead from the first to the second through a
    third. An arrow from a node to itself, and one within a loop, are never left out."""
    arrows = {(a, b) for a, b in solid if a != b}
    after: dict[str, set[str]] = {}
    for a, b in arrows:
        after.setdefault(a, set()).add(b)
        after.setdefault(b, set())
    reach = {node: _reached(node, after) for node in after}
    loop = {
        node: frozenset({node, *(m for m in reach[node] if node in reach[m])}) for node in after
    }
    joined: dict[frozenset[str], set[frozenset[str]]] = {}
    for a, b in arrows:
        if loop[a] != loop[b]:
            joined.setdefault(loop[a], set()).add(loop[b])

    def reaches(start: frozenset[str], goal: frozenset[str]) -> bool:
        member = next(iter(goal))
        return any(member in reach[node] for node in start)

    implied = {
        (first, second)
        for first, nexts in joined.items()
        for second in nexts
        if any(third != second and reaches(third, second) for third in nexts)
    }
    return {(a, b) for a, b in arrows if (loop[a], loop[b]) in implied}


def _reached(start: str, after: Mapping[str, set[str]]) -> set[str]:
    """Every node a path of one arrow or more leads to from `start`."""
    seen: set[str] = set()
    stack: list[str] = list(after.get(start, ()))
    while stack:
        node = stack.pop()
        if node in seen:
            continue
        seen.add(node)
        stack.extend(after.get(node, ()))
    return seen


def ordered_areas(areas: Sequence[str]) -> list[str]:
    """The areas in the order of their numbers, then those without one, each by name."""
    return sorted(
        set(areas),
        key=lambda area: (
            area_number(area) is None,
            area_number(area) or 0,
            area,
        ),
    )
