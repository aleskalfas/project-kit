"""The wiring resolver — connection points (COR-053 point 7), read-only.

This module is the **one** computation of the wiring: `pkit validate` reports
it, and the graph, the status report and the install / uninstall plans
(COR-053 points 7 and 8) read its `Wiring` rather than resolving anything of
their own. A plan resolves a hypothetical set of components the same way:
`resolve_wiring_with` is `resolve_wiring` over the installed set plus or
minus a candidate, every other input read from the tree as the live wiring
reads it (`capability_plans` is its reader).

It reads, and reads only:

- each registered component's `package.yaml` — `connections.roles`,
  `extension-points.accepts` / `offers`, `extensions.contributes` /
  `subscribes` / the generated `depends-on` — and the companion schemas its
  points name (for the fingerprint);
- the backbone configuration's two selection keys, `connections.providers`
  and `connections.selections`, read forgivingly (`project_config.read_config`);
- the installed versions: the backbone manifest's `backbone_version` and each
  component's version of record;
- the project's filler files — every file under the fillers prefix of the
  internal documentation root, parsed once per run (`project_fillers`), of
  which the wiring reads only the envelope's `schema_version`.

It resolves wiring, not data: it never runs a filler command, and it never
parses a process definition — an implementation-addressed upstream is found
among the offered points, or by its definition file existing at the
conventional path (COR-053 point 6 reads the mark from package metadata).
What each data point resolves to — its fillers combined by its policy — is
the second layer over this one, `project_kit.data_points`, which reads this
module's `Wiring` and its filler files rather than resolving either again.

`resolve` is a pure function of those inputs, so the same repository state
yields the same `Wiring`, finding for finding. It computes:

- the **active provider** per qualified role — the one installed provider, or
  the one the provider selection names; several and no selection is a *role
  conflict* (COR-053 point 1). An installed provider that is not the active one
  keeps its commands; its points are not defined and its own extensions are
  inert;
- the points each active role defines, and for every contribution,
  subscription and `depends-on` entry its point and whether the two are
  **compatible** — equal integers (point 5) — else the counterpart is *inert*;
- the accepted points nothing fills, the **mandatory** marks left unmet, and
  the **mandatory cycles** marks facing each other form (point 6);
- the schema **fingerprints** two installed providers of one qualified point
  and version must agree on (point 5) — computed, compared, stored nowhere;
- the **version relations** (`Relation`): `requires_backbone` against the
  installed backbone, capability dependency ranges against installed versions
  (COR-030), contributions and subscriptions against point versions,
  `depends-on` entries against the offered process interface's version, a
  project filler against its point's version, and a rule set's inheritance
  pins against the inherited sets' majors (COR-051 point 7), read from the
  rule-set files by `rule_sets.pin_checks`. A version range is compared with a
  version in one place, `range_admits`, which the capability install and
  register gates, the capability and backbone upgrade gates and the dependency
  check they share call too, reading a package file as the resolver does
  (`read_package`).

Disposition follows the direction split of COR-030 as COR-053 point 6 applies
it: the side carrying a mandatory mark, or the dependent of a version range,
carries the error with the fix named; the side it targets is warned, with the
counterpart named.

`pkit validate` runs the resolver as two members, each finding under the
functionality it concerns (`connections_outcome`, `versions_outcome`):
`connections` — the resolved wiring and its findings — and `versions` — how
many of each relation were checked and each version finding labelled with its
relation. Within one run the wiring is resolved once (`shared_wiring`, ADR-057
point 2): those two members read it, and so does container validation in the
`friction` and `rule-sets` members, through `container_wiring` — the active
roles and, for each data point their providers define, its version and its
point schema (COR-053 point 10). `package_validate.check_wiring` is the same
resolution for the register pre-flight and the plans. The
configuration pass reads the same resolved wiring to check the two selection
keys: a provider selection against the declarations, a contributor selection
against the active provider's point and its contributors (`Wiring.data_point`,
`PointBinding.contributors`). It also owns the last relation, the configuration
file's shape against the schema the installed backbone ships.

A stale generated `depends-on` is the packages pass's finding
(`process_dependencies.staleness`): detecting it means reading the process
definitions this module never opens. What it offers the other readers of
`depends_on` is the resolved wiring itself: health finds the implementation of
a role-addressed upstream through `Wiring.offered_process`, and the capability
lifecycle refuses or warns on `Wiring.unmet_marks` (COR-053 point 6).
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import shlex
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path, PurePosixPath
from typing import Any, cast

from jsonschema import Draft202012Validator
from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.version import InvalidVersion, Version
from ruamel.yaml import YAML

from project_kit import backbone_schemas as bs
from project_kit import docs_roots, rule_sets, validators
from project_kit.manifest import read_backbone_manifest, read_component_manifest
from project_kit.package_validate import (
    POINT_SEPARATOR,
    ROLE_QUALIFIER,
    Severity,
    installed_package_files,
    relative_path_problem,
    role_of,
)
from project_kit.project_config import PROJECT_CONFIG_RELPATH, project_config_path, read_config
from project_kit.schemas_validate import _build_registry_for_paths, _kit_defs_schema_paths
from project_kit.working_tree import working_tree

_yaml = YAML(typ="safe")

# The configuration block and its two selection keys (COR-053 point 7).
CONNECTIONS_KEY = "connections"
PROVIDERS_KEY = "providers"
SELECTIONS_KEY = "selections"

# The configuration command that writes a provider selection: a role conflict
# names it, once per provider, as the exact fix (`provider_set_command`).
PROVIDERS_SET_COMMAND = "pkit connections providers set"

# A component's companion schemas and, by convention, its process definitions
# (`schemas/<process-id>.yaml`, the process area README; `pkit process new`
# stamps them there), relative to its root. Of a definition file only the
# existence is consulted, never the content.
SCHEMAS_DIR = "schemas"

# The kind of registry entry that may provide a role (COR-053 point 1).
CAPABILITY = "capability"

# The package key of a component's backbone range (COR-010, COR-017).
REQUIRES_BACKBONE_KEY = "requires_backbone"

# The combination policies of a data point (COR-052 point 3). A point that
# declares none is `single`: one answer, and several contributors need a
# selection rather than being merged silently.
SINGLE = "single"
UNION = "union"
ADDITIVE = "additive"
COMBINATIONS = (SINGLE, UNION, ADDITIVE)


# --- the data model ------------------------------------------------------


class PointKind(Enum):
    """The three kinds of one mechanism (COR-053 point 2)."""

    DATA = "data"
    PROCESS = "process"
    EVENT = "event"


class CounterpartKind(Enum):
    """What sits at the other end of a connection, by the key that declares it."""

    CONTRIBUTION = "contributes"
    SUBSCRIPTION = "subscribes"
    DEPENDENCY = "depends-on"


# The point kind each counterpart kind connects to.
_TARGET_KIND = {
    CounterpartKind.CONTRIBUTION: PointKind.DATA,
    CounterpartKind.SUBSCRIPTION: PointKind.EVENT,
    CounterpartKind.DEPENDENCY: PointKind.PROCESS,
}


class BindingStatus(Enum):
    """How a counterpart stands against the wiring."""

    BOUND = "bound"  # a compatible point of an active provider, or an existing upstream
    INERT_VERSION = "inert (version)"  # the point exists; the versions differ
    INERT_PROVIDER = "inert (provider)"  # its own capability is a provider not selected
    NO_ACTIVE_PROVIDER = "no active provider"  # the target role has no active provider
    NO_SUCH_POINT = "no such point"  # the provider defines no such point / upstream
    NOT_INSTALLED = "not installed"  # an implementation-addressed upstream's capability


class Relation(Enum):
    """A version relation the resolver checks; its findings are reported under
    the `versions` heading, labelled with the value."""

    BACKBONE_RANGE = "backbone range"  # `requires_backbone` (COR-010, COR-017)
    CAPABILITY_RANGE = "capability dependency range"  # `requires_capabilities` (COR-030)
    POINT_VERSION = "point version"  # a contribution or subscription (COR-053 point 5)
    INTERFACE_VERSION = "process interface version"  # a `depends-on` entry (COR-036)
    FILLER_VERSION = "project filler version"  # a project filler file (COR-052 point 2)
    RULE_SET_PIN = "rule-set pin"  # an inherited rule set's major version (COR-051 point 7)


# The order the `versions` heading reports them in.
_RELATION_ORDER = {relation: index for index, relation in enumerate(Relation)}


@dataclass(frozen=True)
class Installed:
    """One registered component whose package file is present — or, for a plan,
    a candidate: `file` is where its package file sits once it is installed, so
    findings are located where the operation will put them, and `component_dir`
    is where its companion schemas and definitions are read from now."""

    name: str
    kind: str  # "capability" | "adapter"
    version: str | None  # the installed version of record; None when unreadable
    file: Path  # its package.yaml
    component_dir: Path
    package: Mapping[str, Any]


@dataclass(frozen=True)
class Point:
    """A point one installed provider defines (COR-053 point 2)."""

    address: str  # <publisher>::<role>:<point>
    role: str  # <publisher>::<role>
    kind: PointKind
    version: int
    provider: str  # the capability defining it
    pointer: str  # JSON Pointer to the declaration in the provider's package file
    combination: str | None = None  # data: "single" | "union" | None
    mandatory: str | None = None  # the reason, when the mark is set
    schema: str | None = None  # companion schema, relative to the provider's schemas/
    process_id: str | None = None  # process: the offered definition's id
    fingerprint: str | None = None  # sha256 of the canonical companion schema, when readable
    description: str | None = None  # the declaration's prose; read by people, never parsed

    @property
    def policy(self) -> str | None:
        """A data point's combination policy in force: as declared, `single` when
        it declares none (COR-052 point 3); None for a process or an event."""
        if self.kind is not PointKind.DATA:
            return None
        return self.combination or SINGLE


@dataclass(frozen=True)
class Counterpart:
    """One contribution, subscription or `depends-on` entry (COR-053 point 3)."""

    capability: str  # the component declaring it
    kind: CounterpartKind
    target: str  # the address as written; a `depends-on` entry may use `<capability>:<id>`
    version: int | None  # the version it targets; a `depends-on` entry may leave it out
    pointer: str  # JSON Pointer to the entry in its package file
    mandatory: str | None = None  # the reason, when the mark is set
    command: str | None = None
    description: str | None = None  # the entry's optional prose; never parsed

    @property
    def role_form(self) -> bool:
        """Addressed by role (`::` present) rather than by implementation."""
        return ROLE_QUALIFIER in self.target

    @property
    def role(self) -> str | None:
        return role_of(self.target) if self.role_form else None


@dataclass(frozen=True)
class Binding:
    """A counterpart against its resolved target."""

    counterpart: Counterpart
    point: Point | None  # the point it resolved to, when there is one
    status: BindingStatus


@dataclass(frozen=True)
class RoleBinding:
    """Who answers one qualified role (COR-053 point 1)."""

    role: str
    providers: tuple[str, ...]  # installed capabilities providing it, sorted
    selected: str | None  # the provider-selection entry as written, valid or not
    active: str | None  # the one active provider, or None

    @property
    def conflict(self) -> bool:
        """Several installed providers and no selection."""
        return len(self.providers) > 1 and self.selected is None


@dataclass(frozen=True)
class ProjectFiller:
    """A project filler file answering a data point (COR-052 point 2)."""

    file: Path
    version: int  # the `schema_version` its envelope carries


@dataclass(frozen=True)
class PointBinding:
    """A point of an active role with every counterpart aimed at it."""

    point: Point
    bindings: tuple[Binding, ...]  # every counterpart resolved to this point, in order
    filler: ProjectFiller | None = None  # data: the project's own filler, when one exists
    selected: str | None = None  # data: the contributor-selection entry for a `single` point

    @property
    def bound(self) -> tuple[Binding, ...]:
        return tuple(b for b in self.bindings if b.status is BindingStatus.BOUND)

    @property
    def filler_compatible(self) -> bool:
        """A project filler exists and targets the point's version (COR-052 point 5)."""
        return self.filler is not None and self.filler.version == self.point.version

    @property
    def filled(self) -> bool:
        """Filled by something other than the default (COR-053 point 6): a bound
        contribution, or a project filler at a compatible version."""
        return bool(self.bound) or self.filler_compatible

    @property
    def mark_unmet(self) -> bool:
        """A mandatory data point filled only by its default (COR-053 point 6) —
        what `pkit validate` reports as an error on the point's provider."""
        return (
            self.point.mandatory is not None
            and self.point.kind is PointKind.DATA
            and not self.filled
        )

    @property
    def contributors(self) -> tuple[str, ...]:
        """Every capability declaring a contribution to this point, sorted, whether
        or not the contribution is bound — the candidates of a contributor selection
        (COR-052 point 4)."""
        return tuple(
            sorted(
                {
                    b.counterpart.capability
                    for b in self.bindings
                    if b.counterpart.kind is CounterpartKind.CONTRIBUTION
                }
            )
        )


