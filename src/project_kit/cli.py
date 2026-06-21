"""pkit CLI entry point.

Phase 1 (foundation) shipped the dispatcher skeleton with `version`.
Phase 2 ports the bash dispatcher's commands one at a time:
PR-D adds `init`; PR-E adds `status`; PR-F adds `new decision`. Phase 3
adds the new COR-004 surface (sync, merge, upgrade, validate,
the rest of new).
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import click

from project_kit import __version__
from project_kit import cli_render
from project_kit.decisions import Namespace, stamp_decision
from project_kit.dispatcher import CapabilityDispatchGroup
from project_kit.install import find_source_kit, find_target_root, install_kit
from project_kit.merge import run_merge
from project_kit.scaffolds import (
    AreaVariant,
    MigrationScope,
    MigrationTier,
    register_kit_shipped_component,
    stamp_adapter,
    stamp_area,
    stamp_capability,
    stamp_migration,
)
from project_kit.agents import Namespace as AgentNamespace, stamp_new_agent
from project_kit.storyboards import ArtifactKind, stamp_new_storyboard
from project_kit import refs as refs_mod
from project_kit.scratchpads import (
    stamp_new_scratchpad,
    transition_to_done,
    transition_to_dropped,
)
from project_kit.status import report_status
from project_kit.sync import run_sync
from project_kit.upgrade import run_upgrade
from project_kit.validate import print_validate_report, run_validate
from project_kit.versioning import (
    PreKind,
    Segment,
    bump_pre,
    bump_version,
    promote_version,
    tag_version,
    unbump_version,
    untag_version,
)

if TYPE_CHECKING:
    from project_kit.process import ProcessEngine


@click.group(cls=CapabilityDispatchGroup, invoke_without_command=True)
@click.version_option(version=__version__, prog_name="pkit")
@click.option(
    "--color",
    type=click.Choice(["auto", "always", "never"]),
    default="auto",
    show_default=True,
    help="Colourize human output: auto (TTY only) | always | never. Honours "
    "NO_COLOR; never load-bearing — plain text carries all structure (ADR-011).",
)
@click.pass_context
def main(ctx: click.Context, color: str) -> None:
    """project-kit CLI.

    Installed capabilities surface their subcommands lazily via the
    `CapabilityDispatchGroup` — namespaces resolve from the backbone
    manifest on every invocation, per [COR-021].
    """
    # The command boundary: resolve the colour decision once per process
    # (ADR-011 §2), so style() never has to sniff a stream it can't see.
    # Mirror the decision onto ctx.color so Click's echo honours it rather than
    # re-deciding (and stripping our SGR) by its own tty sniff.
    ctx.color = cli_render.resolve_color(color)
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@main.group()
def capabilities() -> None:
    """Manage installed capabilities (per COR-017): list, install, uninstall, upgrade.

    Noun-first, consistent with the other resource-domain groups
    (`schemas`, `permissions`, `refs`, `hooks`, `migrations`).
    """


@main.group("agents", invoke_without_command=True)
@click.pass_context
def agents(ctx: click.Context) -> None:
    """Inspect kit-shipped agents + their overlay-category resolution (per COR-013).

    No subcommand: report which agents will deploy vs. be skipped (because they
    reference a category the project overlay doesn't define). Deployment itself
    happens via `pkit sync`; configuration is `.pkit/agents/project/overlay.yaml`.
    """
    if ctx.invoked_subcommand is not None:
        return
    from project_kit import agents_overlay as ao

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    click.echo(ao.render_status(target_root), nl=False)


@agents.command("reconcile")
@click.option(
    "--write",
    is_flag=True,
    default=False,
    help="Append the missing categories to the overlay (default: dry-run, show only).",
)
def agents_reconcile(write: bool) -> None:
    """Surface referenced-but-undefined overlay categories into overlay.yaml as
    commented stubs (per COR-013). Explicit + idempotent; dry-run by default."""
    from project_kit import agents_overlay as ao

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    try:
        _added, report = ao.reconcile_overlay(target_root, write=write)
    except FileNotFoundError as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(report, nl=False)


@agents.command("adopt")
@click.argument("agent_name", metavar="AGENT")
def agents_adopt(agent_name: str) -> None:
    """Create the conventional doc dirs, wire the overlay, and deploy AGENT.

    For each overlay category the agent references that is not yet defined in
    `.pkit/agents/project/overlay.yaml`:

    \b
    1. Creates the conventional default directory if absent (with a seed README
       explaining the directory's purpose).
    2. Writes the category into the overlay uncommented with the conventional path.
       An adopter-set value is never overwritten.

    Then runs the adapter's deploy step so the agent ends up in `.claude/agents/`.

    Idempotent: re-running on an already-adopted agent reports no changes and
    re-deploys (the deploy step is itself idempotent).
    """
    from project_kit import agents_overlay as ao

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    try:
        result = ao.adopt_agent(target_root, agent_name)
    except click.ClickException:
        raise
    except FileNotFoundError as exc:
        raise click.ClickException(str(exc)) from exc

    lines: list[str] = []
    if result.dirs_created:
        lines.append(cli_render.style("strong", f"created {len(result.dirs_created)} director(ies):"))
        for d in result.dirs_created:
            lines.append(f"  {d}/")
            lines.append(f"    (seed README.md written explaining the directory's purpose)")
    if result.categories_wired:
        lines.append(cli_render.style("strong", f"wired {len(result.categories_wired)} overlay categor(ies):"))
        for cat in result.categories_wired:
            lines.append(f"  {cat}")
    if result.categories_already_set:
        lines.append(cli_render.style("strong",
            f"{len(result.categories_already_set)} categor(ies) already defined (unchanged):"))
        for cat in result.categories_already_set:
            lines.append(f"  {cat}")
    if not result.dirs_created and not result.categories_wired:
        lines.append(cli_render.style("strong",
            f"agent {agent_name!r}: overlay already complete — no changes."))
    if result.deployed:
        lines.append("")
        lines.append(cli_render.style("strong", f"agent {agent_name!r} deployed."))
    click.echo("\n".join(lines))


@main.group(invoke_without_command=True)
@click.pass_context
def version(ctx: click.Context) -> None:
    """Show the source kit's backbone version, or bump it."""
    if ctx.invoked_subcommand is None:
        click.echo(f"pkit {__version__}")


@version.command("bump")
@click.argument("segment", type=click.Choice(["patch", "minor", "major", "pre"]))
@click.option(
    "--pre",
    "pre",
    type=click.Choice(["a", "b", "rc"]),
    default=None,
    help="Append a PEP 440 pre-release suffix (a=alpha, b=beta, rc=release-candidate). "
    "Pre-release bumps do not broaden requires_backbone.",
)
def version_bump(segment: str, pre: str | None) -> None:
    """Bump .pkit/VERSION (segment: patch | minor | major | pre).

    With `--pre <kind>`, appends a PEP 440 pre-release suffix
    (`X.Y.Z<kind>1`). Without it, `pre` as the segment increments the
    existing pre-release counter (`1.2.0rc1` -> `1.2.0rc2`). See PRJ-002.
    """
    source_kit = find_source_kit()
    if segment == "pre":
        if pre is not None:
            raise click.ClickException(
                "`bump pre` and `--pre <kind>` are mutually exclusive. "
                "Use `bump pre` to increment an existing pre-release counter, "
                "or `bump <segment> --pre <kind>` to start a new pre-release line."
            )
        bump_pre(source_kit)
        return
    bump_version(source_kit, _cast_segment(segment), pre=_cast_pre(pre))


@version.command("promote")
def version_promote() -> None:
    """Drop the pre-release suffix from VERSION (e.g., `1.2.0rc3` -> `1.2.0`).

    Refuses if VERSION has no pre-release suffix. See PRJ-002.
    """
    source_kit = find_source_kit()
    promote_version(source_kit)


@version.command("tag")
@click.option(
    "--push",
    is_flag=True,
    default=False,
    help="After tagging, push the new tag to the `origin` remote.",
)
def version_tag(push: bool) -> None:
    """Tag HEAD as `v<version>` from .pkit/VERSION (per PRJ-002 + PRJ-004)."""
    source_kit = find_source_kit()
    tag_version(source_kit, push=push)


@version.command("untag")
@click.option(
    "--push",
    is_flag=True,
    default=False,
    help="Also delete the tag on the `origin` remote.",
)
def version_untag(push: bool) -> None:
    """Remove the `v<version>` tag matching .pkit/VERSION (local; --push for remote)."""
    source_kit = find_source_kit()
    untag_version(source_kit, push=push)


@version.command("unbump")
def version_unbump() -> None:
    """Revert the most recent `bump`: narrow requires_backbone + rewrite VERSION.

    Order: run `pkit version untag` first; unbump refuses while the tag
    for the current VERSION still exists locally. Refuses when the prior
    version cannot be determined unambiguously (e.g., pre-release, pre-1.0
    boundary) — set VERSION by hand in that case.
    """
    source_kit = find_source_kit()
    unbump_version(source_kit)


def _cast_segment(value: str) -> Segment:
    """Click's `Choice` already validates; this widens str → Segment for the type checker."""
    if value == "patch":
        return "patch"
    if value == "minor":
        return "minor"
    return "major"


def _cast_pre(value: str | None) -> PreKind | None:
    """Click's `Choice` already validates; widen str → PreKind for the type checker."""
    if value is None:
        return None
    if value == "a":
        return "a"
    if value == "b":
        return "b"
    return "rc"


@main.command()
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Show what would be installed without writing any files (per COR-004).",
)
def init(dry_run: bool) -> None:
    """First install: propagation + seed + merge per COR-001 / COR-002 / COR-004."""
    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException(
            "pkit init must be run inside a git repository or a directory "
            "pkit can resolve as a project root."
        )
    install_kit(target_root, dry_run=dry_run)


@main.command()
def status() -> None:
    """Show how project-kit is wired in this project (read-only)."""
    report_status()


@main.command()
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Show what would be refreshed without writing any files (per COR-004).",
)
def sync(dry_run: bool) -> None:
    """Re-run propagation: refresh kit-owned content from source (per COR-001)."""
    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    run_sync(target_root, dry_run=dry_run)


