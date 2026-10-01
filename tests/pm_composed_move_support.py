"""The process engine and `move-issue` as start-work and review-work meet them (#1242).

Both verbs ask the process engine where the issue is
(`_lib/issue_position.ask_engine`, a `pkit process status --json` run), then
run `move-issue` as a child process (`_lib/composed_move.invoke_move_issue`),
which asks the engine again when it moves. `FakeEngine` answers those asks in
turn, so a test can move the issue between the verb's check and the move.
`MoveIssueInProcess` stands in for the child: it runs move-issue's own
`main()` here, on the child's arguments.
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
    """`pkit process status --json`, answering each ask with the next answer.

    An answer is a status payload, printed as JSON with exit 0, or None: the
    engine gives nothing, exiting 1 with a line on stderr. The last answer
    repeats. `asks` holds the argv of each ask."""

    def __init__(self, *answers: dict[str, Any] | None) -> None:
        self.answers: list[dict[str, Any] | None] = list(answers) or [None]
        self.asks: list[list[str]] = []

    def install(self, monkeypatch: pytest.MonkeyPatch, issue_position: ModuleType) -> None:
        """Answer every engine ask `issue_position` makes in this test."""
        monkeypatch.setattr(issue_position, "subprocess", SimpleNamespace(run=self.run))

    def run(self, argv: list[str], **_kw: Any) -> subprocess.CompletedProcess[str]:
        assert argv[:3] == ["pkit", "process", "status"], argv
        answer = self.answers[min(len(self.asks), len(self.answers) - 1)]
        self.asks.append(list(argv))
        if answer is None:
            return subprocess.CompletedProcess(argv, 1, "", "Error: no engine in this test\n")
        return subprocess.CompletedProcess(argv, 0, json.dumps(answer), "")


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
    its hooks are silent; the engine answers whatever `issue_position` is
    given (a `FakeEngine`). It makes no write: a move that gets as far as a
    `gh` call or a label write fails the test. `runs` holds each command."""

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
