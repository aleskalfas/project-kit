"""living-docs' checks over a project's documentation spaces (DEC-001 points 1, 2 and 4).

What is checked, each against the record's words:

- **Places and their assignment** (point 1). A root is a default place of the
  space it serves; a project place inside a root belongs to that root's space
  unless assigned elsewhere; a project place **outside every root** that holds
  a document nothing else claims is assigned to exactly one declared space in
  this capability's project configuration — its absence is an error, and so is
  an assignment naming a place the backbone configuration's `friction.places`
  does not declare, or a space nobody declares. A project place **equal to or
  enclosing a root** is refused. Where places nest, the backbone's order
  decides (COR-056 point 3): a document's matching places come ranked in its
  answer, the first root or project place among them gives its space, and a
  file two project places claim at equal rank, ahead of every other, is an
  error. Nothing here ranks a place.
- **The definitions' scopes** (point 1). Where a space's definition carries a
  scope, each page an assigned place gives that space lies in that scope and
  in no other space definition's scope — read from the scopes covering the page
  in the backbone's answer (COR-051 point 2) — and where the definition selects
  by type, an assigned place outside every root gives the page type. A
  definition with no scope selects nothing itself, so nothing joins it.
- **Whose a document is** (points 1 and 4). Each document takes the type the
  backbone gives it (COR-056). A document of another component's type, or one
  another component holds in a folder it declares (COR-050 point 1), or of no
  type in another component's place, is that component's; one of a type the
  project gives is the project's; one of this capability's template type is
  its own; a rule-set file holds rules, and a document whose id reads as a
  decision record's is a decision record. None is a page, and their own fields
  are their owners'. A decision record that would otherwise be a page — of the
  page type, or a page of no type below — is an error.
- **Pages** (point 4). A document is a page when it is of the page type: the
  place that wins for it gives that type and it declares its page kind in
  `kind`. In a project place outside every root that gives no type, a document
  of no type that declares its page kind is a page too. A page's `kind`, and
  its `reader` where RS-LDOC-003 binds on it, are validated by this
  capability's companion schema, `schemas/page.schema.json`. The friction
  block in the container is the core's, and the backbone's `friction` pass
  validates it. Any other document
  in the spaces' places is an **unclassified document**, counted for
  onboarding (point 8) and never failed.
- **Pages left unanchored** (point 8). Onboarding is complete when no page is
  left unanchored without an accepted reason: a page whose friction block
  lists no anchor is counted, and listed, unless the block gives the reason a
  person accepted it with none — its `unanchored-because`, the core's key
  (COR-050 point 1) — which is counted apart. Both as the backbone reads the
  block; an excluded page is in neither (COR-050 point 7). Never failed.
- **Where `LDOC` binds** (point 3). Each check of a part of an `LDOC` rule
  runs only on the pages where that rule binds (COR-051 point 2), read once from
  the backbone's one answer (`binding`, COR-051 point 7). `LDOC` binds only
  through a set of the project's own whose scope selects the page, such as the
  page's space definition. No answer is one error, and then no page's
  structure or reader is checked.
- **Page formats** (point 3; RS-LDOC-004). A page whose kind declares its
  structure — the sections its body carries, in order where order matters, in
  this capability's `schemas/page-kinds.yaml` — is checked against it where
  RS-LDOC-004 binds on it: a section the page lacks or carries out of order is
  an error. Under any status but accepted the rule binds nothing, so the
  backbone's answer names no page, and the summary says why (`_unaccepted`).
  A kind that declares no structure is reported with the pages that name it
  where the rule binds, never failed. The declaration is read only when the
  rule binds on some page, or there is no page and the rule is accepted: then
  one that gives no reading is one error, "structures unreadable", and no body
  is checked. A checked page whose body cannot be read is an error of its own.
  `formats` says what a section is.
- **Readers** (points 3, 4 and 7). Where RS-LDOC-003 binds on a page, the page
  names its reader in `reader`, and the reader resolves against the readers
  point, `pkit::documentation:readers`, read as it resolves (`readers`) — only
  when some such page names a well-formed reader. A reader the point does not
  hold fails the page, naming the readers it holds. An unresolved point — a
  filler out of step, under the point's `fail` policy — is one error, "readers
  unresolved", never one per page: no reader can be checked against it. Where
  RS-LDOC-003 does not bind, the page's `reader` is not read.
- **Entry points** (point 1). Each space's entry point resolves to a document
  of that space — under its root, or in a place assigned to it — and is not
  another component's, a record or a rule set. Whether it is already a page
  is shown, not failed, until onboarding makes it one.
- **Definitions** (point 2). Each space's definition lies in the definitions
  location's `rule-sets/` folder, where the backbone reads it as a project
  rule set, and inherits the shared method, `living-docs:LDOC`. A space
  without one yet is reported, and so is a definition with no scope, or with
  the template's placeholder in its scope, naming the scope that selects the
  space's pages. So is each page of a space its definition's scope leaves
  out, unless the join with the assignment fails it.
- **Separation** (point 1). Roots that are the same folder, or nested, are
  reported for onboarding to clear, never failed.
- **Captured sources** (point 4). The sources folder holds only captured
  sources, each found from its name; a `source` anchor or a rule's cited
  source that no file captures, and a captured source nothing names, are
  reported. `sources` states those checks.

**Where the documents are is read, never computed here.** The roots, every
place the project and each capability declares, the files each one matches,
each file's front matter, each artefact's type, its places in the core's order
and the scopes covering it are the backbone's artefact discovery, read once
through `pkit friction artefacts --json` (`artefacts`). What this module
decides over that answer is DEC-001's: the space a place serves, and what a
document is to the spaces.

A page's body is read from the working tree, at the path the backbone names.

**Not here.** A synced tree declared as a place is the backbone's finding,
under `friction` — such a file is not among the documents a place matches; the
friction block and the rule sets themselves are the backbone's `friction` and
`rule-sets` passes; an unresolved readers point is also the backbone's finding,
under `connections`, which names its fix.

`pages` answers which documents are pages without reading the readers point or
where the rules bind: the doc-check filler asks it while the backbone resolves
every point, so it must not ask the backbone for one. Reading the places
resolves no point.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from _lib import formats, sources
from _lib.artefacts import Document, Unreadable, read_artefacts
from _lib.binding import Binding, read_binding
from _lib.binding import Unreadable as Unbound
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
    is_markdown_file,
    is_within,
    literal_prefix,
    normalise,
    pointer_token,
    read_declarations,
)
from _lib.readers import READERS_POINT, Readers, filler_path, read_readers

#: The spaces every project has, and the root each one's new pages go under (DEC-001 point 1).
USER_SPACE = "user"
TECHNICAL_SPACE = "technical"
SPACE_OF_ROOT = {USER_ROOT: USER_SPACE, INTERNAL_ROOT: TECHNICAL_SPACE}

#: The capability's types (DEC-001 points 2 and 4; COR-056), in full, and the
#: page type's kind field, the field in which a page declares its page kind.
PAGE_TYPE = f"{CAPABILITY}:page"
TEMPLATE_TYPE = f"{CAPABILITY}:template"
KIND_FIELD = "kind"

#: The backbone's own types are written with this owner (COR-056 point 1).
BACKBONE = "backbone"

#: This capability's companion schema for a page's own fields.
PAGE_SCHEMA = Path(__file__).resolve().parents[2] / "schemas" / "page.schema.json"

#: Where each page kind's structure is declared: the file, and the path a message names.
PAGE_KINDS = Path(__file__).resolve().parents[2] / formats.PAGE_KINDS
PAGE_KINDS_PATH = f"{CAPABILITIES_DIR}/{CAPABILITY}/{formats.PAGE_KINDS.as_posix()}"

#: The shared method rule set a space's definition inherits (DEC-001 point 2).
LDOC = f"{CAPABILITY}:LDOC"
LDOC_PIN = re.compile(rf"^{re.escape(LDOC)}@(?:0|[1-9][0-9]*)$")

#: The shared method's rule whose part the reader check enforces: a page names its
#: reader, one the readers point holds (DEC-001 points 3 and 6; RS-LDOC-003).
READER_RULE = "RS-LDOC-003"

#: A decision record's own id, in the four id-spaces of the decision-record
#: specification: COR, PRJ, ADR and a capability's DEC.
RECORD_ID = re.compile(r"^(?:COR|PRJ|ADR|DEC)-[0-9]{3,}$")

#: The folder of the definitions location the spaces' definitions live in, where
#: the backbone reads them as project rule sets (COR-051 point 2).
RULE_SETS = "rule-sets"

ERROR, REPORT = "error", "report"


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
    one folder, so its space is undetermined until they are separated. Where
    places nest, the backbone ranks them (COR-056 point 3); a Place carries no
    order of its own.
    """

    pattern: str
    project: ProjectPlace | None = None
    audience: str | None = None


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
    """Why a document is not a page of any space: whose it is.

    `held` marks another component's claim through a folder of held documents
    rather than a place: the document is that component's, but not an artefact.
    `type` is the type that says whose it is, where one does (COR-056).
    """

    kind: str  # "definition", "component", "project", "rule-set", "record"
    by: str  # the claimant, for a message
    held: bool = False
    type: str | None = None

    def described(self) -> str:
        if self.held:
            return f"a document {self.by} holds in a folder it declares (COR-050 point 1)"
        if self.kind == "component" and self.type is not None:
            return f"of type {self.type}, an artefact of {self.by}"
        return {
            "definition": f"an artefact of {CAPABILITY}'s definitions location ({self.by})",
            "component": f"an artefact of {self.by}, which declares the place it is in",
            "project": f"of type {self.by!r}, which the project gives one of its places",
            "rule-set": "a rule-set file, an anchor target (COR-051)",
            "record": f"a decision record ({self.by}), an anchor target (COR-050)",
        }[self.kind]


