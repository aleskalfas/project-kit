"""The backbone's run command: a command starts an agent only through it (ADR-066).

No command calls a harness. A capability asks `pkit agents run` to run an agent,
and the backbone starts the runner the project's adapter registers, which
starts the harness (ADR-066 point 1). This module is that command's work:

- **Finding the runner.** An adapter registers its runner in its package's
  `commands:` tree under one fixed reference, `RUNNER_REFERENCE`. The backbone
  finds it with its one lookup of that tree (`command_runner`). Where no
  registered adapter has one, the run is refused and names the adapters. Where
  more than one has one, it is refused too, until a record says how a project
  names its harness. An adapter's name must be a plain name, and its runner's
  script must lie inside its folder, or no runner of it is run.
- **Running it.** The runner runs under the agent-run policy of the one command
  runner (ADR-057 point 5): no arguments, the request as one JSON document on
  standard input, the caller's environment unchanged but for the run's
  deadline, from the project root, bounded by the run's limit plus
  `RUNNER_MARGIN_SECONDS`, the time the runner keeps to end the harness and
  answer. A confined run's runner runs from the clone's root instead, and
  Python writes no bytecode there, so the check reads no file the runner's
  own imports wrote. Past that bound, or on an interrupt, the runner is asked to stop, so
  it ends the harness it started, and is killed after `END_GRACE_SECONDS`. A
  run inside a command the backbone runs is refused: that run's kill asks
  nothing first, so the harness would escape it.
- **Reading its answer.** The runner answers with one JSON document
  (`ANSWER_VERSION`): how the run ended, the harness's exit, the agent's
  output, the harness's diagnostics and a reason, and the calls the harness
  refused where it reports them. Anything else is a run with no answer, and
  the document says how the runner ended.
- **The marker of a run** (ADR-066 point 8). A run is a leaf. The runner sets
  `MARKER_ENV` in the harness's environment, so every process of the run
  inherits it. The run command refuses whenever it is set, empty included,
  before it reads or writes anything. Nothing in the backbone sets it.

What crosses the boundary is ADR-066 point 2's, in two forms:

- **Unconfined:** the agent, the brief, the folder the run runs in, a
  wall-clock limit, and an effort level where one is set. The review
  command's runs take this form (ADR-066 point 10).
- **Confined:** the same without the folder, and in its place the commit, the
  command whose run rules hold the run (`<capability>:<command>`), and the
  folder the run's files go to. The backbone makes a clone at the commit,
  reads the run's rules there, starts the runner the clone's adapter
  registers, checks the clone after the run, and copies the run's files
  (`agent_confinement`, ADR-066 points 6 and 7).

The document the command writes for its caller (`AgentRun.as_json`) is the
contract. A caller decides on its `ending`, never on the exit code. For a
confined run, it reads the check's verdict before it trusts the run's files.
"""

from __future__ import annotations

import dataclasses
import json
import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from project_kit import agent_confinement, agent_policy, command_runner
from project_kit.agent_confinement import CHECK_NOT_RUN, Check, Confinement
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
#: README, "Model and effort"), held once in `agent_policy`.
EFFORT_LEVELS = agent_policy.EFFORT_LEVELS

#: An agent's name: a letter or digit, then letters, digits, dots, underscores
#: and hyphens. So no name reads as a flag, a path or a second argument.
AGENT_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")

#: The marker of a run (ADR-066 point 8). The runner sets it in the harness's
#: environment; the run command refuses wherever it is set, empty included.
MARKER_ENV = "PKIT_AGENT_RUN"

#: A confined run's commit: a full commit id.
COMMIT_ID = re.compile(r"[0-9a-f]{40}")

#: The command whose run rules hold a confined run: a capability's name and one
#: of its commands, each a plain name.
RULES_OF = re.compile(r"[a-z][a-z0-9-]{0,63}:[a-z][a-z0-9-]{0,63}")

#: What the run command refuses with when the marker is set.
INSIDE_A_RUN = (
    f"`{MARKER_ENV}` is set, so this runs inside an agent run, and a run starts no other "
    "agent (ADR-066 point 8). Nothing was read or written"
)

