"""Tests for the manifest read/write layer (per COR-010 + PR-G of the build roadmap)."""

from __future__ import annotations

from pathlib import Path

from project_kit.manifest import (
    BackboneManifest,
    ComponentRegistryEntry,
    read_backbone_manifest,
    write_backbone_manifest,
)


def test_read_returns_none_when_manifest_absent(tmp_path: Path) -> None:
    assert read_backbone_manifest(tmp_path) is None


def test_write_then_read_roundtrips_minimal_manifest(tmp_path: Path) -> None:
    (tmp_path / ".pkit").mkdir()
    write_backbone_manifest(tmp_path, BackboneManifest(backbone_version="0.9.0"))
    loaded = read_backbone_manifest(tmp_path)
    assert loaded is not None
    assert loaded.backbone_version == "0.9.0"
    assert loaded.schema_version == 1
    assert loaded.components == []


def test_write_then_read_roundtrips_with_components(tmp_path: Path) -> None:
    (tmp_path / ".pkit").mkdir()
    manifest = BackboneManifest(
        backbone_version="0.9.0",
        components=[
            ComponentRegistryEntry(
                kind="capability",
                name="evidence",
                manifest=".pkit/capabilities/evidence/manifest.yaml",
            ),
            ComponentRegistryEntry(
                kind="adapter",
                name="claude-code",
                manifest=".pkit/adapters/claude-code/project/manifest.yaml",
            ),
        ],
    )
    write_backbone_manifest(tmp_path, manifest)
    loaded = read_backbone_manifest(tmp_path)

    assert loaded is not None
    assert loaded.backbone_version == "0.9.0"
    assert len(loaded.components) == 2
    assert loaded.components[0].kind == "capability"
    assert loaded.components[0].name == "evidence"
    assert loaded.components[1].kind == "adapter"
    assert loaded.components[1].name == "claude-code"


def test_write_preserves_existing_comments(tmp_path: Path) -> None:
    """ruamel.yaml round-trip mode keeps comments through write+read."""
    (tmp_path / ".pkit").mkdir()
    path = tmp_path / ".pkit" / "manifest.yaml"
    path.write_text(
        "# Backbone manifest — adopter-managed.\n"
        "schema_version: 1\n"
        "backbone_version: 0.5.0\n"
        "components: []\n",
        encoding="utf-8",
    )

    write_backbone_manifest(tmp_path, BackboneManifest(backbone_version="0.6.0"))

    contents = path.read_text(encoding="utf-8")
    assert "# Backbone manifest — adopter-managed." in contents
    assert "backbone_version: 0.6.0" in contents


def test_write_uses_block_style_not_flow_style(tmp_path: Path) -> None:
    (tmp_path / ".pkit").mkdir()
    write_backbone_manifest(
        tmp_path,
        BackboneManifest(
            backbone_version="0.9.0",
            components=[
                ComponentRegistryEntry(
                    kind="capability",
                    name="evidence",
                    manifest=".pkit/capabilities/evidence/manifest.yaml",
                )
            ],
        ),
    )

    contents = (tmp_path / ".pkit" / "manifest.yaml").read_text(encoding="utf-8")
    # Block style: sequences use `- ` prefix on their own lines, not `[...]`.
    assert "  - kind: capability" in contents
    assert "[" not in contents.splitlines()[3]  # the components line itself isn't flow-style