def claim_of(rel: str, document: Document, decl: Declarations) -> Claim | None:
    """Whose `rel` is, when the type the backbone gives it, or its holder, says it
    is another owner's (DEC-001 points 1 and 2; COR-056); `None` for a document of
    the page type, or of no type that no other component's place holds.

    A held document is its holder's (COR-050 point 1). A rule-set file holds
    rules (COR-051 point 2): in the definitions location, the spaces'
    definitions. A document of the template type is this capability's own, one
    of another component's type that component's, and one of a bare type the
    project's. Whether a document of no type is a decision record, a page or
    unclassified is the walk's."""
    if document.held_by is not None:
        return Claim("component", document.held_by, held=True)
    if document.rule_set:
        if decl.definitions is not None and is_within(rel, decl.definitions):
            return Claim("definition", decl.definitions)
        return Claim("rule-set", rel)
    types = document.types
    if PAGE_TYPE in types:
        return None
    if TEMPLATE_TYPE in types:
        return Claim("definition", decl.definitions or rel, type=TEMPLATE_TYPE)
    for named in types:
        owner, sep, _name = named.partition(":")
        if not sep:
            return Claim("project", named, type=named)
        if owner == BACKBONE:
            return Claim("rule-set", rel, type=named)
        return Claim("component", owner, type=named)
    for index in document.places:
        component = decl.component_places.get(index)
        if component is not None:
            return Claim("component", component)
    return None


