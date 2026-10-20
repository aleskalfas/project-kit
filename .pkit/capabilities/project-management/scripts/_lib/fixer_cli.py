"""Shared CLI driver for the fixer verbs that write the grant list (DEC-056 point 2).

`grant-fixer` and `revoke-fixer` differ only in the answer they record:
`grant-fixer` records yes for an agent's types, and `revoke-fixer` records no, a
refusal. The argument grammar, the reading of the point and the grant list, the
foreign-repository guard and the write live here once, so each script stays a
thin entry point. `ask-fixers` asks the question, through `ask_pending`, which
the drift command calls too.

- **grant-fixer <agent> [--type <type>]...** grants the agent every type the
  point gives it, or only the types named. It refuses an agent no entry names,
  and a type the point does not give that agent, so a grant never names what
  nothing declares. An entry that fails a check is granted all the same and
  noted: it starts no agent until it is mended.
- **revoke-fixer <agent> [--type <type>]...** refuses the agent every type the
  point gives it and every type it is granted, or only the types named. It works
  while the point does not resolve, on the grant list alone, since a grant
  validation reports must stay revocable.
- **--dry-run**, on either, says what would be written and writes nothing. It
  refuses where the configuration does not exist, as the write does.

- **ask-fixers** asks one question for each agent about the types nobody was
  asked about, where a person can answer: at a terminal, both standard input
  and standard output. Each answer is recorded as it is given, a yes as a grant
  and a no as a refusal. With nobody to ask, nothing is granted or recorded,
  and each question is printed with the one command line that grants its
  fixer. Running it is never the consent: only the answer is.

Running grant or revoke is the person's own answer (DEC-056 point 2). Each
change shows in the project's diff, and counts once it merges into the default
branch.
"""

from __future__ import annotations

import argparse
import contextlib
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import TextIO

from _lib import fixers, session_guard
from _lib.membership import CAPABILITY_NAME, resolve_capability_root

try:  # Only where a terminal's pending input can be dropped.
    import termios
except ImportError:  # pragma: no cover — no such module off POSIX
    termios = None  # type: ignore[assignment]


def run_answer_verb(*, verb: str, answer: str, argv: Sequence[str] | None = None) -> int:
    """Parse the verb's arguments and record `answer` for the agent's types.

    Exit codes: 0 recorded, or nothing to change; 1 refused, nothing written;
    2 usage error, or the capability is not found."""
    granting = answer == fixers.GRANTED
    parser = argparse.ArgumentParser(
        prog=f"{fixers.COMMAND} {verb}",
        description=(
            (
                "Grant a fixer: let the agent start on its own on the stale artefacts of "
                "its types (DEC-056 point 2). Running it is your answer yes."
            )
            if granting
            else (
                "Revoke a fixer: record a refusal for the agent's types, so it starts on none "
                "of them (DEC-056 point 2)."
            )
        ),
    )
    parser.add_argument("agent", help="The fixer's agent, as `list-fixers` names it.")
    parser.add_argument(
        "--type",
        dest="types",
        action="append",
        default=[],
        metavar="TYPE",
        help=(
            "Only this artefact type (repeatable). Default: every type the point gives the "
            "agent" + ("." if granting else ", and every type it is granted.")
        ),
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Say what would be written, and write nothing."
    )
    parser.add_argument(
        "--capability-root",
        type=Path,
        default=None,
        help=f"Default: <repo-root>/.pkit/capabilities/{CAPABILITY_NAME}/.",
    )
    session_guard.add_override_argument(parser)
    args = parser.parse_args(argv)

    if not fixers.AGENT_NAME.fullmatch(args.agent):
        parser.error(f"{args.agent!r} is not an agent's name")
    for artefact_type in args.types:
        if not fixers.TYPE_NAME.fullmatch(artefact_type):
            parser.error(f"{artefact_type!r} is not an artefact type's name")
    capability_root = resolve_capability_root(args.capability_root)
    if capability_root is None:
        print(f"error: {CAPABILITY_NAME} capability not found.", file=sys.stderr)
        return 2
    repo_root = capability_root.parents[2]
    config_path = capability_root / fixers.CONFIG_RELATIVE
    shown = (
        config_path.relative_to(repo_root) if config_path.is_relative_to(repo_root) else config_path
    )

    try:
        answers = fixers.answers_of(fixers.load_config(config_path))
    except fixers.Malformed as exc:
        print(f"error: the grant list cannot be read: {exc}; fix it first.", file=sys.stderr)
        return 1
    try:
        point = fixers.read_point()
    except fixers.Unreadable as exc:
        point = fixers.Point(False, why=str(exc))

    if granting:
        chosen = _granted_types(point, args.agent, args.types)
    else:
        chosen = _revoked_types(point, answers, args.agent, args.types)
    if isinstance(chosen, str):
        print(f"error: {chosen}", file=sys.stderr)
        return 1
    if granting:
        _note_problems(point, repo_root, args.agent, chosen)

    unchanged = all(answers.of(args.agent, t) == answer for t in chosen)
    what = f"{args.agent} {'granted' if granting else 'refused'} {', '.join(chosen)}"
    if unchanged:
        print(f"Nothing to write: the grant list already has {what}.")
        return 0
    if args.dry_run:
        # The write refuses a configuration that does not exist, so the dry run
        # checks it too, and says so.
        missing = fixers.missing_config(config_path)
        if missing is not None:
            print(f"error: {missing}. Nothing was written (--dry-run).", file=sys.stderr)
            return 1
        print(f"Would record in {shown}, which exists: {what}. Nothing was written (--dry-run).")
        return 0
    if not session_guard.enforce(override=args.allow_foreign_repo):
        return 1
    try:
        fixers.record(config_path, args.agent, chosen, answer)
    except fixers.Refused as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"Recorded in {shown}: {what}.")
    if granting:
        entries = tuple(e for e in point.entries if e.agent == args.agent and e.type in chosen)
        question = fixers.Question(args.agent, entries, point.types_of(args.agent))
        print(f'It answers yes to: "{fixers.question_text(question)}"')
    print(
        "Commit it: the grant counts once this change merges into the default branch."
        if granting
        else "Commit it: the fixer stops starting on these types once this change merges "
        "into the default branch."
    )
    return 0


