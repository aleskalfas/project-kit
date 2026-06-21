"""Predicate bodies for the rebound issue-lifecycle (DEC-033).

These are the READ-ONLY checks the process engine (COR-031) runs to resolve a
keyed issue's position and to evaluate its gates. The engine invokes each as a
plain subprocess `[script, <issue-number>, --json]` (no shell, no `with` args
threaded — see the per-state detector scripts for how the target state is
fixed), reads structured JSON on stdout, and acts on it:

  detection / deterministic gate -> {result: bool, reason: str, detail?: {}}
  authorisation-artifact gate    -> {exists: bool, produced_by: str|null,
                                     reason: str, detail?: {}}

Every function here fetches issue/PR state via the adopter-pinned `gh` helper
and returns the contract dict. They are strictly read-only (COR-031: `status`
runs them live, so a mutating predicate is a bug). All domain inference is
delegated to `lifecycle_inference`, which lifts move-issue's logic verbatim for
behaviour parity (the acceptance bar).

This module is loaded by the thin PEP-723 predicate scripts in `scripts/`; it is
not itself executable.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

_HERE = Path(__file__).parent.parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from _lib import lifecycle_inference as infer  # noqa: E402
from _lib.gh import gh_run, load_adopter_config  # noqa: E402
from _lib.membership import resolve_capability_root  # noqa: E402


# A predicate that genuinely COULD NOT evaluate (gh failure, capability
# missing) carries this marker key. The thin predicate script strips it and
# exits non-zero, so the engine treats the predicate as INDETERMINATE
# (fail-closed, COR-031) rather than a clean result=False — a "couldn't tell"
# must never look like a "no".
INDETERMINATE_KEY = "_indeterminate"


def _indeterminate(reason: str) -> dict[str, Any]:
    return {"result": False, "reason": reason, INDETERMINATE_KEY: True}


# Pagination ceilings for the `gh list` queries below. When a returned list hits
# its ceiling there MAY be more rows we never saw, so the query is honestly
# indeterminate (fail-closed, COR-031) — not a confident negative. Kept named so
# the limit and its ceiling-check can never drift apart.
_OPEN_ISSUES_LIMIT = 500
_MERGED_PRS_LIMIT = 100

# Sentinel for "the gh list hit its pagination ceiling": there may be more rows
# than we fetched, so the query is indeterminate rather than a confident
# negative. Distinct from `_GH_ERROR` (the query itself failed) only in the
# message; both map to fail-closed indeterminate.
_GH_CEILING = object()


# --- shared issue access --------------------------------------------------


def _capability_root() -> Path | None:
    return resolve_capability_root(None)


def _config(capability_root: Path) -> dict[str, Any]:
    return load_adopter_config(capability_root)


def _issue_labels(issue: dict[str, Any]) -> list[str]:
    return [
        lbl.get("name", "") if isinstance(lbl, dict) else str(lbl)
        for lbl in (issue.get("labels") or [])
    ]


def _fetch_issue(issue_number: int, config: dict[str, Any], fields: str) -> dict[str, Any] | None:
    """Read-only `gh issue view`. Returns None on any failure (fail-closed at
    the engine: an unevaluable predicate is indeterminate)."""
    try:
        proc = gh_run(
            ["gh", "issue", "view", str(issue_number), "--json", fields],
            config,
            check=False,
        )
    except FileNotFoundError:
        return None
    if proc.returncode != 0:
        return None

    try:
        parsed = json.loads(proc.stdout)
    except (json.JSONDecodeError, ValueError):
        return None
    return parsed if isinstance(parsed, dict) else None


# --- position detection ---------------------------------------------------


def detect_state(issue_number: int, target_state: str) -> dict[str, Any]:
    """Detection predicate for one lifecycle state.

    Resolves the issue's live position via `infer_current_state` (move-issue's
    exact precedence) and returns result=True iff it equals `target_state`.
    Because every state's detector shares this single resolver, the detectors
    are mutually exclusive — exactly one matches — so the engine's
    "first-matching-state" rule reproduces move-issue regardless of state order.
    """
    capability_root = _capability_root()
    if capability_root is None:
        return _indeterminate("project-management capability not found")
    config = _config(capability_root)
    issue = _fetch_issue(issue_number, config, "state,milestone,labels")
    if issue is None:
        return _indeterminate(f"could not read issue #{issue_number} (gh failure)")
    state = str(issue.get("state", "")).lower()
    milestone = issue.get("milestone") or {}
    labels = _issue_labels(issue)
    resolved = infer.infer_current_state(state=state, milestone=milestone, labels=labels)
    return {
        "result": resolved == target_state,
        "reason": f"#{issue_number} inferred state is {resolved!r}",
        "detail": {"inferred_state": resolved, "target": target_state},
    }


def parent_has_active_descendant(parent_number: int) -> dict[str, Any]:
    """Pm-LOCAL descendant walk (DEC-033 Implications (d); breadth, NEVER in the
    engine): True when at least one child issue (one that names this parent in
    its body parent-ref line) is at in-progress or further.

    Exposed as its own predicate, separate from the position detectors — it does
    NOT participate in `infer_current_state`, so it cannot alter the parity
    truth-table (an issue's resolved position stays label-driven). It is the
    pm-local mechanism a wrapper can consult for forward-cascade reasoning.
    """
    capability_root = _capability_root()
    if capability_root is None:
        return _indeterminate("project-management capability not found")
    config = _config(capability_root)
    children = _list_open_issues(config)
    if children is None:
        return _indeterminate("could not list issues (gh failure)")
    if children is _GH_CEILING:
        return _indeterminate(
            f"issue list hit the pagination ceiling ({_OPEN_ISSUES_LIMIT}); "
            "descendant walk may be incomplete"
        )
    active: list[int] = []
    for child in children:
        body = str(child.get("body") or "")
        if not infer.names_parent(body, parent_number):
            continue
        child_state = infer.infer_current_state(
            state=str(child.get("state", "")).lower(),
            milestone=child.get("milestone") or {},
            labels=_issue_labels(child),
        )
        if infer.state_is_active(child_state):
            active.append(int(child.get("number", 0)))
    return {
        "result": bool(active),
        "reason": (
            f"#{parent_number} has active descendant(s): "
            f"{', '.join(f'#{n}' for n in active)}"
            if active
            else f"#{parent_number} has no in-progress-or-further descendant"
        ),
        "detail": {"active_descendants": active},
    }


def _list_open_issues(config: dict[str, Any]) -> Any:
    """List issues for the descendant walk. Returns the parsed list, `None` on a
    gh failure, or the `_GH_CEILING` sentinel when the result hits the pagination
    ceiling (there may be unseen rows -> the caller maps that to indeterminate).
    """
    try:
        proc = gh_run(
            [
                "gh",
                "issue",
                "list",
                "--state",
                "all",
                "--limit",
                str(_OPEN_ISSUES_LIMIT),
                "--json",
                "number,body,state,labels,milestone",
            ],
            config,
            check=False,
        )
    except FileNotFoundError:
        return None
    if proc.returncode != 0:
        return None
    try:
        parsed = json.loads(proc.stdout)
    except (json.JSONDecodeError, ValueError):
        return None
    if not isinstance(parsed, list):
        return None
    if len(parsed) >= _OPEN_ISSUES_LIMIT:
        return _GH_CEILING
    return parsed


# --- gates ----------------------------------------------------------------


def gate_checkboxes_ticked(issue_number: int) -> dict[str, Any]:
    """Deterministic close-gate (DEC-007): result=True iff the issue body has no
    unticked `- [ ]` checkbox. Lifts close-issue / merge-pr's `_unticked_boxes`.
    """
    capability_root = _capability_root()
    if capability_root is None:
        return _indeterminate("project-management capability not found")
    config = _config(capability_root)
    issue = _fetch_issue(issue_number, config, "body")
    if issue is None:
        return _indeterminate(f"could not read issue #{issue_number} (gh failure)")
    body = str(issue.get("body") or "")
    unticked = infer.unticked_boxes(body)
    return {
        "result": not unticked,
        "reason": (
            "all checkboxes ticked"
            if not unticked
            else f"{len(unticked)} unticked checkbox(es) remain"
        ),
        "detail": {"unticked": unticked},
    }


def gate_pr_merged(issue_number: int, actor: str | None = None) -> dict[str, Any]:
    """Authorisation-artifact gate (PR-merge, cross-authority): reports whether a
    merged PR closing this issue exists and WHO merged it (`produced_by`).

    The ENGINE computes result = exists && produced_by != actor (cross-authority
    is non-overridable, COR-031 P4) — this predicate returns only the facts. A
    PR merged by the actor being gated is the actor's own assertion and must not
    pass; a merge by a different authority (a human reviewer / merger) passes.
    """
    capability_root = _capability_root()
    if capability_root is None:
        return _indeterminate("project-management capability not found")
    config = _config(capability_root)
    pr = _find_merged_pr_for_issue(issue_number, config)
    if pr is _GH_ERROR:
        # Couldn't determine the answer -> indeterminate (fail-closed), distinct
        # from a confident "no merged PR exists". Either the query failed or it
        # hit the pagination ceiling (an unseen merged PR may exist).
        return _indeterminate(
            "could not determine merged-PR state (gh failure or pagination "
            f"ceiling of {_MERGED_PRS_LIMIT} reached)"
        )
    if pr is None:
        return {
            "exists": False,
            "produced_by": None,
            "reason": f"no merged PR closing #{issue_number} found",
        }
    merged_by = pr.get("merged_by")
    return {
        "exists": True,
        "produced_by": merged_by,
        "reason": (
            f"PR #{pr.get('number')} closing #{issue_number} merged by "
            f"{merged_by!r}"
        ),
        "detail": {"pr_number": pr.get("number"), "merged_by": merged_by},
    }


# Sentinel distinguishing "gh query failed" (indeterminate) from "no merged PR
# found" (a confident negative) in `_find_merged_pr_for_issue`.
_GH_ERROR = object()


def _find_merged_pr_for_issue(issue_number: int, config: dict[str, Any]) -> Any:
    """Find a merged PR whose body closes `issue_number`; report its merger.

    Read-only. Returns the {number, merged_by} dict when found, None when no
    merged PR closes the issue, or the `_GH_ERROR` sentinel when the PR query
    itself failed (so the caller maps that to indeterminate, not a negative).
    `merged_by` is the GitHub login of whoever merged the PR (the
    cross-authority producer) — distinct from the PR author.
    """
    try:
        proc = gh_run(
            [
                "gh",
                "pr",
                "list",
                "--state",
                "merged",
                "--limit",
                str(_MERGED_PRS_LIMIT),
                "--json",
                "number,body,mergedBy",
            ],
            config,
            check=False,
        )
    except FileNotFoundError:
        return _GH_ERROR
    if proc.returncode != 0:
        return _GH_ERROR
    try:
        prs = json.loads(proc.stdout)
    except (json.JSONDecodeError, ValueError):
        return _GH_ERROR
    if not isinstance(prs, list):
        return _GH_ERROR
    for pr in prs:
        if not isinstance(pr, dict):
            continue
        body = str(pr.get("body") or "")
        if issue_number in infer.closing_issue_numbers(body):
            merged_by_raw = pr.get("mergedBy")
            merged_by = (
                merged_by_raw.get("login")
                if isinstance(merged_by_raw, dict)
                else merged_by_raw
            )
            return {"number": pr.get("number"), "merged_by": merged_by}
    # No match within the fetched page. If we hit the ceiling there may be an
    # unseen merged PR -> indeterminate (fail-closed), not a confident negative.
    if len(prs) >= _MERGED_PRS_LIMIT:
        return _GH_ERROR
    return None
