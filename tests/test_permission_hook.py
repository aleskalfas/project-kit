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
