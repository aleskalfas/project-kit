"""The agent workspace (#1043): `init` / `sync` create `.agent-workspace/` and its
local git exclusion idempotently, and `pkit status` reports both.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from click.testing import CliRunner

from project_kit import sync, workspace
from project_kit.cli import status
from tests.adopter_repo import GitRepo, MakeAdopterRepo

WS = workspace.WORKSPACE_DIR


def _entry_lines(exclude: Path) -> list[str]:
    return [line for line in exclude.read_text(encoding="utf-8").splitlines() if line.strip("/") == WS]


def _ignored(root: Path) -> bool:
    result = subprocess.run(
        ["git", "-C", str(root), "check-ignore", "-q", f"{WS}/"], check=False
    )
    return result.returncode == 0


# --- create and exclude --------------------------------------------------------


def test_init_creates_the_workspace_and_excludes_it(make_adopter_repo: MakeAdopterRepo) -> None:
    root = make_adopter_repo().root

    assert (root / WS).is_dir()
    assert _entry_lines(root / ".git" / "info" / "exclude") == [workspace.EXCLUDE_ENTRY]
    assert _ignored(root)


def test_a_rerun_is_a_no_op(make_adopter_repo: MakeAdopterRepo) -> None:
    root = make_adopter_repo().root
    exclude = root / ".git" / "info" / "exclude"
    before = exclude.read_text(encoding="utf-8")

    lines = workspace.ensure(root)

    assert [verb for verb, _ in lines] == ["unchanged", "unchanged"]
    assert exclude.read_text(encoding="utf-8") == before


def test_sync_restores_a_missing_folder_and_entry(make_adopter_repo: MakeAdopterRepo) -> None:
    root = make_adopter_repo().root
    exclude = root / ".git" / "info" / "exclude"
    (root / WS).rmdir()
    exclude.write_text("# nothing here\n", encoding="utf-8")

    sync.run_sync(root)

    assert (root / WS).is_dir()
    assert _entry_lines(exclude) == [workspace.EXCLUDE_ENTRY]
    assert exclude.read_text(encoding="utf-8").startswith("# nothing here\n")


@pytest.mark.parametrize("spelling", [".agent-workspace/", ".agent-workspace", "/.agent-workspace"])
def test_an_equivalent_line_counts_as_the_entry(tmp_path: Path, spelling: str) -> None:
    repo = GitRepo.init(tmp_path / "repo")
    exclude = repo.root / ".git" / "info" / "exclude"
    exclude.write_text(f"{spelling}\n", encoding="utf-8")

    workspace.ensure(repo.root)

    assert exclude.read_text(encoding="utf-8") == f"{spelling}\n"


def test_an_exclude_file_without_a_trailing_newline_is_appended_cleanly(tmp_path: Path) -> None:
    repo = GitRepo.init(tmp_path / "repo")
    exclude = repo.root / ".git" / "info" / "exclude"
    exclude.write_text("*.log", encoding="utf-8")

    workspace.ensure(repo.root)

    lines = exclude.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "*.log"
    assert lines[-1] == workspace.EXCLUDE_ENTRY
    assert _ignored(repo.root)


def test_a_worktree_is_excluded_through_the_common_git_directory(tmp_path: Path) -> None:
    main = GitRepo.init(tmp_path / "main")
    main.commit("initial", {"README.md": "hello\n"})
    worktree = tmp_path / "wt"
    main.git("worktree", "add", "-q", "-b", "topic", str(worktree))

    lines = workspace.ensure(worktree)

    assert (worktree / WS).is_dir()
    assert _entry_lines(main.root / ".git" / "info" / "exclude") == [workspace.EXCLUDE_ENTRY]
    assert _ignored(worktree)
    # The exclude file is shown by its absolute path: it lives outside the worktree.
    assert any(str(main.root.resolve() / ".git" / "info" / "exclude") in detail for _, detail in lines)
    # The main checkout reads the same entry, for its own folder at its own root.
    assert _ignored(main.root)


def test_outside_a_git_repository_the_folder_is_created_and_the_exclusion_skipped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))
    project = tmp_path / "project"
    project.mkdir()

    lines = workspace.ensure(project)

    assert (project / WS).is_dir()
    verb, detail = lines[1]
    assert verb == "skipped"
    assert "not a git repository" in detail


def test_dry_run_writes_nothing(tmp_path: Path) -> None:
    repo = GitRepo.init(tmp_path / "repo")
    exclude = repo.root / ".git" / "info" / "exclude"
    before = exclude.read_text(encoding="utf-8")

    lines = workspace.ensure(repo.root, dry_run=True)

    assert [verb for verb, _ in lines] == ["would create", "would exclude"]
    assert not (repo.root / WS).exists()
    assert exclude.read_text(encoding="utf-8") == before


# --- pkit status -----------------------------------------------------------------


def _status_output(monkeypatch: pytest.MonkeyPatch) -> str:
    monkeypatch.setenv("PKIT_SOURCE_BIN", "/fake/pkit")
    result = CliRunner().invoke(status, [])
    assert result.exit_code == 0, result.output
    return result.output


def _workspace_line(output: str) -> str:
    return next(line for line in output.splitlines() if "Agent workspace:" in line)


def test_status_reports_a_present_excluded_workspace(
    make_adopter_repo: MakeAdopterRepo, monkeypatch: pytest.MonkeyPatch
) -> None:
    make_adopter_repo()

    line = _workspace_line(_status_output(monkeypatch))

    assert f"{WS}/" in line
    assert "present, excluded from git" in line
    assert "pkit sync" not in line


def test_status_names_sync_when_the_folder_is_missing(
    make_adopter_repo: MakeAdopterRepo, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = make_adopter_repo().root
    (root / WS).rmdir()

    line = _workspace_line(_status_output(monkeypatch))

    assert "missing, excluded from git" in line
    assert "run `pkit sync`" in line


def test_status_names_sync_when_the_folder_is_not_excluded(
    make_adopter_repo: MakeAdopterRepo, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = make_adopter_repo().root
    (root / ".git" / "info" / "exclude").write_text("", encoding="utf-8")

    line = _workspace_line(_status_output(monkeypatch))

    assert "present, NOT excluded from git" in line
    assert "run `pkit sync`" in line
