"""The refusal in the gap between the two source tests (ADR-059; #1070, #1090).

The methodology's source repository is recognised by sync's test (the target is
the parent of the tree the running code resolves) and by the marker test (the
package source beside `.pkit/`). Route 1 keeps them equal; where the running
code is not the repository's own they disagree, and sync and upgrade would copy
a foreign `.pkit/` over the source, and the capability verbs a foreign
capability subtree. They refuse instead, and `pkit pin` refuses wherever either
test recognises the source. A deleted dispatcher is one more way into the gap,
never a way out of the marker test.

Each path into the gap is exercised without taking it for real: the fixture
tree carries both markers while this suite's checkout is the running code, so
sync's test says no exactly as it does under another checkout's or an installed
distribution's code.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import click
import pytest
from click.testing import CliRunner

from project_kit import capabilities as caps
from project_kit import install, manifest, router, upgrade
from project_kit.cli import main
from project_kit.sync import run_sync
from tests.adopter_repo import MakeAdopterRepo

# A kit-owned file carrying a local edit. Propagation overwrites it from the
# running code's tree, so its surviving a refused run shows nothing propagated.
_SENTINEL = Path(".pkit") / "decisions" / "README.md"
_SENTINEL_TEXT = "edited in the source repository\n"


@pytest.fixture(autouse=True)
def _no_release_lookup(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep upgrade's tool step off the network should a refusal ever regress."""
    monkeypatch.setattr(upgrade, "_latest_released_version", lambda: None)


