"""The analysis, as the backbone finds it: which artefact of which kind is where.

Where the analysis lies and what its places hold is computed once, by the
backbone's artefact discovery (ADR-057 point 2): the analysis location — the
recorded one, else the `analysis` sub-path of the internal root (COR-049) —
the places this capability declares inside it, the files each matches, and
each artefact's own fields and anchors. A capability script never imports the
backbone and never walks the places itself, so it reads that answer through
the backbone's reading command, `pkit friction artefacts --json`, at the
working tree or, with `--at`, at one commit (`backbone.read_document`).

What this module decides over the answer is DEC-001's: each place of this
capability holds one kind of artefact (point 2) — the glossary and the actors
are collection files, one keyed entry per artefact; a use case and a journey
are a document each — and a file in a place that holds no artefact of its
kind's shape is a stray the check reports. The revalidation records are not
artefacts: their folder is this capability's folder of held documents (COR-050
point 1), and the records are the files the answer's declaration of that
folder holds. A file the project's `friction.exclude` leaves out is no part of
the analysis, as it is no part of friction (COR-050 point 7): the discovery
marks it `excluded`, and the stamp, the checks and the filler read nothing of
it — only its path is kept, so the history reading leaves it out too
(`_lib/history.py`).
"""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

#: This capability's name, and the documentation location its package declares.
CAPABILITY = "software-analysis"
LOCATION = "analysis"

#: The four kinds of anchored artefact (DEC-001 point 1).
ACTOR, TERM, USE_CASE, JOURNEY = "actor", "term", "use-case", "journey"
KINDS = (ACTOR, TERM, USE_CASE, JOURNEY)

#: The kinds kept as one collection file, an entry per artefact (DEC-001 point 2).
COLLECTIONS = frozenset({ACTOR, TERM})

#: Each kind's id prefix (DEC-001 point 3); use cases and journeys are numbered.
PREFIX = {ACTOR: "ACT", TERM: "TERM", USE_CASE: "UC", JOURNEY: "JRN"}
NUMBERED = frozenset({USE_CASE, JOURNEY})

#: How each kind is named in a message, and how its id is written.
NOUN = {ACTOR: "actor", TERM: "term", USE_CASE: "use case", JOURNEY: "journey"}
ID_SHAPE = {ACTOR: "ACT-<slug>", TERM: "TERM-<slug>", USE_CASE: "UC-NNN", JOURNEY: "JRN-NNN"}

#: A use case's or journey's id with its number in any number of digits — the
#: spellings the id schema refuses included.
_NUMBER = rf"(?P<prefix>{PREFIX[USE_CASE]}|{PREFIX[JOURNEY]})-(?P<number>[0-9]+)"
_ANY_NUMBER = re.compile(rf"^{_NUMBER}$")

#: A file named after the use case or journey it holds, `UC-NNN-<slug>.md`, as the
#: stamp names one: the number, then a hyphen or the extension.
_NAMED = re.compile(rf"^{_NUMBER}(?=[-.])")


def identity(artefact_id: str) -> str:
    """The id `artefact_id` stands for: a use case's or journey's number in its one
    spelling, the one the id schema admits — `UC-0007` stands for `UC-007` — any
    other id as written. The stamp counts a number as held, and the check two
    artefacts as sharing an id, by this, so the two never disagree."""
    return number_in(artefact_id) or artefact_id


def number_in(artefact_id: str) -> str | None:
    """The use case's or journey's number `artefact_id` spells, as `identity` spells
    it; `None` for an id that is no such number."""
    found = _ANY_NUMBER.match(artefact_id)
    return None if found is None else _spelt(found)


def number_of(artefact_id: str) -> int:
    """The number of a use case's or journey's id as `identity` spells it: 7 for `UC-007`."""
    return int(artefact_id.split("-", 1)[1])


def kind_numbered(artefact_id: str) -> str:
    """The kind a use case's or journey's number is of, by its prefix."""
    return JOURNEY if artefact_id.startswith(f"{PREFIX[JOURNEY]}-") else USE_CASE


