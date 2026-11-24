"""The probe of ADR-095's facts a person runs (ADR-095 point 6).

`probe-hook-out-of-reach.py` is a script, never a test: a person runs it and it
starts real Claude Code sessions. These guards hold what they can of it without
starting anything: that it refuses without its flag, that it parses and imports
where the runner it borrows from runs, and that it reads a file as written only
where a write landed.
"""

from __future__ import annotations

import ast
import importlib.util
import os
import sys
from pathlib import Path
from types import ModuleType

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
PROBE = REPO_ROOT / ".pkit" / "adapters" / "claude-code" / "probe-hook-out-of-reach.py"
TOKEN = "0123456789abcdef"


def _load(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def probe() -> ModuleType:
    return _load(PROBE, "claude_code_adr095_probe_under_test")


def test_the_probe_starts_nothing_without_its_flag(
    probe: ModuleType, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def no_folder(*_args: object, **_kwargs: object) -> str:
        raise AssertionError("the probe made a folder or started a process")

    monkeypatch.setattr(probe.tempfile, "mkdtemp", no_folder)
    monkeypatch.setattr(probe.subprocess, "run", no_folder)
    assert probe.main([]) == probe.REFUSED
    assert "--start-claude" in capsys.readouterr().err


def test_the_probe_parses_as_python_3_9_and_imports_only_the_standard_library() -> None:
    """It borrows the runner's helpers, so it runs where the runner runs."""
    text = PROBE.read_text(encoding="utf-8")
    tree = ast.parse(text, feature_version=(3, 9))
    imported = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        (node.module or "").split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    assert imported <= set(sys.stdlib_module_names)
    assert text.startswith("#!/usr/bin/env python3\n")
    assert os.access(PROBE, os.X_OK)


@pytest.mark.parametrize(
    ("written", "verdict"),
    [
        (frozenset(), "inconclusive"),
        (frozenset({"control"}), "holds"),
        (frozenset({"control", "nested"}), "holds"),
        (frozenset({"control", "settings"}), "disproved"),
        (frozenset({"control", "symlink"}), "disproved"),
        (frozenset({"control", "escape"}), "inconclusive"),
    ],
)
def test_a_file_reads_as_reached_only_where_a_write_landed(
    probe: ModuleType, tmp_path: Path, written: frozenset[str], verdict: str
) -> None:
    """Each target starts without the run's token, so the verdict follows what
    the session wrote, not the seed (#3429: every row read as reached)."""
    scratch = probe.make_scratch(tmp_path)
    assert not [t.name for t in scratch["targets"] if probe.reached(t, TOKEN)]
    for target in scratch["targets"]:
        if target.group in written:
            with target.check.open("ab") as handle:
                handle.write(TOKEN.encode())
    result = probe.read_precondition(scratch, {"ended": "finished"}, TOKEN)
    assert result["verdict"] == verdict
    landed = {name for name, reached in result["found"].items() if reached}
    assert landed == {name for name, group in result["group"].items() if group in written}
