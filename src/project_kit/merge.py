"""`pkit merge` — re-run merge delivery per COR-002.

Walks every installed adapter's merge primitive and invokes it. The
adapter primitives stay shell scripts (per the cutover plan in PR-H);
this module's job is orchestration and dry-run reporting.

COR-004's surface specifies `merge [<target>...]` — re-run merge for one
or all targets. Today the only merge primitive shipped is the
`claude-code` adapter's `merge-settings.sh`, but the framework supports
more (future adapters / future fixed-path config files). The optional
positional args filter to specific targets when there are several.

`merge` stays separate from `sync` per COR-004's "sync and merge stay
separate" — they encode different consent profiles (sync silently
overwrites core-owned paths; merge prompts and appends on project-owned
paths). Calling them together is the adopter's choice, not the runtime's.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import click


def run_merge(
    target_root: Path,
    targets: tuple[str, ...] = (),
    dry_run: bool = False,
) -> None:
    """Invoke every installed adapter's merge primitive (or only those named in `targets`).

    `targets` are interpreted as adapter names (e.g., `claude-code`).
    Empty tuple = all adapters with a merge primitive.
    """
    if not (target_root / ".pkit").is_dir():
        raise click.ClickException(f"{target_root}/.pkit/ does not exist. Run 'pkit init' first.")

    adapters_dir = target_root / ".pkit" / "adapters"
    if not adapters_dir.is_dir():
        click.echo("No adapters installed.")
        return

    selected = _select_adapters(adapters_dir, targets)
    if not selected:
        if targets:
            raise click.ClickException(
                f"no installed adapter matches the requested target(s): {', '.join(targets)}"
            )
        click.echo("No installed adapter ships a merge primitive.")
        return

    click.echo(f"Running merge against {target_root}")
    if dry_run:
        click.echo("  (dry-run — no changes will be written)")
    click.echo()

    for _adapter_dir, primitive in selected:
        rel = primitive.relative_to(target_root)
        if dry_run:
            click.echo(f"  would run    {rel}")
            continue
        click.echo(f"  running      {rel}")
        subprocess.run([str(primitive)], check=True, cwd=target_root)

    click.echo()
    click.echo("Merge complete.")


def _select_adapters(adapters_dir: Path, targets: tuple[str, ...]) -> list[tuple[Path, Path]]:
    """Return [(adapter_dir, merge_primitive_path), ...] for adapters that match.

    An adapter "ships a merge primitive" when its directory contains
    `merge-settings.sh`. Future adapters that have multiple primitives
    (e.g., `merge-config.sh`) extend this list — for now `merge-settings.sh`
    is the convention.
    """
    selection: list[tuple[Path, Path]] = []
    for adapter_dir in sorted(p for p in adapters_dir.iterdir() if p.is_dir()):
        if targets and adapter_dir.name not in targets:
            continue
        primitive = adapter_dir / "merge-settings.sh"
        if primitive.is_file():
            selection.append((adapter_dir, primitive))
    return selection
