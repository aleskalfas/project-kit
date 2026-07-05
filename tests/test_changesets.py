"""Tests for changeset parsing, component discovery, and filename generation
(PRJ-002 D1/D2)."""

from __future__ import annotations

from pathlib import Path

import click
import pytest

from project_kit import changesets


def _make_kit(tmp_path: Path, version: str = "1.5.0") -> Path:
    """A minimal source kit: VERSION + two component package.yaml files."""
    source_kit = tmp_path / ".pkit"
    source_kit.mkdir()
    (source_kit / "VERSION").write_text(f"{version}\n", encoding="utf-8")

    adapter = source_kit / "adapters" / "claude-code"
    adapter.mkdir(parents=True)
    (adapter / "package.yaml").write_text(
        "schema_version: 1\n"
        "component:\n"
        "  kind: adapter\n"
        "  name: claude-code\n"
        "  version: 0.5.0\n"
        'requires_backbone: ">=0.1.0,<2.0.0"\n',
        encoding="utf-8",
    )
    cap = source_kit / "capabilities" / "project-management"
    cap.mkdir(parents=True)
    (cap / "package.yaml").write_text(
        "schema_version: 2\n"
        "component:\n"
        "  kind: capability\n"
        "  name: project-management\n"
        "  version: 0.47.0\n"
        'requires_backbone: ">=1.0.0,<2.0.0"\n',
        encoding="utf-8",
    )
    return source_kit


def _write_changeset(source_kit: Path, component: str, kind: str, body: str, name: str) -> Path:
    directory = changesets.unreleased_dir(source_kit.parent)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    path.write_text(f"component: {component}\nkind: {kind}\nbody: {body}\n", encoding="utf-8")
    return path


def test_discover_components_lists_backbone_first_then_sorted(tmp_path: Path) -> None:
    source_kit = _make_kit(tmp_path)
    components = changesets.discover_components(source_kit)
    names = [c.name for c in components]
    assert names[0] == "backbone"
    assert names[1:] == ["claude-code", "project-management"]

    backbone = components[0]
    assert backbone.kind == "backbone"
    assert backbone.version == "1.5.0"
    assert backbone.subtree is None

    adapter = components[1]
    assert adapter.version == "0.5.0"
    assert adapter.subtree == Path(".pkit/adapters/claude-code")


def test_parse_changeset_reads_changie_native_fields(tmp_path: Path) -> None:
    source_kit = _make_kit(tmp_path)
    path = _write_changeset(source_kit, "backbone", "minor", "Add release step.", "cs.yaml")
    cs = changesets.parse_changeset(path)
    assert cs.component == "backbone"
    assert cs.segment == "minor"
    assert cs.note == "Add release step."


def test_parse_changeset_ignores_extra_changie_fields(tmp_path: Path) -> None:
    """changie writes `time` / `custom`; the parser must tolerate them."""
    source_kit = _make_kit(tmp_path)
    directory = changesets.unreleased_dir(source_kit.parent)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "cs.yaml"
    path.write_text(
        "component: claude-code\n"
        "kind: patch\n"
        "body: Fix a thing.\n"
        "time: 2026-07-03T10:00:00Z\n"
        "custom: {}\n",
        encoding="utf-8",
    )
    cs = changesets.parse_changeset(path)
    assert cs.component == "claude-code"
    assert cs.segment == "patch"


def test_parse_changeset_reads_category_and_pr_top_level(tmp_path: Path) -> None:
    source_kit = _make_kit(tmp_path)
    directory = changesets.unreleased_dir(source_kit.parent)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "cs.yaml"
    path.write_text(
        "component: backbone\nkind: minor\nbody: A thing.\ncategory: Added\npr: 465\n",
        encoding="utf-8",
    )
    cs = changesets.parse_changeset(path)
    assert cs.category == "Added"
    assert cs.pr == "465"


def test_parse_changeset_reads_category_and_pr_from_custom(tmp_path: Path) -> None:
    """changie writes the extra fields under a nested `custom:` map."""
    source_kit = _make_kit(tmp_path)
    directory = changesets.unreleased_dir(source_kit.parent)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "cs.yaml"
    path.write_text(
        "component: backbone\n"
        "kind: minor\n"
        "body: A thing.\n"
        "custom:\n"
        "  category: Fixed\n"
        "  pr: 'https://example.test/pull/470'\n",
        encoding="utf-8",
    )
    cs = changesets.parse_changeset(path)
    assert cs.category == "Fixed"
    assert cs.pr == "https://example.test/pull/470"


def test_parse_changeset_defaults_category_and_pr_to_none_when_absent(tmp_path: Path) -> None:
    source_kit = _make_kit(tmp_path)
    path = _write_changeset(source_kit, "backbone", "minor", "A thing.", "cs.yaml")
    cs = changesets.parse_changeset(path)
    assert cs.category is None
    assert cs.pr is None


def test_parse_changeset_none_kind_needs_no_category(tmp_path: Path) -> None:
    """A `none` changeset carries no category and still parses cleanly."""
    source_kit = _make_kit(tmp_path)
    path = _write_changeset(source_kit, "backbone", "none", "docs only", "cs.yaml")
    cs = changesets.parse_changeset(path)
    assert cs.segment == "none"
    assert cs.category is None


def test_parse_changeset_refuses_unknown_kind(tmp_path: Path) -> None:
    source_kit = _make_kit(tmp_path)
    path = _write_changeset(source_kit, "backbone", "huge", "x", "cs.yaml")
    with pytest.raises(click.ClickException, match="expected one of"):
        changesets.parse_changeset(path)


def test_parse_changeset_refuses_missing_component(tmp_path: Path) -> None:
    source_kit = _make_kit(tmp_path)
    directory = changesets.unreleased_dir(source_kit.parent)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "cs.yaml"
    path.write_text("kind: minor\nbody: x\n", encoding="utf-8")
    with pytest.raises(click.ClickException, match="missing `component`"):
        changesets.parse_changeset(path)


def test_load_changesets_empty_when_no_dir(tmp_path: Path) -> None:
    source_kit = _make_kit(tmp_path)
    assert changesets.load_changesets(source_kit.parent) == []


def test_load_changesets_sorted_by_filename(tmp_path: Path) -> None:
    source_kit = _make_kit(tmp_path)
    _write_changeset(source_kit, "backbone", "minor", "b", "b.yaml")
    _write_changeset(source_kit, "claude-code", "patch", "a", "a.yaml")
    loaded = changesets.load_changesets(source_kit.parent)
    assert [cs.path.name for cs in loaded] == ["a.yaml", "b.yaml"]


def test_changeset_filename_is_collision_free_across_calls(tmp_path: Path) -> None:
    """Two changesets for the same component+segment must not collide."""
    names = {changesets.changeset_filename("backbone", "minor") for _ in range(200)}
    assert len(names) == 200  # random suffix guarantees distinctness


def test_changeset_filename_shape_and_safety() -> None:
    name = changesets.changeset_filename("project-management", "patch", rand="deadbeef")
    assert name.startswith("project-management-patch-")
    assert name.endswith("-deadbeef.yaml")
    # Filesystem-safe: no path separators or spaces.
    assert "/" not in name and " " not in name


def test_segment_rank_orders_none_lowest_major_highest() -> None:
    ranks = [changesets.segment_rank(s) for s in ("none", "patch", "minor", "major")]
    assert ranks == sorted(ranks)
    assert ranks == [0, 1, 2, 3]
