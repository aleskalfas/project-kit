"""Discovery: what a capability connects to, before it is installed and before
it is removed (COR-053 point 8).

Three readers of the one wiring resolver (`connections`, ADR-057 points 2 and
6), none of which resolves anything of its own:

- **`show`** — a capability's connections read from its package metadata
  alone, installed or not: the roles it provides, the points it defines
  (`accepts`, `offers`), its extensions (`contributes`, `subscribes`,
  `depends-on`), and what would connect here — for an installed capability
  the live wiring's bindings to and from it, for one not installed the
  bindings of the wiring the project would have with it installed.
- **The plans.** An install plan and an uninstall plan are the difference
  between the live wiring and the wiring the resolver computes for the
  installed set plus or minus the capability (`connections.resolve_wiring_with`),
  every other input read from the tree as the live wiring reads it. So a
  plan is exact: the wiring an operation leaves differs from the one before
  it by exactly the plan's `WiringDiff` (`diff_wiring`), which a test pins for
  both operations. On top of the difference, an install plan names the role
  conflicts it would open and the command that resolves each, what the
  capability needs that the project does not give it (the errors the install
  would put on the capability itself — unmet mandatory marks, mandatory
  cycles, required versions), and the role blocks whose meaning changes; an
  uninstall plan names the fillers lost, the counterparts left without a
  provider — processes among them — the artefacts whose role blocks would be
  orphaned, and the selections left naming the capability. A plan writes
  nothing and runs no filler command: the resolver resolves wiring, not data.
- **Suggestions** — where a data point is unfilled, a role nobody provides is
  targeted, or an implementation-addressed upstream is not installed, the
  capabilities of the local catalogue that would answer it
  (`capabilities.local_catalogue`: the installed tree, capabilities authored
  in the repository, the capabilities that ship with the running pkit). Only
  what is on disk is read; nothing is fetched. A suggestion is text — it names
  the capability and the command that shows it, and never installs anything.

What a plan does not predict, stated: the artefacts whose role blocks it
judges are those found in the places declared now, so a place the operation
itself adds or removes is not walked in advance; the rule-set pins among the
version relations are relations between rule-set files, not connections, and
are left out of the difference.

`suggestions` is the one computation of the suggestions: the status report
reads it, and so does any other view of the wiring that shows them — the
graph among them — rather than suggesting on its own.
"""

from __future__ import annotations

import dataclasses
import json
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from project_kit import backbone_schemas as bs
from project_kit import capabilities as caps
from project_kit import cli_render
from project_kit import connections as cx
from project_kit.friction_discovery import discover_artefacts
from project_kit.package_validate import POINT_SEPARATOR, Severity

# The operations a plan is computed for.
INSTALL = "install"
UNINSTALL = "uninstall"

# How a role block's meaning changes (COR-053 point 10).
ORPHANED = "orphaned"  # its role would have no active provider: preserved, reported
ADOPTED = "adopted"  # an orphaned block whose role would gain an active provider
AMBIGUOUS = "ambiguous"  # a bare key whose word two active roles would share

# What becomes of a data point a lost filler answered.
STAYS_FILLED = "stays filled"
LEFT_UNFILLED = "left unfilled"
NO_LONGER_DEFINED = "no longer defined"

# The command that selects a role's provider — the connections command group's.
PROVIDERS_SET = "pkit connections providers set"

_BOUND = cx.BindingStatus.BOUND.value


# --- the local catalogue, read as the resolver reads a package ---------------


@dataclass(frozen=True)
class Candidate:
    """A capability of the local catalogue with its package metadata."""

    name: str
    origin: str  # kit-shipped | incubated-in-repo
    installed: bool
    component_dir: Path  # where its package metadata is read from
    package: Mapping[str, Any]

    @property
    def version(self) -> str | None:
        component = self.package.get("component")
        if not isinstance(component, Mapping):
            return None
        version = cast("Mapping[str, Any]", component).get("version")
        return version if isinstance(version, str) and version else None

    @property
    def description(self) -> str:
        description = self.package.get("description")
        return description.strip() if isinstance(description, str) else ""


def candidate_of(
    source: caps.CapabilitySource, origin: str, *, installed: bool
) -> Candidate | None:
    """A capability source as a candidate; None when its package file does not read."""
    package = cx.read_package(source.path / "package.yaml")
    if package is None:
        return None
    return Candidate(source.name, origin, installed, source.path, package)


