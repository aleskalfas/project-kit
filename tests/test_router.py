"""Tests for the `pkit` entry-point router (ADR-039).

The router runs on *every* `pkit` invocation and decides which process serves
the command before the heavy CLI is imported. These tests cover each of the
three routes, graceful degradation on an unresolvable pin, the loop guard, the
bypass env, and that a normal (route-3) invocation still reaches the CLI.

Exec / subprocess seams are patched so no process is actually replaced or
spawned; the routing *decision* is what is under test.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest

from project_kit import router


class _ExecCalled(Exception):
    """Sentinel raised in place of `os.execv`, which would replace the process."""

    def __init__(self, path: str, argv: tuple[str, ...]) -> None:
        super().__init__(path)
        self.path = path
        self.argv = argv


@pytest.fixture(autouse=True)
def no_inherited_notice(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every test starts with no pin-fallback notice said: the router sets the
    notice guard on this process's environment when it degrades, and
    monkeypatch restores it only for a variable it has recorded."""
    monkeypatch.setenv(router._PIN_UNRESOLVED_ENV, "")
    monkeypatch.delenv(router._PIN_UNRESOLVED_ENV)


@pytest.fixture
def ran_self(monkeypatch: pytest.MonkeyPatch) -> list[bool]:
    """Record whether the route-3 `_run_self` hand-off fired (without importing
    the real CLI)."""
    calls: list[bool] = []
    monkeypatch.setattr(router, "_run_self", lambda: calls.append(True))
    return calls


@pytest.fixture
def no_exec(monkeypatch: pytest.MonkeyPatch) -> None:
    """Turn `os.execv` into a raising sentinel so route 1 never replaces the
    test process."""

    def fake_execv(path: str, argv: list[str]) -> None:
        raise _ExecCalled(path, tuple(argv))

    monkeypatch.setattr(router.os, "execv", fake_execv)


def _make_source_checkout(
    root: Path, *, dispatcher_executable: bool = True, version: str | None = None
) -> Path:
    """Materialise the minimal markers of a project-kit source checkout.

    Writes a `.pkit/VERSION` when `version` is given; omits it otherwise (the
    missing-VERSION case route 1 must tolerate). Source-shaped by construction,
    and only ever routed, never synced: every test here that falls through to
    the CLI stubs `_run_self`, so the refusal to propagate over the source
    (#1070) is out of reach."""
    (root / "src" / "project_kit").mkdir(parents=True)
    (root / "src" / "project_kit" / "__init__.py").write_text("", encoding="utf-8")
    (root / ".git").mkdir()
    cli_dir = root / ".pkit" / "cli"
    cli_dir.mkdir(parents=True)
    dispatcher = cli_dir / "pkit"
    dispatcher.write_text("#!/usr/bin/env bash\n", encoding="utf-8")
    dispatcher.chmod(0o755 if dispatcher_executable else 0o644)
    if version is not None:
        (root / ".pkit" / "VERSION").write_text(version + "\n", encoding="utf-8")
    return dispatcher


def _make_adopter(root: Path, version: str) -> None:
    """Materialise an adopter project pinning `version` via `.pkit/version-pin`
    (ADR-049)."""
    (root / ".git").mkdir()
    pkit = root / ".pkit"
    pkit.mkdir()
    (pkit / "version-pin").write_text(version + "\n", encoding="utf-8")


# --- Predicates ----------------------------------------------------------------


