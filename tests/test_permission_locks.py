"""The locked commands: the core's own verdicts, the hook's judgements apart
from one another, and the native locks beside them (ADR-095 points 3 and 4,
ADR-099 point 1).

The reading is tested in process against the real catalog: what it locks, what
it reads as a mention and leaves alone, and where it is in doubt. The hook is
driven end to end as Claude Code drives it, in every permission mode and with
its model, its core or its catalog broken. The native locks are held to the
catalog they are derived from.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import click
import pytest

REPO = Path(__file__).resolve().parent.parent
PERMISSIONS = REPO / ".pkit" / "permissions"
CATALOG = REPO / ".pkit" / "schemas" / "privilege-catalog.yaml"
HOOK = REPO / ".pkit" / "adapters" / "claude-code" / "permission-hook.py"
CORE_SETTINGS = REPO / ".pkit" / "adapters" / "claude-code" / "settings" / "core" / "settings.json"
NAME = "permissions folders name"


def _module(name: str) -> Any:
    spec = importlib.util.spec_from_file_location(f"locks_{name}", PERMISSIONS / f"{name}.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


decide = _module("decide")
projection = _module("projection")


@pytest.fixture(scope="module")
def catalog() -> dict[str, Any]:
    return decide.load_catalog(str(REPO))


def _verdict(catalog: dict[str, Any], command: str, tool: str = "bash") -> str | None:
    """The reading's verdict, in one word: `deny`, `ask`, `runner`, `doubt` or
    None for a call that runs no locked command."""
    verdict, kind, _, _ = decide.own_verdict(catalog, tool, command)
    return verdict if verdict in ("deny", "ask") else kind


# ---- the reading: what it locks ------------------------------------------------

LOCKED = [
    "pkit permissions apply",
    "pkit permissions apply --help",
    "pkit permissions enable",
    "pkit permissions disable",
    "pkit permissions profile activate solo",
    "pkit permissions setup autonomy",
    "pkit permissions setup autonomy down",
    "pkit permissions sandbox enable",
    "pkit permissions sandbox exclude gh --remove",
    "pkit permissions sandbox accommodate uv",
    "pkit upgrade",
    "/usr/local/bin/pkit permissions apply",
    "pkit -- permissions apply",
    "pkit --color never permissions apply",
    "pkit --color=never permissions apply",
    "pkit permissions apply\n",
    "cd /x && pkit permissions apply",
    "true # it's\npkit permissions apply",
    'echo "<<X"\npkit permissions apply\nX',
    "echo $((1<<2)); pkit permissions apply",
    'cat <<<"x"; pkit permissions apply',
    'echo "$(pkit permissions apply)"',
    "$(pkit permissions apply)",
    "cat <<EOF\n$(pkit permissions apply)\nEOF",
    "bash <<'EOF'\npkit permissions apply\nEOF",
    "if true; then pkit permissions apply; fi",
    "for f in a b; do pkit permissions apply; done",
    "case $x in a) pkit permissions apply;; esac",
    "( pkit permissions apply )",
    "{ pkit permissions apply; }",
    "f() { pkit permissions apply; }",
    "X=1 pkit permissions apply 2>&1 | tail",
    "nohup pkit permissions apply &",
    "timeout 5 pkit permissions apply",
    "stdbuf -oL pkit permissions apply",
    "noglob pkit permissions apply",
    "xargs -I{} pkit permissions apply",
    "uv run pkit permissions apply",
    "find . -exec pkit permissions apply \\;",
    "uvx project-kit@2.2.0 permissions apply",
    "uvx project-kit -- permissions apply",
    "uvx project-kit --color never permissions apply",
    "uvx --from project-kit pkit -- permissions apply",
    "uvx --from project-kit -- pkit permissions apply",
    "uv tool run project-kit permissions apply",
    "uv tool uvx project-kit permissions apply",
]

INSTALLER = [
    "uv tool install --force git+https://x/project-kit.git@v2",
    "uv tool install --force ./x",
    "uv tool install --force --from ./y uv",
    "uv tool install ruff --with project-kit",
    "uv tool uninstall project-kit",
    "uv tool uninstall --all",
    "uv tool upgrade project-kit",
    "uv tool upgrade --all",
    "uv tool upgrade foo",
    "uv tool update foo",
    "uv self update",
    "uv python install",
    "uv python install --reinstall",
    "uv python upgrade",
    "uv python uninstall 3.12",
    "uv pip install --python ~/.local/share/uv/tools/project-kit/bin/python foo",
    "uv pip uninstall project-kit",
    "uv -q tool upgrade foo",
    "uv --offline tool install --force x",
    "uv tool -q install --force x",
    "uv -q python install",
]

NAMED = [
    f"pkit {NAME} x",
    f"pkit {NAME} --help",
    f"pkit --color never {NAME} x",
    f"pkit -- {NAME} x",
    f'echo "$(pkit {NAME} x)"',
    f"uvx project-kit {NAME} x",
    f"uvx -q project-kit {NAME} x",
    f"uvx --offline project-kit {NAME} x",
    f"uvx project-kit@2.2.0 {NAME} x",
    f"uvx project-kit -- {NAME} x",
    f"uvx project-kit --color never {NAME} x",
    f"uvx --from project-kit pkit {NAME} x",
    f"uvx --from=project-kit pkit {NAME} x",
    f"uvx --from project-kit -q pkit {NAME} x",
    f"uvx --from project-kit pkit -- {NAME} x",
    f"uvx --from project-kit -- pkit {NAME} x",
    f"uvx --from project-kit pkit --color=never {NAME} x",
    f"uvx --from git+https://x/project-kit.git@v2 pkit {NAME} x",
    f"uv tool run -q project-kit {NAME} x",
    f"uv tool uvx project-kit {NAME} x",
    f"uv -q tool run project-kit {NAME} x",
    f"uv tool -q run project-kit {NAME} x",
    f"uv tool -q run --from project-kit pkit {NAME} x",
]


@pytest.mark.parametrize("command", LOCKED)
def test_the_interlock_asks_on_a_command_that_changes_what_judges(catalog, command):
    assert _verdict(catalog, command) == "ask"


@pytest.mark.parametrize("command", INSTALLER)
def test_the_interlock_asks_on_the_installer_writing_a_guarded_folder(catalog, command):
    assert _verdict(catalog, command) == "ask"


@pytest.mark.parametrize("command", NAMED)
def test_naming_a_folder_is_denied_in_every_form(catalog, command):
    verdict, _, reason, names = decide.own_verdict(catalog, "bash", command)
    assert (verdict, names) == ("deny", ["name-folder"])
    assert "pkit permissions folders name <folder>" in reason


@pytest.mark.parametrize("tool", ["powershell", "monitor"])
def test_every_tool_that_runs_a_command_is_read(catalog, tool):
    assert _verdict(catalog, "pkit permissions enable", tool) == "ask"
    assert _verdict(catalog, f"pkit {NAME} x", tool) == "deny"


# ---- the reading: what it leaves alone -----------------------------------------

LEFT_ALONE = [
    "git status",
    "echo 'pkit permissions apply'",
    "true # pkit permissions apply",
    "pkit permissions applyx",
    "pkit permissions -- apply",
    "pkit permissions sandbox toolkit list",
    "pkit permissions profile list",
    "pkit permissions folders remove x",
    "pkit permissions folders list",
    "pkit capabilities upgrade x",
    "git commit -m \"$(cat <<'EOF'\nfix: pkit permissions apply now\n\"quoted\" 'single'\n"
    'pkit permissions apply\nEOF\n)"',
    "git commit -m \"$(cat <<'EOF'\nfix(x): (a) b) c\nRun `pkit permissions apply` and "
    '$(pkit permissions apply)\nEOF\n)"',
    "gh pr create --body \"$(cat <<'EOF'\nRun `pkit permissions apply`\nEOF\n)\"",
    'gh pr create --body "$(cat <<EOF\nsee \\`pkit permissions apply\\` and '
    '\\$(pkit permissions apply)\nEOF\n)"',
    f"gh pr create --title 'x' --body-file - <<'EOF'\npkit {NAME} x\nEOF",
    'git commit -m "Deny \\"cd x; pkit permissions apply y\\" now"',
    "cat <<'EOF' > doc.md\npkit permissions apply\nEOF",
    "sh -c 'cat > \"$1\"' _ f <<'EOF'\npkit permissions apply\nEOF",
    "bash x.sh <<'EOF'\npkit permissions apply\nEOF",
    'uvx project-kit@2.2.0 pm comment 42 --body "x pkit permissions apply y"',
    f'uvx project-kit@2 pm comment 42 --body "x pkit {NAME} y"',
    "uvx --from project-kit python -m project_kit permissions apply",
    "uv tool install ruff",
    "uv tool uninstall ruff",
    "uv tool list",
    "uv tool dir",
    "uv tool update-shell",
    "uv python list",
    "uv python find",
    "uv pip install foo",
    "uv pip install --python ~/.local/share/uv/python/cpython-3.12.1/bin/python3 ./x",
]


@pytest.mark.parametrize("command", LEFT_ALONE)
def test_a_mention_or_another_command_meets_no_lock(catalog, command):
    assert _verdict(catalog, command) is None


def test_powershell_reads_a_backslash_as_an_ordinary_character(catalog):
    command = 'git commit -m "Fix C:\\tools\\" -m "Run; pkit permissions apply C:\\x\\"'
    assert _verdict(catalog, command, "powershell") is None


# ---- the reading: where it is in doubt -----------------------------------------

DOUBTS = [
    ("bash", 'echo "unclosed'),
    ("bash", "echo $'it\\'s'; pkit permissions apply"),
    ("bash", "echo $(echo $(pkit permissions apply))"),
    ("powershell", "git commit -m \u201cdocs; pkit permissions apply\u201d"),
    ("powershell", "echo `; pkit permissions apply"),
    ("powershell", "echo @'\npkit permissions apply\n'@"),
    ("powershell", "pkit --% permissions apply"),
    ("powershell", "echo 'it''s'; pkit permissions apply"),
    ("powershell", "<# x #> pkit permissions apply"),
]


@pytest.mark.parametrize(("tool", "command"), DOUBTS)
def test_a_doubt_gives_no_verdict_of_its_own(catalog, tool, command):
    assert _verdict(catalog, command, tool) == "doubt"


def test_a_runner_it_cannot_read_gives_adr_025_point_7s_verdict(catalog):
    verdict, kind, reason, names = decide.own_verdict(
        catalog, "bash", "env -X pkit permissions apply"
    )
    assert (verdict, kind) == ("abstain", "runner")
    assert "realize" in names and "ADR-025 point 7" in reason


def test_the_reason_never_quotes_the_command(catalog):
    _, _, reason, _ = decide.own_verdict(catalog, "bash", "pkit permissions apply # secret-token")
    assert "secret-token" not in reason


def test_a_payload_it_cannot_read_gives_no_verdict(catalog):
    for payload in (
        {"tool_name": "Bash"},
        {"tool_name": "Bash", "tool_input": {"command": 7}},
        {"tool_name": "Read", "tool_input": {"command": "pkit permissions apply"}},
        "not a payload",
    ):
        verdict, kind, _, _ = decide.hook_own_verdict(catalog, payload)
        assert (verdict, kind) == ("abstain", None), payload


# ---- the catalog's locks ---------------------------------------------------------


def test_the_catalog_parses_alike_with_and_without_ruamel():
    text = CATALOG.read_text(encoding="utf-8")
    assert decide._stdlib_load_yaml(text) == decide.load_yaml(str(CATALOG))


def test_a_capability_fragment_may_not_declare_a_lock(tmp_path):
    (tmp_path / ".pkit" / "schemas").mkdir(parents=True)
    shutil.copy(CATALOG, tmp_path / ".pkit" / "schemas" / "privilege-catalog.yaml")
    (tmp_path / ".pkit" / "manifest.yaml").write_text(
        "schema_version: 1\ncomponents:\n  - kind: capability\n    name: trip\n"
        "    manifest: .pkit/capabilities/trip/manifest.yaml\n",
        encoding="utf-8",
    )
    fragment = tmp_path / ".pkit" / "capabilities" / "trip" / "permissions"
    fragment.mkdir(parents=True)
    (fragment / "privilege-catalog.yaml").write_text(
        "schema_version: 1\nprivileges: {}\nlocks:\n  realize:\n"
        "    description: a lock that loosens\n    verdict: ask\n"
        "    recognize:\n      - methodology: [status]\n",
        encoding="utf-8",
    )
    merged = decide.load_catalog(str(tmp_path))
    assert set(decide.catalog_locks(merged)) == set(
        decide.catalog_locks(decide.load_catalog(str(REPO)))
    )
    assert decide.own_verdict(merged, "bash", "pkit status")[0] == "abstain"
    assert any("may not declare a lock" in r for r in merged["_fragment_rejections"])


def test_the_methodology_options_are_the_command_groups_own():
    from project_kit.cli import main

    params = main.get_params(click.Context(main))
    opts = [(opt, param) for param in params for opt in param.opts + param.secondary_opts]
    assert all(opt.startswith("--") for opt, _ in opts), "a short option the reading skips"
    flags = {opt[2:] for opt, param in opts if getattr(param, "is_flag", False)}
    valued = {opt[2:] for opt, param in opts if not getattr(param, "is_flag", False)}
    assert (flags, valued) == (decide._METHODOLOGY_OPTIONS[3], decide._METHODOLOGY_OPTIONS[4])


# ---- the native locks --------------------------------------------------------------


def _core() -> dict[str, list[str]]:
    return json.loads(CORE_SETTINGS.read_text(encoding="utf-8"))["permissions"]


def test_the_core_settings_carry_the_native_locks_the_catalog_derives(catalog):
    native = projection.native_locks(catalog)
    core = _core()
    assert core["ask"] == native["ask"]
    assert set(native["deny"]) <= set(core["deny"])
    guardrails = [rule for rule in core["deny"] if rule not in native["deny"]]
    assert "Bash(sudo:*)" in guardrails and core["deny"] == guardrails + native["deny"]


def test_each_native_lock_names_the_shell_and_powershell_alike(catalog):
    for rules in projection.native_locks(catalog).values():
        bash = {rule[len("Bash(") :] for rule in rules if rule.startswith("Bash(")}
        shell = {rule[len("PowerShell(") :] for rule in rules if rule.startswith("PowerShell(")}
        assert bash == shell and len(bash) * 2 == len(rules)


def test_the_native_locks_name_no_option_the_reading_alone_reads(catalog):
    for rules in projection.native_locks(catalog).values():
        assert not [rule for rule in rules if "--color" in rule or "uv * tool" in rule]


def _matches(rule: str, command: str) -> bool:
    """Claude Code's wildcard matching of a shell rule, as its documentation
    gives it: `*` matches any run of characters, and a trailing ` *` also
    matches the bare form where it is the rule's only wildcard."""
    body = rule[rule.index("(") + 1 : -1]
    pattern = ".*".join(re.escape(part) for part in body.split("*"))
    if body.endswith(" *") and body.count("*") == 1:
        pattern = pattern[: -len(re.escape(" ") + ".*")] + "(?: .*)?"
    return re.fullmatch(pattern, command, re.DOTALL) is not None


