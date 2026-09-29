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
  file are anchor targets; a document in another component's place is that
  component's; a document in this capability's definitions location is its
  own artefact. None is a page, and one that carries a page's fields says it
  is one, which is an error — except in the definitions location, where the
  templates carry them by design.
- **Pages** (point 4). A document is a page when it carries the `reader` and
  `kind` fields; they are validated by this capability's companion schema,
  `schemas/page.schema.json`. The friction block in the container is the
  core's, and the backbone's `friction` pass validates it. A document that
  nothing claims and that carries neither field is an **unclassified
  document**, counted for onboarding (point 8) and never failed.
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

**Not here.** A synced tree declared as a place is the backbone's finding,
under `friction`; the friction block and the rule sets themselves are the
backbone's `friction` and `rule-sets` passes. **Reader resolution is
dormant**: a page's `reader` is checked for its shape only, until the readers
point `pkit::documentation:readers` ships and names the readers it resolves to.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any

from jsonschema import Draft202012Validator

from _lib.declarations import (
    BACKBONE_CONFIG,
    CAPABILITIES_DIR,
    CAPABILITY,
    INTERNAL_ROOT,
    LIVING_DOCS_CONFIG,
    USER_ROOT,
    Declarations,
    ProjectPlace,
    is_glob,
    is_within,
    literal_prefix,
    literal_text_prefix,
    markdown_listing,
    matches,
    normalise,
    pointer_token,
    read_declarations,
    read_front_matter,
)

#: The spaces every project has, and the root each one's new pages go under (DEC-001 point 1).
USER_SPACE = "user"
TECHNICAL_SPACE = "technical"
SPACE_OF_ROOT = {USER_ROOT: USER_SPACE, INTERNAL_ROOT: TECHNICAL_SPACE}

#: A page's own fields (DEC-001 point 4): what makes a document a page.
PAGE_FIELDS = ("reader", "kind")

#: This capability's companion schema for a page's own fields.
PAGE_SCHEMA = Path(__file__).resolve().parents[2] / "schemas" / "page.schema.json"

#: The shared method rule set a space's definition inherits (DEC-001 point 2).
LDOC_FILE = Path(__file__).resolve().parents[2] / "rule-sets" / "ldoc.md"
LDOC_PIN = re.compile(rf"^{re.escape(CAPABILITY)}:LDOC@(?:0|[1-9][0-9]*)$")

#: The readers point whose shipping wakes reader resolution (DEC-001 point 7).
READERS_POINT = "pkit::documentation:readers"

#: A decision record's own id, in the four id-spaces of the decision-record
#: specification: COR, PRJ, ADR and a capability's DEC.
RECORD_ID = re.compile(r"^(?:COR|PRJ|ADR|DEC)-[0-9]{3,}$")

#: The folder name that makes a Markdown file a rule-set file (COR-051 point 2),
#: and the signpost such a folder may hold, which is not one.
RULE_SETS = "rule-sets"
SIGNPOST = "README.md"

#: Probes for "a place equal to or enclosing a root": a place encloses a root
#: when it reaches a document directly in the root and one three folders deep.
_PROBES = ("__living-docs-probe__.md", "__a__/__b__/__living-docs-probe__.md")

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
    """What the check answers: summary lines, findings, and the unclassified documents."""

    summary: list[str] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    unclassified: list[str] = field(default_factory=list)

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
        if is_glob(self.pattern):
            return (1, len(literal_text_prefix(self.pattern)))
        if self.pattern == path:
            return (3, 0)
        return (2, len(_parts(self.pattern)))


def _parts(path: str) -> tuple[str, ...]:
    return () if path == "." else tuple(path.split("/"))


def root_places(decl: Declarations) -> list[Place]:
    """The two roots as places; one place when they are the same folder."""
    if decl.user_root == decl.internal_root:
        return [Place(decl.user_root)]
    return [
        Place(decl.user_root, audience=USER_ROOT),
        Place(decl.internal_root, audience=INTERNAL_ROOT),
    ]


def encloses(pattern: str, root: str) -> bool:
    """Whether a place is the root or encloses it: it reaches every document in it."""
    return all(matches(pattern, f"{root}/{probe}") for probe in _PROBES)


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
    """Why a document is not a page of any space: whose artefact it is."""

    kind: str  # "definition", "component", "rule-set", "record"
    by: str  # the claimant, for a message

    def described(self) -> str:
        return {
            "definition": f"an artefact of {CAPABILITY}'s definitions location ({self.by})",
            "component": f"an artefact of {self.by}, which declares the place it is in",
            "rule-set": "a rule-set file, an anchor target (COR-051)",
            "record": f"a decision record ({self.by}), an anchor target (COR-050)",
        }[self.kind]


def claim_of(rel: str, front: Mapping[str, Any] | None, decl: Declarations) -> Claim | None:
    """Who claims `rel`, if it is not a page; `None` when nothing does (DEC-001 points 1 and 4)."""
    if decl.definitions is not None and is_within(rel, decl.definitions):
        return Claim("definition", decl.definitions)
    for place in decl.component_places:
        if matches(place.pattern, rel):
            return Claim("component", place.component)
    if _is_rule_set_file(rel, decl):
        return Claim("rule-set", rel)
    record = front.get("id") if front is not None else None
    if isinstance(record, str) and RECORD_ID.match(record):
        return Claim("record", record)
    return None


