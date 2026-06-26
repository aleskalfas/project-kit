"""Tests for `pkit upgrade` (PR-J of the build roadmap)."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import click
import pytest

from project_kit import install, manifest, upgrade


@pytest.fixture
def installed_target(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A git repo with the kit installed; ready for upgrade."""
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    monkeypatch.chdir(tmp_path)

    def _noop(_script: Path, _ctx: install.InstallContext) -> None:
        return None

    monkeypatch.setattr(install, "_run_adapter_primitive", _noop)
    install.install_kit(tmp_path)
    return tmp_path


def test_upgrade_refuses_when_pkit_dir_missing(tmp_path: Path) -> None:
    with pytest.raises(click.ClickException, match=r"\.pkit/ does not exist"):
        upgrade.run_upgrade(tmp_path)


def test_upgrade_refuses_when_backbone_manifest_missing(tmp_path: Path) -> None:
    (tmp_path / ".pkit").mkdir()
    with pytest.raises(click.ClickException, match=r"manifest\.yaml is missing"):
        upgrade.run_upgrade(tmp_path)


def test_upgrade_self_host_delegates_to_sync(monkeypatch: pytest.MonkeyPatch) -> None:
    """On self-host (source == target), upgrade short-circuits to sync's deploy.

    There is no backbone to upgrade — the source IS the installed state — so
    upgrade delegates to sync (whose self-host branch re-runs the deploy
    primitives) and skips the version comparison + migration steps.
    """
    source_repo = install.find_source_kit().parent
    monkeypatch.chdir(source_repo)

    called = {"sync": 0}

    def _spy_sync(_target_root: Path, dry_run: bool = False) -> None:
        called["sync"] += 1

    monkeypatch.setattr(upgrade, "run_sync", _spy_sync)

    upgrade.run_upgrade(source_repo)  # must not raise

    assert called["sync"] == 1


