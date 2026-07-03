"""Tests for the release step: compute, write, broaden-at-release, changelog,
and consumption (PRJ-002 D3/D4). Plus a cutover check that the legacy
`version bump` path still works alongside the release path."""

from __future__ import annotations

import subprocess
from datetime import date
from pathlib import Path

import click
import pytest

from project_kit import changesets, release, versioning


def _make_kit(tmp_path: Path, backbone: str = "1.5.0") -> Path:
    """A source kit in a git repo (so `tag_version` has a HEAD to tag)."""
    repo = tmp_path
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "t@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "T"], cwd=repo, check=True)

    source_kit = repo / ".pkit"
    source_kit.mkdir()
    (source_kit / "VERSION").write_text(f"{backbone}\n", encoding="utf-8")

    adapter = source_kit / "adapters" / "claude-code"
    adapter.mkdir(parents=True)
    (adapter / "package.yaml").write_text(
        "schema_version: 1\n"
        "component:\n"
        "  kind: adapter\n"
        "  name: claude-code\n"
        "  version: 0.5.0\n"
        'requires_backbone: ">=0.1.0,<1.6.0"\n',
        encoding="utf-8",
    )
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "seed"], cwd=repo, check=True)
    return source_kit


def _add(source_kit: Path, component: str, kind: str, body: str, name: str) -> None:
    directory = changesets.unreleased_dir(source_kit.parent)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / name).write_text(
        f"component: {component}\nkind: {kind}\nbody: {body}\n", encoding="utf-8"
    )


def test_compute_takes_highest_segment_per_component(tmp_path: Path) -> None:
    source_kit = _make_kit(tmp_path)
    _add(source_kit, "backbone", "patch", "a small fix", "a.yaml")
    _add(source_kit, "backbone", "minor", "a new command", "b.yaml")

    plan = release.compute_release(source_kit)
    backbone = plan.backbone
    assert backbone is not None
    assert backbone.segment == "minor"
    assert backbone.new_version == "1.6.0"
    assert backbone.notes == ["a small fix", "a new command"]


def test_compute_computes_each_tier_independently(tmp_path: Path) -> None:
    source_kit = _make_kit(tmp_path)
    _add(source_kit, "backbone", "minor", "backbone change", "a.yaml")
    _add(source_kit, "claude-code", "patch", "adapter fix", "b.yaml")

    plan = release.compute_release(source_kit)
    by_name = {r.component.name: r for r in plan.releases}
    assert by_name["backbone"].new_version == "1.6.0"
    assert by_name["claude-code"].new_version == "0.5.1"


def test_compute_none_only_component_does_not_move(tmp_path: Path) -> None:
    source_kit = _make_kit(tmp_path)
    _add(source_kit, "backbone", "none", "docs only", "a.yaml")
    plan = release.compute_release(source_kit)
    assert plan.is_empty
    assert len(plan.consumed) == 1  # still consumed


def test_compute_refuses_unknown_component(tmp_path: Path) -> None:
    source_kit = _make_kit(tmp_path)
    _add(source_kit, "nonexistent", "minor", "x", "a.yaml")
    with pytest.raises(click.ClickException, match="unknown component"):
        release.compute_release(source_kit)


def test_apply_writes_backbone_version_and_broadens(tmp_path: Path) -> None:
    source_kit = _make_kit(tmp_path)
    _add(source_kit, "backbone", "minor", "a new command", "a.yaml")

    plan = release.compute_release(source_kit)
    release.apply_release(source_kit, plan, tag=False)

    assert (source_kit / "VERSION").read_text().strip() == "1.6.0"
    # Broaden-at-release (D4): the adapter's `<1.6.0` no longer covers 1.6.0,
    # so it broadens to `<1.7.0`.
    pkg = (source_kit / "adapters" / "claude-code" / "package.yaml").read_text()
    assert 'requires_backbone: ">=0.1.0,<1.7.0"' in pkg


def test_apply_writes_component_version_line(tmp_path: Path) -> None:
    source_kit = _make_kit(tmp_path)
    _add(source_kit, "claude-code", "minor", "adapter feature", "a.yaml")

    plan = release.compute_release(source_kit)
    release.apply_release(source_kit, plan, tag=False)

    pkg = (source_kit / "adapters" / "claude-code" / "package.yaml").read_text()
    assert "  version: 0.6.0\n" in pkg
    # schema_version untouched.
    assert "schema_version: 1\n" in pkg
    # Backbone unmoved → no tag path; VERSION unchanged.
    assert (source_kit / "VERSION").read_text().strip() == "1.5.0"