def _is_rule_set_file(rel: str, decl: Declarations) -> bool:
    """The backbone's location rule for a project rule set (COR-051 point 2): in the
    internal root's `rule-sets/`, or in a project place whose path has that segment.
    A capability's own `rule-sets/` is its place, claimed before this."""
    if PurePosixPath(rel).name == SIGNPOST:
        return False
    if is_within(rel, f"{decl.internal_root}/{RULE_SETS}"):
        return True
    return any(
        RULE_SETS in _parts(place.path) and matches(place.path, rel)
        for place in decl.project_places
    )


# --- the check ----------------------------------------------------------------


@dataclass
class _Walk:
    """One pass over the documents of the spaces' places."""

    listing: set[str]
    space_of: dict[str, str | None] = field(default_factory=dict)  # unclaimed document -> space
    claims: dict[str, Claim] = field(default_factory=dict)
    pages: dict[str, str | None] = field(default_factory=dict)  # page -> space
    holds: dict[int, str] = field(
        default_factory=dict
    )  # project place index -> a document it holds
    ties: dict[tuple[int, int], list[str]] = field(default_factory=dict)


def check(root: Path) -> Outcome:
    """Every check of this module over the project at `root`."""
    decl = read_declarations(root)
    outcome = Outcome()
    refused = _refused_places(decl, outcome)
    places = [
        *root_places(decl),
        *(Place(p.path, project=p) for p in decl.project_places if p.index not in refused),
    ]
    walk = _walk(root, decl, places, outcome)
    _assignment_findings(decl, refused, walk, outcome)
    _tie_findings(decl, walk, outcome)
    entry_notes = _entry_point_findings(decl, walk, outcome)
    definition_notes = _definition_findings(root, decl, walk, outcome)
    _separation_findings(decl, outcome)
    outcome.summary = _summary(decl, walk, entry_notes, definition_notes, outcome)
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
            if encloses(place.path, root)
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


def _walk(root: Path, decl: Declarations, places: Sequence[Place], outcome: Outcome) -> _Walk:
    """Classify every document the spaces' places reach, and validate the pages."""
    listing = markdown_listing(root)
    walk = _Walk(listing=set(listing))
    schema = Draft202012Validator(json.loads(PAGE_SCHEMA.read_text(encoding="utf-8")))
    for rel in listing:
        matched = [place for place in places if matches(place.pattern, rel)]
        if not matched:
            continue
        front = read_front_matter(root, rel)
        declared = [name for name in PAGE_FIELDS if front is not None and name in front]
        claim = claim_of(rel, front, decl)
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
            outcome.findings.extend(_page_findings(rel, front or {}, schema))
        elif not any(matches(path, rel) for path in decl.exclude):
            # Excluded paths are left out of the measures (COR-050 point 7).
            outcome.unclassified.append(rel)
    return walk


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
) -> list[Finding]:
    """A page's own fields against the companion schema (DEC-001 point 4)."""
    findings: list[Finding] = []
    for error in sorted(
        schema.iter_errors(dict(front)), key=lambda e: list(map(str, e.absolute_path))
    ):
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
    return findings


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


def _entry_point_findings(decl: Declarations, walk: _Walk, outcome: Outcome) -> dict[str, str]:
    """Each space's entry point resolves to a document of that space (DEC-001 point 1).
    Returns a note per space for the summary."""
    notes: dict[str, str] = {}
    for space, config in decl.spaces.items():
        if config.entry_point is None:
            continue
        entry = normalise(config.entry_point)
        location = f"{LIVING_DOCS_CONFIG}:/spaces/{pointer_token(space)}/entry-point"
        problem: str | None = None
        if entry not in walk.listing:
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


def _definition_findings(
    root: Path, decl: Declarations, walk: _Walk, outcome: Outcome
) -> dict[str, str]:
    """Each space's definition is a project rule set in the definitions location that
    inherits the shared method (DEC-001 point 2). Returns a note per space."""
    notes: dict[str, str] = {}
    folder = f"{decl.definitions}/{RULE_SETS}" if decl.definitions is not None else None
    pin = f"{CAPABILITY}:LDOC@{_ldoc_major()}"
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
        elif definition not in walk.listing:
            problem = "is not a Markdown document of the working tree"
        elif not _inherits_ldoc(read_front_matter(root, definition)):
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


def _ldoc_major() -> str:
    """The shared method's major, from its own file: what a definition pins."""
    front = read_front_matter(LDOC_FILE.parent, LDOC_FILE.name)
    version = front.get("version") if front is not None else None
    match = re.match(r"(0|[1-9][0-9]*)\.", version) if isinstance(version, str) else None
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
        pages = sum(1 for page_space in walk.pages.values() if page_space == space)
        lines.append(f"{space}: {pages} page(s); " + "; ".join(notes or ["no entry point"]) + ".")
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
    lines.append(
        f"reader resolution: dormant until the readers point {READERS_POINT} ships — a page's "
        f"reader is checked for its shape only."
    )
    errors = len(outcome.errors)
    lines.append(f"{errors} error(s), {len(outcome.findings) - errors} report(s).")
    return lines


def _fields(names: Sequence[str]) -> str:
    return " and ".join(f"`{name}`" for name in names)