def test_upgrade_reports_already_at_version_when_in_sync(
    installed_target: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Fresh install records the source kit's version; upgrade is a no-op."""
    upgrade.run_upgrade(installed_target)
    captured = capsys.readouterr()
    assert "Already at backbone v" in captured.out
    assert "nothing to upgrade" in captured.out


def _adapter_pkg(version: str, requires: str) -> str:
    return (
        "schema_version: 1\n"
        "component:\n"
        "  kind: adapter\n"
        "  name: claude-code\n"
        f"  version: {version}\n"
        f'requires_backbone: "{requires}"\n'
    )


def _fake_source(tmp_path: Path, *, version: str, adapter_requires: str | None) -> Path:
    """A minimal source `.pkit` with a VERSION and (optionally) a claude-code
    adapter package.yaml — enough for the compatibility step to read."""
    src = tmp_path / "fake-source" / ".pkit"
    src.mkdir(parents=True)
    (src / "VERSION").write_text(f"{version}\n", encoding="utf-8")
    # A `decisions/` subtree is the discriminator that marks this as a real
    # methodology source (per `find_source_kit` / the source-incomplete guard
    # added for ADR-033). Without it, `run_upgrade` refuses before reaching the
    # compatibility check this fixture exists to exercise.
    (src / "decisions").mkdir()
    if adapter_requires is not None:
        adir = src / "adapters" / "claude-code"
        adir.mkdir(parents=True)
        (adir / "package.yaml").write_text(_adapter_pkg("9.9.9", adapter_requires), encoding="utf-8")
    return src


def test_compat_ignores_stale_installed_ceiling(
    installed_target: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The fix: a stale *installed* requires_backbone that excludes the target must
    NOT block the upgrade — the check reads the *source* (post-upgrade) ceiling,
    which auto-broadens with the backbone. Reproduces the interaction-gateway
    deadlock (installed adapter `<old>`, source compatible)."""
    pkg = installed_target / ".pkit" / "adapters" / "claude-code" / "package.yaml"
    pkg.write_text(_adapter_pkg("0.1.0", ">=0.1.0,<0.5.0"), encoding="utf-8")  # stale, excludes source

    # Real source (find_source_kit unpatched) — its adapter ceiling includes the
    # current backbone. No compatibility error; installed==source ⇒ already-at.
    upgrade.run_upgrade(installed_target)
    out = capsys.readouterr().out
    assert "compatibility check failed" not in out
    assert "Already at backbone v" in out


def test_compat_refuses_when_source_component_incompatible(
    installed_target: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A genuine incompatibility — the *source* (new) adapter can't run on the
    target backbone — still refuses, before any state change."""
    src = _fake_source(tmp_path, version="2.0.0", adapter_requires=">=0.1.0,<1.5.0")
    monkeypatch.setattr(upgrade, "find_source_kit", lambda: src)
    with pytest.raises(click.ClickException, match="compatibility check failed"):
        upgrade.run_upgrade(installed_target)


def test_compat_falls_back_to_installed_when_source_lacks_component(
    installed_target: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """For a component the source no longer ships, the check falls back to the
    installed range (it won't be refreshed by sync, so its range still governs)."""
    src = _fake_source(tmp_path, version="2.0.0", adapter_requires=None)  # source dropped the adapter
    monkeypatch.setattr(upgrade, "find_source_kit", lambda: src)
    pkg = installed_target / ".pkit" / "adapters" / "claude-code" / "package.yaml"
    pkg.write_text(_adapter_pkg("0.1.0", ">=0.1.0,<1.5.0"), encoding="utf-8")  # installed excludes 2.0.0
    with pytest.raises(click.ClickException, match="compatibility check failed"):
        upgrade.run_upgrade(installed_target)


def test_upgrade_dry_run_writes_nothing(
    installed_target: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Dry-run prints the plan but doesn't touch the recorded manifest."""
    # Force recorded version backwards so upgrade has work to do.
    m = manifest.read_backbone_manifest(installed_target)
    assert m is not None
    m.backbone_version = "0.1.0"
    manifest.write_backbone_manifest(installed_target, m)

    upgrade.run_upgrade(installed_target, dry_run=True)

    post = manifest.read_backbone_manifest(installed_target)
    assert post is not None
    assert post.backbone_version == "0.1.0"  # unchanged


def test_upgrade_updates_recorded_version_when_run_for_real(
    installed_target: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A real upgrade run (no dry-run) advances the recorded version to match source."""
    m = manifest.read_backbone_manifest(installed_target)
    assert m is not None
    source_version = m.backbone_version  # captured before tampering
    m.backbone_version = "0.1.0"
    manifest.write_backbone_manifest(installed_target, m)

    upgrade.run_upgrade(installed_target)

    post = manifest.read_backbone_manifest(installed_target)
    assert post is not None
    assert post.backbone_version == source_version


# --- backbone + component migration execution (per COR-010) ----------


def _stage_backbone_migration(
    source_kit: Path, version: str, script_name: str, body: str
) -> Path:
    """Drop a backbone migration script at <source_kit>/migrations/backbone/<version>/<script>.

    Migrations are kit-shipped: they live in the *source* and reach the adopter
    via the sync step (ADR-033 §4 propagates the `migrations` area). Staging
    into the source — not the adopter tree — survives the upgrade's sync, which
    refreshes the adopter's `migrations/` from source. The caller passes a
    throwaway source copy via `_real_source_copy` so the real repo is untouched.
    """
    version_dir = source_kit / "migrations" / "backbone" / version
    version_dir.mkdir(parents=True, exist_ok=True)
    script = version_dir / script_name
    script.write_text(body, encoding="utf-8")
    script.chmod(0o755)
    return script


def _real_source_copy(tmp_path: Path) -> Path:
    """Copy the live `.pkit/` source tree into `tmp_path` for tests that mutate it.

    Backbone-migration tests stage extra migration version dirs into the
    source. Since the upgrade's sync now propagates `migrations/` from source
    into the adopter (ADR-033 §4), the staged scripts must live in the source
    to survive that sync — but the real repo source must never be mutated by a
    test. A throwaway copy gives a complete, syncable source (all areas present)
    that the test can freely stage into. Returns the copy's `.pkit/` path,
    suitable for monkeypatching `find_source_kit`.
    """
    real_source = install.find_source_kit()
    dest = tmp_path / "source-copy" / ".pkit"
    shutil.copytree(real_source, dest)
    return dest


def test_upgrade_runs_backbone_migrations_in_version_order(
    installed_target: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Backbone migration scripts run in semver-then-NNN order against the target root."""
    # Move recorded backbone backwards so upgrade has work to do.
    m = manifest.read_backbone_manifest(installed_target)
    assert m is not None
    m.backbone_version = "0.1.0"
    manifest.write_backbone_manifest(installed_target, m)

    source = _real_source_copy(tmp_path)
    # Patch on both modules: upgrade bound the name at import; sync resolves
    # its own source via `install.find_source_kit` during the upgrade's sync
    # step, which is what propagates the staged migrations into the adopter.
    monkeypatch.setattr(upgrade, "find_source_kit", lambda: source)
    monkeypatch.setattr(install, "find_source_kit", lambda: source)

    trace = installed_target / "backbone-migration-trace.txt"
    # Stage two migrations in two version dirs in the (copied) source; they
    # propagate to the adopter via the upgrade's sync step, then run. The real
    # source's VERSION is the upgrade target — both 0.2.0 and 0.3.0 fall inside
    # the (0.1.0, target] window.
    _stage_backbone_migration(
        source,
        "0.2.0",
        "001-first.sh",
        f'#!/usr/bin/env bash\necho "0.2.0/001" >> "{trace}"\n',
    )
    _stage_backbone_migration(
        source,
        "0.3.0",
        "001-second.sh",
        f'#!/usr/bin/env bash\necho "0.3.0/001" >> "{trace}"\n',
    )
    # A version far above target — should NOT run.
    _stage_backbone_migration(
        source,
        "99.0.0",
        "001-future.sh",
        f'#!/usr/bin/env bash\necho "99.0.0/001" >> "{trace}"\n',
    )

    upgrade.run_upgrade(installed_target)

    assert trace.is_file()
    lines = trace.read_text(encoding="utf-8").strip().splitlines()
    assert "0.2.0/001" in lines
    assert "0.3.0/001" in lines
    assert "99.0.0/001" not in lines
    # In order: 0.2.0 before 0.3.0.
    assert lines.index("0.2.0/001") < lines.index("0.3.0/001")


def test_upgrade_backbone_migrations_dry_run_does_not_execute(
    installed_target: Path,
) -> None:
    """Dry-run reports migrations but doesn't run them."""
    m = manifest.read_backbone_manifest(installed_target)
    assert m is not None
    m.backbone_version = "0.1.0"
    manifest.write_backbone_manifest(installed_target, m)

    trace = installed_target / "trace.txt"
    # Dry-run does not sync, so the discovery reads the adopter's own
    # migrations tree directly — stage there (no source copy needed).
    _stage_backbone_migration(
        installed_target / ".pkit",
        "0.2.0",
        "001-runme.sh",
        f'#!/usr/bin/env bash\necho "ran" >> "{trace}"\n',
    )

    upgrade.run_upgrade(installed_target, dry_run=True)
    assert not trace.exists()


def test_upgrade_backbone_migration_failure_halts_run(
    installed_target: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A non-zero exit halts the upgrade, surfaced as ClickException."""
    m = manifest.read_backbone_manifest(installed_target)
    assert m is not None
    m.backbone_version = "0.1.0"
    manifest.write_backbone_manifest(installed_target, m)

    source = _real_source_copy(tmp_path)
    # Patch on both modules: upgrade bound the name at import; sync resolves
    # its own source via `install.find_source_kit` during the upgrade's sync
    # step, which is what propagates the staged migrations into the adopter.
    monkeypatch.setattr(upgrade, "find_source_kit", lambda: source)
    monkeypatch.setattr(install, "find_source_kit", lambda: source)
    _stage_backbone_migration(
        source,
        "0.2.0",
        "001-fails.sh",
        '#!/usr/bin/env bash\necho "boom" >&2\nexit 1\n',
    )

    with pytest.raises(click.ClickException, match="exited with status 1"):
        upgrade.run_upgrade(installed_target)


def test_upgrade_skips_capability_migrations_in_component_runner(
    installed_target: Path,
) -> None:
    """Capabilities are handled by sync's refresh path — not double-run here.

    Stage a capability with a migration that would write a trace file if
    invoked. Register it in the backbone manifest. Run `pkit upgrade`.
    The trace must NOT contain entries from the component runner — only
    the sync's auto-upgrade should have run it (and even that only if
    the per-component manifest exists with an older version).
    """
    cap_dir = installed_target / ".pkit" / "capabilities" / "evidence-fake"
    (cap_dir / "skills").mkdir(parents=True)
    (cap_dir / "package.yaml").write_text(
        "schema_version: 1\ncomponent:\n  kind: capability\n  name: evidence-fake\n  version: 0.2.0\n"
        'requires_backbone: ">=0.1.0,<99.0.0"\n',
        encoding="utf-8",
    )

    backbone_manifest = manifest.read_backbone_manifest(installed_target)
    assert backbone_manifest is not None
    backbone_manifest.components.append(
        manifest.ComponentRegistryEntry(
            kind="capability",
            name="evidence-fake",
            manifest=".pkit/capabilities/evidence-fake/manifest.yaml",
        )
    )
    backbone_manifest.backbone_version = "0.1.0"
    manifest.write_backbone_manifest(installed_target, backbone_manifest)

    # Trace file the component-runner WOULD write to if it (wrongly)
    # walked capabilities — we want to confirm it does not.
    component_runner_trace = installed_target / "component-runner-trace.txt"
    (cap_dir / "migrations" / "0.2.0").mkdir(parents=True)
    (cap_dir / "migrations" / "0.2.0" / "001-cap.sh").write_text(
        f'#!/usr/bin/env bash\necho "ran-from-component-runner" >> "{component_runner_trace}"\n',
        encoding="utf-8",
    )
    (cap_dir / "migrations" / "0.2.0" / "001-cap.sh").chmod(0o755)

    # Even if execution races, the gate is: _run_component_migrations
    # filters entries to (bundle, adapter) only. The trace may exist
    # from sync's parallel run — but that's a different code path.
    # What we assert here is that AT MINIMUM, the component runner did
    # not invoke the script (verified by skipping the entry kind).
    from project_kit.upgrade import _run_component_migrations

    _run_component_migrations(installed_target, backbone_manifest.components, dry_run=False)
    # No file written by the component runner — it skipped the capability.
    assert not component_runner_trace.exists()


# ============================================================================
# COR-030: backbone-wide upgrade capability dependency check
# ============================================================================


def _stage_installed_capability(
    target_root: Path,
    name: str,
    *,
    version: str = "0.1.0",
    requires_backbone: str = ">=0.1.0,<99.0.0",
    requires_capabilities: list[dict[str, str]] | None = None,
) -> None:
    """Directly create a capability under .pkit/capabilities/<name>/ and register it.

    Bypasses source-kit lookup — used in upgrade tests where we only need
    the installed state, not the source. The package.yaml is written to the
    installed path so _resolve_compatibility can read it.
    """
    from project_kit import capabilities as caps
    from project_kit.manifest import ComponentRegistryEntry, read_backbone_manifest, write_backbone_manifest

    cap_dir = target_root / ".pkit" / "capabilities" / name
    cap_dir.mkdir(parents=True, exist_ok=True)

    req_caps_block = ""
    if requires_capabilities:
        lines = ["requires_capabilities:"]
        for req in requires_capabilities:
            lines.append(f'  - name: {req["name"]}')
            lines.append(f'    version: "{req["version"]}"')
        req_caps_block = "\n" + "\n".join(lines)

    (cap_dir / "package.yaml").write_text(
        f"""schema_version: 1
component:
  kind: capability
  name: {name}
  version: {version}
description: Test.
requires_backbone: "{requires_backbone}"{req_caps_block}
""",
        encoding="utf-8",
    )

    # Stamp a minimal per-component manifest so version reads work.
    import datetime as _dt
    (cap_dir / "manifest.yaml").write_text(
        f"""schema_version: 1
component:
  kind: capability
  name: {name}
  version: {version}
  installed_at: '{_dt.datetime.now(_dt.timezone.utc).isoformat()}'
requires_backbone: '{requires_backbone}'
backend_state: {{}}
""",
        encoding="utf-8",
    )

    # Register in backbone manifest.
    backbone = read_backbone_manifest(target_root)
    assert backbone is not None
    backbone.components = [
        c for c in backbone.components
        if not (c.kind == "capability" and c.name == name)
    ]
    backbone.components.append(ComponentRegistryEntry(
        kind="capability",
        name=name,
        manifest=f".pkit/capabilities/{name}/manifest.yaml",
    ))
    write_backbone_manifest(target_root, backbone)


def test_backbone_upgrade_refuses_when_installed_cap_has_absent_dep(
    installed_target: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Backbone upgrade refuses when an installed capability's declared dependency
    is not installed."""
    # Install consumer with a dep on evidence; evidence is NOT installed.
    _stage_installed_capability(
        installed_target, "consumer",
        requires_capabilities=[{"name": "evidence", "version": ">=0.1.0,<2.0.0"}],
    )

    with pytest.raises(click.ClickException, match="capability dependency check failed"):
        upgrade.run_upgrade(installed_target)


def test_backbone_upgrade_refuses_when_installed_cap_dep_out_of_range(
    installed_target: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Backbone upgrade refuses when a declared dependency is installed but out of range."""
    _stage_installed_capability(installed_target, "evidence", version="0.1.0")
    _stage_installed_capability(
        installed_target, "consumer",
        requires_capabilities=[{"name": "evidence", "version": ">=0.2.0,<2.0.0"}],
    )

    with pytest.raises(click.ClickException, match="capability dependency check failed"):
        upgrade.run_upgrade(installed_target)


def test_backbone_upgrade_succeeds_when_cap_deps_satisfied(
    installed_target: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Backbone upgrade proceeds when all capability dependency requirements are satisfied."""
    _stage_installed_capability(installed_target, "evidence", version="0.3.0")
    _stage_installed_capability(
        installed_target, "consumer",
        requires_capabilities=[{"name": "evidence", "version": ">=0.2.0,<1.0.0"}],
    )

    # Already at current version → should report "Already at backbone".
    upgrade.run_upgrade(installed_target)
    captured = capsys.readouterr()
    assert "Already at backbone v" in captured.out


def test_backbone_upgrade_no_cap_deps_unaffected(
    installed_target: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A capability with no requires_capabilities is unaffected by the new check."""
    _stage_installed_capability(installed_target, "standalone")

    upgrade.run_upgrade(installed_target)
    captured = capsys.readouterr()
    assert "Already at backbone v" in captured.out


def test_upgrade_refuses_cleanly_when_source_incomplete(
    installed_target: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An incomplete resolved source yields a clean ClickException before read_kit_version.

    Mirrors sync's guard (ADR-033 / issue #333): upgrade must refuse on a source
    that lacks the `decisions/` discriminator rather than crashing inside
    `read_kit_version`. The stand-in source lives off the adopter root so the
    self-host branch is not taken; the fixture already wrote the backbone
    manifest, so the missing-manifest guard is not what trips.
    """
    incomplete = tmp_path / "broken-source" / ".pkit"
    incomplete.mkdir(parents=True)  # no decisions/ subdir
    monkeypatch.setattr(upgrade, "find_source_kit", lambda: incomplete)

    with pytest.raises(click.ClickException, match="methodology source not found"):
        upgrade.run_upgrade(installed_target)
