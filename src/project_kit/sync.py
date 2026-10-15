"""`pkit sync` — reconciliation at the version the project records (COR-059 point 2).

The code behind `pkit sync` is two parts, a propagation step and the sync
command that runs it (ADR-065 point 1):

- **The propagation step** (`propagate`) copies the content the running pkit
  ships (ADR-033): the methodology's trees, adapters included, and the shipped
  capabilities its caller names, with their skips. It checks no version, runs
  no migration, writes no manifest and creates no seed path. A version
  transition, `pkit upgrade`, calls the step too, never the command.
- **The sync command** (`run_sync`) runs its guard first
  (`refuse_version_mismatch`), which stops under a pkit at another version than
  the project records, or over an unfinished upgrade. In the methodology's
  source it then runs the self-host branch alone. Elsewhere it runs the step,
  naming each shipped capability the bundle ships at its recorded version, and
  regenerates the derivable state: merge delivery in its auto-add tier, deploy,
  the `.pkit/.gitignore` render, the agent workspace and provisioning. It writes
  no manifest and no seed path, and runs no migration.

Project-owned content (`.pkit/<area>/project/`) is never overwritten. The two
fixed-path files the harness expects, `.claude/settings.json` and `CLAUDE.md`,
are merged into by the adapter's merge primitives, never replaced (COR-002).
Idempotent: re-running with no change is a clean no-op.
"""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import click
from packaging.version import InvalidVersion, Version

from project_kit import install

if TYPE_CHECKING:
    from project_kit.capabilities import CapabilityRecord, CapabilitySource
from project_kit.manifest import (
    ORIGIN_INCUBATED_IN_REPO,
    ORIGIN_KIT_SHIPPED,
    BackboneManifest,
    read_backbone_manifest,
    read_kit_version,
)
from project_kit.router import (
    DISTRIBUTION_GIT_URL,
    DISTRIBUTION_HTTPS_URL,
    fell_back_from_pin,
    is_source_checkout,
    read_version_pin,
)

# What `pkit sync --force` says, for the one release that accepts the flag and
# ignores it (ADR-065 point 10). Its one effect, copying an older capability over
# a newer one, moved a recorded version down. A later release removes the flag.
SYNC_FORCE_IGNORED = (
    "note: `pkit sync --force` is ignored, and a later release removes the flag. Sync no "
    "longer copies a capability over a newer one: it copies each capability only at the "
    "version the project records. `pkit upgrade` moves a capability, with its migrations."
)


def run_sync(target_root: Path, dry_run: bool = False) -> None:
    """The sync command: reconcile the project at the version it records.

    Its guard comes first (`refuse_version_mismatch`), before anything is read
    for propagation or written, under `--dry-run` too. It stops, naming the
    remedy, when the running pkit is not the release the project records, when
    the last upgrade is incomplete, or when the pin is newer than this pkit.
    Nothing overrides it. Then the self-host branch in the methodology's
    source, and elsewhere the propagation step and the derivable state.
    """
    if not (target_root / ".pkit").is_dir():
        raise click.ClickException(f"{target_root}/.pkit/ does not exist. Run 'pkit init' first.")

    source_kit = install.find_source_kit()

    # The guard first (ADR-065 point 7). It lets the methodology's source pass.
    refuse_version_mismatch(target_root, source_kit, command="sync")

    # Self-host (project-kit): its own .pkit/ IS the source, so propagation
    # would copy files onto themselves. This is sync's test for the
    # methodology's source repository (ADR-059 point 2). It is exact whenever
    # the running code is that repository's own; code that cannot ask it runs
    # the marker test (`router.is_source_checkout`) instead.
    if install.is_self_host(target_root, source_kit):
        run_self_host(target_root, source_kit, dry_run=dry_run)
        return

    # Sync's test has said no, but the markers may still call the target the
    # methodology's source: the running code is then not the repository's own,
    # and propagating its tree would overwrite the source (the gap, ADR-059).
    # Refuse rather than propagate; no flag overrides it (#1070).
    install.refuse_propagation_into_source(target_root, source_kit, command="sync")

    ctx = install.InstallContext(target_root=target_root, source_kit=source_kit, dry_run=dry_run)

    click.echo(f"Syncing project-kit at {target_root}")
    click.echo(f"  source: {source_kit}")
    if dry_run:
        click.echo("  (dry-run — no changes will be written)")
    click.echo()

    # Every capability's record is read before anything is copied (ADR-065
    # point 2): its version falls back to the installed `package.yaml`, which the
    # capability's copy replaces.
    from project_kit import capabilities as caps

    plans = plan_capabilities(target_root, source_kit, caps.read_capability_records(target_root))
    propagate(ctx, [plan for plan in plans if plan.disposition == COPY])
    _report_sync_capabilities(plans, dry_run=dry_run)

    regenerate_derivable_state(ctx)

    click.echo()
    click.echo("Sync complete.")

    if not ctx.dry_run:
        _hint_settings_consolidation(target_root)


