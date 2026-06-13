"""Read-only inventory of how project-kit is wired in a project.

Python port of the bash dispatcher's `cmd_status`. The Python CLI is now
authoritative (the bash dispatcher is being retired); status output follows
the #299 output convention + the ADR-011 styling layer, so it intentionally
diverges from the legacy bash version (no status parity test enforces a match
— only `version` and `init` remain in `tests/test_parity.py`). Styling is
never load-bearing: under `--color never` / pipes the structure reads plain.

The bash version reports `$SCRIPT_PATH` (the resolved bash dispatcher
path) on the "Source pkit" line. When this module is invoked through
the shim, the bash dispatcher passes its `$SCRIPT_PATH` as the
`PKIT_SOURCE_BIN` env var. When invoked directly (e.g., after
`uv tool install`), we fall back to the Python module path.
"""

from __future__ import annotations

import os
from pathlib import Path

import click

from project_kit import cli_render
from project_kit.install import find_source_kit, find_target_root
from project_kit.manifest import read_backbone_manifest, read_kit_version


def report_status() -> None:
    """Walk the project tree and print the status report."""
    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not inside a project tree.")

    source_kit = find_source_kit()
    source_pkit = os.environ.get("PKIT_SOURCE_BIN") or str(Path(__file__).resolve())

    click.echo()
    click.echo(cli_render.style("title", "project-kit status — how the methodology is wired in this project"))
    click.echo()
    click.echo(f"  {'Project root:':<22} {target_root}")
    click.echo(f"  {'Source pkit:':<22} {source_pkit}")
    click.echo(f"  {'Source kit:':<22} {source_kit}")

    pkit_dir = target_root / ".pkit"
    if not pkit_dir.is_dir():
        click.echo()
        click.echo("  " + cli_render.style("strong", "project-kit is NOT installed in this project."))
        click.echo("  Run 'pkit init' from this project's root to install.")
        click.echo()
        return

    click.echo(f"  {'Kit installed at:':<22} .pkit/")
    _report_backbone_version(target_root, source_kit)

    _report_claude_adapter(target_root)
    _report_capabilities(target_root, source_kit)
    _report_decisions(target_root)
    _report_skills_inventory(target_root)
    _report_agents_inventory(target_root)
    click.echo()


def _report_backbone_version(target_root: Path, source_kit: Path) -> None:
    """Installed backbone version (from the manifest) vs. what the source ships.

    The at-a-glance "am I current?" line — pairs with `pkit version` (source)
    and points at `pkit upgrade --dry-run` for the full delta when behind.
    """
    manifest = read_backbone_manifest(target_root)
    installed = manifest.backbone_version if manifest else ""
    try:
        source_version = read_kit_version(source_kit)
    except OSError:
        source_version = ""

    if not installed:
        click.echo(f"  {'Backbone version:':<22} unknown (no manifest)")
        return
    if source_version and installed != source_version:
        gloss = f"source {source_version} — run `pkit upgrade --dry-run` to preview"
    else:
        gloss = "up to date"
    click.echo(f"  {'Backbone version:':<22} {installed}   ({gloss})")