def record_of(document: Document) -> str | None:
    """The decision record `document` is, by its own id (DEC-001 point 4), or `None`."""
    record = document.fields.get("id") if document.fields is not None else None
    return record if isinstance(record, str) and RECORD_ID.match(record) else None


def declares_kind(fields: Mapping[str, Any] | None) -> bool:
    """Whether a document declares its page kind in `kind`, read as the backbone reads
    a kind field (COR-056 point 4): present and not empty. Which kind it names is
    the page schema's to judge."""
    value = fields.get(KIND_FIELD) if fields is not None else None
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, Mapping | list):
        return bool(value)
    return True


# --- the check ----------------------------------------------------------------


@dataclass
class _Walk:
    """One pass over the documents of the spaces' places."""

    space_of: dict[str, str | None] = field(default_factory=dict)  # unclaimed document -> space
    claims: dict[str, Claim] = field(default_factory=dict)
    pages: dict[str, str | None] = field(default_factory=dict)  # page -> space
    giver: dict[str, ProjectPlace] = field(default_factory=dict)  # page -> its project place
    fronts: dict[str, Mapping[str, Any]] = field(default_factory=dict)  # page -> its front matter
    # The pages RS-LDOC-003 binds on, each with its well-formed reader, if it names one.
    readers: dict[str, str] = field(default_factory=dict)
    reader_bound: set[str] = field(default_factory=set)
    kinds: dict[str, str] = field(default_factory=dict)  # page -> its well-formed kind
    holds: dict[int, str] = field(
        default_factory=dict
    )  # project place index -> a document it holds
    ties: dict[tuple[int, int], list[str]] = field(default_factory=dict)
    # A document that holds no artefact, which the backbone ranks no place for,
    # whose places of the spaces would tell it apart -> those places.
    untold: dict[str, list[Place]] = field(default_factory=dict)


