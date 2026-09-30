"""One primitive for the commands a component registers (ADR-057 point 5).

A capability or an adapter registers what the backbone can run in one place:
the `commands:` tree of its package metadata (COR-021). A key is a token; a
value carrying `script` is a leaf; any other mapping is a group of further
tokens. Two halves live here, and every reader of that tree goes through them.

**The lookup.** `command_leaves` is the one walk of the tree, and
`registered_commands` reads a component's package file through it; a reference
— a path through the tree, tokens separated by spaces (`create page`) — names
a leaf through `resolve_command`. The dispatcher (`pkit <capability> <command>`),
package validation, the validator registry, the process engine's predicate
runner and the report builder, asking for the workstream, all read the tree
this way, so what counts as a leaf, and where its script is, is decided once.

**The run.** `run_command` starts a leaf's script with an explicit argument
list from a working directory, in its own process group, bounded by
`COMMAND_TIMEOUT_SECONDS`; it captures standard output and standard error and
parses standard output as one JSON document. Exceeding the bound kills the
whole process group — a script with a `uv run --script` shebang starts its
interpreter as a grandchild, which killing the child alone would leave running
with the pipes open. The run never outlives its caller: an interrupt kills the
group too. `CommandRun` says how the run ended; it never raises for what the
command did.

**A run inside a run** (ADR-057 point 3). A command the runner starts may start
`pkit` again — a validator reads a point through `pkit connections resolve`,
whose filler this runner then starts. Every run tells its command, in the
environment, the deadline by which anything it starts must have ended
(`DEADLINE_ENV`): its own end less `ANSWER_MARGIN_SECONDS`, the time the
command keeps to answer after something it started ran out. A run that
inherits one is *nested*: it is bounded by the time remaining, never more than
its own bound, and it does not start a new session, so its command joins the
group the outermost run kills — its deadline and its interrupt reach the whole
tree. The innermost command to overrun is the one a no-answer names, since its
deadline comes first. A nested run cannot kill a group it shares with its own
caller, so on its timeout it kills its command alone and records, in the file
the outermost run named (`STRAYS_ENV`), that what that command started may
still be running; the outermost run kills its whole group when its command
ends. Without an inherited deadline — `pkit` run from a shell — nothing
changes.

**Policies stay with their callers** — one mechanism, a policy per kind:

- the *predicate* policy (`process.PredicateRunner`): the subject and `--json`
  as arguments, the caller's environment unchanged — a predicate may reach the
  network — and the payload read by the gate; anything but an answered JSON
  object is indeterminate, fail-closed;
- the *query* policy (`validators.run_query`, ADR-057 point 3, ADR-058): the
  leaf must declare the query contract, `--json` as the one argument, the
  offline marker set, and the answer validated against the shape asked for;
  anything else is no answer, an error finding;
- the *context-read* policy (`report_context.pm_workstream`, ADR-050): no
  arguments, the caller's environment unchanged — the verb asks the tracker —
  and the value read as the text an exit-0 run prints, not a JSON document;
  anything else omits the workstream from the report, and an overrun says so;
- a *subscriber* policy joins when events run subscribers (COR-053 point 9
  sets its limits; point 11 asks the kinds to share one command runner).

The dispatcher's proxy — `pkit <capability> <command>` run by a person — uses
the lookup and not the run: it inherits the terminal's streams and is not
bounded.
"""

from __future__ import annotations

import contextlib
import json
import math
import os
import signal
import subprocess
import tempfile
import time
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, TypeVar

from ruamel.yaml import YAML

# A component's package metadata, relative to the component root, and the keys
# of the command tree inside it (COR-021).
PACKAGE_FILE = "package.yaml"
COMMANDS_KEY = "commands"
SCRIPT_KEY = "script"
HELP_KEY = "help"

# The time bound on every command the backbone runs on a component's behalf
# and reads an answer from — predicates and queries alike. A fixed backbone
# constant, not a setting (ADR-057 point 3); exceeding it kills the command's
# whole process group.
COMMAND_TIMEOUT_SECONDS = 30

# A run inside a run (the module docstring). The environment every run gives its
# command: the deadline, in seconds since the epoch, by which anything the
# command starts must have ended; and the path of the file a nested run writes
# when what its command started may outlive it, which the run that named the
# file reads when its own command ends. The margin is what each command keeps
# of its bound to answer after something it started ran out of time.
DEADLINE_ENV = "PKIT_COMMAND_DEADLINE"
STRAYS_ENV = "PKIT_COMMAND_STRAYS"
ANSWER_MARGIN_SECONDS = 2

# The detail of a nested run that had no time left to start its command.
NO_TIME_LEFT = "no time was left of the bound of the run that started it"

_yaml = YAML(typ="safe")

_Leaf = TypeVar("_Leaf")


# --- the lookup -----------------------------------------------------------