# How a run ended (ADR-066 point 2). The runner answers with the first four;
# the fifth is the backbone's, for a runner that gave no answer it could read.
FINISHED = "finished"  # the harness ran and exited: `exit_code` is its exit
NOT_STARTED = "not-started"  # the harness, or the runner, could not be started
TIMED_OUT = "timed-out"  # stopped at its limit, with the processes the runner reaches
REFUSED = "refused"  # refused before it started, with the reason
NO_ANSWER = "no-answer"  # the runner ended without an answer; what ran is not known
RUNNER_ENDINGS = (FINISHED, NOT_STARTED, TIMED_OUT, REFUSED)
ENDINGS = (*RUNNER_ENDINGS, NO_ANSWER)


@dataclass(frozen=True)
class Request:
    """What a caller passes for one run (ADR-066 point 2).

    An unconfined run names its `folder`. A confined run names none, and names
    instead the `commit`, the command whose run rules hold it (`rules_of`, as
    `<capability>:<command>`) and the folder its files go to (`files_to`)."""

    agent: str
    brief: str
    folder: Path | None
    limit_seconds: int
    effort: str | None = None
    commit: str | None = None
    rules_of: str | None = None
    files_to: Path | None = None

    @property
    def confined(self) -> bool:
        """Whether the run is confined: it names no folder to run in."""
        return self.folder is None

    def problem(self, target_root: Path | None = None) -> str | None:
        """Why the request cannot be run as it stands, or None. The CLI checks the
        same through its options; this holds for any other caller. With
        `target_root`, a confined run's commit must be one that repository holds."""
        if not AGENT_NAME.fullmatch(self.agent):
            return (
                f"agent name {self.agent!r} is not a name: a letter or digit, then letters, "
                "digits, '.', '_' or '-'"
            )
        if not self.brief.strip():
            return "the brief is empty"
        if "\0" in self.brief:
            return "the brief holds a NUL character"
        if isinstance(self.limit_seconds, bool) or not 1 <= self.limit_seconds <= MAX_LIMIT_SECONDS:
            return f"the limit must be from 1 to {MAX_LIMIT_SECONDS} seconds"
        if self.effort is not None and self.effort not in EFFORT_LEVELS:
            return f"effort {self.effort!r} is not one of {', '.join(EFFORT_LEVELS)}"
        if self.folder is not None:
            if (self.commit, self.rules_of, self.files_to) != (None, None, None):
                return (
                    "a run names a folder to run in, or a commit, the rules of a command and a "
                    "folder for its files, never both"
                )
            if not self.folder.is_absolute() or not self.folder.is_dir():
                return f"the folder {self.folder} is not a directory"
            return None
        return self._confined_problem(target_root)

    def _confined_problem(self, target_root: Path | None) -> str | None:
        """Why a confined request cannot be run, or None."""
        if self.commit is None or self.rules_of is None or self.files_to is None:
            return (
                "a run names a folder to run in, or a commit, the rules of a command and a "
                "folder for its files, all three"
            )
        if not COMMIT_ID.fullmatch(self.commit):
            return f"the commit {self.commit!r} is not a full commit id, 40 lowercase hex digits"
        if not RULES_OF.fullmatch(self.rules_of):
            return (
                f"the rules of {self.rules_of!r} name no command: a capability's name and one of "
                "its commands, as `<capability>:<command>`"
            )
        if not self.files_to.is_absolute() or not self.files_to.is_dir():
            return f"the folder for the run's files, {self.files_to}, is not a directory"
        if target_root is not None and not agent_confinement.holds_commit(target_root, self.commit):
            return f"the repository holds no commit {self.commit}"
        return None

    def as_json(self, confined: Mapping[str, Any] | None = None) -> dict[str, Any]:
        """The request as the runner reads it on standard input: with the folder,
        or, for a confined run, with the `confined` block in its place
        (`agent_confinement.request_block`)."""
        document: dict[str, Any] = {
            "schema_version": REQUEST_VERSION,
            "agent": self.agent,
            "brief": self.brief,
        }
        if confined is None:
            document["folder"] = str(self.folder)
        document["limit_seconds"] = self.limit_seconds
        document["effort"] = self.effort
        if confined is not None:
            document["confined"] = dict(confined)
        return document