PLAIN_ASKED = [
    "pkit permissions apply",
    "pkit permissions apply --dry-run",
    "uvx project-kit permissions apply",
    "uvx project-kit@2.2.0 permissions apply",
    "uvx -q --from project-kit pkit permissions enable",
    "uv tool run project-kit permissions setup autonomy",
    "uv tool uvx project-kit upgrade",
    "uv tool upgrade foo",
    "uv tool install --force ruff",
    "uv tool uninstall project-kit",
    "uv self update",
    "uv python install",
    "uv pip install project-kit",
]
PLAIN_NAMED = [
    f"pkit {NAME} x",
    f"uvx project-kit {NAME} x",
    f"uvx -q project-kit {NAME} x",
    f"uvx --from project-kit pkit {NAME} x",
    f"uvx --from=project-kit pkit {NAME} x",
    f"uvx --offline --from project-kit pkit {NAME} x",
    f"uv tool run project-kit {NAME} x",
    f"uv tool uvx --offline project-kit {NAME} x",
]


@pytest.mark.parametrize("command", PLAIN_ASKED)
def test_a_native_ask_meets_each_plain_form_the_interlock_asks_on(catalog, command):
    assert _verdict(catalog, command) == "ask"
    assert any(_matches(rule, command) for rule in projection.native_locks(catalog)["ask"])


