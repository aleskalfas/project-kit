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

import json
import os
from pathlib import Path
from typing import TYPE_CHECKING

import click

from project_kit import cli_render, workspace
from project_kit.install import find_source_kit, find_target_root
from project_kit.manifest import read_backbone_manifest, read_kit_version

if TYPE_CHECKING:
    from project_kit.connections import Binding, PointBinding, RoleBinding, Wiring
    from project_kit.data_points import ResolvedPoint

# The indent of an entry listed under a status line's label.
_LIST_INDENT = " " * 25


def report_status() -> None:
    """Walk the project tree and print the status report — as one run, so every
    section that reads the wiring reads the same resolution of it (ADR-057 point 2)."""
    from project_kit import validators

    validators.as_one_run(_report_status)


def _report_status() -> None:
    target_root = find_target_root()
    if target_root is None:
        raise click.ClickException("not inside a project tree.")

    source_kit = find_source_kit()
    source_pkit = os.environ.get("PKIT_SOURCE_BIN") or str(Path(__file__).resolve())

    click.echo()
    click.echo(
        cli_render.style(
            "title", "project-kit status — how the methodology is wired in this project"
        )
    )
    click.echo()
    click.echo(f"  {'Project root:':<22} {target_root}")
    click.echo(f"  {'Source pkit:':<22} {source_pkit}")
    click.echo(f"  {'Source kit:':<22} {source_kit}")

    pkit_dir = target_root / ".pkit"
    if not pkit_dir.is_dir():
        click.echo()
        click.echo(
            "  " + cli_render.style("strong", "project-kit is NOT installed in this project.")
        )
        click.echo("  Run 'pkit init' from this project's root to install.")
        click.echo()
        return

    click.echo(f"  {'Kit installed at:':<22} .pkit/")
    _report_backbone_version(target_root, source_kit)
    _report_workspace(target_root)

    _report_claude_adapter(target_root)
    _report_capabilities(target_root, source_kit)
    _report_documentation(target_root)
    _report_friction(target_root)
    _report_rule_sets(target_root)
    _report_connections(target_root)
    _report_data_points(target_root)
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


def _report_workspace(target_root: Path) -> None:
    """The agent workspace (#1043): whether the folder exists and whether git
    ignores it, with `pkit sync` as the remedy when either is missing — or that
    a symlink sits where the folder belongs, which is never the workspace."""
    state = workspace.inspect(target_root)
    if state.symlinked:
        click.echo(
            f"  {'Agent workspace:':<22} {workspace.WORKSPACE_DIR}   (a symlink, never the "
            "workspace — remove the link, then run `pkit sync`)"
        )
        return
    parts = ["present" if state.present else "missing"]
    if not state.in_git:
        parts.append("not a git repository, nothing to exclude it from")
    else:
        parts.append("excluded from git" if state.excluded else "NOT excluded from git")
    gloss = ", ".join(parts)
    if not state.present or (state.in_git and not state.excluded):
        gloss += " — run `pkit sync`"
    click.echo(f"  {'Agent workspace:':<22} {workspace.WORKSPACE_DIR}/   ({gloss})")


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
        origins = caps.installed_capability_origins(target_root)
    except Exception:
        # Defensive: missing/malformed manifest shouldn't crash status.
        available, installed, origins = [], [], {}

    available_value = ", ".join(available) if available else "(none)"
    click.echo(f"    {'available':<18} {available_value}")

    # Annotate each installed capability with its origin so an incubated
    # (in-repo) capability is visibly distinct from a kit-shipped one
    # (COR-031): the adopter sees it's home-grown, not something to upgrade
    # from kit source.
    if installed:
        labelled = [
            f"{name} (incubated)" if origins.get(name) == caps.INCUBATED_IN_REPO else name
            for name in installed
        ]
        installed_value = ", ".join(labelled)
    else:
        installed_value = "(none)"
    click.echo(f"    {'installed':<18} {installed_value}")
    _report_suggestions(target_root, source_kit)


