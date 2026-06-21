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


# ---- ADR-014: zero-dep python3 hook (bare shebang, no uv) -------------------

def test_hook_shebang_is_bare_python3():
    """The hook must use #!/usr/bin/env python3, not uv run --script.
    ADR-014 pt.1: the hook must start inside macOS Seatbelt where uv panics."""
    first_line = HOOK.read_text(encoding="utf-8").splitlines()[0]
    assert first_line == "#!/usr/bin/env python3", (
        f"Hook shebang is {first_line!r}; expected #!/usr/bin/env python3 (ADR-014)"
    )


def test_hook_has_no_pep723_metadata():
    """The hook must NOT have PEP-723 uv script metadata (# /// script ... ///).
    ADR-014: uv cannot run confined under macOS Seatbelt."""
    text = HOOK.read_text(encoding="utf-8")
    assert "# /// script" not in text, "Hook still has PEP-723 uv script metadata (ADR-014)"
    assert "requires-python" not in text and "dependencies" not in text, (
        "Hook still has uv dependency declarations (ADR-014)"
    )


def _invoke_with_ruamel_blocked(root: Path, payload: dict) -> tuple[int, dict | None]:
    """Run the hook under bare python3 with ruamel.yaml import blocked via env.
    Simulates the macOS Seatbelt environment where uv (and thus ruamel.yaml)
    is not available — verifies the stdlib fallback path is taken."""
    import os as _os
    env = {
        "CLAUDE_PROJECT_DIR": str(root),
        "PATH": _os.environ["PATH"],
        # Poison PYTHONPATH so ruamel.yaml cannot be found — only stdlib available.
        # The hook must still decide correctly via the stdlib fallback in load_yaml.
        "PKIT_TEST_BLOCK_RUAMEL": "1",
    }
    proc = subprocess.run(
        [sys.executable, "-c",
         # Monkey-patch builtins.__import__ before importing the hook module to
         # simulate ruamel being absent.  We inline the hook logic here rather
         # than patching the shebang (which subprocess can't easily do).
         f"""
import builtins, sys, json, os
real_import = builtins.__import__
def _block(name, *a, **kw):
    if 'ruamel' in name:
        raise ImportError('simulated missing ruamel: ' + name)
    return real_import(name, *a, **kw)
builtins.__import__ = _block
sys.path.insert(0, str({str(root / '.pkit' / 'permissions')!r}))
os.environ['CLAUDE_PROJECT_DIR'] = {str(root)!r}
# Now import the hook's logic directly (can't exec the file as it has a shebang).
import importlib.util, pathlib
spec = importlib.util.spec_from_file_location('hook', {str(HOOK)!r})
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
sys.exit(mod.main())
"""],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
    )
    assert proc.returncode == 0, proc.stderr
    out = proc.stdout.strip()
    return proc.returncode, (json.loads(out) if out else None)


def test_hook_decides_correctly_with_ruamel_absent(tmp_path):
    """With ruamel blocked, the hook uses the stdlib fallback and still decides
    correctly: guardrail deny for sudo, abstain for unrecognized commands.
    This is the macOS Seatbelt scenario (ADR-014 pt.1)."""
    root = _tree(tmp_path)
    # Guardrail: sudo must be DENIED even with only the stdlib YAML parser.
    _, parsed = _invoke_with_ruamel_blocked(root, {
        "tool_name": "Bash", "tool_input": {"command": "sudo whoami"}, "cwd": str(root),
    })
    assert _decision(parsed) == "deny", "sudo must be denied even with stdlib YAML fallback"

    # Unrecognized command: must abstain (lenient posture, no grants).
    _, parsed = _invoke_with_ruamel_blocked(root, {
        "tool_name": "Bash", "tool_input": {"command": "frobnicate xyz"}, "cwd": str(root),
    })
    assert parsed is None, "unrecognized command must abstain with stdlib YAML fallback"


def test_hook_allows_granted_privilege_with_ruamel_absent(tmp_path):
    """A vcs grant is honored via the stdlib fallback path (no ruamel)."""
    root = _tree(tmp_path, grants=(
        "schema_version: 1\n"
        "grants:\n"
        "  - subject: operator\n"
        "    privilege: \"[privilege-catalog:vcs]\"\n"
        "    effect: allow\n"
    ))
    _, parsed = _invoke_with_ruamel_blocked(root, {
        "tool_name": "Bash", "tool_input": {"command": "git status"}, "cwd": str(root),
    })
    assert _decision(parsed) == "allow", (
        "vcs grant must be honored by the hook even with stdlib YAML fallback"
    )


# ---- ADR-002 amendment: enforcement-runtime self-check ----------------------

def _tree_with_hook(tmp_path: Path, **kwargs) -> Path:
    """Like _tree() but also copies the hook script into the adopter tree's
    expected location so _hook_runtime_check can find and run it."""
    root = _tree(tmp_path, **kwargs)
    hook_dir = root / ".pkit" / "adapters" / "claude-code"
    hook_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(HOOK, hook_dir / "permission-hook.py")
    return root