def _granted_types(point: fixers.Point, agent: str, named: list[str]) -> list[str] | str:
    """The types to grant, or why there are none."""
    if not point.resolved:
        detail = "".join(f"\n  inert: {line}" for line in point.inert)
        return (
            f"the {fixers.POINT} point does not resolve, so no fixer can be granted: "
            f"{point.why}{detail}"
        )
    given = point.types_of(agent)
    if not given:
        return (
            f"no entry of {fixers.POINT} names agent {agent}; "
            f"`{fixers.COMMAND} {fixers.LIST_VERB}` lists the fixers"
        )
    foreign = [t for t in named if t not in given]
    if foreign:
        return (
            f"the point does not give {agent} {', '.join(foreign)}; it gives it {', '.join(given)}"
        )
    return list(dict.fromkeys(named)) or list(given)


def _revoked_types(
    point: fixers.Point, answers: fixers.Answers, agent: str, named: list[str]
) -> list[str] | str:
    """The types to refuse, or why there are none. Without the point, the grant
    list's own types."""
    if named:
        return list(dict.fromkeys(named))
    if not point.resolved:
        print(
            f"note: the {fixers.POINT} point does not resolve ({point.why}), so only the types "
            f"the grant list grants {agent} are refused.",
            file=sys.stderr,
        )
    chosen = list(dict.fromkeys([*point.types_of(agent), *answers.granted(agent)]))
    if not chosen:
        return (
            f"nothing to revoke: no entry of {fixers.POINT} names agent {agent}, and the "
            "grant list grants it nothing"
        )
    return chosen


def _note_problems(point: fixers.Point, repo_root: Path, agent: str, chosen: list[str]) -> None:
    """Say which granted types still start no agent, and why."""
    for item in fixers.check(point, repo_root):
        if item.entry.agent != agent or item.entry.type not in chosen:
            continue
        for problem in item.problems:
            print(
                f"note: {item.entry.type} starts no agent until this is mended: {problem.text}.",
                file=sys.stderr,
            )


# --- the question ---------------------------------------------------------------------


def at_a_terminal(stdin: TextIO | None = None, stdout: TextIO | None = None) -> bool:
    """Whether a person can answer here: standard input and standard output are
    both terminals. A piped `yes` is no person, and an absent or closed stream
    is no terminal."""
    return _tty(sys.stdin if stdin is None else stdin) and _tty(
        sys.stdout if stdout is None else stdout
    )


def _tty(stream: TextIO | None) -> bool:
    if stream is None:
        return False
    try:
        return bool(stream.isatty())
    except (ValueError, OSError):
        return False


def read_line() -> str:
    """One line typed at standard input. EOFError when the input has ended."""
    line = sys.stdin.readline()
    if not line:
        raise EOFError
    return line


def drop_typed_ahead() -> None:
    """Drop what was typed at the terminal and not yet read, such as an Enter
    pressed during a slow install. Called before each prompt is shown, so only
    an answer typed to the question shown is read."""
    if termios is not None and _tty(sys.stdin):
        with contextlib.suppress(termios.error, OSError, ValueError):
            termios.tcflush(sys.stdin.fileno(), termios.TCIFLUSH)


