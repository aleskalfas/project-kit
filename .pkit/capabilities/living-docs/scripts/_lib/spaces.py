"""living-docs' checks over a project's documentation spaces (DEC-001 points 1, 2 and 4).

What is checked, each against the record's words:

- **Places and their assignment** (point 1). A root is a default place of the
  space it serves; a project place inside a root belongs to that root's space
  unless assigned elsewhere; a project place **outside every root** that holds
  a document nothing else claims is assigned to exactly one declared space in
  this capability's project configuration — its absence is an error, and so is
  an assignment naming a place the backbone configuration's `friction.places`
  does not declare, or a space nobody declares. A project place **equal to or
  enclosing a root** is refused. Where places nest the most specific wins; a
  file two project places claim with equal specificity is an error.
- **What is never a page** (points 1 and 4). A decision record and a rule-set
  file are anchor targets; a document in another component's place, or in a
  folder of held documents another component declares (COR-050 point 1), is
  that component's; a document in this capability's definitions location is
  its own artefact. None is a page, and one that carries a page's fields says
  it is one, which is an error — except in the definitions location, where the
  templates carry them by design.
- **Pages** (point 4). A document is a page when it carries the `reader` and
  `kind` fields; they are validated by this capability's companion schema,
  `schemas/page.schema.json`. The friction block in the container is the
  core's, and the backbone's `friction` pass validates it. A document that
  nothing claims and that carries neither field is an **unclassified
  document**, counted for onboarding (point 8) and never failed.
- **Pages left unanchored** (point 8). Onboarding is complete when no page is
  left unanchored without an accepted reason: a page whose friction block
  lists no anchor is counted, and listed, unless the block gives the reason a
  person accepted it with none — its `unanchored-because`, the core's key
  (COR-050 point 1) — which is counted apart. Both as the backbone reads the
  block; an excluded page is in neither (COR-050 point 7). Never failed.
- **Page formats** (point 3; RS-LDOC-004). A page whose kind declares its
  structure — the sections its body carries, in order where order matters, in
  this capability's `schemas/page-kinds.yaml` — is checked against it. While
  the rule is accepted in the shared method, a section the page lacks or
  carries out of order is an error; under any other status the rule binds
  nothing and no body is checked (`SEVERITY_OF_STATUS`). A kind that declares
  no structure is reported with the pages that name it, never failed. A
  declaration that gives no reading is one error, "structures unreadable", and
  no body is checked; a page whose body cannot be read is an error of its own.
  `formats` says what a section is.
- **Readers** (points 4 and 7). Each page's `reader` resolves against the
  readers point, `pkit::documentation:readers`, read as it resolves (`readers`)
  — only when some page names a well-formed reader. A reader the point does not
  hold fails the page, naming the readers it holds. An unresolved point — a
  filler out of step, under the point's `fail` policy — is one error, "readers
  unresolved", never one per page: no reader can be checked against it.
- **Entry points** (point 1). Each space's entry point resolves to a document
  of that space — under its root, or in a place assigned to it — and is not
  another component's, a record or a rule set. Whether it is already a page
  is shown, not failed, until onboarding makes it one.
- **Definitions** (point 2). Each space's definition lies in the definitions
  location's `rule-sets/` folder, where the backbone reads it as a project
  rule set, and inherits the shared method, `living-docs:LDOC`. A space
  without one yet is reported.
- **Separation** (point 1). Roots that are the same folder, or nested, are
  reported for onboarding to clear, never failed.

**Where the documents are is read, never computed here.** The roots, every
place the project and each capability declares, the files each one matches and
each file's front matter are the backbone's artefact discovery, read once
through `pkit friction artefacts --json` (`artefacts`). What this module
decides over that answer is DEC-001's: which of several matching places wins,
the space a place serves, and what a document is.

A page's body is read from the working tree, at the path the backbone names.

**Not here.** A synced tree declared as a place is the backbone's finding,
under `friction` — such a file is not among the documents a place matches; the
friction block and the rule sets themselves are the backbone's `friction` and
`rule-sets` passes; an unresolved readers point is also the backbone's finding,
under `connections`, which names its fix.

`pages` answers which documents are pages without reading the readers point:
the doc-check filler asks it while the backbone resolves every point, so it
must not ask the backbone for one. Reading the places resolves no point.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from _lib import formats
from _lib.artefacts import Document, Unreadable, read_artefacts
from _lib.declarations import (
    BACKBONE_CONFIG,
    CAPABILITIES_DIR,
    CAPABILITY,
    INTERNAL_ROOT,
    LDOC_FILE,
    LIVING_DOCS_CONFIG,
    USER_ROOT,
    Declarations,
    ProjectPlace,
    has_wildcard,
    is_markdown_file,
    is_within,
    literal_prefix,
    literal_text_prefix,
    normalise,
    pointer_token,
    read_declarations,
)
from _lib.readers import READERS_POINT, Readers, filler_path, read_readers

#: The spaces every project has, and the root each one's new pages go under (DEC-001 point 1).
USER_SPACE = "user"
TECHNICAL_SPACE = "technical"
SPACE_OF_ROOT = {USER_ROOT: USER_SPACE, INTERNAL_ROOT: TECHNICAL_SPACE}

#: A page's own fields (DEC-001 point 4): what makes a document a page.
PAGE_FIELDS = ("reader", "kind")

#: This capability's companion schema for a page's own fields.
PAGE_SCHEMA = Path(__file__).resolve().parents[2] / "schemas" / "page.schema.json"

#: Where each page kind's structure is declared: the file, and the path a message names.
PAGE_KINDS = Path(__file__).resolve().parents[2] / formats.PAGE_KINDS
PAGE_KINDS_PATH = f"{CAPABILITIES_DIR}/{CAPABILITY}/{formats.PAGE_KINDS.as_posix()}"

#: The shared method rule set a space's definition inherits (DEC-001 point 2).
LDOC_PIN = re.compile(rf"^{re.escape(CAPABILITY)}:LDOC@(?:0|[1-9][0-9]*)$")

#: A decision record's own id, in the four id-spaces of the decision-record
#: specification: COR, PRJ, ADR and a capability's DEC.
RECORD_ID = re.compile(r"^(?:COR|PRJ|ADR|DEC)-[0-9]{3,}$")

#: The folder of the definitions location the spaces' definitions live in, where
#: the backbone reads them as project rule sets (COR-051 point 2).
RULE_SETS = "rule-sets"

ERROR, REPORT = "error", "report"

#: What a rule's status makes of a departure from it (COR-051 point 4): an
#: accepted rule binds, and checks enforce it; a rule of any other status — a
#: rule without one is proposed — binds nothing, so nothing is checked.
SEVERITY_OF_STATUS = {"accepted": ERROR}


@dataclass(frozen=True)
class Finding:
    severity: str
    location: str
    message: str

    def as_json(self) -> dict[str, str]:
        return {"severity": self.severity, "location": self.location, "message": self.message}


@dataclass
class Outcome:
    """What the check answers: summary lines, findings, the unclassified documents, and
    the pages left unanchored — without an accepted reason, and apart from them those
    accepted with one, each with its reason (DEC-001 point 8)."""

    summary: list[str] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    unclassified: list[str] = field(default_factory=list)
    unanchored: list[str] = field(default_factory=list)
    accepted_unanchored: list[tuple[str, str]] = field(default_factory=list)

    @property
    def errors(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == ERROR]

    def document(self) -> dict[str, Any]:
        """The findings document a validator answers with (ADR-058)."""
        return {"summary": self.summary, "findings": [f.as_json() for f in self.findings]}


# --- places -----------------------------------------------------------------


@dataclass(frozen=True)
class Place:
    """A place a space's pages are found in: a root, or a project place.

    `audience` names the root a root place is — `None` when the two roots are
    one folder, so its space is undetermined until they are separated.
    """

    pattern: str
    project: ProjectPlace | None = None
    audience: str | None = None

    def specificity(self, path: str) -> tuple[int, int]:
        """Most specific wins (DEC-001 point 1): an exact file beats a directory, a
        directory a glob; the longer directory prefix, the longer literal prefix of a
        glob; any project place beats a root, and the nested root the outer one."""
        if self.project is None:
            return (0, len(_parts(self.pattern)))
        if has_wildcard(self.pattern):
            return (1, len(literal_text_prefix(self.pattern)))
        if self.pattern == path:
            return (3, 0)
        return (2, len(_parts(self.pattern)))


#: A place of the spaces with the indices of the backbone's places it stands
#: for — the files those places match are the files it reaches.
Reach = tuple[frozenset[int], Place]


def _parts(path: str) -> tuple[str, ...]:
    return () if path == "." else tuple(path.split("/"))


def root_places(decl: Declarations) -> list[Reach]:
    """The two roots as places, each standing for this capability's place that is
    the root; one place when they are the same folder."""
    of = {
        audience: frozenset(i for i, root in decl.root_places.items() if root == audience)
        for audience in (USER_ROOT, INTERNAL_ROOT)
    }
    if decl.user_root == decl.internal_root:
        return [(of[USER_ROOT] | of[INTERNAL_ROOT], Place(decl.user_root))]
    return [
        (of[USER_ROOT], Place(decl.user_root, audience=USER_ROOT)),
        (of[INTERNAL_ROOT], Place(decl.internal_root, audience=INTERNAL_ROOT)),
    ]


def root_space(path: str, decl: Declarations) -> str | None:
    """The space of the root `path` lies in — the nested one when roots nest;
    `None` outside every root, or when the two roots are one folder."""
    inside = [(aud, root) for aud, root in decl.roots().items() if is_within(path, root)]
    if not inside:
        return None
    if len(inside) == 2 and decl.user_root == decl.internal_root:
        return None
    audience, _root = max(inside, key=lambda item: len(_parts(item[1])))
    return SPACE_OF_ROOT[audience]


def in_root(place: ProjectPlace, decl: Declarations) -> bool:
    prefix = literal_prefix(place.path)
    return any(is_within(prefix, root) for root in decl.roots().values())


# --- what claims a document -------------------------------------------------


@dataclass(frozen=True)
class Claim:
    """Why a document is not a page of any space: whose artefact it is.

    `held` marks another component's claim through a folder of held documents
    rather than a place: the document is that component's, but not an artefact.
    """

    kind: str  # "definition", "component", "rule-set", "record"
    by: str  # the claimant, for a message
    held: bool = False

    def described(self) -> str:
        if self.held:
            return f"a document {self.by} holds in a folder it declares (COR-050 point 1)"
        return {
            "definition": f"an artefact of {CAPABILITY}'s definitions location ({self.by})",
            "component": f"an artefact of {self.by}, which declares the place it is in",
            "rule-set": "a rule-set file, an anchor target (COR-051)",
            "record": f"a decision record ({self.by}), an anchor target (COR-050)",
        }[self.kind]


def claim_of(rel: str, document: Document, decl: Declarations) -> Claim | None:
    """Who claims `rel`, if it is not a page; `None` when nothing does (DEC-001 points 1
    and 4). Another component claims it when a place or a folder of held documents
    it declares holds it (COR-050 point 1); it is a rule-set file when the
    backbone's location rule claims it (COR-051 point 2)."""
    if decl.definitions is not None and is_within(rel, decl.definitions):
        return Claim("definition", decl.definitions)
    if document.held_by is not None:
        return Claim("component", document.held_by, held=True)
    for index in document.places:
        component = decl.component_places.get(index)
        if component is not None:
            return Claim("component", component)
    if document.rule_set:
        return Claim("rule-set", rel)
    record = document.fields.get("id") if document.fields is not None else None
    if isinstance(record, str) and RECORD_ID.match(record):
        return Claim("record", record)
    return None


