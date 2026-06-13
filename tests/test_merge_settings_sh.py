"""Tests for the claude-code adapter's `merge-settings.sh` script.

Direct shell-script tests — earlier tests in `test_merge.py` mock the
primitive invocation; these exercise the script's actual jq behaviour.

Adds coverage for the top-level-key preservation broadening landed in
#190: keys outside `permissions` (`agent`, `model`, custom config blocks)
must flow through with last-write-wins precedence across the source
chain.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
ADAPTER_SCRIPT = REPO_ROOT / ".pkit" / "adapters" / "claude-code" / "merge-settings.sh"


@pytest.fixture
def adapter_tree(tmp_path: Path) -> Path:
    """A tmp tree mirroring the kit-installed claude-code adapter layout.

    The script resolves `ROOT` from its own location (three dirs up), so
    placing the script + settings dirs under `tmp_path/.pkit/adapters/...`
    gives the same `ROOT` resolution it'd get in a real adopter tree.
    """
    adapter_dir = tmp_path / ".pkit" / "adapters" / "claude-code"
    (adapter_dir / "settings" / "core").mkdir(parents=True)
    (adapter_dir / "settings" / "project").mkdir(parents=True)
    # Skill source trees the script walks must exist (empty is fine).
    (tmp_path / ".pkit" / "skills" / "core").mkdir(parents=True)
    (tmp_path / ".pkit" / "skills" / "project").mkdir(parents=True)
    (tmp_path / ".pkit" / "capabilities").mkdir(parents=True)
    shutil.copy(ADAPTER_SCRIPT, adapter_dir / "merge-settings.sh")
    return tmp_path


def _write_settings(adapter_tree: Path, layer: str, payload: dict) -> None:
    path = (
        adapter_tree
        / ".pkit"
        / "adapters"
        / "claude-code"
        / "settings"
        / layer
        / "settings.json"
    )
    path.write_text(json.dumps(payload), encoding="utf-8")


def _run_merge(adapter_tree: Path, env: dict | None = None) -> subprocess.CompletedProcess:
    run_env = None
    if env is not None:
        import os

        run_env = {**os.environ, **env}
    return subprocess.run(
        ["bash", str(adapter_tree / ".pkit" / "adapters" / "claude-code" / "merge-settings.sh")],
        capture_output=True,
        text=True,
        check=False,
        env=run_env,
    )


def _read_target(adapter_tree: Path) -> dict:
    return json.loads(
        (adapter_tree / ".claude" / "settings.json").read_text(encoding="utf-8")
    )


def test_top_level_agent_key_preserved_from_core(adapter_tree: Path) -> None:
    """A source file's top-level `agent` key flows through to `.claude/settings.json`."""
    _write_settings(adapter_tree, "core", {
        "permissions": {"allow": ["Bash(ls)"], "deny": []},
        "agent": "project-manager",
    })

    result = _run_merge(adapter_tree)

    assert result.returncode == 0, result.stderr
    merged = _read_target(adapter_tree)
    assert merged["agent"] == "project-manager"


def test_project_layer_overrides_core_for_scalar_top_level_key(adapter_tree: Path) -> None:
    """Last-write-wins: `project/` source overrides `core/` source for top-level scalars."""
    _write_settings(adapter_tree, "core", {
        "permissions": {"allow": [], "deny": []},
        "agent": "core-default",
        "model": "sonnet",
    })
    _write_settings(adapter_tree, "project", {
        "permissions": {"allow": [], "deny": []},
        "agent": "project-override",
    })

    result = _run_merge(adapter_tree)

    assert result.returncode == 0, result.stderr
    merged = _read_target(adapter_tree)
    # project's override won.
    assert merged["agent"] == "project-override"
    # core's `model` survived (project didn't set it).
    assert merged["model"] == "sonnet"


def test_permissions_union_behaviour_unchanged(adapter_tree: Path) -> None:
    """The existing permissions union-deduped semantics still apply."""
    _write_settings(adapter_tree, "core", {
        "permissions": {"allow": ["Bash(ls)", "Bash(grep)"], "deny": ["Bash(rm)"]},
    })
    _write_settings(adapter_tree, "project", {
        "permissions": {"allow": ["Bash(pwd)", "Bash(ls)"], "deny": []},
    })

    result = _run_merge(adapter_tree)

    assert result.returncode == 0, result.stderr
    merged = _read_target(adapter_tree)
    assert sorted(merged["permissions"]["allow"]) == ["Bash(grep)", "Bash(ls)", "Bash(pwd)"]
    assert merged["permissions"]["deny"] == ["Bash(rm)"]


