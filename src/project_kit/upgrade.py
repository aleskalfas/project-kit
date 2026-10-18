"""`pkit upgrade` — the version transition of the backbone (COR-059, ADR-065).

The one command that moves a project to a new release. Its own checks come
first, and depend on the code that runs it (ADR-065 points 4 and 9):

- **a pinned project's upgrade under its pin's code** (the router's routed
  child, or the installed pkit that is the pin): the hand-over to a newer
  latest release, then the older-direction check. Otherwise it runs the
  transition to its pin.
- **any other upgrade:** the refusal under the router's fallback, then
  ADR-063's tool step in an un-pinned project, then the older-direction check.

It records its target first, as `backbone_version`, and its completion last,
as `completed_version`, and every migration runs inside it, in COR-010's order
(ADR-065 point 4):

  1. Compatibility and collisions, each of which may refuse and none of which
     writes: the refusal of an adapter or capability its bundle ships older
     than the project records (point 7), the refusal of a clash of area names
     (point 13), every component's post-upgrade `requires_backbone` against the
     target, the dependency gates over the set the transition would leave
     (COR-030, COR-053 point 6), and the collision flow, which asks at a
     terminal and refuses without one (point 6).
  2. Record the target, move each capability manifest still at its root under
     its `project/`, record each skip chosen in step 1, and remove each project
     artefact an override replaces.
  3. Propagate at the target, through the propagation step `pkit sync` runs
     (`sync.propagate`), never the sync command, so sync's guard never stops an
     upgrade (ADR-065 point 1). Register an adapter the target adds, and render
     `.pkit/.gitignore`, so a migration reads the target's render.
  4. Run the backbone migrations, from the last completion.
  5. Run each adapter's migrations, read from the bundle, and record it.
  6. Run each capability's migrations, dependencies first, and restamp it.
  7. Create each missing seed path.
  8. Regenerate the derivable state, and report each widening the settings
     merge brings.
  9. Record the completion, then (10) the pin.

Then, outside the transition, the questions the data points declare
(COR-061; `point_questions`).

When the project is current, upgrade reports it and exits: refreshing content
at the recorded version is `sync`'s job, not upgrade's.
"""

from __future__ import annotations

import os
import re
import shlex
import subprocess
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import TYPE_CHECKING, NoReturn

import click
from packaging.version import InvalidVersion, Version

from project_kit.install import (
    InstallContext,
    find_source_kit,
    is_self_host,
    refuse_if_source_kit_incomplete,
    refuse_propagation_into_source,
    register_adapters,
    seed_missing_paths,
)
from project_kit.manifest import (
    ORIGIN_KIT_SHIPPED,
    BackboneManifest,
    ComponentManifest,
    ComponentRegistryEntry,
    read_backbone_manifest,
    read_component_manifest,
    read_component_package,
    read_kit_version,
    record_adapter_version,
    record_backbone_target,
    record_completed_version,
    write_component_manifest,
)
from project_kit.migrations import (
    execute_migration_scripts,
    pending_migration_scripts,
    report_pending_migrations,
)
from project_kit.router import (
    DISTRIBUTION_GIT_URL,
    is_route_bypassed,
    is_routed_child,
    is_source_checkout,
    pin_file_path,
    read_version_pin,
    run_bypassed,
    running_version,
    unresolved_pin,
    write_version_pin,
)
from project_kit.sync import (
    COPIES,
    EXTERNAL,
    INCUBATED,
    ORPHAN,
    UNVERSIONED,
    CapabilityPlan,
    fallback_remedies,
    plan_capabilities,
    propagate,
    refuse_area_name_clash,
    refuse_content_downgrade,
    regenerate_derivable_state,
    report_incubated_capability,
    run_self_host,
)
from project_kit.versioning import is_release_version

if TYPE_CHECKING:
    from project_kit.capabilities import MandatoryUpstream

# Capability-dependency check (COR-030) — imported lazily below to avoid
# any circular-import issues at module load time. The functions used are:
#   capabilities.check_capability_dependencies
#   capabilities.find_declared_dependents
#   capabilities.get_installed_capability_version
#   capabilities._read_package_yaml (internal, accessed via CapabilitySource path)


