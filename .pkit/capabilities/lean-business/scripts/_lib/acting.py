"""How a command writes, acts and moves (lean-business DEC-001 point 3; DEC-002 points 1, 2
and 14; DEC-003 points 1 and 5; the process area's README, "Seam-ordering contract").

**Content, an act, a move.** A command writes content, such as a canvas's entry, or records
an act of the person's, such as a verdict, which may take a move of a process. Each write
goes through `writes`: built, held to the check and the data validation, then written. The
ways a command meets the engine:

- **Content** (`content`): no question, and no record of who or when, since content is no
  judgement.
- **An act with no move** (`act`): the person's consent first, then the write.
- **The person's move** (`person_move`), with one target or two, and whether or not the
  write is what lets its gate through: the order is the engine's seam. The command reads
  where the subject stands (`position`) and checks its input against the predicate it
  shares with the check. It asks the engine whether a move its trigger declares from there
  may be taken (`can-move`), and refuses where none may. It never chooses the target
  before the write: after it, it reads where the subject stands from the engine and moves
  there, naming the origin it read before (`move --from`). Where the engine refuses, the
  write is undone.
- **An act followed by the script's move** (`act_then_moved`): the person's act is written,
  and the move the data then makes, such as a cycle into suspended, is taken from the
  origin read before, with no `can-move` first, since its gate is closed until the write.
  Where the engine places the subject in none of its states after the write, the act
  stands, since it is the person's whatever the engine reads, and the command says that the
  move waits; a person's move undoes its write instead, since the move is the act.

**The consent forms** (`consent`; DEC-003 point 5; COR-048 point 5). An act or a move of
the person's is taken only on the person's word: given by `--person-decided`, which an
agent passes only once the person answered in the session; or at a terminal, by a yes to
the question; and with neither, nothing is done and the question is printed (`Asked`). A
move's question is its definition's prompt, and an act with no move asks in the
capability's own words.

**The day and who.** The day a command acts on is today, read once by the command's script
where it starts and handed to `main`, never read from its arguments or the environment
(DEC-003 point 1); no module here reads the clock. Who acted is git's `user.name`, never
the address. A test gives the context its own day, engine and person.

**What is said.** A write says what it did first, then the location it recorded, each
judgement it leaves stale, read before anything is written, each warning it adds, and each
error already in the files, which it left as it was.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import TextIO

from _lib import staling, writes
from _lib.engine import Engine, EngineFailed, PkitEngine, Status
from _lib.findings import Finding
from _lib.root import CONFIG, project_root
from _lib.writes import Files, Held, Refused

#: The exit codes every command shares.
DONE = 0
REFUSED = 1
USAGE = 2
ASKED = 3

#: The flag by which an agent says the person decided, once they answered in the session.
PERSON_DECIDED = "--person-decided"


class Asked(Exception):
    """Nobody could be asked, and nothing says the person decided: the question, printed,
    and nothing done."""

    def __init__(self, question: str) -> None:
        super().__init__(question)
        self.question = question


@dataclass
class Context:
    """What a command runs with: the project, the day it acts on, the engine, whether a person
    sits at the terminal and how they are asked, where it prints, and who acts."""

    root: Path
    on: date
    engine: Engine
    terminal: bool
    ask: Callable[[str], bool]
    out: TextIO
    err: TextIO
    whom: Callable[[], str | None]
    _who: str | None = field(default=None, init=False)

    @property
    def who(self) -> str:
        """Who acts: git's `user.name`. Raises Refused where none is set, since an act
        records who made it (DEC-002 point 2)."""
        if self._who is None:
            name = self.whom()
            if not name or not name.strip():
                raise Refused(
                    "an act records who made it, and git names nobody: set git's user.name, "
                    "`git config user.name <your name>`"
                )
            self._who = name.strip()
        return self._who

    def say(self, line: str = "") -> None:
        print(line, file=self.out)


def git_user(root: Path) -> str | None:
    """Git's `user.name` for the project at `root`, or None."""
    try:
        done = subprocess.run(
            ["git", "config", "user.name"], cwd=root, capture_output=True, text=True, check=False
        )
    except OSError:
        return None
    if done.returncode != 0:
        return None
    return done.stdout.strip() or None


def _ask_at_terminal(question: str) -> bool:
    answer = input(f"{question} [y/N] ")
    return answer.strip().lower() in ("y", "yes")


def real_context(on: date) -> Context:
    """The context a command runs in: the project it is installed in, the day `on` its script
    read where it started, the engine itself, and git's user."""
    root = project_root()
    stdin = sys.stdin
    terminal = bool(stdin is not None and _isatty(stdin))
    return Context(
        root=root,
        on=on,
        engine=PkitEngine(root),
        terminal=terminal,
        ask=_ask_at_terminal,
        out=sys.stdout,
        err=sys.stderr,
        whom=lambda: git_user(root),
    )


