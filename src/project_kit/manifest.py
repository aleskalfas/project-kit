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

import datetime as _dt
import io
import re
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Literal, cast

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap

ComponentKind = Literal["adapter", "capability"]

# Capability origin (COR-031): where a capability came from, recorded in
# lifecycle-owned install-state (the backbone manifest's component registry),
# never inside the capability's own subtree. Two origins today; an absent
# origin on read means `kit-shipped` so existing registrations are unchanged
# (additive, no migration — COR-031 D2).
ORIGIN_KIT_SHIPPED = "kit-shipped"
ORIGIN_INCUBATED_IN_REPO = "incubated-in-repo"
# COR-041's third origin: content pulled whole from an external source at a
# pin and restored to it by reconciliation. Its fetch is not built yet; the
# wire value is named so a reader can tell an entry carrying it apart.
ORIGIN_EXTERNALLY_SOURCED = "externally-sourced"

# A per-component manifest's file name, in its component's `project/`.
COMPONENT_MANIFEST_NAME = "manifest.yaml"

# The backbone manifest's two recorded states (ADR-065 point 3). Both stay
# top-level scalars in every schema version, so a pkit that reads only
# `backbone_version` still finds the target.
BACKBONE_VERSION_KEY = "backbone_version"
COMPLETED_VERSION_KEY = "completed_version"


# Singleton YAML instance: round-trip mode preserves comments and key
# ordering when re-serialising. `default_flow_style = False` forces
# block style, matching the lifecycle README's worked example.
_yaml = YAML(typ="rt")
_yaml.default_flow_style = False
_yaml.indent(mapping=2, sequence=4, offset=2)


def _yaml_load(text: str) -> Any:
    """Typed wrapper around ruamel.yaml's untyped load."""
    return _yaml.load(text)


def _yaml_dump(data: Any, stream: io.IOBase) -> None:
    """Typed wrapper around ruamel.yaml's untyped dump."""
    _yaml.dump(data, stream)


@dataclass(frozen=True)
class ComponentRegistryEntry:
    """One component listed in the backbone manifest's `components` registry.

    ``origin`` (COR-031) records where a capability came from —
    ``kit-shipped`` (copied from kit source on install) or
    ``incubated-in-repo`` (authored in, and lives in, the adopter's own
    repo). It is meaningful only for capabilities; adapters are always
    kit-shipped. An absent origin on read defaults to ``kit-shipped``
    (the field is omitted from serialization when it holds that default),
    so existing registrations are unchanged and the change needs no
    migration.
    """

    kind: ComponentKind
    name: str
    manifest: str  # relative path from repo root to the per-component manifest
    origin: str = ORIGIN_KIT_SHIPPED


@dataclass
class BackboneManifest:
    """Adopter-side `.pkit/manifest.yaml`.

    Tracks the backbone's two recorded states and the components registry
    (ADR-065 points 2 and 3):

    - `backbone_version`: the release whose content the project holds, or the
      target of a transition not yet complete. A transition writes it first.
    - `completed_version`: the last release a transition of the backbone
      completed. A transition writes it last. `None` when the key is missing,
      which reads as incomplete with no lower bound: the project's backbone
      migration history is unknown.
    """

    backbone_version: str
    components: list[ComponentRegistryEntry] = field(default_factory=lambda: [])
    schema_version: int = 1
    completed_version: str | None = None

    @property
    def transition_incomplete(self) -> bool:
        """True unless the two recorded states name the same version (COR-059 point 6).

        A missing `completed_version`, one behind `backbone_version` (an
        interrupted transition) and one ahead of it (an older pkit's sync over a
        finished transition) all read as incomplete.
        """
        return self.completed_version is None or self.completed_version != self.backbone_version


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
            # Absent origin ⇒ kit-shipped (COR-031 D2): existing
            # registrations carry no origin and must read unchanged.
            origin=str(entry.get("origin", ORIGIN_KIT_SHIPPED)),
        )
        for entry in components_raw
    ]
    completed = raw.get(COMPLETED_VERSION_KEY)
    return BackboneManifest(
        backbone_version=str(raw.get(BACKBONE_VERSION_KEY, "") or ""),
        components=components,
        schema_version=int(raw.get("schema_version", 1)),
        # An empty value is no recorded completion.
        completed_version=str(completed) if completed not in (None, "") else None,
    )


def _state_line(key: str) -> re.Pattern[str]:
    """The pattern of one recorded state's line: the key at column 0, its value."""
    return re.compile(rf"(?m)^({re.escape(key)}:[ \t]*)(\S*)")


BACKBONE_VERSION_LINE_RE = _state_line(BACKBONE_VERSION_KEY)
COMPLETED_VERSION_LINE_RE = _state_line(COMPLETED_VERSION_KEY)


