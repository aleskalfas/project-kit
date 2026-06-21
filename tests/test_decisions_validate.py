"""Tests for the decision-id collision check (`pkit decisions validate`, Feature #162)."""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from project_kit import decisions_validate
from project_kit.cli import main


def _write_record(path: Path, record_id: str) -> None:
    """Stamp a minimal decision record with the given frontmatter id at `path`."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"---\nid: {record_id}\ntitle: x\nstatus: proposed\n"
        f"date: 2026-06-21\nauthor: t\n---\n\n## Context\n",
        encoding="utf-8",
    )


def _make_capability(target_root: Path, name: str) -> Path:
    """Create a minimal valid capability directory; return its decisions/ path."""
    cap_dir = target_root / ".pkit" / "capabilities" / name
    cap_dir.mkdir(parents=True)
    (cap_dir / "package.yaml").write_text(
        f"component:\n  kind: capability\n  name: {name}\n  version: 0.1.0\n",
        encoding="utf-8",
    )
    decisions_dir = cap_dir / "decisions"
    decisions_dir.mkdir()
    return decisions_dir


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """A project tree with the fixed decision namespaces present."""
    (tmp_path / ".pkit" / "decisions" / "core").mkdir(parents=True)
    (tmp_path / ".pkit" / "decisions" / "project").mkdir(parents=True)
    return tmp_path


# --- clean repo --------------------------------------------------------


def test_clean_repo_passes(project: Path) -> None:
    core = project / ".pkit" / "decisions" / "core"
    _write_record(core / "COR-001-a.md", "COR-001")
    _write_record(core / "COR-002-b.md", "COR-002")
    _write_record(project / ".pkit" / "decisions" / "project" / "PRJ-001-c.md", "PRJ-001")

    report = decisions_validate.validate_decision_ids(project)
    assert report.is_clean
    assert report.records_checked == 3


def test_empty_repo_is_clean(project: Path) -> None:
    report = decisions_validate.validate_decision_ids(project)
    assert report.is_clean
    assert report.records_checked == 0


# --- duplicate detection -----------------------------------------------


def test_duplicate_id_in_same_space_fails(project: Path) -> None:
    core = project / ".pkit" / "decisions" / "core"
    _write_record(core / "COR-001-a.md", "COR-001")
    _write_record(core / "COR-001-b.md", "COR-001")

    report = decisions_validate.validate_decision_ids(project)
    assert not report.is_clean
    dupes = [i for i in report.issues if "COR-001" in i.location]
    assert len(dupes) == 1
    assert "COR-001-a.md" in dupes[0].message
    assert "COR-001-b.md" in dupes[0].message


def test_duplicate_dec_in_same_capability_fails(project: Path) -> None:
    cap = _make_capability(project, "alpha")
    _write_record(cap / "DEC-001-one.md", "DEC-001")
    _write_record(cap / "DEC-001-two.md", "DEC-001")

    report = decisions_validate.validate_decision_ids(project)
    assert not report.is_clean
    assert any("capability:alpha :: DEC-001" == i.location for i in report.issues)


# --- cross-space is NOT a collision ------------------------------------


def test_same_dec_number_in_two_capabilities_is_not_a_collision(project: Path) -> None:
    alpha = _make_capability(project, "alpha")
    beta = _make_capability(project, "beta")
    _write_record(alpha / "DEC-001-a.md", "DEC-001")
    _write_record(beta / "DEC-001-b.md", "DEC-001")

    report = decisions_validate.validate_decision_ids(project)
    assert report.is_clean, [i.message for i in report.issues]
    assert report.records_checked == 2


def test_cor_and_prj_with_same_number_is_not_a_collision(project: Path) -> None:
    _write_record(project / ".pkit" / "decisions" / "core" / "COR-001-a.md", "COR-001")
    _write_record(project / ".pkit" / "decisions" / "project" / "PRJ-001-b.md", "PRJ-001")

    report = decisions_validate.validate_decision_ids(project)
    assert report.is_clean


# --- id / filename consistency -----------------------------------------


def test_id_filename_mismatch_is_flagged(project: Path) -> None:
    core = project / ".pkit" / "decisions" / "core"
    _write_record(core / "COR-005-mismatch.md", "COR-003")

    report = decisions_validate.validate_decision_ids(project)
    assert not report.is_clean
    assert any("disagrees with the filename" in i.message for i in report.issues)


def test_zero_padding_difference_is_not_a_mismatch(project: Path) -> None:
    core = project / ".pkit" / "decisions" / "core"
    # filename uses unpadded number; frontmatter is padded — same number.
    _write_record(core / "COR-7-x.md", "COR-007")
    report = decisions_validate.validate_decision_ids(project)
    assert report.is_clean


def test_unparseable_id_is_flagged(project: Path) -> None:
    core = project / ".pkit" / "decisions" / "core"
    (core / "COR-001-bad.md").write_text("no frontmatter here\n", encoding="utf-8")
    report = decisions_validate.validate_decision_ids(project)
    assert not report.is_clean
    assert any("could not parse" in i.message for i in report.issues)


def test_readme_in_decisions_dir_is_skipped(project: Path) -> None:
    proj = project / ".pkit" / "decisions" / "project"
    (proj / "README.md").write_text("# index\n", encoding="utf-8")
    _write_record(proj / "PRJ-001-a.md", "PRJ-001")
    report = decisions_validate.validate_decision_ids(project)
    assert report.is_clean
    assert report.records_checked == 1


# --- ADR id-space ------------------------------------------------------


def test_adr_duplicates_detected_via_overlay(project: Path) -> None:
    overlay = project / ".pkit" / "agents" / "project" / "overlay.yaml"
    overlay.parent.mkdir(parents=True)
    overlay.write_text("adr-records:\n  - docs/architecture/decisions/\n", encoding="utf-8")
    adr_dir = project / "docs" / "architecture" / "decisions"
    adr_dir.mkdir(parents=True)
    _write_record(adr_dir / "ADR-001-a.md", "ADR-001")
    _write_record(adr_dir / "ADR-001-b.md", "ADR-001")

    report = decisions_validate.validate_decision_ids(project)
    assert not report.is_clean
    assert any("adr :: ADR-001" == i.location for i in report.issues)


def test_missing_overlay_does_not_error(project: Path) -> None:
    # No overlay configured: ADRs simply aren't scanned, no crash.
    _write_record(project / ".pkit" / "decisions" / "core" / "COR-001-a.md", "COR-001")
    report = decisions_validate.validate_decision_ids(project)
    assert report.is_clean


# --- CLI ---------------------------------------------------------------


def test_cli_clean_exits_zero(project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import subprocess

    subprocess.run(["git", "init", "-q"], cwd=project, check=True)
    _write_record(project / ".pkit" / "decisions" / "core" / "COR-001-a.md", "COR-001")
    monkeypatch.chdir(project)
    result = CliRunner().invoke(main, ["decisions", "validate"])
    assert result.exit_code == 0
    assert "No id collisions found" in result.output


def test_cli_duplicate_exits_nonzero(project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import subprocess

    subprocess.run(["git", "init", "-q"], cwd=project, check=True)
    core = project / ".pkit" / "decisions" / "core"
    _write_record(core / "COR-001-a.md", "COR-001")
    _write_record(core / "COR-001-b.md", "COR-001")
    monkeypatch.chdir(project)
    result = CliRunner().invoke(main, ["decisions", "validate"])
    assert result.exit_code != 0
    assert "COR-001" in result.output
