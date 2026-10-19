#!/usr/bin/env python3
"""The Claude Code adapter's agent runner (ADR-066 points 1, 2, 4 and 10).

The backbone's run command, `pkit agents run`, starts this script as the
command the adapter registers under `run-agent`. It never runs on its own
behalf: a command that starts an agent asks the backbone, and the backbone
starts this runner, which starts Claude Code. The tie to `claude` lives here,
and nowhere in a capability.

**The request**, one JSON document on standard input: `schema_version` (1),
`agent`, `brief`, `folder`, `limit_seconds`, `effort` (a level or null). That
is the unconfined form, the one the review command's runs take (ADR-066
point 10). A request that carries any other key is refused, never run without
it: the confined form arrives with a runner that reads it.

**What it does,** in Claude Code's terms:

- It refuses the run when `claude` is not on the path, or when the agent is
  not deployed: no `.claude/agents/<agent>.md` in the folder or a folder above
  it, nor in the person's own agents folder.
- It starts `claude -p --agent <agent>`, with `--effort <level>` where one is
  set, in the request's folder, and writes the brief to its standard input.
  The run takes the person's and the project's settings there, and starts in
  the mode they or the harness choose, as a session started in that folder
  would.
- Those three flags are the closed set (ADR-066 point 4). No other flag is
  ever passed, and none of them approves a call or loads other configuration.
  `command` builds the command line, and `check_flags` refuses one with a
  flag outside the set. The brief goes on standard input, so no word of it is
  read as a flag or a subcommand.
- The harness starts in a session of its own. At the limit the runner ends
  that session's whole process group: the harness and every process it
  started there. Asked to stop itself (`SIGTERM`, `SIGHUP`, `SIGINT`), it ends
  that group first, then exits with no answer.
- The harness gets the runner's environment, less the variables of the
  backbone's run of this runner (`RUN_VARIABLES`). So a `pkit` an agent runs
  starts as a run of its own, as in a session a person started.

**The answer**, one JSON document on standard output, exit 0: `schema_version`
(1), `ending` (`finished`, `not-started`, `timed-out` or `refused`),
`exit_code` (the harness's when it finished, else null), `output` (the
harness's standard output), `diagnostics` (its standard error), `reason`.

Runs under the system `python3`, standard library only, as the permission hook
does: no `uv`, nothing to provision.
"""

from __future__ import annotations

import contextlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
from pathlib import Path
from typing import Any

REQUEST_VERSION = 1
ANSWER_VERSION = 1

#: The harness's command line.
HARNESS = "claude"

#: The keys of a request this runner runs. Any other key is refused.
REQUEST_KEYS = frozenset({"schema_version", "agent", "brief", "folder", "limit_seconds", "effort"})

#: The closed set of flags this runner passes the harness (ADR-066 point 4),
#: each with whether it takes a value. No member approves a call or loads
#: configuration other than the run's own.
FLAGS = {"-p": False, "--agent": True, "--effort": True}

#: The harness's effort levels, the methodology's vocabulary.
EFFORT_LEVELS = ("low", "medium", "high", "xhigh", "max")

#: The longest limit a run takes, as the backbone bounds it: a week.
MAX_LIMIT_SECONDS = 7 * 24 * 60 * 60

#: An agent's name, as the backbone admits it: no flag, no path.
AGENT_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")

#: The backbone's own variables for its run of this runner. The harness's run
#: is not part of that run, so they are not passed on.
RUN_VARIABLES = ("PKIT_COMMAND_DEADLINE", "PKIT_COMMAND_STRAYS", "PKIT_RUN_CACHE")

FINISHED = "finished"
NOT_STARTED = "not-started"
TIMED_OUT = "timed-out"
REFUSED = "refused"

# The harness, once started: what a signal to stop ends first.
_harness: list[subprocess.Popen[bytes]] = []


class Refused(Exception):
    """The run is refused before it starts; the message is the reason."""


def answer(
    ending: str,
    *,
    exit_code: int | None = None,
    output: str = "",
    diagnostics: str = "",
    reason: str = "",
) -> dict[str, Any]:
    return {
        "schema_version": ANSWER_VERSION,
        "ending": ending,
        "exit_code": exit_code,
        "output": output,
        "diagnostics": diagnostics,
        "reason": reason,
    }


