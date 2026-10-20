"""The confined form of the Claude Code adapter's agent runner (ADR-066 points 2 to 6, 8, 9
and 12; #1744).

- a confined request is read whole: its folders, its rules in their three forms and its
  exclusions, and a key it does not run is refused;
- each refusal before the start names its cause: the tested version range (empty as
  shipped), the platform's sandbox, the runner not being the working copy's own, the
  agent's definition, and the run's settings;
- the definition is the deploy's resolution of the file the deploy picks, in the
  methodology's shape, and only the description, the instructions, the tools, the model
  and the effort are passed, under a name unique to the run; both fixers pass the check;
- the run's settings are its own, carry the denies of every settings file it leaves out,
  and hold the confined form's fixed values; the command line is the closed set; the
  environment holds only what the run needs, with the marker;
- the start report is read, and a mismatch or a hook ends the run at once; the answer
  carries the agent's final message, never a tool's result, and the calls refused;
- the probe starts nothing without its flag.

A stub harness on a PATH the test builds stands in for `claude`: no real agent starts.
"""

from __future__ import annotations

import ast
import importlib.util
import json
import os
import re
import shutil
import signal
import stat
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
ADAPTER = REPO_ROOT / ".pkit" / "adapters" / "claude-code"
RUNNER = ADAPTER / "run-agent.py"
PROBE = ADAPTER / "probe-confined-run.py"
REFS = REPO_ROOT / "src" / "project_kit" / "refs.py"

TESTED = ("2.1.300", "2.1.310")
RUN_TOOLS = ["Read", "Glob", "Grep", "Write", "Bash"]

INIT: dict[str, Any] = {
    "type": "system",
    "subtype": "init",
    "cwd": "/somewhere",
    "session_id": "s-1",
    "tools": RUN_TOOLS,
    "mcp_servers": [],
    "model": "claude-x",
    "permissionMode": "dontAsk",
    "slash_commands": [],
    "plugins": [],
}
TOOL_RESULT = {
    "type": "user",
    "message": {"content": [{"type": "tool_result", "content": "A TOOL'S RESULT"}]},
}
FINAL = "Fixer result (probe): none `x`: not-mine: it is not mine"
RESULT = {
    "type": "result",
    "subtype": "success",
    "is_error": False,
    "result": FINAL,
    "permission_denials": [
        {"tool_name": "Bash", "tool_use_id": "t-1", "tool_input": {"command": "gh pr list"}}
    ],
}

AGENT_FILE = """---
name: probe
description: A probe agent.
tools: [Read, Glob, Grep, Write, Bash]
storyboards:
  - storyboard.md
reads:
  paths:
    - README.md
owns: []
needs: []
gates: [COR-001]
---

You are the probe.
"""

IDENTITY_RESOLVER = "import sys\nsys.stdout.write(open(sys.argv[1], encoding='utf-8').read())\n"

# A harness that answers `--version`, records how it was started, then prints
# the stream the test wrote beside it (a `SLEEP n` line waits) and exits.
STUB_HARNESS = """
import json, os, sys, time
here = os.path.dirname(os.path.abspath(sys.argv[0]))
if sys.argv[1:] == ["--version"]:
    print(open(os.path.join(here, "version")).read().strip() + " (Claude Code)")
    sys.exit(0)
record = {"argv": sys.argv[1:], "env": dict(os.environ), "cwd": os.getcwd(),
          "brief": sys.stdin.read(), "pid": os.getpid()}
open(os.path.join(here, "record.json"), "w").write(json.dumps(record))
for line in open(os.path.join(here, "stream.jsonl")):
    if line.startswith("SLEEP"):
        sys.stdout.flush()
        time.sleep(float(line.split()[1]))
        continue
    sys.stdout.write(line)
    sys.stdout.flush()
print("a warning", file=sys.stderr)
sys.exit(int(open(os.path.join(here, "exit")).read()))
"""