# --- the check ----------------------------------------------------------------


@dataclass
class _Walk:
    """One pass over the documents of the spaces' places."""

    space_of: dict[str, str | None] = field(default_factory=dict)  # unclaimed document -> space
    claims: dict[str, Claim] = field(default_factory=dict)
    pages: dict[str, str | None] = field(default_factory=dict)  # page -> space
    readers: dict[str, str] = field(default_factory=dict)  # page -> its well-formed reader
    kinds: dict[str, str] = field(default_factory=dict)  # page -> its well-formed kind
    holds: dict[int, str] = field(
        default_factory=dict
    )  # project place index -> a document it holds
    ties: dict[tuple[int, int], list[str]] = field(default_factory=dict)


def check(root: Path, read: Callable[[], Readers] = read_readers) -> Outcome:
    """Every check of this module over the project at `root`; `read` answers the
    readers point, asked only when some page names a well-formed reader. When
    the backbone gives no reading of the places, that is the one finding."""
    try:
        decl, refused, walk, outcome = _classify(root)
    except Unreadable as exc:
        return _unreadable(exc)
    _assignment_findings(decl, refused, walk, outcome)
    _tie_findings(decl, walk, outcome)
    entry_notes = _entry_point_findings(root, decl, walk, outcome)
    definition_notes = _definition_findings(decl, outcome)
    _separation_findings(decl, outcome)
    reader_note = _reader_findings(decl, walk, read, outcome)
    format_note = _format_findings(root, decl, walk, outcome)
    outcome.summary = _summary(
        decl, walk, entry_notes, definition_notes, (reader_note, format_note), outcome
    )
    return outcome