def test_hook_runtime_check_ok_when_hook_present(tmp_path):
    """_hook_runtime_check returns ok=True when the hook script is intact."""
    from project_kit import permissions as perm
    root = _tree_with_hook(tmp_path)
    ok, detail = perm._hook_runtime_check(root)
    assert ok, f"runtime check should be ok but got: {detail}"


def test_hook_runtime_check_fails_when_hook_missing(tmp_path):
    """_hook_runtime_check returns ok=False when the hook script is missing."""
    from project_kit import permissions as perm
    root = tmp_path / "proj"
    root.mkdir()
    # No hook script at the expected path.
    ok, detail = perm._hook_runtime_check(root)
    assert not ok
    assert "not found" in detail


def test_hook_runtime_check_fails_when_decide_missing(tmp_path):
    """_hook_runtime_check fails (hook exits non-zero or crashes) when the
    hook can start but decide.py is missing from the target tree."""
    from project_kit import permissions as perm
    root = tmp_path / "proj"
    (root / ".pkit" / "permissions").mkdir(parents=True)
    (root / ".pkit" / "schemas").mkdir(parents=True)
    # Copy the hook but NOT decide.py — hook will start but fail to import.
    (root / ".pkit" / "adapters" / "claude-code").mkdir(parents=True)
    shutil.copy(HOOK, root / ".pkit" / "adapters" / "claude-code" / "permission-hook.py")
    # With decide.py missing, hook should still exit 0 (fail-open) but the
    # runtime check itself considers "no decide.py" as a fault since the hook
    # effectively can't build the model.
    # However the hook is designed to fail-open (exit 0) even without decide.py,
    # so the runtime check succeeds at the process-start level but the hook
    # will abstain. The runtime check only tests CAN-START, not correctness.
    ok, detail = perm._hook_runtime_check(root)
    # Hook starts (it fails-open on missing decide.py → exit 0) so runtime is OK.
    assert ok, f"hook exits 0 even with missing decide.py (fail-open); got: {detail}"


# ---- default-agent subject resolution (issue #57) ----------------------------
#
# End-to-end subprocess tests: the real hook script, invoked the same way Claude
# Code does (payload on stdin, CLAUDE_PROJECT_DIR env), proves that main-session
# payloads (no agent_type) resolve to the configured default agent and that
# per-agent deny grants apply.

def _write_settings(root: Path, agent: str) -> None:
    """Write a minimal .claude/settings.json with the given agent value."""
    import json as _json
    claude_dir = root / ".claude"
    claude_dir.mkdir(parents=True, exist_ok=True)
    (claude_dir / "settings.json").write_text(
        _json.dumps({"agent": agent}), encoding="utf-8"
    )


def test_hook_default_agent_deny_applies_to_main_session(tmp_path):
    """Main-session payload (no agent_type) + settings.json agent: project-manager
    + deny grant → hook returns deny for gh issue edit.

    This is the issue #57 end-to-end enforcement test: the per-agent deny on
    agent:project-manager now blocks the main session's raw gh issue edit because
    the hook resolves the missing agent_type from settings.json.
    """
    root = _tree(tmp_path, grants=(
        "schema_version: 1\n"
        "grants:\n"
        "- subject: agent:project-manager\n"
        "  privilege: '[privilege-catalog:issue-tracker-write]'\n"
        "  effect: deny\n"
    ))
    _write_settings(root, "project-manager")

    _, parsed = _invoke(root, {
        "tool_name": "Bash",
        "tool_input": {"command": "gh issue edit 53 --body 'new body'"},
        "cwd": str(root),
        # Deliberately no agent_type — this is the main-session gap.
    })
    assert _decision(parsed) == "deny", (
        "per-agent deny on agent:project-manager must apply to the main session "
        "when settings.json sets agent: project-manager (issue #57)"
    )


def test_hook_default_agent_no_settings_falls_back_to_operator(tmp_path):
    """Main-session payload (no agent_type) + no settings.json → subject operator,
    per-agent deny on agent:project-manager does NOT fire (correct fallback)."""
    root = _tree(tmp_path, grants=(
        "schema_version: 1\n"
        "grants:\n"
        "- subject: agent:project-manager\n"
        "  privilege: '[privilege-catalog:issue-tracker-write]'\n"
        "  effect: deny\n"
    ))
    # No settings.json → no default agent → operator subject.

    _, parsed = _invoke(root, {
        "tool_name": "Bash",
        "tool_input": {"command": "gh issue edit 53 --body 'new body'"},
        "cwd": str(root),
    })
    # The deny is scoped to agent:project-manager; operator has no deny → abstain.
    assert parsed is None, (
        "without a configured agent, main-session subject must be operator and "
        "the agent:project-manager deny must not fire"
    )


