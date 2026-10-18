"""The validation findings COR-050 point 12 assigns to validation.

Over the artefacts `friction_discovery` finds in the declared places, and the
settings that declare them, this pass reports:

- **a capability place the walk does not follow** — one discovery could not
  read in the package schema's shape `{path, location?, type?, description?}`
  (plain text, no `path`, a location `docs.locations` does not declare, or
  declares in another shape with nothing recorded), or one that leaves the
  repository, through a link included; reported whenever it is declared,
  dormant or not, because a place nothing is found under must never look like
  a place with nothing in it (COR-050 point 7);
- **a place matching a synced copy** — a declared place, the project's or a
  capability's, whose path or glob matches a file the methodology's sync
  writes into the repository, as the tree's ownership predicate judges it
  (`Discovery.synced`); discovery did not walk that file and walked the
  place's other matches. Reported at the place's declaration whenever it is
  declared, dormant or not: a place is never a synced tree (COR-050 point 14);
- **a capability surface entry not read** — `friction.surface` not a list of
  repository-relative paths, or an entry in it that is not a path; reported
  whenever it is declared, for the same reason: a surface nothing is measured
  against must never look like a covered one;
- **a capability held folder not held** — a `friction.held` entry discovery
  could not read in its shape (no `location`, a glob or a path leaving its
  location, or any shape a place could not have), or one that leaves the
  repository, through a link included; it holds nothing, so the places
  matching its documents read them as artefacts. Reported whenever declared,
  dormant or not. A held folder overstepping its bounds — equal to or
  enclosing a root or another declaration's place, sharing files with its own
  place, another held folder or a rule-set folder — is the packages pass's
  finding, at the declaration (`package_validate`);
- **a held document whose front matter does not parse** — a friction block
  in it could not be looked for, so a YAML typo never hides one; and **a
  friction block in a held document**, anywhere in its front matter — a
  document a component holds is not an artefact (COR-050 point 1), so nothing
  reads its anchors or its revalidation. Both reported whenever declared,
  dormant or not (COR-050 point 12);
- **unparsable front matter** in a declared place — reported whenever places
  are declared, dormant or not, because the check never skips an artefact it
  cannot parse: the broken file may be the one carrying the container;
- **mixed line endings** — a file the walk read, a rule-set file's included,
  written with more than one line break (`DiscoveredFile.mixed_line_endings`):
  discovery reads every one as `\\n`, so a carriage return that is part of a
  value would be read as a line break, and no writer could keep the file's
  other bytes; a file written with one, `\\r\\n` included, is read and
  written as a `\\n` file is;
- **a malformed block** — the container fails its schema or the container's
  rule, or a compatible point block fails its provider's point schema;
  delegated to `backbone_schemas.validate_container`, handed what the wiring
  says of the active roles and their data points (`connections.
  container_wiring`, from the one resolution of the run), whose errors are
  surfaced against the artefact (COR-050 point 2, COR-053 point 10);
- **`unanchored-because` beside anchors** — the reason an artefact has no
  anchors, written in a block that lists some: the two contradict each other
  (COR-050 points 1 and 12). The container schema admits the key alone; the
  pair is this pass's own finding, so it reads as what it is rather than as a
  shape error;
- **a dangling deferral** — a `deferred[].anchor` naming, by kind and value,
  no anchor of the artefact (COR-050 point 4);
- **a deferral repeated** — a `deferred[]` entry for an anchor an earlier
  entry already defers, by kind and value: the list holds one entry per
  anchor (COR-050 point 4), so one anchor never carries two reasons;
- **a dangling or repeated revisit, and a link's field that lists no anchor**
  (`_link_findings`) — read with the links the artefact's places declare
  (`Discovery.links`): a `revisited[]` entry naming no target of them, a
  second entry for one target, and a link's field that is no list of texts
  or lists a value no anchor of the artefact has (COR-050 point 16). Entries
  on an artefact whose places declare no link are a **report**, never an
  error: the component that declared it may be uninstalled;
- **an anchor kind nothing resolves** — a kind outside the backbone's three
  that no installed capability registers, or whose registration is refused
  (two registrants, a command without the query contract or naming no leaf),
  as the one anchor-kind registry judges it (`unresolved_kind_reason`;
  ADR-057 point 2). A **report**, never an error (COR-050 points 7 and 12):
  the container schema admits any kind a word names, as the container admits
  a role block with no active provider, and a refused registration fails once,
  at the registration, in the packages pass. This pass runs no resolver;
- **a cycle between artefacts**, with the cycle's path — a cycle has no
  order in which its members could be revalidated (COR-050 point 5). It is
  found along the one edge set truth-chain order reads too
  (`friction_check.upstream_artefacts`): artefact anchors, an anchor on a
  document's section or its lead counting as one on the document, and record
  anchors, whole or on a point, on a record whose file is an artefact. A path
  anchor and an anchor of a registered kind name files, so neither is
  followed. So an anchor on a part of its own artefact is a cycle, as is a
  record's anchor on itself or on one of its own points, said so;
- **a dead or ambiguous anchor on a record's point** (`_PointAnchors`), an
  error: its record does not resolve, holds no point with the id, writes its
  points as a list, or holds two with the id (COR-050 points 7 and 12) — and
  **an anchor on a retired point**, a warning naming the point's successors,
  until it is re-pointed. Each record is read from the working tree through
  `record_points`, the one reading of a record's points (ADR-057 point 2);
- **a dead, ambiguous or refused anchor on a document's section or its lead**
  (`_part_anchor_findings`), an error whatever made it so, its artefact gone
  included: no artefact by its name, no heading with its slug — a renamed
  heading's anchor among them — two headings with it, or a part COR-050
  point 2 refuses, a section or the lead of a collection file, a collection
  entry or a record, naming the anchor to use (COR-050 points 2, 7 and 12).
  Read from the working tree's discovery through `artefact_parts`, the one
  reading of an artefact anchor's part.

These fail validation in either mode, because the project can fix them. A
rule-set file is claimed before the container rule (ADR-056 point 2): its
front matter and each rule's container are the rule-set pass's findings
(`rule_sets`), so this pass reports neither, while its rules still take part
in the beside-anchors, deferral and cycle checks like every artefact. The
project's settings themselves — an invalid `friction.mode`, a place, surface
or exclude path outside the repository — are the configuration pass's findings
(`config_validate`, which owns the file), and a capability's `friction` block
is the packages pass's, which judges its shape but cannot know where a place
resolves; so a capability place the walk does not follow, and a surface entry
it does not read, are reported here too — as is a place of either kind that
matches a synced copy, which only the walk can tell. This pass never walks a
place that leaves the repository, nor a synced copy a declared place matches.
Without the tree's ownership module no match can be told a synced copy; that
is a report, not an error. What it does not do either: compute friction, resolve
path anchors against git, run a registered kind's resolver, or report a dead
path, whole-record or whole-artefact anchor — those are the two checks' findings
(COR-050 points 6 and 7). What the
container validator reports rather than judges — a role block whose role has no
active provider, a point block the active provider's point does not match — is
carried through as reports (never errors) so `pkit validate` can show them.

Dormant until used (COR-050 point 15): with no places declared, or nothing in
them to judge — no artefact carrying the container and no file it failed to
parse — the pass reports nothing but its counts, any capability place the walk
does not follow, any place matching a synced copy, any capability surface
entry it does not read or held folder it does not hold, and any held document
it cannot parse or that carries a friction block.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, cast

from project_kit import backbone_schemas as bs
from project_kit import connections, validators
from project_kit.artefact_parts import PartState, anchored_part
from project_kit.friction_check import (
    Upstream,
    point_problem,
    record_file,
    record_naming,
    upstream_artefacts,
)
from project_kit.friction_discovery import (
    CORE_ANCHOR_KINDS,
    FRICTION_KEY,
    REVISITED_KEY,
    SKIP_OUTSIDE,
    UNANCHORED_BECAUSE_KEY,
    Anchor,
    Artefact,
    Discovery,
    FrictionSettings,
    ResolverCommand,
    RevisitLink,
    SettingsPath,
    UnreadableFile,
    is_inside_repository,
    link_targets,
    link_values,
    registered_anchor_kinds,
    shared_discovery,
    synced_copy_test,
    unresolved_kind_reason,
)
from project_kit.lifecycle_ownership import OWNERSHIP_MODULE
from project_kit.record_points import (
    AnchoredPoint,
    PointState,
    RecordPoints,
    read_points_bytes,
    split_anchor,
    successors_phrase,
)
from project_kit.working_tree import WorkingTree


class Severity(Enum):
    """Whether a finding fails validation (`error`), asks for attention without failing
    (`warning`, an anchor on a retired point), or is only reported (`report`) — COR-050
    points 7 and 12. A container finding keeps the severity the container validator gives
    it (`bs.Severity`), read by its value."""

    ERROR = "error"
    WARNING = "warning"
    REPORT = "report"


class FrictionFindingKind(Enum):
    MALFORMED_PLACE = "malformed-place"  # a capability place not in the schema's shape
    PLACE_OUTSIDE_REPOSITORY = "place-outside-repository"  # a capability place leaving it
    SYNCED_PLACE = "synced-place"  # a place, project or capability, matching a synced copy
    OWNERSHIP_UNAVAILABLE = "ownership-unavailable"  # no predicate to tell a synced copy
    MALFORMED_SURFACE = "malformed-surface"  # a capability surface entry not in the shape
    MALFORMED_HELD = "malformed-held"  # a capability held folder not in its shape
    HELD_OUTSIDE_REPOSITORY = "held-outside-repository"  # a held folder leaving it
    HELD_UNPARSABLE = "held-unparsable-front-matter"  # a held document's front matter
    HELD_BLOCK = "held-friction-block"  # a friction block in a document a component holds
    MALFORMED_BLOCK = "malformed-block"
    UNANCHORED_BESIDE_ANCHORS = "unanchored-beside-anchors"  # the reason for none, and anchors
    UNPARSABLE_FRONT_MATTER = "unparsable-front-matter"
    MIXED_LINE_ENDINGS = "mixed-line-endings"  # a file written with more than one line break
    DANGLING_DEFERRAL = "dangling-deferral"
    DUPLICATE_DEFERRAL = "duplicate-deferral"  # an anchor an earlier entry already defers
    DANGLING_REVISIT = "dangling-revisit"  # a revisit entry naming no target of a link
    ORPHANED_REVISIT = "orphaned-revisit"  # a revisit entry where no place declares a link
    DUPLICATE_REVISIT = "duplicate-revisit"  # a target an earlier revisit entry already names
    MALFORMED_LINK_FIELD = "malformed-link-field"  # a link's field that is no list of texts
    UNANCHORED_TARGET = "unanchored-target"  # a link's field listing a value no anchor has
    UNRESOLVED_KIND = "unresolved-kind"  # an anchor kind nothing installed resolves: a report
    CYCLE = "cycle"
    DEAD_POINT_ANCHOR = "dead-point-anchor"  # an anchor on a record's point that names none
    AMBIGUOUS_POINT_ANCHOR = "ambiguous-point-anchor"  # an id two live points of a record share
    RETIRED_POINT_ANCHOR = "retired-point-anchor"  # an anchor on a point its record retires
    DEAD_SECTION_ANCHOR = "dead-section-anchor"  # a section or lead anchor that names none
    AMBIGUOUS_SECTION_ANCHOR = "ambiguous-section-anchor"  # a slug two headings share
    REFUSED_SECTION_ANCHOR = (
        "refused-section-anchor"  # a section or lead anchor COR-050 point 2 refuses
    )
    CONTAINER_REPORT = "container-report"  # an orphaned role block, an inert point block
    SCHEMA_UNAVAILABLE = "schema-unavailable"  # the tree ships no readable container schema


@dataclass(frozen=True)
class FrictionFinding:
    """One finding, located by file (`path`, `path#id` for an entry) and pointer."""

    location: str  # the artefact's location, relative to the root
    pointer: str  # JSON Pointer inside it, or "" when the finding is about the whole
    severity: Severity
    kind: FrictionFindingKind
    message: str

    @property
    def where(self) -> str:
        return f"{self.location} {self.pointer}".rstrip()


@dataclass(frozen=True)
class FrictionValidation:
    """Outcome of the pass: what was walked and what was found."""

    discovery: Discovery
    findings: tuple[FrictionFinding, ...]

    @property
    def errors(self) -> tuple[FrictionFinding, ...]:
        return tuple(f for f in self.findings if f.severity is Severity.ERROR)

    @property
    def warnings(self) -> tuple[FrictionFinding, ...]:
        return tuple(f for f in self.findings if f.severity is Severity.WARNING)

    @property
    def reports(self) -> tuple[FrictionFinding, ...]:
        return tuple(f for f in self.findings if f.severity is Severity.REPORT)

    @property
    def is_dormant(self) -> bool:
        return self.discovery.is_dormant


def validate_friction(target_root: Path) -> FrictionValidation:
    """Run the pass over the project at `target_root`.

    A capability place the walk does not follow, a place matching a synced
    copy, a capability surface entry not read or held folder not held, and a
    held document that does not parse or carries a friction block, are
    reported whenever declared. Unparsable front
    matter is reported whenever places are declared: a file that fails to parse
    also keeps the pass awake (`Discovery.is_dormant`), so a YAML typo in the
    only container-carrying file is an error, not silence. The line-ending,
    container, deferral, unresolved-kind and cycle findings run only when the
    pass is awake.
    """
    discovery = shared_discovery(target_root)
    settings = discovery.settings
    findings: list[FrictionFinding] = []
    findings.extend(_capability_place_findings(target_root, settings))
    findings.extend(_synced_place_findings(target_root, discovery))
    findings.extend(_capability_surface_findings(settings))
    findings.extend(_capability_held_findings(discovery))
    findings.extend(_held_document_findings(discovery))
    findings.extend(_unreadable_findings(discovery))
    if not discovery.is_dormant:
        findings.extend(_mixed_line_endings_findings(discovery))
        findings.extend(_artefact_findings(target_root, discovery))
    return FrictionValidation(discovery=discovery, findings=tuple(findings))


# --- capability places --------------------------------------------------

# The findings about a capability place the walk does not follow.
PLACE_KINDS = frozenset(
    {FrictionFindingKind.MALFORMED_PLACE, FrictionFindingKind.PLACE_OUTSIDE_REPOSITORY}
)


def _capability_place_findings(
    target_root: Path, settings: FrictionSettings
) -> Iterable[FrictionFinding]:
    """Each capability place the walk does not follow, located in its package metadata.

    First those discovery could not read in the package schema's shape, in
    the order read; then those that leave the repository — absolute, climbing
    above the root, or resolving outside it through a link — judged as
    discovery judges it (`is_inside_repository`). A project's places are the
    configuration pass's.
    """
    for place in settings.malformed_places:
        yield FrictionFinding(
            location=place.file,
            pointer=place.pointer,
            severity=Severity.ERROR,
            kind=FrictionFindingKind.MALFORMED_PLACE,
            message=(
                f"{place.reason}, so friction discovery walks nothing under it; a capability "
                f"place is `{{path, location?, type?, description?}}`, its `location` naming a "
                f"`docs.locations` entry written `{{path, root?}}` (COR-050 point 7)."
            ),
        )
    for declared in settings.places:
        if declared.is_capability and not is_inside_repository(target_root, declared.resolved):
            yield FrictionFinding(
                location=declared.file,
                pointer=declared.pointer,
                severity=Severity.ERROR,
                kind=FrictionFindingKind.PLACE_OUTSIDE_REPOSITORY,
                message=(
                    f"capability place {declared.value!r} resolves to {declared.resolved!r}, "
                    f"which leaves the repository (absolute, climbing above the root, or "
                    f"resolving outside it through a link), so friction discovery walks "
                    f"nothing under it; every place stays inside the repository (COR-050 "
                    f"point 14)."
                ),
            )


# The finding about a place matching a synced copy, and how many of its
# matches the message names before it counts the rest.
SYNCED_KINDS = frozenset({FrictionFindingKind.SYNCED_PLACE})
_SYNCED_SHOWN = 3


def _synced_place_findings(target_root: Path, discovery: Discovery) -> Iterable[FrictionFinding]:
    """Each declared place, the project's or a capability's, matching a synced copy.

    One error per declaration, at the place's own entry, naming the matches
    discovery did not walk because they are synced copies (`Discovery.synced`);
    the place's other matches were walked. Reported whenever declared, dormant
    or not: a place every match of which is refused holds nothing, and must
    never look like an empty place. Without the tree's ownership module nothing
    can be told a synced copy, so every match was walked and a report says so.
    """
    if discovery.settings.places and synced_copy_test(target_root) is None:
        yield FrictionFinding(
            location=OWNERSHIP_MODULE.as_posix(),
            pointer="",
            severity=Severity.REPORT,
            kind=FrictionFindingKind.OWNERSHIP_UNAVAILABLE,
            message=(
                "the tree carries no ownership module, so no place is checked for synced "
                "copies and every match is walked (run `pkit sync`)."
            ),
        )
        return
    matches: dict[SettingsPath, list[str]] = {}
    for match in discovery.synced:
        matches.setdefault(match.place.declaration, []).append(match.path)
    for declaration, paths in matches.items():
        yield FrictionFinding(
            location=declaration.file,
            pointer=declaration.pointer,
            severity=Severity.ERROR,
            kind=FrictionFindingKind.SYNCED_PLACE,
            message=_synced_place_message(declaration, paths),
        )


def _synced_place_message(declaration: SettingsPath, paths: list[str]) -> str:
    who = "capability place" if declaration.is_capability else "place"
    at = "" if declaration.resolved == declaration.value else f" (at {declaration.resolved!r})"
    if paths == [declaration.resolved]:
        what, them = "is a synced copy", "it"
    else:
        shown = ", ".join(repr(p) for p in paths[:_SYNCED_SHOWN])
        if len(paths) > _SYNCED_SHOWN:
            shown += f" and {len(paths) - _SYNCED_SHOWN} more"
        count = "a synced copy" if len(paths) == 1 else f"{len(paths)} synced copies"
        what, them = f"matches {count}: {shown}", "it" if len(paths) == 1 else "them"
    return (
        f"{who} {declaration.value!r}{at} {what} — the methodology's sync writes {them} "
        f"into this repository, so friction discovery does not walk {them}; a place is "
        f"never a synced tree: narrow it to the project's own files or remove it (COR-050 "
        f"point 14)."
    )


# The finding about a capability surface entry not read.
SURFACE_KINDS = frozenset({FrictionFindingKind.MALFORMED_SURFACE})


def _capability_surface_findings(settings: FrictionSettings) -> Iterable[FrictionFinding]:
    """Each capability surface entry discovery could not read in the package
    schema's shape, located in its package metadata, in the order read. A
    project's surface is the configuration pass's."""
    for entry in settings.malformed_surface:
        yield FrictionFinding(
            location=entry.file,
            pointer=entry.pointer,
            severity=Severity.ERROR,
            kind=FrictionFindingKind.MALFORMED_SURFACE,
            message=(
                f"{entry.reason}, so the uncovered-surface measure reads nothing from it; a "
                f"capability's `friction.surface` is a list of repository-relative paths or "
                f"globs (COR-050 points 7 and 8)."
            ),
        )


# --- held documents (COR-050 point 1) ------------------------------------

# The findings about a held folder not held, and about a held document.
HELD_KINDS = frozenset(
    {
        FrictionFindingKind.MALFORMED_HELD,
        FrictionFindingKind.HELD_OUTSIDE_REPOSITORY,
        FrictionFindingKind.HELD_UNPARSABLE,
        FrictionFindingKind.HELD_BLOCK,
    }
)


def _capability_held_findings(discovery: Discovery) -> Iterable[FrictionFinding]:
    """Each capability held folder that holds nothing for a reason this pass owns,
    located in its package metadata: first those discovery could not read in
    their shape, in the order read; then those that leave the repository —
    through their location or a link — judged as discovery judges it
    (`HeldFolder.skipped`). One that oversteps its bounds is the packages
    pass's (`package_validate`)."""
    for entry in discovery.settings.malformed_held:
        yield FrictionFinding(
            location=entry.file,
            pointer=entry.pointer,
            severity=Severity.ERROR,
            kind=FrictionFindingKind.MALFORMED_HELD,
            message=(
                f"{entry.reason}, so friction discovery holds nothing under it, and a place "
                f"matching its documents reads them as artefacts; a held folder is "
                f"`{{location, path, description?}}`, `path` a folder within that location "
                f"(COR-050 point 1)."
            ),
        )
    for folder in discovery.held_folders:
        if folder.skipped is None or folder.skipped.reason != SKIP_OUTSIDE:
            continue
        declared = folder.declaration
        yield FrictionFinding(
            location=declared.file,
            pointer=declared.pointer,
            severity=Severity.ERROR,
            kind=FrictionFindingKind.HELD_OUTSIDE_REPOSITORY,
            message=(
                f"held folder {declared.value!r} resolves to {declared.resolved!r}, which leaves "
                f"the repository (its location lies outside it, or it resolves outside it "
                f"through a link), so friction discovery holds nothing under it; a held folder "
                f"lies within one of the component's locations, inside the repository (COR-050 "
                f"point 1)."
            ),
        )


