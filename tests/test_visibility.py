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
    read_backbone_manifest,
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


# --- runtime-ignore aggregation (ADR-009 Amendment 1) ------------------------

def _install_capability_with_runtime_ignore(
    root: Path, name: str, runtime_ignore: list[str]
) -> None:
    """Fabricate an installed capability whose package.yaml declares
    `runtime_ignore:`, and register it in the backbone manifest — mirroring how
    `repo` fabricates the adapter's `footprint:`."""
    cdir = root / ".pkit" / "capabilities" / name
    cdir.mkdir(parents=True)
    body = (
        f"schema_version: 1\ncomponent:\n  kind: capability\n  name: {name}\n"
        "  version: 0.1.0\nruntime_ignore:\n"
        + "".join(f"  - {p}\n" for p in runtime_ignore)
    )
    (cdir / "package.yaml").write_text(body, encoding="utf-8")
    manifest = read_backbone_manifest(root)
    assert manifest is not None
    manifest.components.append(ComponentRegistryEntry(
        kind="capability", name=name,
        manifest=f".pkit/capabilities/{name}/project/manifest.yaml"))
    write_backbone_manifest(root, manifest)


def test_runtime_ignore_includes_backbone_permissions_seam(repo: Path) -> None:
    # The core-level seam covers the backbone's own caches and the permissions
    # surface (no package.yaml — it piggybacks the seam).
    out = vis.runtime_ignore(repo)
    assert ".pkit/**/__pycache__/" in out
    assert ".pkit/permissions/project/diagnose-log.jsonl" in out
    assert ".pkit/permissions/project/diagnose.yaml" in out
    assert ".pkit/permissions/project/sandbox-provenance.yaml" in out


def test_runtime_ignore_aggregates_component_declaration(repo: Path) -> None:
    _install_capability_with_runtime_ignore(
        repo, "demo", [".pkit/capabilities/demo/project/run.log"])
    out = vis.runtime_ignore(repo)
    # The component's declared path is present, after the backbone seam.
    assert ".pkit/capabilities/demo/project/run.log" in out
    assert out[: len(vis._BACKBONE_RUNTIME_IGNORE)] == list(vis._BACKBONE_RUNTIME_IGNORE)


def test_runtime_ignore_is_deduped_and_order_stable(repo: Path) -> None:
    # A component echoing a backbone-seam path collapses to one entry, in order.
    _install_capability_with_runtime_ignore(
        repo, "dup", [".pkit/**/__pycache__/", ".pkit/capabilities/dup/x.log"])
    out = vis.runtime_ignore(repo)
    assert out.count(".pkit/**/__pycache__/") == 1
    assert out == vis._dedupe(out)  # idempotent


def test_runtime_ignore_tolerates_component_without_key(repo: Path) -> None:
    # The adapter in `repo` declares `footprint:` but no `runtime_ignore:` —
    # absence contributes nothing beyond the backbone seam.
    assert vis.runtime_ignore(repo) == list(vis._BACKBONE_RUNTIME_IGNORE)


# --- runtime-ignore renderer (ADR-009 Amendment 1, T2) -----------------------

def test_render_strips_pkit_prefix_for_nested_gitignore(repo: Path) -> None:
    # Patterns are stored repo-root-relative; the file lives at `.pkit/.gitignore`,
    # so the `.pkit/` prefix is stripped to match the nested file's directory.
    content = vis.render_runtime_ignore_content(repo)
    assert "permissions/project/diagnose.yaml" in content
    assert ".pkit/permissions/project/diagnose.yaml" not in content
    assert "**/__pycache__/" in content


def test_render_writes_file_and_returns_summary(repo: Path) -> None:
    out = vis.render_runtime_ignore(repo)
    gi = repo / ".pkit" / ".gitignore"
    assert gi.is_file()
    assert "pkit-owned" in gi.read_text(encoding="utf-8")
    # Summary names the rendered path, pattern count, component count.
    assert ".pkit/.gitignore" in out
    assert "pattern(s)" in out and "component(s)" in out


def test_render_is_idempotent_byte_identical(repo: Path) -> None:
    vis.render_runtime_ignore(repo)
    first = (repo / ".pkit" / ".gitignore").read_text(encoding="utf-8")
    vis.render_runtime_ignore(repo)
    second = (repo / ".pkit" / ".gitignore").read_text(encoding="utf-8")
    assert first == second


def test_render_dry_run_writes_nothing(repo: Path) -> None:
    gi = repo / ".pkit" / ".gitignore"
    assert not gi.exists()
    out = vis.render_runtime_ignore(repo, dry_run=True)
    assert not gi.exists()  # nothing written
    assert "would render" in out
    assert "pattern(s)" in out and "component(s)" in out


def test_render_drops_uninstalled_component_lines(repo: Path) -> None:
    # A component's runtime_ignore lines appear while installed...
    _install_capability_with_runtime_ignore(
        repo, "demo", [".pkit/capabilities/demo/project/run.log"])
    vis.render_runtime_ignore(repo)
    assert "capabilities/demo/project/run.log" in (
        repo / ".pkit" / ".gitignore").read_text(encoding="utf-8")
    # ...and are simply absent on the next render once it's gone (wholesale
    # regeneration — no orphan reconciliation). Drop it from the manifest.
    manifest = read_backbone_manifest(repo)
    assert manifest is not None
    manifest.components = [c for c in manifest.components if c.name != "demo"]
    write_backbone_manifest(repo, manifest)
    vis.render_runtime_ignore(repo)
    assert "capabilities/demo/project/run.log" not in (
        repo / ".pkit" / ".gitignore").read_text(encoding="utf-8")


def test_render_component_count_reflects_declaring_components(repo: Path) -> None:
    # Backbone seam alone = 1 component.
    assert vis._runtime_ignore_component_count(repo) == 1
    # Adding a capability that declares runtime_ignore bumps the count.
    _install_capability_with_runtime_ignore(
        repo, "demo", [".pkit/capabilities/demo/project/run.log"])
    assert vis._runtime_ignore_component_count(repo) == 2


def test_rendered_gitignore_actually_matches_declared_path(repo: Path) -> None:
    # The rendered file must *actually ignore* a declared path. Render it, then
    # ask git itself whether a declared runtime-local path is ignored.
    _install_capability_with_runtime_ignore(
        repo, "demo", [".pkit/capabilities/demo/project/run.log"])
    vis.render_runtime_ignore(repo)
    target = repo / ".pkit" / "capabilities" / "demo" / "project" / "run.log"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("runtime\n", encoding="utf-8")
    # git check-ignore exits 0 when the path IS ignored.
    res = subprocess.run(
        ["git", "check-ignore", "-q", ".pkit/capabilities/demo/project/run.log"],
        cwd=repo, capture_output=True, text=True, check=False,
    )
    assert res.returncode == 0, "rendered .pkit/.gitignore must ignore the declared path"
    # And a non-declared sibling is NOT ignored.
    res2 = subprocess.run(
        ["git", "check-ignore", "-q", ".pkit/capabilities/demo/project/keep.txt"],
        cwd=repo, capture_output=True, text=True, check=False,
    )
    assert res2.returncode == 1


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
