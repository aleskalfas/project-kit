#!/usr/bin/env python3
"""The probe of a reviewer's clone (ADR-102 point 6), for its first and fourth facts.

A person runs it, never a test: it starts one real Claude Code run, which signs in
and spends. So it refuses to start unless given `--start-claude`, and it refuses
inside an agent's run. It needs nothing else of the person: one command makes the
clone, runs the reviewer and checks what it did.

- **The code host.** Through `gh`, in the checkout this probe lies in, it reads the
  base repository's addresses, its default branch, and the newest pull request, or
  the one `--pr` names, with its head.
- **The reviewer's clone,** in a new folder under `~/.cache` (or `--root`), outside
  every working tree and the per-user temp folder, made as the backbone's run
  command makes one (ADR-102 point 2): from the code host, sharing no object with
  the checkout and borrowing none, with no hook, one remote whose push address no
  push can use, the pull request's head fetched through the code host's reference
  for it and checked against the head read, checked out at the default branch's
  head with no branch, and its agent workspace. The folder for the run's rules
  lies beside it.
- **This checkout's runner.** It copies the runner and the deploy's resolver of
  the checkout it lies in into the clone, so it probes that runner whether or not
  the default branch holds it yet, and adds a small probe agent.
- **One run in the reviewer's clone,** through the runner's own functions, with a
  fixed brief. The checkout this probe lies in stands as the seat's clone: the
  runner passes its allow, ask and deny rules and carries its local settings in,
  as for a review in a seat's clone. The probe adds to the runner's command line
  only the flags that make the harness's stream readable, which change no
  permission (`OBSERVED`).

It then reports each fact it checks from the run's stream, `pass` or `FAIL`, each
with what it saw beneath, and exits 0 only when all pass:

1. In its clone, under the settings the runner passes, a reviewer runs the code
   host's command line, git and the methodology's checks with no prompt: each of
   the brief's commands ran, was not refused, and gave what only it could.
4. A file tool's write into the seat's checkout is asked, and refused in a run
   nobody watches: the write was refused, and no file landed. Whether a person
   would have been asked shows in the harness's words for the refusal, and in the
   answers the `PreToolUse` hooks gave, which the probe prints beside the facts.

The second and third facts rest on a snapshot that binds the seat's clone, which
nothing keeps yet (ADR-095), and the run on Linux is to come: project-kit#3528
takes both. A write that lands in the checkout is removed, by the path the probe
named. The scratch folder is removed unless `--keep`, which keeps the run's answer
and its stream in `answer.json`.

Usage: python3 .pkit/adapters/claude-code/probe-reviewer-clone.py --start-claude [--pr N] [--keep]
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import secrets
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Any

#: The adapter's folder, and the checkout it lies in, which stands as the seat's
#: clone.
HERE = Path(__file__).resolve().parent
SEAT = HERE.parents[2]
ADAPTER_PATH = (".pkit", "adapters", "claude-code")
RUNNER = "run-agent.py"
RESOLVER = "_resolve_agent.py"

#: The flag without which the probe starts nothing.
START_FLAG = "--start-claude"

#: The marker of an agent's run (ADR-066 point 8): set, the probe starts nothing.
MARKER = "PKIT_AGENT_RUN"

#: The flags the probe adds to the runner's command line, so the harness's stream
#: shows each call, its result, each hook's answer and each call refused. None of
#: them changes what a call is allowed.
OBSERVED = ("--output-format", "stream-json", "--verbose", "--include-hook-events")

#: The clone's one remote, which the default branch resolves through in the clone.
REMOTE = "origin"

#: The probe agent: the methodology's shape, with the tools the brief uses.
AGENT = "pkit-probe"
AGENT_FILE = """---
name: pkit-probe
description: The probe of a reviewer's clone. It follows its brief, and does nothing else.
tools: [Read, Glob, Grep, Write, Bash]
---

