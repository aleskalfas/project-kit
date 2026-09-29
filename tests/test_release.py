"""Tests for the release step: compute, write, broaden-at-release, the declared
floor raise, changelog, and consumption (PRJ-002 D3/D4). Plus a cutover check
that the legacy `version bump` path still works alongside the release path."""

from __future__ import annotations

import shutil
import subprocess
from datetime import date
from pathlib import Path

import click
import pytest

from project_kit import changesets, release, versioning
from project_kit.manifest import read_backbone_manifest
from project_kit.migrations import parse_version_tuple
from tests.adopter_repo import GitRepo


def _make_kit(tmp_path: Path, backbone: str = "1.5.0") -> Path:
    """A source kit in a git repo (so `tag_version` has a HEAD to tag)."""
    repo = GitRepo.init(tmp_path)

    source_kit = tmp_path / ".pkit"
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
    repo.commit("seed")
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


# --- #494: component-release auto-broaden to the current backbone ----------


def _write_capability(source_kit: Path, name: str, version: str, requires_backbone: str) -> Path:
    """Add a kit-shipped capability package.yaml under capabilities/<name>/."""
    cap = source_kit / "capabilities" / name
    cap.mkdir(parents=True)
    pkg = cap / "package.yaml"
    pkg.write_text(
        "schema_version: 1\n"
        "component:\n"
        "  kind: capability\n"
        f"  name: {name}\n"
        f"  version: {version}\n"
        f'requires_backbone: "{requires_backbone}"\n',
        encoding="utf-8",
    )
    return pkg


def test_component_release_broadens_to_current_backbone(tmp_path: Path) -> None:
    """A component release under backbone 1.5.0 widens the released component's
    upper bound to cover it — `<1.2.0` becomes `<1.6.0` (backbone minor + 1)."""
    source_kit = _make_kit(tmp_path, backbone="1.5.0")
    pkg = _write_capability(source_kit, "houseware", "0.3.0", ">=1.0.0,<1.2.0")
    _add(source_kit, "houseware", "minor", "house feature", "a.yaml")

    plan = release.compute_release(source_kit)
    release.apply_release(source_kit, plan, tag=False)

    text = pkg.read_text()
    assert "  version: 0.4.0\n" in text
    assert 'requires_backbone: ">=1.0.0,<1.6.0"' in text
    # Backbone did not move.
    assert (source_kit / "VERSION").read_text().strip() == "1.5.0"


def test_component_release_broaden_is_widen_only(tmp_path: Path) -> None:
    """A component whose range already covers (or exceeds) the current backbone
    is left untouched — the broaden never narrows a wider existing bound."""
    source_kit = _make_kit(tmp_path, backbone="1.5.0")
    pkg = _write_capability(source_kit, "houseware", "0.3.0", ">=1.0.0,<2.0.0")
    _add(source_kit, "houseware", "patch", "house fix", "a.yaml")

    plan = release.compute_release(source_kit)
    release.apply_release(source_kit, plan, tag=False)

    # Upper bound `<2.0.0` already covers backbone 1.5.0 → unchanged.
    assert 'requires_backbone: ">=1.0.0,<2.0.0"' in pkg.read_text()


def test_component_release_no_broaden_skips(tmp_path: Path) -> None:
    """`broaden=False` (the --no-broaden flag) leaves the range as authored."""
    source_kit = _make_kit(tmp_path, backbone="1.5.0")
    pkg = _write_capability(source_kit, "houseware", "0.3.0", ">=1.0.0,<1.2.0")
    _add(source_kit, "houseware", "minor", "house feature", "a.yaml")

    plan = release.compute_release(source_kit)
    release.apply_release(source_kit, plan, tag=False, broaden=False)

    assert 'requires_backbone: ">=1.0.0,<1.2.0"' in pkg.read_text()


# --- PRJ-007: release keeps the self-host manifest backbone_version current ---