def _held_document_findings(discovery: Discovery) -> Iterable[FrictionFinding]:
    """What a document a component holds may not be (COR-050 points 1 and 12), in
    the order discovery lists the held files.

    Its front matter parses: otherwise a friction block could not be looked for,
    so the typo is an error rather than a hiding place. And it carries no
    friction block, anywhere: a held document is not an artefact — no place
    walks it, so no check reads its anchors or its revalidation, and a block
    there would look like a claim that is never checked. Located at the file,
    and at each block by its pointer.
    """
    for held in discovery.held:
        declaration = held.folder.declaration
        where = f"its held folder {declaration.value!r}, {declaration.file}:{declaration.pointer}"
        if held.unreadable is not None:
            yield FrictionFinding(
                location=held.path,
                pointer="",
                severity=Severity.ERROR,
                kind=FrictionFindingKind.HELD_UNPARSABLE,
                message=(
                    f"front matter does not parse ({held.unreadable}); the document is held by "
                    f"{held.component} ({where}), and a friction block in it could not be looked "
                    f"for — fix the YAML (COR-050 points 1 and 12)."
                ),
            )
        for pointer in held.blocks:
            yield FrictionFinding(
                location=held.path,
                pointer=pointer,
                severity=Severity.ERROR,
                kind=FrictionFindingKind.HELD_BLOCK,
                message=(
                    f"a friction block in a document held by {held.component} ({where}): a held "
                    f"document is not an artefact, so no check reads its anchors or its "
                    f"revalidation — remove the block (COR-050 points 1 and 12)."
                ),
            )


