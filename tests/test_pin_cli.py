"""Tests for `pkit pin` / `pkit unpin` (ADR-049).

The two operator gestures that manage a project's `.pkit/version-pin` directive:
`pin` writes it (freeze at the current content version by default, or reconcile
to a given version), `unpin` removes it. The pin token is a version number only
(a single leading `v` stripped) — branch / sha / pre-release forms are refused.
The router reads the file elsewhere; these tests cover only the write/remove
gestures and the sync-exclusion invariant that neither `init` nor `sync` ever
touches the directive.
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
    current content version it compares the target against (ADR-049)."""
    (tmp_path / ".pkit" / "manifest.yaml").write_text(
        f"schema_version: 1\nbackbone_version: {backbone_version}\ncomponents: []\n",
        encoding="utf-8",
    )


def test_pin_no_arg_freezes_at_content_version_not_running_version(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No-arg `pin` freezes at the CONTENT version (`backbone_version`), not the
    running binary — even when the installed tool is ahead of synced content."""
    _git_repo(tmp_path)
    _write_manifest(tmp_path, "1.5.0")
    monkeypatch.chdir(tmp_path)
    # Installed tool is ahead of the project's synced content; freeze at content.
    monkeypatch.setattr(router, "running_version", lambda: "9.9.9")

    result = CliRunner().invoke(main, ["pin"])

    assert result.exit_code == 0
    assert router.read_version_pin(tmp_path) == "1.5.0"
    assert "1.5.0" in result.output


def test_pin_no_arg_refuses_when_manifest_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No-arg `pin` has no recorded content version to freeze at → hard refuse."""
    _git_repo(tmp_path)  # .pkit/ exists but no manifest.yaml
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(main, ["pin"])

    assert result.exit_code != 0
    assert not router.pin_file_path(tmp_path).exists()
    assert "pkit sync" in result.output


def test_pin_strips_leading_v_and_routes_bare(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`pin v1.145.0` normalises to the bare `1.145.0` — so the router builds
    `@v1.145.0`, never a broken `@vv1.145.0`."""
    _git_repo(tmp_path)
    _write_manifest(tmp_path, "1.145.0")  # equal → freeze in place
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(main, ["pin", "v1.145.0"])

    assert result.exit_code == 0
    written = router.read_version_pin(tmp_path)
    assert written == "1.145.0"  # the leading `v` was stripped before writing
    # And the router routes the written pin to the bare `v<semver>` tag.
    assert f"@v{written}" in " ".join(router._pinned_base(written))
    assert "@vv" not in " ".join(router._pinned_base(written))


@pytest.mark.parametrize(
    "token",
    [
        "feature-branch",  # branch name
        "abc1234",  # commit sha
        "1.2.3rc1",  # pre-release
        "1.2.3+build",  # build metadata
        "1.2",  # not three-part
        "latest",  # tag alias
    ],
)
def test_pin_refuses_non_semver_token(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, token: str
) -> None:
    """Only a bare `MAJOR.MINOR.PATCH` semver is accepted; everything else is
    refused (exit non-zero, nothing written) — the router can't route it."""
    _git_repo(tmp_path)
    _write_manifest(tmp_path, "1.0.0")
    monkeypatch.chdir(tmp_path)

    def _boom(*_a: object, **_k: object) -> int:
        raise AssertionError("a refused token must not reconcile content")

    monkeypatch.setattr(upgrade, "run_bypassed", _boom)

    result = CliRunner().invoke(main, ["pin", token])

    assert result.exit_code != 0
    assert not router.pin_file_path(tmp_path).exists()
    assert "1.145.0" in result.output  # the "takes a version like …" guidance


def test_pin_version_refuses_when_manifest_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`pin <version>` has nothing to order the target against without a manifest
    → hard refuse (exit non-zero, nothing written)."""
    _git_repo(tmp_path)  # .pkit/ exists but no manifest.yaml
    monkeypatch.chdir(tmp_path)

    def _boom(*_a: object, **_k: object) -> int:
        raise AssertionError("a refused pin must not reconcile content")

    monkeypatch.setattr(upgrade, "run_bypassed", _boom)

    result = CliRunner().invoke(main, ["pin", "1.99.0"])

    assert result.exit_code != 0
    assert not router.pin_file_path(tmp_path).exists()
    assert "pkit sync" in result.output


def test_pin_overwrites_an_existing_pin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _git_repo(tmp_path)
    _write_manifest(tmp_path, "2.0.0")
    monkeypatch.chdir(tmp_path)
    router.pin_file_path(tmp_path).write_text("1.0.0\n", encoding="utf-8")

    result = CliRunner().invoke(main, ["pin", "2.0.0"])  # equal → freeze in place

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


# --- `pin <version>` reconcile + downgrade guard (ADR-049) ----------------------


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
    past content that failed to land (ADR-049)."""
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


def test_pin_newer_in_routed_context_reconciles_content_not_just_flips_pin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`pin <newer>` invoked as a routed child (PKIT_ROUTED set) bootstraps the
    reconcile with routing truly OFF — PKIT_NO_ROUTE set AND PKIT_ROUTED cleared —
    so the target's `upgrade` reaches its content-sync path instead of re-detecting
    itself as the routed pinned child and no-op'ing (which would flip the pin
    without syncing content: pin-ahead-of-content corruption). Regression for the
    env-leak (ADR-049)."""
    _git_repo(tmp_path)
    _write_manifest(tmp_path, "1.0.0")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv(router._LOOP_GUARD_ENV, "1")  # we are the pinned routed child

    captured: dict[str, object] = {}
    real_run = subprocess.run

    def _fake_run(cmd, *args, **kwargs):  # type: ignore[no-untyped-def]
        # Intercept only the bootstrap `uvx …` spawn; delegate everything else
        # (the CLI's `git rev-parse` root resolution) to the genuine run, since
        # patching the shared `subprocess` module replaces `run` process-wide.
        if list(cmd[:1]) != ["uvx"]:
            return real_run(cmd, *args, **kwargs)
        captured["cmd"] = list(cmd)
        captured["env"] = kwargs["env"]
        return subprocess.CompletedProcess(cmd, 0)

    # run_bypassed spawns via router.subprocess.run — patch there so the real
    # env-clearing logic runs (not a stubbed run_bypassed).
    monkeypatch.setattr(router.subprocess, "run", _fake_run)

    result = CliRunner().invoke(main, ["pin", "2.0.0"])

    assert result.exit_code == 0
    cmd = captured["cmd"]
    assert cmd[-1] == "upgrade"
    assert f"{router.DISTRIBUTION_GIT_URL}@v2.0.0" in cmd
    env = captured["env"]
    assert env[router._BYPASS_ENV] == "1"  # routing bypassed for the reconcile
    assert router._LOOP_GUARD_ENV not in env  # cleared → grandchild reconciles for real
    assert router.read_version_pin(tmp_path) == "2.0.0"  # flipped after reconcile


# --- Sync-exclusion invariant (ADR-049): init / sync never touch the pin --------


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
    directive is never seeded (ADR-049 — it is created only by `pkit pin`)."""
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
