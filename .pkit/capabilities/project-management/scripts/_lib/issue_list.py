"""The one read of this capability's issues, which leaves state issues out (DEC-058).

[project-management:DEC-058-state-issues] keeps shared state that changes while
agents work in *state issues*: issues outside the work hierarchy, each with a
hidden marker that says it is one (point 2). Point 3 puts the exclusion here.
This capability's one read of its issues leaves state issues out by their
marker, so every listing, check and plan of work gets the issues of work alone.
The exclusion lives in this one read, never in each consumer, as the one reader
of labels does ([pkit:ADR-026]).

Every `gh issue list` in project-management runs through :func:`list_issues`,
and `tests/test_pm_issue_list_guard.py` fails on any other. It runs the listing
its caller describes, asks `gh` for each issue's body as well, and drops each
issue whose body carries the marker. Each issue of work comes back in the fields
the caller asked for, with `body` only where the caller asked for it, so a work
issue reads as it did before this read existed. The state issues it dropped come
back apart (:attr:`IssueListing.state_rows`), so the state-issue seam finds one
by its marker through this read ([pkit:ADR-071] point 2).

A page that reached its limit is judged by what `gh` returned
(:attr:`IssueListing.returned`), state issues included. A page of 50 that held
two state issues still reached its limit, and the issues past it were never
read.

The runner is injectable (`gh_call`), as in the board read seam
(`_lib/board_fields`). A caller passes its own `gh` runner, so its invocation
path and its tests' patch point stay as they were.

The marker
----------
The state-issue seam (`_lib/state_issues`) builds a state issue's marker and
holds its one reader ([pkit:ADR-071] point 6). :func:`is_state_issue` asks that
reader, so this read and the seam agree on what a state issue is. A marker
counts on a line of its own, outside a fenced code block, in any version. A
work issue that quotes one in a sentence or a code block stays a work issue.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

from _lib import state_issues
from _lib.gh import gh_run

GhCall = Callable[..., "subprocess.CompletedProcess[str]"]

_BODY = "body"


def is_state_issue(body: str) -> bool:
    """Whether `body` marks its issue a state issue, by the state-issue seam's
    one reader of the marker."""
    return state_issues.is_state_issue(body)


@dataclass(frozen=True)
class IssueListing:
    """What one `gh issue list` returned, with the state issues left out.

    ``rows`` holds the issues of work, each as `gh` returned it in the fields
    the caller asked for. It is None when the command failed (``returncode``
    and ``stderr`` are `gh`'s, verbatim) or printed no JSON list.
    ``state_rows`` holds the state issues left out, each with its body.
    ``returned`` counts every issue `gh` returned, state issues included: what
    a limit is measured against.
    """

    rows: tuple[Any, ...] | None
    state_rows: tuple[Any, ...] = ()
    returned: int = 0
    returncode: int = 0
    stderr: str = ""


def list_issues(
    config: dict[str, Any],
    flags: Sequence[str],
    *,
    fields: str,
    gh_call: GhCall | None = None,
    **kwargs: Any,
) -> IssueListing:
    """Run ``gh issue list <flags> --json <fields>``, and keep the issues of work.

    ``gh_call`` runs the command as ``gh_call(argv, config, **kwargs)``. It
    defaults to `gh_run` with ``check=False``. A `gh` that is not installed
    raises `FileNotFoundError`, as the runner raises it, so each caller keeps
    its own answer to that.
    """
    asked_body = _BODY in (name.strip() for name in fields.split(","))
    argv = ["gh", "issue", "list", *flags, "--json", fields if asked_body else f"{fields},{_BODY}"]
    runner = gh_call
    if runner is None:
        runner = gh_run
        kwargs.setdefault("check", False)
    proc = runner(argv, config, **kwargs)
    stderr = proc.stderr or ""
    if proc.returncode != 0:
        return IssueListing(rows=None, returncode=proc.returncode, stderr=stderr)
    try:
        parsed = json.loads(proc.stdout or "[]")
    except (ValueError, json.JSONDecodeError):
        return IssueListing(rows=None, stderr=stderr)
    if not isinstance(parsed, list):
        return IssueListing(rows=None, stderr=stderr)
    rows: list[Any] = []
    state_rows: list[Any] = []
    for row in parsed:
        if _is_state_row(row):
            state_rows.append(row)
        else:
            rows.append(row if asked_body else _without_body(row))
    return IssueListing(
        rows=tuple(rows), state_rows=tuple(state_rows), returned=len(parsed), stderr=stderr
    )


def _is_state_row(row: Any) -> bool:
    return isinstance(row, dict) and is_state_issue(str(row.get(_BODY) or ""))


def _without_body(row: Any) -> Any:
    """`row` as `gh` returns it without the body this read added."""
    if not isinstance(row, dict):
        return row
    return {name: value for name, value in row.items() if name != _BODY}