def _report_suggestions(target_root: Path, source_kit: Path) -> None:
    """Capabilities of the local catalogue that would answer an unmet need of the
    wiring — an unfilled data point, a targeted role nobody provides, an upstream
    not installed (COR-053 point 8). Read from package metadata on disk only;
    nothing is fetched and nothing is installed: a suggestion is never an action.
    Shown only when there is one. Reads forgivingly: a broken declaration is
    validate's finding."""
    from project_kit import capability_plans as plans

    try:
        found = plans.suggest(target_root, source_kit)
    except Exception:  # soft probe
        return
    if not found:
        return
    click.echo(f"    {'suggested':<18} {len(found)} from local catalogues (nothing is installed):")
    for suggestion in found:
        click.echo(f"{_LIST_INDENT}{plans.suggestion_line(suggestion)}")


def _report_documentation(target_root: Path) -> None:
    """The two documentation roots with their source, then every recorded
    location — those inside the internal root, then those outside it
    (COR-049 points 6 and 7).

    One line per root, one per recorded location, in a fixed order, so the
    same repository state always renders the same lines. Reads forgivingly:
    an unreadable configuration shows the defaults.
    """
    from project_kit import docs_roots

    click.echo()
    click.echo("  " + cli_render.style("heading", "Documentation"))
    roots = docs_roots.resolve_roots(target_root)
    for label, audience in (
        ("user root", docs_roots.USER_KEY),
        ("internal root", docs_roots.INTERNAL_KEY),
    ):
        path, source = roots.for_audience(audience)
        click.echo(f"    {label:<18} {path.as_posix()}/   ({source.value})")
    try:
        inside = docs_roots.inside_root(target_root, roots)
        outside = docs_roots.outside_root(target_root, roots)
    except Exception:  # soft probe; a broken overlay is validate's finding
        inside, outside = [], []
    for label, where, recorded in (
        ("inside root", "inside", inside),
        ("outside root", "outside", outside),
    ):
        if not recorded:
            continue
        click.echo(
            f"    {label:<18} {len(recorded)} recorded location(s) {where} the internal root:"
        )
        for rec in recorded:
            owner = "" if rec.component == docs_roots.BACKBONE else f" ({rec.component})"
            click.echo(f"{_LIST_INDENT}{rec.name}{owner} -> {rec.path.as_posix()}")


def _report_friction(target_root: Path) -> None:
    """The friction settings discovery reads (COR-050 point 14): the mode, then
    each declared place, surface and excluded path — the project's in written
    order, then each capability's, tagged with the capability.

    Places are always shown, so a project sees at a glance that it declares
    none; surface and exclude only when declared. Rule-set folders are places
    by the location rule, not by declaration, and are not listed. Reads
    forgivingly, as discovery does; `pkit validate` reports a malformed
    setting.
    """
    from project_kit.friction_discovery import read_friction_settings

    click.echo()
    click.echo("  " + cli_render.style("heading", "Friction"))
    try:
        settings = read_friction_settings(target_root)
    except Exception:  # soft probe; a broken configuration is validate's finding
        return
    # A value the reader does not recognise falls back to the default, and says so.
    mode_source = "explicit" if settings.mode == settings.mode_or_default else "default"
    click.echo(f"    {'mode':<18} {settings.mode_or_default}   ({mode_source})")
    if not settings.places:
        click.echo(f"    {'places':<18} none declared")
    for label, declared in (
        ("places", settings.places),
        ("surface", settings.surface),
        ("exclude", settings.exclude),
    ):
        if not declared:
            continue
        click.echo(f"    {label:<18} {len(declared)} declared:")
        for entry in declared:
            owner = "" if entry.source == "project" else f" ({entry.source.split(':', 1)[-1]})"
            click.echo(f"{_LIST_INDENT}{entry.resolved}{owner}")


