"""Tests for `pkit new capability` (per COR-017)."""

from __future__ import annotations

from pathlib import Path

import click
import pytest
from click.testing import CliRunner

from project_kit.cli import main
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
    assert (
        result.migrations_dir == kit_target / ".pkit" / "capabilities" / "evidence" / "migrations"
    )
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


# Each reserved name, with a phrase of the reason its refusal gives: `core` names
# core's own decision records, agents and schemas area (#919, #1289); `project`
# names the project's own entries (#1269); `adr` names the project's architecture
# decision records (#1289); `backbone` names the four places the backbone's name is
# read as a component's (#1292).
RESERVED = [
    ("core", "the namespace of the core decision records and agents, and the core schemas area"),
    ("project", "indistinguishable from the project itself"),
    ("adr", "the namespace of the project's architecture decision records"),
    (
        "backbone",
        "the component of the backbone's changesets, the owner of its validators, the component "
        "its rule sets are cited with, and the component its documentation locations are "
        "recorded under",
    ),
]


@pytest.mark.parametrize(("name", "reason"), RESERVED)
def test_stamp_capability_refuses_a_reserved_name(kit_target: Path, name: str, reason: str) -> None:
    """A reserved name is refused with its reason, and nothing is written."""
    with pytest.raises(click.ClickException, match=f"'{name}' is reserved") as refused:
        stamp_capability(kit_target, name=name)
    assert reason in refused.value.message
    assert not (kit_target / ".pkit" / "capabilities" / name).exists()


@pytest.mark.parametrize(("name", "reason"), RESERVED)
def test_cli_new_capability_refuses_a_reserved_name(
    kit_target: Path, name: str, reason: str
) -> None:
    result = CliRunner().invoke(main, ["new", "capability", name])
    assert result.exit_code != 0
    output = " ".join(result.output.split())
    assert f"capability name '{name}' is reserved" in output
    assert reason in output
    assert not (kit_target / ".pkit" / "capabilities" / name).exists()


# A backbone command holds its top-level name before any capability, so a
# capability named after one could never surface its commands as `pkit <name> …`
# (#1300). The commands are read from the dispatcher when asked, never listed here.


@pytest.mark.parametrize("name", ["validate", "status", "sync", "capabilities"])
def test_stamp_capability_refuses_a_backbone_command_name(kit_target: Path, name: str) -> None:
    with pytest.raises(
        click.ClickException, match=f"is the backbone command `pkit {name}`"
    ) as refused:
        stamp_capability(kit_target, name=name)
    assert f"could never surface its commands as `pkit {name} …`" in refused.value.message
    assert not (kit_target / ".pkit" / "capabilities" / name).exists()


def test_stamp_capability_reads_the_backbone_commands_when_asked(
    kit_target: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A command the backbone gains is refused as soon as it is one."""
    assert "gather" not in main.commands
    monkeypatch.setitem(main.commands, "gather", click.Command("gather"))
    with pytest.raises(click.ClickException, match="is the backbone command `pkit gather`"):
        stamp_capability(kit_target, name="gather")


def test_cli_new_capability_refuses_a_backbone_command_name(kit_target: Path) -> None:
    result = CliRunner().invoke(main, ["new", "capability", "validate"])
    assert result.exit_code != 0
    output = " ".join(result.output.split())
    assert "capability name 'validate' is the backbone command `pkit validate`" in output
    assert "which every capability name and alias yields to" in output
    assert not (kit_target / ".pkit" / "capabilities" / "validate").exists()


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
    """Capabilities are kit-shipped; adopters register them at install time, not at scaffold
    time."""
    from project_kit import manifest as manifest_mod

    stamp_capability(kit_target, name="evidence")
    backbone = manifest_mod.read_backbone_manifest(kit_target)
    assert backbone is not None
    names_of_capability_kind = [c.name for c in backbone.components if c.kind == "capability"]
    assert "evidence" not in names_of_capability_kind