def test_idempotent_re_run_reports_exists(adapter_tree: Path) -> None:
    """A second run on an unchanged target reports `exists` and does not rewrite."""
    _write_settings(adapter_tree, "core", {
        "permissions": {"allow": ["Bash(ls)"], "deny": []},
        "agent": "project-manager",
    })

    first = _run_merge(adapter_tree)
    assert first.returncode == 0, first.stderr

    target = adapter_tree / ".claude" / "settings.json"
    mtime_before = target.stat().st_mtime_ns

    second = _run_merge(adapter_tree)
    assert second.returncode == 0, second.stderr
    assert "exists" in second.stdout, f"expected 'exists' in stdout, got: {second.stdout!r}"
    assert target.stat().st_mtime_ns == mtime_before, "target was rewritten on idempotent re-run"


def test_no_top_level_keys_outside_permissions_yields_permissions_only(adapter_tree: Path) -> None:
    """When sources only carry `permissions`, the merged file is permissions-only.

    Regression guard: the broadening must not introduce phantom top-level
    keys when no source provides any.
    """
    _write_settings(adapter_tree, "core", {
        "permissions": {"allow": ["Bash(ls)"], "deny": ["Bash(rm)"]},
    })
    _write_settings(adapter_tree, "project", {
        "permissions": {"allow": ["Bash(pwd)"], "deny": []},
    })

    result = _run_merge(adapter_tree)

    assert result.returncode == 0, result.stderr
    merged = _read_target(adapter_tree)
    assert set(merged.keys()) == {"permissions"}, merged


# --- capability-contributed adapter overlays (DEC-030) -------------------


def _install_capability(
    adapter_tree: Path,
    name: str,
    overlay: dict | None = None,
    *,
    register_in_manifest: bool = True,
) -> Path:
    """Set up an installed capability and (optionally) its active overlay.

    Writes a minimal manifest at .pkit/manifest.yaml that the walker reads,
    drops an overlay file under the capability's project/adapter-overlays/
    when `overlay` is provided. Returns the capability's directory.
    """
    cap_dir = adapter_tree / ".pkit" / "capabilities" / name
    cap_dir.mkdir(parents=True, exist_ok=True)
    if overlay is not None:
        overlay_dir = cap_dir / "project" / "adapter-overlays"
        overlay_dir.mkdir(parents=True, exist_ok=True)
        (overlay_dir / "claude-code.json").write_text(
            json.dumps(overlay), encoding="utf-8"
        )

    if register_in_manifest:
        manifest_path = adapter_tree / ".pkit" / "manifest.yaml"
        existing = manifest_path.read_text(encoding="utf-8") if manifest_path.is_file() else (
            "schema_version: 1\nbackbone_version: 1.0.0\ncomponents:\n"
        )
        addition = f"  - kind: capability\n    name: {name}\n    manifest: ignored\n"
        manifest_path.write_text(existing + addition, encoding="utf-8")
    return cap_dir


def test_capability_overlay_with_active_file_lands_top_level_key(adapter_tree: Path) -> None:
    """An overlay file at <cap>/project/adapter-overlays/claude-code.json flows through."""
    _write_settings(adapter_tree, "core", {"permissions": {"allow": [], "deny": []}})
    _install_capability(adapter_tree, "project-management", overlay={"agent": "project-manager"})

    result = _run_merge(adapter_tree)

    assert result.returncode == 0, result.stderr
    merged = _read_target(adapter_tree)
    assert merged.get("agent") == "project-manager"


def test_capability_overlay_absent_means_inactive(adapter_tree: Path) -> None:
    """A capability registered in the manifest but with no overlay file contributes nothing."""
    _write_settings(adapter_tree, "core", {"permissions": {"allow": [], "deny": []}})
    _install_capability(adapter_tree, "project-management", overlay=None)

    result = _run_merge(adapter_tree)

    assert result.returncode == 0, result.stderr
    merged = _read_target(adapter_tree)
    assert "agent" not in merged