def _write_self_host_manifest(source_kit: Path, backbone_version: str) -> Path:
    """Write a self-host `.pkit/manifest.yaml` with a components registry."""
    path = source_kit / "manifest.yaml"
    path.write_text(
        "schema_version: 1\n"
        f"backbone_version: {backbone_version}\n"
        "components:\n"
        "  - kind: adapter\n"
        "    name: claude-code\n"
        "    manifest: .pkit/adapters/claude-code/project/manifest.yaml\n",
        encoding="utf-8",
    )
    return path


def test_apply_backbone_bump_updates_self_host_manifest(tmp_path: Path) -> None:
    """On a backbone bump, apply writes the new version into the self-host
    manifest's `backbone_version`, matching the new `.pkit/VERSION` (PRJ-007)."""
    source_kit = _make_kit(tmp_path, backbone="1.5.0")
    _write_self_host_manifest(source_kit, "1.0.0")
    _add(source_kit, "backbone", "minor", "a new command", "a.yaml")

    plan = release.compute_release(source_kit)
    release.apply_release(source_kit, plan, tag=False)

    version = (source_kit / "VERSION").read_text().strip()
    assert version == "1.6.0"
    updated = read_backbone_manifest(source_kit.parent)
    assert updated is not None
    assert updated.backbone_version == version


def test_apply_backbone_bump_preserves_other_manifest_keys(tmp_path: Path) -> None:
    """Only `backbone_version` moves — the components registry and schema
    version are preserved (PRJ-007)."""
    source_kit = _make_kit(tmp_path, backbone="1.5.0")
    _write_self_host_manifest(source_kit, "1.0.0")
    _add(source_kit, "backbone", "minor", "x", "a.yaml")

    plan = release.compute_release(source_kit)
    release.apply_release(source_kit, plan, tag=False)

    updated = read_backbone_manifest(source_kit.parent)
    assert updated is not None
    assert updated.schema_version == 1
    assert [e.name for e in updated.components] == ["claude-code"]
    assert updated.components[0].kind == "adapter"


def test_apply_capability_only_release_leaves_manifest_backbone(tmp_path: Path) -> None:
    """A capability-only release does not move the backbone, so the self-host
    manifest's `backbone_version` is untouched (PRJ-007)."""
    source_kit = _make_kit(tmp_path, backbone="1.5.0")
    _write_capability(source_kit, "houseware", "0.3.0", ">=1.0.0,<1.6.0")
    _write_self_host_manifest(source_kit, "1.0.0")
    _add(source_kit, "houseware", "minor", "house feature", "a.yaml")

    plan = release.compute_release(source_kit)
    release.apply_release(source_kit, plan, tag=False)

    # Backbone did not move → manifest backbone_version stays as authored.
    assert (source_kit / "VERSION").read_text().strip() == "1.5.0"
    updated = read_backbone_manifest(source_kit.parent)
    assert updated is not None
    assert updated.backbone_version == "1.0.0"


def test_apply_backbone_bump_no_manifest_is_noop(tmp_path: Path) -> None:
    """An apply in a repo with no self-host manifest is unaffected — the sync is
    source-repo-only mechanics and no-ops when there is nothing to maintain."""
    source_kit = _make_kit(tmp_path, backbone="1.5.0")  # _make_kit writes no manifest
    _add(source_kit, "backbone", "minor", "x", "a.yaml")

    plan = release.compute_release(source_kit)
    release.apply_release(source_kit, plan, tag=False)  # must not raise

    assert (source_kit / "VERSION").read_text().strip() == "1.6.0"
    assert read_backbone_manifest(source_kit.parent) is None


def test_backbone_release_still_broadens_all_components(tmp_path: Path) -> None:
    """No regression: a backbone release widens every component to the new
    backbone minor (the original PRJ-002 D4 broaden), not the component path."""
    source_kit = _make_kit(tmp_path, backbone="1.5.0")
    pkg = _write_capability(source_kit, "houseware", "0.3.0", ">=1.0.0,<1.2.0")
    _add(source_kit, "backbone", "minor", "backbone change", "a.yaml")

    plan = release.compute_release(source_kit)
    release.apply_release(source_kit, plan, tag=False)

    # Backbone 1.5.0 -> 1.6.0; every component broadens to <1.7.0.
    assert (source_kit / "VERSION").read_text().strip() == "1.6.0"
    assert 'requires_backbone: ">=1.0.0,<1.7.0"' in pkg.read_text()
    adapter = (source_kit / "adapters" / "claude-code" / "package.yaml").read_text()
    assert 'requires_backbone: ">=0.1.0,<1.7.0"' in adapter


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


