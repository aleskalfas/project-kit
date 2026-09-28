"""The validation findings COR-050 point 12 assigns to validation.

Over the artefacts `friction_discovery` finds in the declared places, and the
settings that declare them, this pass reports:

- **a malformed block** — the container fails its schema or the container's
  rule; delegated to `backbone_schemas.validate_container`, whose errors are
  surfaced against the artefact (COR-050 point 2, COR-053 point 10). Front
  matter in a declared place that does not parse is reported too, because the
  check never skips an artefact it cannot parse;
- **a dangling deferral** — a `deferred[].anchor` naming, by kind and value,
  no anchor of the artefact (COR-050 point 4);
- **a cycle between artefacts** through `anchors.artefact`, with the cycle's
  path — a cycle has no order in which its members could be revalidated
  (COR-050 point 5);
- **an invalid friction mode** in the configuration (COR-050 points 12, 14);
- **a settings path outside the repository** — a place, surface or exclude
  entry of the project, or a capability's place or surface (COR-050 point 14).

These fail validation in either mode, because the project can fix them. What
this pass does not do: compute friction, resolve path anchors against git, or
report dead anchors — those are the two checks' findings (COR-050 points 6
and 7), later Tasks. Orphaned role blocks the container validator reports are
carried through as reports (never errors) so `pkit validate` can show them.

Dormant until used (COR-050 point 15): with no places declared, or no
artefact carrying the container, the pass reports nothing but its counts.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from project_kit import backbone_schemas as bs
from project_kit.friction_discovery import (
    FRICTION_KEY,
    FRICTION_MODES,
    Artefact,
    Discovery,
    FrictionSettings,
    discover_artefacts,
    is_inside_repository,
    read_friction_settings,
)

Severity = bs.Severity


class FrictionFindingKind(Enum):
    MALFORMED_BLOCK = "malformed-block"
    UNPARSABLE_FRONT_MATTER = "unparsable-front-matter"
    DANGLING_DEFERRAL = "dangling-deferral"
    CYCLE = "cycle"
    INVALID_MODE = "invalid-mode"
    PATH_OUTSIDE_REPOSITORY = "path-outside-repository"
    CONTAINER_REPORT = "container-report"  # an orphaned role block, an inert point block
    SCHEMA_UNAVAILABLE = "schema-unavailable"  # the tree ships no readable container schema


@dataclass(frozen=True)
class FrictionFinding:
    """One finding, located by file (`path`, `path#id` for an entry) and pointer."""

    location: str  # the artefact's or settings file's location, relative to the root
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

    The settings findings (mode, paths) are checked whenever a `friction` key
    is present anywhere, dormant or not: an invalid mode must never switch
    enforcement off silently (COR-050 point 12). The artefact findings run only
    when the pass is awake.
    """
    settings = read_friction_settings(target_root)
    discovery = discover_artefacts(target_root, settings)
    findings: list[FrictionFinding] = []
    findings.extend(_settings_findings(target_root, settings))
    if not discovery.is_dormant:
        findings.extend(_artefact_findings(target_root, discovery))
    return FrictionValidation(discovery=discovery, findings=tuple(findings))


# --- settings -----------------------------------------------------------


def _settings_findings(target_root: Path, settings: FrictionSettings) -> list[FrictionFinding]:
    findings: list[FrictionFinding] = []
    if settings.mode is not None and settings.mode not in FRICTION_MODES:
        allowed = ", ".join(repr(m) for m in FRICTION_MODES)
        findings.append(
            FrictionFinding(
                location=settings.config_file,
                pointer=settings.mode_location,
                severity=Severity.ERROR,
                kind=FrictionFindingKind.INVALID_MODE,
                message=(
                    f"{FRICTION_KEY}.mode {settings.mode!r} is not one of {allowed}; "
                    f"set it to one of those (the default, when absent, is 'warning')."
                ),
            )
        )
    for declared in settings.all_paths:
        if is_inside_repository(target_root, declared.resolved):
            continue
        resolved = ""
        if declared.resolved != declared.value:
            resolved = f" (resolved: {declared.resolved!r})"
        findings.append(
            FrictionFinding(
                location=declared.file,
                pointer=declared.pointer,
                severity=Severity.ERROR,
                kind=FrictionFindingKind.PATH_OUTSIDE_REPOSITORY,
                message=(
                    f"path {declared.value!r}{resolved} lies outside the repository; "
                    f"every friction path is relative to the repository root and must stay "
                    f"inside it (COR-050 point 14)."
                ),
            )
        )
    return findings


# --- artefacts ----------------------------------------------------------


def _artefact_findings(target_root: Path, discovery: Discovery) -> list[FrictionFinding]:
    findings: list[FrictionFinding] = []
    for unreadable in discovery.unreadable:
        findings.append(
            FrictionFinding(
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
        )

    schema, schema_finding = _container_schema(target_root)
    if schema_finding is not None:
        findings.append(schema_finding)

    for artefact in discovery.with_container:
        if schema is not None:
            findings.extend(_container_findings(artefact, schema))
        findings.extend(_dangling_deferrals(artefact))

    findings.extend(_cycles(discovery))
    return findings


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
    """A `deferred[].anchor` that names no anchor of the artefact, by kind and value."""
    for index, deferral in enumerate(artefact.deferrals):
        if deferral.value in artefact.anchors_of_kind(deferral.kind):
            continue
        declared = artefact.anchors_of_kind(deferral.kind)
        known = ""
        if declared:
            known = f" (its {deferral.kind} anchors: {', '.join(map(repr, declared))})"
        yield FrictionFinding(
            location=artefact.location,
            pointer=f"/{bs.CONTAINER_KEY}/{FRICTION_KEY}/revalidated/deferred/{index}/anchor",
            severity=Severity.ERROR,
            kind=FrictionFindingKind.DANGLING_DEFERRAL,
            message=(
                f"deferral names {deferral.kind} anchor {deferral.value!r}, which the artefact "
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


# --- rendering for `pkit validate` --------------------------------------


def summary_lines(result: FrictionValidation) -> list[str]:
    """The lines `pkit validate` prints under its `friction` heading.

    Dormant: the counts alone (COR-050 point 15). Awake: the counts, then any
    reports (which do not fail validation). Errors are handed to the command's
    issue list, so they print with every other pass's issues.
    """
    d = result.discovery
    places, artefacts, carrying = len(d.places), len(d.artefacts), len(d.with_container)
    if not d.places:
        counts = "no places declared; dormant."
    elif not carrying:
        counts = (
            f"{places} place(s), {artefacts} artefact(s), none carrying the "
            f"`{bs.CONTAINER_KEY}` container; dormant."
        )
    else:
        counts = (
            f"{places} place(s), {artefacts} artefact(s), {carrying} carrying the "
            f"`{bs.CONTAINER_KEY}` container; mode {d.settings.mode_or_default}; "
            f"{len(result.errors)} error(s), {len(result.reports)} report(s)."
        )
    lines = [counts]
    lines.extend(f"{finding.where}: {finding.message}" for finding in result.reports)
    return lines
