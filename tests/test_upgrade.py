"""Tests for `pkit upgrade` (PR-J of the build roadmap)."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import click
import pytest
from packaging.version import Version

from project_kit import install, manifest, router, upgrade
from tests.adopter_repo import MakeAdopterRepo


@pytest.fixture
def installed_target(make_adopter_repo: MakeAdopterRepo) -> Path:
    """A git repo with the kit installed; ready for upgrade."""
    return make_adopter_repo().root


class _RecordingRun:
    """Stand-in for `subprocess.run` while the ADR-063 staleness check runs.

    Intercepts only the `git ls-remote` the check issues — returning a
    configurable stdout/returncode (or raising a configured exception) to drive
    the staleness branches, so the suite never touches the network. Every *other*
    command (git plumbing in fixtures, the real migration scripts) is delegated
    to the genuine `subprocess.run`, since patching the shared `subprocess`
    module replaces `run` process-wide. Records every argv so a test can assert
    what was — and was not — invoked, in particular whether `pkit upgrade`
    shells out to `uv tool install`: it does not where it may only print the
    command (no terminal, as under the suite, `--no-self-update`, a dry run, or
    a pkit that is not the installed tool).

    It also answers the tool step's two `uv` calls, so the suite never asks the
    machine's real `uv`: `uv tool dir` (default: fails, so the running pkit is
    not the installed tool) and `uv tool install` (default: succeeds).
    """

    def __init__(self, real_run) -> None:
        self._real_run = real_run
        self.calls: list[list[str]] = []
        self.ls_remote_stdout = ""
        self.ls_remote_returncode = 1  # default: lookup fails → degrade path
        self.raise_exc: Exception | None = None
        self.tool_dir_stdout = ""
        self.tool_dir_returncode = 1  # default: `uv` cannot say → not the installed tool
        self.tool_dir_exc: Exception | None = None
        self.install_returncode = 0

    def __call__(self, argv, *args, **kwargs):
        self.calls.append(list(argv))
        if list(argv[:3]) == ["uv", "tool", "dir"]:
            if self.tool_dir_exc is not None:
                raise self.tool_dir_exc
            return subprocess.CompletedProcess(
                argv, self.tool_dir_returncode, self.tool_dir_stdout, ""
            )
        if list(argv[:3]) == ["uv", "tool", "install"]:
            return subprocess.CompletedProcess(argv, self.install_returncode, "", "")
        if list(argv[:2]) != ["git", "ls-remote"]:
            return self._real_run(argv, *args, **kwargs)
        if self.raise_exc is not None:
            raise self.raise_exc
        return subprocess.CompletedProcess(
            argv, self.ls_remote_returncode, self.ls_remote_stdout, ""
        )

    @property
    def ls_remote_calls(self) -> list[list[str]]:
        return [c for c in self.calls if c[:2] == ["git", "ls-remote"]]

    @property
    def install_calls(self) -> list[list[str]]:
        return [c for c in self.calls if c[:3] == ["uv", "tool", "install"]]


@pytest.fixture(autouse=True)
def stub_ls_remote(monkeypatch: pytest.MonkeyPatch) -> _RecordingRun:
    """Intercept the ADR-063 staleness check's `git ls-remote` so it never touches
    the network anywhere in this suite (all other subprocess calls pass through).
    Defaults to a *failed* ls-remote (the degrade path); tests exercising the
    stale/current branches configure the returned recorder."""
    rec = _RecordingRun(subprocess.run)
    monkeypatch.setattr(subprocess, "run", rec)
    return rec


def _tag_output(*versions: str) -> str:
    """Fabricate `git ls-remote --tags` output for the given `v<semver>` tags.

    Emits both the tag ref and its dereferenced-annotated peel (`^{}`) line, so
    the parser's `^{}` stripping is exercised.
    """
    sha = "0" * 40
    lines: list[str] = []
    for v in versions:
        lines.append(f"{sha}\trefs/tags/v{v}")
        lines.append(f"{sha}\trefs/tags/v{v}^{{}}")
    return "\n".join(lines) + "\n"


def test_upgrade_refuses_when_pkit_dir_missing(tmp_path: Path) -> None:
    with pytest.raises(click.ClickException, match=r"\.pkit/ does not exist"):
        upgrade.run_upgrade(tmp_path)


def test_upgrade_self_host_delegates_to_sync(monkeypatch: pytest.MonkeyPatch) -> None:
    """On self-host (source == target), upgrade short-circuits to sync's deploy.

    There is no backbone to upgrade — the source IS the installed state — so
    upgrade runs sync's self-host branch (which re-runs the deploy primitives)
    and skips the version comparison + migration steps (ADR-065 point 1).
    """
    source_repo = install.find_source_kit().parent
    monkeypatch.chdir(source_repo)

    called = {"sync": 0}

    def _spy_self_host(_target_root: Path, _source_kit: Path, *, dry_run: bool = False) -> None:
        called["sync"] += 1

    monkeypatch.setattr(upgrade, "run_self_host", _spy_self_host)

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
        (adir / "package.yaml").write_text(
            _adapter_pkg("9.9.9", adapter_requires), encoding="utf-8"
        )
    return src


def test_compat_ignores_stale_installed_ceiling(
    installed_target: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The fix: a stale *installed* requires_backbone that excludes the target must
    NOT block the upgrade — the check reads the *source* (post-upgrade) ceiling,
    which auto-broadens with the backbone. Reproduces the interaction-gateway
    deadlock (installed adapter `<old>`, source compatible)."""
    pkg = installed_target / ".pkit" / "adapters" / "claude-code" / "package.yaml"
    pkg.write_text(
        _adapter_pkg("0.1.0", ">=0.1.0,<0.5.0"), encoding="utf-8"
    )  # stale, excludes source

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
    src = _fake_source(
        tmp_path, version="2.0.0", adapter_requires=None
    )  # source dropped the adapter
    monkeypatch.setattr(upgrade, "find_source_kit", lambda: src)
    pkg = installed_target / ".pkit" / "adapters" / "claude-code" / "package.yaml"
    pkg.write_text(
        _adapter_pkg("0.1.0", ">=0.1.0,<1.5.0"), encoding="utf-8"
    )  # installed excludes 2.0.0
    with pytest.raises(click.ClickException, match="compatibility check failed"):
        upgrade.run_upgrade(installed_target)


@pytest.mark.parametrize(
    ("written", "refused"),
    [
        # Single quotes are YAML too: the range governs, as `pkit validate` reads it.
        ("requires_backbone: '>=0.1.0,<1.5.0'\n", True),
        # A commented-out range is no range; the one below it governs.
        (
            '# requires_backbone: ">=0.1.0,<1.5.0"\nrequires_backbone: ">=0.1.0,<99.0.0"\n',
            False,
        ),
    ],
)
def test_compat_reads_the_range_as_the_resolver_does(
    installed_target: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    written: str,
    refused: bool,
) -> None:
    """The source range is read as YAML, however it is quoted, and compared through
    the resolver's one relation — never picked out of the text by a pattern."""
    src = _fake_source(tmp_path, version="2.0.0", adapter_requires=">=0.1.0,<99.0.0")
    package = src / "adapters" / "claude-code" / "package.yaml"
    package.write_text(
        _adapter_pkg("9.9.9", "").replace('requires_backbone: ""\n', written), encoding="utf-8"
    )
    monkeypatch.setattr(upgrade, "find_source_kit", lambda: src)
    monkeypatch.setattr(upgrade, "propagate", lambda *args, **kwargs: None)
    if refused:
        with pytest.raises(click.ClickException, match=r"requires backbone >=0\.1\.0,<1\.5\.0"):
            upgrade.run_upgrade(installed_target, dry_run=True)
    else:
        upgrade.run_upgrade(installed_target, dry_run=True)


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


# --- pin-by-default on upgrade (ADR-064) ----------------------------


def _recorded_version(target: Path) -> str:
    m = manifest.read_backbone_manifest(target)
    assert m is not None
    return m.backbone_version


def test_upgrade_pins_unpinned_project_by_default(installed_target: Path) -> None:
    """Plain `pkit upgrade` pins an un-pinned project at the content version — the
    reversed default (pin-by-default), no flag needed."""
    assert router.read_version_pin(installed_target) is None
    upgrade.run_upgrade(installed_target)  # default: pins
    assert router.read_version_pin(installed_target) == _recorded_version(installed_target)


def test_upgrade_no_pin_leaves_project_unpinned(installed_target: Path) -> None:
    """`--no-pin` (pin=False) opts out — the project stays un-pinned (old behaviour)."""
    upgrade.run_upgrade(installed_target, pin=False)
    assert router.read_version_pin(installed_target) is None


