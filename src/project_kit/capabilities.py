"""Capability install / uninstall / list operations (per COR-017).

A capability is a self-contained opt-in unit of methodology that lives
at `.pkit/capabilities/<name>/`. Adopters install per project via
`pkit capabilities install <name>`; uninstall via
`pkit capabilities uninstall <name>`. Capabilities slot into the kit's existing component
registry (per COR-010) alongside adapters.

This module covers the deterministic mechanics. Interactive collision
resolution (override / skip / inspect) lives in the CLI layer where
Click prompts are available.

Capability dependencies (COR-030): a capability may declare
``requires_capabilities`` in its ``package.yaml`` — an optional list of
``{name, version}`` entries, each expressing a semver range that a
dependency capability's installed version must satisfy. The install
pre-flight, both upgrade entry points, and the uninstall gate enforce
this contract. See ``check_capability_dependencies``.
"""

from __future__ import annotations

import datetime as _dt
import io
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path, PurePath
from typing import Any, cast

import click
from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.version import InvalidVersion, Version
from ruamel.yaml import YAML

from project_kit import treecopy
from project_kit.manifest import (
    BackboneManifest,
    ComponentManifest,
    ComponentRegistryEntry,
    read_backbone_manifest,
    write_backbone_manifest,
    write_component_manifest,
)
from project_kit.migrations import (
    execute_migration_scripts,
    pending_migration_scripts,
    report_pending_migrations,
)


_NAME_RE = re.compile(r"^[a-z][a-z0-9-]*[a-z0-9]$|^[a-z]$")
_yaml = YAML(typ="safe")

# A capability's top-level `project/` subtree is adopter-owned (the
# no-shared-files invariant, COR-001): seeded at install, never overwritten
# or removed on refresh. See `_copy_capability_tree`.
_CAPABILITY_PROJECT_SUBTREE = "project"


@dataclass(frozen=True)
class CapabilityDependency:
    """One entry from the ``requires_capabilities`` list in a ``package.yaml``."""

    name: str     # capability name (e.g. "evidence")
    version: str  # semver range string (e.g. ">=0.2.0,<1.0.0")


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
    return _resolve_capability_dir(
        target_root / ".pkit" / "capabilities" / name, name
    )


# Which source a caller wants when a name resolves in more than one place.
CapabilityOrigin = str  # "kit-shipped" | "incubated-in-repo"

KIT_SHIPPED: CapabilityOrigin = "kit-shipped"
INCUBATED_IN_REPO: CapabilityOrigin = "incubated-in-repo"


@dataclass(frozen=True)
class ResolvedCapability:
    """The outcome of resolving a capability name across both possible sources.

    Carries the chosen source plus enough context for the caller to surface
    a both-present collision (COR-031's boundary case: "surface the collision
    rather than silently skip it") instead of one source silently shadowing
    the other.
    """

    source: CapabilitySource     # the selected source (per `prefer`)
    origin: CapabilityOrigin     # which tree the selected source came from
    in_kit_source: bool          # the name also resolved in the kit source
    in_repo: bool                # the name also resolved in the adopter's repo


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
        installed = [
            c.name for c in backbone.components if c.kind == "capability"
        ]
    installed.sort()
    return available, installed


def is_installed(target_root: Path, name: str) -> bool:
    """True if the named capability is registered in the adopter's backbone manifest."""
    backbone = read_backbone_manifest(target_root)
    if backbone is None:
        return False
    return any(
        c.kind == "capability" and c.name == name for c in backbone.components
    )


def get_installed_capability_version(target_root: Path, name: str) -> str | None:
    """Return the installed version of a capability, or None if not installed / unreadable.

    Reads the per-component manifest at
    ``.pkit/capabilities/<name>/manifest.yaml``. This is the public
    counterpart of the private ``_read_installed_capability_version``
    used internally by ``refresh_capability``; exposing it lets the
    upgrade layer query installed versions without importing private
    internals.
    """
    return _read_installed_capability_version(target_root, name)