def test_apply_generates_changelog_from_notes(tmp_path: Path) -> None:
    source_kit = _make_kit(tmp_path)
    _add(source_kit, "backbone", "minor", "Add `pkit release`.", "a.yaml")

    plan = release.compute_release(source_kit)
    release.apply_release(source_kit, plan, tag=False, today=date(2026, 7, 3))

    changelog = (source_kit.parent / "CHANGELOG.md").read_text()
    assert "# Changelog" in changelog
    assert "## 1.6.0 — 2026-07-03" in changelog
    assert "### backbone (1.5.0 → 1.6.0)" in changelog
    assert "- Add `pkit release`." in changelog


def test_apply_prepends_new_entry_above_existing(tmp_path: Path) -> None:
    source_kit = _make_kit(tmp_path)
    (source_kit.parent / "CHANGELOG.md").write_text(
        "# Changelog\n\n## 1.5.0 — 2026-06-01\n\n### backbone (1.4.0 → 1.5.0)\n- old\n",
        encoding="utf-8",
    )
    _add(source_kit, "backbone", "minor", "new", "a.yaml")
    plan = release.compute_release(source_kit)
    release.apply_release(source_kit, plan, tag=False, today=date(2026, 7, 3))

    text = (source_kit.parent / "CHANGELOG.md").read_text()
    assert text.index("## 1.6.0") < text.index("## 1.5.0")
    assert text.count("# Changelog") == 1


def test_apply_deletes_consumed_changesets(tmp_path: Path) -> None:
    source_kit = _make_kit(tmp_path)
    _add(source_kit, "backbone", "minor", "x", "a.yaml")
    _add(source_kit, "backbone", "none", "y", "b.yaml")

    plan = release.compute_release(source_kit)
    release.apply_release(source_kit, plan, tag=False)

    remaining = list(changesets.unreleased_dir(source_kit.parent).glob("*.yaml"))
    assert remaining == []


def test_apply_cuts_tag_on_backbone_bump(tmp_path: Path) -> None:
    source_kit = _make_kit(tmp_path)
    _add(source_kit, "backbone", "minor", "x", "a.yaml")
    plan = release.compute_release(source_kit)
    release.apply_release(source_kit, plan, tag=True)

    result = subprocess.run(
        ["git", "tag", "-l", "v1.6.0"],
        capture_output=True,
        text=True,
        cwd=source_kit.parent,
        check=True,
    )
    assert result.stdout.strip() == "v1.6.0"


def test_apply_does_not_tag_by_default(tmp_path: Path) -> None:
    """Tag is a separate anchored step — default apply writes but cuts no tag."""
    source_kit = _make_kit(tmp_path)
    _add(source_kit, "backbone", "minor", "x", "a.yaml")
    plan = release.compute_release(source_kit)
    release.apply_release(source_kit, plan)  # tag defaults to False

    result = subprocess.run(
        ["git", "tag", "-l", "v1.6.0"],
        capture_output=True,
        text=True,
        cwd=source_kit.parent,
        check=True,
    )
    assert result.stdout.strip() == ""


def test_apply_empty_plan_is_noop(tmp_path: Path) -> None:
    source_kit = _make_kit(tmp_path)
    plan = release.compute_release(source_kit)
    assert plan.is_empty
    release.apply_release(source_kit, plan, tag=True)  # must not raise
    assert (source_kit / "VERSION").read_text().strip() == "1.5.0"


def test_render_changelog_keys_component_only_release_by_date(tmp_path: Path) -> None:
    source_kit = _make_kit(tmp_path)
    _add(source_kit, "claude-code", "minor", "adapter feature", "a.yaml")
    plan = release.compute_release(source_kit)
    entry = release.render_changelog_entry(plan, date(2026, 7, 3))
    assert entry.startswith("## 2026-07-03 — 2026-07-03")


def test_cutover_legacy_version_bump_still_works(tmp_path: Path) -> None:
    """The old in-branch path is untouched: `bump_version` writes + broadens,
    and the release path computes forward from whatever state it left."""
    source_kit = _make_kit(tmp_path, backbone="1.5.0")

    old, new = versioning.bump_version(source_kit, "minor")
    assert (old, new) == ("1.5.0", "1.6.0")
    assert (source_kit / "VERSION").read_text().strip() == "1.6.0"

    # And the release path reads that new state as its current baseline.
    _add(source_kit, "backbone", "patch", "later fix", "a.yaml")
    plan = release.compute_release(source_kit)
    assert plan.backbone is not None
    assert plan.backbone.new_version == "1.6.1"
