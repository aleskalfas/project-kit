"""Tests for the pre-sharing shareability check (`pkit release check-shareable`,
#494 / COR-041): a capability is ready to be consumed externally-sourced when it
declares a version, a well-formed manifest, and a bounded requires_backbone
range the consumer's compatibility gate can evaluate."""

from __future__ import annotations

from pathlib import Path

import click
import pytest

from project_kit import release


def _make_kit(tmp_path: Path, backbone: str = "1.5.0") -> Path:
    source_kit = tmp_path / ".pkit"
    source_kit.mkdir()
    (source_kit / "VERSION").write_text(f"{backbone}\n", encoding="utf-8")
    return source_kit


def _write_capability(source_kit: Path, name: str, body: str) -> Path:
    cap = source_kit / "capabilities" / name
    cap.mkdir(parents=True)
    pkg = cap / "package.yaml"
    pkg.write_text(body, encoding="utf-8")
    return pkg


def _well_formed(name: str = "houseware") -> str:
    return (
        "schema_version: 1\n"
        "component:\n"
        "  kind: capability\n"
        f"  name: {name}\n"
        "  version: 0.3.0\n"
        'requires_backbone: ">=1.0.0,<2.0.0"\n'
    )


def test_shareable_passes_well_formed_capability(tmp_path: Path) -> None:
    source_kit = _make_kit(tmp_path)
    _write_capability(source_kit, "houseware", _well_formed())

    report = release.check_shareable(source_kit, "houseware")
    assert report.ok
    assert report.gaps == []
    assert report.warnings == []


def test_shareable_flags_missing_version(tmp_path: Path) -> None:
    source_kit = _make_kit(tmp_path)
    _write_capability(
        source_kit,
        "houseware",
        "schema_version: 1\n"
        "component:\n"
        "  kind: capability\n"
        "  name: houseware\n"
        'requires_backbone: ">=1.0.0,<2.0.0"\n',
    )

    report = release.check_shareable(source_kit, "houseware")
    assert not report.ok
    assert any("version" in gap for gap in report.gaps)


def test_shareable_flags_missing_requires_backbone(tmp_path: Path) -> None:
    source_kit = _make_kit(tmp_path)
    _write_capability(
        source_kit,
        "houseware",
        "schema_version: 1\n"
        "component:\n"
        "  kind: capability\n"
        "  name: houseware\n"
        "  version: 0.3.0\n",
    )

    report = release.check_shareable(source_kit, "houseware")
    assert not report.ok
    assert any("requires_backbone" in gap for gap in report.gaps)


def test_shareable_flags_unbounded_requires_backbone(tmp_path: Path) -> None:
    source_kit = _make_kit(tmp_path)
    _write_capability(
        source_kit,
        "houseware",
        "schema_version: 1\n"
        "component:\n"
        "  kind: capability\n"
        "  name: houseware\n"
        "  version: 0.3.0\n"
        'requires_backbone: "*"\n',
    )

    report = release.check_shareable(source_kit, "houseware")
    assert not report.ok
    assert any("bounded range" in gap for gap in report.gaps)


def test_shareable_flags_malformed_manifest(tmp_path: Path) -> None:
    source_kit = _make_kit(tmp_path)
    # A well-formed YAML mapping but with no `component:` block — the manifest
    # is malformed for a component (no version/kind/name can be read).
    _write_capability(
        source_kit,
        "houseware",
        "schema_version: 1\ndescription: a capability with no component block\n",
    )

    report = release.check_shareable(source_kit, "houseware")
    assert not report.ok
    assert any("component" in gap for gap in report.gaps)


def test_shareable_warns_on_local_path(tmp_path: Path) -> None:
    source_kit = _make_kit(tmp_path)
    _write_capability(
        source_kit,
        "houseware",
        "schema_version: 1\n"
        "component:\n"
        "  kind: capability\n"
        "  name: houseware\n"
        "  version: 0.3.0\n"
        'requires_backbone: ">=1.0.0,<2.0.0"\n'
        "description: reads /Users/alice/secret/config.yaml at load time\n",
    )

    report = release.check_shareable(source_kit, "houseware")
    # A local path is a non-blocking warning, not a gap.
    assert report.ok
    assert any("local-only path" in w for w in report.warnings)


def test_shareable_refuses_backbone(tmp_path: Path) -> None:
    source_kit = _make_kit(tmp_path)
    with pytest.raises(click.ClickException, match="backbone tier"):
        release.check_shareable(source_kit, "backbone")


def test_shareable_refuses_unknown_component(tmp_path: Path) -> None:
    source_kit = _make_kit(tmp_path)
    _write_capability(source_kit, "houseware", _well_formed())
    with pytest.raises(click.ClickException, match="unknown component"):
        release.check_shareable(source_kit, "nope")