def check(
    root: Path,
    read: Callable[[], Readers] = read_readers,
    reach: Callable[[Path], Binding] = read_binding,
) -> Outcome:
    """Every check of this module over the project at `root`; `read` answers the
    readers point, asked only when some page names a well-formed reader where
    RS-LDOC-003 binds, and `reach` where the rules bind, asked only when there is
    a page. When the backbone gives no reading of the places, that is the one
    finding."""
    try:
        decl, refused, walk, outcome = _classify(root)
    except Unreadable as exc:
        return _unreadable(exc)
    binding = _binding(root, walk, reach, outcome)
    _field_findings(walk, binding, outcome)
    _assignment_findings(decl, refused, walk, outcome)
    _tie_findings(decl, walk, outcome)
    _untold_findings(decl, walk, outcome)
    scope_note = _scope_findings(decl, refused, walk, outcome)
    entry_notes = _entry_point_findings(root, decl, walk, outcome)
    definition_notes = _definition_findings(decl, outcome)
    _separation_findings(decl, outcome)
    reader_note = _reader_findings(decl, walk, binding, read, outcome)
    format_note = _format_findings(root, decl, walk, binding, outcome)
    captured = sources.check(root, decl.artefacts)
    outcome.findings.extend(
        Finding(ERROR if problem.error else REPORT, problem.location, problem.message)
        for problem in captured.problems
    )
    outcome.summary = _summary(
        decl,
        walk,
        entry_notes,
        definition_notes,
        (reader_note, format_note, captured.summary, scope_note),
        outcome,
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
    reach = {index: place for indices, place in places for index in indices}
    for rel, document in sorted(decl.documents.items()):
        ordered = _ordered(document, reach)
        if not ordered:
            continue
        claim = claim_of(rel, document, decl)
        if claim is not None:
            walk.claims[rel] = claim
            continue
        front = document.fields
        page = PAGE_TYPE in document.types or _untyped_page(document, ordered[0][1], decl)
        record = record_of(document)
        if record is not None:
            walk.claims[rel] = Claim("record", record)
            if page:
                outcome.findings.append(_record_finding(rel, record, PAGE_TYPE in document.types))
            continue
        if document.ranked is None and len(ordered) > 1:
            # Unranked places all share rank 0, so `_winner` is never asked: it
            # would read every pair of them as a tie.
            told = _told(ordered, decl)
            if told is None:
                walk.untold[rel] = [place for _rank, place in ordered]
                if not document.excluded:
                    outcome.unclassified.append(rel)
                continue
            winner = told
        else:
            winner = _winner(rel, ordered, walk)
        space = _space_of_place(winner, decl)
        if winner.project is not None:
            walk.holds.setdefault(winner.project.index, rel)
        walk.space_of[rel] = space
        if page:
            walk.pages[rel] = space
            if winner.project is not None:
                walk.giver[rel] = winner.project
            _anchoring(rel, document, outcome)
            walk.fronts[rel] = front or {}
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


def _ordered(document: Document, reach: Mapping[int, Place]) -> list[tuple[int, Place]]:
    """The spaces' places matching `document`, each with its rank, in the order the
    backbone gives (COR-056 points 3 and 6): ranked by it, never here. Two root
    places that are one folder stand for one Place, listed once. A file that
    holds no artefact — no front matter the backbone reads — has no ranked places:
    its places come unranked, as the backbone lists them (`_told`)."""
    listed = (
        document.ranked
        if document.ranked is not None
        else tuple((index, 0) for index in document.places)
    )
    ordered: list[tuple[int, Place]] = []
    for index, rank in listed:
        place = reach.get(index)
        if place is not None and all(place is not seen for _rank, seen in ordered):
            ordered.append((rank, place))
    return ordered


def _told(ordered: Sequence[tuple[int, Place]], decl: Declarations) -> Place | None:
    """The place to read a file that holds no artefact under, when its several
    places of the spaces make the order between them moot; `None` when they do
    not, and its space cannot be told.

    The backbone ranks the places of artefacts only, and this capability ranks
    none itself (DEC-001 point 1). The order is moot when every place gives the
    file the same space and none owes an assignment for holding it: none is a
    project place outside every root that no assignment names."""
    spaces = {_space_of_place(place, decl) for _rank, place in ordered}
    owing = any(_owes_assignment(place, decl) for _rank, place in ordered)
    return ordered[0][1] if len(spaces) == 1 and not owing else None


def _owes_assignment(place: Place, decl: Declarations) -> bool:
    """Whether `place` is a project place outside every root with no assignment,
    which owes one for any document nothing else claims (DEC-001 point 1)."""
    project = place.project
    return (
        project is not None and not in_root(project, decl) and decl.assigned(project.path) is None
    )


def _winner(rel: str, ordered: Sequence[tuple[int, Place]], walk: _Walk) -> Place:
    """The first of the spaces' places in the backbone's order: it gives `rel` its
    space (DEC-001 point 1). Project places that share its rank are a tie."""
    rank, best = ordered[0]
    for other_rank, other in ordered[1:]:
        if other_rank != rank:
            break
        if best.project is not None and other.project is not None:
            low, high = sorted((best.project.index, other.project.index))
            walk.ties.setdefault((low, high), []).append(rel)
    return best


def _untyped_page(document: Document, winner: Place, decl: Declarations) -> bool:
    """A page of no type (DEC-001 point 4): a document no place types, whose space a
    project place outside every root that gives no type gives, and that declares
    its page kind in `kind`, as the page type would ask."""
    project = winner.project
    return (
        not document.types
        and project is not None
        and project.type is None
        and not in_root(project, decl)
        and declares_kind(document.fields)
    )


def _record_finding(rel: str, record: str, typed: bool) -> Finding:
    """A decision record that would otherwise be a page (DEC-001 point 4): `typed`
    when it takes the page type, else a page of no type in a project place that
    gives none."""
    would = (
        f"so it takes the type {PAGE_TYPE}, or counts as it in a tie (COR-056 points 3 and 4)"
        if typed
        else "in a project place outside every root that gives no type, so it would be a page"
    )
    return Finding(
        ERROR,
        f"{rel}:/{KIND_FIELD}",
        f"{rel} is a decision record ({record}), an anchor target (COR-050), and declares a "
        f"page kind in `{KIND_FIELD}`, {would}: a decision record is never a page — remove "
        f"`{KIND_FIELD}` (DEC-001 point 4).",
    )


def _space_of_place(place: Place, decl: Declarations) -> str | None:
    if place.project is None:
        return SPACE_OF_ROOT.get(place.audience) if place.audience is not None else None
    assigned = decl.assigned(place.project.path)
    if assigned is not None:
        return assigned
    return root_space(literal_prefix(place.project.path), decl)


def cited(rule: str) -> str:
    """A rule of the shared method, as the backbone's answer cites it (COR-051 point 6)."""
    return f"{CAPABILITY}:{rule}"


def _binding(
    root: Path, walk: _Walk, reach: Callable[[Path], Binding], outcome: Outcome
) -> Binding | None:
    """Where the rules bind on the pages, read once from the backbone's one answer
    (COR-051 point 7; DEC-001 point 3), and only when there is a page. A check of a
    part of a rule runs only where the rule binds (COR-051 point 2). So when the
    answer cannot be read, that is one error, and neither a page's structure nor
    its reader is checked: `None`."""
    if not walk.pages:
        return Binding()
    try:
        return reach(root)
    except Unbound as exc:
        outcome.findings.append(
            Finding(
                ERROR,
                BACKBONE_CONFIG,
                f"where {LDOC}'s rules bind cannot be read — {str(exc).rstrip('.')}. No page's "
                f"structure or reader is checked until it can: {CAPABILITY} checks each part of a "
                f"rule only where the rule binds, read through the backbone's `pkit rule-sets "
                f"reach --json` (DEC-001 point 3; COR-051 point 7).",
            )
        )
        return None


def _field_findings(walk: _Walk, binding: Binding | None, outcome: Outcome) -> None:
    """Each page's own fields against the companion schema (DEC-001 point 4), and its
    reader where RS-LDOC-003 binds on it (point 3): there the page names its reader,
    a word, which `_reader_findings` resolves. Where the rule does not bind, the
    page's `reader` is not read. Records the readers to resolve and the kinds whose
    structure to check."""
    schema = Draft202012Validator(json.loads(PAGE_SCHEMA.read_text(encoding="utf-8")))
    rule = cited(READER_RULE)
    for rel in sorted(walk.pages):
        front = walk.fronts.get(rel, {})
        bound = binding is not None and binding.binds(rel, rule)
        fields = {key: value for key, value in front.items() if bound or key != "reader"}
        findings, invalid = _page_findings(rel, fields, schema)
        outcome.findings.extend(findings)
        kind = front.get("kind")
        if isinstance(kind, str) and "kind" not in invalid:
            walk.kinds[rel] = kind
        if not bound:
            continue
        walk.reader_bound.add(rel)
        reader = front.get("reader")
        if "reader" not in front:
            outcome.findings.append(
                Finding(
                    ERROR,
                    rel,
                    f"{rel} names no reader, and {READER_RULE} binds on it: the page names its "
                    f"reader in its `reader` field, a word that names a reader the readers point "
                    f"holds — add `reader: <id>` (DEC-001 point 3; {READER_RULE}).",
                )
            )
        elif isinstance(reader, str) and "reader" not in invalid:
            walk.readers[rel] = reader


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
                f"{error.message} — a page names its kind, and its reader where "
                f"{READER_RULE} binds on it, each a word (`[a-z][a-z0-9-]*`), in the fields "
                f"{CAPABILITY}'s schema fixes (schemas/page.schema.json; DEC-001 point 4).",
            )
        )
    return findings, invalid