def run_self_host(target_root: Path, source_kit: Path, *, dry_run: bool) -> None:
    """The self-host branch: all that sync or upgrade runs in the methodology's source.

    The source IS the installed state (ADR-059 point 2), so nothing is copied
    and no version moves. It regenerates the derivable state alone, re-wiring
    the harness (.claude/ agents, skills, settings, CLAUDE.md) from the source
    the maintainer just edited: "re-wire me to my own source". The render, the
    workspace and provisioning are core steps, so they run here too, or a
    backbone or capability runtime ignore would never render in self-host.
    """
    ctx = install.InstallContext(target_root=target_root, source_kit=source_kit, dry_run=dry_run)
    click.echo(f"Syncing project-kit at {target_root} (self-host)")
    click.echo("  source == target: skipping propagation; running deploy primitives only.")
    if dry_run:
        click.echo("  (dry-run — no changes will be written)")
    click.echo()
    regenerate_derivable_state(ctx)
    click.echo()
    click.echo("Self-host sync complete (deploy primitives re-run).")


def regenerate_derivable_state(ctx: install.InstallContext) -> None:
    """Regenerate the state derived from the project's own declarations (ADR-065 point 11).

    None of it is recorded in a manifest (COR-010), so sync, a transition and
    the self-host branch each regenerate all of it:

    - each installed adapter's primitives: merge delivery in its auto-add tier
      (`.claude/settings.json`, `CLAUDE.md`), then deploy of skills and agents
    - `.pkit/.gitignore`, rendered at the core tier from the runtime-ignore
      declarations of the backbone and every installed component (ADR-009 rule 7)
    - the agent workspace and its line in the local exclude file (#1043)
    - each registered query command's environment, resolved once, online (#1092)
    """
    install.run_installed_adapter_primitives(ctx)
    install._render_runtime_ignore(ctx)
    install.ensure_agent_workspace(ctx)
    install.provision_query_commands(ctx)


# --- The propagation step (ADR-065 point 1) ------------------------------------


def propagate(ctx: install.InstallContext, capabilities: Sequence[CapabilityPlan]) -> None:
    """Copy the running pkit's content into the project: the step both callers run.

    The methodology's trees (`install.PROPAGATED_AREAS`, adapters included) are
    refreshed in place, and each capability in *capabilities* is copied from
    its bundled source, leaving out the artefacts its record skips. The step
    checks no version, runs no migration, writes no manifest and creates no
    seed path (ADR-065 point 1). Before it writes the methodology's trees, it
    stops on a clash of area names (`refuse_area_name_clash`, point 13).
    Project-owned content is never overwritten. Under `--dry-run` it writes nothing. A capability is
    copied only where its disposition is one a copy may take (`COPIES`): never
    an incubated, an externally sourced, a no-longer-shipped one, or one
    bundled older.
    """
    from project_kit import capabilities as caps

    # A clash of area names stops the step before it writes the methodology's
    # trees, under `--dry-run` too (ADR-065 point 13). So sync's copy meets it
    # as a transition does, on an untagged install as well (point 12). A
    # transition has refused it in its step 1 already, and nothing it writes
    # before this step makes one, so only sync meets the refusal here.
    refuse_area_name_clash(ctx.target_root, ctx.source_kit, command="sync")
    for area in install.PROPAGATED_AREAS:
        src = ctx.source_kit / area
        if src.is_dir():
            install._install_area(src, ctx.target_root / ".pkit" / area, ctx, overwrite=True)
    if ctx.dry_run:
        return
    for plan in capabilities:
        if plan.source is None or plan.disposition not in COPIES:
            continue
        skipped = plan.record.skipped if plan.record is not None else ()
        caps.copy_shipped_capability(ctx.target_root, plan.source, skipped)


# --- A clash of area names (ADR-065 point 13) ------------------------------------


