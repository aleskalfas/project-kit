"""The Claude Code adapter's agent runner, `run-agent.py` (ADR-066 points 1, 2, 4 and 10; #1742).

- it reads a request and refuses one it does not run: another version, a key
  of the confined form or any other, an agent that is no name, an empty brief,
  a folder that is not an absolute directory, a limit out of range, an effort
  outside the levels;
- it passes the harness the closed set of flags and nothing else, and refuses
  a command line with any other: none of the flags ADR-066 point 4 rules out
  can be passed;
- it finds the agent where Claude Code does, and refuses an agent that is not
  deployed, and a harness that is not on PATH;
- the harness gets the brief on standard input, starts in the folder, and gets
  none of the backbone's run variables;
- at the limit it ends the harness and every process still descended from it,
  a shell command in a session of its own included, and asked to stop it ends
  them first;
- the harness it runs is the one it found, even through a relative PATH entry;
- it runs under the system `python3` of a stock macOS: Python 3.9 syntax, the
  standard library only.
"""

from __future__ import annotations

import ast
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

REPO_ROOT = Path(__file__).resolve().parent.parent
RUNNER = REPO_ROOT / ".pkit" / "adapters" / "claude-code" / "run-agent.py"


@pytest.fixture(scope="module")
def runner() -> ModuleType:
    spec = importlib.util.spec_from_file_location("claude_code_run_agent_under_test", RUNNER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _request(in_folder: Path, **overrides: object) -> dict[str, object]:
    request: dict[str, object] = {
        "schema_version": 1,
        "agent": "code-reviewer",
        "brief": "Review pull request 99.",
        "folder": str(in_folder),
        "limit_seconds": 30,
        "effort": None,
    }
    request.update(overrides)
    return request


def _script(path: Path, body: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"#!{sys.executable}\n{body}", encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return path


def _deploy(folder: Path, name: str = "code-reviewer") -> None:
    agents = folder / ".claude" / "agents"
    agents.mkdir(parents=True, exist_ok=True)
    (agents / f"{name}.md").write_text("---\nname: x\n---\n", encoding="utf-8")


def _run(
    request: dict[str, object] | str, env: dict[str, str], cwd: Path | None = None
) -> dict[str, object]:
    text = request if isinstance(request, str) else json.dumps(request)
    done = subprocess.run(
        [sys.executable, str(RUNNER)],
        input=text.encode(),
        capture_output=True,
        env=env,
        cwd=cwd,
        timeout=60,
        check=False,
    )
    assert done.returncode == 0, done.stderr
    answer = json.loads(done.stdout)
    assert isinstance(answer, dict)
    return answer


@pytest.fixture
def env(tmp_path: Path) -> dict[str, str]:
    """An environment whose PATH starts with a folder for a fake `claude`, and
    whose own agents folder is empty."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    home = tmp_path / "home"
    home.mkdir()
    return {
        **os.environ,
        "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
        "CLAUDE_CONFIG_DIR": str(home),
    }


def _bin(env: dict[str, str]) -> Path:
    return Path(env["PATH"].split(os.pathsep)[0])


# --- the request ------------------------------------------------------------------


@pytest.mark.parametrize(
    ("overrides", "says"),
    [
        ({"schema_version": 2}, "schema_version is 2"),
        ({"commit": "abc"}, "keys this runner does not run: commit"),
        ({"settings": {}}, "keys this runner does not run: settings"),
        ({"agent": "--dangerously-skip-permissions"}, "is not a name"),
        ({"agent": "a/b"}, "is not a name"),
        ({"brief": ""}, "the brief is empty"),
        ({"brief": 7}, "the brief is empty"),
        ({"folder": "relative"}, "is not a directory"),
        ({"limit_seconds": 0}, "the limit 0"),
        ({"limit_seconds": True}, "the limit True"),
        ({"limit_seconds": 7 * 24 * 60 * 60 + 1}, "the limit"),
        ({"effort": "auto"}, "the effort 'auto'"),
    ],
)
def test_a_request_it_does_not_run_is_refused(
    runner: ModuleType, tmp_path: Path, overrides: dict[str, object], says: str
) -> None:
    with pytest.raises(runner.Refused, match=says):
        runner.read_request(json.dumps(_request(tmp_path, **overrides)))


def test_a_request_that_is_no_json_object_is_refused(runner: ModuleType) -> None:
    with pytest.raises(runner.Refused, match="not a JSON document"):
        runner.read_request("{nope")
    with pytest.raises(runner.Refused, match="not a JSON object"):
        runner.read_request("[1]")


# --- the closed set of flags ------------------------------------------------------


def test_the_command_line_is_the_closed_set(runner: ModuleType) -> None:
    assert runner.command("claude", "code-reviewer", None) == [
        "claude",
        "-p",
        "--agent",
        "code-reviewer",
    ]
    assert runner.command("claude", "code-reviewer", "low") == [
        "claude",
        "-p",
        "--agent",
        "code-reviewer",
        "--effort",
        "low",
    ]
    assert set(runner.FLAGS) == {"-p", "--agent", "--effort"}


@pytest.mark.parametrize(
    "flag",
    [
        "--dangerously-skip-permissions",
        "--allow-dangerously-skip-permissions",
        "--permission-mode",
        "--permission-prompt-tool",
        "--allowedTools",
        "--allowed-tools",
        "--add-dir",
        "--settings",
        "--agents",
        "--mcp-config",
    ],
)
def test_no_flag_outside_the_set_is_ever_passed(runner: ModuleType, flag: str) -> None:
    with pytest.raises(runner.Refused, match="not in the closed set"):
        runner.check_flags(["claude", "-p", flag, "bypassPermissions"])


def test_a_flags_value_never_reads_as_a_flag(runner: ModuleType) -> None:
    with pytest.raises(runner.Refused, match="with no value"):
        runner.check_flags(["claude", "-p", "--agent", "--dangerously-skip-permissions"])
    with pytest.raises(runner.Refused, match="with no value"):
        runner.check_flags(["claude", "-p", "--agent"])


# --- the agent, and the environment ----------------------------------------------------


def test_the_agent_is_found_where_claude_code_finds_it(runner: ModuleType, tmp_path: Path) -> None:
    project = tmp_path / "project"
    folder = project / "a" / "b"
    folder.mkdir(parents=True)
    home = tmp_path / "home"
    env = {"CLAUDE_CONFIG_DIR": str(home)}
    assert runner.agent_file("code-reviewer", folder, env) is None
    _deploy(tmp_path / "elsewhere")  # not above the folder: not found
    assert runner.agent_file("code-reviewer", folder, env) is None
    (home / "agents").mkdir(parents=True)
    (home / "agents" / "mine.md").write_text("x", encoding="utf-8")
    assert runner.agent_file("mine", folder, env) == home / "agents" / "mine.md"
    _deploy(project)
    assert runner.agent_file("code-reviewer", folder, env) == (
        project / ".claude" / "agents" / "code-reviewer.md"
    )


def test_the_harness_gets_none_of_the_backbones_run_variables(runner: ModuleType) -> None:
    env = {
        "PATH": "/bin",
        "HOME": "/home/x",
        "PKIT_COMMAND_DEADLINE": "1.0",
        "PKIT_COMMAND_STRAYS": "/tmp/x",
        "PKIT_RUN_CACHE": "/tmp/y",
    }
    assert runner.harness_environment(env) == {"PATH": "/bin", "HOME": "/home/x"}


# --- runs -----------------------------------------------------------------------------


def test_no_harness_on_path_is_refused(tmp_path: Path) -> None:
    _deploy(tmp_path)
    empty = tmp_path / "empty-bin"
    empty.mkdir()
    answer = _run(_request(tmp_path), {"PATH": str(empty), "HOME": str(tmp_path)})
    assert answer["ending"] == "refused"
    assert "`claude` command line is not on PATH" in str(answer["reason"])


def test_an_agent_not_deployed_is_refused(tmp_path: Path, env: dict[str, str]) -> None:
    _script(_bin(env) / "claude", "print('should not run')\n")
    answer = _run(_request(tmp_path), env)
    assert answer["ending"] == "refused"
    assert "is not deployed" in str(answer["reason"])


def test_a_run_finishes_with_the_harness_exit(tmp_path: Path, env: dict[str, str]) -> None:
    _deploy(tmp_path)
    record = tmp_path / "record.json"
    _script(
        _bin(env) / "claude",
        "import json, os, sys\n"
        f"open({str(record)!r}, 'w').write(json.dumps({{'argv': sys.argv[1:], "
        "'brief': sys.stdin.read(), 'cwd': os.getcwd(), "
        "'deadline': os.environ.get('PKIT_COMMAND_DEADLINE')}))\n"
        "print('the review')\nprint('a warning', file=sys.stderr)\nsys.exit(5)\n",
    )
    env = {**env, "PKIT_COMMAND_DEADLINE": "9999999999.0"}
    answer = _run(_request(tmp_path, effort="max", brief="Review --dangerously-skip-it"), env)
    assert answer == {
        "schema_version": 1,
        "ending": "finished",
        "exit_code": 5,
        "output": "the review\n",
        "diagnostics": "a warning\n",
        "reason": "",
    }
    seen = json.loads(record.read_text(encoding="utf-8"))
    assert seen["argv"] == ["-p", "--agent", "code-reviewer", "--effort", "max"]
    assert seen["brief"] == "Review --dangerously-skip-it"
    assert Path(seen["cwd"]).resolve() == tmp_path.resolve()
    assert seen["deadline"] is None


# A harness that starts what Claude Code starts: a child in its own process
# group, and a shell command in a session of its own, which starts a
# grandchild in a further session. It writes the pids of all four once they
# run, then outlives any limit a test sets.
_SPAWNING_HARNESS = """
import os, subprocess, sys, time
sleeper = [sys.executable, "-c", "import time; time.sleep(120)"]
in_group = subprocess.Popen(sleeper)
grandchild_pids = sys.argv[0] + ".grandchild"
shell = subprocess.Popen(
    [sys.executable, "-c",
     "import subprocess, sys, time\\n"
     "g = subprocess.Popen(sys.argv[1:-1], start_new_session=True)\\n"
     "open(sys.argv[-1], 'w').write(str(g.pid))\\n"
     "time.sleep(120)\\n",
     *sleeper, grandchild_pids],
    start_new_session=True,
)
while not (os.path.exists(grandchild_pids) and open(grandchild_pids).read()):
    time.sleep(0.05)
pids = [os.getpid(), in_group.pid, shell.pid, int(open(grandchild_pids).read())]
open(os.environ["HARNESS_PIDS"], "w").write(" ".join(str(pid) for pid in pids))
time.sleep(120)
"""


def _spawning_harness(tmp_path: Path, env: dict[str, str]) -> tuple[Path, dict[str, str]]:
    _deploy(tmp_path)
    pids = tmp_path / "pids"
    _script(_bin(env) / "claude", _SPAWNING_HARNESS)
    return pids, {**env, "HARNESS_PIDS": str(pids)}


def _wait_for(pids: Path) -> list[int]:
    for _ in range(600):
        if pids.is_file() and pids.read_text(encoding="utf-8"):
            return [int(pid) for pid in pids.read_text(encoding="utf-8").split()]
        time.sleep(0.05)
    pytest.fail("the harness never started what it starts")


# Serial: the harness must start its children and grandchild inside the run's
# limit, which a machine busy with other test workers misses.
@pytest.mark.serial
def test_at_the_limit_the_harness_and_every_descendant_are_ended(
    tmp_path: Path, env: dict[str, str]
) -> None:
    """Claude Code starts each shell command in a session of its own, which a
    kill of the harness's group alone would leave running."""
    pids, env = _spawning_harness(tmp_path, env)
    started = time.monotonic()
    answer = _run(_request(tmp_path, limit_seconds=5), env)
    assert time.monotonic() - started < 30
    assert answer["ending"] == "timed-out"
    assert answer["exit_code"] is None
    assert "within 5 s" in str(answer["reason"])
    assert "every process still descended from it" in str(answer["reason"])
    for pid in _wait_for(pids):
        _assert_gone(pid)


def test_asked_to_stop_it_ends_the_harness_and_every_descendant_first(
    tmp_path: Path, env: dict[str, str]
) -> None:
    pids, env = _spawning_harness(tmp_path, env)
    process = subprocess.Popen(
        [sys.executable, str(RUNNER)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )
    assert process.stdin is not None
    process.stdin.write(json.dumps(_request(tmp_path, limit_seconds=60)).encode())
    process.stdin.close()
    try:
        started = _wait_for(pids)
    except BaseException:
        process.kill()
        raise
    process.send_signal(signal.SIGTERM)
    assert process.wait(timeout=20) == 128 + signal.SIGTERM
    assert process.stdout is not None
    assert process.stdout.read() == b""  # no answer
    for pid in started:
        _assert_gone(pid)


def test_the_walk_finds_every_descendant_and_nothing_else(runner: ModuleType) -> None:
    table = {
        10: (1, 10),  # the harness
        11: (10, 10),  # a child in its group
        12: (10, 12),  # a shell command in a session of its own
        13: (12, 13),  # its child, in a further session
        20: (1, 20),  # unrelated
        21: (20, 20),
    }
    assert runner.descendants(10, table) == {11, 12, 13}
    assert runner.descendants(99, table) == set()


def test_the_process_table_lists_this_process(runner: ModuleType) -> None:
    table = runner.process_table()
    assert table[os.getpid()] == (os.getppid(), os.getpgrp())


def test_a_relative_path_entry_runs_the_harness_it_found(
    tmp_path: Path, env: dict[str, str]
) -> None:
    """A relative PATH entry is found from the runner's folder. The harness
    run is that one, never a `claude` the run's folder holds."""
    runner_folder = tmp_path / "runner"
    run_folder = tmp_path / "run"
    _deploy(run_folder)
    _script(runner_folder / "bin" / "claude", "print('the one found')\n")
    _script(run_folder / "bin" / "claude", "print('the run folder\\'s')\n")
    env = {**env, "PATH": f"bin{os.pathsep}{os.environ.get('PATH', '')}"}
    answer = _run(_request(run_folder), env, cwd=runner_folder)
    assert (answer["ending"], answer["output"]) == ("finished", "the one found\n")


def _assert_gone(pid: int) -> None:
    for _ in range(100):
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return
        time.sleep(0.05)
    os.kill(pid, signal.SIGKILL)
    pytest.fail(f"process {pid} outlived the run")


# --- the interpreter it runs under -------------------------------------------------------


def test_it_parses_as_python_3_9_and_imports_only_the_standard_library() -> None:
    tree = ast.parse(RUNNER.read_text(encoding="utf-8"), feature_version=(3, 9))
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
    assert RUNNER.read_text(encoding="utf-8").startswith("#!/usr/bin/env python3\n")
    assert os.access(RUNNER, os.X_OK)


@pytest.mark.skipif(not Path("/usr/bin/python3").is_file(), reason="no system python3")
def test_it_runs_under_the_system_python3(tmp_path: Path) -> None:
    """Where the system has its own `python3`, as a stock macOS has 3.9, the
    runner answers under it."""
    empty = tmp_path / "empty-bin"
    empty.mkdir()
    done = subprocess.run(
        ["/usr/bin/python3", str(RUNNER)],
        input=json.dumps(_request(tmp_path)).encode(),
        capture_output=True,
        env={"PATH": str(empty), "HOME": str(tmp_path)},
        timeout=60,
        check=False,
    )
    assert done.returncode == 0, done.stderr
    assert json.loads(done.stdout)["ending"] == "refused"
