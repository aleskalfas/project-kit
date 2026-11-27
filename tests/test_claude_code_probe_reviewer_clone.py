"""The probe of a reviewer's clone (ADR-102 point 6, its first and fourth facts).

- the probe starts nothing without its flag, nor inside an agent's run, and runs
  where the runner runs: Python 3.9 and the standard library;
- its clone is made from the code host as a reviewer's clone is: no object shared or
  borrowed, no hook, one remote that cannot push, the pull request's head fetched
  and checked, the default branch's head checked out with no branch, and its
  workspace;
- it adds to the runner's command line only the flags that make the stream readable,
  after the runner's own check;
- it reads the run's stream into calls, their results, the calls refused and the
  hooks' answers, and each fact holds only on what shows it;
- one command makes the clone, runs the reviewer there through the runner with the
  seat's rules, and reports each fact; a write that lands in the seat fails and is
  removed.

The "code host" is a bare repository on disk, which keeps a pull request's head under
`refs/pull/<N>/head` as GitHub does. A stub harness on a PATH the test builds stands in
for `claude`: no real agent starts.
"""

from __future__ import annotations

import ast
import importlib.util
import json
import os
import shutil
import stat
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
ADAPTER = REPO_ROOT / ".pkit" / "adapters" / "claude-code"
PROBE = ADAPTER / "probe-reviewer-clone.py"
RUNNER = ADAPTER / "run-agent.py"
DECLARATION = ADAPTER / "tool-access.json"
READER = REPO_ROOT / ".pkit" / "agents" / "tool_access.py"
PICKER = REPO_ROOT / ".pkit" / "agents" / "definition_source.py"
RECORDS_READER = REPO_ROOT / ".pkit" / "lifecycle" / "capability_records.py"

PULL = 7
SEAT_RULES = {"allow": ["Bash(gh:*)", "Bash(git:*)", "Write"], "deny": ["Bash(sudo:*)"]}

# A resolver that answers the runner's pick as the picker would for an agent of the
# project's place (ADR-087 point 2), and resolves a definition to its text.
IDENTITY_RESOLVER = (
    "import json, os, sys\n"
    "if sys.argv[1:2] == ['--pick']:\n"
    "    name = sys.argv[2]\n"
    "    path = os.path.join('.pkit', 'agents', 'project', name, f'{name}.md')\n"
    "    if os.path.lexists(path):\n"
    "        print(json.dumps({'name': name, 'shipped': True, 'place': 'project',\n"
    "                          'agent': os.path.join(os.getcwd(), path)}))\n"
    "    else:\n"
    "        print(json.dumps({'name': name, 'shipped': False}))\n"
    "    sys.exit(0)\n"
    "sys.stdout.write(open(sys.argv[1], encoding='utf-8').read())\n"
)

# A harness that answers `--version`, records how it was started, then works the
# brief's steps: it runs each git command in its folder for real, answers `gh` and
# `pkit` from its plan, and refuses the brief's write, or makes it where the plan
# says the write lands. It prints the stream a run with those calls gives.
STUB_HARNESS = """
import json, os, re, subprocess, sys
here = os.path.dirname(os.path.abspath(sys.argv[0]))
if sys.argv[1:] == ["--version"]:
    print("2.1.999 (Claude Code)")
    sys.exit(0)
brief = sys.stdin.read()
plan = json.load(open(os.path.join(here, "plan.json")))
open(os.path.join(here, "record.json"), "w").write(
    json.dumps({"argv": sys.argv[1:], "cwd": os.getcwd(), "brief": brief})
)
def emit(event):
    print(json.dumps(event), flush=True)
emit({"type": "system", "subtype": "init", "cwd": os.getcwd(), "permissionMode": "default"})
denials = []
for index, command in enumerate(re.findall(r"Run this shell command: (.+)", brief)):
    use = {"type": "tool_use", "id": f"t{index}", "name": "Bash", "input": {"command": command}}
    emit({"type": "assistant", "message": {"content": [use]}})
    if command.startswith("git "):
        text = subprocess.run(command.split(), capture_output=True, text=True).stdout
    else:
        text = plan[command.split()[0]]
    result = {"type": "tool_result", "tool_use_id": f"t{index}", "content": text}
    emit({"type": "user", "message": {"content": [result]}})
target = re.search(r"to the new file (\\S+)", brief).group(1)
use = {"type": "tool_use", "id": "w", "name": "Write", "input": {"file_path": target}}
emit({"type": "assistant", "message": {"content": [use]}})
answer = {"hookSpecificOutput": {"permissionDecision": "ask"}}
emit({"type": "system", "subtype": "hook_response", "hook_event": "PreToolUse",
      "hook_name": "PreToolUse:Write", "output": json.dumps(answer)})
if plan["land"]:
    open(target, "w").write("probe")
    result = {"type": "tool_result", "tool_use_id": "w", "content": "File created"}
else:
    denials.append({"tool_name": "Write", "tool_use_id": "w", "tool_input": {"file_path": target}})
    result = {"type": "tool_result", "tool_use_id": "w", "is_error": True,
              "content": "Claude requested permissions to write, but you haven't granted it yet."}
emit({"type": "user", "message": {"content": [result]}})
emit({"type": "result", "subtype": "success", "is_error": False, "result": "done",
      "permission_denials": denials})
"""