# --- The declared floor raise (PRJ-002 D4) ----------------------------------


def _add_floor(
    source_kit: Path, component: str, kind: str, name: str, *, value: str = "release"
) -> None:
    """A changeset declaring its component needs the backbone the release ships."""
    directory = changesets.unreleased_dir(source_kit.parent)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / name).write_text(
        f"component: {component}\nkind: {kind}\nbody: Needs the new backbone.\n"
        f"custom:\n  requires_backbone: {value}\n",
        encoding="utf-8",
    )


def test_backbone_release_raises_a_declared_floor_to_the_new_backbone(tmp_path: Path) -> None:
    """The declared component's floor rises to the backbone the release ships; a
    component that declared nothing keeps its floor — the raise is never automatic."""
    source_kit = _make_kit(tmp_path, backbone="1.5.0")
    declared = _write_capability(source_kit, "houseware", "0.3.0", ">=1.0.0,<2.0.0")
    silent = _write_capability(source_kit, "otherware", "0.1.0", ">=1.0.0,<2.0.0")
    _add(source_kit, "backbone", "minor", "backbone change", "a.yaml")
    _add_floor(source_kit, "houseware", "minor", "b.yaml")

    plan = release.compute_release(source_kit)
    assert plan.shipped_backbone == "1.6.0"
    assert [r.component.name for r in plan.floor_raises] == ["houseware"]
    release.apply_release(source_kit, plan, tag=False)

    assert (source_kit / "VERSION").read_text().strip() == "1.6.0"
    assert 'requires_backbone: ">=1.6.0,<2.0.0"' in declared.read_text()
    assert "  version: 0.4.0\n" in declared.read_text()
    assert 'requires_backbone: ">=1.0.0,<2.0.0"' in silent.read_text()
    adapter = (source_kit / "adapters" / "claude-code" / "package.yaml").read_text()
    assert 'requires_backbone: ">=0.1.0,<1.7.0"' in adapter  # broadened, floor untouched


def test_component_release_raises_a_declared_floor_to_the_current_backbone(
    tmp_path: Path,
) -> None:
    """With no backbone move, the backbone the release ships is the current one."""
    source_kit = _make_kit(tmp_path, backbone="1.5.0")
    pkg = _write_capability(source_kit, "houseware", "0.3.0", ">=1.0.0,<2.0.0")
    _add_floor(source_kit, "houseware", "patch", "a.yaml")

    plan = release.compute_release(source_kit)
    assert plan.shipped_backbone == "1.5.0"
    release.apply_release(source_kit, plan, tag=False)

    assert 'requires_backbone: ">=1.5.0,<2.0.0"' in pkg.read_text()
    assert (source_kit / "VERSION").read_text().strip() == "1.5.0"


def test_declared_floor_raise_is_raise_only(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source_kit = _make_kit(tmp_path, backbone="1.5.0")
    pkg = _write_capability(source_kit, "houseware", "0.3.0", ">=1.5.0,<2.0.0")
    _add_floor(source_kit, "houseware", "patch", "a.yaml")

    release.apply_release(source_kit, release.compute_release(source_kit), tag=False)

    assert 'requires_backbone: ">=1.5.0,<2.0.0"' in pkg.read_text()
    assert "already admits no backbone older than 1.5.0" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("component", "kind", "value", "problem"),
    [
        ("backbone", "minor", "release", "the backbone has no `requires_backbone`"),
        ("houseware", "none", "release", "a `none` changeset moves no version"),
        ("houseware", "minor", "1.6.0", "takes one value, `release`"),
        ("wildware", "minor", "release", "has a floor the release can raise"),
    ],
)
def test_compute_refuses_a_floor_field_it_cannot_carry(
    tmp_path: Path, component: str, kind: str, value: str, problem: str
) -> None:
    """A declared floor is never dropped silently: the release refuses to plan."""
    source_kit = _make_kit(tmp_path, backbone="1.5.0")
    _write_capability(source_kit, "houseware", "0.3.0", ">=1.0.0,<2.0.0")
    _write_capability(source_kit, "wildware", "0.3.0", "*")
    _add_floor(source_kit, component, kind, "a.yaml", value=value)

    with pytest.raises(click.ClickException, match="cannot raise a requires_backbone floor") as err:
        release.compute_release(source_kit)
    assert problem in err.value.message


