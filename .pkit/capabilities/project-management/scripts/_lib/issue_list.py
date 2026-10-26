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
issue reads as it did before this read existed.

A page that reached its limit is judged by what `gh` returned
(:attr:`IssueListing.returned`), state issues included. A page of 50 that held
two state issues still reached its limit, and the issues past it were never
read.

The runner is injectable (`gh_call`), as in the board read seam
(`_lib/board_fields`). A caller passes its own `gh` runner, so its invocation
path and its tests' patch point stay as they were.

The marker
----------
A line of its own, outside a fenced code block, of the form
``<!-- pkit:state-issue v=1 key=<key> -->``. A line that opens the comment with
``pkit:state-issue`` and closes it marks a state issue, whatever attributes it
carries, so a later version of the stamp still reads as one. The marker quoted
in a code block, or inline in a sentence, marks nothing, so a work issue that
writes about state issues stays a work issue. :func:`marker` and
:func:`is_state_issue` are the form's one home until the state issue's schema
holds it (DEC-058 Implications).
"""

from __future__ import annotations

import json
import re
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

from _lib.body_rules import lines_outside_fences

# Sibling module — the gh shell-out helper that pins the adopter's host/owner
# (DEC-023), imported as `_lib/containment` imports it.
try:
    from gh import gh_run  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover
    try:
        from _lib.gh import gh_run  # type: ignore[no-redef]
    except ImportError:  # pragma: no cover
        gh_run = None  # type: ignore[assignment]

GhCall = Callable[..., "subprocess.CompletedProcess[str]"]

#: The version of the marker this module writes.
MARKER_VERSION = 1

_MARKER_LINE = re.compile(r"<!--\s*pkit:state-issue(?:\s+[^\s>]+)*\s*-->")
_KEY = re.compile(r"[^\s>]+")

_BODY = "body"


def marker(key: str) -> str:
    """The marker line of the state issue that holds the piece of state `key`."""
    if not _KEY.fullmatch(key):
        raise ValueError(f"a state issue's key holds no space and no `>`: {key!r}")
    return f"<!-- pkit:state-issue v={MARKER_VERSION} key={key} -->"


def is_state_issue(body: str) -> bool:
    """Whether `body` marks its issue a state issue.

    It does when a line of its own, outside a fenced code block, is the marker.
    """
    return any(_MARKER_LINE.fullmatch(line.strip()) for line in lines_outside_fences(body))


@dataclass(frozen=True)
class IssueListing:
    """What one `gh issue list` returned, with the state issues left out.

    ``rows`` holds the issues of work, each as `gh` returned it in the fields
    the caller asked for. It is None when the command failed (``returncode``
    and ``stderr`` are `gh`'s, verbatim) or printed no JSON list.
    ``returned`` counts every issue `gh` returned, state issues included: what
    a limit is measured against.
    """

    rows: tuple[Any, ...] | None
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
    rows = tuple(
        row if asked_body else _without_body(row) for row in parsed if not _is_state_row(row)
    )
    return IssueListing(rows=rows, returned=len(parsed), stderr=stderr)


def _is_state_row(row: Any) -> bool:
    return isinstance(row, dict) and is_state_issue(str(row.get(_BODY) or ""))


def _without_body(row: Any) -> Any:
    """`row` as `gh` returns it without the body this read added."""
    if not isinstance(row, dict):
        return row
    return {name: value for name, value in row.items() if name != _BODY}
