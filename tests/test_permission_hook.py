"""End-to-end tests for the claude-code PreToolUse hook script.

Drives the real `.pkit/adapters/claude-code/permission-hook.py` as a subprocess
the way Claude Code does — payload on stdin, decision JSON on stdout, exit 0 —
against a constructed adopter tree. Proves the live wiring (allow / deny /
abstain) and the fail-open guarantee end to end, complementing the decision-core
conformance fixtures (which prove the logic in-process).
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
HOOK = REPO / ".pkit" / "adapters" / "claude-code" / "permission-hook.py"


def _tree(tmp_path: Path, *, grants: str | None = None, config: str | None = None,
          decide: bool = True) -> Path:
    root = tmp_path / "proj"
    (root / ".pkit" / "schemas").mkdir(parents=True)
    shutil.copy(REPO / ".pkit" / "schemas" / "privilege-catalog.yaml",
                root / ".pkit" / "schemas" / "privilege-catalog.yaml")
    (root / ".pkit" / "permissions").mkdir(parents=True)
    if decide:
        shutil.copy(REPO / ".pkit" / "permissions" / "decide.py",
                    root / ".pkit" / "permissions" / "decide.py")
    if grants is not None or config is not None:
        (root / ".pkit" / "permissions" / "project").mkdir(parents=True)
        if grants is not None:
            (root / ".pkit" / "permissions" / "project" / "grants.yaml").write_text(grants)
        if config is not None:
            (root / ".pkit" / "permissions" / "project" / "config.yaml").write_text(config)
    return root


def _invoke(root: Path, payload: dict) -> tuple[int, dict | None]:
    """Run the hook with `payload` on stdin; return (exit_code, parsed stdout
    or None when the hook abstained with no output)."""
    proc = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env={"CLAUDE_PROJECT_DIR": str(root), "PATH": __import__("os").environ["PATH"]},
    )
    assert proc.returncode == 0, proc.stderr  # always fail-open / exit 0
    out = proc.stdout.strip()
    return proc.returncode, (json.loads(out) if out else None)


def _decision(parsed: dict | None) -> str | None:
    if parsed is None:
        return None
    return parsed["hookSpecificOutput"]["permissionDecision"]


def test_hook_denies_guardrail(tmp_path):
    root = _tree(tmp_path)
    _, parsed = _invoke(root, {"tool_name": "Bash", "tool_input": {"command": "sudo rm x"},
                               "cwd": str(root)})
    assert _decision(parsed) == "deny"
    assert parsed["hookSpecificOutput"]["hookEventName"] == "PreToolUse"


def test_hook_allows_granted_privilege(tmp_path):
    root = _tree(tmp_path, grants=(
        "schema_version: 1\n"
        "grants:\n"
        "  - subject: operator\n"
        "    privilege: \"[privilege-catalog:vcs]\"\n"
        "    effect: allow\n"
    ))
    _, parsed = _invoke(root, {"tool_name": "Bash", "tool_input": {"command": "git status"},
                               "cwd": str(root)})
    assert _decision(parsed) == "allow"


def test_hook_abstains_on_unmodeled_lenient(tmp_path):
    root = _tree(tmp_path)  # no grants → operator gh is unmodeled, lenient default
    _, parsed = _invoke(root, {"tool_name": "Bash", "tool_input": {"command": "gh pr list"},
                               "cwd": str(root)})
    assert parsed is None  # abstain = no stdout, defer to normal flow


def test_hook_denies_unmodeled_strict(tmp_path):
    root = _tree(tmp_path, config="schema_version: 1\nposture: strict\n")
    _, parsed = _invoke(root, {"tool_name": "Bash", "tool_input": {"command": "gh pr list"},
                               "cwd": str(root)})
    assert _decision(parsed) == "deny"


def test_hook_subagent_subject(tmp_path):
    root = _tree(tmp_path, grants=(
        "schema_version: 1\n"
        "grants:\n"
        "  - subject: agent:critic\n"
        "    privilege: \"[privilege-catalog:web-fetch]\"\n"
        "    effect: allow\n"
    ))
    _, parsed = _invoke(root, {"tool_name": "WebFetch", "tool_input": {"url": "https://x"},
                               "cwd": str(root), "agent_type": "critic"})
    assert _decision(parsed) == "allow"


def test_hook_fails_open_on_malformed_payload(tmp_path):
    root = _tree(tmp_path)
    _, parsed = _invoke(root, {"garbage": True})
    assert parsed is None  # fail open → abstain


def test_hook_fails_open_when_decision_core_missing(tmp_path):
    root = _tree(tmp_path, decide=False)  # broken adopter tree
    _, parsed = _invoke(root, {"tool_name": "Bash", "tool_input": {"command": "sudo rm x"},
                               "cwd": str(root)})
    assert parsed is None  # config fault never silently blocks
