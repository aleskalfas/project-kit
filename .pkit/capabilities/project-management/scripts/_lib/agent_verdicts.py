"""DEC-028 reviewer-verdict *posted-comment* parsing — the single source of truth.

Scope: this module is the single source of truth for parsing a reviewer's
verdict out of a *posted PR comment* — a comment whose FIRST line is one of
the two recognised shapes below. It is NOT the source of truth for extracting
a verdict from an agent's *raw output*: DEC-028's raw-output contract is "scan
for the first grammar-matching line ANYWHERE in the output" (an agent emits
preamble before its verdict line), which is a different rule from this module's
first-line-of-a-posted-comment parse. `review-pr` owns that raw-output scan
inline and does NOT route through this module — do not repurpose
`parse_verdict_line` (first-line-only) for raw-output extraction.

DEC-028 has reviewer agents post their verdict as a PR comment whose first
line is one of two recognised shapes:

    remote path:  Reviewer agent: APPROVED | CHANGES_REQUESTED
    local path:   Reviewer agent (local, <name>): APPROVED | CHANGES_REQUESTED

Two consumers read these comments and MUST agree on what they say (COR-007 —
one parser, not two):

  * `done-work`'s agent-mode gate collapses to the latest verdict *token* per
    reviewer (freshness-filtered against the latest commit, restricted to the
    resolved required set) and checks every required reviewer has a fresh
    APPROVED.
  * `show-pr --field review` surfaces the latest verdict *token and body* per
    reviewer so an operator can read the reasons through the governed pm
    surface (issue #544).

The gate needs only the token; the read surface needs the body too. So the
shared record (`Verdict`) carries the token, the full comment body, the
reviewer identity, the path, and the timestamp — the gate ignores the fields
it does not need. The "latest verdict per reviewer, selected by timestamp"
rule (DEC-028 step 5 — a later CHANGES_REQUESTED must override an earlier
APPROVED regardless of `gh`'s array order) lives here once, so the two
consumers cannot diverge on which comment is a reviewer's current verdict.

This module owns NO `gh` wiring: both consumers fetch the PR's comments via
their own governed `gh_run` helper and pass the resulting comment list in.
That keeps this module pure-logic and unit-testable without a live repo.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable

APPROVED = "APPROVED"
CHANGES_REQUESTED = "CHANGES_REQUESTED"

# Verdict-comment path (DEC-028): a remote reviewer posts under its GitHub
# login; a local reviewer names itself in the first line.
PATH_REMOTE = "remote"
PATH_LOCAL = "local"

# DEC-028 remote-path first lines. Fixed strings (the reviewer identity is the
# comment's GitHub author, not embedded in the line).
_REMOTE_VERDICT_LINES = {
    f"Reviewer agent: {APPROVED}": APPROVED,
    f"Reviewer agent: {CHANGES_REQUESTED}": CHANGES_REQUESTED,
}

# DEC-028 local-path first line, generalised to any registered name (the
# singleton cap lifted in DEC-032 D3). Kept identical to the pattern
# `review-pr` writes and `done-work` matched inline before extraction.
_LOCAL_VERDICT_RE = re.compile(
    r"^Reviewer agent \(local, (?P<name>[^)]+)\): "
    rf"(?P<verdict>{APPROVED}|{CHANGES_REQUESTED})$"
)


@dataclass(frozen=True)
class Verdict:
    """One reviewer's verdict, as parsed from a DEC-028 comment.

    * `reviewer` — the reviewer's identity: the GitHub login on the remote
      path, the registered name embedded in the line on the local path. This
      is the latest-per-reviewer key.
    * `token` — `APPROVED` or `CHANGES_REQUESTED`.
    * `path` — `PATH_REMOTE` or `PATH_LOCAL`.
    * `body` — the full comment body (the reasons the read surface shows).
    * `timestamp` — the comment's `createdAt` (ISO-8601 UTC; string-comparable
      for the latest-by-timestamp selection).
    """

    reviewer: str
    token: str
    path: str
    body: str
    timestamp: str


def parse_verdict_line(first_line: str) -> tuple[str | None, str, str | None]:
    """Recognise a DEC-028 verdict from a comment's first line.

    Returns `(token, path, name)`:
      * remote match → `(token, PATH_REMOTE, None)` (identity is the author),
      * local match  → `(token, PATH_LOCAL, name)`,
      * no match     → `(None, "", None)`.

    Owns the shape both `done-work` and `show-pr` recognise, so neither
    re-derives the line grammar.
    """
    remote_token = _REMOTE_VERDICT_LINES.get(first_line)
    if remote_token is not None:
        return remote_token, PATH_REMOTE, None
    match = _LOCAL_VERDICT_RE.match(first_line)
    if match is not None:
        return match.group("verdict"), PATH_LOCAL, match.group("name")
    return None, "", None


def latest_verdicts_per_reviewer(
    comments: list,
    *,
    remote_reviewer_ok: Callable[[str], bool] = lambda _login: True,
    local_reviewer_ok: Callable[[str], bool] = lambda _name: True,
    min_timestamp: str | None = None,
) -> list[Verdict]:
    """Collapse a PR's comments to the latest verdict per reviewer (DEC-028).

    This is the permissive *read-surface* primitive: `show-pr --field review`
    calls it directly to show every posted verdict (latest per reviewer). Its
    defaults are deliberately permissive — no freshness anchor, allow-all
    membership — because a read surface shows whatever verdicts exist. Those
    defaults are NOT safe for the merge gate: a caller that wants gate
    semantics must go through `gate_verdicts` (below), whose freshness and
    membership filters are required, non-defaulted arguments. Do not call this
    primitive from a gate path — the permissive default would silently count
    every verdict from anyone at any age (self-approval included).

    Walks `comments` (the `gh pr view --json comments` array), recognises the
    DEC-028 verdict shapes, and returns the latest verdict *per reviewer*,
    selected by timestamp (DEC-028 step 5) — a later CHANGES_REQUESTED
    correctly supersedes an earlier APPROVED and vice versa, regardless of
    how `gh` ordered the array.

    The two consumers share this selection but scope it differently, so the
    filters are injected rather than baked in:

      * `remote_reviewer_ok` / `local_reviewer_ok` — predicates on the
        reviewer identity. The gate (via `gate_verdicts`) passes
        membership-in-the-required-set predicates (and its remote predicate
        also excludes the PR author, per DEC-028 step 3); `show-pr` accepts
        every reviewer (it shows whatever verdicts exist).
      * `min_timestamp` — when set, only comments strictly after it are
        considered (the gate's freshness anchor: the latest commit
        timestamp). `show-pr` leaves it `None` — a stale verdict is still the
        reviewer's current verdict to *display*; freshness is a gate concern,
        not a read-surface one.

    A reviewer is keyed by `(path, reviewer)` so a remote and a local verdict
    from names that happen to collide never overwrite each other. The returned
    list is ordered by reviewer identity for deterministic output.
    """
    latest: dict[tuple[str, str], Verdict] = {}
    for comment in comments:
        if not isinstance(comment, dict):
            continue
        body = comment.get("body") or ""
        first_line = body.split("\n", 1)[0].strip()
        token, path, name = parse_verdict_line(first_line)
        if token is None:
            continue

        timestamp = str(comment.get("createdAt") or "")
        if min_timestamp is not None and timestamp <= min_timestamp:
            continue

        if path == PATH_REMOTE:
            reviewer = (comment.get("author") or {}).get("login") or ""
            if not remote_reviewer_ok(reviewer):
                continue
        else:
            reviewer = name or ""
            if not local_reviewer_ok(reviewer):
                continue

        key = (path, reviewer)
        prior = latest.get(key)
        # ISO-8601 (UTC `Z`) timestamps compare correctly as strings. Strict
        # `>` keeps the first-seen verdict on an exact tie (deterministic).
        if prior is None or timestamp > prior.timestamp:
            latest[key] = Verdict(
                reviewer=reviewer,
                token=token,
                path=path,
                body=body,
                timestamp=timestamp,
            )

    return sorted(latest.values(), key=lambda v: (v.path, v.reviewer))


def gate_verdicts(
    comments: list,
    *,
    min_timestamp: str,
    local_reviewer_ok: Callable[[str], bool],
    remote_reviewer_ok: Callable[[str], bool],
) -> list[Verdict]:
    """Strict, gate-facing verdict selection for the merge gate (DEC-028).

    Behaviour-identical to `latest_verdicts_per_reviewer`, but the three
    security-relevant filters are REQUIRED (non-defaulted) keyword arguments —
    there is no way to call this permissively. That makes the fail-open default
    of the read-surface primitive unreachable from the gate path: the gate's
    correctness no longer depends on `done-work` *remembering* to inject a
    freshness anchor and membership/author-exclusion predicates; forgetting one
    is a `TypeError` at the call site, not a silently weakened gate.

      * `min_timestamp` — the freshness anchor (the latest-commit timestamp);
        only comments strictly after it count (DEC-028 step 4). Required so a
        stale APPROVED can never slip through as fresh.
      * `local_reviewer_ok` / `remote_reviewer_ok` — membership predicates
        scoping the count to the resolved required set (and excluding the PR
        author on the remote path, DEC-028 step 3). Required so a verdict from
        an unrequired identity (self-approval included) can never count.
    """
    return latest_verdicts_per_reviewer(
        comments,
        min_timestamp=min_timestamp,
        local_reviewer_ok=local_reviewer_ok,
        remote_reviewer_ok=remote_reviewer_ok,
    )
