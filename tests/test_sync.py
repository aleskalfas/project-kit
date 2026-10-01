"""Tests for `pkit sync` (PR-G of the build roadmap)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import click
import pytest

from project_kit import install, router, sync
from project_kit.manifest import read_backbone_manifest, read_kit_version, write_backbone_manifest
from tests.adopter_repo import MakeAdopterRepo

# The backbone version an installed fixture records: the real source kit's. A
# fake source a capability test stages carries it too, since sync refuses a
# source older than the project's content outright (#1212).
_INSTALLED_BACKBONE = read_kit_version(install.find_source_kit())


@pytest.fixture
def installed_target(make_adopter_repo: MakeAdopterRepo) -> Path:
    """A git repo with the kit already installed; ready for sync."""
    return make_adopter_repo().root


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

    called = {"deploy": 0, "render": 0, "workspace": 0, "provision": 0}

    def _spy_deploy(_ctx: install.InstallContext) -> None:
        called["deploy"] += 1

    def _no_propagate(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("self-host sync must not propagate (copy onto source)")

    # Spy the core-tier renderer so we assert it runs on the self-host path
    # WITHOUT writing `.pkit/.gitignore` into the real source tree.
    def _spy_render(_ctx: install.InstallContext) -> None:
        called["render"] += 1

    # Likewise the agent-workspace step: it runs on self-host, but must not
    # write the folder or an exclude entry into the real source clone here.
    def _spy_workspace(_ctx: install.InstallContext) -> None:
        called["workspace"] += 1

    # And the provisioning step, which must not ask uv about the real checkout's
    # query commands here.
    def _spy_provision(_ctx: install.InstallContext) -> None:
        called["provision"] += 1

    monkeypatch.setattr(install, "run_installed_adapter_primitives", _spy_deploy)
    monkeypatch.setattr(install, "_install_area", _no_propagate)
    monkeypatch.setattr(install, "_render_runtime_ignore", _spy_render)
    monkeypatch.setattr(install, "ensure_agent_workspace", _spy_workspace)
    monkeypatch.setattr(install, "provision_query_commands", _spy_provision)

    sync.run_sync(source_repo)  # must not raise

    assert called["deploy"] == 1
    # The renderer is a CORE step, not an adapter primitive — it must run on the
    # self-host short-circuit too (ADR-009 rule 7), or backbone /
    # capability runtime ignores would never render without an adapter.
    assert called["render"] == 1
    # So is the workspace step (#1043): the methodology's own checkout gets one.
    assert called["workspace"] == 1
    # And provisioning (#1092): it readies the checkout for an offline validate.
    assert called["provision"] == 1


def test_sync_renders_runtime_ignore_on_normal_path(installed_target: Path) -> None:
    # The normal (non-self-host) sync path renders `.pkit/.gitignore` at the
    # core tier — proving the renderer is wired into BOTH sync code paths.
    (installed_target / ".pkit" / ".gitignore").unlink(missing_ok=True)
    sync.run_sync(installed_target)
    gi = installed_target / ".pkit" / ".gitignore"
    assert gi.is_file()
    assert "pkit-owned" in gi.read_text(encoding="utf-8")


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
    # Install no longer seeds the source project's own `project/` files (#812),
    # so the adopter authors their config here — which is what a real adopter
    # does, and what makes this test's subject (no-clobber on sync) meaningful
    # rather than incidental to a seed.
    assert not config.exists(), "install must not seed the source project's config"
    config.parent.mkdir(parents=True, exist_ok=True)
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
    orphan = installed_target / ".pkit" / "adapters" / "claude-code" / "deploy-removed.sh"
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
    project_skill.write_text("---\nname: my-skill\n---\nadopter skill body\n", encoding="utf-8")

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

    def _fake_run(cmd, **kwargs):
        return sp.CompletedProcess(args=cmd, returncode=1)

    monkeypatch.setattr(install.subprocess, "run", _fake_run)
    ctx = install.InstallContext(target_root=tmp_path, source_kit=tmp_path, dry_run=False)

    with pytest.raises(click.ClickException, match="exited with status 1"):
        install._run_adapter_primitive(script, ctx)


def _stage_capability_in_source(
    source_kit: Path,
    name: str,
    *,
    skill_body: str = "# Skill\n",
    extra_decision: str | None = None,
    version: str = "1.0.0",
) -> Path:
    """Create a capability under source_kit/capabilities/<name>/ for sync tests.

    Mirrors the layout `pkit capabilities install` expects in source:
    package.yaml + skills/ + decisions/. Also stamps a VERSION + decisions/
    scaffold so sync's _update_recorded_backbone_version + the
    source-kit-missing guard don't trip.

    ``version`` sets the capability's package.yaml version, letting a test
    stage a source that is older / equal / newer than an installed copy —
    the axis the #524 downgrade guard turns on.
    """
    cap_dir = source_kit / "capabilities" / name
    (cap_dir / "skills").mkdir(parents=True, exist_ok=True)
    (cap_dir / "decisions").mkdir(parents=True, exist_ok=True)
    # Sync's manifest update needs a VERSION file in the source.
    version_file = source_kit / "VERSION"
    if not version_file.is_file():
        version_file.write_text(f"{_INSTALLED_BACKBONE}\n", encoding="utf-8")
    # Sync's _refuse_if_source_kit_missing equivalent wants decisions/.
    (source_kit / "decisions").mkdir(parents=True, exist_ok=True)
    (cap_dir / "package.yaml").write_text(
        f"""component:
  kind: capability
  name: {name}
  version: {version}
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
    installed_target: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
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
    (fake_source_b / "VERSION").write_text(f"{_INSTALLED_BACKBONE}\n", encoding="utf-8")

    sync.run_sync(installed_target)
    out = capsys.readouterr().out
    assert "orphan" in out
    assert "ghost" in out
    # Tree on disk is untouched.
    ghost_dir = installed_target / ".pkit" / "capabilities" / "ghost"
    assert ghost_dir.is_dir()