@pytest.mark.parametrize("command", PLAIN_NAMED)
def test_a_native_deny_meets_each_plain_form_of_naming_a_folder(catalog, command):
    assert _verdict(catalog, command) == "deny"
    assert any(_matches(rule, command) for rule in projection.native_locks(catalog)["deny"])


@pytest.mark.parametrize(
    "command",
    [
        f"uvx project-kit@2.2.0 {NAME} x",
        f"uvx project-kit --color never {NAME} x",
        f"uvx --from project-kit -q pkit {NAME} x",
        f'uvx project-kit pm comment 42 --body "x pkit {NAME} y"',
    ],
)
def test_the_native_deny_takes_no_text_after_the_package(catalog, command):
    """The native deny's wildcard stands before the package alone, so a
    version written onto it, or an option after it, passes the native deny
    and meets the core's, and a later argument mentioning the naming form by
    the command's own name meets neither (ADR-099 point 1, "The runners'
    options")."""
    assert not any(_matches(rule, command) for rule in projection.native_locks(catalog)["deny"])


@pytest.mark.parametrize(
    "command",
    ["pkit permissions folders remove x", "pkit permissions folders list", "pkit permissions"],
)
def test_no_native_lock_meets_the_removal_or_the_listing(catalog, command):
    native = projection.native_locks(catalog)
    assert not any(_matches(rule, command) for rule in native["ask"] + native["deny"])


