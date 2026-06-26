"""Install helpers for `pkit init` and `pkit sync`.

The Python port of `cmd_init` from `.pkit/cli/pkit`. Behaviour preserved
exactly: same target-root resolution, same area iteration order, same
adapter-side mechanics, same .claude/settings.json backup-then-merge
flow. `--dry-run` support per COR-004.
"""

from __future__ import annotations

import atexit
import shutil
import stat
import subprocess
from contextlib import ExitStack
from dataclasses import dataclass
from importlib.resources import as_file, files
from pathlib import Path

import click

from project_kit import treecopy

# Settings-file template seeded into adopter projects when no
# project-side overrides exist. Matches the bash dispatcher's heredoc.
EMPTY_PROJECT_SETTINGS_JSON = """\
{
  "permissions": {
    "allow": [],
    "deny": []
  }
}
"""


# Seeded into `.pkit/agents/project/overlay.yaml` on first install (or
# when sync catches up an adopter installed before the agents area
# landed). Safe defaults so deploy-agents.sh succeeds out of the box;
# adopters tailor the paths to their actual layout.
_AGENTS_OVERLAY_SEED = """\
# Adopter overlay for kit-shipped agents (per COR-013).
#
# Each top-level key is a *category* — a named bucket of adopter-specific
# paths. Kit-shipped agents reference these categories via `<name>`
# placeholders in their frontmatter and body. The deploy-agents primitive
# resolves each placeholder with the values listed here at deploy time.
#
# Customise this file for your project's actual file paths. The defaults
# below assume a generic repo layout — change them to the docs your team
# actually uses.

workflow-docs:
  - README.md

project-root-docs:
  - README.md

# Architecture documentation roots (per COR-024). The architect agent
# reads these; populate with the docs your team treats as architectural.
# Conventional default points at docs/architecture/ when that tree exists.
architecture-docs:
  - README.md

# ADR records location (per COR-024 + COR-025). The architect agent owns
# this directory; `pkit new decision adr <slug>` stamps records here. The
# directory is not created on install — author your first ADR via the
# command, which prompts you to create the directory first.
adr-records:
  - docs/architecture/decisions/

# Per-agent overrides (optional): replace categories for a specific agent.
# overrides:
#   product-manager:
#     workflow-docs:
#       - docs/roadmap.md
"""


# Kit-shipped areas propagated into adopters on `pkit init` and refreshed
# on `pkit sync` (per COR-001). One source of truth — add a new area
# here and both `pkit init` and `pkit sync` pick it up. Order is the
# iteration order at install/sync time.
PROPAGATED_AREAS: tuple[str, ...] = (
    "decisions",
    "skills",
    "cli",
    "adapters",
    "scratchpad",
    "agents",
    "schemas",
    "permissions",
    "rules",
    "process",
    # Backbone migrations must reach the adopter tree: `pkit upgrade` reads
    # `<target>/.pkit/migrations/backbone/` *after* sync to run pending
    # backbone migrations (ADR-033 §4 — fixes a pre-existing omission where
    # migrations were read from the source kit but never propagated). Sync
    # runs before the migration steps in `run_upgrade`, so listing the area
    # here is sufficient for ordering. `capabilities` is deliberately NOT
    # here: capability source is bundled (a distribution medium) but installed
    # on demand, not auto-propagated to every adopter (ADR-033 §3).
    "migrations",
)


@dataclass(frozen=True)
class InstallContext:
    """Resolved roots for an install run."""

    target_root: Path
    source_kit: Path
    dry_run: bool


def find_target_root(start: Path | None = None) -> Path | None:
    """Resolve the project root by `git rev-parse --show-toplevel` first,
    then by walking up looking for `.git/` or `.pkit/`. Mirrors the bash
    dispatcher's `find_target_root` helper.
    """
    cwd = start if start is not None else Path.cwd()
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            cwd=cwd,
            check=False,
        )
        if result.returncode == 0:
            return Path(result.stdout.strip())
    except FileNotFoundError:
        pass

    cur = cwd.resolve()
    while cur != cur.parent:
        # `.git` may be a directory (normal repo) or a file (worktree marker
        # pointing at the main repo's worktrees dir). Either form counts.
        if (cur / ".git").exists() or (cur / ".pkit").is_dir():
            return cur
        cur = cur.parent
    return None


