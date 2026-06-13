"""`pkit sync` — re-run propagation per COR-001.

Pulls the kit-shipped (canonical) content from source and refreshes the
adopter's kit-owned paths. **Never** touches project-owned content
(`.pkit/<area>/project/`, fixed-path adopter files like
`.claude/settings.json`). Idempotent: re-running with no source change
is a clean no-op.

Sync re-uses the install module's area / adapter copy primitives in
*overwrite* mode. The bash dispatcher does not have a sync command —
this is genuinely new surface, gated only by the existing PR-D / PR-E
infrastructure being in place.
"""

from __future__ import annotations

from pathlib import Path

import click

from project_kit import install
from project_kit.manifest import (
    BackboneManifest,
    read_backbone_manifest,
    read_kit_version,
    write_backbone_manifest,
)


def run_sync(target_root: Path, dry_run: bool = False) -> None:
    """Re-run propagation against an already-initialised target."""
    if not (target_root / ".pkit").is_dir():
        raise click.ClickException(f"{target_root}/.pkit/ does not exist. Run 'pkit init' first.")

    source_kit = install.find_source_kit()

    # Mirror init's source==target guard: project-kit self-hosts, so its
    # own .pkit/ IS the source. Copying files onto themselves either
    # raises SameFileError or is a no-op; either way, sync against
    # project-kit's own tree is the wrong gesture (commit changes
    # directly to the source instead).
    if target_root.resolve() == source_kit.parent.resolve():
        raise click.ClickException(
            f"source and target are the same project ({target_root}).\n"
            f"       project-kit self-hosts directly; running 'pkit sync' on\n"
            f"       project-kit itself would copy files onto themselves. Edit\n"
            f"       the source tree directly instead."
        )

    ctx = install.InstallContext(
        target_root=target_root,
        source_kit=source_kit,
        dry_run=dry_run,
    )

    click.echo(f"Syncing project-kit at {target_root}")
    click.echo(f"  source: {source_kit}")
    if dry_run:
        click.echo("  (dry-run — no changes will be written)")
    click.echo()

    for area in install.PROPAGATED_AREAS:
        src = source_kit / area
        if src.is_dir():
            install._install_area(  # pyright: ignore[reportPrivateUsage]
                src, target_root / ".pkit" / area, ctx, overwrite=True
            )

    # Refresh installed capabilities from source (auto-upgrade per
    # COR-017). Walks the adopter's backbone manifest for components of
    # kind `capability`; for each, re-copies the source subtree (so new
    # files appear, removed files disappear, modified files update). If
    # the capability is no longer in source, warn but leave its tree in
    # place — adopters chose to install it and the kit shouldn't yank
    # content out from under them on sync.
    _sync_installed_capabilities(target_root, source_kit, ctx)

    # Re-run each installed adapter's primitives so the harness side
    # picks up renamed / removed / newly-resolved content (skills moved
    # to flat form, agents whose overlay categories changed, etc.).
    # Init does the same after its first-time copy; sync mirrors it
    # so post-sync state matches post-init state.
    install.run_installed_adapter_primitives(ctx)

    _update_recorded_backbone_version(target_root, source_kit, ctx)
    click.echo()
    click.echo("Sync complete.")

    if not ctx.dry_run:
        _hint_settings_consolidation(target_root)


def _hint_settings_consolidation(target_root: Path) -> None:
    """Print a one-line hint when `.claude/settings.json` has redundant allow entries.

    Detection only — sync never mutates `.claude/settings.json`'s allow
    list beyond what `merge-settings.sh` did (union with baseline +
    skill grants). Cleanup is the adopter's deliberate gesture via
    `pkit settings consolidate`.
    """
    from project_kit import settings_consolidate as consolidator

    plan = consolidator.detect_consolidation_opportunities(target_root)
    if plan is None or not plan.has_redundancies:
        return
    click.echo(
        f"  Note: {len(plan.pairs)} redundant entry(ies) in .claude/settings.json. "
        f"Run `pkit settings consolidate` to clean them up."
    )


def _sync_installed_capabilities(
    target_root: Path, source_kit: Path, ctx: install.InstallContext
) -> None:
    """Refresh installed capabilities from source per COR-017.

    For each capability listed in the adopter's backbone manifest:
    - In source: re-copy the subtree (preserves the capability's
      registered-state and any prior skip overrides). Emits a refreshed
      / unchanged status line per capability.
    - Not in source: warn but do not remove the adopter's installed
      tree.
    """
    from project_kit import capabilities as caps

    backbone = read_backbone_manifest(target_root)
    if backbone is None:
        return
    installed_caps = [c for c in backbone.components if c.kind == "capability"]
    if not installed_caps:
        return

    click.echo()
    click.echo("  Capabilities")

    for entry in installed_caps:
        source = caps.find_capability_in_source(source_kit, entry.name)
        if source is None:
            click.echo(
                f"    {'orphan':<12} {entry.name!r} — no longer ships from source; "
                f"leaving installed copy in place."
            )
            continue
        if ctx.dry_run:
            click.echo(f"    {'would refresh':<12} {entry.name!r} -> v{source.package.version}")
            continue
        # Refresh in place via the capabilities module's auto-upgrade
        # primitive; preserves any skip state from the original install.
        prior_skipped = caps.read_prior_skipped_artifacts(target_root, entry.name)
        caps.refresh_capability(
            target_root,
            source,
            skipped_artifacts=prior_skipped,
            dry_run=False,
        )
        click.echo(f"    {'refreshed':<12} {entry.name!r} -> v{source.package.version}")


def _update_recorded_backbone_version(
    target_root: Path, source_kit: Path, ctx: install.InstallContext
) -> None:
    """Bump the backbone manifest's `backbone_version` to match source after sync."""
    if ctx.dry_run:
        new_version = read_kit_version(source_kit)
        click.echo(f"  {'would update':<12} .pkit/manifest.yaml backbone_version -> {new_version}")
        return

    new_version = read_kit_version(source_kit)
    existing = read_backbone_manifest(target_root)
    if existing is None:
        # Fresh manifest — new install_kit run already stamped it; if
        # absent here, the project pre-dates the manifest layer, so
        # write a minimal one.
        existing = BackboneManifest(backbone_version=new_version)
    elif existing.backbone_version == new_version:
        click.echo(
            f"  {'unchanged':<12} .pkit/manifest.yaml backbone_version stays at {new_version}"
        )
        return
    else:
        click.echo(
            f"  {'updated':<12} .pkit/manifest.yaml backbone_version "
            f"{existing.backbone_version} -> {new_version}"
        )
        existing.backbone_version = new_version

    write_backbone_manifest(target_root, existing)
