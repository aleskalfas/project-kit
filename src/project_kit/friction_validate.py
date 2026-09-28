"""The validation findings COR-050 point 12 assigns to validation.

Over the artefacts `friction_discovery` finds in the declared places, and the
settings that declare them, this pass reports:

- **a capability place the walk does not follow** — one discovery could not
  read in the package schema's shape `{path, location?}` (plain text, no
  `path`, a location `docs.locations` does not declare in its shape), or one
  that leaves the repository, through a link included; reported whenever it
  is declared, dormant or not, because a place nothing is found under must
  never look like a place with nothing in it (COR-050 point 7);
- **unparsable front matter** in a declared place — reported whenever places
  are declared, dormant or not, because the check never skips an artefact it
  cannot parse: the broken file may be the one carrying the container;
- **a malformed block** — the container fails its schema or the container's
  rule; delegated to `backbone_schemas.validate_container`, whose errors are
  surfaced against the artefact (COR-050 point 2, COR-053 point 10);
- **a dangling deferral** — a `deferred[].anchor` naming, by kind and value,
  no anchor of the artefact (COR-050 point 4);
- **a cycle between artefacts** through `anchors.artefact`, with the cycle's
  path — a cycle has no order in which its members could be revalidated
  (COR-050 point 5).

These fail validation in either mode, because the project can fix them. A
rule-set file is claimed before the container rule (ADR-056 point 2): its
front matter and each rule's container are the rule-set pass's findings
(`rule_sets`), so this pass reports neither, while its rules still take part
in the deferral and cycle checks like every artefact. The project's settings
themselves — an invalid `friction.mode`, a place, surface or exclude path
outside the repository — are the configuration pass's findings
(`config_validate`, which owns the file), and a capability's `friction` block
is the packages pass's, which judges its shape but cannot know where a place
resolves; so a capability place the walk does not follow is reported here
too. This pass never walks a place that leaves the repository. What it does
not do either: compute friction, resolve path anchors against git, or report
dead anchors — those are the two checks'
findings (COR-050 points 6 and 7), later Tasks. Orphaned role blocks the
container validator reports are carried through as reports (never errors) so
`pkit validate` can show them.

Dormant until used (COR-050 point 15): with no places declared, or nothing in
them to judge — no artefact carrying the container and no file it failed to
parse — the pass reports nothing but its counts and any capability place the
walk does not follow.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


from project_kit import backbone_schemas as bs
from project_kit import validators
from project_kit.friction_discovery import (
    FRICTION_KEY,
    Artefact,
    Discovery,
    FrictionSettings,
    UnreadableFile,
    discover_artefacts,
    is_inside_repository,
    read_friction_settings,
)

Severity = bs.Severity


class FrictionFindingKind(Enum):
    MALFORMED_PLACE = "malformed-place"  # a capability place not in the schema's shape
    PLACE_OUTSIDE_REPOSITORY = "place-outside-repository"  # a capability place leaving it
    MALFORMED_BLOCK = "malformed-block"
    UNPARSABLE_FRONT_MATTER = "unparsable-front-matter"
    DANGLING_DEFERRAL = "dangling-deferral"
    CYCLE = "cycle"
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
    def reports(self) -> tuple[FrictionFinding, ...]:
        return tuple(f for f in self.findings if f.severity is Severity.REPORT)

    @property
    def is_dormant(self) -> bool:
        return self.discovery.is_dormant


def validate_friction(target_root: Path) -> FrictionValidation:
    """Run the pass over the project at `target_root`.

    A capability place the walk does not follow is reported whenever it is
    declared. Unparsable front matter is reported whenever places are declared:
    a file that fails to parse also keeps the pass awake (`Discovery.is_dormant`),
    so a YAML typo in the only container-carrying file is an error, not silence.
    The container, deferral and cycle findings run only when the pass is awake.
    """
    settings = read_friction_settings(target_root)
    discovery = discover_artefacts(target_root, settings)
    findings: list[FrictionFinding] = []
    findings.extend(_capability_place_findings(target_root, settings))
    findings.extend(_unreadable_findings(discovery))
    if not discovery.is_dormant:
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
                f"place is `{{path, location?}}`, its `location` naming a `docs.locations` "
                f"entry written `{{path, root?}}` (COR-050 point 7)."
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


def _artefact_findings(target_root: Path, discovery: Discovery) -> list[FrictionFinding]:
    findings: list[FrictionFinding] = []
    schema, schema_finding = _container_schema(target_root)
    if schema_finding is not None:
        findings.append(schema_finding)

    for artefact in discovery.with_container:
        if schema is not None and artefact.rule_set is None:  # a rule's: the rule-set pass's
            findings.extend(_container_findings(artefact, schema))
        findings.extend(_dangling_deferrals(artefact))

    findings.extend(_cycles(discovery))
    return findings


def block_findings(artefact: Artefact, schema: dict | None) -> tuple[FrictionFinding, ...]:
    """What this pass finds in one artefact's own block: its shape and dangling deferrals.

    The per-artefact judgments `validate_friction` applies — the container
    schema and the container's rule (skipped when `schema` is `None`, as the
    pass skips them without a readable schema), then every deferral naming no
    anchor of the artefact. The cycle check spans artefacts and is not here.
    The writing commands (`friction_write`) read what they would write back
    through this, so a writer never writes a block validation would refuse.
    """
    findings: list[FrictionFinding] = []
    if schema is not None:
        findings.extend(_container_findings(artefact, schema))
    findings.extend(_dangling_deferrals(artefact))
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


def _container_findings(artefact: Artefact, schema: dict) -> Iterable[FrictionFinding]:
    """Delegate the block's shape and the container's rule; surface each finding."""
    report = bs.validate_container(artefact.carrier, schema)
    for finding in report.findings:
        is_error = finding.severity is Severity.ERROR
        yield FrictionFinding(
            location=artefact.location,
            pointer=finding.location,
            severity=finding.severity,
            kind=(
                FrictionFindingKind.MALFORMED_BLOCK
                if is_error
                else FrictionFindingKind.CONTAINER_REPORT
            ),
            message=finding.message,
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


def _cycles(discovery: Discovery) -> list[FrictionFinding]:
    """Cycles through `anchors.artefact`, each reported once with its path.

    Edges go from an artefact to every artefact its `anchors.artefact`
    values name (a value naming nothing is a dead anchor — the checks' finding,
    not this pass's). A depth-first walk in discovery order finds each cycle
    the first time it closes; the cycle is rotated to start at its smallest
    member so the same cycle reached from two sides is reported once.
    """
    order = list(discovery.artefacts)
    edges: dict[int, list[int]] = {}
    index_of = {id(a): i for i, a in enumerate(order)}
    for i, artefact in enumerate(order):
        targets: list[int] = []
        for reference in artefact.anchors_of_kind("artefact"):
            target = discovery.find(reference)
            if target is not None:
                targets.append(index_of[id(target)])
        edges[i] = targets

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
                    findings.append(_cycle_finding([order[i] for i in canonical]))
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


def _cycle_finding(members: list[Artefact]) -> FrictionFinding:
    head = members[0]
    shown = " -> ".join(a.id for a in members) + f" -> {head.id}"
    what = "anchors to itself" if len(members) == 1 else "form a cycle through anchors.artefact"
    return FrictionFinding(
        location=head.location,
        pointer=f"/{bs.CONTAINER_KEY}/{FRICTION_KEY}/anchors/artefact",
        severity=Severity.ERROR,
        kind=FrictionFindingKind.CYCLE,
        message=(
            f"{'the artefact' if len(members) == 1 else 'the artefacts'} {what}: {shown}; "
            f"a cycle has no order in which its members could be revalidated — remove one "
            f"of the artefact anchors (COR-050 point 5)."
        ),
    )


# --- the `friction` member of `pkit validate` -----------------------------


def summary_lines(result: FrictionValidation) -> list[str]:
    """The count line `pkit validate` prints under its `friction` heading.

    Dormant: the counts alone (COR-050 point 15). Awake: the counts, errors and
    reports included; the findings themselves follow as the member's findings.
    A capability place the walk does not follow is counted in either case, so
    the line never reads as nothing declared while one was.
    """
    d = result.discovery
    places, artefacts, carrying = len(d.places), len(d.artefacts), len(d.with_container)
    unfollowed = sum(1 for f in result.findings if f.kind in PLACE_KINDS)
    not_walked = f"; {unfollowed} capability place(s) not walked" if unfollowed else ""
    if not d.places and not unfollowed:
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
            f"{len(result.errors)} error(s), {len(result.reports)} report(s){not_walked}."
        )
    return [counts]


UMBRELLA_SEVERITY = {
    Severity.ERROR: validators.Severity.ERROR,
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
