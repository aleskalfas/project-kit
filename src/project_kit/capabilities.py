"""Capability install / uninstall / list operations (per COR-017).

A capability is a self-contained opt-in unit of methodology that lives
at `.pkit/capabilities/<name>/`. Adopters install per project via
`pkit capabilities install <name>`; uninstall via
`pkit capabilities uninstall <name>`. Capabilities slot into the kit's existing component
registry (per COR-010) alongside adapters.

This module covers the deterministic mechanics, and the one prompt both a
capability's install and a version transition ask on a naming collision
(override / skip / inspect, ``resolve_collision_interactive``, COR-017).

Capability dependencies (COR-030): a capability may declare
``requires_capabilities`` in its ``package.yaml`` — an optional list of
``{name, version}`` entries, each expressing a semver range that a
dependency capability's installed version must satisfy. An entry marked
``optional: true`` need not be installed, but an installed one must satisfy
its range. The install pre-flight, both upgrade entry points, and the
uninstall gate enforce this contract; an optional dependency never blocks
uninstalling the capability it names. See ``check_capability_dependencies``
and ``find_declared_dependents``.

Mandatory process connections (COR-053 point 6): an entry of a capability's
generated ``depends-on`` list may carry a mandatory mark — its upstream process
definition must exist, at a compatible interface version when the entry names
one. The lifecycle is that mark's one reader, with COR-030's direction split:
install, register and the single-capability upgrade refuse the capability
carrying an unmet mark (``unmet_mandatory_upstreams``); upgrading or
uninstalling the capability it targets warns, naming each counterpart, and
proceeds only under ``--force`` (``mandatory_counterparts_left_unmet``). Both
judge through the wiring resolver, never by reading process definitions.
"""

from __future__ import annotations

import datetime as _dt
import re
import shutil
import subprocess
from collections.abc import Collection, Iterable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path, PurePath
from typing import TYPE_CHECKING, Any, cast

import click
from packaging.version import InvalidVersion, Version
from ruamel.yaml import YAML

from project_kit import treecopy
from project_kit.changesets import BACKBONE
from project_kit.manifest import (
    ORIGIN_INCUBATED_IN_REPO,
    ORIGIN_KIT_SHIPPED,
    ComponentKind,
    ComponentManifest,
    ComponentRegistryEntry,
    capability_manifest_path,
    capability_manifest_rel,
    capability_root_manifest_path,
    read_backbone_manifest,
    read_capability_origin,
    read_component_manifest,
    recorded_capability_manifest,
    set_component_manifest_path,
    write_backbone_manifest,
    write_component_manifest,
)
from project_kit.manifest import set_capability_origin as _manifest_set_capability_origin
from project_kit.migrations import (
    execute_migration_scripts,
    pending_migration_scripts,
    report_pending_migrations,
)
from project_kit.schemas_validate import CORE_SCHEMAS_OWNER

if TYPE_CHECKING:
    # The wiring resolver imports this module (through rule sets); its types are
    # read here for annotations only, and the module itself inside the gates.
    from project_kit.connections import Binding, Installed, Wiring


_NAME_RE = re.compile(r"^[a-z][a-z0-9-]*[a-z0-9]$|^[a-z]$")
_yaml = YAML(typ="safe")

# Names a capability may not take because another subsystem already gives
# them a meaning, each mapped to the reason shown in the refusal. `core` is
# the name core's own entries carry where a capability's carry the
# capability's: the namespace `pkit new decision`, `pkit new agent` and
# `pkit new storyboard` read as core's before any capability name
# (`decisions`, `agents`), and the schemas-home owner name for the core
# schemas area (`schemas_validate.schemas_home`), so a capability named `core`
# could have no decision records or agents stamped and would have its
# `schemas/` silently unreachable (#919, #1289). `project` is the name the
# project's own entries carry where a capability's carry the capability's:
# the namespace `pkit new decision`, `pkit new agent` and `pkit new storyboard`
# read as the project's before any capability name (`decisions`, `agents`),
# and the opening name of the project's checks in the evidence points
# (software-analysis and living-docs DEC-001 point 7), so a capability named
# `project` would be indistinguishable from the project itself (#1269). `adr`
# is the namespace of the project's architecture decision records, which
# `pkit new decision` reads before any capability name (`decisions`), so a
# capability named `adr` could have no decision records stamped (#1289).
# `backbone` is the name the backbone carries where a component's carry the
# component's: the component of its changesets (`changesets.BACKBONE`, the
# constant read here), the owner of its validators (`validators.BACKBONE_OWNER`,
# beside `<capability>:<name>`), the component its rule sets are cited with
# (`friction_discovery.BACKBONE_COMPONENT`) and the component its documentation
# locations are recorded under (`docs_roots.BACKBONE`), so a capability named
# `backbone` would have its changesets, validators, rule sets and documentation
# locations read as the backbone's (#1292).
RESERVED_CAPABILITY_NAMES: dict[str, str] = {
    CORE_SCHEMAS_OWNER: (
        "it is the name core's own entries carry where a capability's carry the "
        "capability's name: the namespace of the core decision records and agents, "
        "and the core schemas area wherever a schemas verb takes an owner, so a "
        "capability named `core` could have no decision records or agents of its own "
        "stamped, and its schemas would be unreachable"
    ),
    "project": (
        "it is the name the project's own entries carry where a capability's carry "
        "the capability's name: the namespace of the project's decision records and "
        "agents, and the opening name of the project's checks in an evidence point, "
        "so a capability named `project` would be indistinguishable from the project "
        "itself"
    ),
    "adr": (
        "it is the namespace of the project's architecture decision records, which "
        "`pkit new decision` reads before any capability name, so a capability named "
        "`adr` could have no decision records of its own stamped"
    ),
    BACKBONE: (
        "it is the name the backbone carries where a component's carry the component's "
        "name: the component of the backbone's changesets, the owner of its validators, "
        "the component its rule sets are cited with, and the component its documentation "
        "locations are recorded under, so a capability named `backbone` would have its "
        "changesets, validators, rule sets and documentation locations read as the "
        "backbone's"
    ),
}

# Why an adapter and a capability may not share a name, shown in each refusal and
# finding: the backbone reads a component by its name alone in places that read
# both kinds. A changeset names its component (`changesets.Changeset.component`)
# and the release keys every `package.yaml` under `.pkit/` by name
# (`changesets.discover_components`, `release.compute_release`), so one of the two
# would be moved and the other never; every registered component's validators
# are owned by its name (`validators.capability_validators`), so the two would
# share one owner; and the wiring resolver reads the component registry by name
# (`connections._installed_components`), so one of the two would be read under
# the other's kind.
SHARED_NAME_REASON = (
    "an adapter and a capability cannot share a name, because the backbone reads a "
    "component by its name alone where it reads both kinds: a changeset names its "
    "component by name and the release keys every `package.yaml` under `.pkit/` by name, "
    "so a release would move only one of the two; every registered component's "
    "validators are owned by its name, so the two would share one owner; and the wiring "
    "resolver reads the component registry by name, so one of the two would be read "
    "under the other's kind"
)

# Where a component of each kind lives in a project tree, relative to `.pkit/`.
_COMPONENT_AREAS: dict[ComponentKind, str] = {"adapter": "adapters", "capability": "capabilities"}

# A capability's top-level `project/` subtree is adopter-owned (the
# no-shared-files invariant, COR-001): never overwritten or removed on
# refresh, and never seeded from the source either — the source's own
# `project/` tree is that project's instance data, not a template (#812).
# See `_copy_capability_tree`.
_CAPABILITY_PROJECT_SUBTREE = "project"


# The key that marks a `requires_capabilities` entry optional (COR-030).
OPTIONAL_DEPENDENCY_KEY = "optional"


def is_optional_dependency(entry: Mapping[str, Any]) -> bool:
    """Whether a raw `requires_capabilities` entry is an optional dependency (COR-030).

    Only `optional: true` marks one; any other value, or none, reads as a
    required dependency, the stricter reading. The lifecycle gates and
    validation read the mark through this one predicate.
    """
    return entry.get(OPTIONAL_DEPENDENCY_KEY) is True


@dataclass(frozen=True)
class CapabilityDependency:
    """One entry from the ``requires_capabilities`` list in a ``package.yaml``."""

    name: str  # capability name (e.g. "evidence")
    version: str  # semver range string (e.g. ">=0.2.0,<1.0.0")
    optional: bool = False  # `optional: true` — need not be installed (COR-030)


@dataclass(frozen=True)
class CapabilityPackage:
    """A capability's package.yaml content, as read from disk."""

    name: str
    version: str
    description: str
    requires_backbone: str
    requires_capabilities: tuple[CapabilityDependency, ...] = field(default_factory=tuple)
    schema_version: int = 1


@dataclass(frozen=True)
class CapabilitySource:
    """Resolved location of a capability, in either the kit source tree or the adopter's repo.

    Both resolvers (``find_capability_in_source`` for the kit source and
    ``find_capability_in_repo`` for the adopter's own repo, per COR-031)
    return this same type, so downstream register / deploy / stamp consume a
    capability uniformly regardless of where it was found.
    """

    name: str
    # capability dir: <kit-source>/capabilities/<name>/ (kit source) or
    # <target-root>/.pkit/capabilities/<name>/ (adopter's repo)
    path: Path
    package: CapabilityPackage


def _resolve_capability_dir(cap_dir: Path, name: str) -> CapabilitySource | None:
    """Validate and read a candidate capability directory. Returns None if absent or malformed."""
    if not _is_valid_name(name):
        return None
    if not cap_dir.is_dir():
        return None
    package_yaml = cap_dir / "package.yaml"
    if not package_yaml.is_file():
        return None
    package = _read_package_yaml(package_yaml)
    if package is None or package.name != name:
        return None
    return CapabilitySource(name=name, path=cap_dir, package=package)


def refuse_reserved_capability_name(name: str) -> None:
    """Refuse a capability name in `RESERVED_CAPABILITY_NAMES`.

    Called by every path that brings a capability into a project — create
    (`pkit new capability`), install, and register — so a reserved name is
    refused before any file is written or any registry entry is made.
    """
    reason = RESERVED_CAPABILITY_NAMES.get(name)
    if reason is not None:
        raise click.ClickException(
            f"capability name {name!r} is reserved: {reason}. Choose another name."
        )


def refuse_name_held_by_other_kind(target_root: Path, kind: ComponentKind, name: str) -> None:
    """Refuse a component of `kind` a name a component of the other kind holds.

    The other kind holds the name when the backbone manifest registers a component
    of that kind under it — `is_installed`'s reading — or its directory exists at
    `.pkit/<area>/<name>/` — the reading `pkit new adapter` and `pkit new
    capability` refuse an existing one by — so an unregistered capability authored
    in the tree holds its name too: its `package.yaml` is a component of the
    changesets all the same. Called where a component is named into a project —
    `pkit new adapter` (its stamp and its registration), `pkit new capability`, and
    every path that registers a capability (`_refuse_unregistrable`) — before any
    file is written or any registry entry is made. The reason is
    `SHARED_NAME_REASON`.
    """
    other: ComponentKind = "capability" if kind == "adapter" else "adapter"
    backbone = read_backbone_manifest(target_root)
    directory = f".pkit/{_COMPONENT_AREAS[other]}/{name}/"
    if backbone is not None and any(
        c.kind == other and c.name == name for c in backbone.components
    ):
        where = "registered in `.pkit/manifest.yaml`"
    elif (target_root / directory).exists():
        where = f"at `{directory}`"
    else:
        return
    raise click.ClickException(
        f"{kind} name {name!r} is held by the {other} {name!r} {where}: "
        f"{SHARED_NAME_REASON}. Choose another name."
    )