def run_upgrade(
    target_root: Path,
    dry_run: bool = False,
    pin: bool = True,
    self_update: bool = True,
    force: bool = False,
) -> None:
    """Transition the project to the source kit's current backbone version.

    The steps run in COR-010's order, as the module docstring lists them
    (ADR-065 point 4). *force* (`pkit upgrade --force`) overrides the two
    warnings of the dependency gates, for a capability that does not move, and
    nothing else: no guard, no compatibility refusal, no refusal of a
    component bundled older, no collision, no clash of area names and no
    refusal under the router's fallback (point 6). A pinned upgrade that hands
    over to a newer release passes it, and *dry_run*, to that release's upgrade
    (point 9).

    **Pins by default** (ADR-064): an **un-pinned** project is pinned at the
    version its content just synced to, so pinning is the norm and a project
    stays code/content-coherent without a remembered gesture. `pin=False` (the
    `--no-pin` opt-out) keeps the project un-pinned, following the installed
    global tool. The pin uses the local synced version (offline-safe — no
    `git ls-remote` lookup), is written LAST (after content + migrations, so a
    failed sync never leaves a pin ahead of content), and is a no-op on a project
    that is already pinned (the existing pin-raise already maintains it). Self-host
    is never pinned — it returns before the pin logic.
    """
    if not (target_root / ".pkit").is_dir():
        raise click.ClickException(f"{target_root}/.pkit/ does not exist. Run 'pkit init' first.")

    source_kit = find_source_kit()

    # Self-host (project-kit): the source IS the installed state, so there is
    # no backbone to upgrade. Run sync's self-host branch, before any of
    # upgrade's checks, which re-runs the deploy primitives so the harness picks
    # up source edits (ADR-065 point 1). Skips the version comparison (the
    # recorded manifest version is moot on self-host) and the migration steps
    # (self-host authors migrations with the source change; it does not run them
    # against itself). The test is sync's test for the methodology's source
    # repository (ADR-059 point 2).
    if is_self_host(target_root, source_kit):
        click.echo("Self-host: source is the installed state; no backbone upgrade needed.")
        click.echo("Re-running deploy primitives via sync.")
        click.echo()
        run_self_host(target_root, source_kit, dry_run=dry_run)
        return

    # Sync's test has said no, but the markers may still call the target the
    # methodology's source: the running code is then not the repository's own
    # (the gap, ADR-059). Refuse here, before the pinned-child branch and the
    # bypass guard: both bypass paths into the gap set PKIT_NO_ROUTE, which skips
    # the tool step below, so a refusal placed there would never be reached (#1070).
    refuse_propagation_into_source(target_root, source_kit, command="upgrade")

    # ADR-049: this project may pin a pkit version via `.pkit/version-pin`. Its
    # presence changes what `pkit upgrade` means — an upgrade *raises* the pin
    # (flipped last) rather than floating on the installed tool.
    current_pin = read_version_pin(target_root)
    pinned = current_pin is not None
    if current_pin is not None and runs_at_its_pin(current_pin):
        # Under its pin's code (ADR-065 point 9): the router's routed child, or
        # the installed pkit the router runs in process because it is the pin.
        # Its checks, in order: the hand-over to a newer latest release, then
        # the older-direction check. Otherwise it runs the transition to its pin
        # below, with no tool step (ADR-063 point 5).
        if _auto_advance_pinned(target_root, source_kit, current_pin, dry_run=dry_run, force=force):
            return
    else:
        # Any other upgrade. First the refusal under the router's fallback
        # (ADR-065 point 9): run by the installed pkit because the router could
        # not fetch the pin, the upgrade would move the pin to that pkit's
        # version, not to a release it resolved. A routed child that inherited
        # the mark never meets it: its branch is above.
        refuse_under_routers_fallback(target_root)

        # ADR-063: detect a newer *released tool* and install it, or print the
        # command where it cannot or may not. This is about the `uv`-installed
        # binary, not this project's `.pkit/` content — so it runs before the
        # backbone-version comparison below and its early return (point 4), or
        # the stale-tool adopter would still see only "nothing to upgrade".
        # Best-effort: a failed lookup or install never fails the command,
        # though a failed hand-over stops it before the sync and the pin (point
        # 3). It is never reached in a source checkout (point 5) — the self-host
        # branch returns and the source refusal raises above it.
        #
        # It runs only in an un-pinned project (ADR-063 point 5): a pinned
        # project's pin moves through the router's bypass, never by the tool.
        # And it is suppressed on the bootstrap hop: inside a
        # `run_bypassed`-launched reconcile (PKIT_NO_ROUTE set), this upgrade is
        # running *under* a pin raise, and a second `git ls-remote` here would
        # print a nonsensical "tool is current" line mid-raise.
        if not pinned and not is_route_bypassed(os.environ):
            # Tool axis (ADR-063): self-update the global tool when stale
            # and re-exec to finish under the new version (never returns on a
            # successful self-update); otherwise instruct or report current.
            _maybe_self_update_tool(self_update=self_update, dry_run=dry_run)

        # Past the self-host short-circuit: a real adopter upgrade reads
        # `read_kit_version(source_kit)` next and propagates from `source_kit`
        # via its sync step. Guard the resolved source first, so an incomplete
        # bundle surfaces as a clean ClickException rather than a raw
        # FileNotFoundError inside `read_kit_version` (ADR-033; issue #333).
        # The self-host branch above is skipped — its source is the live
        # checkout.
        refuse_if_source_kit_incomplete(source_kit)

        # #1212: a pkit older than the project's content or pin must not sync
        # its older content over the project's or move the pin down. Checked
        # before anything below writes, after the tool step, which leaves the
        # project untouched and whose re-exec under a newer tool is a way past
        # this refusal. The older direction of sync's guard (ADR-065 point 7):
        # the running pkit against the newest of `backbone_version`,
        # `completed_version` and the pin.
        refuse_content_downgrade(target_root, source_kit, command="upgrade")

    target_version = read_kit_version(source_kit)
    # Read before anything is written. No manifest is no refusal: the transition
    # writes one at its target and replays (ADR-065 points 2 and 5).
    manifest = read_backbone_manifest(target_root)
    components = manifest.components if manifest is not None else []

    # A project already current returns after upgrade's own checks, before step
    # 1, and only writes or raises its pin (ADR-065 point 4).
    if manifest is not None and is_current(target_root, source_kit, manifest, target_version):
        click.echo(f"Already at backbone v{target_version}; nothing to upgrade.")
        # ADR-049: content is already current, but a pinned project may still
        # need its pin flipped forward (e.g. raised via the bypass with content
        # already synced). Flip only when it actually moves.
        if pinned:
            _raise_pin_to(target_root, target_version, dry_run)
        elif pin:
            # Pin-by-default on an un-pinned project whose content is already
            # current: pin at the current content version (unless `--no-pin`).
            _pin_after_upgrade(target_root, target_version, dry_run)
        return

    # The lower bound of the backbone's migration window: the last completed
    # transition, or none, which replays every backbone migration once.
    completed = replay_lower_bound(manifest)
    _report_transition(manifest, completed, target_version, dry_run)

    # Every capability's record is read before anything is written (ADR-065
    # point 2): its version falls back to the installed `package.yaml`, which the
    # copy replaces.
    from project_kit import capabilities as caps

    plans = plan_capabilities(target_root, source_kit, caps.read_capability_records(target_root))
    moves = component_moves(target_root, source_kit, manifest) if manifest is not None else []
    _report_component_moves(moves)

    # Step 1: compatibility and collisions (ADR-065 points 4, 6, 7 and 13). Each
    # may refuse, and none writes: the refusal of a component its bundle ships
    # older, the refusal of a clash of area names, compatibility resolution
    # against the post-upgrade (bundled) versions, the dependency gates over the
    # set the transition would leave, and the collision flow, which asks a person
    # or refuses.
    refuse_components_bundled_older(moves)
    refuse_area_name_clash(target_root, source_kit, command="upgrade")
    _resolve_compatibility(components, target_root, source_kit, target_version)
    _check_capability_dep_conflicts_for_upgrade(target_root, plans, force=force)
    answers = _settle_new_collisions(target_root, plans, dry_run=dry_run)
    plans = [answers.in_force(plan) for plan in plans]
    # Every shipped capability the bundle ships moves with the release.
    moving = [plan for plan in plans if plan.disposition in COPIES]
    ctx = InstallContext(target_root=target_root, source_kit=source_kit, dry_run=dry_run)

    # Step 2: the target is recorded before anything else is written, so an
    # interrupted transition reads as one, to this pkit and to an older one
    # alike. Then each capability manifest still at its root moves under its
    # `project/`, where the copy cannot prune it, each skip chosen in step 1 is
    # recorded there, and each override removes the project's artefact. So an
    # interrupted transition does not ask again: the next one finds a skip in
    # the record, and an overridden name in the capability's installed copy.
    # Step 3: propagation at the target, through the propagation step sync runs,
    # never the sync command, so sync's guard never stops an upgrade. Then an
    # adapter the target adds is registered, and `.pkit/.gitignore` is
    # rendered, so a migration reads the target's render.
    if dry_run:
        click.echo(
            f"  {'would record':<12} .pkit/manifest.yaml backbone_version -> {target_version} "
            "(the target, before anything else is written)"
        )
        _move_root_manifests(target_root, plans, dry_run=True)
        click.echo(
            "  would copy   .pkit/ kit-owned content and each shipped capability from source"
        )
        _report_adapters_to_register(target_root, source_kit, components)
    else:
        record_backbone_target(target_root, target_version)
        click.echo(
            f"  {'recorded':<12} .pkit/manifest.yaml backbone_version -> {target_version} "
            "(the target)"
        )
        _move_root_manifests(target_root, plans, dry_run=False)
        _record_new_skips(target_root, moving, answers)
        caps.apply_overrides(target_root, answers.overridden, dry_run=False)
        propagate(ctx, moving)
        register_adapters(target_root)
        reread = read_backbone_manifest(target_root)
        components = reread.components if reread is not None else []
        _render_runtime_ignore(target_root)

    # Step 4: the backbone's migrations, from the last completion.
    _run_backbone_migrations(target_root, source_kit, completed, target_version, dry_run)
    # Step 5: each adapter's, read from the bundle, and its record.
    _run_component_migrations(target_root, source_kit, components, dry_run)
    # Step 6: each capability's, after its copy, dependencies first, and its
    # restamp.
    _migrate_capabilities(target_root, plans, dependencies_first(moving), dry_run=dry_run)

    # Step 7: the seed paths a release declares are created where missing, never
    # over one that exists (ADR-065 point 11): after the migrations, so a
    # migration that moves a project's file to a seed path finds no fresh seed
    # there, and before deploy reads the overlay and merge the adapter's project
    # settings.
    seed_missing_paths(ctx, capabilities=[plan.name for plan in moving])
    # Step 8: the derivable state, after every migration: merge delivery,
    # deploy, `.pkit/.gitignore` rendered again, the agent workspace and
    # provisioning. The report names each widening the settings merge brings.
    if not dry_run:
        from project_kit import settings_consolidate as settings

        before = settings.read_merged_settings(target_root)
        regenerate_derivable_state(ctx)
        settings.report_widening(
            settings.settings_widening(before, settings.read_merged_settings(target_root))
        )

    # Step 9: the completion is recorded last before the pin: every migration
    # has run and the derivable state is regenerated.
    if dry_run:
        click.echo(
            f"  {'would record':<12} .pkit/manifest.yaml completed_version -> {target_version} "
            "(the completion, once every migration has run)"
        )
    else:
        record_completed_version(target_root, target_version)
        click.echo(
            f"  {'recorded':<12} .pkit/manifest.yaml completed_version -> {target_version} "
            "(the transition is complete)"
        )

    # Step 10, ADR-049: on a pinned project, flip the pin LAST — after content
    # sync and migrations — so a failed upgrade never advances the pin past
    # content that isn't in place. The write itself is atomic. On an un-pinned
    # project the same last-position write freezes the pin at the just-synced
    # version by default (pin-by-default, ADR-064; `--no-pin` sets pin=False to
    # skip it).
    if pinned:
        _raise_pin_to(target_root, target_version, dry_run)
    elif pin:
        _pin_after_upgrade(target_root, target_version, dry_run)

    click.echo()
    click.echo("Upgrade complete.")

    # After the transition (COR-061; ADR-065 point 4): every question a data
    # point declares, once the transition is complete and the pin written, asked
    # where a person can answer and named otherwise. No step of the transition.
    # A dry run names them from the wiring with each moving capability at the
    # version the bundle ships.
    from project_kit import point_questions

    sources = [plan.source for plan in moving if plan.source is not None] if dry_run else []
    point_questions.ask(
        target_root,
        point_questions.questions_for(point_questions.wiring_after(target_root, sources)),
        dry_run=dry_run,
    )


# --- What a transition records and moves (ADR-065 points 2, 3 and 5) -----------


@dataclass(frozen=True)
class ComponentMove:
    """One component whose record is not the version the running pkit's bundle ships.

    *recorded* is None when it records no version. Most are moves a transition
    makes. One *ahead* of the bundle is not: a transition never moves a recorded
    state down, and refuses it in its step 1 (ADR-065 point 7,
    `refuse_components_bundled_older`).
    """

    kind: str
    name: str
    recorded: str | None
    bundled: str

    @property
    def ahead(self) -> bool:
        """The record is newer than the version the bundle ships."""
        return self.recorded is not None and not _moves_up(self.recorded, self.bundled)


def as_recorded_version(text: str | None) -> str | None:
    """A recorded version as the `X.Y.Z` the migration window reads, or None when
    it is missing or no version, which reads as no record (ADR-065 point 2)."""
    if not text:
        return None
    try:
        parsed = Version(text)
    except InvalidVersion:
        return None
    return f"{parsed.major}.{parsed.minor}.{parsed.micro}"


def replay_lower_bound(manifest: BackboneManifest | None) -> str | None:
    """The lower bound of the backbone's migration window: the recorded
    completion, or None, which replays every backbone migration once.

    None when the project has no manifest, no completion or one that is no
    version (ADR-065 point 5), and when its `backbone_version` is no version:
    upgrade then writes the manifest at its target as first install does, and
    replays (point 2). Read-only.
    """
    if manifest is None or as_recorded_version(manifest.backbone_version) is None:
        return None
    return as_recorded_version(manifest.completed_version)


def _bundled_adapter_package(source_kit: Path, name: str) -> Path:
    """Where the running pkit's bundle keeps adapter *name*'s `package.yaml`."""
    return source_kit / "adapters" / name / "package.yaml"


def component_moves(
    target_root: Path, source_kit: Path, manifest: BackboneManifest
) -> list[ComponentMove]:
    """Each component whose record is not the version the running pkit's bundle
    ships (ADR-065 point 2).

    A registered adapter the bundle ships, whose manifest records another
    version, or none, a missing manifest included. A registered `kit-shipped`
    capability the bundle ships, whose record (its manifest, else its installed
    `package.yaml`) is another version, or none. An incubated, externally-sourced
    or no-longer-shipped component moves by its own course, and is not listed.
    A bundled version that is no version moves nothing. Read-only.
    """
    from project_kit import capabilities as caps

    moves: list[ComponentMove] = []
    for entry in manifest.components:
        if entry.kind == "adapter":
            package = read_component_package(_bundled_adapter_package(source_kit, entry.name))
            if package is None or as_recorded_version(package[0]) is None:
                continue
            recorded_manifest = _read_adapter_manifest(target_root, entry)
            recorded = recorded_manifest.version if recorded_manifest is not None else None
            if not _same_version(recorded, package[0]):
                moves.append(ComponentMove("adapter", entry.name, recorded, package[0]))
        elif entry.kind == "capability" and entry.origin == ORIGIN_KIT_SHIPPED:
            source = caps.find_capability_in_source(source_kit, entry.name)
            if source is None:
                continue
            recorded = caps.read_capability_record(target_root, entry.name).version
            move = capability_move(entry.name, recorded, source.package.version)
            if move is not None:
                moves.append(move)
    return moves


