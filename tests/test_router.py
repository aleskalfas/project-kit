"""Tests for the `pkit` entry-point router (ADR-039).

The router runs on *every* `pkit` invocation and decides which process serves
the command before the heavy CLI is imported. These tests cover each of the
three routes, graceful degradation on an unresolvable pin, the loop guard, the
bypass env, and that a normal (route-3) invocation still reaches the CLI.

Exec / subprocess seams are patched so no process is actually replaced or
spawned; the routing *decision* is what is under test.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from project_kit import router


class _ExecCalled(Exception):
    """Sentinel raised in place of `os.execv`, which would replace the process."""

    def __init__(self, path: str, argv: tuple[str, ...]) -> None:
        super().__init__(path)
        self.path = path
        self.argv = argv


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


def _make_source_checkout(root: Path, *, dispatcher_executable: bool = True) -> Path:
    """Materialise the minimal markers of a project-kit source checkout."""
    (root / "src" / "project_kit").mkdir(parents=True)
    (root / "src" / "project_kit" / "__init__.py").write_text("", encoding="utf-8")
    (root / ".git").mkdir()
    cli_dir = root / ".pkit" / "cli"
    cli_dir.mkdir(parents=True)
    dispatcher = cli_dir / "pkit"
    dispatcher.write_text("#!/usr/bin/env bash\n", encoding="utf-8")
    dispatcher.chmod(0o755 if dispatcher_executable else 0o644)
    return dispatcher


def _make_adopter(root: Path, version: str) -> None:
    """Materialise an adopter project pinning `version` via `.pkit/VERSION`."""
    (root / ".git").mkdir()
    pkit = root / ".pkit"
    pkit.mkdir()
    (pkit / "VERSION").write_text(version + "\n", encoding="utf-8")


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


def test_is_source_checkout_true_only_with_package_source(tmp_path: Path) -> None:
    _make_source_checkout(tmp_path)
    assert router._is_source_checkout(tmp_path) is True


def test_is_source_checkout_false_for_adopter(tmp_path: Path) -> None:
    _make_adopter(tmp_path, "1.100.0")
    (tmp_path / ".pkit" / "cli").mkdir()
    (tmp_path / ".pkit" / "cli" / "pkit").write_text("", encoding="utf-8")
    # Has the dispatcher, but no src/project_kit → not a source checkout.
    assert router._is_source_checkout(tmp_path) is False


def test_resolve_pin_reads_version(tmp_path: Path) -> None:
    _make_adopter(tmp_path, "1.100.0")
    assert router._resolve_pin(tmp_path) == "1.100.0"


def test_resolve_pin_none_when_absent(tmp_path: Path) -> None:
    (tmp_path / ".pkit").mkdir()
    assert router._resolve_pin(tmp_path) is None


def test_pinned_base_is_git_tag_pin(tmp_path: Path) -> None:
    base = router._pinned_base("1.100.0")
    assert base[0] == "uvx"
    assert "--from" in base
    assert f"{router._DISTRIBUTION_GIT_URL}@v1.100.0" in base
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


# --- Route 2: pin mismatch → re-exec the pinned wheel --------------------------


class _FakeCompleted:
    def __init__(self, returncode: int) -> None:
        self.returncode = returncode


def _patch_subprocess(
    monkeypatch: pytest.MonkeyPatch, results: list[object]
) -> list[dict[str, object]]:
    """Patch `router.subprocess.run` to return/raise `results` in order,
    recording each call. A result that is an Exception is raised."""
    calls: list[dict[str, object]] = []
    it = iter(results)

    def fake_run(cmd, **kwargs):  # type: ignore[no-untyped-def]
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
    monkeypatch.setattr(router, "_running_version", lambda: "1.139.0")
    # Probe resolves (rc 0), then the real command exits 3.
    calls = _patch_subprocess(monkeypatch, [_FakeCompleted(0), _FakeCompleted(3)])

    with pytest.raises(SystemExit) as excinfo:
        router.main(["validate"])

    assert excinfo.value.code == 3
    assert ran_self == []  # ran the pinned command, not self
    # Two invocations: the --version probe, then the real command.
    assert len(calls) == 2
    probe_cmd = calls[0]["cmd"]
    real_cmd = calls[1]["cmd"]
    assert probe_cmd[-1] == "--version"
    assert f"{router._DISTRIBUTION_GIT_URL}@v1.100.0" in real_cmd
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
    monkeypatch.setattr(router, "_running_version", lambda: "1.139.0")
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
    monkeypatch.setattr(router, "_running_version", lambda: "1.139.0")
    _patch_subprocess(monkeypatch, [FileNotFoundError("uvx")])

    router.main(["status"])

    assert ran_self == [True]
    assert "could not be resolved" in capsys.readouterr().err


# --- Route 3: match / no pin / not-in-project → run self ------------------------


def test_route3_runs_self_on_version_match(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, no_exec: None, ran_self: list[bool]
) -> None:
    _make_adopter(tmp_path, "1.139.0")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(router, "_running_version", lambda: "1.139.0")
    ran = _patch_subprocess(monkeypatch, [])  # nothing should be spawned

    router.main(["status"])

    assert ran_self == [True]
    assert ran == []


def test_route3_runs_self_when_adopter_has_no_pin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, no_exec: None, ran_self: list[bool]
) -> None:
    (tmp_path / ".git").mkdir()
    (tmp_path / ".pkit").mkdir()  # a project, but no VERSION file
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
