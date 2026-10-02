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
list from a working directory, in its own process group — inside another run,
the outermost run's — bounded by `COMMAND_TIMEOUT_SECONDS`; it captures
standard output and standard error and parses standard output as one JSON
document. Exceeding the bound kills the whole process group — a script with a
`uv run --script` shebang starts its interpreter as a grandchild, which killing
the child alone would leave running with the pipes open. The run never
outlives its caller: an interrupt kills the group too. `CommandRun` says how
the run ended; it never raises for what the command did.

**What a no-answer shows.** A caller that reports a run which gave no answer
names how it ended (`CommandRun.ending_described`) and may show what the
command said on standard error (`CommandRun.stderr_tail`): never the stream
whole, only its last lines, bounded in lines and in bytes
(`DIAGNOSTIC_TAIL_LINES`, `DIAGNOSTIC_TAIL_BYTES`), with every terminal
escape sequence and control character removed — a command's words reach the
operator's terminal, so a command must not be able to flood it or rewrite it.

**A run inside a run** (ADR-057 point 5). A command the runner starts may start
`pkit` again — a validator reads a point through `pkit connections resolve`,
whose filler this runner then starts — and the tree keeps one deadline and one
kill. Every run tells its command, in the environment, the deadline by which
anything it starts must have ended (`DEADLINE_ENV`): its own end less
`ANSWER_MARGIN_SECONDS`, the time the command keeps to answer after something
it started ran out. A run is *nested* when it runs inside a live run
(`inherited_deadline`); it is then bounded by the time remaining, never more
than its own bound, and it does not start a new session, so its command joins
the group the outermost run owns and kills — the outermost deadline and an
interrupt reach the whole tree. Each level's deadline comes before its
caller's, so the command that overran is the one a no-answer names, with the
bound it had, which may be the time its caller had left (`CommandRun.clipped`).

A nested run cannot kill a group it shares with its own caller, so on its
timeout it kills its command alone. What that command started — a `uv run
--script` interpreter, a `pkit` reading command — is left to the outermost
run: each nested run keeps a marker in the directory the outermost run made
(`STRAYS_ENV`) from before it starts its command until the command ends by
itself. A marker left behind — the command overran or was interrupted, or the
nested run's own process was killed by anyone else — makes the outermost run
end its whole group when its own command ends, however it ended. With no
marker left, nothing is swept, so a run's group is left as a run outside any
other leaves it. Without a live run around it — `pkit` run from a shell,
whatever variables the shell holds — a run is outermost.

**The clock.** The deadline crosses processes, so it is written on the wall
clock (seconds since the epoch): a monotonic clock has no reference point two
processes can share portably. Each run's own bound is measured on the
monotonic clock. A clock step — a time synchronisation, the machine sleeping —
between a run and one nested under it shifts the nested bound by the step,
never beyond `COMMAND_TIMEOUT_SECONDS`; the outermost kill is never late.

**Policies stay with their callers** — one mechanism, a policy per kind:

- the *predicate* policy (`process.PredicateRunner`): the subject and `--json`
  as arguments, the caller's environment unchanged but for the run's deadline
  — a predicate may reach the network — and the payload read by the gate;
  anything but an answered JSON object is indeterminate, fail-closed;
- the *query* policy (`validators.run_query`, ADR-057 point 3, ADR-058): the
  leaf must declare the query contract, `--json` as the one argument, the
  offline marker set, the base override removed (`validators.QUERY_DROPPED_ENV`) —
  a query answers about state, never about a base named for one run (COR-052
  point 6) — and the answer validated against the shape asked for; anything
  else is no answer, an error finding;
- the *context-read* policy (`report_context.pm_workstream`, ADR-050): no
  arguments, the caller's environment unchanged but for the run's deadline —
  the verb asks the tracker — and the value read as the text an exit-0 run
  prints, not a JSON document; anything else omits the workstream from the
  report — silently where the verb is absent or printed nothing, with a
  warning naming how the run ended and what the verb said where it failed;
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
import re
import shutil
import signal
import subprocess
import tempfile
import time
import unicodedata
from collections.abc import Collection, Mapping, Sequence
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
# command starts must have ended — a command may read it; and the directory the
# outermost run made for the markers of the runs nested under it, which only
# exists while that run's command runs — the runner's own. The margin is what
# each command keeps of its bound to answer after something it started ran out
# of time.
DEADLINE_ENV = "PKIT_COMMAND_DEADLINE"
STRAYS_ENV = "PKIT_COMMAND_STRAYS"
ANSWER_MARGIN_SECONDS = 2