# A real source checkout's `.pkit/` is distinguished from anything else by the
# presence of its `decisions/` subtree — the same discriminator
# `_refuse_if_source_kit_missing` applies. A bare-existence check is not enough:
# the bundled `_kit/` also exists, but checkout-first resolution (ADR-033 §2)
# must return the *checkout* when one is present.
def _looks_like_source_checkout(candidate: Path) -> bool:
    return (candidate / "decisions").is_dir()


# Process-lifetime materialisation of the bundled `_kit/` tree, used only when
# the package is imported from a zipped/zipimport wheel (where `files()` yields
# a path inside the zip that has no on-disk form). `as_file()` extracts it to a
# temp dir whose lifetime is bounded by the `with` block; returning a path from
# inside a closed block would hand callers a deleted directory. We hold the
# context open for the whole process via a module-level `ExitStack` flushed at
# interpreter exit, and cache the materialised path so we extract at most once.
# The common `uv tool` install is unzipped — real files in site-packages — so
# this path is never taken there (see `_bundled_source_kit`).
_BUNDLE_EXITSTACK = ExitStack()
atexit.register(_BUNDLE_EXITSTACK.close)
_materialised_bundle: Path | None = None


def _bundled_source_kit() -> Path:
    """Return the bundled methodology tree at `project_kit/_kit/` (ADR-033).

    For an unzipped install (the `uv tool` case — real files in site-packages),
    `files()` yields a directory that already exists on disk; return it
    directly. For a zipped wheel, materialise the tree once to a
    process-lifetime temp dir and return that. Either way the returned path is
    valid for the rest of the process — never a path from inside a closed
    `as_file()` context.
    """
    global _materialised_bundle

    resource = files("project_kit").joinpath("_kit")
    on_disk = Path(str(resource))
    if on_disk.is_dir():
        return on_disk

    if _materialised_bundle is None:
        _materialised_bundle = _BUNDLE_EXITSTACK.enter_context(as_file(resource))
    return _materialised_bundle


def find_source_kit() -> Path:
    """Return the methodology source kit's `.pkit/`-equivalent directory.

    Checkout-first (ADR-033 §2): when invoked from a real project-kit checkout
    (`__file__` at `<repo>/src/project_kit/install.py`, so `.pkit/` is two
    parents up), and that directory looks like a real source tree, return it —
    preserving dev live-edit and self-host. Otherwise (the official `uv tool`
    install, where no checkout `.pkit/` exists) fall back to the bundled
    `project_kit/_kit/` shipped in the wheel.
    """
    checkout = Path(__file__).resolve().parents[2] / ".pkit"
    if _looks_like_source_checkout(checkout):
        return checkout
    return _bundled_source_kit()


def install_kit(target_root: Path, dry_run: bool = False) -> None:
    """Run `pkit init` against `target_root`. Refuses to run if `.pkit/`
    already exists, if the source kit doesn't look like a real source
    tree, or if the target is the source itself (project-kit
    self-hosts).
    """
    source_kit = find_source_kit()
    ctx = InstallContext(target_root=target_root, source_kit=source_kit, dry_run=dry_run)

    _refuse_if_already_initialised(ctx)
    _refuse_if_source_kit_missing(ctx)
    _refuse_if_target_is_source(ctx)

    click.echo(f"Installing project-kit into {target_root}")
    click.echo(f"  source: {source_kit}")
    if dry_run:
        click.echo("  (dry-run — no changes will be written)")
    click.echo()

    _mkdir(target_root / ".pkit", ctx)
    for area in PROPAGATED_AREAS:
        src = source_kit / area
        if src.is_dir():
            _install_area(src, target_root / ".pkit" / area, ctx)

    _backup_existing_claude_settings(ctx)
    run_installed_adapter_primitives(ctx)

    _stamp_backbone_manifest(ctx)
    _render_runtime_ignore(ctx)
    _print_next_steps(ctx)


def _render_runtime_ignore(ctx: InstallContext) -> None:
    """Wholesale-regenerate `.pkit/.gitignore` at the CORE tier (ADR-009
    Amendment 1, T2).

    Runs *after* the manifest is stamped so the component walk sees every
    registered adapter/capability. Deliberately a core step — NOT an adapter
    primitive — so backbone + capability `runtime_ignore:` declarations render
    even when no adapter is installed (the layering inversion ADR-009 forbids).
    Local import to keep `visibility`'s heavier deps off the install hot path
    and avoid an import-time cycle.
    """
    from project_kit import visibility

    click.echo(visibility.render_runtime_ignore(ctx.target_root, dry_run=ctx.dry_run))


