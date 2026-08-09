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

import os
import re
import subprocess
import sys
from pathlib import Path

import click
from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.version import InvalidVersion, Version

from project_kit.install import find_source_kit, refuse_if_source_kit_incomplete
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
from project_kit.router import (
    DISTRIBUTION_GIT_URL,
    is_route_bypassed,
    is_routed_child,
    is_source_checkout,
    pin_file_path,
    read_version_pin,
    run_bypassed,
    running_version,
)
from project_kit.sync import run_sync

# Capability-dependency check (COR-030) — imported lazily below to avoid
# any circular-import issues at module load time. The functions used are:
#   capabilities.check_capability_dependencies
#   capabilities.find_declared_dependents
#   capabilities.get_installed_capability_version
#   capabilities._read_package_yaml (internal, accessed via CapabilitySource path)


def run_upgrade(
    target_root: Path, dry_run: bool = False, pin: bool = True, self_update: bool = True
) -> None:
    """Transition the project to the source kit's current backbone version.

    **Pins by default** (ADR-049, amended 2026-08-09): an **un-pinned** project is
    pinned at the version its content just synced to, so pinning is the norm and a
    project stays code/content-coherent without a remembered gesture. `pin=False`
    (the `--no-pin` opt-out) keeps the old un-pinned "follow the installed global
    tool" behaviour. The pin uses the local synced version (offline-safe — no
    `git ls-remote` lookup), is written LAST (after content + migrations, so a
    failed sync never leaves a pin ahead of content), and is a no-op on a project
    that is already pinned (the existing pin-raise already maintains it). Self-host
    is never pinned — it returns before the pin logic.
    """
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

    # Self-host (project-kit): the source IS the installed state, so there is
    # no backbone to upgrade. Delegate to sync, whose self-host branch re-runs
    # the deploy primitives so the harness picks up source edits. Skips the
    # version comparison (the recorded manifest version is moot on self-host)
    # and the migration steps (self-host authors migrations with the source
    # change; it does not run them against itself).
    if target_root.resolve() == source_kit.parent.resolve():
        click.echo("Self-host: source is the installed state; no backbone upgrade needed.")
        click.echo("Re-running deploy primitives via sync.")
        click.echo()
        run_sync(target_root, dry_run=dry_run)
        return

    # ADR-049: this project may pin a pkit version via `.pkit/version-pin`. Its
    # presence changes what `pkit upgrade` means — an upgrade *raises* the pin
    # (flipped last) rather than floating on the installed tool.
    pinned = read_version_pin(target_root) is not None
    if pinned and is_routed_child(os.environ):
        # The router re-exec'd us INTO the pinned version, which cannot mutate the
        # global tool from inside. Auto-advance the pin to the latest release
        # through the router bypass (no `uv tool install`, no manual escape).
        _auto_advance_pinned(target_root, dry_run)
        return

    # ADR-044: detect a newer *released tool* and instruct (print-only). This is
    # about the `uv`-installed binary, not this project's `.pkit/` content — so it
    # runs before the backbone-version comparison below and its early return, or
    # the stale-tool adopter would still see only "nothing to upgrade" and never
    # learn the fix lives in `uv`. Best-effort and read-only: it never installs,
    # never fails the command, and is suppressed on a source checkout (D3).
    #
    # ADR-049: suppress it on the bootstrap hop. Inside a `run_bypassed`-launched
    # reconcile (PKIT_NO_ROUTE set), this upgrade is running *under* a pin raise;
    # a second `git ls-remote` here would print a nonsensical "tool is current"
    # line mid-raise. The outer, non-bypassed upgrade already ran the probe.
    if not is_route_bypassed(os.environ):
        # Tool axis (ADR-044, amended): self-update the global tool when stale
        # and re-exec to finish under the new version (never returns on a
        # successful self-update); otherwise instruct or report current.
        _maybe_self_update_tool(target_root, self_update=self_update, dry_run=dry_run)

    # Past the self-host short-circuit: a real adopter upgrade reads
    # `read_kit_version(source_kit)` next and propagates from `source_kit` via
    # its sync step. Guard the resolved source first, so an incomplete bundle
    # surfaces as a clean ClickException rather than a raw FileNotFoundError
    # inside `read_kit_version` (ADR-033; issue #333). The self-host branch
    # above is skipped — its source is the live checkout.
    refuse_if_source_kit_incomplete(source_kit)

    target_version = read_kit_version(source_kit)
    current_version = manifest.backbone_version

    # Step 1: compatibility resolution against the POST-upgrade (source)
    # component versions — what sync will refresh them to — not the stale
    # installed copies (which always lag the auto-broadened source ceiling).
    _resolve_compatibility(manifest.components, target_root, source_kit, target_version)

    if current_version == target_version:
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

    # ADR-049: on a pinned project, flip the pin LAST — after content sync and
    # migrations — so a failed upgrade never advances the pin past content that
    # isn't in place. The write itself is atomic. On an un-pinned project the same
    # last-position write freezes the pin at the just-synced version by default
    # (pin-by-default; `--no-pin` sets pin=False to skip it).
    if pinned:
        _raise_pin_to(target_root, target_version, dry_run)
    elif pin:
        _pin_after_upgrade(target_root, target_version, dry_run)

    click.echo()
    click.echo("Upgrade complete.")