# ---- the hook, end to end ----------------------------------------------------------

MODES = ("default", "plan", "acceptEdits", "dontAsk", "auto", "bypassPermissions", None)


def _tree(tmp_path: Path, *, grants: str | None = None, decide_core: bool = True) -> Path:
    root = tmp_path / "proj"
    (root / ".pkit" / "schemas").mkdir(parents=True)
    shutil.copy(CATALOG, root / ".pkit" / "schemas" / "privilege-catalog.yaml")
    (root / ".pkit" / "permissions").mkdir(parents=True)
    if decide_core:
        shutil.copy(PERMISSIONS / "decide.py", root / ".pkit" / "permissions" / "decide.py")
    if grants is not None:
        (root / ".pkit" / "permissions" / "project").mkdir(parents=True)
        (root / ".pkit" / "permissions" / "project" / "grants.yaml").write_text(grants)
    return root


def _hook(root: Path, payload: dict[str, Any], mode: object = None) -> tuple[str | None, str]:
    """Run the hook as Claude Code does: (its decision or None, its reason)."""
    if mode is not None:
        payload = {**payload, "permission_mode": mode}
    proc = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env={"CLAUDE_PROJECT_DIR": str(root), "PATH": os.environ["PATH"]},
    )
    assert proc.returncode == 0, proc.stderr
    if not proc.stdout.strip():
        return None, ""
    out = json.loads(proc.stdout)["hookSpecificOutput"]
    return out["permissionDecision"], out["permissionDecisionReason"]


