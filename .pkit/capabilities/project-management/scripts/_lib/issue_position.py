"""Where an issue stands in its lifecycle — the one reading every move judges from.

`move-issue` judges a move from the issue's current state. `start-work` and
`review-work` judge, before they cut a branch or touch a pull request, whether
the move they then make through `move-issue` is legal (#942, #947). All three
take the state from `read` here, so the early check and the move it guards read
state one way and cannot disagree (#1242).

The process engine answers first (DEC-033 D7: read, don't re-infer) — `pkit
process status --json`, run as a subprocess and never imported (ADR-020). Its
position is authoritative. When it gives none — `pkit` not on PATH, a failed or
unparseable run, an indeterminate or empty position — the state is inferred
from the issue's own fields through `lifecycle_inference.infer_current_state`,
the precedence the shipped detectors apply, so the two agree wherever those
fields carry the state. An issue with no state label and no milestone reads as
Todo, as it always has.

Where the fields do not carry it — the configured board carries `state`
(`axis_carriage`, DEC-051) — that inference is a stand-in no substrate backs:
nothing reads a board's Status field yet (ADR-053 point 6). The reading says
so in `Position.unread` and takes no view on it. Each caller decides what that
means: `move-issue` goes on as it always has, and the composing verbs refuse
before they change anything.

One reading per run. The engine's answer is costly — it runs each state's
detector until one matches, each a `gh` read — so a composing verb hands the
status it judged from to the `move-issue` it runs (`handed_down`), and that
`move-issue` takes it instead of asking again. The hand-off is an environment
variable naming the issue, set only in that child's environment and removed by
the first `engine_status` that reads it, so nothing the move starts in turn
inherits it.
"""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from typing import Any

from _lib import axis_carriage, axis_labels
from _lib import lifecycle_inference as infer

PROCESS_ADDRESS = "project-management:issue-lifecycle"

# Carries one run's engine status from a composing verb to its `move-issue`:
# `{"issue": <number>, "status": <payload or null>}`. Internal to this module.
HANDED_DOWN_ENV = "PKIT_PM_ISSUE_STATUS"

UNREAD_ON_BOARD = (
    "the process engine gave no position, and the issue's labels cannot stand in "
    "for it: the configured Projects board carries this project's state, and "
    "nothing reads a board's Status field yet"
)


@dataclass(frozen=True)
class Position:
    """An issue's current state as one run reads it.

    `state` is what a move is judged from. `status` is the engine's status
    payload when it answered at all — `move-issue` also counts the journal in
    it. `unread` is None when `state` is a reading, and otherwise says why it is
    only a stand-in."""

    state: str
    status: dict[str, Any] | None = None
    unread: str | None = None


def engine_status(issue_number: int) -> dict[str, Any] | None:
    """The issue's engine status payload (`pkit process status --json`), or None
    when the engine cannot be reached or answers with something unparseable.

    A status a composing verb handed down for this issue is taken instead of
    asking again, None included (the engine gave nothing in this run)."""
    handed = _take_handed_down(issue_number)
    if handed is not _NOT_HANDED:
        return handed
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
    except (OSError, FileNotFoundError):
        return None
    if proc.returncode != 0:
        return None
    try:
        payload = json.loads(proc.stdout)
    except (json.JSONDecodeError, ValueError):
        return None
    return payload if isinstance(payload, dict) else None


def position_from_status(status: dict[str, Any] | None) -> str | None:
    """The resolved state id from an engine status payload.

    None when there is no payload or the position is missing/indeterminate —
    `read` then infers the state from the issue's fields."""
    position = status.get("position") if isinstance(status, dict) else None
    if not isinstance(position, dict) or position.get("indeterminate"):
        return None
    state = position.get("state")
    return state if isinstance(state, str) else None


def read(
    issue: dict[str, Any],
    status: dict[str, Any] | None,
    *,
    labels: list[str],
    config: dict[str, Any] | None,
    substrate_map: axis_labels.SubstrateMap | None,
) -> Position:
    """The issue's current state: the engine's position in `status`, else the
    inference from the issue's own fields (`issue` as `gh issue view` gives it,
    `labels` its label names). Performs no I/O; `status` comes from
    `engine_status`."""
    engine_state = position_from_status(status)
    if engine_state is not None:
        return Position(engine_state, status)
    inferred = infer.infer_current_state(
        state=str(issue.get("state", "")).lower(),
        milestone=issue.get("milestone") or {},
        labels=labels,
        substrate_map=substrate_map,
    )
    on_board = axis_carriage.is_board_carried("state", config, substrate_map)
    return Position(inferred, status, UNREAD_ON_BOARD if on_board else None)


def handed_down(issue_number: int, status: dict[str, Any] | None) -> dict[str, str]:
    """The environment entry that hands `status` to the `move-issue` a composing
    verb runs for `issue_number`. Merge it into that child's environment only."""
    return {HANDED_DOWN_ENV: json.dumps({"issue": issue_number, "status": status})}


_NOT_HANDED = object()


def _take_handed_down(issue_number: int) -> Any:
    """The status handed down for `issue_number`, or `_NOT_HANDED`. Removes the
    hand-off from this process's environment whatever it names."""
    raw = os.environ.pop(HANDED_DOWN_ENV, None)
    if raw is None:
        return _NOT_HANDED
    try:
        payload = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return _NOT_HANDED
    if not isinstance(payload, dict) or payload.get("issue") != issue_number:
        return _NOT_HANDED
    status = payload.get("status")
    return status if isinstance(status, dict) else None