def pages(root: Path) -> list[str]:
    """The pages of the project's spaces, sorted — what the walk classifies as a
    page, by the rules above, without reading the readers point. Raises
    Unreadable when the backbone gives no reading of the places."""
    _decl, _refused, walk, _outcome = _classify(root)
    return sorted(walk.pages)


def _classify(root: Path) -> tuple[Declarations, set[int], _Walk, Outcome]:
    """The declarations, the refused project places, and the walk over every
    document the spaces' places reach, with the findings the walk makes."""
    decl = read_declarations(root, read_artefacts(root))
    outcome = Outcome()
    refused = _refused_places(decl, outcome)
    places: list[Reach] = [
        *root_places(decl),
        *(
            (frozenset({p.index}), Place(p.path, project=p))
            for p in decl.project_places
            if p.index not in refused
        ),
    ]
    return decl, refused, _walk(decl, places, outcome), outcome


def _unreadable(exc: Unreadable) -> Outcome:
    """The answer when the places cannot be read: one error, and nothing checked."""
    outcome = Outcome()
    outcome.findings.append(
        Finding(
            ERROR,
            BACKBONE_CONFIG,
            f"the documentation places cannot be read — {str(exc).rstrip('.')}. No space is "
            f"checked until they can: {CAPABILITY} reads the roots, the places and the "
            f"documents in them through the backbone's `pkit friction artefacts --json` "
            f"(DEC-001 point 1).",
        )
    )
    outcome.summary = ["places unreadable: no space checked.", "1 error(s), 0 report(s)."]
    return outcome