def local_candidates(target_root: Path, source_kit: Path) -> tuple[Candidate, ...]:
    """The local catalogue (`capabilities.local_catalogue`), each package read."""
    out: list[Candidate] = []
    for entry in caps.local_catalogue(target_root, source_kit):
        found = candidate_of(entry.source, entry.origin, installed=entry.installed)
        if found is not None:
            out.append(found)
    return tuple(out)


def find_candidate(target_root: Path, source_kit: Path, name: str) -> Candidate | None:
    return next((c for c in local_candidates(target_root, source_kit) if c.name == name), None)


def as_installed(target_root: Path, candidate: Candidate) -> cx.Installed:
    """The candidate as the resolver would read it once installed or registered:
    its package file where the operation puts it, its companions read where
    they are now, its version of record the one its package declares — the
    version install stamps and register reads (`connections.Installed`)."""
    return cx.Installed(
        name=candidate.name,
        kind=cx.CAPABILITY,
        version=candidate.version,
        file=target_root / ".pkit" / "capabilities" / candidate.name / "package.yaml",
        component_dir=candidate.component_dir,
        package=candidate.package,
    )


# --- the difference between two wirings --------------------------------------


@dataclass(frozen=True)
class RoleState:
    """Who answers a role in one wiring."""

    providers: tuple[str, ...]
    selected: str | None
    active: str | None
    conflict: bool

    @property
    def text(self) -> str:
        if self.active is not None:
            return self.active if self.selected is None else f"{self.active} (selected)"
        if self.conflict:
            return f"conflict: {', '.join(self.providers)} (no selection)"
        if self.selected is not None:
            return f"selection {self.selected!r} is not a provider"
        return "no provider"


@dataclass(frozen=True)
class RoleChange:
    role: str
    before: RoleState | None  # None: nothing named the role
    after: RoleState | None


@dataclass(frozen=True)
class PointRef:
    """A point an active provider defines."""

    address: str
    kind: str
    version: int
    provider: str


@dataclass(frozen=True)
class ConnectionChange:
    """One counterpart whose binding the operation changes."""

    capability: str  # the component declaring the counterpart
    kind: str  # contributes | subscribes | depends-on
    target: str  # the address as written
    pointer: str  # the entry in its package file
    before: str | None  # its status before; None when it was not declared
    after: str | None  # its status after; None when it is no longer declared
    provider_before: str | None  # the capability answering it before, when bound
    provider_after: str | None

    @property
    def made(self) -> bool:
        """Bound after, and not bound before."""
        return self.after == _BOUND and self.before != _BOUND

    @property
    def lost(self) -> bool:
        """Bound before, and not bound after."""
        return self.before == _BOUND and self.after != _BOUND


@dataclass(frozen=True)
class FindingRef:
    """A wiring finding, located relative to the project root."""

    file: str
    path: str
    severity: str
    message: str
    relation: str | None = None

    @property
    def where(self) -> str:
        return f"{self.file}:{self.path}" if self.path else self.file


@dataclass(frozen=True)
class WiringDiff:
    """How one wiring differs from another, in terms that do not depend on where
    the operation read anything from."""

    roles: tuple[RoleChange, ...]
    points_defined: tuple[PointRef, ...]
    points_undefined: tuple[PointRef, ...]
    connections: tuple[ConnectionChange, ...]
    findings_added: tuple[FindingRef, ...]
    findings_resolved: tuple[FindingRef, ...]

    @property
    def made(self) -> tuple[ConnectionChange, ...]:
        return tuple(c for c in self.connections if c.made)

    @property
    def lost(self) -> tuple[ConnectionChange, ...]:
        return tuple(c for c in self.connections if c.lost)