def _load(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _script(path: Path, body: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"#!{sys.executable}\n{body}", encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return path


@pytest.fixture
def runner() -> ModuleType:
    return _load(RUNNER, "claude_code_confined_runner_under_test")


@dataclass
class Scene:
    clone: Path
    adapter: Path
    workspace: Path
    temp: Path
    pkit_folder: Path
    checkout: Path
    harness_bin: Path
    home: Path

    def request(self, **overrides: Any) -> dict[str, Any]:
        confined: dict[str, Any] = {
            "working_copy": str(self.clone),
            "workspace": str(self.workspace),
            "temp": str(self.temp),
            "pkit_folder": str(self.pkit_folder),
            "project_root": str(self.checkout),
            "rules": {
                "allow": [
                    {"tool": "Read", "folder": str(self.clone)},
                    {"tool": "Write", "folder": str(self.workspace)},
                    {"command": ["git", "-C", str(self.clone), "log"]},
                    {"command": ["pkit", "analysis", "propose"]},
                ],
                "deny": [{"tool": "Edit"}, {"command": ["gh"]}],
            },
            "excluded": [["pkit", "analysis", "propose"]],
        }
        confined.update(overrides.pop("confined", {}))
        request: dict[str, Any] = {
            "schema_version": 1,
            "agent": "probe",
            "brief": "Propose the fixes.",
            "limit_seconds": 30,
            "effort": None,
            "confined": confined,
        }
        request.update(overrides)
        return request

    def env(self) -> dict[str, str]:
        return {
            "PATH": f"{self.harness_bin}{os.pathsep}{os.environ.get('PATH', '')}",
            "HOME": str(self.home),
            "USER": "someone",
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "ANTHROPIC_API_KEY": "a-key",
            "CLAUDE_CONFIG_DIR": str(self.home / ".claude"),
            "CLAUDE_CODE_TMPDIR": "/elsewhere",
            "TMPDIR": "/elsewhere",
            "HTTPS_PROXY": "http://proxy:3128",
            "no_proxy": "localhost",
            "ANTHROPIC_BASE_URL": "https://gateway",
            "UV_CACHE_DIR": "/a/cache",
            "UV_NO_CONFIG": "0",
            "PYTHONPATH": "/a/path",
            "PKIT_COMMAND_DEADLINE": "9999999999.0",
            "A_PERSONS_SECRET": "s",
        }

    def harness(self, events: list[Any], *, exit_code: int = 0, version: str = "2.1.302") -> None:
        """The stub harness, the stream it prints, its exit and its version."""
        _script(self.harness_bin / "claude", STUB_HARNESS)
        lines = [event if isinstance(event, str) else json.dumps(event) for event in events]
        (self.harness_bin / "stream.jsonl").write_text(
            "".join(line + "\n" for line in lines), encoding="utf-8"
        )
        (self.harness_bin / "exit").write_text(str(exit_code), encoding="utf-8")
        (self.harness_bin / "version").write_text(version, encoding="utf-8")

    def record(self) -> dict[str, Any]:
        return json.loads((self.harness_bin / "record.json").read_text(encoding="utf-8"))

    def started(self) -> bool:
        return (self.harness_bin / "record.json").exists()


@pytest.fixture
def scene(tmp_path: Path, runner: ModuleType, monkeypatch: pytest.MonkeyPatch) -> Scene:
    clone = tmp_path / "clone"
    adapter = clone.joinpath(".pkit", "adapters", "claude-code")
    _script(adapter / "_resolve_agent.py", IDENTITY_RESOLVER)
    agent = clone.joinpath(".pkit", "agents", "project", "probe", "probe.md")
    agent.parent.mkdir(parents=True)
    agent.write_text(AGENT_FILE, encoding="utf-8")
    workspace = clone / ".agent-workspace"
    temp = workspace / ".tmp"
    temp.mkdir(parents=True)
    built = Scene(
        clone=clone,
        adapter=adapter,
        workspace=workspace,
        temp=temp,
        pkit_folder=tmp_path / "run-bin",
        checkout=tmp_path / "checkout",
        harness_bin=tmp_path / "harness-bin",
        home=tmp_path / "home",
    )
    for folder in (built.pkit_folder, built.checkout, built.harness_bin, built.home):
        folder.mkdir()
    monkeypatch.setattr(runner, "ADAPTER_FOLDER", adapter)
    monkeypatch.setattr(runner, "TESTED_RANGE", TESTED)
    monkeypatch.setattr(runner, "sandbox_gap", lambda _platform, _path: None)
    return built


def _run(runner: ModuleType, scene: Scene, **overrides: Any) -> dict[str, Any]:
    request = runner.read_request(json.dumps(scene.request(**overrides)))
    return runner.run(request, scene.env())


def _refusal(runner: ModuleType, scene: Scene, **overrides: Any) -> str:
    with pytest.raises(runner.Refused) as refused:
        _run(runner, scene, **overrides)
    return str(refused.value)


# --- the request --------------------------------------------------------------------------


def test_a_confined_request_takes_no_folder(runner: ModuleType, scene: Scene) -> None:
    request = scene.request(folder=str(scene.clone))
    with pytest.raises(runner.Refused, match=r"does not run: folder\. The confined form takes no"):
        runner.read_request(json.dumps(request))


@pytest.mark.parametrize(
    ("confined", "says"),
    [
        ({"settings": {}}, "confined carries keys this runner does not run: settings"),
        ({"working_copy": "relative"}, "working_copy 'relative' is not an absolute directory"),
        ({"temp": "/no/such/folder"}, "temp '/no/such/folder' is not an absolute directory"),
        ({"rules": {"allow": []}}, "rules are not an object of allow and deny"),
        ({"rules": {"allow": {}, "deny": []}}, "allow rules are not a list"),
        ({"excluded": [["uv"]]}, "excluded command \\['uv'\\] is not one the run's rules allow"),
        ({"excluded": "pkit"}, "excluded commands are not a list"),
    ],
)
def test_a_confined_object_it_does_not_run_is_refused(
    runner: ModuleType, scene: Scene, confined: dict[str, Any], says: str
) -> None:
    with pytest.raises(runner.Refused, match=says):
        runner.read_request(json.dumps(scene.request(confined=confined)))


def test_a_confined_object_lacking_a_key_is_refused(runner: ModuleType, scene: Scene) -> None:
    request = scene.request()
    del request["confined"]["project_root"]
    with pytest.raises(runner.Refused, match="confined lacks project_root"):
        runner.read_request(json.dumps(request))


def test_the_folders_lie_where_the_run_needs_them(
    runner: ModuleType, scene: Scene, tmp_path: Path
) -> None:
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    for confined, says in (
        ({"workspace": str(elsewhere)}, "workspace is not a folder inside its working copy"),
        ({"workspace": str(scene.clone)}, "workspace is not a folder inside its working copy"),
        ({"temp": str(elsewhere)}, "temp folder is not inside its workspace"),
        ({"temp": str(scene.workspace)}, "temp folder is not inside its workspace"),
        ({"pkit_folder": str(scene.temp)}, "pkit folder lies in its workspace"),
        ({"pkit_folder": str(scene.workspace)}, "pkit folder lies in its workspace"),
    ):
        with pytest.raises(runner.Refused, match=says):
            runner.read_request(json.dumps(scene.request(confined=confined)))


def test_a_workspace_that_is_a_link_is_refused(
    runner: ModuleType, scene: Scene, tmp_path: Path
) -> None:
    target = scene.clone / "real-workspace"
    (target / ".tmp").mkdir(parents=True)
    linked = scene.clone / "linked-workspace"
    linked.symlink_to(target)
    with pytest.raises(runner.Refused, match="workspace is not a folder inside"):
        runner.read_request(
            json.dumps(
                scene.request(confined={"workspace": str(linked), "temp": str(linked / ".tmp")})
            )
        )


# --- the rules, rendered ------------------------------------------------------------------


def test_each_rule_form_renders_as_the_harness_reads_it(runner: ModuleType) -> None:
    assert runner.render_rule({"tool": "Edit"}) == "Edit"
    assert runner.render_rule({"tool": "Read", "folder": "/abs/clone"}) == "Read(//abs/clone/**)"
    # A folder rule is written in its tool's rule family, the one the harness
    # matches the tool's path against.
    assert runner.render_rule({"tool": "Write", "folder": "/abs/ws/"}) == "Edit(//abs/ws/**)"
    assert runner.render_rule({"tool": "Grep", "folder": "/abs/clone"}) == "Read(//abs/clone/**)"
    assert runner.render_rule({"tool": "Glob", "folder": "/abs/clone"}) == "Read(//abs/clone/**)"
    assert runner.render_rule({"tool": "Bash", "folder": "/abs"}) == "Bash(//abs/**)"
    assert (
        runner.render_rule({"command": ["git", "-C", "/abs/clone", "log"]})
        == "Bash(git -C /abs/clone log:*)"
    )
    assert runner.render_rule({"command": ["pkit", "pm"]}) == "Bash(pkit pm:*)"


@pytest.mark.parametrize(
    "token",
    [
        "two words",
        "tab\there",
        "it's",
        'say"',
        "back`tick",
        "star*",
        "(open",
        "close)",
        "nul\x00",
        "",
    ],
)
def test_a_command_token_that_could_widen_its_rule_is_refused(
    runner: ModuleType, token: str
) -> None:
    with pytest.raises(runner.Refused, match="command token"):
        runner.render_rule({"command": ["git", token]})


@pytest.mark.parametrize(
    "rule",
    [
        {"tool": "Read", "folder": "relative/path"},
        {"tool": "Read", "folder": "/abs/*/x"},
        {"tool": "Read", "folder": "/abs/../etc"},
        {"tool": "Read", "folder": "/abs/(x)"},
        {"tool": "Bash(rm:*)"},
        {"tool": "Read", "command": ["ls"]},
        {"command": []},
        {"command": "git log"},
        ["Read"],
    ],
)
def test_a_rule_outside_the_three_forms_is_refused(runner: ModuleType, rule: Any) -> None:
    with pytest.raises(runner.Refused):
        runner.render_rule(rule)


# --- the run's settings -------------------------------------------------------------------


def _settings_file(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data if isinstance(data, str) else json.dumps(data), encoding="utf-8")


def test_the_settings_are_the_runs_own_with_the_denies_of_each_file_left_out(
    runner: ModuleType, scene: Scene
) -> None:
    # A deny the tool list already holds is not copied: `Edit` alone would take
    # `Write` away from the workspace. `Edit(path)` is copied, since the harness
    # matches `Write` against it.
    _settings_file(
        scene.home / ".claude" / "settings.json",
        {
            "permissions": {
                "deny": ["Bash(sudo:*)", "Edit", "WebFetch(domain:x.com)", "Edit(//etc/**)"],
                "allow": ["Bash(gh:*)"],
            },
            "hooks": {},
        },
    )
    _settings_file(
        scene.clone / ".claude" / "settings.json", {"permissions": {"deny": ["Read(~/.ssh/**)"]}}
    )
    _settings_file(
        scene.checkout / ".claude" / "settings.json", {"permissions": {"deny": ["Bash(rm -rf:*)"]}}
    )
    _settings_file(
        scene.checkout / ".claude" / "settings.local.json",
        {"permissions": {"deny": ["Bash(sudo:*)"], "defaultMode": "bypassPermissions"}},
    )
    settings = runner.run_settings(scene.request()["confined"], scene.env())
    assert settings == {
        "permissions": {
            "allow": [
                f"Read(/{scene.clone}/**)",
                f"Edit(/{scene.workspace}/**)",
                f"Bash(git -C {scene.clone} log:*)",
                "Bash(pkit analysis propose:*)",
            ],
            "deny": [
                "Bash(gh:*)",
                "Bash(sudo:*)",
                "Edit(//etc/**)",
                "Read(~/.ssh/**)",
                "Bash(rm -rf:*)",
            ],
            "defaultMode": "dontAsk",
            "disableBypassPermissionsMode": "disable",
            "blockReadsOutsideWorkingDirectories": True,
        },
        "sandbox": {
            "enabled": True,
            "failIfUnavailable": True,
            "autoAllowBashIfSandboxed": False,
            "allowUnsandboxedCommands": False,
            "excludedCommands": ["pkit analysis propose"],
            "network": {"allowedDomains": []},
        },
        "autoMemoryEnabled": False,
    }
    runner.check_settings(settings)


def _rules(scene: Scene, *deny: dict[str, Any], allow: list[Any] | None = None) -> dict[str, Any]:
    rules = dict(scene.request()["confined"]["rules"])
    rules["deny"] = list(deny)
    if allow is not None:
        rules["allow"] = allow
    return rules


@pytest.mark.parametrize(
    "deny",
    [
        {"tool": "Edit"},
        {"tool": "MultiEdit"},
        {"tool": "NotebookEdit"},
        {"tool": "WebFetch"},
        {"tool": "Edit", "folder": "/anywhere"},
    ],
)
def test_a_deny_of_a_tool_outside_the_runs_is_held_by_the_tool_list(
    runner: ModuleType, scene: Scene, deny: dict[str, Any]
) -> None:
    assert runner.held_denies(_rules(scene, deny)) == []


def test_a_deny_apart_from_every_allow_is_held_natively(runner: ModuleType, scene: Scene) -> None:
    denies = [
        {"command": ["gh"]},
        {"command": ["git", "-C", str(scene.clone), "push"]},
        {"command": ["pkit", "pm"]},
        {"tool": "Read", "folder": "/etc"},
        {"tool": "Write", "folder": str(scene.clone / "src")},
    ]
    assert runner.held_denies(_rules(scene, *denies)) == [
        "Bash(gh:*)",
        f"Bash(git -C {scene.clone} push:*)",
        "Bash(pkit pm:*)",
        "Read(//etc/**)",
        f"Edit(/{scene.clone}/src/**)",
    ]


@pytest.mark.parametrize(
    ("deny", "allow"),
    [
        ({"command": ["pkit"]}, "Bash(pkit analysis propose:*)"),
        ({"command": ["git", "-C"]}, "Bash(git -C"),
        ({"tool": "Bash"}, "Bash(git -C"),
        ({"tool": "Read", "folder": "/"}, "Read(/"),
        ({"tool": "Grep"}, "Read(/"),
        ({"tool": "Write"}, "Edit(/"),
        ({"tool": "Write", "folder": "WORKSPACE"}, "Edit(/"),
        ({"tool": "Glob", "folder": "WORKSPACE/deeper"}, "Read(/"),
    ],
)
def test_a_deny_that_would_take_away_an_allow_refuses_the_run(
    runner: ModuleType, scene: Scene, deny: dict[str, Any], allow: str
) -> None:
    if "folder" in deny:
        deny = {**deny, "folder": deny["folder"].replace("WORKSPACE", str(scene.workspace))}
    with pytest.raises(runner.Refused) as refused:
        runner.held_denies(_rules(scene, deny))
    reason = str(refused.value)
    assert f"the deny {runner.render_rule(deny)} would take away the allow {allow}" in reason
    assert "same rule family" in reason
    scene.harness([INIT, RESULT])
    request = scene.request()
    request["confined"]["rules"]["deny"] = [deny]
    with pytest.raises(runner.Refused, match="would take away the allow"):
        runner.run(runner.read_request(json.dumps(request)), scene.env())
    assert not scene.started()


def test_the_user_settings_are_found_without_a_config_folder(
    runner: ModuleType, scene: Scene
) -> None:
    env = {"HOME": str(scene.home)}
    paths = runner.left_out_settings(env, scene.clone, scene.checkout)
    assert paths[0] == scene.home / ".claude" / "settings.json"
    env["CLAUDE_CONFIG_DIR"] = "/config"
    assert runner.left_out_settings(env, scene.clone, scene.checkout)[0] == Path(
        "/config/settings.json"
    )


@pytest.mark.parametrize(
    ("data", "says"),
    [
        ("{not json", "cannot be read"),
        ([1], "not a JSON object"),
        ({"permissions": []}, "permissions are no object"),
        ({"permissions": {"deny": "Bash(sudo:*)"}}, "are not a list of rules"),
    ],
)
def test_a_settings_file_whose_denies_cannot_be_read_refuses_the_run(
    runner: ModuleType, scene: Scene, data: Any, says: str
) -> None:
    _settings_file(scene.checkout / ".claude" / "settings.local.json", data)
    scene.harness([INIT, RESULT])
    assert says in _refusal(runner, scene)
    assert not scene.started()


def test_a_deny_the_harness_schema_would_reject_refuses_the_run(
    runner: ModuleType, scene: Scene
) -> None:
    _settings_file(scene.home / ".claude" / "settings.json", {"permissions": {"deny": ["bash(x)"]}})
    scene.harness([INIT, RESULT])
    reason = _refusal(runner, scene)
    assert "fail the harness's settings schema" in reason
    assert "'bash(x)' names a tool that does not start with a capital" in reason
    assert not scene.started()


@pytest.mark.parametrize(
    ("change", "says"),
    [
        (lambda s: s.update(hooks={}), "hooks is not a key the runner writes"),
        (lambda s: s["sandbox"].update(enableWeakerNetworkIsolation=True), "not a key"),
        (lambda s: s["permissions"].update(defaultMode="auto"), 'defaultMode is not "dontAsk"'),
        (lambda s: s["permissions"].update(defaultMode="yolo"), "'yolo' is not one of"),
        (lambda s: s["sandbox"].update(autoAllowBashIfSandboxed=True), "autoAllowBash"),
        (lambda s: s["sandbox"].update(allowUnsandboxedCommands=True), "allowUnsandboxed"),
        (lambda s: s["sandbox"]["network"].update(allowedDomains=["x.com"]), "allowedDomains"),
        (lambda s: s.update(autoMemoryEnabled="no"), "autoMemoryEnabled is not a boolean"),
        (
            lambda s: s["permissions"].update(blockReadsOutsideWorkingDirectories=False),
            "blockReadsOutsideWorkingDirectories is not true",
        ),
        (lambda s: s["permissions"]["allow"].append("Read(x:*)"), "the :* prefix form"),
        (lambda s: s["permissions"]["allow"].append("mcp__s__t(x)"), "MCP tool a pattern"),
        (lambda s: s["permissions"]["deny"].append("Bash(:*)"), "no prefix before :*"),
        (lambda s: s["permissions"]["deny"].append("Bash(x"), "not of the form"),
    ],
)
def test_settings_outside_the_schema_or_the_confined_form_are_refused(
    runner: ModuleType, scene: Scene, change: Any, says: str
) -> None:
    settings = runner.run_settings(scene.request()["confined"], scene.env())
    change(settings)
    with pytest.raises(runner.Refused, match=re.escape(says)):
        runner.check_settings(settings)


# --- refusals before the start ------------------------------------------------------------


def test_as_shipped_every_confined_run_is_refused_until_the_probe_widens_the_range(
    runner: ModuleType, scene: Scene, monkeypatch: pytest.MonkeyPatch
) -> None:
    shipped = _load(RUNNER, "claude_code_runner_as_shipped")
    assert shipped.TESTED_RANGE == ()
    monkeypatch.setattr(runner, "TESTED_RANGE", ())
    scene.harness([INIT, RESULT])
    reason = _refusal(runner, scene)
    assert "the range is empty until the adapter's author runs the probe" in reason
    assert "probe-confined-run.py" in reason
    assert not scene.started()


@pytest.mark.parametrize("version", ["2.1.299", "2.1.311", "3.0.0"])
def test_a_harness_outside_the_tested_range_is_refused(
    runner: ModuleType, scene: Scene, version: str
) -> None:
    scene.harness([INIT, RESULT], version=version)
    reason = _refusal(runner, scene)
    assert f"version {version} lies outside the range" in reason
    assert "2.1.300 to 2.1.310" in reason
    assert not scene.started()


def test_a_platform_with_no_sandbox_is_refused(
    runner: ModuleType, scene: Scene, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(runner, "sandbox_gap", lambda _platform, _path: "no box here")
    scene.harness([INIT, RESULT])
    assert "the harness cannot sandbox the run: no box here" in _refusal(runner, scene)
    assert not scene.started()


def test_the_sandbox_each_platform_needs(
    runner: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(runner, "MACOS_SANDBOX", str(tmp_path / "sandbox-exec"))
    assert "is not there" in runner.sandbox_gap("darwin", "")
    _script(tmp_path / "sandbox-exec", "")
    assert runner.sandbox_gap("darwin", "") is None
    empty = tmp_path / "empty"
    empty.mkdir()
    assert (
        runner.sandbox_gap("linux", str(empty))
        == "the sandbox needs bwrap and socat on the run's PATH"
    )
    _script(empty / "bwrap", "")
    assert runner.sandbox_gap("linux", str(empty)) == "the sandbox needs socat on the run's PATH"
    _script(empty / "socat", "")
    assert runner.sandbox_gap("linux", str(empty)) is None
    assert "offers no sandbox" in runner.sandbox_gap("win32", str(empty))


def test_a_runner_that_is_not_the_working_copys_own_is_refused(
    runner: ModuleType, scene: Scene, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(runner, "ADAPTER_FOLDER", ADAPTER)
    scene.harness([INIT, RESULT])
    assert "not in the working copy's adapter folder" in _refusal(runner, scene)
    assert not scene.started()


def test_no_harness_on_path_is_refused(runner: ModuleType, scene: Scene) -> None:
    request = runner.read_request(json.dumps(scene.request()))
    with pytest.raises(runner.Refused, match="`claude` command line is not on PATH"):
        runner.run(request, {**scene.env(), "PATH": str(scene.pkit_folder)})


# --- the agent's definition ---------------------------------------------------------------


def _agent(scene: Scene, text: str, name: str = "probe") -> None:
    (scene.clone / ".pkit" / "agents" / "project" / name / f"{name}.md").write_text(
        text, encoding="utf-8"
    )


@pytest.mark.parametrize("field", ["hooks", "mcpServers", "permissionMode", "memory", "skills"])
def test_a_field_outside_the_methodologys_shape_refuses_the_run(
    runner: ModuleType, scene: Scene, field: str
) -> None:
    _agent(scene, AGENT_FILE.replace("owns: []\n", f"owns: []\n{field}: x\n"))
    scene.harness([INIT, RESULT])
    reason = _refusal(runner, scene)
    assert f"fields outside the methodology's shape: {field}" in reason
    assert not scene.started()


def test_the_resolvers_failure_refuses_the_run(runner: ModuleType, scene: Scene) -> None:
    _script(
        scene.adapter / "_resolve_agent.py",
        "import sys\nprint('probe: category <code-paths> referenced but not defined', "
        "file=sys.stderr)\nsys.exit(1)\n",
    )
    scene.harness([INIT, RESULT])
    reason = _refusal(runner, scene)
    assert "the deploy would not resolve the agent's definition: probe: category" in reason


@pytest.mark.parametrize(
    ("warning", "says"),
    [
        ("warning: model 'gpt' from the front matter is not one the harness accepts", "would drop"),
        ("warning: effort 'huge' from overrides.probe.effort is not one", "would drop"),
        ("warning: something new", "cannot tell whether it drops"),
    ],
)
def test_a_warning_that_may_drop_a_passed_value_refuses_the_run(
    runner: ModuleType, scene: Scene, warning: str, says: str
) -> None:
    _script(
        scene.adapter / "_resolve_agent.py",
        f"import sys\nprint({warning!r}, file=sys.stderr)\n{IDENTITY_RESOLVER}",
    )
    scene.harness([INIT, RESULT])
    assert says in _refusal(runner, scene)
    assert not scene.started()


def test_the_optional_read_warning_refuses_nothing(runner: ModuleType, scene: Scene) -> None:
    warning = "warning: optional category <conventions> is set with no value in overlay.yaml"
    _script(
        scene.adapter / "_resolve_agent.py",
        f"import sys\nprint({warning!r}, file=sys.stderr)\n{IDENTITY_RESOLVER}",
    )
    scene.harness([INIT, RESULT])
    assert _run(runner, scene)["ending"] == "finished"


def test_an_agent_the_deploy_would_not_pick_is_refused(runner: ModuleType, scene: Scene) -> None:
    scene.harness([INIT, RESULT])
    assert "holds no definition of nobody" in _refusal(runner, scene, agent="nobody")


def test_an_agent_file_leading_outside_the_working_copy_is_refused(
    runner: ModuleType, scene: Scene, tmp_path: Path
) -> None:
    outside = tmp_path / "outside.md"
    outside.write_text(AGENT_FILE, encoding="utf-8")
    source = scene.clone / ".pkit" / "agents" / "project" / "probe" / "probe.md"
    source.unlink()
    source.symlink_to(outside)
    scene.harness([INIT, RESULT])
    assert "leads outside the working copy" in _refusal(runner, scene)


def test_the_deploy_picks_the_project_then_a_capability_then_core(
    runner: ModuleType, tmp_path: Path
) -> None:
    pkit = tmp_path / ".pkit"
    core = pkit / "agents" / "core" / "a.md"
    later = pkit / "capabilities" / "zeta" / "agents" / "a" / "a.md"
    first = pkit / "capabilities" / "alpha" / "agents" / "a" / "a.md"
    flat = pkit / "capabilities" / "alpha" / "agents" / "a.md"
    project = pkit / "agents" / "project" / "a" / "a.md"
    picks = []
    for path in (core, later, first, flat, project):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x", encoding="utf-8")
        picks.append(runner.agent_source(tmp_path, "a"))
    assert picks == [core, later, first, flat, project]
    assert runner.agent_source(tmp_path, "b") is None


def test_only_the_runs_fields_are_passed_under_a_name_unique_to_the_run(
    runner: ModuleType, scene: Scene
) -> None:
    _agent(scene, AGENT_FILE.replace("owns: []\n", "owns: []\nmodel: sonnet\neffort: max\n"))
    scene.harness([INIT, RESULT])
    _run(runner, scene, effort="low")
    argv = scene.record()["argv"]
    name = argv[argv.index("--agent") + 1]
    assert re.fullmatch(r"pkit-run-[0-9a-f]{16}", name)
    agents = json.loads(argv[argv.index("--agents") + 1])
    assert agents == {
        name: {
            "description": "A probe agent.",
            "prompt": "\nYou are the probe.\n",
            "tools": RUN_TOOLS,
            "model": "sonnet",
            "effort": "low",
        }
    }


def test_the_definitions_own_effort_holds_where_the_caller_sets_none(
    runner: ModuleType, scene: Scene
) -> None:
    _agent(scene, AGENT_FILE.replace("owns: []\n", "owns: []\neffort: high\n"))
    definition = runner.checked_definition(
        scene.clone, "probe", None, scene.adapter / "_resolve_agent.py", scene.env()
    )
    assert definition["effort"] == "high"
    assert "model" not in definition


_needs_uv = pytest.mark.skipif(
    shutil.which("uv") is None, reason="the deploy's resolver runs on uv"
)


def _source_description(path: Path) -> str:
    line = next(
        line
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.startswith("description: ")
    )
    return line[len("description: ") :]


@_needs_uv
@pytest.mark.parametrize(
    "source",
    [
        ".pkit/capabilities/living-docs/agents/living-docs/living-docs.md",
        ".pkit/capabilities/software-analysis/agents/analysis-resolver/analysis-resolver.md",
    ],
)
def test_both_fixers_pass_the_check_as_they_stand(runner: ModuleType, source: str) -> None:
    path = REPO_ROOT / source
    agent = path.stem
    resolver = runner.resolver_of(REPO_ROOT)
    definition = runner.checked_definition(REPO_ROOT, agent, "medium", resolver, dict(os.environ))
    assert set(definition) == {"description", "prompt", "tools", "effort"}
    assert definition["description"] == _source_description(path)
    assert definition["tools"] == ["Read", "Glob", "Grep", "Bash", "Write"]
    assert definition["effort"] == "medium"
    # The storyboard is named by its path from the root, where the run reads it.
    assert (
        f"`{path.parent.relative_to(REPO_ROOT).as_posix()}/storyboard.md`" in definition["prompt"]
    )


@_needs_uv
def test_the_deploys_drop_of_a_model_refuses_the_run(runner: ModuleType, tmp_path: Path) -> None:
    adapter = tmp_path.joinpath(".pkit", "adapters", "claude-code")
    adapter.mkdir(parents=True)
    shutil.copy2(ADAPTER / "_resolve_agent.py", adapter / "_resolve_agent.py")
    agent = tmp_path.joinpath(".pkit", "agents", "project", "probe.md")
    agent.parent.mkdir(parents=True)
    agent.write_text(
        AGENT_FILE.replace("owns: []\n", "owns: []\nmodel: no-such-model\n"), encoding="utf-8"
    )
    with pytest.raises(
        runner.Refused, match=r"would drop a value the run passes.*: model 'no-such-model'"
    ):
        runner.checked_definition(
            tmp_path, "probe", None, adapter / "_resolve_agent.py", dict(os.environ)
        )


def test_the_shape_is_refs_declared_with_the_agents_identity_and_policy(
    runner: ModuleType,
) -> None:
    """The runner's set of fields is the methodology's: each field of `Declared`, with
    `reads` holding its three lists, and an agent's name, description, tools, model and
    effort."""
    tree = ast.parse(REFS.read_text(encoding="utf-8"))
    declared = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef) and node.name == "Declared"
    )
    fields = {
        node.target.id
        for node in declared.body
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
    }
    top = {"reads" if field.startswith("reads_") else field for field in fields}
    methodology = top | {"name", "description", "tools", "model", "effort"}
    assert methodology == runner.DEFINITION_FIELDS


# --- the front matter, as the resolver writes it -----------------------------------------


@pytest.mark.parametrize(
    ("lines", "value"),
    [
        (["A plain value."], "A plain value."),
        (
            ["The first, ", "  and the second line", "", "  after a break."],
            "The first, and the second line\nafter a break.",
        ),
        (["plain  # with a comment"], "plain"),
        (['"double \\"quoted\\" \\u00e9 \\t"'], 'double "quoted" é \t'),
        (['"over two ', '  lines"'], "over two lines"),
        (["'it''s single'"], "it's single"),
        (["|", "  line one", "  line two", ""], "line one\nline two\n"),
        (["|-", "  kept", "    indented"], "kept\n  indented"),
        ([">", "  folded", "  text", "", "  para"], "folded text\npara\n"),
    ],
)
def test_a_scalar_reads_as_yaml_reads_it(runner: ModuleType, lines: list[str], value: str) -> None:
    assert runner.scalar(lines, "description") == value


@pytest.mark.parametrize(
    "lines",
    [
        ["&anchor value"],
        ["*alias"],
        ["!tag value"],
        ["{a: b}"],
        ["key: value"],
        ['"no closing quote'],
        ['"bad \\q escape"'],
        ["|2", "  indented"],
        ["text", "  # a comment line"],
    ],
)
def test_a_scalar_the_runner_does_not_read_refuses(runner: ModuleType, lines: list[str]) -> None:
    with pytest.raises(runner.Refused, match="not in the form the runner reads"):
        runner.scalar(lines, "description")


@pytest.mark.parametrize(
    ("lines", "tools"),
    [
        (["[Read, Glob, Grep]"], ["Read", "Glob", "Grep"]),
        (["[Read, 'Bash',", "  Write]"], ["Read", "Bash", "Write"]),
        (["", "  - Read", "  - Write  # new files only"], ["Read", "Write"]),
        (["Read, Grep"], ["Read", "Grep"]),
        (["[]"], []),
    ],
)
def test_the_tools_read_in_each_form(
    runner: ModuleType, lines: list[str], tools: list[str]
) -> None:
    assert runner.tool_list(lines) == tools


@pytest.mark.parametrize(
    "lines", [["[Read, [Bash]]"], ["[Read"], ["", "  Read"], ["[Bash(git:*)]"]]
)
def test_tools_the_runner_does_not_read_refuse(runner: ModuleType, lines: list[str]) -> None:
    with pytest.raises(runner.Refused, match="not in the form the runner reads"):
        runner.tool_list(lines)


def test_the_front_matter_splits_into_its_fields(runner: ModuleType) -> None:
    text = (
        "# managed-by: a comment\n"
        "name: probe\n"
        "description: one\n  two\n"
        "reads:\n  paths:\n    - a\n"
        "owns:\n- b\n"
    )
    assert runner.front_matter(text) == {
        "name": ["probe"],
        "description": ["one", "  two"],
        "reads": ["", "  paths:", "    - a"],
        "owns": ["", "- b", ""],
    }
    for broken in ("name: a\nname: b\n", "name:a\n", "  indented first\n", "[flow]: x\n"):
        with pytest.raises(runner.Refused, match="not in the form the runner reads"):
            runner.front_matter(broken)


# --- the command line and the environment ---------------------------------------------------


def test_the_command_line_is_the_confined_closed_set(runner: ModuleType, scene: Scene) -> None:
    scene.harness([INIT, RESULT])
    _run(runner, scene, effort="high")
    argv = scene.record()["argv"]
    name = argv[argv.index("--agent") + 1]
    settings = argv[argv.index("--settings") + 1]
    agents = argv[argv.index("--agents") + 1]
    assert argv == [
        "-p",
        "--setting-sources",
        "",
        "--settings",
        settings,
        "--agents",
        agents,
        "--agent",
        name,
        "--permission-mode",
        "dontAsk",
        "--permission-prompts",
        "none",
        "--tools",
        "Read,Glob,Grep,Write,Bash",
        "--strict-mcp-config",
        "--disable-slash-commands",
        "--no-session-persistence",
        "--output-format",
        "stream-json",
        "--verbose",
        "--include-hook-events",
        "--effort",
        "high",
    ]
    assert json.loads(settings)["permissions"]["defaultMode"] == "dontAsk"
    assert set(runner.FLAGS) == {"-p", "--agent", "--effort"}


@pytest.mark.parametrize(
    "flag",
    [
        "--dangerously-skip-permissions",
        "--allow-dangerously-skip-permissions",
        "--permission-prompt-tool",
        "--allowedTools",
        "--allowed-tools",
        "--add-dir",
        "--mcp-config",
        "--restricted",
        "--plugin-dir",
        "--append-system-prompt",
    ],
)
def test_no_flag_outside_the_confined_set_is_ever_passed(runner: ModuleType, flag: str) -> None:
    with pytest.raises(runner.Refused, match="not in the closed set"):
        runner.check_flags(
            ["claude", "-p", flag, "x"], runner.CONFINED_FLAGS, runner.CONFINED_VALUES
        )


@pytest.mark.parametrize(
    ("flag", "value"),
    [
        ("--permission-mode", "bypassPermissions"),
        ("--permission-mode", "auto"),
        ("--permission-mode", "acceptEdits"),
        ("--permission-prompts", "host"),
        ("--setting-sources", "user,project"),
        ("--tools", "Read,Edit,Bash"),
        ("--output-format", "json"),
    ],
)
def test_a_confined_flag_takes_only_its_one_value(
    runner: ModuleType, flag: str, value: str
) -> None:
    with pytest.raises(runner.Refused, match="the form passes only"):
        runner.check_flags(
            ["claude", "-p", flag, value], runner.CONFINED_FLAGS, runner.CONFINED_VALUES
        )


def test_a_flag_passed_twice_is_refused(runner: ModuleType) -> None:
    argv = ["claude", "-p", "--permission-mode", "dontAsk", "--permission-mode", "dontAsk"]
    with pytest.raises(runner.Refused, match="twice"):
        runner.check_flags(argv, runner.CONFINED_FLAGS, runner.CONFINED_VALUES)


def test_the_environment_holds_only_what_the_run_needs(runner: ModuleType, scene: Scene) -> None:
    scene.harness([INIT, RESULT])
    _run(runner, scene)
    env = scene.record()["env"]
    env.pop("__CF_USER_TEXT_ENCODING", None)  # set by macOS for every process
    env.pop("LC_CTYPE", None)  # a locale variable Python may set for itself
    git = shutil.which("git")
    assert git is not None
    folders = env["PATH"].split(os.pathsep)
    assert folders[0] == str(scene.pkit_folder)
    assert folders[1] == str(scene.harness_bin)
    assert os.path.dirname(git) in folders
    assert folders[-4:] == ["/usr/bin", "/bin", "/usr/sbin", "/sbin"]
    # No `UV_*`, no configuration folder, nothing else of the person's; the
    # proxy and gateway variables pass, and both temp variables name the run's.
    assert {key: value for key, value in env.items() if key != "PATH"} == {
        "HOME": str(scene.home),
        "USER": "someone",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "ANTHROPIC_API_KEY": "a-key",
        "HTTPS_PROXY": "http://proxy:3128",
        "no_proxy": "localhost",
        "ANTHROPIC_BASE_URL": "https://gateway",
        "TMPDIR": str(scene.temp),
        "CLAUDE_CODE_TMPDIR": str(scene.temp),
        "CLAUDE_CODE_SUBPROCESS_ENV_SCRUB": "1",
        "PKIT_AGENT_RUN": "1",
    }


def test_the_harness_starts_in_the_workspace_with_the_brief_on_stdin(
    runner: ModuleType, scene: Scene
) -> None:
    scene.harness([INIT, RESULT])
    _run(runner, scene, brief="Propose --dangerously-skip-it")
    record = scene.record()
    assert Path(record["cwd"]).resolve() == scene.workspace.resolve()
    assert record["brief"] == "Propose --dangerously-skip-it"


# --- the stream: the start report, the result, and the end ----------------------------------


def test_a_confined_run_answers_with_the_agents_final_message_and_its_refused_calls(
    runner: ModuleType, scene: Scene
) -> None:
    scene.harness([INIT, {"type": "assistant", "message": {}}, TOOL_RESULT, RESULT], exit_code=0)
    answer = _run(runner, scene)
    assert answer == {
        "schema_version": 1,
        "ending": "finished",
        "exit_code": 0,
        "output": FINAL,
        "diagnostics": "a warning\n",
        "reason": "",
        "refused_calls": [{"tool": "Bash", "input": '{"command": "gh pr list"}'}],
        "start_report": INIT,
    }


def test_a_run_with_no_result_answers_no_message(runner: ModuleType, scene: Scene) -> None:
    scene.harness([INIT, "not json at all", TOOL_RESULT], exit_code=3)
    answer = _run(runner, scene)
    assert (answer["ending"], answer["exit_code"], answer["output"]) == ("finished", 3, "")
    assert answer["refused_calls"] == []


HOOK = {"type": "system", "subtype": "hook_started", "hook_name": "h", "hook_event": "SessionStart"}


@pytest.mark.parametrize(
    ("events", "says"),
    [
        ([{**INIT, "permissionMode": "default"}], "started in the mode 'default', not dontAsk"),
        ([{**INIT, "permissionMode": "bypassPermissions"}], "mode 'bypassPermissions'"),
        (
            [{**INIT, "tools": [*RUN_TOOLS, "Agent", "Edit"]}],
            "tools outside the run's: Agent, Edit",
        ),
        ([{**INIT, "mcp_servers": [{"name": "m", "status": "connected"}]}], "loaded MCP servers"),
        ([{**INIT, "mcp_server_errors": [{"name": "m"}]}], "loaded MCP servers"),
        ([{**INIT, "plugins": [{"name": "p", "path": "/p"}]}], "loaded plugins"),
        (
            [{k: v for k, v in INIT.items() if k != "plugins"}],
            "does not list the harness's plugins",
        ),
        ([HOOK, INIT], "ran a hook ('SessionStart', 'h')"),
        ([INIT, {**HOOK, "subtype": "hook_response"}], "ran a hook"),
        (
            [{"type": "assistant", "message": {}}, INIT],
            "reported 'assistant' before its start report",
        ),
    ],
)
def test_a_start_report_that_does_not_match_ends_the_run_at_once(
    runner: ModuleType, scene: Scene, events: list[Any], says: str
) -> None:
    scene.harness([*events, "SLEEP 60", RESULT])
    started = time.monotonic()
    answer = _run(runner, scene)
    assert time.monotonic() - started < 30
    assert answer["ending"] == "refused"
    assert "the run was ended at once" in answer["reason"]
    assert says in answer["reason"]
    assert answer["output"] == ""
    assert answer["exit_code"] is None
    # The report is kept where it came before what ended the run.
    reported = events[0].get("subtype") == "init"
    assert (answer["start_report"] is not None) is reported
    _assert_gone(scene.record()["pid"])


def test_a_run_with_no_start_report_is_refused(runner: ModuleType, scene: Scene) -> None:
    scene.harness([], exit_code=1)
    answer = _run(runner, scene)
    assert answer["ending"] == "refused"
    assert "gave no start report" in answer["reason"]
    assert "exited with 1" in answer["reason"]
    assert answer["start_report"] is None


@pytest.mark.serial
def test_at_the_limit_a_confined_run_is_ended(runner: ModuleType, scene: Scene) -> None:
    scene.harness([INIT, "SLEEP 60", RESULT])
    started = time.monotonic()
    answer = _run(runner, scene, limit_seconds=3)
    assert time.monotonic() - started < 30
    assert answer["ending"] == "timed-out"
    assert answer["start_report"] == INIT
    assert "within 3 s" in answer["reason"]
    _assert_gone(scene.record()["pid"])


def _assert_gone(pid: int) -> None:
    for _ in range(100):
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return
        time.sleep(0.05)
    os.kill(pid, signal.SIGKILL)
    pytest.fail(f"process {pid} outlived the run")


# --- the marker, and the answer to a refused confined request ---------------------------------


@pytest.mark.parametrize("value", ["1", ""])
def test_inside_a_run_a_confined_request_is_refused_with_the_confined_keys(
    scene: Scene, value: str
) -> None:
    scene.harness([INIT, RESULT])
    done = subprocess.run(
        [sys.executable, str(RUNNER)],
        input=json.dumps(scene.request()).encode(),
        capture_output=True,
        env={**scene.env(), "PKIT_AGENT_RUN": value},
        timeout=60,
        check=False,
    )
    assert done.returncode == 0, done.stderr
    answer = json.loads(done.stdout)
    assert answer["ending"] == "refused"
    assert "PKIT_AGENT_RUN is set" in answer["reason"]
    assert (answer["refused_calls"], answer["start_report"]) == ([], None)
    assert not scene.started()


# --- the probe ----------------------------------------------------------------------------------


def test_the_probe_starts_nothing_without_its_flag(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    probe = _load(PROBE, "claude_code_probe_under_test")

    def no_folder(*_args: object, **_kwargs: object) -> str:
        raise AssertionError("the probe made a folder")

    monkeypatch.setattr(probe.tempfile, "mkdtemp", no_folder)
    monkeypatch.setattr(probe.subprocess, "run", no_folder)
    assert probe.main([]) == 2
    assert "--start-claude" in capsys.readouterr().err


def test_the_probe_parses_as_python_3_9_and_imports_only_the_standard_library() -> None:
    """It loads the runner's functions, so it runs where the runner runs."""
    path = PROBE
    tree = ast.parse(path.read_text(encoding="utf-8"), feature_version=(3, 9))
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
    assert path.read_text(encoding="utf-8").startswith("#!/usr/bin/env python3\n")
    assert os.access(path, os.X_OK)