def known_spaces(decl: Declarations) -> list[str]:
    """The spaces of the project: the two every project has, then those it adds."""
    return list(dict.fromkeys([USER_SPACE, TECHNICAL_SPACE, *decl.spaces]))


def _refused_places(decl: Declarations, outcome: Outcome) -> set[int]:
    """Project places equal to or enclosing a root: refused (DEC-001 point 1)."""
    refused: set[int] = set()
    for place in decl.project_places:
        enclosed = [
            f"the {audience} root {root!r}"
            for audience, root in decl.roots().items()
            if audience in place.encloses
        ]
        if not enclosed:
            continue
        refused.add(place.index)
        outcome.findings.append(
            Finding(
                ERROR,
                f"{BACKBONE_CONFIG}:{place.pointer}",
                f"project place {place.written!r} is equal to or encloses "
                f"{' and '.join(enclosed)}; a root is already a default place of its space, "
                f"which {CAPABILITY} declares, so a project place never equals or encloses one "
                f"— narrow it to the documents it means, or remove it (DEC-001 point 1).",
            )
        )
    return refused


def _walk(decl: Declarations, places: Sequence[Reach], outcome: Outcome) -> _Walk:
    """Classify every document the spaces' places reach, and validate the pages."""
    walk = _Walk()
    schema = Draft202012Validator(json.loads(PAGE_SCHEMA.read_text(encoding="utf-8")))
    for rel, document in sorted(decl.documents.items()):
        matching = frozenset(document.places)
        matched = [place for indices, place in places if indices & matching]
        if not matched:
            continue
        front = document.fields
        declared = [name for name in PAGE_FIELDS if front is not None and name in front]
        claim = claim_of(rel, document, decl)
        if claim is not None:
            walk.claims[rel] = claim
            if declared and claim.kind != "definition":
                outcome.findings.append(
                    Finding(
                        ERROR,
                        f"{rel}:/{declared[0]}",
                        f"{rel} carries a page's {_fields(declared)} but is {claim.described()}; "
                        f"what another component or schema claims is never a page — remove "
                        f"{_fields(declared)} (DEC-001 points 1 and 4).",
                    )
                )
            continue
        winner = _most_specific(rel, matched, walk)
        space = _space_of_place(winner, decl)
        if winner.project is not None:
            walk.holds.setdefault(winner.project.index, rel)
        walk.space_of[rel] = space
        if declared:
            walk.pages[rel] = space
            _anchoring(rel, document, outcome)
            findings, invalid = _page_findings(rel, front or {}, schema)
            outcome.findings.extend(findings)
            reader = (front or {}).get("reader")
            if isinstance(reader, str) and "reader" not in invalid:
                walk.readers[rel] = reader
            kind = (front or {}).get("kind")
            if isinstance(kind, str) and "kind" not in invalid:
                walk.kinds[rel] = kind
        elif not document.excluded:
            # Excluded paths are left out of the measures (COR-050 point 7).
            outcome.unclassified.append(rel)
    return walk


def _anchoring(rel: str, document: Document, outcome: Outcome) -> None:
    """A page left unanchored: without an accepted reason, onboarding's work still to
    do; with one — the block's `unanchored-because` — accepted, apart (DEC-001 point
    8; COR-050 point 1). An excluded page is left out, as the measures leave it out
    (COR-050 point 7), and one whose anchoring the backbone does not say is not
    judged."""
    if document.excluded or document.anchored is not False:
        return
    if document.unanchored_because is None:
        outcome.unanchored.append(rel)
    else:
        outcome.accepted_unanchored.append((rel, document.unanchored_because))