def test_no_broaden_still_raises_a_declared_floor(tmp_path: Path) -> None:
    """`--no-broaden` keeps an upper bound as authored; a declared need still stands."""
    source_kit = _make_kit(tmp_path, backbone="1.5.0")
    pkg = _write_capability(source_kit, "houseware", "0.3.0", ">=1.0.0,<2.0.0")
    _add_floor(source_kit, "houseware", "minor", "a.yaml")

    release.apply_release(source_kit, release.compute_release(source_kit), tag=False, broaden=False)

    assert 'requires_backbone: ">=1.5.0,<2.0.0"' in pkg.read_text()


def test_no_broaden_refuses_a_floor_the_upper_bound_cannot_hold(tmp_path: Path) -> None:
    """Raised under an upper bound that excludes the shipped backbone, the range would
    admit nothing — refused before anything is written."""
    source_kit = _make_kit(tmp_path, backbone="1.5.0")
    pkg = _write_capability(source_kit, "houseware", "0.3.0", ">=1.0.0,<1.5.0")
    _add_floor(source_kit, "houseware", "minor", "a.yaml")
    before = pkg.read_text()

    plan = release.compute_release(source_kit)
    with pytest.raises(click.ClickException, match="would admit no backbone"):
        release.apply_release(source_kit, plan, tag=False, broaden=False)

    assert pkg.read_text() == before
    assert list(changesets.unreleased_dir(source_kit.parent).glob("*.yaml"))


def test_no_broaden_does_not_refuse_a_floor_it_leaves_alone(tmp_path: Path) -> None:
    """A floor already above the shipped backbone is not raised, so its range is
    not the release's to refuse."""
    source_kit = _make_kit(tmp_path, backbone="1.5.0")
    pkg = _write_capability(source_kit, "houseware", "0.3.0", ">=1.7.0,<2.0.0")
    _add_floor(source_kit, "houseware", "patch", "a.yaml")

    release.apply_release(source_kit, release.compute_release(source_kit), tag=False, broaden=False)

    assert 'requires_backbone: ">=1.7.0,<2.0.0"' in pkg.read_text()
    assert "  version: 0.3.1\n" in pkg.read_text()


def test_a_pre_release_backbone_is_refused_before_anything_is_written(tmp_path: Path) -> None:
    """A component release under a pre-release `.pkit/VERSION` ships that
    pre-release, which no floor is raised to: the release refuses to plan, so
    `apply` never writes the component's version first and double-bumps on retry."""
    source_kit = _make_kit(tmp_path, backbone="1.6.0rc1")
    pkg = _write_capability(source_kit, "houseware", "0.3.0", ">=1.0.0,<2.0.0")
    _add_floor(source_kit, "houseware", "minor", "a.yaml")
    before = pkg.read_text()

    with pytest.raises(click.ClickException, match="not a release version") as err:
        release.compute_release(source_kit)
    assert "ships backbone '1.6.0rc1'" in err.value.message
    assert pkg.read_text() == before


def test_a_backbone_move_lifts_the_pre_release_refusal(tmp_path: Path) -> None:
    """Moving the backbone ships a release version, whatever `.pkit/VERSION` held."""
    source_kit = _make_kit(tmp_path, backbone="1.6.0rc1")
    pkg = _write_capability(source_kit, "houseware", "0.3.0", ">=1.0.0,<2.0.0")
    _add(source_kit, "backbone", "patch", "backbone fix", "a.yaml")
    _add_floor(source_kit, "houseware", "minor", "b.yaml")

    plan = release.compute_release(source_kit)
    assert plan.shipped_backbone == "1.6.1"
    release.apply_release(source_kit, plan, tag=False)
    assert 'requires_backbone: ">=1.6.1,<2.0.0"' in pkg.read_text()