# --- artefacts ----------------------------------------------------------


def _unreadable_findings(discovery: Discovery) -> Iterable[FrictionFinding]:
    """A Markdown file in a declared place whose front matter does not parse.

    A rule-set file is left to the rule-set pass, which claims it.
    """
    for unreadable in _unclaimed_unreadable(discovery):
        yield FrictionFinding(
            location=unreadable.path,
            pointer="",
            severity=Severity.ERROR,
            kind=FrictionFindingKind.UNPARSABLE_FRONT_MATTER,
            message=(
                f"front matter does not parse ({unreadable.reason}); the file is in the "
                f"declared place {unreadable.place.pattern!r}, so its block cannot be "
                f"skipped — fix the YAML or move the file out of the place."
            ),
        )


def _mixed_line_endings_findings(discovery: Discovery) -> Iterable[FrictionFinding]:
    """A file the walk read that mixes line endings, in the order it lists the files.

    A rule-set file is reported here too: the rule-set pass reads the set's
    shape, and the line endings are the walk's reading of the file.
    """
    for file in discovery.files:
        if not file.mixed_line_endings:
            continue
        yield FrictionFinding(
            location=file.path,
            pointer="",
            severity=Severity.ERROR,
            kind=FrictionFindingKind.MIXED_LINE_ENDINGS,
            message=(
                "mixes line endings (`\\n` on some lines, `\\r\\n` or a lone `\\r` on others); "
                "friction discovery reads every one as `\\n`, so a carriage return that is part "
                "of a value would be read as a line break, and the friction writers cannot keep "
                "the file's other bytes as they are — write it with one kind of line ending "
                "(COR-050 point 12)."
            ),
        )


