"""Tests for the redacted environment snapshot (`pkit report`, PRJ-008 / ADR-047)."""

from __future__ import annotations

from pathlib import Path

from project_kit.environment import (
    UNRESOLVED,
    collect_environment,
    render_environment_block,
)
from project_kit.manifest import (
    ORIGIN_KIT_SHIPPED,
    BackboneManifest,
    ComponentManifest,
    ComponentRegistryEntry,
    write_backbone_manifest,
    write_component_manifest,
)


def _stage(target_root: Path) -> None:
    """A minimal installed tree: backbone + one kit-shipped and one incubated
    capability, each with a version in its component manifest."""
    (target_root / ".pkit").mkdir(parents=True, exist_ok=True)
    entries = []
    for name, origin, version in (
        ("project-management", ORIGIN_KIT_SHIPPED, "0.52.0"),
        ("secret-internal", "incubated-in-repo", "0.1.0"),
    ):
        rel = f".pkit/capabilities/{name}/project/manifest.yaml"
        write_component_manifest(
            target_root / rel,
            ComponentManifest(
                kind="capability", name=name, version=version,
                installed_at="2026-08-07", requires_backbone=">=1.0.0",
            ),
        )
        entries.append(
            ComponentRegistryEntry(
                kind="capability", name=name, manifest=rel, origin=origin
            )
        )
    write_backbone_manifest(
        target_root, BackboneManifest(backbone_version="1.143.1", components=entries)
    )


def test_collect_environment_basic(tmp_path: Path) -> None:
    _stage(tmp_path)
    env = collect_environment(tmp_path)
    assert env.backbone_version == "1.143.1"
    # Kit-shipped capability listed with version; incubated one withheld.
    assert ("project-management", "0.52.0") in env.capabilities
    assert all(name != "secret-internal" for name, _ in env.capabilities)
    assert env.private_capability_count == 1
    assert env.tool_version  # non-empty
    assert env.python


def test_collect_environment_include_private(tmp_path: Path) -> None:
    _stage(tmp_path)
    env = collect_environment(tmp_path, include_private=True)
    names = {name for name, _ in env.capabilities}
    assert {"project-management", "secret-internal"} <= names
    assert env.private_capability_count == 0


def test_collect_environment_no_manifest(tmp_path: Path) -> None:
    # A tree with no manifest degrades gracefully rather than raising.
    (tmp_path / ".pkit").mkdir(parents=True)
    env = collect_environment(tmp_path)
    assert env.backbone_version == "unknown"
    assert env.capabilities == ()


def test_render_environment_block_is_redacted(tmp_path: Path) -> None:
    _stage(tmp_path)
    block = render_environment_block(collect_environment(tmp_path))
    assert block.startswith("## Environment")
    assert "backbone:      1.143.1" in block
    assert "project-management 0.52.0" in block
    # Redaction: no filesystem paths leak, and the withheld count is surfaced
    # without the private capability's name.
    assert str(tmp_path) not in block
    assert "/Users/" not in block and "/home/" not in block
    assert "secret-internal" not in block
    assert "names withheld" in block


def test_collect_environment_unresolved_root_collects_no_project_half() -> None:
    # No root resolved (#693): the project half is NOT collected — and the
    # snapshot says so, instead of reporting an empty install.
    env = collect_environment(None)
    assert env.project_resolved is False
    assert env.backbone_version == UNRESOLVED
    assert env.adapter == UNRESOLVED
    assert env.capabilities == ()
    # the process half is a property of the running command, so still honest
    assert env.tool_version and env.python and env.os


def test_render_environment_block_unresolved_reads_as_not_collected() -> None:
    block = render_environment_block(collect_environment(None))
    assert block.startswith("## Environment")
    assert block.rstrip().endswith("```")  # same fenced shape
    assert "NOT COLLECTED" in block
    # never the values a maintainer reads as facts about the reporter's install
    assert "(none installed)" not in block
    assert "backbone:" not in block and "adapter:" not in block


def test_render_environment_block_unresolved_carries_no_path(
    tmp_path: Path, monkeypatch
) -> None:
    # The unresolved marker rides into a PUBLIC issue body: path-free, always.
    monkeypatch.chdir(tmp_path)
    block = render_environment_block(collect_environment(None))
    assert str(Path.cwd()) not in block
    assert "/Users/" not in block and "/home/" not in block


def test_render_environment_block_shows_private_names_when_included(tmp_path: Path) -> None:
    _stage(tmp_path)
    block = render_environment_block(
        collect_environment(tmp_path, include_private=True)
    )
    assert "secret-internal 0.1.0" in block
    assert "names withheld" not in block