def find_capability_in_source(source_kit: Path, name: str) -> CapabilitySource | None:
    """Locate a capability in the kit source. Returns None if absent."""
    return _resolve_capability_dir(source_kit / "capabilities" / name, name)


def find_capability_in_repo(target_root: Path, name: str) -> CapabilitySource | None:
    """Locate a capability authored in the adopter's own repo (per COR-031).

    Resolves ``<target_root>/.pkit/capabilities/<name>/`` — the adopter's
    own capabilities tree — distinct from the kit-source resolver above.
    This is the incubated-in-repo origin: the working tree *is* the source,
    so register/deploy consume the returned ``CapabilitySource`` in place,
    without copying from kit source. Returns None if absent or malformed.

    Note the path overlaps the *install destination* of a kit-shipped
    capability: a kit-shipped capability that has already been installed
    also lives under ``.pkit/capabilities/<name>/``. This resolver does not
    distinguish the two — it answers "is there a usable capability subtree
    in the repo at this name?". Origin (incubated vs. installed-kit-shipped)
    is a lifecycle-owned property recorded in install-state (COR-031 D2),
    not something this resolver infers.
    """
    return _resolve_capability_dir(target_root / ".pkit" / "capabilities" / name, name)


def authored_in_source(target_root: Path, source_kit: Path, name: str) -> bool:
    """True when the capability's subtree in *target_root* is its source, not a copy (#1107).

    *source_kit* is the methodology tree the running code resolves
    (`install.find_source_kit`), the tree `install` and `upgrade` copy a
    kit-shipped capability from. `<target_root>/.pkit/capabilities/<name>/`
    lies inside it in the methodology's source repository run by its own code —
    where sync's test holds (ADR-059 point 2) — and there the subtree is where
    the capability is authored. The lifecycle then copies nothing onto it and
    never deletes it: uninstall deletes a kit-shipped subtree only because it is
    a disposable copy (COR-031 D4), and the source is never a copy. Where other
    code runs in the source, sync's test says no and the capability verbs refuse
    instead (`install.refuse_propagation_into_source`).
    """
    subtree = target_root / ".pkit" / "capabilities" / name
    return subtree.resolve().is_relative_to(source_kit.resolve())


# Which source a caller wants when a name resolves in more than one place.
CapabilityOrigin = str  # "kit-shipped" | "incubated-in-repo"

# The origin string values have a single canonical definition in
# `manifest.py` (COR-031 D2 — origin is lifecycle-owned install-state, so the
# manifest layer owns it). These module-level names are stable aliases kept
# here so capability callers can keep referring to `caps.KIT_SHIPPED` /
# `caps.INCUBATED_IN_REPO`; both bind to the manifest constants, so there is
# one source of truth for the strings themselves.
KIT_SHIPPED: CapabilityOrigin = ORIGIN_KIT_SHIPPED
INCUBATED_IN_REPO: CapabilityOrigin = ORIGIN_INCUBATED_IN_REPO


@dataclass(frozen=True)
class ResolvedCapability:
    """The outcome of resolving a capability name across both possible sources.

    Carries the chosen source plus enough context for the caller to surface
    a both-present collision (COR-031's boundary case: "surface the collision
    rather than silently skip it") instead of one source silently shadowing
    the other.
    """

    source: CapabilitySource  # the selected source (per `prefer`)
    origin: CapabilityOrigin  # which tree the selected source came from
    in_kit_source: bool  # the name also resolved in the kit source
    in_repo: bool  # the name also resolved in the adopter's repo


def resolve_capability_source(
    name: str,
    *,
    source_kit: Path,
    target_root: Path,
    prefer: CapabilityOrigin,
) -> ResolvedCapability | None:
    """Resolve a capability name across both the kit source and the adopter's repo.

    Consults *both* resolvers and makes the both-present case unambiguous:
    the caller states which origin it wants via ``prefer`` (``KIT_SHIPPED``
    or ``INCUBATED_IN_REPO``), and that choice is honoured whenever the
    preferred source is present. The returned ``ResolvedCapability`` always
    reports ``in_kit_source`` / ``in_repo`` so the caller can detect — and
    surface — a name that exists in *both* trees rather than letting one
    silently shadow the other (COR-031 boundary case).

    Selection contract:
    - ``prefer`` present → return that source, with its origin.
    - ``prefer`` absent but the other source present → return the other
      source. (A pure preference, not a hard requirement: the caller asked
      for one origin but only the other exists; returning it lets the caller
      decide, rather than failing a resolvable name.)
    - neither present → ``None``.

    The caller never gets an ambiguous result: exactly one source is
    selected, deterministically, and the presence flags expose the overlap.
    """
    if prefer not in (KIT_SHIPPED, INCUBATED_IN_REPO):
        raise ValueError(
            f"prefer must be one of {KIT_SHIPPED!r}, {INCUBATED_IN_REPO!r}; got {prefer!r}"
        )

    kit_source = find_capability_in_source(source_kit, name)
    repo_source = find_capability_in_repo(target_root, name)
    in_kit_source = kit_source is not None
    in_repo = repo_source is not None

    if prefer == KIT_SHIPPED:
        order = ((kit_source, KIT_SHIPPED), (repo_source, INCUBATED_IN_REPO))
    else:
        order = ((repo_source, INCUBATED_IN_REPO), (kit_source, KIT_SHIPPED))

    for candidate, origin in order:
        if candidate is not None:
            return ResolvedCapability(
                source=candidate,
                origin=origin,
                in_kit_source=in_kit_source,
                in_repo=in_repo,
            )
    return None


def list_capabilities(target_root: Path, source_kit: Path) -> tuple[list[str], list[str]]:
    """Return (available_in_source, installed) capability-name lists."""
    available: list[str] = []
    source_caps = source_kit / "capabilities"
    if source_caps.is_dir():
        for entry in sorted(source_caps.iterdir()):
            if entry.is_dir() and (entry / "package.yaml").is_file():
                available.append(entry.name)

    installed: list[str] = []
    backbone = read_backbone_manifest(target_root)
    if backbone is not None:
        installed = [c.name for c in backbone.components if c.kind == "capability"]
    installed.sort()
    return available, installed


@dataclass(frozen=True)
class CatalogueEntry:
    """One capability the project can see without the network (COR-053 point 8)."""

    source: CapabilitySource  # where its package metadata is read from
    origin: CapabilityOrigin  # kit-shipped | incubated-in-repo
    installed: bool


def local_catalogue(target_root: Path, source_kit: Path) -> list[CatalogueEntry]:
    """Every capability readable locally, one entry per name, sorted by name.

    Three places, all on disk, none fetched: the capabilities registered in this
    project (their installed tree, origin as recorded); capability subtrees
    authored in this repository at `.pkit/capabilities/<name>/` and not
    registered (incubated, COR-031); and the capabilities that ship with the
    running pkit (`<source_kit>/capabilities/`, the tree installed with the
    tool). A name found in more than one place is read from the first, in that
    order — an unregistered in-repo copy is the one `register` would take, as
    its collision note says (COR-031). Where the in-repo tree *is* the kit source
    (the methodology's own repository), an unregistered capability is
    kit-shipped. A subtree that does not read as a capability is not listed.
    """
    origins = installed_capability_origins(target_root)
    entries: dict[str, CatalogueEntry] = {}
    for name in sorted(origins):
        source = find_capability_in_repo(target_root, name)
        if source is not None:
            entries[name] = CatalogueEntry(source, origins[name], installed=True)
    for parent, origin in (
        (target_root / ".pkit" / "capabilities", INCUBATED_IN_REPO),
        (source_kit / "capabilities", KIT_SHIPPED),
    ):
        if not parent.is_dir():
            continue
        for candidate in sorted(parent.iterdir()):
            name = candidate.name
            if name in entries:
                continue
            source = _resolve_capability_dir(candidate, name)
            if source is None:
                continue
            in_source = find_capability_in_source(source_kit, name)
            # The in-repo tree may be the kit source itself: then it ships.
            is_kit_source = (
                in_source is not None and in_source.path.resolve() == candidate.resolve()
            )
            entries[name] = CatalogueEntry(
                source, KIT_SHIPPED if is_kit_source else origin, installed=False
            )
    return [entries[name] for name in sorted(entries)]


def installed_capability_origins(target_root: Path) -> dict[str, str]:
    """Return ``{name: origin}`` for every registered capability (per COR-031).

    Reads origin from lifecycle-owned install-state (the backbone manifest's
    component registry), where an absent origin reads as ``kit-shipped``.
    Lets `list` / status mark each installed capability as kit-shipped or
    incubated-in-repo without the caller re-deriving the default.
    """
    backbone = read_backbone_manifest(target_root)
    if backbone is None:
        return {}
    return {c.name: c.origin for c in backbone.components if c.kind == "capability"}


def is_installed(target_root: Path, name: str) -> bool:
    """True if the named capability is registered in the adopter's backbone manifest."""
    backbone = read_backbone_manifest(target_root)
    if backbone is None:
        return False
    return any(c.kind == "capability" and c.name == name for c in backbone.components)


def get_installed_capability_version(target_root: Path, name: str) -> str | None:
    """Return the installed version of a capability, or None if not installed / unreadable.

    Reads the capability's manifest as every reader of its record does
    (``read_capability_record``), falling back to its installed
    ``package.yaml``. This is the public counterpart of the private
    ``_read_installed_capability_version``; exposing it lets the
    upgrade layer query installed versions without importing private
    internals.
    """
    return _read_installed_capability_version(target_root, name)


# The key of a capability manifest's `backend_state` that lists the artefacts
# the project chose to skip on a naming collision (COR-017).
SKIPPED_KEY = "skipped"


@dataclass(frozen=True)
class CapabilityRecord:
    """What a project records for one installed capability (ADR-065 point 2).

    Read from the capability's manifest: at its root where one is still there,
    else under its ``project/`` (``manifest.recorded_capability_manifest``).
    With no manifest that reads, its version falls back to the installed
    ``package.yaml``, which a copy replaces, so a record is read before
    propagation.
    """

    name: str
    # The manifest's version, else the installed package.yaml's; None when neither reads.
    version: str | None
    # The skips the project chose, from `backend_state.skipped`.
    skipped: tuple[tuple[str, str], ...] = ()
    # The manifest still sits at the capability's root, where a copy prunes it.
    at_root: bool = False


def read_capability_record(target_root: Path, name: str) -> CapabilityRecord:
    """Read what the project records for capability *name* (ADR-065 point 2).

    The one reader behind the version and the skips: the capability downgrade
    check, the dependency gates and a refresh read through it. The manifest
    read is the root one where it exists, then the one under ``project/``. A
    manifest that does not parse reads as recording nothing, and the version
    then falls back to the installed ``package.yaml``, the version of record
    for an incubated capability, which has no manifest (COR-031 D2). A
    refresh's restamp then writes a new manifest (`_stamp_component_manifest`).
    """
    manifest = recorded_capability_manifest(target_root, name)
    raw = _load_mapping(manifest) if manifest is not None else None
    version: str | None = None
    skipped: tuple[tuple[str, str], ...] = ()
    if raw is not None:
        component = raw.get("component")
        if isinstance(component, dict):
            recorded = cast("dict[str, Any]", component).get("version")
            if isinstance(recorded, str):
                version = recorded
        state = raw.get("backend_state")
        if isinstance(state, dict):
            skipped = _parse_skipped(cast("dict[str, Any]", state).get(SKIPPED_KEY))
    if version is None:
        package_path = target_root / ".pkit" / "capabilities" / name / "package.yaml"
        package = _read_package_yaml(package_path) if package_path.is_file() else None
        if package is not None:
            version = package.version
    return CapabilityRecord(
        name=name,
        version=version,
        skipped=skipped,
        at_root=manifest is not None
        and manifest == capability_root_manifest_path(target_root, name),
    )


