"""Authoring scaffolds for `pkit new adapter / migration / area / capability`.

Each function stamps the contract its owning record fixes (COR-005 for
adapters, COR-010 for migrations, COR-011 for areas, COR-017 for
capabilities) and wires the result into the manifest layer where
applicable. The conversational layer — slug choice, body drafting,
discipline self-checks — is each paired skill's job (per COR-005's
"Skill / command pairing"); these functions are the deterministic
stamp underneath.

Design parallels `project_kit.decisions.stamp_decision`: each helper
returns the stamped path (or directory) and raises `click.ClickException`
for any user-facing precondition failure (invalid slug, missing
prerequisite, name collision). All writes are synchronous; no dry-run
mode (one-shot scaffolds are not destructive — a stray run leaves a
fresh directory the author can `rm -rf` if they didn't mean to).
"""

from __future__ import annotations

import re
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import click

from project_kit.manifest import (
    ComponentRegistryEntry,
    read_backbone_manifest,
    read_kit_version,
    write_backbone_manifest,
)

_SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
_AREA_NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
_VERSION_RE = re.compile(r"^(\d+)\.(\d+)\.0$")

AreaVariant = Literal["universal", "adapter-umbrella", "specialized"]
MigrationTier = Literal["backbone", "adapter", "capability"]
MigrationScope = Literal["manifest-schema", "structural", "resource"]


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------


_PACKAGE_YAML_TEMPLATE = """\
schema_version: 1
component:
  kind: {kind}
  name: {name}
  version: 0.1.0
requires_backbone: "{requires_backbone}"
"""


_CAPABILITY_PACKAGE_YAML_TEMPLATE = """\
schema_version: 1
component:
  kind: capability
  name: {name}
  version: 0.1.0
description: <one-line summary of what discipline this capability formalises>
requires_backbone: "{requires_backbone}"
"""


_CAPABILITY_README_TEMPLATE = """\
# {name} capability

<one-paragraph summary: what discipline this capability formalises, who it's for,
when an adopter would install it (per COR-017)>

## What this capability ships

<list the kit-shipped artifacts an adopter receives when they
`pkit capabilities install {name}`: decisions, skills, agents, scripts, schemas>

- `decisions/DEC-NNN-*.md` — <the principles this capability fixes>
- `skills/<name>.md` — <the operational tasks this capability requires>
- `scripts/<name>.{{py,sh}}` — <runtime tools, if any>

## Adopter setup

Install:

```
pkit capabilities install {name}
```

After install:

<describe any per-project configuration the adopter must fill in, or
files/conventions they need to author themselves>

## Citing this capability's decisions

Inside this capability's own content, cite decisions by their filename
stem: `[{name}:DEC-001-<slug>]`. Other capabilities and adopter content
use the same form.

## Dependencies

<what the adopter needs in place for this capability to work — external
tooling, accounts, conventions, other capabilities>
"""


_ADAPTER_README_TEMPLATE = """\
# {name} adapter

<one-paragraph summary: which harness this adapter translates for, what
kit content it carries across>

## What this adapter ships

```
.pkit/adapters/{name}/
├── README.md                          # this file
├── package.yaml                       # component metadata (per COR-010)
├── migrations/                        # version migrations (per COR-010)
└── (harness-specific content)         # settings, deploy scripts, runtime artifacts
```

## How adopters use this adapter

<deployment steps: how settings get merged, how skills/agents get deployed,
what the adopter has to do once vs. what happens at install/sync>
"""


_MIGRATION_TEMPLATE = """\
#!/usr/bin/env bash
# {scope_comment}
# Idempotent — re-running on already-migrated state is a no-op.

set -euo pipefail

# ROOT is the adopter's project root, provided by the runtime.
: "${{ROOT:?ROOT must be set by the upgrade runtime}}"

# TODO: implement the migration.
# Detect already-applied state and exit cleanly:
#   if <state is already correct>; then
#       echo "  exists  <description>"
#       exit 0
#   fi
#
# Then apply the change idempotently.

echo "  TODO  {slug} migration not yet implemented"
"""