def _most_specific(rel: str, matched: Sequence[Place], walk: _Walk) -> Place:
    ranked = sorted(matched, key=lambda place: place.specificity(rel), reverse=True)
    best = ranked[0]
    for other in ranked[1:]:
        if other.specificity(rel) != best.specificity(rel):
            break
        if best.project is not None and other.project is not None:
            low, high = sorted((best.project.index, other.project.index))
            walk.ties.setdefault((low, high), []).append(rel)
    return best


def _space_of_place(place: Place, decl: Declarations) -> str | None:
    if place.project is None:
        return SPACE_OF_ROOT.get(place.audience) if place.audience is not None else None
    assigned = decl.assigned(place.project.path)
    if assigned is not None:
        return assigned
    return root_space(literal_prefix(place.project.path), decl)


def _page_findings(
    rel: str, front: Mapping[str, Any], schema: Draft202012Validator
) -> tuple[list[Finding], set[str]]:
    """A page's own fields against the companion schema (DEC-001 point 4): the
    findings, and the fields the schema refuses."""
    findings: list[Finding] = []
    invalid: set[str] = set()
    for error in sorted(
        schema.iter_errors(dict(front)), key=lambda e: list(map(str, e.absolute_path))
    ):
        if error.absolute_path:
            invalid.add(str(error.absolute_path[0]))
        pointer = "/".join(pointer_token(segment) for segment in error.absolute_path)
        location = f"{rel}:/{pointer}" if pointer else rel
        findings.append(
            Finding(
                ERROR,
                location,
                f"{error.message} — a page names its reader and its kind, each a word "
                f"(`[a-z][a-z0-9-]*`), in the fields {CAPABILITY}'s schema fixes "
                f"(schemas/page.schema.json; DEC-001 point 4).",
            )
        )
    return findings, invalid


def _reader_findings(
    decl: Declarations, walk: _Walk, read: Callable[[], Readers], outcome: Outcome
) -> str:
    """Each page's reader resolves against the readers point (DEC-001 points 4 and 7).
    Returns the summary's line about it."""
    if not walk.readers:
        return f"readers: no page names one yet, so {READERS_POINT} is not read."
    readers = read()
    if not readers.resolved:
        outcome.findings.append(
            Finding(
                ERROR,
                READERS_POINT,
                f"readers unresolved — {readers.why.rstrip('.')}. No page's reader can be "
                f"checked until "
                f"the point resolves; `pkit validate` names the fix under `connections` "
                f"(DEC-001 point 7; COR-052 point 6).",
            )
        )
        return f"readers unresolved: {len(walk.readers)} page reader(s) not checked."
    known = set(readers.ids)
    for rel, reader in sorted(walk.readers.items()):
        if reader in known:
            continue
        outcome.findings.append(
            Finding(
                ERROR,
                f"{rel}:/reader",
                f"{rel} is for reader {reader!r}, which does not resolve: the readers point "
                f"{READERS_POINT} holds {list(readers.ids)} — name one of them, or add "
                f"{reader!r} to the point in the project's filler, "
                f"{filler_path(decl.internal_root)} (DEC-001 points 4 and 7).",
            )
        )
    return (
        f"readers ({READERS_POINT}): {', '.join(readers.ids) or 'none'}; "
        f"{len(walk.readers)} page reader(s) checked."
    )


