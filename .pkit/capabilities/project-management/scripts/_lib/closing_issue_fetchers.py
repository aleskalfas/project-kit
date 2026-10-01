"""Shared `gh`-backed PR-data fetchers for required-reviewer resolution.

`done-work`'s gate and `review-pr`'s invoke loop both feed the shared resolver
(`_lib.required_reviewers.resolve_required_local_reviewers`) the same inputs
about a PR:

  * which issues the PR closes (`gh pr view`'s `closingIssuesReferences`),
  * each closing issue's labels (for the `workstream:*` / `type:*`
    classification), and
  * the PR's changed files (every page of GitHub's pull-request files API,
    the complete path set), consulted only when a floor-carrying contribution
    is installed (the DEC-032 diff-property floor).

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
    from _lib.required_reviewers import _TooManyChangedFiles, _Unresolvable
except ImportError:  # pragma: no cover - exercised via spec-loaded fallback
    from required_reviewers import (  # type: ignore[no-redef]
        _TooManyChangedFiles,
        _Unresolvable,
    )


# Type of the injected `gh_run` (matches `_lib.gh.gh_run`): runs a `gh` argv
# with the adopter's pinned environment, returns the CompletedProcess.
GhRunFn = Callable[..., Any]
# Type of the injected `gh_get_issue` (matches `_lib.gh.gh_get_issue`): fetches
# issue JSON for the requested `--json` fields, or None on any failure.
GhGetIssueFn = Callable[..., "dict | None"]

# GitHub's "list pull request files" endpoint: one page holds at most 100
# entries, and the whole listing stops at 3000 files however many the PR
# changes. A listing that reaches the ceiling may have been cut short, so it is
# refused rather than read as complete.
_FILES_PAGE_SIZE = 100
_FILES_CEILING = 3000
# One JSON array per changed file: its path, then its path before a rename
# (null when it was not renamed).
_FILES_JQ = ".[] | [.filename, .previous_filename]"


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
    """The PR's changed-file paths, via GitHub's paginated files API (DEC-032 amendment).

    Feeds the resolver's diff-property floor (`touches-code`), so the SOURCE of
    the file set must be complete. Two sources were rejected for missing part
    of it. `gh pr view --json files` returns only a bounded first page (~100
    files, no pagination), so a large PR with code past page 1 read as
    docs-only and the floor silently did not fire. `gh pr diff --name-only` is
    refused outright by GitHub for a PR changing more than 300 files, so the
    resolver failed closed on a PR that was merely large. `gh api --paginate`
    reads every page of `repos/{owner}/{repo}/pulls/<n>/files`, which lists up
    to 3000 files.

    A renamed file contributes its old path as well as its new one: moving a
    file out of code removes code, exactly as deleting it does, and a deleted
    file is listed under its old path.

    Fail-closed contract (mirrors `pr_closing_issue_numbers`, DEC-032 D5):

    - **The file list is determinable and non-empty** → the changed paths.
    - **Could not determine it, OR it came back empty** (gh non-zero exit, a
      line that is not a file entry, or zero entries) → `_Unresolvable`, so
      the resolver fails closed. A PR always changes at least one file, so an
      empty result is treated as unknown ground truth rather than "touches
      nothing"; returning `[]` here would let a floor reviewer be dropped on a
      transient gh failure — a retry-/induce-able bypass, exactly the hole
      DEC-032 D5 guards.
    - **The listing reached GitHub's 3000-file ceiling** → `_TooManyChangedFiles`
      (an `_Unresolvable`): files past the ceiling are never listed, so the set
      may be incomplete, and a retry reads the same cut-short list.

    The resolver only calls this when a floor-carrying contribution is
    installed, so a floor-free project never issues this `gh` round-trip.
    `gh_run` is injected (the consumer's `_lib.gh.gh_run`) so this module
    carries no substrate of its own; both consumers share this one definition.
    """
    proc = gh_run(
        ["gh", "api", "--paginate",
         f"repos/{{owner}}/{{repo}}/pulls/{pr_number}/files"
         f"?per_page={_FILES_PAGE_SIZE}",
         "--jq", _FILES_JQ],
        config, check=False,
    )
    if proc.returncode != 0:
        return _Unresolvable(
            f"gh api pulls/{pr_number}/files failed: {proc.stderr.strip()}"
        )
    paths: list[str] = []
    listed = 0
    for line in proc.stdout.splitlines():
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except ValueError:
            entry = None
        if not (isinstance(entry, list) and entry and isinstance(entry[0], str)
                and entry[0]):
            return _Unresolvable(
                f"gh api pulls/{pr_number}/files returned a line that is not "
                f"a file entry: {line.strip()!r}"
            )
        listed += 1
        paths.extend(path for path in entry[:2] if isinstance(path, str) and path)
    if not listed:
        return _Unresolvable(
            f"gh api pulls/{pr_number}/files returned no files — diff "
            "undeterminable"
        )
    # Counted in files GitHub listed, not in paths: a rename adds two paths
    # but is one file toward the ceiling.
    if listed >= _FILES_CEILING:
        return _TooManyChangedFiles(
            f"PR #{pr_number} changes at least {_FILES_CEILING} files, the "
            "most GitHub lists for a pull request — its complete changed-file "
            "set cannot be read"
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
