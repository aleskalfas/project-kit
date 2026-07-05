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


def _write_categorised(
    source_kit: Path,
    component: str,
    kind: str,
    body: str,
    category: str,
    name: str,
    *,
    pr: str | None = None,
) -> None:
    directory = changesets.unreleased_dir(source_kit.parent)
    directory.mkdir(parents=True, exist_ok=True)
    text = f"component: {component}\nkind: {kind}\nbody: {body}\ncategory: {category}\n"
    if pr is not None:
        text += f'pr: "{pr}"\n'
    (directory / name).write_text(text, encoding="utf-8")


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
    # No category on the changeset → defaults to `Changed`; backbone entry plain.
    assert "### Changed" in changelog
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
    # No backbone move → the section keys by date alone (no `<version> — date`).
    assert entry.startswith("## 2026-07-03\n")
    # The inline component tag surfaces which component moved and to what.
    assert "**claude-code 0.6.0** — adapter feature" in entry


def test_render_groups_entries_by_category(tmp_path: Path) -> None:
    source_kit = _make_kit(tmp_path)
    _write_categorised(source_kit, "backbone", "minor", "New thing.", "Added", "a.yaml")
    _write_categorised(source_kit, "backbone", "patch", "Broken thing.", "Fixed", "b.yaml")
    plan = release.compute_release(source_kit)
    entry = release.render_changelog_entry(plan, date(2026, 7, 3))

    assert "### Added\n- New thing." in entry
    assert "### Fixed\n- Broken thing." in entry
    # Canonical KaC order: Added precedes Fixed.
    assert entry.index("### Added") < entry.index("### Fixed")


def test_render_tags_non_backbone_component_inline(tmp_path: Path) -> None:
    source_kit = _make_kit(tmp_path)
    _write_categorised(source_kit, "backbone", "minor", "Backbone thing.", "Added", "a.yaml")
    _write_categorised(source_kit, "claude-code", "minor", "Adapter thing.", "Added", "b.yaml")
    plan = release.compute_release(source_kit)
    entry = release.render_changelog_entry(plan, date(2026, 7, 3))

    # Section keys on the backbone version; the backbone entry is plain, the
    # non-backbone one is tagged inline with its own name + new version.
    assert entry.startswith("## 1.6.0 — 2026-07-03")
    assert "- Backbone thing." in entry
    assert "- **claude-code 0.6.0** — Adapter thing." in entry


def test_render_resolves_pr_links_in_trailing_block(tmp_path: Path) -> None:
    source_kit = _make_kit(tmp_path)
    _write_categorised(source_kit, "backbone", "minor", "A change.", "Changed", "a.yaml", pr="465")
    _write_categorised(
        source_kit,
        "backbone",
        "patch",
        "A URL-linked fix.",
        "Fixed",
        "b.yaml",
        pr="https://example.test/pull/470",
    )
    plan = release.compute_release(source_kit)
    entry = release.render_changelog_entry(plan, date(2026, 7, 3))

    # Inline `([#N])` on the entry, definition resolved at the foot.
    assert "- A change. ([#465])" in entry
    assert "- A URL-linked fix. ([#470])" in entry
    assert "[#465]: 465" in entry
    assert "[#470]: https://example.test/pull/470" in entry
    # The link block sits below the entries.
    assert entry.index("### Changed") < entry.index("[#465]: 465")


def test_render_omits_link_when_pr_absent(tmp_path: Path) -> None:
    source_kit = _make_kit(tmp_path)
    _write_categorised(source_kit, "backbone", "minor", "No PR here.", "Added", "a.yaml")
    plan = release.compute_release(source_kit)
    entry = release.render_changelog_entry(plan, date(2026, 7, 3))

    assert "- No PR here." in entry
    assert "([#" not in entry  # no inline link
    assert "]: " not in entry  # no trailing reference block


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


def _add_migration_dir(source_kit: Path, version: str) -> None:
    (source_kit / "migrations" / "backbone" / version).mkdir(parents=True, exist_ok=True)


def test_release_summary_shape_for_backbone_move(tmp_path: Path) -> None:
    source_kit = _make_kit(tmp_path)
    _add(source_kit, "backbone", "minor", "a new command", "a.yaml")
    plan = release.compute_release(source_kit)

    summary = release.release_summary(source_kit, plan)
    assert summary["empty"] is False
    assert summary["backbone_version"] == "1.6.0"
    assert summary["changesets_consumed"] == 1
    assert summary["migration_warnings"] == []
    releases = summary["releases"]
    assert isinstance(releases, list)
    assert releases[0]["component"] == "backbone"
    assert releases[0]["old_version"] == "1.5.0"
    assert releases[0]["new_version"] == "1.6.0"
    assert releases[0]["segment"] == "minor"
    assert releases[0]["notes"] == ["a new command"]


def test_release_summary_empty_plan(tmp_path: Path) -> None:
    source_kit = _make_kit(tmp_path)
    plan = release.compute_release(source_kit)

    summary = release.release_summary(source_kit, plan)
    assert summary["empty"] is True
    assert summary["backbone_version"] is None
    assert summary["releases"] == []


def test_migration_dir_no_warning_when_dir_matches_computed(tmp_path: Path) -> None:
    source_kit = _make_kit(tmp_path)
    _add(source_kit, "backbone", "minor", "x", "a.yaml")  # 1.5.0 -> 1.6.0
    _add_migration_dir(source_kit, "1.6.0")
    plan = release.compute_release(source_kit)

    assert release.migration_dir_mismatches(source_kit, plan) == []


def test_migration_dir_warns_on_stale_prediction(tmp_path: Path) -> None:
    source_kit = _make_kit(tmp_path)
    _add(source_kit, "backbone", "minor", "x", "a.yaml")  # computes 1.6.0
    _add_migration_dir(source_kit, "1.7.0")  # predicts a version the release won't cut
    plan = release.compute_release(source_kit)

    warnings = release.migration_dir_mismatches(source_kit, plan)
    assert len(warnings) == 1
    assert "backbone/1.7.0" in warnings[0]
    assert "1.6.0" in warnings[0]


def test_migration_dir_ignores_released_history(tmp_path: Path) -> None:
    source_kit = _make_kit(tmp_path)
    _add(source_kit, "backbone", "minor", "x", "a.yaml")
    _add_migration_dir(source_kit, "1.5.0")  # == current VERSION, already-released history
    plan = release.compute_release(source_kit)

    assert release.migration_dir_mismatches(source_kit, plan) == []


def test_migration_dir_warns_when_release_moves_no_backbone(tmp_path: Path) -> None:
    source_kit = _make_kit(tmp_path)
    _add(source_kit, "claude-code", "minor", "adapter feature", "a.yaml")  # no backbone move
    _add_migration_dir(source_kit, "1.6.0")  # future backbone dir with nothing to cut
    plan = release.compute_release(source_kit)

    warnings = release.migration_dir_mismatches(source_kit, plan)
    assert len(warnings) == 1
    assert "backbone/1.6.0" in warnings[0]
