"""Tests for `pkit sync` (PR-G of the build roadmap)."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

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
# adopter-owned `project/` content (never overwrite/remove on refresh).
# `pkit sync` fans out to three structurally-different copy primitives —
# `_install_area` (backbone areas), `_install_adapter` (harness adapters), and
# `_copy_capability_tree` via `copy_shipped_capability` (installed
# capabilities). Each enforces the rule with its own mechanics, so each needs
# its own preservation guard at the `run_sync` entry point. The capability case
# is the one that regressed in #332 (its guard lived only at the refresh's unit
# level, a rung below `run_sync`).
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


# Each seed path a project deleted (ADR-065 point 11), relative to the project root.
_SEED_PATHS = (
    ".pkit/agents/project",
    ".pkit/decisions/project",
    ".pkit/agents/project/overlay.yaml",
    ".pkit/adapters/claude-code/settings/project/settings.json",
    ".pkit/adapters/claude-code/settings/project",
    ".pkit/scratchpad/active",
)


@pytest.mark.parametrize("seed", _SEED_PATHS)
def test_sync_creates_no_seed_path(installed_target: Path, seed: str) -> None:
    """A seed path the project deleted stays deleted: sync creates none, so a seed
    removed on purpose does not return on every routine run (COR-059 point 8). The
    next transition creates it where missing, and `pkit agents reconcile --write`
    repairs a missing overlay."""
    import shutil

    path = installed_target / seed
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()

    sync.run_sync(installed_target)

    assert not path.exists(), f"sync created the seed path {seed}"


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
    package.yaml + skills/ + decisions/. Also stamps a VERSION, at the version
    the installed fixture records so sync's guard lets it run, and the
    decisions/ scaffold the source-kit-missing guard reads.

    ``version`` sets the capability's package.yaml version, letting a test
    stage a source that is older / equal / newer than an installed copy —
    the axis sync's handling of each capability turns on (ADR-065 point 1).
    """
    cap_dir = source_kit / "capabilities" / name
    (cap_dir / "skills").mkdir(parents=True, exist_ok=True)
    (cap_dir / "decisions").mkdir(parents=True, exist_ok=True)
    # Sync's guard reads the source's VERSION, the version the fixture records.
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
    # equivalent doesn't trip and sync's guard reads the recorded version.
    (fake_source_b / "decisions").mkdir()
    (fake_source_b / "VERSION").write_text(f"{_INSTALLED_BACKBONE}\n", encoding="utf-8")

    sync.run_sync(installed_target)
    out = capsys.readouterr().out
    assert "orphan" in out
    assert "ghost" in out
    # Tree on disk is untouched.
    ghost_dir = installed_target / ".pkit" / "capabilities" / "ghost"
    assert ghost_dir.is_dir()


# --- each capability by its recorded version: a stale source never clobbers (#524) ---


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