# --- Per-project version pin (ADR-049) -----------------------------------------


def _raise_pin_to(target_root: Path, target_version: str, dry_run: bool) -> None:
    """Flip `.pkit/version-pin` forward to `target_version` (ADR-049 pin raise).

    Writes only when the pin actually moves — an idempotent no-op when the pin is
    already at the target. The write is atomic (temp file + `os.replace`) and, by
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
    tmp = pin_path.with_name(pin_path.name + ".tmp")
    tmp.write_text(target_version + "\n", encoding="utf-8")
    os.replace(tmp, pin_path)  # atomic on POSIX; the pin never observes a torn write
    click.echo(f"  pin raised: {prior} -> {target_version} (.pkit/version-pin)")


def _pin_after_upgrade(target_root: Path, version: str, dry_run: bool) -> None:
    """Pin-by-default on an un-pinned project: freeze the pin at the just-synced
    version (ADR-049, amended 2026-08-09).

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
    point (`_normalize_pin_version`), so the router can always route it."""
    pin_path = pin_file_path(target_root)
    pin_path.parent.mkdir(parents=True, exist_ok=True)
    pin_path.write_text(version + "\n", encoding="utf-8")
    click.echo(f"Pinned project-kit to {version} ({pin_path.relative_to(target_root)}).")


def freeze_at_content(target_root: Path) -> None:
    """No-arg `pkit pin`: freeze the project at its current CONTENT version (ADR-049).

    Freezes at `.pkit/manifest.yaml`'s `backbone_version` — the content the
    project last synced — *not* the running binary's version. When the installed
    tool is ahead of the project's synced content, freezing at the binary version
    would bake in a code-vs-content mismatch; freezing at content keeps the
    version⟺content invariant intact. Refuses when the manifest is absent (there
    is no recorded content version to pin against).
    """
    current = _require_backbone_version(target_root)
    freeze_pin(target_root, current)


def reconcile_pin(target_root: Path, version: str) -> None:
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
    version) is refused too — there is nothing to order the target against.
    """
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
    _advance_pin_to(target_root, normalized)


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
    Absent, there is no recorded content version, so both hard-refuse with the same
    seed-the-manifest posture `run_upgrade` uses (ADR-049). Raises
    `click.ClickException`; nothing is written.
    """
    manifest = read_backbone_manifest(target_root)
    if manifest is None:
        raise click.ClickException(
            f"{target_root}/.pkit/manifest.yaml is missing — pkit has no record of "
            "this project's content version to pin against. Run 'pkit sync' once to "
            "seed the manifest, then retry."
        )
    return manifest.backbone_version


def reconcile_forward_via_target(target_root: Path, target: str) -> None:
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
    """
    returncode = run_bypassed(target, ["upgrade"])
    if returncode != 0:
        raise click.ClickException(
            f"reconciling content forward to {target} failed: the bootstrapped "
            f"`uvx project-kit@v{target} upgrade` exited {returncode}. The pin was "
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
            "semver — the manifest may be corrupt. Run 'pkit sync' to reconcile it, "
            "then retry."
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


def _advance_pin_to(target_root: Path, target: str) -> None:
    """Reconcile content forward to `target`, then flip the pin LAST (ADR-049).

    The shared "raise" shape both pin-forward gestures use (COR-007): `pkit pin
    <newer>` and `pkit upgrade` in a pinned project. It runs the *target* version's
    own code via the router bypass to sync content and forward-migrate
    (`reconcile_forward_via_target`), and only on its success flips
    `.pkit/version-pin` to `target` — so the pin never advances past content that
    failed to land.

    The explicit `_raise_pin_to` here is the load-bearing write when the project
    had no pin yet (first-time `pkit pin <newer>`): the bootstrapped upgrade sees
    no pin and does not flip one. When the project *was* already pinned (the
    `pkit upgrade` raise), the bootstrapped upgrade flips the pin from inside its
    own OUTER path, so this flip is a benign idempotent no-op.
    """
    reconcile_forward_via_target(target_root, target)
    _raise_pin_to(target_root, target, dry_run=False)


def _auto_advance_pinned(target_root: Path, dry_run: bool) -> None:
    """`pkit upgrade` as the pinned child: auto-advance the pin to the latest release (ADR-049).

    The router re-exec'd us INTO the pinned version (PKIT_ROUTED set), so we run
    the pinned code and cannot mutate the global tool. Resolve the latest released
    version (ADR-044's `git ls-remote` check) and dispatch on how it orders against
    the current pin:

    - **latest > pin** → reconcile content forward to latest under the target's own
      code (via the router bypass) and flip the pin last — no global `uv tool
      install`, no manual escape.
    - **latest == pin** → no-op with a clear "already at the latest release" line.
    - **latest < pin** → the project is pinned ahead of the newest release; say so
      and leave the pin (pkit never downgrades a pin — migrations are forward-only,
      COR-010).
    - **latest unresolvable** (offline / `_latest_released_version` returns None) →
      degrade loudly to stderr and leave the pin unchanged; never brick the command.
    """
    current_pin = read_version_pin(target_root)
    latest = _latest_released_version()
    if latest is None:
        click.secho(
            "warning: could not check for the latest pkit release "
            f"(`git ls-remote {DISTRIBUTION_GIT_URL}` failed — offline, missing "
            "credentials, git unavailable, or timed out). The pin is unchanged "
            f"({current_pin}); re-run when the release source is reachable.",
            err=True,
            fg="yellow",
        )
        return

    try:
        pinned_version = Version(current_pin) if current_pin is not None else None
    except InvalidVersion:
        pinned_version = None
    if pinned_version is None:
        # The pin the router routed on is unparseable — refuse to guess an order
        # rather than advance blindly. Degrade like an unresolvable lookup.
        click.secho(
            f"warning: this project's pin ({current_pin!r}) is not valid semver, so "
            f"`pkit upgrade` cannot order it against the latest release (v{latest}). "
            "The pin is unchanged; re-pin with `pkit pin <version>`.",
            err=True,
            fg="yellow",
        )
        return

    if latest == pinned_version:
        click.echo(f"Already at the latest pkit release (v{latest}); pin unchanged.")
        return

    if latest < pinned_version:
        click.echo(
            f"This project is pinned to {current_pin}, which is AHEAD of the latest "
            f"pkit release (v{latest}); leaving the pin unchanged (pkit does not "
            "downgrade a pin)."
        )
        return

    # latest > pin → raise. Flip last, after content lands (ADR-049).
    target = str(latest)
    if dry_run:
        click.echo(
            f"  (dry-run) would raise pin {current_pin} -> {target} (latest pkit "
            "release), reconciling content forward under the target's own code first."
        )
        return
    click.echo(
        f"Raising the pin: {current_pin} -> {target} (latest pkit release); "
        "reconciling content forward under the target's own code first."
    )
    _advance_pin_to(target_root, target)


# --- Tool-staleness detection (ADR-044) ----------------------------------------

# Bounded so an unreachable release source (offline, DNS black-hole) can't hang
# `pkit upgrade`. The check is best-effort; a timeout degrades to a warning.
_LS_REMOTE_TIMEOUT_SECONDS = 5.0


#: Guard env var: set on the re-exec'd child after a self-update, so the child
#: never attempts a second self-update (defence against a re-exec loop, on top of
#: the version comparison that already no-ops once the tool is current).
_SELF_UPDATED_ENV = "PKIT_SELF_UPDATED"


def run_tool_update(dry_run: bool = False, self_update: bool = True) -> None:
    """`pkit upgrade` run **outside any project**: update the global tool only.

    The "just update my tool" case (ADR-044, amended) — there is no project
    content to sync, so this handles the tool axis alone and reports the result,
    instead of erroring on a missing project/manifest.
    """
    if is_route_bypassed(os.environ):
        return
    _maybe_self_update_tool(None, self_update=self_update, dry_run=dry_run)


def _maybe_self_update_tool(
    target_root: Path | None, *, self_update: bool, dry_run: bool
) -> None:
    """Detect a newer released pkit tool and **act** on it (ADR-044, amended):
    self-update the global binary and re-exec, or degrade to instruct.

    - **D3 suppression.** On a source checkout / self-host, reinstalling a released
      tag over working-tree code is nonsensical — skip entirely (no lookup, no
      output). `target_root is None` (run outside a project) is never a checkout.
    - **D1 degrade.** Any lookup failure (offline, no credentials, `git` absent,
      timeout) warns and returns; the caller proceeds unchanged.
    - **Act (amended).** When the tool is behind and self-update is allowed
      (`self_update`, an interactive TTY, not a dry-run, not the guarded re-exec
      child), run `uv tool install --force …@v<latest>` and **re-exec** the same
      command under the new version (never returns on success). Pin-by-default
      (v1.145.0) insulates projects from the global tool, so this no longer has
      cross-project blast radius.
    - **Instruct (degrade).** Otherwise (non-interactive, `--no-self-update`, a
      failed/declined install, or a dry-run) fall back to printing the exact
      command — today's behaviour. Never fails `pkit upgrade`.
    """
    if target_root is not None and is_source_checkout(target_root):
        return

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

    # Stale. Act when allowed; otherwise instruct.
    if self_update and not dry_run and _self_update_allowed():
        if _self_update_tool(latest):
            _reexec_after_self_update()  # never returns on success
        # Install failed/declined → fall through to instruct.
    elif self_update and dry_run:
        click.echo()
        click.echo(
            f"A newer pkit tool is available: v{latest} (you are running "
            f"v{running}). (dry-run) would run `uv tool install --force "
            f"{DISTRIBUTION_GIT_URL}@v{latest}` and re-run this upgrade."
        )
        return

    _instruct_tool_update(latest, running)


def _self_update_allowed() -> bool:
    """True iff we may auto-run the tool self-update: an interactive TTY and not
    the guarded re-exec child. Non-interactive (CI / piped) callers degrade to
    instruct so a network install is never forced under automation."""
    if os.environ.get(_SELF_UPDATED_ENV) == "1":
        return False
    return sys.stdin.isatty() and sys.stdout.isatty()


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


def _reexec_after_self_update() -> None:
    """Re-exec the same `pkit` command under the freshly-installed tool, so the
    content sync + pin run under the new bundle — one seamless upgrade. Sets the
    guard env so the child never self-updates again. Replaces the process image
    (does not return) on success; on an exec failure, returns so the caller can
    proceed with the (old) in-process upgrade rather than bricking."""
    click.echo("Re-running the upgrade under the new version …")
    env = {**os.environ, _SELF_UPDATED_ENV: "1"}
    try:
        os.execvpe("pkit", ["pkit", *sys.argv[1:]], env)
    except OSError:
        return  # exec failed; caller continues under the old binary


def _instruct_tool_update(latest: Version, running: Version) -> None:
    """Print the exact manual update command (ADR-044 D2 instruct — the degrade)."""
    click.echo()
    click.echo(f"A newer pkit tool is available: v{latest} (you are running v{running}).")
    click.echo("Update the tool, then re-run this command:")
    click.echo()
    click.echo(f"    uv tool install --force {DISTRIBUTION_GIT_URL}@v{latest}")
    click.echo("    pkit upgrade")


def _latest_released_version() -> Version | None:
    """Query the distribution source for the highest released `v<semver>` tag.

    Best-effort per ADR-044 D1: returns None on *any* failure — `git` missing
    (`OSError`), the source unreachable (non-zero exit), a bounded-timeout expiry,
    or output with no parseable `v<semver>` tag. The caller degrades loudly. Uses
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
    """Pick the highest `v<semver>` tag from `git ls-remote --tags` output.

    Each line is `<sha>\trefs/tags/<tag>`. Annotated tags also emit a
    dereferenced `<tag>^{}` peel line; the `^{}` suffix is stripped so both
    resolve to the same version. Only `v`-prefixed valid semver tags count;
    anything else (a non-release tag, a malformed ref) is skipped. Returns None
    when no release tag is present.
    """
    versions: list[Version] = []
    for line in ls_remote_output.splitlines():
        ref = line.rpartition("refs/tags/")[2].strip()
        ref = ref.removesuffix("^{}")
        if not ref.startswith("v"):
            continue
        try:
            versions.append(Version(ref[1:]))
        except InvalidVersion:
            continue
    return max(versions) if versions else None


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

    Also checks capability dependency requirements (COR-030): for each installed
    capability that declares ``requires_capabilities``, verifies that each
    declared dependency is installed and its installed version satisfies the
    range. Uses *installed* versions for both sides (backbone upgrade does not
    change capability versions). Conflicts are refused with an actionable hint.
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

    # Capability-dependency check (COR-030): refuse backbone upgrade when an
    # installed capability's declared dependency is absent or out of range.
    # Backbone upgrade uses installed versions for both sides — it does not
    # change capability versions (sync propagates kit-owned content but does
    # not bump capability versions; `pkit capabilities upgrade` does that).
    _check_capability_dep_conflicts_for_upgrade(target_root, components)


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


def _check_capability_dep_conflicts_for_upgrade(
    target_root: Path,
    components: list[ComponentRegistryEntry],
) -> None:
    """Refuse backbone upgrade when any installed capability has an unsatisfied dependency.

    Iterates over every installed capability in the registry, reads its
    installed ``package.yaml`` (not the source copy — backbone upgrade does
    not change capability versions, so the installed copy is authoritative),
    and calls ``capabilities.check_capability_dependencies`` to evaluate each
    declared ``requires_capabilities`` entry against the installed state.

    This is the backbone-wide half of the capability-dependency gate
    (COR-030). The single-capability-upgrade half lives in
    ``upgrade_capability_cmd`` in ``cli.py``.

    Direction: backbone upgrade is not moving any capability version, so
    any desync found here is pre-existing. We apply the "dependent against
    out-of-range dependency" disposition (refuse with hint) rather than the
    "dependency past dependent's range" disposition (warn + force), because
    the operator can resolve by first upgrading the dependency capability.
    """
    from project_kit import capabilities as caps

    dep_conflicts: list[str] = []
    for entry in components:
        if entry.kind != "capability":
            continue
        pkg_yaml_path = (
            target_root / ".pkit" / "capabilities" / entry.name / "package.yaml"
        )
        if not pkg_yaml_path.is_file():
            continue
        pkg = caps._read_package_yaml(pkg_yaml_path)
        if pkg is None or not pkg.requires_capabilities:
            continue
        conflicts = caps.check_capability_dependencies(
            target_root, pkg.requires_capabilities
        )
        for conflict in conflicts:
            if conflict.reason == "absent":
                dep_conflicts.append(
                    f"  capability '{entry.name}' requires capability "
                    f"'{conflict.dep_name}' ({conflict.dep_version_range}), "
                    f"which is not installed — install it first"
                )
            else:
                dep_conflicts.append(
                    f"  capability '{entry.name}' requires capability "
                    f"'{conflict.dep_name}' {conflict.dep_version_range}, "
                    f"but v{conflict.installed_version} is installed — "
                    f"upgrade it first"
                )

    if dep_conflicts:
        raise click.ClickException(
            "capability dependency check failed — installed capabilities have "
            "unsatisfied dependencies:\n" + "\n".join(dep_conflicts) + "\n"
            "Resolve the dependencies first, then retry the backbone upgrade."
        )