@main.command()
@click.argument("targets", nargs=-1)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Show which merge primitives would run without invoking them (per COR-004).",
)
def merge(targets: tuple[str, ...], dry_run: bool) -> None:
    """Re-run merge delivery on adapter-owned config files (per COR-002).

    Optional TARGETS filter to specific adapter names; all installed adapters
    that ship a merge primitive run by default.
    """
    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    run_merge(target_root, targets=targets, dry_run=dry_run)


@main.command()
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Show what would be upgraded without writing any files (per COR-004).",
)
def upgrade(dry_run: bool) -> None:
    """Transition the project to a newer backbone (per COR-010).

    Bumps the project to the source kit's current backbone version. To
    upgrade a single capability, use `pkit capabilities upgrade <name>`.
    """
    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    run_upgrade(target_root, dry_run=dry_run)


@main.group("visibility", invoke_without_command=True)
@click.pass_context
def visibility(ctx: click.Context) -> None:
    """Control pkit's git footprint (per ADR-009). No subcommand = status.

    `shared` (default): pkit committed; `.git/info/exclude` kept clear.
    `private`: hide the whole footprint via the per-clone `.git/info/exclude`
    (no committed `.gitignore` is ever written) + a confirm-gated untrack.
    `untrack`: the standalone index cleanup (its own verb — the destructive
    git-index gesture is never silently folded into a mode flip).
    """
    if ctx.invoked_subcommand is not None:
        return
    from project_kit import visibility as vis

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    click.echo(vis.status(target_root), nl=False)


def _visibility_target() -> Path:
    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    return target_root


@visibility.command("shared")
@click.option("--dry-run", is_flag=True, default=False,
              help="Preview clearing the .git/info/exclude region without changing anything.")
def visibility_shared(dry_run: bool) -> None:
    """Return pkit to committed (default): clear pkit's `.git/info/exclude` region."""
    from project_kit import visibility as vis

    click.echo(vis.set_visibility(_visibility_target(), "shared", dry_run=dry_run, confirm=click.confirm), nl=False)


@visibility.command("private")
@click.option("--dry-run", is_flag=True, default=False,
              help="Preview the .git/info/exclude write + untrack set without changing anything.")
def visibility_private(dry_run: bool) -> None:
    """Hide the whole footprint via the per-clone `.git/info/exclude` (no committed
    `.gitignore` is ever written) + a confirm-gated untrack of tracked footprint files."""
    from project_kit import visibility as vis

    click.echo(vis.set_visibility(_visibility_target(), "private", dry_run=dry_run, confirm=click.confirm), nl=False)


@visibility.command("untrack")
@click.option("--dry-run", is_flag=True, default=False,
              help="Preview the footprint files that would be removed from the index.")
def visibility_untrack(dry_run: bool) -> None:
    """Remove already-tracked pkit footprint files from the git index (per ADR-009).

    Footprint-only, confirm-gated, working-copy-preserving (`git rm --cached`).
    Refuses mid-merge/rebase or when footprint paths have staged changes. Its own
    subcommand so the one git-index-mutating gesture stays explicit, never folded
    silently into a `shared`/`private` mode flip.
    """
    from project_kit import visibility as vis

    click.echo(vis.untrack(_visibility_target(), dry_run=dry_run, confirm=click.confirm), nl=False)


@capabilities.command("upgrade")
@click.argument("name")
@click.option(
    "--interactive",
    is_flag=True,
    default=False,
    help="Prompt per collision (override / skip / inspect) when the upgraded "
    "source introduces new naming collisions (per COR-017).",
)
@click.option(
    "--force",
    is_flag=True,
    default=False,
    help="Proceed even when upgrading this capability would desync an installed "
    "dependent's declared version range (COR-030). Mirrors the uninstall "
    "--force shape; use when cascade-upgrading dependents manually.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Show what would happen without writing any files.",
)
def upgrade_capability_cmd(name: str, interactive: bool, force: bool, dry_run: bool) -> None:
    """Refresh a single installed capability from source (per COR-017).

    Walks the capability's source subtree, detects any *new* naming
    collisions introduced since install, and either:
    - Refreshes in place if no new collisions are found, preserving any
      skip state from the original install.
    - Refuses (without --interactive) and suggests `--interactive` if
      new collisions exist.
    - Prompts per collision and then refreshes with the merged skip
      state (with --interactive).

    Also enforces capability dependency constraints (COR-030) with a
    direction-split disposition:
    - If the new source version of this capability (the *dependent*) has
      requirements its dependencies don't satisfy → refuse with hint.
    - If this capability is a *dependency* for other installed capabilities
      and the new version would fall outside their declared range → loud
      warning and require --force to proceed (not a hard block; a hard
      block would deadlock since cascade-upgrade is out of scope).
    """
    from project_kit import capabilities as caps

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    if not (target_root / ".pkit").is_dir():
        raise click.ClickException(
            f"{target_root}/.pkit/ does not exist. Run 'pkit init' first."
        )

    if not caps.is_installed(target_root, name):
        raise click.ClickException(
            f"capability {name!r} is not installed. "
            f"Use `pkit capabilities install {name}` first."
        )

    source_kit = find_source_kit()
    capability_source = caps.find_capability_in_source(source_kit, name)
    if capability_source is None:
        raise click.ClickException(
            f"capability {name!r} no longer ships from source at {source_kit}/capabilities/. "
            "Use `pkit capabilities uninstall` to remove the orphan, or sync "
            "the source kit if you expect it to ship."
        )

    # --- Capability dependency check: direction-split (COR-030) ---

    # Direction 1 — this capability is the *dependent*: its new source version
    # may declare requires_capabilities that the installed dependencies don't
    # satisfy. Refuse with hint (operator controls which version to upgrade to).
    dep_conflicts = caps.check_capability_dependencies(
        target_root, capability_source.package.requires_capabilities
    )
    if dep_conflicts:
        lines = []
        for conflict in dep_conflicts:
            if conflict.reason == "absent":
                lines.append(
                    f"    - '{conflict.dep_name}' ({conflict.dep_version_range}) "
                    f"is not installed"
                )
            else:
                lines.append(
                    f"    - '{conflict.dep_name}' {conflict.dep_version_range} "
                    f"required but v{conflict.installed_version} is installed"
                )
        raise click.ClickException(
            f"capability {name!r} v{capability_source.package.version} has "
            f"unsatisfied dependencies:\n" + "\n".join(lines) + "\n"
            "Install or upgrade the required capabilities first, then retry."
        )

    # Direction 2 — this capability is a *dependency*: upgrading it to the new
    # source version may push it outside the declared range of installed
    # dependents. Warn loudly + require --force (not a hard block — a hard block
    # would deadlock since cascade-upgrade is out of scope per COR-030).
    new_version = capability_source.package.version
    desynced_dependents = _find_desynced_dependents(
        target_root, dep_name=name, new_dep_version=new_version
    )
    if desynced_dependents and not force:
        click.echo(
            "\n  " + cli_render.style("strong",
                f"Warning: upgrading {name!r} to v{new_version} would desync "
                f"{len(desynced_dependents)} installed dependent(s):")
        )
        for dep_cap, declared_range in desynced_dependents:
            click.echo(
                f"    - '{dep_cap}' declares {name!r} {declared_range} "
                f"(v{new_version} is outside this range)"
            )
        raise click.ClickException(
            "refusing to upgrade: the new version would desync installed dependents.\n"
            "Upgrade those capabilities to versions compatible with the new range, "
            "then retry — or pass --force to proceed anyway and fix dependents "
            "manually (the deadlock-free override per COR-030)."
        )
    if desynced_dependents and force:
        click.echo(
            "\n  " + cli_render.style("strong",
                f"Warning (--force): upgrading {name!r} to v{new_version} "
                f"desyncs {len(desynced_dependents)} dependent(s):")
        )
        for dep_cap, declared_range in desynced_dependents:
            click.echo(
                f"    - '{dep_cap}' declares {name!r} {declared_range} "
                f"(v{new_version} is outside this range)"
            )
        click.echo(
            "  Proceeding under --force; upgrade dependent capabilities "
            "to restore consistency."
        )

    # --- Collision detection ---

    # Detect collisions introduced by the upgraded source. Filter
    # self-collisions against the currently-installed copy — those will
    # be replaced in place.
    new_collisions = caps.detect_upgrade_collisions(target_root, capability_source)
    prior_skipped = list(caps.read_prior_skipped_artifacts(target_root, name))

    if new_collisions and not interactive:
        click.echo(
            "\n  " + cli_render.style("strong",
                f"{len(new_collisions)} new naming collision(s) introduced by "
                f"v{capability_source.package.version}:")
        )
        for finding in new_collisions:
            click.echo(
                f"    - {finding.artifact_kind} '{finding.artifact_name}' "
                f"collides with {finding.target_path.relative_to(target_root)}"
            )
        raise click.ClickException(
            f"refusing to upgrade with unresolved collisions. "
            f"Re-run with --interactive to resolve them."
        )

    new_skipped: list[tuple[str, str]] = []
    if new_collisions and interactive:
        click.echo(
            "\n  " + cli_render.style("strong", f"{len(new_collisions)} new collision(s) — resolve per artifact:") + "\n"
        )
        for finding in new_collisions:
            choice = _resolve_collision_interactive(
                target_root, finding, dry_run=dry_run
            )
            if choice == "skip":
                new_skipped.append((finding.artifact_kind, finding.artifact_name))

    # Merge prior + new skip state. De-dup by (kind, name).
    merged_skipped = tuple(
        sorted(set(prior_skipped).union(new_skipped))
    )

    refreshed_path = caps.refresh_capability(
        target_root,
        capability_source,
        skipped_artifacts=merged_skipped,
        dry_run=dry_run,
    )

    verb = "Would refresh" if dry_run else "Refreshed"
    skip_note = (
        f" ({len(merged_skipped)} artifact(s) skipped)" if merged_skipped else ""
    )
    click.echo(
        "\n  " + cli_render.style("strong",
            f"{verb} capability {name!r} -> v{capability_source.package.version} "
            f"at {refreshed_path.relative_to(target_root)}/{skip_note}")
    )

    if not dry_run:
        # Re-run installed adapter primitives so the harness side picks
        # up any newly-added skills/agents from the upgraded capability.
        from project_kit import install as install_mod
        ctx = install_mod.InstallContext(
            target_root=target_root,
            source_kit=source_kit,
            dry_run=False,
        )
        install_mod.run_installed_adapter_primitives(ctx)


