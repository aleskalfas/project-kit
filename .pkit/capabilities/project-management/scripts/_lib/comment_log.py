"""The one reader of an issue's comment log, read whole (ADR-041 point 1, ADR-071 point 3).

Two seams fold a log of event comments: the ownership seam folds an issue's
owner ([pkit:ADR-041]), and the state-issue seam folds the state a state issue
holds ([pkit:ADR-071]). Both read the log here, so both mean one thing by a log
read whole. A fold of a log cut short could miss a release or the claim that
holds, so no fold reads the comments a listing returns.

:func:`read_log` pages the issue's comments through GitHub's REST endpoint, a
hundred to a call, to their end. Each comment comes back with its id, its
author's login, the time GitHub records for its creation and its body, in the
order of its id, which is the order GitHub lists them in. A read that cannot
reach the end says so, with its cause: a failed call, an answer that is no list,
an entry with no id, or a log longer than the reader goes.

The ``gh`` runner is the caller's (``gh(argv)``), so a test fakes it and the
module imports no ``gh`` helper. Failure-posture neutral: the reader reports,
and its caller decides what an incomplete log means.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

#: Comments a page holds, GitHub's largest.
PAGE_SIZE = 100

#: The pages a read goes to, ten thousand comments. A longer log is reported
#: incomplete rather than read in part.
MAX_PAGES = 100

#: A ``gh`` runner: takes the argv, returns what ``subprocess.run`` returns.
Gh = Callable[[list[str]], Any]


@dataclass(frozen=True)
class LogComment:
    """One comment of the log. ``author`` is None for an account GitHub no
    longer has."""

    id: int
    author: str | None
    created_at: str
    body: str


@dataclass(frozen=True)
class LogRead:
    """The log of one issue: whole, or incomplete with its cause."""

    complete: bool
    comments: tuple[LogComment, ...] = ()
    cause: str | None = None


def page_args(issue_number: int, page: int) -> list[str]:
    """The ``gh api`` call that reads one page of the issue's comments."""
    return [
        "gh",
        "api",
        f"repos/{{owner}}/{{repo}}/issues/{int(issue_number)}/comments"
        f"?per_page={PAGE_SIZE}&page={int(page)}",
    ]


def read_log(issue_number: int, gh: Gh) -> LogRead:
    """Read the whole comment log of ``issue_number``, paged to its end."""
    by_id: dict[int, LogComment] = {}
    for page in range(1, MAX_PAGES + 1):
        try:
            proc = gh(page_args(issue_number, page))
        except FileNotFoundError:
            return LogRead(False, cause="`gh` is not on PATH")
        if getattr(proc, "returncode", 1) != 0:
            return LogRead(False, cause=said(proc))
        try:
            entries = json.loads(getattr(proc, "stdout", "") or "")
        except (TypeError, ValueError):
            return LogRead(False, cause=f"page {page} of #{issue_number}'s comments is not JSON")
        if not isinstance(entries, list):
            return LogRead(False, cause=f"page {page} of #{issue_number}'s comments is no list")
        for entry in entries:
            comment = _comment(entry)
            if comment is None:
                return LogRead(False, cause=f"a comment on #{issue_number} carries no id")
            by_id[comment.id] = comment
        if len(entries) < PAGE_SIZE:
            return LogRead(True, tuple(by_id[i] for i in sorted(by_id)))
    return LogRead(
        False,
        cause=f"#{issue_number} holds more than {MAX_PAGES * PAGE_SIZE} comments; not read in part",
    )


def _comment(entry: Any) -> LogComment | None:
    if not isinstance(entry, dict):
        return None
    cid = entry.get("id")
    if not isinstance(cid, int) or isinstance(cid, bool):
        return None
    user = entry.get("user")
    login = user.get("login") if isinstance(user, dict) else None
    return LogComment(
        id=cid,
        author=login if isinstance(login, str) and login else None,
        created_at=str(entry.get("created_at") or ""),
        body=str(entry.get("body") or ""),
    )


def said(proc: Any) -> str:
    """What a failed ``gh`` call said, in one line."""
    lines = str(getattr(proc, "stderr", "") or "").strip().splitlines()
    return lines[-1] if lines else f"gh exited {getattr(proc, 'returncode', '?')}"
