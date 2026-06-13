"""Tests for `pkit new adapter` (the Python port stamping adapter scaffolds)."""

from __future__ import annotations

from pathlib import Path

import click
import pytest

from project_kit import manifest
from project_kit.manifest import BackboneManifest, write_backbone_manifest
from project_kit.scaffolds import register_kit_shipped_component, stamp_adapter


@pytest.fixture
def kit_target(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Synthesise a minimal project tree with `.pkit/adapters/` + backbone manifest."""
    (tmp_path / ".pkit" / "adapters").mkdir(parents=True)
    write_backbone_manifest(tmp_path, BackboneManifest(backbone_version="1.0.0"))
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_stamp_adapter_creates_expected_layout(kit_target: Path) -> None:
    result = stamp_adapter(kit_target, name="claude-code")
    assert result.adapter_dir.is_dir()
    assert result.adapter_dir == kit_target / ".pkit" / "adapters" / "claude-code"
    assert result.package_yaml.is_file()
    assert result.readme.is_file()
    assert result.migrations_dir.is_dir()


def test_stamp_adapter_package_yaml_has_adapter_kind(kit_target: Path) -> None:
    result = stamp_adapter(kit_target, name="myadapter")
    text = result.package_yaml.read_text(encoding="utf-8")
    assert "kind: adapter" in text
    assert "name: myadapter" in text
    assert "version: 0.1.0" in text


def test_stamp_adapter_refuses_on_name_collision(kit_target: Path) -> None:
    stamp_adapter(kit_target, name="dupe")
    with pytest.raises(click.ClickException, match="already exists"):
        stamp_adapter(kit_target, name="dupe")


def test_stamp_adapter_refuses_invalid_slug(kit_target: Path) -> None:
    with pytest.raises(click.ClickException, match="kebab-case"):
        stamp_adapter(kit_target, name="Bad_Name")


def test_stamp_adapter_refuses_when_pkit_missing(tmp_path: Path) -> None:
    with pytest.raises(click.ClickException, match="does not exist"):
        stamp_adapter(tmp_path, name="x")


def test_stamp_adapter_refuses_when_adapters_dir_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / ".pkit").mkdir()
    monkeypatch.chdir(tmp_path)
    with pytest.raises(click.ClickException, match="adapters"):
        stamp_adapter(tmp_path, name="x")


def test_stamp_adapter_registers_in_backbone_manifest(kit_target: Path) -> None:
    stamp_adapter(kit_target, name="newadapter")
    register_kit_shipped_component(
        kit_target,
        kind="adapter",
        name="newadapter",
        manifest_path=".pkit/adapters/newadapter/project/manifest.yaml",
    )
    backbone = manifest.read_backbone_manifest(kit_target)
    assert backbone is not None
    names = [c.name for c in backbone.components if c.kind == "adapter"]
    assert "newadapter" in names