@dataclass(frozen=True)
class Finding:
    """One finding, located by file and JSON Pointer.

    `relation` names the version relation a finding checks; None for the
    connection findings proper (roles, points, marks, cycles, fingerprints).
    """

    file: Path  # absolute, or relative to the project root
    path: str  # "" for the file as a whole
    severity: Severity
    message: str
    relation: Relation | None = None


@dataclass(frozen=True)
class Declarations:
    """Everything a set of installed package files declares about connections."""

    installed: tuple[Installed, ...]
    points: tuple[Point, ...]  # every installed provider's points, active or not
    counterparts: tuple[Counterpart, ...]

    @classmethod
    def from_installed(cls, installed: Iterable[Installed]) -> Declarations:
        """The declarations of these components: the live set (`load_declarations`),
        or a plan's hypothetical one — the installed set plus or minus a candidate."""
        components = tuple(installed)
        return cls(
            installed=components,
            points=tuple(p for c in components for p in _points_of(c)),
            counterparts=tuple(x for c in components for x in _counterparts_of(c)),
        )

    def by_name(self, name: str) -> Installed | None:
        return next((i for i in self.installed if i.name == name), None)

    def roles_of(self, name: str) -> tuple[str, ...]:
        component = self.by_name(name)
        return _roles(component.package) if component is not None else ()

    def providers_of(self, role: str) -> tuple[str, ...]:
        """The installed capabilities providing `role`, sorted."""
        return tuple(
            sorted(
                i.name for i in self.installed if i.kind == CAPABILITY and role in _roles(i.package)
            )
        )

    def role_pointer(self, name: str, role: str) -> str | None:
        """Where the component `name` declares that it provides `role`: a JSON
        Pointer into its package file; None when no such component is installed."""
        component = self.by_name(name)
        return _roles_pointer(component, role) if component is not None else None


@dataclass(frozen=True)
class Selections:
    """The configuration's two selection keys, as read (COR-053 point 7)."""

    providers: Mapping[str, str] = field(default_factory=dict[str, str])
    selections: Mapping[str, str] = field(default_factory=dict[str, str])


