"""How project-management starts an agent with nobody watching (ADR-066 point 1).

A capability never calls a harness, and never looks for an adapter. It asks the
backbone's run command, `pkit agents run`, which starts the runner the
project's adapter registers, and the runner starts the harness. This module is
the one place project-management asks: `review-pr` starts its reviewers
through it (`run_agent`, the unconfined form), and `fix-drift` starts the
granted fixers through it (`run_confined`, the confined form: a clone at a
pinned commit, under the rules `permissions/runs.yaml` declares).

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
which ends the harness and the processes still descended from it. In a project
pinned to another backbone version, `pkit` is the router, which passes no such
signal on; there the runner still ends the harness at the run's limit.

The agent's name goes last, after `--`, so no name is read as an option.

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
#: killed: the backbone's grace on the runner (2 s), and room to spare.
GRACE_SECONDS = 10.0

# How a run ended, as the backbone's document names it.
FINISHED = "finished"
NOT_STARTED = "not-started"
TIMED_OUT = "timed-out"
REFUSED = "refused"
NO_ANSWER = "no-answer"
ENDINGS = (FINISHED, NOT_STARTED, TIMED_OUT, REFUSED, NO_ANSWER)


#: The check of a confined run's clone, as the backbone's document names it
#: (ADR-066 point 7): nothing changed outside the workspace, or a breach.
CLEAN = "clean"
BREACH = "breach"
NOT_RUN = "not-run"


@dataclass(frozen=True)
class AgentRun:
    """How one run ended: the ending, the harness's exit when it finished, the
    agent's output, the harness's diagnostics, and the reason for any other
    ending.

    A confined run (`run_confined`) also carries the check of its clone, its
    verdict and what changed; the folder its files were copied to; the calls
    the harness refused; and each command it ran outside the sandbox. An
    unconfined run leaves them empty."""

    ending: str
    exit_code: int | None = None
    output: str = ""
    diagnostics: str = ""
    reason: str = ""
    check: str = NOT_RUN
    changes: tuple[str, ...] = ()
    files: str | None = None
    refused_calls: tuple[str, ...] = ()
    excluded: tuple[str, ...] = ()

    @property
    def breached(self) -> bool:
        """The check found a change outside the workspace, or could not tell."""
        return self.check == BREACH


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
    argv = [*ARGV, "--folder", str(folder), "--limit", str(limit_seconds)]
    return _run(name, brief, argv, limit_seconds=limit_seconds, effort=effort)


def run_confined(
    name: str,
    brief: str,
    *,
    commit: str,
    rules_of: str,
    files_to: Path,
    limit_seconds: int,
    effort: str | None = None,
) -> AgentRun:
    """Run agent `name` once, confined (ADR-066 points 3 to 8): in a clone of
    the repository at `commit`, under the rules `rules_of` names
    (`<capability>:<command>`), its files copied to `files_to` once the clone
    is checked. The brief names the run's folders by the backbone's markers.
    Never raises for what the run did."""
    argv = [
        *ARGV,
        "--commit",
        commit,
        "--rules-of",
        rules_of,
        "--files-to",
        str(files_to),
        "--limit",
        str(limit_seconds),
    ]
    return _run(name, brief, argv, limit_seconds=limit_seconds, effort=effort)


def _run(
    name: str, brief: str, argv: list[str], *, limit_seconds: int, effort: str | None
) -> AgentRun:
    if effort is not None:
        argv += ["--effort", effort]
    argv += ["--json", "--", name]
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
    confined = _confined_keys(document)
    if isinstance(confined, str):
        return None, confined
    return AgentRun(str(ending), exit_code, **texts, **confined), ""


def _confined_keys(document: Mapping[str, Any]) -> dict[str, Any] | str:
    """A confined run's keys, which a backbone adds to its document (ADR-066
    point 2): absent, an unconfined run's. A null check is a run refused before
    its clone was made, so nothing was checked. A check that cannot be read is
    read as a breach, so the run's files are set aside."""
    if not document.get("confined"):
        return {}
    check = document.get("check")
    verdict, changes = BREACH, ("the backbone's check of the clone cannot be read",)
    if check is None:
        verdict, changes = NOT_RUN, ()
    elif isinstance(check, Mapping) and check.get("verdict") in (CLEAN, BREACH, NOT_RUN):
        verdict = str(check["verdict"])
        raw = check.get("changes") or []
        changes = tuple(str(c) for c in raw) if isinstance(raw, list) else changes
    files = document.get("files")
    if files is not None and not isinstance(files, str):
        return "a files that is not a path"
    refused = document.get("refused_calls") or []
    excluded = document.get("excluded") or []
    if not isinstance(refused, list) or not isinstance(excluded, list):
        return "refused_calls or excluded that is not a list"
    return {
        "check": verdict,
        "changes": changes,
        "files": files,
        "refused_calls": tuple(_call(c) for c in refused),
        "excluded": tuple(" ".join(e) if isinstance(e, list) else str(e) for e in excluded),
    }


def _call(value: Any) -> str:
    """A refused call as one line: its tool and what it was called with."""
    if isinstance(value, Mapping):
        return f"{value.get('tool', '?')}: {value.get('input', '')}".strip()
    return str(value)


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
