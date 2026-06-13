"""Manifest read/write helpers for the lifecycle layer (per COR-010).

Two manifest forms today:

- **Backbone manifest** at `.pkit/manifest.yaml` — adopter-side. Records
  the backbone version installed and a registry of installed components.
- **Per-component manifest** at `<component-project-side>/manifest.yaml`
  — one per installed adapter / capability. Records the component's
  version, install timestamp, `requires_backbone` range, and any opaque
  backend IDs (`backend_state`).

Round-trip-safe via `ruamel.yaml`: comments and key order are preserved
when an existing manifest is updated. New manifests are written with
explicit ordering matching the lifecycle README's worked example.
"""

from __future__ import annotations

import io
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, cast

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap

ComponentKind = Literal["adapter", "capability"]


# Singleton YAML instance: round-trip mode preserves comments and key
# ordering when re-serialising. `default_flow_style = False` forces
# block style, matching the lifecycle README's worked example.
_yaml = YAML(typ="rt")
_yaml.default_flow_style = False
_yaml.indent(mapping=2, sequence=4, offset=2)


def _yaml_load(text: str) -> Any:
    """Typed wrapper around ruamel.yaml's untyped load."""
    return _yaml.load(text)  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]


def _yaml_dump(data: Any, stream: io.IOBase) -> None:
    """Typed wrapper around ruamel.yaml's untyped dump."""
    _yaml.dump(data, stream)  # pyright: ignore[reportUnknownMemberType]


@dataclass(frozen=True)
class ComponentRegistryEntry:
    """One component listed in the backbone manifest's `components` registry."""

    kind: ComponentKind
    name: str
    manifest: str  # relative path from repo root to the per-component manifest


@dataclass
class BackboneManifest:
    """Adopter-side `.pkit/manifest.yaml`.

    Tracks recorded backbone version + components registry.
    """

    backbone_version: str
    components: list[ComponentRegistryEntry] = field(default_factory=lambda: [])
    schema_version: int = 1


def read_backbone_manifest(target_root: Path) -> BackboneManifest | None:
    """Read `.pkit/manifest.yaml` if present; return None otherwise."""
    path = _backbone_manifest_path(target_root)
    if not path.is_file():
        return None
    raw_loaded = _yaml_load(path.read_text(encoding="utf-8"))
    raw: dict[str, Any] = cast(dict[str, Any], raw_loaded) if raw_loaded is not None else {}
    components_raw = cast(list[dict[str, Any]], raw.get("components") or [])
    components = [
        ComponentRegistryEntry(
            kind=cast(ComponentKind, entry["kind"]),
            name=str(entry["name"]),
            manifest=str(entry["manifest"]),
        )
        for entry in components_raw
    ]
    return BackboneManifest(
        backbone_version=str(raw.get("backbone_version", "")),
        components=components,
        schema_version=int(raw.get("schema_version", 1)),
    )


def write_backbone_manifest(target_root: Path, manifest: BackboneManifest) -> Path:
    """Write `.pkit/manifest.yaml`. Round-trip-preserves comments if the file already exists."""
    path = _backbone_manifest_path(target_root)
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.is_file():
        # Update in place: preserve comments and unrecognised keys.
        existing = cast(
            CommentedMap, _yaml_load(path.read_text(encoding="utf-8")) or CommentedMap()
        )
        existing["schema_version"] = manifest.schema_version
        existing["backbone_version"] = manifest.backbone_version
        existing["components"] = [_entry_to_map(e) for e in manifest.components]
        with path.open("w", encoding="utf-8") as f:
            _yaml_dump(existing, f)
    else:
        # Fresh write: explicit key order matching the lifecycle README example.
        doc = CommentedMap()
        doc["schema_version"] = manifest.schema_version
        doc["backbone_version"] = manifest.backbone_version
        doc["components"] = [_entry_to_map(e) for e in manifest.components]
        with path.open("w", encoding="utf-8") as f:
            _yaml_dump(doc, f)

    return path


def _backbone_manifest_path(target_root: Path) -> Path:
    return target_root / ".pkit" / "manifest.yaml"


def _entry_to_map(entry: ComponentRegistryEntry) -> CommentedMap:
    out = CommentedMap()
    out["kind"] = entry.kind
    out["name"] = entry.name
    out["manifest"] = entry.manifest
    return out


def read_kit_version(source_kit: Path) -> str:
    """Read the source kit's `.pkit/VERSION` file."""
    version_file = source_kit / "VERSION"
    return version_file.read_text(encoding="utf-8").strip()


@dataclass
class ComponentManifest:
    """Adopter-side per-component manifest.

    Lives at the component's project-side path (e.g.,
    `.pkit/adapters/<name>/project/manifest.yaml`,
    `.pkit/capabilities/<name>/project/manifest.yaml`). Records what was
    installed: version, install timestamp, recorded `requires_backbone`,
    and any opaque backend identifiers the kit cannot rederive.
    """

    kind: ComponentKind
    name: str
    version: str
    installed_at: str  # ISO 8601
    requires_backbone: str
    backend_state: dict[str, Any] = field(default_factory=lambda: {})
    schema_version: int = 1


def read_component_manifest(path: Path) -> ComponentManifest | None:
    """Read a per-component `manifest.yaml` if present."""
    if not path.is_file():
        return None
    raw_loaded = _yaml_load(path.read_text(encoding="utf-8"))
    raw: dict[str, Any] = cast(dict[str, Any], raw_loaded) if raw_loaded is not None else {}
    component = cast(dict[str, Any], raw.get("component") or {})
    return ComponentManifest(
        kind=cast(ComponentKind, component.get("kind", "adapter")),
        name=str(component.get("name", "")),
        version=str(component.get("version", "")),
        installed_at=str(component.get("installed_at", "")),
        requires_backbone=str(raw.get("requires_backbone", "")),
        backend_state=cast(dict[str, Any], raw.get("backend_state") or {}),
        schema_version=int(raw.get("schema_version", 1)),
    )


def write_component_manifest(path: Path, manifest: ComponentManifest) -> Path:
    """Write a per-component `manifest.yaml`. Round-trip-preserves comments on update."""
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.is_file():
        existing = cast(
            CommentedMap, _yaml_load(path.read_text(encoding="utf-8")) or CommentedMap()
        )
        existing["schema_version"] = manifest.schema_version
        component_map = CommentedMap()
        component_map["kind"] = manifest.kind
        component_map["name"] = manifest.name
        component_map["version"] = manifest.version
        component_map["installed_at"] = manifest.installed_at
        existing["component"] = component_map
        existing["requires_backbone"] = manifest.requires_backbone
        existing["backend_state"] = manifest.backend_state
        with path.open("w", encoding="utf-8") as f:
            _yaml_dump(existing, f)
    else:
        doc = CommentedMap()
        doc["schema_version"] = manifest.schema_version
        component_map = CommentedMap()
        component_map["kind"] = manifest.kind
        component_map["name"] = manifest.name
        component_map["version"] = manifest.version
        component_map["installed_at"] = manifest.installed_at
        doc["component"] = component_map
        doc["requires_backbone"] = manifest.requires_backbone
        doc["backend_state"] = manifest.backend_state
        with path.open("w", encoding="utf-8") as f:
            _yaml_dump(doc, f)

    return path
