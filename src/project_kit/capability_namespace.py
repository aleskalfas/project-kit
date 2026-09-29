"""A capability name as an authoring namespace.

`pkit new decision`, `pkit new agent` and `pkit new storyboard` each take a
namespace: one of the command's fixed names (`core`, `project`, and for
decisions `adr`) or the name of a capability under `.pkit/capabilities/`. This
module holds the capability half once — the existence contract (a capability is
a directory carrying a `package.yaml`, the contract the capability lifecycle
uses) and the one refusal every authoring command gives for a name that is
neither, listing the capabilities that do exist.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from pathlib import Path

import click

CAPABILITIES_DIR = Path(".pkit") / "capabilities"

# Capability names are kebab-case (`pkit new capability` enforces it). Anything
# else — a path segment such as `..` among them — names no capability.
_CAPABILITY_NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def capability_names(target_root: Path) -> list[str]:
    """Sorted names of the capabilities under `.pkit/capabilities/` (each has a package.yaml)."""
    caps_dir = target_root / CAPABILITIES_DIR
    if not caps_dir.is_dir():
        return []
    return sorted(
        entry.name
        for entry in caps_dir.iterdir()
        if entry.is_dir() and (entry / "package.yaml").is_file()
    )


def resolve_capability_dir(target_root: Path, namespace: str, fixed: Iterable[str]) -> Path:
    """The directory of the capability `namespace` names, or refuse.

    `fixed` are the command's own namespaces; the refusal names them beside the
    available capabilities, so a typo'd name reads against every value the
    argument accepts instead of silently creating a stray tree.
    """
    cap_dir = target_root / CAPABILITIES_DIR / namespace
    if _CAPABILITY_NAME_RE.match(namespace) and (cap_dir / "package.yaml").is_file():
        return cap_dir
    available = capability_names(target_root)
    avail_note = (
        f" Available capabilities: {', '.join(available)}."
        if available
        else " No capabilities are present under .pkit/capabilities/."
    )
    raise click.ClickException(
        f"unknown namespace {namespace!r}: not one of {'/'.join(fixed)} and "
        f"no capability at .pkit/capabilities/{namespace}/.{avail_note}"
    )
