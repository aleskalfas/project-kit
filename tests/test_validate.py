"""Tests for `pkit validate` (PR-L of the build roadmap; closes #8)."""

from __future__ import annotations

from pathlib import Path

import click
import pytest

from project_kit import manifest, validate
from tests.adopter_repo import MakeAdopterRepo


@pytest.fixture
def installed_target(make_adopter_repo: MakeAdopterRepo) -> Path:
    """A git repo with the kit installed; ready for validation."""
    return make_adopter_repo().root


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


# --- synced copies (COR-055 point 1) -----------------------------------


def test_validate_leaves_out_a_synced_copy_with_a_bad_front_matter(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    """In an adopter a core record arrives as a synced copy, which the project cannot
    mend: its front matter is not checked, and the project's own record's is."""
    root = make_adopter_repo().root
    decisions = root / ".pkit" / "decisions"
    (decisions / "core" / "COR-900-broken.md").write_text("# No front matter\n", encoding="utf-8")
    (decisions / "core" / "COR-901-bad-status.md").write_text(
        "---\nid: COR-901\ntitle: x\nstatus: unknown-status\ndate: 2026-10-13\nauthor: t\n---\n",
        encoding="utf-8",
    )
    (decisions / "project" / "PRJ-900-broken.md").write_text(
        "# No front matter\n", encoding="utf-8"
    )

    issues = validate.decision_frontmatter_issues(root)

    assert [issue.location for issue in issues] == [".pkit/decisions/project/PRJ-900-broken.md"]


def test_validate_checks_core_front_matter_in_the_methodology_source(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    """Where the methodology is authored nothing is a copy, so a core record's front
    matter is checked."""
    root = make_adopter_repo().root
    package = root / "src" / "project_kit" / "__init__.py"
    package.parent.mkdir(parents=True)
    package.write_text("", encoding="utf-8")
    core = root / ".pkit" / "decisions" / "core"
    (core / "COR-900-broken.md").write_text("# No front matter\n", encoding="utf-8")

    issues = validate.decision_frontmatter_issues(root)

    assert [issue.location for issue in issues] == [".pkit/decisions/core/COR-900-broken.md"]
