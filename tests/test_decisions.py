"""Tests for `pkit new decision` (the Python port of the bash dispatcher's `cmd_new_decision`)."""

from __future__ import annotations

from pathlib import Path

import click
import pytest

from project_kit import decisions


@pytest.fixture
def kit_target(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Synthesise a minimal project tree with `.pkit/decisions/{core,project}/`."""
    (tmp_path / ".pkit" / "decisions" / "core").mkdir(parents=True)
    (tmp_path / ".pkit" / "decisions" / "project").mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture(autouse=True)
def fixed_today(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pin `decisions._today()` so frontmatter dates are deterministic."""
    monkeypatch.setattr(decisions, "_today", lambda: "2026-05-09")


@pytest.fixture(autouse=True)
def fixed_git_author(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pin git config user.name + user.email lookups so author is deterministic."""

    def _fake_git_config(key: str) -> str:
        return {"user.name": "Test Author", "user.email": "test@example.com"}.get(key, "")

    monkeypatch.setattr(decisions, "_git_config", _fake_git_config)


def test_stamp_decision_writes_cor_in_core_namespace(kit_target: Path) -> None:
    target = decisions.stamp_decision(kit_target, namespace="core", slug="my-rule")
    assert target.name == "COR-001-my-rule.md"
    assert target.parent == kit_target / ".pkit" / "decisions" / "core"

    content = target.read_text(encoding="utf-8")
    assert "id: COR-001" in content
    assert "title: <short imperative title>" in content
    assert "status: proposed" in content
    assert "date: 2026-05-09" in content
    assert "author: Test Author <test@example.com>" in content
    for header in ("## Context", "## Decision", "## Rationale", "## Implications"):
        assert header in content


def test_stamp_decision_writes_prj_in_project_namespace(kit_target: Path) -> None:
    target = decisions.stamp_decision(kit_target, namespace="project", slug="my-decision")
    assert target.name == "PRJ-001-my-decision.md"
    assert "id: PRJ-001" in target.read_text(encoding="utf-8")


def test_stamp_decision_picks_next_number_per_namespace(kit_target: Path) -> None:
    core_dir = kit_target / ".pkit" / "decisions" / "core"
    (core_dir / "COR-001-first.md").write_text("dummy", encoding="utf-8")
    (core_dir / "COR-002-second.md").write_text("dummy", encoding="utf-8")
    (core_dir / "COR-005-fifth.md").write_text("dummy", encoding="utf-8")

    target = decisions.stamp_decision(kit_target, namespace="core", slug="next")
    assert target.name == "COR-006-next.md"


def test_stamp_decision_numbering_is_independent_across_namespaces(kit_target: Path) -> None:
    core_dir = kit_target / ".pkit" / "decisions" / "core"
    (core_dir / "COR-001-x.md").write_text("dummy", encoding="utf-8")
    (core_dir / "COR-002-y.md").write_text("dummy", encoding="utf-8")

    target = decisions.stamp_decision(kit_target, namespace="project", slug="first-prj")
    # No PRJs exist yet → next number is 1, not 3.
    assert target.name == "PRJ-001-first-prj.md"


def test_stamp_decision_refuses_invalid_slug(kit_target: Path) -> None:
    with pytest.raises(click.ClickException, match="kebab-case"):
        decisions.stamp_decision(kit_target, namespace="core", slug="Has_Underscore")


def test_stamp_decision_refuses_duplicate_slug(kit_target: Path) -> None:
    decisions.stamp_decision(kit_target, namespace="core", slug="dupe")
    with pytest.raises(click.ClickException, match="already exists"):
        decisions.stamp_decision(kit_target, namespace="core", slug="dupe")


def test_stamp_decision_refuses_when_namespace_dir_missing(tmp_path: Path) -> None:
    # Only .pkit/ exists; no decisions/<ns>/ subdir.
    (tmp_path / ".pkit").mkdir()
    with pytest.raises(click.ClickException, match="does not exist"):
        decisions.stamp_decision(tmp_path, namespace="core", slug="x")


def _empty_git_config(_key: str) -> str:
    return ""


def _name_only_git_config(key: str) -> str:
    return "Just A Name" if key == "user.name" else ""


def test_stamp_decision_falls_back_to_unknown_author_when_git_unset(
    kit_target: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(decisions, "_git_config", _empty_git_config)
    target = decisions.stamp_decision(kit_target, namespace="core", slug="anonymous")
    assert "author: <unknown>" in target.read_text(encoding="utf-8")


def test_stamp_decision_uses_name_only_when_email_missing(
    kit_target: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(decisions, "_git_config", _name_only_git_config)
    target = decisions.stamp_decision(kit_target, namespace="core", slug="name-only")
    assert "author: Just A Name" in target.read_text(encoding="utf-8")


# ---------------------------------------------------------------- ADR namespace


def _write_overlay(kit_target: Path, content: str) -> Path:
    overlay = kit_target / ".pkit" / "agents" / "project" / "overlay.yaml"
    overlay.parent.mkdir(parents=True, exist_ok=True)
    overlay.write_text(content, encoding="utf-8")
    return overlay


def test_stamp_decision_writes_adr_at_overlay_path(kit_target: Path) -> None:
    _write_overlay(kit_target, "adr-records:\n  - docs/architecture/decisions/\n")
    adr_dir = kit_target / "docs" / "architecture" / "decisions"
    adr_dir.mkdir(parents=True)

    target = decisions.stamp_decision(kit_target, namespace="adr", slug="first-adr")
    assert target.name == "ADR-001-first-adr.md"
    assert target.parent == adr_dir
    content = target.read_text(encoding="utf-8")
    assert "id: ADR-001" in content
    assert "status: proposed" in content
    for header in ("## Context", "## Decision", "## Rationale", "## Implications"):
        assert header in content


def test_stamp_decision_adr_numbering_is_independent(kit_target: Path) -> None:
    _write_overlay(kit_target, "adr-records:\n  - docs/architecture/decisions/\n")
    adr_dir = kit_target / "docs" / "architecture" / "decisions"
    adr_dir.mkdir(parents=True)
    (adr_dir / "ADR-001-existing.md").write_text("dummy", encoding="utf-8")
    (adr_dir / "ADR-003-skip.md").write_text("dummy", encoding="utf-8")
    # COR records in .pkit/decisions/core/ must not affect ADR numbering.
    (kit_target / ".pkit" / "decisions" / "core" / "COR-007-x.md").write_text("dummy", encoding="utf-8")

    target = decisions.stamp_decision(kit_target, namespace="adr", slug="next-adr")
    assert target.name == "ADR-004-next-adr.md"


def test_stamp_decision_adr_refuses_when_overlay_missing(kit_target: Path) -> None:
    # No overlay.yaml seeded.
    with pytest.raises(click.ClickException, match="overlay"):
        decisions.stamp_decision(kit_target, namespace="adr", slug="orphan")


def test_stamp_decision_adr_refuses_when_overlay_lacks_adr_records(kit_target: Path) -> None:
    _write_overlay(kit_target, "workflow-docs:\n  - README.md\n")
    with pytest.raises(click.ClickException, match="adr-records"):
        decisions.stamp_decision(kit_target, namespace="adr", slug="no-key")


def test_stamp_decision_adr_refuses_when_adr_records_empty_list(kit_target: Path) -> None:
    _write_overlay(kit_target, "adr-records: []\n")
    with pytest.raises(click.ClickException, match="missing or empty"):
        decisions.stamp_decision(kit_target, namespace="adr", slug="empty-list")


def test_stamp_decision_adr_refuses_when_path_inside_pkit(kit_target: Path) -> None:
    _write_overlay(kit_target, "adr-records:\n  - .pkit/decisions/adr/\n")
    (kit_target / ".pkit" / "decisions" / "adr").mkdir(parents=True)
    with pytest.raises(click.ClickException, match="outside .pkit/"):
        decisions.stamp_decision(kit_target, namespace="adr", slug="inside-pkit")


def test_stamp_decision_adr_refuses_when_directory_missing(kit_target: Path) -> None:
    _write_overlay(kit_target, "adr-records:\n  - docs/architecture/decisions/\n")
    # Directory deliberately not created.
    with pytest.raises(click.ClickException, match="does not exist"):
        decisions.stamp_decision(kit_target, namespace="adr", slug="no-dir")


def test_stamp_decision_adr_refuses_duplicate_slug(kit_target: Path) -> None:
    _write_overlay(kit_target, "adr-records:\n  - docs/architecture/decisions/\n")
    (kit_target / "docs" / "architecture" / "decisions").mkdir(parents=True)
    decisions.stamp_decision(kit_target, namespace="adr", slug="dupe")
    with pytest.raises(click.ClickException, match="already exists"):
        decisions.stamp_decision(kit_target, namespace="adr", slug="dupe")


def test_resolve_adr_records_dir_returns_absolute_path(kit_target: Path) -> None:
    _write_overlay(kit_target, "adr-records:\n  - docs/architecture/decisions/\n")
    adr_dir = kit_target / "docs" / "architecture" / "decisions"
    adr_dir.mkdir(parents=True)
    resolved = decisions.resolve_adr_records_dir(kit_target)
    assert resolved == adr_dir.resolve()