def test_upgrade_dry_run_writes_no_pin(
    installed_target: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`--dry-run` reports the pin it would write by default but touches nothing."""
    upgrade.run_upgrade(installed_target, dry_run=True)
    assert router.read_version_pin(installed_target) is None
    assert "would pin" in capsys.readouterr().out


def test_upgrade_pin_is_noop_when_already_pinned(installed_target: Path) -> None:
    """An already-pinned project: the default pin write is a no-op (pin machinery maintains it)."""
    version = _recorded_version(installed_target)
    upgrade.freeze_pin(installed_target, version)
    upgrade.run_upgrade(installed_target)  # must not raise / must not change
    assert router.read_version_pin(installed_target) == version


def test_upgrade_skips_pin_when_sync_fails(
    installed_target: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The default pin writes nothing when the content sync fails — the flip-last
    invariant: a failed upgrade never leaves a pin ahead of content that didn't land."""
    m = manifest.read_backbone_manifest(installed_target)
    assert m is not None
    m.backbone_version = "0.1.0"  # force the upgrade to reach the sync step
    manifest.write_backbone_manifest(installed_target, m)

    def _boom(*_args: object, **_kwargs: object) -> None:
        raise click.ClickException("sync failed")

    monkeypatch.setattr(upgrade, "propagate", _boom)

    with pytest.raises(click.ClickException):
        upgrade.run_upgrade(installed_target)  # default pins, but sync fails first
    assert router.read_version_pin(installed_target) is None  # pin never written


def test_upgrade_no_pin_on_real_move_stays_unpinned(installed_target: Path) -> None:
    """`--no-pin` on an upgrade that actually moves content advances the content but
    leaves the project un-pinned."""
    source_version = _recorded_version(installed_target)
    m = manifest.read_backbone_manifest(installed_target)
    assert m is not None
    m.backbone_version = "0.1.0"
    manifest.write_backbone_manifest(installed_target, m)

    upgrade.run_upgrade(installed_target, pin=False)

    assert _recorded_version(installed_target) == source_version  # content moved
    assert router.read_version_pin(installed_target) is None  # but stayed un-pinned


def test_upgrade_default_on_real_move_pins_at_new_version(installed_target: Path) -> None:
    """A default upgrade that moves content pins at the new synced version (flip-last)."""
    source_version = _recorded_version(installed_target)
    m = manifest.read_backbone_manifest(installed_target)
    assert m is not None
    m.backbone_version = "0.1.0"
    manifest.write_backbone_manifest(installed_target, m)

    upgrade.run_upgrade(installed_target)  # default pins

    assert _recorded_version(installed_target) == source_version  # content moved
    assert router.read_version_pin(installed_target) == source_version  # pin followed


def test_cli_upgrade_no_pin_flag_forwards(monkeypatch: pytest.MonkeyPatch) -> None:
    """`--no-pin` threads through to `run_upgrade(pin=False)`; the default is `pin=True`."""
    from click.testing import CliRunner

    from project_kit import cli

    captured: dict[str, object] = {}

    def _fake(target_root: Path, **kwargs: object) -> None:
        captured["pin"] = kwargs.get("pin")

    monkeypatch.setattr(cli, "run_upgrade", _fake)
    monkeypatch.setattr(cli, "find_target_root", lambda: Path("/tmp"))

    res = CliRunner().invoke(cli.main, ["upgrade", "--no-pin"])
    assert res.exit_code == 0, res.output
    assert captured["pin"] is False

    res = CliRunner().invoke(cli.main, ["upgrade"])  # default
    assert res.exit_code == 0, res.output
    assert captured["pin"] is True


# --- tool self-update (ADR-063) --------------------------------------


def _stale(monkeypatch: pytest.MonkeyPatch, running: str = "0.1.0", latest: str = "9.9.9") -> None:
    monkeypatch.setattr(upgrade, "running_version", lambda: running)
    monkeypatch.setattr(upgrade, "_latest_released_version", lambda: Version(latest))


def test_self_update_acts_when_stale_and_allowed(monkeypatch: pytest.MonkeyPatch) -> None:
    _stale(monkeypatch)
    monkeypatch.setattr(upgrade, "_self_update_allowed", lambda: True)
    monkeypatch.setattr(upgrade, "_running_is_installed_tool", lambda: True)
    calls: dict = {"install": None, "reexec": 0}
    monkeypatch.setattr(
        upgrade, "_self_update_tool", lambda v: calls.__setitem__("install", v) or True
    )
    monkeypatch.setattr(
        upgrade,
        "_reexec_after_self_update",
        lambda v: calls.__setitem__("reexec", calls["reexec"] + 1),
    )
    upgrade._maybe_self_update_tool(self_update=True, dry_run=False)
    assert calls["install"] == Version("9.9.9")
    assert calls["reexec"] == 1


def test_self_update_degrades_when_not_allowed(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _stale(monkeypatch)
    monkeypatch.setattr(upgrade, "_self_update_allowed", lambda: False)
    installed = {"v": False}
    monkeypatch.setattr(
        upgrade, "_self_update_tool", lambda v: installed.__setitem__("v", True) or True
    )
    upgrade._maybe_self_update_tool(self_update=True, dry_run=False)
    assert installed["v"] is False
    assert "uv tool install --force" in capsys.readouterr().out  # instruct


def test_self_update_off_instructs(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _stale(monkeypatch)
    monkeypatch.setattr(upgrade, "_self_update_allowed", lambda: True)
    installed = {"v": False}
    monkeypatch.setattr(
        upgrade, "_self_update_tool", lambda v: installed.__setitem__("v", True) or True
    )
    upgrade._maybe_self_update_tool(self_update=False, dry_run=False)
    assert installed["v"] is False
    assert "uv tool install --force" in capsys.readouterr().out


def test_self_update_install_failure_degrades(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _stale(monkeypatch)
    monkeypatch.setattr(upgrade, "_self_update_allowed", lambda: True)
    monkeypatch.setattr(upgrade, "_running_is_installed_tool", lambda: True)
    monkeypatch.setattr(upgrade, "_self_update_tool", lambda v: False)  # install fails
    reexec = {"n": 0}
    monkeypatch.setattr(
        upgrade, "_reexec_after_self_update", lambda v: reexec.__setitem__("n", reexec["n"] + 1)
    )
    upgrade._maybe_self_update_tool(self_update=True, dry_run=False)
    assert reexec["n"] == 0
    assert "uv tool install --force" in capsys.readouterr().out


def test_self_update_dry_run_reports_no_install(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _stale(monkeypatch)
    monkeypatch.setattr(upgrade, "_self_update_allowed", lambda: True)
    monkeypatch.setattr(upgrade, "_running_is_installed_tool", lambda: True)
    installed = {"v": False}
    monkeypatch.setattr(
        upgrade, "_self_update_tool", lambda v: installed.__setitem__("v", True) or True
    )
    upgrade._maybe_self_update_tool(self_update=True, dry_run=True)
    assert installed["v"] is False
    assert "would run" in capsys.readouterr().out


def test_self_update_current_tool_noops(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _stale(monkeypatch, running="9.9.9", latest="9.9.9")  # equal → current
    installed = {"v": False}
    monkeypatch.setattr(
        upgrade, "_self_update_tool", lambda v: installed.__setitem__("v", True) or True
    )
    upgrade._maybe_self_update_tool(self_update=True, dry_run=False)
    assert installed["v"] is False
    assert "tool is current" in capsys.readouterr().out


def test_self_update_allowed_false_when_guarded(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(upgrade._SELF_UPDATED_ENV, "1")
    assert upgrade._self_update_allowed() is False


def test_run_tool_update_forwards_no_project(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict = {}
    monkeypatch.setattr(
        upgrade,
        "_maybe_self_update_tool",
        lambda *, self_update, dry_run: seen.update(su=self_update),
    )
    upgrade.run_tool_update(dry_run=False, self_update=True)
    assert seen["su"] is True


def test_cli_upgrade_outside_project_updates_tool(monkeypatch: pytest.MonkeyPatch) -> None:
    from click.testing import CliRunner

    from project_kit import cli

    called = {"tool": False}
    monkeypatch.setattr(cli, "find_target_root", lambda: None)
    monkeypatch.setattr(cli, "run_tool_update", lambda **k: called.__setitem__("tool", True))
    res = CliRunner().invoke(cli.main, ["upgrade"])
    assert res.exit_code == 0, res.output
    assert called["tool"] is True  # tool-only update, not an error


def test_cli_upgrade_with_stray_pkit_above_cwd_updates_tool(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """#656 end-to-end: a stray `.pkit/` holding only junk above CWD (the
    leftover-`~/.pkit` shape) must not resolve as a project root. Upgrade
    takes the tool-only path and never emits the seed-the-manifest
    remediation (which would invite `pkit sync` into the stray directory).

    Uses the REAL `find_target_root` (unlike the test above): the stray
    `.pkit` fails the install-marker check, the walk continues upward, and
    resolution comes back None."""
    from click.testing import CliRunner

    from project_kit import cli

    home = tmp_path / "home"
    (home / ".pkit" / "shim").mkdir(parents=True)  # junk only — no markers
    workdir = home / "pkit_temp"
    workdir.mkdir()
    monkeypatch.chdir(workdir)
    monkeypatch.setenv("PATH", "/nonexistent")  # no git → the stage-2 walk runs

    called = {"tool": False}
    monkeypatch.setattr(cli, "run_tool_update", lambda **k: called.__setitem__("tool", True))
    res = CliRunner().invoke(cli.main, ["upgrade"])
    assert res.exit_code == 0, res.output
    assert called["tool"] is True
    assert "manifest.yaml is missing" not in res.output


def test_cli_upgrade_no_self_update_forwards(monkeypatch: pytest.MonkeyPatch) -> None:
    from click.testing import CliRunner

    from project_kit import cli

    seen: dict = {}
    monkeypatch.setattr(cli, "find_target_root", lambda: Path("/tmp"))
    monkeypatch.setattr(cli, "run_upgrade", lambda tr, **k: seen.update(k))
    res = CliRunner().invoke(cli.main, ["upgrade", "--no-self-update"])
    assert res.exit_code == 0, res.output
    assert seen["self_update"] is False


# --- the tool step runs only under the installed tool (#1473) -------------------


class _HandedOver(Exception):
    """Stands in for the process replacement a successful `os.execvpe` makes."""


def _stale_at_a_terminal(
    stub_ls_remote: _RecordingRun, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> Path:
    """A stale running pkit (1.0.0 behind 2.5.0) at a terminal, with no guard, and
    `uv tool dir` answering `<tmp>/tools`. Returns the installed tool's
    environment, `<tmp>/tools/project-kit`; the test sets `sys.prefix`."""
    stub_ls_remote.ls_remote_returncode = 0
    stub_ls_remote.ls_remote_stdout = _tag_output("1.0.0", "2.5.0")
    monkeypatch.setattr(upgrade, "running_version", lambda: "1.0.0")
    monkeypatch.setattr(upgrade, "_is_tty", lambda _stream: True)
    monkeypatch.delenv(upgrade._SELF_UPDATED_ENV, raising=False)
    monkeypatch.setattr(upgrade.sys, "argv", ["pkit", "upgrade"])
    tools = tmp_path / "tools"
    environment = tools / "project-kit"
    environment.mkdir(parents=True)
    stub_ls_remote.tool_dir_returncode = 0
    stub_ls_remote.tool_dir_stdout = f"{tools}\n"
    return environment


def _record_exec(monkeypatch: pytest.MonkeyPatch, error: OSError | None = None) -> list[tuple]:
    """Patch `os.execvpe`: record each call, then raise `error`, or `_HandedOver`
    in place of the process replacement."""
    calls: list[tuple] = []

    def _execvpe(file: str, args: list[str], env: dict[str, str]) -> None:
        calls.append((file, list(args), dict(env)))
        raise error if error is not None else _HandedOver()

    monkeypatch.setattr(upgrade.os, "execvpe", _execvpe)
    return calls


def _content_behind(target: Path) -> None:
    """Put the project's content behind the running pkit's, so an upgrade that went
    on would sync and pin."""
    m = manifest.read_backbone_manifest(target)
    assert m is not None
    m.backbone_version = "0.1.0"
    manifest.write_backbone_manifest(target, m)


@pytest.mark.parametrize(
    "prefix",
    [
        pytest.param(("cache", "uv", "archive-v0", "Xq3vB1"), id="uvx"),
        pytest.param(("project", ".venv"), id="uv-run"),
        pytest.param(("pip-env",), id="pip"),
    ],
)
def test_tool_step_not_under_the_installed_tool_reports_and_goes_on(
    prefix: tuple[str, ...],
    installed_target: Path,
    stub_ls_remote: _RecordingRun,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A stale pkit run through `uvx`, `uv run` or a pip install, at a terminal,
    reports the newer release and its install command, installs nothing, hands
    over to no other pkit, and goes on under itself to the project's own steps."""
    _stale_at_a_terminal(stub_ls_remote, monkeypatch, tmp_path)
    running_from = tmp_path.joinpath(*prefix)
    running_from.mkdir(parents=True)
    monkeypatch.setattr(upgrade.sys, "prefix", str(running_from))
    execs = _record_exec(monkeypatch)

    upgrade.run_upgrade(installed_target)

    out = capsys.readouterr().out
    assert "This pkit is not the `uv`-installed tool" in out
    assert "A newer pkit tool is available: v2.5.0 (you are running v1.0.0)." in out
    assert f"uv tool install --force {upgrade.DISTRIBUTION_GIT_URL}@v2.5.0" in out
    assert stub_ls_remote.install_calls == []
    assert execs == []
    # It went on under itself: the project's own steps ran, to the default pin.
    assert "Already at backbone v" in out
    assert router.read_version_pin(installed_target) == _recorded_version(installed_target)


def test_tool_step_dry_run_not_under_the_installed_tool_would_install_nothing(
    stub_ls_remote: _RecordingRun,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A dry run predicts the real run: a pkit that is not the installed tool says
    so and prints the command, not the install it would run."""
    _stale_at_a_terminal(stub_ls_remote, monkeypatch, tmp_path)
    monkeypatch.setattr(upgrade.sys, "prefix", str(tmp_path / "project" / ".venv"))

    upgrade._maybe_self_update_tool(self_update=True, dry_run=True)

    out = capsys.readouterr().out
    assert "This pkit is not the `uv`-installed tool" in out
    assert "would run" not in out
    assert f"uv tool install --force {upgrade.DISTRIBUTION_GIT_URL}@v2.5.0" in out
    assert stub_ls_remote.install_calls == []


def test_tool_step_under_the_installed_tool_installs_and_hands_over(
    installed_target: Path,
    stub_ls_remote: _RecordingRun,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """The installed tool, stale at a terminal, installs the latest release and
    hands the same command to the `pkit` on the PATH, under the guard, before
    the project's own steps."""
    environment = _stale_at_a_terminal(stub_ls_remote, monkeypatch, tmp_path)
    monkeypatch.setattr(upgrade.sys, "prefix", str(environment))
    execs = _record_exec(monkeypatch)

    with pytest.raises(_HandedOver):
        upgrade.run_upgrade(installed_target)

    assert stub_ls_remote.install_calls == [
        ["uv", "tool", "install", "--force", f"{upgrade.DISTRIBUTION_GIT_URL}@v2.5.0"]
    ]
    [(file, args, env)] = execs
    assert (file, args) == ("pkit", ["pkit", "upgrade"])
    assert env[upgrade._SELF_UPDATED_ENV] == "1"
    assert router.read_version_pin(installed_target) is None


def test_tool_step_hand_over_that_cannot_start_pins_nothing(
    installed_target: Path,
    stub_ls_remote: _RecordingRun,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """The install succeeds but `pkit` cannot be started: the upgrade stops before
    it syncs or pins, and names the command to re-run."""
    environment = _stale_at_a_terminal(stub_ls_remote, monkeypatch, tmp_path)
    monkeypatch.setattr(upgrade.sys, "prefix", str(environment))
    monkeypatch.setattr(upgrade.sys, "argv", ["pkit", "upgrade", "--no-pin"])
    _record_exec(monkeypatch, FileNotFoundError(2, "No such file or directory"))
    _content_behind(installed_target)
    synced: list[Path] = []
    monkeypatch.setattr(upgrade, "propagate", lambda ctx, _caps: synced.append(ctx.target_root))

    with pytest.raises(click.ClickException) as raised:
        upgrade.run_upgrade(installed_target)

    message = raised.value.format_message()
    assert "pkit v2.5.0 was installed, but `pkit` could not be started" in message
    assert "No such file or directory" in message
    assert "stopped before it synced or pinned anything" in message
    assert message.endswith("    pkit upgrade --no-pin")
    assert synced == []
    assert _recorded_version(installed_target) == "0.1.0"
    assert router.read_version_pin(installed_target) is None


def test_tool_step_hand_over_to_a_pkit_still_behind_pins_nothing(
    installed_target: Path,
    stub_ls_remote: _RecordingRun,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """The run the hand-over started finds itself still behind: the PATH found an
    older `pkit` first. It stops before it syncs or pins, installs nothing, and
    names the command to re-run."""
    _stale_at_a_terminal(stub_ls_remote, monkeypatch, tmp_path)
    monkeypatch.setenv(upgrade._SELF_UPDATED_ENV, "1")
    monkeypatch.setattr(upgrade.sys, "prefix", str(tmp_path / "pip-env"))
    execs = _record_exec(monkeypatch)
    _content_behind(installed_target)
    synced: list[Path] = []
    monkeypatch.setattr(upgrade, "propagate", lambda ctx, _caps: synced.append(ctx.target_root))

    with pytest.raises(click.ClickException) as raised:
        upgrade.run_upgrade(installed_target)

    message = raised.value.format_message()
    assert "a newer pkit tool (v2.5.0) was installed" in message
    assert "runs first is v1.0.0" in message
    assert "stopped before it synced or pinned anything" in message
    assert message.endswith("    pkit upgrade")
    assert stub_ls_remote.install_calls == []
    assert execs == []
    assert synced == []
    assert _recorded_version(installed_target) == "0.1.0"
    assert router.read_version_pin(installed_target) is None


def test_tool_step_hand_over_to_the_installed_tool_still_behind_goes_on(
    installed_target: Path,
    stub_ls_remote: _RecordingRun,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The run the hand-over started is the installed tool, yet still behind: the
    release just installed reports a version below its tag. The PATH is not at
    fault, so it does not stop. The guard keeps it from installing again; it
    prints the command and goes on to the project's own steps."""
    environment = _stale_at_a_terminal(stub_ls_remote, monkeypatch, tmp_path)
    monkeypatch.setenv(upgrade._SELF_UPDATED_ENV, "1")
    monkeypatch.setattr(upgrade.sys, "prefix", str(environment))
    execs = _record_exec(monkeypatch)

    upgrade.run_upgrade(installed_target)

    out = capsys.readouterr().out
    assert f"uv tool install --force {upgrade.DISTRIBUTION_GIT_URL}@v2.5.0" in out
    assert stub_ls_remote.install_calls == []
    assert execs == []
    assert router.read_version_pin(installed_target) == _recorded_version(installed_target)


def test_tool_step_guard_without_a_terminal_does_not_stop(
    installed_target: Path,
    stub_ls_remote: _RecordingRun,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The guard set where no install ran — no terminal, so no hand-over could
    have started this run — prints the command and goes on, as it always did."""
    _stale_at_a_terminal(stub_ls_remote, monkeypatch, tmp_path)
    monkeypatch.setattr(upgrade, "_is_tty", lambda _stream: False)
    monkeypatch.setenv(upgrade._SELF_UPDATED_ENV, "1")
    monkeypatch.setattr(upgrade.sys, "prefix", str(tmp_path / "pip-env"))

    upgrade.run_upgrade(installed_target)

    out = capsys.readouterr().out
    assert f"uv tool install --force {upgrade.DISTRIBUTION_GIT_URL}@v2.5.0" in out
    assert stub_ls_remote.install_calls == []
    assert router.read_version_pin(installed_target) == _recorded_version(installed_target)


def test_running_is_installed_tool_when_prefix_is_the_tool_environment(
    stub_ls_remote: _RecordingRun, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    environment = _stale_at_a_terminal(stub_ls_remote, monkeypatch, tmp_path)
    monkeypatch.setattr(upgrade.sys, "prefix", str(environment))
    assert upgrade._running_is_installed_tool() is True


@pytest.mark.parametrize(
    "answer",
    [
        pytest.param({"tool_dir_exc": FileNotFoundError("uv")}, id="uv-missing"),
        pytest.param(
            {"tool_dir_exc": subprocess.TimeoutExpired(cmd="uv tool dir", timeout=5.0)},
            id="uv-slow",
        ),
        pytest.param({"tool_dir_returncode": 2}, id="uv-fails"),
        pytest.param({"tool_dir_stdout": "\n"}, id="no-path"),
        pytest.param({"tool_dir_stdout": "/a\n/b\n"}, id="two-paths"),
        pytest.param(
            {"tool_dir_exc": UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid start byte")},
            id="undecodable",
        ),
        pytest.param({"tool_dir_stdout": "/a\x00b\n"}, id="nul-in-path"),
    ],
)
def test_running_is_installed_tool_answers_no_when_uv_cannot_tell(
    answer: dict,
    stub_ls_remote: _RecordingRun,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Any doubt answers "not the installed tool", which costs only the printed
    command — even when the running pkit is in fact the tool's environment."""
    environment = _stale_at_a_terminal(stub_ls_remote, monkeypatch, tmp_path)
    monkeypatch.setattr(upgrade.sys, "prefix", str(environment))
    for name, value in answer.items():
        setattr(stub_ls_remote, name, value)
    assert upgrade._running_is_installed_tool() is False


# --- backbone + component migration execution (per COR-010) ----------


def _stage_backbone_migration(source_kit: Path, version: str, script_name: str, body: str) -> Path:
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
    # Move both recorded states backwards so upgrade has work to do.
    _record_finished_at(installed_target, "0.1.0")

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
    _record_finished_at(installed_target, "0.1.0")

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
        "schema_version: 1\ncomponent:\n  kind: capability\n  name: evidence-fake\n"
        "  version: 0.2.0\n"
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

    _run_component_migrations(
        installed_target, install.find_source_kit(), backbone_manifest.components, dry_run=False
    )
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
    requires_capabilities: list[dict[str, Any]] | None = None,
) -> None:
    """Directly create a capability under .pkit/capabilities/<name>/ and register it.

    Bypasses source-kit lookup — used in upgrade tests where we only need
    the installed state, not the source. The package.yaml is written to the
    installed path so _resolve_compatibility can read it.
    """
    from project_kit.manifest import (
        ComponentRegistryEntry,
        read_backbone_manifest,
        write_backbone_manifest,
    )

    cap_dir = target_root / ".pkit" / "capabilities" / name
    cap_dir.mkdir(parents=True, exist_ok=True)

    req_caps_block = ""
    if requires_capabilities:
        lines = ["requires_capabilities:"]
        for req in requires_capabilities:
            lines.append(f"  - name: {req['name']}")
            lines.append(f'    version: "{req["version"]}"')
            if req.get("optional"):
                lines.append("    optional: true")
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

    # Stamp a minimal per-component manifest under its project/, where a capability
    # records its version (ADR-065 point 2), so version reads work.
    import datetime as _dt

    (cap_dir / "project").mkdir(exist_ok=True)
    (cap_dir / "project" / "manifest.yaml").write_text(
        f"""schema_version: 1
component:
  kind: capability
  name: {name}
  version: {version}
  installed_at: '{_dt.datetime.now(_dt.UTC).isoformat()}'
requires_backbone: '{requires_backbone}'
backend_state: {{}}
""",
        encoding="utf-8",
    )

    # Register in backbone manifest.
    backbone = read_backbone_manifest(target_root)
    assert backbone is not None
    backbone.components = [
        c for c in backbone.components if not (c.kind == "capability" and c.name == name)
    ]
    backbone.components.append(
        ComponentRegistryEntry(
            kind="capability",
            name=name,
            manifest=f".pkit/capabilities/{name}/project/manifest.yaml",
        )
    )
    write_backbone_manifest(target_root, backbone)


def _package_text(
    name: str,
    version: str,
    requires_capabilities: list[dict[str, Any]] | None = None,
) -> str:
    """A capability's `package.yaml`, with the `requires_capabilities` given."""
    lines = [
        "schema_version: 1",
        "component:",
        "  kind: capability",
        f"  name: {name}",
        f"  version: {version}",
        "description: Test.",
        'requires_backbone: ">=0.0.0"',
    ]
    if requires_capabilities:
        lines.append("requires_capabilities:")
        for req in requires_capabilities:
            lines.append(f"  - name: {req['name']}")
            lines.append(f'    version: "{req["version"]}"')
            if req.get("optional"):
                lines.append("    optional: true")
    return "\n".join(lines) + "\n"


def _stage_moving_capability(
    source_kit: Path,
    target: Path,
    name: str,
    *,
    installed: str = "0.1.0",
    bundled: str = "0.2.0",
    requires_capabilities: list[dict[str, Any]] | None = None,
) -> None:
    """Capability *name* installed at *installed*, and bundled at *bundled* by
    *source_kit*, whose version requires *requires_capabilities*: the transition
    moves it."""
    _stage_installed_capability(target, name, version=installed)
    cap = source_kit / "capabilities" / name
    cap.mkdir(parents=True, exist_ok=True)
    (cap / "package.yaml").write_text(
        _package_text(name, bundled, requires_capabilities), encoding="utf-8"
    )


def test_the_gate_refuses_a_moving_capability_whose_dependency_is_not_installed(
    installed_target: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A moving capability's new version requires a capability the project has not
    installed: the project controls it, so the transition refuses with a hint,
    before it writes anything (ADR-065 point 6, COR-030)."""
    source = _real_source_copy(tmp_path)
    _use_source(monkeypatch, source)
    _stage_moving_capability(
        source,
        installed_target,
        "consumer",
        requires_capabilities=[{"name": "absent", "version": ">=0.1.0,<2.0.0"}],
    )
    before = _tree_bytes(installed_target)

    with pytest.raises(click.ClickException) as excinfo:
        upgrade.run_upgrade(installed_target, force=True)

    message = excinfo.value.message
    assert "capability dependency check failed" in message
    assert "capability 'consumer' v0.2.0 requires capability 'absent'" in message
    assert "which is not installed: install it first" in message
    assert _tree_bytes(installed_target) == before


@pytest.mark.parametrize("optional", [False, True], ids=["required", "optional"])
def test_the_gate_refuses_a_moving_capability_whose_dependency_does_not_move_out_of_range(
    installed_target: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, optional: bool
) -> None:
    """The dependency is installed, does not move, and is out of the range the
    moving capability's new version declares: refused, `--force` included. An
    installed optional dependency must meet its range too (COR-030)."""
    source = _real_source_copy(tmp_path)
    _use_source(monkeypatch, source)
    _stage_installed_capability(installed_target, "homegrown", version="0.1.0")
    _stage_moving_capability(
        source,
        installed_target,
        "consumer",
        requires_capabilities=[
            {"name": "homegrown", "version": ">=0.2.0,<2.0.0", "optional": optional}
        ],
    )

    with pytest.raises(click.ClickException) as excinfo:
        upgrade.run_upgrade(installed_target, force=True)

    assert (
        "capability 'consumer' v0.2.0 requires capability 'homegrown' >=0.2.0,<2.0.0, and "
        "v0.1.0 is installed, which this upgrade does not move: upgrade it first"
    ) in excinfo.value.message


def test_the_gate_passes_an_absent_optional_dependency(
    installed_target: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An optional dependency that is not installed passes (COR-030)."""
    source = _real_source_copy(tmp_path)
    _use_source(monkeypatch, source)
    _stage_moving_capability(
        source,
        installed_target,
        "consumer",
        requires_capabilities=[{"name": "absent", "version": ">=0.1.0", "optional": True}],
    )

    upgrade.run_upgrade(installed_target, pin=False)

    assert caps_version(installed_target, "consumer") == "0.2.0"


def caps_version(target: Path, name: str) -> str | None:
    from project_kit import capabilities as caps

    return caps.get_installed_capability_version(target, name)


def test_the_dependency_check_reads_the_versions_the_transition_installs(
    installed_target: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Installed at 0.1.0, the dependency is out of the range the dependent's new
    version declares, but the transition moves it to 0.2.0, inside the range: the
    check reads the versions the transition installs, so the upgrade proceeds
    (ADR-065 point 6)."""
    source = _real_source_copy(tmp_path)
    _use_source(monkeypatch, source)
    _stage_moving_capability(source, installed_target, "provider")
    _stage_moving_capability(
        source,
        installed_target,
        "consumer",
        requires_capabilities=[{"name": "provider", "version": ">=0.2.0,<1.0.0"}],
    )

    upgrade.run_upgrade(installed_target, pin=False)

    assert caps_version(installed_target, "consumer") == "0.2.0"
    assert caps_version(installed_target, "provider") == "0.2.0"


def test_the_gate_warns_when_a_moving_dependency_leaves_a_capability_that_does_not_move(
    installed_target: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The dependency moves past the range a capability that does not move
    declares for it: the transition warns, naming the dependent, and refuses
    unless `--force`, under which it proceeds (ADR-065 point 6, COR-030)."""
    source = _real_source_copy(tmp_path)
    _use_source(monkeypatch, source)
    _stage_moving_capability(source, installed_target, "provider")
    _stage_installed_capability(
        installed_target,
        "homegrown",
        requires_capabilities=[{"name": "provider", "version": ">=0.1.0,<0.2.0"}],
    )
    before = _tree_bytes(installed_target)

    with pytest.raises(click.ClickException) as excinfo:
        upgrade.run_upgrade(installed_target, pin=False)

    out = capsys.readouterr().out
    assert "Warning: 1 declared range(s) of a capability this upgrade does not move" in out
    assert "- 'homegrown' declares 'provider' >=0.1.0,<0.2.0 (this upgrade brings v0.2.0)" in out
    assert "or pass --force to proceed anyway" in excinfo.value.message
    assert _tree_bytes(installed_target) == before

    upgrade.run_upgrade(installed_target, pin=False, force=True)

    out = capsys.readouterr().out
    assert "Warning (--force): 1 declared range(s)" in out
    assert "Proceeding under --force" in out
    assert caps_version(installed_target, "provider") == "0.2.0"


def test_force_overrides_no_refusal_of_a_component_bundled_older(
    installed_target: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`pkit upgrade --force` overrides the two warnings and nothing else."""
    source = _real_source_copy(tmp_path)
    _use_source(monkeypatch, source)
    _stage_moving_capability(source, installed_target, "provider", installed="0.3.0")

    with pytest.raises(click.ClickException, match="no flag overrides this refusal"):
        upgrade.run_upgrade(installed_target, force=True)


def test_backbone_upgrade_succeeds_when_cap_deps_satisfied(
    installed_target: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Backbone upgrade proceeds when all capability dependency requirements are satisfied."""
    # At the version the bundle ships, so the capability is current too.
    bundled = (install.find_source_kit() / "capabilities" / "evidence" / "package.yaml").read_text(
        encoding="utf-8"
    )
    evidence_version = re.search(r"(?m)^  version: (\S+)", bundled)
    assert evidence_version is not None
    _stage_installed_capability(installed_target, "evidence", version=evidence_version.group(1))
    _stage_installed_capability(
        installed_target,
        "consumer",
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


# ============================================================================
# ADR-063: `pkit upgrade` detects a stale tool; without a terminal it prints
# ============================================================================


def test_tool_staleness_instructs_when_behind(
    installed_target: Path,
    stub_ls_remote: _RecordingRun,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Without a terminal, a running tool behind the latest release prints the
    exact update command and installs nothing (ADR-063 point 3). The project-sync
    axis is untouched."""
    stub_ls_remote.ls_remote_returncode = 0
    stub_ls_remote.ls_remote_stdout = _tag_output("1.0.0", "2.5.0")
    monkeypatch.setattr(upgrade, "running_version", lambda: "1.0.0")

    upgrade.run_upgrade(installed_target)  # must not raise

    out = capsys.readouterr().out
    assert "A newer pkit tool is available: v2.5.0" in out
    assert "you are running v1.0.0" in out
    assert f"uv tool install --force {upgrade.DISTRIBUTION_GIT_URL}@v2.5.0" in out
    # Print-only: the check queried the source but ran no install.
    assert stub_ls_remote.ls_remote_calls
    assert stub_ls_remote.install_calls == []
    # The project axis still reports normally (installed == source version).
    assert "Already at backbone v" in out


def test_tool_staleness_reports_current_when_up_to_date(
    installed_target: Path,
    stub_ls_remote: _RecordingRun,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A running tool at the latest release prints a plain "current" line instead
    of an instruction (ADR-063 point 1), and installs nothing."""
    stub_ls_remote.ls_remote_returncode = 0
    stub_ls_remote.ls_remote_stdout = _tag_output("1.0.0", "1.2.3")
    monkeypatch.setattr(upgrade, "running_version", lambda: "1.2.3")

    upgrade.run_upgrade(installed_target)

    out = capsys.readouterr().out
    assert "pkit tool is current (v1.2.3)." in out
    assert "A newer pkit tool is available" not in out
    assert stub_ls_remote.install_calls == []


def test_tool_staleness_degrades_on_ls_remote_failure_and_sync_proceeds(
    installed_target: Path,
    stub_ls_remote: _RecordingRun,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failed lookup warns loudly and never fails the command — today's sync
    still runs, exit code unchanged (ADR-063 point 1)."""
    # Force a version mismatch so the normal sync step actually runs.
    m = manifest.read_backbone_manifest(installed_target)
    assert m is not None
    m.backbone_version = "0.1.0"
    manifest.write_backbone_manifest(installed_target, m)

    called = {"sync": 0}

    def _spy_propagate(_ctx: object, _capabilities: object) -> None:
        called["sync"] += 1

    monkeypatch.setattr(upgrade, "propagate", _spy_propagate)

    # stub_ls_remote defaults to a failed lookup (returncode 1) → degrade.
    upgrade.run_upgrade(installed_target)  # must not raise → exit code unchanged

    captured = capsys.readouterr()
    assert "could not check for a newer pkit tool" in captured.err
    assert called["sync"] == 1  # today's behaviour proceeded
    assert stub_ls_remote.install_calls == []


def test_tool_staleness_degrades_on_timeout(
    installed_target: Path,
    stub_ls_remote: _RecordingRun,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A bounded-timeout expiry is caught and degrades to a warning (ADR-063 point 1)."""
    stub_ls_remote.raise_exc = subprocess.TimeoutExpired(cmd="git ls-remote", timeout=5.0)

    upgrade.run_upgrade(installed_target)  # must not raise

    assert "could not check for a newer pkit tool" in capsys.readouterr().err


def test_tool_staleness_degrades_when_git_missing(
    installed_target: Path,
    stub_ls_remote: _RecordingRun,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """`git` not on PATH (OSError) is caught and degrades to a warning (ADR-063 point 1)."""
    stub_ls_remote.raise_exc = FileNotFoundError("git")

    upgrade.run_upgrade(installed_target)  # must not raise

    assert "could not check for a newer pkit tool" in capsys.readouterr().err


def test_tool_staleness_ignores_malformed_tags(
    installed_target: Path,
    stub_ls_remote: _RecordingRun,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Non-release, malformed and pre-release tags are skipped; the highest
    release tag wins, so the tool step never offers a pre-release (#1472)."""
    stub_ls_remote.ls_remote_returncode = 0
    stub_ls_remote.ls_remote_stdout = (
        "0000000000000000000000000000000000000000\trefs/tags/not-a-version\n"
        "0000000000000000000000000000000000000000\trefs/tags/v-broken\n"
        "0000000000000000000000000000000000000000\trefs/tags/v3.1.0\n"
        "0000000000000000000000000000000000000000\trefs/tags/v3.2.0rc1\n"
    )
    monkeypatch.setattr(upgrade, "running_version", lambda: "1.0.0")

    upgrade.run_upgrade(installed_target)

    out = capsys.readouterr().out
    assert "A newer pkit tool is available: v3.1.0" in out
    assert "3.2.0rc1" not in out


@pytest.mark.parametrize(
    "above",
    [
        pytest.param("2.1.0rc1", id="release-candidate"),
        pytest.param("2.1.0a1", id="alpha"),
        pytest.param("2.1.0b1", id="beta"),
        pytest.param("2.1.0.dev1", id="dev-release"),
        pytest.param("2.1.0rc1.dev1", id="dev-release-of-a-pre-release"),
    ],
)
def test_max_released_tag_skips_a_pre_release_above_the_latest_release(above: str) -> None:
    """A pre-release or dev release tagged above the latest release is skipped:
    the latest release wins, as `pkit pin` and the release step refuse it (#1472)."""
    assert upgrade._max_released_tag(_tag_output("1.0.0", "2.0.0", above)) == Version("2.0.0")


@pytest.mark.parametrize(
    "above",
    [
        pytest.param("2.1.0.post1", id="post-release"),
        pytest.param("2.1.0+build", id="local-version"),
        pytest.param("2.1", id="two-part"),
        pytest.param("02.1.0", id="zero-padded"),
    ],
)
def test_max_released_tag_skips_a_tag_the_release_step_never_writes(above: str) -> None:
    """Only a tag the release test accepts counts, so the version found is spelled
    as its tag: a padded `v02.1.0` would otherwise come back as 2.1.0 and the tool
    step would install `@v2.1.0`, a tag that may not exist."""
    assert upgrade._max_released_tag(_tag_output("1.0.0", "2.0.0", above)) == Version("2.0.0")


def test_max_released_tag_is_none_when_only_pre_releases_are_tagged() -> None:
    """A tag list holding only pre-releases and dev releases has no release."""
    assert upgrade._max_released_tag(_tag_output("1.0.0rc1", "1.0.0b2", "1.0.0.dev1")) is None


def test_upgrade_pinned_child_never_raises_the_pin_to_a_pre_release(
    installed_target: Path,
    stub_ls_remote: _RecordingRun,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A pre-release tagged above the latest release is not what a pinned raise
    writes: the pin is raised to the latest release (#1472)."""
    router.pin_file_path(installed_target).write_text("1.0.0\n", encoding="utf-8")
    monkeypatch.setenv(router._LOOP_GUARD_ENV, "1")
    stub_ls_remote.ls_remote_returncode = 0
    stub_ls_remote.ls_remote_stdout = _tag_output("1.0.0", "2.0.0", "2.1.0rc1")
    raised_to: list[str] = []

    def _reconciled(pin: str, _argv: list[str], _environ: object = None) -> int:
        raised_to.append(pin)
        return 0

    monkeypatch.setattr(upgrade, "run_bypassed", _reconciled)

    upgrade.run_upgrade(installed_target)

    assert raised_to == ["2.0.0"]
    assert router.read_version_pin(installed_target) == "2.0.0"


def test_tool_staleness_not_reached_on_source_checkout_run_by_other_code(
    tmp_path: Path,
    stub_ls_remote: _RecordingRun,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """In a source checkout the tool check never runs (ADR-063 point 5). Under the
    checkout's own code the self-host branch returns first (the test below);
    under any other code the refusal to propagate over the source raises first
    (ADR-059; #1070) — no lookup, no tool output.

    The tree is source-shaped by construction (the two markers) while this
    suite's checkout is the running code, so sync's test says no: the gap."""
    (tmp_path / "src" / "project_kit").mkdir(parents=True)
    (tmp_path / "src" / "project_kit" / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / ".pkit" / "cli").mkdir(parents=True)
    (tmp_path / ".pkit" / "cli" / "pkit").write_text("", encoding="utf-8")
    manifest.write_backbone_manifest(tmp_path, manifest.BackboneManifest(backbone_version="0.1.0"))

    with pytest.raises(click.ClickException, match="refusing to run `upgrade`"):
        upgrade.run_upgrade(tmp_path)

    assert stub_ls_remote.ls_remote_calls == []
    assert capsys.readouterr().out == ""


def test_tool_staleness_not_run_on_self_host(
    stub_ls_remote: _RecordingRun,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The self-host short-circuit returns before the check — no ls-remote call."""
    source_repo = install.find_source_kit().parent
    monkeypatch.chdir(source_repo)
    monkeypatch.setattr(upgrade, "run_self_host", lambda *_a, **_k: None)

    upgrade.run_upgrade(source_repo)

    assert stub_ls_remote.ls_remote_calls == []


# --- Per-project version pin: `pkit upgrade` semantics (ADR-049) ----------------


def test_upgrade_pinned_child_auto_advances_to_latest(
    installed_target: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Run as the pinned child (router set PKIT_ROUTED): auto-advance the pin to the
    latest release, reconciling content forward then flipping the pin LAST — no
    `uv tool install`, no manual escape (ADR-049)."""
    router.pin_file_path(installed_target).write_text("1.0.0\n", encoding="utf-8")
    monkeypatch.setenv(router._LOOP_GUARD_ENV, "1")
    monkeypatch.setattr(upgrade, "_latest_released_version", lambda: Version("2.0.0"))

    seen: dict[str, object] = {}

    def _fake_bypassed(pin: str, argv: list[str], environ: object = None) -> int:
        seen["target"] = pin
        seen["argv"] = argv
        # The pin must NOT yet be advanced while the forward reconcile runs.
        seen["pin_during_reconcile"] = router.read_version_pin(installed_target)
        return 0

    monkeypatch.setattr(upgrade, "run_bypassed", _fake_bypassed)

    upgrade.run_upgrade(installed_target)

    assert seen["target"] == "2.0.0"  # reconciled forward under the latest release
    assert seen["argv"] == ["upgrade"]
    assert seen["pin_during_reconcile"] == "1.0.0"  # flipped only after reconcile
    assert router.read_version_pin(installed_target) == "2.0.0"  # flipped last
    out = capsys.readouterr().out
    assert "Raising the pin: 1.0.0 -> 2.0.0" in out
    assert "uv tool install" not in out  # no manual escape any more


def _no_hand_over(monkeypatch: pytest.MonkeyPatch, why: str) -> None:
    """Make any hand-over through the router's bypass fail the test."""

    def _boom(*_a: object, **_k: object) -> int:
        raise AssertionError(why)

    monkeypatch.setattr(upgrade, "run_bypassed", _boom)


def test_upgrade_pinned_child_at_the_latest_release_stays_at_its_pin(
    installed_target: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Pin at the latest release, the project current: nothing to hand over to and
    nothing to finish. No reconcile is bootstrapped and the pin is not touched
    (ADR-065 point 9)."""
    router.pin_file_path(installed_target).write_text(f"{_this_pkit()}\n", encoding="utf-8")
    monkeypatch.setenv(router._LOOP_GUARD_ENV, "1")
    monkeypatch.setattr(upgrade, "_latest_released_version", lambda: Version(_this_pkit()))
    _no_hand_over(monkeypatch, "an at-latest pin must not hand over")

    upgrade.run_upgrade(installed_target)

    out = capsys.readouterr().out
    assert f"Already at the latest pkit release (v{_this_pkit()}); the pin stays." in out
    assert "Already at backbone v" in out
    assert router.read_version_pin(installed_target) == _this_pkit()


def test_upgrade_pinned_child_leaves_pin_when_ahead_of_latest(
    installed_target: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Pin ahead of the newest release → a distinct message; pkit never downgrades
    a pin, so it is left unchanged and no reconcile runs (ADR-049)."""
    router.pin_file_path(installed_target).write_text(f"{_this_pkit()}\n", encoding="utf-8")
    monkeypatch.setenv(router._LOOP_GUARD_ENV, "1")
    monkeypatch.setattr(upgrade, "_latest_released_version", lambda: Version("1.0.0"))
    _no_hand_over(monkeypatch, "a pin ahead of latest must not hand over")

    upgrade.run_upgrade(installed_target)

    out = capsys.readouterr().out
    assert "AHEAD of the latest" in out
    assert router.read_version_pin(installed_target) == _this_pkit()  # unchanged


def test_upgrade_pinned_child_degrades_when_latest_unresolvable(
    installed_target: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Offline / unresolvable latest (None) → say so on stderr, hand over to no
    release and leave the pin unchanged; never brick the command (ADR-049)."""
    router.pin_file_path(installed_target).write_text(f"{_this_pkit()}\n", encoding="utf-8")
    monkeypatch.setenv(router._LOOP_GUARD_ENV, "1")
    monkeypatch.setattr(upgrade, "_latest_released_version", lambda: None)
    _no_hand_over(monkeypatch, "an unresolvable latest must not hand over")

    upgrade.run_upgrade(installed_target)  # must not raise

    err = capsys.readouterr().err
    assert "could not check for the latest pkit release" in err
    assert f"The pin stays at {_this_pkit()}" in err
    assert router.read_version_pin(installed_target) == _this_pkit()  # unchanged


@pytest.mark.parametrize("force", [False, True], ids=["", "force"])
def test_upgrade_pinned_child_dry_run_runs_the_targets_upgrade_with_dry_run(
    installed_target: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    force: bool,
) -> None:
    """A pinned dry run hands over with `--dry-run`, so it lists what the target's
    upgrade would do, and `--force` passes too. The pin is not flipped (ADR-065
    point 9)."""
    router.pin_file_path(installed_target).write_text("1.0.0\n", encoding="utf-8")
    monkeypatch.setenv(router._LOOP_GUARD_ENV, "1")
    monkeypatch.setattr(upgrade, "_latest_released_version", lambda: Version("2.0.0"))
    handed: list[tuple[str, list[str]]] = []
    monkeypatch.setattr(
        upgrade, "run_bypassed", lambda pin, argv, _environ=None: handed.append((pin, argv)) or 0
    )

    upgrade.run_upgrade(installed_target, dry_run=True, force=force)

    flags = ["--dry-run", "--force"] if force else ["--dry-run"]
    assert handed == [("2.0.0", ["upgrade", *flags])]
    assert "would raise pin 1.0.0 -> 2.0.0" in capsys.readouterr().out
    assert router.read_version_pin(installed_target) == "1.0.0"  # unchanged


def test_upgrade_pinned_child_passes_force_to_the_newer_release(
    installed_target: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`pkit upgrade --force` reaches a pinned project's transition through the
    hand-over: the target's upgrade gets `--force`, and the pin flips after it
    (ADR-065 point 9)."""
    router.pin_file_path(installed_target).write_text("1.0.0\n", encoding="utf-8")
    monkeypatch.setenv(router._LOOP_GUARD_ENV, "1")
    monkeypatch.setattr(upgrade, "_latest_released_version", lambda: Version("2.0.0"))
    handed: list[tuple[str, list[str], str | None]] = []

    def _bypassed(pin: str, argv: list[str], _environ: object = None) -> int:
        handed.append((pin, argv, router.read_version_pin(installed_target)))
        return 0

    monkeypatch.setattr(upgrade, "run_bypassed", _bypassed)

    upgrade.run_upgrade(installed_target, force=True)

    assert handed == [("2.0.0", ["upgrade", "--force"], "1.0.0")]
    assert router.read_version_pin(installed_target) == "2.0.0"


def _leave_behind_the_pin(target: Path, state: str) -> None:
    """Leave the project short of its pin, this pkit's version: its content behind
    the pin, or the last transition to the pin incomplete. 1.148.0 opens no
    backbone migration window to this pkit's version."""
    if state == "behind":
        _record_finished_at(target, "1.148.0")
    else:
        manifest.record_completed_version(target, "1.148.0")
    router.pin_file_path(target).write_text(f"{_this_pkit()}\n", encoding="utf-8")


@pytest.mark.parametrize("state", ["behind", "incomplete"])
@pytest.mark.parametrize(
    "latest",
    ["at-latest", "ahead-of-latest", "offline"],
)
def test_a_routed_child_with_no_newer_release_finishes_the_transition_to_its_pin(
    installed_target: Path,
    monkeypatch: pytest.MonkeyPatch,
    state: str,
    latest: str,
) -> None:
    """No newer latest release resolves, and the content is behind the pin or the
    transition to it is incomplete: the routed child runs the transition to its pin
    in its own process. It hands over to nothing, and the pin, already at the
    target, is not written (ADR-065 point 9)."""
    _leave_behind_the_pin(installed_target, state)
    monkeypatch.setenv(router._LOOP_GUARD_ENV, "1")
    found = {
        "at-latest": Version(_this_pkit()),
        "ahead-of-latest": Version("1.0.0"),
        "offline": None,
    }[latest]
    monkeypatch.setattr(upgrade, "_latest_released_version", lambda: found)
    _no_hand_over(monkeypatch, "no newer release resolves, so nothing to hand over to")
    pin_at_copy: list[str | None] = []
    real_propagate = upgrade.propagate

    def spy_propagate(ctx: install.InstallContext, capabilities: Any) -> None:
        pin_at_copy.append(router.read_version_pin(ctx.target_root))
        real_propagate(ctx, capabilities)

    monkeypatch.setattr(upgrade, "propagate", spy_propagate)
    writes = _record_pin_writes(monkeypatch)

    upgrade.run_upgrade(installed_target)

    assert pin_at_copy == [_this_pkit()]
    assert _states(installed_target) == (_this_pkit(), _this_pkit())
    assert writes == []
    assert router.read_version_pin(installed_target) == _this_pkit()


@pytest.mark.parametrize("terminal", [False, True], ids=["no-terminal", "terminal"])
def test_a_pinned_project_whose_installed_pkit_is_its_pin_advances_to_a_newer_release(
    installed_target: Path,
    stub_ls_remote: _RecordingRun,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    terminal: bool,
) -> None:
    """The installed pkit is the pin, so the router runs it in process, with no mark
    of a routed child. Its upgrade checks and advances as the routed child does,
    with or without a terminal, and never updates the tool (ADR-065 point 9,
    ADR-063 point 5)."""
    router.pin_file_path(installed_target).write_text(f"{_this_pkit()}\n", encoding="utf-8")
    stub_ls_remote.ls_remote_returncode = 0
    stub_ls_remote.ls_remote_stdout = _tag_output(_this_pkit(), _NEWER)
    monkeypatch.setattr(upgrade, "_at_a_terminal", lambda: terminal)
    monkeypatch.setattr(upgrade, "_running_is_installed_tool", lambda: True)
    handed: list[tuple[str, list[str]]] = []
    monkeypatch.setattr(
        upgrade, "run_bypassed", lambda pin, argv, _environ=None: handed.append((pin, argv)) or 0
    )

    upgrade.run_upgrade(installed_target)

    assert handed == [(_NEWER, ["upgrade"])]
    assert router.read_version_pin(installed_target) == _NEWER
    assert len(stub_ls_remote.ls_remote_calls) == 1  # its own lookup: no tool step
    assert stub_ls_remote.install_calls == []
    out = capsys.readouterr().out
    assert "Already at backbone" not in out
    assert "pkit tool" not in out


def test_runs_at_its_pin_is_the_routed_child_or_the_installed_pin_never_a_bypass(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The routed child runs at its pin, and so does the installed pkit that is the
    pin. Under `PKIT_NO_ROUTE` the run is the code an operator or a raise asked for
    (ADR-065 point 9)."""
    assert upgrade.runs_at_its_pin(_this_pkit())
    assert not upgrade.runs_at_its_pin("0.1.0")
    monkeypatch.setenv(router._LOOP_GUARD_ENV, "1")
    assert upgrade.runs_at_its_pin("0.1.0")
    monkeypatch.delenv(router._LOOP_GUARD_ENV)
    monkeypatch.setenv(router._BYPASS_ENV, "1")
    assert not upgrade.runs_at_its_pin(_this_pkit())


@pytest.mark.parametrize("latest", ["online", "offline"])
def test_a_routed_child_refuses_content_ahead_of_its_pin_and_names_the_remedy(
    installed_target: Path, monkeypatch: pytest.MonkeyPatch, latest: str
) -> None:
    """A recorded state ahead of the pin, and no newer release to hand over to: the
    older-direction check refuses before the child's own transition writes
    anything. Offline the message names reconnecting, and online #1212's remedies
    (ADR-065 point 9)."""
    _record_content_version(installed_target, _NEWER)
    router.pin_file_path(installed_target).write_text(f"{_this_pkit()}\n", encoding="utf-8")
    monkeypatch.setenv(router._LOOP_GUARD_ENV, "1")
    found = Version(_this_pkit()) if latest == "online" else None
    monkeypatch.setattr(upgrade, "_latest_released_version", lambda: found)
    _no_hand_over(monkeypatch, "no newer release resolves, so nothing to hand over to")
    before = _tree_bytes(installed_target)

    with pytest.raises(click.ClickException) as excinfo:
        upgrade.run_upgrade(installed_target)

    message = excinfo.value.message
    assert f"content ({_NEWER}, in .pkit/manifest.yaml)" in message
    if latest == "offline":
        assert "Reconnect and run `pkit upgrade` again: it then hands over to the latest" in (
            message
        )
        assert "pkit pin" not in message
    else:
        assert f"run `pkit pin {_NEWER}` to pin the project at its content" in message
        assert "Reconnect" not in message
    assert _tree_bytes(installed_target) == before


@pytest.mark.parametrize(
    "flags", [{}, {"dry_run": True}, {"force": True}], ids=["", "dry", "force"]
)
@pytest.mark.parametrize("installed", ["older", "newer"])
def test_upgrade_under_the_routers_fallback_refuses_before_it_writes(
    installed_target: Path,
    stub_ls_remote: _RecordingRun,
    monkeypatch: pytest.MonkeyPatch,
    installed: str,
    flags: dict[str, bool],
) -> None:
    """The router could not fetch the pin and ran the installed pkit: upgrade
    refuses in both directions, before its tool step and before anything is
    written, under `--dry-run` and `--force` too, and never raises the pin to the
    installed version (ADR-065 point 9)."""
    pin = _NEWER if installed == "older" else "0.1.0"
    router.pin_file_path(installed_target).write_text(f"{pin}\n", encoding="utf-8")
    monkeypatch.setenv(router._PIN_UNRESOLVED_ENV, pin)
    _no_hand_over(monkeypatch, "the fallback refuses before any hand-over")
    before = _tree_bytes(installed_target)

    with pytest.raises(click.ClickException) as excinfo:
        upgrade.run_upgrade(installed_target, **flags)

    message = excinfo.value.message
    assert (
        f"refusing to run `pkit upgrade`: this project pins pkit {pin}, which the router "
        f"could not fetch, so this run is pkit {_this_pkit()}, not the pin."
    ) in message
    assert "Reconnect and run `pkit upgrade` again" in message
    assert f"`uvx --from {router.DISTRIBUTION_GIT_URL}@v{pin} project-kit upgrade`" in message
    assert f"`uv tool install --force {router.DISTRIBUTION_HTTPS_URL}@v{pin}`" in message
    assert "`pkit unpin`, then `pkit upgrade`" in message
    assert stub_ls_remote.ls_remote_calls == []
    assert _tree_bytes(installed_target) == before


def test_upgrade_under_the_routers_fallback_names_no_release_for_a_pin_that_is_no_version(
    installed_target: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A pin that is no version is one the router can never fetch: the refusal
    builds no command from it, and names replacing it or moving on purpose."""
    router.pin_file_path(installed_target).write_text("main\n", encoding="utf-8")
    monkeypatch.setenv(router._PIN_UNRESOLVED_ENV, "main")

    with pytest.raises(click.ClickException) as excinfo:
        upgrade.run_upgrade(installed_target)

    message = excinfo.value.message
    assert "The pin, 'main', is no version, so the router can never fetch it." in message
    assert "Replace it with `pkit pin`" in message
    assert "`pkit unpin`, then `pkit upgrade`" in message
    assert "@vmain" not in message
    assert router.read_version_pin(installed_target) == "main"


def test_upgrade_under_a_deliberate_bypass_with_the_fallback_mark_runs(
    installed_target: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`PKIT_NO_ROUTE` marks a run someone asked for, so the fallback mark it
    carries refuses nothing: the upgrade moves the pin to the running version, as
    a raise does (ADR-065 point 9)."""
    router.pin_file_path(installed_target).write_text("0.1.0\n", encoding="utf-8")
    monkeypatch.setenv(router._PIN_UNRESOLVED_ENV, "0.1.0")
    monkeypatch.setenv(router._BYPASS_ENV, "1")

    upgrade.run_upgrade(installed_target)

    assert router.read_version_pin(installed_target) == _this_pkit()


def test_a_routed_child_that_inherited_the_fallback_mark_never_meets_the_refusal(
    installed_target: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The refusal comes after the routed child's checks: a routed child carrying
    the mark from the command that spawned it runs as the pin's code (ADR-065
    point 9)."""
    router.pin_file_path(installed_target).write_text(f"{_this_pkit()}\n", encoding="utf-8")
    monkeypatch.setenv(router._LOOP_GUARD_ENV, "1")
    monkeypatch.setenv(router._PIN_UNRESOLVED_ENV, _this_pkit())
    monkeypatch.setattr(upgrade, "_latest_released_version", lambda: None)

    upgrade.run_upgrade(installed_target)  # must not raise

    assert router.read_version_pin(installed_target) == _this_pkit()


def test_upgrade_skips_tool_staleness_on_bypass_hop(
    installed_target: Path,
    stub_ls_remote: _RecordingRun,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Inside a `run_bypassed`-bootstrapped upgrade (PKIT_NO_ROUTE set), the ADR-063
    tool-staleness probe is suppressed — no second `git ls-remote`, no "tool is
    current" line mid-raise (ADR-049)."""
    monkeypatch.setenv(router._BYPASS_ENV, "1")
    monkeypatch.delenv(router._LOOP_GUARD_ENV, raising=False)

    upgrade.run_upgrade(installed_target)

    assert stub_ls_remote.ls_remote_calls == []  # staleness probe skipped


def test_upgrade_pinned_raise_flips_pin_after_content_sync(
    installed_target: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A pinned project's upgrade raises the pin to the target — and flips it LAST,
    after content sync, so a failed sync would leave the old pin intact (ADR-049)."""
    m = manifest.read_backbone_manifest(installed_target)
    assert m is not None
    source_version = m.backbone_version  # the target the raise moves to
    m.backbone_version = "0.1.0"  # force content behind so upgrade has work
    manifest.write_backbone_manifest(installed_target, m)
    router.pin_file_path(installed_target).write_text("0.1.0\n", encoding="utf-8")
    monkeypatch.delenv(router._LOOP_GUARD_ENV, raising=False)  # not a routed child

    pin_seen_at_sync: list[str | None] = []

    def spy_propagate(ctx: install.InstallContext, _capabilities: object) -> None:
        pin_seen_at_sync.append(router.read_version_pin(ctx.target_root))

    monkeypatch.setattr(upgrade, "propagate", spy_propagate)

    upgrade.run_upgrade(installed_target)

    assert pin_seen_at_sync == ["0.1.0"]  # pin NOT yet flipped when sync ran
    assert router.read_version_pin(installed_target) == source_version  # flipped last
    assert f"pin raised: 0.1.0 -> {source_version}" in capsys.readouterr().out


def test_upgrade_pinned_already_current_still_flips_lagging_pin(
    installed_target: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Content already current but the pin lags (e.g. content synced separately):
    the upgrade still flips the pin forward on the already-at-version path."""
    m = manifest.read_backbone_manifest(installed_target)
    assert m is not None
    source_version = m.backbone_version  # content already current
    router.pin_file_path(installed_target).write_text("0.1.0\n", encoding="utf-8")
    monkeypatch.delenv(router._LOOP_GUARD_ENV, raising=False)

    upgrade.run_upgrade(installed_target)

    out = capsys.readouterr().out
    assert "Already at backbone v" in out
    assert router.read_version_pin(installed_target) == source_version


def test_upgrade_no_pin_writes_no_pin_file(
    installed_target: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With `--no-pin`, an un-pinned project stays un-pinned: plain content sync,
    no pin directive written (ADR-064 point 2 — pinning is the default, so the
    no-pin outcome requires the opt-out)."""
    m = manifest.read_backbone_manifest(installed_target)
    assert m is not None
    m.backbone_version = "0.1.0"
    manifest.write_backbone_manifest(installed_target, m)
    monkeypatch.setattr(upgrade, "propagate", lambda *_a, **_k: None)

    upgrade.run_upgrade(installed_target, pin=False)

    assert not router.pin_file_path(installed_target).exists()


def test_upgrade_dry_run_pinned_does_not_write_pin(
    installed_target: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A dry-run raise reports the flip but writes nothing (ADR-049 + COR-004)."""
    m = manifest.read_backbone_manifest(installed_target)
    assert m is not None
    m.backbone_version = "0.1.0"
    manifest.write_backbone_manifest(installed_target, m)
    router.pin_file_path(installed_target).write_text("0.1.0\n", encoding="utf-8")
    monkeypatch.delenv(router._LOOP_GUARD_ENV, raising=False)

    upgrade.run_upgrade(installed_target, dry_run=True)

    assert router.read_version_pin(installed_target) == "0.1.0"  # unchanged


# --- the upgrade's pin writes go through the pin's one writer (#1211) -----------


def _record_pin_writes(monkeypatch: pytest.MonkeyPatch) -> list[tuple[Path, str | None]]:
    """Stand in for the pin's one writer and record each write the upgrade asks of it."""
    writes: list[tuple[Path, str | None]] = []
    monkeypatch.setattr(upgrade, "write_version_pin", lambda *call: writes.append(call))
    return writes


def test_upgrade_default_pin_writes_through_the_one_pin_writer(
    installed_target: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    writes = _record_pin_writes(monkeypatch)

    upgrade.run_upgrade(installed_target)  # un-pinned: pins by default

    assert writes == [(installed_target, _recorded_version(installed_target))]


def test_upgrade_pin_raise_writes_through_the_one_pin_writer(
    installed_target: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    router.pin_file_path(installed_target).write_text("0.1.0\n", encoding="utf-8")
    monkeypatch.delenv(router._LOOP_GUARD_ENV, raising=False)  # not a routed child
    writes = _record_pin_writes(monkeypatch)

    upgrade.run_upgrade(installed_target)  # pinned behind its content: raises

    assert writes == [(installed_target, _recorded_version(installed_target))]


# --- an older pkit never takes a project back (#1212) ---------------------------

# A version no release reaches: the project's content or pin, ahead of this pkit.
_NEWER = "999.0.0"


def _record_finished_at(target: Path, version: str) -> None:
    """Record *version* as both of the backbone's states: a project a finished
    transition left at *version*."""
    manifest.record_backbone_target(target, version)
    manifest.record_completed_version(target, version)


def _record_content_version(target: Path, version: str) -> None:
    """Record *version* as the project's content version, as a newer pkit's sync would."""
    m = manifest.read_backbone_manifest(target)
    assert m is not None
    m.backbone_version = version
    manifest.write_backbone_manifest(target, m)


def _tree_bytes(root: Path) -> dict[str, bytes | None]:
    """Every path under *root* outside `.git/`, with a file's bytes (None for a
    directory): what a refusal must leave exactly as it was."""
    return {
        path.relative_to(root).as_posix(): path.read_bytes() if path.is_file() else None
        for path in sorted(root.rglob("*"))
        if path.relative_to(root).parts[0] != ".git"
    }


def _this_pkit() -> str:
    return manifest.read_kit_version(install.find_source_kit())


@pytest.mark.parametrize("dry_run", [False, True], ids=["run", "dry-run"])
@pytest.mark.parametrize("pinned", [False, True], ids=["no-pin", "pinned"])
def test_upgrade_refuses_content_newer_than_this_pkit_and_writes_nothing(
    installed_target: Path, monkeypatch: pytest.MonkeyPatch, pinned: bool, dry_run: bool
) -> None:
    """The router's offline fallback runs an older pkit over newer content: upgrade
    refuses before it writes, so the content does not move back, the pin does not
    move down, and an un-pinned project is not pinned at the older version."""
    monkeypatch.delenv(router._LOOP_GUARD_ENV, raising=False)
    _record_content_version(installed_target, _NEWER)
    if pinned:
        router.pin_file_path(installed_target).write_text(f"{_NEWER}\n", encoding="utf-8")
    before = _tree_bytes(installed_target)

    with pytest.raises(click.ClickException) as excinfo:
        upgrade.run_upgrade(installed_target, dry_run=dry_run)

    message = excinfo.value.message
    assert f"refusing to run `pkit upgrade`: this pkit is {_this_pkit()}" in message
    assert f"content ({_NEWER}, in .pkit/manifest.yaml)" in message
    assert f"{router.DISTRIBUTION_GIT_URL}@v{_NEWER} project-kit upgrade" in message
    assert _tree_bytes(installed_target) == before


def test_upgrade_refuses_to_move_a_newer_pin_down(
    installed_target: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Content at this pkit's version, pin ahead of it: the already-at-version path
    would otherwise rewrite the pin down to this pkit's version."""
    monkeypatch.delenv(router._LOOP_GUARD_ENV, raising=False)
    router.pin_file_path(installed_target).write_text(f"{_NEWER}\n", encoding="utf-8")
    before = _tree_bytes(installed_target)

    with pytest.raises(click.ClickException) as excinfo:
        upgrade.run_upgrade(installed_target)

    assert f"pin ({_NEWER}, in .pkit/version-pin)" in excinfo.value.message
    assert router.read_version_pin(installed_target) == _NEWER
    assert _tree_bytes(installed_target) == before


@pytest.mark.parametrize("content", ["equal", "older"])
def test_upgrade_at_or_ahead_of_the_content_is_unchanged(
    installed_target: Path, monkeypatch: pytest.MonkeyPatch, content: str
) -> None:
    """This pkit at the project's version, or newer: upgrade runs as before and
    leaves content and pin at this pkit's version."""
    monkeypatch.delenv(router._LOOP_GUARD_ENV, raising=False)
    recorded = _this_pkit() if content == "equal" else "0.1.0"
    _record_content_version(installed_target, recorded)
    router.pin_file_path(installed_target).write_text(f"{recorded}\n", encoding="utf-8")

    upgrade.run_upgrade(installed_target)  # must not raise

    assert _recorded_version(installed_target) == _this_pkit()
    assert router.read_version_pin(installed_target) == _this_pkit()


def test_upgrade_as_the_pinned_child_still_raises_a_pin_behind_its_content(
    installed_target: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The pinned child runs the pin's own code, and its auto-advance is how a
    content-ahead-of-pin state recovers (ADR-049): the refusal comes after it."""
    _record_content_version(installed_target, _NEWER)
    router.pin_file_path(installed_target).write_text(f"{_this_pkit()}\n", encoding="utf-8")
    monkeypatch.setenv(router._LOOP_GUARD_ENV, "1")
    monkeypatch.setattr(upgrade, "_latest_released_version", lambda: Version(_NEWER))
    raised_to: list[str] = []

    def _reconciled(pin: str, _argv: list[str], _environ: object = None) -> int:
        raised_to.append(pin)
        return 0

    monkeypatch.setattr(upgrade, "run_bypassed", _reconciled)

    upgrade.run_upgrade(installed_target)  # must not raise

    assert raised_to == [_NEWER]
    assert router.read_version_pin(installed_target) == _NEWER


# --- the remedy sync's refusal names runs the migrations (#1452) -----------------


def test_upgrade_across_a_backbone_migration_directory_runs_it_and_records_the_version(
    installed_target: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`pkit upgrade` is the remedy the sync command's refusal names, and that
    refusal is not on upgrade's path: from 1.149.0 under a 1.150.0 pkit, upgrade
    runs both `1.150.0/` migrations and records 1.150.0."""
    from click.testing import CliRunner

    from project_kit.cli import main

    monkeypatch.delenv(router._LOOP_GUARD_ENV, raising=False)
    source = _real_source_copy(tmp_path)
    (source / "VERSION").write_text("1.150.0\n", encoding="utf-8")
    # The release that ships 1.150.0 broadens each range to admit it. The copy
    # admits it the same way, so compatibility does not stop the upgrade.
    for package_yaml in source.glob("*/*/package.yaml"):
        text = package_yaml.read_text(encoding="utf-8")
        admitted = re.sub(
            r"^requires_backbone: .*$", 'requires_backbone: ">=0.1.0,<2.0.0"', text, flags=re.M
        )
        package_yaml.write_text(admitted, encoding="utf-8")
    monkeypatch.setattr(upgrade, "find_source_kit", lambda: source)
    monkeypatch.setattr(install, "find_source_kit", lambda: source)
    _record_content_version(installed_target, "1.149.0")
    # A journal the project kept, so `keep-process-journal-logging` keeps logging on.
    process_dir = installed_target / ".pkit" / "capabilities" / "kept" / "project" / "process"
    process_dir.mkdir(parents=True)
    (process_dir / "subject.journal.jsonl").write_text("{}\n", encoding="utf-8")

    result = CliRunner().invoke(main, ["upgrade", "--no-self-update", "--no-pin"])

    assert result.exit_code == 0, result.output
    assert "running 2 backbone migration(s) (1.149.0 -> v1.150.0)" in result.output
    assert "1.150.0/001-keep-process-journal-logging.sh" in result.output
    assert "1.150.0/001-untrack-runtime-ignored-files.sh" in result.output
    assert _recorded_version(installed_target) == "1.150.0"
    # What `keep-process-journal-logging` writes, and nothing else does.
    config = (installed_target / ".pkit" / "project" / "config.yaml").read_text(encoding="utf-8")
    assert "Recorded by\n# the 1.150.0 upgrade" in config
    assert "    enabled: true" in config


@pytest.mark.parametrize("stdin", [None, "closed"])
def test_self_update_not_allowed_without_a_usable_stdin(monkeypatch, stdin) -> None:
    """An absent or closed stdin is non-interactive, not a crash (#913)."""
    import io

    monkeypatch.delenv(upgrade._SELF_UPDATED_ENV, raising=False)
    if stdin == "closed":
        stream = io.StringIO()
        stream.close()
        monkeypatch.setattr(upgrade.sys, "stdin", stream)
    else:
        monkeypatch.setattr(upgrade.sys, "stdin", None)
    assert upgrade._self_update_allowed() is False


# --- the target recorded first, the completion last (#1459, ADR-065) -------------


def _states(target: Path) -> tuple[str, str | None]:
    """The backbone's two recorded states: the target and the completion."""
    m = manifest.read_backbone_manifest(target)
    assert m is not None
    return m.backbone_version, m.completed_version


def _drop_completion(target: Path) -> None:
    """Take the `completed_version` line out, as every manifest before #1459 is."""
    path = target / ".pkit" / "manifest.yaml"
    text = path.read_text(encoding="utf-8")
    path.write_text(re.sub(r"(?m)^completed_version:.*\n", "", text), encoding="utf-8")


def _use_source(monkeypatch: pytest.MonkeyPatch, source: Path) -> None:
    monkeypatch.setattr(upgrade, "find_source_kit", lambda: source)
    monkeypatch.setattr(install, "find_source_kit", lambda: source)


def _tracing(trace: Path, label: str, *, unless_missing: Path | None = None) -> str:
    """A migration script that appends *label* to *trace*, and fails with status 3
    while *unless_missing* does not exist."""
    body = f'#!/usr/bin/env bash\necho "{label}" >> "{trace}"\n'
    if unless_missing is not None:
        body += f'[ -e "{unless_missing}" ] || exit 3\n'
    return body


def test_init_records_both_states_equal(installed_target: Path) -> None:
    assert _states(installed_target) == (_this_pkit(), _this_pkit())


def test_an_upgrade_interrupted_in_its_migrations_is_finished_by_the_next(
    installed_target: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The first upgrade records its target, then stops on a failing migration: the
    completion stays behind and no pin is written. The next upgrade runs the
    backbone window again from the completion, and records it last (ADR-065 points
    3 and 4)."""
    _record_finished_at(installed_target, "0.1.0")
    source = _real_source_copy(tmp_path)
    _use_source(monkeypatch, source)
    trace, fixed = tmp_path / "trace.txt", tmp_path / "fixed"
    _stage_backbone_migration(source, "0.2.0", "001-first.sh", _tracing(trace, "0.2.0"))
    _stage_backbone_migration(
        source, "0.3.0", "001-flaky.sh", _tracing(trace, "0.3.0", unless_missing=fixed)
    )

    with pytest.raises(click.ClickException, match="exited with status 3"):
        upgrade.run_upgrade(installed_target)

    target = _this_pkit()
    assert _states(installed_target) == (target, "0.1.0")
    assert router.read_version_pin(installed_target) is None
    capsys.readouterr()

    fixed.touch()
    upgrade.run_upgrade(installed_target)

    out = capsys.readouterr().out
    assert "The last transition is incomplete: completed_version is 0.1.0" in out
    assert _states(installed_target) == (target, target)
    assert trace.read_text(encoding="utf-8").split() == ["0.2.0", "0.3.0", "0.2.0", "0.3.0"]
    assert router.read_version_pin(installed_target) == target


def test_the_target_is_recorded_before_propagation_and_the_completion_before_the_pin(
    installed_target: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Merge and deploy, the workspace and provisioning all run while the target is
    recorded and the completion is not; the completion comes after them, and the
    pin after it (ADR-065 point 4)."""
    _record_finished_at(installed_target, "0.1.0")
    events: list[tuple[str, tuple[str, str | None]]] = []

    def spy(name: str, real: Any, root_of: Any) -> Any:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            events.append((name, _states(root_of(*args))))
            return real(*args, **kwargs)

        return wrapper

    first = lambda root, *_a, **_k: root  # noqa: E731
    of_ctx = lambda ctx, *_a, **_k: ctx.target_root  # noqa: E731
    monkeypatch.setattr(
        upgrade, "record_backbone_target", spy("target", upgrade.record_backbone_target, first)
    )
    monkeypatch.setattr(upgrade, "propagate", spy("propagation", upgrade.propagate, of_ctx))
    monkeypatch.setattr(
        install,
        "run_installed_adapter_primitives",
        spy("merge and deploy", install.run_installed_adapter_primitives, of_ctx),
    )
    monkeypatch.setattr(
        install, "ensure_agent_workspace", spy("workspace", install.ensure_agent_workspace, of_ctx)
    )
    monkeypatch.setattr(
        install,
        "provision_query_commands",
        spy("provisioning", install.provision_query_commands, of_ctx),
    )
    monkeypatch.setattr(
        upgrade,
        "record_completed_version",
        spy("completion", upgrade.record_completed_version, first),
    )
    monkeypatch.setattr(upgrade, "freeze_pin", spy("pin", upgrade.freeze_pin, first))

    upgrade.run_upgrade(installed_target)

    target = _this_pkit()
    assert events == [
        ("target", ("0.1.0", "0.1.0")),
        ("propagation", (target, "0.1.0")),
        ("merge and deploy", (target, "0.1.0")),
        ("workspace", (target, "0.1.0")),
        ("provisioning", (target, "0.1.0")),
        ("completion", (target, "0.1.0")),
        ("pin", (target, target)),
    ]


def test_a_missing_completion_replays_every_backbone_migration_once(
    installed_target: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The project is at its target, but no completion is recorded: its history is
    unknown, so every backbone migration up to the target runs, and the report
    names the replay. Once the completion is recorded, the next upgrade has
    nothing to do (ADR-065 point 5)."""
    source = _real_source_copy(tmp_path)
    _use_source(monkeypatch, source)
    trace = tmp_path / "trace.txt"
    _stage_backbone_migration(source, "0.2.0", "001-old.sh", _tracing(trace, "0.2.0"))
    _drop_completion(installed_target)

    upgrade.run_upgrade(installed_target, pin=False)

    out = capsys.readouterr().out
    assert "No completed transition is recorded" in out
    assert "backbone migration(s), the replay (no completed transition -> v" in out
    assert "0.2.0/001-old.sh" in out
    assert "1.31.0/001-retire-pm-core-agents.sh" in out
    assert trace.read_text(encoding="utf-8").split() == ["0.2.0"]
    assert _states(installed_target) == (_this_pkit(), _this_pkit())

    upgrade.run_upgrade(installed_target, pin=False)

    assert "Already at backbone v" in capsys.readouterr().out
    assert trace.read_text(encoding="utf-8").split() == ["0.2.0"]


def test_the_dry_run_lists_the_replay_and_writes_nothing(
    installed_target: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A dry run copies nothing, so it lists the scripts of the running pkit's
    bundle, which the propagation would bring (ADR-065 point 5)."""
    source = _real_source_copy(tmp_path)
    _use_source(monkeypatch, source)
    trace = tmp_path / "trace.txt"
    _stage_backbone_migration(source, "0.2.0", "001-old.sh", _tracing(trace, "0.2.0"))
    _drop_completion(installed_target)
    before = _tree_bytes(installed_target)

    upgrade.run_upgrade(installed_target, dry_run=True)

    out = capsys.readouterr().out
    assert "No completed transition is recorded" in out
    assert "would run" in out and "migration(s) for backbone, the replay" in out
    assert "0.2.0/001-old.sh" in out
    assert "would record .pkit/manifest.yaml completed_version" in out
    assert not trace.exists()
    assert _tree_bytes(installed_target) == before


def test_a_completion_ahead_of_the_target_reads_as_incomplete(
    installed_target: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """An older pkit synced over a finished transition: the completion is ahead of
    `backbone_version`. The next upgrade propagates again, runs the window from the
    completion, and records both states (ADR-065 point 3)."""
    target = _this_pkit()
    _record_content_version(installed_target, "0.1.0")
    assert _states(installed_target) == ("0.1.0", target)

    upgrade.run_upgrade(installed_target, pin=False)

    out = capsys.readouterr().out
    assert "Already at backbone" not in out
    assert f"no backbone migrations to run between {target} and {target}" in out
    assert _states(installed_target) == (target, target)


def test_a_registered_adapter_with_no_record_is_recorded_and_runs_no_migration(
    installed_target: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Every project's adapter has no manifest before #1459: it reads as at the
    backbone, so the first transition records it at its bundled version and runs
    none of its migrations (ADR-065 point 2)."""
    adapter = installed_target / ".pkit" / "adapters" / "claude-code"
    (adapter / "project" / "manifest.yaml").unlink()
    trace = tmp_path / "adapter-trace.txt"
    scripts = adapter / "migrations" / "0.1.0"
    scripts.mkdir(parents=True)
    (scripts / "001-trace.sh").write_text(_tracing(trace, "adapter"), encoding="utf-8")
    bundled = manifest.read_component_package(
        install.find_source_kit() / "adapters" / "claude-code" / "package.yaml"
    )
    assert bundled is not None

    upgrade.run_upgrade(installed_target, pin=False)

    assert "no record before: it reads as at the backbone" in capsys.readouterr().out
    assert not trace.exists()
    recorded = manifest.read_component_manifest(adapter / "project" / "manifest.yaml")
    assert recorded is not None and recorded.version == bundled[0]

    upgrade.run_upgrade(installed_target, pin=False)

    assert "Already at backbone v" in capsys.readouterr().out


def test_the_early_return_needs_both_states_and_every_component_at_the_target(
    installed_target: Path,
) -> None:
    """Upgrade returns early only when both keys name the target and every registered
    adapter and shipped capability records its bundled version (ADR-065 point 2)."""
    source = install.find_source_kit()
    target = _this_pkit()

    def current() -> bool:
        state = manifest.read_backbone_manifest(installed_target)
        assert state is not None
        return upgrade.is_current(installed_target, source, state, target)

    assert current()

    _drop_completion(installed_target)
    assert not current()
    manifest.record_completed_version(installed_target, target)
    assert current()

    record = installed_target / ".pkit" / "adapters" / "claude-code" / "project" / "manifest.yaml"
    kept = record.read_bytes()
    record.unlink()
    assert not current()
    record.write_bytes(kept)
    assert current()

    # A shipped capability recorded at another version than its bundle's moves.
    _stage_installed_capability(installed_target, "evidence", version="0.1.0")
    state = manifest.read_backbone_manifest(installed_target)
    assert state is not None
    assert [
        (m.kind, m.name, m.recorded)
        for m in upgrade.component_moves(installed_target, source, state)
    ] == [("capability", "evidence", "0.1.0")]
    assert not current()
    # One the bundle does not ship keeps its own course, and moves nothing.
    _stage_installed_capability(installed_target, "evidence", version="0.1.0")
    _stage_installed_capability(installed_target, "homegrown", version="0.1.0")
    state = manifest.read_backbone_manifest(installed_target)
    assert state is not None
    assert "homegrown" not in [
        m.name for m in upgrade.component_moves(installed_target, source, state)
    ]


def test_a_record_newer_than_the_bundle_refuses_the_transition(
    installed_target: Path,
) -> None:
    """A transition never moves a recorded state down (ADR-065 point 7): an adapter
    recorded ahead of the bundle refuses the transition in its step 1, before it
    writes anything, with no override. It is not at its bundled version, so the
    early return does not apply (point 2), and the move is listed as ahead."""
    record = installed_target / ".pkit" / "adapters" / "claude-code" / "project" / "manifest.yaml"
    record.write_text(
        re.sub(r"(?m)^  version: .*$", "  version: 99.0.0", record.read_text(encoding="utf-8")),
        encoding="utf-8",
    )
    _drop_completion(installed_target)
    before = _tree_bytes(installed_target)
    source = install.find_source_kit()
    bundled = manifest.read_component_package(source / "adapters" / "claude-code" / "package.yaml")
    assert bundled is not None

    with pytest.raises(click.ClickException) as excinfo:
        upgrade.run_upgrade(installed_target, pin=False, force=True)

    message = excinfo.value.message
    assert (
        f"this pkit's bundle ships adapter 'claude-code' at {bundled[0]}, older than the "
        "99.0.0 this project records"
    ) in message
    assert "no flag overrides this refusal" in message
    assert "a pkit whose bundle ships adapter 'claude-code' at 99.0.0 or newer" in message
    assert _tree_bytes(installed_target) == before
    state = manifest.read_backbone_manifest(installed_target)
    assert state is not None
    moves = upgrade.component_moves(installed_target, source, state)
    assert [(m.name, m.recorded, m.ahead) for m in moves] == [("claude-code", "99.0.0", True)]
    assert not upgrade.is_current(installed_target, source, state, _this_pkit())


def test_a_record_of_the_bundled_version_written_another_way_is_current(
    installed_target: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`v0.6.0` names the version `0.6.0` does: the adapter is at its bundled version,
    so the early return applies and nothing is moved or kept."""
    record = installed_target / ".pkit" / "adapters" / "claude-code" / "project" / "manifest.yaml"
    text = record.read_text(encoding="utf-8")
    record.write_text(re.sub(r"(?m)^  version: (.*)$", r"  version: v\1", text), encoding="utf-8")
    state = manifest.read_backbone_manifest(installed_target)
    assert state is not None
    source = install.find_source_kit()
    assert upgrade.component_moves(installed_target, source, state) == []

    upgrade.run_upgrade(installed_target, pin=False)

    assert "Already at backbone v" in capsys.readouterr().out


def test_an_adapter_registered_after_the_copy_is_rendered_into_the_ignore_file(
    installed_target: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The render after propagation reads the registry, so an adapter the transition
    registers there is rendered again (ADR-065 point 4, step 3)."""
    from project_kit import visibility

    events: list[str] = []
    real_render = visibility.render_runtime_ignore

    def render(*args: Any, **kwargs: Any) -> str:
        events.append("render")
        return real_render(*args, **kwargs)

    def register(_root: Path) -> list[str]:
        events.append("register")
        return ["harness"]

    monkeypatch.setattr(visibility, "render_runtime_ignore", render)
    monkeypatch.setattr(upgrade, "register_adapters", register)
    _drop_completion(installed_target)

    upgrade.run_upgrade(installed_target, pin=False)

    # Registered, then rendered after propagation, and rendered again with the
    # derivable state.
    assert events == ["register", "render", "render"]


@pytest.mark.parametrize(
    "state",
    ["no manifest", "no version", "no version, completion kept", "empty", "empty completion"],
)
def test_upgrade_writes_a_missing_or_corrupt_manifest_at_its_target_and_replays(
    installed_target: Path, capsys: pytest.CaptureFixture[str], state: str
) -> None:
    """No manifest, a `backbone_version` that is no version or empty, or an empty
    completion: upgrade writes the manifest at its target, as first install does,
    registers the adapters, and replays every backbone migration once (ADR-065
    points 2 and 5). Each line it writes keeps the manifest YAML."""
    path = installed_target / ".pkit" / "manifest.yaml"
    text = path.read_text(encoding="utf-8")
    if state == "no manifest":
        path.unlink()
    elif state == "no version":
        _drop_completion(installed_target)
        manifest.record_backbone_target(installed_target, "not-a-version")
    elif state == "no version, completion kept":
        manifest.record_backbone_target(installed_target, "not-a-version")
    elif state == "empty":
        path.write_text(
            re.sub(
                r"(?m)^completed_version:.*\n",
                "",
                re.sub(r"(?m)^backbone_version:.*$", "backbone_version:", text),
            ),
            encoding="utf-8",
        )
    else:
        path.write_text(
            re.sub(r"(?m)^completed_version:.*$", "completed_version:", text), encoding="utf-8"
        )

    upgrade.run_upgrade(installed_target, pin=False)

    out = capsys.readouterr().out
    if state == "no manifest":
        assert "Upgrading backbone: no .pkit/manifest.yaml ->" in out
        assert "registered   adapter 'claude-code'" in out
    elif state.startswith("no version"):
        assert "'not-a-version', which is no version" in out
    if state == "no version, completion kept":
        assert "The recorded states cannot be read" in out
    else:
        assert "No completed transition is recorded" in out
    assert "backbone migration(s), the replay" in out
    assert _states(installed_target) == (_this_pkit(), _this_pkit())
    written = manifest.read_backbone_manifest(installed_target)
    assert written is not None
    assert [(c.kind, c.name) for c in written.components] == [("adapter", "claude-code")]


def test_the_older_direction_check_reads_the_completion_too(
    installed_target: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Upgrade compares the running pkit with the newest of both states and the pin
    (ADR-065 point 7): a completion ahead of this pkit refuses, writing nothing."""
    monkeypatch.delenv(router._LOOP_GUARD_ENV, raising=False)
    manifest.record_completed_version(installed_target, _NEWER)
    before = _tree_bytes(installed_target)

    with pytest.raises(click.ClickException) as excinfo:
        upgrade.run_upgrade(installed_target)

    assert f"content ({_NEWER}, in .pkit/manifest.yaml)" in excinfo.value.message
    assert _tree_bytes(installed_target) == before


def test_a_corrupt_recorded_version_names_upgrade_for_pin() -> None:
    with pytest.raises(click.ClickException, match="Run 'pkit upgrade'"):
        upgrade._pin_order("1.0.0", "not-a-version")


# --- the propagation step, and each capability after its copy (#1460, ADR-065) ---


def _stage_trial(source_kit: Path, version: str, *, skill: str = "# Skill\n") -> Path:
    """The capability `trial` at *version* under *source_kit*'s `capabilities/`."""
    cap = source_kit / "capabilities" / "trial"
    (cap / "skills").mkdir(parents=True, exist_ok=True)
    (cap / "package.yaml").write_text(
        "schema_version: 1\ncomponent:\n  kind: capability\n  name: trial\n"
        f'  version: {version}\ndescription: Test.\nrequires_backbone: ">=0.0.0"\n',
        encoding="utf-8",
    )
    (cap / "skills" / "trial-skill.md").write_text(
        f"---\nname: trial-skill\n---\n{skill}", encoding="utf-8"
    )
    return cap


def _install_trial(
    target: Path, tmp_path: Path, version: str, *, skipped: tuple[tuple[str, str], ...] = ()
) -> Path:
    """Install `trial` at *version* into *target*; returns its installed folder."""
    from project_kit import capabilities as caps

    install_source = tmp_path / "install-source" / ".pkit"
    _stage_trial(install_source, version)
    source = caps.find_capability_in_source(install_source, "trial")
    assert source is not None
    caps.install_capability(target, source, skipped_artifacts=skipped)
    return target / ".pkit" / "capabilities" / "trial"


def _trial_record(target: Path) -> manifest.ComponentManifest | None:
    return manifest.read_component_manifest(
        target / ".pkit" / "capabilities" / "trial" / "project" / "manifest.yaml"
    )


def test_an_upgrade_to_a_newer_release_runs_the_step_and_never_meets_syncs_guard(
    installed_target: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An upgrade runs where the running pkit is newer than the project by design: it
    calls the propagation step, never the sync command, so sync's guard never
    stops it (ADR-065 point 1)."""
    from project_kit import sync

    _record_finished_at(installed_target, "0.1.0")
    steps: list[Path] = []
    real_step = upgrade.propagate

    def step(ctx: install.InstallContext, capabilities: Any) -> None:
        steps.append(ctx.target_root)
        real_step(ctx, capabilities)

    def guard(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("an upgrade ran sync's guard")

    monkeypatch.setattr(upgrade, "propagate", step)
    monkeypatch.setattr(sync, "refuse_version_mismatch", guard)

    upgrade.run_upgrade(installed_target, pin=False)

    assert steps == [installed_target]
    assert _states(installed_target) == (_this_pkit(), _this_pkit())


def test_upgrade_runs_a_capability_migration_after_its_copy_and_restamps_it(
    installed_target: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Each capability's migrations run after its copy, so a migration reads the
    files of the version it migrates to (COR-010's order), and the capability is
    restamped when they finish."""
    _install_trial(installed_target, tmp_path, "0.1.0")
    source = _real_source_copy(tmp_path)
    _use_source(monkeypatch, source)
    cap = _stage_trial(source, "0.2.0", skill="# New\n")
    trace = tmp_path / "trace.txt"
    script = cap / "migrations" / "0.2.0" / "001-read-the-copy.sh"
    script.parent.mkdir(parents=True)
    script.write_text(
        "#!/usr/bin/env bash\nset -euo pipefail\n"
        'if grep -q "# New" "$ROOT/.pkit/capabilities/trial/skills/trial-skill.md"; then\n'
        f'  echo after >> "{trace}"\nelse\n  echo before >> "{trace}"\nfi\n',
        encoding="utf-8",
    )
    _record_finished_at(installed_target, "0.1.0")

    upgrade.run_upgrade(installed_target, pin=False)

    assert trace.read_text(encoding="utf-8").split() == ["after"]
    record = _trial_record(installed_target)
    assert record is not None and record.version == "0.2.0"


def test_upgrade_moves_a_root_record_under_project_before_its_copy(
    installed_target: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A record an older release left at the root keeps the project from reading as
    current. The transition moves it under project/ before its copy, which would
    prune it there, keeping its state and skips (ADR-065 point 2)."""
    installed = _install_trial(
        installed_target, tmp_path, "0.1.0", skipped=(("skill", "trial-skill"),)
    )
    root = installed / "manifest.yaml"
    (installed / "project" / "manifest.yaml").rename(root)
    with root.open("a", encoding="utf-8") as f:
        f.write("  project_board:\n    uuid: PVT_kwDOAA12345\n")
    manifest.set_component_manifest_path(
        installed_target, "capability", "trial", ".pkit/capabilities/trial/manifest.yaml"
    )
    source = _real_source_copy(tmp_path)
    _use_source(monkeypatch, source)
    _stage_trial(source, "0.1.0")

    upgrade.run_upgrade(installed_target, pin=False)

    assert "Already at backbone" not in capsys.readouterr().out
    assert not root.exists()
    record = _trial_record(installed_target)
    assert record is not None
    assert record.version == "0.1.0"
    assert record.backend_state == {
        "skipped": [{"kind": "skill", "name": "trial-skill"}],
        "project_board": {"uuid": "PVT_kwDOAA12345"},
    }
    assert not (installed / "skills" / "trial-skill.md").exists()
    backbone = manifest.read_backbone_manifest(installed_target)
    assert backbone is not None
    assert {c.name: c.manifest for c in backbone.components}["trial"] == (
        ".pkit/capabilities/trial/project/manifest.yaml"
    )


def test_upgrade_records_a_capability_with_no_readable_version_and_runs_none_of_its_migrations(
    installed_target: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Neither a manifest nor a readable package.yaml: the transition copies the
    capability, records the version its bundle ships, and runs none of its
    migrations, since its history is unknown (ADR-065 point 2)."""
    installed = _install_trial(installed_target, tmp_path, "0.1.0")
    (installed / "project" / "manifest.yaml").unlink()
    (installed / "package.yaml").write_text("not: a package\n", encoding="utf-8")
    source = _real_source_copy(tmp_path)
    _use_source(monkeypatch, source)
    cap = _stage_trial(source, "0.2.0")
    script = cap / "migrations" / "0.1.0" / "001-mark.sh"
    script.parent.mkdir(parents=True)
    script.write_text('#!/usr/bin/env bash\ntouch "$ROOT/migrated"\n', encoding="utf-8")

    upgrade.run_upgrade(installed_target, pin=False)

    assert not (installed_target / "migrated").exists()
    record = _trial_record(installed_target)
    assert record is not None and record.version == "0.2.0"
    assert "no recorded version before, so none of its migrations runs" in capsys.readouterr().out


def test_upgrade_moves_the_root_record_of_a_capability_no_longer_shipped(
    installed_target: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The transition moves every root manifest (ADR-065 point 2), that of a
    capability its bundle no longer ships included, so the next upgrade reads the
    project as current. The capability itself stays installed (COR-017)."""
    installed = _install_trial(installed_target, tmp_path, "0.1.0")
    root = installed / "manifest.yaml"
    (installed / "project" / "manifest.yaml").rename(root)
    manifest.set_component_manifest_path(
        installed_target, "capability", "trial", ".pkit/capabilities/trial/manifest.yaml"
    )

    upgrade.run_upgrade(installed_target, pin=False)
    first = capsys.readouterr().out
    upgrade.run_upgrade(installed_target, pin=False)
    second = capsys.readouterr().out

    assert "Already at backbone" not in first
    assert "orphan       'trial'" in first
    assert not root.exists()
    record = _trial_record(installed_target)
    assert record is not None and record.version == "0.1.0"
    assert "Already at backbone" in second


def test_upgrade_refuses_a_capability_its_bundle_ships_older(
    installed_target: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A transition never moves a recorded version down: a capability its bundle
    ships older refuses the transition before it writes anything, `--force`
    included, naming both versions (ADR-065 point 7)."""
    _install_trial(installed_target, tmp_path, "0.3.0")
    source = _real_source_copy(tmp_path)
    _use_source(monkeypatch, source)
    _stage_trial(source, "0.1.0", skill="# Older\n")
    _record_finished_at(installed_target, "0.1.0")
    before = _tree_bytes(installed_target)

    for dry_run in (True, False):
        with pytest.raises(click.ClickException) as excinfo:
            upgrade.run_upgrade(installed_target, pin=False, dry_run=dry_run, force=True)

        assert (
            "this pkit's bundle ships capability 'trial' at 0.1.0, older than the 0.3.0 this "
            "project records"
        ) in excinfo.value.message
        assert _tree_bytes(installed_target) == before


def test_upgrade_creates_each_missing_seed_path_and_never_writes_over_one(
    installed_target: Path,
) -> None:
    """A transition creates each declared seed path that is missing, and leaves one
    that exists as the project wrote it (ADR-065 point 11, COR-059 point 8)."""
    pkit = installed_target / ".pkit"
    overlay = pkit / "agents" / "project" / "overlay.yaml"
    overlay.unlink()
    shutil.rmtree(pkit / "decisions" / "project")
    shutil.rmtree(pkit / "scratchpad" / "active")
    settings = pkit / "adapters" / "claude-code" / "settings" / "project" / "settings.json"
    custom = '{"permissions": {"allow": ["Bash(echo:*)"], "deny": []}}'
    settings.write_text(custom, encoding="utf-8")
    _record_finished_at(installed_target, "0.1.0")

    upgrade.run_upgrade(installed_target, pin=False)

    assert overlay.read_text(encoding="utf-8") == install.AGENTS_OVERLAY_SEED
    assert (pkit / "decisions" / "project" / ".gitkeep").is_file()
    assert (pkit / "scratchpad" / "active" / ".gitkeep").is_file()
    assert settings.read_text(encoding="utf-8") == custom


def test_upgrade_dry_run_lists_each_capability_migration_and_writes_nothing(
    installed_target: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The dry run reads a capability's migrations from the bundle, lists them, and
    writes nothing."""
    _install_trial(installed_target, tmp_path, "0.1.0")
    source = _real_source_copy(tmp_path)
    _use_source(monkeypatch, source)
    cap = _stage_trial(source, "0.2.0")
    script = cap / "migrations" / "0.2.0" / "001-mark.sh"
    script.parent.mkdir(parents=True)
    script.write_text('#!/usr/bin/env bash\ntouch "$ROOT/migrated"\n', encoding="utf-8")
    _record_finished_at(installed_target, "0.1.0")
    before = _tree_bytes(installed_target)

    upgrade.run_upgrade(installed_target, dry_run=True)

    out = capsys.readouterr().out
    assert "would run 1 migration(s) for capability 'trial' (0.1.0 -> v0.2.0)" in out
    assert "would record capability 'trial' at 0.2.0 (from 0.1.0)" in " ".join(out.split())
    assert _tree_bytes(installed_target) == before


# --- every migration in COR-010's order, and the collisions and gates (#1461) ----


def _bump_bundled_adapter(source_kit: Path, version: str) -> Path:
    """The bundle's claude-code adapter at *version*; returns its folder."""
    adapter = source_kit / "adapters" / "claude-code"
    package = adapter / "package.yaml"
    text = package.read_text(encoding="utf-8")
    package.write_text(re.sub(r"(?m)^  version: .*$", f"  version: {version}", text), "utf-8")
    return adapter


def _stage_script(component: Path, version: str, body: str, name: str = "001-trace.sh") -> Path:
    """A migration script under *component*'s `migrations/<version>/`."""
    script = component / "migrations" / version / name
    script.parent.mkdir(parents=True, exist_ok=True)
    script.write_text(body, encoding="utf-8")
    script.chmod(0o755)
    return script


def _note(trace: Path, label: str) -> None:
    with trace.open("a", encoding="utf-8") as handle:
        handle.write(f"{label}\n")


def _lines(trace: Path) -> list[str]:
    return trace.read_text(encoding="utf-8").splitlines()


def test_an_upgrade_runs_every_step_in_cor_010s_order(
    installed_target: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Propagation and the ignore render, then the backbone's, the adapters' and the
    capabilities' migrations, then the seed paths, merge, deploy, the render again,
    the workspace and provisioning, the completion and the pin (ADR-065 point 4)."""
    from project_kit import visibility

    _install_trial(installed_target, tmp_path, "0.1.0")
    source = _real_source_copy(tmp_path)
    _use_source(monkeypatch, source)
    trace = tmp_path / "trace.txt"
    _stage_backbone_migration(source, "0.2.0", "001-trace.sh", _tracing(trace, "backbone"))
    _stage_script(_bump_bundled_adapter(source, "0.7.0"), "0.7.0", _tracing(trace, "adapter"))
    _stage_script(_stage_trial(source, "0.2.0"), "0.2.0", _tracing(trace, "capability"))
    _record_finished_at(installed_target, "0.1.0")

    def spy(label: str, real: Any) -> Any:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            _note(trace, label)
            return real(*args, **kwargs)

        return wrapper

    for module, name, label in [
        (upgrade, "record_backbone_target", "target"),
        (upgrade, "propagate", "propagation"),
        (visibility, "render_runtime_ignore", "render"),
        (upgrade, "seed_missing_paths", "seed paths"),
        (install, "run_installed_adapter_primitives", "merge and deploy"),
        (install, "ensure_agent_workspace", "workspace"),
        (install, "provision_query_commands", "provisioning"),
        (upgrade, "record_completed_version", "completion"),
        (upgrade, "freeze_pin", "pin"),
    ]:
        monkeypatch.setattr(module, name, spy(label, getattr(module, name)))

    upgrade.run_upgrade(installed_target)

    assert _lines(trace) == [
        "target",
        "propagation",
        "render",
        "backbone",
        "adapter",
        "capability",
        "seed paths",
        "merge and deploy",
        "render",
        "workspace",
        "provisioning",
        "completion",
        "pin",
    ]


def test_an_adapter_migration_in_the_window_runs_from_the_bundle(
    installed_target: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The project's copy of an adapter holds no `migrations/`: the transition reads
    the adapter's migrations from the bundle, runs those in its window, and records
    the adapter at its bundled version (ADR-065 point 4, step 5)."""
    source = _real_source_copy(tmp_path)
    _use_source(monkeypatch, source)
    trace = tmp_path / "trace.txt"
    adapter = _bump_bundled_adapter(source, "0.7.0")
    _stage_script(adapter, "0.7.0", _tracing(trace, "0.7.0"))
    project_adapter = installed_target / ".pkit" / "adapters" / "claude-code"
    record = project_adapter / "project" / "manifest.yaml"
    recorded = manifest.read_component_manifest(record)
    assert recorded is not None and recorded.version == "0.6.0"

    upgrade.run_upgrade(installed_target, dry_run=True)

    out = capsys.readouterr().out
    assert "adapter 'claude-code': 0.6.0 -> 0.7.0" in out
    assert "would run 1 migration(s) for adapter 'claude-code' (0.6.0 -> v0.7.0)" in out
    assert not trace.exists()

    upgrade.run_upgrade(installed_target, pin=False)

    assert "running 1 migration(s) for adapter 'claude-code'" in capsys.readouterr().out
    assert _lines(trace) == ["0.7.0"]
    recorded = manifest.read_component_manifest(record)
    assert recorded is not None and recorded.version == "0.7.0"
    assert not (project_adapter / "migrations").exists()


def test_the_adapter_copy_carries_its_permission_enforcement_declaration(
    installed_target: Path,
) -> None:
    """First install copies the adapter's declaration of the permission dimensions
    its harness enforces, a transition brings it to a project that lacks it, and
    `pkit permissions` reads it there. A top-level file the bundle no longer ships
    is removed (ADR-065 point 4)."""
    from project_kit import permissions

    adapter = installed_target / ".pkit" / "adapters" / "claude-code"
    declaration = adapter / "permission-enforcement.yaml"
    assert declaration.is_file()
    declaration.unlink()  # as in every project installed before this release
    stale = adapter / "retired.yaml"
    stale.write_text("retired: true\n", encoding="utf-8")
    _record_finished_at(installed_target, "0.1.0")

    upgrade.run_upgrade(installed_target, pin=False)

    assert declaration.is_file()
    assert not stale.exists()
    gap = permissions._gap_report(installed_target, {"runtime": [], "unprojectable": []})
    assert any("network-egress" in line for line in gap), gap


def test_a_releases_new_adapter_is_registered_at_its_bundled_version(
    installed_target: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """An adapter the target adds is registered by the transition that brings it,
    and recorded at the version it ships (ADR-065 point 2)."""
    source = _real_source_copy(tmp_path)
    _use_source(monkeypatch, source)
    harness = source / "adapters" / "harness"
    harness.mkdir()
    (harness / "package.yaml").write_text(
        "schema_version: 1\ncomponent:\n  kind: adapter\n  name: harness\n  version: 0.3.0\n"
        'requires_backbone: ">=0.0.0"\n',
        encoding="utf-8",
    )
    _record_finished_at(installed_target, "0.1.0")

    upgrade.run_upgrade(installed_target, pin=False, dry_run=True)
    assert "would register adapter 'harness' at 0.3.0" in " ".join(capsys.readouterr().out.split())

    upgrade.run_upgrade(installed_target, pin=False)

    backbone = manifest.read_backbone_manifest(installed_target)
    assert backbone is not None
    entries = {(c.kind, c.name): c.manifest for c in backbone.components}
    assert entries[("adapter", "harness")] == ".pkit/adapters/harness/project/manifest.yaml"
    record = manifest.read_component_manifest(
        installed_target / ".pkit" / "adapters" / "harness" / "project" / "manifest.yaml"
    )
    assert record is not None and record.version == "0.3.0"


def test_capability_migrations_run_dependencies_first(
    installed_target: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`alpha` comes first in the registry and requires `beta`: `beta`'s migrations
    run first, by `requires_capabilities`, not in the manifest's order (COR-030)."""
    source = _real_source_copy(tmp_path)
    _use_source(monkeypatch, source)
    trace = tmp_path / "trace.txt"
    _stage_moving_capability(
        source,
        installed_target,
        "alpha",
        requires_capabilities=[{"name": "beta", "version": ">=0.2.0,<1.0.0"}],
    )
    _stage_moving_capability(source, installed_target, "beta")
    for name in ("alpha", "beta"):
        _stage_script(source / "capabilities" / name, "0.2.0", _tracing(trace, name))
    backbone = manifest.read_backbone_manifest(installed_target)
    assert backbone is not None
    assert [c.name for c in backbone.components if c.kind == "capability"] == ["alpha", "beta"]

    upgrade.run_upgrade(installed_target, pin=False)

    assert _lines(trace) == ["beta", "alpha"]


def test_dependencies_first_keeps_registry_order_otherwise_and_breaks_a_cycle() -> None:
    from project_kit.capabilities import CapabilityDependency, CapabilityPackage, CapabilitySource
    from project_kit.sync import COPY, CapabilityPlan

    def plan(name: str, *requires: str) -> CapabilityPlan:
        package = CapabilityPackage(
            name=name,
            version="0.2.0",
            description="Test.",
            requires_backbone=">=0.0.0",
            requires_capabilities=tuple(CapabilityDependency(r, ">=0.0.0") for r in requires),
        )
        return CapabilityPlan(name, COPY, CapabilitySource(name, Path(name), package))

    plans = [plan("a", "c"), plan("b"), plan("c", "a"), plan("d", "b")]

    assert [p.name for p in upgrade.dependencies_first(plans)] == ["c", "a", "b", "d"]


def _a_new_collision(target: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """`trial` installed at 0.1.0, the project's own committed skill `clash`, and a
    bundle whose `trial` 0.2.0 ships a skill `clash` too. Returns the bundle's
    `trial`."""
    from tests.adopter_repo import GitRepo

    _install_trial(target, tmp_path, "0.1.0")
    skill = target / ".pkit" / "skills" / "project" / "clash.md"
    skill.parent.mkdir(parents=True, exist_ok=True)
    skill.write_text("---\nname: clash\n---\n# The project's\n", encoding="utf-8")
    GitRepo(target).commit("the project's skill")
    source = _real_source_copy(tmp_path)
    _use_source(monkeypatch, source)
    cap = _stage_trial(source, "0.2.0")
    (cap / "skills" / "clash.md").write_text("---\nname: clash\n---\n# Trial's\n", "utf-8")
    return cap


def _upgrade_at_a_terminal(monkeypatch: pytest.MonkeyPatch, answers: str) -> Any:
    from click.testing import CliRunner

    from project_kit.cli import main

    monkeypatch.setattr(upgrade, "_at_a_terminal", lambda: True)
    return CliRunner().invoke(main, ["upgrade", "--no-self-update", "--no-pin"], input=answers)


def test_without_a_terminal_a_new_collision_refuses_before_anything_is_written(
    installed_target: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With nobody to answer, the transition refuses before it writes anything, and
    names a terminal re-run or a rename. `--force` does not override it (ADR-065
    point 6)."""
    _a_new_collision(installed_target, tmp_path, monkeypatch)
    monkeypatch.setattr(upgrade, "_at_a_terminal", lambda: False)
    before = _tree_bytes(installed_target)

    with pytest.raises(click.ClickException) as excinfo:
        upgrade.run_upgrade(installed_target, pin=False, force=True)

    message = excinfo.value.message
    assert "a capability's new version brings a new naming collision" in message
    assert "nobody can answer here" in message
    assert "Run `pkit upgrade` again at a terminal" in message
    assert "rename the project's artefact" in message
    assert _tree_bytes(installed_target) == before


def test_at_a_terminal_a_skip_is_recorded_before_the_copy_and_never_asked_again(
    installed_target: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A new collision is asked about at a terminal. A skip is recorded in the
    capability's manifest before its copy, so after a migration stops the
    transition, the next one, with nobody to answer, does not ask again
    (ADR-065 point 6)."""
    cap = _a_new_collision(installed_target, tmp_path, monkeypatch)
    fixed = tmp_path / "fixed"
    _stage_script(cap, "0.2.0", _tracing(tmp_path / "trace.txt", "ran", unless_missing=fixed))

    result = _upgrade_at_a_terminal(monkeypatch, "skip\n")

    assert result.exit_code != 0
    assert "skill 'clash' collides with existing .pkit/skills/project/clash.md" in result.output
    assert "exited with status 3" in result.output
    record = _trial_record(installed_target)
    assert record is not None and record.version == "0.1.0"
    assert record.backend_state["skipped"] == [{"kind": "skill", "name": "clash"}]

    fixed.touch()
    monkeypatch.setattr(upgrade, "_at_a_terminal", lambda: False)
    upgrade.run_upgrade(installed_target, pin=False)

    record = _trial_record(installed_target)
    assert record is not None and record.version == "0.2.0"
    assert record.backend_state["skipped"] == [{"kind": "skill", "name": "clash"}]
    installed = installed_target / ".pkit" / "capabilities" / "trial" / "skills"
    assert (installed / "trial-skill.md").is_file()
    assert not (installed / "clash.md").exists()
    project = installed_target / ".pkit" / "skills" / "project" / "clash.md"
    assert project.read_text(encoding="utf-8") == "---\nname: clash\n---\n# The project's\n"


def test_at_a_terminal_an_override_replaces_the_projects_artefact(
    installed_target: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Override: the capability's artefact replaces the project's, which git keeps,
    and nothing is recorded (ADR-065 point 6, COR-017)."""
    _a_new_collision(installed_target, tmp_path, monkeypatch)

    result = _upgrade_at_a_terminal(monkeypatch, "override\n")

    assert result.exit_code == 0, result.output
    assert "removed      .pkit/skills/project/clash.md (override; git keeps it)" in result.output
    assert not (installed_target / ".pkit" / "skills" / "project" / "clash.md").exists()
    copied = installed_target / ".pkit" / "capabilities" / "trial" / "skills" / "clash.md"
    assert copied.read_text(encoding="utf-8") == "---\nname: clash\n---\n# Trial's\n"
    record = _trial_record(installed_target)
    assert record is not None and record.version == "0.2.0"
    assert "skipped" not in record.backend_state


def test_the_dry_run_lists_each_components_migrations_and_each_collision(
    installed_target: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The dry run lists each component's move and migrations, and each collision a
    real run would ask about, asks nothing and writes nothing (ADR-065 point 4)."""
    cap = _a_new_collision(installed_target, tmp_path, monkeypatch)
    source = cap.parent.parent
    _stage_script(cap, "0.2.0", "#!/usr/bin/env bash\nexit 0\n")
    _stage_script(_bump_bundled_adapter(source, "0.7.0"), "0.7.0", "#!/usr/bin/env bash\n")
    _stage_backbone_migration(source, "0.2.0", "001-old.sh", "#!/usr/bin/env bash\n")
    _record_finished_at(installed_target, "0.1.0")
    monkeypatch.setattr(upgrade, "_at_a_terminal", lambda: False)
    before = _tree_bytes(installed_target)

    upgrade.run_upgrade(installed_target, dry_run=True)

    out = " ".join(capsys.readouterr().out.split())
    assert "Components adapter 'claude-code': 0.6.0 -> 0.7.0" in out
    assert "capability 'trial': 0.1.0 -> 0.2.0" in out
    assert "capability 'trial': skill 'clash' collides with .pkit/skills/project/clash.md" in out
    assert "The upgrade asks about each one where a person can answer" in out
    assert "migration(s) for backbone" in out and "0.2.0/001-old.sh" in out
    assert "would run 1 migration(s) for adapter 'claude-code' (0.6.0 -> v0.7.0)" in out
    assert "would run 1 migration(s) for capability 'trial' (0.1.0 -> v0.2.0)" in out
    assert _tree_bytes(installed_target) == before


def test_the_report_lists_each_widening_the_settings_merge_brings(
    installed_target: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A baseline that adds an allow entry and a `hooks` key: the report names each,
    and the `ask` rule that brings the question back (ADR-065 point 4)."""
    import json

    settings = installed_target / ".claude" / "settings.json"
    settings.parent.mkdir(exist_ok=True)
    held = {"permissions": {"allow": ["Bash(git:*)"], "deny": []}}
    settings.write_text(json.dumps(held), encoding="utf-8")

    def merge(_ctx: install.InstallContext) -> None:
        widened = {
            "permissions": {"allow": ["Bash(git:*)", "Bash(curl:*)"], "deny": []},
            "hooks": {"PreToolUse": []},
        }
        settings.write_text(json.dumps(widened), encoding="utf-8")

    monkeypatch.setattr(install, "run_installed_adapter_primitives", merge)
    _record_finished_at(installed_target, "0.1.0")

    upgrade.run_upgrade(installed_target, pin=False)

    out = capsys.readouterr().out
    assert "The settings merge widens .claude/settings.json:" in out
    assert "    allow        Bash(curl:*)" in out
    assert "    key          hooks" in out
    assert "allow        Bash(git:*)" not in out
    assert (
        "add it as an `ask` rule to .pkit/adapters/claude-code/settings/project/settings.json"
    ) in out


def test_cli_upgrade_force_flag_forwards(monkeypatch: pytest.MonkeyPatch) -> None:
    """`--force` threads through to `run_upgrade(force=True)`; the default is False."""
    from click.testing import CliRunner

    from project_kit import cli

    seen: dict[str, object] = {}
    monkeypatch.setattr(cli, "find_target_root", lambda: Path("/tmp"))
    monkeypatch.setattr(cli, "run_upgrade", lambda _root, **kwargs: seen.update(kwargs))

    assert CliRunner().invoke(cli.main, ["upgrade", "--force"]).exit_code == 0
    assert seen["force"] is True
    assert CliRunner().invoke(cli.main, ["upgrade"]).exit_code == 0
    assert seen["force"] is False


def test_an_override_holds_when_a_migration_stops_the_transition(
    installed_target: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The override removes the project's artefact in step 2, before the copy, so a
    transition a migration stops keeps the answer: the next one finds the name in
    the capability's installed copy, asks nothing, and the capability's deploys
    (ADR-065 point 6)."""
    cap = _a_new_collision(installed_target, tmp_path, monkeypatch)
    fixed = tmp_path / "fixed"
    _stage_script(cap, "0.2.0", _tracing(tmp_path / "trace.txt", "ran", unless_missing=fixed))
    project = installed_target / ".pkit" / "skills" / "project" / "clash.md"

    stopped = _upgrade_at_a_terminal(monkeypatch, "override\n")

    assert stopped.exit_code != 0
    assert "exited with status 3" in stopped.output
    assert not project.exists()

    fixed.touch()
    monkeypatch.setattr(upgrade, "_at_a_terminal", lambda: False)
    upgrade.run_upgrade(installed_target, pin=False)

    assert not project.exists()
    copied = installed_target / ".pkit" / "capabilities" / "trial" / "skills" / "clash.md"
    assert copied.read_text(encoding="utf-8") == "---\nname: clash\n---\n# Trial's\n"
    record = _trial_record(installed_target)
    assert record is not None and record.version == "0.2.0"


def test_a_skip_of_a_capability_with_no_readable_version_is_recorded_before_the_copy(
    installed_target: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With no readable version, the skip is recorded at the bundled version, which
    the transition records anyway, so a transition a later step stops does not ask
    again (ADR-065 points 2 and 6)."""
    _a_new_collision(installed_target, tmp_path, monkeypatch)
    installed = installed_target / ".pkit" / "capabilities" / "trial"
    (installed / "project" / "manifest.yaml").unlink()
    (installed / "package.yaml").write_text("not: a package\n", encoding="utf-8")
    fixed = tmp_path / "fixed"
    _stage_backbone_migration(
        upgrade.find_source_kit(),
        "0.2.0",
        "001-flaky.sh",
        _tracing(tmp_path / "trace.txt", "ran", unless_missing=fixed),
    )
    _record_finished_at(installed_target, "0.1.0")

    stopped = _upgrade_at_a_terminal(monkeypatch, "skip\n")

    assert stopped.exit_code != 0
    record = _trial_record(installed_target)
    assert record is not None and record.version == "0.2.0"
    assert record.backend_state["skipped"] == [{"kind": "skill", "name": "clash"}]

    fixed.touch()
    monkeypatch.setattr(upgrade, "_at_a_terminal", lambda: False)
    upgrade.run_upgrade(installed_target, pin=False)

    assert not (installed / "skills" / "clash.md").exists()
