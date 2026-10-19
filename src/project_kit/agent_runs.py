"""The backbone's run command: a command starts an agent only through it (ADR-066).

No command calls a harness. A capability asks `pkit agents run` to run an agent,
and the backbone starts the runner the project's adapter registers, which
starts the harness (ADR-066 point 1). This module is that command's work:

- **Finding the runner.** An adapter registers its runner in its package's
  `commands:` tree under one fixed reference, `RUNNER_REFERENCE`. The backbone
  finds it with its one lookup of that tree (`command_runner`). Where no
  registered adapter has one, the run is refused and names the adapters. Where
  more than one has one, it is refused too, until a record says how a project
  names its harness.
- **Running it.** The runner runs under the agent-run policy of the one command
  runner (ADR-057 point 5): no arguments, the request as one JSON document on
  standard input, the caller's environment unchanged but for the run's
  deadline, from the project root, bounded by the run's limit plus
  `RUNNER_MARGIN_SECONDS`, the time the runner keeps to end the harness and
  answer. Past that bound, or on an interrupt, the runner is asked to stop, so
  it ends the harness it started, and is killed after `END_GRACE_SECONDS`.
- **Reading its answer.** The runner answers with one JSON document
  (`ANSWER_VERSION`): how the run ended, the harness's exit, the agent's
  output, the harness's diagnostics and a reason. Anything else is a run with
  no answer, and the document says how the runner ended.

What crosses the boundary is ADR-066 point 2's, in its unconfined form: the
agent, the brief, the folder the run runs in, a wall-clock limit, and an
effort level where one is set. The confined form, its clone and its check,
and the marker of a run are the drift command's change (ADR-066,
Implications). Until they arrive, a request carries no other key, and a
runner refuses one that does.

The document the command writes for its caller (`AgentRun.as_json`) is the
contract. A caller decides on its `ending`, never on the exit code.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from project_kit import command_runner
from project_kit.command_runner import END_GRACE_SECONDS, Ending, registered_commands
from project_kit.manifest import read_backbone_manifest

#: The reference under which an adapter registers its runner in its `commands:`
#: tree (ADR-066 point 1). One fixed reference, so the backbone finds a runner
#: by its one lookup and never by a file's name.
RUNNER_REFERENCE = "run-agent"

#: The version of the request the backbone writes to the runner, of the answer
#: it reads back, and of the document it writes for its caller. A reader refuses
#: a version it does not know.
REQUEST_VERSION = 1
ANSWER_VERSION = 1
DOCUMENT_VERSION = 1

#: The time the runner keeps, past the run's limit, to end the harness and
#: answer. The backbone stops the runner only once this too has passed.
RUNNER_MARGIN_SECONDS = 30

#: The longest limit a run takes: a week. It keeps every wait on the run well
#: inside what the operating system's timers take.
MAX_LIMIT_SECONDS = 7 * 24 * 60 * 60

#: The effort levels a run may set, the methodology's vocabulary (the agents
#: README, "Model and effort").
EFFORT_LEVELS = ("low", "medium", "high", "xhigh", "max")

#: An agent's name: a letter or digit, then letters, digits, dots, underscores
#: and hyphens. So no name reads as a flag, a path or a second argument.
AGENT_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")

# How a run ended (ADR-066 point 2). The runner answers with the first four;
# the fifth is the backbone's, for a runner that gave no answer it could read.
FINISHED = "finished"  # the harness ran and exited: `exit_code` is its exit
NOT_STARTED = "not-started"  # the harness, or the runner, could not be started
TIMED_OUT = "timed-out"  # stopped at its limit, with every process it started
REFUSED = "refused"  # refused before it started, with the reason
NO_ANSWER = "no-answer"  # the runner ended without an answer; what ran is not known
RUNNER_ENDINGS = (FINISHED, NOT_STARTED, TIMED_OUT, REFUSED)
ENDINGS = (*RUNNER_ENDINGS, NO_ANSWER)


@dataclass(frozen=True)
class Request:
    """What a caller passes for one run (ADR-066 point 2, the unconfined form)."""

    agent: str
    brief: str
    folder: Path
    limit_seconds: int
    effort: str | None = None

    def problem(self) -> str | None:
        """Why the request cannot be run as it stands, or None. The CLI checks the
        same through its options; this holds for any other caller."""
        if not AGENT_NAME.fullmatch(self.agent):
            return (
                f"agent name {self.agent!r} is not a name: a letter or digit, then letters, "
                "digits, '.', '_' or '-'"
            )
        if not self.brief.strip():
            return "the brief is empty"
        if "\0" in self.brief:
            return "the brief holds a NUL character"
        if not self.folder.is_absolute() or not self.folder.is_dir():
            return f"the folder {self.folder} is not a directory"
        if isinstance(self.limit_seconds, bool) or not 1 <= self.limit_seconds <= MAX_LIMIT_SECONDS:
            return f"the limit must be from 1 to {MAX_LIMIT_SECONDS} seconds"
        if self.effort is not None and self.effort not in EFFORT_LEVELS:
            return f"effort {self.effort!r} is not one of {', '.join(EFFORT_LEVELS)}"
        return None

    def as_json(self) -> dict[str, Any]:
        """The request as the runner reads it on standard input."""
        return {
            "schema_version": REQUEST_VERSION,
            "agent": self.agent,
            "brief": self.brief,
            "folder": str(self.folder),
            "limit_seconds": self.limit_seconds,
            "effort": self.effort,
        }


@dataclass(frozen=True)
class AgentRun:
    """How one run ended (ADR-066 point 2): the ending, the harness's exit when
    it finished, the agent's output, the harness's diagnostics, and the reason
    for any ending but a finish. `runner` names the adapter whose runner ran it,
    or None when no runner was reached."""

    agent: str
    ending: str
    runner: str | None = None
    exit_code: int | None = None
    output: str = ""
    diagnostics: str = ""
    reason: str = ""

    @property
    def succeeded(self) -> bool:
        """The harness ran and exited 0."""
        return self.ending == FINISHED and self.exit_code == 0

    def as_json(self) -> dict[str, Any]:
        return {
            "schema_version": DOCUMENT_VERSION,
            "agent": self.agent,
            "runner": self.runner,
            "ending": self.ending,
            "exit_code": self.exit_code,
            "output": self.output,
            "diagnostics": self.diagnostics,
            "reason": self.reason,
        }

    @property
    def described(self) -> str:
        """How the run ended, as a line names it after the agent's name."""
        if self.ending == FINISHED:
            return f"finished, exit {self.exit_code}"
        return f"{self.ending}: {self.reason}"


