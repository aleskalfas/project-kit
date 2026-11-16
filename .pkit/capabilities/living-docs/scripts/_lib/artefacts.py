"""The declared places and the documents in them, read as the backbone finds them.

Where artefacts are is computed once, by the backbone's artefact discovery
(ADR-057 point 2): the documentation roots, the places the project and every
installed capability declare — a capability's inside the location it names —
which files each one matches, the skips validation applies (a synced copy, a
place outside the repository, a malformed declaration), and the documents a
component holds that are not artefacts, with their owner. A capability script
runs in its own environment and never imports the backbone, so it reads that
answer through the backbone's read command, `pkit friction artefacts --json`
(the lifecycle README, "How a registered command is run"), and never re-reads
the declarations or walks the places itself.

The same answer gives each artefact its type, the place that gave it, and the
places matching its file in the order COR-056 point 3 sets, with each one's
rank (COR-056 point 6). living-docs reads them and ranks no place itself.
What it decides over the answer is its own: which space a place serves, and
what a document is to its spaces (`spaces`).

The answer is read by its keys (ADR-097 point 3). A key the reading does not
read, it ignores. A key it reads that is missing, null where the CLI reference
does not print it null, of another type, or a value it does not know of a set it
decides on, is an answer it cannot tell anything from: `Unreadable`, never a
default such as false or empty. Every key it reads is printed by each backbone
this capability runs on, so only a malformed answer lacks one.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from _lib import backbone
from _lib import document_keys as keys

#: The document version this reading understands (the CLI reference, "friction
#: artefacts"). A later backbone raises it only when a key or a value of a set goes,
#: and no key or value comes to mean anything else; the reading refuses a version
#: other than this one.
SCHEMA_VERSION = 1

ARGV = ("pkit", "friction", "artefacts", "--json")

#: The key of an artefact's type in the document, added within its version 1
#: (COR-056 point 6): a backbone that answers without it predates types.
TYPE_KEY = "type"

#: The key of every declared type in the document, added with an artefact's
#: type: present even where the places hold no artefact.
TYPES_KEY = "types"

#: The documentation roots, by audience (COR-049 point 1). A root of another
#: audience is one this capability serves no space in, so it is not read.
AUDIENCES = ("user", "internal")

#: Who declares a place: the project, the backbone for its rule-set folder, or a
#: capability, `capability:<name>`. Any other is a source this reading does not know.
PROJECT, BACKBONE, CAPABILITY_SOURCE = "project", "backbone", "capability:"

#: What an artefact is: a whole document, or an entry of a collection file.
DOCUMENT, ENTRY = "document", "entry"

#: The kinds of anchor whose part a page's mentions stand on. The answer may list
#: an anchor of another kind; a reader skips it (the CLI reference, `part_anchors`).
PART_KINDS = frozenset({"artefact", "record"})

Runner = Callable[..., subprocess.CompletedProcess[str]]


class Unreadable(Exception):
    """The backbone's read command gave no document this reading understands."""


@dataclass(frozen=True)
class DeclaredPlace:
    """One place of the document: where it is declared and what it reaches.

    `index` is its position in the document's `places`, by which a file names
    the places matching it. `location` and `location_path` are the capability
    documentation location it lies inside, if it names one; `encloses` the
    audiences of the roots it reaches whole, of those in `AUDIENCES`: a root of
    another audience holds no space of this capability's. `rule_sets` is whether
    it holds rule sets, as the answer's `rule_sets` marks it (COR-051 point 2): a
    rule-set folder, or a declared place whose path has a `rule-sets` segment.
    """

    index: int
    source: str  # "project", "capability:<name>" or "backbone"
    declared: bool  # declared in `friction.places`, not a rule-set folder
    pointer: str
    written: str | None
    location: str | None
    location_path: str | None
    encloses: frozenset[str]
    type: str | None = None  # the type it gives, in full, or `None` (COR-056 point 3)
    rule_sets: bool = False

    @property
    def is_project(self) -> bool:
        return self.declared and self.source == "project"

    @property
    def capability(self) -> str | None:
        """The capability that declares it, for a capability's place."""
        return capability_of(self.source)