_AREA_README_BY_VARIANT: dict[AreaVariant, str] = {
    "universal": """\
---
variant: universal
---

# {title}

<one-paragraph summary: what this area is for, who consumes its content>

## Layout

```
.pkit/{name}/
├── README.md                          # this file
├── core/                              # kit-owned content (propagation)
└── project/                           # adopter-owned content (extension)
```

The `core/` + `project/` split is the universal area pattern (per COR-003).
""",
    "adapter-umbrella": """\
---
variant: adapter-umbrella
---

# {title}

<one-paragraph summary: what kinds of adapters live here>

## Layout

```
.pkit/{name}/
├── README.md                          # this file
└── <adapter-name>/                    # one directory per supported harness/backend
    ├── README.md
    └── (adapter-specific content)
```

The adapter-umbrella variant is per COR-005.
""",
    "specialized": """\
---
variant: specialized
---

# {title}

<one-paragraph summary: what this area is for, what content shape it has>

<describe the area's own internal layout below; specialized areas do not
follow the universal core/project shape>
""",
}


# ---------------------------------------------------------------------------
# Capabilities (per COR-017)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CapabilityScaffoldResult:
    """Paths created by `stamp_capability`."""

    capability_dir: Path
    package_yaml: Path
    readme: Path
    decisions_dir: Path
    skills_dir: Path
    agents_dir: Path
    scripts_dir: Path
    schemas_dir: Path
    migrations_dir: Path


def stamp_capability(target_root: Path, name: str) -> CapabilityScaffoldResult:
    """Scaffold a new capability at `.pkit/capabilities/<name>/` (per COR-017).

    Creates:
    - `package.yaml` with `component.kind: capability`, `version: 0.1.0`,
      and a `requires_backbone:` pinned to the project's current backbone.
    - `README.md` adopter-facing template explaining the discipline.
    - Empty `decisions/`, `skills/`, `agents/`, `scripts/`, `schemas/`,
      and `migrations/` subdirectories with `.gitkeep` (per COR-017's
      subdir taxonomy plus the COR-010 migration directory for version
      bumps).

    Refuses if `name` is not kebab-case or a capability with that name
    already exists.
    """
    _validate_kebab_case(name, "capability name")

    pkit_dir = _require_pkit_dir(target_root)
    caps_dir = pkit_dir / "capabilities"
    caps_dir.mkdir(parents=True, exist_ok=True)

    capability_dir = caps_dir / name
    if capability_dir.exists():
        raise click.ClickException(
            f"capability '{name}' already exists at {capability_dir.relative_to(target_root)}."
        )

    capability_dir.mkdir(parents=True, exist_ok=False)

    package_yaml = capability_dir / "package.yaml"
    requires_backbone = _default_requires_backbone(target_root)
    package_yaml.write_text(
        _CAPABILITY_PACKAGE_YAML_TEMPLATE.format(
            name=name, requires_backbone=requires_backbone
        ),
        encoding="utf-8",
    )

    readme = capability_dir / "README.md"
    readme.write_text(_CAPABILITY_README_TEMPLATE.format(name=name), encoding="utf-8")

    # Empty subtrees with `.gitkeep` so git tracks the skeleton even
    # before the first decision / skill / agent / script / schema /
    # migration lands.
    decisions_dir = capability_dir / "decisions"
    skills_dir = capability_dir / "skills"
    agents_dir = capability_dir / "agents"
    scripts_dir = capability_dir / "scripts"
    schemas_dir = capability_dir / "schemas"
    migrations_dir = capability_dir / "migrations"
    for sub in (decisions_dir, skills_dir, agents_dir, scripts_dir, schemas_dir, migrations_dir):
        sub.mkdir(parents=True, exist_ok=False)
        (sub / ".gitkeep").touch()

    return CapabilityScaffoldResult(
        capability_dir=capability_dir,
        package_yaml=package_yaml,
        readme=readme,
        decisions_dir=decisions_dir,
        skills_dir=skills_dir,
        agents_dir=agents_dir,
        scripts_dir=scripts_dir,
        schemas_dir=schemas_dir,
        migrations_dir=migrations_dir,
    )


# ---------------------------------------------------------------------------
# Adapters
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AdapterScaffoldResult:
    """Paths created by `stamp_adapter`."""

    adapter_dir: Path
    package_yaml: Path
    readme: Path
    migrations_dir: Path