def capability_move(name: str, recorded: str | None, bundled: str) -> ComponentMove | None:
    """Capability *name*'s move from *recorded* to *bundled*, the version the
    running pkit's bundle ships, or None when it records that version already, or
    the bundled version is no version, which moves nothing (ADR-065 point 2).

    The transition of the backbone reads it for each shipped capability
    (`component_moves`), and the transition of one capability for its own
    (`pkit capabilities upgrade`). A move *ahead* of the bundle is refused by
    either (`refuse_components_bundled_older`). Read-only.
    """
    if as_recorded_version(bundled) is None or _same_version(recorded, bundled):
        return None
    return ComponentMove("capability", name, recorded, bundled)


def _same_version(recorded: str | None, bundled: str) -> bool:
    """Whether *recorded* names the version *bundled* does, however each is
    written (`v0.6.0` and `0.6.0` alike)."""
    normalised = as_recorded_version(recorded)
    return normalised is not None and normalised == as_recorded_version(bundled)


def _moves_up(recorded: str | None, bundled: str) -> bool:
    """Whether a component recorded at *recorded* moves to *bundled*: it records no
    version, or an older one. A bundled version that is no version moves nothing."""
    if as_recorded_version(bundled) is None:
        return False
    if as_recorded_version(recorded) is None:
        return True
    return Version(recorded or "") < Version(bundled)


def is_current(
    target_root: Path, source_kit: Path, manifest: BackboneManifest, target_version: str
) -> bool:
    """Whether upgrade's early return applies (ADR-065 point 2): `backbone_version`
    and `completed_version` both name *target_version*, and every registered
    adapter and shipped capability records the version the bundle ships, under
    its `project/`. A capability manifest still at its root is one sync skips
    and names `pkit upgrade` for, so the transition runs to move it."""
    return (
        manifest.backbone_version == target_version
        and manifest.completed_version == target_version
        and not component_moves(target_root, source_kit, manifest)
        and not _capability_manifests_at_root(target_root, manifest)
    )


def _capability_manifests_at_root(target_root: Path, manifest: BackboneManifest) -> list[str]:
    """The shipped capabilities whose manifest is still at the capability's root."""
    from project_kit import capabilities as caps

    return [
        entry.name
        for entry in manifest.components
        if entry.kind == "capability"
        and entry.origin == ORIGIN_KIT_SHIPPED
        and caps.read_capability_record(target_root, entry.name).at_root
    ]


def _read_adapter_manifest(
    target_root: Path, entry: ComponentRegistryEntry
) -> ComponentManifest | None:
    """A registered adapter's manifest, None when it has none or records no version.

    The path is the one its registry entry names. A manifest whose version is no
    version records nothing, as a missing one (ADR-065 point 2).
    """
    recorded = read_component_manifest(target_root / entry.manifest)
    if recorded is None or as_recorded_version(recorded.version) is None:
        return None
    return recorded


def _report_transition(
    manifest: BackboneManifest | None,
    completed: str | None,
    target_version: str,
    dry_run: bool,
) -> None:
    """The transition's opening lines: where it moves from, and where its
    backbone migrations run from, the replay named (ADR-065 point 5)."""
    if manifest is None:
        origin = "no .pkit/manifest.yaml"
    elif as_recorded_version(manifest.backbone_version) is None:
        origin = f"{manifest.backbone_version!r}, which is no version"
    else:
        origin = manifest.backbone_version
    if origin == target_version:
        click.echo(f"Completing the transition to backbone v{target_version}")
    else:
        click.echo(f"Upgrading backbone: {origin} -> {target_version}")
    if dry_run:
        click.echo("  (dry-run — no changes will be written)")
    if manifest is None:
        click.echo(
            f"  The project has no manifest: the upgrade writes one at {target_version}, "
            "as first install does."
        )
    if completed is None:
        unreadable = manifest is not None and manifest.completed_version is not None
        why = (
            "The recorded states cannot be read (`backbone_version` or "
            "`completed_version` in .pkit/manifest.yaml is no version)"
            if unreadable
            else "No completed transition is recorded (`completed_version` in .pkit/manifest.yaml)"
        )
        click.echo(
            f"  {why}, so this project's backbone migration history is "
            f"unknown. Every backbone migration up to {target_version} runs once, and "
            "the completion recorded at the end keeps it from running again."
        )
    elif manifest is not None and manifest.transition_incomplete:
        click.echo(
            f"  The last transition is incomplete: completed_version is {completed}. "
            f"The backbone migrations run from {completed}."
        )
    click.echo()


def _report_component_moves(moves: Sequence[ComponentMove]) -> None:
    """Each component's move, in the report and the dry run alike (ADR-065 point 4):
    every registered adapter and shipped capability the transition records at the
    version the bundle ships. One the bundle ships older is not a move, and step 1
    refuses it."""
    up = [move for move in moves if not move.ahead]
    if not up:
        return
    click.echo("  Components")
    for move in up:
        origin = move.recorded if move.recorded is not None else "no recorded version"
        click.echo(f"    {move.kind} {move.name!r}: {origin} -> {move.bundled}")
    click.echo()


def refuse_components_bundled_older(
    moves: Sequence[ComponentMove], *, command: str | None = None
) -> None:
    """Refuse a transition whose bundle ships an adapter or a capability older than
    the project records (ADR-065 point 7).

    Copying it would move its recorded version down, under migrations that run
    forward only (COR-010). Skipping it would leave the project at two releases
    (COR-059 point 7). So the transition refuses in its step 1, before it writes
    anything. No flag overrides it, `--force` included. The message names each
    component, both versions, and a pkit whose bundle ships that version or
    newer.

    *command* is None for the transition of the backbone, `pkit upgrade`. For
    the transition of one capability it is that command as the operator runs
    it, `capabilities upgrade <name>`, as sync's guard takes it. That transition
    runs only where this pkit is the release the project records (sync's guard,
    point 7), so its remedy is `pkit upgrade`, run by a pkit whose bundle ships
    the capability at the recorded version or newer.
    """
    ahead = [move for move in moves if move.ahead]
    if not ahead:
        return
    backbone = command is None
    opening = "refusing to upgrade" if backbone else f"refusing to run `pkit {command}`"
    lines = [
        f"{opening}: this pkit's bundle ships {move.kind} {move.name!r} at "
        f"{move.bundled}, older than the {move.recorded} this project records."
        for move in ahead
    ]
    lines.append(
        "A transition never moves a recorded version down: migrations run forward only "
        "(COR-010, ADR-065 point 7). Nothing was written, and no flag overrides this refusal."
    )
    if backbone:
        lines.extend(
            f"Run the upgrade with a pkit whose bundle ships {move.kind} {move.name!r} at "
            f"{move.recorded} or newer."
            for move in ahead
        )
    else:
        lines.extend(
            f"Run `pkit upgrade` with a pkit whose bundle ships {move.kind} {move.name!r} at "
            f"{move.recorded} or newer: it moves the project to that pkit's release. "
            f"`pkit {command}` moves a capability only to the version the project's "
            "release ships."
            for move in ahead
        )
    raise click.ClickException("\n       ".join(lines))


@dataclass(frozen=True)
class CollisionAnswers:
    """What a person chose for each new collision in step 1 (ADR-065 point 6).

    *skips* holds the artefacts each capability's copy leaves out, by
    capability, and *overridden* the project's artefacts an override removes in
    step 2, before the copy.
    """

    skips: Mapping[str, tuple[tuple[str, str], ...]] = field(default_factory=lambda: {})
    overridden: tuple[Path, ...] = ()

    def in_force(self, plan: CapabilityPlan) -> CapabilityPlan:
        """*plan* with the skips in force: those its record holds and those chosen."""
        chosen = self.skips.get(plan.name)
        if not chosen or plan.record is None:
            return plan
        skipped = tuple(sorted({*plan.record.skipped, *chosen}))
        return replace(plan, record=replace(plan.record, skipped=skipped))


def _settle_new_collisions(
    target_root: Path, plans: Sequence[CapabilityPlan], *, dry_run: bool
) -> CollisionAnswers:
    """The collision flow of a transition of the backbone (ADR-065 point 6, COR-017).

    For each shipped capability the transition moves, the new collisions its
    bundled version brings (`capabilities.detect_new_collisions`): a name its
    installed copy holds, or its record skips, is not new, and the artefacts of
    the release, core's and each shipped capability's, are left out. Where a
    person can answer, standard input and standard output both terminals, it
    asks override, skip or inspect for each. With nobody to answer it refuses,
    before anything is written, and names a terminal re-run or a rename. A dry
    run lists each collision and asks nothing. No capability is held back, so
    the project stays at one release (COR-059 point 7).
    """
    from project_kit import capabilities as caps

    released = frozenset(
        plan.name
        for plan in plans
        if plan.source is not None and plan.disposition not in (INCUBATED, EXTERNAL)
    )
    found = [
        (plan.name, finding)
        for plan in plans
        if plan.disposition in COPIES and plan.source is not None
        for finding in caps.detect_new_collisions(
            target_root,
            plan.source,
            skipped=plan.record.skipped if plan.record is not None else (),
            released=released,
        )
    ]
    if not found:
        return CollisionAnswers()
    click.echo(f"  {len(found)} new naming collision(s) a capability's new version brings:")
    for name, finding in found:
        click.echo(
            f"    - capability {name!r}: {finding.artifact_kind} '{finding.artifact_name}' "
            f"collides with {finding.target_path.relative_to(target_root)}"
        )
    if dry_run:
        click.echo(
            "  The upgrade asks about each one where a person can answer (override, skip or "
            "inspect), and refuses without one, before it writes anything."
        )
        click.echo()
        return CollisionAnswers()
    if not _at_a_terminal():
        raise click.ClickException(
            "\n       ".join(
                [
                    "refusing to upgrade: a capability's new version brings a new naming "
                    "collision, and nobody can answer here: standard input and standard "
                    "output are not both terminals. Nothing was written.",
                    "Run `pkit upgrade` again at a terminal: it asks about each collision, "
                    "override, skip or inspect (COR-017).",
                    "Or rename the project's artefact, so the names no longer collide, and "
                    "run `pkit upgrade` again.",
                ]
            )
        )
    click.echo()
    skips: dict[str, list[tuple[str, str]]] = {}
    overridden: list[Path] = []
    for name, finding in found:
        choice = caps.resolve_collision_interactive(target_root, finding, capability=name)
        artefact = (finding.artifact_kind, finding.artifact_name)
        if choice == "skip":
            skips.setdefault(name, []).append(artefact)
        else:
            overridden.extend(caps.project_artefact_paths(target_root, *artefact))
    click.echo()
    return CollisionAnswers(
        skips={name: tuple(chosen) for name, chosen in skips.items()},
        overridden=tuple(overridden),
    )


