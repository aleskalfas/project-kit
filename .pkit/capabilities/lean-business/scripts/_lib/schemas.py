"""What the check reads from the capability's own schemas: where each kind of file writes a
calendar day (lean-business DEC-003 point 1).

A day's shape, `YYYY-MM-DD`, is the schemas' (`shapes.schema.json`, `day`), and the
backbone's data validation holds a file to it. The shape admits a day the calendar does not
hold, such as `2026-12-32`, which `reading.day` reads as none, so every date the check
compares would pass over it without a word. `unreadable_days` finds each such value, at
each place the file's schema puts a day, so the check reports it.

The places are read from the schemas themselves, every property whose shape is the shared
day, through the schema's own definitions and its lists, so a field added to a schema is
found with no list to keep beside it.
"""

from __future__ import annotations

import json
from collections.abc import Iterator, Mapping
from functools import cache
from pathlib import Path
from typing import Any

from _lib.reading import day, written_as_day

#: The capability's schemas, beside its scripts.
FOLDER = Path(__file__).resolve().parent.parent.parent / "schemas"

#: The shared shape of a day, as a schema of the capability's refers to it.
DAY = "shapes.schema.json#/$defs/day"

#: A place's step that stands for each item of a list.
EACH = "*"

_LOCAL = "#/$defs/"


@cache
def day_places(kind: str) -> tuple[tuple[str, ...], ...]:
    """Each place where a file of `kind`, such as `cycle`, writes a day: a path of keys
    from the file's top, `EACH` standing for each item of a list. In the schema's order."""
    schema = json.loads((FOLDER / f"{kind}.schema.json").read_text(encoding="utf-8"))
    defs = schema.get("$defs") or {}
    return tuple(dict.fromkeys(_walk(schema, defs, (), frozenset())))


def _walk(
    node: object, defs: Mapping[str, Any], path: tuple[str, ...], seen: frozenset[str]
) -> Iterator[tuple[str, ...]]:
    if not isinstance(node, Mapping):
        return
    ref = node.get("$ref")
    if ref == DAY:
        yield path
        return
    if isinstance(ref, str) and ref.startswith(_LOCAL) and ref not in seen:
        yield from _walk(defs.get(ref[len(_LOCAL) :]), defs, path, seen | {ref})
    properties = node.get("properties")
    if isinstance(properties, Mapping):
        for key, sub in properties.items():
            yield from _walk(sub, defs, (*path, str(key)), seen)
    if "items" in node:
        yield from _walk(node["items"], defs, (*path, EACH), seen)
    for combined in ("allOf", "anyOf", "oneOf"):
        for sub in node.get(combined) or []:
            yield from _walk(sub, defs, path, seen)
    for branch in ("if", "then", "else"):
        yield from _walk(node.get(branch), defs, path, seen)


def days_written(kind: str, data: object) -> list[tuple[str, object]]:
    """Each value a file of `kind` writes at a place its schema puts a day, with the JSON
    Pointer to it, in the schema's order of places."""
    found: list[tuple[str, object]] = []
    for place in day_places(kind):
        found.extend(_at(data, place, ""))
    return found


def _at(node: object, place: tuple[str, ...], pointer: str) -> Iterator[tuple[str, object]]:
    if not place:
        yield pointer, node
        return
    step, rest = place[0], place[1:]
    if step == EACH:
        if isinstance(node, list):
            for index, item in enumerate(node):
                yield from _at(item, rest, f"{pointer}/{index}")
    elif isinstance(node, Mapping) and step in node:
        yield from _at(node[step], rest, f"{pointer}/{step}")


def unreadable_days(kind: str, data: object) -> list[tuple[str, str]]:
    """Each day a file of `kind` writes in the shape of a day that names no day of the
    calendar, with the JSON Pointer to it. A value of another shape is the shape's to
    report."""
    return [
        (pointer, value)
        for pointer, value in days_written(kind, data)
        if isinstance(value, str) and written_as_day(value) and day(value) is None
    ]