def test_enclosing_project_walks_up_to_boundary(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    deep = tmp_path / "a" / "b" / "c"
    deep.mkdir(parents=True)
    assert router._enclosing_project(deep) == tmp_path.resolve()


def test_enclosing_project_none_outside_any_project(tmp_path: Path) -> None:
    # tmp_path has no .git/.pkit anywhere above it; the walk reaches the
    # filesystem root and returns None.
    plain = tmp_path / "plain"
    plain.mkdir()
    assert router._enclosing_project(plain) is None


def test_enclosing_project_skips_bare_pkit_dir(tmp_path: Path) -> None:
    # A stray `.pkit/` with only junk (no manifest, no decisions/) is not an
    # install and must not qualify its parent as a project boundary (#656).
    (tmp_path / ".pkit" / "shim").mkdir(parents=True)
    deep = tmp_path / "work"
    deep.mkdir()
    assert router._enclosing_project(deep) is None


def test_enclosing_project_accepts_install_marked_pkit(tmp_path: Path) -> None:
    pkit_dir = tmp_path / ".pkit"
    pkit_dir.mkdir()
    (pkit_dir / "manifest.yaml").write_text("backbone_version: 1.0.0\n", encoding="utf-8")
    deep = tmp_path / "a" / "b"
    deep.mkdir(parents=True)
    assert router._enclosing_project(deep) == tmp_path.resolve()


def test_looks_like_pkit_install_markers(tmp_path: Path) -> None:
    pkit_dir = tmp_path / ".pkit"
    assert router.looks_like_pkit_install(pkit_dir) is False  # absent
    pkit_dir.mkdir()
    assert router.looks_like_pkit_install(pkit_dir) is False  # bare
    (pkit_dir / "decisions").mkdir()
    assert router.looks_like_pkit_install(pkit_dir) is True  # legacy marker
    (pkit_dir / "manifest.yaml").write_text("backbone_version: 1.0.0\n", encoding="utf-8")
    assert router.looks_like_pkit_install(pkit_dir) is True  # manifest marker


def test_is_source_checkout_true_only_with_package_source(tmp_path: Path) -> None:
    _make_source_checkout(tmp_path)
    assert router.is_source_checkout(tmp_path) is True


def test_is_source_checkout_false_for_adopter(tmp_path: Path) -> None:
    _make_adopter(tmp_path, "1.100.0")
    (tmp_path / ".pkit" / "cli").mkdir()
    (tmp_path / ".pkit" / "cli" / "pkit").write_text("", encoding="utf-8")
    # Has the dispatcher, but no src/project_kit → not a source checkout.
    assert router.is_source_checkout(tmp_path) is False


def test_is_source_checkout_true_with_the_dispatcher_deleted(tmp_path: Path) -> None:
    """The package source beside `.pkit/` is what tells the source from an adopter;
    the dispatcher is only what route 1 execs, so losing it never makes the
    checkout an adopter (#1090)."""
    _make_source_checkout(tmp_path).unlink()
    assert router.is_source_checkout(tmp_path) is True
    assert router.source_dispatcher_missing(tmp_path) is True


def test_package_source_without_a_pkit_tree_is_not_a_source_checkout(tmp_path: Path) -> None:
    (tmp_path / "src" / "project_kit").mkdir(parents=True)
    (tmp_path / "src" / "project_kit" / "__init__.py").write_text("", encoding="utf-8")
    assert router.is_source_checkout(tmp_path) is False


def test_resolve_pin_reads_version_pin(tmp_path: Path) -> None:
    _make_adopter(tmp_path, "1.100.0")
    assert router._resolve_pin(tmp_path) == "1.100.0"


def test_resolve_pin_none_when_absent(tmp_path: Path) -> None:
    (tmp_path / ".pkit").mkdir()
    assert router._resolve_pin(tmp_path) is None


def test_resolve_pin_ignores_pkit_version_file(tmp_path: Path) -> None:
    # `.pkit/VERSION` is the source tree's identity, NOT the pin source (ADR-049).
    # A project with only VERSION and no version-pin resolves to no pin.
    (tmp_path / ".pkit").mkdir()
    (tmp_path / ".pkit" / "VERSION").write_text("1.100.0\n", encoding="utf-8")
    assert router._resolve_pin(tmp_path) is None


def test_read_version_pin_strips_and_empty_is_none(tmp_path: Path) -> None:
    (tmp_path / ".pkit").mkdir()
    pin = tmp_path / ".pkit" / "version-pin"
    pin.write_text("  1.100.0  \n", encoding="utf-8")
    assert router.read_version_pin(tmp_path) == "1.100.0"
    pin.write_text("\n", encoding="utf-8")  # present but empty → no pin
    assert router.read_version_pin(tmp_path) is None


def test_pin_file_path_is_under_pkit(tmp_path: Path) -> None:
    assert router.pin_file_path(tmp_path) == tmp_path / ".pkit" / "version-pin"


# --- write_version_pin: the pin's one writer, whole or not at all (#1211) -------


def _pkit_entries(root: Path) -> list[str]:
    """What `.pkit/` holds — the pin, and any temporary file a write left beside it."""
    return sorted(entry.name for entry in (root / ".pkit").iterdir())


def test_write_version_pin_writes_what_the_reader_reads_and_no_temporary(tmp_path: Path) -> None:
    (tmp_path / ".pkit").mkdir()

    router.write_version_pin(tmp_path, "1.100.0")

    assert router.pin_file_path(tmp_path).read_bytes() == b"1.100.0\n"
    assert router.read_version_pin(tmp_path) == "1.100.0"
    assert _pkit_entries(tmp_path) == ["version-pin"]


@pytest.mark.parametrize("failing", ["fsync", "replace"])
def test_write_version_pin_cut_short_leaves_the_previous_pin_intact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failing: str
) -> None:
    """A write that dies before its bytes reach the disk, or at the rename, leaves
    the previous pin byte-identical and no temporary file: the router never reads
    a torn pin as the version to run."""
    (tmp_path / ".pkit").mkdir()
    pin = router.pin_file_path(tmp_path)
    pin.write_bytes(b"1.145.0\n")

    def _cut_short(*_args: object) -> None:
        raise OSError("the write died here")

    monkeypatch.setattr(os, failing, _cut_short)

    with pytest.raises(OSError, match="the write died here"):
        router.write_version_pin(tmp_path, "1.146.0")

    assert pin.read_bytes() == b"1.145.0\n"
    assert _pkit_entries(tmp_path) == ["version-pin"]


