"""`pkit upgrade` — version-aware migrations + sync per COR-010.

The full lifecycle COR-010 specifies six steps:

  1. Resolve compatibility (every component's *post-upgrade* `requires_backbone`
     — read from source, the version sync will refresh it to — must include the
     target backbone version).
  2. Pull new propagated content (sync per COR-001).
  3. Run backbone migrations: manifest-schema → structural → resource-scoped.
  4. Run per-component migrations.
  5. Reconcile derivable state (setup primitives idempotently re-apply).
  6. Update recorded versions in manifests.

PR-J ships the **skeleton**: steps 1, 2, 6 are real (compatibility check,
sync delegation, manifest version update via sync). Steps 3, 4, 5 are
placeholders today — no migration scripts exist in the source kit yet,
and no setup primitive contract is fully formalised. The upgrade walks
the migrations tree, reports what it finds (empty today), and
graduates each step into a real implementation as the kit grows.

Compared to `pkit sync` (PR-G), `pkit upgrade` adds:

- Compatibility resolution: refuses if a component's *post-upgrade* (source)
  `requires_backbone` doesn't include the target backbone version. Catches the
  "the new adapter version genuinely can't run on the new backbone" failure
  mode — without the false positive of reading the stale installed ceiling,
  which always lags the auto-broadened source and would block every adopter a
  minor behind.
- Migration discovery + ordered execution (skeleton; no scripts yet).
- Clear "upgrading from X to Y" framing (vs sync's "refreshing").

When the kit is up to date, upgrade reports it and exits — refreshing
content is `sync`'s job, not upgrade's.
"""

from __future__ import annotations

from pathlib import Path

import click
from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.version import InvalidVersion, Version

from project_kit.install import find_source_kit
from project_kit.manifest import (
    ComponentManifest,
    ComponentRegistryEntry,
    read_backbone_manifest,
    read_component_manifest,
    read_kit_version,
    write_component_manifest,
)
from project_kit.migrations import (
    execute_migration_scripts,
    pending_migration_scripts,
    report_pending_migrations,
)
from project_kit.sync import run_sync


def run_upgrade(target_root: Path, dry_run: bool = False) -> None:
    """Transition the project to the source kit's current backbone version."""
    if not (target_root / ".pkit").is_dir():
        raise click.ClickException(f"{target_root}/.pkit/ does not exist. Run 'pkit init' first.")

    manifest = read_backbone_manifest(target_root)
    if manifest is None:
        raise click.ClickException(
            f"{target_root}/.pkit/manifest.yaml is missing. The kit at this target "
            "pre-dates the manifest layer (COR-010). Run 'pkit sync' once to seed "
            "the manifest, then retry upgrade."
        )

    source_kit = find_source_kit()
    target_version = read_kit_version(source_kit)
    current_version = manifest.backbone_version

    # Step 1: compatibility resolution against the POST-upgrade (source)
    # component versions — what sync will refresh them to — not the stale
    # installed copies (which always lag the auto-broadened source ceiling).
    _resolve_compatibility(manifest.components, target_root, source_kit, target_version)

    if current_version == target_version:
        click.echo(f"Already at backbone v{target_version}; nothing to upgrade.")
        return

    click.echo(f"Upgrading backbone: {current_version} -> {target_version}")
    if dry_run:
        click.echo("  (dry-run — no changes will be written)")
    click.echo()

    # Step 2: pull new propagated content (sync). Sync also updates the
    # recorded backbone version (step 6 for the backbone tier).
    if dry_run:
        click.echo("  would sync   .pkit/ kit-owned content from source")
    else:
        run_sync(target_root, dry_run=False)

    # Steps 3-5: migrations + reconciliation. Skeleton today.
    _run_backbone_migrations(target_root, current_version, target_version, dry_run)
    _run_component_migrations(target_root, manifest.components, dry_run)

    click.echo()
    click.echo("Upgrade complete.")