def _report_rule_sets(target_root: Path) -> None:
    """The rule sets found, then each inheritance pin whose inherited set has moved
    to another major, with the edit that re-pins it (COR-051 point 7).

    The pins are the ones `pkit validate` fails under `versions`, from the same
    computation (`rule_sets.pin_checks`), so the two never disagree; status
    shows each beside that failure with its fix. Reads forgivingly: a rule set
    that cannot be read is validate's finding.
    """
    from project_kit import rule_sets

    click.echo()
    click.echo("  " + cli_render.style("heading", "Rule sets"))
    try:
        discovery = rule_sets.discover_rule_sets(target_root)
        checks = rule_sets.pin_checks(discovery)
    except Exception:  # soft probe; a broken rule set is validate's finding
        return
    if not discovery.rule_sets and not discovery.unreadable:
        click.echo(f"    {'found':<18} none")
        return
    unreadable = f", {len(discovery.unreadable)} unreadable" if discovery.unreadable else ""
    click.echo(
        f"    {'found':<18} {len(discovery.rule_sets)} rule set(s){unreadable}, "
        f"{len(discovery.rules)} rule(s)"
    )
    behind = [check for check in checks if check.repinned is not None]
    if not checks:
        click.echo(f"    {'pins':<18} none")
    elif not behind:
        click.echo(f"    {'pins':<18} {len(checks)} checked, all current")
    else:
        click.echo(
            f"    {'pins':<18} {len(checks)} checked, {len(behind)} behind the inherited "
            f"set's major:"
        )
        for check in behind:
            click.echo(
                f"{_LIST_INDENT}{check.rule_set.citation} pins {check.pin}; "
                f"{check.inherited.citation} is at {check.inherited.version}"
            )
            click.echo(f"{_LIST_INDENT}  fix: {check.fix}")


def _report_connections(target_root: Path) -> None:
    """The resolved wiring (COR-053 point 7): who answers each role, then what
    reaches each point, then the counterparts that reach none.

    Per role: its provider; a conflict — several provide it and none is
    selected — or a selection naming no provider, each with the exact command
    that resolves it, once per provider; or orphaned — no installed capability
    provides it. Per point an active provider defines: the project filler and
    the counterparts bound to it, the inert ones with why, and each mandatory
    mark it leaves unmet. What a data point resolves to, and how its fillers
    combine, is the Data points section's, below — not repeated here.

    The wiring is `pkit validate`'s own (`connections.shared_wiring`), so the
    two never disagree; its findings are validate's to report. Reads
    forgivingly: a failure to resolve leaves the section with its heading only.
    """
    from project_kit import connections

    click.echo()
    click.echo("  " + cli_render.style("heading", "Connections"))
    try:
        wiring = connections.shared_wiring(target_root)
    except Exception:  # soft probe; a broken declaration is validate's finding
        return
    for line in (
        *_role_lines(wiring),
        *_point_lines(wiring, target_root),
        *_unreached_lines(wiring),
    ):
        click.echo(line)


def _role_lines(wiring: Wiring) -> list[str]:
    if not wiring.roles:
        return [f"    {'roles':<18} none named"]
    conflicts = sum(1 for r in wiring.roles if r.conflict)
    orphaned = sum(1 for r in wiring.roles if not r.providers)
    lines = [
        f"    {'roles':<18} {len(wiring.roles)} named: {len(wiring.active_roles())} active, "
        f"{conflicts} in conflict, {orphaned} orphaned"
    ]
    for role in wiring.roles:
        lines.extend(_role_entry(role))
    return lines


def _role_entry(role: RoleBinding) -> list[str]:
    """A role's provider; its conflict, or a selection naming no provider, with a
    fix per provider; or orphaned."""
    from project_kit.connections import provider_set_command

    if role.active is not None:
        notes = ["selected"] if role.selected is not None else []
        others = [p for p in role.providers if p != role.active]
        if others:
            notes.append(f"not selected: {', '.join(others)}")
        tail = f" ({'; '.join(notes)})" if notes else ""
        return [f"{_LIST_INDENT}{role.role} → {role.active}{tail}"]
    if not role.providers:
        named = f"; the selection names {role.selected!r}" if role.selected is not None else ""
        return [f"{_LIST_INDENT}{role.role} — orphaned: no installed capability provides it{named}"]
    if role.conflict:
        state = f"conflict: {', '.join(role.providers)} provide it and none is selected"
    else:
        state = f"the selection names {role.selected!r}, which does not provide it"
    return [
        f"{_LIST_INDENT}{role.role} — {state}",
        *(f"{_LIST_INDENT}  fix: {provider_set_command(role.role, p)}" for p in role.providers),
    ]


