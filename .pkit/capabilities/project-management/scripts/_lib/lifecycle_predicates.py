"""Predicate bodies for the rebound issue-lifecycle (DEC-033).

These are the READ-ONLY checks the process engine (COR-033) runs to resolve a
keyed issue's position and to evaluate its gates. The engine invokes each as a
plain subprocess `[script, <issue-number>, --json]` through the backbone's command runner — its own
process group, killed at the 30-second bound; see the process README's predicate-runner section —
(no shell, no `with` args
threaded — see the per-state detector scripts for how the target state is
fixed), reads structured JSON on stdout, and acts on it:

  classified detection (the lifecycle's one classifier, `detect-state`)
                                 -> {state: str|null, reason: str, detail?: {}}
  inferred detection (the per-state `detect-<state>`) / deterministic gate
                                 -> {result: bool, reason: str, detail?: {}}
  authorisation-artifact gate    -> {exists: bool, produced_by: str|null,
                                     reason: str, detail?: {}}

The shipped lifecycle detects with the classifier (COR-033 point 5): every
state names it, so the engine reads an issue once per reading of its position.
The per-state detectors stay registered, for direct use; both read the issue
through the one function below, so they cannot disagree.

Every function here fetches issue/PR state via the adopter-pinned `gh` helper
and returns the contract dict. They are strictly read-only (COR-033: `status`
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

from _lib import axis_labels, body_parent_ref, containment
from _lib import lifecycle_inference as infer
from _lib.gh import gh_run, load_adopter_config
from _lib.membership import resolve_capability_root

# A predicate that genuinely COULD NOT evaluate (gh failure, capability
# missing) carries this marker key. The thin predicate script strips it and
# exits non-zero, so the engine treats the predicate as INDETERMINATE
# (fail-closed, COR-033) rather than a clean result=False — a "couldn't tell"
# must never look like a "no".
INDETERMINATE_KEY = "_indeterminate"


def _indeterminate(reason: str) -> dict[str, Any]:
    return {"result": False, "reason": reason, INDETERMINATE_KEY: True}


# Pagination ceiling for the merged-PR lookup below. When the returned list hits
# its ceiling there MAY be rows we never saw, so the query is honestly
# indeterminate (fail-closed, COR-033) — not a confident negative. Kept named so
# the limit and its ceiling-check can never drift apart, and measured against the
# set the query actually fetches: the issue-corpus ceiling now lives behind the
# containment seam, which owns acquisition (ADR-035 §5).
_MERGED_PRS_LIMIT = 100


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
    the engine: an unevaluable predicate is indeterminate), and says why on
    standard error — a predicate's diagnostics channel, which the engine shows
    beside the indeterminate verdict — passing on what `gh` itself said."""
    try:
        proc = gh_run(
            ["gh", "issue", "view", str(issue_number), "--json", fields],
            config,
            check=False,
        )
    except FileNotFoundError:
        _say_unread(issue_number, "`gh` is not installed or not on PATH")
        return None
    if proc.returncode != 0:
        said = (proc.stderr or "").strip()
        _say_unread(issue_number, f"`gh issue view` exited {proc.returncode}", said)
        return None

    try:
        parsed = json.loads(proc.stdout)
    except (json.JSONDecodeError, ValueError):
        _say_unread(issue_number, "`gh issue view` printed no JSON document")
        return None
    if not isinstance(parsed, dict):
        _say_unread(issue_number, "`gh issue view` printed JSON that is not an object")
        return None
    return parsed


def _say_unread(issue_number: int, cause: str, said: str = "") -> None:
    """Why issue #N could not be read, on standard error."""
    print(f"could not read issue #{issue_number}: {cause}", file=sys.stderr)
    if said:
        print(said, file=sys.stderr)


# --- position detection ---------------------------------------------------


def _inferred_state(issue_number: int) -> str | dict[str, Any]:
    """The issue's live position by move-issue's exact precedence
    (`infer_current_state`), from ONE read of the issue — or, when it cannot be
    read, the indeterminate payload saying why. The one function the classifier
    and the per-state detectors answer from, so they cannot disagree.

    Map-aware (ADR-026 §5): the adopter's substrate-map is loaded and threaded
    into `infer_current_state`, so under a present map binding `state` to a
    `derive` predicate the position resolves from open/closed (+ a blocked label)
    rather than a kit `state:*` label — `open` or `blocked`, values the lifecycle
    does not declare. No map ⇒ the kit `state:*` precedence, byte-unchanged.
    """
    capability_root = _capability_root()
    if capability_root is None:
        return _indeterminate("project-management capability not found")
    config = _config(capability_root)
    substrate_map = axis_labels.load_substrate_map(capability_root)
    issue = _fetch_issue(issue_number, config, "state,milestone,labels")
    if issue is None:
        return _indeterminate(f"could not read issue #{issue_number} (gh failure)")
    return infer.infer_current_state(
        state=str(issue.get("state", "")).lower(),
        milestone=issue.get("milestone") or {},
        labels=_issue_labels(issue),
        substrate_map=substrate_map,
    )