def diff_wiring(target_root: Path, before: cx.Wiring, after: cx.Wiring) -> WiringDiff:
    """What changes from `before` to `after`: roles whose answer changes, points
    defined and no longer defined, counterparts whose status changes, and the
    findings added and resolved. Rule-set pins are left out (the module
    docstring). Deterministic: every part is sorted."""
    roles_before = {r.role: _role_state(r) for r in before.roles}
    roles_after = {r.role: _role_state(r) for r in after.roles}
    roles = tuple(
        RoleChange(role, roles_before.get(role), roles_after.get(role))
        for role in sorted(set(roles_before) | set(roles_after))
        if roles_before.get(role) != roles_after.get(role)
    )
    points_before = {_point_ref(p.point) for p in before.points}
    points_after = {_point_ref(p.point) for p in after.points}
    bindings_before = {_binding_key(b): b for b in before.bindings}
    bindings_after = {_binding_key(b): b for b in after.bindings}
    connections: list[ConnectionChange] = []
    for key in sorted(set(bindings_before) | set(bindings_after)):
        old, new = bindings_before.get(key), bindings_after.get(key)
        change = ConnectionChange(
            capability=key[0],
            kind=key[1],
            target=key[2],
            pointer=key[3],
            before=old.status.value if old is not None else None,
            after=new.status.value if new is not None else None,
            provider_before=_answered_by(old),
            provider_after=_answered_by(new),
        )
        if (change.before, change.provider_before) != (change.after, change.provider_after):
            connections.append(change)
    found_before = Counter(_finding_refs(target_root, before))
    found_after = Counter(_finding_refs(target_root, after))
    return WiringDiff(
        roles=roles,
        points_defined=tuple(sorted(points_after - points_before, key=_point_order)),
        points_undefined=tuple(sorted(points_before - points_after, key=_point_order)),
        connections=tuple(connections),
        findings_added=tuple(sorted((found_after - found_before).elements(), key=_finding_order)),
        findings_resolved=tuple(
            sorted((found_before - found_after).elements(), key=_finding_order)
        ),
    )


def _role_state(role: cx.RoleBinding) -> RoleState:
    return RoleState(role.providers, role.selected, role.active, role.conflict)


def _point_ref(point: cx.Point) -> PointRef:
    return PointRef(point.address, point.kind.value, point.version, point.provider)


def _point_order(point: PointRef) -> tuple[str, str]:
    return (point.address, point.provider)


def _binding_key(binding: cx.Binding) -> tuple[str, str, str, str]:
    c = binding.counterpart
    return (c.capability, c.kind.value, c.target, c.pointer)


def _answered_by(binding: cx.Binding | None) -> str | None:
    """The capability a bound counterpart reaches: its point's provider, or the
    implementation-addressed upstream whose definition exists."""
    if binding is None or binding.status is not cx.BindingStatus.BOUND:
        return None
    if binding.point is not None:
        return binding.point.provider
    return binding.counterpart.target.partition(POINT_SEPARATOR)[0]


def _finding_refs(target_root: Path, wiring: cx.Wiring) -> list[FindingRef]:
    return [
        FindingRef(
            file=_relative(target_root, f.file),
            path=f.path,
            severity=f.severity.value,
            message=f.message,
            relation=f.relation.value if f.relation is not None else None,
        )
        for f in wiring.findings
        if f.relation is not cx.Relation.RULE_SET_PIN
    ]


def _finding_order(finding: FindingRef) -> tuple[str, str, str, str, str]:
    return (finding.file, finding.path, finding.severity, finding.message, finding.relation or "")


def _relative(target_root: Path, file: Path) -> str:
    if file.is_absolute() and file.is_relative_to(target_root):
        file = file.relative_to(target_root)
    return file.as_posix()


# --- role blocks in artefacts (COR-053 point 10) --------------------------------


@dataclass(frozen=True)
class RoleBlockChange:
    """A role block in an artefact whose meaning the operation changes."""

    artefact: str  # its location: `path`, or `path#id` for a collection entry
    key: str  # the role block's key as written
    change: str  # orphaned | adopted | ambiguous