@dataclass(frozen=True)
class Wiring:
    """The resolved wiring of one project: what the graph, status and plans read."""

    backbone_version: str | None
    declarations: Declarations
    roles: tuple[RoleBinding, ...]  # sorted by role
    points: tuple[PointBinding, ...]  # the active roles' points, sorted by address
    bindings: tuple[Binding, ...]  # every counterpart, in declaration order
    findings: tuple[Finding, ...]  # sorted by file, pointer, severity, message
    checked: Mapping[Relation, int] = field(default_factory=dict[Relation, int])

    def active_roles(self) -> frozenset[str]:
        return frozenset(r.role for r in self.roles if r.active is not None)

    def role(self, role: str) -> RoleBinding | None:
        """Who answers the qualified role `role`, or None when nothing names it."""
        return next((r for r in self.roles if r.role == role), None)

    def data_point(self, address: str) -> PointBinding | None:
        """The data point at `address` as the active provider of its role defines it,
        with every counterpart resolved to it; None when no active provider defines
        one — a point only an unselected provider declares is not defined in the
        project (COR-053 point 1)."""
        return next(
            (
                p
                for p in self.points
                if p.point.address == address and p.point.kind is PointKind.DATA
            ),
            None,
        )

    def offered_process(self, address: str) -> Point | None:
        """The process offered at the role address `address` as the active provider
        of its role defines it — the implementation a role-addressed `depends_on`
        entry reaches (COR-053 point 2); None when no active provider offers a
        process there. Health reads it to find the upstream of a role-addressed
        hand-off contract rather than resolving roles of its own."""
        return next(
            (
                p.point
                for p in self.points
                if p.point.address == address and p.point.kind is PointKind.PROCESS
            ),
            None,
        )

    def unmet_marks(self, kind: CounterpartKind | None = None) -> tuple[Binding, ...]:
        """The counterparts, of `kind` or of every kind, whose mandatory mark this
        wiring leaves unmet (`mark_unmet`), in declaration order. The capability
        lifecycle reads the `depends-on` ones to refuse or warn (COR-053 point 6)."""
        return tuple(
            b
            for b in self.bindings
            if (kind is None or b.counterpart.kind is kind) and self.mark_unmet(b)
        )

    def mark_unmet(self, binding: Binding) -> bool:
        """Whether `binding` carries a mandatory mark this wiring leaves unmet —
        what `pkit validate` reports as an error on the side carrying it (COR-053
        point 6): its target missing, or at another version. An unselected
        provider's marks bind nothing (point 1), and a mark aimed at a role in
        conflict waits on the conflict, which is the finding."""
        c = binding.counterpart
        if c.mandatory is None or binding.status in (
            BindingStatus.BOUND,
            BindingStatus.INERT_PROVIDER,
        ):
            return False
        if binding.status is BindingStatus.NO_ACTIVE_PROVIDER:
            return not self.declarations.providers_of(c.role or "")
        return True

    def errors(self) -> tuple[Finding, ...]:
        return tuple(f for f in self.findings if f.severity is Severity.ERROR)

    def warnings(self) -> tuple[Finding, ...]:
        return tuple(f for f in self.findings if f.severity is Severity.WARNING)

    def connection_findings(self) -> tuple[Finding, ...]:
        """Roles, points, mandatory marks, cycles, fingerprints: the `connections` heading."""
        return tuple(f for f in self.findings if f.relation is None)

    def version_findings(self) -> tuple[Finding, ...]:
        """The version relations, grouped by relation: the `versions` heading."""
        found = (f for f in self.findings if f.relation is not None)
        return tuple(sorted(found, key=lambda f: (_relation_rank(f), _finding_key(f))))


# --- reading the repository -----------------------------------------------


def load_declarations(target_root: Path) -> Declarations:
    """Read every registered component's package file for its connections.

    Shape is the package schema's business (`package_validate`): a slice that
    is not the expected type is skipped here, never reported twice.
    """
    return Declarations.from_installed(_installed_components(target_root))


def _installed_components(target_root: Path) -> list[Installed]:
    """Every registered component whose package file reads, in registry order."""
    backbone = read_backbone_manifest(target_root)
    entries = {e.name: e for e in backbone.components} if backbone is not None else {}
    installed: list[Installed] = []
    for name, component_dir, file in installed_package_files(target_root):
        package = read_package(file)
        if package is None:
            continue  # the packages pass reports the parse error
        entry = entries.get(name)
        installed.append(
            Installed(
                name=name,
                kind=entry.kind if entry is not None else CAPABILITY,
                version=_version_of_record(
                    target_root, entry.manifest if entry is not None else None, package
                ),
                file=file,
                component_dir=component_dir,
                package=package,
            )
        )
    return installed


def read_package(file: Path) -> Mapping[str, Any] | None:
    """A package file as the resolver reads it: its parsed YAML, every key as its
    text; None when it cannot be read, does not parse, or is not a mapping."""
    try:
        raw: Any = _yaml.load(file.read_text(encoding="utf-8"))
    except Exception:
        return None
    return _mapping(_string_keys(raw))


def load_selections(target_root: Path) -> Selections:
    """The configuration's `connections` block, read forgivingly (COR-048 point 4):
    anything malformed reads as no selection, and the configuration pass reports it."""
    block = _mapping(read_config(target_root).get(CONNECTIONS_KEY))
    if block is None:
        return Selections()
    return Selections(
        providers=_string_map(block.get(PROVIDERS_KEY)),
        selections=_string_map(block.get(SELECTIONS_KEY)),
    )


def resolve_wiring(target_root: Path) -> Wiring:
    """The live wiring of the project at `target_root`, with the rule-set pins
    read from its rule-set files among the version relations."""
    return resolve_wiring_with(target_root)


def resolve_wiring_with(
    target_root: Path,
    *,
    add: Iterable[Installed] = (),
    remove: Iterable[str] = (),
) -> Wiring:
    """The wiring the project at `target_root` would have with the components in
    `add` installed and those named in `remove` not; with neither, the live wiring.

    What a plan predicts (COR-053 point 8), computed by the one resolver: only
    the component set is hypothetical. The selections, the installed backbone
    version, the project's filler files and the rule-set pins are read from the
    tree exactly as the live wiring reads them, and the candidates in `add` come
    after the installed components, where install and register append them to
    the registry — so the wiring the operation then leaves is this one.
    """
    added = tuple(add)
    removed = frozenset(remove)
    backbone = read_backbone_manifest(target_root)
    declarations = Declarations.from_installed(
        (*(c for c in _installed_components(target_root) if c.name not in removed), *added)
    )
    fillers = project_fillers(target_root)
    wiring = resolve(
        declarations,
        load_selections(target_root),
        backbone.backbone_version if backbone is not None else None,
        definition_exists=lambda capability, process_id: _definition_file_exists(
            declarations, capability, process_id
        ),
        filler=lambda address: _project_filler(target_root, fillers, address),
        config_file=project_config_path(target_root),
    )
    pin_checks = rule_sets.pin_checks(rule_sets.discover_rule_sets(target_root))
    pins = rule_set_pin_findings(pin_checks)
    return dataclasses.replace(
        wiring,
        findings=tuple(sorted((*wiring.findings, *pins), key=_finding_key)),
        checked={**wiring.checked, Relation.RULE_SET_PIN: len(pin_checks)},
    )


def shared_wiring(target_root: Path) -> Wiring:
    """The live wiring, resolved once per run of `pkit validate` and shared by
    every member that reads it (ADR-057 point 2: a second computation is a
    defect). Outside a run — a focused surface — it resolves afresh."""
    return validators.once_per_run(
        ("wiring", target_root.resolve()), lambda: resolve_wiring(target_root)
    )


# --- what the container reads of the wiring (COR-053 point 10) -----------------


def container_wiring(target_root: Path) -> bs.ContainerWiring:
    """What container validation reads of the run's wiring: the provider of each
    active role, and every data point those providers define with its version
    and its point schema — loaded once per run, like the wiring it comes from.

    Only data points: a point block is data a role's provider keeps about an
    artefact, versioned as a project filler is (COR-052 points 2 and 5); a
    process or an event point has no data to keep there.
    """
    return validators.once_per_run(
        ("container-wiring", target_root.resolve()),
        lambda: _container_wiring(shared_wiring(target_root), target_root),
    )


def container_wiring_of(wiring: Wiring, target_root: Path) -> bs.ContainerWiring:
    """What container validation would read of `wiring` — a plan's hypothetical
    one (`resolve_wiring_with`), so the plan judges a role block by the rule
    validation applies, against the wiring the operation would leave."""
    return _container_wiring(wiring, target_root)


def _container_wiring(wiring: Wiring, target_root: Path) -> bs.ContainerWiring:
    return bs.ContainerWiring(
        providers={r.role: r.active for r in wiring.roles if r.active is not None},
        points={
            p.point.address: _active_point(wiring.declarations, p.point, target_root)
            for p in wiring.points
            if p.point.kind is PointKind.DATA
        },
    )