def _reader_findings(
    decl: Declarations,
    walk: _Walk,
    binding: Binding | None,
    read: Callable[[], Readers],
    outcome: Outcome,
) -> str:
    """Each page's reader resolves against the readers point where RS-LDOC-003 binds
    on the page (DEC-001 points 3 and 7). Returns the summary's line about it."""
    if binding is None:
        return f"readers: not checked — where {READER_RULE} binds cannot be read."
    unbound = len(walk.pages) - len(walk.reader_bound)
    if walk.pages and not walk.reader_bound:
        why = _unaccepted(READER_RULE, decl)
        if why is not None:
            return f"readers: not checked — {why}."
        return (
            f"readers: not checked — {READER_RULE} binds on none of the {unbound} page(s), so "
            f"{READERS_POINT} is not read (COR-051 point 7)."
        )
    beyond = f"; {unbound} page(s) {READER_RULE} does not bind on, not checked" if unbound else ""
    if not walk.readers:
        return f"readers: no page names one yet, so {READERS_POINT} is not read{beyond}."
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
        return f"readers unresolved: {len(walk.readers)} page reader(s) not checked{beyond}."
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
        f"{len(walk.readers)} page reader(s) checked{beyond}."
    )


def _format_findings(
    root: Path, decl: Declarations, walk: _Walk, binding: Binding | None, outcome: Outcome
) -> str:
    """Each page's body against the structure its kind declares, where RS-LDOC-004
    binds on the page, as the backbone's answer gives it (DEC-001 point 3; COR-051
    point 7). There a departure is an error. No body is checked on a page the rule
    does not bind on, and under any status but accepted it binds on none. A kind that declares
    no structure is reported, never failed; a declaration that gives no reading is
    one error. Returns the summary's line about it."""
    rule = formats.FORMAT_RULE
    if binding is None:
        return f"page formats: not checked — where {rule} binds cannot be read."
    kinds = {rel: kind for rel, kind in walk.kinds.items() if binding.binds(rel, cited(rule))}
    unbound = sum(1 for rel in walk.pages if not binding.binds(rel, cited(rule)))
    if unbound == len(walk.pages):
        why = _unaccepted(rule, decl)
        if why is not None:
            return f"page formats: not checked — {why}."
        if walk.pages:
            return (
                f"page formats: not checked — {rule} binds on none of the {unbound} page(s) "
                f"(COR-051 point 7): {LDOC} binds only through a set of the project's own whose "
                f"scope selects a page, such as a space's definition (DEC-001 point 2)."
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
    for rel, kind in sorted(kinds.items()):
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
            Finding(ERROR, rel, _departure_message(rel, kind, structure, departure))
            for departure in found
        )
    outcome.findings.extend(
        Finding(REPORT, f"{rels[0]}:/kind", _undeclared_message(kind, rels, sorted(structures)))
        for kind, rels in sorted(undeclared.items())
    )
    unchecked = sum(len(rels) for rels in undeclared.values())
    return (
        f"page formats ({rule}, accepted): {checked} page(s) checked against the structure "
        f"their kind declares in {PAGE_KINDS_PATH}, {departing} departing from it; "
        f"{unchecked} page(s) not checked, of {len(undeclared)} kind(s) that declare no structure"
        + (f"; {unreadable} page(s) that cannot be read" if unreadable else "")
        + (f"; {unbound} page(s) {rule} does not bind on, not checked" if unbound else "")
        + "."
    )


