"""The backbone's run command, `pkit agents run` (ADR-066 points 1, 2 and 10; #1742).

- the runner is the command a registered adapter registers under `run-agent`,
  found by the one lookup: a capability's command of that name is none, no
  runner refuses and names the adapters, two refuse and name both, and a
  runner whose script is gone is refused;
- a request with a problem is refused before any runner is looked for;
- the run reaches the harness through the claude-code adapter's runner: the
  closed set of flags, the brief on standard input, the folder, and none of the
  backbone's run variables;
- the runner's answer is read strictly: another version, a finished run with no
  exit, or a runner that exits without an answer is a run with no answer, and
  one that cannot start did not start;
- past the limit and its margin the runner is asked to stop before it is
  killed, and `SIGTERM` to `pkit agents run` stops the runner and its harness;
- the command's document, exits and usage errors.
"""

from __future__ import annotations

import dataclasses
import importlib.util
import json
import os
import signal
import stat
import subprocess
import sys
import time
from pathlib import Path
from types import ModuleType

import pytest
from click.testing import CliRunner

from project_kit import agent_runs, command_runner, run_cache
from project_kit.agent_runs import Request, run_agent
from project_kit.cli import main
from project_kit.manifest import (
    ComponentKind,
    ComponentRegistryEntry,
    read_backbone_manifest,
    write_backbone_manifest,
)
from tests.adopter_repo import MakeAdopterRepo

AGENT = "code-reviewer"

# A harness that records how it was started — its arguments, the brief on its
# standard input, its folder, and whether the backbone's run variables reached
# it — then answers as a reviewer does, and says something on standard error.
_RECORDING_HARNESS = """
import json, os, sys
brief = sys.stdin.read()
record = {
    "argv": sys.argv[1:],
    "brief": brief,
    "cwd": os.getcwd(),
    "run_variables": [k for k in ("PKIT_COMMAND_DEADLINE", "PKIT_COMMAND_STRAYS")
                      if k in os.environ],
}
open(os.environ["HARNESS_RECORD"], "w").write(json.dumps(record))
agent = sys.argv[sys.argv.index("--agent") + 1]
print(f"Reviewer agent (local, {agent}): APPROVED")
print("said on standard error", file=sys.stderr)
sys.exit(int(os.environ.get("HARNESS_EXIT", "0")))
"""

# A harness that records its pid and outlives any limit a test sets.
_LINGERING_HARNESS = """
import os, sys, time
open(os.environ["HARNESS_PID"], "w").write(str(os.getpid()))
time.sleep(60)
"""