def id_in_name(path: str) -> str | None:
    """The use case's or journey's id a file's name carries — `UC-007` for
    `…/UC-007-export.md` — as `identity` spells it; `None` for a name carrying none.
    The stamp names each file so, and counts the number a name carries as held
    whatever the file holds — no front matter, one that does not parse, one naming
    no id — so a number is never used again because its file cannot be read."""
    found = _NAMED.match(path.rsplit("/", 1)[-1])
    return None if found is None else _spelt(found)


def _spelt(found: re.Match[str]) -> str:
    return f"{found['prefix']}-{int(found['number']):03d}"


#: The places this capability's package metadata declares (`friction.places`),
#: by the path each is written with inside the analysis location, and the kind
#: each holds. A test holds this table to the package.
KIND_OF_PLACE = {
    "glossary.md": TERM,
    "use-case-model/actors.md": ACTOR,
    "use-case-model/use-cases": USE_CASE,
    "use-case-model/journeys": JOURNEY,
}

#: The revalidation records' folder inside the analysis location. The records
#: describe an act and are not anchored artefacts, so it is not a place: the
#: package declares it as its folder of held documents (`friction.held`), by
#: this path. A test holds this to the package.
REVALIDATIONS = "revalidations"

#: The methodology's front-matter container, and the friction block's keys that
#: lead to an artefact's revalidation marker (COR-050 points 1 and 3).
CONTAINER = "pkit"
REVALIDATED_AT = ("friction", "revalidated", "at")

#: The key an actor or a term nothing embodies carries in its friction block
#: instead of anchors: the reason onboarding accepts it unanchored (DEC-001
#: point 9). The key is the core's (COR-050 point 1): the unanchored measure
#: lists such an artefact apart, and validation refuses it beside anchors.
UNANCHORED_BECAUSE = "unanchored-because"

#: The version of `pkit friction artefacts --json` this reading understands, and
#: the key of each artefact's anchors in it — added within that version, so a
#: backbone that predates it answers the same version without the key.
SCHEMA_VERSION = 1
ANCHORS = "anchors"

#: The key of each artefact's reason for having no anchors in that document,
#: added within its version: a backbone that predates it gives none.
REASON = "unanchored_because"

#: The key of the folders of held documents in that document, each declared as a
#: place is, with the files it holds (COR-050 point 1).
HELD = "held"


class Unreadable(Exception):
    """The backbone gave no document this reading understands."""


@dataclass(frozen=True)
class Artefact:
    """One analysis artefact: its kind, its id (`None` for a document that names
    none), where it is — `path`, and `location`, the path or `path#id` of an
    entry — its own fields, its anchors by kind, and the reason its friction
    block gives for having none (`UNANCHORED_BECAUSE`, whitespace folded, as
    the backbone reads it; `None` when it gives none)."""

    kind: str
    id: str | None
    path: str
    location: str
    entry: bool
    fields: Mapping[str, Any]
    anchors: Mapping[str, tuple[str, ...]]
    unanchored_because: str | None = None

    def anchored_to(self, anchor_kind: str) -> tuple[str, ...]:
        return self.anchors.get(anchor_kind, ())

    @property
    def withdrawn(self) -> bool:
        return self.fields.get("status") == "withdrawn"


@dataclass(frozen=True)
class Stray:
    """A file in one of the places that holds no artefact of the place's kind, and why."""

    kind: str
    path: str
    why: str