def read_capability_records(target_root: Path) -> dict[str, CapabilityRecord]:
    """The record of every registered capability, by name (``read_capability_record``)."""
    backbone = read_backbone_manifest(target_root)
    if backbone is None:
        return {}
    return {
        entry.name: read_capability_record(target_root, entry.name)
        for entry in backbone.components
        if entry.kind == "capability"
    }


def move_capability_manifest(target_root: Path, name: str) -> bool:
    """Move a capability's manifest from its root under its ``project/`` (ADR-065 point 2).

    Under ``project/`` no copy of the capability's tree deletes or overwrites
    it. The root manifest wins: it replaces one already under ``project/``.
    The registry entry is pointed at the new path before the root file goes,
    so an interrupted move leaves two equal copies, which the next move
    finishes. Returns True when a root manifest was moved, False when none was
    there.

    The code that writes the record calls it, never sync: the version
    transition, before its copy (``upgrade.run_upgrade``), and the refresh of
    ``pkit capabilities upgrade``, before its migrations and its copy
    (``refresh_capability``).
    """
    root = capability_root_manifest_path(target_root, name)
    if not root.is_file():
        return False
    dest = capability_manifest_path(target_root, name)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(root, dest)
    set_component_manifest_path(target_root, "capability", name, capability_manifest_rel(name))
    root.unlink()
    return True


def record_skips(
    target_root: Path,
    name: str,
    skipped: Sequence[tuple[str, str]],
    *,
    version: str | None,
) -> bool:
    """Record the skips in force in the capability's manifest, before its copy (ADR-065 point 6).

    A transition records each skip a person chose on a new collision in step 2,
    after the manifest's move under ``project/`` and before the copy. So a
    transition a migration stops does not ask again: the next one reads the
    skip, and the collision is no longer new. The manifest's version and every
    other key of ``backend_state`` stay as they are, until the restamp after the
    capability's migrations.

    A capability with no manifest under ``project/`` gets one at *version*, the
    version it records, with the skips alone. With no version to record, or a
    manifest that does not read as a mapping, nothing is written, and the
    restamp records the skips. Returns True when the manifest was written.
    """
    path = capability_manifest_path(target_root, name)
    entries = [{"kind": kind, "name": artefact} for kind, artefact in skipped]
    if path.is_file():
        if _load_mapping(path) is None:
            return False
        manifest = read_component_manifest(path)
        if manifest is None:
            return False
    elif version is not None:
        manifest = ComponentManifest(
            kind="capability",
            name=name,
            version=version,
            installed_at=_dt.datetime.now(_dt.UTC).isoformat(),
            requires_backbone="",
            backend_state={},
        )
    else:
        return False
    manifest.backend_state = {
        key: value for key, value in manifest.backend_state.items() if key != SKIPPED_KEY
    }
    if entries:
        manifest.backend_state[SKIPPED_KEY] = entries
    write_component_manifest(path, manifest)
    set_component_manifest_path(target_root, "capability", name, capability_manifest_rel(name))
    return True


@dataclass(frozen=True)
class CapabilityDependencyConflict:
    """One failing dependency found during the pre-flight check (COR-030)."""

    dep_name: str  # the dependency capability's name
    dep_version_range: str  # the declared range (e.g. ">=0.2.0,<1.0.0")
    installed_version: str | None  # None means not installed at all
    reason: str  # "absent" or "out-of-range"


def check_capability_dependencies(
    target_root: Path,
    requires_capabilities: tuple[CapabilityDependency, ...],
) -> list[CapabilityDependencyConflict]:
    """Evaluate declared dependency requirements against the installed state.

    This is the shared predicate used by *both* the install pre-flight
    (refusing to install a dependent when a dependency is absent or out-
    of-range) and the single-capability-upgrade check (refusing to upgrade
    a dependent capability when a dependency is out-of-range). It never
    auto-installs.

    For each ``CapabilityDependency`` in ``requires_capabilities``:
    - If a required dependency is not installed → conflict with reason
      "absent". An optional one that is not installed passes: the dependent
      works without it (COR-030).
    - If the dependency is installed but its version does not satisfy the
      declared semver range → conflict with reason "out-of-range".
    - If the range string is invalid (unparseable) → silently skip (the
      package.yaml is malformed; the gate can only work with valid ranges).

    Returns a list of conflicts; empty means all requirements satisfied.

    Reuses ``is_installed`` and ``get_installed_capability_version`` (this
    module) for the installed-state side, and compares the range through
    the wiring resolver's one version-range relation
    (``connections.range_admits``, ADR-057 point 2), so this gate and
    ``pkit validate`` never disagree on whether a range admits a version.
    """
    # Imported here: the resolver imports this module (through rule sets).
    from project_kit.connections import range_admits

    if not requires_capabilities:
        return []

    conflicts: list[CapabilityDependencyConflict] = []
    for dep in requires_capabilities:
        if not is_installed(target_root, dep.name):
            if dep.optional:
                continue
            conflicts.append(
                CapabilityDependencyConflict(
                    dep_name=dep.name,
                    dep_version_range=dep.version,
                    installed_version=None,
                    reason="absent",
                )
            )
            continue

        installed_version = get_installed_capability_version(target_root, dep.name)
        if installed_version is None:
            # Installed but version unreadable — treat as a soft miss
            # rather than blocking: the manifest is the adopter's own
            # record and unreadable manifests are already a degraded state.
            continue

        # A malformed range or version (None) can't be evaluated — skip.
        if range_admits(dep.version, installed_version) is False:
            conflicts.append(
                CapabilityDependencyConflict(
                    dep_name=dep.name,
                    dep_version_range=dep.version,
                    installed_version=installed_version,
                    reason="out-of-range",
                )
            )

    return conflicts


def find_declared_dependents(target_root: Path, dep_name: str) -> list[str]:
    """Find all installed capabilities that declare *dep_name* in their requires_capabilities.

    Every declaring capability is returned, whether its entry is required or
    optional: the install and upgrade gates judge each declared range
    (COR-030). The uninstall gate keeps only the dependents that declare the
    target required, at its call site, since an optional dependency never
    blocks uninstalling its target. Walks the backbone manifest's component
    registry, filters to capabilities, and reads each one's installed
    package.yaml to extract ``requires_capabilities``.

    Returns a sorted list of dependent capability names (may be empty).
    """
    backbone = read_backbone_manifest(target_root)
    if backbone is None:
        return []

    dependents: list[str] = []
    for entry in backbone.components:
        if entry.kind != "capability":
            continue
        if entry.name == dep_name:
            continue  # skip self
        # Read the installed package.yaml to get requires_capabilities.
        pkg_yaml_path = target_root / ".pkit" / "capabilities" / entry.name / "package.yaml"
        if not pkg_yaml_path.is_file():
            continue
        pkg = _read_package_yaml(pkg_yaml_path)
        if pkg is None:
            continue
        for dep in pkg.requires_capabilities:
            if dep.name == dep_name:
                dependents.append(entry.name)
                break

    dependents.sort()
    return dependents


def declared_dependencies(
    target_root: Path, dependent: str, dep_name: str
) -> tuple[CapabilityDependency, ...]:
    """The entries the installed capability *dependent* declares for *dep_name* in its
    ``requires_capabilities`` (COR-030) — every one, should it list the name twice —
    or none when it declares none or its package.yaml does not read. The one reader
    of a found dependent's entries."""
    pkg_yaml_path = target_root / ".pkit" / "capabilities" / dependent / "package.yaml"
    if not pkg_yaml_path.is_file():
        return ()
    pkg = _read_package_yaml(pkg_yaml_path)
    if pkg is None:
        return ()
    return tuple(dep for dep in pkg.requires_capabilities if dep.name == dep_name)


@dataclass(frozen=True)
class MandatoryUpstream:
    """A mandatory process connection a wiring leaves unmet (COR-053 point 6).

    `capability` carries the mark: one of its generated `depends-on` entries names
    `process` as mandatory, for `reason`; `problem` says why the upstream is not
    met in the wiring the operation would leave — missing, or at another
    interface version.
    """

    capability: str
    process: str
    reason: str
    problem: str


def unmet_mandatory_upstreams(
    target_root: Path, capability_source: CapabilitySource
) -> list[MandatoryUpstream]:
    """The mandatory upstreams the capability would find missing or incompatible
    once installed, registered or upgraded to `capability_source` — the side
    carrying the mark, which the lifecycle refuses (COR-053 point 6).

    Read from the capability's generated `depends-on` list in its package
    metadata, never from its process definitions (validation keeps the list
    fresh), and judged by the one wiring resolver over the installed set with
    the capability in place of any installed copy — the wiring the operation
    would leave, as its plan computes it. An interface version is compatible
    when it is equal (COR-053 point 5); the capability ranges of COR-030 stay
    `check_capability_dependencies`'s.
    """
    from project_kit import connections as cx

    candidate = _as_candidate(target_root, capability_source)
    if candidate is None:
        return []  # a package that does not read is the self-consistency check's
    after = cx.resolve_wiring_with(target_root, add=[candidate], remove=[candidate.name])
    return [
        _mandatory_upstream(binding, after)
        for binding in after.unmet_marks(cx.CounterpartKind.DEPENDENCY)
        if binding.counterpart.capability == candidate.name
    ]


def mandatory_counterparts_left_unmet(
    target_root: Path,
    name: str,
    *,
    replacement: CapabilitySource | None = None,
) -> list[MandatoryUpstream]:
    """The other capabilities' mandatory process connections that uninstalling
    `name` — or, with `replacement`, upgrading it to that source — would leave
    unmet: met, or at least not unmet, in the live wiring and unmet after. The
    side targeted by the marks, which the lifecycle warns about and lets
    through only under force (COR-053 point 6, COR-030's direction split).
    """
    from project_kit import connections as cx

    added = [_as_candidate(target_root, replacement)] if replacement is not None else []
    before = cx.resolve_wiring(target_root)
    after = cx.resolve_wiring_with(
        target_root, add=[c for c in added if c is not None], remove=[name]
    )
    unmet_before = {_mark_key(b) for b in before.unmet_marks(cx.CounterpartKind.DEPENDENCY)}
    return [
        _mandatory_upstream(binding, after)
        for binding in after.unmet_marks(cx.CounterpartKind.DEPENDENCY)
        if binding.counterpart.capability != name and _mark_key(binding) not in unmet_before
    ]


def marks_a_transition_leaves_unmet(
    target_root: Path, sources: Sequence[CapabilitySource]
) -> tuple[list[MandatoryUpstream], list[MandatoryUpstream]]:
    """The mandatory process connections a transition moving *sources* would leave
    unmet (COR-053 point 6, ADR-065 point 6), in COR-030's direction split.

    The wiring judged is the one the transition would leave: each capability of
    *sources* at its source version in place of its installed copy, every other
    at its installed version. Returns two lists, judged as `capabilities
    upgrade` judges each side:

    - the marks a moving capability carries that this wiring leaves unmet,
      which the transition refuses (`unmet_mandatory_upstreams`)
    - the marks of a capability that does not move that this wiring leaves
      unmet and the live wiring does not, which the transition warns about and
      lets through only under its `--force` (`mandatory_counterparts_left_unmet`).
      A mark of such a capability already unmet before is not the transition's
      to report.
    """
    from project_kit import connections as cx

    candidates = [c for c in (_as_candidate(target_root, s) for s in sources) if c is not None]
    if not candidates:
        return [], []
    moving = {c.name for c in candidates}
    after = cx.resolve_wiring_with(target_root, add=candidates, remove=moving)
    unmet = after.unmet_marks(cx.CounterpartKind.DEPENDENCY)
    carried = [_mandatory_upstream(b, after) for b in unmet if b.counterpart.capability in moving]
    staying = [b for b in unmet if b.counterpart.capability not in moving]
    if not staying:
        return carried, []
    before = cx.resolve_wiring(target_root)
    unmet_before = {_mark_key(b) for b in before.unmet_marks(cx.CounterpartKind.DEPENDENCY)}
    left = [_mandatory_upstream(b, after) for b in staying if _mark_key(b) not in unmet_before]
    return carried, left