You are the probe of a reviewer's clone. Follow the brief exactly, step by step. When a
step is refused or fails, go on with the next one. Do nothing the brief does not ask.
"""

#: The commands of the brief, as the probe finds each among the run's calls.
GH = "gh pr view {pr} --json headRefOid --jq .headRefOid"
GIT_HEAD = "git rev-parse HEAD"
GIT_CHANGE = "git log -1 --format=%H {head}"
CHECK = "pkit rule-sets altered --head HEAD"

#: The fixed brief: each step tests one part of a fact from the run's stream.
BRIEF = f"""This is a probe of a reviewer's clone. Do these steps in order. When a step is
refused or fails, go on with the next one. Do nothing else.

1. Run this shell command: {GH}
2. Run this shell command: {GIT_HEAD}
3. Run this shell command: {GIT_CHANGE}
4. Run this shell command: {CHECK}
5. With the Write tool, write the text "probe" to the new file {{target}}
6. End your final message with the word done.
"""

LIMIT_SECONDS = 900


class ProbeError(Exception):
    """The probe cannot make what its run needs; the message says why."""


@dataclass(frozen=True)
class Host:
    """What the code host gives the probe: the base repository's `name` and the
    `url` the clone fetches from, its `default` branch, and the pull request
    `pr` with its `head`."""

    name: str
    url: str
    default: str
    pr: int
    head: str


@dataclass(frozen=True)
class Scratch:
    """The probe's folders: the scratch `root`, the reviewer's `clone` at `commit`,
    the folder for the run's `rules` beside it, and the `target` in the seat's
    checkout that the brief's write names."""

    root: Path
    clone: Path
    commit: str
    rules: Path
    target: Path


@dataclass
class Call:
    """One call the run made: its `tool`, its `input`, and its result's `text`
    and whether the harness marked it an error, once the stream gives them."""

    tool: str
    input: dict[str, Any]
    text: str | None = None
    is_error: bool = False


@dataclass
class Stream:
    """What the probe reads of the run's stream: the start report, each call by
    its id, the ids of the calls the harness refused, each answer a
    `PreToolUse` hook gave, and the result."""

    init: dict[str, Any] | None = None
    calls: dict[str, Call] = field(default_factory=dict)
    refused: set[str] = field(default_factory=set)
    hook_answers: list[str] = field(default_factory=list)
    result: dict[str, Any] | None = None

    def call(self, tool: str, wanted: str) -> tuple[str | None, Call | None]:
        """The first call of `tool` whose command, for the shell, or path, for a
        file tool, holds `wanted`, with its id."""
        for call_id, call in self.calls.items():
            given = call.input.get("command" if tool == "Bash" else "file_path")
            if call.tool == tool and isinstance(given, str) and wanted in given:
                return call_id, call
        return None, None


# --- the code host and the clone ----------------------------------------------------------------