def test_sync_skips_a_capability_the_bundle_ships_older_and_leaves_its_tree(
    installed_target: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The trip-planner failure (#524): a source older than the record is skipped and
    reported, never copied, and nothing overrides it (ADR-065 point 1)."""
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

    # Skipped, naming both versions; the installed tree is byte-for-byte intact.
    assert "skipped" in out
    assert "'software-engineering'" in out
    assert "v0.1.0, older than the recorded v0.3.0" in out
    assert "never moves down" in out
    assert skill.read_text(encoding="utf-8") == before
    assert "From sync source" not in skill.read_text(encoding="utf-8")


def test_cli_sync_force_is_accepted_ignored_and_reported(
    installed_target: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """`pkit sync --force` is accepted for one release, ignored and reported: it no
    longer copies an older capability over a newer one (ADR-065 point 10)."""
    skill = _install_then_repoint_source(
        installed_target,
        monkeypatch,
        tmp_path,
        "software-engineering",
        installed_version="0.3.0",
        source_version="0.1.0",
    )
    before = skill.read_text(encoding="utf-8")

    result = _cli_sync("--force")

    assert result.exit_code == 0, result.output
    assert sync.SYNC_FORCE_IGNORED in result.output
    assert "Sync complete." in result.output
    assert skill.read_text(encoding="utf-8") == before


def test_sync_leaves_a_capability_the_bundle_ships_newer_to_upgrade(
    installed_target: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A source newer than the record is a move, which only a transition makes: sync
    skips it, reports it pending `pkit upgrade`, and runs none of its migrations."""
    skill = _install_then_repoint_source(
        installed_target,
        monkeypatch,
        tmp_path,
        "evidence",
        installed_version="0.1.0",
        source_version="0.3.0",
    )
    migrations = tmp_path / "sync-source" / ".pkit" / "capabilities" / "evidence" / "migrations"
    script = migrations / "0.3.0" / "001-mark.sh"
    script.parent.mkdir(parents=True)
    script.write_text('#!/usr/bin/env bash\nset -euo pipefail\ntouch "$ROOT/migrated"\n')
    record = _record(installed_target, "evidence")
    recorded = record.read_bytes()

    sync.run_sync(installed_target)
    out = capsys.readouterr().out

    assert "pending" in out
    assert "the bundle ships v0.3.0, and the project records v0.1.0" in out
    assert "`pkit upgrade` moves it" in out
    assert "From sync source" not in skill.read_text(encoding="utf-8")
    assert not (installed_target / "migrated").exists()
    assert record.read_bytes() == recorded


def test_sync_copies_a_capability_at_its_recorded_version(
    installed_target: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Bundled at the recorded version: the one case sync copies, with no stamp."""
    skill = _install_then_repoint_source(
        installed_target,
        monkeypatch,
        tmp_path,
        "evidence",
        installed_version="0.2.0",
        source_version="0.2.0",
    )
    record = _record(installed_target, "evidence")
    recorded = record.read_bytes()

    sync.run_sync(installed_target)
    out = capsys.readouterr().out

    assert "copied       'evidence' at v0.2.0" in out
    assert "From sync source" in skill.read_text(encoding="utf-8")
    assert record.read_bytes() == recorded, "sync wrote the capability's manifest"


def test_sync_dry_run_over_an_older_bundle_reports_the_skip_and_writes_nothing(
    installed_target: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A dry run reports the skip as the run would, and writes nothing."""
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

    assert "skipped" in out
    assert "would copy" not in out
    assert skill.read_text(encoding="utf-8") == before


# --- the capability's record, under its project/ (ADR-065 point 2) ---


def _record(target: Path, name: str, *, at_root: bool = False) -> Path:
    cap = target / ".pkit" / "capabilities" / name
    return cap / "manifest.yaml" if at_root else cap / "project" / "manifest.yaml"


def _installed_with_skip(
    installed_target: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, name: str
) -> Path:
    """Install `name` at 0.1.0 with its skill skipped, then point sync at a 0.1.0 source
    that still ships the skill. Returns the skill's path in the project."""
    from project_kit import capabilities as caps

    install_source = tmp_path / "install-source" / ".pkit"
    install_source.mkdir(parents=True)
    _stage_capability_in_source(install_source, name, version="0.1.0")
    source = caps.find_capability_in_source(install_source, name)
    assert source is not None
    caps.install_capability(
        installed_target, source, skipped_artifacts=(("skill", f"{name}-skill"),)
    )

    sync_source = tmp_path / "sync-source" / ".pkit"
    sync_source.mkdir(parents=True)
    _stage_capability_in_source(sync_source, name, version="0.1.0")
    monkeypatch.setattr(install, "find_source_kit", lambda: sync_source)
    monkeypatch.setattr(sync.install, "find_source_kit", lambda: sync_source)
    return installed_target / ".pkit" / "capabilities" / name / "skills" / f"{name}-skill.md"


def test_sync_keeps_an_artefact_the_project_skipped(
    installed_target: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The skip is read from the record, so the copy leaves the skill out again, and
    the record is left as it was."""
    from project_kit.manifest import read_component_manifest

    skill = _installed_with_skip(installed_target, monkeypatch, tmp_path, "evidence")
    assert not skill.exists()
    recorded = _record(installed_target, "evidence").read_bytes()

    sync.run_sync(installed_target)
    sync.run_sync(installed_target)

    assert not skill.exists()
    assert _record(installed_target, "evidence").read_bytes() == recorded
    record = read_component_manifest(_record(installed_target, "evidence"))
    assert record is not None
    assert record.version == "0.1.0"
    assert record.backend_state["skipped"] == [{"kind": "skill", "name": "evidence-skill"}]


def test_sync_skips_a_capability_whose_record_is_still_at_the_root(
    installed_target: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A record an older release left at the root: sync never moves a record, and the
    copy would prune it there, so sync skips the capability and names `pkit upgrade`,
    which moves it (ADR-065 point 2)."""
    from project_kit.manifest import set_component_manifest_path

    _installed_with_skip(installed_target, monkeypatch, tmp_path, "evidence")
    root = _record(installed_target, "evidence", at_root=True)
    _record(installed_target, "evidence").rename(root)
    set_component_manifest_path(
        installed_target, "capability", "evidence", ".pkit/capabilities/evidence/manifest.yaml"
    )
    recorded = root.read_bytes()
    stale = installed_target / ".pkit" / "capabilities" / "evidence" / "skills" / "stale.md"
    stale.write_text("not in the bundle\n", encoding="utf-8")

    sync.run_sync(installed_target)
    out = capsys.readouterr().out

    assert root.read_bytes() == recorded
    assert not _record(installed_target, "evidence").exists()
    assert stale.is_file(), "sync copied a capability whose record is at the root"
    assert "pending" in out
    assert "its manifest is still at the capability's root" in out
    backbone = read_backbone_manifest(installed_target)
    assert backbone is not None
    assert {c.name: c.manifest for c in backbone.components}["evidence"] == (
        ".pkit/capabilities/evidence/manifest.yaml"
    )


def test_sync_reads_every_record_before_it_copies_anything(
    installed_target: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from project_kit import capabilities as caps

    install_source = tmp_path / "install-source" / ".pkit"
    install_source.mkdir(parents=True)
    for name in ("audit", "evidence"):
        _stage_capability_in_source(install_source, name, version="0.1.0")
        source = caps.find_capability_in_source(install_source, name)
        assert source is not None
        caps.install_capability(installed_target, source)
    sync_source = tmp_path / "sync-source" / ".pkit"
    sync_source.mkdir(parents=True)
    for name in ("audit", "evidence"):
        _stage_capability_in_source(sync_source, name, version="0.1.0")
    monkeypatch.setattr(install, "find_source_kit", lambda: sync_source)
    monkeypatch.setattr(sync.install, "find_source_kit", lambda: sync_source)

    events: list[str] = []
    read, copy_area, copy_capability = (
        caps.read_capability_record,
        install._install_area,
        caps._copy_capability_tree,
    )

    def _read(target_root: Path, name: str) -> caps.CapabilityRecord:
        events.append(f"read {name}")
        return read(target_root, name)

    def _copy_area(*args: Any, **kwargs: Any) -> None:
        events.append("copy")
        copy_area(*args, **kwargs)

    def _copy_capability(*args: Any, **kwargs: Any) -> None:
        events.append("copy capability")
        copy_capability(*args, **kwargs)

    monkeypatch.setattr(caps, "read_capability_record", _read)
    monkeypatch.setattr(install, "_install_area", _copy_area)
    monkeypatch.setattr(caps, "_copy_capability_tree", _copy_capability)

    sync.run_sync(installed_target)

    assert {"read audit", "read evidence"} <= set(events)
    assert events.count("copy capability") == 2
    first_copy = events.index("copy")
    assert all(event.startswith("copy") for event in events[first_copy:]), events


def test_sync_reads_the_installed_package_when_no_manifest_records_a_version(
    installed_target: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """With no manifest, the version falls back to the installed package.yaml, read
    before the copy replaces it. At the bundled version, sync copies the capability,
    runs no migration and writes no manifest."""
    from project_kit import capabilities as caps

    install_source = tmp_path / "install-source" / ".pkit"
    install_source.mkdir(parents=True)
    _stage_capability_in_source(install_source, "evidence", version="0.1.0")
    source = caps.find_capability_in_source(install_source, "evidence")
    assert source is not None
    caps.install_capability(installed_target, source)
    _record(installed_target, "evidence").unlink()

    sync_source = tmp_path / "sync-source" / ".pkit"
    sync_source.mkdir(parents=True)
    cap_dir = _stage_capability_in_source(
        sync_source, "evidence", version="0.1.0", skill_body="# From sync source\n"
    )
    script = cap_dir / "migrations" / "0.1.0" / "001-mark.sh"
    script.parent.mkdir(parents=True)
    script.write_text('#!/usr/bin/env bash\nset -euo pipefail\ntouch "$ROOT/migrated"\n')
    monkeypatch.setattr(install, "find_source_kit", lambda: sync_source)
    monkeypatch.setattr(sync.install, "find_source_kit", lambda: sync_source)

    sync.run_sync(installed_target)

    skills = installed_target / ".pkit" / "capabilities" / "evidence" / "skills"
    assert "From sync source" in (skills / "evidence-skill.md").read_text(encoding="utf-8")
    assert not (installed_target / "migrated").exists()
    assert not _record(installed_target, "evidence").exists()


def test_sync_skips_a_capability_with_no_recorded_version(
    installed_target: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Neither a manifest nor a readable package.yaml names a version: sync skips the
    capability, reports it, and runs none of its migrations (Found on the way 14)."""
    from project_kit import capabilities as caps

    install_source = tmp_path / "install-source" / ".pkit"
    install_source.mkdir(parents=True)
    _stage_capability_in_source(install_source, "evidence", version="0.1.0")
    source = caps.find_capability_in_source(install_source, "evidence")
    assert source is not None
    caps.install_capability(installed_target, source)
    _record(installed_target, "evidence").unlink()
    installed = installed_target / ".pkit" / "capabilities" / "evidence"
    (installed / "package.yaml").write_text("not: a package\n", encoding="utf-8")

    sync_source = tmp_path / "sync-source" / ".pkit"
    sync_source.mkdir(parents=True)
    cap_dir = _stage_capability_in_source(sync_source, "evidence", version="0.1.0")
    script = cap_dir / "migrations" / "0.1.0" / "001-mark.sh"
    script.parent.mkdir(parents=True)
    script.write_text('#!/usr/bin/env bash\nset -euo pipefail\ntouch "$ROOT/migrated"\n')
    monkeypatch.setattr(install, "find_source_kit", lambda: sync_source)
    monkeypatch.setattr(sync.install, "find_source_kit", lambda: sync_source)

    sync.run_sync(installed_target)
    out = capsys.readouterr().out

    assert "no recorded version" in out
    assert not (installed_target / "migrated").exists()
    assert (installed / "package.yaml").read_text(encoding="utf-8") == "not: a package\n"


def test_sync_skips_an_externally_sourced_capability_by_its_origin(
    installed_target: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """An externally-sourced registration is never read as shipped: neither refreshed
    from a bundled capability of its name nor reported orphaned (Found on the way 13)."""
    from project_kit import capabilities as caps
    from project_kit.manifest import ORIGIN_EXTERNALLY_SOURCED

    skill = _install_then_repoint_source(
        installed_target,
        monkeypatch,
        tmp_path,
        "evidence",
        installed_version="0.2.0",
        source_version="0.2.0",
    )
    before = skill.read_text(encoding="utf-8")
    caps.set_capability_origin(installed_target, "evidence", ORIGIN_EXTERNALLY_SOURCED)

    sync.run_sync(installed_target)
    out = capsys.readouterr().out

    assert "externally sourced" in out
    assert "orphan" not in out
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
# A release before this pkit's: the project's content, behind this pkit.
_OLDER = "1.0.0"


def _record_content_version(target: Path, version: str) -> None:
    """Record *version* as the project's `backbone_version`, as a newer pkit's sync did."""
    manifest = read_backbone_manifest(target)
    assert manifest is not None
    manifest.backbone_version = version
    write_backbone_manifest(target, manifest)


def _record_states(target: Path, backbone: str, completed: str | None) -> None:
    """Record the backbone's two states, *completed* None leaving no completion."""
    from project_kit.manifest import record_backbone_target, record_completed_version

    record_backbone_target(target, backbone)
    path = target / ".pkit" / "manifest.yaml"
    if completed is None:
        lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
        path.write_text(
            "".join(line for line in lines if not line.startswith("completed_version:")),
            encoding="utf-8",
        )
    else:
        record_completed_version(target, completed)


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


def _cli_sync(*args: str):
    from click.testing import CliRunner

    from project_kit.cli import main

    return CliRunner().invoke(main, ["sync", *args])


def _refusal(target: Path) -> str:
    """The guard's message for `pkit sync` in *target*, its lines joined."""
    with pytest.raises(click.ClickException) as excinfo:
        sync.run_sync(target)
    return " ".join(excinfo.value.message.split())


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
    pinning at the content, which needs no fetch, or `pkit upgrade`, which finishes
    the raise (ADR-065 point 8)."""
    _record_content_version(installed_target, _NEWER)
    _write_pin(installed_target, _INSTALLED_BACKBONE)

    message = _refusal(installed_target)

    assert f"run `pkit pin {_NEWER}`" in message
    assert "Or run `pkit upgrade`, which finishes the interrupted raise." in message
    assert router.read_version_pin(installed_target) == _INSTALLED_BACKBONE


def test_upgrade_older_direction_names_no_upgrade_for_content_ahead_of_its_pin(
    installed_target: Path,
) -> None:
    """Upgrade's own refusal, the older direction alone, does not name itself."""
    _record_content_version(installed_target, _NEWER)
    _write_pin(installed_target, _INSTALLED_BACKBONE)

    with pytest.raises(click.ClickException) as excinfo:
        sync.refuse_content_downgrade(
            installed_target, install.find_source_kit(), command="upgrade"
        )

    assert f"run `pkit pin {_NEWER}`" in excinfo.value.message
    assert "pkit upgrade`, which finishes" not in excinfo.value.message


@pytest.mark.parametrize("flags", [("--force",), ("--dry-run",)], ids=["force", "dry-run"])
def test_sync_content_downgrade_refusal_has_no_override(
    installed_target: Path, flags: tuple[str, ...]
) -> None:
    """`--force` overrides nothing, and a dry run refuses too."""
    _record_content_version(installed_target, _NEWER)
    before = _tree_bytes(installed_target)

    result = _cli_sync(*flags)

    assert result.exit_code != 0
    assert "no flag overrides this refusal" in " ".join(result.output.split())
    assert _tree_bytes(installed_target) == before


def test_cli_sync_exits_non_zero_on_the_content_downgrade_refusal(installed_target: Path) -> None:
    _record_content_version(installed_target, _NEWER)

    result = _cli_sync()

    assert result.exit_code != 0
    assert "refusing to run `pkit sync`" in result.output


def test_sync_at_the_content_version_proceeds(installed_target: Path) -> None:
    """This pkit at the project's content and pin, the last upgrade complete: sync runs."""
    _write_pin(installed_target, _INSTALLED_BACKBONE)

    sync.run_sync(installed_target)  # must not raise

    manifest = read_backbone_manifest(installed_target)
    assert manifest is not None
    assert manifest.backbone_version == _INSTALLED_BACKBONE
    assert manifest.completed_version == _INSTALLED_BACKBONE
    assert router.read_version_pin(installed_target) == _INSTALLED_BACKBONE


def test_sync_does_not_order_a_pin_that_is_not_a_version(installed_target: Path) -> None:
    """A pin that is not a version has no order to keep, so it stops nothing."""
    _write_pin(installed_target, "main")

    sync.run_sync(installed_target)  # must not raise


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


# --- sync's guard: another version, or an unfinished upgrade (ADR-065 points 7, 8) ---


@pytest.mark.parametrize("flags", [(), ("--dry-run",), ("--force",)], ids=["", "dry-run", "force"])
def test_sync_stops_under_a_newer_pkit_and_names_moving_staying_and_pipelines(
    installed_target: Path, flags: tuple[str, ...]
) -> None:
    """Unpinned, this pkit newer than the content: sync stops before anything is
    written, under a dry run and `--force` too. The message names moving with
    `pkit upgrade`, staying with `pkit pin`, and a pipeline's two ways."""
    _record_states(installed_target, _OLDER, _OLDER)
    before = _tree_bytes(installed_target)

    result = _cli_sync(*flags)

    assert result.exit_code != 0
    output = " ".join(result.output.split())
    assert (
        f"refusing to run `pkit sync`: this pkit is {_INSTALLED_BACKBONE}, newer than this "
        f"project's content, {_OLDER}"
    ) in output
    assert "the project pins no version" in output
    assert "Nothing was written, and no flag overrides this refusal." in output
    assert f"To move the project to {_INSTALLED_BACKBONE}: run `pkit upgrade`." in output
    assert "`--no-pin`" in output and "`--no-self-update`" in output
    assert f"To stay at {_OLDER}: run `pkit pin`." in output
    assert "In a pipeline: commit a pin" in output
    assert f"uv tool install --force {router.DISTRIBUTION_GIT_URL}@v{_OLDER}" in output
    assert "Syncing project-kit" not in output
    assert _tree_bytes(installed_target) == before


@pytest.mark.parametrize("completed", [None, _OLDER], ids=["no-completion", "behind"])
def test_sync_stops_over_an_incomplete_upgrade(
    installed_target: Path, completed: str | None
) -> None:
    """The last upgrade incomplete, this pkit at its target: sync stops and names
    `pkit upgrade`, and for a migration that fails every time, a fix or a rollback."""
    _record_states(installed_target, _INSTALLED_BACKBONE, completed)
    before = _tree_bytes(installed_target)

    message = _refusal(installed_target)

    if completed is None:
        assert "no completed upgrade is recorded for this project" in message
        assert "it runs every backbone migration up to its version once" in message
    else:
        assert "the last upgrade of this project is incomplete" in message
        assert f"running the backbone migrations from {completed}" in message
    assert "Run `pkit upgrade`" in message
    assert "`git checkout <ref> -- .pkit/`" in message
    assert _tree_bytes(installed_target) == before


@pytest.mark.parametrize("recorded", ["not-a-version", None], ids=["not-a-version", "absent"])
def test_sync_stops_with_no_manifest_or_a_recorded_version_that_is_no_version(
    installed_target: Path, recorded: str | None
) -> None:
    """No manifest, or a `backbone_version` that is no version: sync no longer writes
    one. It stops and names `pkit upgrade`, which writes it and replays."""
    if recorded is None:
        (installed_target / ".pkit" / "manifest.yaml").unlink()
    else:
        _record_content_version(installed_target, recorded)
    before = _tree_bytes(installed_target)

    message = _refusal(installed_target)

    if recorded is None:
        assert ".pkit/manifest.yaml is missing" in message
    else:
        assert "'not-a-version', which is no version" in message
    assert "Run `pkit upgrade`: it writes the manifest at its version" in message
    assert _tree_bytes(installed_target) == before


def test_sync_stops_when_the_content_is_behind_the_pin_the_pin_running(
    installed_target: Path,
) -> None:
    """Pinned, the content behind the pin, the pin's own code running: `pkit upgrade`
    brings the content up to the pin."""
    _record_states(installed_target, _OLDER, _OLDER)
    _write_pin(installed_target, _INSTALLED_BACKBONE)

    message = _refusal(installed_target)

    assert f"this project pins pkit {_INSTALLED_BACKBONE}, and its content is behind" in message
    assert "Run `pkit upgrade`: run under the pin, it brings the content up to the pin." in (
        message
    )


def test_sync_under_the_routers_fallback_names_reconnecting_not_a_bare_upgrade(
    installed_target: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Pinned, the router could not fetch the pin and ran this pkit: the message names
    reconnecting, the pin through uvx, an HTTPS install of the pin, and moving on
    purpose with `pkit unpin` first, never a bare `pkit upgrade`."""
    _record_states(installed_target, _OLDER, _OLDER)
    _write_pin(installed_target, _OLDER)
    monkeypatch.setenv(router._PIN_UNRESOLVED_ENV, _OLDER)
    monkeypatch.delenv(router._BYPASS_ENV, raising=False)

    message = _refusal(installed_target)

    assert f"This project pins pkit {_OLDER}, which the router could not fetch" in message
    assert "Reconnect and run `pkit sync` again" in message
    assert f"`uvx --from {router.DISTRIBUTION_GIT_URL}@v{_OLDER} project-kit sync`" in message
    assert f"`uv tool install --force {router.DISTRIBUTION_HTTPS_URL}@v{_OLDER}`" in message
    assert "`pkit unpin`, then `pkit upgrade`" in message
    assert "Run `pkit upgrade`" not in message


def test_sync_under_the_routers_fallback_runs_where_it_finds_no_mismatch(
    installed_target: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The fallback only chooses the message: with no mismatch, sync runs."""
    _write_pin(installed_target, _INSTALLED_BACKBONE)
    monkeypatch.setenv(router._PIN_UNRESOLVED_ENV, _INSTALLED_BACKBONE)
    monkeypatch.delenv(router._BYPASS_ENV, raising=False)

    sync.run_sync(installed_target)  # must not raise


def test_sync_under_a_deliberate_bypass_of_a_pin_names_running_the_pin(
    installed_target: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Pinned, this pkit newer than the content and not the pin, run on purpose
    (`PKIT_NO_ROUTE`, so no fallback even with the mark set): the message names
    running the pin, or moving with `pkit upgrade`."""
    _record_states(installed_target, _OLDER, _OLDER)
    _write_pin(installed_target, _OLDER)
    monkeypatch.setenv(router._PIN_UNRESOLVED_ENV, _OLDER)
    monkeypatch.setenv(router._BYPASS_ENV, "1")

    message = _refusal(installed_target)

    assert f"and the project pins {_OLDER}" in message
    assert "could not fetch" not in message
    assert f"`uvx --from {router.DISTRIBUTION_GIT_URL}@v{_OLDER} project-kit sync`" in message
    assert "To move the project on: run `pkit upgrade`." in message


def test_sync_under_a_pin_that_is_no_version_names_no_release_to_run(
    installed_target: Path,
) -> None:
    """A pin that is no version stops nothing by itself, and where the content is
    behind this pkit the message names pinning or moving, never `uvx …@v<pin>`."""
    _record_states(installed_target, _OLDER, _OLDER)
    _write_pin(installed_target, "main")

    message = _refusal(installed_target)

    assert "the project's pin, 'main', is no version" in message
    assert f"To stay at {_OLDER}: run `pkit pin`" in message
    assert "@vmain" not in message


def test_sync_refuses_a_pin_ahead_of_this_pkit_before_naming_upgrade(
    installed_target: Path,
) -> None:
    """A pin ahead of this pkit is #1212's refusal, whose remedy is the pinned pkit:
    `pkit upgrade` under this one would refuse too. So that row comes first, even
    over an incomplete upgrade."""
    _record_states(installed_target, _OLDER, None)
    _write_pin(installed_target, _NEWER)

    message = _refusal(installed_target)

    assert f"older than this project's pin ({_NEWER}, in .pkit/version-pin)" in message
    assert "Run `pkit upgrade`" not in message


def test_a_sync_that_proceeds_writes_no_manifest_and_runs_no_migration(
    installed_target: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """At the recorded version, sync writes neither the backbone's manifest nor a
    capability's, and runs no migration, a capability pending an upgrade included."""
    from project_kit import capabilities as caps
    from project_kit import migrations

    _install_then_repoint_source(
        installed_target,
        monkeypatch,
        tmp_path,
        "evidence",
        installed_version="0.1.0",
        source_version="0.2.0",
    )
    script = (
        tmp_path / "sync-source" / ".pkit" / "capabilities" / "evidence" / "migrations" / "0.2.0"
    ) / "001-mark.sh"
    script.parent.mkdir(parents=True)
    script.write_text('#!/usr/bin/env bash\nset -euo pipefail\ntouch "$ROOT/migrated"\n')
    ran: list[str] = []

    def _no_migration(*_args: object, **_kwargs: object) -> None:
        ran.append("migration")

    monkeypatch.setattr(migrations, "execute_migration_scripts", _no_migration)
    monkeypatch.setattr(caps, "execute_migration_scripts", _no_migration)
    backbone = installed_target / ".pkit" / "manifest.yaml"
    record = _record(installed_target, "evidence")
    before = (backbone.read_bytes(), record.read_bytes())

    sync.run_sync(installed_target)

    assert (backbone.read_bytes(), record.read_bytes()) == before
    assert ran == []
    assert not (installed_target / "migrated").exists()


def test_sync_is_never_refused_in_the_methodology_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """project-kit's own sync moves no version, so it runs as today even where its
    manifest records a version far behind and no completion. Its primitives are
    stubbed, as in the self-host test above, so nothing is written here."""
    from project_kit.manifest import BackboneManifest

    source_repo = install.find_source_kit().parent
    monkeypatch.chdir(source_repo)
    monkeypatch.setattr(
        sync, "read_backbone_manifest", lambda _root: BackboneManifest(backbone_version="0.1.0")
    )
    for primitive in (
        "run_installed_adapter_primitives",
        "_render_runtime_ignore",
        "ensure_agent_workspace",
        "provision_query_commands",
    ):
        monkeypatch.setattr(install, primitive, lambda _ctx: None)

    result = _cli_sync()

    assert result.exit_code == 0, result.output
    assert "Self-host sync complete" in result.output


def test_sync_command_refuses_an_incomplete_source_with_its_own_message(
    installed_target: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The guard reads the source's version only after the source is known to be
    whole, so an incomplete bundle is refused cleanly, as `run_sync` refuses it."""
    incomplete = tmp_path / "broken-source" / ".pkit"
    incomplete.mkdir(parents=True)  # no decisions/ subdir
    monkeypatch.setattr(install, "find_source_kit", lambda: incomplete)

    result = _cli_sync()

    assert result.exit_code != 0
    assert "methodology source not found" in result.output