def ask_pending(
    *,
    point: fixers.Point,
    repo_root: Path,
    config_path: Path,
    interactive: bool | None = None,
    read: Callable[[], str] = read_line,
    out: TextIO | None = None,
    err: TextIO | None = None,
    guard: Callable[[], bool] = lambda: True,
    types: fixers.TypesReader = fixers.read_types,
) -> int:
    """Ask each question nobody answered, where a person can answer, and record
    each answer in the grant list at `config_path` as it is given (DEC-056
    point 2). With nobody to ask, print each question with the one command line
    that grants its fixer, and record nothing. `guard` runs once before the
    first write; false refuses it.

    Whether a person can answer is `interactive`, and by default whether this
    process has a terminal (`at_a_terminal`). The default reader reads standard
    input, so with it a caller's `True` never stands without that terminal: a
    piped `yes` is never consent.

    Returns 0 when nothing waits, when every question was answered, or when
    nobody was there to ask; 1 when the point does not resolve, the grant list
    cannot be read, or an answer cannot be recorded."""
    out = sys.stdout if out is None else out
    err = sys.stderr if err is None else err
    if interactive is None or read is read_line:
        interactive = (interactive is not False) and at_a_terminal()
    if not point.resolved:
        err.write(f"[unresolved] {fixers.POINT} does not resolve: {point.why}. Nothing is asked.\n")
        for line in point.inert:
            err.write(f"  inert: {line}\n")
        return 1
    try:
        answers = fixers.answers_of(fixers.load_config(config_path))
    except fixers.Malformed as exc:
        err.write(f"error: the grant list cannot be read: {exc}; fix it first.\n")
        return 1
    pending = fixers.questions(point, fixers.check(point, repo_root, types), answers)
    if not pending:
        out.write("No fixer waits for an answer.\n")
        return 0
    if not interactive:
        _print_lines(out, pending)
        out.write("Nothing was granted: nobody was at a terminal to answer.\n")
        return 0
    if not config_path.is_file():
        err.write(
            f"error: {config_path} does not exist, so no answer can be recorded: author "
            'project-management\'s configuration first (its README, "Adopter setup").\n'
        )
        _print_lines(err, pending)
        return 1
    if not guard():
        return 1
    recorded: list[tuple[fixers.Question, str]] = []

    def answer(question: fixers.Question, given: str) -> None:
        fixers.record(config_path, question.agent, question.types, given)
        recorded.append((question, given))

    def shown_now(text: str) -> None:
        """Write and flush: a prompt has no line break, so it must reach the
        terminal before the read blocks. Input typed before it is dropped first,
        so it answers nothing (`drop_typed_ahead`)."""
        if read is read_line:
            drop_typed_ahead()
        out.write(text)
        out.flush()

    try:
        left = fixers.ask(pending, read=read, write=shown_now, answer=answer)
    except fixers.Refused as exc:
        err.write(f"error: the answer could not be recorded: {exc}\n")
        return 1
    finally:
        for question, given in recorded:
            out.write(f"Recorded: {question.agent} {given} {', '.join(question.types)}.\n")
        if recorded:
            shown = (
                config_path.relative_to(repo_root)
                if config_path.is_relative_to(repo_root)
                else config_path
            )
            out.write(
                f"Commit {shown}: an answer counts once its change merges into the default "
                "branch.\n"
            )
    if left:
        out.write("Nobody answered the rest. To turn each on later:\n")
        for question in left:
            out.write(f"  {fixers.grant_line(question)}\n")
    return 0


def _print_lines(stream: TextIO, pending: Sequence[fixers.Question]) -> None:
    for question in pending:
        stream.write(f"{fixers.question_text(question)}\n")
        stream.write(f"  To turn it on: {fixers.grant_line(question)}\n")


def run_ask_verb(argv: Sequence[str] | None = None) -> int:
    """`ask-fixers`: read the point, then `ask_pending` at this terminal, if any."""
    parser = argparse.ArgumentParser(
        prog=f"{fixers.COMMAND} {fixers.ASK_VERB}",
        description=(
            "Ask whether each declared fixer nobody was asked about may start on its own "
            "(DEC-056 point 2), and record each answer. With nobody at a terminal, print each "
            "question and the command that grants its fixer, and record nothing."
        ),
    )
    parser.add_argument(
        "--capability-root",
        type=Path,
        default=None,
        help=f"Default: <repo-root>/.pkit/capabilities/{CAPABILITY_NAME}/.",
    )
    session_guard.add_override_argument(parser)
    args = parser.parse_args(argv)
    capability_root = resolve_capability_root(args.capability_root)
    if capability_root is None:
        print(f"error: {CAPABILITY_NAME} capability not found.", file=sys.stderr)
        return 2
    try:
        point = fixers.read_point()
    except fixers.Unreadable as exc:
        print(f"error: the {fixers.POINT} point could not be read: {exc}", file=sys.stderr)
        return 1
    return ask_pending(
        point=point,
        repo_root=capability_root.parents[2],
        config_path=capability_root / fixers.CONFIG_RELATIVE,
        guard=lambda: bool(session_guard.enforce(override=args.allow_foreign_repo)),
    )