def _active_point(declarations: Declarations, point: Point, target_root: Path) -> bs.ActivePoint:
    """A data point with its point schema loaded: the companion under the
    provider's `schemas/`, its `$ref`s resolved against its siblings and the
    shared `_defs/` library, as capability data is (`data_validate`). A schema
    that cannot be loaded leaves the point without a validator and says why;
    the packages pass reports a missing companion."""
    component = declarations.by_name(point.provider)
    if component is None or point.schema is None or relative_path_problem(point.schema):
        return bs.ActivePoint(point.version, unavailable="no readable companion is declared")
    schemas_dir = component.component_dir / SCHEMAS_DIR
    path = schemas_dir / point.schema
    schema, reason = bs.load_schema_document(path)
    if schema is None:
        where = validators.location_of(path, target_root)
        return bs.ActivePoint(point.version, unavailable=f"{where} is {(reason or '').rstrip('.')}")
    registry, _unloadable = _build_registry_for_paths(
        [*sorted(schemas_dir.glob("*.schema.json")), *_kit_defs_schema_paths(target_root)],
        target_root,
        already_reported=set(),
    )
    return bs.ActivePoint(point.version, validator=Draft202012Validator(schema, registry=registry))


# --- relations read from other files: project fillers and rule-set pins -----


@dataclass(frozen=True)
class FillerFile:
    """One file under the fillers prefix, as read (COR-052 point 2).

    `address` is the point its path names by the location rule
    (`backbone_schemas.filler_address`); None for a file that names none — a
    stray, reported rather than skipped. `document` is its parsed YAML; None
    when it could not be read, and then `problem` says why.
    """

    path: str  # repository-relative POSIX path
    address: str | None
    document: Any = None
    problem: str | None = None

    @property
    def version(self) -> int | None:
        """The envelope's `schema_version` when it is an integer; None otherwise
        (the envelope pass reports the shape)."""
        document = _mapping(self.document)
        return _point_version(document.get("schema_version")) if document is not None else None


def fillers_prefix(target_root: Path) -> PurePosixPath:
    """Where project filler files live, relative to the repository root: the
    backbone's sub-path under the internal documentation root (COR-052 point 2).
    Derived from the current root on every read: no command places a filler
    yet, so none records the prefix as a chosen location (COR-049 point 5)."""
    internal = docs_roots.resolve_roots(target_root).internal
    return PurePosixPath(internal.as_posix()) / bs.FILLERS_SUBPATH


def project_fillers(target_root: Path) -> tuple[FillerFile, ...]:
    """Every file under the fillers prefix, in path order, read once per run of
    `pkit validate` and shared by the wiring and the data points resolved over it.

    The files are those of the working tree's one listing (ADR-057 point 2); a
    project with no folder at the prefix has none, and the listing is not taken.
    """
    return validators.once_per_run(
        ("project-fillers", target_root.resolve()), lambda: _read_fillers(target_root)
    )


def _read_fillers(target_root: Path) -> tuple[FillerFile, ...]:
    prefix = fillers_prefix(target_root)
    if not (target_root / prefix).is_dir():
        return ()
    below = f"{prefix.as_posix()}/"
    out: list[FillerFile] = []
    for rel in working_tree(target_root).files():
        if not rel.startswith(below):
            continue
        address = bs.filler_address(rel[len(below) :])
        if address is None:
            out.append(FillerFile(rel, None))
            continue
        try:
            document: Any = _yaml.load((target_root / rel).read_text(encoding="utf-8"))
        except Exception as exc:  # unreadable, or ruamel's own hierarchy
            out.append(FillerFile(rel, address, problem=f"does not parse as YAML: {exc}"))
            continue
        out.append(FillerFile(rel, address, document=_string_keys(document)))
    return tuple(out)


def project_filler(target_root: Path, address: str) -> ProjectFiller | None:
    """The project filler file answering the data point `address`, with the
    version its envelope targets; None when there is none, or when its envelope
    carries no integer `schema_version` — a malformed envelope fills nothing, and
    the data points' envelope pass reports it.

    It lives at the path the address maps to under the internal documentation
    root (COR-052 point 2; the lifecycle README, "Where a project filler file
    lives": `<internal-root>/pkit/fillers/<publisher>/<role>/<point>.yaml`).
    `resolve` compares its version with the point's — a mismatch is an error
    (COR-052 point 2) — and counts a compatible filler as filling a mandatory point.
    """
    return _project_filler(target_root, project_fillers(target_root), address)


def _project_filler(
    target_root: Path, fillers: Iterable[FillerFile], address: str
) -> ProjectFiller | None:
    found = next((f for f in fillers if f.address == address), None)
    if found is None or found.version is None:
        return None
    return ProjectFiller(target_root / found.path, found.version)


def rule_set_pin_findings(checks: Iterable[rule_sets.PinCheck]) -> list[Finding]:
    """Rule-set inheritance pins against the inherited sets' major versions
    (COR-051 point 7), as `Relation.RULE_SET_PIN` findings.

    A rule set inheriting another pins that set's major version; a newer major
    fails validation until the inheriting set's owner reviews it and updates
    the pin — an error on the inheriting set, naming the new major. The pins
    come from the rule-set files the location rule finds (`rule_sets`, the
    schemas README "Rule-set files"); a pin naming no set, or one it may not
    inherit, is the `rule-sets` pass's finding, not a version relation.
    """
    findings: list[Finding] = []
    for check in checks:
        problem = check.problem
        if problem is not None:
            findings.append(
                Finding(
                    file=Path(check.rule_set.path),
                    path=check.pointer,
                    severity=Severity.ERROR,
                    message=problem,
                    relation=Relation.RULE_SET_PIN,
                )
            )
    return findings


# --- the resolver -----------------------------------------------------------


def resolve(
    declarations: Declarations,
    selections: Selections,
    backbone_version: str | None,
    *,
    definition_exists: Callable[[str, str], bool] | None = None,
    filler: Callable[[str], ProjectFiller | None] | None = None,
    config_file: Path | None = None,
) -> Wiring:
    """Compute the wiring from declarations and selections alone. Pure and deterministic.

    `definition_exists(capability, process_id)` answers whether an
    implementation-addressed upstream process has a definition (a file check by
    the caller; by default nothing beyond the offered points exists).
    `filler(address)` is the project-filler hook. `config_file` locates the
    findings whose fix is a selection entry (default: the configuration file's
    path relative to the project root).
    """
    exists = definition_exists or _no_definition
    find_filler = filler or _no_filler
    config = config_file if config_file is not None else PROJECT_CONFIG_RELPATH
    files = {i.name: i.file for i in declarations.installed}

    roles = _resolve_roles(declarations, selections)
    active_of = {r.role: r.active for r in roles}
    # An installed provider that is not the active one: its role connections are
    # inert (COR-053 point 1), its own extensions included.
    unselected = frozenset(name for r in roles for name in r.providers if name != r.active)
    active_points = {
        p.address: p for p in declarations.points if active_of.get(p.role) == p.provider
    }

    bindings = tuple(
        _bind(c, declarations, active_of, active_points, unselected, exists)
        for c in declarations.counterparts
    )
    points = tuple(
        PointBinding(
            point,
            tuple(b for b in bindings if b.point is point),
            filler=find_filler(address) if point.kind is PointKind.DATA else None,
            selected=selections.selections.get(address),
        )
        for address, point in sorted(active_points.items())
    )

    findings: list[Finding] = []
    findings.extend(_role_findings(roles, declarations, config))
    for binding in bindings:
        findings.extend(_binding_findings(binding, declarations, active_of, files))
    for point in points:
        findings.extend(_point_findings(point, files, config))
    findings.extend(_cycle_findings(bindings, declarations, active_of, files))
    findings.extend(_fingerprint_findings(declarations, files))
    range_findings, checked = _range_findings(declarations, backbone_version)
    findings.extend(range_findings)
    checked[Relation.POINT_VERSION] = _count_versioned(bindings, dependency=False)
    checked[Relation.INTERFACE_VERSION] = _count_versioned(bindings, dependency=True)
    checked[Relation.FILLER_VERSION] = sum(1 for p in points if p.filler is not None)

    return Wiring(
        backbone_version=backbone_version,
        declarations=declarations,
        roles=roles,
        points=points,
        bindings=bindings,
        findings=tuple(sorted(findings, key=_finding_key)),
        checked=checked,
    )