def _record_new_skips(
    target_root: Path, moving: Sequence[CapabilityPlan], answers: CollisionAnswers
) -> None:
    """Record each skip chosen in step 1 in its capability's manifest, before the
    copy (ADR-065 point 6), so a transition a migration stops does not ask again.

    A capability with no readable version is recorded at its bundled version,
    which the transition records anyway, running none of its migrations (point
    2). A manifest that does not read as a mapping is left to the restamp, which
    replaces it and records the skips then.
    """
    from project_kit import capabilities as caps

    for plan in moving:
        if plan.name not in answers.skips or plan.record is None:
            continue
        written = caps.record_skips(
            target_root, plan.name, plan.record.skipped, version=plan.recorded or plan.bundled
        )
        where = "in its manifest" if written else "at its restamp: its manifest does not read"
        click.echo(
            f"  {'recorded':<12} the skips of capability {plan.name!r} {where}: "
            + ", ".join(f"{kind} '{name}'" for kind, name in answers.skips[plan.name])
        )


def dependencies_first(moving: Sequence[CapabilityPlan]) -> list[CapabilityPlan]:
    """*moving* ordered so that each capability follows those it requires (COR-030).

    A capability's requirements are its bundled version's `requires_capabilities`
    among the capabilities the transition moves, optional ones included. Each
    keeps its registry order otherwise. The walk follows registry order and each
    capability's requirements, and a cycle is broken at the first of its
    capabilities the walk reaches: the others in the cycle run before it.
    """
    by_name = {plan.name: plan for plan in moving}
    ordered: list[CapabilityPlan] = []
    placed: set[str] = set()
    visiting: set[str] = set()

    def place(plan: CapabilityPlan) -> None:
        if plan.name in placed or plan.name in visiting:
            return
        visiting.add(plan.name)
        requires = plan.source.package.requires_capabilities if plan.source is not None else ()
        for dependency in requires:
            required = by_name.get(dependency.name)
            if required is not None:
                place(required)
        visiting.discard(plan.name)
        placed.add(plan.name)
        ordered.append(plan)

    for plan in moving:
        place(plan)
    return ordered


def _render_runtime_ignore(target_root: Path) -> None:
    """Render `.pkit/.gitignore` from the declarations the target ships, right after
    propagation, so a migration reads the target's render (ADR-065 point 4, step 3).
    The derivable state renders it again after every migration."""
    from project_kit import visibility

    click.echo(visibility.render_runtime_ignore(target_root))


def _move_root_manifests(target_root: Path, plans: list[CapabilityPlan], *, dry_run: bool) -> None:
    """Move each capability manifest still at its root under its `project/`.

    A transition does it right after recording its target, before its copy,
    which would prune a manifest at the root (ADR-065 point 2). Sync never
    moves one: it skips such a capability. The root manifest replaces one
    already under `project/`, and the registry entry follows
    (`capabilities.move_capability_manifest`).
    """
    from project_kit import capabilities as caps
    from project_kit.manifest import capability_manifest_rel, capability_root_manifest_path

    for plan in plans:
        if plan.record is None or not plan.record.at_root:
            continue
        root = capability_root_manifest_path(target_root, plan.name).relative_to(target_root)
        dest = capability_manifest_rel(plan.name)
        move = f"the manifest of capability {plan.name!r}: {root} -> {dest}"
        if dry_run:
            click.echo(f"  would move {move}")
        elif caps.move_capability_manifest(target_root, plan.name):
            click.echo(f"  moved {move}")


def _migrate_capabilities(
    target_root: Path, plans: list[CapabilityPlan], moving: list[CapabilityPlan], *, dry_run: bool
) -> None:
    """Each copied capability's migrations, after its copy, then its restamp; and a
    line for each capability the transition leaves where it is (ADR-065 point 4,
    step 6).

    *moving* are the capabilities the propagation step copied, in the order
    their migrations run, dependencies first (`dependencies_first`,
    `capabilities.migrate_copied_capability`). A capability bundled older than
    its record never reaches here: step 1 refuses the transition. An incubated,
    externally sourced or no-longer-shipped capability keeps its own course.
    """
    from project_kit import capabilities as caps

    if not plans:
        return
    left = [plan for plan in plans if plan not in moving]
    click.echo()
    click.echo("  Capabilities")
    for plan in moving:
        if plan.source is None or plan.record is None:
            continue
        caps.migrate_copied_capability(target_root, plan.source, plan.record, dry_run=dry_run)
    for plan in left:
        name = repr(plan.name)
        if plan.disposition == ORPHAN:
            click.echo(
                f"    {'orphan':<12} {name} — no longer ships from source; "
                "leaving installed copy in place."
            )
        elif plan.disposition == INCUBATED:
            report_incubated_capability(plan)
        elif plan.disposition == EXTERNAL:
            click.echo(
                f"    {'skipped':<12} {name} — externally sourced: it moves by its pin "
                "(COR-041), never as shipped."
            )
        elif plan.disposition == UNVERSIONED:
            click.echo(
                f"    {'skipped':<12} {name} — the bundle's package.yaml names no version "
                f"({plan.bundled!r}), so there is nothing to move it to."
            )


def _report_adapters_to_register(
    target_root: Path, source_kit: Path, components: list[ComponentRegistryEntry]
) -> None:
    """The dry run's line for each adapter the bundle ships that the registry
    lacks, which the transition registers after its copy."""
    registered = {c.name for c in components if c.kind == "adapter"}
    adapters = source_kit / "adapters"
    if not adapters.is_dir():
        return
    for adapter_dir in sorted(p for p in adapters.iterdir() if p.is_dir()):
        if adapter_dir.name in registered:
            continue
        package = read_component_package(adapter_dir / "package.yaml")
        at = f" at {package[0]}" if package is not None else ""
        click.echo(f"  {'would register':<12} adapter {adapter_dir.name!r}{at}")


# --- Per-project version pin (ADR-049) -----------------------------------------


def _raise_pin_to(target_root: Path, target_version: str, dry_run: bool) -> None:
    """Flip `.pkit/version-pin` forward to `target_version` (ADR-049 pin raise).

    Writes only when the pin actually moves — an idempotent no-op when the pin is
    already at the target. The write is atomic (`write_version_pin`) and, by
    call-site placement, happens LAST in an upgrade: after content sync and
    migrations, so a failed upgrade leaves the project consistently at its old
    pin rather than advancing past content that never landed.
    """
    pin_path = pin_file_path(target_root)
    current_pin = read_version_pin(target_root)
    if current_pin == target_version:
        return
    prior = current_pin if current_pin is not None else "(unpinned)"
    if dry_run:
        click.echo(f"  would raise pin: {prior} -> {target_version} ({pin_path.name})")
        return
    write_version_pin(target_root, target_version)
    click.echo(f"  pin raised: {prior} -> {target_version} (.pkit/version-pin)")


def _pin_after_upgrade(target_root: Path, version: str, dry_run: bool) -> None:
    """Pin-by-default on an un-pinned project: freeze the pin at the just-synced
    version (ADR-064).

    Called when the project was un-pinned, the upgrade succeeded, and `--no-pin`
    was not passed — at the same LAST position as the pinned pin-raise, so a failed
    sync (which raises before this point) never leaves a pin without matching
    content. `version` is the local content version the sync targeted, so this
    needs no `git ls-remote` lookup and works offline. Delegates the write to
    `freeze_pin` (the same validated directive path `pkit pin` uses); honours
    `--dry-run`.
    """
    if dry_run:
        click.echo(f"  would pin project at {version} (.pkit/version-pin; --no-pin to skip)")
        return
    freeze_pin(target_root, version)


def freeze_pin(target_root: Path, version: str) -> None:
    """Write the `.pkit/version-pin` directive at `version`, in place, with no content sync.

    The freeze gesture: lock the project at a version without moving it. Backs
    `pkit pin` with no argument (freeze at the current content version, via
    `freeze_at_content`) and `pkit pin <version>` when the target equals the
    current content version (ADR-049). `version` is always a bare
    `MAJOR.MINOR.PATCH` semver — the callers normalise and validate before this
    point (`_normalize_pin_version`), so the router can always route it. The
    write is atomic (`write_version_pin`)."""
    pin_path = pin_file_path(target_root)
    write_version_pin(target_root, version)
    click.echo(f"Pinned project-kit to {version} ({pin_path.relative_to(target_root)}).")


def freeze_at_content(target_root: Path) -> None:
    """No-arg `pkit pin`: freeze the project at its current CONTENT version (ADR-049).

    Freezes at `.pkit/manifest.yaml`'s `backbone_version` — the content the
    project last synced — *not* the running binary's version. When the installed
    tool is ahead of the project's synced content, freezing at the binary version
    would bake in a code-vs-content mismatch; freezing at content keeps the
    version⟺content invariant intact. Refuses when the manifest is absent (there
    is no recorded content version to pin against), and in the methodology's
    source repository (`_refuse_pin_in_source`).
    """
    _refuse_pin_in_source(target_root)
    current = _require_backbone_version(target_root)
    freeze_pin(target_root, current)


