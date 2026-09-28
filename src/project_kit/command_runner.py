"""One primitive for the commands a component registers (ADR-057 point 5).

A capability or an adapter registers what the backbone can run in one place:
the `commands:` tree of its package metadata (COR-021). A key is a token; a
value carrying `script` is a leaf; any other mapping is a group of further
tokens. Two halves live here, and every reader of that tree goes through them.

**The lookup.** `command_leaves` is the one walk of the tree, and
`registered_commands` reads a component's package file through it; a reference
— a path through the tree, tokens separated by spaces (`create page`) — names
a leaf through `resolve_command`. The dispatcher (`pkit <capability> <command>`),
package validation, the validator registry and the process engine's predicate
runner all read the tree this way, so what counts as a leaf, and where its
script is, is decided once.

**The run.** `run_command` starts a leaf's script with an explicit argument
list from a working directory, in its own process group, bounded by
`COMMAND_TIMEOUT_SECONDS`; it captures standard output and standard error and
parses standard output as one JSON document. Exceeding the bound kills the
whole process group — a script with a `uv run --script` shebang starts its
interpreter as a grandchild, which killing the child alone would leave running
with the pipes open. The run never outlives its caller: an interrupt kills the
group too. `CommandRun` says how the run ended; it never raises for what the
command did.

**Policies stay with their callers** — one mechanism, a policy per kind:

- the *predicate* policy (`process.PredicateRunner`): the subject and `--json`
  as arguments, the caller's environment unchanged — a predicate may reach the
  network — and the payload read by the gate; anything but an answered JSON
  object is indeterminate, fail-closed;
- the *query* policy (`validators.run_query`, ADR-057 point 3, ADR-058): the
  leaf must declare the query contract, `--json` as the one argument, the
  offline marker set, and the answer validated against the shape asked for;
  anything else is no answer, an error finding;
- a *subscriber* policy joins when events run subscribers (COR-053 point 9
  sets its limits; point 11 asks the kinds to share one command runner).

The dispatcher's proxy — `pkit <capability> <command>` run by a person — uses
the lookup and not the run: it inherits the terminal's streams and is not
bounded.
"""

from __future__ import annotations

import contextlib
import json
import os
import signal
import subprocess
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
    NOT_STARTED = "not-started"  # could not be started (`detail`)


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
    standard error is diagnostics."""
    bound = COMMAND_TIMEOUT_SECONDS
    try:
        process = subprocess.Popen(
            [str(script), *args],
            cwd=str(cwd),
            env={**os.environ, **extra_env} if extra_env else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
    except OSError as exc:
        return CommandRun(Ending.NOT_STARTED, bound, detail=str(exc))
    try:
        raw_stdout, raw_stderr = process.communicate(timeout=bound)
    except subprocess.TimeoutExpired:
        _kill_process_group(process)
        return CommandRun(Ending.TIMED_OUT, bound)
    except BaseException:
        _kill_process_group(process)
        raise
    stdout, stderr = _decode(raw_stdout), _decode(raw_stderr)
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
    for stream in (process.stdout, process.stderr):
        if stream is not None:
            stream.close()


def _decode(data: bytes | None) -> str:
    """A command's output as text; a byte the encoding cannot read is replaced,
    never a crash — the output then fails to parse, and the policy says what
    that means."""
    return (data or b"").decode("utf-8", errors="replace")