def read_subject(subject: str) -> int | containment.ForeignIssue | None:
    """The issue a predicate's subject id names: ``"11"`` is this repository's
    #11, ``"owner/repo#42"`` an issue in another repository — the id the
    closure fold gives a native sub-issue that lives there (`cascade_members`)
    — and anything else names none."""
    text = subject.strip()
    if text.isdigit():
        return int(text)
    return containment.ForeignIssue.parse(text)


def member_id(child: containment.ResolvedChild) -> str:
    """The subject id the closure fold gives a child: its number, or
    ``owner/repo#<n>`` for one in another repository (`read_subject` reads it
    back)."""
    return child.ref if child.repository is not None else str(child.number)


def classify_state(issue: int | containment.ForeignIssue) -> dict[str, Any]:
    """The issue lifecycle's classifier — which state is the issue in?

    The lifecycle's five states all name it under `mode: classified` (COR-033
    point 5), so the engine runs it once per reading of an issue's position, and
    it reads the issue once. It answers `{state, reason}`: the inferred state
    when that is one of the lifecycle's states; `state: null`, with the inferred
    value in the reason, when the inference yields a value the lifecycle does
    not declare — a derive binding's `open` / `blocked`, a stray `state:<x>`
    label — which places the issue in none of them, as the five per-state
    detectors say by each answering false. When the issue cannot be read it
    returns the indeterminate payload; the script says why on standard error and
    exits non-zero.

    An issue in another repository is read by its open/closed alone
    (`_classify_foreign`).
    """
    if isinstance(issue, containment.ForeignIssue):
        return _classify_foreign(issue)
    issue_number = issue
    inferred = _inferred_state(issue_number)
    if isinstance(inferred, dict):
        return inferred
    if inferred in infer.STATE_ORDER:
        return {
            "state": inferred,
            "reason": f"#{issue_number} inferred state is {inferred!r}",
            "detail": {"inferred_state": inferred},
        }
    return {
        "state": None,
        "reason": (
            f"#{issue_number} inferred state is {inferred!r}, which is not a state of the "
            "issue lifecycle"
        ),
        "detail": {"inferred_state": inferred},
    }


def _classify_foreign(issue: containment.ForeignIssue) -> dict[str, Any]:
    """Which lifecycle state a native sub-issue in another repository is in.

    Its record is read in its own repository — one read, through the
    containment seam; nothing is ever written there. That repository need not
    follow this lifecycle, so its labels are not read: the tracker's own
    open/closed is. Closed reads `done`, as a closed issue does by every
    reader's precedence; open is none of the lifecycle's states, which holds a
    fold over it as any open child does. A record that cannot be read — no
    access, not found, a failed read — is the indeterminate payload, said why
    on standard error.
    """
    capability_root = _capability_root()
    if capability_root is None:
        return _indeterminate("project-management capability not found")
    config = _config(capability_root)
    record = containment.read_issue_record(
        config, issue_number=issue.number, repository=issue.repository
    )
    if isinstance(record, containment.UnreadIssue):
        print(f"could not read {issue.ref}: {record.detail}", file=sys.stderr)
        return _indeterminate(f"could not read {issue.ref}, an issue in another repository")
    detail = {"repository": issue.repository, "tracker_state": record.issue["state"].lower()}
    if record.issue["state"] == "CLOSED":
        done = infer.infer_current_state(state="closed", milestone={}, labels=[])
        return {
            "state": done,
            "reason": (
                f"{issue.ref} is closed in its own repository, which is read by its "
                "open/closed alone"
            ),
            "detail": detail,
        }
    return {
        "state": None,
        "reason": (
            f"{issue.ref} is open in its own repository, which is read by its open/closed "
            "alone: an open issue there is in none of the issue lifecycle's states"
        ),
        "detail": detail,
    }