@dataclass(frozen=True)
class AgentRun:
    """How one run ended (ADR-066 point 2): the ending, the harness's exit when
    it finished, the agent's output, the harness's diagnostics, and the reason
    for any ending but a finish. `runner` names the adapter whose runner ran it,
    or None when no runner was reached. `refused_calls` are the calls the
    harness refused, where the runner reports them.

    A confined run also carries its `commit`, the `check` of its clone, the
    folder its `files` were copied to (None when they were not), and the
    commands it `excluded` from the sandbox."""

    agent: str
    ending: str
    runner: str | None = None
    exit_code: int | None = None
    output: str = ""
    diagnostics: str = ""
    reason: str = ""
    refused_calls: tuple[Mapping[str, str], ...] = ()
    confined: bool = False
    commit: str | None = None
    check: Check | None = None
    files: Path | None = None
    excluded: tuple[tuple[str, ...], ...] = ()

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
            "refused_calls": [dict(call) for call in self.refused_calls],
            "confined": self.confined,
            "commit": self.commit,
            "check": None if self.check is None else self.check.as_json(),
            "files": None if self.files is None else str(self.files),
            "excluded": [list(command) for command in self.excluded],
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
        if not AGENT_NAME.fullmatch(entry.name):  # a plain name, never a path
            continue
        commands = registered_commands(target_root / ".pkit" / "adapters" / entry.name)
        leaf = command_runner.resolve_command(commands, RUNNER_REFERENCE)
        if leaf is not None:
            runners.append(Runner(entry.name, leaf.script))
    return runners, adapters


def inside_a_run(agent: str, *, confined: bool, commit: str | None = None) -> AgentRun | None:
    """The refusal of a run started inside a run, where the marker is set at all,
    empty included (ADR-066 point 8); None outside one. A caller asks this before
    it reads or writes anything."""
    if MARKER_ENV not in os.environ:
        return None
    return AgentRun(
        agent,
        REFUSED,
        reason=INSIDE_A_RUN,
        confined=confined,
        commit=commit,
        check=CHECK_NOT_RUN if confined else None,
    )


def run_agent(target_root: Path, request: Request) -> AgentRun:
    """Run one agent through the runner the project's adapter registers.

    Never raises for what the runner or the harness did: every ending is in
    the run's document. A request with a problem is refused before any runner
    is looked for.

    A run inside an agent run is refused before anything else (`inside_a_run`).
    So is a run inside a command the backbone runs. That command's run bounds
    what it starts by its own deadline, and on overrun or an interrupt kills its
    whole group without asking first. So the runner would be killed before it
    could end the harness, which leads a session of its own and would run on.

    A confined request runs in a clone at its commit (`_run_confined`)."""
    marked = inside_a_run(request.agent, confined=request.confined, commit=request.commit)
    if marked is not None:
        return marked
    if command_runner.inherited_deadline() is not None:
        return _refused(
            request,
            "this run is inside a command the backbone runs, whose bound and kill the "
            "harness would escape: an agent run starts only outside one",
        )
    problem = request.problem(target_root)
    if problem is not None:
        return _refused(request, problem)
    if request.confined:
        return _run_confined(target_root, request)
    found = _runner_of(target_root, request)
    if isinstance(found, AgentRun):
        return found
    run = command_runner.run_command(
        found.script,
        [],
        cwd=target_root,
        bound_seconds=request.limit_seconds + RUNNER_MARGIN_SECONDS,
        stdin=json.dumps(request.as_json()).encode("utf-8"),
        grace_seconds=END_GRACE_SECONDS,
    )
    return _read(request.agent, found.adapter, run)


def _refused(
    request: Request, reason: str, *, runner: str | None = None, diagnostics: str = ""
) -> AgentRun:
    """A run refused before its runner started, as its document states it."""
    return AgentRun(
        request.agent,
        REFUSED,
        runner=runner,
        diagnostics=diagnostics,
        reason=reason,
        confined=request.confined,
        commit=request.commit,
        check=CHECK_NOT_RUN if request.confined else None,
    )


def _runner_of(root: Path, request: Request) -> Runner | AgentRun:
    """The one runner the adapters registered in the project at `root` register, or
    the refusal that says why there is none to run."""
    runners, adapters = find_runners(root)
    if not runners:
        named = ", ".join(adapters) if adapters else "none is registered"
        return _refused(
            request,
            f"no registered adapter registers an agent runner (the `{RUNNER_REFERENCE}` "
            f"command); registered adapters: {named}",
        )
    if len(runners) > 1:
        named = ", ".join(runner.adapter for runner in runners)
        return _refused(
            request,
            f"more than one registered adapter registers an agent runner: {named}. A "
            "project runs its agents through one adapter's runner",
        )
    [runner] = runners
    if not runner.script.is_file():
        return _refused(
            request,
            f"the runner `{runner.adapter}` registers, {runner.script}, does not exist",
            runner=runner.adapter,
        )
    folder = (root / ".pkit" / "adapters" / runner.adapter).resolve()
    if not runner.script.resolve().is_relative_to(folder):
        return _refused(
            request,
            f"the runner `{runner.adapter}` registers, {runner.script}, lies outside "
            "the adapter's folder",
            runner=runner.adapter,
        )
    return runner