def role_block_changes(
    target_root: Path, before: cx.Wiring, after: cx.Wiring
) -> tuple[RoleBlockChange, ...]:
    """Each role block of an artefact in the declared places that the container
    rule reads differently against `after` than against `before`: orphaned (its
    role loses its active provider — preserved and reported, never an error),
    adopted (an orphaned block's role gains one), or ambiguous (a bare key whose
    word a second active role now shares — to be written qualified, with
    consent). The rule is validation's own (`backbone_schemas.validate_container`);
    only the discrimination is read, so the tree's container schema is applied
    when it loads and an empty one when it does not."""
    discovery = discover_artefacts(target_root)
    if not discovery.with_container:
        return ()
    try:
        schema: Mapping[str, Any] = bs.load_backbone_schema(target_root, "container")
    except (bs.BackboneSchemaMissing, bs.BackboneSchemaInvalid):
        schema = {}
    wiring_before = cx.container_wiring_of(before, target_root)
    wiring_after = cx.container_wiring_of(after, target_root)
    changes: list[RoleBlockChange] = []
    for artefact in discovery.with_container:
        old = bs.validate_container(artefact.carrier, schema, wiring=wiring_before)
        new = bs.validate_container(artefact.carrier, schema, wiring=wiring_after)
        orphaned_before, orphaned_after = set(old.orphaned_roles), set(new.orphaned_roles)
        ambiguous_before, ambiguous_after = _ambiguous_keys(old), _ambiguous_keys(new)
        for key in new.role_blocks:
            if key in orphaned_after - orphaned_before:
                changes.append(RoleBlockChange(artefact.location, key, ORPHANED))
            elif key in orphaned_before - orphaned_after:
                changes.append(RoleBlockChange(artefact.location, key, ADOPTED))
            if key in ambiguous_after - ambiguous_before:
                changes.append(RoleBlockChange(artefact.location, key, AMBIGUOUS))
    return tuple(changes)


def _ambiguous_keys(report: bs.ContainerReport) -> set[str]:
    prefix = f"/{bs.CONTAINER_KEY}/"
    return {
        _unescape(f.location[len(prefix) :])
        for f in report.findings
        if f.kind is bs.FindingKind.AMBIGUOUS_ROLE and f.location.startswith(prefix)
    }


def _unescape(token: str) -> str:
    """One JSON Pointer reference token back to its key (RFC 6901)."""
    return token.replace("~1", "/").replace("~0", "~")


# --- the plans -------------------------------------------------------------------


@dataclass(frozen=True)
class Conflict:
    """A role the install would leave with several providers and no selection."""

    role: str
    providers: tuple[str, ...]
    resolve: tuple[str, ...]  # the command selecting each provider


@dataclass(frozen=True)
class InstallPlan:
    capability: str
    version: str | None
    origin: str
    diff: WiringDiff
    conflicts: tuple[Conflict, ...]
    needs: tuple[FindingRef, ...]  # the errors the install would put on the capability itself
    role_blocks: tuple[RoleBlockChange, ...]


@dataclass(frozen=True)
class FillerLoss:
    """A filler that stops answering a data point."""

    point: str  # the address it answered
    filler: str  # the contributing capability, or the project filler's path
    source: str  # contribution | project filler
    point_after: str  # stays filled | left unfilled | no longer defined


@dataclass(frozen=True)
class UninstallPlan:
    capability: str
    version: str | None
    origin: str
    diff: WiringDiff
    fillers_lost: tuple[FillerLoss, ...]
    left_without_provider: tuple[ConnectionChange, ...]  # others' counterparts it answered
    role_blocks: tuple[RoleBlockChange, ...]
    selections: tuple[str, ...]  # configuration entries naming it, as dotted keys


def plan_install(target_root: Path, candidate: Candidate) -> InstallPlan:
    """What installing (or registering) `candidate` would change in the wiring."""
    before = cx.resolve_wiring(target_root)
    installed = as_installed(target_root, candidate)
    after = cx.resolve_wiring_with(target_root, add=[installed])
    diff = diff_wiring(target_root, before, after)
    conflicted_before = {r.role for r in before.roles if r.conflict}
    conflicts = tuple(
        Conflict(
            r.role,
            r.providers,
            tuple(f"{PROVIDERS_SET} {r.role} {provider}" for provider in r.providers),
        )
        for r in after.roles
        if r.conflict and r.role not in conflicted_before
    )
    own_file = _relative(target_root, installed.file)
    needs = tuple(
        f for f in diff.findings_added if f.file == own_file and f.severity == Severity.ERROR.value
    )
    return InstallPlan(
        capability=candidate.name,
        version=candidate.version,
        origin=candidate.origin,
        diff=diff,
        conflicts=conflicts,
        needs=needs,
        role_blocks=role_block_changes(target_root, before, after),
    )


