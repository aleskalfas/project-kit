"""How project-management starts an agent with nobody watching (ADR-066 point 1).

A capability never calls a harness, and never looks for an adapter. It asks the
backbone's run command, `pkit agents run`, which starts the runner the
project's adapter registers, and the runner starts the harness. This module is
the one place project-management asks: `review-pr` starts its reviewers
through it, and the drift command will start its fixers through it.

The command reads the brief on standard input and writes one JSON document, a
version this module reads (`VERSION`): how the run ended, the harness's exit,
the agent's output, the harness's diagnostics and a reason. pm decides on the
document's `ending`, never on the exit code.

**The run is bounded twice.** The backbone ends the harness at the run's limit,
and its runner at the limit plus the time the runner keeps to answer. pm waits
for the backbone's document that long, plus `MARGIN_SECONDS`. `pkit` runs in
the caller's process group, so an interrupt at the terminal reaches it, and it
stops its runner as it ends. Past pm's bound, or on an exception, `pkit` alone
is asked to stop, and killed `GRACE_SECONDS` later. Asked, it stops the runner,
which ends the harness and every process it started.

When the backbone cannot answer (no `pkit`, a backbone that predates the
command, a run past pm's bound, an answer pm cannot read), the run is one with
no answer, and the reason names the cause.
"""

from __future__ import annotations

import contextlib
import json
import shutil
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

#: The backbone's run command, and the version of its document pm reads.
ARGV = ("pkit", "agents", "run")
VERSION = 1

#: The longest limit the backbone's run command takes: a week. A longer one is
#: its usage error, so pm refuses it before any run starts.
MAX_LIMIT_SECONDS = 7 * 24 * 60 * 60

#: Past the run's limit, how long pm waits for the backbone's document: the
#: time the backbone gives its runner to end the harness and answer (30 s),
#: and the time to start `pkit`.
MARGIN_SECONDS = 60

#: Once asked to stop, how long `pkit` has to stop its runner before it is
#: killed: the runner's own grace (2 s), and room to spare.
GRACE_SECONDS = 10.0

# How a run ended, as the backbone's document names it.
FINISHED = "finished"
NOT_STARTED = "not-started"
TIMED_OUT = "timed-out"
REFUSED = "refused"
NO_ANSWER = "no-answer"
ENDINGS = (FINISHED, NOT_STARTED, TIMED_OUT, REFUSED, NO_ANSWER)


@dataclass(frozen=True)
class AgentRun:
    """How one run ended: the ending, the harness's exit when it finished, the
    agent's output, the harness's diagnostics, and the reason for any other
    ending."""

    ending: str
    exit_code: int | None = None
    output: str = ""
    diagnostics: str = ""
    reason: str = ""


def run_agent(
    name: str,
    brief: str,
    *,
    folder: Path,
    limit_seconds: int,
    effort: str | None = None,
) -> AgentRun:
    """Run agent `name` once on `brief`, in `folder`, within `limit_seconds`, at
    `effort` where one is set. Never raises for what the run did: every ending
    is in the answer. An interrupt stops the run, then propagates."""
    argv = [*ARGV, name, "--folder", str(folder), "--limit", str(limit_seconds)]
    if effort is not None:
        argv += ["--effort", effort]
    argv.append("--json")
    command = f"`{' '.join(ARGV)}`"
    try:
        process = subprocess.Popen(
            argv,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except FileNotFoundError as exc:
        return AgentRun(NOT_STARTED, reason=f"{command}: `pkit` is not on PATH ({exc})")
    except OSError as exc:
        return AgentRun(NOT_STARTED, reason=f"{command} could not be run ({exc})")
    bound = limit_seconds + MARGIN_SECONDS
    try:
        raw_out, raw_err = process.communicate(brief.encode("utf-8"), timeout=bound)
    except subprocess.TimeoutExpired:
        _stop(process)
        return AgentRun(
            NO_ANSWER, reason=f"{command} gave no answer within {bound} s, and was stopped"
        )
    except BaseException:
        _stop(process)
        raise
    return _read(
        command,
        process.returncode,
        raw_out.decode("utf-8", errors="replace"),
        raw_err.decode("utf-8", errors="replace"),
    )


def _read(command: str, returncode: int, stdout: str, stderr: str) -> AgentRun:
    """The run as the backbone's document states it, or why there is none."""
    try:
        document = json.loads(stdout)
    except ValueError:
        document = None
    if isinstance(document, Mapping):
        run, problem = _from_document(document)
        if run is not None:
            return run
        return AgentRun(NO_ANSWER, reason=f"{command} answered {problem}")
    said = [line.strip() for line in stderr.splitlines() if line.strip()]
    if any("No such command" in line for line in said):
        return AgentRun(
            NO_ANSWER,
            reason=(
                f"{command}: the `pkit` that ran — {_which()} — has no such command, so this "
                "project's backbone is older than project-management needs. Upgrade the "
                "backbone (`pkit upgrade`), or put a `pkit` that has the command first on PATH"
            ),
        )
    return AgentRun(
        NO_ANSWER,
        reason=f"{command} exited {returncode}" + (f": {said[-1]}" if said else " with no answer"),
    )


def _from_document(document: Mapping[str, Any]) -> tuple[AgentRun | None, str]:
    """The run the document states, or None and what is wrong with it."""
    version = document.get("schema_version")
    if version != VERSION or isinstance(version, bool):
        return None, f"schema_version {version!r}; pm reads {VERSION}"
    ending = document.get("ending")
    if ending not in ENDINGS:
        return None, f"an ending pm does not know, {ending!r}"
    exit_code = document.get("exit_code")
    if exit_code is not None and (not isinstance(exit_code, int) or isinstance(exit_code, bool)):
        return None, f"an exit_code that is not an integer, {exit_code!r}"
    if ending == FINISHED and exit_code is None:
        return None, "a finished run with no exit_code"
    texts: dict[str, str] = {}
    for key in ("output", "diagnostics", "reason"):
        value = document.get(key, "")
        if not isinstance(value, str):
            return None, f"a {key} that is not a string"
        texts[key] = value
    return AgentRun(str(ending), exit_code, **texts), ""


def _stop(process: subprocess.Popen[bytes]) -> None:
    """Ask `pkit` alone to stop, so it stops its runner; kill it once the grace
    has passed. Its group is the caller's, so the group is never signalled."""
    with contextlib.suppress(ProcessLookupError):  # it ended meanwhile
        process.terminate()
    try:
        process.wait(timeout=GRACE_SECONDS)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()
    for stream in (process.stdin, process.stdout, process.stderr):
        if stream is not None:
            stream.close()


def _which() -> str:
    """The `pkit` a run finds on PATH, as a path."""
    return shutil.which(ARGV[0]) or "not found on PATH"
