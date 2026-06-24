"""Shared issue-lifecycle position + gate inference (pm-local, DEC-033).

This module is the single home of the issue-lifecycle's *domain* inference,
lifted verbatim from `move-issue`'s pre-rebind logic so the rebound predicate
commands resolve identical positions and gate outcomes — behaviour parity is
the acceptance bar (DEC-033 Implications).

The process engine (COR-033, in the binary) is content-free: it knows states,
transitions, gates, a position, a journal — nothing about issues, labels,
milestones, branches, or PRs. All of *that* lives here and is exposed to the
engine only as the structured-JSON predicate contract (the detector + gate
scripts call into this module).

Position precedence (`infer_current_state`) reproduces move-issue's
`_infer_current_state` EXACTLY — this is the #1 parity risk per DEC-033:

  1. GitHub issue state == closed                -> done
  2. first `state:*` label present               -> that state
  3. milestone assigned                          -> backlog
  4. otherwise                                    -> todo

The detectors built on top of this are mutually exclusive (each returns
`result = (infer_current_state(...) == my_state)`), so the engine's
"first matching state wins" rule is satisfied regardless of state order — the
order in workflow.yaml is belt-and-suspenders, not the sole guarantee.

The parent in-progress *descendant walk* (DEC-033 Implications (d)) is a
pm-local breadth concern; it lives in `parent_has_active_descendant` here and is
NEVER pulled into the engine. It is exposed as its own predicate, distinct from
the position detectors — it must not alter the parity truth-table above (an
issue's resolved position stays label-driven), so detection callers do not fold
it into `infer_current_state`.
"""

from __future__ import annotations

import re

from _lib import axis_labels

# Canonical state ordering (matches move-issue's `order` lists).
STATE_ORDER = ["todo", "backlog", "in-progress", "review", "done"]


def workflow_process(workflow: dict | None) -> dict:
    """Return the process-definition block of a parsed workflow.yaml.

    Since the schema_version 3 rebind (DEC-033), `states` + `transitions` live
    under a top-level `process:` block (the substrate shape, COR-033). This
    helper resolves that block, falling back to the top level for a pre-v3
    (schema_version 2) override an adopter may still hold — so pm readers work
    against either shape. Returns an empty dict for unusable input.
    """
    if not isinstance(workflow, dict):
        return {}
    process = workflow.get("process")
    if isinstance(process, dict):
        return process
    return workflow


def infer_current_state(
    *, state: str, milestone: dict | None, labels: list[str]
) -> str:
    """Best-effort live position — reproduces move-issue `_infer_current_state`.

    Precedence (DO NOT reorder — parity-critical, DEC-033):
    closed -> done; first `state:*` label; milestone -> backlog; else todo.
    """
    if state == "closed":
        return "done"
    label_state = axis_labels.read("state", labels)
    if label_state is not None:
        return label_state
    if milestone:
        return "backlog"
    return "todo"


# --- gate inference -------------------------------------------------------


def unticked_boxes(body: str) -> list[str]:
    """Unticked markdown checkboxes in a body (DEC-007 close-gate).

    Lifted verbatim from merge-pr / close-issue's `_unticked_boxes`: a line is
    an unticked box when it is `- [ ]` (or `* [ ]`) followed by real content.
    """
    out: list[str] = []
    for line in (body or "").splitlines():
        if re.match(r"^\s*[-*]\s+\[\s\]\s+\S", line):
            out.append(line.strip())
    return out


def closing_issue_numbers(pr_body: str) -> list[int]:
    """Issue numbers a PR closes via `Closes/Fixes/Resolves #N` (cross-checked
    against the checkbox close-gate)."""
    pattern = re.compile(r"\b(?:closes|fixes|resolves)\s+#(\d+)", re.IGNORECASE)
    seen: list[int] = []
    for m in pattern.finditer(pr_body or ""):
        n = int(m.group(1))
        if n not in seen:
            seen.append(n)
    return seen


def branch_matches_issue(branch: str, issue_number: int) -> bool:
    """True when a branch name matches the `<type>/<N>-<slug>` shape for the
    issue (the start-work convention)."""
    return bool(re.match(rf"^[a-z]+/{issue_number}-", branch))


def parent_ref(child_body: str) -> int | None:
    """The parent issue number named on a child body's FIRST parent-ref line
    (e.g. `EPIC: #42` -> 42), or None when the body declares no parent-ref.

    The methodology's hierarchy source of truth: one parent-ref line by
    convention, on the first non-blank line (mirrors move-issue /
    close-issue's `_walk_parent_chain` recognition). The first non-blank line
    must match `<Word>: #<n>`; otherwise the body names no parent."""
    if not child_body:
        return None
    for line in child_body.splitlines():
        s = line.strip()
        if not s:
            continue
        m = re.match(r"^([A-Za-z]+):\s+#(\d+)", s)
        if not m:
            return None
        return int(m.group(2))
    return None


def names_parent(child_body: str, parent_number: int) -> bool:
    """True when a child issue body's first parent-ref line points at
    `parent_number` (e.g. `EPIC: #42`).

    Mirrors move-issue's `_walk_parent_chain` recognition (one parent-ref line
    by convention, on the first non-blank lines)."""
    return parent_ref(child_body) == parent_number


def state_is_active(state: str) -> bool:
    """True when a state is in-progress or further (used by the parent
    descendant walk: a parent is 'active' if a descendant is at least
    in-progress)."""
    try:
        return STATE_ORDER.index(state) >= STATE_ORDER.index("in-progress")
    except ValueError:
        return False