def plan_uninstall(target_root: Path, name: str, origin: str) -> UninstallPlan:
    """What uninstalling the installed capability `name` would change in the wiring."""
    before = cx.resolve_wiring(target_root)
    after = cx.resolve_wiring_with(target_root, remove=[name])
    diff = diff_wiring(target_root, before, after)
    component = before.declarations.by_name(name)
    return UninstallPlan(
        capability=name,
        version=component.version if component is not None else None,
        origin=origin,
        diff=diff,
        fillers_lost=_fillers_lost(target_root, name, before, after),
        left_without_provider=tuple(c for c in diff.lost if c.capability != name),
        role_blocks=role_block_changes(target_root, before, after),
        selections=_selections_naming(target_root, name),
    )


def _fillers_lost(
    target_root: Path, name: str, before: cx.Wiring, after: cx.Wiring
) -> tuple[FillerLoss, ...]:
    """Its bound contributions, and the project filler files answering a point it
    defines that no active provider would define after it (kept, inert)."""
    losses: list[FillerLoss] = []
    for binding in before.bindings:
        c = binding.counterpart
        if (
            c.capability != name
            or c.kind is not cx.CounterpartKind.CONTRIBUTION
            or binding.status is not cx.BindingStatus.BOUND
        ):
            continue
        losses.append(FillerLoss(c.target, name, "contribution", _point_after(after, c.target)))
    for point in before.points:
        if point.point.provider != name or point.filler is None:
            continue
        address = point.point.address
        state = _point_after(after, address)
        if state == NO_LONGER_DEFINED:
            path = _relative(target_root, point.filler.file)
            losses.append(FillerLoss(address, path, "project filler", state))
    return tuple(sorted(losses, key=lambda f: (f.point, f.source, f.filler)))


def _point_after(after: cx.Wiring, address: str) -> str:
    point = after.data_point(address)
    if point is None:
        return NO_LONGER_DEFINED
    return STAYS_FILLED if point.filled else LEFT_UNFILLED


def _selections_naming(target_root: Path, name: str) -> tuple[str, ...]:
    selections = cx.load_selections(target_root)
    return tuple(
        f"{cx.CONNECTIONS_KEY}.{key}.{entry}"
        for key, block in (
            (cx.PROVIDERS_KEY, selections.providers),
            (cx.SELECTIONS_KEY, selections.selections),
        )
        for entry, capability in sorted(block.items())
        if capability == name
    )


# --- show ------------------------------------------------------------------------


@dataclass(frozen=True)
class PointView:
    address: str
    kind: str
    schema_version: int
    description: str | None
    policy: str | None  # a data point's combination policy in force
    mandatory: str | None  # the reason, when the mark is set
    process: str | None  # an offered process's definition id


@dataclass(frozen=True)
class ExtensionView:
    kind: str  # contributes | subscribes | depends-on
    target: str
    schema_version: int | None
    command: str | None
    mandatory: str | None
    description: str | None


@dataclass(frozen=True)
class ConnectionView:
    """One binding to or from the capability."""

    direction: str  # out: its extension; in: another's extension to its point
    capability: str  # the component declaring the extension
    kind: str
    target: str
    status: str
    provider: str | None  # the capability answering it, when bound


@dataclass(frozen=True)
class RoleView:
    role: str
    state: str  # who answers it in the wiring shown
    providers: tuple[str, ...]
    active: str | None


@dataclass(frozen=True)
class CapabilityView:
    name: str
    version: str | None
    description: str
    origin: str
    installed: bool
    roles: tuple[RoleView, ...]
    accepts: tuple[PointView, ...]
    offers: tuple[PointView, ...]
    extensions: tuple[ExtensionView, ...]
    connections: tuple[ConnectionView, ...]


def show(target_root: Path, candidate: Candidate) -> CapabilityView:
    """The candidate's connections from its package metadata, and what would
    connect here: the live wiring when it is installed, else the wiring the
    project would have with it installed."""
    if candidate.installed:
        wiring = cx.resolve_wiring(target_root)
    else:
        wiring = cx.resolve_wiring_with(target_root, add=[as_installed(target_root, candidate)])
    declared = cx.Declarations.from_installed([as_installed(target_root, candidate)])
    name = candidate.name
    return CapabilityView(
        name=name,
        version=candidate.version,
        description=candidate.description,
        origin=candidate.origin,
        installed=candidate.installed,
        roles=tuple(_role_view(wiring, role) for role in declared.roles_of(name)),
        accepts=tuple(_point_view(p) for p in declared.points if p.kind is cx.PointKind.DATA),
        offers=tuple(_point_view(p) for p in declared.points if p.kind is not cx.PointKind.DATA),
        extensions=tuple(_extension_view(c) for c in declared.counterparts),
        connections=_connections_of(wiring, name),
    )


