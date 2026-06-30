"""The sole constructor of the native sub-issue (containment) link write, AND
the one read seam that resolves a parent's children.

DEC-005 makes **GitHub's native sub-issues field** the canonical structural
mechanism for the hierarchy parent ↔ child edge: every parent-link mutation must
set the native link *in addition to* the textual first-line parent-ref. Until
now the codebase wrote only the textual child-side ref; this module supplies the
missing native write.

The read counterpart (the second half of this module)
--------------------------------------------------------
DEC-005's "native wins" rule is a *read*-time resolution as much as a write-time
one. Where this module's write half is the sole constructor of the native link,
its read half (:func:`resolve_children`) is the sole resolver of "what are this
parent's children?" — native sub-issues where present, textual child-side
parent-refs otherwise, **native-wins on conflict**. Both `show-tree` and the
DEC-034 closure-fold child-walk resolve through it, so no consumer re-derives
containment by parsing body parent-refs directly (ADR-026's one-read-seam
discipline, mirrored here for the containment axis: a second consumer must not
re-derive what one seam already resolves). The formal read-path contract for
this seam will be pinned in the Track-2 containment ADR (architect-owned) when
that lands; until then this module's docstrings carry the resolution semantics.

A *containment link* is a third non-label substrate, distinct from the two
``_lib/substrate_writes`` covers (the Projects-v2 field-value and the milestone
assignment): it establishes the native parent ↔ child edge that surfaces a child
in the parent's sub-issues panel and feeds the Projects-v2 "Sub-issues progress"
field (DEC-005). Because it is a different operation (``gh api
repos/.../sub_issues`` rather than ``gh project item-edit`` / ``gh issue
…--milestone``), it lives in its own module with its own sole-constructor guard
(``tests/test_pm_containment_write_seam.py``) — the same discipline as ADR-031's
substrate-write seam, not a widening of that seam's covered set.

Sole-constructor discipline (ADR-031, applied to containment)
-------------------------------------------------------------
Every script that links a child under a parent obtains the ``gh`` write **only
by asking this module** — it never string-builds the ``gh api …/sub_issues``
argv itself. That makes "no script string-builds the sub-issue write inline" a
structural property the guard enforces, the direct analogue of the field-value /
milestone seam. ``create-issue`` calls it today on ``--parent``; any future
parent-link mutation (re-parent, promote, a batch set-field that moves a parent)
reuses the same construction point.

The API mechanism
-----------------
GitHub's REST endpoint ``POST /repos/{owner}/{repo}/issues/{parent}/sub_issues``
with body ``{"sub_issue_id": <child database id>}`` is the canonical add. The
``sub_issue_id`` is the child's **integer database id** (``gh api
repos/.../issues/<n> --jq .id``), NOT the issue number and NOT the GraphQL
node id (``gh issue view --json id`` returns the node id, which this endpoint
rejects). REST is chosen over the GraphQL ``addSubIssue`` mutation because it
needs only the integer id the same ``gh api`` round-trip already yields, with no
node-id resolution or query crafting.

Idempotency (DEC-026, value-equality)
-------------------------------------
Linking an already-linked child is a no-op. Before adding, the linker lists the
parent's current sub-issues (``GET …/sub_issues``) and skips the write when the
child's database id is already present — value-equality, no duplicate-add error
relied upon.

Graceful degradation (the textual ref is the fallback)
------------------------------------------------------
Where the instance does not support sub-issues — an older GHES, the feature
turned off, the endpoint returning 404 / 410 / 422 — the native write degrades
to a **no-op**: the link result reports ``unsupported`` and the caller carries
on. The textual first-line parent-ref (written unchanged by ``create-issue``)
carries the relationship in that case. A native write never fails the create.
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from enum import Enum
from typing import Any

# Sibling module — the gh shell-out helper that pins the adopter's host/owner
# (DEC-023). Imported the same way `_lib.substrate_writes` does, with a defensive
# fallback for unusual import contexts (tests that load a module by file path may
# not have _lib on sys.path).
try:
    from gh import gh_run  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover
    try:
        from _lib.gh import gh_run  # type: ignore[no-redef]
    except ImportError:  # pragma: no cover
        gh_run = None  # type: ignore[assignment]


class LinkOutcome(Enum):
    """The outcome class of one native sub-issue link attempt.

    LINKED       — the native link was created this call.
    ALREADY       — the child was already a sub-issue of the parent (idempotent
                    no-op, value-equality per DEC-026).
    UNSUPPORTED  — the instance does not support sub-issues (404/410/422/feature
                    off); the textual ref is the fallback. NOT a failure.
    FAILED       — the write was attempted and failed for a reason that is NOT
                    "unsupported" (auth, network, missing `gh`). The caller still
                    has the textual ref, but this signals a genuine problem to
                    report rather than silently swallow.
    """

    LINKED = "linked"
    ALREADY = "already"
    UNSUPPORTED = "unsupported"
    FAILED = "failed"


@dataclass(frozen=True)
class LinkResult:
    """Outcome of one native sub-issue link attempt — a neutral carrier.

    Failure-posture-neutral in the same spirit as
    ``substrate_writes.SubstrateWriteResult`` (ADR-031 point 6): it records what
    happened; the caller decides what to do. ``create-issue`` treats every
    outcome as non-fatal (the textual ref is the spine) but reports a one-line
    note keyed on ``outcome``.

    Fields:
      outcome — the :class:`LinkOutcome`.
      detail  — a one-line human-readable summary for the caller to print.
    """

    outcome: LinkOutcome
    detail: str = ""

    @property
    def ok(self) -> bool:
        """True when the relationship is in place after this call (linked or
        already-linked). UNSUPPORTED and FAILED are not ``ok`` — the native link
        is absent — but only FAILED is a genuine error (UNSUPPORTED is expected
        on instances without the feature)."""
        return self.outcome in (LinkOutcome.LINKED, LinkOutcome.ALREADY)


# HTTP statuses that mean "this instance does not support sub-issues" — degrade
# to a no-op rather than a failure. 404 (endpoint absent on older GHES), 410
# (gone), 422 (unprocessable — feature off / not enabled for this repo).
_UNSUPPORTED_STATUSES = (404, 410, 422)


def add_sub_issue_args(*, parent_number: int | str, child_database_id: int | str) -> list[str]:
    """Construct the ``gh api …/sub_issues`` add argv.

    The sole constructor of the native sub-issue link write. Callers obtain this
    argv only here; they never string-build ``gh api repos/.../sub_issues``
    themselves (the containment-seam guard enforces it).

    ``child_database_id`` is the child's **integer database id** (not its number,
    not its node id). ``-X POST -F sub_issue_id=<id>`` posts the documented body.
    The ``-F`` (typed field) form is REQUIRED, not ``-f``: the endpoint validates
    ``sub_issue_id`` as a JSON *integer* and rejects the string ``-f`` would send
    with ``HTTP 422 … is not of type integer``. The ``{owner}/{repo}``
    placeholders are resolved by ``gh`` against the current repo (host/owner
    pinned via the gh helper per DEC-023).
    """
    return [
        "gh", "api",
        "-X", "POST",
        f"repos/{{owner}}/{{repo}}/issues/{parent_number}/sub_issues",
        "-F", f"sub_issue_id={child_database_id}",
    ]


def list_sub_issues_args(*, parent_number: int | str) -> list[str]:
    """Construct the ``gh api …/sub_issues`` list (GET) argv.

    Used for the value-equality idempotency read before an add — list the
    parent's current sub-issues and skip the add when the child is already among
    them. Paginated so a parent with many children is read in full.
    """
    return [
        "gh", "api",
        "--paginate",
        f"repos/{{owner}}/{{repo}}/issues/{parent_number}/sub_issues",
    ]


def resolve_issue_database_id(
    config: dict[str, Any], *, issue_number: int | str
) -> int | None:
    """Resolve an issue NUMBER to its integer database id via ``gh api``.

    The sub-issues endpoint keys on the database id, not the number and not the
    GraphQL node id. ``gh api repos/{owner}/{repo}/issues/<n> --jq .id`` yields
    the integer id; ``gh issue view --json id`` would return the node id, which
    the endpoint rejects. Returns ``None`` on any failure (missing ``gh``,
    non-zero exit, non-integer payload) — the caller degrades.
    """
    try:
        proc = _gh_call(
            [
                "gh", "api",
                f"repos/{{owner}}/{{repo}}/issues/{issue_number}",
                "--jq", ".id",
            ],
            config,
        )
    except FileNotFoundError:
        return None
    if proc.returncode != 0:
        return None
    text = (proc.stdout or "").strip()
    try:
        return int(text)
    except (TypeError, ValueError):
        return None


def link_sub_issue(
    config: dict[str, Any],
    *,
    parent_number: int | str,
    child_number: int | str,
) -> LinkResult:
    """Link the child issue under the parent via GitHub's native sub-issues API.

    The one place the native containment link is established (ADR-031
    sole-constructor discipline applied to containment). Composes three steps,
    all through the gh helper (DEC-023 host/owner pinning):

      1. resolve the child's integer database id (the id the endpoint needs);
      2. read the parent's current sub-issues and short-circuit to
         :attr:`LinkOutcome.ALREADY` when the child is present (value-equality
         idempotency per DEC-026);
      3. POST the add.

    Never raises and never returns a fatal posture for an *unsupported* instance:
    a 404 / 410 / 422 (or a missing endpoint on older GHES) yields
    :attr:`LinkOutcome.UNSUPPORTED` so the caller carries the textual ref as the
    fallback. A genuine error (auth / network / missing ``gh``, or an
    unresolvable child id) yields :attr:`LinkOutcome.FAILED` for the caller to
    report — still non-fatal to the create, which already wrote the textual ref.
    """
    child_id = resolve_issue_database_id(config, issue_number=child_number)
    if child_id is None:
        return LinkResult(
            LinkOutcome.FAILED,
            detail=(
                f"could not resolve issue #{child_number}'s database id for the "
                "native sub-issue link; textual ref recorded"
            ),
        )

    # Idempotency read: already a sub-issue of this parent? value-equality skip.
    existing = _list_sub_issue_ids(config, parent_number=parent_number)
    if existing is not None and child_id in existing:
        return LinkResult(
            LinkOutcome.ALREADY,
            detail=(
                f"#{child_number} is already a native sub-issue of #{parent_number} "
                "(no-op)"
            ),
        )

    args = add_sub_issue_args(parent_number=parent_number, child_database_id=child_id)
    try:
        proc = _gh_call(args, config)
    except FileNotFoundError:
        return LinkResult(
            LinkOutcome.FAILED,
            detail="`gh` not on PATH; native sub-issue link skipped, textual ref recorded",
        )
    if proc.returncode == 0:
        return LinkResult(
            LinkOutcome.LINKED,
            detail=f"linked #{child_number} as a native sub-issue of #{parent_number}",
        )

    stderr = (proc.stderr or "").strip()
    if _is_unsupported(stderr):
        return LinkResult(
            LinkOutcome.UNSUPPORTED,
            detail="native sub-issues unsupported on this instance; textual ref recorded",
        )
    return LinkResult(
        LinkOutcome.FAILED,
        detail=(
            f"native sub-issue link failed (gh exit {proc.returncode}); "
            f"textual ref recorded. stderr: {stderr or 'no stderr'}"
        ),
    )


def _list_sub_issue_ids(
    config: dict[str, Any], *, parent_number: int | str
) -> set[int] | None:
    """Return the set of database ids of the parent's current sub-issues.

    ``None`` when the list could not be read (missing ``gh``, non-zero exit,
    unparseable payload) — the caller then proceeds to the add without the
    idempotency short-circuit (a duplicate add on an already-linked child is
    itself caught as UNSUPPORTED/handled by the add's own outcome, so a failed
    read never wrongly reports ALREADY). An empty set is a successful read of a
    parent with no sub-issues.
    """
    args = list_sub_issues_args(parent_number=parent_number)
    try:
        proc = _gh_call(args, config)
    except FileNotFoundError:
        return None
    if proc.returncode != 0:
        return None
    payload = _parse_concatenated_arrays((proc.stdout or "").strip())
    if payload is None:
        return None
    ids: set[int] = set()
    for entry in payload:
        if isinstance(entry, dict):
            raw = entry.get("id")
            if isinstance(raw, int):
                ids.add(raw)
    return ids


def _is_unsupported(stderr: str) -> bool:
    """True when ``gh``'s stderr indicates the instance lacks sub-issue support.

    ``gh api`` prints an ``HTTP <status>`` line on a non-2xx response; the
    unsupported statuses (404 / 410 / 422) mean the endpoint is absent or the
    feature is off. Matched as a substring of the stderr so the exact phrasing
    of ``gh``'s error line does not have to be pinned.
    """
    lowered = stderr.lower()
    for status in _UNSUPPORTED_STATUSES:
        if f"http {status}" in lowered or f"({status})" in lowered:
            return True
    # `gh` sometimes phrases a missing endpoint as "Not Found" without the code.
    return "not found" in lowered


def _parse_concatenated_arrays(text: str) -> list | None:
    """Parse ``gh --paginate`` output, which may concatenate JSON arrays.

    Mirrors ``_lib.milestone._parse_concatenated_arrays``. Returns the merged
    list, or ``None`` when nothing parses (so the caller can distinguish an empty
    list — a parent with no sub-issues — from an unreadable payload). An empty
    input is an empty list (a successful read of an empty page).
    """
    if not text:
        return []
    decoder = json.JSONDecoder()
    out: list = []
    idx = 0
    parsed_any = False
    while idx < len(text):
        while idx < len(text) and text[idx].isspace():
            idx += 1
        if idx >= len(text):
            break
        try:
            obj, end = decoder.raw_decode(text, idx)
        except ValueError:
            break
        parsed_any = True
        if isinstance(obj, list):
            out.extend(obj)
        idx = end
    return out if parsed_any else None


def _gh_call(args: list[str], config: dict[str, Any]) -> subprocess.CompletedProcess:
    """Call ``gh`` through the helper. Direct subprocess fallback if helper missing.

    Mirrors ``_lib.substrate_writes._gh_call`` so the containment write keeps the
    same execution path (adopter host/owner pinned per DEC-023) as the other
    non-label substrate writes.
    """
    if gh_run is not None:
        return gh_run(args, config, check=False)
    return subprocess.run(args, capture_output=True, text=True, check=False)


# =========================================================================
# Read seam — resolve a parent's children (native-where-present / textual-
# otherwise / native-wins). The counterpart to the write half above.
# =========================================================================


class ChildSubstrate(Enum):
    """Which substrate a resolved child came from (DEC-005's two mechanisms).

    NATIVE   — a GitHub native sub-issue of the parent (the canonical mechanism).
    TEXTUAL  — discovered only via the child's body first-line parent-ref (the
               projection); present in the corpus but NOT a native sub-issue.

    On conflict (a child present BOTH natively and textually) the child resolves
    to NATIVE — "native wins" (DEC-005). The substrate is surfaced so a consumer
    can render or reason about provenance; the child set itself is the union with
    native-wins dedup.
    """

    NATIVE = "native"
    TEXTUAL = "textual"


@dataclass(frozen=True)
class ResolvedChild:
    """One child of a parent, with the substrate it was resolved from.

    ``number`` is the child issue number (the methodology's stable key, shared by
    both substrates — the native sub-issues payload carries ``number`` and the
    textual parent-ref names ``#<number>``). Dedup across the two substrates is by
    ``number``; ``substrate`` records who won (NATIVE on conflict per DEC-005).
    """

    number: int
    substrate: ChildSubstrate


@dataclass(frozen=True)
class ChildResolution:
    """The resolved child set for one parent, plus how it was resolved.

    Fields:
      children          — the resolved children, sorted by number, deduped across
                          substrates with native-wins.
      native_supported  — False when the native sub-issues read returned
                          unsupported (404/410/422 / missing ``gh``); the result
                          is then textual-only (graceful degradation, like the
                          write side). True when the native read succeeded (even
                          if it returned zero native children). None is not used —
                          a failed-but-supported read also yields textual-only
                          with this False (the consumer cannot tell, and need not:
                          the textual projection is the documented fallback).

    Convenience accessors keep call sites terse and stop each consumer from
    re-deriving the same projections off ``children``.
    """

    children: tuple[ResolvedChild, ...]
    native_supported: bool

    @property
    def numbers(self) -> list[int]:
        """All child numbers (union, native-wins dedup), sorted."""
        return [c.number for c in self.children]

    @property
    def native_numbers(self) -> list[int]:
        """Child numbers that resolved from the NATIVE substrate, sorted."""
        return sorted(c.number for c in self.children if c.substrate is ChildSubstrate.NATIVE)

    @property
    def textual_numbers(self) -> list[int]:
        """Child numbers that resolved from the TEXTUAL substrate only, sorted."""
        return sorted(c.number for c in self.children if c.substrate is ChildSubstrate.TEXTUAL)


def read_native_child_numbers(
    config: dict[str, Any], *, parent_number: int | str
) -> set[int] | None:
    """Return the issue NUMBERS of the parent's native sub-issues.

    Reads ``GET /repos/{owner}/{repo}/issues/{parent}/sub_issues`` (paginated)
    through the gh helper (DEC-023 host/owner pinning), the same endpoint the
    write half's idempotency read uses — but keyed on the child ``number`` (the
    methodology's stable id) rather than the database ``id`` the *write* needs.

    Returns ``None`` when the native read is **unsupported or unreadable** — a
    404/410/422 (older GHES / feature off), a missing ``gh``, a non-zero exit, or
    an unparseable payload. ``None`` is the signal to the resolver to fall back to
    **textual-only** (graceful degradation, the read mirror of the write side's
    UNSUPPORTED no-op). An empty set is a *successful* read of a parent with no
    native sub-issues — distinct from ``None``, and it does NOT trigger textual
    fallback (the parent genuinely has no native children).
    """
    args = list_sub_issues_args(parent_number=parent_number)
    try:
        proc = _gh_call(args, config)
    except FileNotFoundError:
        return None
    if proc.returncode != 0:
        return None
    payload = _parse_concatenated_arrays((proc.stdout or "").strip())
    if payload is None:
        return None
    numbers: set[int] = set()
    for entry in payload:
        if isinstance(entry, dict):
            raw = entry.get("number")
            if isinstance(raw, int):
                numbers.add(raw)
    return numbers


def resolve_children(
    config: dict[str, Any],
    *,
    parent_number: int,
    corpus: dict[int, str],
) -> ChildResolution:
    """Resolve a parent's children — native-where-present, textual-otherwise,
    native-wins on conflict (DEC-005).

    The sole read-seam for "what are this parent's children?" Both ``show-tree``
    and the DEC-034 closure-fold child-walk resolve through it so neither
    re-derives containment (the ADR-026 one-read-seam discipline applied to the
    containment axis).

    Args:
      parent_number — the parent whose children to resolve.
      corpus        — the already-fetched issue corpus as ``{number: body}`` for
                      EVERY issue the caller knows about. The textual side is
                      resolved from this map with **zero** extra API calls — the
                      caller has already paid for the corpus fetch (``show-tree``
                      and the closure-fold both ``gh issue list`` the whole repo
                      once). See the cost note below.

    Resolution:
      1. Native side — one ``GET …/sub_issues`` call for THIS parent
         (:func:`read_native_child_numbers`). Unsupported/unreadable → textual-
         only (``native_supported=False``).
      2. Textual side — every corpus issue whose body first-line parent-ref names
         ``parent_number`` (``_body_names_parent``), excluding the parent itself.
      3. Union with **native-wins dedup**: a child present both ways is NATIVE; a
         child present only textually is TEXTUAL; a native child not in the
         corpus is still NATIVE (mixed-mode — the native panel is authoritative
         even for a child the textual scan missed).

    API cost (the deliberate shape): the textual side is free (corpus already in
    hand); the native side is **one call per parent resolved**, NOT per corpus
    issue. Both consumers resolve children one parent at a time (``show-tree``
    walks known parents; the closure fold resolves a single container), so native
    reads scale with *parents queried*, not corpus size. A whole-tree ``show-tree``
    does pay one native call per node that has children — bounded by the tree's
    internal-node count, well under the corpus size, and the price of honouring
    "native wins" without a private GraphQL batch (a batched ``subIssues`` GraphQL
    pass is a later optimisation, not pinned here — COR-007 speculative-generality
    restraint).
    """
    native = read_native_child_numbers(config, parent_number=parent_number)
    native_supported = native is not None
    native_set = native or set()

    textual_set = {
        number
        for number, body in corpus.items()
        if number != parent_number and _body_names_parent(body, parent_number)
    }

    resolved: list[ResolvedChild] = []
    for number in native_set:
        resolved.append(ResolvedChild(number=number, substrate=ChildSubstrate.NATIVE))
    for number in textual_set - native_set:  # native-wins: skip textual dupes
        resolved.append(ResolvedChild(number=number, substrate=ChildSubstrate.TEXTUAL))
    resolved.sort(key=lambda c: c.number)
    return ChildResolution(children=tuple(resolved), native_supported=native_supported)


def _body_names_parent(body: str, parent_number: int) -> bool:
    """True when a child body's FIRST non-blank line is a parent-ref naming
    ``parent_number`` (``<Word>: #<n>``).

    The textual-side recognition, identical to the convention every other walker
    uses (``show-tree._extract_parent_ref``, ``close-issue._walk_parent_chain``,
    ``lifecycle_inference.parent_ref``). Co-located here so the read seam owns the
    textual projection too — a consumer routing through the seam never re-parses
    the body itself.
    """
    if not body:
        return False
    for line in body.splitlines():
        s = line.strip()
        if not s:
            continue
        m = re.match(r"^([A-Za-z]+):\s+#(\d+)", s)
        if not m:
            return False
        return int(m.group(2)) == parent_number
    return False


# =========================================================================
# Render-on-demand textual children view (DEC-039 D4 / ADR-035 section 4).
#
# Where the tracker has no native sub-issues panel (`containment: textual`), a
# parent has no parent-side children view at all — only the child-side textual
# refs + `show-tree` on demand. This half supplies that view as a **generated
# do-not-edit comment on the parent**, written by **FULL OVERWRITE** through one
# construction point and refreshed by the read path. It is a derived, regenerable
# view: the child-side ref + the read seam (`resolve_children`) remain the source
# of truth. **Never an append** — there is exactly one marked comment per parent,
# found by its marker and updated in place (DEC-039 D4: a stored body block would
# be a drift-prone second source of truth; an append would churn comments on every
# child-create).
#
# Mode gate: the writer is a **no-op in native mode** (the native sub-issues panel
# already gives parent-side visibility). The single mode gate is
# `refresh_children_comment`, which consults the caller-supplied containment mode
# once and returns a no-op outcome for `native`.
# =========================================================================


# The do-not-edit marker that identifies the generated children comment. An HTML
# comment so it is INVISIBLE in rendered markdown, yet a stable string the
# find-existing scan keys on (a human reading the source sees the do-not-edit
# notice; a human reading the rendered comment sees only the children list under
# the visible heading). This is the one place the marker text lives — both the
# renderer (emits it) and the find-existing scan (matches it) reference it, so
# they cannot drift.
CHILDREN_VIEW_MARKER = "<!-- pkit:children-view do-not-edit -->"

# The containment-mode value that ENABLES the textual children view. Mirrors
# ``axis_labels.CONTAINMENT_TEXTUAL`` — duplicated here (a bare string) so this
# module's writer needs no import of the selector seam (it takes the mode as a
# plain ``str`` argument; the caller resolves the mode through
# ``axis_labels.containment_mode`` and passes the value). Any non-``textual``
# value (``native``, the greenfield default, or anything unrecognised) is a no-op.
CONTAINMENT_TEXTUAL = "textual"

# The visible heading + do-not-edit notice the rendered comment carries, so a
# human reading the COMMENT (not the source) also knows not to hand-edit it.
_CHILDREN_VIEW_HEADING = "### Children (auto-generated — do not edit)"
_CHILDREN_VIEW_NOTICE = (
    "_This comment is a regenerable view of this issue's children, refreshed by "
    "project-kit. Edits are overwritten. The source of truth is each child's "
    "first-line parent-ref._"
)


class RefreshOutcome(Enum):
    """The outcome class of one children-comment refresh attempt.

    CREATED    — no marked comment existed; one was posted this call.
    UPDATED    — the marked comment existed and its body changed; PATCHed.
    UNCHANGED  — the marked comment existed and the freshly-rendered body equals
                 its current body (value-equality idempotency) → NO write.
    SKIPPED    — native mode (the native panel suffices) → the writer is a no-op.
    FAILED     — a gh read/write failed (auth/network/missing `gh`). Non-fatal to
                 the caller — the child-side textual ref is the spine.
    """

    CREATED = "created"
    UPDATED = "updated"
    UNCHANGED = "unchanged"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass(frozen=True)
class RefreshResult:
    """Outcome of one children-comment refresh — a neutral carrier.

    Failure-posture-neutral in the same spirit as :class:`LinkResult` (ADR-035
    section 3, ADR-031 point 6): it records what happened; the caller decides what
    it means. ``create-issue`` treats every outcome as non-fatal — the textual ref
    is the spine — and reports a one-line note keyed on ``outcome``.
    """

    outcome: RefreshOutcome
    detail: str = ""

    @property
    def ok(self) -> bool:
        """True when the view is in the desired state after this call (created,
        updated, already-current, or a deliberate native-mode no-op). Only FAILED
        is a genuine problem."""
        return self.outcome is not RefreshOutcome.FAILED


def render_children_comment_body(
    *,
    parent_number: int,
    resolution: ChildResolution,
    titles: dict[int, str] | None = None,
) -> str:
    """Render the parent's children-comment body from a :class:`ChildResolution`.

    The rendered view is DERIVED from the read seam's output (DEC-039 D4: the
    comment is a regenerable view, not a source of truth). The body carries:

      1. the :data:`CHILDREN_VIEW_MARKER` (the find-existing key, invisible in
         rendered markdown);
      2. a visible heading + do-not-edit notice so a human reading the rendered
         comment also knows not to hand-edit it;
      3. one bullet per resolved child — ``- #<n>`` (GitHub auto-links the issue
         reference), with the child's title appended when ``titles`` carries it,
         and a ``(textual)`` provenance marker on a textual-only child (native is
         the default and unmarked, matching ``show-tree``).

    Children are listed in the resolution's order (sorted by number — the seam
    already sorts). An empty child set renders an explicit "no children" line so a
    parent whose last child was removed gets an honest, current view rather than a
    stale list. The output is deterministic for a given ``(resolution, titles)`` so
    the idempotency value-equality check (re-render of the same child set → no
    write) holds.
    """
    titles = titles or {}
    lines = [
        CHILDREN_VIEW_MARKER,
        _CHILDREN_VIEW_HEADING,
        "",
        _CHILDREN_VIEW_NOTICE,
        "",
    ]
    if not resolution.children:
        lines.append("_No children._")
    else:
        for child in resolution.children:
            title = titles.get(child.number)
            label = f"#{child.number}" + (f" — {title}" if title else "")
            marker = "  _(textual)_" if child.substrate is ChildSubstrate.TEXTUAL else ""
            lines.append(f"- {label}{marker}")
    return "\n".join(lines) + "\n"


def list_issue_comments_args(*, parent_number: int | str) -> list[str]:
    """Construct the ``gh api …/comments`` list (GET) argv.

    Reads ``GET /repos/{owner}/{repo}/issues/{parent}/comments`` (paginated) to
    find the existing marked children comment by its marker — and crucially to get
    each comment's REST ``id`` (``gh issue view --json comments`` does NOT carry
    the REST comment id the PATCH needs). The find-existing scan keys on
    :data:`CHILDREN_VIEW_MARKER` in the comment body.
    """
    return [
        "gh", "api",
        "--paginate",
        f"repos/{{owner}}/{{repo}}/issues/{parent_number}/comments",
    ]


def create_comment_args(*, parent_number: int | str, body: str) -> list[str]:
    """Construct the ``gh api …/comments`` create (POST) argv.

    Posts ``POST /repos/{owner}/{repo}/issues/{parent}/comments`` with the
    rendered body. ``-f body=<text>`` sends the body as a string field (the
    comment body is markdown text, not a typed value — ``-f``, not ``-F``). Used
    only when no marked comment yet exists; an existing one is UPDATED in place
    (never a second comment — DEC-039 D4's overwrite-not-append invariant).
    """
    return [
        "gh", "api",
        "-X", "POST",
        f"repos/{{owner}}/{{repo}}/issues/{parent_number}/comments",
        "-f", f"body={body}",
    ]


def update_comment_args(*, comment_id: int | str, body: str) -> list[str]:
    """Construct the ``gh api …/comments/<id>`` update (PATCH) argv.

    PATCHes ``/repos/{owner}/{repo}/issues/comments/{comment_id}`` with the
    freshly-rendered body — the **full overwrite** that makes the children view a
    single source (DEC-039 D4 / ADR-035 section 4). The comment id is the REST id
    read from :func:`list_issue_comments_args`. ``-f body=<text>`` overwrites the
    whole body (markdown string field). This is the overwrite that replaces the
    append a naive children view would do.
    """
    return [
        "gh", "api",
        "-X", "PATCH",
        f"repos/{{owner}}/{{repo}}/issues/comments/{comment_id}",
        "-f", f"body={body}",
    ]


# Sentinel distinguishing "the comment list could not be READ" from "read OK,
# no marked comment present". The distinction is load-bearing: a failed read must
# be reported FAILED (never treated as absent, which would duplicate-post — the
# very append/churn DEC-039 D4 forbids), while a clean read with no marked comment
# is the CREATE path. A distinct singleton (not ``None``) so the two cannot be
# conflated at the call site.
class _CommentReadFailed:
    _instance: _CommentReadFailed | None = None

    def __new__(cls) -> _CommentReadFailed:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance


COMMENT_READ_FAILED: _CommentReadFailed = _CommentReadFailed()


def find_children_comment(
    config: dict[str, Any], *, parent_number: int | str
) -> tuple[int, str] | None | _CommentReadFailed:
    """Find the parent's existing marked children comment.

    Lists the parent's comments and returns one of three signals — the
    three-way distinction overwrite-not-append depends on:

      * ``(comment_id, body)`` — the FIRST comment whose body carries
        :data:`CHILDREN_VIEW_MARKER`. The refresh OVERWRITES this one in place
        (PATCH), never posting a second comment.
      * ``None`` — the list was read cleanly and NO marked comment exists. The
        refresh CREATES one (the first POST).
      * :data:`COMMENT_READ_FAILED` — the list could NOT be read (missing ``gh``,
        non-zero exit, unparseable payload). The refresh reports FAILED and writes
        NOTHING — a failed read is never treated as "absent" (which would
        duplicate-post, the churn DEC-039 D4 forbids).
    """
    args = list_issue_comments_args(parent_number=parent_number)
    try:
        proc = _gh_call(args, config)
    except FileNotFoundError:
        return COMMENT_READ_FAILED
    if proc.returncode != 0:
        return COMMENT_READ_FAILED
    payload = _parse_concatenated_arrays((proc.stdout or "").strip())
    if payload is None:
        return COMMENT_READ_FAILED
    for entry in payload:
        if not isinstance(entry, dict):
            continue
        body = entry.get("body")
        if isinstance(body, str) and CHILDREN_VIEW_MARKER in body:
            cid = entry.get("id")
            if isinstance(cid, int):
                return cid, body
    return None


def refresh_children_comment(
    config: dict[str, Any],
    *,
    parent_number: int,
    corpus: dict[int, str],
    containment_mode: str,
    titles: dict[int, str] | None = None,
) -> RefreshResult:
    """Refresh the parent's render-on-demand children comment (the ONE writer).

    The single construction point for the textual children view (ADR-035 section
    3/4): every refresh of the view routes through here; no script string-builds a
    children-comment write inline. Composes the render + find-existing + overwrite:

      1. **Mode gate (the one point).** In ``native`` mode the native sub-issues
         panel already gives parent-side visibility, so this is a **no-op**
         (:attr:`RefreshOutcome.SKIPPED`). Only ``textual`` mode renders + writes.
      2. **Render** the body from the read seam's resolution
         (:func:`resolve_children` → :func:`render_children_comment_body`) — the
         comment is a derived view, the seam stays the source of truth.
      3. **Find** the existing marked comment (:func:`find_children_comment`). A
         failed READ is :attr:`RefreshOutcome.FAILED` (never treated as "absent",
         which would duplicate-post).
      4. **Idempotency.** If a marked comment exists and its body equals the
         freshly-rendered body, **skip the write** (:attr:`RefreshOutcome.UNCHANGED`)
         — no comment-edit churn on a re-render of the same child set.
      5. **Write by overwrite** — PATCH the existing comment in place
         (:attr:`RefreshOutcome.UPDATED`), or POST a new one when none exists
         (:attr:`RefreshOutcome.CREATED`). **Never a second comment** — overwrite,
         never append (DEC-039 D4).

    Failure-posture-neutral (ADR-035 section 3): never raises; a failed read/write
    yields :attr:`RefreshOutcome.FAILED` for the caller to report as a one-line
    note — the child-side textual ref is the spine, so a failed refresh never fails
    the caller's operation.
    """
    if containment_mode != CONTAINMENT_TEXTUAL:
        return RefreshResult(
            RefreshOutcome.SKIPPED,
            detail=(
                f"containment is {containment_mode!r}; children comment is a no-op "
                "(the native sub-issues panel gives parent-side visibility)"
            ),
        )

    resolution = resolve_children(config, parent_number=parent_number, corpus=corpus)
    body = render_children_comment_body(
        parent_number=parent_number, resolution=resolution, titles=titles
    )

    existing = find_children_comment(config, parent_number=parent_number)
    if existing is COMMENT_READ_FAILED:
        # A failed READ is never treated as "absent" (which would duplicate-post);
        # write nothing and report FAILED (non-fatal — the textual ref is the spine).
        return RefreshResult(
            RefreshOutcome.FAILED,
            detail=(
                f"could not read #{parent_number}'s comments to find the children "
                "view; no write attempted (avoiding a duplicate post)"
            ),
        )
    if existing is not None:
        comment_id, current_body = existing  # type: ignore[misc]
        if current_body == body:
            return RefreshResult(
                RefreshOutcome.UNCHANGED,
                detail=(
                    f"children comment on #{parent_number} already current "
                    f"({len(resolution.children)} child(ren)); no write"
                ),
            )
        args = update_comment_args(comment_id=comment_id, body=body)
        outcome, verb = RefreshOutcome.UPDATED, "updated"
    else:
        args = create_comment_args(parent_number=parent_number, body=body)
        outcome, verb = RefreshOutcome.CREATED, "created"

    try:
        proc = _gh_call(args, config)
    except FileNotFoundError:
        return RefreshResult(
            RefreshOutcome.FAILED,
            detail="`gh` not on PATH; children comment refresh skipped",
        )
    if proc.returncode == 0:
        return RefreshResult(
            outcome,
            detail=(
                f"{verb} children comment on #{parent_number} "
                f"({len(resolution.children)} child(ren))"
            ),
        )
    stderr = (proc.stderr or "").strip()
    return RefreshResult(
        RefreshOutcome.FAILED,
        detail=(
            f"children comment refresh on #{parent_number} failed "
            f"(gh exit {proc.returncode}). stderr: {stderr or 'no stderr'}"
        ),
    )