def area_name_clash(target_root: Path, source_kit: Path) -> Path | None:
    """The project's own area that the running pkit's copy would write over, or None.

    Among published releases one such clash can happen (ADR-065 point 13): a
    project's own area at `.pkit/lifecycle/`, made at a release before v1.149.0,
    which first shipped the core area of that name. The core area holds
    `ownership.py` (`install.LIFECYCLE_MARK`), as it has since it first shipped,
    and a project's own area does not. So, while the running pkit ships the core
    area, the clash is anything at `.pkit/lifecycle` other than a folder, not a
    link, that holds that file. An empty folder is no clash: every copy writes
    the file first, so an interrupted copy leaves the folder empty or holding
    it. Every other area a release propagates has shipped since v1.134.0, and no
    release adds a core area until #1600 builds the full check. Read-only.
    """
    area = install.LIFECYCLE_AREA
    if area not in install.PROPAGATED_AREAS or not (source_kit / area).is_dir():
        return None
    path = target_root / ".pkit" / area
    if not os.path.lexists(path):
        return None
    if path.is_dir() and not path.is_symlink():
        if (path / install.LIFECYCLE_MARK).is_file() or not any(path.iterdir()):
            return None
    return path


def refuse_area_name_clash(target_root: Path, source_kit: Path, *, command: str) -> None:
    """Stop a command whose copy would write a core area over the project's own.

    A transition calls it in its step 1, and the propagation step before it
    writes the methodology's trees, so sync's copy meets it too (ADR-065 point
    13). It writes nothing, stops whether or not a person can answer and under
    `--dry-run` too, and takes no override. Its message names the path, the
    release that ships the core area, and the ways on: move the project's area,
    stay at the release the project records (after a transition's stop alone,
    since sync already runs that release), or restore a core area that lost its
    file. The methodology's source never reaches it: its sync and its upgrade
    run the self-host branch, which copies nothing.
    """
    path = area_name_clash(target_root, source_kit)
    if path is None:
        return
    running = read_kit_version(source_kit)
    shown = f".pkit/{path.name}/"
    mark = install.LIFECYCLE_MARK
    lines = [
        f"refusing to run `pkit {command}`: {shown} is the project's own area, and pkit "
        f"{running} ships a core area of that name, which its copy would write over "
        "(ADR-065 point 13).",
        f"The core area holds {mark}, and this one does not. Nothing was written, and no "
        "flag overrides this refusal.",
        f"To move on: move the project's area to another name, with what refers to it, "
        f"then run `pkit {command}` again.",
        *(_area_clash_stay_lines(target_root) if command == "upgrade" else []),
        f"If {shown} is the methodology's own area and has lost {mark}: restore that file "
        f"from git (`git checkout -- {shown}{mark}`). Where git holds no copy of it, remove "
        f"the folder, which holds none of the project's content. Then run `pkit {command}` "
        "again.",
    ]
    raise click.ClickException("\n       ".join(lines))


def _area_clash_stay_lines(target_root: Path) -> list[str]:
    """How a project stays at its release after a transition's stop on a clash of
    area names (ADR-065 point 13).

    An unpinned project pins the release it records, point 8's Stay remedy. A
    pinned project at its pin needs nothing: the transition moved no pin, and the
    router goes on running that release. Otherwise no way to stay is named.
    """
    manifest = read_backbone_manifest(target_root)
    recorded = manifest.backbone_version if manifest is not None else None
    if _parse_version(recorded) is None:
        return []
    pin = read_version_pin(target_root)
    if pin is None:
        return [
            f"To stay at {recorded}: run `pkit pin`. It pins the project at {recorded}, and "
            "the router then runs that version here."
        ]
    if _parse_version(pin) == _parse_version(recorded):
        return [
            f"To stay at {pin}: do nothing. This upgrade moved no pin, and the router goes "
            f"on running pkit {pin} here."
        ]
    return []


# --- Each capability, by the version it records (ADR-065 point 1) ---------------

# What sync and a transition do with one registered capability.
COPY = "copy"  # bundled at the version its record names
NEWER = "newer"  # bundled newer than its record
AT_ROOT = "at-root"  # its manifest still at the capability's root
OLDER = "older"  # bundled older than its record
UNRECORDED = "unrecorded"  # no recorded version, from neither a manifest nor its package.yaml
UNVERSIONED = "unversioned"  # the bundle's package names no version
ORPHAN = "orphan"  # not in the bundle
INCUBATED = "incubated"  # authored in the project (COR-031)
EXTERNAL = "external"  # externally sourced (COR-041)