def _stamp_backbone_manifest(ctx: InstallContext) -> None:
    """Write the initial `.pkit/manifest.yaml` with the source kit's backbone version.

    Auto-registers every installed adapter (adapters ship with the kit
    and get installed during init, so each lands in the components
    registry from the start — per COR-010's principle that install adds
    a registry entry).

    Local import to avoid an import-time cycle: `project_kit.sync`
    imports `project_kit.install`, and `project_kit.manifest` is
    intentionally lighter than both — it's fine to import here at call
    time.
    """
    if ctx.dry_run:
        click.echo("  would stamp  .pkit/manifest.yaml (backbone manifest + adapter registry)")
        return

    from project_kit.manifest import (
        BackboneManifest,
        ComponentRegistryEntry,
        read_kit_version,
        write_backbone_manifest,
    )

    backbone_version = read_kit_version(ctx.source_kit)
    components: list[ComponentRegistryEntry] = []

    adapters_dir = ctx.target_root / ".pkit" / "adapters"
    if adapters_dir.is_dir():
        for adapter_dir in sorted(p for p in adapters_dir.iterdir() if p.is_dir()):
            components.append(
                ComponentRegistryEntry(
                    kind="adapter",
                    name=adapter_dir.name,
                    manifest=f".pkit/adapters/{adapter_dir.name}/project/manifest.yaml",
                )
            )

    write_backbone_manifest(
        ctx.target_root,
        BackboneManifest(backbone_version=backbone_version, components=components),
    )
    suffix = f"; {len(components)} adapter(s) registered" if components else ""
    click.echo(f"  {'stamped':<12} .pkit/manifest.yaml (backbone v{backbone_version}{suffix})")


def _refuse_if_already_initialised(ctx: InstallContext) -> None:
    if (ctx.target_root / ".pkit").is_dir():
        raise click.ClickException(
            f"{ctx.target_root}/.pkit/ already exists.\n"
            f"       pkit init refuses to re-run on a project that already has the kit\n"
            f"       installed. Remove .pkit/ first to reinstall, or use future refresh\n"
            f"       commands when those land."
        )


def refuse_if_source_kit_incomplete(source_kit: Path) -> None:
    """Raise a clean `ClickException` if `source_kit` is not a usable kit tree.

    The discriminator (`decisions/` present) is the same one
    `find_source_kit` uses to recognise a checkout and `_refuse_if_source_kit_missing`
    uses to gate init. Sync and upgrade call this at entry — *before*
    `read_kit_version` / propagation — so a future incomplete bundle (or any
    resolution that points somewhere without the methodology content) surfaces
    as a clear operator-facing error rather than a raw `FileNotFoundError`
    deep inside propagation (ADR-033; issue #333).
    """
    if not _looks_like_source_checkout(source_kit):
        raise click.ClickException(
            f"methodology source not found at {source_kit} (no decisions/ subdirectory).\n"
            f"       The pkit binary could not resolve its bundled content. Reinstall "
            f"project-kit, or run from a project-kit checkout."
        )


def _refuse_if_source_kit_missing(ctx: InstallContext) -> None:
    refuse_if_source_kit_incomplete(ctx.source_kit)


def _refuse_if_target_is_source(ctx: InstallContext) -> None:
    source_repo = ctx.source_kit.parent.resolve()
    if ctx.target_root.resolve() == source_repo:
        raise click.ClickException(
            f"source and target are the same project ({ctx.target_root}).\n"
            f"       project-kit self-hosts directly; running pkit init on project-kit\n"
            f"       itself is a no-op."
        )


