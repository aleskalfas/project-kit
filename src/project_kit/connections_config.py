"""The provider selection, written with consent: `pkit connections providers set`.

A qualified role that several installed capabilities provide is in conflict
until the project selects one (COR-053 points 1 and 7). The selection is the
backbone configuration's provider-selection key, `connections.providers`, and
it is written only through the configuration's one consent-gated writer
(`project_config.write_config`, COR-048 point 5) — `preview_config` giving the
dry run's diff of exactly what the write would make.

Before anything is written, the capability must be installed and must declare
the role: the resolver's reading of the installed packages decides it
(`connections.load_declarations`, `Declarations.providers_of`), the reading the
configuration pass checks an existing entry against, so a selection this
command writes is one `pkit validate` accepts.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import click
from ruamel.yaml.comments import CommentedMap

from project_kit import connections as cx
from project_kit import project_config


class ProviderRefused(click.ClickException):
    """The capability cannot answer the role: not installed, or it does not provide it."""


def refusal(declarations: cx.Declarations, role: str, capability: str) -> str | None:
    """Why `capability` cannot be selected as the provider of `role`, naming what
    can; None when it declares the role."""
    providers = declarations.providers_of(role)
    if capability in providers:
        return None
    if declarations.by_name(capability) is None:
        why = (
            f"{capability!r} is not an installed capability; install or register it first "
            f"(`pkit capabilities install {capability}`)"
        )
    else:
        roles = declarations.roles_of(capability)
        provides = f"it provides {_names(roles)}" if roles else "it provides no role"
        why = f"{capability!r} does not provide role {role!r} ({provides})"
    if providers:
        choices = " or ".join(f"`{cx.provider_set_command(role, p)}`" for p in providers)
        choice = f"the installed providers of the role are {_names(providers)}: {choices}"
    else:
        choice = "no installed capability provides the role"
    return f"{why}; {choice} (COR-053 point 7)."


def select(role: str, capability: str) -> Callable[[CommentedMap], None]:
    """The mutation: `connections.providers.<role>` set to `capability`."""
    segments = (cx.CONNECTIONS_KEY, cx.PROVIDERS_KEY, role)
    return lambda data: project_config.set_path(data, segments, capability)


def plan(target_root: Path, role: str, capability: str) -> project_config.ConfigChange:
    """What selecting `capability` for `role` would write, checked first: refused
    (`ProviderRefused`) when the capability cannot answer the role, and — by the
    writer — when the result would not validate. Nothing is written."""
    problem = refusal(cx.load_declarations(target_root), role, capability)
    if problem is not None:
        raise ProviderRefused(f"refusing to select {capability!r} for role {role!r}: {problem}")
    return project_config.preview_config(target_root, select(role, capability))


def write(target_root: Path, role: str, capability: str, *, yes: bool) -> Path:
    """Write the selection through the consent-gated writer: `--yes`, or a
    terminal's confirmation; a non-interactive run without `--yes` refuses,
    naming the exact command. Call `plan` first: it checks the capability."""
    return project_config.write_config(
        target_root,
        select(role, capability),
        consent=project_config.Consent(
            yes=yes, rerun=f"{cx.provider_set_command(role, capability)} --yes"
        ),
        description=f"Set {key(role)} = {capability!r}",
    )


def key(role: str) -> str:
    """The dotted configuration key the selection of `role` is written at."""
    return f"{cx.CONNECTIONS_KEY}.{cx.PROVIDERS_KEY}.{role}"


def _names(names: tuple[str, ...]) -> str:
    return ", ".join(repr(n) for n in names)