def set_state_line(text: str, key: str, version: str, *, after: str | None = None) -> str:
    """*text* with the top-level *key*'s line set to *version*, every other byte kept.

    The value of an existing line is replaced in place. A missing line is added
    after the line of the key *after*, or at the end of the text when *after* is
    None or has no line. Neither a comment nor the order of the other keys
    moves, since nothing is re-serialised (ADR-065 point 3).
    """
    pattern = _state_line(key)
    match = pattern.search(text)
    if match is not None:
        return f"{text[: match.start(2)]}{version}{text[match.end(2) :]}"
    line = f"{key}: {version}\n"
    anchor = _state_line(after).search(text) if after is not None else None
    if anchor is not None:
        end = text.find("\n", anchor.end())
        if end != -1:
            return text[: end + 1] + line + text[end + 1 :]
    if text and not text.endswith("\n"):
        text += "\n"
    return text + line


def record_backbone_target(target_root: Path, version: str) -> Path:
    """Record *version* as the backbone's target, `backbone_version`, by an
    in-place edit of its own line (ADR-065 point 3).

    The first write of a transition. `completed_version` keeps its value or
    stays missing. Where the project has no manifest, it is written at
    *version*, with no component registered and no completion recorded, as
    first install writes it before it copies anything.
    """
    path = _backbone_manifest_path(target_root)
    if not path.is_file():
        return write_backbone_manifest(target_root, BackboneManifest(backbone_version=version))
    text = path.read_text(encoding="utf-8")
    updated = set_state_line(text, BACKBONE_VERSION_KEY, version, after="schema_version")
    if updated != text:
        path.write_text(updated, encoding="utf-8")
    return path


def record_completed_version(target_root: Path, version: str) -> Path:
    """Record *version* as the backbone's completion, `completed_version`, by an
    in-place edit of its own line (ADR-065 point 3).

    The last write of a transition, and of first install. A manifest with no
    such line gains one right after its `backbone_version` line.
    """
    path = _backbone_manifest_path(target_root)
    text = path.read_text(encoding="utf-8")
    updated = set_state_line(text, COMPLETED_VERSION_KEY, version, after=BACKBONE_VERSION_KEY)
    if updated != text:
        path.write_text(updated, encoding="utf-8")
    return path


def write_backbone_manifest(target_root: Path, manifest: BackboneManifest) -> Path:
    """Write `.pkit/manifest.yaml`. Round-trip-preserves comments if the file already exists.

    An existing file keeps every key this writer does not set, so a key a later
    release adds survives an older writer. `completed_version` is never written
    here: only its own in-place edit writes it (`record_completed_version`), so
    a registry write from a manifest read earlier cannot move it.
    """
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


def read_capability_origin(target_root: Path, name: str) -> str:
    """Return a registered capability's origin from lifecycle-owned install-state.

    Reads the backbone manifest's component registry (COR-031 D2 — origin
    lives here, never inside the capability's adopter-owned subtree). An
    entry with no origin reads as ``kit-shipped`` (the default baked into
    ``ComponentRegistryEntry``), so existing registrations are unchanged.

    Returns ``kit-shipped`` when the capability is not registered (or no
    manifest exists): a single, safe default keeps callers from scattering
    the absent-origin fallback. Callers that need to distinguish "not
    installed" from "installed kit-shipped" should consult ``is_installed``
    first.
    """
    backbone = read_backbone_manifest(target_root)
    if backbone is None:
        return ORIGIN_KIT_SHIPPED
    for entry in backbone.components:
        if entry.kind == "capability" and entry.name == name:
            return entry.origin
    return ORIGIN_KIT_SHIPPED


def set_capability_origin(target_root: Path, name: str, origin: str) -> bool:
    """Set a registered capability's ``origin`` on its existing registry entry.

    An origin-state upgrade in place (COR-031 D2 — origin is lifecycle-owned
    install-state on the backbone manifest's component registry, recorded
    outside the capability's own subtree). Rewrites only the origin field of
    the existing ``kind: capability`` entry; the subtree is untouched. This is
    the supported path for adopting a manually-registered capability (one
    added with origin unset, which reads back as ``kit-shipped``) as
    ``incubated-in-repo`` so ``pkit sync`` leaves it untouched.

    Returns ``True`` when the entry was found and its origin changed (or was
    written afresh), ``False`` when no matching registry entry exists or the
    origin already held the requested value (nothing to write).
    """
    backbone = read_backbone_manifest(target_root)
    if backbone is None:
        return False
    changed = False
    new_components: list[ComponentRegistryEntry] = []
    for entry in backbone.components:
        if entry.kind == "capability" and entry.name == name:
            if entry.origin == origin:
                return False
            new_components.append(replace(entry, origin=origin))
            changed = True
        else:
            new_components.append(entry)
    if not changed:
        return False
    backbone.components = new_components
    write_backbone_manifest(target_root, backbone)
    return True