def _unaccepted(rule: str, decl: Declarations) -> str | None:
    """Why a rule of the shared method binds on no page whatever the scopes say, for
    the summary: the shared method holds no such rule, or the rule is not accepted
    (COR-051 point 4). `None` for an accepted rule. Where it binds is the backbone's
    answer alone; this only words why that answer is empty."""
    entry = decl.ldoc_rules.get(rule)
    if not isinstance(entry, Mapping):
        return f"{LDOC_FILE} holds no {rule}"
    status = entry.get("status")
    status = status if isinstance(status, str) and status else "proposed"
    if status == "accepted":
        return None
    return f"{rule} is {status}, so it binds nothing (COR-051 point 4)"


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
    """A file two project places claim at equal rank, ahead of every other place of
    the spaces, in the backbone's order (DEC-001 point 1; COR-056 point 3)."""
    by_index = {place.index: place for place in decl.project_places}
    for (first, second), files in sorted(walk.ties.items()):
        a, b = by_index[first], by_index[second]
        more = f" and {len(files) - 1} other file(s)" if len(files) > 1 else ""
        outcome.findings.append(
            Finding(
                ERROR,
                f"{BACKBONE_CONFIG}:{b.pointer}",
                f"project places {a.written!r} and {b.written!r} both claim {files[0]}{more} at "
                f"equal rank in the backbone's order of places (COR-056 point 3), so no one "
                f"place gives it a space; narrow one of the declarations (DEC-001 point 1).",
            )
        )


def _untold_findings(decl: Declarations, walk: _Walk, outcome: Outcome) -> None:
    """A file that holds no artefact, whose places of the spaces would give it
    different spaces or owe an assignment for it: the backbone ranks no place for
    it, and this capability ranks none itself (DEC-001 point 1), so which place
    holds it cannot be told. Reported, and it is unclassified. Where every one of
    its places owes an assignment, whichever holds it owes one, so that fails."""
    for rel, places in sorted(walk.untold.items()):
        named = ", ".join(_place_named(place) for place in places)
        if all(_owes_assignment(place, decl) for place in places):
            outcome.findings.append(
                Finding(
                    ERROR,
                    rel,
                    f"{rel} lies only in project places outside every documentation root that "
                    f"{LIVING_DOCS_CONFIG} assigns to no space ({named}), and holds a document "
                    f"nothing else claims: whichever of them holds it, that place needs an "
                    f"assignment — assign every one of them to the same space under `places` "
                    f"there, or give the file front matter (DEC-001 point 1).",
                )
            )
            continue
        outcome.findings.append(
            Finding(
                REPORT,
                rel,
                f"{rel} holds no artefact — no front matter the backbone reads — so the "
                f"backbone's answer ranks none of its places ({named}), and which of them "
                f"gives it a space cannot be told: no place holds it and no space counts it "
                f"until it carries front matter (DEC-001 point 1; COR-056 point 6).",
            )
        )


def _place_named(place: Place) -> str:
    if place.project is not None:
        return f"project place {place.project.written!r}"
    return f"the {place.audience} root" if place.audience is not None else "the shared root"


@dataclass(frozen=True)
class _Scope:
    """A space definition's scope, as its front matter writes it (COR-051 point 2):
    the definition, and whether the scope selects by type. Which artefacts it
    covers is the backbone's answer, each page's `in_scope_of`, never read here."""

    definition: str
    by_type: bool


def _scopes(decl: Declarations) -> dict[str, _Scope]:
    """The scope of each space's definition that carries one, by space. A definition
    with no scope selects nothing itself (COR-051 point 2), so it is left out:
    nothing joins it (DEC-001 point 1)."""
    scopes: dict[str, _Scope] = {}
    for space in known_spaces(decl):
        config = decl.spaces.get(space)
        if config is None or config.definition is None:
            continue
        definition = normalise(config.definition)
        document = decl.documents.get(definition)
        if document is None or not document.rule_set:
            continue
        scope = (document.fields or {}).get("scope")
        if isinstance(scope, list) and scope:
            scopes[space] = _Scope(definition, by_type=False)
        elif isinstance(scope, Mapping) and (scope.get("paths") or scope.get("types")):
            types = scope.get("types")
            scopes[space] = _Scope(definition, by_type=isinstance(types, list) and bool(types))
    return scopes


