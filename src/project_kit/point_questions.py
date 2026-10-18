"""The questions data points declare (COR-061): which an operation runs, and how.

A data point's definer may name, on the point, a command of its own that asks
the person about the point and records each answer they give: `question` on an
`extension-points.accepts` entry (the lifecycle README, "Field layout and
casing"). The backbone runs it at the end of three operations, and of no other:
`pkit capabilities install` and `register`, `pkit capabilities upgrade`, and
`pkit upgrade`. `pkit sync` never runs one.

- **Which questions** (`questions_for`): read from the resolved wiring, never
  resolved again here. For one capability's install or upgrade, the question of
  each point the capability defines and of each point one of its contributions
  reaches. For the transition of the backbone, every question. Only a point an
  active provider defines has one (COR-053 point 1), each once, in the order of
  the points' addresses.
- **How** (`ask`): where a person can answer — standard input and standard
  output both terminals — each command runs in turn, from the project root,
  with the terminal's streams and no time bound, as the dispatcher's proxy runs
  a command a person types (`dispatcher`). With nobody to answer, none runs and
  nothing is recorded: one line per question names the command to run later. A
  preview names each question and runs none.

The command decides what it asks, from the point's value and the answers it has
recorded, so asking nothing is a normal run; the backbone never sees its words
or its record. A question that fails is reported with its line, and the ones
after it still run. An interrupt stops the questions, and each one left is
printed with its line. Neither undoes the operation, which completed before the
first question ran.
"""

from __future__ import annotations

import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import click

from project_kit.command_runner import commands_of, resolve_command
from project_kit.connections import PointKind, Wiring

if TYPE_CHECKING:
    from project_kit.capabilities import CapabilitySource

# The column the backbone's lifecycle lines align their verb in.
_VERB_WIDTH = 12


@dataclass(frozen=True)
class Question:
    """One data point's question: the point, its definer and the command it names."""

    address: str  # the point, <publisher>::<role>:<point>
    definer: str  # the capability that defines the point
    command: str  # the command reference, a path through the definer's `commands:`
    script: Path | None  # the leaf's script; None when it names none, or it is missing

    @property
    def line(self) -> str:
        """The command line a person runs to answer the question."""
        return f"pkit {self.definer} {self.command}"


def questions_for(wiring: Wiring, *, capability: str | None = None) -> tuple[Question, ...]:
    """The questions an operation runs, read from `wiring`, the wiring it leaves.

    With `capability`, an install or upgrade of that one capability: the question
    of each point it defines, and of each point one of its contributions reaches,
    bound or not. With none, a transition of the backbone: every question. Only
    the active providers' points are among `wiring.points`, which is sorted by
    address, so each question comes once, in that order.
    """
    found: list[Question] = []
    for binding in wiring.points:
        point = binding.point
        if point.kind is not PointKind.DATA or point.question is None:
            continue
        if capability is not None and not (
            point.provider == capability
            or any(b.counterpart.capability == capability for b in binding.bindings)
        ):
            continue
        found.append(
            Question(
                address=point.address,
                definer=point.provider,
                command=point.question,
                script=_script(wiring, point.provider, point.question),
            )
        )
    return tuple(found)


def wiring_after(target_root: Path, sources: Sequence[CapabilitySource] = ()) -> Wiring:
    """The wiring an operation leaves, for its questions.

    Once the operation has run, the live wiring. A preview passes `sources`, the
    capabilities it would install or move at the versions it would bring, and
    gets the wiring with each in place of any installed copy, read by the one
    resolver as a plan reads it (`capability_plans`)."""
    from project_kit import capabilities as caps
    from project_kit import capability_plans as plans
    from project_kit.connections import resolve_wiring, resolve_wiring_with

    if not sources:
        return resolve_wiring(target_root)
    candidates = [
        plans.as_installed(target_root, candidate)
        for source in sources
        if (candidate := plans.candidate_of(source, caps.KIT_SHIPPED, installed=False)) is not None
    ]
    return resolve_wiring_with(
        target_root, add=candidates, remove=[source.name for source in sources]
    )