def _refuse_pin_in_source(target_root: Path) -> None:
    """Refuse `pkit pin` in the methodology's source repository (ADR-059; #1070).

    A pin is meaningless there. The router's route 1 execs the checkout's own
    dispatcher before any pin is read, and where it cannot, it falls back to the
    running binary, never to a pin (ADR-039). `pin` normally runs under route 1,
    so sync's test recognises the source. In the gap only the markers do, and a
    pin is as meaningless there, while `pin <newer>` would run a release's
    `upgrade` over the checkout. So either test refuses, before anything is
    read or written.
    """
    if not (is_self_host(target_root, find_source_kit()) or is_source_checkout(target_root)):
        return
    pin_path = pin_file_path(target_root).relative_to(target_root)
    raise click.ClickException(
        f"refusing to pin {target_root}: it is the methodology's source repository, and "
        "a pin is meaningless in the methodology's source: route 1 runs its own code "
        "before any pin is read.\n"
        "       Here the router runs this checkout's own dispatcher (or, when it cannot, "
        f"the running binary) and never reads {pin_path} (ADR-039, ADR-059). Nothing "
        "was written.\n"
        "       To move this checkout to another release, update it with git: its "
        ".pkit/ moves with its code."
    )


def reconcile_pin(target_root: Path, version: str, *, force: bool = False) -> None:
    """Set the pin at `version`, reconciling content per the target-vs-current order.

    `pkit pin <version>` normalises and validates the token first
    (`_normalize_pin_version`: a bare `MAJOR.MINOR.PATCH` semver, a single leading
    `v` stripped), then compares it against the project's current content version
    (`.pkit/manifest.yaml`'s `backbone_version`) and dispatches on the ordering
    (ADR-049):

    - **equal** → freeze in place (write the pin, no content sync);
    - **newer** → reconcile content forward to the target under the target's own
      code (via the router bypass), then flip the pin last, atomically;
    - **older** → HARD REFUSE — pkit migrations are forward-only (COR-010), so
      there is no safe downgrade path; nothing is written and no content is
      touched (`git checkout` is the rollback route).

    A version-only token is required: branch names, commit shas, and pre-release /
    build-metadata forms are refused at the boundary, because the router's route-2
    can only route a bare `v<semver>` tag (branch/sha pins need a router change and
    are deferred). A project with no `.pkit/manifest.yaml` (no recorded content
    version) is refused too — there is nothing to order the target against — and
    so is the methodology's source repository (`_refuse_pin_in_source`), first,
    so a newer target never bootstraps a release's `upgrade` over it.

    *force* (`pkit pin <newer> --force`) is passed to the target's `upgrade`,
    where it overrides the two warnings of the dependency gates and nothing else
    (ADR-065 points 6 and 9). The refusal of an older version takes no override.
    """
    _refuse_pin_in_source(target_root)
    normalized = _normalize_pin_version(version)
    current = _require_backbone_version(target_root)
    order = _pin_order(normalized, current)

    if order == "older":
        raise click.ClickException(_downgrade_refusal(normalized, current))

    if order == "equal":
        freeze_pin(target_root, normalized)
        return

    # newer → reconcile content forward, then flip the pin LAST, so a failed
    # reconcile never advances the pin past content that never landed.
    click.echo(
        f"Pinning forward to {normalized} (current content {current}): reconciling "
        "content up to the target first."
    )
    _advance_pin_to(target_root, normalized, force=force)


# Accepted pin token: a bare MAJOR.MINOR.PATCH semver. Deliberately stricter than
# `packaging.version.Version` (which also parses `1.2`, `1.2.3rc1`, `1.2.3+build`)
# — the router's route-2 pins by the git tag `v<token>`, and only a plain
# three-part release tag is guaranteed to resolve. Pre-release / build-metadata /
# branch / sha pins need a router change and are deferred (ADR-049).
_PIN_SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")


def _normalize_pin_version(token: str) -> str:
    """Normalise + validate a `pkit pin <token>` argument to a bare semver (ADR-049).

    Strips a single leading `v` (`v1.145.0` and `1.145.0` both normalise to the
    bare `1.145.0` that gets ordered, written, AND routed), then requires a plain
    `MAJOR.MINOR.PATCH` semver. Refuses anything else — branch names, commit shas,
    pre-release / build-metadata forms — because the router can only route a bare
    `v<semver>` tag. Raises `click.ClickException` (nothing is written) on refusal.
    """
    candidate = token[1:] if token.startswith("v") else token
    if not _PIN_SEMVER_RE.match(candidate):
        raise click.ClickException(
            f"pkit pin takes a version like 1.145.0 (got {token!r}); branch and "
            "commit pins aren't supported yet."
        )
    return candidate


def _require_backbone_version(target_root: Path) -> str:
    """Read the project's recorded content version, or refuse when the manifest is absent.

    Both `pkit pin` gestures need `.pkit/manifest.yaml`'s `backbone_version` — the
    no-arg freeze pins *at* it, and `pin <version>` orders the target *against* it.
    Absent, there is no recorded content version, so both hard-refuse and name
    `pkit upgrade`, which writes the manifest at its target and replays every
    backbone migration once (ADR-065 point 8). Raises `click.ClickException`;
    nothing is written.
    """
    manifest = read_backbone_manifest(target_root)
    if manifest is None:
        raise click.ClickException(
            f"{target_root}/.pkit/manifest.yaml is missing — pkit has no record of "
            "this project's content version to pin against. Run 'pkit upgrade', which "
            "writes the manifest at its version and runs every backbone migration once, "
            "then retry."
        )
    return manifest.backbone_version


def reconcile_forward_via_target(
    target_root: Path, target: str, *, dry_run: bool = False, force: bool = False
) -> None:
    """Reconcile content forward to a NEWER `target` using that version's own code.

    Syncing to a newer version needs that version's code and bundled content,
    which the currently-installed tool does not carry. Bootstrap the target wheel
    with `uvx project-kit@v<target>` and run its `upgrade` there — under the
    router's PKIT_NO_ROUTE bypass, so the bootstrapped process runs self instead
    of routing back through this project's (older) pin. That upgrade syncs content
    and runs the forward migrations. Raises ClickException on a non-zero exit so
    the caller aborts BEFORE advancing the pin — the pin never moves past content
    that failed to land (ADR-049). Shares the router's route-2 uvx machinery
    (`run_bypassed`) rather than duplicating the invocation.

    *dry_run* and *force* are passed to the target's upgrade (ADR-065 point 9):
    a dry run lists what the target's upgrade would do, and `--force` overrides
    that upgrade's two dependency-gate warnings and nothing else (point 6).
    """
    argv = ["upgrade", *(["--dry-run"] if dry_run else []), *(["--force"] if force else [])]
    returncode = run_bypassed(target, argv)
    if returncode != 0:
        raise click.ClickException(
            f"reconciling content forward to {target} failed: the bootstrapped "
            f"`uvx project-kit@v{target} {' '.join(argv)}` exited {returncode}. The pin was "
            "not advanced; resolve the error reported above and retry."
        )


def _pin_order(target: str, current: str) -> str:
    """Order `target` against `current` for the pin guard: equal | newer | older.

    `target` is already a validated bare semver (`_normalize_pin_version`);
    `current` is the project's recorded `backbone_version`. A malformed recorded
    version (a corrupt manifest) is refused cleanly rather than crashing the
    comparison (ADR-049)."""
    parsed_target = Version(target)
    try:
        parsed_current = Version(current)
    except InvalidVersion as exc:
        raise click.ClickException(
            f"this project's recorded content version {current!r} is not valid "
            "semver — the manifest may be corrupt. Run 'pkit upgrade', which records "
            "its own version over it, then retry."
        ) from exc
    if parsed_target == parsed_current:
        return "equal"
    return "newer" if parsed_target > parsed_current else "older"


def _downgrade_refusal(target: str, current: str) -> str:
    """The refusal message for a downgrade pin (ADR-049 + COR-010).

    pkit migrations are forward-only, so there is no safe content path back to an
    earlier version; rolling back is a git operation, which restores kit-owned
    *and* project-owned state together — something a forward-only sync cannot."""
    return (
        f"refusing to pin {target}: it is OLDER than this project's current content "
        f"({current}), and pkit cannot safely downgrade — its migrations are "
        "forward-only (COR-010), so there is no reconcile path back to an earlier "
        "version. Nothing was written and no content was touched.\n"
        "To roll this project back, `git checkout` the `.pkit/` tree at a commit "
        "that carried the earlier version:\n"
        "    git checkout <ref> -- .pkit/\n"
        "git restores kit-owned and project-owned state together, atomically — "
        "which a forward-only content sync cannot do. Note this also reverts "
        f"`.pkit/version-pin` itself (the file you are setting), and it only "
        "restores a state that already exists in history."
    )


def _advance_pin_to(target_root: Path, target: str, *, force: bool = False) -> None:
    """Reconcile content forward to `target`, then flip the pin LAST (ADR-049).

    The shared "raise" shape both pin-forward gestures use (COR-007): `pkit pin
    <newer>` and `pkit upgrade` in a pinned project. It runs the *target* version's
    own code via the router bypass to sync content and forward-migrate
    (`reconcile_forward_via_target`), and only on its success flips
    `.pkit/version-pin` to `target` — so the pin never advances past content that
    failed to land.

    The explicit `_raise_pin_to` here makes the flip whatever the target's code
    does. When the project had no pin yet (first-time `pkit pin <newer>`), the
    bootstrapped upgrade sees no pin: a target that pins by default (ADR-064)
    pins the project at the target itself, so this flip is an idempotent no-op,
    and an older target writes no pin, so this flip is the load-bearing write.
    When the project *was* already pinned (the `pkit upgrade` raise), the
    bootstrapped upgrade flips the pin from inside its own OUTER path, so this
    flip is a benign idempotent no-op. *force* passes to the target's upgrade
    (ADR-065 point 9).
    """
    reconcile_forward_via_target(target_root, target, force=force)
    _raise_pin_to(target_root, target, dry_run=False)


def runs_at_its_pin(pin: str) -> bool:
    """Whether this upgrade runs under its pin's code, with no other code asked
    for (ADR-065 point 9).

    Two runs do: the routed child, which the router re-execs into the pin
    (`PKIT_ROUTED`), and the installed pkit the router runs in process because
    it is the pin, which carries no mark of a routed child. A run under a
    deliberate bypass (`PKIT_NO_ROUTE`) is the code an operator or a raise
    asked for, so it is neither.
    """
    if is_route_bypassed(os.environ):
        return False
    return is_routed_child(os.environ) or pin == running_version()


