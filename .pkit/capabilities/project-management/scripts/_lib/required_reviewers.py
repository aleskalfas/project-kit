"""Per-PR required-local-reviewer resolution (per project-management:DEC-032 D1).

DEC-032 D1 fixes the required *local*-reviewer set for a PR as:

    baseline (the project's `review.agents.local_registered:`)
      ∪ every contributed reviewer whose match-predicate matches the
        classification of ANY issue the PR closes

de-duplicated by reviewer name. Two consumers depend on resolving *exactly*
this set, and DEC-032's whole point is that the resolution is "owned once so
the consumers can't diverge":

  * `done-work`'s agent-mode gate (#145) checks the set has a fresh APPROVED.
  * `review-pr` (#147) INVOKES the set so the developer-at-keyboard flow
    produces precisely the verdicts the gate then checks.

If `review-pr` resolved a different set than the gate, a developer could run
`review-pr`, see every invoked agent approve, and still hit a gate refusal
(or worse, the inverse). This module is the single resolution both call, so
invoke-set == gate-set by construction.

The collector (`_lib.review_contributions`) already owns the
manifest-walk + per-issue union (`reviewers_for_issues`). This module adds
the layer above it the two consumers share:

  * fetching the PR's closing-issue classifications (the `gh` round-trips),
  * the fail-closed distinction between "PR closes no classified issue"
    (legitimate baseline-only) and "could not determine what the PR closes"
    (UNKNOWN → fail closed) — the `Unresolvable` sentinel,
  * unioning the baseline local names with the matched contributed reviewers
    and de-duplicating, preserving baseline-first order.

Fail-closed posture (DEC-032 D5)
--------------------------------

Resolution can fail in two structurally distinct ways, and the result type
makes a consumer handle both before reading the set:

  * **collection not ok** — a malformed contribution declaration or an
    installed contribution naming an undeployed agent. The collection's
    errors are surfaced; the required set is unsatisfiable, not smaller.
  * **closing-issue resolution unresolvable** — a transient `gh` failure
    resolving `closingIssuesReferences`, malformed JSON, an unreadable
    closing issue's labels, or invalid multi-workstream label data. Ground
    truth for *what the PR closes* is unknown, so a contributed reviewer it
    might require cannot be dropped.

Both collapse to `Resolution.ok is False` with a structured `error` the
consumer turns into its own refusal / error message. An *empty* contributed
set with `ok is True` is the legitimate baseline-only branch (DEC-032 D1),
distinct from either failure.

This module owns NO output formatting and NO substrate (`gh`) wiring of its
own — the `gh` callables are injected, mirroring `review_contributions`'s
injectable `load_yaml` / `agent_is_deployed`. That keeps it pure-logic and
unit-testable without a live repo or GitHub, and lets each consumer keep its
own already-imported `gh` helpers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from _lib import axis_labels

try:
    from _lib.review_contributions import (
        ContributionCollection,
        ContributionRule,
        collect_contributions as _default_collect_contributions,
    )
except ImportError:  # pragma: no cover - exercised via spec-loaded fallback
    from review_contributions import (  # type: ignore[no-redef]
        ContributionCollection,
        ContributionRule,
        collect_contributions as _default_collect_contributions,
    )


# `workstream:*` label prefix (DEC-012 classification axis). The required-
# reviewer resolution keys contributed match-predicates on the `workstream`
# axis, read off a closing issue's `workstream:<value>` label. Single place
# to widen when a second axis is keyed.
WORKSTREAM_LABEL_PREFIX = axis_labels.prefix("workstream")


# ---- failure kinds (structured, not string-matched) ------------------

# The contribution collection surfaced a blocking error (malformed
# declaration, undeployed contributed agent). `collection` carries the
# detail; the consumer shapes a refusal from `collection.errors`.
ERROR_COLLECTION = "collection-error"
# Ground truth for what the PR closes (or a closing issue's labels) could
# not be established — a transient gh failure / malformed JSON / invalid
# label data. The required set is UNKNOWN, so the consumer fails closed.
ERROR_CLOSING_ISSUES = "closing-issues-unresolvable"


@dataclass(frozen=True)
class RequiredReviewersError:
    """A structured reason the required set could not be resolved (DEC-032 D5).

    `kind` is `ERROR_COLLECTION` or `ERROR_CLOSING_ISSUES` so a consumer can
    branch on the failure class without string-matching `message`. For a
    collection error, `collection` is the failing `ContributionCollection`
    (its `errors` drive the consumer's refusal text); for a closing-issue
    failure it is `None` and `message` carries the human-readable reason.
    """

    kind: str
    message: str
    collection: ContributionCollection | None = None


@dataclass(frozen=True)
class Resolution:
    """The resolved per-PR required-local-reviewer set, or a fail-closed error.

    On success (`ok is True`):
      * `required_local` — the baseline local names UNIONED with the matched
        contributed reviewers, de-duplicated, baseline-first (DEC-032 D1).
        This is the set both `done-work` and `review-pr` act on.
      * `contributed_rules` — the matched contributed `ContributionRule`s (a
        subset, carrying provenance: which capability required each, and the
        deploy-resolution status). Empty for the baseline-only branch.
      * `contributed_by` — reviewer-name → contributing-capability map, for
        provenance in messages (baseline reviewers are absent from it).

    On failure (`ok is False`): `error` is populated and the set fields are
    empty. The two failure kinds are both fail-closed per DEC-032 D5.
    """

    required_local: tuple[str, ...] = ()
    contributed_rules: tuple[ContributionRule, ...] = ()
    contributed_by: dict[str, str] = field(default_factory=dict)
    error: RequiredReviewersError | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


class _Unresolvable:
    """Sentinel: a closing-issue resolution step could not establish ground truth.

    Distinct from an *empty* classification list. An empty list means "we
    determined the PR closes no classified issue" — DEC-032 D1's named,
    intended baseline-only branch (legitimate fail-open). `_Unresolvable`
    means "we could not determine what the PR closes / could not read an
    issue's labels" (transient gh failure / malformed JSON / invalid label
    data) — which must fail *closed*, never collapse to baseline-only and
    silently drop a genuinely-required contributed reviewer.
    """

    def __init__(self, reason: str):
        self.reason = reason


class _MultiWorkstreamError(Exception):
    """An issue carries multiple `workstream:*` labels (DEC-012 forbids this).

    `workstream` is `mutually_exclusive: true` per `classification.yaml`. More
    than one value is invalid upstream label data; the resolver refuses to
    guess which workstream's contributed reviewer to honour (silently picking
    one would drop the others — fail-open). Surfaced as a fail-closed reason.
    """

    def __init__(self, values: list[str]):
        self.values = values
        super().__init__(
            "issue carries multiple workstream labels: "
            + ", ".join(sorted(values))
        )


# Type of the injected closing-issue-numbers resolver. Returns the issue
# numbers the PR closes, or an `_Unresolvable` when ground truth is unknown.
ClosingIssueNumbersFn = Callable[[int], "list[int] | _Unresolvable"]
# Type of the injected per-issue label fetcher. Returns the issue's label
# list, or None when the labels could not be read (fetch failure).
IssueLabelsFn = Callable[[int], "list | None"]


def resolve_required_local_reviewers(
    pr_number: int,
    *,
    baseline_local: list[str],
    repo_root: Path,
    closing_issue_numbers: ClosingIssueNumbersFn,
    issue_labels: IssueLabelsFn,
    collect_contributions: Callable[
        [Path], ContributionCollection
    ] = _default_collect_contributions,
) -> Resolution:
    """Resolve a PR's required-local-reviewer set (DEC-032 D1), fail-closed.

    This is the single resolution `done-work`'s gate-checker and `review-pr`
    both call, so the set the gate checks == the set `review-pr` invokes.

    `baseline_local` is the project's `review.agents.local_registered:` names
    (the union's baseline term). `repo_root` is the directory holding
    `.pkit/` (passed to the contribution collector). `closing_issue_numbers`
    and `issue_labels` are injected `gh`-backed callables (each consumer
    passes its own already-wired helpers); injecting them keeps this module
    free of substrate and unit-testable. `collect_contributions` is injectable
    for the same reason and defaults to the real collector.

    Returns a `Resolution`. On `ok`, `required_local` is the de-duplicated
    baseline-∪-contributed set; on failure (`ok is False`), `error` carries
    the fail-closed reason (DEC-032 D5) and the set fields are empty.

    Order of the two fail-closed checks: the collection is gated FIRST (a
    malformed declaration or undeployed contributed agent is unsatisfiable
    regardless of what the PR closes), then closing-issue resolution. Either
    failing yields a non-ok `Resolution`.
    """
    collection = collect_contributions(repo_root)
    if not collection.ok:
        return Resolution(
            error=RequiredReviewersError(
                kind=ERROR_COLLECTION,
                message="reviewer contribution collection failed",
                collection=collection,
            )
        )

    classifications = _closing_issue_classifications(
        pr_number,
        closing_issue_numbers=closing_issue_numbers,
        issue_labels=issue_labels,
    )
    if isinstance(classifications, _Unresolvable):
        return Resolution(
            error=RequiredReviewersError(
                kind=ERROR_CLOSING_ISSUES,
                message=classifications.reason,
            )
        )

    contributed_rules = collection.reviewers_for_issues(classifications)
    required_local = _dedup_preserve_order(
        list(baseline_local) + [rule.reviewer for rule in contributed_rules]
    )
    contributed_by = {rule.reviewer: rule.capability for rule in contributed_rules}
    return Resolution(
        required_local=required_local,
        contributed_rules=contributed_rules,
        contributed_by=contributed_by,
    )


def _closing_issue_classifications(
    pr_number: int,
    *,
    closing_issue_numbers: ClosingIssueNumbersFn,
    issue_labels: IssueLabelsFn,
) -> "list[dict[str, str]] | _Unresolvable":
    """Classification mapping (e.g. `{workstream: design}`) per closing issue.

    DEC-032 D1's resolution domain is total for the *determinable* cases: a
    PR closing multiple issues yields one mapping per issue (the caller
    unions them); a PR closing no classified issue yields an empty list →
    baseline only. A closing entity with no `workstream:*` label (a sub-task
    or Milestone carries no classification per DEC-012) yields an empty
    mapping — matching nothing, so baseline only, the named gate-escape
    DEC-032 D1 calls out.

    When ground truth cannot be established — `closingIssuesReferences`
    failed to resolve, a closing issue's labels could not be read, or invalid
    multi-workstream label data is present — the result is `_Unresolvable`,
    NOT an empty list. The two states are different per D1: "closes no
    classified issue" is legitimate fail-open; "could not determine" is
    UNKNOWN and must fail closed (the caller refuses). Collapsing the latter
    to baseline-only is a retry-/induce-able bypass of a required reviewer.
    """
    closing_numbers = closing_issue_numbers(pr_number)
    if isinstance(closing_numbers, _Unresolvable):
        return closing_numbers
    classifications: list[dict[str, str]] = []
    for issue_number in closing_numbers:
        labels = issue_labels(issue_number)
        if labels is None:
            # Could not read this issue's labels — its classification is
            # UNKNOWN, so a contributed reviewer it might require cannot be
            # dropped. Fail closed rather than treat as "no classification".
            return _Unresolvable(
                f"could not read labels for closing issue #{issue_number}"
            )
        try:
            classification = _classification_from_labels(labels)
        except _MultiWorkstreamError as exc:
            return _Unresolvable(
                f"closing issue #{issue_number} has multiple workstream "
                f"labels ({', '.join(sorted(exc.values))}); DEC-012 declares "
                "the workstream axis mutually exclusive — fix the labels"
            )
        if classification:
            classifications.append(classification)
    return classifications


def _classification_from_labels(labels: list) -> dict[str, str]:
    """Build the classification mapping from an issue's labels (DEC-012).

    Only the `workstream` axis is keyed at v1 (DEC-032 D1). A `workstream:*`
    label yields `{workstream: <value>}`; no such label yields `{}` (matching
    nothing → baseline only).

    **Single workstream per issue.** The `workstream` axis is declared
    `mutually_exclusive: true` in `schemas/classification.yaml` (DEC-012), so
    at most one `workstream:*` label is valid on an issue. If an issue somehow
    carries multiple distinct `workstream:*` labels (a label-discipline
    violation upstream), raise rather than silently pick one — silently
    dropping the others would skip a contributed reviewer required for a
    dropped workstream (the fail-open hole D5 guards against). A noisy failure
    surfaces the bad data; the operator fixes the labels (or `--bypass`).
    """
    values: list[str] = []
    for lbl in labels:
        name = lbl.get("name", "") if isinstance(lbl, dict) else str(lbl)
        if name.startswith(WORKSTREAM_LABEL_PREFIX):
            value = name[len(WORKSTREAM_LABEL_PREFIX):]
            if value and value not in values:
                values.append(value)
    if not values:
        return {}
    if len(values) > 1:
        raise _MultiWorkstreamError(values)
    return {"workstream": values[0]}


def _dedup_preserve_order(names: list[str]) -> tuple[str, ...]:
    """De-duplicate a name list, preserving first-seen order (DEC-032 D1)."""
    seen: set[str] = set()
    out: list[str] = []
    for name in names:
        if name not in seen:
            seen.add(name)
            out.append(name)
    return tuple(out)