# The dispositions a copy may take: a transition copies all of them, and sync
# only COPY. A capability bundled older is never copied, since a recorded version
# never moves down (ADR-065 point 7); one with no recorded version is copied by a
# transition and recorded at the bundled version (point 2).
COPIES = frozenset({COPY, NEWER, AT_ROOT, UNRECORDED})


@dataclass(frozen=True)
class CapabilityPlan:
    """One registered capability, and what its record and the bundle make of it."""

    name: str
    disposition: str
    source: CapabilitySource | None = None
    record: CapabilityRecord | None = None

    @property
    def bundled(self) -> str | None:
        """The version the running pkit's bundle ships, or None when it ships none."""
        return self.source.package.version if self.source is not None else None

    @property
    def recorded(self) -> str | None:
        """The version the project records for it, or None."""
        return self.record.version if self.record is not None else None


def plan_capabilities(
    target_root: Path, source_kit: Path, records: Mapping[str, CapabilityRecord]
) -> list[CapabilityPlan]:
    """Each registered capability's disposition, in registry order (ADR-065 point 1).

    *records* holds each capability's record, read before propagation
    (`capabilities.read_capability_records`). The checks run in this order,
    the first that holds deciding:

    - incubated: the project's own, never reconciled with the bundle (COR-031)
    - externally sourced: never read as shipped; its fetch brings it to its pin
      once built (COR-041)
    - not in the bundle: COR-017's no-longer-shipped warning
    - the bundle's package names no version, or the record names none
    - bundled older than the record
    - its manifest still at the capability's root, where older releases wrote it
    - bundled newer than the record
    - otherwise bundled at the recorded version: the one case sync copies
    """
    from project_kit import capabilities as caps

    backbone = read_backbone_manifest(target_root)
    if backbone is None:
        return []
    plans: list[CapabilityPlan] = []
    for entry in backbone.components:
        if entry.kind != "capability":
            continue
        if entry.origin == ORIGIN_INCUBATED_IN_REPO:
            # The bundle's capability of the same name, if any, for the report.
            plans.append(
                CapabilityPlan(
                    entry.name, INCUBATED, caps.find_capability_in_source(source_kit, entry.name)
                )
            )
            continue
        if entry.origin != ORIGIN_KIT_SHIPPED:
            plans.append(CapabilityPlan(entry.name, EXTERNAL))
            continue
        record = records.get(entry.name) or caps.read_capability_record(target_root, entry.name)
        source = caps.find_capability_in_source(source_kit, entry.name)
        if source is None:
            # Its record too: a transition moves its manifest from the root.
            plans.append(CapabilityPlan(entry.name, ORPHAN, record=record))
            continue
        bundled, recorded = _parse_version(source.package.version), _parse_version(record.version)
        if bundled is None:
            disposition = UNVERSIONED
        elif recorded is None:
            disposition = UNRECORDED
        elif bundled < recorded:
            disposition = OLDER
        elif record.at_root:
            disposition = AT_ROOT
        elif bundled > recorded:
            disposition = NEWER
        else:
            disposition = COPY
        plans.append(CapabilityPlan(entry.name, disposition, source, record))
    return plans


def _report_sync_capabilities(plans: Sequence[CapabilityPlan], *, dry_run: bool) -> None:
    """Sync's line for each registered capability: copied, or skipped and why."""
    if not plans:
        return
    click.echo()
    click.echo("  Capabilities")
    for plan in plans:
        name = repr(plan.name)
        if plan.disposition == COPY:
            verb = "would copy" if dry_run else "copied"
            click.echo(f"    {verb:<12} {name} at v{plan.bundled}")
        elif plan.disposition == INCUBATED:
            report_incubated_capability(plan)
        elif plan.disposition == EXTERNAL:
            click.echo(
                f"    {'skipped':<12} {name} — externally sourced: sync brings it to its pin "
                "once its fetch is built, and never reads it as shipped."
            )
        elif plan.disposition == ORPHAN:
            click.echo(
                f"    {'orphan':<12} {name} — no longer ships from source; "
                f"leaving installed copy in place."
            )
        elif plan.disposition in (NEWER, AT_ROOT):
            why = (
                "its manifest is still at the capability's root, where older releases wrote it"
                if plan.disposition == AT_ROOT
                else f"the bundle ships v{plan.bundled}, and the project records v{plan.recorded}"
            )
            click.echo(
                f"    {'pending':<12} {name} — {why}. Not copied: `pkit upgrade` moves it, "
                "with its migrations."
            )
        elif plan.disposition == OLDER:
            click.echo(
                f"    {'skipped':<12} {name} — the bundle ships v{plan.bundled}, older than the "
                f"recorded v{plan.recorded}. Not copied: a recorded version never moves down."
            )
        elif plan.disposition == UNRECORDED:
            click.echo(
                f"    {'skipped':<12} {name} — no recorded version: neither its manifest nor "
                "its package.yaml names one. Not copied, and none of its migrations runs: "
                "`pkit upgrade` records it at the version the bundle ships."
            )
        elif plan.disposition == UNVERSIONED:
            click.echo(
                f"    {'skipped':<12} {name} — the bundle's package.yaml names no version "
                f"({plan.bundled!r}). Not copied."
            )