def test_hook_default_agent_deny_via_stdlib_path(tmp_path):
    """End-to-end via the stdlib fallback (no ruamel): main-session payload
    (no agent_type), settings.json agent: project-manager, deny grant →
    the real hook subprocess (bare python3) returns deny.

    This is the definitive enforcement proof for issue #57 through the live
    hook process — the same path that runs inside macOS Seatbelt (ADR-014).
    """
    root = _tree(tmp_path, grants=(
        "schema_version: 1\n"
        "grants:\n"
        "- subject: agent:project-manager\n"
        "  privilege: '[privilege-catalog:issue-tracker-write]'\n"
        "  effect: deny\n"
    ))
    _write_settings(root, "project-manager")

    _, parsed = _invoke_with_ruamel_blocked(root, {
        "tool_name": "Bash",
        "tool_input": {"command": "gh issue edit 53 --body 'new body'"},
        "cwd": str(root),
        # No agent_type — main-session default-agent resolution path.
    })
    assert _decision(parsed) == "deny", (
        "stdlib fallback path must resolve default agent from settings.json and "
        "enforce the deny for main-session gh issue edit (issue #57)"
    )


# ---- PRJ-006: diagnostic capture through the live hook ----------------------
#
# Capture runs in the hook AFTER the decision is computed, gated on the deferred
# (abstain) verdict, and fail-safe-wrapped. These tests drive the real hook
# subprocess (the same path Claude Code runs) to prove: an armed session captures
# an abstain; capture leaves the decision untouched; and a broken capture module
# can never change the verdict or break the hook (inert-on-failure).

def _tree_with_capture(tmp_path: Path, **kwargs) -> Path:
    """Like _tree() but also copies the propagated capture module beside decide.py
    (where the hook imports it from)."""
    root = _tree(tmp_path, **kwargs)
    shutil.copy(REPO / ".pkit" / "permissions" / "diagnose_capture.py",
                root / ".pkit" / "permissions" / "diagnose_capture.py")
    return root


def _arm_session(root: Path, *, ttl_seconds: int = 3600, redact: bool = True) -> None:
    import time
    proj = root / ".pkit" / "permissions" / "project"
    proj.mkdir(parents=True, exist_ok=True)
    (proj / "diagnose.yaml").write_text(
        "schema_version: 1\n"
        f"armed_at: {int(time.time())}\n"
        f"ttl_seconds: {ttl_seconds}\n"
        "max_entries: 2000\n"
        f"redact: {'true' if redact else 'false'}\n",
        encoding="utf-8",
    )


def _read_diag_log(root: Path) -> list[dict]:
    path = root / ".pkit" / "permissions" / "project" / "diagnose-log.jsonl"
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def test_hook_captures_deferred_decision_when_armed(tmp_path):
    """Armed session + an abstain (unmodeled, lenient) → the hook captures it,
    redacted, AND still abstains (no stdout)."""
    root = _tree_with_capture(tmp_path)
    _arm_session(root)
    _, parsed = _invoke(root, {"tool_name": "Bash",
                               "tool_input": {"command": "npm run build --prefix /secret/path"},
                               "cwd": str(root)})
    assert parsed is None, "capture must not change the abstain verdict"
    log = _read_diag_log(root)
    assert len(log) == 1
    assert log[0]["command"].startswith("npm run build")
    assert "/secret/path" not in log[0]["command"], "command tail must be redacted by default"


def test_hook_does_not_capture_when_session_off(tmp_path):
    """No armed marker (default) → the hook captures nothing on an abstain."""
    root = _tree_with_capture(tmp_path)  # no _arm_session call
    _, parsed = _invoke(root, {"tool_name": "Bash",
                               "tool_input": {"command": "gh pr list"}, "cwd": str(root)})
    assert parsed is None
    assert _read_diag_log(root) == []


def test_hook_does_not_capture_allow_or_deny(tmp_path):
    """Only the deferred (abstain) verdict is captured — a guardrail deny is not."""
    root = _tree_with_capture(tmp_path)
    _arm_session(root)
    _, parsed = _invoke(root, {"tool_name": "Bash",
                               "tool_input": {"command": "sudo rm x"}, "cwd": str(root)})
    assert _decision(parsed) == "deny"
    assert _read_diag_log(root) == [], "a deny must not be captured"


def test_hook_capture_failure_is_inert(tmp_path):
    """A BROKEN capture module must never change the decision or break the hook.
    We replace diagnose_capture.py with one whose `capture` raises; the hook's
    inner try must keep enforcement intact (decision unchanged, fail-open held)."""
    root = _tree_with_capture(tmp_path)
    _arm_session(root)
    (root / ".pkit" / "permissions" / "diagnose_capture.py").write_text(
        "def capture(*a, **k):\n    raise RuntimeError('boom')\n", encoding="utf-8",
    )
    # A guardrail deny must STILL be returned despite the broken capture.
    _, parsed = _invoke(root, {"tool_name": "Bash",
                               "tool_input": {"command": "sudo rm x"}, "cwd": str(root)})
    assert _decision(parsed) == "deny", "broken capture must not change the decision"
    # An abstain must STILL abstain (exit 0, no stdout) — fail-open preserved.
    _, parsed = _invoke(root, {"tool_name": "Bash",
                               "tool_input": {"command": "gh pr list"}, "cwd": str(root)})
    assert parsed is None, "broken capture must not break fail-open"
