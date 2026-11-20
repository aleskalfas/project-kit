"""The process engine, as the capability's commands meet it (lean-business DEC-003 points 1
and 5; DEC-002 point 15; the process area's README, "Seam-ordering contract").

A command reads where a subject stands from the engine, and never works a position out
again. It asks three operations:

- **`status`**: where the subject stands, whether the engine could tell, and each move out
  of there the definition declares, with its trigger, its question and the engine's
  precheck of its gate (`Status`);
- **`can_move`**: whether a move to one target may be taken now, its gate asked of the
  files as they stand;
- **`move`**: the move taken, after the command's write, from the origin it read before
  the write (`--from`), its gate asked of the files as the write left them.

`Engine` is that seam. `PkitEngine` is the engine itself, `pkit process`, which runs each
predicate in a process of its own on the real day. A test gives a command another engine
that asks the same predicates in its own process on the test's day.

The engine's status document is read by key, as its contract says (ADR-097 point 3): a key
the command needs and does not find, or a value it does not know, is no answer, never a
default (`EngineFailed`).
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from _lib import backbone
from _lib.root import CAPABILITY

#: The capability's three processes (DEC-003 point 1).
DESK = "desk-stage"
EXPERIMENT = "experiment-lifecycle"
CYCLE = "cycle-lifecycle"


def address(process: str) -> str:
    """The engine's address of one of the capability's processes."""
    return f"{CAPABILITY}:{process}"


class EngineFailed(Exception):
    """The engine could not be asked, or gave no answer the command can read."""


@dataclass(frozen=True)
class Move:
    """A move the definition declares out of where a subject stands: its target, its
    trigger, whether the engine's precheck lets it through and why, and its question, where
    it is the person's."""

    to: str
    trigger: str
    allowed: bool
    reason: str
    prompt: str | None = None


@dataclass(frozen=True)
class Status:
    """Where a subject stands: its state, or None where it stands in none; whether the
    engine could not tell, and why; and the moves out of there."""

    state: str | None
    indeterminate: bool = False
    why: str = ""
    moves: tuple[Move, ...] = ()

    def by(self, trigger: str) -> tuple[Move, ...]:
        """The moves out of here that `trigger` takes."""
        return tuple(move for move in self.moves if move.trigger == trigger)


@dataclass(frozen=True)
class Verdict:
    """Whether the engine let a move through, and why."""

    ok: bool
    reason: str


class Engine(Protocol):
    """The engine's three operations a command asks, each of one subject of one process."""

    def status(self, process: str, subject: str) -> Status: ...

    def can_move(self, process: str, subject: str, to: str, actor: str) -> Verdict: ...

    def move(self, process: str, subject: str, to: str, origin: str, actor: str) -> Verdict: ...


class PkitEngine:
    """The engine itself, asked through `pkit process` from the project `root`."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def _run(self, argv: list[str]) -> Any:
        try:
            return backbone.run(argv, cwd=self.root, capture_output=True, text=True, check=False)
        except OSError as exc:
            raise EngineFailed(f"`pkit` could not be run: {exc}") from exc

    def status(self, process: str, subject: str) -> Status:
        done = self._run(
            ["pkit", "process", "status", address(process), "--subject", subject, "--json"]
        )
        if done.returncode != 0:
            raise EngineFailed(_said(done) or f"`pkit process status` exited {done.returncode}")
        try:
            document = json.loads(done.stdout)
        except (TypeError, ValueError) as exc:
            raise EngineFailed(f"`pkit process status` printed no JSON document: {exc}") from exc
        return read_status(document)

    def can_move(self, process: str, subject: str, to: str, actor: str) -> Verdict:
        argv = ["pkit", "process", "can-move", address(process), "--to", to]
        done = self._run([*argv, "--subject", subject, "--actor", actor])
        return Verdict(done.returncode == 0, _verdict_words(_said(done)))

    def move(self, process: str, subject: str, to: str, origin: str, actor: str) -> Verdict:
        argv = ["pkit", "process", "move", address(process), "--to", to, "--from", origin]
        done = self._run([*argv, "--subject", subject, "--actor", actor])
        return Verdict(done.returncode == 0, _verdict_words(_said(done)))


def read_status(document: object) -> Status:
    """The status the engine's document gives, read by key. Raises EngineFailed where a key
    the command needs is missing or of another shape."""
    if not isinstance(document, Mapping):
        raise EngineFailed("the engine's status is no JSON object")
    position = document.get("position")
    moves = document.get("legal_moves")
    if not isinstance(position, Mapping) or not isinstance(moves, list):
        raise EngineFailed("the engine's status holds no `position` or no `legal_moves`")
    state = position.get("state")
    indeterminate = position.get("indeterminate")
    if (state is not None and not isinstance(state, str)) or not isinstance(indeterminate, bool):
        raise EngineFailed("the engine's status gives no state, or not whether it could tell")
    why = "; ".join(
        f"{entry.get('state')}: {entry.get('reason')}"
        for entry in position.get("unevaluated") or []
        if isinstance(entry, Mapping)
    )
    read: list[Move] = []
    for entry in moves:
        if not isinstance(entry, Mapping):
            raise EngineFailed("the engine's status lists a move that is no JSON object")
        to, trigger, allowed = entry.get("to"), entry.get("trigger"), entry.get("allowed")
        if not isinstance(to, str) or not isinstance(trigger, str) or not isinstance(allowed, bool):
            raise EngineFailed("the engine's status lists a move without its target or trigger")
        reason, prompt = entry.get("reason"), entry.get("prompt")
        read.append(
            Move(
                to,
                trigger,
                allowed,
                reason if isinstance(reason, str) else "",
                prompt if isinstance(prompt, str) else None,
            )
        )
    return Status(state, indeterminate, why, tuple(read))


def _said(done: Any) -> str:
    return "\n".join(
        part.strip() for part in (str(done.stdout or ""), str(done.stderr or "")) if part.strip()
    )


def _verdict_words(said: str) -> str:
    """The engine's words on a move, without the mark it opens them with."""
    words = said.strip()
    for mark in ("✓ ", "✗ ", "refused: ", "moved to "):
        words = words.removeprefix(mark)
    return words