def test_orphan_capability_directory_does_not_contribute(adapter_tree: Path) -> None:
    """A capability directory present on disk but absent from the manifest is ignored.

    Per DEC-030: the walker is manifest-scoped (not directory-presence-scoped)
    to prevent botched-uninstall / stash / rebase states from silently
    activating contributions.
    """
    _write_settings(adapter_tree, "core", {"permissions": {"allow": [], "deny": []}})
    # Drop overlay file but DO NOT register the capability in the manifest.
    _install_capability(
        adapter_tree,
        "ghost-capability",
        overlay={"agent": "ghost-agent"},
        register_in_manifest=False,
    )

    result = _run_merge(adapter_tree)

    assert result.returncode == 0, result.stderr
    merged = _read_target(adapter_tree)
    assert "agent" not in merged, (
        "orphan capability directory contributed despite not being in manifest"
    )


def test_capability_overlay_permissions_key_is_stripped(adapter_tree: Path) -> None:
    """A `permissions` key inside an overlay is silently overridden by step-1 layering.

    Per DEC-030's reserved-key rule: overlays cannot influence permissions.
    The existing two-layer merge's `del(.permissions)` on every source
    enforces this mechanically.
    """
    _write_settings(adapter_tree, "core", {
        "permissions": {"allow": ["Bash(ls)"], "deny": []},
    })
    _install_capability(adapter_tree, "project-management", overlay={
        "agent": "project-manager",
        "permissions": {"allow": ["Bash(rm -rf)"]},  # would be a footgun if honoured
    })

    result = _run_merge(adapter_tree)

    assert result.returncode == 0, result.stderr
    merged = _read_target(adapter_tree)
    assert merged.get("agent") == "project-manager"
    assert "Bash(rm -rf)" not in merged["permissions"]["allow"], (
        "overlay's permissions key leaked into merged permissions"
    )


def test_capability_overlay_overrides_project_settings(adapter_tree: Path) -> None:
    """Overlay sources sit between project/settings.json and target in the merge chain.

    Project's value loses to overlay's; this is the documented precedence per DEC-030.
    """
    _write_settings(adapter_tree, "core", {
        "permissions": {"allow": [], "deny": []},
        "agent": "core-default",
    })
    _write_settings(adapter_tree, "project", {
        "permissions": {"allow": [], "deny": []},
        "agent": "project-default",
    })
    _install_capability(adapter_tree, "project-management", overlay={"agent": "overlay-default"})

    result = _run_merge(adapter_tree)

    assert result.returncode == 0, result.stderr
    merged = _read_target(adapter_tree)
    assert merged.get("agent") == "overlay-default"


# --- authoritative-region tier (COR-002 §80-84 / ADR-002 / #251) -----------

def _set_target(adapter_tree: Path, payload: dict) -> None:
    """Seed the live .claude/settings.json the merge reads back as a source."""
    target = adapter_tree / ".claude" / "settings.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload), encoding="utf-8")


def _set_mode(adapter_tree: Path, mode: str) -> None:
    cfg = adapter_tree / ".pkit" / "permissions" / "project" / "config.yaml"
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text(f"schema_version: 1\nownership_mode: {mode}\nposture: lenient\n", encoding="utf-8")


def _region_file(adapter_tree: Path, region: dict) -> dict:
    path = adapter_tree / "region.json"
    path.write_text(json.dumps(region), encoding="utf-8")
    return {"PKIT_MANAGED_REGION_FILE": str(path)}


def test_managed_region_replaces_permissions_wholesale(adapter_tree: Path) -> None:
    """Managed mode regenerates `permissions` from the supplied region, discarding
    the adopter's prior permissions (no union) — drift heals."""
    _write_settings(adapter_tree, "core", {"permissions": {"allow": ["Bash(git:*)"], "deny": ["Bash(sudo:*)"]}})
    _set_target(adapter_tree, {"permissions": {"allow": ["Bash(rm:*)"], "deny": []}})
    _set_mode(adapter_tree, "managed")
    env = _region_file(adapter_tree, {"allow": ["Bash(gh:*)"], "deny": ["Bash(sudo:*)"]})

    result = _run_merge(adapter_tree, env=env)

    assert result.returncode == 0, result.stderr
    perms = _read_target(adapter_tree)["permissions"]
    assert perms == {"allow": ["Bash(gh:*)"], "deny": ["Bash(sudo:*)"]}, (
        "managed region must replace wholesale — neither core's union nor the "
        "target's prior allow may survive"
    )


