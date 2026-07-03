"""Tests for the surface-without-changeset CI guard (PRJ-002): surface
detection + the escape hatches."""

from __future__ import annotations

import subprocess
from pathlib import Path

from project_kit import changesets, release


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


def _make_repo(tmp_path: Path) -> Path:
    """A git repo with a source kit + one component, committed as `main`."""
    repo = tmp_path
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "T")

    source_kit = repo / ".pkit"
    (source_kit / "cli").mkdir(parents=True)
    (source_kit / "VERSION").write_text("1.5.0\n", encoding="utf-8")
    (source_kit / "cli" / "README.md").write_text("cli spec\n", encoding="utf-8")

    adapter = source_kit / "adapters" / "claude-code"
    adapter.mkdir(parents=True)
    (adapter / "package.yaml").write_text(
        "schema_version: 1\ncomponent:\n  kind: adapter\n  name: claude-code\n"
        '  version: 0.5.0\nrequires_backbone: ">=0.1.0,<2.0.0"\n',
        encoding="utf-8",
    )
    (repo / "src").mkdir()
    (repo / "src" / "seed.txt").write_text("x\n", encoding="utf-8")

    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "seed")
    _git(repo, "branch", "-M", "main")
    _git(repo, "checkout", "-q", "-b", "feature")
    return source_kit


def _commit_change(source_kit: Path, relpath: str, content: str = "changed\n") -> None:
    repo = source_kit.parent
    target = repo / relpath
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", f"touch {relpath}")


def _add_changeset(source_kit: Path, component: str, kind: str) -> None:
    directory = changesets.unreleased_dir(source_kit.parent)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{component}-{kind}.yaml").write_text(
        f"component: {component}\nkind: {kind}\nbody: note\n", encoding="utf-8"
    )


def test_touched_backbone_via_src_change_without_changeset_fails(tmp_path: Path) -> None:
    source_kit = _make_repo(tmp_path)
    _commit_change(source_kit, "src/project_kit/foo.py")
    result = release.check_changesets(source_kit, "main")
    assert result.touched == ["backbone"]
    assert result.missing == ["backbone"]
    assert not result.ok


def test_touched_backbone_with_changeset_passes(tmp_path: Path) -> None:
    source_kit = _make_repo(tmp_path)
    _add_changeset(source_kit, "backbone", "minor")
    _commit_change(source_kit, "src/project_kit/foo.py")
    result = release.check_changesets(source_kit, "main")
    assert result.ok


def test_none_changeset_satisfies_the_guard(tmp_path: Path) -> None:
    """The `none` escape hatch: a declared non-surface change still counts."""
    source_kit = _make_repo(tmp_path)
    _add_changeset(source_kit, "backbone", "none")
    _commit_change(source_kit, ".pkit/cli/README.md")
    result = release.check_changesets(source_kit, "main")
    assert result.touched == ["backbone"]
    assert result.ok


def test_skip_flag_passes_unconditionally(tmp_path: Path) -> None:
    source_kit = _make_repo(tmp_path)
    _commit_change(source_kit, "src/project_kit/foo.py")
    result = release.check_changesets(source_kit, "main", skip=True)
    assert result.skipped
    assert result.ok


def test_component_subtree_touch_requires_component_changeset(tmp_path: Path) -> None:
    source_kit = _make_repo(tmp_path)
    _commit_change(source_kit, ".pkit/adapters/claude-code/new-file.md")
    result = release.check_changesets(source_kit, "main")
    assert result.touched == ["claude-code"]
    assert result.missing == ["claude-code"]


def test_untracked_surface_path_is_not_flagged(tmp_path: Path) -> None:
    """A change outside every surface prefix / subtree does not trip the guard
    (documented false-negative territory — here `docs/` is not surface)."""
    source_kit = _make_repo(tmp_path)
    _commit_change(source_kit, "docs/notes.md")
    result = release.check_changesets(source_kit, "main")
    assert result.touched == []
    assert result.ok


def test_touched_components_maps_prefixes_and_subtrees(tmp_path: Path) -> None:
    source_kit = _make_repo(tmp_path)
    components = changesets.discover_components(source_kit)
    files = [
        ".pkit/cli/README.md",  # backbone surface prefix
        ".pkit/adapters/claude-code/package.yaml",  # component subtree
        "README.md",  # neither
    ]
    touched = release.touched_components(components, files)
    assert set(touched) == {"backbone", "claude-code"}
