"""Where an issue stands — the reading `start-work`, `review-work` and `move-issue` share.

`move-issue` judges a move from the issue's current state. `start-work` and
`review-work` judge, before they cut a branch or touch a pull request, whether
the move they then make through `move-issue` is legal (#942, #947). All three
take the state of the issue being moved from `read` here, so the early check
and the move it guards resolve state one way (#1242). Each reads at its own
moment: the verb for its early check, `move-issue` again when it moves. When
the state changed in between, `move-issue` judges from what it reads and
refuses a move that is no longer legal; the verb's late-failure message then
says what the run left behind. Other readings stay where they are: a parent's
state in `move-issue`'s cascade, and the verbs `done-work` and `promote-issue`.

The process engine answers first (DEC-033 D7: read, don't re-infer) — `pkit
process status --json`, run as a subprocess and never imported (ADR-020). When
it gives no position — `pkit` not found, a failed run, output that is not a
JSON object, an indeterminate or empty position — the state is inferred from
the issue's own fields through `lifecycle_inference.infer_current_state`. The
engine's shipped detectors apply that same inference to the same fields, so
the two give one answer wherever those fields carry the state. An issue with
no state label and no milestone reads as Todo, as it always has.

Where the configured board carries `state` (`axis_carriage`, DEC-051) and the
engine gives no position, the issue's labels cannot stand in for it.
`Position.unread` then says so, and how the engine failed; the reading takes
no view on what that means. Each caller decides: `move-issue` moves from the
stand-in as it always has, and the composing verbs refuse before they change
anything.
"""

from __future__ import annotations

import json
import re
import subprocess
import unicodedata
from dataclasses import dataclass
from typing import Any

from _lib import axis_carriage, axis_labels
from _lib import lifecycle_inference as infer

PROCESS_ADDRESS = "project-management:issue-lifecycle"

BOARD_CARRIES_STATE = (
    "the configured Projects board carries this project's state, so the issue's "
    "labels cannot stand in for it"
)

# What an unread state shows of what was said about it: at most this many of
# the last non-blank lines, and at most this many characters of them.
SAID_LINES = 5
SAID_CHARS = 600

# A terminal escape sequence, removed whole so its parameters do not show as
# text: a control sequence, a string sequence ended by BEL or ST, or any other.
_ESCAPE_SEQUENCE = re.compile(
    r"\x1b(?:\[[0-?]*[ -/]*[@-~]|[\]PX^_][^\x07\x1b]*(?:\x07|\x1b\\)|[ -/]*[0-~])"
)


@dataclass(frozen=True)
class EngineAnswer:
    """What one `pkit process status --json` run gave for an issue.

    `status` is its payload when the run printed a JSON object, and None
    otherwise. `failure` is None when there is a payload, and otherwise says
    how the run failed, as a clause ("`pkit` was not found on PATH").
    `said` is the end of what the run wrote on standard error (`said_tail`);
    "" when it wrote nothing."""

    status: dict[str, Any] | None = None
    failure: str | None = None
    said: str = ""


@dataclass(frozen=True)
class Unread:
    """Why a board-carried state has no reading: the engine gave no position.

    `cause` says how, as a clause; `said` is the end of what was said about it
    (`said_tail`), and `said_by` who said it. `said` is "" when nothing was."""

    cause: str
    said: str = ""
    said_by: str = ""


@dataclass(frozen=True)
class Position:
    """An issue's current state as one read gives it.

    `state` is what a move is judged from. `status` is the engine's status
    payload when it gave one — `move-issue` also counts the journal in it.
    `unread` is None when `state` is a reading, and otherwise says why it is
    only a stand-in."""

    state: str
    status: dict[str, Any] | None = None
    unread: Unread | None = None


