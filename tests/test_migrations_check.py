"""Tests for `pkit migrations check-diff` and the coverage-check helpers."""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from project_kit import migrations as migrations_mod
from project_kit.cli import main
from project_kit.migrations import (
    CoverageReport,
    DiffMigration,
    DiffTrigger,
    check_diff_coverage,
)


# --- _classify_path ----------------------------------------------------


def test_classify_backbone_core_record() -> None:
    assert migrations_mod._classify_path(
        ".pkit/decisions/core/COR-005-bundle-pattern.md"
    ) == ("backbone", None)


def test_classify_backbone_skill() -> None:
    assert migrations_mod._classify_path(".pkit/skills/core/decision-author.md") == (
        "backbone",
        None,
    )


def test_classify_workflow_legacy_path_is_backbone() -> None:
    """Per COR-027, leftover .pkit/workflow/ paths classify as backbone-tier
    (the area was retired; cleanup is backbone-level)."""
    assert migrations_mod._classify_path(
        ".pkit/workflow/bundles/github-issues/skills/foo.md"
    ) == ("backbone", None)


def test_classify_adapter() -> None:
    assert migrations_mod._classify_path(
        ".pkit/adapters/claude-code/deploy-skills.sh"
    ) == ("adapter", "claude-code")


def test_classify_capability() -> None:
    assert migrations_mod._classify_path(
        ".pkit/capabilities/evidence/skills/evidence-add.md"
    ) == ("capability", "evidence")


def test_classify_project_subtrees_excluded() -> None:
    assert migrations_mod._classify_path(".pkit/decisions/project/PRJ-001-foo.md") is None
    assert migrations_mod._classify_path(".pkit/skills/project/my-skill.md") is None
    assert migrations_mod._classify_path(".pkit/agents/project/my-agent.md") is None
    assert migrations_mod._classify_path(".pkit/scratchpad/active/note.md") is None
    assert migrations_mod._classify_path(".pkit/rules/project.md") is None


def test_classify_component_project_subdirs_excluded() -> None:
    assert (
        migrations_mod._classify_path(
            ".pkit/capabilities/evidence/project/manifest.yaml"
        )
        is None
    )
    assert (
        migrations_mod._classify_path(".pkit/adapters/claude-code/project/foo.json")
        is None
    )


def test_classify_non_pkit_returns_none() -> None:
    assert migrations_mod._classify_path("src/project_kit/cli.py") is None
    assert migrations_mod._classify_path("tests/test_foo.py") is None
    assert migrations_mod._classify_path("README.md") is None


# --- _is_migration_path ------------------------------------------------


def test_is_migration_path_recognises_scripts() -> None:
    assert migrations_mod._is_migration_path(".pkit/migrations/1.0.0/001-foo.sh")
    assert migrations_mod._is_migration_path(
        ".pkit/capabilities/evidence/migrations/1.0.0/001-foo.sh"
    )
    assert migrations_mod._is_migration_path(
        ".pkit/adapters/claude-code/migrations/1.1.0/002-bar.py"
    )


def test_is_migration_path_rejects_gitkeep() -> None:
    assert not migrations_mod._is_migration_path(
        ".pkit/capabilities/evidence/migrations/.gitkeep"
    )


def test_is_migration_path_rejects_non_pkit() -> None:
    assert not migrations_mod._is_migration_path("src/migrations/foo.sh")


# --- _migration_path_tier / _component ---------------------------------


def test_migration_path_tier_and_component() -> None:
    assert (
        migrations_mod._migration_path_tier(".pkit/migrations/1.0.0/001-foo.sh")
        == "backbone"
    )
    assert (
        migrations_mod._migration_path_component(
            ".pkit/capabilities/evidence/migrations/1.0.0/001-foo.sh"
        )
        == "evidence"
    )
    assert (
        migrations_mod._migration_path_tier(
            ".pkit/capabilities/evidence/migrations/1.0.0/001-foo.sh"
        )
        == "capability"
    )


# --- CoverageReport ----------------------------------------------------


def test_coverage_report_clean_when_no_triggers() -> None:
    report = CoverageReport(triggers=(), migrations=())
    assert report.is_covered is True
    assert report.uncovered_keys == []


def test_coverage_report_covered_when_migration_matches_trigger() -> None:
    report = CoverageReport(
        triggers=(
            DiffTrigger(
                kind="delete",
                path=".pkit/skills/core/old-skill.md",
                old_path=None,
                tier="backbone",
                component=None,
            ),
        ),
        migrations=(
            DiffMigration(
                path=".pkit/migrations/1.1.0/001-rename-skill.sh",
                tier="backbone",
                component=None,
            ),
        ),
    )
    assert report.is_covered is True


def test_coverage_report_uncovered_when_no_migration() -> None:
    report = CoverageReport(
        triggers=(
            DiffTrigger(
                kind="delete",
                path=".pkit/capabilities/evidence/skills/evidence-add.md",
                old_path=None,
                tier="capability",
                component="evidence",
            ),
        ),
        migrations=(),
    )
    assert report.is_covered is False
    assert report.uncovered_keys == [("capability", "evidence")]


def test_coverage_report_uncovered_when_migration_wrong_tier() -> None:
    """A backbone migration doesn't cover a capability trigger."""
    report = CoverageReport(
        triggers=(
            DiffTrigger(
                kind="rename",
                path=".pkit/capabilities/evidence/skills/evidence/add.md",
                old_path=".pkit/capabilities/evidence/skills/evidence-add.md",
                tier="capability",
                component="evidence",
            ),
        ),
        migrations=(
            DiffMigration(
                path=".pkit/migrations/1.1.0/001-something.sh",
                tier="backbone",
                component=None,
            ),
        ),
    )
    assert report.is_covered is False
    assert report.uncovered_keys == [("capability", "evidence")]