def _artefact_findings(target_root: Path, discovery: Discovery) -> list[FrictionFinding]:
    findings: list[FrictionFinding] = []
    schema, schema_finding = _container_schema(target_root)
    if schema_finding is not None:
        findings.append(schema_finding)
    wiring = connections.container_wiring(target_root)
    registry = registered_anchor_kinds(target_root)  # read once for the pass
    points = _PointAnchors(target_root)
    named: dict[str, str | None] = {}

    def record_named(path: str) -> str | None:
        if path not in named:
            named[path] = record_naming(target_root, path)
        return named[path]

    for artefact in discovery.with_container:
        if schema is not None and artefact.rule_set is None:  # a rule's: the rule-set pass's
            findings.extend(_container_findings(artefact, schema, wiring))
        findings.extend(_unanchored_beside_anchors(artefact))
        findings.extend(_dangling_deferrals(artefact))
        findings.extend(_duplicate_deferrals(artefact))
        findings.extend(_link_findings(artefact, discovery.links(artefact)))
        findings.extend(_unresolved_kinds(artefact, registry))
        findings.extend(points.findings(artefact))
        findings.extend(_part_anchor_findings(artefact, discovery, record_named))

    findings.extend(_cycles(discovery, points.record_path))
    return findings


def block_findings(
    artefact: Artefact,
    schema: dict | None,
    target_root: Path,
    links: Sequence[RevisitLink] = (),
) -> tuple[FrictionFinding, ...]:
    """What this pass finds in one artefact's own block: its shape, a reason for having
    no anchors beside anchors, dangling and repeated deferrals, the revisit entries and
    link fields of the `links` its places declare, and anchor kinds nothing resolves.

    The per-artefact judgments `validate_friction` applies — the container
    schema and the container's rule (skipped when `schema` is `None`, as the
    pass skips them without a readable schema), then `unanchored-because`
    beside anchors, then every deferral naming no anchor of the artefact, then
    every deferral of an anchor an earlier entry defers, then the links
    (`_link_findings`), then every anchor kind nothing installed resolves, which
    is a report. `links` are the ones discovery gives the artefact
    (`Discovery.links`): with none, every revisit entry dangles. The
    cycle check spans artefacts and is not here.
    The writing commands (`friction_write`) read what they would write back
    through this, so a writer never writes a block validation would refuse —
    and writes one validation only reports on, an anchor of a kind nothing
    resolves included.
    """
    findings: list[FrictionFinding] = []
    if schema is not None:
        # the container is read against the tree's active wiring, as the pass
        # reads it — an orphan or an inert block is the same finding either way
        wiring = connections.container_wiring(target_root)
        findings.extend(_container_findings(artefact, schema, wiring))
    findings.extend(_unanchored_beside_anchors(artefact))
    findings.extend(_dangling_deferrals(artefact))
    findings.extend(_duplicate_deferrals(artefact))
    findings.extend(_link_findings(artefact, links))
    findings.extend(_unresolved_kinds(artefact, registered_anchor_kinds(target_root)))
    return tuple(findings)