def report_incubated_capability(plan: CapabilityPlan) -> None:
    """The status line for an incubated (in-repo) capability.

    Reconciliation with the bundle is suppressed for an incubated capability
    (COR-031 D1), so this only reports. When the bundle now ships a capability
    of the same name (*plan*'s source), the line says so: graduation arriving
    unbidden. Until graduation is specified the project decides, and neither
    tree is shadowed.
    """
    if plan.source is None:
        click.echo(
            f"    {'incubated':<12} {plan.name!r} — in-repo capability; "
            "skipping source-reconciliation."
        )
        return
    click.echo(
        f"    {'collision':<12} {plan.name!r} — in-repo capability, but the kit now "
        f"ships a capability of the same name (v{plan.source.package.version}). "
        f"Source-reconciliation stays skipped; resolve the collision manually."
    )


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


# --- Sync's guard (ADR-065 points 7 and 8) ---------------------------------------


def refuse_version_mismatch(target_root: Path, source_kit: Path, *, command: str) -> None:
    """Stop a command that would propagate under another version than the project's.

    Sync's guard (ADR-065 point 7; COR-059 point 9): #1212's refusal of a pkit
    older than the project, widened to the newer direction and to an
    incomplete upgrade. It stops when any of these holds:

    - `.pkit/manifest.yaml` is missing, or its `backbone_version` is no version
    - the running pkit's version is not `backbone_version`
    - `completed_version` differs from `backbone_version`, or is missing
    - the pin is newer than the running pkit

    It stops before anything is written, exits non-zero, stops under
    `--dry-run` too, and takes no override. Its message names the remedy for
    the state it finds, the first that matches in point 8's order
    (`_mismatch_lines`). The pin otherwise only chooses the message, and so
    does the router's fallback mark.

    Every command that copies methodology content calls it at its entry, in
    both directions, with *command* as the operator would re-run it: the sync
    command, `pkit capabilities install <name>` and `pkit capabilities upgrade
    <name>`. `pkit capabilities register` copies nothing and does not call it.

    The methodology's source repository is exempt (ADR-059): where sync's test
    recognises it, sync runs the self-host branch; where only the markers do,
    the refusal in the gap stops the command with its own message. A pkit that
    cannot read its own bundle is refused here too, with that refusal's
    message, before any version is read (#333). Upgrade calls the older
    direction alone (`refuse_content_downgrade`).
    """
    if install.is_self_host(target_root, source_kit) or is_source_checkout(target_root):
        return
    install.refuse_if_source_kit_incomplete(source_kit)
    lines = _mismatch_lines(
        command,
        running=read_kit_version(source_kit),
        manifest=read_backbone_manifest(target_root),
        pin=read_version_pin(target_root),
        fell_back=fell_back_from_pin(os.environ),
    )
    if lines:
        raise click.ClickException("\n       ".join(lines))


