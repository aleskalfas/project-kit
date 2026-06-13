"""Tests for `pkit validate` (PR-L of the build roadmap; closes #8)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import click
import pytest

from project_kit import install, manifest, validate


@pytest.fixture
def installed_target(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A git repo with the kit installed; ready for validation."""
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    monkeypatch.chdir(tmp_path)

    def _noop(_script: Path, _ctx: install.InstallContext) -> None:
        return None

    monkeypatch.setattr(install, "_run_adapter_primitive", _noop)
    install.install_kit(tmp_path)
    return tmp_path


def test_validate_refuses_when_pkit_missing(tmp_path: Path) -> None:
    with pytest.raises(click.ClickException, match=r"\.pkit/ does not exist"):
        validate.run_validate(tmp_path)


def test_validate_fresh_install_returns_no_issues(installed_target: Path) -> None:
    issues = validate.run_validate(installed_target)
    assert issues == [], f"expected clean validate, got: {issues}"


def test_validate_reports_missing_backbone_manifest(installed_target: Path) -> None:
    (installed_target / ".pkit" / "manifest.yaml").unlink()
    issues = validate.run_validate(installed_target)
    assert any(".pkit/manifest.yaml" in i.location for i in issues)
    assert any("missing" in i.diagnosis for i in issues)


def test_validate_reports_unknown_schema_version(installed_target: Path) -> None:
    """Tamper with the manifest's schema_version; validate should flag it."""
    m = manifest.read_backbone_manifest(installed_target)
    assert m is not None
    m.schema_version = 999
    manifest.write_backbone_manifest(installed_target, m)

    issues = validate.run_validate(installed_target)
    assert any("schema_version 999" in i.diagnosis for i in issues)


def test_validate_reports_decision_with_missing_frontmatter(installed_target: Path) -> None:
    """Drop a record with broken frontmatter; validate finds it."""
    record = installed_target / ".pkit" / "decisions" / "project" / "PRJ-999-broken.md"
    record.write_text("# No frontmatter here at all\n", encoding="utf-8")

    issues = validate.run_validate(installed_target)
    assert any("PRJ-999-broken.md" in i.location for i in issues)
    assert any("frontmatter" in i.diagnosis.lower() for i in issues)


def test_validate_reports_decision_with_invalid_status(installed_target: Path) -> None:
    """A record with an unrecognized status gets flagged."""
    record = installed_target / ".pkit" / "decisions" / "project" / "PRJ-998-bad-status.md"
    record.write_text(
        "---\n"
        "id: PRJ-998\n"
        "title: Bad status test\n"
        "status: unknown-status\n"
        "date: 2026-05-11\n"
        "author: Test <test@example.com>\n"
        "---\n"
        "\n## Context\n## Decision\n## Rationale\n## Implications\n",
        encoding="utf-8",
    )

    issues = validate.run_validate(installed_target)
    assert any("PRJ-998-bad-status.md" in i.location for i in issues)
    assert any("unknown-status" in i.diagnosis for i in issues)


def test_validate_passes_for_well_formed_records(installed_target: Path) -> None:
    """A record with all required frontmatter passes silently."""
    record = installed_target / ".pkit" / "decisions" / "project" / "PRJ-997-clean.md"
    record.write_text(
        "---\n"
        "id: PRJ-997\n"
        "title: Clean record\n"
        "status: proposed\n"
        "date: 2026-05-11\n"
        "author: Test <test@example.com>\n"
        "---\n"
        "\n## Context\n## Decision\n## Rationale\n## Implications\n",
        encoding="utf-8",
    )

    issues = validate.run_validate(installed_target)
    record_issues = [i for i in issues if "PRJ-997-clean.md" in i.location]
    assert record_issues == []
