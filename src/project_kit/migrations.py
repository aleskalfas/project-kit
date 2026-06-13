"""Migration runtime + authoring-time coverage check (per COR-010).

Two responsibilities:

1. **Runtime execution** — a migration is a per-minor-version script
   that bridges adopter state from one version to the next. The runner
   contract is the same across backbone, adapter, and capability tiers:

   - Scripts live under `<root>/<X.Y.0>/<NNN>-<slug>.sh`.
   - Execution walks version directories whose minor falls strictly
     above the installed minor and at-or-below the target minor.
   - Each script runs via `bash` with `ROOT=<target_root>` in the
     environment and `cwd` set to `target_root`.
   - A non-zero exit halts the run.

2. **Authoring-time coverage check** — `check_diff_coverage` walks a
   git diff for changes that require migrations (per COR-010's
   "Migrations are mandatory on adopter-breaking surface changes"
   rule) and verifies the same diff includes a matching migration
   script. CI gates the merge; the agent uses it pre-commit.
"""

from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import click

from project_kit import cli_render


_VERSION_DIR_RE = re.compile(r"^\d+\.\d+\.0$")

# A path under one of these prefixes is considered kit-owned (changes
# propagate to adopters via sync or upgrade). Paths under prefix's
# component-owned subdir (project/, namespace=project, etc.) are excluded.
Tier = Literal["backbone", "adapter", "capability"]


def parse_version_tuple(value: str) -> tuple[int, int, int]:
    """Parse `X.Y.Z` into a comparable int tuple. Raises on malformed input."""
    parts = value.split(".")
    if len(parts) < 3:
        raise click.ClickException(f"version {value!r} is not in major.minor.patch form.")
    try:
        return int(parts[0]), int(parts[1]), int(parts[2])
    except ValueError as exc:
        raise click.ClickException(
            f"version {value!r} has non-integer components."
        ) from exc


def pending_migration_scripts(
    migrations_root: Path,
    installed_version: str | None,
    target_version: str,
) -> list[Path]:
    """Collect migration scripts whose minor falls in (installed, target].

    `migrations_root` is the directory containing `<X.Y.0>/<NNN>-*.sh`
    subdirectories. Missing or non-versioned subdirectories are ignored.

    `installed_version=None` means "no prior install recorded" — treat
    every shipped migration as pending (the conservative default; the
    runner may still refuse to apply if the missing record is
    suspicious).

    Returns scripts in execution order: version-dir ascending semver,
    then `NNN-*.sh` filename within each version-dir.
    """
    if not migrations_root.is_dir():
        return []

    target_minor = parse_version_tuple(target_version)[:2]
    if installed_version is None:
        installed_minor: tuple[int, int] = (-1, -1)
    else:
        installed_minor = parse_version_tuple(installed_version)[:2]

    scripts: list[Path] = []
    version_dirs = sorted(
        (p for p in migrations_root.iterdir() if p.is_dir() and _VERSION_DIR_RE.match(p.name)),
        key=lambda p: parse_version_tuple(p.name),
    )
    for version_dir in version_dirs:
        ver_minor = parse_version_tuple(version_dir.name)[:2]
        # Window: installed < version ≤ target. A minor below the
        # installed version is already applied; a minor above the target
        # version isn't shipping yet.
        if not (installed_minor < ver_minor <= target_minor):
            continue
        for script in sorted(version_dir.glob("[0-9]*.sh")):
            scripts.append(script)
    return scripts


def execute_migration_scripts(
    scripts: list[Path],
    target_root: Path,
    label: str,
    *,
    label_rel_to: Path | None = None,
) -> None:
    """Run scripts in order via bash with ROOT env var. Halts on non-zero exit.

    `label` names the migration set in user-facing messages (e.g.
    `"backbone"`, `"capability 'evidence'"`, `"adapter 'claude-code'"`).
    `label_rel_to` is a base path used to render script paths in the
    output relatively — typically the component's root directory.
    Defaults to each script's parent's parent (the migrations root).
    """
    if not scripts:
        return

    env = dict(os.environ)
    env["ROOT"] = str(target_root)

    for script in scripts:
        rel: Path | str
        if label_rel_to is not None:
            try:
                rel = script.relative_to(label_rel_to)
            except ValueError:
                rel = script
        else:
            rel = script.name
        click.echo(f"    • {rel}")
        result = subprocess.run(
            ["bash", str(script)],
            env=env,
            cwd=target_root,
        )
        if result.returncode != 0:
            raise click.ClickException(
                f"{label} migration {rel} exited with status {result.returncode}. "
                f"Run halted — state may be inconsistent. Resolve the migration's "
                f"failure mode (likely an unmet precondition or non-idempotent script) "
                f"and re-run."
            )