@main.command()
@click.option(
    "--include-refs/--no-refs",
    default=True,
    show_default=True,
    help="Include the agent/skill reference-graph check (bidirectional + hook closure). "
    "Disable on corpora with pre-existing drift while it's being cleaned up.",
)
def validate(include_refs: bool) -> None:
    """Check project state against invariants (per COR-004). Exit 1 if issues found."""
    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    issues = run_validate(target_root)
    if include_refs:
        ref_issues = refs_mod.validate_corpus(target_root)
        # Convert refs.Issue to validate.Issue for unified reporting.
        from project_kit.validate import Issue as ValidateIssue

        for ri in ref_issues:
            issues.append(ValidateIssue(location=ri.location, diagnosis=ri.diagnosis))
    print_validate_report(target_root, issues)
    if issues:
        raise SystemExit(1)


# --- refs family (per COR-013 / #74) ----------------------------------


@main.group()
def refs() -> None:
    """Reference-graph operations across agents, skills, decisions, hooks (per COR-013)."""


@refs.command("validate")
def refs_validate() -> None:
    """Bidirectional consistency + hook closure check across the artifact corpus."""
    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    issues = refs_mod.validate_corpus(target_root)
    lines = [cli_render.style("title", "Reference validation — bidirectional consistency + hook closure"), ""]
    if not issues:
        lines.append("  " + cli_render.style("strong", "All checks passed."))
        click.echo("\n".join(lines) + "\n", nl=False)
        return
    lines.append("  " + cli_render.style("strong", f"{len(issues)} issue(s) found:"))
    for issue in issues:
        lines += [f"    {issue.location}", f"      → {issue.diagnosis}"]
    click.echo("\n".join(lines) + "\n", nl=False)
    raise SystemExit(1)


@refs.command("show")
@click.argument("artifact_name")
def refs_show(artifact_name: str) -> None:
    """Show outgoing references for one agent or skill (by name)."""
    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    artifacts = refs_mod.load_artifacts(target_root)
    matches = [a for a in artifacts if a.name == artifact_name]
    if not matches:
        raise click.ClickException(f"no agent or skill named {artifact_name!r}.")
    for art in matches:
        click.echo(cli_render.style("title", f"{art.kind} {art.namespace}/{art.name}"))
        click.echo(f"    path: {art.path.relative_to(target_root)}")
        for bucket, items in refs_mod.outgoing_refs(art).items():
            if items:
                click.echo("    " + cli_render.style("heading", f"{bucket}:"))
                for item in items:
                    click.echo(f"      {item}")


@refs.command("who-references")
@click.argument("target")
def refs_who_references(target: str) -> None:
    """Reverse lookup: list agents/skills that reference the target (path, record ID, hook)."""
    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    artifacts = refs_mod.load_artifacts(target_root)
    matches = refs_mod.who_references(artifacts, target)
    if not matches:
        click.echo(f"  no artifact references {target!r}.")
        return
    click.echo(cli_render.style("strong", f"{len(matches)} artifact(s) reference {target!r}:"))
    for art in matches:
        click.echo(f"    {art.kind} {art.namespace}/{art.name}")


@refs.command("lookup")
@click.argument("record_id")
def refs_lookup(record_id: str) -> None:
    """Resolve a record ID (`COR-005`, `PRJ-002`) to its current file path."""
    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    path = refs_mod.resolve_record(target_root, record_id)
    if path is None:
        raise click.ClickException(f"no record matches {record_id!r}.")
    click.echo(path.relative_to(target_root))


@refs.command("rename")
@click.argument("old")
@click.argument("new")
@click.option("--dry-run", is_flag=True, default=False, help="Report what would change without writing.")
def refs_rename(old: str, new: str, dry_run: bool) -> None:
    """Bulk rewrite a reference value across every agent/skill (frontmatter + body)."""
    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    modified = refs_mod.rename_reference(target_root, old, new, dry_run=dry_run)
    if not modified:
        click.echo(f"  no references to {old!r} found.")
        return
    verb = "would modify" if dry_run else "modified"
    click.echo(cli_render.style("strong", f"  {verb} {len(modified)} file(s):"))
    for path in modified:
        click.echo(f"    {path.relative_to(target_root)}")


@refs.command("rot")
def refs_rot() -> None:
    """List references to superseded records, dropped scratchpads, or missing files."""
    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    artifacts = refs_mod.load_artifacts(target_root)
    issues = refs_mod.find_rot(target_root, artifacts)
    lines = [cli_render.style("title", "Reference rot — superseded records, dropped scratchpads, missing files"), ""]
    if not issues:
        lines.append("  no rotten references found.")
        click.echo("\n".join(lines) + "\n", nl=False)
        return
    lines.append("  " + cli_render.style("strong", f"{len(issues)} rotten reference(s):"))
    for issue in issues:
        lines += [f"    {issue.location}", f"      → {issue.diagnosis}"]
    click.echo("\n".join(lines) + "\n", nl=False)


@refs.command("graph")
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["ascii", "text", "dot"]),
    default="ascii",
    show_default=True,
    help="Output format. `ascii` (default) is a tree-style diagram with "
    "box-drawing characters; `text` is a plain outline; `dot` is Graphviz "
    "(pipe to `dot -Tpng > graph.png` to render).",
)
def refs_graph(fmt: str) -> None:
    """Emit the reference graph for visualisation or downstream tooling."""
    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    artifacts = refs_mod.load_artifacts(target_root)
    if fmt == "dot":
        click.echo(refs_mod.emit_graph_dot(artifacts))
    elif fmt == "text":
        click.echo(refs_mod.emit_graph_text(artifacts))
    else:
        click.echo(refs_mod.emit_graph_ascii(artifacts))


# --- hooks family (per COR-013 / #74) ---------------------------------


@main.group()
def hooks() -> None:
    """Hook-registry queries (per COR-013): list, resolve, who-needs, who-provides."""


@hooks.command("list")
def hooks_list() -> None:
    """List every declared hook with its providers (in precedence order)."""
    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    providers = refs_mod.load_hook_providers(target_root)
    artifacts = refs_mod.load_artifacts(target_root)
    needed = {hk for art in artifacts for hk in art.declared.needs}
    declared_hooks = sorted({p.hook for p in providers} | needed)
    if not declared_hooks:
        click.echo("  no hooks declared.")
        return
    lines = [cli_render.style("title", f"Hooks — {len(declared_hooks)} declared")
             + "   (bound provider by precedence)"]
    for hook in declared_hooks:
        winner = refs_mod.resolve_hook(providers, hook)
        marker = f" -> {winner.tier}:{winner.source}" if winner else " (no provider)"
        lines.append(f"  {hook}{marker}")
    click.echo("\n".join(lines) + "\n", nl=False)


@hooks.command("resolve")
@click.argument("hook")
def hooks_resolve(hook: str) -> None:
    """Show the currently-bound provider for a hook (by precedence)."""
    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    providers = refs_mod.load_hook_providers(target_root)
    winner = refs_mod.resolve_hook(providers, hook)
    if winner is None:
        raise click.ClickException(f"no provider declared for hook {hook!r}.")
    click.echo(f"  {hook} -> {winner.tier}:{winner.source} ({winner.implementation})")


@hooks.command("who-needs")
@click.argument("hook")
def hooks_who_needs(hook: str) -> None:
    """List agents/skills that declare `needs: <hook>`."""
    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    artifacts = refs_mod.load_artifacts(target_root)
    matches = [a for a in artifacts if hook in a.declared.needs]
    if not matches:
        click.echo(f"  no artifact declares need for {hook!r}.")
        return
    click.echo(cli_render.style("strong", f"{len(matches)} artifact(s) need {hook!r}:"))
    for art in matches:
        click.echo(f"  {art.kind} {art.namespace}/{art.name}")


@hooks.command("who-provides")
@click.argument("hook")
def hooks_who_provides(hook: str) -> None:
    """List all providers for a hook (skills + adapter/capability package.yaml)."""
    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    providers = refs_mod.load_hook_providers(target_root)
    matches = [p for p in providers if p.hook == hook]
    if not matches:
        click.echo(f"  no provider declared for hook {hook!r}.")
        return
    order = {"project": 0, "capability": 1, "adapter": 2, "core": 3}
    matches.sort(key=lambda p: order.get(p.tier, 99))
    click.echo(cli_render.style("strong", f"{len(matches)} provider(s) for {hook!r}:"))
    for p in matches:
        click.echo(f"  {p.tier:8} {p.source:30} {p.implementation}")


@main.group()
def migrations() -> None:
    """Migration framework operations (per COR-010)."""


@migrations.command("check-diff")
@click.option(
    "--base",
    "base_ref",
    default="origin/main",
    show_default=True,
    help="Base ref to diff against. Default is `origin/main` (CI's typical PR base).",
)
@click.option(
    "--include-working-tree",
    is_flag=True,
    default=False,
    help="Include staged + unstaged changes in the diff (pre-commit use). "
    "Without this flag, only committed changes are checked (CI's view).",
)
def migrations_check_diff(base_ref: str, include_working_tree: bool) -> None:
    """Verify migration coverage in the diff between `base_ref` and the project state.

    Walks the diff for migration-triggering changes (renames + deletions
    in kit-owned trees per COR-010 / `.pkit/rules/core.md` rule 7), then
    checks whether the same diff includes a matching migration script.

    Default scope: committed branch changes only (`<base_ref>...HEAD`)
    — what CI sees on a PR. With `--include-working-tree`, the scope
    extends to staged + unstaged changes — what's about to be committed.
    The pre-commit form for local use.

    Exits 0 when covered or no triggers exist; exits 1 when triggers
    exist without matching migrations, listing the affected tiers so the
    author can land the missing scripts.
    """
    from project_kit import migrations as migrations_mod

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    try:
        report = migrations_mod.check_diff_coverage(
            target_root, base_ref, include_working_tree=include_working_tree
        )
    except RuntimeError as exc:
        raise click.ClickException(str(exc)) from exc
    migrations_mod.render_coverage_report(report)
    if not report.is_covered:
        raise SystemExit(1)