def _bash(root: Path, command: str, **tool_input: Any) -> dict[str, Any]:
    return {"tool_name": "Bash", "tool_input": {"command": command, **tool_input}, "cwd": str(root)}


_PKIT_GRANTED = (
    "schema_version: 1\ngrants:\n  - subject: operator\n"
    '    privilege: "[privilege-catalog:pkit]"\n    effect: allow\n'
)
_BROKEN_MODEL = "schema_version: 1\ngrants: [unclosed\n"


def test_the_hook_gives_the_own_verdicts_in_every_mode(tmp_path):
    root = _tree(tmp_path, grants=_PKIT_GRANTED)
    for mode in MODES:
        assert _hook(root, _bash(root, "pkit permissions apply"), mode)[0] == "ask", mode
        assert _hook(root, _bash(root, f"pkit {NAME} x"), mode)[0] == "deny", mode
        assert _hook(root, _bash(root, "uv tool upgrade --all"), mode)[0] == "ask", mode


def test_the_hook_leaves_a_mention_to_the_model(tmp_path):
    root = _tree(tmp_path)
    command = 'git commit -m "docs: run pkit permissions apply after the change"'
    assert _hook(root, _bash(root, command), "default")[0] is None


def test_the_hook_asks_on_a_runner_it_cannot_read_meeting_the_mode(tmp_path):
    root = _tree(tmp_path)
    payload = _bash(root, "env -X pkit permissions apply")
    decision, reason = _hook(root, payload, "default")
    assert decision == "ask" and "ADR-025 point 7" in reason
    for mode in ("auto", "bypassPermissions"):
        assert _hook(root, payload, mode)[0] is None, mode