@dataclass(frozen=True)
class RegisteredCommand:
    """One leaf of a component's `commands:` tree: its token path, the script
    it names (relative to the component root, resolved here), and the entry as
    declared — `help`, `query-contract` and whatever else it carries."""

    tokens: tuple[str, ...]
    script: Path
    entry: Mapping[Any, Any]

    @property
    def reference(self) -> str:
        """The path through the tree that names this leaf, as a reference is written."""
        return " ".join(self.tokens)

    @property
    def name(self) -> str:
        """The leaf's own token — the address a process predicate's `run:` uses."""
        return self.tokens[-1]

    @property
    def help(self) -> str:
        return str(self.entry.get(HELP_KEY) or "")


def command_leaves(tree: Mapping[Any, Any]) -> dict[tuple[str, ...], Mapping[Any, Any]]:
    """Every leaf of a `commands:` tree as declared, keyed by token path, in
    declaration order. A leaf is a mapping carrying `script`; any other mapping
    is a group; anything else is skipped."""
    leaves: dict[tuple[str, ...], Mapping[Any, Any]] = {}

    def walk(node: Mapping[Any, Any], prefix: tuple[str, ...]) -> None:
        for token, value in node.items():
            if not isinstance(value, Mapping):
                continue
            tokens = (*prefix, str(token))
            if SCRIPT_KEY in value:
                leaves[tokens] = value
            else:
                walk(value, tokens)

    walk(tree, ())
    return leaves


def commands_of(component_dir: Path, tree: Any) -> dict[tuple[str, ...], RegisteredCommand]:
    """The commands a `commands:` block registers for the component at
    `component_dir`, keyed by token path. A block that is not a mapping
    registers nothing."""
    if not isinstance(tree, Mapping):
        return {}
    return {
        tokens: RegisteredCommand(tokens, component_dir / str(leaf.get(SCRIPT_KEY)), leaf)
        for tokens, leaf in command_leaves(tree).items()
    }


def registered_commands(component_dir: Path) -> dict[tuple[str, ...], RegisteredCommand]:
    """The commands the component at `component_dir` registers in its package
    file. Read defensively: a missing or unreadable file, or one whose
    `commands:` is not a mapping, registers nothing — package validation
    reports why."""
    try:
        raw = _yaml.load((component_dir / PACKAGE_FILE).read_text(encoding="utf-8"))
    except Exception:  # absent, unreadable, or ruamel's own hierarchy
        return {}
    return commands_of(component_dir, raw.get(COMMANDS_KEY) if isinstance(raw, Mapping) else None)


def resolve_command(commands: Mapping[tuple[str, ...], _Leaf], reference: str) -> _Leaf | None:
    """The leaf `reference` names — a path through the tree, tokens separated
    by spaces — or None when it names none. Takes the leaves as `commands_of`
    or `command_leaves` gives them."""
    return commands.get(tuple(reference.split()))


# --- the run --------------------------------------------------------------


class Ending(Enum):
    """How one run of a command ended."""

    ANSWERED = "answered"  # exited 0 and printed one JSON document (`document`)
    UNPARSABLE = "unparsable"  # exited 0; standard output is not one JSON document
    ABNORMAL_EXIT = "abnormal-exit"  # exited non-zero (`returncode`, `stderr`)
    TIMED_OUT = "timed-out"  # exceeded the bound; its whole process group was killed
    NOT_STARTED = "not-started"  # could not be started, or no time was left to (`detail`)


@dataclass(frozen=True)
class CommandRun:
    """What one run of a command produced. `document` is meaningful only when
    the run `ANSWERED`; `bound_seconds` is the bound it ran under."""

    ending: Ending
    bound_seconds: float
    document: Any = None
    returncode: int | None = None
    stdout: str = ""
    stderr: str = ""
    detail: str = ""


def run_command(
    script: Path,
    args: Sequence[str],
    *,
    cwd: Path,
    extra_env: Mapping[str, str] | None = None,
) -> CommandRun:
    """Run `script` with `args` from `cwd`, in its own process group, bounded by
    `COMMAND_TIMEOUT_SECONDS`, and read its answer. `extra_env` is laid over
    the caller's environment. Standard output is the answer and nothing else;
    standard error is diagnostics.

    Inside another run — the environment carries its deadline — the run is
    nested (the module docstring): bounded by the time remaining, in its
    caller's process group. With no time remaining its command is not started."""
    inherited = _inherited_deadline()
    now = time.time()
    bound = COMMAND_TIMEOUT_SECONDS if inherited is None else _remaining(inherited, now)
    if bound <= 0:
        return CommandRun(Ending.NOT_STARTED, 0, detail=NO_TIME_LEFT)
    nested = inherited is not None
    strays = os.environ.get(STRAYS_ENV, "") if nested else _strays_path()
    env = {
        **os.environ,
        **(extra_env or {}),
        DEADLINE_ENV: f"{now + bound - ANSWER_MARGIN_SECONDS:.3f}",
    }
    if strays:
        env[STRAYS_ENV] = strays
    try:
        process = subprocess.Popen(
            [str(script), *args],
            cwd=str(cwd),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=not nested,
        )
    except OSError as exc:
        return CommandRun(Ending.NOT_STARTED, bound, detail=str(exc))
    try:
        raw_stdout, raw_stderr = process.communicate(timeout=bound)
    except subprocess.TimeoutExpired:
        _stop(process, nested=nested, strays=strays)
        return CommandRun(Ending.TIMED_OUT, bound)
    except BaseException:
        _stop(process, nested=nested, strays=strays)
        raise
    finally:
        if not nested:
            _end_strays(process, strays)
    stderr = _decode(raw_stderr)
    try:
        stdout = (raw_stdout or b"").decode("utf-8")
    except UnicodeDecodeError as exc:
        # Standard output is the answer; a byte the encoding cannot read is no
        # answer, never a repaired one (a replacement inside a JSON string would
        # still parse and open a gate). Diagnostics on stderr are only shown.
        return CommandRun(
            Ending.UNPARSABLE, bound, returncode=process.returncode,
            stdout=_decode(raw_stdout), stderr=stderr, detail=f"standard output is not UTF-8: {exc}",
        )
    if process.returncode != 0:
        return CommandRun(
            Ending.ABNORMAL_EXIT, bound, returncode=process.returncode, stdout=stdout, stderr=stderr
        )
    try:
        document = parse_document(stdout)
    except ValueError:
        return CommandRun(Ending.UNPARSABLE, bound, returncode=0, stdout=stdout, stderr=stderr)
    return CommandRun(
        Ending.ANSWERED, bound, document=document, returncode=0, stdout=stdout, stderr=stderr
    )


