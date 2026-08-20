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
manifest-walk + per-issue union (`reviewers_for_issues`) and the floor-match
seam (`reviewers_for_floors`). This module adds the layer above it the two
consumers share:

  * fetching the PR's closing-issue classifications — keyed on the
    `workstream` and `type` axes (DEC-032 amendment) — and, when a
    floor-carrying contribution is installed, the PR's changed files (the
    `gh` round-trips),
  * the fail-closed distinction between "PR closes no classified issue"
    (legitimate baseline-only) and "could not determine what the PR closes"
    (UNKNOWN → fail closed) — the `Unresolvable` sentinel,
  * unioning the baseline local names with the matched contributed reviewers
    (classification-matched ∪ floor-matched) and de-duplicating, preserving
    baseline-first order.

Fail-closed posture (DEC-032 D5)
--------------------------------

Resolution can fail in three structurally distinct ways, and the result type
makes a consumer handle each before reading the set:

  * **collection not ok** — a malformed contribution declaration or an
    installed contribution naming an undeployed agent. The collection's
    errors are surfaced; the required set is unsatisfiable, not smaller.
  * **closing-issue resolution unresolvable** — a transient `gh` failure
    resolving `closingIssuesReferences`, malformed JSON, an unreadable
    closing issue's labels, or invalid multi-value data on a
    mutually-exclusive axis. Ground truth for *what the PR closes* is
    unknown, so a contributed reviewer it might require cannot be dropped.
  * **changed-files resolution unresolvable** — a transient `gh` failure
    determining the PR's diff *while a floor-carrying contribution is
    installed*. Ground truth for *what the diff touches* is unknown, so a
    floor reviewer it might require cannot be dropped. A floor-free collection
    never fetches the diff, so this failure is unreachable there.

All collapse to `Resolution.ok is False` with a structured `error` the
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
from pathlib import Path, PurePosixPath
from typing import Callable

from _lib import axis_labels

try:
    from _lib.review_contributions import (
        ContributionCollection,
        ContributionRule,
        FLOOR_TOUCHES_CODE,
        collect_contributions as _default_collect_contributions,
    )
except ImportError:  # pragma: no cover - exercised via spec-loaded fallback
    from review_contributions import (  # type: ignore[no-redef]
        ContributionCollection,
        ContributionRule,
        FLOOR_TOUCHES_CODE,
        collect_contributions as _default_collect_contributions,
    )


# Classification axes the required-reviewer resolution keys contributed
# match-predicates on (DEC-012), read off a closing issue's `<axis>:<value>`
# labels via the `axis_labels` seam. Both are `mutually_exclusive`, so each is
# single-valued per issue (the multi-value guard below is per-axis). The
# DEC-032 amendment added `type` alongside `workstream`; this is the single
# place to widen when a further mutually-exclusive axis is keyed. It mirrors
# `review_contributions.SUPPORTED_MATCH_AXES` — the collector validates which
# axes a rule may name; this reads those same axes off the issue.
CLASSIFICATION_AXES = ("workstream", "type")


# ---- failure kinds (structured, not string-matched) ------------------

# The contribution collection surfaced a blocking error (malformed
# declaration, undeployed contributed agent). `collection` carries the
# detail; the consumer shapes a refusal from `collection.errors`.
ERROR_COLLECTION = "collection-error"
# Ground truth for what the PR closes (or a closing issue's labels) could
# not be established — a transient gh failure / malformed JSON / invalid
# label data. The required set is UNKNOWN, so the consumer fails closed.
ERROR_CLOSING_ISSUES = "closing-issues-unresolvable"
# The PR's changed files could not be established (a transient gh failure /
# malformed JSON) while a floor-carrying contribution is installed. A floor
# reviewer it might require cannot be dropped, so the consumer fails closed.
# Only reached when a floor-carrying rule exists — floor-free collections
# never fetch the diff (DEC-032 amendment).
ERROR_CHANGED_FILES = "changed-files-unresolvable"


