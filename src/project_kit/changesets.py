"""Changeset parsing + component discovery for the declared, release-driven
version policy (PRJ-002 D1/D2).

A *changeset* is a small YAML file a surface-changing PR drops under
`.changes/unreleased/`. It names one component, the semver *segment* that
component's surface moved (`patch` / `minor` / `major` / `none`), and a
human-readable note. Contributors author them with `changie` — a dev-only
tool provisioned through `mise`, never bundled in the wheel and never a
runtime dependency (see `.pkit/release/README.md`). The file is equally
hand-writable, and this module — not changie — is what *reads* them at
release time. The release step (`project_kit.release`) consumes them; the
CI guard checks for the *file*, not the tool.

On-disk schema (changie-native `component` + `kind` + `body` fields, so a
plain `changie new` writes exactly what this parser reads):

    component: backbone          # `backbone`, or a component (adapter/capability) name
    kind: minor                  # the semver SEGMENT: patch | minor | major | none
    body: Add the `pkit release` command.   # the note
    category: Added              # optional Keep-a-Changelog group (see below)
    pr: 465                      # optional PR reference for the changelog link

`category` and `pr` are optional and read from either the top level (a
hand-written changeset) or a nested `custom:` map (what `changie new` writes
via the `custom:` block in `.changie.yaml`). `category` is one of the
Keep-a-Changelog groups (`Added`, `Changed`, `Fixed`, `Removed`,
`Deprecated`, `Security`); it is **orthogonal to the `kind` segment** (a
`patch` may be `Fixed` or `Changed`) and defaults at render time when absent.
It is irrelevant for `none` changesets, which move no version. `pr` is
captured at author time (release-time derivation is unreliable under
squash/rebase) and the changelog degrades gracefully when it is absent.

changie also writes a `time` field; it is ignored here. `none` is the escape
hatch — a declared "this touched a component's tree but is not a surface
change", consumed at release without moving a version.
"""

from __future__ import annotations

import re
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import click
from ruamel.yaml import YAML

# Segments in ascending precedence — a component's release segment is the
# highest across its changesets. `none` sorts lowest (declares no bump).
SEGMENTS: tuple[str, ...] = ("none", "patch", "minor", "major")
_SEGMENT_RANK = {seg: rank for rank, seg in enumerate(SEGMENTS)}

# The synthetic component name for the backbone tier (`.pkit/VERSION`), which
# has no `package.yaml`. Reserved — a real component may not take this name.
BACKBONE = "backbone"

_yaml = YAML(typ="safe")

# A filesystem-safe slug for the random-suffix filename scheme.
_SLUG_RE = re.compile(r"[^a-z0-9]+")


@dataclass(frozen=True)
class Changeset:
    """One parsed changeset file under `.changes/unreleased/`."""

    component: str
    segment: str  # one of SEGMENTS
    note: str
    path: Path
    category: str | None = None  # optional Keep-a-Changelog group; defaulted at render
    pr: str | None = None  # optional PR reference for the changelog link


@dataclass(frozen=True)
class Component:
    """A versioned tier: the backbone, or one kit-shipped adapter/capability.

    `version_path` is the file carrying the version number (the backbone's
    `VERSION`, or a component's `package.yaml`). `subtree` is the
    repo-root-relative directory whose changes count as touching this
    component's surface (`None` for the backbone, which has no single tree).
    """

    name: str
    kind: str  # "backbone" | "adapter" | "capability"
    version: str
    version_path: Path
    subtree: Path | None


def unreleased_dir(repo_root: Path) -> Path:
    """The directory changesets live in until a release consumes them."""
    return repo_root / ".changes" / "unreleased"


def segment_rank(segment: str) -> int:
    """Ascending precedence rank of a segment (`none` < `patch` < ...)."""
    try:
        return _SEGMENT_RANK[segment]
    except KeyError:
        raise click.ClickException(
            f"unknown segment {segment!r} — expected one of {', '.join(SEGMENTS)}"
        ) from None


def discover_components(source_kit: Path) -> list[Component]:
    """Discover every versioned tier under `source_kit`.

    The backbone (from `VERSION`) plus one `Component` per kit-shipped
    `package.yaml`. Deterministically ordered: backbone first, then
    components by name. `source_kit` is the `.pkit/`-equivalent directory;
    the repo root (for `subtree`) is its parent.
    """
    repo_root = source_kit.parent
    components: list[Component] = []

    version_file = source_kit / "VERSION"
    if version_file.is_file():
        components.append(
            Component(
                name=BACKBONE,
                kind="backbone",
                version=version_file.read_text(encoding="utf-8").strip(),
                version_path=version_file,
                subtree=None,
            )
        )

    discovered: list[Component] = []
    for pkg_file in source_kit.rglob("package.yaml"):
        if not pkg_file.is_file():
            continue
        data = _yaml.load(pkg_file.read_text(encoding="utf-8")) or {}
        comp = data.get("component") or {}
        if not isinstance(comp, dict):
            continue
        name = comp.get("name") or pkg_file.parent.name
        discovered.append(
            Component(
                name=str(name),
                kind=str(comp.get("kind", "capability")),
                version=str(comp.get("version", "0.0.0")),
                version_path=pkg_file,
                subtree=pkg_file.parent.relative_to(repo_root),
            )
        )

    components.extend(sorted(discovered, key=lambda c: c.name))
    return components


def parse_changeset(path: Path) -> Changeset:
    """Parse one changeset file. Raises `click.ClickException` on a bad shape."""
    data = _yaml.load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise click.ClickException(f"changeset {path.name} is not a YAML mapping")

    component = data.get("component")
    segment = data.get("kind")
    note = data.get("body", "")

    if not component:
        raise click.ClickException(f"changeset {path.name} is missing `component`")
    if segment not in _SEGMENT_RANK:
        raise click.ClickException(
            f"changeset {path.name} has kind {segment!r} — expected one of {', '.join(SEGMENTS)}"
        )

    # `category` / `pr` are optional and accepted either top-level (a
    # hand-written changeset) or under changie's nested `custom:` map. A
    # missing value is never an error — the changelog defaults the category
    # and omits the link.
    custom = data.get("custom")
    custom = custom if isinstance(custom, dict) else {}
    category = custom.get("category") or data.get("category")
    pr = custom.get("pr") or data.get("pr")

    return Changeset(
        component=str(component),
        segment=str(segment),
        note=str(note).strip(),
        path=path,
        category=str(category).strip() if category else None,
        pr=str(pr).strip() if pr else None,
    )


def load_changesets(repo_root: Path) -> list[Changeset]:
    """Parse every `*.yaml` under `.changes/unreleased/`, sorted by filename."""
    directory = unreleased_dir(repo_root)
    if not directory.is_dir():
        return []
    return [parse_changeset(p) for p in sorted(directory.glob("*.yaml"))]


def changeset_filename(component: str, segment: str, rand: str | None = None) -> str:
    """A collision-free changeset filename: `<component>-<segment>-<ts>-<rand>.yaml`.

    The random suffix (8 hex chars) is what makes parallel PRs never
    collide — two changesets for the same component+segment authored in the
    same second still land on distinct filenames. `changie`'s
    `fragmentFileFormat` mirrors this scheme (see `.changie.yaml`); this
    function is the canonical implementation used by any pkit-side authoring.
    """
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    suffix = rand or secrets.token_hex(4)
    comp_slug = _SLUG_RE.sub("-", component.lower()).strip("-") or "component"
    return f"{comp_slug}-{segment}-{stamp}-{suffix}.yaml"