@dataclass(frozen=True)
class CapabilityDependencyConflict:
    """One failing dependency found during the pre-flight check (COR-030)."""

    dep_name: str           # the dependency capability's name
    dep_version_range: str  # the declared range (e.g. ">=0.2.0,<1.0.0")
    installed_version: str | None  # None means not installed at all
    reason: str             # "absent" or "out-of-range"


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
    - If the dependency is not installed → conflict with reason "absent".
    - If the dependency is installed but its version does not satisfy the
      declared semver range → conflict with reason "out-of-range".
    - If the range string is invalid (unparseable) → silently skip (the
      package.yaml is malformed; the gate can only work with valid ranges).

    Returns a list of conflicts; empty means all requirements satisfied.

    Reuses ``is_installed`` and ``get_installed_capability_version`` (this
    module) for the installed-state side, and the ``packaging`` library
    directly for range evaluation (the same library ``upgrade.py`` uses
    for backbone-compatibility resolution).
    """
    if not requires_capabilities:
        return []

    conflicts: list[CapabilityDependencyConflict] = []
    for dep in requires_capabilities:
        if not is_installed(target_root, dep.name):
            conflicts.append(CapabilityDependencyConflict(
                dep_name=dep.name,
                dep_version_range=dep.version,
                installed_version=None,
                reason="absent",
            ))
            continue

        installed_version = get_installed_capability_version(target_root, dep.name)
        if installed_version is None:
            # Installed but version unreadable — treat as a soft miss
            # rather than blocking: the manifest is the adopter's own
            # record and unreadable manifests are already a degraded state.
            continue

        try:
            spec = SpecifierSet(dep.version)
            ver = Version(installed_version)
        except (InvalidSpecifier, InvalidVersion):
            # Malformed range or version string — skip; can't evaluate.
            continue

        if ver not in spec:
            conflicts.append(CapabilityDependencyConflict(
                dep_name=dep.name,
                dep_version_range=dep.version,
                installed_version=installed_version,
                reason="out-of-range",
            ))

    return conflicts


def find_declared_dependents(target_root: Path, dep_name: str) -> list[str]:
    """Find all installed capabilities that declare *dep_name* in their requires_capabilities.

    Used by the uninstall gate (COR-030) to refuse removal when another
    installed capability depends on the target. Walks the backbone
    manifest's component registry, filters to capabilities, and reads
    each one's per-component manifest + installed package.yaml to
    extract ``requires_capabilities``.

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
        pkg_yaml_path = (
            target_root / ".pkit" / "capabilities" / entry.name / "package.yaml"
        )
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
) -> list[CollisionFinding]:
    """Find naming collisions between a capability's artifacts and already-installed content.

    Today checks: skills + agents. Capability decisions are namespaced
    by the capability's directory name, so they cannot collide.
    """
    findings: list[CollisionFinding] = []
    # Skills collision: walk capability's skills/ and check against existing skills.
    cap_skills = capability_source.path / "skills"
    if cap_skills.is_dir():
        existing_skill_names = _collect_existing_artifact_names(
            target_root, "skills"
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
            target_root, "agents"
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
    adopter — caller must check first via `is_installed`.
    """
    if is_installed(target_root, capability_source.name):
        raise click.ClickException(
            f"capability {capability_source.name!r} is already installed. "
            f"Use 'pkit capabilities upgrade {capability_source.name}' to refresh."
        )

    dest = target_root / ".pkit" / "capabilities" / capability_source.name
    if dry_run:
        return dest

    # Copy the subtree, omitting any skipped artifacts.
    _copy_capability_tree(capability_source.path, dest, skipped_artifacts)

    # Register in the backbone manifest.
    _register_in_backbone_manifest(target_root, capability_source.name)

    # Stamp per-component manifest with version + install timestamp + skip state.
    _stamp_component_manifest(target_root, capability_source, skipped_artifacts)

    return dest


def read_prior_skipped_artifacts(
    target_root: Path, capability_name: str
) -> tuple[tuple[str, str], ...]:
    """Re-read the capability's per-component manifest to recover skip state.

    Returns an empty tuple when no manifest exists or it's malformed —
    the worst case is the next refresh copies the previously-skipped
    file, which the adopter can re-skip on the next install with the
    interactive resolver if needed.
    """
    manifest_path = (
        target_root
        / ".pkit"
        / "capabilities"
        / capability_name
        / "component-manifest.yaml"
    )
    if not manifest_path.is_file():
        return ()
    try:
        raw = _yaml.load(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return ()
    if not isinstance(raw, dict):
        return ()
    skipped = raw.get("skipped_artifacts")
    if not isinstance(skipped, list):
        return ()
    out: list[tuple[str, str]] = []
    for item in skipped:
        if isinstance(item, dict):
            kind = item.get("kind")
            name = item.get("name")
            if isinstance(kind, str) and isinstance(name, str):
                out.append((kind, name))
    return tuple(out)


def detect_upgrade_collisions(
    target_root: Path,
    capability_source: CapabilitySource,
) -> list[CollisionFinding]:
    """Detect collisions for an upgrade: skip self-collisions per COR-017.

    `detect_collisions` walks every installed capability, so the
    in-place currently-installed copy of the upgrading capability
    surfaces as a collision against itself. For upgrade, every such
    self-collision is a false positive — those files will be replaced
    in-place by `refresh_capability`. This filters them out by checking
    whether the colliding target lives under the upgrading capability's
    own installed tree.
    """
    installed_dir = target_root / ".pkit" / "capabilities" / capability_source.name
    findings: list[CollisionFinding] = []
    for finding in detect_collisions(target_root, capability_source):
        try:
            finding.target_path.relative_to(installed_dir)
        except ValueError:
            findings.append(finding)
    return findings


def refresh_capability(
    target_root: Path,
    capability_source: CapabilitySource,
    *,
    skipped_artifacts: tuple[tuple[str, str], ...] = (),
    dry_run: bool = False,
) -> Path:
    """Refresh an already-installed capability in place from source (per COR-017).

    Differs from `install_capability` in three ways:
    - Requires the capability to already be installed (raises if not).
    - Re-copies the source subtree wholesale: new files appear, removed
      files disappear, modified files update.
    - Preserves `skipped_artifacts` semantics: caller should pass the
      skip state recovered from the prior install's component-manifest
      so previously-skipped files stay absent.

    Migrations are run BEFORE the file refresh (per COR-010's resource-
    lifecycle pattern). For each minor version in the interval
    (installed, source] the matching `<source>/migrations/<X.Y.0>/*.sh`
    scripts are executed against the adopter root. Each script gets
    `ROOT=<target_root>` in its environment and runs from `target_root`
    as cwd. A non-zero exit halts the refresh.

    Returns the refreshed path. Does NOT do collision detection — sync's
    auto-upgrade is opt-out at install time, not opt-in at refresh time.
    A separate `pkit capabilities upgrade X --interactive` command is the
    interactive surface (per COR-017's "new collision during upgrade"
    semantics); that command can call detect_collisions() before this.
    """
    if not is_installed(target_root, capability_source.name):
        raise click.ClickException(
            f"capability {capability_source.name!r} is not installed; "
            f"use 'pkit capabilities install {capability_source.name}' first."
        )
    dest = target_root / ".pkit" / "capabilities" / capability_source.name

    installed_version = _read_installed_capability_version(target_root, capability_source.name)

    if dry_run:
        # Report what would happen without writing.
        _report_pending_migrations(
            capability_source, installed_version, dry_run=True
        )
        return dest

    # Run migrations first so adopter state migrates before the new
    # capability files arrive. If a script fails, halt — the file
    # refresh is skipped to keep state consistent.
    _run_capability_migrations(
        target_root, capability_source, installed_version
    )

    _copy_capability_tree(capability_source.path, dest, skipped_artifacts)
    # Re-stamp the per-component manifest with the new version + install
    # timestamp. Backbone manifest registration stays as-is (the
    # capability was already registered at the original install).
    _stamp_component_manifest(target_root, capability_source, skipped_artifacts)
    return dest


def _read_installed_capability_version(target_root: Path, name: str) -> str | None:
    """Read the installed version recorded in the capability's per-component manifest.

    Returns None when the manifest is absent or malformed — the caller
    treats that as "no migrations to run" rather than failing.
    """
    manifest_path = (
        target_root / ".pkit" / "capabilities" / name / "manifest.yaml"
    )
    if not manifest_path.is_file():
        return None
    try:
        raw = _yaml.load(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(raw, dict):
        return None
    component = raw.get("component")
    if not isinstance(component, dict):
        return None
    version = component.get("version")
    if isinstance(version, str):
        return version
    return None


def _pending_migration_scripts(
    capability_source: CapabilitySource,
    installed_version: str | None,
) -> list[Path]:
    """Collect scripts under `<source>/migrations/<X.Y.0>/` whose minor falls in (installed, source].

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


def uninstall_capability(
    target_root: Path,
    name: str,
    *,
    dry_run: bool = False,
) -> Path:
    """Remove the capability subtree and unregister it.

    Caller is responsible for checking references (the safety check) and
    confirming with the user before invoking. This function performs the
    mechanical removal only.

    Returns the path that was (or would be) removed.
    """
    if not is_installed(target_root, name):
        raise click.ClickException(
            f"capability {name!r} is not installed."
        )

    cap_dir = target_root / ".pkit" / "capabilities" / name
    if dry_run:
        return cap_dir

    if cap_dir.is_dir():
        shutil.rmtree(cap_dir)

    _unregister_from_backbone_manifest(target_root, name)
    return cap_dir


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

    Accepts a list of ``{name: str, version: str}`` dicts. Silently
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
        out.append(CapabilityDependency(name=dep_name, version=dep_version))
    return tuple(out)


def _collect_existing_artifact_names(target_root: Path, area: str) -> dict[str, Path]:
    """Gather all installed artifact names (skills or agents) keyed by name.

    Walks the area's `core/` + `project/` plus every installed
    capability's `<area>/` directory. Returns name → path mapping.
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
) -> None:
    """Refresh capability content into dest, omitting any skipped artifacts.

    Routes through the shared ownership-aware tree-refresh primitive
    (`treecopy.refresh_owned_tree`), so the capability's adopter-owned
    top-level ``project/`` subtree is seeded once and never overwritten or
    removed on refresh, while kit-owned content refreshes wholesale (new
    files appear, removed files disappear, modified files update). This is
    the same mechanic the area/adapter sync uses — reimplementing it here
    is what caused the #332 clobber.
    """
    # Skipped skills/agents become generic relative-path exclusions for the
    # primitive (it knows nothing of "skipped artifacts"). Decisions and
    # other artifacts are not skip-eligible (they don't collide by name).
    exclude = frozenset(
        f"{kind}s/{name}.md"
        for kind, name in skipped_artifacts
        if kind in ("skill", "agent")
    )
    treecopy.refresh_owned_tree(
        source, dest, is_owned=_capability_owned, exclude=exclude
    )


def _register_in_backbone_manifest(target_root: Path, name: str) -> None:
    """Add a `kind: capability` entry to the backbone manifest's components list."""
    backbone = read_backbone_manifest(target_root)
    if backbone is None:
        raise click.ClickException(
            ".pkit/manifest.yaml is missing. Run 'pkit init' first."
        )
    manifest_rel = f".pkit/capabilities/{name}/manifest.yaml"
    entry = ComponentRegistryEntry(
        kind="capability", name=name, manifest=manifest_rel
    )
    # Don't duplicate (caller should check, but defensive).
    backbone.components = [
        c for c in backbone.components
        if not (c.kind == "capability" and c.name == name)
    ]
    backbone.components.append(entry)
    write_backbone_manifest(target_root, backbone)


def _unregister_from_backbone_manifest(target_root: Path, name: str) -> None:
    """Remove the `kind: capability, name: X` entry from the backbone manifest."""
    backbone = read_backbone_manifest(target_root)
    if backbone is None:
        return
    backbone.components = [
        c for c in backbone.components
        if not (c.kind == "capability" and c.name == name)
    ]
    write_backbone_manifest(target_root, backbone)


def _stamp_component_manifest(
    target_root: Path,
    capability_source: CapabilitySource,
    skipped_artifacts: tuple[tuple[str, str], ...],
) -> None:
    """Write the per-component manifest at `.pkit/capabilities/<name>/manifest.yaml`.

    Includes skipped-artifacts state for sync to consult later.
    """
    manifest_path = (
        target_root / ".pkit" / "capabilities" / capability_source.name / "manifest.yaml"
    )
    backend_state: dict[str, Any] = {}
    if skipped_artifacts:
        backend_state["skipped"] = [
            {"kind": k, "name": n} for (k, n) in skipped_artifacts
        ]
    manifest = ComponentManifest(
        kind="capability",
        name=capability_source.name,
        version=capability_source.package.version,
        installed_at=_dt.datetime.now(_dt.timezone.utc).isoformat(),
        requires_backbone=capability_source.package.requires_backbone,
        backend_state=backend_state,
    )
    write_component_manifest(manifest_path, manifest)