@dataclass(frozen=True)
class Analysis:
    """The analysis in one state of the repository.

    `location` is where it lies, repository-relative, and `places` where each
    kind's place resolves — both `None`/empty when the reading holds none of
    this capability's places. `files` is every file in one of the places, and
    the kind its place holds, whatever the file holds; `unreadable` the files
    whose front matter does not parse, each with the backbone's reason. A file
    `friction.exclude` leaves out is in none of these: `excluded` is its path
    alone. `records` are the revalidation records, by path: the files this
    capability's held folder of them holds in the reading — the working tree's
    listing, so a record git ignores is not one, and every Markdown file
    beneath the folder, nested ones included. `records_unheld` says why that
    folder holds nothing, when it does not: the backbone skipped it (its
    validation says why), or the reading declares no such folder.
    """

    location: str | None
    places: Mapping[str, str]
    artefacts: tuple[Artefact, ...]
    strays: tuple[Stray, ...]
    unreadable: Mapping[str, str]
    files: Mapping[str, str]
    records: tuple[str, ...]
    records_unheld: str | None = None
    excluded: frozenset[str] = frozenset()

    def held(self) -> set[str]:
        """Every id this state of the analysis holds, as `identity` spells it: each
        artefact's own id, and each number a use case or journey holds (`numbers`)."""
        return {identity(a.id) for a in self.artefacts if a.id} | set(self.numbers())

    def numbers(self) -> dict[str, set[str]]:
        """Each use case's or journey's number this state holds, as `identity` spells
        it, and the files holding it: by its front matter's id, and by the number a
        file's name carries (`id_in_name`) — so a file whose id cannot be read still
        holds the number its name gives it (DEC-001 point 3)."""
        found: dict[str, set[str]] = defaultdict(set)
        for path, kind in self.files.items():
            if kind in NUMBERED and (named := id_in_name(path)) is not None:
                found[named].add(path)
        for artefact in self.artefacts:
            if artefact.kind in NUMBERED and artefact.id and (own := number_in(artefact.id)):
                found[own].add(artefact.path)
        return dict(found)

    def of_kind(self, kind: str) -> list[Artefact]:
        return [a for a in self.artefacts if a.kind == kind]

    def find(self, artefact_id: str) -> Artefact | None:
        """The first artefact holding `artefact_id`."""
        return next((a for a in self.artefacts if a.id == artefact_id), None)

    def of(self, artefact_id: str, kind: str) -> Artefact | None:
        """The artefact of `kind` holding `artefact_id`, or `None`."""
        found = self.find(artefact_id)
        return found if found is not None and found.kind == kind else None

    def unfit(self, artefact_id: str, kind: str, *, in_force: bool) -> str | None:
        """Why an artefact cannot rest on `artefact_id` as its `kind` — a use case on its
        actor, a journey on its actor and its steps — or `None` when it can.

        What it names is an artefact of the analysis; and an artefact in force rests
        only on artefacts in force, so a withdrawn actor or step is refused to it. A
        withdrawn artefact may name a withdrawn one: it is history, as a revalidation
        record citing a withdrawn artefact is (DEC-001 points 3 and 6). One rule for
        the stamp, which writes artefacts in force, and the check, so the check never
        accepts what the stamp refuses to write."""
        found = self.of(artefact_id, kind)
        if found is None:
            return f"no {NOUN[kind]} {artefact_id} in the analysis"
        if in_force and found.withdrawn:
            return f"{NOUN[kind]} {artefact_id} is withdrawn ({found.location})"
        return None