def stamp_adapter(target_root: Path, name: str) -> AdapterScaffoldResult:
    """Scaffold a new adapter at `.pkit/adapters/<name>/`.

    Refuses if `name` is not kebab-case or an adapter with the same name
    already exists.
    """
    _validate_kebab_case(name, "adapter name")

    pkit_dir = _require_pkit_dir(target_root)
    adapters_dir = pkit_dir / "adapters"
    if not adapters_dir.is_dir():
        raise click.ClickException(
            f"{adapters_dir.relative_to(target_root)} does not exist. "
            f"Run 'pkit init' from this project's root first."
        )

    adapter_dir = adapters_dir / name
    if adapter_dir.exists():
        raise click.ClickException(
            f"adapter '{name}' already exists at {adapter_dir.relative_to(target_root)}."
        )

    adapter_dir.mkdir(parents=True, exist_ok=False)
    package_yaml = adapter_dir / "package.yaml"
    package_yaml.write_text(
        _package_yaml_for("adapter", name, target_root),
        encoding="utf-8",
    )
    readme = adapter_dir / "README.md"
    readme.write_text(_ADAPTER_README_TEMPLATE.format(name=name), encoding="utf-8")
    migrations_dir = adapter_dir / "migrations"
    migrations_dir.mkdir(parents=True, exist_ok=False)
    (migrations_dir / ".gitkeep").touch()

    return AdapterScaffoldResult(
        adapter_dir=adapter_dir,
        package_yaml=package_yaml,
        readme=readme,
        migrations_dir=migrations_dir,
    )


# ---------------------------------------------------------------------------
# Migrations
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MigrationScaffoldResult:
    """Path of the stamped migration script."""

    script: Path


def stamp_migration(
    target_root: Path,
    tier: MigrationTier,
    version: str | None,
    slug: str | None,
    component: str | None = None,
    scope: MigrationScope = "resource",
) -> MigrationScaffoldResult:
    """Drop a numbered migration script in the right `<major>.<minor>.0/` directory.

    Tier-specific layout (per COR-010 + `.pkit/lifecycle/README.md`):
    - `backbone` → `.pkit/migrations/backbone/<X.Y.0>/<NNN>-<slug>.sh`
    - `adapter` → `.pkit/adapters/<component>/migrations/<X.Y.0>/<NNN>-<slug>.sh`
    - `capability` → `.pkit/capabilities/<component>/migrations/<X.Y.0>/<NNN>-<slug>.sh`

    The component name is required for `adapter` / `capability` tiers. The
    script is stamped with the COR-010 contract boilerplate (`set -euo
    pipefail`, `ROOT` consumption, idempotence-pattern comment) and made
    executable.

    For component tiers, the version defaults to the component's recorded
    version (read from `package.yaml`) when omitted. For the backbone
    tier, version is taken from `.pkit/VERSION` when omitted. Either way,
    a passed version overrides.
    """
    pkit_dir = _require_pkit_dir(target_root)

    if tier == "backbone":
        if component is not None:
            raise click.ClickException("--component is not allowed for tier 'backbone'.")
        migrations_root = pkit_dir / "migrations" / "backbone"
        resolved_version = version or _read_backbone_version(target_root)
    else:
        if not component:
            raise click.ClickException(f"--component <name> is required for tier '{tier}'.")
        _validate_kebab_case(component, "component name")
        component_dir = _resolve_component_dir(pkit_dir, tier, component)
        if not component_dir.is_dir():
            raise click.ClickException(f"{tier} '{component}' not found in this project tree.")
        migrations_root = component_dir / "migrations"
        resolved_version = version or _read_component_version(component_dir)

    _validate_minor_version(resolved_version)

    if not slug:
        raise click.ClickException("--name <slug> is required.")
    _validate_kebab_case(slug, "migration slug")

    version_dir = migrations_root / resolved_version
    version_dir.mkdir(parents=True, exist_ok=True)

    next_num = _next_migration_number(version_dir)
    nnn = f"{next_num:03d}"
    script_path = version_dir / f"{nnn}-{slug}.sh"

    scope_comment = _migration_scope_comment(tier, component, resolved_version, scope, slug)
    script_path.write_text(
        _MIGRATION_TEMPLATE.format(scope_comment=scope_comment, slug=slug),
        encoding="utf-8",
    )
    _make_executable(script_path)

    return MigrationScaffoldResult(script=script_path)


def _migration_scope_comment(
    tier: MigrationTier,
    component: str | None,
    version: str,
    scope: MigrationScope,
    slug: str,
) -> str:
    """Build the leading comment that names the migration's tier/scope/version."""
    subject = f"Backbone migration {version}" if tier == "backbone" else f"{component} {version}"
    return f"{subject} — {scope}: {slug}."