def _unclaimed_unreadable(discovery: Discovery) -> tuple[UnreadableFile, ...]:
    """The unparsable files this pass reports: all but rule-set files."""
    return tuple(u for u in discovery.unreadable if u.rule_set is None)


def _container_schema(target_root: Path) -> tuple[dict | None, FrictionFinding | None]:
    """The tree's container schema, or a report saying why the block check is skipped."""
    try:
        return bs.load_backbone_schema(target_root, "container"), None
    except bs.BackboneSchemaMissing as exc:
        message = f"no container schema at {exc}; the block check is skipped (run `pkit sync`)."
    except bs.BackboneSchemaInvalid as exc:
        message = f"{exc}; the block check is skipped (`pkit schemas validate` reports it)."
    return None, FrictionFinding(
        location=str(bs.BACKBONE_SCHEMAS_DIR / "container.schema.json"),
        pointer="",
        severity=Severity.REPORT,
        kind=FrictionFindingKind.SCHEMA_UNAVAILABLE,
        message=message,
    )


def _container_findings(
    artefact: Artefact, schema: dict, wiring: bs.ContainerWiring
) -> Iterable[FrictionFinding]:
    """Delegate the block's shape and the container's rule, read against the
    active wiring; surface each finding."""
    report = bs.validate_container(artefact.carrier, schema, wiring=wiring)
    for finding in report.findings:
        is_error = finding.severity is bs.Severity.ERROR
        yield FrictionFinding(
            location=artefact.location,
            pointer=finding.location,
            severity=Severity(finding.severity.value),
            kind=(
                FrictionFindingKind.MALFORMED_BLOCK
                if is_error
                else FrictionFindingKind.CONTAINER_REPORT
            ),
            message=finding.message,
        )


def _unanchored_beside_anchors(artefact: Artefact) -> Iterable[FrictionFinding]:
    """`unanchored-because` in a block that lists anchors (COR-050 points 1 and 12).

    The reason says why the artefact has none, so beside anchors one of the
    two is wrong, and the measure would read the artefact as anchored and
    never show the reason. Any value of the key counts — its shape is the
    schema's finding — beside any anchor the block lists as text.
    """
    friction = artefact.friction
    if not isinstance(friction, Mapping) or UNANCHORED_BECAUSE_KEY not in friction:
        return
    kinds = [kind for kind, values in artefact.anchors.items() if values]
    if not kinds:
        return
    yield FrictionFinding(
        location=artefact.location,
        pointer=f"/{bs.CONTAINER_KEY}/{FRICTION_KEY}/{UNANCHORED_BECAUSE_KEY}",
        severity=Severity.ERROR,
        kind=FrictionFindingKind.UNANCHORED_BESIDE_ANCHORS,
        message=(
            f"`{UNANCHORED_BECAUSE_KEY}` stands beside anchors ({', '.join(kinds)}): the "
            f"reason says why the artefact has none, so the two contradict each other — "
            f"remove the reason, or the anchors (COR-050 point 1)."
        ),
    )


def _dangling_deferrals(artefact: Artefact) -> Iterable[FrictionFinding]:
    """A `deferred[].anchor` that names no anchor of the artefact, by kind and value.

    The pointer carries the entry's index as written (`Deferral.index`), so it
    names the right entry even when a malformed one precedes it.
    """
    for deferral in artefact.deferrals:
        anchor = deferral.anchor
        declared = artefact.anchors_of_kind(anchor.kind)
        if anchor.value in declared:
            continue
        known = ""
        if declared:
            known = f" (its {anchor.kind} anchors: {', '.join(map(repr, declared))})"
        yield FrictionFinding(
            location=artefact.location,
            pointer=(
                f"/{bs.CONTAINER_KEY}/{FRICTION_KEY}/revalidated/deferred/{deferral.index}/anchor"
            ),
            severity=Severity.ERROR,
            kind=FrictionFindingKind.DANGLING_DEFERRAL,
            message=(
                f"deferral names {anchor.kind} anchor {anchor.value!r}, which the artefact "
                f"does not declare{known}; remove the entry, or add the anchor it postpones "
                f"(COR-050 point 4)."
            ),
        )


def _duplicate_deferrals(artefact: Artefact) -> Iterable[FrictionFinding]:
    """Each `deferred[]` entry for an anchor an earlier entry already defers, by kind and
    value (COR-050 point 4: one entry per anchor).

    The first entry for an anchor stands; each later one is reported, its
    pointer carrying its index as written (`Deferral.index`). Two entries give
    one anchor two reasons, so what the deferral says depends on which a
    reader takes.
    """
    first: dict[Anchor, int] = {}
    for deferral in artefact.deferrals:
        earlier = first.setdefault(deferral.anchor, deferral.index)
        if earlier == deferral.index:
            continue
        anchor = deferral.anchor
        yield FrictionFinding(
            location=artefact.location,
            pointer=(
                f"/{bs.CONTAINER_KEY}/{FRICTION_KEY}/revalidated/deferred/{deferral.index}/anchor"
            ),
            severity=Severity.ERROR,
            kind=FrictionFindingKind.DUPLICATE_DEFERRAL,
            message=(
                f"{anchor.kind} anchor {anchor.value!r} is deferred again: entry {earlier} "
                f"defers it already, and the list holds one entry per anchor — keep one, with "
                f"one reason (`pkit friction defer` writes it so) (COR-050 point 4)."
            ),
        )