def set_component_manifest_path(
    target_root: Path, kind: ComponentKind, name: str, manifest: str
) -> bool:
    """Point a registered component's registry entry at *manifest*, a repo-relative path.

    Rewrites only the entry's ``manifest`` field. Returns ``True`` when the entry
    was found and its path changed, ``False`` when no such entry is registered or
    it already names *manifest* (nothing to write).
    """
    backbone = read_backbone_manifest(target_root)
    if backbone is None:
        return False
    changed = False
    new_components: list[ComponentRegistryEntry] = []
    for entry in backbone.components:
        if entry.kind == kind and entry.name == name and entry.manifest != manifest:
            new_components.append(replace(entry, manifest=manifest))
            changed = True
        else:
            new_components.append(entry)
    if not changed:
        return False
    backbone.components = new_components
    write_backbone_manifest(target_root, backbone)
    return True


def adapter_manifest_rel(name: str) -> str:
    """The repo-relative path of an adapter's manifest, under its ``project/``.

    The path first install and a version transition write when they record the
    adapter's version, and the one its registry entry names (ADR-065 point 2).
    """
    return f".pkit/adapters/{name}/project/{COMPONENT_MANIFEST_NAME}"


def read_component_package(package_yaml: Path) -> tuple[str, str] | None:
    """A component's ``package.yaml``: its version and its ``requires_backbone``
    range, the range empty when it declares none. None when the file is missing,
    does not parse, or names no version."""
    if not package_yaml.is_file():
        return None
    try:
        raw: Any = _yaml_load(package_yaml.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(raw, dict):
        return None
    data = cast(dict[str, Any], raw)
    component = data.get("component")
    version = (
        cast(dict[str, Any], component).get("version") if isinstance(component, dict) else None
    )
    if not isinstance(version, str) or not version:
        return None
    requires = data.get("requires_backbone")
    return version, str(requires) if requires is not None else ""


def record_adapter_version(target_root: Path, name: str, package_yaml: Path) -> str | None:
    """Record adapter *name* at the version its *package_yaml* ships (ADR-065 point 2).

    Writes the adapter's manifest under its ``project/``, keeping any
    ``backend_state`` one already there holds. Returns the version recorded, or
    None when *package_yaml* names none, and then writes nothing.
    """
    package = read_component_package(package_yaml)
    if package is None:
        return None
    version, requires_backbone = package
    path = target_root / adapter_manifest_rel(name)
    prior = read_component_manifest(path) if path.is_file() else None
    write_component_manifest(
        path,
        ComponentManifest(
            kind="adapter",
            name=name,
            version=version,
            installed_at=_dt.datetime.now(_dt.UTC).isoformat(),
            requires_backbone=requires_backbone,
            backend_state=prior.backend_state if prior is not None else {},
        ),
    )
    return version


def capability_manifest_rel(name: str) -> str:
    """The repo-relative path of a capability's manifest, under its ``project/``.

    The path a capability's install and a version transition write, and the one
    its registry entry names (ADR-065 point 2).
    """
    return f".pkit/capabilities/{name}/project/{COMPONENT_MANIFEST_NAME}"


def capability_manifest_path(target_root: Path, name: str) -> Path:
    """A capability's manifest under its ``project/``, where no copy touches it."""
    return target_root / capability_manifest_rel(name)


def capability_root_manifest_path(target_root: Path, name: str) -> Path:
    """Where a capability's manifest was written before it moved under ``project/``.

    The capability's root, a position every copy of its tree manages: a refresh
    deletes or overwrites a file there. A manifest found there moves under
    ``project/`` the next time the record is written
    (``capabilities.move_capability_manifest``).
    """
    return target_root / ".pkit" / "capabilities" / name / COMPONENT_MANIFEST_NAME


def recorded_capability_manifest(target_root: Path, name: str) -> Path | None:
    """The capability manifest a reader of its record reads, or None (ADR-065 point 2).

    The manifest at the capability's root where one exists, else the one under
    its ``project/``. Both exist only after an interrupted move, or after a write
    that does not know the move, such as an older pkit's restamp or a rollback of
    ``.pkit/``. Either way the root one names the content the project holds, so
    it wins. A reader that finds neither falls back to the capability's installed
    ``package.yaml``.
    """
    for path in (
        capability_root_manifest_path(target_root, name),
        capability_manifest_path(target_root, name),
    ):
        if path.is_file():
            return path
    return None


def _backbone_manifest_path(target_root: Path) -> Path:
    return target_root / ".pkit" / "manifest.yaml"


def _entry_to_map(entry: ComponentRegistryEntry) -> CommentedMap:
    out = CommentedMap()
    out["kind"] = entry.kind
    out["name"] = entry.name
    out["manifest"] = entry.manifest
    # Omit origin when it holds the default (kit-shipped): the field is
    # additive (COR-031 D2), so an absent origin reads back as kit-shipped.
    # Writing it only for the non-default keeps adapter entries and existing
    # capability entries byte-identical to before this field landed.
    if entry.origin != ORIGIN_KIT_SHIPPED:
        out["origin"] = entry.origin
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

    A capability's manifest written before it moved there sits at the
    capability's root, `.pkit/capabilities/<name>/manifest.yaml`, until its
    record is next written (`recorded_capability_manifest`,
    `capabilities.move_capability_manifest`).
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
