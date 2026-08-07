"""Redacted environment snapshot for `pkit report` (PRJ-008 / ADR-045).

Collects the version + platform context a bug report needs, **redacted by
construction** for a public tracker:

- no filesystem paths at all (only versions + OS/arch/python) — so `$HOME`,
  usernames, and directory structure cannot leak;
- kit-shipped capabilities by name + version, while **incubated (in-repo)
  capability names are withheld by default** (they can reveal internal product
  names, COR-031) — surfaced only under an explicit opt-in.

This is the single version-enumeration accessor `pkit report` consumes, and the
one `status` should read from too (COR-007) so the two never drift.
"""

from __future__ import annotations

import platform
from dataclasses import dataclass
from pathlib import Path

from project_kit.manifest import (
    ORIGIN_KIT_SHIPPED,
    read_backbone_manifest,
    read_component_manifest,
)


@dataclass(frozen=True)
class Environment:
    """A redacted environment snapshot safe to attach to a public bug report."""

    tool_version: str
    backbone_version: str
    #: (name, version) for kit-shipped capabilities, sorted by name.
    capabilities: tuple[tuple[str, str], ...]
    #: count of incubated/in-repo capabilities whose names were withheld.
    private_capability_count: int
    adapter: str
    os: str
    arch: str
    python: str


def collect_environment(
    target_root: Path, *, include_private: bool = False
) -> Environment:
    """Gather the redacted environment. Reads the *installed* manifest side
    (what the adopter is actually running), never the kit source."""
    manifest = read_backbone_manifest(target_root)
    backbone_version = manifest.backbone_version if manifest else "unknown"

    caps: list[tuple[str, str]] = []
    private = 0
    if manifest is not None:
        for entry in manifest.components:
            if entry.kind != "capability":
                continue
            if entry.origin != ORIGIN_KIT_SHIPPED and not include_private:
                # Incubated / in-repo capability — name withheld by default.
                private += 1
                continue
            cm = read_component_manifest(target_root / entry.manifest)
            caps.append((entry.name, cm.version if cm is not None else "unknown"))

    return Environment(
        tool_version=_running_tool_version(),
        backbone_version=backbone_version,
        capabilities=tuple(sorted(caps)),
        private_capability_count=private,
        adapter=_adapter_summary(target_root),
        os=platform.system() or "unknown",
        arch=platform.machine() or "unknown",
        python=platform.python_version(),
    )


def _running_tool_version() -> str:
    # Local import: `router` is off the import-light path, and this keeps the
    # environment module cheap to import.
    from project_kit.router import running_version

    return running_version()


def _adapter_summary(target_root: Path) -> str:
    """The active harness adapter, no paths. Today: claude-code (detected by a
    merged `.claude/settings.json`)."""
    if (target_root / ".claude" / "settings.json").is_file():
        return "claude-code"
    return "none"


def render_environment_block(env: Environment) -> str:
    """Render the `## Environment` markdown section for a report body.

    Pure over `env` (already redacted). A fenced block so it reads verbatim on
    the tracker; contains only versions + platform — no paths.
    """
    body = [
        f"pkit (tool):   {env.tool_version}",
        f"backbone:      {env.backbone_version}",
        f"adapter:       {env.adapter}",
        f"os:            {env.os} {env.arch}",
        f"python:        {env.python}",
    ]
    if env.capabilities:
        body.append(
            "capabilities:  "
            + ", ".join(f"{name} {version}" for name, version in env.capabilities)
        )
    else:
        body.append("capabilities:  (none installed)")
    if env.private_capability_count:
        body.append(
            f"               (+{env.private_capability_count} in-repo "
            "capabilities — names withheld; pass --include-private to include)"
        )
    return "## Environment\n\n```\n" + "\n".join(body) + "\n```\n"
