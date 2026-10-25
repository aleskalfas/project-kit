"""A person's authorisation of a step that is theirs, asked only at a terminal (#2015).

A record gives some steps to a person: a close, or a change to the project's own
configuration. A verb that takes such a step goes on with `--yes`, or with a yes
the person types at a terminal. Off a terminal, without `--yes`, nobody is there
to ask, so the verb refuses before it changes anything. The refusal names the
command that carries the authorisation. An answer piped into standard input is
never read: `echo y | pkit pm …` is no person, as the backbone's commands hold
(#2003).

- `authorise(question, yes=, step=, verb=)` asks, refuses or lets the run go on;
- `refuse(step, verb)` is the refusal alone, for a verb that asks its own question;
- `at_a_terminal()` is the test both use.
"""

from __future__ import annotations

import shlex
import sys

#: The exit code of a step refused off a terminal.
REFUSED = 1


def at_a_terminal() -> bool:
    """Whether standard input is a terminal a person types at. An absent or closed
    stream is not, nor is a stand-in with no `isatty`."""
    stdin = sys.stdin
    if stdin is None:
        return False
    try:
        return bool(stdin.isatty())
    except (AttributeError, ValueError, OSError):  # ValueError: I/O on a closed file
        return False


def rerun_with_yes(verb: str) -> str:
    """This run's command, through the dispatcher, with `--yes` added."""
    return shlex.join(["pkit", "pm", verb, *sys.argv[1:], "--yes"])


def refuse(step: str, verb: str) -> int:
    """Say that `step` is the person's and that no terminal is here to ask them.

    Returns `REFUSED`, the exit code to stop with. `step` names what was not
    done, as a sentence's subject: "Closing milestone #6".
    """
    print(
        f"[refused] {step} is the person's to authorise, and no terminal is here to "
        "ask them. Nothing was changed.\n"
        f"  → on their authorisation, run:\n    {rerun_with_yes(verb)}",
        file=sys.stderr,
    )
    return REFUSED


def authorise(question: str, *, yes: bool, step: str, verb: str) -> int | None:
    """Ask the person at the terminal to authorise `step`.

    Returns None to go on: `--yes` was given, or the person answered yes. Else
    returns the exit code to stop with: `REFUSED` off a terminal, where nothing
    is read, and 0 where the person declined at the prompt.
    """
    if yes:
        return None
    if not at_a_terminal():
        return refuse(step, verb)
    try:
        reply = input(question).strip().lower()
    except EOFError:
        reply = ""
    if reply in ("y", "yes"):
        return None
    print("aborted.", file=sys.stderr)
    return 0