def _no_definition(_capability: str, _process_id: str) -> bool:
    return False


def _no_filler(_address: str) -> ProjectFiller | None:
    return None


def _resolve_roles(declarations: Declarations, selections: Selections) -> tuple[RoleBinding, ...]:
    """One binding per role anything names: provided, targeted, or selected."""
    names = sorted(
        {r for i in declarations.installed for r in _roles(i.package)}
        | {c.role for c in declarations.counterparts if c.role is not None}
        | {r for r in selections.providers if _is_qualified_role(r)}
    )
    out: list[RoleBinding] = []
    for role in names:
        providers = declarations.providers_of(role)
        selected = selections.providers.get(role)
        if selected is not None:
            # A selection naming a non-provider is the configuration pass's finding.
            active = selected if selected in providers else None
        else:
            active = providers[0] if len(providers) == 1 else None
        out.append(RoleBinding(role, providers, selected, active))
    return tuple(out)


def _bind(
    counterpart: Counterpart,
    declarations: Declarations,
    active_of: Mapping[str, str | None],
    active_points: Mapping[str, Point],
    unselected: frozenset[str],
    definition_exists: Callable[[str, str], bool],
) -> Binding:
    """Resolve one counterpart to its point and status."""
    point: Point | None
    if not counterpart.role_form:
        point, status = _bind_implementation(counterpart, declarations, definition_exists)
    elif active_of.get(counterpart.role or "") is None:
        point, status = None, BindingStatus.NO_ACTIVE_PROVIDER
    else:
        point = active_points.get(counterpart.target)
        if point is None or point.kind is not _TARGET_KIND[counterpart.kind]:
            point, status = None, BindingStatus.NO_SUCH_POINT
        else:
            status = _version_status(counterpart, point)
    if counterpart.capability in unselected:
        status = BindingStatus.INERT_PROVIDER
    return Binding(counterpart, point, status)


def _bind_implementation(
    counterpart: Counterpart,
    declarations: Declarations,
    definition_exists: Callable[[str, str], bool],
) -> tuple[Point | None, BindingStatus]:
    """`<capability>:<process-id>`, the implementation form a `depends-on` entry may
    use (COR-038): an offered point with that process id carries the interface
    version; failing that, the definition file's existence is the whole answer."""
    capability, _, process_id = counterpart.target.partition(POINT_SEPARATOR)
    if declarations.by_name(capability) is None:
        return None, BindingStatus.NOT_INSTALLED
    offered = next(
        (
            p
            for p in declarations.points
            if p.provider == capability
            and p.kind is PointKind.PROCESS
            and p.process_id == process_id
        ),
        None,
    )
    if offered is not None:
        return offered, _version_status(counterpart, offered)
    if definition_exists(capability, process_id):
        return None, BindingStatus.BOUND
    return None, BindingStatus.NO_SUCH_POINT


def _version_status(counterpart: Counterpart, point: Point) -> BindingStatus:
    """Compatible when the integers are equal; a `depends-on` entry may declare none."""
    if counterpart.version is None or counterpart.version == point.version:
        return BindingStatus.BOUND
    return BindingStatus.INERT_VERSION


def _count_versioned(bindings: Iterable[Binding], *, dependency: bool) -> int:
    """How many counterparts had a version compared with their point's."""
    return sum(
        1
        for b in bindings
        if (b.counterpart.kind is CounterpartKind.DEPENDENCY) == dependency
        and b.point is not None
        and b.counterpart.version is not None
        and b.status in (BindingStatus.BOUND, BindingStatus.INERT_VERSION)
    )


# --- findings: the connections ------------------------------------------------


def _role_findings(
    roles: Iterable[RoleBinding], declarations: Declarations, config_file: Path
) -> list[Finding]:
    """A role conflict is an error on the configuration; an unselected provider is warned."""
    findings: list[Finding] = []
    for role in roles:
        if role.conflict:
            commands = " or ".join(
                f"`{provider_set_command(role.role, name)}`" for name in role.providers
            )
            findings.append(
                Finding(
                    config_file,
                    f"/{CONNECTIONS_KEY}/{PROVIDERS_KEY}",
                    Severity.ERROR,
                    f"role {role.role!r} is provided by {_list(role.providers)} and no "
                    f"provider is selected; select one with {commands}, which writes the "
                    f"`{CONNECTIONS_KEY}.{PROVIDERS_KEY}` entry `{role.role}: <one of them>` "
                    f"(COR-053 point 1).",
                )
            )
            continue
        if role.active is None:
            continue  # no provider, or a selection naming a non-provider (the configuration pass's)
        for name in role.providers:
            if name == role.active:
                continue
            component = declarations.by_name(name)
            if component is None:
                continue
            findings.append(
                Finding(
                    component.file,
                    _roles_pointer(component, role.role),
                    Severity.WARNING,
                    f"{name!r} provides role {role.role!r}, but {role.active!r} is the selected "
                    f"provider: the points {name!r} declares under it are not defined in this "
                    f"project and its own extensions are inert; its commands still run "
                    f"(COR-053 point 1).",
                )
            )
    return findings


def _binding_findings(
    binding: Binding,
    declarations: Declarations,
    active_of: Mapping[str, str | None],
    files: Mapping[str, Path],
) -> list[Finding]:
    """What one counterpart's status means.

    Optional (the default): an incompatible version or a missing point is a
    warning, a role nobody provides or an absent upstream capability is silent.
    Mandatory: any of them is an error on the side carrying the mark, and the
    capability it targets, when there is one, is warned (COR-053 point 6).
    """
    c = binding.counterpart
    status = binding.status
    if status in (BindingStatus.BOUND, BindingStatus.INERT_PROVIDER):
        return []
    what = f"{c.kind.value} entry for {c.target!r}"
    target: tuple[str, str] | None = None  # (capability, pointer) warned on an unmet mark
    relation: Relation | None = None
    record = "COR-053 point 2"  # the addressing rule an optional miss is reported under
    if status is BindingStatus.INERT_VERSION and binding.point is not None:
        point = binding.point
        problem = (
            f"targets version {c.version}, but {point.provider!r} defines the point at "
            f"version {point.version}"
        )
        fix = f"target version {point.version} once its contract is met"
        target = (point.provider, point.pointer)
        relation = (
            Relation.INTERFACE_VERSION
            if c.kind is CounterpartKind.DEPENDENCY
            else Relation.POINT_VERSION
        )
    elif status is BindingStatus.NO_SUCH_POINT and c.role_form:
        role = c.role or ""
        provider = active_of.get(role) or ""
        wanted = _TARGET_KIND[c.kind]
        known = sorted(
            p.address
            for p in declarations.points
            if p.provider == provider and p.role == role and p.kind is wanted
        )
        problem = f"names no {wanted.value} point of role {role!r}, whose active provider is " + (
            f"{provider!r} (it defines: {_list(known)})" if known else f"{provider!r}"
        )
        fix = "correct the address, or drop the entry"
        component = declarations.by_name(provider)
        if component is not None:
            target = (provider, _roles_pointer(component, role))
    elif status is BindingStatus.NO_SUCH_POINT:
        capability, _, process_id = c.target.partition(POINT_SEPARATOR)
        problem = (
            f"names process {process_id!r}, which {capability!r} neither offers nor defines at "
            f"{SCHEMAS_DIR}/{process_id}.yaml"
        )
        record = "COR-038"
        fix = (
            "correct the upstream in the process definition's `depends_on` and regenerate the list"
        )
        target = (capability, "")
    elif c.mandatory is None:
        return []  # optional, and nothing installed to connect to: silent
    elif status is BindingStatus.NO_ACTIVE_PROVIDER:
        role = c.role or ""
        if declarations.providers_of(role):
            return []  # the role conflict, or the selection naming a non-provider, is the finding
        problem = f"has no provider: no installed capability provides role {role!r}"
        fix = "install a capability that provides the role"
    elif status is BindingStatus.NOT_INSTALLED:
        capability = c.target.partition(POINT_SEPARATOR)[0]
        problem = f"names upstream capability {capability!r}, which is not installed"
        fix = f"install it (`pkit capabilities install {capability}`)"
    else:
        return []

    file = files[c.capability]
    if c.mandatory is None:
        tail = (
            "the connection is inert until the versions agree (COR-053 point 5)"
            if relation is not None
            else f"{fix} ({record})"
        )
        return [Finding(file, c.pointer, Severity.WARNING, f"{what} {problem}; {tail}.", relation)]
    findings = [
        Finding(
            file,
            c.pointer,
            Severity.ERROR,
            f"mandatory {what} {problem}: the mark is unmet (reason: {c.mandatory}) — {fix}, "
            f"or drop the mark (COR-053 point 6).",
        )
    ]
    if target is not None and target[0] in files and target[0] != c.capability:
        name, pointer = target
        findings.append(
            Finding(
                files[name],
                pointer,
                Severity.WARNING,
                f"{c.capability!r} carries a mandatory {what} that {name!r} does not meet "
                f"({problem}); the error sits with {c.capability!r} (COR-053 point 6).",
            )
        )
    return findings