def analysis_of(document: Mapping[str, Any]) -> Analysis:
    """The `pkit friction artefacts --json` document as the analysis. Raises
    Unreadable for a document this reading does not understand — another
    version, or an artefact of this capability's places without its anchors,
    which reading as none would report every use case as not anchored."""
    if document.get("schema_version") != SCHEMA_VERSION:
        raise Unreadable(
            f"`pkit friction artefacts` answered schema_version "
            f"{document.get('schema_version')!r}; this capability reads {SCHEMA_VERSION}"
        )
    kind_of_place: dict[int, str] = {}
    places: dict[str, str] = {}
    location: str | None = None
    for index, place in enumerate(_mappings(document.get("places"))):
        where = place.get("location")
        if (
            place.get("source") != f"capability:{CAPABILITY}"
            or not place.get("declared")
            or not isinstance(where, Mapping)
            or where.get("name") != LOCATION
        ):
            continue
        kind = KIND_OF_PLACE.get(str(place.get("written")))
        path = place.get("path")
        if kind is None or not isinstance(path, str):
            continue
        kind_of_place[index] = kind
        places[kind] = path
        location = location or _text(where.get("path"))

    records, unheld = _records(document.get(HELD))
    kind_of_file: dict[str, str] = {}
    unreadable: dict[str, str] = {}
    no_front_matter: list[str] = []
    excluded: set[str] = set()
    for entry in _mappings(document.get("files")):
        kinds = [kind_of_place[i] for i in entry.get("places") or [] if i in kind_of_place]
        if not kinds:
            continue
        path = str(entry.get("path"))
        if entry.get("excluded") is True:
            excluded.add(path)
            continue
        kind_of_file[path] = kinds[0]
        reason = entry.get("unreadable")
        if reason is not None:
            unreadable[path] = reason if isinstance(reason, str) else ""
        elif entry.get("fields") is None:
            no_front_matter.append(path)

    artefacts: list[Artefact] = []
    strays: dict[str, Stray] = {
        path: Stray(
            kind_of_file[path],
            path,
            f"has no front matter: every file here is {with_article(kind_of_file[path])}",
        )
        for path in no_front_matter
    }
    for entry in _mappings(document.get("artefacts")):
        path = str(entry.get("path"))
        kind = kind_of_file.get(path)
        if kind is None:
            continue
        if ANCHORS not in entry:
            raise Unreadable(
                f"`pkit friction artefacts` gave {entry.get('location') or path} without the "
                f"`{ANCHORS}` key this capability reads each artefact's anchors from: the "
                f"installed backbone predates it — upgrade it (`pkit upgrade`)"
            )
        if path in strays:
            continue
        is_entry = entry.get("kind") == "entry"
        if is_entry != (kind in COLLECTIONS):
            strays[path] = Stray(kind, path, _misshapen(kind))
            continue
        fields = entry.get("fields")
        fields = fields if isinstance(fields, Mapping) else {}
        own_id = entry.get("id") if is_entry else fields.get("id")
        artefacts.append(
            Artefact(
                kind=kind,
                id=own_id if isinstance(own_id, str) and own_id else None,
                path=path,
                location=str(entry.get("location") or path),
                entry=is_entry,
                fields=fields,
                anchors=_anchors(entry.get(ANCHORS)),
                unanchored_because=_text(entry.get(REASON)),
            )
        )
    return Analysis(
        location=location,
        places=places,
        artefacts=tuple(a for a in artefacts if a.path not in strays),
        strays=tuple(sorted(strays.values(), key=lambda s: s.path)),
        unreadable=unreadable,
        files=kind_of_file,
        records=records,
        records_unheld=unheld,
        excluded=frozenset(excluded),
    )


def _records(held: Any) -> tuple[tuple[str, ...], str | None]:
    """The revalidation records — the files the document's declaration of this
    capability's folder of them holds — and why it holds none, when it holds
    nothing: the backbone skipped it, or the document declares no such folder."""
    for entry in _mappings(held):
        where = entry.get("location")
        if (
            entry.get("source") == f"capability:{CAPABILITY}"
            and entry.get("written") == REVALIDATIONS
            and isinstance(where, Mapping)
            and where.get("name") == LOCATION
        ):
            skipped = entry.get("skipped")
            if isinstance(skipped, Mapping):
                return (), f"the backbone skipped it ({skipped.get('reason')})"
            files = entry.get("files")
            return tuple(sorted(str(f) for f in files)) if isinstance(files, list) else (), None
    return (), "the backbone's reading declares no such folder of this capability's"


def _misshapen(kind: str) -> str:
    if kind in COLLECTIONS:
        return (
            f"is not a collection of {NOUN[kind]}s: each {NOUN[kind]} is an entry of its front "
            f"matter keyed by its id, carrying the `pkit:` container"
        )
    return f"holds keyed entries: each {NOUN[kind]} is a document of its own"


def with_article(kind: str) -> str:
    """The kind's noun with its indefinite article: `an actor`, `a use case`."""
    return f"{'an' if kind == ACTOR else 'a'} {NOUN[kind]}"


def _anchors(value: Any) -> dict[str, tuple[str, ...]]:
    if not isinstance(value, Mapping):
        return {}
    return {
        str(kind): tuple(v for v in values if isinstance(v, str))
        for kind, values in value.items()
        if isinstance(values, list)
    }


def _mappings(value: Any) -> list[Mapping[str, Any]]:
    return [item for item in value if isinstance(item, Mapping)] if isinstance(value, list) else []


def _text(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None