def _mismatch_lines(
    command: str,
    *,
    running: str,
    manifest: BackboneManifest | None,
    pin: str | None,
    fell_back: bool,
) -> list[str] | None:
    """The guard's message for the state found, or None when the command may run.

    The rows of ADR-065 point 8, the first that matches winning:

    1. pinned, and the router fell back to another installed pkit
    2. no manifest, or a recorded version that is no version
    3. this pkit older than the content or the pin (#1212)
    4. the last upgrade incomplete
    5. pinned, the content behind the pin, the pin's code running
    6. unpinned, this pkit newer than the content

    A pinned project whose content this pkit, not the pin's code, is newer
    than matches none of them: its message names running the pin, or moving.
    """
    recorded = manifest.backbone_version if manifest is not None else None
    completed = manifest.completed_version if manifest is not None else None
    readable = _parse_version(recorded) is not None
    content = _newest(recorded, completed) if manifest is not None else None
    pin_ahead = _is_older(running, pin)
    incomplete = manifest is not None and manifest.transition_incomplete
    another = readable and _parse_version(running) != _parse_version(recorded)
    if readable and not (another or incomplete or pin_ahead):
        return None

    rule = (
        f"`pkit {command}` works only at the release this project records, and never over "
        "an unfinished upgrade: under another pkit it would copy another release's content "
        "without that release's migrations (ADR-065). Nothing was written, and no flag "
        "overrides this refusal."
    )
    state = _mismatch_state(running, manifest, pin)

    if pin is not None and fell_back:
        return [
            f"refusing to run `pkit {command}`: {state}.",
            f"This project pins pkit {pin}, which the router could not fetch, so this run is "
            f"pkit {running}, not the pin.",
            rule,
            *fallback_remedies(command, pin),
        ]
    if manifest is None or not readable:
        return [
            f"refusing to run `pkit {command}`: {state}.",
            rule,
            "Run `pkit upgrade`: it writes the manifest at its version and runs every backbone "
            "migration once.",
        ]
    if _is_older(running, content) or pin_ahead:
        return _content_downgrade_lines(command, running, content, pin)
    if incomplete:
        if completed is None:
            remedy = (
                "Run `pkit upgrade`: it runs every backbone migration up to its version once, "
                "and records the completion last."
            )
        else:
            remedy = (
                f"Run `pkit upgrade`: it finishes the upgrade, running the backbone migrations "
                f"from {completed}."
            )
        return [
            f"refusing to run `pkit {command}`: {state}.",
            rule,
            remedy,
            "If a migration fails every time, fix its cause and run `pkit upgrade` again, or "
            "roll the project back with `git checkout <ref> -- .pkit/`, which restores both "
            "recorded versions.",
        ]
    if pin is not None and _is_older(recorded, pin) and _same_version(running, pin):
        return [
            f"refusing to run `pkit {command}`: {state}.",
            rule,
            "Run `pkit upgrade`: run under the pin, it brings the content up to the pin.",
        ]
    if pin is None:
        return [
            f"refusing to run `pkit {command}`: {state}, and the project pins no version.",
            rule,
            f"To move the project to {running}: run `pkit upgrade`. It pins the project by "
            "default (`--no-pin` keeps it unpinned), and at a terminal it may first update "
            "the pkit tool (`--no-self-update` declines).",
            f"To stay at {recorded}: run `pkit pin`. It pins the project at {recorded}, and the "
            "router then runs that version here.",
            f"In a pipeline: commit a pin, or install pkit {recorded} there: "
            f"`uv tool install --force {DISTRIBUTION_GIT_URL}@v{recorded}`.",
        ]
    if _parse_version(pin) is None:
        # A pin that is no version names no release to run.
        return [
            f"refusing to run `pkit {command}`: {state}, and the project's pin, {pin!r}, is "
            "no version.",
            rule,
            f"To stay at {recorded}: run `pkit pin`, which pins the project at {recorded}.",
            "To move the project on: run `pkit upgrade`.",
        ]
    return [
        f"refusing to run `pkit {command}`: {state}, and the project pins {pin}.",
        rule,
        f"To run it at the pin: let the router run it, which it does unless `PKIT_NO_ROUTE` is "
        f"set, or run `uvx --from {DISTRIBUTION_GIT_URL}@v{pin} project-kit {command}`.",
        "To move the project on: run `pkit upgrade`.",
    ]


def fallback_remedies(command: str, pin: str) -> list[str]:
    """The remedies of the router's fallback, the first row of ADR-065 point 8,
    for *command* in a project that pins *pin*: sync's guard names them, and so
    does `pkit upgrade`'s refusal under the fallback (point 9).

    The router runs the pin whenever it can fetch it, so the remedies are
    reconnecting, the pin run through `uvx`, or the pin's version installed
    from the HTTPS URL where SSH keys fail. Moving on purpose is `pkit unpin`,
    then `pkit upgrade`, never a bare `pkit upgrade`. A pin that is no version
    names no release the router can ever fetch, so it gets no command built
    from it: it is replaced with `pkit pin`, or the project moves on purpose.
    """
    if _parse_version(pin) is None:
        return [
            f"The pin, {pin!r}, is no version, so the router can never fetch it. Replace it "
            "with `pkit pin`, which pins the project at its content's version.",
            "To move the project on purpose: `pkit unpin`, then `pkit upgrade`.",
        ]
    return [
        f"Reconnect and run `pkit {command}` again: the router runs the pin whenever it can "
        f"fetch it. Or run the pin through uvx: `uvx --from {DISTRIBUTION_GIT_URL}@v{pin} "
        f"project-kit {command}`.",
        "Where SSH keys are what fail, install the pin's version from the repository's "
        f"HTTPS URL: `uv tool install --force {DISTRIBUTION_HTTPS_URL}@v{pin}`. The router "
        "then runs it with no fetch.",
        "To move the project on purpose: `pkit unpin`, then `pkit upgrade`.",
    ]