def _install_area(src: Path, dst: Path, ctx: InstallContext, *, overwrite: bool = False) -> None:
    """Copy a single area's kit-shipped content into the adopter tree.

    `overwrite=False` (init): refuses to copy over existing trees, so
    re-running init is the structural error COR-004 specifies.
    `overwrite=True` (sync): refreshes kit-owned content in place,
    leaving project-owned content untouched.
    """
    area_name = src.name
    _mkdir(dst, ctx)

    readme = src / "README.md"
    if readme.is_file():
        _copy_file(readme, dst / "README.md", ctx)

    verb = "refreshed" if overwrite else "installed"

    for sub in ("core", "_defs"):
        sub_src = src / sub
        if sub_src.is_dir():
            _copy_tree(sub_src, dst / sub, ctx, overwrite=overwrite)
            click.echo(f"  {verb:<12} .pkit/{area_name}/{sub}/")

    if area_name == "cli":
        pkit_src = src / "pkit"
        if pkit_src.is_file():
            _copy_file(pkit_src, dst / "pkit", ctx, executable=True)
            click.echo(f"  {verb:<12} .pkit/cli/pkit")

    if area_name == "adapters":
        for adapter_src in sorted(p for p in src.iterdir() if p.is_dir()):
            _install_adapter(adapter_src, dst / adapter_src.name, ctx, overwrite=overwrite)

    # Propagate any remaining kit-owned content the area keeps as flat
    # top-level files or non-standard subdirs. Most areas follow the
    # COR-011 layout (content under `core/`, already copied above), but
    # some are not COR-011 areas: `permissions/` ships flat code
    # (`decide.py`, `projection.py`) + a `profiles/` dir, and `schemas/`
    # ships flat `*.yaml` / `*.schema.json`. Without this pass those never
    # reach adopters — breaking the whole permission subsystem (the
    # decision core + catalog the CLI imports). Skip what is already
    # handled (README, core/_defs), adopter-owned (`project/`, scratchpad
    # state), specially handled (adapter subdirs, `cli/pkit`), or a build
    # cache (`__pycache__`).
    _handled = {"README.md", "core", "_defs", "project", "__pycache__"}
    if area_name == "adapters":
        _handled |= {p.name for p in src.iterdir() if p.is_dir()}
    elif area_name == "cli":
        _handled.add("pkit")
    elif area_name == "scratchpad":
        _handled |= {"active", "done", "dropped"}
    elif area_name == "rules":
        # project.md is adopter-owned (per the rules area README): the adopter
        # authors their project-specific rules there; kit sync must never
        # overwrite it. Exclude it from the flat-content pass so sync only
        # propagates core.md. On init (overwrite=False), project.md is
        # absent in fresh adopters so the file-presence guard below handles it.
        _handled.add("project.md")
    for entry in sorted(src.iterdir()):
        if entry.name in _handled:
            continue
        target = dst / entry.name
        if entry.is_dir():
            _copy_tree(entry, target, ctx, overwrite=overwrite)
            click.echo(f"  {verb:<12} .pkit/{area_name}/{entry.name}/")
        elif entry.is_file():
            _copy_file(entry, target, ctx)
            click.echo(f"  {verb:<12} .pkit/{area_name}/{entry.name}")

    # Scratchpad state folders are adopter-owned (per COR-012). Sync must
    # never touch them; init stubs them so the layout exists for the
    # adopter's first note. Folder *contents* in the source kit (e.g.
    # project-kit's own inventory note in done/) are not propagated.
    if area_name == "scratchpad" and not overwrite:
        for state_dir in ("active", "done", "dropped"):
            state_dst = dst / state_dir
            _mkdir(state_dst, ctx)
            _touch(state_dst / ".gitkeep", ctx)
        click.echo(f"  {'stubbed':<12} .pkit/scratchpad/{{active,done,dropped}}/")

    # Sync must NEVER overwrite project/ content. But it MAY stub the
    # project/ directory if it doesn't yet exist on the adopter side —
    # this catches up adopters who installed before an area landed,
    # so they get the project/ scaffolding without an extra step.
    # Anything already in project/ is left untouched.
    if (src / "project").is_dir():
        project_dst = dst / "project"
        if not project_dst.is_dir():
            _mkdir(project_dst, ctx)
            _touch(project_dst / ".gitkeep", ctx)
            click.echo(f"  {'stubbed':<12} .pkit/{area_name}/project/")

    # Agents area: seed a starter overlay.yaml if the adopter doesn't
    # have one yet. The seed declares the categories kit-shipped agents
    # reference (`<workflow-docs>`, `<project-root-docs>`) with safe
    # defaults so deploy-agents.sh succeeds out of the box; adopters
    # tailor the paths to their actual layout. Never overwrites an
    # existing overlay.
    if area_name == "agents":
        overlay = dst / "project" / "overlay.yaml"
        if not overlay.exists():
            _write_text(overlay, _AGENTS_OVERLAY_SEED, ctx)
            click.echo(f"  {'seeded':<12} .pkit/agents/project/overlay.yaml")