@main.group()
def permissions() -> None:
    """Inspect the permission model and reconcile it against live harness state (per COR-028). Read-only."""


@permissions.command("explain")
@click.argument("agent", required=False)
def permissions_explain(agent: str | None) -> None:
    """Render the per-agent permission mental model (grants, scopes, effects)."""
    from project_kit import permissions as perm

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    click.echo(perm.explain(target_root, agent), nl=False)


@permissions.command("diff")
@click.argument("agent", required=False)
def permissions_diff(agent: str | None) -> None:
    """Reconcile the model against live `.claude/settings.json` — flags live rules no granted privilege justifies, and dimensions the harness can't enforce."""
    from project_kit import permissions as perm

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    report, _clean = perm.diff(target_root, agent)
    click.echo(report, nl=False)


@permissions.command("catalog")
def permissions_catalog() -> None:
    """List the privilege catalog (baseline + extensions)."""
    from project_kit import permissions as perm

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    click.echo(perm.catalog(target_root), nl=False)


@permissions.command("overview")
def permissions_overview() -> None:
    """Role-grouped catalog overview: guardrails (deny by default) vs enablers (grant to enable), with provenance and who each is granted to."""
    from project_kit import permissions as perm

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    click.echo(perm.overview(target_root), nl=False)


@permissions.command("grant")
@click.argument("subject")
@click.argument("privilege")
@click.option("--scope", multiple=True, help="Directory glob constraining the grant "
              "(repeatable; only for scope-typed privileges).")
@click.option("--deny", is_flag=True, default=False, help="Record a deny grant (default: allow).")
def permissions_grant(subject: str, privilege: str, scope: tuple[str, ...], deny: bool) -> None:
    """Grant SUBJECT a PRIVILEGE (optionally scoped) — writes the model."""
    from project_kit import permissions as perm

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    try:
        click.echo(perm.grant(target_root, subject, privilege, scope, deny))
    except perm.PermissionsError as exc:
        raise click.ClickException(str(exc)) from exc


@permissions.command("revoke")
@click.argument("subject")
@click.argument("privilege")
def permissions_revoke(subject: str, privilege: str) -> None:
    """Remove SUBJECT's grant of PRIVILEGE."""
    from project_kit import permissions as perm

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    click.echo(perm.revoke(target_root, subject, privilege))


@permissions.command("mode")
@click.argument("mode", required=False, type=click.Choice(["additive", "managed"]))
def permissions_mode(mode: str | None) -> None:
    """Show (no arg) or set the ownership mode: additive | managed."""
    from project_kit import permissions as perm

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    click.echo(perm.show_mode(target_root) if mode is None else perm.set_mode(target_root, mode))


@permissions.command("enable")
def permissions_enable() -> None:
    """Turn on live enforcement: register the PreToolUse hook + ensure the native guardrail denies (the double-lock). Opt-in per issue #247."""
    from project_kit import permissions as perm

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    try:
        click.echo(perm.enable(target_root))
    except perm.PermissionsError as exc:
        raise click.ClickException(str(exc)) from exc


@permissions.command("disable")
def permissions_disable() -> None:
    """Turn off live enforcement: strip the PreToolUse hook registration (native guardrail denies stay)."""
    from project_kit import permissions as perm

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    try:
        click.echo(perm.disable(target_root))
    except perm.PermissionsError as exc:
        raise click.ClickException(str(exc)) from exc


@permissions.command("apply")
def permissions_apply() -> None:
    """Additively realize the model into `.claude/settings.json` (union the projected allow rules + ensure guardrail denies) and report the out-of-harness gap. Additive + idempotent; managed-mode wholesale regeneration is separate."""
    from project_kit import permissions as perm

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    try:
        click.echo(perm.apply(target_root), nl=False)
    except perm.PermissionsError as exc:
        raise click.ClickException(str(exc)) from exc


@permissions.group("setup", invoke_without_command=True)
@click.pass_context
def permissions_setup(ctx: click.Context) -> None:
    """Goal-oriented setup commands (per ADR-007): stand up a composite goal stepwise + resumably. No goal = list goals."""
    if ctx.invoked_subcommand is not None:
        return
    from project_kit import permissions as perm

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    click.echo(perm.setup_list(target_root), nl=False)


@permissions_setup.group("autonomy", invoke_without_command=True)
@click.option("--profile", default="autonomous", show_default=True,
              help="The autonomy profile to activate as the goal's intent layer.")
@click.pass_context
def permissions_setup_autonomy(ctx: click.Context, profile: str) -> None:
    """Stand up autonomous agents: profile + enforcement + OS sandbox, then prove it.

    Resumable: re-run after the session restart to verify; finished steps are
    skipped. The goal is declared reached only when the probe proof passes."""
    if ctx.invoked_subcommand is not None:
        return
    from project_kit import permissions as perm

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    try:
        report, ok = perm.setup_autonomy(target_root, profile=profile)
    except perm.PermissionsError as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(report, nl=False)
    if not ok:
        raise SystemExit(1)


@permissions_setup_autonomy.command("down")
def permissions_setup_autonomy_down() -> None:
    """Tear the autonomy goal's live switches down (hook + sandbox), reporting residual state loudly."""
    from project_kit import permissions as perm

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    try:
        click.echo(perm.setup_autonomy_down(target_root), nl=False)
    except perm.PermissionsError as exc:
        raise click.ClickException(str(exc)) from exc


@permissions.command("probe")
@click.option("--subject", default="operator", show_default=True,
              help="Decide as this subject: `operator` or `agent:<name>`.")
@click.option("--live", is_flag=True, default=False,
              help="Also execute reachability probes against the sandbox credential "
                   "denyRead floor (open-attempt only; never reads content).")
def permissions_probe(subject: str, live: bool) -> None:
    """Probe-by-probe proof that the current model rejects/allows what it declares.

    Drives the live hook's entry point (hook_decide) over curated concrete requests
    and checks each verdict against the declared model; also checks the native
    double-lock denies. Read-only; non-zero exit if any probe is broken."""
    from project_kit import permissions as perm

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    try:
        report, ok = perm.probe(target_root, subject=subject, live=live)
    except perm.PermissionsError as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(report, nl=False)
    if not ok:
        raise SystemExit(1)


@permissions.group("sandbox", invoke_without_command=True)
@click.pass_context
def permissions_sandbox(ctx: click.Context) -> None:
    """OS-sandbox confinement (per ADR-004): prompt-free scripting inside the box. No subcommand = status."""
    if ctx.invoked_subcommand is not None:
        return
    from project_kit import permissions as perm

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    click.echo(perm.sandbox_status(target_root), nl=False)


@permissions_sandbox.command("enable")
@click.option("--strict", is_flag=True, default=False,
              help="Also lock the unsandboxed fail-over escape hatch "
                   "(allowUnsandboxedCommands: false). Optional hardening; breaks "
                   "legit fail-over like `git push` / `gh` — pair with excludedCommands.")
@click.option("--dangerously-allow-unconfined", is_flag=True, default=False,
              help="Operator-only, per-invocation: write failIfUnavailable: false "
                   "(fail-open). Never a committable default — re-running enable "
                   "without it restores fail-closed.")
def permissions_sandbox_enable(strict: bool, dangerously_allow_unconfined: bool) -> None:
    """Turn on the OS sandbox with prompt-free scripting (fail-closed, additive, idempotent)."""
    from project_kit import permissions as perm

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    try:
        click.echo(perm.sandbox_enable(target_root, strict=strict,
                                       dangerously_allow_unconfined=dangerously_allow_unconfined),
                   nl=False)
    except perm.PermissionsError as exc:
        raise click.ClickException(str(exc)) from exc


@permissions_sandbox.command("disable")
def permissions_sandbox_disable() -> None:
    """Turn the OS sandbox off (enabled: false); operator sandbox keys survive."""
    from project_kit import permissions as perm

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    try:
        click.echo(perm.sandbox_disable(target_root), nl=False)
    except perm.PermissionsError as exc:
        raise click.ClickException(str(exc)) from exc


@permissions_sandbox.group("toolkit")
def permissions_sandbox_toolkit() -> None:
    """Confinement toolkits (per ADR-008): per-tool sandbox allowances, classified narrowing/widening."""


@permissions_sandbox_toolkit.command("list")
def permissions_sandbox_toolkit_list() -> None:
    """List available confinement toolkits, marked by boundary effect + which are accommodated."""
    from project_kit import permissions as perm

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    click.echo(perm.confinement_list(target_root), nl=False)


@permissions_sandbox_toolkit.command("show")
@click.argument("name")
def permissions_sandbox_toolkit_show(name: str) -> None:
    """Show a toolkit's exact allowances, each marked narrowing or widening."""
    from project_kit import permissions as perm

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    try:
        click.echo(perm.confinement_show(target_root, name), nl=False)
    except perm.PermissionsError as exc:
        raise click.ClickException(str(exc)) from exc


@permissions_sandbox.command("accommodate")
@click.argument("tools", nargs=-1)
@click.option("--detect", is_flag=True, default=False,
              help="Also scan the project for known tools (lockfiles/manifests) and accommodate them.")
@click.option("--socket", "socket_path", default=None,
              help="Allow a one-off unix socket by path (e.g. --socket \"$SSH_AUTH_SOCK\") — "
                   "narrowing, per-machine, never committed (per ADR-010). Use --name to label it.")
@click.option("--name", default="manual", show_default=True,
              help="Logical name for a --socket allowance (its recompute-replace key).")
@click.option("--remove", is_flag=True, default=False,
              help="Remove the named toolkits' (or the --socket --name) pkit-authored entries (operator entries untouched).")
def permissions_sandbox_accommodate(tools: tuple[str, ...], detect: bool, socket_path: str | None,
                                    name: str, remove: bool) -> None:
    """Apply NARROWING allowances so legit tooling works inside the box.

    Toolkits (build caches, sockets) are recorded in permission-config and auto-applied
    by `setup autonomy`. `--socket <path>` is a one-off per-machine socket allowance
    (never committed) — for the SSH agent / signing sockets. For carving a command OUT
    of the box, use `sandbox exclude` (explicit, loud)."""
    from project_kit import permissions as perm

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    try:
        if socket_path is not None or (remove and not tools and name != "manual"):
            click.echo(perm.accommodate_socket(target_root, socket_path or "", name=name,
                                               remove=remove), nl=False)
        else:
            click.echo(perm.accommodate(target_root, tools, detect=detect, remove=remove), nl=False)
    except perm.PermissionsError as exc:
        raise click.ClickException(str(exc)) from exc


