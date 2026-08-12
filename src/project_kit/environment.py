"""Redacted environment snapshot for `pkit report` (PRJ-008 / ADR-047).

Collects the version + platform context a bug report needs, **redacted by
construction** for a public tracker:

- no filesystem paths at all (only versions + OS/arch/python) — so `$HOME`,
  usernames, and directory structure cannot leak;
- kit-shipped capabilities by name + version, while **incubated (in-repo)
  capability names are withheld by default** (they can reveal internal product
  names, COR-031) — surfaced only under an explicit opt-in.

The snapshot is also **honest about not knowing** (#693): with no project root
resolved, the project half is not collected and renders as explicitly
unresolved, never as `unknown` / `none` / `(none installed)` — values a
maintainer reads as facts about the reporter's install.

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

#: Placeholder for every project-derived field when no project root resolved
#: (#693). Never rendered as a value — `render_environment_block` swaps the
#: whole project half for `UNRESOLVED_ENV_LINES` — but it keeps the dataclass
#: itself from claiming "unknown backbone / no adapter" as a finding.
UNRESOLVED = "unresolved"

#: What the fenced block says instead of the project half when the snapshot was
#: taken outside a pkit project (#693). "Not collected" is the honest reading;
#: the previous `backbone: unknown` / `adapter: none` / `capabilities: (none
#: installed)` read to a maintainer as a FACT about the reporter's install.
#: **Path-free by construction** — this rides into a PUBLIC issue body, so it
#: must never name the directory the compose ran in (that goes to the terminal
#: warning instead).
UNRESOLVED_ENV_LINES = (
    "project env:   NOT COLLECTED — composed outside a pkit project",
    '               (backbone / adapter / capabilities UNKNOWN, not "none")',
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
    #: False when no project root resolved, so the project half of the snapshot
    #: was never collected (#693) — distinct from "collected and found empty".
    project_resolved: bool = True


def collect_environment(
    target_root: Path | None, *, include_private: bool = False
) -> Environment:
    """Gather the redacted environment. Reads the *installed* manifest side
    (what the adopter is actually running), never the kit source.

    `target_root=None` means *no project root resolved* (the caller's
    `find_target_root()` came back empty): the project half is not collected
    at all and the snapshot is marked `project_resolved=False`, rather than
    probing an arbitrary directory and reporting its emptiness as the
    adopter's install (#693). The tool/OS/python half is a property of the
    running process, so it is still honest and still collected."""
    caps: list[tuple[str, str]] = []
    private = 0
    if target_root is None:
        backbone_version = adapter = UNRESOLVED
    else:
        manifest = read_backbone_manifest(target_root)
        backbone_version = manifest.backbone_version if manifest else "unknown"
        adapter = _adapter_summary(target_root)
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
        adapter=adapter,
        os=platform.system() or "unknown",
        arch=platform.machine() or "unknown",
        python=platform.python_version(),
        project_resolved=target_root is not None,
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

    An **unresolved** snapshot (`project_resolved=False`, #693) keeps the same
    fenced shape but swaps the whole project half for `UNRESOLVED_ENV_LINES`,
    so a maintainer reads "not collected", never "nothing installed".
    """
    body = [f"pkit (tool):   {env.tool_version}"]
    if env.project_resolved:
        body.append(f"backbone:      {env.backbone_version}")
        body.append(f"adapter:       {env.adapter}")
    else:
        body.extend(UNRESOLVED_ENV_LINES)
    body.append(f"os:            {env.os} {env.arch}")
    body.append(f"python:        {env.python}")
    if env.project_resolved:
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