def _script(path: Path, body: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"#!{sys.executable}\n{body}", encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return path


@pytest.fixture
def harness_bin(tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A directory first on PATH, for a fake `claude`."""
    bin_dir = tmp_path_factory.mktemp("harness-bin")
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}")
    return bin_dir


def _deploy_agent(folder: Path, name: str = AGENT) -> None:
    agents = folder / ".claude" / "agents"
    agents.mkdir(parents=True, exist_ok=True)
    (agents / f"{name}.md").write_text(f"---\nname: {name}\n---\nA reviewer.\n", encoding="utf-8")


def _register(
    root: Path,
    kind: ComponentKind,
    name: str,
    runner_body: str | None,
    script_path: str = "run-agent.py",
) -> Path:
    """Register a synthetic component of `kind` whose `commands:` tree names a
    `run-agent` leaf at `script_path`; its script is written with `runner_body`
    unless None."""
    area = "adapters" if kind == "adapter" else "capabilities"
    component_dir = root / ".pkit" / area / name
    component_dir.mkdir(parents=True, exist_ok=True)
    (component_dir / "package.yaml").write_text(
        f"schema_version: 1\ncomponent:\n  kind: {kind}\n  name: {name}\n  version: 0.1.0\n"
        "description: Synthetic component for agent-run tests.\n"
        'requires_backbone: ">=0.1.0"\n'
        f"commands:\n  run-agent:\n    script: {script_path}\n    help: Run an agent.\n",
        encoding="utf-8",
    )
    script = component_dir / script_path
    if runner_body is not None:
        _script(script, runner_body)
    backbone = read_backbone_manifest(root)
    assert backbone is not None
    backbone.components.append(
        ComponentRegistryEntry(kind=kind, name=name, manifest=f".pkit/{area}/{name}/manifest.yaml")
    )
    write_backbone_manifest(root, backbone)
    return script


def _drop_claude_code_runner(root: Path) -> None:
    package = root / ".pkit" / "adapters" / "claude-code" / "package.yaml"
    text = package.read_text(encoding="utf-8")
    package.write_text(text[: text.index("commands:")], encoding="utf-8")


def _request(in_folder: Path, **overrides: object) -> Request:
    return dataclasses.replace(
        Request(AGENT, "Review pull request 99.", in_folder, 30), **overrides
    )


# --- finding the runner -------------------------------------------------------


def test_the_runner_is_the_one_the_registered_adapter_registers(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    root = make_adopter_repo().root
    runners, adapters = agent_runs.find_runners(root)
    assert adapters == ["claude-code"]
    assert runners == [
        agent_runs.Runner(
            "claude-code", root / ".pkit" / "adapters" / "claude-code" / "run-agent.py"
        )
    ]
    assert os.access(runners[0].script, os.X_OK)


def test_a_capabilitys_command_of_that_name_is_no_runner(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    root = make_adopter_repo().root
    _register(root, "capability", "cap", "print('{}')\n")
    runners, _adapters = agent_runs.find_runners(root)
    assert [runner.adapter for runner in runners] == ["claude-code"]


def test_no_runner_refuses_and_names_the_adapters(
    make_adopter_repo: MakeAdopterRepo, tmp_path: Path
) -> None:
    root = make_adopter_repo().root
    _drop_claude_code_runner(root)
    run = run_agent(root, _request(tmp_path))
    assert run.ending == agent_runs.REFUSED
    assert run.runner is None
    assert "`run-agent`" in run.reason
    assert "registered adapters: claude-code" in run.reason


def test_two_runners_refuse_and_name_both(
    make_adopter_repo: MakeAdopterRepo, tmp_path: Path
) -> None:
    root = make_adopter_repo().root
    _register(root, "adapter", "other-harness", "print('{}')\n")
    run = run_agent(root, _request(tmp_path))
    assert run.ending == agent_runs.REFUSED
    assert "claude-code, other-harness" in run.reason


def test_a_runner_whose_script_is_gone_is_refused(
    make_adopter_repo: MakeAdopterRepo, tmp_path: Path
) -> None:
    root = make_adopter_repo().root
    _drop_claude_code_runner(root)
    _register(root, "adapter", "other-harness", None)
    run = run_agent(root, _request(tmp_path))
    assert (run.ending, run.runner) == (agent_runs.REFUSED, "other-harness")
    assert "does not exist" in run.reason


def test_a_runner_outside_its_adapters_folder_is_refused(
    make_adopter_repo: MakeAdopterRepo, tmp_path: Path
) -> None:
    root = make_adopter_repo().root
    _drop_claude_code_runner(root)
    _register(root, "adapter", "other-harness", "print('{}')\n", "../../capabilities/elsewhere.py")
    run = run_agent(root, _request(tmp_path))
    assert (run.ending, run.runner) == (agent_runs.REFUSED, "other-harness")
    assert "lies outside the adapter's folder" in run.reason


def test_an_adapter_whose_name_is_a_path_has_no_runner(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    """The lookup builds an adapter's folder only from a plain name, so no
    manifest entry makes a capability's command a runner."""
    root = make_adopter_repo().root
    _register(root, "adapter", "../capabilities/cap", "print('{}')\n")
    runners, adapters = agent_runs.find_runners(root)
    assert [runner.adapter for runner in runners] == ["claude-code"]
    assert "../capabilities/cap" in adapters


def test_a_run_inside_a_command_the_backbone_runs_is_refused_first(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """That run's kill asks nothing first, so the harness would outlive it."""
    monkeypatch.setattr(agent_runs.command_runner, "inherited_deadline", lambda: 1.0)
    # No project, and a request with a problem: the refusal comes before both.
    run = run_agent(tmp_path / "no-project", _request(tmp_path, brief=""))
    assert run.ending == agent_runs.REFUSED
    assert "inside a command the backbone runs" in run.reason


def _load(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_the_copies_across_the_three_layers_agree() -> None:
    """The adapter's runner runs under the system `python3` and the capability in
    its own environment, so neither imports the backbone. What each copies of
    the contract is held equal here."""
    repo = Path(__file__).resolve().parent.parent
    runner = _load(repo / ".pkit" / "adapters" / "claude-code" / "run-agent.py", "_runner_copy")
    pm = _load(
        repo
        / ".pkit"
        / "capabilities"
        / "project-management"
        / "scripts"
        / "_lib"
        / "agent_runs.py",
        "_pm_agent_runs_copy",
    )
    assert agent_runs.MAX_LIMIT_SECONDS == runner.MAX_LIMIT_SECONDS == pm.MAX_LIMIT_SECONDS
    assert tuple(agent_runs.EFFORT_LEVELS) == tuple(runner.EFFORT_LEVELS)
    assert agent_runs.AGENT_NAME.pattern == runner.AGENT_NAME.pattern
    assert (agent_runs.REQUEST_VERSION, agent_runs.ANSWER_VERSION) == (
        runner.REQUEST_VERSION,
        runner.ANSWER_VERSION,
    )
    assert agent_runs.DOCUMENT_VERSION == pm.VERSION
    assert set(agent_runs.RUNNER_ENDINGS) == {
        runner.FINISHED,
        runner.NOT_STARTED,
        runner.TIMED_OUT,
        runner.REFUSED,
    }
    assert set(agent_runs.ENDINGS) == set(pm.ENDINGS)
    assert set(runner.RUN_VARIABLES) == {
        command_runner.DEADLINE_ENV,
        command_runner.STRAYS_ENV,
        run_cache.CACHE_ENV,
    }
    assert agent_runs.RUNNER_MARGIN_SECONDS + command_runner.END_GRACE_SECONDS < pm.MARGIN_SECONDS
    assert command_runner.END_GRACE_SECONDS < pm.GRACE_SECONDS


# --- the request --------------------------------------------------------------


@pytest.mark.parametrize(
    ("overrides", "says"),
    [
        ({"agent": "--dangerously-skip-permissions"}, "is not a name"),
        ({"agent": "../agents/x"}, "is not a name"),
        ({"agent": "two words"}, "is not a name"),
        ({"brief": "  \n"}, "the brief is empty"),
        ({"brief": "a\0b"}, "NUL"),
        ({"folder": Path("relative")}, "is not a directory"),
        ({"limit_seconds": 0}, "the limit"),
        ({"limit_seconds": True}, "the limit"),
        ({"limit_seconds": agent_runs.MAX_LIMIT_SECONDS + 1}, "the limit"),
        ({"effort": "bypass"}, "effort 'bypass'"),
    ],
)
def test_a_request_with_a_problem_is_refused_before_any_runner(
    tmp_path: Path, overrides: dict[str, object], says: str
) -> None:
    # No project at all: the refusal comes before the runner is looked for.
    run = run_agent(tmp_path / "no-project", _request(tmp_path, **overrides))
    assert run.ending == agent_runs.REFUSED
    assert says in run.reason


# --- the run, through the claude-code adapter's runner --------------------------


def test_the_run_reaches_the_harness_through_the_adapters_runner(
    make_adopter_repo: MakeAdopterRepo,
    harness_bin: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = make_adopter_repo().root
    _deploy_agent(root)
    folder = root / "sub"
    folder.mkdir()
    _script(harness_bin / "claude", _RECORDING_HARNESS)
    record = tmp_path / "record.json"
    monkeypatch.setenv("HARNESS_RECORD", str(record))

    run = run_agent(root, _request(folder, effort="low", brief="Review PR 7.\nLine two."))

    assert (run.ending, run.exit_code, run.runner) == (agent_runs.FINISHED, 0, "claude-code")
    assert run.succeeded
    assert run.output == f"Reviewer agent (local, {AGENT}): APPROVED\n"
    assert run.diagnostics == "said on standard error\n"
    seen = json.loads(record.read_text(encoding="utf-8"))
    # The closed set of flags, and nothing else: the brief is on standard input.
    assert seen["argv"] == ["-p", "--agent", AGENT, "--effort", "low"]
    assert seen["brief"] == "Review PR 7.\nLine two."
    assert Path(seen["cwd"]).resolve() == folder.resolve()
    assert seen["run_variables"] == []


def test_the_harness_exit_is_the_runs(
    make_adopter_repo: MakeAdopterRepo,
    harness_bin: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = make_adopter_repo().root
    _deploy_agent(root)
    _script(harness_bin / "claude", _RECORDING_HARNESS)
    monkeypatch.setenv("HARNESS_RECORD", str(tmp_path / "record.json"))
    monkeypatch.setenv("HARNESS_EXIT", "3")
    run = run_agent(root, _request(root))
    assert (run.ending, run.exit_code) == (agent_runs.FINISHED, 3)
    assert not run.succeeded


# --- reading the runner's answer -------------------------------------------------


def _sole_runner(root: Path, body: str) -> Path:
    _drop_claude_code_runner(root)
    return _register(root, "adapter", "other-harness", body)


@pytest.mark.parametrize(
    ("answer", "says"),
    [
        ({"schema_version": 2, "ending": "finished", "exit_code": 0}, "schema_version 2"),
        ({"schema_version": 1, "ending": "finished"}, "no integer exit_code"),
        ({"schema_version": 1, "ending": "refused", "exit_code": 1}, "did not finish"),
        ({"schema_version": 1, "ending": "no-answer"}, "does not know"),
        ({"schema_version": 1, "ending": "finished", "exit_code": 0, "output": 7}, "output"),
        (["not", "an", "object"], "JSON object"),
    ],
)
def test_an_answer_the_backbone_cannot_read_is_no_answer(
    make_adopter_repo: MakeAdopterRepo, tmp_path: Path, answer: object, says: str
) -> None:
    root = make_adopter_repo().root
    _sole_runner(root, f"import json\nprint(json.dumps({answer!r}))\n")
    run = run_agent(root, _request(tmp_path))
    assert (run.ending, run.runner) == (agent_runs.NO_ANSWER, "other-harness")
    assert says in run.reason


def test_the_runners_answer_is_the_run(make_adopter_repo: MakeAdopterRepo, tmp_path: Path) -> None:
    root = make_adopter_repo().root
    answer = {"schema_version": 1, "ending": "refused", "exit_code": None, "reason": "no harness"}
    _sole_runner(root, f"import json, sys\nsys.stdin.read()\nprint(json.dumps({answer!r}))\n")
    run = run_agent(root, _request(tmp_path))
    assert (run.ending, run.reason, run.runner) == ("refused", "no harness", "other-harness")


def test_the_request_reaches_the_runner_on_standard_input(
    make_adopter_repo: MakeAdopterRepo, tmp_path: Path
) -> None:
    root = make_adopter_repo().root
    seen = tmp_path / "request.json"
    _sole_runner(
        root,
        "import json, sys\n"
        f"open({str(seen)!r}, 'w').write(sys.stdin.read())\n"
        "print(json.dumps({'schema_version': 1, 'ending': 'finished', 'exit_code': 0}))\n",
    )
    run_agent(root, _request(tmp_path, effort="high", limit_seconds=40))
    assert json.loads(seen.read_text(encoding="utf-8")) == {
        "schema_version": 1,
        "agent": AGENT,
        "brief": "Review pull request 99.",
        "folder": str(tmp_path),
        "limit_seconds": 40,
        "effort": "high",
    }


def test_a_runner_that_exits_without_an_answer_is_no_answer(
    make_adopter_repo: MakeAdopterRepo, tmp_path: Path
) -> None:
    root = make_adopter_repo().root
    _sole_runner(root, "import sys\nprint('boom', file=sys.stderr)\nsys.exit(4)\n")
    run = run_agent(root, _request(tmp_path))
    assert run.ending == agent_runs.NO_ANSWER
    assert "exited 4: boom" in run.reason


def test_a_runner_that_cannot_start_did_not_start(
    make_adopter_repo: MakeAdopterRepo, tmp_path: Path
) -> None:
    root = make_adopter_repo().root
    script = _sole_runner(root, "print('{}')\n")
    script.chmod(0o644)
    run = run_agent(root, _request(tmp_path))
    assert run.ending == agent_runs.NOT_STARTED
    assert "could not start" in run.reason


# Serial: the runner must set its handler inside a three-second bound, which a
# machine busy with other test workers misses.
@pytest.mark.serial
def test_past_its_bound_the_runner_is_asked_to_stop_before_it_is_killed(
    make_adopter_repo: MakeAdopterRepo, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = make_adopter_repo().root
    asked = tmp_path / "asked"
    _sole_runner(
        root,
        "import signal, sys, time\n"
        "def stop(signum, frame):\n"
        f"    open({str(asked)!r}, 'w').write(str(signum))\n"
        "    sys.exit(0)\n"
        "signal.signal(signal.SIGTERM, stop)\n"
        "time.sleep(60)\n",
    )
    # Two seconds of margin: a bound of three seconds.
    monkeypatch.setattr(agent_runs, "RUNNER_MARGIN_SECONDS", 2)
    started = time.monotonic()
    run = run_agent(root, _request(tmp_path, limit_seconds=1))
    assert time.monotonic() - started < 20
    assert run.ending == agent_runs.TIMED_OUT
    assert "did not answer within 3 s, its limit and 2 s to end the harness" in run.reason
    assert asked.read_text(encoding="utf-8") == str(int(signal.SIGTERM))


# --- the command ------------------------------------------------------------------


def test_the_command_writes_the_runs_document(
    make_adopter_repo: MakeAdopterRepo,
    harness_bin: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = make_adopter_repo().root
    _deploy_agent(root)
    _script(harness_bin / "claude", _RECORDING_HARNESS)
    monkeypatch.setenv("HARNESS_RECORD", str(tmp_path / "record.json"))
    result = CliRunner().invoke(
        main,
        ["agents", "run", AGENT, "--folder", str(root), "--limit", "30", "--json"],
        input="Review it.",
    )
    assert result.exit_code == 0, result.output
    document = json.loads(result.stdout)
    assert document == {
        "schema_version": 1,
        "agent": AGENT,
        "runner": "claude-code",
        "ending": "finished",
        "exit_code": 0,
        "output": f"Reviewer agent (local, {AGENT}): APPROVED\n",
        "diagnostics": "said on standard error\n",
        "reason": "",
    }
    assert list(json.loads(result.stdout.strip())) == sorted(document)


def test_without_json_the_command_prints_the_output_and_how_it_ended(
    make_adopter_repo: MakeAdopterRepo,
    harness_bin: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = make_adopter_repo().root
    _deploy_agent(root)
    _script(harness_bin / "claude", _RECORDING_HARNESS)
    monkeypatch.setenv("HARNESS_RECORD", str(tmp_path / "record.json"))
    monkeypatch.setenv("HARNESS_EXIT", "2")
    result = CliRunner().invoke(
        main, ["agents", "run", AGENT, "--folder", str(root), "--limit", "30"], input="Go."
    )
    assert result.exit_code == 1
    assert result.stdout == f"Reviewer agent (local, {AGENT}): APPROVED\n"
    assert f"agent {AGENT}: finished, exit 2" in result.stderr


def test_a_refused_run_exits_1_with_its_reason(
    make_adopter_repo: MakeAdopterRepo, tmp_path: Path
) -> None:
    root = make_adopter_repo().root
    _drop_claude_code_runner(root)
    result = CliRunner().invoke(
        main,
        ["agents", "run", AGENT, "--folder", str(tmp_path), "--limit", "5", "--json"],
        input="Go.",
    )
    assert result.exit_code == 1
    assert json.loads(result.stdout)["ending"] == "refused"


@pytest.mark.parametrize(
    ("args", "brief"),
    [
        (["--dangerously-skip-permissions", "--limit", "5"], "Go."),
        (["x y", "--limit", "5"], "Go."),
        ([AGENT, "--limit", "5"], ""),
        ([AGENT], "Go."),
        ([AGENT, "--limit", "0"], "Go."),
        ([AGENT, "--limit", "5", "--effort", "auto"], "Go."),
    ],
    ids=["flag-as-agent", "agent-with-space", "no-brief", "no-limit", "zero-limit", "bad-effort"],
)
def test_a_usage_error_exits_2(
    make_adopter_repo: MakeAdopterRepo, args: list[str], brief: str
) -> None:
    root = make_adopter_repo().root
    result = CliRunner().invoke(main, ["agents", "run", *args, "--folder", str(root)], input=brief)
    assert result.exit_code == 2, result.output


def test_sigterm_stops_the_runner_and_its_harness(
    make_adopter_repo: MakeAdopterRepo, harness_bin: Path, tmp_path: Path
) -> None:
    """A caller that ends `pkit agents run` at its own bound asks it with
    `SIGTERM`: the run stops its runner, which ends the harness."""
    root = make_adopter_repo().root
    _deploy_agent(root)
    _script(harness_bin / "claude", _LINGERING_HARNESS)
    pid_file = tmp_path / "harness.pid"
    env = {**os.environ, "HARNESS_PID": str(pid_file)}
    process = subprocess.Popen(
        [
            sys.executable,
            "-P",
            "-m",
            "project_kit",
            "agents",
            "run",
            AGENT,
            "--folder",
            str(root),
            "--limit",
            "60",
            "--json",
        ],
        cwd=root,
        env=env,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert process.stdin is not None
    process.stdin.write(b"Go.")
    process.stdin.close()
    for _ in range(600):
        if pid_file.is_file() and pid_file.read_text(encoding="utf-8"):
            break
        time.sleep(0.05)
    else:
        process.kill()
        pytest.fail("the harness never started")
    harness = int(pid_file.read_text(encoding="utf-8"))
    process.send_signal(signal.SIGTERM)
    assert process.wait(timeout=20) == 128 + signal.SIGTERM
    for _ in range(100):
        try:
            os.kill(harness, 0)
        except ProcessLookupError:
            return
        time.sleep(0.05)
    os.kill(harness, signal.SIGKILL)
    pytest.fail("the harness survived the stop")
