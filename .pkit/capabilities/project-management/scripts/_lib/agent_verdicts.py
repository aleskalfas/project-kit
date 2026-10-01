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

Three consumers read these comments and MUST agree on what they say (COR-007 —
one parser, not three):

  * `done-work`'s agent-mode gate collapses to the latest verdict *token* per
    reviewer (freshness-filtered, restricted to the resolved required set)
    and checks every required reviewer has a fresh APPROVED.
  * `review-pr` makes the same gate selection (`gate_verdicts`) to skip a
    required reviewer whose latest verdict is still fresh (#1178), so what it
    skips is exactly what the gate would count.
  * `show-pr --field review` surfaces the latest verdict *token and body* per
    reviewer so an operator can read the reasons through the governed pm
    surface (issue #544); `show-pr --field review-history` surfaces the full
    sequence behind that reduction (`all_verdicts`, issue #905).

What counts as fresh is not decided here: each consumer hands in the one
freshness predicate (`_lib.verdict_freshness`, #1179), and this module only
applies it.

The gate needs only the token; the read surface needs the body too. So the
shared record (`Verdict`) carries the token, the full comment body, the
reviewer identity, the path, the timestamp and the head the verdict reviewed —
the gate ignores the fields it does not need. The "latest verdict per
reviewer, selected by timestamp" rule (DEC-028 step 5 — a later
CHANGES_REQUESTED must override an earlier APPROVED regardless of `gh`'s
array order) lives here once, so the consumers cannot diverge on which
comment is a reviewer's current verdict.

This module owns NO `gh` wiring: each consumer fetches the PR's comments via
its own governed `gh_run` helper and passes the resulting comment list in.
That keeps this module pure-logic and unit-testable without a live repo.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass

APPROVED = "APPROVED"
CHANGES_REQUESTED = "CHANGES_REQUESTED"

# Provenance marker the reviewer path stamps on a verdict comment (#593). The
# **gate** counts a verdict only when its body carries this marker, so a bare
# verdict-grammar line posted by any *other* path (a hand-typed comment, a
# freeform note that slipped the DEC-047 write-side guard, a future tool) never
# satisfies the merge gate. The read surface (`show-pr --field review`) stays
# permissive — it displays every verdict-shaped comment, marked or not. Reuses
# the HTML-marker convention (`pkit-provenance`, `pkit-hook`, `pkit-freeform`).
#
# `review-pr` also names the PR head the reviewer was shown in the marker —
# `<!-- pkit-verdict sha=<oid> -->` (#1179) — which is what the freshness rule
# reads (`_lib.verdict_freshness`). The bare form is still a marker: a verdict
# carrying it has no recorded head and is fresh by the latest commit's time.
VERDICT_MARKER = "<!-- pkit-verdict -->"

# A recorded head is a full object name (40 hex digits, or 64 in a SHA-256
# repository), never an abbreviation that could later become ambiguous.
_OBJECT_NAME = r"[0-9a-f]{40}|[0-9a-f]{64}"
_OBJECT_NAME_RE = re.compile(rf"(?:{_OBJECT_NAME})")

# Either marker form; `sha` is the reviewed head when one is named.
_VERDICT_MARKER_RE = re.compile(rf"<!-- pkit-verdict(?: sha=(?P<sha>{_OBJECT_NAME}))? -->")


def verdict_marker(sha: str = "") -> str:
    """The verdict marker, naming the reviewed head when `sha` is a full
    object name. Anything else yields the bare marker — a marker naming a
    malformed head would not be recognised, and the verdict would not gate."""
    if sha and _OBJECT_NAME_RE.fullmatch(sha):
        return f"<!-- pkit-verdict sha={sha} -->"
    return VERDICT_MARKER


def stamp_verdict(body: str, sha: str = "") -> str:
    """Stamp a verdict comment body with the verdict marker (idempotent).

    Any marker already in the body — a reviewer agent is asked to end its
    output with the bare one — is replaced, so the body carries exactly one,
    naming `sha`, the head `review-pr` showed the reviewer. Without a `sha`
    the bare marker is stamped.
    """
    unmarked = _VERDICT_MARKER_RE.sub("", body).rstrip()
    return f"{unmarked}\n\n{verdict_marker(sha)}\n"


def marked_head(body: str) -> tuple[bool, str]:
    """Whether `body` carries a verdict marker, and the head it names.

    Returns `(marked, sha)`; `sha` is "" for the bare marker or no marker.
    When a body carries several markers the last one counts — the stamp is
    appended at the end.
    """
    matches = list(_VERDICT_MARKER_RE.finditer(body))
    if not matches:
        return False, ""
    return True, matches[-1].group("sha") or ""


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
    * `url` — the comment's `url` (empty when the source comment carried none);
      lets a consumer link back to the exact comment — e.g. `done-work`'s
      per-reviewer-override audit pointing at the block comment it waived
      (project-management:DEC-050).
    * `sha` — the PR head the reviewer was shown, named by the verdict marker
      (#1179); empty when the marker names none.
    """

    reviewer: str
    token: str
    path: str
    body: str
    timestamp: str
    url: str = ""
    sha: str = ""


def latest_commit_timestamp(commits: list) -> str:
    """The PR head commit's timestamp — the freshness anchor for a verdict
    that names no reviewed head (DEC-028 "Stale-verdict handling").

    `commits` is the `gh pr view --json commits` array, oldest first, so the
    last entry is the head; its `committedDate` (falling back to
    `authoredDate`) is the instant such a verdict must post-date to be fresh.
    Returns "" when no timestamp is resolvable: the gate then refuses, and the
    freshness rule holds a verdict that names no head stale.
    """
    if not commits:
        return ""
    last = commits[-1]
    if not isinstance(last, dict):
        return ""
    return str(last.get("committedDate") or last.get("authoredDate") or "")


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


def all_verdicts(
    comments: list,
    *,
    remote_reviewer_ok: Callable[[str], bool] = lambda _login: True,
    local_reviewer_ok: Callable[[str], bool] = lambda _name: True,
    is_fresh: Callable[[Verdict], bool] | None = None,
    require_marker: bool = False,
) -> list[Verdict]:
    """Every recognised DEC-028 verdict on a PR, in posting order.

    The full sequence behind `latest_verdicts_per_reviewer`'s reduction: the
    same recognition (`parse_verdict_line` on the comment's first line) and the
    same injected filters (marker, reviewer predicates, freshness — see
    `latest_verdicts_per_reviewer` for their semantics), but nothing is
    collapsed — a verdict a later round superseded is still returned. This is
    what `show-pr --field review-history` reads to show earlier review rounds
    (issue #905).

    Its defaults are the same permissive read-surface defaults as
    `latest_verdicts_per_reviewer`, and NOT safe for the merge gate; a gate
    path goes through `gate_verdicts`.

    Posting order is by `createdAt` (ISO-8601 UTC, string-comparable). The sort
    is stable, so verdicts with an identical timestamp keep `gh`'s array order —
    which is what lets `reduce_latest_per_reviewer` keep the first-seen verdict
    on an exact tie, as the latest-per-reviewer selection always has.
    """
    verdicts: list[Verdict] = []
    for comment in comments:
        if not isinstance(comment, dict):
            continue
        body = comment.get("body") or ""
        first_line = body.split("\n", 1)[0].strip()
        token, path, name = parse_verdict_line(first_line)
        if token is None:
            continue

        # Gate path (#593): only a marker-carrying verdict counts, so a bare
        # verdict-grammar line posted by any non-reviewer path never gates.
        marked, sha = marked_head(body)
        if require_marker and not marked:
            continue

        if path == PATH_REMOTE:
            reviewer = (comment.get("author") or {}).get("login") or ""
            if not remote_reviewer_ok(reviewer):
                continue
        else:
            reviewer = name or ""
            if not local_reviewer_ok(reviewer):
                continue

        verdict = Verdict(
            reviewer=reviewer,
            token=token,
            path=path,
            body=body,
            timestamp=str(comment.get("createdAt") or ""),
            url=str(comment.get("url") or ""),
            sha=sha,
        )
        # Freshness last: it may read the repository (`_lib.verdict_freshness`),
        # so it runs only for a verdict every other filter kept.
        if is_fresh is not None and not is_fresh(verdict):
            continue
        verdicts.append(verdict)

    return sorted(verdicts, key=lambda v: v.timestamp)


def reduce_latest_per_reviewer(verdicts: list[Verdict]) -> list[Verdict]:
    """Collapse a verdict sequence to the latest verdict per reviewer.

    The "latest by timestamp" rule (DEC-028 step 5), stated once. A reviewer is
    keyed by `(path, reviewer)` so a remote and a local verdict from names that
    happen to collide never overwrite each other. Strict `>` keeps the
    first-seen verdict on an exact tie (deterministic). Returns the input's own
    `Verdict` objects (no copies), so a caller holding the full sequence can
    tell by identity which entry is each reviewer's current verdict. Ordered by
    reviewer identity for deterministic output.
    """
    latest: dict[tuple[str, str], Verdict] = {}
    for verdict in verdicts:
        key = (verdict.path, verdict.reviewer)
        prior = latest.get(key)
        # ISO-8601 (UTC `Z`) timestamps compare correctly as strings.
        if prior is None or verdict.timestamp > prior.timestamp:
            latest[key] = verdict
    return sorted(latest.values(), key=lambda v: (v.path, v.reviewer))


def latest_verdicts_per_reviewer(
    comments: list,
    *,
    remote_reviewer_ok: Callable[[str], bool] = lambda _login: True,
    local_reviewer_ok: Callable[[str], bool] = lambda _name: True,
    is_fresh: Callable[[Verdict], bool] | None = None,
    require_marker: bool = False,
) -> list[Verdict]:
    """Collapse a PR's comments to the latest verdict per reviewer (DEC-028).

    This is the permissive *read-surface* primitive: `show-pr --field review`
    calls it directly to show every posted verdict (latest per reviewer). Its
    defaults are deliberately permissive — no freshness filter, allow-all
    membership — because a read surface shows whatever verdicts exist. Those
    defaults are NOT safe for the merge gate: a caller that wants gate
    semantics must go through `gate_verdicts` (below), whose freshness and
    membership filters are required, non-defaulted arguments. Do not call this
    primitive from a gate path — the permissive default would silently count
    every verdict from anyone at any age (self-approval included).

    Recognises the DEC-028 verdict shapes in `comments` (the
    `gh pr view --json comments` array) via `all_verdicts`, then reduces them
    with `reduce_latest_per_reviewer` to the latest verdict *per reviewer*,
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
      * `is_fresh` — when set, only verdicts it holds fresh are considered
        (the freshness predicate, `_lib.verdict_freshness`). It is applied
        before the latest-per-reviewer reduction, so the gate takes a
        reviewer's latest *fresh* verdict (DEC-028 step 4, then step 5).
        `show-pr` leaves it `None` — a stale verdict is still the reviewer's
        current verdict to *display*, marked stale by the same predicate.

    A reviewer is keyed by `(path, reviewer)` so a remote and a local verdict
    from names that happen to collide never overwrite each other. The returned
    list is ordered by reviewer identity for deterministic output.
    """
    return reduce_latest_per_reviewer(
        all_verdicts(
            comments,
            remote_reviewer_ok=remote_reviewer_ok,
            local_reviewer_ok=local_reviewer_ok,
            is_fresh=is_fresh,
            require_marker=require_marker,
        )
    )


def gate_verdicts(
    comments: list,
    *,
    is_fresh: Callable[[Verdict], bool],
    local_reviewer_ok: Callable[[str], bool],
    remote_reviewer_ok: Callable[[str], bool],
) -> list[Verdict]:
    """Strict, gate-facing verdict selection for the merge gate (DEC-028).

    Like `latest_verdicts_per_reviewer`, but the security-relevant filters are
    REQUIRED (non-defaulted) keyword arguments, and it additionally requires the
    verdict marker (`require_marker=True`, #593) — there is no way to call this
    permissively. That makes the fail-open default of the read-surface primitive
    unreachable from the gate path: the gate's correctness no longer depends on
    `done-work` *remembering* to inject a freshness predicate and
    membership/author-exclusion predicates; forgetting one is a `TypeError` at
    the call site, not a silently weakened gate.

    The marker filter (#593) closes the read side of the DEC-047 spoof: a bare
    verdict-grammar line — however it reached the PR — counts only if the
    reviewer path stamped it with a verdict marker.

      * `is_fresh` — the freshness predicate (`_lib.verdict_freshness`); only
        verdicts it holds fresh count (DEC-028 step 4). Required so a stale
        APPROVED can never slip through as fresh.
      * `local_reviewer_ok` / `remote_reviewer_ok` — membership predicates
        scoping the count to the resolved required set (and excluding the PR
        author on the remote path, DEC-028 step 3). Required so a verdict from
        an unrequired identity (self-approval included) can never count.
    """
    return latest_verdicts_per_reviewer(
        comments,
        is_fresh=is_fresh,
        local_reviewer_ok=local_reviewer_ok,
        remote_reviewer_ok=remote_reviewer_ok,
        require_marker=True,
    )