def report_pending_migrations(
    scripts: list[Path],
    label: str,
    installed_version: str | None,
    target_version: str,
    *,
    dry_run: bool,
    label_rel_to: Path | None = None,
) -> None:
    """Print what migrations would run, without executing."""
    if not scripts:
        return
    verb = "would run" if dry_run else "running"
    click.echo(
        f"  {verb} {len(scripts)} migration(s) for {label} "
        f"({installed_version or 'unknown'} -> v{target_version})"
    )
    for script in scripts:
        rel: Path | str
        if label_rel_to is not None:
            try:
                rel = script.relative_to(label_rel_to)
            except ValueError:
                rel = script
        else:
            rel = script.name
        click.echo(f"    • {rel}")


# --- authoring-time coverage check (per COR-010 + rules/core.md #7) ----


@dataclass(frozen=True)
class DiffTrigger:
    """A change in the diff that requires a migration."""

    kind: Literal["rename", "delete"]
    path: str  # destination path (for renames) or removed path (for deletes)
    old_path: str | None  # source path for renames; None for deletes
    tier: Tier
    component: str | None  # adapter/capability name; None for backbone


@dataclass(frozen=True)
class DiffMigration:
    """A migration script newly added in the diff."""

    path: str
    tier: Tier
    component: str | None


@dataclass(frozen=True)
class CoverageReport:
    """Result of a `check_diff_coverage` run."""

    triggers: tuple[DiffTrigger, ...]
    migrations: tuple[DiffMigration, ...]

    @property
    def is_covered(self) -> bool:
        """Covered iff every (tier, component) with triggers has a matching migration."""
        if not self.triggers:
            return True
        trigger_keys = {(t.tier, t.component) for t in self.triggers}
        migration_keys = {(m.tier, m.component) for m in self.migrations}
        return trigger_keys.issubset(migration_keys)

    @property
    def uncovered_keys(self) -> list[tuple[Tier, str | None]]:
        """List of (tier, component) keys with triggers but no matching migration."""
        trigger_keys = {(t.tier, t.component) for t in self.triggers}
        migration_keys = {(m.tier, m.component) for m in self.migrations}
        return sorted(trigger_keys - migration_keys)


def check_diff_coverage(
    target_root: Path,
    base_ref: str,
    *,
    include_working_tree: bool = False,
) -> CoverageReport:
    """Walk the diff between `base_ref` and the project state; identify triggers + new migrations.

    By default the diff is `<base_ref>...HEAD` — committed branch changes
    only (what CI sees on a PR). With `include_working_tree=True`, the
    diff is `<base_ref>` against the working tree — captures committed
    + staged + unstaged changes (what's about to be committed). The
    pre-commit form for local use.

    Returns a CoverageReport. Callers (CLI / CI gate) check
    `report.is_covered` and surface `report.uncovered_keys` to the
    author when False.
    """
    entries = _git_diff_name_status(
        target_root, base_ref, include_working_tree=include_working_tree
    )
    triggers: list[DiffTrigger] = []
    migrations: list[DiffMigration] = []
    for status, path, old_path in entries:
        if status == "A" and _is_migration_path(path):
            migrations.append(
                DiffMigration(
                    path=path,
                    tier=_migration_path_tier(path),
                    component=_migration_path_component(path),
                )
            )
            continue
        if _is_migration_path(path):
            # Renames / deletes within a migrations dir don't trigger;
            # they're internal bookkeeping.
            continue
        tier_info = _classify_path(path)
        if tier_info is None:
            continue
        if status == "D":
            triggers.append(
                DiffTrigger(
                    kind="delete",
                    path=path,
                    old_path=None,
                    tier=tier_info[0],
                    component=tier_info[1],
                )
            )
        elif status == "R":
            triggers.append(
                DiffTrigger(
                    kind="rename",
                    path=path,
                    old_path=old_path,
                    tier=tier_info[0],
                    component=tier_info[1],
                )
            )
    return CoverageReport(
        triggers=tuple(triggers), migrations=tuple(migrations)
    )


def _git_diff_name_status(
    target_root: Path, base_ref: str, *, include_working_tree: bool = False
) -> list[tuple[str, str, str | None]]:
    """Run `git diff --name-status` against `base_ref`. Returns (status, path, old_path?).

    `include_working_tree=False` (default): committed-only diff
    (`<base>...HEAD`). Matches CI's view of the PR.

    `include_working_tree=True`: base vs working tree (`<base>`).
    Includes committed + staged + unstaged changes. For pre-commit use.
    """
    target = base_ref if include_working_tree else f"{base_ref}...HEAD"
    try:
        result = subprocess.run(
            ["git", "diff", "--name-status", target],
            cwd=str(target_root),
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            f"git diff against {base_ref!r} failed: "
            f"{exc.stderr or exc.stdout}".strip()
        ) from exc
    entries: list[tuple[str, str, str | None]] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        status_code = parts[0]
        kind = status_code[0]
        if kind == "R" and len(parts) >= 3:
            entries.append(("R", parts[2], parts[1]))
        elif kind == "C" and len(parts) >= 3:
            entries.append(("A", parts[2], None))
        elif len(parts) >= 2:
            entries.append((kind, parts[1], None))
    return entries


