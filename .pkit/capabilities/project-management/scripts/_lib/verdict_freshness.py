"""When a reviewer's verdict still stands — the one freshness rule (#1179).

DEC-028 "Stale-verdict handling" states the rule; this module is its single
implementation, read by every consumer that has to tell a fresh verdict from
a stale one, so they cannot disagree:

  * `done-work`'s merge gate counts only fresh verdicts (`gate_verdicts`'
    required `is_fresh`) and names, in a refusal, what a stale one reviewed
    and what changed since;
  * `review-pr` skips a required reviewer whose latest verdict is fresh;
  * `show-pr --field review` / `review-history` mark a stale verdict, with
    the reason.

The rule, per verdict:

  * **A verdict naming the head it reviewed** (`<!-- pkit-verdict sha=<oid>
    -->`) stands until the author changes something its reviewer checks. The
    author's changes since that head come from `_lib.author_delta` (a clean
    merge of the base branch contributes nothing). A reviewer only a
    diff-property floor requires on this PR (`Resolution.floors_by_reviewer`)
    stays fresh while those changes satisfy none of its floors, read through
    the same not-code list the resolver applies; any other reviewer — the
    baseline, or one the closing issues' classification matched — goes stale
    on any change. When the changes cannot be computed the verdict is stale.
  * **A verdict naming no head** is fresh when it was posted strictly after
    the PR's latest commit, and stale otherwise — or when that commit's time
    is unknown.

Every outcome carries a one-line reason a consumer prints as it stands. The
rule is pure logic: the author's changes are read through an injected
callable, computed at most once per reviewed head.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass

try:
    from _lib.agent_verdicts import PATH_LOCAL, Verdict, latest_commit_timestamp
    from _lib.audit import short_sha
    from _lib.author_delta import AuthorDelta
    from _lib.required_reviewers import (
        DEFAULT_NOT_CODE,
        NotCode,
        Resolution,
        satisfied_floors,
    )
except ImportError:  # pragma: no cover - exercised via spec-loaded fallback
    from agent_verdicts import (  # type: ignore[no-redef]
        PATH_LOCAL,
        Verdict,
        latest_commit_timestamp,
    )
    from audit import short_sha  # type: ignore[no-redef]
    from author_delta import AuthorDelta  # type: ignore[no-redef]
    from required_reviewers import (  # type: ignore[no-redef]
        DEFAULT_NOT_CODE,
        NotCode,
        Resolution,
        satisfied_floors,
    )


# The `gh pr view --json` fields `rule_for_pr` reads; a consumer adds them to
# the fetch it already makes.
PR_VIEW_FIELDS = ("commits", "headRefOid", "baseRefOid")

# How many changed paths a reason names before counting the rest.
_PATHS_NAMED = 5


@dataclass(frozen=True)
class Freshness:
    """Whether a verdict stands, and why, in one line a consumer prints."""

    fresh: bool
    reason: str


# `(since) -> AuthorDelta`: the author's changes from a reviewed head to the
# PR's head.
DeltaFn = Callable[[str], AuthorDelta]


def _no_delta(_since: str) -> AuthorDelta:
    return AuthorDelta(error="the pull request's head is unknown")


class FreshnessRule:
    """The freshness rule for one PR at its current head.

    Every argument defaults to its fail-closed value: no head, no commit
    time, no floor-only reviewer, and no way to read the author's changes —
    under which no verdict is fresh.
    """

    def __init__(
        self,
        *,
        head_sha: str = "",
        head_timestamp: str = "",
        floors_by_reviewer: Mapping[str, frozenset[str]] | None = None,
        not_code: NotCode = DEFAULT_NOT_CODE,
        delta_since: DeltaFn = _no_delta,
    ) -> None:
        self._head_sha = head_sha
        self._head_timestamp = head_timestamp
        self._floors_by_reviewer = dict(floors_by_reviewer or {})
        self._not_code = not_code
        self._delta_since = delta_since
        self._deltas: dict[str, AuthorDelta] = {}

    def is_fresh(self, verdict: Verdict) -> bool:
        """The predicate `gate_verdicts` takes."""
        return self.assess(verdict).fresh

    def assess(self, verdict: Verdict) -> Freshness:
        if not verdict.sha:
            return self._by_commit_time(verdict)
        reviewed = short_sha(verdict.sha)
        if verdict.sha == self._head_sha:
            return Freshness(True, f"reviewed the current head {reviewed}")
        delta = self._delta(verdict.sha)
        if not delta.ok:
            return Freshness(
                False, f"reviewed {reviewed}; the changes since cannot be read: "
                f"{delta.error}",
            )
        if not delta.paths:
            return Freshness(
                True, f"reviewed {reviewed}; only merges of the base branch since"
            )
        changed = f"reviewed {reviewed}; changed since: {_name_paths(delta.paths)}"
        floors = self._floors_of(verdict)
        if floors is None:
            return Freshness(False, changed)
        reached = sorted(floors & satisfied_floors(delta.paths, self._not_code))
        if reached:
            return Freshness(False, f"{changed} — reaches its {', '.join(reached)} floor")
        return Freshness(
            True, f"{changed} — reaches none of its floors ({', '.join(sorted(floors))})"
        )

    def _by_commit_time(self, verdict: Verdict) -> Freshness:
        if not self._head_timestamp:
            return Freshness(
                False, "no reviewed head recorded; the latest commit's time is unknown"
            )
        if verdict.timestamp > self._head_timestamp:
            return Freshness(
                True, "no reviewed head recorded; posted after the latest commit"
            )
        return Freshness(
            False, "no reviewed head recorded; posted before the latest commit"
        )

    def _floors_of(self, verdict: Verdict) -> frozenset[str] | None:
        """The floors that keep this reviewer's verdict standing, or None when
        it is required for the whole change. Contributed reviewers register on
        the local path only (DEC-032), so a remote verdict is a baseline one."""
        if verdict.path != PATH_LOCAL:
            return None
        return self._floors_by_reviewer.get(verdict.reviewer)

    def _delta(self, sha: str) -> AuthorDelta:
        if sha not in self._deltas:
            self._deltas[sha] = self._delta_since(sha)
        return self._deltas[sha]


def head_sha(pr_view: Mapping) -> str:
    """The PR's head commit: `headRefOid`, else the last listed commit's oid."""
    head = str(pr_view.get("headRefOid") or "")
    if head:
        return head
    commits = pr_view.get("commits") or []
    last = commits[-1] if commits else None
    return str(last.get("oid") or "") if isinstance(last, dict) else ""


def rule_for_pr(
    pr_view: Mapping,
    resolution: Resolution,
    *,
    author_delta: Callable[..., AuthorDelta],
) -> FreshnessRule:
    """The freshness rule for a PR, from its `gh pr view` payload.

    `pr_view` carries at least `PR_VIEW_FIELDS`. `resolution` is the PR's
    resolved required set: its floor-only reviewers and its not-code list
    decide what reaches a floor. A failed resolution names no floor-only
    reviewer, so every verdict goes stale on any change. `author_delta` is
    `_lib.author_delta.author_delta`, passed by the consumer so its tests can
    stand it in.
    """
    head = head_sha(pr_view)
    base_tip = str(pr_view.get("baseRefOid") or "")
    return FreshnessRule(
        head_sha=head,
        head_timestamp=latest_commit_timestamp(pr_view.get("commits") or []),
        floors_by_reviewer=resolution.floors_by_reviewer,
        not_code=resolution.not_code,
        delta_since=lambda since: author_delta(since, head, base_tip=base_tip),
    )


def _name_paths(paths: tuple[str, ...]) -> str:
    named = ", ".join(paths[:_PATHS_NAMED])
    rest = len(paths) - _PATHS_NAMED
    return f"{named} (+{rest} more)" if rest > 0 else named