def test_write_version_pin_none_removes_the_pin_and_absent_is_fine(tmp_path: Path) -> None:
    (tmp_path / ".pkit").mkdir()
    router.pin_file_path(tmp_path).write_text("1.100.0\n", encoding="utf-8")

    router.write_version_pin(tmp_path, None)
    assert not router.pin_file_path(tmp_path).exists()

    router.write_version_pin(tmp_path, None)  # nothing to remove: no error
    assert _pkit_entries(tmp_path) == []


def test_is_routed_child_reads_loop_guard(tmp_path: Path) -> None:
    assert router.is_routed_child({router._LOOP_GUARD_ENV: "1"}) is True
    assert router.is_routed_child({}) is False


def test_pinned_base_is_git_tag_pin(tmp_path: Path) -> None:
    base = router._pinned_base("1.100.0")
    assert base[0] == "uvx"
    assert "--from" in base
    assert f"{router.DISTRIBUTION_GIT_URL}@v1.100.0" in base
    assert base[-1] == "project-kit"


# --- Route 1: source checkout → exec the dispatcher ----------------------------


def test_route1_execs_in_tree_dispatcher(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, no_exec: None, ran_self: list[bool]
) -> None:
    dispatcher = _make_source_checkout(tmp_path)
    monkeypatch.chdir(tmp_path)

    with pytest.raises(_ExecCalled) as excinfo:
        router.main(["sync", "--dry-run"])

    assert excinfo.value.path == str(dispatcher)
    assert excinfo.value.argv == (str(dispatcher), "sync", "--dry-run")
    assert ran_self == []  # never falls through to self on a clean route 1


def test_route1_degrades_to_self_when_dispatcher_not_executable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    no_exec: None,
    ran_self: list[bool],
    capsys: pytest.CaptureFixture[str],
) -> None:
    _make_source_checkout(tmp_path, dispatcher_executable=False)
    monkeypatch.chdir(tmp_path)

    router.main(["version"])

    assert ran_self == [True]
    err = capsys.readouterr().err
    assert "not executable" in err or "missing" in err
    # The fallback runs code that is not the checkout's own: the warning names
    # the repair, not the sync that would refuse there (ADR-059; #1070).
    assert f"chmod +x {router.source_dispatcher(tmp_path)}" in err
    assert "Re-run `pkit sync`" not in err