def detect_state(issue_number: int, target_state: str) -> dict[str, Any]:
    """Detection predicate for one lifecycle state — the per-state detector,
    registered for direct use (the shipped lifecycle names the classifier).

    Answers from the same read as `classify_state` (`_inferred_state`):
    result=True iff the issue's inferred position equals `target_state`. So for
    every lifecycle state S, `detect_state(n, S).result` is
    `classify_state(n).state == S`, and the detectors are mutually exclusive —
    at most one matches — so the engine's first-true-state rule reproduces
    move-issue regardless of state order.
    """
    resolved = _inferred_state(issue_number)
    if isinstance(resolved, dict):
        return resolved
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
    substrate_map = axis_labels.load_substrate_map(capability_root)
    # Corpus + completeness both come from the seam (ADR-035 §5). This walk still
    # filters by the TEXTUAL parent-ref itself, because it needs each row's state,
    # labels and milestone to infer position — which the child-set resolver does
    # not carry. A natively-linked child whose body has no parent-ref line is
    # therefore invisible here; that gap is older than this change and is not the
    # close gate (this predicate informs forward-cascade reasoning).
    corpus = containment.fetch_issue_corpus(config)
    if corpus is None:
        return _indeterminate("could not list issues (gh failure)")
    if not corpus.complete:
        return _indeterminate(
            f"the issue corpus was not enumerated to exhaustion "
            f"(ceiling {containment.CORPUS_CEILING}); descendant walk may be incomplete"
        )
    children = corpus.rows
    active: list[int] = []
    for child in children:
        body = str(child.get("body") or "")
        if body_parent_ref.named_issue(body) != parent_number:
            continue
        child_state = infer.infer_current_state(
            state=str(child.get("state", "")).lower(),
            milestone=child.get("milestone") or {},
            labels=_issue_labels(child),
            substrate_map=substrate_map,
        )
        if infer.state_is_active(child_state):
            active.append(int(child.get("number", 0)))
    return {
        "result": bool(active),
        "reason": (
            f"#{parent_number} has active descendant(s): {', '.join(f'#{n}' for n in active)}"
            if active
            else f"#{parent_number} has no in-progress-or-further descendant"
        ),
        "detail": {"active_descendants": active},
    }


def cascade_members(parent_number: int) -> dict[str, Any]:
    """COR-037 cascade `members` predicate for the issue-lifecycle closure fold
    (DEC-034): the parent-scoped candidate-member SOURCE.

    Returns `{members: ["<n>", ...]}` — the issue numbers (as strings, the
    engine's subject ids) of EVERY child of `parent_number`, open and closed
    alike. Children are resolved through the SAME containment read-seam
    (`_lib.containment.resolve_children`) `show-tree` uses — the union of the
    parent's native sub-issues and every issue whose first line names it, in any
    form, a child present both ways counted once as native (DEC-005). Routing
    both consumers through the one seam is the contract ADR-035 holds: the
    closure fold does NOT re-derive containment by re-parsing body parent-refs in
    parallel with `show-tree`; there is one reader of "what are this parent's
    children?", and this is it for the fold.

    A native sub-issue that lives in another repository is a member like any
    other child, under its own id `owner/repo#<n>` (`member_id`), so it is never
    read as this repository's issue of the same number: the engine's per-member
    steps read its state in its own repository (`classify_state`).

    The full set (not just open children) is intentional: the engine resolves
    EACH member's lifecycle outcome and the `all`-over-`done` reducer folds them.
    A closed child resolves to the terminal `done`; an open child resolves to a
    non-terminal state (outcome unresolved) and so HOLDS the fold — reproducing
    "an open child blocks eligibility" without this predicate filtering by state.
    Read live, run ONCE threaded with the parent subject (COR-037).

    This is the SOLE parent-scoping authority for the fold. The engine does not
    thread the folding parent to the `membership` predicate (COR-032's single-
    subject line), so `cascade_membership` structurally cannot re-scope to this
    parent — if this source were ever made over-broad (e.g. emitting every
    hierarchy child regardless of parent), `membership` would NOT catch it.
    Parent-faithfulness lives here and only here.

    Indeterminate (the engine holds the whole fold fail-closed) whenever the seam
    cannot vouch for the child set: a gh failure, a corpus not enumerated to
    exhaustion, or a native read that failed rather than being unsupported. Never
    a confident "no children" on a partial read — that could let an `all`
    vacuously satisfy via `on_empty`, closing a container over a live child.
    """
    capability_root = _capability_root()
    if capability_root is None:
        return _indeterminate("project-management capability not found")
    config = _config(capability_root)
    # The seam acquires the corpus and reports whether it saw all of it; this
    # predicate no longer keeps its own ceiling (ADR-035 §5). Enumerating the
    # whole tracker to answer a question about one parent is what hit a 500-row
    # ceiling at 507 issues and blocked every container close (#846).
    resolution = containment.resolve_children(config, parent_number=parent_number)
    if not resolution.complete:
        return _indeterminate(
            f"the child set for #{parent_number} may be incomplete: {resolution.incomplete_reason}"
        )
    members = [member_id(child) for child in resolution.children]
    return {
        "members": members,
        "reason": (
            f"#{parent_number} has {len(members)} child member(s): "
            f"{', '.join(child.ref for child in resolution.children)}"
            if members
            else f"#{parent_number} has no child members"
        ),
    }