def _link_findings(artefact: Artefact, links: Sequence[RevisitLink]) -> Iterable[FrictionFinding]:
    """What the links the artefact's places declare find in it (COR-050 points 12 and 16).

    - **A link's field** that is no list of texts (`malformed-link-field`), or
      that lists a value no anchor of the artefact has (`unanchored-target`),
      once per field, however many links name it: a target the field names and
      the anchors leave out would be skipped silently.
    - **A revisit entry** that names no target of a link (`dangling-revisit`),
      and an entry for a target an earlier entry already names
      (`duplicate-revisit`). Each pointer carries the entry's index as written
      (`Revisit.index`).
    - **Revisit entries on an artefact whose places declare no link**
      (`orphaned-revisit`), once for the list: a report, never an error. The
      component that declared the link may be uninstalled, and the project
      cannot mend a component's declarations; the entries are kept, and judged
      again once a place declares a link.
    """
    values = {value for written in artefact.anchors.values() for value in written}
    for field in dict.fromkeys(link.targets for link in links):
        named = next(link for link in links if link.targets == field)
        listed = link_values(artefact, named)
        pointer = f"/{_pointer_token(field)}"
        if listed is None:
            yield FrictionFinding(
                location=artefact.location,
                pointer=pointer,
                severity=Severity.ERROR,
                kind=FrictionFindingKind.MALFORMED_LINK_FIELD,
                message=(
                    f"`{field}` lists the targets of a link that revisits them (declared at "
                    f"{named.file}:{named.pointer}), and is no list of anchor values; write "
                    f"each target as its anchor's value (COR-050 point 16)."
                ),
            )
            continue
        for value in listed:
            if value in values:
                continue
            yield FrictionFinding(
                location=artefact.location,
                pointer=pointer,
                severity=Severity.ERROR,
                kind=FrictionFindingKind.UNANCHORED_TARGET,
                message=(
                    f"`{field}` lists {value!r}, which no anchor of the artefact has, so a "
                    f"change to its trigger fields could not revisit it: add the anchor, or "
                    f"remove the value (COR-050 point 16)."
                ),
            )
    if not links:
        if artefact.revisits:
            count = len(artefact.revisits)
            yield FrictionFinding(
                location=artefact.location,
                pointer=f"/{bs.CONTAINER_KEY}/{FRICTION_KEY}/{REVISITED_KEY}",
                severity=Severity.REPORT,
                kind=FrictionFindingKind.ORPHANED_REVISIT,
                message=(
                    f"`{REVISITED_KEY}` holds {count} entr{'y' if count == 1 else 'ies'}, and no "
                    f"place holding the artefact declares a link that revisits its targets: "
                    f"kept, and judged again once a place declares one (COR-050 point 16)."
                ),
            )
        return
    targets = {anchor for link in links for anchor in link_targets(artefact, link)}
    first: dict[Anchor, int] = {}
    for entry in artefact.revisits:
        anchor = entry.anchor
        pointer = f"/{bs.CONTAINER_KEY}/{FRICTION_KEY}/{REVISITED_KEY}/{entry.index}/anchor"
        earlier = first.setdefault(anchor, entry.index)
        if earlier != entry.index:
            yield FrictionFinding(
                location=artefact.location,
                pointer=pointer,
                severity=Severity.ERROR,
                kind=FrictionFindingKind.DUPLICATE_REVISIT,
                message=(
                    f"{anchor.kind} anchor {anchor.value!r} is revisited again: entry {earlier} "
                    f"names it already, and the list holds one entry per target — keep one "
                    f"(COR-050 point 16)."
                ),
            )
            continue
        if anchor in targets:
            continue
        fields = ", ".join(f"`{f}`" for f in dict.fromkeys(link.targets for link in links))
        why = f"no link's field ({fields}) lists it among the artefact's anchors"
        yield FrictionFinding(
            location=artefact.location,
            pointer=pointer,
            severity=Severity.ERROR,
            kind=FrictionFindingKind.DANGLING_REVISIT,
            message=(
                f"revisit entry names {anchor.kind} anchor {anchor.value!r}, which is no target "
                f"of a link: {why}; remove the entry (COR-050 point 16)."
            ),
        )


def _unresolved_kinds(
    artefact: Artefact, registry: Mapping[str, ResolverCommand]
) -> Iterable[FrictionFinding]:
    """Each anchor kind of the artefact that nothing installed resolves, once per kind
    (COR-050 point 7) — a report, never an error (point 12).

    The one registry's verdict (`unresolved_kind_reason`): no installed
    capability registers the kind, or its registration is refused. A kind
    nothing registers names the nearest kind that is known — a typo of `path`
    reads as one. Uninstalling a capability must not fail validation, nor make
    the writers refuse every artefact naming its kind; the change check fails
    such an anchor where the diff adds it or takes its resolver away, and its
    artefact is not judged while it stands.
    """
    for kind, values in artefact.anchors.items():
        reason = unresolved_kind_reason(kind, registry)
        if reason is None or not values:
            continue
        suggestion = ""
        if kind not in registry:
            nearest = bs.nearest_known_key(kind, (*CORE_ANCHOR_KINDS, *registry))
            suggestion = f" Did you mean {nearest!r}?" if nearest is not None else ""
        yield FrictionFinding(
            location=artefact.location,
            pointer=f"/{bs.CONTAINER_KEY}/{FRICTION_KEY}/anchors/{_pointer_token(kind)}",
            severity=Severity.REPORT,
            kind=FrictionFindingKind.UNRESOLVED_KIND,
            message=(
                f"anchor kind {kind!r} is unresolved: {reason}. Its anchors are not checked, "
                f"and the artefact is not judged, while nothing resolves the kind (COR-050 "
                f"points 2 and 7).{suggestion}"
            ),
        )


