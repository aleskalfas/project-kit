"""Tests for `pkit sync` (PR-G of the build roadmap)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import click
import pytest

from project_kit import install, sync
from project_kit.manifest import read_backbone_manifest


@pytest.fixture
def installed_target(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A git repo with the kit already installed; ready for sync."""
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    monkeypatch.chdir(tmp_path)

    def _noop(_script: Path, _ctx: install.InstallContext) -> None:
        return None

    monkeypatch.setattr(install, "_run_adapter_primitive", _noop)
    install.install_kit(tmp_path)
    return tmp_path


def test_sync_refuses_when_pkit_dir_missing(tmp_path: Path) -> None:
    with pytest.raises(click.ClickException, match=r"\.pkit/ does not exist"):
        sync.run_sync(tmp_path)


def test_sync_self_host_runs_deploy_primitives_only(monkeypatch: pytest.MonkeyPatch) -> None:
    """Project-kit self-hosts; sync re-runs the deploy primitives instead of refusing.

    The source IS the installed `.pkit/`, so propagation would copy files
    onto themselves. The self-host branch skips propagation entirely and runs
    only the deploy primitives (re-wiring the harness from the source the
    maintainer just edited). It must not raise and must not propagate.
    """
    from project_kit import install

    source_repo = install.find_source_kit().parent
    monkeypatch.chdir(source_repo)

    called = {"deploy": 0}

    def _spy_deploy(_ctx: install.InstallContext) -> None:
        called["deploy"] += 1

    def _no_propagate(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("self-host sync must not propagate (copy onto source)")

    monkeypatch.setattr(install, "run_installed_adapter_primitives", _spy_deploy)
    monkeypatch.setattr(install, "_install_area", _no_propagate)

    sync.run_sync(source_repo)  # must not raise

    assert called["deploy"] == 1


def test_sync_runs_idempotently_after_install(installed_target: Path) -> None:
    """Sync on an already-installed target with no source changes is a clean no-op."""
    # No assertion here that *files* are unchanged (sync re-copies them);
    # the contract is that it succeeds and reports the manifest as unchanged.
    sync.run_sync(installed_target)
    manifest = read_backbone_manifest(installed_target)
    assert manifest is not None


# --- the no-shared-files preservation invariant across sync's copy paths ---
#
# COR-001: every copy/refresh path `pkit sync` drives must preserve
# adopter-owned `project/` content (seed-once, never overwrite/remove on
# refresh). `pkit sync` fans out to three structurally-different copy
# primitives — `_install_area` (backbone areas), `_install_adapter`
# (harness adapters), and `_copy_capability_tree` via `refresh_capability`
# (installed capabilities). Each enforces the rule with its own mechanics,
# so each needs its own preservation guard at the `run_sync` entry point.
# The capability case is the one that regressed in #332 (its guard lived
# only at the `refresh_capability` unit level, a rung below `run_sync`).
#
# These guard the top-level `project/` convention per tier (the live
# convention). A NEW copy path added to `run_sync` must add its own case
# here — that is what stops the next silent clobber.


def test_sync_preserves_project_owned_content(installed_target: Path) -> None:
    """Area path: `.pkit/<area>/project/` content must NOT be touched by sync."""
    project_marker = installed_target / ".pkit" / "decisions" / "project" / "PRJ-001-mine.md"
    project_marker.write_text("---\nid: PRJ-001\n---\n", encoding="utf-8")

    sync.run_sync(installed_target)

    assert project_marker.is_file(), "sync clobbered project/ content"
    assert "PRJ-001" in project_marker.read_text(encoding="utf-8")


def test_sync_does_not_overwrite_adopter_settings(installed_target: Path) -> None:
    """Adapter path: `settings/project/settings.json` is adopter-owned."""
    settings_path = (
        installed_target
        / ".pkit"
        / "adapters"
        / "claude-code"
        / "settings"
        / "project"
        / "settings.json"
    )
    custom = '{"permissions": {"allow": ["Bash(echo:*)"], "deny": []}}'
    settings_path.write_text(custom, encoding="utf-8")

    sync.run_sync(installed_target)

    assert settings_path.read_text(encoding="utf-8") == custom


def test_sync_preserves_installed_capability_project_content(
    installed_target: Path,
) -> None:
    """Capability path: an installed capability's adopter-owned `project/` content
    must survive `run_sync` (the #332 scenario, guarded at the sync entry point)."""
    from project_kit import capabilities as caps

    source = install.find_source_kit()
    cap_source = caps.find_capability_in_source(source, "project-management")
    assert cap_source is not None, "project-management capability should ship from source"
    caps.install_capability(installed_target, cap_source)

    config = (
        installed_target
        / ".pkit"
        / "capabilities"
        / "project-management"
        / "project"
        / "config.yaml"
    )
    assert config.is_file(), "seeded config.yaml should exist after install"
    config.write_text(
        "schema_version: 1\ndefault_branch: develop  # adopter customisation\n",
        encoding="utf-8",
    )

    sync.run_sync(installed_target)

    assert config.is_file(), "sync clobbered the capability's adopter-owned project/ file"
    assert "default_branch: develop" in config.read_text(encoding="utf-8")


def test_sync_emits_consolidation_hint_when_redundancies_exist(
    installed_target: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Sync prints a one-line hint when `.claude/settings.json` has redundant entries.

    The merge primitive doesn't auto-consolidate (per the kit's preserve-
    adopter-content stance). Adopters need a deliberate signal that
    cleanup is available — sync emits it at the end of its run.
    """
    import json as _json

    # Fixture mocks adapter primitives, so .claude/settings.json doesn't
    # exist yet — write one with the redundancy we want to detect.
    claude_dir = installed_target / ".claude"
    claude_dir.mkdir(parents=True, exist_ok=True)
    settings_file = claude_dir / "settings.json"
    settings_file.write_text(
        _json.dumps(
            {
                "permissions": {
                    "allow": [
                        "Bash(pkit:*)",
                        "Bash(pkit new *)",
                        "Bash(pkit refs *)",
                    ],
                    "deny": [],
                }
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    sync.run_sync(installed_target)
    captured = capsys.readouterr()
    assert "redundant entry(ies)" in captured.out
    assert "pkit settings consolidate" in captured.out


def test_sync_no_hint_when_settings_already_clean(
    installed_target: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Sync stays quiet about consolidation when there's nothing to clean."""
    import json as _json

    claude_dir = installed_target / ".claude"
    claude_dir.mkdir(parents=True, exist_ok=True)
    (claude_dir / "settings.json").write_text(
        _json.dumps(
            {"permissions": {"allow": ["Bash(pkit:*)", "Bash(git:*)"], "deny": []}},
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    sync.run_sync(installed_target)
    captured = capsys.readouterr()
    assert "settings consolidate" not in captured.out


def test_sync_dry_run_writes_nothing(installed_target: Path) -> None:
    """A dry-run sync must not modify any file under target_root."""
    project_marker = installed_target / ".pkit" / "decisions" / "project" / "PRJ-001-mine.md"
    project_marker.write_text("test-content", encoding="utf-8")
    pre_mtime = project_marker.stat().st_mtime

    sync.run_sync(installed_target, dry_run=True)

    assert project_marker.read_text(encoding="utf-8") == "test-content"
    assert project_marker.stat().st_mtime == pre_mtime


def test_sync_prunes_orphan_file_in_core_tree(installed_target: Path) -> None:
    """Files under `<area>/core/` that no longer exist in source are removed by sync.

    Regression for #84: a previous install whose source had `decision-author/SKILL.md`
    and a later install whose source has only `decision-author.md` would leave the
    legacy folder lingering. Simulate by injecting an orphan into the adopter's tree.
    """
    orphan = installed_target / ".pkit" / "skills" / "core" / "old-skill-orphan.md"
    orphan.write_text("---\nname: old-skill-orphan\n---\nstale content\n", encoding="utf-8")
    assert orphan.is_file()

    sync.run_sync(installed_target)

    assert not orphan.exists(), "sync left an orphan core skill in place"


def test_sync_prunes_orphan_nested_dir_in_core_tree(installed_target: Path) -> None:
    """A nested orphan directory under `<area>/core/` is removed by sync.

    The exact shape of the production bug we hit in example-brownfield:
    a legacy `decision-author/SKILL.md` folder layout left over from before
    COR-015 flattened skills.
    """
    legacy_dir = installed_target / ".pkit" / "skills" / "core" / "legacy-folder-skill"
    legacy_dir.mkdir(parents=True)
    (legacy_dir / "SKILL.md").write_text("legacy folder-form\n", encoding="utf-8")
    assert (legacy_dir / "SKILL.md").is_file()

    sync.run_sync(installed_target)

    assert not legacy_dir.exists(), "sync left a legacy folder-form skill in place"


def test_sync_prunes_orphan_adapter_script(installed_target: Path) -> None:
    """`.pkit/adapters/<name>/*.sh` files with no source counterpart are removed by sync."""
    orphan = (
        installed_target / ".pkit" / "adapters" / "claude-code" / "deploy-removed.sh"
    )
    orphan.write_text("#!/usr/bin/env bash\necho stale\n", encoding="utf-8")
    orphan.chmod(0o755)
    assert orphan.is_file()

    sync.run_sync(installed_target)

    assert not orphan.exists(), "sync left an orphan adapter script in place"


def test_sync_prune_does_not_touch_project_namespace(installed_target: Path) -> None:
    """The prune pass must leave `<area>/project/` content alone."""
    project_decision = installed_target / ".pkit" / "decisions" / "project" / "PRJ-001-mine.md"
    project_decision.write_text("---\nid: PRJ-001\n---\nadopter content\n", encoding="utf-8")

    project_skill = installed_target / ".pkit" / "skills" / "project" / "my-skill.md"
    project_skill.parent.mkdir(parents=True, exist_ok=True)
    project_skill.write_text(
        "---\nname: my-skill\n---\nadopter skill body\n", encoding="utf-8"
    )

    sync.run_sync(installed_target)

    assert project_decision.is_file(), "sync prune clobbered project decision"
    assert "PRJ-001" in project_decision.read_text(encoding="utf-8")
    assert project_skill.is_file(), "sync prune clobbered project skill"
    assert "my-skill" in project_skill.read_text(encoding="utf-8")


def test_sync_dry_run_does_not_prune(installed_target: Path) -> None:
    """A dry-run sync reports the prune intent without actually removing files."""
    orphan = installed_target / ".pkit" / "skills" / "core" / "old-skill-orphan.md"
    orphan.write_text("stale\n", encoding="utf-8")

    sync.run_sync(installed_target, dry_run=True)

    assert orphan.is_file(), "dry-run sync removed a file it should have only previewed"


def test_sync_invokes_installed_adapter_primitives(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`pkit sync` must re-run each installed adapter's primitives.

    Init runs `merge-settings.sh`, `deploy-skills.sh`, `deploy-agents.sh`
    so the harness side is materialised. Sync mirrors that — without it,
    a sync that brings in new agent templates or skill renames leaves
    the adopter's `.claude/agents/` and `.claude/skills/` stale until
    the user runs the deploy scripts by hand.
    """
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    monkeypatch.chdir(tmp_path)

    calls: list[str] = []

    def _record(script: Path, _ctx: install.InstallContext) -> None:
        calls.append(script.name)

    monkeypatch.setattr(install, "_run_adapter_primitive", _record)
    install.install_kit(tmp_path)
    init_calls = list(calls)
    calls.clear()

    sync.run_sync(tmp_path)

    # Sync should invoke the same primitives init did (same adapter, same
    # order). Init's invocation list serves as the contract for sync's.
    assert calls == init_calls, (
        f"sync's primitives don't match init's. init={init_calls!r} sync={calls!r}"
    )
    # And the list must include the deploy scripts we care about.
    assert "deploy-skills.sh" in calls
    assert "deploy-agents.sh" in calls


def test_sync_stubs_project_dir_for_area_that_landed_after_install(
    installed_target: Path,
) -> None:
    """Adopter installed before an area landed should get `project/` stubbed on sync.

    Regression: example-brownfield was installed at backbone 0.13.0 (before the
    agents area). Syncing forward to 1.17.x failed because `.pkit/agents/project/`
    didn't exist, so `deploy-agents.sh` errored on missing overlay.yaml. Sync
    must catch up the project/ scaffolding when it's missing.
    """
    project_dir = installed_target / ".pkit" / "agents" / "project"
    # Simulate the pre-agents-area install state: remove project/ entirely.
    import shutil

    if project_dir.exists():
        shutil.rmtree(project_dir)
    assert not project_dir.exists()

    sync.run_sync(installed_target)

    assert project_dir.is_dir(), "sync didn't stub missing project/"
    assert (project_dir / ".gitkeep").is_file()


def test_sync_seeds_agents_overlay_if_missing(installed_target: Path) -> None:
    """First sync after the agents area appears seeds a starter overlay.yaml."""
    overlay = installed_target / ".pkit" / "agents" / "project" / "overlay.yaml"
    if overlay.exists():
        overlay.unlink()
    assert not overlay.exists()

    sync.run_sync(installed_target)

    assert overlay.is_file(), "sync didn't seed overlay.yaml"
    content = overlay.read_text(encoding="utf-8")
    assert "workflow-docs" in content
    assert "project-root-docs" in content


def test_sync_does_not_overwrite_existing_overlay(installed_target: Path) -> None:
    """If the adopter already has overlay.yaml, sync leaves it untouched."""
    overlay = installed_target / ".pkit" / "agents" / "project" / "overlay.yaml"
    overlay.parent.mkdir(parents=True, exist_ok=True)
    custom = "workflow-docs:\n  - my-roadmap.md\n"
    overlay.write_text(custom, encoding="utf-8")

    sync.run_sync(installed_target)

    assert overlay.read_text(encoding="utf-8") == custom


def test_adapter_primitive_failure_raises_clickexception(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When a deploy script exits non-zero, the user sees a ClickException, not a traceback.

    Regression: a primitive's non-zero exit propagated as
    `subprocess.CalledProcessError` past Click, producing a Python
    traceback instead of a clean error message.
    """
    import subprocess as sp

    script = tmp_path / "deploy.sh"
    script.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
    script.chmod(0o755)

    def _fake_run(cmd, **kwargs):  # type: ignore[no-untyped-def]
        return sp.CompletedProcess(args=cmd, returncode=1)

    monkeypatch.setattr(install.subprocess, "run", _fake_run)
    ctx = install.InstallContext(target_root=tmp_path, source_kit=tmp_path, dry_run=False)

    with pytest.raises(click.ClickException, match="exited with status 1"):
        install._run_adapter_primitive(script, ctx)  # pyright: ignore[reportPrivateUsage]


def _stage_capability_in_source(
    source_kit: Path,
    name: str,
    *,
    skill_body: str = "# Skill\n",
    extra_decision: str | None = None,
) -> Path:
    """Create a capability under source_kit/capabilities/<name>/ for sync tests.

    Mirrors the layout `pkit capabilities install` expects in source:
    package.yaml + skills/ + decisions/. Also stamps a VERSION + decisions/
    scaffold so sync's _update_recorded_backbone_version + the
    source-kit-missing guard don't trip.
    """
    cap_dir = source_kit / "capabilities" / name
    (cap_dir / "skills").mkdir(parents=True, exist_ok=True)
    (cap_dir / "decisions").mkdir(parents=True, exist_ok=True)
    # Sync's manifest update needs a VERSION file in the source.
    version_file = source_kit / "VERSION"
    if not version_file.is_file():
        version_file.write_text("1.0.0\n", encoding="utf-8")
    # Sync's _refuse_if_source_kit_missing equivalent wants decisions/.
    (source_kit / "decisions").mkdir(parents=True, exist_ok=True)
    (cap_dir / "package.yaml").write_text(
        f"""component:
  kind: capability
  name: {name}
  version: 1.0.0
description: Test capability.
requires_backbone: ">=0.0.0"
schema_version: 1
""",
        encoding="utf-8",
    )
    (cap_dir / "skills" / f"{name}-skill.md").write_text(
        f"---\nname: {name}-skill\n---\n{skill_body}",
        encoding="utf-8",
    )
    (cap_dir / "decisions" / "DEC-001-foo.md").write_text(
        "---\nid: DEC-001\nstatus: accepted\n---\n# Foo\n",
        encoding="utf-8",
    )
    if extra_decision is not None:
        (cap_dir / "decisions" / extra_decision).write_text(
            "---\nid: DEC-002\nstatus: accepted\n---\n# Extra\n",
            encoding="utf-8",
        )
    return cap_dir


def test_sync_refreshes_installed_capability(
    installed_target: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Per COR-017 auto-upgrade: sync re-copies installed capability content from source."""
    from project_kit import capabilities as caps

    # Build a fake source kit in a sibling tmp dir with one capability.
    fake_source = tmp_path / "fake-source" / ".pkit"
    fake_source.mkdir(parents=True)
    # Copy minimum scaffolding from the real source so install_capability's
    # backbone-manifest stamp works against the adopter (which uses the
    # real installed manifest).
    cap_dir = _stage_capability_in_source(fake_source, "evidence")

    # Stage the capability as installed in the adopter (use the real
    # find_source_kit-pointing capability install machinery, then swap
    # the source for sync).
    source = caps.find_capability_in_source(fake_source, "evidence")
    assert source is not None
    caps.install_capability(installed_target, source)

    skill_dest = (
        installed_target / ".pkit" / "capabilities" / "evidence" / "skills" / "evidence-skill.md"
    )
    assert skill_dest.is_file()

    # Modify the source skill so sync has something to refresh.
    (cap_dir / "skills" / "evidence-skill.md").write_text(
        "---\nname: evidence-skill\n---\n# Updated body\n", encoding="utf-8"
    )

    # Point find_source_kit at the fake source so sync sees our capability.
    monkeypatch.setattr(install, "find_source_kit", lambda: fake_source)
    monkeypatch.setattr(sync.install, "find_source_kit", lambda: fake_source)

    sync.run_sync(installed_target)

    refreshed = skill_dest.read_text(encoding="utf-8")
    assert "Updated body" in refreshed


def test_sync_warns_when_capability_no_longer_in_source(
    installed_target: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Sync surfaces 'orphan' for installed capabilities that vanished from source.

    Per COR-017 we warn but do NOT remove — adopters chose to install
    and the kit shouldn't yank content out on sync.
    """
    from project_kit import capabilities as caps

    # Stage + install from fake source A.
    fake_source = tmp_path / "fake-source" / ".pkit"
    fake_source.mkdir(parents=True)
    _stage_capability_in_source(fake_source, "ghost")
    source = caps.find_capability_in_source(fake_source, "ghost")
    assert source is not None
    caps.install_capability(installed_target, source)

    # Now point sync at a *different* source (B) that doesn't ship 'ghost'.
    fake_source_b = tmp_path / "fake-source-b" / ".pkit"
    fake_source_b.mkdir(parents=True)
    monkeypatch.setattr(install, "find_source_kit", lambda: fake_source_b)
    monkeypatch.setattr(sync.install, "find_source_kit", lambda: fake_source_b)

    # Required scaffolding so the early _refuse_if_source_kit_missing
    # equivalent doesn't trip and sync's manifest update has a VERSION.
    (fake_source_b / "decisions").mkdir()
    (fake_source_b / "VERSION").write_text("1.0.0\n", encoding="utf-8")

    sync.run_sync(installed_target)
    out = capsys.readouterr().out
    assert "orphan" in out
    assert "ghost" in out
    # Tree on disk is untouched.
    ghost_dir = installed_target / ".pkit" / "capabilities" / "ghost"
    assert ghost_dir.is_dir()


def test_install_kit_stamps_backbone_manifest(installed_target: Path) -> None:
    """PR-G wires init: a fresh install leaves a stamped backbone manifest.

    PR-J extended this: installed adapters are auto-registered in the
    components registry (so `pkit upgrade`'s compatibility check sees
    them). The fixture's install ships the `claude-code` adapter.
    """
    manifest = read_backbone_manifest(installed_target)
    assert manifest is not None
    assert manifest.backbone_version  # non-empty
    assert manifest.schema_version == 1
    assert len(manifest.components) == 1
    assert manifest.components[0].kind == "adapter"
    assert manifest.components[0].name == "claude-code"


# ── rules area sync preservation (issue #96) ──────────────────────────────


def test_sync_refreshes_rules_core_md(installed_target: Path) -> None:
    """Sync propagates an updated core.md (kit-owned) into the adopter tree."""
    core_md = installed_target / ".pkit" / "rules" / "core.md"
    assert core_md.is_file(), "core.md must exist after install"
    # Overwrite with stale content to simulate a pre-update adopter.
    core_md.write_text("# stale\n", encoding="utf-8")

    sync.run_sync(installed_target)

    refreshed = core_md.read_text(encoding="utf-8")
    assert "stale" not in refreshed, "sync did not refresh core.md"
    assert len(refreshed) > 50, "refreshed core.md looks unexpectedly short"


def test_sync_does_not_overwrite_rules_project_md(installed_target: Path) -> None:
    """project.md is adopter-owned; sync must never overwrite it."""
    project_md = installed_target / ".pkit" / "rules" / "project.md"
    adopter_content = "# My project rules\n\nCustom adopter rule.\n"
    project_md.write_text(adopter_content, encoding="utf-8")

    sync.run_sync(installed_target)

    assert project_md.is_file(), "sync removed the adopter's project.md"
    assert project_md.read_text(encoding="utf-8") == adopter_content, (
        "sync clobbered the adopter's project.md"
    )