def _scope_findings(decl: Declarations, refused: set[int], walk: _Walk, outcome: Outcome) -> str:
    """The assignment joined with the definitions' scopes (DEC-001 point 1).

    Where a space's definition selects by type, a place outside every root that is
    assigned to the space gives the page type, or the scope misses its pages.
    Each page an assigned place gives a space lies in that space definition's
    scope and in no other's, read from the scopes covering the page in the
    backbone's answer (COR-051 point 2). A definition with no scope joins
    nothing. Returns the summary's line about it."""
    scopes = _scopes(decl)
    untyped: set[int] = set()
    for place in decl.project_places:
        if place.index in refused or in_root(place, decl):
            continue
        space = decl.assigned(place.path)
        scope = scopes.get(space) if space is not None else None
        if scope is None or not scope.by_type or place.type == PAGE_TYPE:
            continue
        untyped.add(place.index)
        gives = f"gives the type {place.type}" if place.type is not None else "names no type"
        outcome.findings.append(
            Finding(
                ERROR,
                f"{BACKBONE_CONFIG}:{place.pointer}",
                f"project place {place.written!r} lies outside every documentation root and is "
                f"assigned to space {space!r}, whose definition, {scope.definition}, selects by "
                f"type, but it {gives}, so that scope misses its pages; give it the page type, "
                f"written `{{path: {place.written}, type: {PAGE_TYPE}}}` in `friction.places` "
                f"(DEC-001 point 1; COR-056 point 2).",
            )
        )
    outside: dict[tuple[str, str], list[str]] = {}
    inside: dict[tuple[str, str], list[str]] = {}
    for rel, place in sorted(walk.giver.items()):
        space = decl.assigned(place.path)
        if space is None:
            continue
        covering = {normalise(path) for path in decl.documents[rel].in_scope_of}
        own = scopes.get(space)
        if own is not None and own.definition not in covering and place.index not in untyped:
            outside.setdefault((place.path, space), []).append(rel)
        for other, scope in scopes.items():
            if other != space and scope.definition in covering:
                inside.setdefault((place.path, other), []).append(rel)
    written = {}
    for assignment in decl.assignments:
        written.setdefault(assignment.path, assignment.written)
    for (path, space), files in sorted(outside.items()):
        definition = scopes[space].definition
        outcome.findings.append(
            Finding(
                ERROR,
                f"{LIVING_DOCS_CONFIG}:/places/{pointer_token(written[path])}",
                f"place {written[path]!r} is assigned to space {space!r} and gives it "
                f"{_files_named(files)}, which the scope of that space's definition, "
                f"{definition}, does not cover: a place assigned to a space lies in that space "
                f"definition's scope — widen the scope to the place, or assign the place to the "
                f"space whose definition covers it (DEC-001 point 1).",
            )
        )
    for (path, other), files in sorted(inside.items()):
        space = decl.assigned(path)
        definition = scopes[other].definition
        outcome.findings.append(
            Finding(
                ERROR,
                f"{LIVING_DOCS_CONFIG}:/places/{pointer_token(written[path])}",
                f"place {written[path]!r} is assigned to space {space!r} and gives it "
                f"{_files_named(files)}, which the scope of space {other!r}'s definition, "
                f"{definition}, also covers: a place assigned to a space lies in no other "
                f"space definition's scope — leave the place out of that scope with its "
                f"`exclude`, or assign the place to that space (DEC-001 point 1).",
            )
        )
    _left_out_findings(decl, walk, scopes, outcome)
    if not scopes:
        return (
            "scopes: no space's definition carries one, so no assigned place is joined with a "
            "scope (DEC-001 point 1)."
        )
    joined = sum(1 for place in walk.giver.values() if decl.assigned(place.path) is not None)
    return (
        f"scopes: {', '.join(sorted(scopes))} — {joined} page(s) of assigned places joined with "
        f"the definitions' scopes; a definition with no scope joins nothing (DEC-001 point 1)."
    )


def _left_out_findings(
    decl: Declarations, walk: _Walk, scopes: Mapping[str, _Scope], outcome: Outcome
) -> None:
    """Each page of a space whose definition carries a scope that leaves the page out
    (DEC-001 point 2): no rule binds on it through the definition. Reported, one
    finding per space, since a scope may leave pages out on purpose; a page an
    assigned place gives is point 1's, which fails it (`_scope_findings`)."""
    left_out: dict[str, list[str]] = {}
    for rel, space in sorted(walk.pages.items()):
        scope = scopes.get(space) if space is not None else None
        if scope is None:
            continue
        giver = walk.giver.get(rel)
        if giver is not None and decl.assigned(giver.path) is not None:
            continue
        covering = {normalise(path) for path in decl.documents[rel].in_scope_of}
        if scope.definition not in covering:
            left_out.setdefault(space, []).append(rel)
    for space, files in sorted(left_out.items()):
        definition = scopes[space].definition
        outcome.findings.append(
            Finding(
                REPORT,
                definition,
                f"the scope of space {space!r}'s definition, {definition}, leaves out "
                f"{_files_named(files)} of the space's pages, so neither {LDOC}'s rules nor the "
                f"space's own bind on them through it (COR-051 point 7). Widen the scope to them — "
                f"its `paths` name the space's root and the places assigned to it, and a "
                f"placeholder such as `<root>` names nothing — or move them to the space they "
                f"belong to. A scope may leave pages out on purpose, with `exclude`, so this is "
                f"reported, never failed (DEC-001 point 2).",
            )
        )