def _role_view(wiring: cx.Wiring, role: str) -> RoleView:
    binding = wiring.role(role)
    if binding is None:
        return RoleView(role, "no provider", (), None)
    return RoleView(role, _role_state(binding).text, binding.providers, binding.active)


def _point_view(point: cx.Point) -> PointView:
    return PointView(
        address=point.address,
        kind=point.kind.value,
        schema_version=point.version,
        description=point.description,
        policy=point.policy,
        mandatory=point.mandatory,
        process=point.process_id,
    )


def _extension_view(counterpart: cx.Counterpart) -> ExtensionView:
    return ExtensionView(
        kind=counterpart.kind.value,
        target=counterpart.target,
        schema_version=counterpart.version,
        command=counterpart.command,
        mandatory=counterpart.mandatory,
        description=counterpart.description,
    )


def _connections_of(wiring: cx.Wiring, name: str) -> tuple[ConnectionView, ...]:
    out: list[ConnectionView] = []
    for binding in wiring.bindings:
        c = binding.counterpart
        if c.capability == name:
            direction = "out"
        elif _reaches(binding, name):
            direction = "in"
        else:
            continue
        out.append(
            ConnectionView(
                direction=direction,
                capability=c.capability,
                kind=c.kind.value,
                target=c.target,
                status=binding.status.value,
                provider=_answered_by(binding),
            )
        )
    return tuple(sorted(out, key=lambda v: (v.direction != "out", v.target, v.capability)))


def _reaches(binding: cx.Binding, name: str) -> bool:
    """Another capability's counterpart aimed at `name`: at a point it defines, or
    at it by implementation address."""
    if binding.point is not None:
        return binding.point.provider == name
    counterpart = binding.counterpart
    return not counterpart.role_form and counterpart.target.partition(POINT_SEPARATOR)[0] == name


# --- suggestions -------------------------------------------------------------------


@dataclass(frozen=True)
class Suggestion:
    """A capability of the local catalogue that would answer an unmet need. Text only."""

    need: str  # the point address, the role, or the upstream capability
    reason: str  # unfilled point | role without a provider | upstream not installed
    capability: str
    origin: str
    how: str


def suggestions(wiring: cx.Wiring, candidates: Iterable[Candidate]) -> tuple[Suggestion, ...]:
    """For each unmet need of `wiring`, the uninstalled candidates that declare
    what would meet it: a contribution at an unfilled data point's version, the
    role nobody installed provides but an installed counterpart targets, the
    upstream capability an implementation-addressed `depends-on` names. Read
    from package metadata; never installs, never fetches."""
    available = [c for c in candidates if not c.installed]
    if not available:
        return ()
    declared = {c.name: cx.Declarations.from_installed([_as_read(c)]) for c in available}
    out: list[Suggestion] = []
    for point in wiring.points:
        p = point.point
        if p.kind is not cx.PointKind.DATA or point.filled:
            continue
        for candidate in available:
            if any(
                x.kind is cx.CounterpartKind.CONTRIBUTION
                and x.target == p.address
                and x.version == p.version
                for x in declared[candidate.name].counterparts
            ):
                how = f"contributes to it at version {p.version}"
                out.append(
                    Suggestion(p.address, "unfilled point", candidate.name, candidate.origin, how)
                )
    for role in wiring.roles:
        targeted = any(b.counterpart.role == role.role for b in wiring.bindings)
        if role.providers or not targeted:
            continue
        for candidate in available:
            if role.role in declared[candidate.name].roles_of(candidate.name):
                out.append(
                    Suggestion(
                        role.role,
                        "role without a provider",
                        candidate.name,
                        candidate.origin,
                        "provides the role",
                    )
                )
    missing = sorted(
        {
            b.counterpart.target.partition(POINT_SEPARATOR)[0]
            for b in wiring.bindings
            if b.status is cx.BindingStatus.NOT_INSTALLED
        }
    )
    for upstream in missing:
        for candidate in available:
            if candidate.name == upstream:
                out.append(
                    Suggestion(
                        upstream,
                        "upstream not installed",
                        candidate.name,
                        candidate.origin,
                        "is the upstream a process depends on",
                    )
                )
    return tuple(out)