@permissions_sandbox.command("exclude")
@click.argument("command", required=False)
@click.option("--weaker-tls", is_flag=True, default=False,
              help="Instead of excluding a command, weaken network TLS isolation (widening).")
@click.option("--remove", is_flag=True, default=False,
              help="Put the command back inside the box (remove the exclusion).")
def permissions_sandbox_exclude(command: str | None, weaker_tls: bool, remove: bool) -> None:
    """WIDENING gesture: carve a command OUT of the box so it runs UNCONFINED.

    Loud, per-invocation, NEVER written to committed config, never proposed by detect,
    never applied by setup (per ADR-008). Reported by `sandbox status` and `probe`."""
    from project_kit import permissions as perm

    if not command and not weaker_tls:
        raise click.ClickException("give a COMMAND to exclude, or --weaker-tls.")
    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    try:
        click.echo(perm.sandbox_exclude(target_root, command or "", remove=remove,
                                        weaker_tls=weaker_tls), nl=False)
    except perm.PermissionsError as exc:
        raise click.ClickException(str(exc)) from exc


@permissions.group("profile")
def permissions_profile() -> None:
    """Named autonomy profiles (per ADR-005): a posture + a layered grant-set you select per project."""


@permissions_profile.command("list")
def permissions_profile_list() -> None:
    """List available profiles (shipped + project), marking the active one."""
    from project_kit import permissions as perm

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    click.echo(perm.list_profiles(target_root), nl=False)


@permissions_profile.command("show")
@click.argument("name")
def permissions_profile_show(name: str) -> None:
    """Show a profile's posture + layered grants."""
    from project_kit import permissions as perm

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    try:
        click.echo(perm.show_profile(target_root, name), nl=False)
    except perm.PermissionsError as exc:
        raise click.ClickException(str(exc)) from exc


@permissions_profile.command("activate")
@click.argument("name")
@click.option("--no-apply", is_flag=True, default=False,
              help="Set the model only; don't realize to settings (run `apply` yourself later).")
def permissions_profile_activate(name: str, no_apply: bool) -> None:
    """Activate a profile: set posture + layer its grants, then `apply` (unless --no-apply). Does not enable the hook."""
    from project_kit import permissions as perm

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    try:
        click.echo(perm.activate_profile(target_root, name, apply_after=not no_apply), nl=False)
    except perm.PermissionsError as exc:
        raise click.ClickException(str(exc)) from exc


@main.group()
def schemas() -> None:
    """Validate capability YAML schemas against their JSON Schema companions (per COR-018 + the .pkit/schemas/ area)."""


@schemas.command("validate")
@click.argument("path", type=click.Path(exists=True, path_type=Path), required=False)
@click.option(
    "--shape-only",
    is_flag=True,
    default=False,
    help="Skip the cross-file reference-resolution pass; check shape only. "
    "Useful mid-refactor when a referenced target schema doesn't exist yet.",
)
def schemas_validate(path: Path | None, shape_only: bool) -> None:
    """Validate YAML schemas against their JSON Schema companions + resolve references.

    Default (no PATH): walks every installed capability's `schemas/`
    directory under the current project, validates each YAML against
    its sibling `<name>.schema.json`, and reports findings.

    With PATH: validates the YAML schemas at the given file or
    directory. Useful for adopters running the validator against
    non-capability data files that follow the same conventions.

    Two passes run by default:
    - **Shape** — does the YAML satisfy the JSON Schema (per COR-018)?
    - **References** — does every `[<namespace>:<id>]` token in the YAML
      resolve to a real id in the named namespace (per COR-019)?

    With `--shape-only`, only the shape pass runs. Targets must declare
    where their ids live via an `x-pkit-id-collection` annotation in the
    JSON Schema companion (a JSON Pointer into the data YAML).
    """
    from project_kit import schemas_validate as schemas_mod

    resolve = not shape_only
    if path is not None:
        report = schemas_mod.validate_path(
            path, target_root=find_target_root(), resolve=resolve
        )
    else:
        target_root = find_target_root()
        if target_root is None:
            raise click.ClickException("not in a project tree.")
        report = schemas_mod.validate_all(target_root, resolve=resolve)

    schemas_mod.print_report(report)
    if not report.is_clean:
        raise click.ClickException(f"{len(report.issues)} schema validation issue(s) found.")


@schemas.command("list")
def schemas_list() -> None:
    """List every schema under installed capabilities, grouped by capability.

    For each schema, shows whether it owns a namespace (companion declares
    `x-pkit-id-collection`) and, if so, how many entries the namespace
    holds plus a preview of the ids. Consumer schemas (no own namespace)
    are marked.
    """
    from project_kit import schemas_validate as schemas_mod

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    summaries = schemas_mod.summarize_schemas(target_root)
    schemas_mod.print_schema_list(summaries)


@schemas.command("show")
@click.argument("namespace")
def schemas_show(namespace: str) -> None:
    """Show one namespace's entries with one-line summaries.

    NAMESPACE matches the schema's filename stem (e.g., `issue-types`,
    `validation-severity`). Errors cleanly when the namespace is unknown
    or ambiguous (declared by multiple capabilities).
    """
    from project_kit import schemas_validate as schemas_mod

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    detail = schemas_mod.detail_namespace(target_root, namespace)
    if isinstance(detail, str):
        raise click.ClickException(detail)
    schemas_mod.print_namespace_detail(detail, target_root=target_root)


@schemas.command("add")
@click.argument("namespace")
@click.argument("entry_id")
@click.option(
    "--from",
    "from_path",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Path to a YAML or JSON file with the new entry's data. Pass `-` "
    "or omit to read from stdin.",
)
def schemas_add(namespace: str, entry_id: str, from_path: Path | None) -> None:
    """Add a new entry to an existing namespace's id collection.

    NAMESPACE is the schema's filename stem; ENTRY_ID is the new entry's
    kebab-case id. Entry fields come from `--from <path>` (YAML or JSON)
    or stdin. The companion JSON Schema's per-entry shape governs which
    fields are required; the command re-validates after the write and
    restores the prior file if validation fails.

    Refuses if the entry id is already in use (use a different id, or
    edit the existing entry directly).
    """
    from project_kit import schemas_authoring as authoring

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    source: Path | None = None
    if from_path is not None and str(from_path) != "-":
        if not from_path.is_file():
            raise click.ClickException(f"file not found: {from_path}")
        source = from_path
    try:
        entry_data = authoring.load_entry_data(source)
        yaml_path = authoring.add_entry_to_namespace(
            target_root, namespace, entry_id, entry_data
        )
    except authoring.SchemaAuthoringError as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(f"Added entry {entry_id!r} to namespace {namespace!r} at "
               f"{yaml_path.relative_to(target_root)}.")


@schemas.command("rename")
@click.argument("namespace")
@click.argument("old_id")
@click.argument("new_id")
def schemas_rename(namespace: str, old_id: str, new_id: str) -> None:
    """Rename an entry id across the schemas mechanism.

    Updates three reference classes in one atomic operation:

    \b
    1. The namespace owner's collection (mapping key or list item id).
    2. Every value-position typed token `[<namespace>:<old_id>]` in
       any YAML under installed capabilities.
    3. Every mapping-key reference in fields whose companion declares
       `x-pkit-keys-from-namespace: <namespace>`.

    All affected files are validated after the rewrite; on any failure,
    every file is restored to its prior state and the issues are
    surfaced.
    """
    from project_kit import schemas_authoring as authoring

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    try:
        result = authoring.rename_entry(target_root, namespace, old_id, new_id)
    except authoring.SchemaAuthoringError as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo(
        f"Renamed {old_id!r} → {new_id!r} in namespace {namespace!r} "
        f"({len(result.changes)} change(s)):"
    )
    for change in result.changes:
        click.echo(
            f"  [{change.kind}] {change.yaml_path.relative_to(target_root)}"
        )
        click.echo(f"    {change.detail}")


@schemas.command("resolve")
@click.argument("token")
def schemas_resolve(token: str) -> None:
    """Resolve a typed token (`[<namespace>:<id>]`) to its target entry.

    Useful when you encounter a token in someone else's schema or output
    and want to see what it points at. Errors cleanly when the token's
    shape is malformed, the namespace isn't installed, or the id isn't
    in the namespace's collection.
    """
    from project_kit import schemas_validate as schemas_mod

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    resolution = schemas_mod.resolve_token_to_target(target_root, token)
    if isinstance(resolution, str):
        raise click.ClickException(resolution)
    schemas_mod.print_token_resolution(resolution, target_root=target_root)


@main.group()
def data() -> None:
    """Validate adopter data files against capability schemas (per COR-022)."""


@data.command("validate")
@click.argument("path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--shape-only",
    is_flag=True,
    default=False,
    help="Skip cross-file reference resolution; validate shape only (per COR-029).",
)
def data_validate(path: Path, shape_only: bool) -> None:
    """Validate adopter data files against their bound capability schemas.

    The binding from a data file to a schema resolves in two steps
    (per COR-023):

    \b
    1. **Field-first.** A top-level `pkit_schema: <capability>:<schema>`
       field in the data file is authoritative.
    2. **Capability fallback.** Otherwise, the resolver walks every
       installed capability's schema `binds_to:` globs and uses the first
       matching one.

    If neither yields a binding, the file is reported as unresolved.
    A schema-version mismatch between the data file's `schema_version`
    and the capability schema's `schema_version` is refused with a
    migration hint; auto-migration is out of scope in v1.

    By default a second pass resolves cross-file typed references (per
    COR-029): a `[<namespace>:<id>]` token at a field the schema marks
    `x-pkit-reference-namespace` must name an id defined by some in-scope
    file bound to that namespace. The validation scope is exactly PATH —
    the id pool is the union of in-scope bound files. A dangling or
    duplicate id is an error; a reference whose namespace has no bound file
    in scope is a warning (a normal in-progress state). `--shape-only`
    skips this pass.

    PATH is a file or directory. Directories are walked recursively for
    `*.yaml` files (`.pkit/` subtrees are excluded — those are kit-managed,
    not adopter data).
    """
    from project_kit import data_validate as data_mod

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    report = data_mod.validate_path(
        path, target_root, resolve_references=not shape_only
    )
    data_mod.print_report(report)
    if report.has_errors:
        raise click.ClickException(
            f"{len(report.errors)} data-validation error(s) found."
        )


