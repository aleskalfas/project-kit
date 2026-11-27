"""The world lean-business's command tests run in: a copy of the fixture idea where the
capability is installed, the commands run on a day the test names, and a process engine
that answers in this process.

- **The project** (`project`): the fixture's location copied, with the capability's schemas
  beside it, so the backbone's data validation, which every write is held to, finds them.
  Every `pkit` call of the capability's goes to the in-process `pkit` (`route_pkit`).
- **The engine** (`InProcessEngine`). The engine itself runs each predicate in a process of
  its own, which reads the real day. This one asks the same predicates in this process, on
  the test's day: each state's detection through `positions`, and each gate through its
  script's `judge`. It keeps each move it took (`moves`), as the engine's journal
  would, and each operation asked of it (`asked`). A test may make it refuse the move after
  the write (`refuse_move`), as the engine refuses one whose gate the write left closed.
- **A run** (`World.run`): a command run through its parser, in a context on the world's
  day, with a person at a terminal or not and their answers, and git's user. It returns
  the exit code, what the command printed, and each question it asked.
"""

from __future__ import annotations

import io
import shutil
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from ruamel.yaml import YAML

from tests.in_process import CAPABILITIES, load, route_pkit

CAPABILITY = CAPABILITIES / "lean-business"
SCRIPTS = CAPABILITY / "scripts"
FIXTURE = Path(__file__).resolve().parent / "fixtures/lean-business/.repo"

IDEA = "lean-business/meal-plan"
GOAL = f"{IDEA}/goal.yaml"
DIRECT = f"{IDEA}/variants/direct/canvas.yaml"
TWO_SIDED = f"{IDEA}/variants/two-sided/canvas.yaml"
CYCLE = f"{IDEA}/cycles/first.yaml"
CONFIG = ".pkit/capabilities/lean-business/project/config.yaml"

#: The person git names in the tests.
PERSON = "A. Founder"

#: The `_lib` modules the tests read, loaded with the commands so they share them.
LIB_NAMES = (
    "acting",
    "backbone",
    "briefing",
    "cycles",
    "editing",
    "engine",
    "estimates",
    "fingerprint",
    "grid",
    "naming",
    "positions",
    "staling",
    "writes",
)

#: The commands, by their scripts' names.
COMMANDS = (
    "add_assumption",
    "add_entry",
    "add_side",
    "canvas",
    "change_plan",
    "decide",
    "declare",
    "draft_experiment",
    "edit_assumption",
    "edit_entry",
    "estimate",
    "judge",
    "move_entry",
    "new_experiment",
    "new_variant",
    "plan_cycle",
    "rank",
    "reach_stopping_rule",
    "record_estimate",
    "record_result",
    "remove_assumption",
    "remove_entry",
    "remove_experiment",
    "remove_side",
    "resume",
    "review_cycle",
    "set_archetype",
    "set_authors",
    "set_goal",
    "set_inputs",
    "set_location",
    "set_traction",
    "shelve",
    "shortlist",
    "split",
    "status",
    "suspend",
)

_GATE_SCRIPTS = sorted(path.name for path in SCRIPTS.glob("*_gate_*.py"))

_LOADED = load("lean-business", *LIB_NAMES, *_GATE_SCRIPTS, *(f"{name}.py" for name in COMMANDS))
LIB: dict[str, ModuleType] = dict(zip(LIB_NAMES, _LOADED, strict=False))
GATES: dict[str, ModuleType] = {
    name.removesuffix(".py").replace("_", "-"): module
    for name, module in zip(_GATE_SCRIPTS, _LOADED[len(LIB_NAMES) :], strict=False)
}
SCRIPT: dict[str, ModuleType] = dict(
    zip(COMMANDS, _LOADED[len(LIB_NAMES) + len(_GATE_SCRIPTS) :], strict=True)
)
acting = LIB["acting"]
backbone = LIB["backbone"]
engine = LIB["engine"]
positions = LIB["positions"]


# --- the project ------------------------------------------------------------------------------


def project(tmp_path: Path) -> Path:
    """A copy of the fixture where the capability is installed, its schemas beside it."""
    root = tmp_path / "repo"
    shutil.copytree(FIXTURE, root)
    installed = root / ".pkit/capabilities/lean-business"
    installed.mkdir(parents=True)
    shutil.copytree(CAPABILITY / "schemas", installed / "schemas")
    (root / ".pkit/decisions").mkdir()
    return root


def _yaml() -> YAML:
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.width = 4096
    return yaml


def read(root: Path, rel: str) -> Any:
    """The file `rel`'s YAML, read safely: a day is a `date`."""
    return YAML(typ="safe").load((root / rel).read_text(encoding="utf-8"))


def edit(root: Path, rel: str, change: Callable[[Any], None]) -> None:
    """Make `change` to the file `rel`'s YAML, round trip, and write it back."""
    path = root / rel
    data = _yaml().load(path.read_text(encoding="utf-8"))
    change(data)
    with path.open("w", encoding="utf-8") as out:
        _yaml().dump(data, out)


def snapshot(root: Path) -> dict[str, bytes]:
    """Every file under `root` but the capability's own, by its path, with its bytes."""
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file() and "schemas" not in path.parts and ".pkit/decisions" not in str(path)
    }


# --- the engine -------------------------------------------------------------------------------