def _isatty(stream: TextIO) -> bool:
    try:
        return stream.isatty()
    except (AttributeError, ValueError, OSError):
        return False


# --- running a command -----------------------------------------------------------------------


Run = Callable[[argparse.Namespace, Context], None]


def invoke(parser: argparse.ArgumentParser, run: Run, argv: Sequence[str], ctx: Context) -> int:
    """Run the command `run` with `argv`, as `parser` reads it, in `ctx`; its exit code."""
    args = parser.parse_args(list(argv))
    try:
        run(args, ctx)
    except Asked as exc:
        print(exc.question, file=ctx.out)
        print(
            f"Nothing was done: the person's word is needed. At a terminal the command asks "
            f"it; an agent passes {PERSON_DECIDED} only once the person answered.",
            file=ctx.err,
        )
        return ASKED
    except Refused as exc:
        print(f"{parser.prog}: refused: {exc}", file=ctx.err)
        return REFUSED
    except EngineFailed as exc:
        print(f"{parser.prog}: the process engine gave no answer: {exc}", file=ctx.err)
        return REFUSED
    return DONE


def main(parser: argparse.ArgumentParser, run: Run, on: date) -> int:
    """A command's entry, as `pkit` starts it, acting on the day `on`."""
    return invoke(parser, run, sys.argv[1:], real_context(on))


def person_decided(parser: argparse.ArgumentParser) -> None:
    """Add the flag by which an agent says the person decided."""
    parser.add_argument(
        PERSON_DECIDED,
        dest="person_decided",
        action="store_true",
        help="The person decided, in the session: an agent passes it only once the person "
        "answered the question the command asks.",
    )


# --- the consent forms ----------------------------------------------------------------------


def consent(ctx: Context, question: str, decided: bool) -> None:
    """Hold an act to the person (DEC-003 point 5): go on where `decided` says the person
    decided, or where the person at the terminal answers yes. Raises Refused on a no, and
    Asked where nobody can be asked."""
    if decided:
        return
    if not ctx.terminal:
        raise Asked(question)
    if not ctx.ask(question):
        raise Refused("you answered no, so nothing was written")


# --- the ways a command meets the engine ---------------------------------------------------


def position(ctx: Context, process: str, subject: str) -> Status:
    """Where `subject` stands in `process`, from the engine. Raises Refused where the engine
    cannot tell."""
    found = ctx.engine.status(process, subject)
    if found.indeterminate:
        why = f": {found.why}" if found.why else ""
        raise Refused(f"the process engine cannot tell where `{subject}` stands{why}")
    return found


def content(ctx: Context, files: Files, done: str) -> None:
    """Write content: held, then written, with no question and no record of who or when.
    `done` says what was written."""
    prepared = _held(files)
    writes.commit(ctx.root, files.written())
    report(ctx, files, prepared, [done])


def act(ctx: Context, files: Files, done: str, *, question: str, decided: bool) -> None:
    """Record an act of the person's that takes no move: held, asked, then written. `done`
    says what was recorded."""
    prepared = _held(files)
    consent(ctx, question, decided)
    writes.commit(ctx.root, files.written())
    report(ctx, files, prepared, [done])


def person_move(
    ctx: Context,
    process: str,
    subject: str,
    trigger: str,
    before: Status,
    build: Callable[[], tuple[Files, str]],
    *,
    decided: bool,
) -> str:
    """Take the person's move on `trigger` from where `before` places `subject`: refused
    where no move the trigger declares from there may be taken; else the write `build`
    gives, with what it says was written, held, asked and written; then the move to where
    the engine places the subject after it, from the origin `before` read. Returns the
    state it moved to."""
    origin = before.state
    declared = before.by(trigger)
    if origin is None or not declared:
        raise Refused(
            f"`{subject}` stands {_where(origin)}, and no move on `{trigger}` leaves there"
        )
    actor = ctx.who
    asked = [(move, ctx.engine.can_move(process, subject, move.to, actor)) for move in declared]
    opened = [move for move, verdict in asked if verdict.ok]
    if not opened:
        why = "; ".join(f"to {move.to}: {verdict.reason}" for move, verdict in asked)
        raise Refused(f"the process engine refuses `{trigger}` for `{subject}`: {why}")
    files, done = build()
    prepared = _held(files)
    consent(ctx, opened[0].prompt or f"Take `{trigger}` for `{subject}`?", decided)
    undo = writes.commit(ctx.root, files.written())
    after = _after(ctx, process, subject, undo)
    if after.state not in [move.to for move in declared]:
        raise _undone(
            undo,
            f"after the write `{subject}` stands {_where(after.state)}, where `{trigger}` "
            f"does not lead from {origin}",
        )
    moved = _move(ctx, process, subject, after.state, origin, actor, undo)
    report(ctx, files, prepared, [done, f"`{subject}` moved from {origin} to {moved}."])
    return moved