def suggest(target_root: Path, source_kit: Path) -> tuple[Suggestion, ...]:
    """The suggestions for the project's live wiring — the run's one resolution
    (`connections.shared_wiring`) — from the local catalogue."""
    return suggestions(cx.shared_wiring(target_root), local_candidates(target_root, source_kit))


def suggestion_line(suggestion: Suggestion) -> str:
    return (
        f"{suggestion.need} ({suggestion.reason}): {suggestion.capability} "
        f"({suggestion.origin}) {suggestion.how} — see `pkit capabilities show "
        f"{suggestion.capability}`"
    )


def _as_read(candidate: Candidate) -> cx.Installed:
    """A candidate as its package declares it, for reading its declarations only."""
    return cx.Installed(
        name=candidate.name,
        kind=cx.CAPABILITY,
        version=candidate.version,
        file=candidate.component_dir / "package.yaml",
        component_dir=candidate.component_dir,
        package=candidate.package,
    )


# --- rendering ----------------------------------------------------------------------


def to_json(value: CapabilityView | InstallPlan | UninstallPlan) -> str:
    """The machine form: every field, keys sorted, stable across runs."""
    document = dataclasses.asdict(value)
    if isinstance(value, InstallPlan):
        document = {"operation": INSTALL, **document}
    elif isinstance(value, UninstallPlan):
        document = {"operation": UNINSTALL, **document}
    return json.dumps(document, indent=2, sort_keys=True) + "\n"


def render_show(view: CapabilityView) -> str:
    state = "installed" if view.installed else "not installed"
    lines = [
        cli_render.style("title", f"Capability {view.name!r}")
        + f" v{view.version or '?'} ({view.origin}, {state})",
    ]
    if view.description:
        lines.append(f"  {view.description}")
    where = "the live wiring" if view.installed else "the wiring this project would have with it"
    lines.append(f"  read from its package metadata; what connects is {where}")
    lines.extend(_section("Roles it provides", [f"{r.role} — {r.state}" for r in view.roles]))
    lines.extend(_section("Points it accepts", [_point_text(p) for p in view.accepts]))
    lines.extend(_section("Points it offers", [_point_text(p) for p in view.offers]))
    lines.extend(_section("Extensions", [_extension_text(e) for e in view.extensions]))
    lines.extend(_section("What connects here", [_connection_text(c) for c in view.connections]))
    return "\n".join(lines) + "\n"


def render_install_plan(plan: InstallPlan) -> str:
    lines = _plan_header("Install plan", plan.capability, plan.version, plan.origin, "installed")
    lines.extend(_section("Connections it would make", [_change_text(c) for c in plan.diff.made]))
    lines.extend(_section("Connections it would break", [_change_text(c) for c in plan.diff.lost]))
    conflict_lines: list[str] = []
    for conflict in plan.conflicts:
        conflict_lines.append(
            f"{conflict.role} is provided by {', '.join(conflict.providers)} and none is "
            f"selected; select one:"
        )
        conflict_lines.extend(f"  {command}" for command in conflict.resolve)
    lines.extend(_section("Role conflicts", conflict_lines))
    lines.extend(_section("What it needs", [_finding_text(f) for f in plan.needs]))
    lines.extend(_role_block_section(plan.role_blocks))
    lines.extend(_diff_tail(plan.diff, "install"))
    return "\n".join(lines) + "\n"


def render_uninstall_plan(plan: UninstallPlan) -> str:
    lines = _plan_header("Uninstall plan", plan.capability, plan.version, plan.origin, "removed")
    lines.extend(
        _section(
            "Fillers lost",
            [
                f"{f.point} ← {f.filler} ({f.source}); the point is {f.point_after}"
                for f in plan.fillers_lost
            ],
        )
    )
    processes = [
        c for c in plan.left_without_provider if c.kind == cx.CounterpartKind.DEPENDENCY.value
    ]
    others = [
        c for c in plan.left_without_provider if c.kind != cx.CounterpartKind.DEPENDENCY.value
    ]
    lines.extend(
        _section("Processes left without a provider", [_change_text(c) for c in processes])
    )
    lines.extend(
        _section("Other counterparts left without a provider", [_change_text(c) for c in others])
    )
    lines.extend(_role_block_section(plan.role_blocks))
    lines.extend(
        _section(
            "Selections left naming it",
            [f"{key} — remove it once the capability is gone" for key in plan.selections],
        )
    )
    lines.extend(_diff_tail(plan.diff, "uninstall"))
    return "\n".join(lines) + "\n"


