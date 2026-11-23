"""The Claude Code adapter's probe of messaging between sessions (project-management DEC-081,
Context, and DEC-084, Implications; #3461).

- the probe starts nothing without its flag, nor inside an agent's run, nor its terminal part
  without a terminal, and refuses a harness older than messaging;
- it runs under the bare `python3`, as its own hook does;
- the probe agent withholds neither messaging tool, and each folder's settings make it the
  session's agent and register the hook on every event the probe reads;
- the scratch folder holds a clone with a linked worktree, another clone whose shell runs in
  the sandbox, a call allowed to leave it for the probe's outside copy, a folder for each other
  session, and the inbound cases' settings;
- the hook appends each event less the transcripts' paths, prints nothing and never fails; the
  scan names variables, never a value but the inbox's path and the session's id, and reads the
  session's process; the check tells a running process from an ended one;
- the results name no scratch, temp or home folder, no user and no machine, and each listing
  keeps only the probe's rows;
- what the evidence says: the tools an agent holds, whether a message was delivered, the
  folder a row shows, a session's own name from the listing's first line, a message's reply
  address against the sender's own, the session's process against its address, and a
  process's state as another clone sees it;
- the results file holds each measurement the parts run take, and its evidence fenced;
- with a stub harness, the headless part runs each of its runs, and the terminal part and the
  address part walk each of their steps, to the results file.

A stub harness on a PATH the test builds stands in for `claude`: no real session starts.
"""

from __future__ import annotations

import ast
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
PROBE = REPO_ROOT / ".pkit" / "adapters" / "claude-code" / "probe-messaging.py"

STUB = """#!/usr/bin/env python3
import json
import sys

args = sys.argv[1:]
if args[:1] == ["--version"]:
    print("2.1.330 (Claude Code)")
    sys.exit(0)
if args[:2] == ["agents", "--json"]:
    print("[]")
    sys.exit(0)
if "-p" in args:
    brief = sys.stdin.read()

    def emit(event):
        print(json.dumps(event), flush=True)

    emit({"type": "system", "subtype": "init", "tools": ["Bash", "Write", "SendMessage"]})
    if "sleep" in brief:
        use = {"type": "tool_use", "id": "t1", "name": "Bash", "input": {"command": "sleep 1"}}
        emit({"type": "assistant", "message": {"content": [use]}, "parent_tool_use_id": None})
    send = {"type": "tool_use", "id": "t2", "name": "SendMessage", "input": {"to": "x"}}
    emit({"type": "assistant", "message": {"content": [send]}, "parent_tool_use_id": None})
    result = {"type": "tool_result", "tool_use_id": "t2", "content": "Sent."}
    emit({"type": "user", "message": {"content": [result]}})
    emit({"type": "result", "result": "received=none\\nnotice=none"})
    sys.exit(0)
sys.exit(1)
"""


def _load() -> Any:
    spec = importlib.util.spec_from_file_location("claude_code_probe_messaging_under_test", PROBE)
    assert spec is not None and spec.loader is not None
    module: ModuleType = importlib.util.module_from_spec(spec)
    # A dataclass reads its module's annotations from `sys.modules` while it is made.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def probe_module() -> Any:
    return _load()


def _stub(tmp_path: Path) -> Path:
    folder = tmp_path / "bin"
    folder.mkdir()
    stub = folder / "claude"
    stub.write_text(STUB, encoding="utf-8")
    stub.chmod(0o755)
    return stub


def _probe(module: Any, tmp_path: Path, harness: Path) -> Any:
    root = tmp_path / "scratch"
    root.mkdir()
    module.make_scratch(root)
    scrub = module.Scrubber(root, tmp_path / "home", None, "someone", "somehost.local", None)
    report = module.Report(scrub, ["heading"])
    env = {key: value for key, value in os.environ.items() if key != "PKIT_AGENT_RUN"}
    return module.Probe(str(harness), root, env, report, root / "results.md", "--help")


# --- what the probe refuses ------------------------------------------------------------------


