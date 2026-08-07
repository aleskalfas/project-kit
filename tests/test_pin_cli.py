"""Tests for `pkit pin` / `pkit unpin` (ADR-045).

The two operator gestures that manage a project's `.pkit/version-pin` directive:
`pin` writes it (freeze at the current version by default, or at a given token),
`unpin` removes it. The router reads the file elsewhere; these tests cover only
the write/remove gestures and the sync-exclusion invariant that neither `init`
nor `sync` ever touches the directive.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from click.testing import CliRunner

from project_kit import install, router, upgrade
from project_kit.cli import main
from project_kit.sync import run_sync


def _git_repo(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    (tmp_path / ".pkit").mkdir()
    return tmp_path


def _write_manifest(tmp_path: Path, backbone_version: str) -> None:
    """Seed a minimal `.pkit/manifest.yaml` so `pin <version>` can read the
    current content version it compares the target against (ADR-045)."""
    (tmp_path / ".pkit" / "manifest.yaml").write_text(
        f"schema_version: 1\nbackbone_version: {backbone_version}\ncomponents: []\n",
        encoding="utf-8",
    )


def test_pin_no_arg_freezes_at_running_version(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _git_repo(tmp_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(router, "running_version", lambda: "1.140.0")

    result = CliRunner().invoke(main, ["pin"])

    assert result.exit_code == 0
    assert router.read_version_pin(tmp_path) == "1.140.0"
    assert "1.140.0" in result.output


def test_pin_with_token_writes_that_token(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _git_repo(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(main, ["pin", "1.99.0"])

    assert result.exit_code == 0
    assert router.read_version_pin(tmp_path) == "1.99.0"


def test_pin_creates_pkit_dir_if_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)  # no .pkit/ yet
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(main, ["pin", "1.99.0"])

    assert result.exit_code == 0
    assert router.pin_file_path(tmp_path).is_file()
    assert router.read_version_pin(tmp_path) == "1.99.0"


def test_pin_overwrites_an_existing_pin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _git_repo(tmp_path)
    monkeypatch.chdir(tmp_path)
    router.pin_file_path(tmp_path).write_text("1.0.0\n", encoding="utf-8")

    result = CliRunner().invoke(main, ["pin", "2.0.0"])

    assert result.exit_code == 0
    assert router.read_version_pin(tmp_path) == "2.0.0"


def test_unpin_removes_the_pin(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _git_repo(tmp_path)
    monkeypatch.chdir(tmp_path)
    router.pin_file_path(tmp_path).write_text("1.99.0\n", encoding="utf-8")

    result = CliRunner().invoke(main, ["unpin"])

    assert result.exit_code == 0
    assert not router.pin_file_path(tmp_path).exists()


def test_unpin_is_idempotent_when_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _git_repo(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(main, ["unpin"])

    assert result.exit_code == 0  # no error when there is nothing to remove
    assert not router.pin_file_path(tmp_path).exists()


# --- `pin <version>` reconcile + downgrade guard (ADR-045) ----------------------


def test_pin_equal_version_freezes_without_content_sync(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Target == current content version → freeze in place, no content reconcile."""
    _git_repo(tmp_path)
    _write_manifest(tmp_path, "1.5.0")
    monkeypatch.chdir(tmp_path)

    def _boom(*_a: object, **_k: object) -> int:
        raise AssertionError("equal pin must not reconcile content")

    monkeypatch.setattr(upgrade, "run_bypassed", _boom)

    result = CliRunner().invoke(main, ["pin", "1.5.0"])

    assert result.exit_code == 0
    assert router.read_version_pin(tmp_path) == "1.5.0"
    assert "Pinned project-kit to 1.5.0" in result.output


