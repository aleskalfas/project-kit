"""Tests for the surface-without-changeset CI guard (PRJ-002): surface
detection + the escape hatches."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from click.testing import CliRunner

from project_kit import changesets, release
from project_kit.cli import main


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


# --- The release-PR exemption (#503): a release-apply footprint is exempt ---


def _apply_release_footprint(
    source_kit: Path, *, extra_files: dict[str, str] | None = None
) -> None:
    """Stage exactly `pkit release apply`'s output on the current branch.

    Bumps `.pkit/VERSION`, bumps the adapter's `package.yaml` version, prepends
    `CHANGELOG.md`, and deletes any pending changesets — the diff a release PR
    carries. `extra_files` injects unrelated edits to build a *mixed* diff.
    """
    repo = source_kit.parent

    (source_kit / "VERSION").write_text("1.6.0\n", encoding="utf-8")

    pkg = source_kit / "adapters" / "claude-code" / "package.yaml"
    pkg.write_text(
        "schema_version: 1\ncomponent:\n  kind: adapter\n  name: claude-code\n"
        '  version: 0.6.0\nrequires_backbone: ">=0.1.0,<2.0.0"\n',
        encoding="utf-8",
    )

    (repo / "CHANGELOG.md").write_text(
        "# Changelog\n\n## 1.6.0 — 2026-07-07\n\n### Changed\n\n- A release.\n",
        encoding="utf-8",
    )

    for cs in changesets.unreleased_dir(repo).glob("*.yaml"):
        cs.unlink()

    for relpath, content in (extra_files or {}).items():
        target = repo / relpath
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "chore(release): v1.6.0")


def test_release_shaped_diff_is_exempt_without_a_label(tmp_path: Path) -> None:
    """A pure release-apply footprint passes the guard with no label / changeset."""
    source_kit = _make_repo(tmp_path)
    # A pending changeset that the release consumes (deleted in the footprint).
    _add_changeset(source_kit, "backbone", "minor")
    repo = source_kit.parent
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "add changeset")

    _apply_release_footprint(source_kit)

    result = release.check_changesets(source_kit, "main")
    assert release.is_release_diff(source_kit, "main")
    assert result.release_exempt
    assert result.ok


def test_normal_surface_change_still_needs_a_changeset(tmp_path: Path) -> None:
    """A plain `src/` edit is not release-shaped and still fails with no changeset."""
    source_kit = _make_repo(tmp_path)
    _commit_change(source_kit, "src/project_kit/foo.py")
    assert not release.is_release_diff(source_kit, "main")
    result = release.check_changesets(source_kit, "main")
    assert not result.release_exempt
    assert result.missing == ["backbone"]
    assert not result.ok


def test_mixed_release_plus_src_edit_is_not_exempt(tmp_path: Path) -> None:
    """Release footprint PLUS an unrelated `src/` edit must NOT be exempted —
    the exemption cannot smuggle real surface through."""
    source_kit = _make_repo(tmp_path)
    _apply_release_footprint(
        source_kit, extra_files={"src/project_kit/foo.py": "real surface change\n"}
    )
    assert not release.is_release_diff(source_kit, "main")
    result = release.check_changesets(source_kit, "main")
    assert not result.release_exempt
    assert "backbone" in result.missing
    assert not result.ok


def test_release_shaped_manifest_with_extra_line_is_not_exempt(tmp_path: Path) -> None:
    """A `package.yaml` whose diff touches more than version-state lines is a
    real manifest edit, not release-shaped."""
    source_kit = _make_repo(tmp_path)
    repo = source_kit.parent

    (source_kit / "VERSION").write_text("1.6.0\n", encoding="utf-8")
    pkg = source_kit / "adapters" / "claude-code" / "package.yaml"
    # Adds a `description:` line alongside the version bump — not version-state.
    pkg.write_text(
        "schema_version: 1\ncomponent:\n  kind: adapter\n  name: claude-code\n"
        '  version: 0.6.0\n  description: new\nrequires_backbone: ">=0.1.0,<2.0.0"\n',
        encoding="utf-8",
    )
    (repo / "CHANGELOG.md").write_text(
        "# Changelog\n\n## 1.6.0 — 2026-07-07\n\n### Changed\n\n- A release.\n",
        encoding="utf-8",
    )
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "chore(release): v1.6.0")

    assert not release.is_release_diff(source_kit, "main")
    result = release.check_changesets(source_kit, "main")
    assert not result.release_exempt


def test_docs_only_diff_is_not_a_release(tmp_path: Path) -> None:
    """A non-surface, non-footprint diff is not release-shaped (and needs no
    exemption — the guard already passes it)."""
    source_kit = _make_repo(tmp_path)
    _commit_change(source_kit, "docs/notes.md")
    assert not release.is_release_diff(source_kit, "main")
    result = release.check_changesets(source_kit, "main")
    assert not result.release_exempt
    assert result.ok  # not surface at all


# --- The root the guard reads (#877): the working directory, not the checkout
# that owns the interpreter ----------------------------------------------------


def _make_checkout_with_worktree(tmp_path: Path) -> tuple[Path, Path]:
    """A project-kit-shaped checkout on `main` plus a git worktree of it on a
    branch that adds a capability the checkout does not have, and touches it.

    Returns `(checkout, worktree)`. The checkout carries `.pkit/decisions/` so
    `source_checkout_root()` accepts it as the tree owning the interpreter.
    """
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    _make_repo(checkout)
    (checkout / ".pkit" / "decisions").mkdir()
    _git(checkout, "add", "-A")
    _git(checkout, "checkout", "-q", "main")

    worktree = tmp_path / "worktree"
    _git(checkout, "worktree", "add", "-q", "-b", "wt", str(worktree), "main")
    extra = worktree / ".pkit" / "capabilities" / "extra"
    extra.mkdir(parents=True)
    (extra / "package.yaml").write_text(
        "schema_version: 1\ncomponent:\n  kind: capability\n  name: extra\n"
        '  version: 0.1.0\nrequires_backbone: ">=0.1.0,<2.0.0"\n',
        encoding="utf-8",
    )
    (extra / "README.md").write_text("extra\n", encoding="utf-8")
    _git(worktree, "add", "-A")
    _git(worktree, "commit", "-q", "-m", "add extra capability")
    return checkout, worktree


def _point_interpreter_at(monkeypatch, checkout: Path) -> None:
    """Make `install.source_checkout_root()` derive `checkout` from `__file__` —
    the editable-install shape where the module lives inside one fixed tree."""
    from project_kit import install

    monkeypatch.setattr(install, "__file__", str(checkout / "src" / "project_kit" / "install.py"))


def test_guard_reads_the_worktree_at_cwd_not_the_interpreter_checkout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """From a worktree, `release check` diffs and discovers components in the
    worktree — the `extra` capability exists only there — and says which tree it
    is operating on."""


    checkout, worktree = _make_checkout_with_worktree(tmp_path)
    _point_interpreter_at(monkeypatch, checkout)
    monkeypatch.chdir(worktree)

    result = CliRunner().invoke(main, ["release", "check", "--base", "main"])

    assert result.exit_code == 1, result.output
    assert "changeset guard: touched extra" in result.stdout
    assert "surface change without a changeset for: extra" in result.output
    assert "note: operating on" in result.stderr
    assert str(worktree.resolve()) in result.stderr
    assert str(checkout.resolve()) in result.stderr
    assert "note:" not in result.stdout


def test_guard_from_the_checkout_itself_is_silent_and_unchanged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Self-host / dev live-edit: cwd is the checkout, both roots coincide — no
    notice, and the worktree-only component is invisible."""


    checkout, _worktree = _make_checkout_with_worktree(tmp_path)
    _point_interpreter_at(monkeypatch, checkout)
    monkeypatch.chdir(checkout)

    result = CliRunner().invoke(main, ["release", "check", "--base", "main"])

    assert result.exit_code == 0, result.output
    assert "no surface-touched components" in result.stdout
    assert result.stderr == ""