def _files_named(files: Sequence[str]) -> str:
    more = f" and {len(files) - 1} other page(s)" if len(files) > 1 else ""
    return f"{files[0]}{more}"


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
        elif entry in walk.untold:
            told = {_space_of_place(place, decl) for place in walk.untold[entry]}
            if space in told:
                # Not yet a page, and the space it would serve cannot be told
                # until it holds an artefact: reported under the document itself.
                notes[space] = f"entry point {entry}, not yet a page (its space not told)"
                continue
            others = sorted(repr(other) for other in told if other is not None)
            spaces_named = f"other spaces ({', '.join(others)})" if others else ""
            problem = (
                f"lies only in places of {spaces_named}"
                if None not in told
                else "lies only in places of no space"
                + (f" or of {spaces_named}" if others else "")
            )
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
    inherits the shared method, with a scope that selects the space's pages (DEC-001
    point 2). A definition with no scope is reported, naming the scope to give it.
    Returns a note per space."""
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
                    f"inheriting {pin}, scoped to the space's pages, {where} — are written on "
                    f"first use, from "
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
            continue
        notes[space] = f"definition {definition}"
        fields = decl.documents[definition].fields or {}
        if "scope" not in fields:
            outcome.findings.append(
                Finding(REPORT, definition, _no_scope_message(space, definition, decl))
            )
        elif placeholders := _placeholders(fields.get("scope")):
            outcome.findings.append(
                Finding(
                    REPORT,
                    definition,
                    _placeholder_message(space, definition, placeholders, decl),
                )
            )
    return notes


#: A placeholder a template leaves for its writer: words in angle brackets.
PLACEHOLDER = re.compile(r"<[^<>]*>")


def _placeholders(scope: Any) -> list[str]:
    """The paths of a scope, as written, that still hold a template's placeholder."""
    if isinstance(scope, list):
        scope = {"paths": scope}
    if not isinstance(scope, Mapping):
        return []
    return [
        path
        for key in ("paths", "exclude")
        for path in (scope.get(key) if isinstance(scope.get(key), list) else [])
        if isinstance(path, str) and PLACEHOLDER.search(path)
    ]


def _placeholder_message(
    space: str, definition: str, placeholders: Sequence[str], decl: Declarations
) -> str:
    """A scope copied with the template's placeholder: it names no file, so the
    rules reach none of the space's pages through it (DEC-001 point 2)."""
    paths, exclude = _space_paths(space, decl)
    named = ", ".join(f"`{path}`" for path in placeholders)
    fix = (
        f" — `paths: [{', '.join(paths)}]`"
        + (f", `exclude: [{', '.join(exclude)}]`" if exclude else "")
        if paths
        else ""
    )
    return (
        f"the scope of space {space!r}'s definition, {definition}, still holds the template's "
        f"placeholder {named}, which names no file: write the space's root and the places "
        f"assigned to it in its place{fix} (DEC-001 point 2). Until then the join with the "
        f"assignment fails each place assigned to the space that the scope misses (DEC-001 "
        f"point 1)."
    )


def _no_scope_message(space: str, definition: str, decl: Declarations) -> str:
    """A definition with no scope selects no page, so no rule binds through it
    (COR-051 points 2 and 7): reported, naming the scope that selects the space's
    pages (DEC-001 point 2)."""
    paths, exclude = _space_paths(space, decl)
    if paths:
        left_out = f", exclude: [{', '.join(exclude)}]" if exclude else ""
        scope = f"`scope: {{paths: [{', '.join(paths)}]{left_out}, types: [{PAGE_TYPE}]}}`"
    else:
        scope = f"a scope whose `paths` name the space's places, with `types: [{PAGE_TYPE}]`"
    untyped = sorted(
        place.written
        for place in decl.project_places
        if decl.assigned(place.path) == space
        and not in_root(place, decl)
        and place.type != PAGE_TYPE
    )
    typing = (
        f" Give {', '.join(untyped)} the page type in `friction.places` too, as a scope that "
        f"selects by type asks (DEC-001 point 1)."
        if untyped
        else ""
    )
    shared = (
        " The two documentation roots are one folder, so separate them first: each space's "
        "scope then names its own root (DEC-001 point 1)."
        if decl.user_root == decl.internal_root and space in SPACE_OF_ROOT.values()
        else ""
    )
    return (
        f"the definition of space {space!r}, {definition}, carries no scope, so it selects no "
        f"page itself: neither {LDOC}'s rules nor its own reach the space's pages through it, "
        f"nor do the checks of their parts (COR-051 points 2 and 7). Give it the scope of the "
        f"space's pages, {scope} (DEC-001 point 2).{typing}{shared}"
    )


def _space_paths(space: str, decl: Declarations) -> tuple[list[str], list[str]]:
    """The paths that select a space's pages, as a scope writes them, and those it
    leaves out: the space's root, everything beneath it, unless the two roots are
    one folder, then each place assigned to the space outside that root, a root
    nested in it counting as outside. Left out are a root nested in it and each
    place in it assigned to another space."""
    root = next(
        (
            path
            for audience, path in decl.roots().items()
            if SPACE_OF_ROOT[audience] == space and decl.user_root != decl.internal_root
        ),
        None,
    )
    paths = [f"{root}/**"] if root is not None else []
    nested = [
        other
        for other in decl.roots().values()
        if root is not None and other != root and is_within(other, root)
    ]
    exclude = [f"{other}/**" for other in nested]
    for assignment in decl.assignments:
        prefix = literal_prefix(assignment.path)
        inside = (
            root is not None
            and is_within(prefix, root)
            and not any(is_within(prefix, other) for other in nested)
        )
        if assignment.space == space and not inside:
            paths.append(assignment.written)
        elif assignment.space != space and inside:
            exclude.append(assignment.written)
    return paths, exclude


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
        for kind in ("record", "rule-set", "component", "project", "definition")
    }
    lines.append(
        f"not pages: {by_kind['record']} decision record(s), {by_kind['rule-set']} rule-set "
        f"file(s), {by_kind['component']} of another component, {by_kind['project']} of a type "
        f"the project gives, {by_kind['definition']} in the definitions location; "
        f"{len(outcome.unclassified)} unclassified document(s) for onboarding (DEC-001 point 4)."
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