def _report_claude_adapter(target_root: Path) -> None:
    click.echo()
    click.echo("  " + cli_render.style("heading", "Adapter: claude-code"))

    settings = target_root / ".claude" / "settings.json"
    pre_pkit = target_root / ".claude" / "settings.json.pre-pkit"
    if settings.is_file():
        if pre_pkit.is_file():
            value = "merged (backup at .claude/settings.json.pre-pkit)"
        else:
            value = "merged"
    else:
        value = "not present (run 'pkit merge-settings')"
    click.echo(f"    {'settings.json':<18} {value}")

    kit_managed: list[tuple[str, str]] = []
    user_managed: list[str] = []
    skills_dir = target_root / ".claude" / "skills"
    if skills_dir.is_dir():
        for entry in sorted(skills_dir.iterdir()):
            link_target = _kit_skill_link_target(entry)
            if link_target is not None:
                kit_managed.append((entry.name, link_target))
            else:
                user_managed.append(entry.name)

    if kit_managed:
        click.echo(f"    {'skills deployed':<18} {len(kit_managed)} kit-managed:")
        for name, target in kit_managed:
            click.echo(f"                         {name} -> {target}")
    else:
        click.echo(f"    {'skills deployed':<18} 0 (run 'pkit deploy-skills')")

    if user_managed:
        click.echo(f"    {'':<18} {len(user_managed)} user-managed (untouched by pkit):")
        for name in user_managed:
            click.echo(f"                         {name}")

    # Agents deploy as resolved copies (not symlinks), so we can't
    # discriminate kit-managed from user-managed by readlink as we do for
    # skills. Use the deploy-time marker the adapter writes into the
    # frontmatter (`# managed-by: project-kit`) — same source-of-truth
    # the deploy primitive uses for its own kit-vs-user content guard.
    kit_agent_names = _source_agent_names(target_root)
    deployed: list[str] = []
    user_agents: list[str] = []
    agents_dir = target_root / ".claude" / "agents"
    if agents_dir.is_dir():
        for entry in sorted(agents_dir.iterdir()):
            if entry.is_file() and entry.suffix == ".md":
                name = entry.stem
                if name in kit_agent_names and _has_kit_marker(entry):
                    deployed.append(name)
                else:
                    user_agents.append(name)

    if deployed:
        click.echo(f"    {'agents deployed':<18} {len(deployed)} kit-managed:")
        for name in deployed:
            click.echo(f"                         {name}")
    elif kit_agent_names:
        click.echo(f"    {'agents deployed':<18} 0 (run 'pkit deploy-agents')")

    if user_agents:
        click.echo(f"    {'':<18} {len(user_agents)} user-managed (untouched by pkit):")
        for name in user_agents:
            click.echo(f"                         {name}")


def _report_capabilities(target_root: Path, source_kit: Path) -> None:
    """Surface installed + available capabilities (per COR-017).

    Imports `capabilities` lazily so a project pre-dating capabilities
    (no `.pkit/capabilities/` and no capability entries in the manifest)
    still gets a clean section, and so the heavier capabilities module
    isn't loaded for every status invocation.
    """
    from project_kit import capabilities as caps

    click.echo()
    click.echo("  " + cli_render.style("heading", "Capabilities"))

    try:
        available, installed = caps.list_capabilities(target_root, source_kit)
    except Exception:
        # Defensive: missing/malformed manifest shouldn't crash status.
        available, installed = [], []

    available_value = ", ".join(available) if available else "(none)"
    click.echo(f"    {'available':<18} {available_value}")

    installed_value = ", ".join(installed) if installed else "(none)"
    click.echo(f"    {'installed':<18} {installed_value}")


def _report_decisions(target_root: Path) -> None:
    click.echo()
    click.echo("  " + cli_render.style("heading", "Decisions"))
    cor_count = _count_files(target_root / ".pkit" / "decisions" / "core", "COR-*.md")
    prj_count = _count_files(target_root / ".pkit" / "decisions" / "project", "PRJ-*.md")
    click.echo(f"    {'core':<18} {cor_count} records")
    click.echo(f"    {'project':<18} {prj_count} records")

    # ADR namespace (per COR-025). Overlay-resolved; reported only if
    # configured and the directory exists.
    from project_kit.decisions import resolve_adr_records_dir

    try:
        adr_dir = resolve_adr_records_dir(target_root)
    except Exception:  # noqa: BLE001 — soft probe; absence is fine
        return
    adr_count = _count_files(adr_dir, "ADR-*.md")
    click.echo(f"    {'adr':<18} {adr_count} records")


