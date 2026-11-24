"""What a piece's brief hands the review first (visual-communication DEC-070 point 5): the
goals, relations and takeaways of the piece and of each page it speaks of, without their
reasons.

The intent is built by naming each field it keeps, so no field the brief gains reaches it,
the reasons included, until this names it.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from _lib import names
from _lib import pipeline as pl
from _lib.briefs import PAGES, PIECE, read

#: The fields of a part the review is handed, in the order they are printed.
GOALS = "goals"
RELATIONS = "relations"
TAKEAWAY = "takeaway"


def of(piece: pl.Piece) -> dict[str, Any] | None:
    """The intent of the piece's brief: `piece` for the whole piece and `pages` for each page
    it speaks of, in the brief's order. A part holds the goals, relations and takeaway it
    states, and none it leaves unsaid. None where the piece keeps no brief, or its brief
    cannot be read, which the check of bindings reports."""
    brief = read(piece)
    if brief is None:
        return None
    parts = brief.get(PAGES)
    return {
        PIECE: _intent(brief.get(PIECE)),
        PAGES: {
            str(page): _intent(part)
            for page, part in (parts.items() if isinstance(parts, Mapping) else [])
            if page != names.CONTAINER
        },
    }


def _intent(part: Any) -> dict[str, Any]:
    """The goals, relations and takeaway of one part."""
    if not isinstance(part, Mapping):
        return {}
    kept: dict[str, Any] = {}
    goals = part.get(GOALS)
    if isinstance(goals, list):
        kept[GOALS] = [str(goal) for goal in goals]
    relations = part.get(RELATIONS)
    if isinstance(relations, list):
        kept[RELATIONS] = [_relation(each) for each in relations if isinstance(each, Mapping)]
    if TAKEAWAY in part:
        kept[TAKEAWAY] = str(part[TAKEAWAY])
    return kept


def _relation(relation: Mapping[str, Any]) -> dict[str, Any]:
    """A relation's words, and the parts of the content it relates where it names them."""
    kept: dict[str, Any] = {"text": str(relation.get("text", ""))}
    relates = relation.get("relates")
    if isinstance(relates, list):
        kept["relates"] = [str(each) for each in relates]
    return kept


def lines(intent: Mapping[str, Any]) -> list[str]:
    """The intent in words, one line for each goal, relation and takeaway, under the part's
    name; a part that says nothing is named as saying nothing."""
    out = [*_part_lines("the piece", intent[PIECE])]
    for page, part in intent[PAGES].items():
        out.extend(_part_lines(f"page {page}", part))
    return out


def _part_lines(name: str, part: Mapping[str, Any]) -> list[str]:
    out = [f"{name}:"]
    for goal in part.get(GOALS, []):
        out.append(f"  goal: {_flat(goal)}")
    for relation in part.get(RELATIONS, []):
        said = f"  relation: {_flat(relation['text'])}"
        if relation.get("relates"):
            said += f" (relates: {', '.join(relation['relates'])})"
        out.append(said)
    if TAKEAWAY in part:
        out.append(f"  takeaway: {_flat(part[TAKEAWAY])}")
    if len(out) == 1:
        out.append("  (states no goal, relation or takeaway)")
    return out


def _flat(text: str) -> str:
    """`text` on one line."""
    return " ".join(text.split())
