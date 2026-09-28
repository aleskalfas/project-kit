"""Capability-command dispatcher (per COR-021).

The kit's top-level CLI group uses `CapabilityDispatchGroup` so that
installed capabilities' subcommands resolve lazily on each invocation:
`get_command()` and `list_commands()` walk the backbone manifest and
parse each installed capability's `package.yaml` for a `commands:` tree.

Per the COR, the dispatcher is **stateless across invocations** — no
cache; every CLI call rediscovers the surface from disk so capability
install / uninstall surfaces immediately without a refresh step.

The `commands:` tree is read through the backbone's one command lookup
(`command_runner`, ADR-057 point 5) — the walk package validation, the
validator registry and the process engine's predicate runner read too — so
`pkit <capability> <tokens…>` runs the leaf every other reader resolves.

Scripts named in command leaves are proxied via subprocess. Arguments
after the resolved subcommand pass through verbatim; the script's exit
code becomes the CLI's exit code; standard streams are inherited. The
proxy is a person's focused surface, so it takes the lookup and not the
bounded run: nothing here is timed out or captured.
"""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import click
from ruamel.yaml import YAML

from project_kit.command_runner import (
    HELP_KEY,
    RegisteredCommand,
    commands_of,
    registered_commands,
    resolve_command,
)
from project_kit.install import find_target_root
from project_kit.manifest import read_backbone_manifest


_yaml = YAML(typ="safe")


class CapabilityDispatchGroup(click.Group):
    """Click `Group` that lazily resolves installed-capability subcommands.

    Static (decorator-registered) subcommands take precedence — only
    when no static command matches does the dispatcher walk installed
    capabilities. This means a kit-internal command name always wins
    over a capability namespace of the same name (per COR-021's
    name-resolution-on-conflict rule).
    """

    def get_command(self, ctx: click.Context, cmd_name: str) -> click.Command | None:
        static = super().get_command(ctx, cmd_name)
        if static is not None:
            return static
        capability_commands = _discover_capability_commands()
        return capability_commands.get(cmd_name)

    def list_commands(self, ctx: click.Context) -> list[str]:
        static = list(super().list_commands(ctx))
        dynamic = list(_discover_capability_commands().keys())
        return sorted(set(static + dynamic))


def _discover_capability_commands() -> dict[str, click.Group]:
    """Walk installed capabilities and build their top-level command groups.

    Returns `{capability_name: click.Group}` for every installed
    capability whose `package.yaml` declares a `commands:` block, plus
    one entry per declared alias (e.g. `pm` → the `project-management`
    group) pointing at the same group object.

    Capabilities without a `commands:` block do not surface a namespace
    here — installation alone doesn't create a CLI surface; declaration
    does.

    Resolution rules:
      - Static (decorator-registered) subcommands take precedence over
        anything here (enforced by `CapabilityDispatchGroup.get_command`).
      - A capability's canonical name takes precedence over any alias.
        Aliases register in a second pass and only fill slots not
        already claimed by a canonical name.
      - First-declared-wins among alias collisions (deterministic in
        manifest order).

    Errors reading a single capability's `package.yaml` cause that
    capability to be skipped; other capabilities still register.
    """
    target_root = find_target_root()
    if target_root is None:
        return {}

    backbone = read_backbone_manifest(target_root)
    if backbone is None:
        return {}

    out: dict[str, click.Group] = {}
    pending_aliases: list[tuple[str, str]] = []  # (alias, canonical_name)
    for component in backbone.components:
        if component.kind != "capability":
            continue
        cap_dir = target_root / ".pkit" / "capabilities" / component.name
        if not cap_dir.is_dir():
            continue
        package_yaml = cap_dir / "package.yaml"
        if not package_yaml.is_file():
            continue

        commands_tree, description, aliases = _read_commands_description_and_aliases(
            package_yaml
        )
        if commands_tree is None:
            continue

        out[component.name] = _build_capability_group(
            component.name, commands_tree, cap_dir, description
        )
        for alias in aliases:
            pending_aliases.append((alias, component.name))

    for alias, canonical_name in pending_aliases:
        if alias in out:
            # Canonical capability name claims the slot, or an earlier
            # alias already won the deterministic first-declared rule.
            continue
        out[alias] = out[canonical_name]
    return out