@dataclass(frozen=True)
class RequiredReviewersError:
    """A structured reason the required set could not be resolved (DEC-032 D5).

    `kind` is `ERROR_COLLECTION`, `ERROR_CLOSING_ISSUES`, or
    `ERROR_CHANGED_FILES` so a consumer can branch on the failure class
    without string-matching `message`. For a collection error, `collection`
    is the failing `ContributionCollection` (its `errors` drive the
    consumer's refusal text); for a closing-issue or changed-files failure it
    is `None` and `message` carries the human-readable reason.
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


class _MultiValueAxisError(Exception):
    """An issue carries multiple values on a `mutually_exclusive` axis (DEC-012).

    Both keyed axes (`workstream`, `type`) are `mutually_exclusive: true` per
    `classification.yaml`, so at most one value is valid on an issue. More than
    one is invalid upstream label data; the resolver refuses to guess which
    value's contributed reviewer to honour (silently picking one would drop the
    others — fail-open). Surfaced as a fail-closed reason. `axis` names the
    offending axis so the message points the operator at the right labels.
    """

    def __init__(self, axis: str, values: list[str]):
        self.axis = axis
        self.values = values
        super().__init__(
            f"issue carries multiple {axis} labels: " + ", ".join(sorted(values))
        )


# Type of the injected closing-issue-numbers resolver. Returns the issue
# numbers the PR closes, or an `_Unresolvable` when ground truth is unknown.
ClosingIssueNumbersFn = Callable[[int], "list[int] | _Unresolvable"]
# Type of the injected per-issue label fetcher. Returns the issue's label
# list, or None when the labels could not be read (fetch failure).
IssueLabelsFn = Callable[[int], "list | None"]
# Type of the injected changed-files resolver. Returns the PR's changed-file
# paths, or an `_Unresolvable` when the diff could not be determined. Only
# called when a floor-carrying contribution is installed (DEC-032 amendment).
ChangedFilesFn = Callable[[int], "list[str] | _Unresolvable"]


def resolve_required_local_reviewers(
    pr_number: int,
    *,
    baseline_local: list[str],
    repo_root: Path,
    closing_issue_numbers: ClosingIssueNumbersFn,
    issue_labels: IssueLabelsFn,
    changed_files: ChangedFilesFn,
    collect_contributions: Callable[
        [Path], ContributionCollection
    ] = _default_collect_contributions,
) -> Resolution:
    """Resolve a PR's required-local-reviewer set (DEC-032 D1), fail-closed.

    This is the single resolution `done-work`'s gate-checker and `review-pr`
    both call, so the set the gate checks == the set `review-pr` invokes.

    `baseline_local` is the project's `review.agents.local_registered:` names
    (the union's baseline term). `repo_root` is the directory holding
    `.pkit/` (passed to the contribution collector). `closing_issue_numbers`,
    `issue_labels`, and `changed_files` are injected `gh`-backed callables
    (each consumer passes its own already-wired helpers); injecting them keeps
    this module free of substrate and unit-testable. `collect_contributions`
    is injectable for the same reason and defaults to the real collector.

    The contributed set is the UNION of two match paths (DEC-032 amendment):

      * **classification** — rules whose match-predicate holds for the
        classification (`workstream` / `type` axes) of any closing issue.
      * **diff-property floor** — floor-carrying rules whose floor the PR's
        diff satisfies (e.g. `touches-code`), independent of classification.
        This backstops D1's classification gate-escape for floor-carrying
        reviewers: a diff that touches code pulls in the floor reviewer even
        for a `type:docs` / unclassified PR.

    Returns a `Resolution`. On `ok`, `required_local` is the de-duplicated
    baseline-∪-contributed set; on failure (`ok is False`), `error` carries
    the fail-closed reason (DEC-032 D5) and the set fields are empty.

    Order of the fail-closed checks: the collection is gated FIRST (a
    malformed declaration or undeployed contributed agent is unsatisfiable
    regardless of what the PR closes), then closing-issue resolution, then —
    only when a floor-carrying contribution is installed — changed-files
    resolution. Any failing yields a non-ok `Resolution`. A collection with no
    floor-carrying rule never fetches the diff, so a floor-free project pays
    no extra `gh` round-trip and cannot fail on a diff it does not consult.
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

    classification_rules = collection.reviewers_for_issues(classifications)

    floor_rules = _floor_rules(collection, pr_number, changed_files=changed_files)
    if isinstance(floor_rules, _Unresolvable):
        return Resolution(
            error=RequiredReviewersError(
                kind=ERROR_CHANGED_FILES,
                message=floor_rules.reason,
            )
        )

    contributed_rules = _dedup_rules_by_reviewer(
        list(classification_rules) + list(floor_rules)
    )
    required_local = _dedup_preserve_order(
        list(baseline_local) + [rule.reviewer for rule in contributed_rules]
    )
    contributed_by = {rule.reviewer: rule.capability for rule in contributed_rules}
    return Resolution(
        required_local=required_local,
        contributed_rules=contributed_rules,
        contributed_by=contributed_by,
    )


def _floor_rules(
    collection: ContributionCollection,
    pr_number: int,
    *,
    changed_files: ChangedFilesFn,
) -> "tuple[ContributionRule, ...] | _Unresolvable":
    """Floor-carrying rules the PR's diff satisfies (DEC-032 amendment).

    Short-circuits when no installed contribution carries a floor — a
    floor-free project never fetches the diff (no extra `gh` round-trip, and no
    way to fail on a diff it does not consult). Otherwise it resolves the PR's
    changed files and maps them to the set of satisfied floor kinds, then asks
    the collection which floor-carrying rules that set matches.

    Returns `_Unresolvable` when the diff could not be determined while a floor
    rule is installed — a floor reviewer it might require cannot be dropped, so
    the caller fails closed (mirroring the closing-issue posture, DEC-032 D5).
    """
    if not any(rule.floor is not None for rule in collection.rules):
        return ()
    files = changed_files(pr_number)
    if isinstance(files, _Unresolvable):
        return files
    satisfied_floors = _satisfied_floors(files)
    return collection.reviewers_for_floors(satisfied_floors)


def _satisfied_floors(changed_paths: list[str]) -> set[str]:
    """The set of floor kinds the PR's changed files satisfy (DEC-032 amendment).

    Maps the raw diff to the abstract floor-kind vocabulary the collection
    matches on, keeping the collection ignorant of *how* a diff property is
    computed. Currently one floor kind: `touches-code`, satisfied when the diff
    touches code per `diff_touches_code`.
    """
    satisfied: set[str] = set()
    if diff_touches_code(changed_paths):
        satisfied.add(FLOOR_TOUCHES_CODE)
    return satisfied


# Filename suffixes that are ALWAYS code, regardless of directory — the
# dominant test of the `touches-code` classification (see `diff_touches_code`).
# A recognized source / config / schema / script suffix counts as code even
# under a `docs/` directory (e.g. `docs/conf.py`, `docs/deploy.sh`), so real
# code checked into a docs tree cannot slip past the floor. Centralised here so
# the definition is one edit away.
_CODE_SUFFIXES = frozenset({
    # source languages
    ".py", ".pyi", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs",
    ".go", ".rs", ".rb", ".java", ".kt", ".kts", ".scala", ".groovy",
    ".c", ".h", ".cc", ".cpp", ".cxx", ".hpp", ".hh", ".cs", ".swift",
    ".m", ".mm", ".php", ".pl", ".pm", ".lua", ".r", ".jl", ".dart",
    ".ex", ".exs", ".erl", ".clj", ".cljs", ".hs", ".ml", ".fs",
    ".vb", ".sql",
    # shell / batch scripts
    ".sh", ".bash", ".zsh", ".fish", ".ksh", ".ps1", ".psm1",
    ".bat", ".cmd",
    # configuration / data / schema
    ".yaml", ".yml", ".json", ".jsonc", ".toml", ".ini", ".cfg",
    ".conf", ".xml", ".env", ".properties", ".gradle",
})

# Filename suffixes treated as PURE DOCUMENTATION (not code) by the
# `touches-code` floor — but ONLY for a file whose suffix is not in
# `_CODE_SUFFIXES` (a code suffix always wins). A changed file with one of these
# suffixes does not, on its own, make a diff "touch code". `.txt` is
# deliberately absent: `requirements.txt` / `CMakeLists.txt` / `constraints.txt`
# are code-adjacent, so a bare `.txt` is left to fall through to the fail-closed
# code default rather than be demoted to docs.
_DOC_SUFFIXES = (".md", ".mdx", ".markdown", ".rst")

# Path segments (matched case-insensitively) that mark a DOCUMENTATION
# directory. A NON-code-suffixed file living under such a directory is demoted
# to documentation (e.g. an image or diagram under `docs/`). A code-suffixed
# file is code regardless — the `docs/` location never overrides a code suffix.
_DOC_DIR_SEGMENTS = ("docs",)


def diff_touches_code(changed_paths: list[str]) -> bool:
    """Whether the PR's diff touches code — the `touches-code` floor predicate.

    "Touches code" is defined as: **any changed file that is not purely
    documentation**. Classification is code-suffix-dominant and fail-closed, in
    three tiers evaluated per file:

      1. A recognized code suffix (`.py`, `.ts`, `.yaml`, `.json`, `.sh`, … —
         source, config, schema, script) is ALWAYS code, regardless of
         directory. `docs/conf.py` and `docs/deploy.sh` are code, so real code
         checked into a docs tree cannot escape the floor.
      2. Otherwise, a documentation suffix (`.md` / `.mdx` / `.markdown` /
         `.rst`) OR a file under a `docs/` directory (matched
         case-insensitively) is documentation — this is where a non-code asset
         like `docs/img/diagram.png` is demoted.
      3. Otherwise (an unknown suffix, or an extensionless file) → **code**, the
         fail-closed default: when in doubt, the floor fires so the diff is not
         silently waved through unreviewed.

    A conscious call: config/schema changes count as code (a reviewer mandated
    on code-carrying PRs should see a changed `*.yaml`/`*.json`), and a diff
    mixing docs with any code file touches code (the presence of one code file
    is enough — a docs-only PR is the sole non-touching case). An empty diff (no
    changed files) does not touch code. The suffix sets are a small, central
    allow-list, easy to adjust as the panel's mandate sharpens (DEC-032
    amendment names this the genuine design point).
    """
    return any(not _is_documentation_path(path) for path in changed_paths)


def _is_documentation_path(path: str) -> bool:
    """True when `path` is purely documentation (see `diff_touches_code`).

    Code-suffix-dominant and fail-closed: a code suffix returns False (code)
    outright; only a non-code file that is doc-suffixed or under `docs/` returns
    True; any remaining unknown suffix returns False (the code default).
    """
    posix = PurePosixPath(path)
    suffix = posix.suffix.lower()
    if suffix in _CODE_SUFFIXES:
        return False
    if suffix in _DOC_SUFFIXES or _under_docs_dir(posix):
        return True
    return False


def _under_docs_dir(posix: PurePosixPath) -> bool:
    """Whether `posix` lives under a documentation directory (case-insensitive).

    `parts[:-1]` are the directory segments (excluding the filename), so a file
    merely NAMED `docs` is not mistaken for one living under `docs/`. Segment
    matching is case-folded so `Docs/` reads the same as `docs/`.
    """
    return any(
        segment.lower() in _DOC_DIR_SEGMENTS for segment in posix.parts[:-1]
    )


def _dedup_rules_by_reviewer(
    rules: list[ContributionRule],
) -> tuple[ContributionRule, ...]:
    """De-duplicate contributed rules by reviewer name, preserving first order.

    Unions the classification-matched and floor-matched rule lists: a reviewer
    required by both paths is required once, keeping the first rule seen (so
    classification provenance wins over a floor rule for the same reviewer).
    """
    seen: set[str] = set()
    out: list[ContributionRule] = []
    for rule in rules:
        if rule.reviewer not in seen:
            seen.add(rule.reviewer)
            out.append(rule)
    return tuple(out)


def _closing_issue_classifications(
    pr_number: int,
    *,
    closing_issue_numbers: ClosingIssueNumbersFn,
    issue_labels: IssueLabelsFn,
) -> "list[dict[str, str]] | _Unresolvable":
    """Classification mapping (e.g. `{workstream: design, type: feature}`) per closing issue.

    DEC-032 D1's resolution domain is total for the *determinable* cases: a
    PR closing multiple issues yields one mapping per issue (the caller
    unions them); a PR closing no classified issue yields an empty list →
    baseline only. A closing entity carrying none of the keyed axes (a
    sub-task or Milestone carries no classification per DEC-012) yields an
    empty mapping — matching nothing, so baseline only, the named
    classification gate-escape DEC-032 D1 calls out (backstopped, for a
    floor-carrying reviewer, by the diff-property floor).

    When ground truth cannot be established — `closingIssuesReferences`
    failed to resolve, a closing issue's labels could not be read, or invalid
    multi-value label data on a mutually-exclusive axis is present — the result
    is `_Unresolvable`, NOT an empty list. The two states are different per D1:
    "closes no classified issue" is legitimate fail-open; "could not determine"
    is UNKNOWN and must fail closed (the caller refuses). Collapsing the latter
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
        except _MultiValueAxisError as exc:
            return _Unresolvable(
                f"closing issue #{issue_number} has multiple {exc.axis} "
                f"labels ({', '.join(sorted(exc.values))}); DEC-012 declares "
                f"the {exc.axis} axis mutually exclusive — fix the labels"
            )
        if classification:
            classifications.append(classification)
    return classifications


def _classification_from_labels(labels: list) -> dict[str, str]:
    """Build the classification mapping from an issue's labels (DEC-012).

    Keys every axis in `CLASSIFICATION_AXES` (`workstream`, `type`). A
    `<axis>:*` label yields `{<axis>: <value>}`; an axis with no label is
    omitted (an entity carrying none of the axes yields `{}` → matching
    nothing → baseline only). Values are read through the `axis_labels` seam,
    the one place the `<axis>:<value>` encoding lives.

    **Single value per mutually-exclusive axis.** Both keyed axes are declared
    `mutually_exclusive: true` in `schemas/classification.yaml` (DEC-012), so
    at most one `<axis>:*` label is valid per axis on an issue. If an issue
    carries multiple distinct values on one axis (a label-discipline violation
    upstream), raise rather than silently pick one — silently dropping the
    others would skip a contributed reviewer required for a dropped value (the
    fail-open hole D5 guards against). A noisy failure surfaces the bad data;
    the operator fixes the labels (or `--bypass`). The guard is per-axis: a
    valid `type` and a broken multi-value `workstream` fail on the workstream.
    """
    names = [
        lbl.get("name", "") if isinstance(lbl, dict) else str(lbl)
        for lbl in labels
    ]
    classification: dict[str, str] = {}
    for axis in CLASSIFICATION_AXES:
        values: list[str] = []
        for value in axis_labels.read_all(axis, names):
            if value and value not in values:
                values.append(value)
        if not values:
            continue
        if len(values) > 1:
            raise _MultiValueAxisError(axis, values)
        classification[axis] = values[0]
    return classification


def _dedup_preserve_order(names: list[str]) -> tuple[str, ...]:
    """De-duplicate a name list, preserving first-seen order (DEC-032 D1)."""
    seen: set[str] = set()
    out: list[str] = []
    for name in names:
        if name not in seen:
            seen.add(name)
            out.append(name)
    return tuple(out)
