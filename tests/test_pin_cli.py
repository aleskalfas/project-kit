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

from project_kit import install, router
from project_kit.cli import main
from project_kit.sync import run_sync


def _git_repo(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    (tmp_path / ".pkit").mkdir()
    return tmp_path


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