def cascade_membership(child: int | containment.ForeignIssue) -> dict[str, Any]:
    """COR-037 cascade `membership` predicate for the closure fold (DEC-034):
    the per-subject step the engine takes for each candidate `cascade_members`
    listed.

    It answers `result=True` for every candidate it can read, and indeterminate
    for one it cannot; it never answers a determinate "not a member". Who the
    container's children are is decided once, by `cascade_members` through the
    containment seam, which lists native sub-issues as well as issues whose first
    line names the container (ADR-035). A native child's first line may name no
    issue at all — a sub-issue linked in GitHub's UI, or one `create-issue
    --parent N --milestone M` filed, whose first line is the `Milestone:` ref — so
    a second reading of the first line here would drop a child the seam returned,
    and let the container close while that child is open (#1304): the engine
    drops a candidate this predicate determinately rejects, so it rejects none.

    The engine threads ONLY the candidate's subject id (the single-subject runner,
    COR-032's never-hold-a-tree line), so this step has no parent to compare
    against and does not re-scope the members list: parent-faithfulness rests on
    `cascade_members` alone. What this step does carry is the read: a candidate
    whose record cannot be read (a gh failure) is indeterminate, which the engine
    turns into a whole-fold fail-closed hold per COR-037, rather than silently
    dropping the candidate.

    The read is the containment seam's (`containment.resolve_parent`, one record
    read), and what it finds is an account for the reader, not a verdict:
    `detail.parent_ref` is the issue the candidate's first line names, `None`
    when it names none — a line naming the candidate itself names none — and
    `detail.parent_kind` how the first line and the
    native parent stand (`agreed`, `native-only`, `textual-only`, `disagree`,
    `none`). The candidate is read untyped: which issue a line names, and so the
    kind, does not depend on the type.

    A candidate in another repository (`owner/repo#<n>`, a native sub-issue that
    lives there) is a member on the seam's word and is not read here: no first
    line in this repository can name it, so this read would add nothing, and
    whether its record can be read is settled by the one read of its state the
    engine's next step makes (`classify_state`), which holds the fold
    indeterminate when it cannot. `detail.repository` names its repository.
    """
    capability_root = _capability_root()
    if capability_root is None:
        return _indeterminate("project-management capability not found")
    if isinstance(child, containment.ForeignIssue):
        return {
            "result": True,
            "reason": (
                f"{child.ref} is a member: the members list holds it (a native sub-issue in "
                "another repository, whose state is read there)"
            ),
            "detail": {"repository": child.repository},
        }
    child_number = child
    config = _config(capability_root)
    resolution = containment.resolve_parent(
        config, issue_number=child_number, structural_type=None, issue_types={}
    )
    if resolution.unread is not None:
        _say_unread(child_number, resolution.unread.detail)
        return _indeterminate(f"could not read issue #{child_number} (gh failure)")
    parent = resolution.named
    if parent is not None:
        first_line = f"names #{parent}"
    elif resolution.names_itself:
        first_line = "names the issue itself, which is no parent"
    else:
        first_line = "names no issue"
    native = (
        f"its native parent is {resolution.native.ref}"
        if resolution.native is not None
        else "it has no native parent"
    )
    return {
        "result": True,
        "reason": (
            f"#{child_number} is a member: the members list holds it (its first line "
            f"{first_line}, {native})"
        ),
        "detail": {"parent_ref": parent, "parent_kind": resolution.kind.value},
    }


def gate_checkboxes_ticked(issue_number: int) -> dict[str, Any]:
    """Deterministic close-gate (DEC-007): result=True iff the issue body has no
    unticked `- [ ]` checkbox. Reads the rule from `_lib.checkbox_gate`, the one
    home close-issue / done-work / merge-pr also refuse on, so the engine's
    verdict cannot drift from the commands'.
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
    is non-overridable, COR-033 P4) — this predicate returns only the facts. A
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
        "reason": (f"PR #{pr.get('number')} closing #{issue_number} merged by {merged_by!r}"),
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
                merged_by_raw.get("login") if isinstance(merged_by_raw, dict) else merged_by_raw
            )
            return {"number": pr.get("number"), "merged_by": merged_by}
    # No match within the fetched page. If we hit the ceiling there may be an
    # unseen merged PR -> indeterminate (fail-closed), not a confident negative.
    if len(prs) >= _MERGED_PRS_LIMIT:
        return _GH_ERROR
    return None