def _auto_advance_pinned(
    target_root: Path, source_kit: Path, current_pin: str, *, dry_run: bool, force: bool
) -> bool:
    """The checks of `pkit upgrade` under its pin's code, in ADR-065 point 9's order.

    Run by the routed child, or by the installed pkit that is the pin
    (`runs_at_its_pin`). It cannot mutate the global tool, and needs not: it
    resolves the latest release (ADR-063 point 1's `git ls-remote` check), then
    checks three cases, in this order:

    1. **A newer latest release that resolves:** it hands over to the latest
       through the router's bypass, and returns True. The latest's upgrade runs
       from the recorded states, so it finishes the pin's own interrupted
       transition on the way. `--dry-run` and `--force` pass to it, and the pin
       flips last (`_advance_pin_to`).
    2. **A recorded state ahead of the pin,** in `backbone_version` or
       `completed_version`: the older-direction check refuses, before anything
       is written. Offline its message names reconnecting, since the latest's
       upgrade finishes the interrupted raise. Online no release is newer than
       the pin, and the message names #1212's remedies.
    3. **Otherwise,** at the latest, ahead of it or offline: it returns False,
       and the caller runs the transition to the pin in its own process. A
       project already current at its pin returns before step 1 (point 4).

    A pin that is no version cannot be ordered against the latest release, so
    it hands over to none.
    """
    latest = _latest_released_version()
    if latest is None:
        click.secho(
            "warning: could not check for the latest pkit release "
            f"(`git ls-remote {DISTRIBUTION_GIT_URL}` failed — offline, missing "
            "credentials, git unavailable, or timed out), so this upgrade hands over to "
            f"no newer release. The pin stays at {current_pin}; re-run when the release "
            "source is reachable to move past it.",
            err=True,
            fg="yellow",
        )
    else:
        try:
            pinned_version = Version(current_pin)
        except InvalidVersion:
            pinned_version = None
        if pinned_version is None:
            click.secho(
                f"warning: this project's pin ({current_pin!r}) is not valid semver, so "
                f"`pkit upgrade` cannot order it against the latest release (v{latest}) "
                "and hands over to none.",
                err=True,
                fg="yellow",
            )
        elif latest > pinned_version:
            _hand_over_to_latest(target_root, current_pin, str(latest), dry_run, force)
            return True
        elif latest == pinned_version:
            click.echo(f"Already at the latest pkit release (v{latest}); the pin stays.")
        else:
            click.echo(
                f"This project is pinned to {current_pin}, which is AHEAD of the latest "
                f"pkit release (v{latest}); the pin stays (pkit does not downgrade a pin)."
            )

    # Case 2: a recorded state ahead of the pin, before the child's own
    # transition writes anything, which would take it down to the pin.
    refuse_if_source_kit_incomplete(source_kit)
    refuse_content_downgrade(target_root, source_kit, command="upgrade", offline=latest is None)
    return False


def _hand_over_to_latest(
    target_root: Path, current_pin: str, target: str, dry_run: bool, force: bool
) -> None:
    """Hand a pinned upgrade over to the newer latest release *target*, through the
    router's bypass, and flip the pin last (ADR-049, ADR-065 point 9).

    A dry run runs the target's upgrade with `--dry-run`, so it lists what that
    upgrade would do, the pin it would raise included, and writes no pin.
    """
    if dry_run:
        click.echo(
            f"  (dry-run) the latest pkit release, v{target}, is newer than the pin, "
            f"{current_pin}: its own upgrade runs with --dry-run, through the router's "
            "bypass."
        )
        reconcile_forward_via_target(target_root, target, dry_run=True, force=force)
        return
    click.echo(
        f"Raising the pin: {current_pin} -> {target} (latest pkit release); "
        "reconciling content forward under the target's own code first."
    )
    _advance_pin_to(target_root, target, force=force)


def refuse_under_routers_fallback(target_root: Path) -> None:
    """Refuse an upgrade the router's fallback runs (ADR-065 point 9).

    When the router cannot fetch a project's pin, it runs the installed pkit
    instead and sets its fallback mark. The test is the mark without
    `PKIT_NO_ROUTE`, which marks a deliberate bypass, by a raise or by an
    operator (`router.fell_back_from_pin`). Under the fallback the versions can
    look fine, yet an upgrade would move the project and its pin to the
    installed pkit's version, a release it did not resolve (ADR-049 point 3).
    So it refuses in both directions, before the tool step and before anything
    is written, under `--dry-run` too, and no flag overrides it. Its message
    names the fallback's remedies (point 8).
    """
    fallback_pin = unresolved_pin(os.environ)
    if fallback_pin is None:
        return
    pin = read_version_pin(target_root) or fallback_pin
    running = running_version()
    lines = [
        f"refusing to run `pkit upgrade`: this project pins pkit {pin}, which the router "
        f"could not fetch, so this run is pkit {running}, not the pin.",
        "A pinned project's upgrade runs under its pin's code, which finishes the pin and "
        f"moves on only to a newer release it resolves (ADR-065 point 9). Run by pkit "
        f"{running}, it would move the project and its pin to {running} instead. Nothing "
        "was written, and no flag overrides this refusal.",
        *fallback_remedies("upgrade", pin),
    ]
    raise click.ClickException("\n       ".join(lines))


# --- Tool-staleness detection (ADR-063) ----------------------------------------

# Bounded so an unreachable release source (offline, DNS black-hole) can't hang
# `pkit upgrade`. The check is best-effort; a timeout degrades to a warning.
_LS_REMOTE_TIMEOUT_SECONDS = 5.0


#: Guard env var: set on the re-exec'd child after a self-update, so the child
#: never attempts a second self-update (defence against a re-exec loop, on top of
#: the version comparison that already no-ops once the tool is current).
_SELF_UPDATED_ENV = "PKIT_SELF_UPDATED"

#: The directory `uv tool install` gives pkit's environment under `uv tool dir`:
#: the distribution's name.
_TOOL_ENVIRONMENT = "project-kit"

#: Bounded like the release lookup: `uv tool dir` is local and quick, but asking
#: it must never hang `pkit upgrade`. A timeout answers "not the installed tool".
_UV_TOOL_DIR_TIMEOUT_SECONDS = 5.0


def run_tool_update(dry_run: bool = False, self_update: bool = True) -> None:
    """`pkit upgrade` run **outside any project**: update the global tool only.

    The "just update my tool" case (ADR-063 point 5) — there is no project
    content to sync, so this handles the tool axis alone and reports the result,
    instead of erroring on a missing project/manifest.
    """
    if is_route_bypassed(os.environ):
        return
    _maybe_self_update_tool(self_update=self_update, dry_run=dry_run)


def _maybe_self_update_tool(*, self_update: bool, dry_run: bool) -> None:
    """Detect a newer released pkit tool and **act** on it (ADR-063):
    self-update the global binary and re-exec, or degrade to instruct.

    - **Never in a source checkout (point 5).** Reinstalling a released tag over
      a source checkout's working-tree code is nonsensical, and this step is
      never reached there: `run_upgrade`'s self-host branch returns under the
      checkout's own code, and its refusal to propagate over the source raises
      under any other code (ADR-059; #1070) — both before this step. Run outside
      a project (`run_tool_update`), there is no checkout.
    - **Best-effort detection (point 1).** Any lookup failure (offline, no
      credentials, `git` absent, timeout) warns and returns; the caller proceeds
      unchanged.
    - **Act (point 2).** When the tool is behind and self-update is allowed
      (`self_update`, an interactive TTY, not a dry-run, not the guarded re-exec
      child, and the running pkit is the installed tool), run
      `uv tool install --force …@v<latest>` and **re-exec** the same
      command under the new version (never returns on success). Pin-by-default
      (ADR-064) keeps a pinned project at its pin while the router can fetch it;
      the install still moves every un-pinned project on the machine.
    - **Instruct (point 3).** Otherwise (non-interactive, `--no-self-update`, a
      failed/declined install, a dry-run, or a pkit that is not the installed
      tool) fall back to printing the exact command and go on under the
      running pkit. A failed lookup or install never fails `pkit upgrade`. A
      failed hand-over after a successful install stops it before it syncs or
      pins (point 3).
    """
    latest = _latest_released_version()
    if latest is None:
        click.echo()
        click.secho(
            "warning: could not check for a newer pkit tool "
            f"(`git ls-remote {DISTRIBUTION_GIT_URL}` failed — offline, missing "
            "credentials, git unavailable, or timed out). Continuing; your "
            "installed tool may be behind.",
            err=True,
            fg="yellow",
        )
        return

    try:
        running = Version(running_version())
    except InvalidVersion:
        # Our own version string is unparseable — we can't compare, so degrade
        # like a failed lookup rather than printing a misleading instruction.
        return

    if running >= latest:
        click.echo(f"pkit tool is current (v{running}).")
        return

    # Stale, and this run is the one a successful install handed the upgrade
    # to: it carries the guard and the terminal the install ran at. Not the
    # installed tool: the PATH found another, older `pkit` first, and going on
    # would bring the project to its bundle and pin it there (#1473). The
    # installed tool: the release just installed reports a version below its
    # tag, or a release landed during the install, so it carries on, and the
    # guard keeps it from installing.
    handed_over = os.environ.get(_SELF_UPDATED_ENV) == "1" and _at_a_terminal()
    if self_update and not dry_run and handed_over and not _running_is_installed_tool():
        _stop_failed_hand_over(
            f"a newer pkit tool (v{latest}) was installed, but the `pkit` your PATH "
            f"runs first is v{running}, from {sys.prefix}"
        )

    # Stale. Act when allowed and this pkit is the installed tool; otherwise
    # instruct and go on under this pkit. The installed-tool check asks `uv`, so
    # it comes after the cheaper checks that already rule the install out.
    if self_update and dry_run:
        if _running_is_installed_tool():
            click.echo()
            click.echo(
                f"A newer pkit tool is available: v{latest} (you are running "
                f"v{running}). (dry-run) would run `uv tool install --force "
                f"{DISTRIBUTION_GIT_URL}@v{latest}` and re-run this upgrade."
            )
            return
        _report_not_the_installed_tool()
    elif self_update and _self_update_allowed():
        if not _running_is_installed_tool():
            _report_not_the_installed_tool()
        elif _self_update_tool(latest):
            _reexec_after_self_update(latest)  # never returns
        # Not the installed tool, or the install failed/declined → instruct.

    _instruct_tool_update(latest, running)