def _classify_path(path: str) -> tuple[Tier, str | None] | None:
    """Classify a path's tier + component, or None if not kit-owned."""
    # Adopter-owned subtrees: skip.
    if path.startswith(".pkit/decisions/project/"):
        return None
    if path.startswith(".pkit/skills/project/"):
        return None
    if path.startswith(".pkit/agents/project/"):
        return None
    if path.startswith(".pkit/scratchpad/"):
        return None
    if path == ".pkit/rules/project.md":
        return None
    if path.startswith(".pkit/workflow/project/"):
        return None

    # Component subtrees.
    # NB: per COR-027 the bundle pattern is retired; deletion of `.pkit/workflow/`
    # paths falls through to backbone-tier inference below (the workflow area
    # itself is being removed by COR-027).

    if path.startswith(".pkit/adapters/"):
        parts = path.split("/", 4)
        if len(parts) >= 3:
            component = parts[2]
            if len(parts) >= 4 and parts[3] == "project":
                return None
            return ("adapter", component)

    if path.startswith(".pkit/capabilities/"):
        parts = path.split("/", 4)
        if len(parts) >= 3:
            component = parts[2]
            if len(parts) >= 4 and parts[3] == "project":
                return None
            return ("capability", component)

    # Backbone-tier trees.
    backbone_prefixes = (
        ".pkit/decisions/core/",
        ".pkit/skills/core/",
        ".pkit/agents/core/",
        ".pkit/lifecycle/",
        ".pkit/schemas/",
        ".pkit/cli/",
        ".pkit/migrations/",
        ".pkit/workflow/",  # legacy: the workflow area was retired in COR-027;
                            # deletions of leftover content trigger backbone migrations.
    )
    for prefix in backbone_prefixes:
        if path.startswith(prefix):
            return ("backbone", None)
    if path == ".pkit/rules/core.md":
        return ("backbone", None)
    return None


def _is_migration_path(path: str) -> bool:
    """True if path is an actual migration script under any tier's `migrations/` dir.

    Migration scripts are `*.sh` or `*.py` files inside a per-version
    directory like `<X.Y.0>/`. Other content inside migrations/
    (`.gitkeep`, READMEs, etc.) doesn't count — they're scaffolding,
    not migrations.
    """
    if not path.startswith(".pkit/"):
        return False
    is_in_migrations = path.startswith(".pkit/migrations/") or "/migrations/" in path
    if not is_in_migrations:
        return False
    # Restrict to the per-version dir's script files.
    return path.endswith(".sh") or path.endswith(".py")


def _migration_path_tier(path: str) -> Tier:
    """Determine the tier of a migration script."""
    if path.startswith(".pkit/migrations/"):
        return "backbone"
    if path.startswith(".pkit/adapters/"):
        return "adapter"
    if path.startswith(".pkit/capabilities/"):
        return "capability"
    return "backbone"


def _migration_path_component(path: str) -> str | None:
    """Extract the component name from a migration script path; None for backbone."""
    if path.startswith(".pkit/adapters/"):
        parts = path.split("/", 3)
        return parts[2] if len(parts) >= 3 else None
    if path.startswith(".pkit/capabilities/"):
        parts = path.split("/", 3)
        return parts[2] if len(parts) >= 3 else None
    return None


def render_coverage_report(report: CoverageReport) -> None:
    """Render a CoverageReport to stdout in CLI-friendly form."""
    click.echo()
    if not report.triggers:
        click.echo("  No migration-triggering changes in diff.")
        if report.migrations:
            click.echo(
                f"  ({len(report.migrations)} migration script(s) "
                f"in diff, no triggers — that's fine.)"
            )
        click.echo()
        return

    click.echo("  " + cli_render.style("strong", f"{len(report.triggers)} migration trigger(s) in diff:"))
    for t in report.triggers:
        tier_label = t.tier + (":" + t.component if t.component else "")
        if t.kind == "rename":
            click.echo(f"    [{tier_label}] rename: {t.old_path} → {t.path}")
        else:
            click.echo(f"    [{tier_label}] delete: {t.path}")
    click.echo()

    if report.migrations:
        click.echo("  " + cli_render.style("heading", f"{len(report.migrations)} migration script(s) in diff:"))
        for m in report.migrations:
            tier_label = m.tier + (":" + m.component if m.component else "")
            click.echo(f"    [{tier_label}] {m.path}")
        click.echo()

    if report.is_covered:
        click.echo("  " + cli_render.style(
            "strong",
            "Verdict: COVERED (every tier:component with triggers has a matching migration).",
        ))
    else:
        click.echo("  " + cli_render.style(
            "strong",
            "Verdict: UNCOVERED. Author migrations for the following tiers before merging:",
        ))
        for tier, component in report.uncovered_keys:
            tier_label = tier + (":" + component if component else "")
            click.echo(f"    - {tier_label}")
    click.echo()