def test_coverage_report_multi_tier_partial() -> None:
    """A diff with triggers across tiers needs one migration per tier."""
    report = CoverageReport(
        triggers=(
            DiffTrigger(
                kind="rename",
                path=".pkit/skills/core/new.md",
                old_path=".pkit/skills/core/old.md",
                tier="backbone",
                component=None,
            ),
            DiffTrigger(
                kind="delete",
                path=".pkit/capabilities/evidence/skills/evidence-add.md",
                old_path=None,
                tier="capability",
                component="evidence",
            ),
        ),
        migrations=(
            DiffMigration(
                path=".pkit/migrations/1.1.0/001-rename.sh",
                tier="backbone",
                component=None,
            ),
        ),
    )
    assert report.is_covered is False
    assert report.uncovered_keys == [("capability", "evidence")]


# --- check_diff_coverage with monkeypatched git diff -------------------


def test_check_diff_coverage_clean(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No triggers + no migrations → covered."""
    monkeypatch.setattr(
        migrations_mod,
        "_git_diff_name_status",
        lambda root, base, **kw: [("A", ".pkit/skills/core/new-skill.md", None)],
    )
    report = check_diff_coverage(tmp_path, "origin/main")
    assert report.is_covered is True
    assert report.triggers == ()


def test_check_diff_coverage_detects_delete_trigger(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        migrations_mod,
        "_git_diff_name_status",
        lambda root, base, **kw: [("D", ".pkit/skills/core/old-skill.md", None)],
    )
    report = check_diff_coverage(tmp_path, "origin/main")
    assert len(report.triggers) == 1
    assert report.triggers[0].kind == "delete"
    assert report.is_covered is False


def test_check_diff_coverage_detects_rename_trigger(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        migrations_mod,
        "_git_diff_name_status",
        lambda root, base, **kw: [
            ("R", ".pkit/skills/core/schema/author.md", ".pkit/skills/core/schema-author.md"),
        ],
    )
    report = check_diff_coverage(tmp_path, "origin/main")
    assert len(report.triggers) == 1
    assert report.triggers[0].kind == "rename"
    assert report.triggers[0].path == ".pkit/skills/core/schema/author.md"
    assert report.triggers[0].old_path == ".pkit/skills/core/schema-author.md"


def test_check_diff_coverage_pairs_trigger_with_migration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A trigger + a same-tier migration in the diff → covered."""
    monkeypatch.setattr(
        migrations_mod,
        "_git_diff_name_status",
        lambda root, base, **kw: [
            ("D", ".pkit/skills/core/old.md", None),
            ("A", ".pkit/migrations/1.1.0/001-deprecate-skill.sh", None),
        ],
    )
    report = check_diff_coverage(tmp_path, "origin/main")
    assert len(report.triggers) == 1
    assert len(report.migrations) == 1
    assert report.is_covered is True


def test_check_diff_coverage_include_working_tree_flag_propagates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The include_working_tree kwarg threads through to the git diff call."""
    captured: dict = {}

    def fake_diff(root: Path, base: str, *, include_working_tree: bool = False):
        captured["include_working_tree"] = include_working_tree
        return []

    monkeypatch.setattr(migrations_mod, "_git_diff_name_status", fake_diff)
    check_diff_coverage(tmp_path, "origin/main", include_working_tree=True)
    assert captured["include_working_tree"] is True

    check_diff_coverage(tmp_path, "origin/main")
    assert captured["include_working_tree"] is False


def test_check_diff_coverage_project_subtrees_dont_trigger(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Adopter-owned subtrees never trigger migrations."""
    monkeypatch.setattr(
        migrations_mod,
        "_git_diff_name_status",
        lambda root, base, **kw: [
            ("D", ".pkit/decisions/project/PRJ-002-foo.md", None),
            ("R", ".pkit/scratchpad/active/note.md", ".pkit/scratchpad/done/note.md"),
        ],
    )
    report = check_diff_coverage(tmp_path, "origin/main")
    assert report.triggers == ()
    assert report.is_covered is True


# --- CLI integration ---------------------------------------------------


def test_cli_check_diff_passes_when_clean(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        migrations_mod,
        "_git_diff_name_status",
        lambda root, base, **kw: [("A", ".pkit/skills/core/added.md", None)],
    )
    # Set up a minimal target dir so find_target_root succeeds.
    (tmp_path / ".pkit").mkdir()
    (tmp_path / ".git").mkdir()
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        import shutil

        shutil.copytree(tmp_path / ".pkit", Path.cwd() / ".pkit", dirs_exist_ok=True)
        (Path.cwd() / ".git").mkdir(exist_ok=True)
        result = runner.invoke(main, ["migrations", "check-diff", "--base", "main"])
    assert result.exit_code == 0, result.output
    assert "No migration-triggering" in result.output


def test_cli_check_diff_fails_when_uncovered(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        migrations_mod,
        "_git_diff_name_status",
        lambda root, base, **kw: [("D", ".pkit/skills/core/old.md", None)],
    )
    (tmp_path / ".pkit").mkdir()
    (tmp_path / ".git").mkdir()
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        import shutil

        shutil.copytree(tmp_path / ".pkit", Path.cwd() / ".pkit", dirs_exist_ok=True)
        (Path.cwd() / ".git").mkdir(exist_ok=True)
        result = runner.invoke(main, ["migrations", "check-diff", "--base", "main"])
    assert result.exit_code != 0
    assert "UNCOVERED" in result.output
