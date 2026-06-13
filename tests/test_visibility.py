"""Tests for `pkit visibility` + `pkit untrack` (per ADR-009).

Exercised against throwaway git repos so the real mutations — info/exclude
writes and `git rm --cached` — run for real, never against the source tree.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import click
import pytest
from click.testing import CliRunner

from project_kit import visibility as vis
from project_kit.cli import main
from project_kit.manifest import (
    BackboneManifest,
    ComponentRegistryEntry,
    write_backbone_manifest,
)


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=root, capture_output=True, text=True, check=True
    ).stdout


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A git repo with a fake pkit footprint: backbone `.pkit/`, a claude-code
    adapter declaring `.claude/{skills,agents}`, and some tracked footprint files."""
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    _git(tmp_path, "config", "user.email", "t@t")
    _git(tmp_path, "config", "user.name", "t")

    adir = tmp_path / ".pkit" / "adapters" / "claude-code"
    adir.mkdir(parents=True)
    (adir / "package.yaml").write_text(
        "schema_version: 1\ncomponent:\n  kind: adapter\n  name: claude-code\n"
        "  version: 0.4.0\nfootprint:\n  - .claude/skills\n  - .claude/agents\n",
        encoding="utf-8",
    )
    write_backbone_manifest(
        tmp_path,
        BackboneManifest(
            backbone_version="1.0.0",
            components=[ComponentRegistryEntry(
                kind="adapter", name="claude-code",
                manifest=".pkit/adapters/claude-code/project/manifest.yaml")],
        ),
    )
    (tmp_path / ".claude" / "agents").mkdir(parents=True)
    (tmp_path / ".claude" / "agents" / "critic.md").write_text("agent\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("project\n", encoding="utf-8")  # non-footprint
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-qm", "init")
    return tmp_path


# --- footprint aggregation ---------------------------------------------------

def test_footprint_aggregates_backbone_and_adapter(repo: Path) -> None:
    assert vis.footprint(repo) == [".pkit/", ".claude/skills", ".claude/agents"]


# --- info/exclude region + shared/private ------------------------------------

def _exclude(repo: Path) -> str:
    p = repo / ".git" / "info" / "exclude"
    return p.read_text(encoding="utf-8") if p.is_file() else ""


def test_private_writes_region_and_untracks(repo: Path) -> None:
    vis.set_visibility(repo, "private", confirm=lambda _m: True)
    # info/exclude carries the footprint region.
    ex = _exclude(repo)
    assert ".pkit/" in ex and ".claude/agents" in ex and "pkit footprint" in ex
    # footprint files no longer tracked, but working copies remain.
    assert vis._tracked_footprint(repo, vis.footprint(repo)) == []
    assert (repo / ".claude" / "agents" / "critic.md").is_file()
    # non-footprint file is untouched.
    assert "README.md" in _git(repo, "ls-files")


def test_private_is_idempotent(repo: Path) -> None:
    vis.set_visibility(repo, "private", confirm=lambda _m: True)
    first = _exclude(repo)
    vis.set_visibility(repo, "private", confirm=lambda _m: True)
    assert _exclude(repo) == first  # region replaced, not duplicated
    assert _exclude(repo).count(vis._BEGIN) == 1


def test_shared_clears_region(repo: Path) -> None:
    vis.set_visibility(repo, "private", confirm=lambda _m: True)
    assert vis._BEGIN in _exclude(repo)
    vis.set_visibility(repo, "shared")
    assert vis._BEGIN not in _exclude(repo)


def test_shared_preserves_hand_added_exclude_lines(repo: Path) -> None:
    excl = repo / ".git" / "info" / "exclude"
    excl.write_text("# my own\n*.log\n", encoding="utf-8")
    vis.set_visibility(repo, "private", confirm=lambda _m: True)
    vis.set_visibility(repo, "shared")
    text = _exclude(repo)
    assert "*.log" in text and vis._BEGIN not in text  # adopter lines survive


def test_private_dry_run_changes_nothing(repo: Path) -> None:
    before_excl = _exclude(repo)
    before_tracked = vis._tracked_footprint(repo, vis.footprint(repo))
    out = vis.set_visibility(repo, "private", dry_run=True, confirm=lambda _m: True)
    assert _exclude(repo) == before_excl
    assert vis._tracked_footprint(repo, vis.footprint(repo)) == before_tracked
    assert "would write" in out


# --- untrack guards ----------------------------------------------------------

def test_untrack_refuses_mid_merge(repo: Path) -> None:
    (repo / ".git" / "MERGE_HEAD").write_text("deadbeef\n", encoding="utf-8")
    with pytest.raises(click.ClickException, match="merge is in progress"):
        vis.untrack(repo, confirm=lambda _m: True)


def test_untrack_refuses_staged_footprint(repo: Path) -> None:
    (repo / ".claude" / "agents" / "critic.md").write_text("changed\n", encoding="utf-8")
    _git(repo, "add", ".claude/agents/critic.md")
    with pytest.raises(click.ClickException, match="staged changes"):
        vis.untrack(repo, confirm=lambda _m: True)


def test_untrack_cancel_leaves_files_tracked(repo: Path) -> None:
    out = vis.untrack(repo, confirm=lambda _m: False)
    assert "cancelled" in out
    assert vis._tracked_footprint(repo, vis.footprint(repo))  # still tracked


def test_untrack_dry_run_lists_without_removing(repo: Path) -> None:
    before = vis._tracked_footprint(repo, vis.footprint(repo))
    out = vis.untrack(repo, dry_run=True)
    assert "dry-run" in out
    assert vis._tracked_footprint(repo, vis.footprint(repo)) == before


# --- CLI ---------------------------------------------------------------------

def test_cli_visibility_status(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(repo)
    result = CliRunner().invoke(main, ["visibility"])
    assert result.exit_code == 0, result.output
    assert "shared" in result.output
    assert ".claude/agents" in result.output


def test_cli_visibility_untrack_subcommand(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(repo)
    # dry-run lists tracked footprint files without removing them.
    result = CliRunner().invoke(main, ["visibility", "untrack", "--dry-run"])
    assert result.exit_code == 0, result.output
    assert "dry-run" in result.output
    assert vis._tracked_footprint(repo, vis.footprint(repo))  # still tracked
    # there is no bare top-level `untrack` anymore — it lives under `visibility`.
    assert CliRunner().invoke(main, ["untrack"]).exit_code != 0


def test_cli_visibility_never_load_bearing(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from project_kit import cli_render
    monkeypatch.chdir(repo)
    always = CliRunner().invoke(main, ["--color", "always", "visibility"]).output
    never = CliRunner().invoke(main, ["--color", "never", "visibility"]).output
    assert "\033[" in always
    assert cli_render.strip_ansi(always) == never