@dataclass(frozen=True)
class Runner:
    """The runner one registered adapter registers: the adapter, and its script."""

    adapter: str
    script: Path


def find_runners(target_root: Path) -> tuple[list[Runner], list[str]]:
    """Every runner the registered adapters register under `RUNNER_REFERENCE`,
    in manifest order, and the names of every registered adapter. Only an
    adapter's runner counts: the tie to a harness is an adapter's (ADR-066
    point 1)."""
    backbone = read_backbone_manifest(target_root)
    if backbone is None:
        return [], []
    runners: list[Runner] = []
    adapters: list[str] = []
    for entry in backbone.components:
        if entry.kind != "adapter":
            continue
        adapters.append(entry.name)
        commands = registered_commands(target_root / ".pkit" / "adapters" / entry.name)
        leaf = command_runner.resolve_command(commands, RUNNER_REFERENCE)
        if leaf is not None:
            runners.append(Runner(entry.name, leaf.script))
    return runners, adapters


def run_agent(target_root: Path, request: Request) -> AgentRun:
    """Run one agent through the runner the project's adapter registers.

    Never raises for what the runner or the harness did: every ending is in
    the run's document. A request with a problem is refused before any runner
    is looked for."""
    problem = request.problem()
    if problem is not None:
        return AgentRun(request.agent, REFUSED, reason=problem)
    runners, adapters = find_runners(target_root)
    if not runners:
        named = ", ".join(adapters) if adapters else "none is registered"
        return AgentRun(
            request.agent,
            REFUSED,
            reason=(
                f"no registered adapter registers an agent runner (the `{RUNNER_REFERENCE}` "
                f"command); registered adapters: {named}"
            ),
        )
    if len(runners) > 1:
        named = ", ".join(runner.adapter for runner in runners)
        return AgentRun(
            request.agent,
            REFUSED,
            reason=(
                f"more than one registered adapter registers an agent runner: {named}. A "
                "project runs its agents through one adapter's runner"
            ),
        )
    [runner] = runners
    if not runner.script.is_file():
        return AgentRun(
            request.agent,
            REFUSED,
            runner=runner.adapter,
            reason=f"the runner `{runner.adapter}` registers, {runner.script}, does not exist",
        )
    run = command_runner.run_command(
        runner.script,
        [],
        cwd=target_root,
        bound_seconds=request.limit_seconds + RUNNER_MARGIN_SECONDS,
        stdin=json.dumps(request.as_json()).encode("utf-8"),
        grace_seconds=END_GRACE_SECONDS,
    )
    return _read(request.agent, runner.adapter, run)