class _PointAnchors:
    """The findings on each anchor that names one point of a record (COR-050 point 7),
    each record read once from the working tree, its points through `record_points`.

    - **A dead anchor**, an error: the record does not resolve, it holds no
      point with the id and retires none, or it writes its points as a list,
      whose numbers no anchor can rely on (COR-058 point 9).
    - **An ambiguous anchor**, an error: two live points of the record share
      the id.
    - **An anchor on a retired point**, a warning naming the point's
      successors: it stands on nothing, and is no dead anchor, since the
      record says where the point went. It stays until the anchor is
      re-pointed.

    A whole-record anchor is the checks' to judge, as before. Validation reads
    the working tree alone (COR-055 point 2), the one listing discovery reads.
    """

    def __init__(self, target_root: Path) -> None:
        self.root = target_root
        self.tree = WorkingTree(target_root)
        self._files: frozenset[str] | None = None
        self._records: dict[str, RecordPoints | None] = {}
        self._paths: dict[str, str | None] = {}

    def findings(self, artefact: Artefact) -> Iterable[FrictionFinding]:
        for index, value in _written_anchors(artefact, "record"):
            record, point = split_anchor(value)
            if point is None:
                continue
            pointer = f"/{bs.CONTAINER_KEY}/{FRICTION_KEY}/anchors/record/{index}"
            rel = self.record_path(value)
            if rel is None:
                yield self._finding(
                    artefact,
                    pointer,
                    Severity.ERROR,
                    FrictionFindingKind.DEAD_POINT_ANCHOR,
                    f"record anchor {value!r} is dead: it names no record (COR-050 point 7).",
                )
                continue
            points = self._read(rel)
            found = (
                AnchoredPoint(point, PointState.MISSING)
                if points is None
                else points.anchored(point)
            )
            if found.state is PointState.RETIRED:
                yield self._finding(
                    artefact,
                    pointer,
                    Severity.WARNING,
                    FrictionFindingKind.RETIRED_POINT_ANCHOR,
                    f"record anchor {value!r} names a retired point: {record} retires point "
                    f"{point}, and its content is in {successors_phrase(found.successors)}. The "
                    f"anchor stands on nothing until it is re-pointed, which a revalidation "
                    f"records (COR-050 points 6 and 7).",
                )
            elif found.state is PointState.AMBIGUOUS:
                yield self._finding(
                    artefact,
                    pointer,
                    Severity.ERROR,
                    FrictionFindingKind.AMBIGUOUS_POINT_ANCHOR,
                    f"record anchor {value!r} {point_problem(record, found)}: give one of them "
                    f"the next unused number (COR-050 point 7, COR-058 point 3).",
                )
            elif found.dead:
                yield self._finding(
                    artefact,
                    pointer,
                    Severity.ERROR,
                    FrictionFindingKind.DEAD_POINT_ANCHOR,
                    f"record anchor {value!r} is dead: {point_problem(record, found)} "
                    f"(COR-050 point 7).",
                )

    @property
    def files(self) -> frozenset[str]:
        if self._files is None:
            self._files = frozenset(self.tree.files())
        return self._files

    def record_path(self, value: str) -> str | None:
        """The file a record anchor's value names in the working tree, through the record
        resolver (`friction_check.record_file`), whole or on a point, resolved once per
        record; `None` where it names no record."""
        record = split_anchor(value)[0]
        if record not in self._paths:
            self._paths[record] = record_file(self.root, self.files, record)
        return self._paths[record]

    def _read(self, rel: str) -> RecordPoints | None:
        if rel not in self._records:
            raw = self.tree.read_bytes([rel]).get(rel)
            self._records[rel] = None if raw is None else read_points_bytes(raw)
        return self._records[rel]

    @staticmethod
    def _finding(
        artefact: Artefact,
        pointer: str,
        severity: Severity,
        kind: FrictionFindingKind,
        message: str,
    ) -> FrictionFinding:
        return FrictionFinding(artefact.location, pointer, severity, kind, message)


def _part_anchor_findings(
    artefact: Artefact, discovery: Discovery, record_named: Callable[[str], str | None]
) -> Iterable[FrictionFinding]:
    """The findings on each anchor on a document's section or its lead (COR-050 points 2,
    7 and 12), each an error, whatever made it so — its artefact gone included:

    - **a dead anchor**: no artefact by its name, or no heading of the document
      with its slug, as a renamed heading leaves it;
    - **an ambiguous anchor**: two headings of the document share its slug;
    - **a refused anchor**: a section or the lead of a collection file, a
      collection entry, an extension point among them, or a record, with the
      anchor to use where there is one.

    A whole anchor that names nothing is the checks' to judge. The anchor is read
    as both checks read it (`artefact_parts.anchored_part`), against the working
    tree's discovery.
    """
    for index, value in _written_anchors(artefact, "artefact"):
        found = anchored_part(discovery, value, record_named)
        problem = found.problem
        if not found.names_part or problem is None:
            continue
        pointer = f"/{bs.CONTAINER_KEY}/{FRICTION_KEY}/anchors/artefact/{index}"
        if found.state is PartState.AMBIGUOUS:
            kind = FrictionFindingKind.AMBIGUOUS_SECTION_ANCHOR
            message = (
                f"artefact anchor {value!r} {problem}: rename one of the headings, or anchor "
                f"another part (COR-050 point 7)."
            )
        elif found.state is PartState.REFUSED:
            kind = FrictionFindingKind.REFUSED_SECTION_ANCHOR
            message = f"artefact anchor {value!r} {problem} (COR-050 point 2)."
        else:
            kind = FrictionFindingKind.DEAD_SECTION_ANCHOR
            mend = (
                " A renamed heading leaves its anchors dead: re-point the anchor, which a "
                "revalidation records."
                if found.target is not None
                else ""
            )
            message = f"artefact anchor {value!r} is dead: {problem} (COR-050 point 7).{mend}"
        yield FrictionFinding(artefact.location, pointer, Severity.ERROR, kind, message)


def _written_anchors(artefact: Artefact, kind: str) -> list[tuple[int, str]]:
    """Each anchor of `kind` the block writes as text, with its index in the list as
    written, so a finding points at it even beside an entry that is not text."""
    friction = artefact.friction
    if not isinstance(friction, Mapping):
        return []
    anchors = cast("Mapping[str, Any]", friction).get("anchors")
    if not isinstance(anchors, Mapping):
        return []
    written = cast("Mapping[str, Any]", anchors).get(kind)
    if not isinstance(written, list):
        return []
    values = cast("list[Any]", written)
    return [(index, value) for index, value in enumerate(values) if isinstance(value, str)]


def _pointer_token(segment: str) -> str:
    """One JSON Pointer reference token (RFC 6901 escaping)."""
    return segment.replace("~", "~0").replace("/", "~1")


def _cycles(
    discovery: Discovery, record_path: Callable[[str], str | None]
) -> list[FrictionFinding]:
    """Cycles between artefacts, each reported once with its path (COR-050 point 5).

    The edges are the one edge set truth-chain order reads too
    (`friction_check.upstream_artefacts`): an artefact anchor to the artefact it
    names, an anchor on a document's section or its lead to the document
    (`artefact_parts.whole_target`), and a record anchor, whole or on a point, to
    the record, where the record's file is an artefact. `record_path` gives the
    file a record anchor names in the working tree. A path anchor and an anchor of
    a registered kind name files, so neither is followed. So an anchor on a part of
    its own artefact is a cycle, as is a record's anchor on itself or on one of its
    own points. A value naming nothing is a dead anchor — the checks' finding, not
    this pass's. A depth-first walk in discovery order finds each cycle the first
    time it closes; the cycle is rotated to start at its smallest member so the
    same cycle reached from two sides is reported once.
    """
    order = list(discovery.artefacts)
    upstream = upstream_artefacts(discovery, record_path)
    edges = {i: [edge.index for edge in found] for i, found in enumerate(upstream)}

    WHITE, GREY, BLACK = 0, 1, 2
    colour = dict.fromkeys(range(len(order)), WHITE)
    seen_cycles: set[tuple[int, ...]] = set()
    findings: list[FrictionFinding] = []

    def visit(start: int) -> None:
        stack: list[tuple[int, Iterable[int]]] = [(start, iter(edges[start]))]
        path: list[int] = [start]
        colour[start] = GREY
        while stack:
            node, children = stack[-1]
            child = next(children, None)
            if child is None:
                colour[node] = BLACK
                stack.pop()
                path.pop()
                continue
            if colour[child] == GREY:
                cycle = path[path.index(child) :]
                canonical = _rotate_to_smallest(cycle, order)
                if canonical not in seen_cycles:
                    seen_cycles.add(canonical)
                    findings.append(_cycle_finding(canonical, order, upstream, discovery))
            elif colour[child] == WHITE:
                colour[child] = GREY
                path.append(child)
                stack.append((child, iter(edges[child])))

    for i in range(len(order)):
        if colour[i] == WHITE:
            visit(i)
    return findings


