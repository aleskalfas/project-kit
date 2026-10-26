"""The accepted decision records a change alters, shown to the person who authorises its
merge (#2161).

An edit to an accepted record that changes what the record decides, in either
direction, is a decision of its own (the decisions README, "Refining an accepted
record"). The backbone lists each record accepted where the change left its base
that the change alters or removes: each point it adds, alters or retires, each of
the record's own fields that changed, and whether the text its points stand on,
or its other text, changed (`pkit decisions check-diff --json`). The landing
command prints that list among the findings a person judges, before it stops
ready, asks or merges.

- `derive(head, base)` runs `pkit decisions check-diff --json --base <base> --head
  <head>`, unrouted, as the change check's derivation runs the backbone
  (`friction_answers`), after fetching the base where it is a remote's
  (`friction_answers.refresh_base`). It returns each record the change alters, or
  why the list could not be read, which is never an empty list.
- `lines(records)` is the list for a terminal, one line a record, every character a
  terminal would act on escaped (`friction_answers.shown`).

This capability never reads a record's points itself: which points a change edits
is the backbone's one reading of them.
"""

from __future__ import annotations

import json
import os
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

# Sibling _lib imports, dual-form, as `friction_answers` imports its own.
try:
    import friction_answers  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover
    from _lib import friction_answers  # type: ignore[no-redef]

#: The backbone's command, as `friction_answers` runs it: routing off.
CHECK_DIFF = ("decisions", "check-diff")
#: The version of `pkit decisions check-diff --json` this module reads; a document of
#: another is no list, never misread.
SCHEMA_VERSION = 1
#: How a line of the list begins, as a reviewer's finding begins with its reviewer.
SOURCE = "accepted record"
#: What the person is asked of each record, after what the change does to it.
ASK = "Judge whether each edit changes what the record decides."


@dataclass(frozen=True)
class Point:
    """One point of an accepted record the change alters: its id, how, and its title."""

    id: str
    change: str
    title: str = ""


@dataclass(frozen=True)
class Altered:
    """One accepted record the change alters or removes, as the backbone's document gives
    it: its path, its id, each point the change adds, alters, retires or removes, each of
    its own fields that changed, whether the text its points stand on or its other text
    changed, whether it is listed whole since its points are a list, and whether the
    change removes it."""

    path: str
    record: str
    points: tuple[Point, ...] = ()
    fields: tuple[str, ...] = ()
    shared: bool = False
    other: bool = False
    list_form: bool = False
    removed: bool = False

    def said(self) -> str:
        """What the change does to it: `point 1 (Scope) altered and point 4 (Who) added`."""
        if self.removed:
            return "removed"
        if self.list_form:
            return "altered as a whole, since its points are a list"
        parts = [
            f"point {point.id}" + (f" ({point.title})" if point.title else "") + f" {point.change}"
            for point in self.points
        ]
        if self.fields:
            parts.append(f"its {_and(self.fields)} altered")
        if self.shared:
            parts.append("the text its points stand on altered")
        if self.other:
            parts.append("its other text altered")
        return _and(parts) if parts else "altered"


@dataclass(frozen=True)
class Derivation:
    """The accepted records a change alters, or why they could not be read."""

    records: tuple[Altered, ...] = ()
    problem: str | None = None


def derive(head: str, base: str) -> Derivation:
    """The accepted records commit `head` alters against the branch `base`, the pull
    request's, named always, fetched first where it is a remote's. The backbone exits 1
    on an error in the change's numbering and still prints its document, so exit 0 and
    1 both carry one. Anything else, and a document of another version or without the
    list, is why the list could not be read."""
    problem = friction_answers.refresh_base(base)
    if problem is not None:
        return Derivation(problem=problem)
    argv = [*friction_answers.PKIT, *CHECK_DIFF, "--json", "--base", base, "--head", head]
    command = f"`{' '.join(argv)}`"
    try:
        proc = subprocess.run(
            argv,
            env={**os.environ, **friction_answers.UNROUTED},
            capture_output=True,
            text=True,
            check=False,
            timeout=friction_answers.TIMEOUT,
        )
    except FileNotFoundError as exc:
        return Derivation(problem=f"{command}: `pkit` is not on PATH ({exc})")
    except subprocess.TimeoutExpired:
        timeout = friction_answers.TIMEOUT
        return Derivation(problem=f"{command}: it did not answer within {timeout}s")
    except OSError as exc:
        return Derivation(problem=f"{command}: it could not be run ({exc})")
    said = [line.strip() for line in (proc.stderr or "").splitlines() if line.strip()]
    why = f"it exited {proc.returncode}" + (f": {friction_answers.shown(said[-1])}" if said else "")
    if proc.returncode not in (0, 1):
        return Derivation(problem=f"{command}: {why}")
    try:
        document = json.loads(proc.stdout or "")
    except ValueError:
        return Derivation(problem=f"{command}: {why}, with no JSON document")
    return read(document, command)


def read(document: Any, command: str) -> Derivation:
    """The backbone's document read, every field the list rests on checked: a document
    missing one is no list."""
    if not isinstance(document, Mapping) or document.get("schema_version") != SCHEMA_VERSION:
        return Derivation(problem=f"{command}: its answer is not a document of version 1")
    found = document.get("accepted_changes")
    if not isinstance(found, list):
        return Derivation(
            problem=f"{command}: its document lists no accepted records — the backbone "
            "predates the list"
        )
    records: list[Altered] = []
    for entry in found:
        altered = _altered(entry)
        if altered is None:
            return Derivation(problem=f"{command}: an entry of its list lacks what it needs")
        records.append(altered)
    return Derivation(tuple(records))


_FLAGS = ("shared_text", "other_text", "list_form", "removed")


def _altered(entry: Any) -> Altered | None:
    if not isinstance(entry, Mapping):
        return None
    path, record = entry.get("path"), entry.get("record")
    points, fields = entry.get("points"), entry.get("fields")
    flags = [entry.get(key) for key in _FLAGS]
    if not (
        isinstance(path, str)
        and isinstance(record, str)
        and isinstance(points, list)
        and isinstance(fields, list)
        and all(isinstance(field, str) for field in fields)
        and all(isinstance(flag, bool) for flag in flags)
    ):
        return None
    read_points: list[Point] = []
    for point in points:
        if not isinstance(point, Mapping):
            return None
        point_id, how, title = point.get("id"), point.get("change"), point.get("title")
        if not (isinstance(point_id, str) and isinstance(how, str) and isinstance(title, str)):
            return None
        read_points.append(Point(point_id, how, title))
    shared, other, list_form, removed = (bool(flag) for flag in flags)
    return Altered(
        path, record, tuple(read_points), tuple(fields), shared, other, list_form, removed
    )


def lines(records: Sequence[Altered]) -> list[str]:
    """The list for a terminal, a line a record: `[accepted record] PRJ-001, `path`: point 1
    (Scope) altered and point 4 (Who) added. Judge whether …`, every text the author chose
    escaped."""
    shown = friction_answers.shown
    return [
        f"[{SOURCE}] {shown(altered.record)}, `{shown(altered.path)}`: "
        f"{shown(altered.said())}. {ASK}"
        for altered in records
    ]


def _and(items: Sequence[str]) -> str:
    return items[0] if len(items) == 1 else f"{', '.join(items[:-1])} and {items[-1]}"