@pytest.fixture
def source_checkout(make_adopter_repo: MakeAdopterRepo, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A repository the marker test calls the methodology's source, run by other code.

    Source-shaped by construction: an installed tree, which carries the in-tree
    dispatcher (executable, as install leaves it), plus the package source beside
    it. The running code is this suite's checkout, whose tree is not this
    repository's `.pkit/`, so sync's test says no: the gap. The routing variables
    are cleared so each test sets only the path it exercises. The process's
    working directory is the repository, as for a command run there.
    """
    root = make_adopter_repo().root
    (root / "src" / "project_kit").mkdir(parents=True)
    (root / "src" / "project_kit" / "__init__.py").write_text("", encoding="utf-8")
    (root / _SENTINEL).write_text(_SENTINEL_TEXT, encoding="utf-8")
    monkeypatch.delenv(router._BYPASS_ENV, raising=False)
    monkeypatch.delenv(router._LOOP_GUARD_ENV, raising=False)
    assert router.is_source_checkout(root)
    assert not install.is_self_host(root, install.find_source_kit())
    return root


def _assert_untouched(root: Path) -> None:
    assert (root / _SENTINEL).read_text(encoding="utf-8") == _SENTINEL_TEXT
    assert not router.pin_file_path(root).exists()


def _refusal(exc: pytest.ExceptionInfo[click.ClickException]) -> str:
    return exc.value.format_message()


# --- sync and upgrade refuse, naming both tests and the way in ------------------


def test_sync_refuses_under_no_route(
    source_checkout: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An operator's `PKIT_NO_ROUTE=1` skips route 1; sync refuses rather than copy."""
    monkeypatch.setenv(router._BYPASS_ENV, "1")

    with pytest.raises(click.ClickException) as exc:
        run_sync(source_checkout)

    message = _refusal(exc)
    assert f"refusing to run `sync` in {source_checkout}" in message
    assert "The marker test says it is the source" in message
    assert "Sync's test says it is not" in message
    assert "PKIT_NO_ROUTE=1" in message
    assert ".pkit/cli/pkit sync" in message  # the remedy: the checkout's own code
    _assert_untouched(source_checkout)


@pytest.mark.parametrize("flags", [{"force": True}, {"dry_run": True}], ids=["force", "dry-run"])
def test_sync_refusal_has_no_override(
    source_checkout: Path, monkeypatch: pytest.MonkeyPatch, flags: dict[str, bool]
) -> None:
    """`--force` overrides the capability downgrade guard only, and a dry run
    previews nothing past a refusal: the gap is a defect path, not a choice."""
    monkeypatch.setenv(router._BYPASS_ENV, "1")

    with pytest.raises(click.ClickException, match="no flag overrides this refusal"):
        run_sync(source_checkout, **flags)

    _assert_untouched(source_checkout)


def test_upgrade_refuses_under_no_route(
    source_checkout: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Upgrade refuses before its bypass guard: under `PKIT_NO_ROUTE` the tool step
    is skipped, so a refusal placed there would never be reached."""
    recorded = manifest.read_backbone_manifest(source_checkout)
    assert recorded is not None
    recorded.backbone_version = "0.1.0"  # content behind, so upgrade has work to do
    manifest.write_backbone_manifest(source_checkout, recorded)
    monkeypatch.setenv(router._BYPASS_ENV, "1")

    with pytest.raises(click.ClickException) as exc:
        upgrade.run_upgrade(source_checkout)

    message = _refusal(exc)
    assert f"refusing to run `upgrade` in {source_checkout}" in message
    assert "PKIT_NO_ROUTE=1" in message
    _assert_untouched(source_checkout)
    after = manifest.read_backbone_manifest(source_checkout)
    assert after is not None and after.backbone_version == "0.1.0"


def test_release_upgrade_bootstrapped_by_a_pin_refuses(
    source_checkout: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The `pin`-to-newer-release path: `pkit pin <newer>` (and a pinned `pkit
    upgrade`) run that release's `upgrade` through `run_bypassed`. Wherever that
    bootstrap still happens — older code, with no guard of `pin`'s own in the
    source — the release's upgrade must refuse on its own, under exactly the
    environment `run_bypassed` hands it."""
    seen: dict[str, dict[str, str]] = {}

    def _capture(
        cmd: list[str], env: dict[str, str], **_kw: object
    ) -> subprocess.CompletedProcess[str]:
        seen["env"] = env
        return subprocess.CompletedProcess(cmd, 0)

    with monkeypatch.context() as spawn:
        spawn.setattr(router.subprocess, "run", _capture)
        router.run_bypassed("99.0.0", ["upgrade"], environ={router._LOOP_GUARD_ENV: "1"})
    for name in (router._BYPASS_ENV, router._LOOP_GUARD_ENV):
        if name in seen["env"]:
            monkeypatch.setenv(name, seen["env"][name])

    with pytest.raises(click.ClickException) as exc:
        upgrade.run_upgrade(source_checkout)

    message = _refusal(exc)
    assert "PKIT_NO_ROUTE=1" in message
    assert "`pkit pin <version>`" in message
    _assert_untouched(source_checkout)


def test_non_executable_dispatcher_refuses_through_the_router(
    source_checkout: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A dispatcher present but not executable: route 1 falls back to the running
    binary. Its warning points at repairing the dispatcher, and the sync that
    warning used to advise refuses. Driven through the real router and CLI."""
    dispatcher = router.source_dispatcher(source_checkout)
    dispatcher.chmod(0o644)
    monkeypatch.setattr(sys, "argv", ["pkit", "sync"])

    with pytest.raises(SystemExit) as exited:
        router.main(["sync"])

    assert exited.value.code == 1
    err = capsys.readouterr().err
    assert f"chmod +x {dispatcher}" in err  # the router's warning names the repair
    assert "Re-run `pkit sync`" not in err
    assert f"refusing to run `sync` in {source_checkout}" in err
    assert "is not executable, so the router fell back" in err
    _assert_untouched(source_checkout)


def test_deleted_dispatcher_is_still_the_source_and_refuses_through_the_router(
    source_checkout: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The fourth way into the gap (#1090): a dispatcher deleted outright. The
    package source still marks the checkout as the source, so it is never taken
    for an adopter: route 1 falls back naming the restore, and the sync that
    fallback runs refuses rather than propagating over it."""
    dispatcher = router.source_dispatcher(source_checkout)
    dispatcher.unlink()
    monkeypatch.setattr(sys, "argv", ["pkit", "sync"])

    with pytest.raises(SystemExit) as exited:
        router.main(["sync"])

    assert exited.value.code == 1
    err = " ".join(capsys.readouterr().err.split())
    # The router's warning: the checkout is recognised, and what to restore.
    assert "carries the methodology's package source but no dispatcher" in err
    assert f"restore it with `git checkout -- {dispatcher}`" in err
    # The refusal: the dispatcher's absence is the way in, and the remedy waits on it.
    assert f"refusing to run `sync` in {source_checkout}" in err
    assert f"the dispatcher {dispatcher} is missing, so the router fell back" in err
    assert "own code instead, once its dispatcher is restored: `.pkit/cli/pkit sync`" in err
    _assert_untouched(source_checkout)


# --- the capability verbs refuse the same way (#1090) --------------------------

# A file of an installed kit-shipped capability carrying a local edit: a refresh
# from the running code's tree would overwrite it.
_CAPABILITY_SENTINEL = Path(".pkit") / "capabilities" / "evidence" / "README.md"


@pytest.mark.parametrize(
    ("args", "would"),
    [
        pytest.param(
            ["install", "demo-recording"],
            "copy the capability's subtree from that tree into the one it is built from",
            id="install",
        ),
        pytest.param(
            ["install", "demo-recording", "--plan"],
            "copy the capability's subtree from that tree into the one it is built from",
            id="install-plan",
        ),
        pytest.param(
            ["upgrade", "evidence"],
            "refresh the capability with that code — a kit-shipped one from that tree, "
            "over the one it is built from",
            id="upgrade",
        ),
        pytest.param(
            ["register", "evidence"],
            "register the capability with that code, writing install-state into the tree "
            "it is built from",
            id="register",
        ),
    ],
)
def test_capability_verbs_refuse_in_the_source_run_by_other_code(
    source_checkout: Path, monkeypatch: pytest.MonkeyPatch, args: list[str], would: str
) -> None:
    """`capabilities install`, `upgrade` and `register` copy or register a
    capability with the running code's tree, so in the gap they refuse as sync
    does — with the same message, naming the command as it would be re-run —
    before any other pre-flight, and write nothing."""
    installed = caps.find_capability_in_source(install.find_source_kit(), "evidence")
    assert installed is not None
    caps.install_capability(source_checkout, installed)
    (source_checkout / _CAPABILITY_SENTINEL).write_text(_SENTINEL_TEXT, encoding="utf-8")
    recorded = (source_checkout / ".pkit" / "manifest.yaml").read_bytes()
    monkeypatch.setenv(router._BYPASS_ENV, "1")

    result = CliRunner().invoke(main, ["capabilities", *args])

    assert result.exit_code == 1, result.output
    message = " ".join(result.output.split())
    command = " ".join(["capabilities", *args[:2]])
    assert f"refusing to run `{command}` in {source_checkout}" in message
    assert "The marker test says it is the source" in message
    assert "Sync's test says it is not" in message
    assert f"`{command}` would {would} (ADR-059)" in message
    assert "Nothing was written, and no flag overrides this refusal." in message
    assert "PKIT_NO_ROUTE=1" in message
    assert f"own code instead: `.pkit/cli/pkit {command}` from {source_checkout}." in message
    _assert_untouched(source_checkout)
    assert (source_checkout / ".pkit" / "manifest.yaml").read_bytes() == recorded
    assert (source_checkout / _CAPABILITY_SENTINEL).read_text(encoding="utf-8") == _SENTINEL_TEXT
    assert not (source_checkout / ".pkit" / "capabilities" / "demo-recording").exists()


def test_inherited_loop_guard_is_named(
    source_checkout: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A pinned run elsewhere that spawns pkit here passes `PKIT_ROUTED` on, which
    suppresses routing just as the bypass does."""
    monkeypatch.setenv(router._LOOP_GUARD_ENV, "1")

    with pytest.raises(click.ClickException, match=r"PKIT_ROUTED=1"):
        run_sync(source_checkout)

    _assert_untouched(source_checkout)


def test_a_start_without_the_router_is_named(source_checkout: Path) -> None:
    """No routing variable and a working dispatcher: the run never went through
    the router here — another checkout's dispatcher or package was started."""
    with pytest.raises(click.ClickException, match="did not start through the router"):
        run_sync(source_checkout)

    _assert_untouched(source_checkout)


# --- `pkit pin` refuses in the source repository ---------------------------------


@pytest.mark.parametrize("args", [["pin"], ["pin", "99.0.0"]], ids=["freeze", "newer"])
@pytest.mark.parametrize("test_holding", ["sync's test", "markers only"])
def test_pin_refuses_in_the_source_repository(
    source_checkout: Path,
    monkeypatch: pytest.MonkeyPatch,
    args: list[str],
    test_holding: str,
) -> None:
    """Under route 1 the running code is the checkout's own and sync's test holds;
    in the gap only the markers do. A pin is meaningless either way, and a newer
    target must never bootstrap a release's upgrade over the checkout."""
    if test_holding == "sync's test":
        # Route 1: the running code's tree is this repository's own `.pkit/`.
        monkeypatch.setattr(upgrade, "find_source_kit", lambda: source_checkout / ".pkit")

    def _no_bootstrap(*_a: object, **_k: object) -> int:
        raise AssertionError("a refused pin must not bootstrap a release's upgrade")

    monkeypatch.setattr(upgrade, "run_bypassed", _no_bootstrap)

    result = CliRunner().invoke(main, args)

    assert result.exit_code != 0
    assert f"refusing to pin {source_checkout}" in result.output
    assert (
        "a pin is meaningless in the methodology's source: route 1 runs its own code "
        "before any pin is read"
    ) in " ".join(result.output.split())
    _assert_untouched(source_checkout)