def _rotate_to_smallest(cycle: list[int], order: list[Artefact]) -> tuple[int, ...]:
    pivot = min(range(len(cycle)), key=lambda k: order[cycle[k]].location)
    return tuple(cycle[pivot:] + cycle[:pivot])


#: What an anchor of an artefact on itself names, in the order a finding lists them.
_ITSELF = "itself"
_OWN_PART = "a section or the lead of itself"
_OWN_POINT = "one of its own points"


def _own_part(anchor: Anchor, discovery: Discovery) -> str:
    """What an anchor on its own artefact names (COR-050 points 2 and 5): the artefact
    itself, a section or the lead of it, or one of the record's own points."""
    if anchor.kind == "record":
        return _ITSELF if split_anchor(anchor.value)[1] is None else _OWN_POINT
    return _ITSELF if discovery.find(anchor.value) is not None else _OWN_PART


def _listed_with_and(items: list[str]) -> str:
    """`a`, `a, and b`, or `a, b, and c`."""
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + ", and " + items[-1]


def _cycle_finding(
    cycle: tuple[int, ...],
    order: list[Artefact],
    upstream: tuple[tuple[Upstream, ...], ...],
    discovery: Discovery,
) -> FrictionFinding:
    """The finding on one cycle, `cycle` its members by their index in `order`, at the
    first member, naming the kind of the anchor by which it rests on the next member:
    `anchors/artefact` or `anchors/record`. An artefact that anchors a part of itself — a
    section or the lead, or one of a record's own points — is told so, with each anchor
    on itself it writes, whole or a part."""
    members = [order[i] for i in cycle]
    head = members[0]
    closing = [
        edge.anchor
        for k, index in enumerate(cycle)
        for edge in upstream[index]
        if edge.index == cycle[(k + 1) % len(cycle)]
    ]
    pointer = f"/{bs.CONTAINER_KEY}/{FRICTION_KEY}/anchors/{closing[0].kind}"
    if len(cycle) == 1:
        named_parts = {_own_part(anchor, discovery) for anchor in closing}
        if named_parts - {_ITSELF}:
            parts = [part for part in (_ITSELF, _OWN_PART, _OWN_POINT) if part in named_parts]
            named = ", ".join(repr(anchor.value) for anchor in closing)
            return FrictionFinding(
                location=head.location,
                pointer=pointer,
                severity=Severity.ERROR,
                kind=FrictionFindingKind.CYCLE,
                message=(
                    f"the artefact anchors {_listed_with_and(parts)} ({named}), which is a "
                    f"cycle: its own edits would flag it, and so would its own revalidation — "
                    f"anchor what lies outside it (COR-050 point 5)."
                ),
            )
    kinds = [kind for kind in ("artefact", "record") if any(a.kind == kind for a in closing)]
    shown = " -> ".join(a.id for a in members) + f" -> {head.id}"
    through = " and ".join(f"anchors.{kind}" for kind in kinds)
    what = "anchors to itself" if len(members) == 1 else f"form a cycle through {through}"
    return FrictionFinding(
        location=head.location,
        pointer=pointer,
        severity=Severity.ERROR,
        kind=FrictionFindingKind.CYCLE,
        message=(
            f"{'the artefact' if len(members) == 1 else 'the artefacts'} {what}: {shown}; "
            f"a cycle has no order in which its members could be revalidated — remove one "
            f"of the {' or '.join(kinds)} anchors (COR-050 point 5)."
        ),
    )


# --- the `friction` member of `pkit validate` -----------------------------


def summary_lines(result: FrictionValidation) -> list[str]:
    """The count line `pkit validate` prints under its `friction` heading.

    Dormant: the counts alone (COR-050 point 15). Awake: the counts, errors and
    reports included; the findings themselves follow as the member's findings.
    A capability place the walk does not follow, a place matching a synced
    copy, a capability surface entry not read, and a held folder not held or a
    held document's finding, are counted in either case, so the line never
    reads as nothing declared while one was.
    """
    d = result.discovery
    places, artefacts, carrying = len(d.places), len(d.artefacts), len(d.with_container)
    unfollowed = sum(1 for f in result.findings if f.kind in PLACE_KINDS)
    synced = sum(1 for f in result.findings if f.kind in SYNCED_KINDS)
    unread = sum(1 for f in result.findings if f.kind in SURFACE_KINDS)
    held = sum(1 for f in result.findings if f.kind in HELD_KINDS)
    not_walked = f"; {unfollowed} capability place(s) not walked" if unfollowed else ""
    if synced:
        not_walked += f"; {synced} place(s) matching a synced copy"
    if unread:
        not_walked += f"; {unread} capability surface entr{'y' if unread == 1 else 'ies'} not read"
    if held:
        not_walked += f"; {held} finding(s) on held folders and documents"
    if not d.places and not unfollowed and not unread and not held:
        counts = "no places declared; dormant."
    elif d.is_dormant:
        counts = (
            f"{places} place(s), {artefacts} artefact(s), none carrying the "
            f"`{bs.CONTAINER_KEY}` container; dormant{not_walked}."
        )
    else:
        reported = _unclaimed_unreadable(d)
        unreadable = f", {len(reported)} with unparsable front matter" if reported else ""
        counts = (
            f"{places} place(s), {artefacts} artefact(s), {carrying} carrying the "
            f"`{bs.CONTAINER_KEY}` container{unreadable}; mode {d.settings.mode_or_default}; "
            f"{len(result.errors)} error(s), {_warnings(result)}{len(result.reports)} "
            f"report(s){not_walked}."
        )
    return [counts]


def _warnings(result: FrictionValidation) -> str:
    """The warnings in the count line, `n warning(s), `, or nothing when there are none,
    so the line reads as it did where nothing warns."""
    return f"{len(result.warnings)} warning(s), " if result.warnings else ""


UMBRELLA_SEVERITY = {
    Severity.ERROR: validators.Severity.ERROR,
    Severity.WARNING: validators.Severity.WARNING,
    Severity.REPORT: validators.Severity.REPORT,
}


def outcome(target_root: Path) -> validators.Outcome:
    """The `friction` member of `pkit validate`: the counts, then every finding —
    errors fail, reports print (COR-050 point 12)."""
    result = validate_friction(target_root)
    findings = tuple(
        validators.Finding(
            f"{f.location}:{f.pointer}" if f.pointer else f.location,
            f.message,
            UMBRELLA_SEVERITY[f.severity],
        )
        for f in result.findings
    )
    return validators.Outcome(tuple(summary_lines(result)), findings)
