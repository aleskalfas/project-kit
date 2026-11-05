"""The Claude Code adapter's workspace sentence, where it reaches an agent (#2026).

The harness's environment note tells every session and subagent to keep
temporary files in a session scratch directory outside the repository. The
adapter answers it with one sentence, where the note arrives. These tests hold
its delivery, not an agent's obedience.

- **The start hook** (`session-start-hook.py`) answers `SessionStart` and
  `SubagentStart` with the sentence as `additionalContext`, under the event's
  own name. It gives nothing, and exits 0, on any other event or a payload it
  cannot read.
- **Its runtime** is the bare system python3, with no PEP 723 metadata, as the
  permission hook's is. Git tracks it executable, and the command the baseline
  registers starts it.
- **The registration.** The baseline settings register the hook for both
  events, and the merge carries both into `.claude/settings.json` beside a
  `PreToolUse` hook already there.
- **The agent bodies.** The resolver's sentence is the hook's, and every agent
  the deploy wrote into this repository ends with it.
"""

from __future__ import annotations

import ast
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
ADAPTER = REPO / ".pkit" / "adapters" / "claude-code"
HOOK = ADAPTER / "session-start-hook.py"
RESOLVER = ADAPTER / "_resolve_agent.py"
BASELINE = ADAPTER / "settings" / "core" / "settings.json"
MERGE = ADAPTER / "merge-settings.sh"
DEPLOYED = REPO / ".claude" / "agents"
MARKER = "# managed-by: project-kit (deploy-agents.sh)"

EVENTS = ("SessionStart", "SubagentStart")


def _constant(path: Path, name: str) -> str:
    """The string a module-level assignment of *name* in *path* holds."""
    for node in ast.parse(path.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == name for target in node.targets
        ):
            value = ast.literal_eval(node.value)
            assert isinstance(value, str)
            return value
    raise AssertionError(f"{path.name} assigns no {name}")


NOTE = _constant(HOOK, "WORKSPACE_NOTE")


def _run_hook(stdin: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(HOOK)], input=stdin, capture_output=True, text=True, check=False
    )


def _payload(event: str) -> str:
    return json.dumps(
        {
            "session_id": "abc123",
            "cwd": str(REPO),
            "hook_event_name": event,
            "agent_id": "agent-abc123",
            "agent_type": "Explore",
        }
    )


# ---- the start hook ----------------------------------------------------------


def test_the_sentence_names_the_harness_note_and_the_workspace() -> None:
    assert NOTE == (
        "The session scratch directory your environment names is replaced by "
        "`.agent-workspace/` at the repository root: keep every intermediate file there, "
        "never in that directory."
    )


@pytest.mark.parametrize("event", EVENTS)
def test_the_hook_gives_the_sentence_at_each_start(event: str) -> None:
    done = _run_hook(_payload(event))
    assert done.returncode == 0, done.stderr
    assert json.loads(done.stdout) == {
        "hookSpecificOutput": {"hookEventName": event, "additionalContext": NOTE}
    }


@pytest.mark.parametrize(
    "stdin",
    [
        _payload("PreToolUse"),
        _payload("SubagentStop"),
        json.dumps({"hook_event_name": None}),
        json.dumps({}),
        json.dumps(["SessionStart"]),
        "not json",
        "",
    ],
)
def test_the_hook_gives_nothing_elsewhere_and_never_blocks(stdin: str) -> None:
    done = _run_hook(stdin)
    assert done.returncode == 0, done.stderr
    assert done.stdout == ""


def test_the_hook_runs_under_the_bare_system_python3() -> None:
    text = HOOK.read_text(encoding="utf-8")
    assert text.splitlines()[0] == "#!/usr/bin/env python3"
    assert "# /// script" not in text


def test_git_tracks_the_hook_executable() -> None:
    done = subprocess.run(
        ["git", "ls-files", "-s", str(HOOK.relative_to(REPO))],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    )
    if not done.stdout:
        pytest.skip("the hook is not committed yet")
    assert done.stdout.startswith("100755 "), done.stdout


# ---- the registration --------------------------------------------------------


def _registered_commands(settings: dict, event: str) -> list[str]:
    return [
        hook["command"]
        for group in settings.get("hooks", {}).get(event, [])
        for hook in group.get("hooks", [])
        if hook.get("type") == "command"
    ]


@pytest.mark.parametrize("event", EVENTS)
def test_the_baseline_registers_the_hook_and_its_command_starts_it(event: str) -> None:
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    commands = [c for c in _registered_commands(baseline, event) if "session-start-hook" in c]
    assert len(commands) == 1, commands
    done = subprocess.run(
        ["bash", "-c", commands[0]],
        input=_payload(event),
        capture_output=True,
        text=True,
        check=False,
        env={"CLAUDE_PROJECT_DIR": str(REPO), "PATH": os.environ["PATH"]},
    )
    assert done.returncode == 0, done.stderr
    assert json.loads(done.stdout)["hookSpecificOutput"]["additionalContext"] == NOTE


@pytest.mark.skipif(shutil.which("jq") is None, reason="the merge runs on jq")
def test_the_merge_keeps_the_start_hooks_beside_an_existing_pre_tool_use_hook(
    tmp_path: Path,
) -> None:
    adapter = tmp_path / ".pkit" / "adapters" / "claude-code"
    (adapter / "settings" / "core").mkdir(parents=True)
    for folder in ("skills/core", "skills/project", "capabilities"):
        (tmp_path / ".pkit" / folder).mkdir(parents=True)
    shutil.copy(MERGE, adapter / "merge-settings.sh")
    shutil.copy(BASELINE, adapter / "settings" / "core" / "settings.json")
    permission_hook = {
        "matcher": "*",
        "hooks": [{"type": "command", "command": "/somewhere/permission-hook.py"}],
    }
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "settings.json").write_text(
        json.dumps({"hooks": {"PreToolUse": [permission_hook]}}), encoding="utf-8"
    )
    done = subprocess.run(
        ["bash", str(adapter / "merge-settings.sh")], capture_output=True, text=True, check=False
    )
    assert done.returncode == 0, done.stderr
    merged = json.loads((tmp_path / ".claude" / "settings.json").read_text(encoding="utf-8"))
    assert merged["hooks"]["PreToolUse"] == [permission_hook]
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    for event in EVENTS:
        assert merged["hooks"][event] == baseline["hooks"][event]


# ---- the agent bodies --------------------------------------------------------


def test_the_resolver_ends_bodies_with_the_hooks_sentence() -> None:
    assert _constant(RESOLVER, "WORKSPACE_NOTE") == NOTE


def test_every_deployed_agent_ends_with_the_sentence() -> None:
    deployed = [
        path
        for path in sorted(DEPLOYED.glob("*.md"))
        if MARKER in "\n".join(path.read_text(encoding="utf-8").splitlines()[:5])
    ]
    assert deployed, "no agent the deploy wrote"
    missing = [
        path.name
        for path in deployed
        if not path.read_text(encoding="utf-8").rstrip().endswith(NOTE)
    ]
    assert not missing, missing