def _as_candidate(target_root: Path, source: CapabilitySource) -> Installed | None:
    """`source` as the wiring resolver reads a component once installed: its package
    file where the operation puts it, its companions and definitions read where
    they are now (`capability_plans.as_installed`)."""
    from project_kit import capability_plans as plans

    candidate = plans.candidate_of(source, KIT_SHIPPED, installed=False)
    return plans.as_installed(target_root, candidate) if candidate is not None else None


def _mark_key(binding: Binding) -> tuple[str, str]:
    """One mark across two wirings: the capability carrying it and where."""
    return (binding.counterpart.capability, binding.counterpart.pointer)


def _mandatory_upstream(binding: Binding, wiring: Wiring) -> MandatoryUpstream:
    """An unmet mandatory `depends-on` binding, with why its upstream is not met."""
    from project_kit import connections as cx

    counterpart = binding.counterpart
    status = binding.status
    capability, _, process_id = counterpart.target.partition(":")
    if status is cx.BindingStatus.NOT_INSTALLED:
        problem = f"its capability {capability!r} is not installed"
    elif status is cx.BindingStatus.NO_ACTIVE_PROVIDER:
        problem = f"no installed capability provides role {counterpart.role!r}"
    elif status is cx.BindingStatus.INERT_VERSION and binding.point is not None:
        problem = (
            f"{binding.point.provider!r} offers it at interface version "
            f"{binding.point.version}, and the entry targets version {counterpart.version}"
        )
    elif counterpart.role_form:
        role = wiring.role(counterpart.role or "")
        provider = role.active if role is not None else None
        problem = (
            f"{provider!r}, the active provider of role {counterpart.role!r}, offers no "
            f"process at that address"
        )
    else:
        problem = f"{capability!r} neither offers nor defines process {process_id!r}"
    return MandatoryUpstream(
        capability=counterpart.capability,
        process=counterpart.target,
        reason=counterpart.mandatory or "",
        problem=problem,
    )


@dataclass(frozen=True)
class CollisionFinding:
    """One naming collision detected during install pre-flight."""

    artifact_kind: str  # "skill" or "agent"
    artifact_name: str  # the colliding name
    source_path: Path  # the capability's file
    target_path: Path  # the existing file the new one would collide with


def detect_collisions(
    target_root: Path,
    capability_source: CapabilitySource,
    exclude: str | None = None,
) -> list[CollisionFinding]:
    """Find naming collisions between a capability's artifacts and already-installed content.

    Today checks: skills + agents. Capability decisions are namespaced
    by the capability's directory name, so they cannot collide.

    `exclude` is threaded to `_collect_existing_artifact_names` to skip a
    capability's own installed tree in the existing-names walk (see #225);
    existing callers default to None and are unaffected.
    """
    findings: list[CollisionFinding] = []
    # Skills collision: walk capability's skills/ and check against existing skills.
    cap_skills = capability_source.path / "skills"
    if cap_skills.is_dir():
        existing_skill_names = _collect_existing_artifact_names(
            target_root, "skills", exclude=exclude
        )
        for sk_file in sorted(cap_skills.iterdir()):
            if sk_file.is_file() and sk_file.suffix == ".md":
                name = sk_file.stem
                if name in existing_skill_names:
                    findings.append(
                        CollisionFinding(
                            artifact_kind="skill",
                            artifact_name=name,
                            source_path=sk_file,
                            target_path=existing_skill_names[name],
                        )
                    )
    # Agents collision: same.
    cap_agents = capability_source.path / "agents"
    if cap_agents.is_dir():
        existing_agent_names = _collect_existing_artifact_names(
            target_root, "agents", exclude=exclude
        )
        for ag_file in sorted(cap_agents.iterdir()):
            if ag_file.is_file() and ag_file.suffix == ".md":
                name = ag_file.stem
                if name in existing_agent_names:
                    findings.append(
                        CollisionFinding(
                            artifact_kind="agent",
                            artifact_name=name,
                            source_path=ag_file,
                            target_path=existing_agent_names[name],
                        )
                    )
    return findings


# The area folder under `.pkit/` that holds artefacts of each kind a collision
# names: the project's own in its `project/`, core's in its `core/`, and each
# capability's in `.pkit/capabilities/<name>/<area>/`.
_ARTEFACT_AREAS: dict[str, str] = {"skill": "skills", "agent": "agents"}


def project_artefact_paths(target_root: Path, kind: str, name: str) -> tuple[Path, ...]:
    """The project's own artefact of `kind` and `name`, in each form it has.

    These are what an override removes (COR-017). A skill or an agent is a file
    `<name>.md`, or a folder `<name>/` holding `<name>.md` (COR-015). A project
    may hold both forms, and either deploys under the name, so an override
    removes both. Empty when the project has none.
    """
    project_dir = target_root / ".pkit" / _ARTEFACT_AREAS[kind] / "project"
    flat = project_dir / f"{name}.md"
    folder = project_dir / name
    paths: list[Path] = []
    if flat.is_file():
        paths.append(flat)
    if (folder / f"{name}.md").is_file():
        paths.append(folder)
    return tuple(paths)


def shipped_artefact_paths(
    target_root: Path, kind: str, name: str, *, capability: str
) -> tuple[Path, ...]:
    """Core's artefact of `kind` and `name`, and each other capability's: what an override leaves.

    They are not the project's to remove (the no-shared-files invariant, COR-001),
    so an override leaves them, and the deploy's name precedence picks among them
    and the capability's. `capability` names the capability the collision is
    resolved for: its own installed copy is not listed. Each is the artefact's
    file, `<name>.md` or `<name>/<name>.md` (COR-015).
    """
    area = _ARTEFACT_AREAS[kind]
    folders = [target_root / ".pkit" / area / "core"]
    caps_dir = target_root / ".pkit" / "capabilities"
    if caps_dir.is_dir():
        folders.extend(
            cap / area
            for cap in sorted(caps_dir.iterdir())
            if cap.is_dir() and cap.name != capability
        )
    return tuple(
        candidate
        for folder in folders
        for candidate in (folder / f"{name}.md", folder / name / f"{name}.md")
        if candidate.is_file()
    )


def paths_git_cannot_restore(target_root: Path, paths: Sequence[Path]) -> tuple[Path, ...]:
    """The paths among `paths` that git could not give back as they stand.

    Git gives a path back when it is tracked, and nothing at it or beneath it
    differs from the last commit, is untracked or is ignored. Outside a git work
    tree, or without git, no path can be given back. An override removes the
    project's artefact only when git keeps it (COR-017: "the prior content
    recovers via git").
    """

    def _git(*args: str) -> bytes:
        return subprocess.run(
            ["git", *args], cwd=target_root, capture_output=True, check=True
        ).stdout

    lost: list[Path] = []
    for path in paths:
        rel = path.relative_to(target_root).as_posix()
        try:
            tracked = _git("ls-files", "-z", "--", rel)
            changed = _git(
                "status", "--porcelain", "-z", "--ignored", "--untracked-files=all", "--", rel
            )
        except (OSError, subprocess.CalledProcessError):
            lost.append(path)
            continue
        if not tracked or changed:
            lost.append(path)
    return tuple(lost)


def remove_overridden(paths: Sequence[Path]) -> None:
    """Remove the project's artefacts an override replaces: each file or folder in `paths`.

    The caller checks first that git keeps them (`paths_git_cannot_restore`).
    """
    for path in paths:
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path)
        else:
            path.unlink(missing_ok=True)


def resolve_collision_interactive(
    target_root: Path, finding: CollisionFinding, *, capability: str
) -> str:
    """Ask the person for override, skip or inspect on one collision (COR-017).

    The one prompt a capability's install, `pkit capabilities upgrade
    --interactive` and a version transition ask. It loops on `inspect`, which
    shows the diff and asks again, until the person picks override or skip, and
    returns that choice.

    Before each prompt it names what `override` would do: each path of the
    project's own artefact of that name it removes, which the caller removes
    (`apply_overrides`), and each artefact core or another capability ships,
    which it leaves. `override` is refused, and the prompt asked again, while
    git could not give the project's artefact back as it stands.
    """
    kind, name = finding.artifact_kind, finding.artifact_name
    replaced = project_artefact_paths(target_root, kind, name)
    left = shipped_artefact_paths(target_root, kind, name, capability=capability)
    while True:
        click.echo(
            f"  - {kind} '{name}' collides with existing "
            f"{finding.target_path.relative_to(target_root)}"
        )
        unheld = paths_git_cannot_restore(target_root, replaced)
        for path in replaced:
            click.echo(
                f"    override removes {path.relative_to(target_root)}, "
                + (
                    "which git does not hold as it stands, so override is refused"
                    if path in unheld
                    else "which git keeps"
                )
            )
        for path in left:
            click.echo(
                f"    override leaves {path.relative_to(target_root)}: it is not the "
                "project's, and the deploy's name precedence picks which one deploys"
            )
        choice = click.prompt(
            "    [override / skip / inspect]",
            type=click.Choice(["override", "skip", "inspect"]),
            default="inspect",
            show_default=False,
        )
        if choice == "inspect":
            show_unified_diff(finding.target_path, finding.source_path)
            continue
        if choice == "override":
            lost = paths_git_cannot_restore(target_root, replaced)
            if lost:
                for path in lost:
                    click.echo(
                        f"    override refused: {path.relative_to(target_root)} is not "
                        "committed as it stands, so git could not give it back. "
                        "Choose skip, or commit it and choose override."
                    )
                continue
        return choice


def apply_overrides(target_root: Path, paths: Sequence[Path], *, dry_run: bool) -> None:
    """Remove the project's artefacts an override chose to replace, naming each (COR-017).

    Runs before deploy, so the project's artefact no longer comes first under the
    name. A capability's install runs it after its copy. A transition runs it
    before its copy, beside the skips it records, so the answer holds when a
    migration stops the transition: the next one finds the name in the
    capability's installed copy, and asks nothing. Git keeps what is removed: the
    prompt refused an override git could not give back.
    """
    if not dry_run:
        remove_overridden(paths)
    verb = "would remove" if dry_run else "removed"
    for path in paths:
        click.echo(f"  {verb:<12} {path.relative_to(target_root)} (override; git keeps it)")


def show_unified_diff(existing: Path, incoming: Path) -> None:
    """Show a unified diff between the existing file and the incoming one."""
    try:
        result = subprocess.run(
            ["git", "diff", "--no-index", "--color=always", str(existing), str(incoming)],
            capture_output=True,
            text=True,
        )
        click.echo(result.stdout)
    except FileNotFoundError:
        # git not available: fall back to a plain difflib diff.
        import difflib

        existing_lines = existing.read_text().splitlines(keepends=True)
        incoming_lines = incoming.read_text().splitlines(keepends=True)
        diff = difflib.unified_diff(
            existing_lines,
            incoming_lines,
            fromfile=str(existing),
            tofile=str(incoming),
        )
        for line in diff:
            click.echo(line, nl=False)