def _point_findings(
    point: PointBinding,
    files: Mapping[str, Path],
    config_file: Path,
) -> list[Finding]:
    """A data point's own findings: a project filler at another version; a mandatory
    point filled only by its default; a `single` point with several contributors
    and no selection."""
    p = point.point
    if p.kind is not PointKind.DATA:
        return []
    findings: list[Finding] = []
    if point.filler is not None and point.filler.version != p.version:
        findings.append(
            Finding(
                point.filler.file,
                "/schema_version",
                Severity.ERROR,
                f"the project filler for {p.address!r} targets version {point.filler.version}, "
                f"but {p.provider!r} defines the point at version {p.version}; update the "
                f"filler to the point's contract and its `schema_version` (COR-052 point 2).",
                Relation.FILLER_VERSION,
            )
        )
    if p.mandatory is not None and not point.filled:
        contributors = point.contributors
        undelivered = (
            f" (declared but not delivered: {_list(contributors)})" if contributors else ""
        )
        findings.append(
            Finding(
                files[p.provider],
                f"{p.pointer}/mandatory",
                Severity.ERROR,
                f"mandatory point {p.address!r} is filled only by its default{undelivered}: the "
                f"mark is unmet (reason: {p.mandatory}) — have a capability contribute to it at "
                f"version {p.version} or a project filler answer it, or drop the mark "
                f"(COR-053 point 6).",
            )
        )
    bound = sorted({b.counterpart.capability for b in point.bound})
    if p.policy == SINGLE and len(bound) > 1 and point.selected is None:
        findings.append(
            Finding(
                config_file,
                f"/{CONNECTIONS_KEY}/{SELECTIONS_KEY}",
                Severity.ERROR,
                f"point {p.address!r} is `single` and {_list(bound)} contribute to it; select "
                f"one with the `{CONNECTIONS_KEY}.{SELECTIONS_KEY}` entry `{p.address}: <one of "
                f"them>`{_config_set_hint(SELECTIONS_KEY, p.address)} (COR-052 point 4).",
            )
        )
    return findings


def _cycle_findings(
    bindings: Iterable[Binding],
    declarations: Declarations,
    active_of: Mapping[str, str | None],
    files: Mapping[str, Path],
) -> list[Finding]:
    """Mandatory marks facing each other (COR-053 point 6).

    An edge runs from the capability carrying a mandatory counterpart to the one
    capability its target needs installed first — the active provider of the
    target role, or the implementation-addressed capability. A role without an
    active provider draws no edge: its conflict is its own finding, and which
    provider is selected decides whether a cycle exists. Every strongly connected
    group of more than one capability is a cycle no install order can satisfy;
    each mark inside it is an error.
    """
    edges: dict[str, set[str]] = {}
    marks: dict[tuple[str, str], list[Counterpart]] = {}
    for binding in bindings:
        c = binding.counterpart
        if c.mandatory is None or binding.status is BindingStatus.INERT_PROVIDER:
            continue  # an unselected provider's marks bind nothing (COR-053 point 1)
        if c.role_form:
            needed = active_of.get(c.role or "")
        else:
            needed = c.target.partition(POINT_SEPARATOR)[0]
        if needed is None or needed == c.capability or declarations.by_name(needed) is None:
            continue
        edges.setdefault(c.capability, set()).add(needed)
        marks.setdefault((c.capability, needed), []).append(c)
    findings: list[Finding] = []
    for component in _strongly_connected(edges):
        if len(component) < 2:
            continue
        inside = sorted(pair for pair in marks if pair[0] in component and pair[1] in component)
        description = "; ".join(
            f"{a} → {b} ({', '.join(f'{c.kind.value} {c.target!r}' for c in marks[(a, b)])})"
            for a, b in inside
        )
        for a, b in inside:
            for c in marks[(a, b)]:
                findings.append(
                    Finding(
                        files[a],
                        c.pointer,
                        Severity.ERROR,
                        f"mandatory cycle among {_list(sorted(component))}: {description}; no "
                        f"member could be installed first — drop one mark (COR-053 point 6).",
                    )
                )
    return findings


def _strongly_connected(edges: Mapping[str, set[str]]) -> list[frozenset[str]]:
    """Tarjan's algorithm over a small graph; components in a fixed order."""
    nodes = sorted(set(edges) | {t for ts in edges.values() for t in ts})
    index: dict[str, int] = {}
    low: dict[str, int] = {}
    on_stack: set[str] = set()
    stack: list[str] = []
    components: list[frozenset[str]] = []

    def visit(node: str) -> None:
        index[node] = low[node] = len(index)
        stack.append(node)
        on_stack.add(node)
        for succ in sorted(edges.get(node, ())):
            if succ not in index:
                visit(succ)
                low[node] = min(low[node], low[succ])
            elif succ in on_stack:
                low[node] = min(low[node], index[succ])
        if low[node] == index[node]:
            component: set[str] = set()
            while True:
                member = stack.pop()
                on_stack.discard(member)
                component.add(member)
                if member == node:
                    break
            components.append(frozenset(component))

    for node in nodes:
        if node not in index:
            visit(node)
    return sorted(components, key=sorted)


def _fingerprint_findings(declarations: Declarations, files: Mapping[str, Path]) -> list[Finding]:
    """Two installed providers of one qualified point and version must define the
    same companion-schema shape (COR-053 point 5); compared here, kept nowhere."""
    groups: dict[tuple[str, int], list[Point]] = {}
    for point in declarations.points:
        if point.fingerprint is not None:
            groups.setdefault((point.address, point.version), []).append(point)
    findings: list[Finding] = []
    for (address, version), points in sorted(groups.items()):
        if len({p.fingerprint for p in points}) < 2:
            continue
        for point in sorted(points, key=lambda p: p.provider):
            others = _list(sorted(p.provider for p in points if p.provider != point.provider))
            findings.append(
                Finding(
                    files[point.provider],
                    f"{point.pointer}/schema",
                    Severity.ERROR,
                    f"{point.provider!r} and {others} define {address!r} at version {version} "
                    f"with different companion schemas; providers of one qualified point and "
                    f"version must agree — raise the version on the side that changed, or align "
                    f"the schemas (COR-053 point 5).",
                )
            )
    return findings


# --- findings: the version ranges -------------------------------------------------


def range_admits(version_range: Any, version: Any) -> bool | None:
    """Whether a version range admits a version — the one comparison of a version
    range relation, for every reader: a component's `requires_backbone` against a
    backbone (COR-010, COR-017), a `requires_capabilities` range against a
    capability (COR-030). Validation reads it here; so do the install, register
    and upgrade gates.

    `None` when either side cannot be read — a range that is not a non-empty
    PEP 440 specifier set, a version that is not a PEP 440 version — which every
    reader takes as no constraint: the packages pass reports a malformed range.
    """
    spec = _specifier(version_range)
    actual = _version(version) if isinstance(version, str) else None
    if spec is None or actual is None:
        return None
    return actual in spec