# ---------------------------------------------------------------------------
# Areas
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AreaScaffoldResult:
    """Paths created by `stamp_area`."""

    area_dir: Path
    readme: Path


def stamp_area(
    target_root: Path,
    name: str,
    variant: AreaVariant = "specialized",
) -> AreaScaffoldResult:
    """Scaffold a new area at `.pkit/<name>/` with the variant's expected layout.

    Refuses if `name` is not kebab-case or an area with the same name
    already exists (kit-shipped or otherwise — the no-shared-files
    invariant prevents collision).
    """
    _validate_kebab_case(name, "area name")
    if not _AREA_NAME_RE.match(name):
        raise click.ClickException("area name must be kebab-case.")

    pkit_dir = _require_pkit_dir(target_root)
    area_dir = pkit_dir / name
    if area_dir.exists():
        raise click.ClickException(
            f"area '{name}' already exists at {area_dir.relative_to(target_root)}."
        )

    area_dir.mkdir(parents=True, exist_ok=False)

    readme_template = _AREA_README_BY_VARIANT[variant]
    title = _title_case(name)
    readme = area_dir / "README.md"
    readme.write_text(readme_template.format(name=name, title=title), encoding="utf-8")

    # Stamp the variant's expected sub-directory layout so the area is
    # immediately usable.
    if variant == "universal":
        (area_dir / "core").mkdir(parents=True, exist_ok=False)
        (area_dir / "core" / ".gitkeep").touch()
        (area_dir / "project").mkdir(parents=True, exist_ok=False)
        (area_dir / "project" / ".gitkeep").touch()
    # adapter-umbrella and specialized: README + leave sub-layout to the author.

    return AreaScaffoldResult(area_dir=area_dir, readme=readme)


# ---------------------------------------------------------------------------
# Manifest registration (for components)
# ---------------------------------------------------------------------------


def register_kit_shipped_component(
    target_root: Path,
    kind: Literal["adapter"],
    name: str,
    manifest_path: str,
) -> None:
    """Append (or refresh) a kit-shipped component entry in the backbone manifest.

    Used by the adapter scaffold command to honour the "Scaffold output is
    wired" implication: a freshly-stamped component is immediately
    discoverable via the backbone manifest's `components` registry, no
    manual edit needed.

    No-op if the backbone manifest doesn't exist (e.g. before `pkit init`).
    """
    backbone = read_backbone_manifest(target_root)
    if backbone is None:
        return

    entry = ComponentRegistryEntry(kind=kind, name=name, manifest=manifest_path)
    # De-duplicate (in case of stale state).
    backbone.components = [
        c for c in backbone.components if not (c.kind == kind and c.name == name)
    ]
    backbone.components.append(entry)
    write_backbone_manifest(target_root, backbone)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _validate_kebab_case(value: str, label: str) -> None:
    if not _SLUG_RE.match(value):
        raise click.ClickException(
            f"{label} {value!r} must be kebab-case (lowercase letters, digits, single hyphens)."
        )


def _validate_minor_version(value: str) -> None:
    if not _VERSION_RE.match(value):
        raise click.ClickException(
            f"version {value!r} must be X.Y.0 (patch segment must be 0 per COR-010 — "
            f"patches have no migrations)."
        )


def _require_pkit_dir(target_root: Path) -> Path:
    pkit_dir = target_root / ".pkit"
    if not pkit_dir.is_dir():
        raise click.ClickException(
            f"{target_root}/.pkit/ does not exist. Run 'pkit init' from this project's root first."
        )
    return pkit_dir


_AREA_VARIANT_RE = re.compile(r"^variant:\s*([A-Za-z0-9-]+)\s*$", re.MULTILINE)


def _read_area_variant(readme: Path) -> str | None:
    """Read the `variant:` line from an area's README frontmatter.

    Returns None if the README is missing or has no variant declaration.
    """
    if not readme.is_file():
        return None
    text = readme.read_text(encoding="utf-8")
    match = _AREA_VARIANT_RE.search(text)
    return match.group(1) if match else None


