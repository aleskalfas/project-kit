"""The process engine and `move-issue` as start-work and review-work meet them (#1242).

Both verbs check, before they change anything, that their move is legal from
the state the issue's labels and milestone give (`_lib/issue_position`); that
check starts no `pkit` run. They then run `move-issue` as a child process
(`_lib/composed_move.invoke_move_issue`), which asks the process engine itself
when it moves. `FakeEngine` answers every `pkit process status` the code under
test starts and records every `pkit` run, so a test can tell who asked.
`MoveIssueInProcess` stands in for the child: it runs move-issue's own `main()`
here, on the child's arguments.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest

SCRIPTS_DIR = (
    Path(__file__).resolve().parent.parent / ".pkit" / "capabilities" / "project-management"
) / "scripts"
CAPABILITY_ROOT = SCRIPTS_DIR.parent


def status_at(state: str) -> dict[str, Any]:
    """An engine status payload placing the issue in `state`."""
    return {"position": {"state": state, "indeterminate": False}, "journal": []}


class FakeEngine:
    """`pkit process status --json`, wherever the code under test starts it.

    Installed over `subprocess.run`: each `pkit process status` prints `status`
    as JSON with exit 0, or, when `status` is None, exits 1 with a line on
    stderr (the engine gives nothing). Any other `pkit` run fails the test, and
    every other command runs as it would. `asks` holds the argv of each `pkit`
    run."""

    def __init__(self, status: dict[str, Any] | None = None) -> None:
        self.status = status
        self.asks: list[list[str]] = []
        self._run = subprocess.run

    def install(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Answer every `pkit` run the test's code starts."""
        monkeypatch.setattr(subprocess, "run", self.run)

    def run(self, argv: Any, *args: Any, **kw: Any) -> Any:
        if not isinstance(argv, (list, tuple)) or not argv or argv[0] != "pkit":
            return self._run(argv, *args, **kw)
        self.asks.append([str(a) for a in argv])
        assert list(argv[1:3]) == ["process", "status"], argv
        if self.status is None:
            return subprocess.CompletedProcess(argv, 1, "", "Error: no engine in this test\n")
        return subprocess.CompletedProcess(argv, 0, json.dumps(self.status), "")


def load_move_issue() -> ModuleType:
    """move-issue.py as a module, loaded once per test session."""
    name = "pm_move_issue_in_process"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, SCRIPTS_DIR / "move-issue.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class MoveIssueInProcess:
    """Stands in for the `move-issue` child a composing verb starts.

    `run` takes the child's command and runs move-issue's `main()` here on its
    arguments, against `issue` as its fetch returns it at move time. Its
    membership, session and bootstrap gates pass, no board carries state, and
    its hooks are silent; its engine read meets whatever answers
    `subprocess.run` (a `FakeEngine`). It makes no write: a move that gets as
    far as a `gh` call or a label write fails the test. `runs` holds each
    command."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch, issue: dict[str, Any]) -> None:
        mi = load_move_issue()
        invoker = SimpleNamespace(github_login="me", email="me@example.com")
        monkeypatch.setattr(mi, "resolve_capability_root", lambda _arg: CAPABILITY_ROOT)
        monkeypatch.setattr(mi, "_read_members", lambda *_a: [])
        monkeypatch.setattr(mi, "resolve_invoker_identity", lambda config=None: invoker)
        monkeypatch.setattr(mi, "check_membership", lambda *_a: SimpleNamespace(allowed=True))
        monkeypatch.setattr(mi.session_guard, "enforce", lambda **_kw: True)
        monkeypatch.setattr(mi.bootstrap_gate, "enforce", lambda *_a, **_kw: True)
        monkeypatch.setattr(mi.axis_carriage, "is_board_carried", lambda *_a, **_kw: False)
        monkeypatch.setattr(mi, "_gh_get_issue", lambda _n, _config: issue)
        monkeypatch.setattr(mi, "gh_run", _no_write)
        monkeypatch.setattr(mi, "_gh_apply_state_label", _no_write)
        monkeypatch.setattr(mi, "fire_hooks", lambda *_a, **_kw: None)
        self.module = mi
        self.runs: list[list[str]] = []

    def run(self, cmd: list[str], **_kw: Any) -> subprocess.CompletedProcess[str]:
        self.runs.append(list(cmd))
        assert cmd[1].endswith("move-issue.py"), cmd
        saved = sys.argv
        sys.argv = ["move-issue.py", *cmd[2:]]
        try:
            rc = self.module.main()
        finally:
            sys.argv = saved
        return subprocess.CompletedProcess(cmd, rc)


def _no_write(*args: Any, **_kw: Any) -> Any:
    raise AssertionError(f"move-issue wrote: {args}")