def _range_findings(
    declarations: Declarations, backbone_version: str | None
) -> tuple[list[Finding], dict[Relation, int]]:
    """`requires_backbone` against the installed backbone; `requires_capabilities`
    ranges against installed versions (COR-030): the dependent carries the error,
    the dependency is warned with each dependent named. With how many were checked."""
    findings: list[Finding] = []
    checked = {Relation.BACKBONE_RANGE: 0, Relation.CAPABILITY_RANGE: 0}
    capabilities = {i.name: i for i in declarations.installed if i.kind == CAPABILITY}
    out_of_range: dict[str, list[str]] = {}
    for component in declarations.installed:
        package = component.package
        required = package.get(REQUIRES_BACKBONE_KEY)
        admitted = range_admits(required, backbone_version)
        if admitted is not None:
            checked[Relation.BACKBONE_RANGE] += 1
            if not admitted:
                findings.append(
                    Finding(
                        component.file,
                        f"/{REQUIRES_BACKBONE_KEY}",
                        Severity.ERROR,
                        f"{component.name!r} requires backbone {required} but {backbone_version} "
                        f"is installed; upgrade {component.name!r} to a version whose range "
                        f"admits this backbone, or move the backbone into the range "
                        f"(COR-010, COR-017).",
                        Relation.BACKBONE_RANGE,
                    )
                )
        for index, raw_dependency in enumerate(_entries(package.get("requires_capabilities"))):
            dependency = _mapping(raw_dependency)
            if dependency is None:
                continue
            name = dependency.get("name")
            dependency_range = dependency.get("version")
            if not isinstance(name, str) or not name or _specifier(dependency_range) is None:
                continue  # the packages pass reports the malformed entry
            checked[Relation.CAPABILITY_RANGE] += 1
            pointer = f"/requires_capabilities/{index}"
            target = capabilities.get(name)
            if target is None:
                findings.append(
                    Finding(
                        component.file,
                        pointer,
                        Severity.ERROR,
                        f"{component.name!r} requires capability {name!r} {dependency_range}, "
                        f"which is not installed; install it (`pkit capabilities install "
                        f"{name}`) (COR-030).",
                        Relation.CAPABILITY_RANGE,
                    )
                )
                continue
            if range_admits(dependency_range, target.version) is not False:
                continue  # an unreadable version is not refused, as the dependency gate reads it
            findings.append(
                Finding(
                    component.file,
                    pointer,
                    Severity.ERROR,
                    f"{component.name!r} requires capability {name!r} {dependency_range} but "
                    f"{target.version} is installed; upgrade {component.name!r} to a version "
                    f"whose range admits it, or move {name!r} into the range (COR-030).",
                    Relation.CAPABILITY_RANGE,
                )
            )
            out_of_range.setdefault(name, []).append(f"{component.name} ({dependency_range})")
    for name, dependents in sorted(out_of_range.items()):
        target = capabilities[name]
        findings.append(
            Finding(
                target.file,
                "/component/version",
                Severity.WARNING,
                f"{name!r} at {target.version} is outside the range declared by "
                f"{_list(sorted(dependents))}; the error is theirs (COR-030).",
                Relation.CAPABILITY_RANGE,
            )
        )
    return findings, checked


# --- parsing the package metadata --------------------------------------------


def _connections_block(package: Mapping[str, Any]) -> Mapping[str, Any]:
    return _mapping(package.get(CONNECTIONS_KEY)) or {}


def _roles(package: Mapping[str, Any]) -> tuple[str, ...]:
    return tuple(
        r for r in _entries(_connections_block(package).get("roles")) if isinstance(r, str)
    )


def _roles_pointer(component: Installed, role: str) -> str:
    """Where `component` declares that it provides `role`."""
    roles = _entries(_connections_block(component.package).get("roles"))
    if role in roles:
        return f"/{CONNECTIONS_KEY}/roles/{roles.index(role)}"
    return f"/{CONNECTIONS_KEY}/roles"


def _points_of(component: Installed) -> list[Point]:
    """Every point the component declares under `extension-points`, active or not."""
    extension_points = _mapping(_connections_block(component.package).get("extension-points"))
    if extension_points is None:
        return []
    roles = set(_roles(component.package))
    points: list[Point] = []
    for group in ("accepts", "offers"):
        declared = _mapping(extension_points.get(group))
        if declared is None:
            continue
        for address, value in declared.items():
            raw = _mapping(value)
            if raw is None:
                continue
            role = role_of(address)
            version = _point_version(raw.get("schema_version"))
            if role is None or role not in roles or version is None:
                continue  # the packages pass reports the shape
            if group == "accepts":
                kind = PointKind.DATA
            elif raw.get("kind") == PointKind.EVENT.value:
                kind = PointKind.EVENT
            elif raw.get("kind") == PointKind.PROCESS.value:
                kind = PointKind.PROCESS
            else:
                continue
            schema = _optional_str(raw, "schema")
            points.append(
                Point(
                    address=address,
                    role=role,
                    kind=kind,
                    version=version,
                    provider=component.name,
                    pointer=f"/{CONNECTIONS_KEY}/extension-points/{group}/{_token(address)}",
                    combination=_optional_str(raw, "combination"),
                    mandatory=_mandatory_reason(raw),
                    schema=schema,
                    process_id=_optional_str(raw, "process"),
                    fingerprint=_fingerprint(component.component_dir, schema),
                    description=_optional_str(raw, "description"),
                )
            )
    return points


def _counterparts_of(component: Installed) -> list[Counterpart]:
    """Every contribution, subscription and generated `depends-on` entry."""
    extensions = _mapping(_connections_block(component.package).get("extensions"))
    if extensions is None:
        return []
    out: list[Counterpart] = []
    for kind in CounterpartKind:
        raw = extensions.get(kind.value)
        if kind is CounterpartKind.DEPENDENCY:
            entries = _entries((_mapping(raw) or {}).get("entries"))
            base = f"/{CONNECTIONS_KEY}/extensions/{kind.value}/entries"
            key = "process"
        else:
            entries = _entries(raw)
            base = f"/{CONNECTIONS_KEY}/extensions/{kind.value}"
            key = "point"
        for index, value in enumerate(entries):
            entry = _mapping(value)
            if entry is None:
                continue
            target = entry.get(key)
            if not isinstance(target, str) or not target:
                continue
            if ROLE_QUALIFIER in target and role_of(target) is None:
                continue  # not a point address: the packages pass reports the shape
            version = _point_version(entry.get("schema_version"))
            if kind is not CounterpartKind.DEPENDENCY and (
                version is None or ROLE_QUALIFIER not in target
            ):
                continue  # a contribution or subscription is role-addressed and versioned
            if kind is CounterpartKind.DEPENDENCY and "schema_version" in entry and version is None:
                continue  # a malformed version: the packages pass reports it
            out.append(
                Counterpart(
                    capability=component.name,
                    kind=kind,
                    target=target,
                    version=version,
                    pointer=f"{base}/{index}",
                    mandatory=_mandatory_reason(entry),
                    command=_optional_str(entry, "command"),
                    description=_optional_str(entry, "description"),
                )
            )
    return out


def _point_version(value: Any) -> int | None:
    """A point version: an integer, never a boolean (the schema's `integer`)."""
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _mandatory_reason(raw: Mapping[str, Any]) -> str | None:
    """The mark's reason; a mark without one is the packages pass's error, not a mark."""
    mark = _mapping(raw.get("mandatory"))
    return _optional_str(mark, "reason") if mark is not None else None