def install_capability(
    target_root: Path,
    capability_source: CapabilitySource,
    *,
    skipped_artifacts: tuple[tuple[str, str], ...] = (),
    dry_run: bool = False,
) -> Path:
    """Copy the capability subtree into the adopter and register it.

    `skipped_artifacts` is a tuple of (artifact_kind, artifact_name)
    pairs the adopter chose to skip during interactive collision
    resolution. These files are NOT copied from source; their absence
    is recorded in the per-component manifest's `backend_state`.

    Returns the installed path: `<target_root>/.pkit/capabilities/<name>/`.

    Refuses to install if the capability is already installed in the
    adopter — caller must check first via `is_installed` — if its name
    is reserved (`refuse_reserved_capability_name`) or an adapter holds it
    (`refuse_name_held_by_other_kind`), or if the source is the
    destination (`_refuse_copy_onto_itself`; `register_capability_in_source`
    registers that one).
    """
    _refuse_unregistrable(target_root, capability_source.name)

    dest = target_root / ".pkit" / "capabilities" / capability_source.name
    _refuse_copy_onto_itself(capability_source.path, dest)
    if dry_run:
        return dest

    # Copy the subtree, omitting any skipped artifacts.
    _copy_capability_tree(capability_source.path, dest, skipped_artifacts)

    # Register in the backbone manifest.
    _register_in_backbone_manifest(target_root, capability_source.name)

    # Stamp per-component manifest with version + install timestamp + skip state.
    _stamp_component_manifest(target_root, capability_source, skipped_artifacts)

    return dest


def register_incubated_capability(
    target_root: Path,
    capability_source: CapabilitySource,
    *,
    dry_run: bool = False,
) -> Path:
    """Register an in-repo (incubated) capability without copying (per COR-031 D3).

    For a kit-shipped capability, entering the project means copying the
    subtree from kit source (`install_capability`). For an incubated
    capability the subtree is *already in place* in the adopter's own repo
    — source and destination are the same directory — so this records and
    activates the capability but performs **no copy**:

    - registers it in the backbone component registry with
      ``origin: incubated-in-repo`` (COR-031 D2 — recorded in lifecycle-
      owned install-state, never inside the capability's adopter-owned
      subtree);
    - stamps no per-component manifest into the capability tree — that tree
      is entirely adopter-owned (the no-shared-files invariant, COR-001), so
      writing lifecycle state into it would re-create the ownership blur
      this path exists to avoid. Install-state lives in the backbone
      manifest alone for an incubated capability.

    Deploy (skills/agents) and dependency-gating registration are the
    caller's responsibility and happen identically to a kit-shipped
    capability — the caller runs the adapter deploy primitives after this,
    exactly as the kit-source install path does. Origin governs source-
    reconciliation only, not participation (COR-031 D1).

    Skipped-artifacts / collision handling is **not** part of this path:
    the capability's skills and agents are already present in the adopter's
    own tree (the adopter authored them), so there is nothing to copy and
    nothing to selectively omit.

    Refuses if the capability is already registered or its name is
    reserved (`refuse_reserved_capability_name`) or an adapter's
    (`refuse_name_held_by_other_kind`). Guards that the
    resolved source genuinely lives at the in-repo destination — the copy
    primitive (`refresh_owned_tree`) is *not* safe for source == dest, and
    this path must never reach it; the guard makes that structural rather
    than incidental.

    Returns the in-place path: ``<target_root>/.pkit/capabilities/<name>/``.
    """
    name = capability_source.name
    _refuse_unregistrable(target_root, name)

    dest = target_root / ".pkit" / "capabilities" / name
    # The incubated subtree *is* the destination. Assert source == dest so
    # the no-copy contract (COR-031 D3) is enforced here and the copy
    # primitive is never invoked on an in-place tree (which it would
    # clobber). Resolve both sides to compare canonical paths.
    if capability_source.path.resolve() != dest.resolve():
        raise click.ClickException(
            f"register_incubated_capability expects the capability to live in "
            f"the adopter's repo at {dest}, but its source resolved to "
            f"{capability_source.path}. Use 'install_capability' for a "
            f"kit-shipped capability that must be copied in."
        )

    if dry_run:
        return dest

    # Record + activate, but DO NOT copy: the subtree is already in place.
    _register_in_backbone_manifest(target_root, name, origin=INCUBATED_IN_REPO)
    return dest


def register_capability_in_source(
    target_root: Path,
    capability_source: CapabilitySource,
    *,
    dry_run: bool = False,
) -> Path:
    """Register a capability whose source is its destination, without copying (#1107).

    In the methodology's source repository run by its own code
    (`authored_in_source`), the tree `install_capability` would copy from is
    the destination itself. As for an incubated capability (COR-031 D3),
    registration then records the capability and copies nothing. It is
    registered ``kit-shipped``, the origin `install` gives, as the source
    registers the capabilities it ships. No per-component receipt is stamped
    into the subtree: it is authored source, so its install-state lives in the
    backbone manifest alone, as an incubated capability's does (COR-031 D2).
    Deploy is the caller's, as after `install_capability`.

    Refuses, as `install_capability` does, a reserved, adapter-held or
    already-registered name; and a source that is not the destination, which
    `install_capability` copies in.

    Returns the in-place path: ``<target_root>/.pkit/capabilities/<name>/``.
    """
    name = capability_source.name
    _refuse_unregistrable(target_root, name)

    dest = target_root / ".pkit" / "capabilities" / name
    if capability_source.path.resolve() != dest.resolve():
        raise click.ClickException(
            f"register_capability_in_source expects the capability's source to be its "
            f"destination {dest}, but it resolved to {capability_source.path}. Use "
            f"'install_capability' for a capability that must be copied in."
        )

    if dry_run:
        return dest

    _register_in_backbone_manifest(target_root, name)
    return dest


def read_prior_skipped_artifacts(
    target_root: Path, capability_name: str
) -> tuple[tuple[str, str], ...]:
    """The skips the project chose for a capability, from its manifest's `backend_state.skipped`.

    Read where they are written (``_stamp_component_manifest``), by
    ``read_capability_record``. Returns an empty tuple when no manifest exists
    or it's malformed — the worst case is the next refresh copies the
    previously-skipped file, which the adopter can re-skip on the next install
    with the interactive resolver if needed.
    """
    return read_capability_record(target_root, capability_name).skipped


def _parse_skipped(raw: object) -> tuple[tuple[str, str], ...]:
    """`backend_state.skipped` as `(kind, name)` pairs; a malformed item is left out."""
    if not isinstance(raw, list):
        return ()
    out: list[tuple[str, str]] = []
    for item in cast("list[object]", raw):
        if isinstance(item, dict):
            entry = cast("dict[str, object]", item)
            kind = entry.get("kind")
            name = entry.get("name")
            if isinstance(kind, str) and isinstance(name, str):
                out.append((kind, name))
    return tuple(out)