def _read(agent: str, adapter: str, run: command_runner.CommandRun) -> AgentRun:
    """The run's document from the runner's run: its answer, or what ended it."""
    named = f"the runner `{adapter}`"
    if run.ending is Ending.ANSWERED:
        answer, problem = _answer(run.document)
        if answer is not None:
            return AgentRun(agent, runner=adapter, **answer)
        return AgentRun(agent, NO_ANSWER, runner=adapter, reason=f"{named} answered {problem}")
    if run.ending is Ending.TIMED_OUT:
        within = (
            run.bound_described
            if run.clipped
            else f"{run.bound_seconds:g} s, its limit and {RUNNER_MARGIN_SECONDS} s to end the "
            "harness"
        )
        return AgentRun(
            agent,
            TIMED_OUT,
            runner=adapter,
            reason=f"{named} did not answer within {within}, and was stopped",
        )
    if run.ending is Ending.NOT_STARTED:
        return AgentRun(
            agent, NOT_STARTED, runner=adapter, reason=f"{named} {run.ending_described}"
        )
    tail = run.stderr_tail
    return AgentRun(
        agent,
        NO_ANSWER,
        runner=adapter,
        diagnostics=tail,
        reason=f"{named} {run.ending_described}" + (f": {tail.splitlines()[-1]}" if tail else ""),
    )


def _answer(document: object) -> tuple[dict[str, Any] | None, str]:
    """The runner's answer as `AgentRun` fields, or None and what is wrong with it.

    The answer is a JSON object of `ANSWER_VERSION`: `ending`, one of the
    runner's endings; `exit_code`, an integer when the run finished and null
    otherwise; and `output`, `diagnostics` and `reason`, strings, each absent
    read as empty."""
    if not isinstance(document, Mapping):
        return None, "something other than a JSON object"
    fields = cast("Mapping[str, object]", document)
    version = fields.get("schema_version")
    if isinstance(version, bool) or version != ANSWER_VERSION:
        return None, f"schema_version {version!r}; the backbone reads {ANSWER_VERSION}"
    ending = fields.get("ending")
    if ending not in RUNNER_ENDINGS:
        return None, f"an ending the backbone does not know, {ending!r}"
    exit_code = fields.get("exit_code")
    if ending == FINISHED:
        if isinstance(exit_code, bool) or not isinstance(exit_code, int):
            return None, "a finished run with no integer exit_code"
    elif exit_code is not None:
        return None, f"exit_code {exit_code!r} for a run that did not finish"
    texts: dict[str, str] = {}
    for key in ("output", "diagnostics", "reason"):
        value = fields.get(key, "")
        if not isinstance(value, str):
            return None, f"a {key} that is not a string"
        texts[key] = value
    return {"ending": ending, "exit_code": exit_code, **texts}, ""


def render_json(run: AgentRun) -> str:
    """The run's document as one line of JSON, keys sorted."""
    return json.dumps(run.as_json(), sort_keys=True, ensure_ascii=False) + "\n"