def _self_update_allowed() -> bool:
    """True iff we may auto-run the tool self-update: an interactive TTY and not
    the guarded re-exec child. Non-interactive (CI / piped) callers degrade to
    instruct so a network install is never forced under automation."""
    if os.environ.get(_SELF_UPDATED_ENV) == "1":
        return False
    return _at_a_terminal()


def _at_a_terminal() -> bool:
    """True iff both standard input and standard output are terminals."""
    return _is_tty(sys.stdin) and _is_tty(sys.stdout)


def _is_tty(stream: object) -> bool:
    """A stream is interactive only if it exists, is open, and is a terminal.
    An absent (`None`, fd closed at start) or closed stream is non-interactive,
    not a crash -- the same guard `pkit init` uses (#913)."""
    if stream is None:
        return False
    try:
        return bool(stream.isatty())
    except (ValueError, OSError):
        return False


def _self_update_tool(latest: Version) -> bool:
    """Run `uv tool install --force <dist>@v<latest>` to update the global binary.
    Returns True on success; False on any failure (caller degrades to instruct).
    A global-binary mutation the sandbox may gate — a decline surfaces as non-zero
    and degrades, never bricks."""
    click.echo(f"Updating the pkit tool to v{latest} …")
    cmd = ["uv", "tool", "install", "--force", f"{DISTRIBUTION_GIT_URL}@v{latest}"]
    try:
        proc = subprocess.run(cmd, check=False)
    except OSError:
        return False
    return proc.returncode == 0


def _running_is_installed_tool() -> bool:
    """True only when this process runs from the environment `uv tool install`
    made for pkit: `sys.prefix` is `<uv tool dir>/project-kit`.

    That environment is the tool the install replaces, and the `pkit` the
    hand-over expects to find. A `uvx` run that uv serves from its cache, a
    `uv run` from a project's virtual environment, and a pip install run from
    elsewhere. None of them is that tool, so the upgrade must not replace the
    tool and hand itself to another pkit (#1473). A `uvx` run that uv serves
    from the installed tool's environment, as it does when that tool meets the
    request (not under `--isolated`), is that tool, and is treated as it. Any
    doubt answers False: `uv` missing, failing or slow, an answer that is not
    one path, or a path that cannot be read or resolved. False costs only the
    printed command.
    """
    try:
        completed = subprocess.run(
            ["uv", "tool", "dir"],
            capture_output=True,
            text=True,
            timeout=_UV_TOOL_DIR_TIMEOUT_SECONDS,
        )
    except (OSError, ValueError, subprocess.SubprocessError):
        # ValueError covers output that does not decode as text.
        return False
    tool_dir = completed.stdout.strip()
    if completed.returncode != 0 or not tool_dir or "\n" in tool_dir:
        return False
    try:
        return Path(sys.prefix).resolve() == (Path(tool_dir) / _TOOL_ENVIRONMENT).resolve()
    except (OSError, ValueError, RuntimeError):
        # ValueError covers a path with a NUL byte; RuntimeError a symlink loop.
        return False


def _report_not_the_installed_tool() -> None:
    """Say why a stale pkit that could otherwise install does not (#1473)."""
    click.echo()
    click.echo(
        f"This pkit is not the `uv`-installed tool (it runs from {sys.prefix}), so "
        "the upgrade installs nothing and stays with this pkit."
    )


def _rerun_command() -> list[str]:
    """The command the hand-over runs, and the one a stopped upgrade names."""
    return ["pkit", *sys.argv[1:]]


def _stop_failed_hand_over(what_happened: str) -> NoReturn:
    """Stop the upgrade after a successful install whose hand-over failed.

    Raised before the project's own steps, so nothing is synced, migrated or
    pinned: going on under this older pkit would pin the project at its release
    (#1473). Names the command to re-run once the new tool is the `pkit` the
    PATH finds.
    """
    raise click.ClickException(
        f"{what_happened}, so the upgrade stopped before it synced or pinned "
        "anything. Make sure uv's tool directory (`uv tool dir --bin`) comes first "
        "on your PATH (`uv tool update-shell` adds it), then re-run:\n\n"
        f"    {shlex.join(_rerun_command())}"
    )


def _reexec_after_self_update(latest: Version) -> NoReturn:
    """Re-exec the same `pkit` command under the freshly-installed tool, so the
    content sync + pin run under the new bundle — one seamless upgrade. Sets the
    guard env so the child never self-updates again. Replaces the process image
    on success. When `pkit` cannot be started, it stops the upgrade before the
    project's steps rather than going on under the old pkit (#1473). Never
    returns."""
    click.echo("Re-running the upgrade under the new version …")
    env = {**os.environ, _SELF_UPDATED_ENV: "1"}
    try:
        os.execvpe("pkit", _rerun_command(), env)
    except OSError as exc:
        _stop_failed_hand_over(
            f"pkit v{latest} was installed, but `pkit` could not be started to "
            f"finish the upgrade under it ({exc.strerror or exc})"
        )


def _instruct_tool_update(latest: Version, running: Version) -> None:
    """Print the exact manual update command (ADR-063 point 3 — the fallback)."""
    click.echo()
    click.echo(f"A newer pkit tool is available: v{latest} (you are running v{running}).")
    click.echo("Update the tool, then re-run this command:")
    click.echo()
    click.echo(f"    uv tool install --force {DISTRIBUTION_GIT_URL}@v{latest}")
    click.echo("    pkit upgrade")


def _latest_released_version() -> Version | None:
    """Query the distribution source for the highest release tag, pre-releases skipped.

    Best-effort per ADR-063 point 1: returns None on *any* failure — `git` missing
    (`OSError`), the source unreachable (non-zero exit), a bounded-timeout expiry,
    or output with no release tag (`_max_released_tag`). The caller degrades loudly. Uses
    the same compiled distribution URL the router pins against (`router`), so tool
    detection and route-2 pinning share one source of truth.
    """
    try:
        completed = subprocess.run(
            ["git", "ls-remote", "--tags", DISTRIBUTION_GIT_URL],
            capture_output=True,
            text=True,
            timeout=_LS_REMOTE_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.SubprocessError):
        # OSError: git not on PATH. SubprocessError covers TimeoutExpired et al.
        return None
    if completed.returncode != 0:
        return None
    return _max_released_tag(completed.stdout)


def _max_released_tag(ls_remote_output: str) -> Version | None:
    """Pick the highest release tag from `git ls-remote --tags` output.

    Each line is `<sha>\trefs/tags/<tag>`. Annotated tags also emit a
    dereferenced `<tag>^{}` peel line; the `^{}` suffix is stripped so both
    resolve to the same version. Only a `v` followed by a release version
    counts, tested as the release step tests a floor
    (`versioning.is_release_version`): `major.minor.patch`, no part padded by
    a leading zero. Every pre-release and dev release is skipped (`v2.0.0rc1`,
    `v2.0.0.dev1`), even one above the latest release, as is any other tag (a
    non-release tag, a malformed ref). So what the tool step installs and a
    pinned raise writes is a release `pkit pin` accepts. Returns None when no
    release tag is present.
    """
    versions: list[Version] = []
    for line in ls_remote_output.splitlines():
        ref = line.rpartition("refs/tags/")[2].strip()
        ref = ref.removesuffix("^{}")
        if ref.startswith("v") and is_release_version(ref[1:]):
            versions.append(Version(ref[1:]))
    return max(versions) if versions else None


