"""A pull request's required reviewers and its freshness rule, wired once (#1195).

Three verbs judge a PR's reviewer verdicts, and they must agree on who has to
review it and on whether a verdict still stands:

  * `done-work`'s merge gate counts each required reviewer's fresh verdict;
  * `review-pr` invokes the required set and skips a reviewer whose verdict
    is fresh;
  * `show-pr --field review` / `review-history` mark a verdict stale exactly
    when the gate would not count it (ADR-042 D2).

Each used to wire the resolver by hand — the same closing-issue, label and
changed-files fetchers, the same opt-out and not-code reads, its own reading
of the baseline, the same PR view fields and the same `rule_for_pr` call — so
the agreement rested on three copies staying identical. This module is that
wiring: `resolve_pr_review` resolves the PR's required set
(`_lib.required_reviewers`) from the project config and returns it with the
freshness rule it keys (`_lib.verdict_freshness`), and `REVIEW_VIEW_FIELDS`
names what the rule and the verdict reading need from `gh pr view`.

The substrate stays injected, as in the modules this one composes: the `gh`
callables, the contribution collector and the author-change readers are
arguments, and each verb passes the names its own module imported. A verb's
tests patch those names on the verb's module, so the patches reach the
resolution and the rule.

The rule reads the PR's head, base and commits from its view, which
`done-work` and `review-pr` fetch only once the resolution has succeeded —
the gate after it has checked the per-reviewer overrides against the
resolved set, too. So the rule is completed from the view the verb fetched
(`PrReview.freshness_rule`), not fetched here: a refusal still comes before
the round trip.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from _lib.author_delta import AuthorDelta, BaseCheck
    from _lib.closing_issue_fetchers import (
        GhGetIssueFn,
        GhRunFn,
        issue_labels,
        pr_changed_files,
        pr_closing_issue_numbers,
    )
    from _lib.required_reviewers import (
        Resolution,
        read_not_code,
        resolve_required_local_reviewers,
    )
    from _lib.review_contributions import ContributionCollection
    from _lib.review_opt_outs import read_opt_outs
    from _lib.verdict_freshness import PR_VIEW_FIELDS, FreshnessRule, rule_for_pr
except ImportError:  # pragma: no cover - exercised via spec-loaded fallback
    from author_delta import AuthorDelta, BaseCheck  # type: ignore[no-redef]
    from closing_issue_fetchers import (  # type: ignore[no-redef]
        GhGetIssueFn,
        GhRunFn,
        issue_labels,
        pr_changed_files,
        pr_closing_issue_numbers,
    )
    from required_reviewers import (  # type: ignore[no-redef]
        Resolution,
        read_not_code,
        resolve_required_local_reviewers,
    )
    from review_contributions import ContributionCollection  # type: ignore[no-redef]
    from review_opt_outs import read_opt_outs  # type: ignore[no-redef]
    from verdict_freshness import (  # type: ignore[no-redef]
        PR_VIEW_FIELDS,
        FreshnessRule,
        rule_for_pr,
    )


# The `gh pr view --json` fields a PR's verdicts are judged from: the comments
# they are posted in, and what the freshness rule reads. A verb adds the
# fields it needs for itself to these.
REVIEW_VIEW_FIELDS = ("comments", *PR_VIEW_FIELDS)


@dataclass(frozen=True)
class PrReview:
    """A PR's resolved required reviewers, and the freshness rule they key.

    `resolution` is the required set, or the fail-closed reason it could not
    be resolved (DEC-032 D5) — a verb checks `resolution.ok` before acting on
    the set. `author_delta` and `base_kept` are `_lib.author_delta`'s, as the
    verb passed them in.
    """

    resolution: Resolution
    author_delta: Callable[..., AuthorDelta]
    base_kept: Callable[..., BaseCheck]

    def freshness_rule(self, pr_view: Mapping) -> FreshnessRule:
        """The freshness rule for the PR at the head `pr_view` reports.

        `pr_view` carries at least `REVIEW_VIEW_FIELDS`. A resolution that
        failed names no floor-scoped reviewer, so under it every verdict goes
        stale on any change.
        """
        return rule_for_pr(
            pr_view,
            self.resolution,
            author_delta=self.author_delta,
            base_kept=self.base_kept,
        )


def resolve_pr_review(
    pr_number: int,
    config: dict,
    repo_root: Path,
    *,
    gh_run: GhRunFn,
    gh_get_issue: GhGetIssueFn,
    collect_contributions: Callable[[Path], ContributionCollection],
    author_delta: Callable[..., AuthorDelta],
    base_kept: Callable[..., BaseCheck],
) -> PrReview:
    """Resolve PR `pr_number`'s required reviewers, with their freshness rule.

    The required set is DEC-032 D1's: the baseline under
    `review.agents.local_registered:` united with every contributed reviewer
    the PR's closing issues or its diff require, less the opt-outs, the diff
    read through the not-code list — all read from `config`, the adopter's pm
    config. `repo_root` is the directory holding `.pkit/`, where
    `collect_contributions` finds the installed contributions.

    `gh_run` and `gh_get_issue` (`_lib.gh`'s) feed the closing-issue, label
    and changed-files fetchers; `author_delta` and `base_kept` are what the
    freshness rule reads the author's changes and the base's history through.
    """
    resolution = resolve_required_local_reviewers(
        pr_number,
        baseline_local=_baseline_local(config),
        repo_root=repo_root,
        closing_issue_numbers=lambda n: pr_closing_issue_numbers(n, config, gh_run=gh_run),
        issue_labels=lambda n: issue_labels(n, config, gh_get_issue=gh_get_issue),
        changed_files=lambda n: pr_changed_files(n, config, gh_run=gh_run),
        opt_outs=read_opt_outs(config),
        not_code=read_not_code(config),
        collect_contributions=collect_contributions,
    )
    return PrReview(resolution, author_delta=author_delta, base_kept=base_kept)


def _baseline_local(config: Any) -> list[str]:
    """The baseline term of the required set: each named entry under
    `review.agents.local_registered:`, in order."""
    review = config.get("review") if isinstance(config, dict) else None
    agents = review.get("agents") if isinstance(review, dict) else None
    registered = (agents.get("local_registered") if isinstance(agents, dict) else None) or []
    return [
        entry.get("name") for entry in registered if isinstance(entry, dict) and entry.get("name")
    ]
