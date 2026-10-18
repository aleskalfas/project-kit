"""Tests for `pkit migrations check-diff` and the coverage-check helpers."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from click.testing import CliRunner

from project_kit import migrations as migrations_mod
from project_kit.cli import main
from project_kit.default_branch import CHECK_BASE_ENV
from project_kit.migrations import (
    CoverageReport,
    DiffMigration,
    DiffTrigger,
    check_diff_coverage,
)
from tests.adopter_repo import GitRepo


def _make_repo(root: Path) -> None:
    """A real repository with one commit on `main`: the base the command resolves
    (COR-054) — the local `main`, with no remote — before the stubbed diff runs."""
    import subprocess

    identity = ["-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false"]
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=root, check=True)
    subprocess.run(
        ["git", *identity, "commit", "-q", "--allow-empty", "-m", "base"], cwd=root, check=True
    )


def _make_git_dir(root: Path) -> None:
    """Give `root` a structurally-real `.git/` (objects/ + refs/) so
    `find_target_root` resolves it. A bare/vestigial `.git` no longer qualifies
    (#787); these tests stub the git diff, so the `.git` is only a resolution
    marker."""
    (root / ".git" / "objects").mkdir(parents=True, exist_ok=True)
    (root / ".git" / "refs").mkdir(parents=True, exist_ok=True)


# --- _classify_path ----------------------------------------------------


def test_classify_backbone_core_record() -> None:
    assert migrations_mod._classify_path(".pkit/decisions/core/COR-005-bundle-pattern.md") == (
        "backbone",
        None,
    )


def test_classify_backbone_skill() -> None:
    assert migrations_mod._classify_path(".pkit/skills/core/decision-author.md") == (
        "backbone",
        None,
    )


def test_classify_workflow_legacy_path_is_backbone() -> None:
    """Per COR-027, leftover .pkit/workflow/ paths classify as backbone-tier
    (the area was retired; cleanup is backbone-level)."""
    assert migrations_mod._classify_path(".pkit/workflow/bundles/github-issues/skills/foo.md") == (
        "backbone",
        None,
    )


def test_classify_adapter() -> None:
    assert migrations_mod._classify_path(".pkit/adapters/claude-code/deploy-skills.sh") == (
        "adapter",
        "claude-code",
    )


def test_classify_capability() -> None:
    assert migrations_mod._classify_path(".pkit/capabilities/evidence/skills/evidence-add.md") == (
        "capability",
        "evidence",
    )


def test_classify_project_subtrees_excluded() -> None:
    assert migrations_mod._classify_path(".pkit/decisions/project/PRJ-001-foo.md") is None
    assert migrations_mod._classify_path(".pkit/skills/project/my-skill.md") is None
    assert migrations_mod._classify_path(".pkit/agents/project/my-agent.md") is None
    assert migrations_mod._classify_path(".pkit/scratchpad/active/note.md") is None
    assert migrations_mod._classify_path(".pkit/rules/project.md") is None


def test_classify_component_project_subdirs_excluded() -> None:
    assert (
        migrations_mod._classify_path(".pkit/capabilities/evidence/project/manifest.yaml") is None
    )
    assert migrations_mod._classify_path(".pkit/adapters/claude-code/project/foo.json") is None


def test_classify_non_pkit_returns_none() -> None:
    assert migrations_mod._classify_path("src/project_kit/cli.py") is None
    assert migrations_mod._classify_path("tests/test_foo.py") is None
    assert migrations_mod._classify_path("README.md") is None


# --- _is_decision_path -------------------------------------------------


def test_is_decision_path_recognises_decision_records() -> None:
    assert migrations_mod._is_decision_path(".pkit/decisions/core/COR-001-x.md")
    assert migrations_mod._is_decision_path(".pkit/decisions/project/PRJ-001-x.md")
    assert migrations_mod._is_decision_path(
        ".pkit/capabilities/project-management/decisions/DEC-033-rebind.md"
    )


def test_is_decision_path_rejects_non_decisions() -> None:
    assert not migrations_mod._is_decision_path(
        ".pkit/capabilities/project-management/scripts/move-issue.py"
    )
    assert not migrations_mod._is_decision_path(
        ".pkit/capabilities/project-management/schemas/workflow.yaml"
    )
    assert not migrations_mod._is_decision_path("src/project_kit/cli.py")


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
    assert not migrations_mod._is_migration_path(".pkit/capabilities/evidence/migrations/.gitkeep")


def test_is_migration_path_rejects_non_pkit() -> None:
    assert not migrations_mod._is_migration_path("src/migrations/foo.sh")


# --- _migration_path_tier / _component ---------------------------------


def test_migration_path_tier_and_component() -> None:
    assert migrations_mod._migration_path_tier(".pkit/migrations/1.0.0/001-foo.sh") == "backbone"
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


def test_check_diff_coverage_clean(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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


def test_check_diff_coverage_decision_rename_does_not_trigger(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Decision-record renames/deletes (COR / PRJ / DEC) are kit-owned
    reference content orphan-pruned by sync — never adopter-breaking, so they
    owe no migration. A real capability script rename in the same diff must
    still trigger (the exclusion is decision-specific, not blanket)."""
    monkeypatch.setattr(
        migrations_mod,
        "_git_diff_name_status",
        lambda root, base, **kw: [
            (  # capability DEC renumber — must NOT trigger
                "R",
                ".pkit/capabilities/project-management/decisions/DEC-033-rebind.md",
                ".pkit/capabilities/project-management/decisions/DEC-032-rebind.md",
            ),
            (  # core COR rename — must NOT trigger
                "R",
                ".pkit/decisions/core/COR-099-new.md",
                ".pkit/decisions/core/COR-099-old.md",
            ),
            (  # capability decision delete — must NOT trigger
                "D",
                ".pkit/capabilities/evidence/decisions/DEC-009-dropped.md",
                None,
            ),
            (  # a real capability script rename — MUST still trigger
                "R",
                ".pkit/capabilities/project-management/scripts/new.py",
                ".pkit/capabilities/project-management/scripts/old.py",
            ),
        ],
    )
    report = check_diff_coverage(tmp_path, "origin/main")
    assert len(report.triggers) == 1
    assert report.triggers[0].kind == "rename"
    assert report.triggers[0].path.endswith("scripts/new.py")
    assert report.triggers[0].component == "project-management"


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


def test_cli_check_diff_passes_when_clean(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        migrations_mod,
        "_git_diff_name_status",
        lambda root, base, **kw: [("A", ".pkit/skills/core/added.md", None)],
    )
    # Set up a minimal target dir so find_target_root succeeds. The `.git` must
    # be structurally real (objects/ + refs/) — a bare/vestigial `.git` no longer
    # resolves as a root (#787). The git diff itself is stubbed above.
    (tmp_path / ".pkit").mkdir()
    _make_git_dir(tmp_path)
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        import shutil

        shutil.copytree(tmp_path / ".pkit", Path.cwd() / ".pkit", dirs_exist_ok=True)
        _make_repo(Path.cwd())
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
    _make_git_dir(tmp_path)
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        import shutil

        shutil.copytree(tmp_path / ".pkit", Path.cwd() / ".pkit", dirs_exist_ok=True)
        _make_repo(Path.cwd())
        result = runner.invoke(main, ["migrations", "check-diff", "--base", "main"])
    assert result.exit_code != 0
    assert "UNCOVERED" in result.output


# --- a migration whose version is already released (COR-010; #1754) --------------------


_EVIDENCE = ".pkit/capabilities/evidence/package.yaml"
_SCRIPT = "#!/usr/bin/env bash\nset -euo pipefail\n"


def _package(name: str, version: str) -> str:
    return (
        f"schema_version: 1\ncomponent:\n  kind: capability\n  name: {name}\n  version: {version}\n"
    )


@pytest.fixture
def released(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> GitRepo:
    """A repository whose `main` records backbone 1.149.0, with a migration in its
    folder, and the evidence capability at 0.54.0; checked out on `topic`, cut from it."""
    monkeypatch.delenv(CHECK_BASE_ENV, raising=False)
    repo = GitRepo.init(tmp_path / "kit")
    repo.commit(
        "released",
        {
            ".pkit/VERSION": "1.149.0\n",
            ".pkit/migrations/backbone/1.149.0/001-shipped.sh": _SCRIPT,
            _EVIDENCE: _package("evidence", "0.54.0"),
        },
    )
    repo.git("checkout", "-q", "-b", "topic")
    monkeypatch.chdir(repo.root)
    return repo


def _check(*args: str) -> Any:
    return CliRunner().invoke(main, ["migrations", "check-diff", "--base", "main", *args])


def test_a_migration_in_a_released_folder_fails_the_check(released: GitRepo) -> None:
    released.commit("late", {".pkit/migrations/backbone/1.149.0/002-late.sh": _SCRIPT})
    result = _check()
    assert result.exit_code == 1, result.output
    assert (
        "[backbone] .pkit/migrations/backbone/1.149.0/002-late.sh: targets 1.149.0, but main "
        "already records backbone 1.149.0, so a project at 1.149.0 never runs it. Move it to "
        "1.150.0/ (`pkit new migration` without `--version` picks it)."
    ) in result.output
    assert "Verdict: RELEASED." in result.output
    # A folder below the released one is released too.
    released.commit("older", {".pkit/migrations/backbone/1.100.0/001-older.sh": _SCRIPT})
    assert "targets 1.100.0, but main already records" in _check().output


def test_a_migration_past_the_released_version_passes(released: GitRepo) -> None:
    released.commit("next", {".pkit/migrations/backbone/1.150.0/001-next.sh": _SCRIPT})
    result = _check()
    assert result.exit_code == 0, result.output
    assert "RELEASED" not in result.output
    # Uncommitted, it is judged the same with the working tree included.
    released.write({".pkit/migrations/backbone/1.149.0/002-late.sh": _SCRIPT})
    released.git("add", "-A")
    assert _check("--include-working-tree").exit_code == 1
    assert _check().exit_code == 0


def test_a_release_after_the_branch_was_cut_is_read_at_the_tip(released: GitRepo) -> None:
    """The branch point records 1.149.0, but the base's tip released 1.150.0 since: a
    folder 1.150.0/ the branch adds never runs for a project at it."""
    released.commit("next", {".pkit/migrations/backbone/1.150.0/001-next.sh": _SCRIPT})
    released.git("checkout", "-q", "main")
    released.commit("chore(release): v1.150.0", {".pkit/VERSION": "1.150.0\n"})
    released.git("checkout", "-q", "topic")
    result = _check()
    assert result.exit_code == 1, result.output
    assert "targets 1.150.0, but main already records backbone 1.150.0" in result.output
    assert "Move it to 1.151.0/" in result.output


def test_a_script_the_tip_already_holds_is_not_judged(released: GitRepo) -> None:
    """The change's own script, landed on the base already, as a stacked parent's is,
    and released since: the change did not bring it."""
    script = {".pkit/migrations/backbone/1.150.0/001-next.sh": _SCRIPT}
    released.commit("next", script)
    released.git("checkout", "-q", "main")
    released.commit("the parent lands", script)
    released.commit("chore(release): v1.150.0", {".pkit/VERSION": "1.150.0\n"})
    released.git("checkout", "-q", "topic")
    assert _check().exit_code == 0


def test_a_component_migration_is_judged_against_its_own_version(released: GitRepo) -> None:
    folder = ".pkit/capabilities/evidence/migrations"
    released.commit("late", {f"{folder}/0.54.0/001-late.sh": _SCRIPT})
    result = _check()
    assert result.exit_code == 1, result.output
    assert (
        f"[capability:evidence] {folder}/0.54.0/001-late.sh: targets 0.54.0, but main "
        "already records capability evidence 0.54.0"
    ) in result.output
    assert "Move it to 0.55.0/" in result.output
    released.git("rm", "-q", f"{folder}/0.54.0/001-late.sh")
    released.commit("moved on", {f"{folder}/0.55.0/001-late.sh": _SCRIPT})
    assert _check().exit_code == 0


def test_a_tier_the_tip_records_no_version_for_has_nothing_released(released: GitRepo) -> None:
    """A capability the change adds has shipped no version, so no folder of it is
    released."""
    released.commit(
        "a new capability",
        {
            ".pkit/capabilities/fresh/package.yaml": _package("fresh", "0.1.0"),
            ".pkit/capabilities/fresh/migrations/0.1.0/001-first.sh": _SCRIPT,
        },
    )
    assert _check().exit_code == 0


def test_a_script_moved_into_a_released_folder_fails_the_check(released: GitRepo) -> None:
    released.git("checkout", "-q", "main")
    released.commit("pending", {".pkit/migrations/backbone/1.150.0/001-pending.sh": _SCRIPT})
    released.git("checkout", "-q", "-B", "topic")
    released.git(
        "mv",
        ".pkit/migrations/backbone/1.150.0/001-pending.sh",
        ".pkit/migrations/backbone/1.149.0/002-pending.sh",
    )
    released.commit("moved back")
    result = _check()
    assert result.exit_code == 1, result.output
    assert "1.149.0/002-pending.sh: targets 1.149.0" in result.output


def test_a_script_the_project_receives_by_sync_is_not_judged(
    released: GitRepo, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An adopter's upgrade brings the methodology's scripts as synced copies: they are
    the methodology's, judged where it authors them."""
    released.commit("late", {".pkit/migrations/backbone/1.149.0/002-late.sh": _SCRIPT})
    synced = SimpleNamespace(is_synced_copy=lambda root, path: path.startswith(".pkit/migrations/"))
    monkeypatch.setattr(migrations_mod.lifecycle_ownership, "load_ownership", lambda root: synced)
    assert _check().exit_code == 0


def test_a_version_the_tip_records_in_no_readable_form_fails_the_check(
    released: GitRepo,
) -> None:
    released.git("checkout", "-q", "main")
    released.commit("broken", {".pkit/VERSION": "next\n"})
    released.git("checkout", "-q", "topic")
    released.commit("next", {".pkit/migrations/backbone/1.150.0/001-next.sh": _SCRIPT})
    result = _check()
    assert result.exit_code == 1, result.output
    assert (
        "[backbone] .pkit/migrations/backbone/1.150.0/001-next.sh: at main, .pkit/VERSION "
        "records no version in major.minor.patch form ('next'), so whether 1.150.0 is "
        "released cannot be told."
    ) in result.output


def test_landed_holds_added_scripts_and_scripts_moved_in(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        migrations_mod,
        "_git_diff_name_status",
        lambda root, base, **kw: [
            ("A", ".pkit/migrations/backbone/1.150.0/001-new.sh", None),
            (
                "R",
                ".pkit/migrations/backbone/1.149.0/002-moved.sh",
                ".pkit/migrations/backbone/1.150.0/002-moved.sh",
            ),
            ("M", ".pkit/migrations/backbone/1.140.0/001-edited.sh", None),
            ("D", ".pkit/migrations/backbone/1.150.0/003-gone.sh", None),
        ],
    )
    report = check_diff_coverage(tmp_path, "origin/main")
    assert report.landed == (
        ".pkit/migrations/backbone/1.150.0/001-new.sh",
        ".pkit/migrations/backbone/1.149.0/002-moved.sh",
    )
    assert report.triggers == ()


def test_the_target_never_names_a_released_minor() -> None:
    for released, own, folders, expected in [
        ("1.149.0", None, (), "1.150.0"),
        ("1.149.2", None, (), "1.150.0"),
        ("1.149.0", "1.149.0", (), "1.150.0"),
        ("1.149.0", "1.148.0", (), "1.150.0"),
        ("1.149.0", "1.151.1", (), "1.151.0"),
        ("1.149.0", None, ("1.150.0", "2.0.0"), "2.0.0"),
        ("1.149.0", None, ("1.152.0", "3.0.0"), "1.150.0"),
        ("0.54.0", None, ("1.0.0",), "1.0.0"),
        ("1.150.0-rc.1", None, (), "1.151.0"),
    ]:
        target = migrations_mod.migration_target(
            "backbone", released, "main", own=own, folders=folders
        )
        assert target.version == expected, (released, own, folders)
        assert migrations_mod.minor_of(target.version) > migrations_mod.minor_of(released)