def _point_lines(wiring: Wiring, target_root: Path) -> list[str]:
    from project_kit.connections import PointKind

    if not wiring.points:
        return [f"    {'points':<18} none defined"]
    unfilled = sum(1 for p in wiring.points if p.point.kind is PointKind.DATA and not p.filled)
    unmet = sum(1 for p in wiring.points if p.mark_unmet) + sum(
        1 for p in wiring.points for b in p.bindings if wiring.mark_unmet(b)
    )
    lines = [
        f"    {'points':<18} {len(wiring.points)} defined: {unfilled} unfilled, "
        f"{unmet} unmet mandatory mark(s)"
    ]
    for point in wiring.points:
        lines.extend(_wired_point_lines(wiring, point, target_root))
    return lines


def _wired_point_lines(wiring: Wiring, point: PointBinding, target_root: Path) -> list[str]:
    """One point: its kind, version and provider, whether anything fills or
    reaches it, then the project filler and each counterpart — bound or inert —
    and an unmet mandatory mark of its own."""
    from project_kit.connections import PointKind

    p = point.point
    mark = " · mandatory" if p.mandatory is not None else ""
    if p.kind is PointKind.DATA:
        state = "filled" if point.filled else "unfilled"
    else:
        state = f"{len(point.bound)} bound" if point.bindings else "no counterpart"
    lines = [
        f"    {p.address}",
        f"{_LIST_INDENT}{p.kind.value} v{p.version} · {p.provider}{mark} — {state}",
    ]
    filler = point.filler
    if filler is not None:
        path = filler.file
        if path.is_absolute() and path.is_relative_to(target_root):
            path = path.relative_to(target_root)
        who = f"project filler {path.as_posix()}"
        if point.filler_compatible:
            lines.append(f"{_LIST_INDENT}{'bound':<8} {who}")
        else:
            lines.append(
                f"{_LIST_INDENT}{'inert':<8} {who} — targets v{filler.version}; the point is at "
                f"v{p.version}"
            )
    lines.extend(_counterpart_line(wiring, b) for b in point.bindings)
    if point.mark_unmet:
        lines.append(
            f"{_LIST_INDENT}{'unmet':<8} mandatory, filled only by its default "
            f"(reason: {p.mandatory})"
        )
    return lines


def _counterpart_line(wiring: Wiring, binding: Binding) -> str:
    """A counterpart reaching a point: bound, or inert with why."""
    from project_kit.connections import BindingStatus

    c = binding.counterpart
    who = f"{c.capability} ({c.kind.value})"
    mark = _mark(wiring, binding)
    if binding.status is BindingStatus.BOUND:
        return f"{_LIST_INDENT}{'bound':<8} {who}{mark}"
    if binding.status is BindingStatus.INERT_VERSION and binding.point is not None:
        why = f"targets v{c.version}; the point is at v{binding.point.version}"
    elif binding.status is BindingStatus.INERT_PROVIDER:
        why = (
            f"not delivered: {c.capability} provides a role for which it is not the "
            f"selected provider"
        )
    else:
        why = binding.status.value
    return f"{_LIST_INDENT}{'inert':<8} {who} — {why}{mark}"


def _unreached_lines(wiring: Wiring) -> list[str]:
    """The counterparts that reach no point: a role nobody answers, a point its
    role does not define, an upstream not installed."""
    from project_kit.connections import BindingStatus

    unreached = [
        b for b in wiring.bindings if b.point is None and b.status is not BindingStatus.BOUND
    ]
    if not unreached:
        return []
    lines = [f"    {'unreached':<18} {len(unreached)} counterpart(s) reach no point:"]
    for b in unreached:
        c = b.counterpart
        lines.append(
            f"{_LIST_INDENT}{c.capability} ({c.kind.value}) {c.target} — "
            f"{b.status.value}{_mark(wiring, b)}"
        )
    return lines


def _mark(wiring: Wiring, binding: Binding) -> str:
    """A counterpart's mandatory mark, and whether the wiring leaves it unmet."""
    if wiring.mark_unmet(binding):
        return " · mandatory, unmet"
    return " · mandatory" if binding.counterpart.mandatory is not None else ""