def _install_adapter(src: Path, dst: Path, ctx: InstallContext, *, overwrite: bool = False) -> None:
    adapter_name = src.name
    _mkdir(dst, ctx)

    readme = src / "README.md"
    if readme.is_file():
        _copy_file(readme, dst / "README.md", ctx)

    # Adapter metadata file (per COR-010): kit-owned, propagated to
    # adopter so `pkit upgrade`'s compatibility check has access to the
    # adapter's recorded `requires_backbone` range.
    package_yaml = src / "package.yaml"
    if package_yaml.is_file():
        _copy_file(package_yaml, dst / "package.yaml", ctx)

    # Propagate orchestrator scripts (*.sh) and sibling helpers (*.py).
    # The bash orchestrator may call Python helpers self-contained via
    # PEP 723 inline metadata (see deploy-agents.sh + _resolve_agent.py).
    # Both are executable from the adopter side; preserve the executable
    # bit so the shebang works directly.
    src_scripts = sorted([*src.glob("*.sh"), *src.glob("*.py")])
    for script in src_scripts:
        _copy_file(script, dst / script.name, ctx, executable=True)

    # Sync mode: drop any *.sh / *.py in dst whose source counterpart no
    # longer exists. Init never runs into orphans (fresh tree), so gate
    # on overwrite to keep init's behaviour unchanged.
    if overwrite and dst.is_dir():
        kept = {p.name for p in src_scripts}
        for orphan in sorted([*dst.glob("*.sh"), *dst.glob("*.py")]):
            if orphan.name not in kept:
                _remove_file(orphan, ctx, label=f".pkit/adapters/{adapter_name}/{orphan.name}")

    settings_src = src / "settings"
    if settings_src.is_dir():
        settings_dst = dst / "settings"
        _mkdir(settings_dst, ctx)
        core_src = settings_src / "core"
        if core_src.is_dir():
            _copy_tree(core_src, settings_dst / "core", ctx, overwrite=overwrite)
        project_src = settings_src / "project"
        if project_src.is_dir():
            project_dst = settings_dst / "project"
            _mkdir(project_dst, ctx)
            seed_target = project_dst / "settings.json"
            # Sync must NEVER overwrite an existing project/settings.json
            # — that's adopter content. Init seeds it only when absent.
            if not seed_target.exists() and not overwrite:
                _write_text(seed_target, EMPTY_PROJECT_SETTINGS_JSON, ctx)

    verb = "refreshed" if overwrite else "installed"
    click.echo(f"  {verb:<12} .pkit/adapters/{adapter_name}/")


def _backup_existing_claude_settings(ctx: InstallContext) -> None:
    settings = ctx.target_root / ".claude" / "settings.json"
    if settings.is_file():
        backup = settings.with_suffix(".json.pre-pkit")
        _copy_file(settings, backup, ctx)
        click.echo(f"  {'backed-up':<12} .claude/settings.json -> .claude/settings.json.pre-pkit")


def _run_adapter_primitive(script: Path, ctx: InstallContext) -> None:
    if ctx.dry_run:
        click.echo(f"  {'would run':<12} {script.relative_to(ctx.target_root)}")
        return
    if not script.is_file():
        return
    # Run without raising on non-zero. The primitive prints its own
    # status lines (created/exists/error/...) which already explain any
    # partial failure. We surface the failure cleanly via a
    # ClickException so the operator sees `Error: ...` instead of a
    # Python traceback, but the script's own output stays intact.
    result = subprocess.run([str(script)], cwd=ctx.target_root)
    if result.returncode != 0:
        rel = script.relative_to(ctx.target_root)
        raise click.ClickException(
            f"adapter primitive {rel} exited with status "
            f"{result.returncode}. See the output above for details."
        )


# Names of adapter primitive scripts that init and sync invoke in order.
# Each is optional: a primitive missing from a given adapter is silently
# skipped (per `_run_adapter_primitive`'s file-presence guard). Ordering
# matters: settings merge precedes content deploys because some skills
# may rely on settings being in place. Adding a new primitive: extend
# this list and document the new script's contract in the adapter README.
_ADAPTER_PRIMITIVES = ("merge-settings.sh", "merge-claude-md.sh", "deploy-skills.sh", "deploy-agents.sh")