def _report_skills_inventory(target_root: Path) -> None:
    click.echo()
    click.echo("  " + cli_render.style("heading", "Skills"))
    core_count = _count_artifacts(target_root / ".pkit" / "skills" / "core")
    project_count = _count_artifacts(target_root / ".pkit" / "skills" / "project")
    click.echo(f"    {'core':<18} {core_count}")
    click.echo(f"    {'project':<18} {project_count}")


def _report_agents_inventory(target_root: Path) -> None:
    agents_root = target_root / ".pkit" / "agents"
    if not agents_root.is_dir():
        return
    click.echo()
    click.echo("  " + cli_render.style("heading", "Agents"))
    core_count = _count_artifacts(agents_root / "core")
    project_count = _count_artifacts(agents_root / "project")
    click.echo(f"    {'core':<18} {core_count}")
    click.echo(f"    {'project':<18} {project_count}")


def _list_subdir_names(parent: Path) -> list[str]:
    if not parent.is_dir():
        return []
    return sorted(p.name for p in parent.iterdir() if p.is_dir())


def _count_files(parent: Path, pattern: str) -> int:
    if not parent.is_dir():
        return 0
    return sum(1 for _ in parent.rglob(pattern) if _.is_file())


def _count_artifacts(parent: Path) -> int:
    """Count file-bearing artifacts (skills, agents) under a namespace dir.

    Per COR-015 each artifact lives either as a flat `<name>.md` or as a
    folder `<name>/<name>.md`. Both shapes count as one artifact each.
    Ignores `.gitkeep` and similar non-artifact entries.
    """
    if not parent.is_dir():
        return 0
    count = 0
    for entry in parent.iterdir():
        if entry.is_file() and entry.suffix == ".md":
            count += 1
        elif entry.is_dir() and (entry / f"{entry.name}.md").is_file():
            count += 1
    return count


def _kit_skill_link_target(entry: Path) -> str | None:
    """Return the kit-relative symlink target if `entry` is a kit-managed skill.

    Pre-COR-015: `.claude/skills/<name>` is a directory-symlink to
    `.pkit/skills/<ns>/<name>/`. Post-COR-015: `.claude/skills/<name>/`
    is a real directory containing a `SKILL.md` symlink to
    `.pkit/skills/<ns>/<name>.md` (flat) or `.pkit/skills/<ns>/<name>/<name>.md`
    (folder). Both shapes return the resolved source path; non-kit
    entries return None.
    """
    if entry.is_symlink():
        link = os.readlink(entry)
        if "/.pkit/skills/" in link:
            return link
        return None
    if entry.is_dir():
        inner = entry / "SKILL.md"
        if inner.is_symlink():
            link = os.readlink(inner)
            if "/.pkit/skills/" in link:
                return link
    return None


_KIT_AGENT_MARKER = "managed-by: project-kit"


def _has_kit_marker(agent_file: Path) -> bool:
    """True if the deployed agent file carries the kit's marker in its frontmatter.

    The marker is a YAML comment the adapter inserts as line 2 of every
    resolved file (see `.pkit/adapters/claude-code/deploy-agents.sh`).
    Read only enough of the file to find it — large agent bodies don't
    matter.
    """
    try:
        with agent_file.open("r", encoding="utf-8") as f:
            head = "".join(line for _, line in zip(range(5), f))
    except OSError:
        return False
    return _KIT_AGENT_MARKER in head


def _source_agent_names(target_root: Path) -> set[str]:
    """Names of every kit-shipped agent across core/ and project/ namespaces."""
    names: set[str] = set()
    for ns in ("core", "project"):
        ns_dir = target_root / ".pkit" / "agents" / ns
        if not ns_dir.is_dir():
            continue
        for entry in ns_dir.iterdir():
            if entry.is_file() and entry.suffix == ".md":
                names.add(entry.stem)
            elif entry.is_dir() and (entry / f"{entry.name}.md").is_file():
                names.add(entry.name)
    return names
