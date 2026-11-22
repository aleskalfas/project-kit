"""A canvas drawn as a grid in the terminal, arranged as in the book, with its credit and
licence line beneath (lean-business DEC-001 point 6).

Five columns, each a box over a box, and a row of two boxes along the bottom:

    +------------------+------------------+------------------+------------------+------------------+
    | PROBLEM          | SOLUTION         | UNIQUE VALUE     | UNFAIR ADVANTAGE | CUSTOMER         |
    |                  |                  | PROPOSITION      |                  | SEGMENTS         |
    +------------------+------------------+------------------+------------------+------------------+
    | EXISTING         | KEY METRICS      | HIGH-LEVEL       | CHANNELS         | EARLY ADOPTERS   |
    | ALTERNATIVES     |                  | CONCEPT          |                  |                  |
    +----------------------------------------------------------------------------------------------+
    | COST STRUCTURE                               | REVENUE STREAMS                               |
    +----------------------------------------------+-----------------------------------------------+

The upper boxes share one height, and the lower ones another, each the height of the box
with the most to say. The line beneath credits where the arrangement comes from and names
the licence the template is published under; it claims no licence for the grid.

`pkit lean canvas` draws one variant's canvas, and the status of an idea draws the canvas
of each variant in play, each the same way: the line that names the variant and its model
(`heading`), then the grid (`draw`).
"""

from __future__ import annotations

import textwrap
from collections.abc import Mapping, Sequence
from typing import Any

from _lib import readings

#: The columns, each its upper box and its lower one, in the book's order.
COLUMNS = (
    ("problem", "existing-alternatives"),
    ("solution", "key-metrics"),
    ("unique-value-proposition", "high-level-concept"),
    ("unfair-advantage", "channels"),
    ("customer-segments", "early-adopters"),
)

#: The row along the bottom.
BOTTOM = ("cost-structure", "revenue-streams")

#: Each box's heading.
HEADINGS = {
    "problem": "Problem",
    "existing-alternatives": "Existing alternatives",
    "solution": "Solution",
    "key-metrics": "Key metrics",
    "unique-value-proposition": "Unique value proposition",
    "high-level-concept": "High-level concept",
    "unfair-advantage": "Unfair advantage",
    "channels": "Channels",
    "customer-segments": "Customer segments",
    "early-adopters": "Early adopters",
    "cost-structure": "Cost structure",
    "revenue-streams": "Revenue streams",
}

#: The line beneath the grid.
CREDIT = (
    "Arranged as the Lean Canvas, Ash Maurya's adaptation of the Business Model Canvas by "
    "Alex Osterwalder; both are published under Creative Commons Attribution-ShareAlike 3.0, "
    "creativecommons.org/licenses/by-sa/3.0. The grid claims no licence of its own."
)

#: The width of a column's text.
WIDTH = 16


def entry_lines(entry: Mapping[str, Any], box: str, width: int, *, with_ids: bool) -> list[str]:
    """An entry's words, as its box shows them: its side first in a model with several, and
    what it links to after."""
    text = str(entry.get("text", ""))
    side = entry.get("side")
    if isinstance(side, str):
        text = f"[{side}] {text}"
    if box == "channels" and isinstance(entry.get("kind"), str):
        text = f"{text} ({entry['kind']})"
    if box == "key-metrics" and isinstance(entry.get("step"), str):
        text = f"{text} ({entry['step']})"
    if box == "unique-value-proposition" and isinstance(entry.get("sub-headline"), str):
        text = f"{text}: {entry['sub-headline']}"
    if box == "early-adopters":
        held = entry.get("triggers")
        triggers = [t for t in held if isinstance(t, str)] if isinstance(held, list) else []
        if triggers:
            text = f"{text}; switches on: {'; '.join(triggers)}"
    lines = textwrap.wrap(text, width - 2) or [""]
    out = [f"- {lines[0]}", *(f"  {line}" for line in lines[1:])]
    if with_ids and isinstance(entry.get("id"), str):
        own = str(entry["id"]).rsplit("--", 1)[-1]
        out.extend(f"  {part}" for part in textwrap.wrap(f"[{own}]", width - 2))
    return out


def _box(canvas: Mapping[str, Any], box: str, width: int, *, with_ids: bool) -> list[str]:
    lines = textwrap.wrap(HEADINGS[box].upper(), width)
    for entry in readings.entries(canvas, box):
        lines.extend(entry_lines(entry, box, width, with_ids=with_ids))
    return lines


def heading(canvas: Mapping[str, Any]) -> str:
    """The line above the grid: the variant's id, its model's archetype, and the sides it
    serves where it names any."""
    archetype = canvas.get("archetype")
    model = (
        f"a {archetype} model"
        if isinstance(archetype, str)
        else "a model whose archetype cannot be read"
    )
    sides = canvas.get("sides")
    named = [s for s in sides if isinstance(s, str)] if isinstance(sides, list) else []
    head = f"`{canvas.get('id')}`, {model}"
    return f"{head}, serving {', '.join(named)}" if named else head


def _padded(lines: Sequence[str], height: int) -> list[str]:
    return [*lines, *([""] * (height - len(lines)))]


def draw(canvas: Mapping[str, Any], *, with_ids: bool = False) -> list[str]:
    """The canvas as the grid's lines, its credit line last."""
    upper = [_box(canvas, top, WIDTH, with_ids=with_ids) for top, _ in COLUMNS]
    lower = [_box(canvas, bottom, WIDTH, with_ids=with_ids) for _, bottom in COLUMNS]
    high, low = max(map(len, upper)), max(map(len, lower))
    rule = "+" + "+".join("-" * (WIDTH + 2) for _ in COLUMNS) + "+"
    out = [rule]
    for row in range(high):
        out.append("| " + " | ".join(f"{_padded(c, high)[row]:<{WIDTH}}" for c in upper) + " |")
    out.append(rule)
    for row in range(low):
        out.append("| " + " | ".join(f"{_padded(c, low)[row]:<{WIDTH}}" for c in lower) + " |")
    total = len(rule) - 4
    half = (total - 3) // 2
    other = total - 3 - half
    out.append("+" + "-" * (len(rule) - 2) + "+")
    left = _box(canvas, BOTTOM[0], half, with_ids=with_ids)
    right = _box(canvas, BOTTOM[1], other, with_ids=with_ids)
    rows = max(len(left), len(right))
    for row in range(rows):
        out.append(f"| {_padded(left, rows)[row]:<{half}} | {_padded(right, rows)[row]:<{other}} |")
    out.append(f"+{'-' * (half + 2)}+{'-' * (other + 2)}+")
    out.extend(textwrap.wrap(CREDIT, len(rule)))
    return out