def _resolve_compatibility(
    components: list[ComponentRegistryEntry],
    target_root: Path,
    source_kit: Path,
    target_version: str,
) -> None:
    """Check every component's post-upgrade `requires_backbone` accepts the target.

    For each installed component, reads the `requires_backbone` range from the
    **source** `package.yaml` (the version it becomes after the upgrade's copy),
    falling back to the installed copy for components the source no longer ships
    (see `_resolve_package_yaml`). The file is read as the wiring resolver reads
    a package (`connections.read_package`), so the range is found however it is
    quoted, and compared through the resolver's one relation
    (`connections.range_admits`). Raises `click.ClickException` on conflict so
    the caller surfaces it before any state changes.

    Compatibility resolution in step 1 (ADR-065 point 4). The dependency gates
    between capabilities follow it (`_check_capability_dep_conflicts_for_upgrade`).
    """
    from project_kit.connections import REQUIRES_BACKBONE_KEY, range_admits, read_package

    try:
        Version(target_version)
    except InvalidVersion as exc:
        raise click.ClickException(
            f"source kit version {target_version!r} is not valid semver"
        ) from exc

    conflicts: list[str] = []
    for entry in components:
        package_yaml = _resolve_package_yaml(target_root, source_kit, entry)
        if package_yaml is None:
            continue
        # The package read as the resolver reads it — any YAML quoting — and the
        # range compared through its one relation, as `pkit validate` compares it.
        package = read_package(package_yaml) or {}
        required = package.get(REQUIRES_BACKBONE_KEY)
        if range_admits(required, target_version) is False:
            conflicts.append(
                f"  {entry.kind} '{entry.name}' requires backbone {required}; "
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
    upgrade's propagation step copies kit-shipped content (COR-001 / COR-017).
    Reading the *installed* copy would consult the stale, about-to-be-replaced
    `requires_backbone` ceiling and wrongly refuse every adopter that is a minor
    behind (the source ceiling auto-broadens on each backbone bump, so the
    installed copy always lags the target). Falls back to the installed copy for
    a component the source no longer ships — the copy does not reach it, so
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


def _run_backbone_migrations(
    target_root: Path,
    source_kit: Path,
    completed_version: str | None,
    target_version: str,
    dry_run: bool,
) -> None:
    """Run the backbone's migration window, from the last completed transition.

    Per COR-010, backbone migrations live at
    `.pkit/migrations/backbone/<X.Y.0>/<NNN>-<slug>.sh`. They're
    kit-shipped content the propagation step copies; by the time this runs,
    after the propagation, they're present in the target tree. A dry run copies
    nothing, so it reads the same scripts from the running pkit's bundle.

    Window: every minor version strictly above `completed_version` and
    at-or-below `target_version` (ADR-065 point 3). A missing completion has no
    lower bound: every backbone migration up to the target runs once, the
    replay (point 5), which the report names and lists. Halts on the first
    non-zero exit, so the completion is not recorded and the next upgrade runs
    the migration again.

    Scope ordering (manifest-schema → structural → resource) per COR-010
    is *within* a version dir, expressed via `NNN-*.sh` filename order
    — author by convention rather than declared metadata for now.
    """
    base = source_kit if dry_run else target_root / ".pkit"
    migrations_root = base / "migrations" / "backbone"
    scripts = pending_migration_scripts(migrations_root, completed_version, target_version)
    lower = completed_version or "no completed transition"

    if not scripts:
        click.echo(f"  no backbone migrations to run between {lower} and {target_version}")
        return

    replay = "" if completed_version is not None else ", the replay"
    if dry_run:
        report_pending_migrations(
            scripts,
            label=f"backbone{replay}",
            installed_version=lower,
            target_version=target_version,
            dry_run=True,
            label_rel_to=migrations_root,
        )
        return

    click.echo(
        f"  running {len(scripts)} backbone migration(s){replay} ({lower} -> v{target_version})"
    )
    execute_migration_scripts(
        scripts,
        target_root,
        label="backbone",
        label_rel_to=migrations_root,
    )


def _run_component_migrations(
    target_root: Path,
    source_kit: Path,
    components: list[ComponentRegistryEntry],
    dry_run: bool,
) -> None:
    """Run each registered adapter's migrations, and record it at its bundled version.

    Capabilities are not handled here: the transition runs each capability's
    migrations after its copy (`_migrate_capabilities`).

    For each registered adapter the running pkit's bundle ships (ADR-065
    point 2):
    - **No manifest,** or one that records no version: it reads as at the
      backbone. It is recorded at the version the bundle ships, and runs no
      migration.
    - **A manifest:** the scripts in its window run, read from the running
      pkit's bundle, as a capability's are: the adapter copy carries no
      `migrations/` (ADR-065 point 4, step 5). It is then recorded at the
      bundled version, with no script in the window too, so a record never
      stays behind the content.

    An adapter the bundle ships older than its record never reaches here: step
    1 refuses the transition (`refuse_components_bundled_older`).
    """
    eligible = [c for c in components if c.kind == "adapter"]
    if not eligible:
        return

    ran = 0
    for entry in eligible:
        package = read_component_package(_bundled_adapter_package(source_kit, entry.name))
        if package is None or as_recorded_version(package[0]) is None:
            # The bundle no longer ships it, or names no version: nothing to move it to.
            continue
        bundled = package[0]
        installed_manifest_path = target_root / entry.manifest
        label = f"{entry.kind} {entry.name!r}"

        installed_manifest = _read_adapter_manifest(target_root, entry)
        if installed_manifest is None:
            verb = "would record" if dry_run else "recorded"
            if not dry_run:
                record_adapter_version(
                    target_root,
                    entry.name,
                    target_root / ".pkit" / "adapters" / entry.name / "package.yaml",
                    manifest_rel=entry.manifest,
                )
            click.echo(
                f"  {verb:<12} {label} at {bundled} (no record before: it reads as at "
                "the backbone, so no migration runs)"
            )
            ran += 1
            continue

        if not _moves_up(installed_manifest.version, bundled):
            # At its bundled version, or ahead of it, which step 1 refuses: a
            # recorded version never moves down (ADR-065 point 7).
            continue
        source_dir = _bundled_adapter_package(source_kit, entry.name).parent
        scripts = pending_migration_scripts(
            source_dir / "migrations", installed_manifest.version, bundled
        )
        if dry_run:
            if scripts:
                report_pending_migrations(
                    scripts,
                    label=label,
                    installed_version=installed_manifest.version,
                    target_version=bundled,
                    dry_run=True,
                    label_rel_to=source_dir,
                )
            click.echo(
                f"  {'would record':<12} {label} at {bundled} (from {installed_manifest.version})"
            )
            ran += 1
            continue

        if scripts:
            click.echo(
                f"  running {len(scripts)} migration(s) for {label} "
                f"({installed_manifest.version} -> v{bundled})"
            )
            execute_migration_scripts(scripts, target_root, label=label, label_rel_to=source_dir)
        prior = installed_manifest.version
        _restamp_component_manifest_version(installed_manifest_path, installed_manifest, bundled)
        click.echo(f"  {'recorded':<12} {label} at {bundled} (from {prior})")
        ran += 1

    if ran == 0:
        click.echo(f"  no component migrations to run (0 of {len(eligible)} adapter component(s))")


def _restamp_component_manifest_version(
    manifest_path: Path, manifest: ComponentManifest, new_version: str
) -> None:
    """Update the per-component manifest's `version` (+ `installed_at`) after migrations succeed."""
    import datetime as _dt

    manifest.version = new_version
    manifest.installed_at = _dt.datetime.now(_dt.UTC).isoformat()
    write_component_manifest(manifest_path, manifest)


def _check_capability_dep_conflicts_for_upgrade(
    target_root: Path,
    plans: Sequence[CapabilityPlan],
    *,
    force: bool,
) -> None:
    """The dependency gates of a transition of the backbone, over the set it would
    leave (ADR-065 point 6; COR-030, COR-053 point 6).

    That set holds every shipped capability the transition moves at the version
    its bundle ships, with that version's `requires_capabilities` and
    mandatory process connections, and every other capability at its installed
    version. Within one release the moving capabilities agree, so a conflict
    involves a capability that does not move: an incubated, externally-sourced
    or no-longer-shipped one. The gates run as `pkit capabilities upgrade` runs
    them, in COR-030's direction split:

    - **A moving capability** whose required dependency is not installed, or
      whose dependency is out of the range it declares, refuses with a hint,
      and so does one whose mandatory upstream it would leave unmet. The
      project controls that dependency. No flag overrides it.
    - **A moving dependency** whose new version falls outside the range a
      capability that does not move declares for it warns, naming each such
      dependent, and so does one that leaves a dependent's mandatory
      connection unmet. The transition proceeds only under *force*
      (`pkit upgrade --force`), so neither is a hard block.

    A pair in which neither side moves is not the transition's to judge, and
    neither is a mandatory connection of a capability that does not move,
    already unmet before it. An optional dependency that is not installed
    passes. Read-only.
    """
    from project_kit import capabilities as caps
    from project_kit.connections import range_admits

    moving = {
        plan.name: plan for plan in plans if plan.disposition in COPIES and plan.source is not None
    }
    if not moving:
        return
    registered = {plan.name for plan in plans}

    def version_after(name: str) -> str | None:
        plan = moving.get(name)
        if plan is not None:
            return plan.bundled
        return caps.get_installed_capability_version(target_root, name)

    refusals: list[str] = []
    for plan in moving.values():
        requires = plan.source.package.requires_capabilities if plan.source is not None else ()
        for dep in requires:
            if dep.name not in registered:
                if not dep.optional:
                    refusals.append(
                        f"capability {plan.name!r} v{plan.bundled} requires capability "
                        f"{dep.name!r} ({dep.version}), which is not installed: install it first"
                    )
                continue
            version = version_after(dep.name)
            if version is None or range_admits(dep.version, version) is not False:
                continue
            if dep.name in moving:
                why = (
                    f"and this release ships v{version}: the release's own versions "
                    "disagree, which no step of yours resolves, so report it to its "
                    "maintainers"
                )
            else:
                why = (
                    f"and v{version} is installed, which this upgrade does not move: "
                    "upgrade it first"
                )
            refusals.append(
                f"capability {plan.name!r} v{plan.bundled} requires capability "
                f"{dep.name!r} {dep.version}, {why}"
            )
    sources = [plan.source for plan in moving.values() if plan.source is not None]
    carried, left = caps.marks_a_transition_leaves_unmet(target_root, sources)
    refusals.extend(_mandatory_line(unmet) for unmet in carried)
    if refusals:
        raise click.ClickException(
            "capability dependency check failed: the capabilities this upgrade moves "
            "would have unmet dependencies:\n"
            + "".join(f"  - {line}\n" for line in refusals)
            + "Install or upgrade the capabilities they need first, then retry the "
            "upgrade (COR-030, COR-053 point 6). No flag overrides this refusal."
        )

    desynced = [
        f"{dependent.name!r} declares {name!r} {requirement.version} "
        f"(this upgrade brings v{plan.bundled})"
        for dependent in plans
        if dependent.name not in moving
        for name, plan in moving.items()
        for requirement in caps.declared_dependencies(target_root, dependent.name, name)
        if range_admits(requirement.version, plan.bundled or "") is False
    ]
    if not (desynced or left):
        return
    heading = "Warning (--force):" if force else "Warning:"
    if desynced:
        click.echo(
            f"  {heading} {len(desynced)} declared range(s) of a capability this upgrade "
            "does not move would exclude the version it brings (COR-030):"
        )
        for line in desynced:
            click.echo(f"    - {line}")
    if left:
        click.echo(
            f"  {heading} {len(left)} mandatory process connection(s) of a capability this "
            "upgrade does not move would be left unmet (COR-053 point 6):"
        )
        for unmet in left:
            click.echo(f"    - {_mandatory_line(unmet, carrier=True)}")
    if force:
        click.echo(
            "  Proceeding under --force: upgrade or uninstall those capabilities to restore "
            "consistency."
        )
        click.echo()
        return
    raise click.ClickException(
        "refusing to upgrade: a capability this upgrade moves would leave a capability "
        "that does not move out of range, or its mandatory process connection unmet.\n"
        "Upgrade or uninstall those capabilities first, or pass --force to proceed anyway "
        "(the deadlock-free override, COR-030 and COR-053 point 6)."
    )


def _mandatory_line(unmet: MandatoryUpstream, *, carrier: bool = False) -> str:
    """One unmet mandatory mark: the capability carrying it where it is not the one
    the line is about, the upstream, why it is not met, and the mark's reason."""
    who = f"{unmet.capability!r} depends on " if carrier else f"capability {unmet.capability!r}: "
    return f"{who}{unmet.process!r}: {unmet.problem} (mandatory: {unmet.reason})"