def _fingerprint(component_dir: Path, schema: str | None) -> str | None:
    """sha256 of the companion schema's canonical JSON (keys sorted, no whitespace),
    so key order and layout never count and every other difference does; None when
    there is no readable schema (its existence is the packages pass's check)."""
    if schema is None or relative_path_problem(schema) is not None:
        return None
    try:
        document = json.loads((component_dir / SCHEMAS_DIR / schema).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    canonical = json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _definition_file_exists(declarations: Declarations, capability: str, process_id: str) -> bool:
    """Does `<capability>:<process-id>` have a definition file by convention? Existence only."""
    component = declarations.by_name(capability)
    if component is None or PurePosixPath(process_id).name != process_id:
        return False  # not installed, or not a plain file name
    return (component.component_dir / SCHEMAS_DIR / f"{process_id}.yaml").is_file()


def _version_of_record(
    target_root: Path, manifest: str | None, package: Mapping[str, Any]
) -> str | None:
    """The installed version: the component manifest's, else the authored package's —
    an incubated capability has no kit-written manifest (COR-031) — in the order the
    dependency gate reads it (`capabilities.get_installed_capability_version`)."""
    if manifest is not None:
        try:
            component = read_component_manifest(target_root / manifest)
        except Exception:
            component = None  # `pkit validate`'s manifest checks report it
        if component is not None and component.version:
            return component.version
    block = _mapping(package.get("component"))
    return _optional_str(block, "version") if block is not None else None


# --- `pkit validate` ------------------------------------------------------------


UMBRELLA_SEVERITY = {
    Severity.ERROR: validators.Severity.ERROR,
    Severity.WARNING: validators.Severity.WARNING,
}


def connections_outcome(target_root: Path) -> validators.Outcome:
    """The `connections` member of `pkit validate`: the wiring as resolved — roles,
    points, counterparts — then the connection findings (roles, points, marks,
    cycles, fingerprints), each at its own severity; then how each data point
    resolved, what each command filler that reads beyond the working tree read
    and at which commit (COR-052 point 7), and the findings of its fillers
    (`data_points`, the second layer over the same wiring)."""
    from project_kit import data_points  # the second layer imports this module

    wiring = shared_wiring(target_root)
    findings = wiring.connection_findings()
    data = data_points.shared_resolution(target_root)
    return validators.Outcome(
        (*_connections_summary(wiring, findings), *data_points.summary_lines(data)),
        (*_as_findings(target_root, findings), *data.findings),
    )


def versions_outcome(target_root: Path) -> validators.Outcome:
    """The `versions` member of `pkit validate`: how many of each relation were
    checked, then each version finding labelled with its relation."""
    wiring = shared_wiring(target_root)
    findings = wiring.version_findings()
    checked = ", ".join(f"{n} {relation.value}(s)" for relation, n in wiring.checked.items())
    return validators.Outcome(
        (f"checked: {checked}; {_counts(findings)}.",),
        _as_findings(target_root, findings, labelled=True),
    )


def _connections_summary(wiring: Wiring, findings: tuple[Finding, ...]) -> list[str]:
    if not wiring.roles and not wiring.bindings:
        return ["no connection points declared by installed components."]
    declaring = sum(
        1
        for i in wiring.declarations.installed
        if isinstance(i.package.get(CONNECTIONS_KEY), Mapping)
    )
    bound = sum(1 for b in wiring.bindings if b.status is BindingStatus.BOUND)
    lines = [
        f"{declaring} component(s) declare connections; {len(wiring.roles)} role(s), "
        f"{len(wiring.active_roles())} active; {len(wiring.points)} point(s); "
        f"{len(wiring.bindings)} counterpart(s), {bound} bound; "
        f"{_counts(findings)}."
    ]
    for role in wiring.roles:
        lines.append(f"{role.role} → {_role_state(role)}")
    for point in wiring.points:
        lines.append(f"  {_point_line(point)}")
    shown = {id(b) for p in wiring.points for b in p.bindings}
    for binding in wiring.bindings:
        if id(binding) not in shown:
            c = binding.counterpart
            lines.append(f"  {c.capability} {c.kind.value} {c.target!r}: {binding.status.value}")
    return lines


def _as_findings(
    target_root: Path, findings: Iterable[Finding], *, labelled: bool = False
) -> tuple[validators.Finding, ...]:
    return tuple(
        validators.Finding(
            _locate(target_root, f),
            f.message,
            UMBRELLA_SEVERITY[f.severity],
            label=f.relation.value if labelled and f.relation else "",
        )
        for f in findings
    )


def _role_state(role: RoleBinding) -> str:
    if role.active is not None:
        return role.active if role.selected is None else f"{role.active} (selected)"
    if role.conflict:
        return f"CONFLICT: {', '.join(role.providers)} (no selection)"
    if role.selected is not None:
        return f"selection {role.selected!r} is not a provider"
    return "no provider installed"


def _point_line(point: PointBinding) -> str:
    p = point.point
    parts = [
        f"{b.counterpart.capability} ({b.counterpart.kind.value}, {b.status.value})"
        for b in point.bindings
    ]
    if p.kind is PointKind.DATA:
        if point.filler is not None:
            parts.append(f"project filler (v{point.filler.version})")
        if not parts:
            parts.append("unfilled")
    mark = " [mandatory]" if p.mandatory else ""
    tail = "; ".join(parts) if parts else "no counterpart"
    return f"{p.address} ({p.kind.value} v{p.version}, {p.provider}){mark} ← {tail}"


def _counts(findings: Iterable[Finding]) -> str:
    severities = [f.severity for f in findings]
    errors = severities.count(Severity.ERROR)
    return f"{errors} error(s), {len(severities) - errors} warning(s)"


def _locate(target_root: Path, finding: Finding) -> str:
    file = finding.file
    if file.is_absolute() and file.is_relative_to(target_root):
        file = file.relative_to(target_root)
    return f"{file.as_posix()}:{finding.path}" if finding.path else file.as_posix()


# --- helpers ----------------------------------------------------------------------


def _is_qualified_role(name: str) -> bool:
    """`<publisher>::<role>`, each side non-empty and free of `:`."""
    publisher, sep, role = name.partition(ROLE_QUALIFIER)
    return bool(sep and publisher and role) and POINT_SEPARATOR not in publisher + role


def provider_set_command(role: str, capability: str) -> str:
    """The exact command that selects `capability` as the provider of the qualified
    `role` — the fix a role conflict names, in `pkit validate` and `pkit status`."""
    return f"{PROVIDERS_SET_COMMAND} {shlex.quote(role)} {shlex.quote(capability)}"


def _config_set_hint(key: str, entry: str) -> str:
    """The `pkit config set` form of a selection entry, when its dotted key is unambiguous."""
    if "." in entry:
        return ""
    return f" (`pkit config set {CONNECTIONS_KEY}.{key}.{entry} <capability>`)"


def _version(value: str | None) -> Version | None:
    if not value:
        return None
    try:
        return Version(value)
    except InvalidVersion:
        return None


def _specifier(value: Any) -> SpecifierSet | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return SpecifierSet(value)
    except InvalidSpecifier:
        return None  # the packages pass reports the malformed range


def _mapping(value: Any) -> Mapping[str, Any] | None:
    """`value` as a mapping, or None. Package data has string keys (`_string_keys`)."""
    return cast("Mapping[str, Any]", value) if isinstance(value, Mapping) else None


def _entries(value: Any) -> list[Any]:
    """`value` as a list, or an empty one."""
    return cast("list[Any]", value) if isinstance(value, list) else []


def _optional_str(raw: Mapping[str, Any], key: str) -> str | None:
    value = raw.get(key)
    return value if isinstance(value, str) and value else None


def _string_keys(obj: Any) -> Any:
    """YAML may read a key as a number or a date; every key here is its text."""
    if isinstance(obj, Mapping):
        items = cast("Mapping[Any, Any]", obj).items()
        return {str(k): _string_keys(v) for k, v in items}
    if isinstance(obj, list):
        return [_string_keys(x) for x in cast("list[Any]", obj)]
    return obj


def _string_map(raw: Any) -> dict[str, str]:
    block = _mapping(raw)
    if block is None:
        return {}
    return {str(k): v for k, v in block.items() if isinstance(v, str) and v}


def _relation_rank(finding: Finding) -> int:
    return _RELATION_ORDER[finding.relation] if finding.relation is not None else -1


def _list(names: Iterable[str]) -> str:
    return ", ".join(repr(n) for n in names)


def _token(segment: Any) -> str:
    """One JSON Pointer reference token (RFC 6901 escaping)."""
    return str(segment).replace("~", "~0").replace("/", "~1")


def _finding_key(finding: Finding) -> tuple[str, str, str, str]:
    return (finding.file.as_posix(), finding.path, finding.severity.value, finding.message)