@dataclass(frozen=True)
class Document:
    """One Markdown file a place matches: the places matching it, whether it is a
    rule-set file, whether `friction.exclude` leaves it out, its front matter's
    own fields (`None` without a front-matter mapping), and — for a document a
    component holds, which no place walks (COR-050 point 1) — the capability
    holding it.

    `anchored` is whether the file's friction block, read as one document,
    lists an anchor, and `unanchored_because` the reason it gives for listing
    none — the reason a person accepted it with none (COR-050 point 1); both as
    the backbone reads them. `anchored` is `None` when the file is no one
    document artefact — a collection file, or a held document.

    `types` holds every type the file's artefacts take, or count as while a
    tie stands, as the backbone resolves them (COR-056 points 3 and 6): one at
    most for a document, each entry's for a collection file, none for a file
    no typed place types. `ranked` is the places matching the file in the
    order COR-056 point 3 sets, each `(place, rank)`, places that rank equal
    sharing a rank; `None` for a file that holds no artefact, whose places the
    backbone does not rank. `in_scope_of` is the rule-set files whose scope
    covers the file's one document artefact (COR-051 point 2)."""

    path: str
    places: tuple[int, ...]
    rule_set: bool
    excluded: bool
    fields: Mapping[str, Any] | None
    held_by: str | None = None
    anchored: bool | None = None
    unanchored_because: str | None = None
    types: tuple[str, ...] = ()
    ranked: tuple[tuple[int, int], ...] | None = None
    in_scope_of: tuple[str, ...] = ()


@dataclass(frozen=True)
class Part:
    """One anchor of an artefact that names a part of a file, as the backbone
    resolves it: an entry's section, a document's section or its lead, or a
    record's point (COR-050 point 2). `span` is the lines the part spans,
    `(first, last)` counted from 1, or `None` where it spans none."""

    kind: str
    value: str
    path: str
    span: tuple[int, int] | None


@dataclass(frozen=True)
class Artefact:
    """One artefact the places hold, as the backbone reads it: its file, its id,
    whether it is an entry of a collection file or a rule of a rule set rather
    than a whole document, the anchors its friction block lists by kind — every
    kind, in written order — the reason it gives for listing none,
    `unanchored_because` (COR-050 point 1), and its own fields, the container
    left out (a rule's carry its cited origin).

    Its type, as the backbone resolves it (COR-056 point 6): `type`, or every
    type it counts as while a tie stands (`conflict`), the places matching its
    file in the core's order with each one's rank (`ranked`), and the paths of
    the rule-set files whose scope covers it (`in_scope_of`).

    What its anchors resolve to, as the backbone resolves them: each anchor of a
    kind in `PART_KINDS` that names a part of a file, with the lines it spans
    (`parts`), and each path anchor with the files it stands on (`standing`)."""

    path: str
    id: str
    entry: bool
    rule: bool
    anchors: Mapping[str, tuple[str, ...]]
    unanchored_because: str | None
    fields: Mapping[str, Any]
    type: str | None = None
    conflict: tuple[str, ...] = ()
    ranked: tuple[tuple[int, int], ...] = ()
    in_scope_of: tuple[str, ...] = ()
    parts: tuple[Part, ...] = ()
    standing: Mapping[str, tuple[str, ...]] = field(default_factory=dict)

    @property
    def types(self) -> tuple[str, ...]:
        """The type it takes, or each it counts as while a tie stands."""
        return (self.type,) if self.type is not None else self.conflict

    @property
    def anchored(self) -> bool:
        """Whether its friction block lists an anchor."""
        return any(self.anchors.values())


@dataclass(frozen=True)
class Reading:
    """The backbone's answer: the roots by audience, the places, the documents by
    path — the files the places read, and the documents components hold — and
    every artefact in them."""

    roots: Mapping[str, str]
    places: tuple[DeclaredPlace, ...]
    documents: Mapping[str, Document]
    artefacts: tuple[Artefact, ...] = ()