# --- downgrade guard: a stale source must not clobber a newer install (#524) ---


def _install_then_repoint_source(
    installed_target: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    name: str,
    *,
    installed_version: str,
    source_version: str,
) -> Path:
    """Install `name` at `installed_version`, then repoint sync at a source at `source_version`.

    Returns the capability's skill file in the adopter (so a test can assert
    whether a refresh reached it). The installed copy is staged from a source
    at `installed_version`; sync is then pointed at a *fresh* source tree
    whose same-named capability sits at `source_version` — the two versions
    are the downgrade-guard axis.
    """
    from project_kit import capabilities as caps

    install_source = tmp_path / "install-source" / ".pkit"
    install_source.mkdir(parents=True)
    _stage_capability_in_source(install_source, name, version=installed_version)
    source = caps.find_capability_in_source(install_source, name)
    assert source is not None
    caps.install_capability(installed_target, source)

    # A distinct source tree carrying the (older / equal / newer) version.
    sync_source = tmp_path / "sync-source" / ".pkit"
    sync_source.mkdir(parents=True)
    _stage_capability_in_source(
        sync_source, name, version=source_version, skill_body="# From sync source\n"
    )
    monkeypatch.setattr(install, "find_source_kit", lambda: sync_source)
    monkeypatch.setattr(sync.install, "find_source_kit", lambda: sync_source)

    return installed_target / ".pkit" / "capabilities" / name / "skills" / f"{name}-skill.md"