def test_a_comment_naming_the_key_is_neither_broadened_nor_raised(tmp_path: Path) -> None:
    """A comment quoting an older range sits above the key. The broaden and the
    floor raise both rewrite the key, so the raised range still admits the
    backbone — were the comment broadened instead, the key would be left
    `">=1.5.0,<1.5.0"`, admitting nothing."""
    source_kit = _make_kit(tmp_path, backbone="1.5.0")
    pkg = _write_capability(source_kit, "houseware", "0.3.0", ">=1.0.0,<1.5.0")
    comment = '# was requires_backbone: ">=1.0.0,<1.4.0"\n'
    pkg.write_text(pkg.read_text().replace("requires_backbone:", comment + "requires_backbone:"))
    _add_floor(source_kit, "houseware", "minor", "a.yaml")

    release.apply_release(source_kit, release.compute_release(source_kit), tag=False)

    text = pkg.read_text()
    assert comment in text
    assert 'requires_backbone: ">=1.5.0,<1.6.0"' in text


def test_the_empty_range_check_runs_with_the_broaden_too(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The check is not a `--no-broaden` special case: every raise is checked
    against the range computed in memory. With a broaden that (hypothetically)
    widens nothing, the raised range would be empty, and nothing is written."""
    source_kit = _make_kit(tmp_path, backbone="1.5.0")
    pkg = _write_capability(source_kit, "houseware", "0.3.0", ">=1.0.0,<1.5.0")
    _add_floor(source_kit, "houseware", "minor", "a.yaml")
    before = pkg.read_text()

    def widens_nothing(package_text: str, backbone: str) -> tuple[str, str] | None:
        return None

    monkeypatch.setattr(versioning, "broaden_requires_backbone", widens_nothing)

    plan = release.compute_release(source_kit)
    with pytest.raises(click.ClickException, match="would admit no backbone"):
        release.apply_release(source_kit, plan, tag=False)

    assert pkg.read_text() == before
    assert (source_kit / "VERSION").read_text().strip() == "1.5.0"


# --- Dogfood: the release that ships the backbone-owned journal line ---------

REPO_ROOT = Path(__file__).resolve().parent.parent

# The backbone release that took the process-journal ignore line over from the
# project-management package (#1120; its migration is
# `.pkit/migrations/backbone/1.150.0/001-keep-process-journal-logging.sh`).
JOURNAL_LINE_BACKBONE = "1.150.0"


def test_pending_release_leaves_project_management_on_the_journal_owning_backbone(
    tmp_path: Path,
) -> None:
    """project-management stopped declaring the journal ignore line when the backbone
    took it over, so on an older backbone its journals go unignored. Applying the
    pending changesets to a copy of this tree must leave its floor at or above that
    backbone: until the release that ships it has run, the changeset that dropped
    the line raises the floor; afterwards the package carries it."""
    source_kit = tmp_path / ".pkit"
    source_kit.mkdir()
    shutil.copy(REPO_ROOT / ".pkit" / "VERSION", source_kit / "VERSION")
    for package in (REPO_ROOT / ".pkit").rglob("package.yaml"):
        target = source_kit / package.relative_to(REPO_ROOT / ".pkit")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(package, target)
    pending = changesets.unreleased_dir(REPO_ROOT)
    if pending.is_dir():
        shutil.copytree(pending, changesets.unreleased_dir(tmp_path))

    plan = release.compute_release(source_kit)
    release.apply_release(source_kit, plan, tag=False, today=date(2026, 9, 29))

    package = source_kit / "capabilities" / "project-management" / "package.yaml"
    floor = versioning.requires_backbone_floor(package.read_text(encoding="utf-8"))
    assert floor is not None
    assert parse_version_tuple(floor) >= parse_version_tuple(JOURNAL_LINE_BACKBONE)