def test_managed_preserves_content_outside_the_region(adapter_tree: Path) -> None:
    """Everything outside `.permissions` is left byte-for-byte (adopter-owned)."""
    _write_settings(adapter_tree, "core", {"permissions": {"allow": [], "deny": []}})
    _set_target(adapter_tree, {
        "permissions": {"allow": ["Bash(rm:*)"], "deny": []},
        "agent": "project-manager",
        "customBlock": {"nested": [1, 2, 3]},
    })
    _set_mode(adapter_tree, "managed")
    env = _region_file(adapter_tree, {"allow": [], "deny": ["Bash(sudo:*)"]})

    result = _run_merge(adapter_tree, env=env)

    assert result.returncode == 0, result.stderr
    merged = _read_target(adapter_tree)
    assert merged["agent"] == "project-manager"
    assert merged["customBlock"] == {"nested": [1, 2, 3]}


def test_managed_round_trip_add_set_equals_remove_set(adapter_tree: Path) -> None:
    """The symmetry from #251's filed criterion: apply A, then apply B with a grant
    dropped — the dropped grant vanishes (no strip-logic, no markers)."""
    _write_settings(adapter_tree, "core", {"permissions": {"allow": [], "deny": []}})
    _set_mode(adapter_tree, "managed")

    env_a = _region_file(adapter_tree, {"allow": ["Bash(a:*)", "Bash(b:*)"], "deny": []})
    assert _run_merge(adapter_tree, env=env_a).returncode == 0
    assert _read_target(adapter_tree)["permissions"]["allow"] == ["Bash(a:*)", "Bash(b:*)"]

    env_b = _region_file(adapter_tree, {"allow": ["Bash(a:*)"], "deny": []})
    assert _run_merge(adapter_tree, env=env_b).returncode == 0
    assert _read_target(adapter_tree)["permissions"]["allow"] == ["Bash(a:*)"], (
        "dropping b from the projection must remove it — no leftover, no marker"
    )

    env_empty = _region_file(adapter_tree, {"allow": [], "deny": []})
    assert _run_merge(adapter_tree, env=env_empty).returncode == 0
    assert _read_target(adapter_tree)["permissions"] == {"allow": [], "deny": []}, (
        "heals to empty — the region is exactly the current projection"
    )


def test_additive_mode_ignores_region_file(adapter_tree: Path) -> None:
    """The gate is `ownership_mode: managed`, not file-presence — a region file
    under additive mode (e.g. orphaned) must not reactivate wholesale replace."""
    _write_settings(adapter_tree, "core", {"permissions": {"allow": ["Bash(git:*)"], "deny": []}})
    _set_target(adapter_tree, {"permissions": {"allow": ["Bash(rm:*)"], "deny": []}})
    _set_mode(adapter_tree, "additive")
    env = _region_file(adapter_tree, {"allow": ["ONLY-IF-MANAGED"], "deny": []})

    result = _run_merge(adapter_tree, env=env)

    assert result.returncode == 0, result.stderr
    allow = _read_target(adapter_tree)["permissions"]["allow"]
    assert "ONLY-IF-MANAGED" not in allow, "region applied despite additive mode"
    # Additive union preserved (core + adopter's own).
    assert "Bash(git:*)" in allow and "Bash(rm:*)" in allow


def test_managed_mode_without_region_falls_back_to_additive(adapter_tree: Path) -> None:
    """Managed mode but no region supplied (e.g. plain sync, no apply) leaves the
    additive default untouched — managed replace only fires when the realizer
    hands over a projection."""
    _write_settings(adapter_tree, "core", {"permissions": {"allow": ["Bash(git:*)"], "deny": []}})
    _set_target(adapter_tree, {"permissions": {"allow": ["Bash(rm:*)"], "deny": []}})
    _set_mode(adapter_tree, "managed")

    result = _run_merge(adapter_tree)  # no PKIT_MANAGED_REGION_FILE

    assert result.returncode == 0, result.stderr
    allow = _read_target(adapter_tree)["permissions"]["allow"]
    assert "Bash(git:*)" in allow and "Bash(rm:*)" in allow