def _script(wiring: Wiring, definer: str, reference: str) -> Path | None:
    """The script the definer's command `reference` runs, read from the package
    the wiring read; None when the reference names no leaf, or its script is
    not a file (the packages member reports both)."""
    component = wiring.declarations.by_name(definer)
    if component is None:
        return None
    leaf = resolve_command(
        commands_of(component.component_dir, component.package.get("commands")), reference
    )
    if leaf is None or not leaf.script.is_file():
        return None
    return leaf.script


def at_a_terminal() -> bool:
    """Whether a person can answer here: standard input and standard output both
    terminals. A stream that is absent or closed is no terminal."""
    return _is_tty(sys.stdin) and _is_tty(sys.stdout)


def _is_tty(stream: object) -> bool:
    isatty = getattr(stream, "isatty", None)
    if not callable(isatty):
        return False
    try:
        return bool(isatty())
    except (ValueError, OSError):
        return False


def ask(
    target_root: Path,
    questions: Sequence[Question],
    *,
    dry_run: bool = False,
    interactive: bool | None = None,
    run: Callable[[Question, Path], int] | None = None,
) -> None:
    """Run `questions` at the end of an operation, or name them (COR-061).

    `interactive` overrides the terminal test, for tests; `run` starts one
    question's command and answers its exit status (`_run`, which hands it the
    terminal). With no question, prints nothing.
    """
    if not questions:
        return
    echo = click.echo
    if dry_run:
        echo(
            f"\n  {len(questions)} question(s) the data points declare, asked where a "
            "person can answer (COR-061):"
        )
        for question in questions:
            echo(f"  {'would ask':<{_VERB_WIDTH}} {question.address}: {question.line}")
        return
    if not (at_a_terminal() if interactive is None else interactive):
        echo(
            f"\n  {len(questions)} question(s) the data points declare were not asked, and "
            "nothing was recorded: nobody can answer here, since standard input and "
            "standard output are not both terminals (COR-061). Run each at a terminal "
            "to answer it:"
        )
        for question in questions:
            echo(f"  {'not asked':<{_VERB_WIDTH}} {question.address}: {question.line}")
        return
    start = run if run is not None else _run
    echo(f"\n  {len(questions)} question(s) the data points declare (COR-061):")
    for index, question in enumerate(questions):
        echo(f"\n  {'asking':<{_VERB_WIDTH}} {question.address}: {question.line}")
        if question.script is None:
            echo(
                f"  {'warning':<{_VERB_WIDTH}} {question.address}: command "
                f"{question.command!r} of {question.definer!r} names no script that "
                "exists, so it was not asked (`pkit validate`'s packages member says why)."
            )
            continue
        try:
            status = start(question, target_root)
        except KeyboardInterrupt:
            echo(f"\n  {'stopped':<{_VERB_WIDTH}} the questions. Run each left at a terminal:")
            for left in questions[index:]:
                echo(f"  {'not asked':<{_VERB_WIDTH}} {left.address}: {left.line}")
            return
        except OSError as exc:
            echo(
                f"  {'warning':<{_VERB_WIDTH}} {question.address}: {question.line} could not "
                f"start ({exc.strerror or exc}). Run it again at a terminal: {question.line}"
            )
            continue
        if status != 0:
            ending = f"was ended by signal {-status}" if status < 0 else f"exited {status}"
            echo(
                f"  {'warning':<{_VERB_WIDTH}} {question.address}: {question.line} {ending}. "
                f"Run it again at a terminal: {question.line}"
            )


def _run(question: Question, target_root: Path) -> int:
    """Start the question's command from the project root, with no argument,
    through the dispatcher's proxy run (`dispatcher.run_as_typed`): the
    terminal's streams and no time bound. Answers its exit status."""
    from project_kit.dispatcher import run_as_typed

    assert question.script is not None
    return run_as_typed(question.script, cwd=target_root)
