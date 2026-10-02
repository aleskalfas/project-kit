"""Tests for `pkit new adapter` (the Python port stamping adapter scaffolds)."""

from __future__ import annotations

from pathlib import Path

import click
import pytest
from click.testing import CliRunner

from project_kit import manifest
from project_kit.cli import main
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


# --- reserved names (#1300) ----------------------------------------
#
# `backbone` is the name the backbone's changesets and validators are read under,
# and both read adapters as well as capabilities, so an adapter named `backbone`
# would have its own read as the backbone's. The names reserved for capabilities
# alone collide only where a capability's name is read, and stay free here.

ADAPTER_RESERVED = [
    ("backbone", "the component of the backbone's changesets and the owner of its validators"),
]


@pytest.mark.parametrize(("name", "reason"), ADAPTER_RESERVED)
def test_stamp_adapter_refuses_a_reserved_name(kit_target: Path, name: str, reason: str) -> None:
    """A reserved name is refused with its reason, and nothing is written."""
    with pytest.raises(click.ClickException, match=f"adapter name '{name}' is reserved") as refused:
        stamp_adapter(kit_target, name=name)
    assert reason in refused.value.message
    assert not (kit_target / ".pkit" / "adapters" / name).exists()


@pytest.mark.parametrize(("name", "reason"), ADAPTER_RESERVED)
def test_register_kit_shipped_component_refuses_a_reserved_name(
    kit_target: Path, name: str, reason: str
) -> None:
    with pytest.raises(click.ClickException, match=f"adapter name '{name}' is reserved") as refused:
        register_kit_shipped_component(
            kit_target,
            kind="adapter",
            name=name,
            manifest_path=f".pkit/adapters/{name}/project/manifest.yaml",
        )
    assert reason in refused.value.message
    backbone = manifest.read_backbone_manifest(kit_target)
    assert backbone is not None
    assert [c.name for c in backbone.components] == []


@pytest.mark.parametrize(("name", "reason"), ADAPTER_RESERVED)
def test_cli_new_adapter_refuses_a_reserved_name(kit_target: Path, name: str, reason: str) -> None:
    result = CliRunner().invoke(main, ["new", "adapter", name])
    assert result.exit_code != 0
    output = " ".join(result.output.split())
    assert f"adapter name '{name}' is reserved" in output
    assert reason in output
    assert not (kit_target / ".pkit" / "adapters" / name).exists()
    backbone = manifest.read_backbone_manifest(kit_target)
    assert backbone is not None
    assert [c.name for c in backbone.components] == []


@pytest.mark.parametrize("name", ["core", "project", "adr"])
def test_cli_new_adapter_takes_a_name_reserved_for_capabilities_alone(
    kit_target: Path, name: str
) -> None:
    """`core`, `project` and `adr` name decision, agent and schema namespaces, and an
    evidence point's checks — places a capability's name is read and an adapter's
    never is — so an adapter may take them."""
    result = CliRunner().invoke(main, ["new", "adapter", name])
    assert result.exit_code == 0, result.output
    assert (kit_target / ".pkit" / "adapters" / name / "package.yaml").is_file()
    backbone = manifest.read_backbone_manifest(kit_target)
    assert backbone is not None
    assert [c.name for c in backbone.components if c.kind == "adapter"] == [name]