def act_then_moved(
    ctx: Context,
    process: str,
    subject: str,
    before: Status,
    files: Files,
    done: str,
    *,
    question: str,
    decided: bool,
) -> str | None:
    """Record an act of the person's whose effect the script's move then takes, such as a
    suspension: held, asked and written; then, where the engine places `subject` elsewhere
    than `before` did, the move there from the origin it read, with no `can-move` first.
    Where it places `subject` in none of its states, the act stands and the move waits.
    `done` says what was recorded. Returns the state it moved to, or None where nothing
    moved."""
    origin = before.state
    prepared = _held(files)
    consent(ctx, question, decided)
    actor = ctx.who
    undo = writes.commit(ctx.root, files.written())
    after = _after(ctx, process, subject, undo)
    if origin is not None and after.state is None:
        waits = (
            f"After the write the process engine places `{subject}` in none of its states, so "
            f"its move from {origin} waits until the engine places it in one; `pkit lean "
            f"check` names what the files hold."
        )
        report(ctx, files, prepared, [done, waits])
        return None
    if origin is None or after.state is None or after.state == origin:
        report(ctx, files, prepared, [done])
        return None
    moved = _move(ctx, process, subject, after.state, origin, actor, undo)
    report(ctx, files, prepared, [done, f"`{subject}` moved from {origin} to {moved}."])
    return moved


def _after(ctx: Context, process: str, subject: str, undo: writes.Undo) -> Status:
    """Where the engine places `subject` after the write; the write undone where it gives no
    answer or cannot tell."""
    try:
        after = ctx.engine.status(process, subject)
    except EngineFailed as exc:
        raise _undone(undo, f"after the write the process engine gave no answer: {exc}") from exc
    if after.indeterminate:
        raise _undone(undo, f"after the write the engine cannot tell where `{subject}` stands")
    return after


def _move(
    ctx: Context,
    process: str,
    subject: str,
    to: str | None,
    origin: str,
    actor: str,
    undo: writes.Undo,
) -> str:
    """The engine's move of `subject` from `origin` to `to`; the write undone where the
    engine refuses it, or gives no answer."""
    if to is None:
        raise _undone(undo, f"after the write `{subject}` stands in none of its states")
    try:
        verdict = ctx.engine.move(process, subject, to, origin, actor)
    except EngineFailed as exc:
        raise _undone(
            undo, f"the process engine gave no answer to the move to {to}: {exc}"
        ) from exc
    if not verdict.ok:
        raise _undone(undo, f"the process engine refused the move to {to}: {verdict.reason}")
    return to


def _where(state: str | None) -> str:
    return f"in {state}" if state is not None else "in none of its states"


def _undone(undo: writes.Undo, why: str) -> Refused:
    """Take the write back, and the refusal that says why."""
    left = undo()
    unrestored = f"; these could not be put back: {', '.join(left)}" if left else ""
    return Refused(f"{why}, so the write was undone{unrestored}")


# --- held, and what is said ----------------------------------------------------------------


@dataclass(frozen=True)
class Prepared:
    """What holding a write found, and the judgements it leaves stale, both read before
    anything is written."""

    held: Held
    stale: tuple[staling.Stale, ...]


def _held(files: Files) -> Prepared:
    """`writes.hold`, refused where the write adds an error, and what the write leaves
    stale, read from the files as they stand."""
    held = writes.hold(files)
    if held.added:
        named = "\n".join(_finding(f) for f in held.added)
        raise Refused(f"the write would add {_count(len(held.added), 'error')}:\n{named}")
    return Prepared(held, tuple(staling.stale(files)))


def report(ctx: Context, files: Files, prepared: Prepared, done: Sequence[str]) -> None:
    """What a write leaves to say: what it did, the location it recorded, the judgements its
    change leaves stale, the warnings it adds and the errors already in the files."""
    for line in done:
        ctx.say(line)
    if files.target.record:
        ctx.say(
            f"Recorded where the ideas live, `{files.location}/`, in `{CONFIG}`. To keep them "
            f"elsewhere, move the folder and change its `location:` line."
        )
    for stale in prepared.stale:
        ctx.say(f"{'WARNING' if stale.loud else 'warning'}: {stale.line}")
    held = prepared.held
    for finding in held.warnings:
        if finding.label != staling.LABEL:
            ctx.say(_finding(finding))
    if held.standing:
        ctx.say(
            f"Already in the files, and left as they were: "
            f"{_count(len(held.standing), 'error')}, `pkit lean check` names "
            f"{'it' if len(held.standing) == 1 else 'them'}:"
        )
        for finding in held.standing:
            ctx.say(_finding(finding))


def _finding(finding: Finding) -> str:
    """A finding, as the check prints one."""
    return f"  {finding.severity:<8}{finding.location}  [{finding.label}]\n    {finding.message}"


def _count(count: int, word: str) -> str:
    return f"{count} {word}" if count == 1 else f"{count} {word}s"