def _resolve_compatibility(
    components: list[ComponentRegistryEntry],
    target_root: Path,
    source_kit: Path,
    target_version: str,
) -> None:
    """Check every component's post-upgrade `requires_backbone` accepts the target.

    For each installed component, reads the `requires_backbone` range from the
    **source** `package.yaml` (the version it becomes after the upgrade's sync),
    falling back to the installed copy for components the source no longer ships
    (see `_resolve_package_yaml`). Raises `click.ClickException` on conflict so
    the caller surfaces it before any state changes.
    """
    try:
        target = Version(target_version)
    except InvalidVersion as exc:
        raise click.ClickException(
            f"source kit version {target_version!r} is not valid semver"
        ) from exc

    conflicts: list[str] = []
    for entry in components:
        package_yaml = _resolve_package_yaml(target_root, source_kit, entry)
        if package_yaml is None:
            continue
        range_str = _extract_requires_backbone(package_yaml)
        if range_str is None:
            continue
        spec = _to_specifier_set(range_str)
        if spec is None:
            continue
        if target not in spec:
            conflicts.append(
                f"  {entry.kind} '{entry.name}' requires backbone {range_str}; "
                f"target {target_version} is out of range"
            )

    if conflicts:
        raise click.ClickException(
            "compatibility check failed — installed components are not compatible "
            f"with backbone v{target_version}:\n" + "\n".join(conflicts)
        )


def _resolve_package_yaml(
    target_root: Path, source_kit: Path, entry: ComponentRegistryEntry
) -> Path | None:
    """Locate a component's kit-owned `package.yaml` for the compatibility check.

    Prefers the **source** copy — the version the component *becomes* after the
    upgrade's own sync step refreshes kit-shipped content (COR-001 / COR-017).
    Reading the *installed* copy would consult the stale, about-to-be-replaced
    `requires_backbone` ceiling and wrongly refuse every adopter that is a minor
    behind (the source ceiling auto-broadens on each backbone bump, so the
    installed copy always lags the target). Falls back to the installed copy for
    a component the source no longer ships — it won't be refreshed by sync, so
    its declared range still governs.
    """
    if entry.kind == "adapter":
        rel = Path("adapters") / entry.name / "package.yaml"
    elif entry.kind == "capability":
        rel = Path("capabilities") / entry.name / "package.yaml"
    else:
        return None
    for base in (source_kit, target_root / ".pkit"):
        candidate = base / rel
        if candidate.is_file():
            return candidate
    return None


def _extract_requires_backbone(package_yaml: Path) -> str | None:
    """Read a package.yaml file and return the requires_backbone string, or None."""
    import re

    text = package_yaml.read_text(encoding="utf-8")
    match = re.search(r'requires_backbone:\s*"([^"]+)"', text)
    return match.group(1) if match else None


def _to_specifier_set(range_str: str) -> SpecifierSet | None:
    """Parse a `>=X,<Y` range into a packaging SpecifierSet, or None on error."""
    try:
        return SpecifierSet(range_str)
    except InvalidSpecifier:
        return None


def _run_backbone_migrations(
    target_root: Path, current_version: str, target_version: str, dry_run: bool
) -> None:
    """Walk backbone migrations between current and target versions and execute them.

    Per COR-010, backbone migrations live at
    `.pkit/migrations/backbone/<X.Y.0>/<NNN>-<slug>.sh`. They're
    kit-shipped content propagated by sync; by the time this runs
    (upgrade step 3, after sync), they're present in the target tree.

    Window: every minor version strictly above `current_version` and
    at-or-below `target_version`. Halts on first non-zero exit so a
    half-applied upgrade is visible.

    Scope ordering (manifest-schema → structural → resource) per COR-010
    is *within* a version dir, expressed via `NNN-*.sh` filename order
    — author by convention rather than declared metadata for now.
    """
    migrations_root = target_root / ".pkit" / "migrations" / "backbone"
    scripts = pending_migration_scripts(migrations_root, current_version, target_version)

    if not scripts:
        click.echo(
            f"  no backbone migrations to run between {current_version} and {target_version}"
        )
        return

    if dry_run:
        report_pending_migrations(
            scripts,
            label="backbone",
            installed_version=current_version,
            target_version=target_version,
            dry_run=True,
            label_rel_to=migrations_root,
        )
        return

    click.echo(
        f"  running {len(scripts)} backbone migration(s) "
        f"({current_version} -> v{target_version})"
    )
    execute_migration_scripts(
        scripts,
        target_root,
        label="backbone",
        label_rel_to=migrations_root,
    )