@main.group()
def settings() -> None:
    """Manage `.claude/settings.json` (per COR-002)."""


@settings.command("consolidate")
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Show what would be removed without writing.",
)
@click.option(
    "--yes",
    is_flag=True,
    default=False,
    help="Skip the confirmation prompt and write directly.",
)
def settings_consolidate(dry_run: bool, yes: bool) -> None:
    """Remove redundant entries from `.claude/settings.json` + `.claude/settings.local.json`.

    An entry is redundant when a broader rule in the union of both
    files already covers it — e.g., `Bash(pkit new *)` is redundant
    when `Bash(pkit:*)` is present (in either file). The merge
    primitive doesn't auto-clean these on sync (it only adds, per
    COR-001's preserve-adopter-content stance); this command is the
    explicit cleanup pass.

    Walks both `.claude/settings.json` (committed) and
    `.claude/settings.local.json` (gitignored, per-machine). A redundant
    entry is removed from whichever file(s) contain it.

    Default: print the plan grouped by file, prompt for confirmation,
    then write.
    --dry-run: print only.
    --yes:     skip confirmation.
    """
    from project_kit import settings_consolidate as consolidator

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    plan = consolidator.detect_consolidation_opportunities(target_root)
    if plan is None:
        click.echo("  no .claude/settings.json or .claude/settings.local.json at this project.")
        return
    if not plan.has_redundancies:
        click.echo("  no redundant entries across .claude/settings.json + settings.local.json.")
        return

    files = plan.files_to_modify
    click.echo(
        "  " + cli_render.style("strong", f"Found {len(plan.pairs)} redundant entry(ies) across {len(files)} file(s):") + "\n"
    )
    for source_file in files:
        rel = source_file.relative_to(target_root)
        file_pairs = plan.pairs_in(source_file)
        click.echo("  " + cli_render.style("heading", f"{rel} ({len(file_pairs)}):"))
        for pair in file_pairs:
            click.echo(f"    {pair.redundant!r}")
            click.echo(f"      subsumed by  {pair.subsumed_by!r}")
        click.echo()

    if dry_run:
        click.echo("  (dry-run — no changes written)")
        return

    if not yes:
        file_list = ", ".join(str(f.relative_to(target_root)) for f in files)
        confirmed = click.confirm(
            f"  Remove these entries from {file_list}?", default=False
        )
        if not confirmed:
            click.echo("  cancelled.")
            return

    modified = consolidator.apply_consolidation(target_root, plan)
    rels = ", ".join(str(f.relative_to(target_root)) for f in modified)
    click.echo("  " + cli_render.style("strong", f"Removed {len(plan.pairs)} entry(ies) from {rels}."))


# --- Capability commands (per COR-017) ------------------------------------


@capabilities.command("install")
@click.argument("name")
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Show what would be installed without writing files.",
)
def install_capability_cmd(name: str, dry_run: bool) -> None:
    """Install a capability: copy subtree into adopter, register in manifest, re-deploy."""
    from project_kit import capabilities as caps

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    if not (target_root / ".pkit").is_dir():
        raise click.ClickException(
            f"{target_root}/.pkit/ does not exist. Run 'pkit init' first."
        )

    source_kit = find_source_kit()
    capability_source = caps.find_capability_in_source(source_kit, name)
    if capability_source is None:
        raise click.ClickException(
            f"no capability named {name!r} ships in this kit version. "
            f"Try `pkit capabilities list` to see what's available."
        )

    # Pre-flight: already installed?
    if caps.is_installed(target_root, name):
        raise click.ClickException(
            f"capability {name!r} is already installed. "
            f"Use `pkit capabilities upgrade {name}` to refresh."
        )

    # Pre-flight: capability dependency check (COR-030).
    # Refuse if any declared dependency is absent or its installed version
    # is outside the required range. Never auto-installs.
    dep_conflicts = caps.check_capability_dependencies(
        target_root, capability_source.package.requires_capabilities
    )
    if dep_conflicts:
        lines = []
        for conflict in dep_conflicts:
            if conflict.reason == "absent":
                lines.append(
                    f"    - '{conflict.dep_name}' ({conflict.dep_version_range}) "
                    f"is not installed"
                )
            else:
                lines.append(
                    f"    - '{conflict.dep_name}' {conflict.dep_version_range} "
                    f"required but v{conflict.installed_version} is installed"
                )
        raise click.ClickException(
            f"capability {name!r} v{capability_source.package.version} has "
            f"unsatisfied dependencies:\n" + "\n".join(lines) + "\n"
            "Install or upgrade the required capabilities first."
        )

    # Pre-flight: collision detection.
    collisions = caps.detect_collisions(target_root, capability_source)
    skipped: list[tuple[str, str]] = []

    if collisions:
        click.echo("\n  " + cli_render.style("strong", f"{len(collisions)} naming collision(s) detected:") + "\n")
        for finding in collisions:
            choice = _resolve_collision_interactive(target_root, finding, dry_run=dry_run)
            if choice == "skip":
                skipped.append((finding.artifact_kind, finding.artifact_name))

    # Install.
    installed_path = caps.install_capability(
        target_root,
        capability_source,
        skipped_artifacts=tuple(skipped),
        dry_run=dry_run,
    )

    verb = "Would install" if dry_run else "Installed"
    skip_note = f" ({len(skipped)} artifact(s) skipped)" if skipped else ""
    click.echo(
        "\n  " + cli_render.style("strong",
            f"{verb} capability {name!r} v{capability_source.package.version} "
            f"at {installed_path.relative_to(target_root)}/{skip_note}")
    )

    if not dry_run:
        # Re-run installed adapter primitives so the harness picks up
        # the capability's newly-copied skills and agents (e.g.,
        # deploy-skills.sh symlinks them into .claude/skills/).
        # Mirrors what `pkit capabilities upgrade` does after refresh and
        # what `pkit init` does after its first-time copy.
        from project_kit import install as install_mod
        ctx = install_mod.InstallContext(
            target_root=target_root,
            source_kit=source_kit,
            dry_run=False,
        )
        install_mod.run_installed_adapter_primitives(ctx)


def _find_desynced_dependents(
    target_root: Path, dep_name: str, new_dep_version: str
) -> list[tuple[str, str]]:
    """Find installed capabilities whose declared range for *dep_name* excludes *new_dep_version*.

    Used by the single-capability upgrade direction-2 check (COR-030): when
    upgrading a dependency capability, detect installed dependents that would
    become desynced by the new version.

    Returns a list of (dependent_name, declared_range_string) pairs.
    Uses installed versions of the dependent side — only the dependency's
    version is moving; per the architect note in COR-030 + issue #90.
    """
    from packaging.specifiers import InvalidSpecifier, SpecifierSet
    from packaging.version import InvalidVersion, Version
    from project_kit import capabilities as caps

    try:
        new_ver = Version(new_dep_version)
    except InvalidVersion:
        return []

    declared_dependents = caps.find_declared_dependents(target_root, dep_name)
    desynced: list[tuple[str, str]] = []
    for dep_cap in declared_dependents:
        pkg_yaml_path = (
            target_root / ".pkit" / "capabilities" / dep_cap / "package.yaml"
        )
        if not pkg_yaml_path.is_file():
            continue
        pkg = caps._read_package_yaml(pkg_yaml_path)
        if pkg is None:
            continue
        for req in pkg.requires_capabilities:
            if req.name != dep_name:
                continue
            try:
                spec = SpecifierSet(req.version)
            except InvalidSpecifier:
                continue
            if new_ver not in spec:
                desynced.append((dep_cap, req.version))
            break
    return desynced


def _resolve_collision_interactive(target_root, finding, *, dry_run: bool) -> str:
    """Prompt the adopter for override/skip/inspect on a single collision.

    Loops on `inspect` (re-prompts after showing diff) until adopter
    picks override or skip. Returns the final choice as a string.
    """
    from project_kit import capabilities as caps  # local to avoid cycle

    while True:
        click.echo(
            f"  - {finding.artifact_kind} '{finding.artifact_name}' "
            f"collides with existing {finding.target_path.relative_to(target_root)}"
        )
        choice = click.prompt(
            "    [override / skip / inspect]",
            type=click.Choice(["override", "skip", "inspect"]),
            default="inspect",
            show_default=False,
        )
        if choice == "inspect":
            _show_unified_diff(finding.target_path, finding.source_path)
            continue
        return choice


def _show_unified_diff(existing: Path, incoming: Path) -> None:
    """Display a unified diff between the existing file and the incoming one."""
    import subprocess

    try:
        result = subprocess.run(
            ["git", "diff", "--no-index", "--color=always", str(existing), str(incoming)],
            capture_output=True,
            text=True,
        )
        click.echo(result.stdout)
    except FileNotFoundError:
        # git not available — fall back to a plain difflib diff.
        import difflib

        existing_lines = existing.read_text().splitlines(keepends=True)
        incoming_lines = incoming.read_text().splitlines(keepends=True)
        diff = difflib.unified_diff(
            existing_lines, incoming_lines,
            fromfile=str(existing), tofile=str(incoming),
        )
        for line in diff:
            click.echo(line, nl=False)