def _format_findings(root: Path, decl: Declarations, walk: _Walk, outcome: Outcome) -> str:
    """Each page's body against the structure its kind declares (DEC-001 point 3;
    RS-LDOC-004), at the severity the rule's status in the shared method gives:
    an error while the rule is accepted, and under any other status no body is
    checked. A kind that declares no structure is reported, never failed; a
    declaration that gives no reading is one error. Returns the summary's line
    about it."""
    rule = formats.FORMAT_RULE
    entry = decl.ldoc_rules.get(rule)
    if not isinstance(entry, Mapping):
        return f"page formats: not checked — {LDOC_FILE} holds no {rule}."
    status = entry.get("status")
    status = status if isinstance(status, str) and status else "proposed"
    severity = SEVERITY_OF_STATUS.get(status)
    if severity is None:
        return (
            f"page formats: not checked — {rule} is {status}, so it binds nothing "
            f"(COR-051 point 4)."
        )
    try:
        structures = formats.read_structures(PAGE_KINDS)
    except formats.Unreadable as exc:
        outcome.findings.append(
            Finding(
                ERROR,
                PAGE_KINDS_PATH,
                f"structures unreadable — {str(exc).rstrip('.')}. No page's body is checked "
                f"until the page kinds' structures can be read: the file is {CAPABILITY}'s own, "
                f"never the project's to edit — restore it as the capability ships it "
                f"(DEC-001 point 3).",
            )
        )
        return "page formats: structures unreadable, so no page's body is checked."
    checked = departing = unreadable = 0
    undeclared: dict[str, list[str]] = {}
    for rel, kind in sorted(walk.kinds.items()):
        structure = structures.get(kind)
        if structure is None:
            undeclared.setdefault(kind, []).append(rel)
            continue
        try:
            text = (root / rel).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            unreadable += 1
            outcome.findings.append(Finding(ERROR, rel, _unread_message(rel, kind, exc)))
            continue
        checked += 1
        found = formats.departures(formats.headings(text), structure)
        departing += 1 if found else 0
        outcome.findings.extend(
            Finding(severity, rel, _departure_message(rel, kind, structure, departure))
            for departure in found
        )
    outcome.findings.extend(
        Finding(REPORT, f"{rels[0]}:/kind", _undeclared_message(kind, rels, sorted(structures)))
        for kind, rels in sorted(undeclared.items())
    )
    unchecked = sum(len(rels) for rels in undeclared.values())
    return (
        f"page formats ({rule}, {status}): {checked} page(s) checked against the structure "
        f"their kind declares in {PAGE_KINDS_PATH}, {departing} departing from it; "
        f"{unchecked} page(s) not checked, of {len(undeclared)} kind(s) that declare no structure"
        + (f"; {unreadable} page(s) that cannot be read" if unreadable else "")
        + "."
    )


def _departure_message(
    rel: str, kind: str, structure: formats.Structure, departure: formats.Departure
) -> str:
    section = departure.section.described()
    if departure.how == formats.MISSING:
        problem = f"lacks {section} at the start of a line"
        fix = (
            "add it; a heading that is underlined, written in HTML, indented, empty or a "
            "template's unfilled `<placeholder>` is not read"
        )
    else:
        problem = f"carries {section} out of order, at line {departure.line}"
        fix = "move the section into that order"
    return (
        f"{rel}, a page of kind {kind!r}, {problem}: the structure its kind declares is "
        f"{structure.described()} ({PAGE_KINDS_PATH}) — {fix}. A page may carry other sections "
        f"besides (RS-LDOC-004)."
    )


def _undeclared_message(kind: str, rels: Sequence[str], declared: Sequence[str]) -> str:
    return (
        f"kind {kind!r} declares no structure, so the body of the {len(rels)} page(s) that "
        f"name it is not checked: {', '.join(rels)}. {PAGE_KINDS_PATH} declares "
        f"{list(declared)} — name one of them where a page is of that kind; a kind the "
        f"project adds is reported, never failed (DEC-001 point 3)."
    )


def _unread_message(rel: str, kind: str, exc: Exception) -> str:
    why = exc.strerror if isinstance(exc, OSError) and exc.strerror else "it is not UTF-8 text"
    return (
        f"{rel}, a page of kind {kind!r}, cannot be read ({why}), so its body is not checked "
        f"against the structure its kind declares (RS-LDOC-004)."
    )


def _assignment_findings(
    decl: Declarations, refused: set[int], walk: _Walk, outcome: Outcome
) -> None:
    """Every out-of-root project place holding a document nothing else claims is
    assigned, and every assignment names a declared place and space (DEC-001 point 1)."""
    spaces = known_spaces(decl)
    for place in decl.project_places:
        if place.index in refused or in_root(place, decl) or decl.assigned(place.path) is not None:
            continue
        held = walk.holds.get(place.index)
        if held is None:
            continue
        outcome.findings.append(
            Finding(
                ERROR,
                f"{BACKBONE_CONFIG}:{place.pointer}",
                f"project place {place.written!r} lies outside every documentation root and holds "
                f"a document nothing else claims ({held}), but {LIVING_DOCS_CONFIG} assigns it to "
                f"no space: add `{place.written}: <space>` under `places` there, naming one of "
                f"{spaces} (DEC-001 point 1).",
            )
        )
    declared = {place.path for place in decl.project_places}
    first: dict[str, str] = {}
    for assignment in decl.assignments:
        written, space = assignment.written, assignment.space
        location = f"{LIVING_DOCS_CONFIG}:/places/{pointer_token(written)}"
        if assignment.path in first:
            outcome.findings.append(
                Finding(
                    ERROR,
                    location,
                    f"assigns {written!r}, the place already assigned as "
                    f"{first[assignment.path]!r}: both name {assignment.path!r} once normalised, "
                    f"and a place is assigned to exactly one space — keep one entry (DEC-001 "
                    f"point 1).",
                )
            )
            continue
        first[assignment.path] = written
        if assignment.path not in declared:
            outcome.findings.append(
                Finding(
                    ERROR,
                    location,
                    f"assigns {written!r}, which `friction.places` in {BACKBONE_CONFIG} does not "
                    f"declare; a place is declared there and assigned here, joined by its path — "
                    f"declare it, or remove the assignment (DEC-001 point 1).",
                )
            )
        if space not in spaces:
            outcome.findings.append(
                Finding(
                    ERROR,
                    location,
                    f"assigns {written!r} to space {space!r}, which is not a space of this project "
                    f"(spaces: {spaces}); declare it under `spaces`, or assign the place to one of "
                    f"them (DEC-001 point 1).",
                )
            )