def _run_component_migrations(
    target_root: Path,
    components: list[ComponentRegistryEntry],
    dry_run: bool,
) -> None:
    """Walk each installed adapter, run any pending migrations.

    Capabilities are NOT handled here — their migration story runs
    through `pkit sync` → `_sync_installed_capabilities` →
    `refresh_capability` (per COR-017). Double-running here would
    re-execute scripts that sync already applied.

    For each component:
    - Read installed version from the per-component manifest.
    - Read source version from the kit-shipped `package.yaml`.
    - Walk `<source>/migrations/<X.Y.0>/` for the open window.
    - Execute scripts.
    - On success, re-stamp the per-component manifest with the new
      version + a fresh `installed_at` timestamp.
    """
    if not components:
        return

    eligible = [c for c in components if c.kind == "adapter"]
    if not eligible:
        return

    ran = 0
    for entry in eligible:
        component_dirs = _resolve_component_dirs(target_root, entry)
        if component_dirs is None:
            # Unable to resolve source / installed manifest for this
            # component — skip rather than raise.
            continue
        source_dir, installed_manifest_path = component_dirs
        package_yaml = source_dir / "package.yaml"
        if not package_yaml.is_file():
            continue
        source_version = _extract_package_version(package_yaml)
        if source_version is None:
            continue

        installed_manifest = read_component_manifest(installed_manifest_path)
        if installed_manifest is None:
            # No record of installed version — skip rather than guess.
            continue

        migrations_root = source_dir / "migrations"
        scripts = pending_migration_scripts(
            migrations_root, installed_manifest.version, source_version
        )
        if not scripts:
            continue

        label = f"{entry.kind} {entry.name!r}"
        if dry_run:
            report_pending_migrations(
                scripts,
                label=label,
                installed_version=installed_manifest.version,
                target_version=source_version,
                dry_run=True,
                label_rel_to=source_dir,
            )
            ran += 1
            continue

        click.echo(
            f"  running {len(scripts)} migration(s) for {label} "
            f"({installed_manifest.version} -> v{source_version})"
        )
        execute_migration_scripts(
            scripts, target_root, label=label, label_rel_to=source_dir
        )
        # Re-stamp installed manifest with new version + timestamp.
        _restamp_component_manifest_version(
            installed_manifest_path, installed_manifest, source_version
        )
        ran += 1

    if ran == 0:
        click.echo(
            f"  no component migrations to run (0 of {len(eligible)} adapter component(s))"
        )


def _resolve_component_dirs(
    target_root: Path, entry: ComponentRegistryEntry
) -> tuple[Path, Path] | None:
    """Return (source_dir, installed_manifest_path) for a registered component.

    Source dir contains `package.yaml` + `migrations/`. Installed manifest
    is where the adopter-side per-component receipt lives.
    - Adapter: source `.pkit/adapters/<name>/`, manifest
      `.pkit/adapters/<name>/project/manifest.yaml`.

    Returns None when resolution fails (missing files, unknown kind).
    Capabilities are handled by sync; future kinds skip.
    """
    pkit_dir = target_root / ".pkit"

    if entry.kind == "adapter":
        source_dir = pkit_dir / "adapters" / entry.name
        installed_manifest = source_dir / "project" / "manifest.yaml"
        if not source_dir.is_dir():
            return None
        return source_dir, installed_manifest

    # Unknown kind (capability handled by sync; future kinds skip).
    return None


def _extract_package_version(package_yaml: Path) -> str | None:
    """Parse `version:` from a component's `package.yaml`, returning None if absent."""
    import re as _re

    text = package_yaml.read_text(encoding="utf-8")
    match = _re.search(r"version:\s*([0-9]+\.[0-9]+\.[0-9]+)", text)
    return match.group(1) if match else None


def _restamp_component_manifest_version(
    manifest_path: Path, manifest: ComponentManifest, new_version: str
) -> None:
    """Update the per-component manifest's `version` (+ `installed_at`) after migrations succeed."""
    import datetime as _dt

    manifest.version = new_version
    manifest.installed_at = _dt.datetime.now(_dt.timezone.utc).isoformat()
    write_component_manifest(manifest_path, manifest)