def read_request(text: str) -> dict[str, Any]:
    """The request, checked. Raises `Refused` naming what is wrong."""
    try:
        request = json.loads(text)
    except ValueError as exc:
        raise Refused(f"the request is not a JSON document: {exc}") from None
    if not isinstance(request, dict):
        raise Refused("the request is not a JSON object")
    unknown = sorted(set(request) - REQUEST_KEYS)
    if unknown:
        raise Refused(
            "the request carries keys this runner does not run: "
            + ", ".join(unknown)
            + ". It runs only the unconfined form"
        )
    version = request.get("schema_version")
    if version != REQUEST_VERSION or isinstance(version, bool):
        raise Refused(f"the request's schema_version is {version!r}; this runner reads 1")
    agent = request.get("agent")
    if not isinstance(agent, str) or not AGENT_NAME.fullmatch(agent):
        raise Refused(f"the agent {agent!r} is not a name")
    brief = request.get("brief")
    if not isinstance(brief, str) or not brief.strip() or "\0" in brief:
        raise Refused("the brief is empty, or not text")
    folder = request.get("folder")
    if not isinstance(folder, str) or not Path(folder).is_absolute() or not Path(folder).is_dir():
        raise Refused(f"the folder {folder!r} is not a directory")
    limit = request.get("limit_seconds")
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= MAX_LIMIT_SECONDS:
        raise Refused(f"the limit {limit!r} is not from 1 to {MAX_LIMIT_SECONDS} seconds")
    effort = request.get("effort")
    if effort is not None and effort not in EFFORT_LEVELS:
        raise Refused(f"the effort {effort!r} is not one of {', '.join(EFFORT_LEVELS)}")
    return request


def agent_file(agent: str, folder: Path, env: dict[str, str]) -> Path | None:
    """Where Claude Code finds the agent's definition: `.claude/agents/<agent>.md`
    in the folder or a folder above it, else in the person's own agents folder
    (`$CLAUDE_CONFIG_DIR/agents`, else `~/.claude/agents`). None when neither has
    it."""
    name = f"{agent}.md"
    for place in (folder, *folder.parents):
        candidate = place / ".claude" / "agents" / name
        if candidate.is_file():
            return candidate
    config = env.get("CLAUDE_CONFIG_DIR") or str(Path.home() / ".claude")
    candidate = Path(config) / "agents" / name
    return candidate if candidate.is_file() else None


def command(harness: str, agent: str, effort: str | None) -> list[str]:
    """The harness's command line: the closed set's flags, and nothing else."""
    argv = [harness, "-p", "--agent", agent]
    if effort is not None:
        argv += ["--effort", effort]
    check_flags(argv)
    return argv


def check_flags(argv: list[str]) -> None:
    """Raise `Refused` when the command line passes a flag outside the closed
    set, or a flag's value that reads as a flag."""
    index = 1
    while index < len(argv):
        token = argv[index]
        if token not in FLAGS:
            raise Refused(f"the command line passes {token!r}, which is not in the closed set")
        if FLAGS[token]:
            index += 1
            if index >= len(argv) or argv[index].startswith("-"):
                raise Refused(f"the command line passes {token!r} with no value")
        index += 1


def harness_environment(env: dict[str, str]) -> dict[str, str]:
    """The runner's environment, less the backbone's variables for its run."""
    return {key: value for key, value in env.items() if key not in RUN_VARIABLES}


def end_harness(process: subprocess.Popen[bytes]) -> None:
    """End the harness's session: its process group, the harness and every
    process it started there."""
    with contextlib.suppress(ProcessLookupError, PermissionError):
        os.killpg(process.pid, signal.SIGKILL)


def run(request: dict[str, Any], env: dict[str, str]) -> dict[str, Any]:
    """Run the request, and answer how it ended."""
    harness = shutil.which(HARNESS, path=env.get("PATH"))
    if harness is None:
        raise Refused(f"the `{HARNESS}` command line is not on PATH")
    folder = Path(request["folder"])
    agent = request["agent"]
    if agent_file(agent, folder, env) is None:
        raise Refused(
            f"the agent {agent} is not deployed: no .claude/agents/{agent}.md in {folder} "
            "or a folder above it, nor in the person's own agents folder"
        )
    argv = command(harness, agent, request.get("effort"))
    try:
        process = subprocess.Popen(
            argv,
            cwd=str(folder),
            env=harness_environment(env),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
    except OSError as exc:
        return answer(NOT_STARTED, reason=f"`{HARNESS}` could not be started: {exc}")
    _harness.append(process)
    limit = request["limit_seconds"]
    try:
        raw_out, raw_err = process.communicate(
            request["brief"].encode("utf-8", errors="replace"), timeout=limit
        )
    except subprocess.TimeoutExpired:
        end_harness(process)
        process.wait()
        for stream in (process.stdout, process.stderr):
            if stream is not None:
                stream.close()
        return answer(
            TIMED_OUT,
            reason=(
                f"the agent did not finish within {limit} s, so the harness was ended "
                "with every process it started"
            ),
        )
    return answer(
        FINISHED,
        exit_code=process.returncode,
        output=raw_out.decode("utf-8", errors="replace"),
        diagnostics=raw_err.decode("utf-8", errors="replace"),
    )


def stop(signum: int, _frame: object) -> None:
    """Asked to stop: end the harness's session first, then exit with no answer."""
    for process in _harness:
        end_harness(process)
    os._exit(128 + signum)


def main() -> int:
    for signum in (signal.SIGTERM, signal.SIGHUP, signal.SIGINT):
        signal.signal(signum, stop)
    env = dict(os.environ)
    try:
        request = read_request(sys.stdin.buffer.read().decode("utf-8", errors="replace"))
        result = run(request, env)
    except Refused as refused:
        result = answer(REFUSED, reason=str(refused))
    sys.stdout.write(json.dumps(result) + "\n")
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