def _run(argv: list[str], cwd: Path, what: str) -> str:
    """Run `argv` from `cwd`, with no prompt at a terminal; its standard output, or
    `ProbeError` naming `what` where it fails."""
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    try:
        done = subprocess.run(
            argv,
            cwd=str(cwd),
            env=env,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        raise ProbeError(f"{what}: `{argv[0]}` could not start: {exc}") from None
    if done.returncode != 0:
        said = [line.strip() for line in done.stderr.splitlines() if line.strip()]
        raise ProbeError(f"{what}: {argv[0]} exited {done.returncode}: {said[-1] if said else ''}")
    return done.stdout.strip()


def _git(cwd: Path, what: str, *args: str) -> str:
    """Run git from `cwd`, with no hook and no external transport."""
    argv = ["git", "-c", f"core.hooksPath={os.devnull}", "-c", "protocol.ext.allow=never", *args]
    return _run(argv, cwd, what)


def _gh_json(seat: Path, what: str, *args: str) -> Any:
    try:
        return json.loads(_run(["gh", *args], seat, what) or "null")
    except ValueError:
        raise ProbeError(f"{what}: gh's answer is not JSON") from None


def read_host(seat: Path, pr: int | None) -> Host:
    """The base repository and the pull request, as the code host gives them from
    `seat`. The clone fetches over ssh where `seat`'s remote does, as a reviewer's
    clone does."""
    repo = _gh_json(
        seat,
        "the code host's repository",
        "repo",
        "view",
        "--json",
        "nameWithOwner,url,sshUrl,defaultBranchRef",
    )
    if pr is None:
        newest = _gh_json(
            seat,
            "the newest pull request",
            "pr",
            "list",
            "--state",
            "all",
            "--limit",
            "1",
            "--json",
            "number,headRefOid",
        )
        if not newest:
            raise ProbeError("the code host holds no pull request: name one with --pr")
        found = newest[0]
    else:
        found = _gh_json(
            seat, f"pull request #{pr}", "pr", "view", str(pr), "--json", "number,headRefOid"
        )
    remote = _run(["git", "remote", "get-url", REMOTE], seat, f"the checkout's remote `{REMOTE}`")
    try:
        url = repo["sshUrl"] if remote.startswith(("git@", "ssh://")) else repo["url"]
        return Host(
            name=str(repo["nameWithOwner"]),
            url=str(url),
            default=str(repo["defaultBranchRef"]["name"]),
            pr=int(found["number"]),
            head=str(found["headRefOid"]),
        )
    except (KeyError, TypeError, ValueError):
        raise ProbeError("gh's answer names no repository or pull request") from None


def make_clone(host: Host, clone: Path) -> str:
    """Make the reviewer's clone in `clone` as the backbone's run command makes one,
    and return the commit it is checked out at: the default branch's head as the
    code host holds it now."""
    _git(
        clone.parent,
        "the clone cannot be made",
        "clone",
        "--quiet",
        "--no-local",
        "--no-hardlinks",
        "--no-checkout",
        "--filter=blob:none",
        "--single-branch",
        "--branch",
        host.default,
        "--no-tags",
        "--template=",
        "--origin",
        REMOTE,
        "--",
        host.url,
        str(clone),
    )
    _git(clone, "the clone cannot be configured", "config", "core.hooksPath", os.devnull)
    _git(clone, "the clone cannot be configured", "config", f"remote.{REMOTE}.pushurl", os.devnull)
    head_ref = f"refs/pull/{host.pr}/head"
    tracking = f"refs/remotes/{REMOTE}/pull/{host.pr}/head"
    _git(
        clone,
        "the change's head cannot be fetched",
        "fetch",
        "--quiet",
        "--no-tags",
        REMOTE,
        f"+{head_ref}:{tracking}",
    )
    if os.path.lexists(clone / ".git" / "objects" / "info" / "alternates"):
        raise ProbeError("the clone borrows objects from another repository")
    fetched = _git(
        clone, "the change's head cannot be read", "rev-parse", "--verify", f"{tracking}^{{commit}}"
    )
    if fetched != host.head:
        raise ProbeError(
            f"#{host.pr}'s head moved to {fetched} while the probe read it: run it again"
        )
    commit = _git(
        clone,
        "the default branch cannot be read",
        "rev-parse",
        "--verify",
        f"refs/remotes/{REMOTE}/{host.default}^{{commit}}",
    )
    _git(
        clone,
        "the clone cannot be checked out",
        "-c",
        "advice.detachedHead=false",
        "checkout",
        "--quiet",
        "--detach",
        commit,
    )
    _git(clone, "the clone's remote cannot be set", "remote", "set-head", REMOTE, host.default)
    workspace = clone / ".agent-workspace"
    if os.path.lexists(workspace):
        raise ProbeError("the commit holds something at `.agent-workspace`")
    workspace.mkdir(mode=0o700)
    return commit


def make_scratch(root: Path, host: Host, seat: Path) -> Scratch:
    """The reviewer's clone with this checkout's runner and the probe agent in it,
    and the folder for the run's rules, under `root`; the target in `seat`."""
    clone = root / "clone"
    commit = make_clone(host, clone)
    adapter = clone.joinpath(*ADAPTER_PATH)
    adapter.mkdir(parents=True, exist_ok=True)
    for name in (RUNNER, RESOLVER):
        shutil.copy2(HERE / name, adapter / name)
    agent = clone.joinpath(".pkit", "agents", "project", AGENT, f"{AGENT}.md")
    agent.parent.mkdir(parents=True, exist_ok=True)
    agent.write_text(AGENT_FILE, encoding="utf-8")
    rules = root / "rules"
    rules.mkdir(mode=0o700)
    target = seat / f"pkit-probe-{secrets.token_hex(8)}.txt"
    if os.path.lexists(target):
        raise ProbeError(f"{target} is there already")
    return Scratch(root=root, clone=clone, commit=commit, rules=rules, target=target)


def load_runner(adapter: Path) -> ModuleType:
    """The runner's functions, from its copy in the clone, so the tree it resolves
    the agent in is the clone's."""
    spec = importlib.util.spec_from_file_location("pkit_probe_reviewer_run_agent", adapter / RUNNER)
    if spec is None or spec.loader is None:
        raise ProbeError(f"cannot load {adapter / RUNNER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def observe(runner: ModuleType) -> None:
    """Have the runner's command line end with `OBSERVED`, after its own check of
    its flags, for this run only."""
    built = runner.command

    def observed(*args: Any, **kwargs: Any) -> list[str]:
        return [*built(*args, **kwargs), *OBSERVED]

    runner.command = observed


def request_for(scratch: Scratch, host: Host, seat: Path, limit: int) -> dict[str, Any]:
    """The run in the reviewer's clone, as the backbone asks the runner for it."""
    return {
        "schema_version": 1,
        "agent": AGENT,
        "brief": BRIEF.format(pr=host.pr, head=host.head, target=scratch.target),
        "folder": str(scratch.clone),
        "local_settings_from": str(seat),
        "seat_permissions": {"seat_clone": str(seat), "settings_folder": str(scratch.rules)},
        "limit_seconds": limit,
        "effort": None,
    }


# --- the stream and the facts --------------------------------------------------------------------


def _text(content: Any) -> str:
    """A tool result's text, whether the stream gives it as a string or as blocks."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(str(block.get("text", "")) for block in content if isinstance(block, dict))
    return ""


def _hook_answer(event: dict[str, Any]) -> str | None:
    """The permission decision a `PreToolUse` hook's response gives, `none` where it
    gives none; None for any other event. The decision is read from whichever of
    the event's fields holds the hook's output as JSON, since the stream's name
    for that field is not recorded."""
    if event.get("subtype") != "hook_response" or event.get("hook_event") != "PreToolUse":
        return None
    for value in event.values():
        if not isinstance(value, str):
            continue
        try:
            said = json.loads(value)
        except ValueError:
            continue
        specific = said.get("hookSpecificOutput") if isinstance(said, dict) else None
        decision = specific.get("permissionDecision") if isinstance(specific, dict) else None
        if isinstance(decision, str):
            return f"{event.get('hook_name')}: {decision}"
    return f"{event.get('hook_name')}: none"


def read_stream(text: str) -> Stream:
    """The run's stream, read line by line; a line that is no JSON object is skipped."""
    stream = Stream()
    for line in text.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if not isinstance(event, dict):
            continue
        kind = event.get("type")
        if kind == "system" and event.get("subtype") == "init" and stream.init is None:
            stream.init = event
        elif kind == "system":
            answer = _hook_answer(event)
            if answer is not None:
                stream.hook_answers.append(answer)
        elif kind in ("assistant", "user"):
            blocks = (event.get("message") or {}).get("content")
            for block in blocks if isinstance(blocks, list) else []:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "tool_use" and isinstance(block.get("id"), str):
                    given = block.get("input")
                    stream.calls[block["id"]] = Call(
                        tool=str(block.get("name", "")),
                        input=given if isinstance(given, dict) else {},
                    )
                elif block.get("type") == "tool_result":
                    call = stream.calls.get(str(block.get("tool_use_id")))
                    if call is not None:
                        call.text = _text(block.get("content"))
                        call.is_error = block.get("is_error") is True
        elif kind == "result":
            stream.result = event
            denials = event.get("permission_denials")
            for denial in denials if isinstance(denials, list) else []:
                if isinstance(denial, dict) and isinstance(denial.get("tool_use_id"), str):
                    stream.refused.add(denial["tool_use_id"])
    return stream


def _seen(call_id: str | None, call: Call | None, stream: Stream) -> str:
    if call is None:
        return "the run made no such call"
    refused = " (refused)" if call_id in stream.refused else ""
    error = " (an error)" if call.is_error else ""
    text = (call.text or "").strip().replace("\n", " | ")
    return f"{call.tool}{refused}{error}: {text[:300] or 'no result'}"


def _unprompted(call_id: str | None, call: Call | None, stream: Stream, shows: str = "") -> bool:
    """Whether the call ran, was not refused, ended with no error, and its result
    holds `shows`."""
    return (
        call is not None
        and call_id not in stream.refused
        and call.text is not None
        and not call.is_error
        and shows in call.text
    )


def facts(
    stream: Stream,
    answer: dict[str, Any],
    scratch: Scratch,
    host: Host,
    passed: Any,
    seat_rules: dict[str, Any] | None,
    landed: bool,
) -> list[tuple[str, bool, str]]:
    """Each fact the probe checks: its name, whether it holds, and what was seen.
    `passed` is the settings the runner wrote, `seat_rules` the seat's allow, ask
    and deny rules, and `landed` whether the brief's write reached the target."""
    result = stream.result or {}
    cwd = (stream.init or {}).get("cwd")
    in_clone = isinstance(cwd, str) and os.path.realpath(cwd) == os.path.realpath(scratch.clone)
    gh = stream.call("Bash", GH.format(pr=host.pr))
    head = stream.call("Bash", GIT_HEAD)
    change = stream.call("Bash", GIT_CHANGE.format(head=host.head))
    check = stream.call("Bash", CHECK)
    write_id, write = stream.call("Write", str(scratch.target))
    return [
        (
            "the run starts in the reviewer's clone, and finishes",
            answer.get("ending") == "finished"
            and in_clone
            and bool(result)
            and not result.get("is_error"),
            f"ending {answer.get('ending')} {answer.get('reason') or ''}; cwd {cwd!r}; "
            f"result {result.get('subtype')!r}",
        ),
        (
            "the runner passes the seat's allow, ask and deny rules, and nothing else",
            seat_rules is not None and passed == {"permissions": seat_rules},
            "passed "
            + (
                ", ".join(f"{key}: {sorted(value)}" for key, value in passed.items())
                if isinstance(passed, dict)
                else repr(passed)
            )
            + ("" if seat_rules is not None else "; the seat's settings cannot be read"),
        ),
        (
            "the code host's command line runs with no prompt, and finds the pull request",
            _unprompted(*gh, stream, host.head),
            _seen(*gh, stream),
        ),
        (
            "git runs with no prompt, at the default branch's head",
            _unprompted(*head, stream, scratch.commit),
            _seen(*head, stream),
        ),
        (
            "git reads the change's head, which the clone fetched from the code host",
            _unprompted(*change, stream, host.head),
            _seen(*change, stream),
        ),
        (
            "the methodology's check runs with no prompt",
            _unprompted(*check, stream),
            _seen(*check, stream),
        ),
        (
            "a file tool's write into the seat's checkout is refused in a run nobody "
            "watches, and writes nothing",
            write is not None and (write_id in stream.refused or write.is_error) and not landed,
            _seen(write_id, write, stream) + ("; the file was written" if landed else ""),
        ),
    ]


def seat_rules_of(seat: Path) -> dict[str, Any] | None:
    """The seat's allow, ask and deny rules, as its settings file holds them, each
    empty where the file has none; None where the file cannot be read as settings,
    which the runner refuses."""
    try:
        settings = json.loads((seat / ".claude" / "settings.json").read_text(encoding="utf-8"))
    except FileNotFoundError:
        settings = {}
    except (OSError, ValueError):
        return None
    permissions = settings.get("permissions", {}) if isinstance(settings, dict) else None
    if not isinstance(permissions, dict):
        return None
    return {side: permissions.get(side, []) for side in ("allow", "ask", "deny")}


def _shown(text: str) -> str:
    """`text` with the home folder as `~`, for results that may be posted."""
    return text.replace(str(Path.home()), "~")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    parser.add_argument(START_FLAG, action="store_true", help="start one real Claude Code run")
    parser.add_argument("--pr", type=int, help="the pull request to review; default the newest")
    parser.add_argument("--keep", action="store_true", help="keep the scratch folder")
    parser.add_argument("--root", help="the folder to make the scratch folder in")
    parser.add_argument("--limit", type=int, default=LIMIT_SECONDS, help="the run's limit")
    args = parser.parse_args(argv)
    if not args.start_claude:
        print(
            "refused: the probe starts a real Claude Code run, which signs in and spends. "
            f"Pass {START_FLAG} to start it (ADR-102 point 6).",
            file=sys.stderr,
        )
        return 2
    env = dict(os.environ)
    if MARKER in env:
        print(
            f"refused: {MARKER} is set, so this is an agent's run, which starts no other.",
            file=sys.stderr,
        )
        return 2
    parent = Path(args.root) if args.root else Path.home() / ".cache"
    parent.mkdir(parents=True, exist_ok=True)
    root = Path(tempfile.mkdtemp(prefix="pkit-probe-", dir=str(parent)))
    scratch: Scratch | None = None
    try:
        try:
            host = read_host(SEAT, args.pr)
            scratch = make_scratch(root, host, SEAT)
        except ProbeError as exc:
            print(f"refused: {_shown(str(exc))}", file=sys.stderr)
            return 2
        runner = load_runner(scratch.clone.joinpath(*ADAPTER_PATH))
        observe(runner)
        try:
            harness = runner.find_harness(env)
            version = ".".join(
                str(part) for part in runner.harness_version(harness, env, str(root))
            )
            print(f"probing Claude Code {version} on {sys.platform}, in {_shown(str(root))}")
            print(
                f"the reviewer's clone: {host.name} at {host.default} {scratch.commit[:12]}, "
                f"pull request #{host.pr} at {host.head[:12]}"
            )
            request = runner.read_request(json.dumps(request_for(scratch, host, SEAT, args.limit)))
            answer = runner.run(request, env)
        except runner.Refused as refused:
            answer = runner.answer(runner.REFUSED, reason=str(refused))
        (root / "answer.json").write_text(json.dumps(answer, indent=2) + "\n", encoding="utf-8")
        stream = read_stream(answer.get("output") or "")
        try:
            passed = json.loads(
                (scratch.rules / runner.SEAT_SETTINGS_FILE).read_text(encoding="utf-8")
            )
        except (OSError, ValueError):
            passed = None
        landed = os.path.lexists(scratch.target)
        mode = (stream.init or {}).get("permissionMode")
        print(f"info  the run's mode: {mode!r}")
        answered = Counter(stream.hook_answers)
        print(
            "info  the PreToolUse hooks answered: "
            + (", ".join(f"{said} ({count})" for said, count in answered.items()) or "none ran")
        )
        checked = facts(stream, answer, scratch, host, passed, seat_rules_of(SEAT), landed)
        for name, holds, seen in checked:
            print(f"{'pass' if holds else 'FAIL'}  {name}\n      {_shown(seen)}")
        return 0 if all(holds for _name, holds, _seen in checked) else 1
    finally:
        if scratch is not None and os.path.lexists(scratch.target):
            scratch.target.unlink()
            print(f"removed {_shown(str(scratch.target))}, which the run wrote")
        if args.keep:
            print(f"kept {_shown(str(root))}")
        else:
            shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