# The detail of a nested run that had no time left to start its command.
NO_TIME_LEFT = "no time was left of the bound of the run that started it"

# What a no-answer shows of a command's standard error (the module docstring):
# at most this many of its last non-blank lines, and at most this many bytes of
# them, encoded as UTF-8. Enough for a refusal's hint or a traceback's last
# frames; little enough that several failing commands stay readable together.
DIAGNOSTIC_TAIL_LINES = 10
DIAGNOSTIC_TAIL_BYTES = 1500

# Marks a tail that lost its beginning to either bound.
_TRUNCATED = "…"

# A terminal escape sequence: a control sequence (colours, cursor moves,
# erasing), a string sequence ended by BEL or ST (window titles, hyperlinks),
# or any other escape. Removed whole, so its parameters do not show as text.
_ESCAPE_SEQUENCE = re.compile(
    r"\x1b(?:\[[0-?]*[ -/]*[@-~]|[\]PX^_][^\x07\x1b]*(?:\x07|\x1b\\)|[ -/]*[0-~])"
)

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

    @property
    def clipped(self) -> bool:
        """Whether the run gave no answer for want of the time its caller had
        left rather than of its own bound: a nested run that timed out under
        less than `COMMAND_TIMEOUT_SECONDS`, or had no time left to start. A
        caller with more time might have had an answer."""
        if self.ending is Ending.NOT_STARTED:
            return self.detail == NO_TIME_LEFT
        return self.ending is Ending.TIMED_OUT and self.bound_seconds < COMMAND_TIMEOUT_SECONDS

    @property
    def bound_described(self) -> str:
        """The bound as a message names it: `30 s`, or `the 0.4 s its caller had
        left` when the run was clipped."""
        if self.clipped:
            return f"the {self.bound_seconds} s its caller had left"
        return f"{self.bound_seconds} s"

    @property
    def ending_described(self) -> str:
        """How the run ended, as a message names it after the command's name:
        `exited 2`, `did not answer within 30 s`, `could not start: …`. A
        caller reads an answer through its own policy; this names the ending
        it saw when there was none."""
        if self.ending is Ending.NOT_STARTED:
            return f"could not start: {self.detail}"
        if self.ending is Ending.TIMED_OUT:
            return f"did not answer within {self.bound_described} and was stopped"
        if self.ending is Ending.ABNORMAL_EXIT:
            if self.returncode is not None and self.returncode < 0:
                return f"was ended by signal {-self.returncode}"
            return f"exited {self.returncode}"
        if self.ending is Ending.UNPARSABLE:
            return self.detail or "printed no JSON document on its standard output"
        return "answered"

    @property
    def stderr_tail(self) -> str:
        """What the command said on standard error, fit to be shown
        (`diagnostic_tail`) — "" when it said nothing, or nothing was read (a
        run stopped at its bound has its pipes closed unread)."""
        return diagnostic_tail(self.stderr)


def diagnostic_tail(text: str) -> str:
    """The end of a command's diagnostic output, fit to be shown to the operator.

    Terminal escape sequences are removed whole and every other control or
    format character dropped (a tab becomes a space), so the text cannot move
    the cursor, recolour, retitle or otherwise rewrite the terminal it is shown
    on. Then only the last `DIAGNOSTIC_TAIL_LINES` non-blank lines are kept, and
    of those only the last `DIAGNOSTIC_TAIL_BYTES` bytes; a tail that lost its
    beginning to either bound starts with `…`. The text is already decoded with
    replacement (`run_command`), so no byte the command wrote can fail here."""
    lines: list[str] = []
    for raw_line in _ESCAPE_SEQUENCE.sub("", text).splitlines():
        line = "".join(
            " " if char == "\t" else char
            for char in raw_line
            if char == "\t" or unicodedata.category(char) not in ("Cc", "Cf")
        ).rstrip()
        if line.strip():
            lines.append(line)
    truncated = len(lines) > DIAGNOSTIC_TAIL_LINES
    tail = "\n".join(lines[-DIAGNOSTIC_TAIL_LINES:])
    encoded = tail.encode("utf-8")
    if len(encoded) > DIAGNOSTIC_TAIL_BYTES:
        room = DIAGNOSTIC_TAIL_BYTES - len(_TRUNCATED.encode("utf-8"))
        # A cut through a multi-byte character drops what is left of it.
        tail = encoded[-room:].decode("utf-8", errors="ignore")
        truncated = True
    return f"{_TRUNCATED}{tail}" if truncated else tail