#: How each process places a subject, as its detection predicate answers.
DETECT: dict[str, Callable[[Path, str, date], Any]] = {
    "desk-stage": lambda root, subject, _on: positions.desk_stage_of(root, subject),
    "cycle-lifecycle": positions.cycle_lifecycle_of,
    "experiment-lifecycle": positions.experiment_lifecycle_of,
}


def _definition(process: str) -> dict[str, Any]:
    return YAML(typ="safe").load((CAPABILITY / f"schemas/{process}.yaml").read_text())["process"]


class _Indeterminate(Exception):
    pass


@dataclass
class InProcessEngine:
    """The engine's three operations, asked in this process on the day `on`."""

    root: Path
    on: date
    moves: list[tuple[str, str, str, str, str]] = field(default_factory=list)
    asked: list[tuple[str, str, str]] = field(default_factory=list)
    refuse_move: str | None = None

    def _state(self, process: str, subject: str) -> str | None:
        try:
            return DETECT[process](self.root, subject, self.on).state
        except positions.Unreadable as exc:
            raise _Indeterminate(str(exc)) from exc

    def _gate(self, process: str, transition: dict[str, Any], subject: str) -> tuple[bool, str]:
        gate = transition.get("gate")
        if not gate:
            return True, "no gate"
        try:
            answer = GATES[gate["predicate"]["run"]].judge(self.root, subject, self.on)
        except positions.Unreadable as exc:
            return False, f"indeterminate: {exc}"
        return bool(answer.result), str(answer.reason)

    def _from(self, process: str, state: str | None) -> list[dict[str, Any]]:
        return [t for t in _definition(process)["transitions"] if t["from"] == state]

    def status(self, process: str, subject: str) -> Any:
        self.asked.append(("status", process, subject))
        try:
            state = self._state(process, subject)
        except _Indeterminate as exc:
            return engine.Status(None, True, str(exc), ())
        moves = []
        for transition in self._from(process, state):
            allowed, reason = self._gate(process, transition, subject)
            moves.append(
                engine.Move(
                    transition["to"],
                    transition["trigger"],
                    allowed,
                    reason,
                    transition.get("prompt"),
                )
            )
        return engine.Status(state, False, "", tuple(moves))

    def can_move(self, process: str, subject: str, to: str, actor: str) -> Any:
        self.asked.append(("can-move", process, f"{subject} to {to}"))
        state = self._state(process, subject)
        found = [t for t in self._from(process, state) if t["to"] == to]
        if not found:
            return engine.Verdict(False, f"no move from {state} to {to}")
        return engine.Verdict(*self._gate(process, found[0], subject))

    def move(self, process: str, subject: str, to: str, origin: str, actor: str) -> Any:
        self.asked.append(("move", process, f"{subject} from {origin} to {to}"))
        if self.refuse_move is not None:
            return engine.Verdict(False, self.refuse_move)
        state = self._state(process, subject)
        if state not in (origin, to):
            return engine.Verdict(False, f"the subject is at {state}, neither {origin} nor {to}")
        found = [t for t in self._from(process, origin) if t["to"] == to]
        if not found:
            return engine.Verdict(False, f"no move from {origin} to {to}")
        allowed, reason = self._gate(process, found[0], subject)
        if allowed:
            self.moves.append((process, subject, origin, to, actor))
        return engine.Verdict(allowed, reason)


# --- a run ------------------------------------------------------------------------------------


@dataclass
class Run:
    """A command's run: its exit code, what it printed, and each question it asked."""

    code: int
    out: str
    err: str
    asked: list[str]


def context(
    root: Path,
    on: date,
    the_engine: Any,
    *,
    terminal: bool = False,
    answers: Sequence[bool] = (),
    who: str | None = PERSON,
    asked: list[str] | None = None,
) -> Any:
    """The commands' context on the day `on`, with `the_engine`; a person at the terminal
    who answers `answers` in turn, where `terminal`; and git's user `who`. Each question
    asked goes into `asked`."""
    left = list(answers)
    kept = asked if asked is not None else []

    def ask(question: str) -> bool:
        kept.append(question)
        return left.pop(0)

    return acting.Context(
        root=root,
        on=on,
        engine=the_engine,
        terminal=terminal,
        ask=ask,
        out=io.StringIO(),
        err=io.StringIO(),
        whom=lambda: who,
    )


@dataclass
class World:
    """A copy of the fixture, the in-process engine on the day `on`, and the in-process
    `pkit` every call of the capability's goes to."""

    root: Path
    engine: InProcessEngine
    pkit: Any

    def run(
        self,
        command: str,
        *argv: str,
        terminal: bool = False,
        answers: Sequence[bool] = (),
        who: str | None = PERSON,
    ) -> Run:
        """Run the command `command` with `argv`."""
        asked: list[str] = []
        ctx = context(
            self.root,
            self.engine.on,
            self.engine,
            terminal=terminal,
            answers=answers,
            who=who,
            asked=asked,
        )
        script = SCRIPT[command]
        code = acting.invoke(script.parser(), script.run, argv, ctx)
        return Run(code, ctx.out.getvalue(), ctx.err.getvalue(), asked)

    def read(self, rel: str) -> Any:
        return read(self.root, rel)

    def edit(self, rel: str, change: Callable[[Any], None]) -> None:
        edit(self.root, rel, change)


def world(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, on: date) -> World:
    """A world on the day `on`."""
    root = project(tmp_path)
    pkit = route_pkit(monkeypatch, backbone)
    return World(root, InProcessEngine(root, on), pkit)
