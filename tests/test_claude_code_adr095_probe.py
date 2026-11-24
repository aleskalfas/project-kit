"""The probe of ADR-095's facts a person runs (ADR-095 point 6).

`probe-hook-out-of-reach.py` is a script, never a test: a person runs it and it
starts real Claude Code sessions. These guards hold what they can of it without
starting anything: that it refuses without its flag, that it parses and imports
where the runner it borrows from runs, that it reads a file as written only
where a write landed, and that the folder and scripts it makes for the person's
interactive session act only in that folder and leave there what the probe reads.
"""

from __future__ import annotations

import ast
import importlib.util
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

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


@pytest.fixture
def terminal(probe: ModuleType, tmp_path: Path) -> Any:
    # A space in the path holds every command the person types to its quoting.
    return probe.make_terminal(tmp_path / "a probe root", TOKEN)


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


def test_the_marks_script_reports_each_mark_apart_and_tells_unset_from_empty(
    probe: ModuleType, terminal: Any
) -> None:
    """macOS's `printenv` reads only its first name, so the probe has no
    command name several (#3429)."""
    env = {k: v for k, v in os.environ.items() if k not in probe.MARKS}
    env |= {"CLAUDECODE": "1", "CLAUDE_CODE_CHILD_SESSION": ""}
    subprocess.run(["sh", str(terminal.marks), "shell-mode"], env=env, check=True)
    marks = probe.read_marks(terminal.marks_file("shell-mode"))
    assert marks == {"CLAUDE_PROJECT_DIR": None, "CLAUDECODE": "1", "CLAUDE_CODE_CHILD_SESSION": ""}
    assert probe.describe_marks(marks) == (
        "CLAUDE_PROJECT_DIR unset, CLAUDECODE='1', CLAUDE_CODE_CHILD_SESSION set and empty"
    )


def test_the_reset_the_person_types_acts_only_in_the_probes_folder_whose_settings_deny_it(
    probe: ModuleType, terminal: Any, tmp_path: Path
) -> None:
    """The command is pinned to the probe's folder, so typed in any other
    session it still discards nothing but the probe's change (#3429: it was
    typed in a worktree of this repository)."""
    settings = json.loads((terminal.folder / ".claude" / "settings.json").read_text())
    assert settings["permissions"]["deny"] == [probe.RESET_DENY]
    assert settings["sandbox"]["enabled"] is True
    step = next(s for s in probe.terminal_steps(terminal) if s.key == "shell-mode-seen")
    typed = next(line.strip() for line in step.lines if probe.RESET in line)
    assert typed == f"!cd {shlex.quote(str(terminal.folder))} && {probe.RESET}"

    assert probe.reset_ran(terminal.tracked) is False
    subprocess.run(["sh", "-c", typed[1:]], cwd=tmp_path, check=True, capture_output=True)
    assert probe.reset_ran(terminal.tracked) is True


def test_the_stand_in_hook_logs_each_call_for_the_probe_to_read(
    probe: ModuleType, terminal: Any
) -> None:
    settings = json.loads((terminal.folder / ".claude" / "settings.json").read_text())
    (entry,) = settings["hooks"]["PreToolUse"]
    command = entry["hooks"][0]["command"]
    for call in (
        {"tool_name": "Bash", "tool_input": {"command": "git status"}},
        {"tool_name": "Read", "tool_input": {"file_path": "/x"}},
    ):
        subprocess.run(["sh", "-c", command], input=json.dumps(call).encode(), check=True)
    assert probe.read_calls(terminal.hook_log) == [
        {"tool": "Bash", "command": "git status"},
        {"tool": "Read", "command": None},
    ]


def test_every_script_the_person_runs_parses_as_sh(terminal: Any) -> None:
    hook = terminal.folder / ".claude" / "hooks" / "log-call.sh"
    for script in (terminal.marks, terminal.multiplexer, hook):
        subprocess.run(["sh", "-n", str(script)], check=True)


def test_the_multiplexer_finding_reads_what_its_script_left(
    probe: ModuleType, terminal: Any
) -> None:
    (terminal.folder / "multiplexer.txt").write_text(
        "multiplexer=tmux\nserver_already_running=no\nstarted=yes\n"
    )
    terminal.marks_file("multiplexer").write_text(
        "CLAUDE_PROJECT_DIR unset\nCLAUDECODE=1\nCLAUDE_CODE_CHILD_SESSION unset\n"
    )
    found = probe.read_multiplexer(terminal, [])
    assert found["marks"] == {
        "CLAUDE_PROJECT_DIR": None,
        "CLAUDECODE": "1",
        "CLAUDE_CODE_CHILD_SESSION": None,
    }
    assert "its server started by this command" in found["line"]