def test_route1_names_a_deleted_dispatcher_and_its_restore(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    no_exec: None,
    ran_self: list[bool],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A checkout with its dispatcher deleted is still the source: route 1 falls
    back, and its warning says what is missing and how to restore it, never
    treating the checkout as an adopter silently (#1090)."""
    dispatcher = _make_source_checkout(tmp_path)
    dispatcher.unlink()
    monkeypatch.chdir(tmp_path)

    router.main(["version"])

    assert ran_self == [True]
    err = capsys.readouterr().err
    assert "carries the methodology's package source but no dispatcher" in err
    assert f"restore it with `git checkout -- {dispatcher}`" in err
    assert "chmod +x" not in err  # nothing to chmod: the file is gone


# --- Route 1: PKIT_CLI_VERSION stamp (spurious-drift fix, #488) -----------------


def test_route1_stamps_cli_version_from_tree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, no_exec: None
) -> None:
    _make_source_checkout(tmp_path, version="1.141.0")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv(router._CLI_VERSION_ENV, raising=False)

    with pytest.raises(_ExecCalled):
        router.main(["version"])

    # The dispatched child inherits os.environ; the tree version is stamped so
    # provenance reads cli == tree.
    assert os.environ[router._CLI_VERSION_ENV] == "1.141.0"


def test_route1_does_not_overwrite_explicit_cli_version(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, no_exec: None
) -> None:
    _make_source_checkout(tmp_path, version="1.141.0")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv(router._CLI_VERSION_ENV, "9.9.9")  # explicit override

    with pytest.raises(_ExecCalled):
        router.main(["version"])

    assert os.environ[router._CLI_VERSION_ENV] == "9.9.9"  # left untouched


def test_route1_leaves_cli_version_unset_when_tree_version_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, no_exec: None
) -> None:
    _make_source_checkout(tmp_path)  # no .pkit/VERSION written
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv(router._CLI_VERSION_ENV, raising=False)

    with pytest.raises(_ExecCalled):  # missing VERSION must not crash the route
        router.main(["version"])

    assert router._CLI_VERSION_ENV not in os.environ  # no guess, stays unset


# --- Route 2: pin mismatch → re-exec the pinned wheel --------------------------


class _FakeCompleted:
    def __init__(self, returncode: int) -> None:
        self.returncode = returncode


def _patch_subprocess(
    monkeypatch: pytest.MonkeyPatch, results: list[object]
) -> list[dict[str, Any]]:
    """Patch `router.subprocess.run` to return/raise `results` in order,
    recording each call. A result that is an Exception is raised."""
    calls: list[dict[str, Any]] = []
    it = iter(results)

    def fake_run(cmd, **kwargs):
        calls.append({"cmd": cmd, "kwargs": kwargs})
        outcome = next(it)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    monkeypatch.setattr(router.subprocess, "run", fake_run)
    return calls


def test_route2_reexecs_pinned_version_and_propagates_exit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, no_exec: None, ran_self: list[bool]
) -> None:
    _make_adopter(tmp_path, "1.100.0")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv(router._CLI_VERSION_ENV, raising=False)
    monkeypatch.setattr(router, "running_version", lambda: "1.139.0")
    # Probe resolves (rc 0), then the real command exits 3.
    calls = _patch_subprocess(monkeypatch, [_FakeCompleted(0), _FakeCompleted(3)])

    with pytest.raises(SystemExit) as excinfo:
        router.main(["validate"])

    assert excinfo.value.code == 3
    assert ran_self == []  # ran the pinned command, not self
    # Route 2 must NOT stamp the CLI version: the pinned wheel reports its own
    # accurate metadata, so a genuine cli ≠ tree drift stays visible.
    assert router._CLI_VERSION_ENV not in calls[1]["kwargs"]["env"]
    assert router._CLI_VERSION_ENV not in os.environ
    # Two invocations: the --version probe, then the real command.
    assert len(calls) == 2
    probe_cmd = calls[0]["cmd"]
    real_cmd = calls[1]["cmd"]
    assert probe_cmd[-1] == "--version"
    assert f"{router.DISTRIBUTION_GIT_URL}@v1.100.0" in real_cmd
    assert real_cmd[-1] == "validate"
    # The loop guard is set on the child's environment.
    assert calls[1]["kwargs"]["env"][router._LOOP_GUARD_ENV] == "1"