def resolve_capability_script(
    target_root: Path, capability: str, command: str
) -> Path | None:
    """Resolve an installed capability's command leaf to its script path —
    `command` is a reference, a path through the `commands:` tree (tokens
    separated by spaces), resolved by the same lookup the dispatch group
    uses, exposed for backbone code that invokes a capability verb by
    subprocess (per COR-021; first consumer: ADR-050's `context-workstream`
    read on report compose).

    Returns None on every degrade axis — capability not registered in the
    backbone manifest, subtree or `package.yaml` missing, no such command
    declared, or the declared script file absent — so callers can treat the
    verb as optional.
    """
    backbone = read_backbone_manifest(target_root)
    if backbone is None:
        return None
    for component in backbone.components:
        if component.kind != "capability" or component.name != capability:
            continue
        cap_dir = target_root / ".pkit" / "capabilities" / capability
        leaf = resolve_command(registered_commands(cap_dir), command)
        if leaf is None or not leaf.script.is_file():
            return None
        return leaf.script
    return None


def _read_commands_description_and_aliases(
    package_yaml: Path,
) -> tuple[dict[str, Any] | None, str, list[str]]:
    """Parse `commands:`, `description:`, and optional `aliases:` from package.yaml.

    Returns (commands_tree, description, aliases). `commands_tree` is
    None when the file is unreadable or has no `commands:` block.
    `description` defaults to "" on failure. `aliases` defaults to []
    when missing or malformed; only string entries are kept.
    """
    try:
        raw = _yaml.load(package_yaml.read_text(encoding="utf-8"))
    except Exception:
        return None, "", []
    if not isinstance(raw, dict):
        return None, "", []
    description = str(raw.get("description", ""))
    commands = raw.get("commands")
    aliases_raw = raw.get("aliases", [])
    aliases = (
        [a for a in aliases_raw if isinstance(a, str) and a]
        if isinstance(aliases_raw, list)
        else []
    )
    if not isinstance(commands, dict):
        return None, description, aliases
    return commands, description, aliases


def _build_capability_group(
    name: str,
    commands_tree: dict[str, Any],
    cap_dir: Path,
    description: str,
) -> click.Group:
    """Construct the top-level Click group for one capability."""
    short_help = _short_help(description)

    @click.group(
        name=name,
        help=description or None,
        short_help=short_help,
        invoke_without_command=True,
    )
    @click.pass_context
    def cap_group(ctx: click.Context) -> None:
        if ctx.invoked_subcommand is None:
            click.echo(ctx.get_help())

    _add_commands_to_group(cap_group, commands_tree, cap_dir)
    return cap_group


def _add_commands_to_group(
    group: click.Group,
    commands_tree: dict[str, Any],
    cap_dir: Path,
) -> None:
    """Add the tree's leaves and sub-groups to `group`. Which node is a leaf,
    and the script it runs, is the one lookup's answer (`commands_of`); the
    walk here only lays out the groups, each with its own `help`."""
    _add_level(group, commands_tree, (), commands_of(cap_dir, commands_tree))


def _add_level(
    group: click.Group,
    node: Mapping[Any, Any],
    prefix: tuple[str, ...],
    commands: Mapping[tuple[str, ...], RegisteredCommand],
) -> None:
    for key, value in node.items():
        if not isinstance(value, Mapping):
            continue
        tokens = (*prefix, str(key))
        command = commands.get(tokens)
        if command is not None:
            group.add_command(
                _make_proxy_command(
                    name=command.name, script_path=command.script, help_text=command.help
                )
            )
        else:
            sub = _make_sub_group(name=str(key), help_text=str(value.get(HELP_KEY, "")))
            _add_level(sub, value, tokens, commands)
            group.add_command(sub)


def _make_sub_group(name: str, help_text: str) -> click.Group:
    """Factory for a sub-group inside a capability namespace."""
    short_help = _short_help(help_text)

    @click.group(
        name=name,
        help=help_text or None,
        short_help=short_help,
        invoke_without_command=True,
    )
    @click.pass_context
    def grp(ctx: click.Context) -> None:
        if ctx.invoked_subcommand is None:
            click.echo(ctx.get_help())

    return grp


def _make_proxy_command(
    name: str, script_path: Path, help_text: str
) -> click.Command:
    """Factory for a leaf command that proxies args to a capability script."""
    short_help = _short_help(help_text)

    @click.command(
        name=name,
        help=help_text or None,
        short_help=short_help,
        context_settings={
            "ignore_unknown_options": True,
            "allow_extra_args": True,
            "help_option_names": [],
        },
    )
    @click.argument("args", nargs=-1, type=click.UNPROCESSED)
    def cmd(args: tuple[str, ...]) -> None:
        if not script_path.is_file():
            raise click.ClickException(f"script not found: {script_path}")
        result = subprocess.run([str(script_path), *args])
        sys.exit(result.returncode)

    return cmd


def _short_help(text: str) -> str:
    """First sentence or first line of `text`, capped at 80 chars."""
    if not text:
        return ""
    head = text.split("\n", 1)[0].split(". ", 1)[0]
    if len(head) > 80:
        head = head[:77] + "..."
    return head
