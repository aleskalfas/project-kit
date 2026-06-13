"""Tests for `pkit new area` (the Python port stamping area scaffolds)."""

from __future__ import annotations

from pathlib import Path

import click
import pytest

from project_kit.scaffolds import stamp_area


@pytest.fixture
def kit_target(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A minimal project with `.pkit/` only."""
    (tmp_path / ".pkit").mkdir()
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_stamp_area_default_specialized(kit_target: Path) -> None:
    result = stamp_area(kit_target, name="myarea")
    assert result.area_dir == kit_target / ".pkit" / "myarea"
    assert result.area_dir.is_dir()
    text = result.readme.read_text(encoding="utf-8")
    assert "variant: specialized" in text
    # Specialized variant adds no sub-layout — just README.
    entries = sorted(p.name for p in result.area_dir.iterdir())
    assert entries == ["README.md"]


def test_stamp_area_universal_variant_creates_core_and_project(kit_target: Path) -> None:
    result = stamp_area(kit_target, name="universal-area", variant="universal")
    assert (result.area_dir / "core").is_dir()
    assert (result.area_dir / "project").is_dir()
    text = result.readme.read_text(encoding="utf-8")
    assert "variant: universal" in text


def test_stamp_area_adapter_umbrella_no_sublayout(kit_target: Path) -> None:
    result = stamp_area(kit_target, name="harnesses", variant="adapter-umbrella")
    text = result.readme.read_text(encoding="utf-8")
    assert "variant: adapter-umbrella" in text
    # Only README — adapter directories are added later by `pkit new adapter`.
    entries = sorted(p.name for p in result.area_dir.iterdir())
    assert entries == ["README.md"]


def test_stamp_area_refuses_on_name_collision(kit_target: Path) -> None:
    stamp_area(kit_target, name="dupe")
    with pytest.raises(click.ClickException, match="already exists"):
        stamp_area(kit_target, name="dupe")


def test_stamp_area_refuses_invalid_slug(kit_target: Path) -> None:
    with pytest.raises(click.ClickException, match="kebab-case"):
        stamp_area(kit_target, name="Bad Area")


def test_stamp_area_refuses_when_pkit_missing(tmp_path: Path) -> None:
    with pytest.raises(click.ClickException, match="does not exist"):
        stamp_area(tmp_path, name="x")


def test_stamp_area_readme_includes_title(kit_target: Path) -> None:
    result = stamp_area(kit_target, name="multi-word-area")
    text = result.readme.read_text(encoding="utf-8")
    # Title-case rendering: "Multi word area" (first word capitalized).
    assert "# Multi word area" in text