def run_command(
    script: Path,
    args: Sequence[str],
    *,
    cwd: Path,
    extra_env: Mapping[str, str] | None = None,
    drop_env: Collection[str] = (),
) -> CommandRun:
    """Run `script` with `args` from `cwd`, in its own process group, bounded by
    `COMMAND_TIMEOUT_SECONDS`, and read its answer. `extra_env` is laid over
    the caller's environment, then each variable `drop_env` names is removed —
    whether the caller's or `extra_env`'s — and the run's deadline is laid over
    what remains. Standard output is the answer and nothing else; standard
    error is diagnostics.

    Inside a live run (`inherited_deadline`) the run is nested (the module
    docstring): bounded by the time remaining, in the outermost run's process
    group. With no time remaining its command is not started."""
    inherited = inherited_deadline()
    now = time.time()
    bound = COMMAND_TIMEOUT_SECONDS if inherited is None else _remaining(inherited, now)
    if bound <= 0:
        return CommandRun(Ending.NOT_STARTED, 0, detail=NO_TIME_LEFT)
    tree = _Tree.nested() if inherited is not None else _Tree.outermost()
    env = {**os.environ, **(extra_env or {})}
    for name in drop_env:
        env.pop(name, None)
    env[DEADLINE_ENV] = _written_deadline(now + bound - ANSWER_MARGIN_SECONDS)
    env.pop(STRAYS_ENV, None)  # only a live run's directory is passed on
    if tree.strays:
        env[STRAYS_ENV] = tree.strays
    try:
        process = subprocess.Popen(
            [str(script), *args],
            cwd=str(cwd),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=not tree.is_nested,
        )
    except OSError as exc:
        tree.leave(None, ended=True)
        return CommandRun(Ending.NOT_STARTED, bound, detail=str(exc))
    ended = False
    try:
        raw_stdout, raw_stderr = process.communicate(timeout=bound)
        ended = True
    except subprocess.TimeoutExpired:
        tree.stop(process)
        return CommandRun(Ending.TIMED_OUT, bound)
    except BaseException:
        tree.stop(process)
        raise
    finally:
        tree.leave(process, ended=ended)
    stderr = _decode(raw_stderr)
    try:
        stdout = (raw_stdout or b"").decode("utf-8")
    except UnicodeDecodeError as exc:
        # Standard output is the answer; a byte the encoding cannot read is no
        # answer, never a repaired one (a replacement inside a JSON string would
        # still parse and open a gate). Diagnostics on stderr are only shown.
        return CommandRun(
            Ending.UNPARSABLE,
            bound,
            returncode=process.returncode,
            stdout=_decode(raw_stdout),
            stderr=stderr,
            detail=f"standard output is not UTF-8: {exc}",
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


def inherited_deadline() -> float | None:
    """The deadline of the live run this process runs inside, or None outside one.

    A run is live to this process when three things hold: the environment
    carries a deadline that is a number, as a run writes it; the process is in
    the process group that leads its session, as every process the outermost
    run's command starts is — that command leads a session of its own — and a
    command started from a terminal is not; and the directory the outermost run
    named in `STRAYS_ENV` exists, which it does only while that run's command
    runs. So a variable left over in a shell, or outliving its run, never makes
    a run nested, nor makes a process a reader of another run's cache
    (`run_cache`)."""
    raw = os.environ.get(DEADLINE_ENV)
    if raw is None:
        return None
    try:
        deadline = float(raw)
    except ValueError:
        return None
    if not math.isfinite(deadline) or not _in_a_live_run():
        return None
    return deadline


def _in_a_live_run() -> bool:
    """The last two conditions of `inherited_deadline`."""
    strays = os.environ.get(STRAYS_ENV, "")
    if not strays or not hasattr(os, "getsid"):  # no sessions on this platform: never nested
        return False
    return os.getpgrp() == os.getsid(0) and os.path.isdir(strays)


def _remaining(deadline: float, now: float) -> float:
    """A nested run's bound: the time left until the inherited deadline, rounded
    down to a tenth of a second — so its own deadline never falls after its
    caller's — and never more than a run's own bound."""
    return min(COMMAND_TIMEOUT_SECONDS, math.floor((deadline - now) * 10) / 10)


def _written_deadline(deadline: float) -> str:
    """A deadline as the environment carries it: seconds since the epoch to the
    millisecond, rounded down, so the written deadline is never later than the
    run's."""
    return f"{math.floor(deadline * 1000) / 1000:.3f}"


@dataclass(frozen=True)
class _Tree:
    """Where one run stands in the tree of runs, and what it keeps there.

    The outermost run makes the strays directory and owns the group its command
    leads; a nested run keeps a marker in the directory it inherited while its
    command runs. Either may be missing: a directory that could not be made —
    the runs under it then run as runs of their own — or a marker that could
    not be written, which leaves what an overrun command started to the
    outermost kill alone (`_kill_command`)."""

    is_nested: bool
    strays: str
    marker: str = ""

    @classmethod
    def outermost(cls) -> _Tree:
        try:
            return cls(False, tempfile.mkdtemp(prefix="pkit-strays-"))
        except OSError:
            return cls(False, "")

    @classmethod
    def nested(cls) -> _Tree:
        strays = os.environ.get(STRAYS_ENV, "")
        if not strays:
            return cls(True, "")
        try:
            handle, marker = tempfile.mkstemp(dir=strays, prefix="run-")
        except OSError:
            return cls(True, strays)
        os.close(handle)
        return cls(True, strays, marker)

    def stop(self, process: subprocess.Popen[bytes]) -> None:
        """End a command that overran or was interrupted: the outermost run's
        whole group; a nested run's command alone, its marker left behind."""
        if self.is_nested:
            _kill_command(process)
        else:
            _kill_process_group(process)

    def leave(self, process: subprocess.Popen[bytes] | None, *, ended: bool) -> None:
        """After the command — `ended` when it ended by itself, or never started.
        A nested run removes its marker then, and only then. The outermost run,
        when its command ended by itself and a marker remains — a run under it
        did not end cleanly — ends what is left of its group (on a timeout or an
        interrupt it has just killed the group); then it removes the directory."""
        if self.is_nested:
            if ended and self.marker:
                with contextlib.suppress(OSError):
                    os.unlink(self.marker)
            return
        if not self.strays:
            return
        if ended and process is not None and _marked(self.strays):
            _sweep(process)
        shutil.rmtree(self.strays, ignore_errors=True)


def _marked(strays: str) -> bool:
    """Whether a run nested under the outermost one left its marker behind."""
    try:
        with os.scandir(strays) as entries:
            return any(True for _ in entries)
    except OSError:
        return False


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


def _kill_command(process: subprocess.Popen[bytes]) -> None:
    """End a nested run's command. Its group is the outermost run's too, so a
    signal to the group would end its callers: the command alone is killed,
    its pipes closed unread as for a group. What it started may still run — a
    `uv run --script` shebang's interpreter, a `pkit` reading command — in that
    group, and the marker the nested run leaves behind makes the outermost run
    end it when its own command ends. Without a marker — none could be
    written — only the outermost kill, at its deadline or on an interrupt,
    reaches it: an outermost command that answers in time leaves it running."""
    process.kill()
    process.wait()
    _close_pipes(process)


def _sweep(process: subprocess.Popen[bytes]) -> None:
    """End what is left of the group the outermost run's command led, after
    that command ended by itself and a run nested under it did not.

    The command has been reaped, and the group is signalled by its id, the
    command's pid. While any member of the group lives, that id cannot be given
    to another process — the system never reuses a process group's id until
    the group is gone — so the signal reaches the group and nothing else. Once
    the last member has ended the id is free; the signal follows the command's
    end at once, and could reach another group only if the system handed that
    very id to a new group leader in between — the window every signal sent by
    id carries. A group already gone, or an id now another user's, is left
    alone."""
    if hasattr(os, "killpg"):  # without process groups, no run is ever nested
        with contextlib.suppress(ProcessLookupError, PermissionError):
            os.killpg(process.pid, signal.SIGKILL)


def _close_pipes(process: subprocess.Popen[bytes]) -> None:
    for stream in (process.stdout, process.stderr):
        if stream is not None:
            stream.close()


def _decode(data: bytes | None) -> str:
    """Diagnostic output as text; a byte the encoding cannot read is replaced,
    never a crash. Standard output — the answer — is decoded strictly in
    `run_command`, where an undecodable byte ends the run as UNPARSABLE."""
    return (data or b"").decode("utf-8", errors="replace")
