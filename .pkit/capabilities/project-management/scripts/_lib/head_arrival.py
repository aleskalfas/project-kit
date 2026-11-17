"""When a pull request's head arrived on the host (#2930).

A verdict that names no reviewed head is fresh only when it was posted after
the PR's head arrived (DEC-028 "Stale-verdict handling"). The head commit's
own dates cannot say when that was: the committer's clock sets them, and a
rebase or an amend keeps them, so a commit made before a verdict and pushed
after it would read as one the verdict judged.

The host records when a branch moved. GitHub's repository activity lists each
push, force push, branch creation and merge on a branch, with the commit the
branch moved to and when (`GET /repos/{owner}/{repo}/activity?ref=<branch>`).
The PR's head arrived at the latest entry for its head branch, in the
repository the branch lives in, that moved the branch to that head.

Not the head commit's first check suite: a check suite belongs to a commit,
not to a branch, and is made wherever the commit is pushed. A commit pushed
to another branch before the verdict would read as arrived before it, and a
repository where no app makes check suites has none.

`read_head_arrival` makes one `gh api` call, on the first page of the
branch's activity, newest first; the freshness rule asks it only when it
judges a verdict that names no head. Where the arrival cannot be read — the
PR's head, its head branch or the branch's repository unknown, a call that
fails, an answer that does not read, or no entry moving the branch to the
head — the answer says why, and the rule holds such a verdict stale with
that reason (fail closed).
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

try:
    from _lib.audit import short_sha
except ImportError:  # pragma: no cover - exercised via spec-loaded fallback
    from audit import short_sha  # type: ignore[no-redef]


# The `gh pr view --json` fields the arrival is read from, beside the head.
ARRIVAL_VIEW_FIELDS = ("headRefName", "headRepository")

# GitHub's activity listing, newest first: the head's arrival is the first
# entry unless the branch moved again since the PR was read.
_ACTIVITY_PAGE = 30

# A repository as GitHub names it, `owner/name`, one path segment each.
_REPOSITORY_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9-]*/(?!\.+$)[A-Za-z0-9_.-]+")

# The instant GitHub writes, in UTC to the second: string-comparable with a
# comment's `createdAt`, which GitHub writes the same way.
_INSTANT_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")

GhRunFn = Callable[..., Any]


@dataclass(frozen=True)
class HeadArrival:
    """When the PR's head arrived on its branch, or why that cannot be read.

    `timestamp` is ISO-8601 UTC, to the second, as GitHub writes it; it is ""
    whenever `error` names why it could not be read.
    """

    timestamp: str = ""
    error: str = ""

    @property
    def ok(self) -> bool:
        return bool(self.timestamp) and not self.error


def unread_arrival(_pr_view: Mapping, _head: str) -> HeadArrival:
    """The fail-closed reader: no arrival is ever read."""
    return HeadArrival(error="no reader of when the head arrived was given")


def read_head_arrival(
    pr_view: Mapping,
    head: str,
    config: dict,
    *,
    gh_run: GhRunFn,
) -> HeadArrival:
    """When `head`, the head of the PR `pr_view` describes, arrived on its
    branch, from the host's record of the branch's moves.

    `pr_view` carries `ARRIVAL_VIEW_FIELDS`. `gh_run` is the caller's pm `gh`
    helper, which threads `config`, the adopter's pm config.
    """
    if not head:
        return HeadArrival(error="the pull request's head is unknown")
    branch = str(pr_view.get("headRefName") or "")
    repository = _repository(pr_view.get("headRepository"))
    if not branch or not repository:
        return HeadArrival(
            error="the pull request names no head branch, or no repository it lives in"
        )
    ref = quote(f"refs/heads/{branch}", safe="")
    endpoint = f"repos/{repository}/activity?ref={ref}&per_page={_ACTIVITY_PAGE}"
    try:
        proc = gh_run(["gh", "api", endpoint], config, check=False)
    except OSError as exc:
        return HeadArrival(error=f"`gh` could not be run ({exc})")
    if proc.returncode != 0:
        said = " ".join((proc.stderr or "").split()) or f"gh exited {proc.returncode}"
        return HeadArrival(error=f"gh api repos/{repository}/activity failed: {said}")
    try:
        entries = json.loads(proc.stdout or "")
    except ValueError:
        entries = None
    if not isinstance(entries, list):
        return HeadArrival(error=f"GitHub's activity on {branch} does not read as a list")
    arrivals = [
        entry["timestamp"]
        for entry in entries
        if isinstance(entry, dict)
        and entry.get("after") == head
        and isinstance(entry.get("timestamp"), str)
        and _INSTANT_RE.fullmatch(entry["timestamp"])
    ]
    if not arrivals:
        return HeadArrival(
            error=(f"GitHub's latest activity on {branch} records no move to {short_sha(head)}")
        )
    return HeadArrival(timestamp=max(arrivals))


def _repository(head_repository: object) -> str:
    """The `owner/name` of the repository the head branch lives in, or ""."""
    if not isinstance(head_repository, dict):
        return ""
    name = head_repository.get("nameWithOwner")
    return name if isinstance(name, str) and _REPOSITORY_RE.fullmatch(name) else ""
