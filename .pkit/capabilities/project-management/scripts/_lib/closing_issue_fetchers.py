"""Shared `gh`-backed PR-data fetchers for required-reviewer resolution.

`done-work`'s gate and `review-pr`'s invoke loop both feed the shared resolver
(`_lib.required_reviewers.resolve_required_local_reviewers`) the same inputs
about a PR:

  * which issues the PR closes (`gh pr view`'s `closingIssuesReferences`),
  * each closing issue's labels (for the `workstream:*` / `type:*`
    classification), and
  * the PR's changed files (`gh pr diff --name-only`, the complete path set),
    consulted only when a floor-carrying contribution is installed (the
    DEC-032 diff-property floor).

The closing-issue and label fetchers were duplicated byte-for-byte in both
consumers. The
resolver checks the *exact* `_Unresolvable` sentinel they return to decide
fail-closed vs. baseline-only (DEC-032 D5), so the two copies had to agree
character-for-character — but nothing tested that they did. "Fix one fetcher,
not the other" would silently diverge the invoke-set from the gate-set with
no test catching it. This module is the SINGLE definition both import, closing
that divergence seam (COR-007: extract the recurring shape instead of copying).

The fetchers stay substrate-injectable to honour `required_reviewers`'s
no-substrate stance and to keep each consumer's existing test seams effective:
each consumer passes its own already-wired `gh_run` / `gh_get_issue` (the same
callables its tests monkeypatch on the consumer module). The fetcher *logic* —
the empty-vs-unresolvable distinction, the JSON shape checks, the None-on-fetch
contract — lives here once.
"""

from __future__ import annotations

import json
from typing import Any, Callable

try:
    from _lib.required_reviewers import _Unresolvable
except ImportError:  # pragma: no cover - exercised via spec-loaded fallback
    from required_reviewers import _Unresolvable  # type: ignore[no-redef]


# Type of the injected `gh_run` (matches `_lib.gh.gh_run`): runs a `gh` argv
# with the adopter's pinned environment, returns the CompletedProcess.
GhRunFn = Callable[..., Any]
# Type of the injected `gh_get_issue` (matches `_lib.gh.gh_get_issue`): fetches
# issue JSON for the requested `--json` fields, or None on any failure.
GhGetIssueFn = Callable[..., "dict | None"]


def pr_closing_issue_numbers(
    pr_number: int, config: dict, *, gh_run: GhRunFn,
) -> "list[int] | _Unresolvable":
    """Issue numbers the PR closes, via `gh pr view`'s closingIssuesReferences.

    Distinguishes two states DEC-032 D1 treats differently:

    - **PR closes nothing** (the `closingIssuesReferences` array is present
      and empty) → `[]`, the "no closing issue" branch → baseline only. This
      is the legitimate, named fail-open branch.
    - **Could not determine what the PR closes** (gh non-zero exit, malformed
      JSON, or the field absent from the payload) → `_Unresolvable`, so the
      resolver fails closed. Returning `[]` here would silently drop a
      genuinely-required contributed reviewer on a transient gh failure — a
      retry-/induce-able bypass of a required review.

    `gh_run` is injected (the consumer's `_lib.gh.gh_run`) so this module
    carries no substrate of its own; both consumers share this one definition.
    """
    proc = gh_run(
        ["gh", "pr", "view", str(pr_number),
         "--json", "closingIssuesReferences"],
        config, check=False,
    )
    if proc.returncode != 0:
        return _Unresolvable(
            f"gh pr view closingIssuesReferences failed: {proc.stderr.strip()}"
        )
    try:
        data = json.loads(proc.stdout)
    except (ValueError, json.JSONDecodeError):
        return _Unresolvable(
            "gh pr view closingIssuesReferences returned malformed JSON"
        )
    if not isinstance(data, dict) or "closingIssuesReferences" not in data:
        return _Unresolvable(
            "gh pr view payload missing closingIssuesReferences"
        )
    refs = data["closingIssuesReferences"]
    if not isinstance(refs, list):
        # A present-but-null (or otherwise non-list) field is UNKNOWN ground
        # truth, not "closes nothing" — fail closed rather than collapse a
        # null to the legitimate empty branch and drop a required reviewer.
        return _Unresolvable(
            "gh pr view closingIssuesReferences is null or not a list"
        )
    numbers: list[int] = []
    for ref in refs:
        if isinstance(ref, dict) and isinstance(ref.get("number"), int):
            numbers.append(ref["number"])
    return numbers


def pr_changed_files(
    pr_number: int, config: dict, *, gh_run: GhRunFn,
) -> "list[str] | _Unresolvable":
    """The PR's changed-file paths, via `gh pr diff --name-only` (DEC-032 amendment).

    Feeds the resolver's diff-property floor (`touches-code`), so the SOURCE of
    the file set must be complete: `gh pr view --json files` returns only a
    bounded first page (~100 files, no pagination), so a >100-file PR with code
    after page 1 would read as docs-only and the floor would silently not fire.
    `gh pr diff <n> --name-only` returns the full path set (one path per line),
    closing that page-cap gate-escape.

    Fail-closed contract (mirrors `pr_closing_issue_numbers`, DEC-032 D5):

    - **The diff is determinable and non-empty** → the list of changed paths.
    - **Could not determine the diff, OR it came back empty** (gh non-zero exit,
      or zero paths) → `_Unresolvable`, so the resolver fails closed. A PR
      always changes at least one file, so an empty result is treated as
      unknown ground truth rather than "touches nothing"; returning `[]` here
      would let a floor reviewer be dropped on a transient gh failure — a
      retry-/induce-able bypass, exactly the hole DEC-032 D5 guards.

    The resolver only calls this when a floor-carrying contribution is
    installed, so a floor-free project never issues this `gh` round-trip.
    `gh_run` is injected (the consumer's `_lib.gh.gh_run`) so this module
    carries no substrate of its own; both consumers share this one definition.
    """
    proc = gh_run(
        ["gh", "pr", "diff", str(pr_number), "--name-only"],
        config, check=False,
    )
    if proc.returncode != 0:
        return _Unresolvable(
            f"gh pr diff --name-only failed: {proc.stderr.strip()}"
        )
    paths = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    if not paths:
        return _Unresolvable(
            "gh pr diff --name-only returned no files — diff undeterminable"
        )
    return paths


def issue_labels(
    issue_number: int, config: dict, *, gh_get_issue: GhGetIssueFn,
) -> "list | None":
    """Read an issue's labels for classification (None on fetch failure).

    The injected per-issue label fetcher the shared resolver calls. A None
    return (the issue's labels could not be read) is the resolver's
    fail-closed signal — the issue's classification is UNKNOWN, so a
    contributed reviewer it might require cannot be dropped (DEC-032 D5).

    `gh_get_issue` is injected (the consumer's `_lib.gh.gh_get_issue`) so this
    module carries no substrate of its own; both consumers share this one
    definition.
    """
    issue = gh_get_issue(issue_number, config, fields="labels")
    if issue is None:
        return None
    return issue.get("labels") or []