def _plan_header(title: str, name: str, version: str | None, origin: str, verb: str) -> list[str]:
    return [
        cli_render.style("title", f"{title} — capability {name!r}")
        + f" v{version or '?'} ({origin})",
        f"  computed by the wiring resolver over this project with {name!r} {verb}; "
        f"nothing is written",
    ]


def _section(heading: str, rows: Sequence[str]) -> list[str]:
    """A heading with its count, then one row per line — `none` when empty, so an
    empty section reads as checked rather than missing."""
    lines = ["", "  " + cli_render.style("heading", f"{heading} ({len(rows)})")]
    lines.extend(f"    {row}" for row in rows or ["none"])
    return lines


def _role_block_section(changes: Sequence[RoleBlockChange]) -> list[str]:
    meaning = {
        ORPHANED: "orphaned: preserved and reported until a provider of the role is active",
        ADOPTED: "adopted: validated again by the role's new provider",
        AMBIGUOUS: "ambiguous: a second active role shares the word; write the qualified key",
    }
    return _section(
        "Role blocks in artefacts",
        [f"{c.artefact} /{bs.CONTAINER_KEY}/{c.key} — {meaning[c.change]}" for c in changes],
    )


def _diff_tail(diff: WiringDiff, operation: str) -> list[str]:
    lines = _section(
        "Roles",
        [
            f"{r.role}: {r.before.text if r.before else 'not named'} → "
            f"{r.after.text if r.after else 'not named'}"
            for r in diff.roles
        ],
    )
    lines.extend(
        _section(
            "Points",
            [f"+ {_point_ref_text(p)}" for p in diff.points_defined]
            + [f"- {_point_ref_text(p)}" for p in diff.points_undefined],
        )
    )
    lines.extend(
        _section(
            f"Findings the {operation} would add", [_finding_text(f) for f in diff.findings_added]
        )
    )
    lines.extend(
        _section(
            f"Findings the {operation} would resolve",
            [_finding_text(f) for f in diff.findings_resolved],
        )
    )
    return lines


def _point_text(point: PointView) -> str:
    parts = [f"{point.kind} v{point.schema_version}"]
    if point.policy:
        parts.append(point.policy)
    if point.process:
        parts.append(f"process {point.process}")
    if point.mandatory:
        parts.append(f"mandatory: {point.mandatory}")
    text = f"{point.address} ({', '.join(parts)})"
    return f"{text} — {point.description}" if point.description else text


def _extension_text(extension: ExtensionView) -> str:
    parts: list[str] = []
    if extension.schema_version is not None:
        parts.append(f"v{extension.schema_version}")
    if extension.command:
        parts.append(f"command {extension.command}")
    if extension.mandatory:
        parts.append(f"mandatory: {extension.mandatory}")
    detail = f" ({', '.join(parts)})" if parts else ""
    text = f"{extension.kind} {extension.target}{detail}"
    return f"{text} — {extension.description}" if extension.description else text


def _connection_text(view: ConnectionView) -> str:
    answered = f" → {view.provider}" if view.provider else ""
    return (
        f"{view.direction:<3} {view.capability} {view.kind} {view.target}{answered}: {view.status}"
    )


def _change_text(change: ConnectionChange) -> str:
    provider = change.provider_after or change.provider_before
    answered = f" → {provider}" if provider else ""
    before = change.before or "not declared"
    after = change.after or "not declared"
    return f"{change.capability} {change.kind} {change.target}{answered}: {before} → {after}"


def _point_ref_text(point: PointRef) -> str:
    return f"{point.address} ({point.kind} v{point.version}, {point.provider})"


def _finding_text(finding: FindingRef) -> str:
    label = f" [{finding.relation}]" if finding.relation else ""
    return f"{finding.severity:<7}{label} {finding.where} — {finding.message}"