def _read_backbone_version(target_root: Path) -> str:
    """Resolve the recorded backbone version's `X.Y.0` form.

    Prefers the project's backbone manifest; falls back to `.pkit/VERSION`
    in the project tree. Whatever's read is truncated to `X.Y.0` (the
    migration-directory naming rule per COR-010).
    """
    backbone = read_backbone_manifest(target_root)
    if backbone is not None and backbone.backbone_version:
        return _truncate_to_minor(backbone.backbone_version)
    version_file = target_root / ".pkit" / "VERSION"
    if version_file.is_file():
        return _truncate_to_minor(read_kit_version(target_root / ".pkit"))
    raise click.ClickException(
        "can't resolve a backbone version (no manifest, no .pkit/VERSION). "
        "Pass --version <X.Y.0> explicitly."
    )


def _read_component_version(component_dir: Path) -> str:
    """Read a component's `version` field from its `package.yaml`, truncated to X.Y.0."""
    package_yaml = component_dir / "package.yaml"
    if not package_yaml.is_file():
        raise click.ClickException(
            f"component at {component_dir} has no package.yaml — can't infer version. "
            f"Pass --version <X.Y.0> explicitly."
        )
    text = package_yaml.read_text(encoding="utf-8")
    match = re.search(r"version:\s*([0-9]+\.[0-9]+\.[0-9]+)", text)
    if match is None:
        raise click.ClickException(
            f"component's package.yaml at {package_yaml} has no version field. "
            f"Pass --version <X.Y.0> explicitly."
        )
    return _truncate_to_minor(match.group(1))


def _truncate_to_minor(version: str) -> str:
    """`1.2.3` → `1.2.0`. Per COR-010 migration directories always end `.0`."""
    parts = version.split(".")
    if len(parts) < 2:
        raise click.ClickException(f"version {version!r} is not in major.minor.patch form.")
    return f"{parts[0]}.{parts[1]}.0"


def _resolve_component_dir(pkit_dir: Path, tier: MigrationTier, component: str) -> Path:
    """Resolve a component name to its source directory.

    Adapters live under `adapters/<component>/`; capabilities under
    `capabilities/<component>/` (per COR-017).
    """
    if tier == "adapter":
        return pkit_dir / "adapters" / component
    if tier == "capability":
        return pkit_dir / "capabilities" / component
    raise click.ClickException(f"unknown tier '{tier}'.")


def _next_migration_number(version_dir: Path) -> int:
    """Highest `NNN` in `NNN-*.sh` filenames + 1, defaulting to 1."""
    highest = 0
    for path in version_dir.glob("[0-9][0-9][0-9]-*.sh"):
        if not path.is_file():
            continue
        try:
            num = int(path.name.split("-", 1)[0], base=10)
        except ValueError:
            continue
        if num > highest:
            highest = num
    return highest + 1


def _package_yaml_for(kind: Literal["adapter"], name: str, target_root: Path) -> str:
    """Stamp a fresh `package.yaml` with `requires_backbone` matching the project's backbone."""
    requires_backbone = _default_requires_backbone(target_root)
    return _PACKAGE_YAML_TEMPLATE.format(kind=kind, name=name, requires_backbone=requires_backbone)


def _default_requires_backbone(target_root: Path) -> str:
    """Compute a sensible `requires_backbone` for a freshly scaffolded component.

    Pins the lower bound to the project's current backbone version and
    the upper bound to the next major. This matches the spirit of
    PRJ-002's auto-broadening: components scaffolded today work against
    today's backbone and forward across the same major.
    """
    backbone = read_backbone_manifest(target_root)
    if backbone is not None and backbone.backbone_version:
        version = backbone.backbone_version
    else:
        version_file = target_root / ".pkit" / "VERSION"
        if version_file.is_file():
            version = read_kit_version(target_root / ".pkit")
        else:
            # No version info to anchor against — emit a wildcard so the
            # author can fill it in.
            return "*"
    parts = version.split(".")
    if len(parts) < 3:
        return "*"
    major = int(parts[0])
    minor = int(parts[1])
    return f">={major}.{minor}.0,<{major + 1}.0.0"


def _title_case(name: str) -> str:
    """`my-area` → `My area` (for area README titles)."""
    words = name.split("-")
    if not words:
        return name
    return words[0].capitalize() + (" " + " ".join(words[1:]) if len(words) > 1 else "")


def _make_executable(path: Path) -> None:
    """Set the executable bit on a freshly stamped script."""
    mode = path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
    path.chmod(mode)