def ask_engine(issue_number: int) -> EngineAnswer:
    """Ask the process engine where the issue is (`pkit process status --json`).

    Never raises: a run that gives no payload comes back with `failure` saying
    how — `pkit` not found or not startable, a non-zero exit, or output that is
    not a JSON object — and with the end of what it wrote on stderr."""
    try:
        proc = subprocess.run(
            [
                "pkit",
                "process",
                "status",
                PROCESS_ADDRESS,
                "--subject",
                str(issue_number),
                "--json",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return EngineAnswer(failure="`pkit` was not found on PATH")
    except OSError as exc:
        return EngineAnswer(failure=f"`pkit` could not start: {_clean(str(exc))}")
    said = said_tail(proc.stderr or "")
    if proc.returncode != 0:
        return EngineAnswer(failure=f"`pkit process status` exited {proc.returncode}", said=said)
    try:
        payload = json.loads(proc.stdout)
    except (json.JSONDecodeError, ValueError):
        payload = None
    if not isinstance(payload, dict):
        return EngineAnswer(failure="`pkit process status` printed no JSON object", said=said)
    return EngineAnswer(payload, said=said)


def position_from_status(status: dict[str, Any] | None) -> str | None:
    """The resolved state id from an engine status payload.

    None when there is no payload or the position is missing, malformed or
    indeterminate — `read` then infers the state from the issue's fields."""
    position = status.get("position") if isinstance(status, dict) else None
    if not isinstance(position, dict) or position.get("indeterminate"):
        return None
    state = position.get("state")
    return state if isinstance(state, str) else None


def read(
    issue: dict[str, Any],
    engine: EngineAnswer,
    *,
    labels: list[str],
    config: dict[str, Any] | None,
    substrate_map: axis_labels.SubstrateMap | None,
) -> Position:
    """The issue's current state: the engine's position in `engine`, else the
    inference from the issue's own fields (`issue` as `gh issue view` gives it,
    `labels` its label names). Performs no I/O; `engine` comes from
    `ask_engine`."""
    engine_state = position_from_status(engine.status)
    if engine_state is not None:
        return Position(engine_state, engine.status)
    inferred = infer.infer_current_state(
        state=str(issue.get("state", "")).lower(),
        milestone=issue.get("milestone") or {},
        labels=labels,
        substrate_map=substrate_map,
    )
    if not axis_carriage.is_board_carried("state", config, substrate_map):
        return Position(inferred, engine.status)
    return Position(inferred, engine.status, why_no_position(engine))


def why_no_position(engine: EngineAnswer) -> Unread:
    """How `engine` came to give no position.

    The run failed (`EngineAnswer.failure`, with what `pkit` said); or it
    answered and could not place the issue, naming the first state whose
    detection it could not evaluate and what that predicate said; or it
    answered and no state's detection matched. A payload in any other shape is
    told apart from these as one that gave no position."""
    if engine.failure is not None or engine.status is None:
        return Unread(
            engine.failure or "it gave no answer",
            engine.said,
            "`pkit process status`" if engine.said else "",
        )
    position = engine.status.get("position")
    if not isinstance(position, dict):
        return Unread("its answer carried no position")
    if not position.get("indeterminate"):
        return Unread("no state's detection matched the issue")
    unevaluated = position.get("unevaluated")
    for entry in unevaluated if isinstance(unevaluated, list) else []:
        if not isinstance(entry, dict):
            continue
        state = _clean(str(entry.get("state", "")))
        reason = _clean(str(entry.get("reason", ""))) or "no reason given"
        said = said_tail(str(entry.get("stderr_tail") or ""))
        return Unread(
            f"it could not evaluate the detection of {state!r}: {reason}",
            said,
            f"the {state!r} detection predicate" if said else "",
        )
    return Unread("it could not place the issue (an indeterminate position, no reason given)")


def said_tail(text: str) -> str:
    """The end of what a command said, fit to show the operator.

    Terminal escape sequences are removed whole and every other control or
    format character dropped (a tab becomes a space), so the text cannot
    rewrite the terminal it is shown on. Only the last `SAID_LINES` non-blank
    lines are kept, and of those the last `SAID_CHARS` characters; a tail that
    lost its beginning starts with `…`."""
    lines = [line for line in (_clean(raw) for raw in text.splitlines()) if line]
    truncated = len(lines) > SAID_LINES
    tail = "\n".join(lines[-SAID_LINES:])
    if len(tail) > SAID_CHARS:
        tail = tail[-(SAID_CHARS - 1) :]
        truncated = True
    return f"…{tail}" if truncated else tail


def _clean(line: str) -> str:
    """`line` with escape sequences and control or format characters removed
    (a tab becomes a space), and trailing whitespace stripped."""
    return "".join(
        " " if char == "\t" else char
        for char in _ESCAPE_SEQUENCE.sub("", line)
        if char == "\t" or unicodedata.category(char) not in ("Cc", "Cf")
    ).rstrip()