def _report_data_points(target_root: Path) -> None:
    """How each data point resolved, and why (COR-052 point 7): where project
    fillers live, then per point its policy, its value or why it has none, and
    every filler considered — taken, inert or passed over, with the reason.

    The resolution is `pkit validate`'s own (`data_points`), so the two never
    disagree; its findings are validate's to report. Command fillers run here as
    they do there, under the query policy. Reads forgivingly: a failure to
    resolve leaves the section with its heading only.
    """
    from project_kit import connections, data_points

    click.echo()
    click.echo("  " + cli_render.style("heading", "Data points"))
    try:
        prefix = connections.fillers_prefix(target_root)
        resolution = data_points.shared_resolution(target_root)
    except Exception:  # soft probe; a broken declaration is validate's finding
        return
    click.echo(f"    {'fillers':<18} {prefix.as_posix()}/   ({resolution.filler_files} file(s))")
    if not resolution.points:
        click.echo(f"    {'points':<18} none defined")
        return
    resolved = sum(1 for p in resolution.points if p.resolved)
    click.echo(
        f"    {'points':<18} {len(resolution.points)} defined: {resolved} resolved, "
        f"{len(resolution.points) - resolved} unresolved"
    )
    for point in resolution.points:
        for line in _data_point_lines(point):
            click.echo(line)


def _data_point_lines(point: ResolvedPoint) -> list[str]:
    """One point: its address, its policy and outcome, its value, its fillers.

    A command filler says whether its command declares the query contract —
    needing no network among its limits — which is declared and trusted, never
    enforced (COR-050 point 2): nothing holds a command to no network (ADR-057
    point 4). One that reads beyond the working tree, once asked, says what it
    read and at which commit, since its answer depends on them (COR-052 point
    7).
    """
    from project_kit.data_points import reads_described

    default = f" · default {point.participation}" if point.participation else ""
    outcome = "resolved" if point.resolved else f"unresolved: {point.why}"
    lines = [
        f"    {point.address}",
        f"{_LIST_INDENT}{point.policy} · inert {point.inert_policy}{default} — {outcome}",
    ]
    if point.entries:
        for entry in point.entries:
            replaces = f", replaces {', '.join(entry.replaces)}" if entry.replaces else ""
            lines.append(f"{_LIST_INDENT}{'entry':<8} {entry.id} — {entry.origin}{replaces}")
    elif point.resolved and point.origin:
        lines.append(f"{_LIST_INDENT}{'value':<8} {_compact(point.value)} — {point.origin}")
    elif point.resolved:
        lines.append(f"{_LIST_INDENT}{'value':<8} no entries")
    for removal in point.removals:
        source = (
            f"from {', '.join(removal.removed_from)}" if removal.removed_from else "matched nothing"
        )
        lines.append(f"{_LIST_INDENT}{'removed':<8} {removal.id} — {removal.reason} ({source})")
    for filler in point.fillers:
        how = filler.label
        if filler.query_contract is not None:
            declared = (
                "query contract declared: no network, trusted, not enforced"
                if filler.query_contract
                else "no query-contract declaration"
            )
            reads = f"; reads {reads_described(filler.reads)}" if filler.reads else ""
            how = f"{filler.name} ({filler.supplies}; {declared}{reads})"
        reason = f" — {filler.reason}" if filler.reason else ""
        lines.append(f"{_LIST_INDENT}{'filler':<8} {how}: {filler.state.value}{reason}")
    return lines


def _compact(value: object, limit: int = 72) -> str:
    """A value on one line, cut at `limit` characters."""
    text = json.dumps(value, sort_keys=True, ensure_ascii=False, default=str)
    return text if len(text) <= limit else text[: limit - 1] + "…"


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
    except Exception:  # soft probe; absence is fine
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
        if (entry.is_file() and entry.suffix == ".md") or (
            entry.is_dir() and (entry / f"{entry.name}.md").is_file()
        ):
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
            head = "".join(line for _, line in zip(range(5), f, strict=False))
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