def read_artefacts(root: Path, run: Runner = backbone.run) -> Reading:
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
    """The `pkit friction artefacts --json` document as a Reading. Raises Unreadable
    for a version other than this reading's, and for an answer it cannot tell
    anything from at a key it reads (ADR-097 point 3): the key missing, null where
    the CLI reference does not print it null, of another type, or a value it does
    not know."""
    version = document.get("schema_version")
    if type(version) is not int or version != SCHEMA_VERSION:
        raise Unreadable(
            f"`{' '.join(ARGV)}` answered schema_version {version!r}; "
            f"this capability reads {SCHEMA_VERSION}"
        )
    try:
        return _reading(document)
    except keys.Untold as exc:
        raise Unreadable(
            f"`{' '.join(ARGV)}` answered a document this capability cannot read: {exc}"
        ) from exc


def _reading(document: Mapping[str, Any]) -> Reading:
    roots = _roots(document)
    places = tuple(
        _place(index, where, entry)
        for index, (where, entry) in enumerate(keys.objects(document, "places", ""))
    )
    listed = keys.objects(document, "artefacts", "")
    if TYPES_KEY not in document or any(TYPE_KEY not in entry for _where, entry in listed):
        raise Unreadable(
            f"`{' '.join(ARGV)}` answered without each artefact's type and ranked places; "
            f"this capability reads them (COR-056 point 6), so the backbone needs upgrading"
        )
    keys.mapping(document, TYPES_KEY, "")
    artefacts = tuple(_artefact(where, entry) for where, entry in listed)
    # A file is one document artefact unless it is a collection file, whose
    # entries are artefacts of their own. Every artefact of one file shares its
    # matching places, ranked by the file's path.
    whole = {artefact.path: artefact for artefact in artefacts if not artefact.entry}
    of_file: dict[str, list[Artefact]] = {}
    for artefact in artefacts:
        of_file.setdefault(artefact.path, []).append(artefact)
    documents: dict[str, Document] = {}
    for where, entry in keys.objects(document, "files", ""):
        path = keys.text(entry, "path", where)
        artefact = whole.get(path)
        found = of_file.get(path, [])
        documents[path] = Document(
            path=path,
            places=keys.numbers(entry, "places", where),
            rule_set=keys.number_or_null(entry, "rule_set", where) is not None,
            excluded=keys.flag(entry, "excluded", where),
            fields=keys.mapping_or_null(entry, "fields", where),
            anchored=artefact.anchored if artefact is not None else None,
            unanchored_because=artefact.unanchored_because if artefact is not None else None,
            types=tuple(sorted({named for each in found for named in each.types})),
            ranked=found[0].ranked if found else None,
            in_scope_of=artefact.in_scope_of if artefact is not None else (),
        )
    # A held document is walked by no place, so it is never among the files; it
    # carries the places matching it and the held folder holding it, whose
    # declaration names its owner (COR-050 point 1).
    owners = [_holder(where, entry) for where, entry in keys.objects(document, "held", "")]
    for where, entry in keys.objects(document, "held_files", ""):
        path = keys.text(entry, "path", where)
        folder = keys.number(entry, "held", where)
        if not 0 <= folder < len(owners):
            raise keys.Untold(f"`{where}.held` is {folder}, which names no folder of `held`")
        documents[path] = Document(
            path=path,
            places=keys.numbers(entry, "places", where),
            rule_set=False,
            excluded=False,
            fields=keys.mapping_or_null(entry, "fields", where),
            held_by=owners[folder],
        )
    return Reading(roots=roots, places=places, documents=documents, artefacts=artefacts)


def _roots(document: Mapping[str, Any]) -> dict[str, str]:
    """The documentation roots this capability serves spaces in, by audience."""
    found = document.get("roots")
    if not isinstance(found, Mapping) or not all(
        isinstance(found.get(audience), str) for audience in AUDIENCES
    ):
        raise Unreadable(f"`{' '.join(ARGV)}` answered without both documentation roots")
    return {audience: found[audience] for audience in AUDIENCES}