def _tie_findings(decl: Declarations, walk: _Walk, outcome: Outcome) -> None:
    """A file claimed by two project places of equal specificity (DEC-001 point 1)."""
    by_index = {place.index: place for place in decl.project_places}
    for (first, second), files in sorted(walk.ties.items()):
        a, b = by_index[first], by_index[second]
        more = f" and {len(files) - 1} other file(s)" if len(files) > 1 else ""
        outcome.findings.append(
            Finding(
                ERROR,
                f"{BACKBONE_CONFIG}:{b.pointer}",
                f"project places {a.written!r} and {b.written!r} both claim {files[0]}{more} with "
                f"equal specificity, so no one place wins; narrow one of the declarations "
                f"(DEC-001 point 1).",
            )
        )


def _entry_point_findings(
    root: Path, decl: Declarations, walk: _Walk, outcome: Outcome
) -> dict[str, str]:
    """Each space's entry point resolves to a document of that space (DEC-001 point 1).
    Returns a note per space for the summary."""
    notes: dict[str, str] = {}
    for space, config in decl.spaces.items():
        if config.entry_point is None:
            continue
        entry = normalise(config.entry_point)
        location = f"{LIVING_DOCS_CONFIG}:/spaces/{pointer_token(space)}/entry-point"
        problem: str | None = None
        if entry not in decl.documents and not is_markdown_file(root, entry):
            problem = "is not a Markdown document of the working tree"
        elif entry in walk.claims:
            problem = f"is {walk.claims[entry].described()}, never a page"
        elif entry not in walk.space_of:
            problem = (
                "lies in no place of any space — under neither documentation root, and in no "
                f"project place of `friction.places` in {BACKBONE_CONFIG}"
            )
        elif walk.space_of[entry] != space:
            owner = walk.space_of[entry]
            problem = (
                f"belongs to space {owner!r}, by its root or its assignment"
                if owner is not None
                else "belongs to no space: its place is unassigned, or both roots are one folder"
            )
        if problem is not None:
            outcome.findings.append(
                Finding(
                    ERROR,
                    location,
                    f"the entry point of space {space!r}, {config.entry_point!r}, {problem}; a "
                    f"space's entry point is a page of that space, under its root or in a place "
                    f"assigned to it (DEC-001 point 1).",
                )
            )
            notes[space] = f"entry point {entry} (unresolved)"
        else:
            page = "a page" if entry in walk.pages else "not yet a page"
            notes[space] = f"entry point {entry}, {page}"
    return notes


def _definition_findings(decl: Declarations, outcome: Outcome) -> dict[str, str]:
    """Each space's definition is a project rule set in the definitions location that
    inherits the shared method (DEC-001 point 2). Returns a note per space."""
    notes: dict[str, str] = {}
    folder = f"{decl.definitions}/{RULE_SETS}" if decl.definitions is not None else None
    pin = f"{CAPABILITY}:LDOC@{_ldoc_major(decl)}"
    for space in known_spaces(decl):
        config = decl.spaces.get(space)
        if config is None or config.definition is None:
            where = f"under `{folder}/`" if folder is not None else "in the technical space"
            outcome.findings.append(
                Finding(
                    REPORT,
                    f"{LIVING_DOCS_CONFIG}:/spaces/{pointer_token(space)}",
                    f"space {space!r} has no definition yet: its rules — a project rule set "
                    f"inheriting {pin}, {where} — are written on first use, from "
                    f"{CAPABILITIES_DIR}/{CAPABILITY}/templates/space-definition.md, and named "
                    f"as the space's `definition` (DEC-001 point 2).",
                )
            )
            notes[space] = "no definition yet"
            continue
        definition = normalise(config.definition)
        location = f"{LIVING_DOCS_CONFIG}:/spaces/{pointer_token(space)}/definition"
        problem: str | None = None
        if folder is None:
            problem = f"cannot be placed: {CAPABILITY}'s package declares no definitions location"
        elif not is_within(definition, folder):
            problem = (
                f"lies outside {folder}/, where the spaces' definitions live and the backbone "
                f"reads them as rule sets (COR-051 point 2)"
            )
        elif definition not in decl.documents:
            # The definitions' folder is a place this capability declares, so a
            # definition that is a document of the working tree is among them.
            problem = "is not a Markdown document of the working tree"
        elif not _inherits_ldoc(decl.documents[definition].fields):
            problem = f"does not inherit the shared method: add `{pin}` to its `inherits`"
        if problem is not None:
            outcome.findings.append(
                Finding(
                    ERROR,
                    location,
                    f"the definition of space {space!r}, {config.definition!r}, {problem} "
                    f"(DEC-001 point 2).",
                )
            )
            notes[space] = f"definition {definition} (unresolved)"
        else:
            notes[space] = f"definition {definition}"
    return notes