@capabilities.command("uninstall")
@click.argument("name")
@click.option(
    "--force",
    is_flag=True,
    default=False,
    help="Override the safety checks; remove even if references exist or "
    "other installed capabilities declare a dependency on this one (COR-030).",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Show what would be removed without deleting files.",
)
def uninstall_capability_cmd(name: str, force: bool, dry_run: bool) -> None:
    """Uninstall a capability: remove subtree, unregister from manifest, re-deploy."""
    from project_kit import capabilities as caps

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")

    if not caps.is_installed(target_root, name):
        raise click.ClickException(f"capability {name!r} is not installed.")

    # Declared-dependent safety check (COR-030): refuse when another installed
    # capability declares this one in its requires_capabilities. This catches
    # behavioural dependencies that leave no textual citation (complementing
    # the find_references check below). Both checks are gated by --force.
    if not force:
        declared_dependents = caps.find_declared_dependents(target_root, name)
        if declared_dependents:
            click.echo(
                "\n  " + cli_render.style("strong",
                    f"Refusing to uninstall {name!r}: "
                    f"{len(declared_dependents)} installed capability(ies) "
                    f"declare a dependency on it:") + "\n"
            )
            for dep_cap in declared_dependents:
                click.echo(f"    - {dep_cap}")
            raise click.ClickException(
                "Uninstall or upgrade the dependent capabilities first, "
                "or pass --force to override."
            )

    # Reference safety check.
    if not force:
        references = caps.find_references(target_root, name)
        if references:
            click.echo(
                "\n  " + cli_render.style("strong", f"Refusing to uninstall {name!r}: {len(references)} reference(s) found:") + "\n"
            )
            # Show a compact summary (capped to first 10).
            for path, snippet in references[:10]:
                rel = path.relative_to(target_root) if target_root in path.parents else path
                click.echo(f"    {rel}: {snippet}")
            if len(references) > 10:
                click.echo(f"    ... and {len(references) - 10} more.")
            raise click.ClickException(
                "Clean references first, or pass --force to override."
            )

    removed_path = caps.uninstall_capability(target_root, name, dry_run=dry_run)
    verb = "Would remove" if dry_run else "Removed"
    click.echo(
        "\n  " + cli_render.style("strong",
            f"{verb} capability {name!r} from {removed_path.relative_to(target_root)}")
    )

    if not dry_run:
        # Re-run installed adapter primitives so the harness drops
        # stale symlinks to the removed capability's content (e.g.,
        # deploy-skills.sh's "stale removal" pass).
        from project_kit import install as install_mod
        ctx = install_mod.InstallContext(
            target_root=target_root,
            source_kit=find_source_kit(),
            dry_run=False,
        )
        install_mod.run_installed_adapter_primitives(ctx)


@capabilities.command("list")
def list_capabilities_cmd() -> None:
    """List capabilities available in the kit source and which are installed."""
    from project_kit import capabilities as caps

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    source_kit = find_source_kit()
    available, installed = caps.list_capabilities(target_root, source_kit)

    if not available:
        click.echo(cli_render.view(
            title=cli_render.title("Capabilities", "0 available"),
            sections=[cli_render.section(empty="(none ship in this kit version)")],
        ), nl=False)
        return
    rows = [{"name": n, "status": "installed" if n in installed else ""} for n in available]
    click.echo(cli_render.view(
        title=cli_render.title("Capabilities", f"{len(available)} available",
                               gloss="install with `pkit capabilities install <name>`"),
        sections=[cli_render.section(rows=rows, columns=["name", "status"])],
        commands=[("pkit capabilities install <name>", "install one into this project")],
    ), nl=False)


# --- New artifacts (decisions, agents, etc.) ------------------------------


@main.group()
def new() -> None:
    """Scaffold new methodology artifacts: decisions, adapters, migrations, areas, capabilities, schemas, scratchpads, agents, storyboards."""


@new.command("decision")
@click.argument("namespace", type=click.Choice(["core", "project", "adr"]))
@click.argument("slug")
def new_decision(namespace: str, slug: str) -> None:
    """Stamp a new decision-record stub.

    Namespaces:
      core     → COR-NNN at .pkit/decisions/core/
      project  → PRJ-NNN at .pkit/decisions/project/
      adr      → ADR-NNN at the overlay's <adr-records> path (per COR-024/COR-025)
    """
    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    if not (target_root / ".pkit").is_dir():
        raise click.ClickException(
            f"{target_root}/.pkit/ does not exist. Run 'pkit init' from this project's root first."
        )
    target = stamp_decision(target_root, namespace=cast_namespace(namespace), slug=slug)
    try:
        rel = target.relative_to(target_root)
    except ValueError:
        rel = target
    click.echo(f"Stamped: {rel}")


def cast_namespace(value: str) -> Namespace:
    """Click's `Choice` already validates; this widens str → Namespace for the type checker."""
    if value == "core":
        return "core"
    if value == "adr":
        return "adr"
    return "project"


@new.command("area")
@click.argument("name")
@click.option(
    "--variant",
    type=click.Choice(["universal", "adapter-umbrella", "specialized"]),
    default="specialized",
    show_default=True,
    help="Variant determining the area's internal layout (per COR-011).",
)
def new_area(name: str, variant: str) -> None:
    """Scaffold a new area at .pkit/<name>/ (per COR-011)."""
    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    result = stamp_area(target_root, name=name, variant=_cast_area_variant(variant))
    rel = result.area_dir.relative_to(target_root)
    click.echo(f"Stamped: {rel}/ (variant: {variant})")


@new.command("adapter")
@click.argument("name")
def new_adapter(name: str) -> None:
    """Scaffold a new adapter at .pkit/adapters/<name>/ (per COR-005)."""
    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    result = stamp_adapter(target_root, name=name)
    rel = result.adapter_dir.relative_to(target_root)
    click.echo(f"Stamped: {rel}/")
    # Register in the backbone manifest so the adapter is immediately
    # discoverable (per COR-005's "Scaffold output is wired" implication).
    project_manifest_rel = f".pkit/adapters/{name}/project/manifest.yaml"
    register_kit_shipped_component(
        target_root, kind="adapter", name=name, manifest_path=project_manifest_rel
    )


@new.command("schema")
@click.argument("capability")
@click.argument("name")
@click.option(
    "--collection-form",
    type=click.Choice(["mapping", "list"]),
    default="mapping",
    show_default=True,
    help="Collection layout: `mapping` (keys are ids; the dominant form) or "
    "`list` (each item has `id:`; pick when entries need stable ordering or "
    "per-entry metadata that doesn't fit a mapping value). Ignored with "
    "`--no-namespace`.",
)
@click.option(
    "--collection-name",
    default="entries",
    show_default=True,
    help="Top-level YAML key holding the id collection (e.g., `types`, "
    "`states`, `severities`). Defaults to `entries`; pick a domain-specific "
    "name when one exists. Ignored with `--no-namespace`.",
)
@click.option(
    "--no-namespace",
    is_flag=True,
    default=False,
    help="Stamp a document-shaped schema (one resource per file) rather "
    "than a namespace owner. No top-level id collection, no "
    "`x-pkit-id-collection` annotation, flat `properties: {}` placeholder. "
    "Use for single-document specs (e.g., a `trip.yaml` describing one "
    "trip) where the file IS the resource, not a collection of entries.",
)
def new_schema(
    capability: str,
    name: str,
    collection_form: str,
    collection_name: str,
    no_namespace: bool,
) -> None:
    """Scaffold a new YAML + JSON Schema companion pair.

    CAPABILITY is the target: the reserved value `core` stamps into the
    core schemas area (`.pkit/schemas/`); any other value names a
    capability (`.pkit/capabilities/<capability>/schemas/`).

    Default: stamps a **namespace owner** — top-level id collection +
    `x-pkit-id-collection` annotation pointing at it. Pass
    `--no-namespace` to stamp a **document-shaped schema** instead: one
    resource per file, flat `properties: {}` placeholder, no collection
    annotation.

    Validates the stamp via `pkit schemas validate`; rolls back both
    files if anything fails. Refuses if the schema already exists, or if
    the capability doesn't exist (run `pkit new capability` first).
    """
    from project_kit import schemas_authoring as authoring

    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    try:
        result = authoring.stamp_new_schema(
            target_root,
            capability=capability,
            name=name,
            collection_form=collection_form,  # type: ignore[arg-type]
            collection_name=collection_name,
            no_namespace=no_namespace,
        )
    except authoring.SchemaAuthoringError as exc:
        raise click.ClickException(str(exc)) from exc

    yaml_rel = result.yaml_path.relative_to(target_root)
    companion_rel = result.companion_path.relative_to(target_root)
    click.echo(f"Stamped: {yaml_rel}")
    click.echo(f"Stamped: {companion_rel}")
    if no_namespace:
        click.echo(
            "Next: declare the document's top-level fields in the "
            "companion's `properties`, then fill the YAML body accordingly."
        )
    else:
        click.echo(
            f"Next: fill the companion's $defs.entry.properties with per-entry "
            f"field declarations, then add entries via "
            f"`pkit schemas add {name} <id> --from <path>`."
        )


@new.command("capability")
@click.argument("name")
def new_capability(name: str) -> None:
    """Scaffold a new capability at .pkit/capabilities/<name>/ (per COR-017).

    Stamps `package.yaml`, an adopter-facing `README.md`, and the five
    standard subdirectories (decisions, skills, agents, scripts, schemas)
    so the author has a complete skeleton to populate.

    Unlike `pkit new adapter`, capabilities are NOT registered
    in the backbone manifest by the scaffolding step — they are
    kit-shipped from the source-of-edit's perspective, and adopters
    register them per-project via `pkit capabilities install <name>`.
    """
    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    result = stamp_capability(target_root, name=name)
    rel = result.capability_dir.relative_to(target_root)
    click.echo(f"Stamped: {rel}/")


@new.command("migration")
@click.option(
    "--tier",
    type=click.Choice(["backbone", "adapter", "capability"]),
    required=True,
    help="Which migration tree the script lands in (per COR-010 / COR-017).",
)
@click.option(
    "--component",
    type=str,
    default=None,
    help="Component name; required for --tier adapter / capability.",
)
@click.option(
    "--version",
    type=str,
    default=None,
    help="Target minor version (X.Y.0). Defaults to the tier's current version.",
)
@click.option(
    "--name",
    type=str,
    default=None,
    help="Kebab-case slug for the migration file (e.g., 'add-status-labels').",
)
@click.option(
    "--scope",
    type=click.Choice(["manifest-schema", "structural", "resource"]),
    default="resource",
    show_default=True,
    help="Migration scope (per COR-010); affects the script's boilerplate header.",
)
def new_migration(
    tier: str,
    component: str | None,
    version: str | None,
    name: str | None,
    scope: str,
) -> None:
    """Scaffold a numbered migration script in the right <X.Y.0>/ directory."""
    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    result = stamp_migration(
        target_root,
        tier=_cast_migration_tier(tier),
        component=component,
        version=version,
        slug=name,
        scope=_cast_migration_scope(scope),
    )
    rel = result.script.relative_to(target_root)
    click.echo(f"Stamped: {rel}")


