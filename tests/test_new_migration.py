"""Tests for `pkit new migration` (the Python port stamping migration scripts)."""

from __future__ import annotations

import os
from pathlib import Path

import click
import pytest

from project_kit.manifest import BackboneManifest, write_backbone_manifest
from project_kit.scaffolds import stamp_migration


@pytest.fixture
def kit_target(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Synthesise a minimal kit tree with backbone + an adapter + a capability."""
    pkit = tmp_path / ".pkit"
    pkit.mkdir()
    (pkit / "VERSION").write_text("1.0.0\n", encoding="utf-8")

    # Adapter: adapters/sample/
    adapter = pkit / "adapters" / "sample"
    adapter.mkdir(parents=True)
    (adapter / "package.yaml").write_text(
        "schema_version: 1\ncomponent:\n  kind: adapter\n  name: sample\n  version: 0.5.0\n"
        'requires_backbone: ">=1.0.0,<2.0.0"\n',
        encoding="utf-8",
    )

    # Capability: capabilities/evidence/
    capability = pkit / "capabilities" / "evidence"
    capability.mkdir(parents=True)
    (capability / "package.yaml").write_text(
        "schema_version: 1\ncomponent:\n  kind: capability\n  name: evidence\n  version: 0.2.0\n"
        'requires_backbone: ">=1.0.0,<2.0.0"\n',
        encoding="utf-8",
    )

    write_backbone_manifest(tmp_path, BackboneManifest(backbone_version="1.0.0"))
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_stamp_migration_backbone_uses_pkit_version(kit_target: Path) -> None:
    result = stamp_migration(
        kit_target,
        tier="backbone",
        version=None,
        slug="my-change",
    )
    expected = kit_target / ".pkit" / "migrations" / "backbone" / "1.0.0" / "001-my-change.sh"
    assert result.script == expected
    assert result.script.is_file()
    text = result.script.read_text(encoding="utf-8")
    assert "set -euo pipefail" in text
    assert "ROOT" in text
    assert "Backbone migration 1.0.0" in text


def test_stamp_migration_script_is_executable(kit_target: Path) -> None:
    result = stamp_migration(kit_target, tier="backbone", version=None, slug="exec-check")
    mode = result.script.stat().st_mode
    assert mode & os.X_OK


def test_stamp_migration_picks_next_number(kit_target: Path) -> None:
    stamp_migration(kit_target, tier="backbone", version="1.0.0", slug="one")
    stamp_migration(kit_target, tier="backbone", version="1.0.0", slug="two")
    result = stamp_migration(kit_target, tier="backbone", version="1.0.0", slug="three")
    assert result.script.name == "003-three.sh"


def test_stamp_migration_adapter_resolves_component_version(kit_target: Path) -> None:
    result = stamp_migration(
        kit_target,
        tier="adapter",
        component="sample",
        version=None,
        slug="tweak-settings",
    )
    expected = (
        kit_target
        / ".pkit"
        / "adapters"
        / "sample"
        / "migrations"
        / "0.5.0"
        / "001-tweak-settings.sh"
    )
    assert result.script == expected


def test_stamp_migration_capability_resolves_component_version(kit_target: Path) -> None:
    """Per COR-017 capability tier: migration lands under capabilities/<name>/migrations/<X.Y.0>/."""
    result = stamp_migration(
        kit_target,
        tier="capability",
        component="evidence",
        version=None,
        slug="bump-schema",
    )
    expected = (
        kit_target
        / ".pkit"
        / "capabilities"
        / "evidence"
        / "migrations"
        / "0.2.0"
        / "001-bump-schema.sh"
    )
    assert result.script == expected
    text = result.script.read_text(encoding="utf-8")
    assert "evidence 0.2.0" in text


def test_stamp_migration_capability_requires_component(kit_target: Path) -> None:
    with pytest.raises(click.ClickException, match="--component"):
        stamp_migration(kit_target, tier="capability", version="0.2.0", slug="x")


def test_stamp_migration_capability_refuses_unknown_component(kit_target: Path) -> None:
    with pytest.raises(click.ClickException, match="capability"):
        stamp_migration(
            kit_target, tier="capability", component="ghost", version="0.2.0", slug="x"
        )


def test_stamp_migration_refuses_invalid_version(kit_target: Path) -> None:
    with pytest.raises(click.ClickException, match=r"X\.Y\.0"):
        stamp_migration(kit_target, tier="backbone", version="1.0.3", slug="bad-version")


def test_stamp_migration_refuses_missing_slug(kit_target: Path) -> None:
    with pytest.raises(click.ClickException, match="--name"):
        stamp_migration(kit_target, tier="backbone", version="1.0.0", slug=None)


def test_stamp_migration_refuses_invalid_slug(kit_target: Path) -> None:
    with pytest.raises(click.ClickException, match="kebab-case"):
        stamp_migration(kit_target, tier="backbone", version="1.0.0", slug="Bad_Slug")


def test_stamp_migration_adapter_requires_component(kit_target: Path) -> None:
    with pytest.raises(click.ClickException, match="--component"):
        stamp_migration(kit_target, tier="adapter", version="1.0.0", slug="x")


def test_stamp_migration_backbone_refuses_component(kit_target: Path) -> None:
    with pytest.raises(click.ClickException, match="--component"):
        stamp_migration(
            kit_target,
            tier="backbone",
            component="sample",
            version="1.0.0",
            slug="x",
        )


def test_stamp_migration_refuses_unknown_adapter(kit_target: Path) -> None:
    with pytest.raises(click.ClickException, match="not found"):
        stamp_migration(
            kit_target,
            tier="adapter",
            component="ghost-adapter",
            version="1.0.0",
            slug="x",
        )


def test_stamp_migration_explicit_version_overrides_package_yaml(kit_target: Path) -> None:
    result = stamp_migration(
        kit_target,
        tier="adapter",
        component="sample",
        version="2.5.0",
        slug="future-change",
    )
    assert "2.5.0" in str(result.script)


def test_stamp_migration_includes_scope_in_comment(kit_target: Path) -> None:
    result = stamp_migration(
        kit_target,
        tier="backbone",
        version="1.0.0",
        slug="struct-change",
        scope="structural",
    )
    text = result.script.read_text(encoding="utf-8")
    assert "structural" in text