def _run_confined(target_root: Path, request: Request) -> AgentRun:
    """Run a confined request (ADR-066 points 6 and 7) in a clone at its commit.

    The clone, its workspace and the run's `pkit` are made first, and removed on
    every exit (`agent_confinement.confinement`). A run that cannot be confined is
    refused, and its check is not run."""
    try:
        with agent_confinement.confinement(target_root, cast("str", request.commit)) as made:
            return _run_in(made, request)
    except agent_confinement.Refused as refused:
        return _refused(request, refused.reason)


def _run_in(made: Confinement, request: Request) -> AgentRun:
    """Run a confined request in the clone `made` holds, then check the clone and
    copy the run's files.

    The run's rules are read from the clone, and so is the runner, which the
    clone's registered adapters register. The runner runs from the clone's root
    under the agent-run policy, with Python writing no bytecode, so the runner's
    own imports change nothing the check reads. After the run, or a failed start,
    the clone is checked, and the run's files are copied to the caller's folder.
    What the copy refuses is part of the check."""
    rules_of, files_to = cast("str", request.rules_of), cast("Path", request.files_to)
    warnings = "\n".join(made.warnings)
    projection = agent_confinement.project(made, rules_of, request.agent)
    if isinstance(projection, str):
        return _refused(request, projection, diagnostics=warnings)
    excluded = agent_confinement.exclusions(made.clone, projection)
    found = _runner_of(made.clone, request)
    if isinstance(found, AgentRun):
        return dataclasses.replace(found, diagnostics=warnings)
    before = agent_confinement.record(made.clone)
    if before.unread:
        return _refused(
            request,
            "the clone's state cannot be read before the run: " + "; ".join(before.unread),
            runner=found.adapter,
            diagnostics=warnings,
        )
    brief = agent_confinement.replace_markers(request.brief, made)
    payload = dataclasses.replace(request, brief=brief).as_json(
        confined=agent_confinement.request_block(made, projection, excluded)
    )
    run = command_runner.run_command(
        found.script,
        [],
        cwd=made.clone,
        extra_env={"PYTHONDONTWRITEBYTECODE": "1"},
        bound_seconds=request.limit_seconds + RUNNER_MARGIN_SECONDS,
        stdin=json.dumps(payload).encode("utf-8"),
        grace_seconds=END_GRACE_SECONDS,
    )
    answered = _read(request.agent, found.adapter, run)
    check = agent_confinement.check(made.clone, before)
    check = check.with_refusals(agent_confinement.copy_files(made.workspace, files_to))
    return dataclasses.replace(
        answered,
        diagnostics="\n".join(part for part in (warnings, answered.diagnostics) if part),
        confined=True,
        commit=request.commit,
        check=check,
        files=files_to,
        excluded=excluded,
    )


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
    read as empty. `refused_calls` is read leniently (`_refused_calls`)."""
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
    return {
        "ending": ending,
        "exit_code": exit_code,
        "refused_calls": _refused_calls(fields.get("refused_calls")),
        **texts,
    }, ""


def _refused_calls(value: object) -> tuple[Mapping[str, str], ...]:
    """The calls the harness refused, as the runner reports them: a list of objects,
    each with a `tool` and an `input` string. Read leniently, so a runner that
    reports none, or reports them in another shape, answers with none. The start
    report a confined run's answer may carry is not read: the runner ends a run
    whose start report does not match its settings (ADR-066 point 9)."""
    if not isinstance(value, list):
        return ()
    calls: list[Mapping[str, str]] = []
    for item in cast("list[object]", value):
        if not isinstance(item, Mapping):
            continue
        call = cast("Mapping[str, object]", item)
        tool, given = call.get("tool"), call.get("input")
        if isinstance(tool, str) and isinstance(given, str):
            calls.append({"tool": tool, "input": given})
    return tuple(calls)


def render_json(run: AgentRun) -> str:
    """The run's document as one line of JSON, keys sorted."""
    return json.dumps(run.as_json(), sort_keys=True, ensure_ascii=False) + "\n"