def test_sync_refuses_downgrade_and_leaves_tree_untouched(
    installed_target: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The trip-planner failure (#524): source older than installed → refuse, do not refresh."""
    skill = _install_then_repoint_source(
        installed_target,
        monkeypatch,
        tmp_path,
        "software-engineering",
        installed_version="0.3.0",
        source_version="0.1.0",
    )
    before = skill.read_text(encoding="utf-8")

    sync.run_sync(installed_target)
    out = capsys.readouterr().out

    # Refused, naming both versions; the installed tree is byte-for-byte intact.
    assert "refused" in out
    assert "software-engineering" in out
    assert "0.1.0" in out and "0.3.0" in out
    assert skill.read_text(encoding="utf-8") == before
    assert "From sync source" not in skill.read_text(encoding="utf-8")


def test_sync_force_proceeds_with_downgrade_loudly(
    installed_target: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """--force overrides the guard: the downgrade proceeds, but a loud line records it."""
    skill = _install_then_repoint_source(
        installed_target,
        monkeypatch,
        tmp_path,
        "software-engineering",
        installed_version="0.3.0",
        source_version="0.1.0",
    )

    sync.run_sync(installed_target, force=True)
    out = capsys.readouterr().out

    # Loud downgrade line naming both versions; the older source content lands.
    assert "downgrade" in out
    assert "0.1.0" in out and "0.3.0" in out
    assert "From sync source" in skill.read_text(encoding="utf-8")


def test_sync_refreshes_normally_when_source_newer(
    installed_target: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Source newer than installed is a normal upgrade — the guard does not fire."""
    skill = _install_then_repoint_source(
        installed_target,
        monkeypatch,
        tmp_path,
        "evidence",
        installed_version="0.1.0",
        source_version="0.3.0",
    )

    sync.run_sync(installed_target)
    out = capsys.readouterr().out

    assert "refreshed" in out
    assert "refused" not in out
    assert "From sync source" in skill.read_text(encoding="utf-8")


def test_sync_refreshes_when_source_equal(
    installed_target: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Equal versions are not a downgrade — refresh proceeds unchanged."""
    skill = _install_then_repoint_source(
        installed_target,
        monkeypatch,
        tmp_path,
        "evidence",
        installed_version="0.2.0",
        source_version="0.2.0",
    )

    sync.run_sync(installed_target)
    out = capsys.readouterr().out

    assert "refreshed" in out
    assert "refused" not in out
    assert "From sync source" in skill.read_text(encoding="utf-8")


def test_sync_dry_run_previews_downgrade_refusal_and_writes_nothing(
    installed_target: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Dry-run over a downgrade previews the refusal (not a 'would refresh') and writes nothing."""
    skill = _install_then_repoint_source(
        installed_target,
        monkeypatch,
        tmp_path,
        "software-engineering",
        installed_version="0.3.0",
        source_version="0.1.0",
    )
    before = skill.read_text(encoding="utf-8")

    sync.run_sync(installed_target, dry_run=True)
    out = capsys.readouterr().out

    assert "refused" in out
    assert "would refresh" not in out
    assert skill.read_text(encoding="utf-8") == before


# --- incubated (in-repo) capabilities skip source-reconciliation (COR-031) ---


def _stage_incubated_capability(
    target_root: Path,
    name: str,
    *,
    skill_body: str = "# Skill\n",
) -> Path:
    """Stage + register an in-repo (incubated) capability in the adopter.

    The subtree lives under the adopter's own `.pkit/capabilities/<name>/`
    (the working tree *is* the source — COR-031), and registration records
    `origin: incubated-in-repo` without copying.
    """
    from project_kit import capabilities as caps

    cap_dir = target_root / ".pkit" / "capabilities" / name
    (cap_dir / "skills").mkdir(parents=True, exist_ok=True)
    (cap_dir / "package.yaml").write_text(
        f"""schema_version: 1
component:
  kind: capability
  name: {name}
  version: 0.1.0
description: Home-grown capability.
requires_backbone: ">=0.0.0"
""",
        encoding="utf-8",
    )
    (cap_dir / "skills" / f"{name}-skill.md").write_text(
        f"---\nname: {name}-skill\n---\n{skill_body}",
        encoding="utf-8",
    )
    source = caps.find_capability_in_repo(target_root, name)
    assert source is not None
    caps.register_incubated_capability(target_root, source)
    return cap_dir


def test_sync_skips_source_reconciliation_for_incubated_capability(
    installed_target: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """An incubated capability is left untouched by sync — no refresh, no orphan warning.

    Per COR-031 D1, an in-repo capability is adopter-owned: sync skips
    source-reconciliation entirely. It must not be re-copied from a
    (non-existent) kit source, and it must not be misflagged "no longer
    shipped" — the warning kit-shipped capabilities get when their source
    vanishes.
    """
    cap_dir = _stage_incubated_capability(installed_target, "homegrown")
    skill = cap_dir / "skills" / "homegrown-skill.md"
    # Adopter edits the skill — sync must preserve this exactly.
    adopter_body = "---\nname: homegrown-skill\n---\n# Adopter-authored body\n"
    skill.write_text(adopter_body, encoding="utf-8")

    # Point sync at a fake source that ships NO capability of this name.
    fake_source = tmp_path / "fake-source" / ".pkit"
    fake_source.mkdir(parents=True)
    (fake_source / "decisions").mkdir()
    (fake_source / "VERSION").write_text(f"{_INSTALLED_BACKBONE}\n", encoding="utf-8")
    monkeypatch.setattr(install, "find_source_kit", lambda: fake_source)
    monkeypatch.setattr(sync.install, "find_source_kit", lambda: fake_source)

    sync.run_sync(installed_target)

    out = capsys.readouterr().out
    # Reported as incubated/skipped, never orphaned.
    assert "homegrown" in out
    assert "orphan" not in out
    assert "incubated" in out
    # Adopter's edits survive untouched.
    assert skill.read_text(encoding="utf-8") == adopter_body


def test_sync_still_registers_incubated_capability_after_run(
    installed_target: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Skipping reconciliation does not unregister the incubated capability.

    Origin governs source-reconciliation only — the capability stays
    installed (and so keeps counting for dependency-gating + deploy, COR-031
    D1) across a sync.
    """
    from project_kit import capabilities as caps

    _stage_incubated_capability(installed_target, "homegrown")

    fake_source = tmp_path / "fake-source" / ".pkit"
    fake_source.mkdir(parents=True)
    (fake_source / "decisions").mkdir()
    (fake_source / "VERSION").write_text(f"{_INSTALLED_BACKBONE}\n", encoding="utf-8")
    monkeypatch.setattr(install, "find_source_kit", lambda: fake_source)
    monkeypatch.setattr(sync.install, "find_source_kit", lambda: fake_source)

    sync.run_sync(installed_target)

    assert caps.is_installed(installed_target, "homegrown")


def test_sync_surfaces_collision_when_kit_ships_same_named_capability(
    installed_target: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Boundary case (COR-031): kit now ships a capability named like an incubated one.

    Graduation arriving unbidden. The lifecycle must SURFACE the collision so
    the adopter can decide, rather than silently skipping. Source-
    reconciliation stays suppressed (the incubated tree is not overwritten),
    but a collision notice is emitted.
    """
    cap_dir = _stage_incubated_capability(installed_target, "homegrown")
    skill = cap_dir / "skills" / "homegrown-skill.md"
    adopter_body = "---\nname: homegrown-skill\n---\n# Adopter-authored body\n"
    skill.write_text(adopter_body, encoding="utf-8")

    # Fake source that DOES ship a same-named capability (different version).
    fake_source = tmp_path / "fake-source" / ".pkit"
    fake_source.mkdir(parents=True)
    cap_in_source = _stage_capability_in_source(fake_source, "homegrown")
    # Distinguish the kit version so the notice is meaningful.
    (cap_in_source / "package.yaml").write_text(
        """component:
  kind: capability
  name: homegrown
  version: 2.0.0
description: Kit-shipped homegrown.
requires_backbone: ">=0.0.0"
schema_version: 1
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(install, "find_source_kit", lambda: fake_source)
    monkeypatch.setattr(sync.install, "find_source_kit", lambda: fake_source)

    sync.run_sync(installed_target)

    out = capsys.readouterr().out
    assert "collision" in out
    assert "homegrown" in out
    # The kit version is surfaced so the adopter knows what's now available.
    assert "2.0.0" in out
    # Reconciliation stays suppressed: the adopter's tree is NOT overwritten.
    assert skill.read_text(encoding="utf-8") == adopter_body


def test_sync_dry_run_does_not_refresh_incubated_capability(
    installed_target: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Dry-run sync leaves an incubated capability's adopter-owned tree untouched."""
    cap_dir = _stage_incubated_capability(installed_target, "homegrown")
    skill = cap_dir / "skills" / "homegrown-skill.md"
    adopter_body = "---\nname: homegrown-skill\n---\n# Adopter body\n"
    skill.write_text(adopter_body, encoding="utf-8")
    pre_mtime = skill.stat().st_mtime

    fake_source = tmp_path / "fake-source" / ".pkit"
    fake_source.mkdir(parents=True)
    (fake_source / "decisions").mkdir()
    (fake_source / "VERSION").write_text(f"{_INSTALLED_BACKBONE}\n", encoding="utf-8")
    monkeypatch.setattr(install, "find_source_kit", lambda: fake_source)
    monkeypatch.setattr(sync.install, "find_source_kit", lambda: fake_source)

    sync.run_sync(installed_target, dry_run=True)

    assert skill.read_text(encoding="utf-8") == adopter_body
    assert skill.stat().st_mtime == pre_mtime


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


def test_sync_refuses_cleanly_when_source_incomplete(
    installed_target: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An incomplete resolved source yields a clean ClickException, not a raw crash.

    Guards against a future incomplete bundle (ADR-033 / issue #333): with the
    resolved source lacking the `decisions/` discriminator, sync must refuse
    before `read_kit_version` / propagation rather than letting a raw
    `FileNotFoundError` escape from deep inside. The stand-in source lives off
    the adopter root so the self-host branch (source.parent == target) is not
    taken.
    """
    incomplete = tmp_path / "broken-source" / ".pkit"
    incomplete.mkdir(parents=True)  # no decisions/ subdir
    monkeypatch.setattr(install, "find_source_kit", lambda: incomplete)

    with pytest.raises(click.ClickException, match="methodology source not found"):
        sync.run_sync(installed_target)


# --- an older pkit never takes a project back (#1212) ---------------------------

# A version no release reaches: the project's content or pin, ahead of this pkit.
_NEWER = "999.0.0"


def _record_content_version(target: Path, version: str) -> None:
    """Record *version* as the project's content version, as a newer pkit's sync would."""
    manifest = read_backbone_manifest(target)
    assert manifest is not None
    manifest.backbone_version = version
    write_backbone_manifest(target, manifest)


def _write_pin(target: Path, version: str) -> None:
    router.pin_file_path(target).write_text(f"{version}\n", encoding="utf-8")


def _tree_bytes(root: Path) -> dict[str, bytes | None]:
    """Every path under *root* outside `.git/`, with a file's bytes (None for a
    directory): what a refusal must leave exactly as it was."""
    return {
        path.relative_to(root).as_posix(): path.read_bytes() if path.is_file() else None
        for path in sorted(root.rglob("*"))
        if path.relative_to(root).parts[0] != ".git"
    }


@pytest.mark.parametrize("pinned", [False, True], ids=["no-pin", "pinned"])
def test_sync_refuses_content_newer_than_this_pkit_and_writes_nothing(
    installed_target: Path, pinned: bool
) -> None:
    """The router's offline fallback runs an older pkit over newer content, pinned
    or not: sync refuses, naming both versions and the way to the right pkit, and
    leaves the tree, pin included, byte-identical."""
    _record_content_version(installed_target, _NEWER)
    if pinned:
        _write_pin(installed_target, _NEWER)
    before = _tree_bytes(installed_target)

    with pytest.raises(click.ClickException) as excinfo:
        sync.run_sync(installed_target)

    message = excinfo.value.message
    assert f"this pkit is {_INSTALLED_BACKBONE}, older than this project's content ({_NEWER}" in (
        message
    )
    assert "Nothing was written" in message
    assert f"{router.DISTRIBUTION_GIT_URL}@v{_NEWER} project-kit sync" in message
    if pinned:
        assert f"pin ({_NEWER}, in .pkit/version-pin)" in message
        assert "reconnect" in message
        assert "`pkit pin <version>`" in message
    else:
        assert f"uv tool install --force {router.DISTRIBUTION_GIT_URL}@v{_NEWER}" in message
    assert _tree_bytes(installed_target) == before


def test_sync_refuses_a_pin_newer_than_this_pkit(installed_target: Path) -> None:
    """The pin names the version the project runs at, so a pin ahead of this pkit
    refuses even where the recorded content is this pkit's own version."""
    _write_pin(installed_target, _NEWER)
    before = _tree_bytes(installed_target)

    with pytest.raises(click.ClickException) as excinfo:
        sync.run_sync(installed_target)

    message = excinfo.value.message
    assert f"older than this project's pin ({_NEWER}, in .pkit/version-pin)" in message
    assert "content (" not in message
    assert _tree_bytes(installed_target) == before


def test_sync_names_pinning_at_the_content_when_the_content_is_ahead_of_the_pin(
    installed_target: Path,
) -> None:
    """Content ahead of its pin, as an interrupted pin raise leaves it: the remedy is
    pinning at the content, which needs no fetch."""
    _record_content_version(installed_target, _NEWER)
    _write_pin(installed_target, _INSTALLED_BACKBONE)

    with pytest.raises(click.ClickException) as excinfo:
        sync.run_sync(installed_target)

    assert f"run `pkit pin {_NEWER}`" in excinfo.value.message
    assert router.read_version_pin(installed_target) == _INSTALLED_BACKBONE


@pytest.mark.parametrize("flags", [{"force": True}, {"dry_run": True}], ids=["force", "dry-run"])
def test_sync_content_downgrade_refusal_has_no_override(
    installed_target: Path, flags: dict[str, bool]
) -> None:
    """`--force` overrides only the capability guard, and a dry run refuses too."""
    _record_content_version(installed_target, _NEWER)
    before = _tree_bytes(installed_target)

    with pytest.raises(click.ClickException, match="no flag overrides this refusal"):
        sync.run_sync(installed_target, **flags)

    assert _tree_bytes(installed_target) == before


def test_cli_sync_exits_non_zero_on_the_content_downgrade_refusal(installed_target: Path) -> None:
    from click.testing import CliRunner

    from project_kit.cli import main

    _record_content_version(installed_target, _NEWER)

    result = CliRunner().invoke(main, ["sync"])

    assert result.exit_code != 0
    assert "refusing to run `pkit sync`" in result.output


def test_sync_at_the_content_version_proceeds(installed_target: Path) -> None:
    """This pkit at the project's content and pin: sync runs as before."""
    _write_pin(installed_target, _INSTALLED_BACKBONE)

    sync.run_sync(installed_target)  # must not raise

    manifest = read_backbone_manifest(installed_target)
    assert manifest is not None
    assert manifest.backbone_version == _INSTALLED_BACKBONE
    assert router.read_version_pin(installed_target) == _INSTALLED_BACKBONE


def test_sync_newer_than_the_content_moves_it_forward(installed_target: Path) -> None:
    """This pkit newer than the project's content and pin: sync moves the content
    forward as before, and leaves the pin to the pin gestures."""
    _record_content_version(installed_target, "0.1.0")
    _write_pin(installed_target, "0.1.0")

    sync.run_sync(installed_target)

    manifest = read_backbone_manifest(installed_target)
    assert manifest is not None
    assert manifest.backbone_version == _INSTALLED_BACKBONE
    assert router.read_version_pin(installed_target) == "0.1.0"


@pytest.mark.parametrize("unreadable", ["content", "pin"])
def test_sync_does_not_order_a_version_that_is_not_one(
    installed_target: Path, unreadable: str
) -> None:
    """Only an unambiguous downgrade refuses: a corrupt content version is one sync
    repairs, and a pin that is not a version has no order to keep."""
    if unreadable == "content":
        _record_content_version(installed_target, "not-a-version")
    else:
        _write_pin(installed_target, "main")

    sync.run_sync(installed_target)  # must not raise

    manifest = read_backbone_manifest(installed_target)
    assert manifest is not None
    assert manifest.backbone_version == _INSTALLED_BACKBONE


def test_read_only_commands_run_under_a_pkit_older_than_the_content(
    installed_target: Path,
) -> None:
    """The refusal is sync's and upgrade's alone: a read-only command still runs."""
    from click.testing import CliRunner

    from project_kit.cli import main

    _record_content_version(installed_target, _NEWER)
    _write_pin(installed_target, _NEWER)

    result = CliRunner().invoke(main, ["status"])

    assert result.exit_code == 0, result.output
    assert _NEWER in result.output