def test_the_probe_starts_nothing_without_its_flag(
    probe_module: Any, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def started(*_args: object, **_kwargs: object) -> str:
        raise AssertionError("the probe started something")

    monkeypatch.setattr(probe_module.tempfile, "mkdtemp", started)
    monkeypatch.setattr(probe_module.subprocess, "run", started)
    monkeypatch.setattr(probe_module.subprocess, "Popen", started)
    assert probe_module.main([]) == 2
    assert "--start-claude" in capsys.readouterr().err


def test_the_probe_starts_nothing_inside_an_agents_run(
    probe_module: Any, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("PKIT_AGENT_RUN", "1")
    assert probe_module.main(["--start-claude", "--part", "headless"]) == 2
    assert "agent's run" in capsys.readouterr().err


def test_the_terminal_part_needs_a_terminal(
    probe_module: Any, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("PKIT_AGENT_RUN", raising=False)
    monkeypatch.setattr(probe_module.sys.stdin, "isatty", lambda: False)
    assert probe_module.main(["--start-claude"]) == 2
    assert "--part headless" in capsys.readouterr().err


def test_a_harness_older_than_messaging_is_refused(probe_module: Any) -> None:
    assert probe_module.version_of("2.1.330 (Claude Code)") == (2, 1, 330)
    assert probe_module.version_refusal((2, 1, 224)) is None
    refusal = probe_module.version_refusal((2, 1, 223))
    assert refusal is not None and "2.1.224 or later" in refusal
    assert probe_module.version_refusal(None) is not None


def test_the_probe_parses_as_python_3_9_and_imports_only_the_standard_library() -> None:
    """It is its own hook, so it runs under the bare `python3` in every session it starts."""
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


# --- the scratch folder ----------------------------------------------------------------------


def test_the_probe_agent_withholds_neither_messaging_tool(probe_module: Any) -> None:
    front = probe_module.AGENT_FILE.split("---")[1]
    assert "\ntools:" not in front
    withheld = next(line for line in front.splitlines() if line.startswith("disallowedTools:"))
    for tool in ("Monitor", "PowerShell", "RemoteTrigger", "Workflow"):
        assert tool in withheld
    for tool in ("SendMessage", "ListAgents"):
        assert tool not in withheld


def test_a_folders_settings_make_the_probe_the_sessions_agent_and_hook_each_event(
    probe_module: Any, tmp_path: Path
) -> None:
    settings = probe_module.folder_settings(tmp_path)
    assert settings["agent"] == "pkit-probe"
    assert "crossSessionInbound" not in settings
    hooks = settings["hooks"]
    for event in ("SessionStart", "UserPromptSubmit", "SubagentStart", "SubagentStop"):
        assert hooks[event][0]["hooks"][0]["command"].endswith(f"--capture {tmp_path}")
    for event in ("PreToolUse", "PostToolUse"):
        assert {"SendMessage", "ListAgents", "Agent"} <= set(hooks[event][0]["matcher"].split("|"))
    command = hooks["SessionStart"][0]["hooks"][0]["command"]
    assert command.startswith(f"python3 {tmp_path / 'probe-messaging.py'} ")
    allow = settings["permissions"]["allow"]
    assert f"Edit(/{tmp_path}/evidence/**)" in allow
    assert [rule for rule in allow if rule.startswith("Edit(")] == [
        f"Edit(//{str(tmp_path).lstrip('/')}/evidence/**)"
    ]
    scan_rule = f"Bash(python3 {tmp_path / 'probe-messaging.py'} --scan-env:*)"
    assert scan_rule in allow
    assert probe_module.scan_command(tmp_path).startswith(scan_rule[5:-3])
    assert probe_module.folder_settings(tmp_path, "hold")["crossSessionInbound"] == "hold"


def test_the_scratch_folder_holds_a_clone_with_a_linked_worktree(
    probe_module: Any, tmp_path: Path
) -> None:
    probe_module.make_scratch(tmp_path)
    assert (tmp_path / "probe-messaging.py").read_bytes() == PROBE.read_bytes()
    clone, worktree = tmp_path / "clone", tmp_path / "clone-wt"
    committed = subprocess.run(
        ["git", "-C", str(clone), "ls-files"], capture_output=True, text=True, check=True
    ).stdout.split()
    assert ".claude/settings.json" in committed
    assert ".claude/agents/pkit-probe.md" in committed
    listed = subprocess.run(
        ["git", "-C", str(clone), "worktree", "list", "--porcelain"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert f"worktree {os.path.realpath(worktree)}" in listed
    assert (worktree / ".claude" / "settings.json").is_file()
    assert (worktree / "sub").is_dir()
    for name in ("twin", "held", "sender", "remote", "sink"):
        assert (tmp_path / name / ".claude" / "agents" / "pkit-probe.md").is_file()
    assert not (tmp_path / "build" / ".claude").exists()
    assert (tmp_path / "probe-outside.py").read_bytes() == PROBE.read_bytes()
    other = tmp_path / "other"
    assert (other / ".git").is_dir()
    sandbox = json.loads((other / ".claude" / "settings.json").read_text())["sandbox"]
    assert sandbox["enabled"] is True
    assert sandbox["allowUnsandboxedCommands"] is True
    assert "excludedCommands" not in sandbox
    for case in probe_module.INBOUND_CASES:
        written = json.loads(
            (tmp_path / f"inbound-{case.key}" / ".claude" / "settings.json").read_text()
        )
        assert written.get("crossSessionInbound") == case.project


# --- the hook and the scan -------------------------------------------------------------------


def test_the_hook_appends_each_event_less_the_transcripts_and_prints_nothing(
    tmp_path: Path,
) -> None:
    payload = {
        "hook_event_name": "SessionStart",
        "session_id": "s-1",
        "cwd": str(tmp_path),
        "transcript_path": "/somewhere/transcript.jsonl",
        "session_title": "pkit-probe-a",
    }
    env = {
        **os.environ,
        "SOME_NAME": "pkit-probe-a",
        "CLAUDE_CODE_MESSAGING_TOKEN": "a-secret-token",
        "CLAUDE_CODE_MESSAGING_SOCKET": "/tmp/cc-socks-501/s-1.sock",
    }
    done = subprocess.run(
        [sys.executable, str(PROBE), "--capture", str(tmp_path)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert (done.returncode, done.stdout, done.stderr) == (0, "", "")
    text = (tmp_path / "evidence" / "hooks.jsonl").read_text()
    assert "a-secret-token" not in text
    entry = json.loads(text)
    assert "transcript_path" not in entry
    assert entry["session_title"] == "pkit-probe-a"
    scan = entry["probe_environment"]
    assert scan["variables_naming_a_probe_session"] == ["SOME_NAME"]
    assert "CLAUDE_CODE_MESSAGING_TOKEN" in scan["claude_variables"]
    assert scan["messaging_socket"] == "/tmp/cc-socks-501/s-1.sock"


def test_the_hook_never_fails_the_session(tmp_path: Path) -> None:
    done = subprocess.run(
        [sys.executable, str(PROBE), "--capture", str(tmp_path / "missing" / "root")],
        input="not json",
        capture_output=True,
        text=True,
        check=False,
    )
    assert (done.returncode, done.stdout) == (0, "")


def test_the_scan_names_variables_and_no_value_but_the_inbox_and_the_session(
    tmp_path: Path,
) -> None:
    env = {
        **os.environ,
        "A_TITLE": "pkit-probe-b",
        "CLAUDE_CODE_MESSAGING_TOKEN": "a-secret-token",
        "CLAUDE_CODE_SESSION_ID": "s-2",
    }
    done = subprocess.run(
        [sys.executable, str(PROBE), "--scan-env", str(tmp_path)],
        capture_output=True,
        text=True,
        env=env,
        check=True,
    )
    assert "a-secret-token" not in done.stdout
    scan = json.loads(done.stdout)["probe_scan"]
    assert scan["variables_naming_a_probe_session"] == ["A_TITLE"]
    assert scan["session_id"] == "s-2"


def test_the_scan_reads_the_sessions_process_and_the_processes_its_shell_runs_under(
    tmp_path: Path,
) -> None:
    """This test's own process stands for the session's: the scan's shell runs under it."""
    me = os.getpid()
    env = {
        **os.environ,
        "CLAUDE_PID": str(me),
        "CLAUDE_CODE_MESSAGING_SOCKET": f"/tmp/cc-socks/{me}.sock",
    }
    done = subprocess.run(
        [sys.executable, str(PROBE), "--scan-env", str(tmp_path)],
        capture_output=True,
        text=True,
        env=env,
        check=True,
    )
    scan = json.loads(done.stdout)["probe_scan"]
    assert (scan["claude_pid"], scan["socket_pid"]) == (me, me)
    assert scan["process_start"]
    assert scan["chain"][0]["pid"] == me
    assert scan["confined"] is False
    assert not list(tmp_path.glob("confinement-*"))


def test_the_check_tells_a_running_process_from_an_ended_one(
    probe_module: Any, tmp_path: Path
) -> None:
    me = os.getpid()
    start, _ = probe_module.ps_field(me, "lstart")
    assert start
    running = probe_module.check_process(tmp_path, me, start)
    assert running["signal"] == "exists"
    assert probe_module.liveness_reading(running, live=True).startswith("tells it runs")
    ended = subprocess.Popen([sys.executable, "-c", "pass"])
    ended.wait()
    gone = probe_module.check_process(tmp_path, ended.pid, start)
    assert gone["signal"] == "no such process"
    assert probe_module.liveness_reading(gone, live=False) == (
        "tells it ended: ps shows no process under its id"
    )
    printed = subprocess.run(
        [sys.executable, str(PROBE), "--check-process", str(tmp_path), str(me), start],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert json.loads(printed)["probe_check"]["start"] == start


# --- keeping the person's data out of the results --------------------------------------------


def test_the_scrubber_names_no_folder_user_machine_or_id(probe_module: Any, tmp_path: Path) -> None:
    home = tmp_path / "home"
    root = home / ".cache" / "pkit-messaging-probe-x"
    scrub = probe_module.Scrubber(root, home, "/var/tmp/T/", "someone", "box.example.org", 501)
    text = (
        f"{root}/clone {home}/other /var/tmp/T/sock someone@box someone-else "
        "box.example.org /tmp/cc-socks-501/a /tmp/cc-socks-5012/b"
    )
    assert scrub(text) == (
        "<scratch>/clone ~/other $TMPDIR/sock <user>@<host> someone-else <host> "
        "/tmp/cc-socks-<uid>/a /tmp/cc-socks-5012/b"
    )


def test_a_listing_keeps_only_the_probes_rows(probe_module: Any) -> None:
    text = "\n".join(
        [
            "You are pkit-probe-a",
            "  my-secret-project  ~/work/secret",
            "  pkit-probe-b  <scratch>/clone-wt",
            "     address: b-1",
            "  another  ~/elsewhere",
            "  yet another  ~/more",
        ]
    )
    assert probe_module.kept_lines(text) == "\n".join(
        [
            "You are pkit-probe-a",
            "[1 lines about other sessions left out]",
            "  pkit-probe-b  <scratch>/clone-wt",
            "     address: b-1",
            "[2 lines about other sessions left out]",
        ]
    )
    rows = {"self": "pkit-probe-a", "rows": [{"name": "pkit-probe-b"}, {"name": "secret"}]}
    assert probe_module.kept_items(rows) == {
        "self": "pkit-probe-a",
        "rows": [{"name": "pkit-probe-b"}, "[1 rows about other sessions left out]"],
    }


# --- what the evidence says ------------------------------------------------------------------


def test_the_hook_log_reads_one_folders_events_after_a_mark(
    probe_module: Any, tmp_path: Path
) -> None:
    clone, worktree = tmp_path / "clone", tmp_path / "clone-wt"
    log = tmp_path / "hooks.jsonl"
    entries = [
        {"hook_event_name": "SessionStart", "cwd": str(clone)},
        {"hook_event_name": "PreToolUse", "cwd": str(clone / "sub"), "tool_name": "ListAgents"},
        {"hook_event_name": "PreToolUse", "cwd": str(worktree), "tool_name": "SendMessage"},
    ]
    log.write_text("".join(json.dumps(entry) + "\n" for entry in entries) + "{torn")
    reader = probe_module.HookLog(log)
    assert reader.mark() == 3
    assert [entry["tool_name"] for entry in reader.since(1, clone)] == ["ListAgents"]
    assert [entry["tool_name"] for entry in reader.since(0, worktree)] == ["SendMessage"]


def test_what_an_agent_holds_comes_from_its_calls_or_its_list(
    probe_module: Any, tmp_path: Path
) -> None:
    holds = probe_module.holds
    assert holds("ListAgents", {"ListAgents"}, None) == "held: it called it"
    assert holds("ListAgents", set(), ["Read", "ListAgents"]) == "held: it lists it"
    assert holds("ListAgents", {"Write"}, ["Read"]).startswith("not held")
    assert holds("ListAgents", {"Write"}, None).startswith("not held")
    assert holds("ListAgents", set(), None).startswith("undetermined")
    entries = [
        {
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "agent_id": "fg-1",
            "tool_input": {"file_path": str(tmp_path / "m1-terminal-foreground.txt")},
        },
        {"hook_event_name": "PreToolUse", "tool_name": "ListAgents", "agent_id": "fg-1"},
        {"hook_event_name": "PreToolUse", "tool_name": "SendMessage", "agent_id": "fg-1"},
        {
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "agent_id": "bg-1",
            "tool_input": {"file_path": str(tmp_path / "m1-terminal-background.txt")},
        },
        {"hook_event_name": "PreToolUse", "tool_name": "SendMessage", "agent_id": "bg-1"},
        {"hook_event_name": "PreToolUse", "tool_name": "ListAgents"},
    ]
    (tmp_path / "m1-terminal-background.txt").write_text("Read, Write, SendMessage")
    readings = probe_module.subagent_readings(entries, tmp_path, "terminal")
    assert readings["a foreground subagent"] == {
        "SendMessage": "held: it called it",
        "ListAgents": "held: it called it",
    }
    background = readings["a background subagent"]
    assert background["SendMessage"] == "held: it called it"
    assert background["ListAgents"] == "not held: it neither calls nor lists it"
    assert probe_module.calls(entries, None) == {"ListAgents"}
    assert probe_module.tool_summary("a background subagent", background) == (
        "a background subagent: SendMessage held, ListAgents not held"
    )


def test_a_stream_gives_the_start_report_the_calls_and_their_results(probe_module: Any) -> None:
    events = [
        {"type": "system", "subtype": "init", "tools": ["Bash"]},
        {
            "type": "assistant",
            "parent_tool_use_id": None,
            "message": {"content": [{"type": "tool_use", "id": "t1", "name": "ListAgents"}]},
        },
        {
            "type": "assistant",
            "parent_tool_use_id": "t0",
            "message": {"content": [{"type": "tool_use", "id": "t2", "name": "ListAgents"}]},
        },
        {
            "type": "user",
            "message": {
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "t1",
                        "content": [{"type": "text", "text": "pkit-probe-b"}],
                    }
                ]
            },
        },
        {"type": "system", "subtype": "notice", "text": "held probe-m5-x"},
        {"type": "result", "result": "done\n`received=none`"},
    ]
    assert probe_module.init_event(events) == events[0]
    assert [use["parent"] for use in probe_module.tool_uses(events)] == [None, "t0"]
    assert probe_module.first_use(events, "ListAgents")["id"] == "t1"
    assert probe_module.tool_result(events, "t1") == "pkit-probe-b"
    assert probe_module.tool_result(events, "t2") is None
    assert probe_module.said(probe_module.final_text(events), "received") == "none"
    assert probe_module.carried(events, "probe-m5-x") == ["system/notice"]
    assert probe_module.sleeping(events) is False


def test_a_message_is_delivered_only_where_it_reached_the_receiving_claude(
    probe_module: Any,
) -> None:
    delivery = probe_module.delivery
    assert delivery(["probe-m: hi"], None, [], "probe-m") == "delivered"
    assert delivery([], "probe-m: hi", [], "probe-m") == "delivered"
    assert delivery([], "none", ["system/notice"], "probe-m").startswith("not delivered, though")
    assert delivery([], None, [], "probe-m") == "not delivered"


def test_the_folder_a_row_shows_is_read_from_that_row_alone(probe_module: Any) -> None:
    text = "\n".join(
        [
            "pkit-probe-build  <scratch>/build",
            "pkit-probe-b",
            "   <scratch>/clone-wt/sub",
            "pkit-probe-a  <scratch>/clone",
        ]
    )
    assert probe_module.row_paths(text, "pkit-probe-b") == ["<scratch>/clone-wt/sub"]
    rows = [
        {"name": "pkit-probe-b", "cwd": "<scratch>/clone-wt"},
        {"name": "pkit-probe-a", "cwd": "<scratch>/clone"},
    ]
    assert probe_module.row_paths(rows, "pkit-probe-b") == ["<scratch>/clone-wt"]
    reading = probe_module.folder_reading
    started, moved = "<scratch>/clone-wt", "<scratch>/clone-wt/sub"
    assert "moved to" in reading([moved], started, moved)
    assert "started in" in reading([started], started, moved)
    assert reading([], started) == "the row shows no folder of the probe's"


def test_a_sessions_own_name_is_read_from_the_listings_first_line(
    probe_module: Any, tmp_path: Path
) -> None:
    """The hook sees the listing as a structure; its first line read as JSON would be `{`."""
    listing = {
        "listing": "This session is pkit-probe-a [5c2091] — the name other sessions use\n\n"
        "Peer sessions (1):\n  pkit-probe-b [aa11bb]  ·  interactive  ·  idle",
        "sections": [{"kind": "sessions", "rows": [{"name": "pkit-probe-b"}]}],
    }
    assert probe_module.listing_text(listing).startswith("This session is pkit-probe-a")
    assert probe_module.listing_text("plain text") == "plain text"
    probe = _probe(probe_module, tmp_path, tmp_path / "no-harness")
    entries = [
        {"hook_event_name": "PostToolUse", "tool_name": "ListAgents", "tool_response": listing}
    ]
    probe_module.name_findings(probe, "a session", entries, [], probe.path("clone"))
    assert "a session: the session reads its name through the listing's first line" in (
        probe.report.render()
    )


def test_a_messages_reply_address_is_read_from_its_frame_and_compared_with_the_senders_own(
    probe_module: Any,
) -> None:
    frame = (
        '<cross-session-message from="uds:/tmp/cc-socks/41.sock" from-name="pkit-probe-a" '
        'from-mode="prompting">\nprobe-m9-first: no answer is needed.\n</cross-session-message>'
    )
    assert probe_module.message_sender(frame) == ("uds:/tmp/cc-socks/41.sock", "pkit-probe-a")
    assert probe_module.message_sender(None) == (None, None)
    same = probe_module.same_address
    assert same("uds:/tmp/cc-socks/41.sock", "/tmp/cc-socks/41.sock")
    assert same("/tmp/cc-socks/41.sock", "/tmp/cc-socks/41.sock")
    assert not same("uds:/tmp/cc-socks/42.sock", "/tmp/cc-socks/41.sock")
    assert not same(None, "/tmp/cc-socks/41.sock")
    reading = probe_module.second_address_reading
    one, two = "/tmp/cc-socks/41.sock", "/tmp/cc-socks/42.sock"
    assert reading((f"uds:{one}", one), (f"uds:{two}", two)).startswith("holds")
    assert reading((f"uds:{one}", one), (f"uds:{one}", two)).startswith("does not hold")
    assert "not the address its own shell reads" in reading(
        (f"uds:{one}", two), (f"uds:{two}", two)
    )
    assert "read no address" in reading((f"uds:{one}", None), (f"uds:{two}", two))
    assert reading((None, one), (f"uds:{two}", two)) == (
        "not measured: no message from the first session arrived"
    )
    subagent = probe_module.subagent_address_reading
    assert "session's own" in subagent("a subagent", f"uds:{one}", one, one)
    assert "of its own" in subagent("a subagent", f"uds:{two}", one, two)
    assert "another address" in subagent("a subagent", "uds:/x", one, two)
    assert "no message" in subagent("a subagent", None, one, two)


def test_the_sessions_process_is_read_against_the_process_its_address_names(
    probe_module: Any,
) -> None:
    reading = probe_module.process_reading
    chain = [{"pid": 7, "command": "zsh"}, {"pid": 41, "command": "claude"}]
    scan = {"claude_pid": 41, "socket_pid": 41, "chain": chain, "socket_held": "yes"}
    assert reading(scan).startswith("holds") and "lsof shows it holds" in reading(scan)
    assert reading({**scan, "socket_pid": 42}).startswith("does not hold")
    assert "not among" in reading({**scan, "chain": chain[:1]})
    assert reading({**scan, "socket_held": "no"}).startswith("does not hold as lsof shows it")
    assert reading({**scan, "claude_pid": None}).startswith("cannot tell")
    assert reading(None).startswith("not measured")


def test_a_check_says_where_it_ran_and_what_it_could_tell(probe_module: Any) -> None:
    where = probe_module.where_checked
    assert where({"copy": "probe-outside.py", "confined": False}) == "a command outside the sandbox"
    assert where({"copy": "probe-messaging.py", "confined": True}) == "a command in the sandbox"
    assert "though the session was asked to run it outside" in where(
        {"copy": "probe-outside.py", "confined": True}
    )
    liveness = probe_module.liveness_reading
    unread = {"start": None, "start_unread": "operation not permitted", "signal": "not permitted"}
    assert liveness(unread, live=True).startswith("cannot tell")
    other = {"start": "Tue", "recorded_start": "Mon", "start_unread": None}
    assert liveness(other, live=True).startswith("does not tell it runs")
    assert liveness(other, live=False) == "tells it ended: another process holds its id"
    still = {"start": "Mon", "recorded_start": "Mon", "start_unread": None}
    assert liveness(still, live=False).startswith("does not tell it ended")
    assert liveness(None, live=True).startswith("not measured")


def test_the_inbound_settings_are_read_from_each_file_that_may_set_them(
    probe_module: Any, tmp_path: Path
) -> None:
    home = tmp_path
    user = home / ".claude" / "settings.json"
    user.parent.mkdir()
    user.write_text(
        json.dumps({"crossSessionInbound": "hold", "permissions": {"defaultMode": "auto"}})
    )
    lines = probe_module.inbound_settings(
        home, "plan9", {"CLAUDE_CODE_USER_DIALOG_TIMEOUT_MS": "5"}
    )
    assert lines[0].startswith("user settings")
    assert '`crossSessionInbound` = `"hold"`' in lines[0]
    assert '`permissions.defaultMode` = `"auto"`' in lines[0]
    assert lines[1] == "`CLAUDE_CODE_USER_DIALOG_TIMEOUT_MS` is `5` in the probe's environment"
    user.write_text("{")
    assert "could not be read" in probe_module.inbound_settings(home, "plan9", {})[0]
    user.unlink()
    assert "set none of them" in probe_module.inbound_settings(home, "plan9", {})[0]


# --- the results -----------------------------------------------------------------------------


def test_the_results_hold_each_measurement_with_its_evidence_scrubbed(
    probe_module: Any, tmp_path: Path
) -> None:
    root = tmp_path / "scratch"
    scrub = probe_module.Scrubber(root, tmp_path, None, "someone", "somehost", None)
    report = probe_module.Report(scrub, ["Claude Code 2.1.330."])
    report.result(1, f"held in {root}/clone")
    report.answer(3, "Same address?", "yes")
    listing = (
        f"You are pkit-probe-a\nsecret-session {tmp_path}/secret\npkit-probe-b {root}/clone-wt"
    )
    report.attach(4, "a listing", listing, listing=True)
    report.attach(6, "a block", "```\ninner\n```")
    text = report.render()
    assert str(tmp_path) not in text
    assert "secret" not in text
    assert "| 1. The tools reach the agent | held in <scratch>/clone |" in text
    assert "| 2. A session's own name | not measured |" in text
    for number in range(1, 9):
        assert f"\n## {number}. " in text
    assert "Asked “Same address?”, the person answered: yes." in text
    assert "pkit-probe-b <scratch>/clone-wt" in text
    assert "````text\n```\ninner\n```\n````" in text


def test_the_results_hold_only_the_measurements_the_parts_run_take(probe_module: Any) -> None:
    assert probe_module.measured_by("address") == [2, 9, 10, 11, 12]
    assert probe_module.measured_by("all") == list(range(1, 13))
    scrub = probe_module.Scrubber(Path("/nowhere"), Path("/home"), None, "someone", "host", None)
    report = probe_module.Report(scrub, ["heading"], probe_module.measured_by("address"))
    text = report.render()
    assert "\n## 9. A second session's address" in text
    assert "\n## 1. " not in text and "| 1. " not in text


# --- the parts, against a stub harness -------------------------------------------------------


def test_the_headless_part_runs_each_of_its_runs_to_the_results(
    probe_module: Any, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    probe = _probe(probe_module, tmp_path, _stub(tmp_path))
    try:
        probe_module.headless_part(probe)
    finally:
        probe.end_all()
    probe.save()
    text = probe.out.read_text()
    labels = sorted(path.name for path in (probe.root / "evidence").glob("m*.jsonl"))
    cases = len(probe_module.INBOUND_CASES)
    assert len(labels) == 2 + 2 * cases + 2
    for number in (1, 5, 6, 8):
        section = text.split(f"\n## {number}. ")[1].split("\n## ")[0]
        assert "- Not measured." not in section
    assert "SendMessage held" in text
    assert "the run holds SendMessage" in text
    # The stub delivers nothing, so the cases the documentation reads as held agree with it.
    assert (
        "3 of 5 cases measured read as the documentation says; "
        "these differ: both-bypass, flag-accept-bypass." in text
    )
    assert str(tmp_path) not in text
    capsys.readouterr()


def test_the_held_cases_summary_counts_only_the_cases_measured(
    probe_module: Any, tmp_path: Path
) -> None:
    probe = _probe(probe_module, tmp_path, _stub(tmp_path))
    probe_module.report_inbound(probe, {"one": True, "two": None, "three": False})
    probe_module.report_inbound(probe, {"one": None})
    text = probe.report.render()
    assert (
        "headless: 1 of 2 cases measured read as the documentation says; "
        "these differ: three; 1 not measured." in text
    )
    assert "headless: not measured, no receiver started." in text


def test_the_terminal_part_walks_each_step_to_the_results(
    probe_module: Any,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    probe = _probe(probe_module, tmp_path, _stub(tmp_path))
    monkeypatch.setattr("builtins.input", lambda _prompt="": "y")
    monkeypatch.setattr(probe_module, "pause", lambda _seconds: None)
    probe_module.terminal_part(probe)
    probe.save()
    shown = capsys.readouterr().out
    assert probe.steps == len(probe_module.TERMINAL_STEPS) + 1
    assert f"cd {probe.root / 'clone-wt'} && claude --name pkit-probe-b" in shown
    assert f"--scan-env {probe.root}" in shown
    text = probe.out.read_text()
    for number in (1, 2, 3, 4, 5, 7, 8):
        section = text.split(f"\n## {number}. ")[1].split("\n## ")[0]
        assert "- Not measured." not in section
    assert "the person read the reply address as the listing's: yes" in text


def _frame(socket: str, marker: str) -> str:
    return (
        f'<cross-session-message from="uds:{socket}" from-name="pkit-probe-a" '
        f'from-mode="prompting">\n{marker}: no answer is needed.\n</cross-session-message>'
    )


def _scan(pid: int, start: str, *, confined: bool = False) -> dict[str, Any]:
    return {
        "messaging_socket": f"/tmp/cc-socks/{pid}.sock",
        "claude_pid": pid,
        "socket_pid": pid,
        "process_start": start,
        "socket_held": "yes",
        "chain": [{"pid": 3, "command": "zsh"}, {"pid": pid, "command": "claude"}],
        "confined": confined,
    }


def _printed(key: str, value: Any, agent: str | None = None) -> dict[str, Any]:
    entry = {
        "hook_event_name": "PostToolUse",
        "tool_name": "Bash",
        "tool_response": {"stdout": json.dumps({key: value})},
    }
    return {**entry, "agent_id": agent} if agent else entry


def _at(folder: Path, *entries: dict[str, Any]) -> list[dict[str, Any]]:
    """Hook events as a session in a folder records them."""
    return [{**entry, "cwd": str(folder)} for entry in entries]


def _message(socket: str, marker: str) -> dict[str, Any]:
    """A marked message as the session that takes it records it."""
    return {"hook_event_name": "UserPromptSubmit", "prompt": _frame(socket, marker)}


def _check(pid: int, copy: str, start: str | None, *, confined: bool) -> dict[str, Any]:
    recorded = "Mon Nov 23 15:00:00 2026" if pid == 41 else "Mon Nov 23 15:05:00 2026"
    return {
        "copy": copy,
        "pid": pid,
        "recorded_start": recorded,
        "signal": "exists" if start else "no such process",
        "start": start,
        "start_unread": None,
        "confined": confined,
    }


def test_the_address_part_walks_each_step_to_the_results(
    probe_module: Any,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Each wait for the person writes what the sessions would have recorded by then, so the
    part reads evidence shaped as the harness gives it."""
    probe = _probe(probe_module, tmp_path, _stub(tmp_path))
    first, second = "Mon Nov 23 15:00:00 2026", "Mon Nov 23 15:05:00 2026"
    listing = {
        "hook_event_name": "PostToolUse",
        "tool_name": "ListAgents",
        "tool_response": {"listing": "This session is pkit-probe-a [5c2091] — the name\n"},
    }
    inside, outside = "probe-messaging.py", "probe-outside.py"
    clone, other, twin = probe.path("clone"), probe.path("other"), probe.path("twin")
    sends = [
        {
            "hook_event_name": "PreToolUse",
            "tool_name": "SendMessage",
            "agent_id": agent,
            "tool_input": {"to": "pkit-probe-b", "message": f"{marker}: no answer"},
        }
        for agent, marker in (("fg", "probe-m11-foreground"), ("bg", "probe-m11-background"))
    ]
    live_checks = [
        _printed("probe_check", _check(pid, copy, start, confined=copy == inside))
        for pid, start in ((41, first), (42, second))
        for copy in (inside, outside)
    ]
    ended_checks = [
        _printed("probe_check", _check(42, copy, None, confined=copy == inside))
        for copy in (inside, outside)
    ]
    by_wait = {
        "has done both": _at(clone, listing, _printed("probe_scan", _scan(41, first))),
        "has run it": _at(other, _printed("probe_scan", _scan(77, "Mon", confined=True))),
        "has done all three": _at(twin, listing, _printed("probe_scan", _scan(42, second)))
        + _at(other, _message("/tmp/cc-socks/42.sock", "probe-m9-second")),
        "shows the message": _at(other, _message("/tmp/cc-socks/41.sock", "probe-m9-first")),
        "both agents have finished": _at(
            clone,
            *sends,
            *(_printed("probe_scan", _scan(41, first), agent) for agent in ("fg", "bg")),
        )
        + _at(other, _message("/tmp/cc-socks/41.sock", "probe-m11-foreground")),
        "has run all 4": _at(other, *live_checks),
        "has run all 2": _at(other, *ended_checks),
    }
    log = probe.path("evidence", "hooks.jsonl")

    def wait(what: str) -> None:
        for key, entries in by_wait.items():
            if key in what:
                with open(log, "a", encoding="utf-8") as handle:
                    handle.writelines(json.dumps(entry) + "\n" for entry in entries)

    monkeypatch.setattr(probe, "wait", wait)
    probe.report.numbers = probe_module.measured_by("address")
    probe_module.address_part(probe)
    probe.save()
    shown = capsys.readouterr().out
    assert probe.steps == len(probe_module.ADDRESS_STEPS)
    assert f"cd {probe.root / 'other'} && claude --name pkit-probe-b" in shown
    outside_call = f"(2, outside the sandbox) python3 {probe.root / 'probe-outside.py'}"
    assert f"{outside_call} --check-process {probe.root} 41" in shown
    assert "dangerouslyDisableSandbox set to true" in shown
    text = probe.out.read_text()
    assert "the session reads its name through the listing's first line" in text
    assert "| 9. A second session's address | holds: the two sessions sent" in text
    assert "the first pkit-probe-a: holds: the address and CLAUDE_PID name process 41" in text
    assert "a foreground subagent: its message carried the session's own messaging address" in (
        text
    )
    assert "a background subagent: no message from it arrived" in text
    assert (
        "the first pkit-probe-a's process, running, from a command in the sandbox: tells it runs"
        in text
    )
    assert (
        "the second pkit-probe-a's process, ended, from a command outside the sandbox: tells it "
        "ended: ps shows no process under its id" in text
    )
    assert str(tmp_path) not in text