def _load_mapping(path: Path) -> dict[str, Any] | None:
    """A YAML file's top-level mapping, or None when it cannot be read or is not one."""
    try:
        raw = _yaml.load(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return cast("dict[str, Any]", raw) if isinstance(raw, dict) else None


def validate_capability_self_consistency(
    capability_source: CapabilitySource,
) -> list[str]:
    """Structurally validate an incubated capability against its own tree (COR-031 D1).

    An incubated capability is hand-authored in the adopter's repo; nothing
    upstream validated it. Before activation, check its own manifest, schemas,
    and layout are structurally sound against the working tree (which is its
    spec). This is *self-consistency*, not source-reconciliation — origin
    suppresses the latter, never the former (COR-031 D1).

    Returns a list of human-readable problem descriptions; an empty list means
    the capability is structurally sound. Checks performed:

    - **package.yaml** — the same validator `pkit validate` runs over every
      installed package (`package_validate`): the shape against the package
      schema when the tree ships one, and the repository checks — declared
      name matches the directory, version and ranges parse, command scripts
      exist, connection points sit under provided roles with their companion
      schemas and commands present, documentation locations and friction
      places are relative. Only its *errors* refuse — an unknown key among
      them, since the package schema refuses one; under a tree's older,
      open schema an unknown key is a warning, `pkit validate`'s to show.
    - **README.md** is present (the capability's layout contract);
    - the capability's **own schema pairs** (under ``schemas/``) pass schema
      validation, reusing the same validator ``pkit schemas validate`` runs.

    Deeper citation/reference closure is corpus-wide (``refs.validate_corpus``)
    and runs post-activation, not here.
    """
    from project_kit import package_validate, schemas_validate

    problems: list[str] = []
    cap_dir = capability_source.path

    package_path = cap_dir / "package.yaml"
    schema, _note = package_validate.load_package_schema(_project_root_of(cap_dir))
    if package_path.is_file():
        report = package_validate.validate_package_file(
            package_path, schema, component_dir=cap_dir, expected_name=capability_source.name
        )
        findings = report.errors
    else:
        # A hand-built `CapabilitySource` with no file on disk: judge the
        # package it carries, so the checks still run standalone.
        findings = tuple(
            f
            for f in package_validate.validate_package(
                _package_as_mapping(capability_source.package),
                schema,
                component_dir=cap_dir,
                expected_name=capability_source.name,
            )
            if f.severity is package_validate.Severity.ERROR
        )
    problems.extend(f"package.yaml{f.path}: {f.message}" if f.path else f.message for f in findings)

    if not (cap_dir / "README.md").is_file():
        problems.append("README.md is missing (required capability layout).")

    schemas_dir = cap_dir / "schemas"
    if schemas_dir.is_dir():
        report = schemas_validate.validate_path(schemas_dir, resolve=False)
        for issue in report.issues:
            problems.append(f"schema {issue.location}: {issue.message}")

    return problems


def _project_root_of(cap_dir: Path) -> Path:
    """The project root a capability directory sits in — `<root>/.pkit/capabilities/<name>`
    — where the package schema is read from (ADR-056 point 1). A directory not in
    that layout yields its own parent, where no schema will be found and the
    validator runs its repository checks alone."""
    if cap_dir.parent.name == "capabilities" and cap_dir.parent.parent.name == ".pkit":
        return cap_dir.parent.parent.parent
    return cap_dir.parent


def _package_as_mapping(package: CapabilityPackage) -> dict[str, Any]:
    """Render a `CapabilityPackage` back to the mapping shape its file has."""
    raw: dict[str, Any] = {
        "schema_version": package.schema_version,
        "component": {"kind": "capability", "name": package.name, "version": package.version},
    }
    if package.description:
        raw["description"] = package.description
    if package.requires_backbone:
        raw["requires_backbone"] = package.requires_backbone
    if package.requires_capabilities:
        raw["requires_capabilities"] = [
            {"name": dep.name, "version": dep.version}
            | ({OPTIONAL_DEPENDENCY_KEY: True} if dep.optional else {})
            for dep in package.requires_capabilities
        ]
    return raw


def artefact_names(area_dir: Path) -> dict[str, Path]:
    """The skills or agents a folder holds, by name, each with the file that holds it.

    A skill or an agent is a file `<name>.md`, or a folder `<name>/` holding
    `<name>.md` (COR-015). Where a folder holds both forms of one name, the
    first in name order is listed. Empty when the folder is missing.
    """
    found: dict[str, Path] = {}
    if not area_dir.is_dir():
        return found
    for entry in sorted(area_dir.iterdir()):
        if entry.is_file() and entry.suffix == ".md":
            found.setdefault(entry.stem, entry)
        elif entry.is_dir() and (entry / f"{entry.name}.md").is_file():
            found.setdefault(entry.name, entry / f"{entry.name}.md")
    return found


def shipped_capability_names(target_root: Path, source_kit: Path) -> frozenset[str]:
    """The registered ``kit-shipped`` capabilities the running pkit's bundle ships.

    Their artefacts are the release's, as core's are: a collision between two
    artefacts one release ships is the release's to prevent, and no transition
    asks about it (ADR-065 point 6).
    """
    return frozenset(
        name
        for name, origin in installed_capability_origins(target_root).items()
        if origin == KIT_SHIPPED and find_capability_in_source(source_kit, name) is not None
    )


def detect_new_collisions(
    target_root: Path,
    capability_source: CapabilitySource,
    *,
    skipped: Iterable[tuple[str, str]] = (),
    released: Collection[str] = (),
) -> list[CollisionFinding]:
    """The new collisions a capability's target version brings (ADR-065 point 6, COR-017).

    A new collision is a skill or agent name the target version ships, in either
    form (`artefact_names`), that another installed artefact already uses. A name
    the capability's installed copy holds is not new, and neither is one its
    manifest records as skipped (*skipped*): the project already chose.

    The other installed artefacts are the project's own, under
    `.pkit/skills/project/` and `.pkit/agents/project/`, and those of each other
    capability that is neither the release's nor externally sourced: an
    incubated one, or one the methodology no longer ships. So the flow leaves
    out core's artefacts and those of each capability in *released*
    (`shipped_capability_names`), since a clash between two artefacts one
    release ships is the release's to prevent, and a collision with
    externally-sourced content, which surfaces as COR-041 sets. Read-only.
    """
    own = capability_source.name
    installed = target_root / ".pkit" / "capabilities" / own
    already_chosen = set(skipped)
    origins = installed_capability_origins(target_root)
    findings: list[CollisionFinding] = []
    for kind, area in _ARTEFACT_AREAS.items():
        shipped = artefact_names(capability_source.path / area)
        if not shipped:
            continue
        held = artefact_names(installed / area)
        existing = _artefacts_outside_the_release(
            target_root, area, own=own, released=released, origins=origins
        )
        for artefact, source_path in shipped.items():
            if artefact in held or (kind, artefact) in already_chosen:
                continue
            target_path = existing.get(artefact)
            if target_path is not None:
                findings.append(CollisionFinding(kind, artefact, source_path, target_path))
    return findings


def _artefacts_outside_the_release(
    target_root: Path,
    area: str,
    *,
    own: str,
    released: Collection[str],
    origins: Mapping[str, str],
) -> dict[str, Path]:
    """The installed artefacts of one area a capability's new artefact can collide
    with: the project's own first, then each other capability's that is neither the
    release's nor externally sourced (`detect_new_collisions`)."""
    found = dict(artefact_names(target_root / ".pkit" / area / "project"))
    caps_dir = target_root / ".pkit" / "capabilities"
    if not caps_dir.is_dir():
        return found
    for cap in sorted(caps_dir.iterdir()):
        if not cap.is_dir() or cap.name == own or cap.name in released:
            continue
        origin = origins.get(cap.name)
        if origin is not None and origin not in (KIT_SHIPPED, INCUBATED_IN_REPO):
            continue
        for artefact, path in artefact_names(cap / area).items():
            found.setdefault(artefact, path)
    return found


def detect_incubated_collisions(
    target_root: Path,
    capability_source: CapabilitySource,
) -> list[CollisionFinding]:
    """Detect collisions for an incubated (in-repo) register: skip self-collisions.

    An incubated capability's own skills/agents already live in its in-repo
    tree, so `detect_collisions` — which walks every installed capability's
    tree — surfaces them as collisions against themselves. For the register
    path every such self-collision is a false positive: the capability *is*
    its own source, nothing is being copied over it. This filters them out
    by passing the capability's name as `exclude`, so the existing-names walk
    skips the capability's own tree entirely — making detection order-
    independent and semantically correct (a capability cannot shadow itself),
    leaving only genuine collisions against *other* installed content (#225).
    `install` of a capability authored in the methodology's source runs it for
    the same reason: that capability is its own source too (#1107).
    """
    own_dir = target_root / ".pkit" / "capabilities" / capability_source.name
    findings: list[CollisionFinding] = []
    for finding in detect_collisions(
        target_root, capability_source, exclude=capability_source.name
    ):
        # `exclude` above is the primary guard; this post-hoc filter is a
        # harmless belt-and-suspenders against any future self-collision path.
        try:
            finding.target_path.relative_to(own_dir)
        except ValueError:
            findings.append(finding)
    return findings


def refresh_capability(
    target_root: Path,
    capability_source: CapabilitySource,
    *,
    skipped_artifacts: tuple[tuple[str, str], ...] = (),
    dry_run: bool = False,
    record: CapabilityRecord | None = None,
    overridden: Sequence[Path] = (),
) -> Path:
    """Move an installed capability to its source version: a transition of one capability.

    `pkit capabilities upgrade` runs it, after its own step 1: the dependency
    gates and the collision flow, which choose *skipped_artifacts* and the
    project's artefacts an override replaces, *overridden* (ADR-065
    point 4, "A transition of one capability"; COR-010). Sync never does, and
    a transition of the backbone copies through the propagation step and then
    runs `migrate_copied_capability` (ADR-065 points 1 and 4). Its steps:

    1. **The record** is read before anything is written: *record* when the
       caller read it, else here (`read_capability_record`).
    2. **The manifest** still at the capability's root moves under its
       ``project/`` (`move_capability_manifest`), where the copy cannot prune
       it. Where *skipped_artifacts* differ from the skips it records, they are
       recorded there before the copy (`record_skips`), and each artefact in
       *overridden* is removed (`apply_overrides`). So each answer holds when
       a migration stops the refresh: the next one does not ask again, and the
       name it then finds in the installed copy is no longer a collision.
    3. **The copy** replaces the kit-owned part of the installed subtree with
       the source's, leaving out *skipped_artifacts*. It creates no seed path,
       so it stubs no ``project/``. Then `.pkit/.gitignore` is rendered, so a
       migration reads the render of the new version's declarations.
    4. **The migrations** then run, so each reads the files of the version it
       migrates to (COR-010's order), from the version the record names, and
       the manifest is restamped when they finish, with *skipped_artifacts*
       (`migrate_copied_capability`). A capability with no readable version
       runs none of its migrations and is recorded at the source version. A
       migration that exits non-zero raises before the restamp, so the
       manifest still names the version the migrations run from, and the next
       refresh runs them again.

    Requires the capability to be installed. Under *dry_run* it writes
    nothing, and says what it would move and run. Returns the refreshed path.
    Collision detection is its caller's (`detect_new_collisions`).
    """
    name = capability_source.name
    if not is_installed(target_root, name):
        raise click.ClickException(
            f"capability {name!r} is not installed; use 'pkit capabilities install {name}' first."
        )
    dest = target_root / ".pkit" / "capabilities" / name
    # Before the move, the copy and the migrations, which would otherwise write
    # into the source.
    _refuse_copy_onto_itself(capability_source.path, dest)

    if record is None:
        record = read_capability_record(target_root, name)
    move = (
        f"the manifest of capability {name!r}: "
        f"{capability_root_manifest_path(target_root, name).relative_to(target_root)} -> "
        f"{capability_manifest_rel(name)}"
    )
    in_force = replace(record, skipped=tuple(skipped_artifacts))

    if dry_run:
        # Report what would happen without writing.
        if record.at_root:
            click.echo(f"  would move {move}")
        apply_overrides(target_root, overridden, dry_run=True)
        migrate_copied_capability(target_root, capability_source, in_force, dry_run=True)
        return dest

    if move_capability_manifest(target_root, name):
        click.echo(f"  moved {move}")
    if set(in_force.skipped) != set(record.skipped):
        # A capability with no readable version is recorded at the version the
        # copy brings, and none of its migrations runs (ADR-065 point 2).
        version = record.version or capability_source.package.version
        record_skips(target_root, name, in_force.skipped, version=version)
    apply_overrides(target_root, overridden, dry_run=False)

    _copy_capability_tree(capability_source.path, dest, in_force.skipped, stub_project=False)
    from project_kit import visibility

    click.echo(visibility.render_runtime_ignore(target_root))
    # Its migrations, after its copy, then the restamp with the skips in force,
    # keeping the rest of the manifest's state. The registry entry stays as it is.
    migrate_copied_capability(target_root, capability_source, in_force)
    return dest


def copy_shipped_capability(
    target_root: Path,
    capability_source: CapabilitySource,
    skipped_artifacts: tuple[tuple[str, str], ...],
) -> Path:
    """Copy a shipped capability's files over its installed copy, and nothing else.

    The propagation step's copy of one capability (ADR-065 point 1), for sync
    and for a transition alike: the source subtree replaces the kit-owned part
    of the installed one, leaving out the artefacts *skipped_artifacts* names.
    It runs no migration, writes no manifest, and creates no seed path, so the
    capability's ``project/`` is neither touched nor stubbed. Its caller has
    already read the capability's record, and a transition has moved a root
    manifest under ``project/``, where the copy cannot prune it.
    """
    dest = target_root / ".pkit" / "capabilities" / capability_source.name
    _refuse_copy_onto_itself(capability_source.path, dest)
    _copy_capability_tree(capability_source.path, dest, skipped_artifacts, stub_project=False)
    return dest


def migrate_copied_capability(
    target_root: Path,
    capability_source: CapabilitySource,
    record: CapabilityRecord,
    *,
    dry_run: bool = False,
) -> None:
    """Run a copied capability's migrations, then restamp its manifest (ADR-065 point 4).

    A transition calls it after its copy, of the backbone in its step 6 and of
    one capability in `refresh_capability`, so each migration
    reads the files of the version it migrates to, as COR-010's order sets. The
    window runs from the version *record* names to the version the copy ships,
    read from the bundle. A capability with no readable version runs none of
    its migrations: its history is unknown, and the replay is the backbone's
    alone (COR-059 point 6). It is recorded at the bundled version, and said so.

    The restamp, under the capability's ``project/``, records the bundled
    version, the timestamp and the range, and the skips *record* holds, and
    keeps the rest of ``backend_state``. A migration that exits non-zero raises
    before it, so the manifest still names the version the migrations run from.
    """
    name = capability_source.name
    bundled = capability_source.package.version
    recorded = _release_version(record.version)
    if recorded is not None:
        if dry_run:
            _report_pending_migrations(capability_source, recorded, dry_run=True)
        else:
            _run_capability_migrations(target_root, capability_source, recorded)
    if not dry_run:
        _stamp_component_manifest(target_root, capability_source, record.skipped, restamp=True)
    verb = "would record" if dry_run else "recorded"
    origin = (
        f"from {record.version}"
        if recorded is not None
        else "no recorded version before, so none of its migrations runs"
    )
    click.echo(f"    {verb:<12} capability {name!r} at {bundled} ({origin})")


def _release_version(text: str | None) -> str | None:
    """*text* as the `X.Y.Z` a migration window reads, or None when it is no version."""
    if not text:
        return None
    try:
        parsed = Version(text)
    except InvalidVersion:
        return None
    return f"{parsed.major}.{parsed.minor}.{parsed.micro}"


def _read_installed_capability_version(target_root: Path, name: str) -> str | None:
    """Read the installed version of a capability.

    A kit-shipped capability records its installed version in its manifest,
    written at install time (`read_capability_record` says which manifest is
    read). An incubated (in-repo) capability has no such
    kit-written manifest — its subtree is entirely adopter-owned (COR-031
    D2), so no lifecycle state is stamped into it — and its version of
    record is its own authored ``package.yaml``. This reads the
    manifest first, then falls back to the authored
    ``package.yaml`` so an incubated capability still reports a version
    for dependency-gating (COR-031 D1: an incubated capability participates
    in dependency resolution identically to a kit-shipped one). The same
    fallback is a safe last resort for a kit-shipped capability whose
    manifest is missing or malformed.

    Returns None when neither source yields a version — the caller treats
    that as "no migrations to run" / "version unreadable" rather than
    failing.
    """
    return read_capability_record(target_root, name).version


def _pending_migration_scripts(
    capability_source: CapabilitySource,
    installed_version: str | None,
) -> list[Path]:
    """Collect scripts under `<source>/migrations/<X.Y.0>/` whose minor is in (installed, source].

    Delegates to `migrations.pending_migration_scripts`. Kept as a
    capability-specific wrapper so tests have a stable API and the
    capability-aware caller doesn't need to know about the
    migrations-root path layout.
    """
    return pending_migration_scripts(
        capability_source.path / "migrations",
        installed_version,
        capability_source.package.version,
    )


def _run_capability_migrations(
    target_root: Path,
    capability_source: CapabilitySource,
    installed_version: str | None,
) -> None:
    """Execute pending migrations for the capability. Halts on first failure."""
    scripts = _pending_migration_scripts(capability_source, installed_version)
    if not scripts:
        return
    click.echo(
        f"  running {len(scripts)} migration(s) for capability "
        f"{capability_source.name!r} "
        f"({installed_version or 'unknown'} -> v{capability_source.package.version})"
    )
    execute_migration_scripts(
        scripts,
        target_root,
        label=f"capability {capability_source.name!r}",
        label_rel_to=capability_source.path,
    )


def _report_pending_migrations(
    capability_source: CapabilitySource,
    installed_version: str | None,
    *,
    dry_run: bool,
) -> None:
    """Print what migrations would run, without executing."""
    scripts = _pending_migration_scripts(capability_source, installed_version)
    report_pending_migrations(
        scripts,
        label=f"capability {capability_source.name!r}",
        installed_version=installed_version,
        target_version=capability_source.package.version,
        dry_run=dry_run,
        label_rel_to=capability_source.path,
    )


@dataclass(frozen=True)
class UninstallOutcome:
    """What an uninstall did, so the CLI can report it accurately (COR-031 D4).

    Origin governs whether the authored subtree is deleted:
    - a ``kit-shipped`` capability's subtree is a disposable copy of kit
      source, so uninstall deletes it (``files_deleted=True``);
    - an ``incubated-in-repo`` capability's subtree is the adopter's *only*
      copy of authored work, so uninstall unregisters in place and leaves
      the files (``files_deleted=False``), unless the caller opts in to a
      purge.

    Where the subtree is the capability's source (``in_source``, #1107) it is
    kept whatever the origin.

    A kept subtree is undeployed through each adapter's undeploy primitive;
    ``adapters_without_undeploy`` names the adapters that ship none, whose
    harness still carries the capability (each is also reported as it runs).
    """

    cap_dir: Path  # the capability's subtree path (deleted or kept)
    origin: str  # kit-shipped | incubated-in-repo
    files_deleted: bool  # whether the subtree was (or would be) removed
    in_source: bool = False  # the subtree is the capability's source (`authored_in_source`)
    adapters_without_undeploy: tuple[str, ...] = ()  # adapters that could not undeploy it


def uninstall_capability(
    target_root: Path,
    name: str,
    *,
    source_kit: Path | None = None,
    purge: bool = False,
    dry_run: bool = False,
) -> UninstallOutcome:
    """Unregister a capability, deleting its subtree only when origin permits (COR-031 D4).

    Caller is responsible for checking references (the safety check) and
    confirming with the user before invoking. This function performs the
    mechanical unregister (+ conditional removal) only.

    Origin-aware removal:
    - **kit-shipped** — the subtree is a disposable copy of kit source;
      delete it and unregister. The caller re-runs deploy, whose
      stale-removal drops the harness entries of the deleted source.
    - **incubated-in-repo** — the subtree is the adopter's only copy of
      authored work; *unregister in place* and leave the files on disk
      (the destroy-adopter-work hazard COR-031 exists to prevent). Its
      deployed skills and agents are removed through each installed
      adapter's undeploy primitive (``install.undeploy_capability_from_adapters``),
      since a deploy re-run cannot see a surviving subtree as gone.

    ``purge=True`` is the explicit opt-in that deletes an incubated
    capability's files anyway (the caller must confirm first, honouring the
    pause-before-destructive-ops discipline). It has no effect on a
    kit-shipped capability, which always deletes.

    Neither applies where the subtree is the capability's source — inside
    *source_kit*, the tree the running code resolves (`authored_in_source`;
    the methodology's source repository under its own code). It is never a
    copy, so it is unregistered in place whatever the origin, and ``purge`` is
    refused (#1107). *source_kit* defaults to that tree
    (`install.find_source_kit`), so the guard holds for every caller.

    Returns an ``UninstallOutcome`` describing what was (or would be) done.
    """
    if not is_installed(target_root, name):
        raise click.ClickException(f"capability {name!r} is not installed.")

    if source_kit is None:
        from project_kit.install import find_source_kit

        source_kit = find_source_kit()
    in_source = authored_in_source(target_root, source_kit, name)
    cap_dir = target_root / ".pkit" / "capabilities" / name
    if in_source and purge:
        raise click.ClickException(
            f"refusing to purge {cap_dir}: it is the capability's source, and uninstall "
            "never deletes a capability's source (ADR-059). Nothing was written."
        )

    origin = read_capability_origin(target_root, name)
    # An incubated capability keeps its files unless the caller purges; a
    # kit-shipped one always deletes its disposable copy; the source is kept.
    delete_files = not in_source and (origin != ORIGIN_INCUBATED_IN_REPO or purge)

    if dry_run:
        return UninstallOutcome(
            cap_dir=cap_dir, origin=origin, files_deleted=delete_files, in_source=in_source
        )

    adapters_without_undeploy: tuple[str, ...] = ()
    if delete_files:
        if cap_dir.is_dir():
            shutil.rmtree(cap_dir)
        # The subtree is gone, so the deploy primitives' own stale-removal
        # drops the harness entries on the caller's deploy re-run.
    else:
        # Kept in place (incubated, or the source): the subtree survives, so a
        # deploy re-run, keyed on whether the source file exists, would not drop
        # the capability's harness entries. Each adapter's undeploy primitive
        # does (COR-031 D4: uninstall drops them though the files stay). It runs
        # before the unregister, so a failing adapter leaves the capability
        # registered and the uninstall re-runnable.
        from project_kit import install

        ctx = install.InstallContext(target_root=target_root, source_kit=source_kit, dry_run=False)
        adapters_without_undeploy = install.undeploy_capability_from_adapters(ctx, name)

    _unregister_from_backbone_manifest(target_root, name)
    return UninstallOutcome(
        cap_dir=cap_dir,
        origin=origin,
        files_deleted=delete_files,
        in_source=in_source,
        adapters_without_undeploy=adapters_without_undeploy,
    )


def find_references(target_root: Path, capability_name: str) -> list[tuple[Path, str]]:
    """Find references to the capability in the adopter's tree.

    Two kinds of references count:
    - Citations: `[<name>:...]` tokens in .md / .yaml files.
    - Path references: literal `.pkit/capabilities/<name>/` strings in
      any text file (scripts, configs, prose).

    Returns a list of (file_path, snippet) pairs describing each match.
    Scans the project tree but skips `.pkit/capabilities/<name>/` itself
    (the capability's own files don't count as "references to it"), and
    skips `.git/`, `.venv/`, `node_modules/`, etc.
    """
    findings: list[tuple[Path, str]] = []
    citation_re = re.compile(rf"\[{re.escape(capability_name)}:[^\]]+\]")
    path_re = re.compile(rf"\.pkit/capabilities/{re.escape(capability_name)}/")
    self_path = (target_root / ".pkit" / "capabilities" / capability_name).resolve()

    ignored_dirs = {".git", ".venv", "node_modules", "__pycache__", ".pytest_cache"}

    for path in target_root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in ignored_dirs for part in path.parts):
            continue
        # Skip kit-propagated content (the kit's own examples or content
        # in adopter trees that came from sync, not from adopter authoring).
        # The adopter-authored areas are <area>/project/ paths plus
        # everything outside `.pkit/` entirely.
        if _is_kit_propagated_path(target_root, path):
            continue
        # Skip the capability's own files.
        try:
            if self_path in path.resolve().parents or path.resolve() == self_path:
                continue
        except OSError:
            continue
        if path.suffix not in {".md", ".yaml", ".yml", ".py", ".sh", ".txt", ".rst"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for match in citation_re.finditer(text):
            findings.append((path, match.group(0)))
        for match in path_re.finditer(text):
            findings.append((path, match.group(0)))
    return findings


def _is_kit_propagated_path(target_root: Path, path: Path) -> bool:
    """True if the path is kit-shipped content (not adopter-authored).

    Adopter-authored content lives at two depths under `.pkit/`:

    - Area-level:       `.pkit/<area>/project/`          (parts[2] == "project")
    - Capability-level: `.pkit/capabilities/<name>/project/` (parts[3] == "project")

    Everything else under `.pkit/` (core/, adapters/, cli/, lifecycle/,
    etc.) is kit-shipped — references inside it are kit's own example
    prose, not adopter references.
    """
    try:
        rel = path.relative_to(target_root)
    except ValueError:
        return False
    parts = rel.parts
    if not parts or parts[0] != ".pkit":
        return False
    # Inside .pkit/. Adopter content lives at .pkit/<area>/project/.
    # Anything else under .pkit/ is kit-shipped.
    if len(parts) >= 3 and parts[2] == "project":
        return False
    # Capability-level adopter content lives at .pkit/capabilities/<name>/project/.
    if len(parts) >= 4 and parts[1] == "capabilities" and parts[3] == "project":
        return False
    return True


# ---------------------------------------------------------------- internals


def _is_valid_name(name: str) -> bool:
    return bool(_NAME_RE.match(name))


def _refuse_unregistrable(target_root: Path, name: str) -> None:
    """Refuse a reserved name, a name an adapter holds, or an already-registered
    capability.

    The pre-flight every path that registers a capability runs first:
    `install_capability`, `register_incubated_capability` and
    `register_capability_in_source`.
    """
    refuse_reserved_capability_name(name)
    refuse_name_held_by_other_kind(target_root, "capability", name)
    if is_installed(target_root, name):
        raise click.ClickException(
            f"capability {name!r} is already installed. "
            f"Use 'pkit capabilities upgrade {name}' to refresh."
        )


def _refuse_copy_onto_itself(source: Path, dest: Path) -> None:
    """Refuse a capability copy whose source and destination are one tree (#1107).

    In the methodology's source repository run by its own code, the tree a
    kit-shipped capability is copied from is its destination
    (`authored_in_source`). A copy there fails on the first file copied onto
    itself — after the migrations have run against the source — and, with an
    artefact skipped, prunes that artefact from the source. The CLI takes the
    in-place paths there; this keeps any other caller of `install_capability`
    or `refresh_capability` from reaching the copy. Either tree inside the
    other counts as one: copying would write into the tree being read.
    """
    source_resolved, dest_resolved = source.resolve(), dest.resolve()
    if source_resolved.is_relative_to(dest_resolved) or dest_resolved.is_relative_to(
        source_resolved
    ):
        raise click.ClickException(
            f"refusing to copy the capability tree at {source} onto itself: the "
            f"destination {dest} is the same tree, where the capability is authored "
            "(ADR-059). Nothing was written."
        )


def _read_package_yaml(path: Path) -> CapabilityPackage | None:
    """Read a capability's package.yaml. Returns None on parse failure or schema mismatch."""
    try:
        raw = _yaml.load(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(raw, dict):
        return None
    component = raw.get("component") or {}
    if not isinstance(component, dict):
        return None
    if component.get("kind") != "capability":
        return None
    name = component.get("name")
    version = component.get("version")
    if not isinstance(name, str) or not isinstance(version, str):
        return None
    description = raw.get("description", "")
    requires_backbone = raw.get("requires_backbone", "")
    requires_capabilities = _parse_requires_capabilities(raw.get("requires_capabilities"))
    return CapabilityPackage(
        name=name,
        version=version,
        description=str(description),
        requires_backbone=str(requires_backbone),
        requires_capabilities=requires_capabilities,
        schema_version=int(raw.get("schema_version", 1)),
    )


def _parse_requires_capabilities(
    raw: object,
) -> tuple[CapabilityDependency, ...]:
    """Parse the ``requires_capabilities`` list from a package.yaml value.

    Accepts a list of ``{name: str, version: str}`` dicts, each optionally
    marked ``optional: true`` (``is_optional_dependency``). Silently
    skips entries that are malformed — a capability with a broken dep
    declaration is still usable; the install gate will simply not enforce
    the malformed entry (a future schema validation pass can surface it).
    Absence of the field (``None``) returns an empty tuple.
    """
    if raw is None:
        return ()
    if not isinstance(raw, list):
        return ()
    out: list[CapabilityDependency] = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        dep_name = entry.get("name")
        dep_version = entry.get("version")
        if not isinstance(dep_name, str) or not isinstance(dep_version, str):
            continue
        if not dep_name or not dep_version:
            continue
        out.append(
            CapabilityDependency(
                name=dep_name,
                version=dep_version,
                optional=is_optional_dependency(cast("Mapping[str, Any]", entry)),
            )
        )
    return tuple(out)


def _collect_existing_artifact_names(
    target_root: Path, area: str, exclude: str | None = None
) -> dict[str, Path]:
    """Gather all installed artifact names (skills or agents) keyed by name.

    Walks the area's `core/` + `project/` plus every installed
    capability's `<area>/` directory. Returns name → path mapping.

    `exclude` names a capability directory to skip in the installed-
    capabilities walk. An incubated capability's own tree lives under
    `.pkit/capabilities/<name>/` too, so without this it could shadow
    another capability's same-named artifact (last-writer-wins over an
    unsorted `iterdir()`) and mask a genuine collision (#225).
    """
    out: dict[str, Path] = {}
    # Area core + project
    for ns in ("core", "project"):
        ns_dir = target_root / ".pkit" / area / ns
        if not ns_dir.is_dir():
            continue
        for entry in ns_dir.iterdir():
            if entry.is_file() and entry.suffix == ".md":
                out[entry.stem] = entry
            elif entry.is_dir():
                inner = entry / f"{entry.name}.md"
                if inner.is_file():
                    out[entry.name] = inner
    # Installed capabilities
    caps_dir = target_root / ".pkit" / "capabilities"
    if caps_dir.is_dir():
        for cap in caps_dir.iterdir():
            if not cap.is_dir():
                continue
            if exclude is not None and cap.name == exclude:
                continue
            cap_area = cap / area
            if not cap_area.is_dir():
                continue
            for entry in cap_area.iterdir():
                if entry.is_file() and entry.suffix == ".md":
                    out[entry.stem] = entry
    return out


def _capability_owned(rel: PurePath) -> bool:
    """Ownership predicate for a capability tree (relative to the capability root).

    The capability's **top-level** ``project/`` subtree is adopter-owned (the
    no-shared-files invariant, COR-001) — positional, matching the
    ``.pkit/<area>/project/`` convention `_is_kit_propagated_path` enforces.
    A ``project`` segment nested below a kit-owned subdir is *not* adopter-
    owned (it refreshes), by the same positional rule.
    """
    return bool(rel.parts) and rel.parts[0] == _CAPABILITY_PROJECT_SUBTREE


def _copy_capability_tree(
    source: Path,
    dest: Path,
    skipped_artifacts: tuple[tuple[str, str], ...],
    *,
    stub_project: bool = True,
) -> None:
    """Refresh capability content into dest, omitting any skipped artifacts.

    Routes through the shared ownership-aware tree-refresh primitive
    (`treecopy.refresh_owned_tree`), so kit-owned content refreshes wholesale
    (new files appear, removed files disappear, modified files update) while
    the adopter's own ``project/`` tree is never overwritten or removed. This
    is the same mechanic the area/adapter sync uses — reimplementing it here
    is what caused the #332 clobber.

    ``seed_owned=False`` is the fix for #812: the source's ``project/`` subtree
    is the SOURCE PROJECT's instance data, not a neutral template, so seeding
    it handed one project's state to every adopter. It shipped project-kit's
    own default-agent activation (switching on an agent DEC-030 promises stays
    off), its bootstrap stamp (which a fresh adopter's setup gate then read as
    completion), its issue-lifecycle journals (keyed by issue number, so an
    adopter's issue #446 inherited project-kit's #446 history), and its config
    and workstream taxonomy. The area install path never had this defect — it
    skips the source ``project/`` tree and stubs an empty directory instead;
    capabilities were simply never brought in line.

    Seeding a *neutral starter* config is a separate question and deliberately
    not done here: that is new install behaviour and needs its own record.

    *stub_project* creates the capability's ``project/`` folder, as an install
    and ``pkit capabilities upgrade`` do. The propagation step passes False: the
    folder is a seed path, which sync never creates and a transition creates
    where it is missing (ADR-065 point 11).
    """
    # Skipped skills/agents become generic relative-path exclusions for the
    # primitive (it knows nothing of "skipped artifacts"), in either form
    # (COR-015): the file `<name>.md`, and every file of the folder `<name>/`.
    # Decisions and other artifacts are not skip-eligible (they don't collide
    # by name).
    skipped_folders = [
        source / _ARTEFACT_AREAS[kind] / name
        for kind, name in skipped_artifacts
        if kind in _ARTEFACT_AREAS
    ]
    exclude = frozenset(
        {
            f"{_ARTEFACT_AREAS[kind]}/{name}.md"
            for kind, name in skipped_artifacts
            if kind in _ARTEFACT_AREAS
        }
        | {
            path.relative_to(source).as_posix()
            for folder in skipped_folders
            if folder.is_dir()
            for path in folder.rglob("*")
            if path.is_file()
        }
    )
    treecopy.refresh_owned_tree(
        source,
        dest,
        is_owned=_capability_owned,
        exclude=exclude,
        seed_owned=False,
    )
    # The primitive reproduces every source folder, so a skipped folder-form
    # artefact leaves its folders behind, empty: remove each one.
    for folder in skipped_folders:
        copied = dest / folder.relative_to(source)
        if copied.is_dir() and not any(p.is_file() for p in copied.rglob("*")):
            shutil.rmtree(copied)
    if not stub_project:
        return
    # Stub the adopter-owned tree so the directory exists to be written into,
    # mirroring the area install path's `_touch(project_dst / ".gitkeep")`.
    # Only the top level: nested structure is the adopter's to create as they
    # use it, and materialising the source's nested dirs would leak its shape.
    project_dir = dest / _CAPABILITY_PROJECT_SUBTREE
    project_dir.mkdir(parents=True, exist_ok=True)
    keep = project_dir / ".gitkeep"
    if not any(project_dir.iterdir()):
        keep.touch()


def _register_in_backbone_manifest(
    target_root: Path, name: str, *, origin: str = KIT_SHIPPED
) -> None:
    """Add a `kind: capability` entry to the backbone manifest's components list.

    ``origin`` records where the capability came from (COR-031 D2) in
    lifecycle-owned install-state. Defaults to ``kit-shipped``; the
    incubated-in-repo register path passes ``INCUBATED_IN_REPO``.

    The entry names the capability's manifest under its ``project/``
    (``manifest.capability_manifest_rel``), whatever the origin. Only a
    kit-shipped install writes a manifest there.
    """
    backbone = read_backbone_manifest(target_root)
    if backbone is None:
        raise click.ClickException(".pkit/manifest.yaml is missing. Run 'pkit init' first.")
    entry = ComponentRegistryEntry(
        kind="capability", name=name, manifest=capability_manifest_rel(name), origin=origin
    )
    # Don't duplicate (caller should check, but defensive).
    backbone.components = [
        c for c in backbone.components if not (c.kind == "capability" and c.name == name)
    ]
    backbone.components.append(entry)
    write_backbone_manifest(target_root, backbone)


def set_capability_origin(target_root: Path, name: str, origin: str) -> bool:
    """Set a registered capability's ``origin`` in place (COR-031 D2).

    Thin wrapper over the manifest helper, kept on this module so callers reach
    origin state through the capabilities API alongside ``read_capability_origin``
    and ``installed_capability_origins``. Returns ``True`` when the existing
    registry entry's origin changed, ``False`` when the capability is not
    registered or already holds that origin.
    """
    return _manifest_set_capability_origin(target_root, name, origin)


def _unregister_from_backbone_manifest(target_root: Path, name: str) -> None:
    """Remove the `kind: capability, name: X` entry from the backbone manifest."""
    backbone = read_backbone_manifest(target_root)
    if backbone is None:
        return
    backbone.components = [
        c for c in backbone.components if not (c.kind == "capability" and c.name == name)
    ]
    write_backbone_manifest(target_root, backbone)


def _stamp_component_manifest(
    target_root: Path,
    capability_source: CapabilitySource,
    skipped_artifacts: tuple[tuple[str, str], ...],
    *,
    restamp: bool = False,
) -> None:
    """Write the capability's manifest under its ``project/`` (ADR-065 point 2).

    Records the version, the install timestamp and the range of
    *capability_source*, and the skips in force in ``backend_state.skipped``,
    for the next refresh to read back (`read_prior_skipped_artifacts`), and
    points the registry entry at the path written.

    A *restamp*, after a refresh's migrations and copy, keeps every key of the
    manifest's ``backend_state`` but the skips, which *skipped_artifacts*
    replaces. The refresh moved the manifest under ``project/`` before its
    migrations, so it reads it there, with what the migrations wrote. A manifest
    there that does not read as a mapping, such as one left with merge-conflict
    markers, is replaced by a new one, as an install writes.

    A manifest at the capability's root here came with the copy, from the
    source: the project's own moved before the copy, or there was none. It is
    removed, since readers read a root manifest first.
    """
    name = capability_source.name
    capability_root_manifest_path(target_root, name).unlink(missing_ok=True)
    path = capability_manifest_path(target_root, name)
    prior = _load_mapping(path) if restamp and path.is_file() else None
    if prior is None and path.is_file():
        if restamp:
            # Say so: what it held, such as both sides of a merge conflict, is git's to recover.
            click.echo(
                f"  replaced the manifest of capability {name!r}: "
                f"{capability_manifest_rel(name)} did not parse"
            )
        path.unlink()
    state = prior.get("backend_state") if prior is not None else None
    backend_state: dict[str, Any] = {
        key: value
        for key, value in (cast("dict[str, Any]", state) if isinstance(state, dict) else {}).items()
        if key != SKIPPED_KEY
    }
    if skipped_artifacts:
        backend_state[SKIPPED_KEY] = [{"kind": k, "name": n} for (k, n) in skipped_artifacts]
    manifest = ComponentManifest(
        kind="capability",
        name=name,
        version=capability_source.package.version,
        installed_at=_dt.datetime.now(_dt.UTC).isoformat(),
        requires_backbone=capability_source.package.requires_backbone,
        backend_state=backend_state,
    )
    write_component_manifest(path, manifest)
    set_component_manifest_path(target_root, "capability", name, capability_manifest_rel(name))