def test_pin_newer_version_reconciles_forward_then_flips_pin_last(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Target > current → reconcile content forward under the target's own code,
    then flip the pin LAST: the pin is not yet advanced while the reconcile runs."""
    _git_repo(tmp_path)
    _write_manifest(tmp_path, "1.0.0")
    monkeypatch.chdir(tmp_path)

    seen: dict[str, object] = {}

    def _fake_bypassed(pin: str, argv: list[str], environ: object = None) -> int:
        # The pin must NOT yet be advanced when the forward reconcile runs.
        seen["pin_during_reconcile"] = router.read_version_pin(tmp_path)
        seen["target"] = pin
        seen["argv"] = argv
        return 0

    monkeypatch.setattr(upgrade, "run_bypassed", _fake_bypassed)

    result = CliRunner().invoke(main, ["pin", "2.0.0"])

    assert result.exit_code == 0
    assert seen["target"] == "2.0.0"
    assert seen["argv"] == ["upgrade"]
    assert seen["pin_during_reconcile"] is None  # flipped only after reconcile
    assert router.read_version_pin(tmp_path) == "2.0.0"  # flipped last


def test_pin_newer_version_aborts_without_advancing_pin_on_reconcile_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A non-zero reconcile exit leaves the pin unmoved — the pin never advances
    past content that failed to land (ADR-045)."""
    _git_repo(tmp_path)
    _write_manifest(tmp_path, "1.0.0")
    router.pin_file_path(tmp_path).write_text("1.0.0\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(upgrade, "run_bypassed", lambda *_a, **_k: 3)

    result = CliRunner().invoke(main, ["pin", "2.0.0"])

    assert result.exit_code != 0
    assert router.read_version_pin(tmp_path) == "1.0.0"  # unmoved


def test_pin_older_version_is_refused_and_writes_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Target < current → hard refuse: exit non-zero, write no pin, touch no
    content (migrations are forward-only, COR-010)."""
    _git_repo(tmp_path)
    _write_manifest(tmp_path, "2.0.0")
    monkeypatch.chdir(tmp_path)

    def _boom(*_a: object, **_k: object) -> int:
        raise AssertionError("a downgrade must never reconcile content")

    monkeypatch.setattr(upgrade, "run_bypassed", _boom)

    result = CliRunner().invoke(main, ["pin", "1.0.0"])

    assert result.exit_code != 0
    assert not router.pin_file_path(tmp_path).exists()  # nothing written
    # The manifest (content version) is untouched.
    manifest_text = (tmp_path / ".pkit" / "manifest.yaml").read_text(encoding="utf-8")
    assert "backbone_version: 2.0.0" in manifest_text
    assert "forward-only" in result.output
    assert "git checkout" in result.output


def test_pin_branch_token_skips_guard_and_pins_in_place(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A non-semver token (a PRJ-004 branch/sha) can't be ordered → the guard is
    skipped, the pin is written in place, and the comparison never crashes."""
    _git_repo(tmp_path)
    _write_manifest(tmp_path, "1.0.0")
    monkeypatch.chdir(tmp_path)

    def _boom(*_a: object, **_k: object) -> int:
        raise AssertionError("a non-orderable pin must not reconcile content")

    monkeypatch.setattr(upgrade, "run_bypassed", _boom)

    result = CliRunner().invoke(main, ["pin", "feature-branch"])

    assert result.exit_code == 0
    assert router.read_version_pin(tmp_path) == "feature-branch"
    assert "not a comparable version" in result.output


# --- Sync-exclusion invariant (ADR-045): init / sync never touch the pin --------


def _install(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Install the kit into a fresh repo, stubbing adapter primitives (no harness)."""
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    monkeypatch.chdir(tmp_path)

    def _noop(_script: Path, _ctx: install.InstallContext) -> None:
        return None

    monkeypatch.setattr(install, "_run_adapter_primitive", _noop)
    install.install_kit(tmp_path)


def test_init_does_not_create_a_version_pin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`pkit init` propagates only the kit-owned areas; the project-owned pin
    directive is never seeded (ADR-045 — it is created only by `pkit pin`)."""
    _install(tmp_path, monkeypatch)
    assert not router.pin_file_path(tmp_path).exists()


def test_sync_preserves_an_existing_version_pin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`pkit sync` never writes or clobbers `.pkit/version-pin` — it is
    project-owned, outside the propagated areas, and survives a content refresh."""
    _install(tmp_path, monkeypatch)
    router.pin_file_path(tmp_path).write_text("1.99.0\n", encoding="utf-8")

    run_sync(tmp_path)

    assert router.read_version_pin(tmp_path) == "1.99.0"