def _mismatch_state(running: str, manifest: BackboneManifest | None, pin: str | None) -> str:
    """What the guard found, as the clause after `refusing to run …:`, in the
    order of the rows that name its remedy (`_mismatch_lines`)."""
    if manifest is None:
        return ".pkit/manifest.yaml is missing"
    recorded, completed = manifest.backbone_version, manifest.completed_version
    if _parse_version(recorded) is None:
        return f"`backbone_version` in .pkit/manifest.yaml is {recorded!r}, which is no version"
    content = _newest(recorded, completed)
    if _is_older(running, content) or _is_older(running, pin):
        ahead: list[str] = []
        if _is_older(running, content):
            ahead.append(f"content ({content}, in .pkit/manifest.yaml)")
        if _is_older(running, pin):
            ahead.append(f"pin ({pin}, in .pkit/version-pin)")
        return f"this pkit is {running}, older than this project's " + " and ".join(ahead)
    if manifest.transition_incomplete:
        running_too = "" if _same_version(running, recorded) else f", and this pkit is {running}"
        if completed is None:
            return (
                "no completed upgrade is recorded for this project: .pkit/manifest.yaml "
                f"records `backbone_version` {recorded} and no `completed_version`, so its "
                f"backbone migration history is unknown{running_too}"
            )
        return (
            "the last upgrade of this project is incomplete: .pkit/manifest.yaml records "
            f"`backbone_version` {recorded} and `completed_version` {completed}{running_too}"
        )
    if pin is not None and _is_older(recorded, pin) and _same_version(running, pin):
        return (
            f"this project pins pkit {pin}, and its content is behind the pin: "
            f".pkit/manifest.yaml records {recorded}"
        )
    if _is_older(recorded, running):
        return (
            f"this pkit is {running}, newer than this project's content, {recorded} "
            "(`backbone_version` in .pkit/manifest.yaml)"
        )
    return (
        f"this pkit is {running}, and this project records {recorded} "
        "(`backbone_version` in .pkit/manifest.yaml)"
    )


def refuse_content_downgrade(
    target_root: Path, source_kit: Path, *, command: str, offline: bool = False
) -> None:
    """Refuse to run under a pkit older than the project's content or pin (#1212).

    The older direction of sync's guard (ADR-065 point 7), which `pkit upgrade`
    calls alone: it moves the project to the running version, so only an older
    pkit stops it. Sync's guard reaches the same message through
    `refuse_version_mismatch`.

    The content this pkit writes is its own version's (ADR-033 ties a release's
    content to its code), so a pkit older than the project's recorded content
    (the newer of `.pkit/manifest.yaml`'s `backbone_version` and
    `completed_version`) or than its pin (`.pkit/version-pin`) would take the
    project back: older content over newer, and, in `upgrade`, the pin moved
    down to it. pkit does neither: migrations are forward-only (COR-010) and a
    pin is never moved down (ADR-049). An older pkit is a normal state, not a
    defect: a pin raise leaves the installed tool where it was, and when the
    router cannot fetch a project's pin it runs the installed tool instead
    (ADR-039). Nothing overrides the refusal, `--force` included, and a dry run
    refuses too: as with `pkit pin <older>` (ADR-049), there is no safe path
    down.

    Only an unambiguous downgrade refuses. A recorded version that is absent or
    not valid semver (a corrupt manifest, over which `pkit upgrade` records its
    target; a pin that is not a version) is not ordered. *command* names the
    refusing command as the operator would re-run it.

    *offline* is set by a pinned project's upgrade run under its pin's code
    that could not look up the latest release (ADR-065 point 9). Content ahead
    of the pin is then what an interrupted raise to a newer release leaves, so
    the message names reconnecting: online, that upgrade hands over to the
    latest release, whose upgrade finishes the raise.
    """
    tool = read_kit_version(source_kit)
    manifest = read_backbone_manifest(target_root)
    content = (
        _newest(manifest.backbone_version, manifest.completed_version)
        if manifest is not None
        else None
    )
    pin = read_version_pin(target_root)
    if not (_is_older(tool, content) or _is_older(tool, pin)):
        return
    raise click.ClickException(
        "\n       ".join(_content_downgrade_lines(command, tool, content, pin, offline=offline))
    )


