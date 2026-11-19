"""The probe of ADR-095's facts a person runs (ADR-095 point 6).

`probe-hook-out-of-reach.py` is a script, never a test: a person runs it and it
starts real Claude Code sessions. These guards hold what they can of it without
starting anything — that it refuses without its flag, and that it parses and
imports where the runner it borrows from runs.
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


def _load(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_probe_starts_nothing_without_its_flag(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    probe = _load(PROBE, "claude_code_adr095_probe_under_test")

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