def _load(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # A dataclass reads its module's annotations from `sys.modules` while it is made.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _script(path: Path, body: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"#!{sys.executable}\n{body}", encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return path


def _git(root: Path, *args: str) -> str:
    """Run git in a test's own repository, never signing."""
    done = subprocess.run(
        ["git", "-c", "commit.gpgsign=false", *args],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return done.stdout.strip()


def _commit(root: Path, message: str) -> str:
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "--no-verify", "-m", message)
    return _git(root, "rev-parse", "HEAD")


@pytest.fixture
def probe() -> ModuleType:
    return _load(PROBE, "claude_code_probe_reviewer_clone_under_test")


@dataclass(frozen=True)
class CodeHost:
    """A bare repository standing in for the code host: `main` at `commit`, and pull
    request `PULL`'s head at `head`, a commit `main` does not hold."""

    bare: Path
    commit: str
    head: str


def _code_host(tmp_path: Path, files: dict[str, str] | None = None) -> CodeHost:
    work = tmp_path / "work"
    work.mkdir()
    _git(work, "init", "-q", "-b", "main")
    _git(work, "config", "user.email", "probe@example.invalid")
    _git(work, "config", "user.name", "Probe")
    (work / "README.md").write_text("the project\n", encoding="utf-8")
    for name, text in (files or {}).items():
        (work / name).parent.mkdir(parents=True, exist_ok=True)
        (work / name).write_text(text, encoding="utf-8")
    commit = _commit(work, "the default branch's head")
    _git(work, "checkout", "-q", "-b", "change")
    (work / "change.txt").write_text("the change\n", encoding="utf-8")
    head = _commit(work, "the change")
    bare = tmp_path / "host.git"
    _git(tmp_path, "clone", "-q", "--bare", str(work), str(bare))
    _git(bare, "update-ref", f"refs/pull/{PULL}/head", head)
    _git(bare, "branch", "-D", "change")
    return CodeHost(bare=bare, commit=commit, head=head)


def _host(probe: ModuleType, host: CodeHost, **overrides: Any) -> Any:
    fields: dict[str, Any] = {
        "name": "owner/repo",
        "url": str(host.bare),
        "default": "main",
        "pr": PULL,
        "head": host.head,
        **overrides,
    }
    return probe.Host(**fields)


# --- what it starts ------------------------------------------------------------------------------


def test_the_probe_starts_nothing_without_its_flag(
    probe: ModuleType, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def nothing(*_args: object, **_kwargs: object) -> str:
        raise AssertionError("the probe made or started something")

    monkeypatch.setattr(probe.tempfile, "mkdtemp", nothing)
    monkeypatch.setattr(probe.subprocess, "run", nothing)
    assert probe.main([]) == 2
    assert "--start-claude" in capsys.readouterr().err


def test_the_probe_starts_nothing_inside_an_agents_run(
    probe: ModuleType, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def nothing(*_args: object, **_kwargs: object) -> str:
        raise AssertionError("the probe made or started something")

    monkeypatch.setattr(probe.tempfile, "mkdtemp", nothing)
    monkeypatch.setattr(probe.subprocess, "run", nothing)
    monkeypatch.setenv("PKIT_AGENT_RUN", "")
    assert probe.main(["--start-claude"]) == 2
    assert "PKIT_AGENT_RUN is set" in capsys.readouterr().err


def test_the_probe_parses_as_python_3_9_and_imports_only_the_standard_library() -> None:
    """It loads the runner's functions, so it runs where the runner runs."""
    tree = ast.parse(PROBE.read_text(encoding="utf-8"), feature_version=(3, 9))
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
    assert PROBE.read_text(encoding="utf-8").startswith("#!/usr/bin/env python3\n")
    assert os.access(PROBE, os.X_OK)


# --- the clone -----------------------------------------------------------------------------------


def test_the_clone_is_made_from_the_code_host_as_a_reviewers_clone_is(
    probe: ModuleType, tmp_path: Path
) -> None:
    host = _code_host(tmp_path)
    clone = tmp_path / "scratch" / "clone"
    clone.parent.mkdir()
    assert probe.make_clone(_host(probe, host), clone) == host.commit
    git_dir = clone / ".git"
    assert not (git_dir / "objects" / "info" / "alternates").exists()
    hosted = {os.stat(path).st_ino for path in host.bare.rglob("*") if path.is_file()}
    held = [path for path in (git_dir / "objects").rglob("*") if path.is_file()]
    assert held and not {os.stat(path).st_ino for path in held} & hosted
    assert not (git_dir / "hooks").exists()
    assert _git(clone, "config", "core.hooksPath") == os.devnull
    assert _git(clone, "remote").split() == ["origin"]
    assert _git(clone, "remote", "get-url", "--push", "origin") == os.devnull
    pushed = subprocess.run(
        ["git", "push", "-q", "origin", f"{host.commit}:refs/heads/elsewhere"],
        cwd=clone,
        capture_output=True,
        check=False,
    )
    assert pushed.returncode != 0
    assert "elsewhere" not in _git(host.bare, "branch")
    assert (git_dir / "HEAD").read_text(encoding="utf-8").strip() == host.commit
    assert _git(clone, "rev-parse", f"refs/remotes/origin/pull/{PULL}/head") == host.head
    assert _git(clone, "symbolic-ref", "refs/remotes/origin/HEAD") == "refs/remotes/origin/main"
    workspace = clone / ".agent-workspace"
    assert workspace.is_dir() and stat.S_IMODE(workspace.stat().st_mode) == 0o700


def test_a_head_that_moved_refuses_the_clone(probe: ModuleType, tmp_path: Path) -> None:
    host = _code_host(tmp_path)
    clone = tmp_path / "clone"
    with pytest.raises(probe.ProbeError, match=r"head moved to .* run it again"):
        probe.make_clone(_host(probe, host, head=host.commit), clone)


def test_a_commit_that_holds_the_workspace_refuses_the_clone(
    probe: ModuleType, tmp_path: Path
) -> None:
    host = _code_host(tmp_path, {".agent-workspace/notes.md": "planted\n"})
    with pytest.raises(probe.ProbeError, match=r"holds something at `\.agent-workspace`"):
        probe.make_clone(_host(probe, host), tmp_path / "clone")


# --- the command line ----------------------------------------------------------------------------


def test_observing_adds_only_the_streams_flags_after_the_runners_own_check(
    probe: ModuleType,
) -> None:
    runner = _load(RUNNER, "claude_code_runner_for_the_reviewer_probe")
    settings = Path("/rules/settings.json")
    before = runner.command("claude", "a-reviewer", None, settings=settings)
    probe.observe(runner)
    after = runner.command("claude", "a-reviewer", None, settings=settings)
    assert after == [*before, *probe.OBSERVED]
    flags = {token for token in probe.OBSERVED if token.startswith("--")}
    # The flags the confined form passes to read its stream, and none that allows.
    assert flags <= set(runner.CONFINED_FLAGS)
    assert not flags & {"--settings", "--permission-mode", "--permission-prompts", "--agents"}


# --- the stream and the facts --------------------------------------------------------------------


def _use(call_id: str, tool: str, **given: str) -> dict[str, Any]:
    use = {"type": "tool_use", "id": call_id, "name": tool, "input": given}
    return {"type": "assistant", "message": {"content": [use]}}


def _result(call_id: str, content: Any, *, is_error: bool = False) -> dict[str, Any]:
    result = {"type": "tool_result", "tool_use_id": call_id, "content": content}
    if is_error:
        result["is_error"] = True
    return {"type": "user", "message": {"content": [result]}}


def _lines(*events: Any) -> str:
    return "".join(
        (event if isinstance(event, str) else json.dumps(event)) + "\n" for event in events
    )


def test_the_stream_gives_each_call_its_result_and_the_calls_refused(probe: ModuleType) -> None:
    stream = probe.read_stream(
        _lines(
            "a warning, no JSON",
            {"type": "system", "subtype": "init", "cwd": "/the/clone"},
            {"type": "system", "subtype": "init", "cwd": "/a/second/start"},
            _use("a", "Bash", command="git rev-parse HEAD"),
            _result("a", "abc\n"),
            _use("b", "Write", file_path="/seat/x.txt"),
            _result("b", [{"type": "text", "text": "refused"}], is_error=True),
            _result("unknown", "a result of no call"),
            {
                "type": "result",
                "subtype": "success",
                "permission_denials": [{"tool_name": "Write", "tool_use_id": "b"}, "junk"],
            },
        )
    )
    assert stream.init == {"type": "system", "subtype": "init", "cwd": "/the/clone"}
    assert set(stream.calls) == {"a", "b"}
    assert (stream.calls["a"].text, stream.calls["a"].is_error) == ("abc\n", False)
    assert (stream.calls["b"].text, stream.calls["b"].is_error) == ("refused", True)
    assert stream.refused == {"b"}
    assert stream.call("Bash", "rev-parse")[0] == "a"
    assert stream.call("Write", "/seat/x.txt")[0] == "b"
    assert stream.call("Bash", "/seat/x.txt") == (None, None)


def test_a_pretooluse_hooks_answer_is_read_from_whichever_field_holds_its_output(
    probe: ModuleType,
) -> None:
    asked = json.dumps({"hookSpecificOutput": {"permissionDecision": "ask"}})
    stream = probe.read_stream(
        _lines(
            {"type": "system", "subtype": "hook_started", "hook_event": "PreToolUse"},
            {
                "type": "system",
                "subtype": "hook_response",
                "hook_event": "PreToolUse",
                "hook_name": "PreToolUse:Write",
                "stdout": asked,
            },
            {
                "type": "system",
                "subtype": "hook_response",
                "hook_event": "PreToolUse",
                "hook_name": "PreToolUse:Bash",
                "output": "",
            },
            {
                "type": "system",
                "subtype": "hook_response",
                "hook_event": "SessionStart",
                "hook_name": "SessionStart:startup",
                "output": asked,
            },
        )
    )
    assert stream.hook_answers == ["PreToolUse:Write: ask", "PreToolUse:Bash: none"]


@dataclass(frozen=True)
class Shown:
    """What the facts are checked against: a run's events, its answer, and its folders."""

    scratch: Any
    host: Any
    passed: Any
    seat_rules: dict[str, Any] | None
    landed: bool


def _shown(probe: ModuleType, tmp_path: Path) -> Shown:
    scratch = probe.Scratch(
        root=tmp_path,
        clone=tmp_path / "clone",
        commit="c" * 40,
        rules=tmp_path / "rules",
        target=tmp_path / "seat" / "pkit-probe-1.txt",
    )
    host = probe.Host(name="owner/repo", url="u", default="main", pr=PULL, head="h" * 40)
    rules = {"allow": ["Bash(gh:*)"], "ask": [], "deny": []}
    return Shown(scratch, host, {"permissions": rules}, rules, False)


def _events(probe: ModuleType, shown: Shown, **changes: Any) -> list[Any]:
    """A run that shows every fact, less what `changes` names."""
    head, commit = shown.host.head, shown.scratch.commit
    target = str(shown.scratch.target)
    events: list[Any] = [
        {"type": "system", "subtype": "init", "cwd": changes.get("cwd", str(shown.scratch.clone))},
        _use("gh", "Bash", command=probe.GH.format(pr=PULL)),
        _result("gh", changes.get("gh", head + "\n")),
        _use("head", "Bash", command=probe.GIT_HEAD),
        _result("head", changes.get("head", commit + "\n")),
        _use("change", "Bash", command=probe.GIT_CHANGE.format(head=head)),
        _result("change", changes.get("change", head + "\n")),
        _use("check", "Bash", command=probe.CHECK),
        _result("check", "no artefact altered", is_error=changes.get("check_failed", False)),
    ]
    if not changes.get("no_write"):
        events += [
            _use("w", "Write", file_path=target),
            _result(
                "w",
                "File created" if changes.get("write_ran") else "refused",
                is_error=not changes.get("write_ran"),
            ),
        ]
    refused = changes.get("refused", [] if changes.get("write_ran") else ["w"])
    denials = [{"tool_name": "Bash", "tool_use_id": call_id} for call_id in refused]
    events.append({"type": "result", "subtype": "success", "permission_denials": denials})
    return events


def _holding(
    probe: ModuleType, shown: Shown, answer: dict[str, Any] | None = None, **changes: Any
) -> dict[str, bool]:
    stream = probe.read_stream(_lines(*_events(probe, shown, **changes)))
    checked = probe.facts(
        stream,
        answer or {"ending": "finished"},
        shown.scratch,
        shown.host,
        changes.get("passed", shown.passed),
        changes.get("seat_rules", shown.seat_rules),
        changes.get("landed", shown.landed),
    )
    return {name: holds for name, holds, _seen in checked}


def test_every_fact_holds_on_a_run_that_shows_them(probe: ModuleType, tmp_path: Path) -> None:
    held = _holding(probe, _shown(probe, tmp_path))
    assert len(held) == 7 and all(held.values()), held


@pytest.mark.parametrize(
    ("changes", "fails"),
    [
        ({"cwd": "/the/seat"}, "the run starts in the reviewer's clone"),
        ({"passed": {"permissions": {}, "hooks": {}}}, "the runner passes the seat's"),
        ({"seat_rules": None}, "the runner passes the seat's"),
        ({"refused": ["gh", "w"]}, "the code host's command line runs"),
        ({"gh": "another head\n"}, "the code host's command line runs"),
        ({"head": "another commit\n"}, "git runs with no prompt"),
        ({"change": "fatal: bad object\n"}, "git reads the change's head"),
        ({"check_failed": True}, "the methodology's check runs"),
        ({"no_write": True, "refused": []}, "a file tool's write into the seat's checkout"),
        ({"write_ran": True}, "a file tool's write into the seat's checkout"),
        ({"landed": True}, "a file tool's write into the seat's checkout"),
    ],
)
def test_each_fact_fails_on_what_breaks_it_alone(
    probe: ModuleType, tmp_path: Path, changes: dict[str, Any], fails: str
) -> None:
    held = _holding(probe, _shown(probe, tmp_path), **changes)
    assert [name for name, holds in held.items() if not holds] == [
        name for name in held if name.startswith(fails)
    ]


def test_a_run_that_did_not_finish_fails_the_first_fact(probe: ModuleType, tmp_path: Path) -> None:
    held = _holding(probe, _shown(probe, tmp_path), answer={"ending": "timed-out"})
    assert [name for name, holds in held.items() if not holds] == [
        "the run starts in the reviewer's clone, and finishes"
    ]


# --- one command ---------------------------------------------------------------------------------


@dataclass(frozen=True)
class Scene:
    seat: Path
    host: CodeHost
    harness_bin: Path
    scratch_parent: Path

    def record(self) -> dict[str, Any]:
        return json.loads((self.harness_bin / "record.json").read_text(encoding="utf-8"))

    def kept(self) -> Path:
        (kept,) = self.scratch_parent.iterdir()
        return kept


@pytest.fixture
def scene(probe: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Scene:
    """A code host whose commit holds what the runner reads to resolve an agent, this
    checkout's runner beside a resolver that answers as the picker would, a seat
    with its rules, and a stub harness first on the PATH."""
    files = {
        ".pkit/adapters/claude-code/tool-access.json": DECLARATION.read_text(encoding="utf-8"),
        ".pkit/agents/tool_access.py": READER.read_text(encoding="utf-8"),
        ".pkit/agents/definition_source.py": PICKER.read_text(encoding="utf-8"),
        ".pkit/lifecycle/capability_records.py": RECORDS_READER.read_text(encoding="utf-8"),
    }
    host = _code_host(tmp_path, files)
    here = tmp_path / "adapter"
    here.mkdir()
    shutil.copy2(RUNNER, here / RUNNER.name)
    _script(here / "_resolve_agent.py", IDENTITY_RESOLVER)
    seat = tmp_path / "seat"
    (seat / ".claude").mkdir(parents=True)
    settings = {"permissions": SEAT_RULES, "hooks": {"PreToolUse": []}, "sandbox": {}}
    (seat / ".claude" / "settings.json").write_text(json.dumps(settings), encoding="utf-8")
    harness_bin = tmp_path / "harness-bin"
    _script(harness_bin / "claude", STUB_HARNESS)
    plan = {"gh": host.head + "\n", "pkit": "no artefact altered\n", "land": False}
    (harness_bin / "plan.json").write_text(json.dumps(plan), encoding="utf-8")
    scratch_parent = tmp_path / "scratch"
    scratch_parent.mkdir()
    monkeypatch.setattr(probe, "HERE", here)
    monkeypatch.setattr(probe, "SEAT", seat)
    monkeypatch.setattr(probe, "read_host", lambda _seat, _pr: _host(probe, host))
    monkeypatch.setenv("PATH", f"{harness_bin}{os.pathsep}{os.environ.get('PATH', '')}")
    monkeypatch.delenv("PKIT_AGENT_RUN", raising=False)
    return Scene(seat=seat, host=host, harness_bin=harness_bin, scratch_parent=scratch_parent)


def _main(probe: ModuleType, scene: Scene) -> int:
    return probe.main(
        ["--start-claude", "--root", str(scene.scratch_parent), "--keep", "--limit", "120"]
    )


def test_one_command_runs_the_reviewer_in_its_clone_and_reports_each_fact(
    probe: ModuleType, scene: Scene, capsys: pytest.CaptureFixture[str]
) -> None:
    assert _main(probe, scene) == 0
    printed = capsys.readouterr().out
    verdicts = [line.split()[0] for line in printed.splitlines() if line[:4] in ("pass", "FAIL")]
    assert verdicts == ["pass"] * 7, printed
    assert "info  the PreToolUse hooks answered: PreToolUse:Write: ask (1)" in printed
    record = scene.record()
    kept = scene.kept()
    clone = kept / "clone"
    assert Path(record["cwd"]).resolve() == clone.resolve()
    argv = record["argv"]
    assert argv[-len(probe.OBSERVED) :] == list(probe.OBSERVED)
    passed = Path(argv[argv.index("--settings") + 1])
    assert passed.resolve() == (kept / "rules" / "settings.json").resolve()
    assert json.loads(passed.read_text(encoding="utf-8")) == {
        "permissions": {"allow": SEAT_RULES["allow"], "ask": [], "deny": SEAT_RULES["deny"]}
    }
    assert f"gh pr view {PULL} " in record["brief"]
    assert f"git log -1 --format=%H {scene.host.head}" in record["brief"]
    assert (clone / ".pkit" / "adapters" / "claude-code" / "run-agent.py").read_bytes() == (
        RUNNER.read_bytes()
    )
    assert list(scene.seat.iterdir()) == [scene.seat / ".claude"]


def test_a_write_that_lands_in_the_seat_fails_and_is_removed(
    probe: ModuleType, scene: Scene, capsys: pytest.CaptureFixture[str]
) -> None:
    plan = json.loads((scene.harness_bin / "plan.json").read_text(encoding="utf-8"))
    (scene.harness_bin / "plan.json").write_text(
        json.dumps({**plan, "land": True}), encoding="utf-8"
    )
    assert _main(probe, scene) == 1
    printed = capsys.readouterr().out
    assert "FAIL  a file tool's write into the seat's checkout" in printed
    assert "the file was written" in printed
    assert "which the run wrote" in printed
    assert list(scene.seat.iterdir()) == [scene.seat / ".claude"]


def test_a_code_host_that_cannot_be_read_refuses_and_leaves_nothing(
    probe: ModuleType,
    scene: Scene,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def unread(_seat: Path, _pr: int | None) -> Any:
        raise probe.ProbeError("the code host's repository: gh exited 1: not signed in")

    monkeypatch.setattr(probe, "read_host", unread)
    assert probe.main(["--start-claude", "--root", str(scene.scratch_parent)]) == 2
    assert "refused: the code host's repository: gh exited 1" in capsys.readouterr().err
    assert list(scene.scratch_parent.iterdir()) == []
    assert not (scene.harness_bin / "record.json").exists()