def run_installed_adapter_primitives(ctx: InstallContext) -> None:
    """Invoke each installed adapter's primitive scripts in turn.

    Called by `install_kit` after the first-time copy and by
    `pkit sync` after the refresh pass — both need the harness side
    (re-)materialised. Adapters are discovered by walking
    `.pkit/adapters/<name>/`; the scripts must be idempotent so re-runs
    on a stable state report "exists" rather than "created".
    """
    adapters_root = ctx.target_root / ".pkit" / "adapters"
    if not adapters_root.is_dir():
        return
    for adapter_dir in sorted(p for p in adapters_root.iterdir() if p.is_dir()):
        for name in _ADAPTER_PRIMITIVES:
            _run_adapter_primitive(adapter_dir / name, ctx)


def _print_next_steps(ctx: InstallContext) -> None:
    source_kit = ctx.source_kit
    click.echo()
    click.echo("Install complete. Recommended next steps:")
    click.echo()
    click.echo("  1. (One-time per machine, skip if already done) Make pkit available on")
    click.echo("     PATH. ONE symlink works for any number of project-kit-adopting")
    click.echo("     projects on this machine — the dispatcher resolves the current")
    click.echo("     project's root from CWD at invocation time:")
    click.echo()
    click.echo(f"       ln -s {source_kit}/cli/pkit ~/.local/bin/pkit")
    click.echo()
    click.echo("     Symlink the SOURCE pkit (the one you just invoked), not this")
    click.echo("     project's just-installed copy. This project's .pkit/cli/pkit is a")
    click.echo("     fallback for machines that don't have project-kit cloned.")
    click.echo()
    click.echo("  2. Fill in adopter-side configs as needed:")
    click.echo("       .pkit/capabilities/<name>/project/config.yaml        (per installed capability)")
    click.echo("       .pkit/adapters/claude-code/settings/project/settings.json")
    click.echo(
        "                                                          (project-specific allows)"
    )
    click.echo()
    click.echo("  3. Review .claude/settings.json — kit baseline merged with prior content.")
    click.echo("     Backup at .claude/settings.json.pre-pkit if you need to compare or revert.")
    click.echo()
    click.echo("  4. Add to your .gitignore (if not already):")
    click.echo("       .claude/settings.local.json")
    click.echo("       .claude/worktrees/")
    click.echo("       !.claude/skills/")
    click.echo()
    click.echo("  5. To keep pkit private — invisible to a shared repo whose team")
    click.echo("     hasn't adopted it — run `pkit visibility private` (per ADR-009).")


# --- Filesystem primitives (each respects ctx.dry_run) -------------------


def _mkdir(path: Path, ctx: InstallContext) -> None:
    if ctx.dry_run:
        return
    path.mkdir(parents=True, exist_ok=True)


def _copy_file(src: Path, dst: Path, ctx: InstallContext, *, executable: bool = False) -> None:
    if ctx.dry_run:
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    if executable:
        mode = dst.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
        dst.chmod(mode)


def _copy_tree(src: Path, dst: Path, ctx: InstallContext, *, overwrite: bool = False) -> None:
    if ctx.dry_run:
        return
    if overwrite:
        # Sync mode: refresh in place through the ownership-aware primitive
        # so renamed/removed source files don't linger as orphans, without a
        # bulk `rmtree` first. The callers only point us at purely kit-owned
        # trees (`core/`, adapter `settings/core/`) — nothing here is
        # adopter-owned, so `nothing_owned` makes this a plain overwrite +
        # orphan-prune (equivalent to the prior rmtree + copytree, but never
        # destroying before copying). One copy mechanic, shared with the
        # capability refresh (per COR-001 / the tree-refresh ADR).
        treecopy.refresh_owned_tree(src, dst, is_owned=treecopy.nothing_owned)
        return
    # Init mode: fresh copy. copytree raises FileExistsError if dst already
    # exists — that raise is load-bearing (re-running init is the structural
    # error COR-004 specifies), so it is preserved untouched.
    shutil.copytree(src, dst)


def _write_text(path: Path, content: str, ctx: InstallContext) -> None:
    if ctx.dry_run:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _touch(path: Path, ctx: InstallContext) -> None:
    if ctx.dry_run:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch(exist_ok=True)


def _remove_file(path: Path, ctx: InstallContext, *, label: str | None = None) -> None:
    if ctx.dry_run:
        click.echo(f"  {'would remove':<12} {label or path}")
        return
    path.unlink()
    click.echo(f"  {'removed':<12} {label or path}")