@new.command("agent")
@click.argument("namespace", type=click.Choice(["core", "project"]))
@click.argument("name")
@click.option(
    "--with-storyboard",
    is_flag=True,
    default=False,
    help="Stamp folder-form per COR-015 with a sibling storyboard.md per COR-016. "
    "Pass this when the agent drives a scripted interaction scenario; the "
    "storyboard is the design source authored before the agent body.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Show what would be stamped without writing the file (per COR-004).",
)
def new_agent(namespace: str, name: str, with_storyboard: bool, dry_run: bool) -> None:
    """Stamp a new agent stub at .pkit/agents/<namespace>/<name>.md (per COR-013 + COR-015).

    With --with-storyboard, stamps folder layout with a sibling storyboard
    scaffold (per COR-016) — for agents driving scripted interaction scenarios.
    """
    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    if not (target_root / ".pkit").is_dir():
        raise click.ClickException(
            f"{target_root}/.pkit/ does not exist. Run 'pkit init' from this project's root first."
        )
    target = stamp_new_agent(
        target_root,
        name=name,
        namespace=_cast_agent_namespace(namespace),
        with_storyboard=with_storyboard,
        dry_run=dry_run,
    )
    rel = target.relative_to(target_root)
    verb = "Would stamp" if dry_run else "Stamped"
    if with_storyboard:
        sibling = target.parent / "storyboard.md"
        rel_sb = sibling.relative_to(target_root)
        click.echo(f"{verb}: {rel}")
        click.echo(f"{verb}: {rel_sb}")
    else:
        click.echo(f"{verb}: {rel}")


def _cast_agent_namespace(value: str) -> AgentNamespace:
    if value == "core":
        return "core"
    return "project"


@new.command("storyboard")
@click.argument("artifact_kind", type=click.Choice(["agent"]))
@click.argument("name")
@click.option(
    "--scenario",
    type=str,
    default=None,
    help="Slug for a per-scenario storyboard file (stamps `<scenario>.storyboard.md`). "
    "Default: one `storyboard.md` covering one or more scenarios.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Show what would be stamped without writing the file (per COR-004).",
)
def new_storyboard(
    artifact_kind: str,
    name: str,
    scenario: str | None,
    dry_run: bool,
) -> None:
    """Stamp a storyboard sibling to an implementing artifact (per COR-016).

    Today's only supported artifact-kind is `agent`. The command resolves
    the named agent (in either namespace, either flat or folder form);
    if the agent is currently flat, it migrates to folder form first per
    COR-015. Future application classes (cli, migration, tutorial) slot
    in as additional artifact-kind values without renaming this command.
    """
    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    if not (target_root / ".pkit").is_dir():
        raise click.ClickException(
            f"{target_root}/.pkit/ does not exist. Run 'pkit init' from this project's root first."
        )
    target = stamp_new_storyboard(
        target_root,
        kind=_cast_artifact_kind(artifact_kind),
        name=name,
        scenario=scenario,
        dry_run=dry_run,
    )
    rel = target.relative_to(target_root)
    verb = "Would stamp" if dry_run else "Stamped"
    click.echo(f"{verb}: {rel}")


def _cast_artifact_kind(value: str) -> ArtifactKind:
    if value == "agent":
        return "agent"
    raise click.ClickException(f"unsupported artifact-kind: {value!r}")


@new.command("scratchpad")
@click.argument("slug")
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Show what would be stamped without writing the file (per COR-004).",
)
def new_scratchpad(slug: str, dry_run: bool) -> None:
    """Stamp a new active-state scratchpad note (per COR-012)."""
    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    if not (target_root / ".pkit").is_dir():
        raise click.ClickException(
            f"{target_root}/.pkit/ does not exist. Run 'pkit init' from this project's root first."
        )
    target = stamp_new_scratchpad(target_root, slug=slug, dry_run=dry_run)
    rel = target.relative_to(target_root)
    verb = "Would stamp" if dry_run else "Stamped"
    click.echo(f"{verb}: {rel}")


@main.group()
def scratchpad() -> None:
    """Manage scratchpad notes (per COR-012): retire active notes by transitioning to done or dropped."""


@scratchpad.command("done")
@click.argument("slug")
@click.option(
    "--produced",
    multiple=True,
    metavar="REF",
    help="Artifact reference the note produced (record ID, file path, or URL). Repeatable.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Show what would change without moving the file or writing frontmatter.",
)
def scratchpad_done(slug: str, produced: tuple[str, ...], dry_run: bool) -> None:
    """Move an active scratchpad note to done/, appending retired/produced frontmatter."""
    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    src, dst = transition_to_done(target_root, slug=slug, produced=produced, dry_run=dry_run)
    src_rel = src.relative_to(target_root)
    dst_rel = dst.relative_to(target_root)
    verb = "Would move" if dry_run else "Moved"
    click.echo(f"{verb}: {src_rel} -> {dst_rel}")


@scratchpad.command("drop")
@click.argument("slug")
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Show what would change without moving the file or writing frontmatter.",
)
def scratchpad_drop(slug: str, dry_run: bool) -> None:
    """Move an active scratchpad note to dropped/, appending retired frontmatter."""
    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not in a project tree.")
    src, dst = transition_to_dropped(target_root, slug=slug, dry_run=dry_run)
    src_rel = src.relative_to(target_root)
    dst_rel = dst.relative_to(target_root)
    verb = "Would move" if dry_run else "Moved"
    click.echo(f"{verb}: {src_rel} -> {dst_rel}")


def _cast_area_variant(value: str) -> AreaVariant:
    """Click's `Choice` already validates; this widens str → AreaVariant for pyright."""
    if value == "universal":
        return "universal"
    if value == "adapter-umbrella":
        return "adapter-umbrella"
    return "specialized"


def _cast_migration_tier(value: str) -> MigrationTier:
    """Click's `Choice` already validates; this widens str → MigrationTier for pyright."""
    if value == "backbone":
        return "backbone"
    if value == "capability":
        return "capability"
    return "adapter"


def _cast_migration_scope(value: str) -> MigrationScope:
    """Click's `Choice` already validates; this widens str → MigrationScope for pyright."""
    if value == "manifest-schema":
        return "manifest-schema"
    if value == "structural":
        return "structural"
    return "resource"


# --- process substrate (per COR-031 / ADR-020) ------------------------


@main.group()
def process() -> None:
    """Process-substrate engine (per COR-031): resolve position, validate +
    execute guarded moves, render the self-explaining status view.

    Content-free — addresses a capability's process definition as
    `<capability>:<process-id>` and reads the subject's reality. Homed in the
    binary (ADR-020); capability wrappers call it by subprocess.
    """


def _load_engine(address: str, subject: str | None) -> ProcessEngine:
    """Resolve the repo root + definition + engine for a process address."""
    from project_kit import process as process_mod

    try:
        repo_root = process_mod.resolve_repo_root()
        definition = process_mod.load_definition(repo_root, address)
    except process_mod.ProcessError as exc:
        raise click.ClickException(str(exc)) from exc
    subject_key = subject if subject is not None else process_mod.SINGLETON_SUBJECT
    return process_mod.ProcessEngine(definition, repo_root, subject=subject_key)


@process.command("status")
@click.argument("address")
@click.option("--subject", default=None, help="Subject key (singleton default: the fixed key).")
@click.option("--actor", default="operator", show_default=True,
              help="Evaluate gate prechecks as this actor (cross-authority).")
@click.option("--json", "as_json", is_flag=True, default=False,
              help="Emit structured JSON instead of the narrative view.")
def process_status(address: str, subject: str | None, actor: str, as_json: bool) -> None:
    """Where the subject is · why · how it got here · legal moves · next hint."""
    from project_kit import process as process_mod

    engine = _load_engine(address, subject)
    try:
        if as_json:
            click.echo(process_mod.render_status_json(engine, actor), nl=False)
        else:
            click.echo(process_mod.render_status_narrative(engine, actor), nl=False)
    except process_mod.ProcessError as exc:
        raise click.ClickException(str(exc)) from exc


@process.command("can-move")
@click.argument("address")
@click.option("--to", "to_state", required=True, help="Target state id.")
@click.option("--subject", default=None, help="Subject key (singleton default: the fixed key).")
@click.option("--actor", default="operator", show_default=True,
              help="The actor being gated (cross-authority is computed against this).")
def process_can_move(address: str, to_state: str, subject: str | None, actor: str) -> None:
    """Validate a candidate move; refuse (fail-closed) with a self-explaining reason."""
    from project_kit import process as process_mod

    engine = _load_engine(address, subject)
    try:
        allowed, reason, _position = engine.can_move(to_state, actor)
    except process_mod.ProcessError as exc:
        raise click.ClickException(str(exc)) from exc
    marker = "✓" if allowed else "✗"
    click.echo(f"  {marker} {reason}")
    if not allowed:
        raise SystemExit(1)


@process.command("move")
@click.argument("address")
@click.option("--to", "to_state", required=True, help="Target state id.")
@click.option("--subject", default=None, help="Subject key (singleton default: the fixed key).")
@click.option("--actor", default="operator", show_default=True,
              help="The actor performing the move (recorded in the journal; gated "
                   "cross-authority).")
def process_move(address: str, to_state: str, subject: str | None, actor: str) -> None:
    """Execute a legal move; append the journal entry. Refuses an illegal move."""
    from project_kit import process as process_mod

    engine = _load_engine(address, subject)
    try:
        result = engine.move(to_state, actor)
    except process_mod.ProcessError as exc:
        raise click.ClickException(str(exc)) from exc
    if not result.ok:
        click.echo("  " + cli_render.style("strong", f"refused: {result.reason}"))
        raise SystemExit(1)
    click.echo("  " + cli_render.style("strong", f"moved to {to_state!r}: {result.reason}"))


if __name__ == "__main__":
    main()
