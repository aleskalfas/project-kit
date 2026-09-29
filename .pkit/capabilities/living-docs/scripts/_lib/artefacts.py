"""The declared places and the documents in them, read as the backbone finds them.

Where artefacts are is computed once, by the backbone's artefact discovery
(ADR-057 point 2): the documentation roots, the places the project and every
installed capability declare — a capability's inside the location it names —
which files each one matches, and the skips validation applies (a synced copy,
a place outside the repository, a malformed declaration). A capability script
runs in its own environment and never imports the backbone, so it reads that
answer through the backbone's read command, `pkit friction artefacts --json`
(the lifecycle README, "How a registered command is run"), and never re-reads
the declarations or walks the places itself.

What living-docs decides over it is its own: which of several places matching
a file wins, and which space a place serves (`spaces`).
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

#: The document version this reading understands (the CLI reference, "friction
#: artefacts"); a later backbone that changes its meaning raises it.
SCHEMA_VERSION = 1

ARGV = ("pkit", "friction", "artefacts", "--json")

Runner = Callable[..., subprocess.CompletedProcess[str]]


class Unreadable(Exception):
    """The backbone's read command gave no document this reading understands."""


@dataclass(frozen=True)
class DeclaredPlace:
    """One place of the document: where it is declared and what it reaches.

    `index` is its position in the document's `places`, by which a file names
    the places matching it. `location` and `location_path` are the capability
    documentation location it lies inside, if it names one; `encloses` the
    audiences of the roots it reaches whole.
    """

    index: int
    source: str  # "project", "capability:<name>" or "backbone"
    declared: bool  # declared in `friction.places`, not a rule-set folder
    pointer: str
    written: str | None
    location: str | None
    location_path: str | None
    encloses: frozenset[str]

    @property
    def is_project(self) -> bool:
        return self.declared and self.source == "project"

    @property
    def capability(self) -> str | None:
        """The capability that declares it, for a capability's place."""
        prefix = "capability:"
        return self.source[len(prefix) :] if self.source.startswith(prefix) else None


@dataclass(frozen=True)
class Document:
    """One Markdown file a place matches: the places matching it, whether it is a
    rule-set file, whether `friction.exclude` leaves it out, and its front
    matter's own fields (`None` without a front-matter mapping)."""

    path: str
    places: tuple[int, ...]
    rule_set: bool
    excluded: bool
    fields: Mapping[str, Any] | None


@dataclass(frozen=True)
class Reading:
    """The backbone's answer: the roots by audience, the places, the documents by path."""

    roots: Mapping[str, str]
    places: tuple[DeclaredPlace, ...]
    documents: Mapping[str, Document]


def read_artefacts(root: Path, run: Runner = subprocess.run) -> Reading:
    """The declared places and their documents in the project at `root`, through
    `pkit friction artefacts --json`. Raises Unreadable when there is no document
    to read: `pkit` absent, a backbone without the command, a configuration it
    cannot read, a crash."""
    try:
        proc = run(list(ARGV), cwd=root, capture_output=True, text=True, check=False)
    except OSError as exc:
        raise Unreadable(f"`pkit` could not be run ({exc})") from exc
    try:
        document = json.loads(proc.stdout or "") if proc.returncode == 0 else None
    except ValueError:
        document = None
    if not isinstance(document, Mapping):
        detail = (proc.stderr or "").strip().splitlines()
        raise Unreadable(
            f"`{' '.join(ARGV)}` exited {proc.returncode} without its document"
            + (f": {detail[-1]}" if detail else "")
        )
    return reading_of(document)


def reading_of(document: Mapping[str, Any]) -> Reading:
    """The `pkit friction artefacts --json` document as a Reading."""
    if document.get("schema_version") != SCHEMA_VERSION:
        raise Unreadable(
            f"`{' '.join(ARGV)}` answered schema_version {document.get('schema_version')!r}; "
            f"this capability reads {SCHEMA_VERSION}"
        )
    roots = {str(k): v for k, v in _mapping(document.get("roots")).items() if isinstance(v, str)}
    if not {"user", "internal"} <= set(roots):
        raise Unreadable(f"`{' '.join(ARGV)}` answered without both documentation roots")
    places = tuple(
        _place(index, entry) for index, entry in enumerate(_mappings(document.get("places")))
    )
    documents = {}
    for entry in _mappings(document.get("files")):
        path = str(entry.get("path"))
        fields = entry.get("fields")
        documents[path] = Document(
            path=path,
            places=tuple(i for i in entry.get("places") or [] if isinstance(i, int)),
            rule_set=entry.get("rule_set") is not None,
            excluded=bool(entry.get("excluded")),
            fields=fields if isinstance(fields, Mapping) else None,
        )
    return Reading(roots=roots, places=places, documents=documents)


def _place(index: int, entry: Mapping[str, Any]) -> DeclaredPlace:
    location = entry.get("location")
    location = location if isinstance(location, Mapping) else {}
    written = entry.get("written")
    return DeclaredPlace(
        index=index,
        source=str(entry.get("source")),
        declared=bool(entry.get("declared")),
        pointer=str(entry.get("pointer") or ""),
        written=written if isinstance(written, str) else None,
        location=_text(location.get("name")),
        location_path=_text(location.get("path")),
        encloses=frozenset(str(a) for a in entry.get("encloses") or []),
    )


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _mappings(value: Any) -> list[Mapping[str, Any]]:
    return [item for item in value if isinstance(item, Mapping)] if isinstance(value, list) else []


def _text(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None