def _inherits_ldoc(front: Mapping[str, Any] | None) -> bool:
    inherits = front.get("inherits") if front is not None else None
    return isinstance(inherits, list) and any(
        isinstance(pin, str) and LDOC_PIN.match(pin.strip()) for pin in inherits
    )


def _ldoc_major(decl: Declarations) -> str:
    """The shared method's major, from its own rule-set file: what a definition pins."""
    version = decl.ldoc_version
    match = re.match(r"(0|[1-9][0-9]*)\.", version) if version is not None else None
    return match.group(1) if match else "<major>"


def _separation_findings(decl: Declarations, outcome: Outcome) -> None:
    """The two spaces are separate: neither root lies inside the other (DEC-001 point 1).
    Reported for onboarding to clear, never failed."""
    user, internal = decl.user_root, decl.internal_root
    if user == internal:
        state = f"both documentation roots are {user!r}"
    elif is_within(user, internal) or is_within(internal, user):
        state = f"the documentation roots {user!r} and {internal!r} nest"
    else:
        return
    outcome.findings.append(
        Finding(
            REPORT,
            f"{BACKBONE_CONFIG}:/docs",
            f"{state}, so the user and technical spaces are not separate yet: user-facing "
            f"navigation must never lead into technical material, and neither root lies inside "
            f"the other — onboarding separates them (DEC-001 points 1 and 8).",
        )
    )


def _summary(
    decl: Declarations,
    walk: _Walk,
    entry_notes: Mapping[str, str],
    definition_notes: Mapping[str, str],
    page_notes: Sequence[str],
    outcome: Outcome,
) -> list[str]:
    spaces = known_spaces(decl)
    assigned = sum(1 for place in decl.project_places if decl.assigned(place.path) is not None)
    definitions = f"; definitions under {decl.definitions}/" if decl.definitions else ""
    config = "" if decl.config_exists else f"; no {LIVING_DOCS_CONFIG} yet"
    lines = [
        f"{len(spaces)} space(s); roots {decl.user_root}/ (user) and {decl.internal_root}/ "
        f"(internal); {len(decl.project_places)} project place(s), {assigned} assigned"
        f"{definitions}{config}."
    ]
    for space in spaces:
        notes = [n for n in (entry_notes.get(space), definition_notes.get(space)) if n]
        count = sum(1 for page_space in walk.pages.values() if page_space == space)
        lines.append(f"{space}: {count} page(s); " + "; ".join(notes or ["no entry point"]) + ".")
    by_kind = {
        kind: sum(1 for c in walk.claims.values() if c.kind == kind)
        for kind in ("record", "rule-set", "component", "definition")
    }
    lines.append(
        f"not pages: {by_kind['record']} decision record(s), {by_kind['rule-set']} rule-set "
        f"file(s), {by_kind['component']} of another component, {by_kind['definition']} in the "
        f"definitions location; {len(outcome.unclassified)} unclassified document(s) for "
        f"onboarding (DEC-001 point 4)."
    )
    lines.extend(page_notes)
    lines.append(
        f"pages unanchored: {len(outcome.unanchored)} without an accepted reason, "
        f"{len(outcome.accepted_unanchored)} accepted with one (`unanchored-because`); "
        f"onboarding leaves none without (DEC-001 point 8)."
    )
    errors = len(outcome.errors)
    lines.append(f"{errors} error(s), {len(outcome.findings) - errors} report(s).")
    return lines


def _fields(names: Sequence[str]) -> str:
    return " and ".join(f"`{name}`" for name in names)