def _content_downgrade_lines(
    command: str, tool: str, content: str | None, pin: str | None, *, offline: bool = False
) -> list[str]:
    """#1212's refusal: the versions ahead of this pkit, why, and the way to the right pkit."""
    ahead: list[str] = []
    if _is_older(tool, content):
        ahead.append(f"content ({content}, in .pkit/manifest.yaml)")
    if _is_older(tool, pin):
        ahead.append(f"pin ({pin}, in .pkit/version-pin)")
    if offline:
        remedy = [
            "This upgrade could not look up the latest release, so it could not hand over "
            f"to one. Reconnect and run `pkit {command}` again: it then hands over to the "
            "latest release, whose upgrade finishes the interrupted raise.",
        ]
    else:
        remedy = _content_downgrade_remedy(command, content, pin)
    return [
        f"refusing to run `pkit {command}`: this pkit is {tool}, older than this project's "
        + " and ".join(ahead)
        + ".",
        f"Run by this pkit, `{command}` would take the project back to {tool}, and pkit "
        "never moves a project to an older version: its migrations are forward-only "
        "(COR-010), and a pin is never moved down (ADR-049). Nothing was written, and no "
        "flag overrides this refusal.",
        *remedy,
        "To take the project back to an older version, restore `.pkit/` from git: "
        "`git checkout <ref> -- .pkit/`.",
    ]


def _content_downgrade_remedy(command: str, content: str | None, pin: str | None) -> list[str]:
    """The way to the pkit a refused *command* needs, by what the project records.

    Three cases. A pin no older than the content is the version the project
    runs at, so the remedy is that version, which the router runs whenever it
    can fetch it. Content ahead of its pin is the state an interrupted pin raise
    leaves (ADR-049), so the remedy is pinning at the content, which needs no
    fetch, or, for a command other than upgrade, `pkit upgrade`, which finishes
    the raise (ADR-065 point 8). With no pin, or one that is not a version, the
    remedy is a pkit at the content's version, run once or installed.
    """
    if _parse_version(pin) is not None and not _is_older(pin, content):
        return [
            f"Run it with pkit {pin}, the version this project pins: reconnect and re-run "
            f"`pkit {command}` (the router runs the pin whenever it can fetch it), or run "
            f"`uvx --from {DISTRIBUTION_GIT_URL}@v{pin} project-kit {command}`.",
            "To move the pin instead, run `pkit pin <version>`; it takes a version no older "
            "than the project's content.",
        ]
    if _parse_version(pin) is not None:
        lines = [
            f"The content is ahead of the pin ({pin}), as an interrupted pin raise leaves it: "
            f"run `pkit pin {content}` to pin the project at its content, then re-run "
            f"`pkit {command}`.",
        ]
        if command != "upgrade":
            lines.append("Or run `pkit upgrade`, which finishes the interrupted raise.")
        return lines
    return [
        f"Run it with pkit {content} or newer: `uvx --from {DISTRIBUTION_GIT_URL}@v{content} "
        f"project-kit {command}`, or install that version as your pkit: `uv tool install "
        f"--force {DISTRIBUTION_GIT_URL}@v{content}`.",
    ]


def _is_older(version: str | None, than: str | None) -> bool:
    """True iff *version* is strictly older than *than*; False when either is
    absent or not valid semver, so the guard fires only on an unambiguous order."""
    parsed, parsed_than = _parse_version(version), _parse_version(than)
    if parsed is None or parsed_than is None:
        return False
    return parsed < parsed_than


def _same_version(version: str | None, other: str | None) -> bool:
    """True iff both are versions and name the same one, however each is written."""
    parsed, parsed_other = _parse_version(version), _parse_version(other)
    return parsed is not None and parsed == parsed_other


def _newest(*versions: str | None) -> str | None:
    """The newest of *versions* that is a version, else the first one given, so a
    recorded state that is no version is shown but never ordered."""
    parsed = [(v, p) for v in versions if (p := _parse_version(v)) is not None]
    if parsed:
        return max(parsed, key=lambda pair: pair[1])[0]
    return versions[0] if versions else None


def _parse_version(text: str | None) -> Version | None:
    """*text* as a version, or None when it is absent or not valid semver."""
    if not text:
        return None
    try:
        return Version(text)
    except InvalidVersion:
        return None
