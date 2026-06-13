"""Tests for `pkit new capability` (per COR-017)."""

from __future__ import annotations

from pathlib import Path

import click
import pytest

from project_kit.manifest import BackboneManifest, write_backbone_manifest
from project_kit.scaffolds import stamp_capability


@pytest.fixture
def kit_target(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Minimal project tree with a stamped backbone manifest."""
    (tmp_path / ".pkit").mkdir(parents=True)
    write_backbone_manifest(tmp_path, BackboneManifest(backbone_version="1.19.0"))
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_stamp_capability_creates_expected_layout(kit_target: Path) -> None:
    """Every COR-017 subdirectory is created with a .gitkeep so git tracks it."""
    result = stamp_capability(kit_target, name="evidence")
    assert result.capability_dir == kit_target / ".pkit" / "capabilities" / "evidence"
    assert result.capability_dir.is_dir()
    assert result.package_yaml.is_file()
    assert result.readme.is_file()
    for sub in (
        result.decisions_dir,
        result.skills_dir,
        result.agents_dir,
        result.scripts_dir,
        result.schemas_dir,
        result.migrations_dir,
    ):
        assert sub.is_dir()
        assert (sub / ".gitkeep").is_file()


def test_stamp_capability_creates_migrations_subdir(kit_target: Path) -> None:
    """Per COR-010, capabilities ship a migrations/ directory so version bumps can bridge state."""
    result = stamp_capability(kit_target, name="evidence")
    assert result.migrations_dir == kit_target / ".pkit" / "capabilities" / "evidence" / "migrations"
    assert result.migrations_dir.is_dir()
    assert (result.migrations_dir / ".gitkeep").is_file()


def test_stamp_capability_package_yaml_carries_capability_kind(kit_target: Path) -> None:
    result = stamp_capability(kit_target, name="evidence")
    text = result.package_yaml.read_text(encoding="utf-8")
    assert "kind: capability" in text
    assert "name: evidence" in text
    assert "version: 0.1.0" in text
    # requires_backbone reflects the project's backbone (>=1.19.0,<2.0.0).
    assert ">=1.19.0" in text
    assert "<2.0.0" in text


def test_stamp_capability_readme_mentions_citation_form(kit_target: Path) -> None:
    """The stamped README documents the [<cap>:DEC-NNN] citation form per COR-017."""
    result = stamp_capability(kit_target, name="evidence")
    text = result.readme.read_text(encoding="utf-8")
    assert "[evidence:DEC-001-" in text


def test_stamp_capability_refuses_on_name_collision(kit_target: Path) -> None:
    stamp_capability(kit_target, name="dupe")
    with pytest.raises(click.ClickException, match="already exists"):
        stamp_capability(kit_target, name="dupe")


def test_stamp_capability_refuses_invalid_slug(kit_target: Path) -> None:
    with pytest.raises(click.ClickException, match="kebab-case"):
        stamp_capability(kit_target, name="Bad_Name")


def test_stamp_capability_refuses_when_pkit_missing(tmp_path: Path) -> None:
    with pytest.raises(click.ClickException, match="does not exist"):
        stamp_capability(tmp_path, name="x")


def test_stamp_capability_creates_capabilities_dir_if_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Unlike bundle/adapter, capabilities dir is auto-created on first stamp.

    The bundle/adapter scaffolds require the containing area dir to exist
    (it's part of the kit's initial layout). Capabilities can ship at
    install time, so the `.pkit/capabilities/` subtree is created on
    demand when the first capability is stamped.
    """
    (tmp_path / ".pkit").mkdir()
    monkeypatch.chdir(tmp_path)
    write_backbone_manifest(tmp_path, BackboneManifest(backbone_version="1.19.0"))

    result = stamp_capability(tmp_path, name="evidence")
    assert result.capability_dir.is_dir()
    assert (tmp_path / ".pkit" / "capabilities").is_dir()


def test_stamp_capability_does_not_register_in_backbone_manifest(kit_target: Path) -> None:
    """Capabilities are kit-shipped; adopters register them at install time, not at scaffold time."""
    from project_kit import manifest as manifest_mod

    stamp_capability(kit_target, name="evidence")
    backbone = manifest_mod.read_backbone_manifest(kit_target)
    assert backbone is not None
    names_of_capability_kind = [
        c.name for c in backbone.components if c.kind == "capability"
    ]
    assert "evidence" not in names_of_capability_kind
