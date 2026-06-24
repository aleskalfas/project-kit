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
`_infer_current_state` EXACTLY in the greenfield (no-map) case — this is the #1
parity risk per DEC-033:

  1. GitHub issue state == closed                -> done
  2. first `state:*` label present               -> that state
  3. milestone assigned                          -> backlog
  4. otherwise                                    -> todo

Under a PRESENT substrate-map (ADR-026 §5, DEC-033 detector swap) the reader is
map-aware. When that map binds `state` to a `derive` predicate, position
resolves from the open/closed substrate (+ a blocked label) instead of the kit
`state:*` labels — closed -> done, open+Blocked -> blocked, else the collapsed
open-ish `open` — and any kit `state:*` label is IGNORED (the wedge #265 named,
closed by #269). A `label`-bound `state` reads the adopter's mapped label set
(reverse remap) in place of the kit set. No map / non-derive / greenfield reads
exactly the four-step precedence above — the parity bar. The swap is a CHANGE OF
PREDICATE, not of the engine/position contract (DEC-033): first-matching-detection
still wins; only WHICH reality the predicate reads changes.

The detectors built on top of this are mutually exclusive (each returns
`result = (infer_current_state(...) == my_state)`), so the engine's
"first matching state wins" rule is satisfied regardless of state order — the
order in workflow.yaml is belt-and-suspenders, not the sole guarantee. Because
this reader is the single home of the position read (the engine detectors and
move-issue's local alias all delegate here), making it map-aware makes the whole
detection path map-aware at one point — and that read AGREES with how
move-issue / close-issue WRITE under a derive map (they write/strip no kit
`state:*` label; the open/closed substrate carries state), so there is no
read/write disagreement.

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
    *,
    state: str,
    milestone: dict | None,
    labels: list[str],
    substrate_map: "axis_labels.SubstrateMap | None" = None,
) -> str:
    """Best-effort live position — reproduces move-issue `_infer_current_state`.

    Two arms, selected by the adopter's substrate-map (ADR-026 §5, DEC-033):

    **Greenfield / non-derive `state` (``substrate_map is None``, OR present but
    `state` is not `derive`-bound).** The kit `state:*` precedence, UNCHANGED —
    parity-critical, DO NOT reorder:
      closed -> done; first `state:*` label; milestone -> backlog; else todo.
    This is the byte-identical default: a `None` map (the default arg) reproduces
    the pre-map behaviour exactly, so every caller that does not thread a map
    keeps today's resolution. A present map whose `state` is `label`-bound reads
    the adopter's mapped label set (reverse remap) in place of the kit `state:*`
    set, falling through to milestone/todo as before; a present map whose `state`
    is `title-prefix`/`unsupported`/absent simply finds no label and falls
    through — none of these touch the closed->done or milestone arms.

    **Derive-bound `state` (a present map binds `state` to a `derive` predicate).**
    Position resolves from the open/closed substrate via
    ``axis_labels.derive_state`` (ADR-026 §5's reduced state set): closed ⇒ the
    terminal ``done``; an open issue with a ``Blocked`` label ⇒ ``blocked``; an
    open issue without ⇒ the collapsed open-ish ``open``. This **ignores any kit
    ``state:*`` label entirely** — a leftover ``state:todo`` (written before the
    map was declared) must NOT shadow the open/closed read. The milestone arm
    does not apply: a derive-from-open/closed binding cannot distinguish Backlog
    from the other open-ish states, so they collapse to one ``open`` (the reduced
    state set is the binding's decision, DEC-036). This closes the SIBLING GAP
    #265's docstring named (#269 under Feature #268): the derive READ is a
    predicate SWAP, faithful to DEC-033 — the engine/position contract is
    unchanged, only WHICH predicate over reality resolves position.

    This reader is the single home of the position read: the engine detectors
    (`lifecycle_predicates.detect_state`, `parent_has_active_descendant`,
    `cascade_members`) and move-issue's local alias all delegate here, so making
    THIS map-aware makes the whole detection path map-aware in one place — the
    read agrees with how move-issue / close-issue WRITE under a derive map (they
    write/strip no kit `state:*` label; the open/closed substrate carries state).
    """
    derive = axis_labels.state_derive_binding(substrate_map)
    if derive is not None:
        # Derive-bound `state`: resolve from open/closed (+ blocked label),
        # ignoring any kit `state:*` label (the wedge). The milestone/todo
        # fall-throughs do not apply — the open-ish states are collapsed.
        return axis_labels.derive_state(is_closed=state == "closed", labels=labels)

    if state == "closed":
        return "done"
    # A present map may bind `state` to the adopter's own label set (reverse
    # remap); greenfield reads the kit `state:*` set. `resolve_read` is the
    # identity in the no-map case, so greenfield stays byte-identical.
    label_state = axis_labels.resolve_read("state", labels, substrate_map)
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
    in-progress).

    Greenfield reads the kit five-state order (in-progress / review / done all
    count as active — `done` counts because it is `>= in-progress` in the order;
    this is the established greenfield contract and is preserved here unchanged).
    Under a `derive` binding the open-ish states collapse to a single ``open``
    (ADR-026 §5) that subsumes in-progress — the predicate cannot tell Backlog
    from In-progress — so a derived ``open`` (and the open-ish ``blocked``)
    counts as active: the forward-cascade walk treats a possibly-in-flight
    open-ish child as active rather than silently dropping it (a `ValueError` on
    `STATE_ORDER.index("open")` would otherwise misclassify it as inactive). The
    derived ``done`` IS ``"done"`` (the kit terminal value), so it falls through
    to the order check and counts active exactly as greenfield `done` does — no
    divergence. A whole-tracker derive map is the only place ``open``/``blocked``
    appear, so this does not perturb the greenfield order.
    """
    if state in (axis_labels.DERIVE_STATE_OPEN, axis_labels.DERIVE_STATE_BLOCKED):
        return True
    try:
        return STATE_ORDER.index(state) >= STATE_ORDER.index("in-progress")
    except ValueError:
        return False
