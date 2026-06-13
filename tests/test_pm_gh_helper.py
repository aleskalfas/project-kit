"""Tests for project-management's shared `gh` shell-out helper.

The library lives at `.pkit/capabilities/project-management/scripts/_lib/gh.py`
— capability-internal, per DEC-023. These tests load it via `importlib`
so the kit's pytest run catches regressions in the contract every pm
script depends on for `gh` routing.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
GH_PY = (
    REPO_ROOT
    / ".pkit"
    / "capabilities"
    / "project-management"
    / "scripts"
    / "_lib"
    / "gh.py"
)


@pytest.fixture(scope="module")
def gh():
    """Load the capability-internal gh helper by file path."""
    module_name = "pm_gh_under_test"
    spec = importlib.util.spec_from_file_location(module_name, GH_PY)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


# --- gh_env --------------------------------------------------------------


def test_gh_env_without_gh_block_returns_environ_copy(gh) -> None:
    """No gh block in config → env is a copy of os.environ unchanged."""
    env = gh.gh_env({})
    assert env == dict(os.environ)
    # It's a copy, not the same dict.
    assert env is not os.environ


def test_gh_env_with_host_sets_gh_host(gh) -> None:
    """gh.host configured → GH_HOST is overridden in the returned env."""
    config = {"gh": {"host": "github.com"}}
    env = gh.gh_env(config)
    assert env["GH_HOST"] == "github.com"


def test_gh_env_config_wins_over_ambient_gh_host(
    gh, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Per DEC-023: when both ambient GH_HOST and gh.host are set, config wins."""
    monkeypatch.setenv("GH_HOST", "ambient.example.com")
    config = {"gh": {"host": "config.example.com"}}
    env = gh.gh_env(config)
    assert env["GH_HOST"] == "config.example.com"


def test_gh_env_without_host_preserves_ambient_gh_host(
    gh, monkeypatch: pytest.MonkeyPatch
) -> None:
    """gh.host absent + ambient GH_HOST present → ambient passes through."""
    monkeypatch.setenv("GH_HOST", "ambient.example.com")
    env = gh.gh_env({"gh": {}})
    assert env["GH_HOST"] == "ambient.example.com"


def test_gh_env_with_null_gh_block_is_safe(gh) -> None:
    """`gh: null` in YAML parses as None — treated as absent, no crash."""
    env = gh.gh_env({"gh": None})
    # No GH_HOST override — whatever ambient says, passes through.
    assert env == dict(os.environ)


def test_gh_env_empty_string_host_is_ignored(gh) -> None:
    """An empty `host:` value isn't a meaningful override; ignore it."""
    config = {"gh": {"host": ""}}
    env = gh.gh_env(config)
    # GH_HOST shouldn't be set from the empty config value.
    # (If ambient has GH_HOST, it passes through; we don't assert that here.)
    if "GH_HOST" in env:
        # If present, it's only because ambient set it — not the empty config.
        assert env["GH_HOST"] != ""


# --- gh_owner_flag -------------------------------------------------------


def test_gh_owner_flag_with_default_owner(gh) -> None:
    """gh.default_owner configured → ['--owner', <name>]."""
    config = {"gh": {"default_owner": "ai-platform-incubation"}}
    assert gh.gh_owner_flag(config) == ["--owner", "ai-platform-incubation"]


def test_gh_owner_flag_without_default_owner(gh) -> None:
    """No default_owner → empty list (no flag spliced)."""
    assert gh.gh_owner_flag({}) == []
    assert gh.gh_owner_flag({"gh": {}}) == []


def test_gh_owner_flag_with_null_gh_block(gh) -> None:
    """`gh: null` is treated as absent — no owner flag."""
    assert gh.gh_owner_flag({"gh": None}) == []


def test_gh_owner_flag_empty_string_owner_is_ignored(gh) -> None:
    """An empty `default_owner:` value isn't a meaningful override."""
    assert gh.gh_owner_flag({"gh": {"default_owner": ""}}) == []


# --- gh_run --------------------------------------------------------------


def test_gh_run_threads_env_dict(gh, monkeypatch: pytest.MonkeyPatch) -> None:
    """`gh_run` should pass `env=gh_env(config)` to subprocess.run."""
    captured: dict = {}

    def fake_run(args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    config = {"gh": {"host": "github.com"}}
    gh.gh_run(["gh", "api", "user"], config)

    assert captured["args"] == ["gh", "api", "user"]
    assert captured["kwargs"]["env"]["GH_HOST"] == "github.com"


def test_gh_run_defaults_text_and_capture_output(
    gh, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`gh_run` should default `text=True` and `capture_output=True`."""
    captured: dict = {}

    def fake_run(args, **kwargs):
        captured["kwargs"] = kwargs
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    gh.gh_run(["gh", "api", "user"], {})

    assert captured["kwargs"]["text"] is True
    assert captured["kwargs"]["capture_output"] is True


def test_gh_run_respects_caller_kwargs(gh, monkeypatch: pytest.MonkeyPatch) -> None:
    """Caller-passed kwargs override defaults (text, capture_output, env)."""
    captured: dict = {}

    def fake_run(args, **kwargs):
        captured["kwargs"] = kwargs
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    custom_env = {"FOO": "bar"}
    gh.gh_run(
        ["gh", "api", "user"],
        {"gh": {"host": "ignored.com"}},
        env=custom_env,
        text=False,
        capture_output=False,
    )

    assert captured["kwargs"]["env"] == custom_env
    assert captured["kwargs"]["text"] is False
    assert captured["kwargs"]["capture_output"] is False