def test_the_hook_keeps_the_guardrail_and_the_interlock_where_the_model_fails(tmp_path):
    root = _tree(tmp_path, grants=_BROKEN_MODEL)
    for mode in MODES:
        assert _hook(root, _bash(root, "sudo rm x"), mode)[0] == "deny", mode
        assert _hook(root, _bash(root, "pkit permissions enable"), mode)[0] == "ask", mode
        assert _hook(root, _bash(root, f"pkit {NAME} x"), mode)[0] == "deny", mode
        assert _hook(root, _bash(root, "git status"), mode)[0] is None, mode


def test_the_hook_asks_before_a_write_outside_the_repository_where_the_model_fails(tmp_path):
    root = _tree(tmp_path, grants=_BROKEN_MODEL)
    foreign = tmp_path / "elsewhere" / "file.txt"
    payload = {
        "tool_name": "Write",
        "tool_input": {"file_path": str(foreign), "content": "x"},
        "cwd": str(root),
    }
    for mode in MODES:
        decision, reason = _hook(root, payload, mode)
        assert decision == "ask" and "outside this session's repo" in reason, mode


def test_the_hook_asks_before_leaving_the_sandbox_in_every_mode(tmp_path):
    root = _tree(tmp_path, grants=_PKIT_GRANTED)
    for mode in MODES:
        for command in ("git status", "pkit status"):
            payload = _bash(root, command, dangerouslyDisableSandbox=True)
            decision, reason = _hook(root, payload, mode)
            assert decision == "ask" and "ADR-095 point 4" in reason, (mode, command)
        payload = _bash(root, "sudo rm x", dangerouslyDisableSandbox=True)
        assert _hook(root, payload, mode)[0] == "deny", mode


def test_the_hook_asks_where_it_cannot_read_the_sandbox_request(tmp_path):
    root = _tree(tmp_path)
    for flag in ("yes", 1, None):
        payload = _bash(root, "git status", dangerouslyDisableSandbox=flag)
        assert _hook(root, payload, "bypassPermissions")[0] == "ask", flag
    payload = {"tool_name": "PowerShell", "tool_input": "git status", "cwd": str(root)}
    assert _hook(root, payload, "auto")[0] == "ask"


def test_the_hook_asks_before_leaving_the_sandbox_without_its_core(tmp_path):
    root = _tree(tmp_path, decide_core=False)
    payload = _bash(root, "git status", dangerouslyDisableSandbox=True)
    assert _hook(root, payload, "auto")[0] == "ask"
    assert _hook(root, _bash(root, "git status", dangerouslyDisableSandbox=False))[0] is None


def test_the_hook_asks_before_leaving_the_sandbox_without_its_catalog(tmp_path):
    root = _tree(tmp_path)
    (root / ".pkit" / "schemas" / "privilege-catalog.yaml").write_text("locks: [unclosed\n")
    payload = _bash(root, "git status", dangerouslyDisableSandbox=True)
    assert _hook(root, payload, "auto")[0] == "ask"