def test_route2_degrades_to_self_when_pin_unresolvable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    no_exec: None,
    ran_self: list[bool],
    capsys: pytest.CaptureFixture[str],
) -> None:
    _make_adopter(tmp_path, "1.100.0")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(router, "running_version", lambda: "1.139.0")
    # Probe fails to resolve (rc 1); no real command should run.
    calls = _patch_subprocess(monkeypatch, [_FakeCompleted(1)])

    router.main(["status"])  # must NOT raise SystemExit

    assert ran_self == [True]  # degraded to running self
    assert len(calls) == 1  # only the probe ran
    err = capsys.readouterr().err
    assert "1.100.0" in err and "1.139.0" in err  # loud drift warning names both


def test_route2_degrades_when_uvx_absent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    no_exec: None,
    ran_self: list[bool],
    capsys: pytest.CaptureFixture[str],
) -> None:
    _make_adopter(tmp_path, "1.100.0")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(router, "running_version", lambda: "1.139.0")
    _patch_subprocess(monkeypatch, [FileNotFoundError("uvx")])

    router.main(["status"])

    assert ran_self == [True]
    assert "could not be resolved" in capsys.readouterr().err


def test_route2_fallback_says_when_this_binary_is_older_than_the_pin(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    no_exec: None,
    ran_self: list[bool],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A binary older than the pin is a normal state, and the one in which sync and
    upgrade refuse (#1212): the fallback says so, and still runs the command."""
    _make_adopter(tmp_path, "1.150.0")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(router, "running_version", lambda: "1.149.0")
    _patch_subprocess(monkeypatch, [_FakeCompleted(1)])

    router.main(["status"])

    assert ran_self == [True]  # a read-only command still runs
    err = capsys.readouterr().err
    assert "pkit 1.149.0 instead, an OLDER pkit than the pin names" in err
    assert "`pkit sync` and `pkit upgrade` refuse" in err
    assert f"{router.DISTRIBUTION_GIT_URL}@v1.150.0" in err
    assert err.count("pkit:") == 1


def test_route2_fallback_to_a_newer_binary_does_not_call_it_older(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    no_exec: None,
    ran_self: list[bool],
    capsys: pytest.CaptureFixture[str],
) -> None:
    _make_adopter(tmp_path, "1.100.0")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(router, "running_version", lambda: "1.139.0")
    _patch_subprocess(monkeypatch, [_FakeCompleted(1)])

    router.main(["status"])

    err = capsys.readouterr().err
    assert "OLDER" not in err
    assert "Running 1.139.0 instead" in err


def test_route2_fallback_notice_is_said_once_per_command(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    no_exec: None,
    ran_self: list[bool],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A `pkit` subprocess of the degraded command inherits its environment and
    does not repeat the notice; it still probes the pin, as routing is unchanged."""
    _make_adopter(tmp_path, "1.150.0")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(router, "running_version", lambda: "1.149.0")
    calls = _patch_subprocess(monkeypatch, [_FakeCompleted(1), _FakeCompleted(1)])

    router.main(["pm", "open-pr"])  # the command the operator ran
    router.main(["friction", "check"])  # a `pkit` call it makes, same environment

    assert ran_self == [True, True]
    assert len(calls) == 2  # each probed the pin
    assert capsys.readouterr().err.count("pkit:") == 1
    assert os.environ[router._PIN_UNRESOLVED_ENV] == "1.150.0"


@pytest.mark.parametrize(
    ("version", "than", "older"),
    [
        ("1.149.0", "1.150.0", True),
        ("1.150.0", "1.150.0", False),
        ("1.151.0", "1.150.0", False),
        ("1.9.0", "1.10.0", True),  # numeric, not lexical
        ("1.149", "1.150.0", False),  # not MAJOR.MINOR.PATCH: no order claimed
        ("1.149.0", "main", False),
        ("1.149.0rc1", "1.150.0", False),
    ],
)
def test_is_older_release_orders_only_bare_releases(version: str, than: str, older: bool) -> None:
    assert router._is_older_release(version, than) is older


# --- run_bypassed: bootstrap the pin raise with routing truly off ---------------


def test_run_bypassed_sets_no_route_and_clears_loop_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """run_bypassed's child runs TRULY non-routed: PKIT_NO_ROUTE set and the loop
    guard PKIT_ROUTED cleared. Called from an already-routed child (the pinned
    case), a leaked PKIT_ROUTED would make the bootstrapped grandchild re-detect
    itself as the routed pinned child and sync NOTHING while the outer reconcile
    still flipped the pin — pin-ahead-of-content corruption (ADR-049)."""
    monkeypatch.setenv(router._LOOP_GUARD_ENV, "1")  # we are an already-routed child
    calls = _patch_subprocess(monkeypatch, [_FakeCompleted(0)])

    rc = router.run_bypassed("2.0.0", ["upgrade"])

    assert rc == 0
    env = calls[0]["kwargs"]["env"]
    assert env[router._BYPASS_ENV] == "1"  # routing bypassed
    assert router._LOOP_GUARD_ENV not in env  # loop guard NOT leaked into the child
    cmd = calls[0]["cmd"]
    assert f"{router.DISTRIBUTION_GIT_URL}@v2.0.0" in cmd
    assert cmd[-1] == "upgrade"


# --- Route 3: match / no pin / not-in-project → run self ------------------------


def test_route3_runs_self_on_version_match(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, no_exec: None, ran_self: list[bool]
) -> None:
    _make_adopter(tmp_path, "1.139.0")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv(router._CLI_VERSION_ENV, raising=False)
    monkeypatch.setattr(router, "running_version", lambda: "1.139.0")
    ran = _patch_subprocess(monkeypatch, [])  # nothing should be spawned

    router.main(["status"])

    assert ran_self == [True]
    assert ran == []
    # Route 3 (match) leaves the CLI version unstamped — metadata is accurate.
    assert router._CLI_VERSION_ENV not in os.environ


def test_route3_runs_self_when_adopter_has_no_pin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, no_exec: None, ran_self: list[bool]
) -> None:
    (tmp_path / ".git").mkdir()
    (tmp_path / ".pkit").mkdir()  # a project, but no version-pin directive
    monkeypatch.chdir(tmp_path)

    router.main(["status"])

    assert ran_self == [True]


# --- Loop guard + bypass -------------------------------------------------------


def test_loop_guard_suppresses_routing_even_in_source_checkout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, no_exec: None, ran_self: list[bool]
) -> None:
    _make_source_checkout(tmp_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv(router._LOOP_GUARD_ENV, "1")

    router.main(["version"])  # would be route 1 without the guard

    assert ran_self == [True]  # guard forces run-self, no exec


def test_bypass_env_suppresses_routing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, no_exec: None, ran_self: list[bool]
) -> None:
    _make_source_checkout(tmp_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv(router._BYPASS_ENV, "1")

    router.main(["version"])

    assert ran_self == [True]


@pytest.mark.parametrize("value", ["1", "true", "TRUE", "yes"])
def test_env_true_accepts_truthy(value: str) -> None:
    assert router._env_true({"X": value}, "X") is True


@pytest.mark.parametrize("value", ["", "0", "false", "no", "off"])
def test_env_true_rejects_falsey(value: str) -> None:
    assert router._env_true({"X": value}, "X") is False


# --- Route 3 hand-off actually reaches the CLI ---------------------------------


def test_run_self_invokes_cli_main(monkeypatch: pytest.MonkeyPatch) -> None:
    """The route-3 hand-off calls the real CLI group with prog_name=pkit — i.e.
    every existing command still runs through the router's fall-through."""
    import project_kit.cli as cli_mod

    seen: dict[str, object] = {}
    monkeypatch.setattr(cli_mod, "main", lambda **kw: seen.update(kw))
    router._run_self()
    assert seen == {"prog_name": "pkit"}
