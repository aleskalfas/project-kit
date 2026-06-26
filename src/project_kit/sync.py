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
    ORIGIN_INCUBATED_IN_REPO,
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

    # Self-host (project-kit): its own .pkit/ IS the source, so propagation
    # would copy files onto themselves. Rather than refuse, run only the
    # deploy primitives — they (re-)materialise the harness side
    # (.claude/agents, skills, settings, CLAUDE.md) from the source tree the
    # maintainer just edited. This is the self-host equivalent of sync:
    # "re-wire me to my own source." Propagation, capability refresh, and the
    # recorded-version stamp are skipped — the source is already the state.
    if target_root.resolve() == source_kit.parent.resolve():
        ctx = install.InstallContext(
            target_root=target_root,
            source_kit=source_kit,
            dry_run=dry_run,
        )
        click.echo(f"Syncing project-kit at {target_root} (self-host)")
        click.echo(
            "  source == target: skipping propagation; running deploy "
            "primitives only."
        )
        if dry_run:
            click.echo("  (dry-run — no changes will be written)")
        click.echo()
        install.run_installed_adapter_primitives(ctx)
        # Render `.pkit/.gitignore` at the CORE tier (ADR-009 Amendment 1, T2).
        # The self-host path runs ONLY the adapter-primitives runner and skips
        # propagation — but the renderer is a core step, not an adapter
        # primitive, so it must run here too or backbone/capability runtime
        # ignores would never render in self-host (or any adapter-less) sync.
        install._render_runtime_ignore(ctx)  # pyright: ignore[reportPrivateUsage]
        click.echo()
        click.echo("Self-host sync complete (deploy primitives re-run).")
        return

    # Past the self-host short-circuit: this is a real adopter sync, which reads
    # `read_kit_version(source_kit)` and propagates trees from `source_kit`.
    # Guard the resolved source before either, so an incomplete bundle yields a
    # clean ClickException rather than a raw FileNotFoundError mid-propagation
    # (ADR-033; issue #333). The self-host branch above is skipped — its source
    # is the live checkout, which always satisfies the guard.
    install.refuse_if_source_kit_incomplete(source_kit)

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

    # Render `.pkit/.gitignore` at the CORE tier (ADR-009 Amendment 1, T2) —
    # wholesale from the current installed components' `runtime_ignore:`
    # declarations. A core step (sibling to propagation), not an adapter
    # primitive, so it covers backbone + capability declarations regardless of
    # whether an adapter is installed.
    install._render_runtime_ignore(ctx)  # pyright: ignore[reportPrivateUsage]

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
    """Refresh installed capabilities from source per COR-017 / COR-031.

    For each capability listed in the adopter's backbone manifest:
    - `kit-shipped` origin:
        - In source: re-copy the subtree (preserves the capability's
          registered-state and any prior skip overrides). Emits a refreshed
          / unchanged status line per capability.
        - Not in source: warn but do not remove the adopter's installed
          tree.
    - `incubated-in-repo` origin (COR-031 D1): skip source-reconciliation
      entirely — the subtree is adopter-owned (the no-shared-files invariant,
      COR-001), there is no kit source to refresh from, and the
      "no-longer-shipped" warning would mislabel deliberately-local content.
      Boundary case (COR-031): if the kit *does* now ship a same-named
      capability, surface that collision (graduation arriving unbidden) so the
      adopter can decide, rather than silently skipping. Self-consistency
      validation, dependency-gating, and deploy still apply to incubated
      capabilities — only reconciliation-against-kit-source is suppressed here.
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
        # Incubated (in-repo) capabilities are adopter-owned: skip
        # source-reconciliation (no refresh, no orphan warning). Origin lives
        # in lifecycle-owned install-state on the registry entry (COR-031 D2),
        # so branch on it directly.
        if entry.origin == ORIGIN_INCUBATED_IN_REPO:
            _report_incubated_capability(source_kit, entry.name)
            continue

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


def _report_incubated_capability(source_kit: Path, name: str) -> None:
    """Emit the per-capability status line for an incubated (in-repo) capability.

    Source-reconciliation is suppressed for an incubated capability (COR-031
    D1), so this never refreshes or removes anything — it only reports. Two
    cases (COR-031's boundary case):

    - The kit ships **no** capability of this name: skip silently. The
      capability is deliberately adopter-owned; reporting it as orphaned or
      refreshing it would be wrong. A one-line ``incubated`` status keeps the
      output honest without implying anything is amiss.
    - The kit **now ships** a same-named capability: surface the collision —
      graduation arriving unbidden (the deferred case showing up early). Until
      graduation is specified, the adopter decides; the lifecycle must not
      silently shadow either the incubated tree or the newly-available kit
      capability.
    """
    from project_kit import capabilities as caps

    kit_source = caps.find_capability_in_source(source_kit, name)
    if kit_source is None:
        click.echo(
            f"    {'incubated':<12} {name!r} — in-repo capability; "
            f"skipping source-reconciliation."
        )
        return
    click.echo(
        f"    {'collision':<12} {name!r} — in-repo capability, but the kit now "
        f"ships a capability of the same name (v{kit_source.package.version}). "
        f"Source-reconciliation stays skipped; resolve the collision manually."
    )


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