def parse_document(text: str) -> Any:
    """The one JSON document `text` holds — whitespace around it allowed,
    nothing else. Raises `ValueError` when it holds none."""
    return json.loads(text)


def _inherited_deadline() -> float | None:
    """The deadline of the run this process runs inside, from the environment;
    None outside one, or when the value is not a number, which no run writes."""
    raw = os.environ.get(DEADLINE_ENV)
    if raw is None:
        return None
    try:
        deadline = float(raw)
    except ValueError:
        return None
    return deadline if math.isfinite(deadline) else None


def _remaining(deadline: float, now: float) -> float:
    """A nested run's bound: the time left until the inherited deadline, to a
    tenth of a second, never more than a run's own bound."""
    return min(COMMAND_TIMEOUT_SECONDS, round(deadline - now, 1))


def _strays_path() -> str:
    """A path no run has named, for the file a nested run under this one writes
    when what its command started may outlive it. Nothing is created here."""
    return os.path.join(tempfile.gettempdir(), f"pkit-strays-{uuid.uuid4().hex}")


def _stop(process: subprocess.Popen[bytes], *, nested: bool, strays: str) -> None:
    """End a command that overran or was interrupted: its whole group when the
    run started one, else the command alone, recording the strays."""
    if nested:
        _kill_command(process, strays)
    else:
        _kill_process_group(process)


def _kill_process_group(process: subprocess.Popen[bytes]) -> None:
    """End the command and everything it started. `start_new_session` made it
    the leader of its own group, so one signal reaches the grandchild a `uv run
    --script` shebang starts — which `Popen.kill` alone leaves running, holding
    the pipes open, and a second `communicate` would then wait on. The pipes
    are closed unread: nothing printed after the bound is an answer."""
    if hasattr(os, "killpg"):
        with contextlib.suppress(ProcessLookupError):  # the whole group already ended
            os.killpg(process.pid, signal.SIGKILL)
    else:  # pragma: no cover — no process groups on this platform
        process.kill()
    process.wait()
    _close_pipes(process)


def _kill_command(process: subprocess.Popen[bytes], strays: str) -> None:
    """End a nested run's command. Its group is its caller's too, so a signal to
    the group would end the caller: the command alone is killed, its pipes
    closed unread as for a group. What it started may still run — a `uv run
    --script` shebang's interpreter, a `pkit` reading command — in the group
    the outermost run kills; the strays file tells that run to, when its
    command ends, rather than only on its own timeout."""
    process.kill()
    process.wait()
    _close_pipes(process)
    if strays:
        with contextlib.suppress(OSError):  # unrecorded, they end only with the outer kill
            Path(strays).touch()


def _end_strays(process: subprocess.Popen[bytes], strays: str) -> None:
    """After the outermost run's command ended, however it ended: when a nested
    run recorded strays, end the whole group the command led, then forget the
    record. The group outlives its leader while any member runs, so its id
    still names it."""
    record = Path(strays)
    if not record.exists():
        return
    if hasattr(os, "killpg"):
        with contextlib.suppress(ProcessLookupError):  # nothing was left after all
            os.killpg(process.pid, signal.SIGKILL)
    record.unlink(missing_ok=True)


def _close_pipes(process: subprocess.Popen[bytes]) -> None:
    for stream in (process.stdout, process.stderr):
        if stream is not None:
            stream.close()


def _decode(data: bytes | None) -> str:
    """Diagnostic output as text; a byte the encoding cannot read is replaced,
    never a crash. Standard output — the answer — is decoded strictly in
    `run_command`, where an undecodable byte ends the run as UNPARSABLE."""
    return (data or b"").decode("utf-8", errors="replace")