def _artefact(where: str, entry: Mapping[str, Any]) -> Artefact:
    return Artefact(
        path=keys.text(entry, "path", where),
        id=keys.text(entry, "id", where),
        entry=keys.one_of(entry, "kind", where, (DOCUMENT, ENTRY)) == ENTRY,
        rule=keys.number_or_null(entry, "rule_set", where) is not None,
        anchors=_anchors(entry, where),
        unanchored_because=keys.text_or_null(entry, "unanchored_because", where) or None,
        fields=keys.mapping(entry, "fields", where),
        type=keys.text_or_null(entry, TYPE_KEY, where) or None,
        conflict=tuple(
            keys.text(tied, "type", inner)
            for inner, tied in keys.objects(entry, "type_conflict", where)
        ),
        ranked=tuple(
            (keys.number(ranked, "place", inner), keys.number(ranked, "rank", inner))
            for inner, ranked in keys.objects(entry, "ranked_places", where)
        ),
        in_scope_of=keys.texts(entry, "in_scope_of", where),
        parts=tuple(
            part
            for inner, listed in keys.objects(entry, "part_anchors", where)
            if (part := _part(inner, listed)) is not None
        ),
        standing=_standing(entry, where),
    )


def _anchors(entry: Mapping[str, Any], where: str) -> dict[str, tuple[str, ...]]:
    """Its friction block's anchors, by kind: a mapping keyed by data, each kind's
    values as written."""
    listed = keys.mapping(entry, "anchors", where)
    inner = keys.at(where, "anchors")
    return {str(kind): keys.texts(listed, kind, inner) for kind in listed}


def _part(where: str, entry: Mapping[str, Any]) -> Part | None:
    """One part anchor, or `None` for an anchor of a kind no mention stands on."""
    kind = keys.text(entry, "kind", where)
    if kind not in PART_KINDS:
        return None
    span = keys.mapping_or_null(entry, "span", where)
    inner = keys.at(where, "span")
    lines = (
        None
        if span is None
        else (keys.number(span, "first_line", inner), keys.number(span, "last_line", inner))
    )
    return Part(kind, keys.text(entry, "value", where), keys.text(entry, "path", where), lines)


def _standing(entry: Mapping[str, Any], where: str) -> dict[str, tuple[str, ...]]:
    """Each path anchor's files, by the anchor as written."""
    return {
        keys.text(anchor, "value", inner): keys.texts(anchor, "files", inner)
        for inner, anchor in keys.objects(entry, "path_anchors", where)
    }


def capability_of(source: str) -> str | None:
    """The capability a declaration's `source` names — `capability:<name>` — or `None`."""
    return source[len(CAPABILITY_SOURCE) :] if source.startswith(CAPABILITY_SOURCE) else None


def _source(entry: Mapping[str, Any], where: str) -> str:
    """Who declares the place: `project`, `backbone` or `capability:<name>`."""
    source = keys.text(entry, "source", where)
    if source in (PROJECT, BACKBONE) or capability_of(source):
        return source
    raise keys.Untold(
        f"`{keys.at(where, 'source')}` is {source!r}, a source this reading does not know"
    )


def _holder(where: str, entry: Mapping[str, Any]) -> str:
    """The capability that declares a folder of held documents."""
    source = keys.text(entry, "source", where)
    holder = capability_of(source)
    if not holder:
        raise keys.Untold(f"`{keys.at(where, 'source')}` is {source!r}, which names no capability")
    return holder


def _place(index: int, where: str, entry: Mapping[str, Any]) -> DeclaredPlace:
    location = keys.mapping_or_null(entry, "location", where)
    inner = keys.at(where, "location")
    return DeclaredPlace(
        index=index,
        source=_source(entry, where),
        declared=keys.flag(entry, "declared", where),
        pointer=keys.text(entry, "pointer", where),
        written=keys.text_or_null(entry, "written", where),
        location=None if location is None else keys.text(location, "name", inner),
        location_path=None if location is None else keys.text(location, "path", inner),
        encloses=frozenset(keys.texts(entry, "encloses", where)) & frozenset(AUDIENCES),
        type=keys.text_or_null(entry, "type", where) or None,
        rule_sets=keys.mapping_or_null(entry, "rule_sets", where) is not None,
    )
